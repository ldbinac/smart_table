# Flask 后端实施任务清单

## 阶段一：基础架构搭建

### 任务 1：项目初始化
- [ ] 1.1 创建项目目录结构
- [ ] 1.2 配置 Python 虚拟环境
- [ ] 1.3 创建 requirements.txt 依赖文件
- [ ] 1.4 配置 .env 环境变量
- [ ] 1.5 初始化 Git 仓库

### 任务 2：Flask 应用配置
- [ ] 2.1 创建 Flask 应用工厂函数
- [ ] 2.2 配置 SQLAlchemy 数据库连接
- [ ] 2.3 配置 Redis 缓存
- [ ] 2.4 配置 JWT 认证
- [ ] 2.5 配置 CORS 跨域
- [ ] 2.6 配置日志系统

### 任务 3：数据库模型设计
- [ ] 3.1 创建 User 模型
- [ ] 3.2 创建 Base 和 BaseMember 模型
- [ ] 3.3 创建 Table 模型
- [ ] 3.4 创建 Field 模型
- [ ] 3.5 创建 Record 模型
- [ ] 3.6 创建 View 模型
- [ ] 3.7 创建 Dashboard 模型
- [ ] 3.8 创建 Attachment 模型
- [ ] 3.9 创建 OperationHistory 模型
- [ ] 3.10 配置数据库索引

### 任务 4：数据库迁移
- [ ] 4.1 配置 Alembic 迁移工具
- [ ] 4.2 创建初始迁移脚本
- [ ] 4.3 编写数据库初始化脚本

---

## 阶段二：用户认证模块

### 任务 5：用户认证接口
- [ ] 5.1 实现用户注册接口 POST /api/auth/register
- [ ] 5.2 实现用户登录接口 POST /api/auth/login
- [ ] 5.3 实现 Token 刷新接口 POST /api/auth/refresh
- [ ] 5.4 实现退出登录接口 POST /api/auth/logout
- [ ] 5.5 实现获取当前用户接口 GET /api/auth/me

### 任务 6：用户服务层
- [ ] 6.1 实现用户注册业务逻辑
- [ ] 6.2 实现密码加密和验证
- [ ] 6.3 实现 JWT Token 生成和验证
- [ ] 6.4 实现登录失败次数限制
- [ ] 6.5 编写单元测试

### 任务 7：用户数据验证
- [ ] 7.1 创建 Marshmallow 用户 Schema
- [ ] 7.2 实现邮箱格式验证
- [ ] 7.3 实现密码强度验证
- [ ] 7.4 实现唯一性检查

---

## 阶段三：Base 管理模块

### 任务 8：Base CRUD 接口
- [ ] 8.1 实现获取所有 Base 接口 GET /api/bases
- [ ] 8.2 实现创建 Base 接口 POST /api/bases
- [ ] 8.3 实现获取单个 Base 接口 GET /api/bases/:id
- [ ] 8.4 实现更新 Base 接口 PUT /api/bases/:id
- [ ] 8.5 实现删除 Base 接口 DELETE /api/bases/:id
- [ ] 8.6 实现收藏/取消收藏接口 POST /api/bases/:id/star

### 任务 9：Base 成员管理
- [ ] 9.1 实现获取成员列表接口 GET /api/bases/:id/members
- [ ] 9.2 实现添加成员接口 POST /api/bases/:id/members
- [ ] 9.3 实现移除成员接口 DELETE /api/bases/:id/members/:userId
- [ ] 9.4 实现权限检查装饰器

### 任务 10：Base 服务层
- [ ] 10.1 实现 Base CRUD 业务逻辑
- [ ] 10.2 实现级联删除逻辑
- [ ] 10.3 实现权限验证逻辑
- [ ] 10.4 编写单元测试

---

## 阶段四：Table 管理模块

### 任务 11：Table CRUD 接口
- [ ] 11.1 实现获取所有 Table 接口 GET /api/bases/:baseId/tables
- [ ] 11.2 实现创建 Table 接口 POST /api/bases/:baseId/tables
- [ ] 11.3 实现获取单个 Table 接口 GET /api/tables/:id
- [ ] 11.4 实现更新 Table 接口 PUT /api/tables/:id
- [ ] 11.5 实现删除 Table 接口 DELETE /api/tables/:id
- [ ] 11.6 实现批量排序接口 POST /api/bases/:baseId/tables/reorder

### 任务 12：Table 服务层
- [ ] 12.1 实现 Table CRUD 业务逻辑
- [ ] 12.2 实现记录数统计更新
- [ ] 12.3 实现主字段自动设置
- [ ] 12.4 编写单元测试

---

## 阶段五：Field 管理模块

### 任务 13：Field CRUD 接口
- [ ] 13.1 实现获取所有 Field 接口 GET /api/tables/:tableId/fields
- [ ] 13.2 实现创建 Field 接口 POST /api/tables/:tableId/fields
- [ ] 13.3 实现更新 Field 接口 PUT /api/fields/:id
- [ ] 13.4 实现删除 Field 接口 DELETE /api/fields/:id
- [ ] 13.5 实现批量排序接口 POST /api/fields/reorder

### 任务 14：Field 服务层
- [ ] 14.1 实现 Field CRUD 业务逻辑
- [ ] 14.2 实现 22 种字段类型创建逻辑
- [ ] 14.3 实现字段选项验证
- [ ] 14.4 实现系统字段保护
- [ ] 14.5 编写单元测试

---

## 阶段六：Record 管理模块

### 任务 15：Record CRUD 接口
- [ ] 15.1 实现获取所有 Record 接口 GET /api/tables/:tableId/records
- [ ] 15.2 实现创建 Record 接口 POST /api/tables/:tableId/records
- [ ] 15.3 实现获取单个 Record 接口 GET /api/records/:id
- [ ] 15.4 实现更新 Record 接口 PUT /api/records/:id
- [ ] 15.5 实现删除 Record 接口 DELETE /api/records/:id

### 任务 16：Record 批量操作
- [ ] 16.1 实现批量创建接口 POST /api/tables/:tableId/records/batch
- [ ] 16.2 实现批量更新接口 PUT /api/records/batch
- [ ] 16.3 实现批量删除接口 DELETE /api/records/batch

### 任务 17：Record 高级查询
- [ ] 17.1 实现分页查询功能
- [ ] 17.2 实现多字段筛选功能
- [ ] 17.3 实现多字段排序功能
- [ ] 17.4 实现全文搜索功能

### 任务 18：Record 服务层
- [ ] 18.1 实现 Record CRUD 业务逻辑
- [ ] 18.2 实现必填字段验证
- [ ] 18.3 实现字段类型验证
- [ ] 18.4 实现自动编号生成
- [ ] 18.5 实现创建人/更新人自动填充
- [ ] 18.6 编写单元测试

---

## 阶段七：View 管理模块

### 任务 19：View CRUD 接口
- [ ] 19.1 实现获取所有 View 接口 GET /api/tables/:tableId/views
- [ ] 19.2 实现创建 View 接口 POST /api/tables/:tableId/views
- [ ] 19.3 实现获取单个 View 接口 GET /api/views/:id
- [ ] 19.4 实现更新 View 接口 PUT /api/views/:id
- [ ] 19.5 实现删除 View 接口 DELETE /api/views/:id
- [ ] 19.6 实现设置默认视图接口 POST /api/views/:id/set-default

### 任务 20：View 服务层
- [ ] 20.1 实现 View CRUD 业务逻辑
- [ ] 20.2 实现 6 种视图类型配置
- [ ] 20.3 实现视图筛选/排序/分组逻辑
- [ ] 20.4 编写单元测试

---

## 阶段八：Dashboard 管理模块

### 任务 21：Dashboard CRUD 接口
- [ ] 21.1 实现获取所有 Dashboard 接口 GET /api/bases/:baseId/dashboards
- [ ] 21.2 实现创建 Dashboard 接口 POST /api/bases/:baseId/dashboards
- [ ] 21.3 实现获取单个 Dashboard 接口 GET /api/dashboards/:id
- [ ] 21.4 实现更新 Dashboard 接口 PUT /api/dashboards/:id
- [ ] 21.5 实现删除 Dashboard 接口 DELETE /api/dashboards/:id

### 任务 22：Dashboard 服务层
- [ ] 22.1 实现 Dashboard CRUD 业务逻辑
- [ ] 22.2 实现 Widget 管理逻辑
- [ ] 22.3 实现布局管理逻辑
- [ ] 22.4 编写单元测试

---

## 阶段九：附件管理模块

### 任务 23：文件上传接口
- [ ] 23.1 实现单文件上传接口 POST /api/attachments/upload
- [ ] 23.2 实现批量文件上传接口
- [ ] 23.3 实现分片上传接口

### 任务 24：文件管理接口
- [ ] 24.1 实现获取文件信息接口 GET /api/attachments/:id
- [ ] 24.2 实现文件下载接口 GET /api/attachments/:id/download
- [ ] 24.3 实现删除文件接口 DELETE /api/attachments/:id

### 任务 25：文件服务层
- [ ] 25.1 集成 MinIO 对象存储
- [ ] 25.2 实现文件上传业务逻辑
- [ ] 25.3 实现缩略图生成逻辑
- [ ] 25.4 实现文件清理逻辑
- [ ] 25.5 编写单元测试

---

## 阶段十：导入导出模块

### 任务 26：数据导入
- [ ] 26.1 实现 Excel 导入接口 POST /api/import
- [ ] 26.2 实现 CSV 导入接口
- [ ] 26.3 实现 JSON 导入接口
- [ ] 26.4 实现导入预览功能
- [ ] 26.5 实现字段映射功能

### 任务 27：数据导出
- [ ] 27.1 实现 Excel 导出接口 POST /api/export
- [ ] 27.2 实现 CSV 导出接口
- [ ] 27.3 实现 JSON 导出接口
- [ ] 27.4 实现导出进度查询接口

### 任务 28：导入导出服务
- [ ] 28.1 实现 Excel 读写逻辑（openpyxl）
- [ ] 28.2 实现 CSV 读写逻辑（pandas）
- [ ] 28.3 实现 Celery 异步任务
- [ ] 28.4 编写单元测试

---

## 阶段十一：公式引擎

### 任务 29：公式计算服务
- [ ] 29.1 实现公式解析器
- [ ] 29.2 实现数学函数（SUM、AVG、MAX、MIN 等）
- [ ] 29.3 实现文本函数（CONCAT、UPPER、LOWER 等）
- [ ] 29.4 实现日期函数（YEAR、MONTH、DAY 等）
- [ ] 29.5 实现逻辑函数（IF、AND、OR 等）
- [ ] 29.6 实现统计函数（COUNT、COUNTA 等）

### 任务 30：公式应用
- [ ] 30.1 实现 Record 保存时公式计算
- [ ] 30.2 实现批量公式重算
- [ ] 30.3 实现公式缓存
- [ ] 30.4 编写单元测试

---

## 阶段十二：前端对接

### 任务 31：前端 API 客户端
- [ ] 31.1 安装并配置 Axios
- [ ] 31.2 创建 API 客户端实例
- [ ] 31.3 实现请求拦截器（Token）
- [ ] 31.4 实现响应拦截器（错误处理）

### 任务 32：API 类型定义
- [ ] 32.1 创建 API 响应类型
- [ ] 32.2 创建请求 DTO 类型
- [ ] 32.3 确保前后端类型一致性

### 任务 33：前端 Service 层改造
- [ ] 33.1 修改 baseStore.ts 调用 API
- [ ] 33.2 修改 tableStore.ts 调用 API
- [ ] 33.3 修改 fieldStore.ts 调用 API
- [ ] 33.4 修改 recordStore.ts 调用 API
- [ ] 33.5 修改 viewStore.ts 调用 API

### 任务 34：离线缓存（可选）
- [ ] 34.1 保留 Dexie 作为离线缓存
- [ ] 34.2 实现数据同步策略
- [ ] 34.3 实现冲突解决

---

## 阶段十三：测试与部署

### 任务 35：单元测试
- [ ] 35.1 配置 pytest 测试框架
- [ ] 35.2 编写 Service 层单元测试
- [ ] 35.3 编写验证器单元测试
- [ ] 35.4 达到 80% 以上覆盖率

### 任务 36：集成测试
- [ ] 36.1 编写 API 接口测试
- [ ] 36.2 编写数据库操作测试
- [ ] 36.3 编写认证流程测试

### 任务 37：性能测试
- [ ] 37.1 编写 API 性能基准测试
- [ ] 37.2 测试大数据量场景
- [ ] 37.3 测试并发场景

### 任务 38：部署配置
- [ ] 38.1 编写 Dockerfile
- [ ] 38.2 编写 docker-compose.yml
- [ ] 38.3 编写 Nginx 配置文件
- [ ] 38.4 配置生产环境变量

### 任务 39：部署上线
- [ ] 39.1 配置 CI/CD 流水线
- [ ] 39.2 执行数据库迁移
- [ ] 39.3 部署到生产环境
- [ ] 39.4 监控系统运行状态

---

## 任务依赖关系

```
阶段一：基础架构
├── 1.1-1.5 项目初始化
├── 2.1-2.6 Flask 应用配置
├── 3.1-3.10 数据库模型设计
└── 4.1-4.3 数据库迁移
    │
    ▼
阶段二：用户认证
├── 5.1-5.5 用户认证接口
├── 6.1-6.5 用户服务层
└── 7.1-7.4 用户数据验证
    │
    ▼
阶段三：Base 管理
├── 8.1-8.6 Base CRUD 接口
├── 9.1-9.4 Base 成员管理
└── 10.1-10.4 Base 服务层
    │
    ▼
阶段四：Table 管理
├── 11.1-11.6 Table CRUD 接口
└── 12.1-12.4 Table 服务层
    │
    ▼
阶段五：Field 管理
├── 13.1-13.5 Field CRUD 接口
└── 14.1-14.5 Field 服务层
    │
    ▼
阶段六：Record 管理
├── 15.1-15.5 Record CRUD 接口
├── 16.1-16.3 Record 批量操作
├── 17.1-17.4 Record 高级查询
└── 18.1-18.6 Record 服务层
    │
    ▼
阶段七：View 管理
├── 19.1-19.6 View CRUD 接口
└── 20.1-20.4 View 服务层
    │
    ▼
阶段八：Dashboard 管理
├── 21.1-21.5 Dashboard CRUD 接口
└── 22.1-22.4 Dashboard 服务层
    │
    ▼
阶段九：附件管理
├── 23.1-23.3 文件上传接口
├── 24.1-24.3 文件管理接口
└── 25.1-25.5 文件服务层
    │
    ▼
阶段十：导入导出
├── 26.1-26.5 数据导入
├── 27.1-27.4 数据导出
└── 28.1-28.4 导入导出服务
    │
    ▼
阶段十一：公式引擎
├── 29.1-29.6 公式计算服务
└── 30.1-30.4 公式应用
    │
    ▼
阶段十二：前端对接
├── 31.1-31.4 前端 API 客户端
├── 32.1-32.3 API 类型定义
├── 33.1-33.5 前端 Service 层改造
└── 34.1-34.4 离线缓存（可选）
    │
    ▼
阶段十三：测试与部署
├── 35.1-35.4 单元测试
├── 36.1-36.3 集成测试
├── 37.1-37.3 性能测试
├── 38.1-38.4 部署配置
└── 39.1-39.4 部署上线
```

---

## 里程碑

| 阶段 | 工期 | 交付物 | 验收标准 |
|------|------|--------|----------|
| 阶段一 | 1 周 | Flask 基础框架、数据库模型 | 应用可运行，数据库连接正常 |
| 阶段二 | 0.5 周 | 用户认证模块 | 注册、登录、Token 正常 |
| 阶段三 | 0.5 周 | Base 管理模块 | Base CRUD 和成员管理正常 |
| 阶段四 | 0.5 周 | Table 管理模块 | Table CRUD 正常 |
| 阶段五 | 0.5 周 | Field 管理模块 | 22 种字段类型创建正常 |
| 阶段六 | 1 周 | Record 管理模块 | Record CRUD 和批量操作正常 |
| 阶段七 | 0.5 周 | View 管理模块 | 6 种视图类型正常 |
| 阶段八 | 0.5 周 | Dashboard 管理模块 | Dashboard CRUD 正常 |
| 阶段九 | 0.5 周 | 附件管理模块 | 文件上传下载正常 |
| 阶段十 | 0.5 周 | 导入导出模块 | Excel/CSV 导入导出正常 |
| 阶段十一 | 0.5 周 | 公式引擎 | 40+ 函数计算正常 |
| 阶段十二 | 0.5 周 | 前端对接 | 前端功能正常调用 API |
| 阶段十三 | 0.5 周 | 测试与部署 | 测试通过，成功上线 |

**总计预计工期：7 周**
