/**
 * Dashboard API 服务
 */
import { apiClient } from '@/api/client';
import type { Dashboard, DashboardWidget } from '@/api/types';

export const getDashboards = async (baseId: string): Promise<Dashboard[]> => {
  return apiClient.get<Dashboard[]>(`/bases/${baseId}/dashboards`);
};

export const getDashboard = async (id: string): Promise<Dashboard> => {
  return apiClient.get<Dashboard>(`/dashboards/${id}`);
};

export const createDashboard = async (data: Partial<Dashboard>): Promise<Dashboard> => {
  return apiClient.post<Dashboard>('/dashboards', data);
};

export const updateDashboard = async (id: string, data: Partial<Dashboard>): Promise<Dashboard> => {
  return apiClient.put<Dashboard>(`/dashboards/${id}`, data);
};

export const deleteDashboard = async (id: string): Promise<void> => {
  await apiClient.delete<void>(`/dashboards/${id}`);
};

export const dashboardApiService = {
  getDashboards,
  getDashboard,
  createDashboard,
  updateDashboard,
  deleteDashboard
};

export default dashboardApiService;
