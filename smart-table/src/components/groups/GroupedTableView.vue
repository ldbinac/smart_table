<script setup lang="ts">
import { ref, computed, watch } from "vue";
import type { FieldEntity, RecordEntity } from "../../db/schema";
import type { GroupNode } from "../../utils/group";
import { FieldType } from "../../types";
import { groupRecords } from "../../utils/group";
import dayjs from "dayjs";
import { FormulaEngine } from "@/utils/formula/engine";
import { ZoomIn } from "@element-plus/icons-vue";

interface Props {
  fields: FieldEntity[];
  records: RecordEntity[];
  groupBy: string[];
  rowHeight?: "short" | "medium" | "tall";
}

const props = withDefaults(defineProps<Props>(), {
  groupBy: () => [],
  rowHeight: "medium",
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
}>();

const groupNodes = ref<GroupNode[]>([]);
const expandedKeys = ref<Set<string>>(new Set());
const selectedRows = ref<Set<string>>(new Set());
const hoveredRowId = ref<string | null>(null);

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
  }
  refreshCounter.value++;
}

function updateGroups() {
  if (props.groupBy.length === 0) {
    groupNodes.value = [];
    expandedKeys.value.clear();
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
}

watch(
  () => [props.records, props.groupBy],
  () => {
    updateGroups();
  },
  { deep: true, immediate: true },
);

function toggleGroup(groupKey: string) {
  if (expandedKeys.value.has(groupKey)) {
    expandedKeys.value.delete(groupKey);
  } else {
    expandedKeys.value.add(groupKey);
  }
  refreshCounter.value++;
}

function isGroupExpanded(groupKey: string): boolean {
  return expandedKeys.value.has(groupKey);
}

// 获取选项信息
function getSelectOption(field: FieldEntity, value: string) {
  const options = (field.options?.options || []) as Array<{
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

  const showTime = (field.options?.showTime as boolean) ?? false;
  const format = showTime ? "YYYY-MM-DD HH:mm:ss" : "YYYY-MM-DD";

  // 处理字符串格式的日期（如 "2024-01-15"）
  if (typeof value === "string") {
    // 如果是标准日期格式，直接返回
    if (/^\d{4}-\d{2}-\d{2}/.test(value)) {
      return value.substring(0, showTime ? 19 : 10);
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
  // 如果点击的是复选框，不处理
  if ((event.target as HTMLElement).closest(".row-checkbox")) {
    return;
  }

  // 支持 Ctrl/Cmd 多选
  if (event.ctrlKey || event.metaKey) {
    toggleRowSelection(record.id);
  } else {
    // 单选模式：清除其他选择，只选当前行
    selectedRows.value.clear();
    selectedRows.value.add(record.id);
    emitSelectedRecords();
    emit("rowClick", record);
  }
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
  if (!value || !field.options?.options) return value;
  const options = field.options.options as Array<{ id: string; name: string }>;
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
</script>

<template>
  <div class="grouped-table-view">
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
              <el-checkbox
                :model-value="isAllSelected"
                :indeterminate="selectedRows.size > 0 && !isAllSelected"
                @change="toggleSelectAll" />
            </th>
            <th class="column-header expand-column"></th>
            <th
              v-for="field in visibleFields"
              :key="field.id"
              class="column-header resizable"
              :style="{ width: getColumnWidth(field.id) }">
              <div class="header-content">
                <el-icon
                  v-if="
                    field.type === FieldType.SINGLE_SELECT ||
                    field.type === FieldType.MULTI_SELECT
                  "
                  class="header-icon">
                  <CollectionTag />
                </el-icon>
                <el-icon
                  v-else-if="field.type === FieldType.DATE"
                  class="header-icon">
                  <Calendar />
                </el-icon>
                <el-icon
                  v-else-if="field.type === FieldType.NUMBER"
                  class="header-icon">
                  <Sort />
                </el-icon>
                <el-icon v-else class="header-icon">
                  <Document />
                </el-icon>
                {{ field.name }}
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
              </td>
              <td :colspan="visibleFields.length" class="group-info-cell">
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
              @mouseenter="hoveredRowId = item.record!.id"
              @mouseleave="hoveredRowId = null">
              <!-- 序号/复选框列 -->
              <td class="index-cell" @click.stop>
                <div class="index-wrapper">
                  <el-checkbox
                    class="row-checkbox"
                    :model-value="isRowSelected(item.record!.id)"
                    @change="toggleRowSelection(item.record!.id)" />
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
              <td
                class="expand-cell empty"
                :style="getIndentStyle(item.level)"></td>
              <td
                v-for="field in visibleFields"
                :key="field.id"
                class="data-cell"
                :style="{ width: getColumnWidth(field.id) }"
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
                <template v-else-if="field.type === FieldType.DATE">
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
              v-else-if="item.type === 'addButton'"
              class="add-button-row"
              :style="{ height: rowHeightMap[rowHeight] }">
              <td class="index-cell"></td>
              <td
                class="expand-cell empty"
                :style="getIndentStyle(item.level)"></td>
              <td :colspan="visibleFields.length" class="add-button-cell">
                <div class="add-button-wrapper" @click="handleAddRecord(item)">
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
  .header-row {
    background-color: #f5f7fa;
    height: 20px;
  }

  .column-header {
    text-align: left;
    padding: 1px 2px 1px 4px;
    border-bottom: 1px solid $border-color;
    border-right: 1px solid $border-color;
    font-size: $font-size-sm;
    font-weight: 500;
    color: $text-secondary;
    position: sticky;
    top: 0;
    z-index: 10;
    background-color: #f5f7fa;
    height: 20px;
    box-sizing: border-box;

    &:last-child {
      border-right: none;
    }

    .header-content {
      display: flex;
      align-items: center;
      gap: 6px;
    }

    .header-icon {
      font-size: 14px;
      color: $text-secondary;
    }

    &.index-column {
      width: 50px;
      min-width: 50px;
      text-align: center;
      // 冻结序号列
      position: sticky;
      left: 0;
      z-index: 20;
      background-color: #f5f7fa;
    }

    &.expand-column {
      // 冻结展开列
      position: sticky;
      left: 50px;
      z-index: 20;
      background-color: #f5f7fa;
    }

    &.expand-column {
      width: 40px;
      min-width: 40px;
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
  width: 50px;
  min-width: 50px;
  text-align: center;
  padding: $spacing-sm;
  // 冻结序号列
  position: sticky;
  left: 0;
  z-index: 5;
  background-color: inherit;

  .index-wrapper {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;

    .row-checkbox {
      position: absolute;
      opacity: 0;
      transition: opacity 0.2s ease;
    }

    .expand-btn {
      position: absolute;
      width: 20px;
      height: 20px;
      display: flex;
      align-items: center;
      justify-content: center;
      border: none;
      border-radius: 4px;
      background-color: #999999;
      color: white;
      cursor: pointer;
      opacity: 0;
      transform: scale(0.8);
      transition: all 0.2s ease;
      z-index: 10;

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
      font-size: $font-size-sm;
      color: $text-secondary;
      transition: opacity 0.2s ease;
    }
  }
}

// 数据行悬停时显示复选框和放大按钮，隐藏序号
.data-row {
  &:hover {
    .index-wrapper {
      .row-checkbox {
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
      .row-checkbox {
        opacity: 1;
      }

      .expand-btn.is-visible {
        opacity: 1;
        transform: scale(1);
      }

      .row-number {
        opacity: 0;
      }
    }
  }
}

// 展开列
.expand-cell {
  width: 40px;
  min-width: 40px;
  text-align: center;
  padding: $spacing-sm;
  // 冻结展开列
  position: sticky;
  left: 50px;
  z-index: 5;
  background-color: inherit;

  &.empty {
    background-color: transparent;
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
      margin-left: $spacing-md;
    }
  }

  // 二级分组
  &.group-level-2 {
    background-color: #f0f7ff;
    border-bottom: 1px solid #d9e8ff;

    .group-info-cell {
      padding: $spacing-sm $spacing-md;
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
      margin-left: $spacing-md;
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
      margin-left: $spacing-md;
    }
  }
}

.group-info {
  display: flex;
  align-items: center;
}

// 数据行
.data-row {
  background-color: $surface-color;
  border-bottom: 1px solid $border-color;
  transition: background-color 0.2s ease;

  // 斑马纹样式 - 偶数行
  &.is-even {
    background-color: rgba($bg-color, 0.5);
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
