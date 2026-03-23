<script setup lang="ts">
import { onMounted } from 'vue'
import MainLayout from '@/layouts/MainLayout.vue'
import { useThemeStore } from '@/stores/theme'
import { useKeyboardShortcutsStore } from '@/stores/keyboardShortcuts'

const themeStore = useThemeStore()
const keyboardStore = useKeyboardShortcutsStore()

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
  <MainLayout>
    <router-view v-slot="{ Component, route }">
      <Transition name="slide-fade" mode="out-in">
        <component :is="Component" :key="route.path" />
      </Transition>
    </router-view>
  </MainLayout>
</template>

<style lang="scss">
@use '@/assets/styles/global.scss';
</style>
