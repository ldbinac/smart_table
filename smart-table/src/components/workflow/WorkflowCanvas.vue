<script setup lang="ts">
import { computed, ref } from "vue";
import { VueFlow } from "@vue-flow/core";
import { Handle, Position } from "@vue-flow/core";
import { Background } from "@vue-flow/background";
import { Controls } from "@vue-flow/controls";
import { Plus, Delete } from "@element-plus/icons-vue";
import type {
  Node as FlowNode,
  Edge as FlowEdge,
  NodeMouseEvent,
  NodeDragEvent,
  Connection,
} from "@vue-flow/core";
import type { WorkflowNode } from "@/types/workflow";
import {
  getConditionBranches,
  setConditionBranchTarget,
} from "@/utils/conditionBranch";
import {
  ADDABLE_NODE_TYPES,
  LOOP_BODY_ALLOWED_NODE_TYPES,
  NODE_TYPE_ICON_MAP,
  NODE_TYPE_LABEL_MAP,
} from "@/utils/workflowNodeType";
import WorkflowNodeCard from "./WorkflowNodeCard.vue";
import WorkflowEdgeWithAddButton from "./WorkflowEdgeWithAddButton.vue";
import "@vue-flow/core/dist/style.css";

interface Props {
  nodes: WorkflowNode[];
  readonly?: boolean;
  selectedNodeId?: string | null;
}

const props = withDefaults(defineProps<Props>(), {
  readonly: false,
  selectedNodeId: null,
});

const emit = defineEmits<{
  (e: "update:nodes", nodes: WorkflowNode[]): void;
  (e: "select-node", nodeId: string): void;
  (
    e: "node-drag-stop",
    payload: { nodeId: string; position: { x: number; y: number } },
  ): void;
  (
    e: "edge-insert",
    payload: { sourceId: string; targetId: string; nodeType: string },
  ): void;
  (
    e: "add-node",
    payload: {
      position: "before" | "after" | "first";
      nodeType: string;
      targetId?: string;
      parentId?: string;
    },
  ): void;
  (e: "delete-node", nodeId: string): void;
  (e: "edge-delete", payload: { sourceId: string; targetId: string; branchId?: string }): void;
}>();

const vueFlowRef = ref<InstanceType<typeof VueFlow> | null>(null);

const isEmpty = computed(() => props.nodes.length === 0);

const flowNodes = computed<FlowNode[]>(() =>
  props.nodes.map((node) => ({
    id: node.id,
    type: node.node_type === "loop" ? "workflow-loop" : "workflow",
    position: node.ui_layout ?? { x: 0, y: 0 },
    data: { node, readonly: props.readonly },
    selectable: !props.readonly,
    draggable: !props.readonly,
    connectable: node.node_type === "condition" ? !props.readonly : false,
    class: {
      "workflow-node": true,
      "workflow-node-loop": node.node_type === "loop",
      selected: node.id === props.selectedNodeId,
    },
  })),
);

/** 循环体允许添加的节点类型 */
const loopBodyAllowedTypes = LOOP_BODY_ALLOWED_NODE_TYPES;

/** 循环节点数据源摘要（用于容器展示） */
function getLoopDataSourceLabel(node: WorkflowNode): string {
  const ds = (node.config?.data_source ?? {}) as {
    type?: string;
    node_id?: string;
    field_id?: string;
  };
  if (!ds.type) return "未配置";
  const dsTypeLabel: Record<string, string> = {
    find_records_all: "查找记录 - 全部",
    find_records_column: "查找记录 - 列值",
    webhook_array: "Webhook - json.array",
    trigger_field: "触发器字段",
  };
  return dsTypeLabel[ds.type] ?? ds.type;
}

/** 获取循环体子节点列表 */
function getLoopBodyNodes(node: WorkflowNode): WorkflowNode[] {
  if (node.node_type !== "loop") return [];
  return (node.config?.loop_body_nodes as WorkflowNode[] | undefined) ?? [];
}

/** 循环体子节点点击：选中该子节点 */
function handleSelectLoopChild(parentId: string, childId: string) {
  emit("select-node", childId);
}

/** 循环体子节点删除 */
function handleDeleteLoopChild(parentId: string, childId: string) {
  emit("delete-node", childId);
}

/** 在 loop 容器底部添加子节点 */
function handleAddLoopChild(parentId: string, nodeType: string) {
  emit("add-node", {
    position: "after",
    nodeType,
    targetId: parentId,
    parentId,
  });
}

function getChildNodeIcon(nodeType: string) {
  return NODE_TYPE_ICON_MAP[nodeType] ?? Plus;
}

function getChildNodeLabel(nodeType: string) {
  return NODE_TYPE_LABEL_MAP[nodeType] ?? nodeType;
}

const flowEdges = computed<FlowEdge[]>(() => {
  const edges: FlowEdge[] = [];
  props.nodes.forEach((node) => {
    if (node.node_type === "condition") {
      getConditionBranches(node.config).forEach((branch) => {
        if (!branch.target_node_id) return;
        edges.push({
          id: `e-${node.id}-${branch.target_node_id}-${branch.id}`,
          source: node.id,
          target: branch.target_node_id,
          sourceHandle: branch.id,
          type: "workflow",
          label: branch.name,
          markerEnd: "arrowclosed",
          data: {
            readonly: props.readonly,
            sourceNodeType: node.node_type,
            branchId: branch.id,
            branchName: branch.name,
          },
        });
      });
    } else {
      node.next_nodes.forEach((targetId) => {
        edges.push({
          id: `e-${node.id}-${targetId}`,
          source: node.id,
          target: targetId,
          type: "workflow",
          markerEnd: "arrowclosed",
          data: {
            readonly: props.readonly,
            sourceNodeType: node.node_type,
          },
        });
      });
    }
  });
  return edges;
});

function handleNodeClick(event: NodeMouseEvent) {
  emit("select-node", event.node.id);
}

function handleNodeDragStop(event: NodeDragEvent) {
  const nodeId = event.node.id;
  const position = {
    x: event.node.position.x,
    y: event.node.position.y,
  };

  emit("node-drag-stop", { nodeId, position });

  const updatedNodes = props.nodes.map((node) =>
    node.id === nodeId ? { ...node, ui_layout: { ...position } } : node,
  );
  emit("update:nodes", updatedNodes);
}

function handleEdgeInsert(payload: {
  sourceId: string;
  targetId: string;
  nodeType: string;
}) {
  emit("edge-insert", payload);
}

function handleConnect(connection: Connection) {
  const sourceNode = props.nodes.find((n) => n.id === connection.source);
  if (!sourceNode || sourceNode.node_type !== "condition") return;

  const branchId = connection.sourceHandle;
  if (!branchId || !connection.target) return;

  const updatedNodes = props.nodes.map((node) => {
    if (node.id !== sourceNode.id) return node;
    const config = setConditionBranchTarget(
      { branches: getConditionBranches(node.config) },
      branchId,
      connection.target,
    );
    const branches = getConditionBranches(config);
    return {
      ...node,
      config: { ...node.config, branches },
      next_nodes: branches
        .map((b) => b.target_node_id)
        .filter((id): id is string => !!id),
    };
  });
  emit("update:nodes", updatedNodes);
}

function handleEdgeDelete(payload: { sourceId: string; targetId: string; branchId?: string }) {
  const sourceNode = props.nodes.find((n) => n.id === payload.sourceId);
  if (!sourceNode || sourceNode.node_type !== "condition" || !payload.branchId) return;

  const updatedNodes = props.nodes.map((node) => {
    if (node.id !== sourceNode.id) return node;
    const config = setConditionBranchTarget(
      { branches: getConditionBranches(node.config) },
      payload.branchId!,
      undefined,
    );
    const branches = getConditionBranches(config);
    return {
      ...node,
      config: { ...node.config, branches },
      next_nodes: branches.map((b) => b.target_node_id).filter((id): id is string => !!id),
    };
  });
  emit("update:nodes", updatedNodes);
}

function handleAddBefore(nodeId: string, nodeType: string) {
  emit("add-node", { position: "before", nodeType, targetId: nodeId });
}

function handleAddAfter(nodeId: string, nodeType: string) {
  emit("add-node", { position: "after", nodeType, targetId: nodeId });
}

function handleAddFirstNode(nodeType: string) {
  emit("add-node", { position: "first", nodeType });
}

function handleDeleteNode(nodeId: string) {
  emit("delete-node", nodeId);
}

const addableNodeTypes = ADDABLE_NODE_TYPES;

function fitView() {
  vueFlowRef.value?.fitView();
}

function zoomIn() {
  vueFlowRef.value?.zoomIn();
}

function zoomOut() {
  vueFlowRef.value?.zoomOut();
}

defineExpose({
  fitView,
  zoomIn,
  zoomOut,
});
</script>

<template>
  <div class="workflow-canvas">
    <VueFlow
      ref="vueFlowRef"
      :nodes="flowNodes"
      :edges="flowEdges"
      :nodes-draggable="!readonly"
      :nodes-connectable="!readonly"
      :elements-selectable="!readonly"
      :select-nodes-on-drag="false"
      :pan-on-drag="true"
      :zoom-on-scroll="true"
      :min-zoom="0.1"
      :max-zoom="2"
      fit-view-on-init
      @node-click="handleNodeClick"
      @node-drag-stop="handleNodeDragStop"
      @connect="handleConnect"
    >
      <template #node-workflow="nodeProps">
        <WorkflowNodeCard
          v-bind="nodeProps"
          @add-before="handleAddBefore(nodeProps.id, $event)"
          @add-after="handleAddAfter(nodeProps.id, $event)"
          @delete-node="handleDeleteNode(nodeProps.id)"
        />
      </template>
      <template #node-workflow-loop="nodeProps">
        <div class="workflow-loop-container" :class="{ selected: nodeProps.data?.node?.id === selectedNodeId }">
          <div class="loop-container-header">
            <el-icon class="loop-container-icon">
              <component :is="NODE_TYPE_ICON_MAP.loop" />
            </el-icon>
            <div class="loop-container-info">
              <div class="loop-container-name">{{ nodeProps.data?.node?.name }}</div>
              <div class="loop-container-summary">
                <span>依次处理每条数据</span>
                <span class="loop-separator">·</span>
                <span>{{ getLoopDataSourceLabel(nodeProps.data?.node) }}</span>
                <span class="loop-separator">·</span>
                <span>最多 {{ nodeProps.data?.node?.config?.max_iterations ?? 100 }} 次</span>
              </div>
            </div>
            <el-icon
              v-if="!readonly"
              class="loop-container-delete"
              title="删除循环节点"
              @click.stop="handleDeleteNode(nodeProps.data?.node?.id)">
              <Delete />
            </el-icon>
          </div>

          <div class="loop-container-body">
            <div
              v-for="child in getLoopBodyNodes(nodeProps.data?.node)"
              :key="child.id"
              class="loop-child-item"
              :class="{ selected: child.id === selectedNodeId }"
              @click.stop="handleSelectLoopChild(nodeProps.data?.node?.id, child.id)">
              <el-icon class="loop-child-icon">
                <component :is="getChildNodeIcon(child.node_type)" />
              </el-icon>
              <div class="loop-child-info">
                <div class="loop-child-name">{{ child.name }}</div>
                <div class="loop-child-type">{{ getChildNodeLabel(child.node_type) }}</div>
              </div>
              <el-icon
                v-if="!readonly"
                class="loop-child-delete"
                title="删除子节点"
                @click.stop="handleDeleteLoopChild(nodeProps.data?.node?.id, child.id)">
                <Delete />
              </el-icon>
            </div>

            <div v-if="getLoopBodyNodes(nodeProps.data?.node).length === 0" class="loop-body-empty">
              暂无循环体节点
            </div>

            <div v-if="!readonly" class="loop-container-add">
              <el-dropdown placement="bottom" trigger="click">
                <el-button type="primary" :icon="Plus" text size="small">
                  添加循环体节点
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item
                      v-for="item in loopBodyAllowedTypes"
                      :key="item.type"
                      @click="handleAddLoopChild(nodeProps.data?.node?.id, item.type)">
                      <el-icon><component :is="item.icon" /></el-icon>
                      <span>{{ item.label }}</span>
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </div>

          <Handle
            type="target"
            :position="Position.Top"
            :connectable="!readonly"
            class="node-handle-target"
          />
          <Handle
            type="source"
            :position="Position.Bottom"
            :connectable="false"
            class="node-handle-source"
          />
        </div>
      </template>
      <template #edge-workflow="edgeProps">
        <WorkflowEdgeWithAddButton
          v-bind="edgeProps"
          @edge-insert="handleEdgeInsert"
          @edge-delete="handleEdgeDelete"
        />
      </template>
      <Background />
      <Controls />
    </VueFlow>

    <div
      v-if="isEmpty && !readonly"
      class="canvas-empty-add"
    >
      <el-dropdown placement="bottom" trigger="click">
        <el-button type="primary" :icon="Plus">
          添加节点
        </el-button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item
              v-for="item in addableNodeTypes"
              :key="item.type"
              @click="handleAddFirstNode(item.type)"
            >
              <el-icon><component :is="item.icon" /></el-icon>
              <span>{{ item.label }}</span>
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.workflow-canvas {
  width: 100%;
  height: 100%;
  background-color: $bg-color;

  :deep(.vue-flow) {
    width: 100%;
    height: 100%;
  }

  :deep(.workflow-node) {
    &.selected {
      outline: 2px solid $primary-color;
    }
  }
}

.canvas-empty-add {
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  z-index: 10;
}

.workflow-loop-container {
  position: relative;
  width: 260px;
  background-color: rgba($primary-color, 0.04);
  border: 2px solid rgba($primary-color, 0.3);
  border-radius: $border-radius-md;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
  cursor: pointer;
  transition: all 0.2s;
  user-select: none;

  &:hover {
    border-color: rgba($primary-color, 0.6);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  }

  &.selected {
    border-color: $primary-color;
    box-shadow: 0 0 0 2px rgba($primary-color, 0.15);
  }
}

.loop-container-header {
  display: flex;
  align-items: flex-start;
  gap: $spacing-sm;
  padding: $spacing-sm $spacing-sm 0;
}

.loop-container-icon {
  flex-shrink: 0;
  font-size: 18px;
  color: $primary-color;
  margin-top: 2px;
}

.loop-container-info {
  flex: 1;
  min-width: 0;
}

.loop-container-name {
  font-size: $font-size-sm;
  font-weight: 600;
  color: $text-primary;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.loop-container-summary {
  font-size: 12px;
  color: $text-secondary;
  margin-top: 2px;
  display: flex;
  flex-wrap: wrap;
  gap: 2px;

  .loop-separator {
    color: $text-disabled;
  }
}

.loop-container-delete {
  flex-shrink: 0;
  font-size: 14px;
  color: $text-secondary;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.2s, color 0.2s;

  .workflow-loop-container:hover & {
    opacity: 1;
  }

  &:hover {
    color: $error-color;
  }
}

.loop-container-body {
  padding: $spacing-sm;
  display: flex;
  flex-direction: column;
  gap: $spacing-xs;
}

.loop-child-item {
  display: flex;
  align-items: center;
  gap: $spacing-xs;
  padding: $spacing-xs $spacing-sm;
  background-color: white;
  border: 1px solid $border-color;
  border-radius: $border-radius-sm;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    border-color: rgba($primary-color, 0.4);
  }

  &.selected {
    border-color: $primary-color;
    background-color: rgba($primary-color, 0.08);
  }
}

.loop-child-icon {
  flex-shrink: 0;
  font-size: 14px;
  color: $primary-color;
}

.loop-child-info {
  flex: 1;
  min-width: 0;
}

.loop-child-name {
  font-size: 12px;
  font-weight: 500;
  color: $text-primary;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.loop-child-type {
  font-size: 11px;
  color: $text-secondary;
}

.loop-child-delete {
  flex-shrink: 0;
  font-size: 12px;
  color: $text-secondary;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.2s, color 0.2s;

  .loop-child-item:hover & {
    opacity: 1;
  }

  &:hover {
    color: $error-color;
  }
}

.loop-body-empty {
  font-size: 12px;
  color: $text-secondary;
  text-align: center;
  padding: $spacing-sm;
  background-color: white;
  border: 1px dashed $border-color;
  border-radius: $border-radius-sm;
}

.loop-container-add {
  display: flex;
  justify-content: center;
  margin-top: $spacing-xs;
}
</style>
