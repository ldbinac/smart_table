# SmartTable Java 后端技术栈选型建议

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
| **并发处理** | 支持多用户同时操作，高并发场景 |
| **API 设计** | RESTful API，支持批量操作 |
| **实时通信** | WebSocket 支持实时协作 |
| **文件存储** | 对象存储集成 |
| **性能要求** | 单表支持 10万+ 记录，查询 < 200ms |
| **扩展性** | 支持微服务拆分 |

---

## 二、推荐技术栈方案

### 2.1 最终推荐：Spring Boot 3.x + MyBatis-Plus + PostgreSQL

**推荐理由：**

1. ✅ **企业级稳定性** - Spring 生态最成熟，大量生产环境验证
2. ✅ **强事务支持** - 完善的事务管理机制，ACID 保证
3. ✅ **高性能** - JVM 优化成熟，高并发处理能力强
4. ✅ **生态完善** - Spring Security、Spring Data、Spring Cloud 等全家桶
5. ✅ **长期维护** - 企业级支持，版本升级路径清晰
6. ✅ **人才充足** - Java 开发者市场最大，招聘容易

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
│                            网关层 (Spring Cloud Gateway)                 │
│  ┌─────────────────────────────────────────────────────────────────┐   │
│  │  负载均衡 │ 限流熔断 │ 路由转发 │ 认证鉴权                          │   │
│  └─────────────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           应用层 (Spring Boot)                           │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │  Controller │  │   Service   │  │   Security  │  │  AOP/Aspect │    │
│  │   控制层    │  │   业务层    │  │   安全控制  │  │  日志/事务  │    │
│  └──────┬──────┘  └──────┬──────┘  └─────────────┘  └─────────────┘    │
│         │                │                                              │
│  ┌──────▼────────────────▼──────┐  ┌─────────────────────────────┐     │
│  │      Mapper (MyBatis-Plus)   │  │      WebSocket Handler      │     │
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
│ • Field/Record  │      │ • 分布式锁       │      │ • 缩略图         │
│ • View/Dashboard│      │ • 消息队列       │      │ • 备份文件       │
│ • User/Auth     │      │ • 会话存储       │      │                 │
└─────────────────┘      └─────────────────┘      └─────────────────┘
```

---

### 3.2 后端技术组件清单

#### 核心框架

| 组件 | 技术选型 | 版本 | 用途 |
|------|----------|------|------|
| 基础框架 | Spring Boot | 3.2.x | 核心应用框架 |
| JDK 版本 | Java | 21 LTS | 长期支持版本 |
| 构建工具 | Maven | 3.9.x | 依赖管理和构建 |

#### Web 层

| 组件 | 技术选型 | 版本 | 用途 |
|------|----------|------|------|
| Web 框架 | Spring Web MVC | 6.1.x | RESTful API 开发 |
| 响应式 Web | Spring WebFlux | 6.1.x | 可选，高并发场景 |
| 验证框架 | Spring Validation | 3.2.x | 参数校验 |
| JSON 处理 | Jackson | 2.16.x | JSON 序列化/反序列化 |

#### 数据访问层

| 组件 | 技术选型 | 版本 | 用途 |
|------|----------|------|------|
| ORM 框架 | MyBatis-Plus | 3.5.x | 增强型 MyBatis |
| 数据库连接池 | HikariCP | 5.1.x | 高性能连接池 |
| 数据库 | PostgreSQL | 16.x | 主数据库 |
| 缓存框架 | Spring Data Redis | 3.2.x | Redis 集成 |
| Redis 客户端 | Lettuce | 6.3.x | 响应式 Redis 客户端 |
| 分布式锁 | Redisson | 3.25.x | 分布式锁实现 |

#### 安全认证

| 组件 | 技术选型 | 版本 | 用途 |
|------|----------|------|------|
| 安全框架 | Spring Security | 6.2.x | 认证授权 |
| JWT 支持 | jjwt | 0.12.x | JWT Token 生成验证 |
| OAuth2 | Spring Security OAuth2 | 6.2.x | OAuth2 支持 |
| 密码加密 | BCrypt | 内置 | 密码哈希 |

#### 实时通信

| 组件 | 技术选型 | 版本 | 用途 |
|------|----------|------|------|
| WebSocket | Spring WebSocket | 6.1.x | WebSocket 支持 |
| STOMP 协议 | Spring Messaging | 6.1.x | 消息协议 |
| SockJS | Spring SockJS | 6.1.x | WebSocket 降级方案 |

#### 任务调度

| 组件 | 技术选型 | 版本 | 用途 |
|------|----------|------|------|
| 定时任务 | Spring Scheduler | 3.2.x | 本地定时任务 |
| 分布式任务 | XXL-Job | 2.4.x | 分布式任务调度 |
| 异步处理 | Spring Async | 3.2.x | 异步方法支持 |
| 消息队列 | RabbitMQ | 3.12.x | 消息中间件 |
| MQ 集成 | Spring AMQP | 3.2.x | RabbitMQ 集成 |

#### 文件处理

| 组件 | 技术选型 | 版本 | 用途 |
|------|----------|------|------|
| 对象存储 | MinIO | 最新 | 文件存储 |
| MinIO SDK | minio-java | 8.5.x | MinIO 客户端 |
| 文件上传 | Apache Commons FileUpload | 1.5.x | 文件上传处理 |
| Excel 处理 | EasyExcel | 3.3.x | 阿里巴巴 Excel 工具 |
| 图片处理 | Thumbnailator | 0.4.x | 缩略图生成 |

#### 监控运维

| 组件 | 技术选型 | 版本 | 用途 |
|------|----------|------|------|
| 健康检查 | Spring Boot Actuator | 3.2.x | 应用监控端点 |
| 指标监控 | Micrometer | 1.12.x | 指标收集 |
| Prometheus | micrometer-registry-prometheus | 1.12.x | Prometheus 集成 |
| 链路追踪 | Micrometer Tracing | 1.2.x | 分布式追踪 |
| 日志框架 | SLF4J + Logback | 2.0.x | 日志记录 |
| 分布式日志 | ELK Stack | 8.x | 日志收集分析 |

#### API 文档

| 组件 | 技术选型 | 版本 | 用途 |
|------|----------|------|------|
| OpenAPI | SpringDoc OpenAPI | 2.3.x | API 文档生成 |
| Swagger UI | springdoc-openapi-ui | 2.3.x | 文档界面 |

#### 测试

| 组件 | 技术选型 | 版本 | 用途 |
|------|----------|------|------|
| 单元测试 | JUnit 5 | 5.10.x | 测试框架 |
| 模拟框架 | Mockito | 5.8.x | 模拟对象 |
| 集成测试 | Spring Boot Test | 3.2.x | 集成测试支持 |
| API 测试 | REST Assured | 5.4.x | API 测试 |

---

## 四、项目目录结构

### 4.1 后端项目结构

```
smarttable-backend/
├── src/
│   ├── main/
│   │   ├── java/
│   │   │   └── com/
│   │   │       └── smarttable/
│   │   │           ├── SmartTableApplication.java    # 应用入口
│   │   │           ├── config/                       # 配置类
│   │   │           │   ├── MybatisPlusConfig.java
│   │   │           │   ├── RedisConfig.java
│   │   │           │   ├── SecurityConfig.java
│   │   │           │   ├── WebSocketConfig.java
│   │   │           │   ├── MinioConfig.java
│   │   │           │   └── RabbitMQConfig.java
│   │   │           ├── common/                       # 公共模块
│   │   │           │   ├── constants/                # 常量定义
│   │   │           │   ├── enums/                    # 枚举类
│   │   │           │   ├── exception/                # 异常处理
│   │   │           │   ├── result/                   # 统一响应
│   │   │           │   ├── utils/                    # 工具类
│   │   │           │   └── aspect/                   # AOP 切面
│   │   │           ├── entity/                       # 实体类
│   │   │           │   ├── Base.java
│   │   │           │   ├── Table.java
│   │   │           │   ├── Field.java
│   │   │           │   ├── Record.java
│   │   │           │   ├── View.java
│   │   │           │   ├── Dashboard.java
│   │   │           │   ├── Attachment.java
│   │   │           │   ├── User.java
│   │   │           │   └── OperationHistory.java
│   │   │           ├── mapper/                       # MyBatis Mapper
│   │   │           │   ├── BaseMapper.java
│   │   │           │   ├── TableMapper.java
│   │   │           │   ├── FieldMapper.java
│   │   │           │   ├── RecordMapper.java
│   │   │           │   ├── ViewMapper.java
│   │   │           │   └── ...
│   │   │           ├── service/                      # 业务层
│   │   │           │   ├── BaseService.java
│   │   │           │   ├── TableService.java
│   │   │           │   ├── FieldService.java
│   │   │           │   ├── RecordService.java
│   │   │           │   ├── ViewService.java
│   │   │           │   ├── DashboardService.java
│   │   │           │   ├── AttachmentService.java
│   │   │           │   ├── FormulaService.java
│   │   │           │   ├── ImportExportService.java
│   │   │           │   └── impl/                     # 实现类
│   │   │           ├── controller/                   # 控制层
│   │   │           │   ├── AuthController.java
│   │   │           │   ├── BaseController.java
│   │   │           │   ├── TableController.java
│   │   │           │   ├── FieldController.java
│   │   │           │   ├── RecordController.java
│   │   │           │   ├── ViewController.java
│   │   │           │   ├── DashboardController.java
│   │   │           │   ├── AttachmentController.java
│   │   │           │   └── ImportExportController.java
│   │   │           ├── dto/                          # 数据传输对象
│   │   │           │   ├── request/                  # 请求 DTO
│   │   │           │   │   ├── CreateBaseRequest.java
│   │   │           │   │   ├── UpdateRecordRequest.java
│   │   │           │   │   └── ...
│   │   │           │   └── response/                 # 响应 DTO
│   │   │           │       ├── BaseResponse.java
│   │   │           │       ├── RecordResponse.java
│   │   │           │       └── ...
│   │   │           ├── vo/                           # 视图对象
│   │   │           ├── websocket/                    # WebSocket
│   │   │           │   ├── CollaborationHandler.java
│   │   │           │   ├── WebSocketInterceptor.java
│   │   │           │   └── WebSocketService.java
│   │   │           └── security/                     # 安全模块
│   │   │               ├── JwtAuthenticationFilter.java
│   │   │               ├── JwtTokenProvider.java
│   │   │               ├── UserDetailsServiceImpl.java
│   │   │               └── CustomAccessDeniedHandler.java
│   │   └── resources/
│   │       ├── application.yml                       # 主配置
│   │       ├── application-dev.yml                   # 开发环境
│   │       ├── application-prod.yml                  # 生产环境
│   │       ├── mapper/                               # MyBatis XML
│   │       │   ├── BaseMapper.xml
│   │       │   ├── RecordMapper.xml
│   │       │   └── ...
│   │       └── db/
│   │           └── migration/                        # Flyway 迁移
│   └── test/                                         # 测试代码
│       └── java/
│           └── com/
│               └── smarttable/
│                   └── ...
├── pom.xml                                           # Maven 配置
├── Dockerfile                                        # Docker 构建
├── docker-compose.yml                                # Docker 编排
├── mvnw                                              # Maven Wrapper
└── README.md
```

---

## 五、数据库设计

### 5.1 实体类设计

```java
// entity/User.java
package com.smarttable.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@TableName("users")
public class User {
    @TableId(type = IdType.ASSIGN_UUID)
    private String id;
    
    private String email;
    private String password;
    private String name;
    private String avatar;
    
    @EnumValue
    private UserRole role;
    
    @EnumValue
    private UserStatus status;
    
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
    
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updatedAt;
}

// entity/Base.java
package com.smarttable.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@TableName("bases")
public class Base {
    @TableId(type = IdType.ASSIGN_UUID)
    private String id;
    
    private String name;
    private String description;
    private String icon;
    private String color;
    private Boolean isStarred;
    
    private String ownerId;
    
    @TableField(exist = false)
    private User owner;
    
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
    
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updatedAt;
}

// entity/Table.java
package com.smarttable.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@TableName("tables")
public class Table {
    @TableId(type = IdType.ASSIGN_UUID)
    private String id;
    
    private String name;
    private String description;
    private String primaryFieldId;
    private Integer recordCount;
    private Integer order;
    private Boolean isStarred;
    
    private String baseId;
    
    @TableField(exist = false)
    private Base base;
    
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
    
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updatedAt;
}

// entity/Field.java
package com.smarttable.entity;

import com.baomidou.mybatisplus.annotation.*;
import com.baomidou.mybatisplus.extension.handlers.JacksonTypeHandler;
import lombok.Data;
import java.time.LocalDateTime;
import java.util.Map;

@Data
@TableName(value = "fields", autoResultMap = true)
public class Field {
    @TableId(type = IdType.ASSIGN_UUID)
    private String id;
    
    private String name;
    
    @EnumValue
    private FieldType type;
    
    @TableField(typeHandler = JacksonTypeHandler.class)
    private Map<String, Object> options;
    
    private Boolean isPrimary;
    private Boolean isSystem;
    private Boolean isRequired;
    private Boolean isVisible;
    
    @TableField(typeHandler = JacksonTypeHandler.class)
    private Object defaultValue;
    
    private String description;
    private Integer order;
    
    private String tableId;
    
    @TableField(exist = false)
    private Table table;
    
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
    
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updatedAt;
}

// entity/Record.java
package com.smarttable.entity;

import com.baomidou.mybatisplus.annotation.*;
import com.baomidou.mybatisplus.extension.handlers.JacksonTypeHandler;
import lombok.Data;
import java.time.LocalDateTime;
import java.util.Map;

@Data
@TableName(value = "records", autoResultMap = true)
public class Record {
    @TableId(type = IdType.ASSIGN_UUID)
    private String id;
    
    @TableField(typeHandler = JacksonTypeHandler.class)
    private Map<String, Object> values;
    
    private String tableId;
    
    @TableField(exist = false)
    private Table table;
    
    private String createdById;
    private String updatedById;
    
    @TableField(exist = false)
    private User createdBy;
    
    @TableField(exist = false)
    private User updatedBy;
    
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
    
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updatedAt;
}

// entity/View.java
package com.smarttable.entity;

import com.baomidou.mybatisplus.annotation.*;
import com.baomidou.mybatisplus.extension.handlers.JacksonTypeHandler;
import lombok.Data;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@Data
@TableName(value = "views", autoResultMap = true)
public class View {
    @TableId(type = IdType.ASSIGN_UUID)
    private String id;
    
    private String name;
    
    @EnumValue
    private ViewType type;
    
    @TableField(typeHandler = JacksonTypeHandler.class)
    private Map<String, Object> config;
    
    @TableField(typeHandler = JacksonTypeHandler.class)
    private List<Map<String, Object>> filters;
    
    @TableField(typeHandler = JacksonTypeHandler.class)
    private List<Map<String, Object>> sorts;
    
    @TableField(typeHandler = JacksonTypeHandler.class)
    private List<String> groupBys;
    
    @TableField(typeHandler = JacksonTypeHandler.class)
    private List<String> hiddenFields;
    
    @TableField(typeHandler = JacksonTypeHandler.class)
    private List<String> frozenFields;
    
    @EnumValue
    private RowHeight rowHeight;
    
    private Boolean isDefault;
    private Integer order;
    
    private String tableId;
    
    @TableField(exist = false)
    private Table table;
    
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
    
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updatedAt;
}

// entity/Dashboard.java
package com.smarttable.entity;

import com.baomidou.mybatisplus.annotation.*;
import com.baomidou.mybatisplus.extension.handlers.JacksonTypeHandler;
import lombok.Data;
import java.time.LocalDateTime;
import java.util.List;
import java.util.Map;

@Data
@TableName(value = "dashboards", autoResultMap = true)
public class Dashboard {
    @TableId(type = IdType.ASSIGN_UUID)
    private String id;
    
    private String name;
    private String description;
    
    @TableField(typeHandler = JacksonTypeHandler.class)
    private List<Map<String, Object>> widgets;
    
    @TableField(typeHandler = JacksonTypeHandler.class)
    private Map<String, Object> layout;
    
    @EnumValue
    private LayoutType layoutType;
    
    private Integer gridColumns;
    
    @TableField(typeHandler = JacksonTypeHandler.class)
    private Map<String, Object> refreshConfig;
    
    private Boolean isStarred;
    private Integer order;
    
    private String baseId;
    private String createdById;
    
    @TableField(exist = false)
    private Base base;
    
    @TableField(exist = false)
    private User createdBy;
    
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
    
    @TableField(fill = FieldFill.INSERT_UPDATE)
    private LocalDateTime updatedAt;
}

// entity/Attachment.java
package com.smarttable.entity;

import com.baomidou.mybatisplus.annotation.*;
import lombok.Data;
import java.time.LocalDateTime;

@Data
@TableName("attachments")
public class Attachment {
    @TableId(type = IdType.ASSIGN_UUID)
    private String id;
    
    private String name;
    private String originalName;
    private Long size;
    private String type;
    private String fileType;
    private String extension;
    private String storageKey;
    private String thumbnailKey;
    
    private String recordId;
    private String fieldId;
    private String tableId;
    private String baseId;
    private String createdById;
    
    @TableField(fill = FieldFill.INSERT)
    private LocalDateTime createdAt;
}

// 枚举定义
package com.smarttable.common.enums;

public enum UserRole {
    ADMIN, USER, GUEST
}

public enum UserStatus {
    ACTIVE, INACTIVE, SUSPENDED
}

public enum FieldType {
    TEXT, NUMBER, DATE, SINGLE_SELECT, MULTI_SELECT, CHECKBOX,
    MEMBER, PHONE, EMAIL, URL, ATTACHMENT, FORMULA, LINK, LOOKUP,
    CREATED_BY, CREATED_TIME, UPDATED_BY, UPDATED_TIME, AUTO_NUMBER,
    RATING, PROGRESS
}

public enum ViewType {
    TABLE, KANBAN, CALENDAR, GANTT, FORM, GALLERY
}

public enum RowHeight {
    SHORT, MEDIUM, TALL
}

public enum LayoutType {
    GRID, FREE
}
```

---

## 六、API 设计规范

### 6.1 RESTful API 路由设计

```java
// controller/BaseController.java
package com.smarttable.controller;

import com.smarttable.common.result.Result;
import com.smarttable.dto.request.CreateBaseRequest;
import com.smarttable.dto.request.UpdateBaseRequest;
import com.smarttable.dto.response.BaseResponse;
import com.smarttable.service.BaseService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api/bases")
@RequiredArgsConstructor
@Tag(name = "Base 管理", description = "多维表格相关接口")
public class BaseController {

    private final BaseService baseService;

    @GetMapping
    @Operation(summary = "获取所有 Base")
    public Result<List<BaseResponse>> list() {
        return Result.success(baseService.listAll());
    }

    @GetMapping("/{id}")
    @Operation(summary = "获取单个 Base")
    public Result<BaseResponse> getById(@PathVariable String id) {
        return Result.success(baseService.getById(id));
    }

    @PostMapping
    @Operation(summary = "创建 Base")
    public Result<BaseResponse> create(@Valid @RequestBody CreateBaseRequest request) {
        return Result.success(baseService.create(request));
    }

    @PutMapping("/{id}")
    @Operation(summary = "更新 Base")
    public Result<BaseResponse> update(
            @PathVariable String id,
            @Valid @RequestBody UpdateBaseRequest request) {
        return Result.success(baseService.update(id, request));
    }

    @DeleteMapping("/{id}")
    @Operation(summary = "删除 Base")
    public Result<Void> delete(@PathVariable String id) {
        baseService.delete(id);
        return Result.success();
    }

    @PostMapping("/{id}/star")
    @Operation(summary = "收藏/取消收藏 Base")
    public Result<Void> toggleStar(@PathVariable String id) {
        baseService.toggleStar(id);
        return Result.success();
    }
}

// controller/RecordController.java
package com.smarttable.controller;

import com.smarttable.common.result.PageResult;
import com.smarttable.common.result.Result;
import com.smarttable.dto.request.BatchOperationRequest;
import com.smarttable.dto.request.CreateRecordRequest;
import com.smarttable.dto.request.UpdateRecordRequest;
import com.smarttable.dto.response.RecordResponse;
import com.smarttable.service.RecordService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import jakarta.validation.Valid;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequestMapping("/api")
@RequiredArgsConstructor
@Tag(name = "Record 管理", description = "数据记录相关接口")
public class RecordController {

    private final RecordService recordService;

    @GetMapping("/tables/{tableId}/records")
    @Operation(summary = "获取记录列表")
    public Result<PageResult<RecordResponse>> list(
            @PathVariable String tableId,
            @RequestParam(defaultValue = "1") Integer page,
            @RequestParam(defaultValue = "50") Integer pageSize,
            @RequestParam(required = false) String search,
            @RequestParam(required = false) String filters,
            @RequestParam(required = false) String sorts) {
        return Result.success(recordService.list(tableId, page, pageSize, search, filters, sorts));
    }

    @GetMapping("/records/{id}")
    @Operation(summary = "获取单个记录")
    public Result<RecordResponse> getById(@PathVariable String id) {
        return Result.success(recordService.getById(id));
    }

    @PostMapping("/tables/{tableId}/records")
    @Operation(summary = "创建记录")
    public Result<RecordResponse> create(
            @PathVariable String tableId,
            @Valid @RequestBody CreateRecordRequest request) {
        return Result.success(recordService.create(tableId, request));
    }

    @PutMapping("/records/{id}")
    @Operation(summary = "更新记录")
    public Result<RecordResponse> update(
            @PathVariable String id,
            @Valid @RequestBody UpdateRecordRequest request) {
        return Result.success(recordService.update(id, request));
    }

    @DeleteMapping("/records/{id}")
    @Operation(summary = "删除记录")
    public Result<Void> delete(@PathVariable String id) {
        recordService.delete(id);
        return Result.success();
    }

    @PostMapping("/tables/{tableId}/records/batch")
    @Operation(summary = "批量操作记录")
    public Result<Void> batchOperation(
            @PathVariable String tableId,
            @Valid @RequestBody BatchOperationRequest request) {
        recordService.batchOperation(tableId, request);
        return Result.success();
    }
}
```

### 6.2 统一响应格式

```java
// common/result/Result.java
package com.smarttable.common.result;

import lombok.Data;
import java.time.LocalDateTime;

@Data
public class Result<T> {
    private Boolean success;
    private T data;
    private String message;
    private String code;
    private LocalDateTime timestamp;

    public static <T> Result<T> success(T data) {
        Result<T> result = new Result<>();
        result.setSuccess(true);
        result.setData(data);
        result.setTimestamp(LocalDateTime.now());
        return result;
    }

    public static <T> Result<T> success() {
        return success(null);
    }

    public static <T> Result<T> error(String message) {
        Result<T> result = new Result<>();
        result.setSuccess(false);
        result.setMessage(message);
        result.setCode("ERROR");
        result.setTimestamp(LocalDateTime.now());
        return result;
    }

    public static <T> Result<T> error(String code, String message) {
        Result<T> result = new Result<>();
        result.setSuccess(false);
        result.setCode(code);
        result.setMessage(message);
        result.setTimestamp(LocalDateTime.now());
        return result;
    }
}

// common/result/PageResult.java
package com.smarttable.common.result;

import lombok.Data;
import java.util.List;

@Data
public class PageResult<T> {
    private List<T> list;
    private Long total;
    private Long page;
    private Long pageSize;
    private Long totalPages;

    public static <T> PageResult<T> of(List<T> list, Long total, Long page, Long pageSize) {
        PageResult<T> result = new PageResult<>();
        result.setList(list);
        result.setTotal(total);
        result.setPage(page);
        result.setPageSize(pageSize);
        result.setTotalPages((total + pageSize - 1) / pageSize);
        return result;
    }
}
```

---

## 七、核心功能实现方案

### 7.1 公式引擎服务端实现

```java
// service/FormulaService.java
package com.smarttable.service;

import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;

import java.math.BigDecimal;
import java.math.RoundingMode;
import java.time.LocalDate;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.time.temporal.ChronoUnit;
import java.util.*;
import java.util.function.Function;
import java.util.regex.Matcher;
import java.util.regex.Pattern;

@Slf4j
@Service
public class FormulaService {

    private final Map<String, Function<List<Object>, Object>> functions = new HashMap<>();

    public FormulaService() {
        registerDefaultFunctions();
    }

    /**
     * 计算单个记录的公式字段
     */
    public Object calculateFormula(String formula, Map<String, Object> recordValues, 
                                   List<Map<String, Object>> allRecords) {
        try {
            // 1. 解析字段引用 {fieldId}
            List<FieldReference> fieldRefs = extractFieldReferences(formula);
            
            // 2. 替换字段引用为实际值
            String expression = formula;
            for (FieldReference ref : fieldRefs) {
                Object value = recordValues.get(ref.getFieldId());
                expression = expression.replace(ref.getRaw(), formatValue(value));
            }
            
            // 3. 执行计算
            return evaluateExpression(expression);
        } catch (Exception e) {
            log.error("公式计算错误: {}, formula: {}", e.getMessage(), formula);
            return null;
        }
    }

    /**
     * 批量计算公式字段
     */
    public List<Map<String, Object>> calculateBatchFormulas(
            List<FormulaConfig> formulas,
            List<Map<String, Object>> records) {
        
        List<Map<String, Object>> result = new ArrayList<>();
        
        for (Map<String, Object> record : records) {
            Map<String, Object> calculatedValues = new HashMap<>();
            Map<String, Object> currentValues = new HashMap<>(record);
            
            for (FormulaConfig config : formulas) {
                Object value = calculateFormula(
                    config.getFormula(), 
                    currentValues, 
                    records
                );
                calculatedValues.put(config.getFieldId(), value);
                currentValues.put(config.getFieldId(), value);
            }
            
            Map<String, Object> newRecord = new HashMap<>(record);
            newRecord.putAll(calculatedValues);
            result.add(newRecord);
        }
        
        return result;
    }

    private void registerDefaultFunctions() {
        // 数学函数
        functions.put("SUM", args -> args.stream()
            .mapToDouble(this::toDouble)
            .sum());
        
        functions.put("AVG", args -> args.stream()
            .mapToDouble(this::toDouble)
            .average()
            .orElse(0.0));
        
        functions.put("MAX", args -> args.stream()
            .mapToDouble(this::toDouble)
            .max()
            .orElse(0.0));
        
        functions.put("MIN", args -> args.stream()
            .mapToDouble(this::toDouble)
            .min()
            .orElse(0.0));
        
        functions.put("ROUND", args -> {
            if (args.size() < 1) return 0;
            double value = toDouble(args.get(0));
            int decimals = args.size() > 1 ? toInt(args.get(1)) : 0;
            return BigDecimal.valueOf(value)
                .setScale(decimals, RoundingMode.HALF_UP)
                .doubleValue();
        });
        
        // 文本函数
        functions.put("CONCAT", args -> {
            StringBuilder sb = new StringBuilder();
            for (Object arg : args) {
                if (arg != null) sb.append(arg.toString());
            }
            return sb.toString();
        });
        
        functions.put("UPPER", args -> {
            if (args.isEmpty() || args.get(0) == null) return "";
            return args.get(0).toString().toUpperCase();
        });
        
        functions.put("LOWER", args -> {
            if (args.isEmpty() || args.get(0) == null) return "";
            return args.get(0).toString().toLowerCase();
        });
        
        functions.put("LEN", args -> {
            if (args.isEmpty() || args.get(0) == null) return 0;
            return args.get(0).toString().length();
        });
        
        // 日期函数
        functions.put("TODAY", args -> LocalDate.now().toString());
        
        functions.put("NOW", args -> LocalDateTime.now().toString());
        
        functions.put("YEAR", args -> {
            if (args.isEmpty() || args.get(0) == null) return LocalDate.now().getYear();
            LocalDate date = parseDate(args.get(0));
            return date.getYear();
        });
        
        functions.put("MONTH", args -> {
            if (args.isEmpty() || args.get(0) == null) return LocalDate.now().getMonthValue();
            LocalDate date = parseDate(args.get(0));
            return date.getMonthValue();
        });
        
        functions.put("DAY", args -> {
            if (args.isEmpty() || args.get(0) == null) return LocalDate.now().getDayOfMonth();
            LocalDate date = parseDate(args.get(0));
            return date.getDayOfMonth();
        });
        
        functions.put("DATEDIF", args -> {
            if (args.size() < 2) return 0;
            LocalDate start = parseDate(args.get(0));
            LocalDate end = parseDate(args.get(1));
            String unit = args.size() > 2 ? args.get(2).toString() : "D";
            
            return switch (unit.toUpperCase()) {
                case "Y" -> ChronoUnit.YEARS.between(start, end);
                case "M" -> ChronoUnit.MONTHS.between(start, end);
                case "D" -> ChronoUnit.DAYS.between(start, end);
                default -> ChronoUnit.DAYS.between(start, end);
            };
        });
        
        // 逻辑函数
        functions.put("IF", args -> {
            if (args.size() < 3) return null;
            boolean condition = toBoolean(args.get(0));
            return condition ? args.get(1) : args.get(2);
        });
        
        functions.put("AND", args -> args.stream()
            .allMatch(this::toBoolean));
        
        functions.put("OR", args -> args.stream()
            .anyMatch(this::toBoolean));
        
        functions.put("NOT", args -> {
            if (args.isEmpty()) return true;
            return !toBoolean(args.get(0));
        });
        
        // 统计函数
        functions.put("COUNT", args -> (long) args.size());
        
        functions.put("COUNTA", args -> args.stream()
            .filter(Objects::nonNull)
            .filter(v -> !v.toString().isEmpty())
            .count());
    }

    private List<FieldReference> extractFieldReferences(String formula) {
        List<FieldReference> refs = new ArrayList<>();
        Pattern pattern = Pattern.compile("\\{([^}]+)\\}");
        Matcher matcher = pattern.matcher(formula);
        
        while (matcher.find()) {
            refs.add(new FieldReference(matcher.group(0), matcher.group(1)));
        }
        
        return refs;
    }

    private String formatValue(Object value) {
        if (value == null) return "null";
        if (value instanceof String) return "\"" + value + "\"";
        if (value instanceof Number) return value.toString();
        if (value instanceof Boolean) return value.toString();
        return "\"" + value.toString() + "\"";
    }

    private Object evaluateExpression(String expression) {
        // 使用脚本引擎或自定义解析器
        // 这里简化处理，实际生产环境应使用更安全的方案
        try {
            javax.script.ScriptEngine engine = 
                new javax.script.ScriptEngineManager().getEngineByName("JavaScript");
            return engine.eval(expression);
        } catch (Exception e) {
            log.error("表达式求值错误: {}", e.getMessage());
            return null;
        }
    }

    private double toDouble(Object value) {
        if (value == null) return 0.0;
        if (value instanceof Number) return ((Number) value).doubleValue();
        try {
            return Double.parseDouble(value.toString());
        } catch (NumberFormatException e) {
            return 0.0;
        }
    }

    private int toInt(Object value) {
        return (int) toDouble(value);
    }

    private boolean toBoolean(Object value) {
        if (value == null) return false;
        if (value instanceof Boolean) return (Boolean) value;
        if (value instanceof Number) return ((Number) value).doubleValue() != 0;
        return Boolean.parseBoolean(value.toString());
    }

    private LocalDate parseDate(Object value) {
        if (value instanceof LocalDate) return (LocalDate) value;
        if (value instanceof LocalDateTime) return ((LocalDateTime) value).toLocalDate();
        return LocalDate.parse(value.toString(), DateTimeFormatter.ISO_DATE);
    }

    @Data
    public static class FieldReference {
        private final String raw;
        private final String fieldId;
    }

    @Data
    public static class FormulaConfig {
        private String fieldId;
        private String formula;
    }
}
```

### 7.2 实时协作 WebSocket 实现

```java
// websocket/CollaborationHandler.java
package com.smarttable.websocket;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.smarttable.security.JwtTokenProvider;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;
import org.springframework.web.socket.*;
import org.springframework.web.socket.handler.TextWebSocketHandler;

import java.io.IOException;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

@Slf4j
@Component
public class CollaborationHandler extends TextWebSocketHandler {

    private final JwtTokenProvider jwtTokenProvider;
    private final ObjectMapper objectMapper;
    
    // 存储用户会话: userId -> WebSocketSession
    private final Map<String, WebSocketSession> userSessions = new ConcurrentHashMap<>();
    
    // 存储房间用户: baseId -> Set<userId>
    private final Map<String, Set<String>> roomUsers = new ConcurrentHashMap<>();
    
    // 存储用户加入的房间: userId -> Set<baseId>
    private final Map<String, Set<String>> userRooms = new ConcurrentHashMap<>();

    public CollaborationHandler(JwtTokenProvider jwtTokenProvider, ObjectMapper objectMapper) {
        this.jwtTokenProvider = jwtTokenProvider;
        this.objectMapper = objectMapper;
    }

    @Override
    public void afterConnectionEstablished(WebSocketSession session) throws Exception {
        String token = extractToken(session);
        if (token == null || !jwtTokenProvider.validateToken(token)) {
            session.close(CloseStatus.POLICY_VIOLATION);
            return;
        }
        
        String userId = jwtTokenProvider.getUserIdFromToken(token);
        userSessions.put(userId, session);
        userRooms.put(userId, ConcurrentHashMap.newKeySet());
        
        log.info("WebSocket 连接建立: userId={}, sessionId={}", userId, session.getId());
    }

    @Override
    protected void handleTextMessage(WebSocketSession session, TextMessage message) throws Exception {
        String payload = message.getPayload();
        WebSocketMessage wsMessage = objectMapper.readValue(payload, WebSocketMessage.class);
        
        String userId = getUserIdFromSession(session);
        
        switch (wsMessage.getType()) {
            case "join-base":
                handleJoinBase(userId, wsMessage.getData());
                break;
            case "leave-base":
                handleLeaveBase(userId, wsMessage.getData());
                break;
            case "editing-record":
                handleEditingRecord(userId, wsMessage.getData());
                break;
            case "update-record":
                handleUpdateRecord(userId, wsMessage.getData());
                break;
            case "field-change":
                handleFieldChange(userId, wsMessage.getData());
                break;
            case "cursor-position":
                handleCursorPosition(userId, wsMessage.getData());
                break;
            default:
                log.warn("未知消息类型: {}", wsMessage.getType());
        }
    }

    @Override
    public void afterConnectionClosed(WebSocketSession session, CloseStatus status) throws Exception {
        String userId = getUserIdFromSession(session);
        
        // 离开所有房间
        Set<String> rooms = userRooms.getOrDefault(userId, new HashSet<>());
        for (String baseId : rooms) {
            leaveRoom(userId, baseId);
        }
        
        userSessions.remove(userId);
        userRooms.remove(userId);
        
        log.info("WebSocket 连接关闭: userId={}, status={}", userId, status);
    }

    private void handleJoinBase(String userId, Map<String, Object> data) {
        String baseId = (String) data.get("baseId");
        
        roomUsers.computeIfAbsent(baseId, k -> ConcurrentHashMap.newKeySet()).add(userId);
        userRooms.get(userId).add(baseId);
        
        // 通知房间内其他用户
        broadcastToRoom(baseId, userId, new WebSocketMessage("user-joined", Map.of(
            "userId", userId,
            "baseId", baseId
        )));
        
        log.info("用户加入房间: userId={}, baseId={}", userId, baseId);
    }

    private void handleLeaveBase(String userId, Map<String, Object> data) {
        String baseId = (String) data.get("baseId");
        leaveRoom(userId, baseId);
    }

    private void leaveRoom(String userId, String baseId) {
        Set<String> users = roomUsers.get(baseId);
        if (users != null) {
            users.remove(userId);
        }
        
        Set<String> rooms = userRooms.get(userId);
        if (rooms != null) {
            rooms.remove(baseId);
        }
        
        // 通知房间内其他用户
        broadcastToRoom(baseId, userId, new WebSocketMessage("user-left", Map.of(
            "userId", userId,
            "baseId", baseId
        )));
        
        log.info("用户离开房间: userId={}, baseId={}", userId, baseId);
    }

    private void handleEditingRecord(String userId, Map<String, Object> data) {
        String baseId = (String) data.get("baseId");
        
        broadcastToRoom(baseId, userId, new WebSocketMessage("record-editing", Map.of(
            "userId", userId,
            "tableId", data.get("tableId"),
            "recordId", data.get("recordId")
        )));
    }

    private void handleUpdateRecord(String userId, Map<String, Object> data) {
        String baseId = (String) data.get("baseId");
        
        // 广播给房间内所有用户（包括自己确认）
        broadcastToRoom(baseId, null, new WebSocketMessage("record-updated", Map.of(
            "userId", userId,
            "tableId", data.get("tableId"),
            "recordId", data.get("recordId"),
            "values", data.get("values"),
            "timestamp", System.currentTimeMillis()
        )));
    }

    private void handleFieldChange(String userId, Map<String, Object> data) {
        String baseId = (String) data.get("baseId");
        
        broadcastToRoom(baseId, userId, new WebSocketMessage("field-changed", Map.of(
            "userId", userId,
            "tableId", data.get("tableId"),
            "action", data.get("action"),
            "field", data.get("field")
        )));
    }

    private void handleCursorPosition(String userId, Map<String, Object> data) {
        String baseId = (String) data.get("baseId");
        
        broadcastToRoom(baseId, userId, new WebSocketMessage("cursor-moved", Map.of(
            "userId", userId,
            "tableId", data.get("tableId"),
            "recordId", data.get("recordId"),
            "fieldId", data.get("fieldId"),
            "position", data.get("position")
        )));
    }

    private void broadcastToRoom(String baseId, String excludeUserId, WebSocketMessage message) {
        Set<String> users = roomUsers.get(baseId);
        if (users == null) return;
        
        String payload;
        try {
            payload = objectMapper.writeValueAsString(message);
        } catch (Exception e) {
            log.error("消息序列化失败", e);
            return;
        }
        
        for (String userId : users) {
            if (userId.equals(excludeUserId)) continue;
            
            WebSocketSession session = userSessions.get(userId);
            if (session != null && session.isOpen()) {
                try {
                    session.sendMessage(new TextMessage(payload));
                } catch (IOException e) {
                    log.error("发送消息失败: userId={}", userId, e);
                }
            }
        }
    }

    private String extractToken(WebSocketSession session) {
        List<String> authHeaders = session.getHandshakeHeaders().get("Authorization");
        if (authHeaders == null || authHeaders.isEmpty()) {
            return null;
        }
        String bearer = authHeaders.get(0);
        if (bearer != null && bearer.startsWith("Bearer ")) {
            return bearer.substring(7);
        }
        return null;
    }

    private String getUserIdFromSession(WebSocketSession session) {
        // 从 session 属性中获取 userId
        return (String) session.getAttributes().get("userId");
    }

    @lombok.Data
    private static class WebSocketMessage {
        private String type;
        private Map<String, Object> data;

        public WebSocketMessage() {}

        public WebSocketMessage(String type, Map<String, Object> data) {
            this.type = type;
            this.data = data;
        }
    }
}

// websocket/WebSocketConfig.java
package com.smarttable.websocket;

import org.springframework.context.annotation.Configuration;
import org.springframework.web.socket.config.annotation.*;

@Configuration
@EnableWebSocket
public class WebSocketConfig implements WebSocketConfigurer {

    private final CollaborationHandler collaborationHandler;

    public WebSocketConfig(CollaborationHandler collaborationHandler) {
        this.collaborationHandler = collaborationHandler;
    }

    @Override
    public void registerWebSocketHandlers(WebSocketHandlerRegistry registry) {
        registry.addHandler(collaborationHandler, "/ws/collaboration")
                .setAllowedOrigins("*");
    }
}
```

### 7.3 批量操作优化

```java
// service/impl/RecordServiceImpl.java
package com.smarttable.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.baomidou.mybatisplus.extension.service.impl.ServiceImpl;
import com.smarttable.dto.request.*;
import com.smarttable.dto.response.RecordResponse;
import com.smarttable.entity.OperationHistory;
import com.smarttable.entity.Record;
import com.smarttable.entity.Table;
import com.smarttable.mapper.RecordMapper;
import com.smarttable.service.RecordService;
import com.smarttable.service.TableService;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class RecordServiceImpl extends ServiceImpl<RecordMapper, Record> 
    implements RecordService {

    private final TableService tableService;
    private final OperationHistoryService operationHistoryService;

    @Override
    @Transactional(rollbackFor = Exception.class)
    public List<RecordResponse> batchCreate(String tableId, BatchCreateRecordRequest request, String userId) {
        List<Record> records = request.getRecords().stream()
            .map(r -> {
                Record record = new Record();
                record.setTableId(tableId);
                record.setValues(r.getValues());
                record.setCreatedById(userId);
                record.setUpdatedById(userId);
                return record;
            })
            .collect(Collectors.toList());

        // 1. 批量插入记录
        saveBatch(records, 1000);

        // 2. 更新记录数
        Table table = tableService.getById(tableId);
        table.setRecordCount(table.getRecordCount() + records.size());
        tableService.updateById(table);

        // 3. 创建操作历史
        List<OperationHistory> histories = records.stream()
            .map(r -> {
                OperationHistory history = new OperationHistory();
                history.setBaseId(table.getBaseId());
                history.setTableId(tableId);
                history.setRecordId(r.getId());
                history.setAction(ActionType.CREATE);
                history.setEntityType(EntityType.RECORD);
                history.setNewValue(r.getValues());
                history.setUserId(userId);
                return history;
            })
            .collect(Collectors.toList());
        operationHistoryService.saveBatch(histories);

        return records.stream()
            .map(this::convertToResponse)
            .collect(Collectors.toList());
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void batchUpdate(BatchUpdateRecordRequest request, String userId) {
        List<Record> records = request.getUpdates().stream()
            .map(u -> {
                Record record = new Record();
                record.setId(u.getId());
                record.setValues(u.getValues());
                record.setUpdatedById(userId);
                return record;
            })
            .collect(Collectors.toList());

        // 分批更新，每批 1000 条
        List<List<Record>> batches = partition(records, 1000);
        
        for (List<Record> batch : batches) {
            updateBatchById(batch);
        }

        // 创建操作历史
        List<OperationHistory> histories = request.getUpdates().stream()
            .map(u -> {
                Record oldRecord = getById(u.getId());
                OperationHistory history = new OperationHistory();
                history.setBaseId(oldRecord.getTable().getBaseId());
                history.setTableId(oldRecord.getTableId());
                history.setRecordId(u.getId());
                history.setAction(ActionType.UPDATE);
                history.setEntityType(EntityType.RECORD);
                history.setOldValue(oldRecord.getValues());
                history.setNewValue(u.getValues());
                history.setUserId(userId);
                return history;
            })
            .collect(Collectors.toList());
        operationHistoryService.saveBatch(histories);
    }

    @Override
    @Transactional(rollbackFor = Exception.class)
    public void batchDelete(BatchDeleteRequest request, String userId) {
        List<String> ids = request.getIds();
        
        // 获取记录信息用于操作历史
        List<Record> records = listByIds(ids);
        
        // 删除记录
        removeByIds(ids);
        
        // 更新记录数
        Map<String, Long> tableCountMap = records.stream()
            .collect(Collectors.groupingBy(Record::getTableId, Collectors.counting()));
        
        for (Map.Entry<String, Long> entry : tableCountMap.entrySet()) {
            Table table = tableService.getById(entry.getKey());
            table.setRecordCount(table.getRecordCount() - entry.getValue().intValue());
            tableService.updateById(table);
        }
        
        // 创建操作历史
        List<OperationHistory> histories = records.stream()
            .map(r -> {
                OperationHistory history = new OperationHistory();
                history.setBaseId(r.getTable().getBaseId());
                history.setTableId(r.getTableId());
                history.setRecordId(r.getId());
                history.setAction(ActionType.DELETE);
                history.setEntityType(EntityType.RECORD);
                history.setOldValue(r.getValues());
                history.setUserId(userId);
                return history;
            })
            .collect(Collectors.toList());
        operationHistoryService.saveBatch(histories);
    }

    @Override
    public PageResult<RecordResponse> list(String tableId, Integer page, Integer pageSize, 
                                           String search, String filters, String sorts) {
        LambdaQueryWrapper<Record> wrapper = new LambdaQueryWrapper<>();
        wrapper.eq(Record::getTableId, tableId);
        
        // 搜索条件
        if (search != null && !search.isEmpty()) {
            // JSON 字段搜索需要自定义 SQL
            wrapper.apply("values::text ILIKE {0}", "%" + search + "%");
        }
        
        // 排序
        if (sorts != null && !sorts.isEmpty()) {
            // 解析排序参数并应用
            applySorts(wrapper, sorts);
        } else {
            wrapper.orderByDesc(Record::getCreatedAt);
        }
        
        Page<Record> recordPage = page(new Page<>(page, pageSize), wrapper);
        
        List<RecordResponse> records = recordPage.getRecords().stream()
            .map(this::convertToResponse)
            .collect(Collectors.toList());
        
        return PageResult.of(records, recordPage.getTotal(), (long) page, (long) pageSize);
    }

    private RecordResponse convertToResponse(Record record) {
        RecordResponse response = new RecordResponse();
        response.setId(record.getId());
        response.setValues(record.getValues());
        response.setTableId(record.getTableId());
        response.setCreatedAt(record.getCreatedAt());
        response.setUpdatedAt(record.getUpdatedAt());
        
        if (record.getCreatedBy() != null) {
            response.setCreatedBy(new UserBrief(
                record.getCreatedBy().getId(),
                record.getCreatedBy().getName(),
                record.getCreatedBy().getAvatar()
            ));
        }
        
        if (record.getUpdatedBy() != null) {
            response.setUpdatedBy(new UserBrief(
                record.getUpdatedBy().getId(),
                record.getUpdatedBy().getName(),
                record.getUpdatedBy().getAvatar()
            ));
        }
        
        return response;
    }

    private <T> List<List<T>> partition(List<T> list, int size) {
        List<List<T>> partitions = new ArrayList<>();
        for (int i = 0; i < list.size(); i += size) {
            partitions.add(list.subList(i, Math.min(i + size, list.size())));
        }
        return partitions;
    }

    private void applySorts(LambdaQueryWrapper<Record> wrapper, String sorts) {
        // 解析排序 JSON 并应用到 wrapper
        // 示例: [{"fieldId": "name", "order": "asc"}]
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
      - "8080:8080"
    environment:
      - SPRING_PROFILES_ACTIVE=prod
      - SPRING_DATASOURCE_URL=jdbc:postgresql://db:5432/smarttable
      - SPRING_DATASOURCE_USERNAME=postgres
      - SPRING_DATASOURCE_PASSWORD=password
      - SPRING_REDIS_HOST=redis
      - SPRING_REDIS_PORT=6379
      - MINIO_ENDPOINT=http://minio:9000
      - MINIO_ACCESS_KEY=minioadmin
      - MINIO_SECRET_KEY=minioadmin
      - JWT_SECRET=your-secret-key
    depends_on:
      - db
      - redis
      - minio
    networks:
      - smarttable-network
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/actuator/health"]
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
FROM eclipse-temurin:21-jdk-alpine AS builder

WORKDIR /app

# 复制 Maven 配置
COPY pom.xml .
COPY mvnw .
COPY .mvn .mvn

# 下载依赖
RUN ./mvnw dependency:go-offline -B

# 复制源代码
COPY src src

# 构建应用
RUN ./mvnw clean package -DskipTests -B

# 生产镜像
FROM eclipse-temurin:21-jre-alpine

WORKDIR /app

# 安装必要的工具
RUN apk add --no-cache curl

# 复制构建产物
COPY --from=builder /app/target/*.jar app.jar

# 暴露端口
EXPOSE 8080

# 健康检查
HEALTHCHECK --interval=30s --timeout=3s --start-period=60s --retries=3 \
  CMD curl -f http://localhost:8080/actuator/health || exit 1

# JVM 参数优化
ENV JAVA_OPTS="-XX:+UseG1GC -XX:MaxRAMPercentage=75.0 -XX:InitialRAMPercentage=50.0"

# 启动命令
ENTRYPOINT ["sh", "-c", "java $JAVA_OPTS -jar app.jar"]
```

---

## 九、技术选型对比总结

### 9.1 为什么选择 Java Spring Boot？

| 对比维度 | Java Spring Boot | Node.js NestJS | Python FastAPI |
|----------|------------------|----------------|----------------|
| **企业级稳定性** | ⭐⭐⭐⭐⭐ 最成熟 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **事务管理** | ⭐⭐⭐⭐⭐ 最强 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **高并发处理** | ⭐⭐⭐⭐⭐ 最强 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **生态完善度** | ⭐⭐⭐⭐⭐ 最完善 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **长期维护** | ⭐⭐⭐⭐⭐ 最稳定 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **人才招聘** | ⭐⭐⭐⭐⭐ 最容易 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |
| **开发效率** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ 最高 | ⭐⭐⭐⭐⭐ 最高 |
| **代码简洁度** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ 最简洁 | ⭐⭐⭐⭐⭐ 最简洁 |

### 9.2 适用场景分析

**Java Spring Boot 最适合 SmartTable 的场景：**

1. **企业级部署**：
   - 大型企业内部系统
   - 对稳定性要求极高的生产环境
   - 需要长期维护（5-10 年+）的项目

2. **高并发场景**：
   - 多用户同时编辑大量数据
   - 需要处理复杂的并发冲突
   - 高频率的批量操作

3. **复杂业务逻辑**：
   - 需要强事务保证的数据一致性
   - 复杂的权限控制和安全审计
   - 多系统集成需求

4. **团队背景**：
   - 团队已有 Java 技术栈积累
   - 企业已有 Java 基础设施
   - 需要与其他 Java 系统集成

### 9.3 潜在风险与缓解措施

| 风险 | 描述 | 缓解措施 |
|------|------|----------|
| **开发效率较低** | 相比 Node.js/Python 代码量更多 | 使用 MyBatis-Plus 减少重复代码；使用 Lombok 简化实体类 |
| **内存占用较高** | JVM 内存占用较大 | 使用 GraalVM Native Image；合理配置 JVM 参数 |
| **启动时间较长** | 应用启动较慢 | 使用 Spring Boot 懒加载；优化 Bean 初始化 |
| **学习曲线陡峭** | Spring 生态庞大复杂 | 团队培训；使用 Spring Initializr 快速搭建 |
| **配置繁琐** | 大量 XML/注解配置 | 使用配置中心；标准化配置模板 |

---

## 十、实施建议

### 10.1 分阶段实施计划

| 阶段 | 时间 | 目标 |
|------|------|------|
| **第一阶段** | 2-3 周 | 搭建基础框架，完成用户认证、Base/Table CRUD |
| **第二阶段** | 3-4 周 | 完成 Field/Record/View 核心功能 |
| **第三阶段** | 2-3 周 | 实现 Dashboard、附件管理、导入导出 |
| **第四阶段** | 2-3 周 | 实现公式引擎、实时协作 WebSocket |
| **第五阶段** | 1-2 周 | 性能优化、测试覆盖、部署上线 |

### 10.2 团队配置建议

| 角色 | 人数 | 技能要求 |
|------|------|----------|
| 架构师/技术负责人 | 1 | Spring Boot + 微服务架构设计经验 |
| 高级 Java 开发 | 2-3 | Spring Boot + MyBatis + 数据库优化 |
| 中级 Java 开发 | 3-4 | Java 基础 + Spring 框架 |
| 前端适配 | 1 | 熟悉现有 Vue 3 项目，API 对接 |
| DevOps | 1 | Docker + K8s + CI/CD 经验 |

### 10.3 关键成功因素

1. **架构设计先行**：详细的领域模型设计和接口设计
2. **代码规范**：统一的代码风格和开发规范
3. **自动化测试**：单元测试覆盖率 > 80%
4. **性能基准**：建立性能测试基准，持续监控
5. **文档完善**：API 文档、架构文档、部署文档同步更新

---

## 十一、总结

**推荐技术栈：**

```
后端框架：Spring Boot 3.2.x + Java 21
ORM：MyBatis-Plus 3.5.x
数据库：PostgreSQL 16.x
缓存：Redis 7.x
文件存储：MinIO
实时通信：Spring WebSocket
任务队列：RabbitMQ + XXL-Job
监控：Spring Boot Actuator + Micrometer + Prometheus
部署：Docker + Docker Compose
```

**核心优势：**

- ✅ 企业级稳定性，大量生产环境验证
- ✅ 强事务支持，ACID 保证
- ✅ 高并发处理能力
- ✅ 完善的生态体系
- ✅ 长期维护保障
- ✅ 人才市场充足

这套 Java 技术栈能够支撑 SmartTable 构建企业级的多维表格管理系统，特别适合对稳定性、安全性和长期维护有高要求的场景。

---

*文档版本：v1.0*
*最后更新：2026-04-03*
