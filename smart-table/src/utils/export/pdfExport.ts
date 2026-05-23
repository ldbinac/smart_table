/**
 * PDF 前端导出工具
 */

let QuillDeltaToHtmlConverter: any = null;

// 修复图片 URL 问题
function fixImageUrls(delta: any): any {
  if (!delta || !delta.ops) return delta;
  
  // 创建 ops 副本，避免修改原始数据
  const fixedOps = delta.ops.map((op: any) => {
    if (op.insert && op.insert.image) {
      // 确保 image 是一个正确的字符串 URL
      let imageUrl = op.insert.image;
      
      // 如果是对象类型，尝试获取其中的 URL
      if (typeof imageUrl === 'object') {
        console.log('[PDFExport] 发现对象类型的图片:', imageUrl);
        // 尝试从对象中获取 URL
        if (imageUrl.url) {
          imageUrl = imageUrl.url;
        } else if (imageUrl.src) {
          imageUrl = imageUrl.src;
        } else {
          // 如果无法获取 URL，跳过该图片
          console.warn('[PDFExport] 无法解析的图片对象:', imageUrl);
          return { ...op, insert: '[图片]' };
        }
      }
      
      // 确保 URL 是字符串类型
      if (typeof imageUrl === 'string') {
        // 处理相对路径
        if (imageUrl.startsWith('/')) {
          imageUrl = `${window.location.origin}${imageUrl}`;
        } else if (!imageUrl.startsWith('http')) {
          imageUrl = `${window.location.origin}/${imageUrl}`;
        }
        
        console.log('[PDFExport] 修复后的图片 URL:', imageUrl);
        
        // 返回修复后的图片操作
        return {
          ...op,
          insert: { image: imageUrl }
        };
      }
    }
    return op;
  });
  
  return { ...delta, ops: fixedOps };
}

async function deltaToHtml(deltaJson: string): string {
  try {
    if (!QuillDeltaToHtmlConverter) {
      const module = await import('quill-delta-to-html');
      QuillDeltaToHtmlConverter = module.QuillDeltaToHtmlConverter;
    }
    
    let delta = JSON.parse(deltaJson);
    
    // 修复图片 URL
    delta = fixImageUrls(delta);
    
    const converter = new QuillDeltaToHtmlConverter(delta.ops || [], {
      encodeHtml: false,
      inlineStyles: true
    });
    
    const html = converter.convert();
    console.log('[PDFExport] 生成的 HTML:', html);
    return html;
  } catch (e) {
    console.error('[PDFExport] 转换 delta 为 html 失败:', e);
    // 如果转换失败，返回原内容或空内容
    return '';
  }
}

export async function exportPdfFrontend(
  title: string,
  deltaContent: string,
  filename?: string
): Promise<void> {
  console.log('[PDFExport] 开始导出 PDF');
  const html = await deltaToHtml(deltaContent);
  console.log('[PDFExport] 转换 HTML 成功');

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

  try {
    console.log('[PDFExport] 开始使用 html2pdf 导出');
    const html2pdf = (await import('html2pdf.js')).default;
    
    // 优化的 html2canvas 配置
    await html2pdf().set({
      margin: [10, 10],
      filename: filename || `${title}.pdf`,
      image: { type: 'jpeg', quality: 0.98 },
      html2canvas: { 
        scale: 2, 
        useCORS: true,
        allowTaint: true,  // 允许跨域图片
        logging: true,     // 开启日志便于调试
        letterRendering: true,
        backgroundColor: '#ffffff',
        onclone: function (clonedDoc: Document) {
          console.log('[PDFExport] html2canvas 克隆 DOM');
          // 可以在这里进一步处理克隆后的 DOM
          const images = clonedDoc.querySelectorAll('img');
          images.forEach((img, index) => {
            console.log(`[PDFExport] 图片 ${index}:`, img.src);
          });
        }
      },
      jsPDF: { unit: 'mm', format: 'a4', orientation: 'portrait' }
    }).from(container).save();
    
    console.log('[PDFExport] PDF 导出成功');
  } catch (err) {
    console.error('[PDFExport] PDF 导出失败:', err);
    throw err;
  } finally {
    document.body.removeChild(container);
  }
}
