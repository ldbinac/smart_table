<template>
  <div class="geo-detail">
    <!-- 内嵌模式：直接渲染级联面板与详情输入，不 teleport -->
    <template v-if="inline">
      <GeoCascader
        v-if="!readonly"
        :model-value="modelValue"
        :format="cascaderFormat"
        :language="language"
        :show-search="true"
        @change="onCascaderChange"
      />
      <el-input
        v-if="format === 'province_city_district_detail'"
        v-model="detailInput"
        class="geo-detail__input"
        :placeholder="t('field.geo.detailPlaceholder')"
        :readonly="readonly"
        @blur="onDetailBlur"
        @paste="onDetailPaste"
      >
        <template v-if="recognized" #append>
          <span class="geo-detail__tag">{{ t("field.geo.detailRecognized", { value: recognized }) }}</span>
        </template>
      </el-input>
    </template>

    <template v-else>
      <el-popover
        placement="bottom-start"
        :width="popWidth"
        trigger="click"
        :disabled="readonly"
        popper-class="geo-popover"
      >
        <template #reference>
          <div class="geo-detail__bar" :class="{ placeholder: !addressPreview }">
            <el-icon><LocationInformation /></el-icon>
            <span class="geo-detail__text">{{ addressPreview || t("field.geo.selectAddress") }}</span>
          </div>
        </template>

        <GeoCascader
          v-if="!readonly"
          :model-value="modelValue"
          :format="cascaderFormat"
          :show-search="true"
          @change="onCascaderChange"
        />
      </el-popover>

      <el-input
        v-if="format === 'province_city_district_detail'"
        v-model="detailInput"
        class="geo-detail__input"
        :placeholder="t('field.geo.detailPlaceholder')"
        :readonly="readonly"
        @blur="onDetailBlur"
        @paste="onDetailPaste"
      >
        <template v-if="recognized" #append>
          <span class="geo-detail__tag">{{ t("field.geo.detailRecognized", { value: recognized }) }}</span>
        </template>
      </el-input>
    </template>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
import { LocationInformation } from "@element-plus/icons-vue";
import { t } from "@/i18n";
import GeoCascader from "./GeoCascader.vue";
import { getChinaLocations } from "@/services/api";
import { parseAddressText } from "@/utils/geo";
import type { GeoValue, GeoFormat, GeoChinaNode } from "@/types/fields";

const props = defineProps<{
  modelValue?: GeoValue | null;
  format: GeoFormat;
  readonly?: boolean;
  language?: "zh" | "en";
  // 内嵌模式：直接渲染面板（不 teleport），用于表格单元格编辑器
  inline?: boolean;
}>();

const emit = defineEmits<{
  (e: "update:modelValue", v: GeoValue): void;
}>();

const value = computed(() => props.modelValue || {});

const cascaderFormat = computed<GeoFormat>(() =>
  props.format === "province_city_district_detail" ? "province_city_district" : "province_city"
);

const popWidth = computed(() => (cascaderFormat.value === "province_city" ? 360 : 540));

const addressPreview = computed(() => {
  const v = value.value;
  const parts = [v.province, v.city, v.district].filter(Boolean);
  return parts.join(" / ");
});

const detailInput = ref(value.value.detail || "");
const recognized = ref("");

const treeCache = ref<GeoChinaNode[]>([]);
const treeLang = ref<"zh" | "en">("zh");

async function ensureTree() {
  const lang = props.language || "zh";
  // 语言变化时丢弃旧缓存，按新语言重新拉取
  if (!treeCache.value.length || treeLang.value !== lang) {
    try {
      treeCache.value = await getChinaLocations("district", lang);
      treeLang.value = lang;
    } catch {
      /* 忽略 */
    }
  }
  return treeCache.value;
}

function buildValue(patch: Partial<GeoValue>): GeoValue {
  return { ...value.value, ...patch };
}

function onCascaderChange(patch: Partial<GeoValue>) {
  emit("update:modelValue", buildValue(patch));
}

function recognize(text: string) {
  const tree = treeCache.value;
  if (!tree.length) return;
  const parsed = parseAddressText(text, tree);
  const merged = buildValue(parsed);
  emit("update:modelValue", merged);
  recognized.value = [merged.province, merged.city, merged.district]
    .filter(Boolean)
    .join(" / ");
}

async function onDetailBlur() {
  const text = detailInput.value.trim();
  if (!text) return;
  await ensureTree();
  if (!treeCache.value.length) {
    emit("update:modelValue", buildValue({ detail: text }));
    return;
  }
  recognize(text);
}

function onDetailPaste() {
  // 粘贴后等待 DOM 更新再识别
  setTimeout(async () => {
    await ensureTree();
    if (treeCache.value.length && detailInput.value.trim()) {
      recognize(detailInput.value);
    }
  }, 0);
}

// 同步外部 detail 变化
import { watch } from "vue";
watch(
  () => value.value.detail,
  (d) => {
    if (d !== detailInput.value) detailInput.value = d || "";
  }
);
</script>

<style scoped lang="scss">
.geo-detail {
  display: flex;
  flex-direction: column;
  gap: 8px;

  &__bar {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 6px 10px;
    border: 1px solid #dcdfe6;
    border-radius: 4px;
    cursor: pointer;
    font-size: 13px;
    color: #1f2329;
    background: #fff;

    &:hover {
      border-color: #3370ff;
    }

    &.placeholder {
      color: #b0b3b8;
    }

    .el-icon {
      color: #3370ff;
    }
  }

  &__input {
    :deep(.el-input-group__append) {
      color: #34c724;
      font-size: 12px;
    }
  }

  &__tag {
    font-size: 12px;
  }
}
</style>
