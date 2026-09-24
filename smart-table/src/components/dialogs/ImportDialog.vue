<script setup lang="ts">
import { ref, computed, watch, onUnmounted } from "vue";
import { ElMessage, ElLoading } from "element-plus";
import { useI18n } from "vue-i18n";
import {
  Upload,
  ArrowRight,
  ArrowLeft,
  Check,
  ArrowDown,
  Download,
  Close,
  VideoPause,
  VideoPlay,
  Refresh,
} from "@element-plus/icons-vue";
import type { FieldEntity } from "@/db/schema";
import {
  parseFile,
  autoMatchFields,
  convertImportData,
  validateRow,
  getFieldOptions,
  findOptionNameById,
  splitMemberNames,
  type ParsedFileData,
  type FieldMapping,
} from "@/utils/importExport";
import { getFieldTypeLabel, type CellValue, FieldType } from "@/types/fields";
import { exportTemplate } from "@/utils/templateGenerator";
import { searchUsers } from "@/api/user";
import {
  batchMatchRecordLinks,
  type BatchMatchLinkPair,
} from "@/services/api/linkApiService";
import { getFields } from "@/services/api/fieldApiService";
import {
  BatchImportController,
  type BatchProgress,
  type BatchResult,
  type BatchConfig,
  DEFAULT_BATCH_CONFIG,
} from "@/services/batchImportService";

const { t } = useI18n();

interface Props {
  visible: boolean;
  tableId: string;
  fields: FieldEntity[];
}

const props = defineProps<Props>();

const emit = defineEmits<{
  (e: "update:visible", value: boolean): void;
  (e: "imported"): void;
}>();

const currentStep = ref(1);
const totalSteps = 4;

const uploadedFile = ref<File | null>(null);
const parsedData = ref<ParsedFileData | null>(null);
const isParsing = ref(false);

const fieldMappings = ref<FieldMapping[]>([]);

const importController = ref<BatchImportController | null>(null);
const isImporting = ref(false);
const importProgress = ref<BatchProgress | null>(null);
const importResult = ref<BatchResult | null>(null);
const isPaused = ref(false);
const batchConfig = ref<BatchConfig>({ ...DEFAULT_BATCH_CONFIG });
const showErrorDetails = ref(false);
const failedBatchInputs = ref<Record<number, Record<string, unknown>[]>>({});

// ==================== 关联字段自动匹配 ====================

// 关联字段的匹配字段配置：sourceColumn -> 目标表匹配字段 ID
const matchFieldIds = ref<Record<string, string>>({});

// 目标表字段缓存：linkedTableId -> 字段列表
interface TargetFieldOption {
  id: string;
  name: string;
  type: string;
  is_primary: boolean;
}
const targetFieldsCache = ref<Record<string, TargetFieldOption[]>>({});
const isLoadingTargetFields = ref<Record<string, boolean>>({});

// 建关联阶段进度
const linkMatchPhase = ref(false);
const linkMatchProgress = ref<{ current: number; total: number }>({ current: 0, total: 0 });

// 关联匹配结果汇总（展示于结果步骤）
interface LinkMatchSummary {
  fieldLabel: string;
  matchedCount: number;
  unmatchedCount: number;
  unmatchedValues: Array<{ value: string; count: number }>;
  duplicateTargetCount: number;
}
const linkMatchSummaries = ref<LinkMatchSummary[]>([]);

// ==================== 成员字段姓名解析 ====================

// 姓名→用户ID映射（导入前解析构建，convertImportData 转换时使用）
const memberNameToId = ref<Map<string, string>>(new Map());
// 成员解析阶段进度（Step 3 展示）
const memberMatchPhase = ref(false);
// 成员解析结果汇总（展示于结果步骤）
interface MemberMatchSummary {
  fieldLabel: string;
  matchedCount: number;
  unmatchedCount: number;
  unmatchedNames: Array<{ name: string; count: number }>;
}
const memberMatchSummaries = ref<MemberMatchSummary[]>([]);

const availableFields = computed(() => {
  return props.fields.filter((f) => !f.isSystem);
});

onUnmounted(() => {
  if (importController.value) {
    importController.value.cancel();
  }
});

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms.toFixed(0)} ${t('common.unitMillisecond')}`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)} ${t('common.unitSecond')}`;
  const minutes = Math.floor(ms / 60000);
  const seconds = Math.floor((ms % 60000) / 1000);
  return `${minutes} ${t('common.unitMinute')} ${seconds} ${t('common.unitSecond')}`;
}

async function handleFileChange(file: File) {
  const validExtensions = [".xlsx", ".xls", ".csv", ".json"];
  const extension = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();

  if (!validExtensions.includes(extension)) {
    ElMessage.error(t('import.unsupportedFormat'));
    return false;
  }

  uploadedFile.value = file;
  isParsing.value = true;

  try {
    parsedData.value = await parseFile(file);
    fieldMappings.value = autoMatchFields(
      parsedData.value.columns,
      availableFields.value,
    );
    // 自动匹配到关联字段的列：预加载目标表字段并默认选主字段
    fieldMappings.value.forEach((mapping) => {
      if (mapping.targetFieldId && mapping.targetFieldType === FieldType.LINK) {
        const linkedTableId = getLinkedTableId(mapping);
        if (linkedTableId) {
          void ensureTargetFields(linkedTableId).then((fields) => {
            if (!matchFieldIds.value[mapping.sourceColumn]) {
              const primary = fields.find((f) => f.is_primary);
              if (primary) matchFieldIds.value[mapping.sourceColumn] = primary.id;
            }
          });
        }
      }
    });
    ElMessage.success(t('import.parsedSuccess', { count: parsedData.value.data.length }));
    if (parsedData.value.data.length > 0) {
      currentStep.value = 2;
    }
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : t('import.parseFailed'));
    uploadedFile.value = null;
    parsedData.value = null;
  } finally {
    isParsing.value = false;
  }
  return false;
}

function handleMappingChange(index: number, fieldId: string | null) {
  const mapping = fieldMappings.value[index];
  if (fieldId) {
    const field = availableFields.value.find((f) => f.id === fieldId);
    mapping.targetFieldId = fieldId;
    mapping.targetFieldName = field?.name ?? null;
    mapping.targetFieldType = (field?.type as any) ?? null;
    // 关联字段：加载目标表字段并默认选主字段作为匹配字段
    if (mapping.targetFieldType === FieldType.LINK) {
      const linkedTableId = getLinkedTableId(mapping);
      if (linkedTableId) {
        void ensureTargetFields(linkedTableId).then((fields) => {
          if (!matchFieldIds.value[mapping.sourceColumn]) {
            const primary = fields.find((f) => f.is_primary);
            if (primary) matchFieldIds.value[mapping.sourceColumn] = primary.id;
          }
        });
      }
    }
  } else {
    mapping.targetFieldId = null;
    mapping.targetFieldName = null;
    mapping.targetFieldType = null;
    delete matchFieldIds.value[mapping.sourceColumn];
  }
}

function isLinkMapping(mapping: FieldMapping): boolean {
  return mapping.targetFieldType === FieldType.LINK;
}

function getLinkedTableId(mapping: FieldMapping): string {
  if (!mapping.targetFieldId) return "";
  const field = availableFields.value.find((f) => f.id === mapping.targetFieldId);
  const config = field?.config as Record<string, unknown> | undefined;
  return (config?.linkedTableId as string) || "";
}

async function ensureTargetFields(linkedTableId: string): Promise<TargetFieldOption[]> {
  const cached = targetFieldsCache.value[linkedTableId];
  if (cached) return cached;
  isLoadingTargetFields.value[linkedTableId] = true;
  try {
    const fields = await getFields(linkedTableId);
    const list: TargetFieldOption[] = fields
      .filter((f) => !f.is_system)
      .map((f) => ({
        id: f.id,
        name: f.name,
        type: f.type,
        is_primary: !!f.is_primary,
      }));
    targetFieldsCache.value[linkedTableId] = list;
    return list;
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : t('import.loadTargetFieldsFailed'));
    return [];
  } finally {
    isLoadingTargetFields.value[linkedTableId] = false;
  }
}

function formatDateValue(value: string | number, includeTime: boolean): string {
  if (!value || value === "") return "-";
  let date: Date;
  if (typeof value === "number") {
    date = new Date(value);
  } else {
    date = new Date(value);
  }
  if (isNaN(date.getTime())) return "-";
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");
  if (!includeTime) return `${year}-${month}-${day}`;
  const hours = String(date.getHours()).padStart(2, "0");
  const minutes = String(date.getMinutes()).padStart(2, "0");
  const seconds = String(date.getSeconds()).padStart(2, "0");
  return `${year}-${month}-${day} ${hours}:${minutes}:${seconds}`;
}

function generateDisplayData(
  convertedRow: Record<string, any>,
  fields: FieldEntity[]
): Record<string, string> {
  const displayData: Record<string, string> = {};
  fields.forEach((field) => {
    const value = convertedRow[field.id];
    if (value === null || value === undefined) {
      displayData[field.id] = "-";
      return;
    }
    if (field.type === "single_select") {
      const options = getFieldOptions(field);
      const name = findOptionNameById(options, String(value));
      displayData[field.id] = name ?? String(value);
    } else if (field.type === "multi_select") {
      const options = getFieldOptions(field);
      if (Array.isArray(value)) {
        const names = value
          .map((v) => findOptionNameById(options, String(v)) ?? String(v))
          .filter(Boolean);
        displayData[field.id] = names.join(", ") || "-";
      } else {
        const name = findOptionNameById(options, String(value));
        displayData[field.id] = name ?? String(value);
      }
    } else if (field.type === "date") {
      displayData[field.id] = formatDateValue(value as string | number, false);
    } else if (field.type === "date_time") {
      displayData[field.id] = formatDateValue(value as string | number, true);
    } else {
      displayData[field.id] = String(value);
    }
  });
  return displayData;
}

const previewData = computed(() => {
  if (!parsedData.value) return [];
  return parsedData.value.data.slice(0, 5).map((row, rowIndex) => {
    const convertedRow = convertImportData(row, fieldMappings.value, availableFields.value);
    const validation = validateRow(convertedRow, availableFields.value);
    const displayData = generateDisplayData(convertedRow, availableFields.value);
    return {
      rowIndex: rowIndex + 1,
      rawData: row,
      convertedData: convertedRow,
      displayData,
      errors: validation.errors,
    };
  });
});

const mappedFields = computed(() => {
  return fieldMappings.value
    .filter((m) => m.targetFieldId)
    .map((m) => ({
      id: m.targetFieldId!,
      name: m.targetFieldName!,
      type: m.targetFieldType!,
    }));
});

function prepareImportData(): Record<string, CellValue>[] {
  if (!parsedData.value) return [];
  return parsedData.value.data.map((row) => {
    return convertImportData(row, fieldMappings.value, availableFields.value, memberNameToId.value);
  });
}

function validateAllRows(rows: Record<string, CellValue>[]): {
  validRows: Record<string, CellValue>[];
  invalidRows: Array<{ index: number; row: Record<string, CellValue>; errors: string[] }>;
  validIndexes: number[];
} {
  const validRows: Record<string, CellValue>[] = [];
  const invalidRows: Array<{ index: number; row: Record<string, CellValue>; errors: string[] }> = [];
  const validIndexes: number[] = [];

  rows.forEach((row, index) => {
    const validation = validateRow(row, availableFields.value);
    if (validation.valid) {
      validRows.push(row);
      validIndexes.push(index);
    } else {
      invalidRows.push({ index, row, errors: validation.errors });
    }
  });

  return { validRows, invalidRows, validIndexes };
}

function splitIntoChunks<T>(items: T[], size: number): T[][] {
  const chunks: T[][] = [];
  for (let i = 0; i < items.length; i += size) {
    chunks.push(items.slice(i, Math.min(i + size, items.length)));
  }
  return chunks;
}

/**
 * 成员字段姓名解析阶段：把 Excel 中成员列的姓名解析为用户 ID
 *
 * 收集所有成员映射列中的姓名（去重计数），通过用户搜索接口按姓名
 * 精确匹配构建 name→userId 映射，供 convertImportData 转换时使用；
 * 未匹配的姓名在结果步骤中报告，对应单元格留空。
 *
 * 注意：搜索不限定 Base 成员范围（与单元格内 MemberSelect 手动选择
 * 行为一致——成员字段允许选择系统内所有 ACTIVE 用户），限定 base_id
 * 时未加入该 Base 的用户会因 join base_members 过滤而匹配不到。
 */
async function ensureMemberNameMap() {
  memberNameToId.value = new Map();
  memberMatchSummaries.value = [];

  const memberMappings = fieldMappings.value.filter(
    (m) => m.targetFieldId && m.targetFieldType === FieldType.MEMBER,
  );
  if (memberMappings.length === 0 || !parsedData.value) return;

  memberMatchPhase.value = true;

  try {
    // 收集各成员列的姓名出现次数：sourceColumn -> (name -> count)
    const nameCounterByColumn = new Map<string, Map<string, number>>();
    for (const mapping of memberMappings) {
      const counter = new Map<string, number>();
      for (const row of parsedData.value.data) {
        for (const name of splitMemberNames(row[mapping.sourceColumn])) {
          counter.set(name, (counter.get(name) || 0) + 1);
        }
      }
      if (counter.size > 0) {
        nameCounterByColumn.set(mapping.sourceColumn, counter);
      }
    }

    if (nameCounterByColumn.size === 0) return;

    // 全量去重姓名，分批并发查询用户搜索接口
    const allNames = [...new Set([...nameCounterByColumn.values()].flatMap((c) => [...c.keys()]))];

    const resolveName = async (name: string): Promise<string | null> => {
      // searchUsers 为模糊匹配（name/email LIKE %query%），
      // 翻页直至找到姓名完全相等的用户；上限 10 页防呆
      let page = 1;
      while (page <= 10) {
        const res = await searchUsers({
          query: name,
          page,
          per_page: 100,
        });
        const exact = res.users.find((u) => u.name === name);
        if (exact) return exact.id;
        if (page * 100 >= res.total) return null;
        page += 1;
      }
      return null;
    };

    for (const chunk of splitIntoChunks(allNames, 5)) {
      const results = await Promise.all(
        chunk.map(async (name) => {
          try {
            return { name, userId: await resolveName(name) };
          } catch (error) {
            console.error("[ImportDialog] 解析成员姓名失败:", name, error);
            return { name, userId: null };
          }
        }),
      );
      for (const { name, userId } of results) {
        if (userId) {
          memberNameToId.value.set(name, userId);
        }
      }
    }

    // 按列汇总匹配结果
    for (const mapping of memberMappings) {
      const counter = nameCounterByColumn.get(mapping.sourceColumn);
      if (!counter) continue;

      const fieldLabel =
        availableFields.value.find((f) => f.id === mapping.targetFieldId)?.name ||
        mapping.sourceColumn;

      let matchedCount = 0;
      let unmatchedCount = 0;
      const unmatchedCounter = new Map<string, number>();
      for (const [name, count] of counter) {
        if (memberNameToId.value.has(name)) {
          matchedCount += count;
        } else {
          unmatchedCount += count;
          unmatchedCounter.set(name, count);
        }
      }

      memberMatchSummaries.value.push({
        fieldLabel,
        matchedCount,
        unmatchedCount,
        unmatchedNames: [...unmatchedCounter.entries()]
          .map(([name, count]) => ({ name, count }))
          .sort((a, b) => b.count - a.count)
          .slice(0, 10),
      });
    }
  } finally {
    memberMatchPhase.value = false;
  }
}

/**
 * 建立关联阶段：对映射到关联字段的列，按原始值批量匹配目标表记录
 *
 * @param rowIndexes 参与匹配的行在 parsedData.data 中的原始索引（与 recordIdByRow 行序对齐）
 * @param recordIdByRow 已创建记录 ID（与 rowIndexes 行序对齐，失败行为 null）
 */
async function executeLinkMatching(
  rowIndexes: number[],
  recordIdByRow: (string | null)[],
) {
  const linkMappings = fieldMappings.value.filter(
    (m) => m.targetFieldId && isLinkMapping(m),
  );
  if (linkMappings.length === 0 || !parsedData.value) return;

  linkMatchPhase.value = true;

  for (const mapping of linkMappings) {
    const matchFieldId = matchFieldIds.value[mapping.sourceColumn];
    if (!matchFieldId || !mapping.targetFieldId) continue;

    const fieldLabel =
      availableFields.value.find((f) => f.id === mapping.targetFieldId)?.name ||
      mapping.sourceColumn;

    const summary: LinkMatchSummary = {
      fieldLabel,
      matchedCount: 0,
      unmatchedCount: 0,
      unmatchedValues: [],
      duplicateTargetCount: 0,
    };

    // 组装 pairs：record_id 来自创建结果，value 取 Excel 原始单元格值
    const pairs: BatchMatchLinkPair[] = [];
    rowIndexes.forEach((rowIdx, k) => {
      const recId = recordIdByRow[k];
      if (!recId) return;
      const raw = parsedData.value?.data[rowIdx]?.[mapping.sourceColumn];
      if (raw === null || raw === undefined) return;
      const value = typeof raw === "string" ? raw.trim() : raw;
      if (value === "") return;
      pairs.push({ record_id: recId, value: value as string | number });
    });

    if (pairs.length > 0) {
      const chunks = splitIntoChunks(pairs, 1000);
      linkMatchProgress.value = { current: 0, total: chunks.length };
      const unmatchedCounter = new Map<string, number>();

      for (let i = 0; i < chunks.length; i++) {
        linkMatchProgress.value = { current: i, total: chunks.length };
        try {
          const r = await batchMatchRecordLinks(
            mapping.targetFieldId!,
            matchFieldId,
            chunks[i],
          );
          summary.matchedCount += r.matched_count;
          summary.unmatchedCount += r.unmatched_count;
          summary.duplicateTargetCount += r.duplicate_target_count || 0;
          (r.unmatched_values || []).forEach((uv) => {
            unmatchedCounter.set(uv.value, (unmatchedCounter.get(uv.value) || 0) + uv.count);
          });
        } catch (error) {
          // 单块失败不中断：计入未匹配，继续后续块
          summary.unmatchedCount += chunks[i].length;
          console.error("[ImportDialog] 批量匹配关联失败:", error);
        }
      }
      linkMatchProgress.value = { current: chunks.length, total: chunks.length };

      summary.unmatchedValues = [...unmatchedCounter.entries()]
        .map(([value, count]) => ({ value, count }))
        .sort((a, b) => b.count - a.count)
        .slice(0, 10);
    }

    linkMatchSummaries.value.push(summary);
  }

  linkMatchPhase.value = false;
}

async function handleImport() {
  if (!parsedData.value || !uploadedFile.value) return;

  const validMappings = fieldMappings.value.filter((m) => m.targetFieldId);
  if (validMappings.length === 0) {
    ElMessage.warning(t('import.atLeastOneMapping'));
    return;
  }

  isImporting.value = true;
  importResult.value = null;
  importProgress.value = null;
  isPaused.value = false;
  showErrorDetails.value = false;
  linkMatchPhase.value = false;
  linkMatchSummaries.value = [];

  try {
    // 成员字段姓名解析阶段：构建姓名→用户ID映射（Step 3 显示解析状态）
    await ensureMemberNameMap();
  } catch (error) {
    console.error("[ImportDialog] 成员姓名解析异常:", error);
  }

  const allRows = prepareImportData();
  const { validRows, invalidRows, validIndexes } = validateAllRows(allRows);

  if (validRows.length === 0) {
    ElMessage.error(t('import.allInvalid'));
    isImporting.value = false;
    return;
  }

  if (invalidRows.length > 0) {
    ElMessage.warning(t('import.skippedRows', { count: invalidRows.length }));
  }

  const controller = new BatchImportController(batchConfig.value);
  importController.value = controller;

  controller.onProgress((progress: BatchProgress) => {
    importProgress.value = { ...progress };
  });

  try {
    const result = await controller.execute(props.tableId, validRows);

    result.failedCount += invalidRows.length;

    importResult.value = result;

    if (result.status === "cancelled") {
      ElMessage.info(t('import.cancelled'));
    } else if (result.failedCount > 0 && result.successCount > 0) {
      ElMessage.warning(t('import.partialSuccess', { success: result.successCount, failed: result.failedCount }));
    } else if (result.failedCount === 0) {
      ElMessage.success(t('import.success', { count: result.successCount }));
    } else {
      ElMessage.error(t('import.failed'));
    }

    // 建立关联阶段：仅对已成功创建的行
    if (result.status !== "cancelled" && result.status !== "error") {
      await executeLinkMatching(validIndexes, result.recordIdByRow);
    }

    currentStep.value = 4;
    if (result.successCount > 0) {
      emit("imported");
    }
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : t('import.fatalError'));
    importResult.value = {
      successCount: 0,
      failedCount: allRows.length,
      errors: [
        {
          batchIndex: -1,
          rowRange: { start: 1, end: allRows.length },
          message: error instanceof Error ? error.message : t('common.unknownError'),
          retryCount: 0,
        },
      ],
      totalTime: 0,
      status: "error",
      recordIdByRow: [],
    };
    currentStep.value = 4;
  } finally {
    isImporting.value = false;
    importController.value = null;
  }
}

function handleCancel() {
  if (importController.value) {
    importController.value.cancel();
  }
}

function handlePause() {
  if (importController.value) {
    importController.value.pause();
    isPaused.value = true;
  }
}

function handleResume() {
  if (importController.value) {
    importController.value.resume();
    isPaused.value = false;
  }
}

function handleRetryFailed() {
  if (!importResult.value || importResult.value.errors.length === 0) return;

  const failedRecords: Record<string, unknown>[] = [];
  const failedIndexes: number[] = [];
  if (parsedData.value) {
    const allRows = prepareImportData();
    importResult.value.errors.forEach((err) => {
      for (let i = err.rowRange.start - 1; i < err.rowRange.end && i < allRows.length; i++) {
        failedRecords.push(allRows[i]);
        failedIndexes.push(i);
      }
    });
  }

  if (failedRecords.length === 0) {
    ElMessage.info(t('import.noRetry'));
    return;
  }

  isImporting.value = true;
  importResult.value = null;
  importProgress.value = null;
  isPaused.value = false;
  linkMatchPhase.value = false;
  linkMatchSummaries.value = [];

  const controller = new BatchImportController(batchConfig.value);
  importController.value = controller;

  controller.onProgress((progress: BatchProgress) => {
    importProgress.value = { ...progress };
  });

  controller
    .execute(props.tableId, failedRecords as Record<string, CellValue>[])
    .then(async (result) => {
      importResult.value = result;
      if (result.status === "cancelled") {
        ElMessage.info(t('import.retryCancelled'));
      } else if (result.successCount > 0) {
        ElMessage.success(t('import.retrySuccess', { count: result.successCount }));
        if (result.status !== "error") {
          await executeLinkMatching(failedIndexes, result.recordIdByRow);
        }
        emit("imported");
      }
      currentStep.value = 4;
    })
    .catch((error) => {
      ElMessage.error(error instanceof Error ? error.message : t('import.retryFailed'));
    })
    .finally(() => {
      isImporting.value = false;
      importController.value = null;
    });
}

function prevStep() {
  if (currentStep.value > 1) {
    currentStep.value--;
  }
}

function nextStep() {
  if (currentStep.value === 1) {
    if (!parsedData.value) {
      ElMessage.warning(t('import.pleaseUpload'));
      return;
    }
  } else if (currentStep.value === 2) {
    const validMappings = fieldMappings.value.filter((m) => m.targetFieldId);
    if (validMappings.length === 0) {
      ElMessage.warning(t('import.atLeastOneMapping'));
      return;
    }
    // 关联字段映射必须选择匹配字段
    const linkWithoutMatch = fieldMappings.value.find(
      (m) => m.targetFieldId && isLinkMapping(m) && !matchFieldIds.value[m.sourceColumn],
    );
    if (linkWithoutMatch) {
      ElMessage.warning(
        t('import.selectMatchFieldRequired', { column: linkWithoutMatch.sourceColumn }),
      );
      return;
    }
  } else if (currentStep.value === 3) {
    handleImport();
    return;
  }
  if (currentStep.value < totalSteps) {
    currentStep.value++;
  }
}

function handleClose() {
  if (isImporting.value && importController.value) {
    importController.value.cancel();
  }
  emit("update:visible", false);
  resetState();
}

function resetState() {
  currentStep.value = 1;
  uploadedFile.value = null;
  parsedData.value = null;
  fieldMappings.value = [];
  isImporting.value = false;
  importProgress.value = null;
  importResult.value = null;
  isPaused.value = false;
  showErrorDetails.value = false;
  failedBatchInputs.value = {};
  matchFieldIds.value = {};
  targetFieldsCache.value = {};
  isLoadingTargetFields.value = {};
  linkMatchPhase.value = false;
  linkMatchProgress.value = { current: 0, total: 0 };
  linkMatchSummaries.value = [];
  memberNameToId.value = new Map();
  memberMatchPhase.value = false;
  memberMatchSummaries.value = [];
}

function handleReimport() {
  resetState();
}

function downloadErrorLog() {
  if (!importResult.value || importResult.value.errors.length === 0) return;

  const lines: string[] = [t('import.errorLogTitle')];
  importResult.value.errors.forEach((err) => {
    lines.push(`${t('import.batch', { n: err.batchIndex + 1 })} (${t('import.rowRange', { start: err.rowRange.start, end: err.rowRange.end })}):`);
    lines.push(`  ${err.message}`);
    if (err.retryCount > 0) lines.push(`  ${t('import.retryTimes', { n: err.retryCount })}`);
    lines.push("");
  });

  const content = lines.join("\n");
  const blob = new Blob([content], { type: "text/plain" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = t('import.errorLogFilename', { date: new Date().toISOString().slice(0, 10) });
  link.click();
  URL.revokeObjectURL(link.href);
}

function downloadImportReport() {
  if (!importResult.value) return;

  const statusText = importResult.value.status === "completed" ? t('import.reportStatusCompleted') : importResult.value.status === "cancelled" ? t('import.reportStatusCancelled') : t('import.reportStatusError');
  const report = [
    t('import.reportTitle'),
    t('import.reportImportTime', { time: new Date().toLocaleString() }),
    t('import.reportTotal', { count: importResult.value.successCount + importResult.value.failedCount }),
    t('import.reportSuccess', { count: importResult.value.successCount }),
    t('import.reportFailed', { count: importResult.value.failedCount }),
    t('import.reportElapsed', { time: formatDuration(importResult.value.totalTime) }),
    t('import.reportStatus', { status: statusText }),
    "",
  ];

  if (importResult.value.errors.length > 0) {
    report.push(t('import.reportErrorDetail'));
    importResult.value.errors.forEach((err) => {
      report.push(`${t('import.batch', { n: err.batchIndex + 1 })} (${t('import.rowRange', { start: err.rowRange.start, end: err.rowRange.end })}): ${err.message}`);
    });
  }

  const content = report.join("\n");
  const blob = new Blob([content], { type: "text/plain" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = t('import.reportFilename', { date: new Date().toISOString().slice(0, 10) });
  link.click();
  URL.revokeObjectURL(link.href);
}

watch(
  () => props.visible,
  (visible) => {
    if (visible) resetState();
  },
);

function downloadTemplate(format: "excel" | "csv" | "json") {
  if (!props.fields.length) return;
  const tableName = t('import.tableName');
  exportTemplate(props.fields, tableName, format);
  ElMessage.success(t('import.templateDownloaded'));
}
</script>

<template>
  <el-dialog
    :model-value="visible"
    @update:model-value="handleClose"
    :title="t('import.title')"
    width="820px"
    :close-on-click-modal="false"
    :close-on-press-escape="!isImporting"
    class="import-dialog">
    <el-steps :active="currentStep" finish-status="success" class="import-steps">
      <el-step :title="t('import.stepSelectFile')" />
      <el-step :title="t('import.stepFieldMapping')" />
      <el-step :title="t('import.stepPreview')" />
      <el-step :title="t('import.stepDone')" />
    </el-steps>

    <!-- 步骤 1: 选择文件 -->
    <div v-if="currentStep === 1" class="step-content">
      <el-upload
        drag
        :auto-upload="false"
        :on-change="(file: any) => handleFileChange(file.raw)"
        :show-file-list="false"
        accept=".xlsx,.xls,.csv,.json"
        class="upload-area">
        <el-icon class="upload-icon"><Upload /></el-icon>
        <div class="upload-text">
          <p>{{ t('import.dragOrClick') }}</p>
          <p class="upload-hint">{{ t('import.supportedFormats') }}</p>
        </div>
      </el-upload>

      <div v-if="parsedData" class="file-info">
        <el-alert
          :title="t('import.selectedFile', { name: uploadedFile?.name })"
          type="success"
          :closable="false"
          show-icon>
          <template #default>
            <p>{{ t('import.fileInfo', { rows: parsedData.data.length, cols: parsedData.columns.length }) }}</p>
          </template>
        </el-alert>
      </div>

      <div v-if="isParsing" class="parsing-status">
        <el-loading :visible="true" :text="t('import.parsing')" />
      </div>

      <div class="template-download">
        <p>{{ t('import.noTemplate') }}</p>
        <el-dropdown>
          <el-button link type="primary">
            {{ t('import.downloadTemplate') }}
            <el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="downloadTemplate('excel')">{{ t('import.templateExcel') }}</el-dropdown-item>
              <el-dropdown-item @click="downloadTemplate('csv')">{{ t('import.templateCsv') }}</el-dropdown-item>
              <el-dropdown-item @click="downloadTemplate('json')">{{ t('import.templateJson') }}</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>

    <!-- 步骤 2: 字段映射 -->
    <div v-if="currentStep === 2" class="step-content">
      <div class="mapping-section">
        <p class="mapping-hint">
          <span style="font-weight: bolder;">{{ t('import.mappingConfig') }}&nbsp;</span>
          {{ t('import.mappingHint') }}
        </p>
        <el-table :data="fieldMappings" border class="mapping-table">
          <el-table-column prop="sourceColumn" :label="t('import.sourceColumn')" width="200" />
          <el-table-column :label="t('import.mappingField')" min-width="260">
            <template #default="{ row, $index }">
              <el-select
                :model-value="row.targetFieldId"
                :placeholder="t('import.selectFieldOptional')"
                clearable
                style="width: 100%"
                @change="(val) => handleMappingChange($index, val as string | null)">
                <el-option
                  v-for="field in availableFields"
                  :key="field.id"
                  :label="`${field.name} (${getFieldTypeLabel(field.type)})`"
                  :value="field.id" />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column :label="t('import.matchField')" min-width="220">
            <template #default="{ row, $index }">
              <template v-if="row.targetFieldId && isLinkMapping(fieldMappings[$index])">
                <el-select
                  v-model="matchFieldIds[row.sourceColumn]"
                  :placeholder="t('import.selectMatchField')"
                  :loading="isLoadingTargetFields[getLinkedTableId(fieldMappings[$index])]"
                  size="small"
                  style="width: 100%">
                  <el-option
                    v-for="tf in targetFieldsCache[getLinkedTableId(fieldMappings[$index])] || []"
                    :key="tf.id"
                    :label="`${tf.name}${tf.is_primary ? ` (${t('import.primaryField')})` : ''}`"
                    :value="tf.id" />
                </el-select>
                <div class="link-match-hint">{{ t('import.linkMatchHint') }}</div>
              </template>
              <span v-else class="unmatched-badge">-</span>
            </template>
          </el-table-column>
          <el-table-column :label="t('import.preview')" width="150">
            <template #default="{ row }">
              <span v-if="row.targetFieldName" class="mapped-badge">
                <el-icon><Check /></el-icon>
                {{ row.targetFieldName }}
              </span>
              <span v-else class="unmapped-badge">{{ t('import.unmapped') }}</span>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- 步骤 3: 数据预览 / 导入进度 -->
    <div v-if="currentStep === 3" class="step-content">
      <div v-if="!isImporting" class="preview-section">
        <p class="preview-hint">
          <span style="font-weight: bold;">{{ t('import.previewTitle') }}</span>
          {{ t('import.previewHint') }}
        </p>
        <div class="preview-table-wrapper">
          <el-table :data="previewData" border size="small" height="300" class="preview-table">
            <el-table-column type="index" :label="t('import.rowNumber')" width="30" fixed />
            <el-table-column
              v-for="field in mappedFields"
              :key="field.id"
              :prop="`displayData.${field.id}`"
              :label="`${field.name} (${getFieldTypeLabel(field.type)})`"
              show-overflow-tooltip>
              <template #default="{ row }">
                <span :class="{ 'error-cell': row.errors.length > 0 }">
                  {{ row.displayData[field.id] ?? "-" }}
                </span>
              </template>
            </el-table-column>
            <el-table-column :label="t('import.validationResult')" width="100" fixed="right">
              <template #default="{ row }">
                <el-tag v-if="row.errors.length === 0" type="success" size="small">{{ t('import.passed') }}</el-tag>
                <el-tooltip v-else :content="row.errors.join('\n')" placement="top">
                  <el-tag type="danger" size="small">{{ t('import.error') }}</el-tag>
                </el-tooltip>
              </template>
            </el-table-column>
          </el-table>
        </div>
        <p v-if="parsedData" class="total-records-hint">
          {{ t('import.totalRecordsHint', { count: parsedData.data.length, batch: batchConfig.batchSize }) }}
        </p>
      </div>

      <!-- 导入进度展示 -->
      <div v-else class="importing-section">
        <div class="progress-header">
          <h3>{{ memberMatchPhase ? t('import.memberMatchingTitle') : (linkMatchPhase ? t('import.linkMatchingTitle') : t('import.importingData')) }}</h3>
          <span class="progress-status-badge" :class="isPaused && !memberMatchPhase && !linkMatchPhase ? 'paused' : 'running'">
            {{ memberMatchPhase
              ? t('import.memberMatchingPhase')
              : (linkMatchPhase
                ? t('import.linkMatchingPhase', { current: linkMatchProgress.current, total: linkMatchProgress.total })
                : (isPaused ? t('import.paused') : t('import.importing'))) }}
          </span>
        </div>

        <!-- 进度条 -->
        <div class="progress-bar-area">
          <el-progress
            :percentage="memberMatchPhase ? 100 : (linkMatchPhase
              ? Math.round(linkMatchProgress.current / (linkMatchProgress.total || 1) * 100)
              : Math.round((importProgress?.completedBatches || 0) / (importProgress?.totalBatches || 1) * 100))"
            :stroke-width="24"
            :text-inside="true"
            striped
            :status="isPaused && !memberMatchPhase && !linkMatchPhase ? 'warning' : ''" />
        </div>

        <!-- 统计信息 -->
        <div class="progress-stats">
          <div class="stat-item">
            <span class="stat-label">{{ t('import.statBatchProgress') }}</span>
            <span class="stat-value">{{ importProgress?.completedBatches || 0 }} / {{ importProgress?.totalBatches || 0 }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">{{ t('import.statSuccess') }}</span>
            <span class="stat-value success">{{ importProgress?.successCount || 0 }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">{{ t('import.statFailed') }}</span>
            <span class="stat-value danger">{{ importProgress?.failedCount || 0 }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">{{ t('import.statElapsed') }}</span>
            <span class="stat-value">{{ formatDuration(importProgress?.elapsedTime || 0) }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">{{ t('import.statEta') }}</span>
            <span class="stat-value">{{ importProgress && importProgress.estimatedTimeRemaining > 0 ? formatDuration(importProgress.estimatedTimeRemaining) : t('import.calculating') }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">{{ t('import.statAvgBatch') }}</span>
            <span class="stat-value">{{ importProgress?.averageBatchTime ? `${importProgress.averageBatchTime.toFixed(0)}ms` : "-" }}</span>
          </div>
        </div>

        <!-- 操作按钮 -->
        <div class="progress-actions">
          <el-button
            v-if="!isPaused"
            type="warning"
            :icon="VideoPause"
            @click="handlePause">
            {{ t('import.pause') }}
          </el-button>
          <el-button
            v-else
            type="success"
            :icon="VideoPlay"
            @click="handleResume">
            {{ t('import.resume') }}
          </el-button>
          <el-button
            type="danger"
            :icon="Close"
            @click="handleCancel">
            {{ t('import.cancelImport') }}
          </el-button>
        </div>
      </div>
    </div>

    <!-- 步骤 4: 导入完成 -->
    <div v-if="currentStep === 4" class="step-content">
      <!-- 导入进度（导入中但步骤切换到4的场景） -->
      <div v-if="isImporting" class="importing-section">
        <div class="progress-header">
          <h3>{{ t('import.importingData') }}</h3>
          <span class="progress-status-badge running">{{ t('import.importing') }}</span>
        </div>
        <el-progress
          :percentage="Math.round((importProgress?.completedBatches || 0) / (importProgress?.totalBatches || 1) * 100)"
          :stroke-width="24"
          :text-inside="true"
          striped />
        <div class="progress-stats">
          <div class="stat-item">
            <span class="stat-label">{{ t('import.statSuccess') }}</span>
            <span class="stat-value success">{{ importProgress?.successCount || 0 }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">{{ t('import.statFailed') }}</span>
            <span class="stat-value danger">{{ importProgress?.failedCount || 0 }}</span>
          </div>
        </div>
      </div>

      <!-- 导入结果 -->
      <div v-else-if="importResult" class="result-section">
        <el-result
          :icon="importResult.failedCount === 0 ? 'success' : importResult.successCount === 0 ? 'error' : 'warning'"
          :title="importResult.failedCount === 0 ? t('import.importSuccess') : importResult.successCount === 0 ? t('import.importFailed') : t('import.importPartial')">
          <template #sub-title>
            <div class="result-stats">
              <div class="result-stat-grid">
                <div class="result-stat-item">
                  <span class="result-stat-label">{{ t('import.statTotal') }}</span>
                  <span class="result-stat-value">{{ importResult.successCount + importResult.failedCount }}</span>
                </div>
                <div class="result-stat-item">
                  <span class="result-stat-label">{{ t('import.reportSuccess', { count: importResult.successCount }) }}</span>
                  <span class="result-stat-value success">{{ importResult.successCount }}</span>
                </div>
                <div class="result-stat-item">
                  <span class="result-stat-label">{{ t('import.reportFailed', { count: importResult.failedCount }) }}</span>
                  <span class="result-stat-value danger">{{ importResult.failedCount }}</span>
                </div>
                <div class="result-stat-item">
                  <span class="result-stat-label">{{ t('import.statTime') }}</span>
                  <span class="result-stat-value">{{ formatDuration(importResult.totalTime) }}</span>
                </div>
              </div>
            </div>
          </template>

          <!-- 成员匹配结果 -->
          <div v-if="memberMatchSummaries.length > 0" class="link-match-section">
            <h4 class="link-match-title">{{ t('import.memberMatchResultTitle') }}</h4>
            <div v-for="(s, i) in memberMatchSummaries" :key="i" class="link-match-item">
              <div class="link-match-summary">
                <span class="field-name">{{ s.fieldLabel }}</span>
                <el-tag type="success" size="small">
                  {{ t('import.memberMatched', { count: s.matchedCount }) }}
                </el-tag>
                <el-tag v-if="s.unmatchedCount > 0" type="danger" size="small">
                  {{ t('import.memberUnmatched', { count: s.unmatchedCount }) }}
                </el-tag>
              </div>
              <div v-if="s.unmatchedNames.length > 0" class="link-match-unmatched">
                <span class="label">{{ t('import.memberUnmatchedNames') }}</span>
                <el-tag
                  v-for="un in s.unmatchedNames"
                  :key="un.name"
                  size="small"
                  type="info"
                  class="unmatched-value-tag">
                  {{ un.name }} × {{ un.count }}
                </el-tag>
              </div>
            </div>
          </div>

          <!-- 关联匹配结果 -->
          <div v-if="linkMatchSummaries.length > 0" class="link-match-section">
            <h4 class="link-match-title">{{ t('import.linkMatchResultTitle') }}</h4>
            <div v-for="(s, i) in linkMatchSummaries" :key="i" class="link-match-item">
              <div class="link-match-summary">
                <span class="field-name">{{ s.fieldLabel }}</span>
                <el-tag type="success" size="small">
                  {{ t('import.linkMatched', { count: s.matchedCount }) }}
                </el-tag>
                <el-tag v-if="s.unmatchedCount > 0" type="danger" size="small">
                  {{ t('import.linkUnmatched', { count: s.unmatchedCount }) }}
                </el-tag>
                <el-tag v-if="s.duplicateTargetCount > 0" type="warning" size="small">
                  {{ t('import.linkDuplicateTarget', { count: s.duplicateTargetCount }) }}
                </el-tag>
              </div>
              <div v-if="s.unmatchedValues.length > 0" class="link-match-unmatched">
                <span class="label">{{ t('import.linkUnmatchedValues') }}</span>
                <el-tag
                  v-for="uv in s.unmatchedValues"
                  :key="uv.value"
                  size="small"
                  type="info"
                  class="unmatched-value-tag">
                  {{ uv.value }} × {{ uv.count }}
                </el-tag>
              </div>
            </div>
          </div>

          <template #extra>
            <!-- 失败详情 -->
            <div v-if="importResult.errors.length > 0" class="error-detail-section">
              <el-button
                link
                type="primary"
                @click="showErrorDetails = !showErrorDetails">
                {{ showErrorDetails ? t('import.toggleErrorDetailCollapse') : t('import.toggleErrorDetail', { count: importResult.errors.length }) }}
              </el-button>

              <div v-if="showErrorDetails" class="error-detail-list">
                <div
                  v-for="(err, index) in importResult.errors"
                  :key="index"
                  class="error-detail-item">
                  <div class="error-header">
                    <el-tag type="danger" size="small">{{ t('import.batch', { n: err.batchIndex + 1 }) }}</el-tag>
                    <span class="error-range">{{ t('import.rowRange', { start: err.rowRange.start, end: err.rowRange.end }) }}</span>
                    <span v-if="err.retryCount > 0" class="error-retry">{{ t('import.retryTimes', { n: err.retryCount }) }}</span>
                  </div>
                  <p class="error-message">{{ err.message }}</p>
                </div>
              </div>
            </div>

            <div class="result-actions">
              <el-button :icon="Download" @click="downloadImportReport">{{ t('import.downloadReport') }}</el-button>
              <el-button
                v-if="importResult.errors.length > 0"
                :icon="Download"
                @click="downloadErrorLog">
                {{ t('import.downloadErrorLog') }}
              </el-button>
              <el-button v-if="importResult.errors.length > 0" :icon="Refresh" @click="handleRetryFailed">
                {{ t('import.retryFailedBtn') }}
              </el-button>
              <el-button @click="handleClose">{{ t('common.close') }}</el-button>
              <el-button type="primary" @click="handleReimport">{{ t('import.reimport') }}</el-button>
            </div>
          </template>
        </el-result>
      </div>
    </div>

    <!-- 底部按钮 -->
    <template #footer>
      <div class="dialog-footer">
        <template v-if="!isImporting">
          <el-button v-if="currentStep > 1 && currentStep < 4" @click="prevStep">
            <el-icon><ArrowLeft /></el-icon> {{ t('import.prevStep') }}
          </el-button>
          <el-button
            v-if="currentStep < 2"
            type="primary"
            @click="nextStep"
            :disabled="!parsedData">
            {{ t('import.nextStep') }} <el-icon><ArrowRight /></el-icon>
          </el-button>
          <el-button
            v-if="currentStep === 2"
            type="primary"
            @click="nextStep"
            :disabled="fieldMappings.filter((m) => m.targetFieldId).length === 0">
            {{ t('import.nextStep') }} <el-icon><ArrowRight /></el-icon>
          </el-button>
          <el-button
            v-if="currentStep === 3"
            type="primary"
            @click="nextStep"
            :disabled="!parsedData || parsedData.data.length === 0">
            {{ t('import.startImport', { count: parsedData?.data.length || 0 }) }}
          </el-button>
        </template>
        <template v-else>
          <el-button disabled>{{ t('import.importingDontClose') }}</el-button>
        </template>
      </div>
    </template>
  </el-dialog>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;

.import-dialog {
  :deep(.el-dialog__body) {
    padding-top: 10px;
  }
}

.import-steps {
  margin-bottom: 30px;
}

.step-content {
  min-height: 350px;
}

.upload-area {
  :deep(.el-upload) {
    width: 100%;
  }
  :deep(.el-upload-dragger) {
    width: 100%;
    height: 200px;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
  }
}

.upload-icon {
  font-size: 48px;
  color: $text-secondary;
  margin-bottom: 16px;
}

.upload-text {
  text-align: center;
  p {
    margin: 0;
    color: $text-primary;
    font-size: $font-size-base;
    em {
      color: $primary-color;
      font-style: normal;
    }
  }
  .upload-hint {
    margin-top: 8px;
    color: $text-secondary;
    font-size: $font-size-sm;
  }
}

.file-info {
  margin-top: 20px;
}

.parsing-status {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

.mapping-section {
  margin-bottom: 30px;
  h4 {
    margin: 0 0 8px;
    font-size: $font-size-base;
    color: $text-primary;
  }
  .mapping-hint {
    margin: 0 0 16px;
    color: $text-secondary;
    font-size: $font-size-sm;
  }
}

.mapping-table {
  :deep(.el-table__cell) {
    padding: 8px 0;
  }
}

.mapped-badge {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: $success-color;
  font-size: $font-size-sm;
}

.unmapped-badge {
  color: $text-disabled;
  font-size: $font-size-sm;
}

.preview-section {
  h4 {
    margin: 0 0 8px;
    font-size: $font-size-base;
    color: $text-primary;
  }
  .preview-hint {
    margin: 0 0 16px;
    color: $text-secondary;
    font-size: $font-size-sm;
  }
}

.preview-table-wrapper {
  overflow: visible;
}

.preview-table {
  .error-cell {
    color: $error-color;
  }
}

.total-records-hint {
  margin-top: 12px;
  text-align: center;
  color: $text-secondary;
  font-size: $font-size-sm;
}

.importing-section {
  padding: 20px 0;

  .progress-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 24px;

    h3 {
      margin: 0;
      font-size: $font-size-lg;
      color: $text-primary;
    }
  }

  .progress-status-badge {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 4px 14px;
    border-radius: 12px;
    font-size: $font-size-sm;
    font-weight: 500;

    &.running {
      background: rgba($primary-color, 0.1);
      color: $primary-color;
    }

    &.paused {
      background: rgba($warning-color, 0.1);
      color: $warning-color;
    }
  }

  .progress-bar-area {
    margin-bottom: 24px;
  }

  .progress-stats {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
    margin-bottom: 24px;

    .stat-item {
      text-align: center;
      padding: 12px;
      background: $bg-color;
      border-radius: $border-radius-md;

      .stat-label {
        display: block;
        font-size: $font-size-xs;
        color: $text-secondary;
        margin-bottom: 4px;
      }

      .stat-value {
        font-size: $font-size-lg;
        font-weight: 600;
        color: $text-primary;

        &.success {
          color: $success-color;
        }

        &.danger {
          color: $error-color;
        }
      }
    }
  }

  .progress-actions {
    display: flex;
    justify-content: center;
    gap: 12px;
  }
}

.result-section {
  :deep(.el-result__extra) {
    width: 100%;
  }
}

.result-stats {
  margin-bottom: 20px;

  .result-stat-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 12px;
  }

  .result-stat-item {
    text-align: center;
    padding: 12px 8px;
    background: $bg-color;
    border-radius: $border-radius-md;

    .result-stat-label {
      display: block;
      font-size: $font-size-xs;
      color: $text-secondary;
      margin-bottom: 4px;
    }

    .result-stat-value {
      font-size: $font-size-lg;
      font-weight: 600;
      color: $text-primary;

      &.success {
        color: $success-color;
      }

      &.danger {
        color: $error-color;
      }
    }
  }
}

.error-detail-section {
  margin-bottom: 20px;
  text-align: center;
}

.error-detail-list {
  margin-top: 12px;
  text-align: left;
  background: $bg-color;
  border-radius: $border-radius-md;
  padding: 12px;
  max-height: 250px;
  overflow-y: auto;
}

.error-detail-item {
  padding: 10px 0;
  border-bottom: 1px solid $border-color;

  &:last-child {
    border-bottom: none;
  }

  .error-header {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 4px;

    .error-range {
      font-size: $font-size-sm;
      color: $text-secondary;
    }

    .error-retry {
      font-size: $font-size-xs;
      color: $warning-color;
    }
  }

  .error-message {
    margin: 4px 0 0;
    font-size: $font-size-sm;
    color: $error-color;
  }
}

.result-actions {
  display: flex;
  justify-content: center;
  gap: 12px;
  flex-wrap: wrap;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.template-download {
  margin-top: 24px;
  text-align: center;
  padding: 16px;
  background: $bg-color;
  border-radius: $border-radius-md;

  p {
    margin: 0 0 8px;
    color: $text-secondary;
    font-size: $font-size-sm;
  }
}

.link-match-hint {
  margin-top: 4px;
  font-size: $font-size-xs;
  color: $text-secondary;
  line-height: 1.4;
}

.link-match-section {
  margin-top: 20px;
  padding: 14px 16px;
  background: $bg-color;
  border-radius: $border-radius-md;
  text-align: left;

  .link-match-title {
    margin: 0 0 12px;
    font-size: $font-size-base;
    color: $text-primary;
  }

  .link-match-item {
    padding: 8px 0;
    border-bottom: 1px solid $border-color;

    &:last-child {
      border-bottom: none;
    }
  }

  .link-match-summary {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;

    .field-name {
      font-size: $font-size-sm;
      color: $text-primary;
      font-weight: 500;
    }
  }

  .link-match-unmatched {
    display: flex;
    align-items: center;
    gap: 6px;
    flex-wrap: wrap;
    margin-top: 8px;

    .label {
      font-size: $font-size-xs;
      color: $text-secondary;
      flex-shrink: 0;
    }

    .unmatched-value-tag {
      max-width: 200px;
      overflow: hidden;
      text-overflow: ellipsis;
    }
  }
}
</style>