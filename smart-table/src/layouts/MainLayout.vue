<script setup lang="ts">
import { ref, computed } from "vue";
import { useRoute } from "vue-router";
import AppHeader from "@/components/common/AppHeader.vue";
import AppSidebar from "@/components/common/AppSidebar.vue";

const route = useRoute();

const sidebarCollapsed = ref(false);

const shouldShowSidebar = computed(() => {
  const hiddenRoutes = ["/", "/settings"];
  return !hiddenRoutes.includes(route.path);
});

const mainContentStyle = computed(() => {
  if (shouldShowSidebar.value) {
    return {
      marginLeft: sidebarCollapsed.value ? "64px" : "8px",
      marginRight: "5px",
    };
  }
  return {};
});
</script>

<template>
  <div class="main-layout">
    <AppHeader />
    <div class="layout-body">
      <AppSidebar
        v-if="shouldShowSidebar"
        @collapse="sidebarCollapsed = $event" />
      <main class="main-content" :style="mainContentStyle">
        <div class="content-wrapper">
          <slot />
        </div>
      </main>
    </div>
  </div>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;
@use "@/assets/styles/mixins" as *;

.main-layout {
  @include flex-column;
  width: 100%;
  height: 100%;
  background-color: $bg-color;
}

.layout-body {
  display: flex;
  flex: 1;
  overflow: hidden;
}

.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  transition: margin-left $transition-normal;
}

.content-wrapper {
  flex: 1;
  overflow: auto;
  @include scrollbar-style;
}
</style>
