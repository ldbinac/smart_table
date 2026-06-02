<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from "vue";
import { ElMessage } from "element-plus";
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
import { FieldType } from "@/types/fields";

// 导入 VTable
import { ListTable } from "@visactor/vtable";
// 导入 ContextMenu 组件
import ContextMenu from "@/components/common/ContextMenu.vue";

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

  if (!contextMenuColumn.value) return items;

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

  items.push({ id: 'divider-1', divider: true });

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

  items.push({ id: 'divider-2', divider: true });

  // 字段属性
  items.push({
    id: 'field-settings',
    label: '字段属性',
    icon: 'settings',
    action: () => handleFieldSettings(),
  });

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

  let newFrozen: string[];
  if (freeze) {
    newFrozen = [...currentFrozen, field.id];
    ElMessage.success(`已冻结 ${field.name}`);
  } else {
    newFrozen = currentFrozen.filter(id => id !== field.id);
    ElMessage.success(`已取消冻结 ${field.name}`);
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
  // TODO: 这里可以打开字段设置对话框
  ElMessage.info('字段属性功能开发中...');
  contextMenuVisible.value = false;
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

// 格式化单元格值用于显示
const formatCellValue = (record: RecordEntity, field: FieldEntity): string => {
  const value = record.values[field.id];
  if (value === null || value === undefined) return "";

  switch (field.type) {
    case FieldType.CHECKBOX:
      return value ? "✓" : "";
    case FieldType.DATE:
    case FieldType.DATE_TIME:
      if (typeof value === "number") {
        return new Date(value).toLocaleString();
      }
      return String(value);
    case FieldType.SINGLE_SELECT:
      const options = (field.options?.choices || field.options?.options || []) as Array<{id: string, name: string}>;
      const selectedOption = options.find(opt => opt.id === value || opt.name === value);
      return selectedOption?.name || String(value);
    case FieldType.MULTI_SELECT:
      if (!Array.isArray(value)) return "";
      const multiOptions = (field.options?.choices || field.options?.options || []) as Array<{id: string, name: string}>;
      return value.map(v => {
        const opt = multiOptions.find(o => o.id === v || o.name === v);
        return opt?.name || String(v);
      }).join(", ");
    case FieldType.RATING:
      const maxRating = Number(field.options?.maxRating) || 5;
      const rating = Math.max(0, Math.min(Number(value) || 0, maxRating));
      return "★".repeat(rating) + "☆".repeat(maxRating - rating);
    case FieldType.PROGRESS:
      return `${Number(value) || 0}%`;
    case FieldType.MEMBER:
      if (Array.isArray(value)) {
        return value.length > 0 ? `${value.length} 成员` : "";
      }
      return "";
    case FieldType.ATTACHMENT:
      if (Array.isArray(value)) {
        return value.length > 0 ? `${value.length} 个文件` : "";
      }
      return "";
    case FieldType.LINK:
      if (Array.isArray(value)) {
        return value.length > 0 ? `关联 ${value.length} 条` : "";
      }
      return "";
    case FieldType.FORMULA:
    case FieldType.AUTO_NUMBER:
    case FieldType.CREATED_BY:
    case FieldType.CREATED_TIME:
    case FieldType.UPDATED_BY:
    case FieldType.UPDATED_TIME:
      return String(value);
    default:
      return String(value);
  }
};

// 构建 VTable 配置
const buildTableConfig = (): any => {
  const columns = visibleFields.value.map((field, index) => {
    const isFrozen = frozenFields.value.some(f => f.id === field.id);
    const sortInfo = currentSorts.value.find(s => s.fieldId === field.id);
    
    return {
      field: field.id,
      title: field.name,
      width: columnWidths.value[field.id] || 150,
      frozen: isFrozen ? (index === 0 ? 'left' : 'left') : false,
      minWidth: 60,
      sort: true, // 启用排序
      sortState: sortInfo ? (sortInfo.direction === 'asc' ? 'asc' : 'desc') : 'normal', // 当前排序状态
      // 自定义渲染 - 直接获取值
      customRender: (args: any) => {
        // 添加安全检查
        if (!args || !args.record) return "";
        const value = args.record[field.id];
        if (value === null || value === undefined) return "";

        switch (field.type) {
          case FieldType.CHECKBOX:
            return value ? "✓" : "";
          case FieldType.DATE:
          case FieldType.DATE_TIME:
            if (typeof value === "number") {
              return new Date(value).toLocaleString();
            }
            return String(value);
          case FieldType.SINGLE_SELECT:
            const options = (field.options?.choices || field.options?.options || []) as Array<{id: string, name: string}>;
            const selectedOption = options.find(opt => opt.id === value || opt.name === value);
            return selectedOption?.name || String(value);
          case FieldType.MULTI_SELECT:
            if (!Array.isArray(value)) return "";
            const multiOptions = (field.options?.choices || field.options?.options || []) as Array<{id: string, name: string}>;
            return value.map(v => {
              const opt = multiOptions.find(o => o.id === v || o.name === v);
              return opt?.name || String(v);
            }).join(", ");
          case FieldType.RATING:
            const maxRating = Number(field.options?.maxRating) || 5;
            const rating = Math.max(0, Math.min(Number(value) || 0, maxRating));
            return "★".repeat(rating) + "☆".repeat(maxRating - rating);
          case FieldType.PROGRESS:
            return `${Number(value) || 0}%`;
          case FieldType.MEMBER:
            if (Array.isArray(value)) {
              return value.length > 0 ? `${value.length} 成员` : "";
            }
            return "";
          case FieldType.ATTACHMENT:
            if (Array.isArray(value)) {
              return value.length > 0 ? `${value.length} 个文件` : "";
            }
            return "";
          case FieldType.LINK:
            if (Array.isArray(value)) {
              return value.length > 0 ? `关联 ${value.length} 条` : "";
            }
            return "";
          case FieldType.FORMULA:
          case FieldType.AUTO_NUMBER:
          case FieldType.CREATED_BY:
          case FieldType.CREATED_TIME:
          case FieldType.UPDATED_BY:
          case FieldType.UPDATED_TIME:
            return String(value);
          default:
            return String(value);
        }
      },
    };
  });

  // 添加序号列
  columns.unshift({
    field: '_index',
    title: '#',
    width: 60,
    frozen: 'left',
    minWidth: 50,
  });

  // 转换 records 为 VTable 需要的格式 - 保留原始记录引用
  const tableRecords = sortedRecords.value.map((record, index) => {
    const row: any = {
      _index: index + 1, // 直接设置为从1开始
      _recordId: record?.id || '',
      _originalRecord: record, // 保存原始记录引用
    };
    visibleFields.value.forEach(field => {
      if (field?.id && record?.values) {
        row[field.id] = record.values[field.id];
      }
    });
    return row;
  });

  return {
    columns,
    records: tableRecords,
    widthMode: 'standard',
    heightMode: 'standard',
    autoFillWidth: false,
    autoFillHeight: false,
    showRowNumber: false,
    allowCopy: true,
    select: {
      mode: 'multiple',
      enable: true,
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
    },
  };
};

// 初始化表格
const initTable = () => {
  if (!tableContainerRef.value) return;

  const config = buildTableConfig();
  tableInstance = new ListTable(tableContainerRef.value, config);

  // 绑定事件
  bindTableEvents();
};

// 绑定表格事件
const bindTableEvents = () => {
  if (!tableInstance) return;

  // 使用类型断言来避免 TypeScript 错误
  const tableInstanceAny = tableInstance as any;

  // 选择单元格/行
  tableInstanceAny.on('selected', (args: any) => {
    if (args.type === 'cell' && args.cells) {
      // 获取选中的记录
      const selectedRecordIds: string[] = [];
      args.cells.forEach((cell: any) => {
        if (cell.record && cell.record._recordId) {
          selectedRecordIds.push(cell.record._recordId);
        }
      });
      
      selectedRows.value = Array.from(new Set(selectedRecordIds));
      
      if (selectedRows.value.length > 0) {
        const firstSelectedRecord = sortedRecords.value.find(r => r.id === selectedRows.value[0]);
        emit('record-select', firstSelectedRecord || null);
      } else {
        emit('record-select', null);
      }
      
      const selectedRecords = sortedRecords.value.filter(r => selectedRows.value.includes(r.id));
      emit('records-select', selectedRecords);
    }
  });

  // 列宽调整
  tableInstanceAny.on('columnResize', (args: any) => {
    const colIndex = args.col;
    if (colIndex > 0) { // 跳过序号列
      const field = visibleFields.value[colIndex - 1];
      if (field) {
        columnWidths.value[field.id] = Math.max(60, args.width); // 确保最小宽度
        console.log(`列宽调整: ${field.name} = ${args.width}px`);
      }
    }
  });

  // 排序
  tableInstanceAny.on('sortClick', async (args: any) => {
    if (!currentView.value || !args.col) return;
    
    const colIndex = args.col;
    if (colIndex <= 0) return; // 跳过序号列
    
    const field = visibleFields.value[colIndex - 1];
    if (!field) return;
    
    // 确定新的排序方向
    const currentSort = currentSorts.value.find(s => s.fieldId === field.id);
    let newDirection: 'asc' | 'desc' | null = 'asc';
    if (currentSort) {
      if (currentSort.direction === 'asc') {
        newDirection = 'desc';
      } else if (currentSort.direction === 'desc') {
        newDirection = null; // 取消排序
      }
    }
    
    // 更新排序配置
    let newSorts: any[] = [];
    if (newDirection) {
      newSorts = [{ fieldId: field.id, direction: newDirection }];
      ElMessage.success(`已按 ${field.name} ${newDirection === 'asc' ? '升序' : '降序'}排列`);
    } else {
      ElMessage.success(`已取消 ${field.name} 的排序`);
    }
    
    await viewStore.updateSorts(currentView.value.id, newSorts);
  });

  // 单元格点击
  tableInstanceAny.on('cellClick', (args: any) => {
    console.log('Cell clicked:', args);
  });

  // 单元格双击
  tableInstanceAny.on('cellDblClick', (args: any) => {
    console.log('Cell double clicked:', args);
  });

  // 右键点击 - 表头
  tableInstanceAny.on('headerContextMenu', (args: any) => {
    console.log('Header context menu:', args);
    const colIndex = args.col;
    if (colIndex <= 0) return; // 跳过序号列

    const field = visibleFields.value[colIndex - 1];
    if (!field) return;

    // 获取鼠标位置
    const event = args.event || { clientX: 0, clientY: 0 };
    contextMenuX.value = event.clientX || 0;
    contextMenuY.value = event.clientY || 0;
    contextMenuColumn.value = field;
    contextMenuVisible.value = true;
  });

  // 右键点击 - 单元格
  tableInstanceAny.on('cellContextMenu', (args: any) => {
    console.log('Cell context menu:', args);
    const colIndex = args.col;
    if (colIndex <= 0) return; // 跳过序号列

    const field = visibleFields.value[colIndex - 1];
    if (!field) return;

    // 获取鼠标位置
    const event = args.event || { clientX: 0, clientY: 0 };
    contextMenuX.value = event.clientX || 0;
    contextMenuY.value = event.clientY || 0;
    contextMenuColumn.value = field;
    contextMenuVisible.value = true;
  });
};

// 更新表格数据
const updateTable = () => {
  if (!tableInstance || !tableContainerRef.value) return;
  
  try {
    // 先销毁旧表格
    if (tableContainerRef.value) {
      tableContainerRef.value.innerHTML = '';
    }
    
    // 重新初始化表格
    const config = buildTableConfig();
    tableInstance = new ListTable(tableContainerRef.value, config);
    bindTableEvents();
  } catch (error) {
    console.error('更新表格失败:', error);
  }
};

// 实时协作事件监听
const realtimeHandlers: Array<{ event: string; handler: (...args: unknown[]) => void }> = [];

const setupRealtimeListeners = () => {
  if (!collabStore.isRealtimeAvailable) return;

  const onRecordUpdated = (data: DataRecordUpdatedBroadcast) => {
    if (data.table_id !== props.tableId) return;
    // 延迟更新以确保 store 已更新
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

// 监听数据变化
watch([() => tableStore.records, () => tableStore.fields], () => {
  updateTable();
}, { deep: true });

watch(() => viewStore.currentView, () => {
  updateTable();
}, { deep: true });

onMounted(() => {
  initColumnWidths();
  initTable();
  setupRealtimeListeners();
});

onBeforeUnmount(() => {
  cleanupRealtimeListeners();
  if (tableInstance) {
    // 直接移除 DOM 元素来清理表格
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
    <div ref="tableContainerRef" class="vtable-container"></div>
    
    <!-- 右键菜单 -->
    <ContextMenu
      :items="contextMenuItems"
      :x="contextMenuX"
      :y="contextMenuY"
      v-model:visible="contextMenuVisible"
    />
  </div>
</template>

<style lang="scss" scoped>
.vtable-view {
  width: 100%;
  height: 100%;
  overflow: hidden;
}

.vtable-container {
  width: 100%;
  height: 100%;
}
</style>
