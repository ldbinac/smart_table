<template>
  <div class="user-management-page" append-to-body>
    <div class="page-header">
      <h1 class="page-title">{{ t('user.title') }}</h1>
      <el-button type="primary" @click="showCreateDialog = true">
        <el-icon><Plus /></el-icon>
        {{ t('user.addUser') }}
      </el-button>
    </div>

    <div class="page-content">
      <el-card>
        <div class="filter-bar">
          <div class="filter-left">
            <el-input
              v-model="searchQuery"
              :placeholder="t('user.searchPlaceholder')"
              clearable
              style="width: 300px"
              @clear="handleSearch">
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
              <template #append>
                <el-button @click="handleSearch">{{ t('common.search') }}</el-button>
              </template>
            </el-input>

            <el-select
              v-model="filterRole"
              :placeholder="t('user.roleFilter')"
              clearable
              style="width: 150px; margin-left: 12px"
              @change="handleFilter">
              <el-option :label="t('user.roleAdmin')" value="admin" />
              <el-option :label="t('user.roleWorkspaceAdmin')" value="workspace_admin" />
              <el-option :label="t('user.roleEditor')" value="editor" />
              <el-option :label="t('user.roleViewer')" value="viewer" />
            </el-select>

            <el-select
              v-model="filterStatus"
              :placeholder="t('user.statusFilter')"
              clearable
              style="width: 120px; margin-left: 12px"
              @change="handleFilter">
              <el-option :label="t('user.statusActive')" value="active" />
              <el-option :label="t('user.statusInactive')" value="inactive" />
              <el-option :label="t('user.statusSuspended')" value="suspended" />
              <el-option :label="t('user.statusDeleted')" value="deleted" />
            </el-select>
          </div>

          <div class="filter-right">
            <el-button
              @click="handleBatchDelete"
              :disabled="selectedRows.length === 0">
              {{ t('user.batchDelete') }}
            </el-button>
          </div>
        </div>

        <el-table
          v-loading="loading"
          :data="users"
          style="width: 100%; margin-top: 16px"
          @selection-change="handleSelectionChange">
          <el-table-column type="selection" width="55" />
          <el-table-column prop="email" :label="t('user.email')" min-width="200" />
          <el-table-column prop="name" :label="t('user.name')" min-width="120" />
          <el-table-column prop="role" :label="t('user.role')" width="120">
            <template #default="{ row }">
              <el-tag :type="getRoleTagType(row.role)">
                {{ getRoleLabel(row.role) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="status" :label="t('user.status')" width="100">
            <template #default="{ row }">
              <el-tag :type="getStatusTagType(row.status)">
                {{ getStatusLabel(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" :label="t('user.createdAt')" width="180">
            <template #default="{ row }">
              {{ formatUserDate(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column :label="t('user.actions')" width="280" fixed="right">
            <template #default="{ row }">
              <el-button
                link
                type="primary"
                size="small"
                @click="handleEdit(row as User)">
                {{ t('user.edit') }}
              </el-button>
              <el-button
                v-if="row.status === 'active'"
                link
                type="warning"
                size="small"
                @click="handleSuspend(row as User)">
                {{ t('user.suspend') }}
              </el-button>
              <el-button
                v-else-if="row.status === 'suspended'"
                link
                type="success"
                size="small"
                @click="handleActivate(row as User)">
                {{ t('user.activate') }}
              </el-button>
              <el-button
                link
                type="warning"
                size="small"
                @click="handleResetPassword(row as User)">
                {{ t('user.resetPassword') }}
              </el-button>
              <el-button
                link
                type="danger"
                size="small"
                @click="handleDelete(row as User)">
                {{ t('user.delete') }}
              </el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="pagination-container">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :total="total"
            :page-sizes="[10, 20, 50, 100]"
            layout="total, sizes, prev, pager, next, jumper"
            @size-change="handleSizeChange"
            @current-change="handlePageChange" />
        </div>
      </el-card>
    </div>

    <UserDialog
      v-model:visible="showCreateDialog"
      mode="create"
      @success="handleUserCreated" />

    <UserDialog
      v-model:visible="showEditDialog"
      mode="edit"
      :user-data="editingUser"
      @success="handleUserUpdated" />

    <ResetPasswordDialog
      v-model:visible="showResetPasswordDialog"
      :user-id="resetPasswordUserId"
      @success="handlePasswordReset" />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { Plus, Search } from "@element-plus/icons-vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { useAdminStore } from "@/stores/adminStore";
import type { User, UserRole, UserStatus } from "@/api/types";
import UserDialog from "@/components/dialogs/admin/UserDialog.vue";
import ResetPasswordDialog from "@/components/dialogs/admin/ResetPasswordDialog.vue";
import { formatDateTime } from "@/utils/timezone";
import { useI18n } from "vue-i18n";

const { t } = useI18n();
const adminStore = useAdminStore();

const users = computed(() => {
  const result = adminStore.users;
  console.log("[UserManagement] users computed:", result);
  console.log("[UserManagement] users computed 长度:", result?.length);
  return result;
});
const loading = computed(() => adminStore.userLoading);
const userPagination = computed(() => adminStore.userPagination);

const searchQuery = ref("");
const filterRole = ref<UserRole | "">("");
const filterStatus = ref<UserStatus | "">("");
const currentPage = ref(1);
const pageSize = ref(10);
const selectedRows = ref<User[]>([]);

const showCreateDialog = ref(false);
const showEditDialog = ref(false);
const showResetPasswordDialog = ref(false);
const editingUser = ref<User | null>(null);
const resetPasswordUserId = ref<string>("");

const total = computed(() => userPagination.value.total);

const roleLabelMap: Record<UserRole, string> = {
  admin: t("user.roleAdmin"),
  workspace_admin: t("user.roleWorkspaceAdmin"),
  editor: t("user.roleEditor"),
  viewer: t("user.roleViewer"),
};

const statusLabelMap: Record<UserStatus, string> = {
  active: t("user.statusActive"),
  inactive: t("user.statusInactive"),
  suspended: t("user.statusSuspended"),
  deleted: t("user.statusDeleted"),
};

const getRoleLabel = (role: UserRole): string => {
  return roleLabelMap[role] || role;
};

const getStatusLabel = (status: UserStatus): string => {
  return statusLabelMap[status] || status;
};

const getRoleTagType = (
  role: UserRole,
): "success" | "warning" | "info" | "danger" | undefined => {
  const typeMap: Record<
    UserRole,
    "success" | "warning" | "info" | "danger" | undefined
  > = {
    admin: "danger",
    workspace_admin: "warning",
    editor: "success",
    viewer: "info",
  };
  return typeMap[role] || undefined;
};

const getStatusTagType = (
  status: UserStatus,
): "success" | "warning" | "info" | "danger" | undefined => {
  const typeMap: Record<
    UserStatus,
    "success" | "warning" | "info" | "danger" | undefined
  > = {
    active: "success",
    inactive: "info",
    suspended: "warning",
    deleted: "danger",
  };
  return typeMap[status] || undefined;
};

const formatUserDate = (dateString: string): string => {
  if (!dateString) return "";
  return formatDateTime(dateString, "YYYY-MM-DD HH:mm");
};

const fetchUsers = async () => {
  console.log("[UserManagement] fetchUsers 调用 - 参数:", {
    page: currentPage.value,
    pageSize: pageSize.value,
    search: searchQuery.value || undefined,
    role: filterRole.value || undefined,
    status: filterStatus.value || undefined,
  });
  try {
    await adminStore.fetchUsers({
      page: currentPage.value,
      pageSize: pageSize.value,
      search: searchQuery.value || undefined,
      role: filterRole.value || undefined,
      status: filterStatus.value || undefined,
    });
    console.log("[UserManagement] fetchUsers 完成");
  } catch (error) {
    console.error("[UserManagement] fetchUsers 失败:", error);
    ElMessage.error(t("user.fetchFailed"));
  }
};

const handleSearch = () => {
  currentPage.value = 1;
  fetchUsers();
};

const handleFilter = () => {
  currentPage.value = 1;
  fetchUsers();
};

const handleSelectionChange = (selection: User[]) => {
  selectedRows.value = selection;
};

const handleSizeChange = (size: number) => {
  pageSize.value = size;
  currentPage.value = 1;
  fetchUsers();
};

const handlePageChange = (page: number) => {
  currentPage.value = page;
  fetchUsers();
};

const handleEdit = (user: User) => {
  editingUser.value = user;
  showEditDialog.value = true;
};

const handleUserCreated = () => {
  showCreateDialog.value = false;
  fetchUsers();
};

const handleUserUpdated = () => {
  showEditDialog.value = false;
  editingUser.value = null;
  fetchUsers();
};

const handleSuspend = (user: User) => {
  ElMessageBox.confirm(t("user.suspendConfirm", { name: user.name }), t("user.suspendConfirmTitle"), {
    confirmButtonText: t("common.confirm"),
    cancelButtonText: t("common.cancel"),
    type: "warning",
  })
    .then(async () => {
      try {
        await adminStore.updateUserStatus(user.id, "suspended");
        fetchUsers();
      } catch (error) {
        ElMessage.error(t("user.suspendFailed"));
      }
    })
    .catch(() => {});
};

const handleActivate = (user: User) => {
  ElMessageBox.confirm(t("user.activateConfirm", { name: user.name }), t("user.activateConfirmTitle"), {
    confirmButtonText: t("common.confirm"),
    cancelButtonText: t("common.cancel"),
    type: "success",
  })
    .then(async () => {
      try {
        await adminStore.updateUserStatus(user.id, "active");
        fetchUsers();
      } catch (error) {
        ElMessage.error(t("user.activateFailed"));
      }
    })
    .catch(() => {});
};

const handleResetPassword = (user: User) => {
  resetPasswordUserId.value = user.id;
  showResetPasswordDialog.value = true;
};

const handlePasswordReset = () => {
  showResetPasswordDialog.value = false;
  resetPasswordUserId.value = "";
};

const handleDelete = (user: User) => {
  ElMessageBox.confirm(
    t("user.deleteConfirm", { name: user.name }),
    t("user.deleteConfirmTitle"),
    {
      confirmButtonText: t("common.confirm"),
      cancelButtonText: t("common.cancel"),
      type: "error",
    },
  )
    .then(async () => {
      try {
        await adminStore.deleteUser(user.id);
        fetchUsers();
      } catch (error) {
        ElMessage.error(t("user.deleteFailed"));
      }
    })
    .catch(() => {});
};

const handleBatchDelete = () => {
  ElMessageBox.confirm(
    t("user.batchDeleteConfirm", { count: selectedRows.value.length }),
    t("user.batchDeleteTitle"),
    {
      confirmButtonText: t("common.confirm"),
      cancelButtonText: t("common.cancel"),
      type: "error",
    },
  )
    .then(async () => {
      try {
        for (const user of selectedRows.value) {
          await adminStore.deleteUser(user.id);
        }
        ElMessage.success(t("user.batchDeleteSuccess"));
        selectedRows.value = [];
        fetchUsers();
      } catch (error) {
        ElMessage.error(t("user.batchDeleteFailed"));
      }
    })
    .catch(() => {});
};

onMounted(() => {
  console.log("[UserManagement] onMounted - 开始加载数据");
  fetchUsers();
});
</script>

<style scoped lang="scss">
.user-management-page {
  padding: 24px;

  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;

    .page-title {
      font-size: 24px;
      font-weight: 600;
      margin: 0;
    }
  }

  .page-content {
    .el-card {
      border-radius: 8px;
    }

    .filter-bar {
      display: flex;
      justify-content: space-between;
      align-items: center;

      .filter-left {
        display: flex;
        align-items: center;
      }

      .filter-right {
        display: flex;
        align-items: center;
      }
    }

    .pagination-container {
      display: flex;
      justify-content: flex-end;
      margin-top: 24px;
    }
  }
}
</style>
