<script setup lang="ts">
import { ref, reactive, onMounted, computed, watch } from "vue";
import { useRouter } from "vue-router";
import { useBaseStore } from "@/stores";
import { useAuthStore } from "@/stores/authStore";
import type { FormInstance, FormRules } from "element-plus";
import { ElMessage, ElMessageBox } from "element-plus";
import type { Base } from "@/db/schema";
import { tableTemplates, type TableTemplate } from "@/utils/tableTemplates";
import { templateService } from "@/db/services";
import { getFieldTypeLabel, getFieldTypeIcon } from "@/types";
import { copyBase } from "@/services/api/baseApiService";
import { DocumentCopy } from "@element-plus/icons-vue";

const router = useRouter();
const baseStore = useBaseStore();
const authStore = useAuthStore();
const createFormRef = ref<FormInstance>();
const editFormRef = ref<FormInstance>();

// 当前登录用户ID
const currentUserId = computed(() => authStore.user?.id);

// 判断当前用户是否是Base的所有者
const isBaseOwner = (base: Base) => {
  return base.owner_id === currentUserId.value;
};

// 当前导航项
const currentNav = ref<"home" | "all" | "templates" | "shares">("home");

// 分享视图页签状态
const shareActiveTab = ref<"shared-by-me" | "shared-with-me">("shared-by-me");

// 分享给我的 Base 列表
const sharedWithMeBases = ref<Base[]>([]);
// 我创建的分享列表
const sharedByMeShares = ref<any[]>([]);
// 分享相关加载状态
const sharingLoading = ref(false);

// 加载状态
const templateLoadingMap = ref<Map<string, boolean>>(new Map());

// 全部多维表视图页签状态
const activeTab = ref<"starred" | "all">("starred");

// 加载状态
const isLoading = ref(false);

// 我的收藏分页状态
const starredCurrentPage = ref(1);
const starredPageSize = ref(10);

// 所有多维表格分页状态
const allCurrentPage = ref(1);
const allPageSize = ref(10);

// 分享给我的分页状态
const sharedWithMeCurrentPage = ref(1);
const sharedWithMePageSize = ref(10);

// 我分享的分页状态
const sharedByMeCurrentPage = ref(1);
const sharedByMePageSize = ref(10);

// 创建对话框显示状态
const createDialogVisible = ref(false);

// 编辑对话框显示状态
const editDialogVisible = ref(false);

// 预览对话框显示状态
const previewDialogVisible = ref(false);
const previewTemplate = ref<TableTemplate | null>(null);
const activePreviewTables = ref<string[]>([]);

// 模板搜索状态
const templateSearchQuery = ref("");

// 新建选择对话框显示状态
const createChoiceDialogVisible = ref(false);

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
  "📊",
  "📋",
  "📁",
  "📝",
  "📅",
  "💼",
  "📈",
  "🎯",
  "✅",
  "📌",
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

// 复制加载状态
const copyLoadingMap = ref<Map<string, boolean>>(new Map());

// 判断是否正在复制
const isCopyLoading = (baseId: string) => {
  return copyLoadingMap.value.get(baseId) || false;
};

// ========== 搜索功能（从 AppHeader 接收） ==========
const searchQuery = ref("");

// 高亮匹配文本
const escapeHtml = (str: string): string => {
  return str
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
};

const highlightText = (text: string, query: string): string => {
  if (!query.trim()) return escapeHtml(text);
  const escaped = escapeHtml(text);
  const regex = new RegExp(`(${escapeRegExp(query)})`, "gi");
  return escaped.replace(regex, '<mark class="search-highlight">$1</mark>');
};

// 转义正则特殊字符
const escapeRegExp = (string: string): string => {
  return string.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
};

// 收藏的 Base 列表（带搜索过滤）
const starredBases = computed(() => {
  const query = searchQuery.value.trim().toLowerCase();
  return baseStore.bases
    .filter((base) => base.is_starred)
    .filter((base) => {
      if (!query) return true;
      return base.name.toLowerCase().includes(query);
    })
    .sort(
      (a, b) =>
        new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
    );
});

// 所有 Base 列表（带搜索过滤）
const allBases = computed(() => {
  const query = searchQuery.value.trim().toLowerCase();
  return baseStore.bases
    .filter((base) => {
      if (!query) return true;
      return base.name.toLowerCase().includes(query);
    })
    .sort(
      (a, b) =>
        new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
    );
});

// 是否有收藏的项目
const hasStarredBases = computed(() => starredBases.value.length > 0);

// 是否有搜索结果
const hasSearchResults = computed(() => {
  return starredBases.value.length > 0 || allBases.value.length > 0;
});

// 过滤后的模板列表（仅按名称搜索）
const filteredTemplates = computed(() => {
  const query = templateSearchQuery.value.trim().toLowerCase();
  if (!query) return tableTemplates;
  return tableTemplates.filter((template) =>
    template.name.toLowerCase().includes(query),
  );
});

// 限制显示的收藏卡片数量（最多8个）
const displayedStarredBases = computed(() => {
  return starredBases.value.slice(0, 8);
});

// 限制显示的所有卡片数量（最多15个，不包括创建卡片）
const displayedAllBases = computed(() => {
  return allBases.value.slice(0, 15);
});

// 我的收藏分页数据
const paginatedStarredBases = computed(() => {
  const start = (starredCurrentPage.value - 1) * starredPageSize.value;
  const end = start + starredPageSize.value;
  return starredBases.value.slice(start, end);
});

// 所有多维表格分页数据
const paginatedAllBases = computed(() => {
  const start = (allCurrentPage.value - 1) * allPageSize.value;
  const end = start + allPageSize.value;
  return allBases.value.slice(start, end);
});

// 日期格式化
const formatDate = (timestamp: number): string => {
  const date = new Date(timestamp);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));

  if (days === 0) {
    const hours = Math.floor(diff / (1000 * 60 * 60));
    if (hours === 0) {
      const minutes = Math.floor(diff / (1000 * 60));
      return minutes <= 0 ? "刚刚" : `${minutes}分钟前`;
    }
    return `${hours}小时前`;
  } else if (days === 1) {
    return "昨天";
  } else if (days < 7) {
    return `${days}天前`;
  } else if (days < 30) {
    return `${Math.floor(days / 7)}周前`;
  } else {
    return date.toLocaleDateString("zh-CN", {
      year: "numeric",
      month: "2-digit",
      day: "2-digit",
    });
  }
};

// 我的收藏分页事件
const handleStarredSizeChange = (size: number) => {
  starredPageSize.value = size;
  starredCurrentPage.value = 1;
};

const handleStarredPageChange = (page: number) => {
  starredCurrentPage.value = page;
};

// 所有多维表格分页事件
const handleAllSizeChange = (size: number) => {
  allPageSize.value = size;
  allCurrentPage.value = 1;
};

const handleAllPageChange = (page: number) => {
  allCurrentPage.value = page;
};

// 分享给我的分页事件
const handleSharedWithMeSizeChange = (size: number) => {
  sharedWithMePageSize.value = size;
  sharedWithMeCurrentPage.value = 1;
};

const handleSharedWithMePageChange = (page: number) => {
  sharedWithMeCurrentPage.value = page;
};

// 我分享的分页事件
const handleSharedByMeSizeChange = (size: number) => {
  sharedByMePageSize.value = size;
  sharedByMeCurrentPage.value = 1;
};

const handleSharedByMePageChange = (page: number) => {
  sharedByMeCurrentPage.value = page;
};

// 清空搜索
const clearSearch = () => {
  searchQuery.value = "";
  // 通知 AppHeader 清空搜索框
  window.dispatchEvent(new CustomEvent("home-search-clear"));
};

onMounted(async () => {
  await baseStore.fetchBases();

  // 监听来自 AppHeader 的搜索事件
  window.addEventListener("home-search-query-change", ((event: CustomEvent) => {
    searchQuery.value = event.detail.query;
  }) as EventListener);
});

// 加载分享给我的数据
async function loadSharedWithMe() {
  sharingLoading.value = true;
  try {
    sharedWithMeBases.value = await baseStore.fetchSharedWithMe();
  } catch (error) {
    console.error("加载分享给我的数据失败:", error);
  } finally {
    sharingLoading.value = false;
  }
}

// 加载我创建的分享数据
async function loadSharedByMe() {
  sharingLoading.value = true;
  try {
    sharedByMeShares.value = await baseStore.fetchSharedByMe();
  } catch (error) {
    console.error("加载我创建的分享数据失败:", error);
  } finally {
    sharingLoading.value = false;
  }
}

// 监听导航变化，加载对应数据
watch(currentNav, (newNav) => {
  if (newNav === "shares") {
    loadSharedWithMe();
    loadSharedByMe();
  }
});

// 格式化日期（用于分享视图）
function formatShareDate(dateString: string) {
  const date = new Date(dateString);
  const now = new Date();
  const diff = now.getTime() - date.getTime();
  const days = Math.floor(diff / (1000 * 60 * 60 * 24));

  if (days === 0) return "今天";
  if (days === 1) return "昨天";
  if (days < 7) return `${days}天前`;
  if (days < 30) return `${Math.floor(days / 7)}周前`;
  if (days < 365) return `${Math.floor(days / 30)}个月前`;
  return `${Math.floor(days / 365)}年前`;
}

// 复制分享链接
function copyShareLink(shareToken: string) {
  const baseUrl = window.location.origin;
  const shareUrl = `${baseUrl}/#/share/${shareToken}`;
  navigator.clipboard
    .writeText(shareUrl)
    .then(() => {
      ElMessage.success("链接已复制到剪贴板");
    })
    .catch(() => {
      ElMessage.error("复制失败，请手动复制");
    });
}

// 删除分享
async function handleDeleteShare(shareId: string) {
  try {
    await ElMessageBox.confirm(
      "确定要删除此分享链接吗？删除后将无法通过该链接访问。",
      "确认删除",
      {
        confirmButtonText: "确定",
        cancelButtonText: "取消",
        type: "warning",
      },
    );

    await baseStore.deleteShare(shareId);
    await loadSharedByMe();
    ElMessage.success("分享链接已删除");
  } catch (error) {
    if (error !== "cancel") {
      console.error("删除分享失败:", error);
    }
  }
}

function goToBase(id: string) {
  const baseUrl = window.location.origin;
  window.open(`${baseUrl}/#/base/${id}`, "_blank");
}

function goToSettings() {
  router.push("/settings");
}

function openCreateChoiceDialog() {
  createChoiceDialogVisible.value = true;
}

function closeCreateChoiceDialog() {
  createChoiceDialogVisible.value = false;
}

function handleCreateBlankBase() {
  closeCreateChoiceDialog();
  openCreateDialog();
}

function handleCreateFromTemplate() {
  closeCreateChoiceDialog();
  currentNav.value = "templates";
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
      },
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
  await baseStore.toggleStar(base.id);
  ElMessage.success("已收藏");
}

// 处理取消收藏
async function handleUnstarBase(base: Base, event: Event) {
  event.stopPropagation();
  unstarLoadingMap.value.set(base.id, true);

  try {
    await baseStore.toggleStar(base.id);
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

// 统一的收藏/取消收藏切换函数
async function handleToggleStar(base: Base, event: Event) {
  event.stopPropagation();
  unstarLoadingMap.value.set(base.id, true);

  try {
    await baseStore.toggleStar(base.id);
    ElMessage.success(base.is_starred ? "已取消收藏" : "已收藏");
  } catch (error) {
    ElMessage.error("操作失败");
  } finally {
    unstarLoadingMap.value.set(base.id, false);
  }
}

// 阻止事件冒泡
function stopPropagation(event: Event) {
  event.stopPropagation();
}

// 获取模板加载状态
function isTemplateLoading(templateId: string): boolean {
  return templateLoadingMap.value.get(templateId) || false;
}

// 获取字段类型颜色
function getFieldTypeColor(type: string): string {
  const colors: Record<string, string> = {
    text: "#3B82F6",
    number: "#10B981",
    date: "#F59E0B",
    single_select: "#8B5CF6",
    multi_select: "#8B5CF6",
    checkbox: "#EF4444",
    attachment: "#06B6D4",
    member: "#EC4899",
    rating: "#F59E0B",
    progress: "#10B981",
    phone: "#3B82F6",
    email: "#10B981",
    url: "#8B5CF6",
    formula: "#EF4444",
    link: "#06B6D4",
    lookup: "#EC4899",
    createdBy: "#3B82F6",
    createdTime: "#10B981",
    updatedBy: "#8B5CF6",
    updatedTime: "#EF4444",
    autoNumber: "#06B6D4",
  };
  return colors[type] || "#6B7280";
}

// 获取字段类型名称（使用导入的函数）
function getFieldTypeName(type: string): string {
  return getFieldTypeLabel(type);
}

// 打开预览对话框
function openPreview(template: TableTemplate) {
  previewTemplate.value = template;
  previewDialogVisible.value = true;
}

// 关闭预览对话框
function closePreview() {
  previewDialogVisible.value = false;
  previewTemplate.value = null;
}

// 从模板创建 base
async function handleUseTemplate(template: TableTemplate) {
  templateLoadingMap.value.set(template.id, true);

  // 显示进度提示
  const loadingMsg = ElMessage({
    message: "正在创建多维表...",
    type: "info",
    duration: 0, // 不自动关闭
    icon: "Loading",
  });

  let currentMsg = loadingMsg;

  try {
    const base = await templateService.createBaseFromTemplate(
      template,
      (progress) => {
        // 更新进度提示
        if (currentMsg) {
          currentMsg.close();
        }
        currentMsg = ElMessage({
          message: `${progress.message} (${progress.progress}%)`,
          type: "info",
          duration: 0,
          icon: "Loading",
        });
      },
    );

    // 创建成功，关闭进度提示
    if (currentMsg) {
      currentMsg.close();
    }

    await baseStore.fetchBases();
    ElMessage.success(`已成功使用"${template.name}"模板创建多维表格`);
    closePreview();
    goToBase(base.id);
  } catch (error) {
    console.error("Failed to create base from template:", error);
    // 创建失败，关闭进度提示
    if (currentMsg) {
      currentMsg.close();
    }
    ElMessage.error("创建失败，请稍后重试");
  } finally {
    templateLoadingMap.value.set(template.id, false);
  }
}

// 处理复制 Base
async function handleCopyBase(base: Base, event: Event) {
  event.stopPropagation();

  // 确认对话框
  try {
    await ElMessageBox.confirm(
      `确定要复制"${base.name}"吗？将创建一个包含所有数据和配置的副本。`,
      "复制确认",
      {
        confirmButtonText: "复制",
        cancelButtonText: "取消",
        type: "info",
      }
    );
  } catch {
    // 用户取消
    return;
  }

  // 设置加载状态
  copyLoadingMap.value.set(base.id, true);

  // 显示进度提示
  const loadingMsg = ElMessage({
    message: "正在复制多维表格...",
    type: "info",
    duration: 0,
    icon: "Loading",
  });

  try {
    const newBase = await copyBase(base.id);

    // 关闭进度提示
    loadingMsg.close();

    // 刷新列表
    await baseStore.fetchBases();

    ElMessage.success(`复制成功：${newBase.name}`);
  } catch (error) {
    console.error("Failed to copy base:", error);
    loadingMsg.close();
    ElMessage.error("复制失败，请稍后重试");
  } finally {
    copyLoadingMap.value.set(base.id, false);
  }
}
</script>

<template>
  <div class="home-page">
    <!-- 顶部导航 Tab -->
    <div class="home-nav-tabs">
      <div
        class="nav-tab-item"
        :class="{ active: currentNav === 'home' }"
        @click="currentNav = 'home'">
        <el-icon><HomeFilled /></el-icon>
        <span>首页</span>
      </div>
      <div
        class="nav-tab-item"
        :class="{ active: currentNav === 'all' }"
        @click="currentNav = 'all'">
        <el-icon><Grid /></el-icon>
        <span>全部</span>
      </div>
      <div
        class="nav-tab-item"
        :class="{ active: currentNav === 'templates' }"
        @click="currentNav = 'templates'">
        <el-icon><Document /></el-icon>
        <span>模板</span>
      </div>
      <div
        class="nav-tab-item"
        :class="{ active: currentNav === 'shares' }"
        @click="currentNav = 'shares'">
        <el-icon><Share /></el-icon>
        <span>分享</span>
      </div>
      <!-- 右侧操作区 -->
      <div class="header-right-section">
        <div class="header-actions">
          <el-button
            type="primary"
            class="create-btn"
            @click="openCreateChoiceDialog">
            <el-icon><Plus /></el-icon>
            <span>新建</span>
          </el-button>
        </div>
      </div>
    </div>

    <div class="home-content-wrapper">
      <!-- 顶部搜索栏 -->
      <!-- <header class="home-header">
        <div class="header-actions">
          <el-button
            type="primary"
            class="create-btn"
            @click="openCreateChoiceDialog">
            <el-icon><Plus /></el-icon>
            <span>新建</span>
          </el-button>
          <el-button class="settings-btn" @click="goToSettings">
            <el-icon><Setting /></el-icon>
          </el-button>
        </div>
      </header> -->

      <main
        class="home-content"
        style="overflow: auto; height: calc(100vh - 100px)">
        <!-- 首页视图 -->
        <div v-if="currentNav === 'home'" class="home-view">
          <!-- 空状态 -->
          <div v-if="baseStore.bases.length === 0" class="empty-state">
            <div class="empty-illustration">
              <svg viewBox="0 0 200 200" fill="none">
                <rect
                  x="40"
                  y="60"
                  width="120"
                  height="100"
                  rx="8"
                  fill="#E0E7FF" />
                <rect
                  x="60"
                  y="80"
                  width="80"
                  height="8"
                  rx="4"
                  fill="#6366F1" />
                <rect
                  x="60"
                  y="100"
                  width="60"
                  height="8"
                  rx="4"
                  fill="#A5B4FC" />
                <rect
                  x="60"
                  y="120"
                  width="70"
                  height="8"
                  rx="4"
                  fill="#A5B4FC" />
              </svg>
            </div>
            <h3>开始创建您的第一个多维表格</h3>
            <p class="empty-desc">多维表格让数据管理更简单、更高效</p>
            <el-button
              type="primary"
              size="large"
              @click="openCreateChoiceDialog">
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
                <el-button
                  v-if="starredBases.length > 8"
                  link
                  type="primary"
                  class="view-more-btn"
                  @click="currentNav = 'all'">
                  查看更多……
                </el-button>
              </div>

              <div class="card-grid">
                <div
                  v-for="base in displayedStarredBases"
                  :key="base.id"
                  class="base-card starred"
                  @click="goToBase(base.id)">
                  <div class="card-main">
                    <div
                      class="card-icon"
                      :style="{ backgroundColor: base.color || '#3B82F6' }">
                      {{ base.icon || "📊" }}
                    </div>
                    <div class="card-info">
                      <h3
                        class="card-name"
                        v-html="highlightText(base.name, searchQuery)" />
                      <p class="card-desc">
                        {{ base.description || "暂无描述" }}
                      </p>
                    </div>
                  </div>
                  <div class="card-footer">
                    <span class="update-time">
                      最后修改时间：{{
                        new Date(base.updated_at).toLocaleString("zh-CN", {
                          year: "numeric",
                          month: "2-digit",
                          day: "2-digit",
                          hour: "2-digit",
                          minute: "2-digit",
                        })
                      }}
                    </span>
                    <div class="card-actions" @click.stop="stopPropagation">
                      <el-button
                        link
                        type="warning"
                        :loading="isUnstarLoading(base.id)"
                        @click="handleUnstarBase(base, $event)">
                        <el-icon><StarFilled /></el-icon>
                      </el-button>
                      <el-button
                        link
                        :loading="isCopyLoading(base.id)"
                        @click="handleCopyBase(base, $event)"
                        title="复制">
                        <el-icon><DocumentCopy /></el-icon>
                      </el-button>
                      <el-dropdown
                        v-if="isBaseOwner(base)"
                        trigger="click"
                        @command="
                          (cmd) => {
                            if (cmd === 'edit') openEditDialog(base);
                            else if (cmd === 'delete') handleDeleteBase(base);
                          }
                        ">
                        <el-button link>
                          <el-icon><MoreFilled /></el-icon>
                        </el-button>
                        <template #dropdown>
                          <el-dropdown-menu>
                            <el-dropdown-item command="edit">
                              <el-icon><Edit /></el-icon>编辑
                            </el-dropdown-item>
                            <el-dropdown-item
                              divided
                              command="delete"
                              class="delete-item">
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
                <el-button
                  v-if="allBases.length > 15"
                  link
                  type="primary"
                  class="view-more-btn"
                  @click="currentNav = 'all'">
                  查看更多……
                </el-button>
              </div>

              <div class="card-grid">
                <!-- 创建卡片 -->
                <div
                  class="base-card create-card"
                  @click="openCreateChoiceDialog">
                  <div class="create-content">
                    <div class="create-icon">
                      <el-icon :size="24"><Plus /></el-icon>
                    </div>
                    <span>创建多维表格</span>
                  </div>
                </div>

                <!-- Base 卡片 -->
                <div
                  v-for="base in displayedAllBases"
                  :key="base.id"
                  class="base-card"
                  :class="{ starred: base.is_starred }"
                  @click="goToBase(base.id)">
                  <div class="card-main">
                    <div
                      class="card-icon"
                      :style="{ backgroundColor: base.color || '#3B82F6' }">
                      {{ base.icon || "📊" }}
                    </div>
                    <div class="card-info">
                      <h3
                        class="card-name"
                        v-html="highlightText(base.name, searchQuery)" />
                      <p class="card-desc">
                        {{ base.description || "暂无描述" }}
                      </p>
                    </div>
                  </div>
                  <div class="card-footer">
                    <span class="update-time">
                      最后修改时间：{{
                        new Date(base.updated_at).toLocaleString("zh-CN", {
                          year: "numeric",
                          month: "2-digit",
                          day: "2-digit",
                          hour: "2-digit",
                          minute: "2-digit",
                        })
                      }}
                    </span>
                    <div class="card-actions" @click.stop="stopPropagation">
                      <el-button
                        v-if="!base.is_starred"
                        link
                        @click="handleStarBase(base, $event)">
                        <el-icon><Star /></el-icon>
                      </el-button>
                      <el-button
                        v-else
                        link
                        type="warning"
                        @click="handleUnstarBase(base, $event)">
                        <el-icon><StarFilled /></el-icon>
                      </el-button>
                      <el-button
                        link
                        :loading="isCopyLoading(base.id)"
                        @click="handleCopyBase(base, $event)"
                        title="复制">
                        <el-icon><DocumentCopy /></el-icon>
                      </el-button>
                      <el-dropdown
                        v-if="isBaseOwner(base)"
                        trigger="click"
                        @command="
                          (cmd) => {
                            if (cmd === 'edit') openEditDialog(base);
                            else if (cmd === 'delete') handleDeleteBase(base);
                          }
                        ">
                        <el-button link>
                          <el-icon><MoreFilled /></el-icon>
                        </el-button>
                        <template #dropdown>
                          <el-dropdown-menu>
                            <el-dropdown-item command="edit">
                              <el-icon><Edit /></el-icon>编辑
                            </el-dropdown-item>
                            <el-dropdown-item
                              divided
                              command="delete"
                              class="delete-item">
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
        </div>

        <!-- 模板视图 -->
        <div v-else-if="currentNav === 'templates'" class="templates-view">
          <div class="templates-header">
            <div class="templates-header-top">
              <div>
                <h2 class="view-title">选择模板</h2>
                <p class="view-desc">选择一个预置模板快速开始您的多维表格</p>
              </div>
              <div class="template-search-wrapper">
                <div class="template-search-box">
                  <el-icon class="search-icon"><Search /></el-icon>
                  <input
                    v-model="templateSearchQuery"
                    type="text"
                    class="template-search-input"
                    placeholder="搜索模板..." />
                  <el-icon
                    v-if="templateSearchQuery"
                    class="search-clear"
                    @click="templateSearchQuery = ''">
                    <CircleClose />
                  </el-icon>
                </div>
              </div>
            </div>
          </div>
          <div class="templates-grid">
            <div
              v-for="template in filteredTemplates"
              :key="template.id"
              class="template-card">
              <div class="template-main">
                <div
                  class="template-icon"
                  :style="{ backgroundColor: template.color }">
                  {{ template.icon }}
                </div>
                <div class="template-info">
                  <h3 class="template-name">{{ template.name }}</h3>
                  <p class="template-desc">{{ template.description }}</p>
                  <span class="template-category">{{ template.category }}</span>
                </div>
              </div>
              <div class="template-footer">
                <el-button size="small" @click="openPreview(template)">
                  预览
                </el-button>
                <el-button
                  type="primary"
                  size="small"
                  :loading="isTemplateLoading(template.id)"
                  @click="handleUseTemplate(template)">
                  使用模板
                </el-button>
              </div>
            </div>
          </div>
        </div>

        <!-- 全部多维表视图 -->
        <div v-else-if="currentNav === 'all'" class="all-bases-view">
          <!-- <div class="all-bases-header">
              <h2 class="view-title">多维表管理</h2>
            </div> -->

          <div class="tabs-container">
            <div class="tabs-header">
              <div
                class="tab-item"
                :class="{ active: activeTab === 'starred' }"
                @click="activeTab = 'starred'">
                <el-icon><StarFilled /></el-icon>
                <span>我的收藏</span>
                <span class="tab-count">{{ starredBases.length }}</span>
              </div>
              <div
                class="tab-item"
                :class="{ active: activeTab === 'all' }"
                @click="activeTab = 'all'">
                <el-icon><Grid /></el-icon>
                <span>所有多维表格</span>
                <span class="tab-count">{{ allBases.length }}</span>
              </div>
            </div>

            <div class="tabs-content">
              <!-- 加载状态 -->
              <div v-if="isLoading" class="loading-state">
                <el-icon class="loading-icon" :size="32"><Loading /></el-icon>
                <p>正在加载数据...</p>
              </div>

              <!-- 我的收藏页签 -->
              <div v-else-if="activeTab === 'starred'" class="tab-panel">
                <div v-if="starredBases.length === 0" class="empty-state">
                  <el-icon :size="48" class="empty-icon"><Star /></el-icon>
                  <h3>暂无收藏的表格</h3>
                  <p>在首页点击星标图标收藏您常用的表格</p>
                </div>
                <div v-else class="table-list-container">
                  <div class="table-list">
                    <div
                      v-for="base in paginatedStarredBases"
                      :key="base.id"
                      class="table-list-item"
                      @click="goToBase(base.id)">
                      <div
                        class="item-icon"
                        :style="{ backgroundColor: base.color || '#3B82F6' }">
                        {{ base.icon || "📊" }}
                      </div>
                      <div class="item-info">
                        <h4 class="item-name">{{ base.name }}</h4>
                        <p class="item-desc">
                          {{ base.description || "暂无描述" }}
                        </p>
                      </div>
                      <div class="item-meta">
                        <span class="update-time">
                          修改于 {{ formatDate(base.updated_at) }}
                        </span>
                      </div>
                      <div class="item-actions" @click.stop>
                        <el-button
                          link
                          type="warning"
                          :loading="isUnstarLoading(base.id)"
                          @click="handleUnstarBase(base, $event)">
                          <el-icon><StarFilled /></el-icon>
                        </el-button>
                        <el-button
                          link
                          :loading="isCopyLoading(base.id)"
                          @click="handleCopyBase(base, $event)"
                          title="复制">
                          <el-icon><DocumentCopy /></el-icon>
                        </el-button>
                        <el-dropdown
                          v-if="isBaseOwner(base)"
                          trigger="click"
                          @command="
                            (cmd) => {
                              if (cmd === 'edit') openEditDialog(base);
                              else if (cmd === 'delete') handleDeleteBase(base);
                            }
                          ">
                          <el-button link>
                            <el-icon><MoreFilled /></el-icon>
                          </el-button>
                          <template #dropdown>
                            <el-dropdown-menu>
                              <el-dropdown-item command="edit">
                                <el-icon><Edit /></el-icon>编辑
                              </el-dropdown-item>
                              <el-dropdown-item
                                divided
                                command="delete"
                                class="delete-item">
                                <el-icon><Delete /></el-icon>删除
                              </el-dropdown-item>
                            </el-dropdown-menu>
                          </template>
                        </el-dropdown>
                      </div>
                    </div>
                  </div>

                  <!-- 分页 -->
                  <div class="pagination-container">
                    <div class="pagination-left">
                      <span class="pagination-total"
                        >共 {{ starredBases.length }} 条</span
                      >
                      <el-select
                        v-model="starredPageSize"
                        class="page-size-select"
                        size="small">
                        <el-option :label="'10条/页'" :value="10" />
                        <el-option :label="'20条/页'" :value="20" />
                        <el-option :label="'50条/页'" :value="50" />
                        <el-option :label="'100条/页'" :value="100" />
                      </el-select>
                    </div>
                    <el-pagination
                      v-model:current-page="starredCurrentPage"
                      v-model:page-size="starredPageSize"
                      :total="starredBases.length"
                      :page-sizes="[10, 20, 50, 100]"
                      layout="prev, pager, next, jumper"
                      background
                      @size-change="handleStarredSizeChange"
                      @current-change="handleStarredPageChange" />
                  </div>
                </div>
              </div>

              <!-- 所有多维表格页签 -->
              <div v-else class="tab-panel">
                <div v-if="allBases.length === 0" class="empty-state">
                  <el-icon :size="48" class="empty-icon"><Grid /></el-icon>
                  <h3>暂无多维表格</h3>
                  <p>点击右上角"新建"按钮创建您的第一个表格</p>
                </div>
                <div v-else class="table-list-container">
                  <div class="table-list">
                    <div
                      v-for="base in paginatedAllBases"
                      :key="base.id"
                      class="table-list-item"
                      @click="goToBase(base.id)">
                      <div
                        class="item-icon"
                        :style="{ backgroundColor: base.color || '#3B82F6' }">
                        {{ base.icon || "📊" }}
                      </div>
                      <div class="item-info">
                        <h4 class="item-name">{{ base.name }}</h4>
                        <p class="item-desc">
                          {{ base.description || "暂无描述" }}
                        </p>
                      </div>
                      <div class="item-meta">
                        <span class="update-time">
                          修改于 {{ formatDate(base.updated_at) }}
                        </span>
                      </div>
                      <div class="item-actions" @click.stop>
                        <el-button
                          v-if="!base.is_starred"
                          link
                          @click="handleStarBase(base, $event)">
                          <el-icon><Star /></el-icon>
                        </el-button>
                        <el-button
                          v-else
                          link
                          type="warning"
                          @click="handleUnstarBase(base, $event)">
                          <el-icon><StarFilled /></el-icon>
                        </el-button>
                        <el-button
                          link
                          :loading="isCopyLoading(base.id)"
                          @click="handleCopyBase(base, $event)"
                          title="复制">
                          <el-icon><DocumentCopy /></el-icon>
                        </el-button>
                        <el-dropdown
                          v-if="isBaseOwner(base)"
                          trigger="click"
                          @command="
                            (cmd) => {
                              if (cmd === 'edit') openEditDialog(base);
                              else if (cmd === 'delete') handleDeleteBase(base);
                            }
                          ">
                          <el-button link>
                            <el-icon><MoreFilled /></el-icon>
                          </el-button>
                          <template #dropdown>
                            <el-dropdown-menu>
                              <el-dropdown-item command="edit">
                                <el-icon><Edit /></el-icon>编辑
                              </el-dropdown-item>
                              <el-dropdown-item
                                divided
                                command="delete"
                                class="delete-item">
                                <el-icon><Delete /></el-icon>删除
                              </el-dropdown-item>
                            </el-dropdown-menu>
                          </template>
                        </el-dropdown>
                      </div>
                    </div>
                  </div>

                  <!-- 分页 -->
                  <div class="pagination-container">
                    <div class="pagination-left">
                      <span class="pagination-total"
                        >共 {{ allBases.length }} 条</span
                      >
                      <el-select
                        v-model="allPageSize"
                        class="page-size-select"
                        size="small">
                        <el-option :label="'10条/页'" :value="10" />
                        <el-option :label="'20条/页'" :value="20" />
                        <el-option :label="'50条/页'" :value="50" />
                        <el-option :label="'100条/页'" :value="100" />
                      </el-select>
                    </div>
                    <el-pagination
                      v-model:current-page="allCurrentPage"
                      v-model:page-size="allPageSize"
                      :total="allBases.length"
                      :page-sizes="[10, 20, 50, 100]"
                      layout="prev, pager, next, jumper"
                      background
                      @size-change="handleAllSizeChange"
                      @current-change="handleAllPageChange" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 分享视图 -->
        <div v-if="currentNav === 'shares'" class="all-bases-view">
          <div class="tabs-container">
            <div class="tabs-header">
              <div
                class="tab-item"
                :class="{ active: shareActiveTab === 'shared-by-me' }"
                @click="shareActiveTab = 'shared-by-me'">
                <el-icon><Share /></el-icon>
                <span>我分享的</span>
                <span class="tab-count">{{ sharedByMeShares.length }}</span>
              </div>
              <div
                class="tab-item"
                :class="{ active: shareActiveTab === 'shared-with-me' }"
                @click="shareActiveTab = 'shared-with-me'">
                <el-icon><Connection /></el-icon>
                <span>分享给我的</span>
                <span class="tab-count">{{ sharedWithMeBases.length }}</span>
              </div>
            </div>

            <div class="tabs-content">
              <!-- 加载状态 -->
              <div v-if="sharingLoading" class="loading-state">
                <el-icon class="loading-icon" :size="32"><Loading /></el-icon>
                <p>正在加载数据...</p>
              </div>

              <!-- 我分享的页签 -->
              <div
                v-else-if="shareActiveTab === 'shared-by-me'"
                class="tab-panel">
                <div v-if="sharedByMeShares.length === 0" class="empty-state">
                  <el-icon :size="48" class="empty-icon"><Share /></el-icon>
                  <h3>暂无分享</h3>
                  <p>您还没有创建任何分享链接</p>
                </div>
                <div v-else class="table-list-container">
                  <div class="table-list">
                    <div
                      v-for="share in sharedByMeShares"
                      :key="share.id"
                      class="table-list-item"
                      @click="goToBase(share.base.id)">
                      <div
                        class="item-icon"
                        :style="{
                          backgroundColor: share.base?.color || '#3B82F6',
                        }">
                        {{ share.base?.icon || "📊" }}
                      </div>
                      <div class="item-info">
                        <h4 class="item-name">{{ share.base?.name }}</h4>
                        <div class="share-meta">
                          <el-tag
                            :type="
                              share.permission === 'edit' ? 'warning' : 'info'
                            "
                            size="small">
                            {{
                              share.permission === "edit" ? "可编辑" : "仅查看"
                            }}
                          </el-tag>
                          <span class="access-count"
                            >访问 {{ share.access_count }} 次</span
                          >
                          <span class="share-time"
                            >创建于
                            {{ formatShareDate(share.created_at) }}</span
                          >
                        </div>
                      </div>
                      <div class="item-meta">
                        <span class="update-time">
                          更新于 {{ formatShareDate(share.updated_at) }}
                        </span>
                      </div>
                      <div class="item-actions" @click.stop>
                        <el-tooltip
                          content="复制链接"
                          placement="top"
                          :show-after="200">
                          <el-button
                            link
                            type="primary"
                            class="action-btn"
                            @click.stop="copyShareLink(share.share_token)">
                            <el-icon><DocumentCopy /></el-icon>
                          </el-button>
                        </el-tooltip>
                        <el-tooltip
                          content="删除分享"
                          placement="top"
                          :show-after="200">
                          <el-button
                            link
                            type="danger"
                            class="action-btn"
                            @click.stop="handleDeleteShare(share.id)">
                            <el-icon><Delete /></el-icon>
                          </el-button>
                        </el-tooltip>
                      </div>
                    </div>
                  </div>

                  <!-- 分页 -->
                  <div class="pagination-container">
                    <div class="pagination-left">
                      <span class="pagination-total"
                        >共 {{ sharedByMeShares.length }} 条</span
                      >
                      <el-select
                        v-model="sharedByMePageSize"
                        class="page-size-select"
                        size="small">
                        <el-option :label="'10 条/页'" :value="10" />
                        <el-option :label="'20 条/页'" :value="20" />
                        <el-option :label="'50 条/页'" :value="50" />
                        <el-option :label="'100 条/页'" :value="100" />
                      </el-select>
                    </div>
                    <el-pagination
                      v-model:current-page="sharedByMeCurrentPage"
                      v-model:page-size="sharedByMePageSize"
                      :total="sharedByMeShares.length"
                      :page-sizes="[10, 20, 50, 100]"
                      layout="prev, pager, next, jumper"
                      background
                      @size-change="handleSharedByMeSizeChange"
                      @current-change="handleSharedByMePageChange" />
                  </div>
                </div>
              </div>

              <!-- 分享给我的页签 -->
              <div v-else class="tab-panel">
                <div v-if="sharedWithMeBases.length === 0" class="empty-state">
                  <el-icon :size="48" class="empty-icon"
                    ><Connection
                  /></el-icon>
                  <h3>暂无分享</h3>
                  <p>还没有其他用户分享给您多维表格</p>
                </div>
                <div v-else class="table-list-container">
                  <div class="table-list">
                    <div
                      v-for="base in sharedWithMeBases"
                      :key="base.id"
                      class="table-list-item"
                      @click="goToBase(base.id)">
                      <div
                        class="item-icon"
                        :style="{ backgroundColor: base.color || '#3B82F6' }">
                        {{ base.icon || "📊" }}
                      </div>
                      <div class="item-info">
                        <h4 class="item-name">{{ base.name }}</h4>
                        <p class="item-desc">
                          {{ base.description || "暂无描述" }}
                        </p>
                      </div>
                      <div class="item-meta">
                        <span class="update-time">
                          修改于 {{ formatDate(base.updated_at) }}
                        </span>
                      </div>
                      <div class="item-actions" @click.stop>
                        <el-tooltip
                          :content="base.is_starred ? '取消收藏' : '收藏'"
                          placement="top"
                          :show-after="200">
                          <el-button
                            link
                            :type="base.is_starred ? 'warning' : 'info'"
                            class="action-btn"
                            :loading="isUnstarLoading(base.id)"
                            @click="handleToggleStar(base, $event)">
                            <el-icon>
                              <StarFilled v-if="base.is_starred" />
                              <Star v-else />
                            </el-icon>
                          </el-button>
                        </el-tooltip>
                      </div>
                    </div>
                  </div>

                  <!-- 分页 -->
                  <div class="pagination-container">
                    <div class="pagination-left">
                      <span class="pagination-total"
                        >共 {{ sharedWithMeBases.length }} 条</span
                      >
                      <el-select
                        v-model="sharedWithMePageSize"
                        class="page-size-select"
                        size="small">
                        <el-option :label="'10 条/页'" :value="10" />
                        <el-option :label="'20 条/页'" :value="20" />
                        <el-option :label="'50 条/页'" :value="50" />
                        <el-option :label="'100 条/页'" :value="100" />
                      </el-select>
                    </div>
                    <el-pagination
                      v-model:current-page="sharedWithMeCurrentPage"
                      v-model:page-size="sharedWithMePageSize"
                      :total="sharedWithMeBases.length"
                      :page-sizes="[10, 20, 50, 100]"
                      layout="prev, pager, next, jumper"
                      background
                      @size-change="handleSharedWithMeSizeChange"
                      @current-change="handleSharedWithMePageChange" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </main>
    </div>

    <!-- 创建对话框 -->
    <el-dialog
      v-model="createDialogVisible"
      title="创建多维表格"
      width="480px"
      :close-on-click-modal="false"
      class="create-dialog">
      <el-form
        ref="createFormRef"
        :model="createForm"
        :rules="createFormRules"
        label-width="70px"
        class="compact-form">
        <el-form-item label="名称" prop="name">
          <el-input
            v-model="createForm.name"
            placeholder="请输入多维表格名称"
            maxlength="50"
            show-word-limit />
        </el-form-item>

        <el-form-item label="描述">
          <el-input
            v-model="createForm.description"
            type="textarea"
            :rows="2"
            placeholder="请输入描述（可选）"
            maxlength="200"
            show-word-limit />
        </el-form-item>

        <el-form-item label="图标">
          <div class="icon-selector compact">
            <span
              v-for="icon in iconOptions"
              :key="icon"
              class="icon-option"
              :class="{ active: createForm.icon === icon }"
              @click="createForm.icon = icon">
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
              @click="createForm.color = color" />
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
      class="create-dialog">
      <el-form
        ref="editFormRef"
        :model="editForm"
        :rules="editFormRules"
        label-width="70px"
        class="compact-form">
        <el-form-item label="名称" prop="name">
          <el-input
            v-model="editForm.name"
            placeholder="请输入多维表格名称"
            maxlength="50"
            show-word-limit />
        </el-form-item>

        <el-form-item label="描述">
          <el-input
            v-model="editForm.description"
            type="textarea"
            :rows="2"
            placeholder="请输入描述（可选）"
            maxlength="200"
            show-word-limit />
        </el-form-item>

        <el-form-item label="图标">
          <div class="icon-selector compact">
            <span
              v-for="icon in iconOptions"
              :key="icon"
              class="icon-option"
              :class="{ active: editForm.icon === icon }"
              @click="editForm.icon = icon">
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
              @click="editForm.color = color" />
          </div>
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="closeEditDialog">取消</el-button>
        <el-button type="primary" @click="handleEditBase">保存</el-button>
      </template>
    </el-dialog>

    <!-- 新建选择对话框 -->
    <el-dialog
      v-model="createChoiceDialogVisible"
      title="创建多维表格"
      width="560px"
      :close-on-click-modal="false"
      class="create-choice-dialog"
      align-center>
      <div class="create-choice-content">
        <div class="choice-option" @click="handleCreateBlankBase">
          <div class="choice-icon blank-icon">
            <el-icon :size="32"><Plus /></el-icon>
          </div>
          <div class="choice-info">
            <h3 class="choice-title">创建空白多维表</h3>
            <p class="choice-desc">从零开始创建一个全新的空白多维表格</p>
          </div>
          <el-icon class="choice-arrow"><ArrowRight /></el-icon>
        </div>
        <div class="choice-option" @click="handleCreateFromTemplate">
          <div class="choice-icon template-icon">
            <el-icon :size="32"><DocumentCopy /></el-icon>
          </div>
          <div class="choice-info">
            <h3 class="choice-title">从模板创建</h3>
            <p class="choice-desc">选择系统提供的预置模板快速开始</p>
          </div>
          <el-icon class="choice-arrow"><ArrowRight /></el-icon>
        </div>
      </div>
    </el-dialog>

    <!-- 预览对话框 -->
    <el-dialog
      v-model="previewDialogVisible"
      :title="previewTemplate?.name"
      width="800px"
      :close-on-click-modal="false"
      class="preview-dialog">
      <div v-if="previewTemplate" class="preview-content">
        <!-- 模板基本信息 -->
        <div class="preview-header">
          <div
            class="preview-icon"
            :style="{ backgroundColor: previewTemplate.color }">
            {{ previewTemplate.icon }}
          </div>
          <div class="preview-info">
            <h3 class="preview-title">{{ previewTemplate.name }}</h3>
            <p class="preview-desc">{{ previewTemplate.description }}</p>
            <span class="preview-category">{{ previewTemplate.category }}</span>
          </div>
        </div>

        <!-- 模板包含的数据表 -->
        <div class="preview-section">
          <h4 class="section-title">包含的数据表</h4>
          <el-collapse v-model="activePreviewTables" accordion>
            <el-collapse-item
              v-for="table in previewTemplate.tables"
              :key="table.id"
              :name="table.id"
              :title="table.name">
              <div class="table-preview">
                <p class="table-desc">{{ table.description || "暂无描述" }}</p>
                <h5 class="fields-title">字段列表</h5>
                <div class="fields-grid">
                  <div
                    v-for="field in table.fields"
                    :key="field.id"
                    class="field-card">
                    <div
                      class="field-icon"
                      :style="{
                        backgroundColor: getFieldTypeColor(field.type),
                      }">
                      {{ getFieldTypeIcon(field.type) }}
                    </div>
                    <div class="field-info">
                      <div class="field-name">{{ field.name }}</div>
                      <div class="field-type">
                        {{ getFieldTypeName(field.type) }}
                      </div>
                    </div>
                  </div>
                </div>
                <div
                  v-if="table.sampleData && table.sampleData.length > 0"
                  class="sample-data">
                  <h5 class="sample-title">示例数据</h5>
                  <el-table
                    :data="table.sampleData"
                    style="width: 100%"
                    size="small"
                    border>
                    <el-table-column
                      v-for="field in table.fields"
                      :key="field.id"
                      :prop="field.id"
                      :label="field.name"
                      show-overflow-tooltip />
                  </el-table>
                </div>
              </div>
            </el-collapse-item>
          </el-collapse>
        </div>
      </div>

      <template #footer>
        <el-button @click="closePreview">关闭</el-button>
        <el-button
          type="primary"
          :loading="isTemplateLoading(previewTemplate?.id || '')"
          @click="previewTemplate && handleUseTemplate(previewTemplate)">
          应用此模板
        </el-button>
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
  HomeFilled,
  Loading,
  Document,
  ArrowRight,
  DocumentCopy,
} from "@element-plus/icons-vue";

export default {
  name: "HomeView",
};
</script>

<style lang="scss" scoped>
// 清新配色变量
$primary: #3b82f6;
$primary-light: #eff6ff;
$success: #10b981;
$warning: #f59e0b;
$danger: #ef4444;
$gray-50: #f9fafb;
$gray-100: #f3f4f6;
$gray-200: #e5e7eb;
$gray-300: #d1d5db;
$gray-400: #9ca3af;
$gray-500: #6b7280;
$gray-600: #4b5563;
$gray-700: #374151;
$gray-800: #1f2937;
$gray-900: #111827;
$star-color: #f59e0b;

.home-page {
  min-height: 100vh;
  background: linear-gradient(180deg, #f9fafb 0%, #ffffff 100%);
}

// 顶部导航 Tab
.home-nav-tabs {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px 32px;
  background: white;
  border-bottom: 1px solid $gray-200;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);

  .nav-tab-item {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 10px 20px;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s ease;
    color: $gray-600;
    font-size: 14px;
    font-weight: 500;
    position: relative;

    .el-icon {
      font-size: 18px;
    }

    &:hover {
      background: $gray-100;
      color: $gray-800;
    }

    &.active {
      background: $primary-light;
      color: $primary;

      // 底部蓝色指示条
      &::after {
        content: "";
        position: absolute;
        bottom: -16px;
        left: 50%;
        transform: translateX(-50%);
        width: 40px;
        height: 3px;
        background: linear-gradient(90deg, $primary 0%, #6366f1 100%);
        border-radius: 2px;
      }
    }
  }
}

// 内容包装器
.home-content-wrapper {
  height: calc(100vh - 120px);
  overflow: hidden;
}

// 主内容区
.home-content {
  height: 100%;
  background: linear-gradient(180deg, #f9fafb 0%, #ffffff 100%);
}

// 顶部搜索栏
.home-header {
  overflow: hidden;
  position: sticky;
  top: 0;
  z-index: 100;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px 32px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid $gray-200;
  gap: 24px;

  .header-search {
    flex: 0 1 480px;
  }

  .header-actions {
    position: absolute;
    right: 32px;
  }
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
    background: linear-gradient(135deg, $primary 0%, #6366f1 100%);
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

// 右侧操作区
.header-right-section {
  display: flex;
  align-items: center;
  gap: 24px;
  margin-left: auto;
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
    background: linear-gradient(135deg, $primary 0%, #6366f1 100%);
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

// 首页视图内容
.home-view {
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
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 16px;

    .view-more-btn {
      font-size: 13px;
      font-weight: 500;
      padding: 4px 8px;
      border-radius: 6px;
      transition: all 0.2s ease;

      &:hover {
        background: rgba($primary, 0.1);
        transform: translateX(2px);
      }

      &:active {
        transform: translateX(0);
      }
    }
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
    box-shadow:
      0 0 0 2px $gray-400,
      0 2px 4px rgba(0, 0, 0, 0.1);
  }
}

// 下拉菜单
:deep(.delete-item) {
  color: $danger;

  &:hover {
    background: rgba($danger, 0.05);
  }
}

// 全部多维表视图
.all-bases-view {
  min-height: calc(100vh - 100px);
  padding: 24px 32px;
  background: linear-gradient(180deg, #f9fafb 0%, #ffffff 100%);

  .all-bases-header {
    margin-bottom: 24px;

    .view-title {
      font-size: 24px;
      font-weight: 600;
      color: $gray-800;
      margin: 0;
    }
  }

  .tabs-container {
    background: white;
    border-radius: 12px;
    border: 1px solid $gray-200;
    box-shadow: 0 1px 3px rgba(0, 0, 0, 0.05);
    overflow: hidden;
  }

  .tabs-header {
    display: flex;
    border-bottom: 1px solid $gray-200;
    background: $gray-50;

    .tab-item {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 16px 24px;
      cursor: pointer;
      transition: all 0.2s ease;
      color: $gray-600;
      font-size: 14px;
      font-weight: 500;
      border-bottom: 2px solid transparent;
      margin-bottom: -1px;

      .el-icon {
        font-size: 16px;
      }

      .tab-count {
        padding: 2px 8px;
        border-radius: 10px;
        font-size: 12px;
        font-weight: 500;
        background: $gray-200;
        color: $gray-600;
      }

      &:hover {
        color: $gray-800;
        background: $gray-100;
      }

      &.active {
        color: $primary;
        border-bottom-color: $primary;
        background: white;

        .tab-count {
          background: $primary-light;
          color: $primary;
        }
      }
    }
  }

  .tabs-content {
    padding: 24px;
    min-height: 400px;
  }

  .loading-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 80px 20px;
    color: $gray-500;

    .loading-icon {
      animation: rotate 1s linear infinite;
      margin-bottom: 16px;
      color: $primary;
    }

    p {
      margin: 0;
      font-size: 14px;
    }
  }

  @keyframes rotate {
    from {
      transform: rotate(0deg);
    }
    to {
      transform: rotate(360deg);
    }
  }

  .empty-state {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 80px 20px;
    text-align: center;

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

    p {
      font-size: 14px;
      color: $gray-500;
      margin: 0;
    }
  }

  .table-list-container {
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .table-list {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .table-list-item {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 16px 20px;
    background: white;
    border: 1px solid $gray-200;
    border-radius: 10px;
    cursor: pointer;
    transition: all 0.2s ease;

    &:hover {
      border-color: $primary;
      box-shadow: 0 2px 8px rgba($primary, 0.1);
      transform: translateY(-1px);
    }

    .item-icon {
      width: 44px;
      height: 44px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 10px;
      font-size: 20px;
      flex-shrink: 0;
    }

    .item-info {
      flex: 1;
      min-width: 0;

      .item-name {
        font-size: 15px;
        font-weight: 600;
        color: $gray-800;
        margin: 0 0 4px;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }

      .item-desc {
        font-size: 13px;
        color: $gray-500;
        margin: 0;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
    }

    .item-meta {
      flex-shrink: 0;

      .update-time {
        font-size: 12px;
        color: $gray-400;
      }
    }

    .item-actions {
      display: flex;
      align-items: center;
      gap: 4px;
      flex-shrink: 0;
      opacity: 1;

      .action-btn {
        padding: 6px;
        border-radius: 6px;
        transition: all 0.2s ease;
        opacity: 0.6;

        &:hover {
          opacity: 1;
          background: rgba($primary, 0.1);
          transform: scale(1.1);
        }

        &:active {
          transform: scale(0.95);
        }

        // 不同类型按钮的悬停高亮效果
        &.el-button--primary:hover {
          background: rgba($primary, 0.15);
          color: $primary;
        }

        &.el-button--warning:hover {
          background: rgba($warning, 0.15);
          color: $warning;
        }

        &.el-button--danger:hover {
          background: rgba($danger, 0.15);
          color: $danger;
        }

        &.el-button--info:hover {
          background: rgba($gray-500, 0.15);
          color: $gray-700;
        }

        // 禁用状态
        &.is-loading,
        &.is-disabled {
          opacity: 0.4;
          cursor: not-allowed;
        }

        .el-icon {
          font-size: 16px;
        }
      }
    }
  }

  .pagination-container {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-top: 16px;
    border-top: 1px solid $gray-100;

    .pagination-left {
      display: flex;
      align-items: center;
      gap: 16px;

      .pagination-total {
        font-size: 13px;
        color: $gray-500;
      }

      .page-size-select {
        width: 100px;
      }
    }
  }
}

// 模板视图
.templates-view {
  min-height: calc(100vh - 100px);
  padding: 24px 32px;
  background: linear-gradient(180deg, #f9fafb 0%, #ffffff 100%);
  max-width: 1200px;
  margin: 0 auto;

  .templates-header {
    margin-bottom: 32px;

    .templates-header-top {
      display: flex;
      justify-content: space-between;
      align-items: flex-start;
      gap: 24px;
      flex-wrap: wrap;
    }

    .view-title {
      font-size: 24px;
      font-weight: 700;
      color: $gray-800;
      margin: 0 0 8px;
    }

    .view-desc {
      font-size: 14px;
      color: $gray-500;
      margin: 0;
    }

    .template-search-wrapper {
      flex-shrink: 0;
      width: 320px;
    }

    .template-search-box {
      position: relative;
      display: flex;
      align-items: center;
      background: white;
      border: 1px solid $gray-200;
      border-radius: 24px;
      padding: 0 16px;
      height: 48px;
      transition: all 0.2s ease;

      &:hover {
        border-color: $gray-300;
      }

      &:focus-within {
        border-color: $primary;
        box-shadow: 0 0 0 3px rgba($primary, 0.1);
      }

      .search-icon {
        color: $gray-400;
        font-size: 18px;
        flex-shrink: 0;
      }

      .template-search-input {
        flex: 1;
        border: none;
        outline: none;
        background: transparent;
        font-size: 14px;
        color: $gray-700;
        padding: 0 12px;

        &::placeholder {
          color: $gray-400;
        }
      }

      .search-clear {
        color: $gray-400;
        cursor: pointer;
        font-size: 16px;
        flex-shrink: 0;
        transition: color 0.2s;

        &:hover {
          color: $gray-600;
        }
      }
    }
  }

  .templates-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
    gap: 20px;
  }

  .template-card {
    background: white;
    border-radius: 12px;
    border: 1px solid $gray-200;
    padding: 20px;
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
    }

    .template-main {
      display: flex;
      gap: 16px;
      margin-bottom: 16px;
    }

    .template-icon {
      width: 56px;
      height: 56px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 12px;
      font-size: 28px;
      flex-shrink: 0;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
    }

    .template-info {
      flex: 1;
      min-width: 0;
      display: flex;
      flex-direction: column;
      gap: 4px;
    }

    .template-name {
      font-size: 16px;
      font-weight: 600;
      color: $gray-800;
      margin: 0;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .template-desc {
      font-size: 13px;
      color: $gray-500;
      margin: 0;
      line-height: 1.4;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }

    .template-category {
      font-size: 11px;
      color: $primary;
      background: $primary-light;
      padding: 2px 8px;
      border-radius: 10px;
      font-weight: 500;
      display: inline-block;
      margin-top: 4px;
      width: fit-content;
    }

    .template-footer {
      padding-top: 12px;
      border-top: 1px solid $gray-100;
      display: flex;
      justify-content: flex-end;
      gap: 8px;
    }
  }
}

// 新建选择对话框样式
.create-choice-dialog {
  :deep(.el-dialog__header) {
    padding: 20px 24px 16px;
    border-bottom: 1px solid $gray-100;

    .el-dialog__title {
      font-size: 18px;
      font-weight: 600;
      color: $gray-800;
    }
  }

  :deep(.el-dialog__body) {
    padding: 24px;
  }

  :deep(.el-dialog__footer) {
    display: none;
  }
}

.create-choice-content {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.choice-option {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 20px;
  background: white;
  border: 2px solid $gray-100;
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);

  &:hover {
    border-color: $primary;
    background: $primary-light;
    transform: translateY(-2px);
    box-shadow: 0 8px 24px rgba($primary, 0.15);

    .choice-arrow {
      color: $primary;
      transform: translateX(4px);
    }
  }

  &:active {
    transform: translateY(0);
  }
}

.choice-icon {
  width: 56px;
  height: 56px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 12px;
  flex-shrink: 0;

  &.blank-icon {
    background: linear-gradient(135deg, $primary 0%, #6366f1 100%);
    color: white;
  }

  &.template-icon {
    background: linear-gradient(135deg, #10b981 0%, #06b6d4 100%);
    color: white;
  }
}

.choice-info {
  flex: 1;
  min-width: 0;
}

.choice-title {
  font-size: 16px;
  font-weight: 600;
  color: $gray-800;
  margin: 0 0 4px;
}

.choice-desc {
  font-size: 13px;
  color: $gray-500;
  margin: 0;
}

.choice-arrow {
  color: $gray-400;
  font-size: 20px;
  transition: all 0.2s ease;
  flex-shrink: 0;
}

// 预览对话框样式
.preview-dialog {
  :deep(.el-dialog__header) {
    padding: 20px 24px 16px;
    border-bottom: 1px solid $gray-100;

    .el-dialog__title {
      font-size: 18px;
      font-weight: 600;
      color: $gray-800;
    }
  }

  :deep(.el-dialog__body) {
    padding: 24px;
    max-height: 60vh;
    overflow-y: auto;
  }

  :deep(.el-dialog__footer) {
    padding: 16px 24px;
    border-top: 1px solid $gray-100;
  }
}

.preview-content {
  .preview-header {
    display: flex;
    gap: 20px;
    margin-bottom: 32px;
    padding-bottom: 24px;
    border-bottom: 1px solid $gray-100;
  }

  .preview-icon {
    width: 72px;
    height: 72px;
    display: flex;
    align-items: center;
    justify-content: center;
    border-radius: 16px;
    font-size: 36px;
    flex-shrink: 0;
    box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  }

  .preview-info {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .preview-title {
    font-size: 22px;
    font-weight: 700;
    color: $gray-800;
    margin: 0;
  }

  .preview-desc {
    font-size: 14px;
    color: $gray-500;
    margin: 0;
    line-height: 1.6;
  }

  .preview-category {
    font-size: 12px;
    color: $primary;
    background: $primary-light;
    padding: 4px 12px;
    border-radius: 12px;
    font-weight: 500;
    display: inline-block;
    width: fit-content;
  }

  .preview-section {
    .section-title {
      font-size: 16px;
      font-weight: 600;
      color: $gray-700;
      margin: 0 0 16px;
    }
  }

  .table-preview {
    .table-desc {
      font-size: 14px;
      color: $gray-500;
      margin: 0 0 20px;
    }

    .fields-title,
    .sample-title {
      font-size: 14px;
      font-weight: 600;
      color: $gray-600;
      margin: 20px 0 12px;
    }

    .fields-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
      gap: 12px;
      margin-bottom: 20px;
    }

    .field-card {
      display: flex;
      gap: 12px;
      padding: 12px;
      background: $gray-50;
      border-radius: 8px;
      border: 1px solid $gray-100;
    }

    .field-icon {
      width: 40px;
      height: 40px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: 8px;
      font-size: 18px;
      flex-shrink: 0;
    }

    .field-info {
      flex: 1;
      min-width: 0;
    }

    .field-name {
      font-size: 14px;
      font-weight: 500;
      color: $gray-700;
      margin-bottom: 2px;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }

    .field-type {
      font-size: 12px;
      color: $gray-400;
    }

    .sample-data {
      margin-top: 20px;
      padding-top: 20px;
      border-top: 1px solid $gray-100;
    }
  }
}

// 响应式设计
@media (max-width: 768px) {
  .home-nav-tabs {
    padding: 12px 16px;
    gap: 4px;

    .nav-tab-item {
      flex: 1;
      justify-content: center;
      padding: 8px 12px;
      font-size: 13px;

      span {
        display: none;
      }

      .el-icon {
        font-size: 16px;
      }

      &.active::after {
        width: 30px;
      }
    }
  }

  .home-content-wrapper {
    height: calc(100vh - 100px);
  }

  .home-header {
    padding: 12px 16px;
    flex-wrap: wrap;
    gap: 12px;

    .header-search {
      order: 3;
      max-width: none;
      width: 100%;
    }

    .header-actions {
      position: static;
    }
  }

  .home-view {
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

// 全部多维表视图响应式
@media (max-width: 768px) {
  .all-bases-view {
    padding: 16px;

    .tabs-header {
      .tab-item {
        padding: 12px 16px;
        font-size: 13px;

        .tab-count {
          display: none;
        }
      }
    }

    .tabs-content {
      padding: 16px;
    }

    .table-list-item {
      padding: 12px 16px;

      .item-icon {
        width: 40px;
        height: 40px;
        font-size: 18px;
      }

      .item-info {
        .item-name {
          font-size: 14px;
        }

        .item-desc {
          font-size: 12px;
        }
      }

      .item-meta {
        display: none;
      }

      .item-actions {
        opacity: 1;
        gap: 2px;

        .action-btn {
          padding: 4px;
          opacity: 0.6;

          &:hover {
            opacity: 1;
          }

          .el-icon {
            font-size: 14px;
          }
        }
      }
    }

    .pagination-container {
      flex-direction: column;
      gap: 16px;
      align-items: flex-start;

      .pagination-left {
        width: 100%;
        justify-content: space-between;
      }
    }
  }
}

@media (max-width: 480px) {
  .all-bases-view {
    padding: 12px;

    .all-bases-header {
      .view-title {
        font-size: 20px;
      }
    }

    .tabs-header {
      .tab-item {
        flex: 1;
        justify-content: center;
        padding: 12px;

        span:not(.tab-count) {
          display: none;
        }

        .tab-count {
          display: inline-block;
        }
      }
    }

    .table-list-item {
      .item-icon {
        width: 36px;
        height: 36px;
        font-size: 16px;
      }
    }
  }
}

// 模板视图响应式
@media (max-width: 768px) {
  .templates-view {
    padding: 16px;

    .templates-header {
      margin-bottom: 24px;

      .templates-header-top {
        flex-direction: column;
        align-items: stretch;
      }

      .view-title {
        font-size: 20px;
      }

      .view-desc {
        font-size: 13px;
      }

      .template-search-wrapper {
        width: 100%;
      }
    }

    .templates-grid {
      grid-template-columns: 1fr;
      gap: 16px;
    }

    .template-card {
      padding: 16px;

      .template-icon {
        width: 48px;
        height: 48px;
        font-size: 24px;
      }

      .template-name {
        font-size: 15px;
      }

      .template-desc {
        font-size: 12px;
      }
    }
  }

  // 分享视图页签样式
  .tabs-container {
    width: 100%;
  }

  .tabs-header {
    display: flex;
    gap: 8px;
    margin-bottom: 20px;
    border-bottom: 2px solid $gray-100;
    padding-bottom: 0;

    .tab-item {
      display: flex;
      align-items: center;
      gap: 6px;
      padding: 12px 20px;
      cursor: pointer;
      border-radius: 8px 8px 0 0;
      transition: all 0.2s ease;
      font-size: 14px;
      color: $gray-600;
      background: transparent;
      border: none;
      position: relative;
      bottom: -2px;

      &:hover {
        background: $gray-50;
        color: $primary;
      }

      &.active {
        color: $primary;
        background: white;
        border-bottom: 2px solid white;
        font-weight: 600;

        .tab-count {
          background: $primary;
          color: white;
        }
      }

      .tab-count {
        font-size: 12px;
        padding: 2px 8px;
        border-radius: 12px;
        background: $gray-200;
        color: $gray-600;
        margin-left: 4px;
      }
    }
  }

  .tabs-content {
    .loading-state {
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      padding: 80px 20px;

      .loading-icon {
        animation: spinning 1s linear infinite;
        color: $primary;
        margin-bottom: 16px;
      }

      p {
        font-size: 14px;
        color: $gray-500;
        margin: 0;
      }
    }

    .tab-panel {
      min-height: 400px;
    }
  }

  @keyframes spinning {
    from {
      transform: rotate(0deg);
    }
    to {
      transform: rotate(360deg);
    }
  }
}
</style>
