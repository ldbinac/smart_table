# SmartTable 插件开发者指南

本文面向第三方开发者，说明如何基于 SmartTable 插件体系开发、打包、调试与上架插件。阅读前建议先了解《插件体系架构设计》中"插件清单规范""权限模型""通信接口"三节。

---

## 1. 插件形态速览

| 形态 | `manifest.type` | 运行位置 | 通信方式 | 典型场景 |
| ---- | -------------- | -------- | -------- | -------- |
| 前端 UI 插件 | `ui` | 浏览器 iframe（`sandbox="allow-scripts"`，opaque origin） | postMessage JSON-RPC（握手 token 鉴权） | 工具栏按钮、侧边面板、自定义交互 |
| 后端脚本插件 | `script` | 受控子进程（受限 builtins + 白名单 import） | stdio 协议帧由宿主代理执行表格 API | 批量数据处理、定时/手动触发的自动化 |

两种形态共用同一套清单、生命周期、权限与配置机制。首期不支持插件间依赖，仅支持宿主版本兼容声明（`engines`）。

---

## 2. 清单（manifest.json）

打包根目录必须包含 `manifest.json`，核心字段如下：

| 字段 | 类型 | 说明 |
| ---- | ---- | ---- |
| `id` | string | 全局唯一插件 ID，建议反向域名（如 `com.yourorg.demo`） |
| `name` | string | 展示名称 |
| `description` | string | 简介 |
| `author` | object | `{ name?, url?, email? }` |
| `version` | string | SemVer，如 `1.0.0`；升级时须高于已装版本 |
| `type` | `"ui" \| "script"` | 插件形态 |
| `apiVersion` | string | SDK 协议版本，当前为 `"1"` |
| `engines.smarttable` | string | 宿主版本兼容范围，如 `">=1.7.0 <2.0.0"` |
| `entry` | string | 入口文件名（UI 为 JS，script 为 py） |
| `permissions` | object | 权限声明（见第 3 节） |
| `extensionPoints` | array | UI 扩展点声明（仅 `ui` 类型） |
| `configSchema` | object | 配置 JSON Schema（可选） |
| `script.timeout` | number | 后端脚本超时（秒，可选，封顶 300） |

### 2.1 对象式分级权限

```json
"permissions": {
  "records": "read" | "write",   // 记录读写
  "tables":  "read" | "write",   // 表结构读写
  "storage": true,               // 插件自有 KV（localStorage）
  "network": ["api.example.com"] // 允许外联域名（首期预留）
}
```

未声明的权限点，宿主侧直接拒绝对应调用（deny by default）。对象式结构为未来"限定表/字段"等细粒度权限预留演进空间。

### 2.2 UI 扩展点

```json
"extensionPoints": [
  { "type": "toolbar-button", "title": "批量填充", "icon": "Star" },
  { "type": "side-panel",     "title": "填充面板" }
]
```

支持类型：`toolbar-button`（工具栏按钮）、`side-panel`（右侧 Drawer 中的 iframe）、`base-menu`（Base 级菜单）、`record-detail-block`（记录详情区块）。插件通过清单声明式注册，宿主在启用后自动挂载，无需修改宿主代码。

---

## 3. 前端 UI 插件开发

### 3.1 运行沙箱与 SDK

UI 插件在 iframe 中运行，宿主以同源 URL 加载但 `sandbox="allow-scripts"`（不带 `allow-same-origin`），使插件获得 **opaque origin**（`event.origin === "null"`），天然无法访问宿主 Cookie / localStorage / DOM。

宿主提供 loader HTML 并向插件注入全局对象 `window.SmartTableSDK`：

- `SmartTableSDK.ready(cb)`：握手完成后回调，回调参数为 `sdk`
- `sdk.request(method, params)`：发起 RPC 调用，返回 `Promise`
- `sdk.request("ui.getContext")` → `{ pluginId, baseId, tableId }`

### 3.2 可用方法（受 `permissions` 约束）

| 方法 | 所需权限 | 说明 |
| ---- | -------- | ---- |
| `ui.getContext()` | — | 获取当前上下文 |
| `ui.notify({ message, type })` | — | 弹提示 |
| `config.get()` | —（隐含授予） | 读取生效配置（base 合并 global） |
| `storage.get/set/remove({ key, value })` | `storage` | 插件自有 KV |
| `table.getSchema({ tableId })` | `tables:read` | 表结构 + 字段 |
| `table.listTables()` | `tables:read` | 当前 Base 的表列表 |
| `table.getRecords({ tableId, page, per_page, search })` | `records:read` | 分页读取记录 |
| `record.get({ recordId })` | `records:read` | 单条记录 |
| `record.create({ tableId, values })` | `records:write` | 创建记录 |
| `record.update({ recordId, values })` | `records:write` | 更新记录 |
| `record.delete({ recordId })` | `records:write` | 删除记录 |

> 数据请求由宿主以**当前用户 JWT 身份**转发现有 REST API，插件永不持有凭证。越权调用返回 `{ code: "PERMISSION_DENIED" }`。

### 3.3 最小示例（零构建 IIFE）

无需任何构建工具链，单个 JS 文件即可：

```js
(function () {
  var SDK = window.SmartTableSDK;
  SDK.ready(async function (sdk) {
    var ctx = await sdk.request("ui.getContext");
    var schema = await sdk.request("table.getSchema", { tableId: ctx.tableId });
    var rows = await sdk.request("table.getRecords", { tableId: ctx.tableId, per_page: 20 });
    await sdk.request("ui.notify", { message: "已加载 " + rows.total + " 条", type: "success" });
    // 渲染你自己的 UI 到 document.body
  });
})();
```

完整可运行示例见 `examples/plugins/hello-panel/`（`manifest.json` + `main.js`）：工具栏按钮 + 侧边面板读取当前表记录并批量填充字段。

### 3.4 调试

1. 管理员在"插件管理"页上传 `.stplugin.zip` 安装；
2. 在对应 Base 内启用该插件；
3. 进入数据表，点击工具栏按钮打开面板；
4. 浏览器 DevTools 的 Console 仅能看到宿主注入的 `SmartTableSDK` 与插件自身日志（iframe 隔离，无法访问宿主上下文）。

---

## 4. 后端脚本插件开发

### 4.1 运行沙箱与注入对象

脚本运行在受限子进程中：仅允许白名单模块（`json/re/math/datetime/...`），无网络 / 文件系统 / 系统访问能力；每次数据操作经 **stdio 协议帧** 由宿主按**触发者身份**代理执行并鉴权。

宿主向脚本注入：

- `base`：受限代理对象（方法见下表）
- `context`：`{ plugin_id, base_id, table_id? }`
- `config`：当前 Base 的生效配置（经 `configSchema` 校验）
- `set_result(v)` / `result`：设置最终返回结果

> **业务失败约定**：脚本正常结束时若返回结果（dict）中包含非空 `error` 字段，
> 宿主将该次运行整体标记为 `failed`（错误摘要取该 `error` 值）。需要向宿主
> 报告失败时，推荐 `set_result({"error": "原因"})` 或直接抛出异常（会带 traceback）。

### 4.2 base 代理方法（受 `permissions` 约束）

| 方法 | 所需权限 | 返回 |
| ---- | -------- | ---- |
| `base.list_tables()` | `tables:read` | `[{id, name, description}]` |
| `base.get_fields(table_id)` | `tables:read` | `[{id, name, type}]` |
| `base.list_records(table_id, page, per_page)` | `records:read` | `{items:[{id, values}], total}` |
| `base.get_record(record_id)` | `records:read` | `{id, values}` |
| `base.create_record(table_id, values)` | `records:write` | `{id}` |
| `base.update_record(record_id, values)` | `records:write` | `{id}` |
| `base.delete_record(record_id)` | `records:write` | `{deleted:true}` |
| `base.get_config()` | —（隐含授予） | dict |
| `base.log(message)` | — | 进运行日志 |

### 4.3 最小示例

```python
table_id = config.get("tableId")
field_id = config.get("fieldId")
resp = base.list_records(table_id, page=1, per_page=100)
for rec in resp["items"]:
    values = rec.get("values") or {}
    if not values.get(field_id):
        base.update_record(rec["id"], {field_id: "默认值"})
base.log("批量填充完成")
set_result({"updated": len(resp["items"])})
```

完整示例见 `examples/plugins/batch-clean/`（`manifest.json` + `main.py`）：将指定字段空值批量填充。

### 4.4 安全边界说明

受限 builtins + 模块白名单是"受控执行"而非强沙箱，存在逃逸面。生产环境建议以**低权限 OS 用户**运行子进程。超时默认 30s（可经 `script.timeout` 声明，封顶 300s），连续失败 N 次宿主自动将插件置 `error` 并提示可禁用。

脚本运行可由 Base 管理员在插件管理页"运行"按钮手动触发（以触发者身份），也可在配置中记录 `run_logs`。

---

## 5. 打包与安装

1. 目录结构（包内根即解包根）：

   ```
   your-plugin/
   ├── manifest.json
   └── main.js        # 或 main.py
   # 可选静态资源（UI 插件）
   ```

2. 压缩为 `.stplugin.zip`（注意：包内路径不得包含 `../` 等穿越片段，宿主会校验）：

   ```bash
   cd your-plugin && zip -r ../your-plugin.stplugin.zip .
   ```

3. 管理员进入"插件管理"页 → "上传安装包" → 选择 zip。系统校验：
   - manifest schema 合法（字段、version、type、engines）
   - 入口文件存在（`entry` 指向的文件在包内）
   - semver 与宿主版本 `engines` 兼容
   - zip 路径穿越防护

4. **安装与启用（全部在"插件管理"页完成，Base 页面不提供安装/管理 UI）**：
   - **全局启用/禁用**：插件卡片上的启用/禁用按钮（全局级开关）。
   - **Base 级安装/启停/移除**：卡片上的 **Base 安装状态** 区块（**仅 UI 插件显示**）——先用查询条件区选择目标 Base，再"安装到 Base"并启用。
   - UI 插件只有在 **全局启用 + 该 Base 已安装且启用** 后，才会在该 Base 页面出现（工具栏按钮 / 侧边面板）。
   - **脚本插件无需（也没有）Base 安装步骤**：运行由"触发者对该 Base 的 RBAC（Editor+）+ 全局启用"控制，`installations` 不参与脚本链路。
   - **Base 级配置**（如 UI 插件关联的 base/table）：插件管理页 **配置** 弹窗 → "当前Base配置"页签 → 选择目标 Base 填写。用户在 Base 页面打开插件即按生效配置直接使用，无需任何安装/配置操作。

### 5.1 升级与回滚

- 同 `id` 上传更高 `version` 视为升级：保留配置与 Base 安装关系，旧版本目录保留可回滚。
- 在插件管理页"回滚"可选历史版本切回（指向已保留的旧版本目录）。

---

## 6. 配置（configSchema）

插件可声明 `configSchema`（JSON Schema）。配置分两级作用域：

- **global**：系统级默认配置（系统管理员维护）
- **base**：Base 覆盖配置（管理员在插件管理页的 **配置** 弹窗中按 Base 维护；Base 管理员也可经 REST API 维护）

读写接口：`GET/PUT /api/plugins/<id>/config`（`scope` 参数区分）。运行时 `config.get()` 返回 **base 深合并 global** 后的生效配置。保存时按 `configSchema` 校验，不合法将被拒绝。

---

## 7. REST 管理接口（宿主侧）

插件管理 API 前缀 `/api/plugins`，由插件清单驱动。关键端点：

| 方法 | 路径 | 权限 |
| ---- | ---- | ---- |
| POST | `/upload` | 系统管理员 |
| GET | `/`（`?base_id=`） | 列表（带 Base 级状态） |
| GET | `/<plugin_id>` | 详情（含版本历史） |
| PUT | `/<plugin_id>/status` | 系统管理员（enable/disable/restore） |
| POST | `/<plugin_id>/rollback` | 系统管理员 |
| DELETE | `/<plugin_id>` | 系统管理员（卸载） |
| GET/PUT | `/<plugin_id>/config` | 按 scope |
| POST | `/<plugin_id>/installations` | Base 管理员（安装并启用；仅 UI 插件，脚本插件返回 400） |
| PUT/DELETE | `/<plugin_id>/installations` | Base 管理员（启停/移除；PUT 仅 UI 插件） |
| POST | `/<plugin_id>/run` | 触发者身份（script） |
| GET | `/<plugin_id>/run-logs` | Base 管理员 |
| POST | `/<plugin_id>/sandbox-url` | UI 沙箱签名 URL |
| GET | `/<plugin_id>/versions/<version>/loader.html` | 沙箱 loader（签名鉴权） |

---

## 8. 常见问题

- **插件按钮不可见？** 检查插件全局 `enabled` 且 Base 内 `enabled`，且 `extensionPoints` 声明了 `toolbar-button`，清单 `type` 为 `ui`。
- **RPC 返回 PERMISSION_DENIED？** 调用的方法所需权限未在 `permissions` 声明，或当前用户在目标 Base 无对应 RBAC 权限。
- **脚本运行报权限错误？** 确认 `permissions.records` 为 `write`（写入类方法），且触发者对目标表有写权限。
- **iframe 中拿不到宿主全局变量？** 沙箱 opaque origin 设计如此，所有能力必须经 `SmartTableSDK.request` 走 RPC。
