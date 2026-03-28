<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { fieldService } from "@/db/services/fieldService";
import { recordService } from "@/db/services/recordService";
import type { FieldEntity, RecordEntity } from "@/db/schema";
import type { CellValue } from "@/types";

interface Props {
  modelValue: CellValue;
  field: FieldEntity;
  readonly?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  readonly: false,
});

const emit = defineEmits<{
  (e: "update:modelValue", value: CellValue): void;
}>();

const linkedTableId = ref<string>("");
const linkedFieldId = ref<string>("");
const linkedRecords = ref<RecordEntity[]>([]);
const linkedField = ref<FieldEntity | null>(null);

const lookupValue = computed(() => {
  if (!props.modelValue || !linkedField.value) return null;

  const recordIds = Array.isArray(props.modelValue)
    ? props.modelValue
    : [props.modelValue];

  const values = recordIds
    .map((id) => {
      const record = linkedRecords.value.find(
        (r) =>
          r.id === id ||
          r.id === (typeof id === "object" ? (id as { id: string }).id : id),
      );
      return record ? record.values[linkedFieldId.value] : null;
    })
    .filter((v) => v !== null && v !== undefined);

  if (values.length === 0) return null;
  if (values.length === 1) return values[0];
  return values;
});

watch(
  () => props.field.options,
  async (options) => {
    if (options?.linkedTableId) {
      linkedTableId.value = options.linkedTableId as string;
      linkedRecords.value = await recordService.getRecordsByTable(
        linkedTableId.value,
      );
    }
    if (options?.linkedFieldId) {
      linkedFieldId.value = options.linkedFieldId as string;
      if (linkedTableId.value) {
        const fields = await fieldService.getFieldsByTable(linkedTableId.value);
        linkedField.value =
          fields.find((f) => f.id === linkedFieldId.value) || null;
      }
    }
  },
  { immediate: true },
);

function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "-";
  if (Array.isArray(value)) {
    return value.map((v) => formatValue(v as CellValue)).join(", ");
  }
  return String(value);
}
</script>

<template>
  <div class="lookup-field">
    <span class="lookup-value">{{
      formatValue(lookupValue as CellValue)
    }}</span>
  </div>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;

.lookup-field {
  width: 100%;
}

.lookup-value {
  font-size: $font-size-sm;
  color: $text-primary;
}
</style>
