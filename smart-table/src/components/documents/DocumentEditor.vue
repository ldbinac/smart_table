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
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch } from 'vue';
import { Download } from '@element-plus/icons-vue';
import FluentEditor from '@opentiny/fluent-editor';
import '@opentiny/fluent-editor/style.css';
import { documentApiService } from '@/services/api/documentApiService';
import { attachmentApiService } from '@/services/api/attachmentApiService';
import type { Document } from '@/types/document';

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
let editor: FluentEditor | null = null;

onMounted(() => {
  if (!editorRef.value) return;

  editor = new FluentEditor(editorRef.value, {
    theme: 'snow',
    placeholder: '开始编写文档...',
    modules: {
      toolbar: [
        [{ header: [1, 2, 3, 4, 5, 6, false] }],
        ['bold', 'italic', 'underline', 'strike'],
        [{ color: [] }, { background: [] }],
        [{ align: [] }],
        [{ list: 'ordered' }, { list: 'bullet' }],
        [{ indent: '-1' }, { indent: '+1' }],
        ['blockquote', 'code-block'],
        ['link', 'image', 'video'],
        ['clean']
      ],
      imageUploader: {
        upload: async (file: File) => {
          const result = await attachmentApiService.upload({
            file,
            baseId: props.baseId,
            recordId: 'document',
            fieldId: 'content'
          });
          return result.url;
        }
      }
    }
  });

  if (props.document.content) {
    const content = props.document.contentFormat === 'delta'
      ? JSON.parse(props.document.content)
      : props.document.content;
    editor.setContents(content);
  }
});

onBeforeUnmount(() => {
  editor?.destroy();
  editor = null;
});

watch(() => props.document, (newDoc) => {
  documentName.value = newDoc.name;
  if (editor && newDoc.content) {
    const content = newDoc.contentFormat === 'delta'
      ? JSON.parse(newDoc.content)
      : newDoc.content;
    editor.setContents(content);
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
