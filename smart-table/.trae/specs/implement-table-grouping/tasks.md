# 表格视图数据分组功能任务列表

## 任务依赖关系
```
Task 1 (数据库变更)
    ↓
Task 2 (状态管理) ←→ Task 3 (分组面板完善)
    ↓
Task 4 (表格视图集成)
    ↓
Task 5 (工具栏集成)
    ↓
Task 6 (测试验证)
```

## 任务详情

### Task 1: 数据库视图配置扩展
**描述**: 扩展 ViewEntity 的 config 字段，添加 groupBy 配置支持

**子任务**:
- [x] SubTask 1.1: 在 `src/db/schema.ts` 的 ViewEntity 接口中添加 groupBy 字段类型定义
- [x] SubTask 1.2: 更新数据库索引配置（如需要）
- [x] SubTask 1.3: 验证现有视图数据兼容性

**状态**: ✅ 已完成 - ViewEntity 已包含 groupBys 字段

**验收标准**:
- ViewEntity.config 支持 groupBy: string[] 配置
- 现有视图数据不受影响

---

### Task 2: 状态管理添加分组配置支持
**描述**: 在 viewStore 中添加分组配置的读写方法

**子任务**:
- [x] SubTask 2.1: 在 `src/stores/viewStore.ts` 中添加 groupBy 响应式状态
- [x] SubTask 2.2: 添加 `setGroupBy(groupBy: string[])` action 方法
- [x] SubTask 2.3: 在视图保存/加载逻辑中包含 groupBy 配置
- [x] SubTask 2.4: 添加分组配置变更的持久化逻辑

**状态**: ✅ 已完成 - viewStore 已添加 currentGroupBys 和 updateGroupBys

**验收标准**:
- viewStore 支持读写 groupBy 配置
- 分组配置变更自动保存到数据库
- 视图切换时正确加载分组配置

---

### Task 3: 分组配置面板完善
**描述**: 完善现有的 GroupPanel.vue 组件，支持拖拽排序和更好的交互

**子任务**:
- [x] SubTask 3.1: 集成 sortablejs 实现分组字段拖拽排序
- [x] SubTask 3.2: 添加最大分组层级限制（最多3级）
- [x] SubTask 3.3: 优化分组字段选择下拉菜单的显示
- [x] SubTask 3.4: 添加分组统计信息展示（总记录数、可见记录数）
- [x] SubTask 3.5: 完善响应式布局适配

**状态**: ✅ 已完成 - GroupPanel 已集成所有功能

**验收标准**:
- 支持拖拽调整分组字段顺序
- 最多支持3个分组字段
- 显示分组统计信息
- 移动端正常显示

---

### Task 4: 表格视图集成分组展示
**描述**: 在 TableView.vue 中集成 GroupedTableView，根据 groupBy 配置切换展示模式

**子任务**:
- [x] SubTask 4.1: 修改 `src/components/views/TableView/TableView.vue`，添加 groupBy 属性支持
- [x] SubTask 4.2: 根据 groupBy 长度决定使用普通表格或 GroupedTableView
- [x] SubTask 4.3: 传递分组配置和事件到 GroupedTableView
- [x] SubTask 4.4: 处理分组行的展开/折叠事件
- [x] SubTask 4.5: 确保筛选和排序在分组模式下正常工作

**状态**: ✅ 已完成 - Base.vue 中已集成 GroupedTableView 和普通 TableView 的条件渲染

**验收标准**:
- groupBy 为空时显示普通表格
- groupBy 有值时显示分组表格
- 分组表格正确展示层级结构
- 展开/折叠功能正常

---

### Task 5: 工具栏添加分组按钮和面板
**描述**: 在 Base.vue 的工具栏添加分组按钮，点击展开/收起分组面板

**子任务**:
- [x] SubTask 5.1: 在 `src/views/Base.vue` 工具栏添加"分组"按钮
- [x] SubTask 5.2: 添加分组面板显示状态管理
- [x] SubTask 5.3: 集成 GroupPanel 组件
- [x] SubTask 5.4: 实现分组面板与 viewStore 的数据绑定
- [x] SubTask 5.5: 添加分组按钮的激活状态显示

**状态**: ✅ 已完成 - Base.vue 中已添加分组按钮和面板集成

**验收标准**:
- 工具栏显示"分组"按钮
- 点击按钮展开/收起分组面板
- 分组面板与表格视图联动
- 按钮在有分组配置时显示激活状态

---

### Task 6: 测试验证
**描述**: 全面测试分组功能的各项场景

**子任务**:
- [x] SubTask 6.1: 测试单级分组功能
- [x] SubTask 6.2: 测试多级分组功能（2级、3级）
- [x] SubTask 6.3: 测试分组展开/折叠功能
- [x] SubTask 6.4: 测试分组配置持久化
- [x] SubTask 6.5: 测试响应式布局
- [x] SubTask 6.6: 测试与筛选、排序的兼容性
- [x] SubTask 6.7: 运行所有单元测试确保无回归 (80 tests passed)

**状态**: ✅ 已完成 - 构建成功，所有测试通过

**验收标准**:
- 所有功能场景测试通过
- 无功能回归
- 代码覆盖率不降低

---

## 实现优先级
1. **P0 (必须)**: Task 1, Task 2, Task 4, Task 5 - 核心功能
2. **P1 (重要)**: Task 3 - 用户体验优化
3. **P2 (可选)**: Task 6 - 测试覆盖

## 预估工时
- Task 1: 0.5 天
- Task 2: 1 天
- Task 3: 1.5 天
- Task 4: 2 天
- Task 5: 1 天
- Task 6: 1 天
- **总计**: 7 天
