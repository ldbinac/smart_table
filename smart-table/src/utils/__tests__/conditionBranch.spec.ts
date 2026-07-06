import { describe, it, expect } from 'vitest';
import {
  normalizeConditionConfig,
  getConditionBranches,
  addConditionBranch,
  removeConditionBranch,
  updateConditionBranch,
  setConditionBranchTarget,
  getConditionNextNodeIds,
} from '../conditionBranch';

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
});
