<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { useI18n } from "vue-i18n";
import { ElMessage, ElMessageBox, ElIcon } from "element-plus";
import { Share, Plus, CopyDocument } from "@element-plus/icons-vue";
import { dashboardShareService } from "@/db/services/dashboardShareService";
import type { DashboardShare } from "@/db/schema";
import { formatDateTime } from "@/utils/timezone";

const { t } = useI18n();

const props = defineProps<{
  visible: boolean;
  dashboardId: string;
  dashboardName: string;
}>();

const emit = defineEmits<{
  (e: "update:visible", value: boolean): void;
  (e: "created", share: DashboardShare): void;
}>();

// 对话框可见性
const dialogVisible = computed({
  get: () => props.visible,
  set: (val) => emit("update:visible", val),
});

// 当前步骤: 0=已分享列表, 1=配置, 2=获取链接
const currentStep = ref(0);

// 分享配置表单
const shareForm = ref({
  title: "",
  description: "",
  expiresInHours: 168,
  maxAccessCount: undefined as number | undefined,
  requireAccessCode: false,
  permission: "view" as "view" | "edit",
});

// 已创建的分享
const createdShare = ref<DashboardShare | null>(null);
const shareUrl = ref("");

// 加载状态
const isCreating = ref(false);
const isLoadingList = ref(false);

// 现有分享列表
const existingShares = ref<DashboardShare[]>([]);

// 计算属性：有效分享数量
const activeSharesCount = computed(() => {
  return existingShares.value.filter(
    (s) => s.isActive && !isShareExpired(s) && !isShareReachedLimit(s),
  ).length;
});

// 监听对话框打开
watch(
  () => props.visible,
  (val) => {
    if (val) {
      currentStep.value = 0;
      resetForm();
      loadExistingShares();
    }
  },
);

// 重置表单
function resetForm() {
  shareForm.value = {
    title: props.dashboardName || "",
    description: "",
    expiresInHours: 168,
    maxAccessCount: undefined,
    requireAccessCode: false,
    permission: "view",
  };
  createdShare.value = null;
  shareUrl.value = "";
}

// 加载现有分享列表
async function loadExistingShares() {
  if (!props.dashboardId) return;

  isLoadingList.value = true;
  try {
    existingShares.value =
      await dashboardShareService.getSharesByDashboard(props.dashboardId);
  } catch (error) {
    console.error("加载分享列表失败:", error);
  } finally {
    isLoadingList.value = false;
  }
}

// 创建分享链接
async function createShare() {
  if (!props.dashboardId) {
    ElMessage.error(t("dashboard.shareDialog.errorNoDashboardId"));
    return;
  }

  isCreating.value = true;
  try {
    const share = await dashboardShareService.createShare({
      dashboardId: props.dashboardId,
      title: shareForm.value.title || undefined,
      description: shareForm.value.description || undefined,
      expiresInHours: shareForm.value.expiresInHours || undefined,
      maxAccessCount: shareForm.value.maxAccessCount || undefined,
      requireAccessCode: shareForm.value.requireAccessCode,
      permission: shareForm.value.permission,
    });

    createdShare.value = share;
    shareUrl.value =
      dashboardShareService.generateShareUrl(share.shareToken);

    ElMessage.success(t("dashboard.shareDialog.createdTitle"));
    emit("created", share);

    // 进入获取链接步骤
    currentStep.value = 2;
  } catch (error: any) {
    console.error("创建分享链接失败:", error);
    ElMessage.error(
      error.response?.data?.message || t("dashboard.shareDialog.errorCreateFailed"),
    );
  } finally {
    isCreating.value = false;
  }
}

// 复制分享链接
function copyShareUrl() {
  if (!shareUrl.value) return;

  dashboardShareService.copyToClipboard(shareUrl.value).then((success) => {
    if (success) {
      ElMessage.success(t("dashboard.shareDialog.copied"));
    } else {
      ElMessage.error(t("dashboard.shareDialog.copyFailed"));
    }
  });
}

// 复制访问密码
function copyAccessCode() {
  if (!createdShare.value?.accessCode) return;

  dashboardShareService
    .copyToClipboard(createdShare.value.accessCode)
    .then((success) => {
      if (success) {
        ElMessage.success(t("dashboard.shareDialog.codeCopied"));
      } else {
        ElMessage.error(t("dashboard.shareDialog.copyFailed"));
      }
    });
}

// 复制现有分享链接
function copyExistingShareUrl(share: DashboardShare) {
  const url = dashboardShareService.generateShareUrl(share.shareToken);
  dashboardShareService.copyToClipboard(url).then((success) => {
    if (success) {
      ElMessage.success(t("dashboard.shareDialog.copied"));
    } else {
      ElMessage.error(t("dashboard.shareDialog.copyFailed"));
    }
  });
}

// 复制链接和密码
function copyLinkAndCode() {
  if (!shareUrl.value) return;

  let text = shareUrl.value;
  if (createdShare.value?.accessCode) {
    text += `\n${t("dashboard.shareDialog.accessCodeLabel")}${createdShare.value.accessCode}`;
  }

  dashboardShareService.copyToClipboard(text).then((success) => {
    if (success) {
      ElMessage.success(t("dashboard.shareDialog.copiedAll"));
    } else {
      ElMessage.error(t("dashboard.shareDialog.copyFailed"));
    }
  });
}

// 切换分享状态
async function toggleShareStatus(share: DashboardShare) {
  try {
    if (share.isActive) {
      await ElMessageBox.confirm(
        t("dashboard.shareDialog.disableConfirmMsg"),
        t("dashboard.shareDialog.disableConfirmTitle"),
        { type: "warning" },
      );
      await dashboardShareService.deactivateShare(share.id);
      ElMessage.success(t("dashboard.shareDialog.disabled"));
    } else {
      // 重新启用需要重新创建
      ElMessage.info(t("dashboard.shareDialog.cannotReenable"));
      return;
    }
    loadExistingShares();
  } catch (error: any) {
    if (error !== "cancel") {
      console.error("更新状态失败:", error);
      ElMessage.error(t("dashboard.shareDialog.opFailed"));
    }
  }
}

// 删除分享
async function deleteShare(shareId: string) {
  try {
    await ElMessageBox.confirm(
      t("dashboard.shareDialog.deleteConfirmMsg"),
      t("dashboard.shareDialog.deleteConfirmTitle"),
      {
        confirmButtonText: t("dashboard.shareDialog.delete"),
        cancelButtonText: t("dashboard.shareDialog.close"),
        type: "warning",
      },
    );

    await dashboardShareService.deleteShare(shareId);
    ElMessage.success(t("dashboard.shareDialog.deleted"));
    loadExistingShares();
  } catch (error: any) {
    if (error !== "cancel") {
      console.error("删除失败:", error);
      ElMessage.error(t("dashboard.shareDialog.deleteFailed"));
    }
  }
}

// 判断分享是否过期
function isShareExpired(share: DashboardShare): boolean {
  if (!share.expiresAt) return false;
  return Date.now() > share.expiresAt;
}

// 判断是否达到访问上限
function isShareReachedLimit(share: DashboardShare): boolean {
  if (!share.maxAccessCount) return false;
  return share.currentAccessCount >= share.maxAccessCount;
}

// 获取状态文本
function getStatusText(share: DashboardShare): string {
  if (!share.isActive) return t("dashboard.shareDialog.statusDisabled");
  if (isShareExpired(share)) return t("dashboard.shareDialog.statusExpired");
  if (isShareReachedLimit(share)) return t("dashboard.shareDialog.statusLimited");
  return t("dashboard.shareDialog.statusActive");
}

// 获取状态类型
function getStatusType(
  share: DashboardShare,
): "primary" | "success" | "warning" | "info" | "danger" {
  if (!share.isActive) return "info";
  if (isShareExpired(share)) return "danger";
  if (isShareReachedLimit(share)) return "warning";
  return "success";
}

// 格式化过期时间
function formatExpireTime(timestamp: number): string {
  return formatDateTime(timestamp);
}

// 格式化有效期显示
function formatExpiresLabel(expiresAt?: number): string {
  if (!expiresAt) return t("dashboard.shareDialog.foreverValid");
  return t("dashboard.shareDialog.validUntil", { time: formatDateTime(expiresAt) });
}

// 关闭对话框
function closeDialog() {
  dialogVisible.value = false;
}

// 跳转到创建分享步骤
function goToCreateShare() {
  currentStep.value = 1;
  resetForm();
}


</script>

<template>
  <el-dialog
    v-model="dialogVisible"
    :title="t('dashboard.shareDialog.title')"
    width="700px"
    :close-on-click-modal="false"
    destroy-on-close>
    <el-steps :active="currentStep" finish-status="success" class="share-steps">
      <el-step :title="t('dashboard.shareDialog.stepShared')" />
      <el-step :title="t('dashboard.shareDialog.stepConfig')" />
      <el-step :title="t('dashboard.shareDialog.stepGetLink')" />
    </el-steps>

    <!-- 步骤0：已分享链接列表 -->
    <div v-if="currentStep === 0" class="step-content">
      <div class="shares-header">
        <h3 class="shares-title">{{ t('dashboard.shareDialog.allSharesTitle') }}</h3>
        <p class="shares-description">
          {{ t('dashboard.shareDialog.allSharesDesc') }}
        </p>
      </div>

      <div v-if="isLoadingList" class="text-center py-4">
        <el-skeleton :rows="4" animated />
      </div>

      <el-empty
        v-else-if="existingShares.length === 0"
        :description="t('dashboard.shareDialog.noShares')"
        :image-size="80">
        <template #image>
          <el-icon :size="60" color="#c0c4cc"><Share /></el-icon>
        </template>
        <template #description>
          <p style="color: #909399; margin-top: 8px">{{ t('dashboard.shareDialog.noSharesHint') }}</p>
          <p style="color: #b0b3b8; font-size: 13px">
            {{ t('dashboard.shareDialog.noSharesCta') }}
          </p>
        </template>
      </el-empty>

      <div v-else class="shares-list">
        <el-table :data="existingShares" size="default" class="share-table" stripe>
          <el-table-column :label="t('dashboard.shareDialog.colTitle')" min-width="140" show-overflow-tooltip>
            <template #default="{ row }">
              <span class="share-title">{{ row.title || t('dashboard.shareDialog.unnamedShare') }}</span>
              <p v-if="row.description" class="share-desc">{{ row.description }}</p>
            </template>
          </el-table-column>
          <el-table-column :label="t('dashboard.shareDialog.colStatus')" width="90">
            <template #default="{ row }">
              <el-tag :type="getStatusType(row as DashboardShare)" size="small" effect="light">
                {{ getStatusText(row as DashboardShare) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column :label="t('dashboard.shareDialog.colAccessCount')" width="110">
            <template #default="{ row }">
              <span class="access-count">{{ row.currentAccessCount }}</span>
              <span v-if="row.maxAccessCount" class="access-limit">
                / {{ row.maxAccessCount }}
              </span>
              <span v-else class="access-unlimited">/ {{ t('dashboard.shareDialog.unlimited') }}</span>
            </template>
          </el-table-column>
          <el-table-column :label="t('dashboard.shareDialog.colExpiry')" min-width="130">
            <template #default="{ row }">
              <span v-if="row.expiresAt">{{
                formatExpireTime(row.expiresAt)
              }}</span>
              <span v-else>{{ t('dashboard.shareDialog.forever') }}</span>
            </template>
          </el-table-column>
          <el-table-column :label="t('dashboard.shareDialog.colPermission')" width="80">
            <template #default="{ row }">
              <el-tag
                :type="row.permission === 'view' ? 'info' : 'warning'"
                size="small"
                effect="plain">
                {{ row.permission === "view" ? t('dashboard.shareDialog.permissionView') : t('dashboard.shareDialog.permissionEdit') }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column :label="t('dashboard.shareDialog.colPassword')" width="65">
            <template #default="{ row }">
              <el-tag
                v-if="row.accessCode"
                size="small"
                type="warning"
                effect="light">{{ t('dashboard.shareDialog.yes') }}</el-tag>
              <el-tag v-else size="small" type="info" effect="light">{{ t('dashboard.shareDialog.no') }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column :label="t('dashboard.shareDialog.colActions')" width="180" fixed="right">
            <template #default="{ row }">
              <el-button
                v-if="row.isActive && !isShareExpired(row as DashboardShare)"
                link
                type="primary"
                size="small"
                @click="copyExistingShareUrl(row as DashboardShare)">
                {{ t('dashboard.shareDialog.copyLink') }}
              </el-button>
              <el-button
                v-if="row.isActive"
                link
                type="warning"
                size="small"
                @click="toggleShareStatus(row as DashboardShare)">
                {{ t('dashboard.shareDialog.disable') }}
              </el-button>
              <el-button
                link
                type="danger"
                size="small"
                @click="deleteShare(row.id)">
                {{ t('dashboard.shareDialog.delete') }}
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="shares-summary">
          {{ t('dashboard.shareDialog.summary', { total: existingShares.length, active: activeSharesCount }) }}
        </div>
      </div>

      <div class="new-share-action">
        <el-button type="primary" size="large" @click="goToCreateShare">
          <el-icon><Plus /></el-icon>
          {{ t('dashboard.shareDialog.newShare') }}
        </el-button>
      </div>
    </div>

    <!-- 步骤1：配置分享 -->
    <div v-if="currentStep === 1" class="step-content">
      <el-form label-position="top">
        <!-- 基本信息 -->
        <el-divider content-position="left">{{ t('dashboard.shareDialog.basicInfo') }}</el-divider>

        <el-form-item :label="t('dashboard.shareDialog.labelTitle')">
          <el-input
            v-model="shareForm.title"
            :placeholder="t('dashboard.shareDialog.titlePlaceholder')"
            maxlength="200"
            show-word-limit />
        </el-form-item>

        <el-form-item :label="t('dashboard.shareDialog.labelNote')">
          <el-input
            v-model="shareForm.description"
            type="textarea"
            :rows="3"
            :placeholder="t('dashboard.shareDialog.notePlaceholder')" />
        </el-form-item>

        <!-- 分享设置 -->
        <el-divider content-position="left">{{ t('dashboard.shareDialog.shareSettings') }}</el-divider>

        <el-form-item :label="t('dashboard.shareDialog.labelExpiry')">
          <el-select v-model="shareForm.expiresInHours" style="width: 100%">
            <el-option :value="1" :label="t('dashboard.shareDialog.opt1Hour')" />
            <el-option :value="24" :label="t('dashboard.shareDialog.opt1Day')" />
            <el-option :value="168" :label="t('dashboard.shareDialog.opt7Days')" />
            <el-option :value="720" :label="t('dashboard.shareDialog.opt30Days')" />
            <el-option :value="0" :label="t('dashboard.shareDialog.optForever')" />
          </el-select>
        </el-form-item>

        <el-form-item :label="t('dashboard.shareDialog.labelAccessLimit')">
          <el-input-number
            v-model="shareForm.maxAccessCount"
            :min="0"
            :max="10000"
            :controls="true"
            style="width: 100%"
            :placeholder="t('dashboard.shareDialog.accessLimitPlaceholder')" />
        </el-form-item>

        <el-form-item :label="t('dashboard.shareDialog.labelAccessCode')">
          <el-switch
            v-model="shareForm.requireAccessCode"
            :active-text="t('dashboard.shareDialog.requireCode')"
            :inactive-text="t('dashboard.shareDialog.noCode')" />
        </el-form-item>

        <el-form-item :label="t('dashboard.shareDialog.labelPermission')">
          <el-radio-group v-model="shareForm.permission">
            <el-radio value="view">{{ t('dashboard.shareDialog.radioView') }}</el-radio>
            <el-radio value="edit">{{ t('dashboard.shareDialog.radioEdit') }}</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
    </div>

    <!-- 步骤2：获取链接 -->
    <div v-if="currentStep === 2" class="step-content">
      <el-result
        icon="success"
        :title="t('dashboard.shareDialog.createdTitle')"
        :sub-title="t('dashboard.shareDialog.createdSubtitle')">
        <template #extra>
          <div class="share-url-container">
            <el-input
              v-model="shareUrl"
              readonly
              class="share-url-input"
              size="large">
              <template #append>
                <el-button type="primary" @click="copyShareUrl">
                  <el-icon><CopyDocument /></el-icon>
                  {{ t('dashboard.shareDialog.copyLink') }}
                </el-button>
              </template>
            </el-input>
          </div>

          <!-- 访问密码 -->
          <div
            v-if="createdShare?.accessCode"
            class="share-access-code-block">
            <div class="access-code-row">
              <span class="label">{{ t('dashboard.shareDialog.accessCodeLabel') }}</span>
              <span class="code">{{ createdShare.accessCode }}</span>
              <el-button
                link
                type="primary"
                size="small"
                @click="copyAccessCode">
                <el-icon><CopyDocument /></el-icon>
                {{ t('dashboard.shareDialog.copyCode') }}
              </el-button>
            </div>
            <el-button
              type="primary"
              plain
              size="small"
              class="copy-all-btn"
              @click="copyLinkAndCode">
              {{ t('dashboard.shareDialog.copyAll') }}
            </el-button>
          </div>

          <!-- 分享详情 -->
          <div class="share-info mt-4">
            <el-descriptions :column="2" border size="small">
              <el-descriptions-item :label="t('dashboard.shareDialog.labelTitle')">
                {{ createdShare?.title || t('dashboard.shareDialog.unnamedShare') }}
              </el-descriptions-item>
              <el-descriptions-item :label="t('dashboard.shareDialog.labelPermission')">
                {{ createdShare?.permission === "view" ? t('dashboard.shareDialog.radioView') : t('dashboard.shareDialog.radioEdit') }}
              </el-descriptions-item>
              <el-descriptions-item :label="t('dashboard.shareDialog.labelExpiry')">
                {{ formatExpiresLabel(createdShare?.expiresAt) }}
              </el-descriptions-item>
              <el-descriptions-item :label="t('dashboard.shareDialog.labelAccessLimit2')">
                {{ createdShare?.maxAccessCount
                  ? t('dashboard.shareDialog.maxTimes', { count: createdShare.maxAccessCount })
                  : t('dashboard.shareDialog.unlimited') }}
              </el-descriptions-item>
              <el-descriptions-item
                v-if="createdShare?.description"
                :label="t('dashboard.shareDialog.labelNote')"
                :span="2">
                {{ createdShare.description }}
              </el-descriptions-item>
            </el-descriptions>
          </div>

          <div class="mt-4 share-actions">
            <el-button @click="currentStep = 1">{{ t('dashboard.shareDialog.backEdit') }}</el-button>
            <el-button type="primary" @click="closeDialog">{{ t('dashboard.shareDialog.doneShare') }}</el-button>
            <el-button type="success" plain @click="goToCreateShare">
              {{ t('dashboard.shareDialog.createAnother') }}
            </el-button>
          </div>
        </template>
      </el-result>
    </div>

    <template #footer>
      <span v-if="currentStep === 1" class="dialog-footer">
        <el-button @click="currentStep = 0">{{ t('dashboard.shareDialog.back') }}</el-button>
        <el-button
          type="primary"
          :loading="isCreating"
          @click="createShare">
          {{ t('dashboard.shareDialog.createShare') }}
        </el-button>
      </span>
      <span v-else-if="currentStep === 0" class="dialog-footer">
        <el-button @click="closeDialog">{{ t('dashboard.shareDialog.close') }}</el-button>
      </span>
    </template>
  </el-dialog>
</template>

<style lang="scss" scoped>

@use "@/assets/styles/variables" as *;

.share-steps {
  margin-bottom: 24px;
}

.step-content {
  min-height: 400px;
  max-height: 60vh;
  overflow-y: auto;
  padding-right: 8px;
}

// 步骤0：已分享链接列表
.shares-header {
  margin-bottom: 24px;

  .shares-title {
    font-size: 18px;
    font-weight: 600;
    color: $text-primary;
    margin: 0 0 8px 0;
  }

  .shares-description {
    font-size: 14px;
    color: $text-secondary;
    margin: 0;
  }
}

.shares-list {
  .share-table {
    margin-top: 16px;

    :deep(.el-table__header th) {
      background-color: #fafafa;
      font-weight: 600;
      color: $text-primary;
    }
  }

  .share-title {
    font-weight: 500;
    color: $text-primary;
  }

  .share-desc {
    font-size: 12px;
    color: $text-secondary;
    margin: 4px 0 0 0;
    line-height: 1.4;
  }

  .access-count {
    font-weight: 600;
    color: $primary-color;
  }

  .access-limit {
    color: $text-secondary;
    font-size: 13px;
  }

  .access-unlimited {
    color: #b0b3b8;
    font-size: 13px;
  }

  .shares-summary {
    margin-top: 16px;
    padding: 12px 16px;
    background-color: #f5f7fa;
    border-radius: $border-radius-base;
    font-size: 13px;
    color: $text-secondary;

    strong {
      color: $primary-color;
      font-weight: 600;
    }
  }
}

.new-share-action {
  margin-top: 32px;
  text-align: center;
  padding: 24px;
  border-top: 1px dashed $border-color;

  .el-button {
    padding: 12px 32px;
    font-size: 15px;
  }
}

// 步骤2：获取链接
.share-url-container {
  max-width: 500px;
  margin: 0 auto;
}

.share-url-input {
  :deep(.el-input__wrapper) {
    background-color: $bg-color;
  }
}

.share-access-code-block {
  max-width: 500px;
  margin: 16px auto 0;
  padding: 12px 16px;
  background: #f5f7fa;
  border-radius: 10px;
  border: 1px solid #e4e7ed;

  .access-code-row {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 8px;

    .label {
      color: #909399;
      font-size: 13px;
    }

    .code {
      font-family: monospace;
      font-size: 18px;
      font-weight: 700;
      color: $primary-color;
      letter-spacing: 3px;
      flex: 1;
    }
  }

  .copy-all-btn {
    width: 100%;
  }
}

.share-info {
  max-width: 500px;
  margin: 0 auto;
  text-align: left;
}

.share-actions {
  max-width: 500px;
  margin: 0 auto;
  display: flex;
  justify-content: center;
  gap: 12px;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.mt-4 {
  margin-top: 24px;
}

.py-4 {
  padding-top: 16px;
  padding-bottom: 16px;
}

.text-center {
  text-align: center;
}

// 移动端适配
@media (max-width: 768px) {
  :deep(.el-dialog) {
    width: 95% !important;
  }

  .share-actions {
    flex-wrap: wrap;
  }
}
</style>
