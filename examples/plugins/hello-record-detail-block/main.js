/**
 * Hello Record Detail Block —— 扩展点示例（record-detail-block）
 *
 * 演示：在记录详情抽屉底部挂载一个区块，宿主注入当前记录上下文
 *（ui.getContext().recordId），插件据此读取并展示该记录，并可回写一个字段。
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
      ".hp__row{display:flex;justify-content:space-between;gap:12px;padding:6px 0;border-bottom:1px solid #f2f6fc;font-size:13px;}",
      ".hp__key{color:#909399;}",
      ".hp__val{color:#303133;text-align:right;word-break:break-all;}",
      ".hp__toolbar{margin-top:12px;display:flex;gap:8px;}",
      ".hp__input{padding:6px 8px;border:1px solid #dcdfe6;border-radius:4px;font-size:13px;flex:1;}",
      ".hp__btn{padding:6px 14px;border:1px solid #dcdfe6;border-radius:4px;background:#fff;color:#606266;font-size:13px;cursor:pointer;}",
      ".hp__btn--primary{background:#409EFF;color:#fff;border-color:#409EFF;}",
      ".hp__btn:disabled{opacity:.6;cursor:not-allowed;}",
      ".hp__status{margin:8px 0;color:#909399;font-size:13px;}",
      ".hp__hint{margin:8px 0;color:#E6A23C;font-size:13px;}",
    ].join("\n");
    var style = document.createElement("style");
    style.textContent = css;
    document.head.appendChild(style);
  })();

  Vue.createApp({
    template: `
      <div class="hp">
        <h3 class="hp__title">记录详情区块</h3>
        <p class="hp__desc">
          入口为 record-detail-block：宿主注入当前记录（recordId），插件读取并展示该记录。
        </p>
        <div class="hp__status">{{ status }}</div>

        <div v-if="record">
          <div class="hp__row" v-for="f in fields" :key="f.id">
            <span class="hp__key">{{ f.name }}</span>
            <span class="hp__val">{{ displayValue(f.id) }}</span>
          </div>
        </div>
        <div v-else class="hp__empty">加载中…</div>

        <div class="hp__hint" v-if="!targetField">提示：在插件配置中设置 targetField（字段 ID）后可回写该字段。</div>
        <div class="hp__toolbar" v-if="targetField">
          <input class="hp__input" v-model="writeValue" placeholder="要写入 targetField 的值" />
          <button class="hp__btn hp__btn--primary" :disabled="loading" @click="onWriteClick">
            写入字段
          </button>
        </div>
      </div>
    `,

    data() {
      return {
        config: {},
        context: null,
        recordId: "",
        record: null,
        fields: [],
        targetField: "",
        writeValue: "",
        status: "",
        loading: false,
      };
    },

    methods: {
      displayValue(fieldId) {
        var values = (this.record && this.record.values) || {};
        var v = values[fieldId];
        return v === undefined || v === null || v === "" ? "(空)" : String(v);
      },

      async init() {
        try {
          this.config = (await SDK.request("config.get", {})) || {};
        } catch (e) {
          this.config = {};
        }
        this.targetField = this.config.targetField || "";
        try {
          this.context = (await SDK.request("ui.getContext", {})) || {};
          this.recordId = this.context.recordId || "";
        } catch (e) {
          this.context = {};
        }
        if (!this.recordId) {
          this.status = "未获取到记录 ID（请通过记录详情打开本区块）";
          return;
        }
        await this.loadRecord();
      },

      async loadRecord() {
        this.loading = true;
        this.status = "加载中…";
        try {
          this.record = await SDK.request("table.getRecord", {
            recordId: this.recordId,
          });
          var schema = await SDK.request("table.getSchema", {
            tableId: this.context.tableId,
          });
          this.fields = (schema && schema.fields) || [];
          this.status = "recordId：" + this.recordId;
        } catch (err) {
          this.record = null;
          this.status = "读取记录失败：" + ((err && err.message) || err);
        } finally {
          this.loading = false;
        }
      },

      async onWriteClick() {
        if (!this.targetField) {
          await SDK.request("ui.notify", { message: "请先在插件配置中设置 targetField", type: "warning" });
          return;
        }
        if (this.writeValue === "" || this.writeValue === null) {
          await SDK.request("ui.notify", { message: "请输入要写入的值", type: "warning" });
          return;
        }
        this.loading = true;
        try {
          var values = {};
          values[this.targetField] = this.writeValue;
          await SDK.request("record.update", {
            recordId: this.recordId,
            values: values,
          });
          await SDK.request("ui.notify", { message: "已写入字段", type: "success" });
          try {
            await SDK.request("storage.set", { key: "lastRecordId", value: this.recordId });
          } catch (e) { /* ignore */ }
          await this.loadRecord();
        } catch (err) {
          await SDK.request("ui.notify", { message: "写入失败：" + ((err && err.message) || err), type: "error" });
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
