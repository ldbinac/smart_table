/**
 * Base API 服务
 */
import { apiClient } from "@/api/client";
import type { Base, BaseMember } from "@/api/types";

export const getBases = async (): Promise<Base[]> => {
  return apiClient.get<Base[]>("/bases");
};

export const getBase = async (
  id: string,
  shareToken?: string,
): Promise<Base> => {
  const params = shareToken ? { share_token: shareToken } : undefined;
  return apiClient.get<Base>(`/bases/${id}`, params);
};

export const createBase = async (data: Partial<Base>): Promise<Base> => {
  return apiClient.post<Base>("/bases", data);
};

export const updateBase = async (
  id: string,
  data: Partial<Base>,
): Promise<Base> => {
  return apiClient.put<Base>(`/bases/${id}`, data);
};

export const deleteBase = async (id: string): Promise<void> => {
  await apiClient.delete<void>(`/bases/${id}`);
};

export const starBase = async (id: string): Promise<Base> => {
  return apiClient.post<Base>(`/bases/${id}/star`);
};

export const unstarBase = async (id: string): Promise<Base> => {
  return apiClient.delete<Base>(`/bases/${id}/star`);
};

export const getBaseMembers = async (baseId: string): Promise<BaseMember[]> => {
  return apiClient.get<BaseMember[]>(`/bases/${baseId}/members`);
};

export const addBaseMember = async (
  baseId: string,
  email: string,
  role?: string,
): Promise<BaseMember> => {
  return apiClient.post<BaseMember>(`/bases/${baseId}/members`, {
    email,
    role,
  });
};

export const removeBaseMember = async (
  baseId: string,
  userId: string,
): Promise<void> => {
  await apiClient.delete<void>(`/bases/${baseId}/members/${userId}`);
};

export const baseApiService = {
  getBases,
  getBase,
  createBase,
  updateBase,
  deleteBase,
  starBase,
  unstarBase,
  getBaseMembers,
  addBaseMember,
  removeBaseMember,
};

export default baseApiService;
