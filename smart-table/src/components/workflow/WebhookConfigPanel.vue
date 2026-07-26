<script setup lang="ts">
import { reactive, ref, watch } from "vue";
import { Delete, Plus } from "@element-plus/icons-vue";
import { type FormInstance, type FormRules } from "element-plus";
import { useWorkflowStore } from "@/stores/workflowStore";
import type { WebhookConfig, WebhookMethod } from "@/types/workflow";

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

const variableDefinitions: VariableDef[] = [
  {
    placeholder: "{{event}}",
    label: "触发事件",
    description: "触发工作流执行的完整事件对象，包含事件类型 (event_type)、表格 ID (table_id)、记录 ID (record_id)、变更字段 (changes) 等信息",
    type: "object",
    defaultValue: "{}",
    notes: "支持点号路径访问子属性，如 {{event.event_type}}、{{event.table_id}}",
    group: "basic",
  },
  {
    placeholder: "{{record}}",
    label: "触发记录",
    description: "触发工作流执行的记录数据，键为字段 ID，值为字段值。对于记录创建/更新触发，包含完整的记录字段值",
    type: "object",
    defaultValue: "{}",
    notes: "支持点号路径访问具体字段，如 {{record.field_id}}。若为指定时间触发则可能为空对象",
    group: "basic",
  },
  {
    placeholder: "{{workflow}}",
    label: "工作流信息",
    description: "当前执行的工作流元数据，包含工作流 ID、名称、状态、版本号等信息",
    type: "object",
    defaultValue: "{}",
    notes: "主要用于传递工作流上下文信息给外部系统",
    group: "basic",
  },
  {
    placeholder: "{{instance}}",
    label: "执行实例",
    description: "当前工作流执行实例信息，包含实例 ID、触发类型、状态、创建时间等",
    type: "object",
    defaultValue: "{}",
    notes: "可用于追踪和关联工作流执行记录",
    group: "basic",
  },
  {
    placeholder: "{{loop.current_data}}",
    label: "当前循环数据",
    description: "当前循环迭代的数据项。当数据源为 find_records_all 时，为完整的记录字典（字段ID→字段值）；当为 find_records_column 时，为提取的单值或去重后的列表项",
    type: "object | any",
    defaultValue: "无（必须处于循环体内）",
    notes: "仅在循环体内可用。支持字段下钻：{{loop.current_data.field_id}} 可获取具体字段值（仅 find_records_all 数据源支持）",
    group: "loop",
  },
  {
    placeholder: "{{loop.index}}",
    label: "循环索引",
    description: "当前循环迭代的零基索引，从 0 开始计数",
    type: "number",
    defaultValue: "无（必须处于循环体内）",
    notes: "仅在循环体内可用。第一次迭代为 0，第二次为 1，以此类推",
    group: "loop",
  },
  {
    placeholder: "{{loop.round}}",
    label: "循环轮数",
    description: "当前循环迭代的一基轮数，从 1 开始计数",
    type: "number",
    defaultValue: "无（必须处于循环体内）",
    notes: "仅在循环体内可用。round = index + 1，适合面向用户的序号展示",
    group: "loop",
  },
  {
    placeholder: "{{loop.total}}",
    label: "循环总轮数",
    description: "当前循环的总迭代次数，等于 min(data_array.length, max_iterations)",
    type: "number",
    defaultValue: "无（必须处于循环体内）",
    notes: "仅在循环体内可用。可用于计算进度百分比，如 {{loop.round}}/{{loop.total}}",
    group: "loop",
  },
];

/** 基础变量 */
const basicVariables = variableDefinitions.filter((v) => v.group === "basic");

/** 循环变量 */
const loopVariables = variableDefinitions.filter((v) => v.group === "loop");

/** 生成悬停提示 HTML */
function buildTooltipContent(def: VariableDef): string {
  return [
    `<div class="var-tooltip">`,
    `<div class="var-tooltip-name">${def.label}</div>`,
    `<div class="var-tooltip-desc">${def.description}</div>`,
    `<div class="var-tooltip-meta">`,
    `<span class="var-tooltip-type">类型: ${def.type}</span>`,
    `<span class="var-tooltip-default">默认: ${def.defaultValue}</span>`,
    `</div>`,
    `<div class="var-tooltip-notes">注意: ${def.notes}</div>`,
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
  name: [{ required: true, message: "请输入 Webhook 名称", trigger: "blur" }],
  url: [{ required: true, message: "请输入请求 URL", trigger: "blur" }],
  method: [{ required: true, message: "请选择 HTTP 方法", trigger: "change" }],
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
      <el-form-item label="名称" prop="name">
        <el-input v-model="form.name" placeholder="请输入 Webhook 名称" />
      </el-form-item>

      <el-form-item label="URL" prop="url">
        <el-input v-model="form.url" placeholder="https://example.com/webhook" />
      </el-form-item>

      <el-form-item label="HTTP 方法" prop="method">
        <el-select v-model="form.method" class="config-input">
          <el-option label="GET" value="GET" />
          <el-option label="POST" value="POST" />
          <el-option label="PUT" value="PUT" />
        </el-select>
      </el-form-item>

      <el-form-item label="请求头">
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
            添加请求头
          </el-button>
        </div>
      </el-form-item>

      <el-form-item label="请求体模板">
        <div class="variable-hints">
          <span class="hint-label">可用变量（点击插入）：</span>
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
          <span class="hint-label">循环变量（点击插入，仅循环体内触发）：</span>
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

      <el-form-item label="签名密钥">
        <el-input disabled
          v-model="form.secret"
          type="password"
          show-password
          placeholder="留空表示不启用签名验证"
        >
          <template #append>
            <el-button disabled @click="generateSecret">自动生成</el-button>
          </template>
        </el-input>
      </el-form-item>

      <el-form-item label="重试策略">
        <div class="retry-row">
          <div class="retry-item">
            <span class="retry-label">最大重试次数</span>
            <el-input-number
              v-model="form.retry_policy.max_retries"
              :min="0"
              :max="10"
              :step="1"
            />
          </div>
          <div class="retry-item">
            <span class="retry-label">重试间隔（秒）</span>
            <el-input-number
              v-model="form.retry_policy.retry_interval"
              :min="1"
              :max="3600"
              :step="1"
            />
          </div>
        </div>
      </el-form-item>

      <el-form-item label="启用状态">
        <el-switch
          v-model="form.is_active"
          active-text="启用"
          inactive-text="禁用"
        />
      </el-form-item>
    </el-form>

    <div class="actions">
      <el-button type="primary" :loading="workflowStore.loading" @click="handleSave">
        保存
      </el-button>
      <el-button @click="handleCancel">取消</el-button>
      <el-button :disabled="!webhook?.id" @click="handleTest">测试发送</el-button>
    </div>

    <el-dialog v-model="testResultVisible" title="测试结果" width="600px">
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
