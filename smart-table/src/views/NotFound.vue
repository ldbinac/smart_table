<script setup lang="ts">
import { useRouter } from "vue-router";
import { useI18n } from "vue-i18n";

const router = useRouter();
const { t } = useI18n();

function goHome() {
  router.push("/");
}
</script>

<template>
  <div class="not-found-page">
    <el-result icon="warning" title="404" :sub-title="t('common.pageNotFound')">
      <template #extra>
        <el-button type="primary" @click="goHome">{{ t('common.backHome') }}</el-button>
      </template>
    </el-result>
  </div>
</template>

<style scoped>
.not-found-page {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
}
</style>
