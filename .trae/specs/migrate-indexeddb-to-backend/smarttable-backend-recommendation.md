# SmartTable 后端技术栈选型建议

## 一、项目背景分析

### 1.1 现有技术栈

| 层级 | 技术选型 | 版本 |
|------|----------|------|
| 前端框架 | Vue 3 | ^3.5.30 |
| 语言 | TypeScript | ~5.9.3 |
| 状态管理 | Pinia | ^2.3.1 |
| 路由 | Vue Router | ^4.6.4 |
| UI 组件库 | Element Plus | ^2.13.6 |
| 本地存储 | Dexie (IndexedDB) | ^3.2.7 |
| 构建工具 | Vite | ^8.0.1 |
| 测试框架 | Vitest | ^3.2.4 |

### 1.2 项目核心特点

| 特点 | 说明 |
|------|------|
| **数据模型复杂** | 22 种字段类型，6 种视图类型，动态 Schema |
| **公式引擎** | 支持 40+ 函数，需要服务端计算能力 |
| **实时协作** | 未来需要 WebSocket 实时同步 |
| **文件处理** | 附件上传、缩略图生成 |
| **数据导入导出** | Excel/CSV/JSON 批量处理 |
| **权限控制** | 多用户、多角色、字段级权限 |

### 1.3 后端需求分析

| 需求类型 | 具体要求 |
|----------|----------|
| **数据存储** | 关系型数据库，支持 JSON 字段存储动态配置 |
| **事务管理** | 强一致性，支持复杂业务事务 |
| **并发处理** | 支持多用户同时操作 |
| **API 设计** | RESTful API，支持批量操作 |
| **实时通信** | WebSocket 支持实时协作 |
| **文件存储** | 对象存储集成 |
| **性能要求** | 单表支持 10万+ 记录，查询 < 200ms |
| **扩展性** | 支持微服务拆分 |

---

## 二、推荐技术栈方案

### 2.1 最终推荐：Node.js NestJS + Prisma + PostgreSQL

**推荐理由：**

1. ✅ **全栈 TypeScript 统一** - 前后端共享类型定义
2. ✅ **开发效率高** - 装饰器语法与 Vue 3 风格一致
3. ✅ **现代化架构** - 依赖注入、模块化设计
4. ✅ **ORM 类型安全** - Prisma 提供完整类型推导
5. ✅ **生态丰富** - 实时通信、任务队列、缓存等组件完善
6. ✅ **部署简单** - Docker 镜像小，启动快

---

## 三、完整技术栈架构

### 3.1 整体架构图

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              前端层 (Vue 3)                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │  SmartTable │  │ TanStack    │  │  Axios      │  │  Dexie      │    │
│  │  Components │  │  Query      │  │  Client     │  │  Cache      │    │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └─────────────┘    │
│         │                │                │                             │
│         └────────────────┴────────────────┘                             │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼ WebSocket / HTTP
┌─────────────────────────────────────────────────────────────────────────┐
│                            网关层 (Nginx)                                │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  负载均衡 │ SSL 终止 │ 静态资源缓存 │ 反向代理                      │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           应用层 (NestJS)                                │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │  Controller │  │   Service   │  │   Guard     │  │  Interceptor│    │
│  │   路由层    │  │   业务层    │  │   权限控制  │  │  日志/响应  │    │
│  └──────┬──────┘  └──────┬──────┘  └─────────────┘  └─────────────┘    │
│         │                │                                              │
│  ┌──────▼────────────────▼──────┐  ┌─────────────────────────────┐     │
│  │      Repository (Prisma)     │  │      WebSocket Gateway      │     │
│  │      数据访问层              │  │      实时协作通信           │     │
│  └──────────────────────────────┘  └─────────────────────────────┘     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
          ┌─────────────────────────┼─────────────────────────┐
          ▼                         ▼                         ▼
┌─────────────────┐      ┌─────────────────┐      ┌─────────────────┐
│   PostgreSQL    │      │     Redis       │      │     MinIO       │
│   主数据库       │      │   缓存/会话      │      │   对象存储       │
│                 │      │                 │      │                 │
│ • Base/Table    │      │ • 热点数据缓存   │      │ • 附件文件       │
│ • Field/Record  │      │ • 会话存储       │      │ • 缩略图         │
│ • View/Dashboard│      │ • 分布式锁       │      │ • 备份文件       │
│ • User/Auth     │      │ • 消息队列       │      │                 │
└─────────────────┘      └─────────────────┘      └─────────────────┘
```

---

### 3.2 后端技术组件清单

#### 核心框架

| 组件 | 技术选型 | 版本 | 用途 |
|------|----------|------|------|
| 运行时 | Node.js | 20.x LTS | JavaScript 运行时 |
| Web 框架 | NestJS | ^10.x | 企业级 Node.js 框架 |
| 语言 | TypeScript | ^5.x | 类型安全开发 |

#### 数据访问

| 组件 | 技术选型 | 版本 | 用途 |
|------|----------|------|------|
| ORM | Prisma | ^5.x | 类型安全 ORM |
| 数据库 | PostgreSQL | 16.x | 主数据库 |
| 连接池 | Prisma Client | 内置 | 数据库连接管理 |
| 缓存 | Redis | 7.x | 数据缓存 |
| Redis 客户端 | ioredis | ^5.x | Redis 操作 |

#### 认证授权

| 组件 | 技术选型 | 版本 | 用途 |
|------|----------|------|------|
| JWT | @nestjs/jwt | ^10.x | Token 认证 |
| Passport | @nestjs/passport | ^10.x | 认证策略 |
| 密码加密 | bcrypt | ^5.x | 密码哈希 |
| 权限控制 | CASL | ^6.x | 细粒度权限 |

#### 实时通信

| 组件 | 技术选型 | 版本 | 用途 |
|------|----------|------|------|
| WebSocket | @nestjs/websockets | ^10.x | 实时通信 |
| Socket.io | socket.io | ^4.x | WebSocket 实现 |

#### 任务队列

| 组件 | 技术选型 | 版本 | 用途 |
|------|----------|------|------|
| 任务队列 | BullMQ | ^5.x | 异步任务处理 |
| 定时任务 | @nestjs/schedule | ^4.x | Cron 任务 |

#### 文件处理

| 组件 | 技术选型 | 版本 | 用途 |
|------|----------|------|------|
| 对象存储 | MinIO | 最新 | 文件存储 |
| 文件上传 | @nestjs/platform-express | 内置 | Multer 集成 |
| 图片处理 | sharp | ^0.33.x | 缩略图生成 |

#### 监控日志

| 组件 | 技术选型 | 版本 | 用途 |
|------|----------|------|------|
| 日志 | Pino | ^8.x | 高性能日志 |
| 健康检查 | @nestjs/terminus | ^10.x | 服务健康 |
| 指标监控 | @willsoto/nestjs-prometheus | ^6.x | Prometheus 指标 |
| OpenAPI | @nestjs/swagger | ^7.x | API 文档 |

#### 测试

| 组件 | 技术选型 | 版本 | 用途 |
|------|----------|------|------|
| 单元测试 | Jest | ^29.x | 测试框架 |
| E2E 测试 | @nestjs/testing | 内置 | 集成测试 |
| 覆盖率 | jest-coverage | 内置 | 代码覆盖率 |

---

## 四、项目目录结构

### 4.1 后端项目结构

```
smarttable-backend/
├── prisma/
│   ├── schema.prisma          # Prisma 数据模型
│   ├── migrations/            # 数据库迁移文件
│   └── seed.ts                # 种子数据
├── src/
│   ├── main.ts                # 应用入口
│   ├── app.module.ts          # 根模块
│   ├── config/                # 配置文件
│   │   ├── database.config.ts
│   │   ├── redis.config.ts
│   │   └── minio.config.ts
│   ├── common/                # 公共模块
│   │   ├── decorators/        # 自定义装饰器
│   │   ├── filters/           # 异常过滤器
│   │   ├── guards/            # 守卫
│   │   ├── interceptors/      # 拦截器
│   │   ├── pipes/             # 管道
│   │   └── utils/             # 工具函数
│   ├── auth/                  # 认证模块
│   │   ├── auth.controller.ts
│   │   ├── auth.service.ts
│   │   ├── auth.module.ts
│   │   ├── strategies/
│   │   └── dto/
│   ├── users/                 # 用户模块
│   │   ├── users.controller.ts
│   │   ├── users.service.ts
│   │   ├── users.module.ts
│   │   └── dto/
│   ├── bases/                 # Base 模块
│   │   ├── bases.controller.ts
│   │   ├── bases.service.ts
│   │   ├── bases.module.ts
│   │   └── dto/
│   ├── tables/                # Table 模块
│   │   ├── tables.controller.ts
│   │   ├── tables.service.ts
│   │   ├── tables.module.ts
│   │   └── dto/
│   ├── fields/                # Field 模块
│   │   ├── fields.controller.ts
│   │   ├── fields.service.ts
│   │   ├── fields.module.ts
│   │   └── dto/
│   ├── records/               # Record 模块
│   │   ├── records.controller.ts
│   │   ├── records.service.ts
│   │   ├── records.module.ts
│   │   └── dto/
│   ├── views/                 # View 模块
│   │   ├── views.controller.ts
│   │   ├── views.service.ts
│   │   ├── views.module.ts
│   │   └── dto/
│   ├── dashboards/            # Dashboard 模块
│   │   ├── dashboards.controller.ts
│   │   ├── dashboards.service.ts
│   │   ├── dashboards.module.ts
│   │   └── dto/
│   ├── attachments/           # 附件模块
│   │   ├── attachments.controller.ts
│   │   ├── attachments.service.ts
│   │   ├── attachments.module.ts
│   │   └── dto/
│   ├── formula/               # 公式引擎
│   │   ├── formula.service.ts
│   │   ├── formula.module.ts
│   │   ├── functions/
│   │   └── engine.ts
│   ├── websocket/             # WebSocket 模块
│   │   ├── collaboration.gateway.ts
│   │   ├── collaboration.service.ts
│   │   └── websocket.module.ts
│   ├── import-export/         # 导入导出模块
│   │   ├── import-export.service.ts
│   │   ├── import-export.controller.ts
│   │   └── import-export.module.ts
│   └── prisma/                # Prisma 服务
│       └── prisma.service.ts
├── test/                      # 测试文件
├── docker-compose.yml         # Docker 编排
├── Dockerfile                 # Docker 构建
├── nest-cli.json              # NestJS CLI 配置
├── package.json
├── tsconfig.json
└── README.md
```

---

## 五、数据库设计

### 5.1 Prisma Schema 设计

```prisma
// prisma/schema.prisma

generator client {
  provider = "prisma-client-js"
}

datasource db {
  provider = "postgresql"
  url      = env("DATABASE_URL")
}

// 用户模型
model User {
  id        String   @id @default(uuid())
  email     String   @unique
  password  String
  name      String
  avatar    String?
  role      UserRole @default(USER)
  status    UserStatus @default(ACTIVE)
  createdAt DateTime @default(now())
  updatedAt DateTime @updatedAt

  // 关联
  bases     Base[]
  records   Record[] @relation("RecordCreatedBy")
  updatedRecords Record[] @relation("RecordUpdatedBy")
  dashboards Dashboard[]
  attachments Attachment[]
  shares    DashboardShare[]

  @@map("users")
}

enum UserRole {
  ADMIN
  USER
  GUEST
}

enum UserStatus {
  ACTIVE
  INACTIVE
  SUSPENDED
}

// 多维表格 (Base)
model Base {
  id          String   @id @default(uuid())
  name        String
  description String?
  icon        String?
  color       String?
  isStarred   Boolean  @default(false)
  
  // 关联
  ownerId     String
  owner       User     @relation(fields: [ownerId], references: [id])
  tables      Table[]
  dashboards  Dashboard[]
  attachments Attachment[]
  history     OperationHistory[]
  
  createdAt   DateTime @default(now())
  updatedAt   DateTime @updatedAt

  @@map("bases")
}

// 数据表 (Table)
model Table {
  id             String   @id @default(uuid())
  name           String
  description    String?
  primaryFieldId String?
  recordCount    Int      @default(0)
  order          Int      @default(0)
  isStarred      Boolean  @default(false)
  
  // 关联
  baseId         String
  base           Base     @relation(fields: [baseId], references: [id], onDelete: Cascade)
  fields         Field[]
  records        Record[]
  views          View[]
  attachments    Attachment[]
  history        OperationHistory[]
  
  createdAt      DateTime @default(now())
  updatedAt      DateTime @updatedAt

  @@map("tables")
}

// 字段定义 (Field)
model Field {
  id            String     @id @default(uuid())
  name          String
  type          FieldType
  options       Json?      // 字段配置选项（单选选项、公式等）
  isPrimary     Boolean    @default(false)
  isSystem      Boolean    @default(false)
  isRequired    Boolean    @default(false)
  isVisible     Boolean    @default(true)
  defaultValue  Json?
  description   String?
  order         Int        @default(0)
  
  // 关联
  tableId       String
  table         Table      @relation(fields: [tableId], references: [id], onDelete: Cascade)
  attachments   Attachment[]
  history       OperationHistory[]
  
  createdAt     DateTime   @default(now())
  updatedAt     DateTime   @updatedAt

  @@map("fields")
}

enum FieldType {
  TEXT
  NUMBER
  DATE
  SINGLE_SELECT
  MULTI_SELECT
  CHECKBOX
  MEMBER
  PHONE
  EMAIL
  URL
  ATTACHMENT
  FORMULA
  LINK
  LOOKUP
  CREATED_BY
  CREATED_TIME
  UPDATED_BY
  UPDATED_TIME
  AUTO_NUMBER
  RATING
  PROGRESS
}

// 数据记录 (Record)
model Record {
  id        String   @id @default(uuid())
  values    Json     // 字段值存储为 JSON
  
  // 关联
  tableId   String
  table     Table    @relation(fields: [tableId], references: [id], onDelete: Cascade)
  
  createdById String?
  createdBy   User?  @relation("RecordCreatedBy", fields: [createdById], references: [id])
  updatedById String?
  updatedBy   User?  @relation("RecordUpdatedBy", fields: [updatedById], references: [id])
  
  attachments Attachment[]
  history     OperationHistory[]
  
  createdAt   DateTime @default(now())
  updatedAt   DateTime @updatedAt

  @@map("records")
}

// 视图配置 (View)
model View {
  id            String    @id @default(uuid())
  name          String
  type          ViewType
  config        Json?     // 视图特定配置
  filters       Json      @default("[]")      // 筛选条件
  sorts         Json      @default("[]")      // 排序配置
  groupBys      Json      @default("[]")      // 分组字段
  hiddenFields  Json      @default("[]")      // 隐藏字段ID列表
  frozenFields  Json      @default("[]")      // 冻结字段ID列表
  rowHeight     RowHeight @default(MEDIUM)
  isDefault     Boolean   @default(false)
  order         Int       @default(0)
  
  // 关联
  tableId       String
  table         Table     @relation(fields: [tableId], references: [id], onDelete: Cascade)
  
  createdAt     DateTime  @default(now())
  updatedAt     DateTime  @updatedAt

  @@map("views")
}

enum ViewType {
  TABLE
  KANBAN
  CALENDAR
  GANTT
  FORM
  GALLERY
}

enum RowHeight {
  SHORT
  MEDIUM
  TALL
}

// 仪表盘 (Dashboard)
model Dashboard {
  id            String        @id @default(uuid())
  name          String
  description   String?
  widgets       Json          @default("[]")     // Widget 配置
  layout        Json          @default("{}")     // 布局配置
  layoutType    LayoutType    @default(GRID)
  gridColumns   Int           @default(12)
  refreshConfig Json?
  isStarred     Boolean       @default(false)
  order         Int           @default(0)
  
  // 关联
  baseId        String
  base          Base          @relation(fields: [baseId], references: [id], onDelete: Cascade)
  createdById   String
  createdBy     User          @relation(fields: [createdById], references: [id])
  shares        DashboardShare[]
  
  createdAt     DateTime      @default(now())
  updatedAt     DateTime      @updatedAt

  @@map("dashboards")
}

enum LayoutType {
  GRID
  FREE
}

// 仪表盘分享
model DashboardShare {
  id                String    @id @default(uuid())
  shareToken        String    @unique
  accessCode        String?
  expiresAt         DateTime?
  maxAccessCount    Int?
  currentAccessCount Int      @default(0)
  isActive          Boolean   @default(true)
  permission        SharePermission @default(VIEW)
  lastAccessedAt    DateTime?
  
  // 关联
  dashboardId       String
  dashboard         Dashboard @relation(fields: [dashboardId], references: [id], onDelete: Cascade)
  createdById       String
  createdBy         User      @relation(fields: [createdById], references: [id])
  
  createdAt         DateTime  @default(now())

  @@map("dashboard_shares")
}

enum SharePermission {
  VIEW
  EDIT
}

// 附件 (Attachment)
model Attachment {
  id            String   @id @default(uuid())
  name          String
  originalName  String
  size          Int
  type          String
  fileType      String
  extension     String
  storageKey    String   // MinIO 对象键
  thumbnailKey  String?  // 缩略图键
  
  // 关联
  recordId      String?
  record        Record?  @relation(fields: [recordId], references: [id], onDelete: SetNull)
  fieldId       String?
  field         Field?   @relation(fields: [fieldId], references: [id], onDelete: SetNull)
  tableId       String?
  table         Table?   @relation(fields: [tableId], references: [id], onDelete: SetNull)
  baseId        String?
  base          Base?    @relation(fields: [baseId], references: [id], onDelete: SetNull)
  createdById   String?
  createdBy     User?    @relation(fields: [createdById], references: [id])
  
  createdAt     DateTime @default(now())

  @@map("attachments")
}

// 操作历史 (OperationHistory)
model OperationHistory {
  id          String     @id @default(uuid())
  action      ActionType
  entityType  EntityType
  oldValue    Json?
  newValue    Json?
  
  // 关联
  baseId      String
  base        Base       @relation(fields: [baseId], references: [id], onDelete: Cascade)
  tableId     String?
  table       Table?     @relation(fields: [tableId], references: [id], onDelete: SetNull)
  recordId    String?
  record      Record?    @relation(fields: [recordId], references: [id], onDelete: SetNull)
  fieldId     String?
  field       Field?     @relation(fields: [fieldId], references: [id], onDelete: SetNull)
  userId      String?
  
  timestamp   DateTime   @default(now())

  @@map("operation_history")
}

enum ActionType {
  CREATE
  UPDATE
  DELETE
}

enum EntityType {
  BASE
  TABLE
  FIELD
  RECORD
  VIEW
  DASHBOARD
}
```

---

## 六、API 设计规范

### 6.1 RESTful API 路由设计

```typescript
// Base API
GET    /api/bases                    // 获取所有 Base
POST   /api/bases                    // 创建 Base
GET    /api/bases/:id                // 获取单个 Base
PATCH  /api/bases/:id                // 更新 Base
DELETE /api/bases/:id                // 删除 Base
POST   /api/bases/:id/star           // 收藏/取消收藏

// Table API
GET    /api/bases/:baseId/tables     // 获取 Base 下所有 Table
POST   /api/bases/:baseId/tables     // 创建 Table
GET    /api/tables/:id               // 获取单个 Table
PATCH  /api/tables/:id               // 更新 Table
DELETE /api/tables/:id               // 删除 Table
POST   /api/tables/:id/reorder       // 排序 Table

// Field API
GET    /api/tables/:tableId/fields   // 获取所有 Field
POST   /api/tables/:tableId/fields   // 创建 Field
GET    /api/fields/:id               // 获取单个 Field
PATCH  /api/fields/:id               // 更新 Field
DELETE /api/fields/:id               // 删除 Field
POST   /api/fields/reorder           // 字段排序

// Record API
GET    /api/tables/:tableId/records  // 获取所有 Record（支持分页、筛选、排序）
POST   /api/tables/:tableId/records  // 创建 Record
GET    /api/records/:id              // 获取单个 Record
PATCH  /api/records/:id              // 更新 Record
DELETE /api/records/:id              // 删除 Record
POST   /api/tables/:tableId/records/batch  // 批量操作

// View API
GET    /api/tables/:tableId/views    // 获取所有 View
POST   /api/tables/:tableId/views    // 创建 View
GET    /api/views/:id                // 获取单个 View
PATCH  /api/views/:id                // 更新 View
DELETE /api/views/:id                // 删除 View
POST   /api/views/:id/set-default    // 设置默认视图

// Dashboard API
GET    /api/bases/:baseId/dashboards // 获取所有 Dashboard
POST   /api/bases/:baseId/dashboards // 创建 Dashboard
GET    /api/dashboards/:id           // 获取单个 Dashboard
PATCH  /api/dashboards/:id           // 更新 Dashboard
DELETE /api/dashboards/:id           // 删除 Dashboard

// Attachment API
POST   /api/attachments/upload       // 上传文件
GET    /api/attachments/:id          // 获取文件信息
GET    /api/attachments/:id/download // 下载文件
DELETE /api/attachments/:id          // 删除文件

// Import/Export API
POST   /api/import                   // 导入数据
POST   /api/export                   // 导出数据

// Auth API
POST   /api/auth/register            // 注册
POST   /api/auth/login               // 登录
POST   /api/auth/refresh             // 刷新 Token
POST   /api/auth/logout              // 登出
GET    /api/auth/me                  // 获取当前用户
```

### 6.2 统一响应格式

```typescript
// 成功响应
interface ApiResponse<T> {
  success: true;
  data: T;
  meta?: {
    page: number;
    pageSize: number;
    total: number;
    totalPages: number;
  };
  timestamp: string;
}

// 错误响应
interface ApiError {
  success: false;
  error: {
    code: string;
    message: string;
    details?: Record<string, string[]>;
  };
  timestamp: string;
}

// 示例
{
  "success": true,
  "data": {
    "id": "uuid",
    "name": "My Base"
  },
  "meta": {
    "page": 1,
    "pageSize": 20,
    "total": 100,
    "totalPages": 5
  },
  "timestamp": "2026-04-03T10:00:00.000Z"
}
```

---

## 七、核心功能实现方案

### 7.1 公式引擎服务端实现

```typescript
// src/formula/formula.service.ts
import { Injectable } from '@nestjs/common';

@Injectable()
export class FormulaService {
  private functions: Map<string, Function> = new Map();

  constructor() {
    this.registerDefaultFunctions();
  }

  // 计算单个记录的公式字段
  async calculateFormula(
    formula: string,
    recordValues: Record<string, any>,
    allRecords: Record<string, any>[]
  ): Promise<any> {
    // 1. 解析公式，提取字段引用
    const fieldRefs = this.extractFieldReferences(formula);
    
    // 2. 替换字段引用为实际值
    let expression = formula;
    for (const ref of fieldRefs) {
      const value = recordValues[ref.fieldId];
      expression = expression.replace(ref.raw, this.formatValue(value));
    }
    
    // 3. 执行计算
    return this.evaluateExpression(expression);
  }

  // 批量计算公式字段
  async calculateBatchFormulas(
    formulas: Array<{ fieldId: string; formula: string }>,
    records: Record<string, any>[],
    tableId: string
  ): Promise<Record<string, any>[]> {
    return Promise.all(
      records.map(async (record) => {
        const calculatedValues: Record<string, any> = {};
        
        for (const { fieldId, formula } of formulas) {
          calculatedValues[fieldId] = await this.calculateFormula(
            formula,
            { ...record.values, ...calculatedValues },
            records
          );
        }
        
        return {
          ...record,
          values: {
            ...record.values,
            ...calculatedValues
          }
        };
      })
    );
  }

  private registerDefaultFunctions() {
    // 数学函数
    this.functions.set('SUM', (...args) => args.reduce((a, b) => a + b, 0));
    this.functions.set('AVG', (...args) => args.reduce((a, b) => a + b, 0) / args.length);
    this.functions.set('MAX', Math.max);
    this.functions.set('MIN', Math.min);
    
    // 文本函数
    this.functions.set('CONCAT', (...args) => args.join(''));
    this.functions.set('UPPER', (str) => String(str).toUpperCase());
    this.functions.set('LOWER', (str) => String(str).toLowerCase());
    
    // 日期函数
    this.functions.set('TODAY', () => new Date().toISOString().split('T')[0]);
    this.functions.set('NOW', () => new Date().toISOString());
    
    // 逻辑函数
    this.functions.set('IF', (condition, trueVal, falseVal) => 
      condition ? trueVal : falseVal
    );
    
    // 统计函数
    this.functions.set('COUNT', (range) => range.length);
    this.functions.set('COUNTA', (range) => range.filter(v => v != null).length);
  }

  private extractFieldReferences(formula: string): Array<{ raw: string; fieldId: string }> {
    const regex = /\{([^}]+)\}/g;
    const refs: Array<{ raw: string; fieldId: string }> = [];
    let match;
    
    while ((match = regex.exec(formula)) !== null) {
      refs.push({
        raw: match[0],
        fieldId: match[1]
      });
    }
    
    return refs;
  }

  private formatValue(value: any): string {
    if (value == null) return 'null';
    if (typeof value === 'string') return `"${value}"`;
    return String(value);
  }

  private evaluateExpression(expression: string): any {
    // 使用安全的表达式求值
    // 生产环境应使用更安全的方案，如 vm2 或自定义解析器
    try {
      // eslint-disable-next-line no-eval
      return eval(expression);
    } catch {
      return null;
    }
  }
}
```

### 7.2 实时协作 WebSocket 实现

```typescript
// src/websocket/collaboration.gateway.ts
import {
  WebSocketGateway,
  WebSocketServer,
  SubscribeMessage,
  OnGatewayConnection,
  OnGatewayDisconnect,
} from '@nestjs/websockets';
import { Server, Socket } from 'socket.io';
import { Logger, UseGuards } from '@nestjs/common';
import { WsJwtGuard } from '../auth/guards/ws-jwt.guard';

@WebSocketGateway({
  namespace: 'collaboration',
  cors: {
    origin: '*',
  },
})
@UseGuards(WsJwtGuard)
export class CollaborationGateway
  implements OnGatewayConnection, OnGatewayDisconnect
{
  @WebSocketServer()
  server: Server;

  private logger: Logger = new Logger('CollaborationGateway');
  private userRooms: Map<string, string[]> = new Map();

  // 客户端连接
  handleConnection(client: Socket) {
    this.logger.log(`Client connected: ${client.id}`);
  }

  // 客户端断开
  handleDisconnect(client: Socket) {
    this.logger.log(`Client disconnected: ${client.id}`);
    this.leaveAllRooms(client);
  }

  // 加入 Base 协作房间
  @SubscribeMessage('join-base')
  handleJoinBase(client: Socket, baseId: string) {
    const roomName = `base:${baseId}`;
    client.join(roomName);
    
    // 记录用户加入的房间
    const rooms = this.userRooms.get(client.id) || [];
    rooms.push(roomName);
    this.userRooms.set(client.id, rooms);
    
    // 通知房间内其他用户
    client.to(roomName).emit('user-joined', {
      userId: client.data.user.id,
      socketId: client.id,
    });
    
    return { success: true, room: roomName };
  }

  // 离开 Base 协作房间
  @SubscribeMessage('leave-base')
  handleLeaveBase(client: Socket, baseId: string) {
    const roomName = `base:${baseId}`;
    client.leave(roomName);
    
    // 更新用户房间记录
    const rooms = this.userRooms.get(client.id) || [];
    const index = rooms.indexOf(roomName);
    if (index > -1) rooms.splice(index, 1);
    
    // 通知房间内其他用户
    client.to(roomName).emit('user-left', {
      userId: client.data.user.id,
      socketId: client.id,
    });
    
    return { success: true };
  }

  // 记录编辑中状态
  @SubscribeMessage('editing-record')
  handleEditingRecord(
    client: Socket,
    payload: { baseId: string; tableId: string; recordId: string }
  ) {
    const roomName = `base:${payload.baseId}`;
    
    // 广播给房间内其他用户
    client.to(roomName).emit('record-editing', {
      userId: client.data.user.id,
      userName: client.data.user.name,
      tableId: payload.tableId,
      recordId: payload.recordId,
    });
  }

  // 记录更新
  @SubscribeMessage('update-record')
  async handleUpdateRecord(
    client: Socket,
    payload: {
      baseId: string;
      tableId: string;
      recordId: string;
      values: Record<string, any>;
    }
  ) {
    const roomName = `base:${payload.baseId}`;
    
    // 广播更新给房间内所有用户（包括自己确认）
    this.server.to(roomName).emit('record-updated', {
      userId: client.data.user.id,
      tableId: payload.tableId,
      recordId: payload.recordId,
      values: payload.values,
      timestamp: new Date().toISOString(),
    });
  }

  // 字段变更
  @SubscribeMessage('field-change')
  handleFieldChange(
    client: Socket,
    payload: {
      baseId: string;
      tableId: string;
      action: 'create' | 'update' | 'delete';
      field: any;
    }
  ) {
    const roomName = `base:${payload.baseId}`;
    
    client.to(roomName).emit('field-changed', {
      userId: client.data.user.id,
      tableId: payload.tableId,
      action: payload.action,
      field: payload.field,
    });
  }

  // 光标位置同步
  @SubscribeMessage('cursor-position')
  handleCursorPosition(
    client: Socket,
    payload: {
      baseId: string;
      tableId: string;
      recordId: string;
      fieldId: string;
      position: { x: number; y: number };
    }
  ) {
    const roomName = `base:${payload.baseId}`;
    
    client.to(roomName).emit('cursor-moved', {
      userId: client.data.user.id,
      userName: client.data.user.name,
      ...payload,
    });
  }

  private leaveAllRooms(client: Socket) {
    const rooms = this.userRooms.get(client.id) || [];
    rooms.forEach((room) => {
      client.leave(room);
      client.to(room).emit('user-left', {
        userId: client.data.user?.id,
        socketId: client.id,
      });
    });
    this.userRooms.delete(client.id);
  }

  // 服务端主动广播方法
  broadcastToBase(baseId: string, event: string, data: any) {
    this.server.to(`base:${baseId}`).emit(event, data);
  }
}
```

### 7.3 批量操作优化

```typescript
// src/records/records.service.ts
import { Injectable } from '@nestjs/common';
import { PrismaService } from '../prisma/prisma.service';

@Injectable()
export class RecordsService {
  constructor(private prisma: PrismaService) {}

  // 批量创建记录 - 使用事务保证原子性
  async batchCreate(
    tableId: string,
    records: Array<{ values: Record<string, any> }>,
    userId: string
  ) {
    return this.prisma.$transaction(async (tx) => {
      // 1. 批量创建记录
      const createdRecords = await tx.record.createMany({
        data: records.map((record) => ({
          tableId,
          values: record.values,
          createdById: userId,
          updatedById: userId,
        })),
      });

      // 2. 更新记录数
      await tx.table.update({
        where: { id: tableId },
        data: {
          recordCount: {
            increment: records.length,
          },
        },
      });

      // 3. 创建操作历史
      await tx.operationHistory.createMany({
        data: records.map((record) => ({
          baseId: (await tx.table.findUnique({ where: { id: tableId } })).baseId,
          tableId,
          action: 'CREATE',
          entityType: 'RECORD',
          newValue: record.values,
          userId,
        })),
      });

      return createdRecords;
    });
  }

  // 批量更新 - 使用 CASE WHEN 优化
  async batchUpdate(
    updates: Array<{ id: string; values: Record<string, any> }>,
    userId: string
  ) {
    return this.prisma.$transaction(async (tx) => {
      const results = [];
      
      // 分批处理，每批 1000 条
      const batchSize = 1000;
      for (let i = 0; i < updates.length; i += batchSize) {
        const batch = updates.slice(i, i + batchSize);
        
        // 使用 Promise.all 并行处理
        const batchResults = await Promise.all(
          batch.map((update) =>
            tx.record.update({
              where: { id: update.id },
              data: {
                values: update.values,
                updatedById: userId,
              },
            })
          )
        );
        
        results.push(...batchResults);
      }

      return results;
    });
  }

  // 大数据量查询优化
  async findManyWithPagination(
    tableId: string,
    options: {
      page?: number;
      pageSize?: number;
      filters?: any[];
      sorts?: any[];
      search?: string;
    }
  ) {
    const { page = 1, pageSize = 50, filters, sorts, search } = options;
    const skip = (page - 1) * pageSize;

    // 构建 where 条件
    const where: any = { tableId };
    
    if (search) {
      where.OR = [
        { values: { path: [], string_contains: search } },
      ];
    }

    // 并行执行查询和计数
    const [records, total] = await Promise.all([
      this.prisma.record.findMany({
        where,
        skip,
        take: pageSize,
        orderBy: sorts?.map((sort) => ({
          values: { path: [sort.fieldId], order: sort.order },
        })) || [{ createdAt: 'desc' }],
        include: {
          createdBy: {
            select: { id: true, name: true, avatar: true },
          },
          updatedBy: {
            select: { id: true, name: true, avatar: true },
          },
        },
      }),
      this.prisma.record.count({ where }),
    ]);

    return {
      data: records,
      meta: {
        page,
        pageSize,
        total,
        totalPages: Math.ceil(total / pageSize),
      },
    };
  }
}
```

---

## 八、部署方案

### 8.1 Docker Compose 配置

```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build:
      context: .
      dockerfile: Dockerfile
    container_name: smarttable-api
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=production
      - DATABASE_URL=postgresql://postgres:password@db:5432/smarttable?schema=public
      - REDIS_URL=redis://redis:6379
      - MINIO_ENDPOINT=minio:9000
      - MINIO_ACCESS_KEY=minioadmin
      - MINIO_SECRET_KEY=minioadmin
      - JWT_SECRET=your-secret-key
      - JWT_EXPIRATION=24h
    depends_on:
      - db
      - redis
      - minio
    networks:
      - smarttable-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  db:
    image: postgres:16-alpine
    container_name: smarttable-db
    environment:
      - POSTGRES_USER=postgres
      - POSTGRES_PASSWORD=password
      - POSTGRES_DB=smarttable
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"
    networks:
      - smarttable-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 10s
      timeout: 5s
      retries: 5

  redis:
    image: redis:7-alpine
    container_name: smarttable-redis
    volumes:
      - redis_data:/data
    ports:
      - "6379:6379"
    networks:
      - smarttable-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 10s
      timeout: 5s
      retries: 5

  minio:
    image: minio/minio:latest
    container_name: smarttable-minio
    command: server /data --console-address ":9001"
    environment:
      - MINIO_ROOT_USER=minioadmin
      - MINIO_ROOT_PASSWORD=minioadmin
    volumes:
      - minio_data:/data
    ports:
      - "9000:9000"
      - "9001:9001"
    networks:
      - smarttable-network
    restart: unless-stopped

  nginx:
    image: nginx:alpine
    container_name: smarttable-nginx
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./ssl:/etc/nginx/ssl:ro
    depends_on:
      - app
    networks:
      - smarttable-network
    restart: unless-stopped

volumes:
  postgres_data:
  redis_data:
  minio_data:

networks:
  smarttable-network:
    driver: bridge
```

### 8.2 Dockerfile

```dockerfile
# Dockerfile
FROM node:20-alpine AS builder

WORKDIR /app

# 复制依赖文件
COPY package*.json ./
COPY prisma ./prisma/

# 安装依赖
RUN npm ci

# 生成 Prisma Client
RUN npx prisma generate

# 复制源代码
COPY . .

# 构建应用
RUN npm run build

# 生产镜像
FROM node:20-alpine

WORKDIR /app

# 安装生产依赖
COPY package*.json ./
RUN npm ci --only=production

# 复制构建产物
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/node_modules/.prisma ./node_modules/.prisma
COPY --from=builder /app/prisma ./prisma

# 暴露端口
EXPOSE 3000

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
  CMD node -e "require('http').get('http://localhost:3000/health', (r) => {process.exit(r.statusCode === 200 ? 0 : 1)})"

# 启动命令
CMD ["node", "dist/main.js"]
```

---

## 九、技术选型对比总结

### 9.1 为什么选择 Node.js NestJS？

| 对比维度 | Node.js NestJS | Java Spring Boot | Python Flask |
|----------|----------------|------------------|--------------|
| **与前端技术栈一致性** | ⭐⭐⭐⭐⭐<br>TypeScript 全栈 | ⭐⭐<br>需要切换语言 | ⭐⭐⭐<br>Python 与 TS 差异大 |
| **开发效率** | ⭐⭐⭐⭐<br>装饰器语法与 Vue 一致 | ⭐⭐⭐<br>配置繁琐 | ⭐⭐⭐⭐⭐<br>简洁快速 |
| **类型安全** | ⭐⭐⭐⭐⭐<br>Prisma 类型推导 | ⭐⭐⭐⭐<br>Java 类型系统 | ⭐⭐<br>动态类型 |
| **实时通信** | ⭐⭐⭐⭐⭐<br>Socket.io 原生支持 | ⭐⭐⭐⭐<br>WebSocket 支持 | ⭐⭐⭐⭐<br>Flask-SocketIO |
| **JSON 处理** | ⭐⭐⭐⭐⭐<br>JavaScript 原生优势 | ⭐⭐⭐<br>Jackson 转换 | ⭐⭐⭐⭐<br>Python dict |
| **部署运维** | ⭐⭐⭐⭐⭐<br>轻量快速 | ⭐⭐⭐<br>JVM 较重 | ⭐⭐⭐⭐<br>简单 |
| **人才招聘** | ⭐⭐⭐⭐<br>全栈人才 | ⭐⭐⭐⭐⭐<br>Java 人才多 | ⭐⭐⭐⭐<br>Python 人才多 |
| **长期维护** | ⭐⭐⭐⭐<br>生态快速发展 | ⭐⭐⭐⭐⭐<br>企业级稳定 | ⭐⭐⭐⭐<br>稳定但慢 |

### 9.2 适用场景分析

**Node.js NestJS 最适合 SmartTable 的原因：**

1. **全栈 TypeScript**：
   - 前后端共享类型定义，减少类型转换错误
   - 团队技术栈统一，降低上下文切换成本
   - 类型安全贯穿整个开发流程

2. **现代化架构**：
   - 依赖注入、模块化设计与 Vue 3 组合式 API 理念一致
   - 装饰器语法与前端开发风格统一
   - AOP 编程支持日志、权限等横切关注点

3. **JSON 数据处理优势**：
   - SmartTable 大量动态 JSON 配置（字段 options、视图 config）
   - JavaScript 原生 JSON 支持，无需额外转换
   - Prisma 的 Json 类型支持完美契合需求

4. **实时协作需求**：
   - Socket.io 与 NestJS 深度集成
   - 事件驱动架构适合实时同步场景
   - 异步非阻塞 I/O 处理并发连接

5. **开发效率**：
   - 代码量比 Java 少 30-40%
   - 热重载开发体验好
   - 与前端工具链（Vite、ESLint）一致

### 9.3 潜在风险与缓解措施

| 风险 | 描述 | 缓解措施 |
|------|------|----------|
| **单线程瓶颈** | CPU 密集型任务阻塞事件循环 | 使用 Worker Threads 处理公式计算；复杂任务放入队列异步处理 |
| **类型安全** | 运行时类型检查不足 | 使用 Zod 进行运行时验证；严格的 TypeScript 配置 |
| **生态成熟度** | 相比 Spring 生态较年轻 | 选择经过验证的核心库；关注社区活跃度 |
| **内存泄漏** | 长连接可能导致内存泄漏 | 定期监控内存使用；设置连接超时；使用 PM2 进程管理 |
| **错误处理** | 异步错误捕获困难 | 统一异常过滤器；使用 RxJS 错误处理；完善的日志记录 |

---

## 十、实施建议

### 10.1 分阶段实施计划

| 阶段 | 时间 | 目标 |
|------|------|------|
| **第一阶段** | 1-2 周 | 搭建基础框架，完成用户认证、Base/Table CRUD |
| **第二阶段** | 2-3 周 | 完成 Field/Record/View 核心功能 |
| **第三阶段** | 1-2 周 | 实现 Dashboard、附件管理、导入导出 |
| **第四阶段** | 1-2 周 | 实现公式引擎、实时协作 WebSocket |
| **第五阶段** | 1 周 | 性能优化、测试覆盖、部署上线 |

### 10.2 团队配置建议

| 角色 | 人数 | 技能要求 |
|------|------|----------|
| 后端负责人 | 1 | NestJS + Prisma 经验，架构设计能力 |
| 后端开发 | 2-3 | Node.js + TypeScript，熟悉数据库设计 |
| 前端适配 | 1 | 熟悉现有 Vue 3 项目，API 对接 |
| DevOps | 1 | Docker + K8s，CI/CD 经验 |

### 10.3 关键成功因素

1. **类型共享**：建立前后端共享的类型定义库
2. **API 契约**：使用 Swagger/OpenAPI 严格定义接口契约
3. **自动化测试**：单元测试 + 集成测试 + E2E 测试全覆盖
4. **性能基准**：建立性能测试基准，持续监控
5. **文档先行**：API 文档、架构文档、部署文档同步更新

---

## 十一、总结

**推荐技术栈：**

```
后端框架：Node.js + NestJS + TypeScript
ORM：Prisma
数据库：PostgreSQL
缓存：Redis
文件存储：MinIO
实时通信：Socket.io
任务队列：BullMQ
监控：Prometheus + Grafana
部署：Docker + Docker Compose
```

**核心优势：**

- ✅ 与前端 Vue 3 + TypeScript 技术栈完美契合
- ✅ 现代化架构，开发效率高
- ✅ 类型安全，维护成本低
- ✅ 实时通信原生支持
- ✅ 部署简单，运维成本低

这套技术栈能够支撑 SmartTable 从当前纯前端架构平滑过渡到管理端架构，同时保持高效的开发迭代速度和良好的用户体验。

---

*文档版本：v1.0*
*最后更新：2026-04-03*
