import { createApp } from "vue";
import { createPinia } from "pinia";
import ElementPlus from "element-plus";
import * as ElementPlusIconsVue from "@element-plus/icons-vue";
import "element-plus/dist/index.css";
import VxeTable from "vxe-table";
import "vxe-table/lib/style.css";

import App from "./App.vue";
import router from "./router";
import i18n from "./i18n";
import { db } from "./db";
import { initDayjsPlugins } from "./utils/timezone";
import { getTokenRefreshService } from "./services/tokenRefreshService";

// 初始化时区插件
initDayjsPlugins();

// 将 db 暴露到全局，方便调试
if (typeof window !== "undefined") {
  (window as any).db = db;
}

const app = createApp(App);

app.use(createPinia());
app.use(router);
app.use(i18n);
app.use(ElementPlus);
app.use(VxeTable);

for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component);
}

app.mount("#app");

// 初始化Token自动续期服务
const tokenRefreshService = getTokenRefreshService();
tokenRefreshService.start();

// 隐藏启动加载层（幂等，可重复调用）
let loadingHidden = false;
function hideAppLoading() {
  if (loadingHidden) return;
  const loadingEl = document.getElementById("app-loading");
  if (!loadingEl) {
    loadingHidden = true;
    return;
  }
  loadingHidden = true;
  loadingEl.classList.add("fade-out");
  // 动画完成后移除元素
  setTimeout(() => loadingEl.remove(), 300);
}

// 等待路由准备完成后隐藏加载状态
router.isReady().then(hideAppLoading).catch(hideAppLoading);

// 兜底：首屏导航被取消/失败时 router.isReady() 可能既不 resolve 也不 reject，
// 导致加载层永久盖在页面上（全屏 z-index 9999，会拦截所有点击）
setTimeout(hideAppLoading, 1500);

// 应用销毁时清理资源
window.addEventListener('beforeunload', () => {
  tokenRefreshService.destroy();
});
