/**
 * 关联字段类型定义
 */

/** 关联关系类型 */
export type RelationshipType = "one_to_one" | "one_to_many" | "many_to_one" | "many_to_many";

/** 关联关系类型标签映射 */
export const RELATIONSHIP_TYPE_LABELS: Record<RelationshipType, string> = {
  one_to_one: "一对一",
  one_to_many: "一对多",
  many_to_one: "多对一",
  many_to_many: "多对多",
};

/** 获取反向关联类型 */
export function getInverseRelationshipType(type: RelationshipType): RelationshipType {
  const mapping: Record<RelationshipType, RelationshipType> = {
    one_to_one: "one_to_one",
    one_to_many: "many_to_one",
    many_to_one: "one_to_many",
    many_to_many: "many_to_many",
  };
  return mapping[type];
}

/** 关联关系 */
export interface LinkRelation {
  id: string;
  source_table_id: string;
  target_table_id: string;
  source_field_id: string;
  target_field_id?: string;
  relationship_type: RelationshipType;
  bidirectional: boolean;
  created_at: string;
  updated_at: string;
}

/** 关联值 */
export interface LinkValue {
  id: string;
  link_relation_id: string;
  source_record_id: string;
  target_record_id: string;
  created_at: string;
}

/** 关联记录 */
export interface LinkedRecord {
  record_id: string;
  display_value: string;
  record?: {
    id: string;
    values: Record<string, unknown>;
  };
}

/** 出站关联（当前记录关联到其他记录） */
export interface OutboundLink {
  field_id: string;
  field_name: string;
  target_table_id: string;
  target_table_name: string;
  linked_records: LinkedRecord[];
}

/** 入站关联（其他记录关联到当前记录） */
export interface InboundLink {
  field_id: string;
  field_name: string;
  source_table_id: string;
  source_table_name: string;
  linked_records: LinkedRecord[];
}

/** 记录的完整关联数据 */
export interface RecordLinks {
  outbound: OutboundLink[];
  inbound: InboundLink[];
}

/** 关联字段配置 */
export interface LinkFieldConfig {
  linkedTableId: string;
  relationshipType: RelationshipType;
  displayFieldId?: string;
  bidirectional?: boolean;
}
