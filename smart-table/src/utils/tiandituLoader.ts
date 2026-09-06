/**
 * 天地图（Tianditu）JavaScript API 加载器
 *
 * 采用运行时动态注入 <script> 的方式加载天地图 JS API v4.0，
 * 全局仅注入一次（单例 Promise）。API Key 由后端 /api/geo/config 下发，
 * 不硬编码在前端构建产物中。
 */
import { getGeoConfig } from "@/services/api";

let loadPromise: Promise<typeof window.T> | null = null;
let mapEnabled = false;

declare global {
  interface Window {
    T: any;
    __tiandituLoadStart__?: boolean;
  }
}

/**
 * 加载天地图 JS API，返回全局 T 对象。
 * 若地图未启用（未配置 Key）则 reject。
 *
 * @param lang 语言：zh（默认，中文 UI）/ en（英文 UI）；通过天地图脚本 URL 的
 *             &lang=en 参数生效，使地图控件、版权、比例尺及搜索结果标签本地化。
 */
export function loadTianditu(lang?: "zh" | "en"): Promise<typeof window.T> {
  // 已加载
  if (window.T && typeof window.T.Map === "function") {
    return Promise.resolve(window.T);
  }
  if (loadPromise) return loadPromise;

  loadPromise = (async () => {
    const config = await getGeoConfig();
    if (!config.enabled || !config.key) {
      mapEnabled = false;
      throw new Error("TIANDITU_KEY_NOT_CONFIGURED");
    }
    mapEnabled = true;

    const base = config.apiBase || "https://api.tianditu.gov.cn";
    const langParam = lang === "en" ? "&lang=en" : "";
    const url = `${base}/api?v=4.0&tk=${encodeURIComponent(config.key)}${langParam}`;

    return new Promise<typeof window.T>((resolve, reject) => {
      const script = document.createElement("script");
      script.type = "text/javascript";
      script.src = url;
      script.onload = () => {
        if (window.T && typeof window.T.Map === "function") {
          resolve(window.T);
        } else {
          reject(new Error("TIANDITU_API_INVALID"));
        }
      };
      script.onerror = () => {
        loadPromise = null;
        reject(new Error("TIANDITU_LOAD_FAILED"));
      };
      document.head.appendChild(script);
    });
  })();

  return loadPromise;
}

/** 地图服务是否已启用（已成功加载或后端已下发 Key） */
export function isMapEnabled(): boolean {
  return mapEnabled;
}
