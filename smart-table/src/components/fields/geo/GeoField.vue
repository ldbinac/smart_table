<template>
  <div class="geo-field">
    <!-- 只读展示 -->
    <div v-if="readonly" class="geo-field__readonly">
      <el-icon v-if="displayText"><LocationInformation /></el-icon>
      <span>{{ displayText || "—" }}</span>
    </div>

    <!--
      内嵌模式（inline）：用于表格单元格编辑器。
      el-popover 会被 teleport 到 body，弹层不是编辑器宿主(this.element)的子节点，
      VTable 的 isEditorElement 据此判定点击在"编辑器外"，会结束编辑并在该格重新开启，
      表现为点击穿透到表格。inline 模式直接把面板渲染在宿主内部(不 teleport)，
      既被识别为编辑器内部点击，又天然位于编辑器容器层之上。
    -->
    <template v-else-if="inline">
      <GeoCascader
        v-if="isCascaderFormat"
        :model-value="modelValue"
        :format="format"
        :language="language"
        :show-search="true"
        @change="onCascaderChange"
      />
      <GeoDetailField
        v-else-if="format === 'province_city_district_detail'"
        :model-value="modelValue"
        :format="format"
        :language="language"
        :inline="true"
        @update:model-value="emitValue"
      />
      <GeoRegionSelect
        v-else-if="format === 'country_region'"
        :model-value="modelValue"
        :language="language"
        :inline="true"
        @update:model-value="emitValue"
      />
      <GeoLngLatField
        v-else-if="format === 'lng_lat' || format === 'map_picker'"
        :model-value="modelValue"
        :language="language"
        @update:model-value="emitValue"
      />
    </template>

    <!-- 省 / 省+市 / 省+市+区：多列级联弹出 -->
    <el-popover
      v-else-if="isCascaderFormat"
      placement="bottom-start"
      :width="cascaderPopWidth"
      trigger="click"
      popper-class="geo-popover"
    >
      <template #reference>
        <div class="geo-field__bar" :class="{ placeholder: !displayText }">
          <el-icon><LocationInformation /></el-icon>
          <span class="geo-field__text">{{ displayText || placeholder }}</span>
        </div>
      </template>
      <GeoCascader
        :model-value="modelValue"
        :format="format"
        :language="language"
        :show-search="true"
        @change="onCascaderChange"
      />
    </el-popover>

    <!-- 省/市/区及详情 -->
    <GeoDetailField
      v-else-if="format === 'province_city_district_detail'"
      :model-value="modelValue"
      :format="format"
      :language="language"
      @update:model-value="emitValue"
    />

    <!-- 国家和地区 -->
    <GeoRegionSelect
      v-else-if="format === 'country_region'"
      :model-value="modelValue"
      :language="language"
      @update:model-value="emitValue"
    />

    <!-- 经度和纬度 / 地图选点 -->
    <GeoLngLatField
      v-else-if="format === 'lng_lat' || format === 'map_picker'"
      :model-value="modelValue"
      :language="language"
      @update:model-value="emitValue"
    />
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { LocationInformation } from "@element-plus/icons-vue";
import { t, getI18nLanguage } from "@/i18n";
import GeoCascader from "./GeoCascader.vue";
import GeoDetailField from "./GeoDetailField.vue";
import GeoRegionSelect from "./GeoRegionSelect.vue";
import GeoLngLatField from "./GeoLngLatField.vue";
import { formatGeoValue } from "@/utils/geo";
import type { GeoValue, GeoFormat } from "@/types/fields";

const props = defineProps<{
  modelValue?: GeoValue | null;
  // 兼容多种字段对象（FieldEntity / 表单字段 / 索引字段），仅消费 options.geoFormat
  field?: any;
  readonly?: boolean;
  // 内嵌模式：直接渲染面板（不 teleport），用于表格单元格编辑器，避免点击穿透
  inline?: boolean;
}>();

const emit = defineEmits<{
  (e: "update:modelValue", v: GeoValue): void;
}>();

const format = computed<GeoFormat>(
  () => (props.field?.options?.geoFormat as GeoFormat) || "province_city_district"
);

// 地理数据语言统一跟随界面当前语言（「设置」中切换 中文/English 后立即生效）。
// 字段级别不再提供语言配置。
const language = computed<"zh" | "en">(() =>
  getI18nLanguage().startsWith("en") ? "en" : "zh"
);

const isCascaderFormat = computed(() =>
  ["province", "province_city", "province_city_district"].includes(format.value)
);

const cascaderPopWidth = computed(() =>
  format.value === "province" ? 180 : format.value === "province_city" ? 360 : 540
);

const displayText = computed(() => formatGeoValue(props.modelValue, format.value));

const placeholder = computed(() => {
  switch (format.value) {
    case "province":
      return t("field.geo.format.province");
    case "province_city":
      return t("field.geo.format.province_city");
    case "province_city_district":
      return t("field.geo.format.province_city_district");
    default:
      return t("field.geo.selectAddress");
  }
});

function emitValue(v: GeoValue) {
  emit("update:modelValue", v);
}

function onCascaderChange(patch: Partial<GeoValue>) {
  emit("update:modelValue", { ...(props.modelValue || {}), ...patch });
}
</script>

<style scoped lang="scss">
.geo-field {
  &__readonly {
    display: flex;
    align-items: center;
    gap: 4px;
    color: #1f2329;

    .el-icon {
      color: #3370ff;
    }
  }

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
    min-height: 32px;

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
}
</style>

<!--
  非 scoped：地理弹层(el-popover)会被 teleport 到 body。
  在表格单元格中，GeoLocationEditor 的宿主浮层挂载在 VTable 的“编辑器容器层”
  之上（该层 z-index 高于单元格），而 body 中的弹层默认仅 ~2000，会渲染在该层
  背后，导致点击级联/地区控件时穿透到表格、误触行。
  这里将地理弹层抬到极高 z-index，确保始终位于 VTable 编辑器容器层之上。
-->
<style lang="scss">
.geo-popover {
  z-index: 100000 !important;
}
</style>
