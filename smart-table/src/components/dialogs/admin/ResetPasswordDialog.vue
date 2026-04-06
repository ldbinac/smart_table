<template>
  <el-dialog
    :model-value="visible"
    @update:model-value="$emit('update:visible', $event)"
    title="重置密码"
    width="500px"
    :close-on-click-modal="false"
  >
    <div class="reset-password-dialog">
      <el-alert
        title="警告"
        type="warning"
        :closable="false"
        style="margin-bottom: 20px"
      >
        <p>重置密码后，用户需要使用新密码登录。</p>
        <p>建议要求用户在首次登录时修改密码。</p>
      </el-alert>

      <el-form label-width="120px" label-position="left">
        <el-form-item label="临时密码">
          <div class="password-input-wrapper">
            <el-input
              v-model="temporaryPassword"
              type="password"
              placeholder="生成临时密码"
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
              生成密码
            </el-button>
          </div>
        </el-form-item>

        <el-form-item label="自定义密码">
          <div class="password-input-wrapper">
            <el-input
              v-model="customPassword"
              type="password"
              placeholder="输入自定义临时密码（可选）"
              show-password
              maxlength="50"
              style="width: 100%"
            />
          </div>
          <div class="form-hint">留空则使用上方生成的临时密码</div>
        </el-form-item>

        <el-form-item label="复制密码">
          <el-button
            type="info"
            size="small"
            @click="copyPassword"
            :disabled="!effectivePassword"
          >
            <el-icon><CopyDocument /></el-icon>
            复制密码到剪贴板
          </el-button>
        </el-form-item>
      </el-form>
    </div>

    <template #footer>
      <el-button @click="handleCancel">取消</el-button>
      <el-button
        type="primary"
        :loading="submitting"
        @click="handleSubmit"
      >
        确定
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick } from 'vue'
import { CopyDocument } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useAdminStore } from '@/stores/adminStore'

const props = defineProps<{
  visible: boolean
  userId: string
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  'success': []
}>()

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
  ElMessage.success('密码已生成')
}

const copyPassword = async () => {
  if (!effectivePassword) {
    ElMessage.warning('请先生成或输入密码')
    return
  }

  try {
    await navigator.clipboard.writeText(effectivePassword.value)
    ElMessage.success('密码已复制到剪贴板')
  } catch (error) {
    ElMessage.error('复制失败，请手动复制')
  }
}

const handleCancel = () => {
  emit('update:visible', false)
}

const handleSubmit = async () => {
  if (!props.userId) {
    ElMessage.error('用户 ID 不能为空')
    return
  }

  if (!effectivePassword) {
    ElMessage.warning('请生成或输入临时密码')
    return
  }

  submitting.value = true
  try {
    await adminStore.resetUserPassword(props.userId, effectivePassword.value)
    ElMessage.success('密码重置成功')
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
