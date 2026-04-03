<template>
  <div class="member-management-page">
    <div class="page-header">
      <div class="header-left">
        <el-button link @click="goBack">
          <el-icon><ArrowLeft /></el-icon>
          返回
        </el-button>
        <h1 class="page-title">成员管理</h1>
      </div>
      <el-button type="primary" @click="showAddDialog = true">
        <el-icon><Plus /></el-icon>
        添加成员
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
          @page-change="handlePageChange"
        />
      </el-card>
    </div>
    
    <!-- 添加成员对话框 -->
    <AddMemberDialog
      v-model="showAddDialog"
      @submit="handleAddMember"
    />
    
    <!-- 编辑角色对话框 -->
    <el-dialog
      v-model="showEditDialog"
      title="编辑成员角色"
      width="400px"
    >
      <el-form label-width="80px">
        <el-form-item label="当前角色">
          <el-tag :type="getRoleType(editingMember?.role)">
            {{ getRoleLabel(editingMember?.role) }}
          </el-tag>
        </el-form-item>
        <el-form-item label="新角色">
          <el-select v-model="newRole" placeholder="选择新角色" style="width: 100%">
            <el-option
              v-for="role in roleOptions"
              :key="role.value"
              :label="role.label"
              :value="role.value"
            />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" :loading="updating" @click="confirmEdit">
          确认
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Plus } from '@element-plus/icons-vue'
import { ElMessageBox, ElMessage } from 'element-plus'
import MemberList from '@/components/base/MemberList.vue'
import AddMemberDialog from '@/components/base/AddMemberDialog.vue'
import { baseApiService } from '@/services/api/baseApiService'
import { useAuthStore } from '@/stores/auth/authStore'
import type { BaseMember, BaseRole } from '@/api/types'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()

const baseId = computed(() => route.params.id as string)

// 状态
const members = ref<BaseMember[]>([])
const loading = ref(false)
const total = ref(0)
const currentPage = ref(1)
const pageSize = ref(20)

const showAddDialog = ref(false)
const showEditDialog = ref(false)
const editingMember = ref<BaseMember | null>(null)
const newRole = ref<BaseRole>('editor')
const updating = ref(false)

// 权限检查
const canEdit = computed(() => {
  return authStore.hasPermission('admin')
})

const canDelete = computed(() => {
  return authStore.hasPermission('admin')
})

// 角色选项
const roleOptions = [
  { value: 'admin', label: '管理员' },
  { value: 'editor', label: '编辑者' },
  { value: 'commenter', label: '评论者' },
  { value: 'viewer', label: '查看者' }
]

const roleMap: Record<string, { label: string; type: 'success' | 'warning' | 'info' | 'danger' | '' }> = {
  owner: { label: '所有者', type: 'danger' },
  admin: { label: '管理员', type: 'warning' },
  editor: { label: '编辑者', type: 'success' },
  commenter: { label: '评论者', type: 'info' },
  viewer: { label: '查看者', type: '' }
}

const getRoleLabel = (role?: string): string => {
  return roleMap[role || '']?.label || role || ''
}

const getRoleType = (role?: string): 'success' | 'warning' | 'info' | 'danger' | '' => {
  return roleMap[role || '']?.type || ''
}

// 获取成员列表
const fetchMembers = async () => {
  loading.value = true
  try {
    const response = await baseApiService.getBaseMembers(baseId.value)
    members.value = response
    total.value = response.length
  } catch (error) {
    ElMessage.error('获取成员列表失败')
  } finally {
    loading.value = false
  }
}

// 添加成员
const handleAddMember = async (data: { userId: string; role: BaseRole }) => {
  try {
    await baseApiService.addBaseMember(baseId.value, data.userId, data.role)
    ElMessage.success('成员添加成功')
    fetchMembers()
  } catch (error) {
    ElMessage.error('添加成员失败')
  }
}

// 编辑成员
const handleEdit = (member: BaseMember) => {
  editingMember.value = member
  newRole.value = member.role
  showEditDialog.value = true
}

const confirmEdit = async () => {
  if (!editingMember.value) return
  
  updating.value = true
  try {
    await baseApiService.updateMemberRole(
      baseId.value,
      editingMember.value.id,
      newRole.value
    )
    ElMessage.success('角色更新成功')
    showEditDialog.value = false
    fetchMembers()
  } catch (error) {
    ElMessage.error('更新角色失败')
  } finally {
    updating.value = false
  }
}

// 移除成员
const handleRemove = (member: BaseMember) => {
  ElMessageBox.confirm(
    `确定要移除成员 "${member.user?.nickname || member.user?.username}" 吗？`,
    '确认移除',
    {
      confirmButtonText: '确定',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    try {
      await baseApiService.removeBaseMember(baseId.value, member.id)
      ElMessage.success('成员已移除')
      fetchMembers()
    } catch (error) {
      ElMessage.error('移除成员失败')
    }
  }).catch(() => {
    // 取消操作
  })
}

// 分页处理
const handleSizeChange = (size: number) => {
  pageSize.value = size
  currentPage.value = 1
  fetchMembers()
}

const handlePageChange = (page: number) => {
  currentPage.value = page
  fetchMembers()
}

// 返回
const goBack = () => {
  router.back()
}

onMounted(() => {
  fetchMembers()
})
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
