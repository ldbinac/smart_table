<script setup lang="ts">
import { onMounted, onUnmounted } from "vue";
import {
  Plus,
  Minus,
  FullScreen,
  Handbag,
  Pointer,
} from "@element-plus/icons-vue";

interface Props {
  panMode?: boolean;
}

withDefaults(defineProps<Props>(), {
  panMode: false,
});

const emit = defineEmits<{
  (e: "zoom-in"): void;
  (e: "zoom-out"): void;
  (e: "fit-view"): void;
  (e: "toggle-pan-mode"): void;
}>();

function handleKeyDown(event: KeyboardEvent) {
  const modifierPressed = event.ctrlKey || event.metaKey;
  if (!modifierPressed) {
    return;
  }

  switch (event.key) {
    case "+":
    case "=":
      event.preventDefault();
      emit("zoom-in");
      break;
    case "-":
      event.preventDefault();
      emit("zoom-out");
      break;
    case "0":
      event.preventDefault();
      emit("fit-view");
      break;
  }
}

onMounted(() => {
  window.addEventListener("keydown", handleKeyDown);
});

onUnmounted(() => {
  window.removeEventListener("keydown", handleKeyDown);
});
</script>

<template>
  <div class="workflow-canvas-toolbar">
    <el-button-group>
      <el-button
        size="small"
        :type="panMode ? 'primary' : 'default'"
        :class="{ active: panMode }"
        :title="panMode ? '退出抓手模式' : '进入抓手模式'"
        @click="emit('toggle-pan-mode')"
      >
        <el-icon>
          <Pointer v-if="!panMode" />
          <Handbag v-else />
        </el-icon>
      </el-button>

      <el-button
        size="small"
        title="放大"
        @click="emit('zoom-in')"
      >
        <el-icon><Plus /></el-icon>
      </el-button>

      <el-button
        size="small"
        title="缩小"
        @click="emit('zoom-out')"
      >
        <el-icon><Minus /></el-icon>
      </el-button>

      <el-button
        size="small"
        title="适应屏幕"
        @click="emit('fit-view')"
      >
        <el-icon><FullScreen /></el-icon>
      </el-button>
    </el-button-group>
  </div>
</template>

<style lang="scss" scoped>
.workflow-canvas-toolbar {
  position: absolute;
  bottom: $spacing-lg;
  right: $spacing-lg;
  z-index: 10;
  padding: $spacing-xs;
  background-color: $surface-color;
  border: 1px solid $border-color;
  border-radius: $border-radius-md;
  box-shadow: $shadow-md;
}
</style>
