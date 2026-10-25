/**
 * SmartTableDataSource - 智能数据源
 *
 * 基于 VTable CachedDataSource 实现，支持两种模式：
 * - 全量灌入模式（legacy）：updateMemoryCache(tableRecords, 0) 一次性灌入全量
 * - 懒加载模式（F5）：按需从 sourceRecords getter 取 batch + transform，内存与表大小解耦
 *
 * 懒加载模式核心收益：
 *   避免 updateTable() 入口处 transformRecords(sortedRecords.value) 的 O(N) 全量 transform。
 *   VTable 只对可见 ~30 行调用 get(index) → 只 transform 那一个 batch（~200 行）。
 *   maxCachedBatches 设小（5-10）→ LRU 真驱逐 → 内存占用 = batchSize × maxCachedBatches ≈ 1-2KB 常量。
 *
 * 注意：CachedDataSource 的 get() 必须同步返回，不能是 async —— VTable 对 Promise 对象
 * 不会正确 unwrap，会直接渲染为 "[object Promise]"。
 */

import { data as VTableData } from '@visactor/vtable';

export interface DataSourceRecord {
  _recordId: string;
  _originalRecord: any;
  _rowType?: string;
  [key: string]: any;
}

/**
 * 懒加载源配置
 */
export interface LazySourceConfig<T = any> {
  /** 取原始 records 的 getter（响应式），返回 RecordEntity[] */
  getSource: () => T[];
  /** 将原始 records 转换为 DataSourceRecord 的 transform 回调 */
  transformBatch: (rawRecords: T[]) => DataSourceRecord[];
  /** addButton 虚拟行 —— 不在 source 里但需要在最后一个 index 渲染 */
  addButtonRow?: DataSourceRecord | null;
}

export class SmartTableDataSource {
  // 内存缓存：按批次起始索引存储记录数组（每个数组长度 = batchSize，空位为 null）
  private memoryCache = new Map<number, DataSourceRecord[]>();

  // LRU 访问队列（front=最久未访问, back=最近访问）
  private accessQueue: number[] = [];

  // 最大缓存批次数（超过后驱逐最久未使用的批次；0 表示不限制）
  private maxCachedBatches = 0;

  // F5 prefetch：距当前 batch 末尾多少行内触发预取下一批
  private static readonly PREFETCH_THRESHOLD = 50;
  // F5 prefetch：记录正在预取的 batchKey，防重复
  private _prefetching = new Set<number>();

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

  // ===== F5 懒加载配置 =====
  private lazySource: LazySourceConfig | null = null;

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
    this.cachedDataSource = new VTableData.CachedDataSource({
      get: (index: number): DataSourceRecord | null => {
        // F5 懒加载路径：memoryCache miss 时按需拉取
        const batchKey = Math.floor(index / this.batchSize) * this.batchSize;
        let batch = this.memoryCache.get(batchKey);

        if (!batch && this.lazySource) {
          batch = this.fetchLazyBatch(batchKey);
        }

        if (batch) {
          this.touchBatch(batchKey);

          // F5 prefetch：index 命中但接近 batch 末尾 → 异步预取下一批
          // 用户滚得快时，下一个 get(index) miss 的概率大 — 提前准备好消除空白行
          const offset = index - batchKey;
          if (
            this.lazySource &&
            batchKey + this.batchSize < this._totalCount &&  // 还有下一批
            offset >= this.batchSize - SmartTableDataSource.PREFETCH_THRESHOLD  // 距末尾 < 阈值
          ) {
            const nextBatchKey = batchKey + this.batchSize;
            // 防重复：缓存里已有、正在预取、或已到末尾 → 跳过
            if (
              !this.memoryCache.has(nextBatchKey) &&
              !this._prefetching.has(nextBatchKey) &&
              nextBatchKey < this._totalCount
            ) {
              this._prefetching.add(nextBatchKey);
              // setTimeout(0) 让当前 get() 先同步返回，prefetch 不阻塞可见行渲染
              setTimeout(() => {
                try { this.fetchLazyBatch(nextBatchKey); } catch (_) {}
                this._prefetching.delete(nextBatchKey);
              }, 0);
            }
          }

          return batch[index - batchKey] || null;
        }
        return null;
      },
      length: this._totalCount,
    });

    // 统一 length 访问器（让外部 appendRecords / updateTotalCount 能同步 VTable 感知）
    Object.defineProperty(this.cachedDataSource, 'length', {
      get: () => this._totalCount,
      configurable: true,
    });
  }

  /**
   * F5：配置懒加载数据源
   * 调用后 get(index) 会在 memoryCache miss 时按需从 sourceRecords getter 取 batch + transform
   */
  configureLazySource(config: LazySourceConfig, totalCount: number): void {
    this.lazySource = config;
    this._totalCount = totalCount;

    // F7-2：每次 configure 都清空旧回调，避免累积
    this._batchLoadedCallbacks = [];

    // 预取最后一个 batch（若包含 addButton 虚拟行）
    // VTable 初始只渲染可见 ~30 行，addButton 在最后一个 index，永远不会被初始 get(index) 请求
    // 不预取 → addButton 位置返回 null → 表格末尾没有 "+" 按钮
    if (config.addButtonRow && totalCount > 0) {
      const lastIndex = totalCount - 1;
      const lastBatchKey = Math.floor(lastIndex / this.batchSize) * this.batchSize;
      // 如果最后一个 batch 同时覆盖首屏可见区就不用重复取（get 会在渲染时触发）
      if (lastBatchKey > 0) {
        this.fetchLazyBatch(lastBatchKey);
      }
    }

    // ========== 关键修复：预灌所有 batch 进 cache ==========
    // VTable initTreeHierarchyState 在 ListTable 初始化 dataSource 时会遍历 0..totalCount
    // 所有 index 同步调 get(index)，即使非树形视图也走这个全量遍历。
    // configureLazySource 刚 clearCache 完 → 全部 cache miss → 每个 get 都触发
    // fetchLazyBatch + transformBatch → O(totalCount) 次同步串行调用 → 主线程阻塞数十秒。
    // 修复：configure 结束前一次性预灌所有已加载的 batch，让后续 VTable 全量遍历时
    // 每个 get(index) 只是 Map.get + 数组索引 → O(1) → 总耗时退化为 O(totalBatches)。
    if (totalCount > 0) {
      this.preloadAllBatches();
    }
  }

  /**
   * F5：预灌所有 batch 到 memoryCache
   * 解决 VTable initTreeHierarchyState 遍历 0..totalCount 调 get(index) 时
   * cache miss 导致的 O(totalCount) 次 fetchLazyBatch + transform 串行阻塞
   *
   * 同时临时关闭 LRU 驱逐：records 全量在前端时，raw records 已经占了内存，
   * transform cache 全量保留反而让所有 get(index) 都 O(1) 命中，
   * LRU 驱逐后再按需 fetch 的收益远小于主线程阻塞的代价。
   *
   * 注意：只预灌 sourceRecords 实际覆盖的 batch（流式加载过程中 records 还没全量时，
   * 对空 batch 做 fetchLazyBatch 是 O(1) 空操作，但仍有 Map 开销）。
   * initTreeHierarchyState 遍历 totalCount 全量 index 时，空 batch 的 get(index) 会 miss
   * 并触发 fetchLazyBatch 处理空切片，但空切片的 transform 是 O(1)，整体可接受。
   */
  preloadAllBatches(): void {
    if (!this.lazySource || this._totalCount === 0) return;

    const batchSize = this.batchSize;
    const sourceRecords = this.lazySource.getSource();
    const totalBatches = Math.ceil(this._totalCount / batchSize);

    // 只预灌 sourceRecords 实际覆盖的 batch + 1（addButton 虚拟行的 batch）
    const coveredBatches = Math.min(
      totalBatches,
      Math.ceil((sourceRecords.length + (this.lazySource.addButtonRow ? 1 : 0)) / batchSize) + 1
    );

    // 临时关闭 LRU 驱逐，让预灌的 batch 留在 cache 里
    this.maxCachedBatches = 0;

    for (let b = 0; b < coveredBatches; b++) {
      const batchKey = b * batchSize;
      if (!this.memoryCache.has(batchKey)) {
        this.fetchLazyBatch(batchKey);
      }
    }
  }

  /**
   * F5：按需拉取一个 batch 的数据
   * 返回 batch 数组（长度 = batchSize），已填入 memoryCache
   */
  private fetchLazyBatch(batchKey: number): DataSourceRecord[] | undefined {
    if (!this.lazySource) return undefined;

    const sourceRecords = this.lazySource.getSource();
    const batchSize = this.batchSize;

    // 创建空 batch
    const batch: DataSourceRecord[] = new Array(batchSize).fill(null);

    const sourceLen = sourceRecords.length;
    const hasAddButton = !!this.lazySource.addButtonRow;

    // 从 sourceRecords 切片（addButton 虚拟行在 source 之外，不影响切片范围）
    const sliceStart = Math.max(0, batchKey);
    const sliceEnd = Math.min(sourceLen, batchKey + batchSize);
    if (sliceStart < sourceLen) {
      const rawChunk = sourceRecords.slice(sliceStart, sliceEnd);
      const transformed = this.lazySource.transformBatch(rawChunk);
      for (let i = 0; i < transformed.length; i++) {
        batch[i] = transformed[i];
      }
    }

    // 处理 addButton 虚拟行 —— 它可能落在当前 batch 里
    if (hasAddButton) {
      const addButtonIndex = this._totalCount - 1;
      if (addButtonIndex >= batchKey && addButtonIndex < batchKey + batchSize) {
        batch[addButtonIndex - batchKey] = this.lazySource.addButtonRow!;
      }
    }

    // 写入 memoryCache
    this.memoryCache.set(batchKey, batch);
    this.touchBatch(batchKey);
    this.evictIfNeeded();

    // F7-2：通知外部这个 batch 已加载（用于渐进加载 LINK 显示数据等）
    this._fireBatchLoaded(batchKey, batch);

    return batch;
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
   * F7-2：获取当前缓存中的 record IDs（不含 null 空位和 addButton 虚拟行）
   * 配合 loadLinkDisplayData 只按需扫描可见范围内的 records，避免 O(N) 全量扫
   */
  getCachedRecordIds(): string[] {
    const ids: string[] = [];
    for (const batch of this.memoryCache.values()) {
      for (const rec of batch) {
        if (rec && rec._recordId && !rec._rowType) {
          ids.push(rec._recordId);
        }
      }
    }
    return ids;
  }

  /**
   * 是否有懒加载源（F5 模式）
   */
  get hasLazySource(): boolean {
    return !!this.lazySource;
  }

  /**
   * F7-2：注册 batch 加载完成回调
   * fetchLazyBatch 每次加载完一个新 batch 后会触发这些回调，
   * 用于懒加载模式下渐进加载关联字段显示数据等后处理
   */
  private _batchLoadedCallbacks: Array<(batchKey: number, records: DataSourceRecord[]) => void> = [];

  onBatchLoaded(cb: (batchKey: number, records: DataSourceRecord[]) => void): void {
    this._batchLoadedCallbacks.push(cb);
  }

  /**
   * F7-2：清空所有 batchLoaded 回调（configureLazySource 内部会自动调）
   */
  clearBatchLoadedCallbacks(): void {
    this._batchLoadedCallbacks = [];
  }

  private _fireBatchLoaded(batchKey: number, batch: DataSourceRecord[]): void {
    if (this._batchLoadedCallbacks.length === 0) return;
    for (const cb of this._batchLoadedCallbacks) {
      try { cb(batchKey, batch); } catch (_) { /* 回调异常不影响主流程 */ }
    }
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
   * 批量更新内存缓存 —— F2 单行快路径 / 流式加载时写入 pre-transformed 数据
   * 直接写入 cache，**不受** lazySource 覆盖（写入的数据优先）
   * 自动处理跨批次边界——records 数据量可能超过单个 batch，会拆分写入多个批次数组
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
        this.touchBatch(batchKey);
      }

      for (let i = 0; i < chunk.length; i++) {
        batch[localIdx + i] = chunk[i];
      }

      remaining = remaining.slice(spaceInBatch);
      currentStart += spaceInBatch;
    }

    this.evictIfNeeded();
  }

  /**
   * 标记数据全部加载完成
   */
  markFullyLoaded(): void {
    this._fullyLoaded = true;
    const stats = this.getPerformanceStats();
    console.log(
      `[SmartTableDataSource] 数据加载完成: ${stats.totalRecords} 条, ` +
      `${stats.cachedBatches}/${stats.totalBatches} 批次已缓存` +
      (stats.maxCachedBatches > 0 ? `(上限 ${stats.maxCachedBatches})` : '') +
      `, 总耗时 ${stats.totalTimeMs}ms`
    );
  }

  /**
   * 更新总记录数（同步 VTable CachedDataSource.length）
   */
  updateTotalCount(count: number): void {
    this._totalCount = count;
    if (this.cachedDataSource) {
      Object.defineProperty(this.cachedDataSource, 'length', {
        get: () => this._totalCount,
        configurable: true,
      });
    }
  }

  /**
   * 追加记录到数据源末尾 —— F3 增量 append 快路径用
   * 同时更新 internal count + CachedDataSource.length，使 VTable 感知行数变化
   */
  appendRecords(records: DataSourceRecord[]): void {
    const startIndex = this._totalCount;
    this.updateMemoryCache(records, startIndex);
    this._totalCount += records.length;
    if (this.cachedDataSource) {
      Object.defineProperty(this.cachedDataSource, 'length', {
        get: () => this._totalCount,
        configurable: true,
      });
    }
  }

  /**
   * 清除所有缓存 —— 同时重置 fullyLoaded
   * 注意：不清除 lazySource 配置（那是数据源契约，不是运行时状态）
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
   * LRU 驱逐 — 超过 maxCachedBatches 阈值时驱逐最久未访问的批次
   */
  private evictIfNeeded(): void {
    if (this.maxCachedBatches <= 0) return;
    if (this.memoryCache.size <= this.maxCachedBatches) return;

    const targetCount = Math.max(Math.floor(this.maxCachedBatches * 0.8), 1);
    while (this.memoryCache.size > targetCount && this.accessQueue.length > 1) {
      const oldest = this.accessQueue.shift();
      if (oldest !== undefined && this.memoryCache.has(oldest)) {
        this.memoryCache.delete(oldest);
      }
    }
  }
}
