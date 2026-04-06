<script setup lang="ts">
import { ref, computed, watch } from "vue";
import type { RecordEntity, FieldEntity } from "@/db/schema";
import { FieldType, type CellValue, type FieldTypeValue } from "@/types";
import { ElMessage, ElMessageBox } from "element-plus";
import { generateId } from "@/utils/id";
import dayjs from "dayjs";
import { FormulaEngine } from "@/utils/formula/engine";
import { isFieldRequired, isValueEmpty } from "@/utils/validation";
import AttachmentField from "@/components/fields/AttachmentField.vue";

interface Props {
  fields: FieldEntity[];
  record?: RecordEntity;
  readonly?: boolean;
  title?: string;
  description?: string;
  submitButtonText?: string;
  visibleFieldIds?: string[];
}

const props = withDefaults(defineProps<Props>(), {
  readonly: false,
  title: "",
  description: "",
  submitButtonText: "提交",
});

const emit = defineEmits<{
  (e: "submit", values: Record<string, CellValue>): void;
  (e: "cancel"): void;
}>();

const formValues = ref<Record<string, CellValue>>({});
const formErrors = ref<Record<string, string>>({});
const isSubmitting = ref(false);
const submitSuccess = ref(false);
const newRecordId = ref(generateId());

const visibleFields = computed(() => {
  // 首先过滤掉 isVisible 为 false 的字段
  let fields = props.fields.filter((f) => f.isVisible !== false);

  // 过滤掉 options.hidden 为 true 的字段
  fields = fields.filter((f) => !f.options?.hidden);

  // 如果指定了可见字段ID列表，则只显示这些字段
  if (props.visibleFieldIds && props.visibleFieldIds.length > 0) {
    fields = fields.filter((f) => props.visibleFieldIds?.includes(f.id));
  }

  // 过滤掉系统字段（创建人、创建时间、修改人、修改时间、自动编号）
  if (!props.readonly) {
    const systemFieldTypes: FieldTypeValue[] = [
      FieldType.CREATED_BY,
      FieldType.CREATED_TIME,
      FieldType.UPDATED_BY,
      FieldType.UPDATED_TIME,
      FieldType.AUTO_NUMBER,
    ];
    fields = fields.filter(
      (f) => !systemFieldTypes.includes(f.type as FieldTypeValue),
    );
  }

  return fields;
});

const isValid = computed(() => {
  return Object.keys(formErrors.value).length === 0;
});

const formTitle = computed(() => {
  return props.title || "数据收集表单";
});

watch(
  () => props.record,
  (newRecord) => {
    if (newRecord) {
      // 编辑模式：使用记录的值
      formValues.value = { ...newRecord.values };
    } else {
      // 新建模式：应用默认值
      resetForm();
    }
  },
  { immediate: true },
);

function validateField(field: FieldEntity, value: CellValue): string | null {
  // 必填验证 - 支持 field.isRequired 和 field.options.required
  if (isFieldRequired(field) && isValueEmpty(value)) {
    return `请填写必填字段：${field.name}`;
  }

  // 如果值为空且不是必填项，跳过其他验证
  if (value === null || value === undefined || value === "") {
    return null;
  }

  // 字段类型特定验证
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
        // 最小值验证
        if (
          field.options?.min !== undefined &&
          numValue < Number(field.options.min)
        ) {
          return `${field.name}不能小于${field.options.min}`;
        }
        // 最大值验证
        if (
          field.options?.max !== undefined &&
          numValue > Number(field.options.max)
        ) {
          return `${field.name}不能大于${field.options.max}`;
        }
      }
      break;
    case FieldType.TEXT:
    case FieldType.MULTI_SELECT:
      const strValue = String(value);
      // 最小长度验证
      if (
        field.options?.minLength !== undefined &&
        strValue.length < Number(field.options.minLength)
      ) {
        return `${field.name}至少需要${field.options.minLength}个字符`;
      }
      // 最大长度验证
      if (
        field.options?.maxLength !== undefined &&
        strValue.length > Number(field.options.maxLength)
      ) {
        return `${field.name}不能超过${field.options.maxLength}个字符`;
      }
      break;
  }

  // 自定义验证规则
  const validation = field.options?.validation as
    | { pattern?: string; message?: string }
    | undefined;
  if (validation?.pattern) {
    const pattern = new RegExp(validation.pattern);
    if (!pattern.test(String(value))) {
      return validation.message || `${field.name}格式不正确`;
    }
  }

  return null;
}

function handleFieldChange(fieldId: string, value: CellValue) {
  formValues.value[fieldId] = value;

  const field = props.fields.find((f) => f.id === fieldId);
  if (field) {
    const error = validateField(field, value);
    if (error) {
      formErrors.value[fieldId] = error;
    } else {
      delete formErrors.value[fieldId];
    }
  }
}

async function handleSubmit() {
  formErrors.value = {};

  // 只验证可见字段
  visibleFields.value.forEach((field) => {
    const error = validateField(field, formValues.value[field.id]);
    if (error) {
      formErrors.value[field.id] = error;
    }
  });

  if (Object.keys(formErrors.value).length === 0) {
    isSubmitting.value = true;
    try {
      emit("submit", { ...formValues.value });
      submitSuccess.value = true;

      // 如果不是编辑模式，提交成功后重置表单
      if (!props.record) {
        setTimeout(() => {
          resetForm();
          submitSuccess.value = false;
        }, 1500);
      }
    } finally {
      isSubmitting.value = false;
    }
  } else {
    // 显示第一个错误
    const firstError = Object.values(formErrors.value)[0];
    ElMessage.error(firstError);
  }
}

async function handleCancel() {
  // 如果有填写内容，确认是否放弃
  const hasValues = Object.values(formValues.value).some(
    (v) => v !== null && v !== undefined && v !== "" && v !== false,
  );

  if (hasValues && !props.readonly) {
    try {
      await ElMessageBox.confirm(
        "确定要取消吗？已填写的内容将不会保存。",
        "确认取消",
        {
          confirmButtonText: "确定",
          cancelButtonText: "继续填写",
          type: "warning",
        },
      );
      emit("cancel");
    } catch {
      // 用户选择继续填写
    }
  } else {
    emit("cancel");
  }
}

function resetForm() {
  formValues.value = {};
  formErrors.value = {};
  submitSuccess.value = false;
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

// 计算公式字段值
const calculateFormulaValue = (field: FieldEntity): string => {
  const formula = field.options?.formula as string;
  if (!formula) return "";

  try {
    const engine = new FormulaEngine(props.fields);
    // 构建当前记录对象
    const record: RecordEntity = {
      id: "temp",
      tableId: "",
      values: formValues.value,
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };
    const result = engine.calculate(record, formula);

    if (result === "#ERROR") {
      return "计算错误";
    }

    // 数字格式化
    if (typeof result === "number" && !isNaN(result)) {
      const precision = (field.options?.precision as number) ?? 2;
      return result.toLocaleString("zh-CN", {
        minimumFractionDigits: precision,
        maximumFractionDigits: precision,
      });
    }

    return String(result);
  } catch (error) {
    console.error("Form formula calculation error:", error);
    return "计算错误";
  }
};

// 监听表单值变化，重新计算公式字段
watch(
  formValues,
  () => {
    // 表单值变化时，公式字段会自动重新计算
    // 由于 calculateFormulaValue 在模板中调用，会响应式更新
  },
  { deep: true },
);

// 获取字段类型对应的组件类型
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
    case FieldType.FORMULA:
      return "formula";
    case FieldType.ATTACHMENT:
      return "attachment";
    default:
      return "text";
  }
}

// 获取单选/多选选项
function getSelectOptions(field: FieldEntity) {
  return (
    (field.options?.choices || field.options?.options) as Array<{
      id: string;
      name: string;
      color?: string;
    }> || []
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

  const field = props.fields.find((f) => f.id === fieldId);
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

// 导出表单数据为 JSON
function exportFormData() {
  const data = {
    title: formTitle.value,
    description: props.description,
    fields: visibleFields.value.map((f) => ({
      id: f.id,
      name: f.name,
      type: f.type,
      required: f.options?.required,
      options: f.options,
    })),
    values: { ...formValues.value },
  };

  const blob = new Blob([JSON.stringify(data, null, 2)], {
    type: "application/json",
  });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `form-data-${Date.now()}.json`;
  a.click();
  URL.revokeObjectURL(url);

  ElMessage.success("表单数据已导出");
}

defineExpose({
  resetForm,
  validate: () => isValid.value,
  getValues: () => ({ ...formValues.value }),
  exportFormData,
});
</script>

<template>
  <div class="form-view">
    <!-- 表单头部 -->
    <div class="form-header">
      <div class="form-header-icon">
        <el-icon><Document /></el-icon>
      </div>
      <h2 class="form-title">{{ formTitle }}</h2>
      <p v-if="description" class="form-description">{{ description }}</p>
    </div>

    <!-- 提交成功提示 -->
    <div v-if="submitSuccess" class="success-state">
      <div class="success-icon">
        <el-icon><CircleCheckFilled /></el-icon>
      </div>
      <h3 class="success-title">提交成功</h3>
      <p class="success-subtitle">您的数据已成功保存</p>
      <el-button type="primary" class="success-button" @click="resetForm">
        <el-icon><Plus /></el-icon>
        继续填写
      </el-button>
    </div>

    <!-- 空状态 -->
    <div v-else-if="visibleFields.length === 0" class="empty-state">
      <div class="empty-illustration">
        <el-icon><DocumentDelete /></el-icon>
      </div>
      <h3 class="empty-title">暂无可见字段</h3>
      <p class="empty-subtitle">
        当前没有可填写的字段，请在字段管理中配置表单字段
      </p>
    </div>

    <!-- 表单内容 -->
    <el-form
      v-else
      label-position="top"
      class="form-container"
      @submit.prevent="handleSubmit">
      <div class="form-card">
        <div
          v-for="field in visibleFields"
          :key="field.id"
          class="form-item"
          :class="{
            'has-error': formErrors[field.id],
            'is-readonly': readonly,
          }">
          <label class="form-label">
            {{ field.name }}
            <span
              v-if="field.options?.required && !readonly"
              class="required-mark"
              >*</span
            >
          </label>

          <div class="form-control">
            <!-- 文本类型 -->
            <template v-if="getFieldComponentType(field) === 'text'">
              <el-input
                :model-value="String(formValues[field.id] || '')"
                :placeholder="`请输入${field.name}`"
                :disabled="readonly"
                class="form-input"
                @update:model-value="(val) => handleFieldChange(field.id, val)">
                <template v-if="field.type === FieldType.EMAIL" #prefix>
                  <el-icon><Message /></el-icon>
                </template>
                <template v-else-if="field.type === FieldType.PHONE" #prefix>
                  <el-icon><Phone /></el-icon>
                </template>
                <template v-else-if="field.type === FieldType.URL" #prefix>
                  <el-icon><Link /></el-icon>
                </template>
              </el-input>
            </template>

            <!-- 数字类型 -->
            <template v-else-if="getFieldComponentType(field) === 'number'">
              <el-input-number
                :model-value="Number(formValues[field.id] || 0)"
                :placeholder="`请输入${field.name}`"
                :disabled="readonly"
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
                class="form-input-number"
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
                :disabled="readonly"
                class="form-select"
                clearable
                @update:model-value="(val) => handleFieldChange(field.id, val)">
                <el-option
                  v-for="option in getSelectOptions(field)"
                  :key="option.id"
                  :label="option.name"
                  :value="option.id">
                  <span
                    class="option-color"
                    :style="{ backgroundColor: option.color || '#3B82F6' }" />
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
                :disabled="readonly"
                class="form-select"
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
                    :style="{ backgroundColor: option.color || '#3B82F6' }" />
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
                :disabled="readonly"
                class="form-date-picker"
                @update:model-value="
                  (val) => handleDateChange(field.id, val as Date | null)
                " />
            </template>

            <!-- 复选框类型 -->
            <template v-else-if="getFieldComponentType(field) === 'checkbox'">
              <el-switch
                :model-value="Boolean(formValues[field.id])"
                :disabled="readonly"
                class="form-switch"
                @update:model-value="
                  (val) => handleFieldChange(field.id, val)
                " />
            </template>

            <!-- 公式字段类型 -->
            <template v-else-if="getFieldComponentType(field) === 'formula'">
              <div class="formula-field-display">
                <el-input
                  :model-value="calculateFormulaValue(field)"
                  disabled
                  class="formula-input"
                  :placeholder="'自动计算'">
                  <template #prefix>
                    <el-icon><Calculator /></el-icon>
                  </template>
                </el-input>
                <div v-if="field.options?.formula" class="formula-hint">
                  公式: {{ field.options.formula }}
                </div>
              </div>
            </template>

            <!-- 附件字段类型 -->
            <template v-else-if="getFieldComponentType(field) === 'attachment'">
              <AttachmentField
                :model-value="formValues[field.id]"
                :field="field"
                :record-id="props.record?.id || newRecordId"
                :readonly="readonly"
                @update:model-value="(val) => handleFieldValueChange(field.id, val)"
                @upload="(files) => handleAttachmentUpload(field.id, files)"
                @delete="(fileId) => handleAttachmentDelete(field.id, fileId)" />
            </template>
          </div>

          <div v-if="formErrors[field.id]" class="form-error">
            <el-icon><CircleCloseFilled /></el-icon>
            <span>{{ formErrors[field.id] }}</span>
          </div>

          <div
            v-if="field.options?.description && !readonly"
            class="form-field-description">
            <el-icon><InfoFilled /></el-icon>
            <span>{{ field.options.description }}</span>
          </div>
        </div>
      </div>

      <div v-if="!readonly" class="form-actions">
        <el-button class="cancel-button" @click="handleCancel">
          取消
        </el-button>
        <el-button
          type="primary"
          native-type="submit"
          :loading="isSubmitting"
          :disabled="!isValid && Object.keys(formErrors).length > 0"
          class="submit-button">
          <el-icon v-if="!isSubmitting"><Check /></el-icon>
          {{ submitButtonText }}
        </el-button>
      </div>
    </el-form>
  </div>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;

.form-view {
  width: 100%;
  max-width: 680px;
  margin: 0 auto;
  padding: $spacing-2xl;
  background: linear-gradient(180deg, $surface-color 0%, $gray-50 100%);
  border-radius: $border-radius-xl;
  box-shadow:
    0 4px 6px -1px rgba(0, 0, 0, 0.05),
    0 10px 20px -5px rgba(0, 0, 0, 0.03);
  transition: box-shadow 0.3s ease;

  &:hover {
    box-shadow:
      0 10px 15px -3px rgba(0, 0, 0, 0.08),
      0 20px 30px -5px rgba(0, 0, 0, 0.05);
  }
}

// 表单头部
.form-header {
  text-align: center;
  margin-bottom: $spacing-2xl;
  padding-bottom: $spacing-xl;
  border-bottom: 1px solid $gray-100;
}

.form-header-icon {
  width: 64px;
  height: 64px;
  margin: 0 auto $spacing-lg;
  background: linear-gradient(135deg, $primary-light 0%, $primary-color 100%);
  border-radius: $border-radius-xl;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 4px 12px rgba($primary-color, 0.25);

  .el-icon {
    font-size: 32px;
    color: $surface-color;
  }
}

.form-title {
  font-size: $font-size-2xl;
  font-weight: 700;
  color: $text-primary;
  margin: 0 0 $spacing-sm;
  letter-spacing: -0.5px;
}

.form-description {
  font-size: $font-size-base;
  color: $text-secondary;
  margin: 0;
  line-height: 1.6;
}

// 表单卡片
.form-card {
  background: $surface-color;
  border-radius: $border-radius-xl;
  padding: $spacing-xl;
  box-shadow:
    0 1px 3px rgba(0, 0, 0, 0.04),
    0 4px 8px rgba(0, 0, 0, 0.02);
  border: 1px solid $gray-100;
  transition: all 0.3s ease;

  &:hover {
    box-shadow:
      0 4px 12px rgba(0, 0, 0, 0.06),
      0 8px 16px rgba(0, 0, 0, 0.03);
    border-color: $gray-200;
  }
}

.form-container {
  display: flex;
  flex-direction: column;
  gap: $spacing-lg;
}

// 表单字段项
.form-item {
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
  padding: $spacing-md 0;
  border-bottom: 1px solid transparent;
  transition: all 0.2s ease;

  &:not(:last-child) {
    border-bottom-color: $gray-50;
  }

  &:hover {
    border-bottom-color: $gray-100;
  }

  &.has-error {
    .form-label {
      color: $error-color;
    }

    .form-control {
      :deep(.el-input__wrapper),
      :deep(.el-select__wrapper),
      :deep(.el-textarea__inner),
      :deep(.el-input-number__decrease),
      :deep(.el-input-number__increase) {
        border-color: $error-color;
        box-shadow: 0 0 0 3px rgba($error-color, 0.1);
      }
    }
  }

  &.is-readonly {
    .form-control {
      :deep(.el-input__wrapper),
      :deep(.el-select__wrapper) {
        background-color: $gray-50;
      }
    }
  }
}

// 字段标签
.form-label {
  font-size: $font-size-sm;
  font-weight: 600;
  color: $text-primary;
  display: flex;
  align-items: center;
  letter-spacing: 0.3px;
}

.required-mark {
  color: $error-color;
  margin-left: 4px;
  font-size: $font-size-base;
  font-weight: 700;
}

// 表单控件
.form-control {
  width: 100%;
}

// 输入框样式
.form-input,
.form-select,
.form-date-picker {
  width: 100%;

  :deep(.el-input__wrapper) {
    border-radius: $border-radius-lg;
    box-shadow:
      0 1px 2px rgba(0, 0, 0, 0.03),
      inset 0 1px 2px rgba(0, 0, 0, 0.02);
    border: 1px solid $gray-200;
    transition: all 0.2s ease;

    &:hover {
      border-color: $primary-hover;
      box-shadow:
        0 2px 4px rgba(0, 0, 0, 0.04),
        inset 0 1px 2px rgba(0, 0, 0, 0.02);
    }

    &.is-focus {
      border-color: $primary-color;
      box-shadow:
        0 0 0 3px rgba($primary-color, 0.1),
        0 2px 8px rgba($primary-color, 0.15);
    }
  }

  :deep(.el-input__inner) {
    height: 44px;
    font-size: $font-size-base;
    color: $text-primary;

    &::placeholder {
      color: $text-disabled;
    }
  }

  :deep(.el-input__prefix) {
    color: $text-secondary;
    margin-right: $spacing-sm;
  }
}

// 数字输入框
.form-input-number {
  width: 100%;

  :deep(.el-input__wrapper) {
    border-radius: $border-radius-lg;
    border: 1px solid $gray-200;
    box-shadow:
      0 1px 2px rgba(0, 0, 0, 0.03),
      inset 0 1px 2px rgba(0, 0, 0, 0.02);

    &:hover,
    &.is-focus {
      border-color: $primary-color;
      box-shadow:
        0 0 0 3px rgba($primary-color, 0.1),
        0 2px 8px rgba($primary-color, 0.15);
    }
  }

  :deep(.el-input-number__decrease),
  :deep(.el-input-number__increase) {
    border-radius: $border-radius-md;
    background: $gray-50;
    border-color: $gray-200;
    color: $text-secondary;
    transition: all 0.2s ease;

    &:hover {
      background: $primary-light;
      color: $primary-color;
      border-color: $primary-color;
    }
  }
}

// 下拉选择器
.form-select {
  :deep(.el-select__wrapper) {
    border-radius: $border-radius-lg;
    border: 1px solid $gray-200;
    box-shadow:
      0 1px 2px rgba(0, 0, 0, 0.03),
      inset 0 1px 2px rgba(0, 0, 0, 0.02);
    min-height: 44px;

    &:hover {
      border-color: $primary-hover;
    }

    &.is-focused {
      border-color: $primary-color;
      box-shadow:
        0 0 0 3px rgba($primary-color, 0.1),
        0 2px 8px rgba($primary-color, 0.15);
    }
  }

  :deep(.el-select__selection) {
    font-size: $font-size-base;
  }
}

// 日期选择器
.form-date-picker {
  :deep(.el-input__wrapper) {
    border-radius: $border-radius-lg;
  }

  :deep(.el-input__prefix) {
    color: $primary-color;
  }
}

// 开关样式
.form-switch {
  :deep(.el-switch__core) {
    border-radius: 12px;
    background-color: $gray-300;
    border-color: $gray-300;

    &.is-checked {
      background-color: $primary-color;
      border-color: $primary-color;
    }
  }

  :deep(.el-switch__action) {
    background-color: $surface-color;
    box-shadow: 0 2px 4px rgba(0, 0, 0, 0.15);
  }
}

// 错误提示
.form-error {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: $font-size-xs;
  color: $error-color;
  padding: $spacing-xs $spacing-sm;
  background: $error-light;
  border-radius: $border-radius-md;
  margin-top: $spacing-xs;

  .el-icon {
    font-size: 14px;
  }
}

// 字段描述
.form-field-description {
  display: flex;
  align-items: flex-start;
  gap: 6px;
  font-size: $font-size-xs;
  color: $text-secondary;
  line-height: 1.5;
  margin-top: $spacing-xs;

  .el-icon {
    font-size: 12px;
    color: $info-color;
    margin-top: 1px;
    flex-shrink: 0;
  }
}

// 表单操作按钮
.form-actions {
  display: flex;
  justify-content: flex-end;
  gap: $spacing-md;
  margin-top: $spacing-xl;
  padding-top: $spacing-xl;
  border-top: 1px solid $gray-100;
}

.cancel-button {
  height: 44px;
  padding: 0 $spacing-xl;
  border-radius: $border-radius-lg;
  font-weight: 500;
  color: $text-secondary;
  border-color: $gray-200;
  transition: all 0.2s ease;

  &:hover {
    color: $text-primary;
    border-color: $gray-300;
    background: $gray-50;
  }
}

.submit-button {
  height: 44px;
  padding: 0 $spacing-xl;
  border-radius: $border-radius-lg;
  font-weight: 600;
  background: linear-gradient(135deg, $primary-color 0%, $primary-dark 100%);
  border: none;
  box-shadow: 0 4px 12px rgba($primary-color, 0.35);
  transition: all 0.3s ease;

  &:hover:not(:disabled) {
    background: linear-gradient(135deg, $primary-hover 0%, $primary-color 100%);
    box-shadow: 0 6px 20px rgba($primary-color, 0.45);
    transform: translateY(-1px);
  }

  &:active:not(:disabled) {
    transform: translateY(0);
    box-shadow: 0 2px 8px rgba($primary-color, 0.35);
  }

  &:disabled {
    opacity: 0.6;
    cursor: not-allowed;
  }

  .el-icon {
    margin-right: 6px;
  }
}

// 主键字段样式
.primary-field-input {
  :deep(.el-input__wrapper) {
    background-color: $gray-50;
    border-color: $gray-200;

    .el-input__inner {
      color: $text-secondary;
      font-family: "SF Mono", Monaco, monospace;
    }
  }
}

.auto-filled-hint {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: $font-size-xs;
  color: $info-color;
  margin-top: $spacing-xs;

  .el-icon {
    font-size: 12px;
  }
}

// 选项颜色标记
.option-color {
  display: inline-block;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  margin-right: 8px;
  vertical-align: middle;
  box-shadow: inset 0 0 0 1px rgba(0, 0, 0, 0.1);
}

// 成功状态
.success-state {
  text-align: center;
  padding: $spacing-3xl $spacing-xl;
}

.success-icon {
  width: 80px;
  height: 80px;
  margin: 0 auto $spacing-lg;
  background: linear-gradient(135deg, $success-light 0%, $success-color 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: 0 8px 24px rgba($success-color, 0.3);
  animation: scaleIn 0.4s $ease-spring;

  .el-icon {
    font-size: 40px;
    color: $surface-color;
  }
}

.success-title {
  font-size: $font-size-xl;
  font-weight: 700;
  color: $text-primary;
  margin: 0 0 $spacing-sm;
}

.success-subtitle {
  font-size: $font-size-base;
  color: $text-secondary;
  margin: 0 0 $spacing-xl;
}

.success-button {
  height: 48px;
  padding: 0 $spacing-2xl;
  border-radius: $border-radius-lg;
  font-weight: 600;
  background: linear-gradient(135deg, $primary-color 0%, $primary-dark 100%);
  border: none;
  box-shadow: 0 4px 12px rgba($primary-color, 0.35);

  &:hover {
    box-shadow: 0 6px 20px rgba($primary-color, 0.45);
    transform: translateY(-1px);
  }
}

// 空状态
.empty-state {
  text-align: center;
  padding: $spacing-3xl $spacing-xl;
}

.empty-illustration {
  width: 120px;
  height: 120px;
  margin: 0 auto $spacing-lg;
  background: linear-gradient(135deg, $gray-50 0%, $gray-100 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  box-shadow: inset 0 2px 8px rgba(0, 0, 0, 0.05);

  .el-icon {
    font-size: 56px;
    color: $gray-300;
  }
}

.empty-title {
  font-size: $font-size-lg;
  font-weight: 600;
  color: $text-primary;
  margin: 0 0 $spacing-sm;
}

.empty-subtitle {
  font-size: $font-size-sm;
  color: $text-secondary;
  margin: 0;
  max-width: 280px;
  margin-left: auto;
  margin-right: auto;
  line-height: 1.6;
}

// 动画
@keyframes scaleIn {
  0% {
    transform: scale(0.5);
    opacity: 0;
  }
  50% {
    transform: scale(1.1);
  }
  100% {
    transform: scale(1);
    opacity: 1;
  }
}

// 公式字段样式
.formula-field-display {
  width: 100%;

  .formula-input {
    :deep(.el-input__wrapper) {
      background-color: $gray-50;
      border-color: $gray-200;

      .el-input__inner {
        color: $text-primary;
        font-family: "SF Mono", Monaco, monospace;
      }
    }

    :deep(.el-input__prefix) {
      color: $primary-color;
    }
  }

  .formula-hint {
    margin-top: 4px;
    font-size: $font-size-xs;
    color: $text-secondary;
    font-family: "SF Mono", Monaco, monospace;
  }
}

// 响应式适配
@media (max-width: 768px) {
  .form-view {
    padding: $spacing-lg;
    margin: $spacing-md;
    max-width: none;
  }

  .form-header-icon {
    width: 48px;
    height: 48px;

    .el-icon {
      font-size: 24px;
    }
  }

  .form-title {
    font-size: $font-size-xl;
  }

  .form-card {
    padding: $spacing-lg;
  }

  .form-actions {
    flex-direction: column-reverse;

    .el-button {
      width: 100%;
      height: 48px;
    }
  }
}
</style>
