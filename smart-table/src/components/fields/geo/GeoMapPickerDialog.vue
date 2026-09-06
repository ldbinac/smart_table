<template>
  <el-dialog
    :model-value="modelValue"
    :title="t('field.geo.mapTitle')"
    width="1300px"
    align-center
    append-to-body
    class="geo-map-dialog"
    modal-class="geo-map-overlay"
    @update:model-value="(v: boolean) => emit('update:modelValue', v)"
    @close="onClose"
  >
    <div class="geo-map-dialog__body">
      <TiandituMap :value="selected" :lang="language" @pick="onPick" />

      <div class="geo-map-dialog__coord">
        <span class="label">{{ t("field.geo.coordinate") }}：</span>
        <span v-if="selected" class="value">{{ selected.lng }}, {{ selected.lat }}</span>
        <span v-else class="value placeholder">{{ t("field.geo.mapSearchPlaceholder") }}</span>
      </div>
    </div>

    <template #footer>
      <el-button @click="clear">{{ t("field.geo.clear") }}</el-button>
      <el-button @click="onClose">{{ t("common.cancel") }}</el-button>
      <el-button type="primary" :disabled="!selected" @click="confirm">
        {{ t("field.geo.confirm") }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, watch } from "vue";
import TiandituMap from "./TiandituMap.vue";
import { t } from "@/i18n";
import type { GeoValue } from "@/types/fields";

const props = defineProps<{
  modelValue: boolean;
  value?: GeoValue | null;
  language?: "zh" | "en";
}>();

const emit = defineEmits<{
  (e: "update:modelValue", v: boolean): void;
  (e: "confirm", v: { lng: number; lat: number }): void;
}>();

const selected = ref<{ lng: number; lat: number } | null>(null);

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      selected.value =
        props.value && props.value.lng && props.value.lat
          ? { lng: props.value.lng, lat: props.value.lat }
          : null;
    }
  },
  { immediate: true }
);

function onPick(payload: { lng: number; lat: number }) {
  selected.value = payload;
}

function clear() {
  selected.value = null;
}

function confirm() {
  if (selected.value) {
    emit("confirm", selected.value);
  }
  emit("update:modelValue", false);
}

function onClose() {
  emit("update:modelValue", false);
}
</script>

<style scoped lang="scss">
.geo-map-dialog {
  &__body {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  &__coord {
    display: flex;
    align-items: center;
    font-size: 13px;
    color: #1f2329;

    .label {
      color: #8f959e;
    }
    .value.placeholder {
      color: #b0b3b8;
    }
  }
}
</style>

<!-- 非 scoped：地图选点弹窗(el-dialog)会被 teleport 到 body，
     在表格单元格中需抬升至 VTable 编辑器容器层之上，否则会被遮挡/穿透 -->
<style lang="scss">
.geo-map-overlay {
  z-index: 100000 !important;
}
.geo-map-dialog {
  z-index: 100001 !important;
}
</style>
