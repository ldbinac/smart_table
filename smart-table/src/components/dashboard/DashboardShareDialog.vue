<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { ElMessage, ElMessageBox, ElIcon } from "element-plus";
import { Share, Plus, CopyDocument, Link, Lock } from "@element-plus/icons-vue";
import { dashboardShareService } from "@/db/services/dashboardShareService";
import type { DashboardShare } from "@/db/schema";
import { formatDateTime, formatDate } from "@/utils/timezone";

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
    ElMessage.error("仪表盘ID不能为空");
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

    ElMessage.success("分享链接创建成功");
    emit("created", share);

    // 进入获取链接步骤
    currentStep.value = 2;
  } catch (error: any) {
    console.error("创建分享链接失败:", error);
    ElMessage.error(
      error.response?.data?.message || "创建失败，请稍后重试",
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
      ElMessage.success("链接已复制到剪贴板");
    } else {
      ElMessage.error("复制失败，请手动复制");
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
        ElMessage.success("访问密码已复制到剪贴板");
      } else {
        ElMessage.error("复制失败，请手动复制");
      }
    });
}

// 复制现有分享链接
function copyExistingShareUrl(share: DashboardShare) {
  const url = dashboardShareService.generateShareUrl(share.shareToken);
  dashboardShareService.copyToClipboard(url).then((success) => {
    if (success) {
      ElMessage.success("链接已复制到剪贴板");
    } else {
      ElMessage.error("复制失败，请手动复制");
    }
  });
}

// 复制链接和密码
function copyLinkAndCode() {
  if (!shareUrl.value) return;

  let text = shareUrl.value;
  if (createdShare.value?.accessCode) {
    text += `\n访问密码：${createdShare.value.accessCode}`;
  }

  dashboardShareService.copyToClipboard(text).then((success) => {
    if (success) {
      ElMessage.success("链接和密码已复制到剪贴板");
    } else {
      ElMessage.error("复制失败，请手动复制");
    }
  });
}

// 切换分享状态
async function toggleShareStatus(share: DashboardShare) {
  try {
    if (share.isActive) {
      await ElMessageBox.confirm(
        "禁用后该分享链接将无法访问，是否继续？",
        "确认禁用",
        { type: "warning" },
      );
      await dashboardShareService.deactivateShare(share.id);
      ElMessage.success("分享链接已禁用");
    } else {
      // 重新启用需要重新创建
      ElMessage.info("已停用的分享无法重新启用，请新建分享链接");
      return;
    }
    loadExistingShares();
  } catch (error: any) {
    if (error !== "cancel") {
      console.error("更新状态失败:", error);
      ElMessage.error("操作失败，请稍后重试");
    }
  }
}

// 删除分享
async function deleteShare(shareId: string) {
  try {
    await ElMessageBox.confirm(
      "删除后该分享链接将永久失效，是否继续？",
      "确认删除",
      {
        confirmButtonText: "删除",
        cancelButtonText: "取消",
        type: "warning",
      },
    );

    await dashboardShareService.deleteShare(shareId);
    ElMessage.success("删除成功");
    loadExistingShares();
  } catch (error: any) {
    if (error !== "cancel") {
      console.error("删除失败:", error);
      ElMessage.error("删除失败，请稍后重试");
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
  if (!share.isActive) return "已停用";
  if (isShareExpired(share)) return "已过期";
  if (isShareReachedLimit(share)) return "已达上限";
  return "有效";
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
  if (!expiresAt) return "永久有效";
  return `有效期至 ${formatDateTime(expiresAt)}`;
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

// 跳转到分享列表步骤
function goToSharesList() {
  currentStep.value = 0;
  loadExistingShares();
}
</script>

<template>
  <el-dialog
    v-model="dialogVisible"
    title="分享仪表盘"
    width="700px"
    :close-on-click-modal="false"
    destroy-on-close>
    <el-steps :active="currentStep" finish-status="success" class="share-steps">
      <el-step title="已分享链接" />
      <el-step title="配置分享" />
      <el-step title="获取链接" />
    </el-steps>

    <!-- 步骤0：已分享链接列表 -->
    <div v-if="currentStep === 0" class="step-content">
      <div class="shares-header">
        <h3 class="shares-title">当前仪表盘的所有分享记录</h3>
        <p class="shares-description">
          您可以查看、管理已有的分享，或创建新的分享链接
        </p>
      </div>

      <div v-if="isLoadingList" class="text-center py-4">
        <el-skeleton :rows="4" animated />
      </div>

      <el-empty
        v-else-if="existingShares.length === 0"
        description="暂无分享记录"
        :image-size="80">
        <template #image>
          <el-icon :size="60" color="#c0c4cc"><Share /></el-icon>
        </template>
        <template #description>
          <p style="color: #909399; margin-top: 8px">还没有创建任何分享</p>
          <p style="color: #b0b3b8; font-size: 13px">
            点击下方按钮创建第一个分享链接
          </p>
        </template>
      </el-empty>

      <div v-else class="shares-list">
        <el-table :data="existingShares" size="default" class="share-table" stripe>
          <el-table-column label="标题" min-width="140" show-overflow-tooltip>
            <template #default="{ row }">
              <span class="share-title">{{ row.title || "未命名分享" }}</span>
              <p v-if="row.description" class="share-desc">{{ row.description }}</p>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="90">
            <template #default="{ row }">
              <el-tag :type="getStatusType(row)" size="small" effect="light">
                {{ getStatusText(row) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="访问次数" width="110">
            <template #default="{ row }">
              <span class="access-count">{{ row.currentAccessCount }}</span>
              <span v-if="row.maxAccessCount" class="access-limit">
                / {{ row.maxAccessCount }}
              </span>
              <span v-else class="access-unlimited">/ 无限制</span>
            </template>
          </el-table-column>
          <el-table-column label="有效期" min-width="130">
            <template #default="{ row }">
              <span v-if="row.expiresAt">{{
                formatExpireTime(row.expiresAt)
              }}</span>
              <span v-else>永久</span>
            </template>
          </el-table-column>
          <el-table-column label="权限" width="80">
            <template #default="{ row }">
              <el-tag
                :type="row.permission === 'view' ? 'info' : 'warning'"
                size="small"
                effect="plain">
                {{ row.permission === "view" ? "查看" : "编辑" }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="密码" width="65">
            <template #default="{ row }">
              <el-tag
                v-if="row.accessCode"
                size="small"
                type="warning"
                effect="light">有</el-tag>
              <el-tag v-else size="small" type="info" effect="light">无</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="180" fixed="right">
            <template #default="{ row }">
              <el-button
                v-if="row.isActive && !isShareExpired(row)"
                link
                type="primary"
                size="small"
                @click="copyExistingShareUrl(row)">
                复制链接
              </el-button>
              <el-button
                v-if="row.isActive"
                link
                type="warning"
                size="small"
                @click="toggleShareStatus(row)">
                停用
              </el-button>
              <el-button
                link
                type="danger"
                size="small"
                @click="deleteShare(row.id)">
                删除
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="shares-summary">
          共 <strong>{{ existingShares.length }}</strong> 个分享，
          其中 <strong>{{ activeSharesCount }}</strong> 个有效
        </div>
      </div>

      <div class="new-share-action">
        <el-button type="primary" size="large" @click="goToCreateShare">
          <el-icon><Plus /></el-icon>
          新建分享
        </el-button>
      </div>
    </div>

    <!-- 步骤1：配置分享 -->
    <div v-if="currentStep === 1" class="step-content">
      <el-form label-position="top">
        <!-- 基本信息 -->
        <el-divider content-position="left">基本信息</el-divider>

        <el-form-item label="分享标题">
          <el-input
            v-model="shareForm.title"
            placeholder="请输入分享标题（可选）"
            maxlength="200"
            show-word-limit />
        </el-form-item>

        <el-form-item label="备注">
          <el-input
            v-model="shareForm.description"
            type="textarea"
            :rows="3"
            placeholder="请输入备注信息（可选）" />
        </el-form-item>

        <!-- 分享设置 -->
        <el-divider content-position="left">分享设置</el-divider>

        <el-form-item label="有效期">
          <el-select v-model="shareForm.expiresInHours" style="width: 100%">
            <el-option :value="1" label="1小时" />
            <el-option :value="24" label="1天" />
            <el-option :value="168" label="7天" />
            <el-option :value="720" label="30天" />
            <el-option :value="0" label="永久有效" />
          </el-select>
        </el-form-item>

        <el-form-item label="访问次数限制">
          <el-input-number
            v-model="shareForm.maxAccessCount"
            :min="0"
            :max="10000"
            :controls="true"
            style="width: 100%"
            placeholder="0表示无限制" />
        </el-form-item>

        <el-form-item label="访问密码">
          <el-switch
            v-model="shareForm.requireAccessCode"
            active-text="需要密码"
            inactive-text="无需密码" />
        </el-form-item>

        <el-form-item label="权限">
          <el-radio-group v-model="shareForm.permission">
            <el-radio label="view">仅查看</el-radio>
            <el-radio label="edit">可编辑</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
    </div>

    <!-- 步骤2：获取链接 -->
    <div v-if="currentStep === 2" class="step-content">
      <el-result
        icon="success"
        title="分享链接创建成功"
        sub-title="您可以将以下链接分享给他人访问">
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
                  复制链接
                </el-button>
              </template>
            </el-input>
          </div>

          <!-- 访问密码 -->
          <div
            v-if="createdShare?.accessCode"
            class="share-access-code-block">
            <div class="access-code-row">
              <span class="label">访问密码：</span>
              <span class="code">{{ createdShare.accessCode }}</span>
              <el-button
                link
                type="primary"
                size="small"
                @click="copyAccessCode">
                <el-icon><CopyDocument /></el-icon>
                复制密码
              </el-button>
            </div>
            <el-button
              type="primary"
              plain
              size="small"
              class="copy-all-btn"
              @click="copyLinkAndCode">
              一键复制链接和密码
            </el-button>
          </div>

          <!-- 分享详情 -->
          <div class="share-info mt-4">
            <el-descriptions :column="2" border size="small">
              <el-descriptions-item label="分享标题">
                {{ createdShare?.title || "未命名" }}
              </el-descriptions-item>
              <el-descriptions-item label="权限">
                {{ createdShare?.permission === "view" ? "仅查看" : "可编辑" }}
              </el-descriptions-item>
              <el-descriptions-item label="有效期">
                {{ formatExpiresLabel(createdShare?.expiresAt) }}
              </el-descriptions-item>
              <el-descriptions-item label="访问限制">
                {{ createdShare?.maxAccessCount
                  ? `最多 ${createdShare.maxAccessCount} 次`
                  : "无限制" }}
              </el-descriptions-item>
              <el-descriptions-item
                v-if="createdShare?.description"
                label="备注"
                :span="2">
                {{ createdShare.description }}
              </el-descriptions-item>
            </el-descriptions>
          </div>

          <div class="mt-4 share-actions">
            <el-button @click="currentStep = 1">返回修改</el-button>
            <el-button type="primary" @click="closeDialog">完成分享</el-button>
            <el-button type="success" plain @click="goToCreateShare">
              再创建一个
            </el-button>
          </div>
        </template>
      </el-result>
    </div>

    <template #footer>
      <span v-if="currentStep === 1" class="dialog-footer">
        <el-button @click="currentStep = 0">返回</el-button>
        <el-button
          type="primary"
          :loading="isCreating"
          @click="createShare">
          创建分享
        </el-button>
      </span>
      <span v-else-if="currentStep === 0" class="dialog-footer">
        <el-button @click="closeDialog">关闭</el-button>
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
