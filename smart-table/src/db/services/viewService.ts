import { db } from "../schema";
import type { ViewEntity } from "../schema";
import { generateId } from "../../utils/id";
import type { FilterCondition, SortConfig } from "../../types";
import {
  serializeViewConfig,
  deserializeViewConfig,
} from "../../utils/viewConfigSerializer";
import { viewApiService } from "@/services/api/viewApiService";

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
    try {
      // 先调用后端 API 创建视图
      const apiView = await viewApiService.createView(data.tableId, {
        name: data.name,
        type: data.type,
        config: {},
        filters: [],
        sorts: [],
        description: "",
      });

      // 将后端返回的视图转换为本地格式
      const localView: ViewEntity = {
        id: apiView.id,
        tableId: apiView.table_id || data.tableId,
        name: apiView.name,
        type: apiView.type as string,
        config: apiView.config || {},
        filters: (apiView.filters as FilterCondition[]) || [],
        sorts: (apiView.sorts as SortConfig[]) || [],
        groupBys: (apiView.group_bys as string[]) || [],
        hiddenFields: (apiView.hidden_fields as string[]) || [],
        frozenFields: (apiView.frozen_fields as string[]) || [],
        rowHeight:
          (apiView.row_height as "short" | "medium" | "tall") || "medium",
        isDefault: apiView.is_default || false,
        order: apiView.order ?? 0,
        createdAt: new Date(apiView.created_at).getTime(),
        updatedAt: new Date(apiView.updated_at).getTime(),
      };

      // 保存到本地 IndexedDB
      await db.views.add(localView);
      return localView;
    } catch (error) {
      console.error("[viewService] createView failed:", error);
      throw error;
    }
  }

  async getView(id: string): Promise<ViewEntity | undefined> {
    const view = await db.views.get(id);
    if (view && view.config) {
      view.config = deserializeViewConfig(view.config);
    }
    return view;
  }

  async getViewsByTable(
    tableId: string,
    forceRefresh: boolean = false,
  ): Promise<ViewEntity[]> {
    try {
      // 如果需要强制刷新，先清空本地缓存
      if (forceRefresh) {
        await db.views.where("tableId").equals(tableId).delete();
      }

      // 先从本地 IndexedDB 读取
      const localViews = await db.views
        .where("tableId")
        .equals(tableId)
        .sortBy("order");

      // 如果本地有数据且不需要强制刷新，直接返回（避免重复请求）
      if (localViews.length > 0 && !forceRefresh) {
        return localViews.map((view) => {
          if (view.config) {
            view.config = deserializeViewConfig(view.config);
          }
          return view;
        });
      }

      // 本地没有数据或需要强制刷新，从后端 API 获取
      const apiViews = await viewApiService.getViews(tableId);

      // 将后端返回的视图转换为本地格式并保存
      await db.transaction("rw", db.views, async () => {
        // 先清空本地数据（避免重复）
        await db.views.where("tableId").equals(tableId).delete();

        // 保存新数据
        for (const apiView of apiViews) {
          const localView: ViewEntity = {
            id: apiView.id,
            tableId: apiView.table_id || tableId,
            name: apiView.name,
            type: apiView.type as string,
            config: apiView.config || {},
            filters: (apiView.filters as FilterCondition[]) || [],
            sorts: (apiView.sorts as SortConfig[]) || [],
            groupBys: (apiView.group_bys as string[]) || [],
            hiddenFields: (apiView.hidden_fields as string[]) || [],
            frozenFields: (apiView.frozen_fields as string[]) || [],
            rowHeight:
              (apiView.row_height as "short" | "medium" | "tall") || "medium",
            isDefault: apiView.is_default || false,
            order: apiView.order ?? 0,
            createdAt: new Date(apiView.created_at).getTime(),
            updatedAt: new Date(apiView.updated_at).getTime(),
          };
          await db.views.put(localView);
        }
      });

      // 从本地 IndexedDB 返回
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
    } catch (error) {
      console.error("[viewService] getViewsByTable failed:", error);
      // 如果 API 调用失败，从本地缓存读取
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
  }

  async getDefaultView(tableId: string): Promise<ViewEntity | undefined> {
    const views = await this.getViewsByTable(tableId);
    return views.find((v) => v.isDefault) || views[0];
  }

  async updateView(id: string, data: UpdateViewData): Promise<void> {
    try {
      console.log("[ViewService] Updating view:", id, data);

      // 构建要发送到后端的数据对象，只包含实际有值的字段
      const apiData: Record<string, unknown> = {};

      if (data.name !== undefined) apiData.name = data.name;
      if (data.config !== undefined) apiData.config = data.config;
      if (data.filters !== undefined) apiData.filters = data.filters;
      if (data.sorts !== undefined) apiData.sorts = data.sorts;
      if (data.groupBys !== undefined) apiData.group_bys = data.groupBys;
      if (data.hiddenFields !== undefined)
        apiData.hidden_fields = data.hiddenFields;
      if (data.frozenFields !== undefined)
        apiData.frozen_fields = data.frozenFields;
      if (data.rowHeight !== undefined) apiData.row_height = data.rowHeight;
      if (data.isDefault !== undefined) apiData.is_default = data.isDefault;

      console.log("[ViewService] API data:", apiData);

      // 检查是否有实际要更新的数据
      if (Object.keys(apiData).length === 0) {
        console.warn("[ViewService] No data to update, skipping...");
        return;
      }

      // 先调用后端 API 更新视图
      await viewApiService.updateView(id, apiData);

      // 再更新本地 IndexedDB
      const updateData: Record<string, unknown> = {
        updatedAt: Date.now(),
      };

      // 处理 config - 需要序列化后存储
      if (data.config) {
        const serializedConfig = serializeViewConfig(data.config);
        console.log("[ViewService] Serialized config:", serializedConfig);
        updateData.config = serializedConfig;
      }

      // 添加其他字段
      if (data.name !== undefined) updateData.name = data.name;
      if (data.filters !== undefined)
        updateData.filters = JSON.parse(JSON.stringify(data.filters));
      if (data.sorts !== undefined)
        updateData.sorts = JSON.parse(JSON.stringify(data.sorts));
      if (data.groupBys !== undefined) updateData.groupBys = data.groupBys;
      if (data.hiddenFields !== undefined)
        updateData.hiddenFields = data.hiddenFields;
      if (data.frozenFields !== undefined)
        updateData.frozenFields = data.frozenFields;
      if (data.rowHeight !== undefined) updateData.rowHeight = data.rowHeight;
      if (data.isDefault !== undefined) updateData.isDefault = data.isDefault;

      console.log("[ViewService] Final update data:", updateData);

      // 使用 Dexie 的 update 方法
      const updateCount = await db.views.update(id, updateData);
      console.log("[ViewService] Update count:", updateCount);

      if (updateCount === 0) {
        console.warn("[ViewService] No records were updated!");
      }
    } catch (error) {
      console.error("[viewService] updateView failed:", error);
      throw error;
    }
  }

  async deleteView(id: string): Promise<void> {
    try {
      const view = await this.getView(id);
      if (!view) return;

      // 先调用后端 API 删除视图
      await viewApiService.deleteView(id);

      // 再从本地 IndexedDB 删除
      if (view.isDefault) {
        const views = await this.getViewsByTable(view.tableId);
        const otherViews = views.filter((v) => v.id !== id);
        if (otherViews.length > 0) {
          await this.updateView(otherViews[0].id, { isDefault: true });
        }
      }

      await db.views.delete(id);
    } catch (error) {
      console.error("[viewService] deleteView failed:", error);
      throw error;
    }
  }

  async setDefaultView(id: string): Promise<void> {
    const view = await this.getView(id);
    if (!view) return;

    await this.clearDefaultViews(view.tableId, id);
    await this.updateView(id, { isDefault: true });
  }

  async duplicateView(id: string, newName: string): Promise<ViewEntity> {
    try {
      // 调用后端 API 复制视图
      const apiView = await viewApiService.duplicateView(id, newName);

      // 将后端返回的视图转换为本地格式
      const localView: ViewEntity = {
        id: apiView.id,
        tableId: apiView.table_id || (await this.getView(id))?.tableId || "",
        name: apiView.name,
        type: apiView.type as string,
        config: apiView.config || {},
        filters: (apiView.filters as FilterCondition[]) || [],
        sorts: (apiView.sorts as SortConfig[]) || [],
        groupBys: (apiView.group_bys as string[]) || [],
        hiddenFields: (apiView.hidden_fields as string[]) || [],
        frozenFields: (apiView.frozen_fields as string[]) || [],
        rowHeight:
          (apiView.row_height as "short" | "medium" | "tall") || "medium",
        isDefault: apiView.is_default || false,
        order: apiView.order ?? 0,
        createdAt: new Date(apiView.created_at).getTime(),
        updatedAt: new Date(apiView.updated_at).getTime(),
      };

      // 保存到本地 IndexedDB
      await db.views.add(localView);
      return localView;
    } catch (error) {
      console.error("[viewService] duplicateView failed:", error);
      throw error;
    }
  }

  async setDefaultView(id: string): Promise<void> {
    try {
      const view = await this.getView(id);
      if (!view) return;

      // 调用后端 API 设置默认视图
      await viewApiService.setDefaultView(view.tableId, id);

      // 更新本地状态
      await this.clearDefaultViews(view.tableId, id);
      await this.updateView(id, { isDefault: true });
    } catch (error) {
      console.error("[viewService] setDefaultView failed:", error);
      throw error;
    }
  }

  async reorderViews(tableId: string, viewIds: string[]): Promise<void> {
    try {
      // 调用后端 API 重新排序视图
      const viewOrders = viewIds.map((id, index) => ({ id, order: index }));
      await viewApiService.reorderViews(tableId, viewOrders);

      // 更新本地 IndexedDB
      await db.transaction("rw", db.views, async () => {
        for (let i = 0; i < viewIds.length; i++) {
          await db.views.update(viewIds[i], { order: i });
        }
      });
    } catch (error) {
      console.error("[viewService] reorderViews failed:", error);
      throw error;
    }
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
