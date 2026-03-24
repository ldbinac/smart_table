<script setup lang="ts">
import { ref, watch } from "vue";
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
import type { RecordEntity, FieldEntity } from "@/db/schema";
import { FieldType } from "@/types";

const props = defineProps<{
  visible: boolean;
  record: RecordEntity | null;
  fields: FieldEntity[];
}>();

const emit = defineEmits<{
  "update:visible": [value: boolean];
  "save": [recordId: string, values: Record<string, unknown>];
}>();

const formData = ref<Record<string, unknown>>({});
const isSaving = ref(false);

// 初始化表单数据
watch(
  () => props.record,
  (newRecord) => {
    if (newRecord) {
      formData.value = { ...newRecord.values };
    } else {
      formData.value = {};
    }
  },
  { immediate: true }
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
  return (field.options?.options as Array<{ id: string; name: string; color?: string }>) || [];
}

// 保存记录
async function handleSave() {
  if (!props.record) return;

  isSaving.value = true;
  try {
    emit("save", props.record.id, { ...formData.value });
    ElMessage.success("记录保存成功");
    closeDialog();
  } catch (error) {
    ElMessage.error("保存失败");
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
    title="编辑记录"
    width="600px"
    :close-on-click-modal="false"
  >
    <ElForm label-width="100px" class="record-form">
      <ElFormItem
        v-for="field in fields"
        :key="field.id"
        :label="field.name"
        :required="field.isRequired"
      >
        <!-- 文本类型 -->
        <template v-if="getFieldComponent(field) === 'text'">
          <ElInput
            :model-value="String(formData[field.id] || '')"
            :placeholder="`请输入${field.name}`"
            @update:model-value="(val) => handleValueChange(field.id, val)"
          />
        </template>

        <!-- 数字类型 -->
        <template v-else-if="getFieldComponent(field) === 'number'">
          <ElInputNumber
            :model-value="Number(formData[field.id] || 0)"
            :placeholder="`请输入${field.name}`"
            style="width: 100%"
            @update:model-value="(val) => handleValueChange(field.id, val)"
          />
        </template>

        <!-- 单选类型 -->
        <template v-else-if="getFieldComponent(field) === 'singleSelect'">
          <ElSelect
            :model-value="formData[field.id] as string | undefined"
            :placeholder="`请选择${field.name}`"
            style="width: 100%"
            clearable
            @update:model-value="(val) => handleValueChange(field.id, val)"
          >
            <ElOption
              v-for="option in getSelectOptions(field)"
              :key="option.id"
              :label="option.name"
              :value="option.id"
            >
              <span
                class="option-color"
                :style="{ backgroundColor: option.color || '#3370FF' }"
              />
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
            @update:model-value="(val) => handleValueChange(field.id, val)"
          >
            <ElOption
              v-for="option in getSelectOptions(field)"
              :key="option.id"
              :label="option.name"
              :value="option.id"
            >
              <span
                class="option-color"
                :style="{ backgroundColor: option.color || '#3370FF' }"
              />
              <span>{{ option.name }}</span>
            </ElOption>
          </ElSelect>
        </template>

        <!-- 日期类型 -->
        <template v-else-if="getFieldComponent(field) === 'date'">
          <ElDatePicker
            :model-value="formData[field.id] as number | undefined"
            type="datetime"
            :placeholder="`请选择${field.name}`"
            style="width: 100%"
            value-format="x"
            @update:model-value="(val) => handleValueChange(field.id, val)"
          />
        </template>

        <!-- 复选框类型 -->
        <template v-else-if="getFieldComponent(field) === 'checkbox'">
          <ElSwitch
            :model-value="Boolean(formData[field.id])"
            @update:model-value="(val) => handleValueChange(field.id, val)"
          />
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

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>
