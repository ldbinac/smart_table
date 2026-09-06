/**
 * 地理位置字段工具函数
 * 负责单元格值的格式化展示、地址文本解析（粘贴自动识别）、经纬度解析与导入导出互转。
 */
import type { GeoValue, GeoFormat, GeoChinaNode } from "@/types/fields";

const ADMIN_SUFFIXES = ["特别行政区", "自治区", "省", "市", "区", "县", "自治州", "盟", "地区"];

/** 去除常见行政区划后缀，用于模糊匹配 */
function stripSuffix(name: string): string {
  let n = name;
  for (const s of ADMIN_SUFFIXES) {
    if (n.endsWith(s) && n.length > s.length) {
      n = n.slice(0, -s.length);
    }
  }
  return n;
}

/** 判断一段文本中是否包含某行政区划名称（双向去后缀匹配） */
function textContainsName(text: string, name: string): boolean {
  if (!text || !name) return false;
  if (text.includes(name)) return true;
  const a = stripSuffix(name);
  if (a && text.includes(a)) return true;
  const b = stripSuffix(text);
  if (b && name.includes(b)) return true;
  return false;
}

/** 在两个候选中选择更具体的匹配（名称更长） */
function bestMatch(text: string, names: string[]): string | null {
  let best = null as string | null;
  let bestLen = 0;
  for (const name of names) {
    if (textContainsName(text, name) && name.length > bestLen) {
      best = name;
      bestLen = name.length;
    }
  }
  return best;
}

/** 根据子格式将地理位置值格式化为展示文本 */
export function formatGeoValue(
  value: GeoValue | null | undefined,
  format?: GeoFormat
): string {
  if (!value || typeof value !== "object") return "";

  // 经纬度优先：lng_lat / map_picker 直接展示坐标
  if ((value.lng !== undefined || value.lat !== undefined) && (value.lng || value.lat)) {
    return `${value.lng ?? ""}, ${value.lat ?? ""}`;
  }

  if (format === "country_region") {
    const parts = [value.region, value.country].filter(Boolean);
    return parts.join(" / ");
  }

  const parts: string[] = [];
  if (value.province) parts.push(value.province);
  if (value.city) parts.push(value.city);
  if (value.district) parts.push(value.district);
  if (value.detail) parts.push(value.detail);
  if (parts.length) return parts.join(" / ");

  if (value.address) return value.address;
  return "";
}

/**
 * 解析粘贴的地址文本，基于中国行政区划树做省/市/区最长匹配。
 * 无法识别的剩余部分归入 detail。
 */
export function parseAddressText(
  text: string,
  tree: GeoChinaNode[]
): Partial<GeoValue> {
  const result: Partial<GeoValue> = {};
  if (!text || !tree?.length) return result;

  // 1) 匹配省份（最长匹配，避免「黑龙江省」被「省」误命中）
  const provinceNames = tree.map((p) => p.name);
  const provinceName = bestMatch(text, provinceNames);
  if (!provinceName) {
    // 无省份信息：整段作为 detail
    result.detail = text.trim();
    return result;
  }
  result.province = provinceName;

  const provinceNode = tree.find((p) => p.name === provinceName);
  let rest = text.replace(provinceName, "");
  rest = stripSuffix(provinceName) ? rest.replace(stripSuffix(provinceName), "") : rest;

  // 2) 匹配城市
  const cityNames = (provinceNode?.children || []).map((c) => c.name);
  const cityName = bestMatch(rest, cityNames);
  if (cityName) {
    result.city = cityName;
    rest = rest.replace(cityName, "");
    rest = stripSuffix(cityName) ? rest.replace(stripSuffix(cityName), "") : rest;
    const cityNode = provinceNode?.children?.find((c) => c.name === cityName);
    const districtNames = (cityNode?.children || []).map((d) => d.name);
    const districtName = bestMatch(rest, districtNames);
    if (districtName) {
      result.district = districtName;
      rest = rest.replace(districtName, "");
    }
  }

  const detail = rest.replace(/[/\\\-—\s]+/g, " ").trim();
  if (detail) result.detail = detail;
  return result;
}

/**
 * 解析粘贴的经纬度文本，支持多种常见写法：
 * - "116.397, 39.909"
 * - "116.397 39.909"
 * - "经度: 116.397 纬度: 39.909"
 * - "lng:116.397 lat:39.909"
 * 返回 {lng, lat}；无法解析返回 null。
 */
export function parseLngLatText(text: string): { lng: number; lat: number } | null {
  if (!text) return null;
  const cleaned = text.trim();

  // 提取所有数字（含小数与负号）
  const numbers = cleaned.match(/-?\d+(?:\.\d+)?/g);
  if (numbers && numbers.length >= 2) {
    const a = parseFloat(numbers[0]);
    const b = parseFloat(numbers[1]);
    if (Number.isFinite(a) && Number.isFinite(b)) {
      // 约定：经度在前（范围 -180~180），纬度在后（-90~90）
      let lng = a;
      let lat = b;
      if (Math.abs(a) <= 90 && Math.abs(b) > 90) {
        // 第一个更像纬度，交换
        lng = b;
        lat = a;
      }
      if (lng >= -180 && lng <= 180 && lat >= -90 && lat <= 90) {
        return { lng, lat };
      }
    }
  }
  return null;
}

/** 导出：地理位置值转文本 */
export function geoToText(value: GeoValue | null | undefined, format?: GeoFormat): string {
  return formatGeoValue(value, format);
}

/**
 * 导入：文本转地理位置值。
 * - country_region：整段作为 country（best-effort）
 * - lng_lat / map_picker：尝试解析经纬度
 * - 其他子格式：尝试解析省/市/区，失败则作为 address 兜底
 */
export function textToGeoValue(text: string, format?: GeoFormat, tree?: GeoChinaNode[]): GeoValue {
  const value: GeoValue = {};
  if (!text) return value;

  if (format === "country_region") {
    value.country = text.trim();
    return value;
  }

  if (format === "lng_lat" || format === "map_picker") {
    const ll = parseLngLatText(text);
    if (ll) {
      value.lng = ll.lng;
      value.lat = ll.lat;
      return value;
    }
    value.address = text.trim();
    return value;
  }

  if (tree?.length) {
    const parsed = parseAddressText(text, tree);
    if (parsed.province || parsed.city || parsed.district || parsed.detail) {
      return parsed as GeoValue;
    }
  }
  value.address = text.trim();
  return value;
}

/** 判断地理位置值是否为空 */
export function isGeoEmpty(value: GeoValue | null | undefined): boolean {
  if (!value || typeof value !== "object") return true;
  return !(
    value.province ||
    value.city ||
    value.district ||
    value.detail ||
    value.country ||
    value.region ||
    value.address ||
    (value.lng !== undefined && value.lng !== null) ||
    (value.lat !== undefined && value.lat !== null)
  );
}
