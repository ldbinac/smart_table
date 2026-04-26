<script setup lang="ts">
import { ref, watch, nextTick, computed } from "vue";
import {
  ElDialog,
  ElButton,
  ElInput,
  ElSelect,
  ElOption,
  ElForm,
  ElFormItem,
  ElSwitch,
  ElColorPicker,
  ElTag,
  ElMessage,
  ElMessageBox,
  ElSlider,
  ElIcon,
} from "element-plus";
import { fieldService } from "@/db/services/fieldService";
import { useViewStore } from "@/stores/viewStore";
import { useBaseStore } from "@/stores/baseStore";
import { useTableStore } from "@/stores/tableStore";
import {
  FieldType,
  getFieldTypeLabel,
  getFieldTypeIconComponent,
  type FieldTypeValue,
} from "@/types/fields";
import type { FieldEntity } from "@/db/schema";
import type { FieldOptions } from "@/types";
import type { RelationshipType } from "@/types/link";
import Sortable from "sortablejs";
import { Rank, ArrowRight } from "@element-plus/icons-vue";
import { linkApiService } from "@/services/api/linkApiService";

const viewStore = useViewStore();
const baseStore = useBaseStore();
const tableStore = useTableStore();

const props = defineProps<{
  visible: boolean;
  tableId: string;
  fields: FieldEntity[];
  editFieldId?: string;
  baseId?: string;
}>();

const emit = defineEmits<{
  "update:visible": [value: boolean];
  "field-created": [field: FieldEntity];
  "field-updated": [field: FieldEntity];
  "field-deleted": [fieldId: string];
  "fields-reordered": [fieldIds: string[]];
  "field-visibility-changed": [fieldId: string, isVisible: boolean];
}>();

const activeTab = ref<"list" | "create" | "edit">("list");
const editingField = ref<FieldEntity | null>(null);
const fieldListRef = ref<HTMLElement | null>(null);
let sortableInstance: Sortable | null = null;

// 按 order 排序后的字段列表
const sortedFields = computed(() => {
  return [...props.fields].sort((a, b) => a.order - b.order);
});

const newField = ref<{
  name: string;
  type: FieldTypeValue;
  isRequired: boolean;
  description: string;
  defaultValue?: any;
  // 数值字段配置
  precision: number;
  // 公式字段配置
  formula: string;
  // 关联字段配置
  linkConfig: {
    targetTableId: string;
    relationshipType: RelationshipType;
    displayFieldId: string;
    bidirectional: boolean;
  };
  // 文本字段配置
  maxLength?: number;
}>({
  name: "",
  type: FieldType.SINGLE_LINE_TEXT,
  isRequired: false,
  description: "",
  defaultValue: undefined,
  precision: 0,
  formula: "",
  linkConfig: {
    targetTableId: "",
    relationshipType: "one_to_many",
    displayFieldId: "",
    bidirectional: false,
  },
  maxLength: undefined,
});

const systemTypes = [
  FieldType.CREATED_BY,
  FieldType.CREATED_TIME,
  FieldType.UPDATED_BY,
  FieldType.UPDATED_TIME,
];

// 用户可创建的字段类型（包括自动编号）
const userCreatableTypes = [
  FieldType.SINGLE_LINE_TEXT,
  FieldType.LONG_TEXT,
  FieldType.RICH_TEXT,
  FieldType.NUMBER,
  FieldType.DATE,
  FieldType.DATE_TIME,
  FieldType.SINGLE_SELECT,
  FieldType.MULTI_SELECT,
  FieldType.CHECKBOX,
  FieldType.ATTACHMENT,
  FieldType.RATING,
  FieldType.PROGRESS,
  FieldType.PHONE,
  FieldType.EMAIL,
  FieldType.URL,
  FieldType.FORMULA,
  FieldType.LINK,
  FieldType.AUTO_NUMBER,
];
// 用户可选择的字段类型列表
const fieldTypes = userCreatableTypes;

const selectOptions = ref<{ id: string; name: string; color: string }[]>([]);
const newOptionName = ref("");
const newOptionColor = ref("#3370FF");

// 附件字段配置
const attachmentConfig = ref({
  acceptTypes: [] as string[],
  maxSize: 10, // MB
  maxCount: 20,
  enableThumbnail: true,
});

// 自动编号字段配置
const autoNumberConfig = ref({
  prefix: '',
  suffix: '',
  digitLength: 0,
  includeDate: false,
  dateFormat: 'YYYYMMDD' as 'YYYYMMDD' | 'YYYYMM' | 'YYYY' | 'YYMMDD',
  startNumber: 1,
});

// 关联字段配置 - 可关联的表列表
const availableTables = computed(() => {
  // 使用 tableStore.tables 获取当前 base 的所有表
  return tableStore.tables.filter((t) => t.id !== props.tableId);
});

// 目标表的字段列表
const targetTableFields = ref<FieldEntity[]>([]);

// 加载目标表的字段
async function loadTargetTableFields(tableId: string) {
  if (!tableId) {
    targetTableFields.value = [];
    return;
  }
  try {
    // 使用 fieldService 加载目标表的字段
    const fields = await fieldService.getFieldsByTable(tableId);
    targetTableFields.value = fields || [];
  } catch (error) {
    console.error("加载目标表字段失败:", error);
    targetTableFields.value = [];
  }
}

// 监听目标表变化
watch(
  () => newField.value.linkConfig.targetTableId,
  (newTableId) => {
    if (newTableId) {
      loadTargetTableFields(newTableId);
    } else {
      targetTableFields.value = [];
    }
  },
);

// 监听对话框显示，初始化拖拽排序或直接打开编辑界面
watch(
  () => props.visible,
  (visible) => {
    if (visible) {
      // 如果指定了 editFieldId，直接打开该字段的编辑界面
      if (props.editFieldId) {
        const field = props.fields.find((f) => f.id === props.editFieldId);
        if (field) {
          openEditField(field);
          return;
        }
      }
      activeTab.value = "list";
      nextTick(() => {
        initSortable();
      });
    } else {
      destroySortable();
      // 关闭对话框时清除编辑状态
      editingField.value = null;
    }
  },
);

// 监听字段列表变化，重新初始化拖拽
watch(
  () => props.fields,
  () => {
    if (activeTab.value === "list" && props.visible) {
      nextTick(() => {
        initSortable();
      });
    }
  },
  { deep: true },
);

function initSortable() {
  if (sortableInstance) {
    sortableInstance.destroy();
  }

  if (fieldListRef.value) {
    sortableInstance = new Sortable(fieldListRef.value, {
      handle: ".drag-handle",
      animation: 150,
      ghostClass: "sortable-ghost",
      chosenClass: "sortable-chosen",
      dragClass: "sortable-drag",
      onStart: () => {
        // 拖拽开始时的视觉反馈
        document.body.style.cursor = "grabbing";
      },
      onEnd: (evt) => {
        // 拖拽结束恢复光标
        document.body.style.cursor = "";
        handleFieldDragEnd(evt);
      },
    });
  }
}

function destroySortable() {
  if (sortableInstance) {
    sortableInstance.destroy();
    sortableInstance = null;
  }
}

async function handleFieldDragEnd(evt: Sortable.SortableEvent) {
  if (evt.oldIndex === evt.newIndex) return;

  // 使用排序后的字段列表
  const currentSortedFields = [...sortedFields.value];
  const [movedField] = currentSortedFields.splice(evt.oldIndex!, 1);
  currentSortedFields.splice(evt.newIndex!, 0, movedField);

  const fieldIds = currentSortedFields.map((f) => f.id);

  try {
    await fieldService.reorderFields(props.tableId, fieldIds);
    emit("fields-reordered", fieldIds);
    ElMessage.success("字段排序已更新");
  } catch (error) {
    ElMessage.error("字段排序失败");
  }
}

function openCreateField() {
  activeTab.value = "create";
  newField.value = {
    name: "",
    type: FieldType.SINGLE_LINE_TEXT,
    isRequired: false,
    description: "",
    precision: 0,
    formula: "",
    linkConfig: {
      targetTableId: "",
      relationshipType: "one_to_many",
      displayFieldId: "",
      bidirectional: false,
    },
    maxLength: undefined,
  };
  selectOptions.value = [];
  targetTableFields.value = [];
  // 重置附件配置
  attachmentConfig.value = {
    acceptTypes: [],
    maxSize: 10,
    maxCount: 20,
    enableThumbnail: true,
  };
}

function openEditField(field: FieldEntity) {
  editingField.value = field;
  activeTab.value = "edit";

  // 处理日期字段的默认值：直接使用实际值
  // dateDefaultType 计算属性会自动根据 defaultValue 的值判断类型
  let dateDefaultValue: any = undefined;

  if (field.type === FieldType.DATE || field.type === FieldType.DATE_TIME) {
    if (field.defaultValue === "now") {
      dateDefaultValue = "now";
    } else if (field.defaultValue && field.defaultValue !== "now") {
      // 指定日期的情况，直接使用实际日期值
      dateDefaultValue = field.defaultValue;
    } else {
      // 不使用默认值
      dateDefaultValue = undefined;
    }
  } else {
    // 非日期字段，直接使用默认值
    dateDefaultValue = field.defaultValue;
  }

  newField.value = {
    name: field.name,
    type: field.type as FieldTypeValue,
    isRequired: field.isRequired ?? false,
    description: field.description || "",
    defaultValue: dateDefaultValue,
    precision: (field.options?.precision as number) ?? 0,
    formula: (field.options?.formula as string) ?? "",
    // 关联字段的配置保存在 config 中
    linkConfig: {
      targetTableId: (field.config?.linkedTableId as string) ?? "",
      relationshipType:
        (field.config?.relationshipType as RelationshipType) ?? "one_to_many",
      displayFieldId: (field.config?.displayFieldId as string) ?? "",
      bidirectional: (field.config?.bidirectional as boolean) ?? false,
    },
    maxLength: (field.options?.maxLength as number) ?? undefined,
  };

  // 如果是关联字段，加载目标表字段
  if (
    field.type === FieldType.LINK &&
    newField.value.linkConfig.targetTableId
  ) {
    loadTargetTableFields(newField.value.linkConfig.targetTableId);
  }
  if (
    field.type === FieldType.SINGLE_SELECT ||
    field.type === FieldType.MULTI_SELECT
  ) {
    selectOptions.value =
      (field.options?.choices as {
        id: string;
        name: string;
        color: string;
      }[]) || [];
  } else {
    selectOptions.value = [];
  }

  // 加载附件字段配置
  if (field.type === FieldType.ATTACHMENT) {
    attachmentConfig.value = {
      acceptTypes: (field.options?.acceptTypes as string[]) || [],
      maxSize: Math.floor(
        ((field.options?.maxSize as number) || 10 * 1024 * 1024) / 1024 / 1024,
      ),
      maxCount: (field.options?.maxCount as number) || 20,
      enableThumbnail: field.options?.enableThumbnail !== false,
    };
  } else {
    attachmentConfig.value = {
      acceptTypes: [],
      maxSize: 10,
      maxCount: 20,
      enableThumbnail: true,
    };
  }

  // 加载自动编号字段配置
  if (field.type === FieldType.AUTO_NUMBER) {
    autoNumberConfig.value = {
      prefix: (field.options?.prefix as string) || '',
      suffix: (field.options?.suffix as string) || '',
      digitLength: (field.options?.digitLength as number) || 0,
      includeDate: (field.options?.includeDate as boolean) || false,
      dateFormat: (field.options?.dateFormat as 'YYYYMMDD' | 'YYYYMM' | 'YYYY' | 'YYMMDD') || 'YYYYMMDD',
      startNumber: (field.options?.startNumber as number) || 1,
    };
  } else {
    autoNumberConfig.value = {
      prefix: '',
      suffix: '',
      digitLength: 0,
      includeDate: false,
      dateFormat: 'YYYYMMDD',
      startNumber: 1,
    };
  }
}

function backToList() {
  activeTab.value = "list";
  editingField.value = null;
  newField.value = {
    name: "",
    type: FieldType.SINGLE_LINE_TEXT,
    isRequired: false,
    description: "",
    defaultValue: undefined,
    precision: 0,
    formula: "",
    linkConfig: {
      targetTableId: "",
      relationshipType: "one_to_many",
      displayFieldId: "",
      bidirectional: false,
    },
    maxLength: undefined,
  };
  selectOptions.value = [];
  targetTableFields.value = [];
  // 重置附件配置
  attachmentConfig.value = {
    acceptTypes: [],
    maxSize: 10,
    maxCount: 20,
    enableThumbnail: true,
  };
}

// 计算日期默认值的类型（用于 radio-group 绑定）
const dateDefaultType = computed({
  get: () => {
    if (newField.value.type !== FieldType.DATE && newField.value.type !== FieldType.DATE_TIME) return "";
    if (newField.value.defaultValue === "now") return "now";
    if (newField.value.defaultValue && newField.value.defaultValue !== "now")
      return "custom";
    return "";
  },
  set: (value: string) => {
    handleDateDefaultTypeChange(value);
  },
});

// 处理日期默认值类型变更
function handleDateDefaultTypeChange(value: string) {
  // 如果切换到"不使用默认值"，清空 defaultValue
  if (value === "") {
    newField.value.defaultValue = undefined;
  }
  // 如果切换到"使用添加记录的日期"，设置为 'now'
  if (value === "now") {
    newField.value.defaultValue = "now";
  }
  // 如果切换到"指定日期"，保持当前值或设置为当前日期
  if (
    value === "custom" &&
    (newField.value.defaultValue === "now" || !newField.value.defaultValue)
  ) {
    newField.value.defaultValue = new Date().toISOString().split("T")[0];
  }
}

async function createField() {
  if (!newField.value.name.trim()) {
    ElMessage.warning("请输入字段名称");
    return;
  }

  // 关联字段特殊验证
  if (newField.value.type === FieldType.LINK) {
    if (!newField.value.linkConfig.targetTableId) {
      ElMessage.warning("请选择目标数据表");
      return;
    }
  }

  try {
    const options: FieldOptions = {};
    if (
      newField.value.type === FieldType.SINGLE_SELECT ||
      newField.value.type === FieldType.MULTI_SELECT
    ) {
      // 后端期望的格式是 {choices: [...]}
      options.choices = selectOptions.value.map((opt) => ({
        id: opt.id,
        name: opt.name,
        color: opt.color,
      }));
    }
    // 数值字段精度配置
    if (newField.value.type === FieldType.NUMBER) {
      options.precision = newField.value.precision;
    }
    // 公式字段配置
    if (newField.value.type === FieldType.FORMULA) {
      options.formula = newField.value.formula;
      options.precision = newField.value.precision || 2;
    }
    // 附件字段配置
    if (newField.value.type === FieldType.ATTACHMENT) {
      // 使用 toRaw 转换为普通数组，避免 IndexedDB 克隆错误
      options.acceptTypes = JSON.parse(
        JSON.stringify(attachmentConfig.value.acceptTypes),
      );
      options.maxSize = attachmentConfig.value.maxSize * 1024 * 1024; // 转换为字节
      options.maxCount = attachmentConfig.value.maxCount;
      options.enableThumbnail = attachmentConfig.value.enableThumbnail;
    }
    // 关联字段配置
    if (newField.value.type === FieldType.LINK) {
      options.linkedTableId = newField.value.linkConfig.targetTableId;
      options.relationshipType = newField.value.linkConfig.relationshipType;
      options.displayFieldId = newField.value.linkConfig.displayFieldId;
      options.bidirectional = newField.value.linkConfig.bidirectional;
    }
    // 文本字段配置
    if (newField.value.type === FieldType.SINGLE_LINE_TEXT ||
        newField.value.type === FieldType.LONG_TEXT ||
        newField.value.type === FieldType.RICH_TEXT) {
      if (newField.value.maxLength) {
        options.maxLength = newField.value.maxLength;
      }
    }
    // 自动编号字段配置
    if (newField.value.type === FieldType.AUTO_NUMBER) {
      options.startNumber = autoNumberConfig.value.startNumber;
      options.prefix = autoNumberConfig.value.prefix;
      options.suffix = autoNumberConfig.value.suffix;
      options.digitLength = autoNumberConfig.value.digitLength;
      options.includeDate = autoNumberConfig.value.includeDate;
      options.dateFormat = autoNumberConfig.value.dateFormat;
    }

    let field;

    // 如果是关联字段，使用专门的关联字段创建接口
    if (newField.value.type === FieldType.LINK) {
      try {
        const result = await linkApiService.createLinkField({
          table_id: props.tableId,
          name: newField.value.name.trim(),
          target_table_id: newField.value.linkConfig.targetTableId,
          relationship_type: newField.value.linkConfig.relationshipType,
          display_field_id:
            newField.value.linkConfig.displayFieldId || undefined,
          bidirectional: newField.value.linkConfig.bidirectional,
          description: newField.value.description,
        });
        field = result.field as FieldEntity;
      } catch (linkError) {
        console.error("创建关联字段失败:", linkError);
        throw linkError;
      }
    } else {
      // 非关联字段，使用普通字段创建
      field = await fieldService.createField({
        tableId: props.tableId,
        name: newField.value.name.trim(),
        type: newField.value.type,
        isRequired: newField.value.isRequired,
        description: newField.value.description,
        defaultValue: newField.value.defaultValue,
        options: Object.keys(options).length > 0 ? options : undefined,
      });
    }

    emit("field-created", field);
    ElMessage.success("字段创建成功");
    backToList();
  } catch (error) {
    ElMessage.error(
      "字段创建失败: " + (error instanceof Error ? error.message : "未知错误"),
    );
  }
}

async function updateField() {
  if (!editingField.value) return;
  if (!newField.value.name.trim()) {
    ElMessage.warning("请输入字段名称");
    return;
  }

  // 关联字段特殊验证
  if (newField.value.type === FieldType.LINK) {
    if (!newField.value.linkConfig.targetTableId) {
      ElMessage.warning("请选择目标数据表");
      return;
    }
  }

  try {
    const options: FieldOptions = { ...(editingField.value.options || {}) };
    if (
      newField.value.type === FieldType.SINGLE_SELECT ||
      newField.value.type === FieldType.MULTI_SELECT
    ) {
      // 后端期望的格式是 {choices: [...]}
      options.choices = selectOptions.value.map((opt) => ({
        id: opt.id,
        name: opt.name,
        color: opt.color,
      }));
    }
    // 数值字段精度配置
    if (newField.value.type === FieldType.NUMBER) {
      options.precision = newField.value.precision;
    }
    // 公式字段配置
    if (newField.value.type === FieldType.FORMULA) {
      options.formula = newField.value.formula;
      options.precision = newField.value.precision || 2;
    }
    // 附件字段配置
    if (newField.value.type === FieldType.ATTACHMENT) {
      // 使用 JSON 序列化转换为普通数组，避免 IndexedDB 克隆错误
      options.acceptTypes = JSON.parse(
        JSON.stringify(attachmentConfig.value.acceptTypes),
      );
      options.maxSize = attachmentConfig.value.maxSize * 1024 * 1024; // 转换为字节
      options.maxCount = attachmentConfig.value.maxCount;
      options.enableThumbnail = attachmentConfig.value.enableThumbnail;
    }
    // 关联字段配置
    if (newField.value.type === FieldType.LINK) {
      options.linkedTableId = newField.value.linkConfig.targetTableId;
      options.relationshipType = newField.value.linkConfig.relationshipType;
      options.displayFieldId = newField.value.linkConfig.displayFieldId;
      options.bidirectional = newField.value.linkConfig.bidirectional;
    }
    // 文本字段配置
    if (newField.value.type === FieldType.SINGLE_LINE_TEXT ||
        newField.value.type === FieldType.LONG_TEXT ||
        newField.value.type === FieldType.RICH_TEXT) {
      if (newField.value.maxLength) {
        options.maxLength = newField.value.maxLength;
      }
    }
    // 自动编号字段配置
    if (newField.value.type === FieldType.AUTO_NUMBER) {
      options.startNumber = autoNumberConfig.value.startNumber;
      options.prefix = autoNumberConfig.value.prefix;
      options.suffix = autoNumberConfig.value.suffix;
      options.digitLength = autoNumberConfig.value.digitLength;
      options.includeDate = autoNumberConfig.value.includeDate;
      options.dateFormat = autoNumberConfig.value.dateFormat;
    }

    await fieldService.updateField(editingField.value.id, {
      name: newField.value.name.trim(),
      isRequired: newField.value.isRequired,
      description: newField.value.description,
      defaultValue: newField.value.defaultValue,
      options: options as Record<string, unknown>,
    });

    // 如果是关联字段，更新关联关系
    if (newField.value.type === FieldType.LINK) {
      try {
        await linkApiService.updateLinkField(editingField.value.id, {
          relationship_type: newField.value.linkConfig.relationshipType,
          display_field_id:
            newField.value.linkConfig.displayFieldId || undefined,
          bidirectional: newField.value.linkConfig.bidirectional,
          name: newField.value.name.trim(),
          description: newField.value.description,
        });
      } catch (linkError) {
        console.error("更新关联关系失败:", linkError);
        // 关联关系更新失败不影响字段更新
      }
    }

    const updatedField = {
      ...editingField.value,
      ...newField.value,
      options: options as Record<string, unknown>,
    };
    emit("field-updated", updatedField);
    ElMessage.success("字段更新成功");
    backToList();
  } catch (error) {
    ElMessage.error(
      "字段更新失败: " + (error instanceof Error ? error.message : "未知错误"),
    );
  }
}

async function deleteField(field: FieldEntity) {
  if (field.isSystem) {
    ElMessage.warning("系统字段不能删除");
    return;
  }

  try {
    // 二次确认对话框
    await ElMessageBox.confirm(
      `确定要删除字段 "${field.name}" 吗？删除后该字段的数据将无法恢复。`,
      "删除确认",
      {
        confirmButtonText: "确定删除",
        cancelButtonText: "取消",
        type: "warning",
        confirmButtonClass: "el-button--danger",
      },
    );

    await fieldService.deleteField(field.id);
    emit("field-deleted", field.id);
    ElMessage.success("字段删除成功");
  } catch (error) {
    // 用户取消删除时，ElMessageBox.confirm 会抛出错误，不需要显示错误提示
    if (error === "cancel" || error === "close") {
      return;
    }
    ElMessage.error(
      "字段删除失败: " + (error instanceof Error ? error.message : "未知错误"),
    );
  }
}

function addOption() {
  if (!newOptionName.value.trim()) return;

  selectOptions.value.push({
    id: Date.now().toString(),
    name: newOptionName.value.trim(),
    color: newOptionColor.value,
  });
  newOptionName.value = "";
}

function removeOption(index: number) {
  selectOptions.value.splice(index, 1);
}

function onTypeChange() {
  if (
    newField.value.type !== FieldType.SINGLE_SELECT &&
    newField.value.type !== FieldType.MULTI_SELECT
  ) {
    selectOptions.value = [];
  }
  // 切换类型时重置特定配置
  if (
    newField.value.type !== FieldType.NUMBER &&
    newField.value.type !== FieldType.FORMULA
  ) {
    newField.value.precision = 0;
  }
  if (newField.value.type !== FieldType.FORMULA) {
    newField.value.formula = "";
  }
  // 切换类型时重置关联字段配置
  if (newField.value.type !== FieldType.LINK) {
    newField.value.linkConfig = {
      targetTableId: "",
      relationshipType: "one_to_many",
      displayFieldId: "",
      bidirectional: false,
    };
    targetTableFields.value = [];
  }
}

const presetColors = [
  "#3370FF",
  "#34D399",
  "#FBBF24",
  "#EF4444",
  "#8B5CF6",
  "#EC4899",
  "#14B8A6",
  "#F59E0B",
  "#6366F1",
  "#10B981",
];

// 可用于公式的字段（排除公式字段自身和某些系统字段）
const availableFieldsForFormula = computed(() => {
  return props.fields.filter((field) => {
    // 排除当前编辑的字段（避免循环引用）
    if (editingField.value && field.id === editingField.value.id) {
      return false;
    }
    // 排除某些系统字段
    if (
      field.type === FieldType.CREATED_BY ||
      field.type === FieldType.UPDATED_BY
    ) {
      return false;
    }
    return true;
  });
});

// 自动编号预览
const autoNumberPreview = computed(() => {
  const { prefix, suffix, digitLength, includeDate, dateFormat, startNumber } = autoNumberConfig.value;
  
  let numberPart = String(startNumber);
  if (digitLength > 0 && numberPart.length < digitLength) {
    numberPart = numberPart.padStart(digitLength, '0');
  }
  
  let datePart = '';
  if (includeDate) {
    const now = new Date();
    const year = now.getFullYear();
    const month = String(now.getMonth() + 1).padStart(2, '0');
    const day = String(now.getDate()).padStart(2, '0');
    const yy = String(year).slice(-2);
    
    switch (dateFormat) {
      case 'YYYYMMDD':
        datePart = `${year}${month}${day}`;
        break;
      case 'YYYYMM':
        datePart = `${year}${month}`;
        break;
      case 'YYYY':
        datePart = `${year}`;
        break;
      case 'YYMMDD':
        datePart = `${yy}${month}${day}`;
        break;
      default:
        datePart = `${year}${month}${day}`;
    }
    
    if (datePart) {
      datePart = `${datePart}-`;
    }
  }
  
  return `${prefix}${datePart}${numberPart}${suffix}`;
});

// 插入函数到公式
function insertFunction(funcName: string) {
  const formulaInput = document.querySelector(
    '.formula-field textarea, [placeholder*="公式"]',
  ) as HTMLTextAreaElement;
  if (formulaInput) {
    const start = formulaInput.selectionStart;
    const end = formulaInput.selectionEnd;
    const currentValue = newField.value.formula;
    const newValue =
      currentValue.substring(0, start) +
      funcName +
      "()" +
      currentValue.substring(end);
    newField.value.formula = newValue;
    // 将光标放在括号内
    nextTick(() => {
      formulaInput.focus();
      formulaInput.setSelectionRange(
        start + funcName.length + 1,
        start + funcName.length + 1,
      );
    });
  } else {
    newField.value.formula += funcName + "()";
  }
}

// 插入字段引用到公式
function insertFieldRef(fieldName: string) {
  const formulaInput = document.querySelector(
    '.formula-field textarea, [placeholder*="公式"]',
  ) as HTMLTextAreaElement;
  const fieldRef = `{${fieldName}}`;
  if (formulaInput) {
    const start = formulaInput.selectionStart;
    const end = formulaInput.selectionEnd;
    const currentValue = newField.value.formula;
    const newValue =
      currentValue.substring(0, start) + fieldRef + currentValue.substring(end);
    newField.value.formula = newValue;
    nextTick(() => {
      formulaInput.focus();
      formulaInput.setSelectionRange(
        start + fieldRef.length,
        start + fieldRef.length,
      );
    });
  } else {
    newField.value.formula += fieldRef;
  }
}

// 检查字段是否在视图级隐藏列表中
function isFieldHiddenInView(fieldId: string): boolean {
  // 使用 viewStore 获取最新的 hiddenFields，确保状态同步
  const hiddenFields = viewStore.currentView?.hiddenFields || [];
  const result = hiddenFields.includes(fieldId);
  console.log(
    `[FieldDialog] isFieldHiddenInView(${fieldId}):`,
    result,
    "hiddenFields:",
    hiddenFields,
  );
  return result;
}

// 获取字段当前实际显示状态（同时考虑全局隐藏和视图级隐藏）
function getFieldActualVisibility(field: FieldEntity): boolean {
  const isGloballyVisible = field.isVisible !== false;
  const isHiddenInView = isFieldHiddenInView(field.id);
  const result = isGloballyVisible && !isHiddenInView;
  console.log(
    `[FieldDialog] getFieldActualVisibility(${field.name}):`,
    result,
    "isGloballyVisible:",
    isGloballyVisible,
    "isHiddenInView:",
    isHiddenInView,
  );
  return result;
}

// 切换字段可见性（同时处理全局隐藏和视图级隐藏）
async function toggleFieldVisibility(
  field: FieldEntity,
  newVisibility: boolean,
) {
  console.log(
    `[FieldDialog] toggleFieldVisibility called for ${field.name}, newVisibility:`,
    newVisibility,
  );
  console.log(`[FieldDialog] current field state:`, {
    isVisible: field.isVisible,
    hiddenFields: viewStore.currentView?.hiddenFields,
  });

  try {
    // 获取当前实际显示状态
    const currentVisibility = getFieldActualVisibility(field);
    const isHiddenInView = isFieldHiddenInView(field.id);
    const isGloballyVisible = field.isVisible !== false;

    console.log(
      `[FieldDialog] currentVisibility:`,
      currentVisibility,
      "isHiddenInView:",
      isHiddenInView,
      "isGloballyVisible:",
      isGloballyVisible,
    );

    // 如果当前是隐藏状态，且用户想要显示
    if (!currentVisibility && newVisibility) {
      if (isHiddenInView) {
        // 如果是视图级隐藏，通知父组件从隐藏列表中移除
        console.log(
          `[FieldDialog] Emitting field-visibility-changed: ${field.id}, true`,
        );
        emit("field-visibility-changed", field.id, true);
        ElMessage.success(`字段 "${field.name}" 已显示`);
        return;
      } else if (!isGloballyVisible) {
        // 如果是全局隐藏，更新全局可见性
        console.log(
          `[FieldDialog] Updating global visibility: ${field.id}, true`,
        );
        await fieldService.updateFieldVisibility(field.id, true);
        emit("field-updated", { ...field, isVisible: true });
        ElMessage.success(`字段 "${field.name}" 已显示`);
        return;
      }
    }

    // 如果当前是显示状态，且用户想要隐藏
    if (currentVisibility && !newVisibility) {
      // 优先使用视图级隐藏
      console.log(
        `[FieldDialog] Emitting field-visibility-changed: ${field.id}, false`,
      );
      emit("field-visibility-changed", field.id, false);
      ElMessage.success(`字段 "${field.name}" 已隐藏`);
      return;
    }

    // 如果状态没有变化，给出提示
    console.log(`[FieldDialog] No state change needed`);
    ElMessage.info(`字段 "${field.name}" 状态未改变`);
  } catch (error) {
    console.error(`[FieldDialog] Error in toggleFieldVisibility:`, error);
    ElMessage.error("更新字段可见性失败");
    emit("field-updated", { ...field });
  }
}
</script>

<template>
  <ElDialog
    :model-value="visible"
    @update:model-value="$emit('update:visible', $event)"
    title="字段管理"
    width="600px"
    :close-on-click-modal="false">
    <!-- 字段列表 -->
    <div v-if="activeTab === 'list'" class="field-list">
      <div class="field-list-header">
        <span class="field-count">共 {{ fields.length }} 个字段</span>
        <ElButton type="primary" size="small" @click="openCreateField">
          + 添加字段
        </ElButton>
      </div>

      <div ref="fieldListRef" class="field-items">
        <div
          v-for="field in sortedFields"
          :key="field.id"
          class="field-item"
          :class="{ 'is-system': field.isSystem }"
          :data-field-id="field.id">
          <div class="field-info">
            <span class="drag-handle" title="拖拽排序">
              <ElIcon><Rank /></ElIcon>
            </span>
            <span class="field-icon">
              <el-icon>
                <component :is="getFieldTypeIconComponent(field.type)" />
              </el-icon>
            </span>
            <span class="field-name">{{ field.name }}</span>
            <span class="field-type">{{ getFieldTypeLabel(field.type) }}</span>
            <ElTag v-if="field.isSystem" size="small" type="info">系统</ElTag>
            <ElTag v-if="field.isRequired" size="small" type="warning"
              >必填</ElTag
            >
          </div>
          <div class="field-actions">
            <ElSwitch
              :model-value="getFieldActualVisibility(field)"
              :active-value="true"
              :inactive-value="false"
              size="small"
              inline-prompt
              active-text="显示"
              inactive-text="隐藏"
              @change="(val) => toggleFieldVisibility(field, val as boolean)"
              style="margin-right: 8px" />
            <ElButton
              v-if="!field.isSystem"
              link
              type="primary"
              size="small"
              @click="openEditField(field)">
              编辑
            </ElButton>
            <ElButton
              v-if="!field.isSystem"
              link
              type="danger"
              size="small"
              @click="deleteField(field)">
              删除
            </ElButton>
          </div>
        </div>
      </div>
    </div>

    <!-- 创建/编辑字段 -->
    <div v-else class="field-form">
      <ElForm label-width="100px">
        <ElFormItem label="字段名称" required>
          <ElInput
            v-model="newField.name"
            placeholder="请输入字段名称"
            maxlength="50"
            show-word-limit />
        </ElFormItem>

        <ElFormItem label="字段类型" required>
          <ElSelect
            v-model="newField.type"
            style="width: 100%"
            @change="onTypeChange">
            <ElOption
              v-for="type in fieldTypes"
              :key="type"
              :label="getFieldTypeLabel(type)"
              :value="type">
              <span class="type-option">
                <span class="type-icon">
                  <el-icon>
                    <component :is="getFieldTypeIconComponent(type)" />
                  </el-icon>
                </span>
                <span>{{ getFieldTypeLabel(type) }}</span>
              </span>
            </ElOption>
          </ElSelect>
        </ElFormItem>

        <!-- 文本字段最大长度配置 -->
        <ElFormItem
          v-if="newField.type === FieldType.SINGLE_LINE_TEXT || newField.type === FieldType.LONG_TEXT || newField.type === FieldType.RICH_TEXT"
          label="最大长度">
          <ElInputNumber
            v-model="newField.maxLength"
            :min="1"
            :max="10000"
            :step="1"
            placeholder="不限制"
            style="width: 200px" />
          <div class="field-hint">设置文本的最大长度，不填则不限制</div>
        </ElFormItem>

        <!-- 数值字段精度配置 -->
        <ElFormItem v-if="newField.type === FieldType.NUMBER" label="小数位数">
          <div class="precision-config">
            <ElSlider
              v-model="newField.precision"
              :min="0"
              :max="10"
              :step="1"
              show-stops
              style="width: 300px" />
            <span class="precision-value">{{ newField.precision }} 位</span>
          </div>
          <div class="field-hint">设置数值显示的小数位数，默认为 0</div>
        </ElFormItem>

        <!-- 公式字段配置 -->
        <template v-if="newField.type === FieldType.FORMULA">
          <ElFormItem label="公式表达式" required>
            <ElInput
              v-model="newField.formula"
              type="textarea"
              :rows="3"
              placeholder="输入公式，如: SUM({单价}, {数量}) 或 {单价} * {数量}"
              maxlength="500"
              show-word-limit />
            <div class="field-hint">
              使用 {字段名} 引用其他字段，支持数学、文本、日期、逻辑函数
            </div>
          </ElFormItem>

          <ElFormItem label="小数位数">
            <div class="precision-config">
              <ElSlider
                v-model="newField.precision"
                :min="0"
                :max="10"
                :step="1"
                show-stops
                style="width: 300px" />
              <span class="precision-value"
                >{{ newField.precision || 2 }} 位</span
              >
            </div>
            <div class="field-hint">设置公式结果显示的小数位数，默认为 2</div>
          </ElFormItem>

          <ElFormItem label="可用函数">
            <div class="formula-functions">
              <div class="function-category">
                <div class="category-title">数学函数</div>
                <div class="function-list">
                  <ElTag
                    v-for="func in ['SUM', 'AVG', 'MAX', 'MIN', 'ROUND']"
                    :key="func"
                    size="small"
                    class="function-tag"
                    @click="insertFunction(func)">
                    {{ func }}
                  </ElTag>
                </div>
              </div>
              <div class="function-category">
                <div class="category-title">文本函数</div>
                <div class="function-list">
                  <ElTag
                    v-for="func in ['CONCAT', 'LEFT', 'LEN', 'UPPER']"
                    :key="func"
                    size="small"
                    class="function-tag"
                    @click="insertFunction(func)">
                    {{ func }}
                  </ElTag>
                </div>
              </div>
              <div class="function-category">
                <div class="category-title">日期函数</div>
                <div class="function-list">
                  <ElTag
                    v-for="func in ['TODAY', 'NOW', 'DATEDIF']"
                    :key="func"
                    size="small"
                    class="function-tag"
                    @click="insertFunction(func)">
                    {{ func }}
                  </ElTag>
                </div>
              </div>
              <div class="function-category">
                <div class="category-title">逻辑函数</div>
                <div class="function-list">
                  <ElTag
                    v-for="func in ['IF', 'AND', 'OR']"
                    :key="func"
                    size="small"
                    class="function-tag"
                    @click="insertFunction(func)">
                    {{ func }}
                  </ElTag>
                </div>
              </div>
            </div>
          </ElFormItem>

          <ElFormItem label="可用字段">
            <div class="formula-fields">
              <ElTag
                v-for="field in availableFieldsForFormula"
                :key="field.id"
                size="small"
                type="info"
                class="field-tag"
                @click="insertFieldRef(field.name)">
                {{ field.name }}
              </ElTag>
            </div>
          </ElFormItem>
        </template>

        <!-- 自动编号字段配置 -->
        <template v-if="newField.type === FieldType.AUTO_NUMBER">
          <ElFormItem label="编号预览">
            <div class="auto-number-preview">
              <span class="preview-label">预览:</span>
              <span class="preview-value">{{ autoNumberPreview }}</span>
            </div>
          </ElFormItem>

          <ElFormItem label="起始编号">
            <ElInputNumber
              v-model="autoNumberConfig.startNumber"
              :min="1"
              :max="999999"
              :step="1"
              style="width: 200px" />
            <div class="field-hint">设置编号的起始值，默认为 1</div>
          </ElFormItem>

          <ElFormItem label="编号前缀">
            <ElInput
              v-model="autoNumberConfig.prefix"
              placeholder="如: NO-"
              maxlength="20"
              show-word-limit
              style="width: 200px" />
            <div class="field-hint">在编号前添加固定前缀</div>
          </ElFormItem>

          <ElFormItem label="编号后缀">
            <ElInput
              v-model="autoNumberConfig.suffix"
              placeholder="如: -A"
              maxlength="20"
              show-word-limit
              style="width: 200px" />
            <div class="field-hint">在编号后添加固定后缀</div>
          </ElFormItem>

          <ElFormItem label="编号位数">
            <ElInputNumber
              v-model="autoNumberConfig.digitLength"
              :min="0"
              :max="10"
              :step="1"
              style="width: 200px" />
            <div class="field-hint">设置编号位数，不足时前面补0（0表示不补零）</div>
          </ElFormItem>

          <ElFormItem label="包含日期">
            <ElSwitch
              v-model="autoNumberConfig.includeDate"
              active-text="是"
              inactive-text="否" />
            <div class="field-hint">开启后在编号中包含日期前缀</div>
          </ElFormItem>

          <ElFormItem v-if="autoNumberConfig.includeDate" label="日期格式">
            <ElSelect v-model="autoNumberConfig.dateFormat" style="width: 200px">
              <ElOption label="YYYYMMDD (20240115)" value="YYYYMMDD" />
              <ElOption label="YYYYMM (202401)" value="YYYYMM" />
              <ElOption label="YYYY (2024)" value="YYYY" />
              <ElOption label="YYMMDD (240115)" value="YYMMDD" />
            </ElSelect>
            <div class="field-hint">选择日期前缀的显示格式</div>
          </ElFormItem>
        </template>

        <ElFormItem
          v-if="
            newField.type === FieldType.SINGLE_SELECT ||
            newField.type === FieldType.MULTI_SELECT
          "
          label="选项">
          <div class="options-editor">
            <div class="options-list">
              <div
                v-for="(option, index) in selectOptions"
                :key="option.id"
                class="option-item">
                <ElColorPicker
                  v-model="option.color"
                  size="small"
                  :predefine="presetColors" />
                <ElInput
                  v-model="option.name"
                  size="small"
                  placeholder="选项名称" />
                <ElButton
                  link
                  type="danger"
                  size="small"
                  @click="removeOption(index)">
                  删除
                </ElButton>
              </div>
            </div>
            <div class="add-option">
              <ElColorPicker
                v-model="newOptionColor"
                size="small"
                :predefine="presetColors" />
              <ElInput
                v-model="newOptionName"
                size="small"
                placeholder="输入选项名称，按回车添加"
                @keyup.enter="addOption" />
              <ElButton type="primary" size="small" @click="addOption"
                >添加</ElButton
              >
            </div>
          </div>
        </ElFormItem>

        <!-- 附件字段配置 -->
        <template v-if="newField.type === FieldType.ATTACHMENT">
          <ElFormItem label="文件类型限制">
            <ElSelect
              v-model="attachmentConfig.acceptTypes"
              multiple
              placeholder="选择允许的文件类型"
              style="width: 100%">
              <ElOption label="图片 (image/*)" value="image/*" />
              <ElOption label="文档 (PDF)" value="application/pdf" />
              <ElOption label="文档 (Word .doc)" value="application/msword" />
              <ElOption
                label="文档 (Word .docx)"
                value="application/vnd.openxmlformats-officedocument.wordprocessingml.document" />
              <ElOption
                label="文档 (Excel .xls)"
                value="application/vnd.ms-excel" />
              <ElOption
                label="文档 (Excel .xlsx)"
                value="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" />
              <ElOption label="视频 (video/*)" value="video/*" />
              <ElOption label="音频 (audio/*)" value="audio/*" />
            </ElSelect>
            <div class="field-hint">不选择则表示允许所有文件类型</div>
          </ElFormItem>

          <ElFormItem label="单个文件大小">
            <ElInputNumber
              v-model="attachmentConfig.maxSize"
              :min="1"
              :max="100"
              :step="1"
              style="width: 200px">
              <template #suffix>MB</template>
            </ElInputNumber>
            <div class="field-hint">单个文件的最大大小，默认为 10MB</div>
          </ElFormItem>

          <ElFormItem label="最大文件数量">
            <ElInputNumber
              v-model="attachmentConfig.maxCount"
              :min="1"
              :max="50"
              :step="1"
              style="width: 200px" />
            <div class="field-hint">最多允许上传的文件数量，默认为 20 个</div>
          </ElFormItem>

          <ElFormItem label="生成缩略图">
            <ElSwitch v-model="attachmentConfig.enableThumbnail" />
            <div class="field-hint">开启后会对图片和视频生成缩略图</div>
          </ElFormItem>
        </template>

        <!-- 关联字段配置 -->
        <template v-if="newField.type === FieldType.LINK">
          <ElFormItem label="目标表" required>
            <ElSelect
              v-model="newField.linkConfig.targetTableId"
              placeholder="选择要关联的数据表"
              style="width: 100%">
              <ElOption
                v-for="table in availableTables"
                :key="table.id"
                :label="table.name"
                :value="table.id" />
            </ElSelect>
            <div class="field-hint">选择要关联的目标数据表</div>
          </ElFormItem>

          <ElFormItem label="关联类型" required>
            <ElRadioGroup v-model="newField.linkConfig.relationshipType">
              <ElRadioButton label="one_to_one">一对一</ElRadioButton>
              <ElRadioButton label="one_to_many">一对多</ElRadioButton>
              <ElRadioButton label="many_to_one">多对一</ElRadioButton>
            </ElRadioGroup>
            <div class="field-hint">
              一对一：每条记录只能关联一条目标记录；一对多：每条记录可以关联多条目标记录；多对一：多条记录可以关联到同一条目标记录
            </div>
          </ElFormItem>

          <ElFormItem label="显示字段">
            <ElSelect
              v-model="newField.linkConfig.displayFieldId"
              placeholder="选择在关联字段中显示的字段"
              clearable
              style="width: 100%">
              <ElOption
                v-for="field in targetTableFields"
                :key="field.id"
                :label="field.name"
                :value="field.id" />
            </ElSelect>
            <div class="field-hint">
              选择要在关联字段中显示的目标表字段，不选择则显示第一条字段
            </div>
          </ElFormItem>

          <ElFormItem label="双向关联">
            <ElSwitch v-model="newField.linkConfig.bidirectional" />
            <div class="field-hint">
              开启后会在目标表中自动创建一个反向关联字段，方便从目标记录查看关联的源记录
            </div>
          </ElFormItem>

          <!-- 关联关系预览 -->
          <ElFormItem v-if="newField.linkConfig.targetTableId" label="关联预览">
            <div class="link-preview">
              <div class="link-preview-item">
                <span class="link-preview-label">当前表:</span>
                <ElTag size="small">{{
                  tableStore.tables.find((t) => t.id === tableId)?.name ||
                  tableId
                }}</ElTag>
              </div>
              <div class="link-preview-arrow">
                <ElIcon><ArrowRight /></ElIcon>
                <span class="link-preview-type">
                  {{
                    newField.linkConfig.relationshipType === "one_to_one"
                      ? "一对一"
                      : newField.linkConfig.relationshipType === "one_to_many"
                        ? "一对多"
                        : "多对一"
                  }}
                </span>
              </div>
              <div class="link-preview-item">
                <span class="link-preview-label">目标表:</span>
                <ElTag size="small" type="success">
                  {{
                    tableStore.tables.find(
                      (t) => t.id === newField.linkConfig.targetTableId,
                    )?.name || newField.linkConfig.targetTableId
                  }}
                </ElTag>
              </div>
            </div>
          </ElFormItem>
        </template>

        <ElFormItem label="必填">
          <ElSwitch v-model="newField.isRequired" />
        </ElFormItem>

        <ElFormItem label="字段描述">
          <ElInput
            v-model="newField.description"
            type="textarea"
            :rows="2"
            placeholder="请输入字段描述（可选）" />
        </ElFormItem>

        <!-- 默认值配置 -->
        <ElFormItem label="默认值">
          <!-- 单行文本 -->
          <ElInput
            v-if="newField.type === FieldType.SINGLE_LINE_TEXT"
            v-model="newField.defaultValue"
            placeholder="请输入默认文本"
            style="width: 100%" />

          <!-- 多行文本 -->
          <ElInput
            v-else-if="newField.type === FieldType.LONG_TEXT"
            v-model="newField.defaultValue"
            type="textarea"
            :rows="3"
            placeholder="请输入默认文本"
            style="width: 100%" />

          <!-- 富文本 -->
          <ElInput
            v-else-if="newField.type === FieldType.RICH_TEXT"
            v-model="newField.defaultValue"
            type="textarea"
            :rows="3"
            placeholder="请输入默认文本"
            style="width: 100%" />

          <!-- 数字类型 -->
          <ElInputNumber
            v-else-if="newField.type === FieldType.NUMBER"
            v-model="newField.defaultValue"
            :precision="newField.precision"
            placeholder="请输入默认数值"
            style="width: 100%" />

          <!-- 日期类型 -->
          <div v-else-if="newField.type === FieldType.DATE" style="width: 100%">
            <div style="margin-bottom: 8px">
              <el-radio-group v-model="dateDefaultType" size="small">
                <el-radio-button label="">不使用默认值</el-radio-button>
                <el-radio-button label="now"
                  >使用添加记录的日期</el-radio-button
                >
                <el-radio-button label="custom">指定日期</el-radio-button>
              </el-radio-group>
            </div>
            <el-date-picker
              v-if="dateDefaultType === 'custom'"
              v-model="newField.defaultValue"
              type="date"
              format="YYYY-MM-DD"
              placeholder="选择默认日期"
              style="width: 100%" />
          </div>

          <!-- 日期时间类型 -->
          <div v-else-if="newField.type === FieldType.DATE_TIME" style="width: 100%">
            <div style="margin-bottom: 8px">
              <el-radio-group v-model="dateDefaultType" size="small">
                <el-radio-button label="">不使用默认值</el-radio-button>
                <el-radio-button label="now"
                  >使用添加记录的日期时间</el-radio-button
                >
                <el-radio-button label="custom">指定日期时间</el-radio-button>
              </el-radio-group>
            </div>
            <el-date-picker
              v-if="dateDefaultType === 'custom'"
              v-model="newField.defaultValue"
              type="datetime"
              format="YYYY-MM-DD HH:mm:ss"
              placeholder="选择默认日期时间"
              style="width: 100%" />
          </div>

          <!-- 单选类型 -->
          <ElSelect
            v-else-if="newField.type === FieldType.SINGLE_SELECT"
            v-model="newField.defaultValue"
            placeholder="请选择默认选项"
            clearable
            style="width: 100%">
            <ElOption
              v-for="option in selectOptions"
              :key="option.id"
              :label="option.name"
              :value="option.id" />
          </ElSelect>

          <!-- 多选类型 -->
          <ElSelect
            v-else-if="newField.type === FieldType.MULTI_SELECT"
            v-model="newField.defaultValue"
            placeholder="请选择默认选项"
            multiple
            collapse-tags
            collapse-tags-tooltip
            style="width: 100%">
            <ElOption
              v-for="option in selectOptions"
              :key="option.id"
              :label="option.name"
              :value="option.id" />
          </ElSelect>

          <!-- 复选框类型 -->
          <ElSwitch
            v-else-if="newField.type === FieldType.CHECKBOX"
            v-model="newField.defaultValue"
            active-text="选中"
            inactive-text="未选中" />

          <ElTag
            v-if="
              newField.defaultValue !== undefined &&
              newField.defaultValue !== null
            "
            type="success"
            size="small"
            style="margin-left: 8px">
            已设置
          </ElTag>
          <div class="field-hint">设置字段的默认值，创建记录时会自动填充</div>
        </ElFormItem>
      </ElForm>

      <div class="form-actions">
        <ElButton @click="backToList">返回</ElButton>
        <ElButton
          type="primary"
          @click="activeTab === 'create' ? createField() : updateField()">
          {{ activeTab === "create" ? "创建" : "保存" }}
        </ElButton>
      </div>
    </div>
  </ElDialog>
</template>

<style lang="scss" scoped>
@use "@/assets/styles/variables" as *;

.field-list {
  .field-list-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;
    padding-bottom: 12px;
    border-bottom: 1px solid $border-color;

    .field-count {
      color: $text-secondary;
      font-size: $font-size-sm;
    }
  }

  .field-items {
    max-height: 400px;
    overflow-y: auto;
  }

  .field-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px;
    border-radius: $border-radius-md;
    transition: background-color 0.2s;

    &:hover {
      background-color: $bg-color;

      .drag-handle {
        opacity: 1;
      }
    }

    &.is-system {
      opacity: 0.7;
    }

    .field-info {
      display: flex;
      align-items: center;
      gap: 8px;

      .drag-handle {
        opacity: 0;
        cursor: grab;
        color: $text-secondary;
        transition: opacity 0.2s;
        display: flex;
        align-items: center;

        &:active {
          cursor: grabbing;
        }
      }

      .field-icon {
        font-size: 16px;
      }

      .field-name {
        font-weight: 500;
        color: $text-primary;
      }

      .field-type {
        font-size: $font-size-xs;
        color: $text-secondary;
        background: $bg-color;
        padding: 2px 6px;
        border-radius: $border-radius-sm;
      }
    }

    .field-actions {
      display: flex;
      gap: 8px;
    }

    // 拖拽排序视觉反馈样式
    &.sortable-ghost {
      opacity: 0.4;
      background-color: $primary-light;
      border: 2px dashed $primary-color;
    }

    &.sortable-chosen {
      background-color: $primary-light;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.15);
    }

    &.sortable-drag {
      opacity: 0.9;
      background-color: white;
      box-shadow: 0 4px 12px rgba(0, 0, 0, 0.2);
      transform: scale(1.02);
    }
  }
}

.field-form {
  .type-option {
    display: flex;
    align-items: center;
    gap: 8px;

    .type-icon {
      font-size: 14px;
    }
  }

  .precision-config {
    display: flex;
    align-items: center;
    gap: 16px;
    .precision-value {
      min-width: 50px;
      color: $text-secondary;
      font-size: $font-size-sm;
    }
  }

  .field-hint {
    font-size: calc($font-size-xs * 0.85);
    color: $text-secondary;
    margin-top: 4px;
  }

  .options-editor {
    .options-list {
      display: flex;
      flex-direction: column;
      gap: 8px;
      margin-bottom: 12px;
    }

    .option-item {
      display: flex;
      align-items: center;
      gap: 8px;
    }

    .add-option {
      display: flex;
      align-items: center;
      gap: 8px;
    }
  }

  .form-actions {
    display: flex;
    justify-content: flex-end;
    gap: 12px;
    margin-top: 24px;
    padding-top: 16px;
    border-top: 1px solid $border-color;
  }

  .formula-functions {
    display: flex;
    flex-direction: column;
    gap: 12px;

    .function-category {
      .category-title {
        font-size: $font-size-sm;
        color: $text-secondary;
        margin-bottom: 8px;
        font-weight: 500;
      }

      .function-list {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
      }

      .function-tag {
        cursor: pointer;
        transition: all 0.2s;

        &:hover {
          background-color: $primary-color;
          color: white;
        }
      }
    }
  }

  .formula-fields {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    max-height: 120px;
    overflow-y: auto;
    padding: 8px;
    background-color: $bg-color;
    border-radius: $border-radius-sm;

    .field-tag {
      cursor: pointer;
      transition: all 0.2s;

      &:hover {
        background-color: $primary-color;
        color: white;
      }
    }
  }

  // 自动编号预览样式
  .auto-number-preview {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px 16px;
    background-color: $bg-color;
    border-radius: $border-radius-md;
    border: 1px dashed $border-color;

    .preview-label {
      font-size: $font-size-sm;
      color: $text-secondary;
      font-weight: 500;
    }

    .preview-value {
      font-size: $font-size-base;
      color: $primary-color;
      font-weight: 600;
      font-family: "SF Mono", Monaco, monospace;
      letter-spacing: 0.5px;
    }
  }

  // 关联字段预览样式
  .link-preview {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 12px;
    background-color: $bg-color;
    border-radius: $border-radius-md;
    border: 1px dashed $border-color;

    .link-preview-item {
      display: flex;
      align-items: center;
      gap: 8px;

      .link-preview-label {
        font-size: $font-size-sm;
        color: $text-secondary;
      }
    }

    .link-preview-arrow {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 4px;
      color: $primary-color;

      .link-preview-type {
        font-size: calc($font-size-xs * 0.85);
        color: $text-secondary;
      }
    }
  }
}
</style>
