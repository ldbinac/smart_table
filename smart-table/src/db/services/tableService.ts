import { db } from "../schema";
import type { TableEntity, FieldEntity, ViewEntity } from "../schema";
import { generateId } from "../../utils/id";
import { tableApiService } from "@/services/api/tableApiService";

export interface CreateTableData {
  baseId: string;
  name: string;
  description?: string;
}

export class TableService {
  async createTable(data: CreateTableData): Promise<TableEntity> {
    try {
      // 先调用后端 API 创建表格
      const apiTable = await tableApiService.createTable(data.baseId, {
        name: data.name,
        description: data.description,
      });

      // 将后端返回的表格保存到本地 IndexedDB
      const localTable: TableEntity = {
        id: apiTable.id,
        baseId: apiTable.base_id,
        name: apiTable.name,
        description: apiTable.description,
        primaryFieldId: apiTable.primary_field_id,
        recordCount: apiTable.record_count || 0,
        order: apiTable.order ?? 0,
        isStarred: apiTable.is_starred || false,
        createdAt: new Date(apiTable.created_at).getTime(),
        updatedAt: new Date(apiTable.updated_at).getTime(),
      };

      await db.tableEntities.add(localTable);

      // 后端 API 已经创建了默认字段和视图，从后端获取并保存到本地
      const fields = await tableApiService.getTable(apiTable.id).then(() => []); // 实际应该调用 getFields API
      const views = []; // 实际应该调用 getViews API

      // 如果没有从后端获取字段和视图，创建默认的
      if (fields.length === 0) {
        const primaryField: FieldEntity = {
          id: apiTable.primary_field_id,
          tableId: apiTable.id,
          name: "主键",
          type: "text",
          isPrimary: true,
          isSystem: true,
          isRequired: true,
          isVisible: false,
          order: 0,
          createdAt: Date.now(),
          updatedAt: Date.now(),
        };
        await db.fields.add(primaryField);
      }

      if (views.length === 0) {
        const defaultView: ViewEntity = {
          id: generateId(),
          tableId: apiTable.id,
          name: "表格视图",
          type: "table",
          config: {},
          filters: [],
          sorts: [],
          groupBys: [],
          hiddenFields: [],
          frozenFields: [],
          rowHeight: "medium",
          isDefault: true,
          order: 0,
          createdAt: Date.now(),
          updatedAt: Date.now(),
        };
        await db.views.add(defaultView);
      }

      return localTable;
    } catch (error) {
      console.error("[tableService] createTable failed:", error);
      throw error;
    }
  }

  async getTable(id: string): Promise<TableEntity | undefined> {
    return db.tableEntities.get(id);
  }

  async getTablesByBase(baseId: string): Promise<TableEntity[]> {
    try {
      // 先从后端 API 获取最新数据
      const apiTables = await tableApiService.getTables(baseId);

      // 将后端返回的表格保存到本地 IndexedDB
      await db.transaction("rw", db.tableEntities, async () => {
        for (const apiTable of apiTables) {
          const localTable: TableEntity = {
            id: apiTable.id,
            baseId: apiTable.base_id,
            name: apiTable.name,
            description: apiTable.description,
            primaryFieldId: apiTable.primary_field_id,
            recordCount: apiTable.record_count || 0,
            order: apiTable.order ?? 0,
            isStarred: apiTable.is_starred || false,
            createdAt: new Date(apiTable.created_at).getTime(),
            updatedAt: new Date(apiTable.updated_at).getTime(),
          };

          await db.tableEntities.put(localTable);
        }
      });

      // 从本地 IndexedDB 返回排序后的表格列表
      return db.tableEntities.where("baseId").equals(baseId).sortBy("order");
    } catch (error) {
      console.error("[tableService] getTablesByBase failed:", error);
      // 如果 API 调用失败，从本地缓存读取
      return db.tableEntities.where("baseId").equals(baseId).sortBy("order");
    }
  }

  async updateTable(id: string, changes: Partial<TableEntity>): Promise<void> {
    try {
      // 先调用后端 API 更新表格
      await tableApiService.updateTable(id, changes as any);

      // 再更新本地 IndexedDB
      await db.tableEntities.update(id, {
        ...changes,
        updatedAt: Date.now(),
      });
    } catch (error) {
      console.error("[tableService] updateTable failed:", error);
      throw error;
    }
  }

  async updateRecordCount(tableId: string): Promise<void> {
    const count = await db.records.where("tableId").equals(tableId).count();
    await db.tableEntities.update(tableId, {
      recordCount: count,
      updatedAt: Date.now(),
    });
  }

  async deleteTable(id: string): Promise<void> {
    try {
      // 先调用后端 API 删除表格
      await tableApiService.deleteTable(id);

      // 再从本地 IndexedDB 删除
      await db.transaction(
        "rw",
        [db.tableEntities, db.fields, db.records, db.views],
        async () => {
          await db.fields.where("tableId").equals(id).delete();
          await db.records.where("tableId").equals(id).delete();
          await db.views.where("tableId").equals(id).delete();
          await db.tableEntities.delete(id);
        },
      );
    } catch (error) {
      console.error("[tableService] deleteTable failed:", error);
      throw error;
    }
  }

  async reorderTables(baseId: string, tableIds: string[]): Promise<void> {
    try {
      // 先调用后端 API 更新表格顺序
      const tableOrders = tableIds.map((id, index) => ({
        id,
        order: index,
      }));
      await tableApiService.reorderTables(baseId, tableOrders);

      // 再更新本地 IndexedDB
      await db.transaction("rw", db.tableEntities, async () => {
        for (let i = 0; i < tableIds.length; i++) {
          await db.tableEntities.update(tableIds[i], { order: i });
        }
      });
    } catch (error) {
      console.error("[tableService] reorderTables failed:", error);
      throw error;
    }
  }

  async toggleStarTable(id: string): Promise<void> {
    const table = await db.tableEntities.get(id);
    if (table) {
      await db.tableEntities.update(id, {
        isStarred: !table.isStarred,
        updatedAt: Date.now(),
      });
    }
  }
}

export const tableService = new TableService();
