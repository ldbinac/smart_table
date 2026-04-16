# Tasks

- [x] Task 1: 后端启动参数与功能隔离机制
  - [x] SubTask 1.1: 修改 `run.py`，添加 `argparse` 命令行参数解析，支持 `--enable-realtime` / `-r` 参数和环境变量 `ENABLE_REALTIME`
  - [x] SubTask 1.2: 修改 `run.py` 启动逻辑——默认使用 `app.run()`，指定 `--enable-realtime` 时使用 `socketio.run(app)`
  - [x] SubTask 1.3: 修改 `app/config.py`，添加 `REALTIME_ENABLED` 配置项
  - [x] SubTask 1.4: 修改 `app/__init__.py` 的 `create_app()`，条件初始化 SocketIO
  - [x] SubTask 1.5: 修改 `app/extensions.py`，SocketIO `init_app` 条件调用
  - [x] SubTask 1.6: 添加 `GET /api/realtime/status` 接口
  - [x] SubTask 1.7: 修改 Docker Compose 配置，添加 `ENABLE_REALTIME` 环境变量支持

- [x] Task 2: 后端 SocketIO 基础设施搭建
  - [x] SubTask 2.1: 增强 `extensions.py` 中 SocketIO 配置
  - [x] SubTask 2.2: 在 `app/config.py` 中添加 SocketIO 相关配置项
  - [x] SubTask 2.3: 创建 `app/routes/socketio_events.py`
  - [x] SubTask 2.4: 在 `app/__init__.py` 中条件注册 SocketIO 事件处理器

- [x] Task 3: 后端协作服务层实现
  - [x] SubTask 3.1: 创建 `CollaborationSession` 数据模型
  - [x] SubTask 3.2: 创建数据库迁移文件
  - [x] SubTask 3.3: 实现协作房间管理
  - [x] SubTask 3.4: 实现 Presence 服务
  - [x] SubTask 3.5: 实现编辑锁管理
  - [x] SubTask 3.6: 实现数据变更广播服务
  - [x] SubTask 3.7: 实现 `broadcast_if_enabled()` 守卫方法

- [x] Task 4: 后端 SocketIO 事件处理器实现
  - [x] SubTask 4.1: 实现连接认证事件 `connect`
  - [x] SubTask 4.2: 实现房间管理事件 `room:join` 和 `room:leave`
  - [x] SubTask 4.3: 实现 Presence 事件 `presence:view_changed` 和 `presence:cell_selected`
  - [x] SubTask 4.4: 实现编辑锁事件 `lock:acquire` 和 `lock:release`
  - [x] SubTask 4.5: 实现断开连接处理 `disconnect`

- [x] Task 5: 后端数据变更推送集成（条件调用）
  - [x] SubTask 5.1: 修改 `record_service.py`，条件调用广播方法
  - [x] SubTask 5.2: 修改 `field_service.py`，条件调用广播方法
  - [x] SubTask 5.3: 修改 `view_service.py`，条件调用广播方法
  - [x] SubTask 5.4: 修改 `table_service.py`，条件调用广播方法
  - [x] SubTask 5.5: 实现乐观锁机制（`expected_updated_at` 参数 + `ConflictError` 409）
  - [x] SubTask 5.6: 所有广播调用使用延迟导入

- [x] Task 6: 前端 Socket.IO 客户端集成
  - [x] SubTask 6.1: 安装 `socket.io-client` 依赖
  - [x] SubTask 6.2: 创建 `socketClient.ts`
  - [x] SubTask 6.3: 创建 `eventTypes.ts`
  - [x] SubTask 6.4: 创建 `eventEmitter.ts`
  - [x] SubTask 6.5: 实现动态导入

- [x] Task 7: 前端协作状态管理与功能降级
  - [x] SubTask 7.1: 创建 `collaborationStore.ts`
  - [x] SubTask 7.2: 创建 `useRealtimeCollaboration.ts`
  - [x] SubTask 7.3: 实现前端可用性探测
  - [x] SubTask 7.4: 实现离线操作队列
  - [x] SubTask 7.5: 实现前端功能降级逻辑

- [x] Task 8: 前端视图层实时更新集成（条件接入）
  - [x] SubTask 8.1: 修改 `tableStore.ts`，条件接入 WebSocket 数据变更事件
  - [x] SubTask 8.2: 修改 `viewStore.ts`，条件接入视图配置变更事件
  - [x] SubTask 8.3: 修改 `TableView.vue`
  - [x] SubTask 8.4: 修改 `KanbanView.vue`
  - [x] SubTask 8.5: 修改 `CalendarView.vue`
  - [x] SubTask 8.6: 修改 `GanttView.vue`
  - [x] SubTask 8.7: 修改 `FormView.vue` 和 `GalleryView.vue`

- [x] Task 9: 前端 Presence UI 组件（条件显示）
  - [x] SubTask 9.1: 创建 `OnlineUsers.vue`
  - [x] SubTask 9.2: 创建 `CellEditingIndicator.vue`
  - [x] SubTask 9.3: 创建 `ConnectionStatusBar.vue`
  - [x] SubTask 9.4: 创建 `CollaborationToast.vue`
  - [x] SubTask 9.5: 将 Presence 组件条件集成到 `Base.vue`

- [x] Task 10: 前端冲突解决 UI
  - [x] SubTask 10.1: 创建 `ConflictDialog.vue`
  - [x] SubTask 10.2: 实现冲突检测逻辑
  - [x] SubTask 10.3: 实现编辑锁交互

- [ ] Task 11: 禁用实时协作模式下的功能完整性测试
  - [ ] SubTask 11.1: 编写后端测试——验证默认启动后所有 REST API 正常工作
  - [ ] SubTask 11.2: 编写后端测试——验证禁用模式下 Service 层不调用 `collaboration_service`
  - [ ] SubTask 11.3: 编写后端测试——验证 `GET /api/realtime/status` 在禁用模式下返回 `{enabled: false}`
  - [ ] SubTask 11.4: 编写前端测试——验证禁用模式下前端不加载 `socket.io-client`
  - [ ] SubTask 11.5: 编写前端测试——验证禁用模式下所有视图组件的数据操作通过 REST API 正常完成
  - [ ] SubTask 11.6: 手动验证——禁用模式下核心功能全部正常

- [ ] Task 12: 启用实时协作模式下的功能测试
  - [ ] SubTask 12.1: 编写后端 SocketIO 事件处理器单元测试
  - [ ] SubTask 12.2: 编写后端协作服务单元测试
  - [ ] SubTask 12.3: 编写前端协作 Store 和 Composable 单元测试
  - [ ] SubTask 12.4: 进行多浏览器标签页手动集成测试
  - [ ] SubTask 12.5: 进行网络断开/恢复场景测试
  - [ ] SubTask 12.6: 进行并发编辑冲突场景测试

- [ ] Task 13: 启动参数与模式切换测试
  - [ ] SubTask 13.1: 测试 `python run.py` 默认启动
  - [ ] SubTask 13.2: 测试 `python run.py --enable-realtime` 启动
  - [ ] SubTask 13.3: 测试 `python run.py -r` 简写参数
  - [ ] SubTask 13.4: 测试环境变量 `ENABLE_REALTIME=true`
  - [ ] SubTask 13.5: 测试从禁用模式重启到启用模式
  - [ ] SubTask 13.6: 测试 Docker 部署下 `ENABLE_REALTIME` 环境变量的两种模式

# Task Dependencies

- [Task 2] depends on [Task 1]
- [Task 3] depends on [Task 2]
- [Task 4] depends on [Task 3]
- [Task 5] depends on [Task 3]
- [Task 6] depends on [Task 1]
- [Task 7] depends on [Task 6]
- [Task 8] depends on [Task 7]
- [Task 9] depends on [Task 7]
- [Task 10] depends on [Task 7]
- [Task 11] depends on [Task 1, Task 5, Task 8]
- [Task 12] depends on [Task 4, Task 5, Task 8, Task 9, Task 10]
- [Task 13] depends on [Task 1]

# Parallelizable Work

- [Task 11] 和 [Task 12] 可并行
- [Task 13] 可独立进行
