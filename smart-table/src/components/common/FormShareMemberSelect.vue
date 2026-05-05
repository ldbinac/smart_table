<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Close, Check, Loading, CircleClose } from '@element-plus/icons-vue'
import { useDebounceFn } from '@vueuse/core'
import { formShareApi } from '@/api/formShare'

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
  shareToken?: string  // 分享令牌（必需）
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

// 搜索成员 - 使用分享表单专用接口（无需认证）
async function searchMembers(query: string): Promise<Member[]> {
  console.log('[FormShareMemberSelect] searchMembers called, query:', query, 'shareToken:', props.shareToken)
  
  // 如果没有输入查询内容或没有 shareToken，返回空数组
  if (!query.trim() || !props.shareToken) {
    console.log('[FormShareMemberSelect] Empty query or missing shareToken, returning empty')
    return []
  }

  loading.value = true
  try {
    console.log('[FormShareMemberSelect] Calling API...')
    const response = await formShareApi.searchMembers(props.shareToken, query.trim())
    console.log('[FormShareMemberSelect] API response:', response)
    return response.users.map((user: any) => ({
      id: user.id,
      name: user.name,
      email: user.email,
      avatar: user.avatar,
    }))
  } catch (error) {
    console.error('[FormShareMemberSelect] 搜索用户失败:', error)
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
  console.log('[FormShareMemberSelect] dropdownVisible changed:', visible)
  
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
      console.log('[FormShareMemberSelect] Search input focused')
    }
  }
})

// 判断是否已选中
function isSelected(memberId: string): boolean {
  return selectedMembers.value.some(m => m.id === memberId)
}

// 从 modelValue 初始化选中的成员
function initializeSelectedMembers() {
  if (isUpdating.value) return

  if (!props.modelValue) {
    selectedMembers.value = []
    return
  }

  // 处理 ID 模式
  if (typeof props.modelValue === 'string') {
    // 单个 ID - 需要从搜索结果中查找成员信息
    const memberId = props.modelValue
    // 如果已存在则不重复添加
    if (!selectedMembers.value.find(m => m.id === memberId)) {
      // 创建一个临时的成员对象（只有ID，等待后续补充完整信息）
      selectedMembers.value = [{ id: memberId, name: '', email: '' }]
    }
    return
  }

  if (Array.isArray(props.modelValue)) {
    const ids = props.modelValue as string[]
    if (ids.length === 0) {
      selectedMembers.value = []
      return
    }

    // 过滤掉空值
    const validIds = ids.filter(id => id && id !== 'current_user')
    if (validIds.length === 0) {
      selectedMembers.value = []
      return
    }

    // 更新选中的成员列表（保持已有的成员信息，只添加新的）
    const newMembers: Member[] = validIds.map(id => {
      const existing = selectedMembers.value.find(m => m.id === id)
      if (existing) return existing
      // 新的 ID，创建临时对象
      return { id, name: '', email: '' }
    })

    selectedMembers.value = newMembers
  }
}

// 监听 modelValue 变化，更新选中的成员
watch(() => props.modelValue, () => {
  initializeSelectedMembers()
}, { immediate: true, flush: 'post' })

// 发出更新事件
function emitUpdate(members: Member[]) {
  isUpdating.value = true

  if (props.returnObject) {
    emit('update:modelValue', members.length > 0 ? members : [])
  } else {
    emit('update:modelValue', members.length > 0 ? members.map(m => m.id) : [])
  }

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
      // 添加完整的成员信息（从搜索结果）
      selectedMembers.value.push(member)
    }
    emitUpdate(selectedMembers.value)
  } else {
    // 单选模式
    if (isSelected(member.id)) {
      selectedMembers.value = []
      emitUpdate([])
    } else {
      // 设置完整的成员信息
      selectedMembers.value = [member]
      emitUpdate([member])
    }
    dropdownVisible.value = false
  }
}

// 更新选中成员的详细信息（当搜索结果返回时补充信息）
function updateSelectedMemberInfo(member: Member) {
  const index = selectedMembers.value.findIndex(m => m.id === member.id)
  if (index >= 0 && !selectedMembers.value[index].name) {
    // 补充完整的成员信息
    selectedMembers.value[index] = member
  }
}

// 在搜索结果返回后，更新已选成员的信息
watch(searchResults, (results) => {
  results.forEach(member => updateSelectedMemberInfo(member))
})

// 移除已选成员
function removeMember(memberId: string, event?: Event) {
  event?.stopPropagation()
  if (props.disabled) return

  selectedMembers.value = selectedMembers.value.filter(m => m.id !== memberId)
  emitUpdate(selectedMembers.value)
}

// 清空所有选择
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
              <span class="member-name">{{ member.name || member.id }}</span>
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
  cursor: pointer;  /* 确保显示手型光标 */
  transition: all 0.2s;
  position: relative;  /* 确保定位正确 */
  
  &:hover:not(.is-disabled) {
    border-color: $primary-color;
    background-color: #fafafa;  /* 添加悬停背景色 */
  }

  &.is-disabled {
    background-color: $gray-100;
    cursor: not-allowed;
    opacity: 0.6;
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
