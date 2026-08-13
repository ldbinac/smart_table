import { defineStore } from "pinia";
import { ref, watch } from "vue";
import {
  type SupportedLocale,
  DEFAULT_LOCALE,
} from "@/i18n/types";
import { setI18nLanguage } from "@/i18n";

export interface AppSettings {
  theme: "light" | "dark" | "auto";
  language: SupportedLocale;
  sidebarCollapsed: boolean;
  tableRowHeight: "short" | "medium" | "tall";
  showGridLines: boolean;
  stripeRows: boolean;
  autoSave: boolean;
  autoSaveInterval: number;
  confirmBeforeDelete: boolean;
  showRecordCount: boolean;
  dateFormat: string;
  timeFormat: string;
  numberFormat: string;
  currencySymbol: string;
}

const defaultSettings: AppSettings = {
  theme: "light",
  language: DEFAULT_LOCALE,
  sidebarCollapsed: false,
  tableRowHeight: "medium",
  showGridLines: true,
  stripeRows: false,
  autoSave: true,
  autoSaveInterval: 5000,
  confirmBeforeDelete: true,
  showRecordCount: true,
  dateFormat: "YYYY-MM-DD",
  timeFormat: "HH:mm:ss",
  numberFormat: "#,##0.00",
  currencySymbol: "¥",
};

const STORAGE_KEY = "smart-table-settings";

export const useSettingsStore = defineStore("settings", () => {
  const settings = ref<AppSettings>({ ...defaultSettings });
  const loading = ref(false);

  function loadSettings() {
    loading.value = true;
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        settings.value = { ...defaultSettings, ...parsed };
      }
    } catch (e) {
      console.error("Failed to load settings:", e);
    } finally {
      loading.value = false;
    }
  }

  function saveSettings() {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(settings.value));
    } catch (e) {
      console.error("Failed to save settings:", e);
    }
  }

  function updateSettings<K extends keyof AppSettings>(
    key: K,
    value: AppSettings[K],
  ) {
    settings.value[key] = value;
    saveSettings();
  }

  function updateMultipleSettings(newSettings: Partial<AppSettings>) {
    settings.value = { ...settings.value, ...newSettings };
    saveSettings();
  }

  function resetSettings() {
    settings.value = { ...defaultSettings };
    saveSettings();
  }

  function toggleSidebar() {
    settings.value.sidebarCollapsed = !settings.value.sidebarCollapsed;
    saveSettings();
  }

  function setTheme(theme: "light" | "dark" | "auto") {
    settings.value.theme = theme;
    saveSettings();
    applyTheme(theme);
  }

  function applyTheme(theme: "light" | "dark" | "auto") {
    const root = document.documentElement;
    if (theme === "auto") {
      const prefersDark = window.matchMedia(
        "(prefers-color-scheme: dark)",
      ).matches;
      root.classList.toggle("dark", prefersDark);
    } else {
      root.classList.toggle("dark", theme === "dark");
    }
  }

  function setLanguage(language: SupportedLocale) {
    settings.value.language = language;
    setI18nLanguage(language);
    saveSettings();
  }

  watch(
    () => settings.value.theme,
    (newTheme) => {
      applyTheme(newTheme);
    },
    { immediate: true },
  );

  loadSettings();

  // 初始化时将 settingsStore 中的语言同步到 vue-i18n 实例
  setI18nLanguage(settings.value.language);

  return {
    settings,
    loading,
    loadSettings,
    saveSettings,
    updateSettings,
    updateMultipleSettings,
    resetSettings,
    toggleSidebar,
    setTheme,
    setLanguage,
    applyTheme,
  };
});
