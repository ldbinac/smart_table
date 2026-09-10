<template>
  <div class="geo-cascader">
    <div class="geo-cascader__search" v-if="showSearch">
      <el-input
        v-model="keyword"
        :placeholder="t('field.geo.search')"
        clearable
        size="small"
        :prefix-icon="Search"
      />
    </div>

    <div class="geo-cascader__columns" :style="{ '--cols': columns }">
      <div class="geo-cascader__col">
        <div
          v-for="p in filteredProvinces"
          :key="p.name"
          class="geo-cascader__item"
          :class="{ active: p.name === current.province }"
          @click="selectProvince(p)"
        >
          <span class="name">{{ p.name }}</span>
          <el-icon v-if="p.name === current.province"><ArrowRight /></el-icon>
        </div>
        <div v-if="!filteredProvinces.length" class="geo-cascader__empty">
          {{ t("field.geo.detailRecognizeFailed") }}
        </div>
      </div>

      <div class="geo-cascader__col" v-if="columns >= 2">
        <div
          v-for="c in filteredCities"
          :key="c.name"
          class="geo-cascader__item"
          :class="{ active: c.name === current.city }"
          @click="selectCity(c)"
        >
          <span class="name">{{ c.name }}</span>
          <el-icon v-if="c.name === current.city"><ArrowRight /></el-icon>
        </div>
        <div v-if="current.province && !filteredCities.length" class="geo-cascader__empty">
          —
        </div>
      </div>

      <div class="geo-cascader__col" v-if="columns >= 3">
        <div
          v-for="d in filteredDistricts"
          :key="d.name"
          class="geo-cascader__item"
          :class="{ active: d.name === current.district }"
          @click="selectDistrict(d)"
        >
          <span class="name">{{ d.name }}</span>
        </div>
        <div v-if="current.city && !filteredDistricts.length" class="geo-cascader__empty">—</div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import { ArrowRight, Search } from "@element-plus/icons-vue";
import { t } from "@/i18n";
import { getChinaLocations } from "@/services/api";
import type { GeoChinaNode, GeoValue, GeoFormat } from "@/types/fields";

const props = defineProps<{
  modelValue?: GeoValue | null;
  format: GeoFormat;
  showSearch?: boolean;
  language?: "zh" | "en";
}>();

const emit = defineEmits<{
  (e: "change", v: Partial<GeoValue>): void;
}>();

/** 列数：省份=1，省份/城市=2，其余含区=3 */
const columns = computed(() => {
  switch (props.format) {
    case "province":
      return 1;
    case "province_city":
      return 2;
    default:
      return 3;
  }
});

const tree = ref<GeoChinaNode[]>([]);
const keyword = ref("");
const current = ref<Partial<GeoValue>>({
  province: props.modelValue?.province,
  city: props.modelValue?.city,
  district: props.modelValue?.district,
});

const filteredProvinces = computed(() => {
  const list = tree.value;
  if (!keyword.value) return list;
  const kw = keyword.value.trim();
  return list.filter((p) => p.name.includes(kw));
});

const selectedProvinceNode = computed(() =>
  tree.value.find((p) => p.name === current.value.province)
);

const filteredCities = computed(() => {
  const list = selectedProvinceNode.value?.children || [];
  if (!keyword.value) return list;
  const kw = keyword.value.trim();
  return list.filter((c) => c.name.includes(kw));
});

const selectedCityNode = computed(() =>
  selectedProvinceNode.value?.children?.find((c) => c.name === current.value.city)
);

const filteredDistricts = computed(() => {
  const list = selectedCityNode.value?.children || [];
  if (!keyword.value) return list;
  const kw = keyword.value.trim();
  return list.filter((d) => d.name.includes(kw));
});

function selectProvince(p: GeoChinaNode) {
  current.value = { province: p.name };
  emit("change", { province: p.name, city: undefined, district: undefined });
}

function selectCity(c: GeoChinaNode) {
  current.value.city = c.name;
  current.value.district = undefined;
  emit("change", { province: current.value.province, city: c.name, district: undefined });
}

function selectDistrict(d: GeoChinaNode) {
  current.value.district = d.name;
  emit("change", {
    province: current.value.province,
    city: current.value.city,
    district: d.name,
  });
}

async function loadTree(lang: "zh" | "en") {
  try {
    tree.value = await getChinaLocations("district", lang);
  } catch (err) {
    console.error("[GeoCascader] 加载行政区划失败", err);
  }
}

onMounted(() => {
  void loadTree(props.language || "zh");
});

// 语言切换时重新拉取对应语言的行政区划数据
watch(
  () => props.language,
  (lang) => {
    void loadTree(lang || "zh");
  }
);

watch(
  () => props.modelValue,
  (v) => {
    current.value = { province: v?.province, city: v?.city, district: v?.district };
  }
);
</script>

<style scoped lang="scss">
.geo-cascader {
  width: 100%;

  &__search {
    padding: 8px;
    border-bottom: 1px solid #ebeef5;
  }

  &__columns {
    display: flex;
    min-height: 200px;
    max-height: 280px;
  }

  &__col {
    flex: 1;
    border-right: 1px solid #f0f0f0;
    overflow-y: auto;

    &:last-child {
      border-right: none;
    }
  }

  &__item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 7px 12px;
    font-size: 13px;
    color: #1f2329;
    cursor: pointer;
    transition: background 0.12s ease;

    &:hover {
      background: #f5f6f8;
    }

    &.active {
      background: #e8f0ff;
      color: #3370ff;
      font-weight: 500;
    }

    .el-icon {
      font-size: 12px;
      color: #c0c4cc;
    }
  }

  &__empty {
    padding: 16px;
    text-align: center;
    color: #b0b3b8;
    font-size: 12px;
  }
}
</style>
