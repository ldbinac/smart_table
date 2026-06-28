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
  Message,
  Link,
  Delete,
  Rank,
  Timer,
  CopyDocument,
} from "@element-plus/icons-vue";
import WorkflowNodeConfig from "./WorkflowNodeConfig.vue";
import WorkflowTriggerConfig from "./WorkflowTriggerConfig.vue";

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
const nodeListRef = ref<HTMLElement | null>(null);
const triggerConfigRef = ref<InstanceType<typeof WorkflowTriggerConfig> | null>(null);
let sortableInstance: Sortable | null = null;
let isUpdatingNodesFromParent = false;
let isUpdatingTriggerFromParent = false;

const selectedNode = computed(() =>
  localNodes.value.find((n) => n.id === selectedNodeId.value) ?? null,
);

watch(
  () => props.nodes,
  (newNodes) => {
    isUpdatingNodesFromParent = true;
    localNodes.value = newNodes.map((n) => ({ ...n, config: cloneConfig(n.config) }));
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

function cloneConfig(config: Record<string, unknown>): Record<string, unknown> {
  return JSON.parse(JSON.stringify(config));
}

function generateId(): string {
  return `node_${Date.now()}_${Math.random().toString(36).slice(2, 9)}`;
}

const nodeTypeMenu = [
  { type: "approval" as const, label: "审批节点", icon: CircleCheck },
  { type: "condition" as const, label: "条件节点", icon: Share },
  { type: "update_record" as const, label: "更新记录", icon: EditPen },
  { type: "create_record" as const, label: "创建记录", icon: Plus },
  { type: "send_email" as const, label: "发送邮件", icon: Message },
  { type: "webhook" as const, label: "Webhook", icon: Link },
];

const nodeIconMap: Record<string, typeof CircleCheck> = {
  approval: CircleCheck,
  condition: Share,
  update_record: EditPen,
  create_record: Plus,
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

function addNode(type: WorkflowNodeType) {
  const newNode: WorkflowNode = {
    id: generateId(),
    workflow_id: props.workflow.id,
    node_type: type,
    name: `${getNodeLabel(type)} ${localNodes.value.length + 1}`,
    config: {},
    order: localNodes.value.length,
    next_nodes: [],
  };
  localNodes.value = [...localNodes.value, newNode];
  selectedNodeId.value = newNode.id;
}

function removeNode(nodeId: string) {
  localNodes.value = localNodes.value.filter((n) => n.id !== nodeId);
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
      localNodes.value = list.map((node, index) => ({ ...node, order: index }));
    },
  });
}

onMounted(() => {
  nextTick(() => initSortable());
});

onUnmounted(() => {
  sortableInstance?.destroy();
  sortableInstance = null;
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
</script>

<template>
  <div v-loading="loading" class="workflow-designer" :class="{ 'is-loading': loading }">
    <div class="designer-layout">
      <!-- 左侧：触发器 + 节点列表 -->
      <div class="designer-left">
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
      </div>

      <!-- 右侧：节点配置 -->
      <div class="designer-right">
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
  width: 360px;
  min-width: 320px;
  display: flex;
  flex-direction: column;
  border-right: 1px solid $border-color;
  background-color: white;
  overflow: hidden;
}

.designer-right {
  flex: 1;
  display: flex;
  flex-direction: column;
  background-color: white;
  overflow: hidden;
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
