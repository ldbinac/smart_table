<template>
  <div class="member-management-page">
    <div class="page-header">
      <div class="header-left">
        <el-button link @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
          {{ t('member.back') }}
        </el-button>
        <h1 class="page-title">{{ t('member.title') }}</h1>
      </div>
      <el-button type="primary" @click="showAddDialog = true">
        <el-icon><Plus /></el-icon>
        {{ t('member.addMember') }}
      </el-button>
    </div>

    <div class="page-content">
      <el-card>
        <MemberList
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :members="members"
          :loading="loading"
          :total="total"
          :can-edit="canEdit"
          :can-delete="canDelete"
          @edit="handleEdit"
          @remove="handleRemove"
          @size-change="handleSizeChange"
          @page-change="handlePageChange" />
      </el-card>
    </div>

    <!-- 添加成员对话框 -->
    <AddMemberDialog v-model="showAddDialog" @submit="handleAddMember" />

    <!-- 编辑角色对话框 -->
    <el-dialog v-model="showEditDialog" :title="t('member.editRoleTitle')" width="400px">
      <el-form label-width="80px">
        <el-form-item :label="t('member.currentRole')">
          <el-tag :type="getRoleType(editingMember?.role)">
            {{ getRoleLabel(editingMember?.role) }}
          </el-tag>
        </el-form-item>
        <el-form-item :label="t('member.newRole')">
          <el-select
            v-model="newRole"
            :placeholder="t('member.selectRolePlaceholder')"
            style="width: 100%">
            <el-option
              v-for="role in roleOptions"
              :key="role.value"
              :label="role.label"
              :value="role.value" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">{{ t('member.cancel') }}</el-button>
        <el-button type="primary" :loading="updating" @click="confirmEdit">
          {{ t('member.confirm') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { ArrowLeft, Plus } from "@element-plus/icons-vue";
import { ElMessageBox, ElMessage } from "element-plus";
import MemberList from "@/components/base/MemberList.vue";
import AddMemberDialog from "@/components/base/AddMemberDialog.vue";
import { baseApiService } from "@/services/api/baseApiService";
import { useAuthStore } from "@/stores/auth/authStore";
import { useI18n } from "vue-i18n";
import type { BaseMember } from "@/api/types";

const { t } = useI18n();

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

const baseId = computed(() => route.params.id as string);

// 状态
const members = ref<BaseMember[]>([]);
const loading = ref(false);
const total = ref(0);
const currentPage = ref(1);
const pageSize = ref(10);

const showAddDialog = ref(false);
const showEditDialog = ref(false);
const editingMember = ref<BaseMember | null>(null);
const newRole = ref<string>("editor");
const updating = ref(false);

// 权限检查
const canEdit = computed(() => {
  return authStore.hasPermission("admin");
});

const canDelete = computed(() => {
  return authStore.hasPermission("admin");
});

// 角色选项
const roleOptions = [
  { value: "admin", label: t("member.roleAdmin") },
  { value: "editor", label: t("member.roleEditor") },
  { value: "commenter", label: t("member.roleCommenter") },
  { value: "viewer", label: t("member.roleViewer") },
];

const roleMap: Record<
  string,
  { label: string; type: "success" | "warning" | "info" | "danger" | "" }
> = {
  owner: { label: t("member.roleOwner"), type: "danger" },
  admin: { label: t("member.roleAdmin"), type: "warning" },
  editor: { label: t("member.roleEditor"), type: "success" },
  commenter: { label: t("member.roleCommenter"), type: "info" },
  viewer: { label: t("member.roleViewer"), type: "" },
};

const getRoleLabel = (role?: string): string => {
  return roleMap[role || ""]?.label || role || "";
};

const getRoleType = (
  role?: string,
): "success" | "warning" | "info" | "danger" | "primary" | undefined => {
  return roleMap[role || ""]?.type || "info";
};

// 获取成员列表
const fetchMembers = async () => {
  loading.value = true;
  try {
    const response = await baseApiService.getBaseMembers(baseId.value);
    members.value = response;
    total.value = response.length;
  } catch (error) {
    ElMessage.error(t("member.fetchFailed"));
  } finally {
    loading.value = false;
  }
};

// 添加成员
const handleAddMember = async (data: { userId: string; role: string }) => {
  try {
    await baseApiService.addBaseMember(baseId.value, data.userId, data.role);
    ElMessage.success(t("member.addSuccess"));
    fetchMembers();
  } catch (error) {
    ElMessage.error(t("member.addFailed"));
  }
};

// 编辑成员
const handleEdit = (member: BaseMember) => {
  editingMember.value = member;
  newRole.value = member.role;
  showEditDialog.value = true;
};

const confirmEdit = async () => {
  if (!editingMember.value) return;

  updating.value = true;
  try {
    await baseApiService.updateMemberRole(
      baseId.value,
      editingMember.value.id,
      newRole.value,
    );
    ElMessage.success(t("member.updateRoleSuccess"));
    showEditDialog.value = false;
    fetchMembers();
  } catch (error) {
    ElMessage.error(t("member.updateRoleFailed"));
  } finally {
    updating.value = false;
  }
};

// 移除成员
const handleRemove = (member: BaseMember) => {
  ElMessageBox.confirm(
    t("member.removeConfirm", { name: member.user?.name || member.user_id }),
    t("member.removeConfirmTitle"),
    {
      confirmButtonText: t("common.confirm"),
      cancelButtonText: t("common.cancel"),
      type: "warning",
    },
  )
    .then(async () => {
      try {
        await baseApiService.removeBaseMember(baseId.value, member.id);
        ElMessage.success(t("member.removeSuccess"));
        fetchMembers();
      } catch (error) {
        ElMessage.error(t("member.removeFailed"));
      }
    })
    .catch(() => {
      // 取消操作
    });
};

// 分页处理
const handleSizeChange = (size: number) => {
  pageSize.value = size;
  currentPage.value = 1;
  fetchMembers();
};

const handlePageChange = (page: number) => {
  currentPage.value = page;
  fetchMembers();
};

// 返回
const goBack = () => {
  router.back();
};

onMounted(() => {
  fetchMembers();
});
</script>

<style scoped lang="scss">
.member-management-page {
  padding: 24px;

  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;

    .header-left {
      display: flex;
      align-items: center;
      gap: 16px;

      .page-title {
        font-size: 24px;
        font-weight: 600;
        margin: 0;
      }
    }
  }

  .page-content {
    .el-card {
      border-radius: 8px;
    }
  }
}
</style>
