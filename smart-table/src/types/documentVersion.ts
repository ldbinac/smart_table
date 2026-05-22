/**
 * 文档版本历史类型定义
 */

export interface DocumentVersion {
  id: string;
  documentId?: string;
  document_id?: string;
  name: string;
  content: string;
  contentFormat?: 'delta' | 'markdown';
  content_format?: 'delta' | 'markdown';
  versionNumber?: number;
  version_number?: number;
  changeSummary?: string;
  change_summary?: string;
  createdBy?: string;
  created_by?: string;
  createdByName?: string;
  createdAt: number | string;
  created_at?: string;
}

export interface DocumentVersionListResponse {
  items: DocumentVersion[];
  total: number;
}

export interface RestoreVersionRequest {
  versionId: string;
}
