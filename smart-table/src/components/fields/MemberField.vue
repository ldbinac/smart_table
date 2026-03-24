<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import type { FieldEntity } from '@/db/schema'
import type { CellValue } from '@/types'

interface Member {
  id: string
  name: string
  avatar?: string
}

interface Props {
  modelValue: CellValue
  field: FieldEntity
  readonly?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  readonly: false
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: CellValue): void
}>()

const selectedMembers = ref<Member[]>([])
const searchQuery = ref('')
const visible = ref(false)

const members = computed<Member[]>(() => {
  return (props.field.options?.members as Member[]) || []
})

const allowMultiple = computed(() => {
  return props.field.options?.allowMultiple !== false
})

const filteredMembers = computed(() => {
  if (!searchQuery.value) return members.value
  const query = searchQuery.value.toLowerCase()
  return members.value.filter(m => 
    m.name.toLowerCase().includes(query)
  )
})

watch(() => props.modelValue, (newVal) => {
  if (Array.isArray(newVal)) {
    selectedMembers.value = newVal as Member[]
  } else if (newVal) {
    const member = members.value.find(m => m.id === newVal)
    selectedMembers.value = member ? [member] : []
  } else {
    selectedMembers.value = []
  }
}, { immediate: true })

function isSelected(member: Member): boolean {
  return selectedMembers.value.some(m => m.id === member.id)
}

function toggleMember(member: Member) {
  if (props.readonly) return
  
  if (allowMultiple.value) {
    if (isSelected(member)) {
      selectedMembers.value = selectedMembers.value.filter(m => m.id !== member.id)
    } else {
      selectedMembers.value.push(member)
    }
    emit('update:modelValue', selectedMembers.value)
  } else {
    selectedMembers.value = [member]
    emit('update:modelValue', member.id)
    visible.value = false
  }
}

function removeMember(memberId: string) {
  selectedMembers.value = selectedMembers.value.filter(m => m.id !== memberId)
  emit('update:modelValue', selectedMembers.value)
}

function getInitials(name: string): string {
  return name.split(' ').map(n => n[0]).join('').toUpperCase().slice(0, 2)
}
</script>

<template>
  <div class="member-field">
    <div v-if="readonly" class="member-display">
      <div
        v-for="member in selectedMembers"
        :key="member.id"
        class="member-tag"
      >
        <div class="member-avatar">
          <img v-if="member.avatar" :src="member.avatar" :alt="member.name" />
          <span v-else class="avatar-initials">{{ getInitials(member.name) }}</span>
        </div>
        <span class="member-name">{{ member.name }}</span>
      </div>
      <span v-if="selectedMembers.length === 0" class="empty-text">-</span>
    </div>
    
    <el-popover
      v-else
      v-model:visible="visible"
      trigger="click"
      placement="bottom-start"
      :width="280"
    >
      <template #reference>
        <div class="member-trigger">
          <div
            v-for="member in selectedMembers"
            :key="member.id"
            class="member-tag"
          >
            <div class="member-avatar">
              <img v-if="member.avatar" :src="member.avatar" :alt="member.name" />
              <span v-else class="avatar-initials">{{ getInitials(member.name) }}</span>
            </div>
            <span class="member-name">{{ member.name }}</span>
            <el-icon class="remove-icon" @click.stop="removeMember(member.id)">
              <Close />
            </el-icon>
          </div>
          <span v-if="selectedMembers.length === 0" class="placeholder">
            选择成员
          </span>
        </div>
      </template>
      
      <div class="member-dropdown">
        <el-input
          v-model="searchQuery"
          placeholder="搜索成员"
          prefix-icon="Search"
          size="small"
          clearable
        />
        
        <div class="member-list">
          <div
            v-for="member in filteredMembers"
            :key="member.id"
            class="member-option"
            :class="{ selected: isSelected(member) }"
            @click="toggleMember(member)"
          >
            <div class="member-avatar">
              <img v-if="member.avatar" :src="member.avatar" :alt="member.name" />
              <span v-else class="avatar-initials">{{ getInitials(member.name) }}</span>
            </div>
            <span class="member-name">{{ member.name }}</span>
            <el-icon v-if="isSelected(member)" class="check-icon">
              <Check />
            </el-icon>
          </div>
          
          <div v-if="filteredMembers.length === 0" class="no-results">
            未找到成员
          </div>
        </div>
      </div>
    </el-popover>
  </div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;

.member-field {
  width: 100%;
}

.member-display {
  display: flex;
  flex-wrap: wrap;
  gap: $spacing-xs;
}

.member-trigger {
  display: flex;
  flex-wrap: wrap;
  gap: $spacing-xs;
  min-height: 32px;
  padding: $spacing-xs;
  border: 1px solid $border-color;
  border-radius: $border-radius-sm;
  cursor: pointer;
  
  &:hover {
    border-color: $primary-color;
  }
}

.member-tag {
  display: inline-flex;
  align-items: center;
  gap: $spacing-xs;
  padding: 2px 8px;
  background-color: $bg-color;
  border-radius: $border-radius-sm;
  font-size: $font-size-sm;
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
  color: $text-primary;
}

.remove-icon {
  font-size: 12px;
  color: $text-secondary;
  cursor: pointer;
  
  &:hover {
    color: $error-color;
  }
}

.placeholder {
  color: $text-disabled;
  font-size: $font-size-sm;
}

.empty-text {
  color: $text-disabled;
}

.member-dropdown {
  display: flex;
  flex-direction: column;
  gap: $spacing-sm;
}

.member-list {
  max-height: 200px;
  overflow-y: auto;
}

.member-option {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
  padding: $spacing-sm;
  border-radius: $border-radius-sm;
  cursor: pointer;
  
  &:hover {
    background-color: $bg-color;
  }
  
  &.selected {
    background-color: rgba($primary-color, 0.1);
  }
}

.check-icon {
  margin-left: auto;
  color: $primary-color;
}

.no-results {
  padding: $spacing-md;
  text-align: center;
  color: $text-disabled;
  font-size: $font-size-sm;
}
</style>
