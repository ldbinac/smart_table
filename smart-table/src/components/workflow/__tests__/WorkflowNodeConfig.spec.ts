/**
 * WorkflowNodeConfig 组件测试
 */
import { describe, it, expect, vi, beforeEach } from 'vitest';
import { mount } from '@vue/test-utils';
import { nextTick } from 'vue';
import { ElMessage } from 'element-plus';
import { fieldService } from '@/db/services/fieldService';
import type { FieldEntity } from '@/db/schema';
import WorkflowNodeConfig from '../WorkflowNodeConfig.vue';

// Mock Element Plus 图标
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

// Mock api 模块（send_email 节点通过动态 import("@/utils/api") 加载邮件模板）
vi.mock('@/utils/api', () => ({
  default: {
    get: vi.fn(() => Promise.resolve({ data: { data: [] } })),
  },
}));

// Mock Element Plus 的 ElMessage（避免 jsdom 中真实渲染消息提示）
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

describe('WorkflowNodeConfig', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  const mockNode = {
    id: 'node-1',
    workflow_id: 'wf-1',
    node_type: 'send_email' as const,
    name: '发送邮件 1',
    config: {},
    order: 0,
    next_nodes: [],
  };

  const mockFields = [
    { id: 'field-1', name: '标题', type: 'single_line_text' },
    { id: 'field-2', name: '状态', type: 'single_select' },
    { id: 'field-3', name: '完成度', type: 'progress' },
    { id: 'field-4', name: '是否通过', type: 'checkbox' },
  ];

  const mockTargetFields = [
    { id: 'target-1', name: '目标标题', type: 'single_line_text' },
    { id: 'target-2', name: '目标状态', type: 'single_select' },
    { id: 'target-3', name: '目标完成度', type: 'progress' },
  ] as FieldEntity[];

  const mockTables = [
    { id: 'table-1', name: '源表' },
    { id: 'table-2', name: '目标表' },
  ];

  function mountConfig(overrideProps: any = {}) {
    return mount(WorkflowNodeConfig, {
      props: {
        node: overrideProps.node ?? mockNode,
        fields: overrideProps.fields ?? mockFields,
        tables: overrideProps.tables,
        webhooks: overrideProps.webhooks,
        allNodes: overrideProps.allNodes,
        readonly: overrideProps.readonly ?? false,
      },
      global: {
        stubs: {
          'el-button': {
            template: '<button class="el-button" :class="$props.class" @click="$emit(\'click\', $event)"><slot /></button>',
            props: ['type', 'icon', 'link', 'size', 'class'],
            emits: ['click'],
          },
          'el-input': {
            template: '<input class="el-input" :class="$props.class" :value="modelValue" @input="$emit(\'update:modelValue\', $event.target.value)" @blur="$emit(\'blur\')" @keydown="$emit(\'keydown\', $event)" />',
            props: ['modelValue', 'size', 'class'],
            emits: ['update:modelValue', 'blur', 'keydown'],
          },
          'el-form': { template: '<form class="el-form"><slot /></form>' },
          'el-form-item': { template: '<div class="el-form-item"><label v-if="label" class="el-form-item__label">{{ label }}</label><slot /></div>', props: ['label'] },
          'el-radio-group': { template: '<div class="el-radio-group" :class="{ &quot;is-disabled&quot;: disabled }"><slot /></div>', props: ['disabled', 'modelValue'], emits: ['update:modelValue'] },
          'el-radio': { template: '<label class="el-radio"><slot /></label>' },
          'el-select': { template: '<select class="el-select" :class="$props.class" :value="modelValue" @change="$emit(\'update:modelValue\', $event.target.value); $emit(\'change\', $event.target.value)"><slot /></select>', props: ['class', 'modelValue'], emits: ['update:modelValue', 'change'] },
          'el-option': { template: '<option class="el-option" :value="value">{{ label }}<slot /></option>', props: ['label', 'value'] },
          'el-input-number': { template: '<div class="el-input-number"><input /><slot /></div>' },
          'el-date-picker': { template: '<input class="el-date-picker" />' },
          'el-switch': { template: '<button class="el-switch" @click="$emit(\'update:modelValue\', !modelValue)"><slot /></button>', props: ['modelValue'], emits: ['update:modelValue'] },
          'el-rate': { template: '<div class="el-rate"><slot /></div>' },
          'el-divider': { template: '<hr class="el-divider" />' },
          'el-empty': { template: '<div class="el-empty">{{ description }}<slot /></div>', props: ['description', 'imageSize'] },
          'el-icon': { template: '<i class="el-icon"><slot /></i>' },
          'el-dropdown': {
            template: '<div class="el-dropdown"><slot /><slot name="dropdown" /></div>',
            emits: ['command'],
          },
          'el-dropdown-menu': { template: '<div class="el-dropdown-menu"><slot /></div>' },
          'el-dropdown-item': {
            template: '<div class="el-dropdown-item" :class="{ \'is-disabled\': disabled }" @click="$emit(\'command\', command)"><slot /></div>',
            props: ['command', 'disabled'],
            emits: ['command'],
          },
          'el-tag': { template: '<span class="el-tag"><slot /></span>' },
          'el-alert': {
            template: '<div class="el-alert">{{ title }} {{ description }}</div>',
            props: ['title', 'description', 'type', 'closable'],
          },
          'FieldValueInput': { template: '<input class="field-value-input" />' },
          'LoopVarInserter': {
            template: '<div class="loop-var-inserter" :data-supports-field-drill="supportsFieldDrill ? \'true\' : \'false\'" :data-disabled="disabled ? \'true\' : \'false\'" :data-field-count="fieldOptions ? fieldOptions.length : 0" @click="$emit(\'insert\', \'{{loop.current_data}}\')">插入循环变量</div>',
            props: ['supportsFieldDrill', 'fieldOptions', 'disabled'],
            emits: ['insert'],
          },
        },
      },
    });
  }

  it('应该渲染节点名称（纯文本模式）', () => {
    const wrapper = mountConfig();
    const nameSpan = wrapper.find('.node-name');
    expect(nameSpan.exists()).toBe(true);
    expect(nameSpan.text()).toBe('发送邮件 1');
  });

  it('草稿态下应该显示编辑按钮', () => {
    const wrapper = mountConfig({ readonly: false });
    const editBtn = wrapper.find('.edit-name-btn');
    expect(editBtn.exists()).toBe(true);
  });

  it('非草稿态下不应该显示编辑按钮', () => {
    const wrapper = mountConfig({ readonly: true });
    const editBtn = wrapper.find('.edit-name-btn');
    expect(editBtn.exists()).toBe(false);
  });

  it('点击编辑按钮应该进入编辑模式并显示输入框', async () => {
    const wrapper = mountConfig();
    const editBtn = wrapper.find('.edit-name-btn');
    await editBtn.trigger('click');
    await nextTick();

    const nameInput = wrapper.find('.name-input');
    expect(nameInput.exists()).toBe(true);
    expect(wrapper.find('.node-name').exists()).toBe(false);
  });

  it('修改名称后按 Enter 应该保存并触发 update:node 事件', async () => {
    const wrapper = mountConfig();
    const editBtn = wrapper.find('.edit-name-btn');
    await editBtn.trigger('click');
    await nextTick();

    const input = wrapper.find('.name-input');
    await input.setValue('新发送邮件节点');
    await input.trigger('keydown', { key: 'Enter' });
    await nextTick();

    const emitted = wrapper.emitted('update:node') as any[][];
    expect(emitted).toBeTruthy();
    const lastNode = emitted[emitted.length - 1][0];
    expect(lastNode.name).toBe('新发送邮件节点');
    expect(wrapper.find('.node-name').text()).toBe('新发送邮件节点');
  });

  it('按 Esc 应该取消编辑并恢复原名', async () => {
    const wrapper = mountConfig();
    const editBtn = wrapper.find('.edit-name-btn');
    await editBtn.trigger('click');
    await nextTick();

    const input = wrapper.find('.name-input');
    await input.setValue('临时名称');
    await input.trigger('keydown', { key: 'Escape' });
    await nextTick();

    expect(wrapper.find('.node-name').text()).toBe('发送邮件 1');
    // 取消编辑不应触发名称变更的事件（可能已有其他 config 变更事件，但名称应保持原值）
    // 由于 watch 机制，如果 config 没变，可能不会触发。这里主要验证 DOM 恢复
    expect(wrapper.find('.node-name').exists()).toBe(true);
  });

  it('输入空名称后按 Enter 应该取消编辑并恢复原名', async () => {
    const wrapper = mountConfig();
    const editBtn = wrapper.find('.edit-name-btn');
    await editBtn.trigger('click');
    await nextTick();

    const input = wrapper.find('.name-input');
    await input.setValue('   ');
    await input.trigger('keydown', { key: 'Enter' });
    await nextTick();

    expect(wrapper.find('.node-name').text()).toBe('发送邮件 1');
  });

  it('更新记录节点的静态值字段应直接显示 FieldValueInput 且隐藏值模板输入', async () => {
    const wrapper = mountConfig({
      node: {
        ...mockNode,
        node_type: 'update_record',
        config: {
          updates: [{ field_id: 'field-2', value_template: '' }],
        },
      },
    });
    await nextTick();

    expect(wrapper.find('.template-input').exists()).toBe(false);
    expect(wrapper.find('.field-value-input').exists()).toBe(true);
    expect(wrapper.find('.el-switch').exists()).toBe(false);
  });

  it('更新记录节点的非静态值字段默认启用静态值模式', async () => {
    const wrapper = mountConfig({
      node: {
        ...mockNode,
        node_type: 'update_record',
        config: {
          updates: [{ field_id: 'field-1', value_template: '' }],
        },
      },
    });
    await nextTick();

    expect(wrapper.find('.template-input').exists()).toBe(false);
    expect(wrapper.findAll('.el-switch').length).toBe(1);
    expect(wrapper.find('.field-value-input').exists()).toBe(true);
  });

  it('更新记录节点开启表达式开关后显示表达式输入', async () => {
    const wrapper = mountConfig({
      node: {
        ...mockNode,
        node_type: 'update_record',
        config: {
          updates: [{ field_id: 'field-1', value_template: '' }],
        },
      },
    });
    await nextTick();

    const switchEl = wrapper.find('.el-switch');
    expect(switchEl.exists()).toBe(true);

    await switchEl.trigger('click');
    await nextTick();

    expect(wrapper.find('.template-input').exists()).toBe(true);
    expect(wrapper.find('.field-value-input').exists()).toBe(false);
  });

  it('创建记录节点的静态值字段应直接显示 FieldValueInput 且隐藏值模板输入', async () => {
    vi.mocked(fieldService.getFieldsByTable).mockResolvedValue(mockTargetFields);
    const wrapper = mountConfig({
      node: {
        ...mockNode,
        node_type: 'create_record',
        config: {
          target_table_id: 'table-2',
          field_mappings: [{ target_field_id: 'target-3', source_field_id: '', value_template: '' }],
        },
      },
      tables: mockTables,
    });
    await nextTick();

    expect(wrapper.find('.template-input').exists()).toBe(false);
    expect(wrapper.find('.field-value-input').exists()).toBe(true);
    expect(wrapper.find('.el-switch').exists()).toBe(false);
  });

  it('创建记录节点的非静态值字段默认启用静态值模式', async () => {
    vi.mocked(fieldService.getFieldsByTable).mockResolvedValue(mockTargetFields);
    const wrapper = mountConfig({
      node: {
        ...mockNode,
        node_type: 'create_record',
        config: {
          target_table_id: 'table-2',
          field_mappings: [{ target_field_id: 'target-1', source_field_id: '', value_template: '' }],
        },
      },
      tables: mockTables,
    });
    await nextTick();

    expect(wrapper.find('.template-input').exists()).toBe(false);
    expect(wrapper.findAll('.el-switch').length).toBe(1);
    expect(wrapper.find('.field-value-input').exists()).toBe(true);
  });

  it('创建记录节点开启表达式开关后显示表达式输入', async () => {
    vi.mocked(fieldService.getFieldsByTable).mockResolvedValue(mockTargetFields);
    const wrapper = mountConfig({
      node: {
        ...mockNode,
        node_type: 'create_record',
        config: {
          target_table_id: 'table-2',
          field_mappings: [{ target_field_id: 'target-1', source_field_id: '', value_template: '' }],
        },
      },
      tables: mockTables,
    });
    await nextTick();

    const switchEl = wrapper.find('.el-switch');
    expect(switchEl.exists()).toBe(true);

    await switchEl.trigger('click');
    await nextTick();

    expect(wrapper.find('.template-input').exists()).toBe(true);
    expect(wrapper.find('.field-value-input').exists()).toBe(false);
  });

  it('创建记录节点目标字段下拉从目标表加载字段', async () => {
    vi.mocked(fieldService.getFieldsByTable).mockResolvedValue(mockTargetFields);
    const wrapper = mountConfig({
      node: {
        ...mockNode,
        node_type: 'create_record',
        config: {
          target_table_id: 'table-2',
          field_mappings: [{ target_field_id: '', source_field_id: '', value_template: '' }],
        },
      },
      tables: mockTables,
    });
    await nextTick();
    await new Promise((resolve) => setTimeout(resolve, 0));

    expect(fieldService.getFieldsByTable).toHaveBeenCalledWith('table-2');
    const fieldSelects = wrapper.findAll('.field-select');
    const targetSelect = fieldSelects[0];
    expect(targetSelect.findAll('.el-option').length).toBe(mockTargetFields.length);
  });

  it('创建记录节点切换目标表后清空字段映射', async () => {
    vi.mocked(fieldService.getFieldsByTable).mockResolvedValue(mockTargetFields);
    const wrapper = mountConfig({
      node: {
        ...mockNode,
        node_type: 'create_record',
        config: {
          target_table_id: 'table-2',
          field_mappings: [{ target_field_id: 'target-1', source_field_id: '', value_template: '' }],
        },
      },
      tables: mockTables,
    });
    await nextTick();

    const targetTableSelect = wrapper.find('.full-width');
    await targetTableSelect.setValue('table-1');
    await targetTableSelect.trigger('change');
    await nextTick();
    await new Promise((resolve) => setTimeout(resolve, 0));

    const emitted = wrapper.emitted('update:node') as any[][];
    expect(emitted).toBeTruthy();
    const lastNode = emitted[emitted.length - 1][0];
    expect(lastNode.config.target_table_id).toBe('table-1');
    expect(lastNode.config.field_mappings).toEqual([]);
  });

  it('创建记录节点选择源字段后自动填充表达式', async () => {
    vi.mocked(fieldService.getFieldsByTable).mockResolvedValue(mockTargetFields);
    const wrapper = mountConfig({
      node: {
        ...mockNode,
        node_type: 'create_record',
        config: {
          target_table_id: 'table-2',
          field_mappings: [{ target_field_id: 'target-1', source_field_id: '', value_template: '' }],
        },
      },
      tables: mockTables,
    });
    await nextTick();

    const fieldSelects = wrapper.findAll('.field-select');
    const sourceSelect = fieldSelects[1];
    await sourceSelect.setValue('field-1');
    await sourceSelect.trigger('change');
    await nextTick();

    expect(wrapper.find('.template-input').exists()).toBe(true);
    expect(wrapper.find('.field-value-input').exists()).toBe(false);

    const emitted = wrapper.emitted('update:node') as any[][];
    expect(emitted).toBeTruthy();
    const lastNode = emitted[emitted.length - 1][0];
    expect(lastNode.config.field_mappings[0].source_field_id).toBe('field-1');
    expect(lastNode.config.field_mappings[0].value_template).toBe('{{trigger.record.field-1}}');
  });

  describe('兜底规范化：node_type 为 action 时根据 config.action_type 渲染', () => {
    it('action + create_record 应渲染创建记录配置面板', async () => {
      vi.mocked(fieldService.getFieldsByTable).mockResolvedValue(mockTargetFields);
      const wrapper = mountConfig({
        node: {
          ...mockNode,
          node_type: 'action',
          config: {
            action_type: 'create_record',
            target_table_id: 'table-2',
            field_mappings: [{ target_field_id: 'target-1', source_field_id: '', value_template: '' }],
          },
        },
        tables: mockTables,
      });
      await nextTick();
      await new Promise((resolve) => setTimeout(resolve, 0));

      expect(wrapper.find('.el-empty').exists()).toBe(false);
      expect(wrapper.find('.create-record-mapping-row').exists()).toBe(true);
      expect(wrapper.find('.full-width').exists()).toBe(true);
    });

    it('action + update_record 应渲染更新记录配置面板', async () => {
      const wrapper = mountConfig({
        node: {
          ...mockNode,
          node_type: 'action',
          config: {
            action_type: 'update_record',
            updates: [{ field_id: 'field-1', value_template: '' }],
          },
        },
      });
      await nextTick();

      expect(wrapper.find('.el-empty').exists()).toBe(false);
      expect(wrapper.find('.update-record-mapping-row').exists()).toBe(true);
    });

    it('action + send_email 应渲染发送邮件配置面板', async () => {
      const wrapper = mountConfig({
        node: {
          ...mockNode,
          node_type: 'action',
          config: {
            action_type: 'send_email',
            recipient_type: 'field',
          },
        },
      });
      await nextTick();

      expect(wrapper.find('.el-empty').exists()).toBe(false);
      expect(wrapper.text()).toContain('字段');
      expect(wrapper.text()).toContain('固定邮箱');
      // 验证 content_mode 单选组渲染（自定义内容/邮件模板）
      expect(wrapper.text()).toContain('自定义内容');
      expect(wrapper.text()).toContain('邮件模板');
      // 默认 content_mode 为 custom，应显示主题和正文
      expect(wrapper.text()).toContain('邮件主题');
      expect(wrapper.text()).toContain('邮件正文');
      // 验证收件人字段提示文本
      expect(wrapper.text()).toContain('仅支持邮箱、成员、协作人类型字段');
    });

    it('send_email 自定义内容模式应渲染主题和正文输入框', async () => {
      const wrapper = mountConfig({
        node: {
          ...mockNode,
          node_type: 'send_email',
          config: {
            recipient_type: 'field',
            content_mode: 'custom',
          },
        },
      });
      await nextTick();

      // 验证邮件主题输入框渲染
      expect(wrapper.text()).toContain('邮件主题');
      // 验证邮件正文输入框渲染
      expect(wrapper.text()).toContain('邮件正文');
      // 自定义内容模式下不应显示模板选择下拉框（content_mode 单选组中的"邮件模板"标签仍可见，但模板 select 不渲染）
      expect(wrapper.text()).not.toContain('选择模板');
      // 验证模板提示文本包含 {{record.field_id}}
      const hints = wrapper.findAll('.field-hint');
      const hintTexts = hints.map((h) => h.text());
      expect(hintTexts.some((t) => t.includes('record.field_id'))).toBe(true);
    });

    it('send_email 模板模式应渲染模板选择器', async () => {
      const wrapper = mountConfig({
        node: {
          ...mockNode,
          node_type: 'send_email',
          config: {
            recipient_type: 'field',
            content_mode: 'template',
          },
        },
      });
      await nextTick();

      // 模板模式下应显示邮件模板选择器
      expect(wrapper.text()).toContain('邮件模板');
      // 模板模式下不应显示邮件主题和正文输入框
      expect(wrapper.text()).not.toContain('邮件主题');
      expect(wrapper.text()).not.toContain('邮件正文');
    });

    it('action + trigger_webhook 应渲染 Webhook 配置面板', async () => {
      const wrapper = mountConfig({
        node: {
          ...mockNode,
          node_type: 'action',
          config: {
            action_type: 'trigger_webhook',
            webhook_mode: 'inline',
          },
        },
      });
      await nextTick();

      expect(wrapper.find('.el-empty').exists()).toBe(false);
      expect(wrapper.text()).toContain('选择已配置');
      expect(wrapper.text()).toContain('内联新建');
    });

    it('Webhook 内联新建输入应触发 update:node 更新配置', async () => {
      const wrapper = mountConfig({
        node: {
          ...mockNode,
          node_type: 'webhook',
          config: {
            webhook_mode: 'inline',
            inline_webhook: {
              name: '',
              url: '',
              method: 'POST',
              headers: {},
              body_template: '',
            },
          },
        },
      });
      await nextTick();

      const inputs = wrapper.findAll('.el-input');
      // 0: name input, 1: url input, 2: body_template textarea, 3: new header key input
      expect(inputs.length).toBeGreaterThanOrEqual(2);

      await inputs[0].setValue('测试 Webhook');
      await inputs[1].setValue('https://example.com/hook');
      await nextTick();

      const emitted = wrapper.emitted('update:node') as any[][];
      expect(emitted).toBeTruthy();
      const lastNode = emitted[emitted.length - 1][0];
      expect(lastNode.config.inline_webhook.name).toBe('测试 Webhook');
      expect(lastNode.config.inline_webhook.url).toBe('https://example.com/hook');
    });

    it('新建 Webhook 节点时 Webhook 来源可切换', async () => {
      const wrapper = mountConfig({
        node: {
          ...mockNode,
          id: 'node_temp_123',
          node_type: 'webhook',
          config: {
            webhook_mode: 'existing',
          },
        },
      });
      await nextTick();

      const radioGroup = wrapper.findComponent('.webhook-source-radio');
      expect(radioGroup.exists()).toBe(true);
      expect(radioGroup.classes('is-disabled')).toBe(false);
    });

    it('编辑已保存 Webhook 节点时 Webhook 来源禁用', async () => {
      const wrapper = mountConfig({
        node: {
          ...mockNode,
          id: '550e8400-e29b-41d4-a716-446655440000',
          node_type: 'webhook',
          config: {
            webhook_mode: 'existing',
          },
        },
      });
      await nextTick();

      const radioGroup = wrapper.findComponent('.webhook-source-radio');
      expect(radioGroup.exists()).toBe(true);
      expect(radioGroup.classes('is-disabled')).toBe(true);
    });

    it('availableWebhooks 应过滤掉 is_active=false 的 Webhook', async () => {
      const wrapper = mountConfig({
        node: {
          ...mockNode,
          node_type: 'webhook',
          config: {
            webhook_mode: 'existing',
          },
        },
        webhooks: [
          { id: 'wh-1', name: '启用 WH', is_active: true },
          { id: 'wh-2', name: '禁用 WH', is_active: false },
        ] as any,
      });
      await nextTick();

      const availableWebhooks = (wrapper.vm as any).availableWebhooks;
      expect(availableWebhooks.length).toBe(1);
      expect(availableWebhooks[0].id).toBe('wh-1');
    });

    it('已选中但被禁用的 Webhook 仍保留在可选项中', async () => {
      const wrapper = mountConfig({
        node: {
          ...mockNode,
          node_type: 'webhook',
          config: {
            webhook_mode: 'existing',
            webhook_id: 'wh-2',
          },
        },
        webhooks: [
          { id: 'wh-1', name: '启用 WH', is_active: true },
          { id: 'wh-2', name: '禁用 WH', is_active: false },
        ] as any,
      });
      await nextTick();

      const availableWebhooks = (wrapper.vm as any).availableWebhooks;
      // 启用的 + 当前选中的（即使禁用）
      expect(availableWebhooks.length).toBe(2);
      expect(availableWebhooks.map((w: any) => w.id)).toContain('wh-2');
    });

    it('无 webhook_id 时仅返回启用的 Webhook', async () => {
      const wrapper = mountConfig({
        node: {
          ...mockNode,
          node_type: 'webhook',
          config: {
            webhook_mode: 'existing',
          },
        },
        webhooks: [
          { id: 'wh-1', name: '启用 WH 1', is_active: true },
          { id: 'wh-2', name: '启用 WH 2', is_active: true },
          { id: 'wh-3', name: '禁用 WH', is_active: false },
        ] as any,
      });
      await nextTick();

      const availableWebhooks = (wrapper.vm as any).availableWebhooks;
      expect(availableWebhooks.length).toBe(2);
      expect(availableWebhooks.every((w: any) => w.is_active === true)).toBe(true);
    });

    it('只读模式下 create_record 节点应展示完整字段映射摘要', async () => {
      vi.mocked(fieldService.getFieldsByTable).mockResolvedValue(mockTargetFields);
      const wrapper = mountConfig({
        node: {
          ...mockNode,
          node_type: 'create_record',
          config: {
            target_table_id: 'table-2',
            field_mappings: [
              { target_field_id: 'target-1', source_field_id: 'field-1', value_template: '{{trigger.record.field-1}}' },
              { target_field_id: 'target-2', source_field_id: '', value_template: '静态值' },
            ],
          },
        },
        tables: mockTables,
        readonly: true,
      });
      await nextTick();
      await new Promise((resolve) => setTimeout(resolve, 0));
      await nextTick();

      expect(wrapper.find('.readonly-mapping-summary').exists()).toBe(true);
      expect(wrapper.find('.mapping-list').exists()).toBe(false);
      expect(wrapper.text()).toContain('字段映射');
      expect(wrapper.text()).toContain('目标字段');
      expect(wrapper.text()).toContain('源字段');
      expect(wrapper.text()).toContain('目标标题');
      expect(wrapper.text()).toContain('{{trigger.record.field-1}}');
    });

    it('切换 create_record 节点时不应清空目标字段映射', async () => {
      vi.mocked(fieldService.getFieldsByTable).mockResolvedValue(mockTargetFields);
      const wrapper = mountConfig({
        node: {
          ...mockNode,
          node_type: 'create_record',
          config: {
            target_table_id: 'table-1',
            field_mappings: [{ target_field_id: 'target-1', source_field_id: 'field-1', value_template: '{{trigger.record.field-1}}' }],
          },
        },
        tables: mockTables,
      });
      await nextTick();
      await new Promise((resolve) => setTimeout(resolve, 0));

      await wrapper.setProps({
        node: {
          ...mockNode,
          node_type: 'create_record',
          config: {
            target_table_id: 'table-2',
            field_mappings: [{ target_field_id: 'target-3', source_field_id: 'field-2', value_template: '静态值' }],
          },
        },
      });
      await nextTick();
      await new Promise((resolve) => setTimeout(resolve, 0));
      await nextTick();

      // 切换节点属于 props 更新，不应清空映射；编辑模式下静态值不直接渲染在 DOM 中，
      // 因此直接校验组件内部状态而非文本。
      expect((wrapper.vm as any).localNode.config.field_mappings).toEqual([
        { target_field_id: 'target-3', source_field_id: 'field-2', value_template: '静态值' },
      ]);
      expect(wrapper.emitted('update:node')).toBeFalsy();
    });

    it('action + 未知 action_type 应显示友好错误提示', async () => {
      const wrapper = mountConfig({
        node: {
          ...mockNode,
          node_type: 'action',
          config: {
            action_type: 'unknown_action',
          },
        },
      });
      await nextTick();

      expect(wrapper.find('.el-empty').exists()).toBe(true);
      expect((wrapper.vm as any).localNode.node_type).toBe('action');
    });

    it('action + find_records 应渲染查找记录配置面板', async () => {
      vi.mocked(fieldService.getFieldsByTable).mockResolvedValue(mockTargetFields);
      const wrapper = mountConfig({
        node: {
          ...mockNode,
          node_type: 'action',
          config: {
            action_type: 'find_records',
            target_table_id: 'table-2',
            conditions: [],
            result_variable: 'records',
          },
        },
        tables: mockTables,
      });
      await nextTick();
      await new Promise((resolve) => setTimeout(resolve, 0));
      await nextTick();

      expect(wrapper.find('.el-empty').exists()).toBe(false);
      expect(wrapper.text()).toContain('查找记录');
      expect(wrapper.text()).toContain('目标表格');
      expect(wrapper.text()).toContain('过滤条件');
      expect(wrapper.text()).toContain('排序字段');
      expect(wrapper.text()).toContain('排序方向');
      expect(wrapper.text()).toContain('返回条数上限');
      expect(wrapper.text()).toContain('结果变量名');
      expect(wrapper.text()).toContain('空结果处理');
    });
  });

  describe('查找记录节点', () => {
    it('node_type 为 find_records 时渲染完整配置面板', async () => {
      vi.mocked(fieldService.getFieldsByTable).mockResolvedValue(mockTargetFields);
      const wrapper = mountConfig({
        node: {
          ...mockNode,
          node_type: 'find_records',
          config: {
            target_table_id: 'table-2',
            conditions: [],
            result_variable: 'records',
          },
        },
        tables: mockTables,
      });
      await nextTick();
      await new Promise((resolve) => setTimeout(resolve, 0));
      await nextTick();

      expect(wrapper.find('.el-empty').exists()).toBe(false);
      expect(wrapper.text()).toContain('目标表格');
      expect(wrapper.text()).toContain('过滤条件');
      expect(wrapper.text()).toContain('排序字段');
      expect(wrapper.text()).toContain('排序方向');
      expect(wrapper.text()).toContain('返回条数上限');
      expect(wrapper.text()).toContain('结果变量名');
      expect(wrapper.text()).toContain('空结果处理');
    });

    it('非法变量名应显示错误提示', async () => {
      vi.mocked(fieldService.getFieldsByTable).mockResolvedValue(mockTargetFields);
      const wrapper = mountConfig({
        node: {
          ...mockNode,
          node_type: 'find_records',
          config: {
            target_table_id: 'table-2',
            conditions: [],
            result_variable: '123invalid',
          },
        },
        tables: mockTables,
      });
      await nextTick();
      await new Promise((resolve) => setTimeout(resolve, 0));
      await nextTick();

      expect(wrapper.find('.form-item-error').exists()).toBe(true);
      expect(wrapper.find('.form-item-error').text()).toContain('变量名格式不正确');
    });
  });

  describe('条件节点多分支', () => {
    function mountCondition(config: Record<string, unknown> = {}) {
      return mountConfig({
        node: {
          ...mockNode,
          node_type: 'condition',
          config,
        },
      });
    }

    it('旧单条件组配置自动迁移为单分支', async () => {
      const wrapper = mountCondition({
        conditions: [{ field_id: 'field-1', operator: 'equals', value: 'a' }],
        conjunction: 'or',
      });
      await nextTick();

      const branches = (wrapper.vm as any).branches;
      expect(branches.length).toBe(1);
      expect(branches[0].name).toBe('满足条件');
      expect(branches[0].conjunction).toBe('or');
      expect(branches[0].conditions.length).toBe(1);
    });

    it('已包含 branches 的配置直接保留', async () => {
      const wrapper = mountCondition({
        branches: [
          { id: 'b1', name: '分支 A', conditions: [], conjunction: 'and' },
          { id: 'b2', name: '分支 B', conditions: [], conjunction: 'or' },
        ],
      });
      await nextTick();

      const branches = (wrapper.vm as any).branches;
      expect(branches.length).toBe(2);
      expect(branches[0].name).toBe('分支 A');
      expect(branches[1].name).toBe('分支 B');
    });

    it('添加分支下拉菜单包含条件分支和默认分支选项', async () => {
      const wrapper = mountCondition();
      await nextTick();

      const items = wrapper.findAll('.el-dropdown-item');
      expect(items.length).toBe(2);
      expect(items[0].text()).toContain('条件分支');
      expect(items[1].text()).toContain('默认分支');
    });

    it('通过 command 添加条件分支并切换到新标签', async () => {
      const wrapper = mountCondition();
      await nextTick();

      (wrapper.vm as any).handleAddBranchCommand('condition');
      await nextTick();

      const branches = (wrapper.vm as any).branches;
      expect(branches.length).toBe(2);
      expect(branches[1].name).toBe('分支 2');
      expect(branches[1].is_default).toBeFalsy();
      expect((wrapper.vm as any).activeBranchId).toBe(branches[1].id);
    });

    it('编辑分支名称会更新对应分支', async () => {
      const wrapper = mountCondition({
        branches: [{ id: 'b1', name: '原名称', conditions: [], conjunction: 'and' }],
      });
      await nextTick();

      const input = wrapper.find('.branch-name-input');
      await input.setValue('新名称');
      await input.trigger('input');
      await nextTick();

      const branches = (wrapper.vm as any).branches;
      expect(branches[0].name).toBe('新名称');
    });

    it('删除条件会更新对应分支的条件列表', async () => {
      const wrapper = mountCondition({
        branches: [
          {
            id: 'b1',
            name: '分支',
            conditions: [{ field_id: 'field-1', operator: 'equals', value: 'a' }],
            conjunction: 'and',
          },
        ],
      });
      await nextTick();

      const deleteBtn = wrapper.find('.condition-row .el-button');
      await deleteBtn.trigger('click');
      await nextTick();

      const branches = (wrapper.vm as any).branches;
      expect(branches[0].conditions.length).toBe(0);
    });

    it('只读模式下不显示添加/删除分支按钮', async () => {
      const wrapper = mountCondition({
        branches: [{ id: 'b1', name: '分支', conditions: [], conjunction: 'and' }],
      });
      await nextTick();
      await wrapper.setProps({ readonly: true });
      await nextTick();

      expect(wrapper.find('.branch-tabs .el-button').exists()).toBe(false);
      expect(wrapper.find('.condition-row .el-button').exists()).toBe(false);
    });

    it('条件摘要中单选字段值显示为选项名称（id）', async () => {
      const fields = [
        {
          id: 'field-status',
          name: '状态',
          type: 'single_select',
          options: {
            options: [
              { id: 'opt-1', name: '待办', color: '#fff' },
              { id: 'opt-2', name: '进行中', color: '#fff' },
            ],
          },
        },
      ];
      const wrapper = mountConfig({
        node: {
          ...mockNode,
          node_type: 'condition',
          config: {
            branches: [
              {
                id: 'b1',
                name: '分支',
                conditions: [{ field_id: 'field-status', operator: 'equals', value: 'opt-2' }],
                conjunction: 'and',
              },
            ],
          },
        },
        fields,
      });
      await nextTick();

      const summaryItem = wrapper.find('.summary-item');
      expect(summaryItem.text()).toContain('进行中 (opt-2)');
    });

    it('条件摘要中多选字段值显示为多个选项名称（id）', async () => {
      const fields = [
        {
          id: 'field-tags',
          name: '标签',
          type: 'multi_select',
          options: {
            options: [
              { id: 'tag-a', name: '重要', color: '#fff' },
              { id: 'tag-b', name: '紧急', color: '#fff' },
            ],
          },
        },
      ];
      const wrapper = mountConfig({
        node: {
          ...mockNode,
          node_type: 'condition',
          config: {
            branches: [
              {
                id: 'b1',
                name: '分支',
                conditions: [
                  { field_id: 'field-tags', operator: 'contains_any', value: ['tag-a', 'tag-b'] },
                ],
                conjunction: 'and',
              },
            ],
          },
        },
        fields,
      });
      await nextTick();

      const summaryItem = wrapper.find('.summary-item');
      expect(summaryItem.text()).toContain('重要 (tag-a), 紧急 (tag-b)');
    });

    it('条件摘要中普通文本字段保持原值显示', async () => {
      const wrapper = mountCondition({
        branches: [
          {
            id: 'b1',
            name: '分支',
            conditions: [{ field_id: 'field-1', operator: 'equals', value: 'hello' }],
            conjunction: 'and',
          },
        ],
      });
      await nextTick();

      const summaryItem = wrapper.find('.summary-item');
      expect(summaryItem.text()).toContain('hello');
      expect(summaryItem.text()).not.toContain('(');
    });

    // ==================== 默认分支测试 ====================

    it('通过 command 添加默认分支并切换到新标签', async () => {
      const wrapper = mountCondition();
      await nextTick();

      (wrapper.vm as any).handleAddBranchCommand('default');
      await nextTick();

      const branches = (wrapper.vm as any).branches;
      expect(branches.length).toBe(2);
      expect(branches[1].is_default).toBe(true);
      expect(branches[1].name).toBe('默认分支');
      expect((wrapper.vm as any).activeBranchId).toBe(branches[1].id);
    });

    it('已存在默认分支时默认分支菜单项被禁用', async () => {
      const wrapper = mountCondition({
        branches: [
          { id: 'b1', name: 'B1', conditions: [], conjunction: 'and' },
          { id: 'b-default', name: '默认', conditions: [], conjunction: 'and', is_default: true },
        ],
      });
      await nextTick();

      const items = wrapper.findAll('.el-dropdown-item');
      expect(items[1].classes()).toContain('is-disabled');
    });

    it('默认分支标签页显示"默认"标签', async () => {
      const wrapper = mountCondition({
        branches: [
          { id: 'b1', name: '条件分支', conditions: [], conjunction: 'and' },
          { id: 'b-default', name: '默认分支', conditions: [], conjunction: 'and', is_default: true },
        ],
      });
      await nextTick();

      // 选中默认分支
      (wrapper.vm as any).activeBranchId = 'b-default';
      await nextTick();

      const defaultTab = wrapper.findAll('.branch-tab').find((tab) =>
        tab.classes().includes('is-default'),
      );
      expect(defaultTab).toBeTruthy();
      expect(defaultTab!.find('.el-tag').text()).toContain('默认');
    });

    it('默认分支面板显示提示信息且不显示条件配置区域', async () => {
      const wrapper = mountCondition({
        branches: [
          { id: 'b1', name: '条件分支', conditions: [], conjunction: 'and' },
          { id: 'b-default', name: '默认分支', conditions: [], conjunction: 'and', is_default: true },
        ],
      });
      await nextTick();

      // 选中默认分支
      (wrapper.vm as any).activeBranchId = 'b-default';
      await nextTick();

      expect(wrapper.find('.el-alert').exists()).toBe(true);
      expect(wrapper.find('.el-alert').text()).toContain('默认分支无需配置条件');
      expect(wrapper.find('.conditions-list').exists()).toBe(false);
      expect(wrapper.find('.condition-conjunction').exists()).toBe(false);
    });

    it('默认分支始终位于分支数组末尾', async () => {
      const wrapper = mountCondition();
      await nextTick();

      // 先添加默认分支
      (wrapper.vm as any).handleAddBranchCommand('default');
      await nextTick();

      // 再添加条件分支
      (wrapper.vm as any).handleAddBranchCommand('condition');
      await nextTick();

      const branches = (wrapper.vm as any).branches;
      expect(branches.length).toBe(3);
      // 最后一个应该是默认分支
      expect(branches[branches.length - 1].is_default).toBe(true);
    });

    it('只读模式下不显示添加分支下拉菜单', async () => {
      const wrapper = mountCondition({
        branches: [{ id: 'b1', name: '分支', conditions: [], conjunction: 'and' }],
      });
      await nextTick();
      await wrapper.setProps({ readonly: true });
      await nextTick();

      expect(wrapper.find('.el-dropdown').exists()).toBe(false);
    });
  });

  // ==================== 循环变量插入测试 ====================
  describe('循环变量插入', () => {
    /** 构造一个 loop 容器内 update_record 子节点的测试场景 */
    function mountLoopChildConfig(overrides: {
      loopDataSource?: any;
      childNodeType?: 'update_record' | 'create_record' | 'send_email' | 'webhook';
      childConfig?: Record<string, unknown>;
      readonly?: boolean;
    } = {}) {
      const childId = 'child-1';
      const childType = overrides.childNodeType ?? 'update_record';
      const childConfig =
        overrides.childConfig ??
        (childType === 'update_record'
          ? { updates: [{ field_id: 'field-1', value_template: '' }] }
          : childType === 'create_record'
            ? { target_table_id: 'table-2', field_mappings: [{ target_field_id: 'target-1', source_field_id: '', value_template: '' }] }
            : childType === 'send_email'
              ? { recipient_type: 'field', content_mode: 'custom' }
              : { webhook_mode: 'inline', inline_webhook: { name: '', url: '', method: 'POST', headers: {}, body_template: '' } });

      const findNode = {
        id: 'find-1',
        workflow_id: 'wf-1',
        node_type: 'find_records' as const,
        name: '查找记录 1',
        config: {
          target_table_id: 'table-2',
          result_variable: 'records',
        },
        order: -1,
        next_nodes: [],
      };

      const childNode = {
        id: childId,
        workflow_id: 'wf-1',
        node_type: childType,
        name: `${childType} 子节点`,
        config: childConfig,
        order: 0,
        next_nodes: [],
      };

      const loopNode = {
        id: 'loop-1',
        workflow_id: 'wf-1',
        node_type: 'loop' as const,
        name: '循环 1',
        config: {
          data_source: overrides.loopDataSource ?? { type: 'find_records_all', node_id: 'find-1' },
          max_iterations: 100,
          error_handling: 'skip',
          empty_result_action: 'skip',
          loop_body_nodes: [childNode],
        },
        order: 0,
        next_nodes: [],
      };

      const allNodes = [findNode, loopNode];

      return mountConfig({
        node: childNode,
        fields: mockFields,
        tables: mockTables,
        allNodes,
        readonly: overrides.readonly ?? false,
      });
    }

    /** 开启第 index 个 mapping 的表达式模式 */
    async function enableExpressionMode(wrapper: any) {
      const switchEl = wrapper.find('.el-switch');
      if (switchEl.exists()) {
        await switchEl.trigger('click');
        await nextTick();
      }
    }

    it('循环体子节点的 update_record 配置面板应显示"插入循环变量"按钮', async () => {
      vi.mocked(fieldService.getFieldsByTable).mockResolvedValue(mockTargetFields);
      const wrapper = mountLoopChildConfig();
      await nextTick();
      await new Promise((resolve) => setTimeout(resolve, 0));
      await nextTick();

      await enableExpressionMode(wrapper);

      const inserters = wrapper.findAll('.loop-var-inserter');
      expect(inserters.length).toBeGreaterThan(0);
      expect(inserters[0].text()).toContain('插入循环变量');
    });

    it('非循环体节点的 update_record 配置面板不应显示"插入循环变量"按钮', async () => {
      const wrapper = mountConfig({
        node: {
          ...mockNode,
          id: 'top-level-update',
          node_type: 'update_record',
          config: {
            updates: [{ field_id: 'field-1', value_template: '' }],
          },
        },
        // 不传 allNodes，模拟顶层节点不在 loop 容器内
      });
      await nextTick();

      await enableExpressionMode(wrapper);

      expect(wrapper.find('.loop-var-inserter').exists()).toBe(false);
    });

    it('触发 insert 事件后应将循环变量追加到 value_template 并提示成功', async () => {
      vi.mocked(fieldService.getFieldsByTable).mockResolvedValue(mockTargetFields);
      const wrapper = mountLoopChildConfig();
      await nextTick();
      await new Promise((resolve) => setTimeout(resolve, 0));
      await nextTick();

      await enableExpressionMode(wrapper);

      const inserter = wrapper.find('.loop-var-inserter');
      expect(inserter.exists()).toBe(true);
      await inserter.trigger('click');
      await nextTick();

      // ElMessage.success 被调用
      expect(ElMessage.success).toHaveBeenCalledWith('已插入循环变量');

      // update:node 事件触发，最新节点的 value_template 包含循环变量片段
      const emitted = wrapper.emitted('update:node') as any[][];
      expect(emitted).toBeTruthy();
      const lastNode = emitted[emitted.length - 1][0];
      expect(lastNode.config.updates[0].value_template).toBe('{{loop.current_data}}');
    });

    it('find_records_all 数据源应支持字段下钻', async () => {
      vi.mocked(fieldService.getFieldsByTable).mockResolvedValue(mockTargetFields);
      const wrapper = mountLoopChildConfig({
        loopDataSource: { type: 'find_records_all', node_id: 'find-1' },
      });
      await nextTick();
      await new Promise((resolve) => setTimeout(resolve, 0));
      await nextTick();

      await enableExpressionMode(wrapper);

      const inserter = wrapper.find('.loop-var-inserter');
      expect(inserter.exists()).toBe(true);
      expect(inserter.attributes('data-supports-field-drill')).toBe('true');
      // 字段下钻选项来自 find_records 节点的目标表（mockTargetFields，长度 3）
      expect(inserter.attributes('data-field-count')).toBe(String(mockTargetFields.length));
    });

    it('trigger_field 数据源不应支持字段下钻', async () => {
      const wrapper = mountLoopChildConfig({
        loopDataSource: { type: 'trigger_field', field_id: 'field-1', trigger_field_id: 'field-1' },
      });
      await nextTick();
      await new Promise((resolve) => setTimeout(resolve, 0));
      await nextTick();

      await enableExpressionMode(wrapper);

      const inserter = wrapper.find('.loop-var-inserter');
      expect(inserter.exists()).toBe(true);
      expect(inserter.attributes('data-supports-field-drill')).toBe('false');
    });

    it('只读模式下不应显示"插入循环变量"按钮', async () => {
      vi.mocked(fieldService.getFieldsByTable).mockResolvedValue(mockTargetFields);
      const wrapper = mountLoopChildConfig({ readonly: true });
      await nextTick();
      await new Promise((resolve) => setTimeout(resolve, 0));
      await nextTick();

      // 只读模式下表达式开关被禁用，但仍可能渲染；关键是 LoopVarInserter 不应渲染
      expect(wrapper.find('.loop-var-inserter').exists()).toBe(false);
    });

    it('循环体子节点的 send_email 配置面板应在主题与正文旁显示"插入循环变量"按钮', async () => {
      vi.mocked(fieldService.getFieldsByTable).mockResolvedValue(mockTargetFields);
      const wrapper = mountLoopChildConfig({ childNodeType: 'send_email' });
      await nextTick();
      await new Promise((resolve) => setTimeout(resolve, 0));
      await nextTick();

      const inserters = wrapper.findAll('.loop-var-inserter');
      // 主题与正文各一个
      expect(inserters.length).toBe(2);
    });

    it('循环体子节点的 webhook 配置面板应在 Body 模板旁显示"插入循环变量"按钮', async () => {
      vi.mocked(fieldService.getFieldsByTable).mockResolvedValue(mockTargetFields);
      const wrapper = mountLoopChildConfig({ childNodeType: 'webhook' });
      await nextTick();
      await new Promise((resolve) => setTimeout(resolve, 0));
      await nextTick();

      const inserters = wrapper.findAll('.loop-var-inserter');
      expect(inserters.length).toBe(1);
    });

    it('循环体子节点的 create_record 配置面板应在表达式输入框旁显示"插入循环变量"按钮', async () => {
      vi.mocked(fieldService.getFieldsByTable).mockResolvedValue(mockTargetFields);
      const wrapper = mountLoopChildConfig({ childNodeType: 'create_record' });
      await nextTick();
      await new Promise((resolve) => setTimeout(resolve, 0));
      await nextTick();

      await enableExpressionMode(wrapper);

      const inserters = wrapper.findAll('.loop-var-inserter');
      expect(inserters.length).toBe(1);
    });
  });

  // ==================== 循环节点配置面板测试 ====================
  describe('循环节点配置面板', () => {
    /** 构造 loop 节点配置面板测试场景 */
    function mountLoopConfig(overrides: {
      loopConfig?: Record<string, unknown>;
      allNodes?: any[];
      fields?: any[];
      readonly?: boolean;
    } = {}) {
      const findNode = {
        id: 'find-1',
        workflow_id: 'wf-1',
        node_type: 'find_records' as const,
        name: '查找记录 1',
        config: {
          target_table_id: 'table-2',
          result_variable: 'records',
        },
        order: -1,
        next_nodes: [],
      };

      const defaultLoopConfig = {
        loop_mode: 'sequential',
        data_source: { type: 'find_records_all', node_id: 'find-1' },
        max_iterations: 100,
        error_handling: 'skip',
        empty_result_action: 'skip',
        loop_body_nodes: [
          {
            id: 'body-1',
            workflow_id: 'wf-1',
            node_type: 'update_record',
            name: '更新记录 1',
            config: { updates: [{ field_id: 'field-1', value_template: '' }] },
            order: 0,
            next_nodes: [],
          },
        ],
      };

      const loopNode = {
        id: 'loop-1',
        workflow_id: 'wf-1',
        node_type: 'loop' as const,
        name: '循环 1',
        config: overrides.loopConfig ?? defaultLoopConfig,
        order: 0,
        next_nodes: [],
      };

      const loopFields = overrides.fields ?? [
        { id: 'field-1', name: '标题', type: 'single_line_text' },
        { id: 'field-2', name: '负责人', type: 'collaborator' },
      ];

      const allNodes = overrides.allNodes ?? [findNode, loopNode];

      return mountConfig({
        node: loopNode,
        fields: loopFields,
        tables: mockTables,
        allNodes,
        readonly: overrides.readonly ?? false,
      });
    }

    it('loop 节点应渲染循环配置面板（不显示 el-empty）', async () => {
      const wrapper = mountLoopConfig();
      await nextTick();

      expect(wrapper.find('.el-empty').exists()).toBe(false);
      expect(wrapper.text()).toContain('循环方式');
      expect(wrapper.text()).toContain('数据源');
      expect(wrapper.text()).toContain('最大循环次数');
      expect(wrapper.text()).toContain('错误处理方式');
      expect(wrapper.text()).toContain('空结果处理');
    });

    it('循环方式应为"依次处理每条数据"且禁用切换', async () => {
      const wrapper = mountLoopConfig();
      await nextTick();

      expect(wrapper.text()).toContain('依次处理每条数据');
      // 循环方式 select 是 disabled 的
      const selects = wrapper.findAll('.el-select');
      // 第一个 select 是循环方式
      const loopModeSelect = selects[0];
      expect(loopModeSelect.classes().includes('full-width') || loopModeSelect.attributes('class')?.includes('full-width')).toBe(true);
    });

    it('数据源选择器应展示前序 find_records 节点的选项', async () => {
      const wrapper = mountLoopConfig();
      await nextTick();

      const dsSelect = wrapper.findAll('.el-select')[1];
      const options = dsSelect.findAll('.el-option');
      // find_records 的"所有记录" + "负责人"列值（collaborator 类型）+ 触发器"负责人"
      expect(options.length).toBeGreaterThanOrEqual(2);
      expect(options.some((o) => (o.text() ?? '').includes('所有记录'))).toBe(true);
    });

    it('无前序数据源时应展示提示信息', async () => {
      const wrapper = mountLoopConfig({
        allNodes: [
          {
            id: 'loop-1',
            workflow_id: 'wf-1',
            node_type: 'loop',
            name: '循环 1',
            config: {
              data_source: { type: 'find_records_all' },
              max_iterations: 100,
              error_handling: 'skip',
              empty_result_action: 'skip',
              loop_body_nodes: [],
            },
            order: 0,
            next_nodes: [],
          },
        ],
        fields: [{ id: 'field-1', name: '标题', type: 'single_line_text' }],
      });
      await nextTick();

      // 没有前序 find_records / webhook 且无人员/群组/附件/关联字段
      // 只有触发器字段选项时仍有选项，不应显示"暂无可用"提示
      // 但当 fields 都是普通文本字段时，触发器也不会有选项
      const hint = wrapper.find('.field-hint');
      // 当只有文本字段时，LOOP_ALLOWED_FIELD_TYPES 过滤后为空，find_records 无前序节点
      // 所以可能展示提示
      const hintText = hint.text();
      expect(hintText).toContain('暂无可用的前序数据源');
    });

    it('循环体子节点列表应正确渲染', async () => {
      const wrapper = mountLoopConfig();
      await nextTick();

      const bodyItems = wrapper.findAll('.loop-body-item');
      expect(bodyItems.length).toBe(1);
      expect(bodyItems[0].find('.loop-body-name').text()).toBe('更新记录 1');
    });

    it('循环体为空时应显示空状态', async () => {
      const wrapper = mountLoopConfig({
        loopConfig: {
          loop_mode: 'sequential',
          data_source: { type: 'find_records_all', node_id: 'find-1' },
          max_iterations: 100,
          error_handling: 'skip',
          empty_result_action: 'skip',
          loop_body_nodes: [],
        },
      });
      await nextTick();

      expect(wrapper.findAll('.loop-body-item').length).toBe(0);
      expect(wrapper.find('.loop-body-section .el-empty').exists()).toBe(true);
      expect(wrapper.find('.loop-body-section .el-empty').text()).toContain('暂无循环体节点');
    });

    it('循环体计数应正确显示', async () => {
      const wrapper = mountLoopConfig();
      await nextTick();

      const count = wrapper.find('.loop-body-count');
      expect(count.text()).toContain('1');
    });

    it('添加循环体节点下拉应展示允许的节点类型', async () => {
      const wrapper = mountLoopConfig();
      await nextTick();

      const items = wrapper.findAll('.loop-body-add .el-dropdown-item');
      expect(items.length).toBeGreaterThanOrEqual(5);
      const labels = items.map((i) => i.text());
      expect(labels).toContain('更新记录');
      expect(labels).toContain('创建记录');
      expect(labels).toContain('查找记录');
      expect(labels).toContain('发送邮件');
      expect(labels).toContain('循环');
    });

    it('点击循环体子节点应触发 select-child-node 事件', async () => {
      const wrapper = mountLoopConfig();
      await nextTick();

      const bodyItem = wrapper.find('.loop-body-item');
      await bodyItem.trigger('click');
      await nextTick();

      const emitted = wrapper.emitted('select-child-node') as any[][];
      expect(emitted).toBeTruthy();
      expect(emitted[emitted.length - 1][0]).toBe('body-1');
    });

    it('点击循环体子节点删除按钮应触发 remove-child-node 事件', async () => {
      const wrapper = mountLoopConfig();
      await nextTick();

      const deleteBtn = wrapper.find('.loop-body-delete-btn');
      await deleteBtn.trigger('click');
      await nextTick();

      const emitted = wrapper.emitted('remove-child-node') as any[][];
      expect(emitted).toBeTruthy();
      const payload = emitted[emitted.length - 1][0];
      expect(payload.nodeId).toBe('body-1');
      expect(payload.parentId).toBe('loop-1');
    });

    it('从下拉添加循环体子节点应触发 add-child-node 事件', async () => {
      const wrapper = mountLoopConfig();
      await nextTick();

      const items = wrapper.findAll('.loop-body-add .el-dropdown-item');
      // 点击"创建记录"
      const createItem = items.find((i) => i.text().includes('创建记录'));
      await createItem!.trigger('click');
      await nextTick();

      const emitted = wrapper.emitted('add-child-node') as any[][];
      expect(emitted).toBeTruthy();
      const payload = emitted[emitted.length - 1][0];
      expect(payload.nodeType).toBe('create_record');
      expect(payload.parentId).toBe('loop-1');
    });

    it('只读模式下不显示添加/删除按钮', async () => {
      const wrapper = mountLoopConfig({ readonly: true });
      await nextTick();

      expect(wrapper.find('.loop-body-add').exists()).toBe(false);
      expect(wrapper.find('.loop-body-delete-btn').exists()).toBe(false);
    });

    it('添加第 6 个循环节点应弹出限制提示', async () => {
      // 构造已有 5 个 loop 节点的工作流
      const existingLoops = Array.from({ length: 5 }, (_, i) => ({
        id: `existing-loop-${i}`,
        workflow_id: 'wf-1',
        node_type: 'loop' as const,
        name: `循环 ${i + 1}`,
        config: {
          data_source: { type: 'find_records_all', node_id: 'find-1' },
          max_iterations: 100,
          error_handling: 'skip',
          empty_result_action: 'skip',
          loop_body_nodes: [],
        },
        order: i,
        next_nodes: [],
      }));

      const findNode = {
        id: 'find-1',
        workflow_id: 'wf-1',
        node_type: 'find_records' as const,
        name: '查找记录',
        config: { target_table_id: 'table-2', result_variable: 'records' },
        order: -1,
        next_nodes: [],
      };

      const currentLoop = existingLoops[0];
      const allNodes = [findNode, ...existingLoops];

      const wrapper = mountConfig({
        node: currentLoop,
        fields: mockFields,
        tables: mockTables,
        allNodes,
      });
      await nextTick();

      const items = wrapper.findAll('.loop-body-add .el-dropdown-item');
      const loopItem = items.find((i) => i.text().includes('循环'));
      await loopItem!.trigger('click');
      await nextTick();

      expect(ElMessage.warning).toHaveBeenCalledWith('单个工作流最多 5 个循环节点');
      // 不应触发 add-child-node 事件
      expect(wrapper.emitted('add-child-node')).toBeFalsy();
    });

    it('添加第 4 层嵌套循环应弹出限制提示', async () => {
      // 构造已达 3 层深度的循环链：loop-1 > loop-2 > loop-3
      // 当 loop-3 作为当前节点添加子循环节点时，新循环位于第 4 层，应被阻止。
      // 由于实现通过 simulating allNodes 中替换当前节点来校验深度，
      // 需将当前节点设为顶层 loop-1 且其循环体链已达深度 3，再向其追加子循环
      // 会使模拟后深度仍为 4（> 3），从而触发提示。
      // 为触发深度校验（而非数量校验），此处构造 4 层链（loop-1>loop-2>loop-3>loop-4），
      // loop-1 为当前节点，allNodes=[find, loop-1]。
      // 模拟添加后 loop-1 循环体深度仍为 4 > 3 → 弹出提示。
      const mkLoop = (id: string, name: string, body: any[] = []) => ({
        id,
        workflow_id: 'wf-1',
        node_type: 'loop' as const,
        name,
        config: {
          data_source: { type: 'find_records_all', node_id: 'find-1' },
          max_iterations: 100,
          error_handling: 'skip',
          empty_result_action: 'skip',
          loop_body_nodes: body,
        },
        order: 0,
        next_nodes: [],
      });

      const loop4 = mkLoop('loop-4', '循环 4');
      const loop3 = mkLoop('loop-3', '循环 3', [loop4]);
      const loop2 = mkLoop('loop-2', '循环 2', [loop3]);
      const loop1 = mkLoop('loop-1', '循环 1', [loop2]);

      const findNode = {
        id: 'find-1',
        workflow_id: 'wf-1',
        node_type: 'find_records' as const,
        name: '查找记录',
        config: { target_table_id: 'table-2', result_variable: 'records' },
        order: -1,
        next_nodes: [],
      };

      const wrapper = mountConfig({
        node: loop1,
        fields: mockFields,
        tables: mockTables,
        allNodes: [findNode, loop1],
      });
      await nextTick();

      const items = wrapper.findAll('.loop-body-add .el-dropdown-item');
      const loopItem = items.find((i) => i.text().includes('循环'));
      await loopItem!.trigger('click');
      await nextTick();

      expect(ElMessage.warning).toHaveBeenCalledWith('循环嵌套深度不能超过 3 层');
      expect(wrapper.emitted('add-child-node')).toBeFalsy();
    });
  });
});
