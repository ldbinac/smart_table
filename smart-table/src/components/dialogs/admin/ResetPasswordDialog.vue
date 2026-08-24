<template>
  <el-dialog
    :model-value="visible"
    @update:model-value="$emit('update:visible', $event)"
    :title="t('user.resetPasswordTitle')"
    width="500px"
    :close-on-click-modal="false"
  >
    <div class="reset-password-dialog">
      <el-alert
        :title="t('user.resetWarningTitle')"
        type="warning"
        :closable="false"
        style="margin-bottom: 20px"
      >
        <p>{{ t('user.resetWarningText') }}</p>
        <p>{{ t('user.resetWarningHint') }}</p>
      </el-alert>

      <el-form label-width="120px" label-position="left">
        <el-form-item :label="t('user.tempPassword')">
          <div class="password-input-wrapper">
            <el-input
              v-model="temporaryPassword"
              type="password"
              :placeholder="t('user.tempPasswordPlaceholder')"
              show-password
              readonly
              style="width: 100%"
            />
            <el-button
              type="primary"
              size="small"
              @click="generatePassword"
              style="margin-left: 8px"
            >
              {{ t('user.generatePassword') }}
            </el-button>
          </div>
        </el-form-item>

        <el-form-item :label="t('user.customPassword')">
          <div class="password-input-wrapper">
            <el-input
              v-model="customPassword"
              type="password"
              :placeholder="t('user.customPasswordPlaceholder')"
              show-password
              maxlength="50"
              style="width: 100%"
            />
          </div>
          <div class="form-hint">{{ t('user.leaveEmptyHint') }}</div>
        </el-form-item>

        <el-form-item :label="t('user.copyPassword')">
          <el-button
            type="info"
            size="small"
            @click="copyPassword"
            :disabled="!effectivePassword"
          >
            <el-icon><CopyDocument /></el-icon>
            {{ t('user.copyPassword') }}
          </el-button>
        </el-form-item>
      </el-form>
    </div>

    <template #footer>
      <el-button @click="handleCancel">{{ t('user.cancel') }}</el-button>
      <el-button
        type="primary"
        :loading="submitting"
        @click="handleSubmit"
      >
        {{ t('user.confirm') }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { CopyDocument } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useAdminStore } from '@/stores/adminStore'
import { useI18n } from 'vue-i18n'

const props = defineProps<{
  visible: boolean
  userId: string
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  'success': []
}>()

const { t } = useI18n()
const adminStore = useAdminStore()

const temporaryPassword = ref('')
const customPassword = ref('')
const submitting = ref(false)

const effectivePassword = computed(() => {
  return customPassword.value || temporaryPassword.value
})

watch(
  () => props.visible,
  (visible) => {
    if (visible) {
      resetForm()
    }
  },
  { immediate: true }
)

const resetForm = () => {
  temporaryPassword.value = ''
  customPassword.value = ''
}

const generatePassword = () => {
  const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789'
  let password = ''
  for (let i = 0; i < 12; i++) {
    password += chars.charAt(Math.floor(Math.random() * chars.length))
  }
  temporaryPassword.value = password
  ElMessage.success(t('user.passwordGenerated'))
}

const copyPassword = async () => {
  if (!effectivePassword) {
    ElMessage.warning(t('user.copyEmptyWarning'))
    return
  }

  try {
    await navigator.clipboard.writeText(effectivePassword.value)
    ElMessage.success(t('user.copySuccess'))
  } catch (error) {
    ElMessage.error(t('user.copyFailed'))
  }
}

const handleCancel = () => {
  emit('update:visible', false)
}

const handleSubmit = async () => {
  if (!props.userId) {
    ElMessage.error(t('user.userIdEmptyError'))
    return
  }

  if (!effectivePassword) {
    ElMessage.warning(t('user.tempPasswordEmptyWarning'))
    return
  }

  submitting.value = true
  try {
    await adminStore.resetUserPassword(props.userId, effectivePassword.value)
    ElMessage.success(t('user.resetSuccess'))
    emit('success')
  } catch (error) {
    console.error('密码重置失败:', error)
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped lang="scss">
.reset-password-dialog {
  padding: 8px 0;

  .password-input-wrapper {
    display: flex;
    align-items: center;
    width: 100%;
  }

  .form-hint {
    font-size: 12px;
    color: var(--el-text-color-secondary);
    margin-top: 4px;
  }
}
</style>
