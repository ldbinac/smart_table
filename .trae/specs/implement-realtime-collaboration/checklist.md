# 实时协作更新功能验证检查清单

## 启动参数与功能隔离

- [ ] `run.py` 支持 `--enable-realtime` / `-r` 命令行参数解析
- [ ] `run.py` 支持 `ENABLE_REALTIME` 环境变量
- [ ] 默认启动（`python run.py`）使用 `app.run()`，不启动 WebSocket
- [ ] 启用实时协作（`python run.py --enable-realtime`）使用 `socketio.run(app)`
- [ ] `app/config.py` 包含 `REALTIME_ENABLED` 配置项
- [ ] `app/__init__.py` 根据 `REALTIME_ENABLED` 条件初始化 SocketIO 扩展
- [ ] `app/__init__.py` 根据 `REALTIME_ENABLED` 条件注册 SocketIO 事件处理器
- [ ] `app/extensions.py` SocketIO 的 `init_app` 为条件调用
- [ ] `GET /api/realtime/status` 接口在两种模式下均可用，返回正确的 `enabled` 状态
- [ ] Docker Compose 配置支持 `ENABLE_REALTIME` 环境变量
- [ ] Docker 部署时 gunicorn worker 类型根据 `ENABLE_REALTIME` 动态选择

## 功能隔离验证（禁用模式）

- [ ] 禁用实时协作时，后端不导入 `collaboration_service` 模块（延迟导入）
- [ ] 禁用实时协作时，Service 层不调用任何 SocketIO 相关方法
- [ ] 禁用实时协作时，不产生任何 SocketIO 相关的日志或错误
- [ ] 禁用实时协作时，核心业务操作性能不受影响（零开销）
- [ ] 禁用实时协作时，前端不加载 `socket.io-client` 库（动态导入）
- [ ] 禁用实时协作时，前端不初始化 `collaborationStore`
- [ ] 禁用实时协作时，协作 UI 组件（在线用户、编辑锁指示器等）不显示
- [ ] 禁用实时协作时，前端数据操作通过 REST API 正常完成

## 禁用模式下核心功能完整性

- [ ] Base CRUD 操作正常
- [ ] Table CRUD 操作正常
- [ ] Field CRUD 操作正常
- [ ] Record CRUD 操作正常
- [ ] View CRUD 操作正常
- [ ] 筛选功能正常
- [ ] 排序功能正常
- [ ] 分组功能正常
- [ ] 导入导出功能正常
- [ ] 分享链接功能正常
- [ ] 成员管理功能正常
- [ ] 仪表盘功能正常
- [ ] 表单视图功能正常
- [ ] 看板视图功能正常
- [ ] 日历视图功能正常
- [ ] 甘特图视图功能正常

## 后端 SocketIO 基础设施

- [ ] `extensions.py` 中 SocketIO 配置了 Redis 消息队列适配器，支持多 worker 模式
- [ ] `config.py` 包含 SocketIO 相关配置项（消息队列、ping 超时、ping 间隔）
- [ ] `socketio_events.py` 事件注册文件已创建并在 `__init__.py` 中条件注册

## 后端协作服务

- [ ] `CollaborationSession` 数据模型已创建，字段完整（id, base_id, user_id, socket_id, current_table_id, current_view_id, current_view_type, locked_cells, joined_at, last_active_at, is_active）
- [ ] 数据库迁移文件已生成，`collaboration_sessions` 表可正确创建
- [ ] `collaboration_service.py` 实现了房间管理（加入/离开/获取在线用户）
- [ ] `collaboration_service.py` 实现了 Presence 服务（在线状态、视图位置、操作位置同步）
- [ ] `collaboration_service.py` 实现了编辑锁管理（获取/释放/超时释放/查询状态）
- [ ] `collaboration_service.py` 实现了数据变更广播（构建消息、按房间广播、增量更新）
- [ ] `collaboration_service.py` 实现了 `broadcast_if_enabled()` 守卫方法，封装条件判断

## 后端 SocketIO 事件处理

- [ ] 连接认证事件 `connect` 正确验证 JWT 令牌，无效令牌拒绝连接
- [ ] 房间管理事件 `room:join` 验证用户权限后加入房间，广播 Presence 变更
- [ ] 房间管理事件 `room:leave` 正确移除用户，广播离线通知
- [ ] Presence 事件 `presence:view_changed` 和 `presence:cell_selected` 正确更新和广播用户位置
- [ ] 编辑锁事件 `lock:acquire` 正确处理锁获取和冲突检测
- [ ] 编辑锁事件 `lock:release` 正确释放锁并广播
- [ ] 断开连接 `disconnect` 正确清理会话、释放编辑锁、广播离线

## 后端数据变更推送

- [ ] `record_service.py` 的 create/update/delete 操作完成后条件广播对应事件
- [ ] `field_service.py` 的增删改操作完成后条件广播对应事件
- [ ] `view_service.py` 的配置变更后条件广播对应事件
- [ ] `table_service.py` 的增删改操作完成后条件广播对应事件
- [ ] `update_record` 实现了乐观锁机制，检查 `updated_at` 时间戳
- [ ] 所有广播调用使用延迟导入，禁用时不触发模块加载

## 前端 Socket.IO 客户端

- [ ] `socket.io-client` 依赖已安装
- [ ] `socketClient.ts` 封装了连接管理（JWT 认证、断线重连、指数退避）
- [ ] `eventTypes.ts` 定义了所有 WebSocket 事件的 TypeScript 类型接口
- [ ] `eventEmitter.ts` 实现了发布-订阅模式的事件管理
- [ ] `socketClient.ts` 实现了动态导入——仅在后端实时协作可用时加载

## 前端协作状态管理与功能降级

- [ ] `collaborationStore.ts` 管理在线用户列表、编辑锁状态、连接状态、离线操作队列
- [ ] `collaborationStore.ts` 包含 `isRealtimeAvailable` 状态标识
- [ ] `useRealtimeCollaboration.ts` 封装了自动连接/断开、房间管理、事件监听、数据同步
- [ ] `useRealtimeCollaboration.ts` 实现了前端可用性探测（调用 `GET /api/realtime/status`）
- [ ] 离线操作队列实现了缓存、顺序管理、数量限制（100项）、重连后自动提交
- [ ] 功能降级逻辑正确——`isRealtimeAvailable=false` 时隐藏协作 UI、跳过 WebSocket 事件监听

## 前端视图层实时更新

- [ ] `tableStore.ts` 条件接入 WebSocket 数据变更事件
- [ ] `viewStore.ts` 条件接入视图配置变更事件
- [ ] `TableView.vue` 条件监听实时数据变更事件，实现单元格值更新、行增删、列增删
- [ ] `KanbanView.vue` 条件监听记录变更事件，实现卡片增删和跨列移动
- [ ] `CalendarView.vue` 条件监听记录变更事件，实现日历事件增删和位置更新
- [ ] `GanttView.vue` 条件监听记录变更事件，实现任务条位置和进度更新
- [ ] `FormView.vue` 和 `GalleryView.vue` 条件监听数据变更事件

## 前端 Presence UI

- [ ] `OnlineUsers.vue` 显示在线用户头像列表（最多5个，超出+N），实时协作不可用时隐藏
- [ ] `CellEditingIndicator.vue` 在表格视图中显示其他用户正在编辑的单元格标记
- [ ] `ConnectionStatusBar.vue` 显示 WebSocket 连接状态指示器，实时协作不可用时隐藏
- [ ] `CollaborationToast.vue` 显示协作者操作提示
- [ ] Presence 组件通过 `v-if="collaborationStore.isRealtimeAvailable"` 条件集成到 `Base.vue`

## 前端冲突解决 UI

- [ ] `ConflictDialog.vue` 冲突提示对话框，显示冲突详情和解决方案选项
- [ ] 冲突检测逻辑正确——收到覆盖通知时弹出冲突对话框
- [ ] 编辑锁交互正确——获取锁失败时提示、锁超时释放时通知

## 通信协议验证

- [ ] 连接认证事件协议实现正确（JWT via Query）
- [ ] 房间管理事件协议实现正确（`room:join`/`room:leave`）
- [ ] Presence 事件协议实现正确（`presence:view_changed`/`presence:cell_selected`/`presence:user_joined`/`presence:user_left`）
- [ ] 编辑锁事件协议实现正确（`lock:acquire`/`lock:release`/`lock:acquired`/`lock:released`）
- [ ] 数据变更事件协议实现正确（`data:record_created`/`data:record_updated`/`data:record_deleted` 等）
- [ ] 消息格式符合协议定义（JSON 格式、字段完整）

## 性能验证

- [ ] 单元格编辑端到端延迟 < 300ms（同区域网络）
- [ ] 数据变更端到端延迟 < 500ms（同区域网络）
- [ ] 50 用户同时操作时系统稳定，消息不丢失不乱序
- [ ] 增量更新仅传输变更字段，非整条记录
- [ ] 禁用模式下核心业务操作性能零开销

## 安全性验证

- [ ] WebSocket 连接必须携带有效 JWT 令牌
- [ ] 房间加入需验证用户对 Base 的访问权限
- [ ] 编辑操作需验证用户角色为 editor 及以上
- [ ] 消息隔离——不同 Base 的用户无法接收彼此的消息
- [ ] WebSocket 事件输入参数验证正确，防止注入攻击

## 启用模式集成测试

- [ ] 多浏览器标签页实时同步测试通过
- [ ] 网络断开/恢复场景测试通过（断线重连、离线操作队列）
- [ ] 并发编辑冲突场景测试通过（乐观锁、编辑锁、冲突解决）
- [ ] 后端 SocketIO 单元测试通过
- [ ] 前端协作 Store 和 Composable 单元测试通过

## 启动参数测试

- [ ] `python run.py` 默认启动——不启用实时协作，所有 REST API 正常
- [ ] `python run.py --enable-realtime` 启动——启用实时协作，WebSocket 可连接
- [ ] `python run.py -r` 简写参数——与 `--enable-realtime` 等效
- [ ] 环境变量 `ENABLE_REALTIME=true`——与命令行参数等效
- [ ] 从禁用模式重启到启用模式——功能正确切换
- [ ] Docker 部署下 `ENABLE_REALTIME` 环境变量的两种模式均正常
