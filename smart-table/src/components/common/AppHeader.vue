<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRoute } from "vue-router";
import { useBaseStore } from "@/stores";
import { dashboardService } from "@/db/services/dashboardService";
import type { Dashboard } from "@/db/schema";

const route = useRoute();
const baseStore = useBaseStore();

const currentTitle = computed(() => {
  return (route.meta.title as string) || "Smart Table";
});

// 判断是否在Base页面
const isBasePage = computed(() => {
  return route.path.startsWith("/base/");
});

// 判断是否在仪表盘页面
const isDashboardPage = computed(() => {
  return route.path.includes("/dashboard/");
});

// 当前表格信息
const currentTable = computed(() => {
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

// 左侧显示的标题：Base（多维表根）名称或默认标题
const leftTitle = computed(() => {
  if (currentBase.value) {
    return currentBase.value.name;
  }
  return "Smart Table";
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
</script>

<template>
  <header class="app-header">
    <div class="header-left">
      <div class="logo">
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
        <el-tooltip
          :content="leftTitle"
          placement="bottom"
          :show-after="300"
          :disabled="leftTitle.length <= 15">
          <span class="logo-text">{{ leftTitle }}</span>
        </el-tooltip>
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
    </div>

    <div class="header-right">
      <div class="current-title">{{ currentTitle }}</div>
      <div class="user-avatar">
        <svg viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path
            d="M20 21V19C20 17.9391 19.5786 16.9217 18.8284 16.1716C18.0783 15.4214 17.0609 15 16 15H8C6.93913 15 5.92172 15.4214 5.17157 16.1716C4.42143 16.9217 4 17.9391 4 19V21M16 7C16 9.20914 14.2091 11 12 11C9.79086 11 8 9.20914 8 7C8 4.79086 9.79086 3 12 3C14.2091 3 16 4.79086 16 7Z"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round" />
        </svg>
      </div>
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

.logo-text {
  font-size: $font-size-lg;
  font-weight: 600;
  color: $text-primary;
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

.current-title {
  font-size: $font-size-sm;
  color: $text-secondary;
}

.user-avatar {
  @include flex-center;
  width: 32px;
  height: 32px;
  background-color: $bg-color;
  border-radius: 50%;
  cursor: pointer;
  transition: background-color $transition-fast;

  &:hover {
    background-color: color.adjust($bg-color, $lightness: -5%);
  }

  svg {
    width: 18px;
    height: 18px;
    color: $text-secondary;
  }
}
</style>
