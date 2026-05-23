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

    <!-- 编辑器主体 -->
    <div class="document-editor__main">
      <!-- 左侧：文档标题列表导航 -->
      <div class="document-editor__header-list">
        <p style="font-size: 16px; font-weight: bolder; padding-bottom: 10px; color: blue;">大纲目录</p>
        <div ref="headerListRef" class="document-editor__header-list-wrapper"></div>
      </div>
      
      <!-- 中间：TinyEditor 编辑器 -->
      <div ref="containerRef" class="document-editor__container">
        <div ref="editorRef" class="document-editor__content"></div>
      </div>
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
import HeaderList from 'quill-header-list';
import QuillToolbarTip, { createI18nToolbarTipMap } from 'quill-toolbar-tip';
import 'quill-toolbar-tip/dist/index.css';
import 'quill-table-up/index.css';
import 'quill-table-up/table-creator.css';
import { documentApiService } from '@/services/api/documentApiService';
import { uploadFile } from '@/services/api/attachmentApiService';
import { ElMessage } from 'element-plus';
import DocumentVersionHistory from './DocumentVersionHistory.vue';
import type { Document } from '@/types/document';
import type { DocumentVersion } from '@/types/documentVersion';

// 注册 Markdown 模块
FluentEditor.register('modules/markdownShortcuts', MarkdownShortcuts);
// 注册 HeaderList 模块（注册 HeaderWithID 格式 + 工具栏按钮）
FluentEditor.register('modules/header-list', HeaderList, true);
// 注册工具栏提示模块
FluentEditor.register({ [`modules/${QuillToolbarTip.moduleName}`]: QuillToolbarTip }, true);

// 基于官方 zh-CN 语言包构建 toolbar 嵌套键，供 createI18nToolbarTipMap 使用
// 官方翻译使用扁平键（如 bold、list-ordered），toolbar-tip 需要 toolbar.bold、toolbar.list.ordered
const toolbarI18nMessages = {
  'zh-CN': {
    toolbar: {
      'format-painter': '格式刷',
      'header-list': '标题列表',
      header: { '': '正文', '1': '标题1', '2': '标题2', '3': '标题3', '4': '标题4', '5': '标题5', '6': '标题6' },
      size: { '': '字体大小', '12px': '12px', '13px': '13px', '14px': '14px', '15px': '15px', '16px': '16px', '19px': '19px', '22px': '22px', '24px': '24px', '29px': '29px', '32px': '32px', '40px': '40px', '48px': '48px' },
      bold: '粗体',
      italic: '斜体',
      underline: '下划线',
      strike: '删除线',
      script: { sub: '下标', super: '上标' },
      code: '行内代码',
      color: '字体颜色',
      background: '背景色',
      align: { '': '左对齐', center: '居中对齐', right: '右对齐', justify: '两端对齐' },
      list: { ordered: '有序列表', bullet: '无序列表', check: '任务列表' },
      indent: { '-1': '减少缩进', '+1': '增加缩进' },
      'line-height': { '': '行距', '1': '1倍行距', '1.15': '1.15倍行距', '1.5': '1.5倍行距', '2': '2倍行距', '2.5': '2.5倍行距', '3': '3倍行距' },
      link: '超链接',
      blockquote: '引用',
      divider: '分割线',
      'code-block': '代码块',
      image: '图片',
      video: '视频',
      'table-up': { '': '表格' },
      clean: '清除格式',
      fullscreen: '全屏',
    }
  }
};

// 使用 createI18nToolbarTipMap 生成基于 i18n 的提示映射
// 传入自定义 formats 以覆盖 divider、table-up、line-height 等不在默认列表中的按钮
const toolbarTipTextMap = createI18nToolbarTipMap({
  formats: {
    simple: ['format-painter', 'bold', 'italic', 'underline', 'strike', 'color', 'background', 'blockquote', 'code-block', 'code', 'link', 'image', 'video', 'formula', 'clean', 'divider', 'fullscreen'],
    withValues: {
      list: ['ordered', 'bullet', 'check'],
      script: ['sub', 'super'],
      indent: ['-1', '+1'],
      header: ['', '1', '2', '3', '4', '5', '6'],
      align: ['', 'center', 'right', 'justify'],
      size: ['12px', '13px', '14px', '15px', '16px', '19px', '22px', '24px', '29px', '32px', '40px', '48px'],
      'line-height': ['1', '1.15', '1.5', '2', '2.5', '3'],
      'table-up': [''],
      
    }
  }
});

const props = defineProps<{
  document: Document;
  baseId: string;
}>();

const emit = defineEmits<{
  (e: 'save', doc: Document): void;
  (e: 'export-pdf'): void;
}>();

const editorRef = ref<HTMLDivElement>();
const headerListRef = ref<HTMLDivElement>();
const containerRef = ref<HTMLDivElement>();
const documentName = ref(props.document.name);
const versionHistoryVisible = ref(false);
let editor: FluentEditor | null = null;
let scrollContainer: HTMLElement | null = null;
let scrollHandler: (() => void) | null = null;
let headerClickHandler: ((e: MouseEvent) => void) | null = null;
let textChangeHandler: (() => void) | null = null;
let updateTimer: ReturnType<typeof setTimeout> | null = null;
let currentHighlightId = '';

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

// 计算标题相对于滚动容器顶部的偏移位置
const getHeaderOffsetTop = (headerEl: HTMLElement, container: HTMLElement): number => {
  const containerRect = container.getBoundingClientRect();
  const headerRect = headerEl.getBoundingClientRect();
  return headerRect.top - containerRect.top + container.scrollTop;
};

// 实时重建标题列表（全量替换，避免 quill-header-list update 方法的 bug）
const rebuildHeaderList = () => {
  if (!editor || !headerListRef.value) return;

  const quillRoot = editor.root;
  const headers = quillRoot.querySelectorAll<HTMLElement>(':scope > h1, :scope > h2, :scope > h3, :scope > h4, :scope > h5, :scope > h6');

  const wrapper = headerListRef.value;
  // 清空现有列表
  wrapper.innerHTML = '';

  if (headers.length === 0) {
    const emptyTip = document.createElement('div');
    emptyTip.className = 'header-list-empty';
    emptyTip.textContent = '暂无标题';
    wrapper.appendChild(emptyTip);
    return;
  }

  const listRoot = document.createElement('div');
  listRoot.classList.add('hl-header-list');

  headers.forEach(headerEl => {
    const tagName = headerEl.tagName.toLowerCase();
    const level = parseInt(tagName.replace('h', ''), 10);
    const id = headerEl.getAttribute('data-block-id') || '';
    const text = headerEl.textContent || '';

    const item = document.createElement('div');
    item.classList.add('hl-header-list__item', `level-${level}`);
    item.dataset.id = id;
    item.textContent = text;

    // 恢复之前的高亮状态
    if (id === currentHighlightId) {
      item.classList.add('is-highlight');
    }

    listRoot.appendChild(item);
  });

  wrapper.appendChild(listRoot);
};

// 节流的标题列表更新（避免频繁重建导致性能问题）
const scheduleHeaderListUpdate = () => {
  if (updateTimer) clearTimeout(updateTimer);
  updateTimer = setTimeout(() => {
    rebuildHeaderList();
  }, 300);
};

// 滚动高亮：检测当前视口内最顶部的标题并高亮
const handleScrollHighlight = () => {
  if (!editor || !headerListRef.value || !scrollContainer) return;

  const scrollTop = scrollContainer.scrollTop;
  const headerItems = headerListRef.value.querySelectorAll<HTMLElement>('.hl-header-list__item');
  if (headerItems.length === 0) return;

  const quillRoot = editor.root;
  const headers = quillRoot.querySelectorAll<HTMLElement>(':scope > h1, :scope > h2, :scope > h3, :scope > h4, :scope > h5, :scope > h6');

  // 找到当前视口顶部对应的标题
  let activeId = '';
  for (let i = headers.length - 1; i >= 0; i--) {
    const headerEl = headers[i];
    const offsetTop = getHeaderOffsetTop(headerEl, scrollContainer);
    if (offsetTop <= scrollTop + 40) {
      activeId = headerEl.getAttribute('data-block-id') || '';
      break;
    }
  }

  // 记住当前高亮 ID，供 rebuildHeaderList 恢复
  currentHighlightId = activeId;

  // 更新高亮状态
  headerItems.forEach(item => {
    if (item.dataset.id === activeId) {
      item.classList.add('is-highlight');
    } else {
      item.classList.remove('is-highlight');
    }
  });
};

// 点击标题导航：平滑滚动到对应标题位置
const handleHeaderClick = (e: MouseEvent) => {
  const target = e.target as HTMLElement;
  if (!target || !target.classList.contains('hl-header-list__item')) return;

  const id = target.dataset.id;
  if (!id || !editor || !scrollContainer) return;

  const quillRoot = editor.root;
  const headerEl = quillRoot.querySelector(`:scope > h1[data-block-id="${id}"], :scope > h2[data-block-id="${id}"], :scope > h3[data-block-id="${id}"], :scope > h4[data-block-id="${id}"], :scope > h5[data-block-id="${id}"], :scope > h6[data-block-id="${id}"]`) as HTMLElement;
  if (!headerEl) return;

  const offsetTop = getHeaderOffsetTop(headerEl, scrollContainer);

  scrollContainer.scrollTo({
    top: offsetTop - 20,
    behavior: 'smooth'
  });
};

onMounted(async () => {
  if (!editorRef.value || !headerListRef.value || !containerRef.value) return;

  console.log('[DocumentEditor] 初始化编辑器');

  // 动态导入表格模块（SSR 兼容）
  const { defaultCustomSelect, TableUp, TableSelection, TableMenuContextmenu, TableResizeLine } = await import('quill-table-up');
  const { generateTableUp } = await import('@opentiny/fluent-editor');
  // 注册表格模块
  FluentEditor.register({ 'modules/table-up': generateTableUp(TableUp) }, true);

  editor = new FluentEditor(editorRef.value, {
    theme: 'snow',
    placeholder: '开始编写文档... 支持 Markdown 语法（如 # 标题，**粗体**，`代码` 等）',
    modules: {
      toolbar: [
        // ['header-list'],
        ['format-painter'],
        [{ 'header': [1, 2, 3, 4, 5, false] },
         { size: ['12px', '13px', '14px', '15px', '16px', '19px', '22px', '24px', '29px', '32px', '40px', '48px'] },
         'bold', 'italic', 'underline', 'strike',
          { script: 'super' },
          { script: 'sub' },
          'code',
         { 'color': [] }, { 'background': [] }],
        [{ 'align': [] },
         { 'list': 'ordered' }, { 'list': 'bullet' },
         { 'indent': '-1' }, { 'indent': '+1' },
         { 'line-height': ['1', '1.15', '1.5', '2', '2.5', '3'] },
        ],
        [{ list: 'check' }, 
         'link', 
         'blockquote', 
         'divider',
         'code-block'],
        ['link', 'image', 'video'],
        [{ 'table-up': [] }],
        ['clean'],
        ['fullscreen'],
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
      markdownShortcuts: {},
      // header-list 模块仅用于注册 HeaderWithID 格式和工具栏按钮
      // 标题列表的构建和更新由自定义逻辑处理
      'header-list': {
        container: headerListRef.value,
        scrollContainer: containerRef.value
      },
      // 表格模块：右键菜单 + 单元格选择 + 大小调整
      'table-up': {
        customSelect: defaultCustomSelect,
        modules: [
          { module: TableSelection },
          { module: TableMenuContextmenu },
          { module: TableResizeLine },
        ],
      },
      // 国际化：设置为中文，并注入 toolbar 嵌套键供 toolbar-tip 模块使用
      i18n: {
        locale: 'zh-CN',
        messages: toolbarI18nMessages,
      },
      // 工具栏提示
      [QuillToolbarTip.moduleName]: {
        tipTextMap: toolbarTipTextMap,
      }
    }
  });

  // 实际滚动容器是 .ql-editor（Quill 编辑器自带 overflow-y: auto）
  scrollContainer = editor.root;

  // 自定义全屏逻辑：让整个 .document-editor 全屏，而非仅编辑器内容区
  const editorContainer = editorRef.value!.closest('.document-editor') as HTMLElement;
  const originalFullscreenHandler = () => {
    if (editor!.isFullscreen) {
      editorContainer.classList.remove('document-editor--fullscreen');
    } else {
      editorContainer.classList.add('document-editor--fullscreen');
    }
  };
  editor.on('fullscreen-change', originalFullscreenHandler);

  // 触发 i18n 初始化：设置 locale 会触发 I18N_LOCALE_CHANGE 事件，
  // Snow 主题监听此事件来更新工具栏文本为中文
  const i18nModule = editor.getModule('i18n') as { setLocale: (locale: string) => void };
  if (i18nModule) {
    i18nModule.setLocale('zh-CN');
  }

  // 编辑器初始化完成后立即加载内容
  loadContentToEditor(props.document);

  // 自动显示标题列表（模块默认隐藏）
  const headerListModule = editor.getModule('header-list') as { show: () => void };
  if (headerListModule) {
    headerListModule.show();
  }

  // 监听编辑器内容变化，实时更新标题列表
  textChangeHandler = () => scheduleHeaderListUpdate();
  editor.on('text-change', textChangeHandler);

  // 初始构建标题列表（延迟等待内容渲染完成）
  nextTick(() => {
    rebuildHeaderList();
  });

  // 自定义滚动高亮监听
  scrollHandler = () => handleScrollHighlight();
  scrollContainer.addEventListener('scroll', scrollHandler);

  // 自定义标题点击导航
  headerClickHandler = handleHeaderClick;
  headerListRef.value.addEventListener('click', headerClickHandler);
});

onBeforeUnmount(() => {
  // 清理定时器
  if (updateTimer) clearTimeout(updateTimer);
  // 清理编辑器事件监听
  if (textChangeHandler && editor) {
    editor.off('text-change', textChangeHandler);
  }
  // 清理滚动监听
  if (scrollHandler && scrollContainer) {
    scrollContainer.removeEventListener('scroll', scrollHandler);
  }
  // 清理点击监听
  if (headerClickHandler && headerListRef.value) {
    headerListRef.value.removeEventListener('click', headerClickHandler);
  }
  scrollContainer = null;
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
    flex-shrink: 0;
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

  &__main {
    display: flex;
    flex: 1;
    overflow: hidden;
    padding-bottom: 70px;
  }

  &__header-list {
    width: 260px;
    background: var(--el-bg-color-page);
    border-right: 1px solid var(--el-border-color-light);
    overflow-y: auto;
    padding: 20px 16px;
    flex-shrink: 0;
    height: 100%;
    box-sizing: border-box;
  }

  &__header-list-wrapper {
    width: 100%;
  }

  &__container {
    flex: 1;
    //overflow: auto;
    padding: 24px;
    min-width: 0;
  }

  &__content {
    max-width: 800px;
    margin: 0 auto;
    min-height: 600px;
    background: var(--el-bg-color);
  }
}
</style>

<style lang="scss">
/* 全屏模式样式 */
.document-editor--fullscreen {
  position: fixed !important;
  top: 0;
  left: 0;
  width: 100vw !important;
  height: 100vh !important;
  z-index: 9999;
  background: var(--el-bg-color);
}

/* quill-header-list 样式（包的 exports 字段导致 CSS 无法直接导入） */
.hl-header-list {
  display: flex;
  flex-direction: column;
  width: 100%;

  &__item {
    width: 100%;
    height: 26px;
    padding: 2px 10px 2px 0;
    margin-bottom: 6px;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    font-size: 14px;
    line-height: 22px;
    cursor: pointer;
    font-weight: 500;
    transition: background-color 0.25s linear, border-color 0.25s linear;

    &:hover {
      background-color: #f5f5f5;
      font-weight: 900;
    }

    &.level-1 { padding-left: 16px; }
    &.level-2 { padding-left: 32px; }
    &.level-3 { padding-left: 48px; }
    &.level-4 { padding-left: 64px; }
    &.level-5 { padding-left: 80px; }
    &.level-6 { padding-left: 96px; }

    &.is-highlight {
      border-left: 2px solid currentColor;
      font-weight: 900;
    }
  }
}

.header-list-empty {
  color: var(--el-text-color-placeholder);
  font-size: 13px;
  text-align: center;
  padding: 20px 0;
}

.is-hidden {
  display: none;
}
</style>
