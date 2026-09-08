/**
 * Hello Panel —— 前端 UI 示例插件（零构建 IIFE 单文件）
 *
 * 宿主 loader.html 会注入全局 `window.SmartTableSDK`：
 *   SmartTableSDK.ready(cb)              握手完成后回调
 *   SmartTableSDK.request(method, params) 发起 RPC 调用（Promise）
 *
 * 勾选数据（表格 → 插件）：
 *   ui.getContext() 返回的 selection 为打开插件瞬间的勾选快照：
 *     { recordIds: string[], total: number, truncated: boolean,
 *       selectAll: boolean, scope: "page" | "view", at: number }
 *   也可单独调用 selection.get()。勾选变化不会实时推送，需重新打开插件。
 *
 * 可用方法取决于 manifest.permissions 声明（未声明的方法宿主侧直接拒绝）：
 *   table.getRecords({ tableId, page, per_page })  需要 records: read
 *   table.getSchema({ tableId })                   需要 tables: read
 *   table.listTables()                             需要 tables: read
 *   record.update({ recordId, values })            需要 records: write
 *   storage.get/set/remove({ key, value })         需要 storage
 *   config.get()                                   隐含授予
 *   ui.notify({ message, type })                   无需声明
 *   ui.getContext()                                无需声明
 *
 * 打包：将本目录的 manifest.json 与本文件一起压缩为 .stplugin.zip 即可上传安装，
 * 无需任何构建工具链。
 */
(function () {
  "use strict";

  var SDK = window.SmartTableSDK;

  if (!SDK) {
    document.body.innerHTML =
      '<div style="padding:24px;color:#F56C6C">' +
      "SmartTableSDK 未就绪：请通过宿主插件管理页安装并启用本插件。</div>";
    return;
  }

  // ---------- 极简 DOM 帮助函数（示例不引入任何框架） ----------
  function h(tag, attrs, children) {
    var el = document.createElement(tag);
    attrs = attrs || {};
    Object.keys(attrs).forEach(function (k) {
      if (k === "style") el.setAttribute("style", attrs[k]);
      else if (k.indexOf("on") === 0) el.addEventListener(k.slice(2), attrs[k]);
      else el.setAttribute(k, attrs[k]);
    });
    (children || []).forEach(function (c) {
      el.appendChild(typeof c === "string" ? document.createTextNode(c) : c);
    });
    return el;
  }

  var state = {
    context: null,
    config: {},
    records: [],
    fields: [],
    selectedFieldId: "",
    fillValue: "",
    loading: false,
    /** 打开插件瞬间的表格勾选快照（宿主注入，仅含记录 ID） */
    selection: null,
  };

  /** 勾选摘要文案（含全选/截断提示） */
  function selectionText() {
    var sel = state.selection;
    var ids = (sel && sel.recordIds) || [];
    var total = (sel && sel.total) || ids.length;
    if (!total) return "未勾选记录：请先在表格中勾选数据后重新打开本插件";
    var tip = sel && sel.selectAll ? "（全选）" : "";
    var trunc =
      sel && sel.truncated ? "，已按上限截断为 " + ids.length + " 条" : "";
    return "已勾选 " + total + " 条记录" + tip + trunc;
  }

  /** 当前勾选的记录 ID 列表 */
  function selectedIds() {
    return ((state.selection && state.selection.recordIds) || []).slice();
  }

  // ---------- 渲染 ----------
  var root = document.getElementById("app") || document.body;
  var statusEl = h("div", { style: "margin:8px 0;color:#909399;font-size:13px;" });
  var listEl = h("div", { style: "display:flex;flex-direction:column;gap:6px;" });

  function render() {
    root.innerHTML = "";
    root.appendChild(
      h("div", { style: "padding:16px;font-family:inherit;" }, [
        h("h3", { style: "margin:0 0 4px;font-size:16px;font-weight:600;" }, [
          (state.config.greeting || "Hello") + "，SmartTable 插件",
        ]),
        h("p", { style: "margin:0 0 12px;color:#909399;font-size:13px;" }, [
          "读取表格勾选的记录，并可将指定字段批量填充为同一值（演示 records: write 权限）。",
        ]),
        h("div", { style: "margin:0 0 10px;color:#409EFF;font-size:13px;" }, [
          selectionText(),
        ]),
        h("div", { style: "display:flex;gap:8px;align-items:center;margin-bottom:10px;" }, [
          h("select", {
            id: "field-select",
            style: "padding:6px 8px;border:1px solid #dcdfe6;border-radius:4px;min-width:160px;",
          }),
          h("input", {
            id: "fill-input",
            placeholder: "要填充的值",
            style: "padding:6px 8px;border:1px solid #dcdfe6;border-radius:4px;flex:1;",
          }),
          h("button", {
            style:
              "padding:6px 14px;background:#409EFF;color:#fff;border:none;border-radius:4px;cursor:pointer;",
            onclick: onFillClick,
          }, ["批量填充"]),
          h("button", {
            style:
              "padding:6px 14px;background:#fff;color:#606266;border:1px solid #dcdfe6;border-radius:4px;cursor:pointer;",
            onclick: loadData,
          }, ["刷新"]),
        ]),
        statusEl,
        listEl,
      ]),
    );

    var select = document.getElementById("field-select");
    if (select) {
      state.fields.forEach(function (f) {
        var opt = document.createElement("option");
        opt.value = f.id;
        opt.textContent = f.name;
        if (f.id === state.selectedFieldId) opt.selected = true;
        select.appendChild(opt);
      });
      select.onchange = function () {
        state.selectedFieldId = select.value;
      };
    }

    var input = document.getElementById("fill-input");
    if (input) {
      input.oninput = function () {
        state.fillValue = input.value;
      };
    }
  }

  function renderRecords() {
    listEl.innerHTML = "";
    if (state.records.length === 0) {
      listEl.appendChild(
        h("div", { style: "color:#909399;font-size:13px;padding:8px 0;" }, ["暂无记录"]),
      );
      return;
    }
    state.records.slice(0, 20).forEach(function (r) {
      var title = String(r.values[state.selectedFieldId] ?? "(空)");
      listEl.appendChild(
        h(
          "div",
          {
            style:
              "padding:8px 10px;border:1px solid #ebeef5;border-radius:4px;font-size:13px;color:#303133;",
          },
          [title],
        ),
      );
    });
  }

  function setStatus(text) {
    statusEl.textContent = text;
  }

  // ---------- 数据加载 ----------
  async function loadData() {
    if (state.loading) return;
    state.loading = true;
    setStatus("加载中…");
    try {
      var ctx = state.context || (await SDK.request("ui.getContext", {}));
      state.context = ctx;
      // 勾选快照：宿主在打开插件瞬间生成，仅含记录 ID
      state.selection = ctx.selection || null;

      var schema = await SDK.request("table.getSchema", { tableId: ctx.tableId });
      state.fields = (schema && schema.fields) || [];
      if (!state.selectedFieldId && state.fields.length > 0) {
        state.selectedFieldId = state.fields[0].id;
      }

      var ids = selectedIds();
      if (ids.length === 0) {
        state.records = [];
        setStatus("未勾选记录：请先在表格中勾选数据后重新打开本插件");
        render();
        renderRecords();
        return;
      }

      // 仅预览前 20 条，避免大量 RPC；填充时处理全部勾选记录
      var preview = ids.slice(0, 20);
      var items = [];
      for (var i = 0; i < preview.length; i++) {
        try {
          var rec = await SDK.request("table.getRecord", { recordId: preview[i] });
          if (rec) items.push(rec);
        } catch (e) {
          /* 单条读取失败忽略 */
        }
      }
      state.records = items;
      setStatus(selectionText());
      render();
      renderRecords();
    } catch (err) {
      setStatus("加载失败：" + ((err && err.message) || err));
    } finally {
      state.loading = false;
    }
  }

  // ---------- 批量填充（演示写权限） ----------
  async function onFillClick() {
    if (!state.selectedFieldId) {
      await SDK.request("ui.notify", { message: "请先选择字段", type: "warning" });
      return;
    }
    if (!state.fillValue) {
      await SDK.request("ui.notify", { message: "请输入要填充的值", type: "warning" });
      return;
    }

    // 对全部勾选记录执行填充（不局限于预览的 20 条）
    var ids = selectedIds();
    if (ids.length === 0) {
      await SDK.request("ui.notify", {
        message: "未勾选记录：请先在表格中勾选数据后重新打开本插件",
        type: "warning",
      });
      return;
    }
    var ok = 0;
    var fail = 0;
    for (var i = 0; i < ids.length; i++) {
      try {
        var values = {};
        values[state.selectedFieldId] = state.fillValue;
        await SDK.request("record.update", { recordId: ids[i], values: values });
        ok++;
      } catch (e) {
        fail++;
      }
    }

    await SDK.request("ui.notify", {
      message: "填充完成：成功 " + ok + " 条，失败 " + fail + " 条",
      type: fail === 0 ? "success" : "warning",
    });

    // 记忆上次使用的字段（storage 权限）
    try {
      await SDK.request("storage.set", { key: "lastFieldId", value: state.selectedFieldId });
    } catch (e) {
      /* storage 未授权时忽略 */
    }

    await loadData();
  }

  // ---------- 启动 ----------
  SDK.ready(async function (sdk) {
    // 读取插件配置（config 权限隐含授予）
    try {
      state.config = (await sdk.request("config.get", {})) || {};
    } catch (e) {
      state.config = {};
    }
    // 恢复上次选择的字段
    try {
      var last = await sdk.request("storage.get", { key: "lastFieldId" });
      if (last) state.selectedFieldId = last;
    } catch (e) {
      /* ignore */
    }
    render();
    await loadData();
  });
})();
