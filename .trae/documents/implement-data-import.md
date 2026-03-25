# 数据导入功能实施计划

## 概述

根据产品规划文档和开发任务清单，实现并完善数据导入功能。数据导入功能支持 Excel (.xlsx, .xls)、CSV、JSON 格式的数据导入，包含字段映射配置和导入预览功能。

## 需求分析

### 来自产品规划文档 (2.7 数据导入导出)
- **导入**: Excel (.xlsx, .xls)、CSV、JSON
- **导出**: Excel、CSV、JSON、PDF
- **模板下载**: 字段模板导出

### 来自开发任务清单 (4.6 导入导出功能)
| 序号 | 任务 | 优先级 | 预计工时 | 状态 |
|-----|------|--------|---------|------|
| 4.6.1 | 集成 SheetJS (xlsx) 库 | P1 | 2h | 🔵 待开始 |
| 4.6.2 | 实现 Excel 导出功能 | P1 | 6h | 🔵 待开始 |
| 4.6.3 | 实现 Excel 导入功能 | P1 | 6h | 🔵 待开始 |
| 4.6.4 | 实现 CSV 导出功能 | P1 | 4h | 🔵 待开始 |
| 4.6.5 | 实现 CSV 导入功能 | P1 | 4h | 🔵 待开始 |
| 4.6.6 | 实现 JSON 导出功能 | P1 | 2h | 🔵 待开始 |
| 4.6.7 | 实现 JSON 导入功能 | P1 | 2h | 🔵 待开始 |
| 4.6.8 | 实现字段映射配置 | P1 | 4h | 🔵 待开始 |
| 4.6.9 | 实现导入预览功能 | P1 | 4h | 🔵 待开始 |

## 当前状态分析

### 需要完成
1. ❌ 安装 SheetJS (xlsx) 库
2. ❌ 创建数据导入对话框组件
3. ❌ 实现 Excel 导入功能
4. ❌ 实现 CSV 导入功能
5. ❌ 实现 JSON 导入功能
6. ❌ 实现字段映射配置
7. ❌ 实现导入预览功能
8. ❌ 在 Base.vue 中集成导入功能

## 实施步骤

### 步骤 1: 安装依赖

**安装 SheetJS 库**:
```bash
npm install xlsx
```

### 步骤 2: 创建导入工具函数

**文件**: `src/utils/importExport.ts`

**功能**:
- 解析 Excel 文件 (.xlsx, .xls)
- 解析 CSV 文件
- 解析 JSON 文件
- 数据类型转换
- 字段映射处理

### 步骤 3: 创建数据导入对话框组件

**文件**: `src/components/dialogs/ImportDialog.vue`

**功能**:
1. **文件上传**: 支持拖拽上传和点击选择
2. **格式选择**: 自动识别或手动选择文件格式
3. **字段映射**: 将导入文件的列映射到表格字段
4. **数据预览**: 显示前 N 行数据预览
5. **导入执行**: 批量创建记录
6. **进度显示**: 显示导入进度和结果

**界面布局**:
```
┌─────────────────────────────────────────┐
│  数据导入                                │
├─────────────────────────────────────────┤
│  步骤 1: 选择文件                        │
│  ┌─────────────────────────────────┐   │
│  │  📁 拖拽文件到此处或点击上传      │   │
│  │     支持 .xlsx, .xls, .csv, .json │   │
│  └─────────────────────────────────┘   │
├─────────────────────────────────────────┤
│  步骤 2: 字段映射                        │
│  ┌──────────────┬────────────────────┐ │
│  │ 文件列        │ 映射到表格字段      │ │
│  ├──────────────┼────────────────────┤ │
│  │ 姓名          │ [姓名 ▼]           │ │
│  │ 年龄          │ [年龄 ▼]           │ │
│  │ 邮箱          │ [邮箱 ▼]           │ │
│  └──────────────┴────────────────────┘ │
├─────────────────────────────────────────┤
│  步骤 3: 数据预览 (前 5 行)              │
│  ┌───────────────────────────────────┐ │
│  │ [表格预览导入数据]                 │ │
│  └───────────────────────────────────┘ │
├─────────────────────────────────────────┤
│  [取消]              [开始导入]          │
└─────────────────────────────────────────┘
```

### 步骤 4: 实现导入逻辑

**数据转换流程**:
1. 读取文件内容
2. 解析为结构化数据
3. 根据字段映射转换数据格式
4. 验证数据有效性
5. 批量创建记录

**字段类型转换**:
| 字段类型 | 转换逻辑 |
|---------|---------|
| text | 直接转为字符串 |
| number | 解析为数字 |
| date | 解析为时间戳 |
| singleSelect | 匹配选项ID |
| multiSelect | 解析为数组，匹配选项ID |
| checkbox | 解析为布尔值 |
| email | 验证邮箱格式 |
| phone | 验证手机格式 |
| url | 验证URL格式 |

### 步骤 5: 在 Base.vue 中集成

**修改内容**:
1. 导入 ImportDialog 组件
2. 添加导入按钮到工具栏
3. 处理导入完成后的数据刷新

### 步骤 6: 添加模板下载功能

**文件**: `src/utils/templateGenerator.ts`

**功能**:
- 根据当前表格字段生成导入模板
- 支持 Excel、CSV、JSON 格式模板
- 包含示例数据和字段说明

## 详细实现

### 1. 文件解析工具函数

```typescript
// 解析 Excel 文件
function parseExcel(file: File): Promise<Record<string, any>[]>

// 解析 CSV 文件
function parseCSV(file: File): Promise<Record<string, any>[]>

// 解析 JSON 文件
function parseJSON(file: File): Promise<Record<string, any>[]>

// 自动检测文件类型并解析
function parseFile(file: File): Promise<{
  data: Record<string, any>[];
  columns: string[];
  format: string;
}>
```

### 2. 字段映射配置

```typescript
interface FieldMapping {
  sourceColumn: string;  // 源文件列名
  targetFieldId: string; // 目标字段ID
  targetFieldName: string; // 目标字段名称
  targetFieldType: FieldType; // 目标字段类型
}

// 自动匹配字段
function autoMatchFields(
  sourceColumns: string[],
  targetFields: FieldEntity[]
): FieldMapping[]
```

### 3. 数据转换

```typescript
// 将导入数据转换为记录值
function convertImportData(
  rowData: Record<string, any>,
  fieldMappings: FieldMapping[]
): Record<string, CellValue>

// 类型转换函数
function convertValue(value: any, targetType: FieldType): CellValue
```

### 4. 数据验证

```typescript
interface ValidationResult {
  valid: boolean;
  errors: string[];
}

// 验证单行数据
function validateRow(
  rowData: Record<string, CellValue>,
  fields: FieldEntity[]
): ValidationResult
```

## 测试计划

1. **功能测试**:
   - 导入 Excel 文件 (.xlsx, .xls)
   - 导入 CSV 文件
   - 导入 JSON 文件
   - 字段映射配置
   - 数据预览功能
   - 导入进度显示

2. **边界测试**:
   - 空文件处理
   - 大文件处理 (10000+ 行)
   - 特殊字符处理
   - 日期格式兼容性
   - 必填字段验证

3. **错误处理测试**:
   - 文件格式错误
   - 数据类型不匹配
   - 必填字段缺失
   - 网络中断恢复

## 时间安排

| 任务 | 预计时间 | 实际时间 |
|-----|---------|---------|
| 安装 SheetJS 库 | 0.5h | - |
| 创建导入工具函数 | 3h | - |
| 创建 ImportDialog 组件 | 6h | - |
| 实现字段映射功能 | 3h | - |
| 实现数据预览功能 | 2h | - |
| Base.vue 集成 | 1h | - |
| 添加模板下载功能 | 2h | - |
| 测试与调试 | 3h | - |
| **总计** | **20.5h** | - |
