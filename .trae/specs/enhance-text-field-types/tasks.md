# Tasks

- [x] Task 1: 更新字段类型定义
  - [x] SubTask 1.1: 在 `src/types/fields.ts` 中定义 `TextFieldType` 类型和常量
  - [x] SubTask 1.2: 更新 `FieldOptions` 接口，添加 `textFieldType` 属性
  - [x] SubTask 1.3: 添加向后兼容的辅助函数 `getTextFieldType`

- [x] Task 2: 更新字段对话框配置
  - [x] SubTask 2.1: 在 `FieldDialog.vue` 中添加文本类型选择器（仅文本字段显示）
  - [x] SubTask 2.2: 创建字段时根据选择的文本类型设置 `textFieldType`
  - [x] SubTask 2.3: 编辑字段时正确加载和保存文本类型配置

- [x] Task 3: 实现富文本编辑器组件
  - [x] SubTask 3.1: 创建 `RichTextField.vue` 组件
  - [x] SubTask 3.2: 实现基础富文本编辑功能（加粗、斜体、下划线、列表）
  - [x] SubTask 3.3: 支持只读模式显示

- [x] Task 4: 更新记录详情抽屉
  - [x] SubTask 4.1: 在 `RecordDetailDrawer.vue` 中根据文本类型渲染不同组件
  - [x] SubTask 4.2: 单行文本使用 `el-input`
  - [x] SubTask 4.3: 多行文本使用 `el-input type="textarea"`
  - [x] SubTask 4.4: 富文本使用 `RichTextField` 组件

- [x] Task 5: 更新添加记录抽屉
  - [x] SubTask 5.1: 在 `AddRecordDrawer.vue` 中根据文本类型渲染不同组件
  - [x] SubTask 5.2: 单行文本使用 `el-input`
  - [x] SubTask 5.3: 多行文本使用 `el-input type="textarea"`
  - [x] SubTask 5.4: 富文本使用 `RichTextField` 组件

- [x] Task 6: 更新表格单元格渲染
  - [x] SubTask 6.1: 更新 `TableCell.vue` 适配新的文本类型
  - [x] SubTask 6.2: 多行文本和富文本显示时支持换行和省略

- [x] Task 7: 更新文本字段组件
  - [x] SubTask 7.1: 更新 `TextField.vue` 支持新的 `textFieldType` 属性
  - [x] SubTask 7.2: 保持向后兼容，支持旧的 `isRichText` 选项

# Task Dependencies
- Task 1 必须在 Task 2/3/4/5/6/7 之前完成
- Task 3 必须在 Task 4.4 和 Task 5.4 之前完成
- Task 4 和 Task 5 可以并行
- Task 6 和 Task 7 可以并行
