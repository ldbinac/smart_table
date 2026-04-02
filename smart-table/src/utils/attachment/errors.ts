/**
 * 附件错误代码常量
 */
export const AttachmentErrorCode = {
  // 文件校验错误
  FILE_TOO_LARGE: 'FILE_TOO_LARGE',
  FILE_TYPE_NOT_ALLOWED: 'FILE_TYPE_NOT_ALLOWED',
  FILE_COUNT_EXCEEDED: 'FILE_COUNT_EXCEEDED',
  TOTAL_SIZE_EXCEEDED: 'TOTAL_SIZE_EXCEEDED',
  FILE_EMPTY: 'FILE_EMPTY',

  // 存储错误
  STORAGE_FULL: 'STORAGE_FULL',
  STORAGE_ERROR: 'STORAGE_ERROR',
  STORAGE_QUOTA_EXCEEDED: 'STORAGE_QUOTA_EXCEEDED',

  // 文件处理错误
  READ_ERROR: 'READ_ERROR',
  THUMBNAIL_ERROR: 'THUMBNAIL_ERROR',
  COMPRESSION_ERROR: 'COMPRESSION_ERROR',

  // 业务错误
  ATTACHMENT_NOT_FOUND: 'ATTACHMENT_NOT_FOUND',
  PERMISSION_DENIED: 'PERMISSION_DENIED',
  INVALID_OPERATION: 'INVALID_OPERATION',

  // 网络错误（云存储）
  NETWORK_ERROR: 'NETWORK_ERROR',
  UPLOAD_TIMEOUT: 'UPLOAD_TIMEOUT',
  DOWNLOAD_TIMEOUT: 'DOWNLOAD_TIMEOUT'
} as const;

export type AttachmentErrorCodeType = typeof AttachmentErrorCode[keyof typeof AttachmentErrorCode];

/**
 * 附件错误类
 */
export class AttachmentError extends Error {
  code: AttachmentErrorCodeType;
  details?: Record<string, unknown>;

  constructor(
    message: string,
    code: AttachmentErrorCodeType,
    details?: Record<string, unknown>
  ) {
    super(message);
    this.name = 'AttachmentError';
    this.code = code;
    this.details = details;
  }
}

/**
 * 创建文件过大错误
 */
export function createFileTooLargeError(
  fileName: string,
  fileSize: number,
  maxSize: number
): AttachmentError {
  return new AttachmentError(
    `文件 "${fileName}" (${formatFileSize(fileSize)}) 超过大小限制 ${formatFileSize(maxSize)}`,
    AttachmentErrorCode.FILE_TOO_LARGE,
    { fileName, fileSize, maxSize }
  );
}

/**
 * 创建文件类型不允许错误
 */
export function createFileTypeNotAllowedError(
  fileName: string,
  fileType: string
): AttachmentError {
  return new AttachmentError(
    `文件 "${fileName}" 的类型 "${fileType}" 不被允许`,
    AttachmentErrorCode.FILE_TYPE_NOT_ALLOWED,
    { fileName, fileType }
  );
}

/**
 * 创建文件数量超限错误
 */
export function createFileCountExceededError(
  currentCount: number,
  maxCount: number
): AttachmentError {
  return new AttachmentError(
    `文件数量超过限制，当前 ${currentCount} 个，最多允许 ${maxCount} 个`,
    AttachmentErrorCode.FILE_COUNT_EXCEEDED,
    { currentCount, maxCount }
  );
}

/**
 * 创建总大小超限错误
 */
export function createTotalSizeExceededError(
  currentSize: number,
  maxTotalSize: number
): AttachmentError {
  return new AttachmentError(
    `文件总大小超过限制，当前 ${formatFileSize(currentSize)}，最多允许 ${formatFileSize(maxTotalSize)}`,
    AttachmentErrorCode.TOTAL_SIZE_EXCEEDED,
    { currentSize, maxTotalSize }
  );
}

/**
 * 创建附件未找到错误
 */
export function createAttachmentNotFoundError(attachmentId: string): AttachmentError {
  return new AttachmentError(
    `附件不存在或已被删除 (ID: ${attachmentId})`,
    AttachmentErrorCode.ATTACHMENT_NOT_FOUND,
    { attachmentId }
  );
}

/**
 * 创建存储空间不足错误
 */
export function createStorageFullError(): AttachmentError {
  return new AttachmentError(
    '存储空间不足，请清理不必要的附件后重试',
    AttachmentErrorCode.STORAGE_FULL
  );
}

/**
 * 创建文件读取错误
 */
export function createReadError(fileName: string, reason?: string): AttachmentError {
  return new AttachmentError(
    `文件 "${fileName}" 读取失败${reason ? ': ' + reason : ''}`,
    AttachmentErrorCode.READ_ERROR,
    { fileName, reason }
  );
}

/**
 * 格式化文件大小
 */
function formatFileSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  if (bytes < 1024 * 1024 * 1024) return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  return (bytes / (1024 * 1024 * 1024)).toFixed(1) + ' GB';
}
