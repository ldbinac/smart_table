/**
 * API 客户端
 * 基于 axios 封装的 HTTP 请求客户端，统一处理请求/响应
 * 适配后端 {success, message, data} 统一响应格式
 * 增强版：支持 request_id 追踪和详细的错误日志
 * 增强版：支持401错误自动续期重试机制
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
import { useAuthStore } from "@/stores/authStore";
import devLog from "@/utils/logger";

const { baseURL, timeout } = apiConfig;

// 待重试的请求队列
interface PendingRequest {
  config: InternalAxiosRequestConfig;
  resolve: (value: AxiosResponse) => void;
  reject: (error: unknown) => void;
}

let pendingRequests: PendingRequest[] = [];
let isRefreshing = false;

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
    const token = getToken();

    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
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

      // 处理错误情况（增强版）
      const errorData = data as {
        success: boolean;
        message: string;
        code?: number;
        error?: string;
        details?: Array<{ field: string; message: string }>;
        request_id?: string;
      };
      const code = errorData.code || response.status;
      const requestId = errorData.request_id;

      // 记录详细错误日志（开发环境）
      devLog.apiError({
        requestId,
        url: response.config.url,
        method: response.config.method?.toUpperCase(),
        status: code,
        message: errorData.message,
      });

      if (code === 401) {
        // 分享接口的 401 不跳转登录页（无效 token 是业务错误，不是认证失败）
        const skipRedirect = (response.config as any)?.skipAuthRedirect;
        if (skipRedirect) {
          return Promise.reject(
            Object.assign(new Error(errorData.message || "Unauthorized"), {
              requestId,
              code: 401,
              response,
            })
          );
        }

        // 将当前请求加入队列等待重试，并返回一个 Promise 供拦截器使用
        return new Promise<AxiosResponse>((resolve, reject) => {
          pendingRequests.push({
            config: response.config,
            resolve,
            reject
          });

          // 如果正在续期,只需加入队列等待统一重试
          if (isRefreshing) {
            devLog.debug('[API] 正在续期,将请求加入队列');
            return;
          }

          // 尝试续期
          isRefreshing = true;
          const authStore = useAuthStore();

          devLog.info('[API] Token已过期,触发续期');

          authStore.refreshAccessToken()
            .then((success) => {
              if (success) {
                devLog.info('[API] Token续期成功,重试待处理的请求');

                // 重试所有待重试的请求（包括当前请求）
                const queuedRequests = pendingRequests;
                pendingRequests = [];

                queuedRequests.forEach(({ config, resolve, reject }) => {
                  // 清除旧的Authorization header，让拦截器重新添加新token
                  if (config.headers) {
                    delete config.headers.Authorization;
                  }

                  instance.request(config)
                    .then(resolve)
                    .catch(reject);
                });
              } else {
                devLog.error('[API] Token续期失败,跳转登录页');
                // 续期失败,清除状态并跳转登录页
                clearToken();
                router.push("/login");
                ElMessage.error("登录已过期，请重新登录");
                // 拒绝所有待重试的请求
                pendingRequests.forEach(({ reject }) => {
                  reject(new Error('Token refresh failed'));
                });
                pendingRequests = [];
              }
            })
            .catch((err) => {
              devLog.error('[API] Token续期异常:', err);
              clearToken();
              router.push("/login");
              ElMessage.error("登录已过期，请重新登录");
              // 拒绝所有待重试的请求
              pendingRequests.forEach(({ reject }) => {
                reject(err);
              });
              pendingRequests = [];
            })
            .finally(() => {
              isRefreshing = false;
            });
        });
      }

      if (code === 403) {
        // 分享接口的 403 不跳转登录页
        const skipRedirect = (response.config as any)?.skipAuthRedirect;
        if (skipRedirect) {
          return Promise.reject(
            Object.assign(new Error(errorData.message || "Forbidden"), {
              requestId,
              code: 403,
              response,
            })
          );
        }
        // 检查是否是认证令牌相关的错误
        const isAuthError = 
          errorData.error?.toLowerCase().includes('token') ||
          errorData.error?.toLowerCase().includes('auth') ||
          errorData.message?.toLowerCase().includes('token') ||
          errorData.message?.toLowerCase().includes('认证') ||
          errorData.message?.toLowerCase().includes('无效');
        
        if (isAuthError) {
          // 清除 token 并跳转登录页
          clearToken();
          router.push("/login");
          ElMessage.error(errorData.message || "认证令牌无效，请重新登录");
          return Promise.reject(
            Object.assign(new Error("Forbidden - Invalid Token"), { 
              requestId,
              code: 403 
            })
          );
        }
        
        // 普通权限不足错误
        ElMessage.error(errorData.message || "没有操作权限");
        return Promise.reject(
          Object.assign(new Error("Forbidden"), { 
            requestId,
            code: 403 
          })
        );
      }

      if (code === 404) {
        console.warn("[API] 资源不存在:", response.config.url);
        return Promise.reject(
          Object.assign(new Error("Not Found"), { 
            requestId,
            code: 404 
          })
        );
      }

      const msg = errorData.message || "请求失败";
      ElMessage.error(msg);
      return Promise.reject(
        Object.assign(new Error(msg), { 
          requestId,
          code,
          error: errorData.error,
          details: errorData.details 
        })
      );
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
      | { 
          success?: boolean; 
          message?: string; 
          code?: number;
          error?: string;
          details?: Array<{ field: string; message: string }>;
          request_id?: string;
        }
      | undefined;

    const requestId = data?.request_id;

    // 记录详细错误日志（开发环境）
    devLog.apiError({
      requestId,
      url: error.config?.url,
      method: error.config?.method?.toUpperCase(),
      status,
      message: data?.message || error.message,
      stack: error.stack
    });

    // 优先使用后端返回的消息
    const backendMessage = data?.message;

    switch (status) {
      case 400:
        ElMessage.error(backendMessage || "请求参数错误");
        break;
      case 401:
        {
          // 分享接口的 401 不跳转登录页
          const skipRedirect = (error.config as any)?.skipAuthRedirect;
          if (skipRedirect) {
            // 不弹 ElMessage，由组件自行处理错误
            break;
          }

          // 将当前请求加入队列等待重试，并返回一个 Promise 供拦截器使用
          return new Promise<AxiosResponse>((resolve, reject) => {
            pendingRequests.push({
              config: error.config!,
              resolve,
              reject
            });

            // 如果正在续期,只需加入队列等待统一重试
            if (isRefreshing) {
              devLog.debug('[API] 正在续期,将请求加入队列');
              return;
            }

            // 尝试续期
            isRefreshing = true;
            const authStore = useAuthStore();

            devLog.info('[API] Token已过期,触发续期');

            authStore.refreshAccessToken()
              .then((success) => {
                if (success) {
                  devLog.info('[API] Token续期成功,重试待处理的请求');
                  devLog.info(`[API] 队列中有${pendingRequests.length}个请求需要重试`);

                  // 获取新token
                  const newToken = getToken();
                  devLog.info('[API] 新token:', newToken ? '已获取' : '获取失败');

                  // 重试所有待重试的请求（包括当前请求）
                  const queuedRequests = pendingRequests;
                  pendingRequests = [];

                  queuedRequests.forEach(({ config, resolve, reject }, index) => {
                    devLog.debug(`[API] 重试第${index + 1}个请求:`, config.url);

                    // 清除旧的Authorization header，让拦截器重新添加新token
                    if (config.headers) {
                      delete config.headers.Authorization;
                      devLog.debug('[API] 已清除旧的Authorization header');
                    }

                    instance.request(config)
                      .then(resolve)
                      .catch(reject);
                  });
                  devLog.info('[API] 队列已清空');
                } else {
                  devLog.error('[API] Token续期失败,跳转登录页');
                  // 续期失败,清除状态并跳转登录页
                  clearToken();
                  router.push("/login");
                  ElMessage.error("登录已过期，请重新登录");
                  // 拒绝所有待重试的请求
                  pendingRequests.forEach(({ reject }) => {
                    reject(new Error('Token refresh failed'));
                  });
                  pendingRequests = [];
                }
              })
              .catch((err) => {
                devLog.error('[API] Token续期异常:', err);
                clearToken();
                router.push("/login");
                ElMessage.error("登录已过期，请重新登录");
                // 拒绝所有待重试的请求
                pendingRequests.forEach(({ reject }) => {
                  reject(err);
                });
                pendingRequests = [];
              })
              .finally(() => {
                isRefreshing = false;
              });
          });
        }
        break;
      case 403:
        {
          // 分享接口的 403 不跳转登录页
          const skipRedirect = (error.config as any)?.skipAuthRedirect;
          if (skipRedirect) {
            break;
          }
          // 检查是否是认证令牌相关的错误
          const isAuthErrorFor403 = 
            data?.error?.toLowerCase().includes('token') ||
            data?.error?.toLowerCase().includes('auth') ||
            backendMessage?.toLowerCase().includes('token') ||
            backendMessage?.toLowerCase().includes('认证') ||
            backendMessage?.toLowerCase().includes('无效');
          
          if (isAuthErrorFor403) {
            // 清除 token 并跳转登录页
            clearToken();
            router.push("/login");
            ElMessage.error(backendMessage || "认证令牌无效，请重新登录");
          } else {
            // 普通权限不足错误
            ElMessage.error(backendMessage || "没有操作权限");
          }
        }
        break;
      case 404:
        ElMessage.error(backendMessage || "请求的资源不存在");
        break;
      case 422:
        // 处理验证错误，显示详细的字段错误信息
        const validationErrorData = error.response.data as {
          message?: string;
          details?: Array<{ field: string; message: string }>;
          request_id?: string;
        };
        if (validationErrorData.details && validationErrorData.details.length > 0) {
          // 显示所有字段的验证错误
          const errorMessages = validationErrorData.details.map(
            (detail) => detail.message
          );
          ElMessage.error(errorMessages.join('\n'));
        } else {
          ElMessage.error(backendMessage || "数据验证失败");
        }
        break;
      case 429:
        {
          const skipRedirect = (error.config as any)?.skipAuthRedirect;
          if (!skipRedirect) {
            ElMessage.error(backendMessage || "请求过于频繁，请稍后再试");
          }
        }
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

    return Promise.reject(
      Object.assign(error, { 
        requestId,
        error: data?.error,
        details: data?.details 
      })
    );
  },
);

export interface ErrorDetail {
  field?: string;
  message: string;
  code?: string;
}

export interface ApiResponse<T> {
  success: boolean;
  message: string;
  data: T;
  code?: number;
  error?: string;
  details?: ErrorDetail[];
  request_id?: string;
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
