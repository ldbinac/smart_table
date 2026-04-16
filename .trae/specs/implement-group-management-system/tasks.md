# Tasks

## 第一阶段：后端基础架构

- [ ] **Task 1**: 数据库模型设计与实现
  - [ ] Subtask 1.1: 在 `models.py` 中定义 Group 模型（含软删除、归档字段）
  - [ ] Subtask 1.2: 在 `models.py` 中定义 GroupMember 模型（含最后活动时间）
  - [ ] Subtask 1.3: 在 `models.py` 中定义 GroupInvitation 模型
  - [ ] Subtask 1.4: 在 `models.py` 中定义 GroupField 模型（含验证规则配置）
  - [ ] Subtask 1.5: 在 `models.py` 中定义 GroupRecord 模型（含乐观锁版本号）
  - [ ] Subtask 1.6: 在 `models.py` 中定义 GroupRecordVersion 模型
  - [ ] Subtask 1.7: 在 `models.py` 中定义 GroupView 模型
  - [ ] Subtask 1.8: 在 `models.py` 中定义 GroupActivity 模型
  - [ ] Subtask 1.9: 在 `models.py` 中定义 GroupComment 模型
  - [ ] Subtask 1.10: 在 `models.py` 中定义 Notification 模型
  - [ ] Subtask 1.11: 创建数据库迁移脚本
  - [ ] Subtask 1.12: 执行迁移创建表

- [ ] **Task 2**: 群组管理后端 API
  - [ ] Subtask 2.1: 实现创建群组接口 `POST /groups`（支持模板选择）
  - [ ] Subtask 2.2: 实现获取群组列表接口 `GET /groups`（支持筛选active/archived）
  - [ ] Subtask 2.3: 实现获取归档群组列表接口 `GET /groups/archived`
  - [ ] Subtask 2.4: 实现获取群组详情接口 `GET /groups/{group_id}`
  - [ ] Subtask 2.5: 实现更新群组接口 `PUT /groups/{group_id}`
  - [ ] Subtask 2.6: 实现归档群组接口 `POST /groups/{group_id}/archive`
  - [ ] Subtask 2.7: 实现恢复群组接口 `POST /groups/{group_id}/restore`
  - [ ] Subtask 2.8: 实现永久删除群组接口 `DELETE /groups/{group_id}`
  - [ ] Subtask 2.9: 实现转移群组所有权接口 `POST /groups/{group_id}/transfer`

- [ ] **Task 3**: 群组成员管理后端 API
  - [ ] Subtask 3.1: 实现获取成员列表接口 `GET /groups/{group_id}/members`（含在线状态）
  - [ ] Subtask 3.2: 实现邀请成员接口 `POST /groups/{group_id}/invitations`（支持批量）
  - [ ] Subtask 3.3: 实现生成邀请链接接口 `POST /groups/{group_id}/invitation-link`
  - [ ] Subtask 3.4: 实现接受邀请接口 `POST /invitations/{token}/accept`
  - [ ] Subtask 3.5: 实现拒绝邀请接口 `POST /invitations/{token}/reject`
  - [ ] Subtask 3.6: 实现更新成员角色接口 `PUT /groups/{group_id}/members/{member_id}`
  - [ ] Subtask 3.7: 实现移除成员接口 `DELETE /groups/{group_id}/members/{member_id}`
  - [ ] Subtask 3.8: 实现转移成员记录接口 `POST /groups/{group_id}/members/{member_id}/transfer-records`

## 第二阶段：后端业务逻辑

- [ ] **Task 4**: 群组字段管理后端 API
  - [ ] Subtask 4.1: 实现创建字段接口 `POST /groups/{group_id}/fields`
  - [ ] Subtask 4.2: 实现获取字段列表接口 `GET /groups/{group_id}/fields`
  - [ ] Subtask 4.3: 实现更新字段接口 `PUT /groups/{group_id}/fields/{field_id}`
  - [ ] Subtask 4.4: 实现删除字段接口 `DELETE /groups/{group_id}/fields/{field_id}`
  - [ ] Subtask 4.5: 实现字段排序接口 `PUT /groups/{group_id}/fields/order`
  - [ ] Subtask 4.6: 实现字段验证规则配置接口 `PUT /groups/{group_id}/fields/{field_id}/validation`

- [ ] **Task 5**: 群组记录管理后端 API
  - [ ] Subtask 5.1: 实现创建记录接口 `POST /groups/{group_id}/records`
  - [ ] Subtask 5.2: 实现获取记录列表接口 `GET /groups/{group_id}/records`（含筛选排序分页）
  - [ ] Subtask 5.3: 实现获取记录详情接口 `GET /groups/{group_id}/records/{record_id}`
  - [ ] Subtask 5.4: 实现更新记录接口 `PUT /groups/{group_id}/records/{record_id}`（含乐观锁）
  - [ ] Subtask 5.5: 实现删除记录接口 `DELETE /groups/{group_id}/records/{record_id}`
  - [ ] Subtask 5.6: 实现批量创建记录接口 `POST /groups/{group_id}/records/batch`
  - [ ] Subtask 5.7: 实现批量更新记录接口 `PUT /groups/{group_id}/records/batch`
  - [ ] Subtask 5.8: 实现批量删除记录接口 `DELETE /groups/{group_id}/records/batch`

- [ ] **Task 6**: 群组视图管理后端 API
  - [ ] Subtask 6.1: 实现创建视图接口 `POST /groups/{group_id}/views`
  - [ ] Subtask 6.2: 实现获取视图列表接口 `GET /groups/{group_id}/views`
  - [ ] Subtask 6.3: 实现获取视图详情接口 `GET /groups/{group_id}/views/{view_id}`
  - [ ] Subtask 6.4: 实现更新视图接口 `PUT /groups/{group_id}/views/{view_id}`
  - [ ] Subtask 6.5: 实现删除视图接口 `DELETE /groups/{group_id}/views/{view_id}`
  - [ ] Subtask 6.6: 实现设置默认视图接口 `PUT /groups/{group_id}/views/{view_id}/default`
  - [ ] Subtask 6.7: 实现复制视图接口 `POST /groups/{group_id}/views/{view_id}/duplicate`
  - [ ] Subtask 6.8: 实现视图共享设置接口 `PUT /groups/{group_id}/views/{view_id}/share`

- [ ] **Task 7**: 数据筛选排序后端 API
  - [ ] Subtask 7.1: 实现筛选条件解析器（支持多条件嵌套）
  - [ ] Subtask 7.2: 实现排序逻辑处理器（支持多字段排序）
  - [ ] Subtask 7.3: 实现分组逻辑处理器（支持多级分组）
  - [ ] Subtask 7.4: 实现分页查询接口（支持游标分页和偏移分页）
  - [ ] Subtask 7.5: 实现聚合统计接口（计数、求和、平均值、最大最小值）
  - [ ] Subtask 7.6: 实现快速筛选接口（我的记录、时间范围等）

- [ ] **Task 8**: 数据导入导出后端 API
  - [ ] Subtask 8.1: 实现 Excel 导入接口 `POST /groups/{group_id}/import/excel`
  - [ ] Subtask 8.2: 实现 Excel 导出接口 `GET /groups/{group_id}/export/excel`
  - [ ] Subtask 8.3: 实现 CSV 导入接口 `POST /groups/{group_id}/import/csv`
  - [ ] Subtask 8.4: 实现 CSV 导出接口 `GET /groups/{group_id}/export/csv`
  - [ ] Subtask 8.5: 实现 JSON 导入接口 `POST /groups/{group_id}/import/json`
  - [ ] Subtask 8.6: 实现 JSON 导出接口 `GET /groups/{group_id}/export/json`
  - [ ] Subtask 8.7: 实现字段映射配置解析和自动匹配
  - [ ] Subtask 8.8: 实现导入预览接口 `POST /groups/{group_id}/import/preview`
  - [ ] Subtask 8.9: 实现导出模板下载接口 `GET /groups/{group_id}/export/template`
  - [ ] Subtask 8.10: 实现导入历史查询接口 `GET /groups/{group_id}/import/history`

## 第三阶段：后端权限与协作

- [ ] **Task 9**: 群组权限验证系统
  - [ ] Subtask 9.1: 实现群组访问权限装饰器（检查成员身份和群组状态）
  - [ ] Subtask 9.2: 实现角色权限检查函数（owner/admin/editor/viewer）
  - [ ] Subtask 9.3: 实现操作权限检查装饰器（按操作类型检查）
  - [ ] Subtask 9.4: 在所有群组接口中添加权限验证
  - [ ] Subtask 9.5: 实现权限错误处理和响应
  - [ ] Subtask 9.6: 创建 `group_permission_service.py` 权限服务

- [ ] **Task 10**: 评论与@提及系统
  - [ ] Subtask 10.1: 实现创建评论接口 `POST /groups/{group_id}/records/{record_id}/comments`
  - [ ] Subtask 10.2: 实现获取评论列表接口 `GET /groups/{group_id}/records/{record_id}/comments`
  - [ ] Subtask 10.3: 实现更新评论接口 `PUT /groups/{group_id}/comments/{comment_id}`
  - [ ] Subtask 10.4: 实现删除评论接口 `DELETE /groups/{group_id}/comments/{comment_id}`
  - [ ] Subtask 10.5: 实现回复评论接口 `POST /groups/{group_id}/comments/{comment_id}/replies`
  - [ ] Subtask 10.6: 实现评论点赞接口 `POST /groups/{group_id}/comments/{comment_id}/like`
  - [ ] Subtask 10.7: 实现@提及解析和通知生成

- [ ] **Task 11**: 版本控制与回滚系统
  - [ ] Subtask 11.1: 实现版本自动记录服务（记录变更触发器）
  - [ ] Subtask 11.2: 实现获取版本历史接口 `GET /groups/{group_id}/records/{record_id}/versions`
  - [ ] Subtask 11.3: 实现获取版本详情接口 `GET /groups/{group_id}/records/{record_id}/versions/{version_id}`
  - [ ] Subtask 11.4: 实现版本对比接口 `GET /groups/{group_id}/records/{record_id}/versions/compare`
  - [ ] Subtask 11.5: 实现版本回滚接口 `POST /groups/{group_id}/records/{record_id}/versions/{version_id}/rollback`
  - [ ] Subtask 11.6: 实现版本保留策略配置接口 `PUT /groups/{group_id}/version-policy`

- [ ] **Task 12**: 活动记录与通知系统
  - [ ] Subtask 12.1: 实现活动记录自动创建服务
  - [ ] Subtask 12.2: 实现获取活动列表接口 `GET /groups/{group_id}/activities`（支持筛选）
  - [ ] Subtask 12.3: 实现活动记录导出接口 `GET /groups/{group_id}/activities/export`
  - [ ] Subtask 12.4: 实现通知生成服务（邀请、提及、更新等）
  - [ ] Subtask 12.5: 实现获取通知列表接口 `GET /notifications`（支持分页）
  - [ ] Subtask 12.6: 实现标记通知已读接口 `PUT /notifications/{id}/read`
  - [ ] Subtask 12.7: 实现批量标记已读接口 `PUT /notifications/read-all`
  - [ ] Subtask 12.8: 实现通知设置接口 `PUT /notifications/settings`
  - [ ] Subtask 12.9: 实现删除通知接口 `DELETE /notifications/{id}`

- [ ] **Task 13**: WebSocket 实时协作
  - [ ] Subtask 13.1: 实现 WebSocket 连接管理（认证、心跳）
  - [ ] Subtask 13.2: 实现群组房间管理（用户加入/离开群组房间）
  - [ ] Subtask 13.3: 实现数据变更广播机制（记录增删改）
  - [ ] Subtask 13.4: 实现成员活动广播（在线状态、正在编辑）
  - [ ] Subtask 13.5: 实现评论实时推送
  - [ ] Subtask 13.6: 实现通知实时推送
  - [ ] Subtask 13.7: 实现在线状态追踪服务
  - [ ] Subtask 13.8: 实现消息推送服务（应用内 + 邮件）

## 第四阶段：前端基础架构

- [ ] **Task 14**: 前端路由和页面结构
  - [ ] Subtask 14.1: 在 `router/index.ts` 中添加群组列表路由 `/groups`
  - [ ] Subtask 14.2: 在 `router/index.ts` 中添加群组详情路由 `/groups/:id`
  - [ ] Subtask 14.3: 在 `router/index.ts` 中添加归档群组路由 `/groups/archived`
  - [ ] Subtask 14.4: 创建 `GroupList.vue` 群组列表页面
  - [ ] Subtask 14.5: 创建 `GroupDetail.vue` 群组详情页面
  - [ ] Subtask 14.6: 创建 `GroupArchive.vue` 归档群组页面
  - [ ] Subtask 14.7: 在首页导航中添加群组入口

- [ ] **Task 15**: 前端状态管理
  - [ ] Subtask 15.1: 创建 `groupStore.ts` 群组状态管理
  - [ ] Subtask 15.2: 实现群组列表 state 和 actions
  - [ ] Subtask 15.3: 实现当前群组 state 和 actions
  - [ ] Subtask 15.4: 实现群组成员 state 和 actions
  - [ ] Subtask 15.5: 实现群组字段 state 和 actions
  - [ ] Subtask 15.6: 实现群组记录 state 和 actions
  - [ ] Subtask 15.7: 实现群组视图 state 和 actions
  - [ ] Subtask 15.8: 实现筛选排序 state 和 actions
  - [ ] Subtask 15.9: 创建 `groupCommentStore.ts` 评论状态管理
  - [ ] Subtask 15.10: 创建 `notificationStore.ts` 通知状态管理

- [ ] **Task 16**: API 服务层
  - [ ] Subtask 16.1: 创建 `groupService.ts` 群组 API 服务
  - [ ] Subtask 16.2: 创建 `groupMemberService.ts` 成员 API 服务
  - [ ] Subtask 16.3: 创建 `groupFieldService.ts` 字段 API 服务
  - [ ] Subtask 16.4: 创建 `groupRecordService.ts` 记录 API 服务
  - [ ] Subtask 16.5: 创建 `groupViewService.ts` 视图 API 服务
  - [ ] Subtask 16.6: 创建 `groupCommentService.ts` 评论 API 服务
  - [ ] Subtask 16.7: 创建 `groupVersionService.ts` 版本 API 服务
  - [ ] Subtask 16.8: 创建 `groupActivityService.ts` 活动 API 服务
  - [ ] Subtask 16.9: 创建 `groupImportExportService.ts` 导入导出服务
  - [ ] Subtask 16.10: 创建 `notificationService.ts` 通知 API 服务

- [ ] **Task 17**: 权限和工具函数
  - [ ] Subtask 17.1: 创建 `useGroupPermission.ts` 群组权限组合式函数
  - [ ] Subtask 17.2: 创建 `useGroupFilter.ts` 筛选逻辑组合式函数
  - [ ] Subtask 17.3: 创建 `useGroupSort.ts` 排序逻辑组合式函数
  - [ ] Subtask 17.4: 创建 `filterParser.ts` 筛选条件解析工具
  - [ ] Subtask 17.5: 创建 `fieldValidator.ts` 字段验证工具

## 第五阶段：前端 UI 组件

- [ ] **Task 18**: 群组列表页面
  - [ ] Subtask 18.1: 实现群组卡片展示组件（含头像、名称、成员数）
  - [ ] Subtask 18.2: 实现创建群组对话框（支持模板选择）
  - [ ] Subtask 18.3: 实现群组搜索功能（按名称、描述）
  - [ ] Subtask 18.4: 实现群组筛选功能（我创建的、我参与的、归档的）
  - [ ] Subtask 18.5: 实现群组排序（按时间、名称、成员数）
  - [ ] Subtask 18.6: 实现空状态展示
  - [ ] Subtask 18.7: 实现群组快捷操作菜单（归档、删除）

- [ ] **Task 19**: 群组头部和基本信息
  - [ ] Subtask 19.1: 创建 `GroupHeader.vue` 群组头部组件
  - [ ] Subtask 19.2: 实现群组头像和名称展示
  - [ ] Subtask 19.3: 实现群组信息编辑对话框
  - [ ] Subtask 19.4: 实现群组设置菜单（归档、删除、转移所有权）
  - [ ] Subtask 19.5: 实现群组标签/徽章展示（归档状态、成员角色）

- [ ] **Task 20**: 成员管理组件
  - [ ] Subtask 20.1: 创建 `GroupMemberManager.vue` 成员管理组件
  - [ ] Subtask 20.2: 实现成员列表展示（含头像、角色、在线状态）
  - [ ] Subtask 20.3: 实现成员搜索和筛选（按角色、在线状态）
  - [ ] Subtask 20.4: 实现邀请成员对话框（邮箱搜索、批量邀请）
  - [ ] Subtask 20.5: 实现生成邀请链接功能（有效期设置）
  - [ ] Subtask 20.6: 实现角色选择和更新下拉菜单
  - [ ] Subtask 20.7: 实现移除成员确认对话框（含记录转移选项）
  - [ ] Subtask 20.8: 实现转移所有权对话框

- [ ] **Task 21**: 字段管理组件
  - [ ] Subtask 21.1: 创建 `GroupFieldManager.vue` 字段管理组件
  - [ ] Subtask 21.2: 实现字段列表展示（含类型图标、必填标记）
  - [ ] Subtask 21.3: 实现添加字段对话框（类型选择、选项配置）
  - [ ] Subtask 21.4: 实现字段编辑抽屉（名称、验证规则、默认值）
  - [ ] Subtask 21.5: 实现字段拖拽排序
  - [ ] Subtask 21.6: 实现字段隐藏/显示切换
  - [ ] Subtask 21.7: 实现字段删除确认

- [ ] **Task 22**: 视图切换组件
  - [ ] Subtask 22.1: 创建 `GroupViewSwitcher.vue` 视图切换组件
  - [ ] Subtask 22.2: 实现视图类型图标和切换标签页
  - [ ] Subtask 22.3: 实现创建视图对话框（类型、名称、权限）
  - [ ] Subtask 22.4: 实现视图列表下拉菜单（含收藏、默认标记）
  - [ ] Subtask 22.5: 实现视图重命名、复制、删除功能
  - [ ] Subtask 22.6: 实现视图共享设置
  - [ ] Subtask 22.7: 实现视图收藏功能

- [ ] **Task 23**: 表格视图
  - [ ] Subtask 23.1: 创建 `GroupTableView.vue` 表格视图组件
  - [ ] Subtask 23.2: 集成 Vxe-Table 组件
  - [ ] Subtask 23.3: 实现字段列动态渲染（根据字段类型）
  - [ ] Subtask 23.4: 实现单元格编辑（根据字段类型显示不同编辑器）
  - [ ] Subtask 23.5: 实现列宽调整、列冻结、列隐藏
  - [ ] Subtask 23.6: 实现行选择和批量操作工具栏
  - [ ] Subtask 23.7: 实现虚拟滚动
  - [ ] Subtask 23.8: 实现条件格式设置

- [ ] **Task 24**: 看板视图
  - [ ] Subtask 24.1: 创建 `GroupKanbanView.vue` 看板视图组件
  - [ ] Subtask 24.2: 创建 `KanbanColumn.vue` 看板列组件
  - [ ] Subtask 24.3: 创建 `KanbanCard.vue` 看板卡片组件
  - [ ] Subtask 24.4: 实现按字段分组（列）配置
  - [ ] Subtask 24.5: 实现卡片拖拽排序（同列内）
  - [ ] Subtask 24.6: 实现跨列拖拽（变更分组字段值）
  - [ ] Subtask 24.7: 实现卡片快速编辑弹窗
  - [ ] Subtask 24.8: 实现泳道视图（二级分组）

- [ ] **Task 25**: 日历视图
  - [ ] Subtask 25.1: 创建 `GroupCalendarView.vue` 日历视图组件
  - [ ] Subtask 25.2: 集成 FullCalendar 组件
  - [ ] Subtask 25.3: 实现月/周/日/列表视图切换
  - [ ] Subtask 25.4: 实现日期字段选择配置
  - [ ] Subtask 25.5: 实现事件展示（根据日期字段）
  - [ ] Subtask 25.6: 实现事件拖拽调整日期
  - [ ] Subtask 25.7: 实现日历事件颜色配置

- [ ] **Task 26**: 筛选面板组件
  - [ ] Subtask 26.1: 创建 `GroupFilterPanel.vue` 筛选面板组件
  - [ ] Subtask 26.2: 实现筛选条件添加 UI（字段、操作符、值）
  - [ ] Subtask 26.3: 实现筛选值输入组件（根据字段类型动态渲染）
  - [ ] Subtask 26.4: 实现多条件组合（AND/OR）和嵌套条件组
  - [ ] Subtask 26.5: 实现条件拖拽调整顺序
  - [ ] Subtask 26.6: 实现快速筛选快捷入口
  - [ ] Subtask 26.7: 实现筛选条件保存和重置
  - [ ] Subtask 26.8: 实现筛选结果计数显示

- [ ] **Task 27**: 排序和分组组件
  - [ ] Subtask 27.1: 创建 `GroupSortPanel.vue` 排序面板组件
  - [ ] Subtask 27.2: 实现排序字段选择（支持多字段）
  - [ ] Subtask 27.3: 实现排序方向切换
  - [ ] Subtask 27.4: 实现排序优先级拖拽调整
  - [ ] Subtask 27.5: 创建 `GroupGroupPanel.vue` 分组面板组件
  - [ ] Subtask 27.6: 实现分组字段选择（支持多级分组）
  - [ ] Subtask 27.7: 实现分组统计配置

- [ ] **Task 28**: 导入导出组件
  - [ ] Subtask 28.1: 创建 `GroupImportDialog.vue` 导入对话框
  - [ ] Subtask 28.2: 实现文件上传和格式验证
  - [ ] Subtask 28.3: 实现字段映射配置界面（自动匹配）
  - [ ] Subtask 28.4: 实现导入数据预览（前10条）
  - [ ] Subtask 28.5: 实现导入进度和结果展示
  - [ ] Subtask 28.6: 创建 `GroupExportDialog.vue` 导出对话框
  - [ ] Subtask 28.7: 实现导出范围选择（全部/筛选后/选中）
  - [ ] Subtask 28.8: 实现导出字段选择
  - [ ] Subtask 28.9: 实现导出进度显示

- [ ] **Task 29**: 评论组件
  - [ ] Subtask 29.1: 创建 `GroupCommentPanel.vue` 评论面板组件
  - [ ] Subtask 29.2: 实现评论列表展示（含头像、时间、内容）
  - [ ] Subtask 29.3: 实现评论输入框（支持@提及）
  - [ ] Subtask 29.4: 实现评论回复功能（嵌套展示）
  - [ ] Subtask 29.5: 实现评论编辑和删除
  - [ ] Subtask 29.6: 实现评论点赞
  - [ ] Subtask 29.7: 实现附件上传预览

- [ ] **Task 30**: 版本历史组件
  - [ ] Subtask 30.1: 创建 `GroupVersionHistory.vue` 版本历史组件
  - [ ] Subtask 30.2: 实现版本列表展示（时间、操作人、变更摘要）
  - [ ] Subtask 30.3: 实现版本详情查看
  - [ ] Subtask 30.4: 实现版本对比（字段级差异高亮）
  - [ ] Subtask 30.5: 实现版本回滚确认对话框
  - [ ] Subtask 30.6: 实现回滚预览展示

- [ ] **Task 31**: 活动动态组件
  - [ ] Subtask 31.1: 创建 `GroupActivityFeed.vue` 活动动态组件
  - [ ] Subtask 31.2: 实现活动列表展示（图标、描述、时间）
  - [ ] Subtask 31.3: 实现活动筛选（按类型、操作人、时间）
  - [ ] Subtask 31.4: 实现实时活动更新
  - [ ] Subtask 31.5: 实现活动导出

- [ ] **Task 32**: 通知中心组件
  - [ ] Subtask 32.1: 创建 `NotificationCenter.vue` 通知中心组件
  - [ ] Subtask 32.2: 实现通知列表展示（标题、内容、时间）
  - [ ] Subtask 32.3: 实现通知标记已读
  - [ ] Subtask 32.4: 实现批量标记已读
  - [ ] Subtask 32.5: 实现通知设置（开关、免打扰）
  - [ ] Subtask 32.6: 实现通知实时推送提示

## 第六阶段：实时协作与优化

- [ ] **Task 33**: WebSocket 客户端实现
  - [ ] Subtask 33.1: 创建 `groupWebSocket.ts` WebSocket 服务
  - [ ] Subtask 33.2: 实现连接管理和自动重连机制
  - [ ] Subtask 33.3: 实现消息接收和分发处理
  - [ ] Subtask 33.4: 实现数据变更同步和冲突提示
  - [ ] Subtask 33.5: 实现在线状态更新和成员活动显示
  - [ ] Subtask 33.6: 实现评论实时推送
  - [ ] Subtask 33.7: 实现通知实时推送

- [ ] **Task 34**: 性能优化
  - [ ] Subtask 34.1: 实现数据缓存机制（localStorage + memory）
  - [ ] Subtask 34.2: 实现虚拟滚动优化（表格视图）
  - [ ] Subtask 34.3: 实现防抖节流优化（搜索、筛选）
  - [ ] Subtask 34.4: 实现大数据量分页加载（游标分页）
  - [ ] Subtask 34.5: 实现组件懒加载
  - [ ] Subtask 34.6: 实现图片懒加载和缩略图

- [ ] **Task 35**: 测试与文档
  - [ ] Subtask 35.1: 编写后端单元测试（覆盖率 ≥ 80%）
  - [ ] Subtask 35.2: 编写后端集成测试
  - [ ] Subtask 35.3: 编写前端单元测试（覆盖率 ≥ 70%）
  - [ ] Subtask 35.4: 编写前端 E2E 测试
  - [ ] Subtask 35.5: 编写 API 接口文档（Swagger/OpenAPI）
  - [ ] Subtask 35.6: 编写用户操作手册
  - [ ] Subtask 35.7: 进行性能测试和优化
  - [ ] Subtask 35.8: 生成测试报告

# Task Dependencies

## 后端依赖
- Task 1 是其他所有后端任务的基础，必须最先完成
- Task 2、Task 3 可以并行开发，依赖于 Task 1
- Task 4、Task 5、Task 6 依赖于 Task 1 完成
- Task 7 依赖于 Task 4、Task 5 完成
- Task 8 依赖于 Task 4、Task 5 完成
- Task 9 依赖于 Task 2、Task 3 完成
- Task 10 依赖于 Task 5 完成
- Task 11 依赖于 Task 5 完成
- Task 12 依赖于 Task 5、Task 10 完成
- Task 13 依赖于 Task 9、Task 10、Task 12 完成

## 前端依赖
- Task 14、Task 15、Task 16、Task 17 可以并行开发
- Task 18 依赖于 Task 14、Task 15、Task 16
- Task 19 依赖于 Task 14、Task 15
- Task 20 依赖于 Task 14、Task 15、Task 16
- Task 21 依赖于 Task 14、Task 15、Task 16
- Task 22 依赖于 Task 14、Task 15
- Task 23、Task 24、Task 25 依赖于 Task 14、Task 15、Task 21、Task 22
- Task 26、Task 27 依赖于 Task 14、Task 15
- Task 28 依赖于 Task 14、Task 16
- Task 29 依赖于 Task 14、Task 15、Task 16
- Task 30 依赖于 Task 14、Task 15、Task 16
- Task 31 依赖于 Task 14、Task 15、Task 16
- Task 32 依赖于 Task 14、Task 15

## 前后端联调依赖
- Task 33 依赖于 Task 13、Task 14、Task 15 完成
- Task 34 依赖于 Task 18-32 完成
- Task 35 依赖于所有开发任务完成
