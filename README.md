# Smart Table

中文 | [English](README.en.md)

一个基于 Vue 3 + TypeScript + Pinia + Dexie (IndexedDB) 的智能多维表格系统，类似于 Airtable 或飞书多维表格。

## 功能特性

### 核心功能
- 多维表格管理 - 创建、编辑、删除、收藏多维表格
- 数据表管理 - 支持多个数据表，拖拽排序、重命名、删除
- 字段管理 - 支持 20+ 种字段类型
- 记录管理 - 增删改查、批量操作
- 视图管理 - 多种视图类型，支持筛选、排序、分组

### 支持的字段类型
- 基础类型：文本、数字、日期、复选框
- 选择类型：单选、多选
- 联系类型：成员、电话、邮箱、链接
- 媒体类型：附件
- 计算类型：公式、关联、查找
- 系统类型：创建人、创建时间、更新人、更新时间、自动编号
- 其他：评分、进度

### 支持的视图类型
- 表格视图 - 经典表格展示
- 看板视图 - 卡片式展示
- 日历视图 - 时间维度展示
- 甘特图视图 - 项目进度展示
- 表单视图 - 数据收集表单
- 画廊视图 - 图片卡片展示

### 高级功能
- 数据筛选 - 多条件组合筛选
- 数据排序 - 多字段排序
- 数据分组 - 按字段分组展示
- 数据导出 - 支持 Excel、CSV 格式
- 拖拽排序 - 表格、字段、视图拖拽排序
- 收藏功能 - 快速访问常用表格
- 搜索功能 - 快速搜索表格

## 技术栈

| 类别 | 技术 |
|------|------|
| 前端框架 | Vue 3 (Composition API) |
| 语言 | TypeScript |
| 状态管理 | Pinia |
| 数据库 | Dexie (IndexedDB) |
| UI 组件库 | Element Plus |
| 表格组件 | vxe-table |
| 拖拽排序 | sortablejs |
| 图表 | echarts + vue-echarts |
| 构建工具 | Vite |
| 测试 | Vitest |

## 快速开始

### 环境要求
- Node.js >= 18
- npm >= 9

### 安装依赖

```bash
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
│   │   ├── fields/          # 字段类型组件
│   │   ├── filters/         # 筛选功能组件
│   │   ├── groups/          # 分组功能组件
│   │   ├── sorts/           # 排序功能组件
│   │   └── views/           # 视图组件
│   ├── db/                  # 数据库层
│   │   ├── services/        # 数据服务
│   │   ├── schema.ts        # Dexie 数据库定义
│   │   └── __tests__/       # 测试文件
│   ├── layouts/             # 布局组件
│   ├── router/              # Vue Router 配置
│   ├── stores/              # Pinia 状态管理
│   ├── types/               # TypeScript 类型定义
│   ├── utils/               # 工具函数
│   │   ├── export/          # 导出功能
│   │   └── formula/         # 公式引擎
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
- 支持 20+ 种字段类型

### Record（记录）
- 数据行
- 支持增删改查、批量操作

### View（视图）
- 数据展示方式
- 支持筛选、排序、分组配置

## 浏览器支持

- Chrome >= 90
- Firefox >= 88
- Safari >= 14
- Edge >= 90

## 开发计划

- [x] 多维表格 CRUD
- [x] 数据表 CRUD
- [x] 字段管理
- [x] 记录管理
- [x] 多视图支持
- [x] 数据筛选排序
- [x] 数据导出
- [x] 拖拽排序
- [x] 收藏功能
- [x] 搜索功能
- [ ] 数据导入
- [ ] 协作功能
- [ ] 权限管理
- [ ] 自动化工作流

## 贡献指南

欢迎提交 Issue 和 Pull Request！

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 许可证

[MIT](LICENSE) © 2024 Smart Table Contributors
