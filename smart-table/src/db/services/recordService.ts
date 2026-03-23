import { db } from '../schema';
import type { RecordEntity } from '../schema';
import { generateId } from '../../utils/id';
import type { CellValue } from '../../types';
import { tableService } from './tableService';

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
    const record: RecordEntity = {
      id: generateId(),
      tableId: data.tableId,
      values: data.values,
      createdAt: Date.now(),
      updatedAt: Date.now(),
      createdBy: data.createdBy,
      updatedBy: data.updatedBy
    };

    await db.transaction('rw', [db.records, db.tableEntities], async () => {
      await db.records.add(record);
      await tableService.updateRecordCount(data.tableId);
    });

    return record;
  }

  async getRecord(id: string): Promise<RecordEntity | undefined> {
    return db.records.get(id);
  }

  async getRecordsByTable(tableId: string): Promise<RecordEntity[]> {
    return db.records.where('tableId').equals(tableId).toArray();
  }

  async getRecordsByTableSorted(tableId: string, limit?: number): Promise<RecordEntity[]> {
    let query = db.records.where('tableId').equals(tableId).sortBy('updatedAt');
    if (limit) {
      const all = await query;
      return all.reverse().slice(0, limit);
    }
    const result = await query;
    return result.reverse();
  }

  async updateRecord(id: string, data: UpdateRecordData): Promise<void> {
    const record = await this.getRecord(id);
    if (!record) return;

    await db.records.update(id, {
      values: data.values,
      updatedAt: Date.now(),
      updatedBy: data.updatedBy
    });
  }

  async deleteRecord(id: string): Promise<void> {
    const record = await this.getRecord(id);
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
        const record: RecordEntity = {
          id: generateId(),
          tableId,
          values: data.values,
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

    return createdRecords;
  }

  async batchUpdateRecords(updates: { id: string; values: Record<string, CellValue> }[]): Promise<void> {
    await db.transaction('rw', db.records, async () => {
      for (const update of updates) {
        await db.records.update(update.id, {
          values: update.values,
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
