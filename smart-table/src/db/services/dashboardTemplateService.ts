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
    category: '财务',
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
  {
    name: '项目管理仪表盘',
    description: '项目进度跟踪、任务统计和团队工作负载',
    category: '项目管理',
    layoutType: 'grid',
    gridColumns: 12,
    layout: {},
    widgets: [
      {
        id: 'widget-kpi-proj-1',
        type: 'kpi',
        title: '进行中项目',
        tableId: '',
        fieldId: '',
        aggregation: 'count',
        position: { x: 0, y: 0, w: 3, h: 2, z: 1 },
        config: {
          theme: 'blue',
          fontSize: 28,
          animation: true,
        },
      },
      {
        id: 'widget-kpi-proj-2',
        type: 'kpi',
        title: '待办任务',
        tableId: '',
        fieldId: '',
        aggregation: 'count',
        position: { x: 3, y: 0, w: 3, h: 2, z: 1 },
        config: {
          theme: 'orange',
          fontSize: 28,
          animation: true,
        },
      },
      {
        id: 'widget-kpi-proj-3',
        type: 'kpi',
        title: '本周完成',
        tableId: '',
        fieldId: '',
        aggregation: 'count',
        position: { x: 6, y: 0, w: 3, h: 2, z: 1 },
        config: {
          theme: 'green',
          fontSize: 28,
          animation: true,
        },
      },
      {
        id: 'widget-kpi-proj-4',
        type: 'kpi',
        title: '逾期任务',
        tableId: '',
        fieldId: '',
        aggregation: 'count',
        position: { x: 9, y: 0, w: 3, h: 2, z: 1 },
        config: {
          theme: 'red',
          fontSize: 28,
          animation: true,
        },
      },
      {
        id: 'widget-bar-proj-1',
        type: 'bar',
        title: '项目进度概览',
        tableId: '',
        fieldId: '',
        aggregation: 'sum',
        position: { x: 0, y: 2, w: 6, h: 4, z: 1 },
        config: {
          showLegend: true,
          animation: true,
          horizontal: true,
        },
      },
      {
        id: 'widget-pie-proj-1',
        type: 'pie',
        title: '任务状态分布',
        tableId: '',
        fieldId: '',
        aggregation: 'count',
        position: { x: 6, y: 2, w: 3, h: 4, z: 1 },
        config: {
          showLegend: true,
          animation: true,
        },
      },
      {
        id: 'widget-pie-proj-2',
        type: 'pie',
        title: '优先级分布',
        tableId: '',
        fieldId: '',
        aggregation: 'count',
        position: { x: 9, y: 2, w: 3, h: 4, z: 1 },
        config: {
          showLegend: true,
          animation: true,
        },
      },
      {
        id: 'widget-table-proj-1',
        type: 'table',
        title: '团队成员工作负载',
        tableId: '',
        fieldId: '',
        aggregation: 'count',
        position: { x: 0, y: 6, w: 12, h: 3, z: 1 },
        config: {
          fontSize: 12,
        },
      },
    ],
    isPreset: true,
    isStarred: false,
  },
  {
    name: '人力资源仪表盘',
    description: '员工数据统计、招聘进度和团队结构分析',
    category: '人力资源',
    layoutType: 'grid',
    gridColumns: 12,
    layout: {},
    widgets: [
      {
        id: 'widget-kpi-hr-1',
        type: 'kpi',
        title: '在职员工',
        tableId: '',
        fieldId: '',
        aggregation: 'count',
        position: { x: 0, y: 0, w: 3, h: 2, z: 1 },
        config: {
          theme: 'blue',
          fontSize: 28,
          animation: true,
        },
      },
      {
        id: 'widget-kpi-hr-2',
        type: 'kpi',
        title: '本月入职',
        tableId: '',
        fieldId: '',
        aggregation: 'count',
        position: { x: 3, y: 0, w: 3, h: 2, z: 1 },
        config: {
          theme: 'green',
          fontSize: 28,
          animation: true,
        },
      },
      {
        id: 'widget-kpi-hr-3',
        type: 'kpi',
        title: '待招聘',
        tableId: '',
        fieldId: '',
        aggregation: 'count',
        position: { x: 6, y: 0, w: 3, h: 2, z: 1 },
        config: {
          theme: 'orange',
          fontSize: 28,
          animation: true,
        },
      },
      {
        id: 'widget-kpi-hr-4',
        type: 'kpi',
        title: '离职率',
        tableId: '',
        fieldId: '',
        aggregation: 'avg',
        position: { x: 9, y: 0, w: 3, h: 2, z: 1 },
        config: {
          theme: 'purple',
          fontSize: 28,
          suffix: '%',
          decimal: 1,
          animation: true,
        },
      },
      {
        id: 'widget-pie-hr-1',
        type: 'pie',
        title: '部门人员分布',
        tableId: '',
        fieldId: '',
        aggregation: 'count',
        position: { x: 0, y: 2, w: 4, h: 4, z: 1 },
        config: {
          showLegend: true,
          animation: true,
        },
      },
      {
        id: 'widget-bar-hr-1',
        type: 'bar',
        title: '年龄分布',
        tableId: '',
        fieldId: '',
        aggregation: 'count',
        position: { x: 4, y: 2, w: 4, h: 4, z: 1 },
        config: {
          showLegend: false,
          animation: true,
        },
      },
      {
        id: 'widget-pie-hr-2',
        type: 'pie',
        title: '学历分布',
        tableId: '',
        fieldId: '',
        aggregation: 'count',
        position: { x: 8, y: 2, w: 4, h: 4, z: 1 },
        config: {
          showLegend: true,
          animation: true,
        },
      },
      {
        id: 'widget-line-hr-1',
        type: 'line',
        title: '人员变动趋势',
        tableId: '',
        fieldId: '',
        aggregation: 'count',
        position: { x: 0, y: 6, w: 8, h: 3, z: 1 },
        config: {
          showLegend: true,
          smooth: true,
          animation: true,
        },
      },
      {
        id: 'widget-table-hr-1',
        type: 'table',
        title: '招聘进度',
        tableId: '',
        fieldId: '',
        aggregation: 'count',
        position: { x: 8, y: 6, w: 4, h: 3, z: 1 },
        config: {
          fontSize: 11,
        },
      },
    ],
    isPreset: true,
    isStarred: false,
  },
  {
    name: '客户服务仪表盘',
    description: '客服工单统计、响应时间和服务质量分析',
    category: '客户服务',
    layoutType: 'grid',
    gridColumns: 12,
    layout: {},
    widgets: [
      {
        id: 'widget-kpi-cs-1',
        type: 'kpi',
        title: '今日工单',
        tableId: '',
        fieldId: '',
        aggregation: 'count',
        position: { x: 0, y: 0, w: 3, h: 2, z: 1 },
        config: {
          theme: 'blue',
          fontSize: 28,
          animation: true,
        },
      },
      {
        id: 'widget-kpi-cs-2',
        type: 'kpi',
        title: '待处理',
        tableId: '',
        fieldId: '',
        aggregation: 'count',
        position: { x: 3, y: 0, w: 3, h: 2, z: 1 },
        config: {
          theme: 'orange',
          fontSize: 28,
          animation: true,
        },
      },
      {
        id: 'widget-kpi-cs-3',
        type: 'kpi',
        title: '平均响应',
        tableId: '',
        fieldId: '',
        aggregation: 'avg',
        position: { x: 6, y: 0, w: 3, h: 2, z: 1 },
        config: {
          theme: 'green',
          fontSize: 28,
          suffix: '分钟',
          decimal: 1,
          animation: true,
        },
      },
      {
        id: 'widget-kpi-cs-4',
        type: 'kpi',
        title: '满意度',
        tableId: '',
        fieldId: '',
        aggregation: 'avg',
        position: { x: 9, y: 0, w: 3, h: 2, z: 1 },
        config: {
          theme: 'purple',
          fontSize: 28,
          suffix: '%',
          decimal: 1,
          animation: true,
        },
      },
      {
        id: 'widget-realtime-cs-1',
        type: 'realtime',
        title: '实时工单量',
        tableId: '',
        fieldId: '',
        aggregation: 'count',
        position: { x: 0, y: 2, w: 6, h: 3, z: 1 },
        config: {
          refreshInterval: 5000,
          animation: true,
        },
      },
      {
        id: 'widget-pie-cs-1',
        type: 'pie',
        title: '工单类型分布',
        tableId: '',
        fieldId: '',
        aggregation: 'count',
        position: { x: 6, y: 2, w: 3, h: 3, z: 1 },
        config: {
          showLegend: true,
          animation: true,
        },
      },
      {
        id: 'widget-pie-cs-2',
        type: 'pie',
        title: '工单状态',
        tableId: '',
        fieldId: '',
        aggregation: 'count',
        position: { x: 9, y: 2, w: 3, h: 3, z: 1 },
        config: {
          showLegend: true,
          animation: true,
        },
      },
      {
        id: 'widget-bar-cs-1',
        type: 'bar',
        title: '客服工作量统计',
        tableId: '',
        fieldId: '',
        aggregation: 'count',
        position: { x: 0, y: 5, w: 6, h: 4, z: 1 },
        config: {
          showLegend: true,
          animation: true,
        },
      },
      {
        id: 'widget-table-cs-1',
        type: 'table',
        title: '最新工单',
        tableId: '',
        fieldId: '',
        aggregation: 'count',
        position: { x: 6, y: 5, w: 6, h: 4, z: 1 },
        config: {
          fontSize: 11,
        },
      },
    ],
    isPreset: true,
    isStarred: false,
  },
  {
    name: '营销分析仪表盘',
    description: '营销活动效果、渠道分析和转化漏斗',
    category: '运营',
    layoutType: 'grid',
    gridColumns: 12,
    layout: {},
    widgets: [
      {
        id: 'widget-kpi-mkt-1',
        type: 'kpi',
        title: '活动总数',
        tableId: '',
        fieldId: '',
        aggregation: 'count',
        position: { x: 0, y: 0, w: 3, h: 2, z: 1 },
        config: {
          theme: 'blue',
          fontSize: 28,
          animation: true,
        },
      },
      {
        id: 'widget-kpi-mkt-2',
        type: 'kpi',
        title: '总曝光量',
        tableId: '',
        fieldId: '',
        aggregation: 'sum',
        position: { x: 3, y: 0, w: 3, h: 2, z: 1 },
        config: {
          theme: 'green',
          fontSize: 24,
          animation: true,
        },
      },
      {
        id: 'widget-kpi-mkt-3',
        type: 'kpi',
        title: '转化率',
        tableId: '',
        fieldId: '',
        aggregation: 'avg',
        position: { x: 6, y: 0, w: 3, h: 2, z: 1 },
        config: {
          theme: 'orange',
          fontSize: 28,
          suffix: '%',
          decimal: 2,
          animation: true,
        },
      },
      {
        id: 'widget-kpi-mkt-4',
        type: 'kpi',
        title: 'ROI',
        tableId: '',
        fieldId: '',
        aggregation: 'avg',
        position: { x: 9, y: 0, w: 3, h: 2, z: 1 },
        config: {
          theme: 'purple',
          fontSize: 28,
          suffix: '%',
          decimal: 1,
          animation: true,
        },
      },
      {
        id: 'widget-bar-mkt-1',
        type: 'bar',
        title: '渠道效果对比',
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
        id: 'widget-pie-mkt-1',
        type: 'pie',
        title: '预算分配',
        tableId: '',
        fieldId: '',
        aggregation: 'sum',
        position: { x: 6, y: 2, w: 3, h: 4, z: 1 },
        config: {
          showLegend: true,
          animation: true,
        },
      },
      {
        id: 'widget-pie-mkt-2',
        type: 'pie',
        title: '流量来源',
        tableId: '',
        fieldId: '',
        aggregation: 'count',
        position: { x: 9, y: 2, w: 3, h: 4, z: 1 },
        config: {
          showLegend: true,
          animation: true,
        },
      },
      {
        id: 'widget-line-mkt-1',
        type: 'line',
        title: '活动趋势分析',
        tableId: '',
        fieldId: '',
        aggregation: 'sum',
        position: { x: 0, y: 6, w: 8, h: 3, z: 1 },
        config: {
          showLegend: true,
          smooth: true,
          animation: true,
        },
      },
      {
        id: 'widget-table-mkt-1',
        type: 'table',
        title: '活动列表',
        tableId: '',
        fieldId: '',
        aggregation: 'sum',
        position: { x: 8, y: 6, w: 4, h: 3, z: 1 },
        config: {
          fontSize: 11,
        },
      },
    ],
    isPreset: true,
    isStarred: false,
  },
  {
    name: 'IT运维监控',
    description: '服务器状态、性能指标和告警信息监控',
    category: 'IT运维',
    layoutType: 'grid',
    gridColumns: 12,
    layout: {},
    widgets: [
      {
        id: 'widget-clock-it-1',
        type: 'clock',
        title: '系统时间',
        tableId: '',
        fieldId: '',
        aggregation: 'count',
        position: { x: 0, y: 0, w: 2, h: 2, z: 1 },
        config: {
          fontSize: 20,
          showSeconds: true,
        },
      },
      {
        id: 'widget-kpi-it-1',
        type: 'kpi',
        title: '服务器数量',
        tableId: '',
        fieldId: '',
        aggregation: 'count',
        position: { x: 2, y: 0, w: 2, h: 2, z: 1 },
        config: {
          theme: 'blue',
          fontSize: 24,
          animation: true,
        },
      },
      {
        id: 'widget-kpi-it-2',
        type: 'kpi',
        title: 'CPU平均',
        tableId: '',
        fieldId: '',
        aggregation: 'avg',
        position: { x: 4, y: 0, w: 2, h: 2, z: 1 },
        config: {
          theme: 'green',
          fontSize: 24,
          suffix: '%',
          decimal: 1,
          animation: true,
        },
      },
      {
        id: 'widget-kpi-it-3',
        type: 'kpi',
        title: '内存使用',
        tableId: '',
        fieldId: '',
        aggregation: 'avg',
        position: { x: 6, y: 0, w: 2, h: 2, z: 1 },
        config: {
          theme: 'orange',
          fontSize: 24,
          suffix: '%',
          decimal: 1,
          animation: true,
        },
      },
      {
        id: 'widget-kpi-it-4',
        type: 'kpi',
        title: '告警数量',
        tableId: '',
        fieldId: '',
        aggregation: 'count',
        position: { x: 8, y: 0, w: 2, h: 2, z: 1 },
        config: {
          theme: 'red',
          fontSize: 24,
          animation: true,
        },
      },
      {
        id: 'widget-kpi-it-5',
        type: 'kpi',
        title: '在线服务',
        tableId: '',
        fieldId: '',
        aggregation: 'count',
        position: { x: 10, y: 0, w: 2, h: 2, z: 1 },
        config: {
          theme: 'cyan',
          fontSize: 24,
          animation: true,
        },
      },
      {
        id: 'widget-realtime-it-1',
        type: 'realtime',
        title: '实时流量监控',
        tableId: '',
        fieldId: '',
        aggregation: 'count',
        position: { x: 0, y: 2, w: 8, h: 3, z: 1 },
        config: {
          refreshInterval: 3000,
          animation: true,
        },
      },
      {
        id: 'widget-marquee-it-1',
        type: 'marquee',
        title: '系统告警',
        tableId: '',
        fieldId: '',
        aggregation: 'count',
        position: { x: 8, y: 2, w: 4, h: 1, z: 1 },
        config: {
          speed: 3,
          fontSize: 12,
        },
      },
      {
        id: 'widget-number-it-1',
        type: 'number',
        title: '磁盘IO',
        tableId: '',
        fieldId: '',
        aggregation: 'avg',
        position: { x: 8, y: 3, w: 2, h: 2, z: 1 },
        config: {
          theme: 'blue',
          suffix: 'MB/s',
          decimal: 1,
          animation: true,
        },
      },
      {
        id: 'widget-number-it-2',
        type: 'number',
        title: '网络带宽',
        tableId: '',
        fieldId: '',
        aggregation: 'avg',
        position: { x: 10, y: 3, w: 2, h: 2, z: 1 },
        config: {
          theme: 'green',
          suffix: 'Gbps',
          decimal: 2,
          animation: true,
        },
      },
      {
        id: 'widget-line-it-1',
        type: 'line',
        title: 'CPU/内存趋势',
        tableId: '',
        fieldId: '',
        aggregation: 'avg',
        position: { x: 0, y: 5, w: 6, h: 4, z: 1 },
        config: {
          showLegend: true,
          smooth: true,
          animation: true,
        },
      },
      {
        id: 'widget-table-it-1',
        type: 'table',
        title: '服务器状态',
        tableId: '',
        fieldId: '',
        aggregation: 'count',
        position: { x: 6, y: 5, w: 6, h: 4, z: 1 },
        config: {
          fontSize: 11,
        },
      },
    ],
    isPreset: true,
    isStarred: false,
  },
  {
    name: '电商数据大屏',
    description: '订单统计、商品销售和用户行为分析',
    category: '运营',
    layoutType: 'grid',
    gridColumns: 12,
    layout: {},
    widgets: [
      {
        id: 'widget-kpi-ecom-1',
        type: 'kpi',
        title: '今日订单',
        tableId: '',
        fieldId: '',
        aggregation: 'count',
        position: { x: 0, y: 0, w: 3, h: 2, z: 1 },
        config: {
          theme: 'blue',
          fontSize: 28,
          animation: true,
        },
      },
      {
        id: 'widget-kpi-ecom-2',
        type: 'kpi',
        title: '今日销售额',
        tableId: '',
        fieldId: '',
        aggregation: 'sum',
        position: { x: 3, y: 0, w: 3, h: 2, z: 1 },
        config: {
          theme: 'green',
          fontSize: 24,
          prefix: '¥',
          decimal: 2,
          animation: true,
        },
      },
      {
        id: 'widget-kpi-ecom-3',
        type: 'kpi',
        title: '客单价',
        tableId: '',
        fieldId: '',
        aggregation: 'avg',
        position: { x: 6, y: 0, w: 3, h: 2, z: 1 },
        config: {
          theme: 'orange',
          fontSize: 28,
          prefix: '¥',
          decimal: 2,
          animation: true,
        },
      },
      {
        id: 'widget-kpi-ecom-4',
        type: 'kpi',
        title: '新增用户',
        tableId: '',
        fieldId: '',
        aggregation: 'count',
        position: { x: 9, y: 0, w: 3, h: 2, z: 1 },
        config: {
          theme: 'purple',
          fontSize: 28,
          animation: true,
        },
      },
      {
        id: 'widget-realtime-ecom-1',
        type: 'realtime',
        title: '实时订单流',
        tableId: '',
        fieldId: '',
        aggregation: 'count',
        position: { x: 0, y: 2, w: 8, h: 3, z: 1 },
        config: {
          refreshInterval: 3000,
          animation: true,
        },
      },
      {
        id: 'widget-pie-ecom-1',
        type: 'pie',
        title: '品类销售占比',
        tableId: '',
        fieldId: '',
        aggregation: 'sum',
        position: { x: 8, y: 2, w: 4, h: 3, z: 1 },
        config: {
          showLegend: true,
          animation: true,
        },
      },
      {
        id: 'widget-bar-ecom-1',
        type: 'bar',
        title: '热销商品TOP10',
        tableId: '',
        fieldId: '',
        aggregation: 'sum',
        position: { x: 0, y: 5, w: 6, h: 4, z: 1 },
        config: {
          showLegend: false,
          animation: true,
          horizontal: true,
        },
      },
      {
        id: 'widget-line-ecom-1',
        type: 'line',
        title: '销售趋势',
        tableId: '',
        fieldId: '',
        aggregation: 'sum',
        position: { x: 6, y: 5, w: 6, h: 4, z: 1 },
        config: {
          showLegend: true,
          smooth: true,
          animation: true,
        },
      },
    ],
    isPreset: true,
    isStarred: false,
  },
  {
    name: '生产制造仪表盘',
    description: '生产进度、设备状态和质量检测数据',
    category: '生产',
    layoutType: 'grid',
    gridColumns: 12,
    layout: {},
    widgets: [
      {
        id: 'widget-kpi-prod-1',
        type: 'kpi',
        title: '今日产量',
        tableId: '',
        fieldId: '',
        aggregation: 'sum',
        position: { x: 0, y: 0, w: 3, h: 2, z: 1 },
        config: {
          theme: 'blue',
          fontSize: 28,
          animation: true,
        },
      },
      {
        id: 'widget-kpi-prod-2',
        type: 'kpi',
        title: '设备开工率',
        tableId: '',
        fieldId: '',
        aggregation: 'avg',
        position: { x: 3, y: 0, w: 3, h: 2, z: 1 },
        config: {
          theme: 'green',
          fontSize: 28,
          suffix: '%',
          decimal: 1,
          animation: true,
        },
      },
      {
        id: 'widget-kpi-prod-3',
        type: 'kpi',
        title: '良品率',
        tableId: '',
        fieldId: '',
        aggregation: 'avg',
        position: { x: 6, y: 0, w: 3, h: 2, z: 1 },
        config: {
          theme: 'orange',
          fontSize: 28,
          suffix: '%',
          decimal: 2,
          animation: true,
        },
      },
      {
        id: 'widget-kpi-prod-4',
        type: 'kpi',
        title: '异常工单',
        tableId: '',
        fieldId: '',
        aggregation: 'count',
        position: { x: 9, y: 0, w: 3, h: 2, z: 1 },
        config: {
          theme: 'red',
          fontSize: 28,
          animation: true,
        },
      },
      {
        id: 'widget-realtime-prod-1',
        type: 'realtime',
        title: '生产线实时监控',
        tableId: '',
        fieldId: '',
        aggregation: 'count',
        position: { x: 0, y: 2, w: 8, h: 3, z: 1 },
        config: {
          refreshInterval: 5000,
          animation: true,
        },
      },
      {
        id: 'widget-pie-prod-1',
        type: 'pie',
        title: '产品类型分布',
        tableId: '',
        fieldId: '',
        aggregation: 'count',
        position: { x: 8, y: 2, w: 4, h: 3, z: 1 },
        config: {
          showLegend: true,
          animation: true,
        },
      },
      {
        id: 'widget-bar-prod-1',
        type: 'bar',
        title: '各产线产量对比',
        tableId: '',
        fieldId: '',
        aggregation: 'sum',
        position: { x: 0, y: 5, w: 6, h: 4, z: 1 },
        config: {
          showLegend: true,
          animation: true,
        },
      },
      {
        id: 'widget-line-prod-1',
        type: 'line',
        title: '产量趋势',
        tableId: '',
        fieldId: '',
        aggregation: 'sum',
        position: { x: 6, y: 5, w: 6, h: 4, z: 1 },
        config: {
          showLegend: true,
          smooth: true,
          animation: true,
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
    const allTemplates = await db.dashboardTemplates.toArray()
    const existingPresets = allTemplates.filter(t => t.isPreset === true)
    const existingNames = new Set(existingPresets.map(t => t.name))

    // 添加新模板
    const newTemplates = presetTemplates.filter(preset => !existingNames.has(preset.name))
    
    if (newTemplates.length > 0) {
      const now = Date.now()
      const templates: DashboardTemplate[] = newTemplates.map((preset) => ({
        ...preset,
        id: generateId(),
        createdAt: now,
        updatedAt: now,
      }))

      await db.dashboardTemplates.bulkAdd(templates)
    }

    // 同步已存在模板的属性（如分类变更）
    const existingPresetMap = new Map(existingPresets.map(t => [t.name, t]))
    const updates: Promise<void>[] = []
    
    for (const preset of presetTemplates) {
      const existing = existingPresetMap.get(preset.name)
      if (existing && existing.category !== preset.category) {
        updates.push(db.dashboardTemplates.update(existing.id, {
          category: preset.category,
          description: preset.description,
          updatedAt: Date.now(),
        }).then(() => void 0))
      }
    }
    
    if (updates.length > 0) {
      await Promise.all(updates)
    }
  }

  // 清理重复的预设模板，只保留每个名称的第一个
  async cleanupDuplicatePresets(): Promise<void> {
    const allTemplates = await db.dashboardTemplates.toArray()
    const allPresets = allTemplates.filter(t => t.isPreset === true)

    if (allPresets.length <= presetTemplates.length) {
      return
    }

    const seenNames = new Set<string>()
    const idsToDelete: string[] = []

    for (const preset of allPresets) {
      if (seenNames.has(preset.name)) {
        idsToDelete.push(preset.id)
      } else {
        seenNames.add(preset.name)
      }
    }

    if (idsToDelete.length > 0) {
      await db.dashboardTemplates.bulkDelete(idsToDelete)
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
