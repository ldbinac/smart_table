<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { useTableStore } from "@/stores/tableStore";
import { useViewStore } from "@/stores/viewStore";
import { useCollaborationStore } from "@/stores/collaborationStore";
import { realtimeEventEmitter } from "@/services/realtime/eventEmitter";
import type {
  DataRecordUpdatedBroadcast,
  DataRecordCreatedBroadcast,
  DataRecordDeletedBroadcast,
} from "@/services/realtime/eventTypes";

import type { RecordEntity, FieldEntity } from "@/db/schema";
import { recordService } from "@/db/services";
import { FieldType } from "@/types/fields";
import type { CellValue } from "@/types";

// 导入 VTable
import { ListTable } from "@visactor/vtable";
// 导入 ContextMenu 组件
import ContextMenu from "@/components/common/ContextMenu.vue";
// 导入字段属性对话框
import FieldDialog from "@/components/dialogs/FieldDialog.vue";
// 导入记录详情对话框
import RecordDetailDrawer from "@/components/dialogs/RecordDetailDrawer.vue";

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

const tableStore = useTableStore();
const viewStore = useViewStore();
const collabStore = useCollaborationStore();

const tableContainerRef = ref<HTMLElement | null>(null);
let tableInstance: ListTable | null = null;

const selectedRows = ref<string[]>([]);
const columnWidths = ref<Record<string, number>>({});

// 右键菜单相关
const contextMenuVisible = ref(false);
const contextMenuX = ref(0);
const contextMenuY = ref(0);
const contextMenuColumn = ref<FieldEntity | null>(null);
const contextMenuTarget = ref<"row" | "header" | "cell">("cell");
const contextMenuRecord = ref<RecordEntity | null>(null);

// 字段属性对话框相关
const fieldDialogVisible = ref(false);
const editingFieldId = ref<string | null>(null);

// 记录详情对话框相关
const expandDialogVisible = ref(false);
const expandedRecord = ref<RecordEntity | null>(null);

// 选中单元格相关 - 用于显示悬浮图标
const selectedCell = ref<{col: number, row: number, record: any, x: number, y: number} | null>(null);
const actionIconVisible = ref(false);

// Drawer 抽屉大小（响应式）
const drawerSize = computed(() => {
  const width = window.innerWidth;
  if (width < 768) return "100%";
  if (width < 1024) return "70%";
  if (width < 1440) return "50%";
  return "600px";
});

// 初始化列宽（可以从localStorage或其他地方恢复）
const initColumnWidths = () => {
  // 这里可以从localStorage恢复列宽，暂时留空
};

// 构建右键菜单
const contextMenuItems = computed(() => {
  const items: Array<{
    id: string;
    label: string;
    icon?: string;
    disabled?: boolean;
    divider?: boolean;
    danger?: boolean;
    action?: () => void;
  }> = [];

  if (contextMenuTarget.value === "row") {
    // 行菜单
    items.push({ id: "view-detail", label: "查看详情", icon: "search", action: () => {
      if (contextMenuRecord.value) {
        handleExpandRecord(contextMenuRecord.value);
      }
    }});
    
    if (!props.readonly) {
      items.push({ id: "edit", label: "编辑", icon: "edit", action: () => handleEditRecord() });
      items.push({ id: "duplicate", label: "复制记录", icon: "copy", action: () => handleDuplicateRecord() });
      items.push({ divider: true, id: "divider1", label: "" });

      if (selectedRows.value.length > 1) {
        items.push({
          id: "delete-selected",
          label: `删除选中的 ${selectedRows.value.length} 条记录`,
          icon: "delete",
          danger: true,
          action: () => handleDeleteSelectedRecords(),
        });
      } else {
        items.push({
          id: "delete",
          label: "删除记录",
          icon: "delete",
          danger: true,
          action: () => handleDeleteRecord(),
        });
      }
    }
  } else if (contextMenuTarget.value === "header" && contextMenuColumn.value) {
    // 表头菜单
    const field = contextMenuColumn.value;
    const isFrozen = currentView.value?.frozenFields.includes(field.id) || false;
    const currentSort = currentSorts.value.find(s => s.fieldId === field.id);

    // 排序相关
    items.push({
      id: 'sort-asc',
      label: '升序排列',
      icon: 'sort',
      action: () => handleSort('asc'),
    });

    items.push({
      id: 'sort-desc',
      label: '降序排列',
      icon: 'sort',
      action: () => handleSort('desc'),
    });

    if (currentSort) {
      items.push({
        id: 'sort-clear',
        label: '取消排序',
        action: () => handleSort(null),
      });
    }

    items.push({ id: 'divider-1', divider: true, label: '' });

    // 冻结相关
    items.push({
      id: isFrozen ? 'unfreeze' : 'freeze',
      label: isFrozen ? '取消冻结' : '冻结列',
      icon: 'freeze',
      action: () => handleFreeze(!isFrozen),
    });

    items.push({
      id: 'hide',
      label: '隐藏该列',
      icon: 'hide',
      action: () => handleHideColumn(),
    });

    items.push({ id: 'divider-2', divider: true, label: '' });

    // 字段属性
    items.push({
      id: 'field-settings',
      label: '字段属性',
      icon: 'settings',
      action: () => handleFieldSettings(),
    });
  }

  return items;
});

// 处理排序
const handleSort = async (direction: 'asc' | 'desc' | null) => {
  if (!currentView.value || !contextMenuColumn.value) return;

  const field = contextMenuColumn.value;
  let newSorts: any[] = [];
  
  if (direction) {
    newSorts = [{ fieldId: field.id, direction }];
    ElMessage.success(`已按 ${field.name} ${direction === 'asc' ? '升序' : '降序'}排列`);
  } else {
    ElMessage.success(`已取消 ${field.name} 的排序`);
  }

  await viewStore.updateSorts(currentView.value.id, newSorts);
  contextMenuVisible.value = false;
};

// 处理冻结/取消冻结
const handleFreeze = async (freeze: boolean) => {
  if (!currentView.value || !contextMenuColumn.value) return;

  const field = contextMenuColumn.value;
  const currentFrozen = currentView.value.frozenFields;

  // 找到该列在可见字段数组中的索引
  const fieldIndex = visibleFields.value.findIndex(f => f.id === field.id);
  if (fieldIndex === -1) return;

  let newFrozen: string[];
  if (freeze) {
    // 冻结：冻结该列及其左侧所有列
    newFrozen = visibleFields.value
      .slice(0, fieldIndex + 1)
      .map(f => f.id);
    ElMessage.success(`已冻结 ${field.name} 及其左侧列`);
  } else {
    // 取消冻结：取消该列及其右侧所有列的冻结
    newFrozen = currentFrozen.filter(frozenId => {
      const frozenIndex = visibleFields.value.findIndex(f => f.id === frozenId);
      return frozenIndex !== -1 && frozenIndex < fieldIndex;
    });
    ElMessage.success(`已取消冻结 ${field.name} 及其右侧列`);
  }

  await viewStore.updateFrozenFields(currentView.value.id, newFrozen);
  contextMenuVisible.value = false;
};

// 处理隐藏列
const handleHideColumn = async () => {
  if (!currentView.value || !contextMenuColumn.value) return;

  const field = contextMenuColumn.value;
  const currentHidden = currentView.value.hiddenFields;
  const newHidden = [...currentHidden, field.id];

  await viewStore.updateHiddenFields(currentView.value.id, newHidden);
  ElMessage.success(`已隐藏 ${field.name}`);
  contextMenuVisible.value = false;
};

// 处理字段属性
const handleFieldSettings = () => {
  if (!contextMenuColumn.value) return;
  editingFieldId.value = contextMenuColumn.value.id;
  fieldDialogVisible.value = true;
  contextMenuVisible.value = false;
};

// 处理放大按钮点击 - 打开记录详情
const handleExpandRecord = (record: RecordEntity) => {
  expandedRecord.value = record;
  expandDialogVisible.value = true;
};

// 处理编辑记录
const handleEditRecord = () => {
  if (!contextMenuRecord.value) return;
  handleExpandRecord(contextMenuRecord.value);
  contextMenuVisible.value = false;
};

// 处理复制记录
const handleDuplicateRecord = async () => {
  if (!contextMenuRecord.value) return;
  try {
    const newRecord = await recordService.createRecord({
      tableId: contextMenuRecord.value.tableId,
      values: { ...contextMenuRecord.value.values },
    });
    if (newRecord && tableStore.currentTable) {
      await tableStore.loadTables(tableStore.currentTable.baseId);
      ElMessage.success("复制记录成功");
    }
  } catch (error) {
    console.error("复制记录失败:", error);
    ElMessage.error("复制记录失败");
  }
  contextMenuVisible.value = false;
};

// 处理删除记录
const handleDeleteRecord = async () => {
  if (!contextMenuRecord.value) return;
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
  contextMenuVisible.value = false;
};

// 处理删除选中的记录
const handleDeleteSelectedRecords = async () => {
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
  contextMenuVisible.value = false;
};

// 处理记录保存
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

const records = computed(() => props.records || tableStore.records);

// 排序后的记录
const sortedRecords = computed(() => {
  const sorts = currentSorts.value;
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
      } else if (typeof aVal === 'number' && typeof bVal === 'number') {
        comparison = aVal - bVal;
      } else {
        comparison = String(aVal).localeCompare(String(bVal));
      }

      if (comparison !== 0) {
        return sort.direction === 'desc' ? -comparison : comparison;
      }
    }
    return 0;
  });
});
const fields = computed(() => tableStore.fields);
const currentView = computed(() => viewStore.currentView);

// 计算可见字段
const visibleFields = computed(() => {
  let result = fields.value.filter(
    (field) => (field as any).isVisible !== false,
  );
  if (currentView.value) {
    result = result.filter(
      (field) => !currentView.value!.hiddenFields.includes(field.id),
    );
  }
  return result;
});

// 计算冻结字段
const frozenFields = computed(() => {
  if (!currentView.value) return [];
  return fields.value.filter((field) =>
    currentView.value!.frozenFields.includes(field.id),
  );
});

// 获取当前排序配置
const currentSorts = computed(() => viewStore.currentSorts);

// 保持原始列顺序不变
const orderedVisibleFields = computed(() => visibleFields.value);

// 构建 VTable 配置
const buildTableConfig = (): any => {
  const columns = orderedVisibleFields.value.map((field) => {
    const sortInfo = currentSorts.value.find(s => s.fieldId === field.id);
    
    return {
      field: field.id,
      title: field.name,
      width: columnWidths.value[field.id] || 150,
      minWidth: 60,
      sort: true,
      sortState: sortInfo ? (sortInfo.direction === 'asc' ? 'asc' : 'desc') : 'normal',
      customRender: (args: any) => {
        if (!args || !args.record) return "";
        const value = args.record[field.id];
        if (value === null || value === undefined) return "";

        let displayValue = "";
        switch (field.type) {
          case FieldType.CHECKBOX:
            displayValue = value ? "✓" : "";
            break;
          case FieldType.DATE:
          case FieldType.DATE_TIME:
            if (typeof value === "number") {
              displayValue = new Date(value).toLocaleString();
            } else {
              displayValue = String(value);
            }
            break;
          case FieldType.SINGLE_SELECT:
            const options = (field.options?.choices || field.options?.options || []) as Array<{id: string, name: string}>;
            const selectedOption = options.find(opt => opt.id === value || opt.name === value);
            displayValue = selectedOption?.name || String(value);
            break;
          case FieldType.MULTI_SELECT:
            if (Array.isArray(value)) {
              const multiOptions = (field.options?.choices || field.options?.options || []) as Array<{id: string, name: string}>;
              displayValue = value.map(v => {
                const opt = multiOptions.find(o => o.id === v || o.name === v);
                return opt?.name || String(v);
              }).join(", ");
            }
            break;
          case FieldType.RATING:
            const maxRating = Number(field.options?.maxRating) || 5;
            const rating = Math.max(0, Math.min(Number(value) || 0, maxRating));
            displayValue = "★".repeat(rating) + "☆".repeat(maxRating - rating);
            break;
          case FieldType.PROGRESS:
            displayValue = `${Number(value) || 0}%`;
            break;
          case FieldType.MEMBER:
            if (Array.isArray(value)) {
              displayValue = value.length > 0 ? `${value.length} 成员` : "";
            }
            break;
          case FieldType.ATTACHMENT:
            if (Array.isArray(value)) {
              displayValue = value.length > 0 ? `${value.length} 个文件` : "";
            }
            break;
          case FieldType.LINK:
            if (Array.isArray(value)) {
              displayValue = value.length > 0 ? `关联 ${value.length} 条` : "";
            }
            break;
          case FieldType.FORMULA:
          case FieldType.AUTO_NUMBER:
          case FieldType.CREATED_BY:
          case FieldType.CREATED_TIME:
          case FieldType.UPDATED_BY:
          case FieldType.UPDATED_TIME:
            displayValue = String(value);
            break;
          default:
            displayValue = String(value);
        }

        return displayValue;
      },
    };
  });

  // 转换 records 为 VTable 需要的格式 - 保留原始记录引用
  const tableRecords = sortedRecords.value.map((record) => {
    const row: any = {
      _recordId: record?.id || '',
      _originalRecord: record,
    };
    orderedVisibleFields.value.forEach(field => {
      if (field?.id && record?.values) {
        row[field.id] = record.values[field.id];
      }
    });
    return row;
  });

  // 计算冻结列数
  let frozenColCount = 1;
  if (frozenFields.value.length > 0) {
    const frozenFieldIds = new Set(frozenFields.value.map(f => f.id));
    let rightmostFrozenIndex = -1;
    visibleFields.value.forEach((field, index) => {
      if (frozenFieldIds.has(field.id)) {
        rightmostFrozenIndex = Math.max(rightmostFrozenIndex, index);
      }
    });
    if (rightmostFrozenIndex >= 0) {
      frozenColCount = 1 + rightmostFrozenIndex + 1;
    }
  }

  const allowFrozenColCount = visibleFields.value.length + 1;

  return {
    columns,
    records: tableRecords,
    frozenColCount,
    showFrozenIcon: true,
    allowFrozenColCount,
    widthMode: 'standard',
    heightMode: 'standard',
    autoFillWidth: false,
    autoFillHeight: false,
    rowSeriesNumber: {
      title: '#',
      width: 'auto',
      cellType: 'checkbox',
      headerType: 'checkbox'
    },
    allowCopy: true,
    select: {
      mode: 'multiple',
      enable: true,
      highlightMode: 'row',
    },
    theme: {
      table: {
        borderLineWidth: 1,
        borderColor: '#e5e7eb',
        headerStyle: {
          bgColor: '#f9fafb',
          color: '#374151',
          fontSize: 13,
          fontWeight: 'bold',
        },
        bodyStyle: {
          bgColor: '#ffffff',
          color: '#374151',
          fontSize: 13,
        },
      },
      selectionStyle: {
        inlineRowBgColor: 'rgba(64, 158, 255, 0.1)',
      },
    },
  };
};

// 处理悬浮操作图标点击 - 打开记录详情
const handleActionIconClick = () => {
  if (selectedCell.value && selectedCell.value.record._originalRecord) {
    console.log('================================================');
    console.log('点击操作图标，打开记录详情:', selectedCell.value.record._originalRecord);
    console.log('================================================');
    handleExpandRecord(selectedCell.value.record._originalRecord);
  }
  actionIconVisible.value = false;
  selectedCell.value = null;
};

// 初始化表格
const initTable = () => {
  if (!tableContainerRef.value) return;

  const config = buildTableConfig();
  tableInstance = new ListTable(tableContainerRef.value, config);

  bindTableEvents();
};

// 绑定表格事件
const bindTableEvents = () => {
  if (!tableInstance) return;

  const tableInstanceAny = tableInstance as any;

  // 选择单元格/行
  tableInstanceAny.on('selected', (args: any) => {
    if (args.cells && args.cells.length > 0) {
      const selectedRecordIds: string[] = [];
      args.cells.forEach((cell: any) => {
        if (cell.record && cell.record._recordId) {
          selectedRecordIds.push(cell.record._recordId);
        }
      });
      
      const newIds = Array.from(new Set(selectedRecordIds));
      const oldIds = selectedRows.value;
      const changed = newIds.length !== oldIds.length || newIds.some(id => !oldIds.includes(id));
      
      if (changed) {
        selectedRows.value = newIds;
      }
      
      if (newIds.length > 0) {
        const firstSelectedRecord = sortedRecords.value.find(r => r.id === newIds[0]);
        emit('record-select', firstSelectedRecord || null);
      } else {
        emit('record-select', null);
      }
      
      const selectedRecords = sortedRecords.value.filter(r => newIds.includes(r.id));
      emit('records-select', selectedRecords);
    }
  });

  // 列宽调整
  tableInstanceAny.on('columnResize', (args: any) => {
    const colIndex = args.col;
    if (colIndex > 0) {
      const field = visibleFields.value[colIndex - 1];
      if (field) {
        columnWidths.value[field.id] = Math.max(60, args.width);
      }
    }
  });

  // 排序
  tableInstanceAny.on('sortClick', async (args: any) => {
    if (!currentView.value || !args.col) return;
    
    const colIndex = args.col;
    if (colIndex <= 0) return;
    
    const field = visibleFields.value[colIndex - 1];
    if (!field) return;
    
    const currentSort = currentSorts.value.find(s => s.fieldId === field.id);
    let newDirection: 'asc' | 'desc' | null = 'asc';
    if (currentSort) {
      if (currentSort.direction === 'asc') {
        newDirection = 'desc';
      } else if (currentSort.direction === 'desc') {
        newDirection = null;
      }
    }
    
    let newSorts: any[] = [];
    if (newDirection) {
      newSorts = [{ fieldId: field.id, direction: newDirection }];
      ElMessage.success(`已按 ${field.name} ${newDirection === 'asc' ? '升序' : '降序'}排列`);
    } else {
      ElMessage.success(`已取消 ${field.name} 的排序`);
    }
    
    await viewStore.updateSorts(currentView.value.id, newSorts);
  });

  // 单元格点击 - 使用 VTable API 获取单元格位置
  tableInstanceAny.on('click_cell', (args: any) => {
    if (args.col !== undefined && args.row !== undefined) {
      const cellRecord = args.originData || args.record;

      // 获取单元格矩形：优先用事件参数中的 rect，不可用时用 VTable API
      let cellRect = args.rect;
      if (!cellRect) {
        try {
          cellRect = tableInstanceAny.getCellRect(args.col, args.row);
        } catch (e) {
          console.warn('获取单元格位置失败:', e);
        }
      }

      if (cellRecord && cellRect) {
        const containerRect = tableContainerRef.value!.getBoundingClientRect();
        const iconX = containerRect.left + cellRect.left + cellRect.width + 8;
        const iconY = containerRect.top + cellRect.top;

        selectedCell.value = {
          col: args.col,
          row: args.row,
          record: cellRecord,
          x: Math.min(iconX, window.innerWidth - 40),
          y: Math.max(iconY, 4),
        };
        actionIconVisible.value = true;
      }

      if (cellRecord && cellRecord._originalRecord) {
        console.log('================================================');
        console.log('点击单元格，所在行完整数据:', cellRecord._originalRecord);
        console.log('================================================');
        // ElMessage.success('已输出行数据到浏览器控制台');
      }
    }
  });

  // 单元格双击
  tableInstanceAny.on('dblclick_cell', (args: any) => {
    if (args.record && args.record._originalRecord) {
      handleExpandRecord(args.record._originalRecord);
    }
  });
};

// 更新表格数据（带防重入保护和延迟队列）
let isUpdating = false;
let pendingUpdate = false;
const updateTable = () => {
  if (!tableInstance || !tableContainerRef.value) return;
  if (isUpdating) {
    pendingUpdate = true;
    return;
  }
  
  isUpdating = true;
  pendingUpdate = false;
  
  try {
    if (tableContainerRef.value) {
      tableContainerRef.value.innerHTML = '';
    }
    
    const config = buildTableConfig();
    tableInstance = new ListTable(tableContainerRef.value, config);
    bindTableEvents();
  } catch (error) {
    console.error('更新表格失败:', error);
  } finally {
    isUpdating = false;
    // 如果有排队的更新请求，在当前更新完成后立即执行一次
    if (pendingUpdate) {
      updateTable();
    }
  }
};

// 实时协作事件监听
const realtimeHandlers: Array<{ event: string; handler: (...args: unknown[]) => void }> = [];

// 容器右键事件处理
const handleContainerContextMenu = (e: MouseEvent) => {
  e.preventDefault();
  
  if (tableInstance && tableContainerRef.value) {
    try {
      const rect = tableContainerRef.value.getBoundingClientRect();
      const clickX = e.clientX - rect.left;
      const clickY = e.clientY - rect.top;
      
      const isHeader = clickY < 40;
      
      if (isHeader) {
        let currentX = 0;
        let foundField = null;
        
        if (clickX < 60) {
          return;
        }
        currentX += 60;
        
        for (let i = 0; i < orderedVisibleFields.value.length; i++) {
          const field = orderedVisibleFields.value[i];
          const fieldWidth = columnWidths.value[field.id] ?? 150;
          
          if (clickX >= currentX && clickX < currentX + fieldWidth) {
            foundField = field;
            break;
          }
          
          currentX += fieldWidth;
        }
        
        if (foundField) {
          contextMenuX.value = e.clientX;
          contextMenuY.value = e.clientY;
          contextMenuColumn.value = foundField;
          contextMenuTarget.value = "header";
          contextMenuRecord.value = null;
          contextMenuVisible.value = true;
        }
      } else {
        const rowIndex = Math.floor((clickY - 40) / 36);
        if (rowIndex >= 0 && rowIndex < sortedRecords.value.length) {
          const record = sortedRecords.value[rowIndex];
          
          if (!selectedRows.value.includes(record.id)) {
            selectedRows.value = [record.id];
            const firstSelectedRecord = sortedRecords.value.find(r => r.id === record.id);
            emit('record-select', firstSelectedRecord || null);
            const selectedRecords = sortedRecords.value.filter(r => selectedRows.value.includes(r.id));
            emit('records-select', selectedRecords);
          }
          
          contextMenuX.value = e.clientX;
          contextMenuY.value = e.clientY;
          contextMenuColumn.value = null;
          contextMenuTarget.value = "row";
          contextMenuRecord.value = record;
          contextMenuVisible.value = true;
        }
      }
    } catch (error) {
      console.error('处理右键事件失败:', error);
    }
  }
};

const setupRealtimeListeners = () => {
  if (!collabStore.isRealtimeAvailable) return;

  const onRecordUpdated = (data: DataRecordUpdatedBroadcast) => {
    if (data.table_id !== props.tableId) return;
    setTimeout(updateTable, 100);
  };

  const onRecordCreated = (data: DataRecordCreatedBroadcast) => {
    if (data.table_id !== props.tableId) return;
    setTimeout(updateTable, 100);
  };

  const onRecordDeleted = (data: DataRecordDeletedBroadcast) => {
    if (data.table_id !== props.tableId) return;
    setTimeout(updateTable, 100);
  };

  realtimeEventEmitter.on('data:record_updated', onRecordUpdated);
  realtimeEventEmitter.on('data:record_created', onRecordCreated);
  realtimeEventEmitter.on('data:record_deleted', onRecordDeleted);

  realtimeHandlers.push(
    { event: 'data:record_updated', handler: onRecordUpdated as (...args: unknown[]) => void },
    { event: 'data:record_created', handler: onRecordCreated as (...args: unknown[]) => void },
    { event: 'data:record_deleted', handler: onRecordDeleted as (...args: unknown[]) => void },
  );
};

const cleanupRealtimeListeners = () => {
  for (const { event, handler } of realtimeHandlers) {
    realtimeEventEmitter.off(event as any, handler as any);
  }
  realtimeHandlers.length = 0;
};

watch([() => tableStore.records, () => tableStore.fields], () => {
  updateTable();
}, { deep: true });

watch(() => viewStore.currentView, () => {
  updateTable();
}, { deep: true });

watch(selectedRows, () => {
  // 选中行变化不需要重建表格，VTable 内建选中高亮机制处理视觉更新
}, { deep: true });

onMounted(() => {
  initColumnWidths();
  initTable();
  setupRealtimeListeners();
});

onBeforeUnmount(() => {
  cleanupRealtimeListeners();
  if (tableInstance) {
    if (tableContainerRef.value) {
      tableContainerRef.value.innerHTML = '';
    }
    tableInstance = null;
  }
});

defineExpose({
  selectedRows,
  refresh: () => {
    updateTable();
  },
});
</script>

<template>
  <div class="vtable-view">
    <div 
      ref="tableContainerRef" 
      class="vtable-container"
      @contextmenu.prevent="handleContainerContextMenu"
    ></div>
    
    <!-- 悬浮操作图标 -->
    <div
      v-if="actionIconVisible && selectedCell"
      class="vtable-action-icon"
      :style="{
        left: selectedCell.x + 'px',
        top: selectedCell.y + 'px',
      }"
      @click.stop="handleActionIconClick"
      @mouseenter="actionIconVisible = true"
      title="查看行数据"
    >
      <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="11" cy="11" r="8"/>
        <line x1="21" y1="21" x2="16.65" y2="16.65"/>
        <line x1="11" y1="8" x2="11" y2="14"/>
        <line x1="8" y1="11" x2="14" y2="11"/>
      </svg>
    </div>
    
    <!-- 右键菜单 -->
    <ContextMenu
      :items="contextMenuItems"
      :x="contextMenuX"
      :y="contextMenuY"
      v-model:visible="contextMenuVisible"
    />
    
    <!-- 字段属性对话框 -->
    <FieldDialog
      v-model:visible="fieldDialogVisible"
      :edit-field-id="editingFieldId ?? undefined"
      :table-id="props.tableId"
      :fields="tableStore.fields"
    />
    
    <!-- 记录详情对话框 -->
    <RecordDetailDrawer
      v-model:visible="expandDialogVisible"
      :record="expandedRecord"
      :table-id="props.tableId"
      :fields="tableStore.fields"
      :size="drawerSize"
      :readonly="props.readonly"
      @save="handleRecordSave"
    />
  </div>
</template>

<style lang="scss" scoped>
.vtable-view {
  position: relative;
  width: 100%;
  height: 100%;
  overflow: hidden;
}

.vtable-container {
  width: 100%;
  height: 100%;
}

.vtable-action-icon {
  position: fixed;
  z-index: 1000;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #409eff;
  color: #fff;
  border-radius: 6px;
  cursor: pointer;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.25);
  transform: translate(-50%, -50%);
  transition: transform 0.2s ease, background-color 0.2s ease, opacity 0.2s ease;
  pointer-events: auto;
  animation: iconFadeIn 0.2s ease;

  &:hover {
    background-color: #66b1ff;
    transform: translate(-50%, -50%) scale(1.15);
  }

  &:active {
    transform: translate(-50%, -50%) scale(0.95);
  }
}

@keyframes iconFadeIn {
  from {
    opacity: 0;
    transform: translate(-50%, -50%) scale(0.5);
  }
  to {
    opacity: 1;
    transform: translate(-50%, -50%) scale(1);
  }
}
</style>