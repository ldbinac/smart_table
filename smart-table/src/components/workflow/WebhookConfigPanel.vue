<script setup lang="ts">
import { reactive, ref, watch } from "vue";
import { Delete, Plus } from "@element-plus/icons-vue";
import { type FormInstance, type FormRules } from "element-plus";
import { useWorkflowStore } from "@/stores/workflowStore";
import type { WebhookConfig, WebhookMethod } from "@/types/workflow";
import { useI18n } from "vue-i18n";

interface Props {
  webhook: WebhookConfig | null;
  baseId: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  (e: "saved", webhook: WebhookConfig): void;
  (e: "cancel"): void;
}>();

const workflowStore = useWorkflowStore();
const { t } = useI18n();
const formRef = ref<FormInstance>();
const testResultVisible = ref(false);
const testResult = ref<Record<string, unknown> | null>(null);

// ==================== 可用变量定义 ====================

interface VariableDef {
  /** 变量占位符，如 {{record}} */
  placeholder: string;
  /** 变量显示名称 */
  label: string;
  /** 变量含义 */
  description: string;
  /** 数据类型 */
  type: string;
  /** 默认值说明 */
  defaultValue: string;
  /** 使用注意事项 */
  notes: string;
  /** 变量分组 */
  group: "basic" | "loop";
}

const variableDefinitions = computed<VariableDef[]>(() => [
  {
    placeholder: "{{event}}",
    label: t("workflow.webhook.varEventLabel"),
    description: t("workflow.webhook.varEventDesc"),
    type: "object",
    defaultValue: "{}",
    notes: t("workflow.webhook.varEventNotes"),
    group: "basic",
  },
  {
    placeholder: "{{record}}",
    label: t("workflow.webhook.varRecordLabel"),
    description: t("workflow.webhook.varRecordDesc"),
    type: "object",
    defaultValue: "{}",
    notes: t("workflow.webhook.varRecordNotes"),
    group: "basic",
  },
  {
    placeholder: "{{workflow}}",
    label: t("workflow.webhook.varWorkflowLabel"),
    description: t("workflow.webhook.varWorkflowDesc"),
    type: "object",
    defaultValue: "{}",
    notes: t("workflow.webhook.varWorkflowNotes"),
    group: "basic",
  },
  {
    placeholder: "{{instance}}",
    label: t("workflow.webhook.varInstanceLabel"),
    description: t("workflow.webhook.varInstanceDesc"),
    type: "object",
    defaultValue: "{}",
    notes: t("workflow.webhook.varInstanceNotes"),
    group: "basic",
  },
  {
    placeholder: "{{loop.current_data}}",
    label: t("workflow.webhook.varCurrentDataLabel"),
    description: t("workflow.webhook.varCurrentDataDesc"),
    type: "object | any",
    defaultValue: t("workflow.webhook.noDefaultInLoop"),
    notes: t("workflow.webhook.varCurrentDataNotes"),
    group: "loop",
  },
  {
    placeholder: "{{loop.index}}",
    label: t("workflow.webhook.varIndexLabel"),
    description: t("workflow.webhook.varIndexDesc"),
    type: "number",
    defaultValue: t("workflow.webhook.noDefaultInLoop"),
    notes: t("workflow.webhook.varIndexNotes"),
    group: "loop",
  },
  {
    placeholder: "{{loop.round}}",
    label: t("workflow.webhook.varRoundLabel"),
    description: t("workflow.webhook.varRoundDesc"),
    type: "number",
    defaultValue: t("workflow.webhook.noDefaultInLoop"),
    notes: t("workflow.webhook.varRoundNotes"),
    group: "loop",
  },
  {
    placeholder: "{{loop.total}}",
    label: t("workflow.webhook.varTotalLabel"),
    description: t("workflow.webhook.varTotalDesc"),
    type: "number",
    defaultValue: t("workflow.webhook.noDefaultInLoop"),
    notes: t("workflow.webhook.varTotalNotes"),
    group: "loop",
  },
]);

/** 基础变量 */
const basicVariables = computed(() =>
  variableDefinitions.value.filter((v) => v.group === "basic"),
);

/** 循环变量 */
const loopVariables = computed(() =>
  variableDefinitions.value.filter((v) => v.group === "loop"),
);

/** 生成悬停提示 HTML */
function buildTooltipContent(def: VariableDef): string {
  return [
    `<div class="var-tooltip">`,
    `<div class="var-tooltip-name">${def.label}</div>`,
    `<div class="var-tooltip-desc">${def.description}</div>`,
    `<div class="var-tooltip-meta">`,
    `<span class="var-tooltip-type">${t("workflow.webhook.typeLabel")}${def.type}</span>`,
    `<span class="var-tooltip-default">${t("workflow.webhook.defaultLabel")}${def.defaultValue}</span>`,
    `</div>`,
    `<div class="var-tooltip-notes">${t("workflow.webhook.notesLabel")}${def.notes}</div>`,
    `</div>`,
  ].join("");
}

// ==================== 表单逻辑 ====================

interface HeaderItem {
  key: string;
  value: string;
}

interface RetryPolicy {
  max_retries: number;
  retry_interval: number;
}

const headerList = ref<HeaderItem[]>([]);

const defaultRetryPolicy: RetryPolicy = {
  max_retries: 3,
  retry_interval: 5,
};

const createEmptyForm = () => ({
  name: "",
  url: "",
  method: "POST" as WebhookMethod,
  body_template: "",
  secret: "",
  retry_policy: { ...defaultRetryPolicy },
  is_active: true,
});

const form = reactive(createEmptyForm());

const rules: FormRules = {
  name: [{ required: true, message: t("workflow.webhook.nameRequired"), trigger: "blur" }],
  url: [{ required: true, message: t("workflow.webhook.urlRequired"), trigger: "blur" }],
  method: [{ required: true, message: t("workflow.webhook.methodRequired"), trigger: "change" }],
};

const syncFormFromWebhook = () => {
  const w = props.webhook;
  Object.assign(form, {
    name: w?.name ?? "",
    url: w?.url ?? "",
    method: w?.method ?? "POST",
    body_template: w?.body_template ?? "",
    secret: w?.secret ?? "",
    is_active: w?.is_active ?? true,
    retry_policy: {
      ...defaultRetryPolicy,
      ...((w?.retry_policy as Record<string, unknown> | undefined) ?? {}),
    },
  });

  headerList.value = Object.entries(
    (w?.headers as Record<string, string> | undefined) ?? {},
  ).map(([key, value]) => ({ key, value }));
};

watch(() => props.webhook, syncFormFromWebhook, { immediate: true });

const addHeader = () => {
  headerList.value.push({ key: "", value: "" });
};

const removeHeader = (index: number) => {
  headerList.value.splice(index, 1);
};

const generateSecret = () => {
  const bytes = new Uint8Array(32);
  globalThis.crypto.getRandomValues(bytes);
  const binary = Array.from(bytes)
    .map((byte) => String.fromCharCode(byte))
    .join("");
  form.secret = globalThis.btoa(binary);
};

const insertVariable = (variable: string) => {
  form.body_template = form.body_template
    ? `${form.body_template}${variable}`
    : variable;
};

const buildPayload = (): Partial<WebhookConfig> => {
  const headers: Record<string, string> = {};
  headerList.value.forEach((item) => {
    if (item.key.trim()) {
      headers[item.key.trim()] = item.value;
    }
  });

  return {
    name: form.name,
    url: form.url,
    method: form.method,
    headers,
    body_template: form.body_template || null,
    secret: form.secret || null,
    retry_policy: form.retry_policy,
    is_active: form.is_active,
  };
};

const handleSave = async () => {
  if (!formRef.value) return;

  try {
    await formRef.value.validate();
  } catch {
    return;
  }

  const payload = buildPayload();

  try {
    if (props.webhook?.id) {
      const updated = await workflowStore.updateWebhook(props.webhook.id, payload);
      emit("saved", updated);
    } else {
      const created = await workflowStore.createWebhook(props.baseId, payload);
      emit("saved", created);
    }
  } catch {
    // 错误已由 workflowStore 统一处理
  }
};

const handleCancel = () => {
  emit("cancel");
};

const handleTest = async () => {
  if (!props.webhook?.id) return;

  try {
    const result = await workflowStore.testWebhook(props.webhook.id);
    testResult.value = result as Record<string, unknown>;
    testResultVisible.value = true;
  } catch {
    // 错误已由 workflowStore 统一处理
  }
};
</script>

<template>
  <div class="webhook-config-panel">
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
      <el-form-item :label="t('workflow.webhook.name')" prop="name">
        <el-input v-model="form.name" :placeholder="t('workflow.webhook.namePlaceholder')" />
      </el-form-item>

      <el-form-item :label="t('workflow.webhook.url')" prop="url">
        <el-input v-model="form.url" placeholder="https://example.com/webhook" />
      </el-form-item>

      <el-form-item :label="t('workflow.webhook.method')" prop="method">
        <el-select v-model="form.method" class="config-input">
          <el-option label="GET" value="GET" />
          <el-option label="POST" value="POST" />
          <el-option label="PUT" value="PUT" />
        </el-select>
      </el-form-item>

      <el-form-item :label="t('workflow.webhook.headers')">
        <div class="headers-list">
          <div
            v-for="(header, index) in headerList"
            :key="index"
            class="header-row"
          >
            <el-input v-model="header.key" placeholder="Key" />
            <el-input v-model="header.value" placeholder="Value" />
            <el-button
              type="danger"
              :icon="Delete"
              circle
              @click="removeHeader(index)"
            />
          </div>
          <el-button type="primary" :icon="Plus" @click="addHeader">
            {{ t('workflow.webhook.addHeader') }}
          </el-button>
        </div>
      </el-form-item>

      <el-form-item :label="t('workflow.webhook.bodyTemplate')">
        <div class="variable-hints">
          <span class="hint-label">{{ t('workflow.webhook.availableVars') }}</span>
          <el-tooltip
            v-for="v in basicVariables"
            :key="v.placeholder"
            placement="top"
            :show-after="300"
            raw-content
          >
            <template #content>
              <div v-html="buildTooltipContent(v)" />
            </template>
            <el-tag
              size="small"
              class="variable-tag"
              @click="insertVariable(v.placeholder)"
            >
              {{ v.placeholder }}
            </el-tag>
          </el-tooltip>
        </div>
        <div class="variable-hints variable-hints-loop">
          <span class="hint-label">{{ t('workflow.webhook.loopVars') }}</span>
          <el-tooltip
            v-for="v in loopVariables"
            :key="v.placeholder"
            placement="top"
            :show-after="300"
            raw-content
          >
            <template #content>
              <div v-html="buildTooltipContent(v)" />
            </template>
            <el-tag
              size="small"
              type="warning"
              class="variable-tag"
              @click="insertVariable(v.placeholder)"
            >
              {{ v.placeholder }}
            </el-tag>
          </el-tooltip>
        </div>
        <el-input
          v-model="form.body_template"
          type="textarea"
          :rows="6"
          placeholder='{"event": "{{event}}", "record": {{record}}}'
        />
      </el-form-item>

      <el-form-item :label="t('workflow.webhook.secret')">
        <el-input disabled
          v-model="form.secret"
          type="password"
          show-password
          :placeholder="t('workflow.webhook.secretPlaceholder')"
        >
          <template #append>
            <el-button disabled @click="generateSecret">{{ t('workflow.webhook.autoGen') }}</el-button>
          </template>
        </el-input>
      </el-form-item>

      <el-form-item :label="t('workflow.webhook.retryPolicy')">
        <div class="retry-row">
          <div class="retry-item">
            <span class="retry-label">{{ t('workflow.webhook.maxRetries') }}</span>
            <el-input-number
              v-model="form.retry_policy.max_retries"
              :min="0"
              :max="10"
              :step="1"
            />
          </div>
          <div class="retry-item">
            <span class="retry-label">{{ t('workflow.webhook.retryInterval') }}</span>
            <el-input-number
              v-model="form.retry_policy.retry_interval"
              :min="1"
              :max="3600"
              :step="1"
            />
          </div>
        </div>
      </el-form-item>

      <el-form-item :label="t('workflow.webhook.status')">
        <el-switch
          v-model="form.is_active"
          :active-text="t('workflow.webhook.enabled')"
          :inactive-text="t('workflow.webhook.disabled')"
        />
      </el-form-item>
    </el-form>

    <div class="actions">
      <el-button type="primary" :loading="workflowStore.loading" @click="handleSave">
        {{ t('workflow.webhook.save') }}
      </el-button>
      <el-button @click="handleCancel">{{ t('common.cancel') }}</el-button>
      <el-button :disabled="!webhook?.id" @click="handleTest">{{ t('workflow.webhook.testSend') }}</el-button>
    </div>

    <el-dialog v-model="testResultVisible" :title="t('workflow.webhook.testResult')" width="600px">
      <pre class="test-result">{{ JSON.stringify(testResult, null, 2) }}</pre>
    </el-dialog>
  </div>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;
@use "@/assets/styles/mixins" as *;

.webhook-config-panel {
  @include flex-column;
  gap: $spacing-md;
}

.config-input {
  width: 100%;
}

.headers-list {
  @include flex-column;
  gap: $spacing-sm;
  width: 100%;
}

.header-row {
  display: flex;
  align-items: center;
  gap: $spacing-sm;

  .el-input {
    flex: 1;
  }
}

.variable-hints {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: $spacing-xs;
  margin-bottom: $spacing-xs;

  .hint-label {
    font-size: $font-size-sm;
    color: $text-secondary;
  }
}

.variable-hints-loop {
  padding-left: $spacing-sm;
}

.variable-tag {
  cursor: pointer;
}

.retry-row {
  display: flex;
  gap: $spacing-lg;
}

.retry-item {
  @include flex-column;
  gap: $spacing-xs;

  .retry-label {
    font-size: $font-size-sm;
    color: $text-secondary;
  }
}

.actions {
  display: flex;
  gap: $spacing-sm;
  padding-top: $spacing-md;
  border-top: 1px solid $border-color;
}

.test-result {
  max-height: 400px;
  overflow: auto;
  background-color: #f5f7fa;
  padding: $spacing-md;
  border-radius: 4px;
  margin: 0;
}
</style>

<style lang="scss">
/* 悬停提示全局样式（raw-content 不受 scoped 限制） */
.var-tooltip {
  max-width: 360px;
  line-height: 1.5;
}

.var-tooltip-name {
  font-weight: 600;
  margin-bottom: 4px;
  color: var(--el-color-primary);
}

.var-tooltip-desc {
  font-size: 12px;
  margin-bottom: 6px;
  color: var(--el-color-secondary);
}

.var-tooltip-meta {
  display: flex;
  gap: 12px;
  font-size: 11px;
  color: var(--el-color-primary);
  margin-bottom: 4px;
}

.var-tooltip-notes {
  font-size: 11px;
  color: var(--el-color-secondary);
  border-top: 1px solid var(--el-border-color-lighter);
  padding-top: 4px;
  margin-top: 2px;
}
</style>
