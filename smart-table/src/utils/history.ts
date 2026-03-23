import type { RecordEntity, FieldEntity } from '@/db/schema'
import type { CellValue } from '@/types'

export interface OperationHistory {
  id: string
  type: 'create' | 'update' | 'delete' | 'batch_delete' | 'batch_update'
  tableId: string
  timestamp: number
  userId?: string
  userName?: string
  data: {
    recordId?: string
    recordIds?: string[]
    fieldId?: string
    oldValue?: CellValue
    newValue?: CellValue
    oldValues?: Record<string, CellValue>
    newValues?: Record<string, CellValue>
  }
  description: string
}

export interface HistorySnapshot {
  id: string
  tableId: string
  name: string
  timestamp: number
  records: RecordEntity[]
  fields: FieldEntity[]
}

class HistoryManager {
  private history: OperationHistory[] = []
  private maxHistorySize = 100
  private snapshots: HistorySnapshot[] = []
  private maxSnapshots = 10
  
  addOperation(operation: Omit<OperationHistory, 'id' | 'timestamp'>): void {
    const historyItem: OperationHistory = {
      ...operation,
      id: `history-${Date.now()}-${Math.random().toString(36).slice(2)}`,
      timestamp: Date.now()
    }
    
    this.history.unshift(historyItem)
    
    if (this.history.length > this.maxHistorySize) {
      this.history = this.history.slice(0, this.maxHistorySize)
    }
  }
  
  getHistory(tableId?: string, limit?: number): OperationHistory[] {
    let items = tableId 
      ? this.history.filter(h => h.tableId === tableId)
      : this.history
    
    if (limit) {
      items = items.slice(0, limit)
    }
    
    return items
  }
  
  getOperationById(id: string): OperationHistory | undefined {
    return this.history.find(h => h.id === id)
  }
  
  clearHistory(tableId?: string): void {
    if (tableId) {
      this.history = this.history.filter(h => h.tableId !== tableId)
    } else {
      this.history = []
    }
  }
  
  createSnapshot(
    tableId: string,
    name: string,
    records: RecordEntity[],
    fields: FieldEntity[]
  ): HistorySnapshot {
    const snapshot: HistorySnapshot = {
      id: `snapshot-${Date.now()}-${Math.random().toString(36).slice(2)}`,
      tableId,
      name,
      timestamp: Date.now(),
      records: JSON.parse(JSON.stringify(records)),
      fields: JSON.parse(JSON.stringify(fields))
    }
    
    const existingIndex = this.snapshots.findIndex(s => s.tableId === tableId)
    if (existingIndex >= 0) {
      this.snapshots.splice(existingIndex, 1)
    }
    
    this.snapshots.unshift(snapshot)
    
    if (this.snapshots.length > this.maxSnapshots) {
      this.snapshots = this.snapshots.slice(0, this.maxSnapshots)
    }
    
    return snapshot
  }
  
  getSnapshots(tableId?: string): HistorySnapshot[] {
    return tableId 
      ? this.snapshots.filter(s => s.tableId === tableId)
      : this.snapshots
  }
  
  getSnapshotById(id: string): HistorySnapshot | undefined {
    return this.snapshots.find(s => s.id === id)
  }
  
  deleteSnapshot(id: string): void {
    this.snapshots = this.snapshots.filter(s => s.id !== id)
  }
  
  restoreFromSnapshot(id: string): { records: RecordEntity[]; fields: FieldEntity[] } | null {
    const snapshot = this.getSnapshotById(id)
    if (!snapshot) return null
    
    return {
      records: JSON.parse(JSON.stringify(snapshot.records)),
      fields: JSON.parse(JSON.stringify(snapshot.fields))
    }
  }
  
  compareWithSnapshot(
    currentRecords: RecordEntity[],
    snapshotId: string
  ): { added: string[]; removed: string[]; modified: string[] } {
    const snapshot = this.getSnapshotById(snapshotId)
    if (!snapshot) {
      return { added: [], removed: [], modified: [] }
    }
    
    const currentIds = new Set(currentRecords.map(r => r.id))
    const snapshotIds = new Set(snapshot.records.map(r => r.id))
    
    const added = [...currentIds].filter(id => !snapshotIds.has(id))
    const removed = [...snapshotIds].filter(id => !currentIds.has(id))
    const modified: string[] = []
    
    for (const record of currentRecords) {
      const snapshotRecord = snapshot.records.find(r => r.id === record.id)
      if (snapshotRecord) {
        const currentValues = JSON.stringify(record.values)
        const snapshotValues = JSON.stringify(snapshotRecord.values)
        if (currentValues !== snapshotValues) {
          modified.push(record.id)
        }
      }
    }
    
    return { added, removed, modified }
  }
  
  getOperationDescription(operation: OperationHistory): string {
    switch (operation.type) {
      case 'create':
        return `创建记录`
      case 'update':
        return `更新字段值`
      case 'delete':
        return `删除记录`
      case 'batch_delete':
        return `批量删除 ${operation.data.recordIds?.length || 0} 条记录`
      case 'batch_update':
        return `批量更新 ${operation.data.recordIds?.length || 0} 条记录`
      default:
        return '未知操作'
    }
  }
}

export const historyManager = new HistoryManager()

export function recordCreateOperation(tableId: string, recordId: string, values: Record<string, CellValue>): void {
  historyManager.addOperation({
    type: 'create',
    tableId,
    data: {
      recordId,
      newValues: values
    },
    description: `创建记录 ${recordId}`
  })
}

export function recordUpdateOperation(
  tableId: string,
  recordId: string,
  fieldId: string,
  oldValue: CellValue,
  newValue: CellValue
): void {
  historyManager.addOperation({
    type: 'update',
    tableId,
    data: {
      recordId,
      fieldId,
      oldValue,
      newValue
    },
    description: `更新记录 ${recordId} 的字段 ${fieldId}`
  })
}

export function recordDeleteOperation(tableId: string, recordId: string, oldValues: Record<string, CellValue>): void {
  historyManager.addOperation({
    type: 'delete',
    tableId,
    data: {
      recordId,
      oldValues
    },
    description: `删除记录 ${recordId}`
  })
}

export function recordBatchDeleteOperation(tableId: string, recordIds: string[]): void {
  historyManager.addOperation({
    type: 'batch_delete',
    tableId,
    data: {
      recordIds
    },
    description: `批量删除 ${recordIds.length} 条记录`
  })
}
