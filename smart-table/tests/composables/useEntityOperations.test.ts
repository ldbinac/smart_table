import { vi, describe, it, expect, beforeEach } from "vitest";
import { useEntityOperations } from "@/composables/useEntityOperations";
import { tableService } from "@/db/services/tableService";
import { dashboardService } from "@/db/services/dashboardService";
import { ElMessage, ElMessageBox } from "element-plus";
import type { TableEntity, Dashboard } from "@/db/schema";

// 模拟依赖
vi.mock("@/db/services/tableService");
vi.mock("@/db/services/dashboardService");
vi.mock("element-plus", () => ({
  ElMessage: {
    success: vi.fn(),
    error: vi.fn(),
  },
  ElMessageBox: {
    confirm: vi.fn(),
  },
}));

const mockTableService = tableService as jest.Mocked<typeof tableService>;
const mockDashboardService = dashboardService as jest.Mocked<typeof dashboardService>;
const mockElMessage = ElMessage as jest.Mocked<typeof ElMessage>;
const mockElMessageBox = ElMessageBox as jest.Mocked<typeof ElMessageBox>;

describe("useEntityOperations", () => {
  let operations: ReturnType<typeof useEntityOperations>;

  beforeEach(() => {
    // 重置所有模拟
    vi.clearAllMocks();
    operations = useEntityOperations();
  });

  describe("数据表操作", () => {
    const mockTable: TableEntity = {
      id: "table-1",
      baseId: "base-1",
      name: "测试表",
      description: "测试描述",
      primaryFieldId: "field-1",
      recordCount: 0,
      order: 1,
      isStarred: false,
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };

    it("应该成功重命名数据表", async () => {
      // 模拟成功响应
      mockTableService.updateTable.mockResolvedValue(undefined);

      await operations.renameTable(mockTable, "新表名", "新描述");

      expect(mockTableService.updateTable).toHaveBeenCalledWith("table-1", {
        name: "新表名",
        description: "新描述",
      });
      expect(mockElMessage.success).toHaveBeenCalledWith("数据表更新成功");
    });

    it("应该处理数据表重命名失败", async () => {
      // 模拟失败响应
      const error = new Error("更新失败");
      mockTableService.updateTable.mockRejectedValue(error);

      await expect(operations.renameTable(mockTable, "新表名", "新描述")).rejects.toThrow(error);
      expect(mockElMessage.error).toHaveBeenCalledWith("更新失败");
    });

    it("应该成功删除数据表", async () => {
      // 模拟确认对话框
      mockElMessageBox.confirm.mockResolvedValue(undefined);
      // 模拟成功响应
      mockTableService.deleteTable.mockResolvedValue(undefined);

      const onDeleteSuccess = vi.fn();
      await operations.deleteTable(mockTable, onDeleteSuccess);

      expect(mockElMessageBox.confirm).toHaveBeenCalledWith(
        expect.stringContaining("确定要删除数据表"),
        "删除确认",
        expect.any(Object)
      );
      expect(mockTableService.deleteTable).toHaveBeenCalledWith("table-1");
      expect(mockElMessage.success).toHaveBeenCalledWith("删除成功");
      expect(onDeleteSuccess).toHaveBeenCalled();
    });

    it("应该处理数据表删除取消", async () => {
      // 模拟取消对话框
      mockElMessageBox.confirm.mockRejectedValue("cancel");

      await expect(operations.deleteTable(mockTable)).rejects.toBe("cancel");
      expect(mockTableService.deleteTable).not.toHaveBeenCalled();
    });

    it("应该成功切换数据表收藏状态", async () => {
      // 模拟成功响应
      mockTableService.updateTable.mockResolvedValue(undefined);

      await operations.toggleStarTable(mockTable);

      expect(mockTableService.updateTable).toHaveBeenCalledWith("table-1", {
        isStarred: true,
      });
      expect(mockElMessage.success).toHaveBeenCalledWith("收藏成功");
    });
  });

  describe("仪表板操作", () => {
    const mockDashboard: Dashboard = {
      id: "dashboard-1",
      baseId: "base-1",
      name: "测试仪表板",
      description: "测试描述",
      widgets: [],
      layout: {},
      layoutType: "grid",
      gridColumns: 12,
      isStarred: false,
      order: 1,
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };

    it("应该成功重命名仪表板", async () => {
      // 模拟成功响应
      mockDashboardService.updateDashboard.mockResolvedValue(undefined);

      await operations.renameDashboard(mockDashboard, "新仪表板名", "新描述");

      expect(mockDashboardService.updateDashboard).toHaveBeenCalledWith("dashboard-1", {
        name: "新仪表板名",
        description: "新描述",
      });
      expect(mockElMessage.success).toHaveBeenCalledWith("仪表盘更新成功");
    });

    it("应该处理仪表板重命名失败", async () => {
      // 模拟失败响应
      const error = new Error("更新失败");
      mockDashboardService.updateDashboard.mockRejectedValue(error);

      await expect(operations.renameDashboard(mockDashboard, "新仪表板名", "新描述")).rejects.toThrow(error);
      expect(mockElMessage.error).toHaveBeenCalledWith("更新失败");
    });

    it("应该成功删除仪表板", async () => {
      // 模拟确认对话框
      mockElMessageBox.confirm.mockResolvedValue(undefined);
      // 模拟成功响应
      mockDashboardService.deleteDashboard.mockResolvedValue(undefined);

      const onDeleteSuccess = vi.fn();
      await operations.deleteDashboard(mockDashboard, onDeleteSuccess);

      expect(mockElMessageBox.confirm).toHaveBeenCalledWith(
        expect.stringContaining("确定要删除仪表盘"),
        "删除确认",
        expect.any(Object)
      );
      expect(mockDashboardService.deleteDashboard).toHaveBeenCalledWith("dashboard-1");
      expect(mockElMessage.success).toHaveBeenCalledWith("仪表盘删除成功");
      expect(onDeleteSuccess).toHaveBeenCalled();
    });

    it("应该处理仪表板删除取消", async () => {
      // 模拟取消对话框
      mockElMessageBox.confirm.mockRejectedValue("cancel");

      await expect(operations.deleteDashboard(mockDashboard)).rejects.toBe("cancel");
      expect(mockDashboardService.deleteDashboard).not.toHaveBeenCalled();
    });

    it("应该成功切换仪表板收藏状态", async () => {
      // 模拟成功响应
      mockDashboardService.updateDashboard.mockResolvedValue(undefined);

      await operations.toggleStarDashboard(mockDashboard);

      expect(mockDashboardService.updateDashboard).toHaveBeenCalledWith("dashboard-1", {
        isStarred: true,
      });
      expect(mockElMessage.success).toHaveBeenCalledWith("收藏成功");
    });
  });
});
