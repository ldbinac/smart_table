<template>
  <div class="tianditu-map">
    <div ref="mapEl" class="tianditu-map__canvas"></div>

    <!-- 加载中骨架 -->
    <div v-if="loading" class="tianditu-map__overlay">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>{{ t("field.geo.mapLoading") }}</span>
    </div>

    <!-- 加载失败 -->
    <div v-else-if="error" class="tianditu-map__overlay tianditu-map__overlay--error">
      <el-icon><WarningFilled /></el-icon>
      <span>{{ t("field.geo.mapLoadFailed") }}</span>
      <small v-if="errorMsg">{{ errorMsg }}</small>
    </div>

    <!-- 顶部搜索与定位 -->
    <div v-if="!loading && !error" class="tianditu-map__toolbar">
      <el-input
        v-model="keyword"
        :placeholder="t('field.geo.mapSearchPlaceholder')"
        clearable
        size="default"
        @keyup.enter="doSearch"
        @input="onKeywordInput"
      >
        <template #append>
          <el-button :icon="Search" @click="doSearch">{{ t("field.geo.search") }}</el-button>
        </template>
      </el-input>
      <el-tooltip :content="t('field.geo.mapLocate')">
        <el-button circle :icon="Aim" @click="locateMe" />
      </el-tooltip>
    </div>

    <!-- 搜索候选列表 -->
    <transition name="el-zoom-in-top">
      <div v-if="showSuggestions" class="tianditu-map__results">
        <ul v-if="suggestions.length">
          <li
            v-for="(s, i) in suggestions"
            :key="i"
            :class="{ active: selected && selected.lng === s.lng && selected.lat === s.lat }"
            @click="selectSuggestion(s)"
          >
            <span class="name">{{ s.name }}</span>
            <span v-if="s.address" class="addr">{{ s.address }}</span>
          </li>
        </ul>
        <div v-else class="empty">{{ t("field.geo.mapNoResult") }}</div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, watch } from "vue";
import { ElMessage } from "element-plus";
import { Loading, WarningFilled, Search, Aim } from "@element-plus/icons-vue";
import { t } from "@/i18n";
import { loadTianditu } from "@/utils/tiandituLoader";
import { getGeoLocate } from "@/services/api";

interface Suggestion {
  name: string;
  address: string;
  lng: number;
  lat: number;
}

const props = defineProps<{
  /** 初始坐标 {lng, lat} */
  value?: { lng?: number; lat?: number } | null;
  /** 语言：zh（默认）/ en，用于天地图 UI 与搜索结果语言 */
  lang?: "zh" | "en";
}>();

const emit = defineEmits<{
  (e: "pick", payload: { lng: number; lat: number }): void;
}>();

const mapEl = ref<HTMLDivElement | null>(null);
const loading = ref(true);
const error = ref(false);
const errorMsg = ref("");
const keyword = ref("");
const suggestions = ref<Suggestion[]>([]);
const showSuggestions = ref(false);

const selected = ref<{ lng: number; lat: number } | null>(null);

let map: any = null;
let marker: any = null;
let searchService: any = null;
let T: any = null;

const DEFAULT_CENTER = [116.397428, 39.90923]; // 北京天安门

function ensureMarker(lng: number, lat: number) {
  if (!T || !map) return;
  if (marker) {
    map.removeOverLay(marker);
  }
  marker = new T.Marker(new T.LngLat(lng, lat));
  map.addOverLay(marker);
}

/** 仅居中（不落点），用于自动定位 / 初始化 */
function centerMap(lng: number, lat: number, zoom = 12) {
  if (!map || !T) return;
  map.centerAndZoom(new T.LngLat(lng, lat), zoom);
}

/** 居中并落点 + 回传坐标 */
function centerTo(lng: number, lat: number, zoom = 14) {
  centerMap(lng, lat, zoom);
  ensureMarker(lng, lat);
  emit("pick", { lng: Number(lng.toFixed(6)), lat: Number(lat.toFixed(6)) });
}

function handleClick(e: any) {
  const lnglat = e?.lnglat || e?.containerPoint;
  if (!lnglat) return;
  const lng = typeof lnglat.getLng === "function" ? lnglat.getLng() : lnglat.lng;
  const lat = typeof lnglat.getLat === "function" ? lnglat.getLat() : lnglat.lat;
  if (lng === undefined || lat === undefined) return;
  ensureMarker(lng, lat);
  selected.value = { lng: Number(lng.toFixed(6)), lat: Number(lat.toFixed(6)) };
  emit("pick", selected.value);
  showSuggestions.value = false;
}

/** 尝试用浏览器定位获取当前坐标（受权限与 HTTPS 限制） */
function browserLocate(): Promise<{ lng: number; lat: number }> {
  return new Promise((resolve, reject) => {
    if (!("geolocation" in navigator)) {
      reject(new Error("unsupported"));
      return;
    }
    const invoke = () =>
      navigator.geolocation.getCurrentPosition(
        (pos) => resolve({ lng: pos.coords.longitude, lat: pos.coords.latitude }),
        (err) => reject(err),
        { enableHighAccuracy: false, timeout: 8000, maximumAge: 600000 }
      );

    // 已拒绝授权则直接跳过，避免反复弹窗
    if (navigator.permissions && navigator.permissions.query) {
      navigator.permissions
        .query({ name: "geolocation" as PermissionName })
        .then((st) => {
          if (st.state === "denied") reject(new Error("denied"));
          else invoke();
        })
        .catch(() => invoke());
    } else {
      invoke();
    }
  });
}

/** 自动定位：已有值 > 浏览器定位 > 服务端 IP 定位 > 默认北京 */
async function autoLocate() {
  if (props.value?.lng && props.value?.lat) {
    centerTo(props.value.lng, props.value.lat, 14);
    return;
  }

  try {
    const pos = await browserLocate();
    centerMap(pos.lng, pos.lat, 14);
    return;
  } catch {
    /* 浏览器定位不可用/被拒，继续尝试 IP 定位 */
  }

  try {
    const data = await getGeoLocate();
    if (data.enabled && data.lng && data.lat) {
      centerMap(data.lng, data.lat, 12);
      return;
    }
  } catch {
    /* IP 定位失败，回退默认中心 */
  }

  centerMap(DEFAULT_CENTER[0], DEFAULT_CENTER[1], 12);
}

/** 兼容多种 lonlat 形态：T.LngLat 对象 / {lng,lat} / "lng,lat" 字符串 */
function parseLonlat(ll: any): { lng?: number; lat?: number } {
  if (!ll) return {};
  if (typeof ll.getLng === "function" && typeof ll.getLat === "function") {
    return { lng: Number(ll.getLng()), lat: Number(ll.getLat()) };
  }
  if (typeof ll.lng === "number" && typeof ll.lat === "number") {
    return { lng: ll.lng, lat: ll.lat };
  }
  if (typeof ll === "string" && ll.includes(",")) {
    const [lng, lat] = ll.split(",").map(Number);
    if (!Number.isNaN(lng) && !Number.isNaN(lat)) return { lng, lat };
  }
  return {};
}

function onKeywordInput() {
  if (!keyword.value.trim()) showSuggestions.value = false;
}

function doSearch() {
  if (!keyword.value.trim()) return;
  if (!T || !map) return;
  try {
    if (!searchService && typeof T.LocalSearch === "function") {
      searchService = new T.LocalSearch(map, {
        pageCapacity: 8,
        onSearchComplete: (result: any) => {
          const pois =
            result && typeof result.getPois === "function" ? result.getPois() : null;
          if (!pois || !pois.length) {
            suggestions.value = [];
            showSuggestions.value = true;
            return;
          }
          suggestions.value = pois
            .map((p: any) => {
              const { lng, lat } = parseLonlat(p?.lonlat);
              if (lng === undefined || lat === undefined) return null;
              return {
                name: p?.name || "",
                address: p?.address || "",
                lng: Number(lng),
                lat: Number(lat),
              };
            })
            .filter((s: Suggestion | null): s is Suggestion => !!s);
          showSuggestions.value = true;
        },
      });
    }
    if (searchService) {
      searchService.search(keyword.value.trim());
    } else {
      ElMessage.warning(t("field.geo.mapLoadFailed"));
    }
  } catch (err) {
    console.error("[TiandituMap] 搜索失败", err);
    ElMessage.warning(t("field.geo.mapLoadFailed"));
  }
}

function selectSuggestion(s: Suggestion) {
  centerTo(s.lng, s.lat);
  selected.value = { lng: Number(s.lng.toFixed(6)), lat: Number(s.lat.toFixed(6)) };
  showSuggestions.value = false;
}

function locateMe() {
  if (!navigator.geolocation) {
    ElMessage.warning(t("field.geo.mapLoadFailed"));
    return;
  }
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      const { longitude, latitude } = pos.coords;
      centerTo(longitude, latitude);
      selected.value = {
        lng: Number(longitude.toFixed(6)),
        lat: Number(latitude.toFixed(6)),
      };
    },
    () => {
      ElMessage.warning(t("field.geo.mapLoadFailed"));
    },
    { enableHighAccuracy: true, timeout: 8000 }
  );
}

onMounted(async () => {
  try {
    T = await loadTianditu(props.lang);
  } catch (err: any) {
    error.value = true;
    errorMsg.value = err?.message || "";
    loading.value = false;
    return;
  }
  if (!mapEl.value) return;

  map = new T.Map(mapEl.value);
  map.addEventListener("click", handleClick);
  loading.value = false;

  // 自动定位到用户所在位置（不再默认北京）
  void autoLocate();
});

watch(
  () => props.value,
  (v) => {
    if (v?.lng && v?.lat && map && T) {
      centerTo(v.lng, v.lat);
    }
  }
);

onBeforeUnmount(() => {
  if (map) {
    try {
      map.clearOverLays();
      map.destroy();
    } catch {
      /* 忽略 */
    }
    map = null;
  }
});
</script>

<style scoped lang="scss">
.tianditu-map {
  position: relative;
  width: 100%;
  height: 600px;
  border-radius: 8px;
  overflow: hidden;

  &__canvas {
    width: 100%;
    height: 100%;
    /* 建立独立层叠上下文，避免天地图内部高 z-index 的瓦片/控件面板
       溢出到父级，盖住顶部的搜索框与结果列表 */
    position: relative;
    z-index: 0;
  }

  &__overlay {
    position: absolute;
    inset: 0;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 8px;
    background: #f5f6f8;
    color: #8f959e;
    font-size: 14px;
    z-index: 10;

    .el-icon {
      font-size: 28px;
    }

    small {
      color: #b0b3b8;
      font-size: 12px;
    }

    &--error {
      color: #f54a45;
    }
  }

  &__toolbar {
    position: absolute;
    top: 12px;
    left: 12px;
    right: 12px;
    display: flex;
    gap: 8px;
    z-index: 20;

    .el-input {
      max-width: 320px;
      background: #fff;
    }
  }

  &__results {
    position: absolute;
    top: 62px;
    left: 12px;
    width: 300px;
    max-width: calc(100% - 24px);
    max-height: 320px;
    overflow-y: auto;
    background: #fff;
    border-radius: 8px;
    box-shadow: 0 6px 20px rgba(0, 0, 0, 0.15);
    z-index: 30;
    padding: 4px;

    ul {
      list-style: none;
      margin: 0;
      padding: 0;
    }

    li {
      display: flex;
      flex-direction: column;
      gap: 2px;
      padding: 8px 10px;
      border-radius: 6px;
      cursor: pointer;

      &:hover {
        background: #f5f6f8;
      }

      &.active {
        background: #eaf1ff;
      }

      .name {
        font-size: 13px;
        color: #1f2329;
      }

      .addr {
        font-size: 12px;
        color: #8f959e;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
      }
    }

    .empty {
      padding: 12px;
      text-align: center;
      font-size: 13px;
      color: #8f959e;
    }
  }
}
</style>
