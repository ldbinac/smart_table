/**
 * 认证状态管理 Store 统一入口
 * 实际实现位于 @/stores/auth/authStore，此处仅做转发，
 * 避免项目中同时存在两个 id 为 'auth' 的 Pinia store 定义导致状态冲突。
 */

export { useAuthStore } from './auth/authStore';
