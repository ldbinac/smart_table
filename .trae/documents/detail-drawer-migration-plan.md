# 数据详情弹窗 Drawer 抽屉模式迁移方案

## 一、需求概述

将各视图（表格视图、看板视图、日历视图、甘特图视图、画册视图）中的数据详情弹窗，从 Dialog 弹出模式改为右侧拉开的 Drawer 抽屉模式。

## 二、技术方案

### 2.1 组件替换策略

| 原组件 | 新组件 | 说明 |
|--------|--------|------|
| `ElDialog` | `ElDrawer` | Element Plus 抽屉组件 |
| `width="80%"` | `size="50%"` | 抽屉宽度设置 |
| `top="10vh"` | 移除 | 抽屉从右侧滑出 |
| `center` | 移除 | 抽屉内容左对齐 |
| `destroy-on-close` | `destroy-on-close` | 保持相同 |

### 2.2 Drawer 组件属性配置

```vue
<el-drawer
  v-model="visible"
  title="记录详情"
  :size="drawerSize"
  :direction="'rtl'"
  :destroy-on-close="true"
  :close-on-click-modal="true"
  :modal="true"
  class="record-detail-drawer">
  <!-- 内容区域 -->
</el-drawer>
```

### 2.3 响应式宽度设计

```typescript
// 根据屏幕宽度自适应抽屉大小
const drawerSize = computed(() => {
  const width = window.innerWidth;
  if (width < 768) return '100%';
  if (width < 1024) return '70%';
  if (width < 1440) return '50%';
  return '600px';
});
```

## 三、实现步骤

### 第一阶段：表格视图 (TableView)

#### 任务 1：修改表格视图的记录详情弹窗
**目标**：将 TableView 中的 RecordDialog 改为 Drawer 模式

**实现内容**：
1. 在 `TableView.vue` 中找到 `RecordDialog` 的使用位置
2. 将 `ElDialog` 替换为 `ElDrawer`
3. 调整抽屉大小和方向（从右侧滑出）
4. 保持原有的事件处理逻辑

**代码位置**：`src/components/views/TableView/TableView.vue`

**预计修改**：
```vue
<!-- 原代码 -->
<RecordDialog
  v-model:visible="recordDialogVisible"
  :record="selectedRecord"
  @save="handleSaveRecord"
  @delete="handleDeleteRecord" />

<!-- 改为 Drawer 模式 -->
<el-drawer
  v-model="recordDrawerVisible"
  title="记录详情"
  :size="drawerSize"
  direction="rtl"
  destroy-on-close>
  <RecordDetailPanel
    :record="selectedRecord"
    @save="handleSaveRecord"
    @delete="handleDeleteRecord" />
</el-drawer>
```

### 第二阶段：看板视图 (KanbanView)

#### 任务 2：修改看板卡片的详情弹窗
**目标**：将 KanbanView 中的卡片详情改为 Drawer 模式

**实现内容**：
1. 在 `KanbanView.vue` 中找到卡片点击打开详情的逻辑
2. 将 Dialog 替换为 Drawer
3. 保持拖拽和排序功能不受影响

**代码位置**：`src/components/views/KanbanView/KanbanView.vue`

### 第三阶段：日历视图 (CalendarView)

#### 任务 3：修改日历事件的详情弹窗
**目标**：将 CalendarView 中的事件详情改为 Drawer 模式

**实现内容**：
1. 在 `CalendarView.vue` 中找到事件点击打开详情的逻辑
2. 将 Dialog 替换为 Drawer
3. 保持日历的日期切换和事件渲染功能

**代码位置**：`src/components/views/CalendarView/CalendarView.vue`

### 第四阶段：甘特图视图 (GanttView)

#### 任务 4：修改甘特图任务的详情弹窗
**目标**：将 GanttView 中的任务详情改为 Drawer 模式

**实现内容**：
1. 在 `GanttView.vue` 中找到任务条点击打开详情的逻辑
2. 将 Dialog 替换为 Drawer
3. 保持甘特图的时间轴和依赖关系显示

**代码位置**：`src/components/views/GanttView/GanttView.vue`

### 第五阶段：画册视图 (GalleryView)

#### 任务 5：修改画册图片的详情弹窗
**目标**：将 GalleryView 中的图片详情改为 Drawer 模式

**实现内容**：
1. 在 `GalleryView.vue` 中找到图片点击打开详情的逻辑
2. 将 Dialog 替换为 Drawer
3. 保持画册的网格布局和预览功能

**代码位置**：`src/components/views/GalleryView/GalleryView.vue`

### 第六阶段：样式优化

#### 任务 6：统一 Drawer 样式
**目标**：为所有 Drawer 添加统一的样式

**实现内容**：
1. 创建 `record-detail-drawer` 通用样式类
2. 设置抽屉头部样式（标题、关闭按钮）
3. 设置抽屉内容区域样式（滚动、边距）
4. 设置抽屉底部操作栏样式（保存、取消按钮）

**代码位置**：`src/assets/styles/components/_drawer.scss`（新建）

```scss
.record-detail-drawer {
  .el-drawer__header {
    padding: 16px 20px;
    margin-bottom: 0;
    border-bottom: 1px solid #e4e7ed;
    
    .el-drawer__title {
      font-size: 18px;
      font-weight: 600;
      color: #303133;
    }
  }
  
  .el-drawer__body {
    padding: 20px;
    overflow-y: auto;
  }
  
  .drawer-footer {
    position: absolute;
    bottom: 0;
    left: 0;
    right: 0;
    padding: 16px 20px;
    border-top: 1px solid #e4e7ed;
    background: #fff;
    display: flex;
    justify-content: flex-end;
    gap: 12px;
  }
}
```

## 四、文件变更清单

### 修改文件

```
src/
├── components/
│   └── views/
│       ├── TableView/
│       │   └── TableView.vue          # Dialog 改 Drawer
│       ├── KanbanView/
│       │   └── KanbanView.vue         # Dialog 改 Drawer
│       ├── CalendarView/
│       │   └── CalendarView.vue       # Dialog 改 Drawer
│       ├── GanttView/
│       │   └── GanttView.vue          # Dialog 改 Drawer
│       └── GalleryView/
│           └── GalleryView.vue        # Dialog 改 Drawer
└── assets/
    └── styles/
        └── components/
            └── _drawer.scss           # 新建抽屉样式
```

## 五、验收标准

### 功能验收

- [ ] 表格视图点击记录打开 Drawer 抽屉
- [ ] 看板视图点击卡片打开 Drawer 抽屉
- [ ] 日历视图点击事件打开 Drawer 抽屉
- [ ] 甘特图视图点击任务打开 Drawer 抽屉
- [ ] 画册视图点击图片打开 Drawer 抽屉
- [ ] 抽屉从右侧滑出，宽度自适应
- [ ] 抽屉支持点击遮罩关闭
- [ ] 抽屉支持 ESC 键关闭
- [ ] 抽屉内表单数据正常显示和编辑
- [ ] 抽屉内保存、删除功能正常

### 样式验收

- [ ] 抽屉头部显示标题和关闭按钮
- [ ] 抽屉内容区域可滚动
- [ ] 抽屉底部操作栏固定在底部
- [ ] 响应式布局，移动端全屏显示

### 兼容性验收

- [ ] 支持 Chrome、Firefox、Safari、Edge
- [ ] 支持移动端触摸操作
- [ ] 动画过渡流畅

## 六、分阶段实现计划

| 阶段 | 任务 | 预估工时 | 依赖 |
|------|------|----------|------|
| 第一阶段 | 表格视图 Drawer 改造 | 2h | 无 |
| 第二阶段 | 看板视图 Drawer 改造 | 2h | 无 |
| 第三阶段 | 日历视图 Drawer 改造 | 2h |