/**
 * PDF 前端导出工具
 * 所见即所得：直接截取编辑器 DOM 渲染结果，确保导出样式与编辑器完全一致
 */

export async function exportPdfFrontend(
  title: string,
  _deltaContent: string,
  filename?: string
): Promise<void> {
  console.log('[PDFExport] 开始导出 PDF');

  // 直接截取编辑器内容区域，实现所见即所得
  const editorEl = document.querySelector('.ql-editor');
  if (!editorEl) {
    console.warn('[PDFExport] 未找到编辑器元素');
    return;
  }

  try {
    console.log('[PDFExport] 开始使用 html2pdf 导出');
    const html2pdf = (await import('html2pdf.js')).default;

    await html2pdf().set({
      // jsPDF margin 控制每页的 PDF 页边距（单位 mm，32px ≈ 8.5mm）
      // 这是唯一能让每一页顶部/底部都生效的方式
      margin: 8.5,
      filename: filename || `${title}.pdf`,
      image: { type: 'jpeg', quality: 0.98 },
      html2canvas: {
        scale: 2,
        useCORS: true,
        allowTaint: true,
        backgroundColor: '#ffffff',
        // 临时移除左侧 padding（导航目录空间），导出后恢复
        onclone: (clonedDoc: Document) => {
          const clonedEditor = clonedDoc.querySelector('.ql-editor');
          if (!clonedEditor) return;

          // // 注入导出专用样式（使用 !important 确保覆盖所有来源的样式）
          // const styleEl = clonedDoc.createElement('style');
          // styleEl.textContent = [
          //   '.ql-editor { padding: 0 !important; }',
          //   '.ql-editor > h1,',
          //   '.ql-editor > h2,',
          //   '.ql-editor > h3,',
          //   '.ql-editor > h4,',
          //   '.ql-editor > h5,',
          //   '.ql-editor > h6,',
          //   '.ql-editor > p,',
          //   '.ql-editor > ul,',
          //   '.ql-editor > ol,',
          //   '.ql-editor > blockquote,',
          //   '.ql-editor > .ql-code-block-container,',
          //   '.ql-editor > .ql-table-wrapper {',
          //   '  padding-left: 32px !important;',
          //   '  padding-right: 32px !important;',
          //   '}',
          // ].join('\n');
          // clonedDoc.head.appendChild(styleEl);

          // 移除编辑器辅助 UI 元素
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
              clonedEditor.querySelectorAll(selector).forEach(el => el.remove());
            });
        }
      },
      jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' },
      pagebreak: { mode: ['avoid-all', 'css', 'legacy'] },
    }).from(editorEl).save();

    console.log('[PDFExport] PDF 导出成功');
  } catch (err) {
    console.error('[PDFExport] PDF 导出失败:', err);
    throw err;
  }
}
