<template>
  <el-dropdown
    trigger="click"
    @command="handleCommand"
    placement="bottom-end">
    <span class="lang-switcher-trigger">
      <el-icon class="lang-icon"><Operation /></el-icon>
      <span class="lang-label">{{ currentFlag }} {{ currentLabel }}</span>
      <el-icon class="lang-arrow"><ArrowDown /></el-icon>
    </span>
    <template #dropdown>
      <el-dropdown-menu>
        <el-dropdown-item
          v-for="lang in AVAILABLE_LANGUAGES"
          :key="lang.value"
          :command="lang.value"
          :class="{ 'is-active': lang.value === current }">
          <span class="dropdown-item-label">
            <span class="dropdown-flag">{{ lang.flag }}</span>
            <span>{{ lang.label }}</span>
            <el-icon v-if="lang.value === current" class="dropdown-check">
              <Check />
            </el-icon>
          </span>
        </el-dropdown-item>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { ArrowDown, Check, Operation } from '@element-plus/icons-vue'
import { useSettingsStore } from '@/stores/settingsStore'
import { AVAILABLE_LANGUAGES, type SupportedLocale } from '@/i18n'

const { locale } = useI18n()
const settingsStore = useSettingsStore()

const current = computed<SupportedLocale>(
  () => (locale.value as SupportedLocale) || settingsStore.settings.language,
)

const currentLabel = computed(() => {
  const opt = AVAILABLE_LANGUAGES.find((l) => l.value === current.value)
  return opt ? opt.label : current.value
})

const currentFlag = computed(() => {
  const opt = AVAILABLE_LANGUAGES.find((l) => l.value === current.value)
  return opt ? opt.flag : ''
})

function handleCommand(lang: string | number | object) {
  settingsStore.setLanguage(lang as SupportedLocale)
}
</script>

<style scoped lang="scss">
.lang-switcher-trigger {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 6px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.2s ease;
  user-select: none;

  &:hover {
    background: rgba(0, 0, 0, 0.06);
  }

  .lang-icon {
    font-size: 16px;
  }

  .lang-label {
    font-size: 14px;
    font-weight: 500;
    line-height: 1;
  }

  .lang-arrow {
    font-size: 12px;
    opacity: 0.6;
  }
}

.dropdown-item-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;

  .dropdown-flag {
    font-size: 16px;
  }

  .dropdown-check {
    margin-left: 4px;
    color: var(--el-color-primary);
  }
}
</style>
