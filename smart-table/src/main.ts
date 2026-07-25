import { createApp } from "vue";
import { createPinia } from "pinia";
import ElementPlus from "element-plus";
import * as ElementPlusIconsVue from "@element-plus/icons-vue";
import "element-plus/dist/index.css";
import VxeTable from "vxe-table";
import "vxe-table/lib/style.css";

import App from "./App.vue";
import router from "./router";
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
app.use(ElementPlus);
app.use(VxeTable);

for (const [key, component] of Object.entries(ElementPlusIconsVue)) {
  app.component(key, component);
}

app.mount("#app");

// 初始化Token自动续期服务
const tokenRefreshService = getTokenRefreshService();
tokenRefreshService.start();

// 等待路由准备完成后隐藏加载状态
router.isReady().then(() => {
  // 延迟一小段时间让页面渲染完成
  setTimeout(() => {
    const loadingEl = document.getElementById("app-loading");
    if (loadingEl) {
      loadingEl.classList.add("fade-out");
      // 动画完成后移除元素
      setTimeout(() => {
        loadingEl.remove();
      }, 300);
    }
  }, 100);
});

// 应用销毁时清理资源
window.addEventListener('beforeunload', () => {
  tokenRefreshService.destroy();
});
