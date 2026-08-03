<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch, nextTick, shallowRef, reactive } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { useTableStore } from "@/stores/tableStore";
import { useViewStore } from "@/stores/viewStore";
import { useCollaborationStore } from "@/stores/collaborationStore";
import { useAuthStore } from "@/stores/authStore";
import { useMemberStore } from "@/stores/memberStore";
import { userApi } from "@/api/user";
import { realtimeEventEmitter } from "@/services/realtime/eventEmitter";
import LoadingProgress from "@/components/common/LoadingProgress.vue";
import { SmartTableDataSource } from "@/services/SmartTableDataSource";
import type {
  DataRecordUpdatedBroadcast,
  DataRecordCreatedBroadcast,
  DataRecordDeletedBroadcast,
} from "@/services/realtime/eventTypes";

import type { RecordEntity, FieldEntity } from "@/db/schema";
import { db } from "@/db/schema";
import { recordService } from "@/db/services";
import { serializeRecordValues } from "@/utils/recordValueSerializer";
import { FieldType, fieldTypeSvgContentMap } from "@/types/fields";
import type { FieldTypeValue } from "@/types/fields";
import type { CellValue } from "@/types";
import { formatDateTime, formatDate } from "@/utils/timezone";
import { useUserCacheStore } from "@/stores/userCacheStore";
import { validateFieldFormat } from "@/utils/validation";
import { FormulaEngine } from "@/utils/formula/engine";
import { linkApiService } from "@/services/api/linkApiService";
import { viewApiService } from "@/services/api/viewApiService";
import { recordApiService } from "@/services/api/recordApiService";

// 导入 VTable
import { ListTable, themes, register as registerVTable } from "@visactor/vtable";
// 导入 VRender 图形工厂函数（用于 customLayout）
import { createGroup, createText, createRect, createCircle, createPath, createImage } from '@visactor/vtable/es/vrender';
// 导入 VTable 编辑器
import { InputEditor, DateInputEditor } from '@visactor/vtable-editors';
import type { IEditor, EditContext, RectProps } from '@visactor/vtable-editors';
// 导入 VTable 搜索组件
import { SearchComponent } from '@visactor/vtable-search';
// 导入 Element Plus 图标
import { Search } from '@element-plus/icons-vue';
// 导入 ContextMenu 组件
import ContextMenu from "@/components/common/ContextMenu.vue";
// 导入字段属性对话框
import FieldDialog from "@/components/dialogs/FieldDialog.vue";
// 导入记录详情对话框
import RecordDetailDrawer from "@/components/dialogs/RecordDetailDrawer.vue";
// 导入附件管理浮动面板
import AttachmentManager from "@/components/fields/AttachmentManager.vue";
// 导入关联记录选择器
import LinkRecordSelector from "@/components/fields/LinkField/LinkRecordSelector.vue";
// 主从表功能
import { useMasterDetail } from "@/composables/useMasterDetail";
import { masterDetailService } from "@/services/masterDetailService";
import SubTableToolbar from "@/components/views/TableView/SubTableToolbar.vue";

function recalcFloatingPanelPosition(
  col: number, row: number, panelWidth: number, panelHeight: number
): { x: number; y: number } | null {
  const cellRect = (tableInstance as any)?.getCellRect(col, row);
  const canvas = (tableInstance as any)?.canvas;
  const canvasRect = canvas?.getBoundingClientRect();
  if (!cellRect || !canvasRect) return null;

  // VTable 的 getCellRect 返回表格内绝对坐标，需加上 canvas 视口位置和 tableX/tableY 偏移
  const tableX = (tableInstance as any).tableX || 0;
  const tableY = (tableInstance as any).tableY || 0;
  const cellLeft = canvasRect.left + tableX + cellRect.left;
  const cellTop = canvasRect.top + tableY + cellRect.top;
  const cellRight = cellLeft + cellRect.width;
  const cellBottom = cellTop + cellRect.height;

  let panelX = cellRight;
  let panelY = cellBottom;

  if (panelX + panelWidth > window.innerWidth - 16) {
    panelX = cellLeft - panelWidth;
  }
  if (panelY + panelHeight > window.innerHeight - 16) {
    panelY = cellTop - panelHeight;
  }
  if (panelX < 8) panelX = 8;
  if (panelY < 8) panelY = 8;

  return { x: panelX, y: panelY };
}

interface Props {
  tableId?: string;
  viewId?: string;
  readonly?: boolean;
  records?: any[];
  groupBy?: string[];
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
  (e: "group-add-record", groupFieldValues: Record<string, any>): void;
}>();

const tableStore = useTableStore();
const viewStore = useViewStore();
const collabStore = useCollaborationStore();
const userCacheStore = useUserCacheStore();
const memberStore = useMemberStore();
// 权限控制：字段管理（隐藏/编辑属性）需要管理员及以上角色
const canManage = computed(() => memberStore.canManage);

const tableContainerRef = ref<HTMLElement | null>(null);
let tableInstance: ListTable | null = null;
let smartDataSource: SmartTableDataSource | null = null;

// 主从表功能
const {
  masterDetailPlugin,
  linkFields: masterDetailLinkFields,
  currentLinkFieldId,
  hasLinkFields,
  hasMultipleLinkFields,
  detectLinkFields,
  createPluginInstance,
  handleLazyLoad,
  handleSubTableEvent,
  switchLinkField,
  refreshSubTable,
  setColumnEnhancer,
  setRecordTransformer,
  dispose: disposeMasterDetail,
} = useMasterDetail({
  readonly: props.readonly,
  onSubTableAction: async (action, data) => {
    if (action === 'edit') {
      // 子表编辑后刷新关联显示数据
      loadLinkDisplayData();
    } else if (action === 'unlink' && data?.targetRecordId) {
      // 子表右键解除关联
      await handleSubTableUnlink(data.targetRecordId);
    } else if (action === 'click_cell') {
      // 子表单元格点击：显示放大按钮（与主表行为一致）
      // 点击放大按钮时才真正展开详情抽屉
      const { originalEventArgs, subTable } = data || {};
      if (subTable && originalEventArgs?.col !== undefined && originalEventArgs?.row !== undefined) {
        const cellRecord = subTable.getCellOriginRecord(originalEventArgs.col, originalEventArgs.row);
        if (!cellRecord) return;

        let iconX: number | undefined;
        let iconY: number | undefined;

        // 方法1: 优先使用原生鼠标事件的 clientX/clientY（最可靠）
        // 子表与主表共享 Canvas，坐标转换复杂，直接使用鼠标位置避免坐标计算错误
        const nativeEvent = originalEventArgs.event;
        if (nativeEvent && typeof nativeEvent.clientX === 'number') {
          iconX = nativeEvent.clientX + 12;
          iconY = nativeEvent.clientY - 12;
        }

        // 方法2: 回退到子表单元格位置计算
        if (iconX === undefined || iconY === undefined) {
          let cellRect;
          try {
            cellRect = subTable.getCellRect(originalEventArgs.col, originalEventArgs.row);
          } catch (e) {
            console.warn('[VTableView] 获取子表单元格位置失败:', e);
            return;
          }
          if (!cellRect || !tableContainerRef.value) return;

          // 子表与主表共享 Canvas，通过 viewBox 获取子表在主 Canvas 中的偏移
          const containerRect = tableContainerRef.value.getBoundingClientRect();
          const viewBox = subTable.options?.viewBox;
          const viewBoxX = viewBox?.x1 || 0;
          const viewBoxY = viewBox?.y1 || 0;

          iconX = containerRect.left + viewBoxX + cellRect.left + cellRect.width + 8;
          iconY = containerRect.top + viewBoxY + cellRect.top;
        }

        selectedCell.value = {
          col: originalEventArgs.col,
          row: originalEventArgs.row,
          record: cellRecord,
          x: Math.min(iconX, window.innerWidth - 40),
          y: Math.max(iconY, 4),
        };
        actionIconVisible.value = true;
      }
    }
  },
});

// 树形视图：索引列 "+" 按钮状态
const treeAddChildIconVisible = ref(false);
const treeAddChildIcon = ref<{ x: number; y: number; recordId: string; recordName?: string } | null>(null);
const treeAddChildLoading = ref(false);
let hideTreeAddChildIconTimer: ReturnType<typeof setTimeout> | null = null;

const clearHideTreeAddChildIconTimer = () => {
  if (hideTreeAddChildIconTimer) {
    clearTimeout(hideTreeAddChildIconTimer);
    hideTreeAddChildIconTimer = null;
  }
};

const delayHideTreeAddChildIcon = () => {
  clearHideTreeAddChildIconTimer();
  hideTreeAddChildIconTimer = setTimeout(() => {
    treeAddChildIconVisible.value = false;
    treeAddChildIcon.value = null;
  }, 300);
};

// 子表工具栏状态
const subTableToolbarVisible = ref(false);
const subTableToolbarRecordId = ref('');
const subTableToolbarCol = ref(0);
const subTableToolbarRow = ref(0);
// 子表工具栏动态位置（相对于表格容器，跟随子表末尾定位）
const subTableToolbarPosition = ref<{ top: number; right: number }>({ top: 0, right: 0 });

/**
 * 计算并更新子表工具栏位置
 * 定位到展开子表的末尾右侧：通过主表 getCellRect 获取展开行底部位置，
 * 减去容器偏移并加上子表高度，得到子表末尾的屏幕坐标
 */
const updateSubTableToolbarPosition = () => {
  if (!tableInstance || !tableContainerRef.value) {
    subTableToolbarPosition.value = { top: 0, right: 0 };
    return;
  }
  try {
    const row = subTableToolbarRow.value;
    const col = subTableToolbarCol.value;
    // 获取展开行（含子表）的整体矩形
    const cellRect = tableInstance.getCellRect(col, row);
    if (!cellRect) {
      subTableToolbarPosition.value = { top: 0, right: 0 };
      return;
    }
    // cellRect 是相对于 Canvas 的坐标，需转为相对于表格容器的坐标
    // 子表展开后，展开行的高度包含主行 + 子表区域
    // 工具栏定位到子表末尾（展开行底部）上方 4px，右侧留 16px
    const containerRect = tableContainerRef.value.getBoundingClientRect();
    const canvasRect = tableInstance.getCanvasRect?.();
    const canvasOffsetTop = canvasRect ? (canvasRect as any).top - containerRect.top : 0;
    const canvasOffsetLeft = canvasRect ? (canvasRect as any).left - containerRect.left : 0;

    // 子表末尾的 Y 坐标（展开行底部）
    const subTableBottomY = canvasOffsetTop + cellRect.top + cellRect.height;
    // 工具栏顶部位置：子表末尾上方 4px
    const top = subTableBottomY - 40; // 工具栏高度约 36px，向上偏移使其紧贴子表末尾
    // 右侧距离：Canvas 右侧
    const right = 16;

    subTableToolbarPosition.value = { top: Math.max(0, top), right };
  } catch (e) {
    console.warn('[VTableView] 计算子表工具栏位置失败:', e);
    subTableToolbarPosition.value = { top: 0, right: 0 };
  }
};

// 子表添加按钮禁用状态（一对一关系且已有记录时）
const subTableDisabledAdd = ref(false);
const subTableAddDisabledReason = ref('');

// 附件管理器状态
const attachmentManagerVisible = ref(false);
const attachmentManagerPosition = ref({ x: 0, y: 0 });
const attachmentManagerField = ref<FieldEntity | null>(null);
const attachmentManagerRecordId = ref<string>('');
const attachmentManagerInitialValue = ref<any>(null);
const attachmentManagerOriginalRecord = ref<any>(null);
// 记录触发浮窗的单元格坐标，用于滚动实时同步位置
const lastAttachmentCellCoords = ref<{ col: number; row: number } | null>(null);

// 图片缩略图单击预览状态
const attachmentImagePreviewVisible = ref(false);
const attachmentImagePreviewUrl = ref('');
const attachmentImagePreviewName = ref('');

// ==================== 关联记录选择器状态 ====================
const linkSelectorVisible = ref(false);
const linkSelectorTargetTableId = ref('');
const linkSelectorDisplayFieldId = ref('');
const linkSelectorSelectedIds = ref<string[]>([]);
const linkSelectorFieldId = ref('');
const linkSelectorRecordId = ref('');
const linkSelectorAllowMultiple = ref(true);
/** 自关联（树形）场景下需要排除的当前记录 ID */
const linkSelectorExcludeRecordId = ref('');
const linkSelectorLinkedRecords = ref<{ record_id: string; display_value: string }[]>([]);

// ==================== 搜索功能状态 ====================
const searchVisible = ref(false);
const searchComponent = shallowRef<SearchComponent | null>(null);
const searchInput = ref('');
const searchResultIndex = ref(0);
const searchTotalCount = ref(0);

// ==================== 关联字段数据缓存 ====================
// 键: `${recordId}:${fieldId}`, 值: display_value 数组
const linkDisplayCache = reactive<Record<string, string[]>>({});
// 关联字段加载状态
const linkLoadingStates = reactive<Record<string, boolean>>({});
// 关联字段错误状态
const linkErrorStates = reactive<Record<string, string>>({});

// ==================== 单元格值校验 ====================

// 自定义单元格校验结果类型
interface CellValidationError {
  col: number;
  row: number;
  fieldId: string;
  message: string;
}

// 当前被标记为校验失败的单元格
const cellErrors = ref<CellValidationError[]>([]);

// 校验单元格值（按字段类型）
function validateCellValue(
  value: any,
  field: FieldEntity
): { valid: boolean; message?: string } {
  // 空值不校验（由必填逻辑处理）
  if (value === null || value === undefined || value === '') {
    return { valid: true };
  }

  switch (field.type) {
    case FieldType.NUMBER:
      if (isNaN(Number(value))) {
        return { valid: false, message: `"${field.name}" 字段只能填写数字` };
      }
      return { valid: true };

    case FieldType.PROGRESS:
      if (isNaN(Number(value))) {
        return { valid: false, message: `"${field.name}" 字段只能填写数字` };
      }
      const num = Number(value);
      if (num < 0 || num > 100) {
        return { valid: false, message: `"${field.name}" 字段的值应在 0-100 之间` };
      }
      return { valid: true };

    case FieldType.EMAIL: {
      const result = validateFieldFormat(value, FieldType.EMAIL as any);
      if (!result.valid) {
        return { valid: false, message: result.error || `"${field.name}" 格式不正确，请输入正确的邮箱地址` };
      }
      return { valid: true };
    }

    case FieldType.SINGLE_LINE_TEXT: {
      // 仅当字段配置了 regex 时执行正则校验
      const regexPattern = field.options?.regex as string | undefined;
      if (regexPattern) {
        const result = validateFieldFormat(value, FieldType.SINGLE_LINE_TEXT as any, field);
        if (!result.valid) {
          return {
            valid: false,
            message: result.error || `${field.name} 格式不正确`,
          };
        }
      }
      return { valid: true };
    }

    case FieldType.PHONE: {
      const result = validateFieldFormat(value, FieldType.PHONE as any);
      if (!result.valid) {
        return { valid: false, message: result.error || `"${field.name}" 格式不正确，请输入正确的11位手机号码` };
      }
      return { valid: true };
    }

    case FieldType.URL:
    case FieldType.LINK: {
      const result = validateFieldFormat(value, FieldType.URL as any);
      if (!result.valid) {
        return { valid: false, message: result.error || `"${field.name}" 格式不正确，请输入正确的链接地址` };
      }
      return { valid: true };
    }

    default:
      return { valid: true };
  }
}

// 标记单元格校验失败（红色边框高亮）
function markCellError(col: number, row: number, fieldId: string, message: string) {
  // 清除该单元格的旧错误标记
  clearCellError(col, row);

  // 记录错误
  cellErrors.value.push({ col, row, fieldId, message });

  // 通过 VTable registerCustomCellStyle + arrangeCustomCellStyle 实现红色高亮
  try {
    const tableAny = tableInstance as any;
    // 注册错误样式（只在首次注册）
    tableAny.registerCustomCellStyle('validation-error-cell', {
      borderColor: ['red', 'red', 'red', 'red'],
      borderLineWidth: [2, 2, 2, 2],
      bgColor: '#fff5f5'
    });
    // 应用到单元格
    tableAny.arrangeCustomCellStyle({ col, row }, 'validation-error-cell');
  } catch (e) {
    console.warn('标记单元格错误样式失败:', e);
  }
}

// 清除单元格校验错误标记
function clearCellError(col: number, row: number) {
  const idx = cellErrors.value.findIndex(e => e.col === col && e.row === row);
  if (idx >= 0) {
    cellErrors.value.splice(idx, 1);
  }
  try {
    (tableInstance as any)?.arrangeCustomCellStyle({ col, row }, '');
  } catch (e) {
    // ignore
  }
}

// 注册 VTable 编辑器
const inputEditor = new InputEditor();
const dateEditor = new DateInputEditor();
registerVTable.editor('input', inputEditor);
registerVTable.editor('date', dateEditor);

// 自定义日期编辑器（仅日期，支持 input type=date 格式转换）
class DateOnlyEditor extends InputEditor {
  editorType = 'DateOnly';
  createElement() {
    const input = document.createElement('input');
    input.setAttribute('type', 'date');
    input.style.padding = '4px';
    input.style.width = '100%';
    input.style.boxSizing = 'border-box';
    input.style.position = 'absolute';
    input.style.backgroundColor = '#FFFFFF';
    input.style.borderRadius = '0px';
    input.style.border = '2px solid #d9d9d9';
    input.addEventListener('focus', () => {
      input.style.borderColor = '#4A90E2';
      input.style.outline = 'none';
    });
    input.addEventListener('blur', () => {
      input.style.borderColor = '#d9d9d9';
    });
    this.element = input;
    this.container.appendChild(input);
    input.addEventListener('keydown', (e: KeyboardEvent) => {
      if (e.key === 'a' && (e.ctrlKey || e.metaKey)) e.stopPropagation();
    });
    input.addEventListener('wheel', (e: Event) => { e.preventDefault(); });
  }
  setValue(value: any) {
    let date: Date | null = null;
    if (value instanceof Date) {
      date = value;
    } else if (typeof value === 'number') {
      const d = new Date(value);
      if (!isNaN(d.getTime())) date = d;
    } else if (typeof value === 'string') {
      const ts = Date.parse(value);
      if (!isNaN(ts)) date = new Date(ts);
    }
    if (date) {
      const y = date.getFullYear();
      const m = String(date.getMonth() + 1).padStart(2, '0');
      const d = String(date.getDate()).padStart(2, '0');
      if (this.element) this.element.value = `${y}-${m}-${d}`;
    } else {
      if (this.element) this.element.value = '';
    }
  }
  getValue() {
    const val = this.element?.value;
    return (val ? new Date(val).getTime() : null) as any;
  }
}

// 自定义日期时间编辑器（日期+时间，支持 input type=datetime-local 格式转换）
class DateTimeEditor extends InputEditor {
  editorType = 'DateTime';
  createElement() {
    const input = document.createElement('input');
    input.setAttribute('type', 'datetime-local');
    input.style.padding = '4px';
    input.style.width = '100%';
    input.style.boxSizing = 'border-box';
    input.style.position = 'absolute';
    input.style.backgroundColor = '#FFFFFF';
    input.style.borderRadius = '0px';
    input.style.border = '2px solid #d9d9d9';
    input.addEventListener('focus', () => {
      input.style.borderColor = '#4A90E2';
      input.style.outline = 'none';
    });
    input.addEventListener('blur', () => {
      input.style.borderColor = '#d9d9d9';
    });
    this.element = input;
    this.container.appendChild(input);
    input.addEventListener('keydown', (e: KeyboardEvent) => {
      if (e.key === 'a' && (e.ctrlKey || e.metaKey)) e.stopPropagation();
    });
    input.addEventListener('wheel', (e: Event) => { e.preventDefault(); });
  }
  setValue(value: any) {
    let date: Date | null = null;
    if (value instanceof Date) {
      date = value;
    } else if (typeof value === 'number') {
      const d = new Date(value);
      if (!isNaN(d.getTime())) date = d;
    } else if (typeof value === 'string') {
      const ts = Date.parse(value);
      if (!isNaN(ts)) date = new Date(ts);
    }
    if (date) {
      const y = date.getFullYear();
      const m = String(date.getMonth() + 1).padStart(2, '0');
      const d = String(date.getDate()).padStart(2, '0');
      const h = String(date.getHours()).padStart(2, '0');
      const min = String(date.getMinutes()).padStart(2, '0');
      if (this.element) this.element.value = `${y}-${m}-${d}T${h}:${min}`;
    } else {
      if (this.element) this.element.value = '';
    }
  }
  getValue() {
    const val = this.element?.value;
    return (val ? new Date(val).getTime() : null) as any;
  }
}

registerVTable.editor('date-only', new DateOnlyEditor());
registerVTable.editor('date-time', new DateTimeEditor());

// 自定义多选编辑器（checkbox 下拉列表，支持多项选择和 Enter/外部点击退出）
class MultiSelectEditor implements IEditor {
  editorType = 'MultiSelect';
  container?: HTMLElement;
  element?: HTMLElement;
  editorConfig: { options: Array<{id: string, name: string, color?: string}> };
  successCallback?: () => void;
  selectedValues: string[] = [];

  constructor(editorConfig: { options: Array<{id: string, name: string, color?: string}> }) {
    this.editorConfig = editorConfig;
  }

  onStart({ container, value, referencePosition, endEdit }: EditContext) {
    this.container = container;
    this.successCallback = endEdit;
    const currentValue = String(value ?? '');
    // 兼容 JSON 数组格式和旧版逗号分隔格式
    let parsed: string[] = [];
    if (currentValue) {
      try { const p = JSON.parse(currentValue); if (Array.isArray(p)) parsed = p.map(v => String(v)); } catch {}
      if (parsed.length === 0) parsed = currentValue.split(', ').filter(Boolean);
    }
    this.selectedValues = parsed;
    this.createElement();
    if (referencePosition?.rect) this.adjustPosition(referencePosition.rect);
  }

  createElement() {
    const wrapper = document.createElement('div');
    wrapper.style.cssText = `
      position: absolute;
      background: #ffffff;
      border: 1px solid #d9d9d9;
      border-radius: 6px;
      box-shadow: 0 4px 16px rgba(0,0,0,0.15);
      z-index: 99999;
      max-height: 260px;
      overflow-y: auto;
      min-width: 160px;
      padding: 6px 0;
      box-sizing: border-box;
    `;

    const { options } = this.editorConfig;
    if (options && options.length > 0) {
      options.forEach(opt => wrapper.appendChild(this.createOptionItem(opt)));
    } else {
      const emptyHint = document.createElement('div');
      emptyHint.style.cssText = 'padding: 12px; color: #999; font-size: 12px; text-align: center;';
      emptyHint.textContent = '无可用选项';
      wrapper.appendChild(emptyHint);
    }

    // Enter 键确认
    const keydownHandler = (e: KeyboardEvent) => {
      if (e.key === 'Enter') {
        document.removeEventListener('keydown', keydownHandler);
        this.successCallback?.();
      }
    };
    wrapper.addEventListener('keydown', keydownHandler);

    // 点击外部退出
    const outsideHandler = (e: MouseEvent) => {
      if (wrapper && !wrapper.contains(e.target as Node)) {
        document.removeEventListener('mousedown', outsideHandler, true);
        setTimeout(() => {
          try {
            this.successCallback?.();
          } catch (err) {
            console.warn('Editor exit error:', err);
          }
        }, 0);
      }
    };
    setTimeout(() => document.addEventListener('mousedown', outsideHandler, true), 0);

    this.element = wrapper;
    this.container?.appendChild(wrapper);
  }

  private createOptionItem(opt: {id: string, name: string, color?: string}): HTMLElement {
    const color = opt.color || '#6B7280';
    const isChecked = this.selectedValues.includes(opt.name);

    const item = document.createElement('label');
    item.style.cssText = `
      display: flex;
      align-items: center;
      padding: 6px 14px;
      cursor: pointer;
      font-size: 13px;
      transition: background-color 0.15s;
    `;
    item.addEventListener('mouseenter', () => { item.style.backgroundColor = '#f5f7fa'; });
    item.addEventListener('mouseleave', () => { item.style.backgroundColor = ''; });

    const checkbox = document.createElement('input');
    checkbox.type = 'checkbox';
    checkbox.value = opt.name;
    checkbox.checked = isChecked;
    checkbox.style.cssText = 'margin-right: 10px; cursor: pointer; accent-color: #409eff; flex-shrink: 0;';
    checkbox.addEventListener('change', () => {
      if (checkbox.checked) {
        if (!this.selectedValues.includes(opt.name)) this.selectedValues.push(opt.name);
      } else {
        this.selectedValues = this.selectedValues.filter(v => v !== opt.name);
      }
    });

    // 彩色标签样式，与单元格 customLayout 一致
    const tag = document.createElement('span');
    tag.textContent = opt.name;
    tag.title = opt.name; // 长文本截断时显示完整内容
    tag.style.cssText = `
      display: inline-flex;
      align-items: center;
      background-color: ${color};
      color: white;
      padding: 2px 10px;
      border-radius: 12px;
      font-size: 12px;
      line-height: 1.6;
      white-space: nowrap;
      user-select: none;
      max-width: 240px;
      overflow: hidden;
      text-overflow: ellipsis;
    `;

    item.appendChild(checkbox);
    item.appendChild(tag);
    return item;
  }

  adjustPosition(rect: RectProps) {
    if (!this.element) return;

    const dropdownHeight = this.element.offsetHeight || 260;
    const cellBottom = rect.top + (rect.height || 40);
    const offsetParent = this.element.offsetParent as HTMLElement | null;
    const containerHeight = offsetParent?.clientHeight || window.innerHeight;

    let top: number;
    if (cellBottom + 4 + dropdownHeight > containerHeight) {
      top = Math.max(0, rect.top - dropdownHeight - 2);
    } else {
      top = rect.top - 1;
    }

    const left = rect.left - 1;
    const width = Math.max(rect.width + 2, 160);
    this.element.style.top = `${top}px`;
    this.element.style.left = `${left}px`;
    this.element.style.width = `${width}px`;
  }

  getValue() {
    return this.selectedValues.length > 0 ? JSON.stringify(this.selectedValues) : '';
  }

  onEnd() {
    if (this.element && this.element.parentNode) {
      this.element.parentNode.removeChild(this.element);
    }
    this.element = undefined;
  }

  isEditorElement(target: HTMLElement) {
    return this.element?.contains(target) ?? false;
  }
}

registerVTable.editor('multi-select', new MultiSelectEditor({ options: [] }));

// SingleSelectEditor - 单选编辑器（选择列表，支持清空已选内容）
// 每个选项以彩色标签样式渲染，与单元格内的显示风格一致
class SingleSelectEditor implements IEditor {
  editorType = 'SingleSelect';
  container?: HTMLElement;
  element?: HTMLElement;
  editorConfig: { options: Array<{id: string, name: string, color?: string}> };
  successCallback?: () => void;
  selectedValue: string | null = null;

  constructor(editorConfig: { options: Array<{id: string, name: string, color?: string}> }) {
    this.editorConfig = editorConfig;
  }

  onStart({ container, value, referencePosition, endEdit }: EditContext) {
    this.container = container;
    this.successCallback = endEdit;
    this.selectedValue = String(value ?? '') || null;
    this.createElement();
    if (referencePosition?.rect) this.adjustPosition(referencePosition.rect);
  }

  createElement() {
    const wrapper = document.createElement('div');
    wrapper.style.cssText = `
      position: absolute;
      background: #ffffff;
      border: 1px solid #d9d9d9;
      border-radius: 6px;
      box-shadow: 0 4px 16px rgba(0,0,0,0.15);
      z-index: 999999;
      max-height: 260px;
      overflow-y: auto;
      min-width: 160px;
      padding: 6px 0;
      box-sizing: border-box;
    `;

    const { options } = this.editorConfig;

    // 清空选项（置顶显示）
    wrapper.appendChild(this.createClearItem());

    // 选项列表：每个选项按彩色标签样式渲染
    if (options && options.length > 0) {
      options.forEach(opt => wrapper.appendChild(this.createOptionItem(opt)));
    } else {
      const emptyHint = document.createElement('div');
      emptyHint.style.cssText = 'padding: 12px; color: #999; font-size: 12px; text-align: center;';
      emptyHint.textContent = '无可用选项';
      wrapper.appendChild(emptyHint);
    }

    // 点击外部退出编辑
    const outsideHandler = (e: MouseEvent) => {
      if (wrapper && !wrapper.contains(e.target as Node)) {
        document.removeEventListener('mousedown', outsideHandler, true);
        setTimeout(() => {
          try {
            this.successCallback?.();
          } catch (err) {
            console.warn('Editor exit error:', err);
          }
        }, 0);
      }
    };
    setTimeout(() => document.addEventListener('mousedown', outsideHandler, true), 0);

    this.element = wrapper;
    this.container?.appendChild(wrapper);
  }

  adjustPosition(rect: RectProps) {
    if (!this.element) return;

    const dropdownHeight = this.element.offsetHeight || 260;
    const cellBottom = rect.top + (rect.height || 40);
    // offsetParent 是 VTable 容器（position: relative），其 clientHeight 为可见高度
    const offsetParent = this.element.offsetParent as HTMLElement | null;
    const containerHeight = offsetParent?.clientHeight || window.innerHeight;

    let top: number;
    // 如果单元格下方剩余空间不足以容纳下拉列表 → 向上弹出
    if (cellBottom + 4 + dropdownHeight > containerHeight) {
      top = Math.max(0, rect.top - dropdownHeight - 2);
    } else {
      top = rect.top - 1;
    }

    const left = rect.left - 1;
    const width = Math.max(rect.width + 2, 160);
    this.element.style.top = `${top}px`;
    this.element.style.left = `${left}px`;
    this.element.style.width = `${width}px`;
  }

  private createClearItem(): HTMLElement {
    const item = document.createElement('div');
    item.style.cssText = `
      display: flex;
      align-items: center;
      padding: 8px 14px;
      cursor: pointer;
      font-size: 13px;
      color: #999;
      border-bottom: 1px solid #f0f0f0;
      margin-bottom: 4px;
      transition: background-color 0.15s;
    `;
    item.addEventListener('mouseenter', () => { item.style.backgroundColor = '#fafafa'; });
    item.addEventListener('mouseleave', () => { item.style.backgroundColor = ''; });
    item.addEventListener('click', () => {
      this.selectedValue = null;
      try {
        this.successCallback?.();
      } catch (err) {
        console.warn('Editor exit error:', err);
      }
    });

    const icon = document.createElement('span');
    icon.textContent = '✕';
    icon.style.cssText = 'margin-right: 8px; font-size: 12px; color: #bbb;';
    item.appendChild(icon);
    item.appendChild(document.createTextNode('清空'));
    return item;
  }

  private createOptionItem(opt: {id: string, name: string, color?: string}): HTMLElement {
    const color = opt.color || '#6B7280';
    const isSelected = this.selectedValue === opt.name;

    const item = document.createElement('div');
    item.style.cssText = `
      display: flex;
      align-items: center;
      padding: 6px 14px;
      cursor: pointer;
      font-size: 13px;
      transition: background-color 0.15s;
    `;
    item.addEventListener('mouseenter', () => { item.style.backgroundColor = '#e5f7fa'; });
    item.addEventListener('mouseleave', () => { item.style.backgroundColor = ''; });
    item.addEventListener('click', () => {
      this.selectedValue = opt.name;
      try {
        this.successCallback?.();
      } catch (err) {
        console.warn('Editor exit error:', err);
      }
    });

    // 彩色标签样式，与单元格 customLayout 一致
    const tag = document.createElement('span');
    tag.title = opt.name; // 长文本截断时显示完整内容
    tag.style.cssText = `
      display: inline-flex;
      align-items: center;
      background-color: ${color};
      color: white;
      padding: 2px 10px;
      border-radius: 12px;
      font-size: 12px;
      line-height: 1.6;
      white-space: nowrap;
      user-select: none;
      max-width: 240px;
      overflow: hidden;
      text-overflow: ellipsis;
    `;

    // 已选中项显示 ✓ 标记
    if (isSelected) {
      const check = document.createElement('span');
      check.textContent = '✓ ';
      check.style.cssText = 'font-size: 11px; margin-right: 1px;';
      tag.appendChild(check);
    }

    tag.appendChild(document.createTextNode(opt.name));
    item.appendChild(tag);
    return item;
  }

  getValue() {
    return this.selectedValue ?? '';
  }

  onEnd() {
    if (this.element && this.element.parentNode) {
      this.element.parentNode.removeChild(this.element);
    }
    this.element = undefined;
  }

  isEditorElement(target: HTMLElement) {
    return this.element?.contains(target) ?? false;
  }
}

// TextAreaEditor - 多行文本编辑器（浮窗 textarea，5行高，可拖动调整大小）
class TextAreaEditor implements IEditor {
  editorType = 'TextArea';
  container?: HTMLElement;
  element?: HTMLElement;
  value: string = '';
  successCallback?: () => void;

  onStart({ container, value, referencePosition, endEdit }: EditContext) {
    this.container = container;
    this.successCallback = endEdit;
    this.value = String(value ?? '') || '';
    this.createElement();
    if (referencePosition?.rect) this.adjustPosition(referencePosition.rect);
  }

  createElement() {
    const wrapper = document.createElement('div');
    wrapper.style.cssText = `
      position: absolute;
      z-index: 99999;
      background: #fff;
      border: 1px solid #d9d9d9;
      border-radius: 8px;
      box-shadow: 0 6px 20px rgba(0,0,0,0.18);
      padding: 10px;
      box-sizing: border-box;
      min-width: 260px;
      min-height: 120px;
    `;

    const textarea = document.createElement('textarea');
    textarea.value = this.value;
    textarea.rows = 5;
    textarea.style.cssText = `
      width: 100%;
      height: 100%;
      border: 1px solid #d9d9d9;
      border-radius: 4px;
      padding: 8px 10px;
      font-size: 14px;
      line-height: 1.6;
      resize: both;
      box-sizing: border-box;
      outline: none;
      font-family: inherit;
    `;

    // 聚焦/失焦边框色
    textarea.addEventListener('focus', () => { textarea.style.borderColor = '#4A90E2'; });
    textarea.addEventListener('blur', () => { textarea.style.borderColor = '#d9d9d9'; });

    // 实时同步输入内容到 this.value，确保 VTable 调用 getValue() 时能拿到最新值
    textarea.addEventListener('input', () => {
      this.value = textarea.value;
    });

    // 键盘事件：
    //   - Ctrl+Enter / Cmd+Enter → 保存并退出编辑
    //   - 纯 Enter → 阻止冒泡，防止 VTable 拦截，让 textarea 正常换行
    textarea.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        if (e.ctrlKey || e.metaKey) {
          // Ctrl+Enter → 保存退出
          e.preventDefault();
          this.value = textarea.value;
          this.successCallback?.();
        } else {
          // 纯 Enter → 阻止 VTable 拦截，让 textarea 插入换行
          e.stopPropagation();
        }
      }
      if (e.key === 'Escape') {
        e.stopPropagation();
      }
    });

    wrapper.appendChild(textarea);
    this.element = wrapper;
    this.container?.appendChild(wrapper);

    // 自动聚焦
    setTimeout(() => textarea.focus(), 0);
  }

  adjustPosition(rect: RectProps) {
    if (!this.element) return;

    const popupHeight = 170;
    const cellBottom = rect.top + (rect.height || 40);
    const offsetParent = this.element.offsetParent as HTMLElement | null;
    const containerHeight = offsetParent?.clientHeight || window.innerHeight;

    let top: number;
    if (cellBottom + 4 + popupHeight > containerHeight) {
      top = Math.max(0, rect.top - popupHeight - 2);
    } else {
      top = rect.top - 1;
    }

    const left = rect.left - 1;
    const width = Math.max(rect.width + 2, 300);
    this.element.style.top = `${top}px`;
    this.element.style.left = `${left}px`;
    this.element.style.width = `${width}px`;
    this.element.style.height = `${popupHeight}px`;
  }

  getValue() {
    return this.value;
  }

  onEnd() {
    if (this.element && this.element.parentNode) {
      this.element.parentNode.removeChild(this.element);
    }
    this.element = undefined;
  }

  isEditorElement(target: HTMLElement) {
    return this.element?.contains(target) ?? false;
  }
}

// RichTextEditor - 富文本编辑器（浮窗弹出，集成 @opentiny/fluent-editor）
class RichTextEditor implements IEditor {
  editorType = 'RichText';
  container?: HTMLElement;
  element?: HTMLElement;
  editor: any = null;
  value: string = '';
  /** 用户是否有过操作（输入文本 / 格式变更），区分用户操作与 Quill API 加载 */
  dirty: boolean = false;
  successCallback?: () => void;

  onStart({ container, value, referencePosition, endEdit }: EditContext) {
    this.container = container;
    this.successCallback = endEdit;
    this.value = String(value ?? '') || '';
    this.dirty = false;
    this.createElement();
    if (referencePosition?.rect) this.adjustPosition(referencePosition.rect);
    this.initEditorAsync();
  }

  createElement() {
    const wrapper = document.createElement('div');
    wrapper.style.cssText = `
      position: absolute;
      z-index: 99999;
      background: #fff;
      border: 1px solid #d9d9d9;
      border-radius: 8px;
      box-shadow: 0 6px 20px rgba(0,0,0,0.18);
      padding: 0;
      box-sizing: border-box;
      overflow: hidden;
    `;

    const editorContainer = document.createElement('div');
    editorContainer.style.cssText = `
      min-height: 180px;
    `;
    editorContainer.className = 'rich-text-editor-container';
    wrapper.appendChild(editorContainer);

    this.element = wrapper;
    this.container?.appendChild(wrapper);
  }

  async initEditorAsync() {
    try {
      const { default: FluentEditor } = await import('@opentiny/fluent-editor');

      const editorContainer = this.element?.querySelector('.rich-text-editor-container');
      if (!editorContainer) return;

      this.editor = new FluentEditor(editorContainer as unknown as HTMLElement, {
        theme: 'snow',
        modules: {
          toolbar: [
            ['bold', 'italic', 'underline', 'strike'],
            [{ 'list': 'ordered' }, { 'list': 'bullet' }],
            ['clean'],
          ],
        },
      });

      // 加载已有内容（HTML → Delta）
      if (this.value) {
        const delta = this.editor.clipboard.convert({ html: this.value });
        this.editor.setContents(delta);
      }

      // 监听用户操作：source === 'user' 表示用户主动编辑（输入文本、加粗、列表等）
      // 设置 dirty 标记以在 getValue() 时区分"有改动"和"无改动"
      this.editor.on('text-change', (_delta: any, _oldDelta: any, source: string) => {
        if (source === 'user') {
          this.dirty = true;
        }
      });

      // 阻止 Enter 冒泡到 VTable，确保纯 Enter 只换行不退出编辑
      // 使用捕获阶段拦截，在 VTable 处理之前截断
      (this.editor.root as HTMLElement).addEventListener('keydown', (e: KeyboardEvent) => {
        if (e.key === 'Enter' && !e.ctrlKey && !e.metaKey) {
          e.stopPropagation();
        }
      }, true);
    } catch (e) {
      console.error('[RichTextEditor] 初始化失败:', e);
    }
  }

  adjustPosition(rect: RectProps) {
    if (!this.element) return;

    const popupHeight = 280;
    const cellBottom = rect.top + (rect.height || 40);
    const offsetParent = this.element.offsetParent as HTMLElement | null;
    const containerHeight = offsetParent?.clientHeight || window.innerHeight;

    let top: number;
    if (cellBottom + 4 + popupHeight > containerHeight) {
      top = Math.max(0, rect.top - popupHeight - 2);
    } else {
      top = rect.top - 1;
    }

    const left = rect.left - 1;
    const width = Math.max(rect.width + 2, 420);
    this.element.style.top = `${top}px`;
    this.element.style.left = `${left}px`;
    this.element.style.width = `${width}px`;
    this.element.style.height = `${popupHeight}px`;
  }

  getValue() {
    if (this.editor) {
      const html = (this.editor.root as HTMLElement).innerHTML;
      // Quill 空内容为 <p><br></p>，视为空
      if (html === '<p><br></p>' || html === '<br>') {
        return '';
      }

      // 用户无任何操作（输入文本/格式变更）→ 返回原始值，不触发保存
      if (!this.dirty) {
        return this.value;
      }

      // 用户有操作 → 返回编辑器的实际 HTML（含文本变更和格式变更如加粗/列表等）
      return html;
    }
    return this.value;
  }

  onEnd() {
    this.editor = null;
    if (this.element && this.element.parentNode) {
      this.element.parentNode.removeChild(this.element);
    }
    this.element = undefined;
  }

  isEditorElement(target: HTMLElement) {
    // 包含编辑器内部所有子元素（工具栏、编辑区域等）
    return this.element?.contains(target) ?? false;
  }
}

// RatingEditor - 评分编辑器（星星选择）
class RatingEditor implements IEditor {
  editorType = 'Rating';
  container?: HTMLElement;
  element?: HTMLElement;
  value: number = 0;
  successCallback?: () => void;

  onStart({ container, value, referencePosition, endEdit }: EditContext) {
    this.container = container;
    this.successCallback = endEdit;
    this.value = Number(value) || 0;
    this.createElement();
    if (referencePosition?.rect) this.adjustPosition(referencePosition.rect);
  }

  createElement() {
    const wrapper = document.createElement('div');
    wrapper.style.cssText = `
      display: flex;
      padding: 8px;
      gap: 4px;
      background: #fff;
    `;

    for (let i = 1; i <= 5; i++) {
      const star = document.createElement('span');
      star.textContent = '★';
      star.style.cssText = `
        cursor: pointer;
        font-size: 24px;
        color: ${this.value >= i ? '#F59E0B' : '#e5e7eb'};
        transition: transform 0.15s, color 0.15s;
        user-select: none;
      `;
      star.addEventListener('mouseenter', () => {
        star.style.transform = 'scale(1.2)';
      });
      star.addEventListener('mouseleave', () => {
        star.style.transform = 'scale(1)';
      });
      star.addEventListener('click', () => {
        this.value = i;
        this.successCallback?.();
      });
      wrapper.appendChild(star);
    }

    this.element = wrapper;
    this.container?.appendChild(wrapper);
  }

  adjustPosition(rect: RectProps) {
    if (!this.element) return;
    this.element.style.position = 'absolute';
    this.element.style.top = `${rect.top}px`;
    this.element.style.left = `${rect.left}px`;
    this.element.style.width = `${rect.width}px`;
  }

  getValue() {
    return this.value;
  }

  onEnd() {
    if (this.element && this.element.parentNode) {
      this.element.parentNode.removeChild(this.element);
    }
    this.element = undefined;
  }

  isEditorElement(target: HTMLElement) {
    return this.element?.contains(target) ?? false;
  }
}

// MemberEditor - 成员选择编辑器（带搜索、已选标签、选择即保存）
interface MemberInfo {
  id: string;
  name: string;
  email?: string;
  avatar?: string;
}

class MemberEditor implements IEditor {
  editorType = 'Member';
  container?: HTMLElement;
  element?: HTMLElement;
  editorConfig: {
    allowMultiple?: boolean;
    baseId?: string;
  };
  successCallback?: () => void;
  value?: unknown; // 原始值引用，用于 getValue() 中比较是否变化
  selectedIds: string[] = [];
  selectedMembers: MemberInfo[] = [];
  outsideHandler?: (e: MouseEvent) => void;
  searchTimer?: ReturnType<typeof setTimeout>;
  searchQuery = '';
  searchResults: MemberInfo[] = [];
  isLoading = false;

  // DOM 引用
  selectedTagsEl?: HTMLElement;
  searchInputEl?: HTMLInputElement;
  resultsListEl?: HTMLElement;

  constructor(editorConfig: {
    allowMultiple?: boolean;
    baseId?: string;
  }) {
    this.editorConfig = editorConfig;
  }

  onStart({ container, value, referencePosition, endEdit }: EditContext) {
    this.container = container;
    this.successCallback = endEdit;
    this.value = value; // 保存原始值引用，供 getValue() 比较
    this.selectedIds = this.extractMemberIds(value);
    this.loadSelectedMembers().then(() => {
      this.createElement();
      if (referencePosition?.rect) this.adjustPosition(referencePosition.rect);
      // 聚焦搜索框
      setTimeout(() => this.searchInputEl?.focus(), 50);
    });
  }

  extractMemberIds(value: unknown): string[] {
    if (!value) return [];
    if (Array.isArray(value)) {
      return value.map(v => typeof v === 'string' ? v : (v as any)?.id || '').filter(Boolean);
    }
    if (typeof value === 'string') {
      try { const p = JSON.parse(value); if (Array.isArray(p)) return p.map((v: any) => typeof v === 'string' ? v : v?.id || '').filter(Boolean); } catch {}
      return value ? [value] : [];
    }
    return [];
  }

  async loadSelectedMembers() {
    if (!userCacheStore || this.selectedIds.length === 0) {
      this.selectedMembers = [];
      return;
    }
    try {
      const users = await userCacheStore.fetchUsers(this.selectedIds);
      this.selectedMembers = users.map((u: any) => ({
        id: u.id,
        name: u.name || u.nickname || '未知',
        email: u.email,
        avatar: u.avatar,
      }));
    } catch {
      this.selectedMembers = this.selectedIds.map(id => ({ id, name: '未知成员' }));
    }
  }

  createElement() {
    const wrapper = document.createElement('div');
    wrapper.style.cssText = `
      position: absolute;
      background: #ffffff;
      border: 1px solid #dcdfe6;
      border-radius: 6px;
      box-shadow: 0 4px 20px rgba(0,0,0,0.12);
      z-index: 1000;
      width: 320px;
      max-height: 360px;
      overflow: hidden;
      display: flex;
      flex-direction: column;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      font-size: 13px;
    `;

    // ===== 已选成员标签区域 =====
    const tagsArea = document.createElement('div');
    tagsArea.style.cssText = `
      display: flex; flex-wrap: wrap; align-items: center;
      gap: 6px; padding: 10px 12px; border-bottom: 1px solid #ebeef5;
      min-height: 40px; max-height: 90px; overflow-y: auto;
    `;
    this.selectedTagsEl = tagsArea;
    this.renderSelectedTags();
    wrapper.appendChild(tagsArea);

    // ===== 搜索输入框 =====
    const searchBox = document.createElement('div');
    searchBox.style.cssText = 'padding: 8px 12px; border-bottom: 1px solid #ebeef5;';

    const searchInput = document.createElement('input');
    searchInput.type = 'text';
    searchInput.placeholder = '输入姓名或邮箱搜索';
    searchInput.style.cssText = `
      width: 100%; height: 32px; padding: 0 10px;
      border: 1px solid #dcdfe6; border-radius: 4px;
      font-size: 13px; outline: none; box-sizing: border-box;
    `;
    searchInput.addEventListener('focus', () => { searchInput.style.borderColor = '#409eff'; });
    searchInput.addEventListener('blur', () => { searchInput.style.borderColor = '#dcdfe6'; });
    searchInput.addEventListener('input', (e) => {
      const query = (e.target as HTMLInputElement).value;
      this.handleSearch(query);
    });
    searchInput.addEventListener('keydown', (e) => {
      if (e.key === 'Enter') {
        e.stopPropagation();
        if (!this.editorConfig.allowMultiple) {
          // 单选模式下 Enter 不保存（由点击触发）
        } else {
          // 多选模式下 Enter 保存并关闭
          this.successCallback?.();
        }
      } else if (e.key === 'Escape') {
        this.successCallback?.();
      }
    });
    this.searchInputEl = searchInput;
    searchBox.appendChild(searchInput);
    wrapper.appendChild(searchBox);

    // ===== 搜索结果列表 =====
    const resultsList = document.createElement('div');
    resultsList.style.cssText = `
      flex: 1; overflow-y: auto; min-height: 60px; padding: 4px 0;
    `;
    this.resultsListEl = resultsList;
    this.renderResults();
    wrapper.appendChild(resultsList);

    // ===== 底部提示（多选模式） =====
    if (this.editorConfig.allowMultiple) {
      const tip = document.createElement('div');
      tip.style.cssText = `
        padding: 6px 12px; font-size: 11px; color: #909399;
        text-align: center; border-top: 1px solid #ebeef5;
      `;
      tip.textContent = '点击外部或按 Enter 完成选择';
      wrapper.appendChild(tip);
    }

    // 点击外部保存
    this.outsideHandler = (e: MouseEvent) => {
      if (wrapper && !wrapper.contains(e.target as Node)) {
        document.removeEventListener('mousedown', this.outsideHandler!, true);
        setTimeout(() => this.successCallback?.(), 0);
      }
    };
    setTimeout(() => document.addEventListener('mousedown', this.outsideHandler!, true), 0);

    this.element = wrapper;
    this.container?.appendChild(wrapper);
  }

  // 渲染已选成员标签
  renderSelectedTags() {
    if (!this.selectedTagsEl) return;
    this.selectedTagsEl.innerHTML = '';

    if (this.selectedMembers.length === 0) {
      const placeholder = document.createElement('span');
      placeholder.style.cssText = 'color: #c0c4cc; font-size: 13px;';
      placeholder.textContent = '未选择成员';
      this.selectedTagsEl.appendChild(placeholder);
      return;
    }

    this.selectedMembers.forEach(member => {
      const tag = document.createElement('div');
      tag.style.cssText = `
        display: inline-flex; align-items: center; gap: 4px;
        padding: 2px 8px; background: #f5f7fa;
        border-radius: 4px; font-size: 12px;
        color: #303133; user-select: none;
      `;

      // 头像
      const avatar = document.createElement('div');
      const color = this.getAvatarColor(member.name);
      avatar.style.cssText = `
        width: 18px; height: 18px; border-radius: 50%;
        background-color: ${member.avatar ? 'transparent' : color};
        color: #fff; font-size: 9px; font-weight: 500;
        display: flex; align-items: center; justify-content: center;
        flex-shrink: 0; overflow: hidden;
      `;
      if (member.avatar) {
        const img = document.createElement('img');
        img.src = member.avatar;
        img.style.cssText = 'width: 100%; height: 100%; object-fit: cover;';
        avatar.appendChild(img);
      } else {
        avatar.textContent = (member.name || '?').charAt(0).toUpperCase();
      }

      const nameSpan = document.createElement('span');
      nameSpan.textContent = member.name;
      nameSpan.style.cssText = 'max-width: 80px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;';

      // 删除按钮
      const removeBtn = document.createElement('span');
      removeBtn.textContent = '×';
      removeBtn.style.cssText = `
        cursor: pointer; color: #909399; font-size: 14px;
        line-height: 1; padding: 0 2px; margin-left: 2px;
      `;
      removeBtn.addEventListener('mouseenter', () => { removeBtn.style.color = '#f56c6c'; });
      removeBtn.addEventListener('mouseleave', () => { removeBtn.style.color = '#909399'; });
      removeBtn.addEventListener('click', (e) => {
        e.stopPropagation();
        this.removeMember(member.id);
      });

      tag.appendChild(avatar);
      tag.appendChild(nameSpan);
      tag.appendChild(removeBtn);
      this.selectedTagsEl!.appendChild(tag);
    });
  }

  // 渲染搜索结果
  renderResults() {
    if (!this.resultsListEl) return;
    this.resultsListEl.innerHTML = '';

    if (this.isLoading) {
      const loadingEl = document.createElement('div');
      loadingEl.style.cssText = `
        display: flex; align-items: center; justify-content: center;
        gap: 8px; padding: 24px; color: #909399; font-size: 13px;
      `;
      loadingEl.textContent = '搜索中...';
      this.resultsListEl.appendChild(loadingEl);
      return;
    }

    if (!this.searchQuery.trim()) {
      const emptyEl = document.createElement('div');
      emptyEl.style.cssText = `
        display: flex; flex-direction: column; align-items: center;
        justify-content: center; gap: 8px; padding: 32px 16px;
        color: #909399; font-size: 13px;
      `;
      emptyEl.innerHTML = `
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="opacity:0.5">
          <circle cx="11" cy="11" r="8"></circle>
          <path d="m21 21-4.35-4.35"></path>
        </svg>
        <span>请输入关键词搜索</span>
      `;
      this.resultsListEl.appendChild(emptyEl);
      return;
    }

    if (this.searchResults.length === 0) {
      const emptyEl = document.createElement('div');
      emptyEl.style.cssText = `
        display: flex; flex-direction: column; align-items: center;
        justify-content: center; gap: 8px; padding: 32px 16px;
        color: #909399; font-size: 13px;
      `;
      emptyEl.innerHTML = `
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="opacity:0.5">
          <circle cx="11" cy="11" r="8"></circle>
          <path d="m21 21-4.35-4.35"></path>
        </svg>
        <span>未找到匹配的成员</span>
      `;
      this.resultsListEl.appendChild(emptyEl);
      return;
    }

    this.searchResults.forEach(member => {
      const isSelected = this.selectedIds.includes(member.id);
      const row = document.createElement('div');
      row.style.cssText = `
        display: flex; align-items: center; gap: 10px;
        padding: 10px 12px; cursor: pointer;
        transition: background-color 0.15s;
        ${isSelected ? 'background-color: rgba(64,158,255,0.08);' : ''}
      `;

      // 头像
      const avatar = document.createElement('div');
      const color = this.getAvatarColor(member.name);
      avatar.style.cssText = `
        width: 28px; height: 28px; border-radius: 50%;
        background-color: ${member.avatar ? 'transparent' : color};
        color: #fff; font-size: 11px; font-weight: 600;
        display: flex; align-items: center; justify-content: center;
        flex-shrink: 0; overflow: hidden;
      `;
      if (member.avatar) {
        const img = document.createElement('img');
        img.src = member.avatar;
        img.style.cssText = 'width: 100%; height: 100%; object-fit: cover;';
        avatar.appendChild(img);
      } else {
        avatar.textContent = this.getInitials(member.name);
      }

      // 信息区域
      const info = document.createElement('div');
      info.style.cssText = 'flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px;';

      const nameDiv = document.createElement('div');
      nameDiv.textContent = member.name;
      nameDiv.style.cssText = 'font-size: 13px; color: #303133; font-weight: 500; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;';

      const emailDiv = document.createElement('div');
      emailDiv.textContent = member.email || '';
      emailDiv.style.cssText = 'font-size: 11px; color: #909399; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;';

      info.appendChild(nameDiv);
      if (member.email) info.appendChild(emailDiv);

      // 勾选标记
      const checkMark = document.createElement('span');
      checkMark.textContent = '✓';
      checkMark.style.cssText = `
        color: #409eff; font-size: 16px; font-weight: bold;
        width: 20px; text-align: center; flex-shrink: 0;
        opacity: ${isSelected ? '1' : '0'}; transition: opacity 0.15s;
      `;

      row.appendChild(avatar);
      row.appendChild(info);
      row.appendChild(checkMark);

      row.addEventListener('mouseenter', () => { if (!isSelected) row.style.backgroundColor = '#f5f7fa'; });
      row.addEventListener('mouseleave', () => { if (!isSelected) row.style.backgroundColor = ''; });

      row.addEventListener('click', () => {
        this.toggleMember(member);
      });

      this.resultsListEl!.appendChild(row);
    });
  }

  // 搜索处理（防抖 300ms）
  handleSearch(query: string) {
    this.searchQuery = query;
    if (this.searchTimer) clearTimeout(this.searchTimer);

    if (!query.trim()) {
      this.searchResults = [];
      this.isLoading = false;
      this.renderResults();
      return;
    }

    this.isLoading = true;
    this.renderResults();

    this.searchTimer = setTimeout(async () => {
      try {
        const response = await userApi.searchUsers({
          query: query.trim(),
          per_page: 20,
        });
        this.searchResults = response.users.map((u: any) => ({
          id: u.id,
          name: u.name || u.nickname || '未知',
          email: u.email,
          avatar: u.avatar,
        }));
      } catch (error) {
        console.error('[MemberEditor] 搜索用户失败:', error);
        this.searchResults = [];
      } finally {
        this.isLoading = false;
        this.renderResults();
      }
    }, 300);
  }

  // 选择/取消选择成员
  toggleMember(member: MemberInfo) {
    const { allowMultiple = false } = this.editorConfig;

    // 缓存成员信息到 userCacheStore，确保保存后 transformRecords 能解析到名称
    if (userCacheStore && member.name) {
      userCacheStore.cacheUser({
        id: member.id,
        name: member.name,
        email: member.email || '',
        avatar: member.avatar,
      });
    }

    if (allowMultiple) {
      // 多选：切换选择状态
      if (this.selectedIds.includes(member.id)) {
        this.selectedIds = this.selectedIds.filter(id => id !== member.id);
        this.selectedMembers = this.selectedMembers.filter(m => m.id !== member.id);
      } else {
        this.selectedIds.push(member.id);
        this.selectedMembers.push(member);
      }
      this.renderSelectedTags();
      this.renderResults();
    } else {
      // 单选：直接选中并保存
      this.selectedIds = [member.id];
      this.selectedMembers = [member];
      this.successCallback?.();
    }
  }

  // 移除已选成员（通过标签上的 x 按钮）
  removeMember(memberId: string) {
    this.selectedIds = this.selectedIds.filter(id => id !== memberId);
    this.selectedMembers = this.selectedMembers.filter(m => m.id !== memberId);
    this.renderSelectedTags();
    this.renderResults();
  }

  getAvatarColor(name: string): string {
    const colors = ['#409eff', '#67c23a', '#e6a23c', '#f56c6c', '#909399', '#8e44ad', '#16a085', '#d35400'];
    let hash = 0;
    for (let i = 0; i < (name || '').length; i++) hash = name.charCodeAt(i) + ((hash << 5) - hash);
    return colors[Math.abs(hash) % colors.length];
  }

  getInitials(name: string): string {
    if (!name) return '?';
    return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2);
  }

  adjustPosition(rect: RectProps) {
    if (!this.element) return;

    const popupHeight = this.element.offsetHeight || 300;
    const cellBottom = rect.top + (rect.height || 40);
    const offsetParent = this.element.offsetParent as HTMLElement | null;
    const containerHeight = offsetParent?.clientHeight || window.innerHeight;

    let top: number;
    // 如果单元格下方剩余空间不足以容纳浮窗 → 向上弹出
    if (cellBottom + 4 + popupHeight > containerHeight) {
      top = Math.max(0, rect.top - popupHeight - 2);
    } else {
      top = rect.top - 1;
    }

    this.element.style.top = `${top}px`;
    this.element.style.left = `${rect.left - 1}px`;
    this.element.style.width = '320px';
  }

  getValue() {
    const original = this.value;

    // 提取原始值中的成员 ID 列表（支持字符串 JSON、数组、null 等多种格式）
    let originalIds: string[] = [];
    if (typeof original === 'string' && original) {
      try {
        const parsed = JSON.parse(original);
        if (Array.isArray(parsed)) {
          originalIds = parsed.map((m: any) => typeof m === 'string' ? m : m?.id || '').filter(Boolean);
        }
      } catch {
        // 不是 JSON，视为单个 ID
        originalIds = [original];
      }
    } else if (Array.isArray(original)) {
      originalIds = original.map((v: any) => typeof v === 'string' ? v : v?.id || '').filter(Boolean);
    }

    // 如果成员 ID 列表完全一致，返回原始值引用
    // 这样 VTable 的 === 比较会认为值无变化，不会用 ID 数组覆盖单元格显示
    if (originalIds.length === this.selectedIds.length &&
        originalIds.every((id, i) => id === this.selectedIds[i])) {
      return original;
    }

    return this.selectedIds;
  }

  onEnd() {
    if (this.searchTimer) clearTimeout(this.searchTimer);
    if (this.outsideHandler) {
      document.removeEventListener('mousedown', this.outsideHandler, true);
      this.outsideHandler = undefined;
    }
    if (this.element && this.element.parentNode) {
      this.element.parentNode.removeChild(this.element);
    }
    this.element = undefined;
  }

  isEditorElement(target: HTMLElement) {
    return this.element?.contains(target) ?? false;
  }
}

registerVTable.editor('text-area', new TextAreaEditor());
registerVTable.editor('rating', new RatingEditor());

const selectedRows = ref<string[]>([]);
const checkboxSelectedRows = ref<string[]>([]);

// 合并行选择与复选框选择，作为右键菜单“删除选中记录”的计数/操作依据
const selectedRecordIds = computed(() => {
  const recordIdSet = new Set<string>();
  selectedRows.value.forEach(id => { if (id) recordIdSet.add(id); });
  checkboxSelectedRows.value.forEach(id => { if (id) recordIdSet.add(id); });
  return Array.from(recordIdSet);
});

const columnWidths = ref<Record<string, number>>({});
const frozenDataRowCount = ref<number>(0); // 冻结数据行数（用于响应式更新右键菜单状态）
const deleteLoading = ref(false);

// 右键菜单相关
const contextMenuVisible = ref(false);
const contextMenuX = ref(0);
const contextMenuY = ref(0);
const contextMenuColumn = ref<FieldEntity | null>(null);
const contextMenuTarget = ref<"row" | "header" | "cell">("cell");
const contextMenuRecord = ref<RecordEntity | null>(null);
const contextMenuRow = ref<number>(-1); // 右键点击的行号（VTable 内部行索引）

// 字段属性对话框相关
const fieldDialogVisible = ref(false);
const editingFieldId = ref<string | null>(null);

// 记录详情对话框相关
const expandDialogVisible = ref(false);
const expandedRecord = ref<RecordEntity | null>(null);
// 抽屉展示的字段列表：主表记录用主表字段，子表记录用子表（目标表）字段
// 默认使用主表字段；点击子表放大按钮时切换为子表字段
const expandedFields = ref<FieldEntity[]>([]);
// 抽屉对应的表格 ID（用于保存等后端调用）
const expandedTableId = ref<string>('');

// 选中单元格相关 - 用于显示悬浮图标
const selectedCell = ref<{col: number, row: number, record: any, x: number, y: number} | null>(null);
const actionIconVisible = ref(false);

// URL 字段点击导航定时器（延时区分单击和双击）
let urlClickTimer: ReturnType<typeof setTimeout> | null = null;

// Drawer 抽屉大小（响应式）
const drawerSize = computed(() => {
  const width = window.innerWidth;
  if (width < 768) return "100%";
  if (width < 1024) return "70%";
  if (width < 1440) return "50%";
  return "600px";
});

// 获取列宽本地存储键（按表格+视图隔离，避免不同视图互相覆盖）
const getColumnWidthsStorageKey = () => {
  return `columnWidths_${props.tableId || 'default'}_${props.viewId || 'default'}`;
};

// 从 localStorage 恢复列宽
const initColumnWidths = () => {
  try {
    const key = getColumnWidthsStorageKey();
    const saved = localStorage.getItem(key);
    console.log(`[VTableView] 恢复列宽 key=${key}, saved=${saved}`);
    if (saved) {
      const parsed = JSON.parse(saved);
      if (parsed && typeof parsed === 'object' && !Array.isArray(parsed)) {
        // 只保留字段 ID -> number 的有效映射
        const valid: Record<string, number> = {};
        for (const [key, value] of Object.entries(parsed)) {
          if (typeof value === 'number' && value > 0) {
            valid[key] = value;
          }
        }
        columnWidths.value = valid;
        console.log('[VTableView] 已恢复列宽映射:', valid);
      } else {
        columnWidths.value = {};
      }
    } else {
      columnWidths.value = {};
    }
  } catch (e) {
    console.warn('[VTableView] 恢复列宽失败:', e);
    columnWidths.value = {};
  }
};

// 保存列宽到 localStorage
const saveColumnWidths = () => {
  try {
    const key = getColumnWidthsStorageKey();
    localStorage.setItem(
      key,
      JSON.stringify(columnWidths.value)
    );
    console.log(`[VTableView] 列宽已保存 key=${key}:`, columnWidths.value);
  } catch (e) {
    console.warn('[VTableView] 保存列宽失败:', e);
  }
};

// 将已缓存的列宽应用到 VTable 实例
const applyColumnWidths = () => {
  if (!tableInstance) return;

  const tableAny = tableInstance as any;
  const widths = { ...columnWidths.value };
  console.log('[VTableView] 开始应用列宽:', widths);
  orderedVisibleFields.value.forEach((field, index) => {
    const savedWidth = widths[field.id];
    if (savedWidth && typeof savedWidth === 'number') {
      const colIndex = index + 1; // 第 0 列为行号列
      try {
        const targetWidth = Math.max(60, savedWidth);
        console.log(`[VTableView] 应用列宽 col=${colIndex}, field=${field.id}, width=${targetWidth}`);
        tableAny.setColWidth(colIndex, targetWidth);
        // 部分场景下 setColWidth 不会立即生效，通过 _setColWidth 再写入一次
        if (typeof tableAny._setColWidth === 'function') {
          tableAny._setColWidth(colIndex, targetWidth, true, true);
        }
      } catch (e) {
        console.warn(`[VTableView] 应用列宽失败 col=${colIndex}:`, e);
      }
    }
  });
};

// 构建右键菜单
const contextMenuItems = computed(() => {
  const items: Array<{
    id: string;
    label: string;
    icon?: string;
    hint?: string;
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

    // 冻结行功能 - 使用响应式变量 frozenDataRowCount 确保菜单状态实时更新
    const tableInstanceAny = tableInstance as any;
    const headerRowCount = tableInstanceAny?.headerRowCount ?? 1;
    // 使用响应式变量进行判断（Vue computed 会自动追踪变化）
    const frozenDataRows = frozenDataRowCount.value;
    // 当前数据行索引（从 0 开始）
    const currentDataRow = contextMenuRow.value - headerRowCount;
    // 当前行是否在冻结区（使用响应式变量判断）
    const isFrozen = frozenDataRows > 0 && currentDataRow >= 0 && currentDataRow < frozenDataRows;

    // 根据状态显示不同的菜单项
    if (isFrozen) {
      // 当前行在冻结区 → 显示取消冻结
      items.push({
        id: 'unfreeze-row',
        label: '取消冻结行',
        icon: 'freeze',
        hint: '取消当前行的冻结状态',
        action: () => handleFreezeRow(true),
      });
    } else {
      // 当前行不在冻结区 → 显示冻结到此行
      const freezeCount = currentDataRow + 1;
      items.push({
        id: 'freeze-row',
        label: `冻结到此行（前 ${freezeCount} 行）`,
        icon: 'freeze',
        hint: '冻结当前行及其上方所有行，滚动时保持可见',
        action: () => handleFreezeRow(false, freezeCount),
      });
    }

    items.push({ divider: true, id: "divider-freeze", label: "" });

    // 树形视图操作
    if (isTreeView.value && !props.readonly) {
      items.push({
        id: "add-child-record",
        label: "添加子记录",
        icon: "circle-plus",
        hint: "在当前记录下创建一条子记录",
        action: () => {
          handleAddChildRecord();
        },
      });

      items.push({
        id: "promote",
        label: "提升层级",
        icon: "promote",
        hint: "将当前记录提升到上一层级（与父记录同级）",
        action: () => handlePromoteRecord(),
      });

      items.push({
        id: "demote",
        label: "降低层级",
        icon: "demote",
        hint: "将当前记录下降一个层级（挂到前一条记录下）",
        action: () => handleDemoteRecord(),
      });

      items.push({ divider: true, id: "divider-tree", label: "" });
    }

    if (!props.readonly) {
      items.push({ id: "edit", label: "编辑当前记录", icon: "edit", hint: "打开详情面板，编辑当前记录", action: () => handleEditRecord() });
      items.push({ id: "duplicate", label: "复制当前记录", icon: "copy", hint: "基于当前记录复制生成一条新记录", action: () => handleDuplicateRecord() });
      items.push({ divider: true, id: "divider1", label: "" });

      // 始终显示"删除当前记录"
      items.push({
        id: "delete",
        label: "删除当前记录",
        icon: "delete",
        danger: true,
        hint: "永久删除当前记录，此操作不可撤销",
        action: () => handleDeleteRecord(),
      });

      // 只要有选中的记录（行选择或复选框选择），就显示"删除选中的x条记录"
      const selectedCount = selectedRecordIds.value.length;
      if (selectedCount >= 1) {
        items.push({
          id: "delete-selected",
          label: `删除选中的 ${selectedCount} 条记录`,
          icon: "delete",
          danger: true,
          hint: `永久删除选中的 ${selectedCount} 条记录，此操作不可撤销`,
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
      hint: '按该字段从小到大升序排列记录',
      action: () => handleSort('asc'),
    });

    items.push({
      id: 'sort-desc',
      label: '降序排列',
      icon: 'sort',
      hint: '按该字段从大到小降序排列记录',
      action: () => handleSort('desc'),
    });

    if (currentSort) {
      items.push({
        id: 'sort-clear',
        label: '取消排序',
        hint: '取消该字段当前的排序',
        action: () => handleSort(null),
      });
    }

    items.push({ id: 'divider-1', divider: true, label: '' });

    // 冻结相关
    items.push({
      id: isFrozen ? 'unfreeze' : 'freeze',
      label: isFrozen ? '取消冻结' : '冻结列',
      icon: 'freeze',
      hint: isFrozen ? '取消该列的冻结状态' : '冻结该列及其左侧所有列，滚动时保持可见',
      action: () => handleFreeze(!isFrozen),
    });

    // 隐藏该列和字段属性需要 ADMIN 权限
    if (canManage.value) {
      items.push({
        id: 'hide',
        label: '隐藏该列',
        icon: 'hide',
        hint: '在视图中隐藏该列',
        action: () => handleHideColumn(),
      });

      items.push({ id: 'divider-2', divider: true, label: '' });

      // 字段属性
      items.push({
        id: 'field-settings',
        label: '字段属性',
        icon: 'settings',
        hint: '编辑该字段的属性配置',
        action: () => handleFieldSettings(),
      });
    }
  }

  return items;
});

// 处理排序（右键菜单触发）
// 与 sortClick 一致：同步应用层状态 + 让 VTable 内置排序通过自定义比较函数执行
const handleSort = async (direction: 'asc' | 'desc' | null) => {
  if (!currentView.value || !contextMenuColumn.value) return;

  const field = contextMenuColumn.value;
  const newSorts = direction ? [{ fieldId: field.id, direction }] : [];

  if (direction) {
    ElMessage.success(`已按 ${field.name} ${direction === 'asc' ? '升序' : '降序'}排列`);
  } else {
    ElMessage.success(`已取消 ${field.name} 的排序`);
  }

  // 同步应用层排序状态
  await viewStore.updateSorts(currentView.value.id, newSorts);

  // 通知 VTable 执行内置排序（使用自定义比较函数，addButton 行自动保持在末尾）
  if (tableInstance) {
    const vTableSortState = direction ? { field: field.id, order: direction } : null;
    (tableInstance as any).updateSortState(vTableSortState); // 默认 executeSort=true
  }

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

// 处理冻结行（数据行冻结）
const handleFreezeRow = (isFrozen: boolean, freezeCount?: number) => {
  if (!tableInstance) return;

  const tableInstanceAny = tableInstance as any;
  const headerRowCount = tableInstanceAny.headerRowCount ?? 1;

  // 计算新的冻结行数
  let newFrozenRowCount: number;
  if (isFrozen) {
    // 取消冻结行：只保留表头冻结
    newFrozenRowCount = headerRowCount;
    // 更新响应式变量（取消冻结，数据行冻结数变为 0）
    frozenDataRowCount.value = 0;
    ElMessage.success('已取消冻结行');
  } else {
    // 冻结行：表头行数 + 数据行数
    newFrozenRowCount = headerRowCount + (freezeCount ?? 1);
    // 更新响应式变量（冻结指定数据行数）
    frozenDataRowCount.value = freezeCount ?? 1;
    ElMessage.success(`已冻结前 ${freezeCount ?? 1} 行`);
  }

  // 同时更新配置和内部状态，确保状态一致性
  tableInstanceAny.frozenRowCount = newFrozenRowCount;
  if (tableInstanceAny.internalProps) {
    tableInstanceAny.internalProps.frozenRowCount = newFrozenRowCount;
  }

  // 刷新表格渲染
  tableInstanceAny.renderWithRecreateCells();
  contextMenuVisible.value = false;
};

// 处理隐藏列
const handleHideColumn = async () => {
  if (!currentView.value || !contextMenuColumn.value) return;

  const field = contextMenuColumn.value;

  // 索引列（主键字段）不允许隐藏
  if (field.isPrimary === true) {
    ElMessage.warning('索引列，用来标识每条记录。不能被删除、移动或隐藏。');
    contextMenuVisible.value = false;
    return;
  }

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

// 处理字段创建
const handleFieldCreated = async (field: any) => {
  if (!tableStore.fields.find((f) => f.id === field.id)) {
    tableStore.fields.push(field);
  }
  // 清除关联缓存并刷新记录，确保新增字段立即生效
  if (props.tableId) {
    linkApiService.clearCache();
    await tableStore.refreshRecords(props.tableId);
  }
};

// 处理字段更新
const handleFieldUpdated = async (field: any) => {
  const index = tableStore.fields.findIndex((f) => f.id === field.id);
  if (index !== -1) {
    Object.assign(tableStore.fields[index], field);
  }
  // 清除关联缓存并刷新记录，确保字段更新后关联数据显示正确
  if (props.tableId) {
    linkApiService.clearCache();
    await tableStore.refreshRecords(props.tableId);
  }
};

// 处理字段删除
const handleFieldDeleted = (fieldId: string) => {
  const index = tableStore.fields.findIndex((f) => f.id === fieldId);
  if (index !== -1) {
    tableStore.fields.splice(index, 1);
  }
};

// 处理字段重排序
const handleFieldsReordered = (fieldIds: string[]) => {
  const sortedFields = fieldIds
    .map((id) => tableStore.fields.find((f) => f.id === id))
    .filter((f): f is FieldEntity => f !== undefined);

  sortedFields.forEach((field, index) => {
    field.order = index;
  });

  tableStore.fields = sortedFields;
};

// 处理字段可见性变化（视图级隐藏/显示）
const handleFieldVisibilityChanged = async (fieldId: string, isVisible: boolean) => {
  if (!viewStore.currentView) return;

  const newHiddenFields = isVisible
    ? viewStore.currentView.hiddenFields.filter((id) => id !== fieldId)
    : [...viewStore.currentView.hiddenFields, fieldId];

  await viewStore.updateHiddenFields(viewStore.currentView.id, newHiddenFields);
};

// 处理放大按钮点击 - 打开记录详情
const handleExpandRecord = (record: RecordEntity) => {
  expandedRecord.value = record;
  // 主表记录使用主表字段和主表 ID
  expandedFields.value = tableStore.fields;
  expandedTableId.value = props.tableId;
  expandDialogVisible.value = true;
};

/**
 * 处理子表记录的放大按钮点击 - 打开记录详情抽屉
 * 与主表不同：需使用子表（目标表）的字段和 table ID
 */
const handleSubTableExpandRecord = async (cellRecord: any) => {
  if (!cellRecord) return;
  const original = cellRecord._originalRecord;
  if (!original) return;

  // 获取当前关联字段对应的目标表 ID
  const fieldId = currentLinkFieldId.value;
  if (!fieldId) return;
  const linkField = masterDetailLinkFields.value.find((f: any) => f.fieldId === fieldId);
  if (!linkField) return;
  const targetTableId = linkField.targetTableId;
  if (!targetTableId) return;

  // 获取子表字段定义
  let subFields: any[] = [];
  try {
    subFields = await masterDetailService.getTargetTableFields(targetTableId);
  } catch (e) {
    console.warn('[VTableView] 获取子表字段定义失败:', e);
  }

  // 后端返回的 LinkedRecordDetail 字段为 snake_case（created_at/updated_at），
  // 需转换为 RecordEntity 期望的 camelCase
  const recordEntity: RecordEntity = {
    id: original.id,
    tableId: targetTableId,
    values: { ...original.values },
    createdAt: original.created_at ? new Date(original.created_at).getTime() : Date.now(),
    updatedAt: original.updated_at ? new Date(original.updated_at).getTime() : Date.now(),
  };

  expandedRecord.value = recordEntity;
  expandedFields.value = subFields as FieldEntity[];
  expandedTableId.value = targetTableId;
  expandDialogVisible.value = true;
};

// 处理编辑记录
const handleEditRecord = () => {
  if (!contextMenuRecord.value) return;
  handleExpandRecord(contextMenuRecord.value);
  contextMenuVisible.value = false;
};

// 在表格末尾添加一条新记录（非分组模式「+ 添加记录」按钮点击逻辑）
// 实现策略：
// - 通过 API 创建记录后，直接追加到 store，由 watcher 统一触发 updateTableData 完成渲染
// - 这样避免了直接操作 CachedDataSource.length 导致的兼容性问题（CachedDataSource 的 length
//   在构造后不可变，appendRecords 的 Object.defineProperty 无法可靠同步），
//   同时 watcher 路径已确保 addButton 行始终追加在数据末尾（见 updateTableData）
let isAddingRecord = false;
let addRecordCooldownTimer: ReturnType<typeof setTimeout> | null = null;

// 防止 change_cell_value 事件重复处理
let processingCellKey: string | null = null;
let processingCellTimer: ReturnType<typeof setTimeout> | null = null;

const handleAddNewRecord = async () => {
  if (!props.tableId || isAddingRecord) return;
  isAddingRecord = true;
  if (addRecordCooldownTimer) {
    clearTimeout(addRecordCooldownTimer);
    addRecordCooldownTimer = null;
  }
  try {
    const newRecord = await recordService.createRecord({
      tableId: props.tableId,
      values: {},
    });
    if (!newRecord) return;

    // 不再手动更新 tableStore.records，让实时协作监听器（onRecordCreated）处理
    // 如果实时协作不可用，才手动添加
    const collabStore = useCollaborationStore();
    if (!collabStore.isRealtimeAvailable) {
      if (Array.isArray(tableStore.records)) {
        tableStore.records = [...tableStore.records, newRecord];
      }
    }

    emit('record-create');
    ElMessage.success('已添加新记录');
  } catch (error) {
    console.error('[VTableView] 添加记录失败:', error);
    ElMessage.error('添加记录失败');
  } finally {
    // 添加短暂冷却期，避免 VTable 事件重复触发导致一次点击添加多条记录
    addRecordCooldownTimer = setTimeout(() => {
      isAddingRecord = false;
      addRecordCooldownTimer = null;
    }, 300);
  }
};

// 处理复制记录
const handleDuplicateRecord = async () => {
  if (!contextMenuRecord.value) return;
  try {
    // 使用 tableStore.createRecord 创建记录（与删除逻辑保持一致）
    const newRecord = await tableStore.createRecord({
      tableId: contextMenuRecord.value.tableId,
      values: { ...contextMenuRecord.value.values },
    });
    if (newRecord) {
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

// 处理删除选中的记录 - 删除行选择或复选框勾选的记录
const handleDeleteSelectedRecords = async () => {
  const ids = [...selectedRecordIds.value];
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
    deleteLoading.value = true;
    try {
      await tableStore.batchDeleteRecords(ids);
      emit("record-delete", ids);
      selectedRows.value = selectedRows.value.filter(id => !ids.includes(id));
      checkboxSelectedRows.value = checkboxSelectedRows.value.filter(id => !ids.includes(id));
      ElMessage.success(`成功删除 ${count} 条记录`);
    } finally {
      deleteLoading.value = false;
    }
  } catch (error: any) {
    if (error !== "cancel") {
      console.error("删除记录失败:", error);
      ElMessage.error("删除记录失败");
    }
  }
  contextMenuVisible.value = false;
};

// 提升层级：将记录的父级设为祖父级（即上移一层）
const handlePromoteRecord = async () => {
  if (!contextMenuRecord.value || !parentFieldId.value) return;
  const record = contextMenuRecord.value;
  const currentParentIds = record.values?.[parentFieldId.value];
  if (!currentParentIds || !Array.isArray(currentParentIds) || currentParentIds.length === 0) {
    ElMessage.warning("该记录已经是顶层记录，无法提升层级");
    contextMenuVisible.value = false;
    return;
  }
  const currentParentId = currentParentIds[0];
  // 遍历树形记录，查找父记录的父级
  const findParent = (records: any[]): any => {
    for (const r of records) {
      if (r.id === currentParentId || r._recordId === currentParentId) {
        // 返回父记录，其 _originalRecord.values 包含父级字段值
        // 但我们实际上需要父记录自身的 values，所以用 _originalRecord
        return r._originalRecord || r;
      }
      if (r.children && Array.isArray(r.children)) {
        const found = findParent(r.children);
        if (found) return found;
      }
    }
    return null;
  };
  const parentRecord = findParent(treeRecords.value);
  if (!parentRecord || !parentRecord.values) {
    ElMessage.warning("无法找到父记录");
    contextMenuVisible.value = false;
    return;
  }
  const grandParentIds = parentRecord.values[parentFieldId.value];
  const newParentId = (Array.isArray(grandParentIds) && grandParentIds.length > 0) ? grandParentIds[0] : null;
  try {
    await recordService.updateRecord(record.id, {
      values: { [parentFieldId.value]: newParentId ? [newParentId] : [] },
    });
    await loadTreeRecords();
    ElMessage.success("已提升层级");
  } catch (error) {
    console.error("[VTableView] 提升层级失败:", error);
    ElMessage.error("提升层级失败");
  }
  contextMenuVisible.value = false;
};

// 降低层级：将记录设为上一个兄弟节点的子级（下移一层）
const handleDemoteRecord = async () => {
  if (!contextMenuRecord.value || !parentFieldId.value) return;
  ElMessage.info("降低层级功能正在开发中");
  contextMenuVisible.value = false;
};

// 处理添加子记录（树形视图）
const handleAddChildRecord = async () => {
  if (!contextMenuRecord.value || !parentFieldId.value) return;
  try {
    await recordApiService.createChildRecord(contextMenuRecord.value.id, parentFieldId.value);
    await loadTreeRecords();
    ElMessage.success("子记录已创建");
  } catch (error) {
    console.error("创建子记录失败:", error);
    ElMessage.error("创建子记录失败");
  }
  contextMenuVisible.value = false;
};

// 处理索引列 "+" 按钮点击（树形视图）
const handleTreeAddChildClick = async () => {
  if (!treeAddChildIcon.value || !parentFieldId.value) return;
  if (treeAddChildLoading.value) return;
  const recordId = treeAddChildIcon.value.recordId;
  clearHideTreeAddChildIconTimer();
  treeAddChildLoading.value = true;
  try {
    await recordApiService.createChildRecord(recordId, parentFieldId.value);
    await loadTreeRecords();
    ElMessage.success("子记录已创建");
  } catch (error) {
    console.error("创建子记录失败:", error);
    ElMessage.error("创建子记录失败");
  } finally {
    treeAddChildLoading.value = false;
    treeAddChildIconVisible.value = false;
    treeAddChildIcon.value = null;
  }
};

// 自动创建父字段（树形视图）
const autoCreateParentField = async () => {
  if (!viewStore.currentView?.id) return null;
  try {
    const result = await viewApiService.autoCreateParentField(viewStore.currentView.id);
    await viewStore.loadViews(viewStore.currentView.tableId);
    return result?.parent_field_id || null;
  } catch (error) {
    console.error("自动创建父字段失败:", error);
    return null;
  }
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
    // 判断保存的是主表记录还是子表记录
    // - 主表：expandedTableId === props.tableId，刷新主表记录列表
    // - 子表：expandedTableId 为目标表 ID，刷新对应子表（通过 linkApiService 清缓存 + 触发子表刷新）
    if (expandedTableId.value && expandedTableId.value !== props.tableId) {
      // 子表记录保存：清除关联缓存（关联显示值可能已变更）
      linkApiService.invalidateCacheByPattern('record_links:');
      // 若当前有展开的子表工具栏记录，触发子表数据刷新
      if (subTableToolbarRecordId.value && tableInstance) {
        await refreshSubTable(
          subTableToolbarRecordId.value,
          subTableToolbarCol.value,
          subTableToolbarRow.value,
          tableInstance,
        );
      }
    } else {
      // 主表记录保存：重新加载主表记录列表
      await tableStore.refreshRecords(tableStore.currentTable?.id || "");
      // 树形视图下重新构建树（详情页中修改父级字段后层级需要重排）
      if (isTreeView.value) {
        await loadTreeRecords();
      }
    }
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

/**
 * 数值型字段类型集合 —— 这些字段应按数值大小排序而非文本字典序
 */
const NUMERIC_FIELD_TYPES: Set<FieldTypeValue> = new Set([
  FieldType.NUMBER,
  FieldType.PROGRESS,
  FieldType.PERCENT,
  FieldType.RATING,
  FieldType.CURRENCY,
  // FieldType.AUTO_NUMBER,
  FieldType.DURATION,
]);

/**
 * 创建 VTable 列级自定义排序比较函数
 *
 * VTable 内置排序引擎对数据源（含 addButton 虚拟行）执行排序时，
 * 通过此函数确保：
 * 1. addButton 行始终排在末尾（值以 '__add_button_' 前缀标记）
 * 2. 数值型字段（number/progress/rating/currency 等）按数值大小排序
 * 3. 其他字段按文本字典序排序
 *
 * @param fieldType 字段类型，用于决定数值/文本比较策略
 * 函数签名与 VTable defaultOrderFn 一致：(v1, v2, order) => -1 | 0 | 1
 */
const ADD_BUTTON_PREFIX = '__add_button_';
const createSortComparator = (fieldType: FieldTypeValue | string): ((v1: any, v2: any, order: string) => number) => {
  const isNumeric = NUMERIC_FIELD_TYPES.has(fieldType as FieldTypeValue);

  return (v1: any, v2: any, order: string): number => {
    // addButton 虚拟行检测 —— 始终排到末尾
    const v1IsAdd = typeof v1 === 'string' && v1.startsWith(ADD_BUTTON_PREFIX);
    const v2IsAdd = typeof v2 === 'string' && v2.startsWith(ADD_BUTTON_PREFIX);
    if (v1IsAdd && v2IsAdd) return 0;
    if (v1IsAdd) return 1;
    if (v2IsAdd) return -1;

    // 根据字段类型选择比较策略
    if (isNumeric) {
      // 数值型字段：尝试解析为数字后比较，避免 "10" < "2" 的文本排序问题
      // null/undefined/空字符串视为 0（与 UI 显示一致：空进度显示为 0%）
      const n1 = v1 == null || v1 === '' ? 0 : Number(v1);
      const n2 = v2 == null || v2 === '' ? 0 : Number(v2);
      // 仍为 NaN（如纯文本 "abc"）则视为无效值，排到末尾
      if (isNaN(n1) && isNaN(n2)) return 0;
      if (isNaN(n1)) return 1;
      if (isNaN(n2)) return -1;
      if (order === 'desc') {
        return n1 === n2 ? 0 : n1 < n2 ? 1 : -1;
      }
      return n1 === n2 ? 0 : n1 > n2 ? 1 : -1;
    }

    // 文本型字段：使用默认排序逻辑（与 sortedRecords 应用层保持一致）
    if (order === 'desc') {
      return v1 === v2 ? 0 : v1 < v2 ? 1 : -1;
    }
    return v1 === v2 ? 0 : v1 > v2 ? 1 : -1;
  };
};
const fields = computed(() => tableStore.fields);
const currentView = computed(() => viewStore.currentView);

// 树形视图相关
const parentFieldId = computed(() => viewStore.currentView?.parentFieldId || null);
const isTreeView = computed(() => !!parentFieldId.value);
const treeRecords = ref<any[]>([]);
/** 组件是否已销毁（异步回调保护，避免卸载后仍触发加载） */
const isComponentDestroyed = ref(false);
/** 当前正在加载树形数据的视图 ID（防并发重复请求） */
let treeLoadingViewId = '';

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

// ==================== 记录转换工具函数 ====================
// 将原始 RecordEntity 转换为 VTable 需要的行数据格式
// 从 buildTableConfig 中提取，供流式加载增量更新复用
// 转换记录缓存：避免流式完成后全量重转换
// key: recordId, value: 转换后的行对象
const transformedCache = new Map<string, any>();

const transformRecords = (rawRecords: RecordEntity[]): any[] => {
  // 快速路径：所有记录已在缓存中，直接按原序返回
  if (rawRecords.length > 0 && rawRecords.every(r => r?.id && transformedCache.has(r.id))) {
    return rawRecords
      .map(r => transformedCache.get(r.id))
      .filter(Boolean) as any[];
  }

  const rows: any[] = [];
  const formulaFields = orderedVisibleFields.value.filter(f => f.type === FieldType.FORMULA);
  let formulaEngine: FormulaEngine | null = null;
  if (formulaFields.length > 0) {
    formulaEngine = new FormulaEngine(fields.value);
  }

  for (const record of rawRecords) {
    // 主从表懒加载标识：仅当存在 LINK 字段且至少有一个 LINK 字段存在关联记录时才设置 children: true
    // 无关联记录的行不显示展开按钮，避免展开后显示空白
    let hasLinkedRecords = false;
    if (hasLinkFields.value) {
      for (const lf of masterDetailLinkFields.value) {
        const rawVal = record?.values?.[lf.fieldId];
        if (Array.isArray(rawVal) && rawVal.length > 0) {
          hasLinkedRecords = true;
          break;
        }
      }
    }
    // 预设 hierarchyState: CachedDataSource 模式下 dataSource.records 在 initialized 事件时为空，
    // MasterDetailPlugin.processRecordsHierarchyStates 无法遍历到记录设置 hierarchyState，
    // 需在此预设 'collapse' 确保 VTable tree-helper 能识别并显示展开按钮
    const row: any = {
      _recordId: record?.id || '',
      _originalRecord: record,
      ...(hasLinkedRecords ? { children: true, hierarchyState: 'collapse' } : {}),
    };
    orderedVisibleFields.value.forEach(field => {
      if (!field?.id || !record?.values) return;
      const rawVal = record.values[field.id];
      
      switch (field.type) {
        case FieldType.SINGLE_SELECT: {
          const opts = (field.options?.choices || field.options?.options || []) as Array<{id: string, name: string, color?: string}>;
          const selId = typeof rawVal === 'object' && rawVal !== null ? String((rawVal as any).id || '') : String(rawVal || '');
          const found = opts.find(o => o.id === selId || o.name === selId);
          row[field.id] = found?.name || selId;
          break;
        }
        case FieldType.MULTI_SELECT: {
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
          let mems: any[] = [];
          if (Array.isArray(rawVal)) mems = rawVal;
          else if (typeof rawVal === 'string') try { const p = JSON.parse(rawVal); if (Array.isArray(p)) mems = p; } catch {}
          else if (typeof rawVal === 'object' && rawVal !== null) mems = [rawVal];
          const resolvedMembers = mems.map((m) => {
            let id = '';
            let name: string | undefined;
            if (typeof m === 'string') { id = m; }
            else if (typeof m === 'object' && m !== null) {
              id = String(m.user_id || m.id || '');
              name = m.name || undefined;
            } else { id = String(m); }
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
          if (!rawVal) { row[field.id] = ''; break; }
          if (Array.isArray(rawVal)) { row[field.id] = rawVal; break; }
          if (typeof rawVal === 'object' && rawVal !== null) {
            if ((rawVal as any).url) { row[field.id] = [rawVal]; break; }
            const arr = Object.values(rawVal);
            if (Array.isArray(arr)) { row[field.id] = arr; break; }
          }
          if (typeof rawVal === 'string') {
            try { const p = JSON.parse(rawVal); if (Array.isArray(p)) { row[field.id] = p; break; } } catch {}
            row[field.id] = rawVal; break;
          }
          row[field.id] = rawVal;
          break;
        }
        default:
          row[field.id] = rawVal;
      }
    });

    // 公式字段：逐条计算
    if (formulaEngine && formulaFields.length > 0) {
      formulaFields.forEach(field => {
        const formula = field.options?.formula as string;
        if (!formula) { row[field.id] = ''; return; }
        try {
          const result = formulaEngine!.calculate(record, formula);
          
          if (result === '#ERROR') {
            row[field.id] = '计算错误';
          } else if (typeof result === 'number') {
            // 根据公式类型决定格式化方式
            const resultType = FormulaEngine.inferResultType(formula);
            // 日期时间类型：YYYY-MM-DD HH:mm:ss
            if (resultType === "datetime") {
              row[field.id] = formatDateTime(result);
            }
            // 日期类型：YYYY-MM-DD
            else if (resultType === "date") {
              row[field.id] = formatDate(result);
            }
            // 数字类型：带精度格式化
            else {
              const precision = (field.options?.precision as number) ?? 2;
              row[field.id] = result.toLocaleString('zh-CN', {
                minimumFractionDigits: precision,
                maximumFractionDigits: precision,
              });
            }
          } else {
            row[field.id] = String(result);
          }
        } catch {
          row[field.id] = '计算错误';
        }
      });
    }

    rows.push(row);
  }

  // 更新缓存（仅全量处理路径，增量路径已在快速路径命中）
  for (const row of rows) {
    if (row._recordId) {
      transformedCache.set(row._recordId, row);
    }
  }

  return rows;
};

/** 清除转换缓存（用户缓存变更、公式变更等场景需强制重转换） */
const clearTransformCache = (): void => {
  transformedCache.clear();
};

/** 转换树形记录为 VTable 分层格式 */
const transformTreeRecords = (records: any[], depth: number = 0): any[] => {
  const formulaFields = orderedVisibleFields.value.filter(f => f.type === FieldType.FORMULA);
  let formulaEngine: FormulaEngine | null = null;
  if (formulaFields.length > 0) {
    formulaEngine = new FormulaEngine(fields.value);
  }

  return (records || []).map((record: any) => {
    const row: any = {
      _recordId: record?.id || '',
      _originalRecord: record,
      _depth: depth,
    };

    // 递归转换子节点
    if (record.children && record.children.length > 0) {
      row.children = transformTreeRecords(record.children, depth + 1);
      row.hierarchyState = 'expand';
    } else if (record.has_children) {
      // 有子节点标记但未加载子节点数据，设置占位
      row.children = true;
      row.hierarchyState = 'collapse';
    }

    // 映射字段值（与 transformRecords 逻辑一致）
    orderedVisibleFields.value.forEach(field => {
      if (!field?.id || !record?.values) return;
      const rawVal = record.values[field.id];

      switch (field.type) {
        case FieldType.SINGLE_SELECT: {
          const opts = (field.options?.choices || field.options?.options || []) as Array<{id: string, name: string, color?: string}>;
          const selId = typeof rawVal === 'object' && rawVal !== null ? String((rawVal as any).id || '') : String(rawVal || '');
          const found = opts.find(o => o.id === selId || o.name === selId);
          row[field.id] = found?.name || selId;
          break;
        }
        case FieldType.MULTI_SELECT: {
          let items: any[] = [];
          if (Array.isArray(rawVal)) items = rawVal;
          else if (typeof rawVal === 'string') try { const p = JSON.parse(rawVal); if (Array.isArray(p)) items = p; } catch {}
          if (items.length === 0) { row[field.id] = ''; break; }
          const opts = (field.options?.choices || field.options?.options || []) as Array<{id: string, name: string, color?: string}>;
          row[field.id] = items.map(v => {
            const vid = typeof v === 'object' ? String((v as any).id || '') : String(v);
            const vname = typeof v === 'object' ? String((v as any).name || '') : '';
            const of = opts.find(o => o.id === vid || o.name === vid);
            return vname || of?.name || vid;
          }).join(', ');
          break;
        }
        case FieldType.MEMBER: {
          let mems: any[] = [];
          if (Array.isArray(rawVal)) mems = rawVal;
          else if (typeof rawVal === 'string') try { const p = JSON.parse(rawVal); if (Array.isArray(p)) mems = p; } catch {}
          else if (typeof rawVal === 'object' && rawVal !== null) mems = [rawVal];
          const resolvedMembers = mems.map((m) => {
            let id = '';
            let name: string | undefined;
            if (typeof m === 'string') { id = m; }
            else if (typeof m === 'object' && m !== null) {
              id = String(m.user_id || m.id || '');
              name = m.name || undefined;
            } else { id = String(m); }
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
          // 附件字段：保持原始值，渲染由 customLayout 处理
          row[field.id] = rawVal;
          break;
        }
        case FieldType.FORMULA: {
          if (formulaEngine && rawVal === undefined) {
            try {
              row[field.id] = formulaEngine.calculate(field, record.values);
            } catch { row[field.id] = ''; }
          } else {
            row[field.id] = rawVal ?? '';
          }
          break;
        }
        default: {
          row[field.id] = rawVal ?? '';
          break;
        }
      }
    });

    // 缓存转换结果
    if (row._recordId) {
      transformedCache.set(row._recordId, row);
    }

    return row;
  });
};

/** 加载树形视图记录 */
const loadTreeRecords = async () => {
  if (isComponentDestroyed.value) return;
  // 仅加载当前组件所绑定表格的视图树形数据，避免表格切换/初始化残留时误调其他表格接口
  const current = viewStore.currentView;
  if (!current || current.tableId !== props.tableId) {
    treeRecords.value = [];
    return;
  }
  const viewId = props.viewId;
  if (!isTreeView.value || !viewId) {
    treeRecords.value = [];
    return;
  }
  // 防并发重复：同一视图的加载仍在进行中则跳过
  if (treeLoadingViewId === viewId) return;
  treeLoadingViewId = viewId;
  try {
    // 传递搜索关键词，后端筛选时会包含匹配记录的父级上下文
    const searchParam = searchInput.value ? searchInput.value.trim() : '';
    const data = await viewApiService.getViewTreeRecords(viewId, searchParam);
    if (isComponentDestroyed.value) return;
    treeRecords.value = transformTreeRecords(data.tree || []);
    updateTable();
  } catch (error) {
    console.error('[VTableView] 加载树形记录失败:', error);
    if (!isComponentDestroyed.value) treeRecords.value = [];
  } finally {
    treeLoadingViewId = '';
  }
};

// 为分组模式构建记录（在每个分组末尾插入虚拟「添加记录」行）
const buildGroupedRecords = (tableRecords: any[]): any[] => {
  if (!props.groupBy || props.groupBy.length === 0) return tableRecords;

  const groupToRecords = new Map<string, any[]>();
  for (const row of tableRecords) {
    const groupKey = props.groupBy.map(fieldId => {
      const val = row[fieldId];
      return val !== null && val !== undefined ? String(val) : '__empty__';
    }).join('||');
    if (!groupToRecords.has(groupKey)) {
      groupToRecords.set(groupKey, []);
    }
    groupToRecords.get(groupKey)!.push(row);
  }

  const rebuiltRecords: any[] = [];
  for (const [, records] of groupToRecords) {
    rebuiltRecords.push(...records);

    const groupValues: Record<string, any> = {};
    props.groupBy.forEach(fieldId => {
      groupValues[fieldId] = records[0][fieldId] ?? null;
    });

    const addButtonRecord: any = {
      _recordId: '__add_button__',
      _originalRecord: null,
      _rowType: 'addButton',
      _groupValues: { ...groupValues },
    };

    for (const fieldId of props.groupBy) {
      addButtonRecord[fieldId] = groupValues[fieldId];
    }

    orderedVisibleFields.value.forEach(field => {
      if (!props.groupBy!.includes(field.id)) {
        // 为每个字段设置唯一值，避免与上面空行合并
        const uniqueMarker = `__add_button_${Date.now()}_${field.id}__`;
        addButtonRecord[field.id] = uniqueMarker;
      }
    });

    rebuiltRecords.push(addButtonRecord);
  }

  return rebuiltRecords;
};

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
        barHeight: '20%',
        barBottom:'30%',
        textAlign: 'center',
        textBaseline: 'middle',
        fontSize: 12,
        color: '#374151',
        fontWeight: '500',
      };
      break;
    case FieldType.CHECKBOX:
      config.cellType = 'switch';
      config.style = {
        textAlign: 'center'
      };
      break;
    case FieldType.RICH_TEXT:
      config.cellType = 'text';
      config.fieldFormat = (record: any) => {
        const value = record?.[field.id];
        if (value == null || value === '') return '';
        // 过滤 HTML 标签，仅保留纯文本
        const tmp = document.createElement('div');
        tmp.innerHTML = String(value);
        return tmp.textContent || tmp.innerText || '';
      };
      break;
    case FieldType.URL:
      config.cellType = 'link';
      config.editor = 'input';
      config.linkJump = false; // 禁用 VTable 自动跳转，由 click_cell 延时导航控制
      break;
    case FieldType.EMAIL:
      config.cellType = 'link';
      config.editor = 'input';
      break;
    case FieldType.DATE:
      config.cellType = 'text';
      config.style = {
        textAlign: 'center'
      };
      config.fieldFormat = (value: any) => {
        // fieldFormat 接收的是整条 record，需用 field.id 提取单元格值
        const cellValue = value?.[field.id];
        if (cellValue == null || cellValue === '') return '';
        // 处理 Date 对象
        if (cellValue instanceof Date) {
          return formatDate(cellValue.getTime());
        }
        // 处理数字时间戳
        if (typeof cellValue === "number") {
          return formatDate(cellValue);
        }
        // 处理字符串
        if (typeof cellValue === "string") {
          return formatDate(cellValue);
        }
        return String(cellValue);
      };
      config.editor = 'date-only';
      break;
    case FieldType.DATE_TIME:
      config.cellType = 'text';
      config.fieldFormat = (value: any) => {
        // fieldFormat 接收的是整条 record，需用 field.id 提取单元格值
        const cellValue = value?.[field.id];
        if (cellValue == null || cellValue === '') return '';
        // 处理 Date 对象
        if (cellValue instanceof Date) {
          return formatDateTime(cellValue.getTime());
        }
        // 处理数字时间戳
        if (typeof cellValue === "number") {
          return formatDateTime(cellValue);
        }
        // 处理字符串
        if (typeof cellValue === "string") {
          return formatDateTime(cellValue);
        }
        return String(cellValue);
      };
      config.editor = 'date-time';
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
    case FieldType.LINK:
      config.cellType = 'text';
      config.fieldFormat = (record: any) => {
        const rawIds: string[] = record?.[field.id];
        if (!rawIds) return '';
        const recordId = record?._originalRecord?.id || record?._recordId || '';
        const cacheKey = recordId ? `${recordId}:${field.id}` : '';

        if (cacheKey && linkLoadingStates[cacheKey]) return '加载中...';
        if (cacheKey && linkErrorStates[cacheKey]) return '加载失败';

        const displayValues = cacheKey ? linkDisplayCache[cacheKey] : undefined;
        if (displayValues && displayValues.length > 0) {
          return displayValues.join(', ');
        }
        if (Array.isArray(rawIds) && rawIds.length > 0) {
          return `关联 ${rawIds.length} 条`;
        }
        return '';
      };
      break;
    case FieldType.NUMBER:
    case FieldType.PERCENT:
    case FieldType.CURRENCY:
    case FieldType.DURATION:
      config.cellType = 'text';
      config.editor = 'input';
      config.style = {
        textAlign: 'right'
      };
      config.fieldFormat = (record: any) => {
        const value = record?.[field.id];
        if (value === null || value === undefined || value === '') return '';
        const num = Number(value);
        if (Number.isNaN(num)) return String(value);

        const options = field.options || {};
        const precision = options.precision ?? 0;
        const prefix = options.prefix || '';
        const suffix = options.suffix || '';
        const currencySymbol = options.currencySymbol || '';

        let formatted = num.toFixed(precision);
        if (field.type === FieldType.PERCENT) {
          formatted = `${formatted}%`;
        } else if (field.type === FieldType.CURRENCY && currencySymbol) {
          formatted = `${currencySymbol}${formatted}`;
        }

        return `${prefix}${formatted}${suffix}`;
      };
      break;
    case FieldType.PHONE:
    case FieldType.BARCODE:
      config.cellType = 'text';
      config.editor = 'input';
      break;
    // 公式/只读字段，不绑定编辑器
    case FieldType.FORMULA:
    case FieldType.LOOKUP:
    case FieldType.AUTO_NUMBER:
    case FieldType.CREATED_BY:
    case FieldType.CREATED_TIME:
    case FieldType.UPDATED_BY:
    case FieldType.UPDATED_TIME:
      config.cellType = 'text';
      // 不设置 editor，保持只读
      break;
    default:
      // 文本类、数字类等使用默认 text 类型
      config.cellType = 'text';
      config.editor = 'input';
      break;
  }
  
  return config;
};

/**
 * 子表列增强器
 * 让子表字段渲染样式与主表保持一致：
 * - 复用主表 getCellTypeConfig 的 cellType / fieldFormat / style / editor 配置
 * - 为复杂类型字段（单选/多选/附件/成员/评分等）添加 customLayout，复用主表的渲染逻辑
 * - 为公式/自动编号等字段添加 customRender
 *
 * 该函数作为 useMasterDetail.setColumnEnhancer 的回调注入，在 preloadColumns 阶段执行
 */
const enhanceSubTableColumns = (columns: any[], targetFields: any[]): any[] => {
  return columns.map((col: any) => {
    const field = targetFields.find((f) => f.id === col.field);
    if (!field) return col;

    // 合并主表 getCellTypeConfig 的配置（cellType / fieldFormat / style / editor）
    const cellTypeConfig = getCellTypeConfig(field);
    const enhancedCol = { ...col, ...cellTypeConfig };

    // 为复杂类型字段添加 customLayout（复用主表的 VRender 渲染逻辑）
    const layoutTypes = [
      FieldType.SINGLE_SELECT,
      FieldType.MULTI_SELECT,
      FieldType.MEMBER,
      FieldType.RATING,
      FieldType.ATTACHMENT,
    ];
    if (layoutTypes.includes(field.type as typeof layoutTypes[number])) {
      enhancedCol.customLayout = (args: any) => {
        const { table, row, col: colIdx, rect } = args;
        if (!table) return { renderDefault: true };

        const value = table.getCellValue(colIdx, row);
        if (value === null || value === undefined) return { renderDefault: true };

        const cellHeight = rect?.height || table.getCellRect(colIdx, row).height || 40;
        const cellWidth = rect?.width || table.getCellRect(colIdx, row).width || 150;
        const fontFamily = 'system-ui, -apple-system, sans-serif';
        const fontSize = 12;

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
            const color = found?.color;

            const tagHeight = 26;
            const textWidth = measureText(val);
            const tagWidth = Math.min(textWidth + 16, cellWidth);
            const xOffset = Math.max(0, (cellWidth - tagWidth) / 2);
            const yOffset = Math.max(0, (cellHeight - tagHeight) / 2);

            const container = createGroup({ width: cellWidth, height: cellHeight });
            const bg = createRect({ x: xOffset, y: yOffset, width: tagWidth, height: tagHeight, cornerRadius: 12, fill: color });
            container.add(bg);
            const text = createText({ x: xOffset + 8, y: yOffset + tagHeight / 2, text: val, fontSize, fill: '#ffffff', textBaseline: 'middle' });
            container.add(text);
            return { rootContainer: container, renderDefault: false };
          }
          case FieldType.MULTI_SELECT: {
            let vals: string[] = [];
            if (Array.isArray(value)) {
              vals = value.map(v => typeof v === 'object' ? String((v as any).name || (v as any).id || '') : String(v));
            } else if (typeof value === 'string') {
              try { const p = JSON.parse(value); if (Array.isArray(p)) vals = p.map(v => String(v)); } catch {}
              if (vals.length === 0) vals = value.split(', ').filter(Boolean);
            }
            if (vals.length === 0) return { renderDefault: true };
            const options = (field.options?.choices || field.options?.options || []) as Array<{id: string, name: string, color?: string}>;

            const tagHeight = 26;
            const gap = 8;

            const container = createGroup({
              width: cellWidth, height: cellHeight,
              display: 'flex', flexDirection: 'row', flexWrap: 'wrap',
              alignContent: 'center', alignItems: 'center'
            });
            const spacerLeft = createRect({ x: 0, y: 0, width: 8, height: tagHeight, fill: 'transparent' });
            container.add(spacerLeft);

            vals.forEach((v) => {
              const opt = options.find(o => o.name === v);
              const color = opt?.color || '#6B7280';
              const textWidth = measureText(v);
              const tagWidth = textWidth + 16;
              const tagGroup = createGroup({ width: tagWidth + gap, height: tagHeight, flexDirection: 'row' as const, alignItems: 'center' as const });
              const bg = createRect({ x: 0, y: 0, width: tagWidth, height: tagHeight, cornerRadius: 12, fill: color });
              tagGroup.add(bg);
              const text = createText({ x: 8, y: tagHeight / 2, text: v, fontSize, fill: '#ffffff', textBaseline: 'middle' });
              tagGroup.add(text);
              container.add(tagGroup);
            });
            return { rootContainer: container, renderDefault: false };
          }
          case FieldType.ATTACHMENT: {
            let files: any[] = [];
            if (Array.isArray(value)) {
              files = value;
            } else if (typeof value === 'string') {
              try { const p = JSON.parse(value); if (Array.isArray(p)) files = p; } catch {}
            } else if (value && typeof value === 'object') {
              if ((value as any).id || (value as any).url) files = [value];
            }
            files = files.filter((f: any) => f && (typeof f === 'string' || typeof f === 'object'));
            if (files.length === 0) return { renderDefault: true };

            const isImageFile = (name: string): boolean => {
              const ext = (name || '').split('.').pop()?.toLowerCase() || '';
              return ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'svg', 'ico'].includes(ext);
            };

            const itemSize = 32;
            const gap = 6;
            const maxDisplay = 3;
            const displayFiles = files.slice(0, maxDisplay);
            const overflow = files.length > maxDisplay ? files.length - maxDisplay : 0;

            const container = createGroup({
              width: cellWidth, height: cellHeight,
              display: 'flex', flexDirection: 'row', alignItems: 'center', flexWrap: 'nowrap'
            });

            displayFiles.forEach((file: any) => {
              const fileName = file.name || '';
              const fileUrl = file.url || file.thumbnail || file.preview || '';
              const isImage = isImageFile(fileName);

              if (isImage && fileUrl) {
                const img = createImage({ width: itemSize, height: itemSize, image: fileUrl, cornerRadius: 4, cursor: 'pointer' });
                img.addEventListener('pointerdown', (e: any) => { e.stopPropagation?.(); });
                img.addEventListener('pointertap', (e: any) => {
                  e.stopPropagation?.();
                  attachmentImagePreviewUrl.value = fileUrl;
                  attachmentImagePreviewName.value = fileName;
                  attachmentImagePreviewVisible.value = true;
                });
                const itemGroup = createGroup({ width: itemSize + gap, height: itemSize, display: 'flex', alignItems: 'center' });
                itemGroup.add(img);
                container.add(itemGroup);
              } else {
                const itemGroup = createGroup({ width: itemSize + gap, height: itemSize, display: 'flex', alignItems: 'center' });
                const pinPath = createPath({
                  path: 'M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48',
                  x: (itemSize - 14) / 2, y: (itemSize - 14) / 2,
                  stroke: '#9CA3AF', lineWidth: 1.5, lineCap: 'round', lineJoin: 'round', fill: 'none'
                });
                itemGroup.add(pinPath);
                container.add(itemGroup);
              }
            });

            if (overflow > 0) {
              const overflowGroup = createGroup({ width: itemSize, height: itemSize, display: 'flex', alignItems: 'center', justifyContent: 'center' });
              const overflowText = createText({ x: itemSize / 2, y: itemSize / 2, text: `+${overflow}`, fontSize: 15, fill: '#6B7280', textBaseline: 'middle', textAlign: 'center' });
              overflowGroup.add(overflowText);
              container.add(overflowGroup);
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

            const container = createGroup({ width: cellWidth, height: cellHeight });
            for (let i = 0; i < maxRating; i++) {
              const cx = xOffset + i * (starSize + starSpacing) + starSize / 2;
              const cy = yOffset + starSize / 2;
              const star = createPath({ path: getStarPath(cx, cy, starSize / 2, 5, 0.5), fill: '#e5e7eb' });
              container.add(star);
            }
            const fullStars = Math.floor(rating);
            for (let i = 0; i < fullStars; i++) {
              const cx = xOffset + i * (starSize + starSpacing) + starSize / 2;
              const cy = yOffset + starSize / 2;
              const star = createPath({ path: getStarPath(cx, cy, starSize / 2, 5, 0.5), fill: '#F59E0B' });
              container.add(star);
            }
            return { rootContainer: container, renderDefault: false };
          }
          case FieldType.MEMBER: {
            let memberData: Array<{id: string, name: string}> = [];
            try {
              const parsed = JSON.parse(String(value));
              if (Array.isArray(parsed) && parsed.length > 0) {
                memberData = parsed.map((m: any) => ({ id: String(m.id || ''), name: String(m.name || m.id || '') }));
              }
            } catch (_) {
              const parts = String(value).split(', ').filter(Boolean);
              memberData = parts.map(p => ({ id: p, name: p }));
            }
            if (memberData.length === 0) {
              // 空值显示占位符 -（与主表一致）
              const emptyLabel = createText({
                x: 8,
                y: cellHeight / 2,
                text: '-',
                fontSize,
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

            const container = createGroup({ width: cellWidth, height: cellHeight });
            let currentX = 8;
            const yOffset = Math.max(0, (cellHeight - avatarSize) / 2);
            const nameSpacing = 4;
            const memberSpacing = 12;

            displayMembers.forEach((m) => {
              const hash = m.name.split('').reduce((acc, c) => acc + c.charCodeAt(0), 0);
              const avatarColor = avatarColors[Math.abs(hash) % avatarColors.length];
              const initial = m.name.charAt(0).toUpperCase();
              const circle = createCircle({ x: currentX + radius, y: yOffset + radius, radius, fill: avatarColor });
              container.add(circle);
              const initialText = createText({ x: currentX + radius, y: yOffset + radius, text: initial, fontSize: 10, fontWeight: '600', fill: '#ffffff', textBaseline: 'middle', textAlign: 'center' });
              container.add(initialText);
              const nameTextX = currentX + avatarSize + nameSpacing;
              const nameText = createText({ x: nameTextX, y: yOffset + radius, text: m.name, fontSize: 12, fill: '#333333', textBaseline: 'middle' });
              container.add(nameText);
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
              const overflowBg = createRect({ x: currentX, y: overflowY, width: overflowWidth, height: overflowHeight, cornerRadius: 4, fill: '#e5e7eb' });
              container.add(overflowBg);
              const overflowLabel = createText({ x: currentX + overflowPadding, y: overflowY + overflowHeight / 2, text: overflowText, fontSize: 11, fill: '#6B7280', textBaseline: 'middle' });
              container.add(overflowLabel);
            }
            return { rootContainer: container, renderDefault: false };
          }
        }
        return { renderDefault: true };
      };
    }

    // 为公式/自动编号等字段添加 customRender（复用主表的渲染逻辑）
    const complexRenderTypes = [
      FieldType.FORMULA,
      FieldType.AUTO_NUMBER,
      FieldType.CREATED_BY,
      FieldType.CREATED_TIME,
      FieldType.UPDATED_BY,
      FieldType.UPDATED_TIME,
    ];
    if (complexRenderTypes.includes(field.type as typeof complexRenderTypes[number])) {
      enhancedCol.customRender = (args: any) => {
        if (!args || !args.record) return "";
        const value = args.record[field.id];
        if (value === null || value === undefined) return "";
        return String(value);
      };
    }

    return enhancedCol;
  });
};

/**
 * 子表记录转换器
 * 复用主表 transformRecords 中的字段值转换逻辑，让子表记录值与主表保持一致
 * - 单选：选项 ID -> 选项 name
 * - 多选：ID 数组 -> name 逗号分隔字符串
 * - 成员：解析为 JSON 字符串 [{id, name}]
 * - 附件：统一为数组格式
 */
const transformSubTableRecords = (records: any[], targetFields: any[]): any[] => {
  return records.map((row: any) => {
    const transformed: any = { ...row };
    targetFields.forEach((field: any) => {
      if (!field?.id) return;
      const rawVal = transformed[field.id];
      switch (field.type) {
        case FieldType.SINGLE_SELECT: {
          const opts = (field.options?.choices || field.options?.options || []) as Array<{id: string, name: string, color?: string}>;
          const selId = typeof rawVal === 'object' && rawVal !== null ? String((rawVal as any).id || '') : String(rawVal || '');
          const found = opts.find(o => o.id === selId || o.name === selId);
          transformed[field.id] = found?.name || selId;
          break;
        }
        case FieldType.MULTI_SELECT: {
          let items: any[] = [];
          if (Array.isArray(rawVal)) items = rawVal;
          else if (typeof rawVal === 'string') try { const p = JSON.parse(rawVal); if (Array.isArray(p)) items = p; } catch {}
          if (items.length === 0) { transformed[field.id] = ''; break; }
          const opts = (field.options?.choices || field.options?.options || []) as Array<{id: string, name: string}>;
          transformed[field.id] = items.map(v => {
            const vid = typeof v === 'object' ? String((v as any).id || '') : String(v);
            const vname = typeof v === 'object' ? String((v as any).name || '') : '';
            const of = opts.find(o => o.id === vid || o.name === vid);
            return vname || of?.name || vid;
          }).join(', ');
          break;
        }
        case FieldType.MEMBER: {
          let mems: any[] = [];
          if (Array.isArray(rawVal)) mems = rawVal;
          else if (typeof rawVal === 'string') try { const p = JSON.parse(rawVal); if (Array.isArray(p)) mems = p; } catch {}
          else if (typeof rawVal === 'object' && rawVal !== null) mems = [rawVal];
          const resolvedMembers = mems.map((m) => {
            let id = '';
            let name: string | undefined;
            if (typeof m === 'string') { id = m; }
            else if (typeof m === 'object' && m !== null) {
              id = String(m.user_id || m.id || '');
              name = m.name || undefined;
            } else { id = String(m); }
            if (!name) {
              const cached = userCacheStore.getCachedUser(id);
              name = cached?.name || id;
            }
            return { id, name: name || id };
          });
          transformed[field.id] = JSON.stringify(resolvedMembers);
          break;
        }
        case FieldType.ATTACHMENT: {
          if (!rawVal) { transformed[field.id] = ''; break; }
          if (Array.isArray(rawVal)) { transformed[field.id] = rawVal; break; }
          if (typeof rawVal === 'object' && rawVal !== null) {
            if ((rawVal as any).url) { transformed[field.id] = [rawVal]; break; }
            const arr = Object.values(rawVal);
            if (Array.isArray(arr)) { transformed[field.id] = arr; break; }
          }
          if (typeof rawVal === 'string') {
            try { const p = JSON.parse(rawVal); if (Array.isArray(p)) { transformed[field.id] = p; break; } } catch {}
            transformed[field.id] = rawVal; break;
          }
          transformed[field.id] = rawVal;
          break;
        }
        default:
          // 其他字段保持原值
          break;
      }
    });
    return transformed;
  });
};

// 字段类型到 SVG 图标的映射（用于表头显示，路径数据与 Element Plus 图标保持一致）
function getFieldTypeSvg(type: string, color = '#9CA3AF'): string {
  const pathContent = fieldTypeSvgContentMap[type];
  if (!pathContent) return getFieldTypeSvg('single_line_text', color);
  return `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1024 1024" width="16" height="16" fill="${color}">${pathContent}</svg>`;
}

// 构建 VTable 配置
const buildTableConfig = (): any => {
  const columns = orderedVisibleFields.value.map((field) => {
    const sortInfo = currentSorts.value.find(s => s.fieldId === field.id);
    const cellTypeConfig = getCellTypeConfig(field);
    
    // 为 single_select 字段创建带选项的 SingleSelectEditor（支持选择或清空，选项以彩色标签显示）
    if (field.type === FieldType.SINGLE_SELECT) {
      const options = (field.options?.choices || field.options?.options || []) as Array<{id: string, name: string, color?: string}>;
      cellTypeConfig.editor = new SingleSelectEditor({ options });
    }
    
    // 为 multi_select 字段创建带选项的 MultiSelectEditor（选项以彩色标签显示）
    if (field.type === FieldType.MULTI_SELECT) {
      const options = (field.options?.choices || field.options?.options || []) as Array<{id: string, name: string, color?: string}>;
      cellTypeConfig.editor = new MultiSelectEditor({ options });
    }

    // 为 LONG_TEXT 分配 TextAreaEditor（浮窗多行编辑器）
    if (field.type === FieldType.LONG_TEXT) {
      cellTypeConfig.editor = new TextAreaEditor();
    }

    // 为 RICH_TEXT 分配 RichTextEditor（浮窗富文本编辑器，集成 @opentiny/fluent-editor）
    if (field.type === FieldType.RICH_TEXT) {
      cellTypeConfig.editor = new RichTextEditor();
    }

    // 为 PROGRESS 分配 InputEditor（整数输入 0-100）
    if (field.type === FieldType.PROGRESS) {
      cellTypeConfig.editor = new InputEditor();
    }

    // 为 RATING 分配 RatingEditor
    if (field.type === FieldType.RATING) {
      cellTypeConfig.editor = new RatingEditor();
    }

    // 为 MEMBER 分配 MemberEditor（带搜索、已选标签、选择即保存）
    if (field.type === FieldType.MEMBER) {
      const allowMultiple = (field.options as any)?.allowMultiple !== false;
      const baseId = tableStore.currentTable?.baseId;
      cellTypeConfig.editor = new MemberEditor({ allowMultiple, baseId });
    }

    // 附件类型字段不需要编辑器，由自定义双击浮窗 AttachmentManager 处理
    // 防止 VTable 内置 'input' 编辑器将数组值 toString 为 "[object Object]"
    if (field.type === FieldType.ATTACHMENT) {
      cellTypeConfig.editor = undefined;
    }

    return {
      field: field.id,
      title: field.name,
      description: field.description,
      width: columnWidths.value[field.id] || 150,
      minWidth: 60,
      // 使用自定义排序比较函数：根据字段类型选择数值/文本比较策略，
      // 同时确保 addButton 虚拟行（值以 __add_button_ 前缀标记）始终排到末尾
      sort: createSortComparator(field.type),
      sortState: sortInfo ? (sortInfo.direction === 'asc' ? 'asc' : 'desc') : 'normal',
      headerIcon: [{
        type: 'svg',
        svg: getFieldTypeSvg(field.type),
        positionType: 'inlineFront',
        name: 'field-type-icon',
        width: 16,
        height: 16,
        marginRight: 6,
      }],
      ...cellTypeConfig,
      // 单选/多选/成员字段由 customLayout 接管渲染，不设置 Canvas 层样式
      ...((field.type === FieldType.SINGLE_SELECT || field.type === FieldType.MULTI_SELECT) ? {
        style: {
          padding: [0, 8],
        }
      } : {}),
      // 自动编号字段使用偏灰的蓝色，与邮箱链接颜色类似，便于区分
      ...(field.type === FieldType.AUTO_NUMBER ? {
        style: {
          color: '#409eff',
          fontFamily: '"SF Mono", Monaco, monospace',
          fontWeight: 'bold',
        }
      } : {}),
      // 单元格合并配置：当字段的 options.mergeCell 为 true 时启用
      ...(field.options?.mergeCell ? {
        mergeCell: true
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
    FieldType.ATTACHMENT,
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
          const color = found?.color;

          const tagHeight = 26;
          const textWidth = measureText(val);
          const tagWidth = Math.min(textWidth + 16, cellWidth);
          const xOffset = Math.max(0, (cellWidth - tagWidth) / 2);
          const yOffset = Math.max(0, (cellHeight - tagHeight) / 2);

          const container = createGroup({
            width: cellWidth,
            height: cellHeight
          });

          const bg = createRect({
            x: xOffset,
            y: yOffset,
            width: tagWidth,
            height: tagHeight,
            cornerRadius: 12,
            fill: color
          });
          container.add(bg);

          const text = createText({
            x: xOffset + 8,
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
          // 兼容：string[] | JSON 数组字符串 | 旧版逗号分隔字符串
          let vals: string[] = [];
          if (Array.isArray(value)) {
            vals = value.map(v => typeof v === 'object' ? String((v as any).name || (v as any).id || '') : String(v));
          } else if (typeof value === 'string') {
            try { const p = JSON.parse(value); if (Array.isArray(p)) vals = p.map(v => String(v)); } catch {}
            if (vals.length === 0) vals = value.split(', ').filter(Boolean);
          }
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

          // 左留白 8px（flex 布局不支持 padding，用占位元素实现）
          const spacerLeft = createRect({
            x: 0,
            y: 0,
            width: 8,
            height: tagHeight,
            fill: 'transparent'
          });
          container.add(spacerLeft);

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
              x: 8,
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

          let currentX = 8;
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
        case FieldType.ATTACHMENT: {
          // 解析附件数据，数据格式: [{id, url, name, type?}]
          let files: any[] = [];
          if (Array.isArray(value)) {
            files = value;
          } else if (typeof value === 'string') {
            try { const p = JSON.parse(value); if (Array.isArray(p)) files = p; } catch {}
          } else if (value && typeof value === 'object') {
            // 单个文件对象
            if ((value as any).id || (value as any).url) {
              files = [value];
            }
          }
          // 过滤掉无效条目，始终渲染空容器而非 renderDefault（避免数组被 toString 渲染为 "[object Object]"）
          files = files.filter((f: any) => f && (typeof f === 'string' || typeof f === 'object'));

          // 判断文件名是否为图片
          const isImageFile = (name: string): boolean => {
            const ext = (name || '').split('.').pop()?.toLowerCase() || '';
            return ['jpg', 'jpeg', 'png', 'gif', 'webp', 'bmp', 'svg', 'ico'].includes(ext);
          };

          const itemSize = 32;
          const gap = 6;
          const maxDisplay = 3;
          const displayFiles = files.slice(0, maxDisplay);
          const overflow = files.length > maxDisplay ? files.length - maxDisplay : 0;

          const container = createGroup({
            width: cellWidth,
            height: cellHeight,
            display: 'flex',
            flexDirection: 'row',
            alignItems: 'center',
            flexWrap: 'nowrap'
          });

          displayFiles.forEach((file: any) => {
            const fileName = file.name || '';
            const fileUrl = file.url || file.thumbnail || file.preview || '';
            const isImage = isImageFile(fileName);

            if (isImage && fileUrl) {
              // 图片缩略图
              const img = createImage({
                width: itemSize,
                height: itemSize,
                image: fileUrl,
                cornerRadius: 4,
                cursor: 'pointer',
              });
              // 单击缩略图直接预览完整图片，阻止事件冒泡到单元格
              img.addEventListener('pointerdown', (e: any) => {
                e.stopPropagation?.();
              });
              img.addEventListener('pointertap', (e: any) => {
                e.stopPropagation?.();
                attachmentImagePreviewUrl.value = fileUrl;
                attachmentImagePreviewName.value = fileName;
                attachmentImagePreviewVisible.value = true;
              });
              const itemGroup = createGroup({
                width: itemSize + gap,
                height: itemSize,
                display: 'flex',
                alignItems: 'center'
              });
              itemGroup.add(img);
              container.add(itemGroup);
            } else {
              // 文件类型图标 - 仅显示回形针 SVG 图标
              const itemGroup = createGroup({
                width: itemSize + gap,
                height: itemSize,
                display: 'flex',
                alignItems: 'center'
              });

              // 回形针图标
              const pinPath = createPath({
                path: 'M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48',
                x: (itemSize - 14) / 2,
                y: (itemSize - 14) / 2,
                stroke: '#9CA3AF',
                lineWidth: 1.5,
                lineCap: 'round',
                lineJoin: 'round',
                fill: 'none'
              });
              itemGroup.add(pinPath);
              container.add(itemGroup);
            }
          });

          if (overflow > 0) {
            const overflowGroup = createGroup({
              width: itemSize,
              height: itemSize,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            });
            const overflowText = createText({
              x: itemSize / 2,
              y: itemSize / 2,
              text: `+${overflow}`,
              fontSize: 15,
              fill: '#6B7280',
              textBaseline: 'middle',
              textAlign: 'center'
            });
            overflowGroup.add(overflowText);
            container.add(overflowGroup);
          }

          return { rootContainer: container, renderDefault: false };
        }
      }

      return { renderDefault: true };
    };
  });

  // 树形视图：启用 VTable 原生树形渲染，第一列自动显示展开/折叠图标和层级缩进
  if (isTreeView.value && columns.length > 0) {
    columns[0].tree = true;
  }

  // 转换 records 为 VTable 需要的格式（字段映射 + 公式计算）
  clearTransformCache(); // 确保全量重建时使用最新记录数据，不返回缓存中的旧行
  let tableRecords = isTreeView.value ? treeRecords.value : transformRecords(sortedRecords.value);

  // 非分组模式下在表格末尾追加「+ 添加记录」虚拟行
  // 树形视图不追加按钮行
  if ((!props.groupBy || props.groupBy.length === 0) && !props.readonly && !isTreeView.value) {
    const addButtonRecord: any = {
      _recordId: '__add_button__',
      _originalRecord: null,
      _rowType: 'addButton',
    };
    // 为每个字段设置唯一值，避免与上面空行合并
    // 使用时间戳确保每次都是唯一的值
    const uniqueMarker = `__add_button_${Date.now()}__`;
    orderedVisibleFields.value.forEach(field => {
      addButtonRecord[field.id] = uniqueMarker;
    });
    tableRecords.push(addButtonRecord);
  }

  // 分组末尾添加按钮行
  if (props.groupBy && props.groupBy.length > 0 && tableRecords.length > 0) {
    tableRecords = buildGroupedRecords(tableRecords);
  }

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

  // 数据源模式选择：
  // - 非分组：使用 CachedDataSource 懒渲染，VTable 仅处理可见行
  // - 分组模式：必须使用 records 模式，VTable 的 groupBy/rowSeriesNumber 需要遍历全部记录
  const isGrouped = props.groupBy && props.groupBy.length > 0;

  if (!isGrouped) {
    // 非分组：创建 CachedDataSource
    
    if (!smartDataSource || smartDataSource.totalCount !== tableRecords.length) {
      smartDataSource = new SmartTableDataSource({
        totalCount: tableRecords.length,
        batchSize: 200,
        maxCachedBatches: 80,  // 80×200=16,000条；覆盖 10,000 条 + addButton 虚拟行（共 51 批次），避免 LRU 立即驱逐首批写入批次
      });
    } else {
      smartDataSource.clearCache();
    }
    smartDataSource.updateMemoryCache(tableRecords, 0);
    smartDataSource.markFullyLoaded();
  }

  const config = {
    columns,
    ...(isTreeView.value
      ? { records: tableRecords }
      : (isGrouped
        ? { records: tableRecords }
        : { dataSource: smartDataSource!.dataSource })),
    // 主从表插件配置（树形视图下不启用主从表）
    ...(!isTreeView.value && hasLinkFields.value && masterDetailPlugin.value ? {
      plugins: [masterDetailPlugin.value],
      hierarchyExpandLevel: 1, // 默认折叠
    } : {}),
    // 树形视图配置
    ...(isTreeView.value ? {
      hierarchyExpandLevel: -1, // 展开所有层级
      enableTreeStickCell: true,
    } : {}),
    frozenColCount,
    showFrozenIcon: true,
    allowFrozenColCount,
    widthMode: 'standard',
    heightMode: 'standard',
    autoFillWidth: false,
    autoFillHeight: false,
    defaultRowHeight: 36,
    autoRowHeight: false,
    tooltip: {
      isShowOverflowTextTooltip: true
    },
    rowSeriesNumber: {
      title: '#',
      width: 'auto',
      cellType: 'checkbox',
      headerType: 'checkbox',
      format: (_col: number, row: number, table: any) => {
        if (row === table.dataSource._sourceLength){
          return '+';
        }
        return row;
      },
      // 禁用新增行的复选框（虽然显示但不可点击）
      disable: (args: any) => {
        const { row, table } = args;
        // 新增行禁用复选框
        return row === table.dataSource._sourceLength;
      },
      // 普通平铺模式下启用拖拽排序，树形视图下禁用（避免与树形展开/折叠冲突）
      dragOrder: !isTreeView.value,
    },
    allowCopy: true,
    editCellTrigger: 'click',
    keyboardOptions: {
      copySelected: true,
      pasteValueToCell: true,
      editCellOnEnter: true,
      moveFocusCellOnTab: true,
      moveEditCellOnArrowKeys: true,
      moveFocusCellOnEnter: true,
    },
    select: {
      mode: 'multiple',
      enable: true,
      highlightMode: 'row',
    },
    resize: {
      columnResizeMode: 'all',
    },
    containerFit: {
      width: true,
      height: true
    },
    // 分组配置：当设置分组条件时，使用 VTable 原生分组展示
    ...(props.groupBy && props.groupBy.length > 0 ? {
      groupConfig: {
        groupBy: props.groupBy,
        enableTreeStickCell: true,
        titleCheckbox: false,
        titleFieldFormat: (record: any) => {
          const groupName = record?.vtableMergeName || '';
          const children = record?.vtableChildren || record?.children || [];
          const realCount = children.filter((c: any) => c._rowType !== 'addButton').length;
          return `${groupName} (${realCount} 条)`;
        },
      },
      enableCheckboxCascade: true,
    } : {}),
    theme: themes.DEFAULT.extends({
      scrollStyle: {
        barToSide: true,
        visible: 'always'
      },
      headerStyle: {
        color: '#646A73',
        fontSize: 13,
      },
      bodyStyle: {
        color: '#374151'
      },
      ...(props.groupBy && props.groupBy.length > 0 ? {
        groupTitleStyle: {
          fontWeight: 'bold',
          fontSize: 13,
          color: '#1f2937',
          textAlign: 'left',
          bgColor: (args: any) => {
            const { col, row, table } = args;
            if (!table) return '#f3f4f6';
            const level = table.getGroupTitleLevel(col, row);
            const colors = ['#eef2ff', '#f5f3ff', '#fefce8'];
            return level !== undefined ? colors[level % colors.length] : '#f3f4f6';
          },
        }
      } : {}),
    }),
  };

  // 为所有数据列添加 addButton 行处理：覆盖单元格内容，隐藏分组字段值
  // customMergeCell 与 groupBy 不兼容，故使用每列 customLayout 方式
  if (props.groupBy && props.groupBy.length > 0) {
    columns.forEach((col: any) => {
      const origCustomLayout = col.customLayout;
      col.customLayout = (args: any) => {
        const { table, row, col: colIdx, rect } = args;
        if (!table) return { renderDefault: true };
        const record = table.getCellOriginRecord(colIdx, row);
        if (record && record._rowType === 'addButton') {
          const cellHeight = rect?.height || table.getCellRect(colIdx, row).height || 36;
          const cellWidth = rect?.width || table.getCellRect(colIdx, row).width || 150;
          const container = createGroup({ width: cellWidth, height: cellHeight });
          const bg = createRect({ x: 0, y: 0, width: cellWidth, height: cellHeight, fill: '#f9fafb' });
          container.add(bg);
          const topBorder = createRect({ x: 0, y: 0, width: cellWidth, height: 1, fill: '#e5e7eb' });
          container.add(topBorder);
          if (row < 0 || !table) return undefined;
          // 在第一个数据列（colIdx 2，col 0=行号，col 1=复选框）居中渲染文字
          if (colIdx % 2 === 1) {
            const text = createText({
              x: cellWidth / 2,
              y: cellHeight / 2,
              text: '+ 添加记录',
              fontSize: 13,
              fill: '#c0c0c0',
              textBaseline: 'middle',
              textAlign: 'center',
            });
            container.add(text);
          }
          return { rootContainer: container, renderDefault: false };
        }
        if (origCustomLayout) return origCustomLayout(args);
        return { renderDefault: true };
      };
    });
  }

  // 非分组模式下为所有数据列添加 addButton 行处理
  if ((!props.groupBy || props.groupBy.length === 0) && !props.readonly) {
    columns.forEach((col: any) => {
      const origCustomLayout = col.customLayout;
      col.customLayout = (args: any) => {
        const { table, row, col: colIdx, rect } = args;
        if (!table) return { renderDefault: true };
        const record = table.getCellOriginRecord(colIdx, row);
        if (record && record._rowType === 'addButton') {
          const cellHeight = rect?.height || table.getCellRect(colIdx, row).height || 36;
          const cellWidth = rect?.width || table.getCellRect(colIdx, row).width || 150;
          const container = createGroup({ width: cellWidth, height: cellHeight });
          const bg = createRect({ x: 0, y: 0, width: cellWidth, height: cellHeight, fill: '#f9fafb' });
          container.add(bg);
          const topBorder = createRect({ x: 0, y: 0, width: cellWidth, height: 1, fill: '#e5e7eb' });
          container.add(topBorder);
          // col 0=rowSeriesNumber，col 1=第一数据列
          if (colIdx % 2 === 1) {
            const text = createText({
              x: cellWidth / 2,
              y: cellHeight / 2,
              text: '+ 添加记录',
              fontSize: 13,
              fill: '#c0c0c0',
              textBaseline: 'middle',
              textAlign: 'center',
            });
            container.add(text);
          }
          return { rootContainer: container, renderDefault: false };
        }
        if (origCustomLayout) return origCustomLayout(args);
        return { renderDefault: true };
      };
    });
  }

  return config;
};

// 处理悬浮操作图标点击 - 打开记录详情
const handleActionIconClick = () => {
  if (selectedCell.value && selectedCell.value.record?._originalRecord) {
    const original = selectedCell.value.record._originalRecord;
    // 区分主表与子表记录：
    // - 主表 _originalRecord 是 RecordEntity（含 createdAt/updatedAt camelCase）
    // - 子表 _originalRecord 是 LinkedRecordDetail（含 created_at/updated_at snake_case）
    if ('created_at' in original || 'updated_at' in original) {
      // 子表记录：使用子表字段和目标表 ID
      handleSubTableExpandRecord(selectedCell.value.record);
    } else {
      // 主表记录
      handleExpandRecord(original as RecordEntity);
    }
  }
  actionIconVisible.value = false;
  selectedCell.value = null;
};

// 初始化表格
const initTable = () => {
  if (!tableContainerRef.value) return;

  // 检测 LINK 字段并创建主从表插件（树形视图下禁用主从表）
  detectLinkFields(fields.value);
  if (hasLinkFields.value && !isTreeView.value) {
    // 注入子表列增强器和记录转换器：让子表字段渲染样式和数据转换与主表保持一致
    setColumnEnhancer(enhanceSubTableColumns);
    setRecordTransformer(transformSubTableRecords);
    // 使用与主表一致的定制主题（包含 headerStyle/bodyStyle/scrollStyle 等）
    const subTableTheme = themes.DEFAULT.extends({
      scrollStyle: { barToSide: true, visible: 'always' },
      headerStyle: { color: '#646A73', fontSize: 13 },
      bodyStyle: { color: '#374151' },
    });
    createPluginInstance(subTableTheme);
  }

  // 树形视图：异步加载树形记录后重建表格
  if (isTreeView.value) {
    loadTreeRecords();
  }

  const config = buildTableConfig();
  tableInstance = new ListTable(tableContainerRef.value, config);

  bindTableEvents();

  // 应用缓存的列宽
  applyColumnWidths();
};

// 绑定表格事件
const bindTableEvents = () => {
  if (!tableInstance) return;

  const tableInstanceAny = tableInstance as any;

  // 表格初始化完成后应用缓存列宽（确保渲染完成后再设置）
  tableInstanceAny.on('initialized', () => {
    console.log('[VTableView] initialized 事件触发，准备应用缓存列宽');
    // 延迟到下一帧，确保 VTable 内部布局完成
    nextTick(() => {
      setTimeout(() => applyColumnWidths(), 0);
    });
  });

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
      // 跳过新增行的复选框操作（新增行不显示复选框，但阻止可能的误触）
      if (record && record._rowType === 'addButton') return;
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

        // 协同编辑：检查锁状态
        const authStore = useAuthStore();
        const currentUserId = authStore.user?.id;
        const tableId = tableStore.currentTable?.id;
        const baseId = tableStore.currentTable?.baseId;

        if (tableId && currentUserId && baseId && collabStore.isRealtimeAvailable) {
          // 如果被其他用户锁定，回退开关状态并提示
          if (collabStore.isCellLockedByOther(recordId, fieldId, currentUserId)) {
            const lockInfo = collabStore.getCellLockInfo(recordId, fieldId);
            ElMessage.warning(`${lockInfo?.nickname || lockInfo?.name || '其他用户'} 正在编辑此单元格，无法更改`);
            // 回退到原始状态（需要刷新表格）
            tableStore.refreshRecords(tableId);
            return;
          }

          // 尝试获取锁
          const lockResult = await collabStore.acquireLock(
            { base_id: baseId, table_id: tableId, record_id: recordId, field_id: fieldId },
            currentUserId
          );
          if (!lockResult.success && lockResult.reason === 'locked') {
            ElMessage.warning(`${lockResult.locked_by?.nickname || lockResult.locked_by?.name || '其他用户'} 正在编辑此单元格`);
            tableStore.refreshRecords(tableId);
            return;
          }
        }

        try {
          if (!tableId) return;

          // 乐观冲突检测：记录待提交变更
          if (collabStore.isRealtimeAvailable) {
            collabStore.trackPendingChange(recordId, fieldId, checked);
          }

          await recordService.updateRecord(recordId, {
            values: {
              ...originalRecord.values,
              [fieldId]: checked,
            } as Record<string, CellValue>,
          });

          // 保存成功，移除待提交变更
          if (collabStore.isRealtimeAvailable) {
            collabStore.removePendingChange(recordId, fieldId);
          }

          // 刷新表格数据
          await tableStore.refreshRecords(tableId);

          // 协同编辑：释放锁
          if (tableId && currentUserId && baseId && collabStore.isRealtimeAvailable) {
            collabStore.releaseLock({
              base_id: baseId,
              table_id: tableId,
              record_id: recordId,
              field_id: fieldId,
            });
          }
        } catch (error) {
          console.error('开关状态保存失败:', error);
          ElMessage.error('开关状态保存失败');
          // 保存失败也移除待提交变更，避免残留
          if (collabStore.isRealtimeAvailable) {
            collabStore.removePendingChange(recordId, fieldId);
          }
        }
      }
    }
  });

  // 注意：VTable 无 before_start_edit 事件，编辑锁检查已移至 click_cell 事件中
  // （配合 editCellTrigger: 'click' 配置，在编辑器启动前后介入）

  // 列宽调整结束：按列缓存宽度到 localStorage
  tableInstanceAny.on('resize_column_end', (args: any) => {
    console.log('[VTableView] resize_column_end 事件:', args);
    const colIndex = args.col;
    if (colIndex > 0) {
      const field = orderedVisibleFields.value[colIndex - 1];
      if (!field) {
        console.warn(`[VTableView] 列宽调整结束但找不到对应字段 col=${colIndex}`);
        return;
      }
      // 优先使用事件返回的列宽数组，其次回读当前列宽
      let newWidth: number | undefined = args.colWidths?.[colIndex];
      if (newWidth === undefined || typeof newWidth !== 'number') {
        newWidth = tableInstanceAny.getColWidth?.(colIndex);
      }
      if (typeof newWidth === 'number') {
        const targetWidth = Math.max(60, newWidth);
        columnWidths.value[field.id] = targetWidth;
        console.log(`[VTableView] 保存列宽 field=${field.id}(${field.name}) col=${colIndex} width=${targetWidth}`);
        saveColumnWidths();
      } else {
        console.warn(`[VTableView] 无法获取列宽 field=${field.id} col=${colIndex}`);
      }
    }
  });

  // 树形视图：索引列悬停显示 "+" 按钮
  if (isTreeView.value) {
    tableInstanceAny.on('mouseenter_cell', (args: any) => {
      if (!tableInstance) return;
      clearHideTreeAddChildIconTimer();
      const { col, row } = args;
      // col === 0 表示索引列
      if (col === 0 && !tableInstance.isHeader(col, row)) {
        const record = tableInstance.getCellOriginRecord(col, row);
        if (record && record._recordId && record._rowType !== 'addButton') {
          // 按钮固定在序号列右侧边界、当前行垂直居中，明确指向当前行
          const cellRect = tableInstance.getCellRect(col, row);
          if (!cellRect) return;
          const containerRect = tableContainerRef.value?.getBoundingClientRect();
          if (!containerRect) return;
          const iconX = containerRect.left + cellRect.left + cellRect.width - 10;
          const iconY = containerRect.top + cellRect.top + cellRect.height / 2;

          // 获取当前行主字段显示名（用于操作提示）
          let recordName = '';
          const primaryFieldId = tableStore.currentTable?.primaryFieldId;
          const original = record._originalRecord;
          if (primaryFieldId && original?.values?.[primaryFieldId] != null) {
            const rawName = original.values[primaryFieldId];
            if (String(rawName).trim() !== '') {
              recordName = String(rawName);
            }
          }

          treeAddChildIcon.value = {
            x: iconX,
            y: iconY,
            recordId: record._recordId,
            recordName,
          };
          treeAddChildIconVisible.value = true;
        }
      }
    });

    tableInstanceAny.on('mouseleave_cell', (args: any) => {
      const { col, row } = args;
      if (col === 0) {
        delayHideTreeAddChildIcon();
      }
    });
  }

  // 排序点击 —— 同步应用层排序状态，VTable 内置排序引擎通过自定义比较函数
  // (createSortComparator) 自动将 addButton 虚拟行保持在末尾
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

    // 同步应用层排序状态（sortedRecords computed 依赖此状态）
    const newSorts = newDirection ? [{ fieldId: field.id, direction: newDirection }] : [];
    if (newDirection) {
      ElMessage.success(`已按 ${field.name} ${newDirection === 'asc' ? '升序' : '降序'}排列`);
    } else {
      ElMessage.success(`已取消 ${field.name} 的排序`);
    }
    await viewStore.updateSorts(currentView.value.id, newSorts);
    // 不返回 false → VTable 内置排序正常执行，
    // 自定义比较函数确保 addButton 行始终在末尾
  });

  // 右键菜单 - 统一处理表头和单元格（VTable 的 contextmenu_cell 对所有单元格触发，包括表头）
  tableInstanceAny.on('contextmenu_cell', (args: any) => {
    const { col, row } = args;
    if (!tableInstance) return;

    const mouseEvent = args.event as MouseEvent | undefined;
    const clientX = mouseEvent?.clientX ?? 0;
    const clientY = mouseEvent?.clientY ?? 0;

    if (tableInstance.isHeader(col, row)) {
      // 表头右键菜单
      if (col <= 0) return; // 跳过行号列表头

      const field = orderedVisibleFields.value[col - 1];
      if (!field) return;

      contextMenuX.value = clientX;
      contextMenuY.value = clientY;
      contextMenuColumn.value = field;
      contextMenuTarget.value = "header";
      contextMenuRecord.value = null;
      contextMenuVisible.value = true;
    } else {
      // 数据行右键菜单
      const record = tableInstance.getCellOriginRecord(col, row);
      if (!record) return;

      // 跳过新增按钮行
      if (record._rowType === 'addButton') return;

      // 跳过分组标题行（没有原始数据记录）
      if (!record._originalRecord) return;

      contextMenuX.value = clientX;
      contextMenuY.value = clientY;
      contextMenuColumn.value = null;
      contextMenuTarget.value = "row";
      contextMenuRecord.value = record._originalRecord;
      contextMenuRow.value = row; // 保存行号
      // 同步更新冻结行数响应式变量（确保右键菜单状态正确）
      const headerRowCount = tableInstanceAny?.headerRowCount ?? 1;
      const internalFrozenCount = tableInstanceAny?.internalProps?.frozenRowCount ?? tableInstanceAny?.frozenRowCount ?? headerRowCount;
      frozenDataRowCount.value = Math.max(0, internalFrozenCount - headerRowCount);
      contextMenuVisible.value = true;
    }
  });

  // 单元格点击 - 使用 VTable API 获取单元格位置
  tableInstanceAny.on('click_cell', (args: any) => {
    // 点击图片缩略图时不触发单元格选择，预览由缩略图自身 pointertap 事件处理
    if (args.target?.name === 'attachment-thumbnail') {
      return;
    }

    // 检测是否为虚拟添加按钮行点击
    const clickedRecord = args.originData || args.record;
    if (clickedRecord && clickedRecord._rowType === 'addButton') {
      if (clickedRecord._groupValues) {
        // 分组模式：通过事件触发添加，父组件处理分组字段值
        emit('group-add-record', clickedRecord._groupValues);
      } else {
        // 非分组模式：直接创建新记录
        handleAddNewRecord();
      }
      return;
    }

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
        // 获取水平和垂直滚动偏移量，非冻结列需要减去 scrollLeft，所有行需要减去 scrollTop
        const scrollLeft = tableInstanceAny.scrollLeft || 0;
        const scrollTop = tableInstanceAny.scrollTop || 0;
        const frozenColCount = tableInstanceAny.frozenColCount || 1;
        const adjustedLeft = args.col < frozenColCount ? cellRect.left : cellRect.left - scrollLeft;
        const iconX = containerRect.left + adjustedLeft + cellRect.width + 8;
        const iconY = containerRect.top + cellRect.top - scrollTop;

        selectedCell.value = {
          col: args.col,
          row: args.row,
          record: cellRecord,
          x: Math.min(iconX, window.innerWidth - 40),
          y: Math.max(iconY, 4),
        };
        actionIconVisible.value = true;
      }

      // 协同编辑：进入编辑前检查并获取单元格锁
      // editCellTrigger: 'click' 配置下，VTable 在 click 时启动编辑器，
      // 因此在 click_cell 中接入锁逻辑（VTable 无 before_start_edit 事件）
      if (args.col > 0 && cellRecord?._recordId) {
        const fieldId = orderedVisibleFields.value[args.col - 1]?.id;
        if (fieldId) {
          const authStore = useAuthStore();
          const currentUserId = authStore.user?.id;
          const tableId = tableStore.currentTable?.id;
          const baseId = tableStore.currentTable?.baseId;

          if (tableId && currentUserId && baseId && collabStore.isRealtimeAvailable) {
            // 同步检查本地锁缓存：若被其他用户持有，立即取消编辑器并提示
            if (collabStore.isCellLockedByOther(cellRecord._recordId, fieldId, currentUserId)) {
              const lockInfo = collabStore.getCellLockInfo(cellRecord._recordId, fieldId);
              ElMessage.warning(`${lockInfo?.nickname || lockInfo?.name || '其他用户'} 正在编辑此单元格`);
              // 延迟一帧调用，确保在 VTable 启动编辑器之后取消
              setTimeout(() => {
                try { tableInstanceAny.cancelEditCell?.(); } catch (e) { /* ignore */ }
              }, 0);
            } else {
              // 异步获取锁；仅在真正被其他用户锁定时阻止编辑
              // （服务故障/超时等不阻塞，保证可用性）
              collabStore.acquireLock(
                { base_id: baseId, table_id: tableId, record_id: cellRecord._recordId, field_id: fieldId },
                currentUserId
              ).then((result) => {
                if (!result.success && result.reason === 'locked' && result.locked_by) {
                  ElMessage.warning(`${result.locked_by.nickname || result.locked_by.name || '其他用户'} 已锁定此单元格`);
                  try { tableInstanceAny.cancelEditCell?.(); } catch (e) { /* ignore */ }
                }
              });
            }
          }
        }
      }

      // URL 字段延时导航：单击等待 250ms 后跳转，双击时在 dblclick_cell 中取消
      if (args.col > 0) {
        const field = orderedVisibleFields.value[args.col - 1];
        if (field?.type === FieldType.URL) {
          const fieldValue = cellRecord?._originalRecord?.values?.[field.id] ?? cellRecord?.[field.id];
          if (fieldValue && typeof fieldValue === 'string' && fieldValue.trim()) {
            if (urlClickTimer) clearTimeout(urlClickTimer);
            urlClickTimer = setTimeout(() => {
              window.open(fieldValue, '_blank');
              urlClickTimer = null;
            }, 250);
          }
        }
      }
    }
  });

  // 单元格双击
  tableInstanceAny.on('dblclick_cell', (args: any) => {
    // 取消 URL 字段的延时导航（双击时不跳转，进入编辑模式）
    if (urlClickTimer) {
      clearTimeout(urlClickTimer);
      urlClickTimer = null;
    }

    const colIndex = args.col;
    const rowIndex = args.row;

    // 判断是否为附件类型字段
    if (colIndex > 0 && orderedVisibleFields.value[colIndex - 1]) {
      const field = orderedVisibleFields.value[colIndex - 1];
      if (field.type === FieldType.ATTACHMENT) {
        // 获取单元格位置，用于定位浮动面板
        const cellRect = (tableInstance as any)?.getCellRect(colIndex, rowIndex);
        const containerRect = tableContainerRef.value?.getBoundingClientRect();
        if (cellRect && containerRect) {
          // 使用 VTable getCellOriginRecord API 可靠获取原始记录（与 change_cell_value 共用同一模式）
          const cellRecord = (tableInstance as any)?.getCellOriginRecord?.(colIndex, rowIndex);
          if (!cellRecord) return;

          // 获取水平和垂直滚动偏移量，非冻结列/行需要减去 scrollLeft/scrollTop 以修正位置
          const scrollLeft = (tableInstance as any).scrollLeft || 0;
          const scrollTop = (tableInstance as any).scrollTop || 0;
          const frozenColCount = (tableInstance as any).frozenColCount || 1;
          const adjustedLeft = colIndex < frozenColCount ? cellRect.left : cellRect.left - scrollLeft;

          // 基准位置：单元格右下角（垂直需减去 scrollTop 修正）
          let panelX = containerRect.left + adjustedLeft + cellRect.width;
          let panelY = containerRect.top + cellRect.bottom - scrollTop;

          // 视口边界检测：浮窗宽度约 380px，高度约 480px
          const panelWidth = 380;
          const panelHeight = 480;
          // 水平方向：如果超出右侧，则改为在单元格左侧显示
          if (panelX + panelWidth > window.innerWidth - 16) {
            panelX = containerRect.left + adjustedLeft - panelWidth;
          }
          // 垂直方向：如果超出底部，则改为在单元格上方显示（使用修正后的 top）
          if (panelY + panelHeight > window.innerHeight - 16) {
            panelY = containerRect.top + cellRect.top - scrollTop - panelHeight;
          }
          // 水平不超出左边界
          if (panelX < 8) {
            panelX = 8;
          }
          // 垂直不超出上边界
          if (panelY < 8) {
            panelY = 8;
          }

          attachmentManagerPosition.value = {
            x: panelX,
            y: panelY,
          };
          attachmentManagerField.value = field;
          attachmentManagerRecordId.value = cellRecord._recordId || cellRecord._originalRecord?.id || '';
          attachmentManagerInitialValue.value = cellRecord[field.id] ?? cellRecord._originalRecord?.values?.[field.id] ?? null;
          attachmentManagerOriginalRecord.value = cellRecord._originalRecord || null;
          attachmentManagerVisible.value = true;
          // 记录触发单元格的位置偏移量，用于滚动实时更新
          lastAttachmentCellCoords.value = { col: colIndex, row: rowIndex };
          return;
        }
      }
      // 关联字段：打开记录选择器
      if (field.type === FieldType.LINK) {
        const cellRecord = (tableInstance as any)?.getCellOriginRecord?.(colIndex, rowIndex);
        if (!cellRecord) return;
        const recordId = cellRecord._recordId || cellRecord._originalRecord?.id || '';
        const rawValue = cellRecord[field.id] ?? cellRecord._originalRecord?.values?.[field.id] ?? [];

        // 解析当前选中的记录 ID
        let currentIds: string[] = [];
        if (Array.isArray(rawValue)) {
          currentIds = rawValue.map((id: any) => String(id));
        }

        // 判断是否允许多选（自关联字段强制单选：每个子记录仅能有一个父级）
        const relationshipType = field.options?.relationshipType || field.options?.relationship_type || field.config?.relationshipType || field.config?.relationship_type || 'many_to_many';
        const targetTableId = (field.options?.linkedTableId || field.options?.linked_table_id || field.config?.linkedTableId || field.config?.linked_table_id || '') as string;
        const isSelfLink = targetTableId === props.tableId;
        const allowMultiple = !isSelfLink && relationshipType !== 'one_to_one' && relationshipType !== 'many_to_one';

        linkSelectorTargetTableId.value = targetTableId;
        linkSelectorDisplayFieldId.value = (field.options?.displayFieldId || field.options?.display_field_id || field.config?.displayFieldId || field.config?.display_field_id || '') as string;
        linkSelectorSelectedIds.value = currentIds;
        linkSelectorFieldId.value = field.id;
        linkSelectorRecordId.value = recordId;
        linkSelectorAllowMultiple.value = allowMultiple;
        linkSelectorExcludeRecordId.value = isSelfLink ? recordId : '';

        // 构建 linkedRecords：从缓存中获取已选记录的 display_value
        const linkedRecords: { record_id: string; display_value: string }[] = [];
        if (currentIds.length > 0) {
          const cacheKey = `${recordId}:${field.id}`;
          const cachedDVs = linkDisplayCache[cacheKey] || [];
          // 先按缓存顺序配对（缓存是从 API response 按序提取的）
          // 再对未在缓存中的 ID 使用 ID 本身作为回退
          for (let i = 0; i < currentIds.length; i++) {
            const id = currentIds[i];
            linkedRecords.push({
              record_id: id,
              display_value: cachedDVs[i] || id,
            });
          }
        }
        linkSelectorLinkedRecords.value = linkedRecords;

        linkSelectorVisible.value = true;
        return;
      }
    }
    // 非附件/关联字段，保持原有行为
    if (args.record && args.record._originalRecord) {
      handleExpandRecord(args.record._originalRecord);
    }
  });

  // 表格滚动事件 - 实时更新附件浮窗位置
  tableInstanceAny.on('scroll', (_args: any) => {
    // 更新附件浮窗
    if (attachmentManagerVisible.value && lastAttachmentCellCoords.value) {
      const { col, row } = lastAttachmentCellCoords.value;
      const pos = recalcFloatingPanelPosition(col, row, 380, 480);
      if (pos) attachmentManagerPosition.value = pos;
    }
    // 实时更新子表工具栏位置
    if (subTableToolbarVisible.value) {
      updateSubTableToolbarPosition();
    }
  });

  // 单元格值变更事件
  // 注意：VTable 1.26.1 的 change_cell_value 事件参数为 { col, row, changedValue, rawValue, currentValue }
  // 不含 record 字段，需要通过 getCellOriginRecord 查找记录
  tableInstanceAny.on('change_cell_value', async (args: any) => {
    if (!args || !tableInstance) return;

    const { col, row } = args;
    // 跳过行号列
    if (col <= 0) return;

    // 防抖：同一单元格短时间内可能触发多次事件（编辑器退出时的 bug）
    const cellKey = `${col}:${row}`;
    if (processingCellKey === cellKey) return;
    processingCellKey = cellKey;
    if (processingCellTimer) {
      clearTimeout(processingCellTimer);
    }
    processingCellTimer = setTimeout(() => {
      processingCellKey = null;
      processingCellTimer = null;
    }, 500);

    const record = tableInstance.getCellOriginRecord(col, row);
    if (!record?._recordId || !record._originalRecord) return;
    
    const recordId = record._recordId;
    const fieldId = orderedVisibleFields.value[col - 1]?.id;
    if (!fieldId) return;
    
    const newValue = args.changedValue ?? args.currentValue;
    const originalRecord = record._originalRecord;

    // 字段值类型转换：VTable 内置编辑对日期/日期时间字段返回时间戳，需转为字符串格式
    const targetField = orderedVisibleFields.value[col - 1] ?? null;
    let finalValue = newValue;
    if (targetField?.type && typeof finalValue === 'number') {
      if (targetField.type === FieldType.DATE) {
        // 时间戳 → YYYY-MM-DD 日期字符串，确保与服务端格式一致
        const date = new Date(finalValue);
        const year = date.getFullYear();
        const month = String(date.getMonth() + 1).padStart(2, '0');
        const day = String(date.getDate()).padStart(2, '0');
        finalValue = `${year}-${month}-${day}`;
      } else if (targetField.type === FieldType.DATE_TIME) {
        // 时间戳 → UTC ISO 字符串 (2026-06-19T16:02:00.000Z)
        finalValue = new Date(finalValue).toISOString();
      }
    }

    // ==================== 字段值校验 ====================
    if (targetField) {
      const validation = validateCellValue(finalValue, targetField);
      if (!validation.valid) {
        // 校验失败：标记红色高亮 + 警告提示，不执行保存
        markCellError(col, row, fieldId, validation.message!);
        ElMessage.warning(validation.message);
        return;
      }
    }
    // 校验通过，清除该单元格可能存在的错误标记
    clearCellError(col, row);
    
    const authStore = useAuthStore();
    const currentUserId = authStore.user?.id;
    const tableId = tableStore.currentTable?.id;
    const baseId = tableStore.currentTable?.baseId;

    // 协同编辑：检查锁状态，如果被其他用户锁定则阻止保存
    if (tableId && currentUserId && baseId && collabStore.isRealtimeAvailable) {
      if (collabStore.isCellLockedByOther(recordId, fieldId, currentUserId)) {
        const lockInfo = collabStore.getCellLockInfo(recordId, fieldId);
        ElMessage.warning(`${lockInfo?.nickname || lockInfo?.name || '其他用户'} 正在编辑此单元格，保存被拒绝`);
        // 刷新表格以显示原始数据
        if (tableId) {
          await tableStore.refreshRecords(tableId);
        }
        return;
      }
    }

    // ==================== 无改动检查 ====================
    const originalValue = originalRecord.values[fieldId];
    const normalizeValue = (v: unknown): string | null => {
      if (v == null || v === '') return null;
      return String(v);
    };
    if (normalizeValue(finalValue) === normalizeValue(originalValue)) {
      // 值无实际变化，不触发保存
      return;
    }

    try {
      if (!tableId) return;

      const values = {
        ...originalRecord.values,
        [fieldId]: finalValue,
      };

      // 乐观冲突检测：记录待提交变更
      if (collabStore.isRealtimeAvailable) {
        collabStore.trackPendingChange(recordId, fieldId, finalValue);
      }

      await recordService.updateRecord(recordId, {
        values: values as Record<string, CellValue>,
      });

      // 保存成功，移除待提交变更
      if (collabStore.isRealtimeAvailable) {
        collabStore.removePendingChange(recordId, fieldId);
      }

      // 不再手动刷新表格数据，让实时协作监听器（onRecordUpdated）处理
      // 如果实时协作不可用，才手动刷新
      if (!collabStore.isRealtimeAvailable) {
        await tableStore.refreshRecords(tableId);
        // 树形视图下重新构建树（层级可能因父级字段变化而改变）
        if (isTreeView.value) {
          await loadTreeRecords();
        }
      }

      // 协同编辑：保存成功后释放锁
      if (tableId && currentUserId && baseId && collabStore.isRealtimeAvailable) {
        collabStore.releaseLock({
          base_id: baseId,
          table_id: tableId,
          record_id: recordId,
          field_id: fieldId,
        });
      }

      ElMessage.success('编辑保存成功');
    } catch (error) {
      console.error('编辑保存失败:', error);
      ElMessage.error('编辑保存失败');
      // 保存失败也移除待提交变更，避免残留
      if (collabStore.isRealtimeAvailable) {
        collabStore.removePendingChange(recordId, fieldId);
      }
    }
  });

  // 复制事件 - 使用 VTable 原生复制功能，仅提供操作反馈
  tableInstanceAny.on('copy_data', (args: any) => {
    const ranges: Array<{ start: { col: number; row: number }; end: { col: number; row: number } }> = args?.cellRange ?? [];
    let cellCount = 0;
    for (const range of ranges) {
      const cols = range.end.col - range.start.col + 1;
      const rows = range.end.row - range.start.row + 1;
      cellCount += cols * rows;
    }
    if (cellCount > 0) {
      ElMessage.success(`已复制 ${cellCount} 个单元格`);
    }
  });

  // ==================== 主从表事件 ====================
  // 懒加载：展开行时异步获取关联记录
  tableInstanceAny.on('tree_hierarchy_state_change', async (args: any) => {
    if (hasLinkFields.value && !isTreeView.value && tableInstance) {
      await handleLazyLoad(args, tableInstance);
      // 展开后显示子表工具栏
      if (args.hierarchyState === 'expand') {
        subTableToolbarVisible.value = true;
        subTableToolbarRecordId.value = args.originData?._originalRecord?.id || args.originData?._recordId || '';
        subTableToolbarCol.value = args.col;
        subTableToolbarRow.value = args.row;
        // 检查一对一关系禁用状态
        updateSubTableDisabledAdd();
        // 等待子表渲染完成后计算工具栏位置
        requestAnimationFrame(() => {
          requestAnimationFrame(() => {
            updateSubTableToolbarPosition();
          });
        });
      } else if (args.hierarchyState === 'collapse') {
        // 收起时隐藏工具栏
        subTableToolbarVisible.value = false;
        subTableToolbarRecordId.value = '';
      }
    }
  });

  // 子表事件转发处理
  tableInstanceAny.on('plugin_event', (args: any) => {
    handleSubTableEvent(args);
  });

  // 树形视图：拖拽记录改变层级关系
  if (isTreeView.value) {
    let dragSourceRecordId: string | null = null;
    let dragSourceRow: number = -1;

    // 拖拽开始：记录拖拽源
    tableInstanceAny.on('drag_select_end', (args: any) => {
      if (!tableInstance) return;
      const { col, row } = args;
      if (col === 0 && !tableInstance.isHeader(col, row)) {
        const record = tableInstance.getCellOriginRecord(col, row);
        if (record && record._recordId && record._rowType !== 'addButton') {
          dragSourceRecordId = record._recordId;
          dragSourceRow = row;
        }
      }
    });

    // 拖拽结束：检测放置位置并更新层级
    tableInstanceAny.on('dropdown_menu_close', () => {
      // 重置拖拽状态
      dragSourceRecordId = null;
      dragSourceRow = -1;
    });

    // 监听鼠标释放事件作为拖拽放置的检测
    tableInstanceAny.on('mouseup_cell', async (args: any) => {
      if (!dragSourceRecordId || !parentFieldId.value || !tableInstance) return;
      const { col, row } = args;
      // 目标行不能是原始行
      if (row === dragSourceRow) {
        dragSourceRecordId = null;
        dragSourceRow = -1;
        return;
      }
      if (col === 0 && !tableInstance.isHeader(col, row)) {
        const targetRecord = tableInstance.getCellOriginRecord(col, row);
        if (targetRecord && targetRecord._recordId && targetRecord._rowType !== 'addButton') {
          const targetId = targetRecord._recordId;
          // 避免将记录设为自身的子记录
          if (targetId === dragSourceRecordId) {
            dragSourceRecordId = null;
            dragSourceRow = -1;
            return;
          }
          try {
            // 更新拖拽记录的父记录字段为目标记录
            await recordService.updateRecord(dragSourceRecordId, {
              values: { [parentFieldId.value]: [targetId] } as Record<string, CellValue>,
            });
            await loadTreeRecords();
            ElMessage.success("已更新层级关系");
          } catch (error) {
            console.error("拖拽更新层级失败:", error);
            ElMessage.error("拖拽更新层级失败");
          }
        }
      }
      dragSourceRecordId = null;
      dragSourceRow = -1;
    });
  }
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
    // 释放旧 VTable 实例，避免事件监听器泄漏导致重复触发
    if (tableInstance) {
      try {
        (tableInstance as any).release();
      } catch (_e) {
        // 释放失败不影响重建
      }
      tableInstance = null;
    }
    if (tableContainerRef.value) {
      tableContainerRef.value.innerHTML = '';
    }

    // 重新检测 LINK 字段并创建插件（树形视图下禁用主从表）
    detectLinkFields(fields.value);
    if (hasLinkFields.value && !isTreeView.value) {
      setColumnEnhancer(enhanceSubTableColumns);
      setRecordTransformer(transformSubTableRecords);
      // 使用与主表一致的定制主题
      const subTableTheme = themes.DEFAULT.extends({
        scrollStyle: { barToSide: true, visible: 'always' },
        headerStyle: { color: '#646A73', fontSize: 13 },
        bodyStyle: { color: '#374151' },
      });
      createPluginInstance(subTableTheme);
    }

    const config = buildTableConfig();
    tableInstance = new ListTable(tableContainerRef.value, config);
    bindTableEvents();

    // 应用缓存的列宽
    applyColumnWidths();
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

// 增量更新表格数据（仅数据变更，列结构不变时使用）
// 避免销毁重建 VTable，直接更新 CachedDataSource 缓存后轻量重绘
let isUpdatingData = false;
let pendingDataUpdate = false;
const updateTableData = () => {
  if (!tableInstance || !tableContainerRef.value) return;
  if (isUpdatingData) {
    pendingDataUpdate = true;
    return;
  }

  const isGrouped = props.groupBy && props.groupBy.length > 0;
  isUpdatingData = true;
  pendingDataUpdate = false;

  try {
    if (isTreeView.value || isGrouped) {
      // 树形视图或分组模式：必须全量重建，增量更新无法处理树形结构
      updateTable();
    } else if (smartDataSource) {
      // 非分组 CachedDataSource 模式：更新内存缓存 + 轻量重绘
      clearTransformCache(); // 清除转换缓存，确保 transformRecords 不会从缓存返回旧行
      const newRows = transformRecords(sortedRecords.value);

      // 非分组模式下追加「+ 添加记录」虚拟行，与 buildTableConfig 中的逻辑保持一致
      // 若不追加，watcher 触发 updateTableData 时会用纯记录数据覆盖 smartDataSource 缓存，
      // 导致表格中的 addButton 行消失（这是刷新后按钮闪烁消失的根因）
      if ((!props.groupBy || props.groupBy.length === 0) && !props.readonly) {
        const addButtonRecord: any = {
          _recordId: '__add_button__',
          _originalRecord: null,
          _rowType: 'addButton',
        };
        orderedVisibleFields.value.forEach(f => { addButtonRecord[f.id] = ''; });
        newRows.push(addButtonRecord);
      }

      smartDataSource.clearCache();
      smartDataSource.updateMemoryCache(newRows, 0);
      smartDataSource.markFullyLoaded();
      (tableInstance as any).renderWithRecreateCells();
    } else {
      // 无 dataSource，回退全量重建
      updateTable();
      // 全量重建已包含最新数据（含 addButton 行），
      // 清除重建期间可能累积的 pendingDataUpdate，避免 finally 中重入导致二次覆盖
      pendingDataUpdate = false;
    }
  } catch (error) {
    console.error('增量数据更新失败:', error);
    // 回退到全量重建
    updateTable();
  } finally {
    isUpdatingData = false;
    if (pendingDataUpdate) {
      updateTableData();
    }
  }
};

// 实时协作事件监听
const realtimeHandlers: Array<{ event: string; handler: (...args: unknown[]) => void }> = [];

const setupRealtimeListeners = () => {
  if (!collabStore.isRealtimeAvailable) return;

  const onRecordUpdated = (data: DataRecordUpdatedBroadcast) => {
    if (data.table_id !== props.tableId) return;
    // 树形视图下重新构建树（层级可能因父级字段变化而改变）
    if (isTreeView.value) {
      setTimeout(loadTreeRecords, 100);
    } else {
      setTimeout(updateTable, 100);
    }
  };

  const onRecordCreated = (data: DataRecordCreatedBroadcast) => {
    if (data.table_id !== props.tableId) return;
    if (isTreeView.value) {
      setTimeout(loadTreeRecords, 100);
    } else {
      setTimeout(updateTable, 100);
    }
  };

  const onRecordDeleted = (data: DataRecordDeletedBroadcast) => {
    if (data.table_id !== props.tableId) return;
    if (isTreeView.value) {
      setTimeout(loadTreeRecords, 100);
    } else {
      setTimeout(updateTable, 100);
    }
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

/** 取消流式数据加载 */
const handleCancelLoading = () => {
  tableStore.cancelLoading();
};

/** 预加载所有成员字段的用户信息 */
async function preloadMemberUsers() {
  const allRecords = tableStore.records;
  const allFields = tableStore.fields;
  if (!allRecords.length || !allFields.length) return;

  const memberFields = allFields.filter(f => f.type === FieldType.MEMBER);
  if (memberFields.length === 0) return;

  const memberIds = new Set<string>();
  allRecords.forEach(record => {
    memberFields.forEach(field => {
      const rawVal = record.values[field.id];
      if (!rawVal) return;
      let mems: any[] = [];
      if (Array.isArray(rawVal)) mems = rawVal;
      else if (typeof rawVal === 'string') {
        try { const p = JSON.parse(rawVal); if (Array.isArray(p)) mems = p; } catch {}
      } else if (typeof rawVal === 'object' && rawVal !== null) {
        mems = [rawVal];
      }
      mems.forEach((m: any) => {
        const id = typeof m === 'string' ? m : String(m?.id || m?.user_id || '');
        if (id && id !== 'current_user') memberIds.add(id);
      });
    });
  });

  if (memberIds.size === 0) return;

  try {
    await userCacheStore.fetchUsers(Array.from(memberIds));
    // fetchUsers 完成后，手动清除转换缓存
    // 注意：不在此处调用 updateTableData()，避免与 watcher 末尾的 updateTableData() 构成二次调用。
    // watcher 的调用顺序是：preloadMemberUsers (async yields) → updateTableData (重建) → fetchUsers resolves
    // → preloadMemberUsers 恢复 → 这里再调用 updateTableData 会导致 smartDataSource 路径 clearCache 覆盖正确数据。
    clearTransformCache();
  } catch (error) {
    console.error('[VTableView] 预加载成员信息失败:', error);
  }
}

// 监听 records 变化 → 统一数据更新入口
// 覆盖所有场景：handleAddNewRecord / handleDuplicateRecord / realtime broadcast / 外部操作
watch(() => tableStore.records, async () => {
  if (!tableInstance) return;

  // 树形视图：记录由 tree-records API 管理，跳过 flat records 更新逻辑
  if (isTreeView.value) return;

  // 等待 Vue 响应式链路传播完毕：
  // tableStore.records → 父组件 filteredRecords → props.records → sortedRecords
  // 不等 nextTick 的话，sortedRecords.value 可能还是旧值，导致行数判断错误
  await nextTick();

  // 清理已不存在的记录选中状态，避免删除/刷新后右键菜单计数错误
  const validRecordIds = new Set(sortedRecords.value.map(r => r.id));
  if (selectedRows.value.some(id => !validRecordIds.has(id))) {
    selectedRows.value = selectedRows.value.filter(id => validRecordIds.has(id));
  }
  if (checkboxSelectedRows.value.some(id => !validRecordIds.has(id))) {
    checkboxSelectedRows.value = checkboxSelectedRows.value.filter(id => validRecordIds.has(id));
  }

  clearTransformCache();

  if (!smartDataSource) {
    // 无缓存数据源：走全量重建（首次加载或上一次已销毁）
    preloadMemberUsers();
    updateTableData();
    return;
  }

  const prevTotal = smartDataSource.totalCount;
  // 当前应有的总行数 = 真实记录数 + (非分组非只读时 +1 的 addButton 行)
  const currentRecordCount = sortedRecords.value.length;
  const hasAddButton = (!props.groupBy || props.groupBy.length === 0) && !props.readonly;
  const expectedTotal = hasAddButton ? currentRecordCount + 1 : currentRecordCount;

  if (expectedTotal !== prevTotal) {
    // 行数变化（新增/删除记录）：CachedDataSource.length 在构造时固定，
    // 增量更新无法让 VTable 感知行数变化，必须全量重建
    const isAdding = expectedTotal > prevTotal; // 记录是否为新增操作

    updateTable();

    // 新增记录后自动滚动到最后一行真实记录，方便用户立即编辑
    if (isAdding && tableInstance && hasAddButton && currentRecordCount > 0) {
      // 等待 VTable DOM 渲染完成后再滚动
      await nextTick();
      // 新增的真实记录在倒数第二行（最后一行是 addButton 虚拟行）
      try {
        (tableInstance as any).scrollToRow(currentRecordCount - 1);
      } catch (_e) {
        // 滚动失败不影响主流程，静默忽略
      }
    }
  } else {
    // 行数不变（编辑单元格、成员名称加载等）：增量更新缓存并重绘
    preloadMemberUsers();
    updateTableData();
  }
}, { deep: true });

// 监听 fields 变化 → 列结构变更，需重建表格
watch(() => tableStore.fields, () => {
  // 字段配置（含关联字段的 displayFieldId）可能变化，清空关联显示缓存
  for (const key of Object.keys(linkDisplayCache)) {
    delete linkDisplayCache[key];
  }
  for (const key of Object.keys(linkLoadingStates)) {
    delete linkLoadingStates[key];
  }
  for (const key of Object.keys(linkErrorStates)) {
    delete linkErrorStates[key];
  }
  updateTable();
}, { deep: true });

watch(() => viewStore.currentView, () => {
  // 仅响应当前组件所属表格的视图变化，避免表格切换时旧实例误响应全局 currentView
  if (!viewStore.currentView || viewStore.currentView.tableId !== props.tableId) {
    return;
  }
  if (isTreeView.value) {
    loadTreeRecords();
  } else {
    treeRecords.value = [];
    updateTable();
  }
}, { deep: true });

// 表格切换时重新加载对应缓存列宽
watch(() => props.tableId, (newTableId, oldTableId) => {
  if (newTableId && newTableId !== oldTableId) {
    initColumnWidths();
    updateTable();
  }
});

// 视图切换时重新加载对应缓存列宽
watch(() => props.viewId, (newViewId, oldViewId) => {
  if (newViewId && newViewId !== oldViewId) {
    initColumnWidths();
    updateTable();
  }
});

watch(selectedRows, () => {
  // 选中行变化不需要重建表格，VTable 内建选中高亮机制处理视觉更新
}, { deep: true });

// 用户缓存更新时刷新表格（成员名称异步加载完成后重渲染）
watch(() => userCacheStore.cacheStats.size, () => {
  // 成员名称变更需清除转换缓存，强制重算 MEMBER 字段
  clearTransformCache();
  updateTableData();
});

// 监听流式加载完成：标记 fullyLoaded，交由 records watch 完成重建
watch(() => tableStore.streamingState.isLoading, (wasLoading, isLoading) => {
  if (wasLoading && !isLoading && smartDataSource) {
    smartDataSource.markFullyLoaded();
    
  }
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
  window.addEventListener('resize', handleFloatingPanelWindowResize);
  // 初始加载时预加载成员字段的用户信息
  preloadMemberUsers();
});

onBeforeUnmount(() => {
  // 标记组件已销毁，阻止异步回调（watch / 实时监听）继续触发接口请求
  isComponentDestroyed.value = true;
  // 释放所有持有的协同编辑锁
  const tableId = tableStore.currentTable?.id;
  const baseId = tableStore.currentTable?.baseId;
  if (tableId && baseId && collabStore.isRealtimeAvailable) {
    collabStore.releaseAllCurrentLocks(baseId, tableId);
  }
  cleanupRealtimeListeners();
  // 清理主从表
  disposeMasterDetail();
  document.removeEventListener('click', handleDocumentClick);
  window.removeEventListener('resize', handleFloatingPanelWindowResize);
  if (addRecordCooldownTimer) {
    clearTimeout(addRecordCooldownTimer);
    addRecordCooldownTimer = null;
  }
  if (tableInstance) {
    try {
      (tableInstance as any).release();
    } catch (_e) {
      // 释放失败不影响卸载
    }
    if (tableContainerRef.value) {
      tableContainerRef.value.innerHTML = '';
    }
    tableInstance = null;
  }
});

defineExpose({
  selectedRows,
  openSearch,
  refresh: () => {
    updateTable();
  },
});

// 附件管理器：关闭
function closeAttachmentManager() {
  attachmentManagerVisible.value = false;
  attachmentManagerField.value = null;
  attachmentManagerRecordId.value = '';
  attachmentManagerInitialValue.value = null;
  attachmentManagerOriginalRecord.value = null;
  lastAttachmentCellCoords.value = null;
}

// 窗口 resize 事件 - 重新定位附件浮窗
function handleFloatingPanelWindowResize() {
  // 更新附件浮窗
  if (attachmentManagerVisible.value && lastAttachmentCellCoords.value) {
    const { col, row } = lastAttachmentCellCoords.value;
    const pos = recalcFloatingPanelPosition(col, row, 380, 480);
    if (pos) attachmentManagerPosition.value = pos;
  }
}

// 附件管理器：值变更保存
async function handleAttachmentUpdate(value: any) {
  if (!attachmentManagerRecordId.value || !attachmentManagerField.value || !props.tableId) return;
  const fieldId = attachmentManagerField.value.id;
  const originalRecord = attachmentManagerOriginalRecord.value;
  if (!originalRecord?.values) return;

  const originalValue = originalRecord.values[fieldId];
  try {
    const newValues = { ...originalRecord.values, [fieldId]: value };
    await recordService.updateRecord(attachmentManagerRecordId.value, {
      values: newValues as Record<string, CellValue>,
    });
    // 更新本地原始记录快照，避免重复保存时使用旧值
    attachmentManagerOriginalRecord.value = {
      ...originalRecord,
      values: newValues as Record<string, CellValue>,
    };
    await tableStore.refreshRecords(props.tableId);
    ElMessage.success('附件保存成功');
  } catch (error) {
    console.error('附件保存失败:', error);
    ElMessage.error('附件保存失败');
    // 恢复原始值，使 AttachmentManager 重新加载为删除前的状态
    attachmentManagerInitialValue.value = originalValue;
  }
}

// ==================== 关联字段数据加载 ====================
// 批量加载所有可见 LINK 字段的关联记录 display_value
async function loadLinkDisplayData() {
  const linkFields = orderedVisibleFields.value.filter(f => f.type === FieldType.LINK);
  if (linkFields.length === 0) return;

  // 收集所有需要加载的 (recordId, fieldId) 对
  const needsLoad: Array<{ recordId: string; fieldId: string }> = [];

  for (const record of sortedRecords.value) {
    for (const field of linkFields) {
      const key = `${record.id}:${field.id}`;
      if (linkDisplayCache[key] !== undefined) continue; // 已有缓存
      // 字段有值（目标记录ID数组）才加载
      const rawVal = record.values?.[field.id];
      if (rawVal && Array.isArray(rawVal) && rawVal.length > 0) {
        needsLoad.push({ recordId: record.id, fieldId: field.id });
        linkLoadingStates[key] = true; // 标记加载中
        linkErrorStates[key] = '';     // 清除旧错误
      } else {
        linkDisplayCache[key] = [];    // 空缓存
      }
    }
  }

  if (needsLoad.length === 0) return;

  // 按 recordId 分组去重，每条记录只调一次 API
  const recordIds = [...new Set(needsLoad.map(n => n.recordId))];

  try {
    const results = await Promise.allSettled(
      recordIds.map(recordId => linkApiService.getRecordLinks(recordId))
    );

    for (let i = 0; i < recordIds.length; i++) {
      const recordId = recordIds[i];
      const result = results[i];

      if (result.status === 'rejected') {
        // 该记录下所有字段标记错误
        for (const n of needsLoad.filter(n => n.recordId === recordId)) {
          const key = `${recordId}:${n.fieldId}`;
          linkErrorStates[key] = result.reason?.message || '加载关联数据失败';
          linkLoadingStates[key] = false;
        }
        continue;
      }

      const linkData = result.value;

      // 遍历该记录下需要加载的 LINK 字段
      for (const n of needsLoad.filter(n => n.recordId === recordId)) {
        const key = `${recordId}:${n.fieldId}`;
        // 从 outbound 中找到匹配的字段
        const outbound = linkData.outbound.find(o => o.field_id === n.fieldId);
        if (outbound && outbound.linked_records.length > 0) {
          linkDisplayCache[key] = outbound.linked_records.map(lr => lr.display_value);
        } else {
          linkDisplayCache[key] = [];
        }
        linkLoadingStates[key] = false;
      }
    }
  } catch (error) {
    for (const n of needsLoad) {
      const key = `${n.recordId}:${n.fieldId}`;
      linkErrorStates[key] = '加载关联数据失败';
      linkLoadingStates[key] = false;
    }
  }

  // 缓存更新后触发 VTable 重渲染，确保 fieldFormat 读取最新缓存
  if (needsLoad.length > 0 && tableInstance) {
    try {
      (tableInstance as any).renderWithRecreateCells();
    } catch {}
  }
}

// ==================== 关联记录选择器事件处理 ====================
// 确认选择关联记录后保存
async function handleLinkSelectorConfirm(selectedIds: string[]) {
  if (!linkSelectorRecordId.value || !linkSelectorFieldId.value || !props.tableId) {
    linkSelectorVisible.value = false;
    return;
  }

  const recordId = linkSelectorRecordId.value;
  const fieldId = linkSelectorFieldId.value;

  try {
    await linkApiService.updateRecordLink(recordId, fieldId, {
      target_record_ids: selectedIds,
    });

    // 立即更新本地记录值，确保单元格能及时渲染新选的关联记录
    const recordIndex = tableStore.records.findIndex(r => r.id === recordId);
    if (recordIndex !== -1) {
      const existingRecord = tableStore.records[recordIndex];
      const updatedRecord: RecordEntity = {
        ...existingRecord,
        values: { ...existingRecord.values, [fieldId]: [...selectedIds] },
        updatedAt: Date.now(),
      };
      tableStore.records[recordIndex] = updatedRecord;

      // 同步更新 IndexedDB，避免刷新后数据回退
      try {
        await db.records.update(recordId, {
          values: serializeRecordValues(updatedRecord.values),
          updatedAt: updatedRecord.updatedAt,
        });
      } catch (dbError) {
        console.warn('[VTableView] 更新本地 IndexedDB 关联字段值失败:', dbError);
      }
    }

    // 刷新缓存和数据
    const cacheKey = `${recordId}:${fieldId}`;
    delete linkDisplayCache[cacheKey];
    delete linkLoadingStates[cacheKey];
    delete linkErrorStates[cacheKey];

    await tableStore.refreshRecords(props.tableId);

    // 树形视图下重新构建树（父级字段可能变化，层级需要重排）
    if (isTreeView.value) {
      await loadTreeRecords();
    }

    // 显式重新加载关联显示数据，确保新选择的记录立即显示
    await loadLinkDisplayData();
  } catch (error) {
    console.error('更新关联字段失败:', error);
    ElMessage.error('更新关联字段失败');
  }

  linkSelectorVisible.value = false;
  // 如果是子表触发的添加关联，刷新子表
  if (subTableToolbarRecordId.value === recordId && tableInstance) {
    await refreshSubTable(recordId, subTableToolbarCol.value, subTableToolbarRow.value, tableInstance);
  }
}

function handleLinkSelectorCancel() {
  linkSelectorVisible.value = false;
  linkSelectorExcludeRecordId.value = '';
}

// ==================== 子表操作处理 ====================
// 子表添加关联记录
async function handleSubTableAddLink() {
  if (!subTableToolbarRecordId.value || !currentLinkFieldId.value) return;

  const fieldId = currentLinkFieldId.value;
  const field = fields.value.find(f => f.id === fieldId);
  if (!field) return;

  const targetTableId = (field.options?.linkedTableId || field.config?.linkedTableId || '') as string;
  if (!targetTableId) return;

  // 获取当前已关联的记录ID（用于排除）
  const recordId = subTableToolbarRecordId.value;
  const record = tableStore.records.find(r => r.id === recordId);
  const existingIds = (record?.values?.[fieldId] as string[]) || [];

  // 复用现有的 LinkRecordSelector
  linkSelectorRecordId.value = recordId;
  linkSelectorFieldId.value = fieldId;
  linkSelectorTargetTableId.value = targetTableId;
  linkSelectorDisplayFieldId.value = (field.options?.displayFieldId || '') as string;
  linkSelectorSelectedIds.value = [...existingIds];
  linkSelectorAllowMultiple.value = field.options?.relationshipType !== 'one_to_one';
  linkSelectorExcludeRecordId.value = ''; // 子表场景非自关联，无需排除
  linkSelectorLinkedRecords.value = existingIds.map(id => ({ record_id: id, display_value: '' }));
  linkSelectorVisible.value = true;
}

// 子表切换 LINK 字段
async function handleSubTableSwitchField(fieldId: string) {
  await switchLinkField(fieldId);
  // 刷新当前展开的子表
  if (subTableToolbarRecordId.value && tableInstance) {
    await refreshSubTable(subTableToolbarRecordId.value, subTableToolbarCol.value, subTableToolbarRow.value, tableInstance);
  }
}

// 子表刷新
async function handleSubTableRefresh() {
  if (!subTableToolbarRecordId.value || !tableInstance) return;
  await refreshSubTable(subTableToolbarRecordId.value, subTableToolbarCol.value, subTableToolbarRow.value, tableInstance);
  // 刷新后检查一对一关系禁用状态
  updateSubTableDisabledAdd();
}

// 子表解除关联
async function handleSubTableUnlink(targetRecordId: string) {
  if (!subTableToolbarRecordId.value || !currentLinkFieldId.value || props.readonly) return;

  try {
    await ElMessageBox.confirm(
      '确定要解除与该记录的关联吗？',
      '确认解除关联',
      {
        confirmButtonText: '确认解除',
        cancelButtonText: '取消',
        type: 'warning',
      },
    );

    await linkApiService.deleteRecordLink(subTableToolbarRecordId.value, currentLinkFieldId.value, targetRecordId);

    // 刷新子表
    if (tableInstance) {
      await refreshSubTable(subTableToolbarRecordId.value, subTableToolbarCol.value, subTableToolbarRow.value, tableInstance);
    }

    // 更新主表 LINK 字段显示
    loadLinkDisplayData();
    updateSubTableDisabledAdd();

    ElMessage.success('已解除关联');
  } catch (error) {
    if (error !== 'cancel' && error !== 'close') {
      console.error('[VTableView] 解除关联失败:', error);
      ElMessage.error('解除关联失败');
    }
  }
}

// 更新子表添加按钮禁用状态（一对一关系且已有记录时禁用）
function updateSubTableDisabledAdd() {
  if (!currentLinkFieldId.value || !subTableToolbarRecordId.value) {
    subTableDisabledAdd.value = false;
    subTableAddDisabledReason.value = '';
    return;
  }

  const field = fields.value.find(f => f.id === currentLinkFieldId.value);
  if (!field) return;

  const relationshipType = field.options?.relationshipType || 'one_to_many';
  if (relationshipType === 'one_to_one') {
    const record = tableStore.records.find(r => r.id === subTableToolbarRecordId.value);
    const existingIds = (record?.values?.[field.id] as string[]) || [];
    if (existingIds.length >= 1) {
      subTableDisabledAdd.value = true;
      subTableAddDisabledReason.value = '一对一关系仅支持关联 1 条记录';
      return;
    }
  }

  subTableDisabledAdd.value = false;
  subTableAddDisabledReason.value = '';
}

// ==================== 搜索功能方法 ====================
// 打开搜索弹窗（供父组件调用）
function openSearch() {
  if (!tableInstance) return;

  // 初始化 SearchComponent（仅首次）
  if (!searchComponent.value) {
    searchComponent.value = new SearchComponent({
      table: tableInstance as any,
      autoJump: true,
    });
  }

  searchVisible.value = true;

  // 自动聚焦输入框（需在 nextTick 后）
  nextTick(() => {
    const inputEl = document.querySelector('.vtable-search-input input') as HTMLInputElement;
    inputEl?.focus();
  });
}

// 执行搜索
function handleSearch() {
  if (!searchComponent.value || !searchInput.value.trim()) {
    searchResultIndex.value = 0;
    searchTotalCount.value = 0;
    // 树形视图：搜索词为空时重新加载完整树
    if (isTreeView.value) {
      loadTreeRecords();
    }
    return;
  }

  const result = searchComponent.value.search(searchInput.value.trim());
  searchResultIndex.value = result.index + 1; // 显示为 1-based
  searchTotalCount.value = result.results.length;

  // 树形视图：同步加载筛选后的树记录（包含父级上下文）
  if (isTreeView.value) {
    loadTreeRecords();
  }
}

// 下一个结果
function handleSearchNext() {
  if (!searchComponent.value) return;
  const result = searchComponent.value.next();
  searchResultIndex.value = result.index + 1;
}

// 上一个结果
function handleSearchPrev() {
  if (!searchComponent.value) return;
  const result = searchComponent.value.prev();
  searchResultIndex.value = result.index + 1;
}

// 关闭搜索
function closeSearch() {
  searchVisible.value = false;
  if (searchComponent.value) {
    searchComponent.value.clear();
  }
  searchInput.value = '';
  searchResultIndex.value = 0;
  searchTotalCount.value = 0;
  // 树形视图：关闭搜索时重新加载完整树
  if (isTreeView.value) {
    loadTreeRecords();
  }
}

// 监听记录变化，重新加载关联数据
watch(
  () => [records.value, orderedVisibleFields.value],
  () => {
    // 清空旧缓存，避免数据过时
    for (const key of Object.keys(linkDisplayCache)) {
      delete linkDisplayCache[key];
    }
    for (const key of Object.keys(linkLoadingStates)) {
      delete linkLoadingStates[key];
    }
    for (const key of Object.keys(linkErrorStates)) {
      delete linkErrorStates[key];
    }
    loadLinkDisplayData();
  },
  { deep: false, immediate: true }
);

// 监听分组配置变化，重新初始化表格
watch(
  () => props.groupBy,
  () => {
    if (tableInstance) {
      tableInstance.release();
      tableInstance = null as any;
    }
    nextTick(() => {
      initTable();
    });
  },
  { deep: true }
);
</script>

<template>
  <div class="vtable-view">
    <div
      ref="tableContainerRef"
      class="vtable-container"
      @contextmenu.prevent
    ></div>

    <!-- 子表工具栏（跟随子表末尾定位，放在 vtable-view 下避免被 VTable 初始化清空） -->
    <div
      v-if="subTableToolbarVisible && hasLinkFields && !isTreeView"
      class="sub-table-toolbar-container"
      :style="{ top: subTableToolbarPosition.top + 'px', right: subTableToolbarPosition.right + 'px' }"
    >
      <SubTableToolbar
        :link-fields="masterDetailLinkFields"
        :current-field-id="currentLinkFieldId"
        :readonly="props.readonly"
        :has-multiple-link-fields="hasMultipleLinkFields"
        :disabled-add="subTableDisabledAdd"
        :add-disabled-reason="subTableAddDisabledReason"
        @switch-field="handleSubTableSwitchField"
        @add-link="handleSubTableAddLink"
        @refresh="handleSubTableRefresh"
      />
    </div>

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

    <!-- 树形视图：索引列 "+" 按钮 -->
    <div
      v-if="isTreeView && treeAddChildIconVisible && treeAddChildIcon && !treeAddChildLoading"
      class="vtable-tree-add-child-btn"
      :class="{ 'is-loading': treeAddChildLoading }"
      :style="{
        left: treeAddChildIcon.x + 'px',
        top: treeAddChildIcon.y + 'px',
      }"
      @click.stop="handleTreeAddChildClick"
      @mouseenter="clearHideTreeAddChildIconTimer()"
      @mouseleave="delayHideTreeAddChildIcon()"
      :title="
        treeAddChildIcon?.recordName
          ? `在「${treeAddChildIcon.recordName}」下添加子记录`
          : '在当前行下添加一条子记录'
      "
    >
      <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2.5">
        <line x1="12" y1="5" x2="12" y2="19"/>
        <line x1="5" y1="12" x2="19" y2="12"/>
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
      @field-created="handleFieldCreated"
      @field-updated="handleFieldUpdated"
      @field-deleted="handleFieldDeleted"
      @fields-reordered="handleFieldsReordered"
      @field-visibility-changed="handleFieldVisibilityChanged"
    />
    
    <!-- 记录详情对话框 -->
    <RecordDetailDrawer
      v-model:visible="expandDialogVisible"
      :record="expandedRecord"
      :fields="expandedFields"
      :size="drawerSize"
      :readonly="props.readonly"
      @save="handleRecordSave"
    />

    <!-- 附件管理浮动面板 -->
    <AttachmentManager
      v-if="attachmentManagerVisible && attachmentManagerField"
      :field="attachmentManagerField"
      :record-id="attachmentManagerRecordId"
      :model-value="attachmentManagerInitialValue"
      :position="attachmentManagerPosition"
      @update:model-value="handleAttachmentUpdate"
      @close="closeAttachmentManager"
    />

    <!-- 图片缩略图单击预览对话框 -->
    <el-dialog
      v-model="attachmentImagePreviewVisible"
      :title="attachmentImagePreviewName || '预览'"
      width="90%"
      top="5vh"
      destroy-on-close
      class="attachment-image-preview-dialog"
    >
      <div class="attachment-image-preview-content">
        <img
          :src="attachmentImagePreviewUrl"
          class="attachment-image-preview-img"
          :alt="attachmentImagePreviewName"
        />
      </div>
    </el-dialog>

    <!-- 关联记录选择器 -->
    <LinkRecordSelector
      :visible="linkSelectorVisible"
      :target-table-id="linkSelectorTargetTableId"
      :display-field-id="linkSelectorDisplayFieldId"
      :selected-ids="linkSelectorSelectedIds"
      :linked-records="linkSelectorLinkedRecords"
      :allow-multiple="linkSelectorAllowMultiple"
      :exclude-record-id="linkSelectorExcludeRecordId"
      @confirm="handleLinkSelectorConfirm"
      @cancel="handleLinkSelectorCancel"
    />

    <!-- 加载进度提示 -->
    <LoadingProgress
      :visible="tableStore.streamingState.isLoading"
      :loaded-count="tableStore.streamingState.loadedCount"
      :total-count="tableStore.streamingState.totalCount"
      @cancel="handleCancelLoading" />

    <!-- 批量删除加载遮罩 -->
    <LoadingOverlay
      :visible="deleteLoading"
      :record-count="checkboxSelectedRows.length"
      action-text="删除" />

    <!-- 全局搜索弹窗 -->
    <el-dialog
      v-model="searchVisible"
      title="表格内容全局搜索"
      width="360px"
      :modal="false"
      :close-on-click-modal="false"
      draggable
      @close="closeSearch"
      class="vtable-search-dialog"
    >
      <div class="search-content">
        <el-input
          v-model="searchInput"
          placeholder="输入搜索内容..."
          class="vtable-search-input"
          @input="handleSearch"
          clearable
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>

        <div class="search-result-info" v-if="searchTotalCount > 0">
          <span>{{ searchResultIndex }} / {{ searchTotalCount }}</span>
        </div>
        <div class="search-result-info" v-else-if="searchInput">
          <span>无结果</span>
        </div>

        <div class="search-actions">
          <el-button
            size="small"
            :disabled="searchResultIndex <= 1"
            @click="handleSearchPrev">
            上一个
          </el-button>
          <el-button
            size="small"
            :disabled="searchResultIndex >= searchTotalCount || searchTotalCount === 0"
            @click="handleSearchNext">
            下一个
          </el-button>
        </div>
      </div>
    </el-dialog>
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
  position: relative;
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

.vtable-tree-add-child-btn {
  position: fixed;
  z-index: 1000;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: #67c23a;
  color: #fff;
  border-radius: 50%;
  cursor: pointer;
  box-shadow: 0 2px 8px rgba(103, 194, 58, 0.45);
  transform: translate(-50%, -50%);
  transition: all 0.2s ease;
  pointer-events: auto;
  animation: iconFadeIn 0.15s ease;

  &:hover {
    background-color: #5daf34;
    box-shadow: 0 4px 12px rgba(103, 194, 58, 0.6);
    transform: translate(-50%, -50%) scale(1.2);
  }

  &:active {
    background-color: #4f9e2a;
    transform: translate(-50%, -50%) scale(0.9);
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

// ==================== 搜索弹窗样式 ====================
.vtable-search-dialog {
  .search-content {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .vtable-search-input {
    width: 100%;
  }

  .search-result-info {
    text-align: center;
    color: #606266;
    font-size: 13px;
    padding: 4px 0;
  }

  .search-actions {
    display: flex;
    justify-content: center;
    gap: 8px;
  }
}

// ==================== 图片缩略图预览弹窗样式 ====================
.attachment-image-preview-content {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 300px;
  background-color: #1a1a1a;
  padding: $spacing-lg;
}

.attachment-image-preview-img {
  max-width: 100%;
  max-height: 70vh;
  object-fit: contain;
}

.sub-table-toolbar-container {
  position: absolute;
  z-index: 1000;
  background: var(--el-bg-color);
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.12);
  overflow: hidden;
  transition: top 0.1s ease-out;
}

</style>

<!-- 搜索弹窗与图片预览弹窗全局样式（el-dialog teleport 到 body，需要非 scoped 样式） -->
<style lang="scss">
// .vtable-search-dialog 就是 .el-dialog 本身（custom-class 直接添加到 el-dialog）
.vtable-search-dialog.el-dialog {
  background-color: rgba(255, 255, 255, 0.6) !important;
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
}

.vtable-search-dialog .el-dialog__header {
  padding: 10px 14px;
  border-bottom: 1px solid rgba(235, 238, 245, 0.8);
  cursor: move;
  background-color: transparent;
}

.vtable-search-dialog .el-dialog__body {
  padding: 14px;
  background-color: transparent;
}

.vtable-search-dialog .el-dialog__headerbtn {
  top: 10px;
}

// 图片预览弹窗：内容区无内边距，让图片充满主体区域
.attachment-image-preview-dialog.el-dialog {
  .el-dialog__body {
    padding: 0;
  }
}
</style>