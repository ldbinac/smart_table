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
        :prefix-icon="User"
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

    <!-- 忘记密码 -->
    <div class="forgot-password-link">
      <el-link type="primary" :underline="false" @click="emit('forgotPassword')">
        忘记密码？
      </el-link>
    </div>

    <!-- 验证码 -->
    <el-form-item prop="captcha">
      <div class="captcha-input-group">
        <el-input
          v-model="form.captcha"
          placeholder="请输入验证码"
          size="large"
          maxlength="6"
          style="flex: 1"
        />
        <div class="captcha-image-wrapper" @click="refreshCaptcha">
          <img
            v-if="captchaImage"
            :src="captchaImage"
            alt="验证码"
            class="captcha-image"
          />
          <div v-else class="captcha-placeholder">
            <el-icon><Refresh /></el-icon>
            <span>点击刷新</span>
          </div>
        </div>
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
import { ref, reactive, onMounted } from 'vue'
import { User, Lock, Refresh } from '@element-plus/icons-vue'
import type { FormInstance, FormRules } from 'element-plus'
import type { LoginRequest } from '@/api/types'
import { getAuthCaptcha } from '@/api/captcha'

const props = defineProps<{
  loading?: boolean
}>()

const emit = defineEmits<{
  submit: [data: LoginRequest]
  forgotPassword: []
}>()

const formRef = ref<FormInstance>()
const captchaImage = ref('')

const form = reactive({
  email: '',
  password: '',
  captcha: ''
})

const rules: FormRules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱格式', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' }
  ],
  captcha: [
    { required: true, message: '请输入验证码', trigger: 'blur' },
    { len: 4, message: '验证码长度为4位', trigger: 'blur' }
  ]
}

// 刷新验证码
async function refreshCaptcha() {
  try {
    const result = await getAuthCaptcha('login')
    captchaImage.value = result.image
  } catch (error) {
    console.error('获取验证码失败:', error)
  }
}

const handleSubmit = async () => {
  if (!formRef.value) return
  
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  
  emit('submit', {
    email: form.email,
    password: form.password,
    captcha: form.captcha
  })
}

// 组件挂载时加载验证码
onMounted(() => {
  refreshCaptcha()
})
</script>

<style scoped lang="scss">
.login-form {
  width: 100%;

  .forgot-password-link {
    text-align: right;
    margin-bottom: 16px;
    margin-top: -8px;
  }

  .submit-btn {
    width: 100%;
  }

  .captcha-input-group {
    display: flex;
    gap: 12px;
    align-items: center;
  }

  .captcha-image-wrapper {
    cursor: pointer;
    width: 120px;
    height: 40px;
    background: #f5f7fa;
    border-radius: 4px;
    border: 1px solid #dcdfe6;
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: center;

    &:hover {
      border-color: #409eff;
    }

    .captcha-image {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }

    .captcha-placeholder {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 2px;
      color: #909399;
      font-size: 12px;
    }
  }
}
</style>
