<script setup lang="ts">
import { ref, watch, computed, onMounted, nextTick } from "vue";
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
const editorInstance = ref<any>(null);
const isLoading = ref(true);
const loadError = ref(false);
const currentPlainTextLength = ref(0);
// 防止 emit → watch → setContents 循环的标志位
let isInternalChange = false;

// 只读模式：净化HTML用于安全渲染
const sanitizedHtml = computed(() => {
  if (!props.modelValue) return "";
  return sanitizeHtml(props.modelValue);
});

const isOverLimit = computed(() => {
  if (!props.maxLength) return false;
  return currentPlainTextLength.value > props.maxLength;
});

function normalizeHtml(html: string): string | null {
  if (!html || html === "<p><br></p>" || html === "<br>" || html === "<div><br></div>") {
    return null;
  }
  return html;
}

function updatePlainTextLength() {
  if (!editorInstance.value) return;
  const text = editorInstance.value.getText() || "";
  currentPlainTextLength.value = Math.max(0, text.length - 1);
}

function emitValue() {
  if (!editorInstance.value) return;
  const html = editorInstance.value.root.innerHTML;
  updatePlainTextLength();
  isInternalChange = true;
  emit("update:modelValue", normalizeHtml(html));
  nextTick(() => {
    isInternalChange = false;
  });
}

async function initEditor() {
  if (props.readonly) return;
  try {
    const [{ default: FluentEditor }] = await Promise.all([
      import("@opentiny/fluent-editor"),
      import("@opentiny/fluent-editor/style.css"),
    ]);

    if (!editorRef.value) return;

    editorInstance.value = new FluentEditor(editorRef.value, {
      theme: "snow",
      placeholder: props.placeholder,
      modules: {
        toolbar: [
          ["bold", "italic", "underline", "strike"],
          [{ header: [1, 2, 3, false] }],
          [{ list: "ordered" }, { list: "bullet" }],
          [{ align: [] }],
          ["link", "image"],
          ["clean"],
        ],
      },
    });

    // 加载已有内容（HTML → Delta）
    if (props.modelValue) {
      const delta = editorInstance.value.clipboard.convert({
        html: props.modelValue,
      });
      editorInstance.value.setContents(delta);
    }

    updatePlainTextLength();

    // 监听用户编辑
    editorInstance.value.on(
      "text-change",
      (_delta: any, _oldDelta: any, source: string) => {
        if (source !== "user") return;

        // maxLength 拦截：若超出限制，撤销本次插入
        if (props.maxLength) {
          const text = editorInstance.value.getText();
          const length = Math.max(0, text.length - 1);
          if (length > props.maxLength) {
            const ops = _delta.ops || [];
            let insertCount = 0;
            for (const op of ops) {
              if (op.insert) {
                insertCount +=
                  typeof op.insert === "string" ? op.insert.length : 1;
              }
            }
            const cursor =
              editorInstance.value.getSelection()?.index || 0;
            editorInstance.value.deleteText(
              cursor - insertCount,
              insertCount,
              "silent"
            );
            return;
          }
        }

        emitValue();
      }
    );

    isLoading.value = false;
  } catch (e) {
    console.error("[RichTextField] 初始化失败:", e);
    loadError.value = true;
    isLoading.value = false;
  }
}

onMounted(() => {
  initEditor();
});

// 监听外部值变化
watch(
  () => props.modelValue,
  (newVal) => {
    if (isInternalChange) return; // 忽略由本组件 emit 触发的变化
    if (editorInstance.value && !props.readonly) {
      // 如果编辑器当前有焦点，信任编辑器内部状态，不强制更新
      // 避免 setContents 破坏用户当前选区导致 Quill selection 报错
      if (editorInstance.value.hasFocus()) return;

      const currentHtml = normalizeHtml(
        editorInstance.value.root.innerHTML
      );
      const newHtml = normalizeHtml(newVal || "");
      if (currentHtml !== newHtml) {
        const delta = editorInstance.value.clipboard.convert({
          html: newVal || "",
        });
        editorInstance.value.setContents(delta);
        updatePlainTextLength();
      }
    }
  }
);
</script>

<template>
  <div class="rich-text-field">
    <!-- 编辑模式 -->
    <template v-if="!readonly">
      <div v-if="loadError" class="editor-fallback">
        <textarea
          :value="modelValue || ''"
          @input="
            $emit(
              'update:modelValue',
              normalizeHtml(($event.target as HTMLTextAreaElement).value)
            )
          "
          :placeholder="placeholder"
          class="fallback-textarea"
        />
      </div>
      <template v-else>
        <div ref="editorRef" class="editor-container" />
        <div
          v-if="maxLength"
          class="editor-counter"
          :class="{ 'is-over-limit': isOverLimit }"
        >
          {{ currentPlainTextLength }} / {{ maxLength }}
        </div>
      </template>
    </template>

    <!-- 只读模式 -->
    <div
      v-else
      class="editor-readonly"
      v-html="sanitizedHtml || '<span class=\'placeholder\'>-</span>'"
    />
  </div>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;

.rich-text-field {
  border: 1px solid $border-color;
  border-radius: $border-radius-md;
  background-color: white;
  overflow: hidden;
  transition: all 0.2s;
}

.editor-container {
  min-height: 120px;

  :deep(.ql-toolbar) {
    border: none;
    border-bottom: 1px solid $border-color;
    background-color: #f5f7fa;
    border-radius: $border-radius-md $border-radius-md 0 0;
    padding: $spacing-sm;
  }

  :deep(.ql-container) {
    border: none;
    font-size: 14px;
  }

  :deep(.ql-editor) {
    min-height: 120px;
    max-height: 300px;
    line-height: 1.6;
  }
}

.editor-counter {
  padding: $spacing-xs $spacing-sm;
  text-align: right;
  font-size: $font-size-xs;
  color: $text-secondary;
  border-top: 1px solid $border-color;
  background-color: #f5f7fa;
  border-radius: 0 0 $border-radius-md $border-radius-md;

  &.is-over-limit {
    color: #f56c6c;
    font-weight: 500;
  }
}

.editor-readonly {
  min-height: 40px;
  padding: $spacing-sm 0;
  line-height: 1.6;

  .placeholder {
    color: $text-secondary;
  }
}

.fallback-textarea {
  width: 100%;
  min-height: 120px;
  padding: $spacing-md;
  border: none;
  outline: none;
  resize: vertical;
  font-family: inherit;
  font-size: 14px;
  line-height: 1.6;
}
</style>
