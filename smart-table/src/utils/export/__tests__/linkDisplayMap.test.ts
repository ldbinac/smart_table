/**
 * Issue #IKUAYB 前端回归测试。
 *
 * 双向关联下 /records/links/batch 会把同一条关联同时以 outgoing / incoming
 * 返回（互为镜像）。修复前 ExportDialog 把两处显示名都 push 进数组，
 * 导出单元格变成「苹果, 苹果」，导入侧按显示名匹配不到，导致无法直接导入。
 */
import { describe, it, expect, beforeEach } from "vitest";
import { createPinia, setActivePinia } from "pinia";
import * as XLSX from "xlsx";
import { buildLinkDisplayMap, exportToExcel, exportToCSV } from "@/utils/export";
import { FieldType } from "@/types";
import type { FieldEntity, RecordEntity } from "@/db/schema";

beforeEach(() => {
  setActivePinia(createPinia());
});

const fruitKindFieldId = "f-fruit-kind";
const appleId = "fruit-apple";
const bananaId = "fruit-banana";
const anotherAppleId = "fruit-apple-2";

const fields = [
  { id: "f-serial", name: "序号", type: FieldType.SINGLE_LINE_TEXT, isPrimary: true },
  { id: fruitKindFieldId, name: "水果种类", type: FieldType.LINK },
] as unknown as FieldEntity[];

const records = [
  {
    id: "r1",
    values: { "f-serial": "2026-1", [fruitKindFieldId]: [appleId] },
  },
  {
    id: "r2",
    values: { "f-serial": "2026-2", [fruitKindFieldId]: [bananaId] },
  },
] as unknown as RecordEntity[];

/** 模拟双向关联下接口返回的镜像数据 */
const mirroredBatch = {
  r1: {
    outbound: [
      {
        field_id: fruitKindFieldId,
        linked_records: [{ record_id: appleId, display_value: "苹果" }],
      },
    ],
    inbound: [
      {
        field_id: fruitKindFieldId,
        linked_records: [{ record_id: appleId, display_value: "苹果" }],
      },
    ],
  },
  r2: {
    outbound: [
      {
        field_id: fruitKindFieldId,
        linked_records: [{ record_id: bananaId, display_value: "香蕉" }],
      },
    ],
    inbound: [
      {
        field_id: fruitKindFieldId,
        linked_records: [{ record_id: bananaId, display_value: "香蕉" }],
      },
    ],
  },
};

function sheetToRows(buffer: Uint8Array): string[][] {
  const wb = XLSX.read(buffer, { type: "array" });
  const ws = wb.Sheets[wb.SheetNames[0]];
  return XLSX.utils.sheet_to_json(ws, { header: 1, raw: false }) as string[][];
}

describe("导出：双向关联字段显示名去重", () => {
  it("outgoing 与 incoming 镜像数据只保留一条", () => {
    const map = buildLinkDisplayMap(mirroredBatch);

    expect(map.get("r1")?.get(fruitKindFieldId)).toEqual(["苹果"]);
    expect(map.get("r2")?.get(fruitKindFieldId)).toEqual(["香蕉"]);
  });

  it("一对多的多条关联仍全部保留", () => {
    const map = buildLinkDisplayMap({
      r1: {
        outbound: [
          {
            field_id: fruitKindFieldId,
            linked_records: [
              { record_id: appleId, display_value: "苹果" },
              { record_id: bananaId, display_value: "香蕉" },
            ],
          },
        ],
        inbound: [
          {
            field_id: fruitKindFieldId,
            linked_records: [
              { record_id: appleId, display_value: "苹果" },
              { record_id: bananaId, display_value: "香蕉" },
            ],
          },
        ],
      },
    });

    expect(map.get("r1")?.get(fruitKindFieldId)).toEqual(["苹果", "香蕉"]);
  });

  it("同名但不同记录不会被误去重", () => {
    const map = buildLinkDisplayMap({
      r1: {
        outbound: [
          {
            field_id: fruitKindFieldId,
            linked_records: [
              { record_id: appleId, display_value: "苹果" },
              { record_id: anotherAppleId, display_value: "苹果" },
            ],
          },
        ],
      },
    });

    expect(map.get("r1")?.get(fruitKindFieldId)).toEqual(["苹果", "苹果"]);
  });

  it("缺少 record_id 的旧接口数据按显示名去重", () => {
    const map = buildLinkDisplayMap({
      r1: {
        outbound: [
          {
            field_id: fruitKindFieldId,
            linked_records: [{ display_value: "苹果" }],
          },
        ],
        inbound: [
          {
            field_id: fruitKindFieldId,
            linked_records: [{ display_value: "苹果" }],
          },
        ],
      },
    });

    expect(map.get("r1")?.get(fruitKindFieldId)).toEqual(["苹果"]);
  });

  it("Excel 导出关联单元格为单个显示名", async () => {
    const context = { linkDisplayMap: buildLinkDisplayMap(mirroredBatch) };
    const rows = sheetToRows(await exportToExcel(records, fields, {}, context));
    const col = rows[0].indexOf("水果种类");

    expect(rows[1][col]).toBe("苹果");
    expect(rows[2][col]).toBe("香蕉");
    expect(rows.flat().join("|")).not.toContain("苹果, 苹果");
    expect(rows.flat().join("|")).not.toContain("香蕉, 香蕉");
  });

  it("CSV 导出关联单元格为单个显示名", () => {
    const context = { linkDisplayMap: buildLinkDisplayMap(mirroredBatch) };
    const csv = exportToCSV(records, fields, {}, context);

    expect(csv).toContain("苹果");
    expect(csv).toContain("香蕉");
    expect(csv).not.toContain("苹果, 苹果");
    expect(csv).not.toContain("香蕉, 香蕉");
    // 不能退化成导出记录 ID
    expect(csv).not.toContain(appleId);
  });
});
