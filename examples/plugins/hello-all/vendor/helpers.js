/**
 * Hello Panel · 工具函数（多文件脚本注入示例）
 *
 * 本文件由 manifest.json 的 assets.scripts 声明：
 *   "assets": { "scripts": ["vendor/helpers.js"] }
 * loader 在入口 main.js **之前**以 <script src="files/vendor/helpers.js?fst=…"> 注入，
 * 因此入口可直接使用 window.HPHelpers —— 这是"包内多 JS 文件按序加载"的参考写法。
 *
 * 注意：assets.scripts 仅允许 .js 文件；第三方 CDN 脚本需在 permissions.network
 * 声明域名后于入口中动态加载（loader CSP 会放行白名单域）。
 */
(function () {
  "use strict";

  /** HTML 转义（把记录值插入 innerHTML 前使用，防注入） */
  function esc(value) {
    return String(value == null ? "" : value)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");
  }

  /** 截断长文本 */
  function truncate(text, max) {
    var s = String(text == null ? "" : text);
    return s.length > max ? s.slice(0, max - 1) + "…" : s;
  }

  /** 格式化 JSON（结果展示用） */
  function formatJson(value, indent) {
    try {
      return JSON.stringify(value, null, indent == null ? 2 : indent) || "null";
    } catch (e) {
      return String(value);
    }
  }

  /** 取记录中某字段的可读值（空值统一显示为 (空)） */
  function fieldValue(record, fieldId) {
    var values = (record && record.values) || {};
    var v = values[fieldId];
    return v === undefined || v === null || v === "" ? "(空)" : String(v);
  }

  window.HPHelpers = {
    esc: esc,
    truncate: truncate,
    formatJson: formatJson,
    fieldValue: fieldValue,
  };
})();
