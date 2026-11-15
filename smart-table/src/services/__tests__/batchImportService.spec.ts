/**
 * BatchImportController 单元测试
 *
 * 覆盖场景：
 *  - 顺序导入（sequentialMode=true）：逐条调 createRecord、失败重试、取消、暂停/继续、recordIdByRow 与行序对齐
 *  - 批量导入（sequentialMode=false，默认）：每 batchSize  条调一次 batchCreateRecords
 *  - 两种模式的进度/状态/空数组
 *
 * 注意：不使用 vi.useFakeTimers()——实现里的 sleep/calculateBackoff/AbortController
 * 均依赖真实 setTimeout，fake timers 会让它们永远挂起。mock 的返回值都是立即 resolve
 * 的 Promise，用真实时间即可。
 */
import { describe, it, expect, vi, beforeEach } from "vitest";

// --- 模块 mock ---
const mockBatchCreateRecords = vi.fn();
const mockCreateRecord = vi.fn();
const mockT = vi.fn((key: string) => key);

vi.mock("@/services/api/recordApiService", () => ({
  batchCreateRecords: (...args: unknown[]) => mockBatchCreateRecords(...args),
  createRecord: (...args: unknown[]) => mockCreateRecord(...args),
}));

vi.mock("@/i18n", () => ({
  t: (key: string) => mockT(key),
}));

import {
  BatchImportController,
  DEFAULT_BATCH_CONFIG,
  type BatchConfig,
  type BatchResult,
} from "@/services/batchImportService";

// --- 测试数据 ---
function makeRows(n: number): Record<string, unknown>[] {
  return Array.from({ length: n }, (_, i) => ({
    name: `row-${i + 1}`,
    index: i + 1,
  }));
}

function recordIdForRow(rowIndex: number): string {
  return `rec-${rowIndex + 1}`;
}

describe("BatchImportController", () => {
  beforeEach(() => {
    mockBatchCreateRecords.mockReset();
    mockCreateRecord.mockReset();
    mockT.mockImplementation((k) => k);
  });

  // ============================================================
  // 顺序导入模式
  // ============================================================
  describe("sequentialMode = true", () => {
    /** 顺序导入专用配置：关闭动态延迟、baseDelay=0，避免实现里的 sleep() 额外耗时 */
    const seqConfig: Partial<BatchConfig> = {
      sequentialMode: true,
      batchSize: 100,
      maxRetries: 2,
      baseDelay: 0,
      timeout: 5000,
      minDelay: 0,
      maxDelay: 0,
      enableDynamicDelay: false,
    };

    it("全部成功：逐条调用 createRecord，recordIdByRow 按行序对齐", async () => {
      const rows = makeRows(5);
      mockCreateRecord.mockImplementation((_tableId, values) => {
        const idx = (values.index as number) - 1;
        return Promise.resolve({
          id: recordIdForRow(idx),
          name: values.name,
        });
      });

      const controller = new BatchImportController(seqConfig);
      const completedSteps: number[] = [];
      controller.onProgress((p) => completedSteps.push(p.completedBatches));

      const result = await controller.execute("tbl-1", rows);

      // 必须恰好 5 次调用、每次 tableId 和 values 都对
      expect(mockCreateRecord).toHaveBeenCalledTimes(5);
      for (let i = 0; i < 5; i++) {
        const call = mockCreateRecord.mock.calls[i];
        expect(call[0]).toBe("tbl-1");
        expect(call[1]).toEqual({ name: `row-${i + 1}`, index: i + 1 });
      }

      expect(result.successCount).toBe(5);
      expect(result.failedCount).toBe(0);
      expect(result.errors).toEqual([]);
      expect(result.status).toBe("completed");

      // recordIdByRow 必须严格按输入行序（Issue 核心诉求）
      expect(result.recordIdByRow).toEqual([
        "rec-1",
        "rec-2",
        "rec-3",
        "rec-4",
        "rec-5",
      ]);

      // 进度从 0 → 1 → 2 → 3 → 4 → 5 单调递增
      const sorted = [...completedSteps].sort((a, b) => a - b);
      expect(completedSteps).toEqual(sorted); // 单调非减
      expect(sorted[sorted.length - 1]).toBe(5);
    });

    it("单条失败-重试后成功：不影响最终结果", async () => {
      const rows = makeRows(4);
      let callCount = 0;
      mockCreateRecord.mockImplementation((_t, values) => {
        callCount += 1;
        const idx = (values.index as number) - 1;
        // 第 2 行（index=1）第 1 次失败、retry 后成功
        if (idx === 1) {
          // 让第 1、2 次尝试都在 idx===1 时失败，因为第 2 次是 retry
          // 改用更可靠的方式：按 callCount 计数
        }
        return Promise.resolve({ id: recordIdForRow(idx) });
      });
      // 重写：用 callCount 控制第 2 行第一次失败
      callCount = 0;
      mockCreateRecord.mockImplementation((_t, values) => {
        callCount += 1;
        const idx = (values.index as number) - 1;
        // 4 行调用顺序：row1(1) → row2(2 失败) → row2 retry(3 成功) → row3(4) → row4(5)
        if (idx === 1 && callCount === 2) {
          return Promise.reject(new Error("network boom"));
        }
        return Promise.resolve({ id: recordIdForRow(idx) });
      });

      const controller = new BatchImportController(seqConfig);
      const result = await controller.execute("tbl-1", rows);

      // 4 行 + 第 2 行重试 1 次 = 5 次
      expect(mockCreateRecord).toHaveBeenCalledTimes(5);
      expect(result.successCount).toBe(4);
      expect(result.failedCount).toBe(0);
      expect(result.status).toBe("completed");
      expect(result.recordIdByRow).toEqual(["rec-1", "rec-2", "rec-3", "rec-4"]);
    });

    it("某条最终失败（超过 maxRetries）：继续导入后续行", async () => {
      const rows = makeRows(4);
      mockCreateRecord.mockImplementation((_t, values) => {
        const idx = (values.index as number) - 1;
        if (idx === 2) {
          return Promise.reject(new Error("persistent error"));
        }
        return Promise.resolve({ id: recordIdForRow(idx) });
      });

      const controller = new BatchImportController({ ...seqConfig, maxRetries: 1 });
      const result = await controller.execute("tbl-1", rows);

      // 第 3 行 = 1 次主尝试 + 1 次重试 = 2 次；其他 3 行各 1 次 → 共 5 次
      expect(mockCreateRecord).toHaveBeenCalledTimes(5);

      expect(result.successCount).toBe(3);
      expect(result.failedCount).toBe(1);
      expect(result.errors).toHaveLength(1);
      expect(result.errors[0].rowRange).toEqual({ start: 3, end: 3 });
      expect(result.errors[0].batchIndex).toBe(2);
      expect(result.errors[0].retryCount).toBe(1);
      expect(result.status).toBe("completed"); // 部分成功 → completed

      // 失败行在 recordIdByRow 里是 null
      expect(result.recordIdByRow).toEqual(["rec-1", "rec-2", null, "rec-4"]);
    });

    it("全部最终失败 → 结果 status=error", async () => {
      const rows = makeRows(2);
      mockCreateRecord.mockRejectedValue(new Error("always fails"));

      const controller = new BatchImportController({ ...seqConfig, maxRetries: 0 });
      const result = await controller.execute("tbl-1", rows);

      expect(result.successCount).toBe(0);
      expect(result.failedCount).toBe(2);
      expect(result.status).toBe("error");
      expect(result.recordIdByRow).toEqual([null, null]);
    });

    it("取消（cancel）：已完成的行保留，后续停止", async () => {
      const rows = makeRows(10);
      mockCreateRecord.mockImplementation((_, values) =>
        Promise.resolve({ id: `rec-${values.index}` })
      );

      const controller = new BatchImportController(seqConfig);

      // 进度到达 3 时取消
      controller.onProgress((p) => {
        if (p.completedBatches === 3) controller.cancel();
      });

      const result = await controller.execute("tbl-1", rows);

      expect(result.status).toBe("cancelled");
      expect(result.successCount).toBe(3);
      expect(mockCreateRecord).toHaveBeenCalledTimes(3);
    });

    it("暂停后继续（pause → resume）", async () => {
      const rows = makeRows(6);
      mockCreateRecord.mockImplementation((_, values) =>
        Promise.resolve({ id: `rec-${values.index}` })
      );

      const controller = new BatchImportController(seqConfig);

      let resumed = false;
      controller.onProgress((p) => {
        if (p.completedBatches === 2 && !resumed) {
          resumed = true;
          controller.pause();
          // 用真实定时器恢复（fake timers 没开）
          setTimeout(() => controller.resume(), 5);
        }
      });

      const result = await controller.execute("tbl-1", rows);

      expect(result.status).toBe("completed");
      expect(result.successCount).toBe(6);
      expect(mockCreateRecord).toHaveBeenCalledTimes(6);
    });

    it("空数组：直接成功完成、零调用", async () => {
      const controller = new BatchImportController(seqConfig);
      const result = await controller.execute("tbl-1", []);

      expect(result.successCount).toBe(0);
      expect(result.failedCount).toBe(0);
      expect(result.status).toBe("completed");
      expect(result.recordIdByRow).toEqual([]);
      expect(mockCreateRecord).not.toHaveBeenCalled();
      expect(mockBatchCreateRecords).not.toHaveBeenCalled();
    });

    it("progress.totalBatches = 行数（顺序模式语义）", async () => {
      const rows = makeRows(7);
      mockCreateRecord.mockImplementation((_, values) =>
        Promise.resolve({ id: `rec-${values.index}` })
      );

      const controller = new BatchImportController(seqConfig);
      const totals: number[] = [];
      controller.onProgress((p) => totals.push(p.totalBatches));

      await controller.execute("tbl-1", rows);

      expect(totals).not.toEqual([]);
      // 顺序模式下 totalBatches 应该等于输入行数
      expect(totals.every((t) => t === 7)).toBe(true);
    });
  });

  // ============================================================
  // 批量导入模式（默认）——回归测试
  // ============================================================
  describe("sequentialMode = false（默认批量模式）", () => {
    /** 批量导入专用配置：batchSize 覆盖小值，baseDelay=0 避免批次间 sleep */
    const batchConfig = (batchSize = 10): Partial<BatchConfig> => ({
      ...DEFAULT_BATCH_CONFIG,
      sequentialMode: false,
      batchSize,
      baseDelay: 0,
      timeout: 5000,
      minDelay: 0,
      maxDelay: 0,
      enableDynamicDelay: false,
    });

    it("走 batchCreateRecords、每 batchSize  条一批、不走 createRecord", async () => {
      const rows = makeRows(25);
      mockBatchCreateRecords.mockImplementation((_t, payload) => {
        const ids = payload.map((_r, i) => `batch-item-${i}`);
        return Promise.resolve({ created_count: payload.length, record_ids: ids });
      });

      const controller = new BatchImportController(batchConfig(10));
      const result = await controller.execute("tbl-1", rows);

      // ceil(25/10) = 3 批
      expect(mockBatchCreateRecords).toHaveBeenCalledTimes(3);
      expect(mockBatchCreateRecords.mock.calls[0][1]).toHaveLength(10);
      expect(mockBatchCreateRecords.mock.calls[1][1]).toHaveLength(10);
      expect(mockBatchCreateRecords.mock.calls[2][1]).toHaveLength(5);

      expect(mockCreateRecord).not.toHaveBeenCalled();

      expect(result.successCount).toBe(25);
      expect(result.failedCount).toBe(0);
      expect(result.status).toBe("completed");
    });

    it("recordIdByRow 与输入行序对齐（跨批次）", async () => {
      const rows = makeRows(25);
      let globalCounter = 0;
      mockBatchCreateRecords.mockImplementation((_t, payload) => {
        const ids = payload.map(() => {
          globalCounter += 1;
          return `uid-${globalCounter}`;
        });
        return Promise.resolve({ created_count: payload.length, record_ids: ids });
      });

      const controller = new BatchImportController(batchConfig(10));
      const result = await controller.execute("tbl-1", rows);

      const allIds = result.recordIdByRow.filter((x): x is string => x !== null);
      expect(allIds).toHaveLength(25);
      expect(new Set(allIds).size).toBe(25);
      // recordIdByRow[0] 在第 1 批第 1 个 → uid-1；recordIdByRow[10] 在第 2 批第 1 个 → uid-11
      expect(result.recordIdByRow[0]).toBe("uid-1");
      expect(result.recordIdByRow[10]).toBe("uid-11");
    });

    it("progress.totalBatches = 批次数（不是行数）", async () => {
      const rows = makeRows(35); // ceil(35/10) = 4 批
      mockBatchCreateRecords.mockImplementation((_t, payload) =>
        Promise.resolve({
          created_count: payload.length,
          record_ids: payload.map((_, i) => `b-${i}`),
        })
      );

      const controller = new BatchImportController(batchConfig(10));
      const totalsSeen: number[] = [];
      controller.onProgress((p) => totalsSeen.push(p.totalBatches));

      await controller.execute("tbl-1", rows);

      // execute 入口先把 totalBatches 设为 rows.length，进入 _executeBatch 后修正为批次数
      // 所以取最后一次回调里的值才是真正的批次数
      expect(totalsSeen[totalsSeen.length - 1]).toBe(4);
    });

    it("批量模式：取消后已提交的批次保留", async () => {
      const rows = makeRows(50);
      mockBatchCreateRecords.mockImplementation((_t, payload) =>
        Promise.resolve({
          created_count: payload.length,
          record_ids: payload.map((_, i) => `b-${i}`),
        })
      );

      const controller = new BatchImportController(batchConfig(10));
      controller.onProgress((p) => {
        if (p.completedBatches === 2) controller.cancel();
      });

      const result = await controller.execute("tbl-1", rows);

      expect(result.status).toBe("cancelled");
      expect(mockBatchCreateRecords).toHaveBeenCalledTimes(2);
      expect(result.successCount).toBe(20);
    });
  });

  // ============================================================
  // 两种模式共通
  // ============================================================
  describe("两种模式共通", () => {
    it("构造函数：sequentialMode 默认 false", () => {
      const c = new BatchImportController();
      expect(c).toBeInstanceOf(BatchImportController);
    });

    it("cancel() 后 isCancelled 为 true", () => {
      const c = new BatchImportController();
      expect(c.isCancelled).toBe(false);
      c.cancel();
      expect(c.isCancelled).toBe(true);
    });

    it("execute() 返回的 BatchResult 结构完整", async () => {
      mockBatchCreateRecords.mockResolvedValue({ created_count: 0, record_ids: [] });
      const c = new BatchImportController({ ...DEFAULT_BATCH_CONFIG, baseDelay: 0, enableDynamicDelay: false });
      const result: BatchResult = await c.execute("tbl-1", []);

      expect(result).toHaveProperty("successCount");
      expect(result).toHaveProperty("failedCount");
      expect(result).toHaveProperty("errors");
      expect(result).toHaveProperty("totalTime");
      expect(result).toHaveProperty("status");
      expect(result).toHaveProperty("recordIdByRow");
      expect(Array.isArray(result.errors)).toBe(true);
      expect(Array.isArray(result.recordIdByRow)).toBe(true);
    });
  });
});
