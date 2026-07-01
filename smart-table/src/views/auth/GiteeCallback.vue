<template>
  <div class="gitee-callback-page">
    <div class="callback-box">
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
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Loading } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth/authStore'
import { authService } from '@/services/api/authService'

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
      const redirect = route.query.redirect as string
      await router.push(redirect || '/')
    } else {
      error.value = '登录状态保存失败，请重新登录'
    }
  } catch (err: any) {
    error.value = err?.message || 'Gitee 授权处理失败，请重新登录'
  } finally {
    loading.value = false
  }
})

const goToLogin = () => {
  router.push('/login')
}
</script>

<style scoped lang="scss">
.gitee-callback-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 50%, #9333ea 100%);
}

.callback-box {
  background: rgba(255, 255, 255, 0.9);
  backdrop-filter: blur(20px);
  border-radius: 16px;
  padding: 48px;
  text-align: center;
  min-width: 320px;
  box-shadow: 0 24px 60px rgba(0, 0, 0, 0.18);
}

.error-text {
  color: #f56c6c;
  margin-bottom: 24px;
}

.success-text {
  color: #67c23a;
}
</style>
