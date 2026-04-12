<script setup lang="ts">
import { ref, computed, onMounted, h } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ElMessage, ElLoading } from "element-plus";
import type { FieldEntity } from "@/db/schema";
import { FieldType, type CellValue, type FieldTypeValue } from "@/types";
import { formShareApi, type FormSchema, type FormFieldSchema } from "@/api/formShare";
import { generateId } from "@/utils/id";
import dayjs from "dayjs";
import AttachmentField from "@/components/fields/AttachmentField.vue";

const route = useRoute();
const router = useRouter();

// 加载状态
const isLoading = ref(true);
const loadError = ref("");

// 表单数据
const shareToken = ref("");
const tableId = ref("");
const tableName = ref("");
const fields = ref<FormFieldSchema[]>([]);
const formValues = ref<Record<string, CellValue>>({});
const formErrors = ref<Record<string, string>>({});
const isSubmitting = ref(false);
const submitSuccess = ref(false);
const newRecordId = ref(generateId());

// 验证码
const captchaCode = ref("");
const captchaImage = ref("");

// 表单配置
const formConfig = ref({
  title: "数据收集表单",
  description: "",
  submitButtonText: "提交",
  successMessage: "提交成功，感谢您的参与！",
  requireCaptcha: false,
});

// 可见字段（根据表单配置和表格配置综合判断）
const visibleFields = computed(() => {
  const systemFieldTypes: string[] = [
    FieldType.CREATED_BY,
    FieldType.CREATED_TIME,
    FieldType.UPDATED_BY,
    FieldType.UPDATED_TIME,
    FieldType.AUTO_NUMBER,
  ];

  // 过滤掉系统字段
  return fields.value.filter(
    (f) => !systemFieldTypes.includes(f.type as FieldTypeValue)
  );
});

// 页面加载时获取表单数据
onMounted(async () => {
  const token = route.params.token as string;

  if (!token) {
    loadError.value = "无效的表单链接";
    isLoading.value = false;
    return;
  }

  shareToken.value = token;

  try {
    await loadFormData(token);
  } catch (error) {
    console.error("加载表单失败:", error);
    loadError.value = "表单加载失败，请检查链接是否有效";
  } finally {
    isLoading.value = false;
  }
});

// 加载表单数据
async function loadFormData(token: string) {
  console.log("[FormShare] Loading form data for token:", token);

  try {
    // 1. 先验证表单分享是否有效
    const validation = await formShareApi.validateFormShare(token);
    console.log("[FormShare] Form validation:", validation);

    if (!validation.valid) {
      loadError.value = "该表单分享已失效或已过期";
      return;
    }

    // 2. 获取表单结构
    const schema = await formShareApi.getFormSchema(token);
    console.log("[FormShare] Form schema:", schema);

    tableId.value = schema.table_id;
    tableName.value = schema.table_name;
    fields.value = schema.fields;

    // 加载表单配置
    formConfig.value = {
      title: schema.form_title || "数据收集表单",
      description: schema.form_description || "",
      submitButtonText: schema.submit_button_text || "提交",
      successMessage: schema.success_message || "提交成功，感谢您的参与！",
      requireCaptcha: schema.require_captcha || false,
    };

    // 如果需要验证码，加载验证码
    if (schema.require_captcha) {
      await refreshCaptcha();
    }

    // 初始化表单值
    resetForm();
  } catch (error: any) {
    console.error("[FormShare] Error loading form data:", error);
    if (error.response?.status === 404) {
      loadError.value = "表单分享不存在";
    } else if (error.response?.status === 403) {
      loadError.value = "该表单分享已失效、已过期或已达到提交次数上限";
    } else {
      loadError.value = "表单加载失败，请稍后重试";
    }
    throw error;
  }
}

// 刷新验证码
async function refreshCaptcha() {
  // TODO: 实现验证码获取接口
  // const result = await formShareApi.getCaptcha(shareToken.value);
  // captchaImage.value = result.image;
  console.log("[FormShare] Refresh captcha");
}

// 验证字段
function validateField(field: FormFieldSchema, value: CellValue): string | null {
  if (
    field.required &&
    (value === null || value === undefined || value === "" || value === false)
  ) {
    return `${field.name}为必填项`;
  }

  if (value === null || value === undefined || value === "") {
    return null;
  }

  switch (field.type) {
    case FieldType.EMAIL:
      if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(String(value))) {
        return "请输入有效的邮箱地址";
      }
      break;
    case FieldType.PHONE:
      if (!/^1[3-9]\d{9}$/.test(String(value))) {
        return "请输入有效的手机号码";
      }
      break;
    case FieldType.URL:
      try {
        new URL(String(value));
      } catch {
        return "请输入有效的URL";
      }
      break;
    case FieldType.NUMBER:
    case FieldType.RATING:
    case FieldType.PERCENT:
    case FieldType.CURRENCY:
      if (typeof value === "number" || !isNaN(Number(value))) {
        const numValue = Number(value);
        const config = field.config || {};
        if (
          config.min !== undefined &&
          numValue < Number(config.min)
        ) {
          return `${field.name}不能小于${config.min}`;
        }
        if (
          config.max !== undefined &&
          numValue > Number(config.max)
        ) {
          return `${field.name}不能大于${config.max}`;
        }
      }
      break;
  }

  return null;
}

// 处理字段值变化
function handleFieldChange(fieldId: string, value: CellValue) {
  formValues.value[fieldId] = value;

  const field = fields.value.find((f) => f.id === fieldId);
  if (field) {
    const error = validateField(field, value);
    if (error) {
      formErrors.value[fieldId] = error;
    } else {
      delete formErrors.value[fieldId];
    }
  }
}

// 提交表单
async function handleSubmit() {
  formErrors.value = {};

  visibleFields.value.forEach((field) => {
    const error = validateField(field, formValues.value[field.id]);
    if (error) {
      formErrors.value[field.id] = error;
    }
  });

  if (Object.keys(formErrors.value).length > 0) {
    const firstError = Object.values(formErrors.value)[0];
    ElMessage.error(firstError);
    return;
  }

  if (!shareToken.value) {
    ElMessage.error("表单配置错误");
    return;
  }

  // 验证验证码
  if (formConfig.value.requireCaptcha && !captchaCode.value) {
    ElMessage.error("请输入验证码");
    return;
  }

  isSubmitting.value = true;

  try {
    const submitData: any = {
      values: { ...formValues.value },
    };

    // 如果需要验证码，添加验证码
    if (formConfig.value.requireCaptcha) {
      submitData.captcha = captchaCode.value;
    }

    const result = await formShareApi.submitForm(shareToken.value, submitData);

    submitSuccess.value = true;
    ElMessage.success(formConfig.value.successMessage);
  } catch (error: any) {
    console.error("提交表单失败:", error);
    
    // 处理验证错误
    if (error.response?.status === 400 && error.response?.data?.details) {
      const details = error.response.data.details;
      Object.entries(details).forEach(([fieldId, message]) => {
        formErrors.value[fieldId] = message as string;
      });
      ElMessage.error("表单数据验证失败，请检查填写内容");
    } else {
      ElMessage.error(error.response?.data?.message || "提交失败，请稍后重试");
    }

    // 刷新验证码
    if (formConfig.value.requireCaptcha) {
      await refreshCaptcha();
      captchaCode.value = "";
    }
  } finally {
    isSubmitting.value = false;
  }
}

// 重置表单
function resetForm() {
  formValues.value = {};
  formErrors.value = {};
  newRecordId.value = generateId();
  captchaCode.value = "";

  // 设置默认值
  visibleFields.value.forEach((field) => {
    const config = field.config || {};
    const defaultValue = config.defaultValue ?? config.default ?? null;
    
    if (defaultValue !== null && defaultValue !== undefined && defaultValue !== "") {
      // 特殊处理日期字段的动态默认值 'now'
      if (field.type === FieldType.DATE && defaultValue === 'now') {
        const showTime = config.showTime as boolean ?? false;
        if (showTime) {
          formValues.value[field.id] = new Date().toISOString();
        } else {
          formValues.value[field.id] = new Date().toISOString().split('T')[0];
        }
      } else if (field.type === FieldType.DATE_TIME && defaultValue === 'now') {
        formValues.value[field.id] = new Date().toISOString();
      } else if (field.type === FieldType.MULTI_SELECT && !Array.isArray(defaultValue)) {
        // 多选字段默认值必须是数组
        formValues.value[field.id] = [defaultValue];
      } else {
        formValues.value[field.id] = defaultValue as CellValue;
      }
    }
  });
}

// 处理附件上传
function handleAttachmentUpload(fieldId: string, newFiles: unknown[]) {
  const currentFiles = (formValues.value[fieldId] as unknown[]) || [];
  const fileMap = new Map<string, unknown>();

  currentFiles.forEach((f) => {
    const file = f as { id: string };
    fileMap.set(file.id, f);
  });

  newFiles.forEach((f) => {
    const file = f as { id: string };
    if (!fileMap.has(file.id)) {
      fileMap.set(file.id, f);
    }
  });

  formValues.value[fieldId] = Array.from(fileMap.values()) as CellValue;
}

// 处理附件删除
function handleAttachmentDelete(fieldId: string, fileId: string) {
  const currentFiles = (formValues.value[fieldId] as unknown[]) || [];
  formValues.value[fieldId] = currentFiles.filter(
    (f: unknown) => (f as { id: string }).id !== fileId,
  ) as CellValue;
}

// 返回首页
function goHome() {
  router.push("/");
}

// 重新加载
function reload() {
  window.location.reload();
}

// 获取字段组件类型
function getFieldComponentType(field: FormFieldSchema): string {
  switch (field.type) {
    case FieldType.TEXT:
    case FieldType.SINGLE_LINE_TEXT:
    case FieldType.LONG_TEXT:
    case FieldType.RICH_TEXT:
    case FieldType.URL:
    case FieldType.EMAIL:
    case FieldType.PHONE:
    case FieldType.BARCODE:
      return "text";
    case FieldType.NUMBER:
    case FieldType.RATING:
    case FieldType.PERCENT:
    case FieldType.CURRENCY:
      return "number";
    case FieldType.SINGLE_SELECT:
      return "single_select";
    case FieldType.MULTI_SELECT:
      return "multi_select";
    case FieldType.DATE:
      return "date";
    case FieldType.DATE_TIME:
      return "datetime";
    case FieldType.CHECKBOX:
      return "checkbox";
    case FieldType.ATTACHMENT:
      return "attachment";
    case FieldType.COLLABORATOR:
    case FieldType.CREATED_BY:
    case FieldType.LAST_MODIFIED_BY:
      return "collaborator";
    case FieldType.PROGRESS:
      return "progress";
    default:
      return "text";
  }
}

// 获取选项
function getSelectOptions(field: FormFieldSchema) {
  const config = field.config || {};
  
  // 支持多种选项格式
  let options = config.choices || config.options || [];
  
  // 确保选项是数组
  if (!Array.isArray(options)) {
    console.warn(`[FormShare] Field ${field.name} options is not an array:`, options);
    return [];
  }
  
  // 规范化选项格式
  return options.map((opt: any) => ({
    id: opt.id || opt.value || String(opt),
    name: opt.name || opt.label || String(opt),
    color: opt.color || opt.colorCode || '#3370FF'
  }));
}

// 获取数值字段精度
function getNumberPrecision(field: FormFieldSchema): number {
  return (field.config?.precision as number) ?? 0;
}

// 获取日期字段是否显示时间
function getDateShowTime(field: FormFieldSchema): boolean {
  return (field.config?.showTime as boolean) ?? false;
}

// 获取日期字段格式
function getDateFormat(field: FormFieldSchema): string {
  return getDateShowTime(field) ? "YYYY-MM-DD HH:mm:ss" : "YYYY-MM-DD";
}

// 获取日期选择器类型
function getDatePickerType(field: FormFieldSchema): "date" | "datetime" {
  return getDateShowTime(field) ? "datetime" : "date";
}

// 处理日期变更
function handleDateChange(fieldId: string, val: Date | null) {
  if (!val) {
    handleFieldChange(fieldId, null);
    return;
  }

  const field = fields.value.find((f) => f.id === fieldId);
  if (!field) return;

  const showTime = getDateShowTime(field);
  if (showTime) {
    handleFieldChange(fieldId, val.getTime());
  } else {
    handleFieldChange(fieldId, dayjs(val).format("YYYY-MM-DD"));
  }
}

// 获取进度最大值
function getProgressMax(field: FormFieldSchema): number {
  return (field.config?.max as number) ?? 100;
}

// 获取进度最小值
function getProgressMin(field: FormFieldSchema): number {
  return (field.config?.min as number) ?? 0;
}
</script>

<template>
  <div class="form-share-page">
    <!-- 加载状态 -->
    <div v-if="isLoading" class="loading-container">
      <el-loading :visible="true" text="加载中..." />
    </div>

    <!-- 错误状态 -->
    <el-result
      v-else-if="loadError"
      icon="error"
      title="无法加载表单"
      :sub-title="loadError">
      <template #extra>
        <el-button @click="goHome">返回首页</el-button>
        <el-button type="primary" @click="reload">重新加载</el-button>
      </template>
    </el-result>

    <!-- 提交成功 -->
    <el-result
      v-else-if="submitSuccess"
      icon="success"
      title="提交成功"
      :sub-title="formConfig.successMessage">
      <template #extra>
        <el-button type="primary" @click="resetForm">继续填写</el-button>
        <el-button @click="goHome">返回首页</el-button>
      </template>
    </el-result>

    <!-- 表单内容 -->
    <div v-else class="form-container">
      <div class="form-header">
        <h1 class="form-title">{{ formConfig.title }}</h1>
        <p v-if="formConfig.description" class="form-description">
          {{ formConfig.description }}
        </p>
      </div>

      <el-form
        label-position="top"
        class="form-content"
        @submit.prevent="handleSubmit">
        <div
          v-for="field in visibleFields"
          :key="field.id"
          class="form-item"
          :class="{ 'has-error': formErrors[field.id] }">
          <label class="form-label">
            {{ field.name }}
            <span v-if="field.required" class="required-mark">*</span>
          </label>

          <div class="form-control">
            <!-- 文本类型 -->
            <template v-if="getFieldComponentType(field) === 'text'">
              <el-input
                :model-value="String(formValues[field.id] || '')"
                :placeholder="`请输入${field.name}`"
                :type="field.type === FieldType.LONG_TEXT ? 'textarea' : 'text'"
                :rows="field.type === FieldType.LONG_TEXT ? 4 : undefined"
                @update:model-value="
                  (val) => handleFieldChange(field.id, val)
                " />
            </template>

            <!-- 数字类型 -->
            <template v-else-if="getFieldComponentType(field) === 'number'">
              <el-input-number
                :model-value="Number(formValues[field.id] || 0)"
                :placeholder="`请输入${field.name}`"
                :precision="getNumberPrecision(field)"
                :min="
                  field.config?.min !== undefined
                    ? Number(field.config.min)
                    : undefined
                "
                :max="
                  field.config?.max !== undefined
                    ? Number(field.config.max)
                    : undefined
                "
                style="width: 100%"
                @update:model-value="
                  (val) => handleFieldChange(field.id, val as CellValue)
                " />
            </template>

            <!-- 单选类型 -->
            <template
              v-else-if="getFieldComponentType(field) === 'single_select'">
              <el-select
                :model-value="formValues[field.id] as string | undefined"
                :placeholder="`请选择${field.name}`"
                style="width: 100%"
                clearable
                @update:model-value="(val) => handleFieldChange(field.id, val)">
                <el-option
                  v-for="option in getSelectOptions(field)"
                  :key="option.id"
                  :label="option.name"
                  :value="option.id">
                  <span
                    class="option-color"
                    :style="{ backgroundColor: option.color || '#3370FF' }" />
                  <span>{{ option.name }}</span>
                </el-option>
              </el-select>
            </template>

            <!-- 多选类型 -->
            <template
              v-else-if="getFieldComponentType(field) === 'multi_select'">
              <el-select
                :model-value="(formValues[field.id] as string[]) || []"
                :placeholder="`请选择${field.name}`"
                style="width: 100%"
                multiple
                clearable
                @update:model-value="(val) => handleFieldChange(field.id, val)">
                <el-option
                  v-for="option in getSelectOptions(field)"
                  :key="option.id"
                  :label="option.name"
                  :value="option.id">
                  <span
                    class="option-color"
                    :style="{ backgroundColor: option.color || '#3370FF' }" />
                  <span>{{ option.name }}</span>
                </el-option>
              </el-select>
            </template>

            <!-- 日期类型 -->
            <template v-else-if="getFieldComponentType(field) === 'date'">
              <el-date-picker
                :model-value="
                  formValues[field.id] as unknown as Date | undefined
                "
                :type="getDatePickerType(field)"
                :placeholder="`请选择${field.name}`"
                :format="getDateFormat(field)"
                style="width: 100%"
                @update:model-value="
                  (val) => handleDateChange(field.id, val as Date | null)
                " />
            </template>

            <!-- 日期时间类型 -->
            <template v-else-if="getFieldComponentType(field) === 'datetime'">
              <el-date-picker
                :model-value="
                  formValues[field.id] as unknown as Date | undefined
                "
                type="datetime"
                :placeholder="`请选择${field.name}`"
                format="YYYY-MM-DD HH:mm:ss"
                style="width: 100%"
                @update:model-value="
                  (val) => handleFieldChange(field.id, val ? val.toISOString() : null)
                " />
            </template>

            <!-- 复选框类型 -->
            <template v-else-if="getFieldComponentType(field) === 'checkbox'">
              <el-switch
                :model-value="Boolean(formValues[field.id])"
                @update:model-value="
                  (val) => handleFieldChange(field.id, val)
                " />
            </template>

            <!-- 进度类型 -->
            <template v-else-if="getFieldComponentType(field) === 'progress'">
              <div class="progress-field">
                <el-slider
                  :model-value="Number(formValues[field.id] || 0)"
                  :min="getProgressMin(field)"
                  :max="getProgressMax(field)"
                  show-stops
                  show-input
                  @update:model-value="(val) => handleFieldChange(field.id, val)"
                />
              </div>
            </template>

            <!-- 联系人类型 -->
            <template v-else-if="getFieldComponentType(field) === 'collaborator'">
              <el-input
                :model-value="String(formValues[field.id] || '')"
                :placeholder="`请输入${field.name}（邮箱或用户名）`"
                @update:model-value="
                  (val) => handleFieldChange(field.id, val)
                " />
            </template>

            <!-- 附件字段类型 -->
            <template v-else-if="getFieldComponentType(field) === 'attachment'">
              <AttachmentField
                :model-value="formValues[field.id]"
                :field="field as unknown as FieldEntity"
                :record-id="newRecordId"
                :readonly="false"
                @update:model-value="(val) => handleFieldChange(field.id, val)"
                @upload="(files) => handleAttachmentUpload(field.id, files)"
                @delete="
                  (fileId) => handleAttachmentDelete(field.id, fileId)
                " />
            </template>

            <!-- 不支持的字段类型 -->
            <template v-else>
              <el-alert
                :title="`不支持的字段类型: ${field.type}`"
                type="warning"
                :closable="false"
                show-icon />
            </template>
          </div>

          <div v-if="formErrors[field.id]" class="form-error">
            <el-icon><Warning /></el-icon>
            {{ formErrors[field.id] }}
          </div>

          <div v-if="field.config?.description" class="form-field-description">
            {{ field.config.description }}
          </div>
        </div>

        <!-- 验证码 -->
        <div v-if="formConfig.requireCaptcha" class="form-item captcha-item">
          <label class="form-label">
            验证码
            <span class="required-mark">*</span>
          </label>
          <div class="captcha-input-group">
            <el-input
              v-model="captchaCode"
              placeholder="请输入验证码"
              maxlength="6"
              style="flex: 1"
            />
            <div class="captcha-image" @click="refreshCaptcha">
              <!-- TODO: 实现验证码图片显示 -->
              <el-button link type="primary" @click="refreshCaptcha">
                <el-icon><Refresh /></el-icon>
                刷新验证码
              </el-button>
            </div>
          </div>
        </div>

        <div class="form-actions">
          <el-button
            type="primary"
            native-type="submit"
            :loading="isSubmitting"
            size="large"
            class="submit-btn">
            {{ formConfig.submitButtonText }}
          </el-button>
        </div>
      </el-form>

      <div class="form-footer">
        <p>Powered by Smart Table</p>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;

.form-share-page {
  min-height: 100vh;
  background: linear-gradient(135deg, #f5f7fa 0%, #e4e8ec 100%);
  padding: 40px 20px;
}

.loading-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
}

.form-container {
  max-width: 640px;
  margin: 0 auto;
  background: $surface-color;
  border-radius: $border-radius-lg;
  box-shadow: 0 4px 24px rgba(0, 0, 0, 0.08);
  overflow: hidden;
}

.form-header {
  text-align: center;
  padding: 40px 32px 24px;
  background: linear-gradient(135deg, $primary-color 0%, #5b8ff9 100%);
  color: white;
}

.form-title {
  font-size: 28px;
  font-weight: 600;
  margin: 0 0 12px;
  color: white;
}

.form-description {
  font-size: $font-size-base;
  margin: 0;
  opacity: 0.9;
  line-height: 1.6;
}

.form-content {
  padding: 32px;
}

.form-item {
  margin-bottom: 24px;

  &.has-error {
    .form-label {
      color: $error-color;
    }

    :deep(.el-input__wrapper),
    :deep(.el-select__wrapper) {
      border-color: $error-color;
      box-shadow: 0 0 0 1px $error-color;
    }
  }
}

.form-label {
  display: block;
  font-size: $font-size-sm;
  font-weight: 500;
  color: $text-primary;
  margin-bottom: 8px;
}

.required-mark {
  color: $error-color;
  margin-left: 4px;
}

.form-control {
  width: 100%;
}

.form-error {
  display: flex;
  align-items: center;
  gap: 4px;
  font-size: $font-size-xs;
  color: $error-color;
  margin-top: 4px;
}

.form-field-description {
  font-size: $font-size-xs;
  color: $text-secondary;
  margin-top: 4px;
  line-height: 1.5;
}

// 验证码样式
.captcha-item {
  .captcha-input-group {
    display: flex;
    gap: 12px;
    align-items: center;
  }

  .captcha-image {
    cursor: pointer;
    padding: 8px 16px;
    background: $bg-color;
    border-radius: $border-radius-base;
    border: 1px solid $border-color;

    &:hover {
      background: $border-color;
    }
  }
}

// 进度条样式
.progress-field {
  padding: 8px 0;
}

.form-actions {
  margin-top: 32px;
  padding-top: 24px;
  border-top: 1px solid $border-color;
}

.submit-btn {
  width: 100%;
  height: 48px;
  font-size: 16px;
}

.form-footer {
  text-align: center;
  padding: 16px;
  background: $bg-color;
  border-top: 1px solid $border-color;

  p {
    margin: 0;
    font-size: $font-size-xs;
    color: $text-secondary;
  }
}

.option-color {
  display: inline-block;
  width: 12px;
  height: 12px;
  border-radius: 50%;
  margin-right: 8px;
  vertical-align: middle;
}

// 响应式适配
@media (max-width: 768px) {
  .form-share-page {
    padding: 0;
    background: $surface-color;
  }

  .form-container {
    border-radius: 0;
    box-shadow: none;
    max-width: none;
  }

  .form-header {
    padding: 24px 20px 16px;
  }

  .form-title {
    font-size: 22px;
  }

  .form-content {
    padding: 20px;
  }

  .captcha-item .captcha-input-group {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
