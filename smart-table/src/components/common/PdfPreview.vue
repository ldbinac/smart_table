<script setup lang="ts">
import {
  ref,
  computed,
  watch,
  onMounted,
  onUnmounted,
  nextTick,
  shallowRef,
} from 'vue';
import { useI18n } from 'vue-i18n';
import {
  ArrowLeft,
  ArrowRight,
  ArrowUp,
  ArrowDown,
  ZoomIn,
  ZoomOut,
  RefreshRight,
  Download,
  Document,
  Menu,
  Search,
  Close,
} from '@element-plus/icons-vue';
import { GlobalWorkerOptions, getDocument } from 'pdfjs-dist';
import VuePdfEmbed from 'vue-pdf-embed';

// 配置 pdf.js worker（pdfjs-dist v6 使用 .mjs 模块 worker）
GlobalWorkerOptions.workerSrc = new URL(
  'pdfjs-dist/build/pdf.worker.min.mjs',
  import.meta.url
).toString();

const props = withDefaults(
  defineProps<{
    url: string;
    fileName?: string;
  }>(),
  { fileName: '' }
);

const { t } = useI18n();

const scrollRef = ref<HTMLDivElement | null>(null);
const pdfDoc = shallowRef<any>(null);
const numPages = ref(0);
const page = ref(1);
const zoomMode = ref<'auto' | 'manual'>('manual');
const manualZoom = ref(1.5);
const DEFAULT_ZOOM = 1.5;
const rotation = ref(0);
const containerWidth = ref(0);
const basePageWidth = ref(0);
const basePageHeight = ref(0);
const loading = ref(true);
const loadError = ref(false);

// 大纲/查找
const showSidebar = ref(false);
const outlineLoading = ref(false);
const outline = ref<any[]>([]);
const searchVisible = ref(false);
const findText = ref('');
const findResults = ref<{ page: number; text: string }[]>([]);
const currentMatch = ref(0);
const pageTextCache = new Map<number, string>();

// 按 PDF 自身尺寸（A4 等）为基础；默认“自适应宽度”铺满容器，100% 时按原始页面尺寸渲染
const fitScale = computed(() => {
  if (!basePageWidth.value || !containerWidth.value) return 1;
  return (containerWidth.value - 24) / basePageWidth.value;
});
const effectiveZoom = computed(() =>
  zoomMode.value === 'auto' ? fitScale.value : manualZoom.value
);
const scalePercent = computed(() => Math.round(effectiveZoom.value * 100));
const canPrev = computed(() => page.value > 1);
const canNext = computed(() => numPages.value > 0 && page.value < numPages.value);
const pageWidth = computed(() => {
  const base = basePageWidth.value || containerWidth.value || 800;
  return Math.max(100, Math.floor(base * effectiveZoom.value));
});

const outlineTree = computed(() => buildOutlineTree(outline.value));
const totalMatches = computed(() => findResults.value.length);
const matchLabel = computed(() =>
  totalMatches.value ? `${currentMatch.value + 1} / ${totalMatches.value}` : '0 / 0'
);

// 每页 DOM 引用，用于翻页/查找时平滑滚动定位
const pageEls: Record<number, HTMLElement> = {};
function setPageRef(el: any, p: number) {
  if (el) pageEls[p] = el as HTMLElement;
}

let resizeObserver: ResizeObserver | null = null;

function measureWidth() {
  if (scrollRef.value) containerWidth.value = scrollRef.value.clientWidth;
}

function buildOutlineTree(items: any[]): any[] {
  if (!items || !items.length) return [];
  return items.map((item) => ({
    label: item.title || '',
    dest: item.dest,
    children: buildOutlineTree(item.items),
  }));
}

async function resolveDestToPage(dest: any): Promise<number | undefined> {
  if (!pdfDoc.value || !dest) return undefined;
  try {
    let explicit = dest;
    if (typeof dest === 'string') explicit = await pdfDoc.value.getDestination(dest);
    if (Array.isArray(explicit) && explicit[0]) {
      const index = await pdfDoc.value.getPageIndex(explicit[0]);
      return (index as number) + 1;
    }
  } catch (e) {
    console.error('[PdfPreview] 大纲定位失败:', e);
  }
  return undefined;
}

async function updateBaseDimensions() {
  if (!pdfDoc.value) return;
  try {
    const pageProxy = await pdfDoc.value.getPage(1);
    const viewport = pageProxy.getViewport({ scale: 1, rotation: rotation.value });
    basePageWidth.value = viewport.width;
    basePageHeight.value = viewport.height;
  } catch (e) {
    console.error('[PdfPreview] 获取 PDF 尺寸失败:', e);
  }
}

async function loadPdf() {
  loading.value = true;
  loadError.value = false;
  outlineLoading.value = true;
  numPages.value = 0;
  page.value = 1;
  zoomMode.value = 'manual';
  manualZoom.value = DEFAULT_ZOOM;
  rotation.value = 0;
  outline.value = [];
  pageTextCache.clear();
  findResults.value = [];
  findText.value = '';
  currentMatch.value = 0;
  Object.keys(pageEls).forEach((k) => delete pageEls[Number(k)]);

  if (pdfDoc.value) {
    try { pdfDoc.value.destroy(); } catch (e) { /* ignore */ }
    pdfDoc.value = null;
  }

  try {
    pdfDoc.value = await getDocument({ url: props.url, withCredentials: true }).promise;
    numPages.value = pdfDoc.value.numPages;
    await updateBaseDimensions();
    outline.value = (await pdfDoc.value.getOutline()) || [];
  } catch (e) {
    console.error('[PdfPreview] PDF 加载失败:', e);
    loadError.value = true;
  } finally {
    loading.value = false;
    outlineLoading.value = false;
  }
}

function onLoaded() {
  loadError.value = false;
}

function onFailed() {
  loadError.value = true;
}

function prevPage() {
  if (canPrev.value) page.value -= 1;
}

function nextPage() {
  if (canNext.value) page.value += 1;
}

function applyManualZoom() {
  if (zoomMode.value === 'auto') {
    manualZoom.value = fitScale.value || 1;
    zoomMode.value = 'manual';
  }
}

function zoomIn() {
  applyManualZoom();
  manualZoom.value = Math.min(5, manualZoom.value * 1.2);
}

function zoomOut() {
  applyManualZoom();
  manualZoom.value = Math.max(0.25, manualZoom.value / 1.2);
}

function resetZoom() {
  zoomMode.value = 'manual';
  manualZoom.value = DEFAULT_ZOOM;
}

function rotate() {
  rotation.value = (rotation.value + 90) % 360;
  void updateBaseDimensions();
}

function scrollToPage() {
  const el = pageEls[page.value];
  if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

async function getPageText(p: number): Promise<string> {
  if (pageTextCache.has(p)) return pageTextCache.get(p) || '';
  if (!pdfDoc.value) return '';
  try {
    const pageProxy = await pdfDoc.value.getPage(p);
    const textContent = await pageProxy.getTextContent();
    const text = textContent.items.map((item: any) => item.str || '').join(' ');
    pageTextCache.set(p, text);
    return text;
  } catch (e) {
    return '';
  }
}

async function executeSearch() {
  findResults.value = [];
  currentMatch.value = 0;
  const query = findText.value.trim();
  if (!query || !numPages.value) return;
  const lowerQuery = query.toLowerCase();
  for (let p = 1; p <= numPages.value; p++) {
    const text = await getPageText(p);
    if (text.toLowerCase().includes(lowerQuery)) {
      const idx = text.toLowerCase().indexOf(lowerQuery);
      const snippet = text.slice(Math.max(0, idx - 12), idx + query.length + 24);
      findResults.value.push({ page: p, text: snippet });
    }
  }
  if (findResults.value.length) {
    currentMatch.value = 0;
    page.value = findResults.value[0].page;
  }
}

function findNext() {
  if (!findResults.value.length) {
    void executeSearch();
    return;
  }
  currentMatch.value = (currentMatch.value + 1) % findResults.value.length;
  page.value = findResults.value[currentMatch.value].page;
}

function findPrev() {
  if (!findResults.value.length) return;
  currentMatch.value = (currentMatch.value - 1 + findResults.value.length) % findResults.value.length;
  page.value = findResults.value[currentMatch.value].page;
}

function closeSearch() {
  searchVisible.value = false;
}

function toggleSidebar() {
  showSidebar.value = !showSidebar.value;
}

function toggleSearch() {
  searchVisible.value = !searchVisible.value;
  if (searchVisible.value) nextTick(() => (document.querySelector('.pdf-findbar input') as HTMLInputElement | null)?.focus());
}

async function onOutlineClick(node: any) {
  const targetPage = await resolveDestToPage(node.dest);
  if (targetPage) page.value = targetPage;
}

function triggerDownload() {
  const a = document.createElement('a');
  a.href = props.url;
  a.download = props.fileName || 'document.pdf';
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

function download() {
  triggerDownload();
}

watch(page, () => void nextTick(scrollToPage));

watch(
  () => props.url,
  () => void loadPdf()
);

onMounted(() => {
  measureWidth();
  void loadPdf();
  if (scrollRef.value && typeof ResizeObserver !== 'undefined') {
    resizeObserver = new ResizeObserver(() => measureWidth());
    resizeObserver.observe(scrollRef.value);
  }
});

onUnmounted(() => {
  resizeObserver?.disconnect();
  if (pdfDoc.value) {
    try { pdfDoc.value.destroy(); } catch (e) { /* ignore */ }
  }
});
</script>

<template>
  <div class="pdf-preview">
    <div v-if="loadError" class="pdf-error">
      <el-icon size="48"><Document /></el-icon>
      <p>{{ t('view.attachment.pdfPreviewFailed') }}</p>
      <el-button type="primary" @click="triggerDownload">{{ t('view.attachment.download') }}</el-button>
    </div>

    <template v-else>
      <div class="pdf-toolbar">
        <div class="pdf-toolbar__left">
          <el-button-group>
            <el-button
              size="small"
              :type="showSidebar ? 'primary' : ''"
              :title="t('view.attachment.pdfOutline')"
              @click="toggleSidebar"
            >
              <el-icon><Menu /></el-icon>
            </el-button>
            <el-button
              size="small"
              :type="searchVisible ? 'primary' : ''"
              :title="t('view.attachment.pdfFind')"
              @click="toggleSearch"
            >
              <el-icon><Search /></el-icon>
            </el-button>
          </el-button-group>
          <el-divider direction="vertical" />
          <el-button-group>
            <el-button
              :disabled="!canPrev"
              size="small"
              :title="t('view.attachment.pdfPrevPage')"
              @click="prevPage"
            >
              <el-icon><ArrowLeft /></el-icon>
            </el-button>
            <el-button size="small" disabled>{{ page }} / {{ numPages }}</el-button>
            <el-button
              :disabled="!canNext"
              size="small"
              :title="t('view.attachment.pdfNextPage')"
              @click="nextPage"
            >
              <el-icon><ArrowRight /></el-icon>
            </el-button>
          </el-button-group>
          <el-input-number
            v-if="numPages > 0"
            v-model="page"
            :min="1"
            :max="numPages"
            size="small"
            controls-position="right"
            class="pdf-page-input"
          />
        </div>

        <div class="pdf-toolbar__right">
          <el-button-group>
            <el-button size="small" @click="zoomOut"><el-icon><ZoomOut /></el-icon></el-button>
            <el-button size="small" disabled>{{ scalePercent }}%</el-button>
            <el-button size="small" @click="zoomIn"><el-icon><ZoomIn /></el-icon></el-button>
            <el-button size="small" @click="resetZoom">{{ t('view.attachment.resetZoom') }}</el-button>
          </el-button-group>
          <el-button size="small" @click="rotate">
            <el-icon><RefreshRight /></el-icon> {{ t('view.attachment.pdfRotate') }}
          </el-button>
          <el-button size="small" type="primary" @click="download">
            <el-icon><Download /></el-icon> {{ t('view.attachment.download') }}
          </el-button>
        </div>
      </div>

      <div v-if="searchVisible" class="pdf-findbar">
        <el-input
          v-model="findText"
          size="small"
          clearable
          :placeholder="t('view.attachment.findPlaceholder')"
          @keyup.enter="findNext"
        >
          <template #append>{{ matchLabel }}</template>
        </el-input>
        <el-button-group>
          <el-button
            size="small"
            :disabled="!totalMatches"
            :title="t('view.attachment.searchPrev')"
            @click="findPrev"
          >
            <el-icon><ArrowUp /></el-icon>
          </el-button>
          <el-button
            size="small"
            :disabled="!totalMatches"
            :title="t('view.attachment.searchNext')"
            @click="findNext"
          >
            <el-icon><ArrowDown /></el-icon>
          </el-button>
        </el-button-group>
        <el-button size="small" text @click="closeSearch">
          <el-icon><Close /></el-icon>
        </el-button>
      </div>

      <div class="pdf-body">
        <div v-if="showSidebar" class="pdf-sidebar" v-loading="outlineLoading">
          <div class="pdf-sidebar__header">{{ t('view.attachment.pdfOutline') }}</div>
          <el-tree
            v-if="outlineTree.length"
            :data="outlineTree"
            :props="{ label: 'label', children: 'children' }"
            default-expand-all
            @node-click="onOutlineClick"
          />
          <el-empty v-else :description="t('view.attachment.noOutline')" />
        </div>

        <div ref="scrollRef" class="pdf-canvas" v-loading="loading">
          <div class="pdf-pages">
            <div
              v-for="p in (numPages || 1)"
              :key="p"
              :ref="el => setPageRef(el, p)"
              class="pdf-page"
            >
              <VuePdfEmbed
                :source="url"
                :page="p"
                :width="pageWidth"
                :rotation="rotation"
                @loaded="onLoaded"
                @loading-failed="onFailed"
                @rendering-failed="onFailed"
              />
            </div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style lang="scss" scoped>
.pdf-preview {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

.pdf-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-wrap: wrap;
  gap: 12px;
  padding: 8px 16px;
  background: #ffffff;
  box-shadow: 0 1px 4px rgba(0, 0, 0, 0.35);
  flex-shrink: 0;
  z-index: 1;
}

.pdf-toolbar__left,
.pdf-toolbar__right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.pdf-page-input {
  width: 110px;
}

.pdf-findbar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 16px;
  background: #f5f5f5;
  border-bottom: 1px solid #d8d8d8;
  flex-shrink: 0;

  .el-input {
    width: 260px;
  }
}

.pdf-body {
  display: flex;
  flex: 1;
  min-height: 0;
}

.pdf-sidebar {
  width: 260px;
  flex-shrink: 0;
  background: #f5f5f5;
  border-right: 1px solid #d8d8d8;
  overflow: auto;
  padding: 12px;

  &__header {
    font-weight: 600;
    margin-bottom: 8px;
    color: #303133;
  }
}

.pdf-canvas {
  flex: 1;
  min-width: 0;
  min-height: 0;
  overflow: auto;
  background: #525659;
}

.pdf-pages {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 12px;
}

.pdf-page {
  background: #ffffff;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.4);
  line-height: 0;
  flex-shrink: 0;
}

.pdf-error {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 16px;
  color: #909399;
  background: #525659;
}
</style>
