import type {
  ConditionBranch,
  ConditionItem,
  ConditionNodeConfig,
} from "@/types/workflow";

let branchIdCounter = 0;

export function generateBranchId(): string {
  branchIdCounter += 1;
  return `branch_${Date.now()}_${branchIdCounter}`;
}

export function createEmptyBranch(name?: string): ConditionBranch {
  return {
    id: generateBranchId(),
    name: name ?? "新分支",
    conditions: [],
    conjunction: "and",
    target_node_id: undefined,
  };
}

interface LegacyConditionConfig {
  conditions?: ConditionItem[];
  conjunction?: "and" | "or";
}

export function normalizeConditionConfig(
  config: unknown,
): ConditionNodeConfig {
  if (config && typeof config === "object" && !Array.isArray(config)) {
    const cfg = config as { branches?: unknown } & LegacyConditionConfig;
    if (Array.isArray(cfg.branches)) {
      const branches = cfg.branches.filter(
        (b): b is ConditionBranch =>
          b && typeof b === "object" && typeof (b as ConditionBranch).id === "string",
      );
      if (branches.length > 0) {
        return { branches };
      }
    }

    const oldConditions = Array.isArray(cfg.conditions) ? cfg.conditions : [];
    const oldConjunction = cfg.conjunction === "or" ? "or" : "and";
    return {
      branches: [
        {
          id: generateBranchId(),
          name: "满足条件",
          conditions: oldConditions,
          conjunction: oldConjunction,
          target_node_id: undefined,
        },
      ],
    };
  }

  return { branches: [createEmptyBranch("满足条件")] };
}

export function getConditionBranches(config: unknown): ConditionBranch[] {
  return normalizeConditionConfig(config).branches;
}

export function isEmptyConditionConfig(config: unknown): boolean {
  const { branches } = normalizeConditionConfig(config);
  return branches.length === 0;
}

export function updateConditionBranch(
  config: ConditionNodeConfig,
  branchId: string,
  updater: (branch: ConditionBranch) => ConditionBranch,
): ConditionNodeConfig {
  return {
    ...config,
    branches: config.branches.map((branch) =>
      branch.id === branchId ? updater(branch) : branch,
    ),
  };
}

export function setConditionBranchTarget(
  config: ConditionNodeConfig,
  branchId: string,
  targetNodeId: string | undefined,
): ConditionNodeConfig {
  return updateConditionBranch(config, branchId, (branch) => ({
    ...branch,
    target_node_id: targetNodeId,
  }));
}

export function addConditionBranch(
  config: ConditionNodeConfig,
  name?: string,
): { config: ConditionNodeConfig; branch: ConditionBranch } {
  const branch = createEmptyBranch(
    name ?? `分支 ${config.branches.length + 1}`,
  );
  return {
    config: { ...config, branches: [...config.branches, branch] },
    branch,
  };
}

export function removeConditionBranch(
  config: ConditionNodeConfig,
  branchId: string,
): ConditionNodeConfig {
  const branches = config.branches.filter((b) => b.id !== branchId);
  return { ...config, branches };
}

export function getConditionNextNodeIds(config: unknown): string[] {
  return getConditionBranches(config)
    .map((b) => b.target_node_id)
    .filter((id): id is string => !!id);
}
