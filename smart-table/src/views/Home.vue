<script setup lang="ts">
import { ref, reactive, onMounted, computed } from "vue";
import { useRouter } from "vue-router";
import { useBaseStore } from "@/stores";
import type { FormInstance, FormRules } from "element-plus";
import { ElMessage, ElMessageBox } from "element-plus";
import type { Base } from "@/db/schema";

const router = useRouter();
const baseStore = useBaseStore();
const createFormRef = ref<FormInstance>();
const editFormRef = ref<FormInstance>();

// 创建对话框显示状态
const createDialogVisible = ref(false);

// 编辑对话框显示状态
const editDialogVisible = ref(false);

// 创建表单数据
const createForm = reactive({
  name: "",
  description: "",
  icon: "📊",
  color: "#409EFF",
});

// 编辑表单数据
const editForm = reactive({
  id: "",
  name: "",
  description: "",
  icon: "📊",
  color: "#409EFF",
});

// 表单验证规则
const createFormRules: FormRules = {
  name: [
    { required: true, message: "请输入多维表格名称", trigger: "blur" },
    { min: 1, max: 50, message: "名称长度在 1 到 50 个字符", trigger: "blur" },
  ],
};

// 编辑表单验证规则
const editFormRules: FormRules = {
  name: [
    { required: true, message: "请输入多维表格名称", trigger: "blur" },
    { min: 1, max: 50, message: "名称长度在 1 到 50 个字符", trigger: "blur" },
  ],
};

// 预设图标选项
const iconOptions = [
  "📊", "📋", "📁", "📝", "📅",
  "💼", "📈", "🎯", "✅", "📌",
];

// 预设颜色选项 - 清新配色
const colorOptions = [
  "#3B82F6", // 清新蓝
  "#10B981", // 翠绿
  "#F59E0B", // 活力橙
  "#EF4444", // 珊瑚红
  "#8B5CF6", // 紫罗兰
  "#06B6D4", // 青色
  "#EC4899", // 粉红
  "#6366F1", // 靛蓝
];

// 取消收藏加载状态
const unstarLoadingMap = ref<Map<string, boolean>>(new Map());

// ========== 搜索功能 ==========
const searchQuery = ref("");
const searchInputRef = ref<HTMLInputElement | null>(null);
let searchTimeout: number | null = null;

// 防抖搜索
const handleSearchInput = () => {
  if (searchTimeout) {
    clearTimeout(searchTimeout);
  }
  searchTimeout = window.setTimeout(() => {
    // 搜索逻辑已在计算属性中实现
  }, 300);
};

// 高亮匹配文本
const highlightText = (text: string, query: string): string => {
  if (!query.trim()) return text;
  const regex = new RegExp(`(${escapeRegExp(query)})`, "gi");
  return text.replace(regex, '<mark class="search-highlight">$1</mark>');
};

// 转义正则特殊字符
const escapeRegExp = (string: string): string => {
  return string.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
};

// 收藏的 Base 列表（带搜索过滤）
const starredBases = computed(() => {
  const query = searchQuery.value.trim().toLowerCase();
  return baseStore.bases
    .filter((base) => base.isStarred)
    .filter((base) => {
      if (!query) return true;
      return base.name.toLowerCase().includes(query);
    })
    .sort((a, b) => b.updatedAt - a.updatedAt);
});

// 所有 Base 列表（带搜索过滤）
const allBases = computed(() => {
  const query = searchQuery.value.trim().toLowerCase();
  return baseStore.bases
    .filter((base) => {
      if (!query) return true;
      return base.name.toLowerCase().includes(query);
    })
    .sort((a, b) => b.updatedAt - a.updatedAt);
});

// 是否有收藏的项目
const hasStarredBases = computed(() => starredBases.value.length > 0);

// 是否有搜索结果
const hasSearchResults = computed(() => {
  return starredBases.value.length > 0 || allBases.value.length > 0;
});

// 清空搜索
const clearSearch = () => {
  searchQuery.value = "";
  searchInputRef.value?.focus();
};

onMounted(async () => {
  await baseStore.loadBases();
});

function goToBase(id: string) {
  const baseUrl = window.location.origin;
  window.open(`${baseUrl}/#/base/${id}`, "_blank");
}

function goToSettings() {
  router.push("/settings");
}

function openCreateDialog() {
  createDialogVisible.value = true;
  createForm.name = "";
  createForm.description = "";
  createForm.icon = "📊";
  createForm.color = "#3B82F6";
}

function closeCreateDialog() {
  createDialogVisible.value = false;
  createFormRef.value?.resetFields();
}

async function handleCreateBase() {
  if (!createFormRef.value) return;

  await createFormRef.value.validate(async (valid) => {
    if (valid) {
      const base = await baseStore.createBase({
        name: createForm.name,
        description: createForm.description || undefined,
        icon: createForm.icon,
        color: createForm.color,
      });

      if (base) {
        ElMessage.success("创建成功");
        closeCreateDialog();
      } else {
        ElMessage.error(baseStore.error || "创建失败");
      }
    }
  });
}

// 打开编辑对话框
function openEditDialog(base: Base) {
  editForm.id = base.id;
  editForm.name = base.name;
  editForm.description = base.description || "";
  editForm.icon = base.icon || "📊";
  editForm.color = base.color || "#3B82F6";
  editDialogVisible.value = true;
}

function closeEditDialog() {
  editDialogVisible.value = false;
  editFormRef.value?.resetFields();
}

async function handleEditBase() {
  if (!editFormRef.value) return;

  await editFormRef.value.validate(async (valid) => {
    if (valid) {
      await baseStore.updateBase(editForm.id, {
        name: editForm.name,
        description: editForm.description || undefined,
        icon: editForm.icon,
        color: editForm.color,
      });

      ElMessage.success("更新成功");
      closeEditDialog();
    }
  });
}

// 处理删除
async function handleDeleteBase(base: Base) {
  try {
    await ElMessageBox.confirm(
      `确定要删除多维表格 "${base.name}" 吗？此操作将删除该表格中的所有数据表、字段和记录，且无法恢复。`,
      "删除确认",
      {
        confirmButtonText: "删除",
        cancelButtonText: "取消",
        type: "warning",
        confirmButtonClass: "el-button--danger",
      }
    );

    await baseStore.deleteBase(base.id);
    ElMessage.success("删除成功");
  } catch (error) {
    if (error !== "cancel") {
      ElMessage.error("删除失败");
    }
  }
}

// 处理收藏
async function handleStarBase(base: Base, event: Event) {
  event.stopPropagation();
  await baseStore.toggleStarBase(base.id);
  ElMessage.success("已收藏");
}

// 处理取消收藏
async function handleUnstarBase(base: Base, event: Event) {
  event.stopPropagation();
  unstarLoadingMap.value.set(base.id, true);

  try {
    await baseStore.toggleStarBase(base.id);
    ElMessage.success("已取消收藏");
  } catch (error) {
    ElMessage.error("取消收藏失败");
  } finally {
    unstarLoadingMap.value.set(base.id, false);
  }
}

// 获取取消收藏加载状态
function isUnstarLoading(baseId: string): boolean {
  return unstarLoadingMap.value.get(baseId) || false;
}

// 阻止事件冒泡
function stopPropagation(event: Event) {
  event.stopPropagation();
}
</script>

<template>
  <div class="home-page">
    <!-- 顶部搜索栏 -->
    <header class="home-header">
      <div class="header-brand">
        <div class="brand-logo">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <rect x="3" y="3" width="18" height="18" rx="2" />
            <path d="M3 9h18M9 3v18" />
          </svg>
        </div>
        <h1>Smart Table</h1>
      </div>

      <!-- 全局搜索框 -->
      <div class="header-search">
        <div class="search-wrapper">
          <el-icon class="search-icon"><Search /></el-icon>
          <input
            ref="searchInputRef"
            v-model="searchQuery"
            type="text"
            class="search-input"
            placeholder="搜索多维表格..."
            @input="handleSearchInput"
          />
          <el-icon
            v-if="searchQuery"
            class="search-clear"
            @click="clearSearch"
          >
            <CircleClose />
          </el-icon>
        </div>
        <div v-if="searchQuery" class="search-stats">
          找到 {{ starredBases.length + allBases.length }} 个结果
        </div>
      </div>

      <div class="header-actions">
        <el-button type="primary" class="create-btn" @click="openCreateDialog">
          <el-icon><Plus /></el-icon>
          <span>新建</span>
        </el-button>
        <el-button class="settings-btn" @click="goToSettings">
          <el-icon><Setting /></el-icon>
        </el-button>
      </div>
    </header>

    <main class="home-content">
      <!-- 空状态 -->
      <div v-if="baseStore.bases.length === 0" class="empty-state">
        <div class="empty-illustration">
          <svg viewBox="0 0 200 200" fill="none">
            <rect x="40" y="60" width="120" height="100" rx="8" fill="#E0E7FF" />
            <rect x="60" y="80" width="80" height="8" rx="4" fill="#6366F1" />
            <rect x="60" y="100" width="60" height="8" rx="4" fill="#A5B4FC" />
            <rect x="60" y="120" width="70" height="8" rx="4" fill="#A5B4FC" />
          </svg>
        </div>
        <h3>开始创建您的第一个多维表格</h3>
        <p class="empty-desc">多维表格让数据管理更简单、更高效</p>
        <el-button type="primary" size="large" @click="openCreateDialog">
          <el-icon><Plus /></el-icon>
          创建多维表格
        </el-button>
      </div>

      <!-- 搜索无结果 -->
      <div v-else-if="!hasSearchResults" class="empty-state search-empty">
        <el-icon class="empty-icon" :size="64"><Search /></el-icon>
        <h3>未找到匹配的多维表格</h3>
        <p class="empty-desc">尝试使用其他关键词搜索</p>
        <el-button @click="clearSearch">清除搜索</el-button>
      </div>

      <div v-else class="content-wrapper">
        <!-- 收藏分区 -->
        <section v-if="hasStarredBases" class="section starred-section">
          <div class="section-header">
            <div class="section-title">
              <div class="title-icon starred-icon">
                <el-icon><StarFilled /></el-icon>
              </div>
              <h2>我的收藏</h2>
              <span class="count-badge">{{ starredBases.length }}</span>
            </div>
          </div>

          <div class="card-grid">
            <div
              v-for="base in starredBases"
              :key="base.id"
              class="base-card starred"
              @click="goToBase(base.id)"
            >
              <div class="card-main">
                <div
                  class="card-icon"
                  :style="{ backgroundColor: base.color || '#3B82F6' }"
                >
                  {{ base.icon || "📊" }}
                </div>
                <div class="card-info">
                  <h3
                    class="card-name"
                    v-html="highlightText(base.name, searchQuery)"
                  />
                  <p class="card-desc">{{ base.description || "暂无描述" }}</p>
                </div>
              </div>
              <div class="card-footer">
                <span class="update-time">
                  最后修改时间：{{ new Date(base.updatedAt).toLocaleString("zh-CN", { year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }) }}
                </span>
                <div class="card-actions" @click.stop="stopPropagation">
                  <el-button
                    link
                    type="warning"
                    :loading="isUnstarLoading(base.id)"
                    @click="handleUnstarBase(base, $event)"
                  >
                    <el-icon><StarFilled /></el-icon>
                  </el-button>
                  <el-dropdown
                    trigger="click"
                    @command="(cmd) => {
                      if (cmd === 'edit') openEditDialog(base);
                      else if (cmd === 'delete') handleDeleteBase(base);
                    }"
                  >
                    <el-button link>
                      <el-icon><MoreFilled /></el-icon>
                    </el-button>
                    <template #dropdown>
                      <el-dropdown-menu>
                        <el-dropdown-item command="edit">
                          <el-icon><Edit /></el-icon>编辑
                        </el-dropdown-item>
                        <el-dropdown-item divided command="delete" class="delete-item">
                          <el-icon><Delete /></el-icon>删除
                        </el-dropdown-item>
                      </el-dropdown-menu>
                    </template>
                  </el-dropdown>
                </div>
              </div>
            </div>
          </div>
        </section>

        <!-- 所有多维表格分区 -->
        <section v-if="allBases.length > 0" class="section all-section">
          <div class="section-header">
            <div class="section-title">
              <div class="title-icon all-icon">
                <el-icon><Grid /></el-icon>
              </div>
              <h2>所有多维表格</h2>
              <span class="count-badge gray">{{ allBases.length }}</span>
            </div>
          </div>

          <div class="card-grid">
            <!-- 创建卡片 -->
            <div class="base-card create-card" @click="openCreateDialog">
              <div class="create-content">
                <div class="create-icon">
                  <el-icon :size="24"><Plus /></el-icon>
                </div>
                <span>创建多维表格</span>
              </div>
            </div>

            <!-- Base 卡片 -->
            <div
              v-for="base in allBases"
              :key="base.id"
              class="base-card"
              :class="{ starred: base.isStarred }"
              @click="goToBase(base.id)"
            >
              <div class="card-main">
                <div
                  class="card-icon"
                  :style="{ backgroundColor: base.color || '#3B82F6' }"
                >
                  {{ base.icon || "📊" }}
                </div>
                <div class="card-info">
                  <h3
                    class="card-name"
                    v-html="highlightText(base.name, searchQuery)"
                  />
                  <p class="card-desc">{{ base.description || "暂无描述" }}</p>
                </div>
              </div>
              <div class="card-footer">
                <span class="update-time">
                  最后修改时间：{{ new Date(base.updatedAt).toLocaleString("zh-CN", { year: "numeric", month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }) }}
                </span>
                <div class="card-actions" @click.stop="stopPropagation">
                  <el-button
                    v-if="!base.isStarred"
                    link
                    @click="handleStarBase(base, $event)"
                  >
                    <el-icon><Star /></el-icon>
                  </el-button>
                  <el-button
                    v-else
                    link
                    type="warning"
                    @click="handleUnstarBase(base, $event)"
                  >
                    <el-icon><StarFilled /></el-icon>
                  </el-button>
                  <el-dropdown
                    trigger="click"
                    @command="(cmd) => {
                      if (cmd === 'edit') openEditDialog(base);
                      else if (cmd === 'delete') handleDeleteBase(base);
                    }"
                  >
                    <el-button link>
                      <el-icon><MoreFilled /></el-icon>
                    </el-button>
                    <template #dropdown>
                      <el-dropdown-menu>
                        <el-dropdown-item command="edit">
                          <el-icon><Edit /></el-icon>编辑
                        </el-dropdown-item>
                        <el-dropdown-item divided command="delete" class="delete-item">
                          <el-icon><Delete /></el-icon>删除
                        </el-dropdown-item>
                      </el-dropdown-menu>
                    </template>
                  </el-dropdown>
                </div>
              </div>
            </div>
          </div>
        </section>
      </div>
    </main>

    <!-- 创建对话框 -->
    <el-dialog
      v-model="createDialogVisible"
      title="创建多维表格"
      width="480px"
      :close-on-click-modal="false"
      class="create-dialog"
    >
      <el-form
        ref="createFormRef"
        :model="createForm"
        :rules="createFormRules"
        label-width="70px"
        class="compact-form"
      >
        <el-form-item label="名称" prop="name">
          <el-input
            v-model="createForm.name"
            placeholder="请输入多维表格名称"
            maxlength="50"
            show-word-limit
          />
        </el-form-item>

        <el-form-item label="描述">
          <el-input
            v-model="createForm.description"
            type="textarea"
            :rows="2"
            placeholder="请输入描述（可选）"
            maxlength="200"
            show-word-limit
          />
        </el-form-item>

        <el-form-item label="图标">
          <div class="icon-selector compact">
            <span
              v-for="icon in iconOptions"
              :key="icon"
              class="icon-option"
              :class="{ active: createForm.icon === icon }"
              @click="createForm.icon = icon"
            >
              {{ icon }}
            </span>
          </div>
        </el-form-item>

        <el-form-item label="颜色">
          <div class="color-selector compact">
            <span
              v-for="color in colorOptions"
              :key="color"
              class="color-option"
              :style="{ backgroundColor: color }"
              :class="{ active: createForm.color === color }"
              @click="createForm.color = color"
            />
          </div>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="closeCreateDialog">取消</el-button>
        <el-button type="primary" @click="handleCreateBase">创建</el-button>
      </template>
    </el-dialog>

    <!-- 编辑对话框 -->
    <el-dialog
      v-model="editDialogVisible"
      title="编辑多维表格"
      width="480px"
      :close-on-click-modal="false"
      class="create-dialog"
    >
      <el-form
        ref="editFormRef"
        :model="editForm"
        :rules="editFormRules"
        label-width="70px"
        class="compact-form"
      >
        <el-form-item label="名称" prop="name">
          <el-input
            v-model="editForm.name"
            placeholder="请输入多维表格名称"
            maxlength="50"
            show-word-limit
          />
        </el-form-item>

        <el-form-item label="描述">
          <el-input
            v-model="editForm.description"
            type="textarea"
            :rows="2"
            placeholder="请输入描述（可选）"
            maxlength="200"
            show-word-limit
          />
        </el-form-item>

        <el-form-item label="图标">
          <div class="icon-selector compact">
            <span
              v-for="icon in iconOptions"
              :key="icon"
              class="icon-option"
              :class="{ active: editForm.icon === icon }"
              @click="editForm.icon = icon"
            >
              {{ icon }}
            </span>
          </div>
        </el-form-item>

        <el-form-item label="颜色">
          <div class="color-selector compact">
            <span
              v-for="color in colorOptions"
              :key="color"
              class="color-option"
              :style="{ backgroundColor: color }"
              :class="{ active: editForm.color === color }"
              @click="editForm.color = color"
            />
          </div>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="closeEditDialog">取消</el-button>
        <el-button type="primary" @click="handleEditBase">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script lang="ts">
import {
  Plus,
  Delete,
  Edit,
  Star,
  StarFilled,
  MoreFilled,
  Grid,
  Setting,
  Search,
  CircleClose,
} from "@element-plus/icons-vue";

export default {
  name: "HomeView",
};
</script>

<style lang="scss" scoped>
// 清新配色变量
$primary: #3B82F6;
$primary-light: #EFF6FF;
$success: #10B981;
$warning: #F59E0B;
$danger: #EF4444;
$gray-50: #F9FAFB;
$gray-100: #F3F4F6;
$gray-200: #E5E7EB;
$gray-300: #D1D5DB;
$gray-400: #9CA3AF;
$gray-500: #6B7280;
$gray-600: #4B5563;
$gray-700: #374151;
$gray-800: #1F2937;
$gray-900: #111827;
$star-color: #F59E0B;

.home-page {
  min-height: 100vh;
  background: linear-gradient(180deg, #F9FAFB 0%, #FFFFFF 100%);
}

// 顶部搜索栏
.home-header {
  position: sticky;
  top: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 32px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid $gray-200;
  gap: 24px;
}

.header-brand {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;

  .brand-logo {
    width: 36px;
    height: 36px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, $primary 0%, #6366F1 100%);
    border-radius: 10px;
    color: white;

    svg {
      width: 20px;
      height: 20px;
    }
  }

  h1 {
    font-size: 20px;
    font-weight: 700;
    color: $gray-800;
    margin: 0;
    letter-spacing: -0.5px;
  }
}

// 搜索框
.header-search {
  flex: 1;
  max-width: 480px;
  position: relative;

  .search-wrapper {
    position: relative;
    display: flex;
    align-items: center;
  }

  .search-icon {
    position: absolute;
    left: 14px;
    color: $gray-400;
    font-size: 18px;
    z-index: 1;
  }

  .search-input {
    width: 100%;
    height: 42px;
    padding: 0 40px;
    border: 1px solid $gray-200;
    border-radius: 21px;
    font-size: 14px;
    background: $gray-50;
    transition: all 0.2s ease;

    &::placeholder {
      color: $gray-400;
    }

    &:focus {
      outline: none;
      background: white;
      border-color: $primary;
      box-shadow: 0 0 0 3px rgba($primary, 0.1);
    }
  }

  .search-clear {
    position: absolute;
    right: 14px;
    color: $gray-400;
    cursor: pointer;
    font-size: 16px;
    transition: color 0.2s;

    &:hover {
      color: $gray-600;
    }
  }

  .search-stats {
    position: absolute;
    top: 100%;
    left: 16px;
    margin-top: 6px;
    font-size: 12px;
    color: $gray-500;
  }
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;

  .create-btn {
    height: 40px;
    padding: 0 20px;
    border-radius: 20px;
    font-weight: 500;
    background: linear-gradient(135deg, $primary 0%, #6366F1 100%);
    border: none;
    box-shadow: 0 4px 14px rgba($primary, 0.35);
    transition: all 0.3s ease;

    &:hover {
      transform: translateY(-2px);
      box-shadow: 0 6px 20px rgba($primary, 0.45);
    }

    .el-icon {
      margin-right: 6px;
    }
  }

  .settings-btn {
    width: 40px;
    height: 40px;
    border-radius: 10px;
    border: 1px solid $gray-200;
    color: $gray-500;
    transition: all 0.2s;

    &:hover {
      background: $gray-100;
      color: $gray-700;
      border-color: $gray-300;
    }
  }
}

// 主内容区
.home-content {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px 32px 48px;
}

.content-wrapper {
  display: flex;
  flex-direction: column;
  gap: 32px;
}

// 分区样式
.section {
  .section-header {
    margin-bottom: 16px;
  }

  .section-title {
    display: flex;
    align-items: center;
    gap: 10px;

    .title-icon {
      width: 32px;
      height: 32px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 8px;
      font-size: 16px;

      &.starred-icon {
        background: rgba($star-color, 0.1);
        color: $star-color;
      }

      &.all-icon {
        background: rgba($primary, 0.1);
        color: $primary;
      }
    }

    h2 {
      font-size: 16px;
      font-weight: 600;
      color: $gray-800;
      margin: 0;
    }

    .count-badge {
      padding: 2px 10px;
      border-radius: 12px;
      font-size: 12px;
      font-weight: 500;
      background: rgba($star-color, 0.1);
      color: $star-color;

      &.gray {
        background: $gray-100;
        color: $gray-500;
      }
    }
  }
}

// 卡片网格 - 减小尺寸
.card-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: 16px;
}

// 卡片样式 - 清新风格
.base-card {
  background: white;
  border-radius: 12px;
  border: 1px solid $gray-200;
  padding: 12px 16px;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;

  &::before {
    content: "";
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 3px;
    background: transparent;
    transition: background 0.3s;
  }

  &:hover {
    transform: translateY(-3px);
    box-shadow: 0 12px 24px -8px rgba(0, 0, 0, 0.1);
    border-color: $gray-300;

    .card-actions {
      opacity: 1;
      transform: translateY(0);
    }
  }

  // 收藏卡片保持原有样式（在starred-section中）
  .starred-section &.starred::before {
    background: $star-color;
  }

  // 所有表格区域中的非收藏卡片默认显示顶部条
  .all-section &:not(.starred)::before {
    background: linear-gradient(90deg, $primary 0%, $primary-light 100%);
  }

  // 所有卡片的悬停效果
  &:hover::before {
    opacity: 1;
  }
}

.card-main {
  display: flex;
  gap: 12px;
  margin-bottom: 8px;
}

.card-icon {
  width: 40px;
  height: 40px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  font-size: 18px;
  flex-shrink: 0;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.card-info {
  flex: 1;
  min-width: 0;

  .card-name {
    font-size: 15px;
    font-weight: 600;
    color: $gray-800;
    margin: 0 0 4px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;

    :deep(.search-highlight) {
      background: rgba($primary, 0.2);
      color: $primary;
      padding: 0 2px;
      border-radius: 3px;
      font-weight: 700;
    }
  }

  .card-desc {
    font-size: 12px;
    color: $gray-500;
    margin: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}

.card-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding-top: 8px;
  border-top: 1px solid $gray-100;

  .update-time {
    font-size: 11px;
    color: $gray-400;
    line-height: 1.2;
    text-align: right;
    flex: 1;
  }

  .card-actions {
    display: flex;
    align-items: center;
    gap: 4px;
    opacity: 0;
    transform: translateY(4px);
    transition: all 0.2s ease;

    .el-button {
      padding: 6px;
      color: $gray-400;
      transition: all 0.2s;

      &:hover {
        color: $gray-600;
        background: $gray-100;
      }

      &.el-button--warning {
        color: $star-color;

        &:hover {
          background: rgba($star-color, 0.1);
        }
      }
    }
  }
}

// 创建卡片
.create-card {
  border-style: dashed;
  background: $gray-50;
  border-color: $gray-300;

  &:hover {
    background: white;
    border-color: $primary;
    border-style: solid;
  }
}

.create-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  height: 100%;
  min-height: 80px;
  color: $gray-500;
  font-size: 13px;
  font-weight: 500;

  .create-icon {
    width: 40px;
    height: 40px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: white;
    border-radius: 10px;
    box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
    color: $primary;
  }
}

// 空状态
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  text-align: center;

  .empty-illustration {
    width: 160px;
    height: 160px;
    margin-bottom: 24px;

    svg {
      width: 100%;
      height: 100%;
    }
  }

  .empty-icon {
    color: $gray-300;
    margin-bottom: 16px;
  }

  h3 {
    font-size: 18px;
    font-weight: 600;
    color: $gray-700;
    margin: 0 0 8px;
  }

  .empty-desc {
    font-size: 14px;
    color: $gray-500;
    margin: 0 0 24px;
  }

  &.search-empty {
    padding: 60px 20px;
  }
}

// 对话框样式
.create-dialog {
  :deep(.el-dialog__header) {
    padding: 20px 24px 16px;
    border-bottom: 1px solid $gray-100;

    .el-dialog__title {
      font-size: 16px;
      font-weight: 600;
      color: $gray-800;
    }
  }

  :deep(.el-dialog__body) {
    padding: 20px 24px;
  }

  :deep(.el-dialog__footer) {
    padding: 16px 24px;
    border-top: 1px solid $gray-100;
  }
}

.compact-form {
  .el-form-item {
    margin-bottom: 16px;

    &:last-child {
      margin-bottom: 0;
    }
  }

  :deep(.el-form-item__label) {
    font-size: 13px;
    color: $gray-600;
    padding-right: 12px;
  }
}

// 图标选择器
.icon-selector {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;

  &.compact .icon-option {
    width: 36px;
    height: 36px;
    font-size: 18px;
  }
}

.icon-option {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border: 2px solid $gray-200;
  border-radius: 8px;
  cursor: pointer;
  font-size: 20px;
  transition: all 0.2s;

  &:hover {
    border-color: $primary;
    background: $primary-light;
  }

  &.active {
    border-color: $primary;
    background: $primary-light;
    box-shadow: 0 0 0 2px rgba($primary, 0.2);
  }
}

// 颜色选择器
.color-selector {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;

  &.compact .color-option {
    width: 28px;
    height: 28px;
  }
}

.color-option {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  cursor: pointer;
  transition: all 0.2s;
  border: 3px solid transparent;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);

  &:hover {
    transform: scale(1.15);
  }

  &.active {
    border-color: white;
    box-shadow: 0 0 0 2px $gray-400, 0 2px 4px rgba(0, 0, 0, 0.1);
  }
}

// 下拉菜单
:deep(.delete-item) {
  color: $danger;

  &:hover {
    background: rgba($danger, 0.05);
  }
}

// 响应式设计
@media (max-width: 768px) {
  .home-header {
    padding: 12px 16px;
    flex-wrap: wrap;
    gap: 12px;

    .header-brand h1 {
      display: none;
    }

    .header-search {
      order: 3;
      max-width: none;
      width: 100%;
    }
  }

  .home-content {
    padding: 16px;
  }

  .card-grid {
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 12px;
  }

  .base-card {
    padding: 12px;
  }

  .card-icon {
    width: 38px;
    height: 38px;
    font-size: 18px;
  }

  .card-footer .card-actions {
    opacity: 1;
    transform: translateY(0);
  }
}

@media (max-width: 480px) {
  .card-grid {
    grid-template-columns: 1fr;
  }
}
</style>
