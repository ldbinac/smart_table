<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { useI18n } from "vue-i18n";
import type { FieldEntity } from "@/db/schema";
import { ElMessage } from "element-plus";
import { getFieldTypeLabel } from "@/types/fields";

interface FormConfig {
  title: string;
  description: string;
  submitButtonText: string;
  visibleFieldIds: string[];
  successMessage: string;
  allowMultipleSubmit: boolean;
}

interface Props {
  visible: boolean;
  fields: FieldEntity[];
  initialConfig?: Partial<FormConfig>;
}

const props = withDefaults(defineProps<Props>(), {
  initialConfig: () => ({}),
});

const emit = defineEmits<{
  (e: "update:visible", value: boolean): void;
  (e: "save", config: FormConfig): void;
}>();

const { t } = useI18n();

// 表单配置
const config = ref<FormConfig>({
  title: t("view.formDefaultTitle"),
  description: "",
  submitButtonText: t("view.formSubmit"),
  visibleFieldIds: [],
  successMessage: t("view.formSuccessMessage"),
  allowMultipleSubmit: true,
});

// 初始化配置
watch(
  () => props.visible,
  (visible) => {
    if (visible) {
      // 检查是否明确设置了 visibleFieldIds（包括空数组的情况）
      const hasVisibleFieldIds =
        props.initialConfig &&
        "visibleFieldIds" in props.initialConfig &&
        Array.isArray(props.initialConfig.visibleFieldIds);

      config.value = {
        title: props.initialConfig?.title || t("view.formDefaultTitle"),
        description: props.initialConfig?.description || "",
        submitButtonText: props.initialConfig?.submitButtonText || t("view.formSubmit"),
        visibleFieldIds: hasVisibleFieldIds
          ? props.initialConfig!.visibleFieldIds!
          : props.fields.map((f) => f.id),
        successMessage:
          props.initialConfig?.successMessage || t("view.formSuccessMessage"),
        allowMultipleSubmit: props.initialConfig?.allowMultipleSubmit !== false,
      };
    }
  },
);

// 过滤掉系统字段
const availableFields = computed(() => {
  const systemFieldTypes = [
    "createdBy",
    "createdTime",
    "updatedBy",
    "updatedTime",
    "autoNumber",
  ];
  return props.fields.filter((f) => !systemFieldTypes.includes(f.type));
});

// 全选状态
const isAllSelected = computed(() => {
  return (
    availableFields.value.length > 0 &&
    config.value.visibleFieldIds.length === availableFields.value.length
  );
});

// 半选状态
const isIndeterminate = computed(() => {
  return (
    config.value.visibleFieldIds.length > 0 &&
    config.value.visibleFieldIds.length < availableFields.value.length
  );
});

// 处理全选
function handleCheckAllChange(val: boolean) {
  config.value.visibleFieldIds = val
    ? availableFields.value.map((f) => f.id)
    : [];
}

// 保存配置
function handleSave() {
  if (!config.value.title.trim()) {
    ElMessage.error(t("view.formEnterTitle"));
    return;
  }

  if (config.value.visibleFieldIds.length === 0) {
    ElMessage.error(t("view.formSelectAtLeastOneField"));
    return;
  }

  emit("save", { ...config.value });
  emit("update:visible", false);
  ElMessage.success(t("view.formConfigSaved"));
}

// 取消
function handleCancel() {
  emit("update:visible", false);
}

// 字段排序（上移）
function moveFieldUp(index: number) {
  if (index === 0) return;
  const fieldId = config.value.visibleFieldIds[index];
  config.value.visibleFieldIds.splice(index, 1);
  config.value.visibleFieldIds.splice(index - 1, 0, fieldId);
}

// 字段排序（下移）
function moveFieldDown(index: number) {
  if (index === config.value.visibleFieldIds.length - 1) return;
  const fieldId = config.value.visibleFieldIds[index];
  config.value.visibleFieldIds.splice(index, 1);
  config.value.visibleFieldIds.splice(index + 1, 0, fieldId);
}

// 获取字段名称
function getFieldName(fieldId: string): string {
  const field = props.fields.find((f) => f.id === fieldId);
  return field?.name || fieldId;
}

// 获取字段类型标签

</script>

<template>
  <el-dialog
    :model-value="visible"
    @update:model-value="$emit('update:visible', $event)"
    :title="t('view.formConfigTitle')"
    width="600px"
    :close-on-click-modal="false">
    <el-form label-position="top" class="form-config">
      <!-- 基本信息 -->
      <div class="config-section">
        <h4 class="section-title">{{ t("view.formBasicInfo") }}</h4>

        <el-form-item :label="t('view.formConfigTitleLabel')">
          <el-input
            v-model="config.title"
            :placeholder="t('view.formTitlePlaceholder')"
            maxlength="50"
            show-word-limit />
        </el-form-item>

        <el-form-item :label="t('view.formDescriptionLabel')">
          <el-input
            v-model="config.description"
            type="textarea"
            :rows="3"
            :placeholder="t('view.formDescriptionPlaceholder')"
            maxlength="200"
            show-word-limit />
        </el-form-item>

        <el-form-item :label="t('view.formSubmitButtonLabel')">
          <el-input
            v-model="config.submitButtonText"
            :placeholder="t('view.formSubmitButtonPlaceholder')"
            maxlength="10" />
        </el-form-item>

        <el-form-item :label="t('view.formSuccessMessageLabel')">
          <el-input
            v-model="config.successMessage"
            :placeholder="t('view.formSuccessMessagePlaceholder')"
            maxlength="100" />
        </el-form-item>

        <el-form-item>
          <el-checkbox v-model="config.allowMultipleSubmit">
            {{ t("view.formAllowMultiple") }}
          </el-checkbox>
        </el-form-item>
      </div>

      <!-- 字段选择 -->
      <div class="config-section">
        <h4 class="section-title">{{ t("view.formFieldConfig") }}</h4>

        <div class="field-select-header">
          <el-checkbox
            :model-value="isAllSelected"
            :indeterminate="isIndeterminate"
            @change="(val) => handleCheckAllChange(val as boolean)">
            {{ t("view.selectAll") }}
          </el-checkbox>
          <span class="field-count">
            {{ t("view.fieldsSelected", { count: config.visibleFieldIds.length }) }}
          </span>
        </div>

        <el-divider />

        <div class="field-list">
          <el-checkbox-group v-model="config.visibleFieldIds">
            <div
              v-for="(fieldId, index) in config.visibleFieldIds"
              :key="fieldId"
              class="field-item selected">
              <el-checkbox :label="fieldId">
                {{ getFieldName(fieldId) }}
              </el-checkbox>
              <div class="field-actions">
                <el-button
                  link
                  type="primary"
                  :disabled="index === 0"
                  @click="moveFieldUp(index)">
                  <el-icon><ArrowUp /></el-icon>
                </el-button>
                <el-button
                  link
                  type="primary"
                  :disabled="index === config.visibleFieldIds.length - 1"
                  @click="moveFieldDown(index)">
                  <el-icon><ArrowDown /></el-icon>
                </el-button>
              </div>
            </div>

            <el-divider v-if="config.visibleFieldIds.length > 0" />

            <div
              v-for="field in availableFields.filter(
                (f) => !config.visibleFieldIds.includes(f.id),
              )"
              :key="field.id"
              class="field-item">
              <el-checkbox :label="field.id">
                {{ field.name }}
              </el-checkbox>
              <el-tag size="small" type="info">
                {{ getFieldTypeLabel(field.type) }}
              </el-tag>
            </div>
          </el-checkbox-group>

          <el-empty
            v-if="availableFields.length === 0"
            :description="t('view.noAvailableFields')" />
        </div>
      </div>
    </el-form>

    <template #footer>
      <el-button @click="handleCancel">{{ t("view.cancel") }}</el-button>
      <el-button type="primary" @click="handleSave">{{ t("view.saveConfig") }}</el-button>
    </template>
  </el-dialog>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;

.form-config {
  max-height: 60vh;
  overflow-y: auto;
}

.config-section {
  margin-bottom: $spacing-lg;

  &:last-child {
    margin-bottom: 0;
  }
}

.section-title {
  font-size: $font-size-base;
  font-weight: 600;
  color: $text-primary;
  margin: 0 0 $spacing-md;
  padding-bottom: $spacing-sm;
  border-bottom: 1px solid $border-color;
}

.field-select-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: $spacing-sm 0;
}

.field-count {
  font-size: $font-size-sm;
  color: $text-secondary;
}

.field-list {
  .el-checkbox-group {
    display: flex;
    flex-direction: column;
    gap: $spacing-sm;
  }
}

.field-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: $spacing-sm;
  border-radius: $border-radius-sm;
  transition: background-color 0.2s;

  &:hover {
    background-color: $bg-color;
  }

  &.selected {
    background-color: rgba($primary-color, 0.05);
  }

  .el-checkbox {
    flex: 1;
  }
}

.field-actions {
  display: flex;
  gap: $spacing-xs;
}

:deep(.el-divider) {
  margin: $spacing-sm 0;
}
</style>
