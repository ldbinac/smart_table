<template>
  <div class="oauth-app-page">
    <div class="page-header">
      <div>
        <h1 class="page-title">{{ t("oauthApp.title") }}</h1>
        <p class="page-subtitle">{{ t("oauthApp.subtitle") }}</p>
      </div>
      <div class="header-actions">
        <el-button type="primary" @click="openCreate">
          <el-icon><Plus /></el-icon>
          {{ t("oauthApp.createApp") }}
        </el-button>
      </div>
    </div>

    <div class="page-content">
      <el-card shadow="never">
        <div class="filter-bar">
          <el-input
            v-model="searchQuery"
            :placeholder="t('oauthApp.searchPlaceholder')"
            clearable
            style="width: 320px"
            @clear="loadApps"
            @input="onSearch">
            <template #prefix><el-icon><Search /></el-icon></template>
          </el-input>
        </div>

        <el-table v-loading="loading" :data="filteredApps" style="width: 100%; margin-top: 16px">
          <el-table-column prop="app_name" :label="t('oauthApp.appName')" min-width="160" />
          <el-table-column prop="client_id" :label="t('oauthApp.clientId')" min-width="200">
            <template #default="{ row }">
              <code class="client-id">{{ row.client_id }}</code>
            </template>
          </el-table-column>
          <el-table-column :label="t('oauthApp.scopes')" min-width="240">
            <template #default="{ row }">
              <el-tag
                v-for="s in row.scopes"
                :key="s"
                size="small"
                type="info"
                class="scope-tag">
                {{ s }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column :label="t('oauthApp.allowedBases')" min-width="180">
            <template #default="{ row }">
              <template v-if="row.allowed_base_names && row.allowed_base_names.length">
                <el-tag
                  v-for="n in row.allowed_base_names"
                  :key="n"
                  size="small"
                  type="primary"
                  class="scope-tag">
                  {{ n }}
                </el-tag>
              </template>
              <span v-else class="empty-text">-</span>
            </template>
          </el-table-column>
          <el-table-column :label="t('oauthApp.status')" width="100">
            <template #default="{ row }">
              <el-tag :type="row.is_active ? 'success' : 'info'">
                {{ row.is_active ? t("oauthApp.enabled") : t("oauthApp.disabled") }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" :label="t('oauthApp.createdAt')" width="180">
            <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
          </el-table-column>
          <el-table-column :label="t('oauthApp.actions')" width="260" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" size="small" @click="openEdit(row as OAuthApp)">
                {{ t("oauthApp.editApp") }}
              </el-button>
              <el-button link type="success" size="small" @click="openTokens(row as OAuthApp)">
                  {{ t("oauthApp.viewTokens") }}
                </el-button>
                <el-button link type="info" size="small" @click="openAudit(row as OAuthApp)">
                    {{ t("oauthApp.viewAudit") }}
                </el-button>
                <el-tooltip
                    :content="t('oauthApp.resetSecretTip')"
                    placement="top"
                    :show-after="200">
                  <el-button link type="warning" size="small" @click="openResetSecret(row as OAuthApp)">
                      {{ t("oauthApp.resetSecret") }}
                  </el-button>
                </el-tooltip>
              <el-button link type="danger" size="small" @click="confirmDelete(row as OAuthApp)">
                {{ t("oauthApp.delete") }}
              </el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>

    <!-- 创建 / 编辑抽屉 -->
    <el-drawer append-to-body
      v-model="formVisible"
      size="460px"
      @closed="resetForm">
      <template #header>
        <div class="drawer-header">
          <span class="drawer-title">{{ formMode === 'create' ? t('oauthApp.createApp') : t('oauthApp.editApp') }}</span>
          <el-tooltip :content="t('oauthApp.helpDocs')" placement="bottom">
            <el-icon class="oauth-help-icon" @click="openOAuthDocs">
              <QuestionFilled />
            </el-icon>
          </el-tooltip>
        </div>
      </template>
      <el-form :model="form" label-position="top">
        <el-form-item :label="t('oauthApp.appName')" required>
          <el-input v-model="form.app_name" :placeholder="t('oauthApp.appNamePlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('oauthApp.callbackUrl')">
          <el-input v-model="form.callback_url" :placeholder="t('oauthApp.callbackUrlPlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('oauthApp.allowedBases')">
          <el-select
            v-model="form.allowed_bases"
            multiple
            filterable
            :placeholder="t('oauthApp.allowedBasesPlaceholder')"
            style="width: 100%">
            <el-option
              v-for="b in bases"
              :key="b.id"
              :label="b.name || b.id"
              :value="b.id" />
          </el-select>
        </el-form-item>
        <el-form-item :label="t('oauthApp.scopes')">
          <div class="scope-list">
            <div class="scope-hint">{{ t("oauthApp.scopeHint") }}</div>
            <el-checkbox-group v-model="form.scopes">
              <el-checkbox
                v-for="opt in scopeOptions"
                :key="opt.value"
                :value="opt.value"
                class="scope-item">
                <span class="scope-value">{{ opt.value }}</span>
                <span class="scope-desc">{{ opt.desc }}</span>
              </el-checkbox>
            </el-checkbox-group>
          </div>
        </el-form-item>
        <el-form-item :label="t('oauthApp.status')">
          <el-switch
            v-model="form.is_active"
            :active-text="t('oauthApp.enabled')"
            :inactive-text="t('oauthApp.disabled')" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="formVisible = false">{{ t("oauthApp.close") }}</el-button>
        <el-button type="primary" :loading="submitting" @click="submitForm">
          {{ formMode === "create" ? t("oauthApp.createApp") : t("oauthApp.editApp") }}
        </el-button>
      </template>
    </el-drawer>

    <!-- 重置密钥结果 -->
    <el-dialog v-model="secretVisible" :title="t('oauthApp.secretResetTitle')" width="520px"  append-to-body>
      <el-alert :title="t('oauthApp.secretResetDesc')" type="warning" :closable="false" show-icon />
      <div class="secret-block">
        <div class="secret-row">
          <span class="secret-label">{{ t("oauthApp.clientId") }}</span>
          <code>{{ secretApp?.client_id }}</code>
        </div>
        <div class="secret-row">
          <span class="secret-label">{{ t("oauthApp.newSecret") }}</span>
          <code class="secret-value">{{ secretApp?.client_secret }}</code>
          <el-button size="small" @click="copySecret">{{ t("oauthApp.copy") }}</el-button>
        </div>
      </div>
      <template #footer>
        <el-button type="primary" @click="secretVisible = false">{{ t("oauthApp.close") }}</el-button>
      </template>
    </el-dialog>

    <!-- 令牌列表 -->
    <el-dialog v-model="tokenVisible" :title="t('oauthApp.tokens')" width="640px"  append-to-body>
      <div class="dialog-toolbar">
        <el-button type="danger" plain :disabled="!hasActiveToken" @click="revokeAll">
          {{ t("oauthApp.revokeAll") }}
        </el-button>
      </div>
      <el-table :data="tokens" style="width: 100%">
        <el-table-column prop="jti" :label="t('oauthApp.jti')" min-width="200" />
        <el-table-column :label="t('oauthApp.scopes')" min-width="160">
          <template #default="{ row }">
            <el-tag v-for="s in row.scope" :key="s" size="small" type="info">{{ s }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="expires_at" :label="t('oauthApp.expiresAt')" width="160">
          <template #default="{ row }">{{ formatDate(row.expires_at) }}</template>
        </el-table-column>
        <el-table-column :label="t('oauthApp.status')" width="100">
          <template #default="{ row }">
            <el-tag :type="row.revoked ? 'info' : 'success'">
              {{ row.revoked ? t("oauthApp.revoked") : t("oauthApp.active") }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column :label="t('oauthApp.actions')" width="100" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="!row.revoked"
              link
              type="danger"
              size="small"
              @click="revokeSingle(row.jti)">
              {{ t("oauthApp.revokeSingle") }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <!-- 审计日志 -->
    <el-dialog v-model="auditVisible" :title="t('oauthApp.audit')" width="720px"  append-to-body>
      <el-table :data="auditLogs" style="width: 100%">
        <el-table-column prop="action" :label="t('oauthApp.auditAction')" width="140" />
        <el-table-column prop="detail" :label="t('oauthApp.auditDetail')" min-width="240" />
        <el-table-column prop="ip" :label="t('oauthApp.auditIp')" width="140" />
        <el-table-column prop="created_at" :label="t('oauthApp.auditTime')" width="180">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { Plus, Search, QuestionFilled } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { useI18n } from "vue-i18n";
import { formatDateTime } from "@/utils/timezone";
import {
  listOAuthApps,
  listOAuthBases,
  createOAuthApp,
  updateOAuthApp,
  deleteOAuthApp,
  resetOAuthSecret,
  listOAuthTokens,
  revokeOAuthTokens,
  listOAuthAudit,
  type OAuthApp,
  type BaseOption,
  type ApiAppToken,
  type ApiAppAuditLog,
} from "@/api/oauthApp";

const { t } = useI18n();

// 打开第三方应用（OAuth2 集成）帮助文档
function openOAuthDocs() {
  window.open(
    "https://my-smart-table.github.io/smart-table-docs/zh-CN/developer/app-integration/oauth2-integration.html",
    "_blank",
    "noopener",
  );
}

const apps = ref<OAuthApp[]>([]);
const bases = ref<BaseOption[]>([]);
const loading = ref(false);
const searchQuery = ref("");

const filteredApps = computed(() => {
  const q = searchQuery.value.trim().toLowerCase();
  if (!q) return apps.value;
  return apps.value.filter((a) => a.app_name.toLowerCase().includes(q));
});

const scopeOptions = [
  { value: "base:read", desc: t("oauthApp.scopeBaseRead") },
  { value: "table:read", desc: t("oauthApp.scopeTableRead") },
  { value: "table:write", desc: t("oauthApp.scopeTableWrite") },
  { value: "record:read", desc: t("oauthApp.scopeRecordRead") },
  { value: "record:write", desc: t("oauthApp.scopeRecordWrite") },
  { value: "field:read", desc: t("oauthApp.scopeFieldRead") },
];

const formVisible = ref(false);
const formMode = ref<"create" | "edit">("create");
const submitting = ref(false);
const editingId = ref<string | null>(null);
const form = ref({
  app_name: "",
  callback_url: "",
  allowed_bases: [] as string[],
  scopes: [] as string[],
  is_active: true,
});

const secretVisible = ref(false);
const secretApp = ref<OAuthApp | null>(null);

const tokenVisible = ref(false);
const tokens = ref<ApiAppToken[]>([]);
const tokenAppId = ref<string | null>(null);
const hasActiveToken = computed(() => tokens.value.some((tk) => !tk.revoked));

const auditVisible = ref(false);
const auditLogs = ref<ApiAppAuditLog[]>([]);

const formatDate = (v: string): string =>
  v ? formatDateTime(v, "YYYY-MM-DD HH:mm") : "";

const loadApps = async () => {
  loading.value = true;
  try {
    apps.value = await listOAuthApps();
  } catch {
    ElMessage.error(t("oauthApp.fetchFailed"));
  } finally {
    loading.value = false;
  }
};

const loadBases = async () => {
  try {
    bases.value = await listOAuthBases();
  } catch {
    /* 非关键 */
  }
};

let searchTimer: ReturnType<typeof setTimeout> | null = null;
const onSearch = () => {
  if (searchTimer) clearTimeout(searchTimer);
  searchTimer = setTimeout(loadApps, 300);
};

const resetForm = () => {
  form.value = {
    app_name: "",
    callback_url: "",
    allowed_bases: [],
    scopes: [],
    is_active: true,
  };
  editingId.value = null;
};

const openCreate = () => {
  formMode.value = "create";
  resetForm();
  formVisible.value = true;
};

const openEdit = (row: OAuthApp) => {
  formMode.value = "edit";
  editingId.value = row.id;
  form.value = {
    app_name: row.app_name,
    callback_url: row.callback_url || "",
    allowed_bases: [...row.allowed_bases],
    scopes: [...row.scopes],
    is_active: row.is_active,
  };
  formVisible.value = true;
};

const submitForm = async () => {
  if (!form.value.app_name.trim()) {
    ElMessage.warning(t("oauthApp.appNamePlaceholder"));
    return;
  }
  submitting.value = true;
  try {
    if (formMode.value === "create") {
      await createOAuthApp({
        app_name: form.value.app_name.trim(),
        callback_url: form.value.callback_url || undefined,
        allowed_bases: form.value.allowed_bases,
        scopes: form.value.scopes,
        is_active: form.value.is_active,
      });
    } else if (editingId.value) {
      await updateOAuthApp(editingId.value, {
        app_name: form.value.app_name.trim(),
        callback_url: form.value.callback_url || undefined,
        allowed_bases: form.value.allowed_bases,
        scopes: form.value.scopes,
        is_active: form.value.is_active,
      });
    }
    formVisible.value = false;
    await loadApps();
  } catch {
    ElMessage.error(
      formMode.value === "create"
        ? t("oauthApp.createFailed")
        : t("oauthApp.updateFailed"),
    );
  } finally {
    submitting.value = false;
  }
};

const confirmDelete = (row: OAuthApp) => {
  ElMessageBox.confirm(
    t("oauthApp.confirmDelete", { name: row.app_name }),
    t("oauthApp.delete"),
    { confirmButtonText: t("oauthApp.delete"), cancelButtonText: t("oauthApp.close"), type: "warning" },
  )
    .then(async () => {
      try {
        await deleteOAuthApp(row.id);
        await loadApps();
      } catch {
        ElMessage.error(t("oauthApp.deleteFailed"));
      }
    })
    .catch(() => {});
};

const openResetSecret = (row: OAuthApp) => {
  ElMessageBox.confirm(
    t("oauthApp.resetSecretConfirm", { name: row.app_name }),
    t("oauthApp.resetSecret"),
    { confirmButtonText: t("oauthApp.resetSecret"), cancelButtonText: t("oauthApp.close"), type: "warning" },
  )
    .then(async () => {
      try {
        const updated = await resetOAuthSecret(row.id);
        secretApp.value = updated;
        secretVisible.value = true;
        await loadApps();
      } catch {
        ElMessage.error(t("oauthApp.resetFailed"));
      }
    })
    .catch(() => {});
};

const copySecret = async () => {
  if (!secretApp.value?.client_secret) return;
  try {
    await navigator.clipboard.writeText(secretApp.value.client_secret);
    ElMessage.success(t("oauthApp.copied"));
  } catch {
    /* 忽略 */
  }
};

const openTokens = async (row: OAuthApp) => {
  tokenAppId.value = row.id;
  tokenVisible.value = true;
  try {
    tokens.value = await listOAuthTokens(row.id);
  } catch {
    tokens.value = [];
  }
};

const revokeAll = () => {
  if (!tokenAppId.value) return;
  ElMessageBox.confirm(t("oauthApp.revokeAllConfirm"), t("oauthApp.revokeAll"), {
    confirmButtonText: t("oauthApp.revokeAll"),
    cancelButtonText: t("oauthApp.close"),
    type: "warning",
  })
    .then(async () => {
      try {
        await revokeOAuthTokens(tokenAppId.value!);
        tokens.value = await listOAuthTokens(tokenAppId.value!);
      } catch {
        ElMessage.error(t("oauthApp.revokeFailed"));
      }
    })
    .catch(() => {});
};

const revokeSingle = (jti: string) => {
  if (!tokenAppId.value) return;
  ElMessageBox.confirm(t("oauthApp.revokeSingleConfirm"), t("oauthApp.revokeAll"), {
    confirmButtonText: t("oauthApp.revokeAll"),
    cancelButtonText: t("oauthApp.close"),
    type: "warning",
  })
    .then(async () => {
      try {
        await revokeOAuthTokens(tokenAppId.value!, jti);
        tokens.value = await listOAuthTokens(tokenAppId.value!);
      } catch {
        ElMessage.error(t("oauthApp.revokeFailed"));
      }
    })
    .catch(() => {});
};

const openAudit = async (row: OAuthApp) => {
  auditVisible.value = true;
  try {
    auditLogs.value = await listOAuthAudit(row.id);
  } catch {
    auditLogs.value = [];
  }
};

onMounted(() => {
  loadApps();
  loadBases();
});
</script>

<style scoped lang="scss">
.oauth-app-page {
  padding: 24px;

  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 24px;

    .page-title {
      font-size: 24px;
      font-weight: 600;
      margin: 0;
    }
    .page-subtitle {
      margin: 6px 0 0;
      color: #606266;
      font-size: 14px;
      max-width: 640px;
    }

    .header-actions {
      display: flex;
      align-items: center;
      gap: $spacing-md;
    }
  }

  .page-content {
    .el-card {
      border-radius: 8px;
    }
    .filter-bar {
      display: flex;
      justify-content: flex-start;
    }
  }
}

.client-id {
  font-family: "SFMono-Regular", Consolas, monospace;
  font-size: 12px;
  color: #606266;
  background: #f5f7fa;
  padding: 2px 6px;
  border-radius: 4px;
}

.scope-tag {
  margin: 0 4px 4px 0;
}

.empty-text {
  color: #c0c4cc;
}

.scope-list {
  width: 100%;
  .scope-hint {
    font-size: 12px;
    color: #909399;
    margin-bottom: 8px;
  }
  .scope-item {
    display: flex;
    align-items: baseline;
    width: 100%;
    height: auto;
    margin-right: 0;
    margin-bottom: 8px;
    white-space: normal;
    .scope-value {
      font-family: monospace;
      font-weight: 600;
      margin-right: 8px;
    }
    .scope-desc {
      color: #909399;
      font-size: 12px;
    }
  }
}

.secret-block {
  margin-top: 16px;
  .secret-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 12px;
    .secret-label {
      width: 110px;
      color: #606266;
      flex-shrink: 0;
    }
    code {
      flex: 1;
      background: #f5f7fa;
      padding: 6px 8px;
      border-radius: 4px;
      word-break: break-all;
      font-size: 12px;
    }
    .secret-value {
      color: #f56c6c;
    }
  }
}

.dialog-toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 12px;
}

/* 抽屉 header 使用 append-to-body，渲染在 .oauth-app-page 之外，故置于顶层作用域 */
.drawer-header {
  display: flex;
  align-items: center;
  gap: $spacing-sm;

  .drawer-title {
    font-size: 16px;
    font-weight: 600;
  }

  .oauth-help-icon {
    font-size: 16px;
    color: $text-secondary;
    cursor: pointer;
    transition: color 0.2s ease;

    &:hover {
      color: $primary-color;
    }
  }
}
</style>
