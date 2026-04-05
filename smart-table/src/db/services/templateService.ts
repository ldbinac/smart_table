import { db } from "../schema";
import type { Base } from "../schema";
import { baseService } from "./baseService";
import { tableService } from "./tableService";
import { fieldService } from "./fieldService";
import { viewService } from "./viewService";
import { recordService } from "./recordService";
import type {
  TableTemplate,
  TemplateTable,
  TemplateRecord,
} from "../../utils/tableTemplates";
import { generateId } from "../../utils/id";
import { baseApiService } from "@/services/api/baseApiService";
import { tableApiService } from "@/services/api/tableApiService";
import { fieldApiService } from "@/services/api/fieldApiService";
import { viewApiService } from "@/services/api/viewApiService";
import { recordApiService } from "@/services/api/recordApiService";

export interface CreateTemplateProgress {
  stage:
    | "creating_base"
    | "creating_tables"
    | "creating_fields"
    | "creating_views"
    | "creating_records"
    | "syncing_to_backend"
    | "completed";
  message: string;
  progress: number; // 0-100
}

export class TemplateService {
  async createBaseFromTemplate(
    template: TableTemplate,
    onProgress?: (progress: CreateTemplateProgress) => void,
  ): Promise<Base> {
    let createdBase: Base | undefined;
    const progress: CreateTemplateProgress = {
      stage: "creating_base",
      message: "正在创建多维表...",
      progress: 0,
    };

    try {
      // 第一阶段：创建到后端
      progress.stage = "creating_base";
      progress.message = "正在创建多维表基础结构...";
      progress.progress = 10;
      onProgress?.({ ...progress });

      // 1. 在后端创建 Base
      const apiBase = await baseApiService.createBase({
        name: template.name,
        description: template.description,
        icon: template.icon,
        color: template.color,
      });

      // 2. 同步 Tables 和 Fields
      progress.stage = "creating_tables";
      progress.message = "正在创建数据表和字段...";
      progress.progress = 30;
      onProgress?.({ ...progress });

      const tableIdMap = new Map<string, string>();
      const fieldIdMap = new Map<string, string>();

      for (const templateTable of template.tables) {
        const apiTable = await this.syncTableToBackend(
          apiBase.id,
          templateTable,
          fieldIdMap,
        );
        tableIdMap.set(templateTable.id, apiTable.id);
      }

      // 3. 同步 Views
      progress.stage = "creating_views";
      progress.message = "正在创建视图...";
      progress.progress = 60;
      onProgress?.({ ...progress });

      for (const templateTable of template.tables) {
        await this.syncViewsToBackend(
          tableIdMap.get(templateTable.id)!,
          templateTable,
          fieldIdMap,
        );
      }

      // 4. 同步 Records
      progress.stage = "creating_records";
      progress.message = "正在导入初始数据...";
      progress.progress = 80;
      onProgress?.({ ...progress });

      for (const templateTable of template.tables) {
        await this.syncRecordsToBackend(
          tableIdMap.get(templateTable.id)!,
          templateTable.records,
          fieldIdMap,
        );
      }

      // 第二阶段：保存到 IndexedDB（后端创建成功后）
      progress.stage = "syncing_to_backend";
      progress.message = "正在保存到本地...";
      progress.progress = 90;
      onProgress?.({ ...progress });

      // 保存到 IndexedDB
      await db.transaction(
        "rw",
        [db.bases, db.tableEntities, db.fields, db.views, db.records],
        async () => {
          // 1. 保存 Base
          const localBase = {
            id: apiBase.id,
            name: apiBase.name,
            description: apiBase.description || "",
            icon: apiBase.icon || "",
            color: apiBase.color || "#409EFF",
            isStarred: apiBase.is_starred || false,
            createdAt: new Date(apiBase.created_at).getTime(),
            updatedAt: new Date(apiBase.updated_at).getTime(),
          };
          await db.bases.add(localBase);
          createdBase = localBase;

          // 2. 保存 Tables 和 Fields
          for (const templateTable of template.tables) {
            const apiTableId = tableIdMap.get(templateTable.id)!;
            await this.saveTableToLocal(
              apiBase.id,
              apiTableId,
              templateTable,
              fieldIdMap,
            );
          }

          // 3. 保存 Views
          for (const templateTable of template.tables) {
            const apiTableId = tableIdMap.get(templateTable.id)!;
            await this.saveViewsToLocal(apiTableId, templateTable, fieldIdMap);
          }

          // 4. 保存 Records
          for (const templateTable of template.tables) {
            const apiTableId = tableIdMap.get(templateTable.id)!;
            await this.saveRecordsToLocal(
              apiTableId,
              templateTable.records,
              fieldIdMap,
            );
          }
        },
      );

      progress.stage = "completed";
      progress.message = "创建完成！";
      progress.progress = 100;
      onProgress?.({ ...progress });

      if (!createdBase) {
        throw new Error("Failed to create base from template");
      }

      return { ...createdBase };
    } catch (error) {
      console.error("[templateService] 创建模板失败:", error);
      throw error;
    }
  }

  /**
   * 保存 Table 到 IndexedDB
   */
  private async saveTableToLocal(
    baseId: string,
    tableId: string,
    templateTable: TemplateTable,
    fieldIdMap: Map<string, string>,
  ): Promise<void> {
    const table = {
      id: tableId,
      baseId,
      name: templateTable.name,
      description: templateTable.description || "",
      primaryFieldId:
        fieldIdMap.get(
          templateTable.fields.find((f) => f.isPrimary)?.id || "",
        ) || null,
      recordCount: 0,
      order: templateTable.order || 0,
      isStarred: false,
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };

    await db.tableEntities.add(table);

    // 保存 Fields
    for (const templateField of templateTable.fields) {
      const fieldId = fieldIdMap.get(templateField.id);
      if (!fieldId) continue;

      const field = {
        id: fieldId,
        tableId: table.id,
        name: templateField.name,
        type: templateField.type,
        options: templateField.options as Record<string, unknown> | undefined,
        isPrimary: templateField.isPrimary,
        isSystem: false,
        isRequired: templateField.isRequired,
        isVisible: templateField.isVisible,
        defaultValue: templateField.defaultValue,
        description: templateField.description,
        order: templateField.order,
        createdAt: Date.now(),
        updatedAt: Date.now(),
      };

      await db.fields.add(field);
    }
  }

  /**
   * 保存 Views 到 IndexedDB
   */
  private async saveViewsToLocal(
    tableId: string,
    templateTable: TemplateTable,
    fieldIdMap: Map<string, string>,
  ): Promise<void> {
    for (const templateView of templateTable.views) {
      const view = {
        id: generateId(),
        tableId: tableId,
        name: templateView.name,
        type: templateView.type,
        config: templateView.config,
        filters: templateView.filters,
        sorts: templateView.sorts,
        groupBys: templateView.groupBys,
        hiddenFields: templateView.hiddenFields.map(
          (oldId) => fieldIdMap.get(oldId) || oldId,
        ),
        frozenFields: templateView.frozenFields.map(
          (oldId) => fieldIdMap.get(oldId) || oldId,
        ),
        rowHeight: templateView.rowHeight,
        isDefault: templateView.isDefault,
        order: templateView.order,
        createdAt: Date.now(),
        updatedAt: Date.now(),
      };

      if (
        view.config &&
        (view.type === "gantt" ||
          view.type === "kanban" ||
          view.type === "calendar")
      ) {
        const config = view.config as Record<string, unknown>;
        if (
          config.startDateFieldId &&
          fieldIdMap.has(config.startDateFieldId as string)
        ) {
          config.startDateFieldId = fieldIdMap.get(
            config.startDateFieldId as string,
          );
        }
        if (
          config.endDateFieldId &&
          fieldIdMap.has(config.endDateFieldId as string)
        ) {
          config.endDateFieldId = fieldIdMap.get(
            config.endDateFieldId as string,
          );
        }
        if (
          config.progressFieldId &&
          fieldIdMap.has(config.progressFieldId as string)
        ) {
          config.progressFieldId = fieldIdMap.get(
            config.progressFieldId as string,
          );
        }
        if (
          config.groupFieldId &&
          fieldIdMap.has(config.groupFieldId as string)
        ) {
          config.groupFieldId = fieldIdMap.get(config.groupFieldId as string);
        }
        if (
          config.dateFieldId &&
          fieldIdMap.has(config.dateFieldId as string)
        ) {
          config.dateFieldId = fieldIdMap.get(config.dateFieldId as string);
        }
      }

      await db.views.add(view as unknown as import("../schema").ViewEntity);
    }
  }

  /**
   * 保存 Records 到 IndexedDB
   */
  private async saveRecordsToLocal(
    tableId: string,
    records: TemplateRecord[],
    fieldIdMap: Map<string, string>,
  ): Promise<void> {
    for (const templateRecord of records) {
      const newValues: Record<string, unknown> = {};
      for (const [oldFieldId, value] of Object.entries(templateRecord.values)) {
        const newFieldId = fieldIdMap.get(oldFieldId);
        if (newFieldId) {
          newValues[newFieldId] = value;
        }
      }

      const localRecord = {
        id: generateId(),
        tableId,
        values: newValues as Record<string, import("../../types").CellValue>,
        createdAt: Date.now(),
        updatedAt: Date.now(),
        createdBy: undefined,
        updatedBy: undefined,
      };

      await db.records.add(
        localRecord as unknown as import("../schema").RecordEntity,
      );
    }
  }

  /**
   * 同步数据到后端（已废弃，现在直接在 createBaseFromTemplate 中实现）
   * @deprecated
   */
  private async syncToBackend(
    template: TableTemplate,
    localBase: Base,
  ): Promise<void> {
    // 此方法已不再使用，保留仅为了兼容性
    console.warn("[templateService] syncToBackend 方法已废弃");
  }

  private async syncTableToBackend(
    baseId: string,
    templateTable: TemplateTable,
    fieldIdMap: Map<string, string>,
  ): Promise<any> {
    // 1. 先创建 Table（不指定主字段）
    const apiTable = await tableApiService.createTable(baseId, {
      name: templateTable.name,
      description: templateTable.description,
    });

    // 2. 创建所有字段（包括主字段），并映射类型
    for (const templateField of templateTable.fields) {
      // 映射前端类型到后端类型
      const fieldTypeMap: Record<string, string> = {
        text: "single_line_text",
        member: "collaborator",
        progress: "number",
        created_time: "date_time",
        updated_time: "date_time",
      };

      const backendType =
        fieldTypeMap[templateField.type] || templateField.type;

      // 转换选项格式：前端使用 options.options，后端期望 options.choices
      let backendOptions = templateField.options;
      if (
        backendOptions &&
        (backendType === "single_select" || backendType === "multi_select")
      ) {
        const frontendOptions = (backendOptions as any).options;
        if (Array.isArray(frontendOptions)) {
          backendOptions = {
            choices: frontendOptions.map((opt: any) => ({
              id: opt.id,
              name: opt.name,
              color: opt.color,
            })),
          };
        }
      }

      const apiField = await fieldApiService.createField(apiTable.id, {
        name: templateField.name,
        type: backendType as any,
        options: backendOptions,
        isPrimary: templateField.isPrimary,
        isRequired: templateField.isRequired,
      });
      fieldIdMap.set(templateField.id, apiField.id);
    }

    return apiTable;
  }

  private async syncViewsToBackend(
    tableId: string,
    templateTable: TemplateTable,
    fieldIdMap: Map<string, string>,
  ): Promise<void> {
    for (const templateView of templateTable.views) {
      // 传递完整的视图字段参数
      const viewData: any = {
        name: templateView.name,
        type: templateView.type,
        config: templateView.config || {},
        filters: templateView.filters || [],
        sorts: templateView.sorts || [],
        group_bys: templateView.groupBys || [], // 使用下划线格式
        description: templateView.description || "",
        hidden_fields: templateView.hiddenFields.map(
          (oldId) => fieldIdMap.get(oldId) || oldId,
        ),
        frozen_fields: templateView.frozenFields.map(
          (oldId) => fieldIdMap.get(oldId) || oldId,
        ),
        row_height: templateView.rowHeight || "medium",
        is_default: templateView.isDefault || false,
        field_widths: templateView.fieldWidths || {},
        order: templateView.order || 0,
      };

      await viewApiService.createView(tableId, viewData);
    }
  }

  private async syncRecordsToBackend(
    tableId: string,
    records: TemplateRecord[],
    fieldIdMap: Map<string, string>,
  ): Promise<void> {
    // 批量创建记录（每次最多 100 条）
    const batchSize = 100;
    for (let i = 0; i < records.length; i += batchSize) {
      const batch = records.slice(i, i + batchSize);
      const recordsData = batch.map((templateRecord) => {
        const newValues: Record<string, unknown> = {};
        for (const [oldFieldId, value] of Object.entries(
          templateRecord.values,
        )) {
          const newFieldId = fieldIdMap.get(oldFieldId);
          if (newFieldId) {
            newValues[newFieldId] = value;
          }
        }
        return { values: newValues };
      });

      await recordApiService.batchCreateRecords(tableId, recordsData);
    }
  }
}

export const templateService = new TemplateService();
