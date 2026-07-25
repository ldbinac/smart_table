import { describe, it, expect, vi, beforeEach } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { createPinia, setActivePinia } from "pinia";
import {
  ElButton,
  ElDialog,
  ElForm,
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

// Mock ElMessageBox 用于测试确认弹窗
const { elMessageBoxConfirmMock } = vi.hoisted(() => ({
  elMessageBoxConfirmMock: vi.fn(),
}));
vi.mock("element-plus", async () => {
  const actual = await vi.importActual<typeof import("element-plus")>("element-plus");
  return {
    ...actual,
    ElMessageBox: {
      ...actual.ElMessageBox,
      confirm: elMessageBoxConfirmMock,
    },
  };
});

const createWorkflowMock = vi.fn();
const updateWorkflowMock = vi.fn();
const deleteWebhookMock = vi.fn();
const updateWebhookMock = vi.fn();
const checkWebhookReferencesMock = vi.fn();

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
    deleteWebhook: deleteWebhookMock,
    updateWebhook: updateWebhookMock,
    checkWebhookReferences: checkWebhookReferencesMock,
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

function mountManager() {
  return mount(WorkflowManager, {
    global: {
      plugins: [createPinia()],
      stubs: {
        teleport: true,
        // 避免 ElSelect 在测试环境中触发递归更新
        ElSelect: {
          template: '<select data-testid="workflow-table-select" :value="modelValue" @change="$emit(\'update:modelValue\', $event.target.value)"><slot /></select>',
          props: ['modelValue'],
          emits: ['update:modelValue'],
        },
        ElOption: {
          template: '<option :value="value"><slot /></option>',
          props: ['value', 'label'],
        },
      },
    },
  });
}

describe("WorkflowManager create workflow dialog", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    createWorkflowMock.mockReset();
    updateWorkflowMock.mockReset();
    deleteWebhookMock.mockReset();
    updateWebhookMock.mockReset();
    checkWebhookReferencesMock.mockReset();
    elMessageBoxConfirmMock.mockReset();
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

    const select = wrapper.find('[data-testid="workflow-table-select"]');
    await select.setValue("t1");
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

describe("WorkflowManager webhook operations", () => {
  beforeEach(() => {
    setActivePinia(createPinia());
    vi.clearAllMocks();
    createWorkflowMock.mockReset();
    updateWorkflowMock.mockReset();
    deleteWebhookMock.mockReset();
    updateWebhookMock.mockReset();
    checkWebhookReferencesMock.mockReset();
    elMessageBoxConfirmMock.mockReset();
  });

  const mockWebhookRow = {
    id: "wh-1",
    name: "测试 Webhook",
    is_active: true,
  };

  it("handleDeleteWebhook 确认后调用 deleteWebhook", async () => {
    elMessageBoxConfirmMock.mockResolvedValue("confirm");
    deleteWebhookMock.mockResolvedValue(undefined);

    const wrapper = mountManager();
    await flushPromises();

    await (wrapper.vm as any).handleDeleteWebhook(mockWebhookRow);
    await flushPromises();

    expect(elMessageBoxConfirmMock).toHaveBeenCalledTimes(1);
    expect(deleteWebhookMock).toHaveBeenCalledWith("wh-1");
  });

  it("handleDeleteWebhook 用户取消时不调用 deleteWebhook", async () => {
    elMessageBoxConfirmMock.mockRejectedValue("cancel");

    const wrapper = mountManager();
    await flushPromises();

    await (wrapper.vm as any).handleDeleteWebhook(mockWebhookRow);
    await flushPromises();

    expect(deleteWebhookMock).not.toHaveBeenCalled();
  });

  it("handleDeleteWebhook 被引用时（store 抛错）不修改 selectedWebhookId", async () => {
    elMessageBoxConfirmMock.mockResolvedValue("confirm");
    deleteWebhookMock.mockRejectedValue(new Error("webhook_in_use"));

    const wrapper = mountManager();
    await flushPromises();

    // 模拟当前选中的 webhook
    (wrapper.vm as any).selectedWebhookId = "wh-1";

    await (wrapper.vm as any).handleDeleteWebhook(mockWebhookRow);
    await flushPromises();

    expect(deleteWebhookMock).toHaveBeenCalledWith("wh-1");
    // 删除失败，selectedWebhookId 应保持不变
    expect((wrapper.vm as any).selectedWebhookId).toBe("wh-1");
  });

  it("handleToggleWebhookActive 启用操作直接调用 updateWebhook 不做引用检查", async () => {
    updateWebhookMock.mockResolvedValue({ ...mockWebhookRow, is_active: true });

    const wrapper = mountManager();
    await flushPromises();

    await (wrapper.vm as any).handleToggleWebhookActive(mockWebhookRow, true);
    await flushPromises();

    expect(checkWebhookReferencesMock).not.toHaveBeenCalled();
    expect(elMessageBoxConfirmMock).not.toHaveBeenCalled();
    expect(updateWebhookMock).toHaveBeenCalledWith("wh-1", { is_active: true });
  });

  it("handleToggleWebhookActive 禁用无引用时直接调用 updateWebhook", async () => {
    checkWebhookReferencesMock.mockResolvedValue({ references: [], count: 0 });
    updateWebhookMock.mockResolvedValue({ ...mockWebhookRow, is_active: false });

    const wrapper = mountManager();
    await flushPromises();

    await (wrapper.vm as any).handleToggleWebhookActive(mockWebhookRow, false);
    await flushPromises();

    expect(checkWebhookReferencesMock).toHaveBeenCalledWith("wh-1");
    expect(elMessageBoxConfirmMock).not.toHaveBeenCalled();
    expect(updateWebhookMock).toHaveBeenCalledWith("wh-1", { is_active: false });
  });

  it("handleToggleWebhookActive 禁用带引用时弹出二次确认", async () => {
    checkWebhookReferencesMock.mockResolvedValue({
      references: [
        {
          workflow_id: "wf-1",
          workflow_name: "测试工作流",
          workflow_status: "draft",
          node_id: "node-1",
          node_name: "Webhook 节点",
        },
      ],
      count: 1,
    });
    elMessageBoxConfirmMock.mockResolvedValue("confirm");
    updateWebhookMock.mockResolvedValue({ ...mockWebhookRow, is_active: false });

    const wrapper = mountManager();
    await flushPromises();

    await (wrapper.vm as any).handleToggleWebhookActive(mockWebhookRow, false);
    await flushPromises();

    expect(checkWebhookReferencesMock).toHaveBeenCalledWith("wh-1");
    expect(elMessageBoxConfirmMock).toHaveBeenCalledTimes(1);
    // 确认消息应包含引用工作流名称
    const confirmArg = elMessageBoxConfirmMock.mock.calls[0][0];
    expect(confirmArg).toContain("测试工作流");
    expect(confirmArg).toContain("1");
    expect(updateWebhookMock).toHaveBeenCalledWith("wh-1", { is_active: false });
  });

  it("handleToggleWebhookActive 禁用带引用用户取消时不调用 updateWebhook", async () => {
    checkWebhookReferencesMock.mockResolvedValue({
      references: [
        {
          workflow_id: "wf-1",
          workflow_name: "测试工作流",
          workflow_status: "draft",
          node_id: "node-1",
          node_name: "Webhook 节点",
        },
      ],
      count: 1,
    });
    elMessageBoxConfirmMock.mockRejectedValue("cancel");

    const wrapper = mountManager();
    await flushPromises();

    await (wrapper.vm as any).handleToggleWebhookActive(mockWebhookRow, false);
    await flushPromises();

    expect(checkWebhookReferencesMock).toHaveBeenCalledWith("wh-1");
    expect(elMessageBoxConfirmMock).toHaveBeenCalledTimes(1);
    expect(updateWebhookMock).not.toHaveBeenCalled();
  });
});
