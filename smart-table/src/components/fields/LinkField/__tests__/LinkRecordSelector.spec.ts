/**
 * Issue #IKUAYB 评论问题的组件级回归测试：
 * 「选择关联记录」弹窗的已选标签与列表关联列不得显示裸记录 ID。
 */
import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";

// vi.mock 的工厂会被提升，所有被工厂引用的变量必须用 vi.hoisted 声明
const h = vi.hoisted(() => {
  const appleId = "a874fc42-c70b-45dd-93a6-cc61652f9b01";
  const priceRecordId = "price-row-1";
  const serialFieldId = "f-serial";
  const linkFieldId = "f-kind";

  const stub = (tag: string) => ({ name: `Stub${tag}`, template: `<${tag}><slot /></${tag}>` });
  const page = (items: Array<{ id: string; values: Record<string, unknown> }>) => ({
    items,
    total: items.length,
    page: 1,
    per_page: 20,
    total_pages: 1,
  });
  const state = { fruitSearchFails: false, missingSelectedLookup: false };

  const displayFields = [
    {
      id: serialFieldId,
      name: "序号",
      type: "single_line_text",
      isVisible: true,
      order: 0,
    },
    {
      id: linkFieldId,
      name: "水果种类",
      type: "link",
      isVisible: true,
      order: 1,
      config: { linkedTableId: "fruit-table", displayFieldId: "f-name" },
    },
  ];

  const searchLinkableRecords = vi.fn(
    async (tableId: string, params?: Record<string, unknown>) => {
      if (tableId === "fruit-table") {
        if (state.fruitSearchFails) throw new Error("load failed");
        return page([{ id: appleId, values: { "f-name": "苹果" } }]);
      }
      // loadRecords 会带 exclude_ids；补取已选记录时没有该参数
      if (params?.exclude_ids) {
        return page([
          {
            id: priceRecordId,
            values: { [serialFieldId]: "2026-8", [linkFieldId]: [appleId] },
          },
        ]);
      }
      if (state.missingSelectedLookup) return page([]);
      return page([{ id: appleId, values: { [serialFieldId]: "2026-1" } }]);
    },
  );

  return {
    appleId,
    priceRecordId,
    serialFieldId,
    linkFieldId,
    stub,
    state,
    displayFields,
    searchLinkableRecords,
  };
});

const { appleId, serialFieldId, linkFieldId } = h;

vi.mock("vue-i18n", () => ({
  useI18n: () => ({ t: (key: string) => key }),
}));

vi.mock("element-plus", () => ({
  ElDialog: { name: "ElDialog", template: "<div><slot /></div>" },
  ElInput: { name: "ElInput", template: "<div><slot /></div>" },
  ElIcon: h.stub("i"),
  ElTag: h.stub("span"),
  ElCheckbox: h.stub("span"),
  ElButton: h.stub("button"),
  ElPagination: { name: "ElPagination", template: "<div></div>" },
  ElSkeleton: { name: "ElSkeleton", template: "<div></div>" },
  ElEmpty: { name: "ElEmpty", template: "<div></div>" },
}));

vi.mock("@/services/api/linkApiService", () => ({
  linkApiService: {
    searchLinkableRecords: h.searchLinkableRecords,
    getRecordLinks: vi.fn().mockResolvedValue({ outbound: [], inbound: [] }),
  },
}));

vi.mock("@/services/api/tableApiService", () => ({
  tableApiService: { getTable: vi.fn().mockResolvedValue({ name: "价格表" }) },
}));

vi.mock("@/db/services/tableService", () => ({
  tableService: { getTable: vi.fn().mockResolvedValue({ name: "价格表" }) },
}));

vi.mock("@/db/services/fieldCacheService", () => ({
  fieldCacheService: {
    getFieldsWithCache: vi.fn().mockResolvedValue(h.displayFields),
  },
}));

import LinkRecordSelector from "@/components/fields/LinkField/LinkRecordSelector.vue";

async function mountSelector(linkedRecords: Array<{ record_id: string; display_value: string }>) {
  const wrapper = mount(LinkRecordSelector, {
    props: {
      visible: true,
      targetTableId: "price-table",
      displayFieldId: serialFieldId,
      selectedIds: [appleId],
      linkedRecords,
    },
  });
  // watch(immediate) 与 onMounted 的多层异步加载
  await flushPromises();
  await flushPromises();
  return wrapper;
}

describe("LinkRecordSelector 关联显示值", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    h.state.fruitSearchFails = false;
    h.state.missingSelectedLookup = false;
  });

  it("已选记录显示展示字段值，列表关联列显示名称，均不出现裸 UUID", async () => {
    const wrapper = await mountSelector([{ record_id: appleId, display_value: "" }]);
    const text = wrapper.text();

    expect(text).toContain("2026-1");
    expect(text).toContain("苹果");
    expect(text).not.toContain(appleId);
  });

  it("后端用 ID 兜底 display_value 时，已选标签也不显示 UUID", async () => {
    const wrapper = await mountSelector([{ record_id: appleId, display_value: appleId }]);
    expect(wrapper.text()).not.toContain(appleId);
  });

  it("已选记录显示值补取失败时，标签也不会退化成记录 ID", async () => {
    h.state.missingSelectedLookup = true;
    const wrapper = await mountSelector([{ record_id: appleId, display_value: "" }]);
    expect(wrapper.text()).not.toContain(appleId);
  });

  it("关联显示名映射加载失败时，列表列显示占位而不是 UUID", async () => {
    h.state.fruitSearchFails = true;
    const wrapper = await mountSelector([{ record_id: appleId, display_value: "" }]);
    const text = wrapper.text();

    expect(text).not.toContain(appleId);
    expect(text).toContain("-");
  });
});
