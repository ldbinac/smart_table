/**
 * 验证码 API
 * 提供登录和注册的验证码功能
 */
import { apiClient } from "./client";

/**
 * 获取认证验证码
 * @param key 验证码标识（可选，用于区分不同场景，如 'login' 或 'register'）
 */
export function getAuthCaptcha(key: string = "default"): Promise<{
  image: string;
  expire: number;
}> {
  return apiClient.get("/auth/captcha", { key });
}

export default {
  getAuthCaptcha,
};
