<script setup lang="ts">
import { computed } from "vue";
import { useKeyboardShortcutsStore } from "@/stores/keyboardShortcuts";

const props = defineProps<{
  visible: boolean;
}>();

const emit = defineEmits<{
  close: [];
}>();

const shortcutsStore = useKeyboardShortcutsStore();

const groupedShortcuts = computed(() => shortcutsStore.groupedShortcuts);

function getLabel(shortcut: {
  key: string;
  ctrl?: boolean;
  shift?: boolean;
  alt?: boolean;
}) {
  return shortcutsStore.getShortcutLabel(shortcut as any);
}
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div v-if="visible" class="shortcut-overlay" @click="emit('close')">
        <Transition name="scale">
          <div v-if="visible" class="shortcut-dialog" @click.stop>
            <div class="shortcut-header">
              <h2>键盘快捷键</h2>
              <button class="close-btn" @click="emit('close')">✕</button>
            </div>
            <div class="shortcut-content">
              <div
                v-for="(shortcuts, category) in groupedShortcuts"
                :key="category"
                class="shortcut-group">
                <h3 class="shortcut-category">{{ category }}</h3>
                <div class="shortcut-list">
                  <div
                    v-for="shortcut in shortcuts"
                    :key="shortcut.id"
                    class="shortcut-item">
                    <span class="shortcut-description">{{
                      shortcut.description
                    }}</span>
                    <span class="shortcut-keys">{{ getLabel(shortcut) }}</span>
                  </div>
                </div>
              </div>
            </div>
            <div class="shortcut-footer">
              <span class="shortcut-hint">按 <kbd>?</kbd> 显示此帮助</span>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<style lang="scss" scoped>
.shortcut-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.shortcut-dialog {
  background-color: var(--surface-color);
  border-radius: 12px;
  box-shadow: var(--shadow-lg);
  width: 90%;
  max-width: 600px;
  max-height: 80vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.shortcut-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color);

  h2 {
    font-size: 18px;
    font-weight: 600;
    color: var(--text-primary);
    margin: 0;
  }
}

.close-btn {
  background: none;
  border: none;
  font-size: 18px;
  color: var(--text-secondary);
  cursor: pointer;
  padding: 4px;
  line-height: 1;

  &:hover {
    color: var(--text-primary);
  }
}

.shortcut-content {
  flex: 1;
  overflow-y: auto;
  padding: 16px 20px;
}

.shortcut-group {
  margin-bottom: 20px;

  &:last-child {
    margin-bottom: 0;
  }
}

.shortcut-category {
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  margin-bottom: 12px;
}

.shortcut-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.shortcut-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 8px 12px;
  background-color: var(--bg-color);
  border-radius: 6px;
}

.shortcut-description {
  font-size: 14px;
  color: var(--text-primary);
}

.shortcut-keys {
  display: flex;
  gap: 4px;

  kbd {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 24px;
    height: 24px;
    padding: 0 6px;
    background-color: var(--surface-color);
    border: 1px solid var(--border-color);
    border-radius: 4px;
    font-family: inherit;
    font-size: 12px;
    font-weight: 500;
    color: var(--text-secondary);
    box-shadow: 0 1px 0 var(--border-color);
  }
}

.shortcut-footer {
  padding: 12px 20px;
  border-top: 1px solid var(--border-color);
  text-align: center;
}

.shortcut-hint {
  font-size: 13px;
  color: var(--text-secondary);

  kbd {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 24px;
    height: 22px;
    padding: 0 6px;
    background-color: var(--bg-color);
    border: 1px solid var(--border-color);
    border-radius: 4px;
    font-family: inherit;
    font-size: 12px;
    margin: 0 4px;
  }
}
</style>
