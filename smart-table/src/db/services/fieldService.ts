import { db } from '../schema';
import type { FieldEntity } from '../schema';
import { generateId } from '../../utils/id';
import type { CellValue, FieldOptions } from '../../types';

export interface CreateFieldData {
  tableId: string;
  name: string;
  type: string;
  options?: FieldOptions;
  isRequired?: boolean;
  defaultValue?: CellValue;
  description?: string;
}

export class FieldService {
  async createField(data: CreateFieldData): Promise<FieldEntity> {
    const fields = await db.fields.where('tableId').equals(data.tableId).toArray();
    const maxOrder = fields.length > 0 ? Math.max(...fields.map(f => f.order)) : -1;

    const field: FieldEntity = {
      id: generateId(),
      tableId: data.tableId,
      name: data.name,
      type: data.type,
      options: data.options as Record<string, unknown> | undefined,
      isPrimary: false,
      isSystem: false,
      isRequired: data.isRequired ?? false,
      defaultValue: data.defaultValue,
      description: data.description,
      order: maxOrder + 1,
      createdAt: Date.now(),
      updatedAt: Date.now()
    };

    await db.fields.add(field);
    return field;
  }

  async getField(id: string): Promise<FieldEntity | undefined> {
    return db.fields.get(id);
  }

  async getFieldsByTable(tableId: string): Promise<FieldEntity[]> {
    return db.fields.where('tableId').equals(tableId).sortBy('order');
  }

  async updateField(id: string, changes: Partial<FieldEntity>): Promise<void> {
    await db.fields.update(id, {
      ...changes,
      updatedAt: Date.now()
    });
  }

  async updateFieldOptions(id: string, options: FieldOptions): Promise<void> {
    await db.fields.update(id, {
      options: options as Record<string, unknown>,
      updatedAt: Date.now()
    });
  }

  async deleteField(id: string): Promise<void> {
    const field = await this.getField(id);
    if (!field) return;

    if (field.isSystem) {
      throw new Error('Cannot delete system field');
    }

    await db.transaction('rw', [db.fields, db.records], async () => {
      const records = await db.records.where('tableId').equals(field.tableId).toArray();
      for (const record of records) {
        const newValues = { ...record.values };
        delete newValues[id];
        await db.records.update(record.id, { values: newValues });
      }
      await db.fields.delete(id);
    });
  }

  async reorderFields(_tableId: string, fieldIds: string[]): Promise<void> {
    await db.transaction('rw', db.fields, async () => {
      for (let i = 0; i < fieldIds.length; i++) {
        await db.fields.update(fieldIds[i], { order: i });
      }
    });
  }

  async addFieldOption(fieldId: string, option: { id: string; name: string; color: string }): Promise<void> {
    const field = await this.getField(fieldId);
    if (!field) return;

    const options = (field.options?.options as Array<{ id: string; name: string; color: string }>) || [];
    await this.updateFieldOptions(fieldId, {
      ...field.options as FieldOptions,
      options: [...options, option]
    });
  }

  async removeFieldOption(fieldId: string, optionId: string): Promise<void> {
    const field = await this.getField(fieldId);
    if (!field) return;

    const options = (field.options?.options as Array<{ id: string; name: string; color: string }>) || [];
    await this.updateFieldOptions(fieldId, {
      ...field.options as FieldOptions,
      options: options.filter(opt => opt.id !== optionId)
    });
  }
}

export const fieldService = new FieldService();
