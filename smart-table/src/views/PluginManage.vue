<script setup lang="ts">
/**
 * 插件管理页（系统管理员）
 *
 * 卡片式插件列表 + 上传安装包 + 启用/禁用/配置/升级/回滚/卸载 + 脚本运行日志。
 * 权限：页面级由 adminGuard 限制（与 /admin/* 管理页一致）。
 */
import { ref, onMounted, onUnmounted, computed, watch } from "vue";
import { useI18n } from "vue-i18n";
import { ElMessage, ElMessageBox } from "element-plus";
import { Upload, Refresh, Plus } from "@element-plus/icons-vue";
import { usePluginStore } from "@/stores/pluginStore";
import { invalidatePluginsCache } from "@/plugins/registry";
import { getBases } from "@/services/api/baseApiService";
import PluginTypeTag from "@/components/plugins/PluginTypeTag.vue";
import type {
  PluginEntity,
  PluginStatus,
  PluginRunLog,
} from "@/plugins/types";
import type { UploadUserFile, UploadInstance } from "element-plus";

const { t } = useI18n();
const store = usePluginStore();

const selectedFile = ref<File | null>(null);
const uploadDialogVisible = ref(false);
const uploadRef = ref<UploadInstance | null>(null);
const rollbackDialogVisible = ref(false);
const configDialogVisible = ref(false);
const logDialogVisible = ref(false);
const logBaseId = ref("");

const rollbackTarget = ref<PluginEntity | null>(null);
const rollbackVersion = ref("");
const rollbackVersions = ref<string[]>([]);

const configTarget = ref<PluginEntity | null>(null);
const configScope = ref<"global" | "base">("global");
const configBaseId = ref("");
const configText = ref("");

const logTarget = ref<PluginEntity | null>(null);

const runDialogVisible = ref(false);
const runTarget = ref<PluginEntity | null>(null);
const runBaseId = ref("");

const runResultVisible = ref(false);

interface RunResultView {
  status: string;
  durationMs?: number;
  output: string;
  result: unknown;
  error?: string;
  baseId: string;
  baseName: string;
  pluginId: string;
}
const runResult = ref<RunResultView | null>(null);

function runStatusType(
  status: string,
): "success" | "warning" | "danger" | "info" {
  if (status === "success") return "success";
  if (status === "timeout") return "warning";
  if (status === "running") return "info";
  return "danger";
}

function runStatusText(status: string): string {
  if (status === "success") return t("plugin.runResultDialog.statusSuccess");
  if (status === "timeout") return t("plugin.runResultDialog.statusTimeout");
  if (status === "running") return t("plugin.runLogDialog.statusRunning");
  return t("plugin.runResultDialog.statusFailed");
}

/** 结果单行摘要（表格列用，超长由 tooltip 展示） */
function resultSummary(result: unknown): string {
  if (result === undefined || result === null) return "-";
  try {
    return JSON.stringify(result);
  } catch {
    return String(result);
  }
}

/** 结果多行格式化（详情弹窗用） */
function formatResultText(result: unknown): string {
  if (result === undefined || result === null) return "-";
  try {
    return JSON.stringify(result, null, 2);
  } catch {
    return String(result);
  }
}

function formatDuration(ms?: number): string {
  return ms != null ? `${(ms / 1000).toFixed(1)}s` : "-";
}

/** 结果弹窗多行文本：脚本返回值 + 运行输出 + 错误信息 */
const runResultText = computed(() => {
  const r = runResult.value;
  if (!r) return "";
  const parts: string[] = [];
  if (r.result !== undefined && r.result !== null) {
    try {
      parts.push(
        `【${t("plugin.runResultDialog.resultLabel")}】\n` +
          JSON.stringify(r.result, null, 2),
      );
    } catch {
      parts.push(
        `【${t("plugin.runResultDialog.resultLabel")}】\n` + String(r.result),
      );
    }
  }
  if (r.output) {
    parts.push(`【${t("plugin.runResultDialog.outputLabel")}】\n` + r.output);
  }
  if (r.error) {
    parts.push(`【${t("plugin.messages.runFailed")}】\n` + r.error);
  }
  return parts.join("\n\n") || "-";
});

/** 脚本插件运行/日志需要 Base 上下文：管理员选择一个目标 Base */
const bases = ref<Array<{ id: string; name: string }>>([]);
const selectedBaseId = ref("");

const statusType = computed(() => (status: PluginStatus) => {
  switch (status) {
    case "enabled":
      return "success";
    case "disabled":
      return "info";
    case "error":
      return "danger";
    default:
      return "warning";
  }
});

onMounted(async () => {
  try {
    const list = await getBases();
    bases.value = (list || []).map((b) => ({ id: b.id, name: b.name }));
    if (bases.value.length > 0) selectedBaseId.value = bases.value[0].id;
  } catch (error) {
    console.warn("[PluginManage] Base 列表加载失败（脚本运行将不可用）:", error);
  }
  await store.loadPlugins(selectedBaseId.value || undefined);
});

// 离开插件管理页时使 registry 的插件列表缓存失效：
// 管理页的安装/启停/卸载等变更需要让 Base 页面下次挂载时重新拉取
onUnmounted(() => {
  invalidatePluginsCache();
});

/** 切换 Base：重新加载列表并附带该 Base 的安装/生效状态 */
watch(selectedBaseId, (baseId) => {
  store.loadPlugins(baseId || undefined);
});

function onFileChange(file: { raw?: File } | UploadUserFile): void {
  const raw = (file as { raw?: File }).raw;
  selectedFile.value = raw ?? null;
}

/** 弹窗关闭后清空选择状态，避免再次打开时残留上次的安装包 */
function onUploadDialogClosed(): void {
  selectedFile.value = null;
  uploadRef.value?.clearFiles();
}

async function handleUpload(): Promise<void> {
  if (!selectedFile.value) {
    ElMessage.warning(t("plugin.messages.selectFileFirst"));
    return;
  }
  try {
    const result = await store.upload(selectedFile.value);
    ElMessage.success(
      result?.action === "upgraded"
        ? t("plugin.messages.upgradeSuccess")
        : t("plugin.messages.uploadSuccess"),
    );
    uploadDialogVisible.value = false;
    selectedFile.value = null;
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    ElMessage.error(`${t("plugin.messages.uploadFailed")}: ${message}`);
  }
}

async function handleToggleStatus(plugin: PluginEntity): Promise<void> {
  const next: PluginStatus = plugin.status === "enabled" ? "disabled" : "enabled";
  if (next === "disabled") {
    await ElMessageBox.confirm(
      t("plugin.confirm.disableContent"),
      t("plugin.confirm.disableTitle"),
      { type: "warning" },
    );
  }
  await store.setStatus(plugin.id, next);
  ElMessage.success(
    next === "enabled"
      ? t("plugin.messages.enableSuccess")
      : t("plugin.messages.disableSuccess"),
  );
}

async function handleUninstall(plugin: PluginEntity): Promise<void> {
  await ElMessageBox.confirm(
    t("plugin.confirm.uninstallContent"),
    t("plugin.confirm.uninstallTitle"),
    { type: "warning", confirmButtonText: t("plugin.actions.uninstall") },
  );
  await store.uninstall(plugin.id);
  ElMessage.success(t("plugin.messages.uninstallSuccess"));
}

async function openRollback(plugin: PluginEntity): Promise<void> {
  rollbackTarget.value = plugin;
  rollbackVersion.value = "";
  const versions = await store.loadVersions(plugin.id);
  rollbackVersions.value = versions.map((v) => v.version);
  rollbackDialogVisible.value = true;
}

async function handleRollback(): Promise<void> {
  if (!rollbackTarget.value || !rollbackVersion.value) return;
  await store.rollback(rollbackTarget.value.id, rollbackVersion.value);
  ElMessage.success(t("plugin.messages.rollbackSuccess"));
  rollbackDialogVisible.value = false;
}

async function openConfig(plugin: PluginEntity): Promise<void> {
  configTarget.value = plugin;
  configScope.value = "global";
  configBaseId.value = selectedBaseId.value || bases.value[0]?.id || "";
  await loadConfigForScope();
  configDialogVisible.value = true;
}

/** 按当前作用域加载配置：global 读全局存储；base 读所选 Base 的存储（非合并视图） */
async function loadConfigForScope(): Promise<void> {
  if (!configTarget.value) return;
  if (configScope.value === "base" && !configBaseId.value) {
    configText.value = "{}";
    return;
  }
  try {
    const cfg =
      configScope.value === "global"
        ? await store.loadConfig(configTarget.value.id)
        : await store.loadConfig(configTarget.value.id, configBaseId.value, "base");
    configText.value = JSON.stringify(cfg ?? {}, null, 2);
  } catch (error) {
    console.warn("[PluginManage] 配置加载失败:", error);
    configText.value = "{}";
  }
}

async function handleSaveConfig(): Promise<void> {
  if (!configTarget.value) return;
  if (configScope.value === "base" && !configBaseId.value) {
    ElMessage.warning(t("plugin.detail.selectBaseFirst"));
    return;
  }
  let parsed: Record<string, unknown>;
  try {
    parsed = JSON.parse(configText.value) as Record<string, unknown>;
  } catch {
    ElMessage.error(t("plugin.configDialog.invalidJson"));
    return;
  }
  try {
    await store.saveConfig(
      configTarget.value.id,
      configScope.value,
      parsed,
      configScope.value === "base" ? configBaseId.value : undefined,
    );
  } catch (error) {
    // 后端错误信息已由请求拦截器弹出，这里仅避免未处理的 Promise 拒绝
    console.warn("[PluginManage] 配置保存失败:", error);
    return;
  }
  ElMessage.success(t("plugin.messages.configSaved"));
  configDialogVisible.value = false;
}

/** 点"运行"：弹出对话框显式选择目标 Base，与查询条件区（运行日志用）解耦 */
function openRunDialog(plugin: PluginEntity): void {
  runTarget.value = plugin;
  runBaseId.value = selectedBaseId.value || bases.value[0]?.id || "";
  runDialogVisible.value = true;
}

async function handleRunConfirm(): Promise<void> {
  if (!runTarget.value) return;
  if (!runBaseId.value) {
    ElMessage.warning(t("plugin.detail.selectBaseFirst"));
    return;
  }
  const plugin = runTarget.value;
  const baseId = runBaseId.value;
  try {
    const result = await store.run(plugin.id, baseId);
    // 显式带上本次运行的 Base 名称，避免与查询条件区/配置弹窗所选 Base 混淆
    const baseName = bases.value.find((b) => b.id === baseId)?.name ?? baseId;
    runResult.value = {
      status: result.status,
      durationMs: result.duration_ms,
      output: result.output ?? "",
      result: result.result ?? null,
      error: result.error,
      baseId,
      baseName,
      pluginId: plugin.id,
    };
    runDialogVisible.value = false;
    runResultVisible.value = true;
  } catch (error) {
    // 网络异常/超时/5xx 已由请求拦截器弹出提示；弹窗保持打开便于重试
    console.warn("[PluginManage] 插件运行失败:", error);
  }
}

/** 结果弹窗 → 运行日志：切换查询条件区到本次运行的 Base，保证看到对应日志 */
function openRunLogsFromResult(): void {
  const r = runResult.value;
  if (!r) return;
  selectedBaseId.value = r.baseId;
  if (runTarget.value) openLogs(runTarget.value);
  runResultVisible.value = false;
}

async function openLogs(plugin: PluginEntity): Promise<void> {
  logTarget.value = plugin;
  logBaseId.value = selectedBaseId.value || bases.value[0]?.id || "";
  await reloadRunLogs();
  logDialogVisible.value = true;
}

/** Base 名称（卡片安装区标题用） */
function baseNameById(id: string): string {
  return bases.value.find((b) => b.id === id)?.name ?? id;
}

function baseInstallTagType(
  plugin: PluginEntity,
): "success" | "warning" | "info" {
  if (!plugin.baseInstalled) return "info";
  return plugin.baseEnabled ? "success" : "warning";
}

function baseInstallText(plugin: PluginEntity): string {
  if (!plugin.baseInstalled) return t("plugin.baseInstall.notInstalled");
  if (plugin.baseEnabled) return t("plugin.baseInstall.enabled");
  return t("plugin.baseInstall.disabled");
}

async function handleInstallToBase(plugin: PluginEntity): Promise<void> {
  if (!selectedBaseId.value) return;
  try {
    await store.installToBase(plugin.id, selectedBaseId.value);
    ElMessage.success(t("plugin.baseInstall.installSuccess"));
  } catch (error) {
    // 后端错误信息已由请求拦截器弹出
    console.warn("[PluginManage] Base 安装失败:", error);
  }
}

async function handleSetBaseInstallEnabled(
  plugin: PluginEntity,
  enabled: boolean,
): Promise<void> {
  if (!selectedBaseId.value) return;
  try {
    await store.setBaseEnabled(plugin.id, selectedBaseId.value, enabled);
    ElMessage.success(
      enabled
        ? t("plugin.baseInstall.enableSuccess")
        : t("plugin.baseInstall.disableSuccess"),
    );
  } catch (error) {
    console.warn("[PluginManage] Base 启停失败:", error);
  }
}

async function handleRemoveFromBase(plugin: PluginEntity): Promise<void> {
  if (!selectedBaseId.value) return;
  try {
    await ElMessageBox.confirm(
      t("plugin.baseInstall.removeConfirm"),
      t("plugin.baseInstall.remove"),
      { type: "warning" },
    );
  } catch {
    return; // 用户取消
  }
  try {
    await store.removeFromBase(plugin.id, selectedBaseId.value);
    ElMessage.success(t("plugin.baseInstall.removeSuccess"));
  } catch (error) {
    console.warn("[PluginManage] Base 移除失败:", error);
  }
}

/** 日志弹窗内切换 Base 后重新拉取运行日志 */
async function reloadRunLogs(): Promise<void> {
  if (!logTarget.value || !logBaseId.value) return;
  await store.loadRunLogs(logTarget.value.id, logBaseId.value);
}

/** 日志详情弹窗 */
const logDetailVisible = ref(false);
const logDetail = ref<PluginRunLog | null>(null);

function openLogDetailById(id: string): void {
  const row = store.runLogs.find((l) => l.id === id);
  if (!row) return;
  logDetail.value = row;
  logDetailVisible.value = true;
}

function formatPermissions(plugin: PluginEntity): string[] {
  const perms = plugin.manifest?.permissions || {};
  const list: string[] = [];
  if (perms.records) {
    list.push(
      `${t("plugin.permissions.records")}: ${perms.records === "write" ? t("plugin.permissions.write") : t("plugin.permissions.read")}`,
    );
  }
  if (perms.tables) {
    list.push(
      `${t("plugin.permissions.tables")}: ${perms.tables === "write" ? t("plugin.permissions.write") : t("plugin.permissions.read")}`,
    );
  }
  if (perms.storage) list.push(t("plugin.permissions.storage"));
  if (perms.network?.length) {
    list.push(`${t("plugin.permissions.network")}: ${perms.network.join(", ")}`);
  }
  return list;
}
</script>

<template>
  <div class="plugin-manage">
    <div class="plugin-manage__header">
      <div>
        <h2 class="plugin-manage__title">{{ t("plugin.title") }}</h2>
        <p class="plugin-manage__subtitle">
          {{ t("plugin.uploadHint") }}
        </p>
      </div>
      <div class="plugin-manage__actions">
        <el-button :icon="Refresh" @click="store.loadPlugins()">
          {{ t("plugin.refresh") }}
        </el-button>
        <el-button
          type="primary"
          :icon="Plus"
          @click="uploadDialogVisible = true">
          {{ t("plugin.uploadPackage") }}
        </el-button>
      </div>
    </div>

    <div class="plugin-manage__filters">
      <el-input
        v-model="store.filterKeyword"
        class="plugin-manage__search"
        :placeholder="t('plugin.searchPlaceholder')"
        clearable />
      <el-select
        v-model="selectedBaseId"
        class="plugin-manage__base"
        :placeholder="t('plugin.detail.targetBase')">
        <el-option
          v-for="b in bases"
          :key="b.id"
          :label="b.name"
          :value="b.id" />
      </el-select>
    </div>

    <el-empty
      v-if="!store.loading && store.filteredPlugins.length === 0"
      :description="t('plugin.empty')" />

    <div v-else v-loading="store.loading" class="plugin-manage__grid">
      <el-card
        v-for="plugin in store.filteredPlugins"
        :key="plugin.id"
        shadow="hover"
        class="plugin-card">
        <div class="plugin-card__head">
          <div class="plugin-card__title">
            <span class="plugin-card__name">{{ plugin.name }}</span>
            <PluginTypeTag :type="plugin.type" />
          </div>
          <el-tag :type="statusType(plugin.status)" size="small">
            {{ t(`plugin.status.${plugin.status}`) }}
          </el-tag>
        </div>

        <div class="plugin-card__meta">
          <span>v{{ plugin.current_version }}</span>
          <span class="plugin-card__id">{{ plugin.id }}</span>
        </div>

        <p class="plugin-card__desc">
          {{ plugin.description || plugin.manifest?.description || "-" }}
        </p>

        <div class="plugin-card__perms">
          <el-tag
            v-for="p in formatPermissions(plugin)"
            :key="p"
            size="small"
            type="info"
            effect="plain">
            {{ p }}
          </el-tag>
        </div>

        <!-- Base 级安装管理（仅 UI 插件：installations 只用于 Base 分发挂载；
             脚本插件运行由 RBAC + 全局启停控制，不依赖 Base 安装，故不提供该入口） -->
        <div v-if="plugin.type === 'ui'" class="plugin-card__base">
          <div class="plugin-card__base-head">
            <span class="plugin-card__base-title">
              {{ t("plugin.baseInstall.title") }}（{{ baseNameById(selectedBaseId) }}）
            </span>
            <el-tag :type="baseInstallTagType(plugin)" size="small">
              {{ baseInstallText(plugin) }}
            </el-tag>
          </div>
          <div class="plugin-card__footer">
            <el-button
              v-if="!plugin.baseInstalled"
              size="small"
              type="primary"
              plain
              @click="handleInstallToBase(plugin)">
              {{ t("plugin.baseInstall.install") }}
            </el-button>
            <template v-else>
              <el-button
                size="small"
                @click="handleSetBaseInstallEnabled(plugin, !plugin.baseInstallEnabled)">
                {{
                  plugin.baseInstallEnabled
                    ? t("plugin.actions.disable")
                    : t("plugin.actions.enable")
                }}
              </el-button>
              <el-button
                size="small"
                type="danger"
                plain
                @click="handleRemoveFromBase(plugin)">
                {{ t("plugin.baseInstall.remove") }}
              </el-button>
            </template>
          </div>
          <p
            v-if="plugin.baseInstalled && plugin.status !== 'enabled'"
            class="plugin-manage__notice plugin-card__base-hint">
            {{ t("plugin.baseInstall.globalDisabledHint") }}
          </p>
        </div>

        <div class="plugin-card__footer">
          <el-button
            size="small"
            :type="plugin.status === 'enabled' ? 'default' : 'primary'"
            @click="handleToggleStatus(plugin)">
            {{
              plugin.status === "enabled"
                ? t("plugin.actions.disable")
                : t("plugin.actions.enable")
            }}
          </el-button>
          <el-button size="small" @click="openConfig(plugin)">
            {{ t("plugin.actions.config") }}
          </el-button>
          <el-button size="small" @click="openRollback(plugin)">
            {{ t("plugin.actions.rollback") }}
          </el-button>
          <el-button
            v-if="plugin.type === 'script'"
            size="small"
            @click="openRunDialog(plugin)">
            {{ t("plugin.actions.run") }}
          </el-button>
          <el-button
            v-if="plugin.type === 'script'"
            size="small"
            @click="openLogs(plugin)">
            {{ t("plugin.actions.runLogs") }}
          </el-button>
          <el-button
            size="small"
            type="danger"
            plain
            @click="handleUninstall(plugin)">
            {{ t("plugin.actions.uninstall") }}
          </el-button>
        </div>
      </el-card>
    </div>

    <!-- 上传安装包 -->
    <el-dialog append-to-body
      v-model="uploadDialogVisible"
      :title="t('plugin.uploadDialog.title')"
      width="520px"
      @closed="onUploadDialogClosed">
      <p class="plugin-manage__notice">
        {{ t("plugin.uploadDialog.permissionNotice") }}
      </p>
      <el-upload
        ref="uploadRef"
        drag
        :auto-upload="false"
        :limit="1"
        accept=".zip,.stplugin.zip"
        :on-change="onFileChange">
        <el-icon class="plugin-manage__upload-icon"><Upload /></el-icon>
        <div>{{ t("plugin.uploadDialog.selectFile") }}</div>
      </el-upload>
      <template #footer>
        <el-button @click="uploadDialogVisible = false">
          {{ t("common.cancel") }}
        </el-button>
        <el-button
          type="primary"
          :loading="store.uploading"
          @click="handleUpload">
          {{ t("plugin.uploadPackage") }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 回滚版本 -->
    <el-dialog append-to-body
      v-model="rollbackDialogVisible"
      :title="t('plugin.rollbackDialog.title')"
      width="480px">
      <p class="plugin-manage__notice">
        {{ t("plugin.rollbackDialog.current") }}:
        v{{ rollbackTarget?.current_version }}
      </p>
      <el-select
        v-model="rollbackVersion"
        :placeholder="t('plugin.rollbackDialog.selectVersion')"
        style="width: 100%">
        <el-option
          v-for="v in rollbackVersions"
          :key="v"
          :label="`v${v}`"
          :value="v" />
      </el-select>
      <template #footer>
        <el-button @click="rollbackDialogVisible = false">
          {{ t("common.cancel") }}
        </el-button>
        <el-button
          type="primary"
          :disabled="!rollbackVersion"
          @click="handleRollback">
          {{ t("plugin.actions.rollback") }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 配置编辑 -->
    <el-dialog append-to-body
      v-model="configDialogVisible"
      :title="t('plugin.configDialog.title')"
      width="600px">
      <el-radio-group
        v-model="configScope"
        class="plugin-manage__scope"
        @change="loadConfigForScope">
        <el-radio-button value="global">
          {{ t("plugin.configDialog.scopeGlobal") }}
        </el-radio-button>
        <el-radio-button value="base">
          {{ t("plugin.configDialog.scopeBase") }}
        </el-radio-button>
      </el-radio-group>
      <div
        v-if="configScope === 'base'"
        class="plugin-manage__base-label">
        {{ t("plugin.configDialog.baseLabel") }}：
      </div>
      <el-select
        v-if="configScope === 'base'"
        v-model="configBaseId"
        style="width: 90%; margin-top: 8px; margin-left: 12px; margin-bottom: 6px;"
        :placeholder="t('plugin.detail.selectBaseFirst')"
        @change="loadConfigForScope">
        <el-option
          v-for="b in bases"
          :key="b.id"
          :label="b.name"
          :value="b.id" />
      </el-select>
      <el-input
        v-model="configText"
        type="textarea"
        :rows="12"
        :placeholder="t('plugin.configDialog.jsonHint')" />
      <template #footer>
        <el-button @click="configDialogVisible = false">
          {{ t("common.cancel") }}
        </el-button>
        <el-button type="primary" @click="handleSaveConfig">
          {{ t("common.save") }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 运行脚本插件 -->
    <el-dialog append-to-body
      v-model="runDialogVisible"
      :title="t('plugin.runDialog.title')"
      width="480px">
      <p class="plugin-manage__notice">
        {{ t("plugin.runDialog.notice") }}
      </p>
      <div class="plugin-manage__base-label">
        {{ t("plugin.configDialog.baseLabel") }}
      </div>
      <el-select
        v-model="runBaseId"
        style="width: 100%"
        :placeholder="t('plugin.detail.selectBaseFirst')">
        <el-option
          v-for="b in bases"
          :key="b.id"
          :label="b.name"
          :value="b.id" />
      </el-select>
      <template #footer>
        <el-button @click="runDialogVisible = false">
          {{ t("common.cancel") }}
        </el-button>
        <el-button
          type="primary"
          :loading="store.running"
          @click="handleRunConfirm">
          {{ t("plugin.actions.run") }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 运行结果 -->
    <el-dialog append-to-body
      v-model="runResultVisible"
      :title="t('plugin.runResultDialog.title')"
      width="600px">
      <template v-if="runResult">
        <h4 class="plugin-manage__section-title">
          {{ t("plugin.runResultDialog.execInfo") }}
        </h4>
        <div class="plugin-manage__result-row">
          <span>{{ t("plugin.runResultDialog.status") }}：</span>
          <el-tag :type="runStatusType(runResult.status)" size="small">
            {{ runStatusText(runResult.status) }}
          </el-tag>
        </div>
        <div class="plugin-manage__result-row">
          <span>
            {{ t("plugin.runLogDialog.duration") }}：{{ formatDuration(runResult.durationMs) }}
          </span>
        </div>
        <div class="plugin-manage__result-row">
          <span>{{ t("plugin.configDialog.baseLabel") }}：{{ runResult.baseName }}</span>
        </div>
        <p class="plugin-manage__notice">
          {{ t("plugin.runResultDialog.viewResultHint") }}
        </p>

        <h4 class="plugin-manage__section-title">
          {{ t("plugin.runResultDialog.resultInfo") }}
        </h4>
        <div class="plugin-manage__result-row">
          <span>{{ t("plugin.runResultDialog.overall") }}：</span>
          <el-tag :type="runStatusType(runResult.status)" size="small">
            {{ runStatusText(runResult.status) }}
          </el-tag>
        </div>
        <el-input
          :model-value="runResultText"
          type="textarea"
          :rows="10"
          readonly />
      </template>
      <template #footer>
        <el-button @click="runResultVisible = false">
          {{ t("common.cancel") }}
        </el-button>
        <el-button type="primary" @click="openRunLogsFromResult">
          {{ t("plugin.actions.runLogs") }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 运行日志 -->
    <el-dialog append-to-body
      v-model="logDialogVisible"
      :title="t('plugin.runLogDialog.title')"
      width="720px">
      <div class="plugin-manage__base-label">
        {{ t("plugin.configDialog.baseLabel") }}
      </div>
      <el-select
        v-model="logBaseId"
        style="width: 100%; margin-bottom: 12px"
        :placeholder="t('plugin.detail.selectBaseFirst')"
        @change="reloadRunLogs">
        <el-option
          v-for="b in bases"
          :key="b.id"
          :label="b.name"
          :value="b.id" />
      </el-select>
      <el-empty
        v-if="store.runLogs.length === 0"
        :description="t('plugin.runLogDialog.empty')" />
      <el-table v-else :data="store.runLogs" size="small" max-height="420">
        <el-table-column
          :label="t('plugin.runLogDialog.status')"
          width="90">
          <template #default="{ row }">
            <el-tag :type="runStatusType(row.status)" size="small">
              {{ runStatusText(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column
          :label="t('plugin.runLogDialog.duration')"
          width="90">
          <template #default="{ row }">
            {{ formatDuration(row.duration_ms ?? undefined) }}
          </template>
        </el-table-column>
        <el-table-column
          prop="created_at"
          :label="t('plugin.runLogDialog.time')"
          min-width="150"
          show-overflow-tooltip />
        <el-table-column
          :label="t('plugin.runLogDialog.result')"
          min-width="180"
          show-overflow-tooltip>
          <template #default="{ row }">
            {{ resultSummary(row.result) }}
          </template>
        </el-table-column>
        <el-table-column
          prop="error_summary"
          :label="t('plugin.runLogDialog.error')"
          min-width="150"
          show-overflow-tooltip />
        <el-table-column width="70" fixed="right">
          <template #default="{ row }">
            <el-button
              link
              type="primary"
              size="small"
              @click="openLogDetailById(row.id)">
              {{ t("plugin.runLogDialog.detail") }}
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>

    <!-- 日志详情 -->
    <el-dialog append-to-body
      v-model="logDetailVisible"
      :title="t('plugin.runLogDialog.detailTitle')"
      width="640px">
      <template v-if="logDetail">
        <h4 class="plugin-manage__section-title">
          {{ t("plugin.runResultDialog.execInfo") }}
        </h4>
        <div class="plugin-manage__result-row">
          <span>{{ t("plugin.runResultDialog.status") }}：</span>
          <el-tag :type="runStatusType(logDetail.status)" size="small">
            {{ runStatusText(logDetail.status) }}
          </el-tag>
        </div>
        <div class="plugin-manage__result-row">
          <span>
            {{ t("plugin.runLogDialog.duration") }}：{{ formatDuration(logDetail.duration_ms ?? undefined) }}
          </span>
        </div>
        <div class="plugin-manage__result-row">
          <span>{{ t("plugin.runLogDialog.time") }}：{{ logDetail.created_at || "-" }}</span>
        </div>
        <div class="plugin-manage__result-row">
          <span>{{ t("plugin.runLogDialog.triggeredBy") }}：{{ logDetail.triggered_by || "-" }}</span>
        </div>

        <h4 class="plugin-manage__section-title">
          {{ t("plugin.runResultDialog.resultInfo") }}
        </h4>
        <div class="plugin-manage__result-row">
          <span>{{ t("plugin.runResultDialog.overall") }}：</span>
          <el-tag :type="runStatusType(logDetail.status)" size="small">
            {{ runStatusText(logDetail.status) }}
          </el-tag>
        </div>
        <el-input
          :model-value="formatResultText(logDetail.result)"
          type="textarea"
          :rows="6"
          readonly />

        <h4 class="plugin-manage__section-title">
          {{ t("plugin.runLogDialog.output") }}
        </h4>
        <el-input
          :model-value="logDetail.output || '-'"
          type="textarea"
          :rows="5"
          readonly />

        <template v-if="logDetail.error_summary">
          <h4 class="plugin-manage__section-title">
            {{ t("plugin.runLogDialog.error") }}
          </h4>
          <el-input
            :model-value="logDetail.error_summary"
            type="textarea"
            :rows="2"
            readonly />
        </template>
        <template v-if="logDetail.traceback_text">
          <h4 class="plugin-manage__section-title">
            {{ t("plugin.runLogDialog.traceback") }}
          </h4>
          <el-input
            :model-value="logDetail.traceback_text"
            type="textarea"
            :rows="6"
            readonly />
        </template>
      </template>
      <template #footer>
        <el-button @click="logDetailVisible = false">
          {{ t("common.cancel") }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.plugin-manage {
  padding: 24px;
  background: #f5f7fa;
  min-height: 100%;
}

.plugin-manage__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 16px;
}

.plugin-manage__title {
  font-size: 20px;
  font-weight: 600;
  color: #303133;
  margin: 0 0 4px;
}

.plugin-manage__subtitle {
  font-size: 14px;
  color: #909399;
  margin: 0;
}

.plugin-manage__actions {
  display: flex;
  gap: 8px;
}

.plugin-manage__filters {
  display: flex;
  gap: 12px;
  margin-bottom: 16px;
  flex-wrap: wrap;
}

.plugin-manage__search {
  max-width: 360px;
}

.plugin-manage__base {
  width: 260px;
}

.plugin-manage__grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
  gap: 16px;
}

.plugin-card__head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  margin-bottom: 8px;
}

.plugin-card__title {
  display: flex;
  align-items: center;
  gap: 8px;
}

.plugin-card__name {
  font-size: 16px;
  font-weight: 500;
  color: #303133;
}

.plugin-card__meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: #909399;
  margin-bottom: 8px;
}

.plugin-card__id {
  font-family: Consolas, Monaco, monospace;
}

.plugin-card__desc {
  font-size: 14px;
  color: #606266;
  margin: 0 0 12px;
  min-height: 22px;
}

.plugin-card__perms {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 12px;
}

.plugin-card__footer {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.plugin-manage__notice {
  font-size: 13px;
  color: #909399;
  margin: 0 0 12px;
}

.plugin-manage__upload-icon {
  font-size: 32px;
  color: #409eff;
}

.plugin-manage__scope {
  margin-bottom: 12px;
}

.plugin-manage__base-label {
  font-size: 13px;
  font-weight: 600;
  color: #606266;
  margin: 0 0 4px;
}

.plugin-manage__section-title {
  margin: 4px 0 8px;
  font-size: 14px;
  font-weight: 600;
  color: #303133;
}

.plugin-manage__result-row {
  display: flex;
  align-items: center;
  gap: 6px;
  margin: 0 0 8px;
  font-size: 13px;
  color: #606266;
}

.plugin-card__base {
  margin: 10px 0 0;
  padding: 8px 10px;
  background: #f5f7fa;
  border-radius: 4px;
}

.plugin-card__base-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.plugin-card__base-title {
  font-size: 12px;
  font-weight: 600;
  color: #606266;
}

.plugin-card__base-hint {
  margin: 6px 0 0;
}
</style>
