/**
 * SmartTableDataSource - 异步懒加载数据源
 *
 * 基于 VTable CachedDataSource 模式实现的智能数据源，
 * 支持数据流式加载 + 按需渲染，优化大批量数据场景下的首屏加载和内存占用。
 *
 * 工作原理：
 * 1. VTable 仅对可见行调用 get(index) 获取数据（同步返回内存缓存）
 * 2. 数据通过内存缓存查找，预取通过异步 fire-and-forget 在后台执行
 * 3. 流式加载过程中，数据渐进填充内存缓存，VTable 自动刷新可见区域
 * 4. LRU 淘汰策略：超过 maxCachedBatches 阈值时驱逐最久未访问的批次
 *
 * 注意：CachedDataSource 的 get() 必须同步返回，VTable 对于 async 函数
 * 返回的 Promise 不会正确 unwrap，会直接将 Promise 对象渲染为 "[object Promise]"。
 */

import { data as VTableData } from '@visactor/vtable';

export interface DataSourceRecord {
  _recordId: string;
  _originalRecord: any;
  _rowType?: string;
  [key: string]: any;
}

export class SmartTableDataSource {
  // 内存缓存：按批次索引存储记录数组
  private memoryCache = new Map<number, DataSourceRecord[]>();

  // LRU 访问队列（front=最久未访问, back=最近访问）
  private accessQueue: number[] = [];

  // 最大缓存批次数（超过后驱逐最久未使用的批次；0 表示不限制）
  private maxCachedBatches = 0;

  // 记录总数
  private _totalCount = 0;

  // 数据是否全部加载完成
  private _fullyLoaded = false;

  // 批次大小
  private batchSize = 100;

  // VTable 原生 CachedDataSource 实例
  private cachedDataSource: any;

  // 性能计时
  private loadStartTime = 0;

  constructor(options: {
    totalCount: number;
    batchSize?: number;
    maxCachedBatches?: number;
  }) {
    this._totalCount = options.totalCount;
    this.batchSize = options.batchSize || 100;
    this.maxCachedBatches = options.maxCachedBatches ?? 0;
    this.loadStartTime = performance.now();

    // 创建 VTable CachedDataSource —— get 必须同步返回，不能是 async
    // async 函数返回的 Promise 会被 VTable 当成数据直接渲染
    this.cachedDataSource = new VTableData.CachedDataSource({
      get: (index: number): DataSourceRecord | null => {
        const batchKey = Math.floor(index / this.batchSize) * this.batchSize;
        const batch = this.memoryCache.get(batchKey);
        if (batch) {
          // 更新 LRU：将当前批次移到队列末尾（最近使用）
          this.touchBatch(batchKey);
          return batch[index - batchKey] || null;
        }
        return null;
      },
      length: this._totalCount,
    });
  }

  /**
   * 获取 VTable 可用的 dataSource 对象
   * 用于 ListTable 构造函数 config.dataSource
   */
  get dataSource(): any {
    return this.cachedDataSource;
  }

  /**
   * 获取记录总数
   */
  get totalCount(): number {
    return this._totalCount;
  }

  /**
   * 是否全部加载完成
   */
  get fullyLoaded(): boolean {
    return this._fullyLoaded;
  }

  /**
   * 获取性能统计信息
   */
  getPerformanceStats(): {
    totalTimeMs: number;
    cachedBatches: number;
    totalBatches: number;
    maxCachedBatches: number;
    totalRecords: number;
  } {
    return {
      totalTimeMs: Math.round(performance.now() - this.loadStartTime),
      cachedBatches: this.memoryCache.size,
      totalBatches: Math.ceil(this._totalCount / this.batchSize),
      maxCachedBatches: this.maxCachedBatches,
      totalRecords: this._totalCount,
    };
  }

  /**
   * 批量更新内存缓存（由流式加载过程调用，将新加载的记录写入缓存）
   * 自动处理跨批次边界——records 数据量可能超过单个 batch，会拆分写入多个批次数组
   * 写入新批次后检查 LRU 阈值，驱逐最久未访问的批次
   */
  updateMemoryCache(records: DataSourceRecord[], startIndex: number): void {
    let remaining = records;
    let currentStart = startIndex;

    while (remaining.length > 0) {
      const batchKey = Math.floor(currentStart / this.batchSize) * this.batchSize;
      const localIdx = currentStart - batchKey;
      const spaceInBatch = this.batchSize - localIdx;
      const chunk = remaining.slice(0, spaceInBatch);

      let batch = this.memoryCache.get(batchKey);
      if (!batch) {
        batch = new Array(this.batchSize).fill(null);
        this.memoryCache.set(batchKey, batch);
        // 新批次加入访问队列（标记为最近使用）
        this.touchBatch(batchKey);
      }

      for (let i = 0; i < chunk.length; i++) {
        batch[localIdx + i] = chunk[i];
      }

      remaining = remaining.slice(spaceInBatch);
      currentStart += spaceInBatch;
    }

    // 写入完成后检查 LRU 阈值
    this.evictIfNeeded();
  }

  /**
   * 标记数据全部加载完成
   */
  markFullyLoaded(): void {
    this._fullyLoaded = true;

    // 输出性能统计
    const stats = this.getPerformanceStats();
    console.log(
      `[SmartTableDataSource] 数据加载完成: ${stats.totalRecords} 条, ` +
      `${stats.cachedBatches}/${stats.totalBatches} 批次已缓存` +
      (stats.maxCachedBatches > 0 ? `(上限 ${stats.maxCachedBatches})` : '') +
      `, 总耗时 ${stats.totalTimeMs}ms`
    );
  }

  /**
   * 更新总记录数（用于分页/流式加载场景）
   * 注意：VTable 的 CachedDataSource length 在创建时固定，此方法更新内部计数
   * 元信息，VTable 不会感知此变更——流式加载期间通过此字段追踪已加载数量
   */
  updateTotalCount(count: number): void {
    this._totalCount = count;
  }

  /**
   * 追加记录到数据源末尾并同步 VTable CachedDataSource 的长度
   *
   * 与 updateTotalCount 的区别：
   * - updateTotalCount 仅更新内部计数（用于流式加载追踪），不通知 VTable
   * - appendRecords 同时更新内部计数和 CachedDataSource.length，
   *   使 VTable 感知到数据行数变化（如添加新记录行场景），
   *   后续调用 renderWithRecreateCells 即可正确渲染追加的行
   *
   * 这是修复「添加记录后 addButton 行消失」问题的关键：
   * CachedDataSource 的 length 在构造函数中固定为初始 totalCount，
   * 追加记录时若不同步更新 length，VTable 不会渲染超出原始长度的行。
   */
  appendRecords(records: DataSourceRecord[]): void {
    const startIndex = this._totalCount;
    this.updateMemoryCache(records, startIndex);
    this._totalCount += records.length;
    // 同步 VTable CachedDataSource 的 length，使其感知到行数变化
    if (this.cachedDataSource) {
      Object.defineProperty(this.cachedDataSource, 'length', {
        get: () => this._totalCount,
        configurable: true,
      });
    }
  }

  /**
   * 清除所有缓存
   */
  clearCache(): void {
    this.memoryCache.clear();
    this.accessQueue = [];
    this._fullyLoaded = false;
    this.loadStartTime = performance.now();
  }

  /**
   * 标记批次为最近使用（移到访问队列末尾）
   */
  private touchBatch(batchKey: number): void {
    const idx = this.accessQueue.indexOf(batchKey);
    if (idx >= 0) {
      this.accessQueue.splice(idx, 1);
    }
    this.accessQueue.push(batchKey);
  }

  /**
   * 检查并执行 LRU 驱逐
   * 当缓存批次数超过 maxCachedBatches（且 > 0）时，
   * 从队列前端（最久未使用）开始驱逐，直到低于阈值
   */
  private evictIfNeeded(): void {
    if (this.maxCachedBatches <= 0) return;
    if (this.memoryCache.size <= this.maxCachedBatches) return;

    const targetCount = Math.max(Math.floor(this.maxCachedBatches * 0.8), 1);
    while (this.memoryCache.size > targetCount && this.accessQueue.length > 1) {
      // 从队首取出最久未访问的批次（跳过最后一个批次——保留当前正在写入的）
      const oldest = this.accessQueue.shift();
      if (oldest !== undefined && this.memoryCache.has(oldest)) {
        this.memoryCache.delete(oldest);
      }
    }
  }
}