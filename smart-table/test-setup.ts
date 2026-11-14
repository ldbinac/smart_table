import 'fake-indexeddb/auto';
import { config } from '@vue/test-utils';
import ElementPlus from 'element-plus';
import i18n from '@/i18n';

// 强制设置中文语言，避免 jsdom 环境下 navigator.language 默认值导致的英文翻译
// 注意：ES module 的 import 会被提升，localStorage.setItem 必须放在 import 之前不行，
// 因为 i18n 模块在被 import 时就已经初始化了 locale。
// 所以这里直接修改 i18n 实例的 locale。
i18n.global.locale.value = 'zh-CN';

// 全局注册 Element Plus 组件，解决测试中 el-* 组件未解析的警告
// 同时注册 vue-i18n，确保使用 useI18n() 的组件在测试中可用
config.global.plugins = [ElementPlus, i18n];
// 禁用 teleport，确保弹出层内容渲染在组件 wrapper 内，便于测试查找元素
config.global.stubs = { teleport: true };
