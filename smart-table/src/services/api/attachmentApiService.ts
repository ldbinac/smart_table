/**
 * Attachment API 服务
 */
import { apiClient } from '@/api/client';
import type { Attachment, UploadResult } from '@/api/types';

export const uploadFile = async (
  file: File,
  options?: { table_id?: string; record_id?: string; field_id?: string },
  onProgress?: (percent: number) => void
): Promise<UploadResult> => {
  const formData = new FormData();
  formData.append('file', file);
  if (options?.table_id) formData.append('table_id', options.table_id);
  if (options?.record_id) formData.append('record_id', options.record_id);
  if (options?.field_id) formData.append('field_id', options.field_id);

  return apiClient.upload('/attachments/upload', formData, onProgress) as Promise<UploadResult>;
};

export const getAttachment = async (id: string): Promise<Attachment> => {
  return apiClient.get<Attachment>(`/attachments/${id}`);
};

export const downloadAttachment = async (id: string): Promise<Blob> => {
  const response = await apiClient.raw().get(`/attachments/${id}/download`, { responseType: 'blob' });
  return response.data as Blob;
};

export const deleteAttachment = async (id: string): Promise<void> => {
  await apiClient.delete<void>(`/attachments/${id}`);
};

export const initChunkedUpload = async (
  filename: string,
  fileSize: number,
  mimeType: string
): Promise<{ upload_id: string }> => {
  return apiClient.post<{ upload_id: string }>('/attachments/chunked/init', {
    filename,
    file_size: fileSize,
    mime_type: mimeType
  });
};

export const uploadChunk = async (
  uploadId: string,
  chunkIndex: number,
  totalChunks: number,
  chunk: Blob
): Promise<void> => {
  const formData = new FormData();
  formData.append('upload_id', uploadId);
  formData.append('chunk_index', String(chunkIndex));
  formData.append('total_chunks', String(totalChunks));
  formData.append('chunk', chunk);

  await apiClient.upload('/attachments/chunked/upload', formData);
};

export const completeChunkedUpload = async (uploadId: string): Promise<Attachment> => {
  return apiClient.post<Attachment>('/attachments/chunked/complete', { upload_id: uploadId });
};

export const attachmentApiService = {
  uploadFile,
  getAttachment,
  downloadAttachment,
  deleteAttachment,
  initChunkedUpload,
  uploadChunk,
  completeChunkedUpload
};

export default attachmentApiService;
