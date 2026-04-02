/**
 * 附件文件类型分类
 */
export type AttachmentFileType =
  | 'image'      // 图片：jpg, png, gif, webp, svg
  | 'document'   // 文档：pdf, doc, docx, xls, xlsx, ppt, pptx, txt
  | 'video'      // 视频：mp4, webm, mov, avi
  | 'audio'      // 音频：mp3, wav, ogg, m4a
  | 'archive'    // 压缩包：zip, rar, 7z, tar, gz
  | 'other';     // 其他类型

/**
 * 附件文件元数据
 */
export interface AttachmentFile {
  id: string;                    // 唯一标识符
  name: string;                  // 文件名
  originalName: string;          // 原始文件名（保留）
  size: number;                  // 文件大小（字节）
  type: string;                  // MIME 类型
  fileType: AttachmentFileType;  // 文件类型分类
  extension: string;             // 文件扩展名

  // 存储相关
  url?: string;                  // 访问 URL（DataURL 或 Blob URL）
  storagePath?: string;          // 存储路径（用于云存储）

  // 缩略图（图片类型）
  thumbnail?: string;            // 缩略图 DataURL
  thumbnailWidth?: number;       // 缩略图宽度
  thumbnailHeight?: number;      // 缩略图高度

  // 元数据
  description?: string;          // 文件描述
  tags?: string[];               // 标签

  // 系统字段
  createdAt: number;             // 创建时间
  createdBy?: string;            // 创建人
}

/**
 * 附件字段配置选项
 */
export interface AttachmentFieldOptions {
  // 文件类型限制
  acceptTypes?: string[];        // 接受的 MIME 类型，如 ['image/*', 'application/pdf']
  acceptExtensions?: string[];   // 接受的扩展名，如 ['jpg', 'png', 'pdf']

  // 文件大小限制
  maxSize?: number;              // 单个文件最大大小（字节），默认 10MB
  maxTotalSize?: number;         // 总大小限制（字节）

  // 数量限制
  maxCount?: number;             // 最大文件数量，默认无限制
  minCount?: number;             // 最小文件数量（用于校验）

  // 图片处理
  enableThumbnail?: boolean;     // 是否生成缩略图，默认 true
  thumbnailMaxWidth?: number;    // 缩略图最大宽度，默认 200
  thumbnailMaxHeight?: number;   // 缩略图最大高度，默认 200
  thumbnailQuality?: number;     // 缩略图质量 0-1，默认 0.8

  // 存储配置
  storageType?: 'indexeddb' | 'localstorage' | 'memory';  // 存储类型
}

/**
 * 附件上传状态
 */
export interface AttachmentUploadState {
  file: File;
  progress: number;              // 上传进度 0-100
  status: 'pending' | 'uploading' | 'success' | 'error' | 'cancelled';
  error?: string;                // 错误信息
  attachment?: AttachmentFile;   // 上传成功后的附件信息
}

/**
 * 附件预览配置
 */
export interface AttachmentPreviewConfig {
  enableImagePreview: boolean;   // 启用图片预览
  enableVideoPreview: boolean;   // 启用视频预览
  enableAudioPreview: boolean;   // 启用音频预览
  enablePdfPreview: boolean;     // 启用 PDF 预览
  enableOfficePreview: boolean;  // 启用 Office 文档预览（需外部服务）
}

/**
 * 支持的文件类型配置
 */
export const SUPPORTED_FILE_TYPES: Record<AttachmentFileType, string[]> = {
  image: ['jpg', 'jpeg', 'png', 'gif', 'webp', 'svg', 'bmp', 'ico'],
  document: ['pdf', 'doc', 'docx', 'xls', 'xlsx', 'ppt', 'pptx', 'txt', 'md', 'csv'],
  video: ['mp4', 'webm', 'mov', 'avi', 'mkv', 'flv'],
  audio: ['mp3', 'wav', 'ogg', 'm4a', 'aac', 'flac'],
  archive: ['zip', 'rar', '7z', 'tar', 'gz', 'bz2'],
  other: []
};

/**
 * MIME 类型映射
 */
export const MIME_TYPE_MAP: Record<string, string> = {
  'jpg': 'image/jpeg',
  'jpeg': 'image/jpeg',
  'png': 'image/png',
  'gif': 'image/gif',
  'webp': 'image/webp',
  'svg': 'image/svg+xml',
  'bmp': 'image/bmp',
  'ico': 'image/x-icon',
  'pdf': 'application/pdf',
  'doc': 'application/msword',
  'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'xls': 'application/vnd.ms-excel',
  'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  'ppt': 'application/vnd.ms-powerpoint',
  'pptx': 'application/vnd.openxmlformats-officedocument.presentationml.presentation',
  'txt': 'text/plain',
  'md': 'text/markdown',
  'csv': 'text/csv',
  'mp4': 'video/mp4',
  'webm': 'video/webm',
  'mov': 'video/quicktime',
  'avi': 'video/x-msvideo',
  'mkv': 'video/x-matroska',
  'flv': 'video/x-flv',
  'mp3': 'audio/mpeg',
  'wav': 'audio/wav',
  'ogg': 'audio/ogg',
  'm4a': 'audio/mp4',
  'aac': 'audio/aac',
  'flac': 'audio/flac',
  'zip': 'application/zip',
  'rar': 'application/x-rar-compressed',
  '7z': 'application/x-7z-compressed',
  'tar': 'application/x-tar',
  'gz': 'application/gzip',
  'bz2': 'application/x-bzip2'
};

/**
 * 默认限制配置
 */
export const DEFAULT_ATTACHMENT_LIMITS = {
  maxFileSize: 10 * 1024 * 1024,      // 10MB
  maxTotalSize: 100 * 1024 * 1024,    // 100MB
  maxFileCount: 20,                    // 单个字段最多20个文件
  thumbnailMaxWidth: 200,
  thumbnailMaxHeight: 200,
  thumbnailQuality: 0.8
};

/**
 * 获取文件类型分类
 */
export function getFileType(mimeType: string): AttachmentFileType {
  if (mimeType.startsWith('image/')) return 'image';
  if (mimeType.startsWith('video/')) return 'video';
  if (mimeType.startsWith('audio/')) return 'audio';
  if (mimeType.includes('pdf') ||
      mimeType.includes('word') ||
      mimeType.includes('excel') ||
      mimeType.includes('powerpoint') ||
      mimeType.includes('text/') ||
      mimeType.includes('markdown')) return 'document';
  if (mimeType.includes('zip') ||
      mimeType.includes('compressed') ||
      mimeType.includes('tar') ||
      mimeType.includes('gzip')) return 'archive';
  return 'other';
}

/**
 * 获取文件扩展名
 */
export function getFileExtension(filename: string): string {
  const lastDot = filename.lastIndexOf('.');
  return lastDot > 0 ? filename.slice(lastDot + 1).toLowerCase() : '';
}

/**
 * 格式化文件大小
 */
export function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  return (bytes / (1024 * 1024 * 1024)).toFixed(1) + ' GB';
}

/**
 * 检查是否为图片类型
 */
export function isImageFile(file: File | AttachmentFile): boolean {
  return file.type.startsWith('image/') || getFileType(file.type) === 'image';
}

/**
 * 检查是否为视频类型
 */
export function isVideoFile(file: File | AttachmentFile): boolean {
  return file.type.startsWith('video/') || getFileType(file.type) === 'video';
}

/**
 * 检查是否为音频类型
 */
export function isAudioFile(file: File | AttachmentFile): boolean {
  return file.type.startsWith('audio/') || getFileType(file.type) === 'audio';
}

/**
 * 检查文件类型是否被允许
 */
export function isFileTypeAllowed(
  file: File,
  acceptTypes?: string[],
  acceptExtensions?: string[]
): boolean {
  // 如果没有限制，允许所有类型
  if ((!acceptTypes || acceptTypes.length === 0) &&
      (!acceptExtensions || acceptExtensions.length === 0)) {
    return true;
  }

  // 检查 MIME 类型
  if (acceptTypes && acceptTypes.length > 0) {
    for (const acceptType of acceptTypes) {
      // 支持通配符，如 image/*
      if (acceptType.endsWith('/*')) {
        const prefix = acceptType.slice(0, -1);
        if (file.type.startsWith(prefix)) return true;
      } else if (file.type === acceptType) {
        return true;
      }
    }
  }

  // 检查扩展名
  if (acceptExtensions && acceptExtensions.length > 0) {
    const extension = getFileExtension(file.name);
    if (acceptExtensions.includes(extension)) return true;
  }

  return false;
}
