<template>
  <div v-if="config?.enabled" class="e10-login">
    <el-divider v-if="config.password_login_enabled !== false" class="e10-divider">
      {{ t('auth.e10Or') }}
    </el-divider>

    <el-button class="e10-login-btn" size="large" @click="goToE10">
      <span>{{ t('auth.e10LoginButton') }}</span>
    </el-button>

    <p v-if="config.password_login_enabled === false" class="e10-only-hint">
      {{ t('auth.e10PasswordLoginDisabled') }}
    </p>
  </div>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import { buildE10LoginUrl, type E10SsoConfig } from './api'

const props = defineProps<{
  config: E10SsoConfig | null
  redirect?: string
}>()

const { t } = useI18n()

function goToE10() {
  if (!props.config?.enabled) return
  window.location.assign(buildE10LoginUrl(props.config, props.redirect))
}
</script>

<style scoped lang="scss">
.e10-login {
  width: 100%;
  margin-top: 4px;
}

.e10-divider {
  margin: 18px 0 16px;
  color: #909399;
  font-size: 12px;
}

.e10-login-btn {
  width: 100%;
  height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  border-color: #2f6bff;
  color: #2f6bff;
  font-weight: 600;

  &:hover,
  &:focus {
    border-color: #1f56e0;
    color: #1f56e0;
    background: #f2f6ff;
  }
}

.e10-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 34px;
  height: 20px;
  padding: 0 6px;
  border-radius: 4px;
  background: #2f6bff;
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.3px;
}

.e10-only-hint {
  margin: 10px 0 0;
  color: #909399;
  font-size: 12px;
  line-height: 1.5;
  text-align: center;
}
</style>
