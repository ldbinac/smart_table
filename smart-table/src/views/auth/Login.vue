<template>
  <AuthLayout
    title="登录"
    footer-hint="还没有账号？"
    footer-link-text="立即注册"
    footer-link-to="/register">
    <LoginForm
      :loading="authStore.isLoading"
      @submit="handleLogin"
      @forgot-password="handleForgotPassword" />
  </AuthLayout>
</template>

<script setup lang="ts">
import { useRouter, useRoute } from "vue-router";
import { useAuthStore } from "@/stores/auth/authStore";
import AuthLayout from "./AuthLayout.vue";
import LoginForm from "@/components/auth/LoginForm.vue";

const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();

const handleLogin = async (data: any) => {
  const success = await authStore.login(
    {
      email: data.email,
      password: data.password,
      captcha: data.captcha,
    },
    data.remember,
  );

  if (success) {
    const redirect = route.query.redirect as string;
    router.push(redirect || "/");
  }
};

const handleForgotPassword = () => {
  router.push('/forgot-password');
};
</script>
