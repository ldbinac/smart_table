<script setup lang="ts">
import { ref } from 'vue'
import type { FieldEntity } from '@/db/schema'
import { ElMessage } from 'element-plus'
import { CopyDocument, Refresh, Document, DocumentChecked, ArrowRight } from '@element-plus/icons-vue'

interface Props {
  visible: boolean
  fields: FieldEntity[]
  tableName?: string
  tableId?: string
  formConfig?: {
    title?: string
    description?: string
    submitButtonText?: string
    successMessage?: string
    visibleFieldIds?: string[]
    allowMultipleSubmit?: boolean
  }
}

const props = withDefaults(defineProps<Props>(), {
  tableName: '',
  tableId: '',
  formConfig: () => ({
    title: '数据收集表单',
    description: '',
    submitButtonText: '提交',
    successMessage: '提交成功，感谢您的参与！',
    visibleFieldIds: [],
    allowMultipleSubmit: true
  })
})

const emit = defineEmits<{
  (e: 'update:visible', value: boolean): void
}>()

const activeTab = ref('link')
const shareUrl = ref('')
const isGenerating = ref(false)
const currentFormId = ref('')

// 生成分享链接
function generateShareLink() {
  isGenerating.value = true
  
  // 生成表单ID
  const formId = `form_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`
  currentFormId.value = formId
  
  // 保存表单配置到 localStorage
  saveFormConfig(formId)
  
  // 生成分享链接（使用hash路由格式）
  setTimeout(() => {
    const baseUrl = window.location.origin
    // 使用hash路由格式：/#/form/:id
    shareUrl.value = `${baseUrl}/#/form/${formId}`
    isGenerating.value = false
    ElMessage.success('分享链接已生成')
  }, 800)
}

// 保存表单配置
function saveFormConfig(formId: string) {
  // 过滤掉系统字段
  const systemFieldTypes = ['createdBy', 'createdTime', 'updatedBy', 'updatedTime', 'autoNumber']
  
  // 根据 visibleFieldIds 确定要分享的字段
  let shareableFields: FieldEntity[]
  if (props.formConfig?.visibleFieldIds && props.formConfig.visibleFieldIds.length > 0) {
    // 使用配置的可见字段
    shareableFields = props.fields.filter(f => 
      props.formConfig!.visibleFieldIds!.includes(f.id) && !systemFieldTypes.includes(f.type)
    )
  } else {
    // 默认分享所有非系统字段
    shareableFields = props.fields.filter(f => !systemFieldTypes.includes(f.type))
  }
  
  const config = {
    formId,
    tableId: props.tableId,
    tableName: props.tableName,
    fields: shareableFields,
    formConfig: props.formConfig,
    createdAt: new Date().toISOString()
  }
  
  // 保存到 localStorage
  localStorage.setItem(`form_config_${formId}`, JSON.stringify(config))
  
  // 同时保存表单ID列表，用于清理过期数据
  const formList = JSON.parse(localStorage.getItem('form_share_list') || '[]')
  formList.push({ formId, createdAt: config.createdAt })
  localStorage.setItem('form_share_list', JSON.stringify(formList))
}

// 复制链接
function copyLink() {
  if (!shareUrl.value) {
    ElMessage.warning('请先生成分享链接')
    return
  }
  
  navigator.clipboard.writeText(shareUrl.value).then(() => {
    ElMessage.success('链接已复制到剪贴板')
  }).catch(() => {
    // 降级方案
    const input = document.createElement('input')
    input.value = shareUrl.value
    document.body.appendChild(input)
    input.select()
    document.execCommand('copy')
    document.body.removeChild(input)
    ElMessage.success('链接已复制到剪贴板')
  })
}

// 导出表单为 HTML
function exportAsHtml() {
  const htmlContent = generateFormHtml()
  const blob = new Blob([htmlContent], { type: 'text/html;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${props.tableName || 'form'}_${Date.now()}.html`
  a.click()
  URL.revokeObjectURL(url)
  ElMessage.success('表单已导出为 HTML 文件')
}

// 导出表单数据为 JSON
function exportAsJson() {
  const data = {
    tableName: props.tableName,
    tableId: props.tableId,
    exportTime: new Date().toISOString(),
    fields: props.fields.map(f => ({
      id: f.id,
      name: f.name,
      type: f.type,
      required: f.options?.required,
      options: f.options
    })),
    formConfig: props.formConfig
  }
  
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `${props.tableName || 'form'}_config_${Date.now()}.json`
  a.click()
  URL.revokeObjectURL(url)
  ElMessage.success('表单配置已导出')
}

// 生成表单 HTML
function generateFormHtml(): string {
  const formFields = props.fields
    .filter(f => !['createdBy', 'createdTime', 'updatedBy', 'updatedTime', 'autoNumber'].includes(f.type))
    .map(field => {
      const required = field.options?.required ? ' required' : ''
      let inputHtml = ''
      
      switch (field.type) {
        case 'text':
          inputHtml = `<input type="text" name="${field.id}" placeholder="请输入${field.name}"${required}>`
          break
        case 'number':
          inputHtml = `<input type="number" name="${field.id}" placeholder="请输入${field.name}"${required}>`
          break
        case 'email':
          inputHtml = `<input type="email" name="${field.id}" placeholder="请输入${field.name}"${required}>`
          break
        case 'phone':
          inputHtml = `<input type="tel" name="${field.id}" placeholder="请输入${field.name}"${required}>`
          break
        case 'url':
          inputHtml = `<input type="url" name="${field.id}" placeholder="请输入${field.name}"${required}>`
          break
        case 'date':
          inputHtml = `<input type="date" name="${field.id}"${required}>`
          break
        case 'checkbox':
          inputHtml = `<input type="checkbox" name="${field.id}"${required}>`
          break
        case 'singleSelect':
          const options = (field.options?.options || []) as Array<{id: string; name: string}>
          inputHtml = `<select name="${field.id}"${required}>
            <option value="">请选择</option>
            ${options.map((opt) => `<option value="${opt.id}">${opt.name}</option>`).join('')}
          </select>`
          break
        case 'multiSelect':
          const multiOptions = (field.options?.options || []) as Array<{id: string; name: string}>
          inputHtml = `<div class="checkbox-group">
            ${multiOptions.map((opt) => `
              <label><input type="checkbox" name="${field.id}[]" value="${opt.id}"> ${opt.name}</label>
            `).join('')}
          </div>`
          break
        default:
          inputHtml = `<input type="text" name="${field.id}" placeholder="请输入${field.name}"${required}>`
      }
      
      return `
        <div class="form-field">
          <label>${field.name}${required ? ' <span class="required">*</span>' : ''}</label>
          ${inputHtml}
        </div>
      `
    }).join('')

  return `<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${props.tableName || '数据收集表单'}</title>
  <style>
    * { box-sizing: border-box; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: #f5f6f7;
      padding: 20px;
      margin: 0;
    }
    .form-container {
      max-width: 600px;
      margin: 0 auto;
      background: white;
      padding: 40px;
      border-radius: 8px;
      box-shadow: 0 2px 12px rgba(0,0,0,0.1);
    }
    h1 {
      text-align: center;
      color: #1f2329;
      margin-bottom: 30px;
    }
    .form-field {
      margin-bottom: 20px;
    }
    label {
      display: block;
      margin-bottom: 8px;
      color: #1f2329;
      font-weight: 500;
    }
    input, select, textarea {
      width: 100%;
      padding: 10px 12px;
      border: 1px solid #dee0e3;
      border-radius: 4px;
      font-size: 14px;
    }
    input:focus, select:focus, textarea:focus {
      outline: none;
      border-color: #3370ff;
    }
    .required { color: #ef4444; }
    .checkbox-group {
      display: flex;
      flex-direction: column;
      gap: 8px;
    }
    .checkbox-group label {
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: normal;
    }
    .checkbox-group input {
      width: auto;
    }
    button {
      width: 100%;
      padding: 12px;
      background: #3370ff;
      color: white;
      border: none;
      border-radius: 4px;
      font-size: 16px;
      cursor: pointer;
    }
    button:hover {
      background: #2860e0;
    }
    @media (max-width: 768px) {
      .form-container {
        padding: 20px;
      }
    }
  </style>
</head>
<body>
  <div class="form-container">
    <h1>${props.tableName || '数据收集表单'}</h1>
    <form id="dataForm">
      ${formFields}
      <button type="submit">提交</button>
    </form>
  </div>
  <script>
    document.getElementById('dataForm').addEventListener('submit', function(e) {
      e.preventDefault();
      const formData = new FormData(this);
      const data = {};
      formData.forEach((value, key) => {
        if (data[key]) {
          if (Array.isArray(data[key])) {
            data[key].push(value);
          } else {
            data[key] = [data[key], value];
          }
        } else {
          data[key] = value;
        }
      });
      console.log('Form Data:', data);
      alert('表单数据（实际应用中会提交到服务器）：\\n' + JSON.stringify(data, null, 2));
    });
  <\/script>
</body>
</html>`
}

// 复制嵌入代码
function copyEmbedCode() {
  const embedCode = `<iframe 
  src="${shareUrl.value || window.location.href}" 
  width="100%" 
  height="600" 
  frameborder="0"
  style="border: 1px solid #dee0e3; border-radius: 8px;"
></iframe>`
  
  navigator.clipboard.writeText(embedCode).then(() => {
    ElMessage.success('嵌入代码已复制')
  }).catch(() => {
    ElMessage.error('复制失败')
  })
}

function handleClose() {
  emit('update:visible', false)
  shareUrl.value = ''
  currentFormId.value = ''
  activeTab.value = 'link'
}
</script>

<template>
  <el-dialog
    :model-value="visible"
    @update:model-value="handleClose"
    title="分享表单"
    width="550px"
    :close-on-click-modal="false"
  >
    <el-tabs v-model="activeTab" class="share-tabs">
      <!-- 链接分享 -->
      <el-tab-pane label="链接分享" name="link">
        <div class="share-section">
          <p class="share-desc">生成一个分享链接，其他人可以通过链接访问并填写表单</p>
          
          <div v-if="!shareUrl" class="generate-section">
            <el-button 
              type="primary" 
              :loading="isGenerating"
              @click="generateShareLink"
            >
              生成分享链接
            </el-button>
          </div>
          
          <div v-else class="link-section">
            <el-input
              v-model="shareUrl"
              readonly
              class="link-input"
            >
              <template #append>
                <el-button @click="copyLink">
                  <el-icon><CopyDocument /></el-icon>
                  复制
                </el-button>
              </template>
            </el-input>
            
            <div class="link-actions">
              <el-button link type="primary" @click="generateShareLink">
                <el-icon><Refresh /></el-icon>
                重新生成
              </el-button>
            </div>
          </div>
        </div>
      </el-tab-pane>
      
      <!-- 嵌入代码 -->
      <el-tab-pane label="嵌入网页" name="embed">
        <div class="share-section">
          <p class="share-desc">将表单嵌入到你的网站中</p>
          
          <div v-if="!shareUrl" class="generate-section">
            <el-button 
              type="primary" 
              :loading="isGenerating"
              @click="generateShareLink"
            >
              先生成分享链接
            </el-button>
          </div>
          
          <div v-else class="embed-section">
            <el-input
              type="textarea"
              :rows="4"
              readonly
              :model-value="`<iframe src=&quot;${shareUrl}&quot; width=&quot;100%&quot; height=&quot;600&quot; frameborder=&quot;0&quot; style=&quot;border: 1px solid #dee0e3; border-radius: 8px;&quot;></iframe>`"
            />
            <el-button type="primary" class="copy-btn" @click="copyEmbedCode">
              <el-icon><CopyDocument /></el-icon>
              复制嵌入代码
            </el-button>
          </div>
        </div>
      </el-tab-pane>
      
      <!-- 导出表单 -->
      <el-tab-pane label="导出表单" name="export">
        <div class="share-section">
          <p class="share-desc">将表单导出为文件，方便离线使用或备份</p>
          
          <div class="export-options">
            <div class="export-item" @click="exportAsHtml">
              <div class="export-icon">
                <el-icon :size="32"><Document /></el-icon>
              </div>
              <div class="export-info">
                <h4>导出为 HTML</h4>
                <p>生成独立的 HTML 文件，可在浏览器中打开</p>
              </div>
              <el-icon class="export-arrow"><ArrowRight /></el-icon>
            </div>
            
            <div class="export-item" @click="exportAsJson">
              <div class="export-icon">
                <el-icon :size="32"><DocumentChecked /></el-icon>
              </div>
              <div class="export-info">
                <h4>导出配置 (JSON)</h4>
                <p>导出表单配置数据，用于备份或迁移</p>
              </div>
              <el-icon class="export-arrow"><ArrowRight /></el-icon>
            </div>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>
    
    <template #footer>
      <el-button @click="handleClose">关闭</el-button>
    </template>
  </el-dialog>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;

.share-tabs {
  :deep(.el-tabs__header) {
    margin-bottom: $spacing-lg;
  }
}

.share-section {
  min-height: 200px;
}

.share-desc {
  color: $text-secondary;
  margin-bottom: $spacing-lg;
  line-height: 1.6;
}

.generate-section {
  display: flex;
  justify-content: center;
  padding: $spacing-xl 0;
}

.link-section {
  .link-input {
    margin-bottom: $spacing-sm;
  }
  
  .link-actions {
    display: flex;
    justify-content: center;
  }
}

.embed-section {
  .copy-btn {
    margin-top: $spacing-md;
    width: 100%;
  }
}

.export-options {
  display: flex;
  flex-direction: column;
  gap: $spacing-md;
}

.export-item {
  display: flex;
  align-items: center;
  gap: $spacing-md;
  padding: $spacing-md;
  border: 1px solid $border-color;
  border-radius: $border-radius-md;
  cursor: pointer;
  transition: all 0.2s;
  
  &:hover {
    border-color: $primary-color;
    background-color: rgba($primary-color, 0.02);
  }
  
  .export-icon {
    color: $primary-color;
  }
  
  .export-info {
    flex: 1;
    
    h4 {
      margin: 0 0 $spacing-xs;
      font-size: $font-size-base;
      color: $text-primary;
    }
    
    p {
      margin: 0;
      font-size: $font-size-sm;
      color: $text-secondary;
    }
  }
  
  .export-arrow {
    color: $text-disabled;
  }
}
</style>
