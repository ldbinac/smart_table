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
| `assets` | object | 包内静态资源声明（可选，详见 §2.3）：`{ styles?: string[], scripts?: string[] }` |
| `endpoints` | array | 自定义后端接口声明（可选，详见 §2.3）：`[{ name, entry, description?, timeout? }]` |
| `script.timeout` | number | 后端脚本超时（秒，可选，封顶 300） |

### 2.1 对象式分级权限

```json
"permissions": {
  "records": "read" | "write",   // 记录读写
  "tables":  "read" | "write",   // 表结构读写
  "storage": true,               // 插件自有 KV（localStorage）
  "network": ["api.example.com"] // 允许经宿主代理外联的第三方域名（见 §3.5）
}
```

未声明的权限点，宿主侧直接拒绝对应调用（deny by default）。对象式结构为未来"限定表/字段"等细粒度权限预留演进空间。

### 2.2 UI 扩展点

```json
"extensionPoints": [
  {
    "type": "toolbar-button",
    "title": "批量填充",
    "icon": "Star",
    "requiresSelection": true,
    "maxSelection": 500
  },
  { "type": "side-panel", "title": "填充面板", "requiresSelection": true }
]
```

支持类型：`toolbar-button`（工具栏按钮）、`side-panel`（右侧 Drawer 中的 iframe）、`base-menu`（Base 级菜单）、`record-detail-block`（记录详情区块）、`home-menu`（首页菜单，全局作用域）、`dashboard-widget`（仪表盘自定义组件）。插件通过清单声明式注册，宿主在启用后自动挂载，无需修改宿主代码。

> **`toolbar-button` 与 `side-panel` 是「入口 ↔ 内容」的配对关系**：
> `toolbar-button` 是表格工具栏上的入口按钮；`side-panel` 是点击该按钮后
> 右侧滑出抽屉（Drawer）里的插件界面——二者一起构成"点按钮 → 开面板"的
> 完整交互，**侧边面板没有独立于按钮的入口**。请成对声明这两个扩展点；
> 仅声明 `side-panel` 而无 `toolbar-button` 的插件，其面板没有任何打开途径。
> 其余扩展点均有各自独立的宿主入口，不受此约束。

### 2.3 静态资源（assets）与自定义后端接口（endpoints）

UI 插件可在清单中声明包内静态资源与自定义后端接口，形成前后端一体的能力：

```json
{
  "assets": {
    "styles": ["styles/main.css", "styles/theme.css"], // 仅 .css，在 entry 前以 <link> 注入
    "scripts": ["vendor/lib.js"]                       // 仅 .js，在 entry 前按序以 <script> 注入
  },
  "endpoints": [
    {
      "name": "translate",                 // SDK backend.call 的 name 标识
      "entry": "endpoints/translate.py",   // 包内 .py 文件
      "description": "调用翻译服务",
      "timeout": 60                         // 该接口超时秒数（1-300，默认 30）
    }
  ]
}
```

- `assets`：包内相对路径，`styles` 在入口前注入样式、`scripts` 在入口前注入脚本；入口 JS 中通过 `SDK.assetUrl("images/logo.png")` 解析图片等运行时资源的签名 URL（详见 §3.2）。
- `endpoints`：包内 Python 文件，由宿主 `/api/plugins/<id>/call/<endpoint>` 经**与脚本插件一致的受限沙箱**执行（无网络/文件系统能力），接收 `request`（见 §4.1）并返回 JSON 结果；`name` 须匹配 `^[a-z][a-z0-9-]*$`。

**可选的勾选依赖声明**（作用于该扩展点入口）：

| 字段 | 类型 | 说明 |
| ---- | ---- | ---- |
| `requiresSelection` | boolean | 为 `true` 时，表格中未勾选记录则宿主禁用入口并提示"请先勾选记录" |
| `maxSelection` | number(1-1000) | 允许处理的最大勾选条数，超出时宿主禁用入口并提示 |

勾选数据经 `ui.getContext()` / `selection.get()` 传给插件，详见 §3.3。

---

## 3. 前端 UI 插件开发

### 3.1 运行沙箱与 SDK

UI 插件在 iframe 中运行，宿主以同源 URL 加载但 `sandbox="allow-scripts"`（不带 `allow-same-origin`），使插件获得 **opaque origin**（`event.origin === "null"`），天然无法访问宿主 Cookie / localStorage / DOM。

宿主提供 loader HTML（含挂载点 `<div id="app">`）并向插件注入两个全局对象：

- `window.SmartTableSDK`：插件 SDK
  - `SmartTableSDK.ready(cb)`：握手完成后回调，回调参数为 `sdk`
  - `sdk.request(method, params)`：发起 RPC 调用，返回 `Promise`
  - `sdk.request("ui.getContext")` → `{ pluginId, baseId, tableId, recordId, selection }`（`selection` 为打开插件瞬间的表格勾选快照，见 §3.3；`recordId` 仅在 `record-detail-block` 扩展点为当前记录 ID）
  - `sdk.request("selection.get")` → 单独获取勾选快照（与 `ui.getContext().selection` 同源）
  - `sdk.assetUrl(path)` → 解析包内静态资源的签名 URL（如 `SDK.assetUrl("images/logo.png")`），插件入口可据此引用图片/额外文件，无需自行拼接令牌
- `window.Vue`：Vue3 全局构建（`vue.global.prod.js`，**含模板编译器**），由宿主从同源 `vendor/` 目录注入

> 推荐用 **Vue 模板语法**编写插件 UI（`Vue.createApp({ template: \`...\` })`），支持 `v-model`、`v-for`、`@click`、`:disabled` 与数据响应式，无需任何构建工具链；也允许用原生 HTML/JS 自行渲染挂载点。
> Vue 运行时为宿主同源托管（不依赖外网/CDN，离线可用），生产环境 CSP 已包含 `'unsafe-eval'`（模板编译器需要）。

### 3.2 可用方法（受 `permissions` 约束）

| 方法 | 所需权限 | 说明 |
| ---- | -------- | ---- |
| `ui.getContext()` | — | 获取当前上下文（含勾选快照 `selection`） |
| `selection.get()` | — | 获取打开插件瞬间的表格勾选快照 |
| `ui.notify({ message, type })` | — | 弹提示 |
| `config.get()` | —（隐含授予） | 读取生效配置（base 合并 global） |
| `storage.get/set/remove({ key, value })` | `storage` | 插件自有 KV |
| `table.getSchema({ tableId })` | `tables:read` | 表结构 + 字段 |
| `table.listTables()` | `tables:read` | 当前 Base 的表列表 |
| `table.getRecords({ tableId, page, per_page, search })` | `records:read` | 分页读取记录 |
| `table.getRecord({ recordId })` | `records:read` | 单条记录 |
| `record.create({ tableId, values })` | `records:write` | 创建记录 |
| `record.update({ recordId, values })` | `records:write` | 更新记录 |
| `record.delete({ recordId })` | `records:write` | 删除记录 |
| `backend.call({ name, payload })` | — | 调用插件自定义后端接口（见 §3.6） |
| `network.fetch({ url, method?, headers?, body? })` | `network`（目标域名须命中 `permissions.network` 白名单） | 经宿主代理访问第三方服务（见 §3.5） |

> 数据请求由宿主以**当前用户 JWT 身份**转发现有 REST API，插件永不持有凭证。越权调用返回 `{ code: "PERMISSION_DENIED" }`。

### 3.3 表格勾选数据（selection）

宿主在**打开插件的瞬间**生成表格勾选快照并注入 RPC 上下文，插件通过 `ui.getContext()` 或 `selection.get()` 读取：

```ts
type SelectionSnapshot = {
  recordIds: string[];     // 勾选记录 ID（超过上限会被截断）
  total: number;           // 勾选总数（截断时为真实总数）
  truncated: boolean;      // 是否因超过上限被截断
  selectAll: boolean;      // 是否命中全选
  scope: "page" | "view";  // 勾选范围：当前页 / 当前视图筛选结果
  at: number;              // 快照时间戳（ms）
};
```

约定与边界：

- **只传 ID**：快照不含记录内容，插件按需用 `table.getRecord({ recordId })` 取详情，避免大批量数据进入沙箱上下文；
- **打开时快照**：勾选变化**不实时推送**，需重新打开插件获取最新勾选（语义简单可预测，避免沙箱与表格状态互相牵连）；
- **上限保护**：单次最多传递 **1000** 个 ID，超出时 `truncated = true`（`total` 仍为真实总数），插件应提示用户缩小范围；
- **全选语义**：表头全选映射为当前视图/当页全部行 ID，`selectAll = true`；
- **完整性**：表格刷新/删除后会清理失效 ID；切换数据表时宿主清空勾选状态，避免跨表残留。

典型处理流程：

```js
SDK.ready(async function (sdk) {
  var ctx = await sdk.request("ui.getContext", {});      // 或 sdk.request("selection.get")
  var ids = (ctx.selection && ctx.selection.recordIds) || [];
  if (!ids.length) {
    await sdk.request("ui.notify", { message: "请先勾选记录", type: "warning" });
    return;
  }
  for (var i = 0; i < ids.length; i++) {
    var rec = await sdk.request("table.getRecord", { recordId: ids[i] });
    await sdk.request("record.update", {
      recordId: ids[i],
      values: { fld_xxx: "新值" },
    });
  }
  await sdk.request("ui.notify", { message: "处理完成", type: "success" });
});
```

**框架/组件库兼容性**：SDK 只依赖 `window.SmartTableSDK`（postMessage + Promise），与插件自身使用的框架无关——Vue / React / 原生 JS 均可按上述方式调用；宿主侧通过可插拔的 `SelectionProvider` 接口适配不同表格实现（当前接入 VTable，原生表格可后续接入同一接口），插件无需感知表格组件。

### 3.4 最小示例（零构建 IIFE）

无需任何构建工具链，单个 JS 文件即可；推荐直接用宿主注入的 Vue 写模板：

```js
(function () {
  "use strict";
  var SDK = window.SmartTableSDK;
  var Vue = window.Vue;

  Vue.createApp({
    // 标准 Vue 模板：v-model / v-for / @click / :disabled 均可正常使用
    template: `
      <div class="my-plugin">
        <select v-model="fieldId">
          <option v-for="f in fields" :key="f.id" :value="f.id">{{ f.name }}</option>
        </select>
        <input v-model="keyword" placeholder="查找值" />
        <button :disabled="loading" @click="search">查找</button>
        <p v-if="!records.length">暂无记录</p>
        <div v-for="r in records" :key="r.id">{{ r.id }}</div>
      </div>
    `,
    data() {
      return { fields: [], records: [], fieldId: "", keyword: "", loading: false };
    },
    methods: {
      async search() {
        this.loading = true;
        try {
          var ctx = await SDK.request("ui.getContext", {});
          var schema = await SDK.request("table.getSchema", { tableId: ctx.tableId });
          this.fields = (schema && schema.fields) || [];
          var res = await SDK.request("table.getRecords", {
            tableId: ctx.tableId,
            search: this.keyword,
            per_page: 20,
          });
          this.records = (res && res.items) || [];
          await SDK.request("ui.notify", { message: "已加载 " + this.records.length + " 条", type: "success" });
        } finally {
          this.loading = false;
        }
      },
    },
    mounted() {
      this.search();
    },
  }).mount("#app");
})();
```

说明：

- 挂载点为 loader 提供的 `<div id="app">`，不要自行清空 `document.body`；
- 样式可随脚本注入 `<style>`（零构建下无 SFC 样式块），或用行内 `style`；
- 若不使用 Vue，也可直接操作 `#app` 自行渲染，SDK 能力与模板写法无关；
- 依赖 `window.Vue` 缺失时应给出明确提示（宿主 loader 会注入 vendor 运行时）。

完整可运行示例见 `examples/plugins/hello-panel/`（v1.2.0，多文件综合示例）：声明全部 6 类扩展点（入口按 `ui.getContext()` 自动分支渲染）、`assets` 多样式/脚本注入（`styles/main.css`+`styles/theme.css`、`vendor/helpers.js`）、`SDK.assetUrl` 引用包内图片（`images/logo.png`）、2 个自定义后端接口（`endpoints/echo.py`/`stats.py`，`backend.call`）、`network.fetch` 经宿主代理请求 GitHub API，以及勾选快照批量填充（`records:write`）与 `storage` 记忆。脚本插件示例见 `examples/plugins/batch-clean/`。

### 3.5 第三方网络代理（network.fetch）

iframe 为 opaque origin，直连第三方会受宿主 CSP 与对方 CORS 双重限制。插件以 `network.fetch` 经**宿主代理**转发请求：

- 目标域名须命中清单 `permissions.network` 白名单（支持精确与子域匹配，如声明 `api.example.com` 可匹配 `a.api.example.com`）；未声明 `network` 权限时该 SDK 方法对插件不可见（deny by default）；
- 服务端做 **SSRF 防护**：仅允许 `http/https`，DNS 解析后拒绝内网 / 环回 / 保留网段；过滤 `Cookie/Authorization` 等受控请求头；带超时、响应体大小上限与每插件速率限制；
- 返回 `{ status, headers, body, body_encoding }`：`body_encoding` 为 `text`（UTF-8 文本）或 `base64`（二进制，如图片）。

```js
SDK.ready(async function (sdk) {
  var res = await sdk.request("network.fetch", {
    url: "https://api.example.com/v1/weather?city=Beijing",
    method: "GET",
  });
  // res.body 为 JSON 文本字符串，按需 JSON.parse
  await sdk.request("ui.notify", { message: res.status === 200 ? "OK" : "失败" });
});
```

### 3.6 插件自定义后端接口（backend.call）

前端插件可调用**插件自己实现的后端逻辑**（包内 `endpoints` 声明的 `.py` 文件），形成前后端一体能力（声明见 §2.3）：

- 宿主以**触发者身份**经**与脚本插件一致的受限沙箱**执行对应 `.py` 文件，注入全局 `request = { endpoint, payload, user_id }`；
- 业务失败后处理同脚本插件（`set_result({"error": "原因"})` 或抛异常，宿主整体标记 `failed`）；默认超时 30s（可经 `endpoints[].timeout` 声明，封顶 300s）；
- 调用无需额外权限点（端点声明本身即授权），但受统一 RBAC 与沙箱边界约束。

```js
// 前端
SDK.ready(async function (sdk) {
  var res = await sdk.request("backend.call", {
    name: "translate",
    payload: { text: "你好", to: "en" },
  });
  // res.result 即 Python 端 set_result 的返回值
});
```

```python
# endpoints/translate.py
text = request["payload"].get("text", "")
# ...调用受限沙箱内的逻辑（无网络能力，可经 base.* 读写表格）...
set_result({"translated": text + " [EN]"})
```

> `backend.call` 与脚本插件的区别：脚本插件以整段 `.py` 作为入口（`POST /run`），而 `endpoints` 允许多个命名入口按需调用，更适合"前端 UI + 多个后端服务"的组合场景。

### 3.7 调试

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
- `request`：**仅 `backend.call` 调用模式**下注入，为 `{ endpoint, payload, user_id }`；普通 `run` 为 `None`（详见 §3.6）

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
   ├── main.js                 # 或 main.py（UI/script 入口）
   ├── vendor/helpers.js       # assets.scripts 声明的脚本（入口前按序注入，UI 插件可选）
   ├── styles/main.css         # assets.styles 声明的样式（入口前按序注入，UI 插件可选）
   ├── images/logo.png         # 运行时经 SDK.assetUrl 引用（UI 插件可选）
   └── endpoints/echo.py       # endpoints 声明的自定义后端接口（可选）
   ```

   > 静态资源与 endpoints 入口文件同样受包内路径穿越校验：声明后这些文件必须存在于包内，否则安装失败。

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
| POST | `/<plugin_id>/call/<endpoint>` | 触发者身份（UI/Script 的自定义后端接口，endpoint 须在 `endpoints` 声明） |
| POST | `/<plugin_id>/proxy` | 触发者身份（代理第三方，`permissions.network` 须声明目标域名；`network.fetch` 为 UI 插件 SDK 能力，脚本插件亦可经 API 触达，鉴权模型一致） |
| POST | `/<plugin_id>/sandbox-url` | UI 沙箱签名 URL |
| GET | `/<plugin_id>/versions/<version>/loader.html` | 沙箱 loader（签名鉴权） |

---

## 8. 常见问题

- **插件按钮不可见？** 检查插件全局 `enabled` 且 Base 内 `enabled`，且 `extensionPoints` 声明了 `toolbar-button`，清单 `type` 为 `ui`。
- **侧边面板（side-panel）在哪里 / 打不开？** side-panel **没有独立入口**：点击 `toolbar-button` 后右侧滑出的抽屉就是它的内容，二者是「入口 ↔ 内容」配对关系，须成对声明。抽屉点不开时，多半是未勾选记录（`requiresSelection: true` 时按钮为禁用态）或当前不在表格视图。
- **base-menu / record-detail-block / home-menu / dashboard-widget 不出现？** 确认清单 `type=ui`、全局启用、且（UI 插件）对应 Base 已安装并启用；首页菜单（home-menu）为全局作用域，无需 Base 安装。
- **backend.call 报 endpoint 未声明？** 确认该接口已在 `endpoints` 中声明且 `name` 匹配；endpoint 实质为受限沙箱执行，没有文件/网络能力。
- **network.fetch 报 PERMISSION_DENIED / SSRF_BLOCKED？** 确认目标域名命中 `permissions.network` 白名单（含子域），且非内网/保留地址；仅支持 http/https。
- **RPC 返回 PERMISSION_DENIED？** 调用的方法所需权限未在 `permissions` 声明，或当前用户在目标 Base 无对应 RBAC 权限。
- **脚本运行报权限错误？** 确认 `permissions.records` 为 `write`（写入类方法），且触发者对目标表有写权限。
- **iframe 中拿不到宿主全局变量？** 沙箱 opaque origin 设计如此，所有能力必须经 `SmartTableSDK.request` 走 RPC。
