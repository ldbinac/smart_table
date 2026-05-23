<template>
  <div class="document-editor">
    <!-- 编辑器头部 -->
    <div class="document-editor__header">
      <el-input
        v-model="documentName"
        class="document-editor__title"
        placeholder="文档标题"
        @blur="handleSaveName"
      />
      <div class="document-editor__actions">
        <el-button @click="handleShowVersionHistory">
          <el-icon><Clock /></el-icon>
          版本历史
        </el-button>
        <el-button @click="handleExportPdf">
          <el-icon><Download /></el-icon>
          导出 PDF
        </el-button>
        <el-button type="primary" @click="handleSave">
          保存
        </el-button>
      </div>
    </div>

    <!-- TinyEditor 编辑器 -->
    <div class="document-editor__container">
      <div ref="editorRef" class="document-editor__content"></div>
    </div>

    <!-- 版本历史侧边栏 -->
    <el-drawer
      v-model="versionHistoryVisible"
      title="版本历史"
      size="400px"
      destroy-on-close
    >
      <DocumentVersionHistory
        :document-id="props.document.id"
        @close="versionHistoryVisible = false"
        @restore="handleVersionRestored"
      />
    </el-drawer>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch, nextTick } from 'vue';
import { Download, Clock } from '@element-plus/icons-vue';
import FluentEditor from '@opentiny/fluent-editor';
import '@opentiny/fluent-editor/style.css';
import MarkdownShortcuts from 'quill-markdown-shortcuts';
import { documentApiService } from '@/services/api/documentApiService';
import { uploadFile } from '@/services/api/attachmentApiService';
import { ElMessage } from 'element-plus';
import DocumentVersionHistory from './DocumentVersionHistory.vue';
import type { Document } from '@/types/document';
import type { DocumentVersion } from '@/types/documentVersion';

// 注册 Markdown 模块
FluentEditor.register('modules/markdownShortcuts', MarkdownShortcuts);

const props = defineProps<{
  document: Document;
  baseId: string;
}>();

const emit = defineEmits<{
  (e: 'save', doc: Document): void;
  (e: 'export-pdf'): void;
}>();

const editorRef = ref<HTMLDivElement>();
const documentName = ref(props.document.name);
const versionHistoryVisible = ref(false);
let editor: FluentEditor | null = null;

// 加载内容到编辑器的函数
const loadContentToEditor = (doc: Document) => {
  if (!editor) return;
  
  const contentFormat = doc.contentFormat || doc.content_format || 'delta';
  const content = doc.content;
  
  console.log('[DocumentEditor] 加载内容到编辑器', {
    docId: doc.id,
    content,
    contentFormat,
    rawDoc: doc
  });
  
  try {
    const parsedContent = contentFormat === 'delta' ? JSON.parse(content) : content;
    editor.setContents(parsedContent);
  } catch (e) {
    console.error('[DocumentEditor] 解析内容失败:', e);
  }
};

onMounted(() => {
  if (!editorRef.value) return;

  console.log('[DocumentEditor] 初始化编辑器');
  editor = new FluentEditor(editorRef.value, {
    theme: 'snow',
    placeholder: '开始编写文档... 支持 Markdown 语法（如 # 标题，**粗体**，`代码` 等）',
    modules: {
      toolbar: [
        [{ 'header': [1, 2, 3, 4, 5, 6, false] }],
        ['bold', 'italic', 'underline', 'strike'],
        [{ 'color': [] }, { 'background': [] }],
        [{ 'align': [] }],
        [{ 'list': 'ordered' }, { 'list': 'bullet' }],
        [{ 'indent': '-1' }, { 'indent': '+1' }],
        ['blockquote', 'code-block'],
        ['link', 'image', 'video'],
        ['clean']
      ],
      uploader: {
        mimetypes: {
          image: ['image/png', 'image/jpeg', 'image/gif', 'image/webp']
        },
        maxSize: 10 * 1024 * 1024, // 10MB
        multiple: false,
        handler: async (range, files) => {
          const urls: string[] = [];
          for (const file of files) {
            try {
              const result = await uploadFile(file, {
                table_id: props.baseId,
                record_id: 'document',
                field_id: 'content'
              });
              urls.push(result.attachment.url || '');
            } catch (error) {
              ElMessage.error('图片上传失败');
              console.error('Image upload error:', error);
            }
          }
          return urls;
        }
      },
      markdownShortcuts: {} // 启用 Markdown 快捷键支持
    }
  });

  // 编辑器初始化完成后立即加载内容
  loadContentToEditor(props.document);
});

onBeforeUnmount(() => {
  editor = null;
});

watch(() => props.document, (newDoc, oldDoc) => {
  console.log('[DocumentEditor] props.document 变化:', newDoc.id, '旧值:', oldDoc?.id);
  documentName.value = newDoc.name;
  
  // 只有在文档实际发生变化时才重新加载内容
  if (editor && newDoc.id !== oldDoc?.id) {
    // 等待 DOM 更新后再加载内容
    nextTick(() => {
      loadContentToEditor(newDoc);
    });
  }
}, { deep: true });

const handleSaveName = async () => {
  if (documentName.value !== props.document.name) {
    await documentApiService.update(props.document.id, { name: documentName.value });
  }
};

const handleSave = async () => {
  if (!editor) return;
  const content = JSON.stringify(editor.getContents());
  const updated = await documentApiService.update(props.document.id, {
    content,
    contentFormat: 'delta'
  });
  emit('save', updated);
  ElMessage.success('保存成功');
};

const handleExportPdf = () => {
  emit('export-pdf');
};

const handleShowVersionHistory = () => {
  versionHistoryVisible.value = true;
};

const handleVersionRestored = (version: DocumentVersion) => {
  if (editor && version.content) {
    const content = version.contentFormat === 'delta'
      ? JSON.parse(version.content)
      : version.content;
    editor.setContents(content);
  }
  documentName.value = version.name.replace(/^版本\s+/, '');
  ElMessage.success('已恢复到选中版本，请保存以生效');
};
</script>

<style scoped lang="scss">
.document-editor {
  display: flex;
  flex-direction: column;
  height: 100%;
  background: var(--el-bg-color);

  &__header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 16px 24px;
    border-bottom: 1px solid var(--el-border-color-light);
    background: var(--el-bg-color);
  }

  &__title {
    flex: 1;
    margin-right: 16px;

    :deep(.el-input__wrapper) {
      box-shadow: none;
      padding: 0;
    }

    :deep(.el-input__inner) {
      font-size: 24px;
      font-weight: 600;
      height: 40px;
    }
  }

  &__container {
    flex: 1;
    overflow: auto;
    padding: 24px;
  }

  &__content {
    max-width: 800px;
    margin: 0 auto;
    min-height: 600px;
    background: var(--el-bg-color);
  }
}
</style>
