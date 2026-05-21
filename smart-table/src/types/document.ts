/**
 * 文档类型定义
 */

export interface Document {
  id: string;
  baseId: string;
  base_id?: string;
  name: string;
  content: string;
  contentFormat: 'delta' | 'markdown';
  content_format?: 'delta' | 'markdown';
  order: number;
  isPinned: boolean;
  is_pinned?: boolean;
  createdBy?: string;
  created_by?: string;
  updatedBy?: string;
  updated_by?: string;
  createdAt: number | string;
  created_at?: number | string;
  updatedAt: number | string;
  updated_at?: number | string;
}

export interface DocumentCreateRequest {
  name: string;
  content?: string;
  contentFormat?: 'delta' | 'markdown';
}

export interface DocumentUpdateRequest {
  name?: string;
  content?: string;
  contentFormat?: 'delta' | 'markdown';
  order?: number;
  isPinned?: boolean;
}
