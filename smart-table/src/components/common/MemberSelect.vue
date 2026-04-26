<script setup lang="ts">
import { ref, watch, nextTick, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Close, Check, Loading, CircleClose } from '@element-plus/icons-vue'
import { useDebounceFn } from '@vueuse/core'
import { userApi } from '@/api/user'
import { useUserCacheStore } from '@/stores/userCacheStore'
import type { User } from '@/api/types'

export interface Member {
  id: string
  name: string
  email: string
  avatar?: string
}

interface Props {
  // 支持两种模式：ID 模式（向后兼容）和对象模式
  modelValue: string | string[] | Member | Member[] | null
  placeholder?: string
  disabled?: boolean
  allowMultiple?: boolean
  baseId?: string
  // 是否返回完整对象而不是仅ID
  returnObject?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  placeholder: '选择成员',
  disabled: false,
  allowMultiple: false,
  returnObject: false,
})

const emit = defineEmits<{
  (e: 'update:modelValue', value: string | string[] | Member | Member[] | null): void
}>()

// 用户缓存存储
const userCacheStore = useUserCacheStore()

// 选中的成员
const selectedMembers = ref<Member[]>([])
// 搜索关键词
const searchQuery = ref('')
// 下拉框显示状态
const dropdownVisible = ref(false)
// 加载状态
const loading = ref(false)
// 搜索结果
const searchResults = ref<Member[]>([])
// 是否已加载初始数据
const initialLoaded = ref(false)
// 用于防止循环更新的标志
const isUpdating = ref(false)

// 将 User 转换为 Member
function userToMember(user: User): Member {
  return {
    id: user.id,
    name: user.name,
    email: user.email,
    avatar: user.avatar,
  }
}

// 根据ID获取成员信息（使用缓存）
async function fetchMemberById(id: string): Promise<Member | null> {
  // 使用缓存存储获取用户信息
  const cachedUser = await userCacheStore.fetchUser(id)
  if (cachedUser) {
    return {
      id: cachedUser.id,
      name: cachedUser.name,
      email: cachedUser.email,
      avatar: cachedUser.avatar,
    }
  }
  return null
}

// 搜索成员 - 仅在输入关键词时调用
async function searchMembers(query: string): Promise<Member[]> {
  // 如果没有输入查询内容，返回空数组，不调用接口
  if (!query.trim()) {
    return []
  }

  loading.value = true
  try {
    const response = await userApi.searchUsers({
      query: query.trim(),
      base_id: props.baseId,
      per_page: 20,
    })
    return response.users.map(userToMember)
  } catch (error) {
    console.error('[MemberSelect] 搜索用户失败:', error)
    ElMessage.error('搜索用户失败')
    return []
  } finally {
    loading.value = false
  }
}

// 防抖搜索
const debouncedSearch = useDebounceFn(async (query: string) => {
  searchResults.value = await searchMembers(query)
}, 300)

// 监听搜索关键词变化
watch(searchQuery, (newQuery) => {
  debouncedSearch(newQuery)
})

// 监听下拉框显示状态
watch(dropdownVisible, async (visible) => {
  if (visible && !initialLoaded.value) {
    // 首次打开时，清空搜索和结果，等待用户输入
    searchQuery.value = ''
    searchResults.value = []
    initialLoaded.value = true

    // 聚焦搜索框
    await nextTick()
    const inputEl = document.querySelector('.member-select-popover .el-input__inner') as HTMLInputElement
    if (inputEl) {
      inputEl.focus()
    }
  }
})

// 从 modelValue 提取成员ID列表
function extractMemberIds(): string[] {
  if (!props.modelValue) return []

  if (props.returnObject) {
    // 对象模式
    if (Array.isArray(props.modelValue)) {
      return (props.modelValue as Member[]).map(m => m.id)
    } else {
      return [(props.modelValue as Member).id]
    }
  } else {
    // ID 模式
    if (Array.isArray(props.modelValue)) {
      return props.modelValue as string[]
    } else {
      return [props.modelValue as string]
    }
  }
}

// 加载选中成员信息
async function loadSelectedMembers() {
  // 如果正在更新，避免重复执行
  if (isUpdating.value) return

  const ids = extractMemberIds()

  // 如果没有ID，清空选中成员
  if (ids.length === 0) {
    selectedMembers.value = []
    return
  }

  // 检查是否已经有相同的成员，避免不必要的更新
  const currentIds = selectedMembers.value.map(m => m.id)
  if (JSON.stringify(currentIds.sort()) === JSON.stringify(ids.sort())) {
    return
  }

  // 过滤掉特殊值
  const validIds = ids.filter(id => id !== 'current_user' && id)
  
  if (validIds.length === 0) {
    selectedMembers.value = []
    return
  }

  // 使用批量获取接口（带缓存）
  const cachedUsers = await userCacheStore.fetchUsers(validIds)
  
  const members: Member[] = cachedUsers.map(user => ({
    id: user.id,
    name: user.name,
    email: user.email,
    avatar: user.avatar,
  }))

  selectedMembers.value = members
}

// 组件挂载时加载选中成员
onMounted(() => {
  loadSelectedMembers()
})

// 监听modelValue变化，更新选中的成员
// 使用 { flush: 'post' } 确保在父组件更新后执行，避免循环
watch(() => props.modelValue, () => {
  loadSelectedMembers()
}, { flush: 'post' })

// 判断是否已选中
function isSelected(memberId: string): boolean {
  return selectedMembers.value.some(m => m.id === memberId)
}

// 发出更新事件
// 统一返回数组格式，与后端存储格式保持一致
function emitUpdate(members: Member[]) {
  // 设置更新标志，防止循环
  isUpdating.value = true

  if (props.returnObject) {
    // 返回对象数组
    emit('update:modelValue', members.length > 0 ? members : [])
  } else {
    // 返回ID数组
    emit('update:modelValue', members.length > 0 ? members.map(m => m.id) : [])
  }

  // 延迟重置更新标志
  setTimeout(() => {
    isUpdating.value = false
  }, 0)
}

// 选择/取消选择成员
function toggleMember(member: Member) {
  if (props.disabled) return

  if (props.allowMultiple) {
    // 多选模式
    if (isSelected(member.id)) {
      selectedMembers.value = selectedMembers.value.filter(m => m.id !== member.id)
    } else {
      selectedMembers.value.push(member)
    }
    emitUpdate(selectedMembers.value)
  } else {
    // 单选模式
    if (isSelected(member.id)) {
      selectedMembers.value = []
      emitUpdate([])
    } else {
      selectedMembers.value = [member]
      emitUpdate([member])
    }
    dropdownVisible.value = false
  }
}

// 移除已选成员
function removeMember(memberId: string, event?: Event) {
  event?.stopPropagation()
  if (props.disabled) return

  selectedMembers.value = selectedMembers.value.filter(m => m.id !== memberId)
  emitUpdate(selectedMembers.value)
}

// 清空所有选择
// 统一返回空数组，与后端存储格式保持一致
function clearAll(event?: Event) {
  event?.stopPropagation()
  if (props.disabled) return

  selectedMembers.value = []
  emit('update:modelValue', [])
}

// 获取姓名首字母
function getInitials(name: string | undefined): string {
  if (!name) return '?'
  return name
    .split(' ')
    .map(n => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)
}

// 生成头像背景色
function getAvatarColor(name: string | undefined): string {
  const colors = ['#2d7cfc', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899']
  if (!name) return colors[0]
  let hash = 0
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash)
  }
  return colors[Math.abs(hash) % colors.length]
}
</script>

<template>
  <div class="member-select">
    <el-popover
      v-model:visible="dropdownVisible"
      trigger="click"
      placement="bottom-start"
      :width="320"
      popper-class="member-select-popover"
      :teleported="true"
      :persistent="false"
    >
      <template #reference>
        <div
          class="member-select-trigger"
          :class="{ 'is-disabled': disabled, 'is-multiple': allowMultiple }"
        >
          <!-- 已选成员标签 -->
          <template v-if="selectedMembers.length > 0">
            <div
              v-for="member in selectedMembers"
              :key="member.id"
              class="member-tag"
            >
              <div
                class="member-avatar"
                :style="{ backgroundColor: getAvatarColor(member.name) }"
              >
                <img v-if="member.avatar" :src="member.avatar" :alt="member.name" />
                <span v-else class="avatar-initials">{{ getInitials(member.name) }}</span>
              </div>
              <span class="member-name">{{ member.name }}</span>
              <el-icon
                v-if="!disabled"
                class="remove-icon"
                @click.stop="removeMember(member.id, $event)"
              >
                <Close />
              </el-icon>
            </div>
          </template>

          <!-- 占位符 -->
          <span v-else class="placeholder">{{ placeholder }}</span>

          <!-- 清空按钮（多选且有选中时显示） -->
          <el-icon
            v-if="allowMultiple && selectedMembers.length > 0 && !disabled"
            class="clear-all-icon"
            @click.stop="clearAll($event)"
          >
            <CircleClose />
          </el-icon>
        </div>
      </template>

      <!-- 下拉框内容 -->
      <div class="member-dropdown" @click.stop>
        <!-- 搜索框 -->
        <div class="search-box">
          <el-input
            v-model="searchQuery"
            placeholder="输入姓名或邮箱搜索"
            :prefix-icon="Search"
            size="default"
            clearable
          />
        </div>

        <!-- 加载状态 -->
        <div v-if="loading" class="loading-state">
          <el-icon class="loading-icon"><Loading /></el-icon>
          <span>搜索中...</span>
        </div>

        <!-- 成员列表 -->
        <div v-else class="member-list">
          <div
            v-for="member in searchResults"
            :key="member.id"
            class="member-option"
            :class="{ 'is-selected': isSelected(member.id) }"
            @click.stop="toggleMember(member)"
          >
            <div
              class="member-avatar"
              :style="{ backgroundColor: getAvatarColor(member.name) }"
            >
              <img v-if="member.avatar" :src="member.avatar" :alt="member.name" />
              <span v-else class="avatar-initials">{{ getInitials(member.name) }}</span>
            </div>
            <div class="member-info">
              <div class="member-name">{{ member.name }}</div>
              <div class="member-email">{{ member.email }}</div>
            </div>
            <el-icon v-if="isSelected(member.id)" class="check-icon">
              <Check />
            </el-icon>
          </div>

          <!-- 空结果提示 -->
          <div v-if="searchResults.length === 0 && !loading" class="empty-state">
            <el-icon><Search /></el-icon>
            <span v-if="searchQuery.trim()">未找到匹配的成员</span>
            <span v-else>请输入关键词搜索</span>
          </div>
        </div>
      </div>
    </el-popover>
  </div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;

.member-select {
  width: 100%;
}

.member-select-trigger {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: $spacing-xs;
  min-height: 32px;
  padding: 4px 8px;
  border: 1px solid $border-color;
  border-radius: $border-radius-sm;
  background-color: white;
  cursor: pointer;
  transition: all 0.2s;

  &:hover:not(.is-disabled) {
    border-color: $primary-color;
  }

  &.is-disabled {
    background-color: $gray-100;
    cursor: not-allowed;
  }

  &.is-multiple {
    padding-right: 28px;
  }
}

.member-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 2px 8px;
  background-color: $gray-100;
  border-radius: $border-radius-sm;
  font-size: $font-size-sm;
  transition: background-color 0.2s;

  &:hover {
    background-color: $gray-200;
  }
}

.member-avatar {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;

  img {
    width: 100%;
    height: 100%;
    object-fit: cover;
  }
}

.avatar-initials {
  font-size: 10px;
  color: white;
  font-weight: 600;
}

.member-name {
  color: $text-primary;
  font-size: $font-size-sm;
}

.remove-icon {
  font-size: 12px;
  color: $text-secondary;
  cursor: pointer;
  transition: color 0.2s;

  &:hover {
    color: $error-color;
  }
}

.clear-all-icon {
  position: absolute;
  right: 8px;
  font-size: 14px;
  color: $text-secondary;
  cursor: pointer;
  transition: color 0.2s;

  &:hover {
    color: $text-primary;
  }
}

.placeholder {
  color: $text-disabled;
  font-size: $font-size-sm;
}

.member-dropdown {
  display: flex;
  flex-direction: column;
}

.search-box {
  padding: 8px 12px;
  border-bottom: 1px solid $border-color;
}

.loading-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 24px;
  color: $text-secondary;
  font-size: $font-size-sm;
}

.loading-icon {
  animation: rotating 1s linear infinite;
}

@keyframes rotating {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

.member-list {
  max-height: 240px;
  overflow-y: auto;
  padding: 4px 0;
}

.member-option {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px 12px;
  cursor: pointer;
  transition: background-color 0.2s;

  &:hover {
    background-color: $gray-100;
  }

  &.is-selected {
    background-color: rgba($primary-color, 0.08);
  }
}

.member-info {
  flex: 1;
  min-width: 0;

  .member-name {
    font-size: $font-size-sm;
    color: $text-primary;
    font-weight: 500;
  }

  .member-email {
    font-size: 12px;
    color: $text-secondary;
    margin-top: 2px;
  }
}

.check-icon {
  color: $primary-color;
  font-size: 16px;
}

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 32px 16px;
  color: $text-secondary;
  font-size: $font-size-sm;

  .el-icon {
    font-size: 24px;
    color: $text-disabled;
  }
}
</style>
