<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { ElMessage, ElLoading } from "element-plus";
import {
  Upload,
  ArrowRight,
  ArrowLeft,
  Check,
  ArrowDown,
} from "@element-plus/icons-vue";
import type { FieldEntity } from "@/db/schema";
import type { CellValue } from "@/types";
import {
  parseFile,
  autoMatchFields,
  convertImportData,
  validateRow,
  type ParsedFileData,
  type FieldMapping,
} from "@/utils/importExport";
import { exportTemplate } from "@/utils/templateGenerator";
import { useTableStore } from "@/stores/tableStore";
import { generateId } from "@/utils/id";

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

const tableStore = useTableStore();

// 当前步骤
const currentStep = ref(1);
const totalSteps = 3;

// 文件相关
const uploadedFile = ref<File | null>(null);
const parsedData = ref<ParsedFileData | null>(null);
const isParsing = ref(false);

// 字段映射
const fieldMappings = ref<FieldMapping[]>([]);

// 导入进度
const isImporting = ref(false);
const importProgress = ref(0);
const importResult = ref<{
  success: number;
  failed: number;
  errors: string[];
} | null>(null);

// 计算可用的目标字段
const availableFields = computed(() => {
  return props.fields.filter((f) => !f.isSystem);
});

// 获取主键字段
const primaryField = computed(() => {
  return props.fields.find((f) => f.isPrimary);
});

// 获取字段类型标签
function getFieldTypeLabel(type: string): string {
  const typeMap: Record<string, string> = {
    text: "文本",
    number: "数字",
    date: "日期",
    singleSelect: "单选",
    multiSelect: "多选",
    checkbox: "复选框",
    attachment: "附件",
    member: "成员",
    rating: "评分",
    progress: "进度",
    phone: "电话",
    email: "邮箱",
    url: "链接",
    link: "关联",
    lookup: "查找",
    formula: "公式",
  };
  return typeMap[type] || type;
}

// 文件上传处理
async function handleFileChange(file: File) {
  const validExtensions = [".xlsx", ".xls", ".csv", ".json"];
  const extension = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();

  if (!validExtensions.includes(extension)) {
    ElMessage.error("不支持的文件格式，请上传 .xlsx, .xls, .csv 或 .json 文件");
    return false;
  }

  uploadedFile.value = file;
  isParsing.value = true;

  try {
    parsedData.value = await parseFile(file);

    // 自动匹配字段
    fieldMappings.value = autoMatchFields(
      parsedData.value.columns,
      availableFields.value,
    );

    ElMessage.success(
      `成功解析文件，共 ${parsedData.value.data.length} 行数据`,
    );

    // 自动进入下一步
    if (parsedData.value.data.length > 0) {
      currentStep.value = 2;
    }
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "文件解析失败");
    uploadedFile.value = null;
    parsedData.value = null;
  } finally {
    isParsing.value = false;
  }

  return false; // 阻止自动上传
}

// 处理字段映射变更
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

// 获取预览数据（前5行）
const previewData = computed(() => {
  if (!parsedData.value) return [];

  return parsedData.value.data.slice(0, 5).map((row, rowIndex) => {
    const convertedRow: Record<string, CellValue> = {};
    fieldMappings.value.forEach((mapping) => {
      if (mapping.targetFieldId) {
        convertedRow[mapping.targetFieldId] = row[mapping.sourceColumn];
      }
    });

    // 验证数据
    const validation = validateRow(convertedRow, availableFields.value);

    return {
      rowIndex: rowIndex + 1,
      rawData: row,
      convertedData: convertedRow,
      errors: validation.errors,
    };
  });
});

// 获取已映射的字段
const mappedFields = computed(() => {
  return fieldMappings.value
    .filter((m) => m.targetFieldId)
    .map((m) => ({
      id: m.targetFieldId!,
      name: m.targetFieldName!,
      type: m.targetFieldType!,
    }));
});

// 执行导入
async function handleImport() {
  if (!parsedData.value || !uploadedFile.value) return;

  const validMappings = fieldMappings.value.filter((m) => m.targetFieldId);
  if (validMappings.length === 0) {
    ElMessage.warning("请至少配置一个字段映射");
    return;
  }

  isImporting.value = true;
  importProgress.value = 0;

  const result = {
    success: 0,
    failed: 0,
    errors: [] as string[],
  };

  const totalRows = parsedData.value.data.length;
  const batchSize = 50; // 每批处理50条

  try {
    for (let i = 0; i < totalRows; i += batchSize) {
      const batch = parsedData.value.data.slice(i, i + batchSize);

      for (let j = 0; j < batch.length; j++) {
        const row = batch[j];
        const rowIndex = i + j + 1;

        try {
          // 转换数据
          const values = convertImportData(row, fieldMappings.value);

          // 自动填充主键值
          if (primaryField.value) {
            // 如果用户没有提供主键值，则自动生成
            if (!values[primaryField.value.id]) {
              values[primaryField.value.id] = generateId();
            }
          }

          // 验证数据
          const validation = validateRow(values, availableFields.value);
          if (!validation.valid) {
            result.failed++;
            result.errors.push(
              `第 ${rowIndex} 行: ${validation.errors.join(", ")}`,
            );
            continue;
          }

          // 创建记录
          await tableStore.createRecord({
            tableId: props.tableId,
            values,
          });

          result.success++;
        } catch (error) {
          result.failed++;
          result.errors.push(
            `第 ${rowIndex} 行: ${error instanceof Error ? error.message : "导入失败"}`,
          );
        }
      }

      // 更新进度
      importProgress.value = Math.round(((i + batch.length) / totalRows) * 100);
    }

    importResult.value = result;
    currentStep.value = 3;

    if (result.success > 0) {
      ElMessage.success(`成功导入 ${result.success} 条记录`);
      emit("imported");
    }

    if (result.failed > 0) {
      ElMessage.warning(`${result.failed} 条记录导入失败`);
    }
  } catch (error) {
    ElMessage.error("导入过程中发生错误");
  } finally {
    isImporting.value = false;
  }
}

// 上一步
function prevStep() {
  if (currentStep.value > 1) {
    currentStep.value--;
  }
}

// 下一步
function nextStep() {
  if (currentStep.value === 1) {
    if (!parsedData.value) {
      ElMessage.warning("请先上传文件");
      return;
    }
  } else if (currentStep.value === 2) {
    const validMappings = fieldMappings.value.filter((m) => m.targetFieldId);
    if (validMappings.length === 0) {
      ElMessage.warning("请至少配置一个字段映射");
      return;
    }
  }

  if (currentStep.value < totalSteps) {
    currentStep.value++;
  }
}

// 关闭对话框
function handleClose() {
  emit("update:visible", false);
  resetState();
}

// 重置状态
function resetState() {
  currentStep.value = 1;
  uploadedFile.value = null;
  parsedData.value = null;
  fieldMappings.value = [];
  isImporting.value = false;
  importProgress.value = 0;
  importResult.value = null;
}

// 重新导入
function handleReimport() {
  resetState();
}

// 下载错误日志
function downloadErrorLog() {
  if (!importResult.value || importResult.value.errors.length === 0) return;

  const content = importResult.value.errors.join("\n");
  const blob = new Blob([content], { type: "text/plain" });
  const link = document.createElement("a");
  link.href = URL.createObjectURL(blob);
  link.download = `导入错误日志_${new Date().toISOString().slice(0, 10)}.txt`;
  link.click();
  URL.revokeObjectURL(link.href);
}

// 监听对话框显示状态
watch(
  () => props.visible,
  (visible) => {
    if (visible) {
      resetState();
    }
  },
);

// 下载模板
function downloadTemplate(format: "excel" | "csv" | "json") {
  if (!props.fields.length) return;
  const tableName = "数据表";
  exportTemplate(props.fields, tableName, format);
  ElMessage.success("模板下载成功");
}
</script>

<template>
  <el-dialog
    :model-value="visible"
    @update:model-value="handleClose"
    title="数据导入"
    width="800px"
    :close-on-click-modal="false"
    class="import-dialog">
    <!-- 步骤条 -->
    <el-steps
      :active="currentStep"
      finish-status="success"
      class="import-steps">
      <el-step title="选择文件" />
      <el-step title="字段映射" />
      <el-step title="导入完成" />
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
          <p>拖拽文件到此处，或 <em>点击上传</em></p>
          <p class="upload-hint">支持 .xlsx, .xls, .csv, .json 格式</p>
        </div>
      </el-upload>

      <div v-if="parsedData" class="file-info">
        <el-alert
          :title="`已选择文件: ${uploadedFile?.name}`"
          type="success"
          :closable="false"
          show-icon>
          <template #default>
            <p>
              共 {{ parsedData.data.length }} 行数据，{{
                parsedData.columns.length
              }}
              列
            </p>
          </template>
        </el-alert>
      </div>

      <div v-if="isParsing" class="parsing-status">
        <el-loading :visible="true" text="正在解析文件..." />
      </div>

      <!-- 模板下载 -->
      <div class="template-download">
        <p>没有模板文件？</p>
        <el-dropdown>
          <el-button link type="primary">
            下载导入模板
            <el-icon class="el-icon--right"><arrow-down /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="downloadTemplate('excel')"
                >Excel 模板 (.xlsx)</el-dropdown-item
              >
              <el-dropdown-item @click="downloadTemplate('csv')"
                >CSV 模板 (.csv)</el-dropdown-item
              >
              <el-dropdown-item @click="downloadTemplate('json')"
                >JSON 模板 (.json)</el-dropdown-item
              >
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>

    <!-- 步骤 2: 字段映射 -->
    <div v-if="currentStep === 2" class="step-content">
      <div class="mapping-section">
        <h4>字段映射配置</h4>
        <p class="mapping-hint">
          将文件中的列映射到表格字段，未映射的列将被忽略
        </p>

        <el-table :data="fieldMappings" border class="mapping-table">
          <el-table-column prop="sourceColumn" label="文件列名" width="200" />
          <el-table-column label="映射到表格字段" min-width="300">
            <template #default="{ row, $index }">
              <el-select
                :model-value="row.targetFieldId"
                placeholder="选择字段（可选）"
                clearable
                style="width: 100%"
                @change="
                  (val) => handleMappingChange($index, val as string | null)
                ">
                <el-option
                  v-for="field in availableFields"
                  :key="field.id"
                  :label="`${field.name} (${getFieldTypeLabel(field.type)})`"
                  :value="field.id" />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="预览" width="150">
            <template #default="{ row }">
              <span v-if="row.targetFieldName" class="mapped-badge">
                <el-icon><Check /></el-icon>
                {{ row.targetFieldName }}
              </span>
              <span v-else class="unmapped-badge">未映射</span>
            </template>
          </el-table-column>
        </el-table>
      </div>

      <!-- 数据预览 -->
      <div v-if="previewData.length > 0" class="preview-section">
        <h4>数据预览（前 5 行）</h4>
        <div class="preview-table-wrapper">
          <el-table
            :data="previewData"
            border
            size="small"
            class="preview-table">
            <el-table-column type="index" label="行号" width="60" />
            <el-table-column
              v-for="field in mappedFields"
              :key="field.id"
              :prop="`convertedData.${field.id}`"
              :label="`${field.name} (${getFieldTypeLabel(field.type)})`">
              <template #default="{ row }">
                <span :class="{ 'error-cell': row.errors.length > 0 }">
                  {{ row.convertedData[field.id] ?? "-" }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="验证" width="100">
              <template #default="{ row }">
                <el-tag
                  v-if="row.errors.length === 0"
                  type="success"
                  size="small"
                  >通过</el-tag
                >
                <el-tooltip
                  v-else
                  :content="row.errors.join('\n')"
                  placement="top">
                  <el-tag type="danger" size="small">错误</el-tag>
                </el-tooltip>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>
    </div>

    <!-- 步骤 3: 导入完成 -->
    <div v-if="currentStep === 3" class="step-content">
      <div v-if="importResult" class="result-section">
        <el-result
          :icon="
            importResult.failed === 0
              ? 'success'
              : importResult.success === 0
                ? 'error'
                : 'warning'
          "
          :title="
            importResult.failed === 0
              ? '导入成功'
              : importResult.success === 0
                ? '导入失败'
                : '部分导入成功'
          ">
          <template #sub-title>
            <div class="result-stats">
              <p><strong>成功:</strong> {{ importResult.success }} 条</p>
              <p><strong>失败:</strong> {{ importResult.failed }} 条</p>
            </div>
          </template>

          <template #extra>
            <div v-if="importResult.errors.length > 0" class="error-list">
              <h4>错误详情（显示前 10 条）:</h4>
              <el-scrollbar height="150px">
                <ul>
                  <li
                    v-for="(error, index) in importResult.errors.slice(0, 10)"
                    :key="index">
                    {{ error }}
                  </li>
                </ul>
              </el-scrollbar>
              <el-button
                v-if="importResult.errors.length > 10"
                link
                type="primary"
                @click="downloadErrorLog">
                下载完整错误日志
              </el-button>
            </div>

            <div class="result-actions">
              <el-button @click="handleClose">关闭</el-button>
              <el-button type="primary" @click="handleReimport"
                >重新导入</el-button
              >
            </div>
          </template>
        </el-result>
      </div>

      <!-- 导入进度 -->
      <div v-else-if="isImporting" class="progress-section">
        <el-progress :percentage="importProgress" :stroke-width="20" striped />
        <p class="progress-text">正在导入数据，请勿关闭窗口...</p>
      </div>
    </div>

    <!-- 底部按钮 -->
    <template #footer>
      <div class="dialog-footer">
        <el-button v-if="currentStep > 1 && currentStep < 3" @click="prevStep">
          <el-icon><ArrowLeft /></el-icon>
          上一步
        </el-button>

        <el-button
          v-if="currentStep < 2"
          type="primary"
          @click="nextStep"
          :disabled="!parsedData">
          下一步
          <el-icon><ArrowRight /></el-icon>
        </el-button>

        <el-button
          v-if="currentStep === 2"
          type="primary"
          @click="handleImport"
          :loading="isImporting"
          :disabled="fieldMappings.filter((m) => m.targetFieldId).length === 0">
          开始导入
        </el-button>
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
  min-height: 300px;
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
    margin: 0 0 16px;
    font-size: $font-size-base;
    color: $text-primary;
  }
}

.preview-table-wrapper {
  max-height: 250px;
  overflow: auto;
}

.preview-table {
  .error-cell {
    color: $error-color;
  }
}

.result-section {
  :deep(.el-result__extra) {
    width: 100%;
  }
}

.result-stats {
  text-align: center;
  margin-bottom: 20px;

  p {
    margin: 4px 0;
  }
}

.error-list {
  background: $bg-color;
  border-radius: $border-radius-md;
  padding: 16px;
  margin-bottom: 20px;
  text-align: left;

  h4 {
    margin: 0 0 12px;
    font-size: $font-size-sm;
    color: $text-primary;
  }

  ul {
    margin: 0;
    padding-left: 20px;

    li {
      color: $error-color;
      font-size: $font-size-sm;
      margin-bottom: 4px;
    }
  }
}

.result-actions {
  display: flex;
  justify-content: center;
  gap: 12px;
}

.progress-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 200px;

  .progress-text {
    margin-top: 20px;
    color: $text-secondary;
  }
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
