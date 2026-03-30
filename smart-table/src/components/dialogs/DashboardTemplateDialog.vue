<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import {
  ElDialog,
  ElButton,
  ElInput,
  // ElTabs, ElTabPane 暂时未使用
  ElEmpty,
  ElMessage,
  ElMessageBox,
  ElForm,
  ElFormItem,
  ElSelect,
  ElOption,
} from 'element-plus'
import { Star, StarFilled, Search, View, Check, Plus } from '@element-plus/icons-vue'
import { dashboardTemplateService } from '@/db/services'
import type { DashboardTemplate, Dashboard } from '@/db/schema'

const props = defineProps<{
  visible: boolean
  currentDashboard?: Dashboard
}>()

const emit = defineEmits<{
  'update:visible': [value: boolean]
  'apply': [template: DashboardTemplate]
  'save-as-template': []
}>()

// 模板列表
const templates = ref<DashboardTemplate[]>([])
const loading = ref(false)
const searchQuery = ref('')
const activeCategory = ref('all')

// 保存模板对话框
const saveDialogVisible = ref(false)
const saveForm = ref({
  name: '',
  description: '',
  category: '自定义',
})
const saveLoading = ref(false)

// 预览对话框
const previewDialogVisible = ref(false)
const previewTemplate = ref<DashboardTemplate | null>(null)

// 分类列表
const categories = [
  { label: '全部', value: 'all' },
  { label: '销售', value: '销售' },
  { label: '运营', value: '运营' },
  { label: '财务', value: '财务' },
  { label: '自定义', value: '自定义' },
  { label: '我的收藏', value: 'starred' },
]

// 分类选项（用于保存表单）
const categoryOptions = ['销售', '运营', '财务', '自定义']

// 过滤后的模板列表
const filteredTemplates = computed(() => {
  let result = templates.value

  // 按分类筛选
  if (activeCategory.value !== 'all') {
    if (activeCategory.value === 'starred') {
      result = result.filter((t) => t.isStarred)
    } else {
      result = result.filter((t) => t.category === activeCategory.value)
    }
  }

  // 按搜索词筛选
  if (searchQuery.value.trim()) {
    const query = searchQuery.value.toLowerCase()
    result = result.filter(
      (t) =>
        t.name.toLowerCase().includes(query) ||
        (t.description && t.description.toLowerCase().includes(query))
    )
  }

  return result
})

// 按分类分组的模板
const templatesByCategory = computed(() => {
  const groups: Record<string, DashboardTemplate[]> = {}
  filteredTemplates.value.forEach((template) => {
    if (!groups[template.category]) {
      groups[template.category] = []
    }
    groups[template.category].push(template)
  })
  return groups
})

// 加载模板列表
async function loadTemplates() {
  loading.value = true
  try {
    await dashboardTemplateService.initPresetTemplates()
    templates.value = await dashboardTemplateService.getAllTemplates()
  } catch (error) {
    ElMessage.error('加载模板失败')
    console.error(error)
  } finally {
    loading.value = false
  }
}

// 切换收藏状态
async function toggleStar(template: DashboardTemplate, event: Event) {
  event.stopPropagation()
  try {
    await dashboardTemplateService.toggleStar(template.id)
    template.isStarred = !template.isStarred
    ElMessage.success(template.isStarred ? '已收藏' : '已取消收藏')
  } catch (error) {
    ElMessage.error('操作失败')
  }
}

// 应用模板
async function applyTemplate(template: DashboardTemplate) {
  try {
    emit('apply', template)
    ElMessage.success('模板应用成功')
    emit('update:visible', false)
  } catch (error) {
    ElMessage.error('应用模板失败')
  }
}

// 预览模板
function preview(template: DashboardTemplate) {
  previewTemplate.value = template
  previewDialogVisible.value = true
}

// 打开保存对话框
function openSaveDialog() {
  if (!props.currentDashboard) {
    ElMessage.warning('请先选择仪表盘')
    return
  }
  saveForm.value = {
    name: `${props.currentDashboard.name} 模板`,
    description: props.currentDashboard.description || '',
    category: '自定义',
  }
  saveDialogVisible.value = true
}

// 保存为新模板
async function handleSaveTemplate() {
  if (!saveForm.value.name.trim()) {
    ElMessage.warning('请输入模板名称')
    return
  }

  if (!props.currentDashboard) {
    ElMessage.warning('请先选择仪表盘')
    return
  }

  saveLoading.value = true
  try {
    await dashboardTemplateService.createTemplateFromDashboard(
      props.currentDashboard,
      saveForm.value.name,
      saveForm.value.description,
      saveForm.value.category
    )
    ElMessage.success('模板保存成功')
    saveDialogVisible.value = false
    await loadTemplates()
  } catch (error) {
    ElMessage.error('保存模板失败')
    console.error(error)
  } finally {
    saveLoading.value = false
  }
}

// 删除模板
async function deleteTemplate(template: DashboardTemplate, event: Event) {
  event.stopPropagation()
  
  if (template.isPreset) {
    ElMessage.warning('预设模板不能删除')
    return
  }

  try {
    await ElMessageBox.confirm('确定要删除这个模板吗？', '确认删除', {
      type: 'warning',
    })
    await dashboardTemplateService.deleteTemplate(template.id)
    ElMessage.success('删除成功')
    await loadTemplates()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

// 获取模板图标
function getTemplateIcon(category: string): string {
  const iconMap: Record<string, string> = {
    '销售': '💰',
    '运营': '📊',
    '财务': '💵',
    '自定义': '🎨',
  }
  return iconMap[category] || '📋'
}

// 获取模板颜色
function getTemplateColor(category: string): string {
  const colorMap: Record<string, string> = {
    '销售': '#52c41a',
    '运营': '#1890ff',
    '财务': '#faad14',
    '自定义': '#722ed1',
  }
  return colorMap[category] || '#8c8c8c'
}

// 格式化日期
function formatDate(timestamp: number): string {
  return new Date(timestamp).toLocaleDateString('zh-CN')
}

// 监听对话框打开
watch(
  () => props.visible,
  (visible) => {
    if (visible) {
      loadTemplates()
      searchQuery.value = ''
      activeCategory.value = 'all'
    }
  }
)

onMounted(() => {
  if (props.visible) {
    loadTemplates()
  }
})
</script>

<template>
  <ElDialog
    :model-value="visible"
    @update:model-value="$emit('update:visible', $event)"
    title="仪表盘模板"
    width="900px"
    :close-on-click-modal="false"
    class="dashboard-template-dialog"
  >
    <div class="template-dialog-content">
      <!-- 顶部工具栏 -->
      <div class="toolbar">
        <div class="search-box">
          <ElInput
            v-model="searchQuery"
            placeholder="搜索模板..."
            clearable
            :prefix-icon="Search"
            class="search-input"
          />
        </div>
        <ElButton
          v-if="currentDashboard"
          type="primary"
          :icon="Plus"
          @click="openSaveDialog"
        >
          保存当前为模板
        </ElButton>
      </div>

      <!-- 分类标签 -->
      <div class="category-tabs">
        <div
          v-for="cat in categories"
          :key="cat.value"
          :class="['category-tab', { active: activeCategory === cat.value }]"
          @click="activeCategory = cat.value"
        >
          {{ cat.label }}
        </div>
      </div>

      <!-- 模板列表 -->
      <div v-loading="loading" class="templates-container">
        <template v-if="filteredTemplates.length > 0">
          <!-- 按分类分组显示 -->
          <template v-if="activeCategory === 'all' && !searchQuery">
            <div
              v-for="(groupTemplates, category) in templatesByCategory"
              :key="category"
              class="template-group"
            >
              <div class="group-title">
                <span class="group-icon">{{ getTemplateIcon(category) }}</span>
                <span>{{ category }}</span>
                <span class="group-count">({{ groupTemplates.length }})</span>
              </div>
              <div class="template-grid">
                <div
                  v-for="template in groupTemplates"
                  :key="template.id"
                  class="template-card"
                  :style="{ borderColor: getTemplateColor(template.category) }"
                >
                  <div class="card-header">
                    <div class="template-icon" :style="{ backgroundColor: getTemplateColor(template.category) + '20', color: getTemplateColor(template.category) }">
                      {{ getTemplateIcon(template.category) }}
                    </div>
                    <div class="template-actions">
                      <el-button
                        link
                        :type="template.isStarred ? 'warning' : 'default'"
                        :icon="template.isStarred ? StarFilled : Star"
                        @click="toggleStar(template, $event)"
                        class="star-btn"
                      />
                    </div>
                  </div>
                  <div class="card-body">
                    <h4 class="template-name">{{ template.name }}</h4>
                    <p v-if="template.description" class="template-desc">
                      {{ template.description }}
                    </p>
                    <div class="template-meta">
                      <span class="template-type" :class="{ preset: template.isPreset }">
                        {{ template.isPreset ? '预设' : '自定义' }}
                      </span>
                      <span class="template-date">{{ formatDate(template.updatedAt) }}</span>
                    </div>
                  </div>
                  <div class="card-footer">
                    <ElButton link :icon="View" @click="preview(template)">
                      预览
                    </ElButton>
                    <ElButton type="primary" :icon="Check" @click="applyTemplate(template)">
                      应用
                    </ElButton>
                  </div>
                  <div v-if="!template.isPreset" class="delete-btn" @click="deleteTemplate(template, $event)">
                    ×
                  </div>
                </div>
              </div>
            </div>
          </template>
          
          <!-- 搜索结果或筛选结果平铺显示 -->
          <template v-else>
            <div class="template-grid flat">
              <div
                v-for="template in filteredTemplates"
                :key="template.id"
                class="template-card"
                :style="{ borderColor: getTemplateColor(template.category) }"
              >
                <div class="card-header">
                  <div class="template-icon" :style="{ backgroundColor: getTemplateColor(template.category) + '20', color: getTemplateColor(template.category) }">
                    {{ getTemplateIcon(template.category) }}
                  </div>
                  <div class="template-actions">
                    <el-button
                      link
                      :type="template.isStarred ? 'warning' : 'default'"
                      :icon="template.isStarred ? StarFilled : Star"
                      @click="toggleStar(template, $event)"
                      class="star-btn"
                    />
                  </div>
                </div>
                <div class="card-body">
                  <h4 class="template-name">{{ template.name }}</h4>
                  <p v-if="template.description" class="template-desc">
                    {{ template.description }}
                  </p>
                  <div class="template-meta">
                    <span class="template-category">{{ template.category }}</span>
                    <span class="template-type" :class="{ preset: template.isPreset }">
                      {{ template.isPreset ? '预设' : '自定义' }}
                    </span>
                  </div>
                </div>
                <div class="card-footer">
                  <ElButton link :icon="View" @click="preview(template)">
                    预览
                  </ElButton>
                  <ElButton type="primary" :icon="Check" @click="applyTemplate(template)">
                    应用
                  </ElButton>
                </div>
                <div v-if="!template.isPreset" class="delete-btn" @click="deleteTemplate(template, $event)">
                  ×
                </div>
              </div>
            </div>
          </template>
        </template>
        
        <ElEmpty v-else description="暂无模板" />
      </div>
    </div>

    <!-- 保存模板对话框 -->
    <ElDialog
      v-model="saveDialogVisible"
      title="保存为模板"
      width="500px"
      :close-on-click-modal="false"
      append-to-body
    >
      <ElForm :model="saveForm" label-width="80px">
        <ElFormItem label="模板名称" required>
          <ElInput v-model="saveForm.name" placeholder="请输入模板名称" />
        </ElFormItem>
        <ElFormItem label="模板描述">
          <ElInput
            v-model="saveForm.description"
            type="textarea"
            :rows="3"
            placeholder="请输入模板描述（可选）"
          />
        </ElFormItem>
        <ElFormItem label="分类">
          <ElSelect v-model="saveForm.category" style="width: 100%">
            <ElOption
              v-for="cat in categoryOptions"
              :key="cat"
              :label="cat"
              :value="cat"
            />
          </ElSelect>
        </ElFormItem>
      </ElForm>
      <template #footer>
        <div class="dialog-footer">
          <ElButton @click="saveDialogVisible = false">取消</ElButton>
          <ElButton type="primary" :loading="saveLoading" @click="handleSaveTemplate">
            保存
          </ElButton>
        </div>
      </template>
    </ElDialog>

    <!-- 预览对话框 -->
    <ElDialog
      v-model="previewDialogVisible"
      :title="previewTemplate?.name || '模板预览'"
      width="700px"
      :close-on-click-modal="false"
      append-to-body
    >
      <div v-if="previewTemplate" class="preview-content">
        <div class="preview-info">
          <div class="preview-icon" :style="{ backgroundColor: getTemplateColor(previewTemplate.category) + '20', color: getTemplateColor(previewTemplate.category) }">
            {{ getTemplateIcon(previewTemplate.category) }}
          </div>
          <div class="preview-details">
            <h3>{{ previewTemplate.name }}</h3>
            <p v-if="previewTemplate.description" class="preview-desc">
              {{ previewTemplate.description }}
            </p>
            <div class="preview-tags">
              <span class="tag category">{{ previewTemplate.category }}</span>
              <span class="tag" :class="{ preset: previewTemplate.isPreset }">
                {{ previewTemplate.isPreset ? '预设模板' : '自定义模板' }}
              </span>
              <span v-if="previewTemplate.isStarred" class="tag starred">⭐ 已收藏</span>
            </div>
          </div>
        </div>
        
        <div class="preview-widgets">
          <h4>包含组件 ({{ (previewTemplate.widgets || []).length }})</h4>
          <div class="widgets-list">
            <div
              v-for="(widget, index) in previewTemplate.widgets || []"
              :key="index"
              class="widget-item"
            >
              <span class="widget-type">{{ (widget as any).type }}</span>
              <span class="widget-title">{{ (widget as any).title }}</span>
            </div>
          </div>
        </div>

        <div class="preview-layout">
          <h4>布局信息</h4>
          <div class="layout-info">
            <div class="layout-item">
              <span class="label">布局类型:</span>
              <span class="value">{{ previewTemplate.layoutType === 'grid' ? '网格布局' : '自由布局' }}</span>
            </div>
            <div v-if="previewTemplate.gridColumns" class="layout-item">
              <span class="label">网格列数:</span>
              <span class="value">{{ previewTemplate.gridColumns }}</span>
            </div>
          </div>
        </div>
      </div>
      <template #footer>
        <div class="dialog-footer">
          <ElButton @click="previewDialogVisible = false">关闭</ElButton>
          <ElButton
            v-if="previewTemplate"
            type="primary"
            :icon="Check"
            @click="applyTemplate(previewTemplate); previewDialogVisible = false"
          >
            应用此模板
          </ElButton>
        </div>
      </template>
    </ElDialog>

    <template #footer>
      <div class="dialog-footer">
        <ElButton @click="$emit('update:visible', false)">关闭</ElButton>
      </div>
    </template>
  </ElDialog>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;

.dashboard-template-dialog {
  :deep(.el-dialog__body) {
    padding: 0;
  }
}

.template-dialog-content {
  display: flex;
  flex-direction: column;
  height: 600px;
}

.toolbar {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 16px 20px;
  border-bottom: 1px solid $border-color;

  .search-box {
    flex: 1;

    .search-input {
      width: 100%;
    }
  }
}

.category-tabs {
  display: flex;
  gap: 8px;
  padding: 12px 20px;
  border-bottom: 1px solid $border-color;
  overflow-x: auto;

  .category-tab {
    padding: 6px 16px;
    border-radius: $border-radius-md;
    cursor: pointer;
    font-size: $font-size-sm;
    color: $text-secondary;
    white-space: nowrap;
    transition: all 0.2s;

    &:hover {
      background-color: $gray-100;
      color: $text-primary;
    }

    &.active {
      background-color: $primary-color;
      color: white;
    }
  }
}

.templates-container {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
}

.template-group {
  margin-bottom: 24px;

  &:last-child {
    margin-bottom: 0;
  }

  .group-title {
    display: flex;
    align-items: center;
    gap: 8px;
    font-size: $font-size-lg;
    font-weight: 500;
    color: $text-primary;
    margin-bottom: 16px;

    .group-icon {
      font-size: 20px;
    }

    .group-count {
      font-size: $font-size-sm;
      color: $text-secondary;
      font-weight: normal;
    }
  }
}

.template-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 16px;

  &.flat {
    grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  }
}

.template-card {
  position: relative;
  background: $surface-color;
  border: 1px solid $border-color;
  border-left: 4px solid;
  border-radius: $border-radius-lg;
  padding: 16px;
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    transform: translateY(-2px);

    .delete-btn {
      opacity: 1;
    }
  }

  .card-header {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 12px;

    .template-icon {
      width: 40px;
      height: 40px;
      border-radius: $border-radius-md;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 20px;
    }

    .template-actions {
      .star-btn {
        font-size: 18px;
      }
    }
  }

  .card-body {
    margin-bottom: 12px;

    .template-name {
      font-size: $font-size-base;
      font-weight: 500;
      color: $text-primary;
      margin: 0 0 8px 0;
      overflow: hidden;
      text-overflow: ellipsis;
      white-space: nowrap;
    }

    .template-desc {
      font-size: $font-size-sm;
      color: $text-secondary;
      margin: 0 0 12px 0;
      overflow: hidden;
      text-overflow: ellipsis;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      line-height: 1.5;
    }

    .template-meta {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: $font-size-xs;

      .template-type {
        padding: 2px 8px;
        border-radius: $border-radius-sm;
        background-color: $gray-100;
        color: $text-secondary;

        &.preset {
          background-color: #e6f7ff;
          color: #1890ff;
        }
      }

      .template-category {
        padding: 2px 8px;
        border-radius: $border-radius-sm;
        background-color: #f6ffed;
        color: #52c41a;
      }

      .template-date {
        color: $text-disabled;
      }
    }
  }

  .card-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding-top: 12px;
    border-top: 1px solid $border-color;
  }

  .delete-btn {
    position: absolute;
    top: 8px;
    right: 8px;
    width: 20px;
    height: 20px;
    border-radius: 50%;
    background-color: #ff4d4f;
    color: white;
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 14px;
    cursor: pointer;
    opacity: 0;
    transition: opacity 0.2s;

    &:hover {
      background-color: #ff7875;
    }
  }
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

// 预览对话框样式
.preview-content {
  .preview-info {
    display: flex;
    gap: 16px;
    margin-bottom: 24px;
    padding-bottom: 20px;
    border-bottom: 1px solid $border-color;

    .preview-icon {
      width: 64px;
      height: 64px;
      border-radius: $border-radius-lg;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 32px;
      flex-shrink: 0;
    }

    .preview-details {
      flex: 1;

      h3 {
        font-size: $font-size-lg;
        font-weight: 500;
        color: $text-primary;
        margin: 0 0 8px 0;
      }

      .preview-desc {
        font-size: $font-size-base;
        color: $text-secondary;
        margin: 0 0 12px 0;
        line-height: 1.5;
      }

      .preview-tags {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;

        .tag {
          padding: 4px 12px;
          border-radius: $border-radius-md;
          font-size: $font-size-sm;
          background-color: $gray-100;
          color: $text-secondary;

          &.category {
            background-color: #f6ffed;
            color: #52c41a;
          }

          &.preset {
            background-color: #e6f7ff;
            color: #1890ff;
          }

          &.starred {
            background-color: #fff7e6;
            color: #fa8c16;
          }
        }
      }
    }
  }

  .preview-widgets,
  .preview-layout {
    margin-bottom: 20px;

    h4 {
      font-size: $font-size-base;
      font-weight: 500;
      color: $text-primary;
      margin: 0 0 12px 0;
    }
  }

  .widgets-list {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 8px;

    .widget-item {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      background-color: $gray-50;
      border-radius: $border-radius-md;
      font-size: $font-size-sm;

      .widget-type {
        padding: 2px 8px;
        background-color: $primary-color;
        color: white;
        border-radius: $border-radius-sm;
        font-size: $font-size-xs;
        text-transform: uppercase;
      }

      .widget-title {
        color: $text-primary;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
    }
  }

  .layout-info {
    display: flex;
    flex-direction: column;
    gap: 8px;

    .layout-item {
      display: flex;
      gap: 8px;
      font-size: $font-size-sm;

      .label {
        color: $text-secondary;
      }

      .value {
        color: $text-primary;
        font-weight: 500;
      }
    }
  }
}
</style>
