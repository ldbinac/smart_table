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

interface WidgetPosition {
  x: number
  y: number
  w: number
  h: number
  z?: number
}

interface WidgetConfig {
  id: string
  type: string
  title: string
  tableId?: string
  fieldId?: string
  aggregation?: string
  position: WidgetPosition
  config?: Record<string, unknown>
}

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

// 获取组件类型图标
function getWidgetIcon(type: string): string {
  const iconMap: Record<string, string> = {
    kpi: '📊',
    number: '🔢',
    line: '📈',
    bar: '📊',
    pie: '🥧',
    table: '📋',
    clock: '🕐',
    realtime: '⚡',
    marquee: '📢',
    gauge: '🎯',
    map: '🗺️',
    radar: '📡',
  }
  return iconMap[type] || '📦'
}

// 获取组件类型颜色
function getWidgetColor(type: string): string {
  const colorMap: Record<string, string> = {
    kpi: '#1890ff',
    number: '#52c41a',
    line: '#722ed1',
    bar: '#fa8c16',
    pie: '#eb2f96',
    table: '#13c2c2',
    clock: '#faad14',
    realtime: '#f5222d',
    marquee: '#2f54eb',
    gauge: '#fa541c',
    map: '#52c41a',
    radar: '#722ed1',
  }
  return colorMap[type] || '#8c8c8c'
}

// 获取组件主题颜色
function getWidgetTheme(widget: WidgetConfig): string {
  const config = widget.config || {}
  const theme = config.theme as string
  if (theme) {
    const themeColors: Record<string, string> = {
      blue: '#1890ff',
      green: '#52c41a',
      orange: '#fa8c16',
      purple: '#722ed1',
      red: '#f5222d',
      cyan: '#13c2c2',
    }
    return themeColors[theme] || '#1890ff'
  }
  return getWidgetColor(widget.type)
}

// 生成模拟数据
function getMockValue(widget: WidgetConfig): string {
  const config = widget.config || {}
  const prefix = (config.prefix as string) || ''
  const suffix = (config.suffix as string) || ''
  const decimal = (config.decimal as number) || 0
  
  const mockValues: Record<string, () => number> = {
    kpi: () => Math.random() * 100000 + 50000,
    number: () => Math.random() * 1000 + 100,
    avg: () => Math.random() * 100,
    sum: () => Math.random() * 100000,
    count: () => Math.floor(Math.random() * 10000),
  }
  
  const aggregation = widget.aggregation || 'sum'
  const value = mockValues[aggregation]?.() || Math.random() * 1000
  
  return `${prefix}${value.toFixed(decimal)}${suffix}`
}

// 计算预览布局
const previewLayoutStyle = computed(() => {
  if (!previewTemplate.value) return {}
  const gridColumns = previewTemplate.value.gridColumns || 12
  return {
    gridTemplateColumns: `repeat(${gridColumns}, 1fr)`,
  }
})

// 获取组件样式
function getWidgetStyle(widget: WidgetConfig): Record<string, string> {
  const pos = widget.position
  return {
    gridColumn: `${pos.x + 1} / span ${pos.w}`,
    gridRow: `${pos.y + 1} / span ${pos.h}`,
  }
}

// 计算预览网格行数
const previewGridRows = computed(() => {
  if (!previewTemplate.value?.widgets?.length) return 6
  const widgets = previewTemplate.value.widgets as WidgetConfig[]
  const maxY = Math.max(...widgets.map((w) => w.position.y + w.position.h))
  return Math.max(maxY, 6)
})

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
      width="900px"
      :close-on-click-modal="false"
      append-to-body
      class="template-preview-dialog"
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

        <div class="preview-section">
          <h4 class="section-title">
            <span class="title-icon">🖥️</span>
            仪表盘效果预览
          </h4>
          <div class="dashboard-preview-container">
            <div 
              class="dashboard-preview-grid"
              :style="{ ...previewLayoutStyle, gridTemplateRows: `repeat(${previewGridRows}, 40px)` }"
            >
              <div
                v-for="(widget, index) in (previewTemplate.widgets || []) as WidgetConfig[]"
                :key="index"
                class="preview-widget"
                :style="{ ...getWidgetStyle(widget), borderColor: getWidgetTheme(widget) }"
              >
                <div class="widget-header">
                  <span class="widget-type-icon">{{ getWidgetIcon(widget.type) }}</span>
                  <span class="widget-title">{{ widget.title }}</span>
                </div>
                <div class="widget-body">
                  <template v-if="['kpi', 'number'].includes(widget.type)">
                    <div class="mock-kpi-value" :style="{ color: getWidgetTheme(widget) }">
                      {{ getMockValue(widget) }}
                    </div>
                  </template>
                  <template v-else-if="widget.type === 'clock'">
                    <div class="mock-clock">
                      {{ new Date().toLocaleTimeString() }}
                    </div>
                  </template>
                  <template v-else-if="['line', 'bar'].includes(widget.type)">
                    <div class="mock-chart">
                      <div class="chart-bars">
                        <div v-for="i in 8" :key="i" class="bar" :style="{ height: Math.random() * 80 + 20 + '%', backgroundColor: getWidgetTheme(widget) }"></div>
                      </div>
                    </div>
                  </template>
                  <template v-else-if="widget.type === 'pie'">
                    <div class="mock-pie">
                      <div class="pie-chart" :style="{ background: `conic-gradient(${getWidgetTheme(widget)} 0% 35%, ${getWidgetTheme(widget)}99 35% 60%, ${getWidgetTheme(widget)}66 60% 85%, ${getWidgetTheme(widget)}33 85% 100%)` }"></div>
                    </div>
                  </template>
                  <template v-else-if="widget.type === 'table'">
                    <div class="mock-table">
                      <div class="table-row header">
                        <div class="cell">列1</div>
                        <div class="cell">列2</div>
                        <div class="cell">列3</div>
                      </div>
                      <div v-for="i in 2" :key="i" class="table-row">
                        <div class="cell">-</div>
                        <div class="cell">-</div>
                        <div class="cell">-</div>
                      </div>
                    </div>
                  </template>
                  <template v-else-if="widget.type === 'realtime'">
                    <div class="mock-realtime">
                      <div class="realtime-line">
                        <svg viewBox="0 0 100 30" preserveAspectRatio="none">
                          <polyline
                            :points="Array.from({length: 20}, (_, i) => `${i * 5},${15 + Math.sin(i) * 10 + Math.random() * 5}`).join(' ')"
                            fill="none"
                            :stroke="getWidgetTheme(widget)"
                            stroke-width="2"
                          />
                        </svg>
                      </div>
                    </div>
                  </template>
                  <template v-else-if="widget.type === 'marquee'">
                    <div class="mock-marquee">
                      <span class="marquee-text">📢 系统公告：欢迎使用仪表盘模板...</span>
                    </div>
                  </template>
                  <template v-else>
                    <div class="mock-default">
                      <span class="type-label">{{ widget.type.toUpperCase() }}</span>
                    </div>
                  </template>
                </div>
              </div>
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
              <span class="widget-type">{{ (widget as WidgetConfig).type }}</span>
              <span class="widget-title">{{ (widget as WidgetConfig).title }}</span>
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

  .preview-section {
    margin-bottom: 20px;

    .section-title {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: $font-size-base;
      font-weight: 500;
      color: $text-primary;
      margin: 0 0 12px 0;

      .title-icon {
        font-size: 18px;
      }
    }
  }

  .dashboard-preview-container {
    background-color: #1a1a2e;
    border-radius: $border-radius-lg;
    padding: 16px;
    overflow: hidden;
  }

  .dashboard-preview-grid {
    display: grid;
    gap: 8px;
    min-height: 200px;
  }

  .preview-widget {
    background: linear-gradient(135deg, #2d2d44 0%, #1f1f35 100%);
    border: 1px solid;
    border-radius: $border-radius-md;
    padding: 8px;
    display: flex;
    flex-direction: column;
    overflow: hidden;
    transition: all 0.2s;

    &:hover {
      transform: scale(1.02);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.3);
    }

    .widget-header {
      display: flex;
      align-items: center;
      gap: 6px;
      margin-bottom: 4px;
      flex-shrink: 0;

      .widget-type-icon {
        font-size: 12px;
      }

      .widget-title {
        font-size: 11px;
        color: rgba(255, 255, 255, 0.8);
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
    }

    .widget-body {
      flex: 1;
      display: flex;
      align-items: center;
      justify-content: center;
      min-height: 0;
    }

    .mock-kpi-value {
      font-size: 18px;
      font-weight: 600;
      text-shadow: 0 0 10px currentColor;
    }

    .mock-clock {
      font-size: 14px;
      font-weight: 500;
      color: #fff;
      font-family: monospace;
    }

    .mock-chart {
      width: 100%;
      height: 100%;
      display: flex;
      align-items: flex-end;
      justify-content: center;
      gap: 3px;
      padding: 4px;

      .chart-bars {
        display: flex;
        align-items: flex-end;
        gap: 3px;
        width: 100%;
        height: 100%;

        .bar {
          flex: 1;
          border-radius: 2px 2px 0 0;
          opacity: 0.8;
          min-height: 4px;
        }
      }
    }

    .mock-pie {
      width: 100%;
      height: 100%;
      display: flex;
      align-items: center;
      justify-content: center;
      padding: 4px;

      .pie-chart {
        width: 50px;
        height: 50px;
        border-radius: 50%;
      }
    }

    .mock-table {
      width: 100%;
      font-size: 9px;

      .table-row {
        display: flex;
        border-bottom: 1px solid rgba(255, 255, 255, 0.1);

        &.header {
          background-color: rgba(255, 255, 255, 0.1);
          font-weight: 500;
        }

        .cell {
          flex: 1;
          padding: 2px 4px;
          color: rgba(255, 255, 255, 0.7);
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
      }
    }

    .mock-realtime {
      width: 100%;
      height: 100%;
      padding: 4px;

      .realtime-line {
        width: 100%;
        height: 100%;

        svg {
          width: 100%;
          height: 100%;
        }
      }
    }

    .mock-marquee {
      width: 100%;
      overflow: hidden;

      .marquee-text {
        font-size: 10px;
        color: rgba(255, 255, 255, 0.8);
        white-space: nowrap;
        animation: marquee 5s linear infinite;
        display: inline-block;
      }
    }

    .mock-default {
      display: flex;
      align-items: center;
      justify-content: center;

      .type-label {
        font-size: 10px;
        color: rgba(255, 255, 255, 0.5);
        padding: 4px 8px;
        background-color: rgba(255, 255, 255, 0.1);
        border-radius: 4px;
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

@keyframes marquee {
  0% {
    transform: translateX(100%);
  }
  100% {
    transform: translateX(-100%);
  }
}
</style>
