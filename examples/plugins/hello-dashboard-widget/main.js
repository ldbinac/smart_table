/**
 * Hello Dashboard Widget —— 扩展点示例（dashboard-widget）
 *
 * 演示：在仪表盘自定义组件区挂载一个组件。仪表盘配置数据表后，宿主会在上下文
 *（ui.getContext().tableId）中带上该表 ID；组件据此读取表结构并统计记录总数。
 * 若仪表盘未配置数据表，则友好提示。
 *
 * 复制本目录（manifest.json + main.js）即可作为独立插件上传安装。
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
      ".hp__metric{font-size:13px;color:#909399;}",
      ".hp__num{font-size:36px;font-weight:700;color:#303133;line-height:1.2;}",
      ".hp__table{margin-top:8px;color:#606266;font-size:13px;}",
      ".hp__btn{padding:6px 14px;border:1px solid #dcdfe6;border-radius:4px;background:#fff;color:#606266;font-size:13px;cursor:pointer;}",
      ".hp__btn--primary{background:#409EFF;color:#fff;border-color:#409EFF;}",
      ".hp__btn:disabled{opacity:.6;cursor:not-allowed;}",
      ".hp__status{margin:8px 0;color:#909399;font-size:13px;}",
      ".hp__hint{margin-top:10px;color:#E6A23C;font-size:13px;}",
    ].join("\n");
    var style = document.createElement("style");
    style.textContent = css;
    document.head.appendChild(style);
  })();

  Vue.createApp({
    template: `
      <div class="hp">
        <h3 class="hp__title">{{ metricName }}</h3>
        <p class="hp__desc">入口为 dashboard-widget：读取仪表盘配置的数据表并展示统计。</p>

        <div v-if="tableId">
          <div class="hp__metric">{{ tableName }}</div>
          <div class="hp__num">{{ totalText }}</div>
          <div class="hp__table">数据表：{{ tableId }}</div>
          <button class="hp__btn hp__btn--primary" :disabled="loading" @click="refresh" style="margin-top:10px">
            刷新统计
          </button>
        </div>
        <div v-else>
          <div class="hp__status">尚未配置数据表。</div>
          <div class="hp__hint">请在仪表盘编辑中为本组件选择一张数据表。</div>
        </div>
      </div>
    `,

    data() {
      return {
        config: {},
        context: null,
        tableId: "",
        tableName: "",
        total: null,
        loading: false,
      };
    },

    computed: {
      metricName() {
        return (this.config && this.config.metricName) || "记录总数";
      },
      totalText() {
        return this.total == null ? "—" : String(this.total);
      },
    },

    methods: {
      async init() {
        try {
          this.config = (await SDK.request("config.get", {})) || {};
        } catch (e) {
          this.config = {};
        }
        try {
          this.context = (await SDK.request("ui.getContext", {})) || {};
          this.tableId = this.context.tableId || "";
        } catch (e) {
          this.context = {};
        }
        if (this.tableId) {
          await this.refresh();
        }
      },

      async refresh() {
        if (!this.tableId) return;
        this.loading = true;
        try {
          var schema = await SDK.request("table.getSchema", { tableId: this.tableId });
          this.tableName = (schema && schema.name) || "（未命名表）";
          var res = await SDK.request("table.getRecords", {
            tableId: this.tableId,
            per_page: 1,
          });
          this.total = (res && res.total != null) ? res.total : 0;
        } catch (err) {
          this.total = null;
          await SDK.request("ui.notify", { message: "统计失败：" + ((err && err.message) || err), type: "error" });
        } finally {
          this.loading = false;
        }
      },
    },

    async mounted() {
      await this.init();
    },
  }).mount("#app");
})();
