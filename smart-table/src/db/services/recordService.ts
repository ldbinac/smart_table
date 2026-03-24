import { db } from '../schema';
import type { RecordEntity } from '../schema';
import { generateId } from '../../utils/id';
import type { CellValue } from '../../types';
import { tableService } from './tableService';
import { serializeRecordValues, deserializeRecordValues } from '../../utils/recordValueSerializer';

export interface CreateRecordData {
  tableId: string;
  values: Record<string, CellValue>;
  createdBy?: string;
  updatedBy?: string;
}

export interface UpdateRecordData {
  values: Record<string, CellValue>;
  updatedBy?: string;
}

export class RecordService {
  async createRecord(data: CreateRecordData): Promise<RecordEntity> {
    // 序列化值以支持 IndexedDB 存储
    const serializedValues = serializeRecordValues(data.values);
    
    const record: RecordEntity = {
      id: generateId(),
      tableId: data.tableId,
      values: serializedValues,
      createdAt: Date.now(),
      updatedAt: Date.now(),
      createdBy: data.createdBy,
      updatedBy: data.updatedBy
    };

    await db.transaction('rw', [db.records, db.tableEntities], async () => {
      await db.records.add(record);
      await tableService.updateRecordCount(data.tableId);
    });

    // 返回反序列化的记录
    return {
      ...record,
      values: deserializeRecordValues(record.values)
    };
  }

  async getRecord(id: string): Promise<RecordEntity | undefined> {
    const record = await db.records.get(id);
    if (record) {
      return {
        ...record,
        values: deserializeRecordValues(record.values)
      };
    }
    return undefined;
  }

  async getRecordsByTable(tableId: string): Promise<RecordEntity[]> {
    const records = await db.records.where('tableId').equals(tableId).toArray();
    return records.map(record => ({
      ...record,
      values: deserializeRecordValues(record.values)
    }));
  }

  async getRecordsByTableSorted(tableId: string, limit?: number): Promise<RecordEntity[]> {
    let query = db.records.where('tableId').equals(tableId).sortBy('updatedAt');
    let records: RecordEntity[];
    
    if (limit) {
      const all = await query;
      records = all.reverse().slice(0, limit);
    } else {
      const result = await query;
      records = result.reverse();
    }
    
    return records.map(record => ({
      ...record,
      values: deserializeRecordValues(record.values)
    }));
  }

  async updateRecord(id: string, data: UpdateRecordData): Promise<void> {
    const record = await this.getRecord(id);
    if (!record) return;

    // 序列化值以支持 IndexedDB 存储
    const serializedValues = serializeRecordValues(data.values);

    await db.records.update(id, {
      values: serializedValues,
      updatedAt: Date.now(),
      updatedBy: data.updatedBy
    });
  }

  async deleteRecord(id: string): Promise<void> {
    const record = await db.records.get(id);
    if (!record) return;

    await db.transaction('rw', [db.records, db.tableEntities], async () => {
      await db.records.delete(id);
      await tableService.updateRecordCount(record.tableId);
    });
  }

  async batchCreateRecords(tableId: string, records: CreateRecordData[]): Promise<RecordEntity[]> {
    const createdRecords: RecordEntity[] = [];

    await db.transaction('rw', [db.records, db.tableEntities], async () => {
      for (const data of records) {
        // 序列化值以支持 IndexedDB 存储
        const serializedValues = serializeRecordValues(data.values);
        
        const record: RecordEntity = {
          id: generateId(),
          tableId,
          values: serializedValues,
          createdAt: Date.now(),
          updatedAt: Date.now(),
          createdBy: data.createdBy,
          updatedBy: data.updatedBy
        };
        await db.records.add(record);
        createdRecords.push(record);
      }
      await tableService.updateRecordCount(tableId);
    });

    // 返回反序列化的记录
    return createdRecords.map(record => ({
      ...record,
      values: deserializeRecordValues(record.values)
    }));
  }

  async batchUpdateRecords(updates: { id: string; values: Record<string, CellValue> }[]): Promise<void> {
    await db.transaction('rw', db.records, async () => {
      for (const update of updates) {
        // 序列化值以支持 IndexedDB 存储
        const serializedValues = serializeRecordValues(update.values);
        
        await db.records.update(update.id, {
          values: serializedValues,
          updatedAt: Date.now()
        });
      }
    });
  }

  async batchDeleteRecords(ids: string[]): Promise<void> {
    const records = await db.records.where('id').anyOf(ids).toArray();
    const tableIds = [...new Set(records.map(r => r.tableId))];

    await db.transaction('rw', [db.records, db.tableEntities], async () => {
      await db.records.bulkDelete(ids);
      for (const tableId of tableIds) {
        await tableService.updateRecordCount(tableId);
      }
    });
  }

  async getRecordCount(tableId: string): Promise<number> {
    return db.records.where('tableId').equals(tableId).count();
  }
}

export const recordService = new RecordService();
