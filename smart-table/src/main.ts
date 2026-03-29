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
