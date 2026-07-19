<script setup lang="ts">
import { computed } from 'vue'
import { CircleCheck } from '@element-plus/icons-vue'
import type { FieldEntity, TableEntity } from '@/db/schema'
import type { WorkflowNode, WebhookConfig } from '@/types/workflow'
import { NODE_TYPE_ICON_MAP, NODE_TYPE_LABEL_MAP } from '@/utils/workflowNodeType'

interface Props {
  node: WorkflowNode
  fields?: FieldEntity[]
  tables?: TableEntity[]
  webhooks?: WebhookConfig[]
}

const props = defineProps<Props>()

const nodeIconMap = NODE_TYPE_ICON_MAP

const nodeTypeLabels = NODE_TYPE_LABEL_MAP

function getFieldName(fieldId?: string): string {
  if (!fieldId) return '未选择字段'
  return props.fields?.find(f => f.id === fieldId)?.name || fieldId
}

function getTableName(tableId?: string): string {
  if (!tableId) return '未选择表格'
  return props.tables?.find(t => t.id === tableId)?.name || tableId
}

function getWebhookName(webhookId?: string): string {
  if (!webhookId) return '未选择 Webhook'
  return props.webhooks?.find(w => w.id === webhookId)?.name || webhookId
}

const configEntries = computed(() => {
  const { node_type, config } = props.node
  const entries: { label: string; value: string }[] = []

  if (node_type === 'condition') {
    const conditions = (config.conditions as Array<{ field_id?: string; operator?: string; value?: unknown }>) || []
    conditions.forEach((c, index) => {
      entries.push({
        label: `条件 ${index + 1}`,
        value: `${getFieldName(c.field_id)} ${c.operator || '?'} ${String(c.value ?? '')}`
      })
    })
  }
  else if (node_type === 'update_record') {
    const mappings = (config.update_mappings as Array<{ field_id?: string; value_template?: string }>) || []
    mappings.forEach((m, index) => {
      entries.push({
        label: `更新 ${index + 1}`,
        value: `${getFieldName(m.field_id)} → ${m.value_template || '空'}`
      })
    })
  }
  else if (node_type === 'create_record') {
    entries.push({ label: '目标表格', value: getTableName(config.target_table_id as string) })
    const mappings = (config.create_record_mappings as Array<{ target_field_id?: string; source_field_id?: string; value_template?: string }>) || []
    mappings.forEach((m, index) => {
      const source = m.source_field_id ? getFieldName(m.source_field_id) : (m.value_template || '空')
      entries.push({
        label: `映射 ${index + 1}`,
        value: `${getFieldName(m.target_field_id)} ← ${source}`
      })
    })
  }
  else if (node_type === 'send_email') {
    const recipientType = config.recipient_type as string || '未配置'
    entries.push({ label: '收件人来源', value: recipientType === 'field' ? '字段' : '固定邮箱' })
    const recipientValue = (config.recipient_value as string[] | undefined) || []
    entries.push({ label: '收件人', value: recipientValue.join(', ') || '-' })
    const contentMode = config.content_mode as string || 'custom'
    entries.push({ label: '内容模式', value: contentMode === 'template' ? '邮件模板' : '自定义内容' })
    if (contentMode === 'template') {
      entries.push({ label: '邮件模板', value: config.email_template_id ? String(config.email_template_id) : '未选择' })
    } else {
      entries.push({ label: '邮件主题', value: (config.subject as string) || '-' })
      const body = (config.body as string) || ''
      entries.push({ label: '邮件正文', value: body.length > 80 ? body.substring(0, 80) + '...' : body || '-' })
    }
  }
  else if (node_type === 'webhook') {
    const mode = config.webhook_mode as string || 'inline'
    if (mode === 'existing') {
      entries.push({ label: 'Webhook', value: getWebhookName(config.webhook_id as string) })
    } else {
      const inline = (config.inline_webhook as { name?: string; url?: string; method?: string }) || {}
      entries.push({ label: '名称', value: inline.name || '未命名' })
      entries.push({ label: 'URL', value: inline.url || '-' })
      entries.push({ label: '方法', value: inline.method || '-' })
    }
  }
  else {
    entries.push({ label: '原始配置', value: JSON.stringify(config, null, 2) })
  }

  return entries
})
</script>

<template>
  <div class="node-snapshot">
    <div class="snapshot-header">
      <el-icon class="node-icon"><component :is="nodeIconMap[node.node_type] || CircleCheck" /></el-icon>
      <span class="node-name">{{ node.name }}</span>
      <el-tag size="small" type="info">{{ nodeTypeLabels[node.node_type] || node.node_type }}</el-tag>
    </div>
    <div class="snapshot-body">
      <div
        v-for="(entry, index) in configEntries"
        :key="`${entry.label}-${index}`"
        class="snapshot-row">
        <span class="row-label">{{ entry.label }}：</span>
        <span class="row-value">{{ entry.value }}</span>
      </div>
      <div v-if="configEntries.length === 0" class="snapshot-empty">暂无配置</div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.node-snapshot {
  padding: $spacing-sm 0;
}
.snapshot-header {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  margin-bottom: $spacing-sm;
}
.node-icon {
  color: $primary-color;
}
.node-name {
  font-weight: 500;
  color: $text-primary;
}
.snapshot-body {
  padding-left: 28px;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.snapshot-row {
  display: flex;
  font-size: $font-size-sm;
}
.row-label {
  color: $text-secondary;
  min-width: 80px;
}
.row-value {
  color: $text-primary;
  word-break: break-all;
}
.snapshot-empty {
  font-size: $font-size-sm;
  color: $text-disabled;
}
</style>
