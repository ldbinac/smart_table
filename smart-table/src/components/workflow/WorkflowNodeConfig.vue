<script setup lang="ts">
import { computed, nextTick, ref, watch } from "vue";
import type { FieldEntity, TableEntity } from "@/db/schema";
import type {
  WorkflowNode,
  WebhookConfig,
  ApprovalMode,
  WebhookMethod,
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
import { normalizeWorkflowNode } from "@/utils/workflow";
import FieldValueInput from "@/components/fields/FieldValueInput.vue";
import {
  Delete,
  Plus,
  EditPen,
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

const localNode = ref<WorkflowNode>({
  ...normalizeWorkflowNode(props.node),
  config: cloneConfig(props.node.config),
});
let isUpdatingFromParent = false;

watch(
  () => props.node,
  (newNode) => {
    isUpdatingFromParent = true;
    localNode.value = {
      ...normalizeWorkflowNode(newNode),
      config: cloneConfig(newNode.config),
    };
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
const availableWebhooks = computed(() => props.webhooks ?? []);

// ==================== 审批节点配置 ====================

const approvalModes: { value: ApprovalMode; label: string }[] = [
  { value: "any", label: "或签（任意一人通过即可）" },
  { value: "all", label: "会签（所有人都需通过）" },
  { value: "serial", label: "串行（按顺序审批）" },
];

const timeoutActions = [
  { value: "approve", label: "自动通过" },
  { value: "reject", label: "自动拒绝" },
  { value: "remind", label: "发送提醒" },
];

const assigneeType = computed({
  get: () => configValue<string>("assignee_type", "fixed"),
  set: (value) => setConfigValue("assignee_type", value),
});

const assigneeValue = computed({
  get: () => configValue<string | string[]>("assignee_value", []),
  set: (value) => setConfigValue("assignee_value", value),
});

const approvalMode = computed({
  get: () => configValue<ApprovalMode>("approval_mode", "any"),
  set: (value) => setConfigValue("approval_mode", value),
});

const timeoutMinutes = computed({
  get: () => configValue<number | undefined>("timeout_minutes", undefined),
  set: (value) => setConfigValue("timeout_minutes", value),
});

const timeoutAction = computed({
  get: () => configValue<string | undefined>("timeout_action", undefined),
  set: (value) => setConfigValue("timeout_action", value),
});

const memberFieldOptions = computed(() =>
  props.fields.filter((f) => f.type === "member" || f.type === "collaborator"),
);

// ==================== 条件节点配置 ====================

interface ConditionItem {
  field_id: string;
  operator: FilterOperatorValue;
  value: unknown;
}

const conditions = computed<ConditionItem[]>({
  get: () => configValue<ConditionItem[]>("conditions", []),
  set: (value) => setConfigValue("conditions", value),
});

function addCondition() {
  const firstField = props.fields[0];
  const defaultOperator = firstField
    ? getOperatorsForFieldType(firstField.type)[0] ?? FilterOperator.EQUALS
    : FilterOperator.EQUALS;
  conditions.value = [
    ...conditions.value,
    {
      field_id: firstField?.id ?? "",
      operator: defaultOperator,
      value: undefined,
    },
  ];
}

function removeCondition(index: number) {
  const list = [...conditions.value];
  list.splice(index, 1);
  conditions.value = list;
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

function onConditionFieldChange(index: number, fieldId: string) {
  const list = [...conditions.value];
  const field = getFieldById(fieldId);
  const operators = field ? getOperatorsForFieldType(field.type) : [];
  list[index] = {
    field_id: fieldId,
    operator: operators[0] ?? FilterOperator.EQUALS,
    value: undefined,
  };
  conditions.value = list;
}

function onConditionOperatorChange(index: number, operator: FilterOperatorValue) {
  const list = [...conditions.value];
  list[index] = { ...list[index], operator };
  if (!operatorRequiresValue(operator)) {
    list[index].value = undefined;
  }
  conditions.value = list;
}

function onConditionValueChange(index: number, value: unknown) {
  const list = [...conditions.value];
  list[index] = { ...list[index], value };
  conditions.value = list;
}

function renderConditionValue(condition: ConditionItem): string {
  if (!operatorRequiresValue(condition.operator)) return "";
  if (condition.value === undefined || condition.value === null) return "空";
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
  (newTableId, oldTableId) => {
    loadTargetFields(newTableId);
    if (oldTableId !== undefined && oldTableId !== newTableId) {
      createRecordMappings.value = [];
    }
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

const emailTemplateId = computed({
  get: () => configValue<string | undefined>("email_template_id", undefined),
  set: (value) => setConfigValue("email_template_id", value),
});

const emailFields = computed(() =>
  props.fields.filter((f) => f.type === "email" || f.type === "member" || f.type === "collaborator"),
);

const emailTemplates = [
  { id: "template_1", name: "审批通知" },
  { id: "template_2", name: "状态变更通知" },
  { id: "template_3", name: "自定义模板" },
];

// ==================== Webhook 节点配置 ====================

const webhookMethods: { value: WebhookMethod; label: string }[] = [
  { value: "GET", label: "GET" },
  { value: "POST", label: "POST" },
  { value: "PUT", label: "PUT" },
];

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
  const labels: Record<string, string> = {
    approval: "审批节点",
    condition: "条件节点",
    update_record: "更新记录",
    create_record: "创建记录",
    send_email: "发送邮件",
    webhook: "Webhook",
    action: "动作节点",
    trigger: "触发器",
  };
  return labels[props.node.node_type] ?? props.node.node_type;
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

    <!-- 审批节点 -->
    <template v-if="localNode.node_type === 'approval'">
      <el-form label-position="top" class="config-form">
        <el-form-item label="审批人选择方式">
          <el-radio-group v-model="assigneeType" :disabled="readonly">
            <el-radio label="fixed">固定用户</el-radio>
            <el-radio label="field">字段指定</el-radio>
            <el-radio label="role">角色</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item v-if="assigneeType === 'fixed'" label="审批人">
          <el-select
            v-model="assigneeValue"
            multiple
            placeholder="选择用户"
            class="full-width"
            :disabled="readonly">
            <el-option label="当前用户" value="current_user" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>

        <el-form-item v-else-if="assigneeType === 'field'" label="成员字段">
          <el-select v-model="assigneeValue" placeholder="选择字段" class="full-width" :disabled="readonly">
            <el-option
              v-for="field in memberFieldOptions"
              :key="field.id"
              :label="field.name"
              :value="field.id" />
          </el-select>
        </el-form-item>

        <el-form-item v-else label="角色">
          <el-select v-model="assigneeValue" placeholder="选择角色" class="full-width" :disabled="readonly">
            <el-option label="管理员" value="admin" />
            <el-option label="部门负责人" value="manager" />
          </el-select>
        </el-form-item>

        <el-form-item label="审批模式">
          <el-select v-model="approvalMode" class="full-width" :disabled="readonly">
            <el-option
              v-for="mode in approvalModes"
              :key="mode.value"
              :label="mode.label"
              :value="mode.value" />
          </el-select>
        </el-form-item>

        <el-form-item label="超时时间（分钟）">
          <el-input-number v-model="timeoutMinutes" :min="0" :controls="false" class="full-width" :disabled="readonly" />
        </el-form-item>

        <el-form-item v-if="timeoutMinutes && timeoutMinutes > 0" label="超时动作">
          <el-select v-model="timeoutAction" class="full-width" :disabled="readonly">
            <el-option
              v-for="action in timeoutActions"
              :key="action.value"
              :label="action.label"
              :value="action.value" />
          </el-select>
        </el-form-item>
      </el-form>
    </template>

    <!-- 条件节点 -->
    <template v-else-if="localNode.node_type === 'condition'">
      <div class="conditions-list">
        <div
          v-for="(condition, index) in conditions"
          :key="index"
          class="condition-row">
          <el-select
            :model-value="condition.field_id"
            placeholder="选择字段"
            class="field-select"
            :disabled="readonly"
            @change="(val) => onConditionFieldChange(index, val as string)">
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
            @change="(val) => onConditionOperatorChange(index, val as FilterOperatorValue)">
            <el-option
              v-for="op in getOperatorOptions(getFieldById(condition.field_id)?.type ?? '')"
              :key="op.value"
              :label="op.label"
              :value="op.value" />
          </el-select>

          <FieldValueInput
            v-if="operatorRequiresValue(condition.operator)"
            :field="getFieldById(condition.field_id)!"
            :model-value="condition.value"
            placeholder="值"
            class="value-input"
            :disabled="readonly"
            @update:model-value="(val) => onConditionValueChange(index, val)" />

          <span v-else class="value-placeholder">无需值</span>

          <el-button
            v-if="!readonly"
            type="danger"
            :icon="Delete"
            circle
            size="small"
            @click="removeCondition(index)" />
        </div>

        <el-button v-if="!readonly" type="primary" :icon="Plus" text @click="addCondition">
          添加条件
        </el-button>
      </div>

      <el-divider />

      <div class="summary">
        <div class="summary-title">条件摘要</div>
        <div
          v-for="(condition, index) in conditions"
          :key="`summary-${index}`"
          class="summary-item">
          {{ getFieldById(condition.field_id)?.name ?? "未选择字段" }}
          {{ OPERATOR_LABELS[condition.operator] ?? condition.operator }}
          {{ renderConditionValue(condition) }}
        </div>
        <el-empty v-if="conditions.length === 0" description="暂无条件" :image-size="60" />
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
                v-if="!useExpressionForUpdate[index] && mapping.field_id"
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
                v-if="mapping.field_id"
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
          <el-select v-model="createRecordTargetTableId" placeholder="选择目标表格" class="full-width" :disabled="readonly">
            <el-option
              v-for="table in availableTables"
              :key="table.id"
              :label="table.name"
              :value="table.id" />
          </el-select>
        </el-form-item>
      </el-form>

      <div class="mapping-list">
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
                v-if="!useExpressionForCreate[index] && mapping.target_field_id"
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
                v-if="mapping.target_field_id"
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

        <el-form-item label="邮件模板">
          <el-select v-model="emailTemplateId" placeholder="选择模板" class="full-width" :disabled="readonly">
            <el-option
              v-for="template in emailTemplates"
              :key="template.id"
              :label="template.name"
              :value="template.id" />
          </el-select>
        </el-form-item>
      </el-form>
    </template>

    <!-- Webhook 节点 -->
    <template v-else-if="localNode.node_type === 'webhook'">
      <el-form label-position="top" class="config-form">
        <el-form-item label="Webhook 来源">
          <el-radio-group v-model="webhookMode" :disabled="readonly">
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
            <el-input v-model="inlineWebhook.name" placeholder="Webhook 名称" :disabled="readonly" />
          </el-form-item>

          <el-form-item label="请求地址">
            <el-input v-model="inlineWebhook.url" placeholder="https://example.com/webhook" :disabled="readonly" />
          </el-form-item>

          <el-form-item label="请求方法">
            <el-select v-model="inlineWebhook.method" class="full-width" :disabled="readonly">
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
              v-model="inlineWebhook.body_template"
              type="textarea"
              :rows="4"
              placeholder="JSON 模板，支持 {{trigger.record.field_id}}"
              :disabled="readonly" />
          </el-form-item>
        </template>
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
</style>
