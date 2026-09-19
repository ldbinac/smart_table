# SmartTable 插件体系 · 端到端验证指引

> 用途：按本指引逐项验证"插件体系"在当前代码库中的可行性。
> 适用代码：分支 `feat-plugin`（前端 `smart-table/`、后端 `smarttable-backend/`、示例 `examples/plugins/`）。
> 本指引基于实际代码核对（非仅文档）：后端 `app/routes/plugins.py`、`app/services/plugin_service.py`、`plugin_script_service.py`、`plugin_proxy_service.py`、`app/script_runner/plugin_runner.py`；前端 `src/views/PluginManage.vue`、`src/stores/pluginStore.ts`、`src/components/plugins/*`、`src/plugins/{registry,api-surface,rpc}.ts`。
>
> **覆盖能力**：多文件 UI 插件（`assets` 样式/脚本注入 + `SDK.assetUrl` 包内图片）、全部 6 类扩展点（toolbar-button / side-panel / base-menu / record-detail-block / home-menu / dashboard-widget）、插件自定义后端接口（`endpoints` + `backend.call`）、第三方网络代理（`network.fetch` + 白名单/SSRF 防护）、脚本插件沙箱。

---

## 0. 可行性结论（先读，避免卡在已知缺口）

**结论：核心链路已完整可行。** 上传 → 全局启用 → **Base 级安装/启用（插件管理页 UI）** → UI 沙箱握手/RPC、多文件资源加载、自定义后端接口、第三方网络代理、脚本代理运行、配置读写、权限拦截、运行日志、回滚/卸载均已落地且自洽。

**安装使用模式（设计决策，验证时请遵循）：**
- 插件的**安装、全局启停、回滚、卸载、全局配置、脚本运行**由**系统管理员**在**插件管理页**（`/plugins`）完成；
- **Base 级安装/启停/移除、Base 级配置**由**该 Base 的创建者**在插件管理页完成（页面对所有登录用户开放，无需管理员）；前提是插件已由管理员安装并**全局启用**，未启用的插件不允许挂到 Base；
- **Base 页面不提供任何插件安装/管理 UI**，只消费"已在该 Base 安装并启用"的插件（工具栏按钮 / 侧边面板 / Base 菜单 / 记录详情区块 / 仪表盘组件），打开即用；
- **脚本插件无 Base 安装步骤**：运行由"触发者对该 Base 的 RBAC（Editor+）+ 全局启用"控制；
- **home-menu（首页菜单）为全局作用域**：只要全局启用即可出现，无需 Base 安装；
- UI 插件运行所需的 base/table 等配置，在插件管理页"配置"弹窗中按 Base 作用域配置。

**示例插件（验证载体）：**

| 示例 | 类型 | 覆盖能力 |
| --- | --- | --- |
| `examples/plugins/hello-all/`（v1.2.0） | `ui` | **综合示例**：多文件 assets（2 个 CSS + 1 个 JS + 1 张图片）、全部 6 类扩展点、2 个自定义后端接口（echo/stats）、`network.fetch`（GitHub API）、勾选快照批量填充、storage 记忆 |
| `examples/plugins/hello-panel/` | `ui` | **基础示例**：单一扩展点（`toolbar-button` + `side-panel`），零构建单文件，演示勾选快照批量填充 |
| `examples/plugins/hello-base-menu/`、`hello-record-detail-block/`、`hello-home-menu/`、`hello-dashboard-widget/` | `ui` | **各扩展点独立示例**：每个插件仅关注一个扩展点，便于直接复制使用 |
| `examples/plugins/batch-clean/` | `script` | 脚本沙箱：受限 builtins + 模块白名单、stdio 协议帧代理、configSchema 校验 |

**文档与实现的小出入（不影响功能）：**
- 架构设计 §4.2 的 `record.batchUpdate` / `table.addField` / `base.add_field()` 等属"预留"，当前未实现（示例未涉及）；
- 架构设计 §5.3 列的独立 `GET /api/plugins/<id>/versions` 未实现；版本历史随 `GET /<id>` 返回。

> 登录接口需要验证码（`/api/auth/login` 必填 `captcha`），且 `IS_DEMO_ENVIRONMENT=true` 时不签发令牌。
> 因此后端 API 验证统一采用"**前端 UI 登录拿 Token → curl 调用后端**"路线。

---

## 1. 环境准备

### 1.1 启动后端（Flask，端口 5000）
```powershell
cd smarttable-backend
python run.py create-admin admin@example.com YourPass123 管理员   # 仅需一次
# 确认 .env 中 IS_DEMO_ENVIRONMENT 未设为 true（默认即 false）
python run.py
```
- 健康检查：`http://localhost:5000/api/health`
- API 文档/Swagger：`http://localhost:5000/api/`（标签 `Plugins`）

### 1.2 启动前端（Vite，端口 3000，`/api` 反代到 5000）
```powershell
cd smart-table
pnpm install   # 若未安装依赖
pnpm dev
```
- 访问：`http://localhost:3000`

### 1.3 准备测试数据（在 UI 完成）
1. 用刚建的 admin 账号登录 `http://localhost:3000`（UI 会处理验证码）。
2. 新建一个 Base，新建一张表，加一个**单行文本字段**（记下字段用途）。
3. 在该表填 **3~5 条记录**（至少让目标字段有空值，供脚本/插件填充演示）。
4. 从浏览器地址栏复制 `baseId`（URL 形如 `/base/<baseId>/...`）；字段 `fieldId` 稍后从表结构接口或 DevTools 获取。

### 1.4 获取 Token（供 curl 使用）
- 登录后，打开浏览器 DevTools（F12）→ **Network** → 任意已发出的请求 → 复制请求头 `Authorization: Bearer <TOKEN>` 中的 `<TOKEN>`。
- 后续命令用 `curl.exe`（**PowerShell 中 `curl` 是 `Invoke-WebRequest` 别名，必须用 `curl.exe`**），并把 `<TOKEN>`、`<BASE_ID>`、`<FIELD_ID>`、`<TABLE_ID>` 替换为实际值。
- 注意角色：§2.7/2.8 的 `call`/`proxy` 要求触发者对目标 Base 有 **Editor+** 权限——若 admin 不在该 Base 成员中，请使用 Base Owner/Admin 账号的 Token（下称 `<BASE_TOKEN>`）。

> 登录有频率限制（5 次/15 分钟锁定），不要反复重试。

---

## 2. 后端 API 验证清单（curl，逐项勾选）

> 所有请求加 `-H "Authorization: Bearer <TOKEN>"`。后端地址用 `http://localhost:5000`。
> 不想用命令行？第 **2A** 节提供与本节一一对应的纯界面操作验证，二者可任选或互相印证。

### 2.0 打包两个示例插件（包内根即解包根，无路径穿越）

hello-panel 已是多文件包（manifest + 入口 + vendor 脚本 + 2 个样式 + 图片 + 2 个 endpoint），**全部文件都要打进 zip 且保留目录结构**：

```powershell
cd examples\plugins\hello-panel
python -c "import zipfile as z; f = z.ZipFile('../../hello-panel.stplugin.zip', 'w', z.ZIP_DEFLATED); [f.write(p, p) for p in ['manifest.json', 'main.js', 'vendor/helpers.js', 'styles/main.css', 'styles/theme.css', 'images/logo.png', 'endpoints/echo.py', 'endpoints/stats.py']]; f.close()"
cd ..\..\batch-clean
python -m zipfile -c ..\..\batch-clean.stplugin.zip manifest.json main.py
```

> ⚠️ 不要用 `python -m zipfile -c` 打多文件包：它会**把 arcname 压平成 basename**（`vendor/helpers.js` → `helpers.js`），导致安装校验因"声明的 assets/endpoints 文件不存在"而失败。batch-clean 仅根级两个文件，不受影响。
> 也可用 `Compress-Archive -Path manifest.json, main.js, vendor, styles, images, endpoints -DestinationPath ..\..\hello-panel.stplugin.zip -Force`（Windows PowerShell 会以 `\` 作条目分隔符，宿主解包已做归一化，功能等价）。

- [ ] **包完整性**：`python -c "import zipfile; print(zipfile.ZipFile('../../hello-panel.stplugin.zip').namelist())"` 应列出上述 8 个文件**且带目录前缀**（漏打图片/样式或路径被压平都会导致安装校验失败：assets/endpoints 声明的文件必须存在于包内）。

### 2.1 上传安装包（admin）
```powershell
curl.exe -X POST http://localhost:5000/api/plugins/upload `
  -H "Authorization: Bearer <TOKEN>" `
  -F "package=@examples/hello-panel.stplugin.zip"
curl.exe -X POST http://localhost:5000/api/plugins/upload `
  -H "Authorization: Bearer <TOKEN>" `
  -F "package=@examples/batch-clean.stplugin.zip"
```
- [ ] **通过**：两次均返回 `plugins` 记录，`id` 分别为 `com.smarttable.hello-panel`、`com.smarttable.batch-clean`，`status=installed`；hello-panel 的 `manifest` 应含 `assets`/`endpoints`/6 个 `extensionPoints`。
- [ ] **声明文件缺失校验**：重打包一个删除了 `vendor/helpers.js`（但 manifest 仍声明）的 hello-panel zip 上传 → 应 `400` 拒绝（安装校验：声明的 assets/scripts 文件必须存在）。
- [ ] **异常校验**：上传一个 `manifest.json` 缺 `id`/非法 `version`/未知 `type` 的 zip，应被 `400` 拒绝（验证 `_validate_manifest`）。
- [ ] **路径穿越**：zip 内含 `../evil.txt`，应被 `_safe_extract` 拒绝（解压失败/400）。

### 2.2 列表 / 详情
```powershell
curl.exe http://localhost:5000/api/plugins `
  -H "Authorization: Bearer <TOKEN>"
curl.exe http://localhost:5000/api/plugins/com.smarttable.hello-panel `
  -H "Authorization: Bearer <TOKEN>"
```
- [ ] **通过**：列表含两个插件；详情含 `manifest`、`versions`（版本历史随详情返回）、`current_version=1.2.0`。

### 2.3 全局启用（admin）
```powershell
curl.exe -X PUT http://localhost:5000/api/plugins/com.smarttable.hello-panel/status `
  -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" `
  -d "{\"status\":\"enabled\"}"
curl.exe -X PUT http://localhost:5000/api/plugins/com.smarttable.batch-clean/status `
  -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" `
  -d "{\"status\":\"enabled\"}"
```
- [ ] **通过**：返回 `status=enabled`。

### 2.4 UI 插件 Base 级安装（§3 前置；脚本插件跳过本步）
```powershell
curl.exe -X POST http://localhost:5000/api/plugins/com.smarttable.hello-panel/installations `
  -H "Authorization: Bearer <BASE_TOKEN>" -H "Content-Type: application/json" `
  -d "{\"base_id\":\"<BASE_ID>\"}"
curl.exe -X PUT http://localhost:5000/api/plugins/com.smarttable.hello-panel/installations `
  -H "Authorization: Bearer <BASE_TOKEN>" -H "Content-Type: application/json" `
  -d "{\"base_id\":\"<BASE_ID>\",\"enabled\":true}"
```
- [ ] **通过**：安装返回 `enabled=true`。
- [ ] **脚本插件拒装**：对 `batch-clean` 调同一 `installations` → `400`（`PLUGIN_TYPE_NOT_INSTALLABLE`，脚本插件运行由 RBAC + 全局启停控制）。

### 2.5 配置写入与读取（configSchema 校验 + global/base 合并）
```powershell
# batch-clean 全局配置（admin）
curl.exe -X PUT http://localhost:5000/api/plugins/com.smarttable.batch-clean/config `
  -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" `
  -d "{\"scope\":\"global\",\"config\":{\"fillValue\":\"(空)\"}}"

# batch-clean 某 Base 覆盖配置（Base 管理员）
curl.exe -X PUT http://localhost:5000/api/plugins/com.smarttable.batch-clean/config `
  -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" `
  -d "{\"scope\":\"base\",\"base_id\":\"<BASE_ID>\",\"config\":{\"tableId\":\"<TABLE_ID>\",\"fieldId\":\"<FIELD_ID>\"}}"

# 读取生效配置（应为 base 深合并 global）
curl.exe "http://localhost:5000/api/plugins/com.smarttable.batch-clean/config?base_id=<BASE_ID>" `
  -H "Authorization: Bearer <TOKEN>"
```
- [ ] **通过**：最后一步返回的配置同时含 `tableId/fieldId`（base）与 `fillValue`（global 合并）。
- [ ] **校验失败**：`config` 缺 `required` 的 `tableId/fieldId`，应 `400`（验证 `PluginValidationError`）。

### 2.6 脚本运行（以触发者身份代理）
```powershell
curl.exe -X POST http://localhost:5000/api/plugins/com.smarttable.batch-clean/run `
  -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" `
  -d "{\"base_id\":\"<BASE_ID>\"}"
```
- [ ] **通过**：返回 `status=success`，`result.updated` > 0（目标字段空值被填充为 `fillValue`）。
- [ ] **副作用**：回到 UI 该表，确认原空值字段已写入 `(空)`。

### 2.7 运行日志
```powershell
curl.exe "http://localhost:5000/api/plugins/com.smarttable.batch-clean/run-logs?base_id=<BASE_ID>" `
  -H "Authorization: Bearer <TOKEN>"
```
- [ ] **通过**：含一条 `success` 记录，`output` 含 `Batch clean 完成`。

### 2.8 插件自定义后端接口（endpoints → 受限沙箱执行）
> 前置：hello-panel 已全局启用且已安装到目标 Base（§2.4）；Token 用 `<BASE_TOKEN>`（Editor+）。
```powershell
# echo：回显 payload + 触发者身份 + 表数量（endpoints/echo.py）
curl.exe -X POST http://localhost:5000/api/plugins/com.smarttable.hello-panel/call/echo `
  -H "Authorization: Bearer <BASE_TOKEN>" -H "Content-Type: application/json" `
  -d "{\"base_id\":\"<BASE_ID>\",\"payload\":{\"hello\":\"world\"}}"

# stats：按表/字段统计空值分布（endpoints/stats.py，服务端聚合 base.list_records）
curl.exe -X POST http://localhost:5000/api/plugins/com.smarttable.hello-panel/call/stats `
  -H "Authorization: Bearer <BASE_TOKEN>" -H "Content-Type: application/json" `
  -d "{\"base_id\":\"<BASE_ID>\",\"payload\":{\"tableId\":\"<TABLE_ID>\",\"fieldId\":\"<FIELD_ID>\"}}"
```
- [ ] **通过（echo）**：返回 `result` 含 `echo.hello=world`、`user_id`（触发者 ID）、`base_id`、`table_count`。
- [ ] **通过（stats）**：返回 `result` 含 `total/sampled/filled/empty`，与该表该字段实际空值分布一致；运行日志中该次调用 kind 标记为 endpoint 调用（`result` 包裹 `{endpoint, data}`）。
- [ ] **未声明 endpoint**：`POST /call/not-exist` → `404`（`plugin_endpoint_not_found`）。
- [ ] **RBAC**：用 Base **Viewer** 账号 Token 调用 → `403`（`no_permission_run_plugin`）。
- [ ] **未安装到 Base**：对未安装 hello-panel 的其他 Base 调用 → `403`（`plugin_not_enabled_in_base`）。

### 2.9 第三方网络代理（/proxy → 白名单 + SSRF 防护）
> 前置同 §2.8；hello-panel 声明了 `permissions.network: ["api.github.com"]`。
```powershell
# 白名单内：经宿主代理请求 GitHub 公共 API
curl.exe -X POST http://localhost:5000/api/plugins/com.smarttable.hello-panel/proxy `
  -H "Authorization: Bearer <BASE_TOKEN>" -H "Content-Type: application/json" `
  -d "{\"base_id\":\"<BASE_ID>\",\"url\":\"https://api.github.com/repos/ldbinac/smart_table\",\"method\":\"GET\"}"

# 白名单外：域名未声明
curl.exe -X POST http://localhost:5000/api/plugins/com.smarttable.hello-panel/proxy `
  -H "Authorization: Bearer <BASE_TOKEN>" -H "Content-Type: application/json" `
  -d "{\"base_id\":\"<BASE_ID>\",\"url\":\"https://example.com/api\"}"

# SSRF：目标解析到环回/内网地址（即使域名命中白名单也会被拒）
curl.exe -X POST http://localhost:5000/api/plugins/com.smarttable.hello-panel/proxy `
  -H "Authorization: Bearer <BASE_TOKEN>" -H "Content-Type: application/json" `
  -d "{\"base_id\":\"<BASE_ID>\",\"url\":\"http://127.0.0.1:5000/api/health\"}"
```
- [ ] **通过（放行）**：返回 `{ status: 200, headers, body, body_encoding }`，`body` 为 GitHub JSON 文本（`body_encoding=text`）。
- [ ] **白名单外**：`403`（`PERMISSION_DENIED: host not in network whitelist`）。
- [ ] **SSRF 拦截**：`400`（`SSRF_BLOCKED: target resolves to restricted address`）。
- [ ] **未声明 network 的插件**：对 `batch-clean` 调 `/proxy` → `403`（`plugin_network_not_declared`）。
- [ ] **限流（可选）**：60 秒内连续调用超过 60 次 → `429`（`RATE_LIMITED`）。

### 2.10 回滚 / 卸载（admin，先跳过，留到第 6 节做）
- 端点：`POST /api/plugins/<id>/rollback`（`-d "{\"version\":\"1.0.0\"}"`）、`DELETE /api/plugins/<id>`。

---

## 2A. 界面操作验证（插件管理页 `/plugins`，纯手工点击）

> 适用角色：**系统管理员**（§2A.2~2A.4、2A.6~2A.8）与 **Base 创建者**（§2A.5）。以下步骤基于已实现的 `PluginManage.vue` 管理界面，与第 2 节 curl 一一对应，可完全不依赖命令行完成插件生命周期主链路验证。
> 前置：已用 admin 登录 `http://localhost:3000`，并完成第 2.0 节打包（`examples/hello-panel.stplugin.zip`、`examples/batch-clean.stplugin.zip`）。

### 2A.1 进入插件管理页
1. [ ] 浏览器访问 `http://localhost:3000/plugins`（或从侧边栏进入"插件管理"）。
2. [ ] **非管理员可见性**：用普通账号访问该路由应**可以进入**（不再被 `adminGuard` 拦截），但看不到"上传安装包"按钮，Base 下拉只列出自己创建的 Base。
3. [ ] **旧入口兼容**：访问 `/admin/plugins` 应重定向到 `/plugins`。

### 2A.2 上传安装包（对应 §2.1）
1. [ ] 点右上角 **上传安装包** → 弹窗中拖入或选择 `hello-panel.stplugin.zip` → 点上传。
   - 成功：绿色提示"上传成功"，列表出现 `com.smarttable.hello-panel` 卡片，状态 `installed`。
2. [ ] 同样方式上传 `batch-clean.stplugin.zip`，列表出现第二张卡片。
3. [ ] **卡片声明摘要**：hello-panel 卡片可见类型标签（UI）、权限摘要（含 `network: api.github.com`）；batch-clean 显示脚本类型。
4. [ ] **失败提示可读性**：临时把某插件 manifest 的 `engines.smarttable` 改为 `">=2.0.0"` 打包上传 → 应弹出"上传失败: 当前宿主版本 1.6.6 不满足插件声明的引擎兼容范围 …"这类**中文原因说明**（而非裸错误码）；验证完恢复。
5. [ ] **弹窗状态清空**：上传成功/失败后关闭弹窗，再次打开 → 不应残留上次的安装包文件（`@closed` 清空逻辑）。
6. [ ] **异常包**：上传缺 `manifest.json` 的 zip → 弹"上传失败: …"（400 校验拒绝）。

### 2A.3 列表卡片信息（对应 §2.2）
- [ ] 每张卡片展示：插件名、`pluginId`、版本（hello-panel `1.2.0`）、类型标签（UI/脚本）、状态标签（installed/enabled/disabled）。
- [ ] 顶部搜索框输入关键词可过滤卡片。

### 2A.4 全局启用/禁用（对应 §2.3）
1. [ ] 在 `hello-panel` 卡片点 **启用** → 状态变为 `enabled`，出现成功提示。
2. [ ] 再切回 **禁用** → 应先弹确认框，确认后状态变为 `disabled`。
3. [ ] 最终保持两个插件均为 **enabled**（后续步骤依赖）。

### 2A.5 Base 级安装 / 启停 / 移除（对应 §2.4；**仅 UI 插件显示**）

> 设计决策：Base 级安装由**该 Base 的创建者**在**插件管理页**完成，Base 页面不提供安装 UI；管理员无需（也无法）替他人创建的 Base 代装。
> **适用范围**：`installations` 只用于 UI 插件的 Base 分发挂载；**脚本插件不显示该区块**（运行由 RBAC + 全局启停控制，可直接进入 §2A.7 运行）。
> 卡片上的"Base 安装状态"区块展示查询条件区当前所选 Base 下的安装/生效情况；切换 Base 下拉会自动刷新。
> 若所选 Base 不是当前用户创建的，该区块只显示"仅该多维表格的创建者可以安装/管理此插件"，不出现操作按钮。

1. [ ] `hello-panel`（UI 插件）卡片出现 **Base 安装状态** 区块（标题含当前 Base 名），初始显示 `未安装`；`batch-clean`（脚本插件）卡片**不出现**该区块。
2. [ ] 点 **安装到 Base** → 状态变为 `已启用`（成功提示），卡片出现 **启用/停用** 与 **从 Base 移除** 按钮。
3. [ ] 点 **停用** → 状态变为 `已停用`；再点 **启用** → 恢复 `已启用`。
4. [ ] **联动校验**：切换查询条件区 Base 下拉 → 卡片安装状态随所选 Base 变化（A Base 已安装、B Base 未安装）。
5. [ ] **从 Base 移除** → 确认弹窗 → 状态回到 `未安装`；重新安装恢复。
6. [ ] **全局停用联动**：全局状态为停用时，已安装的插件在 Base 内不生效，卡片出现提示"全局状态为停用，Base 内不会生效"。
7. [ ] `GET /api/plugins?base_id=<BASE_ID>` 响应中各插件应带 `baseInstalled/baseInstallEnabled/baseEnabled` 字段（卡片数据来源）。
8. [ ] **API 一致性**：对脚本插件（batch-clean）经 curl 调 `POST /api/plugins/com.smarttable.batch-clean/installations` → 应 400 拒绝（错误码 `PLUGIN_TYPE_NOT_INSTALLABLE`）。

### 2A.6 配置（对应 §2.5）
1. [ ] `batch-clean` 卡片点 **配置** → 弹窗中选择作用域：
   - `global`：粘贴 `{"fillValue":"(空)"}` → 保存成功提示。
   - `base`：粘贴 `{"tableId":"<TABLE_ID>","fieldId":"<FIELD_ID>"}` → 保存成功提示。
2. [ ] **校验失败**：base 作用域粘贴缺必填项的 `{}` → 应提示保存失败（configSchema 校验 400）。
3. [ ] **页签内容区分**：切换"全局配置"/"当前Base配置"页签 → 文本框应分别显示**对应作用域存储的配置**（base 页签需先选择目标 Base，未选时为空 `{}`）。
4. [ ] 重新打开配置弹窗 → 各页签回显内容与各自保存的一致。

### 2A.7 脚本运行与运行日志（对应 §2.6 / §2.7）
1. [ ] `batch-clean` 卡片点 **运行** → 弹出"运行脚本插件"对话框，**在对话框中显式选择本次运行的目标 Base**（默认预填查询条件区当前 Base，但以对话框选择为准）。
2. [ ] 点对话框中的 **运行** → 按钮进入 loading 态；完成后弹出**"插件运行结果"结果弹窗**，分两段展示：①执行信息（运行状态 tag、耗时、当前 Base）；②插件执行结果（总体结果 tag + 只读多行文本框，含脚本 `result` JSON、运行输出、错误信息）。
3. [ ] **Base 不匹配场景**：在 A Base 上保存 base 级配置，却选择在 B Base 上运行 → 应弹红色"脚本运行失败: 缺少 tableId/fieldId 配置… · 当前 Base: B"。
4. [ ] 点 **运行日志**（使用查询条件区的 Base）→ 弹窗表格正常渲染：状态、耗时、时间、**执行结果列**、错误摘要，每行带 **详情** 按钮。
5. [ ] 点某行的 **详情** → 打开"日志详情"弹窗：执行信息 + 插件执行结果 + 运行输出 + 错误信息/异常堆栈（仅失败时显示）。
6. [ ] **业务失败区分**：选一个未配置 `tableId/fieldId` 的 Base 运行 → 运行结果弹窗总体结果应为红色 **失败**，错误摘要为 `missing tableId/fieldId`。

### 2A.8 升级 / 回滚 / 卸载（对应 §6，可先跳过）
1. [ ] 按第 6 节打好 `1.2.1` 版本包后，重复 2A.2 上传 → 卡片版本变为 `1.2.1`（升级成功提示），配置与安装关系保留。
2. [ ] 点 **回滚** → 弹窗版本下拉应含历史版本；选低版本确认 → 版本回退，卡片版本号随之变化。
3. [ ] 点 **卸载** → 确认弹窗 → 卡片从列表消失（可按需重传恢复）。

---

## 3. UI 插件端到端（前端点击验证）

> 关键前提：UI 插件要出现在 Base 内的各扩展点，必须**全局启用 + 该 Base 已安装并启用**（§2A.4 + §2A.5）。
> **唯一例外**：home-menu（首页菜单）为全局作用域，只要全局启用即可出现（无需 Base 安装）——这本身就是一个验证点（见 §3.7）。
> hello-panel 声明了全部 6 类扩展点，入口按 `ui.getContext()` 自动分支渲染，以下逐项验证。

### 3.1 多文件 assets 验证（styles / scripts / 图片）
1. [ ] **样式注入与覆盖顺序**：进入第 1.3 节那张表，工具栏出现 **"Hello"** 按钮（`toolbar-button`）；面板内主按钮应为**主题蓝底白字**（`styles/theme.css` 在 `styles/main.css` 之后注入并覆盖生效）。
2. [ ] **脚本注入（入口前执行）**：在面板 iframe 内 DevTools Console 执行 `window.HPHelpers` → 应为对象（含 `esc/truncate/formatJson/fieldValue`），证明 `assets.scripts` 声明的 `vendor/helpers.js` 已在 `main.js` 之前加载。
3. [ ] **包内图片（SDK.assetUrl）**：面板头部显示圆角 logo 图片；DevTools Network 中该请求 URL 形如 `files/images/logo.png?fst=<签名>`（文件令牌 `fst`，TTL 2h）。
4. [ ] **loader CSP**：loader.html 响应头 `Content-Security-Policy` 的 `style-src`/`script-src` 放行宿主同源（否则 CSS/JS/图片全挂）；`connect-src` 包含白名单域 `api.github.com`（按 manifest.network 动态生成）。

### 3.2 工具栏按钮 + 侧边面板（toolbar-button / side-panel）

> **入口说明（避免混淆）**：`side-panel` 没有独立入口——它就是点击 `toolbar-button`（"Hello"按钮）后右侧滑出的抽屉**内容**，二者是「入口 ↔ 内容」的配对关系，一起验证即可，不存在"另一处"的侧边面板。抽屉打开但看不到内容时，先检查是否已勾选记录（`requiresSelection: true` 时按钮为**禁用态**，点击无反应）。

1. [ ] **勾选依赖（requiresSelection）**：未勾选任何记录时，"Hello"按钮为**禁用**态，悬浮提示"请先在表格中勾选记录"；勾选 2~3 条后恢复可用（hello-panel 声明 `maxSelection: 500`，可勾选 >500 条验证入口被禁并提示）。
2. [ ] 点击按钮 → 右侧 Drawer 打开 **Hello Panel**，显示标题、logo 与"已勾选 N 条记录"。
3. [ ] 选择字段、输入填充值、点"批量填充"：目标字段被写入；弹出 `填充完成：成功 N 条` 提示（`record.update` 走通，**只作用于勾选记录**）。
4. [ ] **打开时快照语义**：勾选后不重开插件、直接在表格改勾选 → 面板内容不变；表头全选 → 显示"（全选）"。
5. [ ] 刷新页面再次打开面板，上次选中的字段被记住（`storage.get/set`）。

### 3.3 插件自定义后端接口（backend.call → endpoints/*.py）
1. [ ] 在面板内点 **echo** 按钮 → 下方代码块显示 JSON：含 `echo` 回显、`user_id`（当前用户）、`base_id`、`table_count`。
2. [ ] 点 **stats** 按钮 → 显示 `total/sampled/filled/empty`，与该表该字段实际空值分布一致。
3. [ ] **触发者身份**：`user_id` 应为当前登录用户 ID（宿主按 JWT 代理，插件拿不到凭证）。
4. [ ] 失败路径对照：用 curl 对 `batch-clean`（未声明 endpoints 的插件）调 `/call/echo` → `404`（见 §2.8）。

### 3.4 第三方网络代理（network.fetch → 宿主 /proxy）
1. [ ] 在面板内点 **请求 GitHub API** 按钮 → 代码块显示 `{status:200, repo:"ldbinac/smart_table", stars, description}`（需外网；离线环境应显示友好错误而非白屏）。
2. [ ] 返回含 `body_encoding` 字段（文本为 `text`；二进制如图片为 `base64`）。
3. [ ] **白名单外域被拒**：把示例中 URL 临时改为 `https://example.com`（或用 curl，见 §2.9）→ `PERMISSION_DENIED`。
4. [ ] **deny by default**：把 hello-panel 的 `permissions.network` 删除后重传 → `network.fetch` 方法对插件**不可见**（调用报方法不存在，而非 403）。

### 3.5 Base 菜单（base-menu）
1. [ ] 进入该 Base 页面，工具栏区出现 **"Hello 菜单"** 下拉入口（`base-menu` 扩展点，无需勾选记录）。
2. [ ] 点击 → 对话框打开插件沙箱：该入口不携带勾选数据，面板显示"未勾选记录（该入口不携带勾选数据）"提示，且 **echo/stats/GitHub 演示按钮仍可用**（Base 作用域能力完整）。

### 3.6 记录详情区块（record-detail-block）
1. [ ] 打开任意一条记录的详情抽屉 → 底部出现 **"Hello 记录卡片"** 区块（iframe 沙箱）。
2. [ ] 区块内显示当前 `recordId` 与该记录完整 values JSON（`table.getRecord` 走通）。
3. [ ] 区块内 echo 按钮：`payload.recordId` 为当前记录 ID。
4. [ ] **切换记录**：详情抽屉切换到另一条记录 → 区块沙箱**重建**并显示新记录（宿主按 recordId 变化重建 iframe）。

### 3.7 首页菜单（home-menu，全局作用域）
1. [ ] 回到首页（Home）→ 右上操作区出现 **"Hello 工具箱"** 入口；**即使该插件未安装到任何 Base 也会出现**（只看全局启用状态）。
2. [ ] 点击 → 大尺寸对话框（宽 60%、内容高 60vh）打开插件：顶部标签显示 `home-menu · 全局`，显示 logo 与配置的问候语。
3. [ ] 点 **storage 计数**按钮 → 计数递增且刷新后保留（插件自有 KV）。
4. [ ] **能力降级**：该分支下 `backend.call / network.fetch` 按钮为**禁用态**，悬浮提示"需要 Base 上下文"（宿主在无 baseId 时会拒绝这两类调用，插件应优雅降级）。

### 3.8 仪表盘自定义组件（dashboard-widget）
1. [ ] 进入该 Base 的仪表盘 → 添加组件下拉出现 **"插件组件"** 分类（动态来自 registry），含 **"Hello 卡片"**（`dashboard-widget` 扩展点）。
2. [ ] 添加后网格内渲染插件 iframe（非 echarts 分支）；组件配置中保存 `plugin:<pluginId>` 类型与 pluginId。
3. [ ] 保存仪表盘并刷新页面 → 插件组件正常恢复渲染（WidgetConfig 持久化生效）。

### 3.9 沙箱隔离与签名 URL（安全）
1. [ ] **opaque origin**：在面板 iframe 内 DevTools Console 执行 `document.cookie` / `window.parent` → 拿不到宿主 Cookie，且 `event.origin` 为 `"null"`（`sandbox="allow-scripts"` 生效）。
2. [ ] **握手/鉴权**：Network 中 loader.html 请求带 `?st=<签名>&fst=<文件令牌>`；直接打开无签名 URL → `forbidden`（`verify_sandbox_token`）。
3. [ ] **文件令牌隔离**：用 A 插件的 `fst` 请求 B 插件的 `files/<path>` → `forbidden`（令牌绑定 plugin_id+version）。

---

## 4. 脚本插件"沙箱与安全边界"验证

1. [ ] **白名单外模块被拒**：临时把 `examples/plugins/batch-clean/main.py` 顶部加 `import os`（或 `import socket`），重新打包上传并运行 → 应运行失败且日志报模块不在白名单（`safe_import` 拒绝）。
2. [ ] **危险内建被禁**：脚本里调用 `open('/etc/passwd')` 或 `eval(...)` → 应被 `DANGEROUS_BUILTINS` 移除而报 `NameError`。
3. [ ] **超时控制**：把 `manifest.json` 的 `script.timeout` 设为极小值（如 `2`），脚本里写极长死循环，运行应返回 `timeout`（deadline 控制）。
4. [ ] **权限越权被拒**：将 `batch-clean` 的 `permissions.records` 改为 `read` 后重传运行 → `base.update_record` 应被双层权限校验拒绝（宿主侧 `deny by default` + RBAC）。
5. [ ] **endpoints 同边界**：临时在 `endpoints/echo.py` 顶部加 `import os` 重传 → `backend.call("echo")` 应失败（endpoints 与脚本插件共用同一受限沙箱与模块白名单）。

> 上述"临时修改"请在**副本**上做，验证后恢复，避免污染示例。

---

## 5. 权限边界（UI 侧）

1. [ ] 将 `hello-panel` 的 `permissions` 去掉 `records: write` 后重传并重新走 §3.2 → 点"批量填充"时 `record.update` 应返回 `PERMISSION_DENIED`（宿主侧拒绝对应调用）。
2. [ ] 未声明 `storage` 时，`storage.set` 应被拒（示例里已 try/catch 容错，可从 Network 响应确认 `PERMISSION_DENIED`）。
3. [ ] 未声明 `network` 时，`network.fetch` 方法对插件不可见（§3.4 第 4 项）。
4. [ ] 未声明 `endpoints` 时，`backend.call` 任何 name 均返回 404（§2.8）。

---

## 6. 升级 / 回滚验证（复用 2.1 上传链路）

1. [ ] 修改 `hello-panel/manifest.json` 的 `version` 为 `1.2.1`（可同时改 `name` 或加一行日志），重新打包上传（**记得带全部文件且保留目录结构**，打包命令见 §2.0，仅把输出文件名改为 `hello-panel-v121.stplugin.zip`）：
   ```powershell
   cd examples\plugins\hello-panel
   python -c "import zipfile as z; f = z.ZipFile('../../hello-panel-v121.stplugin.zip', 'w', z.ZIP_DEFLATED); [f.write(p, p) for p in ['manifest.json', 'main.js', 'vendor/helpers.js', 'styles/main.css', 'styles/theme.css', 'images/logo.png', 'endpoints/echo.py', 'endpoints/stats.py']]; f.close()"
   curl.exe -X POST http://localhost:5000/api/plugins/upload -H "Authorization: Bearer <TOKEN>" -F "package=@examples/hello-panel-v121.stplugin.zip"
   ```
2. [ ] 详情接口 `versions` 现在含 `1.2.0` 与 `1.2.1`，配置与 Base 安装关系保留。
3. [ ] 回滚到 `1.2.0`：
   ```powershell
   curl.exe -X POST http://localhost:5000/api/plugins/com.smarttable.hello-panel/rollback `
     -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" `
     -d "{\"version\":\"1.2.0\"}"
   ```
4. [ ] 回到 UI 该表，插件行为回到 `1.2.0` 版本（回滚生效）。
5. [ ] 卸载：`DELETE /api/plugins/com.smarttable.hello-panel`（admin），列表不再出现；可按需重传恢复。

---

## 7. 扩展点 × 验证方式对照表

| 扩展点 | 宿主挂载位置 | 作用域 | 验证节 |
| --- | --- | --- | --- |
| `toolbar-button` | 表格工具栏按钮 | Base（需安装启用） | §3.2 |
| `side-panel` | 右侧 Drawer iframe | Base（需安装启用） | §3.2 |
| `base-menu` | Base 工具栏下拉菜单 → 对话框 | Base（需安装启用） | §3.5 |
| `record-detail-block` | 记录详情抽屉底部区块 | Base（需安装启用） | §3.6 |
| `home-menu` | 首页操作区 → 对话框 | **全局**（仅全局启用） | §3.7 |
| `dashboard-widget` | 仪表盘网格组件 | Base（需安装启用） | §3.8 |

其余此前"暂无法验证"项的现状：
- ~~`base-menu` / `record-detail-block` 无宿主组件~~ → **已挂载**，见 §3.5 / §3.6；
- 独立版本历史接口 `GET /versions` 未实现 → 版本历史已并入 `GET /<id>`，直接验证后者即可。

---

## 8. 验证结果记录模板

```
后端 API：
  [ ] 打包完整性（8 文件）    [ ] 上传/声明文件缺失/异常校验/路径穿越
  [ ] 列表/详情              [ ] 全局启用        [ ] Base 安装（脚本拒装）
  [ ] 配置写入+合并+校验失败  [ ] 脚本运行+副作用  [ ] 运行日志
  [ ] call/echo+stats+404+RBAC+未安装      [ ] proxy 放行/白名单外/SSRF/未声明/限流
界面操作（§2A）：
  [ ] 管理页进入/权限守卫     [ ] 弹窗上传×2      [ ] 卡片声明摘要
  [ ] 失败提示可读 / 弹窗无残留 / 异常包
  [ ] 卡片信息/过滤          [ ] 全局启用/禁用    [ ] Base 安装/启停/移除  [ ] 联动
  [ ] 配置保存+校验失败       [ ] 运行+结果弹窗    [ ] 日志弹窗+详情  [ ] 业务失败区分
UI 插件：
  [ ] 主题样式覆盖（assets.styles 顺序）       [ ] HPHelpers 注入（assets.scripts）
  [ ] logo 图片（assetUrl + fst）             [ ] loader CSP
  [ ] 勾选依赖/快照语义/批量填充/storage 记忆
  [ ] backend.call（echo/stats/触发者身份）    [ ] network.fetch（GitHub/白名单外/不可见）
  [ ] base-menu          [ ] record-detail-block（含切换记录重建）
  [ ] home-menu（全局作用域+能力降级）          [ ] dashboard-widget（持久化恢复）
  [ ] opaque origin 隔离  [ ] 签名 URL 鉴权    [ ] 文件令牌隔离
脚本沙箱：
  [ ] 白名单外模块拒   [ ] 危险内建禁   [ ] 超时   [ ] 越权拒   [ ] endpoints 同边界
权限边界： [ ] UI 越权拒   [ ] storage 拒   [ ] network 不可见   [ ] endpoints 404
升级回滚： [ ] 升级   [ ] 回滚   [ ] 卸载
```

> 任何一项未通过，请记录：请求/操作、实际返回、期望返回、相关文件:行（后端 `app/routes/plugins.py`、`app/services/plugin_{service,script_service,proxy_service}.py`；前端 `src/plugins/{registry,api-surface,rpc}.ts`、`src/components/plugins/*`）。
