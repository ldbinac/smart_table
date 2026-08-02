/**
 * WorkflowNodeConfig 组件测试 - script 节点配置面板
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount } from '@vue/test-utils';
import { nextTick } from 'vue';
import WorkflowNodeConfig from '../WorkflowNodeConfig.vue';

// Mock CodeMirror（jsdom 环境下 CodeMirror 6 无法正常渲染）
vi.mock('vue-codemirror', () => ({
  Codemirror: {
    name: 'Codemirror',
    template: '<div class="codemirror-stub" />',
    props: ['modelValue', 'extensions', 'disabled', 'style'],
    emits: ['update:modelValue', 'change'],
  },
}));

// Mock CodeMirror 语言包
vi.mock('@codemirror/lang-python', () => ({
  python: vi.fn(() => []),
}));

// Mock 脚本节点测试 API（避免引入真实 apiClient）
vi.mock('@/services/api/workflowApiService', () => ({
  testScriptNode: vi.fn(),
}));

// Mock Element Plus 图标（包含 Cpu，script 节点图标）
vi.mock('@element-plus/icons-vue', () => ({
  Delete: { template: '<span class="icon-delete" />' },
  Plus: { template: '<span class="icon-plus" />' },
  EditPen: { template: '<span class="icon-edit-pen" />' },
  Check: { template: '<span class="icon-check" />' },
  Close: { template: '<span class="icon-close" />' },
  Document: { template: '<span class="icon-document" />' },
  Memo: { template: '<span class="icon-memo" />' },
  ScaleToOriginal: { template: '<span class="icon-scale-to-original" />' },
  Calendar: { template: '<span class="icon-calendar" />' },
  AlarmClock: { template: '<span class="icon-alarm-clock" />' },
  CircleCheck: { template: '<span class="icon-circle-check" />' },
  FolderChecked: { template: '<span class="icon-folder-checked" />' },
  TurnOff: { template: '<span class="icon-turn-off" />' },
  Star: { template: '<span class="icon-star" />' },
  User: { template: '<span class="icon-user" />' },
  Link: { template: '<span class="icon-link" />' },
  Paperclip: { template: '<span class="icon-paperclip" />' },
  Phone: { template: '<span class="icon-phone" />' },
  Message: { template: '<span class="icon-message" />' },
  PieChart: { template: '<span class="icon-pie-chart" />' },
  List: { template: '<span class="icon-list" />' },
  Share: { template: '<span class="icon-share" />' },
  Search: { template: '<span class="icon-search" />' },
  Timer: { template: '<span class="icon-timer" />' },
  InfoFilled: { template: '<span class="icon-info-filled" />' },
  Refresh: { template: '<span class="icon-refresh" />' },
  Cpu: { template: '<span class="icon-cpu" />' },
  QuestionFilled: { template: '<span class="icon-question-filled" />' },
}));

// Mock 工具函数
vi.mock('@/utils/filter', () => ({
  getOperatorsForFieldType: vi.fn(() => []),
  OPERATOR_LABELS: {},
  operatorRequiresValue: vi.fn(() => true),
}));

// Mock fieldService
vi.mock('@/db/services/fieldService', () => ({
  fieldService: {
    getFieldsByTable: vi.fn(() => Promise.resolve([])),
  },
}));

// Mock api 模块（send_email 节点通过动态 import 加载邮件模板）
vi.mock('@/utils/api', () => ({
  default: {
    get: vi.fn(() => Promise.resolve({ data: { data: [] } })),
  },
}));

// Mock Element Plus 的 ElMessage
vi.mock('element-plus', async () => {
  const actual = await vi.importActual('element-plus');
  return {
    ...actual,
    ElMessage: {
      success: vi.fn(),
      warning: vi.fn(),
      error: vi.fn(),
      info: vi.fn(),
    },
  };
});

describe('WorkflowNodeConfig script 面板', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const mockScriptNode = {
    id: 'n1',
    workflow_id: 'wf1',
    node_type: 'script' as const,
    name: '脚本节点',
    config: {
      language: 'python',
      script_source: '',
      timeout: 30,
      result_variable: 'script_result',
      input_node_id: null,
      branches: [],
    },
    order: 1,
    next_nodes: [],
  };

  function mountScript(overrides: { readonly?: boolean; node?: Record<string, unknown> } = {}) {
    return mount(WorkflowNodeConfig, {
      props: {
        node: overrides.node ?? mockScriptNode,
        fields: [],
        allNodes: [],
        readonly: overrides.readonly ?? false,
      },
      global: {
        stubs: {
          'el-button': {
            template:
              '<button class="el-button" :class="$props.class" :disabled="$props.disabled" @click="$emit(\'click\', $event)"><slot /></button>',
            props: ['type', 'icon', 'link', 'size', 'class', 'disabled', 'loading'],
            emits: ['click'],
          },
          'el-input': {
            template:
              '<input class="el-input" :class="$props.class" :value="modelValue" :disabled="disabled" @input="$emit(\'update:modelValue\', $event.target.value)" @blur="$emit(\'blur\')" @keydown="$emit(\'keydown\', $event)" />',
            props: ['modelValue', 'size', 'class', 'disabled', 'type', 'rows', 'placeholder'],
            emits: ['update:modelValue', 'blur', 'keydown'],
          },
          'el-form': { template: '<form class="el-form"><slot /></form>' },
          'el-form-item': {
            template:
              '<div class="el-form-item"><label v-if="label" class="el-form-item__label">{{ label }}</label><slot /></div>',
            props: ['label'],
          },
          'el-radio-group': {
            template:
              '<div class="el-radio-group" :class="{ \'is-disabled\': disabled }"><slot /></div>',
            props: ['disabled', 'modelValue'],
            emits: ['update:modelValue', 'change'],
          },
          'el-radio': {
            template: '<label class="el-radio"><slot /></label>',
            props: ['label'],
          },
          'el-select': {
            template:
              '<select class="el-select" :class="$props.class" :value="modelValue" :disabled="disabled" @change="$emit(\'update:modelValue\', $event.target.value); $emit(\'change\', $event.target.value)"><slot /></select>',
            props: ['class', 'modelValue', 'disabled', 'placeholder', 'clearable'],
            emits: ['update:modelValue', 'change'],
          },
          'el-option': {
            template: '<option class="el-option" :value="value">{{ label }}<slot /></option>',
            props: ['label', 'value'],
          },
          'el-input-number': {
            template: '<div class="el-input-number"><input :disabled="disabled" /><slot /></div>',
            props: ['modelValue', 'min', 'max', 'disabled'],
            emits: ['update:modelValue', 'change'],
          },
          'el-divider': { template: '<hr class="el-divider" />' },
          'el-empty': {
            template: '<div class="el-empty">{{ description }}<slot /></div>',
            props: ['description', 'imageSize'],
          },
          'el-icon': { template: '<i class="el-icon"><slot /></i>' },
          'el-tag': { template: '<span class="el-tag"><slot /></span>' },
          'el-alert': {
            template: '<div class="el-alert">{{ title }} {{ description }}</div>',
            props: ['title', 'description', 'type', 'closable'],
          },
          'el-dropdown': {
            template: '<div class="el-dropdown"><slot /><slot name="dropdown" /></div>',
            emits: ['command'],
          },
          'el-dropdown-menu': { template: '<div class="el-dropdown-menu"><slot /></div>' },
          'el-dropdown-item': {
            template:
              '<div class="el-dropdown-item" :class="{ \'is-disabled\': disabled }" @click="$emit(\'command\', command)"><slot /></div>',
            props: ['command', 'disabled'],
            emits: ['command'],
          },
          FieldValueInput: { template: '<input class="field-value-input" />' },
          LoopVarInserter: { template: '<div class="loop-var-inserter" />' },
        },
      },
    });
  }

  it('script 节点渲染配置面板', async () => {
    const wrapper = mountScript();
    await nextTick();

    expect(wrapper.text()).toContain('脚本代码');
    expect(wrapper.text()).toContain('超时时间');
  });

  it('不渲染语言选择器（仅支持 Python）', async () => {
    const wrapper = mountScript();
    await nextTick();

    // 语言选择器已移除，不应出现 TypeScript 选项
    expect(wrapper.text()).not.toContain('TypeScript');
    expect(wrapper.text()).not.toContain('脚本语言');
  });

  it('渲染脚本代码编辑器容器', async () => {
    const wrapper = mountScript();
    await nextTick();

    // CodeMirror 被 mock 为 .codemirror-stub
    expect(wrapper.find('.codemirror-stub').exists()).toBe(true);
    expect(wrapper.text()).toContain('脚本代码');
  });

  it('渲染结果变量名输入框', async () => {
    const wrapper = mountScript();
    await nextTick();

    expect(wrapper.text()).toContain('结果变量名');
  });

  it('渲染输入来源选择器', async () => {
    const wrapper = mountScript();
    await nextTick();

    expect(wrapper.text()).toContain('输入来源');
  });

  it('渲染分支路由区域', async () => {
    const wrapper = mountScript();
    await nextTick();

    expect(wrapper.text()).toContain('分支路由');
    expect(wrapper.text()).toContain('添加分支');
  });

  it('渲染测试运行区域与按钮', async () => {
    const wrapper = mountScript();
    await nextTick();

    expect(wrapper.text()).toContain('测试运行');
    expect(wrapper.text()).toContain('示例输入');
    // 测试运行按钮存在
    const buttons = wrapper.findAll('button');
    const testBtn = buttons.find((b) => b.text().includes('测试运行'));
    expect(testBtn).toBeTruthy();
  });

  it('渲染插入模板选择器', async () => {
    const wrapper = mountScript();
    await nextTick();

    expect(wrapper.text()).toContain('插入模板');
  });

  it('只读模式下测试运行按钮被禁用', async () => {
    const wrapper = mountScript({ readonly: true });
    await nextTick();

    const buttons = wrapper.findAll('button');
    const testBtn = buttons.find((b) => b.text().includes('测试运行'));
    expect(testBtn).toBeTruthy();
    expect(testBtn!.attributes('disabled')).toBeDefined();
  });

  it('只读模式下不显示添加分支按钮', async () => {
    const wrapper = mountScript({ readonly: true });
    await nextTick();

    const buttons = wrapper.findAll('button');
    const addBranchBtn = buttons.find((b) => b.text().includes('添加分支'));
    expect(addBranchBtn).toBeFalsy();
  });

  it('渲染使用帮助按钮', async () => {
    const wrapper = mountScript();
    await nextTick();

    const buttons = wrapper.findAll('button');
    const helpBtn = buttons.find((b) => b.text().includes('使用帮助'));
    expect(helpBtn).toBeTruthy();
  });

  it('点击使用帮助按钮切换帮助面板显示', async () => {
    const wrapper = mountScript();
    await nextTick();

    // 初始状态帮助面板隐藏（v-show 控制的元素 style.display 为 none）
    const panel = wrapper.find('.script-help-panel');
    expect(panel.exists()).toBe(true);
    expect(panel.attributes('style')?.includes('display: none')).toBe(true);

    // 点击使用帮助按钮
    const helpBtn = wrapper.find('.script-help-btn');
    expect(helpBtn.exists()).toBe(true);
    await helpBtn.trigger('click');
    await nextTick();

    // 帮助面板显示（display: none 已移除）
    expect(panel.attributes('style')?.includes('display: none')).toBe(false);
    expect(wrapper.text()).toContain('预置变量');
    expect(wrapper.text()).toContain('预置函数');
    expect(wrapper.text()).toContain('白名单模块');
    expect(wrapper.text()).toContain('执行规则');
  });

  it('帮助面板根据语言显示对应的 API 函数名', async () => {
    const wrapper = mountScript();
    await nextTick();

    // 点击使用帮助按钮显示面板
    const buttons = wrapper.findAll('button');
    const helpBtn = buttons.find((b) => b.text().includes('使用帮助'));
    await helpBtn!.trigger('click');
    await nextTick();

    // 默认 Python 语言，应显示 set_result / set_branch
    expect(wrapper.text()).toContain('set_result(value)');
    expect(wrapper.text()).toContain('set_branch(label)');
  });
});
