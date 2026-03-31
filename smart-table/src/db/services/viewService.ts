import { db } from "../schema";
import type { ViewEntity } from "../schema";
import { generateId } from "../../utils/id";
import type { FilterCondition, SortConfig } from "../../types";
import {
  serializeViewConfig,
  deserializeViewConfig,
} from "../../utils/viewConfigSerializer";

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
  rowHeight?: "short" | "medium" | "tall";
  isDefault?: boolean;
  updatedAt?: number;
}

export class ViewService {
  async createView(data: CreateViewData): Promise<ViewEntity> {
    const views = await db.views
      .where("tableId")
      .equals(data.tableId)
      .toArray();
    const maxOrder =
      views.length > 0 ? Math.max(...views.map((v) => v.order)) : -1;

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
      rowHeight: "medium",
      isDefault,
      order: maxOrder + 1,
      createdAt: Date.now(),
      updatedAt: Date.now(),
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
    const views = await db.views
      .where("tableId")
      .equals(tableId)
      .sortBy("order");
    return views.map((view) => {
      if (view.config) {
        view.config = deserializeViewConfig(view.config);
      }
      return view;
    });
  }

  async getDefaultView(tableId: string): Promise<ViewEntity | undefined> {
    const views = await this.getViewsByTable(tableId);
    return views.find((v) => v.isDefault) || views[0];
  }

  async updateView(id: string, data: UpdateViewData): Promise<void> {
    console.log("[ViewService] Updating view:", id, data);
    
    // 先获取当前视图，确保存在
    const existingView = await db.views.get(id);
    if (!existingView) {
      throw new Error(`View with id ${id} not found`);
    }
    console.log("[ViewService] Existing view config:", existingView.config);
    
    if (data.isDefault) {
      await this.clearDefaultViews(existingView.tableId, id);
    }

    // 构建更新数据
    const updateData: Record<string, unknown> = {
      updatedAt: Date.now(),
    };

    // 处理 config - 需要与现有配置合并
    if (data.config) {
      const serializedConfig = serializeViewConfig(data.config);
      console.log("[ViewService] Serialized config:", serializedConfig);
      updateData.config = serializedConfig;
    }
    
    // 添加其他字段
    if (data.name !== undefined) updateData.name = data.name;
    if (data.filters !== undefined) updateData.filters = JSON.parse(JSON.stringify(data.filters));
    if (data.sorts !== undefined) updateData.sorts = JSON.parse(JSON.stringify(data.sorts));
    if (data.groupBys !== undefined) updateData.groupBys = data.groupBys;
    if (data.hiddenFields !== undefined) updateData.hiddenFields = data.hiddenFields;
    if (data.frozenFields !== undefined) updateData.frozenFields = data.frozenFields;
    if (data.rowHeight !== undefined) updateData.rowHeight = data.rowHeight;
    if (data.isDefault !== undefined) updateData.isDefault = data.isDefault;

    console.log("[ViewService] Final update data:", updateData);

    // 使用 Dexie 的 update 方法
    const updateCount = await db.views.update(id, updateData);
    console.log("[ViewService] Update count:", updateCount);

    // 验证更新是否成功
    const updatedView = await db.views.get(id);
    if (updatedView?.config) {
      updatedView.config = deserializeViewConfig(updatedView.config);
    }
    console.log("[ViewService] View after update:", updatedView?.config);
    
    if (updateCount === 0) {
      console.warn("[ViewService] No records were updated!");
    }
  }

  async deleteView(id: string): Promise<void> {
    const view = await this.getView(id);
    if (!view) return;

    if (view.isDefault) {
      const views = await this.getViewsByTable(view.tableId);
      const otherViews = views.filter((v) => v.id !== id);
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
    if (!view) throw new Error("View not found");

    return this.createView({
      tableId: view.tableId,
      name: newName,
      type: view.type,
      isDefault: false,
    });
  }

  async reorderViews(_tableId: string, viewIds: string[]): Promise<void> {
    await db.transaction("rw", db.views, async () => {
      for (let i = 0; i < viewIds.length; i++) {
        await db.views.update(viewIds[i], { order: i });
      }
    });
  }

  private async clearDefaultViews(
    tableId: string,
    exceptId?: string,
  ): Promise<void> {
    const views = await this.getViewsByTable(tableId);
    const defaultViews = views.filter((v) => v.isDefault && v.id !== exceptId);

    for (const view of defaultViews) {
      await db.views.update(view.id, { isDefault: false });
    }
  }
}

export const viewService = new ViewService();
