export interface NumberFormatOptions {
  precision?: number;
  format?: "number" | "currency" | "percent" | "text";
  currencySymbol?: string;
  prefix?: string;
  suffix?: string;
  thousandsSeparator?: boolean;
}

/**
 * 计算数值字段的前缀文字。
 * - 货币格式：货币符号 + 可选自定义前缀
 * - 百分比格式：仅使用自定义前缀（% 作为后缀由 getNumberFieldSuffix 处理）
 * - 数字格式：仅使用自定义前缀
 */
export function getNumberFieldPrefix(options?: NumberFormatOptions): string {
  if (!options) return "";
  if (options.format === "currency") {
    return (options.currencySymbol ?? "¥") + (options.prefix ?? "");
  }
  return options.prefix ?? "";
}

/**
 * 计算数值字段的后缀文字。
 * - 百分比格式：自定义后缀 + %
 * - 其它格式：仅使用自定义后缀
 */
export function getNumberFieldSuffix(options?: NumberFormatOptions): string {
  if (!options) return "";
  if (options.format === "percent") {
    return (options.suffix ?? "") + "%";
  }
  return options.suffix ?? "";
}

/**
 * 统一的数值字段格式化函数，保证表格单元格、详情页、编辑器等展示一致。
 * 支持：小数精度、数字/货币/百分比格式、前后缀文字、千分位分隔符。
 */
export function formatNumberField(
  value: number | null | undefined,
  options?: NumberFormatOptions,
  hideAffixes = false,
): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return "";
  }

  const precision = options?.precision ?? 0;
  const format = options?.format ?? "number";
  const thousandsSeparator = options?.thousandsSeparator ?? false;

  // 文本格式：原样展示，不做数值精度、前后缀、千分位等格式化处理
  if (format === "text") {
    return String(value);
  }

  // 百分比格式：原始值按小数存储，展示时乘以 100
  let num = value;
  if (format === "percent") {
    num = value * 100;
  }

  const numStr = num.toLocaleString("zh-CN", {
    minimumFractionDigits: precision,
    maximumFractionDigits: precision,
    useGrouping: thousandsSeparator,
  });

  // 编辑态（输入框聚焦）下隐藏前缀/后缀，避免光标落在前缀前或后缀后导致无法录入
  if (hideAffixes) {
    return numStr;
  }

  return `${getNumberFieldPrefix(options)}${numStr}${getNumberFieldSuffix(options)}`;
}

/**
 * 生成 el-input-number 等数字输入框的展示态 formatter。
 *
 * 参考 element-plus 官方示例：只在“字符串层面”做千分位分组，保留用户输入的
 * 小数点与末尾 0，不通过 Number() 往返或 toLocaleString 强制精度，否则输入
 * 过程中像 “123.” 这样的中间态会被四舍五入成 “123”，导致无法输入小数。
 *
 * 前/后缀交由官方 #prefix / #suffix 插槽渲染，因此这里永远不包含前后缀。
 */
export function createNumberInputFormatter(fieldOptions?: NumberFormatOptions) {
  const useThousands = fieldOptions?.thousandsSeparator ?? false;
  const isPercent = fieldOptions?.format === "percent";
  return (value: number | string | null | undefined): string => {
    if (value === null || value === undefined || value === "") return "";
    // 数字输入框绑定的是数值，这里只做展示转换，不做二次四舍五入
    let s = String(value);
    if (isPercent) {
      const n = Number(s);
      if (!Number.isNaN(n)) {
        // 百分比按小数存储，展示时 ×100；toFixed 消除浮点噪声（如 0.505*100）
        s = String(Number((n * 100).toFixed(6)));
      }
    }
    if (useThousands) {
      const neg = s.startsWith("-");
      if (neg) s = s.slice(1);
      const [intPart, decPart] = s.split(".");
      const grouped = (intPart && intPart.length ? intPart : "0").replace(
        /\B(?=(\d{3})+(?!\d))/g,
        ",",
      );
      s = (neg ? "-" : "") + grouped + (decPart !== undefined ? "." + decPart : "");
    }
    return s;
  };
}

/**
 * 生成 el-input-number 等数字输入框的 parser。
 *
 * 关键点：必须做“字符串层面”的转换，保留用户输入的小数点/中间态。
 * el-input-number 会把 parser 的结果再次写回输入框，若用 Number() 转换，
 * 像 "1." 会变成 "1"，导致小数点被直接吞掉、后续数字错位成 "15"。
 * 参考官方示例：parser 只剥离格式化字符（千分位），不破坏原始文本。
 *
 * 百分比按小数存储，解析时 ÷100。
 * 前/后缀由官方插槽渲染，不会进入文本，因此无需在此剥离。
 */
export function createNumberInputParser(fieldOptions?: NumberFormatOptions) {
  return (value: string | number | null | undefined): string => {
    if (value === null || value === undefined || value === "") return "";
    // 仅剥离千分位分隔符，保留小数点与中间态（如 "1."）
    let s = String(value)
      .replace(/,/g, "")
      .trim();
    if (fieldOptions?.format === "percent") {
      // 百分比格式按小数存储，编辑时展示值已乘以 100，解析时需还原为小数
      const num = Number(s);
      if (Number.isNaN(num)) return "";
      return String(num / 100);
    }
    return s;
  };
}
