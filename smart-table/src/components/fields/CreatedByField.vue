<script setup lang="ts">
import { computed } from 'vue'
import type { FieldEntity } from '@/db/schema'
import type { CellValue } from '@/types'

interface Props {
  modelValue: CellValue
  field: FieldEntity
  readonly?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  readonly: true
})

interface Member {
  id: string
  name: string
  avatar?: string
}

const member = computed<Member | null>(() => {
  if (!props.modelValue) return null
  if (typeof props.modelValue === 'object' && !Array.isArray(props.modelValue)) {
    return props.modelValue as Member
  }
  return null
})

function getInitials(name: string): string {
  return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
}
</script>

<template>
  <div class="created-by-field">
    <div v-if="member" class="member-display">
      <div class="member-avatar">
        <img v-if="member.avatar" :src="member.avatar" :alt="member.name" />
        <span v-else class="avatar-initials">{{ getInitials(member.name) }}</span>
      </div>
      <span class="member-name">{{ member.name }}</span>
    </div>
    <span v-else class="empty-text">-</span>
  </div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;

.created-by-field {
  width: 100%;
}

.member-display {
  display: flex;
  align-items: center;
  gap: $spacing-xs;
}

.member-avatar {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  overflow: hidden;
  background-color: $primary-color;
  display: flex;
  align-items: center;
  justify-content: center;
  
  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
}

.avatar-initials {
  font-size: 10px;
  color: white;
  font-weight: 500;
}

.member-name {
  font-size: $font-size-sm;
  color: $text-primary;
}

.empty-text {
  color: $text-disabled;
}
</style>
