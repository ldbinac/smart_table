<template>
  <el-dialog append-to-body
    :model-value="visible"
    @update:model-value="$emit('update:visible', $event)"
    :title="mode === 'create' ? t('user.addUser') : t('user.editUser')"
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
      <el-form-item :label="t('user.email')" prop="email" required>
        <el-input
          v-model="formData.email"
          :placeholder="t('user.emailPlaceholder')"
          :disabled="mode === 'edit'"
          maxlength="255"
        />
      </el-form-item>

      <el-form-item
        v-if="mode === 'create'"
        :label="t('user.password')"
        prop="password"
        required
      >
        <el-input
          v-model="formData.password"
          type="password"
          :placeholder="t('user.passwordPlaceholder')"
          show-password
          maxlength="50"
        />
      </el-form-item>

      <el-form-item :label="t('user.name')" prop="name" required>
        <el-input
          v-model="formData.name"
          :placeholder="t('user.namePlaceholder')"
          maxlength="100"
        />
      </el-form-item>

      <el-form-item :label="t('user.role')" prop="role" required>
        <el-select
          v-model="formData.role"
          :placeholder="t('user.rolePlaceholder')"
          style="width: 100%"
        >
          <el-option :label="t('user.roleAdmin')" value="admin" />
          <el-option :label="t('user.roleWorkspaceAdmin')" value="workspace_admin" />
          <el-option :label="t('user.roleEditor')" value="editor" />
          <el-option :label="t('user.roleViewer')" value="viewer" />
        </el-select>
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="handleCancel">{{ t('user.cancel') }}</el-button>
      <el-button
        type="primary"
        :loading="submitting"
        @click="handleSubmit"
      >
        {{ t('user.confirm') }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, reactive, computed, watch, nextTick } from 'vue'
import type { FormInstance, FormRules } from 'element-plus'
import { useAdminStore } from '@/stores/adminStore'
import { useI18n } from 'vue-i18n'
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

const { t } = useI18n()
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
    { required: true, message: t('user.emailRequired'), trigger: 'blur' },
    {
      type: 'email',
      message: t('user.emailInvalid'),
      trigger: 'blur'
    }
  ],
  password: props.mode === 'create' ? [
    { required: true, message: t('user.passwordRequired'), trigger: 'blur' },
    {
      min: 8,
      message: t('user.passwordTooShort'),
      trigger: 'blur'
    }
  ] : [],
  name: [
    { required: true, message: t('user.nameRequired'), trigger: 'blur' },
    {
      min: 1,
      max: 100,
      message: t('user.nameLength'),
      trigger: 'blur'
    }
  ],
  role: [
    { required: true, message: t('user.roleRequired'), trigger: 'change' }
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
