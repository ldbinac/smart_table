/**
 * PDF 前端导出工具
 */

// 修复图片 URL 问题
function fixImageUrls(html: string): string {
  // 处理 src 为 [object Object] 的图片
  const div = document.createElement('div');
  div.innerHTML = html;
  const images = div.querySelectorAll('img');
  images.forEach((img) => {
    const src = img.getAttribute('src');
    if (!src || src === '[object Object]' || src.startsWith('unsafe:')) {
      img.parentNode?.removeChild(img);
    } else if (src.startsWith('/')) {
      img.setAttribute('src', `${window.location.origin}${src}`);
    } else if (!src.startsWith('http') && !src.startsWith('data:')) {
      img.setAttribute('src', `${window.location.origin}/${src}`);
    }
  });
  return div.innerHTML;
}

/**
 * 从编辑器 DOM 获取内容 HTML，保留表格等自定义格式的完整结构
 */
function getEditorHtml(): string {
  const editor = document.querySelector('.ql-editor');
  if (!editor) {
    console.warn('[PDFExport] 未找到编辑器元素');
    return '';
  }

  // 克隆编辑器 DOM，移除不需要的元素
  const clone = editor.cloneNode(true) as HTMLElement;

  // 移除表格工具箱、选择框等辅助元素
  const removeSelectors = [
    '.table-up-toolbox',
    '.table-up-selection',
    '.table-up-resize-line',
    '.table-up-resize-box',
    '.table-up-scrollbar',
    '.table-up-scale',
    '.table-up-drag',
    '.table-up-align',
    '.table-up-menu',
    '.ql-tooltip',
    '.ql-counter',
  ];
  removeSelectors.forEach(selector => {
    clone.querySelectorAll(selector).forEach(el => el.remove());
  });

  // 移除 contenteditable 属性（PDF 不需要）
  clone.querySelectorAll('[contenteditable]').forEach(el => {
    el.removeAttribute('contenteditable');
  });

  // 移除 data-v- scoped 属性
  clone.querySelectorAll('*').forEach(el => {
    Array.from(el.attributes).forEach(attr => {
      if (attr.name.startsWith('data-v-')) {
        el.removeAttribute(attr.name);
      }
    });
  });

  // 清除编辑器中可能导致 PDF 内容截断的内联样式
  // 移除固定 max-width/overflow，让内容在 PDF 中自然流动
  // 保留 width（表格列宽需要）和 height
  const resetElements = [clone, ...Array.from(clone.querySelectorAll('*'))];
  resetElements.forEach(el => {
    if (el instanceof HTMLElement) {
      const style = el.style;
      // 移除最大宽度和溢出隐藏
      style.removeProperty('max-width');
      style.removeProperty('overflow');
      style.removeProperty('overflow-x');
      style.removeProperty('overflow-y');
      // 移除左侧 padding（编辑器为导航目录预留的空间，PDF 不需要）
      if (style.paddingLeft && parseInt(style.paddingLeft) > 20) {
        style.removeProperty('padding-left');
      }
      // 确保文本自动换行（不影响 pre 和 table 内部元素）
      const tag = el.tagName.toLowerCase();
      if (tag !== 'pre' && tag !== 'code' && !el.closest('pre')) {
        style.setProperty('word-wrap', 'break-word');
        style.setProperty('overflow-wrap', 'break-word');
      }
    }
  });

  return clone.innerHTML;
}

export async function exportPdfFrontend(
  title: string,
  _deltaContent: string,
  filename?: string
): Promise<void> {
  console.log('[PDFExport] 开始导出 PDF');

  // 直接从编辑器 DOM 获取 HTML，保留表格等自定义格式的完整结构
  let html = getEditorHtml();
  if (!html) {
    console.warn('[PDFExport] 编辑器内容为空');
    return;
  }

  // 修复图片 URL
  html = fixImageUrls(html);

  const fullHtml = `
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <title>${title}</title>
      <style>
        * { box-sizing: border-box; }
        body { font-family: 'SimSun', 'Microsoft YaHei', sans-serif; padding: 20px 40px; color: #333; }
        h1, h2, h3, h4, h5, h6 { color: #333; margin: 0.5em 0; }
        p { margin: 0.5em 0; }
        img { max-width: 100%; height: auto; }
        pre { background: #f5f5f5; padding: 12px; border-radius: 4px; white-space: pre-wrap; word-wrap: break-word; }
        code { background: #f0f0f0; padding: 2px 4px; border-radius: 3px; font-size: 90%; }
        blockquote { border-left: 4px solid #ddd; margin: 0; padding-left: 16px; color: #666; }
        /* 表格样式 */
        table { border-collapse: collapse; width: 100%; table-layout: auto; }
        td, th { border: 1px solid #a1a1aa; padding: 8px 12px; word-wrap: break-word; overflow-wrap: break-word; }
        .ql-table-wrapper { overflow: visible; }
        .ql-table-cell-inner { min-width: auto; }
        /* 确保所有文本自动换行 */
        * { word-wrap: break-word; overflow-wrap: break-word; }
      </style>
    </head>
    <body>
      <h1>${title}</h1>
      ${html}
    </body>
    </html>
  `;

  const container = document.createElement('div');
  container.innerHTML = fullHtml;
  // 容器放在可见区域但用 opacity 隐藏，确保 html2canvas 能正确渲染
  container.style.width = '794px'; // A4 宽度约 210mm ≈ 794px @96dpi
  container.style.background = '#ffffff';
  document.body.appendChild(container);

  try {
    console.log('[PDFExport] 开始使用 html2pdf 导出');
    const html2pdf = (await import('html2pdf.js')).default;

    await html2pdf().set({
      margin: [10, 10, 10, 10],
      filename: filename || `${title}.pdf`,
      image: { type: 'jpeg', quality: 0.98 },
      html2canvas: {
        scale: 2,
        useCORS: true,
        allowTaint: true,
        backgroundColor: '#ffffff',
      },
      jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
      pagebreak: { mode: ['avoid-all', 'css', 'legacy'] },
    }).from(container).save();

    console.log('[PDFExport] PDF 导出成功');
  } catch (err) {
    console.error('[PDFExport] PDF 导出失败:', err);
    throw err;
  } finally {
    document.body.removeChild(container);
  }
}
