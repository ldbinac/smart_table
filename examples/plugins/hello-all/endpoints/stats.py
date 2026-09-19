# Hello Panel · 自定义后端接口示例 2：stats（读取记录做服务端聚合）
#
# 前端调用方式（见 ../main.js 的 callStats）：
#   await SDK.request("backend.call", {
#     name: "stats",
#     payload: { tableId: "<TABLE_ID>", fieldId: "<FIELD_ID>" },
#   })
#
# 演示点：
#   - 一个插件可声明多个 endpoints（manifest.endpoints 数组），
#     前端以 name 调用，各自可配置 timeout（默认 30s，封顶 300s）；
#   - endpoint 与脚本插件共用同一受限沙箱与权限模型：
#     base.list_records 需 manifest permissions.records:read；
#   - payload 可携带前端上下文（如表格页里选中的 tableId/fieldId）。

payload = (request.get("payload") or {})
table_id = payload.get("tableId") or (context.get("table_id") or "")
field_id = payload.get("fieldId") or ""

if not table_id:
    # 返回 error 字段 → 宿主将本次调用标记为 failed（失败约定）
    set_result({"error": "missing tableId in payload"})
else:
    resp = base.list_records(table_id, page=1, per_page=100)
    items = resp.get("items") or []
    total = resp.get("total", len(items))

    filled = 0
    empty = 0
    for item in items:
        value = (item.get("values") or {}).get(field_id) if field_id else None
        if value in (None, ""):
            empty += 1
        else:
            filled += 1

    base.log("stats: table=%s field=%s sampled=%d" % (table_id, field_id, len(items)))
    set_result({
        "tableId": table_id,
        "fieldId": field_id,
        "total": total,        # 记录总数（含未采样页）
        "sampled": len(items), # 本次实际采样条数（首屏 100 条）
        "filled": filled,      # 指定字段非空条数
        "empty": empty,        # 指定字段空值条数
    })
