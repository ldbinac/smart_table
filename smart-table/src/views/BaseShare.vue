<template>
  <div class="base-share-page">
    <div v-loading="loading" class="share-content">
      <!-- 加载分享信息 -->
      <div v-if="!error && shareData" class="share-success">
        <div class="share-header">
          <div
            class="base-icon"
            :style="{ backgroundColor: shareData.base.color || '#6366f1' }">
            {{ shareData.base.icon || "📊" }}
          </div>
          <h1 class="base-name">{{ shareData.base.name }}</h1>
          <p v-if="shareData.base.description" class="base-description">
            {{ shareData.base.description }}
          </p>
          <div class="permission-badge">
            <el-tag :type="permission === 'edit' ? 'warning' : 'info'" size="large">
              <el-icon><Lock /></el-icon>
              {{ permission === 'edit' ? '可编辑' : '仅查看' }}
            </el-tag>
          </div>
        </div>

        <div class="share-actions">
          <el-button
            type="primary"
            size="large"
            @click="enterBase">
            <el-icon><ArrowRight /></el-icon>
            进入多维表格
          </el-button>
        </div>

        <div class="share-info">
          <el-alert
            v-if="permission === 'view'"
            title="您只有查看权限，无法编辑内容"
            type="info"
            :closable="false"
            show-icon />
          <el-alert
            v-else
            title="您可以编辑此多维表格的内容"
            type="success"
            :closable="false"
            show-icon />
        </div>
      </div>

      <!-- 错误状态 -->
      <div v-else-if="error" class="share-error">
        <el-icon :size="64" color="#f56c6c"><WarningFilled /></el-icon>
        <h2>分享链接无效</h2>
        <p class="error-message">{{ errorMessage }}</p>
        <el-button type="primary" @click="goHome">返回首页</el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { ArrowRight, Lock, WarningFilled } from "@element-plus/icons-vue";
import { shareApiService } from "@/services/api/shareApiService";
import { useBaseStore } from "@/stores/baseStore";

const router = useRouter();
const baseStore = useBaseStore();

const loading = ref(true);
const error = ref(false);
const errorMessage = ref("");
const shareData = ref<{
  base: any;
  permission: "view" | "edit";
  share_token: string;
} | null>(null);

const token = computed(() => {
  return router.currentRoute.value.params.token as string;
});

const permission = computed(() => {
  return shareData.value?.permission || "view";
});

// 加载分享信息
async function loadShareInfo() {
  loading.value = true;
  error.value = false;

  try {
    const data = await shareApiService.accessShare(token.value);
    shareData.value = data;
    
    // 设置页面标题
    document.title = `访问分享 - ${data.base.name}`;
  } catch (err: any) {
    error.value = true;
    errorMessage.value = err.message || "分享链接无效或已过期";
    console.error("加载分享信息失败:", err);
  } finally {
    loading.value = false;
  }
}

// 进入 Base
async function enterBase() {
  if (!shareData.value) return;

  try {
    // 将分享信息存储到 localStorage，供 Base 页面使用
    localStorage.setItem(
      `share_permission_${shareData.value.base.id}`,
      JSON.stringify({
        share_token: shareData.value.share_token,
        base_id: shareData.value.base.id,
      })
    );

    ElMessage.success("正在进入多维表格...");
    
    // 跳转到 Base 页面
    router.push(`/base/${shareData.value.base.id}`);
  } catch (err: any) {
    ElMessage.error("进入失败：" + err.message);
  }
}

// 返回首页
function goHome() {
  router.push("/");
}

onMounted(() => {
  if (token.value) {
    loadShareInfo();
  } else {
    error.value = true;
    errorMessage.value = "分享令牌无效";
    loading.value = false;
  }
});
</script>

<style lang="scss" scoped>
.base-share-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.share-content {
  width: 100%;
  max-width: 600px;
  background: white;
  border-radius: 16px;
  padding: 40px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.share-success {
  text-align: center;

  .share-header {
    margin-bottom: 32px;

    .base-icon {
      width: 80px;
      height: 80px;
      border-radius: 16px;
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 40px;
      margin: 0 auto 24px;
      box-shadow: 0 8px 24px rgba(0, 0, 0, 0.15);
    }

    .base-name {
      font-size: 28px;
      font-weight: 700;
      color: #1f2937;
      margin: 0 0 12px;
    }

    .base-description {
      font-size: 14px;
      color: #6b7280;
      margin: 0 0 24px;
    }

    .permission-badge {
      display: inline-block;
    }
  }

  .share-actions {
    margin-bottom: 24px;
  }

  .share-info {
    text-align: left;
  }
}

.share-error {
  text-align: center;
  padding: 40px 20px;

  h2 {
    margin: 24px 0 12px;
    font-size: 24px;
    font-weight: 600;
    color: #1f2937;
  }

  .error-message {
    margin: 0 0 32px;
    font-size: 14px;
    color: #6b7280;
  }
}
</style>
