# 首页新建多维表选择功能 - 实施计划

## [x] Task 1: 创建新建选择对话框
- **Priority**: P0
- **Depends On**: None
- **Description**: 
  - 在Home.vue中添加新建选择对话框的状态变量（createChoiceDialogVisible）
  - 创建选择对话框UI，包含两个选项卡片：创建空白多维表、从模板创建
  - 每个选项包含图标、标题和描述
  - 确保对话框样式与现有系统一致
- **Acceptance Criteria Addressed**: [AC-1, AC-4]
- **Test Requirements**:
  - `human-judgement` TR-1.1: 点击"新建"按钮显示选择对话框
  - `human-judgement` TR-1.2: 对话框包含两个选项
  - `human-judgement` TR-1.3: 选项有清晰的图标和描述
  - `human-judgement` TR-1.4: 样式与现有系统一致
- **Notes**: 使用Element Plus的el-dialog组件

## [x] Task 2: 实现创建空白多维表选项
- **Priority**: P0
- **Depends On**: [Task 1]
- **Description**: 
  - 实现选择"创建空白多维表"选项的处理逻辑
  - 关闭选择对话框
  - 打开原有的创建对话框（openCreateDialog）
  - 确保流程顺畅
- **Acceptance Criteria Addressed**: [AC-2]
- **Test Requirements**:
  - `human-judgement` TR-2.1: 选择"创建空白多维表"后打开创建对话框
  - `programmatic` TR-2.2: 创建对话框功能正常
- **Notes**: 复用现有的openCreateDialog函数

## [x] Task 3: 实现从模板创建选项
- **Priority**: P0
- **Depends On**: [Task 1]
- **Description**: 
  - 实现选择"从模板创建"选项的处理逻辑
  - 关闭选择对话框
  - 导航到模板视图（currentNav = 'templates'）
  - 确保导航流畅
- **Acceptance Criteria Addressed**: [AC-3]
- **Test Requirements**:
  - `human-judgement` TR-3.1: 选择"从模板创建"后跳转到模板页面
  - `programmatic` TR-3.2: 模板页面正常显示
- **Notes**: 使用现有的currentNav状态

## [x] Task 4: 修改新建按钮点击逻辑
- **Priority**: P0
- **Depends On**: [Task 1]
- **Description**: 
  - 修改首页"新建"按钮的点击事件处理
  - 从直接打开创建对话框改为打开选择对话框
  - 确保按钮样式和行为不变
- **Acceptance Criteria Addressed**: [AC-1]
- **Test Requirements**:
  - `human-judgement` TR-4.1: 点击"新建"按钮显示选择界面
  - `human-judgement` TR-4.2: 按钮样式保持不变
- **Notes**: 修改header中的create-btn点击事件

## [x] Task 5: 添加选择对话框样式
- **Priority**: P1
- **Depends On**: [Task 1]
- **Description**: 
  - 为选择对话框添加样式
  - 设计选项卡片的悬停效果
  - 确保响应式适配
  - 添加图标和视觉引导
- **Acceptance Criteria Addressed**: [AC-4]
- **Test Requirements**:
  - `human-judgement` TR-5.1: 选项卡片有清晰的视觉区分
  - `human-judgement` TR-5.2: 悬停效果流畅
  - `human-judgement` TR-5.3: 移动端显示正常
- **Notes**: 使用SCSS，保持与现有样式一致

# Task Dependencies
- [Task 2] depends on [Task 1]
- [Task 3] depends on [Task 1]
- [Task 4] depends on [Task 1]
- [Task 5] depends on [Task 1]
