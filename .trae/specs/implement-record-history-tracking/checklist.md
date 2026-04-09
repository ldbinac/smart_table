# Checklist

## 后端实现

- [x] RecordHistory 模型已创建，包含所有必要字段
- [ ] 数据库迁移脚本已执行
- [x] 创建记录时自动生成历史记录
- [x] 更新记录时正确记录变更字段（旧值/新值）
- [x] 删除记录时保存数据快照
- [x] GET /api/records/{record_id}/history 接口已实现
- [x] 接口支持分页参数（page, size）
- [x] 返回结果按时间倒序排列

## 前端实现

- [x] recordHistoryApiService.ts 已创建
- [x] TypeScript 类型接口已定义
- [x] RecordHistoryDrawer.vue 组件已创建
- [x] 历史记录项正确展示变更人信息
- [x] 历史记录项正确展示变更时间（精确到秒）
- [x] 历史记录项正确展示操作类型
- [x] 历史记录项正确展示字段变更对比（旧值 → 新值）
- [x] 分页功能正常工作
- [x] RecordDetailDrawer.vue 已添加"变更历史"入口
- [x] 点击入口正确打开历史查看界面

## 功能验证

- [ ] 创建记录后能在历史中看到 CREATE 记录
- [ ] 更新字段后能在历史中看到 UPDATE 记录及字段变化
- [ ] 删除记录前能在历史中看到 DELETE 记录及快照
- [ ] 历史列表按时间倒序排列
- [ ] 分页器在记录多时正常工作
- [ ] 界面展示符合设计要求
