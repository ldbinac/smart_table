# Smart Table - 智能数据表格管理系统

一个功能强大的数据表格管理系统，支持多种视图模式、数据分组、筛选排序等功能。

## 核心功能

### 1. 数据表管理 ✅

- [x] 创建/编辑/删除数据表
- [x] 数据表重命名
- [x] 数据表列表展示
- [x] 数据表切换

### 2. 字段管理 ✅

- [x] 支持多种字段类型：
  - 文本 (Text)
  - 数字 (Number)
  - 单选 (Single Select)
  - 多选 (Multi Select)
  - 日期 (Date)
  - 复选框 (Checkbox)
  - 评分 (Rating)
  - 进度 (Progress)
  - 附件 (Attachment)
  - 成员 (Member)
  - 关联 (Link)
  - 查找 (Lookup)
  - 公式 (Formula)
  - 自动编号 (Auto Number)
  - 创建人/创建时间/更新人/更新时间 (系统字段)
- [x] 字段配置（必填、默认值、验证规则等）
- [x] 字段排序
- [x] 字段显隐控制

### 3. 视图管理 ✅

- [x] 多视图支持
- [x] 视图切换
- [x] 视图配置持久化
- [x] 视图类型：
  - 表格视图 (Table View) ✅
  - 看板视图 (Kanban View) ✅
  - 日历视图 (Calendar View) ✅
  - 甘特图视图 (Gantt View) ✅
  - 画廊视图 (Gallery View) ✅
  - 表单视图 (Form View) ✅

### 4. 数据分组功能 ✅ (已完成)

- [x] 按任意字段进行数据分组
- [x] 支持多级分组（最多3级）
- [x] 分组展开/折叠功能
- [x] 分组配置面板（弹窗形式）
- [x] 分组状态持久化
- [x] 分组配置独立性（数据表级别隔离）
- [x] 分组内序号独立编号
- [x] 分组下新增数据功能

#### 分组视图特性

- [x] 表头固定（滚动时保持可见）
- [x] 列宽可调整
- [x] 斑马纹样式（隔行变色）
- [x] 行选择功能（复选框、悬停效果）
- [x] 单元格内容提示浮层（tooltip）
- [x] 单选/多选字段样式与标准视图一致
- [x] 日期、数值等字段格式化显示

### 5. 筛选功能 ✅

- [x] 多条件筛选
- [x] 筛选条件组合（AND/OR）
- [x] 筛选配置持久化
- [x] 支持多种筛选操作符

### 6. 排序功能 ✅

- [x] 多字段排序
- [x] 排序方向切换（升序/降序）
- [x] 排序配置持久化
- [x] 拖拽调整排序优先级

### 7. 数据操作 ✅

- [x] 新增记录
- [x] 编辑记录
- [x] 删除记录
- [x] 批量操作
- [x] 数据导入/导出

### 8. 表单功能 ✅

- [x] 表单视图配置
- [x] 表单分享
- [x] 表单数据收集

### 9. 用户体验优化 ✅

- [x] 响应式设计（适配移动端）
- [x] 键盘快捷键支持
- [x] 加载状态提示
- [x] 空状态提示
- [x] 操作反馈（Toast 提示）
- [x] 深色/浅色主题切换

### 10. 性能优化 ✅

- [x] 虚拟滚动（大数据量）
- [x] 数据缓存
- [x] 防抖/节流处理
- [x] 性能监控

## 技术栈

- **前端框架**: Vue 3 + TypeScript
- **状态管理**: Pinia
- **UI 组件库**: Element Plus
- **路由**: Vue Router
- **数据库**: IndexedDB (Dexie.js)
- **构建工具**: Vite
- **测试框架**: Vitest
- **样式**: SCSS

## 项目结构

```
smart-table/
├── src/
│   ├── assets/                    # 静态资源
│   │   └── styles/               # SCSS 样式文件（全局样式、变量、混入）
│   ├── components/                # Vue 组件
│   │   ├── common/               # 通用组件
│   │   │   ├── AppHeader.vue     # 应用头部（导航、用户信息、协作状态）
│   │   │   ├── AppSidebar.vue    # 应用侧边栏
│   │   │   ├── Toast.vue         # 消息提示
│   │   │   ├── Loading.vue       # 加载状态
│   │   │   └── ...
│   │   ├── collaboration/        # 协作组件
│   │   │   └── ...
│   │   ├── dialogs/              # 对话框组件
│   │   │   └── ...
│   │   ├── fields/               # 26 种字段类型组件
│   │   │   ├── ...
│   │   ├── filters/              # 筛选功能组件
│   │   │   ├── FilterPanel.vue           # 筛选面板
│   │   │   ├── FilterCondition.vue       # 筛选条件
│   │   │   └── FilterValueInput.vue      # 筛选值输入
│   │   ├── groups/               # 分组功能组件
│   │   │   ├── GroupPanel.vue            # 分组面板
│   │   │   └── GroupedTableView.vue      # 分组表格视图
│   │   ├── sorts/                # 排序功能组件
│   │   │   └── SortPanel.vue            # 排序面板
│   │   ├── views/                # 视图组件
│   │   │   ├── VTableView/                # 表格视图
│   │   │   ├── KanbanView/               # 看板视图
│   │   │   ├── CalendarView/             # 日历视图
│   │   │   ├── GanttView/                # 甘特图视图
│   │   │   ├── FormView/                 # 表单视图
│   │   │   ├── GalleryView/              # 画廊视图
│   │   │   └── ViewSwitcher.vue          # 视图切换器
│   │   ├── dashboard/            # 仪表盘组件
│   │   │   ├── ...
│   │   ├── documents/            # 文档管理组件（v1.4.0 新增）
│   │   │   ├── DocumentEditor.vue      # 文档编辑器
│   │   │   ├── DocumentHistory.vue     # 版本历史
│   │   │   └── DocumentList.vue        # 文档列表
│   │   ├── auth/                 # 认证组件
│   │   │   ├── LoginForm.vue             # 登录表单
│   │   │   └── RegisterForm.vue          # 注册表单
│   │   └── base/                 # Base 组件
│   │       ├── MemberList.vue            # 成员列表
│   │       └── AddMemberDialog.vue       # 添加成员对话框
│   ├── composables/                # 组合式函数
│   │   ├── useEntityOperations.ts        # 实体操作（CRUD）
│   │   └── useRealtimeCollaboration.ts   # 实时协作
│   ├── db/                         # 数据库层（IndexedDB）
│   │   ├── services/               # 数据服务
│   │   │   ├── ...
│   │   ├── schema.ts               # Dexie 数据库定义
│   │   └── __tests__/              # 测试文件
│   ├── layouts/                    # 布局组件
│   │   ├── MainLayout.vue          # 主布局
│   │   └── BlankLayout.vue         # 空白布局
│   ├── router/                     # Vue Router 配置
│   │   ├── index.ts                # 路由定义
│   │   └── guards.ts               # 路由守卫
│   ├── services/api/               # API 服务层
│   │   ├── ...
│   ├── services/realtime/          # 实时协作服务层
│   │   ├── socketClient.ts         # Socket.IO 客户端
│   │   ├── eventTypes.ts           # 事件类型定义
│   │   └── eventEmitter.ts         # 事件总线
│   ├── stores/                     # Pinia 状态管理
│   │   ├── ..
│   ├── types/                      # TypeScript 类型定义
│   │   ├── fields.ts               # 字段类型定义
│   │   ├── views.ts                # 视图类型定义
│   │   ├── filters.ts              # 筛选类型定义
│   │   ├── attachment.ts           # 附件类型定义
│   │   └── link.ts                 # 关联类型定义
│   ├── utils/                      # 工具函数
│   │   ├── formula/                # 公式引擎
│   │   │   ├── engine.ts           # 公式解析引擎
│   │   │   ├── functions.ts        # 43 个内置函数
│   │   │   └── index.ts
│   │   ├── export/                 # 导出功能
│   │   ├── attachment/             # 附件工具
│   │   │   ├── validators.ts       # 验证器
│   │   │   ├── thumbnail.ts        # 缩略图生成
│   │   │   └── errors.ts           # 错误处理
│   │   ├── filter.ts               # 筛选逻辑
│   │   ├── sort.ts                 # 排序逻辑
│   │   ├── group.ts                # 分组逻辑
│   │   ├── validation.ts           # 数据验证
│   │   ├── importExport.ts         # 导入导出逻辑
│   │   ├── cache.ts                # 缓存工具
│   │   ├── debounce.ts             # 防抖函数
│   │   ├── helpers.ts              # 通用辅助函数
│   │   ├── history.ts              # 历史记录
│   │   ├── id.ts                   # ID 生成
│   │   ├── logger.ts               # 日志工具
│   │   ├── message.ts              # 消息工具
│   │   ├── performance.ts          # 性能优化
│   │   ├── sanitize.ts             # HTML 消毒
│   │   ├── tableTemplates.ts       # 表格模板
│   │   ├── templateGenerator.ts    # 模板生成器
│   │   ├── recordValueSerializer.ts # 记录值序列化
│   │   ├── viewConfigSerializer.ts # 视图配置序列化
│   │   ├── dashboardDataProcessor.ts # 仪表盘数据处理
│   │   ├── dashboardLayoutEngine.ts  # 仪表盘布局引擎
│   │   └── dashboardWidgetRegistry.ts # 仪表盘组件注册
│   ├── views/                      # 页面视图
│   │   ├── Home.vue                # 首页
│   │   ├── Base.vue                 # Base 主页面
│   │   ├── Dashboard.vue            # 仪表盘页面
│   │   ├── DashboardShare.vue       # 仪表盘分享页
│   │   ├── FormShare.vue            # 表单分享页
│   │   ├── BaseShare.vue            # Base 分享页
│   │   ├── Settings.vue             # 设置页面
│   │   ├── auth/                   # 认证页面
│   │   │   ├── Login.vue           # 登录
│   │   │   ├── Register.vue        # 注册
│   │   │   ├── ForgotPassword.vue  # 忘记密码
│   │   │   ├── ResetPassword.vue   # 重置密码
│   │   │   └── VerifyEmail.vue     # 邮箱验证
│   │   ├── admin/                  # 管理后台
│   │   │   ├── UserManagement.vue  # 用户管理
│   │   │   ├── SystemSettings.vue  # 系统设置
│   │   │   ├── EmailTemplates.vue  # 邮件模板
│   │   │   ├── EmailLogs.vue       # 邮件日志
│   │   │   ├── EmailStats.vue      # 邮件统计
│   │   │   └── OperationLogs.vue   # 操作日志
│   │   └── base/                   # Base 相关
│   │       └── MemberManagement.vue # 成员管理
│   ├── App.vue                     # 根组件
│   ├── main.ts                     # 入口文件
│   ├── style.css                   # 全局样式
│   ├── auto-imports.d.ts           # 自动导入类型
│   └── components.d.ts             # 组件类型
├── tests/                          # 测试目录
├── package.json
├── vite.config.ts                  # Vite 配置
├── tsconfig.json                   # TypeScript 配置
├── vitest.config.ts                # Vitest 配置
└── README.md
```

## 开发计划

### 已完成功能

- ✅ 基础数据表管理
- ✅ 字段管理系统
- ✅ 多视图支持（表格、看板、日历、甘特图、画廊、表单）
- ✅ 数据分组功能（核心功能已完成）
- ✅ 筛选和排序
- ✅ 数据导入导出
- ✅ 响应式设计

### 进行中功能

- 🔄 分组视图性能优化（大数据量场景）

### 计划功能

- 📋 数据权限管理
- 📋 协作功能（多人实时编辑）
- 📋 自动化工作流
- 📋 数据可视化图表
- 📋 API 接口开放

## 最近更新

### 2024-03-26

- ✅ 完成数据分组功能核心开发
- ✅ 实现分组视图与标准表格视图样式统一
- ✅ 添加分组内序号独立编号功能
- ✅ 优化分组视图交互体验（展开/折叠、行选择、列宽调整等）

## 运行项目

```bash
# 安装依赖
npm install

# 开发模式
npm run dev

# 构建
npm run build

# 测试
npm run test
```

## 贡献指南

欢迎提交 Issue 和 Pull Request 来改进项目。

## 许可证

MIT License
