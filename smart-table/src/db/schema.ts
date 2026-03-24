import Dexie from 'dexie';
import type { Table as DexieTable } from 'dexie';
import type { CellValue } from '../types';

export interface Base {
  id: string;
  name: string;
  description?: string;
  icon?: string;
  color?: string;
  isStarred: boolean;
  createdAt: number;
  updatedAt: number;
}

export interface TableEntity {
  id: string;
  baseId: string;
  name: string;
  description?: string;
  primaryFieldId: string;
  recordCount: number;
  order: number;
  isStarred: boolean;
  createdAt: number;
  updatedAt: number;
}

export interface FieldEntity {
  id: string;
  tableId: string;
  name: string;
  type: string;
  options?: Record<string, unknown>;
  isPrimary: boolean;
  isSystem: boolean;
  isRequired: boolean;
  defaultValue?: CellValue;
  description?: string;
  order: number;
  createdAt: number;
  updatedAt: number;
}

export interface RecordEntity {
  id: string;
  tableId: string;
  values: Record<string, CellValue>;
  createdAt: number;
  updatedAt: number;
  createdBy?: string;
  updatedBy?: string;
}

export interface ViewEntity {
  id: string;
  tableId: string;
  name: string;
  type: string;
  config: Record<string, unknown>;
  filters: unknown[];
  sorts: unknown[];
  groupBys: string[];
  hiddenFields: string[];
  frozenFields: string[];
  rowHeight: 'short' | 'medium' | 'tall';
  isDefault: boolean;
  order: number;
  createdAt: number;
  updatedAt: number;
}

export interface Dashboard {
  id: string;
  baseId: string;
  name: string;
  description?: string;
  widgets: unknown[];
  layout: Record<string, unknown>;
  createdAt: number;
  updatedAt: number;
}

export interface Attachment {
  id: string;
  recordId: string;
  fieldId: string;
  name: string;
  size: number;
  type: string;
  data: Blob;
  thumbnail?: Blob;
  createdAt: number;
}

export interface OperationHistory {
  id: string;
  baseId: string;
  tableId?: string;
  recordId?: string;
  fieldId?: string;
  action: 'create' | 'update' | 'delete';
  entityType: 'base' | 'table' | 'field' | 'record' | 'view';
  oldValue?: unknown;
  newValue?: unknown;
  timestamp: number;
  userId?: string;
}

class SmartTableDB extends Dexie {
  bases!: DexieTable<Base>;
  tableEntities!: DexieTable<TableEntity>;
  fields!: DexieTable<FieldEntity>;
  records!: DexieTable<RecordEntity>;
  views!: DexieTable<ViewEntity>;
  dashboards!: DexieTable<Dashboard>;
  attachments!: DexieTable<Attachment>;
  history!: DexieTable<OperationHistory>;

  constructor() {
    super('SmartTableDB');

    this.version(3).stores({
      bases: 'id, name, updatedAt, isStarred',
      tableEntities: 'id, baseId, name, order, updatedAt, isStarred',
      fields: 'id, tableId, name, type, order, [tableId+order]',
      records: 'id, tableId, updatedAt, [tableId+updatedAt]',
      views: 'id, tableId, name, type, isDefault, [tableId+order]',
      dashboards: 'id, baseId, name, updatedAt',
      attachments: 'id, recordId, fieldId, [recordId+fieldId]',
      history: '++id, baseId, tableId, timestamp, [baseId+timestamp]'
    });
  }
}

export const db = new SmartTableDB();
