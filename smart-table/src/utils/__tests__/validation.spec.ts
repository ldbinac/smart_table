import { describe, it, expect } from "vitest";
import type { FieldEntity } from "@/db/schema";
import { FieldType } from "@/types/fields";
import {
  validateFieldFormat,
  validateFieldsFormat,
  PRESET_REGEX_OPTIONS,
} from "../validation";

// 构造 FieldEntity 测试数据的工厂函数
function createField(overrides: Partial<FieldEntity> = {}): FieldEntity {
  return {
    id: "f1",
    tableId: "t1",
    name: "测试字段",
    type: FieldType.SINGLE_LINE_TEXT,
    options: {},
    isPrimary: false,
    isSystem: false,
    isRequired: false,
    isVisible: true,
    order: 0,
    createdAt: Date.now(),
    updatedAt: Date.now(),
    ...overrides,
  };
}

describe("validateFieldFormat - 单行文本正则校验", () => {
  it("无 regex 配置时任意值放行", () => {
    const field = createField({ options: {} });
    expect(
      validateFieldFormat("abc", FieldType.SINGLE_LINE_TEXT, field),
    ).toEqual({ valid: true });
    expect(
      validateFieldFormat("123", FieldType.SINGLE_LINE_TEXT, field),
    ).toEqual({ valid: true });
  });

  it("配置 regex 且匹配时放行", () => {
    const field = createField({ options: { regex: "^\\d{4}$" } });
    expect(
      validateFieldFormat("1234", FieldType.SINGLE_LINE_TEXT, field),
    ).toEqual({ valid: true });
  });

  it("配置 regex 不匹配时返回自定义 regexMessage", () => {
    const field = createField({
      name: "验证码",
      options: { regex: "^\\d{4}$", regexMessage: "验证码必须是4位数字" },
    });
    const result = validateFieldFormat(
      "abc",
      FieldType.SINGLE_LINE_TEXT,
      field,
    );
    expect(result.valid).toBe(false);
    expect(result.error).toBe("验证码必须是4位数字");
  });

  it("不匹配且未配置 regexMessage 时返回默认提示", () => {
    const field = createField({
      name: "验证码",
      options: { regex: "^\\d{4}$" },
    });
    const result = validateFieldFormat(
      "abc",
      FieldType.SINGLE_LINE_TEXT,
      field,
    );
    expect(result.valid).toBe(false);
    expect(result.error).toBe("验证码 格式不正确");
  });

  it("空值放行（null 与空字符串）", () => {
    const field = createField({ options: { regex: "^\\d{4}$" } });
    expect(
      validateFieldFormat(null, FieldType.SINGLE_LINE_TEXT, field),
    ).toEqual({ valid: true });
    expect(
      validateFieldFormat("", FieldType.SINGLE_LINE_TEXT, field),
    ).toEqual({ valid: true });
  });

  it("非法正则放行（valid:true）", () => {
    const field = createField({ options: { regex: "[" } });
    expect(
      validateFieldFormat("abc", FieldType.SINGLE_LINE_TEXT, field),
    ).toEqual({ valid: true });
  });
});

describe("validateFieldsFormat - 单行文本正则字段收集", () => {
  it("能收集配置了 regex 的 SINGLE_LINE_TEXT 字段错误", () => {
    const fields: FieldEntity[] = [
      createField({
        id: "f-text",
        name: "编码",
        type: FieldType.SINGLE_LINE_TEXT,
        options: { regex: "^\\d{4}$", regexMessage: "编码需为4位数字" },
      }),
      createField({
        id: "f-text-no-regex",
        name: "备注",
        type: FieldType.SINGLE_LINE_TEXT,
        options: {},
      }),
    ];
    const values = {
      "f-text": "abc",
      "f-text-no-regex": "任意内容",
    };
    const errors = validateFieldsFormat(fields, values);
    expect(errors).toHaveLength(1);
    expect(errors[0].fieldId).toBe("f-text");
    expect(errors[0].message).toBe("编码需为4位数字");
  });
});

describe("PRESET_REGEX_OPTIONS", () => {
  it("长度为 4 且各项字段齐全", () => {
    expect(PRESET_REGEX_OPTIONS).toHaveLength(4);
    for (const option of PRESET_REGEX_OPTIONS) {
      expect(typeof option.label).toBe("string");
      expect(option.label.length).toBeGreaterThan(0);
      expect(typeof option.pattern).toBe("string");
      expect(option.pattern.length).toBeGreaterThan(0);
      expect(typeof option.message).toBe("string");
      expect(option.message.length).toBeGreaterThan(0);
    }
  });
});
