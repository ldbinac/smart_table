<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage, ElLoading } from "element-plus";
import type { FieldEntity } from "@/db/schema";
import { FieldType, type CellValue, type FieldTypeValue } from "@/types";
import { useTableStore } from "@/stores/tableStore";
import { generateId } from "@/utils/id";
import dayjs from "dayjs";

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

// 表单配置
const formConfig = ref({
  title: "数据收集表单",
  description: "",
  submitButtonText: "提交",
  successMessage: "提交成功，感谢您的参与！",
  visibleFieldIds: [] as string[],
  allowMultipleSubmit: true,
});

// 获取主键字段
const primaryField = computed(() => {
  return fields.value.find((f) => f.isPrimary) || fields.value[0];
});

// 检查字段是否为主键字段
function isPrimaryField(field: FieldEntity): boolean {
  return primaryField.value?.id === field.id;
}

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

  // 检查是否明确设置了 visibleFieldIds（包括空数组的情况）
  const hasVisibleFieldIds =
    "visibleFieldIds" in formConfig.value &&
    Array.isArray(formConfig.value.visibleFieldIds);

  if (hasVisibleFieldIds) {
    // 按照 visibleFieldIds 的顺序排序，并只显示包含在列表中的字段
    // 即使是空数组也使用配置（显示空表单）
    const fieldMap = new Map(filteredFields.map((f) => [f.id, f]));
    return formConfig.value.visibleFieldIds
      .map((id) => fieldMap.get(id))
      .filter((f): f is FieldEntity => f !== undefined);
  }

  // 否则按照字段的 order 属性排序
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
  // 从 localStorage 获取基础表单配置（标题、描述等）
  const storedConfig = localStorage.getItem(`form_config_${formId}`);
  let config: any = null;

  if (storedConfig) {
    config = JSON.parse(storedConfig);
    tableId.value = config.tableId;
    tableName.value = config.tableName;

    // 加载表单基础配置（标题、描述等UI配置）
    if (config.formConfig) {
      formConfig.value = {
        title: config.formConfig.title ?? "数据收集表单",
        description: config.formConfig.description ?? "",
        submitButtonText: config.formConfig.submitButtonText ?? "提交",
        successMessage:
          config.formConfig.successMessage ?? "提交成功，感谢您的参与！",
        visibleFieldIds: config.formConfig.visibleFieldIds ?? [],
        allowMultipleSubmit: config.formConfig.allowMultipleSubmit ?? true,
      };
    }

    // 关键：优先使用保存的字段配置（已根据visibleFieldIds过滤）
    if (config.fields && config.fields.length > 0) {
      fields.value = config.fields;
    } else if (tableId.value) {
      // 如果没有保存字段，则从服务器加载
      await loadTableData(tableId.value);
    }
  } else {
    // 如果没有存储的配置，尝试从 URL 参数解析
    const queryTableId = route.query.tableId as string;
    if (queryTableId) {
      tableId.value = queryTableId;
      // 从服务器加载表格数据
      await loadTableData(queryTableId);
    } else {
      throw new Error("无法找到表单配置");
    }
  }

  // 初始化表单值
  resetForm();
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
  if (isPrimaryField(field)) return null;

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

  // 为主键字段生成ID
  if (primaryField.value) {
    formValues.value[primaryField.value.id] = generateId();
  }

  // 设置默认值
  visibleFields.value.forEach((field) => {
    if (field.options?.defaultValue !== undefined && !isPrimaryField(field)) {
      formValues.value[field.id] = field.options.defaultValue as CellValue;
    }
  });
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
      return "singleSelect";
    case FieldType.MULTI_SELECT:
      return "multiSelect";
    case FieldType.DATE:
      return "date";
    case FieldType.CHECKBOX:
      return "checkbox";
    default:
      return "text";
  }
}

// 获取选项
function getSelectOptions(field: FieldEntity) {
  return (
    (field.options?.options as Array<{
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
            <span
              v-if="field.options?.required && !isPrimaryField(field)"
              class="required-mark"
              >*</span
            >
          </label>

          <div class="form-control">
            <!-- 主键字段 -->
            <template v-if="isPrimaryField(field)">
              <el-input
                :model-value="String(formValues[field.id] || '')"
                disabled
                :placeholder="`自动生成${field.name}`"
                class="primary-field-input" />
              <span class="auto-filled-hint"
                >系统自动生成唯一标识，不可修改</span
              >
            </template>

            <!-- 文本类型 -->
            <template v-else-if="getFieldComponentType(field) === 'text'">
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
              v-else-if="getFieldComponentType(field) === 'singleSelect'">
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
              v-else-if="getFieldComponentType(field) === 'multiSelect'">
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
          </div>

          <div v-if="formErrors[field.id]" class="form-error">
            <el-icon><Warning /></el-icon>
            {{ formErrors[field.id] }}
          </div>

          <div
            v-if="field.options?.description && !isPrimaryField(field)"
            class="form-field-description">
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
