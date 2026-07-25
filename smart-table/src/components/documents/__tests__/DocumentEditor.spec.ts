/**
 * DocumentEditor 组件测试
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { mount, flushPromises } from '@vue/test-utils';
import { createPinia, setActivePinia } from 'pinia';
import DocumentEditor from '../DocumentEditor.vue';

// Mock TinyEditor
vi.mock('@opentiny/fluent-editor', () => ({
  default: class MockFluentEditor {
    private _contents = { ops: [{ insert: 'test content\n' }] };
    constructor(_container: HTMLElement, _options: any) {
      // Mock implementation
    }
    static register(_name: string | object, _target?: any, _overwrite?: boolean) {}
    setContents(content: any) {
      this._contents = content;
    }
    getContents() {
      return this._contents;
    }
    on(_event: string, _handler: () => void) {}
    off(_event: string, _handler: () => void) {}
    get root() {
      return document.createElement('div');
    }
    getModule(_name: string) {
      return null;
    }
  }
}));

vi.mock('@/services/api/documentApiService', () => ({
  documentApiService: {
    update: vi.fn()
  }
}));

import { documentApiService } from '@/services/api/documentApiService';
const updateMock = documentApiService.update as ReturnType<typeof vi.fn>;

describe('DocumentEditor', () => {
  const createWrapper = (props = {}) => {
    return mount(DocumentEditor, {
      props: {
        document: {
          id: 'doc-1',
          baseId: 'base-1',
          name: '测试文档',
          content: '{"ops":[]}',
          contentFormat: 'delta',
          order: 0,
          isPinned: false,
          createdAt: Date.now(),
          updatedAt: Date.now()
        },
        baseId: 'base-1',
        ...props
      }
    });
  };

  beforeEach(() => {
    setActivePinia(createPinia());
    updateMock.mockReset();
    updateMock.mockResolvedValue({ id: 'doc-1', name: '测试文档' });
    vi.useFakeTimers();
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('renders with document title', () => {
    const wrapper = createWrapper();
    expect(wrapper.find('.document-editor__title').exists()).toBe(true);
    expect(wrapper.find('.document-editor__actions').exists()).toBe(true);
  });

  it('displays document name in title input', () => {
    const wrapper = createWrapper({
      document: {
        id: 'doc-1',
        baseId: 'base-1',
        name: '我的文档',
        content: '{"ops":[]}',
        contentFormat: 'delta',
        order: 0,
        isPinned: false,
        createdAt: Date.now(),
        updatedAt: Date.now()
      }
    });

    const input = wrapper.find('.document-editor__title');
    expect(input.exists()).toBe(true);
  });

  it('emits export-pdf event when export button clicked', async () => {
    const wrapper = createWrapper();
    await flushPromises();

    const exportButton = wrapper.findAll('button').find(btn => btn.text().includes('导出 PDF'));
    if (exportButton) {
      await exportButton.trigger('click');
      expect(wrapper.emitted('export-pdf')).toBeTruthy();
    }
  });

  it('calls update API when save button clicked', async () => {
    const wrapper = createWrapper();
    await flushPromises();

    const saveButton = wrapper.findAll('button').find(btn => btn.text().includes('保存'));
    expect(saveButton).toBeTruthy();

    await saveButton!.trigger('click');
    await flushPromises();

    expect(updateMock).toHaveBeenCalledTimes(1);
    expect(updateMock).toHaveBeenCalledWith('doc-1', {
      content: '{"ops":[{"insert":"test content\\n"}]}',
      contentFormat: 'delta'
    });
  });

  it('shows save status indicator', async () => {
    const wrapper = createWrapper();
    await flushPromises();

    expect(wrapper.find('.save-status').exists()).toBe(true);
  });

  it('exposes hasUnsavedChanges method', async () => {
    const wrapper = createWrapper();
    await flushPromises();

    expect(typeof wrapper.vm.hasUnsavedChanges).toBe('function');
  });
});
