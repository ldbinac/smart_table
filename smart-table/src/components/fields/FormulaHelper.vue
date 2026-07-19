<template>
  <div class="formula-helper">
    <!-- 搜索框 -->
    <ElInput
      v-model="searchQuery"
      placeholder="搜索公式..."
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
        {{ cat }}
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
                  <ElTag size="small" type="info">{{ formula.category }}</ElTag>
                </div>
                <div class="tooltip-desc">{{ formula.desc }}</div>
                <div class="tooltip-section">
                  <span class="tooltip-label">语法：</span>
                  <code class="tooltip-syntax">{{ formula.syntax }}</code>
                </div>
                <div v-if="formula.params?.length" class="tooltip-section">
                  <span class="tooltip-label">参数：</span>
                  <ul class="tooltip-params">
                    <li v-for="p in formula.params" :key="p.name">
                      <code>{{ p.name }}</code> - {{ p.desc }}
                    </li>
                  </ul>
                </div>
                <div v-if="formula.returns" class="tooltip-section">
                  <span class="tooltip-label">返回值：</span>
                  <span>{{ formula.returns }}</span>
                </div>
                <div v-if="formula.example" class="tooltip-section">
                  <span class="tooltip-label">示例：</span>
                  <code class="tooltip-example">{{ formula.example }}</code>
                </div>
              </div>
            </template>
            <div class="formula-info">
              <div class="formula-header">
                <span class="formula-name">{{ formula.name }}</span>
                <ElTag size="small" type="info">{{ formula.category }}</ElTag>
              </div>
              <div class="formula-desc">{{ formula.desc }}</div>
              <code class="formula-syntax">{{ formula.syntax }}</code>
            </div>
          </ElTooltip>
        </div>
        <ElEmpty
          v-if="filteredFormulas.length === 0"
          description="未找到匹配的公式" />
      </ElScrollbar>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from "vue";
import { Search } from "@element-plus/icons-vue";

interface FormulaInfo {
  name: string;
  desc: string;
  syntax: string;
  category: string;
  params?: Array<{ name: string; desc: string }>;
  returns?: string;
  example?: string;
}

// 公式数据（与后端 formula_service.py 对齐）
const formulas: FormulaInfo[] = [
  // ========== 数学函数 ==========
  {
    name: "SUM",
    desc: "计算所有数值参数的和",
    syntax: "SUM(value1, value2, ...)",
    category: "数学",
    params: [{ name: "value1, value2, ...", desc: "要相加的数值或字段引用，支持任意数量参数" }],
    returns: "数字（求和结果）",
    example: "SUM({单价}, {数量}) 或 SUM(10, 20, 30)",
  },
  {
    name: "AVG",
    desc: "计算所有数值参数的平均值",
    syntax: "AVG(value1, value2, ...)",
    category: "数学",
    params: [{ name: "value1, value2, ...", desc: "要计算平均值的数值，跳过空值" }],
    returns: "数字（平均值）",
    example: "AVG({数学成绩}, {英语成绩}, {语文成绩})",
  },
  {
    name: "MAX",
    desc: "返回一组数值中的最大值",
    syntax: "MAX(value1, value2, ...)",
    category: "数学",
    params: [{ name: "value1, value2, ...", desc: "要比较的数值" }],
    returns: "最大值（数字或其他可比较类型）",
    example: "MAX({一月销量}, {二月销量}, {三月销量})",
  },
  {
    name: "MIN",
    desc: "返回一组数值中的最小值",
    syntax: "MIN(value1, value2, ...)",
    category: "数学",
    params: [{ name: "value1, value2, ...", desc: "要比较的数值" }],
    returns: "最小值",
    example: "MIN({最低温度}, {最高温度})",
  },
  {
    name: "ROUND",
    desc: "将数值四舍五入到指定位数",
    syntax: "ROUND(value, digits)",
    category: "数学",
    params: [
      { name: "value", desc: "要四舍五入的数值" },
      { name: "digits", desc: "保留的小数位数，默认为 0" },
    ],
    returns: "四舍五入后的数字",
    example: "ROUND(3.14159, 2) → 3.14",
  },
  {
    name: "ABS",
    desc: "返回数值的绝对值",
    syntax: "ABS(value)",
    category: "数学",
    params: [{ name: "value", desc: "要取绝对值的数值" }],
    returns: "非负数字",
    example: "ABS(-10) → 10",
  },
  {
    name: "CEILING",
    desc: "向上取整到最接近的整数",
    syntax: "CEILING(value)",
    category: "数学",
    params: [{ name: "value", desc: "要向上取整的数值" }],
    returns: "整数",
    example: "CEILING(3.2) → 4",
  },
  {
    name: "FLOOR",
    desc: "向下取整到最接近的整数",
    syntax: "FLOOR(value)",
    category: "数学",
    params: [{ name: "value", desc: "要向下取整的数值" }],
    returns: "整数",
    example: "FLOOR(3.8) → 3",
  },
  {
    name: "POWER",
    desc: "计算数值的幂次方",
    syntax: "POWER(base, exponent)",
    category: "数学",
    params: [
      { name: "base", desc: "底数" },
      { name: "exponent", desc: "指数" },
    ],
    returns: "数字（base 的 exponent 次方）",
    example: "POWER(2, 3) → 8",
  },
  {
    name: "SQRT",
    desc: "计算数值的平方根",
    syntax: "SQRT(value)",
    category: "数学",
    params: [{ name: "value", desc: "非负数值" }],
    returns: "数字（平方根）",
    example: "SQRT(16) → 4",
  },
  {
    name: "MOD",
    desc: "返回两数相除的余数",
    syntax: "MOD(a, b)",
    category: "数学",
    params: [
      { name: "a", desc: "被除数" },
      { name: "b", desc: "除数" },
    ],
    returns: "数字（余数）",
    example: "MOD(10, 3) → 1",
  },
  {
    name: "LN",
    desc: "计算数值的自然对数（以 e 为底）",
    syntax: "LN(value)",
    category: "数学",
    params: [{ name: "value", desc: "正数" }],
    returns: "数字（自然对数）",
    example: "LN(2.718) → 1",
  },
  {
    name: "LOG",
    desc: "计算数值的对数",
    syntax: "LOG(value, base)",
    category: "数学",
    params: [
      { name: "value", desc: "正数" },
      { name: "base", desc: "对数的底数，默认为 10" },
    ],
    returns: "数字（对数）",
    example: "LOG(100, 10) → 2",
  },
  {
    name: "EXP",
    desc: "计算 e 的指定次幂",
    syntax: "EXP(value)",
    category: "数学",
    params: [{ name: "value", desc: "指数值" }],
    returns: "数字（e^value）",
    example: "EXP(1) → 2.718...",
  },
  {
    name: "PI",
    desc: "返回圆周率 π 的值",
    syntax: "PI()",
    category: "数学",
    params: [],
    returns: "数字（约 3.14159）",
    example: "PI() → 3.14159...",
  },
  {
    name: "E",
    desc: "返回自然常数 e 的值",
    syntax: "E()",
    category: "数学",
    params: [],
    returns: "数字（约 2.71828）",
    example: "E() → 2.71828...",
  },
  {
    name: "RAND",
    desc: "返回 [0, 1) 区间的随机数",
    syntax: "RAND()",
    category: "数学",
    params: [],
    returns: "数字（0 <= x < 1）",
    example: "RAND() → 0.428...",
  },
  {
    name: "RANDBETWEEN",
    desc: "返回指定区间内的随机整数",
    syntax: "RANDBETWEEN(min, max)",
    category: "数学",
    params: [
      { name: "min", desc: "最小值（包含）" },
      { name: "max", desc: "最大值（包含）" },
    ],
    returns: "整数",
    example: "RANDBETWEEN(1, 100) → 42",
  },

  // ========== 文本函数 ==========
  {
    name: "CONCAT",
    desc: "拼接多个文本字符串",
    syntax: "CONCAT(text1, text2, ...)",
    category: "文本",
    params: [{ name: "text1, text2, ...", desc: "要拼接的文本值" }],
    returns: "字符串",
    example: "CONCAT({姓}, {名}) → \"张三\"",
  },
  {
    name: "UPPER",
    desc: "将文本转换为大写",
    syntax: "UPPER(text)",
    category: "文本",
    params: [{ name: "text", desc: "要转换的文本" }],
    returns: "字符串（大写）",
    example: "UPPER(\"hello\") → \"HELLO\"",
  },
  {
    name: "LOWER",
    desc: "将文本转换为小写",
    syntax: "LOWER(text)",
    category: "文本",
    params: [{ name: "text", desc: "要转换的文本" }],
    returns: "字符串（小写）",
    example: "LOWER(\"HELLO\") → \"hello\"",
  },
  {
    name: "LEN",
    desc: "返回文本的字符数",
    syntax: "LEN(text)",
    category: "文本",
    params: [{ name: "text", desc: "要计算长度的文本" }],
    returns: "整数",
    example: "LEN(\"Hello\") → 5",
  },
  {
    name: "TRIM",
    desc: "移除文本首尾的空白字符",
    syntax: "TRIM(text)",
    category: "文本",
    params: [{ name: "text", desc: "要修剪的文本" }],
    returns: "字符串",
    example: "TRIM(\"  hello  \") → \"hello\"",
  },
  {
    name: "LEFT",
    desc: "从文本左侧提取指定数量的字符",
    syntax: "LEFT(text, n)",
    category: "文本",
    params: [
      { name: "text", desc: "源文本" },
      { name: "n", desc: "要提取的字符数" },
    ],
    returns: "字符串",
    example: "LEFT(\"Hello\", 2) → \"He\"",
  },
  {
    name: "RIGHT",
    desc: "从文本右侧提取指定数量的字符",
    syntax: "RIGHT(text, n)",
    category: "文本",
    params: [
      { name: "text", desc: "源文本" },
      { name: "n", desc: "要提取的字符数" },
    ],
    returns: "字符串",
    example: "RIGHT(\"Hello\", 2) → \"lo\"",
  },
  {
    name: "MID",
    desc: "从文本中间提取指定数量的字符",
    syntax: "MID(text, start, length)",
    category: "文本",
    params: [
      { name: "text", desc: "源文本" },
      { name: "start", desc: "起始位置（从 1 开始）" },
      { name: "length", desc: "要提取的字符数" },
    ],
    returns: "字符串",
    example: "MID(\"Hello\", 2, 3) → \"ell\"",
  },
  {
    name: "REPLACE",
    desc: "替换文本中指定位置的字符",
    syntax: "REPLACE(text, start, length, new_text)",
    category: "文本",
    params: [
      { name: "text", desc: "源文本" },
      { name: "start", desc: "起始位置（从 1 开始）" },
      { name: "length", desc: "要替换的字符数" },
      { name: "new_text", desc: "替换文本" },
    ],
    returns: "字符串",
    example: "REPLACE(\"Hello\", 2, 2, \"aa\") → \"Haalo\"",
  },
  {
    name: "SUBSTITUTE",
    desc: "替换文本中的指定子串",
    syntax: "SUBSTITUTE(text, old, new, instance)",
    category: "文本",
    params: [
      { name: "text", desc: "源文本" },
      { name: "old", desc: "要替换的子串" },
      { name: "new", desc: "替换为的文本" },
      { name: "instance", desc: "替换第几次出现（可选，默认全部替换）" },
    ],
    returns: "字符串",
    example: "SUBSTITUTE(\"hello hello\", \"hello\", \"hi\") → \"hi hi\"",
  },
  {
    name: "FIND",
    desc: "查找子串在文本中的位置",
    syntax: "FIND(search_text, text, start)",
    category: "文本",
    params: [
      { name: "search_text", desc: "要查找的子串" },
      { name: "text", desc: "源文本" },
      { name: "start", desc: "起始位置（可选，默认为 1）" },
    ],
    returns: "整数（位置，未找到返回 0）",
    example: "FIND(\"l\", \"Hello\") → 3",
  },
  {
    name: "REPT",
    desc: "重复文本指定次数",
    syntax: "REPT(text, count)",
    category: "文本",
    params: [
      { name: "text", desc: "要重复的文本" },
      { name: "count", desc: "重复次数" },
    ],
    returns: "字符串",
    example: "REPT(\"*\", 5) → \"*****\"",
  },
  {
    name: "TEXT",
    desc: "将数值格式化为文本",
    syntax: "TEXT(value, format)",
    category: "文本",
    params: [
      { name: "value", desc: "要格式化的数值" },
      { name: "format", desc: "格式字符串，如 \"0.00\"、\"#,##0\"" },
    ],
    returns: "字符串",
    example: "TEXT(1234.5, \"#,##0.00\") → \"1,234.50\"",
  },
  {
    name: "VALUE",
    desc: "将文本转换为数值",
    syntax: "VALUE(text)",
    category: "文本",
    params: [{ name: "text", desc: "表示数值的文本" }],
    returns: "数字",
    example: "VALUE(\"123.45\") → 123.45",
  },

  // ========== 日期函数 ==========
  {
    name: "NOW",
    desc: "返回当前日期和时间",
    syntax: "NOW()",
    category: "日期",
    params: [],
    returns: "日期时间",
    example: "NOW() → 2026-07-17 09:30:00",
  },
  {
    name: "TODAY",
    desc: "返回当前日期（不含时间）",
    syntax: "TODAY()",
    category: "日期",
    params: [],
    returns: "日期",
    example: "TODAY() → 2026-07-17",
  },
  {
    name: "YEAR",
    desc: "从日期中提取年份",
    syntax: "YEAR(date)",
    category: "日期",
    params: [{ name: "date", desc: "日期值或字段引用" }],
    returns: "整数（年份）",
    example: "YEAR({创建日期}) → 2026",
  },
  {
    name: "MONTH",
    desc: "从日期中提取月份（1-12）",
    syntax: "MONTH(date)",
    category: "日期",
    params: [{ name: "date", desc: "日期值或字段引用" }],
    returns: "整数（1-12）",
    example: "MONTH({创建日期}) → 7",
  },
  {
    name: "DAY",
    desc: "从日期中提取日（1-31）",
    syntax: "DAY(date)",
    category: "日期",
    params: [{ name: "date", desc: "日期值或字段引用" }],
    returns: "整数（1-31）",
    example: "DAY({创建日期}) → 17",
  },
  {
    name: "HOUR",
    desc: "从日期时间中提取小时（0-23）",
    syntax: "HOUR(datetime)",
    category: "日期",
    params: [{ name: "datetime", desc: "日期时间值" }],
    returns: "整数（0-23）",
    example: "HOUR(NOW()) → 9",
  },
  {
    name: "MINUTE",
    desc: "从日期时间中提取分钟（0-59）",
    syntax: "MINUTE(datetime)",
    category: "日期",
    params: [{ name: "datetime", desc: "日期时间值" }],
    returns: "整数（0-59）",
    example: "MINUTE(NOW()) → 30",
  },
  {
    name: "SECOND",
    desc: "从日期时间中提取秒（0-59）",
    syntax: "SECOND(datetime)",
    category: "日期",
    params: [{ name: "datetime", desc: "日期时间值" }],
    returns: "整数（0-59）",
    example: "SECOND(NOW()) → 45",
  },
  {
    name: "WEEKDAY",
    desc: "返回日期对应的星期几（1=周日，7=周六）",
    syntax: "WEEKDAY(date)",
    category: "日期",
    params: [{ name: "date", desc: "日期值" }],
    returns: "整数（1-7）",
    example: "WEEKDAY(TODAY()) → 6（周五）",
  },
  {
    name: "DATEADD",
    desc: "在日期上添加指定时间单位",
    syntax: "DATEADD(date, amount, unit)",
    category: "日期",
    params: [
      { name: "date", desc: "起始日期" },
      { name: "amount", desc: "要添加的数量（可为负数）" },
      { name: "unit", desc: "时间单位：\"day\"、\"month\"、\"year\"、\"hour\"、\"minute\"、\"second\"" },
    ],
    returns: "日期",
    example: 'DATEADD(TODAY(), 7, "day") → 一周后的日期',
  },
  {
    name: "DATEDIF",
    desc: "计算两个日期之间的差值",
    syntax: "DATEDIF(start, end, unit)",
    category: "日期",
    params: [
      { name: "start", desc: "起始日期" },
      { name: "end", desc: "结束日期" },
      { name: "unit", desc: "时间单位：\"day\"、\"month\"、\"year\"" },
    ],
    returns: "整数（差值）",
    example: 'DATEDIF({开始日期}, {结束日期}, "day") → 天数差',
  },
  {
    name: "DATEDIFF",
    desc: "计算两个日期之间的差值（同 DATEDIF）",
    syntax: "DATEDIFF(start, end, unit)",
    category: "日期",
    params: [
      { name: "start", desc: "起始日期" },
      { name: "end", desc: "结束日期" },
      { name: "unit", desc: "时间单位" },
    ],
    returns: "整数（差值）",
    example: 'DATEDIFF({创建时间}, NOW(), "hour") → 小时差',
  },
  {
    name: "DATETIME_FORMAT",
    desc: "按指定格式格式化日期时间",
    syntax: "DATETIME_FORMAT(date, format)",
    category: "日期",
    params: [
      { name: "date", desc: "日期时间值" },
      { name: "format", desc: "格式字符串，如 \"YYYY-MM-DD HH:mm:ss\"" },
    ],
    returns: "字符串",
    example: 'DATETIME_FORMAT(NOW(), "YYYY年MM月DD日")',
  },
  {
    name: "FROMUNIXTIME",
    desc: "将 Unix 时间戳转换为日期时间",
    syntax: "FROMUNIXTIME(timestamp)",
    category: "日期",
    params: [{ name: "timestamp", desc: "Unix 时间戳（秒）" }],
    returns: "日期时间",
    example: "FROMUNIXTIME(1640995200) → 2021-12-31...",
  },
  {
    name: "UNIXTIMESTAMP",
    desc: "将日期时间转换为 Unix 时间戳",
    syntax: "UNIXTIMESTAMP(date)",
    category: "日期",
    params: [{ name: "date", desc: "日期时间值" }],
    returns: "整数（Unix 时间戳）",
    example: "UNIXTIMESTAMP(NOW()) → 1721187000",
  },

  // ========== 逻辑函数 ==========
  {
    name: "IF",
    desc: "根据条件返回不同的值",
    syntax: "IF(condition, true_value, false_value)",
    category: "逻辑",
    params: [
      { name: "condition", desc: "条件表达式" },
      { name: "true_value", desc: "条件为真时返回的值" },
      { name: "false_value", desc: "条件为假时返回的值" },
    ],
    returns: "根据条件返回对应的值",
    example: 'IF({分数} >= 60, "及格", "不及格")',
  },
  {
    name: "IFS",
    desc: "多条件判断，返回第一个为真的条件对应的值",
    syntax: "IFS(cond1, val1, cond2, val2, ...)",
    category: "逻辑",
    params: [{ name: "cond1, val1, ...", desc: "成对的条件和返回值" }],
    returns: "匹配条件的值",
    example: 'IFS({分数}>=90, "A", {分数}>=80, "B", {分数}>=60, "C", "D")',
  },
  {
    name: "SWITCH",
    desc: "多值匹配，根据表达式值返回对应结果",
    syntax: "SWITCH(expr, val1, res1, val2, res2, ..., DEFAULT, default)",
    category: "逻辑",
    params: [
      { name: "expr", desc: "要匹配的表达式" },
      { name: "val1, res1, ...", desc: "值和结果的成对参数" },
      { name: "DEFAULT, default", desc: "默认结果（可选）" },
    ],
    returns: "匹配的结果",
    example: 'SWITCH({状态}, "待处理", "⏳", "进行中", "🔄", "已完成", "✅", "DEFAULT", "?")',
  },
  {
    name: "AND",
    desc: "逻辑与，所有条件都为真时返回 TRUE",
    syntax: "AND(cond1, cond2, ...)",
    category: "逻辑",
    params: [{ name: "cond1, cond2, ...", desc: "要检查的条件" }],
    returns: "TRUE 或 FALSE",
    example: "AND({分数} >= 60, {出勤率} >= 0.8)",
  },
  {
    name: "OR",
    desc: "逻辑或，任一条件为真时返回 TRUE",
    syntax: "OR(cond1, cond2, ...)",
    category: "逻辑",
    params: [{ name: "cond1, cond2, ...", desc: "要检查的条件" }],
    returns: "TRUE 或 FALSE",
    example: 'OR({等级} = "A", {等级} = "B")',
  },
  {
    name: "NOT",
    desc: "逻辑非，取反条件结果",
    syntax: "NOT(condition)",
    category: "逻辑",
    params: [{ name: "condition", desc: "要取反的条件" }],
    returns: "TRUE 或 FALSE",
    example: "NOT(ISBLANK({备注}))",
  },
  {
    name: "XOR",
    desc: "异或，仅当恰好一个条件为真时返回 TRUE",
    syntax: "XOR(cond1, cond2)",
    category: "逻辑",
    params: [
      { name: "cond1", desc: "第一个条件" },
      { name: "cond2", desc: "第二个条件" },
    ],
    returns: "TRUE 或 FALSE",
    example: "XOR({是否会员}, {是否有优惠})",
  },
  {
    name: "ISBLANK",
    desc: "判断值是否为空",
    syntax: "ISBLANK(value)",
    category: "逻辑",
    params: [{ name: "value", desc: "要检查的值" }],
    returns: "TRUE 或 FALSE",
    example: "ISBLANK({备注})",
  },
  {
    name: "ISERROR",
    desc: "判断值是否为错误",
    syntax: "ISERROR(value)",
    category: "逻辑",
    params: [{ name: "value", desc: "要检查的值" }],
    returns: "TRUE 或 FALSE",
    example: "ISERROR(1/0) → TRUE",
  },
  {
    name: "ISNUMBER",
    desc: "判断值是否为数字",
    syntax: "ISNUMBER(value)",
    category: "逻辑",
    params: [{ name: "value", desc: "要检查的值" }],
    returns: "TRUE 或 FALSE",
    example: "ISNUMBER({年龄})",
  },
  {
    name: "ISTEXT",
    desc: "判断值是否为文本",
    syntax: "ISTEXT(value)",
    category: "逻辑",
    params: [{ name: "value", desc: "要检查的值" }],
    returns: "TRUE 或 FALSE",
    example: "ISTEXT({姓名})",
  },
  {
    name: "ISDATE",
    desc: "判断值是否为日期",
    syntax: "ISDATE(value)",
    category: "逻辑",
    params: [{ name: "value", desc: "要检查的值" }],
    returns: "TRUE 或 FALSE",
    example: "ISDATE({创建时间})",
  },
  {
    name: "BLANK",
    desc: "返回空值",
    syntax: "BLANK()",
    category: "逻辑",
    params: [],
    returns: "NULL",
    example: 'IF({分数} = 0, BLANK(), {分数})',
  },

  // ========== 统计函数 ==========
  {
    name: "COUNT",
    desc: "计算数值参数的个数",
    syntax: "COUNT(value1, value2, ...)",
    category: "统计",
    params: [{ name: "value1, value2, ...", desc: "要计数的数值" }],
    returns: "整数",
    example: "COUNT({成绩1}, {成绩2}, {成绩3})",
  },
  {
    name: "COUNTA",
    desc: "计算非空参数的个数",
    syntax: "COUNTA(value1, value2, ...)",
    category: "统计",
    params: [{ name: "value1, value2, ...", desc: "要计数的值" }],
    returns: "整数",
    example: "COUNTA({字段1}, {字段2}, {字段3})",
  },
  {
    name: "COUNTBLANK",
    desc: "计算空值参数的个数",
    syntax: "COUNTBLANK(value1, value2, ...)",
    category: "统计",
    params: [{ name: "value1, value2, ...", desc: "要检查的值" }],
    returns: "整数",
    example: "COUNTBLANK({字段1}, {字段2}, {字段3})",
  },
  {
    name: "STDEV",
    desc: "计算样本标准差",
    syntax: "STDEV(value1, value2, ...)",
    category: "统计",
    params: [{ name: "value1, value2, ...", desc: "样本数据" }],
    returns: "数字",
    example: "STDEV({成绩1}, {成绩2}, {成绩3})",
  },
  {
    name: "VAR",
    desc: "计算样本方差",
    syntax: "VAR(value1, value2, ...)",
    category: "统计",
    params: [{ name: "value1, value2, ...", desc: "样本数据" }],
    returns: "数字",
    example: "VAR({成绩1}, {成绩2}, {成绩3})",
  },
  {
    name: "MEDIAN",
    desc: "计算中位数",
    syntax: "MEDIAN(value1, value2, ...)",
    category: "统计",
    params: [{ name: "value1, value2, ...", desc: "数值数据" }],
    returns: "数字",
    example: "MEDIAN({成绩1}, {成绩2}, {成绩3})",
  },
  {
    name: "MODE",
    desc: "计算众数（出现次数最多的值）",
    syntax: "MODE(value1, value2, ...)",
    category: "统计",
    params: [{ name: "value1, value2, ...", desc: "数值数据" }],
    returns: "数字",
    example: "MODE(1, 2, 2, 3, 3, 3) → 3",
  },
  {
    name: "RANK",
    desc: "计算数值在一组数值中的排名",
    syntax: "RANK(value, value1, value2, ...)",
    category: "统计",
    params: [
      { name: "value", desc: "要排名的数值" },
      { name: "value1, value2, ...", desc: "用于排名的一组数值" },
    ],
    returns: "整数（排名）",
    example: "RANK({分数}, {分数1}, {分数2}, {分数3})",
  },
  {
    name: "UNIQUE",
    desc: "返回去重后的数组",
    syntax: "UNIQUE(value1, value2, ...)",
    category: "统计",
    params: [{ name: "value1, value2, ...", desc: "要去重的值" }],
    returns: "数组",
    example: "UNIQUE(1, 2, 2, 3, 3) → [1, 2, 3]",
  },
];

const emit = defineEmits<{
  (e: "insert", formula: FormulaInfo): void;
}>();

const searchQuery = ref("");
const selectedCategory = ref("");

const categories = computed(() => {
  const cats = new Set(formulas.map((f) => f.category));
  return Array.from(cats);
});

const filteredFormulas = computed(() => {
  let result = formulas;

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