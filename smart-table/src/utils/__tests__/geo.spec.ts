/**
 * 地理位置工具函数单元测试
 *
 * 覆盖 formatGeoValue / parseAddressText / parseLngLatText / geoToText / textToGeoValue / isGeoEmpty
 * 的主要业务场景：正常流程、边界条件与异常路径。
 * 这些函数为纯函数，不依赖 Vue / i18n，可独立运行。
 */
import {
  formatGeoValue,
  parseAddressText,
  parseLngLatText,
  geoToText,
  textToGeoValue,
  isGeoEmpty,
} from "@/utils/geo";
import { validateRequiredFields } from "@/utils/validation";
import { FieldType } from "@/types";
import type { GeoChinaNode } from "@/types/fields";

// 最小化的中国行政区划树（用于地址解析测试）
const chinaTree: GeoChinaNode[] = [
  {
    name: "广东省",
    children: [
      { name: "深圳市", children: [{ name: "南山区" }, { name: "福田区" }] },
      { name: "广州市", children: [{ name: "天河区" }] },
    ],
  },
  {
    name: "北京市",
    children: [{ name: "北京市", children: [{ name: "海淀区" }] }],
  },
];

describe("formatGeoValue", () => {
  it("拼接省/市/区", () => {
    expect(formatGeoValue({ province: "广东", city: "深圳", district: "南山" })).toBe("广东 / 深圳 / 南山");
  });

  it("拼接含详情", () => {
    expect(
      formatGeoValue({ province: "广东", city: "深圳", district: "南山", detail: "科技园1号" })
    ).toBe("广东 / 深圳 / 南山 / 科技园1号");
  });

  it("国家和地区格式用 region/country 拼接", () => {
    expect(formatGeoValue({ country: "中国", region: "亚洲" }, "country_region")).toBe("亚洲 / 中国");
  });

  it("经纬度优先展示坐标串", () => {
    expect(formatGeoValue({ lng: 116.4, lat: 39.9 })).toBe("116.4, 39.9");
  });

  it("仅 address 时回退原始地址", () => {
    expect(formatGeoValue({ address: "某处地址" })).toBe("某处地址");
  });

  it("null / undefined / 非对象返回空串", () => {
    expect(formatGeoValue(null)).toBe("");
    expect(formatGeoValue(undefined)).toBe("");
    expect(formatGeoValue("广东" as any)).toBe("");
  });
});

describe("parseAddressText", () => {
  it("识别省/市/区并保留剩余为详情", () => {
    const r = parseAddressText("广东省深圳市南山区科技园1号", chinaTree);
    expect(r).toMatchObject({ province: "广东省", city: "深圳市", district: "南山区" });
    expect(r.detail).toBe("科技园1号");
  });

  it("无省份信息时整段作为详情", () => {
    const r = parseAddressText("科技园1号", chinaTree);
    expect(r.province).toBeUndefined();
    expect(r.detail).toBe("科技园1号");
  });

  it("空文本或空树返回空对象", () => {
    expect(parseAddressText("", chinaTree)).toEqual({});
    expect(parseAddressText("广东省", [])).toEqual({});
  });

  it("边界：省会名被误命中（黑龙江 vs 省）不截断", () => {
    // 确保"省份"后缀匹配时选择更具体的名称
    const r = parseAddressText("黑龙江省哈尔滨市南岗区", [
      { name: "黑龙江省", children: [{ name: "哈尔滨市", children: [{ name: "南岗区" }] }] },
    ]);
    expect(r).toMatchObject({ province: "黑龙江省", city: "哈尔滨市", district: "南岗区" });
  });
});

describe("parseLngLatText", () => {
  it("逗号分隔", () => {
    expect(parseLngLatText("116.397, 39.909")).toEqual({ lng: 116.397, lat: 39.909 });
  });

  it("空格分隔", () => {
    expect(parseLngLatText("116.397 39.909")).toEqual({ lng: 116.397, lat: 39.909 });
  });

  it("带 lng:/lat: 前缀", () => {
    expect(parseLngLatText("lng:116.397 lat:39.909")).toEqual({ lng: 116.397, lat: 39.909 });
  });

  it("带中文经度/纬度前缀", () => {
    expect(parseLngLatText("经度:116.397 纬度:39.909")).toEqual({ lng: 116.397, lat: 39.909 });
  });

  it("纬度经度顺序颠倒时自动交换", () => {
    // 第一个值更像纬度（<=90），第二个像经度（>90）→ 交换
    expect(parseLngLatText("30, 120")).toEqual({ lng: 120, lat: 30 });
  });

  it("无数字返回 null", () => {
    expect(parseLngLatText("没有坐标")).toBeNull();
  });

  it("越界值返回 null", () => {
    expect(parseLngLatText("200, 100")).toBeNull(); // 经度 200 超出 [-180,180]
    expect(parseLngLatText("181, 91")).toBeNull();
  });

  it("空文本返回 null", () => {
    expect(parseLngLatText("")).toBeNull();
  });
});

describe("geoToText", () => {
  it("与 formatGeoValue 行为一致", () => {
    const v = { province: "广东", city: "深圳" };
    expect(geoToText(v)).toBe(formatGeoValue(v));
  });
});

describe("textToGeoValue", () => {
  it("country_region 整段作为 country", () => {
    expect(textToGeoValue("中国", "country_region")).toEqual({ country: "中国" });
  });

  it("lng_lat 可解析写入坐标", () => {
    expect(textToGeoValue("116.397, 39.909", "lng_lat")).toEqual({ lng: 116.397, lat: 39.909 });
  });

  it("lng_lat 无法解析时回退 address", () => {
    expect(textToGeoValue("无效坐标", "lng_lat")).toEqual({ address: "无效坐标" });
  });

  it("省/市/区格式带树可解析", () => {
    const v = textToGeoValue("广东省深圳市南山区", "province_city_district", chinaTree);
    expect(v).toMatchObject({ province: "广东省", city: "深圳市", district: "南山区" });
  });

  it("省/市/区格式无树时回退 address", () => {
    expect(textToGeoValue("广东省深圳市", "province_city_district")).toEqual({ address: "广东省深圳市" });
  });

  it("空文本返回空对象", () => {
    expect(textToGeoValue("", "province")).toEqual({});
  });
});

describe("isGeoEmpty", () => {
  it("空对象为空", () => {
    expect(isGeoEmpty({})).toBe(true);
  });

  it("有省份不为空", () => {
    expect(isGeoEmpty({ province: "广东" })).toBe(false);
  });

  it("经纬度为 0 视为有效（非空白）", () => {
    expect(isGeoEmpty({ lng: 0, lat: 0 })).toBe(false);
  });

  it("仅空 address 视为空", () => {
    expect(isGeoEmpty({ address: "" })).toBe(true);
  });

  it("null / undefined 为空", () => {
    expect(isGeoEmpty(null)).toBe(true);
    expect(isGeoEmpty(undefined)).toBe(true);
  });

  it("country/region 不为空", () => {
    expect(isGeoEmpty({ country: "中国" })).toBe(false);
  });
});

describe("validateRequiredFields 地理位置必填", () => {
  const geoField = {
    id: "f1",
    name: "地址",
    type: FieldType.GEOLOCATION,
    isRequired: true,
  } as any;

  it("空对象视为未填，拦截必填", () => {
    const r = validateRequiredFields([geoField], { f1: {} });
    expect(r.valid).toBe(false);
    expect(r.errors.length).toBe(1);
  });

  it("null 视为未填，拦截必填", () => {
    const r = validateRequiredFields([geoField], { f1: null });
    expect(r.valid).toBe(false);
  });

  it("经纬度为 0 视为已填，通过必填", () => {
    const r = validateRequiredFields([geoField], { f1: { lng: 0, lat: 0 } });
    expect(r.valid).toBe(true);
  });

  it("有省份视为已填，通过必填", () => {
    const r = validateRequiredFields([geoField], { f1: { province: "广东" } });
    expect(r.valid).toBe(true);
  });

  it("非必填地理位置即使为空也不报错", () => {
    const optional = { ...geoField, isRequired: false };
    const r = validateRequiredFields([optional], { f1: {} });
    expect(r.valid).toBe(true);
  });
});
