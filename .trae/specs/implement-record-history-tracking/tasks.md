# Tasks

## 第一阶段：后端开发

- [x] **Task 1**: 创建数据变更历史模型
  - [x] Subtask 1.1: 创建 `smarttable-backend/app/models/record_history.py` 模型文件
  - [x] Subtask 1.2: 定义 `RecordHistory` 模型，包含字段：id, record_id, table_id, action, changed_by, changed_at, changes, snapshot
  - [ ] Subtask 1.3: 创建数据库迁移脚本

- [x] **Task 2**: 修改记录服务，添加历史记录逻辑
  - [x] Subtask 2.1: 修改 `smarttable-backend/app/services/record_service.py` 中的 `create_record` 方法，在创建记录后保存历史记录
  - [x] Subtask 2.2: 修改 `update_record` 方法，在更新记录前获取旧值，更新后保存变更历史
  - [x] Subtask 2.3: 修改 `delete_record` 方法，在删除记录前保存历史记录

- [x] **Task 3**: 新增变更历史查询接口
  - [x] Subtask 3.1: 在 `smarttable-backend/app/routes/records.py` 中添加 `GET /api/records/<record_id>/history` 路由
  - [x] Subtask 3.2: 实现分页查询逻辑，支持 page 和 size 参数
  - [x] Subtask 3.3: 按时间倒序返回结果

## 第二阶段：前端开发

- [x] **Task 4**: 创建变更历史 API 服务
  - [x] Subtask 4.1: 创建 `smart-table/src/services/api/recordHistoryApiService.ts` 文件
  - [x] Subtask 4.2: 定义 `getRecordHistory(recordId, page, size)` 方法
  - [x] Subtask 4.3: 定义 TypeScript 类型接口 `RecordHistory`, `HistoryChange`

- [x] **Task 5**: 创建变更历史查看组件
  - [x] Subtask 5.1: 创建 `smart-table/src/components/dialogs/RecordHistoryDrawer.vue` 组件
  - [x] Subtask 5.2: 实现抽屉布局，包含标题、历史列表、分页器
  - [x] Subtask 5.3: 实现历史记录项展示：变更人信息、时间、操作类型、字段对比
  - [x] Subtask 5.4: 实现分页功能

- [x] **Task 6**: 修改记录详情抽屉，添加历史查看入口
  - [x] Subtask 6.1: 在 `RecordDetailDrawer.vue` 中添加"变更历史"按钮
  - [x] Subtask 6.2: 点击按钮打开 `RecordHistoryDrawer`
  - [x] Subtask 6.3: 传递当前记录 ID 给历史组件

## 第三阶段：验证测试

- [ ] **Task 7**: 功能验证
  - [ ] Subtask 7.1: 验证创建记录时是否生成历史记录
  - [ ] Subtask 7.2: 验证更新记录时是否正确记录变更字段
  - [ ] Subtask 7.3: 验证删除记录时是否保存快照
  - [ ] Subtask 7.4: 验证历史查看界面是否正确显示数据
  - [ ] Subtask 7.5: 验证分页功能是否正常工作

# Task Dependencies

- Task 1 必须在 Task 2 和 Task 3 之前完成
- Task 2 和 Task 3 可以并行开发
- Task 4 必须在 Task 5 之前完成
- Task 5 必须在 Task 6 之前完成
- Task 7 依赖于所有开发任务完成
