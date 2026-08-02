<script setup lang="ts">
/**
 * 抽屉详情页面内的子表组件
 * 在 RecordDetailDrawer 的关联字段下方渲染关联记录的完整子表数据
 * 与 VTableView 子表展示逻辑一致：
 * - 使用 VTable ListTable 渲染
 * - 字段渲染样式与主表一致（单选/多选/附件/成员/评分等）
 * - 点击单元格显示放大按钮，点击放大按钮触发详情抽屉
 * - 异步加载子表数据，不阻塞抽屉打开
 */
import { ref, shallowRef, onMounted, onBeforeUnmount, watch, nextTick } from 'vue';
import { ListTable, themes } from '@visactor/vtable';
import { createGroup, createText, createRect, createPath, createImage, createCircle } from '@visactor/vtable/es/vrender';
import { FieldType } from '@/types/fields';
import { masterDetailService } from '@/services/masterDetailService';
import type { FieldEntity, RecordEntity } from '@/db/schema';
import { useUserCacheStore } from '@/stores/userCacheStore';
import { formatDate, formatDateTime } from '@/utils/timezone';

const props = defineProps<{
  /** 主表记录 ID */
  recordId: string;
  /** 关联字段 ID */
  fieldId: string;
  /** 目标表 ID（子表所属表） */
  targetTableId: string;
  /** 是否只读 */
  readonly?: boolean;
}>();

const emit = defineEmits<{
  /** 点击放大按钮时触发，传递子表记录原始数据 */
  'expand-record': [record: RecordEntity];
}>();

const userCacheStore = useUserCacheStore();

const containerRef = ref<HTMLDivElement | null>(null);
const tableInstance = shallowRef<ListTable | null>(null);
const loading = ref(false);
const hasData = ref(false);
const errorMessage = ref('');

// 放大按钮状态
const actionIconVisible = ref(false);
const selectedCell = ref<{ x: number; y: number; record: any } | null>(null);

// ==================== 字段类型渲染辅助 ====================

/** 生成五角星 SVG path */
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

/** 根据字段类型构建 VTable 列配置（cellType / fieldFormat / style） */
const buildColumnConfig = (field: any): Record<string, any> => {
  const config: Record<string, any> = {};
  switch (field.type) {
    case FieldType.PROGRESS:
      config.cellType = 'progressbar';
      config.min = 0; config.max = 100;
      config.fieldFormat = (record: any) => {
        const value = record?.[field.id];
        const num = Number(value);
        return isNaN(num) ? '0%' : `${Math.round(num)}%`;
      };
      config.style = {
        barColor: '#409eff', barBgColor: '#e5e7eb', barHeight: '20%', barBottom: '30%',
        textAlign: 'center', textBaseline: 'middle', fontSize: 12, color: '#374151', fontWeight: '500',
      };
      break;
    case FieldType.CHECKBOX:
      config.cellType = 'switch';
      config.style = { textAlign: 'center' };
      break;
    case FieldType.RICH_TEXT:
      config.cellType = 'text';
      config.fieldFormat = (record: any) => {
        const value = record?.[field.id];
        if (value == null || value === '') return '';
        const tmp = document.createElement('div');
        tmp.innerHTML = String(value);
        return tmp.textContent || tmp.innerText || '';
      };
      break;
    case FieldType.URL:
    case FieldType.EMAIL:
      config.cellType = 'link';
      break;
    case FieldType.DATE:
      config.cellType = 'text';
      config.style = { textAlign: 'center' };
      config.fieldFormat = (value: any) => {
        const cellValue = value?.[field.id];
        if (cellValue == null || cellValue === '') return '';
        if (cellValue instanceof Date) return formatDate(cellValue.getTime());
        if (typeof cellValue === 'number') return formatDate(cellValue);
        if (typeof cellValue === 'string') return formatDate(cellValue);
        return String(cellValue);
      };
      break;
    case FieldType.DATE_TIME:
      config.cellType = 'text';
      config.fieldFormat = (value: any) => {
        const cellValue = value?.[field.id];
        if (cellValue == null || cellValue === '') return '';
        if (cellValue instanceof Date) return formatDateTime(cellValue.getTime());
        if (typeof cellValue === 'number') return formatDateTime(cellValue);
        if (typeof cellValue === 'string') return formatDateTime(cellValue);
        return String(cellValue);
      };
      break;
    case FieldType.NUMBER:
    case FieldType.PERCENT:
    case FieldType.CURRENCY:
    case FieldType.DURATION:
      config.cellType = 'text';
      config.style = { textAlign: 'right' };
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
        if (field.type === FieldType.PERCENT) formatted = `${formatted}%`;
        else if (field.type === FieldType.CURRENCY && currencySymbol) formatted = `${currencySymbol}${formatted}`;
        return `${prefix}${formatted}${suffix}`;
      };
      break;
    case FieldType.LINK:
      config.cellType = 'text';
      config.fieldFormat = (record: any) => {
        const rawIds = record?.[field.id];
        if (Array.isArray(rawIds) && rawIds.length > 0) return `关联 ${rawIds.length} 条`;
        return '';
      };
      break;
    case FieldType.SINGLE_SELECT:
    case FieldType.MULTI_SELECT:
    case FieldType.RATING:
    case FieldType.MEMBER:
    case FieldType.ATTACHMENT:
    default:
      config.cellType = 'text';
      break;
  }
  return config;
};

/** 为复杂类型字段添加 customLayout（与 VTableView enhanceSubTableColumns 一致） */
const enhanceColumns = (columns: any[], targetFields: any[]): any[] => {
  return columns.map((col: any) => {
    const field = targetFields.find((f: any) => f.id === col.field);
    if (!field) return col;

    const cellTypeConfig = buildColumnConfig(field);
    const enhancedCol = { ...col, ...cellTypeConfig };

    const layoutTypes = [
      FieldType.SINGLE_SELECT,
      FieldType.MULTI_SELECT,
      FieldType.MEMBER,
      FieldType.RATING,
      FieldType.ATTACHMENT,
    ];
    if (layoutTypes.includes(field.type as any)) {
      enhancedCol.customLayout = (args: any) => {
        const { table, row, col: colIdx, rect } = args;
        if (!table) return { renderDefault: true };

        const value = table.getCellValue(colIdx, row);
        if (value === null || value === undefined) return { renderDefault: true };

        const cellHeight = rect?.height || table.getCellRect(colIdx, row)?.height || 40;
        const cellWidth = rect?.width || table.getCellRect(colIdx, row)?.width || 150;
        const fontFamily = 'system-ui, -apple-system, sans-serif';
        const fontSize = 12;

        const measureText = (text: string): number => {
          try {
            if (table && typeof table.measureText === 'function') {
              const result = table.measureText(text, { fontSize, fontFamily });
              if (result && typeof result.width === 'number') return result.width;
            }
          } catch { /* ignore */ }
          return text.length * 7;
        };

        switch (field.type) {
          case FieldType.SINGLE_SELECT: {
            const val = String(value);
            const options = (field.options?.choices || field.options?.options || []) as Array<{ id: string; name: string; color?: string }>;
            const found = options.find((o) => o.name === val);
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
              vals = value.map((v) => (typeof v === 'object' ? String((v as any).name || (v as any).id || '') : String(v)));
            } else if (typeof value === 'string') {
              try { const p = JSON.parse(value); if (Array.isArray(p)) vals = p.map((v: any) => String(v)); } catch { /* ignore */ }
              if (vals.length === 0) vals = value.split(', ').filter(Boolean);
            }
            if (vals.length === 0) return { renderDefault: true };
            const options = (field.options?.choices || field.options?.options || []) as Array<{ id: string; name: string; color?: string }>;
            const tagHeight = 26;
            const gap = 8;
            const container = createGroup({
              width: cellWidth, height: cellHeight,
              display: 'flex', flexDirection: 'row', flexWrap: 'wrap',
              alignContent: 'center', alignItems: 'center',
            });
            const spacerLeft = createRect({ x: 0, y: 0, width: 8, height: tagHeight, fill: 'transparent' });
            container.add(spacerLeft);
            vals.forEach((v) => {
              const opt = options.find((o) => o.name === v);
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
              try { const p = JSON.parse(value); if (Array.isArray(p)) files = p; } catch { /* ignore */ }
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
              display: 'flex', flexDirection: 'row', alignItems: 'center', flexWrap: 'nowrap',
            });
            displayFiles.forEach((file: any) => {
              const fileName = file.name || '';
              const fileUrl = file.url || file.thumbnail || file.preview || '';
              const isImage = isImageFile(fileName);
              if (isImage && fileUrl) {
                const img = createImage({ width: itemSize, height: itemSize, image: fileUrl, cornerRadius: 4, cursor: 'pointer' });
                const itemGroup = createGroup({ width: itemSize + gap, height: itemSize, display: 'flex', alignItems: 'center' });
                itemGroup.add(img);
                container.add(itemGroup);
              } else {
                const itemGroup = createGroup({ width: itemSize + gap, height: itemSize, display: 'flex', alignItems: 'center' });
                const pinPath = createPath({
                  path: 'M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48',
                  x: (itemSize - 14) / 2, y: (itemSize - 14) / 2,
                  stroke: '#9CA3AF', lineWidth: 1.5, lineCap: 'round', lineJoin: 'round', fill: 'none',
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
            let memberData: Array<{ id: string; name: string }> = [];
            try {
              const parsed = JSON.parse(String(value));
              if (Array.isArray(parsed) && parsed.length > 0) {
                memberData = parsed.map((m: any) => ({ id: String(m.id || ''), name: String(m.name || m.id || '') }));
              }
            } catch {
              const parts = String(value).split(', ').filter(Boolean);
              memberData = parts.map((p) => ({ id: p, name: p }));
            }
            if (memberData.length === 0) {
              // 空值显示占位符 -（与主表一致）
              const emptyLabel = createText({
                x: 8, y: cellHeight / 2, text: '-', fontSize, fill: '#999999', textBaseline: 'middle',
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
            displayMembers.forEach((m) => {
              const hash = m.id.split('').reduce((acc: number, c: string) => acc + c.charCodeAt(0), 0);
              const avatarColor = avatarColors[Math.abs(hash) % avatarColors.length];
              const initial = m.name.charAt(0).toUpperCase();
              const avatar = createCircle({
                x: currentX + radius, y: cellHeight / 2, radius, fill: avatarColor,
              });
              container.add(avatar);
              const initialText = createText({
                x: currentX + radius, y: cellHeight / 2, text: initial, fontSize: 11,
                fill: '#ffffff', textAlign: 'center', textBaseline: 'middle',
              });
              container.add(initialText);
              const nameText = createText({
                x: currentX + avatarSize + 4, y: cellHeight / 2, text: m.name, fontSize,
                fill: '#374151', textBaseline: 'middle',
              });
              container.add(nameText);
              currentX += avatarSize + 4 + m.name.length * 7 + 8;
            });
            if (overflow > 0) {
              const overflowText = createText({
                x: currentX, y: cellHeight / 2, text: `+${overflow}`, fontSize, fill: '#6B7280', textBaseline: 'middle',
              });
              container.add(overflowText);
            }
            return { rootContainer: container, renderDefault: false };
          }
          default:
            return { renderDefault: true };
        }
      };
    }
    return enhancedCol;
  });
};

/** 转换子表记录值（单选 ID -> name、成员解析等，与 VTableView transformSubTableRecords 一致） */
const transformRecords = (records: any[], targetFields: any[]): any[] => {
  return records.map((row: any) => {
    const transformed: any = { ...row };
    targetFields.forEach((field: any) => {
      if (!field?.id) return;
      const rawVal = transformed[field.id];
      switch (field.type) {
        case FieldType.SINGLE_SELECT: {
          const opts = (field.options?.choices || field.options?.options || []) as Array<{ id: string; name: string }>;
          const selId = typeof rawVal === 'object' && rawVal !== null ? String((rawVal as any).id || '') : String(rawVal || '');
          const found = opts.find((o) => o.id === selId || o.name === selId);
          transformed[field.id] = found?.name || selId;
          break;
        }
        case FieldType.MULTI_SELECT: {
          let items: any[] = [];
          if (Array.isArray(rawVal)) items = rawVal;
          else if (typeof rawVal === 'string') {
            try { const p = JSON.parse(rawVal); if (Array.isArray(p)) items = p; } catch { /* ignore */ }
          }
          if (items.length === 0) { transformed[field.id] = ''; break; }
          const opts = (field.options?.choices || field.options?.options || []) as Array<{ id: string; name: string }>;
          transformed[field.id] = items.map((v) => {
            const vid = typeof v === 'object' ? String((v as any).id || '') : String(v);
            const vname = typeof v === 'object' ? String((v as any).name || '') : '';
            const of = opts.find((o) => o.id === vid || o.name === vid);
            return vname || of?.name || vid;
          }).join(', ');
          break;
        }
        case FieldType.MEMBER: {
          let mems: any[] = [];
          if (Array.isArray(rawVal)) mems = rawVal;
          else if (typeof rawVal === 'string') {
            try { const p = JSON.parse(rawVal); if (Array.isArray(p)) mems = p; } catch { /* ignore */ }
          } else if (typeof rawVal === 'object' && rawVal !== null) mems = [rawVal];
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
            try { const p = JSON.parse(rawVal); if (Array.isArray(p)) { transformed[field.id] = p; break; } } catch { /* ignore */ }
            transformed[field.id] = rawVal; break;
          }
          transformed[field.id] = rawVal;
          break;
        }
        default:
          break;
      }
    });
    return transformed;
  });
};

// ==================== 数据加载与表格初始化 ====================

const loadData = async () => {
  if (!props.recordId || !props.fieldId || !props.targetTableId) return;
  loading.value = true;
  errorMessage.value = '';
  try {
    // 并行获取目标表字段定义和关联记录详情
    const [targetFields, response] = await Promise.all([
      masterDetailService.getTargetTableFields(props.targetTableId),
      masterDetailService.getLinkedRecordsDetail(props.recordId, props.fieldId, { page: 1, per_page: 100 }),
    ]);

    if (!response.records || response.records.length === 0) {
      hasData.value = false;
      loading.value = false;
      return;
    }

    // 构建列配置
    let columns = masterDetailService.buildSubTableColumns(targetFields) as any[];
    columns = enhanceColumns(columns, targetFields);

    // 转换记录值
    let childrenData = response.records.map((r) => ({
      ...r.values,
      _recordId: r.id,
      _originalRecord: r,
    }));
    childrenData = transformRecords(childrenData, targetFields);

    hasData.value = childrenData.length > 0;
    loading.value = false;

    // 等待容器渲染完成
    await nextTick();
    if (containerRef.value && hasData.value) {
      renderTable(columns, childrenData);
    }
  } catch (error) {
    console.error('[SubTableInDrawer] 加载子表数据失败:', error);
    errorMessage.value = '加载子表数据失败';
    loading.value = false;
    hasData.value = false;
  }
};

const renderTable = (columns: any[], records: any[]) => {
  if (!containerRef.value) return;

  // 销毁旧实例
  if (tableInstance.value) {
    try { tableInstance.value.release(); } catch { /* ignore */ }
    tableInstance.value = null;
  }

  // 为每列设置最小宽度，避免列被挤压成 ...
  const enhancedColumns = columns.map((col) => ({
    ...col,
    minWidth: col.minWidth || 80, // 最小宽度 120px，列数较多时出现横向滚动条
    width: col.width || undefined,
  }));

  const theme = themes.DEFAULT.extends({
    scrollStyle: { barToSide: true, visible: 'always' },
    headerStyle: { color: '#646A73', fontSize: 13 },
    bodyStyle: { color: '#374151' },
  });

  // 计算表格高度：
  // - 行数 ≤ 5：完整展示所有行，不出现垂直滚动条
  // - 行数 > 5：固定展示 5 行高度 + 垂直滚动条查看剩余
  const rowHeight = 32;
  const headerHeight = 36;
  const minDisplayRows = 5;
  const recordCount = records.length;

  // 通过容器 style 直接设置高度，确保 VTable 能拿到准确高度
  // - 行数 ≤ 5：高度 = 表头 + 所有行 + 边距
  // - 行数 > 5：高度 = 表头 + 5 行 + 边距（出现垂直滚动条）
  const displayRows = Math.min(recordCount, minDisplayRows);
  const containerHeight = headerHeight + displayRows * rowHeight + 8;
  if (containerRef.value) {
    containerRef.value.style.height = `${containerHeight}px`;
  }

  tableInstance.value = new ListTable(containerRef.value, {
    records,
    columns: enhancedColumns,
    defaultRowHeight: rowHeight,
    defaultHeaderRowHeight: headerHeight,
    theme,
    // 使用 standard 模式：列宽按设置渲染，列总宽超过容器时出现横向滚动条
    widthMode: 'standard',
    // 使用固定高度模式，由容器 style.height 控制
    heightMode: 'autoHeight',
    autoWrapText: false,
    showHeader: true,
    disableColumnResize: false,
    emptyTip: '暂无关联记录',
  });

  // 绑定 click_cell 事件：显示放大按钮
  (tableInstance.value as any).on('click_cell', (args: any) => {
    if (args.col === undefined || args.row === undefined) return;
    const cellRecord = (tableInstance.value as any).getCellOriginRecord(args.col, args.row);
    if (!cellRecord) return;

    // 使用原生鼠标事件坐标定位放大按钮
    const nativeEvent = args.event;
    let iconX: number;
    let iconY: number;
    if (nativeEvent && typeof nativeEvent.clientX === 'number') {
      iconX = nativeEvent.clientX + 12;
      iconY = nativeEvent.clientY - 12;
    } else {
      // 回退：使用单元格矩形
      try {
        const cellRect = (tableInstance.value as any).getCellRect(args.col, args.row);
        const containerRect = containerRef.value!.getBoundingClientRect();
        iconX = containerRect.left + cellRect.left + cellRect.width + 8;
        iconY = containerRect.top + cellRect.top;
      } catch {
        return;
      }
    }

    selectedCell.value = {
      x: Math.min(iconX, window.innerWidth - 40),
      y: Math.max(iconY, 4),
      record: cellRecord,
    };
    actionIconVisible.value = true;
  });
};

/** 放大按钮点击 - 触发 expand-record 事件 */
const handleActionIconClick = () => {
  if (!selectedCell.value?.record?._originalRecord) return;
  const original = selectedCell.value.record._originalRecord;
  // 后端返回的 LinkedRecordDetail 转换为 RecordEntity
  const recordEntity: RecordEntity = {
    id: original.id,
    tableId: props.targetTableId,
    values: { ...original.values },
    createdAt: original.created_at ? new Date(original.created_at).getTime() : Date.now(),
    updatedAt: original.updated_at ? new Date(original.updated_at).getTime() : Date.now(),
  };
  emit('expand-record', recordEntity);
  actionIconVisible.value = false;
  selectedCell.value = null;
};

// 监听 props 变化重新加载
watch(
  () => [props.recordId, props.fieldId, props.targetTableId],
  () => {
    hasData.value = false;
    actionIconVisible.value = false;
    selectedCell.value = null;
    loadData();
  },
);

onMounted(() => {
  loadData();
});

onBeforeUnmount(() => {
  if (tableInstance.value) {
    try { tableInstance.value.release(); } catch { /* ignore */ }
    tableInstance.value = null;
  }
});

// 点击容器外区域隐藏放大按钮
const handleDocumentClick = (e: MouseEvent) => {
  if (!actionIconVisible.value) return;
  const target = e.target as HTMLElement;
  if (!target.closest('.subtable-action-icon') && !target.closest('.vtable-action-icon')) {
    actionIconVisible.value = false;
    selectedCell.value = null;
  }
};

onMounted(() => {
  document.addEventListener('click', handleDocumentClick);
});

onBeforeUnmount(() => {
  document.removeEventListener('click', handleDocumentClick);
});
</script>

<template>
  <div class="subtable-in-drawer">
    <div v-if="loading" class="subtable-loading">
      <span>加载中...</span>
    </div>
    <div v-else-if="errorMessage" class="subtable-error">
      <span>{{ errorMessage }}</span>
    </div>
    <div v-else-if="!hasData" class="subtable-empty">
      <span>暂无关联记录</span>
    </div>
    <div
      v-if="hasData && !loading"
      ref="containerRef"
      class="subtable-container">
    </div>

    <!-- 悬浮放大按钮 -->
    <div
      v-if="actionIconVisible && selectedCell"
      class="subtable-action-icon"
      :style="{
        left: selectedCell.x + 'px',
        top: selectedCell.y + 'px',
      }"
      @click.stop="handleActionIconClick"
      @mouseenter="actionIconVisible = true"
      title="查看记录详情">
      <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
        <circle cx="11" cy="11" r="8" />
        <line x1="21" y1="21" x2="16.65" y2="16.65" />
        <line x1="11" y1="8" x2="11" y2="14" />
        <line x1="8" y1="11" x2="14" y2="11" />
      </svg>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.subtable-in-drawer {
  position: relative;
  margin-top: 8px;
  border: 1px solid #e5e7eb;
  border-radius: 6px;
  overflow: hidden;
  background: #ffffff;
}

.subtable-container {
  width: 100%;
  /* 高度由 renderTable 中根据记录行数动态设置 style.height
     - 行数 ≤ 5：完整展示所有行
     - 行数 > 5：限高 5 行 + 垂直滚动条 */
  overflow: hidden;
}

.subtable-loading,
.subtable-error,
.subtable-empty {
  padding: 16px;
  text-align: center;
  color: #6b7280;
  font-size: 13px;
}

.subtable-action-icon {
  position: fixed;
  z-index: 3000;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #ffffff;
  border: 1px solid #d1d5db;
  border-radius: 50%;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
  cursor: pointer;
  color: #4b5563;
  transition: all 0.2s;

  &:hover {
    background: #f3f4f6;
    border-color: #9ca3af;
    color: #1f2937;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
  }
}
</style>
