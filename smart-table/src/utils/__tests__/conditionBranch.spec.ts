import { describe, it, expect } from 'vitest';
import {
  normalizeConditionConfig,
  addConditionBranch,
  addDefaultBranch,
  createDefaultBranch,
  hasDefaultBranch,
  getDefaultBranch,
  moveBranchToEnd,
  removeConditionBranch,
  updateConditionBranch,
  setConditionBranchTarget,
  getConditionNextNodeIds,
} from '../conditionBranch';
import type { ConditionNodeConfig } from '@/types/workflow';

describe('conditionBranch', () => {
  it('空配置迁移为默认单分支', () => {
    const result = normalizeConditionConfig({});
    expect(result.branches.length).toBe(1);
    expect(result.branches[0].name).toBe('满足条件');
    expect(result.branches[0].conditions).toEqual([]);
    expect(result.branches[0].conjunction).toBe('and');
  });

  it('旧配置迁移为单分支并保留条件', () => {
    const result = normalizeConditionConfig({
      conditions: [{ field_id: 'f1', operator: 'equals', value: 'a' }],
      conjunction: 'or',
    });
    expect(result.branches.length).toBe(1);
    expect(result.branches[0].conjunction).toBe('or');
    expect(result.branches[0].conditions).toEqual([
      { field_id: 'f1', operator: 'equals', value: 'a' },
    ]);
  });

  it('新 branches 配置直接保留', () => {
    const result = normalizeConditionConfig({
      branches: [
        { id: 'b1', name: 'B1', conditions: [], conjunction: 'and' },
      ],
    });
    expect(result.branches.length).toBe(1);
    expect(result.branches[0].id).toBe('b1');
  });

  it('过滤非法 branches 项', () => {
    const result = normalizeConditionConfig({
      branches: [{ id: 'b1', name: 'B1', conditions: [], conjunction: 'and' }, null, 123],
    });
    expect(result.branches.length).toBe(1);
  });

  it('添加分支返回新分支并更新配置', () => {
    const config = normalizeConditionConfig({});
    const { config: next, branch } = addConditionBranch(config);
    expect(next.branches.length).toBe(2);
    expect(branch.name).toBe('分支 2');
  });

  it('删除分支返回不含该分支的配置', () => {
    const config = normalizeConditionConfig({
      branches: [
        { id: 'b1', name: 'B1', conditions: [], conjunction: 'and' },
      ],
    });
    const next = removeConditionBranch(config, 'b1');
    expect(next.branches.length).toBe(0);
  });

  it('更新分支条件', () => {
    const config = normalizeConditionConfig({});
    const branchId = config.branches[0].id;
    const next = updateConditionBranch(config, branchId, (branch) => ({
      ...branch,
      name: '新名称',
    }));
    expect(next.branches[0].name).toBe('新名称');
  });

  it('设置分支目标节点', () => {
    const config = normalizeConditionConfig({});
    const branchId = config.branches[0].id;
    const next = setConditionBranchTarget(config, branchId, 'node-2');
    expect(next.branches[0].target_node_id).toBe('node-2');
  });

  it('getConditionNextNodeIds 返回已连线的目标 ID', () => {
    const config = {
      branches: [
        { id: 'b1', name: 'B1', conditions: [], conjunction: 'and', target_node_id: 'n2' },
        { id: 'b2', name: 'B2', conditions: [], conjunction: 'and' },
      ],
    };
    expect(getConditionNextNodeIds(config)).toEqual(['n2']);
  });

  // ==================== 默认分支测试 ====================

  it('createDefaultBranch 返回 is_default 为 true 且名称为"默认分支"', () => {
    const branch = createDefaultBranch();
    expect(branch.is_default).toBe(true);
    expect(branch.name).toBe('默认分支');
    expect(branch.conditions).toEqual([]);
    expect(branch.conjunction).toBe('and');
    expect(branch.target_node_id).toBeUndefined();
  });

  it('createDefaultBranch 支持自定义名称', () => {
    const branch = createDefaultBranch('兜底分支');
    expect(branch.is_default).toBe(true);
    expect(branch.name).toBe('兜底分支');
  });

  it('hasDefaultBranch 在含默认分支时返回 true', () => {
    const config = {
      branches: [
        { id: 'b1', name: 'B1', conditions: [], conjunction: 'and' },
        { id: 'b2', name: '默认', conditions: [], conjunction: 'and', is_default: true },
      ],
    };
    expect(hasDefaultBranch(config)).toBe(true);
  });

  it('hasDefaultBranch 在不含默认分支时返回 false', () => {
    const config = {
      branches: [
        { id: 'b1', name: 'B1', conditions: [], conjunction: 'and' },
      ],
    };
    expect(hasDefaultBranch(config)).toBe(false);
  });

  it('getDefaultBranch 返回默认分支', () => {
    const config = {
      branches: [
        { id: 'b1', name: 'B1', conditions: [], conjunction: 'and' },
        { id: 'b2', name: '默认', conditions: [], conjunction: 'and', is_default: true },
      ],
    };
    const result = getDefaultBranch(config);
    expect(result).toBeDefined();
    expect(result?.id).toBe('b2');
    expect(result?.is_default).toBe(true);
  });

  it('getDefaultBranch 无默认分支时返回 undefined', () => {
    const config = {
      branches: [
        { id: 'b1', name: 'B1', conditions: [], conjunction: 'and' },
      ],
    };
    expect(getDefaultBranch(config)).toBeUndefined();
  });

  it('addDefaultBranch 追加默认分支到末尾', () => {
    const config = normalizeConditionConfig({});
    const { config: next, branch } = addDefaultBranch(config);
    expect(next.branches.length).toBe(2);
    expect(branch.is_default).toBe(true);
    expect(next.branches[1].is_default).toBe(true);
    expect(next.branches[1].name).toBe('默认分支');
  });

  it('addDefaultBranch 已存在默认分支时返回现有分支不变', () => {
    const config: ConditionNodeConfig = {
      branches: [
        { id: 'b1', name: 'B1', conditions: [], conjunction: 'and' as const },
        { id: 'b-default', name: '已有默认', conditions: [], conjunction: 'and' as const, is_default: true },
      ],
    };
    const { config: next, branch } = addDefaultBranch(config);
    expect(next.branches.length).toBe(2);
    expect(branch.id).toBe('b-default');
    expect(branch.name).toBe('已有默认');
  });

  it('addConditionBranch 在存在默认分支时将新条件分支插入默认分支之前', () => {
    const config: ConditionNodeConfig = {
      branches: [
        { id: 'b1', name: 'B1', conditions: [], conjunction: 'and' as const },
        { id: 'b-default', name: '默认', conditions: [], conjunction: 'and' as const, is_default: true },
      ],
    };
    const { config: next } = addConditionBranch(config);
    expect(next.branches.length).toBe(3);
    expect(next.branches[1].name).toBe('分支 3');
    expect(next.branches[1].is_default).toBeFalsy();
    expect(next.branches[next.branches.length - 1].id).toBe('b-default');
    expect(next.branches[next.branches.length - 1].is_default).toBe(true);
  });

  it('moveBranchToEnd 将指定分支移到末尾', () => {
    const config: ConditionNodeConfig = {
      branches: [
        { id: 'b1', name: 'B1', conditions: [], conjunction: 'and' as const },
        { id: 'b2', name: 'B2', conditions: [], conjunction: 'and' as const },
        { id: 'b3', name: 'B3', conditions: [], conjunction: 'and' as const },
      ],
    };
    const next = moveBranchToEnd(config, 'b1');
    expect(next.branches[next.branches.length - 1].id).toBe('b1');
    expect(next.branches[0].id).toBe('b2');
  });

  it('moveBranchToEnd 指定分支已在末尾时不变化', () => {
    const config: ConditionNodeConfig = {
      branches: [
        { id: 'b1', name: 'B1', conditions: [], conjunction: 'and' as const },
        { id: 'b2', name: 'B2', conditions: [], conjunction: 'and' as const },
      ],
    };
    const next = moveBranchToEnd(config, 'b2');
    expect(next.branches.map((b) => b.id)).toEqual(['b1', 'b2']);
  });

  it('removeConditionBranch 删除非默认分支后默认分支仍在末尾', () => {
    const config: ConditionNodeConfig = {
      branches: [
        { id: 'b1', name: 'B1', conditions: [], conjunction: 'and' as const },
        { id: 'b2', name: 'B2', conditions: [], conjunction: 'and' as const },
        { id: 'b-default', name: '默认', conditions: [], conjunction: 'and' as const, is_default: true },
      ],
    };
    const next = removeConditionBranch(config, 'b1');
    expect(next.branches.length).toBe(2);
    expect(next.branches[next.branches.length - 1].id).toBe('b-default');
    expect(next.branches[next.branches.length - 1].is_default).toBe(true);
  });

  it('normalizeConditionConfig 保留 branches 中的 is_default 字段', () => {
    const result = normalizeConditionConfig({
      branches: [
        { id: 'b1', name: 'B1', conditions: [], conjunction: 'and' },
        { id: 'b2', name: '默认', conditions: [], conjunction: 'and', is_default: true },
      ],
    });
    expect(result.branches[1].is_default).toBe(true);
  });
});
