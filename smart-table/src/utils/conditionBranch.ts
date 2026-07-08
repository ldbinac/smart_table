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

export function createDefaultBranch(name?: string): ConditionBranch {
  return {
    id: generateBranchId(),
    name: name ?? "默认分支",
    conditions: [],
    conjunction: "and",
    target_node_id: undefined,
    is_default: true,
  };
}

interface LegacyConditionConfig {
  conditions?: ConditionItem[];
  conjunction?: "and" | "or";
}

function isBranch(value: unknown): value is ConditionBranch {
  return !!value && typeof value === "object" && typeof (value as ConditionBranch).id === "string";
}

export function normalizeConditionConfig(
  config: unknown,
): ConditionNodeConfig {
  if (config && typeof config === "object" && !Array.isArray(config)) {
    const cfg = config as { branches?: unknown } & LegacyConditionConfig;
    if (Array.isArray(cfg.branches)) {
      const branches = cfg.branches.filter(isBranch);
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

export function hasDefaultBranch(config: unknown): boolean {
  return getConditionBranches(config).some((b) => b.is_default === true);
}

export function getDefaultBranch(config: unknown): ConditionBranch | undefined {
  return getConditionBranches(config).find((b) => b.is_default === true);
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
  const nonDefault = config.branches.filter((b) => !b.is_default);
  const defaultBranches = config.branches.filter((b) => b.is_default);
  return {
    config: { ...config, branches: [...nonDefault, branch, ...defaultBranches] },
    branch,
  };
}

export function addDefaultBranch(
  config: ConditionNodeConfig,
  name?: string,
): { config: ConditionNodeConfig; branch: ConditionBranch } {
  const nonDefault = config.branches.filter((b) => !b.is_default);
  const existingDefault = config.branches.find((b) => b.is_default);
  if (existingDefault) {
    return { config, branch: existingDefault };
  }
  const branch = createDefaultBranch(name);
  return {
    config: { ...config, branches: [...nonDefault, branch] },
    branch,
  };
}

export function moveBranchToEnd(
  config: ConditionNodeConfig,
  branchId: string,
): ConditionNodeConfig {
  const idx = config.branches.findIndex((b) => b.id === branchId);
  if (idx < 0 || idx === config.branches.length - 1) return config;
  const next = [...config.branches];
  const [moved] = next.splice(idx, 1);
  next.push(moved);
  return { ...config, branches: next };
}

export function removeConditionBranch(
  config: ConditionNodeConfig,
  branchId: string,
): ConditionNodeConfig {
  const branches = config.branches.filter((b) => b.id !== branchId);
  const nonDefault = branches.filter((b) => !b.is_default);
  const defaultBranches = branches.filter((b) => b.is_default);
  return { ...config, branches: [...nonDefault, ...defaultBranches] };
}

export function getConditionNextNodeIds(config: unknown): string[] {
  return getConditionBranches(config)
    .map((b) => b.target_node_id)
    .filter((id): id is string => !!id);
}
