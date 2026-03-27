<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useBaseStore } from "@/stores";
import { dashboardService } from "@/db/services/dashboardService";
import type { Dashboard, TableEntity } from "@/db/schema";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  Search,
  DataAnalysis,
  Document,
  Rank,
  StarFilled,
  MoreFilled,
  Edit,
  Star,
  Delete,
  Plus,
} from "@element-plus/icons-vue";
import Sortable from "sortablejs";

const props = defineProps<{
  // 当前选中的数据表ID
  currentTableId?: string;
  // 当前选中的仪表盘ID
  currentDashboardId?: string;
  // 是否显示数据表列表
  showTables?: boolean;
  // 是否显示仪表盘列表
  showDashboards?: boolean;
}>();

const emit = defineEmits<{
  // 选择数据表
  (e: "select-table", tableId: string): void;
  // 选择仪表盘
  (e: "select-dashboard", dashboardId: string): void;
  // 添加数据表
  (e: "add-table"): void;
  // 添加仪表盘
  (e: "add-dashboard"): void;
  // 重命名数据表
  (e: "rename-table", table: TableEntity): void;
  // 删除数据表
  (e: "delete-table", table: TableEntity): void;
  // 切换收藏状态
  (e: "toggle-star", table: TableEntity): void;
  // 重命名仪表盘
  (e: "rename-dashboard", dashboard: Dashboard): void;
  // 删除仪表盘
  (e: "delete-dashboard", dashboard: Dashboard): void;
  // 切换仪表盘收藏状态
  (e: "toggle-star-dashboard", dashboard: Dashboard): void;
  // 仪表盘排序变更
  (e: "reorder-dashboards", dashboardIds: string[]): void;
}>();

const route = useRoute();
const router = useRouter();
const baseStore = useBaseStore();

// 侧边栏展开/收缩状态
const isCollapsed = ref(false);

// 搜索关键词
const searchKeyword = ref("");

// 仪表盘列表
const dashboards = ref<Dashboard[]>([]);

// 仪表盘列表的ref，用于拖拽排序
const dashboardListRef = ref<HTMLElement | null>(null);
const tableListRef = ref<HTMLElement | null>(null);

// 切换侧边栏状态
const toggleSidebar = () => {
  isCollapsed.value = !isCollapsed.value;
};

// 过滤后的数据表列表
const filteredTables = computed(() => {
  if (!searchKeyword.value.trim()) {
    return baseStore.sortedTables;
  }
  const keyword = searchKeyword.value.toLowerCase();
  return baseStore.sortedTables.filter((table) =>
    table.name.toLowerCase().includes(keyword),
  );
});

// 排序后的仪表盘列表（收藏的置顶）
const sortedDashboards = computed(() => {
  return [...dashboards.value].sort((a, b) => {
    // 收藏的置顶
    if (a.isStarred && !b.isStarred) return -1;
    if (!a.isStarred && b.isStarred) return 1;
    // 按 order 排序
    return a.order - b.order;
  });
});

// 过滤后的仪表盘列表
const filteredDashboards = computed(() => {
  let result = sortedDashboards.value;
  if (searchKeyword.value.trim()) {
    const keyword = searchKeyword.value.toLowerCase();
    result = result.filter((dashboard) =>
      dashboard.name.toLowerCase().includes(keyword),
    );
  }
  return result;
});

// 是否有搜索结果
const hasSearchResults = computed(() => {
  return filteredTables.value.length > 0 || filteredDashboards.value.length > 0;
});

// 加载仪表盘列表
const loadDashboards = async () => {
  if (!baseStore.currentBase) return;
  dashboards.value = await dashboardService.getDashboardsByBase(
    baseStore.currentBase.id,
  );
};

// 处理点击数据表
const handleTableClick = (tableId: string) => {
  emit("select-table", tableId);
};

// 处理点击仪表盘
const handleDashboardClick = (dashboardId: string) => {
  emit("select-dashboard", dashboardId);
};

// 处理打开添加数据表对话框
const handleAddTable = () => {
  emit("add-table");
};

// 处理打开添加仪表盘对话框
const handleAddDashboard = () => {
  emit("add-dashboard");
};

// 处理打开重命名对话框
const handleRenameTable = (table: TableEntity) => {
  emit("rename-table", table);
};

// 处理删除数据表
const handleDeleteTable = (table: TableEntity) => {
  emit("delete-table", table);
};

// 处理切换收藏状态
const handleToggleStar = (table: TableEntity) => {
  emit("toggle-star", table);
};

// 处理重命名仪表盘
const handleRenameDashboard = (dashboard: Dashboard) => {
  emit("rename-dashboard", dashboard);
};

// 处理删除仪表盘
const handleDeleteDashboard = async (dashboard: Dashboard) => {
  try {
    await ElMessageBox.confirm(
      `确定要删除仪表盘 "${dashboard.name}" 吗？`,
      "删除确认",
      {
        confirmButtonText: "删除",
        cancelButtonText: "取消",
        type: "warning",
      },
    );
    emit("delete-dashboard", dashboard);
  } catch {
    // 用户取消删除
  }
};

// 处理切换仪表盘收藏状态
const handleToggleStarDashboard = (dashboard: Dashboard) => {
  emit("toggle-star-dashboard", dashboard);
};

// 初始化仪表盘拖拽排序
const initDashboardSortable = () => {
  if (!dashboardListRef.value) return;

  Sortable.create(dashboardListRef.value, {
    handle: ".drag-handle",
    animation: 150,
    onEnd: (evt) => {
      if (evt.oldIndex === evt.newIndex) return;

      // 获取排序后的仪表盘ID列表
      const dashboardIds = filteredDashboards.value.map((d) => d.id);
      // 移动元素
      const [movedId] = dashboardIds.splice(evt.oldIndex!, 1);
      dashboardIds.splice(evt.newIndex!, 0, movedId);

      emit("reorder-dashboards", dashboardIds);
    },
  });
};

// 初始化数据表拖拽排序
const initTableSortable = () => {
  if (!tableListRef.value) return;

  Sortable.create(tableListRef.value, {
    handle: ".drag-handle",
    animation: 150,
    onEnd: (evt) => {
      if (evt.oldIndex === evt.newIndex) return;
      // 数据表排序由父组件处理
      emit("reorder-tables", evt);
    },
  });
};

// 监听base变化，重新加载仪表盘
watch(
  () => baseStore.currentBase?.id,
  () => {
    loadDashboards();
  },
);

onMounted(() => {
  loadDashboards();
  // 延迟初始化拖拽，确保DOM已渲染
  setTimeout(() => {
    initDashboardSortable();
    initTableSortable();
  }, 100);
});

// 暴露方法给父组件
defineExpose({
  refreshDashboards: loadDashboards,
  isCollapsed,
});
</script>

<template>
  <aside class="base-sidebar" :class="{ collapsed: isCollapsed }">
    <!-- 头部：搜索框和收缩按钮 -->
    <div class="sidebar-header">
      <div class="header-content" v-show="!isCollapsed">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索数据表和仪表盘"
          clearable
          size="small">
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
      </div>
      <button
        class="collapse-btn"
        @click="toggleSidebar"
        :title="isCollapsed ? '展开' : '收起'">
        <span v-if="isCollapsed" class="collapse-icon">&gt;&gt;</span>
        <span v-else class="collapse-icon">&lt;&lt;</span>
      </button>
    </div>

    <!-- 搜索结果为空提示 -->
    <div
      v-if="searchKeyword && !hasSearchResults && !isCollapsed"
      class="search-empty">
      没有找到匹配的内容
    </div>

    <!-- 仪表盘列表 -->
    <div
      v-if="showDashboards !== false && filteredDashboards.length > 0"
      class="dashboard-section">
      <div v-show="!isCollapsed" class="section-title">
        仪表盘
        <span class="section-count">({{ filteredDashboards.length }})</span>
      </div>
      <div ref="dashboardListRef" class="dashboard-list">
        <template v-for="dashboard in filteredDashboards" :key="dashboard.id">
          <!-- 收缩状态下的仪表盘项（带Tooltip） -->
          <el-tooltip
            v-if="isCollapsed"
            :content="dashboard.name"
            placement="right"
            :show-after="300">
            <div
              class="dashboard-item"
              :class="{ active: currentDashboardId === dashboard.id }"
              @click="handleDashboardClick(dashboard.id)">
              <el-icon class="dashboard-icon"><DataAnalysis /></el-icon>
            </div>
          </el-tooltip>
          <!-- 展开状态下的仪表盘项 -->
          <div
            v-else
            class="dashboard-item"
            :class="{ active: currentDashboardId === dashboard.id }"
            @click="handleDashboardClick(dashboard.id)">
            <span class="drag-handle" @click.stop>
              <el-icon><Rank /></el-icon>
            </span>
            <el-icon class="dashboard-icon"><DataAnalysis /></el-icon>
            <span class="dashboard-name">{{ dashboard.name }}</span>
            <span v-if="dashboard.isStarred" class="star-icon">
              <el-icon><StarFilled /></el-icon>
            </span>
            <el-dropdown
              trigger="click"
              @command="
                (cmd) => {
                  if (cmd === 'rename') handleRenameDashboard(dashboard);
                  else if (cmd === 'delete') handleDeleteDashboard(dashboard);
                  else if (cmd === 'star') handleToggleStarDashboard(dashboard);
                }
              "
              @click.stop>
              <span class="more-icon" @click.stop>
                <el-icon><MoreFilled /></el-icon>
              </span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="rename">
                    <el-icon><Edit /></el-icon>重命名
                  </el-dropdown-item>
                  <el-dropdown-item command="star">
                    <el-icon
                      ><component
                        :is="dashboard.isStarred ? 'Star' : 'StarFilled'"
                    /></el-icon>
                    {{ dashboard.isStarred ? "取消收藏" : "收藏" }}
                  </el-dropdown-item>
                  <el-dropdown-item
                    divided
                    command="delete"
                    class="delete-item">
                    <el-icon><Delete /></el-icon>删除
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </template>
      </div>
    </div>

    <!-- 分隔线 -->
    <div
      v-if="
        showDashboards !== false &&
        filteredDashboards.length > 0 &&
        showTables !== false &&
        filteredTables.length > 0
      "
      class="section-divider"></div>

    <!-- 数据表列表 -->
    <div
      v-if="showTables !== false && filteredTables.length > 0"
      class="table-section">
      <div v-show="!isCollapsed" class="section-title">
        数据表
        <span class="section-count">({{ filteredTables.length }})</span>
      </div>
      <div ref="tableListRef" class="table-list">
        <template v-for="table in filteredTables" :key="table.id">
          <!-- 收缩状态下的表格项（带Tooltip） -->
          <el-tooltip
            v-if="isCollapsed"
            :content="table.name"
            placement="right"
            :show-after="300">
            <div
              class="table-item"
              :class="{ active: currentTableId === table.id }"
              @click="handleTableClick(table.id)">
              <el-icon class="table-icon"><Document /></el-icon>
            </div>
          </el-tooltip>
          <!-- 展开状态下的表格项 -->
          <div
            v-else
            class="table-item"
            :class="{ active: currentTableId === table.id }"
            @click="handleTableClick(table.id)">
            <span class="drag-handle" @click.stop>
              <el-icon><Rank /></el-icon>
            </span>
            <el-icon class="table-icon"><Document /></el-icon>
            <span class="table-name">{{ table.name }}</span>
            <span v-if="table.isStarred" class="star-icon">
              <el-icon><StarFilled /></el-icon>
            </span>
            <el-dropdown
              trigger="click"
              @command="
                (cmd) => {
                  if (cmd === 'rename') handleRenameTable(table);
                  else if (cmd === 'delete') handleDeleteTable(table);
                  else if (cmd === 'star') handleToggleStar(table);
                }
              "
              @click.stop>
              <span class="more-icon" @click.stop>
                <el-icon><MoreFilled /></el-icon>
              </span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="rename">
                    <el-icon><Edit /></el-icon>重命名
                  </el-dropdown-item>
                  <el-dropdown-item command="star">
                    <el-icon
                      ><component :is="table.isStarred ? 'Star' : 'StarFilled'"
                    /></el-icon>
                    {{ table.isStarred ? "取消收藏" : "收藏" }}
                  </el-dropdown-item>
                  <el-dropdown-item
                    divided
                    command="delete"
                    class="delete-item">
                    <el-icon><Delete /></el-icon>删除
                  </el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </template>
      </div>
    </div>

    <!-- 底部按钮 -->
    <div class="sidebar-footer">
      <div class="footer-buttons-column">
        <el-button
          v-if="showTables !== false"
          type="primary"
          text
          @click="handleAddTable"
          class="footer-btn">
          <el-icon><Plus /></el-icon>
          <span v-show="!isCollapsed">添加数据表</span>
        </el-button>
        <el-button
          v-if="showDashboards !== false"
          type="primary"
          text
          @click="handleAddDashboard"
          class="footer-btn">
          <el-icon><DataAnalysis /></el-icon>
          <span v-show="!isCollapsed">添加仪表盘</span>
        </el-button>
      </div>
    </div>
  </aside>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;

.base-sidebar {
  width: $sidebar-width;
  display: flex;
  flex-direction: column;
  border-right: 1px solid $border-color;
  background: $surface-color;
  transition: width $transition-normal;
  overflow: hidden;
  flex-shrink: 0;
  height: 100%;

  &.collapsed {
    width: $sidebar-collapsed-width;

    .sidebar-header {
      justify-content: center;
      padding: $spacing-md $spacing-sm;

      .header-content {
        display: none;
      }
    }

    .section-title {
      display: none;
    }

    .table-list,
    .dashboard-list {
      padding: $spacing-sm 0;
    }

    .table-item,
    .dashboard-item {
      justify-content: center;
      padding: $spacing-md $spacing-sm;
      gap: 0;

      .drag-handle,
      .table-name,
      .dashboard-name,
      .star-icon,
      .more-icon {
        display: none;
      }

      .table-icon,
      .dashboard-icon {
        margin: 0;
      }
    }

    .search-empty {
      display: none;
    }

    .sidebar-footer {
      padding: $spacing-sm;

      .footer-buttons-column {
        flex-direction: column;
      }

      .footer-btn {
        padding: $spacing-sm;
        justify-content: center;

        span:not(.el-icon) {
          display: none;
        }
      }
    }
  }
}

.sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: $spacing-md $spacing-lg;
  border-bottom: 1px solid $border-color;
  min-height: 56px;
  gap: $spacing-sm;

  .header-content {
    flex: 1;
    min-width: 0;

    :deep(.el-input) {
      width: 100%;
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
  flex-shrink: 0;
  font-family: monospace;
  font-weight: bold;
  font-size: 12px;

  &:hover {
    background-color: $bg-color;
    color: $text-primary;
  }

  .collapse-icon {
    letter-spacing: -2px;
  }
}

.search-empty {
  padding: $spacing-lg;
  text-align: center;
  color: $text-secondary;
  font-size: $font-size-sm;
}

.dashboard-section,
.table-section {
  display: flex;
  flex-direction: column;
}

.section-title {
  padding: $spacing-sm $spacing-lg;
  font-size: $font-size-xs;
  font-weight: 600;
  color: $text-secondary;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  display: flex;
  align-items: center;
  justify-content: space-between;

  .section-count {
    font-weight: normal;
    color: $text-disabled;
  }
}

.section-divider {
  height: 1px;
  background-color: $border-color;
  margin: $spacing-sm $spacing-lg;
}

.dashboard-list,
.table-list {
  overflow-y: auto;
  padding: $spacing-sm 0;
  max-height: 300px; // 限制最大高度，避免过度扩张
}

.dashboard-item,
.table-item {
  display: flex;
  align-items: center;
  padding: $spacing-sm $spacing-lg;
  cursor: pointer;
  transition: background-color $transition-fast;
  gap: $spacing-sm;

  &:hover {
    background-color: $bg-color;

    .more-icon {
      opacity: 1;
    }
  }

  &.active {
    background-color: rgba($primary-color, 0.1);
    border-right: 3px solid $primary-color;

    .table-icon,
    .dashboard-icon {
      color: $primary-color;
    }
  }
}

.drag-handle {
  cursor: grab;
  color: $text-disabled;
  display: flex;
  align-items: center;

  &:hover {
    color: $text-secondary;
  }

  &:active {
    cursor: grabbing;
  }
}

.table-icon,
.dashboard-icon {
  color: $text-secondary;
  flex-shrink: 0;
}

.table-name,
.dashboard-name {
  flex: 1;
  font-size: $font-size-sm;
  color: $text-primary;
  @include text-ellipsis;
}

.star-icon {
  color: #f7ba2a;
  display: flex;
  align-items: center;
}

.more-icon {
  color: $text-secondary;
  cursor: pointer;
  padding: $spacing-xs;
  border-radius: $border-radius-sm;
  display: flex;
  align-items: center;
  opacity: 0;
  transition: opacity $transition-fast;

  &:hover {
    background-color: $bg-color;
    color: $text-primary;
  }
}

.sidebar-footer {
  padding: $spacing-md;
  border-top: 1px solid $border-color;
  margin-top: auto;

  .footer-buttons-column {
    display: flex;
    flex-direction: column;
    gap: $spacing-sm;
  }

  .footer-btn {
    width: 100%;
    justify-content: flex-start;
    padding-left: $spacing-sm;
  }
}

// 下拉菜单样式
:deep(.delete-item) {
  color: $error-color;
}
</style>
