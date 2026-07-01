<template>
  <AuthLayout
    title="登录"
    footer-hint="还没有账号？"
    footer-link-text="立即注册"
    footer-link-to="/register"
    :demo-config="demoConfig">
    <LoginForm
      :loading="isLoading"
      @submit="handleLogin"
      @forgot-password="handleForgotPassword" />
  </AuthLayout>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { ElMessageBox } from 'element-plus'
import { useAuthStore } from '@/stores/auth/authStore'
import { authService } from '@/services/api/authService'
import { getDemoConfig } from '@/api/demo'
import AuthLayout from './AuthLayout.vue'
import LoginForm from '@/components/auth/LoginForm.vue'
import type { DemoConfig, LoginResponse, LoginRequest } from '@/api/types'
import { message } from '@/utils/message'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const demoConfig = ref<DemoConfig | null>(null)
const isLoading = ref(false)

onMounted(async () => {
  try {
    demoConfig.value = await getDemoConfig()
  } catch {
    demoConfig.value = null
  }
})

const handleLogin = async (data: LoginRequest) => {
  isLoading.value = true
  try {
    const response: LoginResponse = await authService.login(data)

    if (response.requires_gitee_star_check && response.user_id) {
      try {
        await ElMessageBox.confirm(
          '访问本系统需检测是否 star 本项目，是否继续？',
          '提示',
          {
            confirmButtonText: '继续',
            cancelButtonText: '取消',
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
        message.error('获取 Gitee 授权链接失败，请稍后重试')
      }
      return
    }

    const success = await authStore.completeLogin(response, true)
    if (success) {
      const redirect = Array.isArray(route.query.redirect)
        ? route.query.redirect[0]
        : route.query.redirect
      router.push(redirect || '/')
    }
  } catch (error) {
    console.error('登录失败:', error)
  } finally {
    isLoading.value = false
  }
}

const handleForgotPassword = () => {
  router.push('/forgot-password')
}
</script>
