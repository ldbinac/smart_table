/**
 * workflowNodeType 测试 - script 节点注册
 */
import { describe, it, expect } from 'vitest';
import {
  ADDABLE_NODE_TYPES,
  LOOP_BODY_ALLOWED_NODE_TYPES,
  NODE_TYPE_ICON_MAP,
  NODE_TYPE_LABEL_MAP,
  getNodeLabel,
  getNodeIcon,
} from '@/utils/workflowNodeType';
import { Cpu } from '@element-plus/icons-vue';

describe('script 节点注册', () => {
  it('ADDABLE_NODE_TYPES 包含 script', () => {
    expect(ADDABLE_NODE_TYPES.some((n) => n.type === 'script')).toBe(true);
  });

  it('LOOP_BODY_ALLOWED_NODE_TYPES 包含 script', () => {
    expect(LOOP_BODY_ALLOWED_NODE_TYPES.some((n) => n.type === 'script')).toBe(true);
  });

  it('ADDABLE_NODE_TYPES 中 script 的 label 为"自定义脚本"', () => {
    const scriptNode = ADDABLE_NODE_TYPES.find((n) => n.type === 'script');
    expect(scriptNode).toBeDefined();
    expect(scriptNode!.label).toBe('自定义脚本');
  });

  it('LOOP_BODY_ALLOWED_NODE_TYPES 中 script 的 label 为"自定义脚本"', () => {
    const scriptNode = LOOP_BODY_ALLOWED_NODE_TYPES.find((n) => n.type === 'script');
    expect(scriptNode).toBeDefined();
    expect(scriptNode!.label).toBe('自定义脚本');
  });

  it('NODE_TYPE_ICON_MAP script 使用 Cpu 图标', () => {
    expect(NODE_TYPE_ICON_MAP.script).toBe(Cpu);
  });

  it('NODE_TYPE_LABEL_MAP script 标签为"自定义脚本"', () => {
    expect(NODE_TYPE_LABEL_MAP.script).toBe('自定义脚本');
  });

  it('getNodeLabel("script") 返回"自定义脚本"', () => {
    expect(getNodeLabel('script')).toBe('自定义脚本');
  });

  it('getNodeIcon("script") 返回 Cpu', () => {
    expect(getNodeIcon('script')).toBe(Cpu);
  });

  it('getNodeLabel 未知类型返回类型本身', () => {
    expect(getNodeLabel('unknown_type')).toBe('unknown_type');
  });

  it('getNodeIcon 未知类型返回兜底图标 CircleCheck', () => {
    // 未知类型兜底为 CircleCheck（与 NODE_TYPE_ICON_MAP 默认值一致）
    expect(getNodeIcon('unknown_type')).toBeTruthy();
  });
});
