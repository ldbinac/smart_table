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
} from "element-plus";
import type { FieldEntity } from "@/db/schema";
import { FieldType } from "@/types";
import { generateId } from "@/utils/id";
import dayjs from "dayjs";

const props = defineProps<{
  visible: boolean;
  fields: FieldEntity[];
  groupFieldId?: string;
  groupId?: string;
  groupName?: string;
  initialValues?: Record<string, unknown>;
}>();

const emit = defineEmits<{
  "update:visible": [value: boolean];
  save: [values: Record<string, unknown>];
}>();

const formData = ref<Record<string, unknown>>({});
const isSaving = ref(false);

// 获取主键字段
const primaryField = computed(() => {
  return props.fields.find((f) => f.isPrimary) || props.fields[0];
});

// 初始化表单数据
watch(
  () => props.visible,
  (isVisible) => {
    if (isVisible) {
      formData.value = {};

      // 为主键字段自动生成唯一ID
      if (primaryField.value) {
        formData.value[primaryField.value.id] = generateId();
      }

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

// 获取字段类型对应的组件
function getFieldComponent(field: FieldEntity) {
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
    case FieldType.CREATED_TIME:
    case FieldType.UPDATED_TIME:
      return "date";
    case FieldType.CHECKBOX:
      return "checkbox";
    default:
      return "text";
  }
}

// 获取单选/多选选项
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
  return getDateShowTime(field) ? 'YYYY-MM-DD HH:mm:ss' : 'YYYY-MM-DD';
}

// 获取日期选择器类型
function getDatePickerType(field: FieldEntity): 'date' | 'datetime' {
  return getDateShowTime(field) ? 'datetime' : 'date';
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
    formData.value[field.id] = dayjs(val).format('YYYY-MM-DD');
  }
}

// 检查字段是否已自动填充（分组字段）
function isAutoFilledField(field: FieldEntity): boolean {
  return props.groupFieldId === field.id && props.groupId !== "uncategorized";
}

// 检查字段是否为主键字段
function isPrimaryField(field: FieldEntity): boolean {
  return primaryField.value?.id === field.id;
}

// 保存记录
async function handleSave() {
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
        v-for="field in fields"
        :key="field.id"
        :label="field.name"
        :required="field.isRequired">
        <!-- 主键字段 - 自动生成ID且只读 -->
        <template v-if="isPrimaryField(field)">
          <ElInput
            :model-value="String(formData[field.id] || '')"
            disabled
            :placeholder="`自动生成${field.name}`" />
          <span class="auto-filled-hint">系统自动生成唯一标识，不可修改</span>
        </template>

        <!-- 自动填充的分组字段显示为只读 -->
        <template v-else-if="isAutoFilledField(field)">
          <ElSelect :model-value="groupId" style="width: 100%" disabled>
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
        <template v-else-if="getFieldComponent(field) === 'singleSelect'">
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
        <template v-else-if="getFieldComponent(field) === 'multiSelect'">
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

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>
