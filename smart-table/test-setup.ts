import 'fake-indexeddb/auto';
import { config } from '@vue/test-utils';
import ElementPlus from 'element-plus';
import i18n from '@/i18n';

// 全局注册 Element Plus 组件，解决测试中 el-* 组件未解析的警告
// 同时注册 vue-i18n，确保使用 useI18n() 的组件在测试中可用
config.global.plugins = [ElementPlus, i18n];
// 禁用 teleport，确保弹出层内容渲染在组件 wrapper 内，便于测试查找元素
config.global.stubs = { teleport: true };
