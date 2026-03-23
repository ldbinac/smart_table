import { defineStore } from 'pinia';
import { ref, computed } from 'vue';
import { viewService } from '../db/services/viewService';
import type { ViewEntity } from '../db/schema';
import type { FilterCondition, SortConfig } from '../types';

export const useViewStore = defineStore('view', () => {
  const views = ref<ViewEntity[]>([]);
  const currentView = ref<ViewEntity | null>(null);
  const loading = ref(false);
  const error = ref<string | null>(null);

  const sortedViews = computed(() => {
    return [...views.value].sort((a, b) => a.order - b.order);
  });

  const currentFilters = computed(() => {
    return currentView.value?.filters || [];
  });

  const currentSorts = computed(() => {
    return currentView.value?.sorts || [];
  });

  const hiddenFields = computed(() => {
    return currentView.value?.hiddenFields || [];
  });

  const frozenFields = computed(() => {
    return currentView.value?.frozenFields || [];
  });

  async function loadViews(tableId: string) {
    loading.value = true;
    error.value = null;
    try {
      views.value = await viewService.getViewsByTable(tableId);
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to load views';
    } finally {
      loading.value = false;
    }
  }

  async function selectView(viewId: string) {
    loading.value = true;
    error.value = null;
    try {
      const view = await viewService.getView(viewId);
      if (!view) {
        error.value = 'View not found';
        return;
      }
      currentView.value = view;
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to select view';
    } finally {
      loading.value = false;
    }
  }

  async function selectDefaultView(tableId: string) {
    try {
      const defaultView = await viewService.getDefaultView(tableId);
      currentView.value = defaultView || null;
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to select default view';
    }
  }

  async function createView(data: {
    tableId: string;
    name: string;
    type: string;
    isDefault?: boolean;
  }) {
    loading.value = true;
    error.value = null;
    try {
      const view = await viewService.createView(data);
      views.value.push(view);
      return view;
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to create view';
      return null;
    } finally {
      loading.value = false;
    }
  }

  async function updateView(id: string, data: {
    name?: string;
    config?: Record<string, unknown>;
    filters?: FilterCondition[];
    sorts?: SortConfig[];
    groupBys?: string[];
    hiddenFields?: string[];
    frozenFields?: string[];
    rowHeight?: 'short' | 'medium' | 'tall';
    isDefault?: boolean;
  }) {
    try {
      await viewService.updateView(id, data);
      const index = views.value.findIndex(v => v.id === id);
      if (index !== -1) {
        views.value[index] = {
          ...views.value[index],
          ...data,
          updatedAt: Date.now()
        } as ViewEntity;
      }
      if (currentView.value?.id === id) {
        currentView.value = {
          ...currentView.value,
          ...data,
          updatedAt: Date.now()
        } as ViewEntity;
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to update view';
    }
  }

  async function deleteView(id: string) {
    try {
      await viewService.deleteView(id);
      views.value = views.value.filter(v => v.id !== id);
      if (currentView.value?.id === id) {
        currentView.value = views.value[0] || null;
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to delete view';
    }
  }

  async function duplicateView(id: string, newName: string) {
    try {
      const newView = await viewService.duplicateView(id, newName);
      views.value.push(newView);
      return newView;
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to duplicate view';
      return null;
    }
  }

  async function setDefaultView(id: string) {
    try {
      await viewService.setDefaultView(id);
      views.value.forEach(v => {
        v.isDefault = v.id === id;
      });
      if (currentView.value) {
        currentView.value.isDefault = currentView.value.id === id;
      }
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to set default view';
    }
  }

  async function reorderViews(tableId: string, viewIds: string[]) {
    try {
      await viewService.reorderViews(tableId, viewIds);
      const reorderedViews = viewIds.map((id, index) => {
        const view = views.value.find(v => v.id === id);
        if (view) {
          view.order = index;
        }
        return view!;
      }).filter(Boolean);
      views.value = reorderedViews;
    } catch (e) {
      error.value = e instanceof Error ? e.message : 'Failed to reorder views';
    }
  }

  async function updateFilters(viewId: string, filters: FilterCondition[]) {
    await updateView(viewId, { filters: filters as unknown[] as FilterCondition[] });
  }

  async function updateSorts(viewId: string, sorts: SortConfig[]) {
    await updateView(viewId, { sorts: sorts as unknown[] as SortConfig[] });
  }

  async function updateHiddenFields(viewId: string, hiddenFields: string[]) {
    await updateView(viewId, { hiddenFields });
  }

  async function updateFrozenFields(viewId: string, frozenFields: string[]) {
    await updateView(viewId, { frozenFields });
  }

  async function updateRowHeight(viewId: string, rowHeight: 'short' | 'medium' | 'tall') {
    await updateView(viewId, { rowHeight });
  }

  function clearView() {
    views.value = [];
    currentView.value = null;
  }

  return {
    views,
    currentView,
    loading,
    error,
    sortedViews,
    currentFilters,
    currentSorts,
    hiddenFields,
    frozenFields,
    loadViews,
    selectView,
    selectDefaultView,
    createView,
    updateView,
    deleteView,
    duplicateView,
    setDefaultView,
    reorderViews,
    updateFilters,
    updateSorts,
    updateHiddenFields,
    updateFrozenFields,
    updateRowHeight,
    clearView
  };
});
