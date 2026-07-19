<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import type { FieldEntity, TableEntity } from "@/db/schema";
import type {
  WorkflowNode,
  WebhookConfig,
  WebhookMethod,
  ConditionBranch,
  ConditionItem,
  ConditionNodeConfig,
} from "@/types/workflow";
import { FilterOperator } from "@/types/filters";
import type { FilterOperatorValue } from "@/types/filters";
import {
  getOperatorsForFieldType,
  OPERATOR_LABELS,
  operatorRequiresValue,
} from "@/utils/filter";
import { FieldType } from "@/types/fields";
import type { FieldTypeValue } from "@/types/fields";
import { fieldService } from "@/db/services/fieldService";
import {
  normalizeWorkflowNode,
  isValidWorkflowVariableName,
} from "@/utils/workflow";
import { getNodeLabel } from "@/utils/workflowNodeType";
import {
  normalizeConditionConfig,
  addConditionBranch,
  addDefaultBranch,
  hasDefaultBranch as checkDefaultBranch,
  removeConditionBranch,
  updateConditionBranch,
} from "@/utils/conditionBranch";
import FieldValueInput from "@/components/fields/FieldValueInput.vue";
import {
  Delete,
  Plus,
  EditPen,
  Close,
  InfoFilled,
} from "@element-plus/icons-vue";

interface Props {
  node: WorkflowNode;
  fields: FieldEntity[];
  tables?: TableEntity[];
  webhooks?: WebhookConfig[];
  readonly?: boolean;
}

const props = defineProps<Props>();
const emit = defineEmits<{
  (e: "update:node", node: WorkflowNode): void;
}>();

// ==================== 通用配置辅助 ====================

function migrateConditionConfig(config: Record<string, unknown>): Record<string, unknown> {
  const normalized = normalizeConditionConfig(config);
  const migrated: Record<string, unknown> = { ...config, branches: normalized.branches };
  delete migrated.conditions;
  delete migrated.conjunction;
  return migrated;
}

function buildLocalNode(node: WorkflowNode): WorkflowNode {
  const normalized = normalizeWorkflowNode(node);
  const config = cloneConfig(normalized.config);
  if (normalized.node_type === "condition") {
    return { ...normalized, config: migrateConditionConfig(config) };
  }
  return { ...normalized, config };
}

const localNode = ref<WorkflowNode>(buildLocalNode(props.node));
let isUpdatingFromParent = false;

watch(
  () => props.node,
  (newNode) => {
    isUpdatingFromParent = true;
    localNode.value = buildLocalNode(newNode);
    nextTick(() => {
      isUpdatingFromParent = false;
    });
  },
  { deep: true },
);

watch(
  localNode,
  (newNode) => {
    if (isUpdatingFromParent) return;
    emit("update:node", { ...newNode, config: cloneConfig(newNode.config) });
  },
  { deep: true },
);

function cloneConfig(config: Record<string, unknown>): Record<string, unknown> {
  return JSON.parse(JSON.stringify(config));
}

// ==================== 节点名称编辑 ====================

const isEditingName = ref(false);
const editingName = ref("");
const nameInputRef = ref<any>(null);

function startEditName() {
  if (props.readonly) return;
  editingName.value = localNode.value.name;
  isEditingName.value = true;
  nextTick(() => {
    const inputEl = nameInputRef.value?.$el?.querySelector?.('input') ?? nameInputRef.value;
    if (inputEl && typeof inputEl.focus === 'function') {
      inputEl.focus();
    }
  });
}

function saveName() {
  const trimmed = editingName.value.trim();
  if (trimmed) {
    localNode.value = { ...localNode.value, name: trimmed };
  }
  isEditingName.value = false;
}

function cancelEditName() {
  isEditingName.value = false;
}

function handleNameKeydown(event: Event | KeyboardEvent) {
  if (event instanceof KeyboardEvent) {
    if (event.key === "Enter") {
      saveName();
    } else if (event.key === "Escape") {
      cancelEditName();
    }
  }
}

function configValue<T>(key: string, defaultValue: T): T {
  const value = localNode.value.config[key];
  return value !== undefined ? (value as T) : defaultValue;
}

function setConfigValue(key: string, value: unknown) {
  localNode.value.config[key] = value;
}

const availableTables = computed(() => props.tables ?? []);
const availableWebhooks = computed(() => {
  const all = props.webhooks ?? [];
  const currentId = configValue<string | undefined>("webhook_id", undefined);
  return all.filter(
    (w) => w.is_active || (currentId !== undefined && w.id === currentId),
  );
});

// ==================== 条件节点配置 ====================

type ConjunctionValue = "and" | "or";

const CONJUNCTION_OPTIONS: { value: ConjunctionValue; label: string }[] = [
  { value: "and", label: "满足全部条件" },
  { value: "or", label: "满足任一条件" },
];

const conditionConfig = computed<ConditionNodeConfig>({
  get: () => normalizeConditionConfig(localNode.value.config),
  set: (value) => {
    localNode.value.config = { ...localNode.value.config, branches: value.branches };
  },
});

const branches = computed(() => conditionConfig.value.branches);
const activeBranchId = ref<string | null>(null);

function ensureActiveBranch() {
  const list = branches.value;
  if (!activeBranchId.value || !list.some((b) => b.id === activeBranchId.value)) {
    activeBranchId.value = list[0]?.id ?? null;
  }
}

watch(branches, ensureActiveBranch, { immediate: true });

const activeBranch = computed<ConditionBranch | undefined>(
  () => branches.value.find((b) => b.id === activeBranchId.value),
);

function getConjunctionLabel(value: ConjunctionValue) {
  return CONJUNCTION_OPTIONS.find((opt) => opt.value === value)?.label ?? value;
}

function addBranch() {
  const { config, branch } = addConditionBranch(conditionConfig.value);
  conditionConfig.value = config;
  activeBranchId.value = branch.id;
}

function addDefault() {
  const { config, branch } = addDefaultBranch(conditionConfig.value);
  conditionConfig.value = config;
  activeBranchId.value = branch.id;
}

function handleAddBranchCommand(command: string | number) {
  if (command === "condition") addBranch();
  else if (command === "default") addDefault();
}

const hasDefaultBranch = computed(() => checkDefaultBranch(conditionConfig.value));

function removeBranch(branchId: string) {
  if (branches.value.length <= 1) return;
  conditionConfig.value = removeConditionBranch(conditionConfig.value, branchId);
}

function updateBranchName(branchId: string, name: string) {
  conditionConfig.value = updateConditionBranch(conditionConfig.value, branchId, (branch) => ({
    ...branch,
    name: name.trim() || branch.name,
  }));
}

function updateBranchConjunction(branchId: string, value: ConjunctionValue) {
  conditionConfig.value = updateConditionBranch(conditionConfig.value, branchId, (branch) => ({
    ...branch,
    conjunction: value,
  }));
}

function addCondition(branchId: string) {
  const firstField = props.fields[0];
  const defaultOperator = firstField
    ? getOperatorsForFieldType(firstField.type)[0] ?? FilterOperator.EQUALS
    : FilterOperator.EQUALS;
  conditionConfig.value = updateConditionBranch(conditionConfig.value, branchId, (branch) => ({
    ...branch,
    conditions: [
      ...branch.conditions,
      {
        field_id: firstField?.id ?? "",
        operator: defaultOperator,
        value: undefined,
      },
    ],
  }));
}

function removeCondition(branchId: string, index: number) {
  conditionConfig.value = updateConditionBranch(conditionConfig.value, branchId, (branch) => {
    const conditions = [...branch.conditions];
    conditions.splice(index, 1);
    return { ...branch, conditions };
  });
}

function getFieldById(fieldId: string) {
  return props.fields.find((f) => f.id === fieldId);
}

function getTargetFieldById(fieldId: string) {
  return targetTableFields.value.find((f) => f.id === fieldId);
}

const STATIC_ONLY_FIELD_TYPES: FieldTypeValue[] = [
  FieldType.SINGLE_SELECT,
  FieldType.MULTI_SELECT,
  FieldType.RATING,
  FieldType.PROGRESS,
  FieldType.CHECKBOX,
];

function isStaticOnlyFieldType(fieldType: string): boolean {
  return STATIC_ONLY_FIELD_TYPES.includes(fieldType as FieldTypeValue);
}

function getOperatorOptions(fieldType: string) {
  return getOperatorsForFieldType(fieldType).map((op) => ({
    value: op,
    label: OPERATOR_LABELS[op],
  }));
}

function onConditionFieldChange(branchId: string, index: number, fieldId: string) {
  const field = getFieldById(fieldId);
  const operators = field ? getOperatorsForFieldType(field.type) : [];
  conditionConfig.value = updateConditionBranch(conditionConfig.value, branchId, (branch) => {
    const conditions = [...branch.conditions];
    conditions[index] = {
      field_id: fieldId,
      operator: operators[0] ?? FilterOperator.EQUALS,
      value: undefined,
    };
    return { ...branch, conditions };
  });
}

function onConditionOperatorChange(
  branchId: string,
  index: number,
  operator: FilterOperatorValue,
) {
  conditionConfig.value = updateConditionBranch(conditionConfig.value, branchId, (branch) => {
    const conditions = [...branch.conditions];
    conditions[index] = { ...conditions[index], operator };
    if (!operatorRequiresValue(operator)) {
      conditions[index].value = undefined;
    }
    return { ...branch, conditions };
  });
}

function onConditionValueChange(branchId: string, index: number, value: unknown) {
  conditionConfig.value = updateConditionBranch(conditionConfig.value, branchId, (branch) => {
    const conditions = [...branch.conditions];
    conditions[index] = { ...conditions[index], value };
    return { ...branch, conditions };
  });
}

function renderConditionValue(condition: ConditionItem): string {
  if (!operatorRequiresValue(condition.operator)) return "";
  if (condition.value === undefined || condition.value === null) return "空";

  const field = getFieldById(condition.field_id);
  const fieldType = field?.type;
  const isSelectLike =
    fieldType === FieldType.SINGLE_SELECT || fieldType === FieldType.MULTI_SELECT;
  const rawOptions = field?.options?.options ?? field?.options?.choices;
  const options = Array.isArray(rawOptions) ? (rawOptions as Array<{ id: string; name: string }>) : undefined;

  if (isSelectLike && options && options.length > 0) {
    const values = Array.isArray(condition.value) ? condition.value : [condition.value];
    const labels = values
      .map((val) => {
        const option = options.find((opt: { id: string; name: string }) => opt.id === val);
        return option ? `${option.name} (${option.id})` : String(val);
      })
      .filter(Boolean);
    return labels.length > 0 ? labels.join(", ") : String(condition.value);
  }

  if (Array.isArray(condition.value)) return condition.value.join(", ");
  return String(condition.value);
}

function isExpressionTemplate(value: string | undefined): boolean {
  return typeof value === "string" && value.includes("{{") && value.includes("}}");
}

// ==================== 更新记录节点配置 ====================

interface FieldUpdateMapping {
  field_id: string;
  value_template: string;
}

const updateMappings = computed<FieldUpdateMapping[]>({
  get: () => configValue<FieldUpdateMapping[]>("updates", []),
  set: (value) => setConfigValue("updates", value),
});

function addUpdateMapping() {
  updateMappings.value = [
    ...updateMappings.value,
    { field_id: props.fields[0]?.id ?? "", value_template: "" },
  ];
}

function removeUpdateMapping(index: number) {
  const list = [...updateMappings.value];
  list.splice(index, 1);
  updateMappings.value = list;
}

const useExpressionForUpdate = ref<Record<number, boolean>>({});

function initUpdateModeState() {
  updateMappings.value.forEach((mapping, index) => {
    if (useExpressionForUpdate.value[index] === undefined) {
      useExpressionForUpdate.value[index] = isExpressionTemplate(mapping.value_template);
    }
  });
}

watch(updateMappings, initUpdateModeState, { immediate: true });

function updateMappingFieldId(index: number, fieldId: string) {
  const list = [...updateMappings.value];
  list[index] = { field_id: fieldId, value_template: "" };
  updateMappings.value = list;
  useExpressionForUpdate.value[index] = false;
}

function updateMappingTemplate(index: number, template: string) {
  const list = [...updateMappings.value];
  list[index] = { ...list[index], value_template: template };
  updateMappings.value = list;
}

function onUpdateStaticValueChange(index: number, value: unknown) {
  const stringValue = value === null || value === undefined ? "" : String(value);
  updateMappingTemplate(index, stringValue);
}

function toggleExpressionForUpdate(index: number, value: boolean) {
  useExpressionForUpdate.value[index] = value;
}

// ==================== 创建记录节点配置 ====================

interface FieldMapping {
  target_field_id: string;
  source_field_id?: string;
  value_template?: string;
}

const createRecordTargetTableId = computed({
  get: () => configValue<string>("target_table_id", ""),
  set: (value) => setConfigValue("target_table_id", value),
});

function onCreateRecordTargetTableChange(tableId: string) {
  createRecordTargetTableId.value = tableId;
  createRecordMappings.value = [];
  // 清空表达式模式缓存，避免索引错位
  useExpressionForCreate.value = {};
}

const createRecordMappings = computed<FieldMapping[]>({
  get: () => configValue<FieldMapping[]>("field_mappings", []),
  set: (value) => setConfigValue("field_mappings", value),
});

function addCreateMapping() {
  createRecordMappings.value = [
    ...createRecordMappings.value,
    { target_field_id: "", source_field_id: "", value_template: "" },
  ];
}

function removeCreateMapping(index: number) {
  const list = [...createRecordMappings.value];
  list.splice(index, 1);
  createRecordMappings.value = list;
}

const useExpressionForCreate = ref<Record<number, boolean>>({});

function initCreateModeState() {
  createRecordMappings.value.forEach((mapping, index) => {
    if (useExpressionForCreate.value[index] === undefined) {
      useExpressionForCreate.value[index] = isExpressionTemplate(mapping.value_template);
    }
  });
}

watch(createRecordMappings, initCreateModeState, { immediate: true });

function updateCreateMapping(index: number, patch: Partial<FieldMapping>) {
  const list = [...createRecordMappings.value];
  const shouldClearValue = "target_field_id" in patch;
  list[index] = {
    ...list[index],
    ...patch,
    ...(shouldClearValue ? { value_template: "" } : {}),
  };
  createRecordMappings.value = list;
  if (shouldClearValue) {
    useExpressionForCreate.value[index] = false;
  }
}

function updateCreateValueTemplate(index: number, template: string) {
  updateCreateMapping(index, { value_template: template });
}

function onCreateStaticValueChange(index: number, value: unknown) {
  const stringValue = value === null || value === undefined ? "" : String(value);
  updateCreateValueTemplate(index, stringValue);
}

function toggleExpressionForCreate(index: number, value: boolean) {
  useExpressionForCreate.value[index] = value;
}

function onCreateSourceFieldChange(index: number, sourceFieldId: string | undefined) {
  updateCreateMapping(index, { source_field_id: sourceFieldId });
  if (sourceFieldId) {
    useExpressionForCreate.value[index] = true;
    updateCreateValueTemplate(index, `{{trigger.record.${sourceFieldId}}}`);
  }
}

const targetFields = ref<FieldEntity[]>([]);
const isLoadingTargetFields = ref(false);

async function loadTargetFields(tableId: string) {
  if (!tableId) {
    targetFields.value = [];
    return;
  }
  isLoadingTargetFields.value = true;
  try {
    targetFields.value = await fieldService.getFieldsByTable(tableId);
  } finally {
    isLoadingTargetFields.value = false;
  }
}

watch(
  createRecordTargetTableId,
  (newTableId) => {
    // 仅负责加载目标表字段；清空字段映射由用户主动切换目标表触发 @change 处理，
    // 避免 props 更新（如切换节点）时误清空已有映射。
    loadTargetFields(newTableId);
  },
  { immediate: true },
);

const targetTableFields = computed(() => targetFields.value);

// ==================== 发送邮件节点配置 ====================

const emailRecipientType = computed({
  get: () => configValue<"field" | "fixed">("recipient_type", "field"),
  set: (value) => setConfigValue("recipient_type", value),
});

const emailRecipientValue = computed({
  get: () => configValue<string | string[]>("recipient_value", []),
  set: (value) => setConfigValue("recipient_value", value),
});

const emailContentMode = computed({
  get: () => configValue<"custom" | "template">("content_mode", "custom"),
  set: (value) => setConfigValue("content_mode", value),
});

const emailSubject = computed({
  get: () => configValue<string>("subject", ""),
  set: (value) => setConfigValue("subject", value),
});

const emailBody = computed({
  get: () => configValue<string>("body", ""),
  set: (value) => setConfigValue("body", value),
});

const emailTemplateId = computed({
  get: () => configValue<string | undefined>("email_template_id", undefined),
  set: (value) => setConfigValue("email_template_id", value),
});

const emailFields = computed(() =>
  props.fields.filter((f) => f.type === "email" || f.type === "member" || f.type === "collaborator"),
);

const emailTemplates = ref<Array<{ id: string; name: string; template_key: string }>>([]);

async function loadEmailTemplates() {
  try {
    const { default: api } = await import("@/utils/api");
    const data = await api.get<Array<{ id: string; name: string; template_key: string }>>("/admin/email/templates/list");
    emailTemplates.value = Array.isArray(data) ? data : [];
  } catch {
    emailTemplates.value = [];
  }
}

watch(
  () => props.node.node_type,
  (type) => {
    if (type === "send_email") loadEmailTemplates();
  },
  { immediate: true },
);

// ==================== 查找记录节点配置 ====================

const findRecordsTargetTableId = computed({
  get: () => configValue<string>("target_table_id", (props.node as any).workflow?.table_id ?? ""),
  set: (value) => setConfigValue("target_table_id", value),
});

function onFindRecordsTargetTableChange(tableId: string) {
  findRecordsTargetTableId.value = tableId;
  findRecordsConditions.value = [];
  findRecordsSortFieldId.value = "";
}

const findRecordsSortFieldId = computed({
  get: () => configValue<string>("sort_field_id", ""),
  set: (value) => setConfigValue("sort_field_id", value),
});

const findRecordsSortDirection = computed<"asc" | "desc">({
  get: () => configValue<"asc" | "desc">("sort_direction", "asc"),
  set: (value) => setConfigValue("sort_direction", value),
});

const findRecordsLimit = computed({
  get: () => configValue<number>("limit", 100),
  set: (value) => setConfigValue("limit", Math.min(Math.max(value, 1), 1000)),
});

const findRecordsVariable = computed({
  get: () => configValue<string>("result_variable", "records"),
  set: (value) => setConfigValue("result_variable", value),
});

const findRecordsEmptyAction = computed<"continue" | "stop">({
  get: () => configValue<"continue" | "stop">("empty_result_action", "continue"),
  set: (value) => setConfigValue("empty_result_action", value),
});

const findRecordsConditions = computed<ConditionItem[]>({
  get: () => configValue<ConditionItem[]>("conditions", []),
  set: (value) => setConfigValue("conditions", value),
});

const findRecordsConjunction = computed<ConjunctionValue>({
  get: () => configValue<ConjunctionValue>("conjunction", "and"),
  set: (value) => setConfigValue("conjunction", value),
});

const isFindRecordsVariableValid = computed(() =>
  isValidWorkflowVariableName(findRecordsVariable.value),
);

function addFindRecordsCondition() {
  const firstField = targetTableFields.value[0];
  const defaultOperator = firstField
    ? getOperatorsForFieldType(firstField.type)[0] ?? FilterOperator.EQUALS
    : FilterOperator.EQUALS;
  findRecordsConditions.value = [
    ...findRecordsConditions.value,
    {
      field_id: firstField?.id ?? "",
      operator: defaultOperator,
      value: undefined,
    },
  ];
}

function removeFindRecordsCondition(index: number) {
  const list = [...findRecordsConditions.value];
  list.splice(index, 1);
  findRecordsConditions.value = list;
}

function onFindRecordsConditionFieldChange(index: number, fieldId: string) {
  const field = getTargetFieldById(fieldId);
  const operators = field ? getOperatorsForFieldType(field.type) : [];
  const list = [...findRecordsConditions.value];
  list[index] = {
    field_id: fieldId,
    operator: operators[0] ?? FilterOperator.EQUALS,
    value: undefined,
  };
  findRecordsConditions.value = list;
}

function onFindRecordsConditionOperatorChange(index: number, operator: FilterOperatorValue) {
  const list = [...findRecordsConditions.value];
  list[index] = { ...list[index], operator };
  if (!operatorRequiresValue(operator)) {
    list[index].value = undefined;
  }
  findRecordsConditions.value = list;
}

function onFindRecordsConditionValueChange(index: number, value: unknown) {
  const list = [...findRecordsConditions.value];
  list[index] = { ...list[index], value };
  findRecordsConditions.value = list;
}

watch(
  findRecordsTargetTableId,
  (newTableId) => {
    loadTargetFields(newTableId);
  },
  { immediate: true },
);

// ==================== Webhook 节点配置 ====================

const webhookMethods: { value: WebhookMethod; label: string }[] = [
  { value: "GET", label: "GET" },
  { value: "POST", label: "POST" },
  { value: "PUT", label: "PUT" },
];

const isNewWebhookNode = computed(() => (props.node.id ?? "").startsWith("node_"));

const webhookMode = computed({
  get: () => configValue<"existing" | "inline">("webhook_mode", "existing"),
  set: (value) => setConfigValue("webhook_mode", value),
});

const selectedWebhookId = computed({
  get: () => configValue<string | undefined>("webhook_id", undefined),
  set: (value) => setConfigValue("webhook_id", value),
});

const inlineWebhook = computed({
  get: () =>
    configValue<{
      name: string;
      url: string;
      method: WebhookMethod;
      headers: Record<string, string>;
      body_template?: string;
    }>("inline_webhook", {
      name: "",
      url: "",
      method: "POST",
      headers: {},
      body_template: "",
    }),
  set: (value) => setConfigValue("inline_webhook", value),
});

function updateInlineWebhook(patch: Partial<typeof inlineWebhook.value>) {
  inlineWebhook.value = { ...inlineWebhook.value, ...patch };
}

function updateInlineHeader(key: string, value: string) {
  const headers = { ...inlineWebhook.value.headers, [key]: value };
  if (value === "") delete headers[key];
  updateInlineWebhook({ headers });
}

// ==================== 渲染辅助 ====================

const nodeTypeLabel = computed(() => {
  return getNodeLabel(props.node.node_type);
});
</script>

<template>
  <div class="workflow-node-config">
    <div class="config-header">
      <span class="node-type-tag">{{ nodeTypeLabel }}</span>
      <template v-if="isEditingName">
        <el-input
          ref="nameInputRef"
          v-model="editingName"
          size="small"
          class="name-input"
          @blur="saveName"
          @keydown="handleNameKeydown" />
      </template>
      <template v-else>
        <span class="node-name">{{ localNode.name }}</span>
        <el-button
          v-if="!readonly"
          type="primary"
          :icon="EditPen"
          link
          size="small"
          class="edit-name-btn"
          @click="startEditName" />
      </template>
    </div>

    <!-- 条件节点 -->
    <template v-if="localNode.node_type === 'condition'">
      <div class="condition-branches">
        <div class="branches-header">
          <span class="branches-title">条件分支</span>
          <span class="branches-hint"><el-icon><InfoFilled /></el-icon>&nbsp;在画布上拖拽分支连线到目标节点</span>
        </div>

        <div class="branch-tabs">
          <div
            v-for="branch in branches"
            :key="branch.id"
            class="branch-tab"
            :class="{ active: branch.id === activeBranchId, 'is-default': branch.is_default }"
            @click="activeBranchId = branch.id">
            <span class="branch-tab-name">{{ branch.name }}</span>
            <el-tag v-if="branch.is_default" size="small" type="warning" class="branch-tab-default">默认</el-tag>
            <el-icon
              v-if="!readonly && branches.length > 1"
              class="branch-tab-close"
              @click.stop="removeBranch(branch.id)">
              <Close />
            </el-icon>
          </div>
          <el-dropdown
            v-if="!readonly"
            trigger="click"
            @command="handleAddBranchCommand">
            <el-button type="primary" :icon="Plus" text size="small">
              添加分支
            </el-button>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="condition">条件分支</el-dropdown-item>
                <el-dropdown-item command="default" :disabled="hasDefaultBranch">默认分支</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>

        <div v-if="activeBranch" class="branch-panel">
          <div class="branch-name-row">
            <span class="branch-name-label">分支名称</span>
            <el-input
              :model-value="activeBranch.name"
              :disabled="readonly"
              size="small"
              placeholder="分支名称"
              class="branch-name-input"
              @update:model-value="(val) => updateBranchName((activeBranch as ConditionBranch).id, val as string)" />
          </div>

          <div class="branch-target-row">
            <span class="branch-target-label">连线状态</span>
            <el-tag
              :type="activeBranch.target_node_id ? 'success' : 'info'"
              size="small">
              {{ activeBranch.target_node_id ? "已连线" : "未连线" }}
            </el-tag>
          </div>

          <template v-if="!activeBranch.is_default">
            <div class="condition-conjunction">
              <span class="conjunction-label">条件关系</span>
              <template v-if="readonly">
                <span class="conjunction-value">{{ getConjunctionLabel(activeBranch.conjunction) }}</span>
              </template>
              <el-radio-group
                v-else
                :model-value="activeBranch.conjunction"
                size="small"
                @change="(val) => updateBranchConjunction((activeBranch as ConditionBranch).id, val as ConjunctionValue)">
                <el-radio
                  v-for="opt in CONJUNCTION_OPTIONS"
                  :key="opt.value"
                  :label="opt.value">
                  {{ opt.label }}
                </el-radio>
              </el-radio-group>
            </div>

            <div class="conditions-list">
              <div
                v-for="(condition, index) in activeBranch.conditions"
                :key="index"
                class="condition-row">
                <el-select
                  :model-value="condition.field_id"
                  placeholder="选择字段"
                  class="field-select"
                  :disabled="readonly"
                  @change="(val) => onConditionFieldChange((activeBranch as ConditionBranch).id, index, val as string)">
                  <el-option
                    v-for="field in fields"
                    :key="field.id"
                    :label="field.name"
                    :value="field.id" />
                </el-select>

                <el-select
                  :model-value="condition.operator"
                  placeholder="操作符"
                  class="operator-select"
                  :disabled="readonly"
                  @change="(val) => onConditionOperatorChange((activeBranch as ConditionBranch).id, index, val as FilterOperatorValue)">
                  <el-option
                    v-for="op in getOperatorOptions(getFieldById(condition.field_id)?.type ?? '')"
                    :key="op.value"
                    :label="op.label"
                    :value="op.value" />
                </el-select>

                <FieldValueInput
                  v-if="operatorRequiresValue(condition.operator) && getFieldById(condition.field_id)"
                  :field="getFieldById(condition.field_id)!"
                  :model-value="condition.value"
                  placeholder="值"
                  class="value-input"
                  :disabled="readonly"
                  @update:model-value="(val) => onConditionValueChange((activeBranch as ConditionBranch).id, index, val)" />

                <span v-else class="value-placeholder">无需值</span>

                <el-button
                  v-if="!readonly"
                  type="danger"
                  :icon="Delete"
                  circle
                  size="small"
                  @click="removeCondition(activeBranch.id, index)" />
              </div>

              <el-button
                v-if="!readonly"
                type="primary"
                :icon="Plus"
                text
                @click="addCondition(activeBranch.id)">
                添加条件
              </el-button>
            </div>

            <el-divider />

            <div class="summary">
              <div class="summary-title">条件摘要</div>
              <div v-if="activeBranch.conditions.length > 1" class="summary-conjunction">
                关系：{{ getConjunctionLabel(activeBranch.conjunction) }}
              </div>
              <div
                v-for="(condition, index) in activeBranch.conditions"
                :key="`summary-${index}`"
                class="summary-item">
                {{ getFieldById(condition.field_id)?.name ?? "未选择字段" }}
                {{ OPERATOR_LABELS[condition.operator] ?? condition.operator }}
                {{ renderConditionValue(condition) }}
              </div>
              <el-empty v-if="activeBranch.conditions.length === 0" description="暂无条件" :image-size="60" />
            </div>
          </template>

          <el-alert
            v-else
            type="info"
            :closable="false"
            title="默认分支无需配置条件"
            description="当所有条件分支都不满足时，将执行此分支" />
        </div>
      </div>
    </template>

    <!-- 更新记录节点 -->
    <template v-else-if="localNode.node_type === 'update_record'">
      <div class="mapping-list">
        <div
          v-for="(mapping, index) in updateMappings"
          :key="index"
          class="mapping-row update-record-mapping-row">
          <el-select
            :model-value="mapping.field_id"
            placeholder="目标字段"
            class="field-select"
            :disabled="readonly"
            @change="(val) => updateMappingFieldId(index, val as string)">
            <el-option
              v-for="field in fields"
              :key="field.id"
              :label="field.name"
              :value="field.id" />
          </el-select>

          <div class="template-input-column">
            <template v-if="!isStaticOnlyFieldType(getFieldById(mapping.field_id)?.type ?? '')">
              <div class="mode-switch-row">
                <el-switch
                  :model-value="useExpressionForUpdate[index]"
                  :disabled="readonly || !mapping.field_id"
                  size="small"
                  active-text="使用表达式"
                  inactive-text="使用静态值"
                  @update:model-value="(val) => toggleExpressionForUpdate(index, val as boolean)" />
              </div>

              <el-input
                v-if="useExpressionForUpdate[index]"
                :model-value="mapping.value_template"
                placeholder="使用表达式（支持 {{trigger.record.field_id}}）"
                class="template-input"
                :disabled="readonly"
                @update:model-value="(val) => updateMappingTemplate(index, val)" />

              <FieldValueInput
                v-if="!useExpressionForUpdate[index] && mapping.field_id && getFieldById(mapping.field_id)"
                :key="`update-static-${index}`"
                :field="getFieldById(mapping.field_id)!"
                :model-value="mapping.value_template"
                placeholder="输入静态值"
                class="static-value-input"
                :disabled="readonly"
                @update:model-value="(val) => onUpdateStaticValueChange(index, val)" />
            </template>

            <template v-else>
              <FieldValueInput
                v-if="mapping.field_id && getFieldById(mapping.field_id)"
                :key="`update-static-${index}`"
                :field="getFieldById(mapping.field_id)!"
                :model-value="mapping.value_template"
                placeholder="输入静态值"
                class="static-value-input"
                :disabled="readonly"
                @update:model-value="(val) => onUpdateStaticValueChange(index, val)" />
            </template>
          </div>

          <el-button
            v-if="!readonly"
            type="danger"
            :icon="Delete"
            circle
            size="small"
            class="delete-btn"
            @click="removeUpdateMapping(index)" />
        </div>

        <el-button v-if="!readonly" type="primary" :icon="Plus" text @click="addUpdateMapping">
          添加字段更新
        </el-button>
      </div>
    </template>

    <!-- 创建记录节点 -->
    <template v-else-if="localNode.node_type === 'create_record'">
      <el-form label-position="top" class="config-form">
        <el-form-item label="目标表格">
          <el-select
            v-model="createRecordTargetTableId"
            placeholder="选择目标表格"
            class="full-width"
            :disabled="readonly"
            @change="onCreateRecordTargetTableChange">
            <el-option
              v-for="table in availableTables"
              :key="table.id"
              :label="table.name"
              :value="table.id" />
          </el-select>
        </el-form-item>
      </el-form>

      <!-- 编辑模式：保留原有表单 -->
      <div v-if="!readonly" class="mapping-list">
        <div
          v-for="(mapping, index) in createRecordMappings"
          :key="index"
          class="mapping-row create-record-mapping-row">
          <div class="field-select-group">
            <el-select
              :model-value="mapping.target_field_id"
              placeholder="目标字段"
              class="field-select"
              :disabled="readonly"
              :loading="isLoadingTargetFields"
              @change="(val) => updateCreateMapping(index, { target_field_id: val as string })">
              <el-option
                v-for="field in targetTableFields"
                :key="field.id"
                :label="field.name"
                :value="field.id" />
            </el-select>

            <el-select
              :model-value="mapping.source_field_id"
              placeholder="源字段（可选）"
              clearable
              class="field-select"
              :disabled="readonly"
              @change="(val) => onCreateSourceFieldChange(index, val as string | undefined)">
              <el-option
                v-for="field in fields"
                :key="field.id"
                :label="field.name"
                :value="field.id" />
            </el-select>
          </div>

          <div class="template-input-column">
            <template v-if="!isStaticOnlyFieldType(getTargetFieldById(mapping.target_field_id)?.type ?? '')">
              <div class="mode-switch-row">
                <el-switch
                  :model-value="useExpressionForCreate[index]"
                  :disabled="readonly || !mapping.target_field_id"
                  size="small"
                  active-text="使用表达式"
                  inactive-text="使用静态值"
                  @update:model-value="(val) => toggleExpressionForCreate(index, val as boolean)" />
              </div>

              <el-input
                v-if="useExpressionForCreate[index]"
                :model-value="mapping.value_template"
                placeholder="使用表达式（支持 {{trigger.record.field_id}}）"
                class="template-input"
                :disabled="readonly"
                @update:model-value="(val) => updateCreateValueTemplate(index, val)" />

              <FieldValueInput
                v-if="!useExpressionForCreate[index] && mapping.target_field_id && getTargetFieldById(mapping.target_field_id)"
                :key="`create-static-${index}`"
                :field="getTargetFieldById(mapping.target_field_id)!"
                :model-value="mapping.value_template"
                placeholder="输入静态值"
                class="static-value-input"
                :disabled="readonly"
                @update:model-value="(val) => onCreateStaticValueChange(index, val)" />
            </template>

            <template v-else>
              <FieldValueInput
                v-if="mapping.target_field_id && getTargetFieldById(mapping.target_field_id)"
                :key="`create-static-${index}`"
                :field="getTargetFieldById(mapping.target_field_id)!"
                :model-value="mapping.value_template"
                placeholder="输入静态值"
                class="static-value-input"
                :disabled="readonly"
                @update:model-value="(val) => onCreateStaticValueChange(index, val)" />
            </template>
          </div>

          <el-button
            v-if="!readonly"
            type="danger"
            :icon="Delete"
            circle
            size="small"
            class="delete-btn"
            @click="removeCreateMapping(index)" />
        </div>

        <el-button v-if="!readonly" type="primary" :icon="Plus" text @click="addCreateMapping">
          添加字段映射
        </el-button>
      </div>

      <!-- 只读模式：展示字段映射摘要 -->
      <div v-else class="readonly-mapping-summary">
        <div class="summary-title">字段映射</div>
        <el-empty v-if="createRecordMappings.length === 0" description="暂无字段映射" :image-size="60" />
        <div
          v-for="(mapping, index) in createRecordMappings"
          :key="index"
          class="summary-row">
          <div class="summary-field">
            <span class="summary-label">目标字段</span>
            <span class="summary-value">{{ (getTargetFieldById(mapping.target_field_id)?.name ?? mapping.target_field_id) || '-' }}</span>
          </div>
          <div class="summary-field">
            <span class="summary-label">源字段</span>
            <span class="summary-value">{{ (getFieldById(mapping.source_field_id ?? '')?.name ?? mapping.source_field_id) || '-' }}</span>
          </div>
          <div class="summary-field summary-wide">
            <span class="summary-label">取值</span>
            <span class="summary-value">{{ mapping.value_template || '-' }}</span>
          </div>
        </div>
      </div>
    </template>

    <!-- 发送邮件节点 -->
    <template v-else-if="localNode.node_type === 'send_email'">
      <el-form label-position="top" class="config-form">
        <el-form-item label="收件人来源">
          <el-radio-group v-model="emailRecipientType" :disabled="readonly">
            <el-radio label="field">字段</el-radio>
            <el-radio label="fixed">固定邮箱</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item v-if="emailRecipientType === 'field'" label="收件人字段">
          <el-select
            v-model="emailRecipientValue"
            multiple
            placeholder="选择字段"
            class="full-width"
            :disabled="readonly">
            <el-option
              v-for="field in emailFields"
              :key="field.id"
              :label="field.name"
              :value="field.id" />
          </el-select>
          <div class="field-hint">仅支持邮箱、成员、协作人类型字段</div>
        </el-form-item>

        <el-form-item v-else label="固定邮箱">
          <el-select
            v-model="emailRecipientValue"
            multiple
            filterable
            allow-create
            default-first-option
            placeholder="输入邮箱地址"
            class="full-width"
            :disabled="readonly" />
        </el-form-item>

        <el-form-item label="内容模式">
          <el-radio-group v-model="emailContentMode" :disabled="readonly">
            <el-radio label="custom">自定义内容</el-radio>
            <el-radio label="template">邮件模板</el-radio>
          </el-radio-group>
        </el-form-item>

        <template v-if="emailContentMode === 'custom'">
          <el-form-item label="邮件主题">
            <el-input
              v-model="emailSubject"
              placeholder="请输入邮件主题"
              :disabled="readonly" />
            <div class="field-hint" v-pre>支持 {{record.field_id}} 引用记录字段值</div>
          </el-form-item>

          <el-form-item label="邮件正文">
            <el-input
              v-model="emailBody"
              type="textarea"
              :rows="6"
              placeholder="请输入邮件正文"
              :disabled="readonly" />
            <div class="field-hint" v-pre>支持 {{record.field_id}} 引用记录字段值，{{trigger.event_type}} 引用触发事件</div>
          </el-form-item>
        </template>

        <template v-else>
          <el-form-item label="邮件模板">
            <el-select v-model="emailTemplateId" placeholder="选择模板" class="full-width" :disabled="readonly">
              <el-option
                v-for="template in emailTemplates"
                :key="template.id"
                :label="template.name"
                :value="template.template_key" />
            </el-select>
          </el-form-item>
        </template>
      </el-form>
    </template>

    <!-- Webhook 节点 -->
    <template v-else-if="localNode.node_type === 'webhook'">
      <el-form label-position="top" class="config-form">
        <el-form-item label="Webhook 来源">
          <el-radio-group v-model="webhookMode" class="webhook-source-radio" :disabled="readonly || !isNewWebhookNode">
            <el-radio label="existing">选择已配置</el-radio>
            <el-radio label="inline">内联新建</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item v-if="webhookMode === 'existing'" label="选择 Webhook">
          <el-select v-model="selectedWebhookId" placeholder="选择 Webhook" class="full-width" :disabled="readonly">
            <el-option
              v-for="webhook in availableWebhooks"
              :key="webhook.id"
              :label="webhook.name"
              :value="webhook.id" />
          </el-select>
        </el-form-item>

        <template v-else>
          <el-form-item label="名称">
            <el-input
              :model-value="inlineWebhook.name"
              placeholder="Webhook 名称"
              :disabled="readonly"
              @update:model-value="(val) => updateInlineWebhook({ name: val })" />
          </el-form-item>

          <el-form-item label="请求地址">
            <el-input
              :model-value="inlineWebhook.url"
              placeholder="https://example.com/webhook"
              :disabled="readonly"
              @update:model-value="(val) => updateInlineWebhook({ url: val })" />
          </el-form-item>

          <el-form-item label="请求方法">
            <el-select
              :model-value="inlineWebhook.method"
              class="full-width"
              :disabled="readonly"
              @update:model-value="(val) => updateInlineWebhook({ method: val as WebhookMethod })">
              <el-option
                v-for="method in webhookMethods"
                :key="method.value"
                :label="method.label"
                :value="method.value" />
            </el-select>
          </el-form-item>

          <el-form-item label="Headers">
            <div class="headers-list">
              <div
                v-for="(_, key) in inlineWebhook.headers"
                :key="key"
                class="header-row">
                <el-input :model-value="key" disabled class="header-key" />
                <el-input
                  :model-value="inlineWebhook.headers[key]"
                  placeholder="值"
                  class="header-value"
                  :disabled="readonly"
                  @update:model-value="(val) => updateInlineHeader(key, val)" />
              </div>
              <div v-if="!readonly" class="header-row">
                <el-input
                  placeholder="新 Header 键"
                  class="header-key"
                  @blur="(e: Event) => {
                    const target = e.target as HTMLInputElement;
                    if (target.value) updateInlineHeader(target.value, '');
                  }" />
              </div>
            </div>
          </el-form-item>

          <el-form-item label="Body 模板">
            <el-input
              :model-value="inlineWebhook.body_template"
              type="textarea"
              :rows="4"
              placeholder="JSON 模板（注意对应webhook接口配置要求），支持通过 {{record}}、{{record.field_id}} 获取对应的数据"
              :disabled="readonly"
              @update:model-value="(val) => updateInlineWebhook({ body_template: val })" />
          </el-form-item>
        </template>
      </el-form>
    </template>

    <!-- 查找记录节点 -->
    <template v-else-if="localNode.node_type === 'find_records'">
      <div class="section-title">查找记录</div>
      <el-form label-position="top" class="config-form">
        <el-form-item label="目标表格">
          <el-select
            v-model="findRecordsTargetTableId"
            placeholder="选择目标表格"
            class="full-width"
            :disabled="readonly"
            @change="onFindRecordsTargetTableChange">
            <el-option
              v-for="table in availableTables"
              :key="table.id"
              :label="table.name"
              :value="table.id" />
          </el-select>
        </el-form-item>

        <el-form-item label="过滤条件">
          <div class="find-records-conditions">
            <div class="condition-conjunction">
              <span class="conjunction-label">条件关系</span>
              <template v-if="readonly">
                <span class="conjunction-value">{{ getConjunctionLabel(findRecordsConjunction) }}</span>
              </template>
              <el-radio-group
                v-else
                v-model="findRecordsConjunction"
                size="small">
                <el-radio
                  v-for="opt in CONJUNCTION_OPTIONS"
                  :key="opt.value"
                  :label="opt.value">
                  {{ opt.label }}
                </el-radio>
              </el-radio-group>
            </div>

            <div class="conditions-list">
              <div
                v-for="(condition, index) in findRecordsConditions"
                :key="index"
                class="condition-row">
                <el-select
                  :model-value="condition.field_id"
                  placeholder="选择字段"
                  class="field-select"
                  :disabled="readonly"
                  @change="(val) => onFindRecordsConditionFieldChange(index, val as string)">
                  <el-option
                    v-for="field in targetTableFields"
                    :key="field.id"
                    :label="field.name"
                    :value="field.id" />
                </el-select>

                <el-select
                  :model-value="condition.operator"
                  placeholder="操作符"
                  class="operator-select"
                  :disabled="readonly"
                  @change="(val) => onFindRecordsConditionOperatorChange(index, val as FilterOperatorValue)">
                  <el-option
                    v-for="op in getOperatorOptions(getTargetFieldById(condition.field_id)?.type ?? '')"
                    :key="op.value"
                    :label="op.label"
                    :value="op.value" />
                </el-select>

                <FieldValueInput
                  v-if="operatorRequiresValue(condition.operator) && getTargetFieldById(condition.field_id)"
                  :field="getTargetFieldById(condition.field_id)!"
                  :model-value="condition.value"
                  placeholder="值"
                  class="value-input"
                  :disabled="readonly"
                  @update:model-value="(val) => onFindRecordsConditionValueChange(index, val)" />

                <span v-else class="value-placeholder">无需值</span>

                <el-button
                  v-if="!readonly"
                  type="danger"
                  :icon="Delete"
                  circle
                  size="small"
                  @click="removeFindRecordsCondition(index)" />
              </div>

              <el-button
                v-if="!readonly"
                type="primary"
                :icon="Plus"
                text
                @click="addFindRecordsCondition">
                添加条件
              </el-button>
            </div>
          </div>
        </el-form-item>

        <el-form-item label="排序字段">
          <el-select
            v-model="findRecordsSortFieldId"
            placeholder="选择排序字段"
            class="full-width"
            :disabled="readonly">
            <el-option
              v-for="field in targetTableFields"
              :key="field.id"
              :label="field.name"
              :value="field.id" />
          </el-select>
        </el-form-item>

        <el-form-item label="排序方向">
          <el-radio-group v-model="findRecordsSortDirection" :disabled="readonly">
            <el-radio label="asc">升序</el-radio>
            <el-radio label="desc">降序</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="返回条数上限">
          <el-input-number
            v-model="findRecordsLimit"
            :min="1"
            :max="1000"
            :controls="false"
            class="full-width"
            :disabled="readonly" />
        </el-form-item>

        <el-form-item label="结果变量名">
          <el-input
            v-model="findRecordsVariable"
            placeholder="records"
            class="full-width"
            :disabled="readonly" />
          <div class="form-item-hint">
            变量名只能包含字母、数字和下划线，且不能以数字开头。
          </div>
          <div v-if="!isFindRecordsVariableValid" class="form-item-error">
            变量名格式不正确，请检查输入。
          </div>
        </el-form-item>

        <el-form-item label="空结果处理">
          <el-radio-group v-model="findRecordsEmptyAction" :disabled="readonly">
            <el-radio label="continue">空结果继续执行</el-radio>
            <el-radio label="stop">空结果终止分支</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
    </template>

    <!-- 未知类型 -->
    <template v-else>
      <el-empty :description="`暂不支持该节点类型配置：${localNode.node_type || '未知类型'}`" />
    </template>
  </div>
</template>

<style lang="scss" scoped>
.workflow-node-config {
  padding: $spacing-md;
}

.config-header {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  margin-bottom: $spacing-md;
  padding-bottom: $spacing-sm;
  border-bottom: 1px solid $border-color;
}

.node-type-tag {
  font-size: $font-size-sm;
  color: $primary-color;
  background-color: rgba($primary-color, 0.1);
  padding: 2px $spacing-sm;
  border-radius: $border-radius-sm;
}

.node-name {
  font-weight: 600;
  color: $text-primary;
}

.name-input {
  flex: 1;
  min-width: 120px;
  max-width: 300px;
}

.edit-name-btn {
  margin-left: $spacing-xs;
}

.config-form {
  .el-form-item {
    margin-bottom: $spacing-md;
  }
}

.full-width {
  width: 100%;
}

.field-hint {
  font-size: $font-size-xs;
  color: $text-secondary;
  line-height: 1.4;
  margin-top: 4px;
}

.condition-conjunction {
  display: flex;
  align-items: center;
  gap: $spacing-md;
  padding: $spacing-sm;
  background-color: $bg-color;
  border-radius: $border-radius-md;

  .conjunction-label {
    color: $text-secondary;
    font-size: $font-size-sm;
    flex-shrink: 0;
  }

  .conjunction-value {
    font-weight: 500;
  }
}

.conditions-list,
.mapping-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
}

.condition-row,
.mapping-row {
  display: flex;
  align-items: flex-start;
  gap: $spacing-sm;
  padding: $spacing-sm;
  background-color: $bg-color;
  border-radius: $border-radius-md;
}

.delete-btn {
  margin-top: 6px;
  flex-shrink: 0;
}

.condition-row {
  .field-select,
  .operator-select,
  .value-input,
  .value-placeholder {
    flex: 1 1 0;
    min-width: 0;
  }
}

.field-select,
.operator-select {
  min-width: 120px;
}

.value-input,
.template-input {
  flex: 1;
}

.template-input-column {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: $spacing-xs;
  min-width: 0;
}

.mode-switch-row {
  display: flex;
  align-items: center;
  gap: $spacing-md;
  padding: $spacing-xs 0;
}

.update-record-mapping-row {
  .field-select {
    flex: 0 0 40%;
    min-width: 0;
  }

  .template-input-column {
    flex: 0 0 50%;
    min-width: 0;
  }
}

.create-record-mapping-row {
  .field-select-group {
    flex: 0 0 50%;
    display: flex;
    gap: $spacing-sm;
    min-width: 0;

    .field-select {
      flex: 1;
      min-width: 0;
    }
  }

  .template-input-column {
    flex: 1;
    min-width: 0;
  }
}

.readonly-mapping-summary {
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;

  .summary-title {
    font-size: $font-size-sm;
    color: $text-secondary;
    margin-bottom: $spacing-xs;
  }

  .summary-row {
    display: flex;
    flex-wrap: wrap;
    gap: $spacing-md;
    padding: $spacing-sm;
    background-color: $bg-color;
    border-radius: $border-radius-md;
  }

  .summary-field {
    display: flex;
    flex-direction: column;
    gap: 2px;
    min-width: 120px;

    &.summary-wide {
      flex: 1 1 100%;
      min-width: 0;
    }
  }

  .summary-label {
    font-size: $font-size-xs;
    color: $text-secondary;
  }

  .summary-value {
    font-size: $font-size-sm;
    color: $text-primary;
    word-break: break-all;
  }
}

.static-value-row {
  display: flex;
  flex-direction: column;
  gap: $spacing-xs;
  padding-left: $spacing-sm;
}

.static-value-input {
  width: 100%;
}

.value-placeholder {
  flex: 1;
  color: $text-secondary;
  font-size: $font-size-sm;
}

.summary {
  margin-top: $spacing-md;
}

.summary-title {
  font-weight: 600;
  margin-bottom: $spacing-sm;
  color: $text-primary;
}

.summary-item {
  font-size: $font-size-sm;
  color: $text-secondary;
  padding: $spacing-xs 0;
}

.summary-conjunction {
  font-size: $font-size-sm;
  color: $text-primary;
  margin-bottom: $spacing-xs;
}

.headers-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
  width: 100%;
}

.header-row {
  display: flex;
  gap: $spacing-sm;
}

.header-key,
.header-value {
  flex: 1;
}

.section-title {
  font-weight: 600;
  color: $text-primary;
  margin-bottom: $spacing-md;
}

.form-item-hint {
  font-size: $font-size-xs;
  color: $text-secondary;
  margin-top: $spacing-xs;
  margin-left: $spacing-lg;
  background-color: $bg-color;
  border-radius: $border-radius-md;
}

.form-item-error {
  font-size: $font-size-sm;
  color: $error-color;
  margin-top: $spacing-xs;
}

.find-records-conditions {
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
  width: 100%;
}

.condition-branches {
  display: flex;
  flex-direction: column;
  gap: $spacing-md;
}

.branches-header {
  display: flex;
  align-items: center;
  justify-content: space-between;

  .branches-title {
    font-weight: 600;
    color: $text-primary;
  }

  .branches-hint {
    font-size: $font-size-sm;
    color: $text-secondary;
  }
}

.branch-tabs {
  display: flex;
  align-items: center;
  gap: $spacing-xs;
  flex-wrap: wrap;
}

.branch-tab {
  display: flex;
  align-items: center;
  gap: $spacing-xs;
  padding: $spacing-xs $spacing-sm;
  background-color: $bg-color;
  border-radius: $border-radius-sm;
  cursor: pointer;
  font-size: $font-size-sm;
  color: $text-secondary;
  transition: all 0.2s;

  &.active {
    background-color: rgba($primary-color, 0.1);
    color: $primary-color;
  }

  &.is-default {
    border: 1px dashed $warning-color;
  }

  .branch-tab-name {
    max-width: 120px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .branch-tab-default {
    margin-left: 0;
    transform: scale(0.85);
    transform-origin: center;
  }

  .branch-tab-close {
    font-size: 12px;

    &:hover {
      color: $error-color;
    }
  }
}

.branch-panel {
  display: flex;
  flex-direction: column;
  gap: $spacing-md;
}

.branch-name-row,
.branch-target-row {
  display: flex;
  align-items: center;
  gap: $spacing-sm;

  .branch-name-label,
  .branch-target-label {
    font-size: $font-size-sm;
    color: $text-secondary;
    flex-shrink: 0;
  }

  .branch-name-input {
    flex: 1;
  }
}
</style>
