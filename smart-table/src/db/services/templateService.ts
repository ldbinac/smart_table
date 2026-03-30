import { db } from '../schema';
import type { Base } from '../schema';
import { baseService } from './baseService';
// import { tableService } from './tableService';
// import { fieldService } from './fieldService';
// import { viewService } from './viewService';
import { recordService } from './recordService';
import type { TableTemplate, TemplateTable, TemplateRecord } from '../../utils/tableTemplates';
import { generateId } from '../../utils/id';

export class TemplateService {
  async createBaseFromTemplate(template: TableTemplate): Promise<Base> {
    return await db.transaction(
      'rw',
      [db.bases, db.tableEntities, db.fields, db.views, db.records],
      async () => {
        const base = await baseService.createBase({
          name: template.name,
          description: template.description,
          icon: template.icon,
          color: template.color
        });

        const tableIdMap = new Map<string, string>();
        const fieldIdMap = new Map<string, string>();

        for (const templateTable of template.tables) {
          const createdTable = await this.createTableFromTemplate(base.id, templateTable, tableIdMap, fieldIdMap);
          tableIdMap.set(templateTable.id, createdTable.id);
        }

        for (const templateTable of template.tables) {
          await this.createRecordsFromTemplate(
            tableIdMap.get(templateTable.id)!,
            templateTable.records,
            fieldIdMap
          );
        }

        return base;
      }
    );
  }

  private async createTableFromTemplate(
    baseId: string,
    templateTable: TemplateTable,
    _tableIdMap: Map<string, string>,
    fieldIdMap: Map<string, string>
  ) {
    const tables = await db.tableEntities.where('baseId').equals(baseId).toArray();
    const maxOrder = tables.length > 0 ? Math.max(...tables.map((t) => t.order)) : -1;

    let primaryFieldId: string | null = null;
    const primaryTemplateField = templateTable.fields.find(f => f.isPrimary);
    if (primaryTemplateField) {
      primaryFieldId = generateId();
      fieldIdMap.set(primaryTemplateField.id, primaryFieldId);
    }

    const table = {
      id: generateId(),
      baseId,
      name: templateTable.name,
      description: templateTable.description,
      primaryFieldId: primaryFieldId || generateId(),
      recordCount: 0,
      order: maxOrder + 1,
      isStarred: false,
      createdAt: Date.now(),
      updatedAt: Date.now()
    };

    await db.tableEntities.add(table);

    for (const templateField of templateTable.fields) {
      let newFieldId = fieldIdMap.get(templateField.id);
      if (!newFieldId) {
        newFieldId = generateId();
        fieldIdMap.set(templateField.id, newFieldId);
      }

      const field = {
        id: newFieldId,
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
        updatedAt: Date.now()
      };

      await db.fields.add(field);
    }

    for (const templateView of templateTable.views) {
      const view = {
        id: generateId(),
        tableId: table.id,
        name: templateView.name,
        type: templateView.type,
        config: templateView.config,
        filters: templateView.filters,
        sorts: templateView.sorts,
        groupBys: templateView.groupBys,
        hiddenFields: templateView.hiddenFields.map(oldId => fieldIdMap.get(oldId) || oldId),
        frozenFields: templateView.frozenFields.map(oldId => fieldIdMap.get(oldId) || oldId),
        rowHeight: templateView.rowHeight,
        isDefault: templateView.isDefault,
        order: templateView.order,
        createdAt: Date.now(),
        updatedAt: Date.now()
      };

      if (view.config && (view.type === 'gantt' || view.type === 'kanban' || view.type === 'calendar')) {
        const config = view.config as Record<string, unknown>;
        if (config.startDateFieldId && fieldIdMap.has(config.startDateFieldId as string)) {
          config.startDateFieldId = fieldIdMap.get(config.startDateFieldId as string);
        }
        if (config.endDateFieldId && fieldIdMap.has(config.endDateFieldId as string)) {
          config.endDateFieldId = fieldIdMap.get(config.endDateFieldId as string);
        }
        if (config.progressFieldId && fieldIdMap.has(config.progressFieldId as string)) {
          config.progressFieldId = fieldIdMap.get(config.progressFieldId as string);
        }
        if (config.groupFieldId && fieldIdMap.has(config.groupFieldId as string)) {
          config.groupFieldId = fieldIdMap.get(config.groupFieldId as string);
        }
        if (config.dateFieldId && fieldIdMap.has(config.dateFieldId as string)) {
          config.dateFieldId = fieldIdMap.get(config.dateFieldId as string);
        }
      }

      await db.views.add(view as unknown as import('../schema').ViewEntity);
    }

    return table;
  }

  private async createRecordsFromTemplate(
    tableId: string,
    records: TemplateRecord[],
    fieldIdMap: Map<string, string>
  ) {
    for (const templateRecord of records) {
      const newValues: Record<string, unknown> = {};
      for (const [oldFieldId, value] of Object.entries(templateRecord.values)) {
        const newFieldId = fieldIdMap.get(oldFieldId);
        if (newFieldId) {
          newValues[newFieldId] = value;
        }
      }

      await recordService.createRecord({
        tableId,
        values: newValues as Record<string, import('../../types').CellValue>
      });
    }
  }
}

export const templateService = new TemplateService();
