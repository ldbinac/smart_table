/**
 * i18n 类型定义与语言常量
 */

/** 系统支持的语言（含预留） */
export type SupportedLocale = "zh-CN" | "en-US" | "ja-JP" | "zh-TW";

/** 语言选项接口（UI 下拉/遍历用） */
export interface LanguageOption {
  /** 显示名称（以该语言自身书写） */
  label: string;
  /** 语言代码（BCP 47） */
  value: SupportedLocale;
  /** 国旗 emoji 或代号 */
  flag: string;
}

/**
 * 当前已启用并填充了翻译资源的语言。
 * 未填充资源的语言（ja-JP / zh-TW）暂不启用，避免用户切换后出现空白。
 * 后续填充翻译文件后，将其加入此数组即可在 UI 中显示。
 */
export const ENABLED_LANGUAGES: SupportedLocale[] = ["zh-CN", "en-US"];

/**
 * 可用语言列表（仅包含已启用语言），供 Settings.vue 等界面遍历。
 * 预留语言准备好翻译后只需加入 ENABLED_LANGUAGES 即自动出现。
 */
export const AVAILABLE_LANGUAGES: LanguageOption[] = [
  { label: "简体中文", value: "zh-CN", flag: "🇨🇳" },
  { label: "English", value: "en-US", flag: "🇺🇸" },
  // 预留语言（填充翻译资源后取消注释并加入 ENABLED_LANGUAGES）：
  // { label: "日本語", value: "ja-JP", flag: "🇯🇵" },
  // { label: "繁體中文", value: "zh-TW", flag: "🇭🇰" },
];

/** 默认语言 */
export const DEFAULT_LOCALE: SupportedLocale = "zh-CN";

/** 回退语言 */
export const FALLBACK_LOCALE: SupportedLocale = "zh-CN";

/**
 * 判断给定值是否为受支持的语言代码。
 * 用于从 localStorage / URL 参数等外部来源做类型守卫。
 */
export function isSupportedLocale(value: unknown): value is SupportedLocale {
  return (
    typeof value === "string" &&
    ["zh-CN", "en-US", "ja-JP", "zh-TW"].includes(value)
  );
}
