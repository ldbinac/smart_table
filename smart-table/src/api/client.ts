/**
 * API 客户端
 * 基于 axios 封装的 HTTP 请求客户端，统一处理请求/响应
 * 适配后端 {success, message, data} 统一响应格式
 */
import axios, {
  type AxiosInstance,
  type InternalAxiosRequestConfig,
  type AxiosResponse,
  type AxiosError,
} from "axios";
import { ElMessage } from "element-plus";
import router from "@/router";
import { apiConfig } from "./config";
import { getToken, clearToken } from "@/utils/auth/token";

const { baseURL, timeout } = apiConfig;

const instance: AxiosInstance = axios.create({
  baseURL,
  timeout,
  headers: {
    "Content-Type": "application/json",
  },
  withCredentials: true, // 允许发送凭证（cookies、授权头等）
});

instance.interceptors.request.use(
  (config: InternalAxiosRequestConfig) => {
    // 使用 getToken 工具函数，同时支持 localStorage 和 sessionStorage
    const token = getToken();
    console.log(`[API 拦截器] 请求 URL: ${config.url}`);
    console.log(`[API 拦截器] Token 存在：${!!token}`);
    console.log(
      `[API 拦截器] Token 前缀：${token ? token.substring(0, 20) : "N/A"}...`,
    );
    console.log(`[API 拦截器] Headers 初始：`, config.headers);

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
      console.log(
        `[API 拦截器] 设置 Authorization 头后的 headers:`,
        config.headers,
      );
      console.log(
        `[API] 发送请求 ${config.method?.toUpperCase()} ${config.url}，Token: ${token.substring(0, 20)}...`,
      );
    } else {
      console.warn(
        `[API] 发送请求 ${config.method?.toUpperCase()} ${config.url}，但 Token 不存在！`,
      );
    }
    return config;
  },
  (error: AxiosError) => {
    return Promise.reject(error);
  },
);

instance.interceptors.response.use(
  (response: AxiosResponse) => {
    const data = response.data as ApiResponse<unknown>;

    // 适配后端 {success, message, data} 统一响应格式
    if (typeof data === "object" && data !== null && "success" in data) {
      const success = data.success as boolean;

      if (success) {
        return response;
      }

      // 处理错误情况
      const errorData = data as {
        success: boolean;
        message: string;
        code?: number;
        error?: string;
      };
      const code = errorData.code || response.status;

      if (code === 401) {
        // 清除 token 并跳转登录页
        clearToken();
        router.push("/login");
        ElMessage.error("登录已过期，请重新登录");
        return Promise.reject(new Error("Unauthorized"));
      }

      if (code === 403) {
        ElMessage.error("没有操作权限");
        return Promise.reject(new Error("Forbidden"));
      }

      if (code === 404) {
        console.warn("[API] 资源不存在:", response.config.url);
        return Promise.reject(new Error("Not Found"));
      }

      const msg = errorData.message || "请求失败";
      ElMessage.error(msg);
      return Promise.reject(new Error(msg));
    }

    return response;
  },
  (error: AxiosError) => {
    if (!error.response) {
      ElMessage.error("网络连接失败，请检查网络设置");
      return Promise.reject(error);
    }

    const status = error.response.status;
    const data = error.response.data as
      | { success?: boolean; message?: string; code?: number }
      | undefined;

    // 优先使用后端返回的消息
    const backendMessage = data?.message;

    switch (status) {
      case 400:
        ElMessage.error(backendMessage || "请求参数错误");
        break;
      case 401:
        // 清除 token 并跳转登录页
        clearToken();
        router.push("/login");
        ElMessage.error(backendMessage || "登录已过期，请重新登录");
        break;
      case 403:
        ElMessage.error(backendMessage || "没有操作权限");
        break;
      case 404:
        ElMessage.error(backendMessage || "请求的资源不存在");
        break;
      case 422:
        ElMessage.error(backendMessage || "数据验证失败");
        break;
      case 429:
        ElMessage.error(backendMessage || "请求过于频繁，请稍后再试");
        break;
      case 500:
        ElMessage.error(backendMessage || "服务器内部错误");
        break;
      case 502:
      case 503:
      case 504:
        ElMessage.error(backendMessage || "服务暂时不可用，请稍后再试");
        break;
      default:
        ElMessage.error(backendMessage || `请求失败 (${status})`);
    }

    return Promise.reject(error);
  },
);

export interface ApiResponse<T> {
  success: boolean;
  message: string;
  data: T;
  code?: number;
  error?: string;
}

export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  per_page: number;
  total_pages: number;
}

export const apiClient = {
  get<T>(
    url: string,
    params?: Record<string, unknown>,
    config?: Record<string, unknown>,
  ): Promise<T> {
    return instance.get(url, { params, ...config }).then((res) => {
      const d = res.data as ApiResponse<T> & { meta?: unknown };

      if (typeof d !== "object" || d === null || !("data" in d)) {
        return res.data as T;
      }

      // 如果响应包含 meta 字段，说明是分页列表接口，返回整个对象（包含 data 和 meta）
      if ("meta" in d && d.meta !== undefined) {
        return d as unknown as T;
      }

      // 否则只返回 data 字段
      return d.data as T;
    });
  },

  post<T>(
    url: string,
    data?: unknown,
    config?: Record<string, unknown>,
  ): Promise<T> {
    return instance.post(url, data, config).then((res) => {
      const d = res.data as ApiResponse<T>;
      return typeof d === "object" && d !== null && "data" in d
        ? d.data
        : res.data;
    });
  },

  put<T>(
    url: string,
    data?: unknown,
    config?: Record<string, unknown>,
  ): Promise<T> {
    return instance.put(url, data, config).then((res) => {
      const d = res.data as ApiResponse<T>;
      return typeof d === "object" && d !== null && "data" in d
        ? d.data
        : res.data;
    });
  },

  patch<T>(
    url: string,
    data?: unknown,
    config?: Record<string, unknown>,
  ): Promise<T> {
    return instance.patch(url, data, config).then((res) => {
      const d = res.data as ApiResponse<T>;
      return typeof d === "object" && d !== null && "data" in d
        ? d.data
        : res.data;
    });
  },

  delete<T>(url: string, config?: Record<string, unknown>): Promise<T> {
    return instance.delete(url, config).then((res) => {
      const d = res.data as ApiResponse<T>;
      return typeof d === "object" && d !== null && "data" in d
        ? d.data
        : res.data;
    });
  },

  upload(
    url: string,
    formData: FormData,
    onProgress?: (percent: number) => void,
  ): Promise<unknown> {
    return instance
      .post(url, formData, {
        headers: { "Content-Type": "multipart/form-data" },
        onUploadProgress: (e) => {
          if (e.total && onProgress) {
            onProgress(Math.round((e.loaded * 100) / e.total));
          }
        },
      })
      .then((res) => {
        const d = res.data as ApiResponse<unknown>;
        return typeof d === "object" && d !== null && "data" in d
          ? d.data
          : res.data;
      });
  },

  raw() {
    return instance;
  },
};

export default apiClient;
