import { apiClient } from '@/api/client';

// ===== 记录评论与 @提及 类型 =====

export interface CommentUserDTO {
  id: string;
  name: string;
  avatar?: string;
}

export interface CommentMentionDTO {
  user_id: string;
  type: 'mention' | 'reply_parent';
}

export interface CommentDTO {
  id: string;
  record_id: string;
  content: string | null;
  parent_id: string | null;
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
  deleted_at: string | null;
  user?: CommentUserDTO | null;
  mentions: CommentMentionDTO[];
  replies: CommentDTO[];
}

export interface CommentPagination {
  page: number;
  per_page: number;
  total: number;
  total_pages: number;
  has_next: boolean;
  has_prev: boolean;
}

export interface CommentListResult {
  data: CommentDTO[];
  meta: { pagination: CommentPagination };
}

export interface NotificationPrefs {
  notify_on_mention: boolean;
  notify_on_reply: boolean;
  notify_on_record_comment: boolean;
}

export interface CreateCommentPayload {
  content: string;
  parent_id?: string | null;
}

export const commentApiService = {
  /** 列出记录评论（分页 + 回复树） */
  async list(
    recordId: string,
    params?: { page?: number; per_page?: number },
  ): Promise<CommentListResult> {
    return apiClient.get<CommentListResult>(
      `/records/${recordId}/comments`,
      params,
    );
  },

  /** 发表评论 / 回复 */
  async create(
    recordId: string,
    payload: CreateCommentPayload,
  ): Promise<CommentDTO> {
    return apiClient.post<CommentDTO>(`/records/${recordId}/comments`, payload);
  },

  /** 编辑自己的评论 */
  async update(commentId: string, content: string): Promise<CommentDTO> {
    return apiClient.put<CommentDTO>(`/comments/${commentId}`, { content });
  },

  /** 删除评论（作者本人或 Editor+） */
  async remove(commentId: string): Promise<void> {
    return apiClient.delete<void>(`/comments/${commentId}`);
  },

  /** 关注 / 取消关注记录（toggle） */
  async toggleFollow(recordId: string): Promise<{ following: boolean }> {
    return apiClient.post<{ following: boolean }>(
      `/records/${recordId}/follow`,
    );
  },

  /** 获取当前用户评论类通知偏好 */
  async getMyPrefs(): Promise<NotificationPrefs> {
    return apiClient.get<NotificationPrefs>('/users/me/notification-prefs');
  },

  /** 更新当前用户评论类通知偏好 */
  async updateMyPrefs(
    payload: Partial<NotificationPrefs>,
  ): Promise<NotificationPrefs> {
    return apiClient.put<NotificationPrefs>(
      '/users/me/notification-prefs',
      payload,
    );
  },
};
