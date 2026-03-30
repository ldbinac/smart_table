import { db } from '../schema'
import type { DashboardTemplate, Dashboard } from '../schema'
import { generateId } from '../../utils/id'
import type { WidgetConfig } from './dashboardService'

export interface CreateTemplateData {
  name: string
  description?: string
  category: string
  layout?: Record<string, unknown>
  layoutType?: 'grid' | 'free'
  gridColumns?: number
  widgets?: WidgetConfig[]
}

export interface TemplateFilter {
  category?: string
  isPreset?: boolean
  isStarred?: boolean
}

// 预设模板数据
const presetTemplates: Omit<DashboardTemplate, 'id' | 'createdAt' | 'updatedAt'>[] = [
  {
    name: '销售数据大屏',
    description: '展示销售关键指标、趋势分析和区域分布',
    category: '销售',
    layoutType: 'grid',
    gridColumns: 12,
    layout: {},
    widgets: [
      {
        id: 'widget-kpi-1',
        type: 'kpi',
        title: '总销售额',
        tableId: '',
        fieldId: '',
        aggregation: 'sum',
        position: { x: 0, y: 0, w: 3, h: 2, z: 1 },
        config: {
          theme: 'blue',
          fontSize: 32,
          prefix: '¥',
          decimal: 2,
          animation: true,
        },
      },
      {
        id: 'widget-kpi-2',
        type: 'kpi',
        title: '订单数量',
        tableId: '',
        fieldId: '',
        aggregation: 'count',
        position: { x: 3, y: 0, w: 3, h: 2, z: 1 },
        config: {
          theme: 'green',
          fontSize: 32,
          animation: true,
        },
      },
      {
        id: 'widget-kpi-3',
        type: 'kpi',
        title: '客单价',
        tableId: '',
        fieldId: '',
        aggregation: 'avg',
        position: { x: 6, y: 0, w: 3, h: 2, z: 1 },
        config: {
          theme: 'orange',
          fontSize: 32,
          prefix: '¥',
          decimal: 2,
          animation: true,
        },
      },
      {
        id: 'widget-kpi-4',
        type: 'kpi',
        title: '转化率',
        tableId: '',
        fieldId: '',
        aggregation: 'avg',
        position: { x: 9, y: 0, w: 3, h: 2, z: 1 },
        config: {
          theme: 'purple',
          fontSize: 32,
          suffix: '%',
          decimal: 2,
          animation: true,
        },
      },
      {
        id: 'widget-line-1',
        type: 'line',
        title: '销售趋势',
        tableId: '',
        fieldId: '',
        aggregation: 'sum',
        position: { x: 0, y: 2, w: 8, h: 4, z: 1 },
        config: {
          showLegend: true,
          smooth: true,
          animation: true,
        },
      },
      {
        id: 'widget-pie-1',
        type: 'pie',
        title: '区域分布',
        tableId: '',
        fieldId: '',
        aggregation: 'count',
        position: { x: 8, y: 2, w: 4, h: 4, z: 1 },
        config: {
          showLegend: true,
          animation: true,
        },
      },
    ],
    isPreset: true,
    isStarred: false,
  },
  {
    name: '运营监控中心',
    description: '实时监控运营数据和系统状态',
    category: '运营',
    layoutType: 'grid',
    gridColumns: 12,
    layout: {},
    widgets: [
      {
        id: 'widget-clock-1',
        type: 'clock',
        title: '当前时间',
        tableId: '',
        fieldId: '',
        aggregation: 'count',
        position: { x: 0, y: 0, w: 2, h: 2, z: 1 },
        config: {
          fontSize: 24,
          showSeconds: true,
        },
      },
      {
        id: 'widget-realtime-1',
        type: 'realtime',
        title: '实时访问量',
        tableId: '',
        fieldId: '',
        aggregation: 'count',
        position: { x: 2, y: 0, w: 6, h: 3, z: 1 },
        config: {
          refreshInterval: 5000,
          animation: true,
        },
      },
      {
        id: 'widget-marquee-1',
        type: 'marquee',
        title: '系统公告',
        tableId: '',
        fieldId: '',
        aggregation: 'count',
        position: { x: 8, y: 0, w: 4, h: 1, z: 1 },
        config: {
          speed: 2,
          fontSize: 14,
        },
      },
      {
        id: 'widget-number-1',
        type: 'number',
        title: '在线用户',
        tableId: '',
        fieldId: '',
        aggregation: 'count',
        position: { x: 8, y: 1, w: 2, h: 2, z: 1 },
        config: {
          theme: 'blue',
          animation: true,
        },
      },
      {
        id: 'widget-number-2',
        type: 'number',
        title: '系统负载',
        tableId: '',
        fieldId: '',
        aggregation: 'avg',
        position: { x: 10, y: 1, w: 2, h: 2, z: 1 },
        config: {
          theme: 'green',
          suffix: '%',
          decimal: 1,
          animation: true,
        },
      },
    ],
    isPreset: true,
    isStarred: false,
  },
  {
    name: '财务报表概览',
    description: '展示财务关键指标和报表数据',
    category: '财务',
    layoutType: 'grid',
    gridColumns: 12,
    layout: {},
    widgets: [
      {
        id: 'widget-kpi-1',
        type: 'kpi',
        title: '营业收入',
        tableId: '',
        fieldId: '',
        aggregation: 'sum',
        position: { x: 0, y: 0, w: 4, h: 2, z: 1 },
        config: {
          theme: 'blue',
          prefix: '¥',
          decimal: 2,
          animation: true,
        },
      },
      {
        id: 'widget-kpi-2',
        type: 'kpi',
        title: '净利润',
        tableId: '',
        fieldId: '',
        aggregation: 'sum',
        position: { x: 4, y: 0, w: 4, h: 2, z: 1 },
        config: {
          theme: 'green',
          prefix: '¥',
          decimal: 2,
          animation: true,
        },
      },
      {
        id: 'widget-kpi-3',
        type: 'kpi',
        title: '毛利率',
        tableId: '',
        fieldId: '',
        aggregation: 'avg',
        position: { x: 8, y: 0, w: 4, h: 2, z: 1 },
        config: {
          theme: 'orange',
          suffix: '%',
          decimal: 2,
          animation: true,
        },
      },
      {
        id: 'widget-bar-1',
        type: 'bar',
        title: '月度收支对比',
        tableId: '',
        fieldId: '',
        aggregation: 'sum',
        position: { x: 0, y: 2, w: 6, h: 4, z: 1 },
        config: {
          showLegend: true,
          animation: true,
        },
      },
      {
        id: 'widget-table-1',
        type: 'table',
        title: '收支明细',
        tableId: '',
        fieldId: '',
        aggregation: 'sum',
        position: { x: 6, y: 2, w: 6, h: 4, z: 1 },
        config: {
          fontSize: 12,
        },
      },
    ],
    isPreset: true,
    isStarred: false,
  },
]

export class DashboardTemplateService {
  // 初始化预设模板
  async initPresetTemplates(): Promise<void> {
    const existingPresets = await db.dashboardTemplates
      .where('isPreset')
      .equals(1)
      .count()

    if (existingPresets === 0) {
      const now = Date.now()
      const templates: DashboardTemplate[] = presetTemplates.map((preset) => ({
        ...preset,
        id: generateId(),
        createdAt: now,
        updatedAt: now,
      }))

      await db.dashboardTemplates.bulkAdd(templates)
    }
  }

  // 创建自定义模板
  async createTemplate(data: CreateTemplateData): Promise<DashboardTemplate> {
    const template: DashboardTemplate = {
      id: generateId(),
      name: data.name,
      description: data.description,
      category: data.category,
      layout: data.layout || {},
      layoutType: data.layoutType || 'grid',
      gridColumns: data.gridColumns || 12,
      widgets: data.widgets || [],
      isPreset: false,
      isStarred: false,
      createdAt: Date.now(),
      updatedAt: Date.now(),
    }

    await db.dashboardTemplates.add(template)
    return template
  }

  // 从仪表盘创建模板
  async createTemplateFromDashboard(
    dashboard: Dashboard,
    name: string,
    description?: string,
    category?: string
  ): Promise<DashboardTemplate> {
    const template: DashboardTemplate = {
      id: generateId(),
      name,
      description,
      category: category || '自定义',
      layout: dashboard.layout,
      layoutType: dashboard.layoutType,
      gridColumns: dashboard.gridColumns,
      widgets: (dashboard.widgets || []) as WidgetConfig[],
      isPreset: false,
      isStarred: false,
      createdAt: Date.now(),
      updatedAt: Date.now(),
    }

    await db.dashboardTemplates.add(template)
    return template
  }

  // 获取模板
  async getTemplate(id: string): Promise<DashboardTemplate | undefined> {
    return db.dashboardTemplates.get(id)
  }

  // 获取所有模板
  async getAllTemplates(filter?: TemplateFilter): Promise<DashboardTemplate[]> {
    let collection = db.dashboardTemplates.orderBy('updatedAt').reverse()

    if (filter) {
      if (filter.category) {
        collection = db.dashboardTemplates
          .where('category')
          .equals(filter.category)
          .reverse()
      }
      if (filter.isPreset !== undefined) {
        collection = collection.filter((t) => t.isPreset === filter.isPreset)
      }
      if (filter.isStarred !== undefined) {
        collection = collection.filter((t) => t.isStarred === filter.isStarred)
      }
    }

    return collection.toArray()
  }

  // 获取模板分类列表
  async getCategories(): Promise<string[]> {
    const templates = await db.dashboardTemplates.toArray()
    const categories = new Set(templates.map((t) => t.category))
    return Array.from(categories).sort()
  }

  // 更新模板
  async updateTemplate(
    id: string,
    changes: Partial<DashboardTemplate>
  ): Promise<void> {
    await db.dashboardTemplates.update(id, {
      ...changes,
      updatedAt: Date.now(),
    })
  }

  // 删除模板
  async deleteTemplate(id: string): Promise<void> {
    const template = await this.getTemplate(id)
    if (template?.isPreset) {
      throw new Error('不能删除预设模板')
    }
    await db.dashboardTemplates.delete(id)
  }

  // 切换收藏状态
  async toggleStar(id: string): Promise<void> {
    const template = await this.getTemplate(id)
    if (template) {
      await this.updateTemplate(id, { isStarred: !template.isStarred })
    }
  }

  // 应用模板到仪表盘
  async applyTemplateToDashboard(
    templateId: string,
    _dashboard: Dashboard
  ): Promise<Partial<Dashboard>> {
    const template = await this.getTemplate(templateId)
    if (!template) {
      throw new Error('模板不存在')
    }

    return {
      layout: template.layout,
      layoutType: template.layoutType,
      gridColumns: template.gridColumns,
      widgets: template.widgets,
    }
  }

  // 搜索模板
  async searchTemplates(query: string): Promise<DashboardTemplate[]> {
    const lowerQuery = query.toLowerCase()
    const templates = await db.dashboardTemplates.toArray()

    return templates.filter(
      (t) =>
        t.name.toLowerCase().includes(lowerQuery) ||
        (t.description && t.description.toLowerCase().includes(lowerQuery)) ||
        t.category.toLowerCase().includes(lowerQuery)
    )
  }
}

export const dashboardTemplateService = new DashboardTemplateService()
