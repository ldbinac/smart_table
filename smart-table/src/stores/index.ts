import { createPinia } from "pinia";

export const pinia = createPinia();

export { useBaseStore } from "./baseStore";
export { useTableStore } from "./tableStore";
export { useViewStore } from "./viewStore";
export { useSettingsStore } from "./settingsStore";
