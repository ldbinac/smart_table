import type { RecordEntity, FieldEntity } from "../db/schema";
import { FieldType } from "../types";

export interface GroupNode {
  key: string;
  value: string;
  records: RecordEntity[];
  children?: GroupNode[];
  isExpanded?: boolean;
  count: number;
  aggregations?: Record<string, number | string>;
}

export interface GroupConfig {
  fieldIds: string[];
  showAggregations?: boolean;
  aggregationFields?: string[];
}

export function groupRecords(
  records: RecordEntity[],
  config: GroupConfig,
  fields: FieldEntity[],
): GroupNode[] {
  if (!config.fieldIds || config.fieldIds.length === 0) {
    return [
      {
        key: "all",
        value: "全部",
        records,
        count: records.length,
      },
    ];
  }

  return groupByField(records, config.fieldIds, 0, fields, config);
}

function groupByField(
  records: RecordEntity[],
  fieldIds: string[],
  level: number,
  fields: FieldEntity[],
  config: GroupConfig,
): GroupNode[] {
  if (level >= fieldIds.length) {
    return [];
  }

  const fieldId = fieldIds[level];
  const field = fields.find((f) => f.id === fieldId);
  if (!field) {
    return [];
  }

  const groups: Map<string, RecordEntity[]> = new Map();

  for (const record of records) {
    const groupKey = getGroupKey(record.values[fieldId], field);
    if (!groups.has(groupKey)) {
      groups.set(groupKey, []);
    }
    groups.get(groupKey)!.push(record);
  }

  const sortedGroups = sortGroups(groups, field);

  const result: GroupNode[] = sortedGroups.map(([key, groupRecords]) => {
    const node: GroupNode = {
      key,
      value: getGroupDisplayValue(key, field),
      records: groupRecords,
      count: groupRecords.length,
      isExpanded: level === 0,
    };

    if (level < fieldIds.length - 1) {
      node.children = groupByField(
        groupRecords,
        fieldIds,
        level + 1,
        fields,
        config,
      );
    }

    if (config.showAggregations && config.aggregationFields) {
      node.aggregations = calculateAggregations(
        groupRecords,
        config.aggregationFields,
        fields,
      );
    }

    return node;
  });

  return result;
}

function getGroupKey(value: unknown, field: FieldEntity): string {
  if (value === null || value === undefined || value === "") {
    return "__empty__";
  }

  switch (field.type) {
    case FieldType.SINGLE_SELECT: {
      if (typeof value === "object" && value !== null) {
        return (value as { id?: string }).id || String(value);
      }
      return String(value);
    }

    case FieldType.MULTI_SELECT: {
      if (Array.isArray(value) && value.length > 0) {
        return value
          .map((v) =>
            typeof v === "object" && v !== null
              ? (v as { id?: string }).id || String(v)
              : String(v),
          )
          .sort()
          .join("|");
      }
      return "__empty__";
    }

    case FieldType.DATE:
    case FieldType.CREATED_TIME:
    case FieldType.UPDATED_TIME: {
      const timestamp =
        typeof value === "number" ? value : Date.parse(String(value));
      if (isNaN(timestamp)) return "__empty__";
      const date = new Date(timestamp);
      return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}-${String(date.getDate()).padStart(2, "0")}`;
    }

    case FieldType.CHECKBOX:
      return value ? "__checked__" : "__unchecked__";

    case FieldType.MEMBER: {
      if (Array.isArray(value) && value.length > 0) {
        return value
          .map((v) =>
            typeof v === "object" && v !== null
              ? (v as { id?: string }).id || String(v)
              : String(v),
          )
          .sort()
          .join("|");
      }
      return "__empty__";
    }

    default:
      return String(value);
  }
}

function getGroupDisplayValue(key: string, field: FieldEntity): string {
  if (key === "__empty__") {
    return "空值";
  }

  switch (field.type) {
    case FieldType.SINGLE_SELECT: {
      const options = field.options?.options as
        | Array<{ id: string; name: string }>
        | undefined;
      if (options) {
        const option = options.find((opt) => opt.id === key);
        if (option) return option.name;
      }
      return key;
    }

    case FieldType.MULTI_SELECT:
    case FieldType.MEMBER: {
      const options = field.options?.options as
        | Array<{ id: string; name: string }>
        | undefined;
      if (options) {
        return key
          .split("|")
          .map((id) => {
            const option = options.find((opt) => opt.id === id);
            return option ? option.name : id;
          })
          .join(", ");
      }
      return key.split("|").join(", ");
    }

    case FieldType.CHECKBOX:
      return key === "__checked__" ? "已勾选" : "未勾选";

    case FieldType.DATE:
    case FieldType.CREATED_TIME:
    case FieldType.UPDATED_TIME:
      return key;

    default:
      return key;
  }
}

function sortGroups(
  groups: Map<string, RecordEntity[]>,
  field: FieldEntity,
): [string, RecordEntity[]][] {
  const entries = Array.from(groups.entries());

  if (
    field.type === FieldType.SINGLE_SELECT ||
    field.type === FieldType.MULTI_SELECT
  ) {
    const options = field.options?.options as
      | Array<{ id: string; name: string }>
      | undefined;
    if (options) {
      entries.sort((a, b) => {
        if (a[0] === "__empty__") return 1;
        if (b[0] === "__empty__") return -1;

        const aIndex = options.findIndex(
          (opt) => opt.id === a[0] || a[0].includes(opt.id),
        );
        const bIndex = options.findIndex(
          (opt) => opt.id === b[0] || b[0].includes(opt.id),
        );

        if (aIndex !== -1 && bIndex !== -1) return aIndex - bIndex;
        if (aIndex !== -1) return -1;
        if (bIndex !== -1) return 1;

        return a[0].localeCompare(b[0], "zh-CN");
      });
      return entries;
    }
  }

  if (
    field.type === FieldType.DATE ||
    field.type === FieldType.CREATED_TIME ||
    field.type === FieldType.UPDATED_TIME
  ) {
    entries.sort((a, b) => {
      if (a[0] === "__empty__") return 1;
      if (b[0] === "__empty__") return -1;
      return a[0].localeCompare(b[0]);
    });
    return entries;
  }

  if (
    field.type === FieldType.NUMBER ||
    field.type === FieldType.RATING ||
    field.type === FieldType.PROGRESS
  ) {
    entries.sort((a, b) => {
      if (a[0] === "__empty__") return 1;
      if (b[0] === "__empty__") return -1;
      const aNum = parseFloat(a[0]);
      const bNum = parseFloat(b[0]);
      if (!isNaN(aNum) && !isNaN(bNum)) return aNum - bNum;
      return a[0].localeCompare(b[0]);
    });
    return entries;
  }

  entries.sort((a, b) => {
    if (a[0] === "__empty__") return 1;
    if (b[0] === "__empty__") return -1;
    return a[0].localeCompare(b[0], "zh-CN");
  });

  return entries;
}

function calculateAggregations(
  records: RecordEntity[],
  aggregationFields: string[],
  fields: FieldEntity[],
): Record<string, number | string> {
  const result: Record<string, number | string> = {};

  for (const fieldId of aggregationFields) {
    const field = fields.find((f) => f.id === fieldId);
    if (!field) continue;

    const values = records
      .map((r) => r.values[fieldId])
      .filter((v) => v !== null && v !== undefined && v !== "");

    if (
      field.type === FieldType.NUMBER ||
      field.type === FieldType.RATING ||
      field.type === FieldType.PROGRESS
    ) {
      const numbers = values
        .map((v) => {
          if (typeof v === "number") return v;
          if (typeof v === "string") return parseFloat(v);
          return 0;
        })
        .filter((n) => !isNaN(n));

      if (numbers.length > 0) {
        result[`${fieldId}_sum`] = numbers.reduce((a, b) => a + b, 0);
        result[`${fieldId}_avg`] =
          numbers.reduce((a, b) => a + b, 0) / numbers.length;
        result[`${fieldId}_min`] = Math.min(...numbers);
        result[`${fieldId}_max`] = Math.max(...numbers);
      }
    }

    result[`${fieldId}_count`] = values.length;
  }

  return result;
}

export function flattenGroupTree(
  nodes: GroupNode[],
  level: number = 0,
): Array<{ node: GroupNode; level: number }> {
  const result: Array<{ node: GroupNode; level: number }> = [];

  for (const node of nodes) {
    result.push({ node, level });

    if (node.isExpanded && node.children) {
      result.push(...flattenGroupTree(node.children, level + 1));
    }
  }

  return result;
}

export function toggleGroupExpansion(
  nodes: GroupNode[],
  key: string,
): GroupNode[] {
  return nodes.map((node) => {
    if (node.key === key) {
      return { ...node, isExpanded: !node.isExpanded };
    }

    if (node.children) {
      return {
        ...node,
        children: toggleGroupExpansion(node.children, key),
      };
    }

    return node;
  });
}

export function expandAllGroups(nodes: GroupNode[]): GroupNode[] {
  return nodes.map((node) => ({
    ...node,
    isExpanded: true,
    children: node.children ? expandAllGroups(node.children) : undefined,
  }));
}

export function collapseAllGroups(nodes: GroupNode[]): GroupNode[] {
  return nodes.map((node) => ({
    ...node,
    isExpanded: false,
    children: node.children ? collapseAllGroups(node.children) : undefined,
  }));
}

export function getGroupPath(
  nodes: GroupNode[],
  key: string,
  path: GroupNode[] = [],
): GroupNode[] | null {
  for (const node of nodes) {
    if (node.key === key) {
      return [...path, node];
    }

    if (node.children) {
      const result = getGroupPath(node.children, key, [...path, node]);
      if (result) return result;
    }
  }

  return null;
}

export function countAllRecords(nodes: GroupNode[]): number {
  return nodes.reduce((sum, node) => {
    if (node.children) {
      return sum + countAllRecords(node.children);
    }
    return sum + node.count;
  }, 0);
}

export function countVisibleRecords(nodes: GroupNode[]): number {
  return nodes.reduce((sum, node) => {
    if (node.isExpanded && node.children) {
      return sum + countVisibleRecords(node.children);
    }
    return sum + node.records.length;
  }, 0);
}
