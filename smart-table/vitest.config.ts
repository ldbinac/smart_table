import { defineConfig } from "vitest/config";
import vue from "@vitejs/plugin-vue";
import { fileURLToPath, URL } from "node:url";
import path from "node:path";
import { createRequire } from "node:module";

const require = createRequire(import.meta.url);

/**
 * Vitest 在 Node ESM 环境下不会为裸导入的包子路径自动补全 .js 扩展名。
 * @opentiny/fluent-editor 等包内部存在 `import { Range } from "quill/core/selection"`
 * 这类无扩展名的 ESM 导入，构建阶段 Vite 可以解析，但测试阶段会报
 * ERR_MODULE_NOT_FOUND。此插件为 quill 子路径自动补全 .js。
 */
function quillExtensionResolver() {
  return {
    name: "quill-extension-resolver",
    enforce: "pre" as const,
    async resolveId(source: string, _importer: string | undefined, _options: any) {
      if (
        source.startsWith("quill/") &&
        !source.endsWith("/") &&
        !path.extname(source)
      ) {
        try {
          const quillRoot = path.dirname(require.resolve("quill/package.json"));
          const resolved = path.join(quillRoot, `${source.slice(6)}.js`);
          return resolved;
        } catch {
          // 兜底：交给默认解析器处理
        }
      }
    },
  };
}

export default defineConfig({
  plugins: [vue(), quillExtensionResolver()],
  test: {
    globals: true,
    environment: "jsdom",
    setupFiles: ["./test-setup.ts"],
    include: ["src/**/*.{test,spec}.{js,mjs,cjs,ts,mts,cts,jsx,tsx}"],
    deps: {
      inline: ["@opentiny/fluent-editor", "quill"],
    },
    coverage: {
      provider: "v8",
      reporter: ["text", "json", "html"],
      include: ["src/**/*.ts", "src/**/*.vue"],
      exclude: ["src/**/*.d.ts", "src/**/__tests__/**", "src/main.ts"],
    },
  },
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
});
