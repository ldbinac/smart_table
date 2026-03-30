export { baseService, BaseService, type CreateBaseData } from './baseService';
export { tableService, TableService, type CreateTableData } from './tableService';
export {
  fieldService,
  FieldService,
  type CreateFieldData,
  type LinkFieldConfig,
  type LookupFieldConfig
} from './fieldService';
export { recordService, RecordService, type CreateRecordData, type UpdateRecordData } from './recordService';
export { viewService, ViewService, type CreateViewData, type UpdateViewData } from './viewService';
export { dashboardService, DashboardService, type CreateDashboardData, type WidgetConfig } from './dashboardService';
export { dashboardShareService, DashboardShareService, type CreateShareData, type ShareValidationResult } from './dashboardShareService';
export { dashboardTemplateService, DashboardTemplateService, type CreateTemplateData, type TemplateFilter } from './dashboardTemplateService';
export { dashboardRealtimeService, DashboardRealtimeService, type RefreshConfig, type DataChangeEvent, type WidgetDataState } from './dashboardRealtimeService';
export { templateService, TemplateService } from './templateService';
