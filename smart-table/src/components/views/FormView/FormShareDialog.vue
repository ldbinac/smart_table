<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { useI18n } from "vue-i18n";
import { ElMessage, ElMessageBox, ElIcon } from "element-plus";
import { Share, Plus, CopyDocument } from "@element-plus/icons-vue";
import { formShareApi, type FormShareConfig } from "@/api/formShare";
import type { FieldEntity } from "@/db/schema";
import { FieldType, type FieldTypeValue, getFieldTypeIconComponent } from "@/types";
import { formatDateTime } from "@/utils/timezone";

const props = defineProps<{
  visible: boolean;
  tableId: string;
  tableName: string;
  fields: FieldEntity[];
}>();

const emit = defineEmits<{
  (e: "update:visible", value: boolean): void;
  (e: "created", share: FormShareConfig): void;
}>();

const { t } = useI18n();

// 对话框可见性
const dialogVisible = computed({
  get: () => props.visible,
  set: (val) => emit("update:visible", val),
});

// 当前步骤
const currentStep = ref(1);

// 表单分享配置
const formConfig = ref({
  title: "",
  description: "",
  submitButtonText: t("view.formSubmit"),
  successMessage: t("view.formSuccessMessage"),
  allowAnonymous: true,
  requireCaptcha: true,
  expiresAt: null as Date | null,
  maxSubmissions: null as number | null,
  allowedFields: [] as string[],
  theme: "default",
  columns: 1,
});

// 已创建的分享
const createdShare = ref<FormShareConfig | null>(null);
const shareUrl = ref("");

// 加载状态
const isCreating = ref(false);
const isLoadingList = ref(false);

// 现有分享列表
const existingShares = ref<FormShareConfig[]>([]);

// 可选字段（排除系统字段）
const availableFields = computed(() => {
  const systemFieldTypes: string[] = [
    FieldType.CREATED_BY,
    FieldType.CREATED_TIME,
    FieldType.UPDATED_BY,
    FieldType.UPDATED_TIME,
    FieldType.AUTO_NUMBER,
  ];

  return props.fields.filter(
    (f) => !systemFieldTypes.includes(f.type as FieldTypeValue)
  );
});

// 计算属性：有效分享数量
const activeSharesCount = computed(() => {
  return existingShares.value.filter(s => s.is_active && !s.is_expired && !s.is_reached_limit).length;
});

// 计算属性：总提交数
const totalSubmissions = computed(() => {
  return existingShares.value.reduce((sum, s) => sum + (s.current_submissions || 0), 0);
});

// 监听对话框打开
watch(
  () => props.visible,
  (val) => {
    if (val) {
      currentStep.value = 0;  // 从步骤0（已分享表单）开始
      resetForm();
      loadExistingShares();
    }
  }
);

// 重置表单
function resetForm() {
  formConfig.value = {
    title: props.tableName || t("view.formDefaultTitle"),
    description: "",
    submitButtonText: t("view.formSubmit"),
    successMessage: t("view.formSuccessMessage"),
    allowAnonymous: true,
    requireCaptcha: true,
    expiresAt: null,
    maxSubmissions: null,
    allowedFields: availableFields.value.map((f) => f.id),
    theme: "default",
    columns: 1,
  };
  createdShare.value = null;
  shareUrl.value = "";
}

// 加载现有分享列表
async function loadExistingShares() {
  if (!props.tableId) return;

  isLoadingList.value = true;
  try {
    const shares = await formShareApi.getFormShares(props.tableId);
    existingShares.value = shares;
  } catch (error) {
    console.error("加载分享列表失败:", error);
  } finally {
    isLoadingList.value = false;
  }
}

// 创建表单分享
async function createShare() {
  if (!props.tableId) {
    ElMessage.error(t("view.formTableIdRequired"));
    return;
  }

  if (formConfig.value.allowedFields.length === 0) {
    ElMessage.error(t("view.formSelectAtLeastOneField"));
    return;
  }

  isCreating.value = true;
  try {
    const result = await formShareApi.createFormShare(props.tableId, {
      title: formConfig.value.title,
      description: formConfig.value.description || undefined,
      submit_button_text: formConfig.value.submitButtonText,
      success_message: formConfig.value.successMessage,
      allow_anonymous: formConfig.value.allowAnonymous,
      require_captcha: formConfig.value.requireCaptcha,
      expires_at: formConfig.value.expiresAt
        ? Math.floor(formConfig.value.expiresAt.getTime() / 1000)
        : undefined,
      max_submissions: formConfig.value.maxSubmissions || undefined,
      allowed_fields: formConfig.value.allowedFields,
      theme: formConfig.value.theme,
      columns: formConfig.value.columns,
    });

    createdShare.value = result;
    shareUrl.value = `${window.location.origin}/#/form/${result.share_token}`;

    ElMessage.success(t("view.formShareCreated"));
    emit("created", result);

    // 进入下一步（获取链接）
    currentStep.value = 2;
  } catch (error: any) {
    console.error("创建表单分享失败:", error);
    ElMessage.error(error.response?.data?.message || t("view.formCreateFailed"));
  } finally {
    isCreating.value = false;
  }
}

// 复制分享链接
async function copyShareUrl() {
  if (!shareUrl.value) return;

  const ok = await copyToClipboard(shareUrl.value);
  if (ok) {
    ElMessage.success(t("view.linkCopied"));
  } else {
    ElMessage.error(t("view.copyFailedManual", { url: shareUrl.value }));
  }
}

// 删除分享
async function deleteShare(shareId: string) {
  try {
    await ElMessageBox.confirm(t("view.confirmDeleteShare"), t("view.deleteRecordTitle"), {
      confirmButtonText: t("view.delete"),
      cancelButtonText: t("view.cancel"),
      type: "warning",
    });

    await formShareApi.deleteFormShare(shareId);
    ElMessage.success(t("view.deleteSuccess"));
    loadExistingShares();
  } catch (error: any) {
    if (error !== "cancel") {
      console.error("删除失败:", error);
      ElMessage.error(t("view.deleteFailedRetry"));
    }
  }
}

// 切换分享状态
async function toggleShareStatus(share: FormShareConfig) {
  try {
    await formShareApi.updateFormShare(share.id, {
      is_active: !share.is_active,
    });
    ElMessage.success(share.is_active ? t("view.deactivated") : t("view.activated"));
    loadExistingShares();
  } catch (error) {
    console.error("更新状态失败:", error);
    ElMessage.error(t("view.operationFailed"));
  }
}

// 格式化日期
function formatShareDate(timestamp: number | null): string {
  if (!timestamp) return t("view.permanentlyValid");
  return formatDateTime(timestamp * 1000);
}

// 获取状态文本
function getStatusText(share: FormShareConfig): string {
  if (!share.is_active) return t("view.deactivated");
  if (share.is_expired) return t("view.expired");
  if (share.is_reached_limit) return t("view.reachedLimit");
  return t("view.active");
}

// 获取状态类型
function getStatusType(share: FormShareConfig): "primary" | "success" | "warning" | "info" | "danger" {
  if (!share.is_active) return "info";
  if (share.is_expired) return "danger";
  if (share.is_reached_limit) return "warning";
  return "success";
}

// 关闭对话框
function closeDialog() {
  dialogVisible.value = false;
}

// 跳转到创建分享步骤
function goToCreateShare() {
  currentStep.value = 1;  // 步骤1：配置表单
  resetForm();
}

// 跳转到分享列表步骤
function goToSharesList() {
  currentStep.value = 0;  // 步骤0：已分享表单
  loadExistingShares();   // 刷新列表
}

// 复制文本到剪贴板（优先使用 Clipboard API，非安全上下文/旧浏览器回退 execCommand）
async function copyToClipboard(text: string): Promise<boolean> {
  // 尝试现代 Clipboard API
  if (navigator.clipboard && window.isSecureContext) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch (_e) {
      // 失败时回退到 execCommand 方案
    }
  }
  // 回退方案：临时 textarea + execCommand('copy')，兼容 HTTP 环境及非用户手势场景
  try {
    const textarea = document.createElement("textarea");
    textarea.value = text;
    textarea.style.position = "fixed";
    textarea.style.top = "-9999px";
    textarea.style.opacity = "0";
    document.body.appendChild(textarea);
    textarea.focus();
    textarea.select();
    const ok = document.execCommand("copy");
    document.body.removeChild(textarea);
    return ok;
  } catch (_e) {
    return false;
  }
}

// 复制现有分享链接
async function copyExistingShareUrl(share: FormShareConfig) {
  const shareUrl = `${window.location.origin}/#/form/${share.share_token}`;
  const ok = await copyToClipboard(shareUrl);
  if (ok) {
    ElMessage.success(t("view.linkCopied"));
  } else {
    ElMessage.error(t("view.copyFailedManual", { url: shareUrl }));
  }
}
</script>

<template>
  <el-dialog
    v-model="dialogVisible"
    :title="t('view.createFormShare')"
    width="700px"
    :close-on-click-modal="false"
    destroy-on-close>
    <el-steps :active="currentStep" finish-status="success" class="mb-4">
      <el-step :title="t('view.shareStepList')" />
      <el-step :title="t('view.shareStepConfig')" />
      <el-step :title="t('view.shareStepLink')" />
    </el-steps>

    <!-- 步骤1：已分享表单 -->
    <div v-if="currentStep === 0" class="step-content">
      <div class="shares-header">
        <h3 class="shares-title">{{ t("view.sharesTitle") }}</h3>
        <p class="shares-description">{{ t("view.sharesDescription") }}</p>
      </div>

      <div v-if="isLoadingList" class="text-center py-4">
        <el-loading :visible="true" />
      </div>

      <el-empty
        v-else-if="existingShares.length === 0"
        :description="t('view.noFormShares')"
        :image-size="80">
        <template #image>
          <el-icon :size="60" color="#c0c4cc"><Share /></el-icon>
        </template>
        <template #description>
          <p style="color: #909399; margin-top: 8px;">{{ t("view.noSharesYet") }}</p>
          <p style="color: #b0b3b8; font-size: 13px;">{{ t("view.createFirstShareHint") }}</p>
        </template>
      </el-empty>

      <div v-else class="shares-list">
        <el-table :data="existingShares" size="default" class="share-table" stripe>
          <el-table-column prop="title" :label="t('view.shareTitle')" min-width="140" show-overflow-tooltip />
          <el-table-column :label="t('view.status')" width="90">
            <template #default="{ row }">
              <el-tag :type="getStatusType(row as FormShareConfig)" size="small" effect="light">
                {{ getStatusText(row as FormShareConfig) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column :label="t('view.submissionCount')" width="100">
            <template #default="{ row }">
              <span class="submission-count">{{ row.current_submissions }}</span>
              <span v-if="row.max_submissions" class="submission-limit">/ {{ row.max_submissions }}</span>
              <span v-else class="submission-unlimited">{{ t("view.noLimit") }}</span>
            </template>
          </el-table-column>
          <el-table-column :label="t('view.expiryTime')" min-width="140">
            <template #default="{ row }">
              {{ formatShareDate(row.expires_at) }}
            </template>
          </el-table-column>
          <el-table-column :label="t('view.actions')" width="180" fixed="right">
            <template #default="{ row }">
              <el-button
                v-if="row.can_submit"
                link
                type="primary"
                size="small"
                @click="copyExistingShareUrl(row as FormShareConfig)">
                {{ t("view.copyLink") }}
              </el-button>
              <el-button
                link
                :type="row.is_active ? 'warning' : 'success'"
                size="small"
                @click="toggleShareStatus(row as FormShareConfig)">
                {{ row.is_active ? t("view.deactivate") : t("view.activate") }}
              </el-button>
              <el-button
                link
                type="danger"
                size="small"
                @click="deleteShare(row.id)">
                {{ t("view.delete") }}
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="shares-summary">
          {{ t("view.sharesSummary", { total: existingShares.length, active: activeSharesCount, submissions: totalSubmissions }) }}
        </div>
      </div>

      <div class="new-share-action">
        <el-button type="primary" size="large" @click="goToCreateShare">
          <el-icon><Plus /></el-icon>
          {{ t("view.newShare") }}
        </el-button>
      </div>
    </div>
      <!-- 步骤2：配置表单 -->
    <div v-if="currentStep === 1" class="step-content">
      <el-form label-position="top">
        <!-- 基本信息 -->
        <el-divider content-position="left">{{ t("view.formBasicInfo") }}</el-divider>

        <el-form-item :label="t('view.formConfigTitleLabel')">
          <el-input
            v-model="formConfig.title"
            :placeholder="t('view.formTitlePlaceholder')"
            maxlength="200"
            show-word-limit />
        </el-form-item>

        <el-form-item :label="t('view.formDescriptionLabel')">
          <el-input
            v-model="formConfig.description"
            type="textarea"
            :rows="3"
            :placeholder="t('view.formDescriptionPlaceholder')" />
        </el-form-item>

        <el-form-item :label="t('view.formSubmitButtonLabel')">
          <el-input
            v-model="formConfig.submitButtonText"
            :placeholder="t('view.formSubmit')"
            maxlength="50" />
        </el-form-item>

        <el-form-item :label="t('view.formSuccessMessageLabel')">
          <el-input
            v-model="formConfig.successMessage"
            :placeholder="t('view.formSuccessMessage')"
            maxlength="500" />
        </el-form-item>

        <!-- 权限设置 -->
        <el-divider content-position="left">{{ t("view.permissionSettings") }}</el-divider>

        <el-form-item>
          <el-switch v-model="formConfig.allowAnonymous" :active-text="t('view.allowAnonymous')" />
        </el-form-item>

        <el-form-item>
          <el-switch v-model="formConfig.requireCaptcha" :active-text="t('view.requireCaptcha')" />
        </el-form-item>

        <el-form-item :label="t('view.expiryTime')">
          <el-date-picker
            v-model="formConfig.expiresAt"
            type="datetime"
            :placeholder="t('view.selectExpiryTime')"
            style="width: 100%" />
        </el-form-item>

        <el-form-item :label="t('view.maxSubmissions')">
          <el-input-number
            v-model="formConfig.maxSubmissions"
            :min="1"
            :max="10000"
            :placeholder="t('view.noLimit')"
            style="width: 100%" />
        </el-form-item>

        <!-- 字段选择 -->
        <el-divider content-position="left">{{ t("view.formFieldConfig") }}</el-divider>

        <el-form-item :label="t('view.allowedFieldsLabel')">
          <el-checkbox-group v-model="formConfig.allowedFields" class="field-checkbox-group">
            <el-checkbox
              v-for="field in availableFields"
              :key="field.id"
              :label="field.id">
              <span class="field-checkbox-label">
                <el-icon class="field-icon">
                  <component :is="getFieldTypeIconComponent(field.type)" />
                </el-icon>
                {{ field.name }}
              </span>
              <el-tag v-if="field.isRequired" size="small" type="danger" class="ml-2">
                {{ t("view.required") }}
              </el-tag>
            </el-checkbox>
          </el-checkbox-group>
          <div v-if="formConfig.allowedFields.length === 0" class="field-hint">
            <el-alert
              :title="t('view.formSelectAtLeastOneField')"
              type="warning"
              :closable="false"
              show-icon />
          </div>
        </el-form-item>

        <!-- 布局设置 -->
        <el-divider content-position="left">{{ t("view.formLayoutConfig") }}</el-divider>

        <el-form-item :label="t('view.formColumns')">
          <el-radio-group v-model="formConfig.columns">
            <el-radio-button :value="1">1</el-radio-button>
            <el-radio-button :value="2">2</el-radio-button>
            <el-radio-button :value="3">3</el-radio-button>
            <el-radio-button :value="4">4</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <div class="field-hint">
          <span>{{ t("view.formColumnsHint") }}</span>
        </div>
      </el-form>
    </div>

    <!-- 步骤3：获取链接 -->
    <div v-else-if="currentStep === 2" class="step-content">
      <el-result
        icon="success"
        :title="t('view.formShareCreated')"
        :sub-title="t('view.shareLinkHint')">
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
                  {{ t("view.copyLink") }}
                </el-button>
              </template>
            </el-input>
          </div>

          <div class="share-info mt-4">
            <el-descriptions :column="1" border size="small">
              <el-descriptions-item :label="t('view.shareTitle')">
                {{ createdShare?.title }}
              </el-descriptions-item>
              <el-descriptions-item :label="t('view.allowAnonymous')">
                {{ createdShare?.allow_anonymous ? t("view.yes") : t("view.no") }}
              </el-descriptions-item>
              <el-descriptions-item :label="t('view.requireCaptcha')">
                {{ createdShare?.require_captcha ? t("view.yes") : t("view.no") }}
              </el-descriptions-item>
              <el-descriptions-item :label="t('view.expiryTime')">
                {{ formatShareDate(createdShare?.expires_at || null) }}
              </el-descriptions-item>
              <el-descriptions-item :label="t('view.maxSubmissions')">
                {{ createdShare?.max_submissions || t("view.noLimit") }}
              </el-descriptions-item>
            </el-descriptions>
          </div>

          <div class="mt-4">
            <el-button type="primary" @click="closeDialog">{{ t("view.done") }}</el-button>
            <el-button @click="goToSharesList">{{ t("view.backToShares") }}</el-button>
            <el-button type="success" plain @click="goToCreateShare">{{ t("view.createAnother") }}</el-button>
          </div>
        </template>
      </el-result>
    </div>

    <template #footer>
      <span v-if="currentStep === 1" class="dialog-footer">
        <el-button @click="goToSharesList">{{ t("view.back") }}</el-button>
        <el-button
          type="primary"
          :loading="isCreating"
          :disabled="formConfig.allowedFields.length === 0"
          @click="createShare">
          {{ t("view.createShare") }}
        </el-button>
      </span>
      <span v-else-if="currentStep === 0" class="dialog-footer">
        <el-button @click="closeDialog">{{ t("view.close") }}</el-button>
      </span>
    </template>
  </el-dialog>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;

.step-content {
  min-height: 400px;
  max-height: 60vh;
  overflow-y: auto;
  padding-right: 8px;
}

// 步骤1：已分享表单
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

// 提交数显示样式
.submission-count {
  font-weight: 600;
  color: $primary-color;
}

.submission-limit {
  color: $text-secondary;
  font-size: 13px;
}

.submission-unlimited {
  color: #b0b3b8;
  font-size: 13px;
}

.field-checkbox-group {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;

  :deep(.el-checkbox) {
    margin-right: 0;
    min-width: 140px;
  }

  .field-checkbox-label {
    display: inline-flex;
    align-items: center;
    gap: 6px;
  }

  .field-icon {
    font-size: 14px;
    color: $text-secondary;
  }
}

.field-hint {
  margin-top: 8px;
}

.share-table {
  margin-top: 16px;
}

.share-url-container {
  max-width: 500px;
  margin: 0 auto;
}

.share-url-input {
  :deep(.el-input__wrapper) {
    background-color: $bg-color;
  }
}

.share-info {
  max-width: 500px;
  margin: 0 auto;
  text-align: left;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

.mb-4 {
  margin-bottom: 24px;
}

.mt-4 {
  margin-top: 24px;
}

.ml-2 {
  margin-left: 8px;
}

.py-4 {
  padding-top: 16px;
  padding-bottom: 16px;
}

.text-center {
  text-align: center;
}
</style>
