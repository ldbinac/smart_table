<template>
  <el-dialog
    v-model="dialogVisible"
    :title="t('link.selectRecordTitle')"
    width="620px"
    :close-on-click-modal="false"
    @close="handleCancel"
  >
    <div class="link-record-selector">
      <!-- 关联目标提示 -->
      <div class="selector-header">
        <el-icon class="header-link-icon"><Link /></el-icon>
        <span>{{ t('link.linkTo') }}</span>
        <el-tag size="small" type="primary" effect="plain">
          {{ targetTableName }}
        </el-tag>
        <el-tag v-if="!allowMultiple" size="small" type="warning" effect="plain">
          {{ t('link.onlyOne') }}
        </el-tag>
        <el-tag
          v-if="excludeRecordId"
          size="small"
          type="info"
          effect="plain"
          class="self-hint-tag"
        >
          {{ t('link.cannotSelectSelf') }}
        </el-tag>
      </div>

      <!-- 搜索栏 -->
      <div class="search-bar">
        <el-input
          v-model="searchKeyword"
          :placeholder="t('link.searchPlaceholder')"
          clearable
          @input="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
      </div>

      <!-- 已选记录摘要 -->
      <div v-if="selectedRecords.length > 0" class="selected-section">
        <div class="section-title">
          {{ t('link.selected') }}
          <span class="section-count">{{ selectedRecords.length }}</span>
        </div>
        <div class="selected-list">
          <el-tag
            v-for="record in selectedRecords"
            :key="record.id"
            closable
            size="small"
            class="selected-tag"
            @close="removeSelected(record.id)"
          >
            {{ getDisplayValue(record) }}
          </el-tag>
        </div>
      </div>

      <!-- 可选记录列表 -->
      <div class="records-section">
        <div class="section-title">
          {{ t('link.availableRecords') }}
          <span v-if="records.length > 0" class="section-count">
            {{ total }}
          </span>
        </div>
        <div v-if="loading" class="loading-state">
          <el-skeleton :rows="5" animated />
        </div>
        <div v-else-if="records.length === 0" class="empty-state">
          <el-empty :description="t('link.noAvailableRecords')" :image-size="60" />
        </div>
        <div v-else class="records-table-container">
          <table class="records-table">
            <thead>
              <tr>
                <th class="checkbox-column">
                  <el-checkbox
                    :model-value="allSelected"
                    :indeterminate="indeterminate"
                    @change="toggleSelectAll"
                  />
                </th>
                <th
                  v-for="field in displayFields"
                  :key="field.id"
                  class="field-header"
                >
                  {{ field.name }}
                </th>
              </tr>
            </thead>
            <tbody>
              <tr
                v-for="record in records"
                :key="record.id"
                class="record-row"
                :class="{ selected: isSelected(record.id) }"
                @click="toggleSelect(record)"
              >
                <td class="checkbox-column">
                  <el-checkbox
                    :model-value="isSelected(record.id)"
                    @click.stop
                    @change="() => toggleSelect(record)"
                  />
                </td>
                <td
                  v-for="field in displayFields"
                  :key="field.id"
                  class="field-cell"
                >
                  {{ getFieldValue(record, field.id) }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 分页 -->
      <div v-if="totalPages > 1" class="pagination">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          background
          @change="handlePageChange"
        />
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <span class="footer-count">
          {{ t('link.selectedCount', { count: selectedRecords.length }) }}
        </span>
        <div class="footer-actions">
          <el-button @click="handleCancel">{{ t('link.cancel') }}</el-button>
          <el-button type="primary" @click="handleConfirm">
            {{ t('link.confirm') }}
          </el-button>
        </div>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from "vue";
import { useI18n } from "vue-i18n";
import {
  ElDialog,
  ElInput,
  ElIcon,
  ElTag,
  ElCheckbox,
  ElButton,
  ElPagination,
  ElSkeleton,
  ElEmpty,
} from "element-plus";
import { Search, Link } from "@element-plus/icons-vue";
import { linkApiService } from "@/services/api/linkApiService";
import { tableApiService } from "@/services/api/tableApiService";
import { fieldCacheService } from "@/db/services/fieldCacheService";
import { tableService } from "@/db/services/tableService";
import type { LinkedRecord } from "@/types/link";
import type { FieldEntity } from "@/db/schema";
import { FieldType } from "@/types/fields";
import { formatLinkCellValue, isRawRecordIdDisplay } from "@/utils/linkDisplay";
import { debounce } from "lodash-es";

const { t } = useI18n();

interface Props {
  visible: boolean;
  targetTableId?: string;
  displayFieldId?: string;
  selectedIds?: string[];
  linkedRecords?: LinkedRecord[];
  allowMultiple?: boolean;
  /** 需要从可选列表中排除的记录 ID（如自关联时禁止选择当前记录自身） */
  excludeRecordId?: string;
  /** 匿名分享表单的分享 token：用于在未登录时凭 token 读取字段/记录 */
  shareToken?: string;
}

const props = withDefaults(defineProps<Props>(), {
  selectedIds: () => [],
  linkedRecords: () => [],
  allowMultiple: true,
  excludeRecordId: "",
  shareToken: "",
});

const MAX_DISPLAY_FIELDS = 3;

interface DisplayField {
  id: string;
  name: string;
  type: string;
  options?: Record<string, unknown>;
  config?: Record<string, unknown>;
}

const displayFields = ref<DisplayField[]>([]);

// LINK 类型字段的显示值查找表: fieldId -> (recordId -> displayValue)
const linkFieldDisplayMaps = ref<Map<string, Map<string, string>>>(new Map());

const emit = defineEmits<{
  (e: "confirm", selectedIds: string[], records: LinkedRecord[]): void;
  (e: "cancel"): void;
}>();

const dialogVisible = computed({
  get: () => props.visible,
  set: () => {},
});

const searchKeyword = ref("");
const records = ref<Array<{ id: string; values: Record<string, unknown> }>>([]);
const loading = ref(false);
const total = ref(0);
const currentPage = ref(1);
const pageSize = ref(20);
const selectedRecords = ref<Array<{ id: string; values: Record<string, unknown> }>>([]);

const totalPages = computed(() => Math.ceil(total.value / pageSize.value));

const targetTableName = ref("");

const allSelected = computed(() => {
  if (records.value.length === 0) return false;
  return records.value.every((r) => isSelected(r.id));
});

const indeterminate = computed(() => {
  if (records.value.length === 0) return false;
  const selectedCount = records.value.filter((r) => isSelected(r.id)).length;
  return selectedCount > 0 && selectedCount < records.value.length;
});

function toggleSelectAll(checked: boolean | string | number) {
  if (!props.allowMultiple) {
    if (checked && records.value.length > 0) {
      selectedRecords.value = [records.value[0]];
    } else {
      selectedRecords.value = [];
    }
    return;
  }

  if (checked) {
    const newRecords = records.value.filter(
      (r) => !selectedRecords.value.some((sr) => sr.id === r.id)
    );
    selectedRecords.value.push(...newRecords);
  } else {
    const unselectedIds = new Set(records.value.map((r) => r.id));
    selectedRecords.value = selectedRecords.value.filter(
      (r) => !unselectedIds.has(r.id)
    );
  }
}

const initSelectedRecords = () => {
  selectedRecords.value = [];
  if (props.selectedIds && props.selectedIds.length > 0) {
    const linkedRecordMap = new Map<string, LinkedRecord>();
    for (const lr of props.linkedRecords) {
      if (lr && lr.record_id) {
        linkedRecordMap.set(lr.record_id, lr);
      }
    }

    // 过滤掉当前记录自身（自关联场景禁止选自己作为父级）
    const uniqueIds = [...new Set(props.selectedIds)].filter(
      (id) => id !== props.excludeRecordId
    );

    for (const id of uniqueIds) {
      const linked = linkedRecordMap.get(id);
      const displayVal = linked?.display_value;
      // 显示名缺失（或后端用记录 ID 兜底）时留空，由后续加载补齐；
      // 绝不把 UUID 写进 values，否则已选标签会直接显示 ID。
      const values: Record<string, unknown> = {};
      if (displayVal && props.displayFieldId && !isRawRecordIdDisplay(displayVal, id)) {
        values[props.displayFieldId] = displayVal;
      }
      selectedRecords.value.push({ id, values });
    }
  }
};

const refreshSelectedFromLoadedRecords = async () => {
  if (selectedRecords.value.length === 0) return;

  const loadedRecordMap = new Map<string, { id: string; values: Record<string, unknown> }>();
  for (const r of records.value) {
    loadedRecordMap.set(r.id, r);
  }

  // 检查哪些已选记录不在已加载列表中（因为 exclude_ids 排除）
  const missingIds: string[] = [];
  for (const sr of selectedRecords.value) {
    const loaded = loadedRecordMap.get(sr.id);
    if (loaded) {
      sr.values = { ...sr.values, ...loaded.values };
    } else {
      missingIds.push(sr.id);
    }
  }

  // 对因 exclude_ids 而缺失的已选记录，单独获取显示值
  // 反向关联字段可能没有 displayFieldId；补值只依赖目标表，
  // 补齐后由 getDisplayValue 依次尝试展示字段，因此不能把它作为前置条件。
  if (missingIds.length > 0 && props.targetTableId) {
    try {
      const result = await linkApiService.searchLinkableRecords(
        props.targetTableId,
        { page: 1, per_page: Math.min(missingIds.length, 200) },
        props.shareToken
        // 不使用 exclude_ids，以确保这些记录被返回
      );
      for (const sr of selectedRecords.value) {
        if (missingIds.includes(sr.id)) {
          const loaded = result.items.find(r => r.id === sr.id);
          if (loaded) {
            sr.values = { ...sr.values, ...loaded.values };
          }
        }
      }
    } catch (error) {
      console.error('[LinkRecordSelector] 加载缺失的已选记录显示值失败:', error);
    }
  }
};

const loadTargetTableName = async () => {
  if (!props.targetTableId) return;
  try {
    const table = props.shareToken
      ? await tableApiService.getTable(props.targetTableId, props.shareToken)
      : await tableService.getTable(props.targetTableId);
    targetTableName.value = table?.name || props.targetTableId;
  } catch {
    targetTableName.value = props.targetTableId;
  }
};

const loadDisplayFields = async () => {
  if (!props.targetTableId) {
    displayFields.value = [];
    return;
  }
  try {
    const allFields = await fieldCacheService.getFieldsWithCache(props.targetTableId, false, props.shareToken);
    const visibleFields = allFields
      .filter((field: FieldEntity) => field.isVisible !== false)
      .sort((a: FieldEntity, b: FieldEntity) => a.order - b.order);
    const selectedFields = visibleFields.slice(0, MAX_DISPLAY_FIELDS);
    displayFields.value = selectedFields.map((field: FieldEntity) => ({
      id: field.id,
      name: field.name,
      type: field.type,
      options: field.options,
      config: field.config,
    }));
  } catch (error) {
    console.error("[LinkRecordSelector] 加载字段失败:", error);
    displayFields.value = [];
  }
};

/** 根据字段类型和选项将原始值格式化为可读的显示文本 */
const formatValueForDisplay = (value: unknown, field?: DisplayField): string => {
  if (value === null || value === undefined || value === '') {
    return '';
  }

  // 单选
  if (field?.type === FieldType.SINGLE_SELECT) {
    const choices = (field.options?.choices ?? field.options?.options ?? []) as Array<{ id: string; name: string }>;
    const option = choices.find(c => c.id === value);
    return option?.name ?? String(value);
  }

  // 多选
  if (field?.type === FieldType.MULTI_SELECT) {
    if (Array.isArray(value)) {
      const choices = (field.options?.choices ?? field.options?.options ?? []) as Array<{ id: string; name: string }>;
      return value.map(v => {
        if (typeof v === 'object' && v !== null && 'name' in v) return (v as { name: string }).name;
        const opt = choices.find(c => c.id === v);
        return opt?.name ?? String(v);
      }).filter(Boolean).join(', ');
    }
    if (typeof value === 'string') {
      const choices = (field.options?.choices ?? field.options?.options ?? []) as Array<{ id: string; name: string }>;
      const opt = choices.find(c => c.id === value);
      return opt?.name ?? value;
    }
  }

  return String(value);
};

/** 关联字段配置可能在 config（后端）或 options（前端离线创建路径）中 */
const getLinkFieldConfigValue = (
  field: DisplayField,
  camelKey: string,
  snakeKey: string,
): string | undefined => {
  for (const storage of [field.config, field.options]) {
    if (!storage) continue;
    const value = storage[camelKey] ?? storage[snakeKey];
    if (typeof value === "string" && value) return value;
  }
  return undefined;
};

const preloadLinkFieldDisplayMaps = async () => {
  const newMap = new Map<string, Map<string, string>>();
  const linkFields = displayFields.value.filter(f => f.type === FieldType.LINK || f.type === 'link_to_record');

  if (linkFields.length === 0 || records.value.length === 0) {
    linkFieldDisplayMaps.value = newMap;
    return;
  }

  // 预加载所有关联表的字段信息（用于格式化单选/多选等字段）
  const linkedTableFieldsMap = new Map<string, DisplayField[]>();
  for (const field of linkFields) {
    const linkedTableId = getLinkFieldConfigValue(field, 'linkedTableId', 'linked_table_id');
    if (!linkedTableId || linkedTableFieldsMap.has(linkedTableId)) continue;
    try {
      const fields = await fieldCacheService.getFieldsWithCache(linkedTableId, false, props.shareToken);
      linkedTableFieldsMap.set(linkedTableId, fields.map(f => ({
        id: f.id,
        name: f.name,
        type: f.type,
        options: f.options,
        config: f.config,
      })));
    } catch (error) {
      console.warn('[LinkRecordSelector] 加载关联表字段失败:', linkedTableId, error);
    }
  }

  for (const field of linkFields) {
    const linkedTableId = getLinkFieldConfigValue(field, 'linkedTableId', 'linked_table_id');
    let displayFieldId = getLinkFieldConfigValue(field, 'displayFieldId', 'display_field_id');
    if (!linkedTableId) continue;

    // 如果未配置显示字段，回退到关联表的主字段
    if (!displayFieldId) {
      try {
        const linkedTable: any = props.shareToken
          ? await tableApiService.getTable(linkedTableId, props.shareToken)
          : await tableService.getTable(linkedTableId);
        displayFieldId = linkedTable?.primaryFieldId;
      } catch (error) {
        console.warn('[LinkRecordSelector] 获取关联表主字段失败:', linkedTableId, error);
      }
    }
    if (!displayFieldId) continue;

    const fieldMap = new Map<string, string>();
    newMap.set(field.id, fieldMap);

    // 收集该字段下所有被关联的记录 ID
    const linkedIds = new Set<string>();
    for (const record of records.value) {
      const val = record.values[field.id];
      if (Array.isArray(val)) {
        for (const id of val) {
          if (typeof id === 'string') linkedIds.add(id);
        }
      } else if (typeof val === 'string') {
        linkedIds.add(val);
      }
    }

    if (linkedIds.size === 0) continue;

    const linkedFields = linkedTableFieldsMap.get(linkedTableId) || [];
    const displayField = linkedFields.find(f => f.id === displayFieldId);

    try {
      // 从关联表获取记录以解析显示值
      const result = await linkApiService.searchLinkableRecords(linkedTableId, {
        page: 1,
        per_page: Math.min(linkedIds.size, 200),
      }, props.shareToken);
      for (const item of result.items) {
        if (linkedIds.has(item.id)) {
          const rawDisplayVal = item.values[displayFieldId];
          const displayVal = formatValueForDisplay(rawDisplayVal, displayField);
          fieldMap.set(item.id, displayVal || item.id);
        }
      }
      // 未匹配到的记录不写入 ID 兜底：无法解析时显示占位，而不是裸 UUID
    } catch (error) {
      console.warn('[LinkRecordSelector] 解析关联字段显示值失败:', field.id, error);
    }
  }

  linkFieldDisplayMaps.value = newMap;
};

const loadRecords = async () => {
  if (!props.targetTableId) return;
  loading.value = true;
  try {
    // 自关联场景下排除当前记录自身（禁止选自己作为父级）
    const excludeIds = [...(props.selectedIds || [])];
    if (props.excludeRecordId && !excludeIds.includes(props.excludeRecordId)) {
      excludeIds.push(props.excludeRecordId);
    }
    const result = await linkApiService.searchLinkableRecords(
      props.targetTableId,
      {
        keyword: searchKeyword.value,
        exclude_ids: excludeIds,
        page: currentPage.value,
        per_page: pageSize.value,
      },
      props.shareToken
    );
    records.value = result.items;
    total.value = result.total;
  } catch (error) {
    console.error("[LinkRecordSelector] 加载记录失败:", error);
  } finally {
    loading.value = false;
  }
};

watch(
  () => props.visible,
  async (visible) => {
    if (visible) {
      console.log('[LinkRecordSelector] visible -> true, selectedIds:', props.selectedIds, 'linkedRecords:', props.linkedRecords.length);
      initSelectedRecords();
      console.log('[LinkRecordSelector] after initSelectedRecords, selectedRecords:', selectedRecords.value.length);
      await Promise.all([
        loadDisplayFields(),
        loadRecords(),
        loadTargetTableName(),
      ]);
      await preloadLinkFieldDisplayMaps();
      await refreshSelectedFromLoadedRecords();
      console.log('[LinkRecordSelector] after refresh, selectedRecords:', selectedRecords.value.length);
    }
  },
  { immediate: true }
);

// 当 selectedIds 或 linkedRecords 发生变化时，重新初始化已选记录
watch(
  [() => props.selectedIds, () => props.linkedRecords],
  ([newIds]) => {
    if (props.visible && newIds && newIds.length > 0) {
      console.log('[LinkRecordSelector] selectedIds/linkedRecords changed, re-initializing');
      initSelectedRecords();
    }
  },
  { deep: true }
);

// 搜索/翻页会替换 records，必须同步刷新关联字段的 ID→显示名映射，
// 否则新一页的关联列会退回显示裸 UUID。
const reloadRecordsWithLinkDisplays = async () => {
  await loadRecords();
  await preloadLinkFieldDisplayMaps();
};

const handleSearch = debounce(() => {
  currentPage.value = 1;
  reloadRecordsWithLinkDisplays();
}, 300);

const handlePageChange = () => {
  reloadRecordsWithLinkDisplays();
};

const getDisplayValue = (record: { id: string; values: Record<string, unknown> }): string => {
  // 优先使用配置的展示字段，再依次尝试关联表的显示字段（带字段类型感知）
  const tryField = (fieldId: string): string | null => {
    const rawVal = record.values[fieldId];
    if (rawVal === undefined || rawVal === null || rawVal === "") return null;
    if (isRawRecordIdDisplay(rawVal, record.id)) return null;
    const formatted = getFormattedFieldValue(record, fieldId);
    if (!formatted || formatted === "-" || isRawRecordIdDisplay(formatted, record.id)) return null;
    return formatted;
  };

  if (props.displayFieldId) {
    const value = tryField(props.displayFieldId);
    if (value) return value;
  }
  for (const field of displayFields.value) {
    const value = tryField(field.id);
    if (value) return value;
  }

  // 兜底：取第一个非空的、不是记录 ID 的标量值
  for (const val of Object.values(record.values)) {
    if (val === null || val === undefined || val === "") continue;
    if (typeof val === "object") {
      if (val !== null && "name" in val) return String((val as { name: unknown }).name);
      continue;
    }
    if (isRawRecordIdDisplay(val, record.id)) continue;
    return String(val);
  }
  return t('link.noTitle');
};

/** 按字段类型格式化值（供 getDisplayValue / getFieldValue 复用） */
const getFormattedFieldValue = (record: { id: string; values: Record<string, unknown> }, fieldId: string): string => {
  const field = displayFields.value.find(f => f.id === fieldId);
  const value = record.values[fieldId];
  if (value === null || value === undefined || value === "") {
    return "-";
  }

  // 单选
  if (field?.type === FieldType.SINGLE_SELECT) {
    const choices = (field.options?.choices ?? field.options?.options ?? []) as Array<{ id: string; name: string }>;
    const option = choices.find(c => c.id === value);
    return option?.name ?? String(value);
  }

  // 多选
  if (field?.type === FieldType.MULTI_SELECT) {
    if (Array.isArray(value)) {
      const choices = (field.options?.choices ?? field.options?.options ?? []) as Array<{ id: string; name: string }>;
      return value.map(v => {
        if (typeof v === "object" && v !== null && "name" in v) return (v as { name: string }).name;
        const opt = choices.find(c => c.id === v);
        return opt?.name ?? String(v);
      }).filter(Boolean).join(", ");
    }
    if (typeof value === "string") {
      const choices = (field.options?.choices ?? field.options?.options ?? []) as Array<{ id: string; name: string }>;
      const opt = choices.find(c => c.id === value);
      return opt?.name ?? String(value);
    }
  }

  // LINK：只输出成功解析的显示名，解析不到时显示占位，绝不暴露裸 UUID
  if (field?.type === FieldType.LINK || field?.type === 'link_to_record') {
    const display = formatLinkCellValue(value, linkFieldDisplayMaps.value.get(fieldId));
    return display || "-";
  }

  return String(value ?? "");
};

const getFieldValue = (record: { id: string; values: Record<string, unknown> }, fieldId: string): string => {
  return getFormattedFieldValue(record, fieldId);
};

const isSelected = (recordId: string): boolean => {
  return selectedRecords.value.some((r) => r.id === recordId);
};

const toggleSelect = (record: { id: string; values: Record<string, unknown> }) => {
  // 禁止选择当前记录自身（自关联场景）
  if (props.excludeRecordId && record.id === props.excludeRecordId) return;

  const index = selectedRecords.value.findIndex((r) => r.id === record.id);
  if (index > -1) {
    selectedRecords.value.splice(index, 1);
  } else {
    if (!props.allowMultiple) {
      selectedRecords.value = [];
    }
    selectedRecords.value.push(record);
  }
};

const removeSelected = (recordId: string) => {
  const index = selectedRecords.value.findIndex((r) => r.id === recordId);
  if (index > -1) {
    selectedRecords.value.splice(index, 1);
  }
};

const handleConfirm = () => {
  const seen = new Set<string>();
  const selectedIds: string[] = [];
  const linkedRecords: LinkedRecord[] = [];
  for (const r of selectedRecords.value) {
    if (!seen.has(r.id)) {
      seen.add(r.id);
      selectedIds.push(r.id);
      linkedRecords.push({
        record_id: r.id,
        display_value: getDisplayValue(r),
        record: r,
      });
    }
  }
  emit("confirm", selectedIds, linkedRecords);
};

const handleCancel = () => {
  selectedRecords.value = [];
  searchKeyword.value = "";
  currentPage.value = 1;
  emit("cancel");
};

onMounted(async () => {
  if (props.visible) {
    initSelectedRecords();
    await Promise.all([
      loadDisplayFields(),
      loadRecords(),
      loadTargetTableName(),
    ]);
    await preloadLinkFieldDisplayMaps();
    await refreshSelectedFromLoadedRecords();
  }
});
</script>

<style scoped lang="scss">
.link-record-selector {
  max-height: 520px;
  overflow-y: auto;
}

.selector-header {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--el-border-color-light);
  font-size: 14px;
  color: var(--el-text-color-secondary);

  .header-link-icon {
    font-size: 14px;
    color: var(--el-color-primary);
  }
}

.search-bar {
  margin-bottom: 12px;
}

.section-title {
  font-size: 13px;
  font-weight: 500;
  color: var(--el-text-color-regular);
  margin-bottom: 8px;

  .section-count {
    font-weight: 400;
    color: var(--el-text-color-secondary);
    margin-left: 4px;
    font-size: 12px;
  }
}

.selected-section {
  margin-bottom: 12px;
  padding: 10px 12px;
  background-color: rgba(64, 158, 255, 0.04);
  border: 1px solid rgba(64, 158, 255, 0.1);
  border-radius: 6px;
}

.selected-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.selected-tag {
  cursor: pointer;
}

.records-section {
  min-height: 200px;
}

.loading-state,
.empty-state {
  padding: 24px 0;
}

.records-table-container {
  border: 1px solid var(--el-border-color-light);
  border-radius: 6px;
  max-height: 280px;
  overflow-y: auto;
}

.records-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;
}

.checkbox-column {
  width: 44px;
  text-align: center;
  padding: 8px 4px;
}

.field-header {
  padding: 8px 10px;
  text-align: left;
  font-size: 13px;
  font-weight: 500;
  color: var(--el-text-color-secondary);
  background-color: var(--el-fill-color-light);
  border-bottom: 1px solid var(--el-border-color-light);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.record-row {
  cursor: pointer;
  transition: background-color 0.15s ease;
  border-bottom: 1px solid var(--el-border-color-lighter);

  &:last-child {
    border-bottom: none;
  }

  &:hover {
    background-color: var(--el-color-primary-light-9);
  }

  &.selected {
    background-color: rgba(64, 158, 255, 0.06);
  }
}

.field-cell {
  padding: 8px 10px;
  font-size: 13px;
  color: var(--el-text-color-regular);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  border-right: 1px solid var(--el-border-color-lighter);

  &:last-child {
    border-right: none;
  }
}

.pagination {
  margin-top: 12px;
  display: flex;
  justify-content: flex-end;
}

.dialog-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  width: 100%;

  .footer-count {
    font-size: 13px;
    color: var(--el-text-color-secondary);
  }

  .footer-actions {
    display: flex;
    gap: 8px;
  }
}
</style>