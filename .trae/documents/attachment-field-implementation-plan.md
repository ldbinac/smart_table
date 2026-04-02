# 附件字段功能完整实现方案

> 基于 SmartTable 项目架构设计，针对 `doc/Todo-Task.md` 中附件字段待实现功能的详细规划

## 一、需求概述

根据 `Todo-Task.md` 文档，附件字段需要实现以下核心功能：

- [ ] 1.4.1 附件字段的上传功能
- [ ] 1.4.2 附件字段的下载功能
- [ ] 1.4.3 附件字段的预览功能（支持图片、文档、视频等格式）
- [ ] 1.4.4 附件字段的删除功能
- [ ] 1.4.5 附件字段的预览功能（重复，合并到 1.4.3）

## 二、数据结构设计

### 2.1 附件元数据类型定义

```typescript
// types/attachment.ts

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
  name: string;                  // 原始文件名
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
```

### 2.2 数据库存储结构

```typescript
// db/schema.ts - Attachment 接口扩展

export interface Attachment {
  id: string;
  recordId: string;
  fieldId: string;
  tableId: string;        // 冗余存储，便于查询
  baseId: string;         // 冗余存储，便于查询
  
  // 文件信息
  name: string;
  originalName: string;
  size: number;
  type: string;
  fileType: AttachmentFileType;
  extension: string;
  
  // 存储数据
  data: Blob;             // 文件二进制数据
  thumbnail?: Blob;       // 缩略图二进制数据
  
  // 元数据
  description?: string;
  tags?: string[];
  
  // 系统字段
  createdAt: number;
  createdBy?: string;
}
```

### 2.3 字段值存储格式

附件字段在 RecordEntity.values 中的存储格式：

```typescript
// 附件字段值类型
interface AttachmentCellValue {
  type: 'attachment';
  files: AttachmentFile[];  // 附件元数据数组（不包含二进制数据）
}

// 实际存储示例
{
  "field_attachment_001": {
    type: "attachment",
    files: [
      {
        id: "att_001",
        name: "document.pdf",
        originalName: "项目需求文档.pdf",
        size: 1024567,
        type: "application/pdf",
        fileType: "document",
        extension: "pdf",
        createdAt: 1712345678901
      }
    ]
  }
}
```

## 三、技术选型说明

### 3.1 存储方案对比

| 方案 | 优点 | 缺点 | 适用场景 |
|------|------|------|----------|
| **IndexedDB** | 容量大(50MB+)、支持结构化数据、异步API | 浏览器兼容性需关注 | **首选方案** |
| LocalStorage | 简单易用 | 容量小(5MB)、同步阻塞、仅支持字符串 | 仅存储配置 |
| Memory | 速度快 | 页面刷新丢失 | 临时缓存 |
| 云存储 | 跨设备同步、容量大 | 需要后端服务、网络依赖 | 未来扩展 |

**决策：采用 IndexedDB 作为主存储方案**

### 3.2 文件格式限制策略

```typescript
// utils/attachment/const.ts

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
  'pdf': 'application/pdf',
  'doc': 'application/msword',
  'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
  'xls': 'application/vnd.ms-excel',
  'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  'mp4': 'video/mp4',
  'mp3': 'audio/mpeg',
  // ... 更多映射
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
```

### 3.3 第三方库选型

| 功能 | 库 | 版本 | 说明 |
|------|-----|------|------|
| 文件上传 | 原生 File API | - | 无需额外依赖 |
| 图片压缩 | browser-image-compression | ^2.0.2 | 客户端图片压缩 |
| PDF 预览 | pdf-lib | ^1.17.1 | PDF 处理 |
| 视频预览 | 原生 HTML5 Video | - | 无需额外依赖 |
| 文件类型检测 | file-type | ^19.0.0 | 文件签名检测 |

## 四、核心功能实现逻辑

### 4.1 文件上传流程

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  选择文件    │ --> │  文件校验    │ --> │  生成缩略图  │ --> │  存储到 DB   │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
                           │                   │                   │
                           v                   v                   v
                    ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
                    │ 格式/大小校验 │     │ 图片压缩处理 │     │ 更新记录值   │
                    │ 数量限制检查 │     │ 缩略图生成  │     │ 触发事件    │
                    └─────────────┘     └─────────────┘     └─────────────┘
```

**核心代码结构：**

```typescript
// services/attachmentService.ts

export class AttachmentService {
  /**
   * 上传文件到附件字段
   */
  async uploadFiles(
    files: File[],
    context: {
      recordId: string;
      fieldId: string;
      tableId: string;
      baseId: string;
    },
    options?: AttachmentFieldOptions,
    onProgress?: (progress: number) => void
  ): Promise<AttachmentFile[]> {
    const results: AttachmentFile[] = [];
    
    for (const file of files) {
      // 1. 校验文件
      const validation = this.validateFile(file, options);
      if (!validation.valid) {
        throw new AttachmentError(validation.error);
      }
      
      // 2. 生成缩略图（图片类型）
      let thumbnail: Blob | undefined;
      if (this.isImage(file) && options?.enableThumbnail !== false) {
        thumbnail = await this.generateThumbnail(file, options);
      }
      
      // 3. 读取文件数据
      const fileData = await this.readFileAsBlob(file);
      
      // 4. 创建附件记录
      const attachment: Attachment = {
        id: generateId(),
        recordId: context.recordId,
        fieldId: context.fieldId,
        tableId: context.tableId,
        baseId: context.baseId,
        name: file.name,
        originalName: file.name,
        size: file.size,
        type: file.type,
        fileType: this.getFileType(file),
        extension: this.getFileExtension(file),
        data: fileData,
        thumbnail,
        createdAt: Date.now()
      };
      
      // 5. 存储到 IndexedDB
      await db.attachments.add(attachment);
      
      // 6. 构建返回的元数据
      const attachmentFile: AttachmentFile = {
        id: attachment.id,
        name: attachment.name,
        originalName: attachment.originalName,
        size: attachment.size,
        type: attachment.type,
        fileType: attachment.fileType,
        extension: attachment.extension,
        thumbnail: thumbnail ? URL.createObjectURL(thumbnail) : undefined,
        createdAt: attachment.createdAt
      };
      
      results.push(attachmentFile);
      
      // 7. 更新进度
      onProgress?.((results.length / files.length) * 100);
    }
    
    return results;
  }
  
  /**
   * 生成图片缩略图
   */
  private async generateThumbnail(
    file: File,
    options?: AttachmentFieldOptions
  ): Promise<Blob> {
    const maxWidth = options?.thumbnailMaxWidth ?? 200;
    const maxHeight = options?.thumbnailMaxHeight ?? 200;
    const quality = options?.thumbnailQuality ?? 0.8;
    
    return new Promise((resolve, reject) => {
      const img = new Image();
      img.onload = () => {
        const canvas = document.createElement('canvas');
        let { width, height } = img;
        
        // 计算缩放比例
        if (width > maxWidth || height > maxHeight) {
          const ratio = Math.min(maxWidth / width, maxHeight / height);
          width *= ratio;
          height *= ratio;
        }
        
        canvas.width = width;
        canvas.height = height;
        
        const ctx = canvas.getContext('2d');
        ctx?.drawImage(img, 0, 0, width, height);
        
        canvas.toBlob(
          (blob) => {
            if (blob) resolve(blob);
            else reject(new Error('缩略图生成失败'));
          },
          'image/jpeg',
          quality
        );
      };
      img.onerror = reject;
      img.src = URL.createObjectURL(file);
    });
  }
}
```

### 4.2 文件下载流程

```typescript
// services/attachmentService.ts

export class AttachmentService {
  /**
   * 下载附件
   */
  async downloadAttachment(attachmentId: string): Promise<void> {
    const attachment = await db.attachments.get(attachmentId);
    if (!attachment) {
      throw new AttachmentError('附件不存在');
    }
    
    // 创建 Blob URL
    const blob = attachment.data;
    const url = URL.createObjectURL(blob);
    
    // 创建下载链接
    const link = document.createElement('a');
    link.href = url;
    link.download = attachment.originalName || attachment.name;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    
    // 清理 URL 对象
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
  
  /**
   * 批量下载（打包为 zip）
   */
  async batchDownload(attachmentIds: string[]): Promise<void> {
    // 使用 JSZip 打包下载
    // ... 实现代码
  }
}
```

### 4.3 文件预览实现

```typescript
// components/AttachmentPreview/AttachmentPreview.vue

// 预览组件架构
interface PreviewComponent {
  // 支持的 MIME 类型
  supportedTypes: string[];
  // 预览组件
  component: Component;
}

// 预览组件注册表
const previewRegistry: Record<AttachmentFileType, PreviewComponent> = {
  image: {
    supportedTypes: ['image/jpeg', 'image/png', 'image/gif', 'image/webp'],
    component: ImagePreview
  },
  video: {
    supportedTypes: ['video/mp4', 'video/webm'],
    component: VideoPreview
  },
  audio: {
    supportedTypes: ['audio/mpeg', 'audio/wav', 'audio/ogg'],
    component: AudioPreview
  },
  document: {
    supportedTypes: ['application/pdf'],
    component: PdfPreview
  },
  // ... 其他类型
};

// ImagePreview.vue 示例
<template>
  <div class="image-preview">
    <img 
      :src="imageUrl" 
      :alt="attachment.name"
      @click="openFullscreen"
    />
    <div class="image-toolbar">
      <el-button @click="zoomIn">放大</el-button>
      <el-button @click="zoomOut">缩小</el-button>
      <el-button @click="rotate">旋转</el-button>
      <el-button @click="download">下载</el-button>
    </div>
  </div>
</template>
```

### 4.4 文件删除流程

```typescript
// services/attachmentService.ts

export class AttachmentService {
  /**
   * 删除附件
   */
  async deleteAttachment(attachmentId: string): Promise<void> {
    await db.transaction('rw', [db.attachments, db.records], async () => {
      const attachment = await db.attachments.get(attachmentId);
      if (!attachment) return;
      
      // 1. 从 attachments 表删除
      await db.attachments.delete(attachmentId);
      
      // 2. 更新记录中的附件列表
      const record = await db.records.get(attachment.recordId);
      if (record) {
        const fieldValue = record.values[attachment.fieldId];
        if (fieldValue && typeof fieldValue === 'object') {
          const files = (fieldValue as any).files || [];
          const updatedFiles = files.filter((f: AttachmentFile) => f.id !== attachmentId);
          
          const newValues = {
            ...record.values,
            [attachment.fieldId]: {
              type: 'attachment',
              files: updatedFiles
            }
          };
          
          await db.records.update(attachment.recordId, {
            values: newValues,
            updatedAt: Date.now()
          });
        }
      }
    });
  }
  
  /**
   * 批量删除附件
   */
  async batchDeleteAttachments(attachmentIds: string[]): Promise<void> {
    await db.transaction('rw', [db.attachments, db.records], async () => {
      for (const id of attachmentIds) {
        await this.deleteAttachment(id);
      }
    });
  }
}
```

## 五、异常处理机制

### 5.1 错误类型定义

```typescript
// utils/attachment/errors.ts

export enum AttachmentErrorCode {
  // 文件校验错误
  FILE_TOO_LARGE = 'FILE_TOO_LARGE',
  FILE_TYPE_NOT_ALLOWED = 'FILE_TYPE_NOT_ALLOWED',
  FILE_COUNT_EXCEEDED = 'FILE_COUNT_EXCEEDED',
  TOTAL_SIZE_EXCEEDED = 'TOTAL_SIZE_EXCEEDED',
  
  // 存储错误
  STORAGE_FULL = 'STORAGE_FULL',
  STORAGE_ERROR = 'STORAGE_ERROR',
  
  // 文件处理错误
  READ_ERROR = 'READ_ERROR',
  THUMBNAIL_ERROR = 'THUMBNAIL_ERROR',
  
  // 业务错误
  ATTACHMENT_NOT_FOUND = 'ATTACHMENT_NOT_FOUND',
  PERMISSION_DENIED = 'PERMISSION_DENIED',
  
  // 网络错误（云存储）
  NETWORK_ERROR = 'NETWORK_ERROR',
  UPLOAD_TIMEOUT = 'UPLOAD_TIMEOUT'
}

export class AttachmentError extends Error {
  constructor(
    message: string,
    public code: AttachmentErrorCode,
    public details?: Record<string, unknown>
  ) {
    super(message);
    this.name = 'AttachmentError';
  }
}
```

### 5.2 错误处理策略

| 错误场景 | 处理方式 | 用户提示 |
|----------|----------|----------|
| 文件大小超限 | 阻止上传，提示用户 | "文件 {name} 超过大小限制 {limit}" |
| 文件类型不支持 | 阻止上传，提示用户 | "不支持的文件类型: {type}" |
| 文件数量超限 | 阻止上传，提示用户 | "最多支持 {count} 个文件" |
| 存储空间不足 | 清理旧文件或提示用户 | "存储空间不足，请清理后重试" |
| 读取文件失败 | 重试或跳过 | "文件读取失败，请重试" |
| 缩略图生成失败 | 使用默认图标 | 静默处理 |
| 附件不存在 | 404 处理 | "附件已被删除或不存在" |

### 5.3 全局错误拦截

```typescript
// composables/useAttachment.ts

export function useAttachment() {
  const handleAttachmentError = (error: unknown) => {
    if (error instanceof AttachmentError) {
      switch (error.code) {
        case AttachmentErrorCode.FILE_TOO_LARGE:
          ElMessage.error(`文件过大: ${error.message}`);
          break;
        case AttachmentErrorCode.FILE_TYPE_NOT_ALLOWED:
          ElMessage.error(`不支持的文件类型: ${error.message}`);
          break;
        case AttachmentErrorCode.STORAGE_FULL:
          ElMessage.warning('存储空间不足，请清理不必要的附件');
          break;
        default:
          ElMessage.error(error.message);
      }
    } else {
      ElMessage.error('操作失败，请重试');
      console.error('Attachment error:', error);
    }
  };
  
  return { handleAttachmentError };
}
```

## 六、系统集成方案

### 6.1 与现有字段系统集成

```typescript
// components/fields/FieldComponentFactory.vue

// 1. 在字段组件工厂中注册附件字段
const fieldComponentMap: Record<string, Component> = {
  [FieldType.TEXT]: TextField,
  [FieldType.NUMBER]: NumberField,
  // ... 其他字段
  [FieldType.ATTACHMENT]: AttachmentField,  // 已存在，需增强
};

// 2. 在 FieldConfigPanel 中添加附件字段配置
const showAttachmentOptions = computed(
  () => localField.value.type === FieldType.ATTACHMENT
);
```

### 6.2 字段配置面板扩展

```vue
<!-- FieldConfigPanel.vue - 附件字段配置 -->
<template v-if="showAttachmentOptions">
  <div class="config-section">
    <div class="config-label">文件类型限制</div>
    <el-select
      v-model="attachmentConfig.acceptTypes"
      multiple
      placeholder="选择允许的文件类型">
      <el-option label="图片" value="image/*" />
      <el-option label="文档" value="application/pdf,application/msword" />
      <el-option label="视频" value="video/*" />
      <el-option label="音频" value="audio/*" />
    </el-select>
  </div>
  
  <div class="config-section">
    <div class="config-label">单个文件大小限制 (MB)</div>
    <el-input-number
      v-model="attachmentConfig.maxSizeMB"
      :min="1"
      :max="100"
      :step="1" />
  </div>
  
  <div class="config-section">
    <div class="config-label">最大文件数量</div>
    <el-input-number
      v-model="attachmentConfig.maxCount"
      :min="1"
      :max="50" />
  </div>
  
  <div class="config-section">
    <div class="config-label">生成缩略图</div>
    <el-switch v-model="attachmentConfig.enableThumbnail" />
  </div>
</template>
```

### 6.3 数据导入导出集成

```typescript
// utils/export/index.ts

export async function exportRecordWithAttachments(
  record: RecordEntity,
  fields: FieldEntity[],
  format: 'excel' | 'csv' | 'json'
): Promise<Blob> {
  // 处理附件字段导出
  for (const field of fields) {
    if (field.type === FieldType.ATTACHMENT) {
      const value = record.values[field.id];
      if (value && (value as any).files) {
        // 导出附件元数据（不包含二进制数据）
        // 或打包为 zip 下载
      }
    }
  }
  // ... 导出逻辑
}

// utils/importExport.ts

export async function importRecordsWithAttachments(
  data: unknown[],
  tableId: string,
  fieldMapping: Record<string, string>
): Promise<void> {
  // 处理附件字段导入
  // 支持从 zip 包中提取附件文件
}
```

### 6.4 表单视图集成

```vue
<!-- FormView/FormView.vue -->
<template>
  <div class="form-view">
    <div v-for="field in visibleFields" :key="field.id" class="form-field">
      <label>{{ field.name }}</label>
      
      <!-- 附件字段渲染 -->
      <AttachmentField
        v-if="field.type === FieldType.ATTACHMENT"
        v-model="formData[field.id]"
        :field="field"
        :readonly="isReadonly(field)"
        @upload="handleAttachmentUpload"
        @delete="handleAttachmentDelete"
      />
      
      <!-- 其他字段... -->
    </div>
  </div>
</template>
```

### 6.5 表格视图集成

```vue
<!-- TableView/TableCell.vue -->
<template>
  <div class="table-cell" :class="`cell-${field.type}`">
    <!-- 附件字段单元格 -->
    <div v-if="field.type === FieldType.ATTACHMENT" class="attachment-cell">
      <div v-if="attachments.length > 0" class="attachment-list">
        <el-tooltip
          v-for="att in displayAttachments"
          :key="att.id"
          :content="att.name">
          <div class="attachment-item" @click="previewAttachment(att)">
            <img v-if="att.thumbnail" :src="att.thumbnail" />
            <el-icon v-else><Document /></el-icon>
          </div>
        </el-tooltip>
        <el-tag v-if="remainingCount > 0" size="small">
          +{{ remainingCount }}
        </el-tag>
      </div>
      <span v-else class="empty-cell">-</span>
    </div>
  </div>
</template>
```

## 七、分阶段实现计划

### 第一阶段：基础功能实现（Week 1）

**目标：** 实现核心的上传、下载、删除功能

| 任务 | 优先级 | 预估工时 | 依赖 |
|------|--------|----------|------|
| 1. 完善 Attachment 类型定义 | P0 | 4h | 无 |
| 2. 实现 AttachmentService 核心方法 | P0 | 8h | 1 |
| 3. 重构 AttachmentField.vue 组件 | P0 | 8h | 2 |
| 4. 实现文件上传功能（含校验） | P0 | 6h | 3 |
| 5. 实现文件下载功能 | P0 | 4h | 3 |
| 6. 实现文件删除功能 | P0 | 4h | 3 |
| 7. 单元测试覆盖 | P0 | 6h | 4-6 |

**里程碑：** 附件字段基础 CRUD 功能可用

### 第二阶段：预览功能实现（Week 2）

**目标：** 实现多格式文件预览

| 任务 | 优先级 | 预估工时 | 依赖 |
|------|--------|----------|------|
| 1. 实现图片预览组件 | P0 | 6h | 第一阶段 |
| 2. 实现视频预览组件 | P0 | 4h | 第一阶段 |
| 3. 实现音频预览组件 | P1 | 4h | 第一阶段 |
| 4. 实现 PDF 预览组件 | P1 | 6h | 第一阶段 |
| 5. 实现通用文件预览（不支持格式） | P1 | 4h | 第一阶段 |
| 6. 预览对话框/抽屉组件 | P0 | 4h | 1-5 |
| 7. 单元测试覆盖 | P1 | 6h | 1-6 |

**里程碑：** 支持图片、视频、文档预览

### 第三阶段：配置与优化（Week 3）

**目标：** 完善字段配置和性能优化

| 任务 | 优先级 | 预估工时 | 依赖 |
|------|--------|----------|------|
| 1. 扩展 FieldConfigPanel 附件配置 | P0 | 6h | 第一阶段 |
| 2. 实现缩略图生成与缓存 | P1 | 6h | 第一阶段 |
| 3. 实现图片压缩优化 | P1 | 4h | 2 |
| 4. 实现懒加载优化 | P1 | 4h | 2 |
| 5. 添加存储空间管理 | P2 | 6h | 无 |
| 6. 异常处理完善 | P0 | 4h | 全部 |
| 7. 性能测试与优化 | P1 | 6h | 全部 |

**里程碑：** 附件字段配置完善，性能达标

### 第四阶段：系统集成（Week 4）

**目标：** 与现有系统功能深度集成

| 任务 | 优先级 | 预估工时 | 依赖 |
|------|--------|----------|------|
| 1. 数据导入导出集成 | P1 | 6h | 第一阶段 |
| 2. 表单视图集成优化 | P1 | 4h | 第一阶段 |
| 3. 表格视图集成优化 | P1 | 4h | 第一阶段 |
| 4. 分享功能集成 | P2 | 6h | 全部 |
| 5. 历史记录集成 | P2 | 4h | 全部 |
| 6. 端到端测试 | P0 | 8h | 全部 |
| 7. 文档编写 | P1 | 4h | 全部 |

**里程碑：** 附件字段功能完整，系统级集成完成

### 依赖关系图

```
第一阶段（基础功能）
    │
    ├──> 第二阶段（预览功能）
    │       │
    │       └──> 第四阶段（系统集成）
    │
    └──> 第三阶段（配置优化）
            │
            └──> 第四阶段（系统集成）
```

## 八、文件变更清单

### 8.1 新增文件

```
src/
├── types/
│   └── attachment.ts              # 附件类型定义
├── utils/
│   └── attachment/
│       ├── index.ts               # 工具函数入口
│       ├── const.ts               # 常量定义
│       ├── errors.ts              # 错误类型
│       ├── validators.ts          # 文件校验
│       ├── thumbnail.ts           # 缩略图生成
│       └── fileType.ts            # 文件类型检测
├── services/
│   └── attachmentService.ts       # 附件服务
├── components/
│   └── attachment/
│       ├── AttachmentPreview/
│       │   ├── index.vue          # 预览容器
│       │   ├── ImagePreview.vue   # 图片预览
│       │   ├── VideoPreview.vue   # 视频预览
│       │   ├── AudioPreview.vue   # 音频预览
│       │   ├── PdfPreview.vue     # PDF预览
│       │   └── FilePreview.vue    # 通用文件预览
│       └── AttachmentUpload/
│           ├── index.vue          # 上传组件
│           └── UploadProgress.vue # 上传进度
└── composables/
    └── useAttachment.ts           # 附件组合式函数
```

### 8.2 修改文件

```
src/
├── types/
│   └── fields.ts                  # 添加附件字段选项类型
├── db/
│   └── schema.ts                  # 确认 Attachment 接口
├── components/
│   ├── fields/
│   │   └── AttachmentField.vue    # 重构附件字段组件
│   └── dialogs/
│       └── FieldConfigPanel.vue   # 添加附件字段配置
├── utils/
│   ├── export/
│   │   └── index.ts               # 支持附件导出
│   └── validation.ts              # 添加附件字段校验
└── services/
    └── fieldService.ts            # 添加附件字段特殊处理
```

## 九、风险评估与应对

| 风险 | 可能性 | 影响 | 应对措施 |
|------|--------|------|----------|
| IndexedDB 容量限制 | 中 | 高 | 实现存储空间监控，提供清理功能 |
| 大文件上传性能问题 | 高 | 中 | 分片上传、进度显示、取消功能 |
| 浏览器兼容性问题 | 低 | 中 | 特性检测，降级方案 |
| 图片处理性能问题 | 中 | 中 | Web Worker 处理、异步生成缩略图 |
| 数据迁移问题 | 低 | 高 | 版本升级脚本，向后兼容 |

## 十、验收标准

### 10.1 功能验收

- [ ] 支持拖拽上传和点击上传
- [ ] 支持文件类型、大小、数量限制
- [ ] 支持图片、视频、音频、PDF 预览
- [ ] 支持单个和批量下载
- [ ] 支持单个和批量删除
- [ ] 支持缩略图生成和显示
- [ ] 字段配置面板可配置限制条件

### 10.2 性能验收

- [ ] 10MB 文件上传时间 < 5s
- [ ] 缩略图生成时间 < 2s
- [ ] 表格视图加载 100 条含附件记录 < 3s
- [ ] 内存占用增长 < 20%

### 10.3 质量验收

- [ ] 单元测试覆盖率 > 80%
- [ ] 无阻塞性 Bug
- [ ] 代码审查通过
- [ ] 文档完整

---

*文档版本：v1.0*  
*创建时间：2026-04-01*  
*最后更新：2026-04-01*
