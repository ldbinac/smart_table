import { db } from '../schema';
import type { Dashboard } from '../schema';
import { generateId } from '../../utils/id';

export interface WidgetConfig {
  id: string
  type: 'bar' | 'line' | 'pie' | 'number' | 'table' | 'area' | 'scatter' | 'radar' | 'funnel' | 'gauge' | 'clock' | 'date' | 'marquee' | 'kpi' | 'realtime' | 'text'
  title: string
  tableId: string
  fieldId: string
  aggregation: 'count' | 'sum' | 'avg' | 'max' | 'min' | 'countDistinct'
  groupBy?: string
  filterBy?: Array<{
    fieldId: string
    operator: string
    value: unknown
  }>
  position: { x: number; y: number; w: number; h: number; z?: number }
  config?: {
    // 视觉样式配置
    colors?: string[]
    theme?: string
    backgroundColor?: string
    textColor?: string
    borderColor?: string
    borderWidth?: number
    borderRadius?: number
    shadow?: boolean
    shadowBlur?: number
    shadowColor?: string
    // 字体配置
    fontSize?: number
    fontFamily?: string
    fontWeight?: string | number
    titleFontSize?: number
    titleColor?: string
    valueFontSize?: number
    valueColor?: string
    // 数据显示配置
    showLegend?: boolean
    showLabel?: boolean
    labelPosition?: 'top' | 'inside' | 'bottom' | 'left' | 'right'
    stack?: boolean
    smooth?: boolean
    format?: string
    prefix?: string
    suffix?: string
    decimal?: number
    emptyValue?: string
    // 行为配置
    animation?: boolean
    animationDuration?: number
    refreshInterval?: number
    autoRefresh?: boolean
    enableInteraction?: boolean
    // 联动配置
    linkTarget?: string[]
    linkTrigger?: 'click' | 'hover' | 'select'
    // 筛选配置
    filterTarget?: string[]
    // 大屏组件专用配置
    // 时钟组件
    timeFormat?: '24h' | '12h'
    showSeconds?: boolean
    showDate?: boolean
    timeFontSize?: number
    dateFontSize?: number
    // 日期组件
    dateFormat?: string
    dayFontSize?: number
    monthFontSize?: number
    // 跑马灯组件
    content?: string
    speed?: number
    direction?: 'left' | 'right'
    // KPI 组件
    showTrend?: boolean
    showTarget?: boolean
    targetValue?: number
    // 实时数据流
    chartType?: 'line' | 'area'
    maxDataPoints?: number
    darkMode?: boolean
    // 通用配置
    showHeader?: boolean
    showWeekday?: boolean
    // 边框配置
    borderSize?: 'none' | 'narrow' | 'medium' | 'wide'
    // 标题文字组件
    text?: string
    subtitle?: string
    subtitleFontSize?: number
    textAlign?: 'left' | 'center' | 'right'
    subtitleColor?: string
    backgroundStyle?: 'solid' | 'gradient' | 'transparent'
    gradientColors?: string[]
    letterSpacing?: number
    lineHeight?: number
    textShadow?: boolean
    textShadowColor?: string
    textShadowBlur?: number
  }
}

export interface CreateDashboardData {
  baseId: string
  name: string
  description?: string
  widgets?: WidgetConfig[]
  layoutType?: 'grid' | 'free'
  gridColumns?: number
}

export class DashboardService {
  async createDashboard(data: CreateDashboardData): Promise<Dashboard> {
    const dashboards = await this.getDashboardsByBase(data.baseId)
    const maxOrder = dashboards.length > 0 ? Math.max(...dashboards.map(d => d.order)) : -1

    const dashboard: Dashboard = {
      id: generateId(),
      baseId: data.baseId,
      name: data.name,
      description: data.description,
      widgets: data.widgets || [],
      layout: {},
      layoutType: data.layoutType || 'grid',
      gridColumns: data.gridColumns || 12,
      refreshConfig: {
        enabled: false,
        interval: 30000,
        autoRefresh: false,
      },
      isStarred: false,
      order: maxOrder + 1,
      createdAt: Date.now(),
      updatedAt: Date.now()
    }

    await db.dashboards.add(dashboard)
    return dashboard
  }

  async getDashboard(id: string): Promise<Dashboard | undefined> {
    return db.dashboards.get(id)
  }

  async getDashboardsByBase(baseId: string): Promise<Dashboard[]> {
    return db.dashboards.where('baseId').equals(baseId).sortBy('order')
  }

  async updateDashboard(id: string, changes: Partial<Dashboard>): Promise<void> {
    await db.dashboards.update(id, {
      ...changes,
      updatedAt: Date.now()
    })
  }

  async updateDashboardWidgets(id: string, widgets: WidgetConfig[]): Promise<void> {
    await db.dashboards.update(id, {
      widgets,
      updatedAt: Date.now()
    })
  }

  async deleteDashboard(id: string): Promise<void> {
    await db.dashboards.delete(id)
  }

  async duplicateDashboard(id: string, newName?: string): Promise<Dashboard> {
    const dashboard = await this.getDashboard(id)
    if (!dashboard) {
      throw new Error('Dashboard not found')
    }

    const dashboards = await this.getDashboardsByBase(dashboard.baseId)
    const maxOrder = dashboards.length > 0 ? Math.max(...dashboards.map(d => d.order)) : -1

    const duplicated: Dashboard = {
      ...dashboard,
      id: generateId(),
      name: newName || `${dashboard.name} (复制)`,
      order: maxOrder + 1,
      createdAt: Date.now(),
      updatedAt: Date.now()
    }

    await db.dashboards.add(duplicated)
    return duplicated
  }

  async reorderDashboards(_baseId: string, dashboardIds: string[]): Promise<void> {
    await db.transaction('rw', db.dashboards, async () => {
      for (let i = 0; i < dashboardIds.length; i++) {
        await db.dashboards.update(dashboardIds[i], { order: i })
      }
    })
  }
}

export const dashboardService = new DashboardService()
