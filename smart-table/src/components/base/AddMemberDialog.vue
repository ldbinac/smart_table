<template>
  <el-dialog
    v-model="visible"
    title="添加成员"
    width="500px"
    :close-on-click-modal="false"
  >
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="80px"
    >
      <el-form-item label="用户" prop="userId">
        <el-select
          v-model="form.userId"
          filterable
          remote
          placeholder="搜索用户邮箱或用户名"
          :remote-method="searchUsers"
          :loading="searching"
          style="width: 100%"
        >
          <el-option
            v-for="user in userOptions"
            :key="user.id"
            :label="`${user.nickname || user.username} (${user.email})`"
            :value="user.id"
          >
            <div class="user-option">
              <el-avatar :size="24" :src="user.avatar_url">
                {{ user.username?.charAt(0).toUpperCase() }}
              </el-avatar>
              <span class="user-name">{{ user.nickname || user.username }}</span>
              <span class="user-email">{{ user.email }}</span>
            </div>
          </el-option>
        </el-select>
      </el-form-item>
      
      <el-form-item label="角色" prop="role">
        <el-select v-model="form.role" placeholder="选择角色" style="width: 100%">
          <el-option
            v-for="role in roleOptions"
            :key="role.value"
            :label="role.label"
            :value="role.value"
          >
            <div class="role-option">
              <span class="role-label">{{ role.label }}</span>
              <span class="role-desc">{{ role.description }}</span>
            </div>
          </el-option>
        </el-select>
      </el-form-item>
    </el-form>
    
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="submitting" @click="handleSubmit">
        添加
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import type { User, BaseRole } from '@/api/types'

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  submit: [data: { userId: string; role: BaseRole }]
}>()

const visible = computed({
  get: () => props.modelValue,
  set: (value) => emit('update:modelValue', value)
})

const formRef = ref<FormInstance>()
const searching = ref(false)
const submitting = ref(false)
const userOptions = ref<User[]>([])

const form = reactive({
  userId: '',
  role: 'editor' as BaseRole
})

const rules: FormRules = {
  userId: [{ required: true, message: '请选择用户', trigger: 'change' }],
  role: [{ required: true, message: '请选择角色', trigger: 'change' }]
}

const roleOptions = [
  { value: 'admin', label: '管理员', description: '可以管理Base设置和成员' },
  { value: 'editor', label: '编辑者', description: '可以创建、编辑、删除记录和视图' },
  { value: 'commenter', label: '评论者', description: '可以查看数据并添加评论' },
  { value: 'viewer', label: '查看者', description: '只能查看数据' }
]

// 搜索用户
const searchUsers = async (query: string) => {
  if (query.length < 2) return
  
  searching.value = true
  try {
    // TODO: 调用用户搜索API
    // const response = await userApiService.searchUsers(query)
    // userOptions.value = response.data
    
    // 模拟数据
    userOptions.value = [
      { id: '1', username: 'user1', email: 'user1@example.com', nickname: '用户1', role: 'user', status: 'active', created_at: '', updated_at: '' },
      { id: '2', username: 'user2', email: 'user2@example.com', nickname: '用户2', role: 'user', status: 'active', created_at: '', updated_at: '' }
    ]
  } finally {
    searching.value = false
  }
}

const handleSubmit = async () => {
  if (!formRef.value) return
  
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return
  
  submitting.value = true
  try {
    emit('submit', {
      userId: form.userId,
      role: form.role
    })
    visible.value = false
    // 重置表单
    form.userId = ''
    form.role = 'editor'
  } finally {
    submitting.value = false
  }
}
</script>

<style scoped lang="scss">
.user-option {
  display: flex;
  align-items: center;
  gap: 8px;
  
  .user-name {
    font-weight: 500;
  }
  
  .user-email {
    color: #999;
    font-size: 12px;
  }
}

.role-option {
  display: flex;
  flex-direction: column;
  
  .role-label {
    font-weight: 500;
  }
  
  .role-desc {
    color: #999;
    font-size: 12px;
  }
}
</style>
