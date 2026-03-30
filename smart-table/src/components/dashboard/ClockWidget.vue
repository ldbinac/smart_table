<template>
  <div class="clock-widget" :class="{ 'dark-mode': config.darkMode }">
    <div class="clock-display">
      <div class="time">{{ formattedTime }}</div>
      <div v-if="config.showDate" class="date">{{ formattedDate }}</div>
    </div>
    <div v-if="config.showFormatToggle" class="format-toggle" @click="toggleFormat">
      <span class="toggle-label">{{ is24Hour ? '24H' : '12H' }}</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';
import dayjs from 'dayjs';

interface ClockConfig {
  is24Hour?: boolean;
  showDate?: boolean;
  showFormatToggle?: boolean;
  darkMode?: boolean;
  dateFormat?: string;
}

interface ClockData {
  timezone?: string;
}

const props = defineProps<{
  config: ClockConfig;
  data?: ClockData;
}>();

const defaultConfig: Required<ClockConfig> = {
  is24Hour: true,
  showDate: true,
  showFormatToggle: true,
  darkMode: false,
  dateFormat: 'YYYY年MM月DD日'
};

const mergedConfig = computed(() => ({
  ...defaultConfig,
  ...props.config
}));

const is24Hour = ref(mergedConfig.value.is24Hour);
const currentTime = ref(dayjs());
let timer: number | null = null;

const formattedTime = computed(() => {
  const format = is24Hour.value ? 'HH:mm:ss' : 'hh:mm:ss A';
  return currentTime.value.format(format);
});

const formattedDate = computed(() => {
  return currentTime.value.format(mergedConfig.value.dateFormat);
});

const toggleFormat = () => {
  is24Hour.value = !is24Hour.value;
};

const updateTime = () => {
  currentTime.value = dayjs();
};

onMounted(() => {
  updateTime();
  timer = window.setInterval(updateTime, 1000);
});

onUnmounted(() => {
  if (timer) {
    clearInterval(timer);
  }
});
</script>

<style scoped lang="scss">
.clock-widget {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 24px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 16px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
  position: relative;
  min-height: 160px;
  color: white;
  transition: all 0.3s ease;

  &.dark-mode {
    background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  }

  .clock-display {
    text-align: center;

    .time {
      font-size: 48px;
      font-weight: 700;
      font-family: 'SF Mono', Monaco, monospace;
      letter-spacing: 2px;
      text-shadow: 0 2px 10px rgba(0, 0, 0, 0.3);
      line-height: 1.2;

      @media (max-width: 768px) {
        font-size: 36px;
      }
    }

    .date {
      margin-top: 12px;
      font-size: 16px;
      font-weight: 500;
      opacity: 0.9;
      letter-spacing: 1px;

      @media (max-width: 768px) {
        font-size: 14px;
      }
    }
  }

  .format-toggle {
    position: absolute;
    top: 16px;
    right: 16px;
    padding: 6px 12px;
    background: rgba(255, 255, 255, 0.2);
    border-radius: 20px;
    cursor: pointer;
    transition: all 0.3s ease;
    backdrop-filter: blur(10px);

    &:hover {
      background: rgba(255, 255, 255, 0.3);
      transform: scale(1.05);
    }

    .toggle-label {
      font-size: 12px;
      font-weight: 600;
      letter-spacing: 0.5px;
    }
  }
}
</style>
