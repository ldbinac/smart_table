<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted } from "vue";
import { ElMessage } from "element-plus";
import {
  buildGitHubIssueUrl,
  buildGiteeIssueUrl,
  buildMailtoLink,
  buildIssueBody,
  openInNewTab,
  copyToClipboard,
  WECHAT_QR_PATH,
} from "@/utils/feedback";

const props = defineProps<{
  visible: boolean;
}>();

const emit = defineEmits<{
  "update:visible": [value: boolean];
}>();

// 内部视图状态：渠道列表 或 公众号二维码
const view = ref<"channels" | "qrcode">("channels");

// 弹窗打开时重置为渠道列表视图
watch(
  () => props.visible,
  (val) => {
    if (val) {
      view.value = "channels";
    }
  },
);

function close() {
  emit("update:visible", false);
}

function handleGitHubClick() {
  openInNewTab(buildGitHubIssueUrl());
  close();
}

async function handleGiteeClick() {
  // Gitee Web 表单不支持 URL 查询参数预填充，
  // 改为复制模板到剪贴板 + 跳转到新建页
  const body = buildIssueBody();
  const ok = await copyToClipboard(body);
  if (ok) {
    ElMessage.success("反馈模板已复制，请在 Gitee 新建 Issue 时粘贴");
  } else {
    ElMessage.warning("复制失败，请手动填写反馈内容");
  }
  openInNewTab(buildGiteeIssueUrl());
  close();
}

function handleEmailClick() {
  window.location.href = buildMailtoLink();
  close();
}

function showQrcode() {
  view.value = "qrcode";
}

function backToChannels() {
  view.value = "channels";
}

// ESC 键关闭
function handleKeydown(e: KeyboardEvent) {
  if (e.key === "Escape" && props.visible) {
    close();
  }
}

onMounted(() => {
  window.addEventListener("keydown", handleKeydown);
});

onUnmounted(() => {
  window.removeEventListener("keydown", handleKeydown);
});
</script>

<template>
  <Teleport to="body">
    <Transition name="fade">
      <div
        v-if="visible"
        class="feedback-overlay"
        @click="close">
        <Transition name="scale">
          <div
            v-if="visible"
            class="feedback-dialog"
            @click.stop>
            <!-- 头部 -->
            <div class="feedback-header">
              <h2>问题反馈</h2>
              <button
                class="close-btn"
                title="关闭"
                @click="close">
                ✕
              </button>
            </div>

            <!-- 内容区 -->
            <div class="feedback-content">
              <!-- 渠道列表视图 -->
              <template v-if="view === 'channels'">
                <p class="feedback-intro">
                  感谢您的反馈！请选择以下任一渠道提交您的问题或建议，系统会自动附带环境信息以便定位问题。
                </p>
                <div class="channels-grid">
                  <!-- GitHub Issues -->
                  <div class="channel-card">
                    <div class="channel-icon github-icon">
                      <svg viewBox="0 0 24 24" fill="currentColor">
                        <path
                          d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
                      </svg>
                    </div>
                    <div class="channel-info">
                      <h3>GitHub Issues</h3>
                      <p>跳转到 GitHub 仓库提交 Issue（新标签页打开，预填充系统信息）</p>
                    </div>
                    <el-button
                      type="primary"
                      plain
                      @click="handleGitHubClick">
                      前往提交
                    </el-button>
                  </div>

                  <!-- Gitee Issues -->
                  <div class="channel-card">
                    <div class="channel-icon gitee-icon">
                      <svg viewBox="0 0 24 24" fill="currentColor">
                        <path
                          d="M11.984 0A12 12 0 0 0 0 12a12 12 0 0 0 12 12 12 12 0 0 0 12-12A12 12 0 0 0 12 0a12 12 0 0 0-.016 0zm6.09 5.333c.328 0 .593.266.592.593v1.482a.594.594 0 0 1-.593.592H9.777c-.982 0-1.778.796-1.778 1.778v5.63c0 .327.266.592.593.592h5.63c.982 0 1.778-.796 1.778-1.778v-.296a.594.594 0 0 0-.592-.593h-4.15a.594.594 0 0 1-.592-.592v-1.482a.594.594 0 0 1 .593-.592h6.815c.327 0 .593.265.593.592v3.408a4 4 0 0 1-4 4H6.074a.594.594 0 0 1-.593-.593V9.778a4.444 4.444 0 0 1 4.445-4.444h8.148z" />
                      </svg>
                    </div>
                    <div class="channel-info">
                      <h3>Gitee Issues</h3>
                      <p>跳转到 Gitee 新建 Issue 页（模板自动复制到剪贴板，粘贴即可）</p>
                    </div>
                    <el-button
                      type="primary"
                      plain
                      @click="handleGiteeClick">
                      前往提交
                    </el-button>
                  </div>

                  <!-- 邮件反馈 -->
                  <div class="channel-card">
                    <div class="channel-icon email-icon">
                      <svg viewBox="0 0 24 24" fill="currentColor">
                        <path
                          d="M20 4H4c-1.1 0-1.99.9-1.99 2L2 18c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 4l-8 5-8-5V6l8 5 8-5v2z" />
                      </svg>
                    </div>
                    <div class="channel-info">
                      <h3>邮件反馈</h3>
                      <p>调用系统默认邮件客户端，自动填充收件人、主题与正文模板</p>
                    </div>
                    <el-button
                      type="primary"
                      plain
                      @click="handleEmailClick">
                      发送邮件
                    </el-button>
                  </div>

                  <!-- 公众号关注 -->
                  <div class="channel-card">
                    <div class="channel-icon wechat-icon">
                      <svg viewBox="0 0 576 512" fill="currentColor">
                        <path
                          d="M385.2 167.6c6.4 0 12.6.3 18.8 1.1C398.3 109.7 315.1 64 216.7 64 97.2 64 0 132.1 0 216.7c0 49.3 27.3 93.7 70.2 123.8-3.1 18.8-12.1 50.2-12.7 52.7-.9 3.5 1.4 6.9 5.1 6.9 1.5 0 2.9-.5 4.1-1.5l54.6-37.6c19.5 5.2 40.2 7.9 61.6 7.9 5.4 0 10.7-.2 16-.6-2.8-13.1-4.3-26.7-4.3-40.6 0-85.1 84.1-154.3 188-154.3zm-140.8-47c14.5 0 26.3 11.8 26.3 26.3s-11.8 26.3-26.3 26.3-26.3-11.8-26.3-26.3 11.8-26.3 26.3-26.3zm72.5 0c14.5 0 26.3 11.8 26.3 26.3s-11.8 26.3-26.3 26.3-26.3-11.8-26.3-26.3 11.8-26.3 26.3-26.3zM575.9 330.7c0-75.7-76.1-137.1-170-137.1-93.8 0-170 61.4-170 137.1 0 75.7 76.1 137.1 170 137.1 18.8 0 37-2.4 54.3-6.9l47.4 32.6c1.3.9 2.8 1.4 4.3 1.4 3.5 0 6.3-2.8 6.3-6.3 0-.6-.1-1.1-.2-1.7-.6-2.4-9.4-31-12.3-48.9 38.8-27.2 63.5-70.6 63.5-119.2zm-215.5-18.3c-10.1 0-18.3-8.2-18.3-18.3s8.2-18.3 18.3-18.3 18.3 8.2 18.3 18.3-8.2 18.3-18.3 18.3zm72.7 0c-10.1 0-18.3-8.2-18.3-18.3s8.2-18.3 18.3-18.3 18.3 8.2 18.3 18.3-8.2 18.3-18.3 18.3z" />
                      </svg>
                    </div>
                    <div class="channel-info">
                      <h3>公众号关注反馈</h3>
                      <p>扫码关注 SmartTable 公众号，通过菜单联系反馈</p>
                    </div>
                    <el-button
                      type="primary"
                      plain
                      @click="showQrcode">
                      查看二维码
                    </el-button>
                  </div>
                </div>
              </template>

              <!-- 公众号二维码视图 -->
              <template v-else>
                <div class="qrcode-view">
                  <img
                    :src="WECHAT_QR_PATH"
                    alt="SmartTable 公众号二维码"
                    class="qrcode-img" />
                  <p class="qrcode-tip">
                    扫码关注 SmartTable 公众号，通过菜单联系反馈
                  </p>
                  <el-button
                    type="primary"
                    plain
                    @click="backToChannels">
                    返回选择渠道
                  </el-button>
                </div>
              </template>
            </div>

            <!-- 底部 -->
            <div class="feedback-footer">
              <el-button @click="close">取消</el-button>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;

.feedback-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background-color: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
}

.feedback-dialog {
  background-color: var(--surface-color, $surface-color);
  border-radius: $border-radius-xl;
  box-shadow: $shadow-lg;
  width: 90%;
  max-width: 640px;
  max-height: 85vh;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.feedback-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: $spacing-lg $spacing-xl;
  border-bottom: 1px solid var(--border-color, $border-color);

  h2 {
    font-size: $font-size-xl;
    font-weight: 600;
    color: var(--text-primary, $text-primary);
    margin: 0;
  }
}

.close-btn {
  background: none;
  border: none;
  font-size: $font-size-xl;
  color: var(--text-secondary, $text-secondary);
  cursor: pointer;
  padding: $spacing-xs;
  line-height: 1;
  transition: color $transition-fast;

  &:hover {
    color: var(--text-primary, $text-primary);
  }
}

.feedback-content {
  flex: 1;
  overflow-y: auto;
  padding: $spacing-xl;
}

.feedback-intro {
  margin: 0 0 $spacing-lg;
  font-size: $font-size-sm;
  color: var(--text-secondary, $text-secondary);
  line-height: 1.6;
}

.channels-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: $spacing-md;
}

.channel-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: $spacing-sm;
  padding: $spacing-lg;
  border: 1px solid var(--border-color, $border-color);
  border-radius: $border-radius-lg;
  background-color: var(--bg-color, $bg-color);
  transition: border-color $transition-fast, box-shadow $transition-fast;

  &:hover {
    border-color: $primary-color;
    box-shadow: $shadow-sm;
  }
}

.channel-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 48px;
  height: 48px;
  border-radius: $border-radius-full;
  background-color: $primary-light;

  svg {
    width: 26px;
    height: 26px;
  }

  &.github-icon {
    color: #24292e;
    background-color: #f3f4f6;
  }

  &.gitee-icon {
    color: #c71d23;
    background-color: #fef2f2;
  }

  &.email-icon {
    color: $primary-color;
    background-color: $primary-light;
  }

  &.wechat-icon {
    color: #07c160;
    background-color: #e8f8ee;
  }
}

.channel-info {
  text-align: center;

  h3 {
    margin: 0 0 $spacing-xs;
    font-size: $font-size-base;
    font-weight: 600;
    color: var(--text-primary, $text-primary);
  }

  p {
    margin: 0;
    font-size: $font-size-xs;
    color: var(--text-secondary, $text-secondary);
    line-height: 1.5;
  }
}

.qrcode-view {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: $spacing-md;
  padding: $spacing-lg 0;
}

.qrcode-img {
  width: 360px;
  height: auto;
  border-radius: $border-radius-lg;
  display: block;
  border: 1px solid var(--border-color, $border-color);
}

.qrcode-tip {
  margin: 0;
  font-size: $font-size-sm;
  color: var(--text-secondary, $text-secondary);
  text-align: center;
}

.feedback-footer {
  padding: $spacing-md $spacing-xl;
  border-top: 1px solid var(--border-color, $border-color);
  display: flex;
  justify-content: flex-end;
}

// 窄屏适配
@media (max-width: 768px) {
  .feedback-dialog {
    width: 92vw;
    max-width: none;
  }

  .channels-grid {
    grid-template-columns: 1fr;
  }

  .channel-card {
    flex-direction: row;
    align-items: center;
    text-align: left;

    .channel-info {
      flex: 1;
      text-align: left;
    }
  }

  .qrcode-img {
    width: 200px;
  }
}
</style>
