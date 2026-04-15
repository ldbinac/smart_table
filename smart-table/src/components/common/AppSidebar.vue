<script setup lang="ts">
import { ref, computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useAuthStore } from "@/stores/authStore";

interface NavItem {
  id: string;
  label: string;
  icon: string;
  path?: string;
  children?: NavItem[];
  requiresAdmin?: boolean;
}

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

const isCollapsed = ref(false);

// 当前激活的导航项（用于首页内部导航）
const currentActiveNav = computed(() => {
  if (route.path === "/") return "home";
  if (route.path.startsWith("/bases") || route.path.startsWith("/base/"))
    return "bases";
  if (route.path.startsWith("/dashboard")) return "dashboard";
  if (route.path.startsWith("/settings")) return "settings";
  if (route.path.startsWith("/admin")) return "admin";
  return "home";
});

const navItems = computed<NavItem[]>(() => [
  {
    id: "home",
    label: "我的",
    icon: "HomeFilled",
    path: "/",
  },
  // {
  //   id: "bases",
  //   label: "多维表格",
  //   icon: "table",
  //   children: [
  //     { id: "base-1", label: "项目表格", icon: "file", path: "/base/1" },
  //     { id: "base-2", label: "任务管理", icon: "file", path: "/base/2" },
  //   ],
  // },
  // {
  //   id: "dashboard",
  //   label: "仪表盘",
  //   icon: "dashboard",
  //   path: "/base/1/dashboard",
  // },
  {
    id: "settings",
    label: "设置",
    icon: "View",
    path: "/settings",
  },
  ...(authStore.isAdmin
    ? [
        {
          id: "admin",
          label: "系统管理",
          icon: "Setting",
          children: [
            {
              id: "admin-users",
              label: "用户管理",
              icon: "User",
              path: "/admin/users",
            },
            {
              id: "admin-settings",
              label: "系统配置",
              icon: "Setting",
              path: "/admin/settings",
            },
            {
              id: "admin-logs",
              label: "操作日志",
              icon: "Document",
              path: "/admin/logs",
            },
            {
              id: "admin-email-templates",
              label: "邮件模板",
              icon: "Message",
              path: "/admin/email/templates",
            },
            {
              id: "admin-email-logs",
              label: "邮件日志",
              icon: "MessageBox",
              path: "/admin/email/logs",
            },
            {
              id: "admin-email-stats",
              label: "邮件统计",
              icon: "DataLine",
              path: "/admin/email/stats",
            },
          ],
        },
      ]
    : []),
]);

const expandedItems = ref<string[]>(["bases"]);

const toggleCollapse = () => {
  isCollapsed.value = !isCollapsed.value;
};

const toggleExpand = (id: string) => {
  const index = expandedItems.value.indexOf(id);
  if (index > -1) {
    expandedItems.value.splice(index, 1);
  } else {
    expandedItems.value.push(id);
  }
};

const isExpanded = (id: string) => expandedItems.value.includes(id);

const handleNavClick = (item: NavItem) => {
  if (item.children) {
    if (!isCollapsed.value) {
      toggleExpand(item.id);
    }
  } else if (item.path) {
    router.push(item.path);
  }
};

const isActive = (item: NavItem): boolean => {
  if (item.path) {
    if (item.path === "/") {
      return route.path === "/";
    }
    return route.path.startsWith(item.path);
  }
  if (item.children) {
    return item.children.some(
      (child) => child.path && route.path.startsWith(child.path),
    );
  }
  return false;
};
</script>

<template>
  <aside class="app-sidebar" :class="{ collapsed: isCollapsed }">
    <div class="sidebar-header">
      <span v-if="!isCollapsed" class="sidebar-title">导航菜单</span>
      <button class="collapse-btn" @click="toggleCollapse">
        <svg
          v-if="isCollapsed"
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg">
          <path
            d="M9 18L15 12L9 6"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round" />
        </svg>
        <svg
          v-else
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg">
          <path
            d="M15 18L9 12L15 6"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round" />
        </svg>
      </button>
    </div>

    <nav class="sidebar-nav">
      <ul class="nav-list">
        <li v-for="item in navItems" :key="item.id" class="nav-item-wrapper">
          <button
            class="nav-item"
            :class="{ active: isActive(item), expanded: isExpanded(item.id) }"
            @click="handleNavClick(item)">
            <span class="nav-icon">
              <el-icon>
                <component :is="item.icon || Document" />
              </el-icon>
            </span>
            <span v-if="!isCollapsed" class="nav-label">{{ item.label }}</span>
            <span
              v-if="item.children && !isCollapsed"
              class="expand-icon"
              :class="{ expanded: isExpanded(item.id) }">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                xmlns="http://www.w3.org/2000/svg">
                <path
                  d="M6 9L12 15L18 9"
                  stroke="currentColor"
                  stroke-width="2"
                  stroke-linecap="round"
                  stroke-linejoin="round" />
              </svg>
            </span>
          </button>

          <ul
            v-if="item.children && isExpanded(item.id) && !isCollapsed"
            class="sub-nav-list">
            <li v-for="child in item.children" :key="child.id">
              <button
                class="sub-nav-item"
                :class="{
                  active: child.path && route.path.startsWith(child.path),
                }"
                @click="child.path && router.push(child.path)">
                <span class="nav-icon">
                  <el-icon>
                    <component :is="child.icon || Document" />
                  </el-icon>
                </span>
                <span class="nav-label">{{ child.label }}</span>
              </button>
            </li>
          </ul>
        </li>
      </ul>
    </nav>
  </aside>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;
@use "@/assets/styles/mixins" as *;

.app-sidebar {
  width: $sidebar-width;
  height: 100%;
  background-color: $surface-color;
  border-right: 1px solid $border-color;
  display: flex;
  flex-direction: column;
  transition: width $transition-normal;
  overflow: hidden;

  &.collapsed {
    width: $sidebar-collapsed-width;

    .sidebar-header {
      justify-content: center;
      padding: $spacing-md $spacing-sm;
    }

    .nav-item {
      justify-content: center;
      padding: $spacing-md;
    }
  }
}

.sidebar-header {
  @include flex-between;
  padding: $spacing-md $spacing-lg;
  border-bottom: 1px solid $border-color;
  min-height: 56px;
}

.sidebar-title {
  font-size: $font-size-sm;
  font-weight: 600;
  color: $text-secondary;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.collapse-btn {
  @include flex-center;
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

  svg {
    width: 16px;
    height: 16px;
  }
}

.sidebar-nav {
  flex: 1;
  overflow-y: auto;
  @include scrollbar-style;
}

.nav-list {
  padding: $spacing-sm;
}

.nav-item-wrapper {
  margin-bottom: $spacing-xs;
}

.nav-item {
  @include flex-start;
  width: 100%;
  padding: $spacing-sm $spacing-md;
  background: transparent;
  border: none;
  border-radius: $border-radius-md;
  color: $text-secondary;
  font-size: $font-size-sm;
  cursor: pointer;
  transition: all $transition-fast;
  gap: $spacing-sm;

  &:hover {
    background-color: $bg-color;
    color: $text-primary;
  }

  &.active {
    background-color: rgba($primary-color, 0.1);
    color: $primary-color;
  }
}

.nav-icon {
  @include flex-center;
  width: 20px;
  height: 20px;
  flex-shrink: 0;

  svg {
    width: 18px;
    height: 18px;
  }
}

.nav-label {
  flex: 1;
  text-align: left;
  @include text-ellipsis;
}

.expand-icon {
  @include flex-center;
  width: 16px;
  height: 16px;
  transition: transform $transition-fast;

  &.expanded {
    transform: rotate(180deg);
  }

  svg {
    width: 14px;
    height: 14px;
  }
}

.sub-nav-list {
  padding-left: $spacing-xl;
  margin-top: $spacing-xs;

  .sub-nav-item {
    @include flex-start;
    width: 100%;
    padding: $spacing-sm $spacing-md;
    background: transparent;
    border: none;
    border-radius: $border-radius-sm;
    color: $text-secondary;
    font-size: $font-size-sm;
    cursor: pointer;
    transition: all $transition-fast;
    gap: $spacing-sm;

    &:hover {
      background-color: $bg-color;
      color: $text-primary;
    }

    &.active {
      color: $primary-color;
      background-color: rgba($primary-color, 0.08);
    }

    .nav-icon {
      width: 16px;
      height: 16px;

      svg {
        width: 14px;
        height: 14px;
      }
    }
  }
}
</style>
