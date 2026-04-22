import { db } from '../schema';
import type { Attachment } from '../schema';
import { generateId } from '@/utils/id';
import type {
  AttachmentFile,
  AttachmentFieldOptions,
  AttachmentFileType
} from '@/types/attachment';
import {
  getFileType,
  getFileExtension,
  isImageFile,
  isVideoFile
} from '@/types/attachment';
import {
  validateFiles,
  checkStorageSpace
} from '@/utils/attachment';
import {
  generateThumbnail,
  generateVideoThumbnail
} from '@/utils/attachment';
import {
  createAttachmentNotFoundError
} from '@/utils/attachment';
import { attachmentApiService } from '@/services/api/attachmentApiService';

/**
 * 上传上下文
 */
export interface UploadContext {
  recordId: string;
  fieldId: string;
  tableId: string;
  baseId: string;
}

/**
 * 上传进度回调
 */
export type UploadProgressCallback = (progress: number, currentFile: string) => void;

/**
 * 附件服务类
 */
export class AttachmentService {
  /**
   * 上传文件到附件字段
   */
  async uploadFiles(
    files: File[],
    context: UploadContext,
    options?: AttachmentFieldOptions,
    onProgress?: UploadProgressCallback
  ): Promise<AttachmentFile[]> {
    // 获取现有附件
    const existingAttachments = await this.getAttachmentsByField(
      context.recordId,
      context.fieldId
    );

    // 校验文件
    const validation = validateFiles(files, existingAttachments, options);
    if (!validation.valid) {
      throw validation.error;
    }

    // 检查存储空间
    const totalSize = files.reduce((sum, f) => sum + f.size, 0);
    const spaceCheck = await checkStorageSpace(totalSize);
    if (!spaceCheck.valid) {
      throw spaceCheck.error;
    }

    const results: AttachmentFile[] = [];

    for (let i = 0; i < files.length; i++) {
      const file = files[i];
      onProgress?.(Math.round((i / files.length) * 100), file.name);

      const attachmentFile = await this.uploadSingleFile(file, context, options);
      results.push(attachmentFile);
    }

    onProgress?.(100, '');
    return results;
  }

  /**
   * 上传单个文件
   */
  private async uploadSingleFile(
    file: File,
    context: UploadContext,
    options?: AttachmentFieldOptions
  ): Promise<AttachmentFile> {
    // 调用后端 API 上传文件
    const uploadResult = await attachmentApiService.uploadFile(
      file,
      {
        table_id: context.tableId,
        record_id: context.recordId,
        field_id: context.fieldId
      }
    );

    // 从后端返回的数据构建 AttachmentFile
    const attachmentData = uploadResult.attachment;
    const attachmentFile: AttachmentFile = {
      id: attachmentData.id,
      name: attachmentData.filename || file.name,
      originalName: attachmentData.original_name || file.name,
      size: attachmentData.file_size || file.size,
      type: attachmentData.mime_type || file.type || 'application/octet-stream',
      fileType: getFileType(attachmentData.mime_type || file.type) as AttachmentFileType,
      extension: getFileExtension(file.name),
      thumbnail: attachmentData.thumbnail_url,
      url: attachmentData.url,
      createdAt: new Date(attachmentData.created_at).getTime()
    };

    // 同时保存到本地 IndexedDB 以便离线访问
    try {
      const arrayBuffer = await file.arrayBuffer();
      const blob = new Blob([arrayBuffer], { type: file.type });

      // 生成缩略图用于本地预览
      let thumbnailBlob: Blob | undefined;
      const enableThumbnail = options?.enableThumbnail !== false;

      if (enableThumbnail) {
        try {
          if (isImageFile(file)) {
            thumbnailBlob = await generateThumbnail(file, options);
          } else if (isVideoFile(file)) {
            thumbnailBlob = await generateVideoThumbnail(file, {
              maxWidth: options?.thumbnailMaxWidth,
              maxHeight: options?.thumbnailMaxHeight,
              quality: options?.thumbnailQuality
            });
          }
        } catch (error) {
          console.warn('本地缩略图生成失败:', error);
        }
      }

      const localAttachment: Attachment = {
        id: attachmentData.id,
        recordId: context.recordId,
        fieldId: context.fieldId,
        tableId: context.tableId,
        baseId: context.baseId,
        name: file.name,
        originalName: file.name,
        size: file.size,
        type: file.type || 'application/octet-stream',
        fileType: getFileType(file.type) as AttachmentFileType,
        extension: getFileExtension(file.name),
        data: blob,
        thumbnail: thumbnailBlob,
        createdAt: Date.now()
      };

      await db.attachments.add(localAttachment);
    } catch (error) {
      console.warn('本地缓存附件失败:', error);
      // 本地缓存失败不影响主流程
    }

    return attachmentFile;
  }

  /**
   * 获取附件
   */
  async getAttachment(attachmentId: string): Promise<Attachment | undefined> {
    return db.attachments.get(attachmentId);
  }

  /**
   * 获取附件文件元数据
   */
  async getAttachmentFile(attachmentId: string): Promise<AttachmentFile | undefined> {
    // 首先尝试从本地 IndexedDB 获取
    const localAttachment = await this.getAttachment(attachmentId);
    if (localAttachment) {
      return this.toAttachmentFile(localAttachment);
    }

    // 如果本地没有，从后端 API 获取
    try {
      const apiAttachment = await attachmentApiService.getAttachment(attachmentId);
      if (apiAttachment) {
        return {
          id: apiAttachment.id,
          name: apiAttachment.filename || apiAttachment.original_name,
          originalName: apiAttachment.original_name,
          size: apiAttachment.file_size,
          type: apiAttachment.mime_type,
          fileType: getFileType(apiAttachment.mime_type) as AttachmentFileType,
          extension: getFileExtension(apiAttachment.original_name || apiAttachment.filename || ''),
          url: apiAttachment.url,
          thumbnail: apiAttachment.thumbnail_url,
          createdAt: new Date(apiAttachment.created_at).getTime()
        };
      }
    } catch (error) {
      console.error('从后端获取附件详情失败:', error);
    }

    return undefined;
  }

  /**
   * 获取记录的所有附件
   */
  async getAttachmentsByRecord(recordId: string): Promise<Attachment[]> {
    return db.attachments.where('recordId').equals(recordId).toArray();
  }

  /**
   * 获取字段的所有附件
   */
  async getAttachmentsByField(recordId: string, fieldId: string): Promise<AttachmentFile[]> {
    const attachments = await db.attachments
      .where({ recordId, fieldId })
      .toArray();

    return attachments.map(att => this.toAttachmentFile(att));
  }

  /**
   * 下载附件
   */
  async downloadAttachment(attachmentId: string): Promise<void> {
    // 首先尝试从本地 IndexedDB 获取
    const localAttachment = await this.getAttachment(attachmentId);

    if (localAttachment && localAttachment.data) {
      // 本地有数据，使用本地数据下载
      const url = URL.createObjectURL(localAttachment.data);

      try {
        const link = document.createElement('a');
        link.href = url;
        link.download = localAttachment.originalName || localAttachment.name;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      } finally {
        setTimeout(() => URL.revokeObjectURL(url), 1000);
      }
      return;
    }

    // 本地没有，从后端 API 下载
    try {
      // 首先获取附件元数据
      const attachmentFile = await this.getAttachmentFile(attachmentId);
      if (!attachmentFile) {
        throw createAttachmentNotFoundError(attachmentId);
      }

      // 从后端下载文件 Blob
      const blob = await attachmentApiService.downloadAttachment(attachmentId);

      // 创建 Blob URL 并下载
      const url = URL.createObjectURL(blob);

      try {
        const link = document.createElement('a');
        link.href = url;
        link.download = attachmentFile.originalName || attachmentFile.name;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
      } finally {
        setTimeout(() => URL.revokeObjectURL(url), 1000);
      }
    } catch (error) {
      console.error('从后端下载附件失败:', error);
      throw error;
    }
  }

  /**
   * 获取附件的 Blob URL（用于预览）
   */
  async getAttachmentUrl(attachmentId: string): Promise<string> {
    const attachment = await this.getAttachment(attachmentId);
    if (!attachment) {
      throw createAttachmentNotFoundError(attachmentId);
    }

    return URL.createObjectURL(attachment.data);
  }

  /**
   * 获取附件的缩略图 URL
   */
  async getThumbnailUrl(attachmentId: string): Promise<string | undefined> {
    const attachment = await this.getAttachment(attachmentId);
    if (!attachment) {
      throw createAttachmentNotFoundError(attachmentId);
    }

    if (attachment.thumbnail) {
      return URL.createObjectURL(attachment.thumbnail);
    }

    return undefined;
  }

  /**
   * 删除附件
   */
  async deleteAttachment(attachmentId: string): Promise<void> {
    const attachment = await this.getAttachment(attachmentId);
    if (!attachment) {
      throw createAttachmentNotFoundError(attachmentId);
    }

    await db.attachments.delete(attachmentId);
  }

  /**
   * 批量删除附件
   */
  async batchDeleteAttachments(attachmentIds: string[]): Promise<void> {
    await db.attachments.bulkDelete(attachmentIds);
  }

  /**
   * 删除记录的所有附件
   */
  async deleteAttachmentsByRecord(recordId: string): Promise<number> {
    const attachments = await this.getAttachmentsByRecord(recordId);
    const ids = attachments.map(att => att.id);
    await db.attachments.bulkDelete(ids);
    return ids.length;
  }

  /**
   * 复制附件到新记录
   */
  async copyAttachments(
    sourceRecordId: string,
    targetRecordId: string,
    fieldMapping?: Record<string, string>
  ): Promise<AttachmentFile[]> {
    const sourceAttachments = await this.getAttachmentsByRecord(sourceRecordId);
    const results: AttachmentFile[] = [];

    for (const sourceAtt of sourceAttachments) {
      const newAttachment: Attachment = {
        ...sourceAtt,
        id: generateId(),
        recordId: targetRecordId,
        fieldId: fieldMapping?.[sourceAtt.fieldId] || sourceAtt.fieldId,
        createdAt: Date.now()
      };

      await db.attachments.add(newAttachment);
      results.push(this.toAttachmentFile(newAttachment));
    }

    return results;
  }

  /**
   * 获取附件统计信息
   */
  async getAttachmentStats(recordId: string): Promise<{
    count: number;
    totalSize: number;
    byType: Record<string, number>;
  }> {
    const attachments = await this.getAttachmentsByRecord(recordId);

    const byType: Record<string, number> = {};
    let totalSize = 0;

    for (const att of attachments) {
      totalSize += att.size;
      byType[att.fileType] = (byType[att.fileType] || 0) + 1;
    }

    return {
      count: attachments.length,
      totalSize,
      byType
    };
  }

  /**
   * 清理孤立的附件（没有对应记录的附件）
   */
  async cleanupOrphanedAttachments(): Promise<number> {
    const allAttachments = await db.attachments.toArray();
    const recordIds = new Set(await db.records.toCollection().primaryKeys());

    const orphanedIds: string[] = [];
    for (const att of allAttachments) {
      if (!recordIds.has(att.recordId)) {
        orphanedIds.push(att.id);
      }
    }

    if (orphanedIds.length > 0) {
      await db.attachments.bulkDelete(orphanedIds);
    }

    return orphanedIds.length;
  }

  /**
   * 获取存储使用情况
   */
  async getStorageUsage(): Promise<{
    totalAttachments: number;
    totalSize: number;
    byBase: Record<string, { count: number; size: number }>;
  }> {
    const attachments = await db.attachments.toArray();

    let totalSize = 0;
    const byBase: Record<string, { count: number; size: number }> = {};

    for (const att of attachments) {
      totalSize += att.size;

      if (!byBase[att.baseId]) {
        byBase[att.baseId] = { count: 0, size: 0 };
      }
      byBase[att.baseId].count++;
      byBase[att.baseId].size += att.size;
    }

    return {
      totalAttachments: attachments.length,
      totalSize,
      byBase
    };
  }

  /**
   * 将 Attachment 转换为 AttachmentFile
   */
  private toAttachmentFile(attachment: Attachment): AttachmentFile {
    const file: AttachmentFile = {
      id: attachment.id,
      name: attachment.name,
      originalName: attachment.originalName,
      size: attachment.size,
      type: attachment.type,
      fileType: attachment.fileType as AttachmentFileType,
      extension: attachment.extension,
      createdAt: attachment.createdAt
    };

    // 如果有缩略图，创建 Blob URL
    if (attachment.thumbnail) {
      file.thumbnail = URL.createObjectURL(attachment.thumbnail);
    }

    return file;
  }
}

// 导出单例
export const attachmentService = new AttachmentService();
