<template>
  <div class="register-page">
    <div class="register-container">
      <div class="register-header">
        <h1 class="title">SmartTable</h1>
        <p class="subtitle">多维表格管理系统</p>
      </div>

      <div class="register-box">
        <h2 class="box-title">用户注册</h2>

        <RegisterForm :loading="authStore.isLoading" @submit="handleRegister" />

        <div class="register-footer">
          <span>已有账号？</span>
          <el-link type="primary" @click="$router.push('/login')">
            立即登录
          </el-link>
        </div>
      </div>

      <!-- 底部链接 -->
      <div class="page-footer">
        <div class="footer-links">
          <a
            href="https://github.com/ldbinac/smart_table.git"
            target="_blank"
            rel="noopener noreferrer"
            class="footer-link"
            title="GitHub">
            <svg class="footer-icon" viewBox="0 0 24 24" fill="currentColor">
              <path
                d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
            </svg>
          </a>
          <a
            href="https://gitee.com/binac/smart_table.git"
            target="_blank"
            rel="noopener noreferrer"
            class="footer-link"
            title="Gitee">
            <img
              src="/gitee.ico"
              alt="Gitee"
              class="footer-icon"
              style="width: 20px; height: 20px; object-fit: contain" />
          </a>
        </div>
        <p class="footer-text">SmartTable - 开源多维表格管理系统</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from "vue-router";
import { useAuthStore } from "@/stores/auth/authStore";
import RegisterForm from "@/components/auth/RegisterForm.vue";
import type { RegisterRequest } from "@/api/types";
import { ElMessage } from "element-plus";

const router = useRouter();
const authStore = useAuthStore();

const handleRegister = async (data: RegisterRequest) => {
  const success = await authStore.register(data);

  if (success) {
    ElMessage.success("注册成功，请登录");
    router.push("/login");
  }
};
</script>

<style scoped lang="scss">
.register-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 20px;
}

.register-container {
  width: 100%;
  max-width: 420px;
}

.register-header {
  text-align: center;
  margin-bottom: 40px;
  color: white;

  .title {
    font-size: 36px;
    font-weight: 700;
    margin-bottom: 8px;
    text-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  }

  .subtitle {
    font-size: 16px;
    opacity: 0.9;
  }
}

.register-box {
  background: white;
  border-radius: 12px;
  padding: 40px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.1);

  .box-title {
    font-size: 24px;
    font-weight: 600;
    text-align: center;
    margin-bottom: 30px;
    color: #333;
  }
}

.register-footer {
  text-align: center;
  margin-top: 24px;
  color: #666;

  span {
    margin-right: 4px;
  }
}

// 底部链接样式
.page-footer {
  margin-top: 40px;
  text-align: center;
  color: rgba(255, 255, 255, 0.8);

  .footer-links {
    display: flex;
    justify-content: center;
    gap: 20px;
    margin-bottom: 12px;
  }

  .footer-link {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.2);
    transition: all 0.3s ease;

    &:hover {
      background: rgba(255, 255, 255, 0.3);
      transform: translateY(-2px);
    }

    .footer-icon {
      width: 24px;
      height: 24px;
      fill: white;
    }
  }

  .footer-text {
    font-size: 14px;
    opacity: 0.8;
  }
}
</style>
