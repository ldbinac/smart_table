<script setup lang="ts">
/**
 * 成员信息显示组件
 * 用于在表格视图、看板视图等场景中显示成员信息
 * 样式与 MemberSelect 保持一致，确保视觉连贯性
 * 使用用户缓存机制避免重复请求
 */
import { ref, watch, onMounted, computed } from 'vue'
import { useUserCacheStore } from '@/stores/userCacheStore'

interface Props {
  // 成员ID或ID数组
  userIds: string | string[] | null | undefined
  // 显示模式：
  // - 'name': 只显示名称
  // - 'avatar': 只显示头像（重叠样式）
  // - 'both': 显示头像+名称（水平排列）
  // - 'tag': 标签样式（与 MemberSelect 一致）
  mode?: 'name' | 'avatar' | 'both' | 'tag'
  // 分隔符（多个成员时，name模式）
  separator?: string
  // 最多显示数量，超出显示+n
  maxDisplay?: number
  // 头像大小
  avatarSize?: number
  // 是否显示工具提示
  showTooltip?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  mode: 'tag',
  separator: ', ',
  maxDisplay: 3,
  avatarSize: 22,
  showTooltip: true
})

// 用户缓存存储
const userCacheStore = useUserCacheStore()

// 成员信息列表
const members = ref<Array<{ id: string; name: string; avatar?: string }>>([])
// 加载状态
const loading = ref(false)

// 获取姓名首字母
function getInitials(name: string): string {
  if (!name) return '?'
  return name
    .split(' ')
    .map(n => n[0])
    .join('')
    .toUpperCase()
    .slice(0, 2)
}

// 生成头像背景色
function getAvatarColor(name: string): string {
  const colors = ['#2d7cfc', '#10B981', '#F59E0B', '#EF4444', '#8B5CF6', '#EC4899']
  if (!name) return colors[0]
  let hash = 0
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash)
  }
  return colors[Math.abs(hash) % colors.length]
}

// 加载成员信息
async function loadMembers() {
  if (!props.userIds) {
    members.value = []
    return
  }

  // 标准化为数组
  const ids = Array.isArray(props.userIds) 
    ? props.userIds 
    : [props.userIds]
  
  // 过滤空值
  const validIds = ids.filter(id => id && id !== 'current_user')
  
  if (validIds.length === 0) {
    members.value = []
    return
  }

  loading.value = true
  
  try {
    // 使用缓存批量获取用户信息
    const cachedUsers = await userCacheStore.fetchUsers(validIds)
    
    members.value = cachedUsers.map(user => ({
      id: user.id,
      name: user.name,
      avatar: user.avatar
    }))
  } catch (error) {
    console.error('[MemberDisplay] 加载成员信息失败:', error)
    members.value = []
  } finally {
    loading.value = false
  }
}

// 监听 userIds 变化
watch(() => props.userIds, () => {
  loadMembers()
}, { deep: true })

// 组件挂载时加载
onMounted(() => {
  loadMembers()
})

// 显示的成员（限制数量）
const displayMembers = computed(() => {
  return members.value.slice(0, props.maxDisplay)
})

// 超出数量
const overflowCount = computed(() => {
  return Math.max(0, members.value.length - props.maxDisplay)
})

// 所有成员名称（用于工具提示）
const allMemberNames = computed(() => {
  return members.value.map(m => m.name).join(', ')
})
</script>

<template>
  <div class="member-display" :class="[`mode-${mode}`]">
    <!-- 加载中状态 -->
    <span v-if="loading" class="loading-text">加载中...</span>
    
    <!-- 无数据状态 -->
    <span v-else-if="members.length === 0" class="empty-text">-</span>
    
    <!-- 标签模式（与 MemberSelect 样式一致） -->
    <template v-else-if="mode === 'tag'">
      <div class="member-tags">
        <div
          v-for="member in displayMembers"
          :key="member.id"
          class="member-tag"
          :title="showTooltip ? member.name : ''"
        >
          <div
            class="member-avatar"
            :style="{ 
              width: `${avatarSize}px`, 
              height: `${avatarSize}px`,
              backgroundColor: getAvatarColor(member.name)
            }"
          >
            <img v-if="member.avatar" :src="member.avatar" :alt="member.name" />
            <span v-else class="avatar-initials">{{ getInitials(member.name) }}</span>
          </div>
          <span class="member-name">{{ member.name }}</span>
        </div>
        <span v-if="overflowCount > 0" class="overflow-badge" :title="allMemberNames">
          +{{ overflowCount }}
        </span>
      </div>
    </template>
    
    <!-- 头像模式（重叠样式） -->
    <template v-else-if="mode === 'avatar'">
      <div class="avatar-list" :title="showTooltip ? allMemberNames : ''">
        <div
          v-for="(member, index) in displayMembers"
          :key="member.id"
          class="member-avatar stacked"
          :style="{ 
            width: `${avatarSize}px`, 
            height: `${avatarSize}px`,
            backgroundColor: getAvatarColor(member.name),
            zIndex: displayMembers.length - index
          }"
        >
          <img v-if="member.avatar" :src="member.avatar" :alt="member.name" />
          <span v-else class="avatar-initials">{{ getInitials(member.name) }}</span>
        </div>
        <div v-if="overflowCount > 0" class="overflow-badge stacked" :style="{ height: `${avatarSize}px` }">
          +{{ overflowCount }}
        </div>
      </div>
    </template>
    
    <!-- 名称模式 -->
    <template v-else-if="mode === 'name'">
      <span class="member-names" :title="showTooltip ? allMemberNames : ''">
        {{ displayMembers.map(m => m.name).join(separator) }}
        <span v-if="overflowCount > 0" class="overflow-text">+{{ overflowCount }}</span>
      </span>
    </template>
    
    <!-- 头像+名称模式（水平排列） -->
    <template v-else>
      <div class="member-list">
        <div
          v-for="member in displayMembers"
          :key="member.id"
          class="member-item"
          :title="showTooltip ? member.name : ''"
        >
          <div
            class="member-avatar"
            :style="{ 
              width: `${avatarSize}px`, 
              height: `${avatarSize}px`,
              backgroundColor: getAvatarColor(member.name)
            }"
          >
            <img v-if="member.avatar" :src="member.avatar" :alt="member.name" />
            <span v-else class="avatar-initials">{{ getInitials(member.name) }}</span>
          </div>
          <span class="member-name">{{ member.name }}</span>
        </div>
        <span v-if="overflowCount > 0" class="overflow-text" :title="allMemberNames">
          +{{ overflowCount }}
        </span>
      </div>
    </template>
  </div>
</template>

<style lang="scss" scoped>
@use '@/assets/styles/variables' as *;

.member-display {
  display: inline-flex;
  align-items: center;
  max-width: 100%;
}

.loading-text,
.empty-text {
  color: $text-secondary;
  font-size: $font-size-sm;
}

// 标签模式（与 MemberSelect 样式一致）
.member-tags {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: $spacing-xs;
  
  .member-tag {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 2px 8px;
    background-color: $gray-100;
    border-radius: $border-radius-sm;
    font-size: $font-size-sm;
    transition: background-color 0.2s;
    max-width: 100%;
    overflow: hidden;
    
    &:hover {
      background-color: $gray-200;
    }
  }
  
  .member-avatar {
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
    
    .avatar-initials {
      font-size: 10px;
      color: white;
      font-weight: 600;
    }
  }
  
  .member-name {
    color: $text-primary;
    font-size: $font-size-sm;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }
  
  .overflow-badge {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 2px 6px;
    background-color: $gray-200;
    border-radius: $border-radius-sm;
    font-size: 11px;
    color: $text-secondary;
    cursor: help;
  }
}

// 头像重叠样式
.avatar-list {
  display: flex;
  align-items: center;
  
  .member-avatar {
    border-radius: 50%;
    overflow: hidden;
    display: flex;
    align-items: center;
    justify-content: center;
    flex-shrink: 0;
    border: 2px solid white;
    margin-left: -8px;
    transition: transform 0.2s, margin-left 0.2s;
    
    &:first-child {
      margin-left: 0;
    }
    
    &:hover {
      transform: translateY(-2px);
      z-index: 100 !important;
    }
    
    img {
      width: 100%;
      height: 100%;
      object-fit: cover;
    }
    
    .avatar-initials {
      font-size: 10px;
      color: white;
      font-weight: 600;
    }
  }
  
  .overflow-badge {
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0 6px;
    background-color: $gray-200;
    border-radius: 12px;
    font-size: 11px;
    color: $text-secondary;
    margin-left: 4px;
    border: 2px solid white;
    cursor: help;
  }
}

// 名称模式
.member-names {
  color: $text-primary;
  font-size: $font-size-sm;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  
  .overflow-text {
    color: $text-secondary;
    margin-left: 4px;
  }
}

// 头像+名称模式
.member-list {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
  
  .member-item {
    display: flex;
    align-items: center;
    gap: 6px;
    padding: 2px 8px 2px 2px;
    background-color: $gray-100;
    border-radius: $border-radius-sm;
    transition: background-color 0.2s;
    
    &:hover {
      background-color: $gray-200;
    }
  }
  
  .member-avatar {
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
    
    .avatar-initials {
      font-size: 10px;
      color: white;
      font-weight: 600;
    }
  }
  
  .member-name {
    font-size: $font-size-sm;
    color: $text-primary;
    white-space: nowrap;
  }
  
  .overflow-text {
    color: $text-secondary;
    font-size: $font-size-sm;
    cursor: help;
  }
}

// 响应式处理
@media (max-width: 768px) {
  .member-tags {
    .member-tag {
      .member-name {
        max-width: 80px;
      }
    }
  }
  
  .member-names {
    max-width: 120px;
  }
}
</style>
