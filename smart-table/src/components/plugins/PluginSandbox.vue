<script setup lang="ts">
/**
 * 插件 iframe 沙箱容器
 *
 * 隔离机制：sandbox="allow-scripts"（不带 allow-same-origin）→ 内容为 opaque origin，
 * 即使 URL 同源也无法访问宿主 Cookie/localStorage/DOM；
 * 来源校验不依赖 event.origin（恒为 "null"），改用一次性握手 token。
 */
import { ref, onMounted, onBeforeUnmount, nextTick } from "vue";
import { fetchSandboxUrl } from "@/api/plugins";
import { createPluginBridge, generateHandshakeToken } from "@/plugins/rpc";
import { buildApiSurface } from "@/plugins/api-surface";
import { buildSelectionSnapshot } from "@/plugins/selection";
import { reportPluginError } from "@/plugins/registry";
import type { ExtensionPointType } from "@/plugins/types";

const props = withDefaults(
  defineProps<{
    pluginId: string;
    baseId: string;
    tableId?: string;
    extensionType?: ExtensionPointType;
    config?: Record<string, unknown>;
  }>(),
  {
    tableId: "",
    extensionType: "side-panel",
    config: () => ({}),
  },
);

const emit = defineEmits<{
  (e: "loaded"): void;
  (e: "error", message: string): void;
}>();

const iframeRef = ref<HTMLIFrameElement | null>(null);
const sandboxUrl = ref("");
const loading = ref(true);
const errorMessage = ref("");

let bridge: { destroy: () => void } | null = null;

/** 加载插件：取签名 URL → 生成握手 token → 绑定 RPC 桥 → 设置 iframe src */
async function loadPlugin(): Promise<void> {
  loading.value = true;
  errorMessage.value = "";
  try {
    const { url } = await fetchSandboxUrl(props.pluginId, props.baseId);
    const token = generateHandshakeToken();

    await nextTick();
    const win = iframeRef.value?.contentWindow;
    if (!win) {
      throw new Error("iframe contentWindow 不可用");
    }

    // 取插件权限与配置（用于构造受权的 API 处理器表）
    const { fetchPlugin, fetchPluginConfig } = await import("@/api/plugins");
    const plugin = await fetchPlugin(props.pluginId);
    const permissions = plugin.manifest?.permissions || {};
    const config =
      Object.keys(props.config || {}).length > 0
        ? props.config
        : await fetchPluginConfig(props.pluginId, props.baseId).catch(() => ({}));
    const handlers = buildApiSurface(permissions);

    bridge = createPluginBridge({
      iframeWindow: win,
      handshakeToken: token,
      handlers,
      permissions,
      context: {
        pluginId: props.pluginId,
        baseId: props.baseId,
        tableId: props.tableId,
        config: config || {},
        // 打开插件瞬间的表格勾选快照（仅记录 ID；勾选变化需重开插件感知）
        selection: buildSelectionSnapshot(),
      },
    });

    // token 经 URL fragment 传入（不进服务器日志/Referer）
    sandboxUrl.value = `${url}#token=${encodeURIComponent(token)}`;
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    errorMessage.value = message;
    loading.value = false;
    reportPluginError(props.pluginId, props.extensionType, message);
    emit("error", message);
    console.error("[PluginSandbox] 插件加载失败:", error);
  }
}

function handleIframeLoad(): void {
  // 握手由 RPC 桥异步确认，这里仅结束骨架加载态
  loading.value = false;
  emit("loaded");
}

function handleIframeError(): void {
  const message = "插件沙箱加载失败";
  errorMessage.value = message;
  loading.value = false;
  reportPluginError(props.pluginId, props.extensionType, message);
  emit("error", message);
}

onMounted(loadPlugin);

onBeforeUnmount(() => {
  bridge?.destroy();
  bridge = null;
});

defineExpose({ reload: loadPlugin });
</script>

<template>
  <div class="plugin-sandbox">
    <div v-if="loading && !errorMessage" class="plugin-sandbox__loading">
      <el-skeleton :rows="4" animated />
    </div>

    <div v-else-if="errorMessage" class="plugin-sandbox__error">
      <el-empty :description="errorMessage">
        <el-button
          size="small"
          @click="
            () => {
              errorMessage = '';
              loadPlugin();
            }
          ">
          重试
        </el-button>
      </el-empty>
    </div>

    <iframe
      v-show="!loading && !errorMessage"
      ref="iframeRef"
      class="plugin-sandbox__frame"
      :src="sandboxUrl"
      sandbox="allow-scripts"
      referrerpolicy="no-referrer"
      @load="handleIframeLoad"
      @error="handleIframeError" />
  </div>
</template>

<style scoped>
.plugin-sandbox {
  width: 100%;
  height: 100%;
  position: relative;
  background: #fff;
}

.plugin-sandbox__frame {
  width: 100%;
  height: 100%;
  border: none;
  display: block;
}

.plugin-sandbox__loading {
  padding: 16px;
}

.plugin-sandbox__error {
  padding: 24px 0;
}
</style>
