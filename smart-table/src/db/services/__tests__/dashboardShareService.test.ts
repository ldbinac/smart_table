import { describe, it, expect, beforeEach, vi } from "vitest";
import { dashboardShareService } from "../dashboardShareService";
import { db } from "../../schema";

// 模拟数据库操作
vi.mock("../../schema", () => ({
  db: {
    dashboardShares: {
      add: vi.fn(),
      where: vi.fn().mockReturnValue({
        equals: vi.fn().mockReturnValue({
          first: vi.fn(),
          and: vi.fn().mockReturnValue({
            sortBy: vi.fn(),
          }),
        }),
        below: vi.fn().mockReturnValue({
          and: vi.fn().mockReturnValue({
            toArray: vi.fn(),
          }),
        }),
      }),
      get: vi.fn(),
      update: vi.fn(),
      delete: vi.fn(),
    },
  },
}));

describe("DashboardShareService", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  describe("createShare", () => {
    it("should create a share with correct properties", async () => {
      const dashboardId = "dashboard-1";
      const result = await dashboardShareService.createShare({
        dashboardId,
        expiresInHours: 24,
        maxAccessCount: 10,
        requireAccessCode: true,
        permission: "edit",
      });

      expect(result).toHaveProperty("id");
      expect(result.dashboardId).toBe(dashboardId);
      expect(result.shareToken).toHaveLength(16);
      expect(result.accessCode).toHaveLength(6);
      expect(result.expiresAt).toBeGreaterThan(Date.now());
      expect(result.maxAccessCount).toBe(10);
      expect(result.currentAccessCount).toBe(0);
      expect(result.isActive).toBe(true);
      expect(result.permission).toBe("edit");
      expect(result.createdAt).toBeGreaterThan(0);
    });

    it("should create a share without optional properties", async () => {
      const dashboardId = "dashboard-1";
      const result = await dashboardShareService.createShare({ dashboardId });

      expect(result).toHaveProperty("id");
      expect(result.dashboardId).toBe(dashboardId);
      expect(result.expiresAt).toBeUndefined();
      expect(result.maxAccessCount).toBeUndefined();
      expect(result.accessCode).toBeUndefined();
      expect(result.permission).toBe("view");
    });
  });

  describe("generateShareUrl", () => {
    it("should generate a valid share URL", () => {
      const token = "test-token";
      const expectedUrl = `${window.location.origin}/#/share/dashboard/${token}`;
      const result = dashboardShareService.generateShareUrl(token);
      expect(result).toBe(expectedUrl);
    });
  });

  describe("validateShare", () => {
    it("should validate a valid share", async () => {
      const share = {
        id: "share-1",
        dashboardId: "dashboard-1",
        shareToken: "test-token",
        isActive: true,
        expiresAt: Date.now() + 3600000,
        maxAccessCount: 10,
        currentAccessCount: 5,
      };

      (db.dashboardShares.where as any).mockImplementation(() => ({
        equals: () => ({
          first: () => Promise.resolve(share),
        }),
      }));

      const result = await dashboardShareService.validateShare("test-token");
      expect(result.valid).toBe(true);
      expect(result.share).toEqual(share);
    });

    it("should invalidate an expired share", async () => {
      const share = {
        id: "share-1",
        dashboardId: "dashboard-1",
        shareToken: "test-token",
        isActive: true,
        expiresAt: Date.now() - 3600000,
        maxAccessCount: 10,
        currentAccessCount: 5,
      };

      (db.dashboardShares.where as any).mockImplementation(() => ({
        equals: () => ({
          first: () => Promise.resolve(share),
        }),
      }));

      const result = await dashboardShareService.validateShare("test-token");
      expect(result.valid).toBe(false);
      expect(result.error).toBe("分享链接已过期");
    });

    it("should invalidate a share with max access count reached", async () => {
      const share = {
        id: "share-1",
        dashboardId: "dashboard-1",
        shareToken: "test-token",
        isActive: true,
        maxAccessCount: 5,
        currentAccessCount: 5,
      };

      (db.dashboardShares.where as any).mockImplementation(() => ({
        equals: () => ({
          first: () => Promise.resolve(share),
        }),
      }));

      const result = await dashboardShareService.validateShare("test-token");
      expect(result.valid).toBe(false);
      expect(result.error).toBe("分享链接访问次数已达上限");
    });

    it("should invalidate a disabled share", async () => {
      const share = {
        id: "share-1",
        dashboardId: "dashboard-1",
        shareToken: "test-token",
        isActive: false,
      };

      (db.dashboardShares.where as any).mockImplementation(() => ({
        equals: () => ({
          first: () => Promise.resolve(share),
        }),
      }));

      const result = await dashboardShareService.validateShare("test-token");
      expect(result.valid).toBe(false);
      expect(result.error).toBe("分享链接已被禁用");
    });

    it("should invalidate a non-existent share", async () => {
      (db.dashboardShares.where as any).mockImplementation(() => ({
        equals: () => ({
          first: () => Promise.resolve(undefined),
        }),
      }));

      const result = await dashboardShareService.validateShare("test-token");
      expect(result.valid).toBe(false);
      expect(result.error).toBe("分享链接不存在");
    });
  });
});
