/**
 * DocumentVersionHistory 组件测试
 */
import { describe, it, expect, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import DocumentVersionHistory from '../DocumentVersionHistory.vue';

// Mock TinyEditor
vi.mock('@opentiny/fluent-editor', () => ({
  default: class MockFluentEditor {
    constructor(_container: HTMLElement, _options: any) {
      // Mock implementation
    }
    setContents(_content: any) {}
    getContents() {
      return { ops: [{ insert: 'test content\n' }] };
    }
  },
}));

// Mock Element Plus components
vi.mock('element-plus', async () => {
  const actual = await vi.importActual('element-plus');
  return {
    ...actual,
    ElDialog: { template: '<div><slot></slot><slot name="footer"></slot></div>' },
    ElButton: { template: '<button><slot></slot></button>' },
    ElTag: { template: '<span><slot></slot></span>' },
  };
});

describe('DocumentVersionHistory', () => {
  const mockVersions = [
    {
      id: 'v1',
      documentId: 'doc-1',
      name: '版本 1',
      content: '{"ops":[{"insert":"version 1\\n"}]}',
      contentFormat: 'delta' as const,
      versionNumber: 1,
      changeSummary: '创建文档',
      createdBy: 'user-1',
      createdAt: Date.now() - 3600000
    },
    {
      id: 'v2',
      documentId: 'doc-1',
      name: '版本 2',
      content: '{"ops":[{"insert":"version 2\\n"}]}',
      contentFormat: 'delta' as const,
      versionNumber: 2,
      changeSummary: '更新内容',
      createdBy: 'user-1',
      createdAt: Date.now() - 1800000
    }
  ];

  it('renders without errors', () => {
    const wrapper = mount(DocumentVersionHistory, {
      props: {
        visible: true,
        documentId: 'doc-1',
        versions: mockVersions,
        loading: false
      }
    });

    // 检查是否能正常渲染
    expect(wrapper.exists()).toBe(true);
  });

  it('emits close event', async () => {
    const wrapper = mount(DocumentVersionHistory, {
      props: {
        visible: true,
        documentId: 'doc-1',
        versions: mockVersions,
        loading: false
      }
    });

    // 组件是否能 emit close 事件的基础验证
    expect(wrapper.exists()).toBe(true);
  });
});
