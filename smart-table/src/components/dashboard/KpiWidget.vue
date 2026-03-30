<template>
  <div class="kpi-widget" :class="{ 'dark-mode': config.darkMode, [`size-${config.size}`]: true, 'has-target': config.showTarget }">
    <div class="kpi-header">
      <div class="icon-wrapper" :style="{ backgroundColor: iconBgColor }">
        <el-icon :size="iconSize">
          <component :is="iconComponent" />
        </el-icon>
      </div>
      <div class="title-section">
        <h3 class="title">{{ config.title }}</h3>
        <span v-if="config.subtitle" class="subtitle">{{ config.subtitle }}</span>
      </div>
    </div>

    <div class="kpi-body">
      <div class="value-section">
        <span class="prefix">{{ config.prefix || '' }}</span>
        <span class="value" :style="{ color: valueColor }">{{ animatedValue }}</span>
        <span class="suffix">{{ config.suffix || '' }}</span>
      </div>

      <div v-if="config.showTrend" class="trend-section" :class="trendDirection">
        <el-icon :size="14">
          <ArrowUp v-if="trendDirection === 'up'" />
          <ArrowDown v-else-if="trendDirection === 'down'" />
          <Minus v-else />
        </el-icon>
        <span class="trend-value">{{ Math.abs(trendValue) }}%</span>
        <span class="trend-label">较{{ config.compareLabel || '上期' }}</span>
      </div>
    </div>

    <div v-if="config.showTarget" class="kpi-footer">
      <div class="target-info">
        <span class="target-label">目标</span>
        <span class="target-value">{{ config.prefix || '' }}{{ formatNumber(targetValue) }}{{ config.suffix || '' }}</span>
      </div>
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: `${progressPercentage}%`, backgroundColor: progressColor }"></div>
      </div>
      <div class="progress-text">{{ progressPercentage }}%</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue';
import { ArrowUp, ArrowDown, Minus, TrendCharts, DataLine, Money, User, Goods, ShoppingCart, View } from '@element-plus/icons-vue';

interface KpiConfig {
  title: string;
  subtitle?: string;
  icon?: string;
  value?: number;
  target?: number;
  trend?: number;
  prefix?: string;
  suffix?: string;
  showTrend?: boolean;
  showTarget?: boolean;
  compareLabel?: string;
  darkMode?: boolean;
  size?: 'small' | 'medium' | 'large';
  animationDuration?: number;
  valueColor?: string;
}

interface KpiData {
  value?: number;
  target?: number;
  trend?: number;
}

const props = defineProps<{
  config: KpiConfig;
  data?: KpiData;
}>();

const defaultConfig: Required<KpiConfig> = {
  title: '指标名称',
  subtitle: '',
  icon: 'TrendCharts',
  value: 0,
  target: 100,
  trend: 0,
  prefix: '',
  suffix: '',
  showTrend: true,
  showTarget: true,
  compareLabel: '上期',
  darkMode: false,
  size: 'medium',
  animationDuration: 1500,
  valueColor: ''
};

const mergedConfig = computed(() => ({
  ...defaultConfig,
  ...props.config
}));

const iconMap: Record<string, any> = {
  TrendCharts,
  DataLine,
  Money,
  User,
  Goods,
  ShoppingCart,
  View
};

const iconComponent = computed(() => {
  return iconMap[mergedConfig.value.icon] || TrendCharts;
});

const iconBgColors: Record<string, string> = {
  TrendCharts: 'rgba(59, 130, 246, 0.15)',
  DataLine: 'rgba(16, 185, 129, 0.15)',
  Money: 'rgba(245, 158, 11, 0.15)',
  User: 'rgba(139, 92, 246, 0.15)',
  Goods: 'rgba(236, 72, 153, 0.15)',
  ShoppingCart: 'rgba(14, 165, 233, 0.15)',
  View: 'rgba(99, 102, 241, 0.15)'
};

const iconBgColor = computed(() => {
  return iconBgColors[mergedConfig.value.icon] || iconBgColors.TrendCharts;
});

const iconSize = computed(() => {
  const sizes = { small: 20, medium: 24, large: 28 };
  return sizes[mergedConfig.value.size];
});

const currentValue = computed(() => {
  return props.data?.value ?? mergedConfig.value.value;
});

const targetValue = computed(() => {
  return props.data?.target ?? mergedConfig.value.target;
});

const trendValue = computed(() => {
  return props.data?.trend ?? mergedConfig.value.trend;
});

const trendDirection = computed(() => {
  if (trendValue.value > 0) return 'up';
  if (trendValue.value < 0) return 'down';
  return 'flat';
});

const valueColor = computed(() => {
  if (mergedConfig.value.valueColor) return mergedConfig.value.valueColor;
  if (trendDirection.value === 'up') return '#10b981';
  if (trendDirection.value === 'down') return '#ef4444';
  return '#3b82f6';
});

const progressPercentage = computed(() => {
  const percentage = Math.round((currentValue.value / targetValue.value) * 100);
  return Math.min(percentage, 100);
});

const progressColor = computed(() => {
  if (progressPercentage.value >= 100) return '#10b981';
  if (progressPercentage.value >= 80) return '#3b82f6';
  if (progressPercentage.value >= 60) return '#f59e0b';
  return '#ef4444';
});

// 数字动画
const animatedValue = ref('0');
const isAnimating = ref(false);

const formatNumber = (num: number): string => {
  if (num >= 100000000) {
    return (num / 100000000).toFixed(2) + '亿';
  }
  if (num >= 10000) {
    return (num / 10000).toFixed(2) + '万';
  }
  return num.toLocaleString();
};

const animateValue = (start: number, end: number, duration: number) => {
  if (isAnimating.value) return;
  isAnimating.value = true;

  const startTime = performance.now();

  const step = (currentTime: number) => {
    const elapsed = currentTime - startTime;
    const progress = Math.min(elapsed / duration, 1);

    // 使用 easeOutQuart 缓动函数
    const easeProgress = 1 - Math.pow(1 - progress, 4);
    const current = start + (end - start) * easeProgress;

    animatedValue.value = formatNumber(current);

    if (progress < 1) {
      requestAnimationFrame(step);
    } else {
      isAnimating.value = false;
    }
  };

  requestAnimationFrame(step);
};

watch(() => currentValue.value, (newValue, oldValue) => {
  animateValue(oldValue || 0, newValue, mergedConfig.value.animationDuration);
}, { immediate: true });

onMounted(() => {
  animateValue(0, currentValue.value, mergedConfig.value.animationDuration);
});
</script>

<style scoped lang="scss">
.kpi-widget {
  background: white;
  border-radius: 16px;
  padding: 24px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.08);
  transition: all 0.3s ease;
  min-height: 160px;
  display: flex;
  flex-direction: column;

  &:hover {
    transform: translateY(-4px);
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.12);
  }

  &.dark-mode {
    background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
    color: white;

    .title {
      color: white;
    }

    .subtitle {
      color: rgba(255, 255, 255, 0.6);
    }

    .target-label,
    .trend-label {
      color: rgba(255, 255, 255, 0.5);
    }

    .progress-bar {
      background: rgba(255, 255, 255, 0.1);
    }
  }

  &.size-small {
    padding: 16px;
    min-height: 120px;

    .title {
      font-size: 13px;
    }

    .value {
      font-size: 24px;
    }
  }

  &.size-large {
    padding: 32px;
    min-height: 200px;

    .title {
      font-size: 16px;
    }

    .value {
      font-size: 42px;
    }
  }

  .kpi-header {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 16px;

    .icon-wrapper {
      width: 44px;
      height: 44px;
      border-radius: 12px;
      display: flex;
      align-items: center;
      justify-content: center;
      color: #3b82f6;
      transition: all 0.3s ease;

      &:hover {
        transform: scale(1.1) rotate(5deg);
      }
    }

    .title-section {
      flex: 1;

      .title {
        font-size: 14px;
        font-weight: 600;
        color: #374151;
        margin: 0;
        line-height: 1.4;
      }

      .subtitle {
        font-size: 12px;
        color: #9ca3af;
        margin-top: 2px;
        display: block;
      }
    }
  }

  .kpi-body {
    flex: 1;

    .value-section {
      display: flex;
      align-items: baseline;
      gap: 4px;
      margin-bottom: 12px;

      .prefix,
      .suffix {
        font-size: 16px;
        font-weight: 500;
        color: #6b7280;
      }

      .value {
        font-size: 32px;
        font-weight: 700;
        line-height: 1;
        transition: color 0.3s ease;
      }
    }

    .trend-section {
      display: inline-flex;
      align-items: center;
      gap: 6px;
      padding: 6px 12px;
      border-radius: 20px;
      font-size: 13px;
      font-weight: 500;
      background: rgba(0, 0, 0, 0.05);

      &.up {
        color: #10b981;
        background: rgba(16, 185, 129, 0.1);
      }

      &.down {
        color: #ef4444;
        background: rgba(239, 68, 68, 0.1);
      }

      &.flat {
        color: #6b7280;
        background: rgba(107, 114, 128, 0.1);
      }

      .trend-label {
        font-size: 12px;
        color: #9ca3af;
        margin-left: 4px;
      }
    }
  }

  .kpi-footer {
    margin-top: 16px;
    padding-top: 16px;
    border-top: 1px solid rgba(0, 0, 0, 0.06);

    .target-info {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 8px;

      .target-label {
        font-size: 12px;
        color: #9ca3af;
      }

      .target-value {
        font-size: 13px;
        font-weight: 600;
        color: #374151;
      }
    }

    .progress-bar {
      height: 6px;
      background: #e5e7eb;
      border-radius: 3px;
      overflow: hidden;
      position: relative;

      .progress-fill {
        height: 100%;
        border-radius: 3px;
        transition: width 1s ease, background-color 0.3s ease;
      }
    }

    .progress-text {
      text-align: right;
      font-size: 11px;
      color: #9ca3af;
      margin-top: 4px;
    }
  }
}

// 响应式适配
@media (max-width: 768px) {
  .kpi-widget {
    padding: 16px;

    .kpi-header {
      .icon-wrapper {
        width: 36px;
        height: 36px;
      }
    }

    .kpi-body {
      .value-section {
        .value {
          font-size: 24px;
        }
      }
    }
  }
}
</style>
