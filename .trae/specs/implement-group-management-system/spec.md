# 群组管理系统规格说明

## Why

当前 SmartTable 系统虽然已实现多维表格的核心功能，但缺少面向团队协作场景的群组管理功能。用户需要一个独立的群组管理系统来组织团队成员、管理群组信息、分配权限，并在群组维度上进行协作。该系统将参照飞书多维表的核心功能特性，提供全面的群组管理能力，支持群组信息的多维数据管理、多种视图展示、分层权限控制等功能。

## What Changes

### 新增功能模块

- **群组信息管理**：支持自定义字段类型（文本、数字、日期、成员、单选/多选等）管理群组元数据
- **动态视图系统**：支持表格视图、看板视图、日历视图等多种展示方式切换
- **权限分层管理**：实现群组创建者、管理员、普通成员等不同角色的权限控制
- **数据筛选排序**：支持多条件组合查询和排序
- **数据导入导出**：兼容 Excel、CSV、JSON 等常见格式
- **实时协作机制**：群组信息更新实时同步和提醒
- **群组归档与恢复**：支持群组软删除和恢复功能
- **数据版本控制**：记录变更历史，支持数据回滚
- **评论与@提及**：支持记录级别的评论和成员提及功能

### 数据库变更

- **新增 groups 表**：存储群组基本信息
- **新增 group_members 表**：存储群组成员关系和角色
- **新增 group_fields 表**：存储群组自定义字段定义
- **新增 group_records 表**：存储群组记录数据
- **新增 group_views 表**：存储群组视图配置
- **新增 group_activities 表**：存储群组动态活动记录
- **新增 group_invitations 表**：存储群组邀请信息
- **新增 group_comments 表**：存储记录评论信息
- **新增 group_record_versions 表**：存储记录版本历史

### 后端 API 变更

- **群组管理接口**：创建、更新、删除、查询群组，支持归档和恢复
- **成员管理接口**：添加、移除、更新成员角色，支持批量操作
- **字段管理接口**：自定义字段的 CRUD 操作，支持字段验证规则
- **视图管理接口**：视图的创建、切换、配置，支持视图共享
- **筛选排序接口**：数据筛选和排序查询，支持高级筛选条件
- **导入导出接口**：数据导入导出功能，支持模板下载
- **实时协作接口**：WebSocket 连接和消息推送
- **评论接口**：记录的评论增删改查，支持@提及
- **版本控制接口**：记录版本历史查询和回滚

### 前端页面变更

- **群组列表页面**：展示用户参与的所有群组，支持归档群组查看
- **群组详情页面**：群组信息管理和成员协作的主界面
- **成员管理组件**：群组成员的添加、移除、角色管理，支持批量邀请
- **视图切换组件**：支持多种视图的动态切换和视图配置
- **筛选面板组件**：多条件筛选和排序配置，支持筛选条件保存为视图
- **导入导出组件**：数据导入导出界面，支持字段映射预览
- **活动动态组件**：群组活动记录和实时通知
- **评论组件**：记录级别的评论展示和发布
- **版本历史组件**：记录变更历史展示和回滚操作

## Impact

### 受影响的后端文件

- `smarttable-backend/models.py` - 新增群组相关模型
- `smarttable-backend/routes/group_routes.py` - 新增群组管理路由
- `smarttable-backend/routes/group_member_routes.py` - 新增群组成员路由
- `smarttable-backend/routes/group_view_routes.py` - 新增群组视图路由
- `smarttable-backend/routes/group_comment_routes.py` - 新增评论路由
- `smarttable-backend/routes/group_version_routes.py` - 新增版本控制路由
- `smarttable-backend/services/group_service.py` - 群组业务逻辑服务
- `smarttable-backend/services/group_permission_service.py` - 群组权限服务
- `smarttable-backend/websocket/group_ws.py` - 群组实时协作 WebSocket
- `smarttable-backend/auth.py` - 增强群组权限验证
- `smarttable-backend/utils/filter_parser.py` - 筛选条件解析器
- `smarttable-backend/utils/sort_processor.py` - 排序处理器

### 受影响的前端文件

- `smart-table/src/views/GroupList.vue` - 群组列表页面
- `smart-table/src/views/GroupDetail.vue` - 群组详情页面
- `smart-table/src/views/GroupArchive.vue` - 群组归档页面
- `smart-table/src/components/group/GroupMemberManager.vue` - 成员管理组件
- `smart-table/src/components/group/GroupViewSwitcher.vue` - 视图切换组件
- `smart-table/src/components/group/GroupFilterPanel.vue` - 筛选面板组件
- `smart-table/src/components/group/GroupSortPanel.vue` - 排序面板组件
- `smart-table/src/components/group/GroupImportExport.vue` - 导入导出组件
- `smart-table/src/components/group/GroupActivityFeed.vue` - 活动动态组件
- `smart-table/src/components/group/GroupCommentPanel.vue` - 评论组件
- `smart-table/src/components/group/GroupVersionHistory.vue` - 版本历史组件
- `smart-table/src/components/group/GroupFieldManager.vue` - 字段管理组件
- `smart-table/src/components/group/GroupPermissionPanel.vue` - 权限面板组件
- `smart-table/src/stores/groupStore.ts` - 群组状态管理
- `smart-table/src/stores/groupCommentStore.ts` - 评论状态管理
- `smart-table/src/composables/useGroupPermission.ts` - 群组权限组合式函数
- `smart-table/src/router/index.ts` - 新增群组相关路由

## ADDED Requirements

### Requirement: 群组信息管理

系统 SHALL 提供群组信息的全面管理功能，支持自定义字段类型存储群组元数据。

#### Scenario: 创建群组
- **WHEN** 用户点击"创建群组"
- **THEN** 弹出创建对话框，输入群组名称、描述等基本信息
- **AND** 可选择群组模板（空白、项目管理、客户管理等预设模板）
- **AND** 系统自动创建者为群主（owner）角色
- **AND** 群组创建成功后跳转到群组详情页

#### Scenario: 编辑群组信息
- **WHEN** 群主或管理员编辑群组信息
- **THEN** 可以修改群组名称、描述、头像等基本信息
- **AND** 支持添加自定义字段（文本、数字、日期、成员、单选/多选等）
- **AND** 修改后实时保存并同步给所有成员
- **AND** 记录编辑历史到活动日志

#### Scenario: 删除群组
- **WHEN** 群主选择删除群组
- **THEN** 弹出确认对话框，提示删除后果
- **AND** 可选择软删除（归档）或永久删除
- **AND** 软删除后群组进入归档状态，30天内可恢复
- **AND** 永久删除后无法恢复，需二次确认
- **AND** 通知所有群组成员群组已被删除

#### Scenario: 归档和恢复群组
- **WHEN** 群主选择归档群组
- **THEN** 群组进入只读归档状态
- **AND** 成员可以查看但不能编辑数据
- **AND** 归档群组可从归档列表中恢复
- **AND** 恢复后群组恢复正常状态

#### Scenario: 自定义字段管理
- **WHEN** 群主或管理员添加自定义字段
- **THEN** 可选择字段类型：文本、数字、日期、成员、单选、多选、复选框、附件、公式、关联等
- **AND** 可配置字段属性：必填、默认值、选项值、验证规则、字段说明等
- **AND** 支持字段拖拽排序
- **AND** 支持字段隐藏/显示设置
- **AND** 字段添加后所有成员可见可用

### Requirement: 群组成员管理

系统 SHALL 提供完整的群组成员管理功能，支持分层权限控制和批量操作。

#### Scenario: 邀请成员
- **WHEN** 群主或管理员点击"邀请成员"
- **THEN** 可通过用户邮箱、用户名搜索或生成邀请链接
- **AND** 可为新成员设置角色（admin、editor、viewer）
- **AND** 支持批量邀请多个成员
- **AND** 被邀请用户收到通知并可以选择接受或拒绝
- **AND** 邀请链接可设置有效期（7天/30天/永久）

#### Scenario: 成员角色管理
- **WHEN** 群主或管理员查看成员列表
- **THEN** 显示所有成员的头像、昵称、角色、加入时间、最后活动时间
- **AND** 可以修改成员角色（不能修改群主角色）
- **AND** 角色变更立即生效并通知相关人员
- **AND** 支持按角色筛选成员

#### Scenario: 移除成员
- **WHEN** 群主或管理员移除成员
- **THEN** 弹出确认对话框，显示该成员负责的记录数量
- **AND** 可选择将成员负责的记录转移给其他成员
- **AND** 确认后该成员失去群组访问权限
- **AND** 被移除成员收到通知

#### Scenario: 成员权限控制
- **WHEN** 不同角色的成员访问群组
- **THEN** 群主（owner）：拥有所有权限，可删除群组、转移所有权
- **AND** 管理员（admin）：可管理成员、编辑群组信息、管理视图
- **AND** 编辑者（editor）：可编辑记录数据、添加评论
- **AND** 查看者（viewer）：仅可查看数据、添加评论
- **AND** 权限检查在所有操作前执行

#### Scenario: 转移群组所有权
- **WHEN** 群主选择转移所有权
- **THEN** 可选择群组成员作为新群主
- **AND** 需要新群主确认接受
- **AND** 转移后原群主变为管理员角色
- **AND** 记录所有权转移历史

### Requirement: 动态视图系统

系统 SHALL 支持多种视图展示方式，用户可根据需求动态切换和配置。

#### Scenario: 表格视图
- **WHEN** 用户选择表格视图
- **THEN** 以行列表格形式展示群组记录
- **AND** 支持单元格编辑、列宽调整、列冻结、列隐藏
- **AND** 支持行选择、批量操作
- **AND** 支持虚拟滚动处理大数据量
- **AND** 支持条件格式设置

#### Scenario: 看板视图
- **WHEN** 用户选择看板视图
- **THEN** 按分组字段以卡片形式展示记录
- **AND** 支持卡片拖拽排序和跨列拖拽
- **AND** 可配置看板的分组字段和显示字段
- **AND** 支持卡片快速编辑
- **AND** 支持泳道视图（二级分组）

#### Scenario: 日历视图
- **WHEN** 用户选择日历视图
- **THEN** 按日期字段在日历上展示记录
- **AND** 支持月/周/日/列表视图切换
- **AND** 支持拖拽调整日期
- **AND** 支持多日期字段选择
- **AND** 支持日历事件颜色配置

#### Scenario: 视图创建和切换
- **WHEN** 用户创建新视图
- **THEN** 可选择视图类型（表格、看板、日历）
- **AND** 可配置视图名称、描述、图标
- **AND** 可设置默认筛选条件和排序规则
- **AND** 可设置视图访问权限（私有/群组共享）
- **AND** 视图列表中可快速切换不同视图
- **AND** 支持视图收藏和固定

#### Scenario: 视图共享
- **WHEN** 用户共享视图
- **THEN** 可生成视图分享链接
- **AND** 可设置分享权限（只读/编辑）
- **AND** 可查看当前共享的成员列表
- **AND** 可随时取消共享

### Requirement: 数据筛选与排序

系统 SHALL 提供强大的数据筛选和排序功能，支持多条件组合查询和高级筛选。

#### Scenario: 单条件筛选
- **WHEN** 用户设置筛选条件
- **THEN** 可选择字段、操作符（等于、不等于、包含、不包含、开头是、结尾是、大于、小于、介于、为空、不为空等）
- **AND** 根据字段类型显示相应的值输入组件
- **AND** 输入筛选值后数据实时过滤
- **AND** 显示符合条件的记录数量

#### Scenario: 多条件组合筛选
- **WHEN** 用户添加多个筛选条件
- **THEN** 可选择条件组合方式（AND/OR）
- **AND** 支持嵌套条件组（条件组内支持 AND/OR）
- **AND** 支持条件拖拽调整顺序
- **AND** 筛选结果实时更新
- **AND** 支持保存筛选配置为筛选视图

#### Scenario: 快速筛选
- **WHEN** 用户使用快速筛选
- **THEN** 提供常用筛选条件快捷入口
- **AND** 支持按当前用户筛选（我的记录）
- **AND** 支持按时间范围筛选（今天、本周、本月、本年）
- **AND** 支持按字段值快速筛选（点击字段值自动筛选）

#### Scenario: 排序功能
- **WHEN** 用户设置排序条件
- **THEN** 可选择排序字段和排序方向（升序/降序）
- **AND** 支持多字段排序（最多3级排序）
- **AND** 支持拖拽调整排序优先级
- **AND** 排序结果实时更新
- **AND** 支持按自定义顺序排序（单选/多选字段）

#### Scenario: 分组功能
- **WHEN** 用户设置分组字段
- **THEN** 数据按字段值分组展示
- **AND** 支持多级分组（最多3级）
- **AND** 支持分组折叠/展开
- **AND** 显示每组记录数量
- **AND** 支持分组统计（计数、求和、平均值等）

#### Scenario: 保存筛选排序配置
- **WHEN** 用户保存当前筛选排序配置
- **THEN** 可命名并保存为视图配置的一部分
- **AND** 下次打开视图时自动应用
- **AND** 可重置为默认状态
- **AND** 支持创建个人视图和群组共享视图

### Requirement: 数据导入导出

系统 SHALL 支持数据的导入导出功能，兼容常见文件格式，支持模板和批量操作。

#### Scenario: Excel 导入
- **WHEN** 用户选择导入 Excel 文件
- **THEN** 支持上传 .xlsx 或 .xls 文件
- **AND** 提供字段映射配置界面，支持自动匹配和同名字段映射
- **AND** 支持预览导入数据（前10条）
- **AND** 支持设置数据去重规则（按主键/按字段值）
- **AND** 导入完成后显示成功/失败统计和错误详情
- **AND** 支持导入历史查看

#### Scenario: Excel 导出
- **WHEN** 用户选择导出为 Excel
- **THEN** 可选择导出范围（全部数据、筛选后数据、选中数据）
- **AND** 可选择导出字段（全部字段或自定义选择）
- **AND** 生成 .xlsx 文件并自动下载
- **AND** 保持字段格式和数据完整性
- **AND** 支持导出模板下载（含示例数据）

#### Scenario: CSV 导入导出
- **WHEN** 用户选择 CSV 格式
- **THEN** 支持 CSV 文件导入和导出
- **AND** 支持编码格式选择（UTF-8、GBK、UTF-8 with BOM 等）
- **AND** 支持分隔符配置（逗号、分号、制表符等）
- **AND** 支持文本限定符配置

#### Scenario: JSON 导入导出
- **WHEN** 用户选择 JSON 格式
- **THEN** 支持 JSON 文件导入和导出
- **AND** 保持数据结构完整性
- **AND** 支持格式化输出选项
- **AND** 支持 JSON Schema 验证

### Requirement: 实时协作与提醒

系统 SHALL 提供实时协作功能，支持群组信息的同步更新和提醒机制。

#### Scenario: 实时数据同步
- **WHEN** 群组成员编辑记录数据
- **THEN** 其他在线成员实时看到更新（延迟 < 1秒）
- **AND** 显示数据更新提示（如"张三刚刚更新了某字段"）
- **AND** 离线成员上线后自动同步最新数据
- **AND** 支持冲突检测和解决（乐观锁机制）

#### Scenario: 活动动态记录
- **WHEN** 群组发生重要操作
- **THEN** 记录到活动日志（创建、编辑、删除记录、成员变动等）
- **AND** 显示操作人、操作类型、操作时间、操作详情
- **AND** 支持按操作类型、操作人、时间范围筛选活动记录
- **AND** 支持活动记录导出

#### Scenario: 通知提醒
- **WHEN** 用户被邀请加入群组
- **THEN** 收到系统通知（应用内通知 + 邮件通知）
- **AND** 当记录被分配给成员时，该成员收到通知
- **AND** 当有人@提及成员时，该成员收到通知
- **AND** 当关注的记录被修改时，收到通知
- **AND** 支持通知设置（开启/关闭、通知方式、免打扰时段）
- **AND** 支持通知标记已读和批量已读

#### Scenario: 在线状态显示
- **WHEN** 用户查看群组成员列表
- **THEN** 显示成员的在线/离线/离开状态
- **AND** 显示成员当前正在查看的视图或编辑的记录
- **AND** 显示成员最近活动时间
- **AND** 支持查看成员活动状态（空闲/忙碌）

### Requirement: 评论与@提及

系统 SHALL 支持记录级别的评论功能和成员提及机制。

#### Scenario: 添加评论
- **WHEN** 用户在记录上添加评论
- **THEN** 支持文本评论和富文本评论
- **AND** 支持@提及群组成员
- **AND** 支持附件上传（图片、文档等）
- **AND** 评论实时显示并通知相关人员

#### Scenario: 回复评论
- **WHEN** 用户回复某条评论
- **THEN** 形成评论线程
- **AND** 被回复者收到通知
- **AND** 支持嵌套回复（最多3层）

#### Scenario: 评论管理
- **WHEN** 用户管理评论
- **THEN** 评论作者可编辑自己的评论
- **AND** 评论作者可删除自己的评论
- **AND** 群主和管理员可删除任何评论
- **AND** 支持评论点赞

### Requirement: 数据版本控制

系统 SHALL 支持记录级别的版本控制，记录变更历史并支持数据回滚。

#### Scenario: 版本记录
- **WHEN** 记录数据发生变更
- **THEN** 自动创建版本快照
- **AND** 记录变更字段、变更前值、变更后值
- **AND** 记录变更人和变更时间
- **AND** 支持设置版本保留策略（保留最近N个版本或保留N天）

#### Scenario: 查看版本历史
- **WHEN** 用户查看记录版本历史
- **THEN** 显示该记录的所有历史版本列表
- **AND** 支持版本对比（显示字段级差异）
- **AND** 支持按时间范围筛选版本

#### Scenario: 版本回滚
- **WHEN** 用户选择回滚到某个版本
- **THEN** 显示回滚预览（将恢复的字段值）
- **AND** 确认后恢复到该版本状态
- **AND** 回滚操作本身也记录为新版本
- **AND** 通知相关人员数据已回滚

### Requirement: 数据库模型

#### groups 表
系统 SHALL 创建 groups 表存储群组信息：
- id: UUID 主键
- name: 群组名称（必填，最大100字符）
- description: 群组描述（可选，最大500字符）
- avatar: 群组头像 URL（可选）
- owner_id: 群主用户 ID（外键，必填）
- template: 群组模板类型（blank/project/crm等）
- status: 群组状态（active/archived/deleted，默认active）
- settings: 群组设置（JSON，包含通知设置、权限设置等）
- archived_at: 归档时间（可选）
- archived_by: 归档人 ID（可选）
- created_at: 创建时间
- updated_at: 更新时间
- deleted_at: 软删除时间（可选，用于软删除）

#### group_members 表
系统 SHALL 创建 group_members 表存储成员关系：
- id: UUID 主键
- group_id: 群组 ID（外键，必填）
- user_id: 用户 ID（外键，必填）
- role: 角色（owner/admin/editor/viewer，必填）
- joined_at: 加入时间（必填）
- invited_by: 邀请人 ID（可选）
- last_active_at: 最后活动时间（可选）
- status: 成员状态（active/inactive，默认active）
- UNIQUE(group_id, user_id)

#### group_invitations 表
系统 SHALL 创建 group_invitations 表存储邀请信息：
- id: UUID 主键
- group_id: 群组 ID（外键，必填）
- email: 被邀请人邮箱（必填）
- token: 邀请令牌（UUID，唯一，必填）
- role: 邀请角色（admin/editor/viewer，必填）
- invited_by: 邀请人 ID（必填）
- expires_at: 过期时间（必填）
- status: 邀请状态（pending/accepted/rejected/expired，默认pending）
- created_at: 创建时间
- accepted_at: 接受时间（可选）

#### group_fields 表
系统 SHALL 创建 group_fields 表存储字段定义：
- id: UUID 主键
- group_id: 群组 ID（外键，必填）
- name: 字段名称（必填，最大100字符）
- type: 字段类型（text/number/date/member/select/multi_select/checkbox/attachment/formula/link等，必填）
- options: 字段选项（JSON，包含验证规则、默认值、选项值等）
- order: 字段排序（整数，必填）
- is_required: 是否必填（布尔，默认false）
- is_hidden: 是否隐藏（布尔，默认false）
- description: 字段说明（可选，最大200字符）
- created_by: 创建人 ID（必填）
- created_at: 创建时间
- updated_at: 更新时间

#### group_records 表
系统 SHALL 创建 group_records 表存储记录数据：
- id: UUID 主键
- group_id: 群组 ID（外键，必填）
- data: 记录数据（JSON，必填）
- version: 版本号（整数，默认1，用于乐观锁）
- created_by: 创建人 ID（必填）
- updated_by: 最后修改人 ID（必填）
- created_at: 创建时间
- updated_at: 更新时间

#### group_record_versions 表
系统 SHALL 创建 group_record_versions 表存储版本历史：
- id: UUID 主键
- record_id: 记录 ID（外键，必填）
- group_id: 群组 ID（外键，必填）
- data: 记录数据快照（JSON，必填）
- version: 版本号（整数，必填）
- changed_fields: 变更字段列表（JSON，必填）
- created_by: 操作人 ID（必填）
- created_at: 操作时间（必填）

#### group_views 表
系统 SHALL 创建 group_views 表存储视图配置：
- id: UUID 主键
- group_id: 群组 ID（外键，必填）
- name: 视图名称（必填，最大100字符）
- type: 视图类型（table/kanban/calendar，必填）
- config: 视图配置（JSON，包含筛选、排序、分组、列配置等）
- is_default: 是否默认视图（布尔，默认false）
- is_shared: 是否共享视图（布尔，默认true）
- created_by: 创建人 ID（必填）
- created_at: 创建时间
- updated_at: 更新时间

#### group_activities 表
系统 SHALL 创建 group_activities 表存储活动记录：
- id: UUID 主键
- group_id: 群组 ID（外键，必填）
- user_id: 操作用户 ID（必填）
- action: 操作类型（create/update/delete/invite/join/leave等，必填）
- target_type: 目标类型（record/member/view/field/group，必填）
- target_id: 目标 ID（可选）
- details: 操作详情（JSON，可选）
- created_at: 操作时间（必填）

#### group_comments 表
系统 SHALL 创建 group_comments 表存储评论信息：
- id: UUID 主键
- group_id: 群组 ID（外键，必填）
- record_id: 记录 ID（外键，必填）
- user_id: 评论人 ID（必填）
- content: 评论内容（必填，最大2000字符）
- parent_id: 父评论 ID（可选，用于回复）
- mentions: @提及用户列表（JSON，可选）
- attachments: 附件列表（JSON，可选）
- like_count: 点赞数（整数，默认0）
- created_at: 创建时间
- updated_at: 更新时间
- deleted_at: 删除时间（可选，软删除）

#### notifications 表
系统 SHALL 创建 notifications 表存储用户通知：
- id: UUID 主键
- user_id: 用户 ID（外键，必填）
- type: 通知类型（invite/mention/record_update/system，必填）
- title: 通知标题（必填）
- content: 通知内容（可选）
- data: 通知数据（JSON，包含相关ID等）
- is_read: 是否已读（布尔，默认false）
- read_at: 阅读时间（可选）
- created_at: 创建时间

## MODIFIED Requirements

### Requirement: 用户权限验证

系统 SHALL 在所有群组操作前验证用户权限：
- **读取群组**：用户是群组成员且状态为active
- **编辑群组信息**：用户角色为 admin 或 owner，且群组状态为active
- **管理成员**：用户角色为 admin 或 owner，且群组状态为active
- **删除群组**：用户角色为 owner
- **归档/恢复群组**：用户角色为 owner
- **编辑记录**：用户角色为 editor、admin 或 owner，且群组状态为active
- **查看记录**：所有群组成员，群组状态为active或archived
- **添加评论**：所有群组成员
- **版本回滚**：用户角色为 admin 或 owner

### Requirement: 数据一致性保障

系统 SHALL 保障数据一致性：
- **乐观锁机制**：记录更新时使用版本号检查，防止并发冲突
- **事务处理**：批量操作使用数据库事务，确保原子性
- **级联删除**：删除群组时级联删除相关数据（或标记为删除）
- **外键约束**：维护数据引用完整性

## REMOVED Requirements

无
