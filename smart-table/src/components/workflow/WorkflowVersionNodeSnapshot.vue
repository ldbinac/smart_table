<script setup lang="ts">
import { computed } from 'vue'
import { CircleCheck } from '@element-plus/icons-vue'
import type { FieldEntity, TableEntity } from '@/db/schema'
import type { WorkflowNode, WebhookConfig } from '@/types/workflow'
import { NODE_TYPE_ICON_MAP, NODE_TYPE_LABEL_MAP } from '@/utils/workflowNodeType'
import { useI18n } from 'vue-i18n'

interface Props {
  node: WorkflowNode
  fields?: FieldEntity[]
  tables?: TableEntity[]
  webhooks?: WebhookConfig[]
}

const props = defineProps<Props>()
const { t } = useI18n()

const nodeIconMap = NODE_TYPE_ICON_MAP

const nodeTypeLabels = NODE_TYPE_LABEL_MAP

function getFieldName(fieldId?: string): string {
  if (!fieldId) return t('workflow.version.unselectedField')
  return props.fields?.find(f => f.id === fieldId)?.name || fieldId
}

function getTableName(tableId?: string): string {
  if (!tableId) return t('workflow.version.unselectedTable')
  return props.tables?.find(t => t.id === tableId)?.name || tableId
}

function getWebhookName(webhookId?: string): string {
  if (!webhookId) return t('workflow.version.unselectedWebhook')
  return props.webhooks?.find(w => w.id === webhookId)?.name || webhookId
}

const configEntries = computed(() => {
  const { node_type, config } = props.node
  const entries: { label: string; value: string }[] = []

  if (node_type === 'condition') {
    const conditions = (config.conditions as Array<{ field_id?: string; operator?: string; value?: unknown }>) || []
    conditions.forEach((c, index) => {
      entries.push({
        label: t('workflow.version.condition') + ` ${index + 1}`,
        value: `${getFieldName(c.field_id)} ${c.operator || '?'} ${String(c.value ?? '')}`
      })
    })
  }
  else if (node_type === 'update_record') {
    const mappings = (config.update_mappings as Array<{ field_id?: string; value_template?: string }>) || []
    mappings.forEach((m, index) => {
      entries.push({
        label: t('workflow.version.update') + ` ${index + 1}`,
        value: `${getFieldName(m.field_id)} → ${m.value_template || t('workflow.version.empty')}`
      })
    })
  }
  else if (node_type === 'create_record') {
    entries.push({ label: t('workflow.version.targetTable'), value: getTableName(config.target_table_id as string) })
    const mappings = (config.create_record_mappings as Array<{ target_field_id?: string; source_field_id?: string; value_template?: string }>) || []
    mappings.forEach((m, index) => {
      const source = m.source_field_id ? getFieldName(m.source_field_id) : (m.value_template || t('workflow.version.empty'))
      entries.push({
        label: t('workflow.version.mapping') + ` ${index + 1}`,
        value: `${getFieldName(m.target_field_id)} ← ${source}`
      })
    })
  }
  else if (node_type === 'send_email') {
    const recipientType = config.recipient_type as string || '未配置'
    entries.push({ label: t('workflow.version.recipientSource'), value: recipientType === 'field' ? t('workflow.version.fieldRecipient') : t('workflow.version.fixedEmail') })
    const recipientValue = (config.recipient_value as string[] | undefined) || []
    entries.push({ label: t('workflow.version.recipients'), value: recipientValue.join(', ') || '-' })
    const contentMode = config.content_mode as string || 'custom'
    entries.push({ label: t('workflow.version.contentMode'), value: contentMode === 'template' ? t('workflow.version.emailTemplate') : t('workflow.version.customContent') })
    if (contentMode === 'template') {
      entries.push({ label: t('workflow.version.emailTemplate'), value: config.email_template_id ? String(config.email_template_id) : t('workflow.version.notSelected') })
    } else {
      entries.push({ label: t('workflow.version.emailSubject'), value: (config.subject as string) || '-' })
      const body = (config.body as string) || ''
      entries.push({ label: t('workflow.version.emailBody'), value: body.length > 80 ? body.substring(0, 80) + '...' : body || '-' })
    }
  }
  else if (node_type === 'webhook') {
    const mode = config.webhook_mode as string || 'inline'
    if (mode === 'existing') {
      entries.push({ label: t('workflow.version.webhookName'), value: getWebhookName(config.webhook_id as string) })
    } else {
      const inline = (config.inline_webhook as { name?: string; url?: string; method?: string }) || {}
      entries.push({ label: t('workflow.version.webhookName'), value: inline.name || t('workflow.version.unnamed') })
      entries.push({ label: t('workflow.version.webhookUrl'), value: inline.url || '-' })
      entries.push({ label: t('workflow.version.webhookMethod'), value: inline.method || '-' })
    }
  }
  else {
    entries.push({ label: t('workflow.version.rawConfig'), value: JSON.stringify(config, null, 2) })
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
      <div v-if="configEntries.length === 0" class="snapshot-empty">{{ t('workflow.version.snapshotEmpty') }}</div>
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
