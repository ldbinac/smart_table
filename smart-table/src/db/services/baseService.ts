import { db } from '../schema';
import type { Base, TableEntity } from '../schema';
import { generateId } from '../../utils/id';

export interface CreateBaseData {
  name: string;
  description?: string;
  icon?: string;
  color?: string;
}

export class BaseService {
  async createBase(data: CreateBaseData): Promise<Base> {
    const now = Date.now();
    const base: Base = {
      id: generateId(),
      name: data.name,
      description: data.description || '',
      icon: data.icon || '',
      color: data.color || '#409EFF',
      isStarred: false,
      createdAt: now,
      updatedAt: now
    };
    
    try {
      await db.bases.add(base);
      // 返回一个简单的对象，避免克隆问题
      return { ...base };
    } catch (error) {
      console.error('[baseService] createBase failed:', error);
      throw error;
    }
  }

  async getBase(id: string): Promise<Base | undefined> {
    return db.bases.get(id);
  }

  async getAllBases(): Promise<Base[]> {
    return db.bases.orderBy('updatedAt').reverse().toArray();
  }

  async getStarredBases(): Promise<Base[]> {
    return db.bases.where('isStarred').equals(1).toArray();
  }

  async updateBase(id: string, changes: Partial<Base>): Promise<void> {
    await db.bases.update(id, {
      ...changes,
      updatedAt: Date.now()
    });
  }

  async toggleStar(id: string): Promise<void> {
    const base = await this.getBase(id);
    if (base) {
      await this.updateBase(id, { isStarred: !base.isStarred });
    }
  }

  async deleteBase(id: string): Promise<void> {
    await db.transaction(
      'rw',
      [db.bases, db.tableEntities, db.fields, db.records, db.views, db.dashboards],
      async () => {
        const tables = await db.tableEntities.where('baseId').equals(id).toArray();
        for (const table of tables) {
          await this.deleteTableData(table.id);
        }
        await db.dashboards.where('baseId').equals(id).delete();
        await db.bases.delete(id);
      }
    );
  }

  private async deleteTableData(tableId: string): Promise<void> {
    await db.fields.where('tableId').equals(tableId).delete();
    await db.records.where('tableId').equals(tableId).delete();
    await db.views.where('tableId').equals(tableId).delete();
  }

  async getTablesByBase(baseId: string): Promise<TableEntity[]> {
    return db.tableEntities.where('baseId').equals(baseId).sortBy('order');
  }
}

export const baseService = new BaseService();
