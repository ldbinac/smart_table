<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick, watch } from 'vue';
import { useI18n } from 'vue-i18n';
import { ElMessage } from 'element-plus';

const { t } = useI18n();

interface Props {
  /** 初始已有签字图片（Base64 URL），用于展示和覆盖 */
  existingImage?: string | null;
}

const props = withDefaults(defineProps<Props>(), {
  existingImage: null,
});

const emit = defineEmits<{
  (e: 'save', blob: Blob): void;
  (e: 'cancel'): void;
  (e: 'clear'): void;
}>();

type SignMode = 'handwrite' | 'input';

// ============ 状态 ============
const mode = ref<SignMode>('handwrite');
const canvasRef = ref<HTMLCanvasElement | null>(null);
const containerRef = ref<HTMLDivElement | null>(null);

// 手写模式状态
const isDrawing = ref(false);
const hasStroke = ref(false);

// 输入模式状态
const inputName = ref('');
const selectedFont = ref<'default' | 'cursive'>('default');

// 字体列表
const fontOptions = [
  { value: 'default', label: 'field.signature.fontDefault', css: '"Helvetica Neue", Arial, "Microsoft YaHei", sans-serif' },
  { value: 'cursive', label: 'field.signature.fontCursive', css: '"Brush Script MT", "Lucida Handwriting", cursive' },
];

const currentFont = computed(() => {
  return fontOptions.find((f) => f.value === selectedFont.value)?.css || fontOptions[0].css;
});

// 是否有可保存的内容（手写有笔迹 或 输入有文字）
const hasContent = computed(() => {
  if (mode.value === 'handwrite') return hasStroke.value;
  return inputName.value.trim().length > 0;
});

// ============ Canvas 初始化 ============
let ctx: CanvasRenderingContext2D | null = null;

function resizeCanvas() {
  const canvas = canvasRef.value;
  const container = containerRef.value;
  if (!canvas || !container) return;

  const rect = container.getBoundingClientRect();
  const dpr = window.devicePixelRatio || 1;

  // 设置物理尺寸（2x 高清）
  canvas.width = rect.width * dpr;
  canvas.height = rect.height * dpr;

  // CSS 尺寸保持逻辑尺寸
  canvas.style.width = `${rect.width}px`;
  canvas.style.height = `${rect.height}px`;

  ctx = canvas.getContext('2d');
  if (!ctx) return;

  ctx.scale(dpr, dpr);

  // 白色背景
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, rect.width, rect.height);

  // 如果有已存在的签字，绘制上
  if (props.existingImage) {
    loadExistingImage();
  }
}

function loadExistingImage() {
  if (!ctx || !canvasRef.value || !props.existingImage) return;
  const canvas = canvasRef.value;
  const img = new Image();
  img.onload = () => {
    ctx!.drawImage(img, 0, 0, canvas.clientWidth, canvas.clientHeight);
    hasStroke.value = true;
  };
  img.src = props.existingImage!;
}

// 监听 existingImage 变化
watch(
  () => props.existingImage,
  () => {
    nextTick(() => {
      clearCanvas(false);
      if (props.existingImage) {
        loadExistingImage();
      }
    });
  }
);

// ============ 手写模式 ============
let lastX = 0;
let lastY = 0;

function getPos(e: MouseEvent | TouchEvent): { x: number; y: number } {
  const canvas = canvasRef.value!;
  const rect = canvas.getBoundingClientRect();
  if ('touches' in e) {
    const touch = e.touches[0];
    return { x: touch.clientX - rect.left, y: touch.clientY - rect.top };
  }
  return { x: (e as MouseEvent).clientX - rect.left, y: (e as MouseEvent).clientY - rect.top };
}

function startDraw(e: MouseEvent | TouchEvent) {
  e.preventDefault();
  isDrawing.value = true;
  const pos = getPos(e);
  lastX = pos.x;
  lastY = pos.y;

  // 点一下也画一个点
  if (ctx) {
    ctx.beginPath();
    ctx.arc(lastX, lastY, 1, 0, Math.PI * 2);
    ctx.fillStyle = '#000000';
    ctx.fill();
  }
}

function moveDraw(e: MouseEvent | TouchEvent) {
  if (!isDrawing.value || !ctx) return;
  e.preventDefault();

  const pos = getPos(e);

  ctx.beginPath();
  ctx.strokeStyle = '#000000';
  ctx.lineWidth = 2.5;
  ctx.lineCap = 'round';
  ctx.lineJoin = 'round';
  ctx.moveTo(lastX, lastY);
  ctx.lineTo(pos.x, pos.y);
  ctx.stroke();

  lastX = pos.x;
  lastY = pos.y;
  hasStroke.value = true;
}

function endDraw() {
  isDrawing.value = false;
}

// ============ 输入模式渲染 ============
function renderInputText() {
  if (!ctx || !canvasRef.value) return;
  const canvas = canvasRef.value;
  const w = canvas.clientWidth;
  const h = canvas.clientHeight;

  // 清空画布（白色背景）
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, w, h);

  const name = inputName.value.trim();
  if (!name) {
    hasStroke.value = false;
    return;
  }

  ctx.fillStyle = '#000000';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';

  // 自适应字体大小
  let fontSize = 48;
  ctx.font = `${fontSize}px ${currentFont.value}`;
  const maxWidth = w * 0.85;
  while (ctx.measureText(name).width > maxWidth && fontSize > 16) {
    fontSize -= 2;
    ctx.font = `${fontSize}px ${currentFont.value}`;
  }

  // 垂直居中 + 稍微向上偏移（签名通常偏上）
  ctx.fillText(name, w / 2, h / 2 - fontSize * 0.1);
  hasStroke.value = true;
}

// 监听输入变化自动渲染
watch(inputName, () => {
  if (mode.value === 'input') {
    nextTick(renderInputText);
  }
});

watch(selectedFont, () => {
  if (mode.value === 'input') {
    nextTick(renderInputText);
  }
});

watch(mode, (newMode) => {
  nextTick(() => {
    if (newMode === 'handwrite') {
      resizeCanvas();
    } else {
      renderInputText();
    }
  });
});

// ============ 操作 ============
function clearCanvas(resetHasStroke = true) {
  if (!ctx || !canvasRef.value) return;
  const canvas = canvasRef.value;
  ctx.fillStyle = '#ffffff';
  ctx.fillRect(0, 0, canvas.clientWidth, canvas.clientHeight);
  if (resetHasStroke) {
    hasStroke.value = false;
  }
}

function handleClear() {
  if (mode.value === 'input') {
    inputName.value = '';
  }
  clearCanvas();
}

function handleSave() {
  if (!hasContent.value) {
    ElMessage.warning(mode.value === 'input' ? t('field.signature.inputPlaceholder') : t('field.signature.canvasPlaceholder'));
    return;
  }

  const canvas = canvasRef.value;
  if (!canvas) return;

  canvas.toBlob(
    (blob) => {
      if (blob) {
        emit('save', blob);
      } else {
        ElMessage.error('Export failed');
      }
    },
    'image/png',
    1.0
  );
}

function handleCancel() {
  emit('cancel');
}

// ============ 生命周期 ============
function handleResize() {
  resizeCanvas();
  if (mode.value === 'input') {
    nextTick(renderInputText);
  }
}

let resizeObserver: ResizeObserver | null = null;

onMounted(() => {
  nextTick(() => {
    resizeCanvas();

    // 使用 ResizeObserver 监听容器尺寸变化
    if (containerRef.value && 'ResizeObserver' in window) {
      resizeObserver = new ResizeObserver(() => {
        resizeCanvas();
        if (mode.value === 'input') {
          nextTick(renderInputText);
        }
      });
      resizeObserver.observe(containerRef.value);
    }
  });

  window.addEventListener('resize', handleResize);
});

onUnmounted(() => {
  window.removeEventListener('resize', handleResize);
  resizeObserver?.disconnect();
});
</script>

<template>
  <div class="signature-pad">
    <!-- 模式切换 -->
    <div class="mode-switch">
      <el-radio-group v-model="mode" size="small">
        <el-radio-button value="handwrite">
          {{ t('field.signature.handwriteMode') }}
        </el-radio-button>
        <el-radio-button value="input">
          {{ t('field.signature.inputMode') }}
        </el-radio-button>
      </el-radio-group>

      <!-- 输入模式：字体选择 -->
      <el-select
        v-if="mode === 'input'"
        v-model="selectedFont"
        size="small"
        class="font-select"
        :placeholder="t('field.signature.fontPlaceholder')"
      >
        <el-option
          v-for="font in fontOptions"
          :key="font.value"
          :label="t(font.label)"
          :value="font.value"
        />
      </el-select>
    </div>

    <!-- 输入模式：姓名输入 -->
    <div v-if="mode === 'input'" class="input-area">
      <el-input
        v-model="inputName"
        :placeholder="t('field.signature.inputPlaceholder')"
        clearable
        size="large"
        @input="renderInputText"
      />
    </div>

    <!-- 画布区域 -->
    <div ref="containerRef" class="canvas-wrapper">
      <canvas
        ref="canvasRef"
        class="signature-canvas"
        :class="{ 'is-handwrite': mode === 'handwrite' }"
        @mousedown="mode === 'handwrite' && startDraw($event)"
        @mousemove="mode === 'handwrite' && moveDraw($event)"
        @mouseup="mode === 'handwrite' && endDraw()"
        @mouseleave="mode === 'handwrite' && endDraw()"
        @touchstart.prevent="mode === 'handwrite' && startDraw($event)"
        @touchmove.prevent="mode === 'handwrite' && moveDraw($event)"
        @touchend.prevent="mode === 'handwrite' && endDraw()"
      />
      <!-- 手写模式占位提示 -->
      <div
        v-if="mode === 'handwrite' && !hasStroke"
        class="canvas-placeholder"
      >
        <el-icon class="placeholder-icon"><EditPen /></el-icon>
        <span>{{ t('field.signature.canvasPlaceholder') }}</span>
      </div>
    </div>

    <!-- 提示文字 -->
    <div class="signature-tip">
      <el-icon><InfoFilled /></el-icon>
      {{ t('field.signature.signatureTip') }}
    </div>

    <!-- 操作按钮 -->
    <div class="actions">
      <el-button @click="handleClear" :disabled="!hasContent">
        <el-icon><Delete /></el-icon>
        {{ t('field.signature.clear') }}
      </el-button>
      <div class="spacer" />
      <el-button @click="handleCancel">
        {{ t('field.signature.cancel') }}
      </el-button>
      <el-button type="primary" @click="handleSave" :disabled="!hasContent">
        {{ t('field.signature.save') }}
      </el-button>
    </div>
  </div>
</template>

<script lang="ts">
import { EditPen, InfoFilled, Delete } from '@element-plus/icons-vue';
export default {
  components: { EditPen, InfoFilled, Delete },
};
</script>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;

.signature-pad {
  display: flex;
  flex-direction: column;
  gap: $spacing-md;
  padding: $spacing-lg;
}

.mode-switch {
  display: flex;
  align-items: center;
  gap: $spacing-md;
}

.font-select {
  width: 140px;
}

.input-area {
  :deep(.el-input__wrapper) {
    box-shadow: 0 0 0 1px $border-color inset;
    &:hover {
      box-shadow: 0 0 0 1px $primary-color inset;
    }
  }
}

.canvas-wrapper {
  position: relative;
  width: 100%;
  height: 220px;
  min-height: 200px;
  border: 2px dashed $border-color;
  border-radius: $border-radius-md;
  background-color: #fff;
  overflow: hidden;
  cursor: crosshair;
  transition: border-color 0.2s;

  &:hover {
    border-color: $primary-color;
  }
}

.signature-canvas {
  display: block;
  width: 100%;
  height: 100%;
  cursor: crosshair;
  touch-action: none;

  &:not(.is-handwrite) {
    cursor: default;
  }
}

.canvas-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: $spacing-sm;
  color: $text-disabled;
  pointer-events: none;

  .placeholder-icon {
    font-size: 32px;
  }

  span {
    font-size: $font-size-sm;
  }
}

.signature-tip {
  display: flex;
  align-items: center;
  gap: $spacing-xs;
  padding: $spacing-xs $spacing-sm;
  background-color: rgba($warning-color, 0.1);
  border-radius: $border-radius-sm;
  color: $warning-color;
  font-size: $font-size-xs;
  line-height: 1.5;
}

.actions {
  display: flex;
  align-items: center;
  gap: $spacing-sm;

  .spacer {
    flex: 1;
  }
}
</style>
