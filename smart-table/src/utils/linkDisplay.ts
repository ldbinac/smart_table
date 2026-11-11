/**
 * 关联字段显示值的通用处理。
 *
 * 后端 /records/links[/batch] 把双向关联同时以 outgoing / incoming 返回（互为镜像），
 * 反向字段的关联经常只存在于 incoming 一侧；同时后端解析显示字段失败时会用记录 ID
 * 作为 display_value 兜底。表格单元格、导出、关联选择器都必须统一处理这两点，
 * 否则会出现「关联 1 条」、界面显示裸 UUID 等问题。
 */

/** 接口返回的单个字段关联分组 */
export interface LinkGroup {
  field_id: string;
  linked_records?: Array<{ record_id?: string; display_value?: string | null }>;
}

/** 接口返回的单条记录关联数据 */
export interface RecordLinksData {
  outbound?: LinkGroup[];
  inbound?: LinkGroup[];
}

export interface LinkDisplayRecord {
  record_id: string;
  display_value: string;
}

/** 兼容导出模块此前暴露的类型名 */
export type ExportLinkGroup = LinkGroup;
export type ExportRecordLinks = RecordLinksData;

/**
 * 合并单条记录、单个字段的 outbound / inbound 关联显示值。
 *
 * - 双向关联下两个方向互为镜像：按 record_id 去重，outgoing 优先；
 * - 显示值等于记录 ID 时视为后端兜底值，不作为显示名使用；
 * - 按 record_id 而非显示名去重，同名但不同的记录都会被保留。
 */
export function collectLinkDisplayRecords(
  links: RecordLinksData | undefined,
  fieldId: string,
): LinkDisplayRecord[] {
  const result: LinkDisplayRecord[] = [];
  const seen = new Set<string>();

  const collect = (list?: LinkGroup[]) => {
    for (const group of list || []) {
      if (!group || group.field_id !== fieldId) continue;
      for (const item of group.linked_records || []) {
        if (!item || item.display_value == null || item.display_value === "") continue;
        const displayValue = String(item.display_value);
        const recordId = String(item.record_id ?? `display:${displayValue}`);
        // 后端解析失败时 display_value 就是记录 ID，不能当成显示名
        if (displayValue === recordId) continue;
        if (seen.has(recordId)) continue;
        seen.add(recordId);
        result.push({ record_id: recordId, display_value: displayValue });
      }
    }
  };

  collect(links?.outbound);
  collect(links?.inbound);
  return result;
}

/**
 * 批量构建导出上下文使用的显示名映射：recordId -> (fieldId -> 显示名列表)。
 */
export function buildLinkDisplayMap(
  batch: Record<string, RecordLinksData | undefined>,
): Map<string, Map<string, string[]>> {
  const linkDisplayMap = new Map<string, Map<string, string[]>>();
  for (const [recId, links] of Object.entries(batch)) {
    const fieldIds = new Set<string>();
    for (const group of [...(links?.outbound || []), ...(links?.inbound || [])]) {
      if (group?.field_id) fieldIds.add(group.field_id);
    }
    const fieldMap = new Map<string, string[]>();
    for (const fieldId of fieldIds) {
      fieldMap.set(
        fieldId,
        collectLinkDisplayRecords(links, fieldId).map((r) => r.display_value),
      );
    }
    linkDisplayMap.set(recId, fieldMap);
  }
  return linkDisplayMap;
}

/**
 * 格式化关联字段单元格的原始值（ID 或 ID 数组）。
 * 有显示名映射时输出名称，解析不到时输出空串，绝不暴露裸记录 ID。
 */
export function formatLinkCellValue(
  value: unknown,
  fieldMap?: Map<string, string>,
): string {
  const ids = Array.isArray(value)
    ? value.map((v) => String(v))
    : value === null || value === undefined || value === ""
      ? []
      : [String(value)];
  if (ids.length === 0) return "";

  const names: string[] = [];
  for (const id of ids) {
    const name = fieldMap?.get(id);
    // 映射缺失或仍是 ID 兜底值时不显示
    if (name && name !== id && !names.includes(name)) names.push(name);
  }
  return names.join(", ");
}

/** 判断一个值是不是「记录 ID 被当成显示值」的兜底数据 */
export function isRawRecordIdDisplay(value: unknown, recordId: string): boolean {
  if (value === null || value === undefined || value === "") return true;
  const text = String(value);
  return text === recordId || text === `display:${recordId}`;
}
