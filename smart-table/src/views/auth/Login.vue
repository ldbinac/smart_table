<template>
  <AuthLayout
    :title="t('auth.loginTitle')"
    :footer-hint="showPasswordLogin && isRegistrationEnabledState ? t('auth.noAccount') : ''"
    :footer-link-text="t('auth.goRegister')"
    footer-link-to="/register"
    :demo-config="demoConfig">
    <LoginForm
      v-if="showPasswordLogin"
      :loading="isLoading"
      @submit="handleLogin"
      @forgot-password="handleForgotPassword" />

    <E10LoginButton :config="e10Config" :redirect="redirectTarget" />
  </AuthLayout>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth/authStore'
import { authService } from '@/services/api/authService'
import { getDemoConfig } from '@/api/demo'
import { getE10Config, type E10SsoConfig } from '@/extensions/e10/api'
import E10LoginButton from '@/extensions/e10/E10LoginButton.vue'
import AuthLayout from './AuthLayout.vue'
import LoginForm from '@/components/auth/LoginForm.vue'
import type { DemoConfig, LoginResponse, LoginRequest } from '@/api/types'
import { message } from '@/utils/message'
import { isRegistrationEnabled } from '@/utils/securityConfig'

const router = useRouter()
const route = useRoute()
const { t } = useI18n()
const authStore = useAuthStore()

const demoConfig = ref<DemoConfig | null>(null)
const e10Config = ref<E10SsoConfig | null>(null)
const isLoading = ref(false)
const isRegistrationEnabledState = ref(true)

const redirectTarget = computed(() => {
  const redirect = route.query.redirect
  return Array.isArray(redirect) ? String(redirect[0] || '') : String(redirect || '')
})

// 只有 E10 真正启用时，才允许通过 E10_PASSWORD_LOGIN_ENABLED=false 隐藏密码登录；
// E10 未启用/配置不完整时始终保留本地登录，避免把用户锁在门外。
const showPasswordLogin = computed(() => {
  if (!e10Config.value?.enabled) return true
  return e10Config.value.password_login_enabled !== false
})

onMounted(async () => {
  try {
    demoConfig.value = await getDemoConfig()
  } catch {
    demoConfig.value = null
  }

  try {
    e10Config.value = await getE10Config()
  } catch {
    // E10 未配置/不可用时，保持账号密码登录可用
    e10Config.value = null
  }

  try {
    isRegistrationEnabledState.value = await isRegistrationEnabled()
  } catch {
    isRegistrationEnabledState.value = true
  }
})

const handleLogin = async (data: LoginRequest) => {
  isLoading.value = true
  try {
    const response: LoginResponse = await authService.login(data)

    if (response.requires_gitee_star_check && response.user_id) {
      try {
        await ElMessageBox.confirm(
          t('auth.giteeStarTip'),
          t('auth.giteeStarTipTitle'),
          {
            confirmButtonText: t('auth.continue'),
            cancelButtonText: t('common.cancel'),
            type: 'info',
            closeOnClickModal: false,
          }
        )
      } catch {
        // 用户取消，停留在登录页
        return
      }

      try {
        const { authorize_url } = await authService.getGiteeStarAuthorizeUrl(response.user_id)
        window.location.href = authorize_url
      } catch (error) {
        console.error('获取 Gitee 授权链接失败:', error)
        message.error(t('auth.giteeStarFailed'))
      }
      return
    }

    const success = await authStore.completeLogin(response, true)
    if (success) {
      router.push(redirectTarget.value || '/')
    }
  } catch (error: any) {
    console.error('登录失败:', error)
    // 显示后端返回的错误信息（如"邮箱或密码错误"），而不是笼统的"登录已过期"
    message.error(error?.message || t('auth.loginFailedHint'))
  } finally {
    isLoading.value = false
  }
}

const handleForgotPassword = () => {
  router.push('/forgot-password')
}
</script>
