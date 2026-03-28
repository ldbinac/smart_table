import { db } from "../schema";
import type { TableEntity, FieldEntity } from "../schema";
import { generateId } from "../../utils/id";

export interface CreateTableData {
  baseId: string;
  name: string;
  description?: string;
}

export class TableService {
  async createTable(data: CreateTableData): Promise<TableEntity> {
    const tables = await db.tableEntities
      .where("baseId")
      .equals(data.baseId)
      .toArray();
    const maxOrder =
      tables.length > 0 ? Math.max(...tables.map((t) => t.order)) : -1;

    const primaryFieldId = generateId();

    const table: TableEntity = {
      id: generateId(),
      baseId: data.baseId,
      name: data.name,
      description: data.description,
      primaryFieldId,
      recordCount: 0,
      order: maxOrder + 1,
      isStarred: false,
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };

    await db.transaction("rw", [db.tableEntities, db.fields], async () => {
      await db.tableEntities.add(table);

      const primaryField: FieldEntity = {
        id: primaryFieldId,
        tableId: table.id,
        name: "主键",
        type: "text",
        isPrimary: true,
        isSystem: true,
        isRequired: true,
        order: 0,
        createdAt: Date.now(),
        updatedAt: Date.now(),
      };
      await db.fields.add(primaryField);
    });

    return table;
  }

  async getTable(id: string): Promise<TableEntity | undefined> {
    return db.tableEntities.get(id);
  }

  async getTablesByBase(baseId: string): Promise<TableEntity[]> {
    return db.tableEntities.where("baseId").equals(baseId).sortBy("order");
  }

  async updateTable(id: string, changes: Partial<TableEntity>): Promise<void> {
    await db.tableEntities.update(id, {
      ...changes,
      updatedAt: Date.now(),
    });
  }

  async updateRecordCount(tableId: string): Promise<void> {
    const count = await db.records.where("tableId").equals(tableId).count();
    await db.tableEntities.update(tableId, {
      recordCount: count,
      updatedAt: Date.now(),
    });
  }

  async deleteTable(id: string): Promise<void> {
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
  }

  async reorderTables(_baseId: string, tableIds: string[]): Promise<void> {
    await db.transaction("rw", db.tableEntities, async () => {
      for (let i = 0; i < tableIds.length; i++) {
        await db.tableEntities.update(tableIds[i], { order: i });
      }
    });
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
