import { HeaderWithID } from 'quill-header-list';

/**
 * 修复 quill-header-list 的 HeaderWithID.create 未处理字符串 value 的问题。
 *
 * 工具栏设置标题时传入的是字符串（如 "1"），原实现会把字符串当作对象处理，
 * 导致 value 被错误地置为 0，最终 Parchment 用 tagName[-1] 创建出 <undefined> 节点。
 * 此覆盖类在调用父类前将可解析的字符串/数字统一转换为 number。
 */
export class HeaderWithIDFixed extends HeaderWithID {
  static create(value: any) {
    if (typeof value === 'string') {
      // 优先处理 H1~H6 的 tagName 字符串
      const tagIndex = (this.tagName as string[]).indexOf(value.toUpperCase());
      if (tagIndex >= 0) {
        value = tagIndex + 1;
      } else {
        const num = Number(value);
        if (!Number.isNaN(num)) {
          value = num;
        }
      }
    }
    return super.create(value);
  }
}
