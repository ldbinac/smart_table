<script setup lang="ts">
import { ref, watch, computed, onMounted } from "vue";
import {
  ElButton,
  ElButtonGroup,
  ElTooltip,
} from "element-plus";
import { List, Remove } from "@element-plus/icons-vue";
import { sanitizeHtml } from "@/utils/helpers";

interface Props {
  modelValue: string | null;
  readonly?: boolean;
  placeholder?: string;
  maxLength?: number;
}

const props = withDefaults(defineProps<Props>(), {
  modelValue: null,
  readonly: false,
  placeholder: "请输入内容...",
  maxLength: undefined,
});

const emit = defineEmits<{
  (e: "update:modelValue", value: string | null): void;
}>();

const editorRef = ref<HTMLDivElement>();
const isFocused = ref(false);

// 当前内容（HTML格式）
const currentHtml = computed({
  get: () => props.modelValue || "",
  set: (val: string) => {
    emit("update:modelValue", val || null);
  },
});

// 纯文本长度
const plainTextLength = computed(() => {
  if (!currentHtml.value) return 0;
  const temp = document.createElement("div");
  temp.innerHTML = currentHtml.value;
  return temp.textContent?.length || 0;
});

// 是否超过最大长度
const isOverLimit = computed(() => {
  if (!props.maxLength) return false;
  return plainTextLength.value > props.maxLength;
});

// 净化后的HTML（用于只读模式安全渲染）
const sanitizedHtml = computed(() => {
  if (!currentHtml.value) return '';
  return sanitizeHtml(currentHtml.value);
});

// 执行编辑器命令
function execCommand(command: string, value: string = "") {
  if (props.readonly) return;
  document.execCommand(command, false, value);
  updateContent();
  editorRef.value?.focus();
}

// 更新内容
function updateContent() {
  if (editorRef.value) {
    const html = editorRef.value.innerHTML;
    // 如果内容为空（只有<br>或空字符串），则设为null
    const isEmpty = !html || html === "<br>" || html === "<div><br></div>";
    currentHtml.value = isEmpty ? null : html;
  }
}

// 处理输入
function handleInput() {
  updateContent();
}

// 处理粘贴（纯文本粘贴）
function handlePaste(e: ClipboardEvent) {
  if (props.readonly) {
    e.preventDefault();
    return;
  }
  
  // 检查是否超过最大长度
  if (props.maxLength) {
    const pasteText = e.clipboardData?.getData("text/plain") || "";
    if (plainTextLength.value + pasteText.length > props.maxLength) {
      e.preventDefault();
      // 只允许粘贴部分文本
      const allowedLength = props.maxLength - plainTextLength.value;
      if (allowedLength > 0) {
        const allowedText = pasteText.substring(0, allowedLength);
        document.execCommand("insertText", false, allowedText);
      }
      return;
    }
  }
  
  // 默认粘贴为纯文本
  e.preventDefault();
  const text = e.clipboardData?.getData("text/plain") || "";
  document.execCommand("insertText", false, text);
}

// 处理键盘事件
function handleKeyDown(e: KeyboardEvent) {
  if (props.readonly) {
    e.preventDefault();
    return;
  }
  
  // 检查是否超过最大长度（仅对可打印字符）
  if (props.maxLength && e.key.length === 1 && !e.ctrlKey && !e.metaKey) {
    if (plainTextLength.value >= props.maxLength) {
      e.preventDefault();
      return;
    }
  }
  
  // 快捷键支持
  if (e.ctrlKey || e.metaKey) {
    switch (e.key.toLowerCase()) {
      case "b":
        e.preventDefault();
        execCommand("bold");
        break;
      case "i":
        e.preventDefault();
        execCommand("italic");
        break;
      case "u":
        e.preventDefault();
        execCommand("underline");
        break;
    }
  }
}

// 清除格式
function clearFormat() {
  if (props.readonly) return;
  execCommand("removeFormat");
}

// 聚焦
function focus() {
  editorRef.value?.focus();
}

// 监听外部值变化
watch(
  () => props.modelValue,
  (newVal) => {
    if (editorRef.value && editorRef.value.innerHTML !== newVal) {
      editorRef.value.innerHTML = newVal || "";
    }
  },
  { immediate: false }
);

// 组件挂载时初始化内容
onMounted(() => {
  if (editorRef.value) {
    editorRef.value.innerHTML = props.modelValue || "";
  }
});

defineExpose({ focus });
</script>

<template>
  <div
    class="rich-text-field"
    :class="{
      'is-readonly': readonly,
      'is-focused': isFocused,
      'is-over-limit': isOverLimit,
    }">
    <!-- 工具栏 -->
    <div v-if="!readonly" class="rich-text-toolbar">
      <ElButtonGroup size="small">
        <ElTooltip content="加粗 (Ctrl+B)" placement="top">
          <ElButton @click="execCommand('bold')">
            <span class="toolbar-icon font-bold">B</span>
          </ElButton>
        </ElTooltip>
        <ElTooltip content="斜体 (Ctrl+I)" placement="top">
          <ElButton @click="execCommand('italic')">
            <span class="toolbar-icon italic">I</span>
          </ElButton>
        </ElTooltip>
        <ElTooltip content="下划线 (Ctrl+U)" placement="top">
          <ElButton @click="execCommand('underline')">
            <span class="toolbar-icon underline">U</span>
          </ElButton>
        </ElTooltip>
      </ElButtonGroup>
      
      <ElButtonGroup size="small" class="toolbar-group">
        <ElTooltip content="无序列表" placement="top">
          <ElButton @click="execCommand('insertUnorderedList')">
            <ElIcon><List /></ElIcon>
          </ElButton>
        </ElTooltip>
        <ElTooltip content="有序列表" placement="top">
          <ElButton @click="execCommand('insertOrderedList')">
            <span class="toolbar-icon">1.</span>
          </ElButton>
        </ElTooltip>
      </ElButtonGroup>
      
      <ElButtonGroup size="small" class="toolbar-group">
        <ElTooltip content="清除格式" placement="top">
          <ElButton @click="clearFormat">
            <ElIcon><Remove /></ElIcon>
          </ElButton>
        </ElTooltip>
      </ElButtonGroup>
    </div>
    
    <!-- 编辑器区域 -->
    <div
      v-if="!readonly"
      ref="editorRef"
      class="rich-text-editor"
      contenteditable="true"
      :placeholder="placeholder"
      @input="handleInput"
      @paste="handlePaste"
      @keydown="handleKeyDown"
      @focus="isFocused = true"
      @blur="isFocused = false" />
    
    <!-- 只读模式 -->
    <div
      v-else
      class="rich-text-readonly"
      v-html="sanitizedHtml || '<span class=\'placeholder\'>-</span>'" />
    
    <!-- 字符计数 -->
    <div v-if="maxLength && !readonly" class="rich-text-counter">
      <span :class="{ 'over-limit': isOverLimit }">
        {{ plainTextLength }} / {{ maxLength }}
      </span>
    </div>
  </div>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;

.rich-text-field {
  border: 1px solid $border-color;
  border-radius: $border-radius-md;
  background-color: white;
  transition: all 0.2s;
  
  &.is-focused {
    border-color: $primary-color;
    box-shadow: 0 0 0 2px rgba($primary-color, 0.1);
  }
  
  &.is-over-limit {
    border-color: #f56c6c;
    
    &.is-focused {
      box-shadow: 0 0 0 2px rgba(#f56c6c, 0.1);
    }
  }
  
  &.is-readonly {
    border: none;
    background-color: transparent;
  }
}

.rich-text-toolbar {
  display: flex;
  gap: $spacing-sm;
  padding: $spacing-sm;
  border-bottom: 1px solid $border-color;
  background-color: #f5f7fa;
  border-radius: $border-radius-md $border-radius-md 0 0;
  flex-wrap: wrap;
  
  .toolbar-group {
    margin-left: $spacing-xs;
  }
  
  .toolbar-icon {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    min-width: 14px;
    font-size: 13px;
    font-weight: 500;
    
    &.font-bold {
      font-weight: 700;
    }
    
    &.italic {
      font-style: italic;
    }
    
    &.underline {
      text-decoration: underline;
    }
  }
}

.rich-text-editor {
  min-height: 120px;
  max-height: 300px;
  padding: $spacing-md;
  overflow-y: auto;
  outline: none;
  line-height: 1.6;
  
  &:empty::before {
    content: attr(placeholder);
    color: $text-secondary;
    pointer-events: none;
  }
  
  :deep(ul), :deep(ol) {
    margin: $spacing-sm 0;
    padding-left: $spacing-lg;
  }
  
  :deep(li) {
    margin: $spacing-xs 0;
  }
  
  :deep(b), :deep(strong) {
    font-weight: 600;
  }
  
  :deep(i), :deep(em) {
    font-style: italic;
  }
  
  :deep(u) {
    text-decoration: underline;
  }
}

.rich-text-readonly {
  min-height: 40px;
  padding: $spacing-sm 0;
  line-height: 1.6;
  
  :deep(ul), :deep(ol) {
    margin: $spacing-sm 0;
    padding-left: $spacing-lg;
  }
  
  :deep(li) {
    margin: $spacing-xs 0;
  }
  
  .placeholder {
    color: $text-secondary;
  }
}

.rich-text-counter {
  padding: $spacing-xs $spacing-sm;
  text-align: right;
  font-size: $font-size-xs;
  color: $text-secondary;
  border-top: 1px solid $border-color;
  background-color: #f5f7fa;
  border-radius: 0 0 $border-radius-md $border-radius-md;
  
  .over-limit {
    color: #f56c6c;
    font-weight: 500;
  }
}
</style>
