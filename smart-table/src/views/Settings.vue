<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue';
import { useSettingsStore } from '@/stores';
import { useAuthStore } from '@/stores/auth/authStore';
import { Brush, Grid, DataLine, Calendar, RefreshLeft } from '@element-plus/icons-vue';
import { ElMessage, ElMessageBox } from 'element-plus';
import type { FormInstance, FormRules } from 'element-plus';
import apiClient from '@/api/client';

const settingsStore = useSettingsStore();
const authStore = useAuthStore();

// 修改密码相关
const passwordDialogVisible = ref(false);
const passwordFormRef = ref<FormInstance>();
const passwordLoading = ref(false);

const passwordForm = ref({
  oldPassword: '',
  newPassword: '',
  confirmPassword: ''
});

// 验证两次密码是否一致
const validateConfirmPassword = (_rule: any, value: string, callback: Function) => {
  if (value !== passwordForm.value.newPassword) {
    callback(new Error('两次输入的密码不一致'));
  } else {
    callback();
  }
};

// 密码强度验证
const validatePasswordStrength = (_rule: any, value: string, callback: Function) => {
  if (value.length < 8) {
    callback(new Error('密码长度至少为8位'));
    return;
  }
  if (!/[A-Z]/.test(value)) {
    callback(new Error('密码必须包含至少一个大写字母'));
    return;
  }
  if (!/[a-z]/.test(value)) {
    callback(new Error('密码必须包含至少一个小写字母'));
    return;
  }
  if (!/\d/.test(value)) {
    callback(new Error('密码必须包含至少一个数字'));
    return;
  }
  callback();
};

const passwordRules: FormRules = {
  oldPassword: [
    { required: true, message: '请输入当前密码', trigger: 'blur' }
  ],
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { validator: validatePasswordStrength, trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    { validator: validateConfirmPassword, trigger: 'blur' }
  ]
};

// 打开修改密码对话框
const openPasswordDialog = () => {
  passwordForm.value = {
    oldPassword: '',
    newPassword: '',
    confirmPassword: ''
  };
  passwordDialogVisible.value = true;
};

// 提交修改密码
const submitPasswordChange = async () => {
  if (!passwordFormRef.value) return;

  await passwordFormRef.value.validate(async (valid) => {
    if (!valid) return;

    passwordLoading.value = true;

    try {
      await apiClient.put('/auth/password', {
        old_password: passwordForm.value.oldPassword,
        new_password: passwordForm.value.newPassword
      });

      ElMessage.success('密码修改成功，请重新登录');
      passwordDialogVisible.value = false;

      // 延迟后登出并跳转到登录页
      setTimeout(async () => {
        await authStore.logout();
      }, 1500);

    } catch (error: any) {
      const message = error?.response?.data?.message || '密码修改失败';
      const errorCode = error?.response?.data?.error;

      if (errorCode === 'invalid_old_password') {
        ElMessage.error('当前密码错误');
      } else {
        ElMessage.error(message);
      }
    } finally {
      passwordLoading.value = false;
    }
  });
};

// 监听打开修改密码对话框事件
const handleOpenPasswordDialog = () => {
  openPasswordDialog();
};

onMounted(() => {
  window.addEventListener('open-change-password-dialog', handleOpenPasswordDialog);
});

onUnmounted(() => {
  window.removeEventListener('open-change-password-dialog', handleOpenPasswordDialog);
});
</script>

<template>
  <div class="settings-page">
    <header class="settings-header">
      <div class="header-icon">
        <el-icon :size="28"><Brush /></el-icon>
      </div>
      <div class="header-content">
        <h1>系统设置</h1>
        <p class="header-desc">自定义您的 Smart Table 使用体验</p>
      </div>
    </header>

    <main class="settings-content">
      <!-- 外观设置 -->
      <section class="settings-section">
        <div class="section-header">
          <div class="section-icon">
            <el-icon><Brush /></el-icon>
          </div>
          <h2>外观设置</h2>
        </div>
        <div class="section-body">
          <div class="setting-item">
            <div class="setting-label">
              <span>主题模式</span>
              <span class="setting-desc">选择您喜欢的界面主题</span>
            </div>
            <div class="setting-control">
              <el-radio-group
                :model-value="settingsStore.settings.theme"
                @change="(val) => settingsStore.setTheme(val as 'light' | 'dark' | 'auto')"
                size="large"
              >
                <el-radio-button value="light">
                  <el-icon><Sunny /></el-icon>
                  浅色
                </el-radio-button>
                <el-radio-button value="dark">
                  <el-icon><Moon /></el-icon>
                  深色
                </el-radio-button>
                <el-radio-button value="auto">
                  <el-icon><Monitor /></el-icon>
                  跟随系统
                </el-radio-button>
              </el-radio-group>
            </div>
          </div>

          <div class="setting-item">
            <div class="setting-label">
              <span>界面语言</span>
              <span class="setting-desc">选择您偏好的显示语言</span>
            </div>
            <div class="setting-control">
              <el-select
                :model-value="settingsStore.settings.language"
                @change="(val) => settingsStore.setLanguage(val as 'zh-CN' | 'en-US')"
                size="large"
                style="width: 200px"
              >
                <el-option label="简体中文" value="zh-CN">
                  <span class="lang-option">🇨🇳 简体中文</span>
                </el-option>
                <el-option label="English" value="en-US">
                  <span class="lang-option">🇺🇸 English</span>
                </el-option>
              </el-select>
            </div>
          </div>
        </div>
      </section>

      <!-- 表格设置 -->
      <section class="settings-section">
        <div class="section-header">
          <div class="section-icon">
            <el-icon><Grid /></el-icon>
          </div>
          <h2>表格设置</h2>
        </div>
        <div class="section-body">
          <div class="setting-item">
            <div class="setting-label">
              <span>行高设置</span>
              <span class="setting-desc">调整表格行的显示密度</span>
            </div>
            <div class="setting-control">
              <el-radio-group
                :model-value="settingsStore.settings.tableRowHeight"
                @change="(val) => settingsStore.updateSettings('tableRowHeight', val as 'short' | 'medium' | 'tall')"
                size="large"
              >
                <el-radio-button value="short">紧凑</el-radio-button>
                <el-radio-button value="medium">中等</el-radio-button>
                <el-radio-button value="tall">宽松</el-radio-button>
              </el-radio-group>
            </div>
          </div>

          <div class="setting-item">
            <div class="setting-label">
              <span>显示网格线</span>
              <span class="setting-desc">在单元格之间显示分隔线</span>
            </div>
            <div class="setting-control">
              <el-switch
                :model-value="settingsStore.settings.showGridLines"
                @change="(val) => settingsStore.updateSettings('showGridLines', val as boolean)"
                size="large"
              />
            </div>
          </div>

          <div class="setting-item">
            <div class="setting-label">
              <span>斑马纹效果</span>
              <span class="setting-desc">交替行显示不同背景色</span>
            </div>
            <div class="setting-control">
              <el-switch
                :model-value="settingsStore.settings.stripeRows"
                @change="(val) => settingsStore.updateSettings('stripeRows', val as boolean)"
                size="large"
              />
            </div>
          </div>
        </div>
      </section>

      <!-- 数据设置 -->
      <section class="settings-section">
        <div class="section-header">
          <div class="section-icon">
            <el-icon><DataLine /></el-icon>
          </div>
          <h2>数据设置</h2>
        </div>
        <div class="section-body">
          <div class="setting-item">
            <div class="setting-label">
              <span>自动保存</span>
              <span class="setting-desc">自动保存您的更改到本地存储</span>
            </div>
            <div class="setting-control">
              <el-switch
                :model-value="settingsStore.settings.autoSave"
                @change="(val) => settingsStore.updateSettings('autoSave', val as boolean)"
                size="large"
              />
            </div>
          </div>

          <div class="setting-item">
            <div class="setting-label">
              <span>删除前确认</span>
              <span class="setting-desc">删除数据前显示确认对话框</span>
            </div>
            <div class="setting-control">
              <el-switch
                :model-value="settingsStore.settings.confirmBeforeDelete"
                @change="(val) => settingsStore.updateSettings('confirmBeforeDelete', val as boolean)"
                size="large"
              />
            </div>
          </div>
        </div>
      </section>

      <!-- 格式设置 -->
      <section class="settings-section">
        <div class="section-header">
          <div class="section-icon">
            <el-icon><Calendar /></el-icon>
          </div>
          <h2>格式设置</h2>
        </div>
        <div class="section-body">
          <div class="setting-item">
            <div class="setting-label">
              <span>日期格式</span>
              <span class="setting-desc">设置日期的显示格式</span>
            </div>
            <div class="setting-control">
              <el-input
                :model-value="settingsStore.settings.dateFormat"
                @change="(val) => settingsStore.updateSettings('dateFormat', val as string)"
                placeholder="YYYY-MM-DD"
                size="large"
                style="width: 200px"
              />
            </div>
          </div>

          <div class="setting-item">
            <div class="setting-label">
              <span>时间格式</span>
              <span class="setting-desc">设置时间的显示格式</span>
            </div>
            <div class="setting-control">
              <el-input
                :model-value="settingsStore.settings.timeFormat"
                @change="(val) => settingsStore.updateSettings('timeFormat', val as string)"
                placeholder="HH:mm:ss"
                size="large"
                style="width: 200px"
              />
            </div>
          </div>

          <div class="setting-item">
            <div class="setting-label">
              <span>货币符号</span>
              <span class="setting-desc">设置货币字段的显示符号</span>
            </div>
            <div class="setting-control">
              <el-input
                :model-value="settingsStore.settings.currencySymbol"
                @change="(val) => settingsStore.updateSettings('currencySymbol', val as string)"
                placeholder="¥"
                size="large"
                style="width: 200px"
              />
            </div>
          </div>
        </div>
      </section>

      <!-- 重置按钮 -->
      <div class="reset-section">
        <el-button
          type="danger"
          size="large"
          @click="settingsStore.resetSettings"
          class="reset-btn"
        >
          <el-icon><RefreshLeft /></el-icon>
          重置为默认设置
        </el-button>
        <p class="reset-hint">此操作将恢复所有设置到初始状态，不可撤销</p>
      </div>
    </main>

    <!-- 修改密码对话框 -->
    <el-dialog
      v-model="passwordDialogVisible"
      title="修改密码"
      width="450px"
      :close-on-click-modal="false"
    >
      <el-form
        ref="passwordFormRef"
        :model="passwordForm"
        :rules="passwordRules"
        label-position="top"
      >
        <el-form-item label="当前密码" prop="oldPassword">
          <el-input
            v-model="passwordForm.oldPassword"
            type="password"
            placeholder="请输入当前密码"
            show-password
          />
        </el-form-item>

        <el-form-item label="新密码" prop="newPassword">
          <el-input
            v-model="passwordForm.newPassword"
            type="password"
            placeholder="请输入新密码"
            show-password
          />
          <div class="password-hint">
            密码长度至少8位，需包含大小写字母和数字
          </div>
        </el-form-item>

        <el-form-item label="确认新密码" prop="confirmPassword">
          <el-input
            v-model="passwordForm.confirmPassword"
            type="password"
            placeholder="请再次输入新密码"
            show-password
          />
        </el-form-item>
      </el-form>

      <template #footer>
        <el-button @click="passwordDialogVisible = false">取消</el-button>
        <el-button
          type="primary"
          :loading="passwordLoading"
          @click="submitPasswordChange"
        >
          确认修改
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script lang="ts">
import { Sunny, Moon, Monitor } from '@element-plus/icons-vue';

export default {
  name: 'SettingsView',
};
</script>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;

.settings-page {
  padding: 32px;
  max-width: 900px;
  margin: 0 auto;
  background: linear-gradient(180deg, $gray-50 0%, $surface-color 100%);
  min-height: 100vh;
}

.settings-header {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 32px;
  padding: 24px;
  background: $surface-color;
  border-radius: $border-radius-xl;
  box-shadow: $shadow-sm;

  .header-icon {
    width: 56px;
    height: 56px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: linear-gradient(135deg, $primary-color 0%, $primary-dark 100%);
    border-radius: $border-radius-lg;
    color: white;
  }

  .header-content {
    h1 {
      font-size: $font-size-2xl;
      font-weight: 700;
      color: $gray-800;
      margin: 0 0 4px;
    }

    .header-desc {
      font-size: $font-size-base;
      color: $gray-500;
      margin: 0;
    }
  }
}

.settings-content {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.settings-section {
  background: $surface-color;
  border-radius: $border-radius-xl;
  box-shadow: $shadow-sm;
  overflow: hidden;
  transition: box-shadow $transition-normal;

  &:hover {
    box-shadow: $shadow-md;
  }
}

.section-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 24px;
  background: linear-gradient(90deg, $gray-50 0%, $surface-color 100%);
  border-bottom: 1px solid $gray-100;

  .section-icon {
    width: 40px;
    height: 40px;
    display: flex;
    align-items: center;
    justify-content: center;
    background: rgba($primary-color, 0.1);
    border-radius: $border-radius-md;
    color: $primary-color;
    font-size: 20px;
  }

  h2 {
    font-size: $font-size-lg;
    font-weight: 600;
    color: $gray-800;
    margin: 0;
  }
}

.section-body {
  padding: 8px 24px;
}

.setting-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 0;
  border-bottom: 1px solid $gray-100;

  &:last-child {
    border-bottom: none;
  }
}

.setting-label {
  display: flex;
  flex-direction: column;
  gap: 4px;

  span:first-child {
    font-size: $font-size-base;
    font-weight: 500;
    color: $gray-700;
  }

  .setting-desc {
    font-size: $font-size-sm;
    color: $gray-400;
  }
}

.setting-control {
  :deep(.el-radio-group) {
    .el-radio-button {
      &__inner {
        padding: 12px 20px;
        font-size: $font-size-base;
      }
    }
  }

  :deep(.el-switch) {
    --el-switch-on-color: #{$primary-color};
  }
}

.lang-option {
  display: flex;
  align-items: center;
  gap: 8px;
}

.reset-section {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 32px;
  background: $surface-color;
  border-radius: $border-radius-xl;
  box-shadow: $shadow-sm;

  .reset-btn {
    padding: 14px 32px;
    font-size: $font-size-base;
    font-weight: 500;
    border-radius: $border-radius-lg;

    .el-icon {
      margin-right: 8px;
    }
  }

  .reset-hint {
    font-size: $font-size-sm;
    color: $gray-400;
    margin: 0;
  }
}

.password-hint {
  font-size: $font-size-sm;
  color: $gray-400;
  margin-top: 4px;
}

// 响应式适配
@media (max-width: 768px) {
  .settings-page {
    padding: 16px;
  }

  .settings-header {
    flex-direction: column;
    text-align: center;
    padding: 20px;

    .header-content {
      h1 {
        font-size: $font-size-xl;
      }
    }
  }

  .setting-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 16px;
  }

  .setting-control {
    width: 100%;

    :deep(.el-radio-group) {
      display: flex;
      width: 100%;

      .el-radio-button {
        flex: 1;

        &__inner {
          padding: 10px 12px;
          font-size: $font-size-sm;
        }
      }
    }
  }
}
</style>
