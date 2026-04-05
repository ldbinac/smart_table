/**
 * Dashboard API 服务
 */
import { apiClient } from "@/api/client";
import type { Dashboard, DashboardWidget } from "@/api/types";

export const getDashboards = async (baseId: string): Promise<Dashboard[]> => {
  return apiClient.get<Dashboard[]>(`/bases/${baseId}/dashboards`);
};

export const getDashboard = async (id: string): Promise<Dashboard> => {
  return apiClient.get<Dashboard>(`/dashboards/${id}`);
};

export const createDashboard = async (
  data: Partial<Dashboard> & { base_id?: string },
): Promise<Dashboard> => {
  const { base_id, ...restData } = data;
  // 创建仪表盘需要使用 /bases/{baseId}/dashboards 路由
  if (!base_id) {
    throw new Error("base_id is required for creating dashboard");
  }
  console.log("[DashboardAPI] Creating dashboard:", {
    base_id,
    data: restData,
  });
  const result = await apiClient.post<Dashboard>(
    `/bases/${base_id}/dashboards`,
    restData,
  );
  console.log("[DashboardAPI] Dashboard created:", result);
  return result;
};

export const updateDashboard = async (
  id: string,
  data: Partial<Dashboard>,
): Promise<Dashboard> => {
  return apiClient.put<Dashboard>(`/dashboards/${id}`, data);
};

export const deleteDashboard = async (id: string): Promise<void> => {
  await apiClient.delete<void>(`/dashboards/${id}`);
};

export const duplicateDashboard = async (
  id: string,
  name?: string,
): Promise<Dashboard> => {
  return apiClient.post<Dashboard>(
    `/dashboards/${id}/duplicate`,
    name ? { name } : {},
  );
};

export const addWidget = async (
  dashboardId: string,
  data: Partial<DashboardWidget>,
): Promise<DashboardWidget> => {
  return apiClient.post<DashboardWidget>(
    `/dashboards/${dashboardId}/widgets`,
    data,
  );
};

export const updateWidget = async (
  dashboardId: string,
  widgetId: string,
  data: Partial<DashboardWidget>,
): Promise<DashboardWidget> => {
  return apiClient.put<DashboardWidget>(
    `/dashboards/${dashboardId}/widgets/${widgetId}`,
    data,
  );
};

export const deleteWidget = async (
  dashboardId: string,
  widgetId: string,
): Promise<void> => {
  await apiClient.delete<void>(
    `/dashboards/${dashboardId}/widgets/${widgetId}`,
  );
};

export const updateWidgetsBatch = async (
  dashboardId: string,
  widgets: Array<Partial<DashboardWidget> & { id?: string }>,
): Promise<DashboardWidget[]> => {
  return apiClient.put<DashboardWidget[]>(
    `/dashboards/${dashboardId}/widgets`,
    { widgets },
  );
};

export const updateLayout = async (
  dashboardId: string,
  layoutData: {
    type?: "grid" | "free";
    config?: Record<string, unknown>;
    widgets?: Array<{
      id: string;
      x: number;
      y: number;
      w: number;
      h: number;
      minW?: number;
      minH?: number;
      maxW?: number;
      maxH?: number;
    }>;
  },
): Promise<Dashboard> => {
  return apiClient.put<Dashboard>(
    `/dashboards/${dashboardId}/layout`,
    layoutData,
  );
};

export const setDefaultDashboard = async (
  dashboardId: string,
): Promise<Dashboard> => {
  return apiClient.post<Dashboard>(`/dashboards/${dashboardId}/set-default`);
};

export const dashboardApiService = {
  getDashboards,
  getDashboard,
  createDashboard,
  updateDashboard,
  deleteDashboard,
  duplicateDashboard,
  addWidget,
  updateWidget,
  deleteWidget,
  updateWidgetsBatch,
  updateLayout,
  setDefaultDashboard,
};

export default dashboardApiService;
