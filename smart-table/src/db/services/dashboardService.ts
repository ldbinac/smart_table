import { db } from '../schema';
import type { Dashboard } from '../schema';
import { generateId } from '../../utils/id';
import { dashboardApiService } from '@/services/api/dashboardApiService';

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
    try {
      // 先调用后端 API 创建仪表盘
      const apiDashboard = await dashboardApiService.createDashboard({
        base_id: data.baseId,
        name: data.name,
        description: data.description,
        layout: {
          type: data.layoutType || 'grid',
          config: {
            gridColumns: data.gridColumns || 12
          }
        }
      });

      // 将后端返回的仪表盘转换为本地格式
      const localView: Dashboard = {
        id: apiDashboard.id,
        baseId: apiDashboard.base_id || data.baseId,
        name: apiDashboard.name,
        description: apiDashboard.description,
        widgets: (apiDashboard.widgets as unknown[]) || [],
        layout: apiDashboard.layout || {},
        layoutType: (apiDashboard.layout?.type as 'grid' | 'free') || 'grid',
        gridColumns: apiDashboard.layout?.config?.gridColumns || 12,
        refreshConfig: {
          enabled: false,
          interval: 30000,
          autoRefresh: false,
        },
        isStarred: false,
        order: apiDashboard.order ?? 0,
        createdAt: new Date(apiDashboard.created_at).getTime(),
        updatedAt: new Date(apiDashboard.updated_at).getTime(),
      };

      // 保存到本地 IndexedDB
      await db.dashboards.add(localView);
      return localView;
    } catch (error) {
      console.error('[dashboardService] createDashboard failed:', error);
      throw error;
    }
  }

  async getDashboard(id: string): Promise<Dashboard | undefined> {
    const view = await db.dashboards.get(id);
    return view;
  }

  async getDashboardsByBase(
    baseId: string,
    forceRefresh: boolean = true, // 默认强制刷新
  ): Promise<Dashboard[]> {
    try {
      // 如果需要强制刷新，先清空本地缓存
      if (forceRefresh) {
        await db.dashboards.where('baseId').equals(baseId).delete();
      }

      // 始终优先从后端 API 获取最新数据
      console.log('[DashboardService] Fetching dashboards from API for base:', baseId);
      const apiDashboards = await dashboardApiService.getDashboards(baseId);

      // 将后端返回的仪表盘转换为本地格式并保存
      await db.transaction('rw', db.dashboards, async () => {
        // 先清空本地数据
        await db.dashboards.where('baseId').equals(baseId).delete();

        // 保存新数据
        for (const apiDashboard of apiDashboards) {
          const localView: Dashboard = {
            id: apiDashboard.id,
            baseId: apiDashboard.base_id || baseId,
            name: apiDashboard.name,
            description: apiDashboard.description,
            widgets: (apiDashboard.widgets as unknown[]) || [],
            layout: apiDashboard.layout || {},
            layoutType: (apiDashboard.layout?.type as 'grid' | 'free') || 'grid',
            gridColumns: apiDashboard.layout?.config?.gridColumns || 12,
            refreshConfig: {
              enabled: false,
              interval: 30000,
              autoRefresh: false,
            },
            isStarred: false,
            order: apiDashboard.order ?? 0,
            createdAt: new Date(apiDashboard.created_at).getTime(),
            updatedAt: new Date(apiDashboard.updated_at).getTime(),
          };
          await db.dashboards.put(localView);
        }
      });

      // 从本地 IndexedDB 返回
      const dashboards = await db.dashboards
        .where('baseId')
        .equals(baseId)
        .sortBy('order');
      console.log('[DashboardService] Loaded', dashboards.length, 'dashboards from API');
      return dashboards;
    } catch (error) {
      console.error('[DashboardService] getDashboardsByBase failed:', error);
      // 如果 API 调用失败，从本地缓存读取（降级处理）
      console.warn('[DashboardService] API failed, falling back to local cache');
      const dashboards = await db.dashboards
        .where('baseId')
        .equals(baseId)
        .sortBy('order');
      return dashboards;
    }
  }

  async updateDashboard(id: string, changes: Partial<Dashboard>): Promise<void> {
    try {
      console.log('[DashboardService] Updating dashboard:', id, changes);

      // 构建要发送到后端的数据对象
      const apiData: Record<string, unknown> = {};

      if (changes.name !== undefined) apiData.name = changes.name;
      if (changes.description !== undefined) apiData.description = changes.description;
      if (changes.layout !== undefined) apiData.layout = changes.layout;
      if (changes.widgets !== undefined) apiData.widgets = changes.widgets;

      console.log('[DashboardService] API data:', apiData);

      // 检查是否有实际要更新的数据
      if (Object.keys(apiData).length === 0) {
        console.warn('[DashboardService] No data to update, skipping...');
        return;
      }

      // 先调用后端 API 更新仪表盘
      await dashboardApiService.updateDashboard(id, apiData);

      // 再更新本地 IndexedDB
      const updateData: Record<string, unknown> = {
        updatedAt: Date.now(),
      };

      if (changes.name !== undefined) updateData.name = changes.name;
      if (changes.description !== undefined) updateData.description = changes.description;
      if (changes.layout !== undefined) updateData.layout = changes.layout;
      if (changes.widgets !== undefined) {
        updateData.widgets = JSON.parse(JSON.stringify(changes.widgets));
      }

      console.log('[DashboardService] Final update data:', updateData);

      // 使用 Dexie 的 update 方法
      const updateCount = await db.dashboards.update(id, updateData);
      console.log('[DashboardService] Update count:', updateCount);

      if (updateCount === 0) {
        console.warn('[DashboardService] No records were updated!');
      }
    } catch (error) {
      console.error('[dashboardService] updateDashboard failed:', error);
      throw error;
    }
  }

  async updateDashboardWidgets(id: string, widgets: WidgetConfig[]): Promise<void> {
    console.log('[DashboardService] updateDashboardWidgets called:', {
      id,
      widgetCount: widgets.length,
      firstWidget: widgets[0]
    });
    await this.updateDashboard(id, { widgets: widgets as unknown[] });
  }

  async deleteDashboard(id: string): Promise<void> {
    try {
      // 先调用后端 API 删除仪表盘
      await dashboardApiService.deleteDashboard(id);

      // 再从本地 IndexedDB 删除
      await db.dashboards.delete(id);
    } catch (error) {
      console.error('[dashboardService] deleteDashboard failed:', error);
      throw error;
    }
  }

  async duplicateDashboard(id: string, newName?: string): Promise<Dashboard> {
    try {
      // 调用后端 API 复制仪表盘
      const apiDashboard = await dashboardApiService.duplicateDashboard(id, newName);

      // 将后端返回的仪表盘转换为本地格式
      const localView: Dashboard = {
        id: apiDashboard.id,
        baseId: apiDashboard.base_id || (await this.getDashboard(id))?.baseId || '',
        name: apiDashboard.name,
        description: apiDashboard.description,
        widgets: (apiDashboard.widgets as unknown[]) || [],
        layout: apiDashboard.layout || {},
        layoutType: (apiDashboard.layout?.type as 'grid' | 'free') || 'grid',
        gridColumns: apiDashboard.layout?.config?.gridColumns || 12,
        refreshConfig: {
          enabled: false,
          interval: 30000,
          autoRefresh: false,
        },
        isStarred: false,
        order: apiDashboard.order ?? 0,
        createdAt: new Date(apiDashboard.created_at).getTime(),
        updatedAt: new Date(apiDashboard.updated_at).getTime(),
      };

      // 保存到本地 IndexedDB
      await db.dashboards.add(localView);
      return localView;
    } catch (error) {
      console.error('[dashboardService] duplicateDashboard failed:', error);
      throw error;
    }
  }

  async reorderDashboards(baseId: string, dashboardIds: string[]): Promise<void> {
    try {
      // 更新本地 IndexedDB
      await db.transaction('rw', db.dashboards, async () => {
        for (let i = 0; i < dashboardIds.length; i++) {
          await db.dashboards.update(dashboardIds[i], { order: i });
        }
      });
    } catch (error) {
      console.error('[dashboardService] reorderDashboards failed:', error);
      throw error;
    }
  }
}

export const dashboardService = new DashboardService()
