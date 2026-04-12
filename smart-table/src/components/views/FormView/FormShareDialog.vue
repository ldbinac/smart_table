<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { formShareApi, type FormShareConfig } from "@/api/formShare";
import type { FieldEntity } from "@/db/schema";
import { FieldType } from "@/types";

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
  submitButtonText: "提交",
  successMessage: "提交成功，感谢您的参与！",
  allowAnonymous: true,
  requireCaptcha: false,
  expiresAt: null as Date | null,
  maxSubmissions: null as number | null,
  allowedFields: [] as string[],
  theme: "default",
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
    (f) => !systemFieldTypes.includes(f.type as FieldType)
  );
});

// 监听对话框打开
watch(
  () => props.visible,
  (val) => {
    if (val) {
      currentStep.value = 1;
      resetForm();
      loadExistingShares();
    }
  }
);

// 重置表单
function resetForm() {
  formConfig.value = {
    title: props.tableName || "数据收集表单",
    description: "",
    submitButtonText: "提交",
    successMessage: "提交成功，感谢您的参与！",
    allowAnonymous: true,
    requireCaptcha: false,
    expiresAt: null,
    maxSubmissions: null,
    allowedFields: availableFields.value.map((f) => f.id),
    theme: "default",
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
    ElMessage.error("表格ID不能为空");
    return;
  }

  if (formConfig.value.allowedFields.length === 0) {
    ElMessage.error("请至少选择一个字段");
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
    });

    createdShare.value = result;
    shareUrl.value = `${window.location.origin}/#/form/${result.share_token}`;

    ElMessage.success("表单分享创建成功");
    emit("created", result);

    // 进入下一步
    currentStep.value = 2;
  } catch (error: any) {
    console.error("创建表单分享失败:", error);
    ElMessage.error(error.response?.data?.message || "创建失败，请稍后重试");
  } finally {
    isCreating.value = false;
  }
}

// 复制分享链接
function copyShareUrl() {
  if (!shareUrl.value) return;

  navigator.clipboard
    .writeText(shareUrl.value)
    .then(() => {
      ElMessage.success("链接已复制到剪贴板");
    })
    .catch(() => {
      ElMessage.error("复制失败，请手动复制");
    });
}

// 删除分享
async function deleteShare(shareId: string) {
  try {
    await ElMessageBox.confirm("确定要删除这个表单分享吗？", "确认删除", {
      confirmButtonText: "删除",
      cancelButtonText: "取消",
      type: "warning",
    });

    await formShareApi.deleteFormShare(shareId);
    ElMessage.success("删除成功");
    loadExistingShares();
  } catch (error: any) {
    if (error !== "cancel") {
      console.error("删除失败:", error);
      ElMessage.error("删除失败，请稍后重试");
    }
  }
}

// 切换分享状态
async function toggleShareStatus(share: FormShareConfig) {
  try {
    await formShareApi.updateFormShare(share.id, {
      is_active: !share.is_active,
    });
    ElMessage.success(share.is_active ? "已停用" : "已启用");
    loadExistingShares();
  } catch (error) {
    console.error("更新状态失败:", error);
    ElMessage.error("操作失败，请稍后重试");
  }
}

// 格式化日期
function formatDate(timestamp: number | null): string {
  if (!timestamp) return "永久有效";
  const date = new Date(timestamp * 1000);
  return date.toLocaleString("zh-CN");
}

// 获取状态文本
function getStatusText(share: FormShareConfig): string {
  if (!share.is_active) return "已停用";
  if (share.is_expired) return "已过期";
  if (share.is_reached_limit) return "已达上限";
  return "有效";
}

// 获取状态类型
function getStatusType(share: FormShareConfig): string {
  if (!share.is_active) return "info";
  if (share.is_expired) return "danger";
  if (share.is_reached_limit) return "warning";
  return "success";
}

// 关闭对话框
function closeDialog() {
  dialogVisible.value = false;
}
</script>

<template>
  <el-dialog
    v-model="dialogVisible"
    title="创建表单分享"
    width="700px"
    :close-on-click-modal="false"
    destroy-on-close>
    <el-steps :active="currentStep" finish-status="success" class="mb-4">
      <el-step title="配置表单" />
      <el-step title="获取链接" />
    </el-steps>

    <!-- 步骤1：配置表单 -->
    <div v-if="currentStep === 1" class="step-content">
      <el-form label-position="top">
        <!-- 基本信息 -->
        <el-divider content-position="left">基本信息</el-divider>

        <el-form-item label="表单标题">
          <el-input
            v-model="formConfig.title"
            placeholder="请输入表单标题"
            maxlength="200"
            show-word-limit />
        </el-form-item>

        <el-form-item label="表单描述">
          <el-input
            v-model="formConfig.description"
            type="textarea"
            :rows="3"
            placeholder="请输入表单描述（可选）" />
        </el-form-item>

        <el-form-item label="提交按钮文字">
          <el-input
            v-model="formConfig.submitButtonText"
            placeholder="提交"
            maxlength="50" />
        </el-form-item>

        <el-form-item label="成功提示信息">
          <el-input
            v-model="formConfig.successMessage"
            placeholder="提交成功，感谢您的参与！"
            maxlength="500" />
        </el-form-item>

        <!-- 权限设置 -->
        <el-divider content-position="left">权限设置</el-divider>

        <el-form-item>
          <el-switch v-model="formConfig.allowAnonymous" active-text="允许匿名提交" />
        </el-form-item>

        <el-form-item>
          <el-switch v-model="formConfig.requireCaptcha" active-text="需要验证码" />
        </el-form-item>

        <el-form-item label="过期时间">
          <el-date-picker
            v-model="formConfig.expiresAt"
            type="datetime"
            placeholder="选择过期时间（可选）"
            style="width: 100%" />
        </el-form-item>

        <el-form-item label="最大提交次数">
          <el-input-number
            v-model="formConfig.maxSubmissions"
            :min="1"
            :max="10000"
            placeholder="不限制"
            style="width: 100%" />
        </el-form-item>

        <!-- 字段选择 -->
        <el-divider content-position="left">字段选择</el-divider>

        <el-form-item label="允许填写的字段">
          <el-checkbox-group v-model="formConfig.allowedFields" class="field-checkbox-group">
            <el-checkbox
              v-for="field in availableFields"
              :key="field.id"
              :label="field.id">
              {{ field.name }}
              <el-tag v-if="field.isRequired" size="small" type="danger" class="ml-2">
                必填
              </el-tag>
            </el-checkbox>
          </el-checkbox-group>
          <div v-if="formConfig.allowedFields.length === 0" class="field-hint">
            <el-alert
              title="请至少选择一个字段"
              type="warning"
              :closable="false"
              show-icon />
          </div>
        </el-form-item>
      </el-form>

      <!-- 现有分享列表 -->
      <el-divider content-position="left">现有分享</el-divider>

      <div v-if="isLoadingList" class="text-center py-4">
        <el-loading :visible="true" />
      </div>

      <el-empty
        v-else-if="existingShares.length === 0"
        description="暂无表单分享"
        :image-size="60" />

      <el-table v-else :data="existingShares" size="small" class="share-table">
        <el-table-column prop="title" label="标题" min-width="120" show-overflow-tooltip />
        <el-table-column label="状态" width="80">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row)" size="small">
              {{ getStatusText(row) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="提交数" width="100">
          <template #default="{ row }">
            {{ row.current_submissions }}
            <span v-if="row.max_submissions">/ {{ row.max_submissions }}</span>
          </template>
        </el-table-column>
        <el-table-column label="过期时间" min-width="120">
          <template #default="{ row }">
            {{ formatDate(row.expires_at) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" fixed="right">
          <template #default="{ row }">
            <el-button
              link
              type="primary"
              size="small"
              @click="toggleShareStatus(row)">
              {{ row.is_active ? "停用" : "启用" }}
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
    </div>

    <!-- 步骤2：获取链接 -->
    <div v-else-if="currentStep === 2" class="step-content">
      <el-result
        icon="success"
        title="表单分享创建成功"
        sub-title="您可以将以下链接分享给他人填写">
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

          <div class="share-info mt-4">
            <el-descriptions :column="1" border size="small">
              <el-descriptions-item label="表单标题">
                {{ createdShare?.title }}
              </el-descriptions-item>
              <el-descriptions-item label="允许匿名">
                {{ createdShare?.allow_anonymous ? "是" : "否" }}
              </el-descriptions-item>
              <el-descriptions-item label="需要验证码">
                {{ createdShare?.require_captcha ? "是" : "否" }}
              </el-descriptions-item>
              <el-descriptions-item label="过期时间">
                {{ formatDate(createdShare?.expires_at || null) }}
              </el-descriptions-item>
              <el-descriptions-item label="最大提交次数">
                {{ createdShare?.max_submissions || "不限制" }}
              </el-descriptions-item>
            </el-descriptions>
          </div>

          <div class="mt-4">
            <el-button type="primary" @click="closeDialog">完成</el-button>
            <el-button @click="currentStep = 1">创建新的分享</el-button>
          </div>
        </template>
      </el-result>
    </div>

    <template #footer>
      <span v-if="currentStep === 1" class="dialog-footer">
        <el-button @click="closeDialog">取消</el-button>
        <el-button
          type="primary"
          :loading="isCreating"
          :disabled="formConfig.allowedFields.length === 0"
          @click="createShare">
          创建分享
        </el-button>
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

.field-checkbox-group {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;

  :deep(.el-checkbox) {
    margin-right: 0;
    min-width: 140px;
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
