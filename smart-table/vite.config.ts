import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import AutoImport from "unplugin-auto-import/vite";
import Components from "unplugin-vue-components/vite";
import { ElementPlusResolver } from "unplugin-vue-components/resolvers";
import { fileURLToPath, URL } from "node:url";
import { resolve } from "node:path";
import { readFileSync, writeFileSync, existsSync } from "node:fs";
import { createHash } from "node:crypto";

/**
 * 版本号来源优先级：
 * 1. 环境变量 VITE_APP_VERSION / APP_VERSION（由 build.py / build_docker.py / Dockerfile 注入）
 * 2. 项目根目录 version.json 的 version 字段
 * 3. package.json 的 version 字段
 */
function resolveVersion(): { version: string; buildTime: string } {
  const buildTime = new Date().toISOString();

  // 1. 优先环境变量
  const envVersion = process.env.VITE_APP_VERSION || process.env.APP_VERSION;
  if (envVersion) {
    return { version: envVersion, buildTime };
  }

  // 2. 尝试项目根目录 version.json
  try {
    const rootVersionJson = resolve(__dirname, "..", "version.json");
    if (existsSync(rootVersionJson)) {
      const data = JSON.parse(readFileSync(rootVersionJson, "utf-8"));
      if (data.version) return { version: String(data.version), buildTime };
    }
  } catch { /* ignore */ }

  // 3. fallback 到 package.json
  try {
    const pkgJson = resolve(__dirname, "package.json");
    if (existsSync(pkgJson)) {
      const data = JSON.parse(readFileSync(pkgJson, "utf-8"));
      if (data.version) return { version: String(data.version), buildTime };
    }
  } catch { /* ignore */ }

  return { version: "0.0.0-dev", buildTime };
}

/**
 * Vite 插件：在 closeBundle 时向 dist/ 根目录写入 version.json
 * 同时在 buildHash 中基于源码 + 版本号生成唯一哈希
 */
function generateVersionPlugin() {
  return {
    name: "generate-version-json",
    closeBundle() {
      const { version, buildTime } = resolveVersion();

      // buildHash: 版本号 + 时间戳 + 随机盐 → 唯一标识每次构建
      const buildHash = createHash("sha256")
        .update(`${version}-${buildTime}-${Math.random()}`)
        .digest("hex")
        .slice(0, 16);

      const versionData = {
        version,
        buildTime,
        buildHash,
        buildNumber: parseInt(buildTime.replace(/[-:T.]/g, "").slice(0, 14), 10),
      };

      const distDir = resolve(__dirname, "dist");
      const target = resolve(distDir, "version.json");
      writeFileSync(target, JSON.stringify(versionData, null, 2) + "\n", "utf-8");

      // eslint-disable-next-line no-console
      console.log(`  📦 version.json: ${version} (hash: ${buildHash})`);
    },
  };
}

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
    generateVersionPlugin(),
  ],
  // 允许读取非 VITE_ 前缀的环境变量（APP_VERSION）
  envPrefix: ["VITE_", "APP_"],
  define: {
    // 将版本号注入所有客户端模块，避免运行时再 parse version.json
    __APP_VERSION__: JSON.stringify(resolveVersion().version),
  },
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
    host: '0.0.0.0', // 允许远程访问
    open: true,
    proxy: {
      "/api": {
        target: "http://localhost:5000",
        changeOrigin: true,
        secure: false,
        ws: true,
        followRedirects: true,
        configure: (proxy) => {
          proxy.on("proxyReq", (proxyReq, req: any) => {
            // 插件沙箱 loader.html：保持浏览器原始 Host。
            // 后端依据 Host 生成沙箱 CSP；changeOrigin 改写 Host 后，
            // CSP 会放行 localhost:5000 而沙箱文档实际在 localhost:3000，
            // vendor/vue.global.prod.js 等相对资源会被 CSP 拦截。
            if ((req.url || "").includes("loader.html")) {
              if (req.headers.host) {
                proxyReq.setHeader("Host", req.headers.host);
              }
              return;
            }
            // 保留原始请求的所有头信息，包括 Authorization
            const headers = req.headers;
            if (headers.authorization) {
              proxyReq.setHeader("Authorization", headers.authorization);
            }
            if (headers["content-type"]) {
              proxyReq.setHeader("Content-Type", headers["content-type"]);
            }
            proxyReq.setHeader("Origin", "http://localhost:5000");
            proxyReq.setHeader("Referer", "http://localhost:5000/");
          });
          proxy.on("proxyRes", (proxyRes, _req) => {
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
      // 代理上传文件请求到后端
      "/uploads": {
        target: "http://localhost:5000",
        changeOrigin: true,
        secure: false,
        rewrite: (path) => `/api/attachments${path}`,
      },
    },
  },
  build: {
    sourcemap: process.env.NODE_ENV === 'development',
    minify: 'esbuild',
  },
});
