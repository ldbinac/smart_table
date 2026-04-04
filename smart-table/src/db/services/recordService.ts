import { db } from "../schema";
import type { RecordEntity } from "../schema";
import type { CellValue } from "../../types";
import { tableService } from "./tableService";
import { recordApiService } from "@/services/api/recordApiService";
import {
  serializeRecordValues,
  deserializeRecordValues,
} from "../../utils/recordValueSerializer";

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
    try {
      // 先调用后端 API 创建记录
      const apiRecord = await recordApiService.createRecord(data.tableId, {
        ...data.values,
      } as Record<string, unknown>);

      // 将后端返回的记录转换为本地格式
      const localRecord: RecordEntity = {
        id: apiRecord.id,
        tableId: data.tableId,
        values: apiRecord.values as Record<string, CellValue>,
        createdAt: new Date(apiRecord.created_at).getTime(),
        updatedAt: new Date(apiRecord.updated_at).getTime(),
        createdBy: apiRecord.created_by,
        updatedBy: apiRecord.updated_by,
      };

      // 保存到本地 IndexedDB
      await db.transaction("rw", [db.records, db.tableEntities], async () => {
        await db.records.add(localRecord);
        await tableService.updateRecordCount(data.tableId);
      });

      return localRecord;
    } catch (error) {
      console.error("[recordService] createRecord failed:", error);
      throw error;
    }
  }

  async getRecord(id: string): Promise<RecordEntity | undefined> {
    const record = await db.records.get(id);
    if (record) {
      return {
        ...record,
        values: deserializeRecordValues(record.values),
      };
    }
    return undefined;
  }

  async getRecordsByTable(tableId: string): Promise<RecordEntity[]> {
    try {
      // 先从后端 API 获取最新数据
      const apiRecords = await recordApiService.getRecords(tableId);

      // apiRecords 可能是数组（直接返回的 items）或分页对象
      let recordsToProcess: any[] = [];

      if (Array.isArray(apiRecords)) {
        // 如果是数组，直接使用
        recordsToProcess = apiRecords;
      } else if (apiRecords && typeof apiRecords === "object") {
        // 如果是分页对象，提取 data 数组
        recordsToProcess =
          (apiRecords as any).data || (apiRecords as any).items || [];
      }

      // 将后端返回的记录转换为本地格式并保存
      await db.transaction("rw", db.records, async () => {
        for (const apiRecord of recordsToProcess) {
          const localRecord: RecordEntity = {
            id: apiRecord.id,
            tableId: apiRecord.table_id || tableId,
            values: apiRecord.values as Record<string, CellValue>,
            createdAt: new Date(apiRecord.created_at).getTime(),
            updatedAt: new Date(apiRecord.updated_at).getTime(),
            createdBy: apiRecord.created_by,
            updatedBy: apiRecord.updated_by,
          };
          await db.records.put(localRecord);
        }
      });

      // 从本地 IndexedDB 返回
      return db.records.where("tableId").equals(tableId).toArray();
    } catch (error) {
      console.error("[recordService] getRecordsByTable failed:", error);
      // 如果 API 调用失败，从本地缓存读取
      return db.records.where("tableId").equals(tableId).toArray();
    }
  }

  async getRecordsByTableSorted(
    tableId: string,
    limit?: number,
  ): Promise<RecordEntity[]> {
    let query = db.records.where("tableId").equals(tableId).sortBy("updatedAt");
    let records: RecordEntity[];

    if (limit) {
      const all = await query;
      records = all.reverse().slice(0, limit);
    } else {
      const result = await query;
      records = result.reverse();
    }

    return records.map((record) => ({
      ...record,
      values: deserializeRecordValues(record.values),
    }));
  }

  async updateRecord(id: string, data: UpdateRecordData): Promise<void> {
    try {
      // 先调用后端 API 更新记录
      await recordApiService.updateRecord(id, {
        ...data.values,
      } as Record<string, unknown>);

      // 序列化值以支持 IndexedDB 存储
      const serializedValues = serializeRecordValues(
        data.values as Record<string, CellValue>,
      );

      // 构建更新对象，只包含有效的值
      const updateData: any = {
        values: serializedValues,
        updatedAt: Date.now(),
      };

      // 只有在提供了 updatedBy 时才添加
      if (data.updatedBy) {
        updateData.updatedBy = data.updatedBy;
      }

      // 再更新本地 IndexedDB
      await db.records.update(id, updateData);
    } catch (error) {
      console.error("[recordService] updateRecord failed:", error);
      throw error;
    }
  }

  async deleteRecord(id: string): Promise<void> {
    try {
      const record = await this.getRecord(id);
      if (!record) return;

      // 先调用后端 API 删除记录
      await recordApiService.deleteRecord(id);

      // 再从本地 IndexedDB 删除
      await db.transaction("rw", [db.records, db.tableEntities], async () => {
        await db.records.delete(id);
        if (record) {
          await tableService.updateRecordCount(record.tableId);
        }
      });
    } catch (error) {
      console.error("[recordService] deleteRecord failed:", error);
      throw error;
    }
  }

  async batchCreateRecords(
    tableId: string,
    records: CreateRecordData[],
  ): Promise<RecordEntity[]> {
    try {
      // 调用后端 API 批量创建记录
      const response = await recordApiService.batchCreateRecords(
        tableId,
        records.map((r) => ({ values: r.values as Record<string, unknown> })),
      );

      // 将后端返回的记录保存到本地 IndexedDB
      const createdRecords: RecordEntity[] = [];
      await db.transaction("rw", [db.records, db.tableEntities], async () => {
        for (const apiRecord of response.records) {
          const localRecord: RecordEntity = {
            id: apiRecord.id,
            tableId: apiRecord.table_id || tableId,
            values: apiRecord.values as Record<string, CellValue>,
            createdAt: new Date(apiRecord.created_at).getTime(),
            updatedAt: new Date(apiRecord.updated_at).getTime(),
            createdBy: apiRecord.created_by,
            updatedBy: apiRecord.updated_by,
          };
          await db.records.add(localRecord);
          createdRecords.push(localRecord);
        }
        await tableService.updateRecordCount(tableId);
      });

      return createdRecords;
    } catch (error) {
      console.error("[recordService] batchCreateRecords failed:", error);
      throw error;
    }
  }

  async batchUpdateRecords(
    updates: { id: string; values: Record<string, CellValue> }[],
  ): Promise<void> {
    try {
      // 调用后端 API 批量更新记录
      const recordIds = updates.map((u) => u.id);
      const values = updates[0]?.values as Record<string, unknown>;
      await recordApiService.batchUpdateRecords(recordIds, values);

      // 更新本地 IndexedDB
      await db.transaction("rw", db.records, async () => {
        for (const update of updates) {
          await db.records.update(update.id, {
            values: update.values,
            updatedAt: Date.now(),
          });
        }
      });
    } catch (error) {
      console.error("[recordService] batchUpdateRecords failed:", error);
      throw error;
    }
  }

  async batchDeleteRecords(ids: string[]): Promise<void> {
    const records = await db.records.where("id").anyOf(ids).toArray();
    const tableIds = [...new Set(records.map((r) => r.tableId))];

    await db.transaction("rw", [db.records, db.tableEntities], async () => {
      await db.records.bulkDelete(ids);
      for (const tableId of tableIds) {
        await tableService.updateRecordCount(tableId);
      }
    });
  }

  async getRecordCount(tableId: string): Promise<number> {
    return db.records.where("tableId").equals(tableId).count();
  }
}

export const recordService = new RecordService();
