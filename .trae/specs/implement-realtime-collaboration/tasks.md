# Tasks

- [ ] Task 1: 后端启动参数与功能隔离机制
  - [ ] SubTask 1.1: 修改 `run.py`，添加 `argparse` 命令行参数解析，支持 `--enable-realtime` / `-r` 参数和环境变量 `ENABLE_REALTIME`
  - [ ] SubTask 1.2: 修改 `run.py` 启动逻辑——默认使用 `app.run()`，指定 `--enable-realtime` 时使用 `socketio.run(app)`
  - [ ] SubTask 1.3: 修改 `app/config.py`，添加 `REALTIME_ENABLED` 配置项（从命令行参数或环境变量读取）
  - [ ] SubTask 1.4: 修改 `app/__init__.py` 的 `create_app()`，根据 `REALTIME_ENABLED` 配置条件初始化 SocketIO 扩展和注册事件处理器
  - [ ] SubTask 1.5: 修改 `app/extensions.py`，将 SocketIO 的 `init_app` 改为条件调用（仅在 `REALTIME_ENABLED=True` 时初始化）
  - [ ] SubTask 1.6: 添加 `GET /api/realtime/status` 接口，返回 `{enabled: bool, socket_url: string|null}`，在两种模式下均可用
  - [ ] SubTask 1.7: 修改 Docker Compose 配置，添加 `ENABLE_REALTIME` 环境变量支持，gunicorn worker 类型根据该变量动态选择

- [ ] Task 2: 后端 SocketIO 基础设施搭建
  - [ ] SubTask 2.1: 增强 `extensions.py` 中 SocketIO 配置，添加 Redis 消息队列适配器（支持多 worker 模式），配置 `cors_allowed_origins`、`ping_timeout`、`ping_interval`
  - [ ] SubTask 2.2: 在 `app/config.py` 中添加 SocketIO 相关配置项（`SOCKETIO_MESSAGE_QUEUE`、`SOCKETIO_PING_TIMEOUT`、`SOCKETIO_PING_INTERVAL`）
  - [ ] SubTask 2.3: 创建 `app/routes/socketio_events.py`，实现 SocketIO 事件注册蓝图，包含连接认证、断开处理的基础框架
  - [ ] SubTask 2.4: 在 `app/__init__.py` 中条件注册 SocketIO 事件处理器（仅 `REALTIME_ENABLED=True` 时加载）

- [ ] Task 3: 后端协作服务层实现
  - [ ] SubTask 3.1: 创建 `app/models/collaboration_session.py`，定义 `CollaborationSession` 数据模型（id, base_id, user_id, socket_id, current_table_id, current_view_id, current_view_type, locked_cells, joined_at, last_active_at, is_active）
  - [ ] SubTask 3.2: 创建数据库迁移文件，添加 `collaboration_sessions` 表
  - [ ] SubTask 3.3: 创建 `app/services/collaboration_service.py`，实现协作房间管理（加入/离开房间、获取房间在线用户列表）
  - [ ] SubTask 3.4: 在 `collaboration_service.py` 中实现 Presence 服务（基于 Redis 的在线状态追踪、视图位置同步、操作位置同步）
  - [ ] SubTask 3.5: 在 `collaboration_service.py` 中实现编辑锁管理（获取锁、释放锁、锁超时自动释放、查询锁状态）
  - [ ] SubTask 3.6: 在 `collaboration_service.py` 中实现数据变更广播服务（构建变更消息、按房间广播、增量更新支持）
  - [ ] SubTask 3.7: 在 `collaboration_service.py` 中实现广播守卫方法 `broadcast_if_enabled()`，封装 `REALTIME_ENABLED` 条件判断，Service 层统一调用此方法

- [ ] Task 4: 后端 SocketIO 事件处理器实现
  - [ ] SubTask 4.1: 实现连接认证事件 `connect`——验证 JWT 令牌，认证成功后允许连接，失败则拒绝
  - [ ] SubTask 4.2: 实现房间管理事件 `room:join` 和 `room:leave`——权限验证、加入/离开房间、广播 Presence 变更
  - [ ] SubTask 4.3: 实现 Presence 事件 `presence:view_changed` 和 `presence:cell_selected`——更新用户位置信息、广播给房间内其他用户
  - [ ] SubTask 4.4: 实现编辑锁事件 `lock:acquire` 和 `lock:release`——锁获取/释放、冲突检测、广播锁状态变更
  - [ ] SubTask 4.5: 实现断开连接处理 `disconnect`——清理用户会话、释放所有编辑锁、广播用户离线

- [ ] Task 5: 后端数据变更推送集成（条件调用）
  - [ ] SubTask 5.1: 修改 `app/services/record_service.py`，在 `create_record`、`update_record`、`delete_record` 完成后条件调用 `collaboration_service.broadcast_if_enabled()`
  - [ ] SubTask 5.2: 修改 `app/services/field_service.py`，在字段增删改完成后条件调用广播方法
  - [ ] SubTask 5.3: 修改 `app/services/view_service.py`，在视图配置变更后条件调用广播方法
  - [ ] SubTask 5.4: 修改 `app/services/table_service.py`，在表增删改完成后条件调用广播方法
  - [ ] SubTask 5.5: 实现乐观锁机制——在 `update_record` 中检查 `updated_at` 时间戳，不一致时返回冲突错误（HTTP 409）
  - [ ] SubTask 5.6: 确保所有广播调用使用延迟导入（`from app.services.collaboration_service import ...`），禁用时不会触发模块加载

- [ ] Task 6: 前端 Socket.IO 客户端集成
  - [ ] SubTask 6.1: 安装 `socket.io-client` 依赖
  - [ ] SubTask 6.2: 创建 `smart-table/src/services/realtime/socketClient.ts`，封装 Socket.IO 连接管理（连接建立、JWT 认证、断线重连、指数退避策略）
  - [ ] SubTask 6.3: 创建 `smart-table/src/services/realtime/eventTypes.ts`，定义所有 WebSocket 事件的类型接口（入参和出参类型）
  - [ ] SubTask 6.4: 创建 `smart-table/src/services/realtime/eventEmitter.ts`，封装事件订阅/取消订阅的发布-订阅模式
  - [ ] SubTask 6.5: 在 `socketClient.ts` 中实现动态导入——仅在后端实时协作可用时加载 `socket.io-client`，否则返回 null 客户端

- [ ] Task 7: 前端协作状态管理与功能降级
  - [ ] SubTask 7.1: 创建 `smart-table/src/stores/collaborationStore.ts`，管理在线用户列表、编辑锁状态、连接状态、离线操作队列，包含 `isRealtimeAvailable` 状态标识
  - [ ] SubTask 7.2: 创建 `smart-table/src/composables/useRealtimeCollaboration.ts`，封装协作功能的 Composable——自动连接/断开、房间加入/离开、事件监听、数据同步
  - [ ] SubTask 7.3: 在 `useRealtimeCollaboration.ts` 中实现前端可用性探测——调用 `GET /api/realtime/status` 判断后端是否启用实时协作，据此决定是否初始化 Socket.IO 客户端
  - [ ] SubTask 7.4: 在 `collaborationStore.ts` 中实现离线操作队列——操作缓存、顺序管理、数量限制、重连后自动提交
  - [ ] SubTask 7.5: 实现前端功能降级逻辑——当 `isRealtimeAvailable=false` 时，隐藏协作 UI、跳过 WebSocket 事件监听、使用传统 REST 数据流

- [ ] Task 8: 前端视图层实时更新集成（条件接入）
  - [ ] SubTask 8.1: 修改 `smart-table/src/stores/tableStore.ts`，条件接入 WebSocket 数据变更事件——当实时协作可用时监听事件更新本地状态，否则保持原有 REST 响应更新逻辑
  - [ ] SubTask 8.2: 修改 `smart-table/src/stores/viewStore.ts`，条件接入视图配置变更事件
  - [ ] SubTask 8.3: 修改 `TableView.vue`，条件监听实时数据变更事件，实现单元格值更新、行增删、列增删的实时渲染
  - [ ] SubTask 8.4: 修改 `KanbanView.vue`，条件监听记录变更事件，实现卡片增删和跨列移动的实时渲染
  - [ ] SubTask 8.5: 修改 `CalendarView.vue`，条件监听记录变更事件，实现日历事件的实时增删和位置更新
  - [ ] SubTask 8.6: 修改 `GanttView.vue`，条件监听记录变更事件，实现任务条的实时位置和进度更新
  - [ ] SubTask 8.7: 修改 `FormView.vue` 和 `GalleryView.vue`，条件监听数据变更事件，实现实时更新

- [ ] Task 9: 前端 Presence UI 组件（条件显示）
  - [ ] SubTask 9.1: 创建 `smart-table/src/components/collaboration/OnlineUsers.vue`，显示在线用户头像列表（最多5个，超出+N），悬停显示详情；当实时协作不可用时隐藏
  - [ ] SubTask 9.2: 创建 `smart-table/src/components/collaboration/CellEditingIndicator.vue`，在表格视图中显示其他用户正在编辑的单元格标记（彩色边框+头像）
  - [ ] SubTask 9.3: 创建 `smart-table/src/components/collaboration/ConnectionStatusBar.vue`，显示 WebSocket 连接状态指示器（已连接/重连中/已断开）；当实时协作不可用时隐藏
  - [ ] SubTask 9.4: 创建 `smart-table/src/components/collaboration/CollaborationToast.vue`，显示协作者操作提示（加入/离开/编辑中等）
  - [ ] SubTask 9.5: 将 Presence 组件条件集成到 `Base.vue` 主页面中——通过 `v-if="collaborationStore.isRealtimeAvailable"` 控制显示

- [ ] Task 10: 前端冲突解决 UI
  - [ ] SubTask 10.1: 创建 `smart-table/src/components/collaboration/ConflictDialog.vue`，冲突提示对话框，显示冲突详情和解决方案选项
  - [ ] SubTask 10.2: 在 `useRealtimeCollaboration.ts` 中实现冲突检测逻辑——收到覆盖通知时弹出冲突对话框
  - [ ] SubTask 10.3: 在 `useRealtimeCollaboration.ts` 中实现编辑锁交互——获取锁失败时提示、锁超时释放时通知

- [ ] Task 11: 禁用实时协作模式下的功能完整性测试
  - [ ] SubTask 11.1: 编写后端测试——验证 `python run.py`（不带 `--enable-realtime`）启动后所有 REST API 正常工作
  - [ ] SubTask 11.2: 编写后端测试——验证禁用模式下 Service 层不调用 `collaboration_service`，不产生 SocketIO 相关错误
  - [ ] SubTask 11.3: 编写后端测试——验证 `GET /api/realtime/status` 在禁用模式下返回 `{enabled: false}`
  - [ ] SubTask 11.4: 编写前端测试——验证禁用模式下前端不加载 `socket.io-client`，不初始化 `collaborationStore`
  - [ ] SubTask 11.5: 编写前端测试——验证禁用模式下所有视图组件的数据操作通过 REST API 正常完成
  - [ ] SubTask 11.6: 手动验证——禁用模式下 Base/Table/Field/Record/View 的 CRUD、筛选排序分组、导入导出、分享链接、成员管理、仪表盘功能全部正常

- [ ] Task 12: 启用实时协作模式下的功能测试
  - [ ] SubTask 12.1: 编写后端 SocketIO 事件处理器单元测试（连接认证、房间管理、Presence、编辑锁）
  - [ ] SubTask 12.2: 编写后端协作服务单元测试（房间管理、锁管理、变更广播）
  - [ ] SubTask 12.3: 编写前端协作 Store 和 Composable 单元测试
  - [ ] SubTask 12.4: 进行多浏览器标签页手动集成测试——验证同一 Base 下两个标签页的实时同步
  - [ ] SubTask 12.5: 进行网络断开/恢复场景测试——验证断线重连和离线操作队列
  - [ ] SubTask 12.6: 进行并发编辑冲突场景测试——验证乐观锁、编辑锁、冲突解决流程

- [ ] Task 13: 启动参数与模式切换测试
  - [ ] SubTask 13.1: 测试 `python run.py` 默认启动——验证不启用实时协作，所有 REST API 正常
  - [ ] SubTask 13.2: 测试 `python run.py --enable-realtime` 启动——验证启用实时协作，WebSocket 可连接
  - [ ] SubTask 13.3: 测试 `python run.py -r` 简写参数——验证与 `--enable-realtime` 等效
  - [ ] SubTask 13.4: 测试环境变量 `ENABLE_REALTIME=true`——验证与命令行参数等效
  - [ ] SubTask 13.5: 测试从禁用模式重启到启用模式——验证功能正确切换
  - [ ] SubTask 13.6: 测试 Docker 部署下 `ENABLE_REALTIME` 环境变量的两种模式

# Task Dependencies

- [Task 2] depends on [Task 1] (SocketIO 基础设施依赖启动参数和条件初始化机制)
- [Task 3] depends on [Task 2] (协作服务依赖 SocketIO 基础设施)
- [Task 4] depends on [Task 3] (事件处理器依赖协作服务)
- [Task 5] depends on [Task 3] (数据变更推送依赖协作服务的广播功能)
- [Task 6] depends on [Task 1] (前端客户端依赖后端启动参数和状态 API)
- [Task 7] depends on [Task 6] (协作状态管理依赖 Socket.IO 客户端)
- [Task 8] depends on [Task 7] (视图层实时更新依赖协作状态管理)
- [Task 9] depends on [Task 7] (Presence UI 依赖协作状态管理)
- [Task 10] depends on [Task 7] (冲突解决 UI 依赖协作状态管理)
- [Task 11] depends on [Task 1, Task 5, Task 8] (禁用模式测试依赖功能隔离实现)
- [Task 12] depends on [Task 4, Task 5, Task 8, Task 9, Task 10] (启用模式测试依赖所有功能实现完成)
- [Task 13] depends on [Task 1] (启动参数测试依赖参数解析实现)

# Parallelizable Work

- [Task 1] 和 [Task 6] 可并行（后端启动参数和前端客户端可同时搭建，前端先实现动态导入框架）
- [Task 8, Task 9, Task 10] 可并行（视图更新、Presence UI、冲突解决 UI 相互独立）
- [Task 4] 和 [Task 5] 可并行（事件处理器和数据变更推送可同时开发）
- [Task 11] 和 [Task 12] 可并行（两种模式的测试可同时进行）
