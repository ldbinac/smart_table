"""
文档导出服务模块
支持导出为 PDF 等格式
"""
import tempfile

from app.utils.document_converter import delta_to_html


class DocumentExportService:
    """文档导出服务类"""

    @staticmethod
    def export_pdf(document, export_type='backend'):
        """
        导出文档为 PDF

        Args:
            document: Document 模型实例
            export_type: 'frontend' | 'backend'

        Returns:
            导出结果字典
        """
        if export_type == 'frontend':
            return {
                'type': 'frontend',
                'document': document.to_dict(include_content=True)
            }

        # 后端导出，返回下载链接
        return {
            'type': 'backend',
            'download_url': f'/api/documents/{document.id}/download-pdf',
            'filename': f'{document.name}.pdf'
        }

    @staticmethod
    def _convert_to_html(document):
        """
        将文档内容转换为 HTML

        Args:
            document: Document 模型实例

        Returns:
            HTML 字符串
        """
        content_html = delta_to_html(document.content) if document.content else ''

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{document.name}</title>
            <style>
                @page {{ size: A4; margin: 2cm; }}
                body {{ font-family: 'SimSun', 'Microsoft YaHei', sans-serif; line-height: 1.6; }}
                h1 {{ color: #333; border-bottom: 2px solid #eee; padding-bottom: 10px; }}
                h2, h3, h4, h5, h6 {{ color: #444; margin-top: 20px; }}
                p {{ margin: 10px 0; }}
                img {{ max-width: 100%; height: auto; }}
                pre {{ background: #f5f5f5; padding: 12px; border-radius: 4px; overflow-x: auto; }}
                code {{ background: #f5f5f5; padding: 2px 6px; border-radius: 3px; font-family: monospace; }}
                blockquote {{ border-left: 4px solid #ddd; margin: 0; padding-left: 16px; color: #666; }}
                ul, ol {{ margin: 10px 0; padding-left: 20px; }}
                li {{ margin: 5px 0; }}
                a {{ color: #6366F1; text-decoration: none; }}
                table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background: #f5f5f5; }}
            </style>
        </head>
        <body>
            <h1>{document.name}</h1>
            {content_html}
        </body>
        </html>
        """
