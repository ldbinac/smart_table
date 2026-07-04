<template>
  <div class="auth-page">
    <div class="brand-section">
      <img
        src="/SmartTable.png"
        alt="SmartTable Logo"
        class="brand-logo" />
      <h1 class="brand-title">SmartTable</h1>
      <p class="brand-subtitle">多维表格管理系统</p>
      <p class="brand-slogan">让数据管理更简单、更高效</p>
    </div>

    <div class="form-section">
      <div class="auth-container">
        <div class="auth-box" :class="boxClass">
          <h2 class="box-title">{{ title }}</h2>

          <div v-if="demoConfig?.is_demo_environment" class="demo-star-tip">
            <el-icon><Star /></el-icon>
            <span>
              Tip：请先 watch 本项目后再访问：
              <a
                :href="demoConfig.gitee_repo_url"
                target="_blank"
                rel="noopener noreferrer">
                点击 watch 和关注
              </a>
            </span>
          </div>

          <slot />

          <div v-if="footerHint" class="auth-footer">
            <span>{{ footerHint }}</span>
            <el-link type="primary" @click="$router.push(footerLinkTo || '/')">
              {{ footerLinkText }}
            </el-link>
          </div>
        </div>

        <!-- 底部链接 -->
        <div class="page-footer">
          <div class="footer-links">
            <a
              class="footer-link wechat-link"
              title="微信公众号"
              @click="showWechatQR = true">
              <svg class="footer-icon" viewBox="0 0 576 512" fill="currentColor">
                <path
                  d="M385.2 167.6c6.4 0 12.6.3 18.8 1.1C398.3 109.7 315.1 64 216.7 64 97.2 64 0 132.1 0 216.7c0 49.3 27.3 93.7 70.2 123.8-3.1 18.8-12.1 50.2-12.7 52.7-.9 3.5 1.4 6.9 5.1 6.9 1.5 0 2.9-.5 4.1-1.5l54.6-37.6c19.5 5.2 40.2 7.9 61.6 7.9 5.4 0 10.7-.2 16-.6-2.8-13.1-4.3-26.7-4.3-40.6 0-85.1 84.1-154.3 188-154.3zm-140.8-47c14.5 0 26.3 11.8 26.3 26.3s-11.8 26.3-26.3 26.3-26.3-11.8-26.3-26.3 11.8-26.3 26.3-26.3zm72.5 0c14.5 0 26.3 11.8 26.3 26.3s-11.8 26.3-26.3 26.3-26.3-11.8-26.3-26.3 11.8-26.3 26.3-26.3zM575.9 330.7c0-75.7-76.1-137.1-170-137.1-93.8 0-170 61.4-170 137.1 0 75.7 76.1 137.1 170 137.1 18.8 0 37-2.4 54.3-6.9l47.4 32.6c1.3.9 2.8 1.4 4.3 1.4 3.5 0 6.3-2.8 6.3-6.3 0-.6-.1-1.1-.2-1.7-.6-2.4-9.4-31-12.3-48.9 38.8-27.2 63.5-70.6 63.5-119.2zm-215.5-18.3c-10.1 0-18.3-8.2-18.3-18.3s8.2-18.3 18.3-18.3 18.3 8.2 18.3 18.3-8.2 18.3-18.3 18.3zm72.7 0c-10.1 0-18.3-8.2-18.3-18.3s8.2-18.3 18.3-18.3 18.3 8.2 18.3 18.3-8.2 18.3-18.3 18.3z" />
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
            
          </div>
          <p class="footer-text">SmartTable - 开源多维表格管理系统</p>
        </div>
      </div>
    </div>

    <el-dialog
      v-model="showWechatQR"
      title="微信公众号"
      width="320px"
      align-center
      :show-close="true">
      <img
        src="/wechat_official_account.png"
        alt="微信公众号二维码"
        style="width: 100%; border-radius: 8px; display: block;" />
      <p style="text-align: center; color: #666; margin-top: 12px; font-size: 14px;">扫码关注微信公众号</p>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue';
import { Star } from '@element-plus/icons-vue'
import type { DemoConfig } from '@/api/types'

defineProps<{
  title: string;
  footerHint?: string;
  footerLinkText?: string;
  footerLinkTo?: string;
  boxClass?: string;
  demoConfig?: DemoConfig | null;
}>();

const showWechatQR = ref(false);
</script>

<style scoped lang="scss">
.auth-page {
  min-height: 100vh;
  display: flex;
  position: relative;
  overflow: hidden;
  background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 50%, #9333ea 100%);

  &::before {
    content: '';
    position: absolute;
    inset: 0;
    background-image:
      radial-gradient(circle at 20% 30%, rgba(255, 255, 255, 0.12) 0%, transparent 40%),
      radial-gradient(circle at 80% 70%, rgba(255, 255, 255, 0.08) 0%, transparent 40%);
    pointer-events: none;
  }
}

.brand-section {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  position: relative;
  color: white;
  padding: 60px;
  text-align: center;

  &::before {
    content: '';
    position: absolute;
    width: 500px;
    height: 500px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba(255, 255, 255, 0.15) 0%, transparent 70%);
    filter: blur(40px);
    pointer-events: none;
  }

  .brand-logo {
    width: 180px;
    height: auto;
    margin-bottom: 32px;
    filter: drop-shadow(0 8px 24px rgba(0, 0, 0, 0.2));
    position: relative;
    z-index: 1;
  }

  .brand-title {
    font-size: 52px;
    font-weight: 800;
    margin-bottom: 16px;
    letter-spacing: -0.5px;
    position: relative;
    z-index: 1;
    text-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  }

  .brand-subtitle {
    font-size: 22px;
    font-weight: 400;
    opacity: 0.92;
    margin-bottom: 12px;
    position: relative;
    z-index: 1;
  }

  .brand-slogan {
    font-size: 16px;
    opacity: 0.7;
    font-weight: 300;
    position: relative;
    z-index: 1;
  }
}

.form-section {
  flex: 0 0 40%;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  padding: 40px;
  background: linear-gradient(
    180deg,
    rgba(255, 255, 255, 0.22) 0%,
    rgba(255, 255, 255, 0.12) 100%
  );
  backdrop-filter: blur(24px);
  border-left: 1px solid rgba(255, 255, 255, 0.25);
}

.auth-container {
  width: 100%;
  max-width: 420px;
}

.auth-box {
  background: rgba(255, 255, 255, 0.82);
  border-radius: 20px;
  padding: 48px;
  box-shadow:
    0 24px 60px rgba(0, 0, 0, 0.18),
    0 8px 20px rgba(0, 0, 0, 0.1),
    inset 0 1px 0 rgba(255, 255, 255, 0.6);
  position: relative;
  overflow: hidden;
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.35);

  &::before {
    content: '';
    position: absolute;
    top: 0;
    left: 0;
    right: 0;
    height: 4px;
    background: linear-gradient(90deg, #4f46e5, #7c3aed, #9333ea);
  }

  .box-title {
    font-size: 28px;
    font-weight: 700;
    text-align: center;
    margin-bottom: 32px;
    background: linear-gradient(135deg, #4f46e5 0%, #7c3aed 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }
}

.auth-footer {
  text-align: center;
  margin-top: 24px;
  color: #666;
  font-size: 14px;

  span {
    margin-right: 4px;
  }
}

// 底部链接样式
.page-footer {
  margin-top: 32px;
  text-align: center;
  color: rgba(255, 255, 255, 0.85);

  .footer-links {
    display: flex;
    justify-content: center;
    gap: 16px;
    margin-bottom: 12px;
  }

  .footer-link {
    display: flex;
    align-items: center;
    justify-content: center;
    width: 40px;
    height: 40px;
    border-radius: 50%;
    background: rgba(255, 255, 255, 0.15);
    border: 1px solid rgba(255, 255, 255, 0.2);
    transition: all 0.3s ease;

    &:hover {
      background: rgba(255, 255, 255, 0.25);
      transform: translateY(-2px);
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
    }

    .footer-icon {
      width: 22px;
      height: 22px;
      fill: white;
    }

    &.wechat-link {
      cursor: pointer;

      &:hover {
        background: rgba(255, 255, 255, 0.25);
      }

      .footer-icon {
        fill: white;
      }
    }
  }

  .footer-text {
    font-size: 13px;
    opacity: 0.8;
  }
}

@media (max-width: 768px) {
  .auth-page {
    flex-direction: column;
  }

  .brand-section {
    flex: 0 0 auto;
    padding: 48px 24px 24px;

    &::before {
      width: 300px;
      height: 300px;
    }

    .brand-logo {
      width: 90px;
      margin-bottom: 16px;
    }

    .brand-title {
      font-size: 32px;
      margin-bottom: 8px;
    }

    .brand-subtitle {
      font-size: 14px;
      margin-bottom: 4px;
    }

    .brand-slogan {
      display: none;
    }
  }

  .form-section {
    flex: 1;
    padding: 24px;
    border-left: none;
    border-top: 1px solid rgba(255, 255, 255, 0.1);
  }

  .auth-box {
    padding: 32px 24px;
    border-radius: 16px;

    .box-title {
      font-size: 24px;
      margin-bottom: 24px;
    }
  }
}

.demo-star-tip {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 12px 16px;
  margin-bottom: 24px;
  background: linear-gradient(135deg, #fff7ed 0%, #ffedd5 100%);
  border: 1px solid #fdba74;
  border-radius: 12px;
  color: #9a3412;
  font-size: 14px;
  line-height: 1.5;

  .el-icon {
    margin-top: 2px;
    flex-shrink: 0;
  }

  a {
    color: #ea580c;
    font-weight: 600;
    text-decoration: underline;

    &:hover {
      color: #c2410c;
    }
  }
}
</style>
