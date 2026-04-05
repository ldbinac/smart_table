import { db } from "../schema";
import type { DashboardShare } from "../schema";
import { generateId } from "../../utils/id";
import { apiClient } from "@/api/client";

export interface CreateShareData {
  dashboardId: string;
  expiresInHours?: number;
  maxAccessCount?: number;
  requireAccessCode?: boolean;
  permission?: "view" | "edit";
}

export interface ShareValidationResult {
  valid: boolean;
  share?: DashboardShare;
  error?: string;
}

export class DashboardShareService {
  /**
   * 生成随机分享令牌
   */
  private generateShareToken(): string {
    const chars =
      "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
    let token = "";
    for (let i = 0; i < 16; i++) {
      token += chars.charAt(Math.floor(Math.random() * chars.length));
    }
    return token;
  }

  /**
   * 生成访问密码
   */
  private generateAccessCode(): string {
    const digits = "0123456789";
    let code = "";
    for (let i = 0; i < 6; i++) {
      code += digits.charAt(Math.floor(Math.random() * digits.length));
    }
    return code;
  }

  /**
   * 创建分享链接 - 调用后端 API
   */
  async createShare(data: CreateShareData): Promise<DashboardShare> {
    try {
      console.log("[DashboardShare] Creating share:", data);

      // 调用后端 API 创建分享
      const response = await apiClient.post(
        `/dashboards/${data.dashboardId}/shares`,
        {
          requireAccessCode: data.requireAccessCode,
          expiresInHours: data.expiresInHours,
          maxAccessCount: data.maxAccessCount,
          permission: data.permission || "view",
        },
      );

      console.log("[DashboardShare] API response:", response);

      // 适配后端响应格式
      // 可能是 {success, message, data} 或直接返回数据对象
      let apiShare: any;
      if (response.data?.data) {
        apiShare = response.data.data;
      } else if (response.data) {
        apiShare = response.data;
      } else {
        apiShare = response;
      }

      console.log("[DashboardShare] Extracted share:", apiShare);

      if (!apiShare || !apiShare.id) {
        throw new Error("Invalid API response: missing share data");
      }

      // 转换为本地格式并保存到 IndexedDB
      const share: DashboardShare = {
        id: apiShare.id,
        dashboardId: apiShare.dashboard_id,
        shareToken: apiShare.share_token,
        accessCode: apiShare.has_access_code
          ? this.generateAccessCode()
          : undefined,
        expiresAt: apiShare.expires_at,
        maxAccessCount: apiShare.max_access_count,
        currentAccessCount: apiShare.current_access_count,
        isActive: apiShare.is_active,
        permission: apiShare.permission as "view" | "edit",
        createdAt: new Date(apiShare.created_at).getTime(),
        createdBy: apiShare.created_by,
      };

      await db.dashboardShares.put(share);
      return share;
    } catch (error) {
      console.error("[DashboardShare] createShare failed:", error);
      throw error;
    }
  }

  /**
   * 通过分享令牌获取分享信息 - 调用后端 API（公开接口）
   */
  async getShareByToken(token: string): Promise<DashboardShare | undefined> {
    try {
      // 先尝试从本地获取
      const localShare = await db.dashboardShares
        .where("shareToken")
        .equals(token)
        .first();
      if (localShare) {
        return localShare;
      }

      // 本地没有，从后端获取（这个接口需要 accessCode）
      // 由于是公开接口，我们只从本地读取
      return undefined;
    } catch (error) {
      console.error("[DashboardShare] getShareByToken failed:", error);
      return undefined;
    }
  }

  /**
   * 获取仪表盘的所有分享链接 - 调用后端 API
   */
  async getSharesByDashboard(dashboardId: string): Promise<DashboardShare[]> {
    try {
      console.log(
        "[DashboardShare] Fetching shares from API for dashboard:",
        dashboardId,
      );

      // 检查是否有 token
      const token =
        localStorage.getItem("access_token") ||
        sessionStorage.getItem("access_token");
      console.log(
        "[DashboardShare] Current token:",
        token ? "exists" : "missing",
      );

      // 调用后端 API 获取分享列表
      const response = await apiClient.get(`/dashboards/${dashboardId}/shares`);
      console.log("[DashboardShare] API response:", response);

      // 适配后端响应格式 {success, message, data}
      const apiShares = response.data?.data || response.data || [];
      console.log("[DashboardShare] Extracted shares:", apiShares);

      if (!Array.isArray(apiShares)) {
        console.warn(
          "[DashboardShare] API response is not an array:",
          apiShares,
        );
        return [];
      }

      // 转换为本地格式并保存
      const shares: DashboardShare[] = await Promise.all(
        apiShares.map(async (apiShare: any) => {
          const share: DashboardShare = {
            id: apiShare.id,
            dashboardId: apiShare.dashboard_id,
            shareToken: apiShare.share_token,
            accessCode: apiShare.has_access_code
              ? this.generateAccessCode()
              : undefined,
            expiresAt: apiShare.expires_at,
            maxAccessCount: apiShare.max_access_count,
            currentAccessCount: apiShare.current_access_count,
            isActive: apiShare.is_active,
            permission: apiShare.permission as "view" | "edit",
            createdAt: new Date(apiShare.created_at).getTime(),
            createdBy: apiShare.created_by,
          };
          await db.dashboardShares.put(share);
          return share;
        }),
      );

      console.log("[DashboardShare] Loaded", shares.length, "shares from API");
      return shares;
    } catch (error: any) {
      console.error("[DashboardShare] getSharesByDashboard failed:", error);
      console.error("[DashboardShare] Error details:", {
        message: error.message,
        response: error.response?.data,
        status: error.response?.status,
        headers: error.response?.headers,
      });

      // API 失败时从本地读取
      console.warn("[DashboardShare] Falling back to local cache");
      const shares = await db.dashboardShares
        .where("dashboardId")
        .equals(dashboardId)
        .and((share) => share.isActive)
        .sortBy("createdAt");
      return shares;
    }
  }

  /**
   * 验证分享链接是否有效 - 调用后端 API（公开接口）
   */
  async validateShare(
    token: string,
    accessCode?: string,
  ): Promise<ShareValidationResult> {
    try {
      console.log("[DashboardShare] Validating share:", token);

      // 调用后端 API 验证
      const response = await apiClient.post(`/shares/${token}/validate`, {
        accessCode,
      });

      console.log("[DashboardShare] Full response:", response);

      // 适配多种响应格式
      let result: any;

      // 情况 1: Axios 标准格式 {data: {success, message, data: {share, dashboard}}}
      if (response.data?.data?.share && response.data?.data?.dashboard) {
        result = response.data.data;
      }
      // 情况 2: 直接返回数据 {data: {share, dashboard}}
      else if (response.data?.share && response.data?.dashboard) {
        result = response.data;
      }
      // 情况 3: response 本身就是 {share, dashboard}
      else if (response.share && response.dashboard) {
        result = response;
      }
      // 情况 4: 其他格式
      else {
        result = response.data || response;
      }

      console.log("[DashboardShare] Extracted result:", result);

      if (!result) {
        return {
          valid: false,
          error: "验证失败：无响应数据",
        };
      }

      if (result.share && result.dashboard) {
        const { share, dashboard, tables } = result;

        // 保存 share 到本地
        const localShare: DashboardShare = {
          id: share.id,
          dashboardId: share.dashboard_id,
          shareToken: share.share_token,
          accessCode: accessCode,
          expiresAt: share.expires_at,
          maxAccessCount: share.max_access_count,
          currentAccessCount: share.current_access_count,
          isActive: share.is_active,
          permission: share.permission as "view" | "edit",
          createdAt: new Date(share.created_at).getTime(),
          createdBy: share.created_by,
        };
        await db.dashboardShares.put(localShare);

        // 保存 dashboard 到本地
        const localDashboard: Dashboard = {
          id: dashboard.id,
          baseId: dashboard.base_id,
          name: dashboard.name,
          description: dashboard.description,
          widgets: (dashboard.widgets as any[]) || [],
          layout: dashboard.layout || {},
          layoutType:
            ((dashboard.layout as any)?.type as "grid" | "free") || "grid",
          gridColumns: (dashboard.layout as any)?.config?.gridColumns || 12,
          refreshConfig: {
            enabled: false,
            interval: 30000,
            autoRefresh: false,
          },
          isStarred: false,
          order: 0,
          createdAt: new Date(dashboard.created_at).getTime(),
          updatedAt: new Date(dashboard.updated_at).getTime(),
        };
        await db.dashboards.put(localDashboard);

        // 保存表数据到本地（如果后端返回了 tables）
        if (tables && Array.isArray(tables)) {
          console.log(
            "[DashboardShare] Saving",
            tables.length,
            "tables to local cache",
          );
          for (const table of tables) {
            // 保存表信息到 tableEntities 表
            await db.tableEntities.put({
              id: table.id,
              baseId: table.base_id,
              name: table.name,
              description: table.description,
              order: table.order || 0,
              primaryFieldId: table.primary_field_id,
              createdAt: new Date(table.created_at).getTime(),
              updatedAt: new Date(table.updated_at).getTime(),
            });
            console.log(
              `  [DashboardShare] 保存表：${table.name} (${table.id})`,
            );

            // 保存字段信息
            if (table.fields && Array.isArray(table.fields)) {
              console.log(`    保存 ${table.fields.length} 个字段`);
              for (const field of table.fields) {
                await db.fields.put({
                  id: field.id,
                  tableId: field.table_id,
                  name: field.name,
                  type: field.type,
                  description: field.description,
                  order: field.order || 0,
                  isPrimary: field.is_primary || false,
                  isRequired: field.is_required || false,
                  options: field.options || null,
                  config: field.config || null,
                  createdAt: new Date(field.created_at).getTime(),
                  updatedAt: new Date(field.updated_at).getTime(),
                });
              }
            }

            // 保存记录信息
            if (table.records && Array.isArray(table.records)) {
              console.log(
                `  Table ${table.name}: saving ${table.records.length} records`,
              );
              for (const record of table.records) {
                await db.records.put({
                  id: record.id,
                  tableId: record.table_id,
                  values: record.values || {},
                  created_at: new Date(record.created_at).getTime(),
                  updated_at: new Date(record.updated_at).getTime(),
                });
              }
            }
          }

          // 验证数据是否真的被保存了
          const savedTables = await db.tableEntities.toArray();
          const savedFields = await db.fields.toArray();
          const savedRecords = await db.records.toArray();
          console.log(
            `[DashboardShare] 验证保存结果：${savedTables.length} 个表，${savedFields.length} 个字段，${savedRecords.length} 条记录`,
          );
        }

        return {
          valid: true,
          share: localShare,
          dashboard: localDashboard,
          tables: tables || [], // 返回表数据
        };
      } else {
        console.warn(
          "[DashboardShare] Invalid result format, expected share and dashboard:",
          result,
        );
        return {
          valid: false,
          error: "验证失败：数据格式错误",
        };
      }
    } catch (error: any) {
      console.error("[DashboardShare] validateShare failed:", error);
      const errorMsg =
        error.response?.data?.message || error.message || "验证失败";
      return {
        valid: false,
        error: errorMsg,
      };
    }
  }

  /**
   * 记录访问 - 调用后端 API
   */
  async recordAccess(shareId: string): Promise<void> {
    try {
      // 后端在验证时自动记录，这里只需要更新本地
      const share = await db.dashboardShares.get(shareId);
      if (!share) return;

      await db.dashboardShares.update(shareId, {
        currentAccessCount: share.currentAccessCount + 1,
        lastAccessedAt: Date.now(),
      });
    } catch (error) {
      console.error("[DashboardShare] recordAccess failed:", error);
    }
  }

  /**
   * 禁用分享链接 - 调用后端 API
   */
  async deactivateShare(shareId: string): Promise<void> {
    try {
      // 调用后端 API 禁用
      await apiClient.post(`/shares/${shareId}/deactivate`);

      // 更新本地
      await db.dashboardShares.update(shareId, {
        isActive: false,
      });
    } catch (error) {
      console.error("[DashboardShare] deactivateShare failed:", error);
      throw error;
    }
  }

  /**
   * 删除分享链接 - 调用后端 API
   */
  async deleteShare(shareId: string): Promise<void> {
    try {
      // 调用后端 API 删除
      await apiClient.delete(`/shares/${shareId}`);

      // 从本地删除
      await db.dashboardShares.delete(shareId);
    } catch (error) {
      console.error("[DashboardShare] deleteShare failed:", error);
      throw error;
    }
  }

  /**
   * 清理过期的分享链接
   */
  async cleanupExpiredShares(): Promise<number> {
    const now = Date.now();
    const expiredShares = await db.dashboardShares
      .where("expiresAt")
      .below(now)
      .and((share) => share.isActive)
      .toArray();

    for (const share of expiredShares) {
      await db.dashboardShares.update(share.id, { isActive: false });
    }

    return expiredShares.length;
  }

  /**
   * 生成分享链接 URL
   */
  generateShareUrl(token: string): string {
    const baseUrl = window.location.origin;
    return `${baseUrl}/#/share/dashboard/${token}`;
  }

  /**
   * 复制链接到剪贴板
   */
  async copyToClipboard(text: string): Promise<boolean> {
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
        return true;
      }

      // 降级方案
      const textArea = document.createElement("textarea");
      textArea.value = text;
      textArea.style.position = "fixed";
      textArea.style.left = "-999999px";
      textArea.style.top = "-999999px";
      document.body.appendChild(textArea);
      textArea.focus();
      textArea.select();

      const result = document.execCommand("copy");
      document.body.removeChild(textArea);
      return result;
    } catch (error) {
      console.error("复制失败:", error);
      return false;
    }
  }
}

export const dashboardShareService = new DashboardShareService();
