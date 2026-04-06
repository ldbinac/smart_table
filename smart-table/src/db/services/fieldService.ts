import { db } from "../schema";
import type { FieldEntity } from "../schema";
import { generateId } from "../../utils/id";
import type { CellValue, FieldOptions } from "../../types";
import { fieldApiService } from "@/services/api/fieldApiService";
import { normalizeFieldType, denormalizeFieldType } from "@/types/fields";

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
  relationshipType?: "oneToOne" | "oneToMany" | "manyToMany";
  bidirectional?: boolean;
  inverseFieldId?: string;
}

export interface LookupFieldConfig {
  linkedTableId: string;
  linkedFieldId: string;
  lookupFieldId: string;
  aggregationType?:
    | "single"
    | "concat"
    | "sum"
    | "avg"
    | "min"
    | "max"
    | "count";
  separator?: string;
}

export class FieldService {
  async createField(data: CreateFieldData): Promise<FieldEntity> {
    try {
      // 将前端类型转换为后端类型
      const backendType = denormalizeFieldType(data.type);
      
      // 先调用后端 API 创建字段
      const apiField = await fieldApiService.createField(data.tableId, {
        name: data.name,
        type: backendType,
        isRequired: data.isRequired,
        description: data.description,
        options: data.options as Record<string, unknown>,
        defaultValue: data.defaultValue,
      });

      // 将后端返回的字段类型转换为前端类型
      const frontendType = normalizeFieldType(apiField.type);
      
      // 将后端返回的字段保存到本地 IndexedDB
      const localField: FieldEntity = {
        id: apiField.id,
        tableId: data.tableId,
        name: apiField.name,
        type: frontendType,
        options: apiField.options as Record<string, unknown> | undefined,
        isPrimary: apiField.isPrimary || false,
        isSystem: apiField.isSystem || false,
        isRequired: apiField.isRequired || false,
        isVisible: apiField.isVisible ?? true,
        defaultValue: apiField.defaultValue,
        description: apiField.description,
        order: apiField.order ?? 0,
        createdAt: new Date(apiField.createdAt).getTime(),
        updatedAt: new Date(apiField.updatedAt).getTime(),
      };

      await db.fields.add(localField);
      return localField;
    } catch (error) {
      console.error("[fieldService] createField failed:", error);
      throw error;
    }
  }

  async getField(id: string): Promise<FieldEntity | undefined> {
    return db.fields.get(id);
  }

  async getFieldsByTable(tableId: string): Promise<FieldEntity[]> {
    try {
      // 先从后端 API 获取最新数据
      const apiFields = await fieldApiService.getFields(tableId);

      // 将后端返回的字段保存到本地 IndexedDB
      await db.transaction("rw", db.fields, async () => {
        for (const apiField of apiFields) {
          // 将后端返回的字段类型转换为前端类型
          const frontendType = normalizeFieldType(apiField.type);
          
          const localField: FieldEntity = {
            id: apiField.id,
            tableId: apiField.table_id || tableId,
            name: apiField.name,
            type: frontendType,
            options: apiField.options as Record<string, unknown> | undefined,
            isPrimary: apiField.isPrimary || false,
            isSystem: apiField.isSystem || false,
            isRequired: apiField.isRequired || false,
            isVisible: apiField.isVisible ?? true,
            defaultValue: apiField.defaultValue,
            description: apiField.description,
            order: apiField.order ?? 0,
            createdAt: new Date(apiField.createdAt).getTime(),
            updatedAt: new Date(apiField.updatedAt).getTime(),
          };

          await db.fields.put(localField);
        }
      });

      // 从本地 IndexedDB 返回排序后的字段列表
      return db.fields.where("tableId").equals(tableId).sortBy("order");
    } catch (error) {
      console.error("[fieldService] getFieldsByTable failed:", error);
      // 如果 API 调用失败，从本地缓存读取
      console.log(`[fieldService] 从本地缓存读取表 ${tableId} 的字段...`);
      const fields = await db.fields.where("tableId").equals(tableId).sortBy("order");
      console.log(`[fieldService] 从本地缓存读取到 ${fields.length} 个字段`);
      return fields;
    }
  }

  async updateField(id: string, changes: Partial<FieldEntity>): Promise<void> {
    try {
      // 如果需要更新 type，先转换为后端类型
      const apiChanges: Partial<FieldEntity> = { ...changes };
      if (changes.type) {
        apiChanges.type = denormalizeFieldType(changes.type);
      }
      
      // 先调用后端 API 更新字段
      await fieldApiService.updateField(id, apiChanges as any);

      // 如果需要更新 type，转换为前端类型
      const localChanges: Partial<FieldEntity> = { ...changes };
      if (changes.type) {
        localChanges.type = normalizeFieldType(changes.type);
      }
      
      // 再更新本地 IndexedDB
      await db.fields.update(id, {
        ...localChanges,
        updatedAt: Date.now(),
      });
    } catch (error) {
      console.error("[fieldService] updateField failed:", error);
      throw error;
    }
  }

  async updateFieldOptions(id: string, options: FieldOptions): Promise<void> {
    await db.fields.update(id, {
      options: options as Record<string, unknown>,
      updatedAt: Date.now(),
    });
  }

  async deleteField(id: string): Promise<void> {
    const field = await this.getField(id);
    if (!field) return;

    if (field.isSystem) {
      throw new Error("Cannot delete system field");
    }

    try {
      // 先调用后端 API 删除字段
      await fieldApiService.deleteField(id);

      // 再从本地 IndexedDB 删除
      await db.transaction("rw", [db.fields, db.records], async () => {
        const records = await db.records
          .where("tableId")
          .equals(field.tableId)
          .toArray();
        for (const record of records) {
          const newValues = { ...record.values };
          delete newValues[id];
          await db.records.update(record.id, { values: newValues });
        }
        await db.fields.delete(id);
      });
    } catch (error) {
      console.error("[fieldService] deleteField failed:", error);
      throw error;
    }
  }

  async reorderFields(_tableId: string, fieldIds: string[]): Promise<void> {
    await db.transaction("rw", db.fields, async () => {
      for (let i = 0; i < fieldIds.length; i++) {
        await db.fields.update(fieldIds[i], { order: i });
      }
    });
  }

  async updateFieldVisibility(
    fieldId: string,
    isVisible: boolean,
  ): Promise<void> {
    await db.fields.update(fieldId, {
      isVisible,
      updatedAt: Date.now(),
    });
  }

  async addFieldOption(
    fieldId: string,
    option: { id: string; name: string; color: string },
  ): Promise<void> {
    const field = await this.getField(fieldId);
    if (!field) return;

    const options =
      (field.options?.choices || field.options?.options) as Array<{
        id: string;
        name: string;
        color: string;
      }> || [];
    await this.updateFieldOptions(fieldId, {
      ...(field.options as FieldOptions),
      choices: [...options, option],
      options: [...options, option], // 保持向后兼容
    });
  }

  async removeFieldOption(fieldId: string, optionId: string): Promise<void> {
    const field = await this.getField(fieldId);
    if (!field) return;

    const options =
      (field.options?.choices || field.options?.options) as Array<{
        id: string;
        name: string;
        color: string;
      }> || [];
    const filteredOptions = options.filter((opt) => opt.id !== optionId);
    await this.updateFieldOptions(fieldId, {
      ...(field.options as FieldOptions),
      choices: filteredOptions,
      options: filteredOptions, // 保持向后兼容
    });
  }

  // ==================== 关联字段 (Link Field) 方法 ====================

  /**
   * 创建关联字段配置
   */
  async configureLinkField(
    fieldId: string,
    config: LinkFieldConfig,
  ): Promise<void> {
    const field = await this.getField(fieldId);
    if (!field) {
      throw new Error("Field not found");
    }

    if (field.type !== "link") {
      throw new Error("Field is not a link field");
    }

    const updatedOptions: FieldOptions = {
      ...field.options,
      linkedTableId: config.linkedTableId,
      linkedFieldId: config.linkedFieldId,
      displayFieldId: config.displayFieldId,
      allowMultiple: config.allowMultiple ?? false,
      relationshipType: config.relationshipType ?? "oneToMany",
      bidirectional: config.bidirectional ?? false,
      inverseFieldId: config.inverseFieldId,
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
    config: LinkFieldConfig,
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
      type: "link",
      options: {
        linkedTableId: sourceField.tableId,
        linkedFieldId: sourceFieldId,
        allowMultiple:
          config.relationshipType === "manyToMany" ||
          config.relationshipType === "oneToMany",
        relationshipType: this.getInverseRelationshipType(
          config.relationshipType,
        ),
        bidirectional: true,
        inverseFieldId: sourceFieldId,
      },
      isPrimary: false,
      isSystem: false,
      isRequired: false,
      isVisible: true,
      order: await this.getNextFieldOrder(config.linkedTableId),
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };

    await db.fields.add(inverseField);
  }

  /**
   * 获取反向关联类型
   */
  private getInverseRelationshipType(
    type?: "oneToOne" | "oneToMany" | "manyToMany",
  ): "oneToOne" | "oneToMany" | "manyToMany" {
    switch (type) {
      case "oneToMany":
        return "manyToMany";
      case "manyToMany":
        return "manyToMany";
      case "oneToOne":
        return "oneToOne";
      default:
        return "oneToMany";
    }
  }

  /**
   * 获取关联字段的目标表 ID
   */
  async getLinkedTableId(fieldId: string): Promise<string | undefined> {
    const field = await this.getField(fieldId);
    if (!field || field.type !== "link") return undefined;
    return field.options?.linkedTableId as string;
  }

  /**
   * 获取关联字段配置
   */
  async getLinkFieldConfig(fieldId: string): Promise<LinkFieldConfig | null> {
    const field = await this.getField(fieldId);
    if (!field || field.type !== "link") return null;

    return {
      linkedTableId: field.options?.linkedTableId as string,
      linkedFieldId: field.options?.linkedFieldId as string,
      displayFieldId: field.options?.displayFieldId as string,
      allowMultiple: field.options?.allowMultiple as boolean,
      relationshipType: field.options?.relationshipType as
        | "oneToOne"
        | "oneToMany"
        | "manyToMany",
      bidirectional: field.options?.bidirectional as boolean,
      inverseFieldId: field.options?.inverseFieldId as string,
    };
  }

  /**
   * 更新关联字段的关联记录
   */
  async updateLinkFieldValue(
    recordId: string,
    fieldId: string,
    linkedRecordIds: string | string[] | null,
  ): Promise<void> {
    const field = await this.getField(fieldId);
    if (!field || field.type !== "link") {
      throw new Error("Invalid link field");
    }

    const record = await db.records.get(recordId);
    if (!record) {
      throw new Error("Record not found");
    }

    const config = await this.getLinkFieldConfig(fieldId);
    if (!config) {
      throw new Error("Link field configuration not found");
    }

    // 标准化值为数组
    const normalizedValue = linkedRecordIds
      ? Array.isArray(linkedRecordIds)
        ? linkedRecordIds
        : [linkedRecordIds]
      : [];

    // 更新当前记录的字段值
    const newValues = { ...record.values };
    newValues[fieldId] = config.allowMultiple
      ? normalizedValue
      : normalizedValue[0] || null;

    await db.records.update(recordId, {
      values: newValues,
      updatedAt: Date.now(),
    });

    // 如果是双向关联，更新反向关联字段
    if (config.bidirectional && config.inverseFieldId) {
      await this.updateInverseLinkValues(
        recordId,
        normalizedValue,
        config.inverseFieldId,
        config.linkedTableId,
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
    targetTableId: string,
  ): Promise<void> {
    // 获取目标表的所有记录
    const targetRecords = await db.records
      .where("tableId")
      .equals(targetTableId)
      .toArray();

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
        newLinkedIds = newLinkedIds.filter((id) => id !== sourceRecordId);
      }

      // 只有当值发生变化时才更新
      if (JSON.stringify(linkedIds) !== JSON.stringify(newLinkedIds)) {
        const newValues = { ...targetRecord.values };
        const inverseField = await this.getField(inverseFieldId);
        const allowMultiple = inverseField?.options?.allowMultiple as boolean;
        newValues[inverseFieldId] = allowMultiple
          ? newLinkedIds
          : newLinkedIds[0] || null;

        await db.records.update(targetRecord.id, {
          values: newValues,
          updatedAt: Date.now(),
        });
      }
    }
  }

  /**
   * 获取关联记录的值（用于查找字段）
   */
  async getLinkedRecordValues(
    recordId: string,
    linkFieldId: string,
  ): Promise<Record<string, CellValue>[]> {
    const field = await this.getField(linkFieldId);
    if (!field || field.type !== "link") {
      return [];
    }

    const record = await db.records.get(recordId);
    if (!record) return [];

    const linkedIds = record.values[linkFieldId];
    if (!linkedIds) return [];

    const ids = Array.isArray(linkedIds) ? linkedIds : [linkedIds];

    const linkedRecords = await db.records
      .where("id")
      .anyOf(ids as string[])
      .toArray();
    return linkedRecords.map((r) => ({
      id: r.id,
      ...r.values,
    }));
  }

  // ==================== 查找字段 (Lookup Field) 方法 ====================

  /**
   * 配置查找字段
   */
  async configureLookupField(
    fieldId: string,
    config: LookupFieldConfig,
  ): Promise<void> {
    const field = await this.getField(fieldId);
    if (!field) {
      throw new Error("Field not found");
    }

    if (field.type !== "lookup") {
      throw new Error("Field is not a lookup field");
    }

    const updatedOptions: FieldOptions = {
      ...field.options,
      linkedTableId: config.linkedTableId,
      linkedFieldId: config.linkedFieldId,
      lookupFieldId: config.lookupFieldId,
      aggregationType: config.aggregationType ?? "single",
      separator: config.separator ?? ", ",
    };

    await this.updateFieldOptions(fieldId, updatedOptions);
  }

  /**
   * 计算查找字段的值
   */
  async calculateLookupValue(
    recordId: string,
    lookupFieldId: string,
  ): Promise<CellValue> {
    const field = await this.getField(lookupFieldId);
    if (!field || field.type !== "lookup") {
      return null;
    }

    const config: LookupFieldConfig = {
      linkedTableId: field.options?.linkedTableId as string,
      linkedFieldId: field.options?.linkedFieldId as string,
      lookupFieldId: field.options?.lookupFieldId as string,
      aggregationType: field.options?.aggregationType as
        | "single"
        | "concat"
        | "sum"
        | "avg"
        | "min"
        | "max"
        | "count",
      separator: field.options?.separator as string,
    };

    if (
      !config.linkedTableId ||
      !config.linkedFieldId ||
      !config.lookupFieldId
    ) {
      return null;
    }

    // 获取关联记录
    const linkedValues = await this.getLinkedRecordValues(
      recordId,
      config.linkedFieldId,
    );
    if (linkedValues.length === 0) {
      return null;
    }

    // 获取查找字段的值
    const lookupValues = linkedValues.map(
      (record) => record[config.lookupFieldId],
    );

    // 根据聚合类型处理值
    switch (config.aggregationType) {
      case "concat":
        return lookupValues
          .filter((v) => v !== null && v !== undefined)
          .join(config.separator ?? ", ");
      case "sum":
        return lookupValues.reduce(
          (sum: number, v) => sum + (Number(v) || 0),
          0,
        );
      case "avg":
        const numbers = lookupValues
          .map((v) => Number(v) || 0)
          .filter((n) => !isNaN(n));
        return numbers.length > 0
          ? numbers.reduce((sum, n) => sum + n, 0) / numbers.length
          : 0;
      case "min":
        return Math.min(...lookupValues.map((v) => Number(v) || Infinity));
      case "max":
        return Math.max(...lookupValues.map((v) => Number(v) || -Infinity));
      case "count":
        return lookupValues.length;
      case "single":
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
      (f) => f.type === "lookup" && f.options?.linkedTableId === linkedTableId,
    );

    for (const lookupField of lookupFields) {
      // 获取该查找字段所在表的所有记录
      const records = await db.records
        .where("tableId")
        .equals(lookupField.tableId)
        .toArray();

      for (const record of records) {
        const newValue = await this.calculateLookupValue(
          record.id,
          lookupField.id,
        );
        const newValues = { ...record.values };
        newValues[lookupField.id] = newValue;

        await db.records.update(record.id, {
          values: newValues,
          updatedAt: Date.now(),
        });
      }
    }
  }

  // ==================== 辅助方法 ====================

  /**
   * 获取下一个字段顺序号
   */
  private async getNextFieldOrder(tableId: string): Promise<number> {
    const fields = await db.fields.where("tableId").equals(tableId).toArray();
    return fields.length > 0 ? Math.max(...fields.map((f) => f.order)) + 1 : 0;
  }

  /**
   * 复制字段（用于创建类似字段）
   */
  async duplicateField(
    fieldId: string,
    newName?: string,
  ): Promise<FieldEntity> {
    const field = await this.getField(fieldId);
    if (!field) {
      throw new Error("Field not found");
    }

    const duplicatedField: FieldEntity = {
      ...field,
      id: generateId(),
      name: newName || `${field.name} (复制)`,
      isPrimary: false,
      isSystem: false,
      order: await this.getNextFieldOrder(field.tableId),
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };

    await db.fields.add(duplicatedField);
    return duplicatedField;
  }

  /**
   * 批量更新字段选项
   */
  async batchUpdateFieldOptions(
    updates: { fieldId: string; options: FieldOptions }[],
  ): Promise<void> {
    await db.transaction("rw", db.fields, async () => {
      for (const update of updates) {
        await db.fields.update(update.fieldId, {
          options: update.options as Record<string, unknown>,
          updatedAt: Date.now(),
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
      throw new Error("Field not found");
    }

    const records = await db.records
      .where("tableId")
      .equals(field.tableId)
      .toArray();
    const totalRecords = records.length;
    const filledRecords = records.filter((r) => {
      const value = r.values[fieldId];
      return value !== null && value !== undefined && value !== "";
    }).length;
    const emptyRecords = totalRecords - filledRecords;
    const fillRate =
      totalRecords > 0 ? (filledRecords / totalRecords) * 100 : 0;

    return {
      totalRecords,
      filledRecords,
      emptyRecords,
      fillRate: Math.round(fillRate * 100) / 100,
    };
  }
}

export const fieldService = new FieldService();
