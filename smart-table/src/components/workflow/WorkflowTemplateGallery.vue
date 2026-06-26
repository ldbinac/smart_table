<script setup lang="ts">
import { ref, computed, watch } from "vue";
import { ElMessage } from "element-plus";
import { Collection, CopyDocument } from "@element-plus/icons-vue";
import { useWorkflowStore } from "@/stores/workflowStore";
import type { Workflow, WorkflowTemplate } from "@/types/workflow";
import type { TableEntity } from "@/db/schema";

interface Props {
  visible: boolean;
  baseId: string;
  tableId?: string | null;
  tables?: TableEntity[];
}

const props = withDefaults(defineProps<Props>(), {
  tableId: null,
  tables: () => [],
});

const visible = defineModel<boolean>("visible", { required: true });

const emit = defineEmits<{
  (e: "created", workflow: Workflow): void;
}>();

const workflowStore = useWorkflowStore();

const loading = ref(false);
const selectedTableId = ref<string>(props.tableId || "");
const activeCategory = ref<string>("all");
const activeSource = ref<"all" | "system" | "custom">("all");

watch(
  () => visible.value,
  (isVisible) => {
    if (isVisible) {
      selectedTableId.value = props.tableId || "";
      activeCategory.value = "all";
      activeSource.value = "all";
      loadTemplates();
    }
  },
);

watch(
  () => props.tableId,
  (id) => {
    selectedTableId.value = id || "";
  },
);

async function loadTemplates() {
  loading.value = true;
  try {
    await workflowStore.loadTemplates();
  } finally {
    loading.value = false;
  }
}

const templates = computed(() => workflowStore.templates);

const categories = computed(() => {
  const set = new Set<string>();
  templates.value.forEach((template) => {
    if (template.category) {
      set.add(template.category);
    }
  });
  return ["all", ...Array.from(set)];
});

const filteredTemplates = computed(() => {
  return templates.value.filter((template) => {
    const categoryMatch =
      activeCategory.value === "all" ||
      template.category === activeCategory.value;
    const sourceMatch =
      activeSource.value === "all" ||
      (activeSource.value === "system"
        ? template.is_system
        : !template.is_system);
    return categoryMatch && sourceMatch;
  });
});

const hasCustomCategoryFilter = computed(
  () => categories.value.length > 1,
);

function handleClose() {
  visible.value = false;
}

async function handleUseTemplate(template: WorkflowTemplate) {
  if (!selectedTableId.value) {
    ElMessage.warning("请选择要应用模板的数据表");
    return;
  }

  try {
    const workflow = await workflowStore.instantiateTemplate(
      template.id,
      selectedTableId.value,
    );
    emit("created", workflow);
    visible.value = false;
  } catch {
    // 错误已由 workflowStore 统一处理
  }
}

function formatDate(date: string): string {
  return new Date(date).toLocaleString("zh-CN");
}
</script>

<template>
  <el-dialog
    v-model="visible"
    title="模板库"
    width="900px"
    :close-on-click-modal="false"
    @close="handleClose">
    <div v-loading="loading" class="template-gallery">
      <div class="gallery-toolbar">
        <div class="filter-groups">
          <el-radio-group v-model="activeSource" size="small">
            <el-radio-button label="all">全部</el-radio-button>
            <el-radio-button label="system">系统内置</el-radio-button>
            <el-radio-button label="custom">用户自定义</el-radio-button>
          </el-radio-group>

          <el-radio-group
            v-if="hasCustomCategoryFilter"
            v-model="activeCategory"
            size="small">
            <el-radio-button
              v-for="category in categories"
              :key="category"
              :label="category">
              {{ category === "all" ? "全部分类" : category }}
            </el-radio-button>
          </el-radio-group>
        </div>

        <div class="table-selector">
          <span class="selector-label">应用至数据表：</span>
          <el-select
            v-model="selectedTableId"
            placeholder="请选择数据表"
            style="width: 220px"
            :disabled="!!props.tableId">
            <el-option
              v-for="table in props.tables"
              :key="table.id"
              :label="table.name"
              :value="table.id" />
          </el-select>
        </div>
      </div>

      <div class="template-list">
        <el-empty
          v-if="filteredTemplates.length === 0"
          description="暂无符合条件的模板" />

        <el-card
          v-for="template in filteredTemplates"
          :key="template.id"
          class="template-card"
          shadow="hover">
          <div class="template-header">
            <div class="template-icon">
              <el-icon :size="28"><Collection /></el-icon>
            </div>
            <div class="template-info">
              <div class="template-name">{{ template.name }}</div>
              <div class="template-tags">
                <el-tag v-if="template.is_system" size="small" type="success">
                  系统内置
                </el-tag>
                <el-tag v-else size="small" type="info">用户自定义</el-tag>
                <el-tag
                  v-if="template.category"
                  size="small"
                  type="warning"
                  class="category-tag">
                  {{ template.category }}
                </el-tag>
              </div>
            </div>
          </div>

          <div class="template-description">
            {{ template.description || "暂无描述" }}
          </div>

          <div class="template-meta">
            <span>更新于 {{ formatDate(template.updated_at) }}</span>
          </div>

          <div class="template-actions">
            <el-button
              type="primary"
              :icon="CopyDocument"
              @click="handleUseTemplate(template)">
              使用模板
            </el-button>
          </div>
        </el-card>
      </div>
    </div>
  </el-dialog>
</template>

<style lang="scss" scoped>
.template-gallery {
  display: flex;
  flex-direction: column;
  gap: $spacing-md;
  min-height: 300px;
}

.gallery-toolbar {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: $spacing-md;
}

.filter-groups {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: $spacing-md;
}

.table-selector {
  display: flex;
  align-items: center;
  gap: $spacing-sm;
}

.selector-label {
  font-size: $font-size-sm;
  color: $text-secondary;
  white-space: nowrap;
}

.template-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: $spacing-md;
  max-height: 520px;
  overflow-y: auto;
  padding: $spacing-xs;
}

.template-card {
  display: flex;
  flex-direction: column;

  :deep(.el-card__body) {
    display: flex;
    flex-direction: column;
    flex: 1;
    padding: $spacing-md;
  }
}

.template-header {
  display: flex;
  align-items: flex-start;
  gap: $spacing-md;
  margin-bottom: $spacing-sm;
}

.template-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: $border-radius-md;
  background-color: rgba($primary-color, 0.08);
  color: $primary-color;
  flex-shrink: 0;
}

.template-info {
  flex: 1;
  min-width: 0;
}

.template-name {
  font-weight: 600;
  font-size: $font-size-base;
  color: $text-primary;
  margin-bottom: $spacing-xs;
}

.template-tags {
  display: flex;
  flex-wrap: wrap;
  gap: $spacing-xs;
}

.category-tag {
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.template-description {
  flex: 1;
  font-size: $font-size-sm;
  color: $text-secondary;
  line-height: 1.5;
  margin-bottom: $spacing-md;
  min-height: 40px;
}

.template-meta {
  font-size: 12px;
  color: $text-disabled;
  margin-bottom: $spacing-md;
}

.template-actions {
  display: flex;
  justify-content: flex-end;
  padding-top: $spacing-sm;
  border-top: 1px solid $border-color;
}
</style>
