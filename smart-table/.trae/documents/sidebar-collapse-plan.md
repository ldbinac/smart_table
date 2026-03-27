# Base.vue 侧边栏展开/收缩功能实现计划

## 目标
为 Base.vue 中的侧边栏区域（表格列表区域）添加与 AppSidebar 导航菜单一致的展开/收缩交互功能。

## 参考实现
参考 `AppSidebar.vue` 的实现方式：
- 使用 `isCollapsed` 状态控制展开/收缩
- 点击按钮切换状态
- 使用 CSS transition 实现平滑动画
- 收缩时显示图标，隐藏文字
- 展开时显示完整内容

## 实现步骤

### 1. 添加响应式状态
在 Base.vue 的 script setup 部分添加：
```typescript
// 侧边栏展开/收缩状态
const isSidebarCollapsed = ref(false);

// 切换侧边栏状态
const toggleSidebar = () => {
  isSidebarCollapsed.value = !isSidebarCollapsed.value;
};
```

### 2. 修改模板结构
修改侧边栏区域（L910-L986）：
- 在 `sidebar-header` 中添加展开/收缩按钮
- 为 `aside.sidebar` 添加动态 class `:class="{ collapsed: isSidebarCollapsed }"`
- 调整内容显示逻辑：
  - 搜索框：展开时显示，收缩时隐藏
  - 表格列表项：展开时显示名称，收缩时只显示图标
  - 底部按钮：展开时显示文字，收缩时只显示图标

### 3. 添加展开/收缩按钮
在 `sidebar-header` 中添加：
```html
<button class="collapse-btn" @click="toggleSidebar">
  <el-icon v-if="isSidebarCollapsed"><ArrowRight /></el-icon>
  <el-icon v-else><ArrowLeft /></el-icon>
</button>
```

### 4. 修改表格列表项显示
修改 `table-item` 的显示逻辑：
- 展开时：显示拖拽手柄 + 图标 + 名称 + 收藏标记 + 更多按钮
- 收缩时：只显示图标（居中），hover 时显示 tooltip 提示表格名称

### 5. 添加样式
在 style 部分添加：
```scss
.sidebar {
  width: $sidebar-width;
  transition: width $transition-normal;
  overflow: hidden;

  &.collapsed {
    width: $sidebar-collapsed-width;

    .sidebar-header {
      justify-content: center;
      padding: $spacing-md $spacing-sm;
    }

    .sidebar-search {
      display: none;
    }

    .table-item {
      justify-content: center;
      padding: $spacing-sm;

      .drag-handle,
      .table-name,
      .star-icon,
      .more-icon {
        display: none;
      }

      .table-icon {
        margin: 0;
      }
    }

    .sidebar-footer {
      .el-button {
        padding: $spacing-sm;
        
        span:not(.el-icon) {
          display: none;
        }
      }
    }
  }
}

.collapse-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  background: transparent;
  border: none;
  border-radius: $border-radius-sm;
  color: $text-secondary;
  cursor: pointer;
  transition: all $transition-fast;

  &:hover {
    background-color: $bg-color;
    color: $text-primary;
  }
}
```

### 6. 添加 Tooltip 支持
为收缩状态下的表格项添加 tooltip：
```html
<el-tooltip
  v-if="isSidebarCollapsed"
  :content="table.name"
  placement="right"
>
  <!-- 表格项内容 -->
</el-tooltip>
```

### 7. 持久化状态（可选）
将展开/收缩状态保存到 localStorage：
```typescript
// 初始化时读取状态
onMounted(() => {
  const saved = localStorage.getItem('base-sidebar-collapsed');
  if (saved) {
    isSidebarCollapsed.value = JSON.parse(saved);
  }
});

// 切换时保存状态
const toggleSidebar = () => {
  isSidebarCollapsed.value = !isSidebarCollapsed.value;
  localStorage.setItem('base-sidebar-collapsed', JSON.stringify(isSidebarCollapsed.value));
};
```

## 视觉反馈
1. **箭头方向变化**：
   - 展开状态：显示左箭头（提示点击会收缩）
   - 收缩状态：显示右箭头（提示点击会展开）

2. **Hover 效果**：
   - 按钮 hover 时背景色变化
   - 表格项 hover 时背景色变化

3. **平滑动画**：
   - 宽度变化使用 `transition: width $transition-normal`
   - 内容显示/隐藏使用 CSS 控制

## 布局适配
- 侧边栏收缩时，主内容区域自动填充剩余空间
- 使用 flex 布局确保自适应
- 确保收缩状态下不会出现水平滚动条

## 需要导入的图标
- `ArrowLeft` - 展开状态箭头
- `ArrowRight` - 收缩状态箭头

## 修改文件
- `src/views/Base.vue`
