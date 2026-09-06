<template>
  <div class="geo-lnglat">
    <div class="geo-lnglat__inputs">
      <el-input
        v-model="lngText"
        :placeholder="t('field.geo.lngPlaceholder')"
        :readonly="readonly"
        @blur="onBlur"
        @paste="onPaste"
      >
        <template #prepend>Lng</template>
      </el-input>
      <el-input
        v-model="latText"
        :placeholder="t('field.geo.latPlaceholder')"
        :readonly="readonly"
        @blur="onBlur"
        @paste="onPaste"
      >
        <template #prepend>Lat</template>
      </el-input>
    </div>

    <div class="geo-lnglat__footer">
      <span class="geo-lnglat__hint">{{ t("field.geo.lngLatPasteHint") }}</span>
      <el-button
        size="small"
        :icon="MapLocation"
        :disabled="readonly || !mapEnabled"
        @click="openMap"
      >
        {{ t("field.geo.pickOnMap") }}
      </el-button>
    </div>

    <GeoMapPickerDialog
      v-model="mapVisible"
      :value="modelValue"
      :language="language"
      @confirm="onMapConfirm"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { MapLocation } from "@element-plus/icons-vue";
import { t } from "@/i18n";
import GeoMapPickerDialog from "./GeoMapPickerDialog.vue";
import { parseLngLatText } from "@/utils/geo";
import { isMapEnabled } from "@/utils/tiandituLoader";
import { getGeoConfig } from "@/services/api";
import type { GeoValue } from "@/types/fields";

const props = defineProps<{
  modelValue?: GeoValue | null;
  readonly?: boolean;
  language?: "zh" | "en";
}>();

const emit = defineEmits<{
  (e: "update:modelValue", v: GeoValue): void;
}>();

const value = computed(() => props.modelValue || {});
const lngText = ref(value.value.lng !== undefined ? String(value.value.lng) : "");
const latText = ref(value.value.lat !== undefined ? String(value.value.lat) : "");
const mapVisible = ref(false);
const mapEnabled = ref(false);

function emitValue() {
  const lng = lngText.value.trim() === "" ? undefined : Number(lngText.value);
  const lat = latText.value.trim() === "" ? undefined : Number(latText.value);
  emit("update:modelValue", {
    ...value.value,
    lng: Number.isFinite(lng) ? lng : undefined,
    lat: Number.isFinite(lat) ? lat : undefined,
  });
}

function onBlur() {
  emitValue();
}

function onPaste() {
  // 任一框粘贴「lng, lat」后尝试整体解析
  setTimeout(() => {
    const combined = `${lngText.value}, ${latText.value}`;
    const parsed = parseLngLatText(combined);
    if (parsed) {
      lngText.value = String(parsed.lng);
      latText.value = String(parsed.lat);
      emitValue();
    }
  }, 0);
}

function openMap() {
  mapVisible.value = true;
}

function onMapConfirm(payload: { lng: number; lat: number }) {
  lngText.value = String(payload.lng);
  latText.value = String(payload.lat);
  emitValue();
}

onMounted(async () => {
  try {
    const cfg = await getGeoConfig();
    mapEnabled.value = cfg.enabled;
    // 触发一次脚本预加载判定
    isMapEnabled();
  } catch {
    mapEnabled.value = false;
  }
});

// 同步外部值
import { watch } from "vue";
watch(
  () => props.modelValue,
  (v) => {
    if (v?.lng !== undefined && String(v.lng) !== lngText.value) lngText.value = String(v.lng);
    if (v?.lat !== undefined && String(v.lat) !== latText.value) latText.value = String(v.lat);
  }
);
</script>

<style scoped lang="scss">
.geo-lnglat {
  display: flex;
  flex-direction: column;
  gap: 8px;

  &__inputs {
    display: flex;
    gap: 8px;

    .el-input {
      flex: 1;
    }
  }

  &__footer {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  &__hint {
    font-size: 12px;
    color: #8f959e;
  }
}
</style>
