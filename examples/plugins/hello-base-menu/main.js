/**
 * Hello Base Menu —— 扩展点示例（base-menu）
 *
 * 演示：通过 Base 顶部扩展菜单打开侧边面板，并访问 Base 作用域能力
 *（列出本 Base 全部表、读取表结构、预览记录）。base-menu 与 toolbar-button
 * 一样属于 Base 作用域，但入口在 Base 顶部菜单而非表格工具栏，且不依赖勾选。
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
      ".hp__selection{margin:0 0 10px;color:#409EFF;font-size:13px;}",
      ".hp__toolbar{display:flex;gap:8px;align-items:center;margin-bottom:10px;}",
      ".hp__select{padding:6px 8px;border:1px solid #dcdfe6;border-radius:4px;font-size:13px;min-width:200px;}",
      ".hp__btn{padding:6px 14px;border:1px solid #dcdfe6;border-radius:4px;background:#fff;color:#606266;font-size:13px;cursor:pointer;}",
      ".hp__btn--primary{background:#409EFF;color:#fff;border-color:#409EFF;}",
      ".hp__btn:disabled{opacity:.6;cursor:not-allowed;}",
      ".hp__status{margin:8px 0;color:#909399;font-size:13px;}",
      ".hp__list{display:flex;flex-direction:column;gap:6px;}",
      ".hp__empty{color:#909399;font-size:13px;padding:8px 0;}",
      ".hp__item{padding:8px 10px;border:1px solid #ebeef5;border-radius:4px;font-size:13px;color:#303133;}",
    ].join("\n");
    var style = document.createElement("style");
    style.textContent = css;
    document.head.appendChild(style);
  })();

  Vue.createApp({
    template: `
      <div class="hp">
        <h3 class="hp__title">{{ greeting }}，Base 菜单插件</h3>
        <p class="hp__desc">
          入口为 base-menu：点击 Base 顶部扩展菜单项打开本面板，可访问 Base 作用域（表/记录）。
        </p>
        <div class="hp__selection">Base：{{ baseId || "（无）" }}</div>

        <div class="hp__toolbar">
          <select class="hp__select" v-model="selectedTableId" :disabled="loading">
            <option v-for="t in tables" :key="t.id" :value="t.id">{{ t.name }}</option>
          </select>
          <button class="hp__btn hp__btn--primary" :disabled="loading" @click="loadRecords">
            预览记录
          </button>
        </div>

        <div class="hp__status">{{ status }}</div>

        <div class="hp__list">
          <div v-if="!records.length" class="hp__empty">选择数据表后预览记录</div>
          <div v-for="r in records" :key="r.id" class="hp__item">
            {{ displayValue(r) }}
          </div>
        </div>
      </div>
    `,

    data() {
      return {
        config: {},
        context: null,
        baseId: "",
        tables: [],
        selectedTableId: "",
        fields: [],
        records: [],
        status: "",
        loading: false,
      };
    },

    computed: {
      greeting() {
        return this.config.greeting || "Hello";
      },
    },

    methods: {
      displayValue(record) {
        var values = (record && record.values) || {};
        var v = this.fields.length ? values[this.fields[0].id] : undefined;
        return v === undefined || v === null || v === "" ? "(空)" : String(v);
      },

      async init() {
        try {
          this.config = (await SDK.request("config.get", {})) || {};
        } catch (e) {
          this.config = {};
        }
        try {
          this.context = (await SDK.request("ui.getContext", {})) || {};
          this.baseId = this.context.baseId || "";
        } catch (e) {
          this.context = {};
        }
        await this.loadTables();
      },

      async loadTables() {
        this.loading = true;
        try {
          this.tables = (await SDK.request("table.listTables", {})) || [];
          if (this.tables.length > 0) {
            this.selectedTableId = this.tables[0].id;
            await this.loadRecords();
          } else {
            this.status = "本 Base 暂无数据表";
          }
        } catch (err) {
          this.status = "读取表列表失败：" + ((err && err.message) || err);
        } finally {
          this.loading = false;
        }
      },

      async loadRecords() {
        if (!this.selectedTableId) return;
        this.loading = true;
        this.status = "加载中…";
        try {
          var schema = await SDK.request("table.getSchema", {
            tableId: this.selectedTableId,
          });
          this.fields = (schema && schema.fields) || [];
          var res = await SDK.request("table.getRecords", {
            tableId: this.selectedTableId,
            per_page: 20,
          });
          this.records = (res && res.items) || [];
          this.status = "共 " + (res && res.total != null ? res.total : this.records.length) + " 条，预览前 " + this.records.length + " 条";
        } catch (err) {
          this.records = [];
          this.status = "读取记录失败：" + ((err && err.message) || err);
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
