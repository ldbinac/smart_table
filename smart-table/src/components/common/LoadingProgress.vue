<template>
  <div v-if="visible" class="loading-progress">
    <div class="progress-bar-container">
      <div class="progress-bar" :style="{ width: `${progress}%` }"></div>
    </div>
    <div class="progress-text">
      <span class="loading-icon">
        <el-icon><Loading /></el-icon>
      </span>
      <span>加载中 {{ loadedCount }}/{{ totalCount }} 条记录</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';
import { Loading } from '@element-plus/icons-vue';

interface Props {
  loadedCount: number;
  totalCount: number;
  visible: boolean;
}

const props = defineProps<Props>();

const progress = computed(() => {
  if (props.totalCount === 0) return 0;
  return Math.min((props.loadedCount / props.totalCount) * 100, 100);
});
</script>

<style lang="scss" scoped>
.loading-progress {
  position: fixed;
  bottom: 20px;
  right: 20px;
  background: white;
  border-radius: 8px;
  padding: 12px 16px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  z-index: 1000;
  min-width: 240px;
}

.progress-bar-container {
  width: 100%;
  height: 4px;
  background: #e5e7eb;
  border-radius: 2px;
  overflow: hidden;
  margin-bottom: 8px;
}

.progress-bar {
  height: 100%;
  background: #3b82f6;
  border-radius: 2px;
  transition: width 0.3s ease;
}

.progress-text {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
  color: #6b7280;
}

.loading-icon {
  display: inline-flex;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}
</style>
