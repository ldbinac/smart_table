import { createPinia } from "pinia";

export const pinia = createPinia();

export { useBaseStore } from "./baseStore";
export { useAuthStore } from "./authStore";
export { useTableStore } from "./tableStore";
export { useViewStore } from "./viewStore";
export { useSettingsStore } from "./settingsStore";
export { useMemberStore } from "./memberStore";
export { useShareStore } from "./shareStore";
