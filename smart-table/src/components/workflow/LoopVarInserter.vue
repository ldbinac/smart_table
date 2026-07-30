<script setup lang="ts">
import { ElButton, ElDropdown, ElDropdownItem, ElDropdownMenu } from "element-plus";
import { Refresh } from "@element-plus/icons-vue";

/**
 * 循环变量插入按钮
 *
 * 仅在循环体子节点的模板输入框旁渲染，用于快捷插入
 * {{loop.current_data}} / {{loop.index}} / {{loop.round}} /
 * {{loop.current_data.<field_id>}} 等循环变量片段。
 *
 * 是否支持字段下钻由父组件根据所属 loop 节点的数据源类型决定
 * （仅 find_records_all 数据源支持下钻）。
 */
interface FieldOption {
  id: string;
  name: string;
}

interface Props {
  /** 数据源是否支持下钻字段（仅 find_records_all 时为 true） */
  supportsFieldDrill?: boolean;
  /** 可下钻的字段列表 */
  fieldOptions?: FieldOption[];
  /** 是否禁用 */
  disabled?: boolean;
}

withDefaults(defineProps<Props>(), {
  supportsFieldDrill: false,
  fieldOptions: () => [],
  disabled: false,
});

const emit = defineEmits<{
  (e: "insert", snippet: string): void;
}>();

/** 命令类型：基础循环变量 或 字段下钻 */
type LoopVarCommand =
  | "current_data"
  | "index"
  | "round"
  | { type: "field"; fieldId: string };

function buildSnippet(command: LoopVarCommand): string {
  switch (command) {
    case "current_data":
      return "{{loop.current_data}}";
    case "index":
      return "{{loop.index}}";
    case "round":
      return "{{loop.round}}";
    default: {
      if (typeof command === "object" && command.type === "field") {
        return `{{loop.current_data.${command.fieldId}}}`;
      }
      return "";
    }
  }
}

function handleCommand(command: LoopVarCommand) {
  const snippet = buildSnippet(command);
  if (snippet) {
    emit("insert", snippet);
  }
}
</script>

<template>
  <el-dropdown
    trigger="click"
    :disabled="disabled"
    @command="handleCommand"
  >
    <el-button
      type="primary"
      :icon="Refresh"
      link
      size="small"
      :disabled="disabled"
      class="loop-var-inserter-btn">
      插入循环变量
    </el-button>
    <template #dropdown>
      <el-dropdown-menu>
        <el-dropdown-item command="current_data">当前循环数据</el-dropdown-item>
        <el-dropdown-item command="round">当前循环轮数（1-based）</el-dropdown-item>
        <el-dropdown-item command="index">当前循环索引（0-based）</el-dropdown-item>
        <template v-if="supportsFieldDrill">
          <el-dropdown-item divided disabled class="loop-var-group-title">
            字段下钻
          </el-dropdown-item>
          <el-dropdown-item
            v-for="field in fieldOptions"
            :key="field.id"
            :command="{ type: 'field', fieldId: field.id }">
            {{ field.name }}
          </el-dropdown-item>
          <el-dropdown-item v-if="fieldOptions.length === 0" disabled>
            暂无可下钻字段
          </el-dropdown-item>
        </template>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
</template>

<style lang="scss" scoped>
.loop-var-inserter-btn {
  padding: 0;
}

.loop-var-group-title {
  font-size: 12px;
  color: $text-secondary;
  cursor: default;
}
</style>
