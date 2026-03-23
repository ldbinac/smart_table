import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { baseService } from '../db/services/baseService';
import { tableService } from '../db/services/tableService';
import { fieldService } from '../db/services/fieldService';
import { recordService } from '../db/services/recordService';
import { viewService } from '../db/services/viewService';
import type { Base, TableEntity, FieldEntity, RecordEntity, ViewEntity } from '../db/schema';

export const useBaseStore = defineStore('base', () => {
  const bases = ref<Base[]>([]);
  const currentBase = ref<Base | null>(null);
  const tables = ref<TableEntity[]>([]);
  const currentTable = ref<TableEntity | null>(null);
  const fields = ref<FieldEntity[]>([]);
  const records = ref<RecordEntity[]>([]);
  const views = ref<ViewEntity[]>([]);
  const currentView = ref<ViewEntity | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  const sortedTables = computed(() => {
    return [...tables.value].sort((a, b) => a.order - b.order);
  });

  const sortedFields = computed(() => {
    return [...fields.value].sort((a, b) => a.order - b.order);
  });

  const sortedViews = computed(() => {
    return [...views.value].sort((a, b) => a.order - b.order);
  });

  const visibleFields = computed(() => {
    if (!currentView.value) return sortedFields.value;
    return sortedFields.value.filter(
      field => !currentView.value!.hiddenFields.includes(field.id)
    );
  });

  const frozenFields = computed(() => {
    if (!currentView.value) return [];
    return sortedFields.value.filter(
      field => currentView.value!.frozenFields.includes(field.id)
    );
  });

  async function loadBases() {
    loading.value = true;
    error.value = null;
    try {
      bases.value = await baseService.getAllBases();
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to load bases';
    } finally {
      loading.value = false;
    }
  }

  async function loadBase(id: string) {
    loading.value = true;
    error.value = null;
    try {
      const base = await baseService.getBase(id);
      if (!base) {
        error.value = 'Base not found';
        return;
      }
      currentBase.value = base;
      tables.value = await baseService.getTablesByBase(id);
      if (tables.value.length > 0) {
        await loadTable(tables.value[0].id);
      } else {
        currentTable.value = null;
        fields.value = [];
        records.value = [];
        views.value = [];
        currentView.value = null;
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to load base';
    } finally {
      loading.value = false;
    }
  }

  async function loadTable(tableId: string) {
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
      views.value = await viewService.getViewsByTable(tableId);

      const defaultView = await viewService.getDefaultView(tableId);
      currentView.value = defaultView || null;
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to load table';
    } finally {
      loading.value = false;
    }
  }

  async function createBase(data: { name: string; description?: string; icon?: string; color?: string }) {
    loading.value = true;
    error.value = null;
    try {
      const base = await baseService.createBase(data);
      bases.value.unshift(base);
      return base;
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to create base';
      return null;
    } finally {
      loading.value = false;
    }
  }

  async function updateBase(id: string, changes: Partial<Base>) {
    try {
      await baseService.updateBase(id, changes);
      const index = bases.value.findIndex(b => b.id === id);
      if (index !== -1) {
        bases.value[index] = { ...bases.value[index], ...changes, updatedAt: Date.now() };
      }
      if (currentBase.value?.id === id) {
        currentBase.value = { ...currentBase.value, ...changes, updatedAt: Date.now() };
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to update base';
    }
  }

  async function deleteBase(id: string) {
    try {
      await baseService.deleteBase(id);
      bases.value = bases.value.filter(b => b.id !== id);
      if (currentBase.value?.id === id) {
        currentBase.value = null;
        tables.value = [];
        currentTable.value = null;
        fields.value = [];
        records.value = [];
        views.value = [];
        currentView.value = null;
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to delete base';
    }
  }

  async function toggleStarBase(id: string) {
    try {
      await baseService.toggleStar(id);
      const base = bases.value.find(b => b.id === id);
      if (base) {
        base.isStarred = !base.isStarred;
      }
      if (currentBase.value?.id === id) {
        currentBase.value.isStarred = !currentBase.value.isStarred;
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to toggle star';
    }
  }

  function clearCurrentBase() {
    currentBase.value = null;
    tables.value = [];
    currentTable.value = null;
    fields.value = [];
    records.value = [];
    views.value = [];
    currentView.value = null;
  }

  return {
    bases,
    currentBase,
    tables,
    currentTable,
    fields,
    records,
    views,
    currentView,
    loading,
    error,
    sortedTables,
    sortedFields,
    sortedViews,
    visibleFields,
    frozenFields,
    loadBases,
    loadBase,
    loadTable,
    createBase,
    updateBase,
    deleteBase,
    toggleStarBase,
    clearCurrentBase
  };
});
