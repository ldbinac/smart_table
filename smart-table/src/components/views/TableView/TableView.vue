<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from "vue";
import { useBaseStore } from "@/stores";
import { useTableStore } from "@/stores/tableStore";
import { useViewStore } from "@/stores/viewStore";

import type { RecordEntity, FieldEntity } from "@/db/schema";
import type { CellValue, SortConfig } from "@/types";
import TableCell from "./TableCell.vue";
import TableHeader from "./TableHeader.vue";
import TableRow from "./TableRow.vue";
import ContextMenu from "@/components/common/ContextMenu.vue";
import { generateId } from "@/utils/id";
import { ElMessage, ElMessageBox, ElIcon } from "element-plus";
import { isFieldRequired, isValueEmpty } from "@/utils/validation";
import { ZoomIn, Check } from "@element-plus/icons-vue";
import RecordDetailDrawer from "@/components/dialogs/RecordDetailDrawer.vue";
import FieldDialog from "@/components/dialogs/FieldDialog.vue";

interface Props {
  tableId?: string;
  viewId?: string;
  readonly?: boolean;
  records?: any[];
}

const props = withDefaults(defineProps<Props>(), {
  tableId: "",
  viewId: "",
  readonly: false,
  records: undefined,
});

const emit = defineEmits<{
  (e: "record-select", record: RecordEntity | null): void;
  (e: "records-select", records: RecordEntity[]): void;
  (e: "record-update", record: RecordEntity): void;
  (e: "record-create"): void;
  (e: "record-delete", recordIds: string[]): void;
  (e: "add-record"): void;
}>();

const baseStore = useBaseStore();
const tableStore = useTableStore();
const viewStore = useViewStore();

const selectedRows = ref<string[]>([]);
const hoveredRowId = ref<string | null>(null);
const editingCell = ref<{ recordId: string; fieldId: string } | null>(null);

// 放大按钮相关
const expandedRecord = ref<RecordEntity | null>(null);
const expandDialogVisible = ref(false);

// Drawer 抽屉大小（响应式）
const drawerSize = computed(() => {
  const width = window.innerWidth;
  if (width < 768) return "100%";
  if (width < 1024) return "70%";
  if (width < 1440) return "50%";
  return "600px";
});

// 字段编辑对话框相关
const fieldDialogVisible = ref(false);
const editingFieldId = ref<string | null>(null);

const contextMenuVisible = ref(false);
const contextMenuX = ref(0);
const contextMenuY = ref(0);
const contextMenuTarget = ref<"row" | "header" | "cell">("row");
const contextMenuField = ref<FieldEntity | null>(null);
const contextMenuRecord = ref<RecordEntity | null>(null);

const columnWidths = ref<Record<string, number>>({});
const isDraggingRow = ref(false);
const draggedRowId = ref<string | null>(null);

const records = computed(() => props.records || tableStore.records);
const fields = computed(() => tableStore.fields);
const currentView = computed(() => viewStore.currentView);

// 使用 tableStore.fields 计算可见字段，确保状态同步
const visibleFields = computed(() => {
  // 首先过滤掉 isVisible 为 false 的字段（全局隐藏）
  let result = fields.value.filter(
    (field) => (field as any).isVisible !== false,
  );
  // 再根据当前视图的 hiddenFields 进行过滤（视图级隐藏）
  if (currentView.value) {
    result = result.filter(
      (field) => !currentView.value!.hiddenFields.includes(field.id),
    );
  }
  return result;
});

// 使用 viewStore.currentView 计算冻结字段
const frozenFields = computed(() => {
  if (!currentView.value) return [];
  return fields.value.filter((field) =>
    currentView.value!.frozenFields.includes(field.id),
  );
});

const rowHeight = computed(() => currentView.value?.rowHeight || "medium");

const sortedRecords = computed(() => {
  const sorts = viewStore.currentSorts as SortConfig[];
  if (!sorts || sorts.length === 0) return records.value;

  return [...records.value].sort((a, b) => {
    for (const sort of sorts) {
      const aVal = a.values[sort.fieldId];
      const bVal = b.values[sort.fieldId];

      let comparison = 0;
      if (aVal === null || aVal === undefined) {
        comparison = bVal === null || bVal === undefined ? 0 : -1;
      } else if (bVal === null || bVal === undefined) {
        comparison = 1;
      } else if (typeof aVal === "number" && typeof bVal === "number") {
        comparison = aVal - bVal;
      } else {
        comparison = String(aVal).localeCompare(String(bVal));
      }

      if (comparison !== 0) {
        return sort.direction === "desc" ? -comparison : comparison;
      }
    }
    return 0;
  });
});

const contextMenuItems = computed(() => {
  const items: any[] = [];

  if (contextMenuTarget.value === "row") {
    // 非只读模式下显示编辑、复制和删除选项
    if (!props.readonly) {
      items.push({ id: "edit", label: "编辑", icon: "edit" });
      items.push(
        { id: "duplicate", label: "复制记录", icon: "copy" },
        { divider: true, id: "divider1" },
      );

      if (selectedRows.value.length > 1) {
        items.push({
          id: "delete-selected",
          label: `删除选中的 ${selectedRows.value.length} 条记录`,
          icon: "delete",
          danger: true,
        });
      } else {
        items.push({
          id: "delete",
          label: "删除记录",
          icon: "delete",
          danger: true,
        });
      }
    }
  } else if (contextMenuTarget.value === "header") {
    const field = contextMenuField.value;
    if (field) {
      items.push(
        { id: "sort-asc", label: "升序排列", icon: "sort" },
        { id: "sort-desc", label: "降序排列", icon: "sort" },
        { divider: true, id: "divider1" },
      );

      const isFrozen = frozenFields.value.some((f) => f.id === field.id);
      if (isFrozen) {
        items.push({ id: "unfreeze", label: "取消冻结", icon: "freeze" });
      } else {
        items.push({ id: "freeze", label: "冻结列", icon: "freeze" });
      }

      items.push(
        { divider: true, id: "divider2" },
        { id: "hide-field", label: "隐藏字段", icon: "hide" },
        { id: "edit-field", label: "编辑字段属性", icon: "settings" },
      );
    }
  }

  return items;
});

const handleCellUpdate = async (
  record: RecordEntity,
  fieldId: string,
  value: CellValue,
) => {
  // 1. 检查必填字段
  const field = fields.value.find((f) => f.id === fieldId);
  if (field && isFieldRequired(field) && isValueEmpty(value)) {
    ElMessage.error(`请填写必填字段：${field.name}`);
    editingCell.value = null;
    return;
  }

  // 2. 使用 JSON.parse(JSON.stringify()) 确保所有值都是纯 JavaScript 对象
  // 避免响应式对象导致的 IndexedDB 克隆错误
  const plainValues = JSON.parse(JSON.stringify(record.values));
  const plainValue = JSON.parse(JSON.stringify(value));
  const newValues = { ...plainValues, [fieldId]: plainValue };
  await recordService.updateRecord(record.id, { values: newValues });
  await baseStore.loadTable(record.tableId);
  editingCell.value = null;
};

const handleRowClick = (record: RecordEntity, event: MouseEvent) => {
  // 如果点击的是放大按钮，不处理行选择
  const target = event.target as HTMLElement;
  if (target.closest(".expand-btn")) {
    return;
  }

  if (event.ctrlKey || event.metaKey) {
    const index = selectedRows.value.indexOf(record.id);
    if (index > -1) {
      selectedRows.value.splice(index, 1);
    } else {
      selectedRows.value.push(record.id);
    }
  } else if (event.shiftKey && selectedRows.value.length > 0) {
    const lastSelectedId = selectedRows.value[selectedRows.value.length - 1];
    const lastIndex = sortedRecords.value.findIndex(
      (r) => r.id === lastSelectedId,
    );
    const currentIndex = sortedRecords.value.findIndex(
      (r) => r.id === record.id,
    );

    const start = Math.min(lastIndex, currentIndex);
    const end = Math.max(lastIndex, currentIndex);

    const newSelection = sortedRecords.value
      .slice(start, end + 1)
      .map((r) => r.id);
    selectedRows.value = [...new Set([...selectedRows.value, ...newSelection])];
  } else {
    selectedRows.value = [record.id];
  }

  emit("record-select", record);
  emit(
    "records-select",
    selectedRows.value
      .map((id) => sortedRecords.value.find((r) => r.id === id)!)
      .filter(Boolean),
  );
};

// 处理放大按钮点击
const handleExpandRecord = (record: RecordEntity) => {
  expandedRecord.value = record;
  expandDialogVisible.value = true;
};

// 切换行勾选状态
const toggleRowSelection = (recordId: string) => {
  const index = selectedRows.value.indexOf(recordId);
  if (index > -1) {
    selectedRows.value.splice(index, 1);
  } else {
    selectedRows.value.push(recordId);
  }
  // 触发选择事件
  emit(
    "records-select",
    selectedRows.value
      .map((id) => sortedRecords.value.find((r) => r.id === id)!)
      .filter(Boolean),
  );
};

// 处理弹窗保存
const handleRecordSave = async (
  recordId: string,
  values: Record<string, unknown>,
) => {
  try {
    await recordService.updateRecord(recordId, {
      values: values as Record<string, CellValue>,
    });
    // 重新加载记录列表
    await tableStore.refreshRecords(tableStore.currentTable?.id || "");
    ElMessage.success("保存成功");
    expandDialogVisible.value = false;
    expandedRecord.value = null;
  } catch (error) {
    console.error("Error saving record-tv:", error);
    ElMessage.error("保存失败");
  }
};

const handleRowContextMenu = (record: RecordEntity, event: MouseEvent) => {
  if (!selectedRows.value.includes(record.id)) {
    selectedRows.value = [record.id];
  }

  contextMenuTarget.value = "row";
  contextMenuRecord.value = record;
  contextMenuX.value = event.clientX;
  contextMenuY.value = event.clientY;
  contextMenuVisible.value = true;
};

const handleHeaderContextMenu = (field: FieldEntity, event: MouseEvent) => {
  contextMenuTarget.value = "header";
  contextMenuField.value = field;
  contextMenuX.value = event.clientX;
  contextMenuY.value = event.clientY;
  contextMenuVisible.value = true;
};

const handleContextMenuSelect = async (item: any) => {
  const { id } = item;

  switch (id) {
    case "edit":
      if (contextMenuRecord.value) {
        editingCell.value = {
          recordId: contextMenuRecord.value.id,
          fieldId: fields.value[0]?.id || "",
        };
      }
      break;

    case "duplicate":
      if (contextMenuRecord.value) {
        const newRecord = await recordService.createRecord({
          tableId: contextMenuRecord.value.tableId,
          values: { ...contextMenuRecord.value.values },
        });
        if (newRecord) {
          await baseStore.loadTable(contextMenuRecord.value.tableId);
        }
      }
      break;

    case "delete":
      if (contextMenuRecord.value) {
        try {
          await ElMessageBox.confirm(
            "确定要删除这条记录吗？此操作不可恢复。",
            "删除确认",
            {
              confirmButtonText: "确定删除",
              cancelButtonText: "取消",
              type: "warning",
              confirmButtonClass: "el-button--danger",
            },
          );
          await tableStore.deleteRecord(contextMenuRecord.value.id);
          selectedRows.value = [];
          emit("record-delete", [contextMenuRecord.value.id]);
          ElMessage.success("记录删除成功");
        } catch (error: any) {
          if (error !== "cancel") {
            console.error("删除记录失败:", error);
            ElMessage.error("删除记录失败");
          }
        }
      }
      break;

    case "delete-selected":
      try {
        await ElMessageBox.confirm(
          `确定要删除选中的 ${selectedRows.value.length} 条记录吗？此操作不可恢复。`,
          "批量删除确认",
          {
            confirmButtonText: "确定删除",
            cancelButtonText: "取消",
            type: "warning",
            confirmButtonClass: "el-button--danger",
          },
        );
        await tableStore.batchDeleteRecords(selectedRows.value);
        emit("record-delete", [...selectedRows.value]);
        selectedRows.value = [];
        ElMessage.success("记录删除成功");
      } catch (error: any) {
        if (error !== "cancel") {
          console.error("删除记录失败:", error);
          ElMessage.error("删除记录失败");
        }
      }
      break;

    case "sort-asc":
      if (contextMenuField.value && currentView.value) {
        await viewStore.updateSorts(currentView.value.id, [
          { fieldId: contextMenuField.value.id, direction: "asc" },
        ]);
        ElMessage.success(`已按 ${contextMenuField.value.name} 升序排列`);
      }
      break;

    case "sort-desc":
      if (contextMenuField.value && currentView.value) {
        await viewStore.updateSorts(currentView.value.id, [
          { fieldId: contextMenuField.value.id, direction: "desc" },
        ]);
        ElMessage.success(`已按 ${contextMenuField.value.name} 降序排列`);
      }
      break;

    case "freeze":
      if (contextMenuField.value && currentView.value) {
        const newFrozen = [
          ...currentView.value.frozenFields,
          contextMenuField.value.id,
        ];
        await viewStore.updateFrozenFields(currentView.value.id, newFrozen);
        ElMessage.success(`已冻结列：${contextMenuField.value.name}`);
      }
      break;

    case "unfreeze":
      if (contextMenuField.value && currentView.value) {
        const newFrozen = currentView.value.frozenFields.filter(
          (fid) => fid !== contextMenuField.value!.id,
        );
        await viewStore.updateFrozenFields(currentView.value.id, newFrozen);
        ElMessage.success(`已取消冻结列：${contextMenuField.value.name}`);
      }
      break;

    case "hide-field":
      if (contextMenuField.value && currentView.value) {
        // 检查字段是否已经在隐藏列表中
        if (
          currentView.value.hiddenFields.includes(contextMenuField.value.id)
        ) {
          ElMessage.warning(
            `字段 "${contextMenuField.value.name}" 已经是隐藏状态`,
          );
          break;
        }
        const newHidden = [
          ...currentView.value.hiddenFields,
          contextMenuField.value.id,
        ];
        await viewStore.updateHiddenFields(currentView.value.id, newHidden);
        ElMessage.success(`已隐藏字段：${contextMenuField.value.name}`);
      }
      break;

    case "edit-field":
      if (contextMenuField.value) {
        editingFieldId.value = contextMenuField.value.id;
        fieldDialogVisible.value = true;
      }
      break;
  }

  contextMenuVisible.value = false;
};

const handleSort = async (fieldId: string, direction: "asc" | "desc") => {
  if (currentView.value) {
    const currentSorts = viewStore.currentSorts as SortConfig[];
    const existingSortIndex = currentSorts.findIndex(
      (s) => s.fieldId === fieldId,
    );
    const newSorts = [...currentSorts];

    if (existingSortIndex > -1) {
      newSorts[existingSortIndex] = { fieldId, direction };
    } else {
      newSorts.push({ fieldId, direction });
    }

    await viewStore.updateSorts(currentView.value.id, newSorts as SortConfig[]);
  }
};

const handleColumnResize = (fieldId: string, width: number) => {
  columnWidths.value[fieldId] = width;
};

const handleRowDragStart = (event: DragEvent, record: RecordEntity) => {
  isDraggingRow.value = true;
  draggedRowId.value = record.id;

  if (event.dataTransfer) {
    event.dataTransfer.effectAllowed = "move";
    event.dataTransfer.setData("text/plain", record.id);
  }
};

const handleRowDragEnd = () => {
  isDraggingRow.value = false;
  draggedRowId.value = null;
};

const handleKeyDown = async (event: KeyboardEvent) => {
  if (editingCell.value) return;

  const currentIndex =
    selectedRows.value.length > 0
      ? sortedRecords.value.findIndex((r) => r.id === selectedRows.value[0])
      : -1;

  switch (event.key) {
    case "ArrowUp":
      event.preventDefault();
      if (currentIndex > 0) {
        const newRecord = sortedRecords.value[currentIndex - 1];
        selectedRows.value = [newRecord.id];
        emit("record-select", newRecord);
      }
      break;

    case "ArrowDown":
      event.preventDefault();
      if (currentIndex < sortedRecords.value.length - 1) {
        const newRecord = sortedRecords.value[currentIndex + 1];
        selectedRows.value = [newRecord.id];
        emit("record-select", newRecord);
      }
      break;

    case "Delete":
    case "Backspace":
      if (selectedRows.value.length > 0 && !props.readonly) {
        event.preventDefault();
        try {
          await ElMessageBox.confirm(
            `确定要删除选中的 ${selectedRows.value.length} 条记录吗？此操作不可恢复。`,
            "批量删除确认",
            {
              confirmButtonText: "确定删除",
              cancelButtonText: "取消",
              type: "warning",
              confirmButtonClass: "el-button--danger",
            },
          );
          await tableStore.batchDeleteRecords(selectedRows.value);
          emit("record-delete", [...selectedRows.value]);
          selectedRows.value = [];
          ElMessage.success("记录删除成功");
        } catch (error: any) {
          if (error !== "cancel") {
            console.error("删除记录失败:", error);
            ElMessage.error("删除记录失败");
          }
        }
      }
      break;

    case "a":
      if (event.ctrlKey || event.metaKey) {
        event.preventDefault();
        selectedRows.value = sortedRecords.value.map((r) => r.id);
        emit("records-select", sortedRecords.value);
      }
      break;

    case "Escape":
      selectedRows.value = [];
      emit("record-select", null);
      break;

    case "Enter":
      if (selectedRows.value.length === 1 && !props.readonly) {
        const record = sortedRecords.value.find(
          (r) => r.id === selectedRows.value[0],
        );
        if (record && visibleFields.value.length > 0) {
          editingCell.value = {
            recordId: record.id,
            fieldId: visibleFields.value[0].id,
          };
        }
      }
      break;
  }
};

const addNewRecord = async () => {
  // 触发添加记录事件，由父组件处理打开对话框
  emit("add-record");
};

const getColumnWidth = (fieldId: string): number => {
  return columnWidths.value[fieldId] || 150;
};

const isFieldFrozen = (fieldId: string): boolean => {
  return frozenFields.value.some((f) => f.id === fieldId);
};

// 计算冻结列的 left 位置
const getFrozenFieldLeft = (fieldId: string): number => {
  if (!isFieldFrozen(fieldId)) return 0;

  // 序号列宽度
  const selectorWidth = 70;

  // 计算在当前冻结列之前的所有冻结列的宽度总和
  let leftOffset = selectorWidth;

  for (const field of visibleFields.value) {
    if (field.id === fieldId) break;
    if (isFieldFrozen(field.id)) {
      leftOffset += getColumnWidth(field.id);
    }
  }

  return leftOffset;
};

const getFieldSortDirection = (fieldId: string): "asc" | "desc" | null => {
  const sorts = viewStore.currentSorts as SortConfig[];
  const sort = sorts.find((s) => s.fieldId === fieldId);
  return sort?.direction || null;
};

// 字段更新后的处理
const handleFieldUpdated = async (_updatedField: FieldEntity) => {
  // 刷新字段列表
  if (baseStore.currentTable) {
    await baseStore.loadTable(baseStore.currentTable.id);
  }
  ElMessage.success("字段更新成功");
};

// 字段删除后的处理
const handleFieldDeleted = async (fieldId: string) => {
  // 刷新字段列表
  if (baseStore.currentTable) {
    await baseStore.loadTable(baseStore.currentTable.id);
  }
  // 如果删除的是当前正在编辑的单元格所在字段，清除编辑状态
  if (editingCell.value?.fieldId === fieldId) {
    editingCell.value = null;
  }
  ElMessage.success("字段删除成功");
};

// 字段可见性变化处理（视图级隐藏/显示）
const handleFieldVisibilityChanged = async (
  fieldId: string,
  isVisible: boolean,
) => {
  if (!currentView.value) return;

  try {
    let newHiddenFields: string[];

    if (isVisible) {
      // 从隐藏列表中移除
      newHiddenFields = currentView.value.hiddenFields.filter(
        (id) => id !== fieldId,
      );
    } else {
      // 添加到隐藏列表
      newHiddenFields = [...currentView.value.hiddenFields, fieldId];
    }

    await viewStore.updateHiddenFields(currentView.value.id, newHiddenFields);
    // 注意：不需要调用 loadTable，因为 visibleFields 计算属性会自动响应 currentView 的变化
  } catch (error) {
    ElMessage.error("更新字段可见性失败");
  }
};

onMounted(() => {
  document.addEventListener("keydown", handleKeyDown);
});

onBeforeUnmount(() => {
  document.removeEventListener("keydown", handleKeyDown);
});

defineExpose({
  addNewRecord,
  selectedRows,
  refresh: () => baseStore.loadTable(baseStore.currentTable?.id || ""),
});
</script>

<template>
  <div class="table-view">
    <div class="table-container" v-if="visibleFields.length > 0">
      <div class="table-header">
        <div class="header-row">
          <div class="row-selector-header">
            <input
              type="checkbox"
              :checked="
                selectedRows.length === sortedRecords.length &&
                sortedRecords.length > 0
              "
              :indeterminate="
                selectedRows.length > 0 &&
                selectedRows.length < sortedRecords.length
              "
              @change="
                (e) => {
                  if ((e.target as HTMLInputElement).checked) {
                    selectedRows = sortedRecords.map((r) => r.id);
                  } else {
                    selectedRows = [];
                  }
                }
              " />
          </div>
          <div
            v-for="field in visibleFields"
            :key="field.id"
            class="header-cell"
            :class="{ 'is-frozen': isFieldFrozen(field.id) }"
            :style="{
              width: `${getColumnWidth(field.id)}px`,
              left: isFieldFrozen(field.id)
                ? `${getFrozenFieldLeft(field.id)}px`
                : 'auto',
            }">
            <TableHeader
              :field="field"
              :sort-direction="getFieldSortDirection(field.id)"
              :is-frozen="isFieldFrozen(field.id)"
              @sort="(dir) => handleSort(field.id, dir)"
              @resize="(w) => handleColumnResize(field.id, w)"
              @contextmenu="(e) => handleHeaderContextMenu(field, e)" />
          </div>
        </div>
      </div>

      <div class="table-body">
        <TableRow
          v-for="(record, index) in sortedRecords"
          :key="record.id"
          :record="record"
          :index="index"
          :is-selected="selectedRows.includes(record.id)"
          :is-hovered="hoveredRowId === record.id"
          :row-height="rowHeight"
          @click="(e) => handleRowClick(record, e)"
          @contextmenu="(e) => handleRowContextMenu(record, e)"
          @dragstart="(e) => handleRowDragStart(e, record)"
          @dragend="handleRowDragEnd">
          <div class="row-selector">
            <!-- 自定义勾选按钮 -->
            <div
              class="custom-checkbox"
              :class="{ 'is-checked': selectedRows.includes(record.id) }"
              @click.stop="toggleRowSelection(record.id)">
              <div class="checkbox-inner">
                <ElIcon v-if="selectedRows.includes(record.id)"
                  ><Check
                /></ElIcon>
              </div>
            </div>
            <!-- 放大按钮 - 与勾选按钮并列显示 -->
            <button
              class="expand-btn"
              :class="{ 'is-visible': selectedRows.includes(record.id) }"
              @click.stop="handleExpandRecord(record)"
              title="查看/编辑记录">
              <ElIcon><ZoomIn /></ElIcon>
            </button>
            <span class="row-number">{{ index + 1 }}</span>
          </div>

          <div
            v-for="field in visibleFields"
            :key="field.id"
            class="table-cell-wrapper"
            :class="{
              'is-frozen': isFieldFrozen(field.id),
              'is-editing':
                editingCell?.recordId === record.id &&
                editingCell?.fieldId === field.id,
            }"
            :style="{
              width: `${getColumnWidth(field.id)}px`,
              left: isFieldFrozen(field.id)
                ? `${getFrozenFieldLeft(field.id)}px`
                : 'auto',
            }">
            <TableCell
              :record="record"
              :field="field"
              :fields="fields"
              :readonly="readonly"
              :selected="
                editingCell?.recordId === record.id &&
                editingCell?.fieldId === field.id
              "
              @update="(value) => handleCellUpdate(record, field.id, value)"
              @edit="
                (active) => {
                  if (active) {
                    editingCell = { recordId: record.id, fieldId: field.id };
                  } else if (
                    editingCell?.recordId === record.id &&
                    editingCell?.fieldId === field.id
                  ) {
                    editingCell = null;
                  }
                }
              "
              @open-detail="handleExpandRecord(record)" />
          </div>
        </TableRow>

        <div v-if="!readonly" class="add-row-button" @click="addNewRecord">
          <span class="add-icon">+</span>
          <span>添加记录</span>
        </div>
      </div>
    </div>

    <div v-else class="empty-state">
      <p>暂无字段，请先添加字段</p>
    </div>

    <ContextMenu
      :items="contextMenuItems"
      :x="contextMenuX"
      :y="contextMenuY"
      :visible="contextMenuVisible"
      @update:visible="contextMenuVisible = $event"
      @select="handleContextMenuSelect" />

    <!-- 记录详情/编辑抽屉 -->
    <RecordDetailDrawer
      v-model:visible="expandDialogVisible"
      :record="expandedRecord"
      :fields="fields"
      :size="drawerSize"
      :readonly="readonly"
      @save="handleRecordSave" />

    <!-- 字段编辑对话框 -->
    <FieldDialog
      v-model:visible="fieldDialogVisible"
      :table-id="baseStore.currentTable?.id || ''"
      :fields="fields"
      :edit-field-id="editingFieldId || undefined"
      @field-updated="handleFieldUpdated"
      @field-deleted="handleFieldDeleted"
      @field-visibility-changed="handleFieldVisibilityChanged" />
  </div>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;
@use "@/assets/styles/mixins" as *;

.table-view {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: auto;
  background-color: $surface-color;

  // 自定义滚动条样式
  &::-webkit-scrollbar {
    width: 8px;
    height: 8px;
  }

  &::-webkit-scrollbar-track {
    background: $gray-100;
    border-radius: $border-radius-sm;
  }

  &::-webkit-scrollbar-thumb {
    background: $gray-300;
    border-radius: $border-radius-sm;

    &:hover {
      background: $gray-400;
    }
  }

  &::-webkit-scrollbar-corner {
    background: $gray-100;
  }
}

.table-container {
  min-width: max-content;
}

.table-header {
  position: sticky;
  top: 0;
  z-index: 10;
  background-color: $gray-50;
}

.header-row {
  display: flex;
  border-bottom: 1px solid $gray-200;
  height: 40px;
}

.header-cell {
  flex-shrink: 0;
  border-right: 1px solid $gray-200;

  &.is-frozen {
    position: sticky;
    // left 值通过内联样式动态设置
    z-index: 5;
    background-color: $gray-50;
    box-shadow: 2px 0 4px rgba(0, 0, 0, 0.05);
  }
}

.row-selector-header {
  width: 70px;
  min-width: 70px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-right: 1px solid $gray-200;
  background-color: $gray-50;
  // 冻结序号列表头
  position: sticky;
  left: 0;
  z-index: 10;

  input[type="checkbox"] {
    width: 16px;
    height: 16px;
    cursor: pointer;
    accent-color: $primary-color;
  }
}

.table-body {
  position: relative;
}

.row-selector {
  width: 70px;
  min-width: 70px;
  display: flex;
  align-items: center;
  justify-content: flex-start;
  gap: 8px;
  padding: 0 8px;
  border-right: 1px solid $gray-200;
  background-color: inherit;
  // 冻结序号列
  position: sticky;
  left: 0;
  z-index: 5;

  // 自定义勾选按钮
  .custom-checkbox {
    width: 16px;
    height: 16px;
    border-radius: 3px;
    border: 2px solid #cccccc;
    background-color: transparent;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s ease;
    flex-shrink: 0;
    opacity: 0; // 默认隐藏

    .checkbox-inner {
      width: 100%;
      height: 100%;
      display: flex;
      align-items: center;
      justify-content: center;

      .el-icon {
        font-size: 12px;
        color: white;
        font-weight: bold;
      }
    }

    // 未勾选但悬停状态 - 灰色边框
    &:hover {
      border-color: #999999;
    }

    // 已勾选状态 - 蓝色填充背景 + 白色对勾
    &.is-checked {
      opacity: 1 !important;
      background-color: $primary-color;
      border-color: $primary-color;
    }
  }

  .row-number {
    font-size: $font-size-xs;
    color: $gray-400;
    transition: opacity $transition-fast;
    position: absolute;
    right: 8px;
  }

  .expand-btn {
    width: 20px;
    height: 20px;
    display: flex;
    align-items: center;
    justify-content: center;
    border: none;
    border-radius: $border-radius-sm;
    background-color: #999999;
    color: white;
    cursor: pointer;
    opacity: 0;
    transform: scale(0.8);
    transition: all $transition-fast;
    z-index: 10;
    flex-shrink: 0;
    margin-left: 4px;

    &:hover {
      background-color: #666666;
      transform: scale(1.1);
    }

    &.is-visible {
      opacity: 1;
      transform: scale(1);
    }

    .el-icon {
      font-size: 12px;
    }
  }

  // 悬停时同时显示勾选按钮和放大按钮
  &:hover {
    .custom-checkbox:not(.is-checked) {
      opacity: 1;
    }

    // 悬停时显示放大按钮
    .expand-btn {
      opacity: 1;
      transform: scale(1);
    }

    .row-number {
      opacity: 0;
    }
  }
}

// 行被选中时的样式
:deep(.table-row.is-selected) {
  .row-selector {
    // 已勾选行的勾选按钮持续可见
    .custom-checkbox {
      opacity: 1;
    }

    .expand-btn {
      opacity: 1;
      transform: scale(1);
    }

    .row-number {
      opacity: 0;
    }
  }
}

// 行被选中且悬停时的样式
:deep(.table-row.is-selected.is-hovered) {
  .row-selector {
    .custom-checkbox.is-checked {
      background-color: darken($primary-color, 5%);
      border-color: darken($primary-color, 5%);
    }
  }
}

.table-cell-wrapper {
  flex-shrink: 0;
  border-right: 1px solid $gray-200;

  &.is-frozen {
    position: sticky;
    // left 值通过内联样式动态设置
    z-index: 2;
    background-color: inherit;
    box-shadow: 2px 0 4px rgba(0, 0, 0, 0.05);
  }

  &.is-editing {
    z-index: 10;
  }
}

.add-row-button {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 12px 16px;
  color: $gray-500;
  cursor: pointer;
  transition: all $transition-fast;
  border-radius: $border-radius-md;
  margin: 8px;

  &:hover {
    background-color: rgba($primary-color, 0.05);
    color: $primary-color;
  }

  .add-icon {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 24px;
    height: 24px;
    border: 1.5px dashed currentColor;
    border-radius: $border-radius-md;
    font-size: 14px;
    transition: all $transition-fast;

    &:hover {
      border-style: solid;
      background-color: rgba($primary-color, 0.1);
    }
  }
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 200px;
  color: $text-secondary;
}
</style>
