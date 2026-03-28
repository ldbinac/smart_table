# UI系统优化规格说明

## Why

当前SmartTable系统的UI页面存在视觉风格不统一、交互体验不一致的问题。首页已完成清新风格的优化，但其他视图页面（表格视图、看板视图、日历视图、甘特视图、表单视图、画册视图）以及仪表盘页面仍使用旧版样式，导致用户体验割裂。需要进行系统性的UI优化，确保整体设计语言统一、界面美观且用户体验一致。

## What Changes

### 优化范围

- **视图组件**：表格视图、看板视图、日历视图、甘特视图、表单视图、画册视图
- **页面组件**：仪表盘页面(Dashboard)、多维表格主页面(Base)、设置页面(Settings)
- **核心设计系统**：统一色彩方案、排版样式、组件规范、交互反馈

### 设计规范统一

- **色彩方案**：采用首页清新风格配色（主色#3B82F6、成功#10B981、警告#F59E0B、危险#EF4444）
- **圆角规范**：卡片12px、按钮20px(药丸形)/10px、输入框8px
- **阴影规范**：统一使用柔和阴影（0 4px 14px rgba(59, 130, 246, 0.35)等）
- **间距规范**：采用8px网格系统，保持一致的间距层级
- **字体规范**：使用系统字体栈，统一字号层级

### 交互体验提升

- **悬停效果**：卡片上浮+阴影加深+操作按钮滑入
- **点击反馈**：按钮缩放+颜色变化
- **加载状态**：骨架屏+渐变动画
- **空状态**：插画风格+友好提示

## Impact

### 受影响文件

- `src/views/Base.vue` - 多维表格主页面
- `src/views/Dashboard.vue` - 仪表盘页面
- `src/views/Settings.vue` - 设置页面
- `src/components/views/TableView/TableView.vue` - 表格视图
- `src/components/views/KanbanView/KanbanView.vue` - 看板视图
- `src/components/views/CalendarView/CalendarView.vue` - 日历视图
- `src/components/views/GanttView/GanttView.vue` - 甘特视图
- `src/components/views/FormView/FormView.vue` - 表单视图
- `src/components/views/GalleryView/GalleryView.vue` - 画册视图
- `src/components/views/ViewSwitcher.vue` - 视图切换器

### 新增文件

- `src/styles/design-system.scss` - 设计系统变量和混合宏
- `src/styles/animations.scss` - 统一动画效果

## ADDED Requirements

### Requirement: 设计系统规范

系统 SHALL 建立统一的设计系统，确保所有UI组件视觉风格一致。

#### Scenario: 色彩系统

- **WHEN** 开发者使用颜色变量
- **THEN** 使用 `$primary: #3B82F6`、`$success: #10B981`、`$warning: #F59E0B`、`$danger: #EF4444` 等标准色值
- **AND** 灰色系使用 Tailwind 风格的灰度系统（$gray-50 到 $gray-900）

#### Scenario: 组件样式规范

- **WHEN** 开发者创建新组件
- **THEN** 卡片使用 `border-radius: 12px`、`border: 1px solid $gray-200`
- **AND** 主按钮使用渐变背景 `linear-gradient(135deg, $primary 0%, #6366F1 100%)`
- **AND** 阴影使用 `box-shadow: 0 4px 14px rgba($primary, 0.35)`

### Requirement: Base页面优化

Base页面（多维表格主页面）SHALL 采用清新风格重新设计。

#### Scenario: 顶部导航栏

- **WHEN** 用户查看Base页面
- **THEN** 顶部导航栏使用毛玻璃效果 `backdrop-filter: blur(10px)`
- **AND** 背景使用半透明白色 `rgba(255, 255, 255, 0.95)`
- **AND** 底部有细边框分隔 `border-bottom: 1px solid $gray-200`

#### Scenario: 数据表标签栏

- **WHEN** 用户查看数据表标签
- **THEN** 当前选中标签有底部指示条
- **AND** 标签悬停时有背景色变化
- **AND** 支持拖拽排序的视觉反馈

#### Scenario: 工具栏按钮

- **WHEN** 用户查看工具栏
- **THEN** 按钮使用圆角设计
- **AND** 主要操作按钮使用渐变背景
- **AND** 按钮悬停时有阴影和上浮效果

### Requirement: 表格视图优化

表格视图 SHALL 优化视觉样式和交互体验。

#### Scenario: 表头样式

- **WHEN** 用户查看表格表头
- **THEN** 表头背景使用浅灰色 `$gray-50`
- **AND** 字体使用深色 `$gray-700` 加粗
- **AND** 边框使用细线 `$gray-200`

#### Scenario: 单元格样式

- **WHEN** 用户查看表格单元格
- **THEN** 单元格有合适的内边距 `12px 16px`
- **AND** 行悬停时有背景色变化 `background: $gray-50`
- **AND** 选中行有高亮边框

#### Scenario: 字段类型标识

- **WHEN** 用户查看不同字段类型
- **THEN** 每种字段类型有对应的图标和颜色标识
- **AND** 字段配置按钮悬停时显示

### Requirement: 看板视图优化

看板视图 SHALL 采用卡片式设计和流畅的拖拽交互。

#### Scenario: 看板列样式

- **WHEN** 用户查看看板列
- **THEN** 列标题有清晰的视觉层级
- **AND** 列背景使用浅灰色
- **AND** 列计数徽章使用圆角设计

#### Scenario: 看板卡片样式

- **WHEN** 用户查看看板卡片
- **THEN** 卡片使用圆角12px
- **AND** 卡片有柔和阴影
- **AND** 卡片悬停时上浮并增强阴影
- **AND** 拖拽时有视觉反馈（半透明+旋转）

### Requirement: 日历视图优化

日历视图 SHALL 采用现代化日历设计风格。

#### Scenario: 日历头部

- **WHEN** 用户查看日历头部
- **THEN** 月份切换按钮使用圆角设计
- **AND" 当前日期有特殊标识
- **AND** 视图切换（月/周/日）使用分段控制器样式

#### Scenario: 日历格子

- **WHEN** 用户查看日历格子
- **THEN** 格子有细边框分隔
- **AND** 当天格子有高亮背景
- **AND** 事件卡片使用圆角和颜色标识

### Requirement: 甘特视图优化

甘特视图 SHALL 优化时间轴和任务条的视觉表现。

#### Scenario: 时间轴样式

- **WHEN** 用户查看时间轴
- **THEN** 时间轴刻度清晰可读
- **AND** 周末日期有特殊背景色
- **AND** 当前日期有垂直指示线

#### Scenario: 任务条样式

- **WHEN** 用户查看任务条
- **THEN** 任务条使用圆角6px
- **AND** 任务条有渐变色
- **AND** 任务条悬停时显示详细信息
- **AND** 拖拽调整时有视觉反馈

### Requirement: 表单视图优化

表单视图 SHALL 采用现代化的表单设计风格。

#### Scenario: 表单字段样式

- **WHEN** 用户查看表单字段
- **THEN** 字段标签使用清晰的字体层级
- **AND** 输入框使用圆角8px
- **AND** 输入框聚焦时有蓝色边框和光晕
- **AND** 必填字段有红色星号标识

#### Scenario: 表单布局

- **WHEN** 用户查看表单
- **THEN** 表单有合适的字段间距
- **AND** 提交按钮使用渐变背景
- **AND** 表单有清晰的视觉分组

### Requirement: 画册视图优化

画册视图 SHALL 采用瀑布流或网格布局展示图片。

#### Scenario: 画册卡片样式

- **WHEN** 用户查看画册卡片
- **THEN** 图片使用圆角12px
- **AND** 卡片有柔和阴影
- **AND** 卡片悬停时显示操作按钮
- **AND** 图片加载时有骨架屏占位

### Requirement: 仪表盘优化

仪表盘页面 SHALL 采用现代化的数据可视化设计。

#### Scenario: 图表组件样式

- **WHEN** 用户查看图表
- **THEN** 图表使用统一的配色方案
- **AND** 图表有圆角边框
- **AND** 图表标题使用清晰的字体层级

#### Scenario: 仪表盘布局

- **WHEN** 用户查看仪表盘
- **THEN** 组件使用网格布局
- **AND** 组件支持拖拽调整位置
- **AND** 组件有统一的间距

### Requirement: 视图切换器优化

视图切换器 SHALL 采用现代化的分段控制器设计。

#### Scenario: 切换器样式

- **WHEN** 用户查看视图切换器
- **THEN** 当前选中视图有高亮背景
- **AND** 切换器使用圆角设计
- **AND** 切换时有平滑过渡动画

### Requirement: 响应式适配

所有视图 SHALL 支持响应式设计，在不同设备上均有良好表现。

#### Scenario: 移动端适配

- **WHEN** 用户在移动设备上访问
- **THEN** 布局自动调整为单列
- **AND** 触摸目标大小合适（最小44px）
- **AND** 字体大小可读（不小于14px）

#### Scenario: 平板适配

- **WHEN** 用户在平板上访问
- **THEN** 布局调整为适合屏幕宽度的列数
- **AND** 保持桌面端的核心功能

### Requirement: 性能优化

UI优化 SHALL 不影响页面性能，并尽可能提升渲染效率。

#### Scenario: 动画性能

- **WHEN** 页面执行动画
- **THEN** 使用 `transform` 和 `opacity` 属性
- **AND** 添加 `will-change` 提示
- **AND** 动画帧率保持 60fps

#### Scenario: 渲染性能

- **WHEN** 页面渲染大量数据
- **THEN** 使用虚拟滚动技术
- **AND** 避免不必要的重绘和重排
- **AND** 首屏加载时间 < 2s

## MODIFIED Requirements

### Requirement: 现有样式变量

现有样式变量 SHALL 更新为新的设计系统规范。

#### Scenario: 变量更新

- **WHEN** 开发者使用 `$primary-color`
- **THEN** 值更新为 `#3B82F6`
- **AND** 所有使用旧变量的地方自动更新

## REMOVED Requirements

无移除需求
