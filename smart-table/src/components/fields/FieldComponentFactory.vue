<script setup lang="ts">
import { computed, ref } from 'vue'
import { FieldType, type FieldOptions, type CellValue } from '@/types/fields'
import TextField from './TextField.vue'
import NumberField from './NumberField.vue'
import DateField from './DateField.vue'
import SingleSelectField from './SingleSelectField.vue'
import MultiSelectField from './MultiSelectField.vue'
import CheckboxField from './CheckboxField.vue'
import AttachmentField from './AttachmentField.vue'
import MemberField from './MemberField.vue'
import RatingField from './RatingField.vue'
import ProgressField from './ProgressField.vue'
import PhoneField from './PhoneField.vue'
import EmailField from './EmailField.vue'
import URLField from './URLField.vue'
import LinkField from './LinkField.vue'
import LookupField from './LookupField.vue'
import CreatedByField from './CreatedByField.vue'
import CreatedTimeField from './CreatedTimeField.vue'
import UpdatedByField from './UpdatedByField.vue'
import UpdatedTimeField from './UpdatedTimeField.vue'
import AutoNumberField from './AutoNumberField.vue'

interface Field {
  id: string
  name: string
  type: string
  options?: FieldOptions
}

interface Props {
  modelValue: CellValue
  field: Field
  readonly?: boolean
  placeholder?: string
}

const props = withDefaults(defineProps<Props>(), {
  readonly: false,
  placeholder: ''
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: CellValue): void
}>()

const componentMap: Record<string, unknown> = {
  [FieldType.TEXT]: TextField,
  [FieldType.NUMBER]: NumberField,
  [FieldType.DATE]: DateField,
  [FieldType.SINGLE_SELECT]: SingleSelectField,
  [FieldType.MULTI_SELECT]: MultiSelectField,
  [FieldType.CHECKBOX]: CheckboxField,
  [FieldType.ATTACHMENT]: AttachmentField,
  [FieldType.MEMBER]: MemberField,
  [FieldType.RATING]: RatingField,
  [FieldType.PROGRESS]: ProgressField,
  [FieldType.PHONE]: PhoneField,
  [FieldType.EMAIL]: EmailField,
  [FieldType.URL]: URLField,
  [FieldType.LINK]: LinkField,
  [FieldType.LOOKUP]: LookupField,
  [FieldType.CREATED_BY]: CreatedByField,
  [FieldType.CREATED_TIME]: CreatedTimeField,
  [FieldType.UPDATED_BY]: UpdatedByField,
  [FieldType.UPDATED_TIME]: UpdatedTimeField,
  [FieldType.AUTO_NUMBER]: AutoNumberField
}

const currentComponent = computed(() => {
  return componentMap[props.field.type] || TextField
})

const isSupported = computed(() => {
  return props.field.type in componentMap
})

const localValue = computed({
  get: () => props.modelValue,
  set: (val: CellValue) => emit('update:modelValue', val)
})

const fieldRef = ref()

const focus = () => {
  fieldRef.value?.focus?.()
}

defineExpose({ focus })
</script>

<template>
  <div class="field-component-factory">
    <template v-if="isSupported">
      <component
        :is="currentComponent"
        v-model="localValue"
        :field="field"
        :readonly="readonly"
        :placeholder="placeholder"
        ref="fieldRef"
      />
    </template>
    <template v-else>
      <div class="unsupported-field">
        <span class="unsupported-text">不支持的字段类型: {{ field.type }}</span>
      </div>
    </template>
  </div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;

.field-component-factory {
  width: 100%;
}

.unsupported-field {
  padding: $spacing-sm;
  background-color: rgba($error-color, 0.1);
  border-radius: $border-radius-sm;
}

.unsupported-text {
  color: $error-color;
  font-size: $font-size-sm;
}
</style>
