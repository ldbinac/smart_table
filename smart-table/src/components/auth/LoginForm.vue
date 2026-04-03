<template>
  <el-form
    ref="formRef"
    :model="form"
    :rules="rules"
    class="login-form"
    @submit.prevent="handleSubmit"
  >
    <el-form-item prop="email">
      <el-input
        v-model="form.email"
        placeholder="请输入邮箱"
        size="large"
        :prefix-icon="Message"
      />
    </el-form-item>
    
    <el-form-item prop="password">
      <el-input
        v-model="form.password"
        type="password"
        placeholder="请输入密码"
        size="large"
        :prefix-icon="Lock"
        show-password
        @keyup.enter="handleSubmit"
      />
    </el-form-item>
    
    <el-form-item>
      <div class="form-options">
        <el-checkbox v-model="form.remember">记住登录状态</el-checkbox>
        <el-link type="primary" :underline="false" @click="$emit('forgot-password')">
          忘记密码？
        </el-link>
      </div>
    </el-form-item>
    
    <el-form-item>
      <el-button
        type="primary"
        size="large"
        class="submit-btn"
        :loading="loading"
        @click="handleSubmit"
      >
        登录
      </el-button>
    </el-form-item>
  </el-form>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { Message, Lock } from '@element-plus/icons-vue'
import type { FormInstance, FormRules } from 'element-plus'
import type { LoginRequest } from '@/api/types'

const props = defineProps<{
  loading?: boolean
}>()

const emit = defineEmits<{
  submit: [data: LoginRequest & { remember: boolean }]
  'forgot-password': []
}>()

const formRef = ref<FormInstance>()

const form = reactive({
  email: '',
  password: '',
  remember: false
})

const rules: FormRules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
  ]
}

const handleSubmit = async () => {
  if (!formRef.value) return
  
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  
  emit('submit', {
    email: form.email,
    password: form.password,
    remember: form.remember
  })
}
</script>

<style scoped lang="scss">
.login-form {
  width: 100%;
  
  .form-options {
    display: flex;
    justify-content: space-between;
    align-items: center;
    width: 100%;
  }
  
  .submit-btn {
    width: 100%;
  }
}
</style>
