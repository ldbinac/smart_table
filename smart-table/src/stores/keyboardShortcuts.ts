import { defineStore } from "pinia";
import { ref, computed, onMounted, onUnmounted } from "vue";

export interface KeyboardShortcut {
  id: string;
  key: string;
  ctrl?: boolean;
  shift?: boolean;
  alt?: boolean;
  meta?: boolean;
  description: string;
  category: string;
  action: () => void;
  enabled?: boolean;
}

export const useKeyboardShortcutsStore = defineStore(
  "keyboardShortcuts",
  () => {
    const shortcuts = ref<KeyboardShortcut[]>([]);
    const enabled = ref(true);

    function registerShortcut(shortcut: KeyboardShortcut) {
      const existing = shortcuts.value.find((s) => s.id === shortcut.id);
      if (existing) {
        Object.assign(existing, shortcut);
      } else {
        shortcuts.value.push(shortcut);
      }
    }

    function unregisterShortcut(id: string) {
      const index = shortcuts.value.findIndex((s) => s.id === id);
      if (index !== -1) {
        shortcuts.value.splice(index, 1);
      }
    }

    function getShortcutLabel(shortcut: KeyboardShortcut): string {
      const parts: string[] = [];
      const isMac = navigator.platform.toUpperCase().indexOf("MAC") >= 0;

      if (shortcut.ctrl) parts.push(isMac ? "⌘" : "Ctrl");
      if (shortcut.alt) parts.push(isMac ? "⌥" : "Alt");
      if (shortcut.shift) parts.push(isMac ? "⇧" : "Shift");
      if (shortcut.meta) parts.push("Meta");

      parts.push(shortcut.key.toUpperCase());

      return parts.join(isMac ? "" : "+");
    }

    const groupedShortcuts = computed(() => {
      const groups: Record<string, KeyboardShortcut[]> = {};

      for (const shortcut of shortcuts.value) {
        if (!groups[shortcut.category]) {
          groups[shortcut.category] = [];
        }
        groups[shortcut.category].push(shortcut);
      }

      return groups;
    });

    function handleKeyDown(event: KeyboardEvent) {
      if (!enabled.value) return;

      const target = event.target as HTMLElement;
      if (
        target.tagName === "INPUT" ||
        target.tagName === "TEXTAREA" ||
        target.isContentEditable
      ) {
        return;
      }

      for (const shortcut of shortcuts.value) {
        if (shortcut.enabled === false) continue;

        const keyMatch = event.key.toLowerCase() === shortcut.key.toLowerCase();
        const ctrlMatch = shortcut.ctrl
          ? event.ctrlKey || event.metaKey
          : !event.ctrlKey && !event.metaKey;
        const shiftMatch = shortcut.shift ? event.shiftKey : !event.shiftKey;
        const altMatch = shortcut.alt ? event.altKey : !event.altKey;

        if (keyMatch && ctrlMatch && shiftMatch && altMatch) {
          event.preventDefault();
          shortcut.action();
          return;
        }
      }
    }

    return {
      shortcuts,
      enabled,
      registerShortcut,
      unregisterShortcut,
      getShortcutLabel,
      groupedShortcuts,
      handleKeyDown,
    };
  },
);

export function useKeyboardShortcuts() {
  const store = useKeyboardShortcutsStore();

  function register(shortcut: KeyboardShortcut) {
    store.registerShortcut(shortcut);
  }

  function unregister(id: string) {
    store.unregisterShortcut(id);
  }

  onMounted(() => {
    document.addEventListener("keydown", store.handleKeyDown);
  });

  onUnmounted(() => {
    document.removeEventListener("keydown", store.handleKeyDown);
  });

  return {
    register,
    unregister,
    shortcuts: store.shortcuts,
    groupedShortcuts: store.groupedShortcuts,
    getShortcutLabel: store.getShortcutLabel,
  };
}
