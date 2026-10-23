<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useI18n } from "vue-i18n";
import { ElMessage, ElMessageBox } from "element-plus";
import {
  commentApiService,
  type CommentDTO,
  type CommentUserDTO,
} from "@/services/api/commentApiService";
import { formatDateTime } from "@/utils/timezone";

const { t } = useI18n();

const props = defineProps<{
  recordId: string;
  /** 可 @ 提及的成员列表（Base 成员 + 表分享成员） */
  members?: Array<{ id: string; name: string; avatar?: string }>;
  /** 当前用户 ID，用于判断「我的评论」 */
  currentUserId?: string;
  /** 只读 / 无评论权限时隐藏输入框 */
  readonly?: boolean;
}>();

const PER_PAGE = 20;
const MAX_LEN = 2000;

const comments = ref<CommentDTO[]>([]);
const total = ref(0);
const loading = ref(false);
const newContent = ref("");
const replyTo = ref<CommentDTO | null>(null);
const editing = ref<CommentDTO | null>(null);
const editContent = ref("");

const textareaRef = ref<any>(null);
const showMention = ref(false);
const mentionQuery = ref("");

const canComment = computed(() => !props.readonly);

const mentionResults = computed(() => {
  const q = (mentionQuery.value || "").toLowerCase();
  return (props.members || [])
    .filter((m) => m.name.toLowerCase().includes(q))
    .slice(0, 8);
});

async function load() {
  loading.value = true;
  try {
    const res = await commentApiService.list(props.recordId, {
      page: 1,
      per_page: PER_PAGE,
    });
    comments.value = res.data || [];
    total.value = res.meta?.pagination?.total ?? comments.value.length;
  } catch {
    comments.value = [];
  } finally {
    loading.value = false;
  }
}

function isMine(c: CommentDTO): boolean {
  return !!props.currentUserId && c.user?.id === props.currentUserId;
}

function resetInput() {
  newContent.value = "";
  replyTo.value = null;
  showMention.value = false;
  mentionQuery.value = "";
}

async function submit() {
  const content = newContent.value.trim();
  if (!content) {
    ElMessage.warning(t("comment.contentRequired"));
    return;
  }
  if (content.length > MAX_LEN) {
    ElMessage.warning(t("comment.tooLong"));
    return;
  }
  try {
    await commentApiService.create(props.recordId, {
      content,
      parent_id: replyTo.value?.id ?? null,
    });
    resetInput();
    await load();
  } catch {
    /* 错误已由 apiClient 统一提示 */
  }
}

function startReply(c: CommentDTO) {
  replyTo.value = c;
  textareaRef.value?.focus();
}

function cancelReply() {
  replyTo.value = null;
}

function startEdit(c: CommentDTO) {
  editing.value = c;
  editContent.value = c.content || "";
}

function cancelEdit() {
  editing.value = null;
  editContent.value = "";
}

async function saveEdit() {
  if (!editing.value) return;
  const content = editContent.value.trim();
  if (!content) {
    ElMessage.warning(t("comment.contentRequired"));
    return;
  }
  try {
    await commentApiService.update(editing.value.id, content);
    cancelEdit();
    await load();
  } catch {
    /* 错误已由 apiClient 统一提示 */
  }
}

async function remove(c: CommentDTO) {
  try {
    await ElMessageBox.confirm(t("comment.deleteConfirm"), t("common.confirm"), {
      type: "warning",
    });
  } catch {
    return;
  }
  try {
    await commentApiService.remove(c.id);
    await load();
  } catch {
    /* 错误已由 apiClient 统一提示 */
  }
}

function onInput() {
  const el = textareaRef.value;
  if (!el) return;
  const pos = el.selectionStart ?? newContent.value.length;
  const before = newContent.value.slice(0, pos);
  const match = before.match(/@([^\s@]*)$/);
  if (match) {
    mentionQuery.value = match[1];
    showMention.value = true;
  } else {
    showMention.value = false;
  }
}

function selectMention(m: CommentUserDTO) {
  const el = textareaRef.value;
  if (el) {
    const pos = el.selectionStart ?? newContent.value.length;
    const before = newContent.value.slice(0, pos);
    const after = newContent.value.slice(pos);
    const replaced = before.replace(/@([^\s@]*)$/, `@${m.name} `);
    newContent.value = replaced + after;
  } else {
    newContent.value += `@${m.name} `;
  }
  showMention.value = false;
  el?.focus();
}

function mentionNames(c: CommentDTO): string[] {
  if (!c.mentions || c.mentions.length === 0) return [];
  const map = new Map<string, string>();
  (props.members || []).forEach((m) => map.set(m.id, m.name));
  return c.mentions
    .map((mt) => map.get(mt.user_id) || mt.user_id)
    .filter(Boolean);
}

onMounted(load);
</script>

<template>
  <div class="comment-panel">
    <div class="comment-header">
      <span class="comment-title">{{ t("comment.title") }}</span>
      <span v-if="total" class="comment-count">{{ total }}</span>
    </div>

    <!-- 评论输入区 -->
    <div v-if="canComment" class="comment-editor">
      <div v-if="replyTo" class="reply-hint">
        {{ t("comment.replyingTo") }} <b>{{ replyTo.user?.name }}</b>
        <el-button link size="small" @click="cancelReply">{{
          t("comment.cancel")
        }}</el-button>
      </div>
      <el-input
        ref="textareaRef"
        v-model="newContent"
        type="textarea"
        :rows="3"
        :maxlength="MAX_LEN"
        :placeholder="t('comment.placeholder')"
        @input="onInput"
      />
      <div v-if="showMention && mentionResults.length" class="mention-popup">
        <div
          v-for="m in mentionResults"
          :key="m.id"
          class="mention-item"
          @click="selectMention(m)"
        >
          <el-avatar v-if="m.avatar" :size="20" :src="m.avatar" />
          <el-avatar v-else :size="20">{{ m.name.charAt(0) }}</el-avatar>
          <span class="mention-name">{{ m.name }}</span>
        </div>
      </div>
      <div class="editor-actions">
        <el-button type="primary" :disabled="!newContent.trim()" @click="submit">
          {{ t("comment.send") }}
        </el-button>
      </div>
    </div>

    <!-- 评论列表 -->
    <div v-loading="loading" class="comment-list">
      <div v-if="!loading && comments.length === 0" class="comment-empty">
        {{ t("comment.empty") }}
      </div>

      <div v-for="c in comments" :key="c.id" class="comment-item">
        <template v-if="c.is_deleted">
          <div class="comment-deleted">{{ t("comment.deleted") }}</div>
        </template>
        <template v-else>
          <el-avatar
            v-if="c.user?.avatar"
            :size="32"
            :src="c.user.avatar"
          />
          <el-avatar v-else :size="32">{{ c.user?.name?.charAt(0) }}</el-avatar>
          <div class="comment-body">
            <div class="comment-meta">
              <span class="comment-author">{{ c.user?.name }}</span>
              <span class="comment-time">{{ formatDateTime(c.created_at) }}</span>
            </div>
            <div v-if="editing && editing.id === c.id" class="comment-edit">
              <el-input
                v-model="editContent"
                type="textarea"
                :rows="2"
                :maxlength="MAX_LEN"
              />
              <div class="editor-actions">
                <el-button size="small" @click="cancelEdit">{{
                  t("comment.cancel")
                }}</el-button>
                <el-button size="small" type="primary" @click="saveEdit">{{
                  t("comment.save")
                }}</el-button>
              </div>
            </div>
            <div v-else class="comment-content">{{ c.content }}</div>
            <div
              v-if="mentionNames(c).length"
              class="comment-mentions"
            >
              <el-tag
                v-for="n in mentionNames(c)"
                :key="n"
                size="small"
                type="info"
                >@{{ n }}</el-tag
              >
            </div>
            <div class="comment-actions">
              <el-button
                v-if="canComment"
                link
                size="small"
                @click="startReply(c)"
                >{{ t("comment.reply") }}</el-button
              >
              <el-button
                v-if="isMine(c)"
                link
                size="small"
                @click="startEdit(c)"
                >{{ t("comment.edit") }}</el-button
              >
              <el-button
                v-if="isMine(c)"
                link
                size="small"
                type="danger"
                @click="remove(c)"
                >{{ t("comment.delete") }}</el-button
              >
            </div>

            <!-- 回复树（单层） -->
            <div
              v-if="c.replies && c.replies.length"
              class="comment-replies"
            >
              <div
                v-for="r in c.replies"
                :key="r.id"
                class="comment-item reply"
              >
                <template v-if="r.is_deleted">
                  <div class="comment-deleted">{{ t("comment.deleted") }}</div>
                </template>
                <template v-else>
                  <el-avatar
                    v-if="r.user?.avatar"
                    :size="28"
                    :src="r.user.avatar"
                  />
                  <el-avatar v-else :size="28">{{
                    r.user?.name?.charAt(0)
                  }}</el-avatar>
                  <div class="comment-body">
                    <div class="comment-meta">
                      <span class="comment-author">{{ r.user?.name }}</span>
                      <span class="comment-time">{{
                        formatDateTime(r.created_at)
                      }}</span>
                    </div>
                    <div
                      v-if="editing && editing.id === r.id"
                      class="comment-edit"
                    >
                      <el-input
                        v-model="editContent"
                        type="textarea"
                        :rows="2"
                        :maxlength="MAX_LEN"
                      />
                      <div class="editor-actions">
                        <el-button size="small" @click="cancelEdit">{{
                          t("comment.cancel")
                        }}</el-button>
                        <el-button size="small" type="primary" @click="saveEdit">{{
                          t("comment.save")
                        }}</el-button>
                      </div>
                    </div>
                    <div v-else class="comment-content">{{ r.content }}</div>
                    <div class="comment-actions">
                      <el-button
                        v-if="isMine(r)"
                        link
                        size="small"
                        @click="startEdit(r)"
                        >{{ t("comment.edit") }}</el-button
                      >
                      <el-button
                        v-if="isMine(r)"
                        link
                        size="small"
                        type="danger"
                        @click="remove(r)"
                        >{{ t("comment.delete") }}</el-button
                      >
                    </div>
                  </div>
                </template>
              </div>
            </div>
          </div>
        </template>
      </div>
    </div>
  </div>
</template>

<style scoped>
.comment-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 8px 0;
}
.comment-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}
.comment-count {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.comment-editor {
  position: relative;
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.reply-hint {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  display: flex;
  align-items: center;
  gap: 6px;
}
.mention-popup {
  position: absolute;
  z-index: 20;
  bottom: 96px;
  left: 0;
  width: 240px;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
  box-shadow: var(--el-box-shadow-light);
  max-height: 220px;
  overflow-y: auto;
}
.mention-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 10px;
  cursor: pointer;
}
.mention-item:hover {
  background: var(--el-fill-color-light);
}
.mention-name {
  font-size: 13px;
}
.editor-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}
.comment-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-height: 40px;
}
.comment-empty {
  color: var(--el-text-color-secondary);
  font-size: 13px;
  text-align: center;
  padding: 16px 0;
}
.comment-item {
  display: flex;
  gap: 10px;
}
.comment-item.reply {
  margin-top: 8px;
}
.comment-deleted {
  color: var(--el-text-color-secondary);
  font-size: 13px;
  font-style: italic;
  padding: 4px 0;
}
.comment-body {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.comment-meta {
  display: flex;
  align-items: baseline;
  gap: 8px;
}
.comment-author {
  font-weight: 500;
  font-size: 13px;
}
.comment-time {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.comment-content {
  font-size: 14px;
  white-space: pre-wrap;
  word-break: break-word;
}
.comment-mentions {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}
.comment-actions {
  display: flex;
  gap: 4px;
}
.comment-replies {
  margin-top: 8px;
  padding-left: 12px;
  border-left: 2px solid var(--el-border-color-lighter);
  display: flex;
  flex-direction: column;
  gap: 8px;
}
</style>
