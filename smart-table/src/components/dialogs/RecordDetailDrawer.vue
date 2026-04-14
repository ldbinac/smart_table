<script setup lang="ts">
import { ref, watch, computed, onMounted } from "vue";
import {
  ElDrawer,
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
import { Clock } from "@element-plus/icons-vue";
import type { RecordEntity, FieldEntity } from "@/db/schema";
import { FieldType } from "@/types";
import dayjs from "dayjs";
import { FormulaEngine } from "@/utils/formula/engine";
import {
  validateRequiredFields,
  getRequiredFieldErrorMessage,
  validateFieldsFormat,
} from "@/utils/validation";
import type { CellValue } from "@/types";
import AttachmentField from "@/components/fields/AttachmentField.vue";
import RecordHistoryDrawer from "./RecordHistoryDrawer.vue";
import LinkField from "@/components/fields/LinkField/LinkField.vue";
import type { LinkedRecord } from "@/types/link";
import { linkApiService } from "@/services/api/linkApiService";

const props = defineProps<{
  visible: boolean;
  record: RecordEntity | null;
  fields: FieldEntity[];
  size?: string | number;
  readonly?: boolean;
}>();

const emit = defineEmits<{
  "update:visible": [value: boolean];
  save: [recordId: string, values: Record<string, unknown>];
}>();

const formData = ref<Record<string, unknown>>({});
const isSaving = ref(false);
const historyVisible = ref(false);

// 关联字段相关状态
const linkFieldRecords = ref<Map<string, LinkedRecord[]>>(new Map());
const linkFieldLoading = ref<Set<string>>(new Set());
const editingLinkField = ref<string | null>(null);

// 显示变更历史
const showHistory = () => {
  historyVisible.value = true;
};

// 获取关联字段配置
const getLinkFieldConfig = (field: FieldEntity) => {
  if (field.type !== FieldType.LINK) return null;
  const config = field.config as Record<string, unknown>;
  return {
    targetTableId: config?.linkedTableId as string,
    relationshipType:
      (config?.relationshipType as "one_to_one" | "one_to_many") ||
      "one_to_many",
    displayFieldId: config?.displayFieldId as string,
  };
};

// 加载关联记录详情
const loadLinkedRecords = async (field: FieldEntity) => {
  if (!props.record || field.type !== FieldType.LINK) return;

  const fieldId = field.id;
  const linkedIds = (formData.value[fieldId] as string[]) || [];

  if (linkedIds.length === 0) {
    linkFieldRecords.value.set(fieldId, []);
    return;
  }

  linkFieldLoading.value.add(fieldId);
  try {
    const links = await linkApiService.getRecordLinks(props.record.id);
    const fieldLinks = links.outbound.find((l) => l.field_id === fieldId);
    if (fieldLinks && fieldLinks.linked_records) {
      linkFieldRecords.value.set(
        fieldId,
        fieldLinks.linked_records.map((r) => ({
          record_id: r.record_id,
          display_value: r.display_value,
        })),
      );
    } else {
      linkFieldRecords.value.set(
        fieldId,
        linkedIds.map((id) => ({
          record_id: id,
          display_value: id,
        })),
      );
    }
  } catch (error) {
    console.error("[RecordDetailDrawer] 加载关联记录失败:", error);
    linkFieldRecords.value.set(
      fieldId,
      linkedIds.map((id) => ({
        record_id: id,
        display_value: id,
      })),
    );
  } finally {
    linkFieldLoading.value.delete(fieldId);
  }
};

// 获取关联记录数据
const getLinkedRecords = (field: FieldEntity): LinkedRecord[] => {
  return linkFieldRecords.value.get(field.id) || [];
};

// 处理关联字段编辑
const handleLinkFieldEdit = (fieldId: string) => {
  editingLinkField.value = fieldId;
};

// 处理关联字段值更新
const handleLinkFieldChange = async (
  field: FieldEntity,
  value: string[],
  records: LinkedRecord[],
) => {
  if (!props.record) return;

  try {
    await linkApiService.updateRecordLink(props.record.id, field.id, {
      target_record_ids: value,
    });
    formData.value[field.id] = value;
    linkFieldRecords.value.set(field.id, records);
    editingLinkField.value = null;
    ElMessage.success("关联字段更新成功");
  } catch (error) {
    console.error("[RecordDetailDrawer] 更新关联字段失败:", error);
    ElMessage.error("更新关联字段失败");
  }
};

// 加载所有关联字段数据
const loadAllLinkFields = async () => {
  if (!props.record) return;

  const linkFields = visibleFields.value.filter(
    (f) => f.type === FieldType.LINK,
  );
  for (const field of linkFields) {
    await loadLinkedRecords(field);
  }
};

// 监听记录变化，加载关联数据
watch(
  () => props.record,
  () => {
    linkFieldRecords.value.clear();
    loadAllLinkFields();
  },
  { immediate: true },
);

// 可见字段（用于显示）
const visibleFields = computed(() => {
  return props.fields.filter((f) => f.isVisible !== false);
});

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
  { immediate: true },
);

// 计算所有公式字段的值
const formulaValues = computed(() => {
  const values: Record<string, string> = {};
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
    const currentValues = { ...props.record?.values, ...currentFormData };

    const record: RecordEntity = {
      id: props.record?.id || "temp",
      tableId: props.record?.tableId || "",
      values: currentValues as Record<string, CellValue>,
      createdAt: props.record?.createdAt || Date.now(),
      updatedAt: Date.now(),
    };

    const formulaEngine = new FormulaEngine(props.fields);
    const result = formulaEngine.calculate(record, formula);

    return typeof result === "number" ? result.toString() : String(result);
  } catch (error) {
    console.error("Formula calculation error:", error);
    return "#ERROR";
  }
};

// 获取字段组件类型
const getFieldComponent = (field: FieldEntity): string => {
  switch (field.type) {
    case FieldType.TEXT:
    case FieldType.URL:
    case FieldType.EMAIL:
    case FieldType.PHONE:
      return "text";
    case FieldType.NUMBER:
      return "number";
    case FieldType.RATING:
      return "rating";
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
    case FieldType.LINK:
      return "link";
    case FieldType.PROGRESS:
    case FieldType.PERCENT:
      return "progress";
    default:
      return "text";
  }
};

// 处理值变更
function handleValueChange(fieldId: string, value: unknown) {
  formData.value[fieldId] = value;
}

// 获取评分最大值
function getMaxRating(field: FieldEntity): number {
  return (field.options?.maxRating as number) ?? 5;
}

// 处理附件上传
function handleAttachmentUpload(fieldId: string, newFiles: unknown[]) {
  const currentFiles = (formData.value[fieldId] as unknown[]) || [];
  const fileMap = new Map<string, unknown>();

  currentFiles.forEach((f) => {
    const file = f as { id: string };
    fileMap.set(file.id, f);
  });

  newFiles.forEach((f) => {
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
  formData.value[fieldId] = currentFiles.filter(
    (f: unknown) => (f as { id: string }).id !== fileId,
  );
}

// 获取主键字段
const primaryField = computed(() => {
  return props.fields.find((f) => f.isPrimary);
});

// 获取主键值
const primaryValue = computed(() => {
  if (!primaryField.value) return "";
  return formData.value[primaryField.value.id] || "";
});

// 保存记录
async function handleSave() {
  if (!props.record) return;

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
    emit("save", props.record.id, { ...formData.value });
    ElMessage.success("记录保存成功");
  } catch (error) {
    console.error("Error saving record:", error);
    ElMessage.error("保存失败");
  } finally {
    isSaving.value = false;
  }
}

// 关闭抽屉
function closeDrawer() {
  emit("update:visible", false);
}

// 获取抽屉标题
const drawerTitle = computed(() => {
  if (primaryField.value && primaryValue.value) {
    return `编辑记录 - ${primaryValue.value}`;
  }
  return "编辑记录";
});
</script>

<template>
  <el-drawer
    :model-value="visible"
    :title="drawerTitle"
    :size="size || '50%'"
    direction="rtl"
    :destroy-on-close="true"
    :close-on-click-modal="true"
    :modal="true"
    class="record-detail-drawer"
    @update:model-value="$emit('update:visible', $event)">
    <div v-if="record" class="drawer-content">
      <el-form label-position="top" class="record-form">
        <div v-for="field in visibleFields" :key="field.id" class="form-field">
          <label class="field-label">{{ field.name }}</label>

          <!-- 文本类型 -->
          <template v-if="getFieldComponent(field) === 'text'">
            <el-input
              :model-value="String(formData[field.id] || '')"
              @update:model-value="(val) => handleValueChange(field.id, val)"
              :placeholder="`请输入${field.name}`"
              :disabled="readonly"
              class="field-input" />
          </template>

          <!-- 数字类型 -->
          <template v-else-if="getFieldComponent(field) === 'number'">
            <el-input-number
              :model-value="Number(formData[field.id] || 0)"
              @update:model-value="(val) => handleValueChange(field.id, val)"
              :placeholder="`请输入${field.name}`"
              :disabled="readonly"
              class="field-input"
              style="width: 100%" />
          </template>

          <!-- 单选类型 -->
          <template v-else-if="getFieldComponent(field) === 'single_select'">
            <el-select
              :model-value="formData[field.id] as string"
              @update:model-value="(val) => handleValueChange(field.id, val)"
              :placeholder="`请选择${field.name}`"
              :disabled="readonly"
              class="field-input"
              style="width: 100%">
              <el-option
                v-for="option in field.options?.choices || []"
                :key="option.id"
                :label="option.name"
                :value="option.id">
                <div class="select-option">
                  <span
                    class="option-color"
                    :style="{ backgroundColor: option.color }"></span>
                  <span>{{ option.name }}</span>
                </div>
              </el-option>
            </el-select>
          </template>

          <!-- 多选类型 -->
          <template v-else-if="getFieldComponent(field) === 'multi_select'">
            <el-select
              :model-value="(formData[field.id] as string[]) || []"
              @update:model-value="(val) => handleValueChange(field.id, val)"
              :placeholder="`请选择${field.name}`"
              :disabled="readonly"
              multiple
              class="field-input"
              style="width: 100%">
              <el-option
                v-for="option in field.options?.choices || []"
                :key="option.id"
                :label="option.name"
                :value="option.id">
                <div class="select-option">
                  <span
                    class="option-color"
                    :style="{ backgroundColor: option.color }"></span>
                  <span>{{ option.name }}</span>
                </div>
              </el-option>
            </el-select>
          </template>

          <!-- 日期类型 -->
          <template v-else-if="getFieldComponent(field) === 'date'">
            <el-date-picker
              :model-value="
                formData[field.id]
                  ? dayjs(formData[field.id] as string).toDate()
                  : null
              "
              @update:model-value="
                (val) =>
                  handleValueChange(
                    field.id,
                    val ? dayjs(val).format('YYYY-MM-DD') : null,
                  )
              "
              type="date"
              :placeholder="`请选择${field.name}`"
              :disabled="readonly"
              class="field-input"
              style="width: 100%" />
          </template>

          <!-- 复选框类型 -->
          <template v-else-if="getFieldComponent(field) === 'checkbox'">
            <el-switch
              :model-value="Boolean(formData[field.id])"
              :disabled="readonly"
              @update:model-value="(val) => handleValueChange(field.id, val)" />
          </template>

          <!-- 进度字段类型 -->
          <template v-else-if="getFieldComponent(field) === 'progress'">
            <div class="progress-field">
              <el-slider
                :model-value="Number(formData[field.id] || 0)"
                :max="100"
                :disabled="readonly"
                :format-tooltip="(val: number) => `${val}%`"
                @update:model-value="
                  (val) => handleValueChange(field.id, val)
                " />
              <span class="progress-value">{{ formData[field.id] || 0 }}%</span>
            </div>
          </template>

          <!-- 评分字段类型 -->
          <template v-else-if="getFieldComponent(field) === 'rating'">
            <el-rate
              :model-value="Number(formData[field.id] || 0)"
              :max="getMaxRating(field)"
              :disabled="readonly"
              @update:model-value="(val) => handleValueChange(field.id, val)" />
          </template>

          <!-- 公式字段类型 -->
          <template v-else-if="getFieldComponent(field) === 'formula'">
            <div class="formula-field-wrapper">
              <el-input
                :model-value="formulaValues[field.id]"
                disabled
                :placeholder="field.name"
                class="formula-input">
                <template #prefix>
                  <el-icon class="formula-icon">
                    <span class="formula-icon-text">ƒ</span>
                  </el-icon>
                </template>
              </el-input>
              <div v-if="field.options?.formula" class="formula-expression">
                <span class="formula-label">公式:</span>
                <code class="formula-code">{{ field.options.formula }}</code>
              </div>
            </div>
          </template>

          <!-- 附件类型 -->
          <template v-else-if="getFieldComponent(field) === 'attachment'">
            <AttachmentField
              :model-value="formData[field.id] as CellValue"
              :field="field"
              :record-id="record.id"
              :readonly="readonly"
              @update:model-value="(val) => handleValueChange(field.id, val)"
              @upload="(files) => handleAttachmentUpload(field.id, files)"
              @delete="(fileId) => handleAttachmentDelete(field.id, fileId)" />
          </template>

          <!-- 关联字段类型 -->
          <template v-else-if="getFieldComponent(field) === 'link'">
            <LinkField
              :value="(formData[field.id] as string[]) || []"
              :linked-records="getLinkedRecords(field)"
              :target-table-id="getLinkFieldConfig(field)?.targetTableId"
              :display-field-id="getLinkFieldConfig(field)?.displayFieldId"
              :relationship-type="getLinkFieldConfig(field)?.relationshipType"
              :is-editing="editingLinkField === field.id"
              :readonly="readonly"
              @edit-start="handleLinkFieldEdit(field.id)"
              @update:value="
                (val) =>
                  handleLinkFieldChange(field, val, getLinkedRecords(field))
              "
              @change="
                (val, records) => handleLinkFieldChange(field, val, records)
              "
              @edit-end="editingLinkField = null" />
          </template>
        </div>
      </el-form>
    </div>

    <template #footer>
      <div class="drawer-footer">
        <el-button
          v-if="record?.id"
          :icon="Clock"
          circle
          title="变更历史"
          @click="showHistory" />
        <div class="footer-right">
          <el-button @click="closeDrawer">关闭</el-button>
          <el-button
            v-if="!readonly"
            type="primary"
            :loading="isSaving"
            @click="handleSave">
            保存
          </el-button>
        </div>
      </div>
    </template>
  </el-drawer>

  <!-- 变更历史抽屉 -->
  <RecordHistoryDrawer
    v-model="historyVisible"
    :record-id="record?.id"
    :fields="fields" />
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;

.drawer-content {
  padding: 0;
  height: calc(100% - 10px);
  overflow-y: auto;
}

.record-form {
  padding: 20px;
}

.form-field {
  margin-bottom: 20px;
}

.field-label {
  display: block;
  margin-bottom: 8px;
  font-size: 14px;
  font-weight: 500;
  color: $text-primary;
}

.field-input {
  width: 100%;
}

.select-option {
  display: flex;
  align-items: center;
  gap: 8px;
}

.option-color {
  width: 12px;
  height: 12px;
  border-radius: 2px;
}

.formula-field-wrapper {
  width: 100%;

  .formula-input {
    :deep(.el-input__wrapper) {
      background-color: #f5f7fa;

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
    background-color: #f5f7fa;
    border-radius: 4px;
    border-left: 3px solid $primary-color;
    display: flex;
    align-items: center;
    gap: 8px;

    .formula-label {
      font-size: 12px;
      color: $text-secondary;
      font-weight: 500;
      white-space: nowrap;
    }

    .formula-code {
      font-family: "SF Mono", Monaco, "Courier New", monospace;
      font-size: 12px;
      color: $text-primary;
      background-color: #e4e7ed;
      padding: 2px 6px;
      border-radius: 3px;
      word-break: break-all;
    }
  }
}

.progress-field {
  display: flex;
  align-items: center;
  gap: $spacing-sm;

  .el-slider {
    flex: 1;
  }

  .progress-value {
    font-size: $font-size-sm;
    color: $text-secondary;
    min-width: 40px;
    text-align: right;
  }
}

.drawer-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;

  .footer-right {
    display: flex;
    gap: 12px;
  }
}
</style>
