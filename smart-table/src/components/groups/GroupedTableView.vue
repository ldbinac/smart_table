<script setup lang="ts">
import { ref, computed, watch, nextTick } from "vue";
import type { FieldEntity, RecordEntity } from "../../db/schema";
import type { GroupNode } from "../../utils/group";
import { FieldType, getFieldTypeIconComponent } from "@/types/fields";
import { groupRecords } from "../../utils/group";
import dayjs from "dayjs";
import { truncateRichText } from "@/utils/helpers";
import { FormulaEngine } from "@/utils/formula/engine";
import {
  ZoomIn,
  Paperclip,
  Lock,
} from "@element-plus/icons-vue";
import ContextMenu from "@/components/common/ContextMenu.vue";
import MemberDisplay from "@/components/common/MemberDisplay.vue";
import type { SortConfig } from "@/types";
import LinkField from "@/components/fields/LinkField/LinkField.vue";
import type { LinkedRecord } from "@/types/link";
import { linkApiService } from "@/services/api/linkApiService";

interface Props {
  fields: FieldEntity[];
  records: RecordEntity[];
  groupBy: string[];
  rowHeight?: "short" | "medium" | "tall";
  frozenFields?: string[];
  readonly?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  groupBy: () => [],
  rowHeight: "medium",
  frozenFields: () => [],
  readonly: false,
});

interface GroupLevelInfo {
  fieldId: string;
  fieldName: string;
  value: string;
  valueId?: string;
}

const emit = defineEmits<{
  (e: "rowClick", record: RecordEntity): void;
  (e: "cellClick", record: RecordEntity, field: FieldEntity): void;
  (
    e: "addRecord",
    groupInfo: {
      groupFieldId?: string;
      groupId?: string;
      groupName?: string;
      groupLevels?: GroupLevelInfo[];
    },
  ): void;
  (e: "record-select", record: RecordEntity | null): void;
  (e: "records-select", records: RecordEntity[]): void;
  (e: "expand-record", record: RecordEntity): void;
  (e: "duplicate-record", record: RecordEntity): void;
  (e: "delete-records", records: RecordEntity[]): void;
  (e: "sort", fieldId: string, direction: "asc" | "desc"): void;
  (e: "freeze-field", fieldId: string): void;
  (e: "unfreeze-field", fieldId: string): void;
  (e: "hide-field", fieldId: string): void;
  (e: "edit-field", fieldId: string): void;
}>();

const groupNodes = ref<GroupNode[]>([]);
const expandedKeys = ref<Set<string>>(new Set());
const selectedRows = ref<Set<string>>(new Set());
const hoveredRowId = ref<string | null>(null);

// 右键菜单相关状态
const contextMenuVisible = ref(false);
const contextMenuX = ref(0);
const contextMenuY = ref(0);
const contextMenuTarget = ref<"row" | "header">("row");
const contextMenuField = ref<FieldEntity | null>(null);
const contextMenuRecord = ref<RecordEntity | null>(null);

// 排序配置
const sorts = ref<SortConfig[]>([]);

// 使用 props.frozenFields 替代本地状态
const frozenFields = computed(() => props.frozenFields || []);

// 列宽管理
const columnWidths = ref<Record<string, number>>({});

// 行高与标准表格视图保持一致
const rowHeightMap = {
  short: "28px",
  medium: "36px",
  tall: "48px",
};

// 获取列宽
function getColumnWidth(fieldId: string): string {
  return `${columnWidths.value[fieldId] || 150}px`;
}

// 列宽调整相关状态
const resizingFieldId = ref<string | null>(null);
const resizeStartX = ref(0);
const resizeStartWidth = ref(0);

// 开始调整列宽
function startResize(event: MouseEvent, fieldId: string) {
  resizingFieldId.value = fieldId;
  resizeStartX.value = event.clientX;
  resizeStartWidth.value = columnWidths.value[fieldId] || 150;

  document.addEventListener("mousemove", onResize);
  document.addEventListener("mouseup", stopResize);
}

// 调整中
function onResize(event: MouseEvent) {
  if (!resizingFieldId.value) return;

  const diff = event.clientX - resizeStartX.value;
  const newWidth = Math.max(60, resizeStartWidth.value + diff);
  columnWidths.value[resizingFieldId.value] = newWidth;
}

// 停止调整
function stopResize() {
  resizingFieldId.value = null;
  document.removeEventListener("mousemove", onResize);
  document.removeEventListener("mouseup", stopResize);
}

// 计算数据行的斑马纹索引（只计算数据行，不包括分组行和添加按钮行）
const dataRowIndices = computed(() => {
  const indices = new Map<string, number>();
  let dataRowCount = 0;
  flattenedData.value.forEach((item) => {
    if (item.type === "record" && item.record) {
      indices.set(item.record.id, dataRowCount);
      dataRowCount++;
    }
  });
  return indices;
});

// 判断是否为偶数行（用于斑马纹）
function isEvenRow(recordId: string): boolean {
  const index = dataRowIndices.value.get(recordId);
  return index !== undefined && index % 2 === 1;
}

// 右键菜单项
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

      if (selectedRows.value.size > 1) {
        items.push({
          id: "delete-selected",
          label: `删除选中的 ${selectedRows.value.size} 条记录`,
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

      const isFrozen = frozenFields.value.includes(field.id);
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

// 处理表头右键菜单
function handleHeaderContextMenu(field: FieldEntity, event: MouseEvent) {
  event.preventDefault();
  contextMenuTarget.value = "header";
  contextMenuField.value = field;
  contextMenuX.value = event.clientX;
  contextMenuY.value = event.clientY;
  contextMenuVisible.value = true;
}

// 处理行右键菜单
function handleRowContextMenu(record: RecordEntity, event: MouseEvent) {
  event.preventDefault();
  if (!selectedRows.value.has(record.id)) {
    selectedRows.value.clear();
    selectedRows.value.add(record.id);
    emitSelectedRecords();
  }
  contextMenuTarget.value = "row";
  contextMenuRecord.value = record;
  contextMenuX.value = event.clientX;
  contextMenuY.value = event.clientY;
  contextMenuVisible.value = true;
}

// 处理右键菜单选择
async function handleContextMenuSelect(item: any) {
  const { id } = item;

  switch (id) {
    case "edit":
      if (contextMenuRecord.value) {
        emit("cellClick", contextMenuRecord.value, props.fields[0]);
      }
      break;

    case "duplicate":
      if (contextMenuRecord.value) {
        emit("duplicate-record", contextMenuRecord.value);
      }
      break;

    case "delete":
      if (contextMenuRecord.value) {
        // 触发删除事件给父组件处理
        emit("delete-records", [contextMenuRecord.value]);
      }
      break;

    case "delete-selected":
      emit(
        "delete-records",
        Array.from(selectedRows.value)
          .map((id) => props.records.find((r) => r.id === id)!)
          .filter(Boolean),
      );
      break;

    case "sort-asc":
      if (contextMenuField.value) {
        emit("sort", contextMenuField.value.id, "asc");
      }
      break;

    case "sort-desc":
      if (contextMenuField.value) {
        emit("sort", contextMenuField.value.id, "desc");
      }
      break;

    case "freeze":
      if (contextMenuField.value) {
        emit("freeze-field", contextMenuField.value.id);
      }
      break;

    case "unfreeze":
      if (contextMenuField.value) {
        emit("unfreeze-field", contextMenuField.value.id);
      }
      break;

    case "hide-field":
      if (contextMenuField.value) {
        emit("hide-field", contextMenuField.value.id);
      }
      break;

    case "edit-field":
      if (contextMenuField.value) {
        emit("edit-field", contextMenuField.value.id);
      }
      break;
  }

  contextMenuVisible.value = false;
}

// 获取字段排序方向
function getFieldSortDirection(fieldId: string): "asc" | "desc" | null {
  const sort = sorts.value.find((s) => s.fieldId === fieldId);
  return sort?.direction || null;
}

// 处理字段排序
function handleFieldSort(fieldId: string, direction: "asc" | "desc") {
  const existingSortIndex = sorts.value.findIndex((s) => s.fieldId === fieldId);
  const newSorts = [...sorts.value];

  if (existingSortIndex > -1) {
    newSorts[existingSortIndex] = { fieldId, direction };
  } else {
    newSorts.push({ fieldId, direction });
  }

  sorts.value = newSorts;
  emit("sort", fieldId, direction);
}

// 检查字段是否冻结
function isFieldFrozen(fieldId: string): boolean {
  return frozenFields.value.includes(fieldId);
}

// 计算冻结列的 left 位置
function getFrozenFieldLeft(fieldId: string): number {
  if (!isFieldFrozen(fieldId)) return 0;

  // 序号列(70px) + 不计算展开列宽度，否则会导致左侧空白太多。
  const fixedWidth = 70;

  // 计算在当前冻结列之前的所有冻结列的宽度总和
  let leftOffset = fixedWidth;

  for (const field of visibleFields.value) {
    if (field.id === fieldId) break;
    if (isFieldFrozen(field.id)) {
      leftOffset += parseInt(getColumnWidth(field.id));
    }
  }

  return leftOffset;
}

const visibleFields = computed(() => {
  return props.fields.filter((f) => !f.isSystem);
});

// 获取分组字段信息
const groupFields = computed(() => {
  return props.groupBy
    .map((id) => props.fields.find((f) => f.id === id))
    .filter(Boolean) as FieldEntity[];
});

// 扁平化数据，包含分组行、数据行和新增按钮行
interface FlattenedItem {
  type: "group" | "record" | "addButton";
  node?: GroupNode;
  record?: RecordEntity;
  level: number;
  groupField?: FieldEntity;
  groupKey: string;
  parentGroupKey?: string;
  groupValue?: string;
  rowIndex?: number;
}

// 强制刷新计数器，用于触发 computed 重新计算
const refreshCounter = ref(0);

const flattenedData = computed(() => {
  refreshCounter.value;

  const result: FlattenedItem[] = [];
  // 用于跟踪每个分组内的行号
  const groupRowCounters = new Map<string, number>();

  const processNodes = (
    nodes: GroupNode[],
    level: number,
    parentGroupKey?: string,
  ) => {
    for (const node of nodes) {
      const groupField = groupFields.value[level];
      const currentGroupKey = parentGroupKey
        ? `${parentGroupKey}-${node.key}`
        : node.key;

      result.push({
        type: "group",
        node,
        level,
        groupField,
        groupKey: currentGroupKey,
        parentGroupKey,
        groupValue: node.value,
      });

      const isExpanded = expandedKeys.value.has(currentGroupKey);

      if (isExpanded) {
        if (node.children && node.children.length > 0) {
          processNodes(node.children, level + 1, currentGroupKey);
        } else if (node.records.length > 0) {
          // 重置当前分组的行号计数器
          groupRowCounters.set(currentGroupKey, 0);
          for (const record of node.records) {
            // 获取当前分组的行号并递增
            const currentRowNum =
              (groupRowCounters.get(currentGroupKey) || 0) + 1;
            groupRowCounters.set(currentGroupKey, currentRowNum);

            result.push({
              type: "record",
              record,
              level: level + 1,
              groupKey: currentGroupKey,
              parentGroupKey: currentGroupKey,
              rowIndex: currentRowNum,
            });
          }
          result.push({
            type: "addButton",
            level: level + 1,
            groupField,
            groupKey: currentGroupKey,
            parentGroupKey: currentGroupKey,
            groupValue: node.value,
          });
        } else {
          result.push({
            type: "addButton",
            level: level + 1,
            groupField,
            groupKey: currentGroupKey,
            parentGroupKey: currentGroupKey,
            groupValue: node.value,
          });
        }
      }
    }
  };

  if (groupNodes.value.length > 0) {
    processNodes(groupNodes.value, 0);
  } else {
    // 无分组模式下使用全局行号
    let globalRowIndex = 0;
    for (const record of props.records) {
      globalRowIndex++;
      result.push({
        type: "record",
        record,
        level: 0,
        groupKey: "",
        rowIndex: globalRowIndex,
      });
    }
  }

  return result;
});

const isGrouped = computed(() => props.groupBy.length > 0);

// 是否全选
const isAllSelected = computed(() => {
  const recordItems = flattenedData.value.filter(
    (item) => item.type === "record",
  );
  if (recordItems.length === 0) return false;
  return recordItems.every((item) => selectedRows.value.has(item.record!.id));
});

// 计算所有分组key
const allGroupKeys = computed(() => {
  const keys: string[] = [];
  const collectKeys = (nodes: GroupNode[], parentGroupKey?: string) => {
    for (const node of nodes) {
      const currentGroupKey = parentGroupKey
        ? `${parentGroupKey}-${node.key}`
        : node.key;
      keys.push(currentGroupKey);
      if (node.children) {
        collectKeys(node.children, currentGroupKey);
      }
    }
  };
  collectKeys(groupNodes.value);
  return keys;
});

// 是否全部展开（用于按钮状态）
const isAllExpanded = computed(() => {
  if (allGroupKeys.value.length === 0) return false;
  return allGroupKeys.value.every((key) => expandedKeys.value.has(key));
});

// 切换全部展开/折叠
function toggleExpandAll() {
  if (isAllExpanded.value) {
    // 当前全部展开，执行折叠
    expandedKeys.value.clear();
  } else {
    // 当前未全部展开，执行展开
    const collectKeys = (nodes: GroupNode[], parentGroupKey?: string) => {
      for (const node of nodes) {
        const currentGroupKey = parentGroupKey
          ? `${parentGroupKey}-${node.key}`
          : node.key;
        expandedKeys.value.add(currentGroupKey);
        if (node.children) {
          collectKeys(node.children, currentGroupKey);
        }
      }
    };
    collectKeys(groupNodes.value);
    // 延迟加载关联数据
    nextTick(() => {
      loadLinkDataForVisibleRecords();
    });
  }
  refreshCounter.value++;
}

function updateGroups() {
  if (props.groupBy.length === 0) {
    groupNodes.value = [];
    expandedKeys.value.clear();
    // 无分组模式下也加载关联数据
    nextTick(() => {
      loadLinkDataForVisibleRecords();
    });
    return;
  }

  groupNodes.value = groupRecords(
    props.records,
    { fieldIds: props.groupBy },
    props.fields,
  );

  const collectKeys = (nodes: GroupNode[], parentGroupKey?: string) => {
    for (const node of nodes) {
      const currentGroupKey = parentGroupKey
        ? `${parentGroupKey}-${node.key}`
        : node.key;
      expandedKeys.value.add(currentGroupKey);
      if (node.children) {
        collectKeys(node.children, currentGroupKey);
      }
    }
  };
  collectKeys(groupNodes.value);

  // 初始加载完成后加载关联数据
  nextTick(() => {
    loadLinkDataForVisibleRecords();
  });
}

watch(
  () => [props.records, props.groupBy],
  () => {
    updateGroups();
  },
  { deep: true, immediate: true },
);

function toggleGroup(groupKey: string) {
  const isExpanding = !expandedKeys.value.has(groupKey);
  if (isExpanding) {
    expandedKeys.value.add(groupKey);
    // 延迟加载关联数据，确保DOM已更新
    nextTick(() => {
      loadLinkDataForVisibleRecords();
    });
  } else {
    expandedKeys.value.delete(groupKey);
  }
  refreshCounter.value++;
}

// 加载可见记录的关联数据
function loadLinkDataForVisibleRecords() {
  // 获取所有可见的数据行
  const visibleRecords = flattenedData.value
    .filter((item) => item.type === "record" && item.record)
    .map((item) => item.record!);

  // 为每条记录的关联字段加载数据
  for (const record of visibleRecords) {
    for (const field of visibleFields.value) {
      if (field.type === FieldType.LINK) {
        const linkedIds = record.values[field.id] as string[] | null;
        if (linkedIds && linkedIds.length > 0) {
          // 检查是否已加载
          const existingData = recordLinkData.value.get(record.id)?.get(field.id);
          if (!existingData) {
            loadLinkedRecords(record, field);
          }
        }
      }
    }
  }
}

function isGroupExpanded(groupKey: string): boolean {
  return expandedKeys.value.has(groupKey);
}

// 获取选项信息
function getSelectOption(field: FieldEntity, value: string) {
  const options = (field.options?.choices || []) as Array<{
    id: string;
    name: string;
    color?: string;
  }>;
  return options.find((opt) => opt.id === value || opt.name === value);
}

// 获取单选显示值（带颜色）
function getSingleSelectDisplay(field: FieldEntity, value: unknown) {
  if (value === null || value === undefined) return null;
  const strValue = String(value);
  const option = getSelectOption(field, strValue);
  return option || { name: strValue, color: "#3370FF" };
}

// 获取多选显示值（带颜色）
function getMultiSelectDisplay(field: FieldEntity, value: unknown) {
  if (!Array.isArray(value) || value.length === 0) return [];
  return value.map((v) => {
    const strValue = String(v);
    const option = getSelectOption(field, strValue);
    return option || { name: strValue, color: "#3370FF" };
  });
}

// 获取日期显示值
function getDateDisplay(field: FieldEntity, value: unknown): string {
  if (value === null || value === undefined || value === "") return "";

  // 根据字段类型判断是否显示时间
  const isDateTime = field.type === FieldType.DATE_TIME;
  const format = isDateTime ? "YYYY-MM-DD HH:mm:ss" : "YYYY-MM-DD";

  // 处理字符串格式的日期（如 "2024-01-15"）
  if (typeof value === "string") {
    // 如果是标准日期格式，直接返回
    if (/^\d{4}-\d{2}-\d{2}/.test(value)) {
      return value.substring(0, isDateTime ? 19 : 10);
    }
    // 尝试解析为数字时间戳
    const num = parseInt(value);
    if (!isNaN(num) && num > 0) {
      // 判断是秒级还是毫秒级时间戳
      const msTimestamp = num < 1e10 ? num * 1000 : num;
      return dayjs(msTimestamp).format(format);
    }
    return value;
  }

  // 处理数字类型的时间戳
  if (typeof value === "number") {
    if (value <= 0) return "";
    // 判断是秒级还是毫秒级时间戳（秒级时间戳通常小于 1e10）
    const msTimestamp = value < 1e10 ? value * 1000 : value;
    return dayjs(msTimestamp).format(format);
  }

  return String(value);
}

// 获取数值显示值
function getNumberDisplay(field: FieldEntity, value: unknown): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "number") {
    const precision = (field.options?.precision as number) ?? 0;
    const prefix = (field.options?.prefix as string) || "";
    const suffix = (field.options?.suffix as string) || "";
    const formatted = value.toFixed(precision);
    return `${prefix}${formatted}${suffix}`;
  }
  return String(value);
}

// 计算公式字段值
function getFormulaDisplay(field: FieldEntity, record: RecordEntity): string {
  const formula = field.options?.formula as string;
  if (!formula) return "";

  try {
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
    console.error("Grouped table formula calculation error:", error);
    return "计算错误";
  }
}

// 最后选中的行ID（用于Shift多选）
const lastSelectedRowId = ref<string | null>(null);

// 行选择相关方法
function toggleRowSelection(recordId: string) {
  if (selectedRows.value.has(recordId)) {
    selectedRows.value.delete(recordId);
  } else {
    selectedRows.value.add(recordId);
  }

  emitSelectedRecords();
}

function handleRowClick(record: RecordEntity, event: MouseEvent) {
  // 如果点击的是复选框或放大按钮，不处理
  if ((event.target as HTMLElement).closest(".row-checkbox, .expand-btn")) {
    return;
  }

  // 支持 Shift 范围选择
  if (event.shiftKey && lastSelectedRowId.value) {
    const recordIds = getAllRecordIds();
    const lastIndex = recordIds.indexOf(lastSelectedRowId.value);
    const currentIndex = recordIds.indexOf(record.id);

    if (lastIndex !== -1 && currentIndex !== -1) {
      const start = Math.min(lastIndex, currentIndex);
      const end = Math.max(lastIndex, currentIndex);

      for (let i = start; i <= end; i++) {
        selectedRows.value.add(recordIds[i]);
      }
      emitSelectedRecords();
    }
  }
  // 支持 Ctrl/Cmd 多选
  else if (event.ctrlKey || event.metaKey) {
    toggleRowSelection(record.id);
    lastSelectedRowId.value = record.id;
  } else {
    // 单选模式：清除其他选择，只选当前行
    selectedRows.value.clear();
    selectedRows.value.add(record.id);
    lastSelectedRowId.value = record.id;
    emitSelectedRecords();
    emit("rowClick", record);
  }
}

// 获取所有记录ID（用于Shift多选）
function getAllRecordIds(): string[] {
  const ids: string[] = [];
  flattenedData.value.forEach((item) => {
    if (item.type === "record" && item.record) {
      ids.push(item.record.id);
    }
  });
  return ids;
}

// 键盘事件处理
function handleKeyDown(event: KeyboardEvent) {
  // Ctrl+A 全选
  if ((event.ctrlKey || event.metaKey) && event.key === "a") {
    event.preventDefault();
    toggleSelectAll();
    return;
  }

  // 上下箭头导航
  if (event.key === "ArrowUp" || event.key === "ArrowDown") {
    event.preventDefault();
    navigateRows(event.key === "ArrowUp" ? -1 : 1);
    return;
  }

  // Delete/Backspace 删除
  if (event.key === "Delete" || event.key === "Backspace") {
    if (selectedRows.value.size > 0) {
      event.preventDefault();
      emit(
        "records-select",
        Array.from(selectedRows.value)
          .map((id) => props.records.find((r) => r.id === id)!)
          .filter(Boolean),
      );
    }
    return;
  }

  // Enter 编辑
  if (event.key === "Enter") {
    if (selectedRows.value.size === 1) {
      const selectedId = Array.from(selectedRows.value)[0];
      const record = props.records.find((r) => r.id === selectedId);
      if (record) {
        emit("cellClick", record, props.fields[0]);
      }
    }
    return;
  }

  // Escape 取消选择
  if (event.key === "Escape") {
    selectedRows.value.clear();
    emitSelectedRecords();
    return;
  }
}

// 行导航
function navigateRows(direction: -1 | 1) {
  const recordIds = getAllRecordIds();
  if (recordIds.length === 0) return;

  let currentIndex = -1;
  if (lastSelectedRowId.value) {
    currentIndex = recordIds.indexOf(lastSelectedRowId.value);
  }

  let newIndex = currentIndex + direction;
  if (newIndex < 0) newIndex = 0;
  if (newIndex >= recordIds.length) newIndex = recordIds.length - 1;

  const newRecordId = recordIds[newIndex];
  if (!event?.shiftKey) {
    selectedRows.value.clear();
  }
  selectedRows.value.add(newRecordId);
  lastSelectedRowId.value = newRecordId;
  emitSelectedRecords();
}

function toggleSelectAll() {
  const recordItems = flattenedData.value.filter(
    (item) => item.type === "record",
  );
  if (isAllSelected.value) {
    selectedRows.value.clear();
  } else {
    recordItems.forEach((item) => {
      if (item.record) {
        selectedRows.value.add(item.record.id);
      }
    });
  }
  emitSelectedRecords();
}

function emitSelectedRecords() {
  const selectedRecords: RecordEntity[] = [];
  flattenedData.value.forEach((item) => {
    if (
      item.type === "record" &&
      item.record &&
      selectedRows.value.has(item.record.id)
    ) {
      selectedRecords.push(item.record);
    }
  });
  emit("records-select", selectedRecords);
}

function handleCellClick(record: RecordEntity, field: FieldEntity) {
  emit("cellClick", record, field);
}

// 处理放大按钮点击
function handleExpandRecord(record: RecordEntity) {
  emit("expand-record", record);
}

function handleAddRecord(item: FlattenedItem) {
  const groupField = item.groupField;
  const groupValue = item.groupValue;

  // 构建所有层级的分组信息
  const groupLevels: GroupLevelInfo[] = [];

  if (item.groupKey) {
    // groupKey 格式: "level1Key-level2Key-level3Key"
    const keyParts = item.groupKey.split("-");

    // 根据层级数量，从 groupNodes 树中查找每个层级的信息
    let currentNodes = groupNodes.value;
    let currentKeyPath = "";

    for (let i = 0; i < keyParts.length && i < groupFields.value.length; i++) {
      const keyPart = keyParts[i];
      const field = groupFields.value[i];

      if (!field) continue;

      // 在当前层级查找匹配的分组节点
      const node = currentNodes.find((n) => n.key === keyPart);
      if (node) {
        currentKeyPath = currentKeyPath
          ? `${currentKeyPath}-${keyPart}`
          : keyPart;

        groupLevels.push({
          fieldId: field.id,
          fieldName: field.name,
          value: node.value,
          valueId: getGroupIdFromValue(node.value, field),
        });

        // 进入下一层级
        currentNodes = node.children || [];
      }
    }
  }

  emit("addRecord", {
    groupFieldId: groupField?.id,
    groupId: groupField
      ? getGroupIdFromValue(groupValue, groupField)
      : undefined,
    groupName: groupValue,
    groupLevels: groupLevels.length > 0 ? groupLevels : undefined,
  });
}

function getGroupIdFromValue(
  value: string | undefined,
  field: FieldEntity,
): string | undefined {
  if (!value || !field.options?.choices) return value;
  const options = field.options.choices as Array<{ id: string; name: string }>;
  const option = options.find((opt) => opt.name === value);
  return option?.id || value;
}

function getGroupHeaderClass(level: number): string {
  const classes = ["group-header"];
  if (level === 0) classes.push("group-level-1");
  else if (level === 1) classes.push("group-level-2");
  else classes.push("group-level-3");
  return classes.join(" ");
}

function getIndentStyle(level: number) {
  // 第一层: 8px, 第二层: 32px, 第三层: 72px (增加第三层间距)
  const indentMap: Record<number, number> = {
    0: 8,
    1: 20,
    2: 32,
  };
  return {
    paddingLeft: `${indentMap[level] ?? level * 24 + 8}px`,
  };
}

function isRowSelected(recordId: string): boolean {
  return selectedRows.value.has(recordId);
}

// 获取评分显示
function getRatingDisplay(field: FieldEntity, value: unknown): string {
  const maxRating = (field.options?.maxRating as number) || 5;
  const rating = Number(value) || 0;
  return "★".repeat(rating) + "☆".repeat(maxRating - rating);
}

// ========== 关联字段相关 ==========

// 存储每条记录的关联字段数据
const recordLinkData = ref<Map<string, Map<string, LinkedRecord[]>>>(new Map());
const recordLinkLoading = ref<Map<string, Set<string>>>(new Map());

// 获取关联字段配置
function getLinkFieldConfig(field: FieldEntity) {
  if (field.type !== FieldType.LINK) return null;
  const config = field.config as Record<string, unknown>;
  return {
    targetTableId: config?.linkedTableId as string,
    relationshipType:
      (config?.relationshipType as "one_to_one" | "one_to_many") ||
      "one_to_many",
    displayFieldId: config?.displayFieldId as string,
  };
}

// 加载关联记录详情
async function loadLinkedRecords(record: RecordEntity, field: FieldEntity) {
  if (field.type !== FieldType.LINK) return;

  const recordId = record.id;
  const fieldId = field.id;
  const linkedIds = record.values[fieldId] as string[] | null;

  if (!linkedIds || linkedIds.length === 0) {
    // 清空关联数据
    if (!recordLinkData.value.has(recordId)) {
      recordLinkData.value.set(recordId, new Map());
    }
    recordLinkData.value.get(recordId)!.set(fieldId, []);
    return;
  }

  // 标记加载中
  if (!recordLinkLoading.value.has(recordId)) {
    recordLinkLoading.value.set(recordId, new Set());
  }
  recordLinkLoading.value.get(recordId)!.add(fieldId);

  try {
    // 获取记录的关联数据
    const links = await linkApiService.getRecordLinks(recordId);

    // 找到当前字段的关联数据
    const fieldLinks = links.outbound.find((l) => l.field_id === fieldId);
    let linkedRecords: LinkedRecord[] = [];

    if (fieldLinks && fieldLinks.linked_records) {
      linkedRecords = fieldLinks.linked_records.map((r) => ({
        record_id: r.record_id,
        display_value: r.display_value,
      }));
    } else {
      // 如果没有从API获取到，使用ID列表创建简单的记录
      linkedRecords = linkedIds.map((id) => ({
        record_id: id,
        display_value: id,
      }));
    }

    // 存储关联数据
    if (!recordLinkData.value.has(recordId)) {
      recordLinkData.value.set(recordId, new Map());
    }
    recordLinkData.value.get(recordId)!.set(fieldId, linkedRecords);
  } catch (error) {
    console.error("[GroupedTableView] 加载关联记录失败:", error);
    // 失败时使用ID列表
    if (!recordLinkData.value.has(recordId)) {
      recordLinkData.value.set(recordId, new Map());
    }
    recordLinkData.value.get(recordId)!.set(
      fieldId,
      linkedIds.map((id) => ({
        record_id: id,
        display_value: id,
      }))
    );
  } finally {
    // 移除加载标记
    recordLinkLoading.value.get(recordId)?.delete(fieldId);
  }
}

// 获取关联记录数据
function getLinkedRecords(record: RecordEntity, field: FieldEntity): LinkedRecord[] {
  if (field.type !== FieldType.LINK) return [];
  return recordLinkData.value.get(record.id)?.get(field.id) || [];
}

// 检查关联记录是否正在加载
function isLinkLoading(record: RecordEntity, field: FieldEntity): boolean {
  if (field.type !== FieldType.LINK) return false;
  return recordLinkLoading.value.get(record.id)?.has(field.id) || false;
}

// 处理关联字段点击编辑
function handleLinkFieldClick(record: RecordEntity, field: FieldEntity) {
  if (props.readonly) return;
  // 触发单元格点击事件，父组件会处理编辑
  emit("cellClick", record, field);
}

// 处理关联字段值更新
function handleLinkFieldChange(
  record: RecordEntity,
  field: FieldEntity,
  value: string[],
  records: LinkedRecord[]
) {
  // 更新本地关联数据
  if (!recordLinkData.value.has(record.id)) {
    recordLinkData.value.set(record.id, new Map());
  }
  recordLinkData.value.get(record.id)!.set(field.id, records);

  // 触发更新事件
  emit("cellClick", record, field);
}
</script>

<template>
  <div class="grouped-table-view" tabindex="-1" @keydown="handleKeyDown">
    <!-- 分组工具栏 -->
    <div v-if="isGrouped" class="group-toolbar">
      <div class="toolbar-left">
        <span class="group-summary"> 共 {{ groupNodes.length }} 个分组 </span>
      </div>
      <div class="toolbar-right">
        <el-button
          size="small"
          text
          class="expand-toggle-btn"
          @click="toggleExpandAll">
          <el-icon v-if="isAllExpanded"><ArrowRight /></el-icon>
          <el-icon v-else><ArrowDown /></el-icon>
          <span class="btn-text">{{
            isAllExpanded ? "全部折叠" : "全部展开"
          }}</span>
        </el-button>
      </div>
    </div>

    <div class="table-container">
      <table class="data-table">
        <thead>
          <tr class="header-row">
            <!-- 全选/序号列 -->
            <th class="column-header index-column">
              <input
                type="checkbox"
                :checked="isAllSelected"
                :indeterminate="selectedRows.size > 0 && !isAllSelected"
                @change="
                  (e) => {
                    if ((e.target as HTMLInputElement).checked) {
                      toggleSelectAll();
                    } else {
                      selectedRows.clear();
                      emitSelectedRecords();
                    }
                  }
                " />
            </th>
            <th class="column-header expand-column"></th>
            <th
              v-for="field in visibleFields"
              :key="field.id"
              class="column-header resizable"
              :class="{ 'is-frozen': isFieldFrozen(field.id) }"
              :style="{
                width: getColumnWidth(field.id),
                left: isFieldFrozen(field.id)
                  ? `${getFrozenFieldLeft(field.id)}px`
                  : 'auto',
              }"
              @contextmenu="(e) => handleHeaderContextMenu(field, e)">
              <div class="header-content">
                <el-icon class="header-icon">
                  <component :is="getFieldTypeIconComponent(field.type)" />
                </el-icon>
                {{ field.name }}
              </div>
              <!-- 冻结标识 -->
              <div v-if="isFieldFrozen(field.id)" class="frozen-indicator">
                <el-icon><Lock /></el-icon>
                <span>冻结</span>
              </div>
              <!-- 列宽调整手柄 -->
              <div
                class="resize-handle"
                @mousedown.stop="startResize($event, field.id)" />
            </th>
          </tr>
        </thead>
        <tbody>
          <template
            v-for="(item, index) in flattenedData"
            :key="`${item.type}-${index}-${refreshCounter}`">
            <!-- 分组行 -->
            <tr
              v-if="item.type === 'group'"
              :class="getGroupHeaderClass(item.level)"
              @click="toggleGroup(item.groupKey)">
              <td class="index-cell"></td>
              <td class="expand-cell" :style="getIndentStyle(item.level)">
                <el-icon
                  class="expand-icon"
                  :class="{ expanded: isGroupExpanded(item.groupKey) }">
                  <ArrowRight />
                </el-icon>
                <div class="group-info">
                  <!-- 单选字段分组：使用预定义样式展示 -->
                  <template
                    v-if="item.groupField?.type === FieldType.SINGLE_SELECT">
                    <span
                      v-if="
                        getSingleSelectDisplay(
                          item.groupField,
                          item.node!.value,
                        )
                      "
                      class="group-name select-tag"
                      :style="{
                        backgroundColor: getSingleSelectDisplay(
                          item.groupField,
                          item.node!.value,
                        )?.color,
                      }">
                      {{
                        getSingleSelectDisplay(
                          item.groupField,
                          item.node!.value,
                        )?.name
                      }}
                    </span>
                    <span v-else class="group-name">{{
                      item.node!.value
                    }}</span>
                  </template>
                  <!-- 其他字段分组：保持原有显示方式 -->
                  <template v-else>
                    <span class="group-name">{{ item.node!.value }}</span>
                  </template>
                  <span class="group-count">总数：{{ item.node!.count }}</span>
                </div>
              </td>
              <td :colspan="visibleFields.length" class="group-info-cell"></td>
            </tr>

            <!-- 数据行 -->
            <tr
              v-else-if="item.type === 'record'"
              class="data-row"
              :class="{
                'is-selected': isRowSelected(item.record!.id),
                'is-hovered': hoveredRowId === item.record!.id,
                'is-even': isEvenRow(item.record!.id),
              }"
              :style="{ height: rowHeightMap[rowHeight] }"
              @click="handleRowClick(item.record!, $event)"
              @contextmenu="(e) => handleRowContextMenu(item.record!, e)"
              @mouseenter="hoveredRowId = item.record!.id"
              @mouseleave="hoveredRowId = null">
              <!-- 序号/复选框列 -->
              <td class="index-cell" @click.stop style="padding-top: 8px">
                <div class="index-wrapper">
                  <!-- 自定义勾选按钮 -->
                  <div
                    class="custom-checkbox"
                    :class="{ 'is-checked': isRowSelected(item.record!.id) }"
                    @click.stop="toggleRowSelection(item.record!.id)">
                    <div class="checkbox-inner">
                      <el-icon v-if="isRowSelected(item.record!.id)"
                        ><Check
                      /></el-icon>
                    </div>
                  </div>
                  <!-- 放大按钮 -->
                  <button
                    class="expand-btn"
                    :class="{ 'is-visible': isRowSelected(item.record!.id) }"
                    @click.stop="handleExpandRecord(item.record!)"
                    title="查看/编辑记录">
                    <el-icon><ZoomIn /></el-icon>
                  </button>
                  <span class="row-number">{{ item.rowIndex }}</span>
                </div>
              </td>
              <td class="expand-cell empty"></td>
              <td
                v-for="field in visibleFields"
                :key="field.id"
                class="data-cell"
                :class="{ 'is-frozen': isFieldFrozen(field.id) }"
                :style="{
                  width: getColumnWidth(field.id),
                  left: isFieldFrozen(field.id)
                    ? `${getFrozenFieldLeft(field.id)}px`
                    : 'auto',
                }"
                @click.stop="handleCellClick(item.record!, field)">
                <!-- 单选字段 - 与标准表格视图样式一致 -->
                <template v-if="field.type === FieldType.SINGLE_SELECT">
                  <el-tooltip
                    v-if="
                      getSingleSelectDisplay(
                        field,
                        item.record!.values[field.id],
                      )
                    "
                    :content="
                      getSingleSelectDisplay(
                        field,
                        item.record!.values[field.id],
                      )?.name
                    "
                    placement="top"
                    :show-after="200">
                    <span
                      class="select-tag"
                      :style="{
                        backgroundColor: getSingleSelectDisplay(
                          field,
                          item.record!.values[field.id],
                        )?.color,
                      }">
                      {{
                        getSingleSelectDisplay(
                          field,
                          item.record!.values[field.id],
                        )?.name
                      }}
                    </span>
                  </el-tooltip>
                </template>

                <!-- 多选字段 - 与标准表格视图样式一致 -->
                <template v-else-if="field.type === FieldType.MULTI_SELECT">
                  <el-tooltip
                    :content="
                      getMultiSelectDisplay(
                        field,
                        item.record!.values[field.id],
                      )
                        .map((opt) => opt.name)
                        .join(', ')
                    "
                    placement="top"
                    :show-after="200">
                    <div class="multi-select-tags">
                      <span
                        v-for="(opt, idx) in getMultiSelectDisplay(
                          field,
                          item.record!.values[field.id],
                        )"
                        :key="idx"
                        class="select-tag"
                        :style="{
                          backgroundColor: opt.color,
                        }">
                        {{ opt.name }}
                      </span>
                    </div>
                  </el-tooltip>
                </template>

                <!-- 日期字段 -->
                <template v-else-if="field.type === FieldType.DATE || field.type === FieldType.DATE_TIME">
                  <el-tooltip
                    :content="
                      getDateDisplay(field, item.record!.values[field.id])
                    "
                    placement="top"
                    :show-after="200">
                    <span class="cell-content">
                      {{ getDateDisplay(field, item.record!.values[field.id]) }}
                    </span>
                  </el-tooltip>
                </template>

                <!-- 复选框字段 - 使用开关样式与标准表格视图一致 -->
                <template v-else-if="field.type === FieldType.CHECKBOX">
                  <el-switch
                    :model-value="Boolean(item.record!.values[field.id])"
                    disabled
                    class="cell-switch" />
                </template>

                <!-- 数值字段 -->
                <template v-else-if="field.type === FieldType.NUMBER">
                  <el-tooltip
                    :content="
                      getNumberDisplay(field, item.record!.values[field.id])
                    "
                    placement="top"
                    :show-after="200">
                    <span class="cell-content">
                      {{
                        getNumberDisplay(field, item.record!.values[field.id])
                      }}
                    </span>
                  </el-tooltip>
                </template>

                <!-- 公式字段 -->
                <template v-else-if="field.type === FieldType.FORMULA">
                  <el-tooltip
                    :content="getFormulaDisplay(field, item.record!)"
                    placement="top"
                    :show-after="200">
                    <span class="cell-content formula-cell">
                      {{ getFormulaDisplay(field, item.record!) }}
                    </span>
                  </el-tooltip>
                </template>

                <!-- 链接字段 -->
                <template v-else-if="field.type === FieldType.URL">
                  <a
                    v-if="item.record!.values[field.id]"
                    :href="String(item.record!.values[field.id])"
                    target="_blank"
                    class="url-link"
                    @click.stop>
                    {{ item.record!.values[field.id] }}
                  </a>
                  <span v-else class="cell-content">-</span>
                </template>

                <!-- 邮箱字段 -->
                <template v-else-if="field.type === FieldType.EMAIL">
                  <a
                    v-if="item.record!.values[field.id]"
                    :href="`mailto:${item.record!.values[field.id]}`"
                    class="email-link"
                    @click.stop>
                    {{ item.record!.values[field.id] }}
                  </a>
                  <span v-else class="cell-content">-</span>
                </template>

                <!-- 附件字段 -->
                <template v-else-if="field.type === FieldType.ATTACHMENT">
                  <div
                    class="attachment-cell"
                    @click.stop="handleExpandRecord(item.record!)">
                    <el-icon class="attachment-icon"><Paperclip /></el-icon>
                    <span class="attachment-count">
                      {{
                        Array.isArray(item.record!.values[field.id])
                          ? item.record!.values[field.id].length
                          : 0
                      }}
                      个文件
                    </span>
                  </div>
                </template>

                <!-- 评分字段 -->
                <template v-else-if="field.type === FieldType.RATING">
                  <span class="rating-display">
                    {{ getRatingDisplay(field, item.record!.values[field.id]) }}
                  </span>
                </template>

                <!-- 进度字段 -->
                <template v-else-if="field.type === FieldType.PROGRESS">
                  <div class="progress-cell">
                    <div class="progress-bar">
                      <div
                        class="progress-fill"
                        :style="{
                          width: `${Number(item.record!.values[field.id]) || 0}%`,
                        }" />
                    </div>
                    <span class="progress-text"
                      >{{ Number(item.record!.values[field.id]) || 0 }}%</span
                    >
                  </div>
                </template>

                <!-- 成员字段 -->
                <template v-else-if="field.type === FieldType.MEMBER">
                  <MemberDisplay
                    :user-ids="item.record!.values[field.id] as string[]"
                    mode="tag"
                    :max-display="2"
                    :avatar-size="20" />
                </template>

                <!-- 电话字段 -->
                <template v-else-if="field.type === FieldType.PHONE">
                  <a
                    v-if="item.record!.values[field.id]"
                    :href="`tel:${item.record!.values[field.id]}`"
                    class="phone-link"
                    @click.stop>
                    {{ item.record!.values[field.id] }}
                  </a>
                  <span v-else class="cell-content">-</span>
                </template>

                <!-- 关联字段 -->
                <template v-else-if="field.type === FieldType.LINK">
                  <LinkField
                    :value="(item.record!.values[field.id] as string[]) || []"
                    :linked-records="getLinkedRecords(item.record!, field)"
                    :target-table-id="getLinkFieldConfig(field)?.targetTableId"
                    :display-field-id="getLinkFieldConfig(field)?.displayFieldId"
                    :relationship-type="getLinkFieldConfig(field)?.relationshipType"
                    :is-editing="false"
                    @edit-start="handleLinkFieldClick(item.record!, field)" />
                </template>

                <!-- 单行文本 -->
                <template v-else-if="field.type === FieldType.SINGLE_LINE_TEXT">
                  <el-tooltip
                    :content="String(item.record!.values[field.id] ?? '')"
                    placement="top"
                    :show-after="200">
                    <span class="cell-content">
                      {{ item.record!.values[field.id] ?? "" }}
                    </span>
                  </el-tooltip>
                </template>

                <!-- 多行文本 -->
                <template v-else-if="field.type === FieldType.LONG_TEXT">
                  <el-tooltip
                    :content="String(item.record!.values[field.id] ?? '')"
                    placement="top"
                    :show-after="200">
                    <span class="cell-content">
                      {{ item.record!.values[field.id] ?? "" }}
                    </span>
                  </el-tooltip>
                </template>

                <!-- 富文本 -->
                <template v-else-if="field.type === FieldType.RICH_TEXT">
                  <el-tooltip
                    :content="truncateRichText(String(item.record!.values[field.id] ?? ''), 100)"
                    placement="top"
                    :show-after="200">
                    <span class="cell-content">
                      {{ truncateRichText(String(item.record!.values[field.id] ?? ''), 30) }}
                    </span>
                  </el-tooltip>
                </template>

                <!-- 其他字段 -->
                <template v-else>
                  <el-tooltip
                    :content="String(item.record!.values[field.id] ?? '')"
                    placement="top"
                    :show-after="200">
                    <span class="cell-content">
                      {{ item.record!.values[field.id] ?? "" }}
                    </span>
                  </el-tooltip>
                </template>
              </td>
            </tr>

            <!-- 新增按钮行 -->
            <tr
              v-else-if="item.type === 'addButton' && !readonly"
              class="add-button-row"
              :style="{ height: rowHeightMap[rowHeight] }">
              <td class="index-cell"></td>
              <td class="expand-cell empty"></td>
              <td :colspan="visibleFields.length" class="add-button-cell">
                <div
                  class="add-button-wrapper"
                  @click.stop="handleAddRecord(item)">
                  <el-icon class="add-icon"><Plus /></el-icon>
                  <span class="add-text">添加记录</span>
                </div>
              </td>
            </tr>
          </template>
        </tbody>
      </table>

      <div v-if="flattenedData.length === 0" class="empty-table">
        <el-empty description="暂无数据" />
      </div>
    </div>

    <!-- 右键菜单 -->
    <ContextMenu
      :items="contextMenuItems"
      :x="contextMenuX"
      :y="contextMenuY"
      :visible="contextMenuVisible"
      @update:visible="contextMenuVisible = $event"
      @select="handleContextMenuSelect" />
  </div>
</template>

<script lang="ts">
import {
  ArrowRight,
  ArrowDown,
  CollectionTag,
  Calendar,
  Sort,
  Document,
  Plus,
  Check,
} from "@element-plus/icons-vue";
export default {
  name: "GroupedTableView",
};
</script>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;

.grouped-table-view {
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
  background-color: $surface-color;
}

// 工具栏
.group-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: $spacing-sm $spacing-md;
  border-bottom: 1px solid $border-color;
  background-color: $surface-color;

  .toolbar-left {
    .group-summary {
      font-size: $font-size-sm;
      color: $text-secondary;
    }
  }

  .toolbar-right {
    display: flex;
    gap: $spacing-xs;
  }

  .expand-toggle-btn {
    transition: all 0.3s ease;

    &:hover {
      background-color: rgba($primary-color, 0.1);
    }

    .btn-text {
      margin-left: 4px;
    }
  }
}

// 表格容器
.table-container {
  flex: 1;
  overflow: auto;
}

// 数据表格
.data-table {
  width: 100%;
  border-collapse: collapse;
  table-layout: fixed;

  // 表头
  thead {
    position: sticky;
    top: 0;
    z-index: 20;
  }

  .header-row {
    background-color: #f5f7fa;
    height: 36px;
  }

  .column-header {
    text-align: left;
    padding: 1px 2px 0px 4px;

    border-right: 1px solid $border-color;
    font-size: $font-size-sm;
    font-weight: 600;
    color: $text-secondary;
    background-color: #f5f7fa;
    height: 36px;
    box-sizing: border-box;

    &:last-child {
      border-right: none;
    }

    .header-content {
      display: flex;
      align-items: center;
      gap: 6px;
      border-bottom: 1px solid $border-color;
      height: 100%;
    }

    .header-icon {
      font-size: 14px;
      color: $text-secondary;
    }

    // 冻结标识
    .frozen-indicator {
      position: absolute;
      right: 8px;
      top: 50%;
      transform: translateY(-50%);
      display: flex;
      align-items: center;
      gap: 4px;
      font-size: 10px;
      color: $primary-color;
      font-weight: 500;
      background-color: rgba($primary-color, 0.1);
      padding: 2px 6px;
      border-radius: 4px;

      .el-icon {
        font-size: 12px;
      }
    }

    &.index-column {
      width: 70px;
      min-width: 70px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-right: 1px solid $border-color;
      background-color: #f5f7fa;
      // 冻结序号列 - 横向固定在左侧
      position: sticky;
      left: 0;
      z-index: 30;

      input[type="checkbox"] {
        width: 16px;
        height: 16px;
        cursor: pointer;
        accent-color: $primary-color;
      }
    }

    &.expand-column {
      width: 120px;
      min-width: 120px;
      max-width: 120px;
      // 冻结展开列 - 横向固定在左侧
      position: sticky;
      left: 70px;
      z-index: -1;
      background-color: #f5f7fa;
      padding: $spacing-sm;
      box-sizing: border-box;
      overflow: hidden;
    }

    // 冻结列样式 - 数据列冻结时层级最高
    &.is-frozen {
      position: sticky;
      z-index: 25;
      background-color: #f5f7fa;
      box-shadow: 2px 0 4px rgba(0, 0, 0, 0.05);
    }

    // 列宽调整手柄
    .resize-handle {
      position: absolute;
      right: 0;
      top: 0;
      bottom: 0;
      width: 4px;
      cursor: col-resize;
      background-color: transparent;
      transition: background-color 0.2s;

      &:hover {
        background-color: $primary-color;
      }
    }
  }
}

// 序号列
.index-cell {
  width: 70px;
  min-width: 70px;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 0px 8px;
  border-right: 1px solid $border-color;
  background-color: inherit;
  // 冻结序号列 - 同时固定横向滚动
  position: sticky;
  left: 0;
  z-index: 10;

  .index-wrapper {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    height: 100%;
    width: 100%;

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
      position: absolute;
      left: 0;

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
      transition: all 0.2s ease;
      z-index: 10;
      flex-shrink: 0;
      position: absolute;
      right: 2px;

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

    .row-number {
      font-size: $font-size-xs;
      color: $gray-400;
      transition: opacity 0.2s ease;
      position: relative;
      text-align: center;
      min-width: 20px;
    }
  }
}

// 数据行悬停时显示复选框和放大按钮，隐藏序号
.data-row {
  &:hover {
    .index-wrapper {
      .custom-checkbox:not(.is-checked) {
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

  &.is-selected {
    .index-wrapper {
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
  &.is-selected:hover {
    .index-wrapper {
      .custom-checkbox.is-checked {
        background-color: darken($primary-color, 5%);
        border-color: darken($primary-color, 5%);
      }
    }
  }
}

// 展开列
.expand-cell {
  width: 650px;
  text-align: left;
  padding: $spacing-sm;
  // 冻结展开列 - 与表头展开列层级一致
  position: sticky;
  left: 70px;
  z-index: 8;
  background-color: inherit;
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  box-sizing: border-box;
  overflow: hidden;

  &.empty {
    background-color: transparent;
    display: table-cell;
    padding-left: $spacing-sm;
  }
}

.expand-icon {
  font-size: 14px;
  font-weight: bold;
  color: #003366;
  transition: transform 0.2s ease;
  cursor: pointer;

  &.expanded {
    transform: rotate(90deg);
  }
}

// 分组行样式
.group-header {
  cursor: pointer;
  transition: background-color 0.2s ease;

  &:hover {
    background-color: #e6f2ff;
  }

  // 一级分组
  &.group-level-1 {
    background-color: #f0f7ff;
    border-top: 1px solid #d9e8ff;
    border-bottom: 1px solid #d9e8ff;

    .group-info-cell {
      padding: $spacing-sm $spacing-md;
      z-index: 20;
      position: relative;
    }

    .group-name {
      font-size: $font-size-base;
      font-weight: 600;
      color: $primary-color;

      // 单选标签样式保持与表格行内一致
      &.select-tag {
        font-size: $font-size-xs;
        font-weight: normal;
        color: #fff;
        padding: 4px 10px;
        border-radius: 12px;
      }
    }

    .group-count {
      font-size: $font-size-sm;
      color: $text-secondary;
    }
  }

  // 二级分组
  &.group-level-2 {
    background-color: #f0f7ff;
    border-bottom: 1px solid #d9e8ff;

    .group-info-cell {
      padding: $spacing-sm $spacing-md;
      z-index: 20;
      position: relative;
    }

    .group-name {
      font-size: $font-size-base;
      font-weight: 600;
      color: $primary-color;

      // 单选标签样式保持与表格行内一致
      &.select-tag {
        font-size: $font-size-xs;
        font-weight: normal;
        color: #fff;
        padding: 4px 10px;
        border-radius: 12px;
      }
    }

    .group-count {
      font-size: $font-size-sm;
      color: $text-secondary;
    }
  }

  // 三级分组
  &.group-level-3 {
    background-color: #f0f7ff;
    border-bottom: 1px solid #d9e8ff;

    .expand-cell {
      padding-right: 16px;
    }

    .group-info-cell {
      padding: $spacing-sm $spacing-md;
      padding-left: 8px;
      z-index: 20;
      position: relative;
    }

    .group-name {
      font-size: $font-size-base;
      font-weight: 600;
      color: $primary-color;

      // 单选标签样式保持与表格行内一致
      &.select-tag {
        font-size: $font-size-xs;
        font-weight: normal;
        color: #fff;
        padding: 4px 10px;
        border-radius: 12px;
      }
    }

    .group-count {
      font-size: $font-size-sm;
      color: $text-secondary;
    }
  }
}

.group-info {
  display: flex;
  align-items: center;
  flex-wrap: nowrap;
  gap: $spacing-sm;
  overflow: hidden;
  white-space: nowrap;
  flex: 1;
  min-width: 0;

  .group-name {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    flex-shrink: 1;
    min-width: 0;
  }

  .group-count {
    flex-shrink: 0;
  }
}

// 数据行
.data-row {
  background-color: $surface-color;
  border-bottom: 1px solid $border-color;
  transition: background-color 0.2s ease;

  // 斑马纹样式 - 偶数行
  &.is-even {
    background-color: rgba($bg-color, 0.9);
  }

  &:hover {
    background-color: rgba($primary-color, 0.05);
  }

  &.is-selected {
    background-color: rgba($primary-color, 0.1);

    &:hover {
      background-color: rgba($primary-color, 0.15);
    }
  }

  .data-cell {
    padding: 1px 2px 1px 4px;
    font-size: $font-size-sm;
    color: $text-primary;
    border-right: 1px solid $border-color;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;

    &:last-child {
      border-right: none;
    }

    // 冻结列样式 - 与表头冻结列层级一致
    &.is-frozen {
      position: sticky;
      z-index: 15;
      background-color: inherit;
      box-shadow: 2px 0 4px rgba(0, 0, 0, 0.05);
    }

    // 单元格内容容器，用于tooltip触发
    .cell-content {
      display: block;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
      cursor: default;
    }
  }
}

// 单选/多选标签样式 - 与标准表格视图保持一致
.select-tag {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: $font-size-xs;
  color: #fff;
  white-space: nowrap;
}

.multi-select-tags {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
  overflow: hidden;
}

// 单元格开关样式
.cell-switch {
  :deep(.el-switch__core) {
    border-radius: 10px;
  }
}

// 新增按钮行
.add-button-row {
  background-color: $surface-color;
  border-bottom: 1px solid $border-color;

  &:hover {
    background-color: #f5f7fa;
  }

  .add-button-cell {
    padding: 0;
  }

  .add-button-wrapper {
    display: flex;
    align-items: center;
    justify-content: center;
    gap: $spacing-xs;
    padding: $spacing-sm $spacing-md;
    cursor: pointer;
    color: $primary-color;
    transition: all 0.2s ease;

    &:hover {
      background-color: rgba($primary-color, 0.05);
    }

    .add-icon {
      font-size: 16px;
    }

    .add-text {
      font-size: $font-size-sm;
    }
  }
}

// 链接、邮箱、电话样式
.url-link,
.email-link,
.phone-link {
  color: $primary-color;
  text-decoration: none;

  &:hover {
    text-decoration: underline;
  }
}

// 附件样式
.attachment-cell {
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  color: $primary-color;

  &:hover {
    opacity: 0.8;
  }

  .attachment-icon {
    font-size: 14px;
  }

  .attachment-count {
    font-size: $font-size-xs;
  }
}

// 评分样式
.rating-display {
  color: #fbbf24;
  letter-spacing: 1px;
}

// 进度样式
.progress-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}

.progress-bar {
  flex: 1;
  height: 6px;
  background-color: $bg-color;
  border-radius: 3px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background-color: $primary-color;
  transition: width 0.2s ease;
}

.progress-text {
  font-size: $font-size-xs;
  color: $text-secondary;
  white-space: nowrap;
}

// 成员样式
.member-cell {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
}

.member-tag {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 12px;
  font-size: $font-size-xs;
  color: $text-primary;
  background-color: $bg-color;
  border: 1px solid $border-color;
}

.member-more {
  font-size: $font-size-xs;
  color: $text-secondary;
}

// 空状态
.empty-table {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 300px;
}

// 响应式适配
@media (max-width: 768px) {
  .group-toolbar {
    flex-direction: column;
    gap: $spacing-sm;
    align-items: flex-start;
  }

  .data-table {
    .column-header {
      font-size: $font-size-xs;
      padding: $spacing-xs $spacing-sm;
    }

    .data-cell {
      font-size: $font-size-xs;
      padding: $spacing-xs $spacing-sm;
    }
  }
}
</style>
