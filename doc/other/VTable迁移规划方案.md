# VTable 迁移规划方案

## 1. 项目概述

### 1.1 项目目标
将 SmartTable 项目中的自定义表格控件替换为 VTable 组件，同时保持所有现有功能和交互操作不变，提高表格性能和可维护性。

### 1.2 当前表格功能分析
当前 SmartTable 的 TableView 组件具备以下核心功能：
- **数据展示**：支持多种字段类型（文本、数字、日期、选择框、关联字段等）
- **行选择**：单选、多选、全选
- **单元格编辑**：行内编辑、双击编辑
- **排序功能**：单列升序/降序
- **列冻结**：左侧列冻结
- **列宽调整**：可拖拽调整列宽
- **右键菜单**：行菜单、列菜单
- **行高配置**：short/medium/tall 三种高度
- **键盘导航**：方向键、删除、ESC 等
- **实时协作**：多用户协同编辑支持
- **记录详情抽屉**：查看/编辑完整记录

### 1.3 VTable 优势
- **高性能**：基于 Canvas 渲染，支持百万级数据量
- **丰富功能**：内置编辑、排序、筛选、冻结、拖拽等
- **灵活定制**：支持自定义单元格渲染和编辑器
- **Vue 友好**：有 Vue 3 封装版本可用

## 2. 技术架构分析

### 2.1 当前组件结构
```
TableView.vue (主容器)
├── TableHeader.vue (表头)
│   └── 排序、冻结、调整列宽
├── TableRow.vue (行)
│   └── 行选择、拖拽
└── TableCell.vue (单元格)
    ├── 18种字段类型渲染
    └── 编辑模式切换
```

### 2.2 数据流向
```
tableStore (Pinia)
├── fields[]
├── records[]
└── realtime updates
    ↓
TableView (computed处理)
├── visibleFields (过滤隐藏字段)
├── sortedRecords (排序)
└── frozenFields (冻结配置)
    ↓
渲染层
```

## 3. 迁移方案

### 3.1 总体策略
采用**渐进式迁移**策略：
1. **第一阶段**：创建 VTable 封装层，保持 API 兼容
2. **第二阶段**：重构表格视图，逐步替换组件
3. **第三阶段**：移除旧代码，完成迁移

### 3.2 核心工作

#### 3.2.1 依赖安装
```bash
# 安装 VTable 及 Vue 封装
npm install @visactor/vtable @visactor/vtable-vue
```

#### 3.2.2 主要文件变更清单

| 文件 | 变更类型 | 说明 |
|------|---------|------|
| `smart-table/package.json` | 修改 | 添加 VTable 依赖 |
| `smart-table/src/components/views/TableView/VTableView.vue` | 新建 | VTable 封装组件 |
| `smart-table/src/components/views/TableView/TableCell.vue` | 重构 | 适配 VTable 的自定义渲染 |
| `smart-table/src/components/views/TableView/index.ts` | 修改 | 导出新组件 |
| `smart-table/src/views/Base.vue` | 修改 | 引入新表格组件 |

#### 3.2.3 核心实现思路

**VTable 配置映射**：
```typescript
// 将 SmartTable 的配置映射到 VTable
const tableOptions = {
  columns: visibleFields.map(field => ({
    field: field.id,
    title: field.name,
    width: columnWidths[field.id] || 150,
    frozen: isFieldFrozen(field.id),
    // 自定义单元格渲染
    render: (record, field) => { /* 使用现有 TableCell 逻辑 */ }
  })),
  data: sortedRecords,
  // 事件绑定
  onCellClick: handleCellClick,
  onCellDblClick: handleCellEdit,
  onColumnResize: handleColumnResize,
  onSort: handleSort
}
```

**自定义渲染器**：
- 保持现有的 `TableCell.vue` 组件作为 VTable 的自定义渲染器
- 通过 VTable 的 `customRender` 或 Vue 插槽机制集成

### 3.3 关键功能保持策略

#### 3.3.1 单元格编辑
- VTable 提供 `editable` 配置
- 复用现有字段类型的编辑组件
- 自定义编辑器适配

#### 3.3.2 行选择
- VTable 内置选择功能
- 映射到现有的 `selectedRows` 状态
- 保持多选/单选/全选逻辑

#### 3.3.3 右键菜单
- 使用 VTable 的 `contextmenu` 事件
- 复用现有的 ContextMenu 组件

#### 3.3.4 实时协作
- VTable 支持数据更新
- 保持现有的 realtime 事件监听逻辑
- 通过 VTable API 更新表格数据

## 4. 分阶段实施计划

### 阶段一：基础框架搭建 (1-2天)
- [ ] 安装 VTable 依赖
- [ ] 创建 VTableView 组件框架
- [ ] 配置基础列和数据展示
- [ ] 验证渲染正确性

### 阶段二：核心功能实现 (3-4天)
- [ ] 实现自定义单元格渲染
- [ ] 实现排序功能
- [ ] 实现列冻结
- [ ] 实现列宽调整
- [ ] 实现行选择

### 阶段三：编辑功能 (3-4天)
- [ ] 实现单元格编辑
- [ ] 适配所有字段类型
- [ ] 实现键盘导航
- [ ] 验证数据保存

### 阶段四：高级功能 (2-3天)
- [ ] 右键菜单集成
- [ ] 实时协作适配
- [ ] 记录详情抽屉
- [ ] 行高配置

### 阶段五：测试和优化 (2-3天)
- [ ] 功能测试
- [ ] 性能测试
- [ ] 用户体验优化
- [ ] 移除旧代码

## 5. 风险评估与应对

| 风险 | 影响 | 概率 | 应对措施 |
|------|------|------|---------|
| VTable 自定义渲染复杂 | 高 | 中 | 提前做技术验证，准备备选方案 |
| 性能不如预期 | 高 | 低 | 利用 VTable 的虚拟滚动特性 |
| 实时协作适配困难 | 中 | 中 | 保持现有事件监听层，只修改更新逻辑 |
| 字段类型兼容性问题 | 中 | 低 | 逐个测试字段类型，保留旧代码作为 fallback |

## 6. 验收标准

### 6.1 功能验收
- [ ] 所有字段类型正常显示和编辑
- [ ] 排序、冻结、列宽调整功能正常
- [ ] 行选择、右键菜单功能正常
- [ ] 键盘导航正常工作
- [ ] 实时协作功能正常

### 6.2 性能验收
- [ ] 1000条记录加载时间 < 1s
- [ ] 滚动流畅度 ≥ 60fps
- [ ] 内存占用不显著增加

### 6.3 兼容性验收
- [ ] 在主要浏览器中正常工作 (Chrome, Firefox, Safari, Edge)
- [ ] 响应式布局正常

## 7. 后续优化方向

迁移完成后，可以考虑以下优化：
1. 利用 VTable 的透视表功能
2. 实现更丰富的数据导出功能
3. 添加图表集成
4. 优化移动端体验

---

**文档版本**：v1.0
**创建日期**：2026-06-01
**最后更新**：2026-06-01
