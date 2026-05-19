/**
 * PDF 前端导出工具
 */

function deltaToHtml(deltaJson: string): string {
  const { QuillDeltaToHtmlConverter } = require('quill-delta-to-html');
  const delta = JSON.parse(deltaJson);
  const converter = new QuillDeltaToHtmlConverter(delta.ops || [], {
    encodeHtml: false,
    inlineStyles: true
  });
  return converter.convert();
}

export async function exportPdfFrontend(
  title: string,
  deltaContent: string,
  filename?: string
): Promise<void> {
  const html = deltaToHtml(deltaContent);

  const fullHtml = `
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <title>${title}</title>
      <style>
        body { font-family: 'SimSun', 'Microsoft YaHei', sans-serif; padding: 40px; }
        h1, h2, h3, h4, h5, h6 { color: #333; }
        img { max-width: 100%; }
        pre { background: #f5f5f5; padding: 12px; border-radius: 4px; }
        blockquote { border-left: 4px solid #ddd; margin: 0; padding-left: 16px; color: #666; }
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
  document.body.appendChild(container);

  const html2pdf = (await import('html2pdf.js')).default;
  await html2pdf().set({
    margin: [10, 10],
    filename: filename || `${title}.pdf`,
    image: { type: 'jpeg', quality: 0.98 },
    html2canvas: { scale: 2, useCORS: true },
    jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' }
  }).from(container).save();

  document.body.removeChild(container);
}
