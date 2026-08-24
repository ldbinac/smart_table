import { ElMessage, ElMessageBox } from 'element-plus';

import { t } from '@/i18n';
import { tableService } from '@/db/services/tableService';
import { dashboardService } from '@/db/services/dashboardService';
import type { TableEntity, Dashboard } from '@/db/schema';

// 数据表操作接口
interface TableOperations {
  renameTable: (table: TableEntity, newName: string, newDescription?: string) => Promise<void>;
  deleteTable: (table: TableEntity, onDeleteSuccess?: () => void) => Promise<void>;
  toggleStarTable: (table: TableEntity) => Promise<void>;
}

// 仪表板操作接口
interface DashboardOperations {
  renameDashboard: (dashboard: Dashboard, newName: string, newDescription?: string) => Promise<void>;
  deleteDashboard: (dashboard: Dashboard, onDeleteSuccess?: () => void) => Promise<void>;
  toggleStarDashboard: (dashboard: Dashboard) => Promise<void>;
}

/**
 * 数据表和仪表板的通用操作
 */
export function useEntityOperations(): TableOperations & DashboardOperations {
  // 数据表重命名
  const renameTable = async (
    table: TableEntity,
    newName: string,
    newDescription?: string
  ): Promise<void> => {
    try {
      await tableService.updateTable(table.id, {
        name: newName.trim(),
        description: newDescription?.trim(),
      });
      ElMessage.success(t('base.tableUpdated'));
    } catch (error) {
      ElMessage.error(t('base.updateFailed'));
      console.error(error);
      throw error;
    }
  };

  // 数据表删除
  const deleteTable = async (
    table: TableEntity,
    onDeleteSuccess?: () => void
  ): Promise<void> => {
    try {
      await ElMessageBox.confirm(
        t('base.tableDeleteConfirm', [table.name]),
        t('base.deleteTitle'),
        {
          confirmButtonText: t('base.deleteAction'),
          cancelButtonText: t('common.cancel'),
          type: 'warning',
          confirmButtonClass: 'el-button--danger',
        }
      );

      await tableService.deleteTable(table.id);
      ElMessage.success(t('base.deleted'));
      onDeleteSuccess?.();
    } catch (error: any) {
      if (error !== 'cancel') {
        ElMessage.error(t('base.deleteFailed'));
        console.error(error);
      }
      throw error;
    }
  };

  // 数据表收藏/取消收藏
  const toggleStarTable = async (table: TableEntity): Promise<void> => {
    try {
      await tableService.updateTable(table.id, {
        isStarred: !table.isStarred,
      });
      ElMessage.success(table.isStarred ? t('base.unstarred') : t('base.starred'));
    } catch (error) {
      ElMessage.error(t('base.toggleFailed'));
      console.error(error);
      throw error;
    }
  };

  // 仪表板重命名
  const renameDashboard = async (
    dashboard: Dashboard,
    newName: string,
    newDescription?: string
  ): Promise<void> => {
    try {
      await dashboardService.updateDashboard(dashboard.id, {
        name: newName.trim(),
        description: newDescription?.trim(),
      });
      ElMessage.success(t('base.dashboardUpdated'));
    } catch (error) {
      ElMessage.error(t('base.updateFailed'));
      console.error(error);
      throw error;
    }
  };

  // 仪表板删除
  const deleteDashboard = async (
    dashboard: Dashboard,
    onDeleteSuccess?: () => void
  ): Promise<void> => {
    try {
      await ElMessageBox.confirm(
        t('base.dashboardDeleteConfirm', [dashboard.name]),
        t('base.deleteTitle'),
        {
          confirmButtonText: t('base.deleteAction'),
          cancelButtonText: t('common.cancel'),
          type: 'warning',
        }
      );

      await dashboardService.deleteDashboard(dashboard.id);
      ElMessage.success(t('base.dashboardDeleted'));
      onDeleteSuccess?.();
    } catch (error: any) {
      if (error !== 'cancel') {
        ElMessage.error(t('base.deleteFailed'));
        console.error(error);
      }
      throw error;
    }
  };

  // 仪表板收藏/取消收藏
  const toggleStarDashboard = async (dashboard: Dashboard): Promise<void> => {
    try {
      await dashboardService.updateDashboard(dashboard.id, {
        isStarred: !dashboard.isStarred,
      });
      ElMessage.success(dashboard.isStarred ? t('base.unstarred') : t('base.starred'));
    } catch (error) {
      ElMessage.error(t('base.toggleFailed'));
      console.error(error);
      throw error;
    }
  };

  return {
    renameTable,
    deleteTable,
    toggleStarTable,
    renameDashboard,
    deleteDashboard,
    toggleStarDashboard,
  };
}
