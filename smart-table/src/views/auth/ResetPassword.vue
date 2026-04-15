<template>
  <div class="reset-password-page">
    <div class="reset-container">
      <div class="page-header">
        <h1 class="title">SmartTable</h1>
        <p class="subtitle">多维表格管理系统</p>
      </div>

      <!-- 验证令牌状态 -->
      <div v-if="validating" class="status-box loading">
        <el-icon class="icon" :size="48"><Loading /></el-icon>
        <p>正在验证链接...</p>
      </div>

      <div v-else-if="!tokenValid" class="status-box error">
        <el-icon class="icon" :size="48" color="#f56c6c"><CircleClose /></el-icon>
        <h2>链接无效或已过期</h2>
        <p>{{ errorMessage }}</p>
        <el-button type="primary" @click="goToForgotPassword">重新申请重置</el-button>
      </div>

      <!-- 重置密码表单 -->
      <div v-else-if="!resetSuccess" class="reset-form">
        <h2>重置密码</h2>
        <p class="subtitle">请设置您的新密码</p>

        <el-form
          ref="formRef"
          :model="form"
          :rules="rules"
          label-position="top"
          @keyup.enter="handleSubmit"
        >
          <el-form-item label="新密码" prop="password">
            <el-input
              v-model="form.password"
              type="password"
              placeholder="请输入新密码"
              show-password
            />
          </el-form-item>

          <el-form-item label="确认密码" prop="confirmPassword">
            <el-input
              v-model="form.confirmPassword"
              type="password"
              placeholder="请再次输入新密码"
              show-password
            />
          </el-form-item>

          <el-form-item>
            <el-button
              type="primary"
              :loading="submitting"
              @click="handleSubmit"
              style="width: 100%"
            >
              重置密码
            </el-button>
          </el-form-item>
        </el-form>
      </div>

      <!-- 重置成功 -->
      <div v-else class="status-box success">
        <el-icon class="icon" :size="48" color="#67c23a"><CircleCheck /></el-icon>
        <h2>密码重置成功</h2>
        <p>您的密码已成功重置，请使用新密码登录。</p>
        <el-button type="primary" @click="goToLogin">前往登录</el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Loading, CircleCheck, CircleClose } from '@element-plus/icons-vue'
import type { FormInstance, FormRules } from 'element-plus'
import apiClient from '@/api/client'

const route = useRoute()
const router = useRouter()

const formRef = ref<FormInstance>()
const validating = ref(true)
const tokenValid = ref(false)
const resetSuccess = ref(false)
const submitting = ref(false)
const errorMessage = ref('链接无效或已过期')
const token = ref('')

const form = reactive({
  password: '',
  confirmPassword: ''
})

const validateConfirmPassword = (_rule: any, value: string, callback: Function) => {
  if (value !== form.password) {
    callback(new Error('两次输入的密码不一致'))
  } else {
    callback()
  }
}

const rules: FormRules = {
  password: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 8, message: '密码长度至少为8位', trigger: 'blur' },
    {
      pattern: /^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/,
      message: '密码必须包含大小写字母和数字',
      trigger: 'blur'
    }
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ]
}

const validateToken = async () => {
  token.value = route.query.token as string

  if (!token.value) {
    validating.value = false
    tokenValid.value = false
    errorMessage.value = '无效的重置链接'
    return
  }

  // 令牌格式验证通过，显示重置表单
  // 实际的令牌验证在提交时进行
  validating.value = false
  tokenValid.value = true
}

const handleSubmit = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    submitting.value = true

    try {
      const response = await apiClient.post('/auth/reset-password', {
        token: token.value,
        password: form.password
      })

      if (response.success) {
        resetSuccess.value = true
        ElMessage.success('密码重置成功')
      }
    } catch (error: any) {
      const message = error?.response?.data?.message || '重置失败'
      const errorCode = error?.response?.data?.error

      if (errorCode === 'invalid_token' || errorCode === 'token_expired') {
        tokenValid.value = false
        errorMessage.value = '重置链接已过期，请重新申请'
      } else {
        ElMessage.error(message)
      }
    } finally {
      submitting.value = false
    }
  })
}

const goToLogin = () => {
  router.push('/login')
}

const goToForgotPassword = () => {
  router.push('/forgot-password')
}

onMounted(() => {
  validateToken()
})
</script>

<style scoped lang="scss">
.reset-password-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.reset-container {
  background: white;
  border-radius: 12px;
  padding: 40px;
  width: 100%;
  max-width: 480px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
}

.page-header {
  text-align: center;
  margin-bottom: 32px;

  .title {
    font-size: 36px;
    font-weight: 700;
    color: white;
    margin-bottom: 8px;
    text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  }

  .subtitle {
    font-size: 16px;
    color: rgba(255, 255, 255, 0.9);
  }
}

.reset-form {
  h2 {
    font-size: 20px;
    font-weight: 600;
    margin: 0 0 8px 0;
    color: #333;
    text-align: center;
  }

  .subtitle {
    font-size: 14px;
    color: #666;
    margin: 0 0 24px 0;
    text-align: center;
  }
}

.status-box {
  text-align: center;

  .icon {
    margin-bottom: 16px;
  }

  h2 {
    font-size: 20px;
    font-weight: 600;
    margin: 0 0 12px 0;
    color: #333;
  }

  p {
    font-size: 14px;
    color: #666;
    margin: 0 0 24px 0;
    line-height: 1.6;
  }

  &.loading {
    .icon {
      animation: spin 1s linear infinite;
    }
  }
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
