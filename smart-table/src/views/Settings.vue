<script setup lang="ts">
import { useSettingsStore } from '@/stores';

const settingsStore = useSettingsStore();
</script>

<template>
  <div class="settings-page">
    <header class="settings-header">
      <h1>设置</h1>
    </header>
    <main class="settings-content">
      <el-card>
        <template #header>
          <span>外观设置</span>
        </template>
        <el-form label-width="120px">
          <el-form-item label="主题">
            <el-radio-group
              :model-value="settingsStore.settings.theme"
              @change="(val) => settingsStore.setTheme(val as 'light' | 'dark' | 'auto')"
            >
              <el-radio value="light">浅色</el-radio>
              <el-radio value="dark">深色</el-radio>
              <el-radio value="auto">跟随系统</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="语言">
            <el-select
              :model-value="settingsStore.settings.language"
              @change="(val) => settingsStore.setLanguage(val as 'zh-CN' | 'en-US')"
            >
              <el-option label="简体中文" value="zh-CN" />
              <el-option label="English" value="en-US" />
            </el-select>
          </el-form-item>
        </el-form>
      </el-card>

      <el-card class="mt-4">
        <template #header>
          <span>表格设置</span>
        </template>
        <el-form label-width="120px">
          <el-form-item label="行高">
            <el-radio-group
              :model-value="settingsStore.settings.tableRowHeight"
              @change="(val) => settingsStore.updateSettings('tableRowHeight', val as 'short' | 'medium' | 'tall')"
            >
              <el-radio value="short">紧凑</el-radio>
              <el-radio value="medium">中等</el-radio>
              <el-radio value="tall">宽松</el-radio>
            </el-radio-group>
          </el-form-item>
          <el-form-item label="显示网格线">
            <el-switch
              :model-value="settingsStore.settings.showGridLines"
              @change="(val) => settingsStore.updateSettings('showGridLines', val as boolean)"
            />
          </el-form-item>
          <el-form-item label="斑马纹">
            <el-switch
              :model-value="settingsStore.settings.stripeRows"
              @change="(val) => settingsStore.updateSettings('stripeRows', val as boolean)"
            />
          </el-form-item>
        </el-form>
      </el-card>

      <el-card class="mt-4">
        <template #header>
          <span>数据设置</span>
        </template>
        <el-form label-width="120px">
          <el-form-item label="自动保存">
            <el-switch
              :model-value="settingsStore.settings.autoSave"
              @change="(val) => settingsStore.updateSettings('autoSave', val as boolean)"
            />
          </el-form-item>
          <el-form-item label="删除前确认">
            <el-switch
              :model-value="settingsStore.settings.confirmBeforeDelete"
              @change="(val) => settingsStore.updateSettings('confirmBeforeDelete', val as boolean)"
            />
          </el-form-item>
        </el-form>
      </el-card>

      <el-card class="mt-4">
        <template #header>
          <span>格式设置</span>
        </template>
        <el-form label-width="120px">
          <el-form-item label="日期格式">
            <el-input
              :model-value="settingsStore.settings.dateFormat"
              @change="(val) => settingsStore.updateSettings('dateFormat', val as string)"
            />
          </el-form-item>
          <el-form-item label="时间格式">
            <el-input
              :model-value="settingsStore.settings.timeFormat"
              @change="(val) => settingsStore.updateSettings('timeFormat', val as string)"
            />
          </el-form-item>
          <el-form-item label="货币符号">
            <el-input
              :model-value="settingsStore.settings.currencySymbol"
              @change="(val) => settingsStore.updateSettings('currencySymbol', val as string)"
            />
          </el-form-item>
        </el-form>
      </el-card>

      <div class="mt-4">
        <el-button type="danger" @click="settingsStore.resetSettings">重置为默认设置</el-button>
      </div>
    </main>
  </div>
</template>

<style scoped>
.settings-page {
  padding: 20px;
  max-width: 800px;
  margin: 0 auto;
}

.settings-header {
  margin-bottom: 20px;
}

.mt-4 {
  margin-top: 16px;
}
</style>
