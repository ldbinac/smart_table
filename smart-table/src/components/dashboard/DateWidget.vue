<template>
  <div class="date-widget" :class="{ 'dark-mode': config.darkMode, [`size-${config.size}`]: true }">
    <div class="date-content">
      <div class="day-number">{{ dayNumber }}</div>
      <div class="month-year">{{ monthYear }}</div>
      <div v-if="config.showWeekday" class="weekday">{{ weekday }}</div>
    </div>
    <div v-if="config.showLunar" class="lunar-date">{{ lunarDate }}</div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue';
import dayjs from 'dayjs';
import 'dayjs/locale/zh-cn';

dayjs.locale('zh-cn');

interface DateConfig {
  format?: string;
  showWeekday?: boolean;
  showLunar?: boolean;
  darkMode?: boolean;
  size?: 'small' | 'medium' | 'large';
}

interface DateData {
  customDate?: string;
}

const props = defineProps<{
  config: DateConfig;
  data?: DateData;
}>();

// 使用 props.config
const currentDate = ref(dayjs());
let timer: number | null = null;

const dayNumber = computed(() => {
  return currentDate.value.format('DD');
});

const monthYear = computed(() => {
  return currentDate.value.format('YYYY年MM月');
});

const weekday = computed(() => {
  const weekdays = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六'];
  return weekdays[currentDate.value.day()];
});

const lunarDate = computed(() => {
  // 简化版农历显示，实际项目中可以使用 lunar-javascript 库
  const lunarMonths = ['正月', '二月', '三月', '四月', '五月', '六月', '七月', '八月', '九月', '十月', '冬月', '腊月'];
  const lunarDays = ['初一', '初二', '初三', '初四', '初五', '初六', '初七', '初八', '初九', '初十',
    '十一', '十二', '十三', '十四', '十五', '十六', '十七', '十八', '十九', '二十',
    '廿一', '廿二', '廿三', '廿四', '廿五', '廿六', '廿七', '廿八', '廿九', '三十'];
  const month = lunarMonths[currentDate.value.month()];
  const day = lunarDays[parseInt(currentDate.value.format('D')) - 1];
  return `农历${month}${day}`;
});

const updateDate = () => {
  currentDate.value = dayjs();
};

onMounted(() => {
  updateDate();
  // 每分钟更新一次日期
  timer = window.setInterval(updateDate, 60000);
});

onUnmounted(() => {
  if (timer) {
    clearInterval(timer);
  }
});
</script>

<style scoped lang="scss">
.date-widget {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 32px;
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
  border-radius: 20px;
  box-shadow: 0 10px 40px rgba(245, 87, 108, 0.3);
  color: white;
  min-height: 200px;
  position: relative;
  transition: all 0.3s ease;

  &.dark-mode {
    background: linear-gradient(135deg, #2c3e50 0%, #4a6741 100%);
    box-shadow: 0 10px 40px rgba(0, 0, 0, 0.4);
  }

  &.size-small {
    padding: 20px;
    min-height: 140px;

    .day-number {
      font-size: 48px;
    }

    .month-year {
      font-size: 14px;
    }

    .weekday {
      font-size: 12px;
    }
  }

  &.size-large {
    padding: 48px;
    min-height: 280px;

    .day-number {
      font-size: 96px;
    }

    .month-year {
      font-size: 24px;
    }

    .weekday {
      font-size: 18px;
    }
  }

  .date-content {
    text-align: center;

    .day-number {
      font-size: 72px;
      font-weight: 800;
      line-height: 1;
      text-shadow: 0 4px 15px rgba(0, 0, 0, 0.2);
      margin-bottom: 8px;

      @media (max-width: 768px) {
        font-size: 56px;
      }
    }

    .month-year {
      font-size: 18px;
      font-weight: 600;
      opacity: 0.95;
      letter-spacing: 2px;
      margin-bottom: 8px;

      @media (max-width: 768px) {
        font-size: 16px;
      }
    }

    .weekday {
      font-size: 14px;
      font-weight: 500;
      opacity: 0.9;
      padding: 6px 16px;
      background: rgba(255, 255, 255, 0.2);
      border-radius: 20px;
      display: inline-block;
      backdrop-filter: blur(10px);

      @media (max-width: 768px) {
        font-size: 12px;
      }
    }
  }

  .lunar-date {
    position: absolute;
    bottom: 16px;
    right: 16px;
    font-size: 12px;
    opacity: 0.8;
    padding: 4px 10px;
    background: rgba(255, 255, 255, 0.15);
    border-radius: 12px;
    backdrop-filter: blur(10px);
  }
}
</style>
