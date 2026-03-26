import { db } from '../schema';
import type { ViewEntity } from '../schema';
import { generateId } from '../../utils/id';
import type { FilterCondition, SortConfig } from '../../types';
import { serializeViewConfig, deserializeViewConfig } from '../../utils/viewConfigSerializer';

export interface CreateViewData {
  tableId: string;
  name: string;
  type: string;
  isDefault?: boolean;
}

export interface UpdateViewData {
  name?: string;
  config?: Record<string, unknown>;
  filters?: FilterCondition[];
  sorts?: SortConfig[];
  groupBys?: string[];
  hiddenFields?: string[];
  frozenFields?: string[];
  rowHeight?: 'short' | 'medium' | 'tall';
  isDefault?: boolean;
  updatedAt?: number;
}

export class ViewService {
  async createView(data: CreateViewData): Promise<ViewEntity> {
    const views = await db.views.where('tableId').equals(data.tableId).toArray();
    const maxOrder = views.length > 0 ? Math.max(...views.map(v => v.order)) : -1;

    let isDefault = data.isDefault ?? false;
    if (isDefault) {
      await this.clearDefaultViews(data.tableId);
    }

    const view: ViewEntity = {
      id: generateId(),
      tableId: data.tableId,
      name: data.name,
      type: data.type,
      config: {},
      filters: [],
      sorts: [],
      groupBys: [],
      hiddenFields: [],
      frozenFields: [],
      rowHeight: 'medium',
      isDefault,
      order: maxOrder + 1,
      createdAt: Date.now(),
      updatedAt: Date.now()
    };

    await db.views.add(view);
    return view;
  }

  async getView(id: string): Promise<ViewEntity | undefined> {
    const view = await db.views.get(id);
    if (view && view.config) {
      view.config = deserializeViewConfig(view.config);
    }
    return view;
  }

  async getViewsByTable(tableId: string): Promise<ViewEntity[]> {
    const views = await db.views.where('tableId').equals(tableId).sortBy('order');
    return views.map(view => {
      if (view.config) {
        view.config = deserializeViewConfig(view.config);
      }
      return view;
    });
  }

  async getDefaultView(tableId: string): Promise<ViewEntity | undefined> {
    const views = await this.getViewsByTable(tableId);
    return views.find(v => v.isDefault) || views[0];
  }

  async updateView(id: string, data: UpdateViewData): Promise<void> {
    console.log("[ViewService] Updating view:", id, data);
    if (data.isDefault) {
      const view = await this.getView(id);
      if (view) {
        await this.clearDefaultViews(view.tableId, id);
      }
    }

    // 序列化配置数据，将数组转换为 JSON 字符串
    const updateData: UpdateViewData = {
      ...data,
      updatedAt: Date.now()
    };
    
    if (data.config) {
      updateData.config = serializeViewConfig(data.config);
      console.log("[ViewService] Serialized config:", updateData.config);
    }
    
    console.log("[ViewService] Update data:", updateData);
    
    await db.views.update(id, updateData);
    
    // 验证更新是否成功
    const updatedView = await this.getView(id);
    console.log("[ViewService] View after update:", updatedView?.config);
  }

  async deleteView(id: string): Promise<void> {
    const view = await this.getView(id);
    if (!view) return;

    if (view.isDefault) {
      const views = await this.getViewsByTable(view.tableId);
      const otherViews = views.filter(v => v.id !== id);
      if (otherViews.length > 0) {
        await this.updateView(otherViews[0].id, { isDefault: true });
      }
    }

    await db.views.delete(id);
  }

  async setDefaultView(id: string): Promise<void> {
    const view = await this.getView(id);
    if (!view) return;

    await this.clearDefaultViews(view.tableId, id);
    await this.updateView(id, { isDefault: true });
  }

  async duplicateView(id: string, newName: string): Promise<ViewEntity> {
    const view = await this.getView(id);
    if (!view) throw new Error('View not found');

    return this.createView({
      tableId: view.tableId,
      name: newName,
      type: view.type,
      isDefault: false
    });
  }

  async reorderViews(_tableId: string, viewIds: string[]): Promise<void> {
    await db.transaction('rw', db.views, async () => {
      for (let i = 0; i < viewIds.length; i++) {
        await db.views.update(viewIds[i], { order: i });
      }
    });
  }

  private async clearDefaultViews(tableId: string, exceptId?: string): Promise<void> {
    const views = await this.getViewsByTable(tableId);
    const defaultViews = views.filter(v => v.isDefault && v.id !== exceptId);

    for (const view of defaultViews) {
      await db.views.update(view.id, { isDefault: false });
    }
  }
}

export const viewService = new ViewService();
