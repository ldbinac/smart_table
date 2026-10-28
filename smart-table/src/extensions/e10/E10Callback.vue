<template>
  <AuthLayout :title="t('auth.e10CallbackTitle')">
    <div class="callback-content">
      <el-icon v-if="loading" class="is-loading" :size="48"><Loading /></el-icon>
      <p v-if="loading">{{ t('auth.e10Processing') }}</p>

      <template v-else>
        <p v-if="error" class="error-text">{{ error }}</p>
        <p v-else class="success-text">{{ t('auth.e10LoginSuccess') }}</p>

        <p v-if="upstreamCode" class="error-code">
          {{ t('auth.e10UpstreamCode', { code: upstreamCode }) }}
        </p>

        <el-button v-if="error" type="primary" @click="goToLogin">
          {{ t('auth.backToLogin') }}
        </el-button>
      </template>
    </div>
  </AuthLayout>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Loading } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth/authStore'
import AuthLayout from '@/views/auth/AuthLayout.vue'
import { exchangeE10Ticket } from './api'

const route = useRoute()
const router = useRouter()
const { t } = useI18n()
const authStore = useAuthStore()

const loading = ref(true)
const error = ref('')
const upstreamCode = ref('')

const ERROR_KEYS: Record<string, string> = {
  e10_disabled: 'auth.e10Disabled',
  e10_misconfigured: 'auth.e10ConfigError',
  e10_authorization_denied: 'auth.e10AuthorizationDenied',
  e10_code_missing: 'auth.e10ParamsIncomplete',
  e10_code_expired: 'auth.e10CodeExpired',
  e10_state_missing: 'auth.e10SessionExpired',
  e10_state_mismatch: 'auth.e10SessionExpired',
  e10_state_invalid: 'auth.e10SessionExpired',
  e10_state_expired: 'auth.e10SessionExpired',
  e10_client_invalid: 'auth.e10ConfigError',
  e10_client_not_registered: 'auth.e10ConfigError',
  e10_client_secret_missing: 'auth.e10ConfigError',
  e10_client_secret_unregistered: 'auth.e10ConfigError',
  e10_redirect_missing: 'auth.e10ConfigError',
  e10_redirect_not_registered: 'auth.e10ConfigError',
  e10_redirect_mismatch: 'auth.e10ConfigError',
  e10_app_disabled: 'auth.e10AppDisabled',
  e10_user_not_allowed: 'auth.e10UserNotAllowed',
  e10_user_not_provisioned: 'auth.e10NotProvisioned',
  e10_email_not_configured: 'auth.e10EmailNotConfigured',
  e10_account_disabled: 'auth.e10AccountDisabled',
  e10_ticket_missing: 'auth.e10ExchangeFailed',
  e10_ticket_invalid: 'auth.e10ExchangeFailed',
  e10_ticket_used: 'auth.e10ExchangeFailed',
  e10_network_error: 'auth.e10NetworkError',
  e10_timeout: 'auth.e10NetworkError',
  e10_upstream_error: 'auth.e10UpstreamError',
  e10_upstream_timeout: 'auth.e10UpstreamError',
  e10_invalid_response: 'auth.e10UpstreamError',
  e10_profile_error: 'auth.e10UpstreamError',
  e10_profile_id_missing: 'auth.e10UpstreamError',
  e10_access_token_missing: 'auth.e10UpstreamError',
  e10_access_token_expired: 'auth.e10SessionExpired',
  e10_internal_error: 'auth.e10ExchangeFailed',
}

function queryValue(key: string): string {
  const value = route.query[key]
  if (Array.isArray(value)) return value.length ? String(value[0]) : ''
  return value == null ? '' : String(value)
}

function errorMessage(code: string): string {
  const key = ERROR_KEYS[code] || 'auth.e10ExchangeFailed'
  return t(key)
}

onMounted(async () => {
  const errorCode = queryValue('error')
  const ticket = queryValue('ticket')
  upstreamCode.value = queryValue('e10_code')

  if (errorCode) {
    error.value = errorMessage(errorCode)
    loading.value = false
    return
  }

  if (!ticket) {
    if (authStore.isAuthenticated) {
      await router.replace('/')
      return
    }
    error.value = t('auth.e10ParamsIncomplete')
    loading.value = false
    return
  }

  try {
    const response = await exchangeE10Ticket(ticket)
    const success = await authStore.completeLogin(response, true)
    if (!success) {
      error.value = t('auth.e10StateSaveFailed')
      return
    }
    await router.replace(response.redirect || '/')
  } catch (err: unknown) {
    const apiError = err as { message?: string; code?: number; error?: string }
    if (apiError?.error) {
      error.value = errorMessage(apiError.error)
    } else if (apiError?.code === 403 || apiError?.code === 401) {
      error.value = t('auth.e10ExchangeFailed')
    } else {
      error.value = apiError?.message || t('auth.e10ExchangeFailed')
    }
  } finally {
    loading.value = false
  }
})

function goToLogin() {
  router.replace('/login')
}
</script>

<style scoped lang="scss">
.callback-content {
  text-align: center;
  padding: 12px 0;
}

.error-text {
  color: #f56c6c;
  margin-bottom: 12px;
  line-height: 1.6;
}

.success-text {
  color: #67c23a;
}

.error-code {
  color: #909399;
  font-size: 12px;
  margin-bottom: 18px;
}
</style>
