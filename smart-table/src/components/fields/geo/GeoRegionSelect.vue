<template>
  <div class="geo-region">
    <!-- 内嵌模式：直接渲染搜索与列表，不 teleport -->
    <template v-if="inline">
      <el-input
        v-model="keyword"
        :placeholder="t('field.geo.searchCountryRegion')"
        size="small"
        clearable
        :prefix-icon="Search"
      />

      <div class="geo-region__list">
        <template v-for="group in filteredGroups" :key="group.name">
          <div class="geo-region__group">{{ group.name }}</div>
          <div
            v-for="item in group.matched"
            :key="item"
            class="geo-region__item"
            :class="{ active: item === modelValue?.country }"
            @click="select(item, group.name)"
          >
            <span>{{ item }}</span>
            <el-icon v-if="item === modelValue?.country"><Check /></el-icon>
          </div>
        </template>
        <div v-if="!hasMatch" class="geo-region__empty">{{ t("field.geo.detailRecognizeFailed") }}</div>
      </div>
    </template>

    <el-popover
      v-else
      placement="bottom-start"
      width="320"
      trigger="click"
      :disabled="readonly"
      popper-class="geo-popover"
    >
      <template #reference>
        <div class="geo-region__bar" :class="{ placeholder: !preview }">
          <el-icon><LocationInformation /></el-icon>
          <span class="geo-region__text">{{ preview || t("field.geo.searchCountryRegion") }}</span>
        </div>
      </template>

      <div v-if="!readonly" class="geo-region">
        <el-input
          v-model="keyword"
          :placeholder="t('field.geo.searchCountryRegion')"
          size="small"
          clearable
          :prefix-icon="Search"
        />

        <div class="geo-region__list">
          <template v-for="group in filteredGroups" :key="group.name">
            <div class="geo-region__group">{{ group.name }}</div>
            <div
              v-for="item in group.matched"
              :key="item"
              class="geo-region__item"
              :class="{ active: item === modelValue?.country }"
              @click="select(item, group.name)"
            >
              <span>{{ item }}</span>
              <el-icon v-if="item === modelValue?.country"><Check /></el-icon>
            </div>
          </template>
          <div v-if="!hasMatch" class="geo-region__empty">{{ t("field.geo.detailRecognizeFailed") }}</div>
        </div>
      </div>
    </el-popover>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import { LocationInformation, Search, Check } from "@element-plus/icons-vue";
import { t } from "@/i18n";
import { getRegions } from "@/services/api";
import type { GeoValue, GeoRegionItem } from "@/types/fields";

const props = defineProps<{
  modelValue?: GeoValue | null;
  language?: "zh" | "en";
  readonly?: boolean;
  // 内嵌模式：直接渲染面板（不 teleport），用于表格单元格编辑器
  inline?: boolean;
}>();

const emit = defineEmits<{
  (e: "update:modelValue", v: GeoValue): void;
}>();

const regions = ref<GeoRegionItem[]>([]);
const keyword = ref("");

const preview = computed(() => {
  const v = props.modelValue;
  if (!v) return "";
  return [v.region, v.country].filter(Boolean).join(" / ");
});

const filteredGroups = computed(() => {
  const kw = keyword.value.trim();
  return regions.value
    .map((g) => ({
      name: g.name,
      matched: kw ? g.items.filter((i) => i.includes(kw)) : g.items,
    }))
    .filter((g) => g.matched.length > 0);
});

const hasMatch = computed(() => filteredGroups.value.length > 0);

function select(country: string, region: string) {
  emit("update:modelValue", { region, country });
}

async function loadRegions(lang: "zh" | "en") {
  try {
    regions.value = await getRegions(lang);
  } catch (err) {
    console.error("[GeoRegionSelect] 加载国家和地区失败", err);
  }
}

onMounted(() => {
  void loadRegions(props.language || "zh");
});

// 语言切换时重新拉取对应语言的国家和地区数据
watch(
  () => props.language,
  (lang) => {
    void loadRegions(lang || "zh");
  }
);
</script>

<style scoped lang="scss">
.geo-region {
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

  &__list {
    margin-top: 8px;
    max-height: 280px;
    overflow-y: auto;
  }

  &__group {
    position: sticky;
    top: 0;
    background: #f5f6f8;
    color: #8f959e;
    font-size: 12px;
    padding: 4px 8px;
  }

  &__item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 6px 8px;
    font-size: 13px;
    cursor: pointer;
    border-radius: 4px;

    &:hover {
      background: #f5f6f8;
    }
    &.active {
      color: #3370ff;
      font-weight: 500;
    }
    .el-icon {
      color: #3370ff;
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
