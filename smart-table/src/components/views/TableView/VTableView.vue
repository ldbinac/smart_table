<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Close } from '@element-plus/icons-vue';
import { useTableStore } from "@/stores/tableStore";
import { useViewStore } from "@/stores/viewStore";
import { useCollaborationStore } from "@/stores/collaborationStore";
import { useAuthStore } from "@/stores/authStore";
import { realtimeEventEmitter } from "@/services/realtime/eventEmitter";
import LoadingProgress from "@/components/common/LoadingProgress.vue";
import { SmartTableDataSource } from "@/services/SmartTableDataSource";
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
import { validateFieldFormat } from "@/utils/validation";
import { FormulaEngine } from "@/utils/formula/engine";
import { linkApiService } from "@/services/api/linkApiService";

// 导入 VTable
import { ListTable, themes, register as registerVTable } from "@visactor/vtable";
// 导入 VRender 图形工厂函数（用于 customLayout）
import { createGroup, createText, createRect, createCircle, createPath, createImage } from '@visactor/vtable/es/vrender';
// 导入 VTable 编辑器
import { InputEditor, DateInputEditor } from '@visactor/vtable-editors';
import type { IEditor, EditContext, RectProps } from '@visactor/vtable-editors';
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
// 导入成员选择器
import MemberSelect from "@/components/common/MemberSelect.vue";

// 模块级辅助函数（vue-tsc -b 模式下 script setup 内的函数声明不可见时需要）
function extractMemberIds(value: any): string[] {
  if (!value) return [];
  if (Array.isArray(value)) {
    if (value.length === 0) return [];
    if (typeof value[0] === 'string') return value.filter(Boolean);
    return value.map((m: any) => String(m.id || m.name || '')).filter(Boolean);
  }
  if (typeof value === 'string') {
    try {
      const parsed = JSON.parse(value);
      if (Array.isArray(parsed)) {
        return parsed.map((m: any) => String(m.id || m.name || m)).filter(Boolean);
      }
    } catch {}
    return value ? [value] : [];
  }
  if (typeof value === 'object' && value !== null) {
    return [String((value as any).id || (value as any).name || '')].filter(Boolean);
  }
  return [];
}

function recalcFloatingPanelPosition(
  col: number, row: number, panelWidth: number, panelHeight: number
): { x: number; y: number } | null {
  const cellRect = (tableInstance as any)?.getCellRect(col, row);
  const containerRect = tableContainerRef.value?.getBoundingClientRect();
  if (!cellRect || !containerRect) return null;

  const scrollLeft = (tableInstance as any).scrollLeft || 0;
  const scrollTop = (tableInstance as any).scrollTop || 0;
  const frozenColCount = (tableInstance as any).frozenColCount || 1;
  const adjustedLeft = col < frozenColCount ? cellRect.left : cellRect.left - scrollLeft;

  let panelX = containerRect.left + adjustedLeft + cellRect.width;
  let panelY = containerRect.top + cellRect.bottom - scrollTop;

  if (panelX + panelWidth > window.innerWidth - 16) {
    panelX = containerRect.left + adjustedLeft - panelWidth;
  }
  if (panelY + panelHeight > window.innerHeight - 16) {
    panelY = containerRect.top + cellRect.top - scrollTop - panelHeight;
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

const tableContainerRef = ref<HTMLElement | null>(null);
let tableInstance: ListTable | null = null;
let smartDataSource: SmartTableDataSource | null = null;

// 附件管理器状态
const attachmentManagerVisible = ref(false);
const attachmentManagerPosition = ref({ x: 0, y: 0 });
const attachmentManagerField = ref<FieldEntity | null>(null);
const attachmentManagerRecordId = ref<string>('');
const attachmentManagerInitialValue = ref<any>(null);
const attachmentManagerOriginalRecord = ref<any>(null);
// 记录触发浮窗的单元格坐标，用于滚动实时同步位置
const lastAttachmentCellCoords = ref<{ col: number; row: number } | null>(null);

// ==================== 关联记录选择器状态 ====================
const linkSelectorVisible = ref(false);
const linkSelectorTargetTableId = ref('');
const linkSelectorDisplayFieldId = ref('');
const linkSelectorSelectedIds = ref<string[]>([]);
const linkSelectorFieldId = ref('');
const linkSelectorRecordId = ref('');
const linkSelectorAllowMultiple = ref(true);
const linkSelectorLinkedRecords = ref<{ record_id: string; display_value: string }[]>([]);

// ==================== 成员选择器浮动面板状态 ====================
const memberSelectorVisible = ref(false);
const memberSelectorPosition = ref({ x: 0, y: 0 });
const memberSelectorField = ref<FieldEntity | null>(null);
const memberSelectorRecordId = ref<string>('');
const memberSelectorInitialValue = ref<any>(null);
const lastMemberCellCoords = ref<{ col: number; row: number } | null>(null);
const memberSelectorAllowMultiple = ref(true);
const memberSelectorEditingValue = ref<string[]>([]);

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
        setTimeout(() => this.successCallback?.(), 0);
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
    return this.selectedValues.length > 0 ? JSON.stringify(this.selectedValues) : null;
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
        setTimeout(() => this.successCallback?.(), 0);
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
      this.successCallback?.();
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
      this.successCallback?.();
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
    return this.selectedValue;
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

// TextAreaEditor - 多行文本编辑器
class TextAreaEditor extends InputEditor {
  editorType = 'TextArea';
  createElement() {
    const textarea = document.createElement('textarea');
    textarea.style.width = '100%';
    textarea.style.height = '100%';
    textarea.style.border = '2px solid #4A90E2';
    textarea.style.outline = 'none';
    textarea.style.resize = 'none';
    textarea.style.padding = '4px';
    textarea.style.fontSize = '14px';
    textarea.style.boxSizing = 'border-box';
    textarea.style.backgroundColor = '#FFFFFF';
    this.element = textarea as unknown as HTMLInputElement;
    this.container.appendChild(textarea);
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

// MemberEditor - 成员选择编辑器（多选 checkbox 列表）
class MemberEditor implements IEditor {
  editorType = 'Member';
  container?: HTMLElement;
  element?: HTMLElement;
  editorConfig: { members: Array<{id: string, name: string}> };
  successCallback?: () => void;
  selectedMembers: Array<{id: string, name: string}> = [];

  constructor(editorConfig: { members: Array<{id: string, name: string}> }) {
    this.editorConfig = editorConfig;
  }

  onStart({ container, value, referencePosition, endEdit }: EditContext) {
    this.container = container;
    this.successCallback = endEdit;
    // 解析当前值
    if (value) {
      try {
        const parsed = typeof value === 'string' ? JSON.parse(value) : value;
        if (Array.isArray(parsed)) {
          this.selectedMembers = parsed;
        }
      } catch {
        this.selectedMembers = [];
      }
    } else {
      this.selectedMembers = [];
    }
    this.createElement();
    if (referencePosition?.rect) this.adjustPosition(referencePosition.rect);
  }

  createElement() {
    const wrapper = document.createElement('div');
    wrapper.style.cssText = `
      position: absolute;
      background: #ffffff;
      border: 1px solid #d9d9d9;
      border-radius: 4px;
      box-shadow: 0 2px 12px rgba(0,0,0,0.12);
      z-index: 1000;
      max-height: 220px;
      overflow-y: auto;
      min-width: 160px;
      padding: 4px 0;
    `;

    const { members } = this.editorConfig;
    if (members && members.length > 0) {
      members.forEach(member => {
        const label = document.createElement('label');
        label.style.cssText = `
          display: flex;
          align-items: center;
          padding: 6px 12px;
          cursor: pointer;
          font-size: 13px;
          color: #333;
          transition: background-color 0.15s;
        `;
        label.addEventListener('mouseenter', () => { label.style.backgroundColor = '#f0f5ff'; });
        label.addEventListener('mouseleave', () => { label.style.backgroundColor = ''; });

        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.value = member.id;
        checkbox.checked = this.selectedMembers.some(m => m.id === member.id);
        checkbox.style.cssText = 'margin-right: 8px; cursor: pointer; accent-color: #409eff;';
        checkbox.addEventListener('change', () => {
          if (checkbox.checked) {
            if (!this.selectedMembers.some(m => m.id === member.id)) {
              this.selectedMembers.push({ id: member.id, name: member.name });
            }
          } else {
            this.selectedMembers = this.selectedMembers.filter(m => m.id !== member.id);
          }
        });

        label.appendChild(checkbox);
        label.appendChild(document.createTextNode(member.name));
        wrapper.appendChild(label);
      });
    } else {
      const emptyHint = document.createElement('div');
      emptyHint.style.cssText = 'padding: 12px; color: #999; font-size: 12px; text-align: center;';
      emptyHint.textContent = '无可用成员';
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
        setTimeout(() => this.successCallback?.(), 0);
      }
    };
    setTimeout(() => document.addEventListener('mousedown', outsideHandler, true), 0);

    this.element = wrapper;
    this.container?.appendChild(wrapper);
  }

  adjustPosition(rect: RectProps) {
    if (!this.element) return;
    this.element.style.top = `${rect.top - 1}px`;
    this.element.style.left = `${rect.left - 1}px`;
    this.element.style.width = `${Math.max(rect.width + 2, 160)}px`;
  }

  getValue() {
    return JSON.stringify(this.selectedMembers);
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

registerVTable.editor('text-area', new TextAreaEditor());
registerVTable.editor('rating', new RatingEditor());

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
    const row: any = {
      _recordId: record?.id || '',
      _originalRecord: record,
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
            const precision = (field.options?.precision as number) ?? 2;
            row[field.id] = result.toLocaleString('zh-CN', {
              minimumFractionDigits: precision,
              maximumFractionDigits: precision,
            });
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
        addButtonRecord[field.id] = '';
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
    case FieldType.URL:
    case FieldType.EMAIL:
      config.cellType = 'link';
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

// 字段类型到 SVG 图标的映射（用于表头显示）
function getFieldTypeSvg(type: string, color = '#9CA3AF'): string {
  const svg = (path: string) => `<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="${color}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">${path}</svg>`;
  const map: Record<string, string> = {
    single_line_text: svg('<path d="M17 3a2.85 2.83 0 1 1 4 4L7.5 20.5 2 22l1.5-5.5Z"/>'),
    long_text: svg('<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/>'),
    rich_text: svg('<path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8Z"/><polyline points="14 2 14 8 20 8"/><line x1="10" y1="12" x2="8" y2="12"/><line x1="14" y1="12" x2="12" y2="12"/><line x1="12" y1="16" x2="8" y2="16"/>'),
    number: svg('<rect x="4" y="4" width="16" height="16" rx="2"/><line x1="8" y1="9" x2="16" y2="9"/><line x1="8" y1="12" x2="16" y2="12"/><line x1="8" y1="15" x2="13" y2="15"/>'),
    percent: svg('<line x1="19" y1="5" x2="5" y2="19"/><circle cx="6.5" cy="6.5" r="2.5"/><circle cx="17.5" cy="17.5" r="2.5"/>'),
    date: svg('<rect x="3" y="4" width="18" height="18" rx="2" ry="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/>'),
    date_time: svg('<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>'),
    single_select: svg('<circle cx="12" cy="12" r="10"/><path d="m9 12 2 2 4-4"/>'),
    multi_select: svg('<path d="M22 19a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h5l2 3h9a2 2 0 0 1 2 2z"/><polyline points="9 14 11 16 15 12"/>'),
    checkbox: svg('<rect x="4" y="4" width="16" height="16" rx="2"/><path d="m9 12 2 2 4-4"/>'),
    attachment: svg('<path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"/>'),
    member: svg('<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>'),
    rating: svg('<polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/>'),
    progress: svg('<rect x="3" y="3" width="18" height="18" rx="2"/><line x1="3" y1="12" x2="21" y2="12"/><line x1="12" y1="3" x2="12" y2="21"/>'),
    phone: svg('<path d="M22 16.92v3a2 2 0 0 1-2.18 2 19.79 19.79 0 0 1-8.63-3.07 19.5 19.5 0 0 1-6-6 19.79 19.79 0 0 1-3.07-8.67A2 2 0 0 1 4.11 2h3a2 2 0 0 1 2 1.72 12.84 12.84 0 0 0 .7 2.81 2 2 0 0 1-.45 2.11L8.09 9.91a16 16 0 0 0 6 6l1.27-1.27a2 2 0 0 1 2.11-.45 12.84 12.84 0 0 0 2.81.7A2 2 0 0 1 22 16.92z"/>'),
    email: svg('<path d="M4 4h16c1.1 0 2 .9 2 2v12c0 1.1-.9 2-2 2H4c-1.1 0-2-.9-2-2V6c0-1.1.9-2 2-2z"/><polyline points="22,6 12,13 2,6"/>'),
    url: svg('<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>'),
    link: svg('<path d="M10 13a5 5 0 0 0 7.54.54l3-3a5 5 0 0 0-7.07-7.07l-1.72 1.71"/><path d="M14 11a5 5 0 0 0-7.54-.54l-3 3a5 5 0 0 0 7.07 7.07l1.71-1.71"/>'),
    created_by: svg('<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>'),
    updated_by: svg('<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"/><circle cx="12" cy="7" r="4"/>'),
    formula: svg('<path d="M16 3h-4v5h4"/><path d="M8 3h4v5H8"/><path d="M12 22V8"/><path d="M4 12h16"/><path d="M7 17h10"/>'),
    lookup: svg('<circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/>'),
    created_time: svg('<path d="M12 2a10 10 0 1 0 10 10"/><polyline points="12 6 12 12 16 14"/>'),
    updated_time: svg('<path d="M12 2a10 10 0 1 0 10 10"/><polyline points="12 6 12 12 16 14"/>'),
    auto_number: svg('<polyline points="4 7 4 4 20 4 20 7"/><line x1="9" y1="20" x2="15" y2="20"/><line x1="12" y1="4" x2="12" y2="20"/>'),
    currency: svg('<line x1="12" y1="1" x2="12" y2="23"/><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"/>'),
    barcode: svg('<rect x="3" y="4" width="2" height="16"/><rect x="7" y="4" width="1" height="16"/><rect x="10" y="4" width="3" height="16"/><rect x="15" y="4" width="2" height="16"/><rect x="19" y="4" width="2" height="16"/>'),
    collaborator: svg('<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>'),
    last_modified_by: svg('<path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M23 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/>'),
    duration: svg('<circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/>'),
    button: svg('<rect x="3" y="8" width="18" height="8" rx="2"/><path d="M8 12h8"/>'),
  };
  return map[type] || map.single_line_text;
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

    // 为 LONG_TEXT/RICH_TEXT 分配 TextAreaEditor
    if (field.type === FieldType.LONG_TEXT || field.type === FieldType.RICH_TEXT) {
      cellTypeConfig.editor = new TextAreaEditor();
    }

    // 为 PROGRESS 分配 InputEditor（整数输入 0-100）
    if (field.type === FieldType.PROGRESS) {
      cellTypeConfig.editor = new InputEditor();
    }

    // 为 RATING 分配 RatingEditor
    if (field.type === FieldType.RATING) {
      cellTypeConfig.editor = new RatingEditor();
    }

    // 为 MEMBER 分配 MemberEditor（从 userCacheStore 获取成员列表）
    if (field.type === FieldType.MEMBER) {
      const cachedUsers = Array.from(userCacheStore.userCache.values());
      const members = cachedUsers.map(u => ({ id: u.id, name: u.name }));
      cellTypeConfig.editor = new MemberEditor({ members });
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
      sort: true,
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

  // 转换 records 为 VTable 需要的格式（字段映射 + 公式计算）
  let tableRecords = transformRecords(sortedRecords.value);

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
        maxCachedBatches: 50,  // 50×200=10,000条，LRU 阈值（超过后驱逐最久未访问批次）
      });
    } else {
      smartDataSource.clearCache();
    }
    smartDataSource.updateMemoryCache(tableRecords, 0);
    smartDataSource.markFullyLoaded();
  }

  const config = {
    columns,
    ...(isGrouped
      ? { records: tableRecords }
      : { dataSource: smartDataSource!.dataSource }),
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
      // 自定义渲染：新增行不显示复选框和行号
      customRender: (args: any) => {
        if (args.record && args.record._rowType === 'addButton') {
          return '';
        }
        return undefined;
      },
      formatMethod: (value: any, data: any) => {
        if (data && data._rowType === 'addButton') {
          return '';
        }
        return value;
      },
    },
    allowCopy: true,
    editCellTrigger: 'doubleclick',
    keyboardOptions: {
      copySelected: true,
      pasteValueToCell: true,
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
          if (colIdx === 2 || colIdx % 5 === 0) {
            const text = createText({
              x: cellWidth / 2,
              y: cellHeight / 2,
              text: '+ 添加记录',
              fontSize: 13,
              fill: '#6366f1',
              fontWeight: 'bold',
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

        if (tableId && currentUserId && collabStore.isRealtimeAvailable) {
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
            { table_id: tableId, record_id: recordId, field_id: fieldId },
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

          await recordService.updateRecord(recordId, {
            values: {
              ...originalRecord.values,
              [fieldId]: checked,
            } as Record<string, CellValue>,
          });

          // 刷新表格数据
          await tableStore.refreshRecords(tableId);

          // 协同编辑：释放锁
          if (tableId && currentUserId && collabStore.isRealtimeAvailable) {
            collabStore.releaseLock({
              table_id: tableId,
              record_id: recordId,
              field_id: fieldId,
            });
          }
        } catch (error) {
          console.error('开关状态保存失败:', error);
          ElMessage.error('开关状态保存失败');
        }
      }
    }
  });

  // 编辑开始前事件 - 协同锁检查
  tableInstanceAny.on('before_start_edit', (args: any) => {
    if (!tableInstance) return;

    const { col, row } = args;
    // 跳过行号列
    if (col <= 0) return;

    const record = tableInstance.getCellOriginRecord(col, row);
    if (!record?._recordId) return;

    const fieldId = orderedVisibleFields.value[col - 1]?.id;
    if (!fieldId) return;

    const authStore = useAuthStore();
    const currentUserId = authStore.user?.id;
    if (!currentUserId) return;

    // 检查是否被其他用户锁定
    if (collabStore.isCellLockedByOther(record._recordId, fieldId, currentUserId)) {
      const lockInfo = collabStore.getCellLockInfo(record._recordId, fieldId);
      ElMessage.warning(`${lockInfo?.nickname || lockInfo?.name || '其他用户'} 正在编辑此单元格`);
      return false; // 阻止编辑
    }

    // 如果没有锁定或由当前用户锁定，异步获取锁
    const tableId = tableStore.currentTable?.id;
    if (tableId && collabStore.isRealtimeAvailable) {
      collabStore.acquireLock(
        { table_id: tableId, record_id: record._recordId, field_id: fieldId },
        currentUserId
      ).then((result) => {
        if (!result.success && result.reason === 'locked') {
          // 竞争条件：在我们检查后锁被其他用户获取
          ElMessage.warning(`${result.locked_by?.nickname || result.locked_by?.name || '其他用户'} 已锁定此单元格`);
          // 通知用户但编辑已开启 - 保存时处理冲突
        }
      });
    }

    return true; // 允许编辑
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
      contextMenuVisible.value = true;
    }
  });

  // 单元格点击 - 使用 VTable API 获取单元格位置
  tableInstanceAny.on('click_cell', (args: any) => {
    // 检测是否为虚拟添加按钮行点击
    const clickedRecord = args.originData || args.record;
    if (clickedRecord && clickedRecord._rowType === 'addButton') {
      const groupValues = clickedRecord._groupValues || {};
      emit('group-add-record', groupValues);
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

        // 判断是否允许多选
        const relationshipType = field.options?.relationshipType || field.options?.relationship_type || field.config?.relationshipType || field.config?.relationship_type || 'many_to_many';
        const allowMultiple = relationshipType !== 'one_to_one' && relationshipType !== 'many_to_one';

        linkSelectorTargetTableId.value = (field.options?.linkedTableId || field.options?.linked_table_id || field.config?.linkedTableId || field.config?.linked_table_id || '') as string;
        linkSelectorDisplayFieldId.value = (field.options?.displayFieldId || field.options?.display_field_id || field.config?.displayFieldId || field.config?.display_field_id || '') as string;
        linkSelectorSelectedIds.value = currentIds;
        linkSelectorFieldId.value = field.id;
        linkSelectorRecordId.value = recordId;
        linkSelectorAllowMultiple.value = allowMultiple;

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
      // 成员字段：打开成员选择器浮动面板
      if (field.type === FieldType.MEMBER) {
        const cellRect = (tableInstance as any)?.getCellRect(colIndex, rowIndex);
        const containerRect = tableContainerRef.value?.getBoundingClientRect();
        if (cellRect && containerRect) {
          const cellRecord = (tableInstance as any)?.getCellOriginRecord?.(colIndex, rowIndex);
          if (!cellRecord) return;

          const scrollLeft = (tableInstance as any).scrollLeft || 0;
          const scrollTop = (tableInstance as any).scrollTop || 0;
          const frozenColCount = (tableInstance as any).frozenColCount || 1;
          const adjustedLeft = colIndex < frozenColCount ? cellRect.left : cellRect.left - scrollLeft;

          // 基准位置：单元格右下角
          let panelX = containerRect.left + adjustedLeft + cellRect.width;
          let panelY = containerRect.top + cellRect.bottom - scrollTop;

          // 视口边界检测
          const panelWidth = 360;
          const panelHeight = 420;
          if (panelX + panelWidth > window.innerWidth - 16) {
            panelX = containerRect.left + adjustedLeft - panelWidth;
          }
          if (panelY + panelHeight > window.innerHeight - 16) {
            panelY = containerRect.top + cellRect.top - scrollTop - panelHeight;
          }
          if (panelX < 8) panelX = 8;
          if (panelY < 8) panelY = 8;

          memberSelectorPosition.value = { x: panelX, y: panelY };
          memberSelectorField.value = field;
          memberSelectorRecordId.value = cellRecord._recordId || cellRecord._originalRecord?.id || '';
          memberSelectorInitialValue.value = cellRecord[field.id] ?? cellRecord._originalRecord?.values?.[field.id] ?? null;
          memberSelectorAllowMultiple.value = field.options?.allowMultiple !== false;
          // 初始化编辑值：从当前值中提取成员 ID 列表
          memberSelectorEditingValue.value = extractMemberIds(memberSelectorInitialValue.value);
          memberSelectorVisible.value = true;
          lastMemberCellCoords.value = { col: colIndex, row: rowIndex };
          return;
        }
      }
    }
    // 非附件/关联/成员字段，保持原有行为
    if (args.record && args.record._originalRecord) {
      handleExpandRecord(args.record._originalRecord);
    }
  });

  // 表格滚动事件 - 实时更新附件/成员浮窗位置
  tableInstanceAny.on('scroll', (_args: any) => {
    // 更新附件浮窗
    if (attachmentManagerVisible.value && lastAttachmentCellCoords.value) {
      const { col, row } = lastAttachmentCellCoords.value;
      const pos = recalcFloatingPanelPosition(col, row, 380, 480);
      if (pos) attachmentManagerPosition.value = pos;
    }
    // 更新成员选择器浮窗
    if (memberSelectorVisible.value && lastMemberCellCoords.value) {
      const { col, row } = lastMemberCellCoords.value;
      const pos = recalcFloatingPanelPosition(col, row, 360, 420);
      if (pos) memberSelectorPosition.value = pos;
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
    
    // 协同编辑：检查锁状态，如果被其他用户锁定则阻止保存
    if (tableId && currentUserId && collabStore.isRealtimeAvailable) {
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
      
      await recordService.updateRecord(recordId, {
        values: values as Record<string, CellValue>,
      });
      
      // 刷新表格数据
      await tableStore.refreshRecords(tableId);
      
      // 协同编辑：保存成功后释放锁
      if (tableId && currentUserId && collabStore.isRealtimeAvailable) {
        collabStore.releaseLock({
          table_id: tableId,
          record_id: recordId,
          field_id: fieldId,
        });
      }
      
      ElMessage.success('编辑保存成功');
    } catch (error) {
      console.error('编辑保存失败:', error);
      ElMessage.error('编辑保存失败');
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
    if (isGrouped) {
      // 分组模式：updateOption({ records }) 无法正确重新初始化 groupBy 分组逻辑，
      // 导致全量数据加载后表格空白。必须全量重建以确保 groupBy 与 records 一同初始化。
      updateTable();
    } else if (smartDataSource) {
      // 非分组 CachedDataSource 模式：更新内存缓存 + 轻量重绘
      const newRows = transformRecords(sortedRecords.value);
      smartDataSource.clearCache();
      smartDataSource.updateMemoryCache(newRows, 0);
      smartDataSource.markFullyLoaded();
      (tableInstance as any).renderWithRecreateCells();
    } else {
      // 无 dataSource，回退全量重建
      updateTable();
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

/** 取消流式数据加载 */
const handleCancelLoading = () => {
  tableStore.cancelLoading();
};

// 监听 records 变化 → 增量数据更新
// 流式加载期间：仅增量更新 dataSource 缓存，避免反复重建 VTable
// 非流式：通过 updateTableData 增量更新（不销毁重建 VTable）
watch(() => tableStore.records, () => {
  if (tableStore.streamingState.isLoading && smartDataSource) {
    // 流式加载进行中：增量更新缓存（只加载新增部分）
    const prevCount = smartDataSource.totalCount;
    const rawRecords = sortedRecords.value;
    if (rawRecords.length > prevCount) {
      const newRaw = rawRecords.slice(prevCount);
      const newRows = transformRecords(newRaw);
      smartDataSource.updateMemoryCache(newRows, prevCount);
      smartDataSource.updateTotalCount(rawRecords.length);
      console.log(
        `[VTableView] 流式增量更新: ${newRows.length} 条, 累计 ${rawRecords.length}/${tableStore.streamingState.totalCount}`
      );
    }
    return;
  }
  // 流式完成后：废弃旧的 smartDataSource（CachedDataSource.length 构造时冻结），
  // 强制 updateTableData → updateTable → 以正确 totalCount 重建
  if (smartDataSource && !tableStore.streamingState.isLoading) {
    smartDataSource = null;
  }
  updateTableData();
}, { deep: true });

// 监听 fields 变化 → 列结构变更，需重建表格
watch(() => tableStore.fields, () => {
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
  // 成员名称变更需清除转换缓存，强制重算 MEMBER 字段
  clearTransformCache();
  updateTableData();
});

// 监听流式加载完成：标记 fullyLoaded，交由 records watch 完成重建
watch(() => tableStore.streamingState.isLoading, (wasLoading, isLoading) => {
  if (wasLoading && !isLoading && smartDataSource) {
    smartDataSource.markFullyLoaded();
    console.log(
      `[VTableView] 流式加载完成，当前 sortedRecords: ${sortedRecords.value.length} 条，smartDataSource.totalCount: ${smartDataSource.totalCount}`
    );
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
});

onBeforeUnmount(() => {
  // 释放所有持有的协同编辑锁
  const tableId = tableStore.currentTable?.id;
  if (tableId && collabStore.isRealtimeAvailable) {
    collabStore.releaseAllCurrentLocks(tableId);
  }
  cleanupRealtimeListeners();
  document.removeEventListener('click', handleDocumentClick);
  window.removeEventListener('resize', handleFloatingPanelWindowResize);
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

// 附件管理器：关闭
function closeAttachmentManager() {
  attachmentManagerVisible.value = false;
  attachmentManagerField.value = null;
  attachmentManagerRecordId.value = '';
  attachmentManagerInitialValue.value = null;
  attachmentManagerOriginalRecord.value = null;
  lastAttachmentCellCoords.value = null;
}

// 窗口 resize 事件 - 重新定位所有浮窗
function handleFloatingPanelWindowResize() {
  // 更新附件浮窗
  if (attachmentManagerVisible.value && lastAttachmentCellCoords.value) {
    const { col, row } = lastAttachmentCellCoords.value;
    const pos = recalcFloatingPanelPosition(col, row, 380, 480);
    if (pos) attachmentManagerPosition.value = pos;
  }
  // 更新成员选择器浮窗
  if (memberSelectorVisible.value && lastMemberCellCoords.value) {
    const { col, row } = lastMemberCellCoords.value;
    const pos = recalcFloatingPanelPosition(col, row, 360, 420);
    if (pos) memberSelectorPosition.value = pos;
  }
}

// 附件管理器：值变更保存
async function handleAttachmentUpdate(value: any) {
  if (!attachmentManagerRecordId.value || !attachmentManagerField.value || !props.tableId) return;
  try {
    const fieldId = attachmentManagerField.value.id;
    const originalRecord = attachmentManagerOriginalRecord.value;
    if (originalRecord?.values) {
      const newValues = { ...originalRecord.values, [fieldId]: value };
      await recordService.updateRecord(attachmentManagerRecordId.value, {
        values: newValues as Record<string, CellValue>,
      });
      await tableStore.refreshRecords(props.tableId);
    }
  } catch (error) {
    console.error('附件保存失败:', error);
    ElMessage.error('附件保存失败');
  }
}

// ==================== 成员选择器：关闭、确认 ====================
function closeMemberSelector() {
  memberSelectorVisible.value = false;
  memberSelectorField.value = null;
  memberSelectorRecordId.value = '';
  memberSelectorInitialValue.value = null;
  memberSelectorEditingValue.value = [];
  lastMemberCellCoords.value = null;
}

// 成员选择器：保存
async function handleMemberUpdate(value: any) {
  memberSelectorEditingValue.value = extractMemberIds(value);
}

// 成员选择器：确认保存到数据库
async function confirmMemberUpdate() {
  if (!memberSelectorRecordId.value || !memberSelectorField.value || !props.tableId) return;
  const fieldId = memberSelectorField.value.id;
  const newValue = memberSelectorEditingValue.value;
  try {
    await recordService.updateRecord(memberSelectorRecordId.value, {
      values: { [fieldId]: newValue } as Record<string, CellValue>,
    });
    await tableStore.refreshRecords(props.tableId);
  } catch (error) {
    console.error('成员字段保存失败:', error);
    ElMessage.error('成员字段保存失败');
  }
  closeMemberSelector();
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

  try {
    await linkApiService.updateRecordLink(linkSelectorRecordId.value, linkSelectorFieldId.value, {
      target_record_ids: selectedIds,
    });

    // 刷新缓存和数据
    const cacheKey = `${linkSelectorRecordId.value}:${linkSelectorFieldId.value}`;
    delete linkDisplayCache[cacheKey];
    delete linkLoadingStates[cacheKey];
    delete linkErrorStates[cacheKey];

    await tableStore.refreshRecords(props.tableId);
  } catch (error) {
    console.error('更新关联字段失败:', error);
    ElMessage.error('更新关联字段失败');
  }

  linkSelectorVisible.value = false;
}

function handleLinkSelectorCancel() {
  linkSelectorVisible.value = false;
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

    <!-- 关联记录选择器 -->
    <LinkRecordSelector
      :visible="linkSelectorVisible"
      :target-table-id="linkSelectorTargetTableId"
      :display-field-id="linkSelectorDisplayFieldId"
      :selected-ids="linkSelectorSelectedIds"
      :linked-records="linkSelectorLinkedRecords"
      :allow-multiple="linkSelectorAllowMultiple"
      @confirm="handleLinkSelectorConfirm"
      @cancel="handleLinkSelectorCancel"
    />

    <!-- 成员选择器浮动面板 -->
    <div
      v-if="memberSelectorVisible && memberSelectorField"
      class="member-selector-panel"
      :style="{
        left: memberSelectorPosition.x + 'px',
        top: memberSelectorPosition.y + 'px',
      }"
      @click.stop
    >
      <div class="member-selector-header">
        <span>{{ memberSelectorField.name }}</span>
        <el-icon class="close-btn" @click="closeMemberSelector">
          <Close />
        </el-icon>
      </div>
      <MemberSelect
        v-model="memberSelectorEditingValue"
        :allow-multiple="memberSelectorAllowMultiple"
        @update:model-value="handleMemberUpdate"
      />
      <div class="member-selector-footer">
        <el-button size="small" @click="closeMemberSelector">取消</el-button>
        <el-button size="small" type="primary" @click="confirmMemberUpdate">确定</el-button>
      </div>
    </div>
    
    <!-- 加载进度提示 -->
    <LoadingProgress
      :visible="tableStore.streamingState.isLoading"
      :loaded-count="tableStore.streamingState.loadedCount"
      :total-count="tableStore.streamingState.totalCount"
      @cancel="handleCancelLoading" />
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

// 成员选择器浮动面板
.member-selector-panel {
  position: fixed;
  z-index: 1001;
  width: 320px;
  background-color: #fff;
  border: 1px solid #dcdfe6;
  border-radius: 8px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  overflow: hidden;

  .member-selector-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 10px 12px;
    border-bottom: 1px solid #ebeef5;
    font-size: 13px;
    font-weight: 500;
    color: #303133;

    .close-btn {
      cursor: pointer;
      color: #909399;
      font-size: 14px;

      &:hover {
        color: #303133;
      }
    }
  }

  .member-selector-footer {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
    padding: 8px 12px;
    border-top: 1px solid #ebeef5;
  }

  // MemberSelect 组件在面板内的间距
  .member-select {
    padding: 8px 12px;
  }
}
</style>