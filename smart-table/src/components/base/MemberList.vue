<template>
  <div class="member-list">
    <el-table
      v-loading="loading"
      :data="members"
      style="width: 100%"
    >
      <el-table-column label="用户" min-width="200">
        <template #default="{ row }">
          <div class="user-info">
            <el-avatar :size="32" :src="row.user?.avatar_url">
              {{ row.user?.username?.charAt(0).toUpperCase() }}
            </el-avatar>
            <div class="user-details">
              <div class="username">{{ row.user?.nickname || row.user?.username }}</div>
              <div class="email">{{ row.user?.email }}</div>
            </div>
          </div>
        </template>
      </el-table-column>
      
      <el-table-column label="角色" width="150">
        <template #default="{ row }">
          <el-tag :type="getRoleType(row.role)">
            {{ getRoleLabel(row.role) }}
          </el-tag>
        </template>
      </el-table-column>
      
      <el-table-column label="加入时间" width="180">
        <template #default="{ row }">
          {{ formatDate(row.joined_at) }}
        </template>
      </el-table-column>
      
      <el-table-column label="操作" width="150" fixed="right">
        <template #default="{ row }">
          <el-button
            v-if="canEdit"
            type="primary"
            link
            size="small"
            @click="$emit('edit', row)"
          >
            编辑
          </el-button>
          <el-button
            v-if="canDelete && row.role !== 'owner'"
            type="danger"
            link
            size="small"
            @click="$emit('remove', row)"
          >
            移除
          </el-button>
        </template>
      </el-table-column>
    </el-table>
    
    <!-- 分页 -->
    <div class="pagination-container" v-if="total > 0">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50]"
        :total="total"
        layout="total, sizes, prev, pager, next"
        @size-change="$emit('size-change', $event)"
        @current-change="$emit('page-change', $event)"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import type { BaseMember, BaseRole } from '@/api/types'

const props = defineProps<{
  members: BaseMember[]
  loading?: boolean
  total?: number
  canEdit?: boolean
  canDelete?: boolean
}>()

const emit = defineEmits<{
  edit: [member: BaseMember]
  remove: [member: BaseMember]
  'size-change': [size: number]
  'page-change': [page: number]
}>()

const currentPage = defineModel<number>('currentPage', { default: 1 })
const pageSize = defineModel<number>('pageSize', { default: 20 })

const roleMap: Record<BaseRole, { label: string; type: 'success' | 'warning' | 'info' | 'danger' | '' }> = {
  owner: { label: '所有者', type: 'danger' },
  admin: { label: '管理员', type: 'warning' },
  editor: { label: '编辑者', type: 'success' },
  commenter: { label: '评论者', type: 'info' },
  viewer: { label: '查看者', type: '' }
}

const getRoleLabel = (role: BaseRole): string => {
  return roleMap[role]?.label || role
}

const getRoleType = (role: BaseRole): 'success' | 'warning' | 'info' | 'danger' | '' => {
  return roleMap[role]?.type || ''
}

const formatDate = (date: string): string => {
  return new Date(date).toLocaleDateString('zh-CN')
}
</script>

<style scoped lang="scss">
.member-list {
  .user-info {
    display: flex;
    align-items: center;
    gap: 12px;
    
    .user-details {
      .username {
        font-weight: 500;
        color: #333;
      }
      
      .email {
        font-size: 12px;
        color: #999;
      }
    }
  }
  
  .pagination-container {
    display: flex;
    justify-content: flex-end;
    margin-top: 20px;
  }
}
</style>
