/**
 * Hello Panel —— 前端 UI 示例插件（零构建单文件 + Vue 模板渲染）
 *
 * 运行环境由宿主注入：
 *   window.SmartTableSDK   插件 SDK（握手 + RPC）
 *   window.Vue             Vue3 全局构建（含模板编译器，宿主 loader 从同源 vendor 注入）
 *   #app                   挂载点（loader.html 提供）
 *
 * 本文件无需任何构建工具链，模板以字符串形式书写，可直接与 manifest.json
 * 一起打包为 .stplugin.zip 上传安装。
 *
 * 勾选数据（表格 → 插件）：
 *   ui.getContext() 返回的 selection 为打开插件瞬间的勾选快照：
 *     { recordIds: string[], total: number, truncated: boolean,
 *       selectAll: boolean, scope: "page" | "view", at: number }
 *   也可单独调用 selection.get()。勾选变化不会实时推送，需重新打开插件。
 *
 * 可用 SDK 方法取决于 manifest.permissions 声明（未声明的方法宿主侧直接拒绝）：
 *   table.getRecords({ tableId, page, per_page })  需要 records: read
 *   table.getRecord({ recordId })                  需要 records: read
 *   table.getSchema({ tableId })                   需要 tables: read
 *   table.listTables()                             需要 tables: read
 *   record.update({ recordId, values })            需要 records: write
 *   storage.get/set/remove({ key, value })         需要 storage
 *   config.get()                                   隐含授予
 *   selection.get()                                隐含授予
 *   ui.notify({ message, type }) / ui.getContext() 无需声明
 */
(function () {
  "use strict";

  var SDK = window.SmartTableSDK;
  var Vue = window.Vue;

  if (!SDK) {
    document.body.innerHTML =
      '<div style="padding:24px;color:#F56C6C">' +
      "SmartTableSDK 未就绪：请通过宿主插件管理页安装并启用本插件。</div>";
    return;
  }
  if (!Vue) {
    document.body.innerHTML =
      '<div style="padding:24px;color:#F56C6C">' +
      "Vue 运行时未加载：请确认宿主 loader 已注入 vendor/vue.global.prod.js。</div>";
    return;
  }

  /** 注入样式：零构建下随脚本注入，避免在模板里堆砌内联 style */
  (function injectStyles() {
    var css = [
      ".hp{padding:16px;font-family:inherit;}",
      ".hp__title{margin:0 0 4px;font-size:16px;font-weight:600;}",
      ".hp__desc{margin:0 0 12px;color:#909399;font-size:13px;}",
      ".hp__selection{margin:0 0 10px;color:#409EFF;font-size:13px;}",
      ".hp__toolbar{display:flex;gap:8px;align-items:center;margin-bottom:10px;}",
      ".hp__select,.hp__input{padding:6px 8px;border:1px solid #dcdfe6;border-radius:4px;font-size:13px;}",
      ".hp__select{min-width:160px;}",
      ".hp__input{flex:1;}",
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
        <h3 class="hp__title">{{ greeting }}，SmartTable 插件</h3>
        <p class="hp__desc">
          读取表格勾选的记录，并可将指定字段批量填充为同一值（演示 records: write 权限）。
        </p>
        <div class="hp__selection">{{ selectionText }}</div>

        <div class="hp__toolbar">
          <select class="hp__select" v-model="selectedFieldId">
            <option v-for="f in fields" :key="f.id" :value="f.id">{{ f.name }}</option>
          </select>
          <input
            class="hp__input"
            v-model="fillValue"
            placeholder="要填充的值" />
          <button
            class="hp__btn hp__btn--primary"
            :disabled="loading"
            @click="onFillClick">
            批量填充
          </button>
          <button class="hp__btn" :disabled="loading" @click="loadData">
            刷新
          </button>
        </div>

        <div class="hp__status">{{ status }}</div>

        <div class="hp__list">
          <div v-if="!records.length" class="hp__empty">暂无记录</div>
          <div v-for="r in records" :key="r.id" class="hp__item">
            {{ displayValue(r) }}
          </div>
        </div>
      </div>
    `,

    data() {
      return {
        /** 插件配置（config.get 读取，隐含授予） */
        config: {},
        /** 宿主上下文（含 tableId / selection 等） */
        context: null,
        /** 打开插件瞬间的勾选快照（仅含记录 ID） */
        selection: null,
        /** 表字段列表 */
        fields: [],
        /** 预览记录（最多 20 条） */
        records: [],
        selectedFieldId: "",
        fillValue: "",
        status: "",
        loading: false,
      };
    },

    computed: {
      greeting() {
        return this.config.greeting || "Hello";
      },
      /** 当前勾选的记录 ID 列表 */
      selectedIds() {
        return ((this.selection && this.selection.recordIds) || []).slice();
      },
      /** 勾选摘要文案（含全选/截断提示） */
      selectionText() {
        var sel = this.selection;
        var ids = (sel && sel.recordIds) || [];
        var total = (sel && sel.total) || ids.length;
        if (!total) return "未勾选记录：请先在表格中勾选数据后重新打开本插件";
        var tip = sel && sel.selectAll ? "（全选）" : "";
        var trunc =
          sel && sel.truncated ? "，已按上限截断为 " + ids.length + " 条" : "";
        return "已勾选 " + total + " 条记录" + tip + trunc;
      },
    },

    methods: {
      /** 列表中展示的字段值 */
      displayValue(record) {
        var values = (record && record.values) || {};
        var v = values[this.selectedFieldId];
        return v === undefined || v === null || v === "" ? "(空)" : String(v);
      },

      async init() {
        try {
          this.config = (await SDK.request("config.get", {})) || {};
        } catch (e) {
          this.config = {};
        }
        // 恢复上次选择的字段（storage 未授权时忽略）
        try {
          var last = await SDK.request("storage.get", { key: "lastFieldId" });
          if (last) this.selectedFieldId = last;
        } catch (e) {
          /* ignore */
        }
        await this.loadData();
      },

      async loadData() {
        if (this.loading) return;
        this.loading = true;
        this.status = "加载中…";
        try {
          var ctx = this.context || (await SDK.request("ui.getContext", {}));
          this.context = ctx;
          // 勾选快照：宿主在打开插件瞬间生成，仅含记录 ID
          this.selection = ctx.selection || null;

          var schema = await SDK.request("table.getSchema", {
            tableId: ctx.tableId,
          });
          this.fields = (schema && schema.fields) || [];
          if (!this.selectedFieldId && this.fields.length > 0) {
            this.selectedFieldId = this.fields[0].id;
          }

          var ids = this.selectedIds;
          if (ids.length === 0) {
            this.records = [];
            this.status = "未勾选记录：请先在表格中勾选数据后重新打开本插件";
            return;
          }

          // 仅预览前 20 条，避免大量 RPC；填充时处理全部勾选记录
          var preview = ids.slice(0, 20);
          var items = [];
          for (var i = 0; i < preview.length; i++) {
            try {
              var rec = await SDK.request("table.getRecord", {
                recordId: preview[i],
              });
              if (rec) items.push(rec);
            } catch (e) {
              /* 单条读取失败忽略 */
            }
          }
          this.records = items;
          this.status = this.selectionText;
        } catch (err) {
          this.status = "加载失败：" + ((err && err.message) || err);
        } finally {
          this.loading = false;
        }
      },

      async onFillClick() {
        if (!this.selectedFieldId) {
          await SDK.request("ui.notify", {
            message: "请先选择字段",
            type: "warning",
          });
          return;
        }
        if (!this.fillValue) {
          await SDK.request("ui.notify", {
            message: "请输入要填充的值",
            type: "warning",
          });
          return;
        }

        // 对全部勾选记录执行填充（不局限于预览的 20 条）
        var ids = this.selectedIds;
        if (ids.length === 0) {
          await SDK.request("ui.notify", {
            message: "未勾选记录：请先在表格中勾选数据后重新打开本插件",
            type: "warning",
          });
          return;
        }

        this.loading = true;
        var ok = 0;
        var fail = 0;
        try {
          for (var i = 0; i < ids.length; i++) {
            try {
              var values = {};
              values[this.selectedFieldId] = this.fillValue;
              await SDK.request("record.update", {
                recordId: ids[i],
                values: values,
              });
              ok++;
            } catch (e) {
              fail++;
            }
          }
        } finally {
          this.loading = false;
        }

        await SDK.request("ui.notify", {
          message: "填充完成：成功 " + ok + " 条，失败 " + fail + " 条",
          type: fail === 0 ? "success" : "warning",
        });

        // 记忆上次使用的字段（storage 权限）
        try {
          await SDK.request("storage.set", {
            key: "lastFieldId",
            value: this.selectedFieldId,
          });
        } catch (e) {
          /* storage 未授权时忽略 */
        }

        await this.loadData();
      },
    },

    async mounted() {
      await this.init();
    },
  }).mount("#app");
})();
