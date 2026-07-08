import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import {
  ElButton,
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput,
  ElSelect,
  ElOption,
} from "element-plus";
import WorkflowManager from "../WorkflowManager.vue";

const mockPush = vi.fn();

vi.mock("vue-router", () => ({
  useRoute: () => ({ params: { id: "b1" } }),
  useRouter: () => ({ push: mockPush }),
}));

vi.mock("@/api/client", () => ({
  apiClient: {
    get: vi.fn().mockResolvedValue({}),
    put: vi.fn().mockResolvedValue({}),
    post: vi.fn().mockResolvedValue({}),
  },
}));

vi.mock("@/db/services/fieldService", () => ({
  fieldService: {
    getFieldsByTable: vi.fn().mockResolvedValue([]),
  },
}));

vi.mock("@/utils/timezone", () => ({
  formatDateTime: vi.fn((date: string) => date),
}));

const createWorkflowMock = vi.fn();
const updateWorkflowMock = vi.fn();

vi.mock("@/stores/workflowStore", () => ({
  useWorkflowStore: () => ({
    workflows: [],
    currentWorkflow: null,
    webhooks: [],
    versions: [],
    loading: false,
    $reset: vi.fn(),
    loadWorkflows: vi.fn().mockResolvedValue(undefined),
    loadWebhooks: vi.fn().mockResolvedValue(undefined),
    loadInstances: vi.fn().mockResolvedValue([]),
    createWorkflow: createWorkflowMock,
    updateWorkflow: updateWorkflowMock,
  }),
}));

vi.mock("@/stores/tableStore", () => ({
  useTableStore: () => ({
    tables: [
      { id: "t1", name: "测试表 1" },
      { id: "t2", name: "测试表 2" },
    ],
    loadTables: vi.fn().mockResolvedValue(undefined),
  }),
}));

vi.mock("@/components/workflow/WorkflowListPanel.vue", () => ({
  default: {
    name: "WorkflowListPanel",
    template:
      '<button class="mock-create" @click="$emit(\'create\')">新建</button>',
    emits: ["create"],
  },
}));

vi.mock("@/components/workflow/WorkflowDesigner.vue", () => ({
  default: { template: '<div class="mock-designer">Designer</div>' },
}));

vi.mock("@/components/workflow/WorkflowExecutionLog.vue", () => ({
  default: { template: '<div class="mock-log">Log</div>' },
}));

vi.mock("@/components/workflow/WebhookConfigPanel.vue", () => ({
  default: { template: '<div class="mock-webhook-config">WebhookConfig</div>' },
}));

vi.mock("@/components/workflow/WebhookDeliveryList.vue", () => ({
  default: {
    template: '<div class="mock-webhook-deliveries">WebhookDeliveryList</div>',
  },
}));

vi.mock("@/components/workflow/WorkflowTemplateGallery.vue", () => ({
  default: { template: '<div class="mock-gallery">Gallery</div>' },
}));

vi.mock("@/components/workflow/WorkflowVersionNodeSnapshot.vue", () => ({
  default: {
    template: '<div class="mock-version-snapshot">VersionSnapshot</div>',
  },
}));

const globalComponents = {
  ElButton,
  ElDialog,
  ElForm,
  ElFormItem,
  ElInput,
  ElSelect,
  ElOption,
};

function mountManager() {
  return mount(WorkflowManager, {
    global: {
      plugins: [createPinia()],
      components: globalComponents,
    },
  });
}

describe("WorkflowManager create workflow dialog", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    createWorkflowMock.mockReset();
    updateWorkflowMock.mockReset();
  });

  it("shows table selector and requires it when creating workflow", async () => {
    const wrapper = mountManager();
    await flushPromises();

    await wrapper.find(".mock-create").trigger("click");
    await flushPromises();

    const dialog = wrapper.findComponent(ElDialog);
    expect(dialog.isVisible()).toBe(true);
    expect(dialog.props("title")).toBe("新建工作流");

    const select = wrapper.find('[data-testid="workflow-table-select"]');
    expect(select.exists()).toBe(true);

    const form = wrapper.findComponent(ElForm);
    const rules = form.props("rules") as Record<string, any>;
    expect(rules.table_id).toBeDefined();
    expect(rules.table_id[0].required).toBe(true);
  });

  it("calls createWorkflow with table_id when form is valid", async () => {
    createWorkflowMock.mockResolvedValue({ id: "w1", name: "新工作流" });

    const wrapper = mountManager();
    await flushPromises();

    await wrapper.find(".mock-create").trigger("click");
    await flushPromises();

    const nameInput = wrapper.find('input[placeholder="请输入工作流名称"]');
    await nameInput.setValue("新工作流");

    const select = wrapper.findComponent(ElSelect);
    await select.trigger("click");
    await flushPromises();

    const option = wrapper.findAllComponents(ElOption).find(
      (opt) => opt.props("label") === "测试表 1"
    );
    expect(option).toBeDefined();
    await option!.trigger("click");
    await flushPromises();

    const submitBtn = wrapper.findAllComponents(ElButton).find(
      (btn) => btn.text() === "创建"
    );
    expect(submitBtn).toBeDefined();
    await submitBtn!.trigger("click");
    await flushPromises();

    expect(createWorkflowMock).toHaveBeenCalledWith("b1", {
      name: "新工作流",
      description: "",
      table_id: "t1",
    });
  });
});
