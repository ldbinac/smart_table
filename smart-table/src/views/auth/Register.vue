<template>
  <AuthLayout
    :title="title"
    footer-hint="已有账号？"
    footer-link-text="立即登录"
    footer-link-to="/login">
    <template v-if="!isRegistrationEnabledState && !isLoading">
      <div class="disabled-icon">
        <el-icon :size="48"><Lock /></el-icon>
      </div>
      <p class="disabled-text">当前系统暂不开放新用户注册，请联系管理员获取账号。</p>
      <div class="disabled-action">
        <el-button type="primary" @click="$router.push('/login')">
          前往登录
        </el-button>
      </div>
    </template>

    <template v-else>
      <div v-if="isLoading" class="loading-box">
        <el-icon class="loading-icon" :size="32"><Loading /></el-icon>
        <p>正在加载...</p>
      </div>

      <RegisterForm v-else :loading="authStore.isLoading" @submit="handleRegister" />
    </template>
  </AuthLayout>
</template>

<script setup lang="ts">
import { computed, ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth/authStore";
import AuthLayout from "./AuthLayout.vue";
import RegisterForm from "@/components/auth/RegisterForm.vue";
import type { RegisterRequest } from "@/api/types";
import { ElMessage } from "element-plus";
import { Lock, Loading } from '@element-plus/icons-vue';
import { isRegistrationEnabled } from '@/utils/securityConfig';

const router = useRouter();
const authStore = useAuthStore();

const isLoading = ref(true);
const isRegistrationEnabledState = ref(true);

const title = computed(() => {
  if (!isLoading.value && !isRegistrationEnabledState.value) {
    return '注册已关闭';
  }
  return '注册';
});

const handleRegister = async (data: RegisterRequest) => {
  if (!isRegistrationEnabledState.value) {
    ElMessage.error("当前系统暂不开放新用户注册");
    return;
  }

  const success = await authStore.register(data);

  if (success) {
    ElMessage.success("注册成功，请登录");
    router.push("/login");
  }
};

onMounted(async () => {
  try {
    isRegistrationEnabledState.value = await isRegistrationEnabled();
  } catch {
    isRegistrationEnabledState.value = true;
  } finally {
    isLoading.value = false;
  }
});
</script>

<style scoped lang="scss">
.disabled-icon {
  color: #909399;
  margin-bottom: 20px;
  text-align: center;
}

.disabled-text {
  color: #666;
  margin-bottom: 20px;
  line-height: 1.6;
  text-align: center;
}

.disabled-action {
  text-align: center;
}

.loading-box {
  text-align: center;
  padding: 40px 0;
  color: #909399;

  .loading-icon {
    animation: spin 1s linear infinite;
    margin-bottom: 16px;
  }
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>
