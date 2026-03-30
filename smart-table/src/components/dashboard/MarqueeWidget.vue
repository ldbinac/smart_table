<template>
  <div class="marquee-widget" :class="{ 'dark-mode': config.darkMode, [`direction-${config.direction}`]: true }">
    <div class="marquee-header" v-if="config.title">
      <span class="title-icon">📢</span>
      <span class="title-text">{{ config.title }}</span>
    </div>
    <div class="marquee-container" :style="containerStyle">
      <div class="marquee-content" :style="contentStyle">
        <span class="text-item" v-for="(item, index) in displayItems" :key="index">
          <span class="bullet">•</span>
          {{ item.text }}
        </span>
        <!-- 复制一份用于无缝滚动 -->
        <span class="text-item duplicate" v-for="(item, index) in displayItems" :key="`dup-${index}`">
          <span class="bullet">•</span>
          {{ item.text }}
        </span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue';

interface MarqueeItem {
  text: string;
  link?: string;
  type?: 'info' | 'warning' | 'success' | 'error';
}

interface MarqueeConfig {
  title?: string;
  speed?: number; // 速度值，越小越快（秒）
  direction?: 'left' | 'right';
  darkMode?: boolean;
  pauseOnHover?: boolean;
  itemGap?: number;
}

interface MarqueeData {
  items?: MarqueeItem[];
}

const props = defineProps<{
  config: MarqueeConfig;
  data?: MarqueeData;
}>();

const defaultConfig: Required<MarqueeConfig> = {
  title: '',
  speed: 20,
  direction: 'left',
  darkMode: false,
  pauseOnHover: true,
  itemGap: 48
};

const mergedConfig = computed(() => ({
  ...defaultConfig,
  ...props.config
}));

const defaultItems: MarqueeItem[] = [
  { text: '欢迎使用 Smart Table 智能数据管理系统', type: 'info' },
  { text: '系统运行正常', type: 'success' },
  { text: '今日新增数据 1,234 条', type: 'info' }
];

const displayItems = computed(() => {
  return props.data?.items || defaultItems;
});

const containerStyle = computed(() => ({
  '--marquee-speed': `${mergedConfig.value.speed}s`,
  '--item-gap': `${mergedConfig.value.itemGap}px`
}));

const contentStyle = computed(() => {
  const direction = mergedConfig.value.direction;
  return {
    animationDirection: direction === 'right' ? 'reverse' : 'normal'
  };
});
</script>

<style scoped lang="scss">
.marquee-widget {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 10px 40px rgba(79, 172, 254, 0.3);
  transition: all 0.3s ease;

  &.dark-mode {
    background: linear-gradient(135deg, #1e3c72 0%, #2a5298 100%);
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.4);

    .marquee-header {
      background: rgba(0, 0, 0, 0.2);
      border-bottom-color: rgba(255, 255, 255, 0.1);
    }

    .marquee-container {
      background: rgba(0, 0, 0, 0.15);
    }
  }

  .marquee-header {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px 20px;
    background: rgba(255, 255, 255, 0.2);
    border-bottom: 1px solid rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(10px);

    .title-icon {
      font-size: 18px;
    }

    .title-text {
      font-size: 14px;
      font-weight: 600;
      color: white;
      letter-spacing: 0.5px;
    }
  }

  .marquee-container {
    padding: 16px 0;
    background: rgba(255, 255, 255, 0.1);
    overflow: hidden;
    position: relative;

    &:hover .marquee-content {
      animation-play-state: paused;
    }

    .marquee-content {
      display: flex;
      white-space: nowrap;
      animation: marquee var(--marquee-speed, 20s) linear infinite;
      will-change: transform;

      .text-item {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        padding: 0 var(--item-gap, 48px);
        font-size: 15px;
        font-weight: 500;
        color: white;
        flex-shrink: 0;

        .bullet {
          color: rgba(255, 255, 255, 0.8);
          font-size: 8px;
        }

        &.info .bullet { color: #60a5fa; }
        &.warning .bullet { color: #fbbf24; }
        &.success .bullet { color: #34d399; }
        &.error .bullet { color: #f87171; }
      }
    }
  }
}

@keyframes marquee {
  0% {
    transform: translateX(0);
  }
  100% {
    transform: translateX(-50%);
  }
}

// 响应式适配
@media (max-width: 768px) {
  .marquee-widget {
    .marquee-header {
      padding: 10px 16px;

      .title-text {
        font-size: 13px;
      }
    }

    .marquee-container {
      padding: 12px 0;

      .marquee-content {
        .text-item {
          font-size: 13px;
          padding: 0 32px;
        }
      }
    }
  }
}
</style>
