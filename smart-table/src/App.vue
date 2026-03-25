<script setup lang="ts">
import { onMounted, computed } from 'vue'
import { useRoute } from 'vue-router'
import MainLayout from '@/layouts/MainLayout.vue'
import BlankLayout from '@/layouts/BlankLayout.vue'
import { useThemeStore } from '@/stores/theme'
import { useKeyboardShortcutsStore } from '@/stores/keyboardShortcuts'

const route = useRoute()
const themeStore = useThemeStore()
const keyboardStore = useKeyboardShortcutsStore()

// 根据路由决定使用哪个布局
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
