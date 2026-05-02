import { defineStore } from "pinia";
import { ref } from "vue";
import { tableService } from "../db/services/tableService";
import { fieldService } from "../db/services/fieldService";
import { recordService } from "../db/services/recordService";
import { viewService } from "../db/services/viewService";
import { db } from "../db/schema";
import type { TableEntity, FieldEntity, RecordEntity, ViewEntity } from "../db/schema";
import type { CellValue } from "../types";
import { FieldType } from "../types/fields";
import { deserializeRecordValues } from "../utils/recordValueSerializer";
import { useCollaborationStore } from "./collaborationStore";
import { realtimeEventEmitter } from "../services/realtime/eventEmitter";
import type {
  DataRecordCreatedBroadcast,
  DataRecordUpdatedBroadcast,
  DataRecordDeletedBroadcast,
  DataFieldCreatedBroadcast,
  DataFieldUpdatedBroadcast,
  DataFieldDeletedBroadcast,
} from "../services/realtime/eventTypes";

export const useTableStore = defineStore("table", () => {
  const tables = ref<TableEntity[]>([]);
  const currentTable = ref<TableEntity | null>(null);
  const fields = ref<FieldEntity[]>([]);
  const views = ref<ViewEntity[]>([]);
  const records = ref<RecordEntity[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);
  let cleanupTableListeners: (() => void) | null = null;

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
    try {
      const table = await tableService.getTable(tableId);
      if (!table) {
        error.value = "Table not found";
        return;
      }
      currentTable.value = table;
      // 强制刷新字段、视图和记录，确保与后端一致
      fields.value = await fieldService.getFieldsByTable(tableId);
      views.value = await viewService.getViewsByTable(tableId, true); // 强制刷新视图
      records.value = await recordService.getRecordsByTable(tableId);
    } catch (e) {
      error.value = e instanceof Error ? e.message : "Failed to select table";
    } finally {
      loading.value = false;
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
      // 过滤掉自动编号字段（只读字段不可编辑）
      const editableValues: Record<string, CellValue> = {};
      const autoNumberFieldIds = fields.value
        .filter((f) => f.type === FieldType.AUTO_NUMBER)
        .map((f) => f.id);

      for (const [fieldId, value] of Object.entries(values)) {
        if (!autoNumberFieldIds.includes(fieldId)) {
          editableValues[fieldId] = value;
        }
      }

      await recordService.updateRecord(id, { values: editableValues });
      const index = records.value.findIndex((r) => r.id === id);
      if (index !== -1) {
        // 使用反序列化后的值更新本地缓存
        records.value[index] = {
          ...records.value[index],
          values: deserializeRecordValues(editableValues),
          updatedAt: Date.now(),
        };
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
      if (currentTable.value) {
        currentTable.value.recordCount -= deletedCount;
      }
    } catch (e) {
      error.value =
        e instanceof Error ? e.message : "Failed to batch delete records";
    }
  }

  async function refreshRecords(tableId: string) {
    try {
      records.value = await recordService.getRecordsByTable(tableId);
    } catch (e) {
      error.value =
        e instanceof Error ? e.message : "Failed to refresh records";
    }
  }

  function clearTable() {
    currentTable.value = null;
    fields.value = [];
    records.value = [];
  }

  function setupRealtimeListeners() {
    const collabStore = useCollaborationStore();
    if (!collabStore.isRealtimeAvailable) return;

    if (cleanupTableListeners) {
      cleanupTableListeners();
    }

    const onRecordCreated = (data: DataRecordCreatedBroadcast) => {
      if (!currentTable.value || data.table_id !== currentTable.value.id) return;
      const record = data.record as unknown as RecordEntity;
      if (record && !records.value.find((r) => r.id === record.id)) {
        records.value.push(record);
      }
    };

    const onRecordUpdated = (data: DataRecordUpdatedBroadcast) => {
      if (!currentTable.value || data.table_id !== currentTable.value.id) return;
      const index = records.value.findIndex((r) => r.id === data.record_id);
      if (index !== -1) {
        const existing = records.value[index];
        const updatedValues = { ...existing.values };
        for (const change of data.changes) {
          updatedValues[change.field_id] = change.new_value;
        }
        records.value[index] = {
          ...existing,
          values: updatedValues,
          updatedAt: Date.now(),
        };
      }
    };

    const onRecordDeleted = (data: DataRecordDeletedBroadcast) => {
      if (!currentTable.value || data.table_id !== currentTable.value.id) return;
      const existed = records.value.find((r) => r.id === data.record_id);
      records.value = records.value.filter((r) => r.id !== data.record_id);
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
      console.log('[TableStore] Record updated successfully')
    } else {
      console.log('[TableStore] Record not found in local store')
    }
  }

  async function deleteRecordFromRemote(tableId: string, recordId: string) {
    if (currentTable.value?.id !== tableId) return
    const existed = records.value.find((r) => r.id === recordId)
    records.value = records.value.filter((r) => r.id !== recordId)
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
    currentTable,
    fields,
    records,
    loading,
    error,
    loadTables,
    selectTable,
    createTable,
    updateTable,
    deleteTable,
    reorderTables,
    toggleStarTable,
    createField,
    updateField,
    deleteField,
    reorderFields,
    createRecord,
    updateRecord,
    deleteRecord,
    batchDeleteRecords,
    refreshRecords,
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
