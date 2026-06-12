<script setup lang="ts">
import { ref, watch, computed, onMounted, onUnmounted } from "vue";
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
  // 使用 setTimeout 确保在 Vue 所有 watch/effect 执行完毕后才重置标志位
  // 防止 emit → 父组件更新 → watch(modelValue) → setContents 的循环破坏选区
  setTimeout(() => {
    isInternalChange = false;
  }, 0);
}

async function initEditor() {
  if (props.readonly) return;
  try {
    const [{ default: FluentEditor }] = await Promise.all([
      import("@opentiny/fluent-editor"),
      import("@opentiny/fluent-editor/style.css"),
    ]);

    if (!editorRef.value) {
      console.warn("[RichTextField] initEditor: editorRef is null");
      return;
    }

    const rect = editorRef.value.getBoundingClientRect();
    console.log("[RichTextField] initEditor start", {
      width: rect.width,
      height: rect.height,
      visible: rect.width > 0 && rect.height > 0,
      offsetParent: editorRef.value.offsetParent?.tagName,
      modelValue: props.modelValue?.substring(0, 50),
    });

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

    // 安全补丁：setNativeRange 忽略负偏移，避免 IndexSizeError (offset 4294967295)
    const Selection = editorInstance.value.selection.constructor;
    if (!Selection.prototype.__nativeRangePatched) {
      const originalSetNativeRange = Selection.prototype.setNativeRange;
      Selection.prototype.setNativeRange = function (
        startNode: any,
        startOffset: any,
        endNode?: any,
        endOffset?: any,
        force?: any
      ) {
        if (
          (startNode != null && startOffset < 0) ||
          (endNode != null && endOffset < 0)
        ) {
          return;
        }
        return originalSetNativeRange.call(
          this,
          startNode,
          startOffset,
          endNode,
          endOffset,
          force
        );
      };
      Selection.prototype.__nativeRangePatched = true;
    }

    // 安全补丁：getRange 增加 try-catch 兜底。
    // setContents 替换 DOM 后，MutationObserver 回调触发 Scroll.update 进而调用 getRange，
    // 此时浏览器 native selection 仍指向已被替换的旧 DOM 节点，normalizedToRange 中 blot.find
    // 返回 null 导致崩溃。此补丁捕获该异常，返回 null 而非让整个编辑器崩溃。
    // 注意：不能补丁 normalizedToRange 本身，因为任何对 normalizedToRange 的修改都会干扰
    // Quill 正常的选区解析逻辑，导致工具栏格式按钮失效（getSelection 返回错误值使 format 静默跳过）。
    if (!Selection.prototype.__getRangePatched) {
      const originalGetRange = Selection.prototype.getRange;
      Selection.prototype.getRange = function (this: any) {
        try {
          return originalGetRange.call(this);
        } catch (e) {
          return null;
        }
      };
      Selection.prototype.__getRangePatched = true;
    }

    // 给 toolbar 调用 getFormat 时增加保护：如果无选区则返回 {} 避免崩溃
    const FluentEditorCls = editorInstance.value.constructor;
    if (!FluentEditorCls.prototype.__formatPatched) {
      const originalGetFormat = FluentEditorCls.prototype.getFormat;
      FluentEditorCls.prototype.getFormat = function (index: any, length: any) {
        if (index == null || (typeof index !== "number" && index?.index == null)) {
          return {};
        }
        return originalGetFormat.call(this, index, length);
      };
      FluentEditorCls.prototype.__formatPatched = true;
    }

    // 加载已有内容（HTML → Delta）
    if (props.modelValue) {
      console.log("[RichTextField] setContents start", {
        html: props.modelValue.substring(0, 100),
      });
      // 清洗：如果 modelValue 不是字符串（如 Vue Proxy 对象），先转为字符串
      const htmlString =
        typeof props.modelValue === "string"
          ? props.modelValue
          : String(props.modelValue);
      const delta = editorInstance.value.clipboard.convert({
        html: htmlString,
      });

      editorInstance.value.setContents(delta, "silent");

      // 显式将选区设置到内容开头，使浏览器 native selection 指向新建的有效 DOM 节点。
      // 如果不做此步，浏览器 native selection 仍指向 setContents 前被替换掉的旧 DOM 节点，
      // 后续 selectionchange 事件会触发 Quill 解析失效的 native range，导致崩溃或选区返回 null。
      try {
        editorInstance.value.setSelection(0, 0, "silent");
      } catch (e) {
        console.warn("[RichTextField] setSelection after setContents failed", e);
      }

      console.log("[RichTextField] setContents done");
    }

    updatePlainTextLength();

    // 监听用户编辑
    editorInstance.value.on(
      "text-change",
      (_delta: any, _oldDelta: any, source: string) => {
        console.log("[RichTextField] text-change", { source });
        if (source !== "user") return;

        let selection = null;
        try {
          selection = editorInstance.value.getSelection();
        } catch (e) {
          console.warn("[RichTextField] getSelection failed in text-change", e);
        }
        console.log("[RichTextField] selection before handle:", selection);

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
            const cursor = selection?.index || 0;
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
    console.log("[RichTextField] initEditor success");
  } catch (e) {
    console.error("[RichTextField] 初始化失败:", e);
    loadError.value = true;
    isLoading.value = false;
  }
}

onMounted(() => {
  // 延迟 300ms 初始化，避免 el-drawer 打开动画期间 DOM 不稳定导致 Quill 选区异常
  setTimeout(() => {
    initEditor();
  }, 300);
});

onUnmounted(() => {
  if (editorInstance.value) {
    try {
      // 移除所有 text-change 监听器，避免闭包持有组件引用导致内存泄漏
      editorInstance.value.off("text-change");
    } catch (e) {
      /* ignore */
    }
    editorInstance.value = null;
  }
});

// 注：不监听外部 modelValue 变化来同步编辑器内容。
// 富文本编辑器的内容由其内部状态管理，通过 v-model 单向输出到父组件。
// 这样可以彻底避免外部 setContents 破坏用户选区导致的 Quill selection 报错。
// 初始内容在 initEditor() 中加载。
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
