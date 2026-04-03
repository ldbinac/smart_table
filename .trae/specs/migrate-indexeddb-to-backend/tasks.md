# 数据存储迁移任务清单

## 任务总览

本文档详细规划了将 SmartTable 从 IndexedDB 本地存储迁移到管理端数据库的完整任务清单。

---

## 阶段一：技术准备与架构设计

### 任务 1：后端技术栈搭建
- [ ] 1.1 初始化 NestJS 项目
  - [ ] 安装 NestJS CLI 并创建项目
  - [ ] 配置 TypeScript 严格模式
  - [ ] 设置 ESLint + Prettier 代码规范
  - [ ] 配置环境变量管理（@nestjs/config）

- [ ] 1.2 数据库环境搭建
  - [ ] 安装并配置 PostgreSQL（本地开发环境）
  - [ ] 安装并配置 Redis（本地开发环境）
  - [ ] 配置 Docker Compose 一键启动开发环境
  - [ ] 创建数据库初始化脚本

- [ ] 1.3 Prisma ORM 集成
  - [ ] 安装 Prisma 并初始化
  - [ ] 根据现有 IndexedDB Schema 设计 Prisma Schema
  - [ ] 创建数据库迁移脚本
  - [ ] 生成 Prisma Client 类型定义

- [ ] 1.4 基础模块搭建
  - [ ] 创建用户认证模块（JWT + Passport）
  - [ ] 配置全局异常过滤器
  - [ ] 配置全局响应拦截器（统一响应格式）
  - [ ] 配置日志系统
  - [ ] 集成 Swagger API 文档

---

## 阶段二：后端核心业务实现

### 任务 2：Base 管理模块
- [ ] 2.1 Base 实体与接口定义
  - [ ] 创建 Base Prisma Model
  - [ ] 定义 Base DTO（CreateBaseDto, UpdateBaseDto）
  - [ ] 定义 Base 响应类型

- [ ] 2.2 Base CRUD 接口实现
  - [ ] 实现 POST /bases 创建 Base
  - [ ] 实现 GET /bases 获取所有 Base（支持分页）
  - [ ] 实现 GET /bases/:id 获取单个 Base
  - [ ] 实现 PATCH /bases/:id 更新 Base
  - [ ] 实现 DELETE /bases/:id 删除 Base
  - [ ] 实现 POST /bases/:id/toggle-star 切换收藏状态

- [ ] 2.3 Base 业务逻辑
  - [ ] 实现 Base 数据验证
  - [ ] 实现用户权限检查（只能操作自己的 Base）
  - [ ] 实现删除 Base 时的级联删除逻辑

### 任务 3：Table 管理模块
- [ ] 3.1 Table 实体与接口定义
  - [ ] 创建 Table Prisma Model
  - [ ] 定义 Table DTO
  - [ ] 定义 Table 响应类型

- [ ] 3.2 Table CRUD 接口实现
  - [ ] 实现 POST /bases/:baseId/tables 创建 Table
  - [ ] 实现 GET /bases/:baseId/tables 获取 Base 下的所有 Table
  - [ ] 实现 GET /tables/:id 获取单个 Table
  - [ ] 实现 PATCH /tables/:id 更新 Table
  - [ ] 实现 DELETE /tables/:id 删除 Table

- [ ] 3.3 Table 业务逻辑
  - [ ] 实现 Table 排序功能
  - [ ] 实现记录数统计更新
  - [ ] 实现主字段自动设置逻辑

### 任务 4：Field 管理模块
- [ ] 4.1 Field 实体与接口定义
  - [ ] 创建 Field Prisma Model
  - [ ] 定义 Field DTO（支持 22 种字段类型配置）
  - [ ] 定义 Field 响应类型

- [ ] 4.2 Field CRUD 接口实现
  - [ ] 实现 POST /tables/:tableId/fields 创建 Field
  - [ ] 实现 GET /tables/:tableId/fields 获取所有 Field
  - [ ] 实现 PATCH /fields/:id 更新 Field
  - [ ] 实现 DELETE /fields/:id 删除 Field
  - [ ] 实现 POST /fields/reorder 字段排序

- [ ] 4.3 Field 业务逻辑
  - [ ] 实现字段类型验证
  - [ ] 实现系统字段保护（禁止删除系统字段）
  - [ ] 实现字段选项验证（单选/多选字段）

### 任务 5：Record 管理模块
- [ ] 5.1 Record 实体与接口定义
  - [ ] 创建 Record Prisma Model
  - [ ] 定义 Record DTO
  - [ ] 定义 Record 响应类型

- [ ] 5.2 Record CRUD 接口实现
  - [ ] 实现 POST /tables/:tableId/records 创建 Record
  - [ ] 实现 GET /tables/:tableId/records 获取所有 Record（支持分页）
  - [ ] 实现 GET /records/:id 获取单个 Record
  - [ ] 实现 PATCH /records/:id 更新 Record
  - [ ] 实现 DELETE /records/:id 删除 Record

- [ ] 5.3 Record 批量操作接口
  - [ ] 实现 POST /tables/:tableId/records/batch-create 批量创建
  - [ ] 实现 PATCH /records/batch-update 批量更新
  - [ ] 实现 DELETE /records/batch-delete 批量删除

- [ ] 5.4 Record 业务逻辑
  - [ ] 实现字段值验证
  - [ ] 实现必填字段检查
  - [ ] 实现自动编号字段生成
  - [ ] 实现创建人/更新人自动填充

### 任务 6：View 管理模块
- [ ] 6.1 View 实体与接口定义
  - [ ] 创建 View Prisma Model
  - [ ] 定义 View DTO（支持 6 种视图类型配置）
  - [ ] 定义 View 响应类型

- [ ] 6.2 View CRUD 接口实现
  - [ ] 实现 POST /tables/:tableId/views 创建 View
  - [ ] 实现 GET /tables/:tableId/views 获取所有 View
  - [ ] 实现 GET /views/:id 获取单个 View
  - [ ] 实现 PATCH /views/:id 更新 View
  - [ ] 实现 DELETE /views/:id 删除 View
  - [ ] 实现 POST /views/:id/set-default 设置默认视图

### 任务 7：Dashboard 管理模块
- [ ] 7.1 Dashboard 实体与接口定义
  - [ ] 创建 Dashboard Prisma Model
  - [ ] 定义 Dashboard DTO
  - [ ] 定义 Widget 配置类型

- [ ] 7.2 Dashboard CRUD 接口实现
  - [ ] 实现 Dashboard 的增删改查接口
  - [ ] 实现 Dashboard 布局保存接口
  - [ ] 实现 Dashboard 刷新配置接口

### 任务 8：附件管理模块
- [ ] 8.1 文件存储方案实现
  - [ ] 集成 MinIO 或 AWS S3 对象存储
  - [ ] 实现文件上传接口（支持分片上传）
  - [ ] 实现文件下载接口
  - [ ] 实现缩略图生成（图片文件）

- [ ] 8.2 附件元数据管理
  - [ ] 创建 Attachment Prisma Model
  - [ ] 实现附件元数据 CRUD
  - [ ] 实现附件与记录的关联管理

---

## 阶段三：前端改造与适配

### 任务 9：前端 API 基础设施
- [ ] 9.1 HTTP 客户端封装
  - [ ] 安装并配置 Axios
  - [ ] 创建 API Client 实例
  - [ ] 实现请求拦截器（添加 Token）
  - [ ] 实现响应拦截器（统一错误处理）
  - [ ] 实现 Token 过期自动刷新

- [ ] 9.2 TanStack Query 集成
  - [ ] 安装 @tanstack/vue-query
  - [ ] 配置 Query Client
  - [ ] 创建全局 Query Provider
  - [ ] 配置默认缓存策略

- [ ] 9.3 类型定义同步
  - [ ] 创建 API 响应类型定义
  - [ ] 创建请求 DTO 类型定义
  - [ ] 确保前后端类型一致性

### 任务 10：Service 层改造
- [ ] 10.1 创建 API Service 实现
  - [ ] 创建 api/baseService.ts 调用后端 API
  - [ ] 创建 api/tableService.ts 调用后端 API
  - [ ] 创建 api/fieldService.ts 调用后端 API
  - [ ] 创建 api/recordService.ts 调用后端 API
  - [ ] 创建 api/viewService.ts 调用后端 API

- [ ] 10.2 Service 层抽象
  - [ ] 定义 StorageAdapter 接口
  - [ ] 重构现有 Service 实现接口
  - [ ] 创建 DualWriteStorage 双写实现

### 任务 11：Store 层改造
- [ ] 11.1 创建 Composables
  - [ ] 创建 useBases.ts（使用 TanStack Query）
  - [ ] 创建 useTables.ts
  - [ ] 创建 useFields.ts
  - [ ] 创建 useRecords.ts
  - [ ] 创建 useViews.ts

- [ ] 11.2 改造现有 Pinia Store
  - [ ] 修改 baseStore.ts 使用新的 Service
  - [ ] 修改 tableStore.ts 使用新的 Service
  - [ ] 修改 viewStore.ts 使用新的 Service
  - [ ] 保持 Store 接口不变，仅替换实现

### 任务 12：离线缓存实现
- [ ] 12.1 Dexie 缓存策略
  - [ ] 保留 Dexie 作为本地缓存
  - [ ] 实现数据同步策略
  - [ ] 实现离线队列管理

- [ ] 12.2 同步机制
  - [ ] 实现网络状态检测
  - [ ] 实现在线/离线状态切换处理
  - [ ] 实现待同步数据队列
  - [ ] 实现冲突解决策略

---

## 阶段四：数据迁移与测试

### 任务 13：数据迁移工具
- [ ] 13.1 迁移脚本开发
  - [ ] 创建 IndexedDB 数据导出工具
  - [ ] 创建数据格式转换工具
  - [ ] 创建批量导入 API

- [ ] 13.2 迁移流程
  - [ ] 设计用户数据迁移流程
  - [ ] 实现迁移进度显示
  - [ ] 实现迁移回滚机制

### 任务 14：测试覆盖
- [ ] 14.1 后端测试
  - [ ] 编写单元测试（Service 层）
  - [ ] 编写集成测试（Controller 层）
  - [ ] 编写 E2E 测试（完整流程）
  - [ ] 达到 80% 以上测试覆盖率

- [ ] 14.2 前端测试
  - [ ] 编写 Composables 测试
  - [ ] 编写 Service 层测试
  - [ ] 更新组件测试

- [ ] 14.3 性能测试
  - [ ] 后端 API 性能基准测试
  - [ ] 前端加载性能测试
  - [ ] 大数据量下性能测试

---

## 阶段五：部署与上线

### 任务 15：部署准备
- [ ] 15.1 后端部署
  - [ ] 编写 Dockerfile
  - [ ] 编写 docker-compose.prod.yml
  - [ ] 配置 CI/CD 流水线（GitHub Actions）
  - [ ] 配置生产环境数据库迁移

- [ ] 15.2 前端部署
  - [ ] 配置生产环境 API 地址
  - [ ] 配置 CDN 部署
  - [ ] 配置环境变量注入

### 任务 16：上线切换
- [ ] 16.1 灰度发布
  - [ ] 配置特性开关（Feature Flag）
  - [ ] 实现渐进式迁移策略
  - [ ] 监控关键指标

- [ ] 16.2 回滚预案
  - [ ] 准备回滚方案
  - [ ] 备份策略确认
  - [ ] 应急响应流程

---

## 任务依赖关系

```
阶段一
├── 1.1 初始化 NestJS 项目
├── 1.2 数据库环境搭建
├── 1.3 Prisma ORM 集成
└── 1.4 基础模块搭建
    │
    ▼
阶段二
├── 2.1-2.3 Base 模块
├── 3.1-3.3 Table 模块
├── 4.1-4.3 Field 模块
├── 5.1-5.4 Record 模块
├── 6.1-6.2 View 模块
├── 7.1-7.2 Dashboard 模块
└── 8.1-8.2 附件模块
    │
    ▼
阶段三
├── 9.1-9.3 API 基础设施
├── 10.1-10.2 Service 改造
├── 11.1-11.2 Store 改造
└── 12.1-12.2 离线缓存
    │
    ▼
阶段四
├── 13.1-13.2 数据迁移
└── 14.1-14.3 测试覆盖
    │
    ▼
阶段五
├── 15.1-15.2 部署准备
└── 16.1-16.2 上线切换
```

---

## 里程碑

| 阶段 | 预计工期 | 交付物 | 验收标准 |
|------|----------|--------|----------|
| 阶段一 | 1 周 | 后端基础框架 | 可运行的 NestJS 项目，Swagger 文档正常 |
| 阶段二 | 3 周 | 完整后端 API | 所有 CRUD 接口通过测试，API 文档完整 |
| 阶段三 | 2 周 | 前端改造完成 | 前端可正常调用后端 API，功能无损 |
| 阶段四 | 1 周 | 测试通过 | 测试覆盖率达标，性能测试通过 |
| 阶段五 | 1 周 | 正式上线 | 生产环境稳定运行，监控正常 |

**总计预计工期：8 周**
