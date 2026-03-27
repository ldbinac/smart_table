import { db } from '../schema';
import type { Dashboard } from '../schema';
import { generateId } from '../../utils/id';

export interface WidgetConfig {
  id: string
  type: 'bar' | 'line' | 'pie' | 'number' | 'table' | 'area' | 'scatter' | 'radar' | 'funnel' | 'gauge'
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
  position: { x: number; y: number; w: number; h: number }
  config?: {
    colors?: string[]
    showLegend?: boolean
    showLabel?: boolean
    stack?: boolean
    smooth?: boolean
    format?: string
    prefix?: string
    suffix?: string
    decimal?: number
  }
}

export interface CreateDashboardData {
  baseId: string
  name: string
  description?: string
  widgets?: WidgetConfig[]
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

  async reorderDashboards(baseId: string, dashboardIds: string[]): Promise<void> {
    await db.transaction('rw', db.dashboards, async () => {
      for (let i = 0; i < dashboardIds.length; i++) {
        await db.dashboards.update(dashboardIds[i], { order: i })
      }
    })
  }
}

export const dashboardService = new DashboardService()
