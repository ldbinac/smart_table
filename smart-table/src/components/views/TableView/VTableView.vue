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
import { formatDateTime, formatDate } from "@/utils/timezone";
import { useUserCacheStore } from "@/stores/userCacheStore";

// 导入 VTable
import { ListTable, register as registerVTable } from "@visactor/vtable";
// 导入 VRender 图形工厂函数（用于 customLayout）
import { createGroup, createText, createRect, createCircle, createPath } from '@visactor/vtable/es/vrender';
// 导入 VTable 编辑器
import { InputEditor, DateInputEditor, ListEditor } from '@visactor/vtable-editors';
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
const userCacheStore = useUserCacheStore();

const tableContainerRef = ref<HTMLElement | null>(null);
let tableInstance: ListTable | null = null;

// 注册 VTable 编辑器
const inputEditor = new InputEditor();
const dateEditor = new DateInputEditor();
registerVTable.editor('input', inputEditor);
registerVTable.editor('date', dateEditor);

const selectedRows = ref<string[]>([]);
const checkboxSelectedRows = ref<string[]>([]);
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
    // items.push({ id: "view-detail", label: "查看详情", icon: "search", action: () => {
    //   if (contextMenuRecord.value) {
    //     handleExpandRecord(contextMenuRecord.value);
    //   }
    // }});
    
    if (!props.readonly) {
      items.push({ id: "edit", label: "编辑", icon: "edit", action: () => handleEditRecord() });
      items.push({ id: "duplicate", label: "复制记录", icon: "copy", action: () => handleDuplicateRecord() });
      items.push({ divider: true, id: "divider1", label: "" });

      // 始终显示"删除当前记录"
      items.push({
        id: "delete",
        label: "删除当前记录",
        icon: "delete",
        danger: true,
        action: () => handleDeleteRecord(),
      });

      // 只要有勾选的记录，就显示"删除选中的x条记录"
      if (checkboxSelectedRows.value.length >= 1) {
        items.push({
          id: "delete-selected",
          label: `删除选中的 ${checkboxSelectedRows.value.length} 条记录`,
          icon: "delete",
          danger: true,
          action: () => handleDeleteSelectedRecords(),
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
      await tableStore.refreshRecords(tableStore.currentTable.id);
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
    if (contextMenuRecord.value && contextMenuRecord.value.id) {
      const recordId = contextMenuRecord.value.id;
      await tableStore.deleteRecord(recordId);
      selectedRows.value = [];
      checkboxSelectedRows.value = checkboxSelectedRows.value.filter(id => id !== recordId);
      emit("record-delete", [recordId]);
      ElMessage.success("记录删除成功");
    }
  } catch (error: any) {
    if (error !== "cancel") {
      console.error("删除记录失败:", error);
      ElMessage.error("删除记录失败");
    }
  }
  contextMenuVisible.value = false;
};

// 处理删除选中的记录 - 仅删除通过复选框勾选的记录
const handleDeleteSelectedRecords = async () => {
  const ids = [...checkboxSelectedRows.value];
  const count = ids.length;
  if (count === 0) return;
  try {
    await ElMessageBox.confirm(
      `确定要删除选中的 ${count} 条记录吗？此操作不可恢复。`,
      "批量删除确认",
      {
        confirmButtonText: "确定删除",
        cancelButtonText: "取消",
        type: "warning",
        confirmButtonClass: "el-button--danger",
      },
    );
    await tableStore.batchDeleteRecords(ids);
    emit("record-delete", ids);
    selectedRows.value = selectedRows.value.filter(id => !ids.includes(id));
    checkboxSelectedRows.value = [];
    ElMessage.success(`成功删除 ${count} 条记录`);
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

// 生成五角星 SVG path 数据
const getStarPath = (cx: number, cy: number, outerR: number, points: number, innerRatio: number): string => {
  const innerR = outerR * innerRatio;
  const step = Math.PI / points;
  const startAngle = -Math.PI / 2;
  const parts: string[] = [];

  for (let i = 0; i < points * 2; i++) {
    const r = i % 2 === 0 ? outerR : innerR;
    const angle = startAngle + i * step;
    const x = cx + r * Math.cos(angle);
    const y = cy + r * Math.sin(angle);
    parts.push(`${i === 0 ? 'M' : 'L'}${x.toFixed(2)},${y.toFixed(2)}`);
  }
  parts.push('Z');
  return parts.join('');
};

// 根据字段类型获取 VTable 列配置
const getCellTypeConfig = (field: any): Record<string, any> => {
  const config: Record<string, any> = {};
  
  switch (field.type) {
    case FieldType.PROGRESS:
      config.cellType = 'progressbar';
      config.min = 0;
      config.max = 100;
      config.fieldFormat = (record: any) => {
        const value = record?.[field.id];
        const num = Number(value);
        return isNaN(num) ? '0%' : `${Math.round(num)}%`;
      };
      config.style = {
        barColor: '#409eff',
        barBgColor: '#e5e7eb',
        barHeight: '30%',
        textAlign: 'center',
        textBaseline: 'middle',
        fontSize: 12,
        color: '#374151',
        fontWeight: '500',
      };
      break;
    case FieldType.CHECKBOX:
      config.cellType = 'switch';
      break;
    case FieldType.URL:
    case FieldType.EMAIL:
      config.cellType = 'link';
      break;
    case FieldType.DATE:
    case FieldType.DATE_TIME:
      config.cellType = 'text';
      config.fieldFormat = (value: any) => {
        // eslint-disable-next-line no-console
        if (typeof value === 'object' && value !== null && !(value instanceof Date)) {
          console.log('[VTable-DEBUG] DATE value type:', typeof value, value?.constructor?.name, JSON.stringify(value).slice(0,200));
        }
        // 处理 Date 对象
        if (value instanceof Date) {
          const ts = value.getTime();
          return field.type === FieldType.DATE ? formatDate(ts) : formatDateTime(ts);
        }
        // 处理对象
        if (typeof value === 'object' && value !== null) {
          // 尝试 valueOf
          if (typeof value.valueOf === 'function') {
            const v = value.valueOf();
            if (typeof v === 'number' && !isNaN(v)) {
              return field.type === FieldType.DATE ? formatDate(v) : formatDateTime(v);
            }
            if (typeof v === 'string') {
              const ts = Date.parse(v);
              if (!isNaN(ts)) {
                return field.type === FieldType.DATE ? formatDate(ts) : formatDateTime(ts);
              }
            }
          }
          // 尝试遍历对象属性找到数字值
          for (const key of Object.keys(value)) {
            const prop = (value as any)[key];
            if (typeof prop === 'number' && prop > 1000000000 && prop < 9999999999999) {
              // 看起来像时间戳
              return field.type === FieldType.DATE ? formatDate(prop) : formatDateTime(prop);
            }
            if (typeof prop === 'string' && /^\d{4}-\d{2}/.test(prop)) {
              // 看起来像 ISO 日期字符串
              const ts = Date.parse(prop);
              if (!isNaN(ts)) {
                return field.type === FieldType.DATE ? formatDate(ts) : formatDateTime(ts);
              }
            }
          }
          // 最后尝试 String(value)
          const strVal = String(value);
          if (strVal && strVal !== '[object Object]') {
            const ts = Date.parse(strVal);
            if (!isNaN(ts)) {
              return field.type === FieldType.DATE ? formatDate(ts) : formatDateTime(ts);
            }
          }
          return ""; // 确实无法解析
        }
        // 处理数字时间戳
        if (typeof value === "number") {
          return field.type === FieldType.DATE ? formatDate(value) : formatDateTime(value);
        }
        // 处理字符串
        if (typeof value === "string") {
          return field.type === FieldType.DATE ? formatDate(value) : formatDateTime(value);
        }
        return String(value || "");
      };
      config.editor = 'date';
      break;
    case FieldType.SINGLE_SELECT:
      config.cellType = 'text';
      break;
    case FieldType.MULTI_SELECT:
      config.cellType = 'text';
      break;
    case FieldType.RATING:
      config.cellType = 'text';
      break;
    case FieldType.MEMBER:
      config.cellType = 'text';
      break;
    case FieldType.ATTACHMENT:
      config.cellType = 'text';
      break;
    case FieldType.LINK:
      config.cellType = 'text';
      config.fieldFormat = (value: any) => {
        if (Array.isArray(value)) return value.length > 0 ? `关联 ${value.length} 条` : '';
        return '';
      };
      break;
    case FieldType.NUMBER:
    case FieldType.PERCENT:
    case FieldType.CURRENCY:
    case FieldType.DURATION:
    case FieldType.PHONE:
    case FieldType.BARCODE:
      config.cellType = 'text';
      config.editor = 'input';
      break;
    default:
      // 文本类、数字类等使用默认 text 类型
      config.cellType = 'text';
      config.editor = 'input';
      break;
  }
  
  return config;
};

// 构建 VTable 配置
const buildTableConfig = (): any => {
  const columns = orderedVisibleFields.value.map((field) => {
    const sortInfo = currentSorts.value.find(s => s.fieldId === field.id);
    const cellTypeConfig = getCellTypeConfig(field);
    
    // 为 single_select 字段创建带选项的 ListEditor
    if (field.type === FieldType.SINGLE_SELECT) {
      const options = (field.options?.choices || field.options?.options || []) as Array<{id: string, name: string}>;
      cellTypeConfig.editor = new ListEditor({ values: options.map(o => o.name) });
    }
    
    return {
      field: field.id,
      title: field.name,
      width: columnWidths.value[field.id] || 150,
      minWidth: 60,
      sort: true,
      sortState: sortInfo ? (sortInfo.direction === 'asc' ? 'asc' : 'desc') : 'normal',
      ...cellTypeConfig,
      // 单选/多选/成员字段由 customLayout 接管渲染，不设置 Canvas 层样式
      ...((field.type === FieldType.SINGLE_SELECT || field.type === FieldType.MULTI_SELECT) ? {
        style: {
          padding: [0, 8],
        }
      } : {}),
    };
  });

  // 为需要自定义渲染的复杂类型添加 customRender
  // 注意：customRender 输出 Canvas 文本，不支持 HTML 标签
  const complexTypes = [
    FieldType.FORMULA,
    FieldType.AUTO_NUMBER,
    FieldType.CREATED_BY,
    FieldType.CREATED_TIME,
    FieldType.UPDATED_BY,
    FieldType.UPDATED_TIME,
  ];
  
  columns.forEach((col: any) => {
    const field = orderedVisibleFields.value.find(f => f.id === col.field);
    if (!field || !complexTypes.includes(field.type as typeof complexTypes[number])) return;
    
    col.customRender = (args: any) => {
      if (!args || !args.record) return "";
      const value = args.record[field.id];
      if (value === null || value === undefined) return "";

      let displayValue = "";
      switch (field.type) {
        case FieldType.SINGLE_SELECT: {
          // 支持：string ID | {id, name, color} 对象
          const options = (field.options?.choices || field.options?.options || []) as Array<{id: string, name: string, color?: string}>;
          let selectedId = '';
          let selectedName = '';
          let selectedColor = '#6B7280';
          if (typeof value === 'object' && value !== null) {
            selectedId = String((value as any).id || '');
            selectedName = String((value as any).name || '');
            selectedColor = String((value as any).color || '#6B7280');
          } else {
            selectedId = String(value);
          }
          const selectedOption = options.find(opt => opt.id === selectedId || opt.name === selectedName || opt.name === selectedId);
          const displayText = selectedName || selectedOption?.name || selectedId;
          const color = selectedOption?.color || selectedColor;
          return `<span style="background-color: ${color}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px; line-height: 1.5; display: inline-flex; align-items: center; white-space: nowrap;">${displayText}</span>`;
        }
        case FieldType.MULTI_SELECT: {
          // 支持：string[] | {id, name}[] | JSON 字符串
          let items: any[] = [];
          if (Array.isArray(value)) {
            items = value;
          } else if (typeof value === 'string') {
            try { const p = JSON.parse(value); if (Array.isArray(p)) items = p; } catch {}
          }
          if (items.length === 0) return "";
          const multiOptions = (field.options?.choices || field.options?.options || []) as Array<{id: string, name: string, color?: string}>;
          return items.map(v => {
            const itemId = typeof v === 'object' && v !== null ? String((v as any).id || '') : String(v);
            const itemName = typeof v === 'object' && v !== null ? String((v as any).name || '') : '';
            const itemColor = typeof v === 'object' && v !== null ? String((v as any).color || '') : '';
            const opt = multiOptions.find(o => o.id === itemId || o.name === itemName || o.name === itemId);
            const color = opt?.color || itemColor || '#6B7280';
            const label = itemName || opt?.name || itemId;
            return `<span style="background-color: ${color}; color: white; padding: 2px 8px; border-radius: 12px; font-size: 12px; line-height: 1.5; display: inline-flex; align-items: center; white-space: nowrap; margin-right: 4px;">${label}</span>`;
          }).join("");
        }
        case FieldType.MEMBER: {
          // 支持：string[] | {id, name}[] | {id, name} 对象 | JSON 字符串
          let members: any[] = [];
          if (Array.isArray(value)) {
            members = value;
          } else if (typeof value === 'string') {
            try { const p = JSON.parse(value); if (Array.isArray(p)) members = p; } catch {}
          } else if (typeof value === 'object' && value !== null) {
            // 单个成员对象，包装为数组
            members = [value];
          }
          if (members.length === 0) return "";
          const colors = ['#2d7cfc', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899'];
          const displayMembers = members.slice(0, 2);
          const overflow = members.length > 2 ? members.length - 2 : 0;
          let html = '<div style="display: flex; align-items: center; gap: 4px;">';
          displayMembers.forEach((m: any) => {
            const memberId = typeof m === 'string' ? m : String((m as any).id || m);
            const memberName = typeof m === 'string' ? m : String((m as any).name || m);
            const hash = memberId.split('').reduce((acc: number, c: string) => acc + c.charCodeAt(0), 0);
            const avatarColor = colors[Math.abs(hash) % colors.length];
            const initial = memberName.charAt(0).toUpperCase();
            html += `<span style="width: 20px; height: 20px; border-radius: 50%; background-color: ${avatarColor}; color: white; display: inline-flex; align-items: center; justify-content: center; font-size: 10px; font-weight: 600; flex-shrink: 0;">${initial}</span>`;
          });
          if (overflow > 0) {
            html += `<span style="padding: 0 6px; background-color: #e5e7eb; border-radius: 4px; font-size: 11px; color: #6B7280; line-height: 20px;">+${overflow}</span>`;
          }
          html += '</div>';
          return html;
        }
        case FieldType.ATTACHMENT: {
          // 支持：{id, url, name}[] | {id, url, name} 对象 | JSON 字符串
          let files: any[] = [];
          if (Array.isArray(value)) {
            files = value;
          } else if (typeof value === 'string') {
            try { const p = JSON.parse(value); if (Array.isArray(p)) files = p; } catch {}
          } else if (typeof value === 'object' && value !== null) {
            // 单个文件对象，包装为数组
            files = [value];
          }
          if (files.length === 0) return "";
          return `<span style="display: inline-flex; align-items: center; gap: 4px; font-size: 13px; color: #6B7280;">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="flex-shrink: 0;">
              <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66l-9.2 9.19a2 2 0 01-2.83-2.83l8.49-8.48"/>
            </svg>
            <span>${files.length} 个文件</span>
          </span>`;
        }
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
    };
  });

  // 为需要 VRender 自定义布局的字段类型添加 customLayout
  // 返回 VRender Group 节点，支持 flex 布局和自动换行
  // 参考: https://visactor.io/vtable/demo/custom-render/cell-custom-reactive-layout
  const layoutTypes = [
    FieldType.SINGLE_SELECT,
    FieldType.MULTI_SELECT,
    FieldType.MEMBER,
    FieldType.RATING,
  ];
  columns.forEach((col: any) => {
    const field = orderedVisibleFields.value.find(f => f.id === col.field);
    if (!field || !layoutTypes.includes(field.type as typeof layoutTypes[number])) return;

    col.customLayout = (args: any) => {
      const { table, row, col: colIdx, rect } = args;
      if (!table) return { renderDefault: true };

      const value = table.getCellValue(colIdx, row);
      // 仅对 null/undefined 回退到默认渲染，数值 0 应正常显示灰星星
      if (value === null || value === undefined) return { renderDefault: true };

      const cellHeight = rect?.height || table.getCellRect(colIdx, row).height || 40;
      const cellWidth = rect?.width || table.getCellRect(colIdx, row).width || 150;
      const fontFamily = 'system-ui, -apple-system, sans-serif';
      const fontSize = 12;

      // 测量文本宽度
      const measureText = (text: string): number => {
        try {
          if (table && typeof table.measureText === 'function') {
            const result = table.measureText(text, { fontSize, fontFamily });
            if (result && typeof result.width === 'number') return result.width;
          }
        } catch (_) { /* ignore */ }
        return text.length * 7;
      };

      switch (field.type) {
        case FieldType.SINGLE_SELECT: {
          const val = String(value);
          const options = (field.options?.choices || field.options?.options || []) as Array<{id: string, name: string, color?: string}>;
          const found = options.find(o => o.name === val);
          const color = found?.color || '#6B7280';

          const tagHeight = 26;
          const textWidth = measureText(val);
          const tagWidth = Math.min(textWidth + 16, cellWidth);
          const yOffset = Math.max(0, (cellHeight - tagHeight) / 2);

          const container = createGroup({
            width: cellWidth,
            height: cellHeight
          });

          const bg = createRect({
            x: 0,
            y: yOffset,
            width: tagWidth,
            height: tagHeight,
            cornerRadius: 12,
            fill: color
          });
          container.add(bg);

          const text = createText({
            x: 8,
            y: yOffset + tagHeight / 2,
            text: val,
            fontSize,
            fill: '#ffffff',
            textBaseline: 'middle'
          });
          container.add(text);

          return { rootContainer: container, renderDefault: false };
        }
        case FieldType.MULTI_SELECT: {
          const vals = String(value).split(', ').filter(Boolean);
          if (vals.length === 0) return { renderDefault: true };
          const options = (field.options?.choices || field.options?.options || []) as Array<{id: string, name: string, color?: string}>;

          const tagHeight = 26;
          const gap = 8;

          // 使用 flex 布局容器实现自动换行
          const container = createGroup({
            width: cellWidth,
            height: cellHeight,
            display: 'flex',
            flexDirection: 'row',
            flexWrap: 'wrap',
            alignContent: 'center',
            alignItems: 'center'
          });

          vals.forEach((v) => {
            const opt = options.find(o => o.name === v);
            const color = opt?.color || '#6B7280';
            const textWidth = measureText(v);
            const tagWidth = textWidth + 16;

            // 每个标签用一个子 Group 包裹（flex 布局下自动排列）
            const tagGroup = createGroup({
              width: tagWidth + gap,
              height: tagHeight,
              flexDirection: 'row' as const,
              alignItems: 'center' as const
            });

            const bg = createRect({
              x: 0,
              y: 0,
              width: tagWidth,
              height: tagHeight,
              cornerRadius: 12,
              fill: color
            });
            tagGroup.add(bg);

            const text = createText({
              x: 8,
              y: tagHeight / 2,
              text: v,
              fontSize,
              fill: '#ffffff',
              textBaseline: 'middle'
            });
            tagGroup.add(text);

            container.add(tagGroup);
          });

          return { rootContainer: container, renderDefault: false };
        }
        case FieldType.MEMBER: {
          // 解析结构化成员数据 [{"id":"...","name":"..."}]
          let memberData: Array<{id: string, name: string}> = [];
          try {
            const parsed = JSON.parse(String(value));
            if (Array.isArray(parsed) && parsed.length > 0) {
              memberData = parsed.map((m: any) => ({
                id: String(m.id || ''),
                name: String(m.name || m.id || '')
              }));
            }
          } catch (_) {
            // 降级：尝试逗号分隔的回退解析
            const parts = String(value).split(', ').filter(Boolean);
            memberData = parts.map(p => ({ id: p, name: p }));
          }
          if (memberData.length === 0) {
            // 空值显示占位符 -
            const emptyLabel = createText({
              x: 0,
              y: cellHeight / 2,
              text: '-',
              fontSize: 12,
              fill: '#999999',
              textBaseline: 'middle'
            });
            const container = createGroup({ width: cellWidth, height: cellHeight });
            container.add(emptyLabel);
            return { rootContainer: container, renderDefault: false };
          }

          const avatarColors = ['#2d7cfc', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899'];
          const avatarSize = 22;
          const radius = avatarSize / 2;
          const displayMembers = memberData.slice(0, 2);
          const overflow = memberData.length > 2 ? memberData.length - 2 : 0;

          const container = createGroup({
            width: cellWidth,
            height: cellHeight
          });

          let currentX = 0;
          const yOffset = Math.max(0, (cellHeight - avatarSize) / 2);
          const nameSpacing = 4; // 头像与名称间距
          const memberSpacing = 12; // 成员间间距

          displayMembers.forEach((m) => {
            const hash = m.name.split('').reduce((acc, c) => acc + c.charCodeAt(0), 0);
            const avatarColor = avatarColors[Math.abs(hash) % avatarColors.length];
            const initial = m.name.charAt(0).toUpperCase();

            // 圆形头像
            const circle = createCircle({
              x: currentX + radius,
              y: yOffset + radius,
              radius,
              fill: avatarColor
            });
            container.add(circle);

            // 首字母
            const initialText = createText({
              x: currentX + radius,
              y: yOffset + radius,
              text: initial,
              fontSize: 10,
              fontWeight: '600',
              fill: '#ffffff',
              textBaseline: 'middle',
              textAlign: 'center'
            });
            container.add(initialText);

            // 完整名称
            const nameTextX = currentX + avatarSize + nameSpacing;
            const nameText = createText({
              x: nameTextX,
              y: yOffset + radius,
              text: m.name,
              fontSize: 12,
              fill: '#333333',
              textBaseline: 'middle'
            });
            container.add(nameText);

            // 计算当前成员的宽度（头像+间距+名称宽度+成员间距）
            const nameWidth = measureText(m.name);
            currentX += avatarSize + nameSpacing + nameWidth + memberSpacing;
          });

          if (overflow > 0) {
            const overflowText = `+${overflow}`;
            const overflowPadding = 6;
            const overflowTextWidth = measureText(overflowText);
            const overflowWidth = overflowTextWidth + overflowPadding * 2;
            const overflowHeight = 20;
            const overflowY = Math.max(0, (cellHeight - overflowHeight) / 2);

            const overflowBg = createRect({
              x: currentX,
              y: overflowY,
              width: overflowWidth,
              height: overflowHeight,
              cornerRadius: 4,
              fill: '#e5e7eb'
            });
            container.add(overflowBg);

            const overflowLabel = createText({
              x: currentX + overflowPadding,
              y: overflowY + overflowHeight / 2,
              text: overflowText,
              fontSize: 11,
              fill: '#6B7280',
              textBaseline: 'middle'
            });
            container.add(overflowLabel);
          }

          return { rootContainer: container, renderDefault: false };
        }
        case FieldType.RATING: {
          const maxRating = Number(field.options?.maxRating) || 5;
          const rating = Math.max(0, Math.min(Number(value) || 0, maxRating));
          const starSize = 16;
          const starSpacing = 4;
          const totalWidth = maxRating * (starSize + starSpacing) - starSpacing;
          const xOffset = Math.max(0, (cellWidth - totalWidth) / 2);
          const yOffset = Math.max(0, (cellHeight - starSize) / 2);

          const container = createGroup({
            width: cellWidth,
            height: cellHeight
          });

          // 绘制灰色背景星星
          for (let i = 0; i < maxRating; i++) {
            const cx = xOffset + i * (starSize + starSpacing) + starSize / 2;
            const cy = yOffset + starSize / 2;
            const star = createPath({
              path: getStarPath(cx, cy, starSize / 2, 5, 0.5),
              fill: '#e5e7eb'
            });
            container.add(star);
          }

          // 绘制黄色前景星星（整星）
          const fullStars = Math.floor(rating);
          for (let i = 0; i < fullStars; i++) {
            const cx = xOffset + i * (starSize + starSpacing) + starSize / 2;
            const cy = yOffset + starSize / 2;
            const star = createPath({
              path: getStarPath(cx, cy, starSize / 2, 5, 0.5),
              fill: '#F59E0B'
            });
            container.add(star);
          }

          // 绘制半星（通过 Group clip 裁剪左侧一半）
          const halfStar = rating - fullStars;
          if (halfStar >= 0.5) {
            const cx = xOffset + fullStars * (starSize + starSpacing) + starSize / 2;
            const cy = yOffset + starSize / 2;
            const star = createPath({
              path: getStarPath(cx, cy, starSize / 2, 5, 0.5),
              fill: '#F59E0B'
            });
            const halfGroup = createGroup({
              x: xOffset + fullStars * (starSize + starSpacing),
              y: yOffset,
              width: starSize / 2,
              height: starSize,
              clip: true
            });
            halfGroup.add(star);
            container.add(halfGroup);
          }

          return { rootContainer: container, renderDefault: false };
        }
      }

      return { renderDefault: true };
    };
  });

  // 转换 records 为 VTable 需要的格式 - 预处理字段值
  const tableRecords = sortedRecords.value.map((record) => {
    const row: any = {
      _recordId: record?.id || '',
      _originalRecord: record,
    };
    orderedVisibleFields.value.forEach(field => {
      if (!field?.id || !record?.values) return;
      const rawVal = record.values[field.id];
      
      switch (field.type) {
        case FieldType.SINGLE_SELECT: {
          // 将 ID 映射为选项名称
          const opts = (field.options?.choices || field.options?.options || []) as Array<{id: string, name: string, color?: string}>;
          const selId = typeof rawVal === 'object' && rawVal !== null ? String((rawVal as any).id || '') : String(rawVal || '');
          const found = opts.find(o => o.id === selId || o.name === selId);
          row[field.id] = found?.name || selId;
          break;
        }
        case FieldType.MULTI_SELECT: {
          // 将 ID 数组映射为逗号分隔的名称
          let items: any[] = [];
          if (Array.isArray(rawVal)) items = rawVal;
          else if (typeof rawVal === 'string') try { const p = JSON.parse(rawVal); if (Array.isArray(p)) items = p; } catch {}
          if (items.length === 0) { row[field.id] = ''; break; }
          const opts = (field.options?.choices || field.options?.options || []) as Array<{id: string, name: string}>;
          row[field.id] = items.map(v => {
            const vid = typeof v === 'object' ? String((v as any).id || '') : String(v);
            const vname = typeof v === 'object' ? String((v as any).name || '') : '';
            const of = opts.find(o => o.id === vid || o.name === vid);
            return vname || of?.name || vid;
          }).join(', ');
          break;
        }
        case FieldType.MEMBER: {
  // 将成员 ID/对象解析为结构化成员列表，尝试从缓存解析名称
  let mems: any[] = [];
  if (Array.isArray(rawVal)) mems = rawVal;
  else if (typeof rawVal === 'string') try { const p = JSON.parse(rawVal); if (Array.isArray(p)) mems = p; } catch {}
  else if (typeof rawVal === 'object' && rawVal !== null) mems = [rawVal];

  const resolvedMembers = mems.map((m) => {
    let id = '';
    let name: string | undefined;

    if (typeof m === 'string') {
      id = m;
    } else if (typeof m === 'object' && m !== null) {
      id = String(m.user_id || m.id || '');
      name = m.name || undefined;
    } else {
      id = String(m);
    }

    if (!name) {
      const cached = userCacheStore.getCachedUser(id);
      name = cached?.name || id;
    }

    return { id, name: name || id };
  });

  row[field.id] = JSON.stringify(resolvedMembers);
  break;
}
        case FieldType.ATTACHMENT: {
          // 统计文件数量
          if (!rawVal) { row[field.id] = ''; break; }
          if (Array.isArray(rawVal)) { row[field.id] = `${rawVal.length} 个文件`; break; }
          if (typeof rawVal === 'string') {
            try { const p = JSON.parse(rawVal); if (Array.isArray(p)) { row[field.id] = `${p.length} 个文件`; break; } } catch {}
            row[field.id] = rawVal; break;
          }
          if (typeof rawVal === 'object' && rawVal !== null) {
            if (typeof (rawVal as any).length === 'number') { row[field.id] = `${(rawVal as any).length} 个文件`; break; }
            const keys = Object.keys(rawVal);
            row[field.id] = keys.length > 0 ? `${keys.length} 个文件` : ''; break;
          }
          row[field.id] = String(rawVal);
          break;
        }
        default:
          row[field.id] = rawVal;
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
    defaultRowHeight: 36,
    autoRowHeight: false,
    rowSeriesNumber: {
      title: '#',
      width: 'auto',
      cellType: 'checkbox',
      headerType: 'checkbox'
    },
    allowCopy: true,
    editCellTrigger: 'doubleclick',
    keyboardOptions: {
      editCellOnEnter: true,
      moveFocusCellOnTab: true,
      moveEditCellOnArrowKeys: true,
    },
    select: {
      mode: 'multiple',
      enable: true,
      highlightMode: 'row',
    },
    containerFit: {
      width: true,
      height: true
    },
    // theme: {
    //   table: {
    //     borderLineWidth: 1,
    //     borderColor: '#e5e7eb',
    //     headerStyle: {
    //       bgColor: '#f9fafb',
    //       color: '#374151',
    //       fontSize: 13,
    //       fontWeight: 'bold',
    //     },
    //     bodyStyle: {
    //       bgColor: '#ffffff',
    //       color: '#374151',
    //       fontSize: 13,
    //     },
    //   },
    //   selectionStyle: {
    //     inlineRowBgColor: 'rgba(64, 158, 255, 0.1)',
    //   },
    // },
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

  // 复选框状态变更 - 仅更新 checkboxSelectedRows
  tableInstanceAny.on('checkbox_state_change', (args: any) => {
    if (!tableInstance) return;

    const { col, row, checked } = args;

    if (tableInstance.isHeader(col, row)) {
      // 表头复选框（全选/取消全选）
      checkboxSelectedRows.value = checked
        ? sortedRecords.value.map(r => r.id)
        : [];
    } else {
      // 行复选框（单个切换）
      const record = tableInstance.getCellOriginRecord(col, row);
      if (record && record._recordId) {
        const id = record._recordId;
        if (checked) {
          if (!checkboxSelectedRows.value.includes(id)) {
            checkboxSelectedRows.value = [...checkboxSelectedRows.value, id];
          }
        } else {
          checkboxSelectedRows.value = checkboxSelectedRows.value.filter(i => i !== id);
        }
      }
    }
  });

  // 开关状态变更 - 更新数据并持久化
  tableInstanceAny.on('switch_state_change', async (args: any) => {
    if (!tableInstance) return;

    const { col, row, checked } = args;

    // 仅处理行数据（非表头）
    if (!tableInstance.isHeader(col, row)) {
      const record = tableInstance.getCellOriginRecord(col, row);
      if (record && record._recordId && record._originalRecord) {
        const recordId = record._recordId;
        const fieldId = orderedVisibleFields.value[col - 1]?.id;
        if (!fieldId) return;

        const originalRecord = record._originalRecord;

        try {
          const tableId = tableStore.currentTable?.id;
          if (!tableId) return;

          await recordService.updateRecord(recordId, {
            values: {
              ...originalRecord.values,
              [fieldId]: checked,
            } as Record<string, CellValue>,
          });

          // 刷新表格数据
          await tableStore.refreshRecords(tableId);
        } catch (error) {
          console.error('开关状态保存失败:', error);
          ElMessage.error('开关状态保存失败');
        }
      }
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

  // 单元格值变更事件
  tableInstanceAny.on('change_cell_value', async (args: any) => {
    if (!args || !args.record || !args.record._recordId || !args.record._originalRecord) return;
    
    const recordId = args.record._recordId;
    const fieldId = orderedVisibleFields.value[args.col - 1]?.id;
    if (!fieldId) return;
    
    const newValue = args.newValue;
    const originalRecord = args.record._originalRecord;
    
    try {
      const tableId = tableStore.currentTable?.id;
      if (!tableId) return;
      
      const values = {
        ...originalRecord.values,
        [fieldId]: newValue,
      };
      
      await recordService.updateRecord(recordId, {
        values: values as Record<string, CellValue>,
      });
      
      // 刷新表格数据
      await tableStore.refreshRecords(tableId);
      ElMessage.success('编辑保存成功');
    } catch (error) {
      console.error('编辑保存失败:', error);
      ElMessage.error('编辑保存失败');
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

// 用户缓存更新时刷新表格（成员名称异步加载完成后重渲染）
watch(() => userCacheStore.cacheStats.size, () => {
  updateTable();
});

// 处理文档点击 - 点击表格外部时隐藏悬浮图标
const handleDocumentClick = (e: MouseEvent) => {
  // 如果点击在表格容器内，由 click_cell 管理图标显示
  if (tableContainerRef.value?.contains(e.target as Node)) return;
  actionIconVisible.value = false;
  selectedCell.value = null;
};

onMounted(() => {
  initColumnWidths();
  initTable();
  setupRealtimeListeners();
  document.addEventListener('click', handleDocumentClick);
});

onBeforeUnmount(() => {
  cleanupRealtimeListeners();
  document.removeEventListener('click', handleDocumentClick);
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