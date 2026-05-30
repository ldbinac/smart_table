<script setup lang="ts">
import { ref, computed, watch, onMounted } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Link, ArrowRight, Close, Search, Check } from "@element-plus/icons-vue";
import { tableService } from "@/db/services/tableService";
import { fieldService } from "@/db/services/fieldService";
import { recordService } from "@/db/services/recordService";
import { recordApiService } from "@/services/api/recordApiService";
import { linkApiService } from "@/services/api/linkApiService";
import type { FieldEntity, RecordEntity, TableEntity } from "@/db/schema";
import type { CellValue } from "@/types";
import RecordDetailDrawer from "@/components/dialogs/RecordDetailDrawer.vue";

interface Props {
  modelValue: CellValue;
  field: FieldEntity;
  readonly?: boolean;
  baseId?: string;
  record?: RecordEntity;
}

const props = withDefaults(defineProps<Props>(), {
  readonly: false,
});

const emit = defineEmits<{
  (e: "update:modelValue", value: CellValue): void;
}>();

const MAX_DISPLAY_COUNT = 3;

const linkedTableId = ref<string>("");
const linkedTables = ref<TableEntity[]>([]);
const linkedFields = ref<FieldEntity[]>([]);
const linkedRecords = ref<RecordEntity[]>([]);
const selectedRecords = ref<RecordEntity[]>([]);

const searchQuery = ref("");
const loading = ref(false);
const recordLoading = ref(false);
const showRecordSelector = ref(false);
const deleting = ref(false);

const displayField = computed(() => {
  const displayFieldId = props.field.config?.displayFieldId as string;
  if (displayFieldId) {
    return linkedFields.value.find((f) => f.id === displayFieldId);
  }
  return linkedFields.value.find((f) => f.isPrimary) || linkedFields.value[0];
});

const displayRecords = computed(() => {
  return selectedRecords.value.slice(0, MAX_DISPLAY_COUNT);
});

const hasMoreRecords = computed(() => {
  return selectedRecords.value.length > MAX_DISPLAY_COUNT;
});

const hiddenRecordCount = computed(() => {
  return selectedRecords.value.length - MAX_DISPLAY_COUNT;
});

const filteredRecords = computed(() => {
  if (!searchQuery.value) return linkedRecords.value;
  const query = searchQuery.value.toLowerCase();
  const displayFieldValue = displayField.value;
  return linkedRecords.value.filter((record) => {
    const value = displayFieldValue
      ? record.values[displayFieldValue.id]
      : record.id;
    return String(value || "").toLowerCase().includes(query);
  });
});

const selectedRecordIds = computed(() => {
  return selectedRecords.value.map((r) => r.id);
});

const targetTableName = computed(() => {
  const table = linkedTables.value.find((t) => t.id === linkedTableId.value);
  return table?.name || "";
});

async function loadCurrentBaseId(): Promise<string> {
  if (props.baseId) return props.baseId;
  const field = await fieldService.getField(props.field.id);
  if (field) {
    const table = await tableService.getTable(field.tableId);
    if (table) return table.baseId;
  }
  return "";
}

async function loadLinkedTables() {
  const baseId = await loadCurrentBaseId();
  if (!baseId) return;
  try {
    loading.value = true;
    linkedTables.value = await tableService.getTablesByBase(baseId);
  } catch (error) {
    console.error("加载关联表失败:", error);
  } finally {
    loading.value = false;
  }
}

async function loadLinkedTableData() {
  if (!linkedTableId.value) {
    linkedFields.value = [];
    linkedRecords.value = [];
    return;
  }
  try {
    recordLoading.value = true;
    linkedFields.value = await fieldService.getFieldsByTable(linkedTableId.value);
    linkedRecords.value = await recordService.getRecordsByTable(linkedTableId.value);
    updateSelectedRecordsFromModelValue();
  } catch (error) {
    console.error("加载关联表数据失败:", error);
    ElMessage.error("加载关联表数据失败");
  } finally {
    recordLoading.value = false;
  }
}

function updateSelectedRecordsFromModelValue() {
  const value = props.modelValue;
  console.log('[LinkField] updateSelectedRecordsFromModelValue: value=', value);
  if (!value) {
    selectedRecords.value = [];
    console.log('[LinkField] updateSelectedRecordsFromModelValue: no value, cleared');
    return;
  }

  let ids: string[] = [];
  if (Array.isArray(value)) {
    ids = value.map((v) =>
      typeof v === "string" ? v : (v as { id: string }).id,
    );
  } else if (value && typeof value === "object" && "id" in value) {
    ids = [(value as { id: string }).id];
  } else if (typeof value === "string") {
    ids = [value];
  }

  console.log('[LinkField] updateSelectedRecordsFromModelValue: parsed ids=', ids);

  if (ids.length === 0) {
    selectedRecords.value = [];
    return;
  }

  const existingIds = new Set(linkedRecords.value.map((r) => r.id));
  const matched = linkedRecords.value.filter((r) => ids.includes(r.id));
  const unmatched = ids
    .filter((id) => !existingIds.has(id))
    .map((id) => ({ id, tableId: "", values: {} } as RecordEntity));

  console.log('[LinkField] updateSelectedRecordsFromModelValue: matched=', matched.length, 'unmatched=', unmatched.length);
  console.log('[LinkField] linkedRecords ids:', linkedRecords.value.map(r => r.id));

  selectedRecords.value = [...matched, ...unmatched];
}

function isSelected(record: RecordEntity): boolean {
  return selectedRecordIds.value.includes(record.id);
}

function toggleRecord(record: RecordEntity) {
  if (props.readonly) return;

  const allowMultiple = props.field.config?.relationshipType !== "one_to_one";

  if (allowMultiple) {
    const index = selectedRecords.value.findIndex((r) => r.id === record.id);
    if (index > -1) {
      selectedRecords.value.splice(index, 1);
    } else {
      selectedRecords.value.push(record);
    }
    emit("update:modelValue", selectedRecords.value.map((r) => r.id));
  } else {
    selectedRecords.value = [record];
    emit("update:modelValue", record.id);
    showRecordSelector.value = false;
  }
}

async function removeRecord(recordId: string) {
  if (props.readonly) return;
  if (deleting.value) return;

  const recordName = getRecordDisplayValue(
    selectedRecords.value.find((r) => r.id === recordId) || {
      id: recordId,
      tableId: props.record?.tableId || "",
      values: {},
      createdAt: Date.now(),
      updatedAt: Date.now(),
    }
  );

  try {
    await ElMessageBox.confirm(
      `确定要解除与「${recordName}」的关联关系吗？`,
      "确认解除关联",
      {
        confirmButtonText: "确认解除",
        cancelButtonText: "取消",
        type: "warning",
      }
    );
  } catch {
    return;
  }

  deleting.value = true;
  try {
    if (props.record?.id) {
      await linkApiService.deleteRecordLink(
        props.record.id,
        props.field.id,
        recordId,
      );
    }

    selectedRecords.value = selectedRecords.value.filter((r) => r.id !== recordId);
    const allowMultiple = props.field.config?.relationshipType !== "one_to_one";
    if (allowMultiple) {
      emit("update:modelValue", selectedRecords.value.map((r) => r.id));
    } else {
      emit("update:modelValue", null);
    }

    ElMessage.success("已解除关联");
  } catch (error) {
    console.error("解除关联失败:", error);
    ElMessage.error("解除关联失败，请稍后重试");
  } finally {
    deleting.value = false;
  }
}

function getRecordDisplayValue(record: RecordEntity): string {
  if (!displayField.value) return record.id.slice(0, 8);
  const value = record.values[displayField.value.id];
  return value !== undefined && value !== null ? String(value) : "无标题";
}

function openRecordSelector() {
  if (props.readonly) return;

  if (!linkedTableId.value) {
    linkedTableId.value = (props.field.config?.linkedTableId || props.field.options?.linkedTableId) as string;
  }

  console.log('[LinkField] openRecordSelector: modelValue=', props.modelValue, 'linkedRecords.length=', linkedRecords.value.length);
  updateSelectedRecordsFromModelValue();
  console.log('[LinkField] after updateSelectedRecordsFromModelValue: selectedRecords.length=', selectedRecords.value.length, 'selectedRecords=', selectedRecords.value.map(r => r.id));

  showRecordSelector.value = true;
  searchQuery.value = "";

  if (linkedRecords.value.length === 0 && linkedTableId.value) {
    loadLinkedTableData();
  }
}

function closeRecordSelector() {
  showRecordSelector.value = false;
}

function confirmSelection() {
  const allowMultiple = props.field.config?.relationshipType !== "one_to_one";
  if (allowMultiple) {
    emit("update:modelValue", selectedRecords.value.map((r) => r.id));
  } else {
    emit("update:modelValue", selectedRecords.value[0]?.id || null);
  }
  closeRecordSelector();
}

// 记录详情抽屉
const detailDrawerVisible = ref(false);
const detailRecord = ref<RecordEntity | null>(null);
const detailFields = ref<FieldEntity[]>([]);

async function showRecordDetail(recordId: string) {
  try {
    const record = await recordApiService.getRecord(recordId);
    detailRecord.value = record as unknown as RecordEntity;
    detailFields.value = linkedFields.value;
    detailDrawerVisible.value = true;
  } catch (error) {
    console.error("加载记录详情失败:", error);
    ElMessage.error("加载记录详情失败");
  }
}

function handleDetailSave(_recordId: string, _values: Record<string, unknown>) {
}

watch(
  () => props.field.options,
  async (options) => {
    if (options?.linkedTableId) {
      linkedTableId.value = options.linkedTableId as string;
      await loadLinkedTableData();
    }
  },
  { immediate: true, deep: true },
);

watch(
  () => props.field.config,
  async (config) => {
    if (config?.linkedTableId) {
      linkedTableId.value = config.linkedTableId as string;
      await loadLinkedTableData();
    }
  },
  { immediate: true, deep: true },
);

watch(
  () => props.modelValue,
  () => {
    updateSelectedRecordsFromModelValue();
  },
  { immediate: true },
);

onMounted(async () => {
  await loadLinkedTables();
});
</script>

<template>
  <div class="link-field" :class="{ 'is-readonly': readonly }">
    <!-- 只读模式 -->
    <div v-if="readonly" class="link-display">
      <div class="link-records">
        <div
          v-for="record in displayRecords"
          :key="record.id"
          class="link-record-chip"
          @click="showRecordDetail(record.id)"
        >
          <el-icon class="chip-link-icon"><Link /></el-icon>
          <span class="chip-text">{{ getRecordDisplayValue(record) }}</span>
        </div>
        <div v-if="hasMoreRecords" class="link-record-more">
          +{{ hiddenRecordCount }}
        </div>
        <span v-if="selectedRecords.length === 0" class="empty-text">-</span>
      </div>
    </div>

    <!-- 编辑模式 -->
    <div v-else class="link-editor">
      <div class="link-records" @click="openRecordSelector">
        <div
          v-for="record in displayRecords"
          :key="record.id"
          class="link-record-chip"
          @click.stop="showRecordDetail(record.id)"
        >
          <el-icon class="chip-link-icon"><Link /></el-icon>
          <span class="chip-text">{{ getRecordDisplayValue(record) }}</span>
          <el-icon
            class="chip-remove-icon"
            :class="{ 'is-loading': deleting }"
            @click.stop="removeRecord(record.id)"
          >
            <Close />
          </el-icon>
        </div>
        <div v-if="hasMoreRecords" class="link-record-more">
          +{{ hiddenRecordCount }}
        </div>
        <div v-if="selectedRecords.length === 0" class="link-placeholder">
          <el-icon class="placeholder-icon"><Link /></el-icon>
          <span>选择关联记录</span>
        </div>
        <el-icon class="edit-arrow"><ArrowRight /></el-icon>
      </div>

      <!-- 记录选择弹窗 -->
      <el-dialog
        v-model="showRecordSelector"
        title="选择关联记录"
        width="620px"
        destroy-on-close
        class="link-selector-dialog"
      >
        <div class="selector-body">
          <!-- 关联目标提示 -->
          <div class="selector-header">
            <el-icon class="header-link-icon"><Link /></el-icon>
            <span>关联到：</span>
            <el-tag size="small" type="primary" effect="plain">
              {{ targetTableName || linkedTableId }}
            </el-tag>
          </div>

          <!-- 搜索 -->
          <div class="selector-search">
            <el-input
              v-model="searchQuery"
              placeholder="搜索记录..."
              clearable
              size="default"
            >
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
            </el-input>
          </div>

          <!-- 已选记录摘要 -->
          <div v-if="selectedRecords.length > 0" class="selector-selected-summary">
            <span class="summary-label">已选择</span>
            <div class="summary-tags">
              <el-tag
                v-for="record in selectedRecords"
                :key="record.id"
                closable
                size="small"
                type="primary"
                @close="removeRecord(record.id)"
              >
                {{ getRecordDisplayValue(record) }}
              </el-tag>
            </div>
          </div>

          <!-- 记录列表 -->
          <div class="selector-records">
            <div v-if="recordLoading" class="records-loading">
              <el-skeleton :rows="4" animated />
            </div>
            <template v-else>
              <div
                v-for="record in filteredRecords"
                :key="record.id"
                class="selector-record-item"
                :class="{ 'is-selected': isSelected(record) }"
                @click="toggleRecord(record)"
              >
                <el-checkbox
                  :model-value="isSelected(record)"
                  size="default"
                  @click.stop
                  @change="() => toggleRecord(record)"
                />
                <div class="record-item-info">
                  <div class="record-item-name">
                    {{ getRecordDisplayValue(record) }}
                  </div>
                  <div class="record-item-id">
                    ID: {{ record.id.slice(0, 8) }}...
                  </div>
                </div>
                <el-icon
                  v-if="isSelected(record)"
                  class="record-check-icon"
                >
                  <Check />
                </el-icon>
              </div>
              <div
                v-if="filteredRecords.length === 0"
                class="records-empty"
              >
                <el-empty description="暂无匹配的记录" :image-size="60" />
              </div>
            </template>
          </div>
        </div>

        <template #footer>
          <div class="selector-footer">
            <span class="footer-count">
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

      <!-- 记录详情抽屉 -->
      <RecordDetailDrawer
        v-model:visible="detailDrawerVisible"
        :record="detailRecord"
        :fields="detailFields"
        :readonly="true"
        size="50%"
        @save="handleDetailSave"
      />
    </div>
  </div>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;

.link-field {
  width: 100%;
  min-height: 32px;
}

.link-display,
.link-editor {
  width: 100%;
}

.link-records {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 4px;
  min-height: 32px;
  padding: 2px 4px;
}

.link-editor .link-records {
  cursor: pointer;
  border: 1px solid transparent;
  border-radius: $border-radius-sm;
  transition: all 0.2s ease;
  padding: 2px 4px;

  &:hover {
    border-color: $border-color;
    background-color: rgba($primary-color, 0.02);

    .edit-arrow {
      opacity: 1;
    }
  }
}

.link-record-chip {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 1px 6px 1px 8px;
  background-color: rgba($primary-color, 0.08);
  border: 1px solid rgba($primary-color, 0.15);
  border-radius: 12px;
  font-size: $font-size-sm;
  color: $primary-color;
  cursor: pointer;
  transition: all 0.2s ease;
  max-width: 180px;
  overflow: hidden;
  user-select: none;

  &:hover {
    background-color: rgba($primary-color, 0.14);
    border-color: rgba($primary-color, 0.3);
    transform: translateY(-1px);
    box-shadow: 0 2px 6px rgba($primary-color, 0.12);
  }

  .chip-link-icon {
    font-size: 11px;
    flex-shrink: 0;
  }

  .chip-text {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    line-height: 1.6;
    margin-right: 2px;
  }

  .chip-remove-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 16px;
    height: 16px;
    border-radius: 50%;
    font-size: 10px;
    flex-shrink: 0;
    color: $text-secondary;
    background-color: transparent;
    transition: all 0.15s ease;
    margin-left: 2px;

    &:hover {
      color: #fff;
      background-color: $error-color;
    }

    &.is-loading {
      color: $text-disabled;
      pointer-events: none;
      animation: spin 1s linear infinite;
      background-color: transparent;
    }
  }

  &:hover .chip-remove-icon {
    color: $text-secondary;
  }
}

.link-record-more {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 22px;
  height: 22px;
  padding: 0 6px;
  background-color: $bg-color;
  border: 1px solid $border-color;
  border-radius: 12px;
  font-size: $font-size-xs;
  color: $text-secondary;
  cursor: default;
}

.link-placeholder {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  color: $text-disabled;
  font-size: $font-size-sm;

  .placeholder-icon {
    font-size: 13px;
  }
}

.empty-text {
  color: $text-disabled;
  font-size: $font-size-sm;
}

.edit-arrow {
  margin-left: auto;
  font-size: 13px;
  color: $text-secondary;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.is-readonly {
  .link-record-chip {
    cursor: pointer;
  }
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

// 选择器弹窗样式
:deep(.link-selector-dialog) {
  .el-dialog__body {
    padding: 0;
  }
}

.selector-body {
  padding: 0 20px 20px;
  max-height: 480px;
  overflow-y: auto;
}

.selector-header {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 16px 0 12px;
  font-size: $font-size-sm;
  color: $text-secondary;
  border-bottom: 1px solid $border-color;

  .header-link-icon {
    font-size: 14px;
    color: $primary-color;
  }
}

.selector-search {
  padding: 12px 0;
}

.selector-selected-summary {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 10px 12px;
  margin-bottom: 12px;
  background-color: rgba($primary-color, 0.04);
  border: 1px solid rgba($primary-color, 0.1);
  border-radius: $border-radius-sm;

  .summary-label {
    font-size: $font-size-xs;
    color: $text-secondary;
    font-weight: 500;
  }

  .summary-tags {
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
  }
}

.selector-records {
  border: 1px solid $border-color;
  border-radius: $border-radius-sm;
  max-height: 260px;
  overflow-y: auto;
}

.records-loading {
  padding: 16px;
}

.selector-record-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  cursor: pointer;
  transition: background-color 0.15s ease;
  border-bottom: 1px solid $border-color;

  &:last-child {
    border-bottom: none;
  }

  &:hover {
    background-color: rgba($primary-color, 0.04);
  }

  &.is-selected {
    background-color: rgba($primary-color, 0.08);
  }

  .record-item-info {
    flex: 1;
    min-width: 0;
    display: flex;
    flex-direction: column;
    gap: 1px;
  }

  .record-item-name {
    font-size: $font-size-sm;
    color: $text-primary;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .record-item-id {
    font-size: $font-size-xs;
    color: $text-secondary;
  }

  .record-check-icon {
    font-size: 15px;
    color: $primary-color;
    flex-shrink: 0;
  }
}

.records-empty {
  padding: 24px 0;
}

.selector-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;

  .footer-count {
    font-size: $font-size-sm;
    color: $text-secondary;
  }

  .footer-actions {
    display: flex;
    gap: $spacing-sm;
  }
}
</style>