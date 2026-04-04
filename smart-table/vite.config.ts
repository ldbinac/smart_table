import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import AutoImport from "unplugin-auto-import/vite";
import Components from "unplugin-vue-components/vite";
import { ElementPlusResolver } from "unplugin-vue-components/resolvers";
import { fileURLToPath, URL } from "node:url";

export default defineConfig({
  plugins: [
    vue(),
    AutoImport({
      imports: ["vue", "vue-router", "pinia"],
      resolvers: [ElementPlusResolver()],
      dts: "src/auto-imports.d.ts",
      eslintrc: {
        enabled: true,
      },
    }),
    Components({
      resolvers: [ElementPlusResolver()],
      dts: "src/components.d.ts",
    }),
  ],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  css: {
    preprocessorOptions: {
      scss: {
        additionalData: `
          @use "@/assets/styles/variables" as *;
          @use "@/assets/styles/mixins" as *;
        `,
      },
    },
  },
  server: {
    port: 3000,
    open: true,
    proxy: {
      "/api": {
        target: "http://localhost:5000",
        changeOrigin: true,
        secure: false,
        ws: true,
        followRedirects: true,
        configure: (proxy) => {
          proxy.on("proxyReq", (proxyReq, req) => {
            proxyReq.setHeader("Origin", "http://localhost:5000");
            proxyReq.setHeader("Referer", "http://localhost:5000/");
          });
          proxy.on("proxyRes", (proxyRes, req) => {
            // 移除重定向响应中的 Location 主机部分，保持代理路径
            if (
              proxyRes.headers.location &&
              proxyRes.headers.location.includes("localhost:5000")
            ) {
              proxyRes.headers.location = proxyRes.headers.location.replace(
                "http://localhost:5000",
                "",
              );
            }
          });
        },
      },
    },
  },
  build: {
    sourcemap: true,
  },
});
