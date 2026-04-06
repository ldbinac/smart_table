<template>
  <el-dialog
    :model-value="visible"
    @update:model-value="$emit('update:visible', $event)"
    :title="mode === 'create' ? '添加用户' : '编辑用户'"
    width="500px"
    :close-on-click-modal="false"
  >
    <el-form
      ref="formRef"
      :model="formData"
      :rules="formRules"
      label-width="80px"
      label-position="left"
    >
      <el-form-item label="邮箱" prop="email" required>
        <el-input
          v-model="formData.email"
          placeholder="请输入邮箱地址"
          :disabled="mode === 'edit'"
          maxlength="255"
        />
      </el-form-item>

      <el-form-item
        v-if="mode === 'create'"
        label="密码"
        prop="password"
        required
      >
        <el-input
          v-model="formData.password"
          type="password"
          placeholder="请输入密码（至少 8 位）"
          show-password
          maxlength="50"
        />
      </el-form-item>

      <el-form-item label="姓名" prop="name" required>
        <el-input
          v-model="formData.name"
          placeholder="请输入姓名"
          maxlength="100"
        />
      </el-form-item>

      <el-form-item label="角色" prop="role" required>
        <el-select
          v-model="formData.role"
          placeholder="请选择角色"
          style="width: 100%"
        >
          <el-option label="管理员" value="admin" />
          <el-option label="工作区管理员" value="workspace_admin" />
          <el-option label="编辑者" value="editor" />
          <el-option label="查看者" value="viewer" />
        </el-select>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="handleCancel">取消</el-button>
      <el-button
        type="primary"
        :loading="submitting"
        @click="handleSubmit"
      >
        确定
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, nextTick } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import { ElMessage } from 'element-plus'
import { useAdminStore } from '@/stores/adminStore'
import type { User, UserRole } from '@/api/types'

const props = defineProps<{
  visible: boolean
  mode: 'create' | 'edit'
  userData?: User | null
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  'success': []
}>()

const adminStore = useAdminStore()

const formRef = ref<FormInstance>()
const submitting = ref(false)

const formData = reactive({
  email: '',
  password: '',
  name: '',
  role: '' as UserRole
})

const formRules = computed<FormRules>(() => ({
  email: [
    { required: true, message: '请输入邮箱地址', trigger: 'blur' },
    {
      type: 'email',
      message: '请输入有效的邮箱格式',
      trigger: 'blur'
    }
  ],
  password: props.mode === 'create' ? [
    { required: true, message: '请输入密码', trigger: 'blur' },
    {
      min: 8,
      message: '密码长度至少 8 位',
      trigger: 'blur'
    }
  ] : [],
  name: [
    { required: true, message: '请输入姓名', trigger: 'blur' },
    {
      min: 1,
      max: 100,
      message: '姓名长度在 1 到 100 个字符之间',
      trigger: 'blur'
    }
  ],
  role: [
    { required: true, message: '请选择角色', trigger: 'change' }
  ]
}))

watch(
  () => props.visible,
  (visible) => {
    if (visible) {
      resetForm()
      nextTick(() => {
        formRef.value?.clearValidate()
      })
    }
  },
  { immediate: true }
)

watch(
  () => props.userData,
  (userData) => {
    if (userData && props.mode === 'edit') {
      formData.email = userData.email
      formData.name = userData.name
      formData.role = userData.role
    }
  },
  { immediate: true }
)

const resetForm = () => {
  formData.email = ''
  formData.password = ''
  formData.name = ''
  formData.role = '' as UserRole

  if (props.mode === 'edit' && props.userData) {
    formData.email = props.userData.email
    formData.name = props.userData.name
    formData.role = props.userData.role
  }
}

const handleCancel = () => {
  emit('update:visible', false)
}

const handleSubmit = async () => {
  if (!formRef.value) return

  await formRef.value.validate(async (valid) => {
    if (!valid) return

    submitting.value = true
    try {
      if (props.mode === 'create') {
        await adminStore.createUser({
          email: formData.email,
          password: formData.password,
          name: formData.name,
          role: formData.role
        })
      } else {
        if (!props.userData) return
        await adminStore.updateUser(props.userData.id, {
          email: formData.email,
          name: formData.name,
          role: formData.role
        })
      }
      emit('success')
    } catch (error) {
      console.error('用户操作失败:', error)
    } finally {
      submitting.value = false
    }
  })
}
</script>

<style scoped lang="scss">
.el-form {
  padding-top: 8px;
}
</style>
