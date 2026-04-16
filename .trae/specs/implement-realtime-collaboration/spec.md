# 多维表格实时协作更新功能规格说明

## Why

当前 SmartTable 系统已具备 Base 成员管理与分享功能，支持多用户访问同一 Base，但所有数据操作均为本地单用户模式，无法实现多人同时编辑时的实时同步。后端已安装 Flask-SocketIO 并完成初始化配置（eventlet worker、gunicorn 配置），但未实现任何 WebSocket 事件处理逻辑；前端仅有仪表盘的 HTTP 轮询伪实时方案，无 Socket.IO 客户端集成。需要构建完整的实时协作系统，使多用户在共享表格中能够实时感知彼此操作、同步数据变更、解决编辑冲突，满足企业级多人协作场景的需求。同时，实时协作功能必须设计为可独立启停的模块，默认不启用，确保在不启用时系统核心功能完整可用。

## What Changes

### 后端变更

- **SocketIO 事件处理器**：实现完整的 WebSocket 事件处理模块，包括连接/断开、房间管理、数据变更广播、Presence 追踪
- **协作服务层**：新增 `collaboration_service.py`，管理协作房间、用户在线状态、编辑锁、操作日志
- **数据变更推送**：在现有 RecordService/TableService/FieldService/ViewService 的写操作中集成变更推送逻辑（通过条件调用，仅在实时协作启用时生效）
- **冲突解决引擎**：实现基于操作转换（OT）的轻量级冲突解决机制，处理并发编辑同一单元格的场景
- **Presence 服务**：基于 Redis 实现用户在线状态、当前操作位置（视图/单元格）的实时追踪
- **数据库迁移**：新增 `collaboration_sessions` 表存储协作会话信息
- **启动参数控制**：实现 `--enable-realtime` / `-r` 命令行参数，控制是否启动 SocketIO 实时协作功能
- **功能隔离**：实时协作模块与核心业务模块解耦，确保禁用实时协作时系统所有其他功能正常可用

### 前端变更

- **Socket.IO 客户端集成**：引入 `socket.io-client`，建立与后端的 WebSocket 长连接
- **实时协作 Composable**：新增 `useRealtimeCollaboration.ts`，封装连接管理、事件订阅、断线重连
- **协作状态 Store**：新增 `collaborationStore.ts`，管理在线用户、编辑锁、操作反馈
- **视图层实时更新**：改造 TableView、KanbanView、CalendarView、GanttView、FormView、GalleryView，接入实时数据推送
- **Presence UI 组件**：新增在线用户头像列表、光标/选区高亮、操作状态提示组件
- **冲突解决 UI**：新增冲突提示对话框，支持用户手动选择保留版本
- **断线重连机制**：实现自动重连、离线操作队列、重连后数据同步
- **功能降级**：前端检测后端实时协作是否可用，不可用时自动降级为传统 HTTP 模式，隐藏协作相关 UI

### **BREAKING** 变更

- ~~**run.py 启动方式变更**~~：不再强制变更启动方式，默认仍使用 `app.run()`，仅在指定 `--enable-realtime` 参数时切换为 `socketio.run(app)`
- **前端数据流变更**：当实时协作启用时，视图组件的数据更新路径从"本地操作→本地存储"变为"本地操作→后端API→WebSocket广播→所有客户端更新"；禁用时保持原有数据流不变

## Impact

- Affected specs: `implement-base-member-sharing`（权限系统需与协作房间联动）、`implement-smart-table-system`（视图系统需接入实时更新）、`comprehensive-system-check`（功能完整性需包含协作功能及禁用模式验证）
- Affected code:
  - 后端：`app/extensions.py`（SocketIO 配置增强、条件初始化）、`app/__init__.py`（条件注册 SocketIO 事件）、`app/services/record_service.py`（条件集成变更推送）、`app/services/table_service.py`（条件集成变更推送）、`app/services/field_service.py`（条件集成变更推送）、`app/services/view_service.py`（条件集成变更推送）、`run.py`（启动参数解析、条件启动 SocketIO）、`app/config.py`（新增配置项）
  - 前端：`smart-table/src/stores/tableStore.ts`（条件接入实时更新）、`smart-table/src/stores/viewStore.ts`（条件接入实时更新）、`smart-table/src/components/views/`（所有视图组件条件接入实时更新）、`smart-table/src/db/services/`（本地服务与远程同步协调）、`smart-table/src/services/api/`（API 服务增加协作接口调用）

---

## 技术架构

### 整体架构

```
┌─────────────────────────────────────────────────────────────┐
│                        前端 (Vue3)                          │
│  ┌──────────┐  ┌──────────────┐  ┌────────────────────┐    │
│  │ 视图组件  │  │ 协作状态Store │  │ 实时协作Composable │    │
│  │ (Table/  │◄─┤(collaboration │◄─┤(useRealtime       │    │
│  │ Kanban/  │  │   Store.ts)  │  │ Collaboration.ts)  │    │
│  │ Calendar │  └──────┬───────┘  └────────┬───────────┘    │
│  │ /Gantt)  │         │                   │                │
│  └────┬─────┘         │           ┌───────┴────────┐       │
│       │               │           │ Socket.IO Client│       │
│       │               │           │ (socketClient.ts)│      │
│       │               │           └───────┬────────┘       │
│  ┌────┴─────┐         │                   │                │
│  │tableStore│         │                   │ WebSocket      │
│  │viewStore │◄────────┘                   │                │
│  └──────────┘                             │                │
└───────────────────────────────────────────┼────────────────┘
                                            │
                              ┌─────────────┼─────────────┐
                              │   HTTP REST │  WebSocket   │
                              │     API     │  (Socket.IO) │
                              └──────┬──────┴──────┬───────┘
                                     │             │
┌────────────────────────────────────┼─────────────┼─────────┐
│                        后端 (Flask)                             │
│  ┌──────────┐  ┌──────────┐  ┌───┴───────┐  ┌──┴─────────┐ │
│  │ REST API │  │ Service  │  │ SocketIO  │  │ 协作服务    │ │
│  │ Routes   │─►│ Layer    │─►│ Events    │─►│(collab_    │ │
│  │ (15蓝图) │  │(Record/  │  │ Handler   │  │ service.py)│ │
│  │          │  │ Table/   │  │           │  │            │ │
│  │          │  │ Field/   │  │           │  │ ┌────────┐ │ │
│  │          │  │ View)    │  │           │  │ │Presence│ │ │
│  │          │  │          │  │           │  │ │Service │ │ │
│  └──────────┘  └────┬─────┘  └───────────┘  │ ├────────┤ │ │
│                     │                        │ │LockMgr │ │ │
│                     │  ┌──────────────┐      │ ├────────┤ │ │
│                     │  │ 变更广播服务  │◄─────┤ │Broad-  │ │ │
│                     │  │ (条件调用)    │      │ │caster  │ │ │
│                     │  └──────────────┘      │ └────────┘ │ │
│                     │                        └─────┬──────┘ │ │
│  ┌──────────┐      │                              │        │ │
│  │  Models  │◄─────┘                              │        │ │
│  │(SQLAlchemy)│                                    │        │ │
│  └──────────┘                                     │        │ │
│                                                   │        │ │
│  ┌───────────────────────────────────────────────┐│        │ │
│  │              Redis                            ││        │ │
│  │  ┌──────────┐ ┌────────┐ ┌─────────────────┐ ││        │ │
│  │  │Presence  │ │Lock    │ │SocketIO Message │ ││        │ │
│  │  │Store     │ │Store   │ │Queue(Adapter)   │ ││        │ │
│  │  └──────────┘ └────────┘ └─────────────────┘ ││        │ │
│  └───────────────────────────────────────────────┘│        │ │
└───────────────────────────────────────────────────┼────────┘
                                                    │
                              ┌─────────────────────┼────────┐
                              │   PostgreSQL        │        │
                              │  ┌─────────────────┐│        │
                              │  │collaboration_   ││        │
                              │  │sessions 表      ││        │
                              │  └─────────────────┘│        │
                              └─────────────────────────────┘
```

### 模块依赖关系

```
run.py (--enable-realtime)
  │
  ├── app.__init__.create_app()
  │     ├── [始终] 初始化核心扩展（db, jwt, bcrypt, cors, cache, migrate）
  │     ├── [始终] 注册核心路由蓝图（auth, bases, tables, fields, records, views...）
  │     ├── [条件] 初始化 SocketIO 扩展（仅 --enable-realtime）
  │     └── [条件] 注册 SocketIO 事件处理器（仅 --enable-realtime）
  │
  ├── app.extensions
  │     ├── [始终] db, jwt, bcrypt, cors, cache, migrate
  │     └── [条件] socketio（仅 --enable-realtime 时 init_app）
  │
  ├── app.services.*
  │     ├── [始终] 核心业务逻辑（record_service, table_service...）
  │     └── [条件] collaboration_service（仅 --enable-realtime 时导入和调用）
  │
  └── run.py 启动逻辑
        ├── [默认] app.run(host, port)
        └── [--enable-realtime] socketio.run(app, host, port)
```

### 通信协议定义

#### Socket.IO 事件协议

所有事件遵循统一的命名空间规范：`<类别>:<动作>`，消息体采用 JSON 格式。

**连接与认证事件**

| 事件名 | 方向 | 请求参数 | 响应/广播参数 | 说明 |
|--------|------|---------|-------------|------|
| `connect` | Client→Server | Query: `token=<JWT>` | 认证成功/失败 | 建立连接时携带 JWT |
| `disconnect` | Client→Server | — | 广播 `presence:user_left` | 断开连接 |
| `error` | Server→Client | — | `{code, message}` | 连接错误通知 |

**房间管理事件**

| 事件名 | 方向 | 请求参数 | 响应/广播参数 | 说明 |
|--------|------|---------|-------------|------|
| `room:join` | Client→Server | `{base_id}` | 回调: `{success, online_users}` / 广播: `presence:user_joined` | 加入协作房间 |
| `room:leave` | Client→Server | `{base_id}` | 广播: `presence:user_left` | 离开协作房间 |

**Presence 事件**

| 事件名 | 方向 | 请求参数 | 广播参数 | 说明 |
|--------|------|---------|---------|------|
| `presence:view_changed` | Client→Server | `{base_id, table_id, view_id, view_type}` | `{user_id, nickname, avatar, table_id, view_id, view_type}` | 视图位置变更 |
| `presence:cell_selected` | Client→Server | `{base_id, table_id, record_id, field_id}` | `{user_id, nickname, avatar, table_id, record_id, field_id}` | 操作位置变更 |
| `presence:user_joined` | Server→Client(广播) | — | `{user_id, nickname, avatar, current_view}` | 用户加入 |
| `presence:user_left` | Server→Client(广播) | — | `{user_id, nickname}` | 用户离开 |

**编辑锁事件**

| 事件名 | 方向 | 请求参数 | 响应/广播参数 | 说明 |
|--------|------|---------|-------------|------|
| `lock:acquire` | Client→Server | `{table_id, record_id, field_id}` | 回调: `{success, locked_by?}` / 广播: `lock:acquired` | 获取编辑锁 |
| `lock:release` | Client→Server | `{table_id, record_id, field_id}` | 广播: `lock:released` | 释放编辑锁 |
| `lock:acquired` | Server→Client(广播) | — | `{user_id, nickname, avatar, table_id, record_id, field_id}` | 锁被获取 |
| `lock:released` | Server→Client(广播) | — | `{user_id, table_id, record_id, field_id}` | 锁被释放 |

**数据变更事件（Server→Client 广播）**

| 事件名 | 广播参数 | 说明 |
|--------|---------|------|
| `data:record_created` | `{table_id, record, changed_by, timestamp}` | 记录创建 |
| `data:record_updated` | `{table_id, record_id, changes: [{field_id, old_value, new_value}], changed_by, timestamp, version}` | 记录更新（增量） |
| `data:record_deleted` | `{table_id, record_id, snapshot, changed_by, timestamp}` | 记录删除 |
| `data:field_created` | `{table_id, field, changed_by, timestamp}` | 字段创建 |
| `data:field_updated` | `{table_id, field_id, changes, changed_by, timestamp}` | 字段更新 |
| `data:field_deleted` | `{table_id, field_id, changed_by, timestamp}` | 字段删除 |
| `data:view_updated` | `{table_id, view_id, changes, changed_by, timestamp}` | 视图配置更新 |
| `data:table_created` | `{base_id, table, changed_by, timestamp}` | 表创建 |
| `data:table_updated` | `{base_id, table_id, changes, changed_by, timestamp}` | 表更新 |
| `data:table_deleted` | `{base_id, table_id, changed_by, timestamp}` | 表删除 |

### 数据同步机制

#### 写操作数据流（实时协作启用时）

```
用户操作 → 前端视图组件
  │
  ├─[1]─► REST API 调用（如 PUT /api/records/:id）
  │         │
  │         ├─► 后端 Route → Service → DB 写入
  │         │                    │
  │         │                    └─► [条件] collaboration_service.broadcast_change()
  │         │                              │
  │         │                              └─► socketio.emit() → 房间内所有用户
  │         │
  │         └─► REST 响应返回操作结果
  │
  └─[2]─► 前端收到 WebSocket data:* 事件
            │
            └─► collaborationStore → tableStore/viewStore → 视图更新
```

#### 写操作数据流（实时协作禁用时）

```
用户操作 → 前端视图组件
  │
  └─► REST API 调用（如 PUT /api/records/:id）
        │
        ├─► 后端 Route → Service → DB 写入
        │                    │
        │                    └─► [跳过] collaboration_service 不调用
        │
        └─► REST 响应返回操作结果
              │
              └─► 前端 tableStore/viewStore → 本地状态更新 → 视图更新
```

#### 冲突解决流程

```
用户A提交变更 ──────────────────────────────────────┐
                                                     │
用户B提交变更 ──────────────────────────────────────┐│
                                                   ││
                    ┌──────────────────────────────▼▼
                    │  后端乐观锁检查 (updated_at)
                    │  ┌─────────────────────────────┐
                    │  │ updated_at 匹配？            │
                    │  │  ├─ 是 → 更新成功 → 广播变更 │
                    │  │  └─ 否 → 冲突处理            │
                    │  │      ├─ 不同字段 → 合并更新  │
                    │  │      ├─ 同字段 → LWW策略     │
                    │  │      └─ 记录已删 → 拒绝更新  │
                    │  └─────────────────────────────┘
                    └─────────────────────────────────
```

### 与其他模块的交互接口

| 交互模块 | 接口方式 | 说明 |
|---------|---------|------|
| 权限系统 (PermissionService) | 函数调用 | `room:join` 时调用 `can_access_base()` 验证权限；`lock:acquire` 时调用 `can_edit_base()` 验证编辑权限 |
| 记录服务 (RecordService) | 回调钩子 | 写操作完成后条件调用 `collaboration_service.broadcast_change()`；`update_record` 中增加乐观锁检查 |
| 字段服务 (FieldService) | 回调钩子 | 写操作完成后条件调用 `collaboration_service.broadcast_change()` |
| 视图服务 (ViewService) | 回调钩子 | 写操作完成后条件调用 `collaboration_service.broadcast_change()` |
| 表服务 (TableService) | 回调钩子 | 写操作完成后条件调用 `collaboration_service.broadcast_change()` |
| 记录历史 (RecordHistory) | 数据读取 | 冲突解决时从 RecordHistory 读取历史版本供用户选择恢复 |
| 操作日志 (OperationHistory) | 数据写入 | 协作相关操作（加入/离开/锁获取/释放）记录到 OperationHistory |
| 认证系统 (JWT) | 令牌验证 | WebSocket 连接时验证 JWT 令牌有效性 |

---

## ADDED Requirements

### Requirement: 实时协作功能启停控制

系统 SHALL 支持通过命令行参数控制实时协作功能的启用与禁用，默认禁用。

#### Scenario: 默认启动（禁用实时协作）
- **WHEN** 执行 `python run.py` 或 `python run.py run` 不带额外参数
- **THEN** 系统以传统 HTTP 模式启动，使用 `app.run()`
- **AND** 不初始化 SocketIO 扩展
- **AND** 不注册 SocketIO 事件处理器
- **AND** 不加载协作服务模块
- **AND** 所有 REST API 功能正常可用
- **AND** 前端检测到实时协作不可用，自动降级为 HTTP 模式

#### Scenario: 启用实时协作
- **WHEN** 执行 `python run.py --enable-realtime` 或 `python run.py -r`
- **THEN** 系统以 SocketIO 模式启动，使用 `socketio.run(app)`
- **AND** 初始化 SocketIO 扩展并配置 Redis 消息队列适配器
- **AND** 注册 SocketIO 事件处理器
- **AND** 加载协作服务模块
- **AND** 所有 REST API 功能正常可用
- **AND** WebSocket 实时协作功能可用

#### Scenario: Docker 部署启用实时协作
- **WHEN** 通过 Docker Compose 部署并设置环境变量 `ENABLE_REALTIME=true`
- **THEN** 等同于指定 `--enable-realtime` 参数
- **AND** gunicorn 使用 eventlet worker 启动

#### Scenario: Docker 部署禁用实时协作
- **WHEN** 通过 Docker Compose 部署且未设置 `ENABLE_REALTIME` 或设置为 `false`
- **THEN** 系统以传统模式启动
- **AND** gunicorn 可使用 sync worker（无需 eventlet）

#### Scenario: 无效参数处理
- **WHEN** 执行 `python run.py --enable-realtime --port 8080` 等带其他参数的命令
- **THEN** 正确解析所有参数
- **AND** `--enable-realtime` / `-r` 参数正确生效
- **AND** 其他参数（如 `--port`、`--host`）正常工作

### Requirement: 实时协作功能隔离

系统 SHALL 确保实时协作模块与核心业务模块完全解耦，禁用实时协作时系统所有其他功能完整可用。

#### Scenario: 禁用时核心 CRUD 功能
- **WHEN** 实时协作功能未启用
- **THEN** Base/Table/Field/Record/View 的 CRUD 操作全部正常
- **AND** 筛选、排序、分组功能正常
- **AND** 导入导出功能正常
- **AND** 分享链接功能正常
- **AND** 成员管理功能正常
- **AND** 仪表盘功能正常
- **AND** 表单视图功能正常

#### Scenario: 禁用时数据变更推送跳过
- **WHEN** 实时协作功能未启用且用户执行数据写操作
- **THEN** Service 层的变更推送调用被跳过（条件判断）
- **AND** 不产生任何 SocketIO 相关的日志或错误
- **AND** 写操作性能不受协作模块影响

#### Scenario: 禁用时前端降级
- **WHEN** 前端检测到后端实时协作不可用（WebSocket 连接失败或后端返回协作不可用标识）
- **THEN** 前端自动降级为传统 HTTP 模式
- **AND** 隐藏在线用户列表、编辑锁指示器等协作 UI 组件
- **AND** 数据操作通过 REST API 正常完成
- **AND** 不显示连接状态指示器

#### Scenario: 禁用时资源不加载
- **WHEN** 实时协作功能未启用
- **THEN** 后端不导入 `collaboration_service` 模块（延迟导入）
- **AND** 后端不创建 `collaboration_sessions` 数据库表（迁移文件存在但不执行，或执行时仅创建不使用）
- **AND** 前端不加载 `socket.io-client` 库（动态导入）
- **AND** 前端不初始化 `collaborationStore`

#### Scenario: 运行时切换（不要求热切换）
- **WHEN** 需要从禁用模式切换到启用模式
- **THEN** 需要重启服务并添加 `--enable-realtime` 参数
- **AND** 不要求支持运行时热切换

### Requirement: WebSocket 连接管理

系统 SHALL 建立基于 Socket.IO 的 WebSocket 长连接，支持多用户实时通信。

#### Scenario: 建立连接
- **WHEN** 用户打开一个共享 Base（且后端实时协作已启用）
- **THEN** 前端自动建立 Socket.IO 连接，携带 JWT 令牌进行身份验证
- **AND** 连接成功后自动加入该 Base 对应的协作房间（`base:{base_id}`）
- **AND** 连接超时设置为 30 秒

#### Scenario: 连接认证失败
- **WHEN** JWT 令牌无效或过期
- **THEN** 服务端拒绝连接，返回认证错误
- **AND** 前端尝试刷新令牌后重连

#### Scenario: 断线重连
- **WHEN** 网络中断导致 WebSocket 断开
- **THEN** 前端自动按指数退避策略重连（1s、2s、4s、8s、最大 30s）
- **AND** 重连成功后自动重新加入之前的协作房间
- **AND** 同步断线期间的数据变更

#### Scenario: 用户离开
- **WHEN** 用户关闭 Base 页面或浏览器标签
- **THEN** 前端发送 `room:leave` 事件
- **AND** 服务端将该用户从协作房间移除
- **AND** 广播用户离线状态给房间内其他用户

### Requirement: 协作房间管理

系统 SHALL 基于 Base 维度管理协作房间，同一 Base 的所有在线用户属于同一房间。

#### Scenario: 加入房间
- **WHEN** 用户打开一个 Base
- **THEN** 前端发送 `room:join` 事件，携带 `{base_id, user_id}`
- **AND** 服务端验证用户权限（至少为 viewer 角色）
- **AND** 权限验证通过后，将用户加入 `base:{base_id}` 房间
- **AND** 向房间内其他用户广播 `presence:user_joined` 事件

#### Scenario: 权限不足
- **WHEN** 用户无权访问该 Base
- **THEN** 服务端拒绝加入房间
- **AND** 前端显示权限不足提示

#### Scenario: 离开房间
- **WHEN** 用户主动离开 Base 页面
- **THEN** 前端发送 `room:leave` 事件
- **AND** 服务端将用户从房间移除
- **AND** 广播 `presence:user_left` 事件

### Requirement: 数据变更实时同步

系统 SHALL 在所有视图模式下实现数据变更的实时推送和同步。

#### Scenario: 单元格编辑同步
- **WHEN** 用户 A 在表格视图中编辑某个单元格
- **THEN** 变更通过 REST API 提交到后端
- **AND** 后端保存成功后，通过 WebSocket 广播 `data:record_updated` 事件到同房间所有用户
- **AND** 用户 B 的界面在 200ms 内更新显示新值
- **AND** 变更事件包含 `{table_id, record_id, field_id, old_value, new_value, changed_by, timestamp}`

#### Scenario: 记录增删同步
- **WHEN** 用户添加或删除一条记录
- **THEN** 后端广播 `data:record_created` 或 `data:record_deleted` 事件
- **AND** 所有在线用户的视图自动更新（表格视图新增/移除行，看板视图新增/移除卡片，日历视图新增/移除事件等）

#### Scenario: 字段变更同步
- **WHEN** 用户增删或修改字段（名称、类型、选项等）
- **THEN** 后端广播 `data:field_created`、`data:field_updated` 或 `data:field_deleted` 事件
- **AND** 所有在线用户的表头和对应列数据自动更新

#### Scenario: 视图配置同步
- **WHEN** 用户修改筛选、排序、分组、隐藏字段等视图配置
- **THEN** 后端广播 `data:view_updated` 事件
- **AND** 所有在线用户的视图配置自动同步更新

#### Scenario: 表结构变更同步
- **WHEN** 用户创建、删除或重命名数据表
- **THEN** 后端广播 `data:table_created`、`data:table_updated` 或 `data:table_deleted` 事件
- **AND** 所有在线用户的侧边栏表列表自动更新

#### Scenario: 看板视图拖拽同步
- **WHEN** 用户在看板视图中拖拽卡片到另一列
- **THEN** 对应记录的分组字段值更新
- **AND** 后端广播记录更新事件
- **AND** 其他用户的看板视图自动移动对应卡片

#### Scenario: 甘特图拖拽同步
- **WHEN** 用户在甘特图中拖拽任务条调整时间范围
- **THEN** 对应记录的日期字段值更新
- **AND** 后端广播记录更新事件
- **AND** 其他用户的甘特图自动更新任务条位置

### Requirement: 用户在线状态追踪（Presence）

系统 SHALL 实时追踪和展示同一 Base 内所有在线用户的状态。

#### Scenario: 在线用户列表
- **WHEN** 用户打开一个 Base
- **THEN** 界面顶部显示当前所有在线用户头像列表（最多显示 5 个，超出显示+N）
- **AND** 悬停头像显示用户昵称和当前所在视图

#### Scenario: 用户加入通知
- **WHEN** 新用户加入同一 Base
- **THEN** 界面顶部在线用户列表实时更新
- **AND** 显示轻量级 Toast 提示"XXX 加入了协作"

#### Scenario: 用户离开通知
- **WHEN** 用户离开 Base
- **THEN** 在线用户列表实时移除该用户
- **AND** 显示轻量级 Toast 提示"XXX 离开了协作"

#### Scenario: 当前视图位置同步
- **WHEN** 用户切换视图（如从表格视图切换到看板视图）
- **THEN** 前端发送 `presence:view_changed` 事件，携带 `{base_id, table_id, view_id, view_type}`
- **AND** 其他用户可在在线用户头像悬停时看到该用户当前所在视图

#### Scenario: 当前操作位置同步
- **WHEN** 用户选中某个单元格或记录
- **THEN** 前端发送 `presence:cell_selected` 事件，携带 `{table_id, record_id, field_id}`
- **AND** 其他用户在表格视图中可看到该单元格被高亮标记，显示操作者头像

### Requirement: 数据冲突解决机制

系统 SHALL 提供完善的数据冲突检测和解决机制，保证多人操作时的数据一致性。

#### Scenario: 乐观锁机制
- **WHEN** 用户提交数据变更
- **THEN** 后端检查记录的 `updated_at` 时间戳是否与客户端提交的一致
- **AND** 若一致则更新成功，递增版本号
- **AND** 若不一致则触发冲突处理流程

#### Scenario: 单元格级编辑锁
- **WHEN** 用户 A 正在编辑某个单元格（进入编辑状态）
- **THEN** 前端发送 `lock:acquire` 事件，携带 `{table_id, record_id, field_id}`
- **AND** 服务端检查该单元格是否已被其他用户锁定
- **AND** 若未锁定，授予锁并广播 `lock:acquired` 事件，其他用户看到该单元格显示"正在编辑"标记
- **AND** 若已锁定，返回锁冲突信息，前端提示"XXX 正在编辑此单元格"

#### Scenario: 编辑锁释放
- **WHEN** 用户完成或取消单元格编辑
- **THEN** 前端发送 `lock:release` 事件
- **AND** 服务端释放锁并广播 `lock:released` 事件
- **AND** 其他用户的"正在编辑"标记消失

#### Scenario: 编辑锁超时
- **WHEN** 用户持有编辑锁超过 60 秒无操作
- **THEN** 服务端自动释放锁
- **AND** 广播 `lock:released` 事件
- **AND** 原用户再次操作时提示"编辑锁已超时释放"

#### Scenario: 并发写入冲突
- **WHEN** 两个用户几乎同时修改同一记录的不同字段
- **THEN** 两个修改都应成功应用（字段级合并）
- **AND** 后端合并两个变更，保留各自修改的字段值
- **AND** 广播合并后的最终结果

#### Scenario: 同字段冲突
- **WHEN** 两个用户同时修改同一记录的同一字段（编辑锁失效的极端情况）
- **THEN** 采用"最后写入胜出"（Last Write Wins）策略
- **AND** 广播最终值，同时为被覆盖的用户显示轻量级冲突提示"你的修改已被 XXX 的操作覆盖"
- **AND** 被覆盖用户可通过 RecordHistory 查看和恢复自己的版本

#### Scenario: 行级操作冲突
- **WHEN** 用户 A 编辑某记录时，用户 B 删除了该记录
- **THEN** 删除操作生效
- **AND** 用户 A 收到 `data:record_deleted` 事件
- **AND** 前端关闭编辑状态，提示"该记录已被 XXX 删除"

### Requirement: 操作状态实时反馈

系统 SHALL 提供清晰的操作状态反馈，让用户了解其他协作者的实时动态。

#### Scenario: 协作者操作提示
- **WHEN** 其他用户进行数据操作（编辑单元格、添加记录、删除记录等）
- **THEN** 当前用户界面显示轻量级操作提示，如"XXX 正在编辑表格"
- **AND** 提示在 3 秒后自动消失

#### Scenario: 批量操作进度反馈
- **WHEN** 其他用户执行批量操作（批量删除、批量更新等）
- **THEN** 当前用户界面显示操作进度提示，如"XXX 正在批量更新 15 条记录"
- **AND** 操作完成后提示消失，数据自动刷新

#### Scenario: 连接状态指示
- **WHEN** WebSocket 连接状态变化
- **THEN** 界面显示连接状态指示器（已连接/正在重连/已断开）
- **AND** 断线时显示警告横幅"网络连接已断开，正在尝试重连..."
- **AND** 重连成功后显示"已重新连接"提示，并自动同步数据

#### Scenario: 未保存变更提示
- **WHEN** 用户有未提交的本地变更时网络断开
- **THEN** 界面显示"你有 N 项未同步的变更"
- **AND** 网络恢复后自动提交变更
- **AND** 若提交时发生冲突，触发冲突解决流程

### Requirement: 离线操作队列

系统 SHALL 支持短暂离线期间的本地操作缓存和重连后自动同步。

#### Scenario: 离线操作缓存
- **WHEN** 网络断开时用户继续操作
- **THEN** 操作缓存在本地队列中，按时间顺序排列
- **AND** 每项操作记录类型、目标资源、变更内容、时间戳
- **AND** 界面显示"离线模式"标识和待同步操作数量

#### Scenario: 重连后同步
- **WHEN** 网络恢复并重新建立 WebSocket 连接
- **THEN** 前端按顺序提交离线队列中的操作
- **AND** 服务端逐项处理，遇到冲突时触发冲突解决流程
- **AND** 同步完成后清除本地队列

#### Scenario: 离线操作数量限制
- **WHEN** 离线队列中的操作超过 100 项
- **THEN** 提示用户"离线操作过多，建议恢复网络连接后继续"
- **AND** 阻止新的写操作，仅允许查看

### Requirement: 性能优化

系统 SHALL 满足实时协作场景下的性能指标要求。

#### Scenario: 消息延迟
- **WHEN** 用户执行数据操作
- **THEN** 从操作完成到其他用户看到变更的端到端延迟 < 500ms（同区域网络）
- **AND** 单元格编辑的端到端延迟 < 300ms

#### Scenario: 消息吞吐量
- **WHEN** 同一 Base 有 50 个用户同时操作
- **THEN** 系统应能处理每秒 200 条以上的变更消息
- **AND** 消息不丢失、不乱序

#### Scenario: 连接数支持
- **WHEN** 系统运行时
- **THEN** 单个服务节点支持至少 500 个并发 WebSocket 连接
- **AND** 每个协作房间支持至少 50 个同时在线用户

#### Scenario: 消息压缩
- **WHEN** 传输大量数据变更（如批量操作）
- **THEN** WebSocket 消息使用压缩传输
- **AND** 批量操作合并为单条消息广播，避免消息风暴

#### Scenario: 增量更新
- **WHEN** 记录部分字段变更
- **THEN** 仅传输变更的字段（增量更新），而非整条记录
- **AND** 减少网络带宽占用和客户端处理开销

#### Scenario: 禁用模式零开销
- **WHEN** 实时协作功能未启用
- **THEN** 核心业务操作的性能不受任何影响
- **AND** 不存在因协作模块导致的额外延迟或资源消耗

### Requirement: 安全性

系统 SHALL 确保实时协作通信的安全性。

#### Scenario: 连接认证
- **WHEN** 客户端建立 WebSocket 连接
- **THEN** 必须携带有效的 JWT 令牌
- **AND** 服务端验证令牌后才允许连接

#### Scenario: 房间权限验证
- **WHEN** 用户尝试加入协作房间
- **THEN** 服务端验证用户对该 Base 的访问权限
- **AND** 无权限用户无法接收房间内的任何消息

#### Scenario: 操作权限验证
- **WHEN** 用户通过 WebSocket 发送操作请求（如编辑锁获取）
- **THEN** 服务端验证用户的操作权限（editor 及以上才能编辑）
- **AND** viewer 角色用户只能接收数据，不能发起变更

#### Scenario: 消息隔离
- **WHEN** 数据变更发生
- **THEN** 变更消息仅广播到对应 Base 的协作房间
- **AND** 不同 Base 的用户无法接收彼此的消息

#### Scenario: 输入验证
- **WHEN** 收到 WebSocket 事件
- **THEN** 服务端验证所有输入参数的类型和格式
- **AND** 拒绝格式不正确的消息，防止注入攻击

### Requirement: 协作会话数据模型

系统 SHALL 新增 `collaboration_sessions` 数据表存储协作会话信息。

#### collaboration_sessions 表
- id: UUID 主键
- base_id: 外键关联 bases 表
- user_id: 外键关联 users 表
- socket_id: 当前 Socket 连接 ID
- current_table_id: 当前查看的表 ID（可选）
- current_view_id: 当前查看的视图 ID（可选）
- current_view_type: 当前视图类型（table/kanban/calendar/gantt/form/gallery）
- locked_cells: JSON，存储当前用户持有的编辑锁 `[{record_id, field_id, acquired_at}]`
- joined_at: 加入房间时间
- last_active_at: 最后活跃时间
- is_active: 是否在线（Boolean）

### Requirement: 前端协作可用性探测

系统 SHALL 在前端实现后端实时协作可用性的自动探测机制。

#### Scenario: 启动时探测
- **WHEN** 前端应用加载并用户打开一个 Base
- **THEN** 前端尝试建立 Socket.IO 连接
- **AND** 若连接成功，启用实时协作功能，显示协作 UI
- **AND** 若连接失败（后端未启用实时协作），自动降级为 HTTP 模式，隐藏协作 UI

#### Scenario: 后端状态 API
- **WHEN** 前端需要确认后端实时协作是否可用
- **THEN** 可通过 `GET /api/realtime/status` 接口查询
- **AND** 返回 `{enabled: true/false, socket_url: "ws://..."}` 
- **AND** 该接口在实时协作禁用时也可用（返回 `enabled: false`）

#### Scenario: 优雅降级
- **WHEN** 实时协作从可用变为不可用（如后端重启且未启用实时协作）
- **THEN** 前端检测到 WebSocket 断开后不再重连
- **AND** 隐藏协作 UI 组件
- **AND** 数据操作继续通过 REST API 正常完成

## MODIFIED Requirements

### Requirement: 后端启动方式

系统 SHALL 支持两种启动方式，通过命令行参数控制。

- 默认模式：`python run.py` → 使用 `app.run(host, port)`，不启动 WebSocket
- 实时协作模式：`python run.py --enable-realtime` 或 `python run.py -r` → 使用 `socketio.run(app, host, port)`，启动 WebSocket
- 环境变量支持：`ENABLE_REALTIME=true` 等同于 `--enable-realtime`
- Docker 部署：通过 `ENABLE_REALTIME` 环境变量控制

### Requirement: RecordService 数据变更推送

系统 SHALL 在 RecordService 的写操作（create、update、delete）完成后，条件性地通过 SocketIO 广播变更事件。

- 仅当实时协作功能启用时，才调用 `collaboration_service.broadcast_change()`
- 判断方式：通过 `app.config['REALTIME_ENABLED']` 或全局标志位
- `create_record` 完成后条件广播 `data:record_created`
- `update_record` 完成后条件广播 `data:record_updated`
- `delete_record` 完成后条件广播 `data:record_deleted`
- 广播消息需包含变更详情和操作者信息
- 禁用实时协作时，这些调用被完全跳过，不影响原有逻辑

### Requirement: 前端数据流

系统 SHALL 根据实时协作是否启用来决定前端数据更新路径。

- **实时协作启用时**：写操作先调用后端 API，成功后由 WebSocket 推送更新到所有客户端（包括操作者自身）；读操作优先使用本地缓存，WebSocket 推送时更新缓存；视图组件监听 WebSocket 事件更新数据
- **实时协作禁用时**：保持原有数据流不变，写操作通过 REST API 完成后直接更新本地状态；视图组件通过 Store 的响应式机制更新

## REMOVED Requirements

无
