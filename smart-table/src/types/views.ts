export const ViewType = {
  TABLE: "table",
  KANBAN: "kanban",
  CALENDAR: "calendar",
  GANTT: "gantt",
  FORM: "form",
  GALLERY: "gallery",
} as const;

export type ViewTypeValue = (typeof ViewType)[keyof typeof ViewType];

export type RowHeight = "short" | "medium" | "tall";

export interface ViewTableConfig {
  showGrid?: boolean;
  stripe?: boolean;
}

export interface ViewKanbanConfig {
  groupFieldId?: string;
  cardFields?: string[];
  coverFieldId?: string;
}

export interface ViewCalendarConfig {
  dateFieldId?: string;
  endDateFieldId?: string;
  defaultView?: "day" | "week" | "month";
}

export interface ViewGanttConfig {
  startDateFieldId?: string;
  endDateFieldId?: string;
  durationFieldId?: string;
  progressFieldId?: string;
}

export interface ViewFormConfig {
  fields?: string[];
  title?: string;
  description?: string;
  submitButtonText?: string;
  visibleFieldIds?: string[];
  successMessage?: string;
  allowMultipleSubmit?: boolean;
}

export interface ViewGalleryConfig {
  imageFieldId?: string;
  titleFieldId?: string;
}

export type ViewConfig =
  | ViewTableConfig
  | ViewKanbanConfig
  | ViewCalendarConfig
  | ViewGanttConfig
  | ViewFormConfig
  | ViewGalleryConfig
  | Record<string, unknown>;

export interface View {
  id: string;
  tableId: string;
  name: string;
  type: ViewTypeValue;
  config: ViewConfig;
  filters: import("./filters").FilterCondition[];
  sorts: import("./filters").SortConfig[];
  groupBys: string[];
  hiddenFields: string[];
  frozenFields: string[];
  rowHeight: RowHeight;
  isDefault: boolean;
  order: number;
  createdAt: number;
  updatedAt: number;
}
