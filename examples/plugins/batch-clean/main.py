# -*- coding: utf-8 -*-
"""
Batch Clean —— 后端脚本示例插件

运行环境由宿主注入：
  base     受限 base 代理对象（方法见下方使用）
  context  {"plugin_id", "base_id", "table_id"(可选)}
  config   插件在当前 Base 的生效配置（manifest.configSchema 校验后）
  set_result(v)  设置脚本最终返回结果（也会将 result 变量作为放回值）

可用 base 方法（均按触发者身份 + 插件权限在宿主侧鉴权）：
  base.list_tables()                       -> [{id, name, description}]
  base.get_fields(table_id)                -> [{id, name, type}]
  base.list_records(table_id, page, per_page) -> {items: [{id, values}], total}
  base.get_record(record_id)               -> {id, values}
  base.create_record(table_id, values)     -> {id}
  base.update_record(record_id, values)    -> {id}
  base.delete_record(record_id)            -> {deleted: True}
  base.get_config()                        -> dict
  base.log(message)                        print 也会自动进运行日志

注意：本脚本运行在受限子进程中，仅允许白名单模块（json/re/math/datetime/...），
无网络/文件系统/系统访问能力；每次数据操作都通过 stdio 协议帧由宿主代理执行。

打包：将本目录 manifest.json 与本文件压为 .stplugin.zip 上传安装。
"""
from collections import Counter

# 目标参数来自插件配置（configSchema 已校验存在）
table_id = config.get("tableId") or context.get("table_id")
field_id = config.get("fieldId")
fill_value = config.get("fillValue", "")

if not table_id or not field_id:
    base.log("缺少 tableId/fieldId 配置，无法执行")
    set_result({"updated": 0, "skipped": 0, "error": "missing tableId/fieldId"})
else:
    page = 1
    per_page = 100
    updated = 0
    skipped = 0
    field_value_counter = Counter()

    while True:
        resp = base.list_records(table_id, page=page, per_page=per_page)
        items = resp.get("items") or []
        if not items:
            break

        for rec in items:
            values = rec.get("values") or {}
            current = values.get(field_id)
            field_value_counter[repr(current)] += 1
            # 仅填充空值（None / 空串 / 空列表），其余保持不变
            if current in (None, "", [], {}):
                base.update_record(rec["id"], {field_id: fill_value})
                updated += 1
            else:
                skipped += 1

        if len(items) < per_page:
            break
        page += 1

    summary = {
        "updated": updated,
        "skipped": skipped,
        "valueDistribution": dict(field_value_counter),
        "fillValue": fill_value,
    }
    base.log("Batch clean 完成：更新 %d 条，跳过 %d 条" % (updated, skipped))
    set_result(summary)
