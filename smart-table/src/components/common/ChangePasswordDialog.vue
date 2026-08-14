<script setup lang="ts">
import { reactive, ref, watch } from "vue";
import { useI18n } from "vue-i18n";
import { ElMessage } from "element-plus";
import { changePassword } from "@/services/api/authService";

const { t } = useI18n();

const props = defineProps<{
  visible: boolean;
}>();

const emit = defineEmits<{
  "update:visible": [value: boolean];
}>();

const loading = ref(false);
const formRef = ref();
const form = reactive({
  currentPassword: "",
  newPassword: "",
  confirmPassword: "",
});

const rules = {
  currentPassword: [
    { required: true, message: t("settings.currentPasswordLabel"), trigger: "blur" },
  ],
  newPassword: [
    { required: true, message: t("settings.newPasswordPlaceholder"), trigger: "blur" },
    { min: 8, message: t("settings.passwordTooShort"), trigger: "blur" },
    {
      validator: (_rule: unknown, value: string, callback: (e?: Error) => void) => {
        if (!value) return callback();
        if (!/[A-Z]/.test(value)) return callback(new Error(t("settings.passwordNeedUpper")));
        if (!/[a-z]/.test(value)) return callback(new Error(t("settings.passwordNeedLower")));
        if (!/\d/.test(value)) return callback(new Error(t("settings.passwordNeedDigit")));
        callback();
      },
      trigger: "blur",
    },
  ],
  confirmPassword: [
    { required: true, message: t("settings.confirmPasswordPlaceholder"), trigger: "blur" },
    {
      validator: (_rule: unknown, value: string, callback: (e?: Error) => void) => {
        if (value !== form.newPassword) return callback(new Error(t("settings.passwordMismatch")));
        callback();
      },
      trigger: "blur",
    },
  ],
};

const resetForm = () => {
  form.currentPassword = "";
  form.newPassword = "";
  form.confirmPassword = "";
  formRef.value?.clearValidate();
};

const close = () => {
  emit("update:visible", false);
};

// 关闭弹窗时重置表单
watch(
  () => props.visible,
  (val) => {
    if (!val) {
      resetForm();
    }
  },
);

const handleSubmit = async () => {
  if (!formRef.value) return;
  const valid = await formRef.value.validate().catch(() => false);
  if (!valid) return;

  loading.value = true;
  try {
    await changePassword(form.currentPassword, form.newPassword);
    ElMessage.success(t("settings.passwordChangedSuccess"));
    emit("update:visible", false);
    resetForm();
  } catch (error: any) {
    const message = error?.message || "";
    if (
      message &&
      (message.includes("当前密码") ||
        message.includes("incorrect") ||
        message.includes("密码") ||
        message.includes("password"))
    ) {
      ElMessage.error(t("settings.passwordWrongOld"));
    } else {
      ElMessage.error(t("settings.passwordChangeFailed"));
    }
  } finally {
    loading.value = false;
  }
};
</script>

<template>
  <el-dialog
    :model-value="visible"
    @update:model-value="emit('update:visible', $event)"
    :title="t('auth.changePassword')"
    width="460px"
    :close-on-click-modal="false"
    append-to-body
    class="change-password-dialog"
    :z-index="3000">
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="90px"
      class="change-password-form"
      @submit.prevent>
      <el-form-item :label="t('auth.currentPassword')" prop="currentPassword">
        <el-input
          v-model="form.currentPassword"
          type="password"
          :placeholder="t('settings.currentPasswordPlaceholder')"
          show-password
          autocomplete="current-password" />
      </el-form-item>
      <el-form-item :label="t('auth.newPassword')" prop="newPassword">
        <el-input
          v-model="form.newPassword"
          type="password"
          :placeholder="t('settings.newPasswordPlaceholder')"
          show-password
          autocomplete="new-password" />
      </el-form-item>
      <el-form-item :label="t('auth.confirmPassword')" prop="confirmPassword">
        <el-input
          v-model="form.confirmPassword"
          type="password"
          :placeholder="t('settings.confirmPasswordPlaceholder')"
          show-password
          autocomplete="new-password" />
      </el-form-item>
      <div class="password-hint">{{ t('settings.passwordHint') }}</div>
    </el-form>
    <template #footer>
      <el-button @click="close">{{ t('common.cancel') }}</el-button>
      <el-button type="primary" :loading="loading" @click="handleSubmit">
        {{ t('common.confirm') }}
      </el-button>
    </template>
  </el-dialog>
</template>

<style scoped>
.password-hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
  line-height: 1.5;
}
</style>
