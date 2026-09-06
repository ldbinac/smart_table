<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useI18n } from 'vue-i18n';
import { Close, Document, Loading } from '@element-plus/icons-vue';
import { ElMessage } from 'element-plus';
import PdfPreview from '@/components/common/PdfPreview.vue';
import { attachmentService } from '@/db/services';
import { AttachmentError } from '@/utils/attachment';

const route = useRoute();
const router = useRouter();
const { t } = useI18n();

const fileName = ref<string>((route.query.name as string) || 'document.pdf');
const pdfUrl = ref<string>('');
const loadError = ref(false);

async function loadPdf() {
  const id = route.query.id as string | undefined;
  if (!id) {
    loadError.value = true;
    return;
  }
  try {
    const blob = await attachmentService.getAttachmentBlob(id);
    pdfUrl.value = URL.createObjectURL(blob);
  } catch (e) {
    if (e instanceof AttachmentError) {
      ElMessage.error(e.message);
    } else {
      console.error('PDF 加载失败', e);
    }
    loadError.value = true;
  }
}

function closeTab() {
  if (window.opener) {
    window.close();
  } else {
    router.back();
  }
}

onMounted(loadPdf);

onUnmounted(() => {
  if (pdfUrl.value) {
    URL.revokeObjectURL(pdfUrl.value);
  }
});
</script>

<template>
  <div class="pdf-preview-page">
    <header class="pdf-preview-page__header">
      <div class="pdf-preview-page__title">
        <el-icon><Document /></el-icon>
        <span :title="fileName">{{ fileName }}</span>
      </div>
      <el-button text @click="closeTab">
        <el-icon><Close /></el-icon> {{ t('view.attachment.pdfCloseTab') }}
      </el-button>
    </header>

    <main class="pdf-preview-page__body">
      <PdfPreview v-if="pdfUrl" :url="pdfUrl" :file-name="fileName" />

      <div v-else-if="loadError" class="pdf-preview-page__center">
        <el-icon size="48"><Document /></el-icon>
        <p>{{ t('view.attachment.pdfPreviewFailed') }}</p>
        <el-button type="primary" @click="router.back()">{{ t('view.attachment.pdfCloseTab') }}</el-button>
      </div>

      <div v-else class="pdf-preview-page__center">
        <el-icon class="is-loading" size="32"><Loading /></el-icon>
      </div>
    </main>
  </div>
</template>

<style lang="scss" scoped>
.pdf-preview-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #1a1a1a;
  color: #ffffff;
}

.pdf-preview-page__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 10px 16px;
  background: rgba(255, 255, 255, 0.05);
  border-bottom: 1px solid rgba(255, 255, 255, 0.08);
  flex-shrink: 0;
}

.pdf-preview-page__title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 500;
  min-width: 0;

  span {
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.pdf-preview-page__body {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}

.pdf-preview-page__center {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  color: #909399;
}
</style>
