<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { ElMessage } from "element-plus";
import { useTableStore } from "@/stores/tableStore";
import { fieldService } from "@/db/services/fieldService";
import { lookupApiService } from "@/services/api/lookupApiService";
import type { FieldEntity } from "@/db/schema";
import type {
  LookupFieldConfig,
  LookupAggregationType,
} from "@/types/fields";
import { getLookupAggregationTypeLabel } from "@/types/fields";
import LookupConditionEditor from "./LookupConditionEditor.vue";

interface Props {
  /** 字段对象（包含 name、type、config） */
  field: {
    id?: string;
    name: string;
    type: string;
    config?: LookupFieldConfig;
  };
  /** 当前表 ID */
  tableId: string;
  /** 当前 base ID（可选，用于过滤同库表） */
  baseId?: string;
  /** 当前表字段列表（用于过滤条件的 valueFieldId 选择） */
  currentTableFields?: FieldEntity[];
  /** 当前记录 ID（用于配置预览） */
  recordId?: string;
}

const props = defineProps<Props>();

const emit = defineEmits<{
  (e: "update:field", value: { name: string; config: LookupFieldConfig }): void;
}>();

const tableStore = useTableStore();

// ==================== 内部状态 ====================

// 字段名称
const fieldName = ref<string>(props.field.name);

// 查找字段配置
const config = ref<LookupFieldConfig>({
  sourceTableId: "",
  targetFieldId: "",
  filterConditions: [],
  filterConjunction: "and",
  aggregationType: "original",
  fieldFormat: {
    type: "number",
    precision: 0,
    currencySymbol: "¥",
    dateFormat: "YYYY-MM-DD",
  },
  ...(props.field.config || {}),
});

// 源表字段列表
const sourceTableFields = ref<FieldEntity[]>([]);

// 预览结果
const previewValue = ref<unknown>(null);
const previewLoading = ref(false);

// ==================== 计算属性 ====================

/** 可选的源数据表列表（同库其他表） */
const availableTables = computed(() => {
  return tableStore.tables.filter((t) => t.id !== props.tableId);
});

/** 计算方式选项 */
const aggregationTypeOptions: LookupAggregationType[] = [
  "original",
  "distinct",
  "distinct_count",
  "sum",
  "count",
  "avg",
  "max",
  "min",
];

/** 是否为原值/去重（格式自动跟随源字段） */
const isOriginalOrDistinct = computed(() =>
  ["original", "distinct"].includes(config.value.aggregationType),
);

/** 是否为数字类聚合（distinct_count/sum/count/avg） */
const isNumberAggregation = computed(() =>
  ["distinct_count", "sum", "count", "avg"].includes(
    config.value.aggregationType,
  ),
);

/** 是否为 max/min 且源字段为日期类型 */
const isMaxMinWithDate = computed(() => {
  if (!["max", "min"].includes(config.value.aggregationType)) return false;
  const targetField = sourceTableFields.value.find(
    (f) => f.id === config.value.targetFieldId,
  );
  return !!targetField && ["date", "date_time"].includes(targetField.type);
});

/** 是否需要字段格式配置 */
const needsFieldFormat = computed(() => !isOriginalOrDistinct.value);

/** 是否可以预览 */
const canPreview = computed(
  () =>
    !!props.field.id &&
    !!props.recordId &&
    !!config.value.sourceTableId &&
    !!config.value.targetFieldId,
);

// ==================== 事件触发 ====================

function emitUpdate() {
  emit("update:field", {
    name: fieldName.value,
    config: { ...config.value },
  });
}

// ==================== 数据加载 ====================

async function loadSourceTableFields() {
  if (!config.value.sourceTableId) {
    sourceTableFields.value = [];
    return;
  }
  try {
    sourceTableFields.value = await fieldService.getFieldsByTable(
      config.value.sourceTableId,
    );
  } catch (e) {
    console.error("[LookupFieldConfigPanel] 加载源表字段失败:", e);
    sourceTableFields.value = [];
  }
}

// ==================== 交互处理 ====================

/** 源表变更：清空引用字段与过滤条件，并重新加载字段列表 */
async function onSourceTableChange() {
  config.value.targetFieldId = "";
  config.value.filterConditions = [];
  await loadSourceTableFields();
  emitUpdate();
}

/** 计算方式变更：根据新方式重置 fieldFormat */
function onAggregationTypeChange() {
  if (isOriginalOrDistinct.value) {
    // original/distinct 不需要 fieldFormat
  } else if (isNumberAggregation.value) {
    config.value.fieldFormat.type = "number";
  } else if (isMaxMinWithDate.value) {
    // 保留当前选择或默认 number
    if (
      !["number", "currency", "date"].includes(config.value.fieldFormat.type)
    ) {
      config.value.fieldFormat.type = "number";
    }
  } else {
    // max/min 但非日期
    config.value.fieldFormat.type = "number";
  }
  emitUpdate();
}

/** 预览查找结果 */
async function handlePreview() {
  if (!props.field.id) {
    ElMessage.warning("字段尚未保存，无法预览");
    return;
  }
  if (!props.recordId) {
    ElMessage.warning("需要记录 ID 才能预览");
    return;
  }

  previewLoading.value = true;
  try {
    const result = await lookupApiService.previewLookupValue(props.field.id, {
      record_id: props.recordId,
      config: config.value,
    });
    previewValue.value = result.value;
  } catch (e) {
    ElMessage.error("预览失败：" + (e instanceof Error ? e.message : "未知错误"));
    previewValue.value = null;
  } finally {
    previewLoading.value = false;
  }
}

/** 格式化预览值用于展示 */
function formatPreviewValue(value: unknown): string {
  if (value === null || value === undefined) return "-";
  if (Array.isArray(value)) {
    if (value.length === 0) return "-";
    return value.map((v) => String(v)).join(", ");
  }
  return String(value);
}

// ==================== 初始化 ====================

// 初始化加载源表字段（编辑已有字段时）
watch(
  () => config.value.sourceTableId,
  (newId) => {
    if (newId && sourceTableFields.value.length === 0) {
      loadSourceTableFields();
    }
  },
  { immediate: true },
);
</script>

<template>
  <div class="lookup-config-panel">
    <ElForm label-width="100px" label-position="right">
      <!-- 1. 字段名称 -->
      <ElFormItem label="字段名称" required>
        <ElInput
          v-model="fieldName"
          placeholder="请输入字段名称"
          @input="emitUpdate"
        />
      </ElFormItem>

      <!-- 2. 源数据表 -->
      <ElFormItem label="源数据表" required>
        <ElSelect
          v-model="config.sourceTableId"
          placeholder="选择要查找的数据表"
          style="width: 100%"
          @change="onSourceTableChange"
        >
          <ElOption
            v-for="table in availableTables"
            :key="table.id"
            :label="table.name"
            :value="table.id"
          />
        </ElSelect>
        <div class="field-hint">选择要查找数据的数据表（限同库其他表）</div>
      </ElFormItem>

      <!-- 3. 引用字段 -->
      <ElFormItem label="引用字段" required>
        <ElSelect
          v-model="config.targetFieldId"
          placeholder="选择要引用的字段"
          style="width: 100%"
          :disabled="!config.sourceTableId"
          @change="emitUpdate"
        >
          <ElOption
            v-for="field in sourceTableFields"
            :key="field.id"
            :label="field.name"
            :value="field.id"
          />
        </ElSelect>
        <div class="field-hint">
          选择源数据表中要引用的字段（包含隐藏字段）
        </div>
      </ElFormItem>

      <!-- 4. 过滤条件 -->
      <ElFormItem label="过滤条件">
        <LookupConditionEditor
          v-model:conditions="config.filterConditions"
          v-model:conjunction="config.filterConjunction"
          :source-table-fields="sourceTableFields"
          :current-table-fields="currentTableFields || []"
          @update:conditions="emitUpdate"
          @update:conjunction="emitUpdate"
        />
        <div class="field-hint">最多 5 个条件，留空则返回源表所有记录</div>
      </ElFormItem>

      <!-- 5. 计算方式 -->
      <ElFormItem label="计算方式" required>
        <ElSelect
          v-model="config.aggregationType"
          style="width: 100%"
          @change="onAggregationTypeChange"
        >
          <ElOption
            v-for="type in aggregationTypeOptions"
            :key="type"
            :label="getLookupAggregationTypeLabel(type)"
            :value="type"
          />
        </ElSelect>
        <div class="field-hint">选择如何聚合查找结果</div>
      </ElFormItem>

      <!-- 6. 字段格式 -->
      <ElFormItem v-if="needsFieldFormat" label="字段格式" required>
        <!-- original/distinct：提示自动跟随源字段 -->
        <div v-if="isOriginalOrDistinct" class="format-hint">
          格式自动跟随源字段，不可修改
        </div>

        <!-- distinct_count/sum/count/avg：number/currency 二选一 -->
        <ElRadioGroup
          v-else-if="isNumberAggregation"
          v-model="config.fieldFormat.type"
          @change="emitUpdate"
        >
          <ElRadioButton value="number">数字</ElRadioButton>
          <ElRadioButton value="currency">货币</ElRadioButton>
        </ElRadioGroup>

        <!-- max/min 且源字段为日期类型：可选 date -->
        <ElRadioGroup
          v-else-if="isMaxMinWithDate"
          v-model="config.fieldFormat.type"
          @change="emitUpdate"
        >
          <ElRadioButton value="number">数字</ElRadioButton>
          <ElRadioButton value="currency">货币</ElRadioButton>
          <ElRadioButton value="date">日期</ElRadioButton>
        </ElRadioGroup>
      </ElFormItem>

      <!-- 7. 数字格式：小数位数 -->
      <ElFormItem v-if="config.fieldFormat.type === 'number'" label="小数位数">
        <ElInputNumber
          v-model="config.fieldFormat.precision"
          :min="0"
          :max="10"
          @change="emitUpdate"
        />
      </ElFormItem>

      <!-- 8. 货币格式配置 -->
      <template v-if="config.fieldFormat.type === 'currency'">
        <ElFormItem label="货币符号">
          <ElInput
            v-model="config.fieldFormat.currencySymbol"
            placeholder="如 ¥、$、€"
            @input="emitUpdate"
          />
        </ElFormItem>
        <ElFormItem label="小数位数">
          <ElInputNumber
            v-model="config.fieldFormat.precision"
            :min="0"
            :max="10"
            @change="emitUpdate"
          />
        </ElFormItem>
      </template>

      <!-- 9. 日期格式配置 -->
      <ElFormItem v-if="config.fieldFormat.type === 'date'" label="日期格式">
        <ElSelect
          v-model="config.fieldFormat.dateFormat"
          @change="emitUpdate"
        >
          <ElOption label="YYYY-MM-DD" value="YYYY-MM-DD" />
          <ElOption label="YYYY/MM/DD" value="YYYY/MM/DD" />
          <ElOption label="YYYY年MM月DD日" value="YYYY年MM月DD日" />
          <ElOption label="YYYY-MM-DD HH:mm:ss" value="YYYY-MM-DD HH:mm:ss" />
        </ElSelect>
      </ElFormItem>

      <!-- 10. 预览结果 -->
      <ElFormItem>
        <ElButton
          type="primary"
          plain
          :loading="previewLoading"
          :disabled="!canPreview"
          @click="handlePreview"
        >
          预览结果
        </ElButton>
        <div v-if="previewValue !== null" class="preview-result">
          <span class="preview-label">预览值：</span>
          <span class="preview-value">{{ formatPreviewValue(previewValue) }}</span>
        </div>
      </ElFormItem>
    </ElForm>
  </div>
</template>

<style lang="scss" scoped>
.lookup-config-panel {
  width: 100%;
}

.field-hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  margin-top: 4px;
}

.format-hint {
  color: var(--el-text-color-secondary);
  font-size: 13px;
  font-style: italic;
}

.preview-result {
  margin-top: 8px;
  padding: 8px 12px;
  background: var(--el-fill-color-light);
  border-radius: 4px;

  .preview-label {
    color: var(--el-text-color-secondary);
    margin-right: 8px;
  }

  .preview-value {
    color: var(--el-text-color-primary);
    font-weight: 500;
  }
}
</style>
