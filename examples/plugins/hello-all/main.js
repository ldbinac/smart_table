/**
 * Hello Panel —— 综合示例 UI 插件（零构建多文件 + Vue 模板渲染）
 *
 * 运行环境由宿主 loader 注入：
 *   window.SmartTableSDK   插件 SDK（握手 + RPC + assetUrl）
 *   window.Vue             Vue3 全局构建（含模板编译器，同源 vendor 托管）
 *   window.HPHelpers       本插件 assets.scripts 注入的工具函数（vendor/helpers.js）
 *   #app                   挂载点（loader.html 提供）
 *   <link>                 assets.styles 注入的两份样式（styles/main.css → styles/theme.css）
 *
 * 包结构（见 manifest.json）：
 *   manifest.json / main.js（入口）
 *   vendor/helpers.js        assets.scripts：入口前注入的 JS
 *   styles/main.css          assets.styles[0]：基础样式
 *   styles/theme.css         assets.styles[1]：主题样式（演示按序注入与覆盖）
 *   images/logo.png          运行时资源：经 SDK.assetUrl("images/logo.png") 拿签名 URL
 *   endpoints/echo.py        backend.call("echo")  自定义后端接口
 *   endpoints/stats.py       backend.call("stats") 自定义后端接口
 *
 * 本插件声明了全部 6 类扩展点，入口按 ui.getContext() 返回的上下文自动分支：
 *   home-menu             baseId 为空（全局作用域，无 Base 上下文）
 *   record-detail-block   recordId 存在（记录详情抽屉区块）
 *   toolbar-button / side-panel / base-menu / dashboard-widget
 *                         Base 作用域（dashboard 由仪表盘配置决定 tableId）
 *
 * 作用域能力差异（宿主按上下文注入，插件应优雅降级）：
 *   Base 作用域   全部能力（表格数据 / backend.call / network.fetch / storage…）
 *   记录区块      当前记录 + backend.call / network.fetch / storage
 *   首页菜单      仅 config / storage / ui.notify（backend.call / network.fetch
 *                 需 Base 上下文，宿主会拒绝，本示例在此分支禁用对应入口）
 */
(function () {
  "use strict";

  var SDK = window.SmartTableSDK;
  var Vue = window.Vue;
  var H = window.HPHelpers; // ← assets.scripts 注入（vendor/helpers.js），入口前已就绪

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
  if (!H) {
    // assets.scripts 未注入（异常场景）也能运行，仅失去工具函数
    H = {
      esc: function (s) { return String(s == null ? "" : s); },
      truncate: function (s, n) { return String(s == null ? "" : s).slice(0, n); },
      formatJson: function (v) { try { return JSON.stringify(v, null, 2); } catch (e) { return String(v); } },
      fieldValue: function (r, f) {
        var v = ((r && r.values) || {})[f];
        return v === undefined || v === null || v === "" ? "(空)" : String(v);
      },
    };
  }

  /** 运行时静态资源：SDK.assetUrl 解析包内文件的签名 URL（带 fst 文件令牌） */
  var logoUrl = "";
  try {
    logoUrl = SDK.assetUrl("images/logo.png");
  } catch (e) {
    logoUrl = "";
  }

  Vue.createApp({
    template: `
      <div class="hp">
        <!-- 头部：包内图片（SDK.assetUrl）+ 配置 + 作用域标签 -->
        <div class="hp__head">
          <img v-if="logoUrl && !logoFailed" class="hp__logo" :src="logoUrl"
               @error="logoFailed = true" alt="logo" />
          <span v-else class="hp__logo" style="display:inline-block;background:#ecf5ff"></span>
          <h3 class="hp__title">{{ greeting }}，SmartTable 插件</h3>
          <span class="hp__tag">{{ modeLabel }}</span>
        </div>
        <p class="hp__desc">
          综合示例：多文件 assets、backend.call、network.fetch、storage 与 6 类扩展点。
        </p>

        <!-- ============ 分支 1：首页菜单（全局作用域，无 Base 上下文） ============ -->
        <template v-if="mode === 'home'">
          <div class="hp__card">
            <p class="hp__card-title">全局作用域（home-menu）</p>
            <p>此处没有 Base 上下文，仅可使用 config / storage / ui.notify。</p>
            <button class="hp__btn" :disabled="loading" @click="incVisits">
              storage 计数（当前 {{ visitCount }} 次）
            </button>
            <button class="hp__btn hp__btn--primary" :disabled="true"
                    title="backend.call / network.fetch 需要 Base 上下文，宿主会拒绝">
              backend.call / network.fetch（Base 作用域专属）
            </button>
          </div>
        </template>

        <!-- ============ 分支 2：记录详情区块（record-detail-block） ============ -->
        <template v-else-if="mode === 'record'">
          <div class="hp__card">
            <p class="hp__card-title">当前记录（ui.getContext().recordId）</p>
            <p style="margin:0 0 6px">recordId：{{ context.recordId }}</p>
            <pre class="hp__pre">{{ recordJson }}</pre>
            <button class="hp__btn hp__btn--primary" :disabled="loading" @click="callEcho">
              backend.call("echo", { recordId })
            </button>
          </div>
          <div class="hp__card">
            <p class="hp__card-title">第三方网络（network.fetch）</p>
            <button class="hp__btn" :disabled="loading" @click="fetchGithub">请求 GitHub API</button>
            <pre v-if="netResult" class="hp__pre">{{ netResult }}</pre>
          </div>
        </template>

        <!-- ============ 分支 3：Base 作用域（工具栏 / 侧边面板 / Base 菜单 / 仪表盘） ============ -->
        <template v-else>
          <div class="hp__selection">{{ selectionText }}</div>

          <!-- 勾选填充（toolbar-button / side-panel 的主用例） -->
          <div class="hp__toolbar" v-if="selectionIds.length">
            <select class="hp__select" v-model="selectedFieldId">
              <option v-for="f in fields" :key="f.id" :value="f.id">{{ f.name }}</option>
            </select>
            <input class="hp__input" v-model="fillValue" placeholder="要填充的值" />
            <button class="hp__btn hp__btn--primary" :disabled="loading" @click="onFillClick">
              批量填充
            </button>
            <button class="hp__btn" :disabled="loading" @click="loadBaseData">刷新</button>
          </div>
          <div class="hp__status" v-if="mode === 'base' && !selectionIds.length">
            当前入口无勾选数据：可从表格工具栏勾选记录后打开（快照语义），或在下方使用接口演示。
          </div>

          <div class="hp__list" v-if="records.length">
            <div v-for="r in records" :key="r.id" class="hp__item">
              {{ H.fieldValue(r, selectedFieldId) }}
            </div>
          </div>

          <!-- backend.call 演示：echo / stats（见 endpoints/echo.py、endpoints/stats.py） -->
          <div class="hp__card">
            <p class="hp__card-title">插件自定义后端接口（backend.call → 受限沙箱执行 endpoints/*.py）</p>
            <button class="hp__btn hp__btn--primary" :disabled="loading" @click="callEcho">
              echo：回显参数 + 表数量
            </button>
            <button class="hp__btn" :disabled="loading" @click="callStats">
              stats：统计字段空值分布
            </button>
            <pre v-if="backendResult" class="hp__pre">{{ backendResult }}</pre>
          </div>

          <!-- network.fetch 演示：经宿主代理访问白名单域（permissions.network） -->
          <div class="hp__card">
            <p class="hp__card-title">第三方网络代理（network.fetch → 宿主 /proxy，白名单 api.github.com）</p>
            <button class="hp__btn" :disabled="loading" @click="fetchGithub">请求 GitHub API</button>
            <pre v-if="netResult" class="hp__pre">{{ netResult }}</pre>
          </div>
        </template>
      </div>
    `,

    data() {
      return {
        H: H, // 模板内使用工具函数
        /** 宿主上下文 { pluginId, baseId, tableId, recordId, selection } */
        context: null,
        /** 渲染分支：home / record / base */
        mode: "base",
        /** 插件配置（config.get，隐含授予） */
        config: {},
        /** 包内图片签名 URL（SDK.assetUrl） */
        logoUrl: logoUrl,
        logoFailed: false,

        /** Base 作用域：表字段与勾选记录 */
        fields: [],
        records: [],
        selectedFieldId: "",
        fillValue: "",
        /** 记录区块：当前记录 */
        record: null,
        /** 各接口演示结果 */
        backendResult: "",
        netResult: "",
        visitCount: 0,
        loading: false,
      };
    },

    computed: {
      modeLabel() {
        return {
          home: "home-menu · 全局",
          record: "record-detail-block · 记录",
          base: this.context && this.context.tableId
            ? "表格/仪表盘 · Base"
            : "Base 作用域",
        }[this.mode] || "";
      },
      greeting() {
        return this.config.greeting || "Hello";
      },
      selectionIds() {
        return ((this.context && this.context.selection
          && this.context.selection.recordIds) || []).slice();
      },
      selectionText() {
        var sel = this.context && this.context.selection;
        var ids = (sel && sel.recordIds) || [];
        var total = (sel && sel.total) || ids.length;
        if (!total) return "未勾选记录（该入口不携带勾选数据）";
        var tip = sel.selectAll ? "（全选）" : "";
        var trunc = sel.truncated
          ? "，已按上限截断为 " + ids.length + " 条" : "";
        return "已勾选 " + total + " 条记录" + tip + trunc;
      },
      recordJson() {
        return H.formatJson(this.record || { tip: "加载中…" });
      },
    },

    methods: {
      /** 按宿主上下文自动选择渲染分支（一个插件服务 6 类扩展点的关键） */
      async init() {
        this.context = (await SDK.request("ui.getContext", {})) || {};
        if (!this.context.baseId) {
          this.mode = "home";
        } else if (this.context.recordId) {
          this.mode = "record";
        } else {
          this.mode = "base";
        }
        try {
          this.config = (await SDK.request("config.get", {})) || {};
        } catch (e) {
          this.config = {};
        }
        if (this.mode === "home") {
          await this.loadHome();
        } else if (this.mode === "record") {
          await this.loadRecord();
        } else {
          await this.loadBaseData();
        }
      },

      /** 首页菜单分支：仅 config / storage 能力（优雅降级演示） */
      async loadHome() {
        try {
          var n = await SDK.request("storage.get", { key: "homeVisits" });
          this.visitCount = Number(n) || 0;
        } catch (e) { /* storage 未授权时忽略 */ }
      },

      /** storage 持久化计数（刷新/重开后保留，验证插件自有 KV） */
      async incVisits() {
        this.visitCount += 1;
        try {
          await SDK.request("storage.set", {
            key: "homeVisits",
            value: this.visitCount,
          });
        } catch (e) { /* storage 未授权时忽略 */ }
      },

      /** 记录区块分支：读取当前记录（records:read），recordId 来自宿主上下文 */
      async loadRecord() {
        this.loading = true;
        try {
          this.record = await SDK.request("table.getRecord", {
            recordId: this.context.recordId,
          });
        } catch (err) {
          this.record = { error: (err && err.message) || String(err) };
        } finally {
          this.loading = false;
        }
      },

      /** Base 作用域分支：表结构 + 勾选记录预览（与旧版 hello-panel 一致） */
      async loadBaseData() {
        if (this.loading) return;
        this.loading = true;
        try {
          // 恢复上次使用的字段（storage 权限）
          try {
            var last = await SDK.request("storage.get", { key: "lastFieldId" });
            if (last) this.selectedFieldId = last;
          } catch (e) { /* ignore */ }

          var tableId = this.context.tableId;
          if (!tableId) {
            // 仪表盘组件未配置数据表时跳过表格读取
            this.fields = [];
            this.records = [];
            return;
          }
          var schema = await SDK.request("table.getSchema", { tableId: tableId });
          this.fields = (schema && schema.fields) || [];
          if (!this.selectedFieldId && this.fields.length > 0) {
            this.selectedFieldId = this.fields[0].id;
          }

          // 勾选快照仅含 ID（打开插件瞬间生成），逐条取前 20 条做预览
          var preview = this.selectionIds.slice(0, 20);
          var items = [];
          for (var i = 0; i < preview.length; i++) {
            try {
              var rec = await SDK.request("table.getRecord", {
                recordId: preview[i],
              });
              if (rec) items.push(rec);
            } catch (e) { /* 单条失败忽略 */ }
          }
          this.records = items;
        } catch (err) {
          this.backendResult = "加载失败：" + ((err && err.message) || err);
        } finally {
          this.loading = false;
        }
      },

      /** 批量填充勾选记录（records:write；仅作用于打开瞬间的勾选快照） */
      async onFillClick() {
        if (!this.selectedFieldId || !this.fillValue) {
          await SDK.request("ui.notify", {
            message: "请先选择字段并输入填充值", type: "warning",
          });
          return;
        }
        var ids = this.selectionIds;
        if (!ids.length) {
          await SDK.request("ui.notify", {
            message: "未勾选记录：请先在表格中勾选后重新打开", type: "warning",
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
        try {
          await SDK.request("storage.set", {
            key: "lastFieldId",
            value: this.selectedFieldId,
          });
        } catch (e) { /* storage 未授权时忽略 */ }
        await this.loadBaseData();
      },

      /** backend.call("echo")：演示自定义后端接口与触发者身份注入 */
      async callEcho() {
        this.loading = true;
        this.backendResult = "";
        try {
          var res = await SDK.request("backend.call", {
            name: "echo",
            payload: {
              recordId: this.context.recordId || undefined,
              hello: "world",
              at: new Date().toISOString(),
            },
          });
          // res.result 即 endpoint 内 set_result 的返回值
          this.backendResult = "echo →\n" + H.formatJson(res.result);
        } catch (err) {
          this.backendResult = "echo 失败：" + ((err && err.message) || err);
        } finally {
          this.loading = false;
        }
      },

      /** backend.call("stats")：演示多 endpoint 与服务端聚合 */
      async callStats() {
        this.loading = true;
        this.backendResult = "";
        try {
          var res = await SDK.request("backend.call", {
            name: "stats",
            payload: {
              tableId: this.context.tableId,
              fieldId: this.selectedFieldId,
            },
          });
          this.backendResult = "stats →\n" + H.formatJson(res.result);
        } catch (err) {
          this.backendResult = "stats 失败：" + ((err && err.message) || err);
        } finally {
          this.loading = false;
        }
      },

      /**
       * network.fetch：经宿主代理访问第三方（域须命中 permissions.network 白名单）。
       * 返回 { status, headers, body, body_encoding }；body 为 UTF-8 文本或 base64。
       */
      async fetchGithub() {
        this.loading = true;
        this.netResult = "";
        try {
          var res = await SDK.request("network.fetch", {
            url: "https://api.github.com/repos/ldbinac/smart_table",
            method: "GET",
          });
          var info = { status: res.status, body_encoding: res.body_encoding };
          try {
            var data = JSON.parse(res.body);
            info.repo = data.full_name;
            info.stars = data.stargazers_count;
            info.description = data.description;
          } catch (e) {
            info.body = H.truncate(res.body, 200);
          }
          this.netResult = H.formatJson(info);
        } catch (err) {
          // 白名单外域名 → PERMISSION_DENIED；内网地址 → SSRF_BLOCKED；离线 → 网络错误
          this.netResult = "network.fetch 失败：" + ((err && err.message) || err);
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
