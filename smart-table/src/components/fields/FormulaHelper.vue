<template>
  <div class="formula-helper">
    <!-- 搜索框 -->
    <ElInput
      v-model="searchQuery"
      :placeholder="t('formula.searchPlaceholder')"
      clearable
      class="search-input">
      <template #prefix>
        <ElIcon><Search /></ElIcon>
      </template>
    </ElInput>

    <!-- 分类筛选 -->
    <div class="category-tabs">
      <ElTag
        v-for="cat in categories"
        :key="cat"
        :type="selectedCategory === cat ? 'primary' : 'info'"
        :effect="selectedCategory === cat ? 'dark' : 'plain'"
        class="category-tag"
        @click="selectedCategory = selectedCategory === cat ? '' : cat">
        {{ t(`formula.cat.${cat}`) }}
      </ElTag>
    </div>

    <!-- 公式列表 -->
    <div class="formula-list">
      <ElScrollbar height="300px">
        <div
          v-for="formula in filteredFormulas"
          :key="formula.name"
          class="formula-item"
          @click="insertFormula(formula)">
          <ElTooltip
            :show-after="300"
            placement="right"
            :hide-after="0"
            effect="light"
            popper-class="formula-tooltip">
            <template #content>
              <div class="tooltip-content">
                <div class="tooltip-header">
                  <span class="tooltip-name">{{ formula.name }}</span>
                  <ElTag size="small" type="info">{{ t(`formula.cat.${formula.category}`) }}</ElTag>
                </div>
                <div class="tooltip-desc">{{ formula.desc }}</div>
                <div class="tooltip-section">
                  <span class="tooltip-label">{{ t('formula.syntaxLabel') }}</span>
                  <code class="tooltip-syntax">{{ formula.syntax }}</code>
                </div>
                <div v-if="formula.params?.length" class="tooltip-section">
                  <span class="tooltip-label">{{ t('formula.paramsLabel') }}</span>
                  <ul class="tooltip-params">
                    <li v-for="p in formula.params" :key="p.name">
                      <code>{{ p.name }}</code> - {{ p.desc }}
                    </li>
                  </ul>
                </div>
                <div v-if="formula.returns" class="tooltip-section">
                  <span class="tooltip-label">{{ t('formula.returnsLabel') }}</span>
                  <span>{{ formula.returns }}</span>
                </div>
                <div v-if="formula.example" class="tooltip-section">
                  <span class="tooltip-label">{{ t('formula.exampleLabel') }}</span>
                  <code class="tooltip-example">{{ formula.example }}</code>
                </div>
              </div>
            </template>
            <div class="formula-info">
              <div class="formula-header">
                <span class="formula-name">{{ formula.name }}</span>
                <ElTag size="small" type="info">{{ t(`formula.cat.${formula.category}`) }}</ElTag>
              </div>
              <div class="formula-desc">{{ formula.desc }}</div>
              <code class="formula-syntax">{{ formula.syntax }}</code>
            </div>
          </ElTooltip>
        </div>
        <ElEmpty
          v-if="filteredFormulas.length === 0"
          :description="t('formula.noMatch')" />
      </ElScrollbar>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
import { useI18n } from "vue-i18n";
import { Search } from "@element-plus/icons-vue";
import { getLiteral } from "@/i18n";

const { t } = useI18n();

interface FormulaInfo {
  name: string;
  desc: string;
  syntax: string;
  category: string;
  params?: Array<{ name: string; desc: string }>;
  returns?: string;
  example?: string;
}

// 公式静态骨架（name/syntax/category/参数名），描述文本从 i18n 读取
// 与后端 formula_service.py 对齐
const FUNCS: Array<{ name: string; syntax: string; category: string; params: string[] }> = [
  // ========== 数学函数 ==========
  { name: "SUM", syntax: "SUM(value1, value2, ...)", category: "math", params: ["value1, value2, ..."] },
  { name: "AVG", syntax: "AVG(value1, value2, ...)", category: "math", params: ["value1, value2, ..."] },
  { name: "MAX", syntax: "MAX(value1, value2, ...)", category: "math", params: ["value1, value2, ..."] },
  { name: "MIN", syntax: "MIN(value1, value2, ...)", category: "math", params: ["value1, value2, ..."] },
  { name: "ROUND", syntax: "ROUND(value, digits)", category: "math", params: ["value", "digits"] },
  { name: "ABS", syntax: "ABS(value)", category: "math", params: ["value"] },
  { name: "CEILING", syntax: "CEILING(value)", category: "math", params: ["value"] },
  { name: "FLOOR", syntax: "FLOOR(value)", category: "math", params: ["value"] },
  { name: "POWER", syntax: "POWER(base, exponent)", category: "math", params: ["base", "exponent"] },
  { name: "SQRT", syntax: "SQRT(value)", category: "math", params: ["value"] },
  { name: "MOD", syntax: "MOD(a, b)", category: "math", params: ["a", "b"] },
  { name: "LN", syntax: "LN(value)", category: "math", params: ["value"] },
  { name: "LOG", syntax: "LOG(value, base)", category: "math", params: ["value", "base"] },
  { name: "EXP", syntax: "EXP(value)", category: "math", params: ["value"] },
  { name: "PI", syntax: "PI()", category: "math", params: [] },
  { name: "E", syntax: "E()", category: "math", params: [] },
  { name: "RAND", syntax: "RAND()", category: "math", params: [] },
  { name: "RANDBETWEEN", syntax: "RANDBETWEEN(min, max)", category: "math", params: ["min", "max"] },
  // ========== 文本函数 ==========
  { name: "CONCAT", syntax: "CONCAT(text1, text2, ...)", category: "text", params: ["text1, text2, ..."] },
  { name: "UPPER", syntax: "UPPER(text)", category: "text", params: ["text"] },
  { name: "LOWER", syntax: "LOWER(text)", category: "text", params: ["text"] },
  { name: "LEN", syntax: "LEN(text)", category: "text", params: ["text"] },
  { name: "TRIM", syntax: "TRIM(text)", category: "text", params: ["text"] },
  { name: "LEFT", syntax: "LEFT(text, n)", category: "text", params: ["text", "n"] },
  { name: "RIGHT", syntax: "RIGHT(text, n)", category: "text", params: ["text", "n"] },
  { name: "MID", syntax: "MID(text, start, length)", category: "text", params: ["text", "start", "length"] },
  { name: "REPLACE", syntax: "REPLACE(text, start, length, new_text)", category: "text", params: ["text", "start", "length", "new_text"] },
  { name: "SUBSTITUTE", syntax: "SUBSTITUTE(text, old, new, instance)", category: "text", params: ["text", "old", "new", "instance"] },
  { name: "FIND", syntax: "FIND(search_text, text, start)", category: "text", params: ["search_text", "text", "start"] },
  { name: "REPT", syntax: "REPT(text, count)", category: "text", params: ["text", "count"] },
  { name: "TEXT", syntax: "TEXT(value, format)", category: "text", params: ["value", "format"] },
  { name: "VALUE", syntax: "VALUE(text)", category: "text", params: ["text"] },
  // ========== 日期函数 ==========
  { name: "NOW", syntax: "NOW()", category: "date", params: [] },
  { name: "TODAY", syntax: "TODAY()", category: "date", params: [] },
  { name: "YEAR", syntax: "YEAR(date)", category: "date", params: ["date"] },
  { name: "MONTH", syntax: "MONTH(date)", category: "date", params: ["date"] },
  { name: "DAY", syntax: "DAY(date)", category: "date", params: ["date"] },
  { name: "HOUR", syntax: "HOUR(datetime)", category: "date", params: ["datetime"] },
  { name: "MINUTE", syntax: "MINUTE(datetime)", category: "date", params: ["datetime"] },
  { name: "SECOND", syntax: "SECOND(datetime)", category: "date", params: ["datetime"] },
  { name: "WEEKDAY", syntax: "WEEKDAY(date)", category: "date", params: ["date"] },
  { name: "DATEADD", syntax: "DATEADD(date, amount, unit)", category: "date", params: ["date", "amount", "unit"] },
  { name: "DATEDIF", syntax: "DATEDIF(start, end, unit)", category: "date", params: ["start", "end", "unit"] },
  { name: "DATEDIFF", syntax: "DATEDIFF(start, end, unit)", category: "date", params: ["start", "end", "unit"] },
  { name: "DATETIME_FORMAT", syntax: "DATETIME_FORMAT(date, format)", category: "date", params: ["date", "format"] },
  { name: "FROMUNIXTIME", syntax: "FROMUNIXTIME(timestamp)", category: "date", params: ["timestamp"] },
  { name: "UNIXTIMESTAMP", syntax: "UNIXTIMESTAMP(date)", category: "date", params: ["date"] },
  // ========== 逻辑函数 ==========
  { name: "IF", syntax: "IF(condition, true_value, false_value)", category: "logic", params: ["condition", "true_value", "false_value"] },
  { name: "IFS", syntax: "IFS(cond1, val1, cond2, val2, ...)", category: "logic", params: ["cond1, val1, ..."] },
  { name: "SWITCH", syntax: "SWITCH(expr, val1, res1, val2, res2, ..., DEFAULT, default)", category: "logic", params: ["expr", "val1, res1, ...", "DEFAULT, default"] },
  { name: "AND", syntax: "AND(cond1, cond2, ...)", category: "logic", params: ["cond1, cond2, ..."] },
  { name: "OR", syntax: "OR(cond1, cond2, ...)", category: "logic", params: ["cond1, cond2, ..."] },
  { name: "NOT", syntax: "NOT(condition)", category: "logic", params: ["condition"] },
  { name: "XOR", syntax: "XOR(cond1, cond2)", category: "logic", params: ["cond1", "cond2"] },
  { name: "ISBLANK", syntax: "ISBLANK(value)", category: "logic", params: ["value"] },
  { name: "ISERROR", syntax: "ISERROR(value)", category: "logic", params: ["value"] },
  { name: "ISNUMBER", syntax: "ISNUMBER(value)", category: "logic", params: ["value"] },
  { name: "ISTEXT", syntax: "ISTEXT(value)", category: "logic", params: ["value"] },
  { name: "ISDATE", syntax: "ISDATE(value)", category: "logic", params: ["value"] },
  { name: "BLANK", syntax: "BLANK()", category: "logic", params: [] },
  // ========== 统计函数 ==========
  { name: "COUNT", syntax: "COUNT(value1, value2, ...)", category: "stats", params: ["value1, value2, ..."] },
  { name: "COUNTA", syntax: "COUNTA(value1, value2, ...)", category: "stats", params: ["value1, value2, ..."] },
  { name: "COUNTBLANK", syntax: "COUNTBLANK(value1, value2, ...)", category: "stats", params: ["value1, value2, ..."] },
  { name: "STDEV", syntax: "STDEV(value1, value2, ...)", category: "stats", params: ["value1, value2, ..."] },
  { name: "VAR", syntax: "VAR(value1, value2, ...)", category: "stats", params: ["value1, value2, ..."] },
  { name: "MEDIAN", syntax: "MEDIAN(value1, value2, ...)", category: "stats", params: ["value1, value2, ..."] },
  { name: "MODE", syntax: "MODE(value1, value2, ...)", category: "stats", params: ["value1, value2, ..."] },
  { name: "RANK", syntax: "RANK(value, value1, value2, ...)", category: "stats", params: ["value", "value1, value2, ..."] },
  { name: "UNIQUE", syntax: "UNIQUE(value1, value2, ...)", category: "stats", params: ["value1, value2, ..."] },
];

// 公式数据：描述文本从 i18n 读取，支持语言切换
const formulas = computed<FormulaInfo[]>(() =>
  FUNCS.map((f) => ({
    name: f.name,
    desc: t(`formula.f.${f.name}.desc`),
    syntax: f.syntax,
    category: f.category,
    params: f.params.map((pname, idx) => ({
      name: pname,
      desc: t(`formula.f.${f.name}.p${idx}`),
    })),
    returns: t(`formula.f.${f.name}.returns`),
    example: getLiteral(`formula.f.${f.name}.example`),
  })),
);

const emit = defineEmits<{
  (e: "insert", formula: FormulaInfo): void;
}>();

const searchQuery = ref("");
const selectedCategory = ref("");

const categories = computed(() => {
  const cats = new Set(formulas.value.map((f) => f.category));
  return Array.from(cats);
});

const filteredFormulas = computed(() => {
  let result = formulas.value;

  // 按分类筛选
  if (selectedCategory.value) {
    result = result.filter((f) => f.category === selectedCategory.value);
  }

  // 按搜索词筛选
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase();
    result = result.filter(
      (f) =>
        f.name.toLowerCase().includes(query) ||
        f.desc.toLowerCase().includes(query) ||
        f.syntax.toLowerCase().includes(query)
    );
  }

  return result;
});

function insertFormula(formula: FormulaInfo) {
  emit("insert", formula);
}
</script>

<style scoped>
.formula-helper {
  padding: 12px;
}

.search-input {
  margin-bottom: 12px;
}

.category-tabs {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 12px;
}

.category-tag {
  cursor: pointer;
  user-select: none;
}

.formula-list {
  border: 1px solid var(--el-border-color-light);
  border-radius: 4px;
}

.formula-item {
  padding: 10px 12px;
  border-bottom: 1px solid var(--el-border-color-lighter);
  cursor: pointer;
  transition: background-color 0.2s;
}

.formula-item:last-child {
  border-bottom: none;
}

.formula-item:hover {
  background-color: var(--el-fill-color-light);
}

.formula-info {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.formula-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.formula-name {
  font-weight: 600;
  font-family: "SF Mono", Monaco, "Cascadia Code", monospace;
  color: var(--el-color-primary);
}

.formula-desc {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}

.formula-syntax {
  font-size: 12px;
  background: var(--el-fill-color-light);
  padding: 2px 6px;
  border-radius: 3px;
  font-family: "SF Mono", Monaco, "Cascadia Code", monospace;
}
</style>

<style>
/* 全局样式：提示框 */
.formula-tooltip {
  max-width: 400px !important;
}

.tooltip-content {
  display: flex;
  flex-direction: column;
  gap: 8px;
  font-size: 13px;
}

.tooltip-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.tooltip-name {
  font-weight: 600;
  font-size: 15px;
  font-family: "SF Mono", Monaco, "Cascadia Code", monospace;
  color: var(--el-color-primary);
}

.tooltip-desc {
  color: var(--el-text-color-primary);
}

.tooltip-section {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.tooltip-label {
  font-weight: 500;
  color: var(--el-text-color-secondary);
}

.tooltip-syntax,
.tooltip-example {
  background: var(--el-fill-color-light);
  padding: 4px 8px;
  border-radius: 4px;
  font-family: "SF Mono", Monaco, "Cascadia Code", monospace;
  font-size: 12px;
}

.tooltip-params {
  margin: 0;
  padding-left: 16px;
  font-size: 12px;
}

.tooltip-params li {
  margin: 2px 0;
}

.tooltip-params code {
  background: var(--el-fill-color);
  padding: 1px 4px;
  border-radius: 2px;
  font-family: "SF Mono", Monaco, "Cascadia Code", monospace;
}
</style>
