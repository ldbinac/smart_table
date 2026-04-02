# 字段管理校验功能完善方案

## 一、需求概述

完善字段管理中的校验功能，实现以下三种字段类型的自动校验：

1. **邮箱字段 (EMAIL)** - 校验是否为正确的邮箱地址格式
2. **手机号字段 (PHONE)** - 校验是否为有效的手机号码格式
3. **链接字段 (URL)** - 校验是否为完整的网页链接（支持 http/https/ftp/sftp）

## 二、技术方案

### 2.1 校验规则设计

#### 邮箱字段校验规则
```typescript
// 邮箱校验正则表达式
const EMAIL_REGEX = /^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$/;

// 校验逻辑
function validateEmail(value: string): ValidationResult {
  if (!value) return { valid: true }; // 空值由必填校验处理
  
  const valid = EMAIL_REGEX.test(value);
  return {
    valid,
    error: valid ? undefined : '请输入正确的邮箱地址格式，如：example@domain.com'
  };
}
```

#### 手机号字段校验规则
```typescript
// 手机号校验正则表达式（支持中国大陆手机号）
const PHONE_REGEX = /^1[3-9]\d{9}$/;

// 校验逻辑
function validatePhone(value: string): ValidationResult {
  if (!value) return { valid: true };
  
  // 去除空格和横线
  const cleaned = value.replace(/[\s-]/g, '');
  const valid = PHONE_REGEX.test(cleaned);
  
  return {
    valid,
    error: valid ? undefined : '请输入正确的11位手机号码'
  };
}
```

#### 链接字段校验规则
```typescript
// 链接校验正则表达式（支持 http/https/ftp/sftp）
const URL_REGEX = /^(https?|ftp|sftp):\/\/[^\s/$.?#].[^\s]*$/i;

// 校验逻辑
function validateUrl(value: string): ValidationResult {
  if (!value) return { valid: true };
  
  const valid = URL_REGEX.test(value);
  return {
    valid,
    error: valid ? undefined : '请输入完整的链接地址，需以 http://、https://、ftp:// 或 sftp:// 开头'
  };
}
```

### 2.2 校验触发时机

| 场景 | 触发时机 | 校验方式 |
|------|----------|----------|
| 表单填写 | 输入框失焦 (blur) 时 | 实时校验 |
| 表单提交 | 提交前统一校验 | 批量校验 |
| 批量导入 | 导入前逐行校验 | 批量校验 |
| API 调用 | 数据保存前 | 服务端校验 |

### 2.3 错误提示方式

1. **输入框失焦校验**：显示红色边框 + 下方错误提示文字
2. **表单提交校验**：聚焦到第一个错误字段，显示错误提示
3. **批量导入校验**：在导入结果中显示校验失败的行和原因

## 三、实现步骤

### 第一阶段：基础校验函数实现

#### 任务 1：扩展 validation.ts 工具函数
**目标**：在 `src/utils/validation.ts` 中添加字段类型校验函数

**实现内容**：
1. 添加 `validateEmail` 函数
2. 添加 `validatePhone` 函数
3. 添加 `validateUrl` 函数
4. 添加统一的 `validateFieldByType` 函数

**代码位置**：`src/utils/validation.ts`

#### 任务 2：扩展字段类型定义
**目标**：在字段类型定义中添加校验相关类型

**实现内容**：
1. 在 `src/types/fields.ts` 中添加 `FieldValidationRule` 类型
2. 在 `FieldOptions` 中添加 `validation` 配置项

**代码位置**：`src/types/fields.ts`

### 第二阶段：表单填写实时校验

#### 任务 3：在字段组件中添加实时校验
**目标**：在 EMAIL、PHONE、URL 字段组件中添加失焦校验

**实现内容**：
1. 修改 `EmailField.vue` 组件，添加 blur 事件校验
2. 修改 `PhoneField.vue` 组件，添加 blur 事件校验
3. 修改 `UrlField.vue` 组件，添加 blur 事件校验

**代码位置**：
- `src/components/fields/EmailField.vue`
- `src/components/fields/PhoneField.vue`
- `src/components/fields/UrlField.vue`

#### 任务 4：在表单对话框中集成校验
**目标**：在 AddRecordDialog 和 RecordDialog 中集成字段校验

**实现内容**：
1. 在表单提交前调用字段校验函数
2. 显示校验错误信息
3. 阻止提交直到所有字段校验通过

**代码位置**：
- `src/components/dialogs/AddRecordDialog.vue`
- `src/components/dialogs/RecordDialog.vue`

### 第三阶段：批量导入校验

#### 任务 5：在导入功能中添加字段校验
**目标**：在数据导入时对 EMAIL、PHONE、URL 字段进行校验

**实现内容**：
1. 修改导入解析逻辑，对特定字段类型进行校验
2. 在校验失败时记录错误信息
3. 在导入结果中显示校验失败的行

**代码位置**：`src/utils/importExport.ts`

### 第四阶段：字段配置界面优化

#### 任务 6：在字段配置面板中添加校验开关
**目标**：允许用户启用/禁用字段校验

**实现内容**：
1. 在 `FieldConfigPanel.vue` 中添加校验启用开关
2. 在 `FieldDialog.vue` 中添加校验配置选项
3. 保存校验配置到字段 options 中

**代码位置**：
- `src/components/fields/FieldConfigPanel.vue`
- `src/components/dialogs/FieldDialog.vue`

## 四、文件变更清单

### 新增/修改文件

```
src/
├── types/
│   └── fields.ts                  # 添加校验相关类型定义
├── utils/
│   └── validation.ts              # 添加字段校验函数
├── components/
│   ├── fields/
│   │   ├── EmailField.vue         # 添加实时校验
│   │   ├── PhoneField.vue         # 添加实时校验
│   │   ├── UrlField.vue           # 添加实时校验
│   │   └── FieldConfigPanel.vue   # 添加校验配置
│   └── dialogs/
│       ├── FieldDialog.vue        # 添加校验配置
│       ├── AddRecordDialog.vue    # 集成表单校验
│       └── RecordDialog.vue       # 集成表单校验
└── utils/
    └── importExport.ts            # 添加导入校验
```

## 五、验收标准

### 功能验收

- [ ] 邮箱字段能够正确校验邮箱格式
- [ ] 手机号字段能够正确校验11位手机号
- [ ] 链接字段能够正确校验 http/https/ftp/sftp 开头的链接
- [ ] 输入框失焦时自动触发校验
- [ ] 校验失败时显示清晰的错误提示
- [ ] 表单提交前进行统一校验
- [ ] 批量导入时对字段进行校验

### 性能验收

- [ ] 校验函数执行时间 < 10ms
- [ ] 批量校验 1000 条数据 < 1s

### 兼容性验收

- [ ] 支持中英文邮箱地址
- [ ] 支持带国家代码的手机号（可选）
- [ ] 支持各种格式的 URL

## 六、分阶段实现计划

| 阶段 | 任务 | 预估工时 | 依赖 |
|------|------|----------|------|
| 第一阶段 | 任务 1-2：基础校验函数 | 2h | 无 |
| 第二阶段 | 任务 3-4：表单实时校验 | 3h | 第一阶段 |
| 第三阶段 | 任务 5：批量导入校验 | 2h | 第一阶段 |
| 第四阶段 | 任务 6：配置界面优化 | 2h | 第一阶段 |

**总计预估工时**：9 小时

---

*文档版本：v1.0*  
*创建时间：2026-04-01*  
*最后更新：2026-04-01*
