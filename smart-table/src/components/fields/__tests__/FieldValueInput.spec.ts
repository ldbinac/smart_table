import { describe, it, expect, vi } from 'vitest';
import { mount } from '@vue/test-utils';
import { ElSwitch, ElSelect } from 'element-plus';
import FieldValueInput from '../FieldValueInput.vue';

vi.mock('@/types/fields', async () => {
  const actual = await vi.importActual<typeof import('@/types/fields')>('@/types/fields');
  return {
    ...actual,
  };
});

describe('FieldValueInput', () => {
  function mountFieldValueInput(field: any, modelValue: unknown = '') {
    return mount(FieldValueInput, {
      props: {
        field,
        modelValue,
        disabled: false,
      },
    });
  }

  it('进度字段应渲染 ElSlider', () => {
    const wrapper = mountFieldValueInput({
      id: 'field-progress',
      name: '完成度',
      type: 'progress',
      options: { min: 0, max: 100 },
    }, 30);

    const slider = wrapper.find('.el-slider');
    expect(slider.exists()).toBe(true);
  });

  it('复选框字段应将字符串 "true" 解析为选中', () => {
    const wrapper = mountFieldValueInput({
      id: 'field-checkbox',
      name: '是否通过',
      type: 'checkbox',
    }, 'true');

    const switchInput = wrapper.findComponent(ElSwitch);
    expect(switchInput.exists()).toBe(true);
    expect(switchInput.vm.modelValue).toBe(true);
  });

  it('复选框字段应将字符串 "false" 解析为未选中', () => {
    const wrapper = mountFieldValueInput({
      id: 'field-checkbox',
      name: '是否通过',
      type: 'checkbox',
    }, 'false');

    const switchInput = wrapper.findComponent(ElSwitch);
    expect(switchInput.exists()).toBe(true);
    expect(switchInput.vm.modelValue).toBe(false);
  });

  it('多选字段应将逗号分隔字符串解析为数组', () => {
    const wrapper = mountFieldValueInput({
      id: 'field-multi',
      name: '标签',
      type: 'multi_select',
      options: {
        choices: [
          { id: 'a', name: 'A' },
          { id: 'b', name: 'B' },
        ],
      },
    }, 'a,b');

    const select = wrapper.findComponent(ElSelect);
    expect(select.exists()).toBe(true);
    expect(select.vm.modelValue).toEqual(['a', 'b']);
  });
});
