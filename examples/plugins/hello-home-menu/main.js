/**
 * Hello Home Menu —— 扩展点示例（home-menu）
 *
 * 演示：在 SmartTable 首页的全局扩展菜单挂载入口，打开面板时无任何 Base 上下文
 *（ui.getContext().baseId 为空）。因此只能使用全局作用域能力：config / storage /
 * ui.notify。backend.call / network.fetch 需要 Base 上下文，在此作用域会被宿主拒绝。
 *
 * 复制本目录（manifest.json + main.js）即可作为独立插件上传安装（无需 Base 安装）。
 */
(function () {
  "use strict";

  var SDK = window.SmartTableSDK;
  var Vue = window.Vue;

  if (!SDK) {
    document.body.innerHTML =
      '<div style="padding:24px;color:#F56C6C">SmartTableSDK 未就绪：请安装并启用本插件。</div>';
    return;
  }
  if (!Vue) {
    document.body.innerHTML =
      '<div style="padding:24px;color:#F56C6C">Vue 运行时未加载。</div>';
    return;
  }

  (function injectStyles() {
    var css = [
      ".hp{padding:16px;font-family:inherit;}",
      ".hp__title{margin:0 0 4px;font-size:16px;font-weight:600;}",
      ".hp__desc{margin:0 0 12px;color:#909399;font-size:13px;}",
      ".hp__tag{display:inline-block;margin-bottom:12px;padding:2px 8px;border-radius:10px;background:#ecf5ff;color:#409EFF;font-size:12px;}",
      ".hp__card{padding:12px;border:1px solid #ebeef5;border-radius:6px;margin-bottom:10px;}",
      ".hp__num{font-size:28px;font-weight:600;color:#303133;}",
      ".hp__btn{padding:6px 14px;border:1px solid #dcdfe6;border-radius:4px;background:#fff;color:#606266;font-size:13px;cursor:pointer;}",
      ".hp__btn--primary{background:#409EFF;color:#fff;border-color:#409EFF;}",
      ".hp__btn:disabled{opacity:.6;cursor:not-allowed;}",
      ".hp__note{margin-top:8px;color:#909399;font-size:12px;}",
    ].join("\n");
    var style = document.createElement("style");
    style.textContent = css;
    document.head.appendChild(style);
  })();

  Vue.createApp({
    template: `
      <div class="hp">
        <h3 class="hp__title">{{ greeting }}，首页工具箱</h3>
        <p class="hp__desc">
          入口为 home-menu：全局作用域，无 Base 上下文，仅可用 config / storage / ui.notify。
        </p>
        <span class="hp__tag">全局作用域 · 无 Base 上下文</span>

        <div class="hp__card">
          <p class="hp__num">{{ visitCount }}</p>
          <p class="hp__note">本站累计打开次数（storage 持久化，刷新/重开保留）</p>
          <button class="hp__btn hp__btn--primary" :disabled="loading" @click="incVisits">
            +1 并保存
          </button>
        </div>

        <div class="hp__card">
          <button class="hp__btn" :disabled="loading" @click="notifyDemo">
            发送一条 ui.notify 提示
          </button>
        </div>
      </div>
    `,

    data() {
      return {
        config: {},
        visitCount: 0,
        loading: false,
      };
    },

    methods: {
      async init() {
        try {
          this.config = (await SDK.request("config.get", {})) || {};
        } catch (e) {
          this.config = {};
        }
        try {
          var n = await SDK.request("storage.get", { key: "homeVisits" });
          this.visitCount = Number(n) || 0;
        } catch (e) {
          this.visitCount = 0;
        }
      },

      async incVisits() {
        this.loading = true;
        this.visitCount += 1;
        try {
          await SDK.request("storage.set", { key: "homeVisits", value: this.visitCount });
          await SDK.request("ui.notify", { message: "已保存，当前 " + this.visitCount + " 次", type: "success" });
        } catch (err) {
          await SDK.request("ui.notify", { message: "保存失败：" + ((err && err.message) || err), type: "error" });
        } finally {
          this.loading = false;
        }
      },

      async notifyDemo() {
        await SDK.request("ui.notify", { message: (this.greeting || "Hello") + "，这是一条来自首页插件的提示", type: "info" });
      },
    },

    computed: {
      greeting() {
        return this.config.greeting || "Hello";
      },
    },

    async mounted() {
      await this.init();
    },
  }).mount("#app");
})();
