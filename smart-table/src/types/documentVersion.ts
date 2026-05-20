/**
 * 文档版本历史类型定义
 */

export interface DocumentVersion {
  id: string;
  documentId: string;
  name: string;
  content: string;
  contentFormat: 'delta' | 'markdown';
  versionNumber: number;
  changeSummary: string;
  createdBy?: string;
  createdByName?: string;
  createdAt: number;
}

export interface DocumentVersionListResponse {
  items: DocumentVersion[];
  total: number;
}

export interface RestoreVersionRequest {
  versionId: string;
}
