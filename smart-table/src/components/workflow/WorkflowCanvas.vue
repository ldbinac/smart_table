<script setup lang="ts">
import { computed, ref } from "vue";
import { VueFlow } from "@vue-flow/core";
import { Background } from "@vue-flow/background";
import { Controls } from "@vue-flow/controls";
import { Plus } from "@element-plus/icons-vue";
import type {
  Node as FlowNode,
  Edge as FlowEdge,
  NodeMouseEvent,
  NodeDragEvent,
} from "@vue-flow/core";
import type { WorkflowNode } from "@/types/workflow";
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
    payload: { position: "before" | "after" | "first"; nodeType: string; targetId?: string },
  ): void;
  (e: "delete-node", nodeId: string): void;
}>();

const vueFlowRef = ref<InstanceType<typeof VueFlow> | null>(null);

const isEmpty = computed(() => props.nodes.length === 0);

const flowNodes = computed<FlowNode[]>(() =>
  props.nodes.map((node) => ({
    id: node.id,
    type: "workflow",
    position: node.ui_layout ?? { x: 0, y: 0 },
    data: { node, readonly: props.readonly },
    selectable: !props.readonly,
    draggable: !props.readonly,
    class: {
      "workflow-node": true,
      selected: node.id === props.selectedNodeId,
    },
  })),
);

const flowEdges = computed<FlowEdge[]>(() => {
  const edges: FlowEdge[] = [];
  props.nodes.forEach((node) => {
    node.next_nodes.forEach((targetId) => {
      edges.push({
        id: `e-${node.id}-${targetId}`,
        source: node.id,
        target: targetId,
        type: "workflow",
        label: node.node_type === "condition" ? "满足条件" : undefined,
        markerEnd: "arrowclosed",
        data: {
          readonly: props.readonly,
          sourceNodeType: node.node_type,
        },
      });
    });
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

const addableNodeTypes = [
  { type: "update_record", label: "更新记录" },
  { type: "create_record", label: "创建记录" },
  { type: "webhook", label: "Webhook" },
  { type: "condition", label: "条件节点" },
];

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
      :nodes-connectable="false"
      :elements-selectable="!readonly"
      :select-nodes-on-drag="false"
      :pan-on-drag="true"
      :zoom-on-scroll="true"
      :min-zoom="0.1"
      :max-zoom="2"
      fit-view-on-init
      @node-click="handleNodeClick"
      @node-drag-stop="handleNodeDragStop"
    >
      <template #node-workflow="nodeProps">
        <WorkflowNodeCard
          v-bind="nodeProps"
          @add-before="handleAddBefore(nodeProps.id, $event)"
          @add-after="handleAddAfter(nodeProps.id, $event)"
          @delete-node="handleDeleteNode(nodeProps.id)"
        />
      </template>
      <template #edge-workflow="edgeProps">
        <WorkflowEdgeWithAddButton
          v-bind="edgeProps"
          @edge-insert="handleEdgeInsert"
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
</style>
