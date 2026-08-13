<script setup lang="ts">
import { ref, computed } from 'vue'
import { ElDialog, ElButton, ElRadioGroup, ElRadio, ElCheckbox, ElCheckboxGroup, ElMessage } from 'element-plus'
import { useI18n } from 'vue-i18n'
import { exportToExcel, exportToCSV, exportToJSON } from '@/utils/export'
import type { FieldEntity, RecordEntity } from '@/db/schema'

const { t } = useI18n()

const props = defineProps<{
  visible: boolean
  fields: FieldEntity[]
  records: RecordEntity[]
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
}>()

const exportFormat = ref<'excel' | 'csv' | 'json'>('excel')
const exportScope = ref<'all' | 'selected'>('all')
const selectedFields = ref<string[]>([])
const filename = ref('')

const allFieldIds = computed(() => props.fields.map(f => f.id))

const selectAllFields = computed({
  get: () => selectedFields.value.length === props.fields.length,
  set: (value) => {
    selectedFields.value = value ? [...allFieldIds.value] : []
  }
})

function getDefaultFilename() {
  const date = new Date().toISOString().split('T')[0]
  return t('export.defaultFilename', { date })
}

function downloadFile(content: string, mimeType: string, extension: string) {
  const blob = new Blob([content], { type: mimeType })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `${filename.value || getDefaultFilename()}.${extension}`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  URL.revokeObjectURL(url)
}

async function handleExport() {
  if (selectedFields.value.length === 0) {
    ElMessage.warning(t('export.atLeastOneField'))
    return
  }

  try {
    const fieldsToExport = props.fields.filter(f => selectedFields.value.includes(f.id))
    const recordsToExport = props.records

    switch (exportFormat.value) {
      case 'excel': {
        const buffer = await exportToExcel(recordsToExport, fieldsToExport, {})
        const blob = new Blob([buffer as BlobPart], { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' })
        const url = URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.download = `${filename.value || getDefaultFilename()}.xlsx`
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        URL.revokeObjectURL(url)
        break
      }
      case 'csv': {
        const csv = exportToCSV(recordsToExport, fieldsToExport, {})
        downloadFile(csv, 'text/csv;charset=utf-8;', 'csv')
        break
      }
      case 'json': {
        const json = exportToJSON(recordsToExport, fieldsToExport, {})
        downloadFile(json, 'application/json', 'json')
        break
      }
    }

    ElMessage.success(t('export.success'))
    emit('update:visible', false)
  } catch (error) {
    ElMessage.error(t('export.failed', { message: error instanceof Error ? error.message : '未知错误' }))
  }
}

function onDialogOpen() {
  selectedFields.value = [...allFieldIds.value]
  filename.value = ''
  exportFormat.value = 'excel'
  exportScope.value = 'all'
}
</script>

<template>
  <ElDialog
    :model-value="visible"
    @update:model-value="$emit('update:visible', $event)"
    :title="t('export.title')"
    width="500px"
    :close-on-click-modal="false"
    @open="onDialogOpen"
  >
    <div class="export-dialog">
      <!-- 导出格式 -->
      <div class="export-section">
        <div class="section-title">{{ t('export.format') }}</div>
        <ElRadioGroup v-model="exportFormat">
          <ElRadio label="excel">
            <span class="format-option">
              <span class="format-icon">📊</span>
              <span>{{ t('export.excelFormat') }}</span>
            </span>
          </ElRadio>
          <ElRadio label="csv">
            <span class="format-option">
              <span class="format-icon">📄</span>
              <span>{{ t('export.csvFormat') }}</span>
            </span>
          </ElRadio>
          <ElRadio label="json">
            <span class="format-option">
              <span class="format-icon">📝</span>
              <span>{{ t('export.jsonFormat') }}</span>
            </span>
          </ElRadio>
        </ElRadioGroup>
      </div>

      <!-- 导出范围 -->
      <div class="export-section">
        <div class="section-title">{{ t('export.scope') }}</div>
        <ElRadioGroup v-model="exportScope">
          <ElRadio label="all">{{ t('export.allRecords', { count: records.length }) }}</ElRadio>
          <ElRadio label="selected" disabled>{{ t('export.selectedRecords') }}</ElRadio>
        </ElRadioGroup>
      </div>

      <!-- 字段选择 -->
      <div class="export-section">
        <div class="section-title">
          {{ t('export.selectFields') }}
          <ElCheckbox v-model="selectAllFields" size="small" style="margin-left: 12px;">
            {{ t('export.selectAll') }}
          </ElCheckbox>
        </div>
        <ElCheckboxGroup v-model="selectedFields" class="fields-grid">
          <ElCheckbox
            v-for="field in fields"
            :key="field.id"
            :label="field.id"
          >
            {{ field.name }}
          </ElCheckbox>
        </ElCheckboxGroup>
      </div>

      <!-- 文件名 -->
      <div class="export-section">
        <div class="section-title">{{ t('export.filename') }}</div>
        <input
          v-model="filename"
          type="text"
          class="filename-input"
          :placeholder="getDefaultFilename()"
        />
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <ElButton @click="$emit('update:visible', false)">{{ t('common.cancel') }}</ElButton>
        <ElButton type="primary" @click="handleExport">
          {{ t('export.title') }}
        </ElButton>
      </div>
    </template>
  </ElDialog>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;

.export-dialog {
  .export-section {
    margin-bottom: 20px;

    &:last-child {
      margin-bottom: 0;
    }

    .section-title {
      font-weight: 500;
      color: $text-primary;
      margin-bottom: 12px;
      font-size: $font-size-base;
    }
  }

  .format-option {
    display: flex;
    align-items: center;
    gap: 8px;

    .format-icon {
      font-size: 18px;
    }
  }

  .fields-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 8px;
  }

  .filename-input {
    width: 100%;
    padding: 8px 12px;
    border: 1px solid $border-color;
    border-radius: $border-radius-md;
    font-size: $font-size-base;
    color: $text-primary;
    background: $surface-color;

    &:focus {
      outline: none;
      border-color: $primary-color;
    }

    &::placeholder {
      color: $text-disabled;
    }
  }
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>
