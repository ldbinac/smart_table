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

// 预设颜色选项
const colorOptions = [
  "#409EFF", // 蓝色
  "#67C23A", // 绿色
  "#E6A23C", // 黄色
  "#F56C6C", // 红色
  "#909399", // 灰色
  "#9B59B6", // 紫色
  "#1ABC9C", // 青色
  "#E74C3C", // 深红
];

// 取消收藏加载状态
const unstarLoadingMap = ref<Map<string, boolean>>(new Map());

// 收藏的 Base 列表
const starredBases = computed(() => {
  return baseStore.bases
    .filter((base) => base.isStarred)
    .sort((a, b) => b.updatedAt - a.updatedAt);
});

// 所有 Base 列表（包含已收藏和未收藏）
const allBases = computed(() => {
  return [...baseStore.bases].sort((a, b) => b.updatedAt - a.updatedAt);
});

// 是否有收藏的项目
const hasStarredBases = computed(() => starredBases.value.length > 0);

onMounted(async () => {
  await baseStore.loadBases();
});

function goToBase(id: string) {
  // 使用 hash 路由格式，确保在新窗口中能正确加载
  const baseUrl = window.location.origin;
  window.open(`${baseUrl}/#/base/${id}`, '_blank');
}

function goToSettings() {
  router.push("/settings");
}

function openCreateDialog() {
  createDialogVisible.value = true;
  // 重置表单
  createForm.name = "";
  createForm.description = "";
  createForm.icon = "📊";
  createForm.color = "#409EFF";
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
        // 可选：创建后自动跳转到新 Base
        // router.push(`/base/${base.id}`);
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
  editForm.color = base.color || "#409EFF";
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

  // 设置加载状态
  unstarLoadingMap.value.set(base.id, true);

  try {
    // 调用 API 取消收藏
    await baseStore.toggleStarBase(base.id);

    // 前端实时移除（通过计算属性自动更新）
    ElMessage.success("已取消收藏");
  } catch (error) {
    ElMessage.error("取消收藏失败");
  } finally {
    // 清除加载状态
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
    <header class="home-header">
      <h1>Smart Table</h1>
      <div class="header-actions">
        <el-button type="primary" @click="openCreateDialog">
          <el-icon><Plus /></el-icon>
          创建多维表格
        </el-button>
        <el-button @click="goToSettings">设置</el-button>
      </div>
    </header>

    <main class="home-content">
      <!-- 空状态 -->
      <div v-if="baseStore.bases.length === 0" class="empty-state">
        <el-empty description="暂无多维表格">
          <template #description>
            <p>暂无多维表格</p>
            <p class="empty-subtitle">点击按钮创建您的第一个多维表格</p>
          </template>
          <el-button type="primary" size="large" @click="openCreateDialog">
            <el-icon><Plus /></el-icon>
            创建多维表格
          </el-button>
        </el-empty>
      </div>

      <div v-else class="content-wrapper">
        <!-- 收藏分区 -->
        <section v-if="hasStarredBases" class="starred-section">
          <div class="section-header">
            <div class="section-title">
              <el-icon class="star-icon" :size="20"><StarFilled /></el-icon>
              <h2>我的收藏</h2>
              <el-tag size="small" type="warning" effect="light">
                {{ starredBases.length }}
              </el-tag>
            </div>
          </div>

          <div class="starred-list">
            <el-card
              v-for="base in starredBases"
              :key="base.id"
              class="base-card starred-card"
              shadow="hover"
              @click="goToBase(base.id)"
            >
              <template #header>
                <div class="card-header">
                  <div class="card-title">
                    <span
                      class="base-icon"
                      :style="{ backgroundColor: base.color || '#409EFF' }"
                    >
                      {{ base.icon || "📊" }}
                    </span>
                    <span class="base-name" :title="base.name">
                      {{ base.name }}
                    </span>
                  </div>
                  <div class="card-actions">
                    <!-- 取消收藏按钮 -->
                    <el-button
                      link
                      type="warning"
                      class="unstar-btn"
                      :loading="isUnstarLoading(base.id)"
                      @click="handleUnstarBase(base, $event)"
                    >
                      <el-icon :size="18"><StarFilled /></el-icon>
                      <span class="btn-text">取消收藏</span>
                    </el-button>

                    <!-- 更多操作 -->
                    <el-dropdown
                      trigger="click"
                      @command="
                        (cmd) => {
                          if (cmd === 'edit') openEditDialog(base);
                          else if (cmd === 'delete') handleDeleteBase(base);
                        }
                      "
                      @click.stop="stopPropagation"
                    >
                      <el-button
                        link
                        type="info"
                        class="more-btn"
                        @click.stop="stopPropagation"
                      >
                        <el-icon><MoreFilled /></el-icon>
                      </el-button>
                      <template #dropdown>
                        <el-dropdown-menu>
                          <el-dropdown-item command="edit">
                            <el-icon><Edit /></el-icon>重命名
                          </el-dropdown-item>
                          <el-dropdown-item
                            divided
                            command="delete"
                            class="delete-item"
                          >
                            <el-icon><Delete /></el-icon>删除
                          </el-dropdown-item>
                        </el-dropdown-menu>
                      </template>
                    </el-dropdown>
                  </div>
                </div>
              </template>
              <div class="card-content">
                <p class="base-description">
                  {{ base.description || "暂无描述" }}
                </p>
                <div class="base-meta">
                  <span class="update-time">
                    更新于
                    {{ new Date(base.updatedAt).toLocaleDateString("zh-CN") }}
                  </span>
                </div>
              </div>
            </el-card>
          </div>
        </section>

        <!-- 所有多维表格分区 -->
        <section class="all-bases-section">
          <div class="section-header">
            <div class="section-title">
              <el-icon :size="20"><Grid /></el-icon>
              <h2>所有多维表格</h2>
              <el-tag size="small" type="info" effect="light">
                {{ allBases.length }}
              </el-tag>
            </div>
          </div>

          <div class="base-list">
            <!-- 创建卡片 -->
            <el-card
              class="base-card create-card"
              shadow="hover"
              @click="openCreateDialog"
            >
              <div class="create-card-content">
                <el-icon :size="32"><Plus /></el-icon>
                <span>创建多维表格</span>
              </div>
            </el-card>

            <!-- 所有 Base 卡片（包含已收藏和未收藏）-->
            <el-card
              v-for="base in allBases"
              :key="base.id"
              class="base-card"
              :class="{ 'is-starred': base.isStarred }"
              shadow="hover"
              @click="goToBase(base.id)"
            >
              <template #header>
                <div class="card-header">
                  <div class="card-title">
                    <span
                      class="base-icon"
                      :style="{ backgroundColor: base.color || '#409EFF' }"
                    >
                      {{ base.icon || "📊" }}
                    </span>
                    <span class="base-name" :title="base.name">
                      {{ base.name }}
                    </span>
                  </div>
                  <div class="card-actions">
                    <!-- 收藏/取消收藏按钮 -->
                    <el-button
                      v-if="!base.isStarred"
                      link
                      type="info"
                      class="star-btn"
                      @click="handleStarBase(base, $event)"
                    >
                      <el-icon :size="18"><Star /></el-icon>
                    </el-button>
                    <el-button
                      v-else
                      link
                      type="warning"
                      class="star-btn"
                      @click="handleUnstarBase(base, $event)"
                    >
                      <el-icon :size="18"><StarFilled /></el-icon>
                    </el-button>

                    <!-- 更多操作 -->
                    <el-dropdown
                      trigger="click"
                      @command="
                        (cmd) => {
                          if (cmd === 'edit') openEditDialog(base);
                          else if (cmd === 'delete') handleDeleteBase(base);
                        }
                      "
                      @click.stop="stopPropagation"
                    >
                      <el-button
                        link
                        type="info"
                        class="more-btn"
                        @click.stop="stopPropagation"
                      >
                        <el-icon><MoreFilled /></el-icon>
                      </el-button>
                      <template #dropdown>
                        <el-dropdown-menu>
                          <el-dropdown-item command="edit">
                            <el-icon><Edit /></el-icon>重命名
                          </el-dropdown-item>
                          <el-dropdown-item
                            divided
                            command="delete"
                            class="delete-item"
                          >
                            <el-icon><Delete /></el-icon>删除
                          </el-dropdown-item>
                        </el-dropdown-menu>
                      </template>
                    </el-dropdown>
                  </div>
                </div>
              </template>
              <div class="card-content">
                <p class="base-description">
                  {{ base.description || "暂无描述" }}
                </p>
                <div class="base-meta">
                  <span class="update-time">
                    更新于
                    {{ new Date(base.updatedAt).toLocaleDateString("zh-CN") }}
                  </span>
                </div>
              </div>
            </el-card>
          </div>
        </section>
      </div>
    </main>

    <!-- 创建对话框 -->
    <el-dialog
      v-model="createDialogVisible"
      title="创建多维表格"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="createFormRef"
        :model="createForm"
        :rules="createFormRules"
        label-width="80px"
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
            :rows="3"
            placeholder="请输入描述（可选）"
            maxlength="200"
            show-word-limit
          />
        </el-form-item>

        <el-form-item label="图标">
          <div class="icon-selector">
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
          <div class="color-selector">
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
        <span class="dialog-footer">
          <el-button @click="closeCreateDialog">取消</el-button>
          <el-button type="primary" @click="handleCreateBase">确定</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 编辑对话框 -->
    <el-dialog
      v-model="editDialogVisible"
      title="编辑多维表格"
      width="500px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="editFormRef"
        :model="editForm"
        :rules="editFormRules"
        label-width="80px"
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
            :rows="3"
            placeholder="请输入描述（可选）"
            maxlength="200"
            show-word-limit
          />
        </el-form-item>

        <el-form-item label="图标">
          <div class="icon-selector">
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
          <div class="color-selector">
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
        <span class="dialog-footer">
          <el-button @click="closeEditDialog">取消</el-button>
          <el-button type="primary" @click="handleEditBase">保存</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<style scoped>
.home-page {
  padding: 20px;
  max-width: 1400px;
  margin: 0 auto;
}

.home-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--el-border-color-light);
}

.home-header h1 {
  margin: 0;
  font-size: 24px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.header-actions {
  display: flex;
  gap: 12px;
}

.home-content {
  min-height: 400px;
}

.content-wrapper {
  display: flex;
  flex-direction: column;
  gap: 32px;
}

/* 分区样式 */
.starred-section {
  background: linear-gradient(135deg, #fffbeb 0%, #ffffff 100%);
  border-radius: 12px;
  padding: 20px;
  border: 1px solid #fde68a;
}

.all-bases-section {
  background-color: var(--el-fill-color-light);
  border-radius: 12px;
  padding: 20px;
}

.section-header {
  margin-bottom: 16px;
}

.section-title {
  display: flex;
  align-items: center;
  gap: 10px;
}

.section-title h2 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
  color: var(--el-text-color-primary);
}

.star-icon {
  color: #f7ba2a;
}

/* 列表布局 */
.starred-list,
.base-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 16px;
}

/* 卡片样式 */
.base-card {
  cursor: pointer;
  transition: all 0.3s ease;
  border: 1px solid transparent;
}

.base-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
}

/* 收藏的卡片样式 */
.starred-card {
  border-color: #f7ba2a;
  background: linear-gradient(135deg, #fffbeb 0%, #ffffff 100%);
}

.starred-card:hover {
  border-color: #f59e0b;
  box-shadow: 0 8px 24px rgba(247, 186, 42, 0.2);
}

/* 创建卡片 */
.create-card {
  border: 2px dashed var(--el-border-color);
  background-color: var(--el-fill-color-light);
}

.create-card:hover {
  border-color: var(--el-color-primary);
  background-color: var(--el-fill-color);
}

.create-card-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  min-height: 120px;
  gap: 12px;
  color: var(--el-text-color-secondary);
  font-size: 16px;
}

.create-card:hover .create-card-content {
  color: var(--el-color-primary);
}

/* 卡片头部 */
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 0;
}

.base-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border-radius: 8px;
  font-size: 18px;
  flex-shrink: 0;
}

.base-name {
  font-size: 16px;
  font-weight: 500;
  color: var(--el-text-color-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 卡片操作 */
.card-actions {
  display: flex;
  align-items: center;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.2s;
}

.base-card:hover .card-actions {
  opacity: 1;
}

.star-btn,
.more-btn {
  padding: 6px;
}

.star-btn:hover {
  transform: scale(1.1);
  color: #f7ba2a;
}

/* 取消收藏按钮 */
.unstar-btn {
  padding: 6px 10px;
  display: flex;
  align-items: center;
  gap: 4px;
  color: #f7ba2a;
}

.unstar-btn:hover {
  color: #f59e0b;
  background-color: rgba(247, 186, 42, 0.1);
}

.unstar-btn .btn-text {
  font-size: 12px;
}

/* 卡片内容 */
.card-content {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.base-description {
  margin: 0;
  color: var(--el-text-color-secondary);
  font-size: 14px;
  line-height: 1.5;
  min-height: 42px;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.base-meta {
  display: flex;
  justify-content: flex-end;
}

.update-time {
  font-size: 12px;
  color: var(--el-text-color-placeholder);
}

/* 空状态 */
.empty-state {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 400px;
}

.empty-subtitle {
  color: var(--el-text-color-secondary);
  font-size: 14px;
  margin-top: 8px;
}

/* 图标选择器 */
.icon-selector {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.icon-option {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border: 2px solid var(--el-border-color);
  border-radius: 8px;
  cursor: pointer;
  font-size: 20px;
  transition: all 0.2s;
}

.icon-option:hover {
  border-color: var(--el-color-primary);
  background-color: var(--el-fill-color);
}

.icon-option.active {
  border-color: var(--el-color-primary);
  background-color: var(--el-color-primary-light-9);
}

/* 颜色选择器 */
.color-selector {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.color-option {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  cursor: pointer;
  transition: all 0.2s;
  border: 3px solid transparent;
}

.color-option:hover {
  transform: scale(1.15);
}

.color-option.active {
  border-color: var(--el-text-color-primary);
  transform: scale(1.15);
}

/* 对话框底部 */
.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}

:deep(.delete-item) {
  color: var(--el-color-danger);
}

:deep(.delete-item:hover) {
  color: var(--el-color-danger-light-3);
  background-color: var(--el-color-danger-light-9);
}
</style>
