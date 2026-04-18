import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { ElMessage } from "element-plus";
import type { User, UserRole, UserStatus } from "@/api/types";
import { adminApiService } from "@/services/api/adminApiService";
import type {
  SystemConfig,
  OperationLog,
  Role,
} from "@/services/api/adminApiService";

export interface UserPagination {
  page: number;
  pageSize: number;
  total: number;
}

export interface LogPagination {
  page: number;
  pageSize: number;
  total: number;
}

export const useAdminStore = defineStore("admin", () => {
  const users = ref<User[]>([]);
  const userLoading = ref(false);
  const userPagination = ref<UserPagination>({
    page: 1,
    pageSize: 20,
    total: 0,
  });

  const systemConfigs = ref<Record<string, SystemConfig>>({});
  const configLoading = ref(false);

  const operationLogs = ref<OperationLog[]>([]);
  const logLoading = ref(false);
  const logPagination = ref<LogPagination>({
    page: 1,
    pageSize: 20,
    total: 0,
  });

  const roles = ref<Role[]>([]);

  const getUserById = computed(() => {
    return (userId: string): User | undefined => {
      return users.value.find((user) => user.id === userId);
    };
  });

  const getConfigByKey = computed(() => {
    return (key: string): SystemConfig | undefined => {
      return systemConfigs.value[key];
    };
  });

  const getLogsByAction = computed(() => {
    return (action: string): OperationLog[] => {
      return operationLogs.value.filter((log) => log.action === action);
    };
  });

  async function fetchUsers(
    params: {
      page?: number;
      pageSize?: number;
      search?: string;
      role?: UserRole;
      status?: UserStatus;
    } = {},
  ) {
    userLoading.value = true;
    try {
      const response = await adminApiService.getUserList({
        page: params.page || userPagination.value.page,
        pageSize: params.pageSize || userPagination.value.pageSize,
        search: params.search,
        role: params.role,
        status: params.status,
      });

      users.value = response.items;
      userPagination.value = {
        page: response.page,
        pageSize: response.per_page,
        total: response.total,
      };

      return response;
    } catch (error) {
      throw error;
    } finally {
      userLoading.value = false;
    }
  }

  async function createUser(data: {
    email: string;
    password: string;
    name: string;
    role: UserRole;
  }) {
    userLoading.value = true;
    try {
      const newUser = await adminApiService.createUser(data);
      users.value.unshift(newUser);
      userPagination.value.total += 1;
      ElMessage.success("用户创建成功");
      return newUser;
    } catch (error) {
      throw error;
    }
  }

  async function updateUser(
    userId: string,
    data: {
      name?: string;
      email?: string;
      role?: UserRole;
    },
  ) {
    try {
      const updatedUser = await adminApiService.updateUser(userId, data);
      const index = users.value.findIndex((user) => user.id === userId);
      if (index !== -1) {
        users.value[index] = updatedUser;
      }
      ElMessage.success("用户信息更新成功");
      return updatedUser;
    } catch (error) {
      throw error;
    }
  }

  async function deleteUser(userId: string) {
    try {
      await adminApiService.deleteUser(userId);
      users.value = users.value.filter((user) => user.id !== userId);
      userPagination.value.total -= 1;
      ElMessage.success("用户删除成功");
    } catch (error) {
      throw error;
    }
  }

  async function updateUserStatus(userId: string, status: UserStatus) {
    try {
      const updatedUser = await adminApiService.updateUserStatus(
        userId,
        status,
      );
      const index = users.value.findIndex((user) => user.id === userId);
      if (index !== -1) {
        users.value[index] = updatedUser;
      }
      ElMessage.success("用户状态更新成功");
      return updatedUser;
    } catch (error) {
      throw error;
    }
  }

  async function resetUserPassword(userId: string, password?: string) {
    try {
      const result = await adminApiService.resetUserPassword(userId, password);
      if (result.temporary_password) {
        ElMessage.info(`临时密码：${result.temporary_password}`);
      } else {
        ElMessage.success("密码重置成功，新密码已发送给用户");
      }
      return result;
    } catch (error) {
      throw error;
    }
  }

  async function fetchSystemConfigs() {
    configLoading.value = true;
    try {
      const groupedConfigs = await adminApiService.getSystemConfigs();

      const configMap: Record<string, any> = {};

      if (groupedConfigs && typeof groupedConfigs === "object") {
        Object.keys(groupedConfigs).forEach((group) => {
          const groupData = groupedConfigs[group];
          if (groupData && typeof groupData === "object") {
            Object.keys(groupData).forEach((key) => {
              const value = groupData[key];
              configMap[key] = {
                key: key,
                value: value,
                config_value: value,
                group: group,
              };
            });
          }
        });
      }

      systemConfigs.value = configMap;
      return configMap;
    } catch (error) {
      throw error;
    } finally {
      configLoading.value = false;
    }
  }

  async function updateSystemConfig(
    configs: Array<{
      key: string;
      value: any;
      group?: string;
      description?: string;
    }>,
  ) {
    try {
      const response = await adminApiService.updateSystemConfigs(configs);

      const configMap: Record<string, any> = {};

      if (response && response.configs && Array.isArray(response.configs)) {
        response.configs.forEach((config: any) => {
          configMap[config.key] = {
            ...config,
            config_value: config.value,
          };
        });
      }
      else if (response && typeof response === "object") {
        Object.keys(response).forEach((group) => {
          const groupData = response[group];
          if (groupData && typeof groupData === "object") {
            Object.keys(groupData).forEach((key) => {
              const value = groupData[key];
              configMap[key] = {
                key: key,
                value: value,
                config_value: value,
                group: group,
              };
            });
          }
        });
      }

      systemConfigs.value = configMap;
      ElMessage.success("系统配置更新成功");
      return configMap;
    } catch (error) {
      throw error;
    }
  }

  async function fetchOperationLogs(
    params: {
      page?: number;
      pageSize?: number;
      userId?: string;
      action?: string;
      entityType?: string;
      startDate?: string;
      endDate?: string;
    } = {},
  ) {
    logLoading.value = true;
    try {
      const response = await adminApiService.getOperationLogs({
        page: params.page || logPagination.value.page,
        pageSize: params.pageSize || logPagination.value.pageSize,
        userId: params.userId,
        action: params.action,
        entityType: params.entityType,
        startDate: params.startDate,
        endDate: params.endDate,
      });

      operationLogs.value = response.items;
      logPagination.value = {
        page: response.page,
        pageSize: response.per_page,
        total: response.total,
      };

      return response;
    } catch (error) {
      throw error;
    } finally {
      logLoading.value = false;
    }
  }

  async function exportOperationLogs(
    params: {
      userId?: string;
      action?: string;
      entityType?: string;
      startDate?: string;
      endDate?: string;
    } = {},
  ) {
    try {
      const blob = await adminApiService.exportOperationLogs(params);
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.download = `operation_logs_${new Date().toISOString().split("T")[0]}.csv`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
      ElMessage.success("日志导出成功");
    } catch (error) {
      throw error;
    }
  }

  async function fetchRoles() {
    try {
      roles.value = await adminApiService.getRoles();
      return roles.value;
    } catch (error) {
      throw error;
    }
  }

  async function sendTestEmail(config: {
    smtp_host: string;
    smtp_port: number;
    sender_email: string;
    sender_name?: string;
    smtp_username: string;
    smtp_password: string;
    encryption_type: 'ssl' | 'tls' | 'none';
  }, testEmail: string) {
    try {
      const response = await adminApiService.sendTestEmail(config, testEmail);
      
      if (response.success) {
        ElMessage.success(response.message || "测试邮件发送成功");
        return response;
      } else {
        ElMessage.error(response.message || "测试邮件发送失败");
        throw new Error(response.message);
      }
    } catch (error: any) {
      const errorMessage = error.response?.data?.message || error.message || "测试邮件发送失败";
      ElMessage.error(errorMessage);
      throw error;
    }
  }

  function $reset() {
    users.value = [];
    userPagination.value = {
      page: 1,
      pageSize: 20,
      total: 0,
    };
    systemConfigs.value = {};
    operationLogs.value = [];
    logPagination.value = {
      page: 1,
      pageSize: 20,
      total: 0,
    };
    roles.value = [];
  }

  return {
    users,
    userLoading,
    userPagination,
    systemConfigs,
    configLoading,
    operationLogs,
    logLoading,
    logPagination,
    roles,
    getUserById,
    getConfigByKey,
    getLogsByAction,
    fetchUsers,
    createUser,
    updateUser,
    deleteUser,
    updateUserStatus,
    resetUserPassword,
    fetchSystemConfigs,
    updateSystemConfig,
    fetchOperationLogs,
    exportOperationLogs,
    fetchRoles,
    sendTestEmail,
    $reset,
  };
});
