import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import type { User, LoginResponse } from '@/api/types';
import { getToken, setToken as setAuthToken, clearToken as clearAuthToken } from '@/utils/auth/token';

import { authService } from '@/services/api/authService';

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(getToken());
  const refreshTokenValue = ref<string | null>(getToken());
  const user = ref<User | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  const isAuthenticated = computed(() => !!token.value);
  const isAdmin = computed(() => {
    const userRole = user.value?.role;
    return userRole === 'admin' || userRole === 'workspace_admin';
  });

  function setToken(accessToken: string, refreshTok?: string) {
    token.value = accessToken;
    if (refreshTok) {
      refreshTokenValue.value = refreshTok;
      setAuthToken(accessToken, true);
      setAuthToken(refreshTok, true);
    } else {
      setAuthToken(accessToken, true);
    }
  }

  function clearToken() {
    token.value = null;
    refreshTokenValue.value = null;
    user.value = null;
    clearAuthToken();
  }

  async function login(email: string, password: string): Promise<LoginResponse> {
    loading.value = true;
    error.value = null;
    try {
      const response = await authService.login({ email, password });
      // 后端返回的数据结构是 { user, tokens: { access_token, refresh_token } }
      setToken(response.tokens.access_token, response.tokens.refresh_token);
      user.value = response.user;
      return response;
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '登录失败';
      error.value = msg;
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function register(
    email: string,
    password: string,
    username?: string
  ): Promise<User> {
    loading.value = true;
    error.value = null;
    try {
      const newUser = await authService.register({
        email,
        password,
        username: username || email.split('@')[0],
      });
      return newUser;
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '注册失败';
      error.value = msg;
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function fetchUser(): Promise<User | null> {
    if (!token.value) return null;
    loading.value = true;
    try {
      const userData = await authService.getCurrentUser();
      user.value = userData;
      return userData;
    } catch (e: unknown) {
      console.error('[authStore] fetchUser failed:', e);
      return null;
    } finally {
      loading.value = false;
    }
  }

  async function logout(): Promise<void> {
    try {
      await authService.logout();
    } catch {
      // 即使后端logout失败也清除本地状态
    } finally {
      clearToken();
    }
  }

  async function refreshAccessToken(): Promise<boolean> {
    if (!refreshTokenValue.value) return false;
    try {
      const tokens = await authService.refreshToken(refreshTokenValue.value);
      setToken(tokens.access_token, tokens.refresh_token);
      return true;
    } catch {
      clearToken();
      return false;
    }
  }

  async function changePassword(
    oldPassword: string,
    newPassword: string
  ): Promise<void> {
    loading.value = true;
    try {
      await authService.changePassword(oldPassword, newPassword);
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '修改密码失败';
      error.value = msg;
      throw e;
    } finally {
      loading.value = false;
    }
  }

  async function updateProfile(data: Partial<User>): Promise<User> {
    loading.value = true;
    try {
      const updated = await authService.updateProfile(data);
      if (user.value) {
        user.value = { ...user.value, ...updated };
      }
      return updated;
    } catch (e: unknown) {
      const msg = e instanceof Error ? e.message : '更新个人信息失败';
      error.value = msg;
      throw e;
    } finally {
      loading.value = false;
    }
  }

  function $reset() {
    clearToken();
    loading.value = false;
    error.value = null;
  }

  return {
    token,
    refreshTokenValue,
    user,
    loading,
    error,
    isAuthenticated,
    isAdmin,
    setToken,
    clearToken,
    login,
    register,
    fetchUser,
    logout,
    refreshAccessToken,
    changePassword,
    updateProfile,
    $reset
  };
});
