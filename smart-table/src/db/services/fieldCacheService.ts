import { db } from "../schema";
import type { FieldEntity } from "../schema";
import { fieldApiService } from "@/services/api/fieldApiService";
import { normalizeFieldType } from "@/types/fields";
import { generateId } from "@/utils/id";

const DEFAULT_TTL = 5 * 60 * 1000;

const CACHE_KEY_PREFIX = "fields_";

interface CacheEntry {
  fields: FieldEntity[];
  timestamp: number;
}

function getCacheKey(tableId: string): string {
  return `${CACHE_KEY_PREFIX}${tableId}`;
}

function isCacheValid(timestamp: number, ttl: number = DEFAULT_TTL): boolean {
  return Date.now() - timestamp < ttl;
}

export class FieldCacheService {
  private memoryCache = new Map<string, CacheEntry>();

  async getFieldsWithCache(
    tableId: string,
    forceRefresh: boolean = false
  ): Promise<FieldEntity[]> {
    const cacheKey = getCacheKey(tableId);

    if (!forceRefresh) {
      const memoryCached = this.getFromMemoryCache(cacheKey);
      if (memoryCached) {
        console.log(`[FieldCacheService] 从内存缓存获取表 ${tableId} 的字段`);
        return memoryCached;
      }

      const indexedDBCached = await this.getFromIndexedDB(tableId);
      if (indexedDBCached) {
        console.log(`[FieldCacheService] 从 IndexedDB 缓存获取表 ${tableId} 的字段`);
        this.setMemoryCache(cacheKey, indexedDBCached);
        return indexedDBCached;
      }
    }

    console.log(`[FieldCacheService] 从 API 获取表 ${tableId} 的字段`);
    return this.fetchFromAPI(tableId);
  }

  private getFromMemoryCache(key: string): FieldEntity[] | null {
    const entry = this.memoryCache.get(key);
    if (!entry) return null;

    if (!isCacheValid(entry.timestamp)) {
      this.memoryCache.delete(key);
      return null;
    }

    return entry.fields;
  }

  private setMemoryCache(key: string, fields: FieldEntity[]): void {
    this.memoryCache.set(key, {
      fields,
      timestamp: Date.now(),
    });
  }

  private async getFromIndexedDB(tableId: string): Promise<FieldEntity[] | null> {
    try {
      const cacheKey = getCacheKey(tableId);
      const meta = await db.cacheMeta.where("key").equals(cacheKey).first();

      if (!meta) {
        console.log(`[FieldCacheService] IndexedDB 中无缓存元数据: ${cacheKey}`);
        return null;
      }

      if (!isCacheValid(meta.timestamp, meta.ttl)) {
        console.log(`[FieldCacheService] IndexedDB 缓存已过期: ${cacheKey}`);
        await db.cacheMeta.delete(meta.id);
        return null;
      }

      const fields = await db.fields.where("tableId").equals(tableId).sortBy("order");
      
      if (fields.length === 0) {
        console.log(`[FieldCacheService] IndexedDB 中无字段数据: ${tableId}`);
        return null;
      }

      return fields;
    } catch (error) {
      console.error("[FieldCacheService] IndexedDB 读取失败:", error);
      return null;
    }
  }

  private async fetchFromAPI(tableId: string): Promise<FieldEntity[]> {
    try {
      const apiFields = await fieldApiService.getFields(tableId);

      const fields: FieldEntity[] = apiFields.map((apiField) => {
        const frontendType = normalizeFieldType(apiField.type);
        return {
          id: apiField.id,
          tableId: apiField.table_id || tableId,
          name: apiField.name,
          type: frontendType,
          options: apiField.options as Record<string, unknown> | undefined,
          config: apiField.config as Record<string, unknown> | undefined,
          isPrimary: apiField.is_primary || false,
          isSystem: apiField.is_system || false,
          isRequired: apiField.is_required || false,
          isVisible: apiField.is_visible ?? true,
          defaultValue: apiField.defaultValue,
          description: apiField.description,
          order: apiField.order ?? 0,
          createdAt: new Date(apiField.created_at).getTime(),
          updatedAt: new Date(apiField.updated_at).getTime(),
        };
      });

      await this.saveToIndexedDB(tableId, fields);

      const cacheKey = getCacheKey(tableId);
      this.setMemoryCache(cacheKey, fields);

      return fields;
    } catch (error) {
      console.error("[FieldCacheService] API 获取失败:", error);
      return this.getFromIndexedDBFallback(tableId);
    }
  }

  private async saveToIndexedDB(tableId: string, fields: FieldEntity[]): Promise<void> {
    try {
      const cacheKey = getCacheKey(tableId);

      await db.transaction("rw", [db.fields, db.cacheMeta], async () => {
        await db.fields.where("tableId").equals(tableId).delete();

        for (const field of fields) {
          await db.fields.put(field);
        }

        const existingMeta = await db.cacheMeta.where("key").equals(cacheKey).first();
        const metaId = existingMeta?.id || generateId();

        await db.cacheMeta.put({
          id: metaId,
          key: cacheKey,
          timestamp: Date.now(),
          ttl: DEFAULT_TTL,
        });
      });

      console.log(`[FieldCacheService] 已保存 ${fields.length} 个字段到 IndexedDB 缓存`);
    } catch (error) {
      console.error("[FieldCacheService] IndexedDB 保存失败:", error);
    }
  }

  private async getFromIndexedDBFallback(tableId: string): Promise<FieldEntity[]> {
    try {
      console.log(`[FieldCacheService] 尝试从 IndexedDB 降级获取表 ${tableId} 的字段`);
      const fields = await db.fields.where("tableId").equals(tableId).sortBy("order");
      
      if (fields.length > 0) {
        console.log(`[FieldCacheService] 降级获取到 ${fields.length} 个字段`);
      }
      
      return fields;
    } catch (error) {
      console.error("[FieldCacheService] 降级获取失败:", error);
      return [];
    }
  }

  async invalidateCache(tableId: string): Promise<void> {
    const cacheKey = getCacheKey(tableId);
    
    this.memoryCache.delete(cacheKey);

    try {
      await db.transaction("rw", [db.cacheMeta], async () => {
        await db.cacheMeta.where("key").equals(cacheKey).delete();
      });
      console.log(`[FieldCacheService] 已失效表 ${tableId} 的缓存`);
    } catch (error) {
      console.error("[FieldCacheService] 缓存失效操作失败:", error);
    }
  }

  async clearAllCache(): Promise<void> {
    this.memoryCache.clear();

    try {
      await db.cacheMeta.clear();
      console.log("[FieldCacheService] 已清除所有缓存");
    } catch (error) {
      console.error("[FieldCacheService] 清除缓存失败:", error);
    }
  }
}

export const fieldCacheService = new FieldCacheService();
