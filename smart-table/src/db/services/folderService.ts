/**
 * 文件夹服务（数据表文件夹）
 * 采用「先后端、后本地」双写模式，与 tableService 保持一致
 */
import { db } from "../schema";
import type { FolderEntity } from "../schema";
import { tableFolderApiService } from "@/services/api/tableFolderApiService";

/** 空校验错误（后端 409 兜底前的本地预检） */
export class FolderNotEmptyError extends Error {
  constructor() {
    super("folder_not_empty");
    this.name = "FolderNotEmptyError";
  }
}

export class FolderService {
  /**
   * 获取 base 下所有文件夹（先后端拉取同步本地，失败时降级读本地缓存）
   */
  async getFoldersByBase(baseId: string): Promise<FolderEntity[]> {
    try {
      const apiFolders = await tableFolderApiService.getTableFolders(baseId);
      const apiIds = new Set(apiFolders.map((f) => f.id));

      await db.transaction("rw", db.tableFolderEntities, async () => {
        const localFolders = await db.tableFolderEntities
          .where("baseId")
          .equals(baseId)
          .toArray();

        // 清理本地已删除的文件夹
        for (const local of localFolders) {
          if (!apiIds.has(local.id)) {
            await db.tableFolderEntities.delete(local.id);
          }
        }

        for (const apiFolder of apiFolders) {
          const data = apiFolder as any;
          await db.tableFolderEntities.put({
            id: data.id,
            baseId: data.base_id,
            name: data.name,
            order: data.order ?? 0,
            createdAt: new Date(data.created_at).getTime(),
            updatedAt: new Date(data.updated_at).getTime(),
          });
        }
      });

      return db.tableFolderEntities.where("baseId").equals(baseId).sortBy("order");
    } catch (error) {
      console.error("[folderService] getFoldersByBase failed:", error);
      return db.tableFolderEntities.where("baseId").equals(baseId).sortBy("order");
    }
  }

  async createFolder(baseId: string, name: string): Promise<FolderEntity> {
    try {
      const apiFolder = await tableFolderApiService.createTableFolder(baseId, { name });
      const data = apiFolder as any;
      const local: FolderEntity = {
        id: data.id,
        baseId: data.base_id,
        name: data.name,
        order: data.order ?? 0,
        createdAt: new Date(data.created_at).getTime(),
        updatedAt: new Date(data.updated_at).getTime(),
      };
      await db.tableFolderEntities.add(local);
      return local;
    } catch (error) {
      console.error("[folderService] createFolder failed:", error);
      throw error;
    }
  }

  async updateFolder(
    id: string,
    changes: { name?: string; order?: number }
  ): Promise<void> {
    try {
      // 先后端更新
      await tableFolderApiService.updateTableFolder(id, changes);

      // 再更新本地（显式跳过 undefined，避免 Dexie update 删键语义）
      const localChanges: Partial<FolderEntity> = { updatedAt: Date.now() };
      if (changes.name !== undefined) {
        localChanges.name = changes.name;
      }
      if (changes.order !== undefined) {
        localChanges.order = changes.order;
      }
      await db.tableFolderEntities.update(id, localChanges);
    } catch (error) {
      console.error("[folderService] updateFolder failed:", error);
      throw error;
    }
  }

  async deleteFolder(id: string): Promise<void> {
    try {
      // 本地预检：仅空文件夹可删（后端 409 兜底）
      const count = await db.tableEntities.where("folderId").equals(id).count();
      if (count > 0) {
        throw new FolderNotEmptyError();
      }

      await tableFolderApiService.deleteTableFolder(id);
      await db.tableFolderEntities.delete(id);
    } catch (error) {
      console.error("[folderService] deleteFolder failed:", error);
      throw error;
    }
  }
}

export const folderService = new FolderService();
