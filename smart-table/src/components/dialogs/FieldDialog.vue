<script setup lang="ts">
import { ref, watch, nextTick, computed } from "vue";
import { useI18n } from "vue-i18n";
import { getLiteral } from "@/i18n";
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
  ElTooltip,
  ElNotification,
} from "element-plus";
import { fieldService } from "@/db/services/fieldService";
import { useViewStore } from "@/stores/viewStore";
import { useTableStore } from "@/stores/tableStore";
import {
  FieldType,
  getFieldTypeLabel,
  getFieldTypeIconComponent,
  getUserCreatableFieldTypeOptions,
  type FieldTypeValue,
  type LookupFieldConfig,
} from "@/types/fields";
import type { FieldEntity } from "@/db/schema";
import type { FieldOptions } from "@/types";
import type { RelationshipType } from "@/types/link";
import Sortable from "sortablejs";
import { Rank, ArrowRight, Link } from "@element-plus/icons-vue";
import { linkApiService } from "@/services/api/linkApiService";
import { lookupApiService } from "@/services/api/lookupApiService";
import MemberSelect from "@/components/common/MemberSelect.vue";
import LookupFieldConfigPanel from "@/components/fields/LookupFieldConfigPanel.vue";
import FormulaHelper from "@/components/fields/FormulaHelper.vue";
import { PRESET_REGEX_OPTIONS } from "@/utils/validation";

const { t } = useI18n();
const viewStore = useViewStore();
const tableStore = useTableStore();

// 用于预览的记录 ID（取当前表第一条记录）
const previewRecordId = computed(() => {
  const records = tableStore.records;
  return records.length > 0 ? records[0].id : undefined;
});

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
  // 数值字段展示格式配置
  format: "number" | "currency" | "percent" | "text";
  currencySymbol: string;
  prefix: string;
  suffix: string;
  thousandsSeparator: boolean;
  // 公式字段配置
  formula: string;
  // 关联字段配置
  linkConfig: {
    targetTableId: string;
    relationshipType: RelationshipType;
    displayFieldId: string;
    bidirectional: boolean;
  };
  // 查找字段配置
  lookupConfig: {
    name: string;
    config: LookupFieldConfig;
  };
  // 文本字段配置
  maxLength?: number;
  // 单行文本字段正则校验配置
  regex?: string;
  regexMessage?: string;
  // 单元格合并配置
  mergeCell: boolean;
}>({
  name: "",
  type: FieldType.SINGLE_LINE_TEXT,
  isRequired: false,
  description: "",
  defaultValue: undefined,
  precision: 0,
  format: "number",
  currencySymbol: "¥",
  prefix: "",
  suffix: "",
  thousandsSeparator: false,
  formula: "",
  linkConfig: {
    targetTableId: "",
    relationshipType: "one_to_many",
    displayFieldId: "",
    bidirectional: false,
  },
  lookupConfig: {
    name: "",
    config: {
      sourceTableId: "",
      targetFieldId: "",
      filterConditions: [],
      filterConjunction: "and",
      aggregationType: "original",
      fieldFormat: {
        type: "number",
        precision: 0,
        currencySymbol: "¥",
        dateFormat: "YYYY-MM-DD",
      },
    },
  },
  maxLength: undefined,
  regex: undefined,
  regexMessage: undefined,
  mergeCell: false,
});

// 用户可创建的字段类型配置列表
const fieldTypeConfigs = getUserCreatableFieldTypeOptions({
  includeSpecial: true,
  markSpecial: false,
});

const selectOptions = ref<{ id: string; name: string; color: string }[]>([]);
const newOptionName = ref("");
const newOptionColor = ref("#3370FF");

// 应用预置正则：同时写入 regex 与对应的提示信息
const applyPresetRegex = (preset: {
  label: string;
  pattern: string;
  message: string;
}) => {
  newField.value.regex = preset.pattern;
  newField.value.regexMessage = preset.message;
};

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

// 成员字段配置
const memberConfig = ref({
  defaultType: 'none' as 'none' | 'current_user' | 'specific_user',
  defaultUser: null as { id: string; name: string; email: string; avatar?: string } | null,
});

// 关联字段配置 - 可关联的表列表
const availableTables = computed(() => {
  // 使用 tableStore.tables 获取当前 base 的所有表（包含自身表，用于自关联）
  return tableStore.tables;
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
      // 自关联（关联自身表）时，默认使用一对多关系并禁用变更
      if (newTableId === props.tableId) {
        newField.value.linkConfig.relationshipType = "one_to_many";
      }
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
      filter: ".is-primary-field",
      onStart: () => {
        document.body.style.cursor = "grabbing";
      },
      onMove: (evt) => {
        const primaryField = sortedFields.value.find((f) => f.isPrimary);
        if (!primaryField) return true;

        const primaryFieldIndex = sortedFields.value.findIndex((f) => f.id === primaryField.id);
        if (primaryFieldIndex !== 0) return true;

        const draggedElement = evt.dragged;
        const relatedElement = evt.related;

        const allItems = Array.from(fieldListRef.value!.children);
        const draggedIndex = allItems.indexOf(draggedElement);
        const relatedIndex = allItems.indexOf(relatedElement);

        if (draggedIndex === -1 || relatedIndex === -1) return true;

        const isTryingToMoveBeforePrimary = relatedIndex === 0 && draggedIndex > 0;

        if (isTryingToMoveBeforePrimary) {
          ElMessage.closeAll();
          ElMessage({
            type: "warning",
            message: t('field.cannotDragBeforePrimary'),
            duration: 2000,
            showClose: true,
            customClass: "field-reorder-warning",
          });
          return false;
        }

        return true;
      },
      onEnd: (evt) => {
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

  const primaryField = sortedFields.value.find((f) => f.isPrimary);
  const primaryFieldIndex = primaryField ? sortedFields.value.findIndex((f) => f.id === primaryField.id) : -1;

  if (primaryField && primaryFieldIndex === 0) {
    const currentSortedFields = [...sortedFields.value];
    const [movedField] = currentSortedFields.splice(evt.oldIndex!, 1);
    
    if (movedField.id === primaryField.id) {
      ElNotification({
        title: t('field.notAllowedTitle'),
        message: t('field.primaryMoveMsg'),
        type: "warning",
        duration: 3000,
        position: "top" as any,
      });
      nextTick(() => initSortable());
      return;
    }

    if (evt.newIndex! <= primaryFieldIndex) {
      ElNotification({
        title: t('field.notAllowedTitle'),
        message: t('field.beforePrimaryMsg'),
        type: "warning",
        duration: 3000,
        position: "top" as any,
      });
      nextTick(() => initSortable());
      return;
    }
  }

  const currentSortedFields = [...sortedFields.value];
  const [movedField] = currentSortedFields.splice(evt.oldIndex!, 1);
  currentSortedFields.splice(evt.newIndex!, 0, movedField);

  const fieldIds = currentSortedFields.map((f) => f.id);

  try {
    await fieldService.reorderFields(props.tableId, fieldIds);
    emit("fields-reordered", fieldIds);
    ElMessage.success(t('field.fieldSortUpdated'));
  } catch (error) {
    ElMessage.error(t('field.fieldSortFailed'));
    nextTick(() => initSortable());
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
    format: "number",
    currencySymbol: "¥",
    prefix: "",
    suffix: "",
    thousandsSeparator: false,
    formula: "",
    linkConfig: {
      targetTableId: "",
      relationshipType: "one_to_many",
      displayFieldId: "",
      bidirectional: false,
    },
    lookupConfig: {
      name: "",
      config: {
        sourceTableId: "",
        targetFieldId: "",
        filterConditions: [],
        filterConjunction: "and",
        aggregationType: "original",
        fieldFormat: {
          type: "number",
          precision: 0,
          currencySymbol: "¥",
          dateFormat: "YYYY-MM-DD",
        },
      },
    },
    maxLength: undefined,
    regex: undefined,
    regexMessage: undefined,
    mergeCell: false,
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
  // 重置成员配置
  memberConfig.value = {
    defaultType: 'none',
    defaultUser: null,
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
    format: ((field.options?.format as "number" | "currency" | "percent" | "text") ?? "number"),
    currencySymbol: (field.options?.currencySymbol as string) ?? "¥",
    prefix: (field.options?.prefix as string) ?? "",
    suffix: (field.options?.suffix as string) ?? "",
    thousandsSeparator: Boolean(field.options?.thousandsSeparator),
    formula: (field.options?.formula as string) ?? "",
    // 关联字段的配置保存在 config 中
    linkConfig: {
      targetTableId: (field.config?.linkedTableId as string) ?? "",
      relationshipType:
        (field.config?.relationshipType as RelationshipType) ?? "one_to_many",
      displayFieldId: (field.config?.displayFieldId as string) ?? "",
      bidirectional: (field.config?.bidirectional as boolean) ?? false,
    },
    // 查找字段的配置保存在 config 中
    lookupConfig: {
      name: field.name,
      config: (field.config as unknown as LookupFieldConfig) || {
        sourceTableId: "",
        targetFieldId: "",
        filterConditions: [],
        filterConjunction: "and",
        aggregationType: "original",
        fieldFormat: {
          type: "number",
          precision: 0,
          currencySymbol: "¥",
          dateFormat: "YYYY-MM-DD",
        },
      },
    },
    maxLength: (field.options?.maxLength as number) ?? undefined,
    regex: (field.options?.regex as string) ?? undefined,
    regexMessage: (field.options?.regexMessage as string) ?? undefined,
    mergeCell: Boolean(field.options?.mergeCell),
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

  // 加载成员字段配置
  if (field.type === FieldType.MEMBER) {
    const memberDefaultType = field.options?.memberDefaultType as string | undefined;
    if (memberDefaultType === 'current_user') {
      memberConfig.value.defaultType = 'current_user';
      newField.value.defaultValue = 'current_user';
    } else if (memberDefaultType === 'specific_user' && field.options?.memberDefaultUser) {
      memberConfig.value.defaultType = 'specific_user';
      memberConfig.value.defaultUser = field.options.memberDefaultUser as typeof memberConfig.value.defaultUser;
      newField.value.defaultValue = memberConfig.value.defaultUser?.id;
    } else {
      memberConfig.value.defaultType = 'none';
      memberConfig.value.defaultUser = null;
      newField.value.defaultValue = undefined;
    }
  } else {
    memberConfig.value.defaultType = 'none';
    memberConfig.value.defaultUser = null;
  }
}

function backToList() {
  activeTab.value = "list";
  editingField.value = null;
  nextTick(() => {
    initSortable();
  });
  newField.value = {
    name: "",
    type: FieldType.SINGLE_LINE_TEXT,
    isRequired: false,
    description: "",
    defaultValue: undefined,
    precision: 0,
    format: "number",
    currencySymbol: "¥",
    prefix: "",
    suffix: "",
    thousandsSeparator: false,
    formula: "",
    linkConfig: {
      targetTableId: "",
      relationshipType: "one_to_many",
      displayFieldId: "",
      bidirectional: false,
    },
    lookupConfig: {
      name: "",
      config: {
        sourceTableId: "",
        targetFieldId: "",
        filterConditions: [],
        filterConjunction: "and",
        aggregationType: "original",
        fieldFormat: {
          type: "number",
          precision: 0,
          currencySymbol: "¥",
          dateFormat: "YYYY-MM-DD",
        },
      },
    },
    maxLength: undefined,
    regex: undefined,
    regexMessage: undefined,
    mergeCell: false,
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
    ElMessage.warning(t('field.nameRequired'));
    return;
  }

  // 关联字段特殊验证
  if (newField.value.type === FieldType.LINK) {
    if (!newField.value.linkConfig.targetTableId) {
      ElMessage.warning(t('field.selectTargetTableRequired'));
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
    // 数值字段精度与展示格式配置
    if (newField.value.type === FieldType.NUMBER) {
      options.precision = newField.value.precision;
      options.format = newField.value.format;
      options.currencySymbol = newField.value.currencySymbol;
      options.prefix = newField.value.prefix || undefined;
      options.suffix = newField.value.suffix || undefined;
      options.thousandsSeparator = newField.value.thousandsSeparator || undefined;
    }
    // 公式字段配置
    if (newField.value.type === FieldType.FORMULA) {
      options.formula = newField.value.formula;
      options.format = newField.value.format;
      // 文本格式无需小数位数、前后缀、货币符号、千分位等数值相关配置
      if (newField.value.format !== "text") {
        options.precision = newField.value.precision ?? 0;
        options.currencySymbol = newField.value.currencySymbol;
        options.prefix = newField.value.prefix || undefined;
        options.suffix = newField.value.suffix || undefined;
        options.thousandsSeparator = newField.value.thousandsSeparator || undefined;
      }
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
    // 单行文本字段正则校验配置
    if (newField.value.type === FieldType.SINGLE_LINE_TEXT) {
      if (newField.value.regex) {
        options.regex = newField.value.regex;
        if (newField.value.regexMessage) {
          options.regexMessage = newField.value.regexMessage;
        }
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
    // 成员字段配置
    // 统一使用数组格式存储，通过 memberDefaultType 区分不同类型
    if (newField.value.type === FieldType.MEMBER) {
      if (memberConfig.value.defaultType === 'current_user') {
        options.memberDefaultType = 'current_user';
        delete options.memberDefaultUser;
        // 统一存储为数组格式，但使用空数组表示动态获取当前用户
        options.defaultValue = [];
      } else if (memberConfig.value.defaultType === 'specific_user' && memberConfig.value.defaultUser) {
        options.memberDefaultType = 'specific_user';
        // 使用解构创建普通对象，避免响应式代理问题
        options.memberDefaultUser = {
          id: memberConfig.value.defaultUser.id,
          name: memberConfig.value.defaultUser.name,
          email: memberConfig.value.defaultUser.email,
          avatar: memberConfig.value.defaultUser.avatar,
        };
        // 统一存储为数组格式
        options.defaultValue = [memberConfig.value.defaultUser.id];
      } else {
        // 不设默认值
        delete options.memberDefaultType;
        delete options.memberDefaultUser;
        options.defaultValue = [];
      }
    }

    // 单元格合并配置
    if (newField.value.mergeCell) {
      options.mergeCell = true;
    }

    let field;

    // 如果是查找字段，使用专门的查找字段创建接口
    if (newField.value.type === FieldType.LOOKUP) {
      try {
        const result = await lookupApiService.createLookupField(props.tableId, {
          name: newField.value.lookupConfig.name || newField.value.name.trim(),
          description: newField.value.description,
          config: newField.value.lookupConfig.config,
        });
        field = result as unknown as FieldEntity;
      } catch (lookupError) {
        console.error("创建查找字段失败:", lookupError);
        throw lookupError;
      }
    } else if (newField.value.type === FieldType.LINK) {
      // 如果是关联字段，使用专门的关联字段创建接口
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
        field = result.field as unknown as FieldEntity;
      } catch (linkError) {
        console.error("创建关联字段失败:", linkError);
        throw linkError;
      }
    } else {
      // 非关联字段，使用普通字段创建
      // 构建创建数据
      const createData: Record<string, unknown> = {
        tableId: props.tableId,
        name: newField.value.name.trim(),
        type: newField.value.type,
        isRequired: newField.value.isRequired,
        description: newField.value.description,
        options: Object.keys(options).length > 0 ? options : undefined,
      };

      // 对于非成员字段，使用 defaultValue；成员字段的默认值已在 options 中设置
      if (newField.value.type !== FieldType.MEMBER && newField.value.defaultValue !== undefined) {
        createData.defaultValue = newField.value.defaultValue;
      }

      field = await fieldService.createField(createData as any);
    }

    emit("field-created", field);
    ElMessage.success(t('field.fieldCreated'));
    backToList();
  } catch (error) {
    ElMessage.error(t('field.fieldCreateFailed'));
  }
}

async function updateField() {
  if (!editingField.value) return;
  if (!newField.value.name.trim()) {
    ElMessage.warning(t('field.nameRequired'));
    return;
  }

  // 关联字段特殊验证
  if (newField.value.type === FieldType.LINK) {
    if (!newField.value.linkConfig.targetTableId) {
      ElMessage.warning(t('field.selectTargetTableRequired'));
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
    // 数值字段精度与展示格式配置
    if (newField.value.type === FieldType.NUMBER) {
      options.precision = newField.value.precision;
      options.format = newField.value.format;
      options.currencySymbol = newField.value.currencySymbol;
      options.prefix = newField.value.prefix || undefined;
      options.suffix = newField.value.suffix || undefined;
      options.thousandsSeparator = newField.value.thousandsSeparator || undefined;
    }
    // 公式字段配置
    if (newField.value.type === FieldType.FORMULA) {
      options.formula = newField.value.formula;
      options.format = newField.value.format;
      // 文本格式无需小数位数、前后缀、货币符号、千分位等数值相关配置
      if (newField.value.format !== "text") {
        options.precision = newField.value.precision ?? 0;
        options.currencySymbol = newField.value.currencySymbol;
        options.prefix = newField.value.prefix || undefined;
        options.suffix = newField.value.suffix || undefined;
        options.thousandsSeparator = newField.value.thousandsSeparator || undefined;
      }
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
    // 单行文本字段正则校验配置
    if (newField.value.type === FieldType.SINGLE_LINE_TEXT) {
      if (newField.value.regex) {
        options.regex = newField.value.regex;
        if (newField.value.regexMessage) {
          options.regexMessage = newField.value.regexMessage;
        }
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
    // 成员字段配置
    // 统一使用数组格式存储，通过 memberDefaultType 区分不同类型
    if (newField.value.type === FieldType.MEMBER) {
      if (memberConfig.value.defaultType === 'current_user') {
        options.memberDefaultType = 'current_user';
        delete options.memberDefaultUser;
        // 统一存储为数组格式，但使用空数组表示动态获取当前用户
        options.defaultValue = [];
      } else if (memberConfig.value.defaultType === 'specific_user' && memberConfig.value.defaultUser) {
        options.memberDefaultType = 'specific_user';
        // 使用解构创建普通对象，避免响应式代理问题
        options.memberDefaultUser = {
          id: memberConfig.value.defaultUser.id,
          name: memberConfig.value.defaultUser.name,
          email: memberConfig.value.defaultUser.email,
          avatar: memberConfig.value.defaultUser.avatar,
        };
        // 统一存储为数组格式
        options.defaultValue = [memberConfig.value.defaultUser.id];
      } else {
        // 不设默认值
        delete options.memberDefaultType;
        delete options.memberDefaultUser;
        options.defaultValue = [];
      }
    }

    // 单元格合并配置
    if (newField.value.mergeCell) {
      options.mergeCell = true;
    } else {
      delete options.mergeCell;
    }

    // 构建更新数据
    const updateData: Record<string, unknown> = {
      name: newField.value.name.trim(),
      type: newField.value.type,
      is_required: newField.value.isRequired,
      description: newField.value.description,
      options: options as Record<string, unknown>,
    };

    // 对于非成员字段，使用 defaultValue；成员字段的默认值已在 options 中设置
    if (newField.value.type !== FieldType.MEMBER && newField.value.defaultValue !== undefined) {
      updateData.defaultValue = newField.value.defaultValue;
    }

    let updatedField: FieldEntity | undefined;

    // 如果是查找字段，使用专门的查找字段更新接口
    if (newField.value.type === FieldType.LOOKUP) {
      try {
        updatedField = (await lookupApiService.updateLookupField(
          editingField.value.id,
          {
            name: newField.value.lookupConfig.name || newField.value.name.trim(),
            description: newField.value.description,
            config: newField.value.lookupConfig.config,
          },
        )) as unknown as FieldEntity;
      } catch (lookupError) {
        console.error("更新查找字段失败:", lookupError);
        throw lookupError;
      }
    } else {
      // 非查找字段，使用普通字段更新接口
      updatedField = await fieldService.updateField(
        editingField.value.id,
        updateData,
      );

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
    }

    if (updatedField) {
      emit("field-updated", updatedField);
    }
    ElMessage.success(t('field.fieldUpdated'));
    backToList();
  } catch (error) {
    ElMessage.error(t('field.fieldUpdateFailed'));
  }
}

async function deleteField(field: FieldEntity) {
  if (field.isSystem) {
    ElMessage.warning(t('field.systemCannotDelete'));
    return;
  }

  if (field.isPrimary) {
    ElMessage.warning(t('field.primaryCannotDelete'));
    return;
  }

  try {
    await ElMessageBox.confirm(
      t('field.deleteFieldConfirm', { name: field.name }),
      t('field.deleteTitle'),
      {
        confirmButtonText: t('field.deleteConfirmBtn'),
        cancelButtonText: t('common.cancel'),
        type: "warning",
        confirmButtonClass: "el-button--danger",
      },
    );

    await fieldService.deleteField(field.id);
    emit("field-deleted", field.id);
    ElMessage.success(t('field.fieldDeleted'));
  } catch (error) {
    if (error === "cancel" || error === "close") {
      return;
    }
    ElMessage.error(t('field.fieldDeleteFailed'));
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
  // 切换类型时重置查找字段配置
  if (newField.value.type !== FieldType.LOOKUP) {
    newField.value.lookupConfig = {
      name: "",
      config: {
        sourceTableId: "",
        targetFieldId: "",
        filterConditions: [],
        filterConjunction: "and",
        aggregationType: "original",
        fieldFormat: {
          type: "number",
          precision: 0,
          currencySymbol: "¥",
          dateFormat: "YYYY-MM-DD",
        },
      },
    };
  }
}

/** 查找字段配置面板更新回调 */
function onLookupConfigUpdate(value: { name: string; config: LookupFieldConfig }) {
  newField.value.lookupConfig.name = value.name;
  newField.value.lookupConfig.config = value.config;
  // 同步名称到 newField.name（如果用户在配置面板中修改了名称）
  if (value.name) {
    newField.value.name = value.name;
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

// 处理公式插入（从 FormulaHelper 组件）
function handleFormulaInsert(formula: { name: string; syntax: string }) {
  const formulaInput = document.querySelector(
    '.formula-field textarea, [placeholder*="公式"]',
  ) as HTMLTextAreaElement;
  
  // 插入语法示例（去掉参数说明，只保留函数名和括号）
  const insertText = formula.syntax.replace(/\s+/g, ' ').trim();
  
  if (formulaInput) {
    const start = formulaInput.selectionStart;
    const end = formulaInput.selectionEnd;
    const currentValue = newField.value.formula;
    const newValue =
      currentValue.substring(0, start) + insertText + currentValue.substring(end);
    newField.value.formula = newValue;
    nextTick(() => {
      formulaInput.focus();
      // 将光标移到插入文本末尾
      formulaInput.setSelectionRange(
        start + insertText.length,
        start + insertText.length,
      );
    });
  } else {
    newField.value.formula += insertText;
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
  // console.log(
  //   `[FieldDialog] isFieldHiddenInView(${fieldId}):`,
  //   result,
  //   "hiddenFields:",
  //   hiddenFields,
  // );
  return result;
}

// 获取字段当前实际显示状态（同时考虑全局隐藏和视图级隐藏）
function getFieldActualVisibility(field: FieldEntity): boolean {
  const isGloballyVisible = field.isVisible !== false;
  const isHiddenInView = isFieldHiddenInView(field.id);
  const result = isGloballyVisible && !isHiddenInView;
  // console.log(
  //   `[FieldDialog] getFieldActualVisibility(${field.name}):`,
  //   result,
  //   "isGloballyVisible:",
  //   isGloballyVisible,
  //   "isHiddenInView:",
  //   isHiddenInView,
  // );
  return result;
}

async function toggleFieldVisibility(
  field: FieldEntity,
  newVisibility: boolean,
) {
  if (field.isPrimary && !newVisibility) {
    ElMessage.warning(t('field.primaryCannotHide'));
    return;
  }

  // console.log(
  //   `[FieldDialog] toggleFieldVisibility called for ${field.name}, newVisibility:`,
  //   newVisibility,
  // );
  // console.log(`[FieldDialog] current field state:`, {
  //   isVisible: field.isVisible,
  //   hiddenFields: viewStore.currentView?.hiddenFields,
  // });

  try {
    const currentVisibility = getFieldActualVisibility(field);
    const isHiddenInView = isFieldHiddenInView(field.id);
    const isGloballyVisible = field.isVisible !== false;

    // console.log(
    //   `[FieldDialog] currentVisibility:`,
    //   currentVisibility,
    //   "isHiddenInView:",
    //   isHiddenInView,
    //   "isGloballyVisible:",
    //   isGloballyVisible,
    // );

    if (!currentVisibility && newVisibility) {
      if (isHiddenInView) {
        // console.log(
        //   `[FieldDialog] Emitting field-visibility-changed: ${field.id}, true`,
        // );
        emit("field-visibility-changed", field.id, true);
        ElMessage.success(t('field.fieldShown', { name: field.name }));
        return;
      } else if (!isGloballyVisible) {
        // console.log(
        //   `[FieldDialog] Updating global visibility: ${field.id}, true`,
        // );
        await fieldService.updateFieldVisibility(field.id, true);
        emit("field-updated", { ...field, isVisible: true });
        ElMessage.success(t('field.fieldShown', { name: field.name }));
        return;
      }
    }

    if (currentVisibility && !newVisibility) {
      // console.log(
      //   `[FieldDialog] Emitting field-visibility-changed: ${field.id}, false`,
      // );
      emit("field-visibility-changed", field.id, false);
      ElMessage.success(t('field.fieldHidden', { name: field.name }));
      return;
    }

    // console.log(`[FieldDialog] No state change needed`);
    ElMessage.info(t('field.fieldStateUnchanged', { name: field.name }));
  } catch (error) {
    console.error(`[FieldDialog] Error in toggleFieldVisibility:`, error);
    ElMessage.error(t('field.updateVisibilityFailed'));
    emit("field-updated", { ...field });
  }
}
</script>

<template>
  <ElDialog
    :model-value="visible"
    @update:model-value="$emit('update:visible', $event)"
    :title="t('field.manage')"
    width="600px"
    :close-on-click-modal="false">
    <!-- 字段列表 -->
    <div v-if="activeTab === 'list'" class="field-list">
      <div class="field-list-header">
        <span class="field-count">{{ t('field.totalFields', { count: fields.length }) }}</span>
        <ElButton type="primary" size="small" @click="openCreateField">
          + {{ t('field.addField') }}
        </ElButton>
      </div>

      <div ref="fieldListRef" class="field-items">
        <ElTooltip
          v-for="field in sortedFields"
          :key="field.id"
          :disabled="!field.isPrimary"
          placement="top"
          effect="dark">
          <template #content>
            <div class="primary-field-tooltip">
              {{ t('field.primaryFieldTooltip') }}
            </div>
          </template>
          <div
            class="field-item"
            :class="{ 
              'is-system': field.isSystem,
              'is-primary-field': field.isPrimary 
            }"
            :data-field-id="field.id">
            <div class="field-info">
              <span 
                class="drag-handle" 
                :class="{ 'disabled': field.isPrimary }"
                :title="field.isPrimary ? t('field.primaryCannotMove') : t('field.dragToSort')">
                <ElIcon><Rank /></ElIcon>
              </span>
              <span class="field-icon">
                <el-icon>
                  <component :is="getFieldTypeIconComponent(field.type)" />
                </el-icon>
              </span>
              <span class="field-name">{{ field.name }}</span>
              <span class="field-type">{{ getFieldTypeLabel(field.type) }}</span>
              <ElTag v-if="field.isPrimary" size="small" type="success">{{ t('field.primary') }}</ElTag>
              <ElTag v-if="field.isSystem" size="small" type="info">{{ t('field.system') }}</ElTag>
              <ElTag v-if="field.isRequired" size="small" type="warning"
                >{{ t('field.required') }}</ElTag
              >
            </div>
            <div class="field-actions">
              <ElSwitch
                v-if="!field.isPrimary"
                :model-value="getFieldActualVisibility(field)"
                :active-value="true"
                :inactive-value="false"
                size="small"
                inline-prompt
                :active-text="t('field.show')"
                :inactive-text="t('field.hide')"
                @change="(val) => toggleFieldVisibility(field, val as boolean)"
                style="margin-right: 8px" />
              <ElButton
                v-if="!field.isSystem"
                link
                type="primary"
                size="small"
                @click="openEditField(field)">
                {{ t('common.edit') }}
              </ElButton>
              <ElButton
                v-if="!field.isSystem && !field.isPrimary"
                link
                type="danger"
                size="small"
                @click="deleteField(field)">
                {{ t('common.delete') }}
              </ElButton>
            </div>
          </div>
        </ElTooltip>
      </div>
    </div>

    <!-- 创建/编辑字段 -->
    <div v-else class="field-form">
      <ElForm label-width="100px">
        <ElFormItem :label="t('field.fieldName')" required>
          <ElInput
            v-model="newField.name"
            :placeholder="t('field.nameRequired')"
            maxlength="50"
            show-word-limit />
        </ElFormItem>

        <ElFormItem :label="t('field.fieldType')" required>
          <ElSelect
            v-model="newField.type"
            style="width: 100%"
            @change="onTypeChange">
            <ElOption
              v-for="config in fieldTypeConfigs"
              :key="config.value"
              :label="config.label"
              :value="config.value">
              <span class="type-option">
                <span class="type-icon">
                  <el-icon>
                    <component :is="config.icon" />
                  </el-icon>
                </span>
                <span>{{ config.label }}</span>
              </span>
            </ElOption>
          </ElSelect>
        </ElFormItem>

        <!-- 文本字段最大长度配置 -->
        <ElFormItem
          v-if="newField.type === FieldType.SINGLE_LINE_TEXT || newField.type === FieldType.LONG_TEXT || newField.type === FieldType.RICH_TEXT"
          :label="t('field.maxLength')">
          <ElInputNumber
            v-model="newField.maxLength"
            :min="1"
            :max="10000"
            :step="1"
            :placeholder="t('field.noLimit')"
            style="width: 200px" />
          <div class="field-hint">{{ t('field.maxLengthHint') }}</div>
        </ElFormItem>

        <!-- 单行文本字段正则校验配置 -->
        <template v-if="newField.type === FieldType.SINGLE_LINE_TEXT">
          
          <ElFormItem :label="t('field.regex')">
            <ElInput
              v-model="newField.regex"
              :placeholder="t('field.regexPlaceholder')"
              clearable />
            <div class="field-hint">{{ t('field.regexHint') }}</div>
            <div class="regex-preset-list" style="display: flex; flex-wrap: wrap; gap: 8px;">
              <ElTag
                v-for="preset in PRESET_REGEX_OPTIONS"
                :key="preset.label"
                size="small"
                type="info"
                effect="plain"
                :title="t('field.regexPresetTitle')"
                style="cursor: pointer; user-select: none"
                @click="applyPresetRegex(preset)">
                {{ preset.label }}
              </ElTag>
            </div>
          </ElFormItem>
          <ElFormItem v-if="newField.regex" :label="t('field.regexMessage')">
            <ElInput
              v-model="newField.regexMessage"
              :placeholder="t('field.regexMessagePlaceholder')"
              clearable />
          </ElFormItem>
        </template>

        <!-- 数值字段精度配置 -->
        <ElFormItem v-if="newField.type === FieldType.NUMBER" :label="t('field.precision')">
          <div class="precision-config">
            <ElSlider
              v-model="newField.precision"
              :min="0"
              :max="10"
              :step="1"
              show-stops
              style="width: 300px" />
            <span class="precision-value">{{ newField.precision }} {{ t('field.digitsUnit') }}</span>
          </div>
          <div class="field-hint">{{ t('field.precisionHint') }}</div>
        </ElFormItem>

        <!-- 自定义前缀文字 -->
        <ElFormItem
          v-if="newField.type === FieldType.NUMBER"
          :label="t('field.numberPrefix')">
          <ElInput
            v-model="newField.prefix"
            :maxlength="10"
            style="width: 220px"
            :placeholder="t('field.numberPrefixHint')" />
        </ElFormItem>

        <!-- 自定义后缀文字 -->
        <ElFormItem
          v-if="newField.type === FieldType.NUMBER"
          :label="t('field.numberSuffix')">
          <ElInput
            v-model="newField.suffix"
            :maxlength="10"
            style="width: 220px"
            :placeholder="t('field.numberSuffixHint')" />
        </ElFormItem>

        <!-- 千分位分隔符 -->
        <ElFormItem
          v-if="newField.type === FieldType.NUMBER"
          :label="t('field.thousandsSeparator')">
          <ElSwitch v-model="newField.thousandsSeparator" />
          <div class="field-hint">{{ t('field.thousandsSeparatorHint') }}</div>
        </ElFormItem>

        <!-- 公式字段配置 -->
        <template v-if="newField.type === FieldType.FORMULA">
          <ElFormItem :label="t('field.formulaExpr')" required>
            <ElInput
              v-model="newField.formula"
              type="textarea"
              :rows="3"
              :placeholder="getLiteral('field.formulaExprPlaceholder')"
              maxlength="500"
              show-word-limit />
            <div class="field-hint">
              {{ getLiteral('field.formulaExprHint') }}
            </div>
          </ElFormItem>

          <!-- 公式字段显示格式（置于小数位数之前） -->
          <ElFormItem :label="t('field.numFormat')">
            <ElSelect v-model="newField.format" style="width: 220px">
              <ElOption :label="t('field.numberFormat')" value="number" />
              <ElOption :label="t('field.currencyFormat')" value="currency" />
              <ElOption :label="t('field.percentFormat')" value="percent" />
              <ElOption :label="t('field.textFormat')" value="text" />
            </ElSelect>
          </ElFormItem>

          <!-- 小数位数（文本格式不展示） -->
          <ElFormItem
            v-if="newField.format !== 'text'"
            :label="t('field.precision')">
            <div class="precision-config">
              <ElSlider
                v-model="newField.precision"
                :min="0"
                :max="10"
                :step="1"
                show-stops
                style="width: 300px" />
              <span class="precision-value"
                >{{ newField.precision }} {{ t('field.digitsUnit') }}</span
              >
            </div>
            <div class="field-hint">{{ t('field.formulaPrecisionHint') }}</div>
          </ElFormItem>

          <!-- 货币符号（仅货币格式显示） -->
          <ElFormItem
            v-if="newField.format === 'currency'"
            :label="t('field.currencySymbolLabel')">
            <ElInput
              v-model="newField.currencySymbol"
              :maxlength="4"
              style="width: 220px"
              :placeholder="t('field.currencySymbolPlaceholder')" />
          </ElFormItem>

          <!-- 自定义前缀文字（货币格式使用货币符号，故不在此配置；文本格式不展示） -->
          <ElFormItem
            v-if="newField.format !== 'currency' && newField.format !== 'text'"
            :label="t('field.numberPrefix')">
            <ElInput
              v-model="newField.prefix"
              :maxlength="10"
              style="width: 220px"
              :placeholder="t('field.numberPrefixHint')" />
          </ElFormItem>

          <!-- 自定义后缀文字（百分比格式后缀固定为 %，故不在此配置；文本格式不展示） -->
          <ElFormItem
            v-if="newField.format === 'number'"
            :label="t('field.numberSuffix')">
            <ElInput
              v-model="newField.suffix"
              :maxlength="10"
              style="width: 220px"
              :placeholder="t('field.numberSuffixHint')" />
          </ElFormItem>

          <!-- 千分位分隔符（文本格式不展示） -->
          <ElFormItem
            v-if="newField.format !== 'text'"
            :label="t('field.thousandsSeparator')">
            <ElSwitch v-model="newField.thousandsSeparator" />
            <div class="field-hint">{{ t('field.thousandsSeparatorHint') }}</div>
          </ElFormItem>

          <ElFormItem :label="t('field.formulaFunctions')">
            <FormulaHelper @insert="handleFormulaInsert" />
          </ElFormItem>

          <ElFormItem :label="t('field.availableFields')">
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
          <ElFormItem :label="t('field.preview')">
            <div class="auto-number-preview">
              <span class="preview-label">{{ t('field.previewLabel') }}:</span>
              <span class="preview-value">{{ autoNumberPreview }}</span>
            </div>
          </ElFormItem>

          <ElFormItem :label="t('field.startNumber')">
            <ElInputNumber
              v-model="autoNumberConfig.startNumber"
              :min="1"
              :max="999999"
              :step="1"
              style="width: 200px" />
            <div class="field-hint">{{ t('field.startNumberHint') }}</div>
          </ElFormItem>

          <ElFormItem :label="t('field.prefix')">
            <ElInput
              v-model="autoNumberConfig.prefix"
              :placeholder="t('field.prefixExample')"
              maxlength="20"
              show-word-limit
              style="width: 200px" />
            <div class="field-hint">{{ t('field.prefixHint') }}</div>
          </ElFormItem>

          <ElFormItem :label="t('field.suffix')">
            <ElInput
              v-model="autoNumberConfig.suffix"
              :placeholder="t('field.suffixExample')"
              maxlength="20"
              show-word-limit
              style="width: 200px" />
            <div class="field-hint">{{ t('field.suffixHint') }}</div>
          </ElFormItem>

          <ElFormItem :label="t('field.digitLength')">
            <ElInputNumber
              v-model="autoNumberConfig.digitLength"
              :min="0"
              :max="10"
              :step="1"
              style="width: 200px" />
            <div class="field-hint">{{ t('field.digitsHint') }}</div>
          </ElFormItem>

          <ElFormItem :label="t('field.includeDate')">
            <ElSwitch
              v-model="autoNumberConfig.includeDate"
              :active-text="t('common.yes')"
              :inactive-text="t('common.no')" />
            <div class="field-hint">{{ t('field.includeDateHint') }}</div>
          </ElFormItem>

          <ElFormItem v-if="autoNumberConfig.includeDate" :label="t('field.dateFormat')">
            <ElSelect v-model="autoNumberConfig.dateFormat" style="width: 200px">
              <ElOption label="YYYYMMDD (20240115)" value="YYYYMMDD" />
              <ElOption label="YYYYMM (202401)" value="YYYYMM" />
              <ElOption label="YYYY (2024)" value="YYYY" />
              <ElOption label="YYMMDD (240115)" value="YYMMDD" />
            </ElSelect>
            <div class="field-hint">{{ t('field.dateFormatHint') }}</div>
          </ElFormItem>
        </template>

        <ElFormItem
          v-if="
            newField.type === FieldType.SINGLE_SELECT ||
            newField.type === FieldType.MULTI_SELECT
          "
          :label="t('field.options')">
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
                  :placeholder="t('field.optionNamePlaceholder')" />
                <ElButton
                  link
                  type="danger"
                  size="small"
                  @click="removeOption(index)">
                  {{ t('common.delete') }}
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
                :placeholder="t('field.optionNameInputPlaceholder')"
                @keyup.enter="addOption" />
              <ElButton type="primary" size="small" @click="addOption"
                >{{ t('field.addOption') }}</ElButton
              >
            </div>
          </div>
        </ElFormItem>

        <!-- 附件字段配置 -->
        <template v-if="newField.type === FieldType.ATTACHMENT">
          <ElFormItem :label="t('field.fileTypeLimit')">
            <ElSelect
              v-model="attachmentConfig.acceptTypes"
              multiple
              :placeholder="t('field.fileTypeLimitPlaceholder')"
              style="width: 100%">
              <ElOption :label="t('field.fileTypeImage')" value="image/*" />
              <ElOption :label="t('field.fileTypePdf')" value="application/pdf" />
              <ElOption :label="t('field.fileTypeWordDoc')" value="application/msword" />
              <ElOption
                :label="t('field.fileTypeWordDocx')"
                value="application/vnd.openxmlformats-officedocument.wordprocessingml.document" />
              <ElOption
                :label="t('field.fileTypeExcelXls')"
                value="application/vnd.ms-excel" />
              <ElOption
                :label="t('field.fileTypeExcelXlsx')"
                value="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" />
              <ElOption :label="t('field.fileTypeVideo')" value="video/*" />
              <ElOption :label="t('field.fileTypeAudio')" value="audio/*" />
            </ElSelect>
            <div class="field-hint">{{ t('field.fileTypeLimitHint') }}</div>
          </ElFormItem>

          <ElFormItem :label="t('field.singleFileSize')">
            <ElInputNumber
              v-model="attachmentConfig.maxSize"
              :min="1"
              :max="100"
              :step="1"
              style="width: 200px">
              <template #suffix>MB</template>
            </ElInputNumber>
            <div class="field-hint">{{ t('field.singleFileSizeHint') }}</div>
          </ElFormItem>

          <ElFormItem :label="t('field.maxFileCount')">
            <ElInputNumber
              v-model="attachmentConfig.maxCount"
              :min="1"
              :max="50"
              :step="1"
              style="width: 200px" />
            <div class="field-hint">{{ t('field.maxFileCountHint') }}</div>
          </ElFormItem>

          <ElFormItem :label="t('field.generateThumbnail')">
            <ElSwitch v-model="attachmentConfig.enableThumbnail" />
            <div class="field-hint">{{ t('field.generateThumbnailHint') }}</div>
          </ElFormItem>
        </template>

        <!-- 关联字段配置 -->
        <template v-if="newField.type === FieldType.LINK">
          <ElFormItem :label="t('field.targetTable')" required>
            <ElSelect
              v-model="newField.linkConfig.targetTableId"
              :placeholder="t('field.selectTargetTablePlaceholder')"
              style="width: 100%">
              <ElOption
                v-for="table in availableTables"
                :key="table.id"
                :label="table.id === tableId ? `${table.name}${t('field.currentTableSuffix')}` : table.name"
                :value="table.id" />
            </ElSelect>
            <div class="field-hint">{{ t('field.targetTableHint') }}</div>
            <div
              v-if="newField.linkConfig.targetTableId === tableId"
              class="field-hint self-link-hint">
              {{ t('field.selfLinkHint') }}
            </div>
          </ElFormItem>

          <ElFormItem :label="t('field.linkType')" required>
            <ElRadioGroup
              v-model="newField.linkConfig.relationshipType"
              :disabled="newField.linkConfig.targetTableId === tableId">
              <ElRadioButton label="one_to_one">{{ t('field.oneToOne') }}</ElRadioButton>
              <ElRadioButton label="one_to_many">{{ t('field.oneToMany') }}</ElRadioButton>
              <ElRadioButton label="many_to_one">{{ t('field.manyToOne') }}</ElRadioButton>
              <ElRadioButton label="many_to_many">{{ t('field.manyToMany') }}</ElRadioButton>
            </ElRadioGroup>
            <div class="field-hint">
              {{ t('field.relationshipHint') }}
            </div>
          </ElFormItem>

          <ElFormItem :label="t('field.displayField')">
            <ElSelect
              v-model="newField.linkConfig.displayFieldId"
              :placeholder="t('field.selectDisplayFieldPlaceholder')"
              clearable
              style="width: 100%">
              <ElOption
                v-for="field in targetTableFields"
                :key="field.id"
                :label="field.name"
                :value="field.id" />
            </ElSelect>
            <div class="field-hint">
              {{ t('field.displayFieldHint') }}
            </div>
          </ElFormItem>

          <ElFormItem :label="t('field.bidirectional')">
            <ElSwitch v-model="newField.linkConfig.bidirectional" :disabled="newField.linkConfig.targetTableId === tableId" />
            <div class="field-hint">
              {{ t('field.bidirectionalHint') }}
            </div>
          </ElFormItem>

          <!-- 双向关联预览 -->
          <ElFormItem
            v-if="newField.linkConfig.bidirectional && newField.linkConfig.targetTableId"
            :label="t('field.inverseLinkPreview')"
          >
            <div class="inverse-preview">
              <div class="inverse-preview-row">
                <el-icon><Link /></el-icon>
                <span>{{ t('field.inverseLinkPreviewMsg', { table: tableStore.tables.find((t) => t.id === newField.linkConfig.targetTableId)?.name || t('field.targetTable') }) }}</span>
              </div>
              <el-tag size="small" type="success" effect="plain" class="inverse-field-tag">
                <el-icon style="margin-right: 4px; font-size: 12px;"><Link /></el-icon>
                {{ t('field.inverseLinkField', { table: tableStore.tables.find((t) => t.id === tableId)?.name || t('field.currentTable') }) }}
              </el-tag>
            </div>
          </ElFormItem>

          <!-- 关联关系预览 -->
          <ElFormItem v-if="newField.linkConfig.targetTableId" :label="t('field.linkPreview')">
            <div class="link-preview">
              <div class="link-preview-item">
                <span class="link-preview-label">{{ t('field.currentTable') }}:</span>
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
                      ? t('field.oneToOne')
                      : newField.linkConfig.relationshipType === "one_to_many"
                        ? t('field.oneToMany')
                        : t('field.manyToOne')
                  }}
                </span>
              </div>
              <div class="link-preview-item">
                <span class="link-preview-label">{{ t('field.targetTable') }}:</span>
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

        <!-- 查找字段配置 -->
        <template v-if="newField.type === FieldType.LOOKUP">
          <LookupFieldConfigPanel
            :field="{
              id: editingField?.id,
              name: newField.lookupConfig.name || newField.name,
              type: newField.type,
              config: newField.lookupConfig.config,
            }"
            :table-id="tableId"
            :current-table-fields="fields"
            :record-id="previewRecordId"
            @update:field="onLookupConfigUpdate" />
        </template>

        <!-- 必填选项：自动编号、公式、查找、关联等字段不需要必填选项 -->
        <ElFormItem
          v-if="
            newField.type !== FieldType.AUTO_NUMBER &&
            newField.type !== FieldType.FORMULA &&
            newField.type !== FieldType.LOOKUP &&
            newField.type !== FieldType.LINK &&
            newField.type !== FieldType.CREATED_TIME &&
            newField.type !== FieldType.UPDATED_TIME &&
            newField.type !== FieldType.CREATED_BY &&
            newField.type !== FieldType.LAST_MODIFIED_BY
          "
          :label="t('field.required')">
          <ElSwitch v-model="newField.isRequired" />
        </ElFormItem>

        <ElFormItem :label="t('field.mergeCell')">
          <ElSwitch v-model="newField.mergeCell" />
          <div class="field-hint">&nbsp;{{ t('field.mergeCellHint') }}</div>
        </ElFormItem>

        <ElFormItem :label="t('field.fieldDesc')">
          <ElInput
            v-model="newField.description"
            type="textarea"
            :rows="2"
            :placeholder="t('field.fieldDescPlaceholder')" />
        </ElFormItem>

        <!-- 默认值配置：查找字段、公式字段、自动编号、系统字段等不需要默认值 -->
        <ElFormItem
          v-if="
            newField.type !== FieldType.LOOKUP &&
            newField.type !== FieldType.FORMULA &&
            newField.type !== FieldType.AUTO_NUMBER &&
            newField.type !== FieldType.CREATED_TIME &&
            newField.type !== FieldType.UPDATED_TIME &&
            newField.type !== FieldType.CREATED_BY &&
            newField.type !== FieldType.LAST_MODIFIED_BY &&
            newField.type !== FieldType.LINK
          "
          :label="t('field.defaultValue')">
          <!-- 单行文本 -->
          <ElInput
            v-if="newField.type === FieldType.SINGLE_LINE_TEXT"
            v-model="newField.defaultValue"
            :placeholder="t('field.defaultTextPlaceholder')"
            style="width: 100%" />

          <!-- 多行文本 -->
          <ElInput
            v-else-if="newField.type === FieldType.LONG_TEXT"
            v-model="newField.defaultValue"
            type="textarea"
            :rows="3"
            :placeholder="t('field.defaultTextPlaceholder')"
            style="width: 100%" />

          <!-- 富文本 -->
          <ElInput
            v-else-if="newField.type === FieldType.RICH_TEXT"
            v-model="newField.defaultValue"
            type="textarea"
            :rows="3"
            :placeholder="t('field.defaultTextPlaceholder')"
            style="width: 100%" />

          <!-- 数字类型 -->
          <ElInputNumber
            v-else-if="newField.type === FieldType.NUMBER"
            v-model="newField.defaultValue"
            :precision="newField.precision"
            :placeholder="t('field.defaultNumberPlaceholder')"
            style="width: 100%" />

          <!-- 日期类型 -->
          <div v-else-if="newField.type === FieldType.DATE" style="width: 100%">
            <div style="margin-bottom: 8px">
              <el-radio-group v-model="dateDefaultType" size="small">
                <el-radio-button value="">{{ t('field.noDefault') }}</el-radio-button>
                <el-radio-button value="now"
                  >{{ t('field.dateDefaultNow') }}</el-radio-button
                >
                <el-radio-button value="custom">{{ t('field.dateDefaultCustom') }}</el-radio-button>
              </el-radio-group>
            </div>
            <el-date-picker
              v-if="dateDefaultType === 'custom'"
              v-model="newField.defaultValue"
              type="date"
              format="YYYY-MM-DD"
              :placeholder="t('field.defaultDatePlaceholder')"
              style="width: 100%" />
          </div>

          <!-- 日期时间类型 -->
          <div v-else-if="newField.type === FieldType.DATE_TIME" style="width: 100%">
            <div style="margin-bottom: 8px">
              <el-radio-group v-model="dateDefaultType" size="small">
                <el-radio-button value="">{{ t('field.noDefault') }}</el-radio-button>
                <el-radio-button value="now"
                  >{{ t('field.dateTimeDefaultNow') }}</el-radio-button
                >
                <el-radio-button value="custom">{{ t('field.dateTimeDefaultCustom') }}</el-radio-button>
              </el-radio-group>
            </div>
            <el-date-picker
              v-if="dateDefaultType === 'custom'"
              v-model="newField.defaultValue"
              type="datetime"
              format="YYYY-MM-DD HH:mm:ss"
              :placeholder="t('field.defaultDateTimePlaceholder')"
              style="width: 100%" />
          </div>

          <!-- 单选类型 -->
          <ElSelect
            v-else-if="newField.type === FieldType.SINGLE_SELECT"
            v-model="newField.defaultValue"
            :placeholder="t('field.defaultOptionPlaceholder')"
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
            :placeholder="t('field.defaultOptionPlaceholder')"
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
            :active-text="t('field.checked')"
            :inactive-text="t('field.unchecked')" />

          <!-- 成员类型 -->
          <div v-else-if="newField.type === FieldType.MEMBER" style="width: 100%">
            <div style="margin-bottom: 8px">
              <el-radio-group v-model="memberConfig.defaultType" size="small" @change="(val: string | number | boolean | undefined) => {
                if (val === 'none') {
                  newField.defaultValue = undefined;
                } else if (val === 'current_user') {
                  newField.defaultValue = 'current_user';
                } else if (val === 'specific_user') {
                  newField.defaultValue = memberConfig.defaultUser?.id;
                }
              }">
                <el-radio-button value="none">{{ t('field.noDefault') }}</el-radio-button>
                <el-radio-button value="current_user">{{ t('field.memberDefaultCurrentUser') }}</el-radio-button>
                <el-radio-button value="specific_user">{{ t('field.memberDefaultSpecificUser') }}</el-radio-button>
              </el-radio-group>
            </div>
            <!-- 指定用户选择 -->
            <div v-show="memberConfig.defaultType === 'specific_user'" class="member-default-select" @click.stop>
              <MemberSelect
                v-model="memberConfig.defaultUser"
                :placeholder="t('field.memberDefaultPlaceholder')"
                :allow-multiple="false"
                :return-object="true"
                @update:model-value="(val: any) => {
                  if (val) {
                    memberConfig.defaultUser = val;
                    newField.defaultValue = val.id;
                  } else {
                    memberConfig.defaultUser = null;
                    newField.defaultValue = undefined;
                  }
                }" />
            </div>
          </div>

          <ElTag
            v-if="
              newField.defaultValue !== undefined &&
              newField.defaultValue !== null &&
              newField.type !== FieldType.MEMBER
            "
            type="success"
            size="small"
            style="margin-left: 8px">
            {{ t('field.configured') }}
          </ElTag>
          <ElTag
            v-if="
              newField.type === FieldType.MEMBER &&
              memberConfig.defaultType !== 'none'
            "
            type="success"
            size="small"
            style="margin-left: 8px">
            {{ t('field.configured') }}
          </ElTag>
          <div class="field-hint">{{ t('field.defaultValueHint') }}</div>
        </ElFormItem>
      </ElForm>

      <div class="form-actions">
        <ElButton @click="backToList">{{ t('common.back') }}</ElButton>
        <ElButton
          type="primary"
          @click="activeTab === 'create' ? createField() : updateField()">
          {{ activeTab === "create" ? t('common.create') : t('common.save') }}
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

      .drag-handle:not(.disabled) {
        opacity: 1;
      }
    }

    &.is-system {
      opacity: 0.7;
    }

    &.is-primary-field {
      background-color: rgba(16, 185, 129, 0.05);
      border: 1px solid rgba(16, 185, 129, 0.2);

      &:hover {
        background-color: rgba(16, 185, 129, 0.1);
      }

      .field-name {
        font-weight: 600;
        color: #10b981;
      }
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

        &.disabled {
          opacity: 0.3 !important;
          cursor: not-allowed;
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

.field-reorder-warning {
  font-weight: 500;
  
  .el-message__content {
    font-size: 14px;
  }
}

.primary-field-tooltip {
  font-size: 13px;
  line-height: 1.5;
  max-width: 280px;
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

  .self-link-hint {
    color: var(--el-color-primary);
    font-weight: 500;
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

  // 反向关联预览样式
  .inverse-preview {
    display: flex;
    flex-direction: column;
    gap: 8px;
    padding: 12px;
    background-color: rgba(16, 185, 129, 0.04);
    border-radius: $border-radius-md;
    border: 1px solid rgba(16, 185, 129, 0.15);

    .inverse-preview-row {
      display: flex;
      align-items: center;
      gap: 6px;
      font-size: $font-size-sm;
      color: $text-secondary;
      line-height: 1.5;

      b {
        color: $text-primary;
      }
    }

    .inverse-field-tag {
      width: fit-content;
    }
  }
}
</style>
