import { defineStore } from 'pinia';
import { ref } from 'vue';
import { tableService } from '../db/services/tableService';
import { fieldService } from '../db/services/fieldService';
import { recordService } from '../db/services/recordService';
import type { TableEntity, FieldEntity, RecordEntity } from '../db/schema';
import type { CellValue, FieldOptions } from '../types';

export const useTableStore = defineStore('table', () => {
  const tables = ref<TableEntity[]>([]);
  const currentTable = ref<TableEntity | null>(null);
  const fields = ref<FieldEntity[]>([]);
  const records = ref<RecordEntity[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);

  async function loadTables(baseId: string) {
    loading.value = true;
    error.value = null;
    try {
      tables.value = await tableService.getTablesByBase(baseId);
      return tables.value;
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to load tables';
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
        error.value = 'Table not found';
        return;
      }
      currentTable.value = table;
      fields.value = await fieldService.getFieldsByTable(tableId);
      records.value = await recordService.getRecordsByTable(tableId);
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to select table';
    } finally {
      loading.value = false;
    }
  }

  async function createTable(data: { baseId: string; name: string; description?: string }) {
    loading.value = true;
    error.value = null;
    try {
      const table = await tableService.createTable(data);
      tables.value.push(table);
      return table;
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to create table';
      return null;
    } finally {
      loading.value = false;
    }
  }

  async function updateTable(id: string, changes: Partial<TableEntity>) {
    try {
      await tableService.updateTable(id, changes);
      const index = tables.value.findIndex(t => t.id === id);
      if (index !== -1) {
        tables.value[index] = { ...tables.value[index], ...changes, updatedAt: Date.now() };
      }
      if (currentTable.value?.id === id) {
        currentTable.value = { ...currentTable.value, ...changes, updatedAt: Date.now() };
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to update table';
    }
  }

  async function deleteTable(id: string) {
    try {
      await tableService.deleteTable(id);
      tables.value = tables.value.filter(t => t.id !== id);
      if (currentTable.value?.id === id) {
        currentTable.value = null;
        fields.value = [];
        records.value = [];
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to delete table';
    }
  }

  async function reorderTables(baseId: string, tableIds: string[]) {
    try {
      await tableService.reorderTables(baseId, tableIds);
      const reorderedTables = tableIds.map((id, index) => {
        const table = tables.value.find(t => t.id === id);
        if (table) {
          table.order = index;
        }
        return table!;
      }).filter(Boolean);
      tables.value = reorderedTables;
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to reorder tables';
    }
  }

  async function toggleStarTable(id: string) {
    try {
      const table = tables.value.find(t => t.id === id);
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
      error.value = e instanceof Error ? e.message : 'Failed to toggle star';
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
      error.value = e instanceof Error ? e.message : 'Failed to create field';
      return null;
    }
  }

  async function updateField(id: string, changes: Partial<FieldEntity>) {
    try {
      await fieldService.updateField(id, changes);
      const index = fields.value.findIndex(f => f.id === id);
      if (index !== -1) {
        fields.value[index] = { ...fields.value[index], ...changes, updatedAt: Date.now() };
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to update field';
    }
  }

  async function deleteField(id: string) {
    try {
      await fieldService.deleteField(id);
      fields.value = fields.value.filter(f => f.id !== id);
      records.value = records.value.map(record => {
        const newValues = { ...record.values };
        delete newValues[id];
        return { ...record, values: newValues };
      });
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to delete field';
    }
  }

  async function reorderFields(tableId: string, fieldIds: string[]) {
    try {
      await fieldService.reorderFields(tableId, fieldIds);
      const reorderedFields = fieldIds.map((id, index) => {
        const field = fields.value.find(f => f.id === id);
        if (field) {
          field.order = index;
        }
        return field!;
      }).filter(Boolean);
      fields.value = reorderedFields;
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to reorder fields';
    }
  }

  async function createRecord(data: { tableId: string; values: Record<string, CellValue> }) {
    try {
      const record = await recordService.createRecord(data);
      records.value.push(record);
      if (currentTable.value?.id === data.tableId) {
        currentTable.value.recordCount++;
      }
      return record;
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to create record';
      return null;
    }
  }

  async function updateRecord(id: string, values: Record<string, CellValue>) {
    try {
      await recordService.updateRecord(id, { values });
      const index = records.value.findIndex(r => r.id === id);
      if (index !== -1) {
        records.value[index] = {
          ...records.value[index],
          values,
          updatedAt: Date.now()
        };
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to update record';
    }
  }

  async function deleteRecord(id: string) {
    try {
      const record = records.value.find(r => r.id === id);
      await recordService.deleteRecord(id);
      records.value = records.value.filter(r => r.id !== id);
      if (record && currentTable.value?.id === record.tableId) {
        currentTable.value.recordCount--;
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to delete record';
    }
  }

  async function batchDeleteRecords(ids: string[]) {
    try {
      await recordService.batchDeleteRecords(ids);
      const deletedCount = ids.length;
      records.value = records.value.filter(r => !ids.includes(r.id));
      if (currentTable.value) {
        currentTable.value.recordCount -= deletedCount;
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to batch delete records';
    }
  }

  async function refreshRecords(tableId: string) {
    try {
      records.value = await recordService.getRecordsByTable(tableId);
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to refresh records';
    }
  }

  function clearTable() {
    currentTable.value = null;
    fields.value = [];
    records.value = [];
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
    clearTable
  };
});
