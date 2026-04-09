<template>
  <el-dialog
    v-model="dialogVisible"
    title="选择关联记录"
    width="600px"
    :close-on-click-modal="false"
    @close="handleCancel"
  >
    <div class="link-record-selector">
      <!-- 搜索栏 -->
      <div class="search-bar">
        <el-input
          v-model="searchKeyword"
          placeholder="搜索记录..."
          clearable
          @input="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
      </div>

      <!-- 已选记录 -->
      <div v-if="selectedRecords.length > 0" class="selected-section">
        <div class="section-title">已选择 ({{ selectedRecords.length }})</div>
        <div class="selected-list">
          <el-tag
            v-for="record in selectedRecords"
            :key="record.id"
            closable
            size="small"
            class="selected-tag"
            @close="removeSelected(record.id)"
          >
            {{ getDisplayValue(record) }}
          </el-tag>
        </div>
      </div>

      <!-- 可选记录列表 -->
      <div class="records-section">
        <div class="section-title">可选记录</div>
        <div v-if="loading" class="loading-state">
          <el-skeleton :rows="5" animated />
        </div>
        <div v-else-if="records.length === 0" class="empty-state">
          <el-empty description="暂无可用记录" />
        </div>
        <div v-else class="records-list">
          <div
            v-for="record in records"
            :key="record.id"
            class="record-item"
            :class="{ selected: isSelected(record.id) }"
            @click="toggleSelect(record)"
          >
            <el-checkbox
              :model-value="isSelected(record.id)"
              @click.stop
              @change="() => toggleSelect(record)"
            />
            <span class="record-value">{{ getDisplayValue(record) }}</span>
          </div>
        </div>
      </div>

      <!-- 分页 -->
      <div v-if="totalPages > 1" class="pagination">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @change="handlePageChange"
        />
      </div>
    </div>

    <template #footer>
      <div class="dialog-footer">
        <el-button @click="handleCancel">取消</el-button>
        <el-button type="primary" @click="handleConfirm">
          确定 ({{ selectedRecords.length }})
        </el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from "vue";
import {
  ElDialog,
  ElInput,
  ElIcon,
  ElTag,
  ElCheckbox,
  ElButton,
  ElPagination,
  ElSkeleton,
  ElEmpty,
} from "element-plus";
import { Search } from "@element-plus/icons-vue";
import { linkApiService } from "@/services/api/linkApiService";
import type { LinkedRecord } from "@/types/link";
import { debounce } from "lodash-es";

interface Props {
  visible: boolean;
  targetTableId?: string;
  displayFieldId?: string;
  selectedIds?: string[];
  allowMultiple?: boolean;
}

const props = withDefaults(defineProps<Props>(), {
  selectedIds: () => [],
  allowMultiple: true,
});

const emit = defineEmits<{
  (e: "confirm", selectedIds: string[], records: LinkedRecord[]): void;
  (e: "cancel"): void;
}>();

// 对话框显示状态 - 只读，通过 props.visible 控制
const dialogVisible = computed({
  get: () => props.visible,
  set: () => {
    // 只读，不处理 setter，关闭逻辑由 handleCancel 处理
  },
});

// 搜索关键词
const searchKeyword = ref("");

// 记录列表
const records = ref<Array<{ id: string; values: Record<string, unknown> }>>([]);
const loading = ref(false);
const total = ref(0);
const currentPage = ref(1);
const pageSize = ref(20);

// 已选记录
const selectedRecords = ref<Array<{ id: string; values: Record<string, unknown> }>>([]);

// 总页数
const totalPages = computed(() => Math.ceil(total.value / pageSize.value));

// 监听 visible 变化，初始化数据
watch(
  () => props.visible,
  (visible) => {
    if (visible) {
      initSelectedRecords();
      loadRecords();
    }
  }
);

// 初始化已选记录
const initSelectedRecords = () => {
  // 根据 selectedIds 初始化，实际使用时可能需要从父组件传入完整记录数据
  selectedRecords.value = [];
};

// 加载记录列表
const loadRecords = async () => {
  if (!props.targetTableId) {
    console.log("[LinkRecordSelector] targetTableId 为空，不加载记录");
    return;
  }

  console.log("[LinkRecordSelector] 开始加载记录，参数:", {
    targetTableId: props.targetTableId,
    keyword: searchKeyword.value,
    page: currentPage.value,
    per_page: pageSize.value,
  });

  loading.value = true;
  try {
    const result = await linkApiService.searchLinkableRecords(
      props.targetTableId,
      {
        keyword: searchKeyword.value,
        exclude_ids: props.selectedIds,
        page: currentPage.value,
        per_page: pageSize.value,
      }
    );

    console.log("[LinkRecordSelector] 加载记录结果:", result);

    records.value = result.items;
    total.value = result.total;

    console.log("[LinkRecordSelector] 记录加载完成，共", result.items.length, "条记录");
  } catch (error) {
    console.error("[LinkRecordSelector] 加载记录失败:", error);
  } finally {
    loading.value = false;
  }
};

// 搜索（防抖）
const handleSearch = debounce(() => {
  currentPage.value = 1;
  loadRecords();
}, 300);

// 分页变化
const handlePageChange = () => {
  loadRecords();
};

// 获取显示值
const getDisplayValue = (record: { id: string; values: Record<string, unknown> }): string => {
  if (props.displayFieldId && record.values[props.displayFieldId]) {
    return String(record.values[props.displayFieldId]);
  }
  // 如果没有指定显示字段，尝试使用第一个字段或返回 ID
  const values = Object.values(record.values);
  if (values.length > 0) {
    return String(values[0]);
  }
  return record.id;
};

// 是否已选中
const isSelected = (recordId: string): boolean => {
  return selectedRecords.value.some((r) => r.id === recordId);
};

// 切换选择
const toggleSelect = (record: { id: string; values: Record<string, unknown> }) => {
  const index = selectedRecords.value.findIndex((r) => r.id === record.id);

  if (index > -1) {
    // 取消选择
    selectedRecords.value.splice(index, 1);
  } else {
    // 选择
    if (!props.allowMultiple) {
      // 单选模式，先清空
      selectedRecords.value = [];
    }
    selectedRecords.value.push(record);
  }
};

// 移除已选
const removeSelected = (recordId: string) => {
  const index = selectedRecords.value.findIndex((r) => r.id === recordId);
  if (index > -1) {
    selectedRecords.value.splice(index, 1);
  }
};

// 确认选择
const handleConfirm = () => {
  const selectedIds = selectedRecords.value.map((r) => r.id);
  const linkedRecords: LinkedRecord[] = selectedRecords.value.map((r) => ({
    record_id: r.id,
    display_value: getDisplayValue(r),
    record: r,
  }));

  emit("confirm", selectedIds, linkedRecords);
  // 确认后只触发事件，不重置状态（由父组件控制关闭）
};

// 取消
const handleCancel = () => {
  // 重置选择状态
  selectedRecords.value = [];
  searchKeyword.value = "";
  currentPage.value = 1;
  // 触发取消事件
  emit("cancel");
};

onMounted(() => {
  if (props.visible) {
    loadRecords();
  }
});
</script>

<style scoped lang="scss">
.link-record-selector {
  max-height: 500px;
  overflow-y: auto;
}

.search-bar {
  margin-bottom: 16px;
}

.section-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--el-text-color-regular);
  margin-bottom: 8px;
}

.selected-section {
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--el-border-color-light);
}

.selected-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.selected-tag {
  cursor: pointer;
}

.records-section {
  min-height: 200px;
}

.loading-state,
.empty-state {
  padding: 20px 0;
}

.records-list {
  border: 1px solid var(--el-border-color-light);
  border-radius: 4px;
  max-height: 300px;
  overflow-y: auto;
}

.record-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  cursor: pointer;
  transition: background-color 0.2s;
  border-bottom: 1px solid var(--el-border-color-lighter);

  &:last-child {
    border-bottom: none;
  }

  &:hover {
    background-color: var(--el-fill-color-light);
  }

  &.selected {
    background-color: var(--el-color-primary-light-9);
  }
}

.record-value {
  flex: 1;
  font-size: 14px;
  color: var(--el-text-color-regular);
}

.pagination {
  margin-top: 16px;
  display: flex;
  justify-content: center;
}

.dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>
