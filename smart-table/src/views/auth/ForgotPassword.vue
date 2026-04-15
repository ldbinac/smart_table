<template>
  <div class="forgot-password-page">
    <div class="forgot-container">
      <div class="forgot-header">
        <h1 class="title">SmartTable</h1>
        <p class="subtitle">多维表格管理系统</p>
      </div>

      <div class="forgot-box">
        <h2 class="box-title">找回密码</h2>

        <div v-if="!emailSent" class="forgot-form">
          <p class="form-desc">请输入您的注册邮箱，我们将发送密码重置链接</p>

          <el-form
            ref="formRef"
            :model="form"
            :rules="rules"
            @keyup.enter="handleSubmit"
          >
            <el-form-item prop="email">
              <el-input
                v-model="form.email"
                placeholder="请输入邮箱地址"
                size="large"
              />
            </el-form-item>

            <!-- 验证码 -->
            <el-form-item prop="captcha">
              <div class="captcha-input-group">
                <el-input
                  v-model="form.captcha"
                  placeholder="请输入验证码"
                  size="large"
                  maxlength="4"
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
                :loading="submitting"
                @click="handleSubmit"
              >
                发送重置链接
              </el-button>
            </el-form-item>
          </el-form>
        </div>

        <div v-else class="success-box">
          <el-icon class="success-icon" :size="48" color="#67c23a"><CircleCheck /></el-icon>
          <p class="success-text">邮件已发送</p>
          <p class="success-desc">密码重置链接已发送到 <strong>{{ form.email }}</strong></p>
          <p class="success-hint">请检查您的邮箱（包括垃圾邮件文件夹），点击邮件中的链接重置密码。</p>
          <el-button type="primary" @click="goToLogin">返回登录</el-button>
        </div>

        <div v-if="!emailSent" class="forgot-footer">
          <span>想起密码了？</span>
          <el-link type="primary" @click="goToLogin">
            返回登录
          </el-link>
        </div>
      </div>

      <!-- 底部链接 -->
      <div class="page-footer">
        <div class="footer-links">
          <a
            href="https://github.com/ldbinac/smart_table.git"
            target="_blank"
            rel="noopener noreferrer"
            class="footer-link"
            title="GitHub">
            <svg class="footer-icon" viewBox="0 0 24 24" fill="currentColor">
              <path
                d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
            </svg>
          </a>
          <a
            href="https://gitee.com/binac/smart_table.git"
            target="_blank"
            rel="noopener noreferrer"
            class="footer-link"
            title="Gitee">
            <img
              src="/gitee.ico"
              alt="Gitee"
              class="footer-icon"
              style="width: 20px; height: 20px; object-fit: contain" />
          </a>
        </div>
        <p class="footer-text">SmartTable - 开源多维表格管理系统</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { CircleCheck, Refresh } from '@element-plus/icons-vue'
import type { FormInstance, FormRules } from 'element-plus'
import apiClient from '@/api/client'
import { getAuthCaptcha } from '@/api/captcha'

const router = useRouter()
const formRef = ref<FormInstance>()
const submitting = ref(false)
const emailSent = ref(false)
const captchaImage = ref('')

const form = reactive({
  email: '',
  captcha: ''
})

const rules: FormRules = {
  email: [
    { required: true, message: '请输入邮箱地址', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' }
  ],
  captcha: [
    { required: true, message: '请输入验证码', trigger: 'blur' },
    { len: 4, message: '验证码长度为4位', trigger: 'blur' }
  ]
}

// 刷新验证码
async function refreshCaptcha() {
  try {
    const result = await getAuthCaptcha('forgot_password')
    captchaImage.value = result.image
  } catch (error) {
    console.error('获取验证码失败:', error)
  }
}

const handleSubmit = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    submitting.value = true

    try {
      await apiClient.post('/auth/forgot-password', {
        email: form.email,
        captcha: form.captcha
      })

      // 后端返回成功（即使data为null），显示成功状态
      emailSent.value = true
      ElMessage.success('重置邮件已发送')
    } catch (error: any) {
      const message = error?.response?.data?.message || '发送失败'
      ElMessage.error(message)
      // 刷新验证码
      refreshCaptcha()
    } finally {
      submitting.value = false
    }
  })
}

const goToLogin = () => {
  router.push('/login')
}

// 组件挂载时加载验证码
onMounted(() => {
  refreshCaptcha()
})
</script>

<style scoped lang="scss">
.forgot-password-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.forgot-container {
  width: 100%;
  max-width: 420px;
}

.forgot-header {
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

.forgot-box {
  background: white;
  border-radius: 12px;
  padding: 40px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);

  .box-title {
    font-size: 24px;
    font-weight: 600;
    text-align: center;
    margin-bottom: 16px;
    color: #333;
  }

  .form-desc {
    font-size: 14px;
    color: #666;
    text-align: center;
    margin-bottom: 24px;
  }
}

.forgot-form {
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

.forgot-footer {
  text-align: center;
  margin-top: 24px;
  color: #666;

  span {
    margin-right: 4px;
  }
}

.success-box {
  text-align: center;
  padding: 20px 0;

  .success-icon {
    margin-bottom: 16px;
  }

  .success-text {
    font-size: 20px;
    font-weight: 600;
    color: #333;
    margin: 0 0 12px 0;
  }

  .success-desc {
    font-size: 14px;
    color: #333;
    margin: 0 0 8px 0;
  }

  .success-hint {
    font-size: 13px;
    color: #666;
    margin: 0 0 24px 0;
    line-height: 1.6;
  }
}

// 底部链接样式
.page-footer {
  margin-top: 40px;
  text-align: center;
  color: rgba(255, 255, 255, 0.8);

  .footer-links {
    display: flex;
    justify-content: center;
    gap: 20px;
    margin-bottom: 12px;
  }

  .footer-link {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.2);
    transition: all 0.3s ease;

    &:hover {
      background: rgba(255, 255, 255, 0.3);
      transform: translateY(-2px);
    }

    .footer-icon {
      width: 24px;
      height: 24px;
      fill: white;
    }
  }

  .footer-text {
    font-size: 14px;
    opacity: 0.8;
  }
}
</style>
