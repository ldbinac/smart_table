// 导出错误类型
export {
  AttachmentErrorCode,
  AttachmentError,
  createFileTooLargeError,
  createFileTypeNotAllowedError,
  createFileCountExceededError,
  createTotalSizeExceededError,
  createAttachmentNotFoundError,
  createStorageFullError,
  createReadError
} from './errors';

// 导出校验函数
export {
  validateFile,
  validateFiles,
  validateMinFileCount,
  readFileAsDataURL,
  readFileAsBlob,
  readFileAsArrayBuffer,
  checkStorageSpace,
  type ValidationResult
} from './validators';

// 导出缩略图函数
export {
  generateThumbnail,
  generateVideoThumbnail,
  blobToDataURL,
  getFileIcon,
  createFileIconSvg,
  svgToBlob,
  type ThumbnailOptions
} from './thumbnail';
