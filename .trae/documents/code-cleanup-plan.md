# 代码清理与重构计划

## 项目扫描结果汇总

本次扫描对 `smart-table/src` 目录下的所有代码进行了全面分析，发现以下问题：

---

## 一、重复代码（可重构）

### 1. 配色方案重复定义

**问题描述**：
`freshColors` 配色方案在多个文件中重复定义：
- `src/views/Dashboard.vue` (第 112-127 行)
- `src/views/DashboardShare.vue` (第 21-36 行)

**重复代码**：
```typescript
const freshColors = {
  primary: "#3B82F6",
  primaryLight: "#EFF6FF",
  success: "#10B981",
  warning: "#F59E0B",
  danger: "#EF4444",
  gray50: "#F9FAFB",
  gray100: "#F3F4F6",
  gray200: "#E5E7EB",
  gray300: "#D1D5DB",
  gray400: "#9CA3AF",
  gray500: "#6B7280",
  gray600: "#4B5563",
  gray700: "#374151",
  gray800: "#1F2937",
};
```

**修复方案**：
1. 在 `src/utils/helpers.ts` 中添加共享的配色方案常量
2. 在需要使用的地方导入该常量

### 2. 防抖函数重复实现

**问题描述**：
`debounce` 函数在以下位置重复实现：
- `src/utils/debounce.ts` (已存在)
- `src/views/Home.vue` (第 119-129 行) - 自定义实现

**修复方案**：
1. 删除 `Home.vue` 中的自定义防抖实现
2. 使用 `src/utils/debounce.ts` 中导出的防抖函数

### 3. 日期格式化函数重复

**问题描述**：
日期格式化逻辑在多处重复：
- `src/utils/helpers.ts` 中的 `formatDate` 函数
- `src/utils/export/index.ts` 中的多处 `toLocaleDateString` 调用
- `src/utils/group.ts` 中的日期分组逻辑

**修复方案**：
1. 统一使用 `src/utils/helpers.ts` 中的 `formatDate` 函数
2. 导出并复用该函数

### 4. 导出功能代码重复

**问题描述**：
`src/utils/export/index.ts` 文件中存在大量重复的格式化逻辑：
- `formatValueForExcel` 函数在类方法和独立函数中重复定义
- `formatValueForCSV` 函数在类方法和独立函数中重复定义
- `escapeCSV` 函数重复定义

**修复方案**：
1. 提取公共的格式化函数
2. 类方法和独立函数都调用公共函数

---

## 二、安全漏洞

### 1. Formula Engine 中的代码注入风险

**问题位置**：`src/utils/formula/engine.ts` 第 227-242 行

**问题代码**：
```typescript
private safeEval(expression: string): unknown {
  const sanitized = expression.replace(
    /[^0-9+\-*/().,%<>=!&|?:'" \t\n]/g,
    "",
  );

  if (sanitized !== expression) {
    throw new Error("Invalid expression");
  }

  try {
    return Function(`"use strict"; return (${expression})`)();
  } catch {
    return expression;
  }
}
```

**风险评估**：
- 使用 `Function` 构造函数执行动态代码
- 虽然有过滤，但仍存在潜在的代码注入风险

**修复方案**：
1. 使用更安全的方式执行数学表达式
2. 考虑使用 `mathjs` 等库或自定义表达式解析器
3. 加强输入验证

### 2. localStorage 存储敏感数据

**问题位置**：
- `src/stores/settingsStore.ts` (第 47, 61 行)
- `src/stores/theme.ts` (第 8, 29 行)
- `src/components/filters/FilterPanel.vue` (第 112-114 行)

**问题描述**：
使用 localStorage 存储用户设置和筛选预设，虽然这不是严重的安全漏洞，但存在以下风险：
- 数据可被 XSS 攻击读取
- 存储大小限制

**修复方案**：
1. 对于敏感数据，考虑使用 `sessionStorage` 或内存存储
2. 添加数据验证和清理
3. 对于筛选预设，考虑存储在数据库中

---

## 三、无效/死代码

### 1. 调试用的 console 语句

**问题描述**：
项目中存在大量调试用的 `console.log`、`console.error`、`console.warn` 语句，影响生产环境性能。

**主要文件**：
- `src/views/Base.vue` - 约 20+ 处
- `src/views/Dashboard.vue` - 约 10+ 处
- `src/stores/viewStore.ts` - 约 10+ 处

**修复方案**：
1. 删除所有调试用的 console 语句
2. 对于必要的错误日志，使用更专业的日志库

### 2. 未使用的导入

**问题描述**：
部分文件存在未使用的导入语句。

**需要检查的文件**：
- `src/components/fields/index.ts` - 可能缺少部分导出
- `src/components/filters/index.ts`
- `src/components/sorts/index.ts`
- `src/components/groups/index.ts`

### 3. 重复的主题管理

**问题描述**：
存在两个主题管理 store：
- `src/stores/theme.ts`
- `src/stores/settingsStore.ts` (包含 theme 设置)

**修复方案**：
1. 合并主题管理逻辑
2. 保留一个主题管理源

---

## 四、修复任务清单

### 高优先级

1. **修复 Formula Engine 安全漏洞**
   - 文件：`src/utils/formula/engine.ts`
   - 操作：替换 `Function` 构造函数为更安全的表达式解析

2. **删除调试 console 语句**
   - 文件：`src/views/Base.vue`, `src/views/Dashboard.vue`, `src/stores/viewStore.ts`
   - 操作：删除所有 `console.log` 调试语句

3. **提取共享配色方案**
   - 文件：`src/utils/helpers.ts`, `src/views/Dashboard.vue`, `src/views/DashboardShare.vue`
   - 操作：将配色方案提取到 helpers.ts 并导出

### 中优先级

4. **统一防抖函数使用**
   - 文件：`src/views/Home.vue`
   - 操作：使用 `src/utils/debounce.ts` 中的防抖函数

5. **重构导出功能重复代码**
   - 文件：`src/utils/export/index.ts`
   - 操作：提取公共格式化函数

6. **合并主题管理**
   - 文件：`src/stores/theme.ts`, `src/stores/settingsStore.ts`
   - 操作：统一主题管理逻辑

### 低优先级

7. **清理未使用的导入**
   - 文件：所有组件 index.ts 文件
   - 操作：检查并删除未使用的导入

8. **优化 localStorage 使用**
   - 文件：`src/components/filters/FilterPanel.vue`
   - 操作：添加数据验证

---

## 五、修复原则

1. **保持功能不变**：所有修改不得影响现有功能
2. **保持样式不变**：不得修改任何 UI 样式
3. **保持交互逻辑不变**：不得修改业务逻辑和交互流程
4. **代码质量提升**：提高代码可维护性和安全性

---

## 六、验证计划

修复完成后需要验证：
1. 项目可以正常构建 (`npm run build`)
2. 所有测试通过 (`npm run test`)
3. 主要功能正常工作：
   - 仪表盘显示
   - 数据表操作
   - 公式计算
   - 数据导出
   - 主题切换
