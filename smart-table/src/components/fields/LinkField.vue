<script setup lang="ts">
import { ref, computed, watch, onMounted } from "vue";
import { ElMessage } from "element-plus";
import { tableService } from "@/db/services/tableService";
import { fieldService } from "@/db/services/fieldService";
import { recordService } from "@/db/services/recordService";
import type { FieldEntity, RecordEntity, TableEntity } from "@/db/schema";
import type { CellValue } from "@/types";
import { Check, Link, ArrowRight } from "@element-plus/icons-vue";

interface Props {
  modelValue: CellValue;
  field: FieldEntity;
  readonly?: boolean;
  baseId?: string;
}

const props = withDefaults(defineProps<Props>(), {
  readonly: false,
});

const emit = defineEmits<{
  (e: "update:modelValue", value: CellValue): void;
}>();

// 关联表相关
const currentBaseId = ref<string>("");
const linkedTableId = ref<string>("");
const linkedFieldId = ref<string>("");
const linkedTables = ref<TableEntity[]>([]);
const linkedFields = ref<FieldEntity[]>([]);
const linkedRecords = ref<RecordEntity[]>([]);
const selectedRecords = ref<RecordEntity[]>([]);

// UI 状态
const visible = ref(false);
const searchQuery = ref("");
const loading = ref(false);
const recordLoading = ref(false);
const showRecordSelector = ref(false);

// 多对多关联
const isManyToMany = computed(() => {
  return props.field.options?.relationshipType === "many_to_many";
});

// 是否允许多选
const allowMultiple = computed(() => {
  return props.field.options?.allowMultiple !== false || isManyToMany.value;
});

// 显示字段 - 用于显示关联记录的哪个字段值
const displayField = computed(() => {
  const displayFieldId = props.field.options?.displayFieldId as string;
  if (displayFieldId) {
    return linkedFields.value.find((f) => f.id === displayFieldId);
  }
  // 默认使用主字段或第一个字段
  return linkedFields.value.find((f) => f.isPrimary) || linkedFields.value[0];
});

// 过滤后的记录
const filteredRecords = computed(() => {
  if (!searchQuery.value) return linkedRecords.value;
  const query = searchQuery.value.toLowerCase();
  const displayFieldValue = displayField.value;
  return linkedRecords.value.filter((record) => {
    const value = displayFieldValue
      ? record.values[displayFieldValue.id]
      : record.id;
    return String(value || "")
      .toLowerCase()
      .includes(query);
  });
});

// 已选记录的 ID 列表
const selectedRecordIds = computed(() => {
  return selectedRecords.value.map((r) => r.id);
});

// 获取当前表的基础 ID
async function loadCurrentBaseId() {
  if (props.baseId) {
    currentBaseId.value = props.baseId;
    return;
  }
  // 从当前字段的表获取基础 ID
  const field = await fieldService.getField(props.field.id);
  if (field) {
    const table = await tableService.getTable(field.tableId);
    if (table) {
      currentBaseId.value = table.baseId;
    }
  }
}

// 加载可关联的表列表
async function loadLinkedTables() {
  if (!currentBaseId.value) return;
  try {
    loading.value = true;
    linkedTables.value = await tableService.getTablesByBase(
      currentBaseId.value,
    );
  } catch (error) {
    console.error("加载关联表失败:", error);
    ElMessage.error("加载关联表失败");
  } finally {
    loading.value = false;
  }
}

// 加载关联表的数据（字段和记录）
async function loadLinkedTableData() {
  if (!linkedTableId.value) {
    linkedFields.value = [];
    linkedRecords.value = [];
    return;
  }

  try {
    recordLoading.value = true;
    // 加载字段
    linkedFields.value = await fieldService.getFieldsByTable(
      linkedTableId.value,
    );
    // 加载记录
    linkedRecords.value = await recordService.getRecordsByTable(
      linkedTableId.value,
    );
    // 更新已选记录
    updateSelectedRecordsFromModelValue();
  } catch (error) {
    console.error("加载关联表数据失败:", error);
    ElMessage.error("加载关联表数据失败");
  } finally {
    recordLoading.value = false;
  }
}

// 从 modelValue 更新已选记录
function updateSelectedRecordsFromModelValue() {
  const value = props.modelValue;
  if (!value) {
    selectedRecords.value = [];
    return;
  }

  if (Array.isArray(value)) {
    const ids = value.map((v) =>
      typeof v === "string" ? v : (v as { id: string }).id,
    );
    selectedRecords.value = linkedRecords.value.filter((r) =>
      ids.includes(r.id),
    );
  } else if (value && typeof value === "object" && "id" in value) {
    const id = (value as { id: string }).id;
    selectedRecords.value = linkedRecords.value.filter((r) => r.id === id);
  } else {
    selectedRecords.value = [];
  }
}

// 处理关联表变更
function handleTableChange(tableId: string) {
  linkedTableId.value = tableId;
  linkedFieldId.value = "";
  selectedRecords.value = [];
  emit("update:modelValue", allowMultiple.value ? [] : null);
  loadLinkedTableData();
}

// 处理显示字段变更
function handleDisplayFieldChange(fieldId: string) {
  linkedFieldId.value = fieldId;
}

// 检查记录是否已选中
function isSelected(record: RecordEntity): boolean {
  return selectedRecordIds.value.includes(record.id);
}

// 切换记录选中状态
function toggleRecord(record: RecordEntity) {
  if (props.readonly) return;

  if (allowMultiple.value) {
    const index = selectedRecords.value.findIndex((r) => r.id === record.id);
    if (index > -1) {
      selectedRecords.value.splice(index, 1);
    } else {
      selectedRecords.value.push(record);
    }
    emit(
      "update:modelValue",
      selectedRecords.value.map((r) => r.id),
    );
  } else {
    selectedRecords.value = [record];
    emit("update:modelValue", record.id);
    visible.value = false;
  }
}

// 移除已选记录
function removeRecord(recordId: string) {
  if (props.readonly) return;

  selectedRecords.value = selectedRecords.value.filter(
    (r) => r.id !== recordId,
  );
  if (allowMultiple.value) {
    emit(
      "update:modelValue",
      selectedRecords.value.map((r) => r.id),
    );
  } else {
    emit("update:modelValue", null);
  }
}

// 获取记录的显示值
function getRecordDisplayValue(record: RecordEntity): string {
  if (!displayField.value) return record.id;
  const value = record.values[displayField.value.id];
  return value !== undefined && value !== null ? String(value) : "无标题";
}

// 打开记录选择器
function openRecordSelector() {
  if (props.readonly) return;
  showRecordSelector.value = true;
  searchQuery.value = "";
  loadLinkedTableData();
}

// 关闭记录选择器
function closeRecordSelector() {
  showRecordSelector.value = false;
}

// 确认选择
function confirmSelection() {
  if (allowMultiple.value) {
    emit(
      "update:modelValue",
      selectedRecords.value.map((r) => r.id),
    );
  } else {
    emit("update:modelValue", selectedRecords.value[0]?.id || null);
  }
  closeRecordSelector();
}

// 监听字段选项变化
watch(
  () => props.field.options,
  async (options) => {
    if (options?.linkedTableId) {
      linkedTableId.value = options.linkedTableId as string;
      await loadLinkedTableData();
    }
    if (options?.linkedFieldId) {
      linkedFieldId.value = options.linkedFieldId as string;
    }
  },
  { immediate: true, deep: true },
);

// 监听 modelValue 变化
watch(
  () => props.modelValue,
  () => {
    updateSelectedRecordsFromModelValue();
  },
  { immediate: true },
);

onMounted(async () => {
  await loadCurrentBaseId();
  await loadLinkedTables();
});
</script>

<template>
  <div class="link-field">
    <!-- 只读模式 -->
    <div v-if="readonly" class="link-display">
      <el-tag
        v-for="record in selectedRecords"
        :key="record.id"
        size="small"
        class="link-tag"
        type="primary">
        <el-icon class="link-icon"><Link /></el-icon>
        {{ getRecordDisplayValue(record) }}
      </el-tag>
      <span v-if="selectedRecords.length === 0" class="empty-text">-</span>
    </div>

    <!-- 编辑模式 -->
    <div v-else class="link-editor">
      <!-- 已选记录展示 -->
      <div class="selected-records" @click="openRecordSelector">
        <el-tag
          v-for="record in selectedRecords"
          :key="record.id"
          size="small"
          closable
          class="link-tag"
          type="primary"
          @close.stop="removeRecord(record.id)">
          <el-icon class="link-icon"><Link /></el-icon>
          {{ getRecordDisplayValue(record) }}
        </el-tag>
        <span v-if="selectedRecords.length === 0" class="placeholder">
          <el-icon><Link /></el-icon>
          选择关联记录
        </span>
        <el-icon class="arrow-icon"><ArrowRight /></el-icon>
      </div>

      <!-- 记录选择弹窗 -->
      <el-dialog
        v-model="showRecordSelector"
        title="选择关联记录"
        width="600px"
        destroy-on-close
        class="link-record-dialog">
        <div class="dialog-content">
          <!-- 关联表选择 -->
          <div class="section">
            <label class="section-label">关联数据表</label>
            <el-select
              v-model="linkedTableId"
              placeholder="选择关联表"
              size="default"
              class="table-select"
              @change="handleTableChange">
              <el-option
                v-for="table in linkedTables"
                :key="table.id"
                :label="table.name"
                :value="table.id">
                <span>{{ table.name }}</span>
                <span class="record-count"
                  >({{ table.recordCount }} 条记录)</span
                >
              </el-option>
            </el-select>
          </div>

          <!-- 显示字段选择 -->
          <div v-if="linkedFields.length > 0" class="section">
            <label class="section-label">显示字段</label>
            <el-select
              v-model="linkedFieldId"
              placeholder="选择显示字段"
              size="default"
              class="field-select"
              @change="handleDisplayFieldChange">
              <el-option
                v-for="field in linkedFields"
                :key="field.id"
                :label="field.name"
                :value="field.id">
                <span>{{ field.name }}</span>
                <span v-if="field.isPrimary" class="primary-badge">主字段</span>
              </el-option>
            </el-select>
          </div>

          <!-- 记录搜索和列表 -->
          <div v-if="linkedTableId" class="section">
            <label class="section-label">
              选择记录
              <span v-if="allowMultiple" class="multi-hint">（可多选）</span>
            </label>
            <el-input
              v-model="searchQuery"
              placeholder="搜索记录"
              prefix-icon="Search"
              size="default"
              clearable
              class="search-input" />

            <div v-loading="recordLoading" class="record-list-container">
              <div v-if="filteredRecords.length > 0" class="record-list">
                <div
                  v-for="record in filteredRecords"
                  :key="record.id"
                  class="record-item"
                  :class="{ selected: isSelected(record) }"
                  @click="toggleRecord(record)">
                  <div class="record-checkbox">
                    <el-checkbox :model-value="isSelected(record)" />
                  </div>
                  <div class="record-info">
                    <span class="record-name">{{
                      getRecordDisplayValue(record)
                    }}</span>
                    <span class="record-id"
                      >ID: {{ record.id.slice(0, 8) }}...</span
                    >
                  </div>
                  <el-icon v-if="isSelected(record)" class="check-icon">
                    <Check />
                  </el-icon>
                </div>
              </div>
              <div v-else class="no-records">
                <el-empty description="暂无记录" :image-size="60" />
              </div>
            </div>
          </div>

          <!-- 未选择表时的提示 -->
          <div v-else class="no-table-hint">
            <el-empty description="请先选择关联的数据表" :image-size="80" />
          </div>
        </div>

        <template #footer>
          <div class="dialog-footer">
            <span class="selected-count">
              已选择 {{ selectedRecords.length }} 条记录
            </span>
            <div class="footer-actions">
              <el-button @click="closeRecordSelector">取消</el-button>
              <el-button type="primary" @click="confirmSelection">
                确认
              </el-button>
            </div>
          </div>
        </template>
      </el-dialog>
    </div>
  </div>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;

.link-field {
  width: 100%;
}

// 只读模式
.link-display {
  display: flex;
  flex-wrap: wrap;
  gap: $spacing-xs;
  min-height: 32px;
  align-items: center;

  .link-tag {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    max-width: 200px;
    overflow: hidden;
    text-overflow: ellipsis;

    .link-icon {
      font-size: 12px;
    }
  }

  .empty-text {
    color: $text-disabled;
    font-size: $font-size-sm;
  }
}

// 编辑模式
.link-editor {
  width: 100%;
}

.selected-records {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: $spacing-xs;
  min-height: 32px;
  padding: $spacing-xs $spacing-sm;
  border: 1px solid $border-color;
  border-radius: $border-radius-sm;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    border-color: $primary-color;
  }

  .link-tag {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    max-width: 200px;
    overflow: hidden;
    text-overflow: ellipsis;

    .link-icon {
      font-size: 12px;
    }
  }

  .placeholder {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    color: $text-disabled;
    font-size: $font-size-sm;
  }

  .arrow-icon {
    margin-left: auto;
    color: $text-secondary;
    font-size: 14px;
  }
}

// 弹窗内容
:deep(.link-record-dialog) {
  .el-dialog__body {
    padding: $spacing-md;
  }
}

.dialog-content {
  display: flex;
  flex-direction: column;
  gap: $spacing-lg;
}

.section {
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
}

.section-label {
  font-size: $font-size-sm;
  font-weight: 500;
  color: $text-primary;

  .multi-hint {
    color: $text-secondary;
    font-weight: normal;
  }
}

.table-select,
.field-select {
  width: 100%;
}

.record-count {
  margin-left: auto;
  color: $text-secondary;
  font-size: $font-size-xs;
}

.primary-badge {
  margin-left: auto;
  padding: 2px 6px;
  background-color: $primary-color;
  color: white;
  font-size: $font-size-xs;
  border-radius: $border-radius-sm;
}

.search-input {
  width: 100%;
}

.record-list-container {
  min-height: 200px;
  max-height: 300px;
  overflow-y: auto;
  border: 1px solid $border-color;
  border-radius: $border-radius-sm;
}

.record-list {
  padding: $spacing-xs;
}

.record-item {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  padding: $spacing-sm;
  border-radius: $border-radius-sm;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    background-color: rgba($primary-color, 0.05);
  }

  &.selected {
    background-color: rgba($primary-color, 0.1);
  }

  .record-checkbox {
    flex-shrink: 0;
  }

  .record-info {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 0;

    .record-name {
      font-size: $font-size-sm;
      color: $text-primary;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .record-id {
      font-size: $font-size-xs;
      color: $text-secondary;
    }
  }

  .check-icon {
    color: $primary-color;
    font-size: 16px;
  }
}

.no-records,
.no-table-hint {
  padding: $spacing-xl 0;
}

.dialog-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;

  .selected-count {
    font-size: $font-size-sm;
    color: $text-secondary;
  }

  .footer-actions {
    display: flex;
    gap: $spacing-sm;
  }
}
</style>
