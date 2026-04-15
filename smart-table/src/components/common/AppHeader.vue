<script setup lang="ts">
import { computed, ref, watch, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useBaseStore } from "@/stores";
import { useAuthStore } from "@/stores/auth/authStore";
import { dashboardService } from "@/db/services/dashboardService";
import { ElMessageBox } from "element-plus";
import {
  ArrowDown,
  Share,
  User,
  Search,
  CircleClose,
  Lock,
} from "@element-plus/icons-vue";
import type { Dashboard } from "@/db/schema";
import { debounce } from "@/utils/debounce";

const route = useRoute();
const router = useRouter();
const baseStore = useBaseStore();
const authStore = useAuthStore();

const currentTitle = computed(() => {
  return (route.meta.title as string) || "Smart Table";
});

// 用户菜单控制
const userMenuVisible = ref(false);

// 处理退出登录
const handleLogout = async () => {
  try {
    await ElMessageBox.confirm("确定要退出登录吗？", "退出确认", {
      confirmButtonText: "确定退出",
      cancelButtonText: "取消",
      type: "warning",
    });

    await authStore.logout();
    router.replace("/login");
  } catch {
    // 用户取消退出
  }
};

// 处理退出所有设备
const handleLogoutAll = async () => {
  try {
    await ElMessageBox.confirm(
      "确定要从所有设备退出登录吗？此操作将使您在其他所有设备上也被迫下线。",
      "退出所有设备",
      {
        confirmButtonText: "确定退出",
        cancelButtonText: "取消",
        type: "warning",
      },
    );

    await authStore.logout(true);
    router.replace("/login");
  } catch {
    // 用户取消退出
  }
};

// 处理修改密码 - 跳转到设置页面
const handleChangePassword = () => {
  userMenuVisible.value = false;
  router.push("/settings");
  // 延迟打开修改密码对话框
  setTimeout(() => {
    window.dispatchEvent(new CustomEvent("open-change-password-dialog"));
  }, 100);
};

// 用户信息显示
const userName = computed(() => {
  return authStore.user?.name || "用户";
});

const userEmail = computed(() => {
  return authStore.user?.email || "";
});

// 判断是否在仪表盘页面
const isDashboardPage = computed(() => {
  return route.path.includes("/dashboard/");
});

// 当前表格信息
const currentTable = computed(() => {
  console.log("currentTable:", baseStore);
  return baseStore.currentTable;
});

// 当前仪表盘信息
const currentDashboard = ref<Dashboard | undefined>(undefined);

// 加载仪表盘信息
const loadDashboard = async () => {
  const dashboardId = route.params.dashboardId as string;
  if (dashboardId) {
    try {
      currentDashboard.value = await dashboardService.getDashboard(dashboardId);
    } catch (error) {
      console.error("加载仪表盘失败:", error);
      currentDashboard.value = undefined;
    }
  } else {
    currentDashboard.value = undefined;
  }
};

// 监听路由变化，加载仪表盘信息
watch(() => route.params.dashboardId, loadDashboard, { immediate: true });

// 当前Base（多维表根）信息
const currentBase = computed(() => {
  return baseStore.currentBase;
});

// 是否有管理权限（控制分享和成员按钮显示）
const canManage = computed(() => {
  return baseStore.canManage;
});

// 是否在Base页面
const isBasePage = computed(() => {
  return route.path.startsWith("/base/");
});

// 左侧显示的标题：Base（多维表根）名称或默认标题
const leftTitle = computed(() => {
  if (currentBase.value) {
    return currentBase.value.name;
  }
  return "Smart Table";
});

// 左侧显示的描述：Base（多维表根）描述信息
const leftDescription = computed(() => {
  if (currentBase.value && currentBase.value.description) {
    return currentBase.value.description;
  }
  return "";
});

// 中间显示的信息
const centerInfo = computed(() => {
  if (isDashboardPage.value && currentDashboard.value) {
    return {
      name: currentDashboard.value.name,
      description: currentDashboard.value.description || "",
    };
  }
  if (currentTable.value) {
    return {
      name: currentTable.value.name,
      description: currentTable.value.description || "",
    };
  }
  return null;
});

// 分享按钮点击事件
const handleShareClick = () => {
  // 通过自定义事件通知父组件打开分享对话框
  window.dispatchEvent(new CustomEvent("open-base-share"));
};

// 成员按钮点击事件
const handleMemberClick = () => {
  // 通过自定义事件通知父组件打开成员管理对话框
  window.dispatchEvent(new CustomEvent("open-member-management"));
};

// Logo 点击事件 - 跳转到首页并清空当前 Base
const handleLogoClick = () => {
  baseStore.setCurrentBase(null);
  router.push("/");
};

// ========== 搜索功能（仅在首页显示） ==========
const isHomePage = computed(() => {
  return route.path === "/" || route.path === "/home";
});

// 搜索查询
const searchQuery = ref("");
const searchInputRef = ref<HTMLInputElement | null>(null);

// 防抖搜索输入处理
const handleSearchInput = debounce(() => {
  // 搜索逻辑通过事件传递给 Home.vue
  window.dispatchEvent(
    new CustomEvent("home-search-query-change", {
      detail: { query: searchQuery.value },
    }),
  );
}, 300);

// 清空搜索
const clearSearch = () => {
  searchQuery.value = "";
  searchInputRef.value?.focus();
  window.dispatchEvent(
    new CustomEvent("home-search-query-change", {
      detail: { query: "" },
    }),
  );
};

// 搜索结果统计
const searchStats = computed(() => {
  const query = searchQuery.value.trim().toLowerCase();
  if (!query) return 0;

  const starredCount = baseStore.bases.filter(
    (base) => base.is_starred && base.name.toLowerCase().includes(query),
  ).length;

  const allCount = baseStore.bases.filter((base) =>
    base.name.toLowerCase().includes(query),
  ).length;

  return starredCount + allCount;
});

// 监听来自 Home.vue 的搜索清除事件
onMounted(() => {
  window.addEventListener("home-search-clear", () => {
    searchQuery.value = "";
  });
});
</script>

<template>
  <header class="app-header">
    <div class="header-left">
      <div class="logo" @click="handleLogoClick">
        <svg
          class="logo-icon"
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg">
          <rect x="3" y="3" width="7" height="7" rx="1" fill="#3370FF" />
          <rect
            x="14"
            y="3"
            width="7"
            height="7"
            rx="1"
            fill="#3370FF"
            opacity="0.7" />
          <rect
            x="3"
            y="14"
            width="7"
            height="7"
            rx="1"
            fill="#3370FF"
            opacity="0.7" />
          <rect
            x="14"
            y="14"
            width="7"
            height="7"
            rx="1"
            fill="#3370FF"
            opacity="0.4" />
        </svg>
        <div class="logo-info">
          <el-tooltip
            :content="leftTitle"
            placement="bottom"
            :show-after="300"
            :disabled="leftTitle.length <= 30">
            <span class="logo-text">{{ leftTitle }}</span>
          </el-tooltip>
          <el-tooltip
            v-if="leftDescription"
            :content="leftDescription"
            placement="bottom"
            :show-after="300">
            <span class="logo-description">{{ leftDescription }}</span>
          </el-tooltip>
        </div>
      </div>
    </div>

    <div class="header-center">
      <!-- 在Base页面显示表格或仪表盘名称和描述 -->
      <div v-if="isBasePage && centerInfo" class="table-info-header">
        <el-tooltip
          :content="centerInfo.name"
          placement="bottom"
          :show-after="300"
          :disabled="centerInfo.name.length <= 20">
          <h2 class="table-name">{{ centerInfo.name }}</h2>
        </el-tooltip>
        <el-tooltip
          v-if="centerInfo.description"
          :content="centerInfo.description"
          placement="bottom"
          :show-after="300">
          <p class="table-description">{{ centerInfo.description }}</p>
        </el-tooltip>
      </div>

      <!-- 首页全局搜索框 -->
      <div v-if="isHomePage" class="header-search">
        <div class="search-wrapper">
          <el-icon class="search-icon"><Search /></el-icon>
          <input
            ref="searchInputRef"
            v-model="searchQuery"
            type="text"
            class="search-input"
            placeholder="搜索多维表格..."
            @input="handleSearchInput" />
          <el-icon v-if="searchQuery" class="search-clear" @click="clearSearch">
            <CircleClose />
          </el-icon>
        </div>
        <div v-if="searchQuery" class="search-stats">
          找到 {{ searchStats }} 个结果
        </div>
      </div>
    </div>

    <div class="header-right">
      <!-- Base页面的分享和成员按钮 -->
      <template v-if="isBasePage && currentBase && canManage">
        <el-tooltip
          class="box-item"
          effect="dark"
          content="分享"
          placement="bottom">
          <el-button type="primary" plain circle @click="handleShareClick">
            <el-icon><Share /></el-icon>
          </el-button>
        </el-tooltip>
        <el-tooltip
          class="box-item"
          effect="dark"
          content="成员"
          placement="bottom">
          <el-button
            type="primary"
            plain
            circle
            @click="handleMemberClick"
            style="margin-left: 0px">
            <el-icon><Avatar /></el-icon>
            <!-- <span>成员</span> -->
          </el-button>
        </el-tooltip>
        <el-divider direction="vertical" class="header-divider" />
      </template>
      <!-- <div class="current-title">{{ currentTitle }}</div> -->
      <el-dropdown
        v-model:visible="userMenuVisible"
        trigger="click"
        :hide-on-click="false">
        <div class="user-menu-trigger">
          <el-button type="primary" circle>
            <el-icon><User /></el-icon>
          </el-button>
          <!-- <span class="user-name">{{ userName }}</span> -->
          <el-icon class="user-menu-arrow"><arrow-down /></el-icon>
        </div>
        <template #dropdown>
          <el-dropdown-menu>
            <div class="user-info-panel">
              <div class="user-info-name">{{ userName }}</div>
              <div class="user-info-email">{{ userEmail }}</div>
            </div>
            <el-divider style="margin: 4px 0" />
            <el-dropdown-item @click="handleChangePassword">
              <el-icon><Lock /></el-icon>
              修改密码
            </el-dropdown-item>
            <el-dropdown-item divided @click="handleLogout">
              <el-icon><SwitchButton /></el-icon>
              退出登录
            </el-dropdown-item>
            <el-dropdown-item @click="handleLogoutAll">
              <el-icon><Delete /></el-icon>
              退出所有设备
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>
  </header>
</template>

<style lang="scss" scoped>
@use "sass:color";
@use "@/assets/styles/variables" as *;
@use "@/assets/styles/mixins" as *;

.app-header {
  @include flex-between;
  height: $header-height;
  padding: 0 $spacing-lg;
  background-color: $surface-color;
  border-bottom: 1px solid $border-color;
  box-shadow: $shadow-sm;
  position: relative;
  z-index: 100;
}

.header-left {
  @include flex-start;
  gap: $spacing-lg;
}

.logo {
  @include flex-start;
  gap: $spacing-sm;
  cursor: pointer;
}

.logo-icon {
  width: 28px;
  height: 28px;
}

.logo-info {
  display: flex;
  flex-direction: column;
  gap: $spacing-xs;
  min-width: 0;
}

.logo-text {
  font-size: $font-size-lg;
  font-weight: 800;
  color: $text-primary;
  @include text-ellipsis;
  max-width: 30ch;
  line-height: 1.4;
}

.logo-description {
  font-size: calc($font-size-lg - 3px);
  font-weight: 400;
  color: $text-secondary;
  @include text-ellipsis;
  max-width: 40ch;
  line-height: 1.4;
}

.header-center {
  @include flex-center;
  flex: 1;
  max-width: 600px;
  margin: 0 $spacing-lg;
}

.table-info-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: $spacing-xs;
  max-width: 100%;

  .table-name {
    margin: 0;
    font-size: $font-size-lg;
    font-weight: 600;
    color: $text-primary;
    @include text-ellipsis;
    max-width: 400px;
    line-height: 1.4;
  }

  .table-description {
    margin: 0;
    font-size: $font-size-xs;
    color: $text-secondary;
    @include text-ellipsis;
    max-width: 500px;
    line-height: 1.4;
  }
}

.header-right {
  @include flex-center;
  gap: $spacing-md;
}

.header-action-btn {
  @include flex-center;
  gap: $spacing-xs;
  padding: $spacing-sm;
  font-size: $font-size-sm;
  border-radius: $border-radius-base;

  .el-icon {
    font-size: 14px;
  }
}

.header-divider {
  height: 20px;
  margin: 0 $spacing-xs;
}

.current-title {
  font-size: $font-size-sm;
  color: $text-secondary;
}

.user-menu-trigger {
  @include flex-center;
  gap: $spacing-xs;
  cursor: pointer;
  padding: $spacing-xs $spacing-sm;
  border-radius: $border-radius-base;
  transition: background-color $transition-fast;

  &:hover {
    background-color: color.adjust($bg-color, $lightness: -5%);
  }
}

.user-avatar {
  @include flex-center;
  width: 32px;
  height: 32px;
  background-color: $bg-color;
  border-radius: 50%;
  transition: background-color $transition-fast;

  svg {
    width: 18px;
    height: 18px;
    color: $text-secondary;
  }
}

.user-name {
  font-size: $font-size-sm;
  color: $text-primary;
  font-weight: 500;
  max-width: 120px;
  @include text-ellipsis;
}

.user-menu-arrow {
  font-size: 14px;
  color: $text-secondary;
}

.user-info-panel {
  padding: $spacing-sm $spacing-md;
  min-width: 200px;

  .user-info-name {
    font-size: $font-size-sm;
    font-weight: 600;
    color: $text-primary;
    margin-bottom: 4px;
  }

  .user-info-email {
    font-size: $font-size-xs;
    color: $text-secondary;
    @include text-ellipsis;
    max-width: 240px;
  }
}

// 首页搜索框样式
.header-search {
  width: 100%;
  max-width: 480px;
  position: relative;

  .search-wrapper {
    position: relative;
    display: flex;
    align-items: center;
  }

  .search-icon {
    position: absolute;
    left: 14px;
    color: $text-secondary;
    font-size: 18px;
    z-index: 1;
  }

  .search-input {
    width: 100%;
    height: 40px;
    padding: 0 40px;
    border: 1px solid $border-color;
    border-radius: 20px;
    font-size: $font-size-sm;
    background: $bg-color;
    transition: all 0.2s ease;

    &::placeholder {
      color: $text-secondary;
    }

    &:focus {
      outline: none;
      background: white;
      border-color: $primary-color;
      box-shadow: 0 0 0 3px rgba($primary-color, 0.1);
    }
  }

  .search-clear {
    position: absolute;
    right: 14px;
    color: $text-secondary;
    cursor: pointer;
    font-size: 16px;
    transition: color 0.2s;

    &:hover {
      color: $text-primary;
    }
  }

  .search-stats {
    position: absolute;
    top: 100%;
    left: 16px;
    margin-top: 6px;
    font-size: 12px;
    color: $text-secondary;
  }
}
</style>
