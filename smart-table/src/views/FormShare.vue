<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage, ElLoading } from "element-plus";
import type { FieldEntity } from "@/db/schema";
import { FieldType, type CellValue, type FieldTypeValue } from "@/types";
import { useTableStore } from "@/stores/tableStore";
import { viewService } from "@/db/services/viewService";
import { generateId } from "@/utils/id";
import dayjs from "dayjs";
import AttachmentField from "@/components/fields/AttachmentField.vue";

const route = useRoute();
const router = useRouter();
const tableStore = useTableStore();

// 加载状态
const isLoading = ref(true);
const loadError = ref("");

// 表单数据
const tableId = ref("");
const tableName = ref("");
const fields = ref<FieldEntity[]>([]);
const formValues = ref<Record<string, CellValue>>({});
const formErrors = ref<Record<string, string>>({});
const isSubmitting = ref(false);
const submitSuccess = ref(false);
const newRecordId = ref(generateId());

// 表单配置
const formConfig = ref({
  title: "数据收集表单",
  description: "",
  submitButtonText: "提交",
  successMessage: "提交成功，感谢您的参与！",
  visibleFieldIds: [] as string[],
  allowMultipleSubmit: true,
});

// 可见字段（根据表单配置和表格配置综合判断）
const visibleFields = computed(() => {
  const systemFieldTypes: FieldTypeValue[] = [
    FieldType.CREATED_BY,
    FieldType.CREATED_TIME,
    FieldType.UPDATED_BY,
    FieldType.UPDATED_TIME,
    FieldType.AUTO_NUMBER,
  ];

  // 首先过滤掉系统字段和明确隐藏的字段
  let filteredFields = fields.value
    .filter((f) => !f.options?.hidden)
    .filter((f) => !systemFieldTypes.includes(f.type as FieldTypeValue));

  console.log("[FormShare] visibleFields computed:");
  console.log("[FormShare] All fields count:", fields.value.length);
  console.log("[FormShare] Filtered fields count:", filteredFields.length);
  console.log(
    "[FormShare] formConfig.visibleFieldIds:",
    formConfig.value.visibleFieldIds,
  );

  // 检查是否明确设置了 visibleFieldIds（包括空数组的情况）
  const hasVisibleFieldIds =
    "visibleFieldIds" in formConfig.value &&
    Array.isArray(formConfig.value.visibleFieldIds);

  console.log("[FormShare] hasVisibleFieldIds:", hasVisibleFieldIds);

  if (hasVisibleFieldIds && formConfig.value.visibleFieldIds.length > 0) {
    // 按照 visibleFieldIds 的顺序排序，并只显示包含在列表中的字段
    const fieldMap = new Map(filteredFields.map((f) => [f.id, f]));
    const result = formConfig.value.visibleFieldIds
      .map((id) => fieldMap.get(id))
      .filter((f): f is FieldEntity => f !== undefined);
    console.log(
      "[FormShare] Using visibleFieldIds order, result count:",
      result.length,
    );
    return result;
  }

  // 如果没有设置 visibleFieldIds 或为空数组，显示所有非系统字段
  console.log("[FormShare] Using default order");
  return filteredFields.sort((a, b) => (a.order || 0) - (b.order || 0));
});

// 页面加载时获取表单数据
onMounted(async () => {
  const formId = route.params.id as string;

  if (!formId) {
    loadError.value = "无效的表单链接";
    isLoading.value = false;
    return;
  }

  try {
    // 从 formId 解析 tableId（实际项目中应该从后端获取）
    // 这里使用模拟数据，实际应该调用 API 获取表单配置
    await loadFormData(formId);
  } catch (error) {
    console.error("加载表单失败:", error);
    loadError.value = "表单加载失败，请检查链接是否有效";
  } finally {
    isLoading.value = false;
  }
});

// 加载表单数据
async function loadFormData(formId: string) {
  console.log("[FormShare] Loading form data for formId:", formId);

  try {
    // 从数据库获取视图配置（formId 实际上是 viewId）
    const view = await viewService.getView(formId);
    console.log("[FormShare] View from database:", view);

    if (view && view.type === "form") {
      tableId.value = view.tableId;

      // 从 config 字段加载表单配置（后端会将 form_config 以 config 形式返回）
      const configData = view.config as {
        title?: string;
        description?: string;
        submitButtonText?: string;
        visibleFieldIds?: string[];
        successMessage?: string;
        allowMultipleSubmit?: boolean;
      };

      // 加载表单基础配置（标题、描述等 UI 配置）
      if (configData) {
        console.log(
          "[FormShare] Loading formConfig from database:",
          configData,
        );

        formConfig.value = {
          title: configData.title || "数据收集表单",
          description: configData.description || "",
          submitButtonText: configData.submitButtonText || "提交",
          successMessage:
            configData.successMessage || "提交成功，感谢您的参与！",
          visibleFieldIds: configData.visibleFieldIds || [],
          allowMultipleSubmit: configData.allowMultipleSubmit !== false,
        };

        console.log("[FormShare] Loaded formConfig:", formConfig.value);
        console.log(
          "[FormShare] visibleFieldIds:",
          formConfig.value.visibleFieldIds,
        );
      }

      // 从数据库加载表格数据（字段）
      await loadTableData(view.tableId);
    } else {
      // 如果数据库中没有找到视图配置，尝试从 localStorage 获取（兼容旧数据）
      console.log(
        "[FormShare] View not found in database, trying localStorage",
      );
      await loadFromLocalStorage(formId);
    }

    // 初始化表单值
    resetForm();
  } catch (error) {
    console.error("[FormShare] Error loading form data:", error);
    throw error;
  }
}

// 从 localStorage 加载（兼容旧数据）
async function loadFromLocalStorage(formId: string) {
  const storedConfig = localStorage.getItem(`form_config_${formId}`);

  if (storedConfig) {
    const config = JSON.parse(storedConfig);
    tableId.value = config.tableId;
    tableName.value = config.tableName;

    if (config.formConfig) {
      formConfig.value = {
        title: config.formConfig.title || "数据收集表单",
        description: config.formConfig.description || "",
        submitButtonText: config.formConfig.submitButtonText || "提交",
        successMessage:
          config.formConfig.successMessage || "提交成功，感谢您的参与！",
        visibleFieldIds: config.formConfig.visibleFieldIds || [],
        allowMultipleSubmit: config.formConfig.allowMultipleSubmit !== false,
      };
    }

    if (config.fields && config.fields.length > 0) {
      fields.value = config.fields;
    } else if (tableId.value) {
      await loadTableData(tableId.value);
    }
  } else {
    // 如果没有存储的配置，尝试从 URL 参数解析
    const queryTableId = route.query.tableId as string;
    if (queryTableId) {
      tableId.value = queryTableId;
      await loadTableData(queryTableId);
    } else {
      throw new Error("无法找到表单配置");
    }
  }
}

// 加载表格数据
async function loadTableData(id: string) {
  try {
    // 从 tableStore 加载表格数据
    await tableStore.selectTable(id);
    if (tableStore.currentTable) {
      tableName.value = tableStore.currentTable.name;
      fields.value = tableStore.fields || [];
    } else {
      throw new Error("表格不存在");
    }
  } catch (error) {
    console.error("加载表格数据失败:", error);
    throw error;
  }
}

// 验证字段
function validateField(field: FieldEntity, value: CellValue): string | null {
  if (
    field.options?.required &&
    (value === null || value === undefined || value === "" || value === false)
  ) {
    return `${field.name}为必填项`;
  }

  if (value === null || value === undefined || value === "") {
    return null;
  }

  switch (field.type) {
    case FieldType.EMAIL:
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(value))) {
        return "请输入有效的邮箱地址";
      }
      break;
    case FieldType.PHONE:
      if (!/^1[3-9]\d{9}$/.test(String(value))) {
        return "请输入有效的手机号码";
      }
      break;
    case FieldType.URL:
      try {
        new URL(String(value));
      } catch {
        return "请输入有效的URL";
      }
      break;
    case FieldType.NUMBER:
    case FieldType.RATING:
      if (typeof value === "number" || !isNaN(Number(value))) {
        const numValue = Number(value);
        if (
          field.options?.min !== undefined &&
          numValue < Number(field.options.min)
        ) {
          return `${field.name}不能小于${field.options.min}`;
        }
        if (
          field.options?.max !== undefined &&
          numValue > Number(field.options.max)
        ) {
          return `${field.name}不能大于${field.options.max}`;
        }
      }
      break;
  }

  return null;
}

// 处理字段值变化
function handleFieldChange(fieldId: string, value: CellValue) {
  formValues.value[fieldId] = value;

  const field = fields.value.find((f) => f.id === fieldId);
  if (field) {
    const error = validateField(field, value);
    if (error) {
      formErrors.value[fieldId] = error;
    } else {
      delete formErrors.value[fieldId];
    }
  }
}

// 提交表单
async function handleSubmit() {
  formErrors.value = {};

  visibleFields.value.forEach((field) => {
    const error = validateField(field, formValues.value[field.id]);
    if (error) {
      formErrors.value[field.id] = error;
    }
  });

  if (Object.keys(formErrors.value).length > 0) {
    const firstError = Object.values(formErrors.value)[0];
    ElMessage.error(firstError);
    return;
  }

  if (!tableId.value) {
    ElMessage.error("表单配置错误");
    return;
  }

  isSubmitting.value = true;

  try {
    const record = await tableStore.createRecord({
      tableId: tableId.value,
      values: { ...formValues.value },
    });

    if (record) {
      submitSuccess.value = true;
      ElMessage.success(formConfig.value.successMessage);
    } else {
      ElMessage.error(tableStore.error || "提交失败");
    }
  } catch (error) {
    console.error("提交表单失败:", error);
    ElMessage.error("提交失败，请稍后重试");
  } finally {
    isSubmitting.value = false;
  }
}

// 重置表单
function resetForm() {
  formValues.value = {};
  formErrors.value = {};
  newRecordId.value = generateId();

  // 设置默认值：使用 field.defaultValue（与 AddRecordDrawer 保持一致）
  visibleFields.value.forEach((field) => {
    if (field.defaultValue !== undefined && field.defaultValue !== null) {
      // 特殊处理日期字段的动态默认值 'now'
      if (field.type === FieldType.DATE && field.defaultValue === 'now') {
        // 动态计算当前日期
        const showTime = (field.options?.showTime as boolean) ?? false;
        if (showTime) {
          formValues.value[field.id] = new Date().toISOString();
        } else {
          formValues.value[field.id] = new Date().toISOString().split('T')[0];
        }
      } else {
        formValues.value[field.id] = field.defaultValue as CellValue;
      }
    }
  });
}

// 处理附件上传
function handleAttachmentUpload(fieldId: string, newFiles: unknown[]) {
  // 使用 Map 去重，避免重复添加相同 ID 的文件
  const currentFiles = (formValues.value[fieldId] as unknown[]) || [];
  const fileMap = new Map<string, unknown>();

  // 添加现有文件
  currentFiles.forEach((f) => {
    const file = f as { id: string };
    fileMap.set(file.id, f);
  });

  // 添加新文件（如果 ID 不存在）
  newFiles.forEach((f) => {
    const file = f as { id: string };
    if (!fileMap.has(file.id)) {
      fileMap.set(file.id, f);
    }
  });

  formValues.value[fieldId] = Array.from(fileMap.values()) as CellValue;
}

// 处理附件删除
function handleAttachmentDelete(fieldId: string, fileId: string) {
  const currentFiles = (formValues.value[fieldId] as unknown[]) || [];
  formValues.value[fieldId] = currentFiles.filter(
    (f: unknown) => (f as { id: string }).id !== fileId,
  ) as CellValue;
}

// 返回首页
function goHome() {
  router.push("/");
}

// 重新加载
function reload() {
  window.location.reload();
}

// 获取字段组件类型
function getFieldComponentType(field: FieldEntity): string {
  switch (field.type) {
    case FieldType.TEXT:
    case FieldType.URL:
    case FieldType.EMAIL:
    case FieldType.PHONE:
      return "text";
    case FieldType.NUMBER:
    case FieldType.RATING:
      return "number";
    case FieldType.SINGLE_SELECT:
      return "single_select";
    case FieldType.MULTI_SELECT:
      return "multi_select";
    case FieldType.DATE:
      return "date";
    case FieldType.CHECKBOX:
      return "checkbox";
    case FieldType.ATTACHMENT:
      return "attachment";
    default:
      return "text";
  }
}

// 获取选项
function getSelectOptions(field: FieldEntity) {
  return (
    ((field.options?.choices || field.options?.options) as Array<{
      id: string;
      name: string;
      color?: string;
    }>) || []
  );
}

// 获取数值字段精度
function getNumberPrecision(field: FieldEntity): number {
  return (field.options?.precision as number) ?? 0;
}

// 获取日期字段是否显示时间
function getDateShowTime(field: FieldEntity): boolean {
  return (field.options?.showTime as boolean) ?? false;
}

// 获取日期字段格式
function getDateFormat(field: FieldEntity): string {
  return getDateShowTime(field) ? "YYYY-MM-DD HH:mm:ss" : "YYYY-MM-DD";
}

// 获取日期选择器类型
function getDatePickerType(field: FieldEntity): "date" | "datetime" {
  return getDateShowTime(field) ? "datetime" : "date";
}

// 处理日期变更
function handleDateChange(fieldId: string, val: Date | null) {
  if (!val) {
    handleFieldChange(fieldId, null);
    return;
  }

  const field = fields.value.find((f) => f.id === fieldId);
  if (!field) return;

  const showTime = getDateShowTime(field);
  if (showTime) {
    // 显示时间时存储为时间戳
    handleFieldChange(fieldId, val.getTime());
  } else {
    // 仅日期时存储为日期字符串
    handleFieldChange(fieldId, dayjs(val).format("YYYY-MM-DD"));
  }
}
</script>

<template>
  <div class="form-share-page">
    <!-- 加载状态 -->
    <div v-if="isLoading" class="loading-container">
      <el-loading :visible="true" text="加载中..." />
    </div>

    <!-- 错误状态 -->
    <el-result
      v-else-if="loadError"
      icon="error"
      title="无法加载表单"
      :sub-title="loadError">
      <template #extra>
        <el-button @click="goHome">返回首页</el-button>
        <el-button type="primary" @click="reload">重新加载</el-button>
      </template>
    </el-result>

    <!-- 提交成功 -->
    <el-result
      v-else-if="submitSuccess"
      icon="success"
      title="提交成功"
      :sub-title="formConfig.successMessage">
      <template #extra>
        <el-button type="primary" @click="resetForm">继续填写</el-button>
        <el-button @click="goHome">返回首页</el-button>
      </template>
    </el-result>

    <!-- 表单内容 -->
    <div v-else class="form-container">
      <div class="form-header">
        <h1 class="form-title">{{ formConfig.title }}</h1>
        <p v-if="formConfig.description" class="form-description">
          {{ formConfig.description }}
        </p>
      </div>

      <el-form
        label-position="top"
        class="form-content"
        @submit.prevent="handleSubmit">
        <div
          v-for="field in visibleFields"
          :key="field.id"
          class="form-item"
          :class="{ 'has-error': formErrors[field.id] }">
          <label class="form-label">
            {{ field.name }}
            <span v-if="field.options?.required" class="required-mark">*</span>
          </label>

          <div class="form-control">
            <!-- 文本类型 -->
            <template v-if="getFieldComponentType(field) === 'text'">
              <el-input
                :model-value="String(formValues[field.id] || '')"
                :placeholder="`请输入${field.name}`"
                @update:model-value="
                  (val) => handleFieldChange(field.id, val)
                " />
            </template>

            <!-- 数字类型 -->
            <template v-else-if="getFieldComponentType(field) === 'number'">
              <el-input-number
                :model-value="Number(formValues[field.id] || 0)"
                :placeholder="`请输入${field.name}`"
                :precision="getNumberPrecision(field)"
                :min="
                  field.options?.min !== undefined
                    ? Number(field.options.min)
                    : undefined
                "
                :max="
                  field.options?.max !== undefined
                    ? Number(field.options.max)
                    : undefined
                "
                style="width: 100%"
                @update:model-value="
                  (val) => handleFieldChange(field.id, val as CellValue)
                " />
            </template>

            <!-- 单选类型 -->
            <template
              v-else-if="getFieldComponentType(field) === 'single_select'">
              <el-select
                :model-value="formValues[field.id] as string | undefined"
                :placeholder="`请选择${field.name}`"
                style="width: 100%"
                clearable
                @update:model-value="(val) => handleFieldChange(field.id, val)">
                <el-option
                  v-for="option in getSelectOptions(field)"
                  :key="option.id"
                  :label="option.name"
                  :value="option.id">
                  <span
                    class="option-color"
                    :style="{ backgroundColor: option.color || '#3370FF' }" />
                  <span>{{ option.name }}</span>
                </el-option>
              </el-select>
            </template>

            <!-- 多选类型 -->
            <template
              v-else-if="getFieldComponentType(field) === 'multi_select'">
              <el-select
                :model-value="(formValues[field.id] as string[]) || []"
                :placeholder="`请选择${field.name}`"
                style="width: 100%"
                multiple
                clearable
                @update:model-value="(val) => handleFieldChange(field.id, val)">
                <el-option
                  v-for="option in getSelectOptions(field)"
                  :key="option.id"
                  :label="option.name"
                  :value="option.id">
                  <span
                    class="option-color"
                    :style="{ backgroundColor: option.color || '#3370FF' }" />
                  <span>{{ option.name }}</span>
                </el-option>
              </el-select>
            </template>

            <!-- 日期类型 -->
            <template v-else-if="getFieldComponentType(field) === 'date'">
              <el-date-picker
                :model-value="
                  formValues[field.id] as unknown as Date | undefined
                "
                :type="getDatePickerType(field)"
                :placeholder="`请选择${field.name}`"
                :format="getDateFormat(field)"
                style="width: 100%"
                @update:model-value="
                  (val) => handleDateChange(field.id, val as Date | null)
                " />
            </template>

            <!-- 复选框类型 -->
            <template v-else-if="getFieldComponentType(field) === 'checkbox'">
              <el-switch
                :model-value="Boolean(formValues[field.id])"
                @update:model-value="
                  (val) => handleFieldChange(field.id, val)
                " />
            </template>

            <!-- 附件字段类型 -->
            <template v-else-if="getFieldComponentType(field) === 'attachment'">
              <AttachmentField
                :model-value="formValues[field.id]"
                :field="field"
                :record-id="newRecordId"
                :readonly="false"
                @update:model-value="(val) => handleFieldChange(field.id, val)"
                @upload="(files) => handleAttachmentUpload(field.id, files)"
                @delete="
                  (fileId) => handleAttachmentDelete(field.id, fileId)
                " />
            </template>
          </div>

          <div v-if="formErrors[field.id]" class="form-error">
            <el-icon><Warning /></el-icon>
            {{ formErrors[field.id] }}
          </div>

          <div v-if="field.options?.description" class="form-field-description">
            {{ field.options.description }}
          </div>
        </div>

        <div class="form-actions">
          <el-button
            type="primary"
            native-type="submit"
            :loading="isSubmitting"
            size="large"
            class="submit-btn">
            {{ formConfig.submitButtonText }}
          </el-button>
        </div>
      </el-form>

      <div class="form-footer">
        <p>Powered by Smart Table</p>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;

.form-share-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
  padding: 40px 20px;
}

.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
}

.form-container {
  max-width: 640px;
  margin: 0 auto;
  background: $surface-color;
  border-radius: $border-radius-lg;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.08);
  overflow: hidden;
}

.form-header {
  text-align: center;
  padding: 40px 32px 24px;
  background: linear-gradient(135deg, $primary-color 0%, #5b8ff9 100%);
  color: white;
}

.form-title {
  font-size: 28px;
  font-weight: 600;
  margin: 0 0 12px;
  color: white;
}

.form-description {
  font-size: $font-size-base;
  margin: 0;
  opacity: 0.9;
  line-height: 1.6;
}

.form-content {
  padding: 32px;
}

.form-item {
  margin-bottom: 24px;

  &.has-error {
    .form-label {
      color: $error-color;
    }

    :deep(.el-input__wrapper),
    :deep(.el-select__wrapper) {
      border-color: $error-color;
      box-shadow: 0 0 0 1px $error-color;
    }
  }
}

.form-label {
  display: block;
  font-size: $font-size-sm;
  font-weight: 500;
  color: $text-primary;
  margin-bottom: 8px;
}

.required-mark {
  color: $error-color;
  margin-left: 4px;
}

.form-control {
  width: 100%;
}

.form-error {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: $font-size-xs;
  color: $error-color;
  margin-top: 4px;
}

.form-field-description {
  font-size: $font-size-xs;
  color: $text-secondary;
  margin-top: 4px;
  line-height: 1.5;
}

.form-actions {
  margin-top: 32px;
  padding-top: 24px;
  border-top: 1px solid $border-color;
}

.submit-btn {
  width: 100%;
  height: 48px;
  font-size: 16px;
}

.form-footer {
  text-align: center;
  padding: 16px;
  background: $bg-color;
  border-top: 1px solid $border-color;

  p {
    margin: 0;
    font-size: $font-size-xs;
    color: $text-secondary;
  }
}

.primary-field-input {
  :deep(.el-input__wrapper) {
    background-color: $bg-color;
  }
}

.auto-filled-hint {
  font-size: $font-size-xs;
  color: $text-secondary;
  margin-top: 4px;
  display: block;
}

.option-color {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  margin-right: 8px;
  vertical-align: middle;
}

// 响应式适配
@media (max-width: 768px) {
  .form-share-page {
    padding: 0;
    background: $surface-color;
  }

  .form-container {
    border-radius: 0;
    box-shadow: none;
    max-width: none;
  }

  .form-header {
    padding: 24px 20px 16px;
  }

  .form-title {
    font-size: 22px;
  }

  .form-content {
    padding: 20px;
  }
}
</style>
