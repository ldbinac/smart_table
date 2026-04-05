<script setup lang="ts">
import { onMounted, computed, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth/authStore'
import MainLayout from '@/layouts/MainLayout.vue'
import BlankLayout from '@/layouts/BlankLayout.vue'
import { useThemeStore } from '@/stores/theme'
import { useKeyboardShortcutsStore } from '@/stores/keyboardShortcuts'
import { onLogoutEvent } from '@/utils/auth/token'

const route = useRoute()
const authStore = useAuthStore()
const themeStore = useThemeStore()
const keyboardStore = useKeyboardShortcutsStore()

// 监听登出事件，实现多标签页同步
let removeLogoutListener: (() => void) | null = null

// 根据路由配置中指定了使用空白布局
const layoutComponent = computed(() => {
  // 如果路由配置中指定了使用空白布局
  if (route.meta?.layout === 'blank') {
    return BlankLayout
  }
  // 默认使用主布局
  return MainLayout
})

onMounted(() => {
  themeStore.updateDarkMode()
  
  document.addEventListener('keydown', keyboardStore.handleKeyDown)
  
  keyboardStore.registerShortcut({
    id: 'toggle-theme',
    key: 'd',
    ctrl: true,
    description: '切换深色/浅色模式',
    category: '通用',
    action: () => themeStore.toggleTheme()
  })
  
  keyboardStore.registerShortcut({
    id: 'show-shortcuts',
    key: '?',
    shift: true,
    description: '显示快捷键帮助',
    category: '通用',
    action: () => {
      const event = new CustomEvent('show-shortcuts')
      window.dispatchEvent(event)
    }
  })
  
  // 监听登出事件，当其他标签页退出时同步清除状态
  removeLogoutListener = onLogoutEvent(() => {
    // 清除本地状态（但不触发登出事件，避免无限循环）
    authStore.user = null
    authStore.isAuthenticated = false
  })
})

onUnmounted(() => {
  // 清理监听器
  if (removeLogoutListener) {
    removeLogoutListener()
  }
})
</script>

<template>
  <component :is="layoutComponent">
    <router-view v-slot="{ Component, route }">
      <Transition name="slide-fade" mode="out-in">
        <component :is="Component" :key="route.path" />
      </Transition>
    </router-view>
  </component>
</template>

<style lang="scss">
@use '@/assets/styles/global.scss';
</style>
