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
  type ParsedFileData,
  type FieldMapping,
} from "@/utils/importExport";
import { getFieldTypeLabel, type CellValue } from "@/types/fields";
import { exportTemplate } from "@/utils/templateGenerator";
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

const availableFields = computed(() => {
  return props.fields.filter((f) => !f.isSystem);
});

onUnmounted(() => {
  if (importController.value) {
    importController.value.cancel();
  }
});

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms.toFixed(0)} 毫秒`;
  if (ms < 60000) return `${(ms / 1000).toFixed(1)} 秒`;
  const minutes = Math.floor(ms / 60000);
  const seconds = Math.floor((ms % 60000) / 1000);
  return `${minutes} 分 ${seconds} 秒`;
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
  } else {
    mapping.targetFieldId = null;
    mapping.targetFieldName = null;
    mapping.targetFieldType = null;
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
    return convertImportData(row, fieldMappings.value, availableFields.value);
  });
}

function validateAllRows(rows: Record<string, CellValue>[]): {
  validRows: Record<string, CellValue>[];
  invalidRows: Array<{ index: number; row: Record<string, CellValue>; errors: string[] }>;
} {
  const validRows: Record<string, CellValue>[] = [];
  const invalidRows: Array<{ index: number; row: Record<string, CellValue>; errors: string[] }> = [];

  rows.forEach((row, index) => {
    const validation = validateRow(row, availableFields.value);
    if (validation.valid) {
      validRows.push(row);
    } else {
      invalidRows.push({ index, row, errors: validation.errors });
    }
  });

  return { validRows, invalidRows };
}

async function handleImport() {
  if (!parsedData.value || !uploadedFile.value) return;

  const validMappings = fieldMappings.value.filter((m) => m.targetFieldId);
  if (validMappings.length === 0) {
    ElMessage.warning(t('import.atLeastOneMapping'));
    return;
  }

  const allRows = prepareImportData();
  const { validRows, invalidRows } = validateAllRows(allRows);

  if (validRows.length === 0) {
    ElMessage.error(t('import.allInvalid'));
    return;
  }

  if (invalidRows.length > 0) {
    ElMessage.warning(t('import.skippedRows', { count: invalidRows.length }));
  }

  isImporting.value = true;
  importResult.value = null;
  importProgress.value = null;
  isPaused.value = false;
  showErrorDetails.value = false;

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
          message: error instanceof Error ? error.message : "未知错误",
          retryCount: 0,
        },
      ],
      totalTime: 0,
      status: "error",
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
  if (parsedData.value) {
    const allRows = prepareImportData();
    importResult.value.errors.forEach((err) => {
      for (let i = err.rowRange.start - 1; i < err.rowRange.end && i < allRows.length; i++) {
        failedRecords.push(allRows[i]);
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

  const controller = new BatchImportController(batchConfig.value);
  importController.value = controller;

  controller.onProgress((progress: BatchProgress) => {
    importProgress.value = { ...progress };
  });

  controller
    .execute(props.tableId, failedRecords)
    .then((result) => {
      importResult.value = result;
      if (result.status === "cancelled") {
        ElMessage.info(t('import.retryCancelled'));
      } else if (result.successCount > 0) {
        ElMessage.success(t('import.retrySuccess', { count: result.successCount }));
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
          <el-table-column :label="t('import.mappingField')" min-width="300">
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
          <h3>{{ t('import.importingData') }}</h3>
          <span class="progress-status-badge" :class="isPaused ? 'paused' : 'running'">
            {{ isPaused ? t('import.paused') : t('import.importing') }}
          </span>
        </div>

        <!-- 进度条 -->
        <div class="progress-bar-area">
          <el-progress
            :percentage="Math.round((importProgress?.completedBatches || 0) / (importProgress?.totalBatches || 1) * 100)"
            :stroke-width="24"
            :text-inside="true"
            striped
            :status="isPaused ? 'warning' : ''" />
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
</style>