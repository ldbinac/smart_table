<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { ElMessage } from "element-plus";
import {
  Upload,
  ArrowRight,
  ArrowLeft,
  Check,
  Document,
} from "@element-plus/icons-vue";
import { importExportApiService } from "@/services/api/importExportApiService";

interface ExcelColumn {
  name: string;
  source_column: string;
  suggested_type: string;
  confidence: number;
  sample_values: string[];
  is_primary_candidate: boolean;
}

interface FieldConfig {
  source_column: string;
  name: string;
  type: string;
  is_primary: boolean;
  included: boolean;
  sample_values: string[];
}

interface Props {
  visible: boolean;
  baseId: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  (e: "update:visible", value: boolean): void;
  (e: "created", tableId: string): void;
}>();

// 当前步骤
const currentStep = ref(1);
const totalSteps = 3;

// 文件相关
const uploadedFile = ref<File | null>(null);
const fileKey = ref("");
const originalFilename = ref("");
const isParsing = ref(false);

// 数据表配置
const tableName = ref("");
const tableDescription = ref("");

// 字段配置
const fieldConfigs = ref<FieldConfig[]>([]);
const importData = ref(true);

// 创建进度
const isCreating = ref(false);
const createProgress = ref(0);
const createResult = ref<{
  success: boolean;
  tableId?: string;
  tableName?: string;
  createdFieldsCount?: number;
  importedRows?: number;
  failedRows?: number;
  message?: string;
} | null>(null);

// Excel分析结果
const analysisResult = ref<{
  total_rows: number;
  total_columns: number;
  columns: ExcelColumn[];
  sheet_name: string;
} | null>(null);

// 字段类型选项
const fieldTypeOptions = [
  { value: "text", label: "文本" },
  { value: "rich_text", label: "长文本" },
  { value: "number", label: "数字" },
  { value: "date", label: "日期" },
  { value: "date_time", label: "日期时间" },
  { value: "email", label: "邮箱" },
  { value: "phone", label: "电话" },
  { value: "url", label: "链接" },
  { value: "checkbox", label: "复选框" },
  { value: "single_select", label: "单选" },
  { value: "multi_select", label: "多选" },
];

// 获取字段类型标签
function getFieldTypeLabel(type: string): string {
  const option = fieldTypeOptions.find((o) => o.value === type);
  return option?.label || type;
}

// 文件上传处理
async function handleFileChange(file: File) {
  const validExtensions = [".xlsx", ".xls"];
  const extension = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();

  if (!validExtensions.includes(extension)) {
    ElMessage.error("请上传Excel文件(.xlsx或.xls格式)");
    return false;
  }

  uploadedFile.value = file;
  isParsing.value = true;

  try {
    const result = await importExportApiService.analyzeExcelForTable(file);

    if (result.success && result.data) {
      analysisResult.value = result.data;
      fileKey.value = result.data.file_key;
      originalFilename.value = result.data.original_filename || file.name;

      // 初始化字段配置
      fieldConfigs.value = result.data.columns.map((col: ExcelColumn) => ({
        source_column: col.source_column,
        name: col.name,
        type: col.suggested_type,
        is_primary: col.is_primary_candidate,
        included: true,
        sample_values: col.sample_values,
      }));

      // 设置默认表名
      const baseName = file.name.replace(/\.xlsx?$/, "");
      tableName.value = baseName;

      ElMessage.success(
        `成功解析文件，共 ${result.data.total_rows} 行数据，${result.data.total_columns} 列`
      );

      // 自动进入下一步
      currentStep.value = 2;
    } else {
      ElMessage.error(result.message || "文件解析失败");
    }
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : "文件解析失败");
    uploadedFile.value = null;
    analysisResult.value = null;
  } finally {
    isParsing.value = false;
  }

  return false;
}

// 处理字段类型变更
function handleFieldTypeChange(index: number, newType: string) {
  fieldConfigs.value[index].type = newType;
}

// 处理主字段变更
function handlePrimaryChange(index: number, isPrimary: boolean) {
  if (isPrimary) {
    // 取消其他字段的主字段状态
    fieldConfigs.value.forEach((field, i) => {
      if (i !== index) {
        field.is_primary = false;
      }
    });
  }
  fieldConfigs.value[index].is_primary = isPrimary;
}

// 获取已启用的字段
const enabledFields = computed(() => {
  return fieldConfigs.value.filter((f) => f.included);
});

// 获取主字段
const primaryField = computed(() => {
  return fieldConfigs.value.find((f) => f.is_primary && f.included);
});

// 执行创建
async function handleCreate() {
  if (!tableName.value.trim()) {
    ElMessage.warning("请输入数据表名称");
    return;
  }

  const enabledFieldsList = enabledFields.value;
  if (enabledFieldsList.length === 0) {
    ElMessage.warning("请至少选择一个字段");
    return;
  }

  if (!primaryField.value) {
    ElMessage.warning("请设置一个主字段");
    return;
  }

  isCreating.value = true;
  createProgress.value = 0;

  try {
    const result = await importExportApiService.createTableFromExcel({
      base_id: props.baseId,
      table_name: tableName.value.trim(),
      description: tableDescription.value,
      file_key: fileKey.value,
      fields: enabledFieldsList.map((f) => ({
        source_column: f.source_column,
        name: f.name,
        type: f.type,
        is_primary: f.is_primary,
        included: f.included,
      })),
      import_data: importData.value,
    });

    if (result.success && result.data) {
      createResult.value = {
        success: true,
        tableId: result.data.table_id,
        tableName: result.data.table_name,
        createdFieldsCount: result.data.created_fields_count,
        importedRows: result.data.imported_rows,
        failedRows: result.data.failed_rows,
      };
      currentStep.value = 3;
      ElMessage.success("数据表创建成功");
      emit("created", result.data.table_id);
    } else {
      createResult.value = {
        success: false,
        message: result.message || "创建失败",
      };
      currentStep.value = 3;
      ElMessage.error(result.message || "创建失败");
    }
  } catch (error) {
    createResult.value = {
      success: false,
      message: error instanceof Error ? error.message : "创建失败",
    };
    currentStep.value = 3;
    ElMessage.error(error instanceof Error ? error.message : "创建失败");
  } finally {
    isCreating.value = false;
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
  if (currentStep.value === 2) {
    if (!tableName.value.trim()) {
      ElMessage.warning("请输入数据表名称");
      return;
    }
    if (enabledFields.value.length === 0) {
      ElMessage.warning("请至少选择一个字段");
      return;
    }
    if (!primaryField.value) {
      ElMessage.warning("请设置一个主字段");
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
  fileKey.value = "";
  originalFilename.value = "";
  analysisResult.value = null;
  fieldConfigs.value = [];
  tableName.value = "";
  tableDescription.value = "";
  importData.value = true;
  isCreating.value = false;
  createProgress.value = 0;
  createResult.value = null;
}

// 重新创建
function handleRecreate() {
  resetState();
}

// 监听对话框显示状态
watch(
  () => props.visible,
  (visible) => {
    if (visible) {
      resetState();
    }
  }
);
</script>

<template>
  <el-dialog
    :model-value="visible"
    @update:model-value="handleClose"
    title="Excel导入创建数据表"
    width="900px"
    :close-on-click-modal="false"
    class="excel-import-dialog"
  >
    <!-- 步骤条 -->
    <el-steps
      :active="currentStep"
      finish-status="success"
      class="import-steps"
    >
      <el-step title="选择文件" />
      <el-step title="配置字段" />
      <el-step title="创建完成" />
    </el-steps>

    <!-- 步骤 1: 选择文件 -->
    <div v-if="currentStep === 1" class="step-content">
      <el-upload
        drag
        :auto-upload="false"
        :on-change="(file: any) => handleFileChange(file.raw)"
        :show-file-list="false"
        accept=".xlsx,.xls"
        class="upload-area"
      >
        <el-icon class="upload-icon"><Upload /></el-icon>
        <div class="upload-text">
          <p>拖拽Excel文件到此处，或 <em>点击上传</em></p>
          <p class="upload-hint">支持 .xlsx, .xls 格式</p>
        </div>
      </el-upload>

      <div v-if="analysisResult" class="file-info">
        <el-alert
          :title="`已选择文件: ${originalFilename}`"
          type="success"
          :closable="false"
          show-icon
        >
          <template #default>
            <p>
              共 {{ analysisResult.total_rows }} 行数据，{{
                analysisResult.total_columns
              }}
              列
            </p>
          </template>
        </el-alert>
      </div>

      <div v-if="isParsing" class="parsing-status">
        <el-loading :visible="true" text="正在解析文件..." />
      </div>
    </div>

    <!-- 步骤 2: 配置字段 -->
    <div v-if="currentStep === 2" class="step-content">
      <!-- 数据表基本信息 -->
      <div class="table-info-section">
        <h4>数据表信息</h4>
        <el-form :model="{ tableName, tableDescription }" label-width="80px">
          <el-form-item label="名称" required>
            <el-input
              v-model="tableName"
              placeholder="请输入数据表名称"
              maxlength="50"
              show-word-limit
            />
          </el-form-item>
          <el-form-item label="描述">
            <el-input
              v-model="tableDescription"
              type="textarea"
              :rows="2"
              placeholder="请输入描述（可选）"
              maxlength="200"
              show-word-limit
            />
          </el-form-item>
        </el-form>
      </div>

      <!-- 字段配置 -->
      <div class="fields-section">
        <div class="fields-header">
          <h4>字段配置</h4>
          <el-checkbox v-model="importData">同时导入数据</el-checkbox>
        </div>
        <p class="fields-hint">
          系统将自动识别字段类型，您可以根据需要调整。请设置一个主字段（表格第一列）。
        </p>

        <el-table :data="fieldConfigs" border class="fields-table" size="small">
          <el-table-column type="index" width="50" />
          <el-table-column label="导入" width="60" align="center">
            <template #default="{ row }">
              <el-checkbox v-model="row.included" />
            </template>
          </el-table-column>
          <el-table-column label="主字段" width="80" align="center">
            <template #default="{ row, $index }">
              <el-radio
                v-model="row.is_primary"
                :label="true"
                :disabled="!row.included"
                @change="handlePrimaryChange($index, $event)"
              >
                <span></span>
              </el-radio>
            </template>
          </el-table-column>
          <el-table-column prop="source_column" label="Excel列名" width="150" />
          <el-table-column label="字段名称" width="150">
            <template #default="{ row }">
              <el-input
                v-model="row.name"
                size="small"
                :disabled="!row.included"
                maxlength="50"
              />
            </template>
          </el-table-column>
          <el-table-column label="字段类型" width="130">
            <template #default="{ row, $index }">
              <el-select
                v-model="row.type"
                size="small"
                :disabled="!row.included"
                @change="handleFieldTypeChange($index, $event)"
              >
                <el-option
                  v-for="opt in fieldTypeOptions"
                  :key="opt.value"
                  :label="opt.label"
                  :value="opt.value"
                />
              </el-select>
            </template>
          </el-table-column>
          <el-table-column label="示例数据" min-width="150">
            <template #default="{ row }">
              <span class="sample-values" :title="row.sample_values.join(', ')">
                {{ row.sample_values.join(", ") }}
              </span>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </div>

    <!-- 步骤 3: 创建完成 -->
    <div v-if="currentStep === 3" class="step-content">
      <div v-if="createResult" class="result-section">
        <el-result
          :icon="createResult.success ? 'success' : 'error'"
          :title="createResult.success ? '创建成功' : '创建失败'"
        >
          <template #sub-title>
            <div v-if="createResult.success" class="result-stats">
              <p><strong>数据表:</strong> {{ createResult.tableName }}</p>
              <p>
                <strong>创建字段:</strong>
                {{ createResult.createdFieldsCount }} 个
              </p>
              <p v-if="importData">
                <strong>导入数据:</strong> {{ createResult.importedRows }} 条
              </p>
              <p v-if="importData && createResult.failedRows">
                <strong>失败:</strong> {{ createResult.failedRows }} 条
              </p>
            </div>
            <div v-else class="error-message">
              <p>{{ createResult.message }}</p>
            </div>
          </template>

          <template #extra>
            <div class="result-actions">
              <el-button @click="handleClose">关闭</el-button>
              <el-button v-if="!createResult.success" type="primary" @click="handleRecreate"
                >重新创建</el-button
              >
            </div>
          </template>
        </el-result>
      </div>

      <!-- 创建进度 -->
      <div v-else-if="isCreating" class="progress-section">
        <el-progress :percentage="createProgress" :stroke-width="20" striped />
        <p class="progress-text">正在创建数据表，请勿关闭窗口...</p>
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
          v-if="currentStep === 1"
          type="primary"
          @click="nextStep"
          :disabled="!analysisResult"
        >
          下一步
          <el-icon><ArrowRight /></el-icon>
        </el-button>

        <el-button
          v-if="currentStep === 2"
          type="primary"
          @click="handleCreate"
          :loading="isCreating"
          :disabled="enabledFields.length === 0 || !primaryField"
        >
          创建数据表
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;

.excel-import-dialog {
  :deep(.el-dialog__body) {
    padding-top: 10px;
  }
}

.import-steps {
  margin-bottom: 30px;
}

.step-content {
  min-height: 400px;
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

.table-info-section {
  margin-bottom: 24px;

  h4 {
    margin: 0 0 16px;
    font-size: $font-size-base;
    color: $text-primary;
  }
}

.fields-section {
  .fields-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;

    h4 {
      margin: 0;
      font-size: $font-size-base;
      color: $text-primary;
    }
  }

  .fields-hint {
    margin: 0 0 16px;
    color: $text-secondary;
    font-size: $font-size-sm;
  }
}

.fields-table {
  :deep(.el-table__cell) {
    padding: 4px 0;
  }

  .sample-values {
    display: block;
    max-width: 150px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    color: $text-secondary;
    font-size: $font-size-sm;
  }
}

.result-section {
  :deep(.el-result__extra) {
    width: 100%;
  }
}

.result-stats {
  text-align: center;

  p {
    margin: 4px 0;
  }
}

.error-message {
  text-align: center;
  color: $error-color;
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
</style>
