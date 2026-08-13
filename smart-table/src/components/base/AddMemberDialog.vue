<template>
  <el-dialog
    v-model="visible"
    :title="t('member.addMember')"
    width="500px"
    :close-on-click-modal="false"
  >
    <el-form
      ref="formRef"
      :model="form"
      :rules="rules"
      label-width="80px"
    >
      <el-form-item :label="t('member.user')" prop="userId">
        <el-select
          v-model="form.userId"
          filterable
          remote
          :placeholder="t('member.searchUserPlaceholder')"
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
      
      <el-form-item :label="t('member.role')" prop="role">
        <el-select v-model="form.role" :placeholder="t('member.selectRolePlaceholder')" style="width: 100%">
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
      <el-button @click="visible = false">{{ t('member.cancel') }}</el-button>
      <el-button type="primary" :loading="submitting" @click="handleSubmit">
        {{ t('member.add') }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import type { User, MemberRole } from '@/api/types'
import { useI18n } from 'vue-i18n'

const { t } = useI18n()

const props = defineProps<{
  modelValue: boolean
}>()

const emit = defineEmits<{
  'update:modelValue': [value: boolean]
  submit: [data: { userId: string; role: MemberRole }]
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
  role: 'editor' as MemberRole
})

const rules: FormRules = {
  userId: [{ required: true, message: t('member.selectUser'), trigger: 'change' }],
  role: [{ required: true, message: t('member.selectRole'), trigger: 'change' }]
}

const roleOptions = [
  { value: 'admin', label: t('member.roleAdmin'), description: t('member.descAdmin') },
  { value: 'editor', label: t('member.roleEditor'), description: t('member.descEditor') },
  { value: 'commenter', label: t('member.roleCommenter'), description: t('member.descCommenter') },
  { value: 'viewer', label: t('member.roleViewer'), description: t('member.descViewer') }
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
      { id: '1', username: 'user1', email: 'user1@example.com', nickname: '用户1', name: '用户1', avatar_url: 'avatar1.png', role: 'viewer', status: 'active', email_verified: true, created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z' },
      { id: '2', username: 'user2', email: 'user2@example.com', nickname: '用户2', name: '用户2', avatar_url: 'avatar2.png', role: 'viewer', status: 'active', email_verified: true, created_at: '2024-01-01T00:00:00Z', updated_at: '2024-01-01T00:00:00Z' }
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
