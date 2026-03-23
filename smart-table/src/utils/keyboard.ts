import { onMounted, onUnmounted } from 'vue'

export interface KeyboardShortcut {
  key: string
  ctrl?: boolean
  shift?: boolean
  alt?: boolean
  meta?: boolean
  handler: (event: KeyboardEvent) => void
  preventDefault?: boolean
  description?: string
}

export function useKeyboardShortcuts(shortcuts: KeyboardShortcut[]) {
  function handleKeyDown(event: KeyboardEvent) {
    for (const shortcut of shortcuts) {
      const keyMatch = event.key.toLowerCase() === shortcut.key.toLowerCase()
      const ctrlMatch = shortcut.ctrl ? (event.ctrlKey || event.metaKey) : !event.ctrlKey
      const shiftMatch = shortcut.shift ? event.shiftKey : !event.shiftKey
      const altMatch = shortcut.alt ? event.altKey : !event.altKey
      
      if (keyMatch && ctrlMatch && shiftMatch && altMatch) {
        if (shortcut.preventDefault !== false) {
          event.preventDefault()
        }
        shortcut.handler(event)
        return
      }
    }
  }
  
  onMounted(() => {
    window.addEventListener('keydown', handleKeyDown)
  })
  
  onUnmounted(() => {
    window.removeEventListener('keydown', handleKeyDown)
  })
}

export function formatShortcut(shortcut: KeyboardShortcut): string {
  const parts: string[] = []
  
  if (shortcut.ctrl) {
    parts.push('Ctrl')
  }
  if (shortcut.shift) {
    parts.push('Shift')
  }
  if (shortcut.alt) {
    parts.push('Alt')
  }
  if (shortcut.meta) {
    parts.push('⌘')
  }
  
  parts.push(shortcut.key.toUpperCase())
  
  return parts.join(' + ')
}

export const defaultShortcuts: KeyboardShortcut[] = [
  {
    key: 's',
    ctrl: true,
    handler: () => console.log('Save'),
    description: '保存'
  },
  {
    key: 'z',
    ctrl: true,
    handler: () => console.log('Undo'),
    description: '撤销'
  },
  {
    key: 'y',
    ctrl: true,
    handler: () => console.log('Redo'),
    description: '重做'
  },
  {
    key: 'c',
    ctrl: true,
    handler: () => console.log('Copy'),
    description: '复制'
  },
  {
    key: 'v',
    ctrl: true,
    handler: () => console.log('Paste'),
    description: '粘贴'
  },
  {
    key: 'a',
    ctrl: true,
    handler: () => console.log('Select All'),
    description: '全选'
  },
  {
    key: 'Delete',
    handler: () => console.log('Delete'),
    description: '删除'
  },
  {
    key: 'Escape',
    handler: () => console.log('Cancel'),
    description: '取消'
  },
  {
    key: 'Enter',
    handler: () => console.log('Confirm'),
    description: '确认'
  },
  {
    key: 'F2',
    handler: () => console.log('Edit'),
    description: '编辑'
  },
  {
    key: '/',
    ctrl: true,
    handler: () => console.log('Search'),
    description: '搜索'
  },
  {
    key: 'n',
    ctrl: true,
    handler: () => console.log('New'),
    description: '新建'
  }
]

export function createShortcut(
  key: string,
  handler: (event: KeyboardEvent) => void,
  options: Partial<Omit<KeyboardShortcut, 'key' | 'handler'>> = {}
): KeyboardShortcut {
  return {
    key,
    handler,
    ...options
  }
}
