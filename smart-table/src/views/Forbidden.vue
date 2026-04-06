<template>
  <div class="forbidden-page">
    <div class="content">
      <h1 class="error-code">403</h1>
      <h2 class="error-title">禁止访问</h2>
      <p class="error-message">
        {{ message || '您没有权限访问此页面' }}
      </p>
      <div class="actions">
        <el-button type="primary" @click="goHome">返回首页</el-button>
        <el-button @click="goBack">返回上一页</el-button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter, useRoute } from 'vue-router'

const router = useRouter()
const route = useRoute()

const message = route.query.message as string || ''

const goHome = () => {
  router.push('/')
}

const goBack = () => {
  router.back()
}
</script>

<style scoped lang="scss">
.forbidden-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 100vh;
  background-color: #f5f7fa;

  .content {
    text-align: center;
    padding: 40px;

    .error-code {
      font-size: 120px;
      font-weight: bold;
      color: #f56c6c;
      margin: 0;
      line-height: 1;
    }

    .error-title {
      font-size: 32px;
      color: #606266;
      margin: 20px 0;
    }

    .error-message {
      font-size: 16px;
      color: #909399;
      margin: 20px 0;
    }

    .actions {
      margin-top: 30px;

      .el-button {
        margin: 0 10px;
      }
    }
  }
}
</style>
