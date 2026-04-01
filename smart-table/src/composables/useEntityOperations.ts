import { ElMessage, ElMessageBox } from 'element-plus';
import { tableService } from '@/db/services/tableService';
import { dashboardService } from '@/db/services/dashboardService';
import type { TableEntity, Dashboard } from '@/db/schema';

// 通用操作选项接口
interface EntityOperationOptions {
  onSuccess?: () => void;
  onError?: (error: any) => void;
}

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
      ElMessage.success('数据表更新成功');
    } catch (error) {
      ElMessage.error('更新失败');
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
        `确定要删除数据表 "${table.name}" 吗？此操作将删除该表中的所有数据，包括字段、记录和视图，且无法恢复。`,
        '删除确认',
        {
          confirmButtonText: '删除',
          cancelButtonText: '取消',
          type: 'warning',
          confirmButtonClass: 'el-button--danger',
        }
      );

      await tableService.deleteTable(table.id);
      ElMessage.success('删除成功');
      onDeleteSuccess?.();
    } catch (error: any) {
      if (error !== 'cancel') {
        ElMessage.error('删除失败');
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
      ElMessage.success(table.isStarred ? '已取消收藏' : '收藏成功');
    } catch (error) {
      ElMessage.error('操作失败');
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
      ElMessage.success('仪表盘更新成功');
    } catch (error) {
      ElMessage.error('更新失败');
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
        `确定要删除仪表盘 "${dashboard.name}" 吗？`,
        '删除确认',
        {
          confirmButtonText: '删除',
          cancelButtonText: '取消',
          type: 'warning',
        }
      );

      await dashboardService.deleteDashboard(dashboard.id);
      ElMessage.success('仪表盘删除成功');
      onDeleteSuccess?.();
    } catch (error: any) {
      if (error !== 'cancel') {
        ElMessage.error('删除失败');
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
      ElMessage.success(dashboard.isStarred ? '已取消收藏' : '收藏成功');
    } catch (error) {
      ElMessage.error('操作失败');
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
