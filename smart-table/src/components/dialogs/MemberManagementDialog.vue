<template>
  <el-dialog
    v-model="dialogVisible"
    title="成员管理"
    width="800px"
    :close-on-click-modal="false"
    class="member-management-dialog">
    <div v-loading="loading" class="member-content">
      <!-- 成员列表 -->
      <div class="member-list">
        <div
          v-for="member in members"
          :key="member.user_id"
          class="member-item"
          :class="{ 'is-owner': member.role === 'owner' }">
          <div class="member-info">
            <div class="member-avatar">
              <el-avatar :size="40" :src="member.user?.avatar">
                {{ member.user?.name?.charAt(0) || "U" }}
              </el-avatar>
            </div>
            <div class="member-details">
              <div class="member-name">
                {{ member.user?.name || "未知用户" }}
                <el-tag
                  v-if="member.role === 'owner'"
                  type="warning"
                  size="small"
                  >所有者</el-tag
                >
              </div>
              <div class="member-email">{{ member.user?.email || "" }}</div>
            </div>
          </div>
          <div class="member-actions">
            <el-select
              v-if="member.role !== 'owner'"
              v-model="member.role"
              size="small"
              :disabled="!canManageMembers"
              @change="handleRoleChange(member)">
              <el-option label="管理员" value="admin" />
              <el-option label="编辑者" value="editor" />
              <el-option label="评论者" value="commenter" />
              <el-option label="查看者" value="viewer" />
            </el-select>
            <el-tag v-else type="warning" size="small">所有者</el-tag>

            <el-button
              v-if="member.role !== 'owner' && canManageMembers"
              type="danger"
              size="small"
              text
              @click="handleRemoveMember(member)">
              移除
            </el-button>
          </div>
        </div>
      </div>

      <!-- 添加成员按钮 -->
      <div v-if="canManageMembers" class="add-member-section">
        <el-button type="primary" @click="showAddMemberDialog = true">
          <el-icon><Plus /></el-icon>
          添加成员
        </el-button>
      </div>
    </div>

    <template #footer>
      <el-button @click="closeDialog">关闭</el-button>
    </template>
  </el-dialog>

  <!-- 添加成员对话框 -->
  <el-dialog
    v-model="showAddMemberDialog"
    title="添加成员"
    width="600px"
    :close-on-click-modal="false">
    <el-tabs v-model="activeTab">
      <el-tab-pane label="单个添加" name="single">
        <el-form
          ref="addMemberFormRef"
          :model="addMemberForm"
          :rules="addMemberFormRules"
          label-width="80px">
          <el-form-item label="用户邮箱" prop="email">
            <el-input
              v-model="addMemberForm.email"
              placeholder="请输入用户邮箱"
              type="email" />
          </el-form-item>
          <el-form-item label="角色" prop="role">
            <el-select v-model="addMemberForm.role" placeholder="请选择角色">
              <el-option label="管理员" value="admin" />
              <el-option label="编辑者" value="editor" />
              <el-option label="评论者" value="commenter" />
              <el-option label="查看者" value="viewer" />
            </el-select>
          </el-form-item>
        </el-form>
      </el-tab-pane>

      <el-tab-pane label="批量添加" name="batch">
        <el-alert
          title="批量添加成员"
          description="每行一个邮箱地址，可选角色。格式：邮箱地址 角色（如：user@example.com editor）"
          type="info"
          :closable="false"
          show-icon />
        <el-input
          v-model="batchEmails"
          type="textarea"
          :rows="10"
          placeholder="user1@example.com editor&#10;user2@example.com viewer&#10;user3@example.com" />
      </el-tab-pane>
    </el-tabs>

    <template #footer>
      <el-button @click="showAddMemberDialog = false">取消</el-button>
      <el-button type="primary" :loading="adding" @click="handleAddMember">
        添加
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch } from "vue";
import { ElMessage, ElMessageBox } from "element-plus";
import { Plus } from "@element-plus/icons-vue";
import type { FormInstance, FormRules } from "element-plus";
import { useMemberStore, type BaseMember } from "@/stores/memberStore";

const props = defineProps<{
  baseId: string;
  visible: boolean;
}>();

const emit = defineEmits<{
  (e: "update:visible", value: boolean): void;
  (e: "member-changed"): void;
}>();

const memberStore = useMemberStore();

const dialogVisible = computed({
  get: () => props.visible,
  set: (value) => emit("update:visible", value),
});

const loading = ref(false);
const adding = ref(false);
const showAddMemberDialog = ref(false);
const activeTab = ref("single");
const batchEmails = ref("");
const canManageMembers = ref(true); // TODO: 实现权限检查

const members = ref<BaseMember[]>([]);

const addMemberFormRef = ref<FormInstance>();
const addMemberForm = reactive({
  email: "",
  role: "editor",
});

const addMemberFormRules: FormRules = {
  email: [
    { required: true, message: "请输入用户邮箱", trigger: "blur" },
    { type: "email", message: "请输入有效的邮箱地址", trigger: "blur" },
  ],
  role: [{ required: true, message: "请选择角色", trigger: "change" }],
};

// 监听对话框打开，加载成员列表
watch(
  () => props.visible,
  async (newVal) => {
    if (newVal && props.baseId) {
      await loadMembers();
    }
  },
);

// 加载成员列表
async function loadMembers() {
  loading.value = true;
  try {
    const data = await memberStore.fetchMembers(props.baseId);
    members.value = data;
    console.log("加载成员列表成功:", members.value);
  } catch (error) {
    console.error("加载成员列表失败:", error);
    ElMessage.error("加载成员列表失败");
  } finally {
    loading.value = false;
  }
}

// 处理角色变更
async function handleRoleChange(member: BaseMember) {
  try {
    await memberStore.updateMemberRole(props.baseId, member.user_id, member.role);
    ElMessage.success("成员角色已更新");
    emit("member-changed");
  } catch (error) {
    console.error("更新成员角色失败:", error);
    ElMessage.error("更新成员角色失败");
    // 恢复原角色
    await loadMembers();
  }
}

// 处理移除成员
async function handleRemoveMember(member: BaseMember) {
  try {
    await ElMessageBox.confirm(
      `确定要移除成员"${member.user?.name || "未知用户"}"吗？`,
      "确认移除",
      {
        confirmButtonText: "确定",
        cancelButtonText: "取消",
        type: "warning",
      },
    );

    await memberStore.removeMember(props.baseId, member.user_id);
    ElMessage.success("成员已移除");
    await loadMembers();
    emit("member-changed");
  } catch (error) {
    if (error !== "cancel") {
      console.error("移除成员失败:", error);
      ElMessage.error("移除成员失败");
    }
  }
}

// 处理添加成员
async function handleAddMember() {
  if (activeTab.value === "batch") {
    // 批量添加
    await handleBatchAdd();
  } else {
    // 单个添加
    await handleSingleAdd();
  }
}

// 单个添加
async function handleSingleAdd() {
  if (!addMemberFormRef.value) return;

  try {
    await addMemberFormRef.value.validate();
    adding.value = true;

    await memberStore.addMember(
      props.baseId,
      addMemberForm.email,
      addMemberForm.role,
    );
    ElMessage.success("成员添加成功");
    showAddMemberDialog.value = false;
    await loadMembers();
    emit("member-changed");

    // 重置表单
    addMemberForm.email = "";
    addMemberForm.role = "editor";
  } catch (error) {
    if (error !== "cancel") {
      console.error("添加成员失败:", error);
      ElMessage.error("添加成员失败");
    }
  } finally {
    adding.value = false;
  }
}

// 批量添加
async function handleBatchAdd() {
  if (!batchEmails.value.trim()) {
    ElMessage.warning("请输入成员邮箱列表");
    return;
  }

  try {
    adding.value = true;

    // 解析邮箱列表
    const lines = batchEmails.value.split("\n").filter((line) => line.trim());
    const members = lines.map((line) => {
      const parts = line.trim().split(/\s+/);
      const email = parts[0];
      const role = parts[1] || "editor";
      return { email, role };
    });

    if (members.length === 0) {
      ElMessage.warning("没有有效的邮箱地址");
      return;
    }

    const result = await memberStore.batchAddMembers(props.baseId, members);

    if (result.success_count > 0) {
      ElMessage.success(
        `批量添加完成：成功 ${result.success_count} 个，失败 ${result.failed_count} 个`,
      );

      if (result.failed_count > 0) {
        // 显示失败详情
        const failedDetails = result.failed
          .map((f) => `${f.email}: ${f.error}`)
          .join("\n");
        ElMessage.warning(`失败详情：\n${failedDetails}`);
      }

      showAddMemberDialog.value = false;
      await loadMembers();
      emit("member-changed");
      batchEmails.value = "";
    } else {
      ElMessage.error("批量添加失败，请检查邮箱地址格式");
    }
  } catch (error) {
    if (error !== "cancel") {
      console.error("批量添加失败:", error);
      ElMessage.error("批量添加失败");
    }
  } finally {
    adding.value = false;
  }
}

function closeDialog() {
  dialogVisible.value = false;
}
</script>

<style lang="scss" scoped>
.member-management-dialog {
  .member-content {
    min-height: 300px;
  }

  .member-list {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .member-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px;
    background: #f9fafb;
    border-radius: 8px;
    transition: all 0.3s ease;

    &:hover {
      background: #f3f4f6;
    }

    &.is-owner {
      background: #fffbeb;
      border: 1px solid #fcd34d;
    }

    .member-info {
      display: flex;
      align-items: center;
      gap: 12px;
      flex: 1;

      .member-avatar {
        flex-shrink: 0;
      }

      .member-details {
        flex: 1;
        min-width: 0;

        .member-name {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 14px;
          font-weight: 600;
          color: #1f2937;
          margin-bottom: 4px;
        }

        .member-email {
          font-size: 12px;
          color: #6b7280;
        }
      }
    }

    .member-actions {
      display: flex;
      align-items: center;
      gap: 8px;
      flex-shrink: 0;
      width: 160px;
    }
  }

  .add-member-section {
    margin-top: 24px;
    padding-top: 24px;
    border-top: 1px solid #e5e7eb;
    text-align: right;
  }
}
</style>
