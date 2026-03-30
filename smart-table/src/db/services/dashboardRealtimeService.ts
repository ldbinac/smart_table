// Vue ref 暂时未使用，但保留以备将来扩展
// import { ref, type Ref } from 'vue'
import { recordService } from './recordService'
import type { RecordEntity } from '../schema'
// WidgetConfig 暂时未使用，但保留以备将来扩展
// import type { WidgetConfig } from './dashboardService'

export interface RefreshConfig {
  enabled: boolean
  interval: number
  autoRefresh: boolean
}

export interface DataChangeEvent {
  tableId: string
  recordId?: string
  action: 'create' | 'update' | 'delete'
  timestamp: number
}

export interface WidgetDataState {
  widgetId: string
  tableId: string
  records: RecordEntity[]
  lastUpdated: number
  isLoading: boolean
  error?: string
}

export type DataUpdateCallback = (tableId: string, records: RecordEntity[]) => void
export type DataChangeListener = (event: DataChangeEvent) => void

export class DashboardRealtimeService {
  private refreshTimers: Map<string, number> = new Map()
  private dataCache: Map<string, RecordEntity[]> = new Map()
  private widgetStates: Map<string, WidgetDataState> = new Map()
  private dataChangeListeners: Set<DataChangeListener> = new Set()
  private updateCallbacks: Map<string, Set<DataUpdateCallback>> = new Map()
  private lastFetchTime: Map<string, number> = new Map()

  // 防抖时间（毫秒）
  private readonly DEBOUNCE_TIME = 500
  // 最小刷新间隔（毫秒）
  private readonly MIN_REFRESH_INTERVAL = 1000

  // 注册数据变化监听
  onDataChange(listener: DataChangeListener): () => void {
    this.dataChangeListeners.add(listener)
    return () => {
      this.dataChangeListeners.delete(listener)
    }
  }

  // 触发数据变化事件
  private emitDataChange(event: DataChangeEvent): void {
    this.dataChangeListeners.forEach((listener) => {
      try {
        listener(event)
      } catch (error) {
        console.error('数据变化监听器执行错误:', error)
      }
    })
  }

  // 注册数据更新回调
  subscribeToTable(tableId: string, callback: DataUpdateCallback): () => void {
    if (!this.updateCallbacks.has(tableId)) {
      this.updateCallbacks.set(tableId, new Set())
    }
    this.updateCallbacks.get(tableId)!.add(callback)

    // 立即返回缓存数据
    const cached = this.dataCache.get(tableId)
    if (cached) {
      callback(tableId, cached)
    }

    return () => {
      this.updateCallbacks.get(tableId)?.delete(callback)
    }
  }

  // 通知数据更新
  private notifyDataUpdate(tableId: string, records: RecordEntity[]): void {
    const callbacks = this.updateCallbacks.get(tableId)
    if (callbacks) {
      callbacks.forEach((callback) => {
        try {
          callback(tableId, records)
        } catch (error) {
          console.error('数据更新回调执行错误:', error)
        }
      })
    }
  }

  // 获取组件数据状态
  getWidgetState(widgetId: string): WidgetDataState | undefined {
    return this.widgetStates.get(widgetId)
  }

  // 设置组件数据状态
  setWidgetState(widgetId: string, state: Partial<WidgetDataState>): void {
    const existing = this.widgetStates.get(widgetId)
    if (existing) {
      this.widgetStates.set(widgetId, { ...existing, ...state })
    } else {
      this.widgetStates.set(widgetId, {
        widgetId,
        tableId: '',
        records: [],
        lastUpdated: Date.now(),
        isLoading: false,
        ...state,
      })
    }
  }

  // 加载表数据（带缓存）
  async loadTableData(
    tableId: string,
    forceRefresh = false
  ): Promise<RecordEntity[]> {
    const now = Date.now()
    const lastFetch = this.lastFetchTime.get(tableId) || 0
    const cached = this.dataCache.get(tableId)

    // 如果缓存有效且不需要强制刷新，返回缓存
    if (!forceRefresh && cached && now - lastFetch < this.DEBOUNCE_TIME) {
      return cached
    }

    try {
      const records = await recordService.getRecordsByTable(tableId)
      const oldRecords = this.dataCache.get(tableId)
      this.dataCache.set(tableId, records)
      this.lastFetchTime.set(tableId, now)

      // 检测数据变化
      if (oldRecords) {
        this.detectDataChanges(tableId, oldRecords, records)
      }

      // 通知订阅者
      this.notifyDataUpdate(tableId, records)

      return records
    } catch (error) {
      console.error(`加载表 ${tableId} 数据失败:`, error)
      throw error
    }
  }

  // 检测数据变化
  private detectDataChanges(
    tableId: string,
    oldRecords: RecordEntity[],
    newRecords: RecordEntity[]
  ): void {
    const oldMap = new Map(oldRecords.map((r) => [r.id, r]))
    const newMap = new Map(newRecords.map((r) => [r.id, r]))

    // 检测新增
    for (const [id, record] of newMap) {
      if (!oldMap.has(id)) {
        this.emitDataChange({
          tableId,
          recordId: id,
          action: 'create',
          timestamp: Date.now(),
        })
      } else if (
        JSON.stringify(oldMap.get(id)) !== JSON.stringify(record)
      ) {
        // 检测更新
        this.emitDataChange({
          tableId,
          recordId: id,
          action: 'update',
          timestamp: Date.now(),
        })
      }
    }

    // 检测删除
    for (const [id] of oldMap) {
      if (!newMap.has(id)) {
        this.emitDataChange({
          tableId,
          recordId: id,
          action: 'delete',
          timestamp: Date.now(),
        })
      }
    }
  }

  // 启动自动刷新
  startAutoRefresh(
    widgetId: string,
    tableId: string,
    interval: number,
    callback: (records: RecordEntity[]) => void
  ): void {
    // 停止现有的刷新
    this.stopAutoRefresh(widgetId)

    // 确保间隔不小于最小值
    const safeInterval = Math.max(interval, this.MIN_REFRESH_INTERVAL)

    // 立即执行一次
    this.refreshWidgetData(widgetId, tableId, callback)

    // 设置定时器
    const timerId = window.setInterval(() => {
      this.refreshWidgetData(widgetId, tableId, callback)
    }, safeInterval)

    this.refreshTimers.set(widgetId, timerId)
  }

  // 停止自动刷新
  stopAutoRefresh(widgetId: string): void {
    const timerId = this.refreshTimers.get(widgetId)
    if (timerId) {
      window.clearInterval(timerId)
      this.refreshTimers.delete(widgetId)
    }
  }

  // 刷新组件数据
  private async refreshWidgetData(
    widgetId: string,
    tableId: string,
    callback: (records: RecordEntity[]) => void
  ): Promise<void> {
    this.setWidgetState(widgetId, { isLoading: true, error: undefined })

    try {
      const records = await this.loadTableData(tableId, true)
      this.setWidgetState(widgetId, {
        isLoading: false,
        lastUpdated: Date.now(),
        records,
      })
      callback(records)
    } catch (error) {
      this.setWidgetState(widgetId, {
        isLoading: false,
        error: error instanceof Error ? error.message : '数据加载失败',
      })
    }
  }

  // 手动刷新组件
  async refreshWidget(widgetId: string, tableId: string): Promise<RecordEntity[]> {
    this.setWidgetState(widgetId, { isLoading: true, error: undefined })

    try {
      const records = await this.loadTableData(tableId, true)
      this.setWidgetState(widgetId, {
        isLoading: false,
        lastUpdated: Date.now(),
        records,
      })
      return records
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : '数据加载失败'
      this.setWidgetState(widgetId, {
        isLoading: false,
        error: errorMessage,
      })
      throw error
    }
  }

  // 批量刷新多个组件
  async refreshWidgets(
    widgets: Array<{ widgetId: string; tableId: string }>
  ): Promise<void> {
    // 按表ID分组，避免重复请求
    const tableGroups = new Map<string, string[]>()
    widgets.forEach(({ widgetId, tableId }) => {
      if (!tableGroups.has(tableId)) {
        tableGroups.set(tableId, [])
      }
      tableGroups.get(tableId)!.push(widgetId)
    })

    // 并行加载所有表数据
    const promises = Array.from(tableGroups.entries()).map(
      async ([tableId, widgetIds]) => {
        try {
          const records = await this.loadTableData(tableId, true)
          widgetIds.forEach((widgetId) => {
            this.setWidgetState(widgetId, {
              isLoading: false,
              lastUpdated: Date.now(),
              records,
            })
          })
        } catch (error) {
          const errorMessage =
            error instanceof Error ? error.message : '数据加载失败'
          widgetIds.forEach((widgetId) => {
            this.setWidgetState(widgetId, {
              isLoading: false,
              error: errorMessage,
            })
          })
        }
      }
    )

    await Promise.all(promises)
  }

  // 获取缓存的表数据
  getCachedData(tableId: string): RecordEntity[] | undefined {
    return this.dataCache.get(tableId)
  }

  // 清除缓存
  clearCache(tableId?: string): void {
    if (tableId) {
      this.dataCache.delete(tableId)
      this.lastFetchTime.delete(tableId)
    } else {
      this.dataCache.clear()
      this.lastFetchTime.clear()
    }
  }

  // 清除组件状态
  clearWidgetState(widgetId?: string): void {
    if (widgetId) {
      this.widgetStates.delete(widgetId)
      this.stopAutoRefresh(widgetId)
    } else {
      this.widgetStates.clear()
      this.refreshTimers.forEach((timerId) => {
        window.clearInterval(timerId)
      })
      this.refreshTimers.clear()
    }
  }

  // 销毁服务
  destroy(): void {
    this.clearWidgetState()
    this.clearCache()
    this.dataChangeListeners.clear()
    this.updateCallbacks.clear()
  }
}

export const dashboardRealtimeService = new DashboardRealtimeService()
