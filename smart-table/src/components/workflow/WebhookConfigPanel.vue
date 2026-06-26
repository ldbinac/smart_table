<script setup lang="ts">
import { reactive, ref, watch } from "vue";
import { Delete, Plus } from "@element-plus/icons-vue";
import { ElMessage, type FormInstance, type FormRules } from "element-plus";
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

const variables = ["{{event}}", "{{record}}", "{{workflow}}", "{{instance}}"];

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
          <span class="hint-label">可用变量：</span>
          <el-tag
            v-for="variable in variables"
            :key="variable"
            size="small"
            class="variable-tag"
            @click="insertVariable(variable)"
          >
            {{ variable }}
          </el-tag>
        </div>
        <el-input
          v-model="form.body_template"
          type="textarea"
          :rows="6"
          placeholder='{"event": "{{event}}", "record": {{record}}}'
        />
      </el-form-item>

      <el-form-item label="签名密钥">
        <el-input
          v-model="form.secret"
          type="password"
          show-password
          placeholder="留空表示不启用签名验证"
        >
          <template #append>
            <el-button @click="generateSecret">自动生成</el-button>
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
