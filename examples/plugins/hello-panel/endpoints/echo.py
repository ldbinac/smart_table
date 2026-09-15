# Hello Panel · 自定义后端接口示例 1：echo（多 endpoint 声明演示）
#
# 前端调用方式（见 ../main.js 的 callEcho）：
#   await SDK.request("backend.call", { name: "echo", payload: { hello: "world" } })
#
# 运行位置：宿主受限沙箱子进程（与脚本插件一致）——
#   无网络 / 文件系统 / 系统访问能力，每次数据操作经 stdio 协议帧
#   由宿主按触发者身份代理执行并鉴权。
#
# 注入对象：
#   base      受限代理对象（base.list_tables / base.get_fields / base.list_records …）
#   context   { plugin_id, base_id, table_id? }
#   config    当前 Base 的生效配置（base 深合并 global）
#   request   { endpoint, payload, user_id }   ← 仅 backend.call 模式注入
#   set_result(v)  设置返回给前端的 JSON 结果
#
# 失败约定：结果 dict 含非空 "error" 字段或抛异常 → 宿主整体标记 failed。

payload = (request.get("payload") or {})

table_count = 0
try:
    # 受宿主代理 + permissions.tables:read 约束
    table_count = len(base.list_tables())
except Exception as e:
    base.log("list_tables failed: " + str(e))

set_result({
    "echo": payload,
    # 触发者身份（经宿主按当前用户 JWT 传入，插件拿不到原始凭证）
    "user_id": request.get("user_id"),
    "base_id": context.get("base_id"),
    "table_count": table_count,
})
