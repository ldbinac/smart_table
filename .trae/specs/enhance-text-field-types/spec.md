# 文本字段类型增强 Spec

## Why
当前系统的文本字段只有一种类型，通过 `isRichText` 开关来区分单行和多行文本。这种设计不够灵活，无法支持富文本编辑需求。需要重构文本字段类型系统，明确区分单行文本、多行文本和富文本三种类型，并在抽屉弹窗中根据类型渲染不同的输入组件。

## What Changes
- **新增**: 文本字段类型配置属性 `textFieldType`，支持 `single_line_text`（单行文本）、`long_text`（多行文本）、`rich_text`（富文本）三种类型
- **修改**: 默认文本字段类型为单行文本 (`single_line_text`)
- **修改**: 字段对话框中增加文本类型选择配置
- **修改**: 记录详情抽屉和添加记录抽屉根据文本类型渲染不同组件：
  - 单行文本：使用 `el-input` 渲染为 input
  - 多行文本：使用 `el-input type="textarea"` 渲染为多行文本
  - 富文本：引入简单的富文本编辑器组件
- **修改**: 表格单元格渲染适配新的文本类型
- **废弃**: 原有的 `isRichText` 选项（保留向后兼容）

## Impact
- Affected specs: 字段类型系统、字段对话框、记录详情抽屉、添加记录抽屉、表格视图
- Affected code: 
  - `src/types/fields.ts` - 类型定义
  - `src/components/dialogs/FieldDialog.vue` - 字段配置对话框
  - `src/components/dialogs/RecordDetailDrawer.vue` - 记录详情抽屉
  - `src/components/dialogs/AddRecordDrawer.vue` - 添加记录抽屉
  - `src/components/fields/TextField.vue` - 文本字段组件
  - `src/components/views/TableView/TableCell.vue` - 表格单元格

## ADDED Requirements

### Requirement: 文本字段类型配置
The system SHALL provide text field type configuration with three options:

#### Scenario: 字段类型选择
- **GIVEN** 用户在创建或编辑文本字段
- **WHEN** 打开字段配置对话框
- **THEN** 显示文本类型选择：单行文本、多行文本、富文本
- **AND** 默认选中"单行文本"

#### Scenario: 单行文本渲染
- **GIVEN** 字段类型为单行文本 (`single_line_text`)
- **WHEN** 在抽屉弹窗中编辑该字段
- **THEN** 渲染为 `el-input` 单行输入框

#### Scenario: 多行文本渲染
- **GIVEN** 字段类型为多行文本 (`long_text`)
- **WHEN** 在抽屉弹窗中编辑该字段
- **THEN** 渲染为 `el-input type="textarea"` 多行文本框
- **AND** 默认显示 3 行高度

#### Scenario: 富文本渲染
- **GIVEN** 字段类型为富文本 (`rich_text`)
- **WHEN** 在抽屉弹窗中编辑该字段
- **THEN** 渲染为富文本编辑器组件
- **AND** 支持基本的文本格式化（加粗、斜体、下划线、列表等）

## MODIFIED Requirements

### Requirement: 字段类型定义
**Current**: 使用 `isRichText` boolean 选项区分多行文本
**Modified**: 使用 `textFieldType: 'single_line_text' | 'long_text' | 'rich_text'` 明确区分类型

**向后兼容处理**:
- 如果字段没有 `textFieldType` 但有 `isRichText: true`，则视为 `long_text`
- 如果字段没有 `textFieldType` 且没有 `isRichText`，则视为 `single_line_text`

### Requirement: 表格单元格显示
- **GIVEN** 多行文本或富文本字段在表格中显示
- **WHEN** 内容超过单元格宽度
- **THEN** 显示省略号，hover 时显示完整内容 tooltip

## REMOVED Requirements
无
