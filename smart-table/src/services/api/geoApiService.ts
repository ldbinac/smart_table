/**
 * 地理位置数据 API 服务
 * 提供地图配置、中国行政区划、国家和地区数据的获取，并带内存 + 会话缓存。
 */
import { apiClient } from "@/api/client";
import type { GeoChinaNode, GeoRegionItem } from "@/types/fields";

export interface GeoMapConfig {
  provider: string;
  apiBase: string;
  key: string;
  enabled: boolean;
}

/** IP 定位返回结果（基于客户端 IP 的近似位置） */
export interface GeoLocateResult {
  enabled: boolean;
  lng?: number;
  lat?: number;
  address?: string;
  source?: string;
}

const CHINA_ZH_KEY = "smarttable:geo:china:zh";
const CHINA_EN_KEY = "smarttable:geo:china:en";
const REGION_ZH_KEY = "smarttable:geo:regions:zh";
const REGION_EN_KEY = "smarttable:geo:regions:en";

// 模块级单例 Promise 缓存（避免并发重复请求）
let chinaZhPromise: Promise<GeoChinaNode[]> | null = null;
let chinaEnPromise: Promise<GeoChinaNode[]> | null = null;
let regionZhPromise: Promise<GeoRegionItem[]> | null = null;
let regionEnPromise: Promise<GeoRegionItem[]> | null = null;
let configPromise: Promise<GeoMapConfig> | null = null;

function readSession<T>(key: string): T | null {
  try {
    const raw = sessionStorage.getItem(key);
    return raw ? (JSON.parse(raw) as T) : null;
  } catch {
    return null;
  }
}

function writeSession(key: string, value: unknown): void {
  try {
    sessionStorage.setItem(key, JSON.stringify(value));
  } catch {
    /* 忽略写入失败 */
  }
}

/** 获取地图服务配置（含天地图 Key） */
export const getGeoConfig = (): Promise<GeoMapConfig> => {
  if (!configPromise) {
    configPromise = apiClient.get<GeoMapConfig>("/geo/config");
  }
  return configPromise;
};

/** 基于客户端 IP 的近似定位（地图自动居中用） */
export const getGeoLocate = (): Promise<GeoLocateResult> => {
  return apiClient.get<GeoLocateResult>("/geo/locate");
};

/** 获取中国省/市/区三级数据（按语言返回对应数据） */
export const getChinaLocations = (
  level?: "province" | "city" | "district",
  lang: "zh" | "en" = "zh"
): Promise<GeoChinaNode[]> => {
  const cacheKey = lang === "en" ? CHINA_EN_KEY : CHINA_ZH_KEY;
  const ref = lang === "en" ? "chinaEn" : "chinaZh";
  if (ref === "chinaEn" && !chinaEnPromise) {
    const cached = readSession<GeoChinaNode[]>(cacheKey);
    chinaEnPromise = cached
      ? Promise.resolve(cached)
      : apiClient
        .get<GeoChinaNode[]>("/geo/china-locations", { params: { level, lang } })
        .then((data) => {
          writeSession(cacheKey, data);
          return data;
        });
  } else if (ref === "chinaZh" && !chinaZhPromise) {
    const cached = readSession<GeoChinaNode[]>(cacheKey);
    chinaZhPromise = cached
      ? Promise.resolve(cached)
      : apiClient
        .get<GeoChinaNode[]>("/geo/china-locations", { params: { level, lang } })
        .then((data) => {
          writeSession(cacheKey, data);
          return data;
        });
  }
  return ref === "chinaEn" ? chinaEnPromise! : chinaZhPromise!;
};

/** 获取国家和地区数据（按大洲分组） */
export const getRegions = (lang: "zh" | "en" = "zh"): Promise<GeoRegionItem[]> => {
  const cacheKey = lang === "en" ? REGION_EN_KEY : REGION_ZH_KEY;
  const promiseRef = lang === "en" ? "regionEn" : "regionZh";
  if (promiseRef === "regionEn" && !regionEnPromise) {
    const cached = readSession<GeoRegionItem[]>(cacheKey);
    regionEnPromise = cached
      ? Promise.resolve(cached)
      : apiClient
        .get<GeoRegionItem[]>("/geo/regions", { params: { lang } })
        .then((data) => {
          writeSession(cacheKey, data);
          return data;
        });
  } else if (promiseRef === "regionZh" && !regionZhPromise) {
    const cached = readSession<GeoRegionItem[]>(cacheKey);
    regionZhPromise = cached
      ? Promise.resolve(cached)
      : apiClient
        .get<GeoRegionItem[]>("/geo/regions", { params: { lang } })
        .then((data) => {
          writeSession(cacheKey, data);
          return data;
        });
  }
  return promiseRef === "regionEn" ? regionEnPromise! : regionZhPromise!;
};

/** 清除地理位置数据缓存（用于数据更新或登录态切换） */
export const clearGeoCache = (): void => {
  chinaZhPromise = null;
  chinaEnPromise = null;
  regionZhPromise = null;
  regionEnPromise = null;
  configPromise = null;
  try {
    sessionStorage.removeItem(CHINA_ZH_KEY);
    sessionStorage.removeItem(CHINA_EN_KEY);
    sessionStorage.removeItem(REGION_ZH_KEY);
    sessionStorage.removeItem(REGION_EN_KEY);
  } catch {
    /* 忽略 */
  }
};
