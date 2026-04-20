# Checklist

- [x] 类型定义更新
  - [x] `TextFieldType` 类型已定义
  - [x] `TEXT_FIELD_TYPE` 常量已定义
  - [x] `FieldOptions` 接口已更新
  - [x] `getTextFieldType` 辅助函数已实现

- [x] 字段对话框
  - [x] 文本类型选择器已添加
  - [x] 创建字段时正确设置文本类型
  - [x] 编辑字段时正确加载文本类型

- [x] 富文本编辑器组件
  - [x] `RichTextField.vue` 组件已创建
  - [x] 支持加粗、斜体、下划线功能
  - [x] 支持有序/无序列表
  - [x] 支持只读模式

- [x] 记录详情抽屉
  - [x] 单行文本渲染为 `el-input`
  - [x] 多行文本渲染为 `el-input type="textarea"`
  - [x] 富文本渲染为 `RichTextField`

- [x] 添加记录抽屉
  - [x] 单行文本渲染为 `el-input`
  - [x] 多行文本渲染为 `el-input type="textarea"`
  - [x] 富文本渲染为 `RichTextField`

- [x] 表格单元格
  - [x] 正确显示单行文本
  - [x] 正确显示多行文本（支持换行省略）
  - [x] 正确显示富文本（纯文本预览）

- [x] 文本字段组件
  - [x] 支持 `textFieldType` 属性
  - [x] 向后兼容 `isRichText`

- [x] 向后兼容
  - [x] 旧数据使用 `isRichText: true` 正确识别为多行文本
  - [x] 旧数据无 `isRichText` 正确识别为单行文本
