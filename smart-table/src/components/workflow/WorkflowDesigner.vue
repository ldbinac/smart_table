<script setup lang="ts">
import {
  computed,
  nextTick,
  onMounted,
  onUnmounted,
  ref,
  watch,
} from "vue";
import Sortable from "sortablejs";
import { ElMessageBox } from "element-plus";
import { onBeforeRouteLeave } from "vue-router";
import type { FieldEntity, TableEntity } from "@/db/schema";
import type {
  Workflow,
  WorkflowNode,
  WorkflowTrigger,
  WebhookConfig,
  WorkflowNodeType,
} from "@/types/workflow";
import {
  CircleCheck,
  Share,
  EditPen,
  Plus,
  Search,
  Message,
  Link,
  Delete,
  Rank,
  Timer,
  CopyDocument,
} from "@element-plus/icons-vue";
import WorkflowNodeConfig from "./WorkflowNodeConfig.vue";
import WorkflowTriggerConfig from "./WorkflowTriggerConfig.vue";
import WorkflowCanvas from "./WorkflowCanvas.vue";
import WorkflowCanvasToolbar from "./WorkflowCanvasToolbar.vue";
import {
  layoutWorkflowNodes,
  hasValidLayout,
} from "./workflowLayout";
import {
  getConditionBranches,
  setConditionBranchTarget,
} from "@/utils/conditionBranch";
import { isValidWorkflowVariableName } from "@/utils/workflow";

interface Props {
  workflow: Workflow;
  nodes: WorkflowNode[];
  trigger: WorkflowTrigger;
  fields: FieldEntity[];
  tables?: TableEntity[];
  webhooks?: WebhookConfig[];
  loading?: boolean;
}

const props = defineProps<Props>();
const emit = defineEmits<{
  (e: "update:nodes", nodes: WorkflowNode[]): void;
  (e: "update:trigger", trigger: WorkflowTrigger): void;
  (e: "save"): void;
  (e: "publish"): void;
  (e: "clone"): void;
  (e: "viewVersions"): void;
}>();

const localNodes = ref<WorkflowNode[]>([]);
const localTrigger = ref<WorkflowTrigger>({ ...props.trigger });
const selectedNodeId = ref<string | null>(null);
const viewMode = ref<"list" | "canvas">("list");
const canvasRef = ref<InstanceType<typeof WorkflowCanvas> | null>(null);
const panMode = ref(false);
const nodeListRef = ref<HTMLElement | null>(null);
const triggerConfigRef = ref<InstanceType<typeof WorkflowTriggerConfig> | null>(null);
let sortableInstance: Sortable | null = null;
let isUpdatingNodesFromParent = false;
let isUpdatingTriggerFromParent = false;

const designerLayoutRef = ref<HTMLElement | null>(null);
const isResizing = ref(false);
const listModeLeftWidth = ref(360);
const canvasModeLeftPercent = ref(50);
let resizeCleanup: (() => void) | null = null;

const LIST_MIN_WIDTH = 280;
const LIST_MAX_WIDTH = 600;
const CANVAS_MIN_PERCENT = 30;
const CANVAS_MAX_PERCENT = 70;

const leftPanelStyle = computed(() => {
  if (viewMode.value === "canvas") {
    return {
      flex: `0 0 ${canvasModeLeftPercent.value}%`,
      minWidth: `${CANVAS_MIN_PERCENT}%`,
      maxWidth: `${CANVAS_MAX_PERCENT}%`,
    };
  }
  return {
    flex: `0 0 ${listModeLeftWidth.value}px`,
    minWidth: `${LIST_MIN_WIDTH}px`,
    maxWidth: `${LIST_MAX_WIDTH}px`,
  };
});

const rightPanelStyle = computed(() => {
  if (viewMode.value === "canvas") {
    return {
      flex: `0 0 ${100 - canvasModeLeftPercent.value}%`,
    };
  }
  return {
    flex: 1,
  };
});

const selectedNode = computed(() =>
  localNodes.value.find((n) => n.id === selectedNodeId.value) ?? null,
);

watch(
  () => props.nodes,
  (newNodes) => {
    isUpdatingNodesFromParent = true;
    const chain = rebuildNodeChain(
      newNodes.map((n) => ({ ...n, config: cloneConfig(n.config) })),
    );
    const needsLayout = chain.some((node) => !hasValidLayout(node));
    localNodes.value = needsLayout ? layoutWorkflowNodes(chain) : chain;
    if (!selectedNodeId.value && newNodes.length > 0) {
      selectedNodeId.value = newNodes[0].id;
    }
    nextTick(() => {
      isUpdatingNodesFromParent = false;
    });
  },
  { immediate: true, deep: true },
);

watch(
  () => props.trigger,
  (newTrigger) => {
    isUpdatingTriggerFromParent = true;
    localTrigger.value = { ...newTrigger };
    nextTick(() => {
      isUpdatingTriggerFromParent = false;
    });
  },
  { deep: true },
);

watch(
  localNodes,
  (newNodes) => {
    if (isUpdatingNodesFromParent) return;
    emit("update:nodes", newNodes.map((n) => ({ ...n, config: cloneConfig(n.config) })));
  },
  { deep: true },
);

watch(
  localTrigger,
  (newTrigger) => {
    if (isUpdatingTriggerFromParent) return;
    emit("update:trigger", { ...newTrigger });
  },
  { deep: true },
);

const isDraft = computed(() => props.workflow.status === "draft");
const isPaused = computed(() => props.workflow.status === "paused");
const isFreshDraft = computed(() => isDraft.value && (props.workflow.current_version ?? 0) === 0);
const readonly = computed(() => !["draft", "paused"].includes(props.workflow.status));
const hasInvalidMappingNodes = computed(() => !validateNodeMappings(localNodes.value).valid);

function cloneConfig(config: Record<string, unknown>): Record<string, unknown> {
  return JSON.parse(JSON.stringify(config));
}

function generateId(): string {
  return `node_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
}

// 根据 order 自动重建节点执行链：普通节点默认指向下一个节点；
// 条件节点的 next_nodes 由其 branches 中的 target_node_id 决定；
// 分支目标节点可链接到下一个非分支目标节点（合并点或后续节点），
// 但不会自动链接到任何分支目标节点，以保持并行分支独立。
function rebuildNodeChain(nodes: WorkflowNode[]): WorkflowNode[] {
  const sorted = [...nodes].sort((a, b) => a.order - b.order);
  const branchTargetIds = new Set<string>();
  sorted.forEach((node) => {
    if (node.node_type !== "condition") return;
    getConditionBranches(node.config).forEach((branch) => {
      if (branch.target_node_id) branchTargetIds.add(branch.target_node_id);
    });
  });
  const nextMap = new Map<string, string[]>();
  sorted.forEach((node, index) => {
    if (node.node_type === "condition") {
      const nextIds = getConditionBranches(node.config)
        .map((b) => b.target_node_id)
        .filter((id): id is string => !!id);
      nextMap.set(node.id, nextIds);
    } else {
      const nextNode = sorted[index + 1];
      if (!nextNode || branchTargetIds.has(nextNode.id)) {
        nextMap.set(node.id, []);
      } else {
        nextMap.set(node.id, [nextNode.id]);
      }
    }
  });
  return nodes.map((node) => ({
    ...node,
    next_nodes: nextMap.get(node.id) ?? [],
  }));
}

interface InvalidNodeInfo {
  name: string;
  reason: string;
}

interface MappingValidationResult {
  valid: boolean;
  invalidNodes: InvalidNodeInfo[];
}

function validateNodeMappings(nodes: WorkflowNode[]): MappingValidationResult {
  const invalidNodes: InvalidNodeInfo[] = [];
  nodes.forEach((node) => {
    if (node.node_type === 'create_record') {
      const mappings = (node.config?.field_mappings ?? []) as unknown[];
      if (!mappings.length) {
        invalidNodes.push({ name: node.name, reason: '字段映射未配置' });
      }
    } else if (node.node_type === 'update_record') {
      const updates = (node.config?.updates ?? []) as unknown[];
      if (!updates.length) {
        invalidNodes.push({ name: node.name, reason: '字段映射未配置' });
      }
    } else if (node.node_type === 'condition') {
      const branches = getConditionBranches(node.config);
      if (branches.length === 0) {
        invalidNodes.push({ name: node.name, reason: '分支配置不完整' });
      } else {
        const hasInvalid = branches.some((b) =>
          b.is_default
            ? !b.target_node_id
            : b.conditions.length === 0
        );
        if (hasInvalid) {
          invalidNodes.push({ name: node.name, reason: '分支配置不完整' });
        }
      }
    } else if (node.node_type === 'find_records') {
      const config = node.config || {};
      const targetTableId = config.target_table_id;
      const resultVariable = config.result_variable;
      if (!targetTableId) {
        invalidNodes.push({ name: node.name, reason: '目标表格未选择' });
      } else if (!resultVariable) {
        invalidNodes.push({ name: node.name, reason: '结果变量名未配置' });
      } else if (!isValidWorkflowVariableName(resultVariable as string)) {
        invalidNodes.push({ name: node.name, reason: '结果变量名格式不正确' });
      }
    }
  });
  return { valid: invalidNodes.length === 0, invalidNodes };
}

const nodeTypeMenu = [
  { type: "update_record" as const, label: "更新记录", icon: EditPen },
  { type: "create_record" as const, label: "创建记录", icon: Plus },
  { type: "find_records" as const, label: "查找记录", icon: Search },
  // { type: "send_email" as const, label: "发送邮件（暂不支持）", icon: Message },
  { type: "webhook" as const, label: "Webhook", icon: Link },
  { type: "condition" as const, label: "条件节点", icon: Share },
];

const nodeIconMap: Record<string, typeof CircleCheck> = {
  condition: Share,
  update_record: EditPen,
  create_record: Plus,
  find_records: Search,
  send_email: Message,
  webhook: Link,
  action: EditPen,
  trigger: CircleCheck,
};

function getNodeIcon(nodeType: string) {
  return nodeIconMap[nodeType] ?? CircleCheck;
}

function getNodeLabel(nodeType: string) {
  const item = nodeTypeMenu.find((m) => m.type === nodeType);
  return item?.label ?? nodeType;
}

function getDefaultNodeConfig(type: WorkflowNodeType): Record<string, unknown> {
  if (type === "find_records") {
    return {
      target_table_id: props.workflow.table_id ?? "",
      result_variable: "records",
      conditions: [],
      sort_field_id: undefined,
      sort_direction: "asc",
      limit: 100,
      empty_action: "continue",
    };
  }
  return {};
}

function addNode(type: WorkflowNodeType) {
  const newNode: WorkflowNode = {
    id: generateId(),
    workflow_id: props.workflow.id,
    node_type: type,
    name: `${getNodeLabel(type)} ${localNodes.value.length + 1}`,
    config: getDefaultNodeConfig(type),
    order: localNodes.value.length,
    next_nodes: [],
  };
  localNodes.value = rebuildNodeChain([...localNodes.value, newNode]);
  selectedNodeId.value = newNode.id;
}

function removeNode(nodeId: string) {
  const filtered = localNodes.value.filter((n) => n.id !== nodeId);
  const cleared = filtered.map((node) => {
    if (node.node_type !== "condition") return node;
    const branches = getConditionBranches(node.config);
    const hasTarget = branches.some((b) => b.target_node_id === nodeId);
    if (!hasTarget) return node;
    let updatedConfig = { ...node.config, branches };
    branches.forEach((branch) => {
      if (branch.target_node_id === nodeId) {
        updatedConfig = setConditionBranchTarget(
          updatedConfig as { branches: typeof branches },
          branch.id,
          undefined,
        );
      }
    });
    return { ...node, config: updatedConfig };
  });
  localNodes.value = rebuildNodeChain(cleared);
  if (selectedNodeId.value === nodeId) {
    selectedNodeId.value = localNodes.value[0]?.id ?? null;
  }
}

function selectNode(nodeId: string) {
  selectedNodeId.value = nodeId;
}

function updateNode(updatedNode: WorkflowNode) {
  const index = localNodes.value.findIndex((n) => n.id === updatedNode.id);
  if (index !== -1) {
    const list = [...localNodes.value];
    list[index] = { ...updatedNode, config: cloneConfig(updatedNode.config) };
    localNodes.value = list;
  }
}

function updateTrigger(updatedTrigger: WorkflowTrigger) {
  localTrigger.value = { ...updatedTrigger };
}

function handleCanvasUpdateNodes(nodes: WorkflowNode[]) {
  localNodes.value = rebuildNodeChain(
    nodes.map((node) => ({ ...node, config: cloneConfig(node.config) })),
  );
}

function handleCanvasSelectNode(nodeId: string) {
  selectedNodeId.value = nodeId;
}

function handleCanvasEdgeInsert(payload: {
  sourceId: string;
  targetId: string;
  nodeType: string;
}) {
  insertNodeBetween(payload.sourceId, payload.targetId, payload.nodeType);
}

function handleCanvasEdgeDelete(payload: {
  sourceId: string;
  targetId: string;
  branchId?: string;
}) {
  const sourceNode = localNodes.value.find((n) => n.id === payload.sourceId);
  if (!sourceNode || sourceNode.node_type !== "condition" || !payload.branchId) return;

  const config = setConditionBranchTarget(
    { branches: getConditionBranches(sourceNode.config) },
    payload.branchId,
    undefined,
  );
  const branches = getConditionBranches(config);
  const updatedNode: WorkflowNode = {
    ...sourceNode,
    config: { ...sourceNode.config, branches },
    next_nodes: branches.map((b) => b.target_node_id).filter((id): id is string => !!id),
  };
  updateNode(updatedNode);
}

function handleCanvasAddNode(payload: {
  position: "before" | "after" | "first";
  nodeType: string;
  targetId?: string;
}) {
  const { position, nodeType, targetId } = payload;
  const type = nodeType as WorkflowNodeType;

  if (position === "first") {
    const newNode: WorkflowNode = {
      id: generateId(),
      workflow_id: props.workflow.id,
      node_type: type,
      name: `${getNodeLabel(nodeType)} ${localNodes.value.length + 1}`,
      config: getDefaultNodeConfig(type),
      order: -1,
      next_nodes: [],
    };
    const sorted = [newNode, ...localNodes.value].sort((a, b) => a.order - b.order);
    const reindexed = sorted.map((node, index) => ({ ...node, order: index }));
    localNodes.value = rebuildNodeChain(reindexed);
    selectedNodeId.value = newNode.id;
    return;
  }

  const targetNode = localNodes.value.find((n) => n.id === targetId);
  if (!targetNode) return;

  const newNode: WorkflowNode = {
    id: generateId(),
    workflow_id: props.workflow.id,
    node_type: type,
    name: `${getNodeLabel(nodeType)} ${localNodes.value.length + 1}`,
    config: getDefaultNodeConfig(type),
    order: position === "before" ? targetNode.order - 0.5 : targetNode.order + 0.5,
    next_nodes: [],
  };

  const list = [...localNodes.value, newNode];

  if (position === "after" && targetNode.node_type === "condition") {
    const branches = getConditionBranches(targetNode.config);
    const availableBranch = branches.find((b) => !b.target_node_id);
    if (availableBranch) {
      const updatedConfig = setConditionBranchTarget(
        { branches },
        availableBranch.id,
        newNode.id,
      );
      const targetIndex = list.findIndex((n) => n.id === targetNode.id);
      list[targetIndex] = {
        ...targetNode,
        config: { ...targetNode.config, branches: updatedConfig.branches },
      };
    }
  }

  const sorted = [...list].sort((a, b) => a.order - b.order);
  const reindexed = sorted.map((node, index) => ({ ...node, order: index }));
  localNodes.value = rebuildNodeChain(reindexed);
  selectedNodeId.value = newNode.id;
}

function handleCanvasDeleteNode(nodeId: string) {
  removeNode(nodeId);
}

function insertNodeBetween(sourceId: string, targetId: string, nodeType: string) {
  const sourceNode = localNodes.value.find((n) => n.id === sourceId);
  if (!sourceNode) return;

  const newNode: WorkflowNode = {
    id: generateId(),
    workflow_id: props.workflow.id,
    node_type: nodeType as WorkflowNodeType,
    name: `${getNodeLabel(nodeType)} ${localNodes.value.length + 1}`,
    config: getDefaultNodeConfig(nodeType as WorkflowNodeType),
    order: sourceNode.order + 0.5,
    next_nodes: [targetId],
  };

  const list = [...localNodes.value, newNode];
  const sorted = [...list].sort((a, b) => a.order - b.order);
  const reindexed = sorted.map((node, index) => ({ ...node, order: index }));
  localNodes.value = rebuildNodeChain(reindexed);
  selectedNodeId.value = newNode.id;
}

function handleCanvasZoomIn() {
  canvasRef.value?.zoomIn();
}

function handleCanvasZoomOut() {
  canvasRef.value?.zoomOut();
}

function handleCanvasFitView() {
  canvasRef.value?.fitView();
}

function handleTogglePanMode() {
  panMode.value = !panMode.value;
}

function startResize(event: MouseEvent) {
  if (!designerLayoutRef.value) return;
  isResizing.value = true;
  const containerWidth = designerLayoutRef.value.clientWidth;
  const startX = event.clientX;
  const startValue = viewMode.value === "canvas" ? canvasModeLeftPercent.value : listModeLeftWidth.value;
  const originalUserSelect = document.body.style.userSelect;
  document.body.style.userSelect = "none";

  function onMouseMove(moveEvent: MouseEvent) {
    moveEvent.preventDefault();
    const deltaX = moveEvent.clientX - startX;
    if (viewMode.value === "canvas") {
      const deltaPercent = (deltaX / containerWidth) * 100;
      canvasModeLeftPercent.value = Math.max(
        CANVAS_MIN_PERCENT,
        Math.min(CANVAS_MAX_PERCENT, startValue + deltaPercent),
      );
    } else {
      const newWidth = startValue + deltaX;
      listModeLeftWidth.value = Math.max(
        LIST_MIN_WIDTH,
        Math.min(LIST_MAX_WIDTH, newWidth),
      );
    }
  }

  function onMouseUp() {
    isResizing.value = false;
    document.body.style.userSelect = originalUserSelect;
    document.removeEventListener("mousemove", onMouseMove);
    document.removeEventListener("mouseup", onMouseUp);
    resizeCleanup = null;
  }

  resizeCleanup = () => {
    document.body.style.userSelect = originalUserSelect;
    document.removeEventListener("mousemove", onMouseMove);
    document.removeEventListener("mouseup", onMouseUp);
  };

  document.addEventListener("mousemove", onMouseMove);
  document.addEventListener("mouseup", onMouseUp);
}

function initSortable() {
  if (!nodeListRef.value) return;
  if (sortableInstance) sortableInstance.destroy();

  sortableInstance = new Sortable(nodeListRef.value, {
    animation: 200,
    handle: ".drag-handle",
    disabled: readonly.value,
    onEnd: (event) => {
      if (event.oldIndex === undefined || event.newIndex === undefined) return;
      if (event.oldIndex === event.newIndex) return;

      const list = [...localNodes.value];
      const [moved] = list.splice(event.oldIndex, 1);
      list.splice(event.newIndex, 0, moved);
      localNodes.value = rebuildNodeChain(list.map((node, index) => ({ ...node, order: index })));
    },
  });
}

onMounted(() => {
  nextTick(() => initSortable());
  window.addEventListener('beforeunload', handleBeforeUnload);
});

onUnmounted(() => {
  sortableInstance?.destroy();
  sortableInstance = null;
  window.removeEventListener('beforeunload', handleBeforeUnload);
  resizeCleanup?.();
  resizeCleanup = null;
});

watch(
  () => localNodes.value.length,
  () => {
    nextTick(() => initSortable());
  },
);

watch(
  readonly,
  () => {
    nextTick(() => initSortable());
  },
);

async function handleSave() {
  if (triggerConfigRef.value?.validateFieldIds?.() === false) {
    try {
      await ElMessageBox.confirm(
        '当前触发器类型要求配置"监听字段"，未配置监听字段可能导致触发器无法正常工作。是否仍要保存？',
        '监听字段未配置',
        {
          cancelButtonText: '去配置',
          confirmButtonText: '仍然保存',
          type: 'warning',
        }
      );
    } catch {
      return;
    }
  }

  const mappingValidation = validateNodeMappings(localNodes.value);
  if (!mappingValidation.valid) {
    const nodeList = mappingValidation.invalidNodes
      .map((node) => `· ${node.name}：${node.reason}`)
      .join('\n');
    await ElMessageBox.alert(
      `以下节点配置不完整，请先配置后再保存：\n${nodeList}`,
      '节点配置不完整',
      { confirmButtonText: '去配置' }
    );
    return;
  }

  emit("save");
}

// function handlePublish() {
//   emit("publish");
// }

function handleClone() {
  emit("clone");
}

function handleViewVersions() {
  emit("viewVersions");
}

const LEAVE_CONFIRM_MESSAGE =
  '当前工作流存在配置不完整的节点，离开将丢失未保存的修改，是否继续？';

function handleBeforeUnload(event: BeforeUnloadEvent) {
  if (hasInvalidMappingNodes.value) {
    event.preventDefault();
    event.returnValue = LEAVE_CONFIRM_MESSAGE;
    return LEAVE_CONFIRM_MESSAGE;
  }
}

onBeforeRouteLeave((_, __, next) => {
  if (hasInvalidMappingNodes.value) {
    ElMessageBox.confirm(LEAVE_CONFIRM_MESSAGE, '确认离开', {
      confirmButtonText: '继续离开',
      cancelButtonText: '去配置',
      type: 'warning',
    })
      .then(() => next())
      .catch(() => next(false));
    return;
  }
  next();
});
</script>

<template>
  <div v-loading="loading" class="workflow-designer" :class="{ 'is-loading': loading }">
    <div ref="designerLayoutRef" class="designer-layout">
      <!-- 左侧：触发器 + 节点列表 / 画布 -->
      <div class="designer-left" :style="leftPanelStyle">
        <div class="left-panel-header">
          <span class="left-panel-title">流程设计</span>
          <el-button-group>
            <el-button
              size="small"
              :type="viewMode === 'list' ? 'primary' : 'default'"
              @click="viewMode = 'list'">
              列表
            </el-button>
            <el-button
              size="small"
              :type="viewMode === 'canvas' ? 'primary' : 'default'"
              @click="viewMode = 'canvas'">
              画布
            </el-button>
          </el-button-group>
        </div>

        <template v-if="viewMode === 'list'">
          <div class="section trigger-section">
            <div class="section-title">触发器配置</div>
            <div class="trigger-content">
              <WorkflowTriggerConfig
                ref="triggerConfigRef"
                :trigger="localTrigger"
                :fields="fields"
                :readonly="readonly"
                @update:trigger="updateTrigger" />
            </div>
          </div>

          <div class="section nodes-section">
            <div class="section-title section-title-with-action">
              <span>
                节点列表
                <span class="node-count">（{{ localNodes.length }}）</span>
              </span>
              <div v-if="!readonly" class="add-node-menu">
                <el-dropdown placement="bottom-start" trigger="click">
                  <el-button type="primary" :icon="Plus" class="add-node-btn" size="small">
                    添加节点
                  </el-button>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item
                        v-for="item in nodeTypeMenu"
                        :key="item.type"
                        @click="addNode(item.type)">
                        <el-icon><component :is="item.icon" /></el-icon>
                        <span>{{ item.label }}</span>
                      </el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </div>
            </div>

            <div ref="nodeListRef" class="node-list">
              <div
                v-for="node in localNodes"
                :key="node.id"
                class="node-item"
                :data-node-id="node.id"
                :class="{ active: selectedNodeId === node.id }"
                @click="selectNode(node.id)">
                <el-icon v-show="!readonly" class="drag-handle"><Rank /></el-icon>
                <el-icon class="node-icon"><component :is="getNodeIcon(node.node_type)" /></el-icon>
                <div class="node-info">
                  <div class="node-name">{{ node.name }}</div>
                  <div class="node-type">{{ getNodeLabel(node.node_type) }}</div>
                </div>
                <div class="node-order">#{{ node.order + 1 }}</div>
                <el-button
                  v-if="!readonly"
                  type="danger"
                  :icon="Delete"
                  link
                  size="small"
                  class="delete-btn"
                  @click.stop="removeNode(node.id)" />
              </div>
            </div>
          </div>
        </template>

        <template v-else>
          <div class="canvas-view">
            <WorkflowCanvas
              ref="canvasRef"
              :nodes="localNodes"
              :readonly="readonly"
              :selected-node-id="selectedNodeId"
              @update:nodes="handleCanvasUpdateNodes"
              @select-node="handleCanvasSelectNode"
              @edge-insert="handleCanvasEdgeInsert"
              @edge-delete="handleCanvasEdgeDelete"
              @add-node="handleCanvasAddNode"
              @delete-node="handleCanvasDeleteNode" />
            <WorkflowCanvasToolbar
              :pan-mode="panMode"
              @zoom-in="handleCanvasZoomIn"
              @zoom-out="handleCanvasZoomOut"
              @fit-view="handleCanvasFitView"
              @toggle-pan-mode="handleTogglePanMode" />
          </div>
        </template>
      </div>

      <div
        class="designer-splitter"
        :class="{ 'is-resizing': isResizing }"
        title="拖动调整宽度"
        @mousedown="startResize" />

      <!-- 右侧：节点配置 -->
      <div class="designer-right" :style="rightPanelStyle">
        <div class="section-title">节点配置</div>
        <div class="config-panel">
          <WorkflowNodeConfig
            v-if="selectedNode"
            :node="selectedNode"
            :fields="fields"
            :tables="tables"
            :webhooks="webhooks"
            :readonly="readonly"
            @update:node="updateNode" />
          <el-empty v-else description="请选择或添加一个节点" />
        </div>
      </div>
    </div>

    <!-- 底部操作栏 -->
    <div class="designer-footer">
      <div class="workflow-status">
        <el-tag v-if="isDraft" type="info">草稿</el-tag>
        <el-tag v-else-if="workflow.status === 'active'" type="success">已发布</el-tag>
        <el-tag v-else-if="workflow.status === 'paused'" type="warning">已暂停</el-tag>
        <el-tag v-else type="danger">已归档</el-tag>
      </div>

      <div class="footer-actions">
        <template v-if="!isFreshDraft">
          <el-button title="基于当前流程创建新版本" type="success" plain :icon="CopyDocument" @click="handleClone">
            复制创建新版本
          </el-button>
          <el-button :icon="Timer" @click="handleViewVersions">
            查看版本历史
          </el-button>
        </template>
        <template v-if="isDraft || isPaused">
          <el-button :icon="CircleCheck" type="primary" @click="handleSave">
            保存
          </el-button>
          <!-- <el-button v-if="isPaused" type="success" :icon="CircleCheck" @click="handlePublish">
            发布
          </el-button> -->
        </template>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.workflow-designer {
  display: flex;
  flex-direction: column;
  height: 100%;
  background-color: $bg-color;
}

.designer-layout {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.designer-left {
  display: flex;
  flex-direction: column;
  border-right: 1px solid $border-color;
  background-color: white;
  overflow: hidden;
}

.left-panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: $spacing-sm;
  padding: $spacing-sm $spacing-md;
  border-bottom: 1px solid $border-color;
  background-color: #f2f4f5;
  flex-shrink: 0;
}

.left-panel-title {
  font-weight: 600;
  color: $text-primary;
}

.canvas-view {
  flex: 1;
  position: relative;
  overflow: hidden;
  min-height: 0;
}

.designer-right {
  display: flex;
  flex-direction: column;
  background-color: white;
  overflow: hidden;
}

.designer-splitter {
  width: 6px;
  flex-shrink: 0;
  cursor: col-resize;
  background-color: transparent;
  transition: background-color 0.2s;
  z-index: 10;

  &:hover,
  &.is-resizing {
    background-color: rgba($primary-color, 0.25);
  }
}

.section {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.trigger-section {
  flex: 0 0 auto;
  max-height: 45%;
  overflow: hidden;
  border-bottom: 1px solid $border-color;
}

.trigger-content {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
}

.nodes-section {
  flex: 1;
  overflow: hidden;
}

.section-title {
  display: flex;
  align-items: center;
  gap: $spacing-xs;
  padding: $spacing-md;
  font-weight: 600;
  color: $text-primary;
  border-bottom: 1px solid $border-color;
  background-color: #f2f4f5;
}

.node-count {
  font-weight: normal;
  color: $text-secondary;
  font-size: $font-size-sm;
}

.node-list {
  flex: 1;
  overflow-y: auto;
  padding: $spacing-sm;
}

.node-item {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  padding: $spacing-sm;
  margin-bottom: $spacing-sm;
  background-color: $bg-color;
  border-radius: $border-radius-md;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid $border-color;

  &:hover {
    background-color: rgba($primary-color, 0.04);
  }

  &.active {
    border-color: $primary-color;
    background-color: rgba($primary-color, 0.08);
  }
}

.drag-handle {
  color: $text-secondary;
  cursor: grab;
}

.node-icon {
  font-size: 18px;
  color: $primary-color;
}

.node-info {
  flex: 1;
  min-width: 0;
}

.node-name {
  font-weight: 500;
  color: $text-primary;
  font-size: $font-size-sm;
}

.node-type {
  font-size: 12px;
  color: $text-secondary;
}

.node-order {
  font-size: 12px;
  color: $text-disabled;
}

.delete-btn {
  opacity: 0;
  transition: opacity 0.2s;

  .node-item:hover & {
    opacity: 1;
  }
}

.section-title-with-action {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: $spacing-sm;
}

.add-node-menu {
  .add-node-btn {
    min-width: 80px;
  }
}

.config-panel {
  flex: 1;
  overflow-y: auto;
}

.designer-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: $spacing-md;
  background-color: white;
  border-top: 1px solid $border-color;
}

.footer-actions {
  display: flex;
  gap: $spacing-sm;
}
</style>
