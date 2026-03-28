<script setup lang="ts">
import { ref, watch, nextTick, computed } from "vue";
import {
  ElDialog,
  ElButton,
  ElInput,
  ElSelect,
  ElOption,
  ElForm,
  ElFormItem,
  ElSwitch,
  ElColorPicker,
  ElTag,
  ElMessage,
  ElSlider,
  ElIcon,
} from "element-plus";
import { fieldService } from "@/db/services/fieldService";
import {
  FieldType,
  getFieldTypeLabel,
  getFieldTypeIcon,
  type FieldTypeValue,
} from "@/types/fields";
import type { FieldEntity } from "@/db/schema";
import type { FieldOptions } from "@/types";
import Sortable from "sortablejs";
import { Rank } from "@element-plus/icons-vue";

const props = defineProps<{
  visible: boolean;
  tableId: string;
  fields: FieldEntity[];
}>();

const emit = defineEmits<{
  "update:visible": [value: boolean];
  "field-created": [field: FieldEntity];
  "field-updated": [field: FieldEntity];
  "field-deleted": [fieldId: string];
  "fields-reordered": [fieldIds: string[]];
}>();

const activeTab = ref<"list" | "create" | "edit">("list");
const editingField = ref<FieldEntity | null>(null);
const fieldListRef = ref<HTMLElement | null>(null);
let sortableInstance: Sortable | null = null;

// 按 order 排序后的字段列表
const sortedFields = computed(() => {
  return [...props.fields].sort((a, b) => a.order - b.order);
});

const newField = ref<{
  name: string;
  type: FieldTypeValue;
  isRequired: boolean;
  description: string;
  // 数值字段配置
  precision: number;
  // 日期字段配置
  showTime: boolean;
  // 公式字段配置
  formula: string;
}>({
  name: "",
  type: FieldType.TEXT,
  isRequired: false,
  description: "",
  precision: 0,
  showTime: false,
  formula: "",
});

const systemTypes = [
  FieldType.CREATED_BY,
  FieldType.CREATED_TIME,
  FieldType.UPDATED_BY,
  FieldType.UPDATED_TIME,
  FieldType.AUTO_NUMBER,
];
const fieldTypes = Object.values(FieldType).filter(
  (type): type is FieldTypeValue =>
    !systemTypes.includes(type as (typeof systemTypes)[number]),
);

const selectOptions = ref<{ id: string; name: string; color: string }[]>([]);
const newOptionName = ref("");
const newOptionColor = ref("#3370FF");

// 监听对话框显示，初始化拖拽排序
watch(
  () => props.visible,
  (visible) => {
    if (visible) {
      activeTab.value = "list";
      nextTick(() => {
        initSortable();
      });
    } else {
      destroySortable();
    }
  },
);

// 监听字段列表变化，重新初始化拖拽
watch(
  () => props.fields,
  () => {
    if (activeTab.value === "list" && props.visible) {
      nextTick(() => {
        initSortable();
      });
    }
  },
  { deep: true },
);

function initSortable() {
  if (sortableInstance) {
    sortableInstance.destroy();
  }

  if (fieldListRef.value) {
    sortableInstance = new Sortable(fieldListRef.value, {
      handle: ".drag-handle",
      animation: 150,
      onEnd: handleFieldDragEnd,
    });
  }
}

function destroySortable() {
  if (sortableInstance) {
    sortableInstance.destroy();
    sortableInstance = null;
  }
}

async function handleFieldDragEnd(evt: Sortable.SortableEvent) {
  if (evt.oldIndex === evt.newIndex) return;

  // 使用排序后的字段列表
  const currentSortedFields = [...sortedFields.value];
  const [movedField] = currentSortedFields.splice(evt.oldIndex!, 1);
  currentSortedFields.splice(evt.newIndex!, 0, movedField);

  const fieldIds = currentSortedFields.map((f) => f.id);

  try {
    await fieldService.reorderFields(props.tableId, fieldIds);
    emit("fields-reordered", fieldIds);
    ElMessage.success("字段排序已更新");
  } catch (error) {
    ElMessage.error("字段排序失败");
  }
}

function openCreateField() {
  activeTab.value = "create";
  newField.value = {
    name: "",
    type: FieldType.TEXT,
    isRequired: false,
    description: "",
    precision: 0,
    showTime: false,
    formula: "",
  };
  selectOptions.value = [];
}

function openEditField(field: FieldEntity) {
  editingField.value = field;
  activeTab.value = "edit";
  newField.value = {
    name: field.name,
    type: field.type as FieldTypeValue,
    isRequired: field.isRequired ?? false,
    description: field.description || "",
    precision: (field.options?.precision as number) ?? 0,
    showTime: (field.options?.showTime as boolean) ?? false,
    formula: (field.options?.formula as string) ?? "",
  };
  if (
    field.type === FieldType.SINGLE_SELECT ||
    field.type === FieldType.MULTI_SELECT
  ) {
    selectOptions.value =
      (field.options?.options as {
        id: string;
        name: string;
        color: string;
      }[]) || [];
  } else {
    selectOptions.value = [];
  }
}

function backToList() {
  activeTab.value = "list";
  editingField.value = null;
  newField.value = {
    name: "",
    type: FieldType.TEXT,
    isRequired: false,
    description: "",
    precision: 0,
    showTime: false,
    formula: "",
  };
  selectOptions.value = [];
}

async function createField() {
  if (!newField.value.name.trim()) {
    ElMessage.warning("请输入字段名称");
    return;
  }

  try {
    const options: FieldOptions = {};
    if (
      newField.value.type === FieldType.SINGLE_SELECT ||
      newField.value.type === FieldType.MULTI_SELECT
    ) {
      options.options = selectOptions.value.map((opt) => ({
        id: opt.id,
        name: opt.name,
        color: opt.color,
      }));
    }
    // 数值字段精度配置
    if (newField.value.type === FieldType.NUMBER) {
      options.precision = newField.value.precision;
    }
    // 日期字段时间显示配置
    if (newField.value.type === FieldType.DATE) {
      options.showTime = newField.value.showTime;
    }
    // 公式字段配置
    if (newField.value.type === FieldType.FORMULA) {
      options.formula = newField.value.formula;
      options.precision = newField.value.precision || 2;
    }

    const field = await fieldService.createField({
      tableId: props.tableId,
      name: newField.value.name.trim(),
      type: newField.value.type,
      isRequired: newField.value.isRequired,
      description: newField.value.description,
      options: Object.keys(options).length > 0 ? options : undefined,
    });

    emit("field-created", field);
    ElMessage.success("字段创建成功");
    backToList();
  } catch (error) {
    ElMessage.error(
      "字段创建失败: " + (error instanceof Error ? error.message : "未知错误"),
    );
  }
}

async function updateField() {
  if (!editingField.value) return;
  if (!newField.value.name.trim()) {
    ElMessage.warning("请输入字段名称");
    return;
  }

  try {
    const options: FieldOptions = { ...(editingField.value.options || {}) };
    if (
      newField.value.type === FieldType.SINGLE_SELECT ||
      newField.value.type === FieldType.MULTI_SELECT
    ) {
      options.options = selectOptions.value.map((opt) => ({
        id: opt.id,
        name: opt.name,
        color: opt.color,
      }));
    }
    // 数值字段精度配置
    if (newField.value.type === FieldType.NUMBER) {
      options.precision = newField.value.precision;
    }
    // 日期字段时间显示配置
    if (newField.value.type === FieldType.DATE) {
      options.showTime = newField.value.showTime;
    }
    // 公式字段配置
    if (newField.value.type === FieldType.FORMULA) {
      options.formula = newField.value.formula;
      options.precision = newField.value.precision || 2;
    }

    await fieldService.updateField(editingField.value.id, {
      name: newField.value.name.trim(),
      isRequired: newField.value.isRequired,
      description: newField.value.description,
      options: options as Record<string, unknown>,
    });

    const updatedField = {
      ...editingField.value,
      ...newField.value,
      options: options as Record<string, unknown>,
    };
    emit("field-updated", updatedField);
    ElMessage.success("字段更新成功");
    backToList();
  } catch (error) {
    ElMessage.error(
      "字段更新失败: " + (error instanceof Error ? error.message : "未知错误"),
    );
  }
}

async function deleteField(field: FieldEntity) {
  if (field.isSystem) {
    ElMessage.warning("系统字段不能删除");
    return;
  }

  try {
    await fieldService.deleteField(field.id);
    emit("field-deleted", field.id);
    ElMessage.success("字段删除成功");
  } catch (error) {
    ElMessage.error(
      "字段删除失败: " + (error instanceof Error ? error.message : "未知错误"),
    );
  }
}

function addOption() {
  if (!newOptionName.value.trim()) return;

  selectOptions.value.push({
    id: Date.now().toString(),
    name: newOptionName.value.trim(),
    color: newOptionColor.value,
  });
  newOptionName.value = "";
}

function removeOption(index: number) {
  selectOptions.value.splice(index, 1);
}

function onTypeChange() {
  if (
    newField.value.type !== FieldType.SINGLE_SELECT &&
    newField.value.type !== FieldType.MULTI_SELECT
  ) {
    selectOptions.value = [];
  }
  // 切换类型时重置特定配置
  if (newField.value.type !== FieldType.NUMBER && newField.value.type !== FieldType.FORMULA) {
    newField.value.precision = 0;
  }
  if (newField.value.type !== FieldType.DATE) {
    newField.value.showTime = false;
  }
  if (newField.value.type !== FieldType.FORMULA) {
    newField.value.formula = "";
  }
}

const presetColors = [
  "#3370FF",
  "#34D399",
  "#FBBF24",
  "#EF4444",
  "#8B5CF6",
  "#EC4899",
  "#14B8A6",
  "#F59E0B",
  "#6366F1",
  "#10B981",
];

// 可用于公式的字段（排除公式字段自身和某些系统字段）
const availableFieldsForFormula = computed(() => {
  return props.fields.filter((field) => {
    // 排除当前编辑的字段（避免循环引用）
    if (editingField.value && field.id === editingField.value.id) {
      return false;
    }
    // 排除某些系统字段
    if (
      field.type === FieldType.CREATED_BY ||
      field.type === FieldType.UPDATED_BY
    ) {
      return false;
    }
    return true;
  });
});

// 插入函数到公式
function insertFunction(funcName: string) {
  const formulaInput = document.querySelector(
    '.formula-field textarea, [placeholder*="公式"]'
  ) as HTMLTextAreaElement;
  if (formulaInput) {
    const start = formulaInput.selectionStart;
    const end = formulaInput.selectionEnd;
    const currentValue = newField.value.formula;
    const newValue =
      currentValue.substring(0, start) +
      funcName +
      "()" +
      currentValue.substring(end);
    newField.value.formula = newValue;
    // 将光标放在括号内
    nextTick(() => {
      formulaInput.focus();
      formulaInput.setSelectionRange(start + funcName.length + 1, start + funcName.length + 1);
    });
  } else {
    newField.value.formula += funcName + "()";
  }
}

// 插入字段引用到公式
function insertFieldRef(fieldName: string) {
  const formulaInput = document.querySelector(
    '.formula-field textarea, [placeholder*="公式"]'
  ) as HTMLTextAreaElement;
  const fieldRef = `{${fieldName}}`;
  if (formulaInput) {
    const start = formulaInput.selectionStart;
    const end = formulaInput.selectionEnd;
    const currentValue = newField.value.formula;
    const newValue =
      currentValue.substring(0, start) +
      fieldRef +
      currentValue.substring(end);
    newField.value.formula = newValue;
    nextTick(() => {
      formulaInput.focus();
      formulaInput.setSelectionRange(
        start + fieldRef.length,
        start + fieldRef.length
      );
    });
  } else {
    newField.value.formula += fieldRef;
  }
}

// 切换字段可见性
async function toggleFieldVisibility(field: FieldEntity, isVisible: boolean) {
  try {
    await fieldService.updateFieldVisibility(field.id, isVisible);
    // 不直接修改 prop，而是通过事件通知父组件更新
    emit('field-updated', { ...field, isVisible });
    ElMessage.success(isVisible ? '字段已显示' : '字段已隐藏');
  } catch (error) {
    ElMessage.error('更新字段可见性失败');
    // 发生错误时，让父组件重新加载数据以恢复状态
    emit('field-updated', { ...field, isVisible: field.isVisible });
  }
}
</script>

<template>
  <ElDialog
    :model-value="visible"
    @update:model-value="$emit('update:visible', $event)"
    title="字段管理"
    width="600px"
    :close-on-click-modal="false">
    <!-- 字段列表 -->
    <div v-if="activeTab === 'list'" class="field-list">
      <div class="field-list-header">
        <span class="field-count">共 {{ fields.length }} 个字段</span>
        <ElButton type="primary" size="small" @click="openCreateField">
          + 添加字段
        </ElButton>
      </div>

      <div ref="fieldListRef" class="field-items">
        <div
          v-for="field in sortedFields"
          :key="field.id"
          class="field-item"
          :class="{ 'is-system': field.isSystem }"
          :data-field-id="field.id">
          <div class="field-info">
            <span class="drag-handle" title="拖拽排序">
              <ElIcon><Rank /></ElIcon>
            </span>
            <span class="field-icon">{{ getFieldTypeIcon(field.type) }}</span>
            <span class="field-name">{{ field.name }}</span>
            <span class="field-type">{{ getFieldTypeLabel(field.type) }}</span>
            <ElTag v-if="field.isSystem" size="small" type="info">系统</ElTag>
            <ElTag v-if="field.isRequired" size="small" type="warning"
              >必填</ElTag
            >
          </div>
          <div class="field-actions">
            <ElSwitch
              :model-value="field.isVisible !== false"
              :active-value="true"
              :inactive-value="false"
              size="small"
              inline-prompt
              active-text="显示"
              inactive-text="隐藏"
              @change="(val) => toggleFieldVisibility(field, val as boolean)"
              style="margin-right: 8px"
            />
            <ElButton
              v-if="!field.isSystem"
              link
              type="primary"
              size="small"
              @click="openEditField(field)">
              编辑
            </ElButton>
            <ElButton
              v-if="!field.isSystem"
              link
              type="danger"
              size="small"
              @click="deleteField(field)">
              删除
            </ElButton>
          </div>
        </div>
      </div>
    </div>

    <!-- 创建/编辑字段 -->
    <div v-else class="field-form">
      <ElForm label-width="100px">
        <ElFormItem label="字段名称" required>
          <ElInput
            v-model="newField.name"
            placeholder="请输入字段名称"
            maxlength="50"
            show-word-limit />
        </ElFormItem>

        <ElFormItem label="字段类型" required>
          <ElSelect
            v-model="newField.type"
            style="width: 100%"
            @change="onTypeChange">
            <ElOption
              v-for="type in fieldTypes"
              :key="type"
              :label="getFieldTypeLabel(type)"
              :value="type">
              <span class="type-option">
                <span class="type-icon">{{ getFieldTypeIcon(type) }}</span>
                <span>{{ getFieldTypeLabel(type) }}</span>
              </span>
            </ElOption>
          </ElSelect>
        </ElFormItem>

        <!-- 数值字段精度配置 -->
        <ElFormItem v-if="newField.type === FieldType.NUMBER" label="小数位数">
          <div class="precision-config">
            <ElSlider
              v-model="newField.precision"
              :min="0"
              :max="10"
              :step="1"
              show-stops
              style="width: 300px" />
            <span class="precision-value">{{ newField.precision }} 位</span>
          </div>
          <div class="field-hint">设置数值显示的小数位数，默认为 0</div>
        </ElFormItem>

        <!-- 日期字段时间显示配置 -->
        <ElFormItem v-if="newField.type === FieldType.DATE" label="显示时间">
          <ElSwitch
            v-model="newField.showTime"
            active-text="YYYY-MM-DD HH:mm:ss"
            inactive-text="YYYY-MM-DD" />
          <div class="field-hint">开启后将显示日期和时间，关闭则仅显示日期</div>
        </ElFormItem>

        <!-- 公式字段配置 -->
        <template v-if="newField.type === FieldType.FORMULA">
          <ElFormItem label="公式表达式" required>
            <ElInput
              v-model="newField.formula"
              type="textarea"
              :rows="3"
              placeholder="输入公式，如: SUM({单价}, {数量}) 或 {单价} * {数量}"
              maxlength="500"
              show-word-limit />
            <div class="field-hint">
              使用 {字段名} 引用其他字段，支持数学、文本、日期、逻辑函数
            </div>
          </ElFormItem>

          <ElFormItem label="小数位数">
            <div class="precision-config">
              <ElSlider
                v-model="newField.precision"
                :min="0"
                :max="10"
                :step="1"
                show-stops
                style="width: 300px" />
              <span class="precision-value">{{ newField.precision || 2 }} 位</span>
            </div>
            <div class="field-hint">设置公式结果显示的小数位数，默认为 2</div>
          </ElFormItem>

          <ElFormItem label="可用函数">
            <div class="formula-functions">
              <div class="function-category">
                <div class="category-title">数学函数</div>
                <div class="function-list">
                  <ElTag
                    v-for="func in ['SUM', 'AVG', 'MAX', 'MIN', 'ROUND']"
                    :key="func"
                    size="small"
                    class="function-tag"
                    @click="insertFunction(func)">
                    {{ func }}
                  </ElTag>
                </div>
              </div>
              <div class="function-category">
                <div class="category-title">文本函数</div>
                <div class="function-list">
                  <ElTag
                    v-for="func in ['CONCAT', 'LEFT', 'LEN', 'UPPER']"
                    :key="func"
                    size="small"
                    class="function-tag"
                    @click="insertFunction(func)">
                    {{ func }}
                  </ElTag>
                </div>
              </div>
              <div class="function-category">
                <div class="category-title">日期函数</div>
                <div class="function-list">
                  <ElTag
                    v-for="func in ['TODAY', 'NOW', 'DATEDIF']"
                    :key="func"
                    size="small"
                    class="function-tag"
                    @click="insertFunction(func)">
                    {{ func }}
                  </ElTag>
                </div>
              </div>
              <div class="function-category">
                <div class="category-title">逻辑函数</div>
                <div class="function-list">
                  <ElTag
                    v-for="func in ['IF', 'AND', 'OR']"
                    :key="func"
                    size="small"
                    class="function-tag"
                    @click="insertFunction(func)">
                    {{ func }}
                  </ElTag>
                </div>
              </div>
            </div>
          </ElFormItem>

          <ElFormItem label="可用字段">
            <div class="formula-fields">
              <ElTag
                v-for="field in availableFieldsForFormula"
                :key="field.id"
                size="small"
                type="info"
                class="field-tag"
                @click="insertFieldRef(field.name)">
                {{ field.name }}
              </ElTag>
            </div>
          </ElFormItem>
        </template>

        <ElFormItem
          v-if="
            newField.type === FieldType.SINGLE_SELECT ||
            newField.type === FieldType.MULTI_SELECT
          "
          label="选项">
          <div class="options-editor">
            <div class="options-list">
              <div
                v-for="(option, index) in selectOptions"
                :key="option.id"
                class="option-item">
                <ElColorPicker
                  v-model="option.color"
                  size="small"
                  :predefine="presetColors" />
                <ElInput
                  v-model="option.name"
                  size="small"
                  placeholder="选项名称" />
                <ElButton
                  link
                  type="danger"
                  size="small"
                  @click="removeOption(index)">
                  删除
                </ElButton>
              </div>
            </div>
            <div class="add-option">
              <ElColorPicker
                v-model="newOptionColor"
                size="small"
                :predefine="presetColors" />
              <ElInput
                v-model="newOptionName"
                size="small"
                placeholder="输入选项名称，按回车添加"
                @keyup.enter="addOption" />
              <ElButton type="primary" size="small" @click="addOption"
                >添加</ElButton
              >
            </div>
          </div>
        </ElFormItem>

        <ElFormItem label="必填">
          <ElSwitch v-model="newField.isRequired" />
        </ElFormItem>

        <ElFormItem label="字段描述">
          <ElInput
            v-model="newField.description"
            type="textarea"
            :rows="2"
            placeholder="请输入字段描述（可选）" />
        </ElFormItem>
      </ElForm>

      <div class="form-actions">
        <ElButton @click="backToList">返回</ElButton>
        <ElButton
          type="primary"
          @click="activeTab === 'create' ? createField() : updateField()">
          {{ activeTab === "create" ? "创建" : "保存" }}
        </ElButton>
      </div>
    </div>
  </ElDialog>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;

.field-list {
  .field-list-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
    padding-bottom: 12px;
    border-bottom: 1px solid $border-color;

    .field-count {
      color: $text-secondary;
      font-size: $font-size-sm;
    }
  }

  .field-items {
    max-height: 400px;
    overflow-y: auto;
  }

  .field-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px;
    border-radius: $border-radius-md;
    transition: background-color 0.2s;

    &:hover {
      background-color: $bg-color;

      .drag-handle {
        opacity: 1;
      }
    }

    &.is-system {
      opacity: 0.7;
    }

    .field-info {
      display: flex;
      align-items: center;
      gap: 8px;

      .drag-handle {
        opacity: 0;
        cursor: grab;
        color: $text-secondary;
        transition: opacity 0.2s;
        display: flex;
        align-items: center;

        &:active {
          cursor: grabbing;
        }
      }

      .field-icon {
        font-size: 16px;
      }

      .field-name {
        font-weight: 500;
        color: $text-primary;
      }

      .field-type {
        font-size: $font-size-xs;
        color: $text-secondary;
        background: $bg-color;
        padding: 2px 6px;
        border-radius: $border-radius-sm;
      }
    }

    .field-actions {
      display: flex;
      gap: 8px;
    }
  }
}

.field-form {
  .type-option {
    display: flex;
    align-items: center;
    gap: 8px;

    .type-icon {
      font-size: 14px;
    }
  }

  .precision-config {
    display: flex;
    align-items: center;
    gap: 16px;
    .precision-value {
      min-width: 50px;
      color: $text-secondary;
      font-size: $font-size-sm;
    }
  }

  .field-hint {
    font-size: calc($font-size-xs * 0.85);
    color: $text-secondary;
    margin-top: 4px;
  }

  .options-editor {
    .options-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
      margin-bottom: 12px;
    }

    .option-item {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .add-option {
      display: flex;
      align-items: center;
      gap: 8px;
    }
  }

  .form-actions {
    display: flex;
    justify-content: flex-end;
    gap: 12px;
    margin-top: 24px;
    padding-top: 16px;
    border-top: 1px solid $border-color;
  }

  .formula-functions {
    display: flex;
    flex-direction: column;
    gap: 12px;

    .function-category {
      .category-title {
        font-size: $font-size-sm;
        color: $text-secondary;
        margin-bottom: 8px;
        font-weight: 500;
      }

      .function-list {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
      }

      .function-tag {
        cursor: pointer;
        transition: all 0.2s;

        &:hover {
          background-color: $primary-color;
          color: white;
        }
      }
    }
  }

  .formula-fields {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    max-height: 120px;
    overflow-y: auto;
    padding: 8px;
    background-color: $bg-color;
    border-radius: $border-radius-sm;

    .field-tag {
      cursor: pointer;
      transition: all 0.2s;

      &:hover {
        background-color: $primary-color;
        color: white;
      }
    }
  }
}
</style>
