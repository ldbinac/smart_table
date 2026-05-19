"""
文档内容转换工具
支持 Delta 格式与 HTML 之间的转换
"""
import json


def delta_to_html(delta_json: str) -> str:
    """
    将 Quill Delta JSON 转换为 HTML

    Args:
        delta_json: Quill Delta 格式的 JSON 字符串

    Returns:
        HTML 字符串
    """
    if not delta_json:
        return ''

    try:
        delta = json.loads(delta_json)
        ops = delta.get('ops', [])

        if not ops:
            return ''

        # 简单的 Delta 到 HTML 转换
        html_parts = []
        current_block = []
        block_type = 'paragraph'

        for op in ops:
            insert = op.get('insert', '')
            attributes = op.get('attributes', {})

            if isinstance(insert, str):
                # 处理换行符（段落分隔）
                if '\n' in insert:
                    parts = insert.split('\n')
                    for i, part in enumerate(parts):
                        if part:
                            text = _apply_inline_styles(part, attributes)
                            current_block.append(text)

                        # 如果不是最后一部分，结束当前段落
                        if i < len(parts) - 1:
                            if current_block:
                                html_parts.append(_wrap_block(current_block, block_type))
                                current_block = []
                            block_type = 'paragraph'
                else:
                    text = _apply_inline_styles(insert, attributes)
                    current_block.append(text)

                # 检查块级属性（如标题）
                if attributes.get('header'):
                    block_type = f"h{attributes['header']}"

        # 处理最后一段
        if current_block:
            html_parts.append(_wrap_block(current_block, block_type))

        return '\n'.join(html_parts)

    except (json.JSONDecodeError, KeyError) as e:
        # 如果解析失败，返回原始文本
        return f'<p>{delta_json}</p>'


def _apply_inline_styles(text: str, attributes: dict) -> str:
    """应用内联样式"""
    if attributes.get('bold'):
        text = f'<strong>{text}</strong>'
    if attributes.get('italic'):
        text = f'<em>{text}</em>'
    if attributes.get('underline'):
        text = f'<u>{text}</u>'
    if attributes.get('strike'):
        text = f'<s>{text}</s>'
    if attributes.get('code'):
        text = f'<code>{text}</code>'
    if attributes.get('link'):
        text = f'<a href="{attributes["link"]}">{text}</a>'
    if attributes.get('color'):
        text = f'<span style="color: {attributes["color"]}">{text}</span>'
    if attributes.get('background'):
        text = f'<span style="background-color: {attributes["background"]}">{text}</span>'

    return text


def _wrap_block(block: list[str], block_type: str) -> str:
    """包装块级元素"""
    content = ''.join(block)

    if block_type.startswith('h'):
        return f'<{block_type}>{content}</{block_type}>'
    elif block_type == 'blockquote':
        return f'<blockquote>{content}</blockquote>'
    elif block_type == 'code-block':
        return f'<pre><code>{content}</code></pre>'
    else:
        return f'<p>{content}</p>'
