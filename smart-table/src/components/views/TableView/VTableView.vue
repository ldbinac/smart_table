<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from "vue";
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

const records = computed(() => props.records || tableStore.records);
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
    return {
      field: field.id,
      title: field.name,
      width: columnWidths.value[field.id] || 150,
      frozen: isFrozen ? (index === 0 ? 'left' : 'left') : false,
      minWidth: 60,
      // 自定义渲染
      customRender: (args: any) => {
        return formatCellValue(args.record, field);
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
    customRender: (args: any) => {
      return args.row + 1;
    },
  });

  // 转换 records 为 VTable 需要的格式
  const tableRecords = records.value.map((record, index) => {
    const row: any = {
      _index: index,
      _recordId: record.id,
    };
    visibleFields.value.forEach(field => {
      row[field.id] = record.values[field.id];
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
    if (args.type === 'cell') {
      // 获取选中的记录
      const selectedRecordIds: string[] = [];
      if (args.cells) {
        args.cells.forEach((cell: any) => {
          const record = records.value[cell.row - 1]; // 减去表头
          if (record) {
            selectedRecordIds.push(record.id);
          }
        });
      }
      
      selectedRows.value = Array.from(new Set(selectedRecordIds));
      
      if (selectedRows.value.length > 0) {
        const firstSelectedRecord = records.value.find(r => r.id === selectedRows.value[0]);
        emit('record-select', firstSelectedRecord || null);
      } else {
        emit('record-select', null);
      }
      
      const selectedRecords = records.value.filter(r => selectedRows.value.includes(r.id));
      emit('records-select', selectedRecords);
    }
  });

  // 列宽调整
  tableInstanceAny.on('columnResize', (args: any) => {
    const colIndex = args.col;
    if (colIndex > 0) { // 跳过序号列
      const field = visibleFields.value[colIndex - 1];
      if (field) {
        columnWidths.value[field.id] = args.width;
      }
    }
  });

  // 排序
  tableInstanceAny.on('sortClick', (args: any) => {
    // 排序逻辑将在后续阶段实现
    console.log('Sort clicked:', args);
  });

  // 单元格点击
  tableInstanceAny.on('cellClick', (args: any) => {
    console.log('Cell clicked:', args);
  });

  // 单元格双击
  tableInstanceAny.on('cellDblClick', (args: any) => {
    console.log('Cell double clicked:', args);
  });
};

// 更新表格数据
const updateTable = () => {
  if (!tableInstance) return;
  
  const config = buildTableConfig();
  tableInstance.setRecords(config.records);
  // 使用类型断言来设置列
  (tableInstance as any).updateColumns(config.columns);
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
