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
  LoopDataSource,
  WorkflowNodeType,
  ScriptNodeConfig,
  ScriptBranch,
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
  getAvailableLoopDataSources,
  countLoopNodes,
  getMaxLoopNestingDepth,
  findParentLoopNodeId,
} from "@/utils/workflow";
import {
  getNodeLabel,
  getNodeIcon,
  LOOP_BODY_ALLOWED_NODE_TYPES,
  MAX_LOOP_NODES_PER_WORKFLOW,
  MAX_LOOP_NESTING_DEPTH,
} from "@/utils/workflowNodeType";
import { ElMessage } from "element-plus";
import {
  normalizeConditionConfig,
  addConditionBranch,
  addDefaultBranch,
  hasDefaultBranch as checkDefaultBranch,
  removeConditionBranch,
  updateConditionBranch,
} from "@/utils/conditionBranch";
import FieldValueInput from "@/components/fields/FieldValueInput.vue";
import LoopVarInserter from "./LoopVarInserter.vue";
import {
  Delete,
  Plus,
  EditPen,
  Close,
  InfoFilled,
  QuestionFilled,
} from "@element-plus/icons-vue";
import { Codemirror as codemirror } from "vue-codemirror";
import { python } from "@codemirror/lang-python";
import { lintGutter } from "@codemirror/lint";
import { testScriptNode as apiTestScriptNode } from "@/services/api/workflowApiService";

interface Props {
  node: WorkflowNode;
  fields: FieldEntity[];
  tables?: TableEntity[];
  webhooks?: WebhookConfig[];
  /** 工作流全量节点列表（用于循环节点数据源选择） */
  allNodes?: WorkflowNode[];
  readonly?: boolean;
}

const props = defineProps<Props>();
const emit = defineEmits<{
  (e: "update:node", node: WorkflowNode): void;
  /** 选中循环体子节点切换配置面板 */
  (e: "select-child-node", nodeId: string): void;
  /** 在 loop 容器内添加子节点 */
  (e: "add-child-node", payload: { parentId: string; nodeType: WorkflowNodeType }): void;
  /** 删除 loop 容器内子节点 */
  (e: "remove-child-node", payload: { parentId: string; nodeId: string }): void;
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
    if (newNode.node_type === "script") {
      initScriptConfig();
    }
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

// ==================== 循环节点配置 ====================

const loopDataSource = computed<LoopDataSource>({
  get: () =>
    configValue<LoopDataSource>("data_source", { type: "find_records_all" }),
  set: (value) => setConfigValue("data_source", value),
});

const loopMaxIterations = computed({
  get: () => configValue<number>("max_iterations", 100),
  set: (value) => setConfigValue("max_iterations", value),
});

const loopErrorHandling = computed<"skip" | "terminate">({
  get: () => configValue<"skip" | "terminate">("error_handling", "skip"),
  set: (value) => setConfigValue("error_handling", value),
});

const loopEmptyResultAction = computed<"skip" | "error">({
  get: () => configValue<"skip" | "error">("empty_result_action", "skip"),
  set: (value) => setConfigValue("empty_result_action", value),
});

const loopBodyNodes = computed<WorkflowNode[]>(() => {
  if (localNode.value.node_type !== "loop") return [];
  return (localNode.value.config?.loop_body_nodes as WorkflowNode[] | undefined) ?? [];
});

/** 循环数据源下拉选项 */
const loopDataSourceOptions = computed(() => {
  const allNodes = props.allNodes ?? [props.node];
  return getAvailableLoopDataSources(allNodes, props.node.id, props.fields);
});

/** 将数据源对象序列化为可作 el-option value 的字符串 */
function loopDataSourceKey(ds: LoopDataSource): string {
  return `${ds.type}|${ds.node_id ?? ""}|${ds.field_id ?? ""}|${ds.trigger_field_id ?? ""}`;
}

const loopDataSourceValueKey = computed({
  get: () => loopDataSourceKey(loopDataSource.value),
  set: (key: string) => {
    const opt = loopDataSourceOptions.value.find(
      (o) => loopDataSourceKey(o.value) === key,
    );
    if (opt) {
      loopDataSource.value = opt.value;
    }
  },
});

/** 循环体允许添加的节点类型 */
const loopBodyAllowedTypes = LOOP_BODY_ALLOWED_NODE_TYPES;

function getLoopBodyNodeIcon(type: string) {
  return getNodeIcon(type);
}

function getLoopBodyNodeLabel(type: string) {
  return getNodeLabel(type);
}

/** 选中循环体子节点，切换到该子节点配置面板 */
function handleSelectLoopChild(nodeId: string) {
  emit("select-child-node", nodeId);
}

/** 删除循环体子节点 */
function handleRemoveLoopChild(nodeId: string) {
  if (props.readonly) return;
  emit("remove-child-node", { parentId: localNode.value.id, nodeId });
}

/**
 * 添加循环体子节点：
 * - loop 类型需校验数量与嵌套深度；
 * - 通过 emit('add-child-node') 由父组件统一处理。
 */
function handleAddLoopChild(type: WorkflowNodeType) {
  if (props.readonly) return;

  if (type === "loop") {
    const allNodes = props.allNodes ?? [props.node];
    const currentCount = countLoopNodes(allNodes);
    if (currentCount + 1 > MAX_LOOP_NODES_PER_WORKFLOW) {
      ElMessage.warning("单个工作流最多 5 个循环节点");
      return;
    }
    // 模拟添加后深度校验
    const simulatedBodyNodes: WorkflowNode[] = [
      ...loopBodyNodes.value,
      {
        id: "__simulated__",
        workflow_id: localNode.value.workflow_id,
        node_type: "loop",
        name: "simulated",
        config: { loop_body_nodes: [] },
        order: loopBodyNodes.value.length,
        next_nodes: [],
      },
    ];
    const simulatedNode: WorkflowNode = {
      ...localNode.value,
      config: { ...localNode.value.config, loop_body_nodes: simulatedBodyNodes },
    };
    const simulatedAllNodes = (props.allNodes ?? [props.node]).map((n) =>
      n.id === simulatedNode.id ? simulatedNode : n,
    );
    const newDepth = getMaxLoopNestingDepth(simulatedAllNodes);
    if (newDepth > MAX_LOOP_NESTING_DEPTH) {
      ElMessage.warning("循环嵌套深度不能超过 3 层");
      return;
    }
  }

  emit("add-child-node", { parentId: localNode.value.id, nodeType: type });
}

// ==================== 循环变量插入 ====================

/**
 * 递归在节点树中查找指定 ID 的节点（含 loop_body_nodes 嵌套）。
 * 用于定位循环体子节点的父 loop 容器节点（嵌套循环场景下父 loop 可能位于外层 loop_body_nodes 中）。
 */
function findNodeInTree(nodes: WorkflowNode[], id: string): WorkflowNode | null {
  for (const node of nodes) {
    if (node.id === id) return node;
    if (node.node_type === "loop") {
      const bodyNodes = (node.config?.loop_body_nodes as WorkflowNode[] | undefined) ?? [];
      const found = findNodeInTree(bodyNodes, id);
      if (found) return found;
    }
  }
  return null;
}

/** 当前节点的父 loop 容器节点 ID（不在循环体内返回 null） */
const parentLoopNodeId = computed<string | null>(() => {
  if (!props.node.id) return null;
  const allNodes = props.allNodes ?? [props.node];
  return findParentLoopNodeId(allNodes, props.node.id);
});

/** 当前节点是否位于 loop 容器内 */
const isInLoopBody = computed(() => parentLoopNodeId.value !== null);

/** 当前节点的父 loop 容器节点对象 */
const parentLoopNode = computed<WorkflowNode | null>(() => {
  const id = parentLoopNodeId.value;
  if (!id) return null;
  const allNodes = props.allNodes ?? [props.node];
  return findNodeInTree(allNodes, id);
});

/** 父 loop 节点的数据源配置 */
const parentLoopDataSource = computed<LoopDataSource | null>(() => {
  const loopNode = parentLoopNode.value;
  if (!loopNode) return null;
  return (loopNode.config?.data_source as LoopDataSource | undefined) ?? null;
});

/**
 * 数据源是否支持下钻字段：
 * - find_records_all → 数据为记录字典，支持下钻字段
 * - find_records_column / trigger_field → 数据为单值（人员/群组等），不支持下钻
 * - webhook_array → 数据结构未知，不支持下钻
 */
const loopDataSourceSupportsFieldDrill = computed(
  () => parentLoopDataSource.value?.type === "find_records_all",
);

/** 字段下钻可选项（仅 find_records_all 数据源时加载） */
const loopFieldDrillFields = ref<FieldEntity[]>([]);
const isLoadingLoopFieldDrillFields = ref(false);

async function loadLoopFieldDrillFields() {
  if (!loopDataSourceSupportsFieldDrill.value) {
    loopFieldDrillFields.value = [];
    return;
  }
  const ds = parentLoopDataSource.value;
  if (!ds?.node_id) {
    loopFieldDrillFields.value = [];
    return;
  }
  const allNodes = props.allNodes ?? [props.node];
  const findRecordsNode = allNodes.find((n) => n.id === ds.node_id);
  const targetTableId = findRecordsNode?.config?.target_table_id as string | undefined;
  if (!targetTableId) {
    loopFieldDrillFields.value = [];
    return;
  }
  isLoadingLoopFieldDrillFields.value = true;
  try {
    loopFieldDrillFields.value = await fieldService.getFieldsByTable(targetTableId);
  } catch {
    loopFieldDrillFields.value = [];
  } finally {
    isLoadingLoopFieldDrillFields.value = false;
  }
}

watch(
  [parentLoopDataSource, () => props.allNodes],
  () => {
    loadLoopFieldDrillFields();
  },
  { immediate: true },
);

/** 字段下钻选项（映射为 { id, name }） */
const loopFieldDrillOptions = computed(() =>
  loopFieldDrillFields.value.map((f) => ({ id: f.id, name: f.name })),
);

/** 循环变量是否可插入（仅循环体内 + 非只读 + 已知父 loop 数据源） */
const canInsertLoopVar = computed(
  () => isInLoopBody.value && !props.readonly && parentLoopDataSource.value !== null,
);

/**
 * 将循环变量片段追加到模板字符串末尾，并触发 ElMessage 提示。
 * 返回拼接后的新模板字符串，由调用方写入对应字段。
 */
function appendLoopVarSnippet(currentTemplate: string, snippet: string | undefined): string {
  if (!snippet) return currentTemplate ?? "";
  ElMessage.success("已插入循环变量");
  return `${currentTemplate ?? ""}${snippet}`;
}

// ==================== 脚本节点配置 ====================

const scriptConfig = ref<ScriptNodeConfig>({
  language: "python",
  script_source: "",
  timeout: 30,
  result_variable: "script_result",
  input_node_id: null,
  branches: [],
});

/** 从 localNode.config 初始化 scriptConfig */
function initScriptConfig() {
  const cfg = (localNode.value.config || {}) as Partial<ScriptNodeConfig>;
  scriptConfig.value = {
    language: "python",
    script_source: cfg.script_source || "",
    timeout: cfg.timeout ?? 30,
    result_variable: cfg.result_variable || "script_result",
    input_node_id: cfg.input_node_id ?? null,
    branches: Array.isArray(cfg.branches)
      ? cfg.branches.map((b): ScriptBranch => ({ ...b }))
      : [],
  };
}
initScriptConfig();
watch(() => localNode.value.node_type, (t) => {
  if (t === "script") initScriptConfig();
});

/** 将 scriptConfig 同步回 localNode.config 以触发 emit */
function syncScriptConfig() {
  localNode.value = {
    ...localNode.value,
    config: { ...scriptConfig.value } as Record<string, unknown>,
  };
}

/** 监听 scriptConfig 变化，自动同步到 localNode（不依赖 @change 事件） */
watch(
  scriptConfig,
  () => {
    if (!isUpdatingFromParent) {
      syncScriptConfig();
    }
  },
  { deep: true },
);

/** 结果变量引用提示（避免模板内联 {{ }} 拼接导致编译错误） */
const scriptResultVarHint = computed(() => {
  const varName = scriptConfig.value.result_variable || "script_result";
  return `下游节点可通过 {{${varName}.field}} 引用脚本输出`;
});

const scriptEditorExtensions = computed(() => [python(), lintGutter()]);

/** 帮助面板显示状态 */
const scriptHelpVisible = ref(false);

/** 脚本帮助文档内容 */
const scriptHelpApi = {
  setResult: "set_result(value)",
  setBranch: "set_branch(label)",
  modules: ["json", "re", "math", "datetime", "decimal", "collections", "itertools", "hashlib", "base64", "uuid", "statistics"],
  examples: [
    {
      title: "读取上游输入",
      code: `# input 为上游节点输出
data = input or {}
set_result({
    'received': True,
    'type': type(input).__name__,
})`,
    },
    {
      title: "处理查找记录结果",
      code: `# input 为 find_records 节点输出
data = input or {}
records = data.get('records', []) if isinstance(data, dict) else []
set_result({
    'count': len(records),
    'first': records[0] if records else None,
})`,
    },
    {
      title: "条件分支",
      code: `# 根据值路由到不同分支
value = input.get('score', 0) if isinstance(input, dict) else 0
if value > 80:
    set_branch('high')
elif value > 60:
    set_branch('medium')
else:
    set_branch('low')
set_result({'score': value})`,
    },
    {
      title: "数组聚合",
      code: `# 对数组求和与均值
import statistics
data = input if isinstance(input, list) else [input]
set_result({
    'count': len(data),
    'sum': sum(data),
    'avg': statistics.mean(data) if data else 0,
})`,
    },
    {
      title: "读取触发记录字段",
      code: `# context['record'] 为触发记录
record = context.get('record', {}) if isinstance(context, dict) else {}
field_value = record.get('field_id_here')
set_result({'field_value': field_value})`,
    },
    {
      title: "数据清洗",
      code: `# 清洗字符串字段
import re
data = input or {}
raw = data.get('phone', '') if isinstance(data, dict) else ''
phone = re.sub(r'\\D', '', raw)
set_result({'phone': phone, 'valid': len(phone) == 11})`,
    },
  ],
};

/** 输入来源候选：当前节点之前的节点（order 小于当前节点） */
const scriptInputCandidates = computed(() => {
  const cur = localNode.value;
  return (props.allNodes || []).filter(
    (n) => n.id !== cur.id && n.order < cur.order,
  );
});

/** 分支目标候选：当前节点之外的其他节点 */
const scriptBranchCandidates = computed(() => {
  const cur = localNode.value;
  return (props.allNodes || []).filter((n) => n.id !== cur.id);
});

const SCRIPT_TEMPLATES: { name: string; code: string }[] = [
  {
    name: "数据转换",
    code: '# 转换输入数据\nresult = {"processed": True, "input_type": type(input).__name__}\nset_result(result)',
  },
  {
    name: "条件分支",
    code: '# 根据条件设置分支\nvalue = input.get("score", 0) if isinstance(input, dict) else 0\nif value > 80:\n    set_branch("high")\nelif value > 60:\n    set_branch("medium")\nelse:\n    set_branch("low")\nset_result({"score": value})',
  },
  {
    name: "数组聚合",
    code: "# 对数组求和\nimport statistics\ndata = input if isinstance(input, list) else [input]\nset_result({\"count\": len(data), \"sum\": sum(data), \"avg\": statistics.mean(data) if data else 0})",
  },
  {
    name: "字段提取",
    code: '# 从记录中提取字段\nrecord = context.get("record", {}) if isinstance(context, dict) else {}\nset_result({"field_value": record.get("field_id_here")})',
  },
];

const currentLanguageTemplates = computed(() => SCRIPT_TEMPLATES);

function insertTemplate(name: string) {
  const tpl = currentLanguageTemplates.value.find((t) => t.name === name);
  if (tpl) {
    scriptConfig.value.script_source =
      (scriptConfig.value.script_source
        ? scriptConfig.value.script_source + "\n"
        : "") + tpl.code;
    syncScriptConfig();
  }
}

const scriptTestInput = ref("");

/** 示例输入 placeholder：展示上游节点实际输出格式 */
const scriptTestInputPlaceholder = [
  "模拟上游节点输出（即脚本中的 input 变量）",
  '查找记录：{"count":1,"records":[{"id":"r1","name":"张三"}]}',
  '更新/创建记录：{"record_id":"r1"}',
].join("\n");

const scriptTesting = ref(false);
const scriptTestResult = ref<{
  status: string;
  result: unknown;
  branch?: string | null;
  error?: string;
  duration_ms?: number;
  stdout?: string;
} | null>(null);

async function runScriptTest() {
  if (!scriptConfig.value.script_source.trim()) {
    ElMessage.warning("请先输入脚本代码");
    return;
  }
  let sampleInput: unknown = null;
  const raw = scriptTestInput.value.trim();
  if (raw) {
    try {
      sampleInput = JSON.parse(raw);
    } catch {
      ElMessage.warning("示例输入不是有效的 JSON");
      return;
    }
  }
  scriptTesting.value = true;
  scriptTestResult.value = null;
  try {
    const res = await apiTestScriptNode(localNode.value.workflow_id, {
      language: scriptConfig.value.language,
      script_source: scriptConfig.value.script_source,
      sample_input: sampleInput,
      timeout: scriptConfig.value.timeout,
    });
    scriptTestResult.value = res;
  } catch (e: unknown) {
    const err = e as { message?: string };
    scriptTestResult.value = {
      status: "error",
      result: null,
      error: err?.message || "请求失败",
    };
  } finally {
    scriptTesting.value = false;
  }
}

function formatScriptResult(r: unknown): string {
  try {
    return JSON.stringify(r, null, 2);
  } catch {
    return String(r);
  }
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

              <div
                v-if="useExpressionForUpdate[index]"
                class="template-input-with-loop-var">
                <el-input
                  :model-value="mapping.value_template"
                  placeholder="使用表达式（支持 {{trigger.record.field_id}}）"
                  class="template-input"
                  :disabled="readonly"
                  @update:model-value="(val) => updateMappingTemplate(index, val)" />
                <LoopVarInserter
                  v-if="canInsertLoopVar"
                  :supports-field-drill="loopDataSourceSupportsFieldDrill"
                  :field-options="loopFieldDrillOptions"
                  :disabled="isLoadingLoopFieldDrillFields"
                  @insert="(snippet) => updateMappingTemplate(index, appendLoopVarSnippet(mapping.value_template, snippet))" />
              </div>

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

              <div
                v-if="useExpressionForCreate[index]"
                class="template-input-with-loop-var">
                <el-input
                  :model-value="mapping.value_template"
                  placeholder="使用表达式（支持 {{trigger.record.field_id}}）"
                  class="template-input"
                  :disabled="readonly"
                  @update:model-value="(val) => updateCreateValueTemplate(index, val)" />
                <LoopVarInserter
                  v-if="canInsertLoopVar"
                  :supports-field-drill="loopDataSourceSupportsFieldDrill"
                  :field-options="loopFieldDrillOptions"
                  :disabled="isLoadingLoopFieldDrillFields"
                  @insert="(snippet) => updateCreateValueTemplate(index, appendLoopVarSnippet(mapping.value_template ?? '', snippet))" />
              </div>

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
            <div class="template-input-with-loop-var">
              <el-input
                v-model="emailSubject"
                placeholder="请输入邮件主题"
                :disabled="readonly" />
              <LoopVarInserter
                v-if="canInsertLoopVar"
                :supports-field-drill="loopDataSourceSupportsFieldDrill"
                :field-options="loopFieldDrillOptions"
                :disabled="isLoadingLoopFieldDrillFields"
                @insert="(snippet) => emailSubject = appendLoopVarSnippet(emailSubject, snippet)" />
            </div>
            <div class="field-hint" v-pre>支持 {{record.field_id}} 引用记录字段值</div>
          </el-form-item>

          <el-form-item label="邮件正文">
            <div class="template-input-with-loop-var">
              <el-input
                v-model="emailBody"
                type="textarea"
                :rows="6"
                placeholder="请输入邮件正文"
                :disabled="readonly" />
              <LoopVarInserter
                v-if="canInsertLoopVar"
                :supports-field-drill="loopDataSourceSupportsFieldDrill"
                :field-options="loopFieldDrillOptions"
                :disabled="isLoadingLoopFieldDrillFields"
                @insert="(snippet) => emailBody = appendLoopVarSnippet(emailBody, snippet)" />
            </div>
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
            <div class="template-input-with-loop-var">
              <el-input
                :model-value="inlineWebhook.body_template"
                type="textarea"
                :rows="4"
                placeholder="JSON 模板（注意对应webhook接口配置要求），支持通过 {{record}}、{{record.field_id}} 获取对应的数据"
                :disabled="readonly"
                @update:model-value="(val) => updateInlineWebhook({ body_template: val })" />
              <LoopVarInserter
                v-if="canInsertLoopVar"
                :supports-field-drill="loopDataSourceSupportsFieldDrill"
                :field-options="loopFieldDrillOptions"
                :disabled="isLoadingLoopFieldDrillFields"
                @insert="(snippet) => updateInlineWebhook({ body_template: appendLoopVarSnippet(inlineWebhook.body_template ?? '', snippet) })" />
            </div>
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

    <!-- 循环节点 -->
    <template v-else-if="localNode.node_type === 'loop'">
      <el-form label-position="top" class="config-form">
        <el-form-item label="循环方式">
          <el-select
            :model-value="'sequential'"
            disabled
            class="full-width">
            <el-option label="依次处理每条数据" value="sequential" />
          </el-select>
        </el-form-item>

        <el-form-item label="数据源">
          <el-select
            v-model="loopDataSourceValueKey"
            placeholder="选择数据源"
            class="full-width"
            :disabled="readonly">
            <el-option
              v-for="opt in loopDataSourceOptions"
              :key="loopDataSourceKey(opt.value)"
              :label="opt.label"
              :value="loopDataSourceKey(opt.value)" />
          </el-select>
          <div v-if="loopDataSourceOptions.length === 0" class="field-hint">
            暂无可用的前序数据源，请先在循环前添加"查找记录"或"Webhook"节点，或确保表格中存在人员/群组/附件/关联字段。
          </div>
        </el-form-item>

        <el-form-item label="最大循环次数">
          <el-input-number
            v-model="loopMaxIterations"
            :min="1"
            :max="1000"
            :controls="false"
            class="full-width"
            :disabled="readonly" />
        </el-form-item>

        <el-form-item label="错误处理方式">
          <el-radio-group v-model="loopErrorHandling" :disabled="readonly">
            <el-radio label="skip">跳过当次继续</el-radio>
            <el-radio label="terminate">终止流程</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item label="空结果处理">
          <el-radio-group v-model="loopEmptyResultAction" :disabled="readonly">
            <el-radio label="skip">跳过循环</el-radio>
            <el-radio label="error">报错</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>

      <!-- 循环体子节点编辑区 -->
      <div class="loop-body-section">
        <div class="loop-body-header">
          <span class="loop-body-title">循环体节点</span>
          <span class="loop-body-count">（{{ loopBodyNodes.length }}）</span>
        </div>

        <div class="loop-body-list">
          <div
            v-for="child in loopBodyNodes"
            :key="child.id"
            class="loop-body-item"
            @click="handleSelectLoopChild(child.id)">
            <el-icon class="loop-body-icon">
              <component :is="getLoopBodyNodeIcon(child.node_type)" />
            </el-icon>
            <div class="loop-body-info">
              <div class="loop-body-name">{{ child.name }}</div>
              <div class="loop-body-type">{{ getLoopBodyNodeLabel(child.node_type) }}</div>
            </div>
            <el-button
              v-if="!readonly"
              type="danger"
              :icon="Delete"
              link
              size="small"
              class="loop-body-delete-btn"
              @click.stop="handleRemoveLoopChild(child.id)" />
          </div>

          <el-empty
            v-if="loopBodyNodes.length === 0"
            description="暂无循环体节点"
            :image-size="60" />

          <div v-if="!readonly" class="loop-body-add">
            <el-dropdown placement="bottom-start" trigger="click">
              <el-button type="primary" :icon="Plus" text size="small">
                添加循环体节点
              </el-button>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item
                    v-for="item in loopBodyAllowedTypes"
                    :key="item.type"
                    @click="handleAddLoopChild(item.type as WorkflowNodeType)">
                    <el-icon><component :is="item.icon" /></el-icon>
                    <span>{{ item.label }}</span>
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </div>
      </div>
    </template>

    <!-- 自定义脚本节点 -->
    <template v-else-if="localNode.node_type === 'script'">
      <el-form label-position="top" class="config-form">
        <el-form-item label="脚本代码（python）">
          <div class="script-editor-wrapper">
            <codemirror
              v-model="scriptConfig.script_source"
              :extensions="scriptEditorExtensions"
              :disabled="readonly"
              :style="{ height: '300px' }" />
            <div class="script-editor-toolbar">
              <el-dropdown
                trigger="click"
                :disabled="readonly"
                @command="insertTemplate">
                <el-button
                  type="primary"
                  :icon="Plus"
                  link
                  size="small"
                  :disabled="readonly"
                  class="script-template-inserter-btn">
                  插入模板
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item
                      v-for="tpl in currentLanguageTemplates"
                      :key="tpl.name"
                      :command="tpl.name">
                      {{ tpl.name }}
                    </el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
              <el-button
                type="info"
                :icon="QuestionFilled"
                link
                size="small"
                class="script-help-btn"
                @click="scriptHelpVisible = !scriptHelpVisible">
                使用帮助
              </el-button>
            </div>
            <div v-show="scriptHelpVisible" class="script-help-panel">
              <div class="help-section">
                <div class="help-title">预置变量</div>
                <table class="help-table">
                  <thead>
                    <tr><th>变量</th><th>类型</th><th>说明</th></tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td><code>input</code></td>
                      <td>any</td>
                      <td>上游节点的输出数据（由"输入来源"决定）</td>
                    </tr>
                    <tr>
                      <td><code>context</code></td>
                      <td>object</td>
                      <td>工作流上下文，含 trigger / record / instance / workflow / loop / node_outputs</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div class="help-section">
                <div class="help-title">预置函数</div>
                <table class="help-table">
                  <thead>
                    <tr><th>函数</th><th>说明</th></tr>
                  </thead>
                  <tbody>
                    <tr>
                      <td><code>{{ scriptHelpApi.setResult }}</code></td>
                      <td>设置脚本输出结果（推荐）</td>
                    </tr>
                    <tr>
                      <td><code>{{ scriptHelpApi.setBranch }}</code></td>
                      <td>声明分支标签，路由到对应目标节点</td>
                    </tr>
                  </tbody>
                </table>
              </div>
              <div class="help-section">
                <div class="help-title">白名单模块</div>
                <div class="help-modules">
                  <el-tag
                    v-for="m in scriptHelpApi.modules"
                    :key="m"
                    size="small"
                    class="help-module-tag">{{ m }}</el-tag>
                </div>
              </div>
              <div class="help-section">
                <div class="help-title">执行规则</div>
                <ul class="help-rules">
                  <li>输出必须可 JSON 序列化，体积 ≤ 1MB</li>
                  <li>默认超时 30 秒（可配置 1-300 秒），超时强制终止</li>
                  <li>禁用文件 I/O、网络、子进程等危险操作</li>
                </ul>
              </div>
              <div class="help-example">
                <div class="help-title">常见场景示例</div>
                <div
                  v-for="ex in scriptHelpApi.examples"
                  :key="ex.title"
                  class="help-example-item">
                  <div class="help-example-title">{{ ex.title }}</div>
                  <pre>{{ ex.code }}</pre>
                </div>
              </div>
            </div>
          </div>
        </el-form-item>

        <el-form-item label="超时时间（秒）">
          <el-input-number v-model="scriptConfig.timeout" :min="1" :max="300" :disabled="readonly" @change="syncScriptConfig" />
        </el-form-item>

        <el-form-item label="结果变量名">
          <el-input v-model="scriptConfig.result_variable" :disabled="readonly" placeholder="script_result" @change="syncScriptConfig" />
          <div class="field-hint">{{ scriptResultVarHint }}</div>
        </el-form-item>

        <el-form-item label="输入来源">
          <el-select v-model="scriptConfig.input_node_id" :disabled="readonly" placeholder="默认取上一节点输出" clearable class="full-width" @change="syncScriptConfig">
            <el-option label="上一节点输出（默认）" :value="(null as any)" />
            <el-option v-for="n in scriptInputCandidates" :key="n.id" :label="n.name + ' (' + n.node_type + ')'" :value="n.id" />
          </el-select>
        </el-form-item>

        <el-form-item label="分支路由">
          <div class="script-branches">
            <div v-for="(b, idx) in scriptConfig.branches" :key="idx" class="script-branch-row">
              <el-input v-model="b.label" placeholder="分支标签" :disabled="readonly" style="width:140px" @change="syncScriptConfig" />
              <el-select v-model="b.target_node_id" placeholder="目标节点" :disabled="readonly" class="full-width" @change="syncScriptConfig">
                <el-option v-for="n in scriptBranchCandidates" :key="n.id" :label="n.name + ' (' + n.node_type + ')'" :value="n.id" />
              </el-select>
              <el-button v-if="!readonly" :icon="Delete" link @click="scriptConfig.branches.splice(idx, 1); syncScriptConfig()" />
            </div>
            <el-button v-if="!readonly" :icon="Plus" text size="small" @click="scriptConfig.branches.push({ label: '', target_node_id: '' })">添加分支</el-button>
            <div class="field-hint">脚本中调用 set_branch('标签') 即路由到对应目标节点</div>
          </div>
        </el-form-item>

        <el-divider content-position="left">测试运行</el-divider>
        <el-form-item label="示例输入（JSON）">
          <el-input v-model="scriptTestInput" type="textarea" :rows="4" :placeholder="scriptTestInputPlaceholder" :disabled="readonly" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="scriptTesting" :disabled="readonly" @click="runScriptTest">测试运行</el-button>
        </el-form-item>
        <div v-if="scriptTestResult" class="script-test-result">
          <div class="result-status" :class="{ success: scriptTestResult.status === 'success', error: scriptTestResult.status !== 'success' }">
            {{ scriptTestResult.status === 'success' ? '执行成功' : '执行失败' }}（耗时 {{ scriptTestResult.duration_ms || 0 }}ms）
          </div>
          <pre v-if="scriptTestResult.status === 'success'" class="result-json">{{ formatScriptResult(scriptTestResult.result) }}</pre>
          <pre v-if="scriptTestResult.status !== 'success'" class="result-error">{{ scriptTestResult.error }}</pre>
          <div v-if="scriptTestResult.stdout" class="result-stdout"><span class="hint">stdout:</span> {{ scriptTestResult.stdout }}</div>
        </div>
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
  margin-left: 8px;
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

.template-input-with-loop-var {
  display: flex;
  flex-direction: column;
  gap: $spacing-xs;
  width: 100%;

  .template-input {
    width: 100%;
  }
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

.loop-body-section {
  margin-top: $spacing-md;
  border-top: 1px solid $border-color;
  padding-top: $spacing-md;
}

.loop-body-header {
  display: flex;
  align-items: center;
  gap: $spacing-xs;
  margin-bottom: $spacing-sm;

  .loop-body-title {
    font-weight: 600;
    color: $text-primary;
  }

  .loop-body-count {
    font-weight: normal;
    color: $text-secondary;
    font-size: $font-size-sm;
  }
}

.loop-body-list {
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
}

.loop-body-item {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  padding: $spacing-sm;
  background-color: $bg-color;
  border-radius: $border-radius-md;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid $border-color;

  &:hover {
    background-color: rgba($primary-color, 0.04);
    border-color: rgba($primary-color, 0.4);
  }
}

.loop-body-icon {
  font-size: 18px;
  color: $primary-color;
  flex-shrink: 0;
}

.loop-body-info {
  flex: 1;
  min-width: 0;
}

.loop-body-name {
  font-weight: 500;
  color: $text-primary;
  font-size: $font-size-sm;
}

.loop-body-type {
  font-size: 12px;
  color: $text-secondary;
}

.loop-body-delete-btn {
  opacity: 0;
  transition: opacity 0.2s;

  .loop-body-item:hover & {
    opacity: 1;
  }
}

.loop-body-add {
  margin-top: $spacing-xs;
}

.script-editor-wrapper {
  width: 100%;
  border: 1px solid $border-color;
  border-radius: $border-radius-md;
  overflow: hidden;
  background-color: #fff;

  .script-editor-toolbar {
    display: flex;
    align-items: center;
    gap: $spacing-sm;
    padding: $spacing-xs $spacing-sm;
    border-top: 1px solid $border-color;
    background-color: $bg-color;
  }

  .script-template-inserter-btn,
  .script-help-btn {
    padding: 0;
  }

  .script-help-btn {
    margin-left: auto;
  }

  .script-help-panel {
    padding: $spacing-md;
    max-height: 360px;
    overflow-y: auto;
    border-top: 1px solid $border-color;
    background-color: $bg-color;
    font-size: $font-size-sm;

    .help-section {
      margin-bottom: $spacing-md;

      &:last-child {
        margin-bottom: 0;
      }
    }

    .help-title {
      margin-bottom: $spacing-xs;
      font-weight: 600;
      color: $text-primary;
    }

    .help-table {
      width: 100%;
      border-collapse: collapse;

      th,
      td {
        padding: $spacing-xs $spacing-sm;
        border: 1px solid $border-color;
        text-align: left;
        vertical-align: top;
      }

      th {
        background-color: #fff;
        font-weight: 600;
      }

      code {
        padding: 1px 4px;
        border-radius: $border-radius-sm;
        background-color: $gray-100;
        font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
        font-size: 12px;
        color: $primary-color;
      }
    }

    .help-modules {
      display: flex;
      flex-wrap: wrap;
      gap: $spacing-xs;
    }

    .help-module-tag {
      font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
    }

    .help-rules {
      margin: 0;
      padding-left: $spacing-lg;
      color: $text-secondary;

      li {
        line-height: 1.8;
      }
    }

    .help-example {
      .help-example-item {
        margin-bottom: $spacing-sm;

        &:last-child {
          margin-bottom: 0;
        }
      }

      .help-example-title {
        margin-bottom: $spacing-xs;
        font-weight: 600;
        color: $primary-color;
      }

      pre {
        margin: 0;
        padding: $spacing-sm;
        border-radius: $border-radius-sm;
        background-color: #fff;
        font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
        font-size: 12px;
        color: $text-primary;
        white-space: pre-wrap;
        word-break: break-word;
      }
    }
  }

  :deep(.cm-editor) {
    height: 100%;
    font-size: $font-size-sm;
  }

  :deep(.cm-scroller) {
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
  }
}

.script-branches {
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
  width: 100%;
}

.script-branch-row {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
}

.script-test-result {
  margin-top: $spacing-sm;
  padding: $spacing-sm;
  background-color: $bg-color;
  border-radius: $border-radius-md;
  border: 1px solid $border-color;

  .result-status {
    font-weight: 600;
    margin-bottom: $spacing-xs;

    &.success {
      color: $success-color;
    }

    &.error {
      color: $error-color;
    }
  }

  .result-json {
    margin: 0;
    padding: $spacing-sm;
    background-color: #fff;
    border-radius: $border-radius-sm;
    font-size: $font-size-xs;
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
    white-space: pre-wrap;
    word-break: break-all;
    max-height: 240px;
    overflow: auto;
  }

  .result-error {
    margin: 0;
    padding: $spacing-sm;
    background-color: #fff;
    border-radius: $border-radius-sm;
    font-size: $font-size-xs;
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
    color: $error-color;
    white-space: pre-wrap;
    word-break: break-all;
  }

  .result-stdout {
    margin-top: $spacing-xs;
    font-size: $font-size-xs;
    color: $text-secondary;

    .hint {
      color: $text-secondary;
      margin-right: 4px;
    }
  }
}
</style>
