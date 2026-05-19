/**
 * 文档类型定义
 */

export interface Document {
  id: string;
  baseId: string;
  name: string;
  content: string;
  contentFormat: 'delta' | 'markdown';
  order: number;
  isPinned: boolean;
  createdBy?: string;
  updatedBy?: string;
  createdAt: number;
  updatedAt: number;
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
