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
import {
  Delete,
  Plus,
} from "@element-plus/icons-vue";

interface Props {
  node: WorkflowNode;
  fields: FieldEntity[];
  tables?: TableEntity[];
  webhooks?: WebhookConfig[];
}

const props = defineProps<Props>();
const emit = defineEmits<{
  (e: "update:node", node: WorkflowNode): void;
}>();

// ==================== 通用配置辅助 ====================

const localNode = ref<WorkflowNode>({ ...props.node, config: cloneConfig(props.node.config) });
let isUpdatingFromParent = false;

watch(
  () => props.node,
  (newNode) => {
    isUpdatingFromParent = true;
    localNode.value = { ...newNode, config: cloneConfig(newNode.config) };
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

function updateMappingFieldId(index: number, fieldId: string) {
  const list = [...updateMappings.value];
  list[index] = { ...list[index], field_id: fieldId };
  updateMappings.value = list;
}

function updateMappingTemplate(index: number, template: string) {
  const list = [...updateMappings.value];
  list[index] = { ...list[index], value_template: template };
  updateMappings.value = list;
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

function updateCreateMapping(index: number, patch: Partial<FieldMapping>) {
  const list = [...createRecordMappings.value];
  list[index] = { ...list[index], ...patch };
  createRecordMappings.value = list;
}

const targetTableFields = computed(() => {
  // 当前仅展示源表字段；目标表字段在真实场景中需额外加载
  return props.fields;
});

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
      <span class="node-name">{{ localNode.name }}</span>
    </div>

    <!-- 审批节点 -->
    <template v-if="localNode.node_type === 'approval'">
      <el-form label-position="top" class="config-form">
        <el-form-item label="审批人选择方式">
          <el-radio-group v-model="assigneeType">
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
            class="full-width">
            <el-option label="当前用户" value="current_user" />
            <el-option label="管理员" value="admin" />
          </el-select>
        </el-form-item>

        <el-form-item v-else-if="assigneeType === 'field'" label="成员字段">
          <el-select v-model="assigneeValue" placeholder="选择字段" class="full-width">
            <el-option
              v-for="field in memberFieldOptions"
              :key="field.id"
              :label="field.name"
              :value="field.id" />
          </el-select>
        </el-form-item>

        <el-form-item v-else label="角色">
          <el-select v-model="assigneeValue" placeholder="选择角色" class="full-width">
            <el-option label="管理员" value="admin" />
            <el-option label="部门负责人" value="manager" />
          </el-select>
        </el-form-item>

        <el-form-item label="审批模式">
          <el-select v-model="approvalMode" class="full-width">
            <el-option
              v-for="mode in approvalModes"
              :key="mode.value"
              :label="mode.label"
              :value="mode.value" />
          </el-select>
        </el-form-item>

        <el-form-item label="超时时间（分钟）">
          <el-input-number v-model="timeoutMinutes" :min="0" :controls="false" class="full-width" />
        </el-form-item>

        <el-form-item v-if="timeoutMinutes && timeoutMinutes > 0" label="超时动作">
          <el-select v-model="timeoutAction" class="full-width">
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
            @change="(val) => onConditionOperatorChange(index, val as FilterOperatorValue)">
            <el-option
              v-for="op in getOperatorOptions(getFieldById(condition.field_id)?.type ?? '')"
              :key="op.value"
              :label="op.label"
              :value="op.value" />
          </el-select>

          <el-input
            v-if="operatorRequiresValue(condition.operator)"
            :model-value="String(condition.value ?? '')"
            placeholder="值"
            class="value-input"
            @update:model-value="(val) => onConditionValueChange(index, val)" />

          <span v-else class="value-placeholder">无需值</span>

          <el-button
            type="danger"
            :icon="Delete"
            circle
            size="small"
            @click="removeCondition(index)" />
        </div>

        <el-button type="primary" :icon="Plus" text @click="addCondition">
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
          class="mapping-row">
          <el-select
            :model-value="mapping.field_id"
            placeholder="目标字段"
            class="field-select"
            @change="(val) => updateMappingFieldId(index, val as string)">
            <el-option
              v-for="field in fields"
              :key="field.id"
              :label="field.name"
              :value="field.id" />
          </el-select>

          <el-input
            :model-value="mapping.value_template"
            placeholder="新值（支持 {{trigger.record.field_id}}）"
            class="template-input"
            @update:model-value="(val) => updateMappingTemplate(index, val)" />

          <el-button
            type="danger"
            :icon="Delete"
            circle
            size="small"
            @click="removeUpdateMapping(index)" />
        </div>

        <el-button type="primary" :icon="Plus" text @click="addUpdateMapping">
          添加字段更新
        </el-button>
      </div>
    </template>

    <!-- 创建记录节点 -->
    <template v-else-if="localNode.node_type === 'create_record'">
      <el-form label-position="top" class="config-form">
        <el-form-item label="目标表格">
          <el-select v-model="createRecordTargetTableId" placeholder="选择目标表格" class="full-width">
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
          class="mapping-row">
          <el-select
            :model-value="mapping.target_field_id"
            placeholder="目标字段"
            class="field-select"
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
            @change="(val) => updateCreateMapping(index, { source_field_id: val as string | undefined })">
            <el-option
              v-for="field in fields"
              :key="field.id"
              :label="field.name"
              :value="field.id" />
          </el-select>

          <el-input
            :model-value="mapping.value_template"
            placeholder="或填写模板值"
            class="template-input"
            @update:model-value="(val) => updateCreateMapping(index, { value_template: val })" />

          <el-button
            type="danger"
            :icon="Delete"
            circle
            size="small"
            @click="removeCreateMapping(index)" />
        </div>

        <el-button type="primary" :icon="Plus" text @click="addCreateMapping">
          添加字段映射
        </el-button>
      </div>
    </template>

    <!-- 发送邮件节点 -->
    <template v-else-if="localNode.node_type === 'send_email'">
      <el-form label-position="top" class="config-form">
        <el-form-item label="收件人来源">
          <el-radio-group v-model="emailRecipientType">
            <el-radio label="field">字段</el-radio>
            <el-radio label="fixed">固定邮箱</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item v-if="emailRecipientType === 'field'" label="收件人字段">
          <el-select
            v-model="emailRecipientValue"
            multiple
            placeholder="选择字段"
            class="full-width">
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
            class="full-width" />
        </el-form-item>

        <el-form-item label="邮件模板">
          <el-select v-model="emailTemplateId" placeholder="选择模板" class="full-width">
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
          <el-radio-group v-model="webhookMode">
            <el-radio label="existing">选择已配置</el-radio>
            <el-radio label="inline">内联新建</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item v-if="webhookMode === 'existing'" label="选择 Webhook">
          <el-select v-model="selectedWebhookId" placeholder="选择 Webhook" class="full-width">
            <el-option
              v-for="webhook in availableWebhooks"
              :key="webhook.id"
              :label="webhook.name"
              :value="webhook.id" />
          </el-select>
        </el-form-item>

        <template v-else>
          <el-form-item label="名称">
            <el-input v-model="inlineWebhook.name" placeholder="Webhook 名称" />
          </el-form-item>

          <el-form-item label="请求地址">
            <el-input v-model="inlineWebhook.url" placeholder="https://example.com/webhook" />
          </el-form-item>

          <el-form-item label="请求方法">
            <el-select v-model="inlineWebhook.method" class="full-width">
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
                  @update:model-value="(val) => updateInlineHeader(key, val)" />
              </div>
              <div class="header-row">
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
              placeholder="JSON 模板，支持 {{trigger.record.field_id}}" />
          </el-form-item>
        </template>
      </el-form>
    </template>

    <!-- 未知类型 -->
    <template v-else>
      <el-empty description="暂不支持该节点类型配置" />
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
  align-items: center;
  gap: $spacing-sm;
  padding: $spacing-sm;
  background-color: $bg-color;
  border-radius: $border-radius-md;
}

.field-select,
.operator-select {
  min-width: 120px;
}

.value-input,
.template-input {
  flex: 1;
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
