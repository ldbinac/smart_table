<template>
  <div class="system-settings-page">
    <div class="page-header">
      <h1 class="page-title">系统配置</h1>
    </div>

    <div class="page-content">
      <el-tabs v-model="activeTab" type="border-card" class="settings-tabs">
        <!-- 基础配置 -->
        <el-tab-pane label="基础配置" name="basic">
          <el-form :model="basicConfigs" label-width="200px" label-position="top">
            <el-form-item label="系统名称">
              <el-input v-model="basicConfigs.system_name" placeholder="请输入系统名称" />
            </el-form-item>
            <el-form-item label="系统描述">
              <el-input
                v-model="basicConfigs.system_description"
                type="textarea"
                :rows="3"
                placeholder="请输入系统描述"
              />
            </el-form-item>
            <el-form-item label="每页记录数">
              <el-input-number
                v-model="basicConfigs.page_size"
                :min="10"
                :max="100"
                :step="10"
              />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="saving" @click="saveBasicConfigs">
                保存配置
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 安全配置 -->
        <el-tab-pane label="安全配置" name="security">
          <el-form :model="securityConfigs" label-width="200px" label-position="top">
            <el-form-item label="密码最小长度">
              <el-input-number
                v-model="securityConfigs.password_min_length"
                :min="6"
                :max="50"
              />
            </el-form-item>
            <el-form-item label="会话超时时间（分钟）">
              <el-input-number
                v-model="securityConfigs.session_timeout"
                :min="5"
                :max="1440"
                :step="5"
              />
            </el-form-item>
            <el-form-item label="启用双因素认证">
              <el-switch v-model="securityConfigs.enable_2fa" />
            </el-form-item>
            <el-form-item label="允许注册">
              <el-switch v-model="securityConfigs.enable_registration" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="saving" @click="saveSecurityConfigs">
                保存配置
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>

        <!-- 邮件配置 -->
        <el-tab-pane label="邮件配置" name="email" class="email-config-pane">
          <div class="email-form-container">
            <el-form
              ref="emailFormRef"
              :model="emailConfigs"
              :rules="emailRules"
              label-width="200px"
              label-position="top"
            >
            <el-form-item label="启用邮件服务">
              <el-switch v-model="emailConfigs.email_enabled" />
            </el-form-item>
            <el-form-item label="SMTP 服务器" prop="smtp_host">
              <el-input
                v-model="emailConfigs.smtp_host"
                placeholder="smtp.example.com"
                :disabled="!emailConfigs.email_enabled"
              />
            </el-form-item>
            <el-form-item label="SMTP 端口" prop="smtp_port">
              <el-input-number
                v-model="emailConfigs.smtp_port"
                :min="1"
                :max="65535"
                :disabled="!emailConfigs.email_enabled"
              />
            </el-form-item>
            <el-form-item label="发件人邮箱" prop="sender_email">
              <el-input
                v-model="emailConfigs.sender_email"
                placeholder="noreply@example.com"
                :disabled="!emailConfigs.email_enabled"
              />
            </el-form-item>
            <el-form-item label="发件人显示名称">
              <el-input
                v-model="emailConfigs.sender_name"
                placeholder="Smart Table"
                :disabled="!emailConfigs.email_enabled"
              />
            </el-form-item>
            <el-form-item label="SMTP 账号" prop="smtp_username">
              <el-input
                v-model="emailConfigs.smtp_username"
                placeholder="请输入SMTP账号"
                :disabled="!emailConfigs.email_enabled"
              />
            </el-form-item>
            <el-form-item label="SMTP 密码" prop="smtp_password">
              <el-input
                v-model="emailConfigs.smtp_password"
                type="password"
                placeholder="请输入SMTP密码"
                show-password
                :disabled="!emailConfigs.email_enabled"
              />
            </el-form-item>
            <el-form-item label="加密方式">
              <el-select
                v-model="emailConfigs.encryption_type"
                placeholder="请选择加密方式"
                :disabled="!emailConfigs.email_enabled"
                style="width: 100%"
              >
                <el-option label="SSL" value="ssl" />
                <el-option label="TLS" value="tls" />
                <el-option label="无" value="none" />
              </el-select>
            </el-form-item>
            <el-divider />
            <el-form-item label="测试邮箱地址">
              <el-input
                v-model="emailConfigs.test_email"
                placeholder="请输入测试邮箱地址"
                :disabled="!emailConfigs.email_enabled"
              />
            </el-form-item>
            <el-form-item>
              <el-button
                type="success"
                :disabled="!emailConfigs.email_enabled || !emailConfigs.test_email"
                :loading="sendingTestEmail"
                @click="sendTestEmail"
              >
                发送测试邮件
              </el-button>
            </el-form-item>
              <el-form-item>
                <el-button type="primary" :loading="saving" @click="saveEmailConfigs">
                  保存配置
                </el-button>
              </el-form-item>
            </el-form>
          </div>
        </el-tab-pane>

        <!-- 其他配置 -->
        <el-tab-pane label="其他配置" name="other">
          <el-form :model="otherConfigs" label-width="200px" label-position="top">
            <el-form-item label="启用日志记录">
              <el-switch v-model="otherConfigs.enable_logging" />
            </el-form-item>
            <el-form-item label="日志保留天数">
              <el-input-number
                v-model="otherConfigs.log_retention_days"
                :min="1"
                :max="365"
              />
            </el-form-item>
            <el-form-item label="启用性能监控">
              <el-switch v-model="otherConfigs.enable_performance_monitoring" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="saving" @click="saveOtherConfigs">
                保存配置
              </el-button>
            </el-form-item>
          </el-form>
        </el-tab-pane>
      </el-tabs>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import { ElMessage } from 'element-plus'
import { useAdminStore } from '@/stores/adminStore'

const adminStore = useAdminStore()

const activeTab = ref('basic')
const saving = ref(false)
const sendingTestEmail = ref(false)
const emailFormRef = ref<FormInstance>()

const systemConfigs = computed(() => adminStore.systemConfigs)

const basicConfigs = reactive({
  system_name: '',
  system_description: '',
  page_size: 20
})

const securityConfigs = reactive({
  password_min_length: 8,
  session_timeout: 60,
  enable_2fa: false,
  enable_registration: true
})

const emailConfigs = reactive({
  email_enabled: false,
  smtp_host: '',
  smtp_port: 587,
  sender_email: '',
  sender_name: '',
  smtp_username: '',
  smtp_password: '',
  encryption_type: 'ssl' as 'ssl' | 'tls' | 'none',
  test_email: ''
})

const otherConfigs = reactive({
  enable_logging: true,
  log_retention_days: 30,
  enable_performance_monitoring: false
})

const emailRules: FormRules = {
  smtp_host: [
    { required: true, message: '请输入SMTP服务器地址', trigger: 'blur' }
  ],
  smtp_port: [
    { required: true, message: '请输入SMTP端口', trigger: 'blur' }
  ],
  sender_email: [
    { required: true, message: '请输入发件人邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入正确的邮箱地址', trigger: 'blur' }
  ],
  smtp_username: [
    { required: true, message: '请输入SMTP账号', trigger: 'blur' }
  ],
  smtp_password: [
    { required: true, message: '请输入SMTP密码', trigger: 'blur' }
  ]
}

const loadConfigs = () => {
  const configs = systemConfigs.value

  // 基础配置
  basicConfigs.system_name = configs['system_name']?.config_value || 'Smart Table'
  basicConfigs.system_description = configs['system_description']?.config_value || ''
  basicConfigs.page_size = configs['page_size']?.config_value || 20

  // 安全配置
  securityConfigs.password_min_length = configs['password_min_length']?.config_value || 8
  securityConfigs.session_timeout = configs['session_timeout']?.config_value || 60
  securityConfigs.enable_2fa = configs['enable_2fa']?.config_value || false
  securityConfigs.enable_registration = configs['enable_registration']?.config_value || true

  // 邮件配置
  emailConfigs.email_enabled = configs['email_enabled']?.config_value || false
  emailConfigs.smtp_host = configs['smtp_host']?.config_value || ''
  emailConfigs.smtp_port = configs['smtp_port']?.config_value || 587
  emailConfigs.sender_email = configs['sender_email']?.config_value || ''
  emailConfigs.sender_name = configs['sender_name']?.config_value || ''
  emailConfigs.smtp_username = configs['smtp_username']?.config_value || ''
  emailConfigs.smtp_password = configs['smtp_password']?.config_value || ''
  emailConfigs.encryption_type = configs['encryption_type']?.config_value || 'ssl'

  // 其他配置
  otherConfigs.enable_logging = configs['enable_logging']?.config_value || true
  otherConfigs.log_retention_days = configs['log_retention_days']?.config_value || 30
  otherConfigs.enable_performance_monitoring = configs['enable_performance_monitoring']?.config_value || false
}

const saveBasicConfigs = async () => {
  saving.value = true
  try {
    await adminStore.updateSystemConfig([
      { key: 'system_name', value: basicConfigs.system_name, group: 'basic' },
      { key: 'system_description', value: basicConfigs.system_description, group: 'basic' },
      { key: 'page_size', value: basicConfigs.page_size, group: 'basic' }
    ])
    ElMessage.success('基础配置保存成功')
  } catch (error) {
    ElMessage.error('保存配置失败')
  } finally {
    saving.value = false
  }
}

const saveSecurityConfigs = async () => {
  saving.value = true
  try {
    await adminStore.updateSystemConfig([
      { key: 'password_min_length', value: securityConfigs.password_min_length, group: 'security' },
      { key: 'session_timeout', value: securityConfigs.session_timeout, group: 'security' },
      { key: 'enable_2fa', value: securityConfigs.enable_2fa, group: 'security' },
      { key: 'enable_registration', value: securityConfigs.enable_registration, group: 'security' }
    ])
    ElMessage.success('安全配置保存成功')
  } catch (error) {
    ElMessage.error('保存配置失败')
  } finally {
    saving.value = false
  }
}

const saveEmailConfigs = async () => {
  if (!emailFormRef.value) return

  const valid = await emailFormRef.value.validate().catch(() => false)
  if (!valid) return

  saving.value = true
  try {
    await adminStore.updateSystemConfig([
      { key: 'email_enabled', value: emailConfigs.email_enabled, group: 'email' },
      { key: 'smtp_host', value: emailConfigs.smtp_host, group: 'email' },
      { key: 'smtp_port', value: emailConfigs.smtp_port, group: 'email' },
      { key: 'sender_email', value: emailConfigs.sender_email, group: 'email' },
      { key: 'sender_name', value: emailConfigs.sender_name, group: 'email' },
      { key: 'smtp_username', value: emailConfigs.smtp_username, group: 'email' },
      { key: 'smtp_password', value: emailConfigs.smtp_password, group: 'email' },
      { key: 'encryption_type', value: emailConfigs.encryption_type, group: 'email' }
    ])
    ElMessage.success('邮件配置保存成功')
  } catch (error) {
    ElMessage.error('保存配置失败')
  } finally {
    saving.value = false
  }
}

const saveOtherConfigs = async () => {
  saving.value = true
  try {
    await adminStore.updateSystemConfig([
      { key: 'enable_logging', value: otherConfigs.enable_logging, group: 'other' },
      { key: 'log_retention_days', value: otherConfigs.log_retention_days, group: 'other' },
      { key: 'enable_performance_monitoring', value: otherConfigs.enable_performance_monitoring, group: 'other' }
    ])
    ElMessage.success('其他配置保存成功')
  } catch (error) {
    ElMessage.error('保存配置失败')
  } finally {
    saving.value = false
  }
}

const sendTestEmail = async () => {
  if (!emailConfigs.test_email) {
    ElMessage.warning('请输入测试邮箱地址')
    return
  }

  sendingTestEmail.value = true
  try {
    await adminStore.sendTestEmail({
      smtp_host: emailConfigs.smtp_host,
      smtp_port: emailConfigs.smtp_port,
      sender_email: emailConfigs.sender_email,
      sender_name: emailConfigs.sender_name,
      smtp_username: emailConfigs.smtp_username,
      smtp_password: emailConfigs.smtp_password,
      encryption_type: emailConfigs.encryption_type
    }, emailConfigs.test_email)
  } catch (error) {
    console.error('发送测试邮件失败:', error)
  } finally {
    sendingTestEmail.value = false
  }
}

onMounted(async () => {
  await adminStore.fetchSystemConfigs()
  loadConfigs()
})
</script>

<style scoped lang="scss">
.system-settings-page {
  padding: 24px;

  .page-header {
    margin-bottom: 24px;

    .page-title {
      font-size: 24px;
      font-weight: 600;
      margin: 0;
    }
  }

  .page-content {
    .settings-tabs {
      min-height: 500px;
    }

    .settings-tabs :deep(.el-tabs__content) {
      max-height: calc(100vh - 280px);
      overflow-y: auto;
      padding-right: 16px;
    }

    .settings-tabs :deep(.el-tab-pane) {
      padding-bottom: 40px;
    }

    .el-form {
      max-width: 600px;
      margin-top: 24px;
    }
  }
}
</style>
