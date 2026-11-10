/**
 * 接口错误信息提取工具
 *
 * 后端业务失败响应形如：
 *   { "code": 403, "message": "无权修改该记录", "success": false }
 * apiClient 拦截器会把该 message 写入 Error.message（并保留 response），
 * 但业务码失败、HTTP 错误、网络异常等路径的错误形态不完全一致。
 * 这里统一提取可展示的业务失败原因，缺失时回退到调用方的本地化文案。
 */

type ApiErrorLike = {
  message?: unknown;
  response?: { data?: { message?: unknown } };
  data?: { message?: unknown };
};

/** axios 自身生成的状态码描述不是业务原因，不应直接展示给用户 */
const GENERIC_HTTP_MESSAGE = /^(request failed with status code \d+|forbidden|unauthorized)$/i;

function normalizeMessage(value: unknown): string | null {
  if (typeof value !== "string") return null;
  const message = value.trim();
  if (!message || GENERIC_HTTP_MESSAGE.test(message)) return null;
  return message;
}

/**
 * 提取接口返回的失败原因。
 *
 * @param error 捕获到的异常（任意形态）
 * @param fallback 无法取到 message 时的兜底文案，通常为 t("view.xxxFailed")
 */
export function getApiErrorMessage(error: unknown, fallback: string): string {
  if (!error || typeof error !== "object") return fallback;

  const err = error as ApiErrorLike;
  return (
    normalizeMessage(err.response?.data?.message) ??
    normalizeMessage(err.data?.message) ??
    normalizeMessage(err.message) ??
    fallback
  );
}
