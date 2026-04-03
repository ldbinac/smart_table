<template>
  <div class="register-page">
    <div class="register-container">
      <div class="register-header">
        <h1 class="title">SmartTable</h1>
        <p class="subtitle">多维表格管理系统</p>
      </div>
      
      <div class="register-box">
        <h2 class="box-title">用户注册</h2>
        
        <RegisterForm
          :loading="authStore.isLoading"
          @submit="handleRegister"
        />
        
        <div class="register-footer">
          <span>已有账号？</span>
          <el-link type="primary" @click="$router.push('/login')">
            立即登录
          </el-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth/authStore'
import RegisterForm from '@/components/auth/RegisterForm.vue'
import type { RegisterRequest } from '@/api/types'

const router = useRouter()
const authStore = useAuthStore()

const handleRegister = async (data: RegisterRequest) => {
  const success = await authStore.register(data)
  
  if (success) {
    // 注册成功，跳转到登录页
    router.push('/login')
  }
}
</script>

<style scoped lang="scss">
.register-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.register-container {
  width: 100%;
  max-width: 420px;
}

.register-header {
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

.register-box {
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

.register-footer {
  text-align: center;
  margin-top: 24px;
  color: #666;
  
  span {
    margin-right: 4px;
  }
}
</style>
