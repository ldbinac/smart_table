<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { ElMessage } from "element-plus";
import { useI18n } from "vue-i18n";
import {
  Upload,
  ArrowRight,
  ArrowLeft,
  Loading,
  CircleCheck,
  CircleClose,
  InfoFilled,
} from "@element-plus/icons-vue";
import { importExportApiService } from "@/services/api/importExportApiService";
import { getUserCreatableFieldTypeOptions } from "@/types/fields";

const { t } = useI18n();

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
const createStatus = ref<'idle' | 'creating_table' | 'importing_data' | 'completed' | 'failed'>('idle');
const createStatusText = ref("");
const currentTaskId = ref("");
let progressTimer: ReturnType<typeof setInterval> | null = null;

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

// 字段类型选项（从中央模块获取，确保一致性）
const fieldTypeOptions = getUserCreatableFieldTypeOptions({
  includeSpecial: true,
  markSpecial: true,
});

// 创建步骤配置
const createSteps = [
  { key: 'creating_table', label: t('importExcel.creatingTable'), icon: 'Document' },
  { key: 'importing_data', label: t('importExcel.importingData', { pct: 0 }), icon: 'DataLine' },
  { key: 'completed', label: t('importExcel.done'), icon: 'CircleCheck' },
];

// 文件上传处理
async function handleFileChange(file: File) {
  const validExtensions = [".xlsx", ".xls"];
  const extension = file.name.slice(file.name.lastIndexOf(".")).toLowerCase();

  if (!validExtensions.includes(extension)) {
    ElMessage.error(t('importExcel.unsupportedFormat'));
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
        t('importExcel.parsedSuccess', { rows: result.data.total_rows, cols: result.data.total_columns })
      );

      // 自动进入下一步
      currentStep.value = 2;
    } else {
      ElMessage.error(result.message || t('importExcel.parseFailed'));
    }
  } catch (error) {
    ElMessage.error(error instanceof Error ? error.message : t('importExcel.parseFailed'));
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
function handlePrimaryChange(index: number, isPrimary: string | number | boolean) {
  const primary = Boolean(isPrimary);
  if (primary) {
    // 取消其他字段的主字段状态
    fieldConfigs.value.forEach((field, i) => {
      if (i !== index) {
        field.is_primary = false;
      }
    });
  }
  fieldConfigs.value[index].is_primary = primary;
}

// 获取已启用的字段
const enabledFields = computed(() => {
  return fieldConfigs.value.filter((f) => f.included);
});

// 获取主字段
const primaryField = computed(() => {
  return fieldConfigs.value.find((f) => f.is_primary && f.included);
});

// 查询任务进度
async function queryTaskProgress(taskId: string) {
  try {
    const status = await importExportApiService.getImportTaskStatus(taskId);
    
    if (status) {
      createProgress.value = status.progress || 0;
      
      // 根据状态更新UI
      switch (status.status) {
        case 'pending':
          createStatus.value = 'creating_table';
          createStatusText.value = t('importExcel.waiting');
          break;
        case 'processing':
          if (createProgress.value < 30) {
            createStatus.value = 'creating_table';
            createStatusText.value = t('importExcel.creatingTable');
          } else if (createProgress.value < 90) {
            createStatus.value = 'importing_data';
            createStatusText.value = t('importExcel.importingData', { pct: createProgress.value });
          } else {
            createStatus.value = 'importing_data';
            createStatusText.value = t('importExcel.finishingImport');
          }
          break;
        case 'completed':
          createProgress.value = 100;
          createStatus.value = 'completed';
          createStatusText.value = t('importExcel.done');
          stopProgressTimer();
          break;
        case 'failed':
          createStatus.value = 'failed';
          createStatusText.value = status.error || t('importExcel.failedStatus');
          stopProgressTimer();
          break;
      }
    }
  } catch (error) {
    console.error('查询任务进度失败:', error);
  }
}

// 启动进度定时器
function startProgressTimer(taskId: string) {
  // 立即查询一次
  queryTaskProgress(taskId);
  
  // 每1秒查询一次进度
  progressTimer = setInterval(() => {
    queryTaskProgress(taskId);
  }, 1000);
}

// 停止进度定时器
function stopProgressTimer() {
  if (progressTimer) {
    clearInterval(progressTimer);
    progressTimer = null;
  }
}

// 执行创建
async function handleCreate() {
  if (!tableName.value.trim()) {
    ElMessage.warning(t('importExcel.tableNameRequired'));
    return;
  }

  const enabledFieldsList = enabledFields.value;
  if (enabledFieldsList.length === 0) {
    ElMessage.warning(t('importExcel.atLeastOneField'));
    return;
  }

  if (!primaryField.value) {
    ElMessage.warning(t('importExcel.setPrimary'));
    return;
  }

  isCreating.value = true;
  createProgress.value = 0;
  createStatus.value = 'creating_table';
  createStatusText.value = t('importExcel.creatingTable');
  currentTaskId.value = "";

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
      // 如果有task_id，启动轮询查询进度
      if (result.data.task_id && importData.value) {
        currentTaskId.value = result.data.task_id;
        startProgressTimer(result.data.task_id);
        
        // 等待任务完成（最多等待5分钟）
        await waitForTaskComplete(result.data.task_id, 300);
      } else {
        // 没有task_id或不需要导入数据，直接完成
        createProgress.value = 100;
        createStatus.value = 'completed';
      }

      createResult.value = {
        success: true,
        tableId: result.data.table_id,
        tableName: result.data.table_name,
        createdFieldsCount: result.data.created_fields_count,
        importedRows: result.data.imported_rows,
        failedRows: result.data.failed_rows,
      };
      currentStep.value = 3;
      ElMessage.success(t('importExcel.tableCreated'));
      emit("created", result.data.table_id);
    } else {
      createStatus.value = 'failed';
      createResult.value = {
        success: false,
        message: result.message || t('importExcel.createFailed'),
      };
      currentStep.value = 3;
      ElMessage.error(result.message || t('importExcel.createFailed'));
    }
  } catch (error) {
    createStatus.value = 'failed';
    createResult.value = {
      success: false,
      message: error instanceof Error ? error.message : t('importExcel.createFailed'),
    };
    currentStep.value = 3;
    ElMessage.error(error instanceof Error ? error.message : t('importExcel.createFailed'));
  } finally {
    isCreating.value = false;
    stopProgressTimer();
  }
}

// 等待任务完成
async function waitForTaskComplete(taskId: string, maxAttempts: number): Promise<boolean> {
  return new Promise((resolve) => {
    let attempts = 0;
    const checkInterval = setInterval(async () => {
      attempts++;
      
      if (attempts >= maxAttempts) {
        clearInterval(checkInterval);
        resolve(true); // 超时也算完成
        return;
      }
      
      try {
        const status = await importExportApiService.getImportTaskStatus(taskId);
        if (status && (status.status === 'completed' || status.status === 'failed')) {
          clearInterval(checkInterval);
          resolve(true);
        }
      } catch (error) {
        console.error('查询任务状态失败:', error);
      }
    }, 1000);
  });
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
      ElMessage.warning(t('importExcel.tableNameRequired'));
      return;
    }
    if (enabledFields.value.length === 0) {
      ElMessage.warning(t('importExcel.atLeastOneField'));
      return;
    }
    if (!primaryField.value) {
      ElMessage.warning(t('importExcel.setPrimary'));
      return;
    }
  }

  if (currentStep.value < totalSteps) {
    currentStep.value++;
  }
}

// 关闭对话框
function handleClose() {
  // 如果正在创建中，先停止定时器
  if (isCreating.value) {
    stopProgressTimer();
  }
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
  createStatus.value = 'idle';
  createStatusText.value = "";
  currentTaskId.value = "";
  createResult.value = null;
  stopProgressTimer();
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

// 组件卸载时清理定时器
watch(() => props.visible, () => {
  if (!props.visible) {
    stopProgressTimer();
  }
});
</script>

<template>
  <el-dialog
    :model-value="visible"
    @update:model-value="handleClose"
    :title="t('importExcel.title')"
    width="900px"
    :close-on-click-modal="!isCreating"
    :close-on-press-escape="!isCreating"
    class="excel-import-dialog"
  >
    <!-- 步骤条 -->
    <el-steps
      :active="currentStep"
      finish-status="success"
      class="import-steps"
    >
      <el-step :title="t('importExcel.stepSelectFile')" />
      <el-step :title="t('importExcel.stepConfigField')" />
      <el-step :title="t('importExcel.stepDone')" />
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
        :disabled="isParsing"
      >
        <el-icon class="upload-icon"><Upload /></el-icon>
        <div class="upload-text">
          <p>{{ t('importExcel.dragOrClick') }}</p>
          <p class="upload-hint">{{ t('importExcel.supportedFormats') }}</p>
        </div>
      </el-upload>

      <div v-if="analysisResult" class="file-info">
        <el-alert
          :title="t('importExcel.selectedFile', { name: originalFilename })"
          type="success"
          :closable="false"
          show-icon
        >
          <template #default>
            <p>
              {{ t('importExcel.fileInfo', { rows: analysisResult.total_rows, cols: analysisResult.total_columns }) }}
            </p>
          </template>
        </el-alert>
      </div>

      <!-- 文件解析进度 -->
      <div v-if="isParsing" class="parsing-status">
        <div class="progress-indicator">
          <el-icon class="rotating-icon"><Loading /></el-icon>
          <span class="progress-text">{{ t('importExcel.parsing') }}</span>
        </div>
        <el-progress 
          :percentage="100" 
          :indeterminate="true" 
          :stroke-width="8"
          :show-text="false"
          class="parsing-progress"
        />
      </div>
    </div>

    <!-- 步骤 2: 配置字段 -->
    <div v-if="currentStep === 2" class="step-content">
      <!-- 数据表基本信息 -->
      <div class="table-info-section">
        <h4>{{ t('importExcel.tableInfo') }}</h4>
        <el-form :model="{ tableName, tableDescription }" label-width="80px">
          <el-form-item :label="t('importExcel.name')" required>
            <el-input
              v-model="tableName"
              :placeholder="t('importExcel.namePlaceholder')"
              maxlength="50"
              show-word-limit
            />
          </el-form-item>
          <el-form-item :label="t('importExcel.description')">
            <el-input
              v-model="tableDescription"
              type="textarea"
              :rows="2"
              :placeholder="t('importExcel.descPlaceholder')"
              maxlength="200"
              show-word-limit
            />
          </el-form-item>
        </el-form>
      </div>

      <!-- 字段配置 -->
      <div class="fields-section">
        <div class="fields-header">
          <h4>{{ t('importExcel.fieldConfig') }}</h4>
          <el-checkbox v-model="importData">{{ t('importExcel.importDataTogether') }}</el-checkbox>
        </div>
        <p class="fields-hint">
          {{ t('importExcel.fieldConfigHint') }}
        </p>

        <el-table :data="fieldConfigs" border class="fields-table" size="small">
          <el-table-column type="index" width="50" />
          <el-table-column :label="t('importExcel.importCol')" width="60" align="center">
            <template #default="{ row }">
              <el-checkbox v-model="row.included" />
            </template>
          </el-table-column>
          <el-table-column :label="t('importExcel.primaryCol')" width="80" align="center">
            <template #default="{ row, $index }">
              <el-radio
                v-model="row.is_primary"
                :label="true"
                :disabled="!row.included"
                @change="handlePrimaryChange($index, $event as boolean)"
              >
                <span></span>
              </el-radio>
            </template>
          </el-table-column>
          <el-table-column prop="source_column" :label="t('importExcel.excelCol')" width="150" />
          <el-table-column :label="t('field.fieldName')" width="150">
            <template #default="{ row }">
              <el-input
                v-model="row.name"
                size="small"
                :disabled="row.included !== true"
                maxlength="50"
              />
            </template>
          </el-table-column>
          <el-table-column :label="t('field.fieldType')" width="130">
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
                  :disabled="opt.isSpecial"
                >
                  <span class="type-option">
                    <span class="type-icon">
                      <el-icon>
                        <component :is="opt.icon" />
                      </el-icon>
                    </span>
                    <span :class="{ 'special-type': opt.isSpecial }">
                      {{ opt.label }}
                    </span>
                    <span v-if="opt.specialHint" class="special-hint">
                      ({{ opt.specialHint }})
                    </span>
                  </span>
                </el-option>
              </el-select>
            </template>
          </el-table-column>
          <el-table-column :label="t('importExcel.sampleData')" min-width="150">
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
          :title="createResult.success ? t('importExcel.createSuccess') : t('importExcel.createFailed')"
        >
          <template #sub-title>
            <div v-if="createResult.success" class="result-stats">
              <p><strong>{{ t('importExcel.tableLabel') }}</strong> {{ createResult.tableName }}</p>
              <p>
                <strong>{{ t('importExcel.createdFields', { count: createResult.createdFieldsCount }) }}</strong>
              </p>
              <p v-if="importData">
                <strong>{{ t('importExcel.importedRows', { count: createResult.importedRows }) }}</strong>
              </p>
              <p v-if="importData && createResult.failedRows">
                <strong>{{ t('importExcel.failedRows', { count: createResult.failedRows }) }}</strong>
              </p>
            </div>
            <div v-else class="error-message">
              <p>{{ createResult.message }}</p>
            </div>
          </template>

          <template #extra>
            <div class="result-actions">
              <el-button @click="handleClose">{{ t('common.close') }}</el-button>
              <el-button v-if="!createResult.success" type="primary" @click="handleRecreate"
                >{{ t('importExcel.recreate') }}</el-button
              >
            </div>
          </template>
        </el-result>
      </div>

      <!-- 创建进度 - 优化后的设计 -->
      <div v-else-if="isCreating" class="creating-section">
        <div class="creating-container">
          <!-- 主进度条 -->
          <div class="main-progress-wrapper">
            <el-progress 
              :percentage="createProgress" 
              :stroke-width="12"
              :status="createStatus === 'failed' ? 'exception' : ''"
              class="main-progress"
            />
            <div class="progress-percentage">{{ createProgress }}%</div>
          </div>

          <!-- 状态文字 -->
          <div class="status-text-wrapper">
            <el-icon v-if="createStatus !== 'failed'" class="rotating-icon status-icon">
              <Loading />
            </el-icon>
            <el-icon v-else class="status-icon error-icon">
              <CircleClose />
            </el-icon>
            <span class="status-text" :class="{ 'error-text': createStatus === 'failed' }">
              {{ createStatusText }}
            </span>
          </div>

          <!-- 处理步骤指示器 -->
          <div class="process-steps">
            <div 
              v-for="(step, index) in createSteps" 
              :key="step.key"
              class="process-step"
              :class="{
                'step-active': createStatus === step.key || (createStatus === 'importing_data' && step.key === 'creating_table') || (createStatus === 'completed' && index < 2),
                'step-completed': createStatus === 'completed' || (createStatus === 'importing_data' && step.key === 'creating_table'),
                'step-pending': !((createStatus === step.key) || (createStatus === 'importing_data' && step.key === 'creating_table') || (createStatus === 'completed' && index < 2))
              }"
            >
              <div class="step-icon-wrapper">
                <el-icon v-if="(createStatus === 'completed' && index < 2) || (createStatus === 'importing_data' && step.key === 'creating_table')" class="step-icon">
                  <CircleCheck />
                </el-icon>
                <el-icon v-else-if="createStatus === step.key" class="step-icon rotating">
                  <Loading />
                </el-icon>
                <el-icon v-else class="step-icon">
                  <component :is="step.icon" />
                </el-icon>
              </div>
              <span class="step-label">{{ step.label }}</span>
            </div>
          </div>

          <!-- 提示信息 -->
          <div class="creating-hint">
            <el-icon><Info-Filled /></el-icon>
            <span>{{ t('importExcel.processingHint') }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部按钮 -->
    <template #footer>
      <div class="dialog-footer">
        <el-button v-if="currentStep > 1 && currentStep < 3" @click="prevStep" :disabled="isCreating">
          <el-icon><ArrowLeft /></el-icon>
          {{ t('importExcel.prevStep') }}
        </el-button>

        <el-button
          v-if="currentStep === 1"
          type="primary"
          @click="nextStep"
          :disabled="!analysisResult"
        >
          {{ t('importExcel.nextStep') }}
          <el-icon><ArrowRight /></el-icon>
        </el-button>

        <el-button
          v-if="currentStep === 2"
          type="primary"
          @click="handleCreate"
          :loading="isCreating"
          :disabled="enabledFields.length === 0 || !primaryField"
        >
          {{ t('importExcel.createTable') }}
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
  margin-top: 24px;
  padding: 20px;
  background: $gray-50;
  border-radius: $border-radius-lg;
  border: 1px solid $border-color;

  .progress-indicator {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 12px;
    margin-bottom: 16px;

    .rotating-icon {
      font-size: 24px;
      color: $primary-color;
      animation: rotating 2s linear infinite;
    }

    .progress-text {
      font-size: $font-size-base;
      color: $text-primary;
      font-weight: 500;
    }
  }

  .parsing-progress {
    max-width: 400px;
    margin: 0 auto;
  }
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

.type-option {
  display: flex;
  align-items: center;
  gap: 8px;

  .type-icon {
    font-size: 14px;
    display: flex;
    align-items: center;
  }

  .special-type {
    color: $text-secondary;
  }

  .special-hint {
    font-size: $font-size-xs;
    color: $text-secondary;
    margin-left: 4px;
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

// 优化后的创建进度样式
.creating-section {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 350px;
  padding: 20px;
}

.creating-container {
  width: 100%;
  max-width: 500px;
  text-align: center;
}

.main-progress-wrapper {
  position: relative;
  margin-bottom: 24px;

  .main-progress {
    :deep(.el-progress-bar__outer) {
      border-radius: 6px;
      background-color: $gray-200;
    }

    :deep(.el-progress-bar__inner) {
      border-radius: 6px;
      background: linear-gradient(90deg, $primary-color 0%, $primary-hover 100%);
      transition: width 0.3s ease;
    }
  }

  .progress-percentage {
    position: absolute;
    right: 0;
    top: -28px;
    font-size: $font-size-lg;
    font-weight: 600;
    color: $primary-color;
  }
}

.status-text-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  margin-bottom: 32px;

  .status-icon {
    font-size: 20px;
    color: $primary-color;

    &.rotating-icon {
      animation: rotating 2s linear infinite;
    }

    &.error-icon {
      color: $error-color;
    }
  }

  .status-text {
    font-size: $font-size-lg;
    font-weight: 500;
    color: $text-primary;

    &.error-text {
      color: $error-color;
    }
  }
}

.process-steps {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 40px;
  margin-bottom: 32px;
  padding: 24px;
  background: $gray-50;
  border-radius: $border-radius-xl;
  border: 1px solid $border-color;

  .process-step {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 8px;
    transition: all 0.3s ease;

    .step-icon-wrapper {
      width: 48px;
      height: 48px;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      background: $gray-200;
      transition: all 0.3s ease;

      .step-icon {
        font-size: 24px;
        color: $text-secondary;
        transition: all 0.3s ease;

        &.rotating {
          animation: rotating 2s linear infinite;
        }
      }
    }

    .step-label {
      font-size: $font-size-sm;
      color: $text-secondary;
      font-weight: 500;
      transition: all 0.3s ease;
    }

    // 激活状态
    &.step-active {
      .step-icon-wrapper {
        background: $primary-light;
        box-shadow: 0 0 0 3px rgba($primary-color, 0.2);

        .step-icon {
          color: $primary-color;
        }
      }

      .step-label {
        color: $primary-color;
        font-weight: 600;
      }
    }

    // 完成状态
    &.step-completed {
      .step-icon-wrapper {
        background: $success-light;

        .step-icon {
          color: $success-color;
        }
      }

      .step-label {
        color: $success-color;
      }
    }
  }
}

.creating-hint {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 20px;
  background: $warning-light;
  border-radius: $border-radius-lg;
  border: 1px solid rgba($warning-color, 0.3);

  .el-icon {
    font-size: 16px;
    color: $warning-color;
  }

  span {
    font-size: $font-size-sm;
    color: $warning-dark;
  }
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

// 旋转动画
@keyframes rotating {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
