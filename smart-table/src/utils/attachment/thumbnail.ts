import type { AttachmentFieldOptions } from '@/types/attachment';
import { AttachmentError, AttachmentErrorCode, type AttachmentErrorCodeType } from './errors';
import { DEFAULT_ATTACHMENT_LIMITS } from '@/types/attachment';

/**
 * 缩略图生成选项
 */
export interface ThumbnailOptions {
  maxWidth?: number;
  maxHeight?: number;
  quality?: number;
  type?: string;
}

/**
 * 生成图片缩略图
 */
export async function generateThumbnail(
  file: File,
  options?: AttachmentFieldOptions
): Promise<Blob> {
  const maxWidth = options?.thumbnailMaxWidth ?? DEFAULT_ATTACHMENT_LIMITS.thumbnailMaxWidth;
  const maxHeight = options?.thumbnailMaxHeight ?? DEFAULT_ATTACHMENT_LIMITS.thumbnailMaxHeight;
  const quality = options?.thumbnailQuality ?? DEFAULT_ATTACHMENT_LIMITS.thumbnailQuality;

  return new Promise((resolve, reject) => {
    const img = new Image();
    const objectUrl = URL.createObjectURL(file);

    img.onload = () => {
      URL.revokeObjectURL(objectUrl);

      try {
        const canvas = document.createElement('canvas');
        let { width, height } = img;

        // 计算缩放比例，保持宽高比
        if (width > maxWidth || height > maxHeight) {
          const ratio = Math.min(maxWidth / width, maxHeight / height);
          width = Math.floor(width * ratio);
          height = Math.floor(height * ratio);
        }

        canvas.width = width;
        canvas.height = height;

        const ctx = canvas.getContext('2d');
        if (!ctx) {
          reject(new AttachmentError(
            '无法创建 canvas 上下文',
            AttachmentErrorCode.THUMBNAIL_ERROR as AttachmentErrorCodeType
          ));
          return;
        }

        // 使用更好的图像质量
        ctx.imageSmoothingEnabled = true;
        ctx.imageSmoothingQuality = 'high';

        // 绘制图片
        ctx.drawImage(img, 0, 0, width, height);

        // 转换为 Blob
        canvas.toBlob(
          (blob) => {
            if (blob) {
              resolve(blob);
            } else {
              reject(new AttachmentError(
                '缩略图生成失败：无法转换为 Blob',
                AttachmentErrorCode.THUMBNAIL_ERROR as AttachmentErrorCodeType
              ));
            }
          },
          'image/jpeg',
          quality
        );
      } catch (error) {
        reject(new AttachmentError(
          `缩略图生成失败：${error instanceof Error ? error.message : '未知错误'}`,
          AttachmentErrorCode.THUMBNAIL_ERROR as AttachmentErrorCodeType
        ));
      }
    };

    img.onerror = () => {
      URL.revokeObjectURL(objectUrl);
      reject(new AttachmentError(
        '图片加载失败',
        AttachmentErrorCode.THUMBNAIL_ERROR as AttachmentErrorCodeType
      ));
    };

    img.src = objectUrl;
  });
}

/**
 * 生成视频缩略图（取第一帧）
 */
export async function generateVideoThumbnail(
  file: File,
  options?: ThumbnailOptions
): Promise<Blob> {
  const maxWidth = options?.maxWidth ?? DEFAULT_ATTACHMENT_LIMITS.thumbnailMaxWidth;
  const maxHeight = options?.maxHeight ?? DEFAULT_ATTACHMENT_LIMITS.thumbnailMaxHeight;
  const quality = options?.quality ?? DEFAULT_ATTACHMENT_LIMITS.thumbnailQuality;

  return new Promise((resolve, reject) => {
    const video = document.createElement('video');
    const objectUrl = URL.createObjectURL(file);

    video.onloadedmetadata = () => {
      // 设置视频时间为 0（第一帧）或 1 秒（避免黑屏）
      video.currentTime = Math.min(1, video.duration / 10);
    };

    video.onseeked = () => {
      try {
        const canvas = document.createElement('canvas');
        let { videoWidth: width, videoHeight: height } = video;

        // 计算缩放比例
        if (width > maxWidth || height > maxHeight) {
          const ratio = Math.min(maxWidth / width, maxHeight / height);
          width = Math.floor(width * ratio);
          height = Math.floor(height * ratio);
        }

        canvas.width = width;
        canvas.height = height;

        const ctx = canvas.getContext('2d');
        if (!ctx) {
          reject(new AttachmentError(
            '无法创建 canvas 上下文',
            AttachmentErrorCode.THUMBNAIL_ERROR as AttachmentErrorCodeType
          ));
          return;
        }

        ctx.drawImage(video, 0, 0, width, height);

        // 添加播放按钮图标
        drawPlayButton(ctx, width, height);

        canvas.toBlob(
          (blob) => {
            URL.revokeObjectURL(objectUrl);
            if (blob) {
              resolve(blob);
            } else {
              reject(new AttachmentError(
                '视频缩略图生成失败',
                AttachmentErrorCode.THUMBNAIL_ERROR as AttachmentErrorCodeType
              ));
            }
          },
          'image/jpeg',
          quality
        );
      } catch (error) {
        URL.revokeObjectURL(objectUrl);
        reject(new AttachmentError(
          `视频缩略图生成失败：${error instanceof Error ? error.message : '未知错误'}`,
          AttachmentErrorCode.THUMBNAIL_ERROR as AttachmentErrorCodeType
        ));
      }
    };

    video.onerror = () => {
      URL.revokeObjectURL(objectUrl);
      reject(new AttachmentError(
        '视频加载失败',
        AttachmentErrorCode.THUMBNAIL_ERROR as AttachmentErrorCodeType
      ));
    };

    video.src = objectUrl;
    video.load();
  });
}

/**
 * 在缩略图上绘制播放按钮
 */
function drawPlayButton(
  ctx: CanvasRenderingContext2D,
  width: number,
  height: number
): void {
  const buttonSize = Math.min(width, height) * 0.2;
  const centerX = width / 2;
  const centerY = height / 2;

  // 绘制圆形背景
  ctx.beginPath();
  ctx.arc(centerX, centerY, buttonSize, 0, Math.PI * 2);
  ctx.fillStyle = 'rgba(0, 0, 0, 0.6)';
  ctx.fill();

  // 绘制三角形播放图标
  ctx.beginPath();
  ctx.moveTo(centerX - buttonSize * 0.3, centerY - buttonSize * 0.4);
  ctx.lineTo(centerX - buttonSize * 0.3, centerY + buttonSize * 0.4);
  ctx.lineTo(centerX + buttonSize * 0.4, centerY);
  ctx.closePath();
  ctx.fillStyle = 'rgba(255, 255, 255, 0.9)';
  ctx.fill();
}

/**
 * 将 Blob 转换为 DataURL
 */
export function blobToDataURL(blob: Blob): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result as string);
    reader.onerror = () => reject(new Error('Blob 转 DataURL 失败'));
    reader.readAsDataURL(blob);
  });
}

/**
 * 获取文件图标（用于非图片类型的缩略图）
 */
export function getFileIcon(fileType: string): string {
  const iconMap: Record<string, string> = {
    'pdf': '📄',
    'doc': '📝',
    'docx': '📝',
    'xls': '📊',
    'xlsx': '📊',
    'ppt': '📽️',
    'pptx': '📽️',
    'txt': '📃',
    'md': '📑',
    'csv': '📈',
    'zip': '📦',
    'rar': '📦',
    '7z': '📦',
    'mp4': '🎬',
    'webm': '🎬',
    'mov': '🎬',
    'mp3': '🎵',
    'wav': '🎵',
    'ogg': '🎵',
  };

  const extension = fileType.split('/').pop()?.toLowerCase() || '';
  return iconMap[extension] || '📎';
}

/**
 * 创建 SVG 文件图标（用于无法生成缩略图的文件）
 */
export function createFileIconSvg(fileType: string, fileName: string): string {
  const icon = getFileIcon(fileType);
  const extension = fileName.split('.').pop()?.toUpperCase() || 'FILE';

  return `
    <svg xmlns="http://www.w3.org/2000/svg" width="100" height="100" viewBox="0 0 100 100">
      <rect width="100" height="100" fill="#f5f5f5" rx="8"/>
      <text x="50" y="45" font-size="35" text-anchor="middle" dominant-baseline="middle">${icon}</text>
      <text x="50" y="75" font-size="12" text-anchor="middle" fill="#666" font-family="Arial">${extension}</text>
    </svg>
  `;
}

/**
 * 将 SVG 字符串转换为 Blob
 */
export function svgToBlob(svg: string): Blob {
  return new Blob([svg], { type: 'image/svg+xml' });
}
