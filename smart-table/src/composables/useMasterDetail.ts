import { ref, shallowRef, computed } from 'vue';
import { MasterDetailPlugin } from '@visactor/vtable-plugins';
import type { ListTable } from '@visactor/vtable';
import { FieldType } from '@/types/fields';
import { masterDetailService } from '@/services/masterDetailService';
import { linkApiService } from '@/services/api/linkApiService';

export interface LinkFieldInfo {
  fieldId: string;
  fieldName: string;
  targetTableId: string;
  relationshipType: string;
}

/**
 * 主从表组合式函数
 * 封装 VTable MasterDetailPlugin 插件实例创建、事件监听、懒加载、子表列构建等逻辑
 */
export function useMasterDetail(options: {
  readonly: boolean;
  onSubTableAction?: (action: string, data: any) => void;
}) {
  const { readonly, onSubTableAction } = options;

  // 响应式状态
  const masterDetailPlugin = shallowRef<MasterDetailPlugin | null>(null);
  const linkFields = ref<LinkFieldInfo[]>([]);
  const currentLinkFieldId = ref<string | null>(null);
  // 缓存的子表列配置，在 detectLinkFields / switchLinkField 后预加载
  const cachedColumns = ref<any[]>([]);
  // 子表列增强器：由 VTableView 注入主表的 customRender / customLayout 等渲染配置
  // 让子表字段（单选/多选/附件/成员/评分等）与主表展示样式保持一致
  let columnEnhancer: ((columns: any[], targetFields: any[]) => any[]) | null = null;
  // 子表记录转换器：由 VTableView 注入主表的字段值转换逻辑
  // 让子表记录值（单选 ID -> name、成员解析等）与主表 transformRecords 保持一致
  let recordTransformer: ((records: any[], targetFields: any[]) => any[]) | null = null;

  // 计算属性
  const hasLinkFields = computed(() => linkFields.value.length > 0);
  const hasMultipleLinkFields = computed(() => linkFields.value.length > 1);

  /**
   * 设置子表列增强器
   * VTableView 通过此方法注入主表的 customRender / customLayout 渲染逻辑
   */
  function setColumnEnhancer(enhancer: ((columns: any[], targetFields: any[]) => any[]) | null): void {
    columnEnhancer = enhancer;
  }

  /**
   * 设置子表记录转换器
   * VTableView 通过此方法注入主表的字段值转换逻辑（单选 ID -> name 等）
   */
  function setRecordTransformer(transformer: ((records: any[], targetFields: any[]) => any[]) | null): void {
    recordTransformer = transformer;
  }

  /**
   * 从字段列表中检测 LINK 类型字段，并初始化当前选中的关联字段
   */
  function detectLinkFields(fields: any[]): void {
    const detected = fields
      .filter((f) => f.type === FieldType.LINK)
      .map((f) => ({
        fieldId: f.id,
        fieldName: f.name,
        targetTableId: (f.options?.linkedTableId || f.config?.linkedTableId || '') as string,
        relationshipType: (f.options?.relationshipType || f.config?.relationshipType || 'one_to_many') as string,
      }))
      .filter((f) => f.targetTableId); // 过滤掉没有目标表的

    linkFields.value = detected;

    // 首次自动选中第一个 LINK 字段
    if (detected.length > 0 && !currentLinkFieldId.value) {
      currentLinkFieldId.value = detected[0].fieldId;
    }

    // 如果当前选中的字段已不存在，重置为第一个（或清空）
    if (currentLinkFieldId.value && !detected.find((f) => f.fieldId === currentLinkFieldId.value)) {
      currentLinkFieldId.value = detected.length > 0 ? detected[0].fieldId : null;
    }
  }

  /**
   * 预加载当前 LINK 字段对应目标表的列配置并缓存
   * 列配置在 detailTableOptions 中同步使用，需提前缓存
   * 若设置了 columnEnhancer，会用其增强列配置（注入主表渲染样式）
   */
  async function preloadColumns(): Promise<void> {
    const fieldId = currentLinkFieldId.value;
    if (!fieldId) {
      cachedColumns.value = [];
      return;
    }

    const linkField = linkFields.value.find((f) => f.fieldId === fieldId);
    if (!linkField) {
      cachedColumns.value = [];
      return;
    }

    const targetFields = await masterDetailService.getTargetTableFields(linkField.targetTableId);
    let columns = masterDetailService.buildSubTableColumns(targetFields) as any[];
    // 应用列增强器：注入主表的 customRender / customLayout 等渲染配置
    if (columnEnhancer) {
      columns = columnEnhancer(columns, targetFields);
    }
    cachedColumns.value = columns;
  }

  /**
   * 创建 MasterDetailPlugin 插件实例
   * 列配置使用 cachedColumns（需在调用前通过 preloadColumns 预加载）
   */
  function createPluginInstance(theme?: any): MasterDetailPlugin | null {
    if (!hasLinkFields.value) return null;

    const plugin = new MasterDetailPlugin({
      enableCheckboxCascade: false, // 暂不启用级联选择
      childrenKey: 'children',
      detailTableOptions: () => {
        // 注意：不要返回 records 字段。
        // renderSubTable 会先设置 baseSubTableOptions.records = childrenData，
        // 再用 Object.assign 合并 userDetailConfig（即本函数返回值）。
        // 若此处返回 records: []，会覆盖 childrenData，导致子表数据为空。
        return {
          defaultRowHeight: 32,
          defaultHeaderRowHeight: 36,
          theme: theme || undefined,
          columns: cachedColumns.value,
          emptyTip: '暂无关联记录',
          style: {
            // 底部 margin 设为 48px，为子表工具栏预留空间，避免遮挡最后一条数据
            // 总高度 280 = 240（内容区）+ 8（顶部）+ 48（底部含工具栏）
            margin: [8, 8, 48, 8],
            height: 280,
          },
        };
      },
    });

    masterDetailPlugin.value = plugin;
    return plugin;
  }

  /**
   * 处理 VTable tree_hierarchy_state_change 事件，实现子表懒加载
   * 仅在展开且 children === true（懒加载标识）时触发请求
   */
  async function handleLazyLoad(args: any, tableInstance: ListTable): Promise<void> {
    // 仅处理展开操作且 children === true（懒加载标识）
    if (args.hierarchyState !== 'expand') return;

    const originData = args.originData;
    if (!originData || originData.children !== true) return;

    const recordId = originData._originalRecord?.id || originData._recordId || originData.id;
    if (!recordId) return;

    const fieldId = currentLinkFieldId.value;
    if (!fieldId) return;

    console.log('[useMasterDetail] handleLazyLoad 开始:', {
      recordId,
      fieldId,
      linkFieldsCount: linkFields.value.length,
      linkFields: linkFields.value.map(f => ({ fieldId: f.fieldId, targetTableId: f.targetTableId })),
      cachedColumnsCount: cachedColumns.value.length,
      col: args.col,
      row: args.row,
    });

    // 显示加载状态
    tableInstance.setLoadingHierarchyState(args.col, args.row);

    try {
      const response = await masterDetailService.getLinkedRecordsDetail(recordId, fieldId, {
        page: 1,
        per_page: 100,
      });

      console.log('[useMasterDetail] 后端返回数据:', {
        recordsCount: response.records?.length || 0,
        fieldsCount: response.fields?.length || 0,
        total: response.total,
        firstRecord: response.records?.[0],
        firstRecordValues: response.records?.[0]?.values,
      });

      // 获取目标表字段定义并刷新缓存列配置
      const linkField = linkFields.value.find((f) => f.fieldId === fieldId);
      console.log('[useMasterDetail] linkField 查找结果:', {
        fieldId,
        linkFieldFound: !!linkField,
        targetTableId: linkField?.targetTableId,
      });
      if (linkField) {
        const targetFields = await masterDetailService.getTargetTableFields(linkField.targetTableId);
        let columns = masterDetailService.buildSubTableColumns(targetFields) as any[];
        // 应用列增强器：注入主表的 customRender / customLayout 等渲染配置
        if (columnEnhancer) {
          columns = columnEnhancer(columns, targetFields);
        }
        cachedColumns.value = columns;
        console.log('[useMasterDetail] cachedColumns 已刷新:', {
          targetFieldsCount: targetFields.length,
          cachedColumnsCount: cachedColumns.value.length,
          firstColumn: cachedColumns.value[0],
        });
      } else {
        console.warn('[useMasterDetail] 未找到 linkField，cachedColumns 未刷新，仍为空数组');
      }

      // 准备子表数据（将后端返回的 records 转换为 VTable 子表需要的格式）
      // 先做基本字段映射，再调用 recordTransformer 做字段值转换（单选 ID->name 等）
      let childrenData = response.records.map((r) => ({
        ...r.values,
        _recordId: r.id,
        _originalRecord: r,
      }));
      // 应用记录转换器：注入主表的字段值转换逻辑
      if (recordTransformer && linkField) {
        const targetFields = await masterDetailService.getTargetTableFields(linkField.targetTableId);
        childrenData = recordTransformer(childrenData, targetFields);
      }

      console.log('[useMasterDetail] childrenData 准备完成:', {
        childrenCount: childrenData.length,
        firstChild: childrenData[0],
      });

      // 设置子表数据并展开
      const plugin = masterDetailPlugin.value;
      console.log('[useMasterDetail] plugin 状态:', {
        pluginExists: !!plugin,
      });
      if (plugin) {
        const bodyRowIndex = args.row - tableInstance.columnHeaderLevelCount;

        // 关键修复 1：setRecordChildren 用 getCellOriginRecord（dataSource.get）设置 children，
        // 但 expandRow 用 getRecordByRowIndex（dataSource.getRaw）读取 children。
        // CachedDataSource 两者可能返回不同对象引用，需同步设置 rawRecord.children。
        try {
          const rawRecord = tableInstance.dataSource.getRaw(bodyRowIndex);
          if (rawRecord && typeof rawRecord === 'object') {
            (rawRecord as any).children = childrenData;
            console.log('[useMasterDetail] 已通过 dataSource.getRaw 设置 children');
          }
        } catch (e) {
          console.warn('[useMasterDetail] dataSource.getRaw 设置 children 失败:', e);
        }

        // 关键修复 2：MasterDetailPlugin 的 tree_hierarchy_state_change 事件处理器
        // 先于 handleLazyLoad 执行，已用空 childrenData 调用 expandRow，行已被标记为已展开。
        // setRecordChildren 内部的 expandRow 会因 isRowExpanded 返回 true 而早退，不重新渲染子表。
        // 这里先调用 collapseRow 清除已展开状态和旧子表实例，确保 setRecordChildren 能重新展开渲染。
        if (plugin.collapseRow) {
          try {
            plugin.collapseRow(args.row, args.col);
            console.log('[useMasterDetail] 已调用 collapseRow 清除旧展开状态');
          } catch (e) {
            // 忽略未展开时的关闭错误
          }
        }

        plugin.setRecordChildren(childrenData, args.col, args.row);
        console.log('[useMasterDetail] setRecordChildren 已调用');
      } else {
        console.error('[useMasterDetail] plugin 不存在，无法设置子表数据');
      }
    } catch (error) {
      console.error('[useMasterDetail] 懒加载失败:', error);
      // 设置空数组以关闭加载状态
      const plugin = masterDetailPlugin.value;
      if (plugin) {
        plugin.setRecordChildren([], args.col, args.row);
      }
    }
  }

  /**
   * 处理子表单元格编辑事件
   * 编辑后将变更持久化到后端，清除关联缓存，并通知父组件
   */
  async function handleSubTableEdit(originalEventArgs: any, subTable: any, masterBodyRowIndex: number): Promise<void> {
    if (readonly) return;

    const { row, col, changedValue } = originalEventArgs || {};
    if (!subTable || row === undefined || col === undefined) return;

    // 获取子表中编辑行的记录ID和字段ID
    const record = subTable.getCellOriginRecord(col, row);
    const recordId = record?._recordId || record?.id;
    const column = subTable.getHeaderField(col);
    const fieldId = column?.field;

    if (!recordId || !fieldId) return;

    try {
      // 动态导入避免循环依赖
      const { recordApiService } = await import('@/services/api/recordApiService');
      await recordApiService.updateRecord(recordId, {
        values: { [fieldId]: changedValue },
      });

      // 编辑子表记录后，清除关联缓存（关联显示值可能已变更）
      linkApiService.invalidateCacheByPattern('record_links:');

      onSubTableAction?.('edit', { originalEventArgs, subTable, masterBodyRowIndex, recordId, fieldId });
    } catch (error) {
      console.error('[useMasterDetail] 子表编辑保存失败:', error);
    }
  }

  /**
   * 处理通过 PLUGIN_EVENT 转发的子表事件
   */
  function handleSubTableEvent(args: any): void {
    const { plugin, pluginEventInfo } = args;

    // 检查是否是主从表插件的事件
    if (!plugin || plugin.name !== 'Master Detail Plugin') return;
    if (!pluginEventInfo) return;

    const { eventType, masterRowIndex, masterBodyRowIndex, subTable, originalEventArgs } = pluginEventInfo;

    // MasterDetailPlugin 的 forwardSubTableEvent 将 originalEventArgs 作为数组传递（(...args)），
    // 实际的事件参数对象在数组的第一个元素中，需提取出来使用
    const eventArgs = Array.isArray(originalEventArgs) ? originalEventArgs[0] : originalEventArgs;

    // 根据 eventType 处理不同事件
    switch (eventType) {
      case 'click_cell':
        // 单元格点击
        onSubTableAction?.('click_cell', {
          originalEventArgs: eventArgs,
          subTable,
          masterRowIndex,
          masterBodyRowIndex,
        });
        break;
      case 'change_cell_value':
        // 单元格值变更（编辑完成）
        handleSubTableEdit(eventArgs, subTable, masterBodyRowIndex);
        break;
      case 'contextmenu_cell':
        // 右键菜单 - 解除关联
        if (!readonly) {
          const ctxRecord = subTable?.getCellOriginRecord(eventArgs?.col, eventArgs?.row);
          const targetRecordId = ctxRecord?._recordId || ctxRecord?.id;
          if (targetRecordId) {
            onSubTableAction?.('unlink', {
              targetRecordId,
              subTable,
              masterRowIndex,
              masterBodyRowIndex,
            });
          }
        }
        break;
    }
  }

  /**
   * 切换当前 LINK 字段，并预加载新字段的列配置
   */
  async function switchLinkField(fieldId: string): Promise<void> {
    if (fieldId === currentLinkFieldId.value) return;
    currentLinkFieldId.value = fieldId;
    await preloadColumns();
  }

  /**
   * 刷新指定主记录的子表数据
   */
  async function refreshSubTable(
    recordId: string,
    col: number,
    row: number,
    tableInstance: ListTable
  ): Promise<void> {
    const fieldId = currentLinkFieldId.value;
    if (!fieldId) return;

    tableInstance.setLoadingHierarchyState(col, row);

    try {
      const response = await masterDetailService.getLinkedRecordsDetail(recordId, fieldId, {
        page: 1,
        per_page: 100,
      });

      let childrenData = response.records.map((r) => ({
        ...r.values,
        _recordId: r.id,
        _originalRecord: r,
      }));
      // 应用记录转换器
      if (recordTransformer) {
        const linkField = linkFields.value.find((f) => f.fieldId === fieldId);
        if (linkField) {
          const targetFields = await masterDetailService.getTargetTableFields(linkField.targetTableId);
          childrenData = recordTransformer(childrenData, targetFields);
        }
      }

      const plugin = masterDetailPlugin.value;
      if (plugin) {
        // 同步设置 dataSource.getRaw 返回的 record，确保 expandRow 能读取到最新 children
        const bodyRowIndex = row - tableInstance.columnHeaderLevelCount;
        try {
          const rawRecord = tableInstance.dataSource.getRaw(bodyRowIndex);
          if (rawRecord && typeof rawRecord === 'object') {
            (rawRecord as any).children = childrenData;
          }
        } catch (e) {
          console.warn('[useMasterDetail] refreshSubTable: dataSource.getRaw 设置 children 失败:', e);
        }

        // 先关闭已展开的行（清除 expandedRows 标记），再重新展开，确保子表重新渲染
        try {
          if (plugin.collapseRow) {
            plugin.collapseRow(row, col);
          }
        } catch (e) {
          // 忽略未展开时的关闭错误
        }

        plugin.setRecordChildren(childrenData, col, row);
      }
    } catch (error) {
      console.error('[useMasterDetail] 刷新子表失败:', error);
    }
  }

  /**
   * 释放插件实例和状态
   */
  function dispose(): void {
    masterDetailPlugin.value = null;
    linkFields.value = [];
    currentLinkFieldId.value = null;
    cachedColumns.value = [];
  }

  return {
    masterDetailPlugin,
    linkFields,
    currentLinkFieldId,
    hasLinkFields,
    hasMultipleLinkFields,
    detectLinkFields,
    createPluginInstance,
    handleLazyLoad,
    handleSubTableEvent,
    switchLinkField,
    refreshSubTable,
    setColumnEnhancer,
    setRecordTransformer,
    dispose,
  };
}
