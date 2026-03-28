# Smart Table

中文 | [English](README.en.md)

一个基于 Vue 3 + TypeScript + Pinia + Dexie (IndexedDB) 的智能多维表格系统，类似于 Airtable 或飞书多维表格。

## 功能特性

### 核心功能

- 多维表格管理 - 创建、编辑、删除、收藏多维表格
- 数据表管理 - 支持多个数据表，拖拽排序、重命名、删除
- 字段管理 - 支持 22 种字段类型
- 记录管理 - 增删改查、批量操作
- 视图管理 - 6 种视图类型，支持筛选、排序、分组

### 支持的字段类型（22种）

| 类别 | 字段类型 | 状态 |
|------|---------|------|
| 基础类型 | 文本 | ✅ |
| 基础类型 | 数字 | ✅ |
| 基础类型 | 日期 | ✅ |
| 基础类型 | 单选 | ✅ |
| 基础类型 | 多选 | ✅ |
| 基础类型 | 复选框 | ✅ |
| 联系类型 | 成员 | ✅ |
| 联系类型 | 电话 | ✅ |
| 联系类型 | 邮箱 | ✅ |
| 联系类型 | 链接 | ✅ |
| 媒体类型 | 附件 | ✅ |
| 计算类型 | 公式 | ✅ |
| 计算类型 | 关联 | ✅ |
| 计算类型 | 查找 | ✅ |
| 系统类型 | 创建人 | ✅ |
| 系统类型 | 创建时间 | ✅ |
| 系统类型 | 更新人 | ✅ |
| 系统类型 | 更新时间 | ✅ |
| 系统类型 | 自动编号 | ✅ |
| 其他 | 评分 | ✅ |
| 其他 | 进度 | ✅ |
| 其他 | URL | ✅ |

### 支持的视图类型（6种）

| 视图类型 | 功能描述 | 状态 |
|---------|---------|------|
| 表格视图 | 经典表格展示，支持虚拟滚动、列冻结 | ✅ |
| 看板视图 | 卡片式展示，支持拖拽排序 | ✅ |
| 日历视图 | 时间维度展示 | ✅ |
| 甘特图视图 | 项目进度展示 | ✅ |
| 表单视图 | 数据收集表单，支持分享 | ✅ |
| 画廊视图 | 图片卡片展示 | ✅ |

### 高级功能

- 数据筛选 - 多条件组合筛选，支持 AND/OR 逻辑
- 数据排序 - 多字段排序
- 数据分组 - 按字段分组展示，支持分组统计
- 数据导入 - 支持 Excel、CSV、JSON 格式
- 数据导出 - 支持 Excel、CSV、JSON 格式
- 公式引擎 - 40+ 内置函数，支持数学、文本、日期、逻辑、统计计算
- 拖拽排序 - 表格、字段、视图拖拽排序
- 收藏功能 - 快速访问常用表格
- 搜索功能 - 快速搜索表格

## 技术栈

| 类别      | 技术                    | 版本    |
| --------- | ----------------------- | ------- |
| 前端框架  | Vue 3                   | ^3.5.30 |
| 语言      | TypeScript              | ~5.9.3  |
| 状态管理  | Pinia                   | ^2.3.1  |
| 数据库    | Dexie (IndexedDB)       | ^3.2.7  |
| UI 组件库 | Element Plus            | ^2.13.6 |
| 表格组件  | vxe-table               | ^4.18.7 |
| 拖拽排序  | sortablejs              | ^1.15.7 |
| 图表      | echarts + vue-echarts   | ^5.6.0  |
| 日期处理  | dayjs                   | ^1.11.20|
| 构建工具  | Vite                    | ^8.0.1  |
| 测试      | Vitest                  | ^3.2.4  |

## 快速开始

### 环境要求

- Node.js >= 18
- npm >= 9

### 安装依赖

```bash
cd smart-table
npm install
```

### 开发模式

```bash
npm run dev
```

### 构建生产版本

```bash
npm run build
```

### 预览生产版本

```bash
npm run preview
```

### 运行测试

```bash
# 运行所有测试
npm run test

# 监听模式运行测试
npm run test:watch

# 生成测试覆盖率报告
npm run test:coverage
```

## 项目结构

```
smart-table/
├── src/
│   ├── assets/              # 静态资源
│   │   └── styles/          # SCSS 样式文件
│   ├── components/          # Vue 组件
│   │   ├── common/          # 通用组件
│   │   ├── dialogs/         # 对话框组件
│   │   ├── fields/          # 22种字段类型组件
│   │   ├── filters/         # 筛选功能组件
│   │   ├── groups/          # 分组功能组件
│   │   ├── sorts/           # 排序功能组件
│   │   └── views/           # 6种视图组件
│   ├── db/                  # 数据库层
│   │   ├── services/        # 数据服务（base/table/field/record/view/dashboard）
│   │   ├── schema.ts        # Dexie 数据库定义
│   │   └── __tests__/       # 测试文件
│   ├── layouts/             # 布局组件
│   ├── router/              # Vue Router 配置
│   ├── stores/              # Pinia 状态管理
│   │   ├── baseStore.ts     # 多维表格状态
│   │   ├── tableStore.ts    # 数据表状态
│   │   ├── viewStore.ts     # 视图状态
│   │   └── ...
│   ├── types/               # TypeScript 类型定义
│   │   ├── fields.ts        # 字段类型定义
│   │   ├── views.ts         # 视图类型定义
│   │   └── filters.ts       # 筛选类型定义
│   ├── utils/               # 工具函数
│   │   ├── export/          # 导出功能
│   │   ├── formula/         # 公式引擎
│   │   ├── filter.ts        # 筛选逻辑
│   │   ├── sort.ts          # 排序逻辑
│   │   └── group.ts         # 分组逻辑
│   └── views/               # 页面视图
├── package.json
├── vite.config.ts
├── tsconfig.json
└── README.md
```

## 数据模型

### Base（多维表格）

- 多维表格基础单元
- 支持收藏、自定义图标和颜色

### Table（数据表）

- 包含字段定义和记录数据
- 支持拖拽排序、收藏

### Field（字段）

- 定义数据列的类型和属性
- 支持 22 种字段类型

### Record（记录）

- 数据行
- 支持增删改查、批量操作

### View（视图）

- 数据展示方式
- 支持筛选、排序、分组配置

## 公式引擎

支持 40+ 内置函数：

### 数学函数
`SUM`, `AVG`, `MAX`, `MIN`, `ROUND`, `CEILING`, `FLOOR`, `ABS`, `MOD`, `POWER`, `SQRT`

### 文本函数
`CONCAT`, `LEFT`, `RIGHT`, `LEN`, `UPPER`, `LOWER`, `TRIM`, `SUBSTITUTE`, `REPLACE`, `FIND`

### 日期函数
`TODAY`, `NOW`, `YEAR`, `MONTH`, `DAY`, `HOUR`, `MINUTE`, `SECOND`, `DATEDIF`, `DATEADD`

### 逻辑函数
`IF`, `AND`, `OR`, `NOT`, `IFERROR`, `IFS`, `SWITCH`

### 统计函数
`COUNT`, `COUNTA`, `COUNTIF`, `SUMIF`, `AVERAGEIF`

## 浏览器支持

- Chrome >= 90
- Firefox >= 88
- Safari >= 14
- Edge >= 90

## 开发计划

### 已实现功能 ✅

- [x] 多维表格 CRUD
- [x] 数据表 CRUD
- [x] 字段管理（22种类型）
- [x] 记录管理
- [x] 6种视图支持（表格、看板、日历、甘特图、表单、画廊）
- [x] 数据筛选
- [x] 数据排序
- [x] 数据分组
- [x] 公式引擎（40+函数）
- [x] 数据导入（Excel/CSV/JSON）
- [x] 数据导出（Excel/CSV/JSON）
- [x] 拖拽排序
- [x] 收藏功能
- [x] 搜索功能
- [x] 表单视图分享

### 待实现功能 📋

- [ ] 协作功能（基于 WebRTC）
- [ ] 权限管理
- [ ] 自动化工作流
- [ ] 插件系统
- [ ] 数据仪表盘
- [ ] 移动端适配

## 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 许可证

[MIT](LICENSE) © 2026 Smart Table Contributors
