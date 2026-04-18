<template>
  <div class="email-templates-page">
    <div class="page-header">
      <h1 class="page-title">邮件模板管理</h1>
      <p class="page-description">管理系统邮件模板，支持自定义邮件内容和样式</p>
    </div>

    <div class="page-content">
      <el-card v-loading="loading">
        <el-table :data="templates" stripe style="width: 100%">
          <el-table-column prop="name" label="模板名称" min-width="150">
            <template #default="{ row }">
              <div class="template-name">
                <span>{{ row.name }}</span>
                <el-tag v-if="row.is_default" size="small" type="info" class="ml-2">默认</el-tag>
              </div>
            </template>
          </el-table-column>
          <el-table-column prop="template_key" label="模板标识" min-width="150" />
          <el-table-column prop="subject" label="邮件主题" min-width="200" show-overflow-tooltip />
          <el-table-column prop="description" label="描述" min-width="200" show-overflow-tooltip />
          <el-table-column prop="updated_at" label="更新时间" min-width="150">
            <template #default="{ row }">
              {{ formatDate(row.updated_at) }}
            </template>
          </el-table-column>
          <el-table-column label="操作" width="200" fixed="right">
            <template #default="{ row }">
              <el-button link type="primary" @click="handleEdit(row)">编辑</el-button>
              <el-button link type="primary" @click="handlePreview(row)">预览</el-button>
              <el-button v-if="!row.is_default" link type="danger" @click="handleDelete(row)">删除</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-card>
    </div>

    <!-- 编辑模板对话框 -->
    <el-dialog
      v-model="editDialogVisible"
      title="编辑邮件模板"
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
        <el-form-item label="模板名称" prop="name">
          <el-input v-model="form.name" placeholder="请输入模板名称" />
        </el-form-item>
        <el-form-item label="邮件主题" prop="subject">
          <el-input v-model="form.subject" placeholder="请输入邮件主题" />
        </el-form-item>
        <el-form-item label="描述" prop="description">
          <el-input
            v-model="form.description"
            type="textarea"
            :rows="2"
            placeholder="请输入模板描述"
          />
        </el-form-item>
        <el-form-item label="HTML内容" prop="content_html">
          <el-tabs type="border-card">
            <el-tab-pane label="编辑">
              <el-input
                v-model="form.content_html"
                type="textarea"
                :rows="15"
                placeholder="请输入HTML格式的邮件内容"
                class="code-editor"
              />
            </el-tab-pane>
            <el-tab-pane label="预览">
              <div class="html-preview" v-html="sanitizedFormHtml" />
            </el-tab-pane>
          </el-tabs>
        </el-form-item>
        <el-form-item label="纯文本内容" prop="content_text">
          <el-input
            v-model="form.content_text"
            type="textarea"
            :rows="6"
            placeholder="请输入纯文本格式的邮件内容（用于不支持HTML的邮件客户端）"
          />
        </el-form-item>
        <el-form-item>
          <div class="form-tip">
            <p><strong>可用变量：</strong></p>
            <p v-if="currentTemplate?.template_key === 'user_registration'" v-pre>
              {{user_name}} - 用户名, {{verification_link}} - 验证链接
            </p>
            <p v-else-if="currentTemplate?.template_key === 'password_reset'" v-pre>
              {{user_name}} - 用户名, {{reset_link}} - 重置链接
            </p>
            <p v-else-if="currentTemplate?.template_key === 'share_invitation'" v-pre>
              {{sharer_name}} - 分享者名称, {{base_name}} - 多维表名称, {{base_link}} - 访问链接, {{permission}} - 权限
            </p>
            <p v-else v-pre>
              {{user_name}} - 用户名, {{operation_time}} - 操作时间
            </p>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialogVisible = false">取消</el-button>
        <el-button v-if="currentTemplate?.is_default" type="warning" @click="handleReset">恢复默认</el-button>
        <el-button type="primary" :loading="saving" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>

    <!-- 预览对话框 -->
    <el-dialog
      v-model="previewDialogVisible"
      title="邮件预览"
      width="700px"
      destroy-on-close
    >
      <div class="email-preview-container">
        <div class="preview-header">
          <div class="preview-field">
            <span class="label">收件人：</span>
            <span>用户示例 &lt;user@example.com&gt;</span>
          </div>
          <div class="preview-field">
            <span class="label">主题：</span>
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
import { ElMessage, ElMessageBox } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { emailApiService } from '@/services/api/emailApiService'
import { sanitizeEmailHtml } from '@/utils/sanitize'

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
  name: [{ required: true, message: '请输入模板名称', trigger: 'blur' }],
  subject: [{ required: true, message: '请输入邮件主题', trigger: 'blur' }],
  content_html: [{ required: true, message: '请输入HTML内容', trigger: 'blur' }]
}

const previewData = ref({
  subject: '',
  content_html: ''
})

const sanitizedFormHtml = computed(() => sanitizeEmailHtml(form.value.content_html))

const sanitizedPreviewHtml = computed(() => sanitizeEmailHtml(previewData.value.content_html))

const formatDate = (date: string) => {
  if (!date) return '-'
  return new Date(date).toLocaleString('zh-CN')
}

const fetchTemplates = async () => {
  loading.value = true
  try {
    const response = await emailApiService.getTemplates()
    templates.value = response.data || []
  } catch (error) {
    console.error('获取邮件模板失败:', error)
    ElMessage.error('获取邮件模板失败')
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
      .replace(/\{\{user_name\}\}/g, '张三')
      .replace(/\{\{verification_link\}\}/g, 'http://example.com/verify?token=xxx')
      .replace(/\{\{reset_link\}\}/g, 'http://example.com/reset?token=xxx')
      .replace(/\{\{base_name\}\}/g, '示例多维表')
      .replace(/\{\{sharer_name\}\}/g, '李四')
      .replace(/\{\{permission\}\}/g, '编辑权限')
      .replace(/\{\{operation_time\}\}/g, new Date().toLocaleString('zh-CN'))
      .replace(/\{\{admin_name\}\}/g, '系统管理员')
  }
  previewDialogVisible.value = true
}

const handleSave = async () => {
  if (!formRef.value || !currentTemplate.value) return
  
  await formRef.value.validate(async (valid) => {
    if (!valid) return
    
    saving.value = true
    try {
      await emailApiService.updateTemplate(currentTemplate.value.template_key, form.value)
      ElMessage.success('保存成功')
      editDialogVisible.value = false
      await fetchTemplates()
    } catch (error) {
      console.error('保存模板失败:', error)
      ElMessage.error('保存失败')
    } finally {
      saving.value = false
    }
  })
}

const handleReset = async () => {
  if (!currentTemplate.value) return
  
  try {
    await ElMessageBox.confirm(
      '确定要恢复默认模板吗？这将覆盖您当前的修改。',
      '恢复默认',
      { confirmButtonText: '恢复', cancelButtonText: '取消', type: 'warning' }
    )
    
    await emailApiService.resetTemplate(currentTemplate.value.template_key)
    ElMessage.success('已恢复默认模板')
    editDialogVisible.value = false
    await fetchTemplates()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('恢复默认模板失败:', error)
      ElMessage.error('恢复失败')
    }
  }
}

const handleDelete = async (row: EmailTemplate) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除模板 "${row.name}" 吗？`,
      '删除确认',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
    
    await emailApiService.deleteTemplate(row.template_key)
    ElMessage.success('删除成功')
    await fetchTemplates()
  } catch (error: any) {
    if (error !== 'cancel') {
      console.error('删除模板失败:', error)
      ElMessage.error('删除失败')
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
