import type { AttachmentFieldOptions, AttachmentFile } from '@/types/attachment';
import {
  AttachmentErrorCode,
  type AttachmentErrorCodeType,
  AttachmentError,
  createFileTooLargeError,
  createFileTypeNotAllowedError,
  createFileCountExceededError,
  createTotalSizeExceededError,
  createReadError
} from './errors';
import { isFileTypeAllowed, getFileExtension } from '@/types/attachment';
import { DEFAULT_ATTACHMENT_LIMITS } from '@/types/attachment';

/**
 * 文件校验结果
 */
export interface ValidationResult {
  valid: boolean;
  error?: AttachmentError;
}

/**
 * 校验单个文件
 */
export function validateFile(
  file: File,
  options?: AttachmentFieldOptions
): ValidationResult {
  // 检查文件是否为空
  if (!file || file.size === 0) {
    return {
      valid: false,
      error: new AttachmentError(
        '文件不能为空',
        AttachmentErrorCode.FILE_EMPTY as AttachmentErrorCodeType,
        { fileName: file?.name }
      )
    };
  }

  // 检查文件大小
  const maxSize = options?.maxSize ?? DEFAULT_ATTACHMENT_LIMITS.maxFileSize;
  if (file.size > maxSize) {
    return {
      valid: false,
      error: createFileTooLargeError(file.name, file.size, maxSize)
    };
  }

  // 检查文件类型
  if (options?.acceptTypes || options?.acceptExtensions) {
    const allowed = isFileTypeAllowed(
      file,
      options.acceptTypes,
      options.acceptExtensions
    );
    if (!allowed) {
      return {
        valid: false,
        error: createFileTypeNotAllowedError(file.name, file.type || getFileExtension(file.name))
      };
    }
  }

  return { valid: true };
}

/**
 * 校验多个文件
 */
export function validateFiles(
  files: File[],
  existingFiles: AttachmentFile[],
  options?: AttachmentFieldOptions
): ValidationResult {
  // 检查文件数量
  const maxCount = options?.maxCount ?? DEFAULT_ATTACHMENT_LIMITS.maxFileCount;
  const totalCount = existingFiles.length + files.length;
  if (totalCount > maxCount) {
    return {
      valid: false,
      error: createFileCountExceededError(totalCount, maxCount)
    };
  }

  // 检查总大小
  const maxTotalSize = options?.maxTotalSize ?? DEFAULT_ATTACHMENT_LIMITS.maxTotalSize;
  const existingSize = existingFiles.reduce((sum, f) => sum + f.size, 0);
  const newSize = files.reduce((sum, f) => sum + f.size, 0);
  const totalSize = existingSize + newSize;
  if (totalSize > maxTotalSize) {
    return {
      valid: false,
      error: createTotalSizeExceededError(totalSize, maxTotalSize)
    };
  }

  // 逐个校验文件
  for (const file of files) {
    const result = validateFile(file, options);
    if (!result.valid) {
      return result;
    }
  }

  return { valid: true };
}

/**
 * 校验文件数量是否满足最小要求
 */
export function validateMinFileCount(
  files: AttachmentFile[],
  minCount?: number
): ValidationResult {
  if (minCount && minCount > 0 && files.length < minCount) {
    return {
      valid: false,
      error: new AttachmentError(
        `至少需要 ${minCount} 个文件，当前只有 ${files.length} 个`,
        AttachmentErrorCode.INVALID_OPERATION as AttachmentErrorCodeType,
        { minCount, currentCount: files.length }
      )
    };
  }
  return { valid: true };
}

/**
 * 异步读取文件为 DataURL
 */
export function readFileAsDataURL(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = () => reject(createReadError(file.name, '读取失败'));
    reader.readAsDataURL(file);
  });
}

/**
 * 异步读取文件为 Blob
 */
export function readFileAsBlob(file: File): Promise<Blob> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => {
      if (reader.result instanceof ArrayBuffer) {
        resolve(new Blob([reader.result]));
      } else {
        reject(createReadError(file.name, '格式转换失败'));
      }
    };
    reader.onerror = () => reject(createReadError(file.name, '读取失败'));
    reader.readAsArrayBuffer(file);
  });
}

/**
 * 异步读取文件为 ArrayBuffer
 */
export function readFileAsArrayBuffer(file: File): Promise<ArrayBuffer> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as ArrayBuffer);
    reader.onerror = () => reject(createReadError(file.name, '读取失败'));
    reader.readAsArrayBuffer(file);
  });
}

/**
 * 检查存储空间是否充足（估算）
 */
export async function checkStorageSpace(
  requiredBytes: number
): Promise<ValidationResult> {
  try {
    if ('storage' in navigator && 'estimate' in navigator.storage) {
      const estimate = await navigator.storage.estimate();
      const quota = estimate.quota ?? 0;
      const usage = estimate.usage ?? 0;
      const available = quota - usage;

      if (available < requiredBytes) {
        return {
          valid: false,
          error: new AttachmentError(
            `存储空间不足，可用空间 ${formatFileSize(available)}，需要 ${formatFileSize(requiredBytes)}`,
            AttachmentErrorCode.STORAGE_QUOTA_EXCEEDED as AttachmentErrorCodeType,
            { available, required: requiredBytes }
          )
        };
      }
    }
    return { valid: true };
  } catch {
    // 如果无法获取存储估算，允许操作继续
    return { valid: true };
  }
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
