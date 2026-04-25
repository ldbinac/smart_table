<script setup lang="ts">
import { ref, watch, computed } from "vue";
import {
  ElDialog,
  ElButton,
  ElForm,
  ElFormItem,
  ElInput,
  ElInputNumber,
  ElSelect,
  ElOption,
  ElDatePicker,
  ElSwitch,
  ElMessage,
  ElRate,
  ElSlider,
  ElIcon,
} from "element-plus";
import type { FieldEntity, RecordEntity } from "@/db/schema";
import { FieldType } from "@/types";
import { generateId } from "@/utils/id";
import dayjs from "dayjs";
import { FormulaEngine } from "@/utils/formula/engine";
import {
  validateRequiredFields,
  getRequiredFieldErrorMessage,
  validateFieldsFormat,
} from "@/utils/validation";
import type { CellValue } from "@/types";
import AttachmentField from "@/components/fields/AttachmentField.vue";

interface GroupLevelInfo {
  fieldId: string;
  fieldName: string;
  value: string;
  valueId?: string;
}

const props = defineProps<{
  visible: boolean;
  fields: FieldEntity[];
  groupFieldId?: string;
  groupId?: string;
  groupName?: string;
  groupLevels?: GroupLevelInfo[];
  initialValues?: Record<string, unknown>;
}>();

const emit = defineEmits<{
  "update:visible": [value: boolean];
  save: [values: Record<string, unknown>];
}>();

const formData = ref<Record<string, unknown>>({});
const isSaving = ref(false);
const newRecordId = ref(generateId());

// 可见字段（用于显示）
const visibleFields = computed(() => {
  return props.fields.filter((f) => f.isVisible !== false);
});

// 初始化表单数据
watch(
  () => props.visible,
  (isVisible) => {
    if (isVisible) {
      formData.value = {};

      // 如果有分组信息，自动填充分组字段
      if (
        props.groupFieldId &&
        props.groupId &&
        props.groupId !== "uncategorized"
      ) {
        formData.value[props.groupFieldId] = props.groupId;
      }

      // 应用传入的初始值（如日历视图的日期）
      if (props.initialValues) {
        Object.keys(props.initialValues).forEach((key) => {
          formData.value[key] = props.initialValues![key];
        });
      }
    }
  },
  { immediate: true },
);

// 计算所有公式字段的值 - 使用 computed 确保响应式更新
const formulaValues = computed(() => {
  const values: Record<string, string> = {};

  // 依赖 formData.value，确保表单数据变化时重新计算
  const currentFormData = formData.value;

  props.fields.forEach((field) => {
    if (field.type === FieldType.FORMULA) {
      values[field.id] = calculateFormulaValue(field, currentFormData);
    }
  });

  return values;
});

// 计算公式字段值
const calculateFormulaValue = (
  field: FieldEntity,
  currentFormData: Record<string, unknown> = formData.value,
): string => {
  const formula = field.options?.formula as string;
  if (!formula) return "";

  try {
    // 构建当前记录对象
    const record: RecordEntity = {
      id: "temp",
      tableId: "",
      values: currentFormData as Record<string, import("@/types").CellValue>,
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };

    const engine = new FormulaEngine(props.fields);
    const result = engine.calculate(record, formula);

    if (result === "#ERROR") {
      return "计算错误";
    }

    // 数字格式化
    if (typeof result === "number") {
      const precision = (field.options?.precision as number) ?? 2;
      return result.toLocaleString("zh-CN", {
        minimumFractionDigits: precision,
        maximumFractionDigits: precision,
      });
    }

    return String(result);
  } catch (error) {
    console.error("Add record dialog formula calculation error:", error);
    return "计算错误";
  }
};

// 获取字段类型对应的组件
function getFieldComponent(field: FieldEntity) {
  switch (field.type) {
    case FieldType.SINGLE_LINE_TEXT:
    case FieldType.LONG_TEXT:
    case FieldType.RICH_TEXT:
    case FieldType.URL:
    case FieldType.EMAIL:
    case FieldType.PHONE:
      return "text";
    case FieldType.NUMBER:
      return "number";
    case FieldType.SINGLE_SELECT:
      return "single_select";
    case FieldType.MULTI_SELECT:
      return "multi_select";
    case FieldType.DATE:
    case FieldType.CREATED_TIME:
    case FieldType.UPDATED_TIME:
      return "date";
    case FieldType.CHECKBOX:
      return "checkbox";
    case FieldType.RATING:
      return "rating";
    case FieldType.PROGRESS:
      return "progress";
    case FieldType.ATTACHMENT:
      return "attachment";
    case FieldType.MEMBER:
      return "member";
    case FieldType.AUTO_NUMBER:
      return "autoNumber";
    case FieldType.FORMULA:
      return "formula";
    case FieldType.LINK:
      return "link";
    case FieldType.LOOKUP:
      return "lookup";
    case FieldType.CREATED_BY:
    case FieldType.UPDATED_BY:
      return "readonly";
    default:
      return "text";
  }
}

// 检查字段是否为只读字段（系统字段、公式字段等）
function isReadonlyField(field: FieldEntity): boolean {
  return (
    [
      FieldType.FORMULA,
      FieldType.LOOKUP,
      FieldType.CREATED_BY,
      FieldType.CREATED_TIME,
      FieldType.UPDATED_BY,
      FieldType.UPDATED_TIME,
      FieldType.AUTO_NUMBER,
    ].includes(field.type as any) || field.isSystem
  );
}

// 获取单选/多选选项
function getSelectOptions(field: FieldEntity) {
  // 后端返回的格式是 {choices: [...]}
  const choices = (field.options?.choices as Array<{
    id: string;
    name: string;
    color?: string;
  }>) || [];
  return choices;
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

// 获取评分最大值
function getMaxRating(field: FieldEntity): number {
  return (field.options?.maxRating as number) ?? 5;
}

// 处理日期变更
function handleDateChange(field: FieldEntity, val: Date | null) {
  if (!val) {
    formData.value[field.id] = null;
    return;
  }

  const showTime = getDateShowTime(field);
  if (showTime) {
    // 显示时间时存储为时间戳
    formData.value[field.id] = val.getTime();
  } else {
    // 仅日期时存储为日期字符串
    formData.value[field.id] = dayjs(val).format("YYYY-MM-DD");
  }
}

// 检查字段是否已自动填充（分组字段）
function isAutoFilledField(field: FieldEntity): boolean {
  // 优先使用 groupLevels（多层分组）
  if (props.groupLevels && props.groupLevels.length > 0) {
    return props.groupLevels.some(
      (level) =>
        level.fieldId === field.id &&
        level.valueId &&
        level.valueId !== "uncategorized"
    );
  }
  // 兼容旧版单层分组
  return props.groupFieldId === field.id && props.groupId !== "uncategorized";
}

// 获取字段的自动填充值
function getAutoFilledValue(field: FieldEntity): string | undefined {
  // 优先使用 groupLevels（多层分组）
  if (props.groupLevels && props.groupLevels.length > 0) {
    const level = props.groupLevels.find((l) => l.fieldId === field.id);
    return level?.valueId;
  }
  // 兼容旧版单层分组
  return props.groupId;
}

// 获取只读字段的显示值
function getReadonlyDisplayValue(field: FieldEntity): string {
  const value = formData.value[field.id];
  if (value === null || value === undefined) return "";

  switch (field.type) {
    case FieldType.CREATED_TIME:
    case FieldType.UPDATED_TIME:
      if (typeof value === "number") {
        return dayjs(value).format("YYYY-MM-DD HH:mm:ss");
      }
      return String(value);
    case FieldType.CREATED_BY:
    case FieldType.UPDATED_BY:
      return String(value);
    case FieldType.AUTO_NUMBER:
      return String(value);
    default:
      return String(value);
  }
}

// 保存记录
async function handleSave() {
  // 1. 验证必填字段
  const validation = validateRequiredFields(
    visibleFields.value,
    formData.value as Record<string, CellValue>,
  );

  if (!validation.valid) {
    const errorMessage = getRequiredFieldErrorMessage(validation.errors);
    ElMessage.error(errorMessage);
    return;
  }

  // 2. 验证字段格式（EMAIL、PHONE、URL）
  const formatErrors = validateFieldsFormat(
    visibleFields.value,
    formData.value as Record<string, CellValue>,
  );

  if (formatErrors.length > 0) {
    const errorMessage = formatErrors.map((e) => e.message).join("；");
    ElMessage.error(errorMessage);
    return;
  }

  isSaving.value = true;
  try {
    emit("save", { ...formData.value });
    ElMessage.success("记录添加成功");
    closeDialog();
  } catch (error) {
    ElMessage.error("添加失败");
  } finally {
    isSaving.value = false;
  }
}

// 关闭对话框
function closeDialog() {
  emit("update:visible", false);
}

// 处理值变更
function handleValueChange(fieldId: string, value: unknown) {
  formData.value[fieldId] = value;
}

// 处理附件上传
function handleAttachmentUpload(fieldId: string, newFiles: unknown[]) {
  // 附件已经通过 AttachmentField 组件上传到 IndexedDB
  // 这里只需要更新表单数据中的附件元数据
  // 使用 Map 去重，避免重复添加相同 ID 的文件
  const currentFiles = (formData.value[fieldId] as unknown[]) || [];
  const fileMap = new Map<string, unknown>();
  
  // 添加现有文件
  currentFiles.forEach(f => {
    const file = f as { id: string };
    fileMap.set(file.id, f);
  });
  
  // 添加新文件（如果 ID 不存在）
  newFiles.forEach(f => {
    const file = f as { id: string };
    if (!fileMap.has(file.id)) {
      fileMap.set(file.id, f);
    }
  });
  
  formData.value[fieldId] = Array.from(fileMap.values());
}

// 处理附件删除
function handleAttachmentDelete(fieldId: string, fileId: string) {
  const currentFiles = (formData.value[fieldId] as unknown[]) || [];
  formData.value[fieldId] = currentFiles.filter((f: unknown) => (f as { id: string }).id !== fileId);
}
</script>

<template>
  <ElDialog
    :model-value="visible"
    @update:model-value="$emit('update:visible', $event)"
    :title="groupName ? '添加记录到 ' + groupName : '添加记录'"
    width="600px"
    :close-on-click-modal="false">
    <ElForm label-width="100px" class="record-form">
      <ElFormItem
        v-for="field in visibleFields"
        :key="field.id"
        :label="field.name"
        :required="
          field.isRequired &&
          !isReadonlyField(field) &&
          !isAutoFilledField(field)
        ">
        <!-- 只读字段（系统字段、公式字段等） -->
        <template v-if="isReadonlyField(field)">
          <template v-if="field.type === FieldType.FORMULA">
            <div class="formula-field-wrapper">
              <ElInput
                :model-value="formulaValues[field.id]"
                disabled
                :placeholder="field.name"
                class="formula-input">
                <template #prefix>
                  <ElIcon class="formula-icon"
                    ><span class="formula-icon-text">ƒ</span></ElIcon
                  >
                </template>
              </ElInput>
              <div v-if="field.options?.formula" class="formula-expression">
                <span class="formula-label">公式:</span>
                <code class="formula-code">{{ field.options.formula }}</code>
              </div>
            </div>
          </template>
          <template v-else>
            <ElInput
              :model-value="getReadonlyDisplayValue(field)"
              disabled
              :placeholder="field.name" />
          </template>
          <span class="auto-filled-hint">{{
            field.type === FieldType.FORMULA
              ? "公式计算字段，不可修改"
              : field.type === FieldType.LOOKUP
                ? "查找字段，不可修改"
                : field.type === FieldType.AUTO_NUMBER
                  ? "自动编号，不可修改"
                  : "系统字段，不可修改"
          }}</span>
        </template>

        <!-- 自动填充的分组字段显示为只读 -->
        <template v-else-if="isAutoFilledField(field)">
          <ElSelect
            :model-value="getAutoFilledValue(field)"
            style="width: 100%"
            disabled>
            <ElOption
              v-for="option in getSelectOptions(field)"
              :key="option.id"
              :label="option.name"
              :value="option.id" />
          </ElSelect>
          <span class="auto-filled-hint">已自动关联当前分组</span>
        </template>

        <!-- 文本类型 -->
        <template v-else-if="getFieldComponent(field) === 'text'">
          <ElInput
            :model-value="String(formData[field.id] || '')"
            :placeholder="`请输入${field.name}`"
            @update:model-value="(val) => handleValueChange(field.id, val)" />
        </template>

        <!-- 数字类型 -->
        <template v-else-if="getFieldComponent(field) === 'number'">
          <ElInputNumber
            :model-value="Number(formData[field.id] || 0)"
            :precision="getNumberPrecision(field)"
            :placeholder="`请输入${field.name}`"
            style="width: 100%"
            @update:model-value="(val) => handleValueChange(field.id, val)" />
        </template>

        <!-- 单选类型 -->
        <template v-else-if="getFieldComponent(field) === 'single_select'">
          <ElSelect
            :model-value="formData[field.id] as string | undefined"
            :placeholder="`请选择${field.name}`"
            style="width: 100%"
            clearable
            @update:model-value="(val) => handleValueChange(field.id, val)">
            <ElOption
              v-for="option in getSelectOptions(field)"
              :key="option.id"
              :label="option.name"
              :value="option.id">
              <span
                class="option-color"
                :style="{ backgroundColor: option.color || '#3370FF' }" />
              <span>{{ option.name }}</span>
            </ElOption>
          </ElSelect>
        </template>

        <!-- 多选类型 -->
        <template v-else-if="getFieldComponent(field) === 'multi_select'">
          <ElSelect
            :model-value="(formData[field.id] as string[]) || []"
            :placeholder="`请选择${field.name}`"
            style="width: 100%"
            multiple
            clearable
            @update:model-value="(val) => handleValueChange(field.id, val)">
            <ElOption
              v-for="option in getSelectOptions(field)"
              :key="option.id"
              :label="option.name"
              :value="option.id">
              <span
                class="option-color"
                :style="{ backgroundColor: option.color || '#3370FF' }" />
              <span>{{ option.name }}</span>
            </ElOption>
          </ElSelect>
        </template>

        <!-- 日期类型 -->
        <template v-else-if="getFieldComponent(field) === 'date'">
          <ElDatePicker
            :model-value="formData[field.id] as Date | undefined"
            :type="getDatePickerType(field)"
            :placeholder="`请选择${field.name}`"
            :format="getDateFormat(field)"
            style="width: 100%"
            @update:model-value="(val) => handleDateChange(field, val)" />
        </template>

        <!-- 复选框类型 -->
        <template v-else-if="getFieldComponent(field) === 'checkbox'">
          <ElSwitch
            :model-value="Boolean(formData[field.id])"
            @update:model-value="(val) => handleValueChange(field.id, val)" />
        </template>

        <!-- 评分类型 -->
        <template v-else-if="getFieldComponent(field) === 'rating'">
          <ElRate
            :model-value="Number(formData[field.id] || 0)"
            :max="getMaxRating(field)"
            @update:model-value="(val) => handleValueChange(field.id, val)" />
        </template>

        <!-- 进度类型 -->
        <template v-else-if="getFieldComponent(field) === 'progress'">
          <ElSlider
            :model-value="Number(formData[field.id] || 0)"
            :max="100"
            :format-tooltip="(val: number) => `${val}%`"
            @update:model-value="(val) => handleValueChange(field.id, val)" />
          <span class="progress-value">{{ formData[field.id] || 0 }}%</span>
        </template>

        <!-- 附件类型 -->
        <template v-else-if="getFieldComponent(field) === 'attachment'">
          <AttachmentField
            :model-value="formData[field.id] as CellValue"
            :field="field"
            :record-id="newRecordId"
            @update:model-value="(val) => handleValueChange(field.id, val)"
            @upload="(files) => handleAttachmentUpload(field.id, files)"
            @delete="(fileId) => handleAttachmentDelete(field.id, fileId)" />
        </template>

        <!-- 成员类型 -->
        <template v-else-if="getFieldComponent(field) === 'member'">
          <ElSelect
            :model-value="formData[field.id] as string | undefined"
            :placeholder="`请选择${field.name}`"
            style="width: 100%"
            clearable
            @update:model-value="(val) => handleValueChange(field.id, val)">
            <ElOption label="当前用户" value="current_user" />
          </ElSelect>
        </template>

        <!-- 关联类型 -->
        <template v-else-if="getFieldComponent(field) === 'link'">
          <div class="link-hint">
            <el-icon><Link /></el-icon>
            <span>关联字段请在详情页中编辑</span>
          </div>
        </template>

        <!-- 默认文本类型 -->
        <template v-else>
          <ElInput
            :model-value="String(formData[field.id] || '')"
            :placeholder="`请输入${field.name}`"
            @update:model-value="(val) => handleValueChange(field.id, val)" />
        </template>
      </ElFormItem>
    </ElForm>

    <template #footer>
      <span class="dialog-footer">
        <ElButton @click="closeDialog">取消</ElButton>
        <ElButton type="primary" :loading="isSaving" @click="handleSave">
          保存
        </ElButton>
      </span>
    </template>
  </ElDialog>
</template>

<script lang="ts">
import { Document, Link } from "@element-plus/icons-vue";
export default {
  name: "AddRecordDialog",
};
</script>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;

.record-form {
  max-height: 500px;
  overflow-y: auto;
  padding-right: 10px;
}

.option-color {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  margin-right: 8px;
  vertical-align: middle;
}

.auto-filled-hint {
  font-size: $font-size-xs;
  color: $text-secondary;
  margin-top: 4px;
  display: block;
}

.progress-value {
  font-size: $font-size-sm;
  color: $text-secondary;
  margin-left: 8px;
}

.attachment-hint,
.link-hint {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 12px;
  background-color: $bg-color;
  border-radius: $border-radius-sm;
  color: $text-secondary;
  font-size: $font-size-sm;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

// 公式字段样式
.formula-field-wrapper {
  width: 100%;

  .formula-input {
    :deep(.el-input__wrapper) {
      background-color: $gray-50;

      .el-input__inner {
        color: $text-primary;
        font-family: "SF Mono", Monaco, "Courier New", monospace;
        font-weight: 500;
      }
    }

    .formula-icon {
      color: $primary-color;
      font-size: 16px;
      display: flex;
      align-items: center;
      justify-content: center;

      .formula-icon-text {
        font-family: "Times New Roman", serif;
        font-style: italic;
        font-weight: bold;
        font-size: 14px;
      }
    }
  }

  .formula-expression {
    margin-top: 6px;
    padding: 6px 10px;
    background-color: $gray-50;
    border-radius: $border-radius-sm;
    border-left: 3px solid $primary-color;
    display: flex;
    align-items: center;
    gap: 8px;

    .formula-label {
      font-size: $font-size-xs;
      color: $text-secondary;
      font-weight: 500;
      white-space: nowrap;
    }

    .formula-code {
      font-family: "SF Mono", Monaco, "Courier New", monospace;
      font-size: $font-size-xs;
      color: $text-primary;
      background-color: $gray-100;
      padding: 2px 6px;
      border-radius: 3px;
      word-break: break-all;
    }
  }
}
</style>
