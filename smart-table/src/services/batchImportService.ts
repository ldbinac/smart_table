import { batchCreateRecords, createRecord } from "@/services/api/recordApiService";
import { t } from "@/i18n";

export interface BatchConfig {
  batchSize: number;
  maxRetries: number;
  baseDelay: number;
  timeout: number;
  minDelay: number;
  maxDelay: number;
  enableDynamicDelay: boolean;
  /** 顺序导入模式：逐条调用 createRecord，保证自动编号严格按行序递增；默认 false=批量模式 */
  sequentialMode?: boolean;
}

export const DEFAULT_BATCH_CONFIG: BatchConfig = {
  batchSize: 100,
  maxRetries: 3,
  baseDelay: 600,
  timeout: 30000,
  minDelay: 200,
  maxDelay: 5000,
  enableDynamicDelay: true,
};

export interface BatchProgress {
  totalBatches: number;
  completedBatches: number;
  currentBatch: number;
  totalRecords: number;
  successCount: number;
  failedCount: number;
  startTime: number;
  estimatedTimeRemaining: number;
  elapsedTime: number;
  status: BatchStatus;
  currentBatchResponseTime: number;
  averageBatchTime: number;
}

export type BatchStatus = "idle" | "running" | "paused" | "completed" | "cancelled" | "error";

export interface BatchError {
  batchIndex: number;
  rowRange: { start: number; end: number };
  message: string;
  retryCount: number;
  details?: string;
}

export interface BatchResult {
  successCount: number;
  failedCount: number;
  errors: BatchError[];
  totalTime: number;
  status: BatchStatus;
  /** 与输入行序对齐的记录 ID（行创建失败/批次失败时为 null） */
  recordIdByRow: (string | null)[];
}

interface BatchRecord {
  values: Record<string, unknown>;
  _originalIndex?: number;
}

function splitIntoBatches<T>(items: T[], batchSize: number): T[][] {
  const batches: T[][] = [];
  for (let i = 0; i < items.length; i += batchSize) {
    batches.push(items.slice(i, Math.min(i + batchSize, items.length)));
  }
  return batches;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function calculateBackoff(retryCount: number): number {
  return Math.min(1000 * Math.pow(2, retryCount) + Math.random() * 500, 10000);
}

export class BatchImportController {
  private _cancelled = false;
  private _paused = false;
  private _resolvePause: (() => void) | null = null;
  private _config: BatchConfig;
  private _onProgress: ((progress: BatchProgress) => void) | null = null;
  private _progress: BatchProgress;
  private _responseTimes: number[] = [];
  private _currentDelay: number;

  constructor(config: Partial<BatchConfig> = {}) {
    this._config = { ...DEFAULT_BATCH_CONFIG, ...config };
    this._currentDelay = this._config.baseDelay;
    this._progress = this._createInitialProgress();
  }

  private _createInitialProgress(): BatchProgress {
    return {
      totalBatches: 0,
      completedBatches: 0,
      currentBatch: 0,
      totalRecords: 0,
      successCount: 0,
      failedCount: 0,
      startTime: 0,
      estimatedTimeRemaining: 0,
      elapsedTime: 0,
      status: "idle",
      currentBatchResponseTime: 0,
      averageBatchTime: 0,
    };
  }

  get progress(): BatchProgress {
    return { ...this._progress };
  }

  get isCancelled(): boolean {
    return this._cancelled;
  }

  onProgress(callback: (progress: BatchProgress) => void): void {
    this._onProgress = callback;
  }

  cancel(): void {
    this._cancelled = true;
    this._progress.status = "cancelled";
    if (this._resolvePause) {
      this._resolvePause();
      this._resolvePause = null;
    }
  }

  pause(): void {
    this._paused = true;
    this._progress.status = "paused";
  }

  resume(): void {
    if (this._paused && this._resolvePause) {
      this._resolvePause();
      this._resolvePause = null;
    }
    this._paused = false;
    this._progress.status = "running";
  }

  private async _waitIfPaused(): Promise<void> {
    while (this._paused) {
      await new Promise<void>((resolve) => {
        this._resolvePause = resolve;
      });
    }
  }

  private _updateDelay(responseTime: number): void {
    if (!this._config.enableDynamicDelay) return;
    this._responseTimes.push(responseTime);
    const avgTime =
      this._responseTimes.reduce((a, b) => a + b, 0) / this._responseTimes.length;

    if (responseTime > avgTime * 1.5) {
      this._currentDelay = Math.min(
        this._currentDelay * 1.3,
        this._config.maxDelay,
      );
    } else if (responseTime < avgTime * 0.5 && this._responseTimes.length > 3) {
      this._currentDelay = Math.max(
        this._currentDelay * 0.9,
        this._config.minDelay,
      );
    }
  }

  private _updateProgress(): void {
    const elapsed = Date.now() - this._progress.startTime;
    this._progress.elapsedTime = elapsed;

    if (this._progress.completedBatches > 0) {
      const avgBatchTime = elapsed / this._progress.completedBatches;
      this._progress.averageBatchTime = avgBatchTime;
      const remaining = this._progress.totalBatches - this._progress.completedBatches;
      this._progress.estimatedTimeRemaining = remaining * avgBatchTime;
    }

    if (this._onProgress) {
      this._onProgress(this._progress);
    }
  }

  async execute(
    tableId: string,
    rawRecords: Record<string, unknown>[],
  ): Promise<BatchResult> {
    this._cancelled = false;
    this._paused = false;
    this._responseTimes = [];
    this._currentDelay = this._config.baseDelay;

    const sequentialMode = !!this._config.sequentialMode;

    const errors: BatchError[] = [];
    let successCount = 0;
    let failedCount = 0;
    const recordIdByRow: (string | null)[] = new Array(rawRecords.length).fill(null);

    // totalBatches 在两种模式下语义通用：批量模式=批次数，顺序模式=行数
    const totalUnits = rawRecords.length;

    this._progress = {
      ...this._createInitialProgress(),
      totalBatches: totalUnits,
      totalRecords: rawRecords.length,
      startTime: Date.now(),
      status: "running",
    };

    this._updateProgress();

    if (sequentialMode) {
      // ========== 顺序导入模式：逐条调 createRecord ==========
      await this._executeSequential(tableId, rawRecords, errors, recordIdByRow, (s, f) => {
        successCount = s;
        failedCount = f;
      });
    } else {
      // ========== 批量导入模式（原有逻辑） ==========
      await this._executeBatch(tableId, rawRecords, errors, recordIdByRow, (s, f) => {
        successCount = s;
        failedCount = f;
      });
    }

    const result: BatchResult = {
      successCount,
      failedCount,
      errors,
      totalTime: Date.now() - this._progress.startTime,
      status: this._cancelled ? "cancelled" : errors.length > 0 && successCount === 0 ? "error" : "completed",
      recordIdByRow,
    };

    this._progress.status = result.status;
    this._updateProgress();

    return result;
  }

  /** 顺序导入：逐条调 createRecord，保证自动编号严格按行序 */
  private async _executeSequential(
    tableId: string,
    rawRecords: Record<string, unknown>[],
    errors: BatchError[],
    recordIdByRow: (string | null)[],
    setCounts: (success: number, failed: number) => void,
  ): Promise<void> {
    let successCount = 0;
    let failedCount = 0;

    for (let rowIndex = 0; rowIndex < rawRecords.length; rowIndex++) {
      if (this._cancelled) break;

      await this._waitIfPaused();
      if (this._cancelled) break;

      this._progress.currentBatch = rowIndex + 1;
      this._updateProgress();

      const values = rawRecords[rowIndex];
      const rowNum = rowIndex + 1;
      let rowSuccess = false;
      let lastError: string | null = null;

      for (let retry = 0; retry <= this._config.maxRetries; retry++) {
        if (this._cancelled) break;
        await this._waitIfPaused();
        if (this._cancelled) break;

        if (retry > 0) {
          await sleep(calculateBackoff(retry));
        }

        const rowStartTime = performance.now();

        try {
          const controller = new AbortController();
          const timeoutId = setTimeout(() => controller.abort(), this._config.timeout);

          const record = await createRecord(tableId, values);
          clearTimeout(timeoutId);

          const responseTime = performance.now() - rowStartTime;
          this._progress.currentBatchResponseTime = responseTime;
          this._updateDelay(responseTime);

          successCount += 1;
          recordIdByRow[rowIndex] = record.id ?? null;
          rowSuccess = true;
          break;
        } catch (error: unknown) {
          const errorMessage =
            error instanceof Error ? error.message : t("common.unknownError");
          lastError = errorMessage;

          if (error instanceof Error && error.message.includes("429")) {
            await sleep(calculateBackoff(retry + 2));
            continue;
          }

          if (retry < this._config.maxRetries) {
            continue;
          }

          failedCount += 1;
          errors.push({
            batchIndex: rowIndex,
            rowRange: { start: rowNum, end: rowNum },
            message: errorMessage,
            retryCount: retry,
            details: error instanceof Error ? error.stack : undefined,
          });
        }
      }

      if (!rowSuccess && !lastError) {
        failedCount += 1;
        errors.push({
          batchIndex: rowIndex,
          rowRange: { start: rowNum, end: rowNum },
          message: t('common.importCancelled'),
          retryCount: 0,
        });
      }

      this._progress.completedBatches = rowIndex + 1;
      this._progress.successCount = successCount;
      this._progress.failedCount = failedCount;
      setCounts(successCount, failedCount);
      this._updateProgress();

      // 顺序导入节奏稍慢，行之间不需要额外 sleep
    }

    setCounts(successCount, failedCount);
  }

  /** 批量导入：原有逻辑，每 batchSize 条调一次 batchCreateRecords */
  private async _executeBatch(
    tableId: string,
    rawRecords: Record<string, unknown>[],
    errors: BatchError[],
    recordIdByRow: (string | null)[],
    setCounts: (success: number, failed: number) => void,
  ): Promise<void> {
    let successCount = 0;
    let failedCount = 0;

    const recordsWithIndex: BatchRecord[] = rawRecords.map((values, i) => ({
      values,
      _originalIndex: i,
    }));

    const batches = splitIntoBatches(recordsWithIndex, this._config.batchSize);
    // 批量模式下 totalBatches 应为批次数（之前已设为 rawRecords.length，修正）
    this._progress.totalBatches = batches.length;

    for (let batchIndex = 0; batchIndex < batches.length; batchIndex++) {
      if (this._cancelled) break;

      await this._waitIfPaused();
      if (this._cancelled) break;

      this._progress.currentBatch = batchIndex + 1;
      this._updateProgress();

      const batch = batches[batchIndex];
      const batchPayload = batch.map((r) => ({ values: r.values }));
      const rowStart = batch[0]._originalIndex! + 1;
      const rowEnd = batch[batch.length - 1]._originalIndex! + 1;

      let batchSuccess = false;
      let lastError: string | null = null;

      for (let retry = 0; retry <= this._config.maxRetries; retry++) {
        if (this._cancelled) break;
        await this._waitIfPaused();
        if (this._cancelled) break;

        if (retry > 0) {
          const backoffTime = calculateBackoff(retry);
          await sleep(backoffTime);
        }

        const batchStartTime = performance.now();

        try {
          const controller = new AbortController();
          const timeoutId = setTimeout(() => controller.abort(), this._config.timeout);

          const result = await batchCreateRecords(tableId, batchPayload);
          clearTimeout(timeoutId);

          const responseTime = performance.now() - batchStartTime;
          this._progress.currentBatchResponseTime = responseTime;
          this._updateDelay(responseTime);

          successCount += result.created_count;
          // 按 record_ids 与批内顺序对齐，回填到原始行索引
          if (Array.isArray(result.record_ids) && result.record_ids.length === batch.length) {
            batch.forEach((r, i) => {
              recordIdByRow[r._originalIndex!] = result.record_ids[i] ?? null;
            });
          }
          batchSuccess = true;
          break;
        } catch (error: unknown) {
          const errorMessage =
            error instanceof Error ? error.message : t("common.unknownError");
          lastError = errorMessage;

          if (error instanceof Error && error.message.includes("429")) {
            const backoffTime = calculateBackoff(retry + 2);
            await sleep(backoffTime);
            continue;
          }

          if (retry < this._config.maxRetries) {
            continue;
          }

          failedCount += batch.length;
          errors.push({
            batchIndex,
            rowRange: { start: rowStart, end: rowEnd },
            message: errorMessage,
            retryCount: retry,
            details: error instanceof Error ? error.stack : undefined,
          });
        }
      }

      if (!batchSuccess && !lastError) {
        failedCount += batch.length;
        errors.push({
          batchIndex,
          rowRange: { start: rowStart, end: rowEnd },
          message: t('common.importCancelled'),
          retryCount: 0,
        });
      }

      this._progress.completedBatches = batchIndex + 1;
      this._progress.successCount = successCount;
      this._progress.failedCount = failedCount;
      setCounts(successCount, failedCount);
      this._updateProgress();

      if (batchIndex < batches.length - 1 && !this._cancelled) {
        await sleep(this._currentDelay);
      }
    }

    setCounts(successCount, failedCount);
  }
}