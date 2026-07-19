<script setup lang="ts">
import { computed } from "vue";
import type { RecordEntity, FieldEntity } from "@/db/schema";
import FieldComponentFactory from "@/components/fields/FieldComponentFactory.vue";
import { FieldType } from "@/types";
import { FormulaEngine } from "@/utils/formula/engine";
import { formatDate, formatDateTime } from "@/utils/timezone";
import { useTableStore } from "@/stores/tableStore";

interface Props {
  record: RecordEntity;
  fields: FieldEntity[];
}

const props = defineProps<Props>();
const emit = defineEmits<{
  (e: "edit"): void;
  (e: "delete"): void;
}>();

// 获取表格所有字段（包括隐藏字段，用于公式计算）
const tableStore = useTableStore();
const allFields = computed(() => tableStore.fields);

const primaryField = computed(() => {
  return props.fields.find((f) => f.isPrimary) || props.fields[0];
});

const primaryValue = computed(() => {
  if (!primaryField.value) return "";
  const value = props.record.values[primaryField.value.id];
  
  // 处理单选字段，显示选项名称而不是 ID
  if (primaryField.value.type === 'single_select' && primaryField.value.options?.choices) {
    const options = (primaryField.value.options.choices as any[]) || [];
    const selectedOption = options.find((opt: any) => opt.id === value);
    return selectedOption?.name || value || "";
  }
  
  return value || "";
});

// 计算公式字段值
const formulaValues = computed(() => {
  const values: Record<string, string | number | null> = {};
  const formulaFields = props.fields.filter(f => f.type === FieldType.FORMULA);
  
  if (formulaFields.length === 0) return values;
  
  // 使用所有字段（包括隐藏字段）构建公式引擎
  const engine = new FormulaEngine(allFields.value);
  
  for (const field of formulaFields) {
    const formula = field.options?.formula as string;
    
    if (!formula) {
      values[field.id] = null;
      continue;
    }
    
    try {
      const result = engine.calculate(props.record, formula);
      
      if (typeof result === "number") {
        // 根据公式类型决定格式化方式
        const resultType = FormulaEngine.inferResultType(formula);
        // 日期时间类型：YYYY-MM-DD HH:mm:ss
        if (resultType === "datetime") {
          values[field.id] = formatDateTime(result);
        }
        // 日期类型：YYYY-MM-DD
        else if (resultType === "date") {
          values[field.id] = formatDate(result);
        }
        // 数字类型：带精度格式化
        else {
          const precision = (field.options?.precision as number) ?? 2;
          values[field.id] = result.toLocaleString("zh-CN", {
            minimumFractionDigits: precision,
            maximumFractionDigits: precision,
          });
        }
      } else if (result === "#ERROR") {
        values[field.id] = "计算错误";
      } else {
        values[field.id] = result as string | null;
      }
    } catch (e) {
      console.error('[KanbanCard] 公式计算错误:', e);
      values[field.id] = "计算错误";
    }
  }
  
  return values;
});

// 获取字段显示值（优先使用公式计算值）
const getFieldValue = (field: FieldEntity) => {
  if (field.type === FieldType.FORMULA) {
    return formulaValues.value[field.id] ?? null;
  }
  return props.record.values[field.id];
};

// 处理卡片点击（非操作区域）
function handleCardClick(event: MouseEvent) {
  // 检查点击目标是否在操作区域内
  const target = event.target as HTMLElement;
  const actionsArea = target.closest(".card-actions");
  if (actionsArea) {
    // 点击的是操作区域，不触发编辑
    return;
  }
  emit("edit");
}
</script>

<template>
  <div class="kanban-card" @click="handleCardClick">
    <div class="card-header">
      <span class="card-title">
        {{ primaryValue || "无标题" }}
      </span>
      <div class="card-actions" @click.stop>
        <el-dropdown trigger="click">
          <button class="card-menu-btn">
            <el-icon><MoreFilled /></el-icon>
          </button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="$emit('edit')">
                <el-icon><Edit /></el-icon>
                编辑
              </el-dropdown-item>
              <el-dropdown-item divided @click="$emit('delete')">
                <el-icon><Delete /></el-icon>
                删除
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>

    <div class="card-fields">
      <div
        v-for="field in fields.filter((f) => !f.isPrimary)"
        :key="field.id"
        class="card-field">
        <span class="field-label">{{ field.name }}</span>
        <div class="field-value">
          <FieldComponentFactory
            :model-value="getFieldValue(field)"
            :field="field"
            :readonly="true"
            :record="record"
            :all-fields="allFields" />
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;

.kanban-card {
  padding: $spacing-md;
  margin-bottom: $spacing-md;
  background-color: $surface-color;
  border: 1px solid transparent;
  border-radius: $border-radius-xl;
  box-shadow: $shadow-sm;
  cursor: pointer;
  transition: all 0.25s $ease-out-cubic;

  &:hover {
    border-color: rgba($primary-color, 0.2);
    box-shadow: $shadow-lg;
    transform: translateY(-2px);

    .card-menu-btn {
      opacity: 1;
      transform: scale(1);
    }
  }

  &:active {
    transform: translateY(0);
    box-shadow: $shadow-md;
  }
}

.card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: $spacing-sm;
  margin-bottom: $spacing-sm;
}

.card-title {
  flex: 1;
  font-weight: 600;
  font-size: $font-size-base;
  color: $text-primary;
  line-height: 1.5;
  word-break: break-word;
}

.card-menu-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  padding: 0;
  color: $text-secondary;
  background-color: transparent;
  border: none;
  border-radius: $border-radius-md;
  cursor: pointer;
  opacity: 0;
  transform: scale(0.9);
  transition: all 0.2s $ease-out-cubic;

  &:hover {
    color: $primary-color;
    background-color: $gray-100;
  }
}

.card-actions {
  display: flex;
  align-items: center;
  gap: $spacing-xs;
  flex-shrink: 0;
}

.card-fields {
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
}

.card-field {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.field-label {
  font-size: $font-size-xs;
  font-weight: 500;
  color: $text-secondary;
}

.field-value {
  font-size: $font-size-sm;
  color: $text-primary;
  line-height: 1.4;
}

// 拖拽时的卡片样式
:global(.kanban-card-drag) .kanban-card,
:global(.kanban-card-chosen) .kanban-card {
  box-shadow: $shadow-xl;
}
</style>
