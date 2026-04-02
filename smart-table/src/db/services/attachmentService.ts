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
  readFileAsArrayBuffer,
  checkStorageSpace
} from '@/utils/attachment';
import {
  generateThumbnail,
  generateVideoThumbnail
} from '@/utils/attachment';
import {
  createAttachmentNotFoundError
} from '@/utils/attachment';

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
    // 读取文件数据
    const arrayBuffer = await readFileAsArrayBuffer(file);
    const blob = new Blob([arrayBuffer], { type: file.type });

    // 生成缩略图
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
        // 缩略图生成失败不影响主流程
        console.warn('缩略图生成失败:', error);
      }
    }

    // 创建附件记录
    const attachment: Attachment = {
      id: generateId(),
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

    // 存储到 IndexedDB
    await db.attachments.add(attachment);

    // 构建返回的元数据
    const attachmentFile: AttachmentFile = {
      id: attachment.id,
      name: attachment.name,
      originalName: attachment.originalName,
      size: attachment.size,
      type: attachment.type,
      fileType: attachment.fileType as AttachmentFileType,
      extension: attachment.extension,
      thumbnail: thumbnailBlob ? URL.createObjectURL(thumbnailBlob) : undefined,
      createdAt: attachment.createdAt
    };

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
    const attachment = await this.getAttachment(attachmentId);
    if (!attachment) return undefined;

    return this.toAttachmentFile(attachment);
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
    const attachment = await this.getAttachment(attachmentId);
    if (!attachment) {
      throw createAttachmentNotFoundError(attachmentId);
    }

    // 创建 Blob URL
    const url = URL.createObjectURL(attachment.data);

    try {
      // 创建下载链接
      const link = document.createElement('a');
      link.href = url;
      link.download = attachment.originalName || attachment.name;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } finally {
      // 清理 URL 对象
      setTimeout(() => URL.revokeObjectURL(url), 1000);
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
