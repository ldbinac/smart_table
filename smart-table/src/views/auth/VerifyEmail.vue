<template>
  <div class="verify-email-page">
    <div class="verify-container">
      <div class="page-header">
        <h1 class="title">SmartTable</h1>
        <p class="subtitle">多维表格管理系统</p>
      </div>

      <div v-if="loading" class="status-box loading">
        <el-icon class="icon" :size="48"><Loading /></el-icon>
        <p>正在验证邮箱...</p>
      </div>

      <div v-else-if="success" class="status-box success">
        <el-icon class="icon" :size="48" color="#67c23a"><CircleCheck /></el-icon>
        <h2>邮箱验证成功</h2>
        <p>您的邮箱已成功验证，现在可以使用全部功能了。</p>
        <el-button type="primary" @click="goToLogin">前往登录</el-button>
      </div>

      <div v-else-if="alreadyVerified" class="status-box info">
        <el-icon class="icon" :size="48" color="#409eff"><InfoFilled /></el-icon>
        <h2>邮箱已验证</h2>
        <p>您的邮箱已经验证过了，无需重复验证。</p>
        <el-button type="primary" @click="goToLogin">前往登录</el-button>
      </div>

      <div v-else-if="expired" class="status-box warning">
        <el-icon class="icon" :size="48" color="#e6a23c"><Warning /></el-icon>
        <h2>验证链接已过期</h2>
        <p>该验证链接已过期，请重新发送验证邮件。</p>
        <el-button type="primary" @click="resendVerification">重新发送验证邮件</el-button>
      </div>

      <div v-else class="status-box error">
        <el-icon class="icon" :size="48" color="#f56c6c"><CircleClose /></el-icon>
        <h2>验证失败</h2>
        <p>{{ errorMessage }}</p>
        <el-button type="primary" @click="goToLogin">返回登录</el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Loading, CircleCheck, CircleClose, Warning, InfoFilled } from '@element-plus/icons-vue'
import apiClient from '@/api/client'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const success = ref(false)
const alreadyVerified = ref(false)
const expired = ref(false)
const errorMessage = ref('验证失败，请稍后重试')

const verifyEmail = async () => {
  const token = route.query.token as string

  if (!token) {
    loading.value = false
    errorMessage.value = '无效的验证链接'
    return
  }

  try {
    const response = await apiClient.get(`/auth/verify-email?token=${token}`)

    if (response.success) {
      success.value = true
    }
  } catch (error: any) {
    const errorCode = error?.response?.data?.error
    const message = error?.response?.data?.message || '验证失败'

    if (errorCode === 'token_expired') {
      expired.value = true
    } else if (errorCode === 'already_verified') {
      alreadyVerified.value = true
    } else {
      errorMessage.value = message
    }
  } finally {
    loading.value = false
  }
}

const resendVerification = async () => {
  try {
    const response = await apiClient.post('/auth/resend-verification')

    if (response.success) {
      ElMessage.success('验证邮件已重新发送，请查收')
    }
  } catch (error: any) {
    const message = error?.response?.data?.message || '发送失败'
    ElMessage.error(message)
  }
}

const goToLogin = () => {
  router.push('/login')
}

onMounted(() => {
  verifyEmail()
})
</script>

<style scoped lang="scss">
.verify-email-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.verify-container {
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
