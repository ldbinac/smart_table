import type { WidgetConfig } from '@/db/services/dashboardService'
import type { Component } from 'vue'

export type WidgetType =
  | 'bar'
  | 'line'
  | 'pie'
  | 'number'
  | 'table'
  | 'area'
  | 'scatter'
  | 'radar'
  | 'funnel'
  | 'gauge'
  | 'clock'
  | 'date'
  | 'marquee'
  | 'kpi'
  | 'realtime'

export interface WidgetMetadata {
  type: WidgetType
  name: string
  description: string
  icon: string
  category: 'chart' | 'data' | 'display' | 'screen'
  defaultSize: { w: number; h: number }
  minSize: { w: number; h: number }
  maxSize?: { w: number; h: number }
  configOptions: ConfigOption[]
  defaultConfig: Record<string, unknown>
  dataRequirements: DataRequirement[]
  supportsInteraction: boolean
  supportsAnimation: boolean
  supportsRealtime: boolean
}

export interface ConfigOption {
  key: string
  label: string
  type:
    | 'string'
    | 'number'
    | 'boolean'
    | 'select'
    | 'color'
    | 'range'
    | 'array'
    | 'object'
  defaultValue: unknown
  options?: Array<{ label: string; value: unknown }>
  min?: number
  max?: number
  step?: number
  description?: string
  group?: string
  condition?: (config: Record<string, unknown>) => boolean
}

export interface DataRequirement {
  type: 'table' | 'field' | 'aggregation' | 'groupBy' | 'filter'
  required: boolean
  description: string
  supportedTypes?: string[]
}

export interface RegisteredWidget {
  metadata: WidgetMetadata
  component?: Component
  configComponent?: Component
  renderFn?: (config: WidgetConfig, data: unknown) => unknown
}

// 默认配置选项组
const commonConfigOptions: ConfigOption[] = [
  {
    key: 'theme',
    label: '主题',
    type: 'select',
    defaultValue: 'default',
    options: [
      { label: '默认', value: 'default' },
      { label: '蓝色', value: 'blue' },
      { label: '绿色', value: 'green' },
      { label: '橙色', value: 'orange' },
      { label: '紫色', value: 'purple' },
      { label: '红色', value: 'red' },
      { label: '暗黑', value: 'dark' },
    ],
    group: '样式',
  },
  {
    key: 'backgroundColor',
    label: '背景颜色',
    type: 'color',
    defaultValue: '#ffffff',
    group: '样式',
  },
  {
    key: 'borderColor',
    label: '边框颜色',
    type: 'color',
    defaultValue: '#e5e7eb',
    group: '样式',
  },
  {
    key: 'borderWidth',
    label: '边框宽度',
    type: 'range',
    defaultValue: 1,
    min: 0,
    max: 5,
    step: 1,
    group: '样式',
  },
  {
    key: 'borderRadius',
    label: '圆角',
    type: 'range',
    defaultValue: 8,
    min: 0,
    max: 24,
    step: 2,
    group: '样式',
  },
  {
    key: 'shadow',
    label: '显示阴影',
    type: 'boolean',
    defaultValue: true,
    group: '样式',
  },
  {
    key: 'fontSize',
    label: '字体大小',
    type: 'range',
    defaultValue: 14,
    min: 10,
    max: 32,
    step: 1,
    group: '字体',
  },
  {
    key: 'titleFontSize',
    label: '标题字体大小',
    type: 'range',
    defaultValue: 16,
    min: 12,
    max: 36,
    step: 1,
    group: '字体',
  },
  {
    key: 'titleColor',
    label: '标题颜色',
    type: 'color',
    defaultValue: '#1f2937',
    group: '字体',
  },
  {
    key: 'animation',
    label: '启用动画',
    type: 'boolean',
    defaultValue: true,
    group: '行为',
  },
  {
    key: 'animationDuration',
    label: '动画时长(ms)',
    type: 'range',
    defaultValue: 1000,
    min: 200,
    max: 3000,
    step: 100,
    group: '行为',
    condition: (config) => config.animation === true,
  },
  {
    key: 'refreshInterval',
    label: '刷新间隔(ms)',
    type: 'select',
    defaultValue: 0,
    options: [
      { label: '不自动刷新', value: 0 },
      { label: '1秒', value: 1000 },
      { label: '5秒', value: 5000 },
      { label: '30秒', value: 30000 },
      { label: '1分钟', value: 60000 },
      { label: '5分钟', value: 300000 },
    ],
    group: '行为',
  },
]

// 图表特有配置
const chartConfigOptions: ConfigOption[] = [
  {
    key: 'colors',
    label: '自定义颜色',
    type: 'array',
    defaultValue: [],
    group: '样式',
  },
  {
    key: 'showLegend',
    label: '显示图例',
    type: 'boolean',
    defaultValue: true,
    group: '图表',
  },
  {
    key: 'showLabel',
    label: '显示数值标签',
    type: 'boolean',
    defaultValue: false,
    group: '图表',
  },
  {
    key: 'labelPosition',
    label: '标签位置',
    type: 'select',
    defaultValue: 'top',
    options: [
      { label: '顶部', value: 'top' },
      { label: '内部', value: 'inside' },
      { label: '底部', value: 'bottom' },
      { label: '左侧', value: 'left' },
      { label: '右侧', value: 'right' },
    ],
    group: '图表',
    condition: (config) => config.showLabel === true,
  },
  {
    key: 'smooth',
    label: '平滑曲线',
    type: 'boolean',
    defaultValue: true,
    group: '图表',
    condition: (config) =>
      ['line', 'area'].includes(config.type as string),
  },
  {
    key: 'stack',
    label: '堆叠显示',
    type: 'boolean',
    defaultValue: false,
    group: '图表',
    condition: (config) =>
      ['bar', 'area'].includes(config.type as string),
  },
]

// 数据格式化配置
const formatConfigOptions: ConfigOption[] = [
  {
    key: 'format',
    label: '数值格式',
    type: 'select',
    defaultValue: 'number',
    options: [
      { label: '数字', value: 'number' },
      { label: '货币', value: 'currency' },
      { label: '百分比', value: 'percent' },
      { label: '千分位', value: 'thousands' },
      { label: '科学计数', value: 'scientific' },
    ],
    group: '数据格式',
  },
  {
    key: 'prefix',
    label: '前缀',
    type: 'string',
    defaultValue: '',
    group: '数据格式',
  },
  {
    key: 'suffix',
    label: '后缀',
    type: 'string',
    defaultValue: '',
    group: '数据格式',
  },
  {
    key: 'decimal',
    label: '小数位数',
    type: 'range',
    defaultValue: 0,
    min: 0,
    max: 6,
    step: 1,
    group: '数据格式',
  },
  {
    key: 'emptyValue',
    label: '空值显示',
    type: 'string',
    defaultValue: '-',
    group: '数据格式',
  },
]

// 联动配置
const interactionConfigOptions: ConfigOption[] = [
  {
    key: 'enableInteraction',
    label: '启用交互',
    type: 'boolean',
    defaultValue: true,
    group: '交互',
  },
  {
    key: 'linkTrigger',
    label: '联动触发方式',
    type: 'select',
    defaultValue: 'click',
    options: [
      { label: '点击', value: 'click' },
      { label: '悬停', value: 'hover' },
      { label: '选择', value: 'select' },
    ],
    group: '交互',
    condition: (config) => config.enableInteraction === true,
  },
]

class DashboardWidgetRegistry {
  private widgets: Map<WidgetType, RegisteredWidget> = new Map()

  constructor() {
    this.registerDefaultWidgets()
  }

  // 注册组件
  registerWidget(type: WidgetType, widget: RegisteredWidget): void {
    this.widgets.set(type, widget)
  }

  // 获取组件
  getWidget(type: WidgetType): RegisteredWidget | undefined {
    return this.widgets.get(type)
  }

  // 获取所有组件
  getAllWidgets(): RegisteredWidget[] {
    return Array.from(this.widgets.values())
  }

  // 按分类获取组件
  getWidgetsByCategory(
    category: WidgetMetadata['category']
  ): RegisteredWidget[] {
    return this.getAllWidgets().filter(
      (w) => w.metadata.category === category
    )
  }

  // 获取组件元数据
  getWidgetMetadata(type: WidgetType): WidgetMetadata | undefined {
    return this.widgets.get(type)?.metadata
  }

  // 获取组件配置选项
  getWidgetConfigOptions(type: WidgetType): ConfigOption[] {
    const metadata = this.getWidgetMetadata(type)
    return metadata?.configOptions || []
  }

  // 获取组件默认配置
  getWidgetDefaultConfig(type: WidgetType): Record<string, unknown> {
    const metadata = this.getWidgetMetadata(type)
    if (!metadata) return {}

    const config: Record<string, unknown> = { ...metadata.defaultConfig }
    metadata.configOptions.forEach((option) => {
      if (!(option.key in config)) {
        config[option.key] = option.defaultValue
      }
    })

    return config
  }

  // 检查组件是否存在
  hasWidget(type: WidgetType): boolean {
    return this.widgets.has(type)
  }

  // 注销组件
  unregisterWidget(type: WidgetType): void {
    this.widgets.delete(type)
  }

  // 获取所有组件类型
  getWidgetTypes(): WidgetType[] {
    return Array.from(this.widgets.keys())
  }

  // 获取所有分类
  getCategories(): WidgetMetadata['category'][] {
    const categories = new Set<WidgetMetadata['category']>()
    this.widgets.forEach((widget) => {
      categories.add(widget.metadata.category)
    })
    return Array.from(categories)
  }

  // 注册默认组件
  private registerDefaultWidgets(): void {
    // 柱状图
    this.registerWidget('bar', {
      metadata: {
        type: 'bar',
        name: '柱状图',
        description: '展示分类数据的对比',
        icon: 'BarChart',
        category: 'chart',
        defaultSize: { w: 6, h: 4 },
        minSize: { w: 3, h: 3 },
        configOptions: [
          ...commonConfigOptions,
          ...chartConfigOptions,
          ...formatConfigOptions,
          ...interactionConfigOptions,
        ],
        defaultConfig: {
          type: 'bar',
        },
        dataRequirements: [
          { type: 'table', required: true, description: '选择数据表' },
          { type: 'field', required: true, description: '选择数值字段' },
          {
            type: 'aggregation',
            required: true,
            description: '选择聚合方式',
          },
          { type: 'groupBy', required: false, description: '选择分组字段' },
        ],
        supportsInteraction: true,
        supportsAnimation: true,
        supportsRealtime: true,
      },
    })

    // 折线图
    this.registerWidget('line', {
      metadata: {
        type: 'line',
        name: '折线图',
        description: '展示数据随时间的变化趋势',
        icon: 'TrendCharts',
        category: 'chart',
        defaultSize: { w: 6, h: 4 },
        minSize: { w: 3, h: 3 },
        configOptions: [
          ...commonConfigOptions,
          ...chartConfigOptions,
          ...formatConfigOptions,
          ...interactionConfigOptions,
        ],
        defaultConfig: {
          type: 'line',
        },
        dataRequirements: [
          { type: 'table', required: true, description: '选择数据表' },
          { type: 'field', required: true, description: '选择数值字段' },
          {
            type: 'aggregation',
            required: true,
            description: '选择聚合方式',
          },
          { type: 'groupBy', required: false, description: '选择分组字段' },
        ],
        supportsInteraction: true,
        supportsAnimation: true,
        supportsRealtime: true,
      },
    })

    // 饼图
    this.registerWidget('pie', {
      metadata: {
        type: 'pie',
        name: '饼图',
        description: '展示各部分占整体的比例',
        icon: 'PieChart',
        category: 'chart',
        defaultSize: { w: 4, h: 4 },
        minSize: { w: 3, h: 3 },
        configOptions: [
          ...commonConfigOptions,
          ...chartConfigOptions,
          ...formatConfigOptions,
          ...interactionConfigOptions,
        ],
        defaultConfig: {
          type: 'pie',
        },
        dataRequirements: [
          { type: 'table', required: true, description: '选择数据表' },
          { type: 'field', required: true, description: '选择数值字段' },
          {
            type: 'aggregation',
            required: true,
            description: '选择聚合方式',
          },
          { type: 'groupBy', required: false, description: '选择分组字段' },
        ],
        supportsInteraction: true,
        supportsAnimation: true,
        supportsRealtime: true,
      },
    })

    // 面积图
    this.registerWidget('area', {
      metadata: {
        type: 'area',
        name: '面积图',
        description: '强调数量随时间变化的程度',
        icon: 'Histogram',
        category: 'chart',
        defaultSize: { w: 6, h: 4 },
        minSize: { w: 3, h: 3 },
        configOptions: [
          ...commonConfigOptions,
          ...chartConfigOptions,
          ...formatConfigOptions,
          ...interactionConfigOptions,
        ],
        defaultConfig: {
          type: 'area',
        },
        dataRequirements: [
          { type: 'table', required: true, description: '选择数据表' },
          { type: 'field', required: true, description: '选择数值字段' },
          {
            type: 'aggregation',
            required: true,
            description: '选择聚合方式',
          },
          { type: 'groupBy', required: false, description: '选择分组字段' },
        ],
        supportsInteraction: true,
        supportsAnimation: true,
        supportsRealtime: true,
      },
    })

    // 散点图
    this.registerWidget('scatter', {
      metadata: {
        type: 'scatter',
        name: '散点图',
        description: '展示两个变量之间的关系',
        icon: 'CircleCheck',
        category: 'chart',
        defaultSize: { w: 6, h: 4 },
        minSize: { w: 3, h: 3 },
        configOptions: [
          ...commonConfigOptions,
          ...chartConfigOptions,
          ...formatConfigOptions,
          ...interactionConfigOptions,
        ],
        defaultConfig: {
          type: 'scatter',
        },
        dataRequirements: [
          { type: 'table', required: true, description: '选择数据表' },
          { type: 'field', required: true, description: '选择数值字段' },
          {
            type: 'aggregation',
            required: true,
            description: '选择聚合方式',
          },
          { type: 'groupBy', required: false, description: '选择分组字段' },
        ],
        supportsInteraction: true,
        supportsAnimation: true,
        supportsRealtime: true,
      },
    })

    // 数字卡片
    this.registerWidget('number', {
      metadata: {
        type: 'number',
        name: '数字卡片',
        description: '突出显示关键指标',
        icon: 'DataAnalysis',
        category: 'data',
        defaultSize: { w: 3, h: 2 },
        minSize: { w: 2, h: 2 },
        configOptions: [
          ...commonConfigOptions,
          ...formatConfigOptions,
          {
            key: 'valueFontSize',
            label: '数值字体大小',
            type: 'range',
            defaultValue: 32,
            min: 16,
            max: 72,
            step: 2,
            group: '字体',
          },
          {
            key: 'valueColor',
            label: '数值颜色',
            type: 'color',
            defaultValue: '#3b82f6',
            group: '字体',
          },
        ],
        defaultConfig: {
          type: 'number',
        },
        dataRequirements: [
          { type: 'table', required: true, description: '选择数据表' },
          { type: 'field', required: true, description: '选择数值字段' },
          {
            type: 'aggregation',
            required: true,
            description: '选择聚合方式',
          },
        ],
        supportsInteraction: false,
        supportsAnimation: true,
        supportsRealtime: true,
      },
    })

    // 数据表格
    this.registerWidget('table', {
      metadata: {
        type: 'table',
        name: '数据表格',
        description: '以表格形式展示详细数据',
        icon: 'Grid',
        category: 'data',
        defaultSize: { w: 6, h: 4 },
        minSize: { w: 4, h: 3 },
        configOptions: [
          ...commonConfigOptions,
          ...formatConfigOptions,
          {
            key: 'showHeader',
            label: '显示表头',
            type: 'boolean',
            defaultValue: true,
            group: '表格',
          },
          {
            key: 'showRowNumber',
            label: '显示行号',
            type: 'boolean',
            defaultValue: true,
            group: '表格',
          },
          {
            key: 'maxRows',
            label: '最大行数',
            type: 'range',
            defaultValue: 10,
            min: 5,
            max: 100,
            step: 5,
            group: '表格',
          },
        ],
        defaultConfig: {
          type: 'table',
        },
        dataRequirements: [
          { type: 'table', required: true, description: '选择数据表' },
          { type: 'field', required: true, description: '选择数值字段' },
          {
            type: 'aggregation',
            required: true,
            description: '选择聚合方式',
          },
          { type: 'groupBy', required: false, description: '选择分组字段' },
        ],
        supportsInteraction: true,
        supportsAnimation: false,
        supportsRealtime: true,
      },
    })

    // 时钟组件
    this.registerWidget('clock', {
      metadata: {
        type: 'clock',
        name: '时钟',
        description: '显示当前时间',
        icon: 'Clock',
        category: 'screen',
        defaultSize: { w: 2, h: 2 },
        minSize: { w: 2, h: 2 },
        configOptions: [
          ...commonConfigOptions,
          {
            key: 'showSeconds',
            label: '显示秒数',
            type: 'boolean',
            defaultValue: true,
            group: '显示',
          },
          {
            key: 'showDate',
            label: '显示日期',
            type: 'boolean',
            defaultValue: true,
            group: '显示',
          },
          {
            key: 'timeFormat',
            label: '时间格式',
            type: 'select',
            defaultValue: '24h',
            options: [
              { label: '24小时制', value: '24h' },
              { label: '12小时制', value: '12h' },
            ],
            group: '显示',
          },
        ],
        defaultConfig: {
          type: 'clock',
        },
        dataRequirements: [],
        supportsInteraction: false,
        supportsAnimation: true,
        supportsRealtime: true,
      },
    })

    // 日期组件
    this.registerWidget('date', {
      metadata: {
        type: 'date',
        name: '日期',
        description: '显示当前日期',
        icon: 'Calendar',
        category: 'screen',
        defaultSize: { w: 2, h: 1 },
        minSize: { w: 2, h: 1 },
        configOptions: [
          ...commonConfigOptions,
          {
            key: 'dateFormat',
            label: '日期格式',
            type: 'select',
            defaultValue: 'YYYY-MM-DD',
            options: [
              { label: 'YYYY-MM-DD', value: 'YYYY-MM-DD' },
              { label: 'YYYY年MM月DD日', value: 'YYYY年MM月DD日' },
              { label: 'MM/DD/YYYY', value: 'MM/DD/YYYY' },
              { label: 'DD/MM/YYYY', value: 'DD/MM/YYYY' },
            ],
            group: '显示',
          },
          {
            key: 'showWeekday',
            label: '显示星期',
            type: 'boolean',
            defaultValue: true,
            group: '显示',
          },
        ],
        defaultConfig: {
          type: 'date',
        },
        dataRequirements: [],
        supportsInteraction: false,
        supportsAnimation: false,
        supportsRealtime: false,
      },
    })

    // 跑马灯组件
    this.registerWidget('marquee', {
      metadata: {
        type: 'marquee',
        name: '跑马灯',
        description: '滚动显示通知信息',
        icon: 'ChatDotRound',
        category: 'screen',
        defaultSize: { w: 6, h: 1 },
        minSize: { w: 3, h: 1 },
        configOptions: [
          ...commonConfigOptions,
          {
            key: 'speed',
            label: '滚动速度',
            type: 'range',
            defaultValue: 2,
            min: 1,
            max: 10,
            step: 1,
            group: '行为',
          },
          {
            key: 'direction',
            label: '滚动方向',
            type: 'select',
            defaultValue: 'left',
            options: [
              { label: '向左', value: 'left' },
              { label: '向右', value: 'right' },
            ],
            group: '行为',
          },
          {
            key: 'content',
            label: '显示内容',
            type: 'string',
            defaultValue: '欢迎使用 Smart Table 数据仪表盘',
            group: '内容',
          },
        ],
        defaultConfig: {
          type: 'marquee',
        },
        dataRequirements: [],
        supportsInteraction: false,
        supportsAnimation: true,
        supportsRealtime: false,
      },
    })

    // KPI 指标卡片
    this.registerWidget('kpi', {
      metadata: {
        type: 'kpi',
        name: 'KPI 指标',
        description: '大屏专用 KPI 指标展示',
        icon: 'TrendCharts',
        category: 'screen',
        defaultSize: { w: 3, h: 2 },
        minSize: { w: 2, h: 2 },
        configOptions: [
          ...commonConfigOptions,
          ...formatConfigOptions,
          {
            key: 'showTrend',
            label: '显示趋势',
            type: 'boolean',
            defaultValue: true,
            group: '显示',
          },
          {
            key: 'showTarget',
            label: '显示目标',
            type: 'boolean',
            defaultValue: false,
            group: '显示',
          },
          {
            key: 'targetValue',
            label: '目标值',
            type: 'number',
            defaultValue: 100,
            group: '显示',
            condition: (config) => config.showTarget === true,
          },
        ],
        defaultConfig: {
          type: 'kpi',
        },
        dataRequirements: [
          { type: 'table', required: true, description: '选择数据表' },
          { type: 'field', required: true, description: '选择数值字段' },
          {
            type: 'aggregation',
            required: true,
            description: '选择聚合方式',
          },
        ],
        supportsInteraction: false,
        supportsAnimation: true,
        supportsRealtime: true,
      },
    })

    // 实时数据流
    this.registerWidget('realtime', {
      metadata: {
        type: 'realtime',
        name: '实时数据流',
        description: '实时展示数据变化',
        icon: 'VideoPlay',
        category: 'screen',
        defaultSize: { w: 6, h: 3 },
        minSize: { w: 4, h: 2 },
        configOptions: [
          ...commonConfigOptions,
          {
            key: 'maxDataPoints',
            label: '最大数据点数',
            type: 'range',
            defaultValue: 50,
            min: 10,
            max: 200,
            step: 10,
            group: '行为',
          },
          {
            key: 'showHistory',
            label: '显示历史',
            type: 'boolean',
            defaultValue: true,
            group: '显示',
          },
        ],
        defaultConfig: {
          type: 'realtime',
        },
        dataRequirements: [
          { type: 'table', required: true, description: '选择数据表' },
          { type: 'field', required: true, description: '选择数值字段' },
        ],
        supportsInteraction: false,
        supportsAnimation: true,
        supportsRealtime: true,
      },
    })
  }
}

export const widgetRegistry = new DashboardWidgetRegistry()
