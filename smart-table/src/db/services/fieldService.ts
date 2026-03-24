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

export interface LinkFieldConfig {
  linkedTableId: string;
  linkedFieldId?: string;
  displayFieldId?: string;
  allowMultiple?: boolean;
  relationshipType?: 'oneToOne' | 'oneToMany' | 'manyToMany';
  bidirectional?: boolean;
  inverseFieldId?: string;
}

export interface LookupFieldConfig {
  linkedTableId: string;
  linkedFieldId: string;
  lookupFieldId: string;
  aggregationType?: 'single' | 'concat' | 'sum' | 'avg' | 'min' | 'max' | 'count';
  separator?: string;
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

  // ==================== 关联字段 (Link Field) 方法 ====================

  /**
   * 创建关联字段配置
   */
  async configureLinkField(
    fieldId: string,
    config: LinkFieldConfig
  ): Promise<void> {
    const field = await this.getField(fieldId);
    if (!field) {
      throw new Error('Field not found');
    }

    if (field.type !== 'link') {
      throw new Error('Field is not a link field');
    }

    const updatedOptions: FieldOptions = {
      ...field.options,
      linkedTableId: config.linkedTableId,
      linkedFieldId: config.linkedFieldId,
      displayFieldId: config.displayFieldId,
      allowMultiple: config.allowMultiple ?? false,
      relationshipType: config.relationshipType ?? 'oneToMany',
      bidirectional: config.bidirectional ?? false,
      inverseFieldId: config.inverseFieldId
    };

    await this.updateFieldOptions(fieldId, updatedOptions);

    // 如果是双向关联，创建反向关联字段
    if (config.bidirectional && config.inverseFieldId) {
      await this.createInverseLinkField(fieldId, config);
    }
  }

  /**
   * 创建反向关联字段（用于双向关联）
   */
  private async createInverseLinkField(
    sourceFieldId: string,
    config: LinkFieldConfig
  ): Promise<void> {
    if (!config.inverseFieldId || !config.linkedTableId) return;

    const sourceField = await this.getField(sourceFieldId);
    if (!sourceField) return;

    const sourceTable = await db.tableEntities.get(sourceField.tableId);
    if (!sourceTable) return;

    // 检查反向字段是否已存在
    const existingField = await this.getField(config.inverseFieldId);
    if (existingField) return;

    // 创建反向关联字段
    const inverseField: FieldEntity = {
      id: config.inverseFieldId,
      tableId: config.linkedTableId,
      name: `${sourceTable.name}关联`,
      type: 'link',
      options: {
        linkedTableId: sourceField.tableId,
        linkedFieldId: sourceFieldId,
        allowMultiple: config.relationshipType === 'manyToMany' || config.relationshipType === 'oneToMany',
        relationshipType: this.getInverseRelationshipType(config.relationshipType),
        bidirectional: true,
        inverseFieldId: sourceFieldId
      },
      isPrimary: false,
      isSystem: false,
      isRequired: false,
      order: await this.getNextFieldOrder(config.linkedTableId),
      createdAt: Date.now(),
      updatedAt: Date.now()
    };

    await db.fields.add(inverseField);
  }

  /**
   * 获取反向关联类型
   */
  private getInverseRelationshipType(
    type?: 'oneToOne' | 'oneToMany' | 'manyToMany'
  ): 'oneToOne' | 'oneToMany' | 'manyToMany' {
    switch (type) {
      case 'oneToMany':
        return 'manyToMany';
      case 'manyToMany':
        return 'manyToMany';
      case 'oneToOne':
        return 'oneToOne';
      default:
        return 'oneToMany';
    }
  }

  /**
   * 获取关联字段的目标表 ID
   */
  async getLinkedTableId(fieldId: string): Promise<string | undefined> {
    const field = await this.getField(fieldId);
    if (!field || field.type !== 'link') return undefined;
    return field.options?.linkedTableId as string;
  }

  /**
   * 获取关联字段配置
   */
  async getLinkFieldConfig(fieldId: string): Promise<LinkFieldConfig | null> {
    const field = await this.getField(fieldId);
    if (!field || field.type !== 'link') return null;

    return {
      linkedTableId: field.options?.linkedTableId as string,
      linkedFieldId: field.options?.linkedFieldId as string,
      displayFieldId: field.options?.displayFieldId as string,
      allowMultiple: field.options?.allowMultiple as boolean,
      relationshipType: field.options?.relationshipType as 'oneToOne' | 'oneToMany' | 'manyToMany',
      bidirectional: field.options?.bidirectional as boolean,
      inverseFieldId: field.options?.inverseFieldId as string
    };
  }

  /**
   * 更新关联字段的关联记录
   */
  async updateLinkFieldValue(
    recordId: string,
    fieldId: string,
    linkedRecordIds: string | string[] | null
  ): Promise<void> {
    const field = await this.getField(fieldId);
    if (!field || field.type !== 'link') {
      throw new Error('Invalid link field');
    }

    const record = await db.records.get(recordId);
    if (!record) {
      throw new Error('Record not found');
    }

    const config = await this.getLinkFieldConfig(fieldId);
    if (!config) {
      throw new Error('Link field configuration not found');
    }

    // 标准化值为数组
    const normalizedValue = linkedRecordIds
      ? Array.isArray(linkedRecordIds)
        ? linkedRecordIds
        : [linkedRecordIds]
      : [];

    // 更新当前记录的字段值
    const newValues = { ...record.values };
    newValues[fieldId] = config.allowMultiple ? normalizedValue : (normalizedValue[0] || null);

    await db.records.update(recordId, {
      values: newValues,
      updatedAt: Date.now()
    });

    // 如果是双向关联，更新反向关联字段
    if (config.bidirectional && config.inverseFieldId) {
      await this.updateInverseLinkValues(
        recordId,
        normalizedValue,
        config.inverseFieldId,
        config.linkedTableId
      );
    }
  }

  /**
   * 更新反向关联字段的值
   */
  private async updateInverseLinkValues(
    sourceRecordId: string,
    targetRecordIds: string[],
    inverseFieldId: string,
    targetTableId: string
  ): Promise<void> {
    // 获取目标表的所有记录
    const targetRecords = await db.records.where('tableId').equals(targetTableId).toArray();

    for (const targetRecord of targetRecords) {
      const currentValue = targetRecord.values[inverseFieldId];
      let linkedIds: string[] = [];

      if (Array.isArray(currentValue)) {
        linkedIds = currentValue as string[];
      } else if (currentValue) {
        linkedIds = [currentValue as string];
      }

      const isNowLinked = targetRecordIds.includes(targetRecord.id);
      const wasLinked = linkedIds.includes(sourceRecordId);

      let newLinkedIds = [...linkedIds];

      if (isNowLinked && !wasLinked) {
        // 添加关联
        newLinkedIds.push(sourceRecordId);
      } else if (!isNowLinked && wasLinked) {
        // 移除关联
        newLinkedIds = newLinkedIds.filter(id => id !== sourceRecordId);
      }

      // 只有当值发生变化时才更新
      if (JSON.stringify(linkedIds) !== JSON.stringify(newLinkedIds)) {
        const newValues = { ...targetRecord.values };
        const inverseField = await this.getField(inverseFieldId);
        const allowMultiple = inverseField?.options?.allowMultiple as boolean;
        newValues[inverseFieldId] = allowMultiple ? newLinkedIds : (newLinkedIds[0] || null);

        await db.records.update(targetRecord.id, {
          values: newValues,
          updatedAt: Date.now()
        });
      }
    }
  }

  /**
   * 获取关联记录的值（用于查找字段）
   */
  async getLinkedRecordValues(
    recordId: string,
    linkFieldId: string
  ): Promise<Record<string, CellValue>[]> {
    const field = await this.getField(linkFieldId);
    if (!field || field.type !== 'link') {
      return [];
    }

    const record = await db.records.get(recordId);
    if (!record) return [];

    const linkedIds = record.values[linkFieldId];
    if (!linkedIds) return [];

    const ids = Array.isArray(linkedIds) ? linkedIds : [linkedIds];

    const linkedRecords = await db.records.where('id').anyOf(ids as string[]).toArray();
    return linkedRecords.map(r => ({
      id: r.id,
      ...r.values
    }));
  }

  // ==================== 查找字段 (Lookup Field) 方法 ====================

  /**
   * 配置查找字段
   */
  async configureLookupField(
    fieldId: string,
    config: LookupFieldConfig
  ): Promise<void> {
    const field = await this.getField(fieldId);
    if (!field) {
      throw new Error('Field not found');
    }

    if (field.type !== 'lookup') {
      throw new Error('Field is not a lookup field');
    }

    const updatedOptions: FieldOptions = {
      ...field.options,
      linkedTableId: config.linkedTableId,
      linkedFieldId: config.linkedFieldId,
      lookupFieldId: config.lookupFieldId,
      aggregationType: config.aggregationType ?? 'single',
      separator: config.separator ?? ', '
    };

    await this.updateFieldOptions(fieldId, updatedOptions);
  }

  /**
   * 计算查找字段的值
   */
  async calculateLookupValue(
    recordId: string,
    lookupFieldId: string
  ): Promise<CellValue> {
    const field = await this.getField(lookupFieldId);
    if (!field || field.type !== 'lookup') {
      return null;
    }

    const config: LookupFieldConfig = {
      linkedTableId: field.options?.linkedTableId as string,
      linkedFieldId: field.options?.linkedFieldId as string,
      lookupFieldId: field.options?.lookupFieldId as string,
      aggregationType: field.options?.aggregationType as 'single' | 'concat' | 'sum' | 'avg' | 'min' | 'max' | 'count',
      separator: field.options?.separator as string
    };

    if (!config.linkedTableId || !config.linkedFieldId || !config.lookupFieldId) {
      return null;
    }

    // 获取关联记录
    const linkedValues = await this.getLinkedRecordValues(recordId, config.linkedFieldId);
    if (linkedValues.length === 0) {
      return null;
    }

    // 获取查找字段的值
    const lookupValues = linkedValues.map(record => record[config.lookupFieldId]);

    // 根据聚合类型处理值
    switch (config.aggregationType) {
      case 'concat':
        return lookupValues.filter(v => v !== null && v !== undefined).join(config.separator ?? ', ');
      case 'sum':
        return lookupValues.reduce((sum: number, v) => sum + (Number(v) || 0), 0);
      case 'avg':
        const numbers = lookupValues.map(v => Number(v) || 0).filter(n => !isNaN(n));
        return numbers.length > 0 ? numbers.reduce((sum, n) => sum + n, 0) / numbers.length : 0;
      case 'min':
        return Math.min(...lookupValues.map(v => Number(v) || Infinity));
      case 'max':
        return Math.max(...lookupValues.map(v => Number(v) || -Infinity));
      case 'count':
        return lookupValues.length;
      case 'single':
      default:
        return lookupValues[0] ?? null;
    }
  }

  /**
   * 刷新所有查找字段的值（当关联数据变化时调用）
   */
  async refreshLookupFields(linkedTableId: string): Promise<void> {
    // 查找所有引用该表的查找字段
    const allFields = await db.fields.toArray();
    const lookupFields = allFields.filter(
      f => f.type === 'lookup' && f.options?.linkedTableId === linkedTableId
    );

    for (const lookupField of lookupFields) {
      // 获取该查找字段所在表的所有记录
      const records = await db.records.where('tableId').equals(lookupField.tableId).toArray();

      for (const record of records) {
        const newValue = await this.calculateLookupValue(record.id, lookupField.id);
        const newValues = { ...record.values };
        newValues[lookupField.id] = newValue;

        await db.records.update(record.id, {
          values: newValues,
          updatedAt: Date.now()
        });
      }
    }
  }

  // ==================== 辅助方法 ====================

  /**
   * 获取下一个字段顺序号
   */
  private async getNextFieldOrder(tableId: string): Promise<number> {
    const fields = await db.fields.where('tableId').equals(tableId).toArray();
    return fields.length > 0 ? Math.max(...fields.map(f => f.order)) + 1 : 0;
  }

  /**
   * 复制字段（用于创建类似字段）
   */
  async duplicateField(fieldId: string, newName?: string): Promise<FieldEntity> {
    const field = await this.getField(fieldId);
    if (!field) {
      throw new Error('Field not found');
    }

    const duplicatedField: FieldEntity = {
      ...field,
      id: generateId(),
      name: newName || `${field.name} (复制)`,
      isPrimary: false,
      isSystem: false,
      order: await this.getNextFieldOrder(field.tableId),
      createdAt: Date.now(),
      updatedAt: Date.now()
    };

    await db.fields.add(duplicatedField);
    return duplicatedField;
  }

  /**
   * 批量更新字段选项
   */
  async batchUpdateFieldOptions(
    updates: { fieldId: string; options: FieldOptions }[]
  ): Promise<void> {
    await db.transaction('rw', db.fields, async () => {
      for (const update of updates) {
        await db.fields.update(update.fieldId, {
          options: update.options as Record<string, unknown>,
          updatedAt: Date.now()
        });
      }
    });
  }

  /**
   * 获取字段统计信息
   */
  async getFieldStatistics(fieldId: string): Promise<{
    totalRecords: number;
    filledRecords: number;
    emptyRecords: number;
    fillRate: number;
  }> {
    const field = await this.getField(fieldId);
    if (!field) {
      throw new Error('Field not found');
    }

    const records = await db.records.where('tableId').equals(field.tableId).toArray();
    const totalRecords = records.length;
    const filledRecords = records.filter(r => {
      const value = r.values[fieldId];
      return value !== null && value !== undefined && value !== '';
    }).length;
    const emptyRecords = totalRecords - filledRecords;
    const fillRate = totalRecords > 0 ? (filledRecords / totalRecords) * 100 : 0;

    return {
      totalRecords,
      filledRecords,
      emptyRecords,
      fillRate: Math.round(fillRate * 100) / 100
    };
  }
}

export const fieldService = new FieldService();
