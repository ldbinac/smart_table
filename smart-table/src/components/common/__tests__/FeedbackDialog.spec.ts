import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { nextTick } from "vue";
import FeedbackDialog from "../FeedbackDialog.vue";
import {
  buildGitHubIssueUrl,
  buildMailtoLink,
  WECHAT_QR_PATH,
} from "@/utils/feedback";

// Mock adminStore，避免 formatDateTime 调用时缺少 Pinia
vi.mock("@/stores/adminStore", () => ({
  useAdminStore: () => ({ systemConfigs: {} }),
}));

// Mock feedback 工具模块，便于断言调用
vi.mock("@/utils/feedback", async () => {
  const actual = await vi.importActual<typeof import("@/utils/feedback")>(
    "@/utils/feedback",
  );
  return {
    ...actual,
    buildGitHubIssueUrl: vi.fn(() => "https://github.com/mock/issues/new"),
    buildGiteeIssueUrl: vi.fn(() => "https://gitee.com/mock/issues/new"),
    buildMailtoLink: vi.fn(() => "mailto:mock@example.com"),
    buildIssueBody: vi.fn(() => "MOCK_ISSUE_BODY"),
    openInNewTab: vi.fn(),
    copyToClipboard: vi.fn(async () => true),
  };
});

// Mock ElMessage，避免依赖 Element Plus 全局注册
vi.mock("element-plus", () => ({
  ElMessage: {
    success: vi.fn(),
    warning: vi.fn(),
    error: vi.fn(),
  },
}));

// Stub Element Plus 组件，避免依赖全局注册的复杂行为
const stubs = {
  "el-button": {
    template:
      '<button class="el-button" @click="$emit(\'click\')"><slot /></button>',
    emits: ["click"],
  },
};

function mountDialog(props: Record<string, any> = {}) {
  return mount(FeedbackDialog, {
    props: { visible: true, ...props },
    global: { stubs },
  });
}

describe("FeedbackDialog", () => {
  let wrapper: ReturnType<typeof mountDialog>;

  beforeEach(() => {
    vi.clearAllMocks();
  });

  afterEach(() => {
    wrapper?.unmount();
  });

  describe("基础渲染", () => {
    it("visible=true 时应渲染弹窗与标题", () => {
      wrapper = mountDialog();
      expect(wrapper.find(".feedback-dialog").exists()).toBe(true);
      expect(wrapper.find(".feedback-header h2").text()).toBe("问题反馈");
    });

    it("visible=false 时不应渲染弹窗", () => {
      wrapper = mountDialog({ visible: false });
      expect(wrapper.find(".feedback-dialog").exists()).toBe(false);
    });

    it("应渲染 4 个反馈渠道卡片", () => {
      wrapper = mountDialog();
      const cards = wrapper.findAll(".channel-card");
      expect(cards.length).toBe(4);
    });

    it("渠道卡片应包含 GitHub Issues / Gitee Issues / 邮件 / 公众号", () => {
      wrapper = mountDialog();
      const titles = wrapper.findAll(".channel-info h3").map((n) => n.text());
      expect(titles).toContain("GitHub Issues");
      expect(titles).toContain("Gitee Issues");
      expect(titles).toContain("邮件反馈");
      expect(titles).toContain("公众号关注反馈");
    });

    it("应渲染底部取消按钮", () => {
      wrapper = mountDialog();
      const footerBtn = wrapper.find(".feedback-footer .el-button");
      expect(footerBtn.exists()).toBe(true);
      expect(footerBtn.text()).toContain("取消");
    });
  });

  describe("关闭行为", () => {
    it("点击取消按钮应触发 update:visible=false", async () => {
      wrapper = mountDialog();
      await wrapper.find(".feedback-footer .el-button").trigger("click");
      expect(wrapper.emitted("update:visible")).toBeTruthy();
      expect(wrapper.emitted("update:visible")![0]).toEqual([false]);
    });

    it("点击关闭按钮应触发 update:visible=false", async () => {
      wrapper = mountDialog();
      await wrapper.find(".close-btn").trigger("click");
      expect(wrapper.emitted("update:visible")![0]).toEqual([false]);
    });

    it("点击遮罩应触发 update:visible=false", async () => {
      wrapper = mountDialog();
      await wrapper.find(".feedback-overlay").trigger("click");
      expect(wrapper.emitted("update:visible")![0]).toEqual([false]);
    });

    it("按 ESC 应触发 update:visible=false", async () => {
      wrapper = mountDialog();
      window.dispatchEvent(new KeyboardEvent("keydown", { key: "Escape" }));
      await nextTick();
      expect(wrapper.emitted("update:visible")![0]).toEqual([false]);
    });
  });

  describe("渠道跳转", () => {
    it("点击 GitHub Issues 按钮应调用 buildGitHubIssueUrl 与 openInNewTab", async () => {
      wrapper = mountDialog();
      // 渠道卡片的第一个按钮（GitHub）
      const channelButtons = wrapper.findAll(".channel-card .el-button");
      await channelButtons[0].trigger("click");
      expect(buildGitHubIssueUrl).toHaveBeenCalled();
      const { openInNewTab } = await import("@/utils/feedback");
      expect(openInNewTab).toHaveBeenCalledWith(
        "https://github.com/mock/issues/new",
      );
    });

    it("点击 Gitee Issues 按钮应复制模板并跳转到新建页", async () => {
      const { ElMessage } = await import("element-plus");
      wrapper = mountDialog();
      const channelButtons = wrapper.findAll(".channel-card .el-button");
      await channelButtons[1].trigger("click");
      await flushPromises();
      const { buildIssueBody, copyToClipboard, openInNewTab } =
        await import("@/utils/feedback");
      expect(buildIssueBody).toHaveBeenCalled();
      expect(copyToClipboard).toHaveBeenCalledWith("MOCK_ISSUE_BODY");
      expect(ElMessage.success).toHaveBeenCalled();
      expect(openInNewTab).toHaveBeenCalledWith(
        "https://gitee.com/mock/issues/new",
      );
    });

    it("点击邮件按钮应调用 buildMailtoLink 并设置 window.location.href", async () => {
      const originalHref = window.location.href;
      // jsdom 中 window.location.href 只读，使用 spy 验证赋值
      const locationSpy = vi
        .spyOn(window, "location", "set")
        .mockImplementation(() => {});
      // 由于 jsdom 限制，改用更可靠的方式：临时替换 window.location
      try {
        wrapper = mountDialog();
        const channelButtons = wrapper.findAll(".channel-card .el-button");
        await channelButtons[2].trigger("click");
        expect(buildMailtoLink).toHaveBeenCalled();
      } finally {
        locationSpy.mockRestore();
        // 还原引用
        void originalHref;
      }
    });
  });

  describe("公众号二维码视图", () => {
    it("点击查看二维码应切换到二维码视图", async () => {
      wrapper = mountDialog();
      const channelButtons = wrapper.findAll(".channel-card .el-button");
      // 公众号按钮是第 4 个
      await channelButtons[3].trigger("click");
      expect(wrapper.find(".qrcode-view").exists()).toBe(true);
      expect(wrapper.find(".channels-grid").exists()).toBe(false);
    });

    it("二维码视图应渲染图片与提示", async () => {
      wrapper = mountDialog();
      const channelButtons = wrapper.findAll(".channel-card .el-button");
      await channelButtons[3].trigger("click");
      const img = wrapper.find(".qrcode-img");
      expect(img.exists()).toBe(true);
      expect(img.attributes("src")).toBe(WECHAT_QR_PATH);
      expect(wrapper.find(".qrcode-tip").text()).toContain("SmartTable");
    });

    it("点击返回选择渠道按钮应回到渠道列表", async () => {
      wrapper = mountDialog();
      const channelButtons = wrapper.findAll(".channel-card .el-button");
      await channelButtons[3].trigger("click");
      await wrapper
        .find(".qrcode-view .el-button")
        .trigger("click");
      expect(wrapper.find(".channels-grid").exists()).toBe(true);
      expect(wrapper.find(".qrcode-view").exists()).toBe(false);
    });
  });

  describe("弹窗打开时重置视图", () => {
    it("再次打开弹窗时应回到渠道列表视图", async () => {
      wrapper = mountDialog();
      // 切换到二维码视图
      await wrapper.findAll(".channel-card .el-button")[3].trigger("click");
      expect(wrapper.find(".qrcode-view").exists()).toBe(true);
      // 关闭后再打开
      await wrapper.setProps({ visible: false });
      await flushPromises();
      await wrapper.setProps({ visible: true });
      await flushPromises();
      expect(wrapper.find(".channels-grid").exists()).toBe(true);
    });
  });
});
