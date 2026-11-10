import { describe, it, expect } from "vitest";
import { getApiErrorMessage } from "../apiError";

const FALLBACK = "编辑保存失败";

describe("getApiErrorMessage", () => {
  it("优先展示接口响应体里的 message", () => {
    const error = {
      message: "无权修改该记录",
      response: {
        data: { code: 403, message: "无权修改该记录", success: false },
      },
    };
    expect(getApiErrorMessage(error, FALLBACK)).toBe("无权修改该记录");
  });

  it("响应体 message 优先于 Error.message", () => {
    const error = {
      message: "Request failed with status code 403",
      response: { data: { message: "无权修改该记录" } },
    };
    expect(getApiErrorMessage(error, FALLBACK)).toBe("无权修改该记录");
  });

  it("仅有 Error.message 时使用该 message", () => {
    expect(getApiErrorMessage(new Error("无权修改该记录"), FALLBACK)).toBe(
      "无权修改该记录",
    );
  });

  it("兼容直接挂在 data 上的 message", () => {
    expect(
      getApiErrorMessage({ data: { message: "字段校验失败" } }, FALLBACK),
    ).toBe("字段校验失败");
  });

  it("message 字段不存在时回退到固定文案", () => {
    expect(
      getApiErrorMessage(
        { response: { data: { code: 403, success: false } } },
        FALLBACK,
      ),
    ).toBe(FALLBACK);
    expect(
      getApiErrorMessage(
        new Error("Request failed with status code 403"),
        FALLBACK,
      ),
    ).toBe(FALLBACK);
    expect(getApiErrorMessage(new Error("Forbidden"), FALLBACK)).toBe(
      FALLBACK,
    );
  });

  it("message 为空白或非字符串时回退", () => {
    expect(
      getApiErrorMessage({ response: { data: { message: "   " } } }, FALLBACK),
    ).toBe(FALLBACK);
    expect(
      getApiErrorMessage({ response: { data: { message: 403 } } }, FALLBACK),
    ).toBe(FALLBACK);
  });

  it("异常不是对象时回退", () => {
    expect(getApiErrorMessage(null, FALLBACK)).toBe(FALLBACK);
    expect(getApiErrorMessage(undefined, FALLBACK)).toBe(FALLBACK);
    expect(getApiErrorMessage("cancel", FALLBACK)).toBe(FALLBACK);
    expect(getApiErrorMessage(403, FALLBACK)).toBe(FALLBACK);
  });
});
