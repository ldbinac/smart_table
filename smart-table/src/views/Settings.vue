<template>
  <div class="settings-page">
    <el-card class="settings-card" shadow="never">
      <template #header>
        <div class="card-header">
          <span class="card-title">{{ t('settings.systemSettingsTitle') }}</span>
          <span class="card-subtitle">{{ t('settings.systemSettingsDesc') }}</span>
        </div>
      </template>

      <!-- 外观设置 -->
      <div class="settings-section">
        <h3 class="section-title">{{ t('settings.appearanceSection') }}</h3>

        <div class="setting-item">
          <div class="setting-label">
            <span class="label-text">{{ t('settings.themeMode') }}</span>
            <span class="label-desc">{{ t('settings.themeModeDesc') }}</span>
          </div>
          <div class="setting-control">
            <el-radio-group v-model="theme" @change="handleThemeChange" disabled>
              <el-radio value="light">{{ t('settings.themeLight') }}</el-radio>
              <el-radio value="dark">{{ t('settings.themeDark') }}</el-radio>
              <el-radio value="system">{{ t('settings.themeSystem') }}</el-radio>
            </el-radio-group>
          </div>
        </div>

        <div class="setting-item">
          <div class="setting-label">
            <span class="label-text">{{ t('settings.interfaceLanguage') }}</span>
            <span class="label-desc">{{ t('settings.interfaceLanguageDesc') }}</span>
          </div>
          <div class="setting-control">
            <el-select v-model="language" @change="handleLanguageChange" style="width: 200px">
              <el-option
                v-for="lang in AVAILABLE_LANGUAGES"
                :key="lang.value"
                :label="lang.label"
                :value="lang.value"
              />
            </el-select>
          </div>
        </div>
      </div>

      <!-- 表格设置 -->
      <div class="settings-section" style="display: none;">
        <h3 class="section-title">{{ t('settings.tableSettings') }}</h3>

        <div class="setting-item">
          <div class="setting-label">
            <span class="label-text">{{ t('settings.rowHeight') }}</span>
            <span class="label-desc">{{ t('settings.rowHeightDesc') }}</span>
          </div>
          <div class="setting-control">
            <el-radio-group v-model="rowHeight" @change="handleRowHeightChange">
              <el-radio value="short">{{ t('settings.rowHeightShort') }}</el-radio>
              <el-radio value="medium">{{ t('settings.rowHeightMedium') }}</el-radio>
              <el-radio value="tall">{{ t('settings.rowHeightTall') }}</el-radio>
            </el-radio-group>
          </div>
        </div>

        <div class="setting-item">
          <div class="setting-label">
            <span class="label-text">{{ t('settings.displayGridLines') }}</span>
            <span class="label-desc">{{ t('settings.displayGridLinesDesc') }}</span>
          </div>
          <div class="setting-control">
            <el-switch v-model="gridLines" @change="handleGridLinesChange" />
          </div>
        </div>

        <div class="setting-item">
          <div class="setting-label">
            <span class="label-text">{{ t('settings.stripedRowsLabel') }}</span>
            <span class="label-desc">{{ t('settings.stripedRowsDesc2') }}</span>
          </div>
          <div class="setting-control">
            <el-switch v-model="stripedRows" @change="handleStripedRowsChange" />
          </div>
        </div>
      </div>

      <!-- 数据设置 -->
      <div class="settings-section" style="display: none;">
        <h3 class="section-title">{{ t('settings.dataSection') }}</h3>

        <div class="setting-item">
          <div class="setting-label">
            <span class="label-text">{{ t('settings.autoSave') }}</span>
            <span class="label-desc">{{ t('settings.autoSaveDesc2') }}</span>
          </div>
          <div class="setting-control">
            <el-switch v-model="autoSave" @change="handleAutoSaveChange" />
          </div>
        </div>

        <div class="setting-item">
          <div class="setting-label">
            <span class="label-text">{{ t('settings.confirmBeforeDelete') }}</span>
            <span class="label-desc">{{ t('settings.confirmBeforeDeleteDesc2') }}</span>
          </div>
          <div class="setting-control">
            <el-switch v-model="confirmBeforeDelete" @change="handleConfirmBeforeDeleteChange" />
          </div>
        </div>
      </div>

      <!-- 格式设置 -->
      <div class="settings-section" style="display: none;">
        <h3 class="section-title">{{ t('settings.formatSection') }}</h3>

        <div class="setting-item">
          <div class="setting-label">
            <span class="label-text">{{ t('settings.dateFormat') }}</span>
            <span class="label-desc">{{ t('settings.dateFormatDesc') }}</span>
          </div>
          <div class="setting-control">
            <el-select v-model="dateFormat" @change="handleDateFormatChange" style="width: 200px">
              <el-option label="YYYY-MM-DD" value="YYYY-MM-DD" />
              <el-option label="YYYY/MM/DD" value="YYYY/MM/DD" />
              <el-option label="MM/DD/YYYY" value="MM/DD/YYYY" />
              <el-option label="DD/MM/YYYY" value="DD/MM/YYYY" />
            </el-select>
          </div>
        </div>

        <div class="setting-item">
          <div class="setting-label">
            <span class="label-text">{{ t('settings.timeFormat') }}</span>
            <span class="label-desc">{{ t('settings.timeFormatDesc') }}</span>
          </div>
          <div class="setting-control">
            <el-select v-model="timeFormat" @change="handleTimeFormatChange" style="width: 200px">
              <el-option label="HH:mm:ss" value="HH:mm:ss" />
              <el-option label="HH:mm" value="HH:mm" />
              <el-option label="hh:mm A" value="hh:mm A" />
            </el-select>
          </div>
        </div>

        <div class="setting-item">
          <div class="setting-label">
            <span class="label-text">{{ t('settings.currencySymbol') }}</span>
            <span class="label-desc">{{ t('settings.currencySymbolDesc') }}</span>
          </div>
          <div class="setting-control">
            <el-select v-model="currencySymbol" @change="handleCurrencySymbolChange" style="width: 200px">
              <el-option label="¥" value="¥" />
              <el-option label="$" value="$" />
              <el-option label="€" value="€" />
              <el-option label="£" value="£" />
            </el-select>
          </div>
        </div>
      </div>

      <!-- 重置设置 -->
      <div class="settings-section">
        <div class="setting-item">
          <div class="setting-label">
            <span class="label-text">{{ t('settings.resetSettings') }}</span>
            <span class="label-desc">{{ t('settings.resetSettingsHint') }}</span>
          </div>
          <div class="setting-control">
            <el-button @click="handleResetSettings" type="danger" plain>
              {{ t('settings.resetSettings') }}
            </el-button>
          </div>
        </div>
      </div>

      <!-- 修改密码 -->
      <div class="settings-section" style="display: none;">
        <h3 class="section-title">{{ t('settings.passwordChangeTitle') }}</h3>
        <el-form :model="passwordForm" label-width="120px" class="password-form" ref="passwordFormRef">
          <el-form-item :label="t('settings.currentPasswordLabel')" prop="currentPassword">
            <el-input
              v-model="passwordForm.currentPassword"
              type="password"
              :placeholder="t('settings.currentPasswordPlaceholder')"
              show-password
            />
          </el-form-item>
          <el-form-item :label="t('auth.newPassword')" prop="newPassword">
            <el-input
              v-model="passwordForm.newPassword"
              type="password"
              :placeholder="t('settings.newPasswordPlaceholder')"
              show-password
            />
          </el-form-item>
          <el-form-item :label="t('auth.confirmPassword')" prop="confirmPassword">
            <el-input
              v-model="passwordForm.confirmPassword"
              type="password"
              :placeholder="t('settings.confirmPasswordPlaceholder')"
              show-password
            />
          </el-form-item>
          <el-form-item>
            <div class="password-hint">{{ t('settings.passwordHint') }}</div>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" @click="handleChangePassword" :loading="changingPassword">
              {{ t('auth.changePassword') }}
            </el-button>
          </el-form-item>
        </el-form>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useSettingsStore } from '@/stores/settingsStore'
import type { AppSettings } from '@/stores/settingsStore'
import apiClient from '@/api/client'
import { AVAILABLE_LANGUAGES, type SupportedLocale } from '@/i18n'

const { t } = useI18n()
const settingsStore = useSettingsStore()

// 确保 settingsStore 已加载（store 初始化时即 loadSettings，这里兜底）
onMounted(() => {
  if (settingsStore.loading) {
    settingsStore.loadSettings()
  }
})

// 主题
const theme = ref<string>(settingsStore.settings.theme)
const handleThemeChange = (value: string | number | boolean | undefined) => {
  settingsStore.updateSettings('theme', value as AppSettings['theme'])
}

// 语言
const language = ref<SupportedLocale>(settingsStore.settings.language)
const handleLanguageChange = (value: string | number | boolean | undefined) => {
  settingsStore.setLanguage(value as SupportedLocale)
}

// 行高
const rowHeight = ref<string>(settingsStore.settings.tableRowHeight)
const handleRowHeightChange = (value: string | number | boolean | undefined) => {
  settingsStore.updateSettings('tableRowHeight', value as AppSettings['tableRowHeight'])
}

// 网格线
const gridLines = ref<boolean>(settingsStore.settings.showGridLines)
const handleGridLinesChange = (value: string | number | boolean | undefined) => {
  settingsStore.updateSettings('showGridLines', value as boolean)
}

// 斑马纹
const stripedRows = ref<boolean>(settingsStore.settings.stripeRows)
const handleStripedRowsChange = (value: string | number | boolean | undefined) => {
  settingsStore.updateSettings('stripeRows', value as boolean)
}

// 自动保存
const autoSave = ref<boolean>(settingsStore.settings.autoSave)
const handleAutoSaveChange = (value: string | number | boolean | undefined) => {
  settingsStore.updateSettings('autoSave', value as boolean)
}

// 删除前确认
const confirmBeforeDelete = ref<boolean>(settingsStore.settings.confirmBeforeDelete)
const handleConfirmBeforeDeleteChange = (value: string | number | boolean | undefined) => {
  settingsStore.updateSettings('confirmBeforeDelete', value as boolean)
}

// 日期格式
const dateFormat = ref<string>(settingsStore.settings.dateFormat)
const handleDateFormatChange = (value: string | number | boolean | undefined) => {
  settingsStore.updateSettings('dateFormat', value as string)
}

// 时间格式
const timeFormat = ref<string>(settingsStore.settings.timeFormat)
const handleTimeFormatChange = (value: string | number | boolean | undefined) => {
  settingsStore.updateSettings('timeFormat', value as string)
}

// 货币符号
const currencySymbol = ref<string>(settingsStore.settings.currencySymbol)
const handleCurrencySymbolChange = (value: string | number | boolean | undefined) => {
  settingsStore.updateSettings('currencySymbol', value as string)
}

// 重置设置
const handleResetSettings = async () => {
  try {
    await ElMessageBox.confirm(
      t('settings.resetSettingsConfirm'),
      t('common.confirm'),
      {
        confirmButtonText: t('common.confirm'),
        cancelButtonText: t('common.cancel'),
        type: 'warning'
      }
    )
    settingsStore.resetSettings()
    ElMessage.success(t('common.operationSuccess'))
    // 重置后刷新页面以应用默认设置
    window.location.reload()
  } catch {
    // 用户取消，不做任何操作
  }
}

// 修改密码
const passwordFormRef = ref()
const changingPassword = ref(false)
const passwordForm = reactive({
  currentPassword: '',
  newPassword: '',
  confirmPassword: ''
})

const validatePassword = () => {
  if (passwordForm.newPassword !== passwordForm.confirmPassword) {
    ElMessage.error(t('settings.passwordMismatch'))
    return false
  }
  if (passwordForm.newPassword.length < 8) {
    ElMessage.error(t('settings.passwordTooShort'))
    return false
  }
  if (!/[A-Z]/.test(passwordForm.newPassword)) {
    ElMessage.error(t('settings.passwordNeedUpper'))
    return false
  }
  if (!/[a-z]/.test(passwordForm.newPassword)) {
    ElMessage.error(t('settings.passwordNeedLower'))
    return false
  }
  if (!/\d/.test(passwordForm.newPassword)) {
    ElMessage.error(t('settings.passwordNeedDigit'))
    return false
  }
  return true
}

const handleChangePassword = async () => {
  if (!validatePassword()) {
    return
  }

  changingPassword.value = true
  try {
    await apiClient.put('/auth/password', {
      old_password: passwordForm.currentPassword,
      new_password: passwordForm.newPassword,
    })

    // apiClient 成功（2xx）即视为修改成功
    ElMessage.success(t('settings.passwordChangedSuccess'))
    // 清空表单
    passwordForm.currentPassword = ''
    passwordForm.newPassword = ''
    passwordForm.confirmPassword = ''
  } catch (error: any) {
    const message = error?.message || ''
    if (message && (message.includes('当前密码') || message.includes('incorrect') || message.includes('密码') || message.includes('password'))) {
      ElMessage.error(t('settings.passwordWrongOld'))
    } else {
      ElMessage.error(t('settings.passwordChangeFailed'))
    }
  } finally {
    changingPassword.value = false
  }
}
</script>

<style scoped>
.settings-page {
  padding: 20px;
  max-width: 900px;
  margin: 0 auto;
}

.settings-card {
  border-radius: 8px;
}

.card-header {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.card-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.card-subtitle {
  font-size: 13px;
  color: var(--el-text-color-secondary);
}

.settings-section {
  padding: 16px 0;
  border-bottom: 1px solid var(--el-border-color-lighter);
}

.settings-section:last-child {
  border-bottom: none;
}

.section-title {
  font-size: 15px;
  font-weight: 600;
  margin: 0 0 16px 0;
  color: var(--el-text-color-primary);
}

.setting-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 0;
  gap: 16px;
}

.setting-label {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.label-text {
  font-size: 14px;
  color: var(--el-text-color-primary);
}

.label-desc {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.setting-control {
  flex-shrink: 0;
}

.password-form {
  max-width: 480px;
  margin-top: 8px;
}

.password-hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  line-height: 1.6;
}
</style>
