/**
 * vue-i18n 实例创建与配置
 *
 * 设计要点：
 * - legacy: false  → 启用 Composition API 模式，与项目现有 setup 语法一致
 * - 资源文件通过 import.meta.glob 同步收集，Vite 会按语言 code-split
 * - 仅加载已启用语言（ENABLED_LANGUAGES）的资源，预留语言不打包
 * - 导出 i18n 实例供 main.ts 注册，同时导出便捷的 t 函数供非组件上下文使用
 */
import { createI18n } from "vue-i18n";
import type { I18n } from "vue-i18n";
import {
  FALLBACK_LOCALE,
  isSupportedLocale,
  AVAILABLE_LANGUAGES,
  ENABLED_LANGUAGES,
  type SupportedLocale,
  type LanguageOption,
} from "./types";

/**
 * 通过 import.meta.glob 收集所有已启用语言的 JSON 资源。
 * Vite 在构建时会为每种语言生成独立 chunk，实现按需加载。
 *
 * glob 模式匹配：locales/{zh-CN,en-US}/*.json
 * eager: true → 同步导入，应用启动时即可用，避免首屏闪烁
 */
const localeModules = import.meta.glob(
  ["./locales/zh-CN/*.json", "./locales/en-US/*.json"],
  { eager: true },
);

/**
 * 将收集到的模块按语言组装为 { [lang]: { [module]: {...} } } 结构。
 * 文件名作为模块 key（如 common、route、auth、settings）。
 */
function assembleMessages(): Record<string, Record<string, unknown>> {
  const messages: Record<string, Record<string, unknown>> = {};

  for (const path in localeModules) {
    // path 形如 "./locales/zh-CN/common.json"
    const match = path.match(/\.\/locales\/([^/]+)\/([^/]+)\.json$/);
    if (!match) continue;

    const lang = match[1];
    const moduleName = match[2];
    const moduleContent = (localeModules[path] as { default: Record<string, unknown> }).default;

    if (!messages[lang]) {
      messages[lang] = {};
    }
    messages[lang][moduleName] = moduleContent;
  }

  return messages;
}

const messages = assembleMessages();

/**
 * 根据浏览器/系统语言返回合适的默认语言。
 * 中文环境（zh-*）返回 zh-CN，其余语言环境返回 en-US。
 */
function getSystemLocale(): SupportedLocale {
  const navLang = (
    typeof navigator !== "undefined" ? navigator.language || "" : ""
  ).toLowerCase();
  if (navLang.startsWith("zh")) {
    return "zh-CN";
  }
  return "en-US";
}

/**
 * 从 localStorage 读取用户上次选择的语言（缓存优先）。
 * settingsStore 的存储 key 为 "smart-table-settings"，其中包含 language 字段。
 * 无缓存时按系统语言判断默认语言。
 */
function getInitialLocale(): SupportedLocale {
  try {
    const stored = localStorage.getItem("smart-table-settings");
    if (stored) {
      const parsed = JSON.parse(stored);
      if (parsed && isSupportedLocale(parsed.language)) {
        return parsed.language;
      }
    }
  } catch {
    // 读取失败时静默回退到默认语言
  }
  return getSystemLocale();
}

/** vue-i18n 实例 */
const i18n = createI18n({
  legacy: false,
  locale: getInitialLocale(),
  fallbackLocale: FALLBACK_LOCALE,
  messages: messages as Record<string, any>,
});

export default i18n;

/**
 * 全局翻译函数（非组件上下文使用，如 api/client.ts、router/guards.ts）。
 * 在组件内请使用 useI18n() 获取的 t 函数。
 */
export const t = (i18n.global as any).t as (key: string, ...args: any[]) => string;

/**
 * 按路径从当前 locale message 中读取原始值，不经过 ICU 编译。
 * 用于公式示例、正则占位符等包含字面量花括号的文本，避免触发
 * vue-i18n message compiler 的 “Unterminated/Unbalanced closing brace” 报错。
 */
export function getLiteral(key: string): string {
  const locale = i18n.global.locale.value;
  const localeMessages = i18n.global.getLocaleMessage(locale) as Record<string, unknown>;
  const parts = key.split(".");
  let current: unknown = localeMessages;
  for (const part of parts) {
    if (current && typeof current === "object" && part in current) {
      current = (current as Record<string, unknown>)[part];
    } else {
      return key;
    }
  }
  return typeof current === "string" ? current : key;
}

/**
 * 切换当前语言（供 settingsStore 调用）。
 * @param lang 目标语言代码
 */
export function setI18nLanguage(lang: SupportedLocale): void {
  i18n.global.locale.value = lang;
}

/**
 * 获取当前语言代码。
 */
export function getI18nLanguage(): SupportedLocale {
  return i18n.global.locale.value as SupportedLocale;
}

/** 导出 I18n 类型供其他模块类型标注使用 */
export type { I18n };

/** 重新导出语言相关常量与类型，便于统一从 '@/i18n' 引入 */
export {
  AVAILABLE_LANGUAGES,
  ENABLED_LANGUAGES,
};
export type { LanguageOption };
export type { SupportedLocale };
