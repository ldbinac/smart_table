<template>
  <div class="email-templates-page">
    <div class="page-header">
      <h1 class="page-title">{{ t('email.title') }}</h1>
      <p class="page-description">{{ t('email.description') }}</p>
    </div>

    <div class="page-content">
      <el-card v-loading="loading">
        <el-table :data="templates" stripe style="width: 100%">
          <el-table-column prop="name" :label="t('email.templateName')" min-width="150">
            <template #default="{ row }">
              <div class="template-name">
                <span>{{ row.name }}</span>
                <el-tag v-if="row.is_default" size="small" type="info" class="ml-2">{{ t('email.default') }}</el-tag>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="template_key" :label="t('email.templateKey')" min-width="150" />
          <el-table-column prop="subject" :label="t('email.subject')" min-width="200" show-overflow-tooltip />
          <el-table-column prop="description" :label="t('email.descriptionCol')" min-width="200" show-overflow-tooltip />
          <el-table-column prop="updated_at" :label="t('email.updatedAt')" min-width="150">
            <template #default="{ row }">
              {{ formatDate(row.updated_at) }}
            </template>
          </el-table-column>
          <el-table-column :label="t('email.actions')" width="200" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="handleEdit(row as EmailTemplate)">{{ t('email.edit') }}</el-button>
              <el-button link type="primary" @click="handlePreview(row as EmailTemplate)">{{ t('email.preview') }}</el-button>
              <el-button v-if="!row.is_default" link type="danger" @click="handleDelete(row as EmailTemplate)">{{ t('email.delete') }}</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>

    <!-- 编辑模板对话框 -->
    <el-dialog
      v-model="editDialogVisible"
      :title="t('email.editTitle')"
      width="900px"
      destroy-on-close
    >
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-width="100px"
        label-position="top"
      >
        <el-form-item :label="t('email.templateName')" prop="name">
          <el-input v-model="form.name" :placeholder="t('email.templateNamePlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('email.subject')" prop="subject">
          <el-input v-model="form.subject" :placeholder="t('email.subjectPlaceholder')" />
        </el-form-item>
        <el-form-item :label="t('email.descriptionCol')" prop="description">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="2"
            :placeholder="t('email.descriptionPlaceholder')"
          />
        </el-form-item>
        <el-form-item :label="t('email.htmlContent')" prop="content_html">
          <el-tabs type="border-card">
            <el-tab-pane :label="t('email.editTab')">
              <el-input
                v-model="form.content_html"
                type="textarea"
                :rows="15"
                :placeholder="t('email.htmlPlaceholder')"
                class="code-editor"
              />
            </el-tab-pane>
            <el-tab-pane :label="t('email.previewTab')">
              <div class="html-preview" v-html="sanitizedFormHtml" />
            </el-tab-pane>
          </el-tabs>
        </el-form-item>
        <el-form-item :label="t('email.textContent')" prop="content_text">
          <el-input
            v-model="form.content_text"
            type="textarea"
            :rows="6"
            :placeholder="t('email.textPlaceholder')"
          />
        </el-form-item>
        <el-form-item>
          <div class="form-tip">
            <p><strong>{{ t('email.availableVariables') }}</strong></p>
            <p v-if="currentTemplate?.template_key === 'user_registration'">
              {{ '{{user_name}}' }} - {{ t('email.varUsername') }}, {{ '{{verification_link}}' }} - {{ t('email.varVerificationLink') }}
            </p>
            <p v-else-if="currentTemplate?.template_key === 'password_reset'">
              {{ '{{user_name}}' }} - {{ t('email.varUsername') }}, {{ '{{reset_link}}' }} - {{ t('email.varResetLink') }}
            </p>
            <p v-else-if="currentTemplate?.template_key === 'share_invitation'">
              {{ '{{sharer_name}}' }} - {{ t('email.varSharerName') }}, {{ '{{base_name}}' }} - {{ t('email.varBaseName') }}, {{ '{{base_link}}' }} - {{ t('email.varBaseLink') }}, {{ '{{permission}}' }} - {{ t('email.varPermission') }}
            </p>
            <p v-else>
              {{ '{{user_name}}' }} - {{ t('email.varUsername') }}, {{ '{{operation_time}}' }} - {{ t('email.varOperationTime') }}
            </p>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">{{ t('email.cancel') }}</el-button>
        <el-button v-if="currentTemplate?.is_default" type="warning" @click="handleReset">{{ t('email.restoreDefault') }}</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">{{ t('email.save') }}</el-button>
      </template>
    </el-dialog>

    <!-- 预览对话框 -->
    <el-dialog
      v-model="previewDialogVisible"
      :title="t('email.previewTitle')"
      width="700px"
      destroy-on-close
    >
      <div class="email-preview-container">
        <div class="preview-header">
          <div class="preview-field">
            <span class="label">{{ t('email.recipient') }}</span>
            <span>{{ t('email.userExample') }} &lt;user@example.com&gt;</span>
          </div>
          <div class="preview-field">
            <span class="label">{{ t('email.subjectLabel') }}</span>
            <span>{{ previewData.subject }}</span>
          </div>
        </div>
        <div class="preview-body" v-html="sanitizedPreviewHtml" />
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { emailApiService } from '@/services/api/emailApiService'
import { sanitizeEmailHtml } from '@/utils/sanitize'

const { t } = useI18n()

interface EmailTemplate {
  id: string
  template_key: string
  name: string
  subject: string
  content_html: string
  content_text: string
  description: string
  is_default: boolean
  created_at: string
  updated_at: string
}

const loading = ref(false)
const templates = ref<EmailTemplate[]>([])
const editDialogVisible = ref(false)
const previewDialogVisible = ref(false)
const saving = ref(false)
const formRef = ref<FormInstance>()
const currentTemplate = ref<EmailTemplate | null>(null)

const form = ref({
  name: '',
  subject: '',
  content_html: '',
  content_text: '',
  description: ''
})

const rules: FormRules = {
  name: [{ required: true, message: t('email.nameRequired'), trigger: 'blur' }],
  subject: [{ required: true, message: t('email.subjectRequired'), trigger: 'blur' }],
  content_html: [{ required: true, message: t('email.htmlRequired'), trigger: 'blur' }]
}

const previewData = ref({
  subject: '',
  content_html: ''
})

const sanitizedFormHtml = computed(() => sanitizeEmailHtml(form.value.content_html))

const sanitizedPreviewHtml = computed(() => sanitizeEmailHtml(previewData.value.content_html))

import { formatDateTime } from "@/utils/timezone";

const formatDate = (date: string) => {
  if (!date) return '-'
  return formatDateTime(date, "YYYY-MM-DD HH:mm:ss")
}

const fetchTemplates = async () => {
  loading.value = true
  try {
    const response = await emailApiService.getTemplates()
    templates.value = response.data || []
  } catch (error) {
    console.error('获取邮件模板失败:', error)
    ElMessage.error(t('email.fetchFailed'))
  } finally {
    loading.value = false
  }
}

const handleEdit = (row: EmailTemplate) => {
  currentTemplate.value = row
  form.value = {
    name: row.name,
    subject: row.subject,
    content_html: row.content_html,
    content_text: row.content_text,
    description: row.description
  }
  editDialogVisible.value = true
}

const handlePreview = (row: EmailTemplate) => {
  previewData.value = {
    subject: row.subject,
    content_html: row.content_html
      .replace(/\{\{user_name\}\}/g, t('email.sampleUser'))
      .replace(/\{\{verification_link\}\}/g, 'http://example.com/verify?token=xxx')
      .replace(/\{\{reset_link\}\}/g, 'http://example.com/reset?token=xxx')
      .replace(/\{\{base_name\}\}/g, t('email.sampleBaseName'))
      .replace(/\{\{sharer_name\}\}/g, t('email.sampleSharer'))
      .replace(/\{\{permission\}\}/g, t('email.samplePermission'))
      .replace(/\{\{operation_time\}\}/g, formatDateTime(new Date().toISOString(), "YYYY-MM-DD HH:mm:ss"))
      .replace(/\{\{admin_name\}\}/g, t('email.sampleAdmin'))
  }
  previewDialogVisible.value = true
}

const handleSave = async () => {
  if (!formRef.value || !currentTemplate.value) return
  
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    
    saving.value = true
    try {
      await emailApiService.updateTemplate(currentTemplate.value?.template_key || '', form.value)
      ElMessage.success(t('email.saveSuccess'))
      editDialogVisible.value = false
      await fetchTemplates()
    } catch (error) {
      console.error('保存模板失败:', error)
      ElMessage.error(t('email.saveFailed'))
    } finally {
      saving.value = false
    }
  })
}

const handleReset = async () => {
  if (!currentTemplate.value) return
  
  try {
    await ElMessageBox.confirm(
      t('email.restoreConfirm'),
      t('email.restoreTitle'),
      { confirmButtonText: t('email.restore'), cancelButtonText: t('email.cancel'), type: 'warning' }
    )
    
    await emailApiService.resetTemplate(currentTemplate.value.template_key)
    ElMessage.success(t('email.restoreSuccess'))
    editDialogVisible.value = false
    await fetchTemplates()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('恢复默认模板失败:', error)
      ElMessage.error(t('email.restoreFailed'))
    }
  }
}

const handleDelete = async (row: EmailTemplate) => {
  try {
    await ElMessageBox.confirm(
      t('email.deleteConfirm', { name: row.name }),
      t('email.deleteTitle'),
      { confirmButtonText: t('email.delete'), cancelButtonText: t('email.cancel'), type: 'warning' }
    )
    
    await emailApiService.deleteTemplate(row.template_key)
    ElMessage.success(t('email.deleteSuccess'))
    await fetchTemplates()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('删除模板失败:', error)
      ElMessage.error(t('email.deleteFailed'))
    }
  }
}

onMounted(() => {
  fetchTemplates()
})
</script>

<style scoped lang="scss">
.email-templates-page {
  padding: 24px;
  height: calc(100vh - 48px);
  overflow-y: auto;

  .page-header {
    margin-bottom: 24px;

    .page-title {
      font-size: 24px;
      font-weight: 600;
      margin: 0 0 8px 0;
    }

    .page-description {
      color: #666;
      margin: 0;
    }
  }

  .template-name {
    display: flex;
    align-items: center;
  }

  .code-editor {
    font-family: 'Consolas', 'Monaco', monospace;
  }

  .html-preview {
    border: 1px solid #dcdfe6;
    border-radius: 4px;
    min-height: 300px;
    max-height: 400px;
    overflow: auto;
    padding: 16px;
    background: #fff;
  }

  .form-tip {
    background: #f5f7fa;
    padding: 12px 16px;
    border-radius: 4px;
    font-size: 13px;
    color: #666;

    p {
      margin: 4px 0;
    }
  }

  .email-preview-container {
    border: 1px solid #dcdfe6;
    border-radius: 4px;
    overflow: hidden;

    .preview-header {
      background: #f5f7fa;
      padding: 16px;
      border-bottom: 1px solid #dcdfe6;

      .preview-field {
        margin-bottom: 8px;

        &:last-child {
          margin-bottom: 0;
        }

        .label {
          color: #666;
          font-weight: 500;
        }
      }
    }

    .preview-body {
      padding: 16px;
      min-height: 300px;
      max-height: 500px;
      overflow: auto;
    }
  }
}
</style>
