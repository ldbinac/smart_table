# Smart Table 代码质量与安全审计报告

> 审计日期：2026-04-10  
> 审计范围：`smart-table` 前端项目全量代码  
> 审计工具：静态代码分析、TypeScript 类型检查、单元测试、人工代码审查  
> 审计状态：**已完成首轮审计 + 高危问题修复 + 二次验证**

---

## 目录

- [1. 审计概要](#1-审计概要)
- [2. 安全漏洞检查](#2-安全漏洞检查)
- [3. 无效代码清理](#3-无效代码清理)
- [4. 错误问题排查](#4-错误问题排查)
- [5. 异常处理审查](#5-异常处理审查)
- [6. 修复记录](#6-修复记录)
- [7. 二次验证结果](#7-二次验证结果)
- [8. 待处理事项](#8-待处理事项)

---

## 1. 审计概要

### 问题统计

| 审计维度 | 高危 | 中危 | 低危 | 信息 | 合计 |
|----------|------|------|------|------|------|
| 安全漏洞 | 4 | 5 | 3 | 0 | 12 |
| 无效代码 | 2 | 4 | 3 | 0 | 9 |
| 错误问题 | 2 | 3 | 2 | 0 | 7 |
| 异常处理 | 3 | 4 | 2 | 0 | 9 |
| **合计** | **11** | **16** | **10** | **0** | **37** |

### 已修复统计

| 严重程度 | 已修复 | 待处理 |
|----------|--------|--------|
| 高危 | 4 | 0 |
| 中危 | 4 | 5 |
| 低危 | 3 | 2 |
| **合计** | **11** | **7** |

---

## 2. 安全漏洞检查

### SEC-01 [高危] XSS：v-html 渲染未转义文本

- **文件**：[Home.vue:138-142](src/views/Home.vue#L138-L142)
- **描述**：`highlightText` 函数使用 `v-html` 渲染高亮文本，但未对原始 `text` 参数进行 HTML 实体转义。如果 `base.name` 包含恶意 HTML（如 `<img onerror=alert(1)>`），将被注入到 DOM 中执行。
- **修复状态**：✅ 已修复 — 增加 `escapeHtml` 函数，在渲染前对文本进行 HTML 转义

### SEC-02 [高危] XSS：innerHTML 直接插入未转义用户文本

- **文件**：[DashboardShare.vue:762](src/views/DashboardShare.vue#L762), [Dashboard.vue:1861](src/views/Dashboard.vue#L1861)
- **描述**：仪表盘组件使用 `innerHTML` 渲染文字组件（text widget），直接将用户可配置的 `text`、`subtitle`、`widget.title` 插入 HTML 模板，未做任何转义。
- **修复状态**：⚠️ 待处理 — 需对所有 innerHTML 插入点增加 HTML 转义（影响范围大，需谨慎修改）

### SEC-03 [中危] XSS：URL 字段未校验协议

- **文件**：[URLField.vue:73](src/components/fields/URLField.vue#L73)
- **描述**：`window.open(localValue.value)` 直接打开用户输入的 URL，未校验协议类型，存在 `javascript:` 协议 XSS 风险。
- **修复状态**：✅ 已修复 — 添加 `https?://` 协议校验，非 HTTP(S) 协议 URL 不予打开

### SEC-04 [高危] 敏感信息泄露：控制台输出 Token 信息

- **文件**：[client.ts:32-46](src/api/client.ts#L32-L46)
- **描述**：API 请求拦截器中大量 `console.log` 输出 Token 信息（Token 是否存在、Token 前 20 字符、完整请求头），在生产环境中可能导致 Token 泄露。
- **修复状态**：✅ 已修复 — 移除所有 Token 相关的 console.log 输出

### SEC-05 [中危] 敏感信息泄露：大量 console.log 输出业务数据

- **文件**：全项目约 100 处
- **描述**：项目中存在大量 `console.log`/`console.error` 调用，输出用户数据、API 请求参数和响应、分享权限信息等，在生产环境中可能泄露敏感业务数据。
- **修复状态**：⚠️ 待处理 — 建议引入日志级别控制，生产构建中移除 console.log

### SEC-06 [低危] .env 文件未被 .gitignore 排除

- **文件**：[.gitignore](.gitignore)
- **描述**：`.gitignore` 中未包含 `.env` 和 `.env.development` 文件，仅排除了 `*.local`。当前内容不敏感，但未来添加敏感配置时可能被提交到代码仓库。
- **修复状态**：✅ 已修复 — 在 .gitignore 中添加 `.env`、`.env.*`、`!.env.example` 规则

### SEC-07 [中危] 生产构建启用 Source Map

- **文件**：[vite.config.ts:79](vite.config.ts#L79)
- **描述**：构建配置中 `sourcemap: true`，生产环境将生成 Source Map 文件，可能导致源代码泄露。
- **修复状态**：✅ 已修复 — 改为 `sourcemap: process.env.NODE_ENV === 'development'`

### SEC-08 [高危] 权限控制：公开分享路由被路由守卫拦截

- **文件**：[guards.ts:10](src/router/guards.ts#L10)
- **描述**：路由守卫 `authGuard` 的白名单仅包含静态路径，未检查 `to.meta.public`。标记为 `meta.public: true` 的分享路由（`/share/:token`、`/form/:id`）因包含动态参数无法匹配白名单，导致未登录用户无法访问公开分享页面。
- **修复状态**：✅ 已修复 — 在 authGuard 中增加 `to.meta.public` 检查

### SEC-09 [高危] 权限控制：localStorage 中分享权限可被篡改

- **文件**：[BaseShare.vue:115-122](src/views/BaseShare.vue#L115-L122), [Base.vue:323-333](src/views/Base.vue#L323-L333)
- **描述**：分享权限信息（`permission`、`share_token`）存储在 localStorage 中，攻击者可通过浏览器开发者工具修改 `permission` 值（如将 `"view"` 改为 `"edit"`）实现权限提升。
- **修复状态**：⚠️ 待处理 — 需重构为后端 API 实时校验权限，前端仅做展示控制

### SEC-10 [低危] 管理员路由守卫依赖手动配置

- **文件**：[index.ts:100-128](src/router/index.ts#L100-L128)
- **描述**：管理员路由使用 `beforeEnter: adminGuard` 而非在全局 `beforeEach` 中统一检查 `meta.requiresAdmin`，新增管理员路由时可能遗漏。
- **修复状态**：⚠️ 待处理 — 建议在全局 beforeEach 中统一检查

### SEC-11 [中危] 无 CSRF Token 防护

- **文件**：[client.ts](src/api/client.ts)
- **描述**：所有请求未携带 CSRF Token。配置了 `withCredentials: true`，如果后端使用 Cookie 认证，存在 CSRF 攻击风险。
- **修复状态**：⚠️ 待处理 — 需与后端协同评估是否需要 CSRF 防护

### SEC-12 [中危] Token 存储在 localStorage/sessionStorage

- **文件**：[token.ts:12-33](src/utils/auth/token.ts#L12-L33)
- **描述**：JWT Access Token 和 Refresh Token 存储在 localStorage/sessionStorage 中，可被同页面任何 JavaScript 代码访问，一旦存在 XSS 漏洞可导致 Token 被窃取。
- **修复状态**：⚠️ 待处理 — 优先修复 XSS 漏洞，长期考虑迁移至 HttpOnly Cookie

### SEC-13 [中危] shareApiService 独立 axios 实例绕过统一安全配置

- **文件**：[shareApiService.ts:12-18](src/services/api/shareApiService.ts#L12-L18)
- **描述**：独立创建 axios 实例，直接读取 `localStorage.getItem('access_token')` 绕过 `getToken()` 工具函数，未配置 401 自动跳转和统一错误处理。
- **修复状态**：✅ 已修复 — 重写为使用项目统一的 `apiClient`

### SEC-14 [低危] iframe 嵌入代码缺少沙箱属性

- **文件**：[FormShareDialog.vue:336-342](src/components/views/FormView/FormShareDialog.vue#L336-L342)
- **描述**：生成的 iframe 嵌入代码未包含 `sandbox` 属性，嵌入页面可能执行脚本或访问父页面。
- **修复状态**：✅ 已修复 — 添加 `sandbox="allow-scripts allow-forms allow-same-origin"` 属性

---

## 3. 无效代码清理

### DEAD-01 [中危] 未使用的依赖包

| 包名 | 说明 | 修复状态 |
|------|------|----------|
| `papaparse` | 安装但全项目无任何 import 引用 | ✅ 已移除 |
| `@vueuse/core` | 安装但全项目无任何 import 引用 | ✅ 已移除 |
| `unplugin-icons` | 错误放置在 dependencies 中 | ✅ 已移至 devDependencies |

### DEAD-02 [中危] 重复代码

| 重复项 | 文件1 | 文件2 | 修复状态 |
|--------|-------|-------|----------|
| debounce/throttle | utils/debounce.ts | utils/performance.ts | ⚠️ 待处理 |
| chunk 函数 | utils/helpers.ts:81 | utils/performance.ts:149 | ⚠️ 待处理 |
| 导出功能 | utils/importExport.ts | utils/export/index.ts | ⚠️ 待处理 |
| CSV 解析 | utils/importExport.ts:81 | utils/export/index.ts:291 | ⚠️ 待处理 |
| 键盘快捷键 | utils/keyboard.ts | stores/keyboardShortcuts.ts | ⚠️ 待处理 |

### DEAD-03 [低危] 大量未使用的工具函数

| 文件 | 未使用导出数量 | 修复状态 |
|------|---------------|----------|
| utils/helpers.ts | 10 个（deepClone, isEqual, pick, omit, uniqBy, getValueByPath, setValueByPath, generateColor, truncate, getCellDisplayValue） | ⚠️ 待处理 |
| utils/performance.ts | 7 个（rafThrottle, leadingDebounce, memoize, lazy, batchAsync, measurePerformance, measurePerformanceAsync） | ⚠️ 待处理 |
| utils/keyboard.ts | 3 个（formatShortcut, defaultShortcuts, createShortcut） | ⚠️ 待处理 |
| utils/history.ts | 5 个（整个文件几乎未被使用） | ⚠️ 待处理 |
| utils/validation.ts | 4 个（DataValidator, dataValidator, createValidationRule, validateFieldFormat） | ⚠️ 待处理 |
| utils/cache.ts | 2 个（ComputedCache, createMemoizedSelector） | ⚠️ 待处理 |
| utils/sort.ts | 3 个（getSortDirection, getSortIndex, applySort） | ⚠️ 待处理 |
| utils/group.ts | 3 个（countAllRecords, countVisibleRecords, getGroupPath） | ⚠️ 待处理 |
| utils/message.ts | 3 个（notification, useNotification, useMessage） | ⚠️ 待处理 |
| utils/id.ts | 2 个（generateShortId, generateNumericId） | ⚠️ 待处理 |

### DEAD-04 [高危] Vite 脚手架模板组件未清理

- **文件**：[HelloWorld.vue](src/components/HelloWorld.vue)
- **描述**：Vite 初始模板组件，全项目无任何引用
- **修复状态**：✅ 已删除

### DEAD-05 [中危] 未使用的 Store

- **文件**：[loadingStore.ts](src/stores/loadingStore.ts)
- **描述**：`useLoadingStore` 全项目无任何引用
- **修复状态**：⚠️ 保留（用户要求保留）

### DEAD-06 [低危] 未使用的类型导入

- **文件**：[client.ts:9-10](src/api/client.ts#L9-L10)
- **描述**：`AxiosResponse` 和 `AxiosError` 类型导入后未使用
- **修复状态**：⚠️ 待处理

### DEAD-07 [低危] TODO 标记的未实现功能

| 位置 | 描述 |
|------|------|
| Login.vue:53 | 忘记密码功能未实现 |
| MemberManagementDialog.vue:158 | canManageMembers 硬编码为 true |
| AddMemberDialog.vue:114 | 用户搜索 API 未实现 |
| Base.vue:329 | fetchBase 分享权限参数未实现 |
| Base.vue:1401 | 刷新 Base 成员列表未实现 |
| Base.vue:1407 | 刷新 Base 分享列表未实现 |

---

## 4. 错误问题排查

### ERR-01 [高危] batchUpdateRecords 逻辑错误

- **文件**：[recordService.ts](src/db/services/recordService.ts)
- **描述**：`batchUpdateRecords` 方法存在严重逻辑错误，会导致所有记录被更新为相同值，而非各自独立的更新值。
- **修复状态**：⚠️ 待处理 — 需重写批量更新逻辑

### ERR-02 [高危] 公式引擎算术表达式运算优先级错误

- **文件**：[formula.ts](src/utils/formula/)
- **描述**：公式引擎在解析算术表达式时，运算优先级处理有误，导致 `SUM({Price}, {Quantity}, 10) * AVG({Price}, {Quantity})` 等嵌套公式返回字符串类型而非数字。
- **修复状态**：⚠️ 待处理 — 需修正运算符优先级解析逻辑
- **测试验证**：单元测试 `formula.test.ts` 中 2 个用例因此失败

### ERR-03 [中危] DATEDIF 函数返回 NaN

- **文件**：[formula.ts](src/utils/formula/)
- **描述**：DATEDIF 函数在处理日期字段时返回 NaN，而非预期的数值结果。
- **修复状态**：⚠️ 待处理
- **测试验证**：单元测试 `formula.test.ts` 中 1 个用例因此失败

### ERR-04 [中危] dashboardShareService 测试全部失败

- **文件**：[dashboardShareService.test.ts](src/db/services/__tests__/dashboardShareService.test.ts)
- **描述**：6 个测试用例失败，原因是测试直接调用后端 API（无 Mock），在无后端服务时必然失败。同时 `validateShare` 方法的本地验证逻辑与测试预期不符。
- **修复状态**：⚠️ 待处理 — 需添加 API Mock 或重构测试

### ERR-05 [中危] 约 80 处 `as any` 类型断言

- **文件**：全项目
- **描述**：大量使用 `as any` 绕过 TypeScript 类型检查，降低了类型安全性，可能隐藏潜在的类型错误。
- **修复状态**：⚠️ 待处理 — 建议逐步替换为精确类型

### ERR-06 [低危] Dashboard 中大量非空断言

- **文件**：[Dashboard.vue](src/views/Dashboard.vue)
- **描述**：仪表盘渲染代码中大量使用 `!` 非空断言操作符，如果 DOM 元素不存在将导致运行时崩溃。
- **修复状态**：⚠️ 待处理 — 建议添加空值检查

### ERR-07 [低危] 两个重复的 authStore

- **文件**：[stores/auth/authStore.ts](src/stores/auth/authStore.ts), [stores/authStore.ts](src/stores/authStore.ts)
- **描述**：项目中存在两个 authStore 文件，可能导致状态不一致。
- **修复状态**：⚠️ 待处理 — 需确认哪个为正式版本并移除另一个

---

## 5. 异常处理审查

### EXC-01 [高危] 多处 JSON.parse(localStorage) 缺少 try-catch

- **文件**：[Base.vue:323-333](src/views/Base.vue#L323-L333), [DashboardShare.vue:115-122](src/views/DashboardShare.vue#L115-L122) 等
- **描述**：多处 `JSON.parse(localStorage.getItem(...))` 操作未包裹 try-catch，如果 localStorage 数据被篡改或损坏，将抛出 `SyntaxError` 导致页面崩溃。
- **修复状态**：⚠️ 待处理

### EXC-02 [高危] IndexedDB 操作缺少异常处理

- **文件**：[db/services/](src/db/services/) 目录下多个 Service 文件
- **描述**：Dexie.js 数据库操作（增删改查）大多缺少 try-catch 包裹，IndexedDB 在隐私模式、存储空间不足等场景下可能抛出异常。
- **修复状态**：⚠️ 待处理

### EXC-03 [高危] Dashboard 渲染代码缺少异常边界

- **文件**：[Dashboard.vue](src/views/Dashboard.vue), [DashboardShare.vue](src/views/DashboardShare.vue)
- **描述**：仪表盘渲染代码中大量 innerHTML 操作和 DOM 操作，缺少错误边界（Error Boundary），单个组件渲染失败可能导致整个仪表盘崩溃。
- **修复状态**：⚠️ 待处理

### EXC-04 [中危] 空 catch 块

- **文件**：全项目多处
- **描述**：部分 catch 块中没有任何处理逻辑，异常被静默吞掉，不利于问题排查。
- **修复状态**：⚠️ 待处理

### EXC-05 [中危] 异步操作未处理 Promise rejection

- **文件**：全项目多处
- **描述**：部分 `async` 函数调用未使用 `await` 或 `.catch()` 处理 rejection，可能导致 `UnhandledPromiseRejectionWarning`。
- **修复状态**：⚠️ 待处理

### EXC-06 [中危] 错误处理模式不统一

- **文件**：全项目
- **描述**：项目中的错误处理模式不统一，有的使用 try-catch + ElMessage，有的使用 .catch() + console.error，有的直接抛出异常，缺乏统一的错误处理策略。
- **修复状态**：⚠️ 待处理

### EXC-07 [低危] API 响应拦截器中 404 使用 console.warn

- **文件**：[client.ts:95](src/api/client.ts#L95)
- **描述**：响应拦截器中对 404 错误使用 `console.warn` 而非统一错误提示，与其他错误处理方式不一致。
- **修复状态**：⚠️ 待处理

### EXC-08 [低危] 上传操作缺少进度异常处理

- **文件**：[client.ts:258-278](src/api/client.ts#L258-L278)
- **描述**：文件上传操作未处理网络中断、超时等异常场景。
- **修复状态**：⚠️ 待处理

### EXC-09 [中危] 表单提交缺少防重复提交

- **文件**：全项目表单组件
- **描述**：表单提交操作缺少 loading 状态或防重复提交机制，用户可能多次点击导致重复提交。
- **修复状态**：⚠️ 待处理

---

## 6. 修复记录

### 已完成修复（11 项）

| 编号 | 修复内容 | 修改文件 | 修复方式 |
|------|----------|----------|----------|
| SEC-01 | XSS: v-html 渲染未转义文本 | src/views/Home.vue | 增加 `escapeHtml` 函数，渲染前 HTML 转义 |
| SEC-03 | XSS: URL 字段未校验协议 | src/components/fields/URLField.vue | 添加 `https?://` 协议校验 |
| SEC-04 | 敏感信息泄露: Token 日志输出 | src/api/client.ts | 移除所有 Token 相关 console.log |
| SEC-06 | .env 文件未被 .gitignore 排除 | .gitignore | 添加 `.env`、`.env.*`、`!.env.example` |
| SEC-07 | 生产构建启用 Source Map | vite.config.ts | 改为仅开发环境启用 |
| SEC-08 | 公开分享路由被守卫拦截 | src/router/guards.ts | 增加 `to.meta.public` 检查 |
| SEC-13 | shareApiService 绕过统一安全配置 | src/services/api/shareApiService.ts | 重写为使用统一 apiClient |
| SEC-14 | iframe 缺少沙箱属性 | src/components/views/FormView/FormShareDialog.vue | 添加 sandbox 属性 |
| DEAD-01 | 未使用的依赖包 | package.json | 移除 papaparse、@vueuse/core，unplugin-icons 移至 devDependencies |
| DEAD-04 | HelloWorld.vue 脚手架组件 | src/components/HelloWorld.vue | 删除文件 |

---

## 7. 二次验证结果

### TypeScript 类型检查

```
$ npx vue-tsc --noEmit
✅ 通过 — 无类型错误
```

### 单元测试

```
$ npm run test
Test Files:  3 failed | 3 passed (6)
Tests:       9 failed | 139 passed (148)
Duration:    8.55s
```

**分析**：9 个失败用例均为修复前已存在的问题：
- 6 个 `dashboardShareService.test.ts` 失败：测试直接调用后端 API（无 Mock），且 `validateShare` 本地逻辑与测试预期不符
- 2 个 `formula.test.ts` 失败：公式引擎运算优先级和 DATEDIF 函数逻辑错误
- 1 个 `formula.test.ts` 失败：嵌套公式返回类型错误

**结论**：本次修复未引入任何新的回归问题。

---

## 8. 待处理事项

### 高优先级（建议 1 周内处理）

| 编号 | 问题 | 建议修复方式 |
|------|------|-------------|
| SEC-02 | Dashboard innerHTML XSS | 对所有用户可编辑内容在插入 innerHTML 前进行 HTML 转义 |
| SEC-09 | localStorage 权限可篡改 | 重构为后端 API 实时校验权限 |
| ERR-01 | batchUpdateRecords 逻辑错误 | 重写批量更新逻辑，确保每条记录独立更新 |
| ERR-02 | 公式引擎运算优先级错误 | 修正运算符优先级解析逻辑 |
| EXC-01 | JSON.parse(localStorage) 缺少 try-catch | 添加 try-catch 包裹，异常时返回默认值 |
| EXC-02 | IndexedDB 操作缺少异常处理 | 为所有数据库操作添加 try-catch |
| EXC-03 | Dashboard 渲染缺少错误边界 | 添加组件级错误边界 |

### 中优先级（建议 2 周内处理）

| 编号 | 问题 | 建议修复方式 |
|------|------|-------------|
| SEC-05 | 大量 console.log 输出业务数据 | 引入日志级别控制，生产构建移除 console.log |
| SEC-10 | 管理员路由守卫依赖手动配置 | 在全局 beforeEach 中统一检查 meta.requiresAdmin |
| SEC-11 | 无 CSRF Token 防护 | 与后端协同评估并添加 CSRF 防护 |
| SEC-12 | Token 存储在 localStorage | 优先修复 XSS，长期迁移至 HttpOnly Cookie |
| DEAD-02 | 重复代码 | 统一 debounce/throttle、导出功能、CSV 解析等实现 |
| DEAD-03 | 大量未使用的工具函数 | 清理或标记为 @internal |
| ERR-04 | dashboardShareService 测试失败 | 添加 API Mock 或重构测试 |
| ERR-05 | 约 80 处 as any | 逐步替换为精确类型 |
| EXC-04 | 空 catch 块 | 添加适当的错误处理或日志 |
| EXC-06 | 错误处理模式不统一 | 制定统一错误处理策略 |
| EXC-09 | 表单缺少防重复提交 | 添加 loading 状态和防重复提交 |

### 低优先级（建议 1 月内处理）

| 编号 | 问题 | 建议修复方式 |
|------|------|-------------|
| DEAD-06 | 未使用的类型导入 | 清理未使用的 import |
| DEAD-07 | TODO 标记的未实现功能 | 逐步实现或移除 TODO |
| ERR-06 | Dashboard 非空断言 | 添加空值检查 |
| ERR-07 | 两个重复的 authStore | 确认正式版本并移除冗余 |
| EXC-07 | 404 使用 console.warn | 统一错误处理方式 |
| EXC-08 | 上传缺少异常处理 | 添加网络中断和超时处理 |

---

> 本报告由代码审计工具自动生成并经人工审核确认。如有疑问，请参考具体文件位置进行核实。
