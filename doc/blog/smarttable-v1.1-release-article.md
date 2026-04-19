# 开源多维表格SmartTable v1.1版本更新啦

---

## 一、v1.1 版本更新内容

v1.1 版本更新，主要围绕团队协作、系统安全和运维部署三个方向进行补强。以下是本次更新的完整清单。

### 新增功能

**实时协作**

基于 Flask-SocketIO + Redis 实现的多人实时编辑能力。同一多维表格支持多用户同时在线操作，编辑中的单元格自动锁定，数据变更通过 WebSocket 实时广播到所有在线客户端。冲突场景采用乐观锁机制——比对 `updated_at` 时间戳，检测到冲突时弹出选择界面由用户决定保留哪个版本。

协作功能默认关闭，需在后端配置中设置 `ENABLE_REALTIME=true` 并确保 Redis 可用后启用。

**邮件服务**

完整的邮件系统，覆盖发送、模板、队列、重试四个环节：

- SMTP 连接池管理，支持主流邮件服务商
- Jinja2 模板引擎，HTML 和纯文本双格式渲染
- 队列化发送，避免阻塞主线程
- 发送失败自动重试，最大重试次数可配置
- 内置三套默认模板：注册欢迎、密码重置、邮箱验证

管理员可在后台对模板进行可视化编辑，查看发送日志和统计报表。

**用户认证体系**

v1.1 补全了完整的认证链路：

- 注册 / 登录 / 登出，登录和注册均支持图形验证码
- 忘记密码 → 邮件发送重置链接 → 设置新密码
- 邮箱验证，注册后需点击验证链接激活账号
- 修改密码，登录状态下可自行修改
- JWT 双令牌机制（Access Token + Refresh Token），支持令牌刷新和黑名单（登出即失效）

**仪表盘**

ECharts 驱动的数据可视化面板，支持：

- 柱状图、折线图、饼图三种基础图表
- KPI 指标卡、实时时钟、日期组件、跑马灯等辅助组件
- 网格布局和自由布局两种模式，组件可拖拽调整位置和大小
- 仪表盘分享：生成独立访问链接，可设置访问密码、过期时间、访问次数上限

**管理员面板**

面向系统管理者的后台管理界面：

- 用户管理：列表查询、角色筛选、状态切换、批量删除、重置密码
- 系统配置：SMTP 邮件参数、系统运行参数
- 操作日志：记录关键操作，支持按时间和类型筛选，可导出 CSV
- 邮件管理：模板 CRUD、发送日志查询、统计报表

**角色权限**

实现了六种角色：owner / admin / workspace_admin / editor / commenter / viewer。不同角色对多维表格的操作权限不同，分享链接也可单独设置"仅查看"或"可编辑"。

**Docker 部署**

提供生产级 Docker 部署方案：

- 统一 Dockerfile，三阶段构建（前端编译 → 后端依赖安装 → 生产镜像打包）
- `docker-compose.yml`：SQLite 版，适合小团队快速部署
- `docker-compose.full.yml`：PostgreSQL + Redis 版，适合生产环境
- Nginx 反向代理 + Gunicorn WSGI 服务器 + Supervisor 进程管理

一条 `docker-compose up -d` 即可完成全部部署。

### 安全加固

v1.1 对安全做了系统性排查和修复，主要涉及以下方面：

| 项目 | 措施 |
|------|------|
| XSS 防护 | 前端引入 DOMPurify，所有 `v-html` 和 `innerHTML` 渲染前进行消毒；后端 `sanitize_string()` 清理 script/style 标签 |
| 速率限制 | 五级限制：登录（5次/15分钟）、通用 API（按用户+IP）、文件上传（20次/小时）、数据查询（200次/分钟）、数据写入（100次/分钟） |
| 安全响应头 | X-Content-Type-Options: nosniff、X-Frame-Options: DENY、X-XSS-Protection、Referrer-Policy、Permissions-Policy、HSTS（HTTPS 环境）、CSP（生产环境） |
| 文件上传 | Magic Number 文件头验证 + 扩展名白名单 + SVG 等高风险类型黑名单 |
| 异常信息 | 统一异常处理，API 响应仅返回通用错误描述，内部详情只写服务端日志 |
| 生产日志 | Vite 构建配置 `drop: ['console', 'debugger']`，生产包不含任何调试输出 |
| 密码安全 | bcrypt 哈希存储 + 强度校验（大写+小写+数字，≥8位） |

### Bug 修复

- 修复仪表盘配置页面刷新报错（`loadBase` 方法名错误）
- 修复 ECharts tooltip 中 `params.name` 未转义导致的潜在 XSS
- 修复多个 Vue 组件卸载时未清理事件监听器导致的内存泄漏（EmailStats、Home、GanttView、Dashboard、DashboardShare）
- 修复密码重置路由绕过密码强度校验的问题
- 修复取消收藏接口使用了错误的 HTTP 方法

---

## 二、SmartTable 产品介绍

### 是什么

SmartTable 是一个开源的多维表格管理系统，功能对标 Airtable 和飞书多维表格。你可以用它来搭建各种结构化的数据管理工具——项目追踪、客户管理、库存盘点、内容日历、需求池，诸如此类。

和 Excel 不一样的地方在于，SmartTable 的每一列都有明确的字段类型。文本就是文本，日期就是日期，单选就是单选，关联就是关联。类型约束让数据更干净，也让筛选、排序、分组、公式这些操作变得可靠。

### 核心功能

**22 种字段类型**

文本、数字、日期、单选、多选、复选框、成员、电话、邮箱、链接、附件、公式、关联、查找引用、创建人、创建时间、更新人、更新时间、自动编号、评分、进度、URL。

**6 种视图**

- 表格视图：传统行列展示，支持虚拟滚动和列冻结
- 看板视图：按分组字段展示卡片，支持拖拽排序
- 日历视图：按日期展示，月/周/日三种粒度
- 甘特视图：时间轴展示项目进度
- 画廊视图：以图片为主的卡片展示
- 表单视图：生成可分享的数据收集表单

**43 个公式函数**

数学类（SUM、AVG、ROUND 等 11 个）、文本类（CONCAT、LEFT、FIND 等 10 个）、日期类（TODAY、DATEDIF、DATEADD 等 10 个）、逻辑类（IF、AND、OR 等 7 个）、统计类（COUNTIF、SUMIF 等 5 个）。

**数据操作**

多条件组合筛选（AND/OR）、多字段排序、多级分组（支持折叠/展开和分组统计）、全局搜索、字段显隐控制、列冻结、批量操作。

**导入导出**

Excel（.xlsx/.xls）、CSV、JSON 三种格式，导入导出均支持。

**仪表盘**

ECharts 图表 + 拖拽布局 + 分享功能，上文已介绍。

**实时协作**

WebSocket 多人编辑 + 单元格锁定 + 冲突检测，上文已介绍。

### 技术栈

前端：Vue 3 / TypeScript / Pinia / Element Plus / VXE Table / ECharts / Vite

后端：Flask / SQLAlchemy / Flask-JWT-Extended / Flask-SocketIO / bcrypt / Gunicorn

数据库：PostgreSQL（生产推荐）或 SQLite（轻量部署），Redis（协作功能，可选）

部署：Docker / Nginx / Supervisor

### 适合谁用

- 小团队需要一个灵活的数据管理工具，不想为每个业务场景单独买 SaaS
- 创业公司需要快速搭建内部管理系统，又不想从零开发
- 开发者想基于多维表格做二次开发或集成到自己的产品里
- 任何需要结构化数据管理但觉得 Excel 不够用的个人或团队

### 和同类产品的区别

- 完全开源，MIT 协议，可以自己部署，数据在自己手里
- 不按行数或用户数收费，没有使用限制
- 前后端分离架构，API 完整，方便集成和扩展
- Docker 一键部署，运维成本低

---

## 三、代码仓库

### 仓库地址

| 平台 | 地址 |
|------|------|
| GitHub | https://github.com/ldbinac/smart_table.git |
| Gitee | https://gitee.com/binac/smart_table.git |

两个仓库内容同步，国内用户访问 Gitee 速度更快。

### 为什么值得关注

- 功能完整度高：22 种字段、6 种视图、公式引擎、仪表盘、协作、邮件
- 代码质量有保障：TypeScript 全覆盖、统一异常处理、安全加固、单元测试
- 部署简单：Docker Compose 一条命令启动，不需要复杂的运维知识
- 持续迭代：v1.0 到 v1.1 间隔不到一个周，活跃维护中

### 如何参与

**反馈问题**

在 GitHub Issues 提交 Bug 报告或功能建议，尽量附上复现步骤和环境信息。

**提交代码**

1. Fork 仓库
2. 创建功能分支（`git checkout -b feature/your-feature`）
3. 提交代码（`git commit -m 'Add some feature'`）
4. 推送分支（`git push origin feature/your-feature`）
5. 发起 Pull Request

**获取帮助**

- 项目文档：https://github.com/ldbinac/smart_table/blob/main/doc/Smart-Table-User-Manual.md
- Issues：https://github.com/ldbinac/smart_table/issues

如果觉得项目有用，给个 Star 是最直接的支持方式。
