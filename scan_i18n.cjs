const fs = require("fs");
const path = require("path");

const SRC = path.resolve(__dirname, "smart-table/src");
const LOCALES = ["zh-CN", "en-US"];

// Collect source files
function walk(dir, exts, out) {
  const entries = fs.readdirSync(dir, { withFileTypes: true });
  for (const e of entries) {
    const full = path.join(dir, e.name);
    if (e.isDirectory()) {
      if (["node_modules", "dist", "locales"].includes(e.name)) continue;
      walk(full, exts, out);
    } else if (exts.includes(path.extname(e.name))) {
      out.push(full);
    }
  }
}

const files = [];
walk(SRC, [".vue", ".ts", ".js", ".tsx", ".jsx"], files);

// Extract t('...') / $t('...') / t("...") / t(`...`) calls (static only)
const keyRe = /(?:\$t|\bt)\s*\(\s*(['"`])((?:\\\1|(?!\1).)*)\1/g;
const collected = {}; // namespace -> Set(fullKey)
const usages = []; // {file, key, line}

function resolvePath(obj, parts) {
  let cur = obj;
  for (const p of parts) {
    if (cur == null || typeof cur !== "object" || !(p in cur)) return undefined;
    cur = cur[p];
  }
  return cur;
}

for (const f of files) {
  const content = fs.readFileSync(f, "utf8");
  const lines = content.split("\n");
  let m;
  keyRe.lastIndex = 0;
  while ((m = keyRe.exec(content)) !== null) {
    const raw = m[2];
    if (raw.includes("${")) continue; // dynamic -> skip
    if (!raw.includes(".")) continue; // needs namespace
    const ns = raw.split(".")[0];
    if (!collected[ns]) collected[ns] = new Set();
    collected[ns].add(raw);
    // find line
    const idx = m.index;
    const before = content.slice(0, idx);
    const line = before.split("\n").length;
    usages.push({ file: path.relative(SRC, f), key: raw, line });
  }
}

// Load locale files per namespace
const localeData = {}; // locale -> ns -> json
const nsFileSets = {}; // locale -> Set(ns)
for (const loc of LOCALES) {
  localeData[loc] = {};
  nsFileSets[loc] = new Set();
  const dir = path.join(SRC, "i18n/locales", loc);
  if (!fs.existsSync(dir)) continue;
  for (const fn of fs.readdirSync(dir)) {
    if (!fn.endsWith(".json")) continue;
    const ns = fn.replace(/\.json$/, "");
    nsFileSets[loc].add(ns);
    try {
      localeData[loc][ns] = JSON.parse(fs.readFileSync(path.join(dir, fn), "utf8"));
    } catch (e) {
      console.error("JSON parse error", loc, fn, e.message);
    }
  }
}

// Build missing report
const missing = {}; // ns -> { loc -> [keys] }
for (const ns of Object.keys(collected)) {
  for (const loc of LOCALES) {
    if (!nsFileSets[loc].has(ns)) {
      // namespace file completely missing in this locale
      if (!missing[ns]) missing[ns] = {};
      if (!missing[ns][loc]) missing[ns][loc] = [];
      for (const k of collected[ns]) missing[ns][loc].push(k + "  (NAMESPACE FILE MISSING)");
      continue;
    }
    const json = localeData[loc][ns];
    for (const k of collected[ns]) {
      const parts = k.split(".");
      const val = resolvePath(json, parts.slice(1));
      if (val === undefined) {
        if (!missing[ns]) missing[ns] = {};
        if (!missing[ns][loc]) missing[ns][loc] = [];
        missing[ns][loc].push(k);
      }
    }
  }
}

// Output
let totalMissing = 0;
for (const ns of Object.keys(missing).sort()) {
  for (const loc of LOCALES) {
    if (missing[ns][loc]) {
      console.log(`\n==== ${ns} [${loc}] missing (${missing[ns][loc].length}) ====`);
      for (const k of missing[ns][loc].sort()) console.log("  " + k);
      totalMissing += missing[ns][loc].length;
    }
  }
}
console.log(`\nTOTAL missing entries: ${totalMissing}`);
console.log(`Distinct namespaces referenced: ${Object.keys(collected).length}`);
console.log(`Namespaces: ${Object.keys(collected).sort().join(", ")}`);

// Save detailed report
fs.writeFileSync(
  path.resolve(__dirname, "i18n_missing_report.json"),
  JSON.stringify({ missing, namespaces: Object.keys(collected).sort() }, null, 2)
);
console.log("Report saved to i18n_missing_report.json");
