<template>
  <AuthLayout title="Gitee 授权回调">
    <div class="callback-content">
      <el-icon v-if="loading" class="is-loading" :size="48"><Loading /></el-icon>
      <p v-if="loading">正在处理 Gitee 授权...</p>
      <template v-else>
        <p v-if="error" class="error-text">{{ error }}</p>
        <p v-else class="success-text">登录成功，正在跳转...</p>
        <el-button v-if="error" type="primary" @click="goToLogin">
          返回登录页
        </el-button>
      </template>
    </div>
  </AuthLayout>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Loading } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth/authStore'
import { authService } from '@/services/api/authService'
import AuthLayout from './AuthLayout.vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const loading = ref(true)
const error = ref('')

onMounted(async () => {
  const code = route.query.code as string
  const state = route.query.state as string

  if (!code || !state) {
    error.value = '授权参数不完整，请重新登录'
    loading.value = false
    return
  }

  try {
    const response = await authService.verifyGiteeStarCallback(code, state)
    const success = await authStore.completeLogin(response, true)
    if (success) {
      try {
        const redirect = route.query.redirect as string
        await router.push(redirect || '/')
      } catch (e) {
        error.value = '页面跳转失败，请手动返回首页'
      }
    } else {
      error.value = '登录状态保存失败，请重新登录'
    }
  } catch (err) {
    error.value = err instanceof Error ? err.message : 'Gitee 授权处理失败，请重新登录'
  } finally {
    loading.value = false
  }
})

const goToLogin = () => {
  try {
    router.push('/login')
  } catch (e) {
    error.value = '页面跳转失败，请稍后重试'
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
