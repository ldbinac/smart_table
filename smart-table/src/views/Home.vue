<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useBaseStore } from '@/stores';
import type { FormInstance, FormRules } from 'element-plus';

const router = useRouter();
const baseStore = useBaseStore();
const createFormRef = ref<FormInstance>();

// 创建对话框显示状态
const createDialogVisible = ref(false);

// 创建表单数据
const createForm = reactive({
  name: '',
  description: '',
  icon: '📊',
  color: '#409EFF'
});

// 表单验证规则
const createFormRules: FormRules = {
  name: [
    { required: true, message: '请输入多维表格名称', trigger: 'blur' },
    { min: 1, max: 50, message: '名称长度在 1 到 50 个字符', trigger: 'blur' }
  ]
};

// 预设图标选项
const iconOptions = ['📊', '📋', '📁', '📝', '📅', '💼', '📈', '🎯', '✅', '📌'];

// 预设颜色选项
const colorOptions = [
  '#409EFF', // 蓝色
  '#67C23A', // 绿色
  '#E6A23C', // 黄色
  '#F56C6C', // 红色
  '#909399', // 灰色
  '#9B59B6', // 紫色
  '#1ABC9C', // 青色
  '#E74C3C'  // 深红
];

onMounted(async () => {
  await baseStore.loadBases();
});

function goToBase(id: string) {
  router.push(`/base/${id}`);
}

function goToSettings() {
  router.push('/settings');
}

function openCreateDialog() {
  createDialogVisible.value = true;
  // 重置表单
  createForm.name = '';
  createForm.description = '';
  createForm.icon = '📊';
  createForm.color = '#409EFF';
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
        color: createForm.color
      });
      
      if (base) {
        closeCreateDialog();
        // 可选：创建后自动跳转到新 Base
        // router.push(`/base/${base.id}`);
      }
    }
  });
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

      <!-- Base 列表 -->
      <div v-else class="base-list">
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

        <!-- Base 卡片 -->
        <el-card
          v-for="base in baseStore.bases"
          :key="base.id"
          class="base-card"
          shadow="hover"
          @click="goToBase(base.id)"
        >
          <template #header>
            <div class="card-header">
              <span>
                <span class="base-icon" :style="{ backgroundColor: base.color || '#409EFF' }">
                  {{ base.icon || '📊' }}
                </span>
                {{ base.name }}
              </span>
              <el-tag v-if="base.isStarred" type="warning" size="small">星标</el-tag>
            </div>
          </template>
          <div class="card-content">
            {{ base.description || '暂无描述' }}
          </div>
        </el-card>
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
  </div>
</template>

<style scoped>
.home-page {
  padding: 20px;
}

.home-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.base-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 16px;
}

.base-card {
  cursor: pointer;
  transition: all 0.3s;
}

.base-card:hover {
  transform: translateY(-2px);
}

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
  min-height: 80px;
  gap: 8px;
  color: var(--el-text-color-secondary);
}

.create-card:hover .create-card-content {
  color: var(--el-color-primary);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.base-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 6px;
  margin-right: 8px;
  font-size: 16px;
}

.card-content {
  color: var(--el-text-color-secondary);
  font-size: 14px;
}

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

.icon-selector {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.icon-option {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  border: 2px solid var(--el-border-color);
  border-radius: 6px;
  cursor: pointer;
  font-size: 18px;
  transition: all 0.2s;
}

.icon-option:hover {
  border-color: var(--el-color-primary);
}

.icon-option.active {
  border-color: var(--el-color-primary);
  background-color: var(--el-color-primary-light-9);
}

.color-selector {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.color-option {
  width: 28px;
  height: 28px;
  border-radius: 50%;
  cursor: pointer;
  transition: all 0.2s;
  border: 2px solid transparent;
}

.color-option:hover {
  transform: scale(1.1);
}

.color-option.active {
  border-color: var(--el-text-color-primary);
  transform: scale(1.1);
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>
