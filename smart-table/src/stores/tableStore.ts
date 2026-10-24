import { defineStore } from "pinia";
import { ref } from "vue";
import { tableService } from "../db/services/tableService";
import { folderService, FolderNotEmptyError } from "../db/services/folderService";
import { fieldService } from "../db/services/fieldService";
import { recordService } from "../db/services/recordService";
import { viewService } from "../db/services/viewService";
import { db } from "../db/schema";
import type {
  TableEntity,
  FieldEntity,
  RecordEntity,
  ViewEntity,
  FolderEntity,
} from "../db/schema";
import type { CellValue } from "../types";
import type { FieldOptions } from "../types/fields";
import { FieldType } from "../types/fields";
import { deserializeRecordValues } from "../utils/recordValueSerializer";
import { useCollaborationStore } from "./collaborationStore";
import { realtimeEventEmitter } from "../services/realtime/eventEmitter";
import type {
  DataRecordCreatedBroadcast,
  DataRecordUpdatedBroadcast,
  DataRecordDeletedBroadcast,
} from "../services/realtime/eventTypes";
import type { StreamingLoadState } from "../db/services/recordService";
import { t } from "@/i18n";

// 将后端广播的时间值（ISO 字符串或时间戳）转换为毫秒时间戳
function toTimestamp(value: unknown): number {
  if (typeof value === "number") return value;
  if (typeof value === "string") {
    const t = new Date(value).getTime();
    if (!Number.isNaN(t)) return t;
  }
  return Date.now();
}

export const useTableStore = defineStore("table", () => {
  const tables = ref<TableEntity[]>([]);
  const folders = ref<FolderEntity[]>([]);
  const currentTable = ref<TableEntity | null>(null);
  const fields = ref<FieldEntity[]>([]);
  const views = ref<ViewEntity[]>([]);
  const records = ref<RecordEntity[]>([]);
  // F1 优化：显式版本号，替代对 records 的 deep watch。
  // 所有修改 records 的入口都必须 bump 版本号，让订阅点从 O(N×F) 的深度依赖
  // 收集退化为 O(1) 的浅订阅。
  const recordsVersion = ref(0);
  // F2 优化：变更元信息，让 VTableView watcher 能区分单行编辑 vs 全量替换，
  // 对单行编辑走 O(1) 增量路径而不是 O(N) 全量 rebuild。
  // 'edit'  = 单行/多行值更新（行数不变）
  // 'append'= 新增记录（行数增加）
  // 'delete'= 删除记录（行数减少）
  // 'full'  = 全量替换 / 字段 schema 变更 / 初始化 — 必须全量 rebuild
  type RecordsChangeType = 'edit' | 'append' | 'delete' | 'full';
  const lastChangeType = ref<RecordsChangeType>('full');
  const lastChangedRecordId = ref<string | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);
  const streamingState = ref<StreamingLoadState>({
    isLoading: false,
    loadedCount: 0,
    totalCount: 0,
    currentPage: 0,
    totalPages: 0,
    error: null,
  });
  let cleanupTableListeners: (() => void) | null = null;
  let refreshRecordsGeneration = 0;

  /** F1+F2 辅助：每次 bump 都带上变更类型，让订阅方走增量/全量路径 */
  function _bumpRecordsVersion(
    changeType: RecordsChangeType = 'full',
    recordId: string | null = null,
  ) {
    lastChangeType.value = changeType;
    lastChangedRecordId.value = recordId;
    recordsVersion.value++;
  }

  async function loadTables(baseId: string) {
    loading.value = true;
    error.value = null;
    try {
      tables.value = await tableService.getTablesByBase(baseId);
      return tables.value;
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Failed to load tables";
      return [];
    } finally {
      loading.value = false;
    }
  }

  async function selectTable(tableId: string) {
    loading.value = true;
    error.value = null;
    // 重置流式加载状态
    streamingState.value = {
      isLoading: false,
      loadedCount: 0,
      totalCount: 0,
      currentPage: 0,
      totalPages: 0,
      error: null,
    };
    try {
      const table = await tableService.getTable(tableId);
      if (!table) {
        error.value = "Table not found";
        return;
      }
      currentTable.value = table;
      // 强制刷新字段、视图
      fields.value = await fieldService.getFieldsByTable(tableId);
      views.value = await viewService.getViewsByTable(tableId, true);

      // 使用流式加载记录（pageSize 与 SmartTableDataSource.batchSize 保持一致）
      const { initialRecords, loadPromise } = await recordService.streamLoadRecords(
        tableId,
        {
          onProgress: (state, newRecords) => {
            streamingState.value = { ...state };
            // 内存累加：直接追加新增记录，避免 IndexedDB 全量读取
            if (newRecords && newRecords.length > 0) {
              records.value = [...records.value, ...newRecords];
              // F2：流式加载追加 → append 类型，多条新记录，lastChangedRecordId 取首条
              _bumpRecordsVersion('append', newRecords[0]?.id ?? null);
            }
          },
          onComplete: (state) => {
            streamingState.value = { ...state };
            // F3 Step 1：删除 refreshRecords(tableId) 全量 IndexedDB 回读。
            // 流式 onProgress 已经把所有 records 累加进 records.value，
            // IndexedDB 也同步写入了，再读一遍纯粹是 O(N) I/O + 多余的 full rebuild。
          },
          onError: (err) => {
            console.error("[tableStore] 流式加载失败:", err);
            streamingState.value = {
              ...streamingState.value,
              isLoading: false,
              error: typeof err === 'string' ? err : t('common.loadFailed'),
            };
            error.value = typeof err === 'string' ? err : t('common.loadFailed');
            // F3 Step 1：同样删除 refreshRecords(tableId)，内存里已有部分数据。
          },
        },
        200,
      );

      records.value = initialRecords;
      // F2：初始加载 → full，首次全量渲染
      _bumpRecordsVersion('full');

      // 后台加载不阻塞
      loadPromise.catch((err) => {
        // 错误已在 onError 中处理，这里避免未捕获的 Promise rejection
        if (!err) return;
        console.warn("[tableStore] 后台加载异常:", err);
      });
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Failed to select table";
      streamingState.value = {
        ...streamingState.value,
        isLoading: false,
        error: error.value,
      };
    } finally {
      loading.value = false;
    }
  }

  /**
   * 取消当前表格的流式加载
   */
  function cancelLoading() {
    if (!currentTable.value) return;
    const tableId = currentTable.value.id;
    recordService.cancelStreamingLoad(tableId);
    streamingState.value = {
      ...streamingState.value,
      isLoading: false,
      error: t('common.cancelLoading'),
    };
  }

  async function refreshRecords(tableId: string) {
    const gen = ++refreshRecordsGeneration;
    try {
      const localRecords = await recordService.getLocalRecordsByTable(tableId);
      if (gen === refreshRecordsGeneration) {
        records.value = localRecords;
        _bumpRecordsVersion('full');
        console.log(`[tableStore] 已从本地刷新记录列表: ${localRecords.length} 条`);
      }
    } catch (e) {
      console.error("[tableStore] refreshRecords failed:", e);
    }
  }

  /**
   * 强制从后端重新加载当前表全部记录（刷新按钮）
   * 取消进行中的加载 → 清空本地缓存（防已删除记录回流）→ 重新流式加载
   * @returns 首屏重载是否成功（后台剩余页进度经 streamingState 上报）
   */
  async function reloadRecords() {
    const tableId = currentTable.value?.id;
    if (!tableId) return false;
    recordService.cancelStreamingLoad(tableId);
    streamingState.value = {
      isLoading: false,
      loadedCount: 0,
      totalCount: 0,
      currentPage: 0,
      totalPages: 0,
      error: null,
    };
    try {
      await recordService.clearLocalRecords(tableId);
      const { initialRecords, loadPromise } = await recordService.streamLoadRecords(
        tableId,
        {
          onProgress: (state, newRecords) => {
            streamingState.value = { ...state };
            if (newRecords && newRecords.length > 0) {
              records.value = [...records.value, ...newRecords];
              // F2：流式重载追加 → append
              _bumpRecordsVersion('append', newRecords[0]?.id ?? null);
            }
          },
          onComplete: (state) => {
            streamingState.value = { ...state };
            // F3 Step 1：同 selectTable 的 onComplete，已在 onProgress 累加完毕
          },
          onError: (err) => {
            console.error("[tableStore] 重新加载记录失败:", err);
            streamingState.value = {
              ...streamingState.value,
              isLoading: false,
              error: typeof err === 'string' ? err : t('common.loadFailed'),
            };
            // F3 Step 1：内存里已有已加载的部分，无需 refreshRecords
          },
        },
        200,
      );
      records.value = initialRecords;
      // F2：重载初始加载 → full
      _bumpRecordsVersion('full');
      loadPromise.catch((err) => {
        if (!err) return;
        console.warn("[tableStore] 重新加载后台异常:", err);
      });
      return true;
    } catch (e) {
      console.error("[tableStore] reloadRecords failed:", e);
      streamingState.value = {
        ...streamingState.value,
        isLoading: false,
        error: e instanceof Error ? e.message : t('common.loadFailed'),
      };
      // 失败时尝试从本地恢复已加载的部分
      refreshRecords(tableId);
      return false;
    }
  }

  async function createTable(data: {
    baseId: string;
    name: string;
    description?: string;
  }) {
    loading.value = true;
    error.value = null;
    try {
      const table = await tableService.createTable(data);
      tables.value.push(table);
      return table;
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Failed to create table";
      return null;
    } finally {
      loading.value = false;
    }
  }

  async function updateTable(id: string, changes: Partial<TableEntity>) {
    try {
      await tableService.updateTable(id, changes);
      const index = tables.value.findIndex((t) => t.id === id);
      if (index !== -1) {
        tables.value[index] = {
          ...tables.value[index],
          ...changes,
          updatedAt: Date.now(),
        };
      }
      if (currentTable.value?.id === id) {
        currentTable.value = {
          ...currentTable.value,
          ...changes,
          updatedAt: Date.now(),
        };
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Failed to update table";
    }
  }

  async function deleteTable(id: string) {
    try {
      await tableService.deleteTable(id);
      tables.value = tables.value.filter((t) => t.id !== id);
      if (currentTable.value?.id === id) {
        currentTable.value = null;
        fields.value = [];
        records.value = [];
        _bumpRecordsVersion('full');
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Failed to delete table";
    }
  }

  async function reorderTables(baseId: string, tableIds: string[]) {
    try {
      await tableService.reorderTables(baseId, tableIds);
      const reorderedTables = tableIds
        .map((id, index) => {
          const table = tables.value.find((t) => t.id === id);
          if (table) {
            table.order = index;
          }
          return table!;
        })
        .filter(Boolean);
      tables.value = reorderedTables;
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Failed to reorder tables";
    }
  }

  async function toggleStarTable(id: string) {
    try {
      const table = tables.value.find((t) => t.id === id);
      if (table) {
        const newStarredState = !table.isStarred;
        await tableService.updateTable(id, { isStarred: newStarredState });
        table.isStarred = newStarredState;
        table.updatedAt = Date.now();
        if (currentTable.value?.id === id) {
          currentTable.value.isStarred = newStarredState;
          currentTable.value.updatedAt = Date.now();
        }
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Failed to toggle star";
    }
  }

  // ==================== 文件夹（数据表分组） ====================

  async function loadFolders(baseId: string) {
    try {
      folders.value = await folderService.getFoldersByBase(baseId);
      return folders.value;
    } catch (e) {
      console.error("[tableStore] loadFolders failed:", e);
      return [];
    }
  }

  async function createFolder(baseId: string, name: string) {
    try {
      const folder = await folderService.createFolder(baseId, name);
      folders.value.push(folder);
      return folder;
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Failed to create folder";
      return null;
    }
  }

  async function renameFolder(id: string, name: string) {
    try {
      await folderService.updateFolder(id, { name });
      const index = folders.value.findIndex((f) => f.id === id);
      if (index !== -1) {
        folders.value[index] = { ...folders.value[index], name, updatedAt: Date.now() };
      }
      return true;
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Failed to rename folder";
      return false;
    }
  }

  async function deleteFolder(id: string) {
    try {
      await folderService.deleteFolder(id);
      folders.value = folders.value.filter((f) => f.id !== id);
      return true;
    } catch (e) {
      if (e instanceof FolderNotEmptyError) {
        error.value = "folder_not_empty";
      } else {
        error.value = e instanceof Error ? e.message : "Failed to delete folder";
      }
      return false;
    }
  }

  /**
   * 移动表格到文件夹（folderId 为 null 表示移出文件夹/未分组）
   */
  async function moveTableToFolder(tableId: string, folderId: string | null) {
    await updateTable(tableId, { folderId });
  }

  async function createField(data: {
    tableId: string;
    name: string;
    type: string;
    options?: FieldOptions;
    isRequired?: boolean;
    defaultValue?: CellValue;
    description?: string;
  }) {
    try {
      const field = await fieldService.createField(data);
      fields.value.push(field);
      return field;
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Failed to create field";
      return null;
    }
  }

  async function updateField(id: string, changes: Partial<FieldEntity>) {
    try {
      await fieldService.updateField(id, changes);
      const index = fields.value.findIndex((f) => f.id === id);
      if (index !== -1) {
        fields.value[index] = {
          ...fields.value[index],
          ...changes,
          updatedAt: Date.now(),
        };
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Failed to update field";
    }
  }

  async function deleteField(id: string) {
    try {
      await fieldService.deleteField(id);
      fields.value = fields.value.filter((f) => f.id !== id);
      records.value = records.value.map((record) => {
        const newValues = { ...record.values };
        delete newValues[id];
        return { ...record, values: newValues };
      });
      // F2：删除字段是 schema 变更 — full 重建
      _bumpRecordsVersion('full');
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Failed to delete field";
    }
  }

  async function reorderFields(tableId: string, fieldIds: string[]) {
    try {
      await fieldService.reorderFields(tableId, fieldIds);
      const reorderedFields = fieldIds
        .map((id, index) => {
          const field = fields.value.find((f) => f.id === id);
          if (field) {
            field.order = index;
          }
          return field!;
        })
        .filter(Boolean);
      fields.value = reorderedFields;
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Failed to reorder fields";
    }
  }

  async function createRecord(data: {
    tableId: string;
    values: Record<string, CellValue>;
  }) {
    try {
      const record = await recordService.createRecord(data);
      // 当实时协作不可用时，手动添加记录到列表
      // 当实时协作可用时，通过实时事件监听添加，避免重复添加
      const collabStore = useCollaborationStore();
      if (!collabStore.isRealtimeAvailable) {
        if (currentTable.value?.id === data.tableId) {
          // 检查记录是否已存在，避免重复添加
          if (!records.value.find((r) => r.id === record.id)) {
            records.value.push(record);
            // F2：新增记录 → append，携带 record.id 让 watcher 定位行
            _bumpRecordsVersion('append', record.id);
          }
          currentTable.value.recordCount++;
        }
      } else {
        // 实时协作可用时，只更新记录数
        // 记录会通过实时事件自动添加
        if (currentTable.value?.id === data.tableId) {
          currentTable.value.recordCount++;
        }
      }
      return record;
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Failed to create record";
      return null;
    }
  }

  async function updateRecord(id: string, values: Record<string, CellValue>) {
    try {
      // 过滤掉自动编号字段与系统字段（只读字段不可编辑，值由记录元数据维护）
      const editableValues: Record<string, CellValue> = {};
      const readonlyFieldIds = fields.value
        .filter(
          (f) =>
            f.type === FieldType.AUTO_NUMBER ||
            f.type === FieldType.CREATED_BY ||
            f.type === FieldType.CREATED_TIME ||
            f.type === FieldType.UPDATED_BY ||
            f.type === FieldType.UPDATED_TIME,
        )
        .map((f) => f.id);

      for (const [fieldId, value] of Object.entries(values)) {
        if (!readonlyFieldIds.includes(fieldId)) {
          editableValues[fieldId] = value;
        }
      }

      const computedValues = await recordService.updateRecord(id, {
        values: editableValues,
      });
      const index = records.value.findIndex((r) => r.id === id);
      if (index !== -1) {
        // 合并更新值，保留未修改的字段
        records.value[index] = {
          ...records.value[index],
          values: {
            ...records.value[index].values,
            ...deserializeRecordValues(editableValues),
          },
          // 后端重算后的公式值（含跨表引用），供渲染层优先使用
          ...(computedValues ? { computed_values: computedValues } : {}),
          updatedAt: Date.now(),
        };
        // F2：核心入口！单行编辑 → edit，携带 id 让 watcher 走增量快路径
        _bumpRecordsVersion('edit', id);
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Failed to update record";
    }
  }

  async function deleteRecord(id: string) {
    try {
      const record = records.value.find((r) => r.id === id);
      await recordService.deleteRecord(id);
      records.value = records.value.filter((r) => r.id !== id);
      // F2：单行删除 → delete + id
      _bumpRecordsVersion('delete', id);
      if (record && currentTable.value?.id === record.tableId) {
        currentTable.value.recordCount--;
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Failed to delete record";
    }
  }

  async function batchDeleteRecords(ids: string[]) {
    try {
      await recordService.batchDeleteRecords(ids);
      const deletedCount = ids.length;
      records.value = records.value.filter((r) => !ids.includes(r.id));
      // F2：批量删除 → delete（多条，lastChangedRecordId 取首条）
      _bumpRecordsVersion('delete', ids[0] ?? null);
      if (currentTable.value) {
        currentTable.value.recordCount -= deletedCount;
      }
    } catch (e) {
      error.value =
        e instanceof Error ? e.message : "Failed to batch delete records";
    }
  }

  function clearTable() {
    currentTable.value = null;
    fields.value = [];
    records.value = [];
    // F2：清空表 → full
    _bumpRecordsVersion('full');
  }

  function setupRealtimeListeners() {
    const collabStore = useCollaborationStore();
    if (!collabStore.isRealtimeAvailable) return;

    if (cleanupTableListeners) {
      cleanupTableListeners();
    }

    const onRecordCreated = (data: DataRecordCreatedBroadcast) => {
      if (!currentTable.value || data.table_id !== currentTable.value.id) return;
      // 后端广播的 record 为 Record.to_dict()（snake_case：table_id/created_at/updated_at），
      // 必须转换为 RecordEntity 的 camelCase 格式，否则 tableId/createdAt/updatedAt 为 undefined：
      // - 主从表场景下新记录被误判为子表记录，放大镜打开错误抽屉并保存到错误字段
      // - 复制记录时请求 /tables/undefined/fields
      const raw = (data.record || {}) as Record<string, unknown>;
      const record: RecordEntity = {
        id: String(raw.id ?? ""),
        tableId: (raw.tableId as string) || data.table_id,
        values: (raw.values as Record<string, CellValue>) || {},
        createdAt: toTimestamp(raw.createdAt ?? raw.created_at),
        updatedAt: toTimestamp(raw.updatedAt ?? raw.updated_at),
        createdBy: (raw.createdBy as string) ?? (raw.created_by as string),
        updatedBy: (raw.updatedBy as string) ?? (raw.updated_by as string),
      };
      if (record.id && !records.value.find((r) => r.id === record.id)) {
        records.value.push(record);
        // F2：实时新增 → append + record.id
        _bumpRecordsVersion('append', record.id);
        // 同步持久化到本地 IndexedDB：refreshRecords 仅读取本地缓存，
        // 不落库会导致新记录在后续刷新后从前端消失
        try {
          db.records.put(record);
        } catch (e) {
          console.warn("[tableStore] 实时新增记录写入本地缓存失败:", e);
        }
      }
    };

    const onRecordUpdated = (data: DataRecordUpdatedBroadcast) => {
      if (!currentTable.value || data.table_id !== currentTable.value.id) return;
      const index = records.value.findIndex((r) => r.id === data.record_id);
      if (index !== -1) {
        const existing = records.value[index];
        const updatedValues = { ...existing.values };
        for (const change of data.changes) {
          updatedValues[change.field_id] = change.new_value as any;
        }
        records.value[index] = {
          ...existing,
          values: updatedValues,
          updatedAt: Date.now(),
        };
        // F2：实时编辑 → edit + record_id
        _bumpRecordsVersion('edit', data.record_id);
      }
    };

    const onRecordDeleted = (data: DataRecordDeletedBroadcast) => {
      if (!currentTable.value || data.table_id !== currentTable.value.id) return;
      const existed = records.value.find((r) => r.id === data.record_id);
      records.value = records.value.filter((r) => r.id !== data.record_id);
      // F2：实时删除 → delete + record_id
      _bumpRecordsVersion('delete', data.record_id);
      if (existed && currentTable.value) {
        currentTable.value.recordCount--;
      }
    };

    realtimeEventEmitter.on("data:record_created", onRecordCreated);
    realtimeEventEmitter.on("data:record_updated", onRecordUpdated);
    realtimeEventEmitter.on("data:record_deleted", onRecordDeleted);

    cleanupTableListeners = () => {
      realtimeEventEmitter.off("data:record_created", onRecordCreated);
      realtimeEventEmitter.off("data:record_updated", onRecordUpdated);
      realtimeEventEmitter.off("data:record_deleted", onRecordDeleted);
    };
  }

  function cleanupRealtimeListeners() {
    if (cleanupTableListeners) {
      cleanupTableListeners();
      cleanupTableListeners = null;
    }
  }

  function addRecordFromRemote(tableId: string, record: RecordEntity) {
    if (currentTable.value?.id !== tableId) return
    if (!records.value.find((r) => r.id === record.id)) {
      records.value.push(record)
      _bumpRecordsVersion('append', record.id)
      currentTable.value.recordCount++
    }
  }

  function updateRecordFromRemote(tableId: string, recordId: string, changes: Array<{ field_id: string; old_value: any; new_value: any }>) {
    console.log('[TableStore] updateRecordFromRemote called, tableId:', tableId, 'recordId:', recordId)
    console.log('[TableStore] currentTable?.id:', currentTable.value?.id)
    console.log('[TableStore] changes:', changes)
    
    if (currentTable.value?.id !== tableId) {
      console.log('[TableStore] Skipping update - table mismatch')
      return
    }
    
    const index = records.value.findIndex((r) => r.id === recordId)
    console.log('[TableStore] Record index:', index)
    
    if (index !== -1) {
      const existing = records.value[index]
      const updatedValues = { ...existing.values }
      for (const change of changes) {
        updatedValues[change.field_id] = change.new_value
      }
      records.value[index] = {
        ...existing,
        values: updatedValues,
        updatedAt: Date.now(),
      }
      _bumpRecordsVersion('edit', recordId)
      console.log('[TableStore] Record updated successfully')
    } else {
      console.log('[TableStore] Record not found in local store')
    }
  }

  async function deleteRecordFromRemote(tableId: string, recordId: string) {
    if (currentTable.value?.id !== tableId) return
    const existed = records.value.find((r) => r.id === recordId)
    records.value = records.value.filter((r) => r.id !== recordId)
    _bumpRecordsVersion('delete', recordId)
    if (existed && currentTable.value) {
      currentTable.value.recordCount--
    }

    try {
      await db.records.delete(recordId)
      console.log(`[tableStore] 已从本地缓存删除远程删除的记录: ${recordId}`)
    } catch (error) {
      console.error(`[tableStore] 删除本地记录缓存失败:`, error)
    }
  }

  async function addFieldFromRemote(tableId: string, field: FieldEntity) {
    if (currentTable.value?.id !== tableId) return
    if (!fields.value.find((f) => f.id === field.id)) {
      fields.value.push(field)
      try {
        await db.fields.put(field)
      } catch (e) {
        console.error('[tableStore] Failed to sync field to IndexedDB:', e)
      }
    }
  }

  async function updateFieldFromRemote(tableId: string, fieldId: string, field: Partial<FieldEntity>) {
    if (currentTable.value?.id !== tableId) return
    const index = fields.value.findIndex((f) => f.id === fieldId)
    if (index !== -1) {
      fields.value[index] = {
        ...fields.value[index],
        ...field,
        updatedAt: Date.now(),
      } as FieldEntity
      try {
        await db.fields.update(fieldId, {
          ...field,
          updatedAt: Date.now(),
        })
      } catch (e) {
        console.error('[tableStore] Failed to sync field update to IndexedDB:', e)
      }
    }
  }

  async function deleteFieldFromRemote(tableId: string, fieldId: string) {
    if (currentTable.value?.id !== tableId) return
    fields.value = fields.value.filter((f) => f.id !== fieldId)
    records.value = records.value.map((record) => {
      const newValues = { ...record.values }
      delete newValues[fieldId]
      return { ...record, values: newValues }
    })
    _bumpRecordsVersion('full')
    try {
      await db.fields.delete(fieldId)
    } catch (e) {
      console.error('[tableStore] Failed to sync field deletion to IndexedDB:', e)
    }
  }

  function addTableFromRemote(table: TableEntity) {
    if (!tables.value.find((t) => t.id === table.id)) {
      tables.value.push(table)
    }
  }

  function updateTableFromRemote(tableId: string, changes: Partial<TableEntity>) {
    const index = tables.value.findIndex((t) => t.id === tableId)
    if (index !== -1) {
      tables.value[index] = {
        ...tables.value[index],
        ...changes,
        updatedAt: Date.now(),
      }
    }
    if (currentTable.value?.id === tableId) {
      currentTable.value = {
        ...currentTable.value,
        ...changes,
        updatedAt: Date.now(),
      }
    }
  }

  async function deleteTableFromRemote(tableId: string) {
    tables.value = tables.value.filter((t) => t.id !== tableId)
    if (currentTable.value?.id === tableId) {
      currentTable.value = null
      fields.value = []
      records.value = []
      _bumpRecordsVersion('full')
    }

    try {
      await tableService.deleteTableFromLocal(tableId)
      console.log(`[tableStore] 已从本地缓存删除远程删除的表格: ${tableId}`)
    } catch (error) {
      console.error(`[tableStore] 删除本地缓存失败:`, error)
    }
  }

  return {
    tables,
    folders,
    currentTable,
    fields,
    views,
    records,
    recordsVersion,
    lastChangeType,
    lastChangedRecordId,
    loading,
    error,
    streamingState,
    cancelLoading,
    loadTables,
    selectTable,
    refreshRecords,
    reloadRecords,
    createTable,
    updateTable,
    deleteTable,
    reorderTables,
    toggleStarTable,
    loadFolders,
    createFolder,
    renameFolder,
    deleteFolder,
    moveTableToFolder,
    createField,
    updateField,
    deleteField,
    reorderFields,
    createRecord,
    updateRecord,
    deleteRecord,
    batchDeleteRecords,
    clearTable,
    setupRealtimeListeners,
    cleanupRealtimeListeners,
    addRecordFromRemote,
    updateRecordFromRemote,
    deleteRecordFromRemote,
    addFieldFromRemote,
    updateFieldFromRemote,
    deleteFieldFromRemote,
    addTableFromRemote,
    updateTableFromRemote,
    deleteTableFromRemote,
  };
});
