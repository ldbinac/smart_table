# SmartTable 插件体系 · 端到端验证指引

> 用途：按本指引逐项验证"插件体系"在当前代码库中的可行性。
> 适用代码：分支 `feat-plugin`（前端 `smart-table/`、后端 `smarttable-backend/`、示例 `examples/plugins/`）。
> 本指引基于实际代码核对（非仅文档）：后端 `app/routes/plugins.py`、`app/services/plugin_service.py`、`app/services/plugin_script_service.py`、`app/script_runner/plugin_runner.py`；前端 `src/views/PluginManage.vue`、`src/stores/pluginStore.ts`、`src/components/plugins/*`、`src/plugins/rpc.ts`。

---

## 0. 可行性结论（先读，避免卡在已知缺口）

**结论：核心链路已基本可行。** 上传 → 全局启用 → **Base 级安装/启用（插件管理页 UI）** → UI 沙箱握手/RPC、脚本代理运行、配置读写、权限拦截、运行日志、回滚/卸载均已落地且自洽。

**安装使用模式（设计决策，验证时请遵循）：**
- 插件的**安装、全局启停、Base 级安装/启停/移除、Base 级配置**全部由管理员在**全局插件管理页**（`/admin/plugins`）完成；
- **Base 页面不提供任何插件安装/管理 UI**，只消费"已在该 Base 安装并启用"的插件（工具栏按钮 / 侧边面板 / 脚本运行结果），打开即用；
- UI 插件运行所需的 base/table 等配置，同样在插件管理页的"配置"弹窗中按 Base 作用域配置。

**已知缺口（会挡住部分"纯 UI"验证，需用 curl 绕过或接受"暂不验证"）：**

1. **`base-menu` / `record-detail-block` 扩展点未挂载**：`registry.ts` 收集了声明，但没有任何宿主组件渲染它们。声明式注册存在，挂载缺失 → 这两项**目前无法端到端验证**。（原"Base 级安装无 UI"缺口已解决：插件管理页卡片新增 Base 安装区，见 §2A.5。）
2. **文档与实现的小出入（不影响功能）**：
   - （已修复）开发者指南原写 `record.get({recordId})`，现与实际实现 `table.getRecord` 对齐；架构设计 §4.2 亦为 `table.getRecord`。
   - 架构设计 §4.2 的 `record.batchUpdate` / `table.addField` / `base.add_field()` 等属"首期预留"，当前**未实现**（示例未涉及）。
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
3. 在该表填 **3~5 条记录**（至少让目标字段有空值，供脚本填充演示）。
4. 从浏览器地址栏复制 `baseId`（URL 形如 `/base/<baseId>/...`）；字段 `fieldId` 稍后从表结构接口或 DevTools 获取。

### 1.4 获取 Admin Token（供 curl 使用）
- 登录后，打开浏览器 DevTools（F12）→ **Network** → 任意已发出的请求 → 复制请求头 `Authorization: Bearer <TOKEN>` 中的 `<TOKEN>`。
- 后续命令用 `curl.exe`（**PowerShell 中 `curl` 是 `Invoke-WebRequest` 别名，必须用 `curl.exe`**），并把 `<TOKEN>`、`<BASE_ID>`、`<FIELD_ID>`、`<TABLE_ID>` 替换为实际值。

> 登录有频率限制（5 次/15 分钟锁定），不要反复重试。

---

## 2. 后端 API 验证清单（curl，逐项勾选）

> 所有请求加 `-H "Authorization: Bearer <TOKEN>"`。后端地址用 `http://localhost:5000`。
> 不想用命令行？第 **2A** 节提供与本节一一对应的纯界面操作验证，二者可任选或互相印证。

### 2.0 打包两个示例插件（包内根即解包根，无路径穿越）
```powershell
cd examples\plugins\hello-panel
python -m zipfile -c ..\..\hello-panel.stplugin.zip manifest.json main.js
cd ..\..\batch-clean
python -m zipfile -c ..\..\batch-clean.stplugin.zip manifest.json main.py
```

### 2.1 上传安装包（admin）
```powershell
curl.exe -X POST http://localhost:5000/api/plugins/upload `
  -H "Authorization: Bearer <TOKEN>" `
  -F "package=@examples/hello-panel.stplugin.zip"
curl.exe -X POST http://localhost:5000/api/plugins/upload `
  -H "Authorization: Bearer <TOKEN>" `
  -F "package=@examples/batch-clean.stplugin.zip"
```
- [ ] **通过**：两次均返回 `plugins` 记录，`id` 分别为 `com.smarttable.hello-panel`、`com.smarttable.batch-clean`，`status=installed`。
- [ ] **异常校验**：上传一个 `manifest.json` 缺 `id`/非法 `version`/未知 `type` 的 zip，应被 `400` 拒绝（验证 `_validate_manifest`）。
- [ ] **路径穿越**：zip 内含 `../evil.txt`，应被 `_safe_extract` 拒绝（解压失败/400）。

### 2.2 列表 / 详情
```powershell
curl.exe http://localhost:5000/api/plugins `
  -H "Authorization: Bearer <TOKEN>"
curl.exe http://localhost:5000/api/plugins/com.smarttable.batch-clean `
  -H "Authorization: Bearer <TOKEN>"
```
- [ ] **通过**：列表含两个插件；详情含 `manifest`、`versions`（版本历史随详情返回）、`current_version=1.0.0`。

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

### 2.4 配置写入与读取（configSchema 校验 + global/base 合并）
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

### 2.5 脚本运行（以触发者身份代理）
```powershell
curl.exe -X POST http://localhost:5000/api/plugins/com.smarttable.batch-clean/run `
  -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" `
  -d "{\"base_id\":\"<BASE_ID>\"}"
```
- [ ] **通过**：返回 `status=success`，`result.updated` > 0（目标字段空值被填充为 `fillValue`）。
- [ ] **副作用**：回到 UI 该表，确认原空值字段已写入 `(空)`。

### 2.6 运行日志
```powershell
curl.exe "http://localhost:5000/api/plugins/com.smarttable.batch-clean/run-logs?base_id=<BASE_ID>" `
  -H "Authorization: Bearer <TOKEN>"
```
- [ ] **通过**：含一条 `success` 记录，`output` 含 `Batch clean 完成`。

### 2.7 回滚 / 卸载（admin，先跳过，留到第 7 节做）
- 端点：`POST /api/plugins/<id>/rollback`（`-d "{\"version\":\"1.0.0\"}"`）、`DELETE /api/plugins/<id>`。

---

## 2A. 界面操作验证（插件管理页 `/admin/plugins`，纯手工点击）

> 适用角色：系统管理员。以下步骤基于已实现的 `PluginManage.vue` 管理界面，与第 2 节 curl 一一对应，可完全不依赖命令行完成插件生命周期主链路验证。
> 前置：已用 admin 登录 `http://localhost:3000`，并完成第 2.0 节打包（`examples/hello-panel.stplugin.zip`、`examples/batch-clean.stplugin.zip`）。

### 2A.1 进入插件管理页
1. [ ] 浏览器访问 `http://localhost:3000/admin/plugins`（或从系统管理菜单进入"插件管理"）。
2. [ ] **权限守卫**：用非管理员账号访问该路由，应被 `adminGuard` 拦截（跳转/403 提示）。

### 2A.2 上传安装包（对应 §2.1）
1. [ ] 点右上角 **上传安装包** → 弹窗中拖入或选择 `hello-panel.stplugin.zip` → 点上传。
   - 成功：绿色提示"上传成功"，列表出现 `com.smarttable.hello-panel` 卡片，状态 `installed`。
2. [ ] 同样方式上传 `batch-clean.stplugin.zip`，列表出现第二张卡片。
3. [ ] **失败提示可读性**：临时把某插件 manifest 的 `engines.smarttable` 改为 `">=2.0.0"` 打包上传 → 应弹出"上传失败: 当前宿主版本 1.6.5 不满足插件声明的引擎兼容范围 …"这类**中文原因说明**（而非裸错误码 `ENGINES_INCOMPATIBLE`）；验证完恢复。
4. [ ] **弹窗状态清空**：上传成功/失败后关闭弹窗，再次打开 → 不应残留上次的安装包文件（`@closed` 清空逻辑，修复项）。
5. [ ] **异常包**：上传缺 `manifest.json` 的 zip → 弹"上传失败: …"（400 校验拒绝）。

### 2A.3 列表卡片信息（对应 §2.2）
- [ ] 每张卡片展示：插件名、`pluginId`、版本 `1.0.0`、类型标签（UI/脚本）、状态标签（installed/enabled/disabled）。
- [ ] 顶部搜索框输入关键词可过滤卡片。

### 2A.4 全局启用/禁用（对应 §2.3）
1. [ ] 在 `hello-panel` 卡片点 **启用** → 状态变为 `enabled`，出现成功提示。
2. [ ] 再切回 **禁用** → 应先弹确认框，确认后状态变为 `disabled`。
3. [ ] 最终保持两个插件均为 **enabled**（后续步骤依赖）。

### 2A.5 Base 级安装 / 启停 / 移除（对应第 3 节 curl 步骤；**仅 UI 插件显示**）

> 设计决策：Base 级安装由管理员在**全局插件管理页**完成，Base 页面不提供安装 UI。
> **适用范围**：`installations` 只用于 UI 插件的 Base 分发挂载（registry `isEffective` + 沙箱加载 URL 校验）；**脚本插件运行由 RBAC + 全局启停控制，不依赖 Base 安装，卡片不显示该区块**（脚本可直接进入 §2A.7 运行）。
> 卡片上的"Base 安装状态"区块展示查询条件区当前所选 Base 下的安装/生效情况；切换 Base 下拉会自动刷新。

1. [ ] `hello-panel`（UI 插件）卡片出现 **Base 安装状态** 区块（标题含当前 Base 名），初始显示 `未安装`；`batch-clean`（脚本插件）卡片**不出现**该区块。
2. [ ] 点 **安装到 Base** → 状态变为 `已停用`/`已启用`（成功提示），卡片出现 **启用/停用** 与 **从 Base 移除** 按钮。
3. [ ] 点 **停用** → 状态变为 `已停用`（提示"已在当前 Base 停用"）；再点 **启用** → 恢复 `已启用`。
4. [ ] **联动校验**：切换查询条件区 Base 下拉 → 卡片安装状态随所选 Base 变化（A Base 已安装、B Base 未安装）。
5. [ ] **从 Base 移除** → 确认弹窗 → 状态回到 `未安装`；重新安装恢复。
6. [ ] **全局停用联动**：全局状态为停用时，已安装的插件在 Base 内不生效，卡片出现提示"全局状态为停用，Base 内不会生效"。
7. [ ] `GET /api/plugins?base_id=<BASE_ID>` 响应中各插件应带 `baseInstalled/baseInstallEnabled/baseEnabled` 字段（卡片数据来源）。
8. [ ] **API 一致性**：对脚本插件（batch-clean）经 curl 调 `POST /api/plugins/com.smarttable.batch-clean/installations` → 应 400 拒绝，提示"仅 UI 插件支持 Base 级安装…"（错误码 `PLUGIN_TYPE_NOT_INSTALLABLE`）。

### 2A.6 配置（对应 §2.4）
1. [ ] `batch-clean` 卡片点 **配置** → 弹窗中选择作用域：
   - `global`：粘贴 `{"fillValue":"(空)"}` → 保存成功提示。
   - `base`：粘贴 `{"tableId":"<TABLE_ID>","fieldId":"<FIELD_ID>"}` → 保存成功提示。
2. [ ] **校验失败**：base 作用域粘贴缺必填项的 `{}` → 应提示保存失败（configSchema 校验 400）。
3. [ ] **页签内容区分**：切换"全局配置"/"当前Base配置"页签 → 文本框应分别显示**对应作用域存储的配置**（base 页签需先选择目标 Base，未选时为空 `{}`）；不再是两个页签同一份内容。
4. [ ] 重新打开配置弹窗 → 各页签回显内容与各自保存的一致（base 页签保存后仅写入该 Base 的存储，不污染 global）。

### 2A.7 脚本运行与运行日志（对应 §2.5 / §2.6）
1. [ ] `batch-clean` 卡片点 **运行** → 弹出"运行脚本插件"对话框，**在对话框中显式选择本次运行的目标 Base**（默认预填查询条件区当前 Base，但以对话框选择为准——运行目标与查询条件解耦）。
2. [ ] 点对话框中的 **运行** → 按钮进入 loading 态；完成后弹出**"插件运行结果"结果弹窗**，分两段展示：①执行信息（运行状态 tag：成功/失败/超时、耗时、当前 Base，附"具体查看插件执行结果"引导语）；②插件执行结果（总体结果 tag + 只读多行文本框，含脚本 `result` JSON、运行输出、错误信息）。底部"运行日志"按钮可直达本次运行所在 Base 的日志。关闭弹窗后回到该 Base 的表确认空值字段已被填充为 `(空)`（副作用生效）。
3. [ ] **Base 不匹配场景**：在 A Base 上保存 base 级配置，却选择在 B Base 上运行 → 应弹红色"脚本运行失败: 缺少 tableId/fieldId 配置… · 当前 Base: B"，据此可立即识别运行目标选错。
4. [ ] 点 **运行日志**（使用查询条件区的 Base）→ 弹窗表格正常渲染：状态（tag：成功/失败/超时/运行中）、耗时、时间、**执行结果列**（脚本 `result` 的单行摘要，超长 tooltip 展示）、错误摘要，每行带 **详情** 按钮（该弹窗曾因分页结构解包问题出现 `rows is not iterable`，现已修复）。
5. [ ] 点某行的 **详情** → 打开"日志详情"弹窗：执行信息（状态/耗时/时间/触发者）+ 插件执行结果（总体结果 tag + `result` 格式化 JSON）+ 运行输出 + 错误信息/异常堆栈（仅失败时显示）。
6. [ ] **业务失败区分**：选一个未配置 `tableId/fieldId` 的 Base 运行 → 运行结果弹窗总体结果应为红色 **失败**（而非"成功"），错误摘要为 `missing tableId/fieldId`，多行文本中仍可见脚本返回的完整 `result`（含 `error` 字段）与输出；日志表该行状态 tag 同为失败。

### 2A.8 升级 / 回滚 / 卸载（对应 §6，可先跳过）
1. [ ] 按第 6 节打好 `1.0.1` 版本包后，重复 2A.2 上传 → 卡片版本变为 `1.0.1`（升级成功提示），配置与安装关系保留。
2. [ ] 点 **回滚** → 弹窗版本下拉应含 `1.0.1` 与 `1.0.0`；选 `1.0.0` 确认 → 版本回退，卡片版本号随之变化。
3. [ ] 点 **卸载** → 确认弹窗 → 卡片从列表消失（可按需重传恢复）。

---

## 3. UI 插件端到端（前端点击验证）

> 关键前提：UI 插件要出现在某 Base 的工具栏，必须**先在该 Base 安装并启用**。
> **推荐方式**：插件管理页 `hello-panel` 卡片的"Base 安装状态"区块 → 安装到 Base → 启用（见 §2A.5）。
> 以下 curl 为等价替代（Base 管理员）：

```powershell
# 在目标 Base 安装并启用 hello-panel（Base 管理员）
curl.exe -X POST http://localhost:5000/api/plugins/com.smarttable.hello-panel/installations `
  -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" `
  -d "{\"base_id\":\"<BASE_ID>\"}"
curl.exe -X PUT http://localhost:5000/api/plugins/com.smarttable.hello-panel/installations `
  -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" `
  -d "{\"base_id\":\"<BASE_ID>\",\"enabled\":true}"
```

然后在 UI 验证：
0. [ ] **勾选依赖（selection）**：
   - [ ] 未勾选任何记录时，"Hello" 按钮为**禁用**态，悬浮提示"请先在表格中勾选记录，再使用该插件"；
   - [ ] 勾选 2~3 条记录后按钮恢复可用，悬浮提示显示"已选 N 条"；
   - [ ] 打开面板显示"已勾选 N 条记录"，批量填充**只作用于勾选记录**（未勾选记录字段值不变）；
   - [ ] 勾选后不重开插件、直接在表格改勾选 → 面板内容不变（打开时快照语义）；
   - [ ] 表头全选 → 面板显示"已勾选 N 条记录（全选）"。
1. [ ] 进入第 1.3 节那张表，工具栏出现 **"Hello"** 按钮（来自 `extensionPoints.toolbar-button`）。
2. [ ] 点击按钮，右侧 Drawer 打开 **Hello Panel**（来自 `extensionPoints.side-panel`），显示标题 `Hello，SmartTable 插件` 并自动加载记录列表。
3. [ ] 选择字段、输入填充值、点"批量填充"：目标字段被写入；弹出 `填充完成：成功 N 条` 提示（`ui.notify` + `record.update` 走通）。
4. [ ] 刷新页面再次打开面板，上次选中的字段被记住（`storage.get/set` + `storage:true` 权限走通）。
5. [ ] **沙箱隔离**：在面板 iframe 内 DevTools Console 执行 `document.cookie` / `window.parent` → 应拿不到宿主 Cookie，且 `event.origin` 为 `"null"`（opaque origin，`sandbox="allow-scripts"` 生效）。
6. [ ] **握手/鉴权**：Network 中 loader.html 请求带 `?st=<签名>`；若直接打开无签名 URL，应 `forbidden`（验证 `verify_sandbox_token`）。

---

## 4. 脚本插件"沙箱与安全边界"验证

1. [ ] **白名单外模块被拒**：临时把 `examples/plugins/batch-clean/main.py` 顶部加 `import os`（或 `import socket`），重新打包上传并运行 → 应运行失败且日志报模块不在白名单（`safe_import` 拒绝 `os`/`socket`）。
2. [ ] **危险内建被禁**：脚本里调用 `open('/etc/passwd')` 或 `eval(...)` → 应被 `DANGEROUS_BUILTINS` 移除而报 `NameError`。
3. [ ] **超时控制**：把 `manifest.json` 的 `script.timeout` 设为极小值（如 `2`），脚本里写 `import time; time.sleep(100)`（注意 `time` 不在白名单 → 改用 `import datetime; ...` 死循环或让循环极长），运行应返回 `timeout`（`MAX_TIMEOUT`/deadline 控制）。
4. [ ] **权限越权被拒**：将 `batch-clean` 的 `permissions.records` 改为 `read` 后重传运行 → `base.update_record` 应被双层权限校验拒绝（宿主侧 `deny by default` + RBAC）。

> 上述"临时修改"请在**副本**上做，验证后恢复，避免污染示例。

---

## 5. 权限边界（UI 侧）

1. [ ] 将 `hello-panel` 的 `permissions` 去掉 `records:write` 后重传并重新走第 3 节 → 点"批量填充"时 `record.update` 应返回 `PERMISSION_DENIED`（宿主侧拒绝对应调用）。
2. [ ] 未声明 `storage` 时，`storage.set` 应被拒（示例里已 try/catch 容错，可从 Network 响应确认 `PERMISSION_DENIED`）。

---

## 6. 升级 / 回滚验证（复用 2.1 上传链路）

1. [ ] 修改 `hello-panel/manifest.json` 的 `version` 为 `1.0.1`（可同时改 `name` 或加一行日志），重新打包上传：
   ```powershell
   cd examples\plugins\hello-panel
   python -m zipfile -c ..\..\hello-panel-v101.stplugin.zip manifest.json main.js
   curl.exe -X POST http://localhost:5000/api/plugins/upload -H "Authorization: Bearer <TOKEN>" -F "package=@examples/hello-panel-v101.stplugin.zip"
   ```
2. [ ] 详情接口 `versions` 现在含 `1.0.0` 与 `1.0.1`，配置与 Base 安装关系保留。
3. [ ] 回滚到 `1.0.0`：
   ```powershell
   curl.exe -X POST http://localhost:5000/api/plugins/com.smarttable.hello-panel/rollback `
     -H "Authorization: Bearer <TOKEN>" -H "Content-Type: application/json" `
     -d "{\"version\":\"1.0.0\"}"
   ```
4. [ ] 回到 UI 该表，插件行为回到 `1.0.0` 版本（回滚生效）。
5. [ ] 卸载：`DELETE /api/plugins/com.smarttable.hello-panel`（admin），列表不再出现；可按需重传恢复。

---

## 7. 暂无法用 UI 验证、但接口已就绪的项（curl 替代）

| 验证项 | 为什么 UI 暂不能验 | curl 验证方式 |
| --- | --- | --- |
| Base 级安装/启停 | **已解决**：插件管理页卡片提供 Base 安装区（§2A.5） | curl 仍可用：第 3 节开头的 `installations` POST/PUT |
| `base-menu` 扩展点 | 无宿主组件渲染 | 声明会被 `registry.baseMenuItems` 收集，但无 UI 呈现 → 标记"未实现，暂不验证" |
| `record-detail-block` 扩展点 | 无宿主组件渲染 | 同上 |
| 独立版本历史接口 `GET /versions` | 未实现 | 版本历史已并入 `GET /<id>`，直接验证后者即可 |

---

## 8. 验证结果记录模板

```
后端 API：
  [ ] 上传/异常校验/路径穿越   [ ] 列表/详情   [ ] 全局启用
  [ ] 配置写入+合并+校验失败   [ ] 脚本运行+副作用   [ ] 运行日志
界面操作（§2A）：
  [ ] 管理页进入/权限守卫   [ ] 弹窗上传×2   [ ] 失败提示可读   [ ] 弹窗无残留
  [ ] 卡片信息/过滤   [ ] 全局启用/禁用   [ ] Base 安装/启停/移除（§2A.5）   [ ] Base 切换联动
  [ ] 配置保存+校验失败   [ ] 运行+结果弹窗+副作用   [ ] 运行日志弹窗+详情
  [ ] 业务失败区分   [ ] 升级   [ ] 回滚   [ ] 卸载
UI 插件：
  [ ] 工具栏按钮   [ ] 侧边面板加载   [ ] 批量填充   [ ] storage 记忆
  [ ] opaque origin 隔离   [ ] 签名 URL 鉴权
脚本沙箱：
  [ ] 白名单外模块拒   [ ] 危险内建禁   [ ] 超时   [ ] 越权拒
权限边界： [ ] UI 越权拒   [ ] storage 拒
升级回滚： [ ] 升级   [ ] 回滚   [ ] 卸载
已知缺口确认： [ ] Base 安装已可用 UI（§2A.5）   [ ] base-menu/record-detail-block 未挂载
```

> 任何一项未通过，请记录：请求/操作、实际返回、期望返回、相关文件:行（后端 `app/routes/plugins.py`、前端 `src/plugins/rpc.ts` / `src/components/plugins/*`）。
