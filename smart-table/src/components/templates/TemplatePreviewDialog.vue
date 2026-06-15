<template>
  <ElDialog
    v-model="dialogVisible"
    :title="template?.name || '模板预览'"
    width="90%"
    top="5vh"
    :close-on-click-modal="true"
    :close-on-press-escape="true"
    append-to-body
    destroy-on-close
    class="template-preview-dialog"
    @close="handleClose"
  >
    <template #header>
      <div class="preview-header">
        <span class="template-icon">{{ template?.icon }}</span>
        <div class="template-info">
          <h3 class="template-name">{{ template?.name }}</h3>
          <p class="template-description">{{ template?.description }}</p>
        </div>
      </div>
    </template>

    <div class="preview-content">
      <!-- 多表切换标签 -->
      <div v-if="template && template.tables.length > 1" class="table-tabs">
        <ElTabs v-model="activeTableIndex" type="card">
          <ElTabPane
            v-for="(table, index) in template.tables"
            :key="table.id"
            :label="table.name"
            :name="String(index)"
          />
        </ElTabs>
      </div>

      <!-- 视图切换按钮 -->
      <div class="view-switcher">
        <ElButtonGroup>
          <ElButton
            v-for="view in availableViews"
            :key="view.type"
            :type="currentViewType === view.type ? 'primary' : 'default'"
            size="small"
            @click="currentViewType = view.type"
          >
            <ElIcon><component :is="view.icon" /></ElIcon>
            {{ view.label }}
          </ElButton>
        </ElButtonGroup>
      </div>

      <!-- 预览区域 -->
      <div class="preview-area">
        <!-- 表格视图 -->
        <div v-if="currentViewType === 'table'" class="view-container">
          <div class="preview-table">
            <table>
              <thead>
                <tr>
                  <th
                    v-for="field in currentFields"
                    :key="field.id"
                    class="table-header-cell"
                  >
                    {{ field.name }}
                  </th>
                </tr>
              </thead>
              <tbody>
                <tr
                  v-for="record in currentRecords"
                  :key="record.id"
                  class="table-row"
                >
                  <td
                    v-for="field in currentFields"
                    :key="field.id"
                    class="table-cell"
                  >
                    <template v-if="field.type === 'single_select' || field.type === 'multi_select'">
                      <ElTag
                        v-for="(item, idx) in getSelectValues(record.values[field.id], field)"
                        :key="idx"
                        size="small"
                        :color="getSelectColor(item, field)"
                        class="select-tag"
                      >
                        {{ item }}
                      </ElTag>
                    </template>
                    <template v-else-if="field.type === 'progress'">
                      <ElProgress
                        :percentage="Number(record.values[field.id]) || 0"
                        :stroke-width="6"
                        style="width: 100px"
                      />
                    </template>
                    <template v-else-if="field.type === 'rating'">
                      <ElRate
                        :model-value="Number(record.values[field.id]) || 0"
                        :max="(field.options as any)?.maxRating || 5"
                        disabled
                        size="small"
                      />
                    </template>
                    <template v-else-if="field.type === 'checkbox'">
                      <ElIcon v-if="record.values[field.id]" class="checkbox-checked">
                        <Check />
                      </ElIcon>
                      <span v-else class="checkbox-unchecked">-</span>
                    </template>
                    <template v-else-if="field.type === 'date' || field.type === 'date_time'">
                      {{ formatDate(record.values[field.id]) }}
                    </template>
                    <template v-else-if="field.type === 'member'">
                      <ElAvatar v-if="record.values[field.id]" size="small" class="member-avatar">
                        {{ getMemberInitial(record.values[field.id]) }}
                      </ElAvatar>
                    </template>
                    <template v-else>
                      {{ formatCellValue(record.values[field.id], field) }}
                    </template>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- 看板视图 -->
        <div v-else-if="currentViewType === 'kanban'" class="view-container kanban-preview">
          <div class="kanban-columns">
            <div
              v-for="group in kanbanGroups"
              :key="group.id"
              class="kanban-column"
            >
              <div class="kanban-column-header">
                <span class="column-name">{{ group.name }}</span>
                <span class="column-count">{{ group.records.length }}</span>
              </div>
              <div class="kanban-cards">
                <div
                  v-for="record in group.records"
                  :key="record.id"
                  class="kanban-card"
                >
                  <div class="card-title">
                    {{ getPrimaryValue(record) }}
                  </div>
                  <div v-if="getSecondaryFields.length > 0" class="card-fields">
                    <div
                      v-for="field in getSecondaryFields.slice(0, 3)"
                      :key="field.id"
                      class="card-field"
                    >
                      <span class="field-label">{{ field.name }}:</span>
                      <span class="field-value">{{ formatCellValue(record.values[field.id], field) }}</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 日历视图 -->
        <div v-else-if="currentViewType === 'calendar'" class="view-container calendar-preview">
          <div class="calendar-placeholder">
            <ElIcon size="48"><Calendar /></ElIcon>
            <p>日历视图预览</p>
            <p class="hint">展示「{{ getDateFieldName }}」字段的日期数据</p>
          </div>
        </div>

        <!-- 画廊视图 -->
        <div v-else-if="currentViewType === 'gallery'" class="view-container gallery-preview">
          <div class="gallery-grid">
            <div
              v-for="record in currentRecords"
              :key="record.id"
              class="gallery-card"
            >
              <div class="card-cover">
                <ElIcon size="32"><Picture /></ElIcon>
              </div>
              <div class="card-content">
                <div class="card-title">{{ getPrimaryValue(record) }}</div>
                <div class="card-subtitle">
                  {{ getSecondaryValue(record) }}
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 甘特图视图 -->
        <div v-else-if="currentViewType === 'gantt'" class="view-container gantt-preview">
          <div class="gantt-placeholder">
            <ElIcon size="48"><DataLine /></ElIcon>
            <p>甘特图视图预览</p>
            <p class="hint">展示「{{ getStartDateFieldName }}」到「{{ getEndDateFieldName }}」的时间范围</p>
          </div>
        </div>
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <ElButton @click="handleClose">取消</ElButton>
        <ElButton type="primary" @click="handleConfirm">
          使用此模板
        </ElButton>
      </div>
    </template>
  </ElDialog>
</template>

<script setup lang="ts">
import { ref, computed, watch } from "vue";
import {
  ElDialog,
  ElButton,
  ElButtonGroup,
  ElTabs,
  ElTabPane,
  ElTag,
  ElProgress,
  ElRate,
  ElAvatar,
  ElIcon,
} from "element-plus";
import {
  Check,
  Calendar,
  Picture,
  DataLine,
  Grid,
  Calendar as CalendarIcon,
} from "@element-plus/icons-vue";
import type { TableTemplate, TemplateTable, TemplateField, TemplateRecord } from "@/utils/tableTemplates";
import { formatDate as tzFormatDate } from "@/utils/timezone";

interface Props {
  visible: boolean;
  template: TableTemplate | null;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  (e: "update:visible", value: boolean): void;
  (e: "confirm", template: TableTemplate): void;
  (e: "close"): void;
}>();

const dialogVisible = computed({
  get: () => props.visible,
  set: (value) => emit("update:visible", value),
});

const activeTableIndex = ref(0);
const currentViewType = ref("table");

const currentTable = computed<TemplateTable | undefined>(() => {
  if (!props.template) return undefined;
  return props.template.tables[Number(activeTableIndex.value)];
});

const currentFields = computed<TemplateField[]>(() => {
  return currentTable.value?.fields || [];
});

const currentRecords = computed<TemplateRecord[]>(() => {
  return currentTable.value?.records || [];
});

const currentViews = computed(() => {
  return currentTable.value?.views || [];
});

const availableViews = computed(() => {
  const views = [{ type: "table", label: "表格", icon: Grid }];
  
  const viewTypes = new Set(currentViews.value.map(v => v.type));
  
  if (viewTypes.has("kanban")) {
    views.push({ type: "kanban", label: "看板", icon: CalendarIcon });
  }
  if (viewTypes.has("calendar")) {
    views.push({ type: "calendar", label: "日历", icon: Calendar });
  }
  if (viewTypes.has("gallery")) {
    views.push({ type: "gallery", label: "画廊", icon: Picture });
  }
  if (viewTypes.has("gantt")) {
    views.push({ type: "gantt", label: "甘特图", icon: DataLine });
  }
  
  return views;
});

const primaryField = computed(() => {
  return currentFields.value.find(f => f.isPrimary);
});

const getSecondaryFields = computed(() => {
  return currentFields.value.filter(f => !f.isPrimary).slice(0, 5);
});

const kanbanGroupField = computed(() => {
  const kanbanView = currentViews.value.find(v => v.type === "kanban");
  if (!kanbanView) return null;
  
  const config = kanbanView.config as Record<string, unknown>;
  const groupFieldId = config?.groupFieldId as string;
  return currentFields.value.find(f => f.id === groupFieldId);
});

const kanbanGroups = computed(() => {
  if (!kanbanGroupField.value) return [];

  const field = kanbanGroupField.value;
  
  // ✅ 修复：支持两种格式 - choices（标准格式）和 options（兼容旧格式）
  const choices = (field.options as { choices?: { name: string; color: string }[] })?.choices || [];
  const options = (field.options as { options?: { name: string; color: string }[] })?.options || [];
  const allOptions = choices.length > 0 ? choices : options;
  
  if (allOptions.length === 0) return [];

  // 添加"未分组"列
  const groups = allOptions.map(opt => ({
    id: opt.name,
    name: opt.name,
    color: opt.color,
    records: currentRecords.value.filter(r => {
      const value = r.values[field.id];
      if (Array.isArray(value)) {
        return (value as any[]).includes(opt.name);
      }
      return value === opt.name;
    }),
  }));

  // 找出未分组的记录
  const groupedRecordIds = new Set<string>();
  groups.forEach(group => {
    group.records.forEach((r: TemplateRecord) => groupedRecordIds.add(r.id));
  });

  const ungroupedRecords = currentRecords.value.filter(r => !groupedRecordIds.has(r.id));
  if (ungroupedRecords.length > 0) {
    groups.push({
      id: 'uncategorized',
      name: '未分组',
      color: '#909399',
      records: ungroupedRecords,
    });
  }

  return groups;
});

const getDateFieldName = computed(() => {
  const calendarView = currentViews.value.find(v => v.type === "calendar");
  if (!calendarView) return "";
  
  const config = calendarView.config as Record<string, unknown>;
  const dateFieldId = config?.dateFieldId as string;
  const field = currentFields.value.find(f => f.id === dateFieldId);
  return field?.name || "";
});

const getStartDateFieldName = computed(() => {
  const ganttView = currentViews.value.find(v => v.type === "gantt");
  if (!ganttView) return "";
  
  const config = ganttView.config as Record<string, unknown>;
  const startDateFieldId = config?.startDateFieldId as string;
  const field = currentFields.value.find(f => f.id === startDateFieldId);
  return field?.name || "";
});

const getEndDateFieldName = computed(() => {
  const ganttView = currentViews.value.find(v => v.type === "gantt");
  if (!ganttView) return "";
  
  const config = ganttView.config as Record<string, unknown>;
  const endDateFieldId = config?.endDateFieldId as string;
  const field = currentFields.value.find(f => f.id === endDateFieldId);
  return field?.name || "";
});

watch(() => props.visible, (visible) => {
  if (visible) {
    activeTableIndex.value = 0;
    currentViewType.value = "table";
  }
});

const getSelectValues = (value: unknown, _field: TemplateField): string[] => {
  if (!value) return [];
  if (Array.isArray(value)) return value.map(String);
  return [String(value)];
};

const getSelectColor = (value: string, field: TemplateField): string => {
  // ✅ 修复：支持两种格式 - choices（标准格式）和 options（兼容旧格式）
  const choices = (field.options as { choices?: { name: string; color: string }[] })?.choices || [];
  const options = (field.options as { options?: { name: string; color: string }[] })?.options || [];
  const allOptions = choices.length > 0 ? choices : options;
  
  const option = allOptions.find(o => o.name === value);
  return option?.color || "#909399";
};

const formatDate = (value: unknown): string => {
  if (!value) return "-";
  const timestamp = Number(value);
  if (isNaN(timestamp)) return String(value);
  return tzFormatDate(timestamp, "YYYY-MM-DD");
};

const formatCellValue = (value: unknown, field: TemplateField): string => {
  if (value === null || value === undefined || value === "") return "-";
  
  if (Array.isArray(value)) {
    return value.join(", ");
  }
  
  if (typeof value === "object") {
    return JSON.stringify(value);
  }
  
  if (field.type === "number") {
    const num = Number(value);
    if (!isNaN(num)) {
      const options = field.options as { format?: string; currencySymbol?: string } | undefined;
      if (options?.format === "currency") {
        return `${options.currencySymbol || "¥"}${num.toLocaleString()}`;
      }
      return num.toLocaleString();
    }
  }
  
  return String(value);
};

const getPrimaryValue = (record: TemplateRecord): string => {
  if (!primaryField.value) return record.id;
  const value = record.values[primaryField.value.id];
  return formatCellValue(value, primaryField.value);
};

const getSecondaryValue = (record: TemplateRecord): string => {
  const secondaryFields = getSecondaryFields.value;
  if (secondaryFields.length === 0) return "";
  
  const field = secondaryFields[0];
  const value = record.values[field.id];
  return formatCellValue(value, field);
};

const getMemberInitial = (value: unknown): string => {
  if (!value) return "?";
  if (typeof value === "string") {
    return value.charAt(0).toUpperCase();
  }
  return "?";
};

const handleClose = () => {
  dialogVisible.value = false;
  emit("close");
};

const handleConfirm = () => {
  if (props.template) {
    emit("confirm", props.template);
  }
  handleClose();
};
</script>

<style scoped lang="scss">
.template-preview-dialog {
  :deep(.el-dialog__body) {
    padding: 0;
    max-height: 70vh;
    overflow-y: auto;
  }
}

.preview-header {
  display: flex;
  align-items: center;
  gap: 12px;
  
  .template-icon {
    font-size: 32px;
  }
  
  .template-info {
    .template-name {
      margin: 0;
      font-size: 18px;
      font-weight: 600;
    }
    
    .template-description {
      margin: 4px 0 0;
      font-size: 14px;
      color: var(--el-text-color-secondary);
    }
  }
}

.preview-content {
  .table-tabs {
    padding: 12px 16px 0;
    background: var(--el-fill-color-light);
  }
  
  .view-switcher {
    padding: 12px 16px;
    border-bottom: 1px solid var(--el-border-color-light);
  }
}

.preview-area {
  padding: 16px;
  min-height: 300px;
}

.preview-table {
  width: 100%;
  overflow-x: auto;
  
  table {
    width: 100%;
    border-collapse: collapse;
  }
  
  .table-header-cell {
    padding: 12px 16px;
    text-align: left;
    font-weight: 500;
    font-size: 13px;
    color: var(--el-text-color-secondary);
    background: var(--el-fill-color-light);
    border-bottom: 1px solid var(--el-border-color-lighter);
    white-space: nowrap;
  }
  
  .table-row {
    border-bottom: 1px solid var(--el-border-color-lighter);
    
    &:hover {
      background: var(--el-fill-color-light);
    }
  }
  
  .table-cell {
    padding: 10px 16px;
    font-size: 14px;
    color: var(--el-text-color-primary);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 200px;
    
    .select-tag {
      margin-right: 4px;
      margin-bottom: 2px;
      :deep(.el-tag__content) {
        color: white;
      }
    }
    
    .checkbox-checked {
      color: var(--el-color-success);
    }
    
    .checkbox-unchecked {
      color: var(--el-text-color-placeholder);
    }
    
    .member-avatar {
      background: var(--el-color-primary);
      color: white;
    }
  }
}

.kanban-preview {
  .kanban-columns {
    display: flex;
    gap: 16px;
    overflow-x: auto;
    padding-bottom: 8px;
  }
  
  .kanban-column {
    flex: 0 0 280px;
    background: var(--el-fill-color-light);
    border-radius: 8px;
    padding: 12px;
  }
  
  .kanban-column-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
    
    .column-name {
      font-weight: 500;
      font-size: 14px;
    }
    
    .column-count {
      background: var(--el-color-primary-light-8);
      color: var(--el-color-primary);
      padding: 2px 8px;
      border-radius: 10px;
      font-size: 12px;
    }
  }
  
  .kanban-cards {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }
  
  .kanban-card {
    background: white;
    border-radius: 6px;
    padding: 12px;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
    
    .card-title {
      font-weight: 500;
      font-size: 14px;
      margin-bottom: 8px;
    }
    
    .card-fields {
      .card-field {
        font-size: 12px;
        color: var(--el-text-color-secondary);
        margin-bottom: 4px;
        
        .field-label {
          margin-right: 4px;
        }
      }
    }
  }
}

.calendar-preview,
.gantt-preview {
  .calendar-placeholder,
  .gantt-placeholder {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 300px;
    color: var(--el-text-color-secondary);
    
    p {
      margin: 12px 0 0;
    }
    
    .hint {
      font-size: 12px;
      color: var(--el-text-color-placeholder);
    }
  }
}

.gallery-preview {
  .gallery-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: 16px;
  }
  
  .gallery-card {
    background: white;
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid var(--el-border-color-lighter);
    
    .card-cover {
      height: 120px;
      background: var(--el-fill-color-light);
      display: flex;
      align-items: center;
      justify-content: center;
      color: var(--el-text-color-placeholder);
    }
    
    .card-content {
      padding: 12px;
      
      .card-title {
        font-weight: 500;
        font-size: 14px;
        margin-bottom: 4px;
      }
      
      .card-subtitle {
        font-size: 12px;
        color: var(--el-text-color-secondary);
      }
    }
  }
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>
