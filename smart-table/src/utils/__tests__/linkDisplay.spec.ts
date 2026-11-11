/**
 * Issue #IKUAYB 评论问题回归测试：
 * 水果表反向关联字段显示「关联 1 条」、弹窗显示裸 UUID。
 *
 * 对应修复：表格视图/选择器统一使用本模块合并 outbound + inbound 的显示值，
 * 并过滤后端用记录 ID 充当 display_value 的兜底数据。
 */
import { describe, it, expect } from "vitest";
import {
  buildLinkDisplayMap,
  collectLinkDisplayRecords,
  formatLinkCellValue,
  isRawRecordIdDisplay,
} from "@/utils/linkDisplay";

const fieldId = "f-inverse";
const otherFieldId = "f-forward";
const appleId = "a874fc42-c70b-45dd-93a6-cc61652f9b01";
const bananaId = "09d11dcd-8b39-4eaf-bfc0-1234567890ab";

describe("collectLinkDisplayRecords", () => {
  it("反向双向关联只有 inbound 时也能取到显示名", () => {
    const links = {
      outbound: [],
      inbound: [
        {
          field_id: fieldId,
          linked_records: [{ record_id: appleId, display_value: "2026-1" }],
        },
      ],
    };

    expect(collectLinkDisplayRecords(links, fieldId)).toEqual([
      { record_id: appleId, display_value: "2026-1" },
    ]);
  });

  it("outbound 与 inbound 的镜像数据只保留一条", () => {
    const links = {
      outbound: [
        {
          field_id: fieldId,
          linked_records: [{ record_id: appleId, display_value: "2026-1" }],
        },
      ],
      inbound: [
        {
          field_id: fieldId,
          linked_records: [{ record_id: appleId, display_value: "2026-1" }],
        },
      ],
    };

    expect(collectLinkDisplayRecords(links, fieldId)).toHaveLength(1);
  });

  it("后端用记录 ID 兜底 display_value 时被过滤", () => {
    const links = {
      outbound: [
        {
          field_id: fieldId,
          linked_records: [
            { record_id: appleId, display_value: appleId },
            { record_id: bananaId, display_value: "2026-2" },
          ],
        },
      ],
      inbound: [],
    };

    expect(collectLinkDisplayRecords(links, fieldId)).toEqual([
      { record_id: bananaId, display_value: "2026-2" },
    ]);
  });

  it("同名但不同的记录不会被误去重", () => {
    const links = {
      outbound: [
        {
          field_id: fieldId,
          linked_records: [
            { record_id: appleId, display_value: "苹果" },
            { record_id: bananaId, display_value: "苹果" },
          ],
        },
      ],
    };

    expect(collectLinkDisplayRecords(links, fieldId)).toHaveLength(2);
  });

  it("只返回指定字段的关联且忽略空显示值", () => {
    const links = {
      outbound: [
        { field_id: otherFieldId, linked_records: [{ record_id: appleId, display_value: "苹果" }] },
        { field_id: fieldId, linked_records: [{ record_id: appleId, display_value: "" }] },
      ],
      inbound: [
        { field_id: fieldId, linked_records: [{ record_id: bananaId, display_value: "2026-2" }] },
      ],
    };

    expect(collectLinkDisplayRecords(links, fieldId)).toEqual([
      { record_id: bananaId, display_value: "2026-2" },
    ]);
  });
});

describe("buildLinkDisplayMap", () => {
  it("inbound-only 的反向字段也能生成导出映射", () => {
    const map = buildLinkDisplayMap({
      r1: {
        inbound: [
          { field_id: fieldId, linked_records: [{ record_id: appleId, display_value: "2026-1" }] },
        ],
      },
    });

    expect(map.get("r1")?.get(fieldId)).toEqual(["2026-1"]);
  });

  it("ID 兜底值不会进入导出单元格", () => {
    const map = buildLinkDisplayMap({
      r1: {
        outbound: [
          { field_id: fieldId, linked_records: [{ record_id: appleId, display_value: appleId }] },
        ],
      },
    });

    expect(map.get("r1")?.get(fieldId)).toEqual([]);
  });
});

describe("formatLinkCellValue", () => {
  it("有映射时输出关联记录的显示名", () => {
    const map = new Map([[appleId, "苹果"]]);
    expect(formatLinkCellValue([appleId], map)).toBe("苹果");
  });

  it("无映射时不输出裸 UUID", () => {
    expect(formatLinkCellValue([appleId])).toBe("");
    expect(formatLinkCellValue([appleId], new Map())).toBe("");
    expect(formatLinkCellValue(appleId, new Map())).toBe("");
  });

  it("映射里仍是 ID 兜底值时不输出", () => {
    expect(formatLinkCellValue([appleId], new Map([[appleId, appleId]]))).toBe("");
  });

  it("多个关联按序拼接且同名只输出一次", () => {
    const map = new Map([
      [appleId, "苹果"],
      [bananaId, "苹果"],
    ]);
    expect(formatLinkCellValue([appleId, bananaId], map)).toBe("苹果");
  });

  it("空值输出空串", () => {
    expect(formatLinkCellValue(null)).toBe("");
    expect(formatLinkCellValue([])).toBe("");
    expect(formatLinkCellValue("")).toBe("");
  });
});

describe("isRawRecordIdDisplay", () => {
  it("识别记录 ID 被当作显示值的兜底数据", () => {
    expect(isRawRecordIdDisplay(appleId, appleId)).toBe(true);
    expect(isRawRecordIdDisplay("", appleId)).toBe(true);
    expect(isRawRecordIdDisplay(null, appleId)).toBe(true);
    expect(isRawRecordIdDisplay("苹果", appleId)).toBe(false);
  });
});
