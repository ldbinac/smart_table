<template>
  <div class="user-management-page">
    <div class="page-header">
      <h1 class="page-title">用户管理</h1>
      <el-button type="primary" @click="showCreateDialog = true">
        <el-icon><Plus /></el-icon>
        添加用户
      </el-button>
    </div>

    <div class="page-content">
      <el-card>
        <div class="filter-bar">
          <div class="filter-left">
            <el-input
              v-model="searchQuery"
              placeholder="搜索邮箱或姓名"
              clearable
              style="width: 300px"
              @clear="handleSearch">
              <template #prefix>
                <el-icon><Search /></el-icon>
              </template>
              <template #append>
                <el-button @click="handleSearch">搜索</el-button>
              </template>
            </el-input>

            <el-select
              v-model="filterRole"
              placeholder="角色筛选"
              clearable
              style="width: 150px; margin-left: 12px"
              @change="handleFilter">
              <el-option label="管理员" value="admin" />
              <el-option label="工作区管理员" value="workspace_admin" />
              <el-option label="编辑者" value="editor" />
              <el-option label="查看者" value="viewer" />
            </el-select>

            <el-select
              v-model="filterStatus"
              placeholder="状态筛选"
              clearable
              style="width: 120px; margin-left: 12px"
              @change="handleFilter">
              <el-option label="活跃" value="active" />
              <el-option label="未激活" value="inactive" />
              <el-option label="已暂停" value="suspended" />
              <el-option label="已删除" value="deleted" />
            </el-select>
          </div>

          <div class="filter-right">
            <el-button
              @click="handleBatchDelete"
              :disabled="selectedRows.length === 0">
              批量删除
            </el-button>
          </div>
        </div>

        <el-table
          v-loading="loading"
          :data="users"
          style="width: 100%; margin-top: 16px"
          @selection-change="handleSelectionChange">
          <el-table-column type="selection" width="55" />
          <el-table-column prop="email" label="邮箱" min-width="200" />
          <el-table-column prop="name" label="姓名" min-width="120" />
          <el-table-column prop="role" label="角色" width="120">
            <template #default="{ row }">
              <el-tag :type="getRoleTagType(row.role)">
                {{ getRoleLabel(row.role) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="status" label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="getStatusTagType(row.status)">
                {{ getStatusLabel(row.status) }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="created_at" label="创建时间" width="180">
            <template #default="{ row }">
              {{ formatDate(row.created_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="280" fixed="right">
            <template #default="{ row }">
              <el-button
                link
                type="primary"
                size="small"
                @click="handleEdit(row)">
                编辑
              </el-button>
              <el-button
                v-if="row.status === 'active'"
                link
                type="warning"
                size="small"
                @click="handleSuspend(row)">
                暂停
              </el-button>
              <el-button
                v-else-if="row.status === 'suspended'"
                link
                type="success"
                size="small"
                @click="handleActivate(row)">
                激活
              </el-button>
              <el-button
                link
                type="warning"
                size="small"
                @click="handleResetPassword(row)">
                重置密码
              </el-button>
              <el-button
                link
                type="danger"
                size="small"
                @click="handleDelete(row)">
                删除
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
  admin: "管理员",
  workspace_admin: "工作区管理员",
  editor: "编辑者",
  viewer: "查看者",
};

const statusLabelMap: Record<UserStatus, string> = {
  active: "活跃",
  inactive: "未激活",
  suspended: "已暂停",
  deleted: "已删除",
};

const getRoleLabel = (role: UserRole): string => {
  return roleLabelMap[role] || role;
};

const getStatusLabel = (status: UserStatus): string => {
  return statusLabelMap[status] || status;
};

const getRoleTagType = (
  role: UserRole,
): "success" | "warning" | "info" | "danger" | "" => {
  const typeMap: Record<
    UserRole,
    "success" | "warning" | "info" | "danger" | ""
  > = {
    admin: "danger",
    workspace_admin: "warning",
    editor: "success",
    viewer: "info",
  };
  return typeMap[role] || "";
};

const getStatusTagType = (
  status: UserStatus,
): "success" | "warning" | "info" | "danger" | "" => {
  const typeMap: Record<
    UserStatus,
    "success" | "warning" | "info" | "danger" | ""
  > = {
    active: "success",
    inactive: "info",
    suspended: "warning",
    deleted: "danger",
  };
  return typeMap[status] || "";
};

const formatDate = (dateString: string): string => {
  if (!dateString) return "";
  const date = new Date(dateString);
  return date.toLocaleString("zh-CN", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
    hour: "2-digit",
    minute: "2-digit",
  });
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
    ElMessage.error("获取用户列表失败");
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
  ElMessageBox.confirm(`确定要暂停用户 "${user.name}" 吗？`, "确认暂停", {
    confirmButtonText: "确定",
    cancelButtonText: "取消",
    type: "warning",
  })
    .then(async () => {
      try {
        await adminStore.updateUserStatus(user.id, "suspended");
        fetchUsers();
      } catch (error) {
        ElMessage.error("暂停用户失败");
      }
    })
    .catch(() => {});
};

const handleActivate = (user: User) => {
  ElMessageBox.confirm(`确定要激活用户 "${user.name}" 吗？`, "确认激活", {
    confirmButtonText: "确定",
    cancelButtonText: "取消",
    type: "success",
  })
    .then(async () => {
      try {
        await adminStore.updateUserStatus(user.id, "active");
        fetchUsers();
      } catch (error) {
        ElMessage.error("激活用户失败");
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
    `确定要删除用户 "${user.name}" 吗？此操作不可恢复。`,
    "确认删除",
    {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      type: "error",
    },
  )
    .then(async () => {
      try {
        await adminStore.deleteUser(user.id);
        fetchUsers();
      } catch (error) {
        ElMessage.error("删除用户失败");
      }
    })
    .catch(() => {});
};

const handleBatchDelete = () => {
  ElMessageBox.confirm(
    `确定要删除选中的 ${selectedRows.value.length} 个用户吗？此操作不可恢复。`,
    "批量删除",
    {
      confirmButtonText: "确定",
      cancelButtonText: "取消",
      type: "error",
    },
  )
    .then(async () => {
      try {
        for (const user of selectedRows.value) {
          await adminStore.deleteUser(user.id);
        }
        ElMessage.success("批量删除成功");
        selectedRows.value = [];
        fetchUsers();
      } catch (error) {
        ElMessage.error("批量删除失败");
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
