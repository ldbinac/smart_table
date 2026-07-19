<script setup lang="ts">
import { computed } from "vue";
import { Handle, Position } from "@vue-flow/core";
import { CircleCheck, Delete } from "@element-plus/icons-vue";
import type { WorkflowNode, ConditionBranch } from "@/types/workflow";
import { getConditionBranches } from "@/utils/conditionBranch";
import {
  ALL_NODE_TYPES,
  ADDABLE_NODE_TYPES,
  NODE_TYPE_ICON_MAP,
  getNodeLabel,
} from "@/utils/workflowNodeType";

const nodeTypeOptions = ALL_NODE_TYPES;

const iconMap = NODE_TYPE_ICON_MAP;

interface Props {
  id: string;
  type: string;
  data: { node: WorkflowNode; selected?: boolean; readonly?: boolean };
  selected?: boolean;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  (e: "add-before", nodeType: string): void;
  (e: "add-after", nodeType: string): void;
  (e: "delete-node"): void;
}>();

const node = computed(() => props.data.node);
const isSelected = computed(() => props.data.selected ?? props.selected ?? false);
const isCondition = computed(() => node.value.node_type === "condition");
const isReadonly = computed(() => props.data.readonly ?? false);

const branches = computed<ConditionBranch[]>(() =>
  isCondition.value ? getConditionBranches(node.value.config) : [],
);

const nodeIcon = computed(() => iconMap[node.value.node_type] ?? CircleCheck);

function getBranchHandleStyle(index: number, total: number) {
  const handleRange = 40;
  const step = total > 1 ? handleRange / (total - 1) : 0;
  const top = total > 1 ? 16 + index * step : 50;
  return {
    top: `${top}px`,
    right: "-6px",
    width: "10px",
    height: "10px",
    background: "#2d7cfc",
    border: "2px solid #fff",
  };
}

const nodeTypeLabel = computed(() => {
  return getNodeLabel(node.value.node_type);
});

const addableNodeTypes = ADDABLE_NODE_TYPES;

function handleAddBefore(type: string) {
  emit("add-before", type);
}

function handleAddAfter(type: string) {
  emit("add-after", type);
}

function handleDelete() {
  emit("delete-node");
}
</script>

<template>
  <div class="workflow-node-card-wrapper">
    <div
      v-if="!isReadonly"
      class="node-add-button node-add-before"
      title="在前面添加节点"
    >
      <el-dropdown placement="top" trigger="click">
        <div class="add-button-inner">
          <el-icon><Plus /></el-icon>
        </div>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item
              v-for="item in addableNodeTypes"
              :key="item.type"
              @click="handleAddBefore(item.type)"
            >
              <el-icon><component :is="item.icon" /></el-icon>
              <span>{{ item.label }}</span>
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>

    <div
      class="workflow-node-card"
      :class="{
        'is-selected': isSelected,
        'is-condition': isCondition,
      }"
    >
      <div class="node-card-header">
        <el-icon class="node-type-icon">
          <component :is="nodeIcon" />
        </el-icon>
        <span class="node-name">{{ node.name }}</span>
        <el-icon
          v-if="!isReadonly"
          class="node-delete-btn"
          title="删除节点"
          @click.stop="handleDelete">
          <Delete />
        </el-icon>
      </div>
      <div class="node-card-footer">
        <span class="node-type-label">{{ nodeTypeLabel }}</span>
        <el-icon v-if="isCondition" class="condition-branch-icon"><Share /></el-icon>
      </div>

      <Handle
        type="target"
        :position="Position.Top"
        :connectable="!isReadonly"
        class="node-handle-target"
      />
      <Handle
        v-if="!isCondition"
        type="source"
        :position="Position.Bottom"
        :connectable="false"
        class="node-handle-source"
      />
      <Handle
        v-for="(branch, index) in branches"
        :key="branch.id"
        type="source"
        :position="Position.Right"
        :id="branch.id"
        :connectable="!isReadonly"
        :style="getBranchHandleStyle(index, branches.length)"
      />
    </div>

    <div
      v-if="!isReadonly"
      class="node-add-button node-add-after"
      title="在后面添加节点"
    >
      <el-dropdown placement="bottom" trigger="click">
        <div class="add-button-inner">
          <el-icon><Plus /></el-icon>
        </div>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item
              v-for="item in addableNodeTypes"
              :key="item.type"
              @click="handleAddAfter(item.type)"
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
.workflow-node-card-wrapper {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.node-add-button {
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s;
  z-index: 1;

  .workflow-node-card-wrapper:hover & {
    opacity: 1;
  }
}

.add-button-inner {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  background-color: white;
  border: 1px solid $border-color;
  color: $text-secondary;
  cursor: pointer;
  font-size: 12px;
  transition: all 0.2s;

  &:hover {
    border-color: $primary-color;
    color: $primary-color;
    box-shadow: 0 1px 4px rgba(0, 0, 0, 0.08);
  }
}

.node-add-before {
  margin-bottom: -$spacing-xs;
}

.node-add-after {
  margin-top: -$spacing-xs;
}

.workflow-node-card {
  position: relative;
  width: 160px;
  padding: $spacing-sm;
  background-color: white;
  border: 1px solid $border-color;
  border-radius: $border-radius-md;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.04);
  cursor: pointer;
  transition: all 0.2s;
  user-select: none;

  &:hover {
    border-color: rgba($primary-color, 0.4);
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  }

  &.is-selected {
    border-color: $primary-color;
    box-shadow: 0 0 0 2px rgba($primary-color, 0.15);
  }

  &.is-condition {
    background-color: rgba($warning-color, 0.06);
    border-style: dashed;

    &:hover {
      border-color: rgba($warning-color, 0.6);
    }

    &.is-selected {
      border-color: $warning-color;
      box-shadow: 0 0 0 2px rgba($warning-color, 0.15);
    }
  }
}

.node-card-header {
  display: flex;
  align-items: center;
  gap: $spacing-xs;
  margin-bottom: $spacing-xs;
}

.node-type-icon {
  flex-shrink: 0;
  font-size: 18px;
  color: $primary-color;
}

.is-condition .node-type-icon {
  color: $warning-color;
}

.node-name {
  flex: 1;
  min-width: 0;
  font-size: $font-size-sm;
  font-weight: 500;
  color: $text-primary;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.node-delete-btn {
  flex-shrink: 0;
  font-size: 14px;
  color: $text-secondary;
  cursor: pointer;
  opacity: 0;
  transition: opacity 0.2s, color 0.2s;

  .workflow-node-card:hover & {
    opacity: 1;
  }

  &:hover {
    color: $error-color;
  }
}

.node-card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: $spacing-xs;
}

.node-type-label {
  font-size: 12px;
  color: $text-secondary;
}

.condition-branch-icon {
  font-size: 12px;
  color: $warning-color;
}
</style>
