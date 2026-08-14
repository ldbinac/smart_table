<template>
  <AuthLayout :title="t('auth.giteeCallbackTitle')">
    <div class="callback-content">
      <el-icon v-if="loading" class="is-loading" :size="48"><Loading /></el-icon>
      <p v-if="loading">{{ t('auth.giteeProcessing') }}</p>
      <template v-else>
        <p v-if="error" class="error-text">{{ error }}</p>
        <p v-else class="success-text">{{ t('auth.giteeLoginSuccess') }}</p>
        <el-button v-if="error" type="primary" @click="goToLogin">
          {{ t('auth.backToLogin') }}
        </el-button>
      </template>
    </div>
  </AuthLayout>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Loading } from '@element-plus/icons-vue'
import { ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth/authStore'
import { authService } from '@/services/api/authService'
import { getDemoConfig } from '@/api/demo'
import AuthLayout from './AuthLayout.vue'
import type { DemoConfig } from '@/api/types'

interface ApiError extends Error {
  code?: number
  error?: string
  response?: {
    status?: number
    data?: {
      error?: string
    }
  }
}

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const authStore = useAuthStore()

const loading = ref(true)
const error = ref('')
const demoConfig = ref<DemoConfig | null>(null)

onMounted(async () => {
  try {
    demoConfig.value = await getDemoConfig()
  } catch {
    demoConfig.value = null
  }

  // Gitee 会把授权参数追加到 URL 的 search 部分（hash 模式路由下不会进入 route.query）
  const searchParams = new URLSearchParams(window.location.search)
  const code = (route.query.code as string) || searchParams.get('code') || ''
  const state = (route.query.state as string) || searchParams.get('state') || ''

  if (!code || !state) {
    error.value = t('auth.giteeParamsIncomplete')
    loading.value = false
    return
  }

  try {
    const response = await authService.verifyGiteeStarCallback(code, state)
    const success = await authStore.completeLogin(response, true)
    if (success) {
      try {
        const searchParams = new URLSearchParams(window.location.search)
        const redirect = (route.query.redirect as string) || searchParams.get('redirect') || '/'
        await router.push(redirect)
      } catch (e) {
        error.value = t('auth.giteeRedirectFailed')
      }
    } else {
      error.value = t('auth.giteeStateSaveFailed')
    }
  } catch (err) {
    const apiErr = err as ApiError
    const status = apiErr.response?.status ?? (typeof apiErr.code === 'number' ? apiErr.code : undefined)
    const errorCode = apiErr.error ?? apiErr.response?.data?.error
    if (status === 403 && errorCode === 'gitee_repo_not_watched') {
      const repoUrl = demoConfig.value?.gitee_repo_url || 'https://gitee.com/binac/smart_table'
      try {
        await ElMessageBox.alert(
          t('auth.giteeWatchTip'),
          t('auth.giteeNotWatched'),
          {
            confirmButtonText: t('auth.confirm'),
            type: 'warning',
            closeOnClickModal: false,
            closeOnPressEscape: false,
            showClose: false,
          }
        )
        window.location.href = repoUrl
      } catch {
        // 用户关闭弹窗，停留在当前页
      }
      return
    }
    error.value = apiErr.message || t('auth.giteeAuthFailed')
  } finally {
    loading.value = false
  }
})

const goToLogin = () => {
  try {
    router.push('/login')
  } catch (e) {
    error.value = t('auth.giteeRedirectRetry')
  }
}
</script>

<style scoped lang="scss">
.callback-content {
  text-align: center;
  padding: 12px 0;
}

.error-text {
  color: #f56c6c;
  margin-bottom: 24px;
}

.success-text {
  color: #67c23a;
}
</style>
