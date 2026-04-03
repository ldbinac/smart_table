<template>
  <div class="login-page">
    <div class="login-container">
      <div class="login-header">
        <h1 class="title">SmartTable</h1>
        <p class="subtitle">多维表格管理系统</p>
      </div>
      
      <div class="login-box">
        <h2 class="box-title">用户登录</h2>
        
        <LoginForm
          :loading="authStore.isLoading"
          @submit="handleLogin"
          @forgot-password="handleForgotPassword"
        />
        
        <div class="login-footer">
          <span>还没有账号？</span>
          <el-link type="primary" @click="$router.push('/register')">
            立即注册
          </el-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth/authStore'
import LoginForm from '@/components/auth/LoginForm.vue'
import type { LoginRequest } from '@/api/types'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const handleLogin = async (data: LoginRequest & { remember: boolean }) => {
  const success = await authStore.login(
    { email: data.email, password: data.password },
    data.remember
  )
  
  if (success) {
    // 获取重定向地址
    const redirect = route.query.redirect as string
    router.push(redirect || '/')
  }
}

const handleForgotPassword = () => {
  // TODO: 实现忘记密码功能
  console.log('忘记密码')
}
</script>

<style scoped lang="scss">
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.login-container {
  width: 100%;
  max-width: 420px;
}

.login-header {
  text-align: center;
  margin-bottom: 40px;
  color: white;
  
  .title {
    font-size: 36px;
    font-weight: 700;
    margin-bottom: 8px;
    text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  }
  
  .subtitle {
    font-size: 16px;
    opacity: 0.9;
  }
}

.login-box {
  background: white;
  border-radius: 12px;
  padding: 40px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);
  
  .box-title {
    font-size: 24px;
    font-weight: 600;
    text-align: center;
    margin-bottom: 30px;
    color: #333;
  }
}

.login-footer {
  text-align: center;
  margin-top: 24px;
  color: #666;
  
  span {
    margin-right: 4px;
  }
}
</style>
