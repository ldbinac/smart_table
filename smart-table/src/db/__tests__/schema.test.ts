import { describe, it, expect, beforeEach } from 'vitest'
import 'fake-indexeddb/auto'
import { db, type Base, type TableEntity, type FieldEntity, type RecordEntity } from '../schema'

describe('Database Schema', () => {
  beforeEach(async () => {
    await db.bases.clear()
    await db.tableEntities.clear()
    await db.fields.clear()
    await db.records.clear()
  })

  describe('Base operations', () => {
    it('should create a new base', async () => {
      const base: Base = {
        id: 'base-1',
        name: 'Test Base',
        icon: '📊',
        color: '#3370FF',
        isStarred: false,
        createdAt: Date.now(),
        updatedAt: Date.now()
      }

      const id = await db.bases.add(base)
      expect(id).toBe('base-1')

      const savedBase = await db.bases.get('base-1')
      expect(savedBase).toBeDefined()
      expect(savedBase?.name).toBe('Test Base')
    })

    it('should update a base', async () => {
      const base: Base = {
        id: 'base-2',
        name: 'Test Base',
        icon: '📊',
        color: '#3370FF',
        isStarred: false,
        createdAt: Date.now(),
        updatedAt: Date.now()
      }

      await db.bases.add(base)
      
      await db.bases.update('base-2', { name: 'Updated Base' })
      
      const updatedBase = await db.bases.get('base-2')
      expect(updatedBase?.name).toBe('Updated Base')
    })

    it('should delete a base', async () => {
      const base: Base = {
        id: 'base-3',
        name: 'Test Base',
        icon: '📊',
        color: '#3370FF',
        isStarred: false,
        createdAt: Date.now(),
        updatedAt: Date.now()
      }

      await db.bases.add(base)
      await db.bases.delete('base-3')
      
      const deletedBase = await db.bases.get('base-3')
      expect(deletedBase).toBeUndefined()
    })

    it('should list all bases', async () => {
      for (let i = 0; i < 5; i++) {
        await db.bases.add({
          id: `base-${i}`,
          name: `Base ${i}`,
          icon: '📊',
          color: '#3370FF',
          isStarred: false,
          createdAt: Date.now(),
          updatedAt: Date.now()
        })
      }

      const bases = await db.bases.toArray()
      expect(bases.length).toBe(5)
    })
  })

  describe('Table operations', () => {
    it('should create a new table', async () => {
      const table: TableEntity = {
        id: 'table-1',
        baseId: 'base-1',
        name: 'Test Table',
        primaryFieldId: 'field-1',
        recordCount: 0,
        order: 0,
        isStarred: false,
        createdAt: Date.now(),
        updatedAt: Date.now()
      }

      const id = await db.tableEntities.add(table)
      expect(id).toBe('table-1')

      const savedTable = await db.tableEntities.get('table-1')
      expect(savedTable).toBeDefined()
      expect(savedTable?.name).toBe('Test Table')
    })

    it('should get tables by base id', async () => {
      for (let i = 0; i < 3; i++) {
        await db.tableEntities.add({
          id: `table-${i}`,
          baseId: 'base-1',
          name: `Table ${i}`,
          primaryFieldId: `field-${i}`,
          recordCount: 0,
          order: i,
          isStarred: false,
          createdAt: Date.now(),
          updatedAt: Date.now()
        })
      }

      for (let i = 3; i < 5; i++) {
        await db.tableEntities.add({
          id: `table-${i}`,
          baseId: 'base-2',
          name: `Table ${i}`,
          primaryFieldId: `field-${i}`,
          recordCount: 0,
          order: i,
          isStarred: false,
          createdAt: Date.now(),
          updatedAt: Date.now()
        })
      }

      const tables = await db.tableEntities.where('baseId').equals('base-1').toArray()
      expect(tables.length).toBe(3)
    })
  })

  describe('Field operations', () => {
    it('should create a new field', async () => {
      const field: FieldEntity = {
        id: 'field-1',
        tableId: 'table-1',
        name: 'Name',
        type: 'text',
        options: {},
        order: 0,
        isPrimary: true,
        isSystem: false,
        isRequired: false,
        createdAt: Date.now(),
        updatedAt: Date.now()
      }

      const id = await db.fields.add(field)
      expect(id).toBe('field-1')

      const savedField = await db.fields.get('field-1')
      expect(savedField).toBeDefined()
      expect(savedField?.name).toBe('Name')
      expect(savedField?.isPrimary).toBe(true)
    })

    it('should get fields by table id', async () => {
      for (let i = 0; i < 5; i++) {
        await db.fields.add({
          id: `field-${i}`,
          tableId: 'table-1',
          name: `Field ${i}`,
          type: 'text',
          options: {},
          order: i,
          isPrimary: i === 0,
          isSystem: false,
          isRequired: false,
          createdAt: Date.now(),
          updatedAt: Date.now()
        })
      }

      const fields = await db.fields.where('tableId').equals('table-1').toArray()
      expect(fields.length).toBe(5)
      expect(fields[0].isPrimary).toBe(true)
    })
  })

  describe('Record operations', () => {
    it('should create a new record', async () => {
      const record: RecordEntity = {
        id: 'record-1',
        tableId: 'table-1',
        values: {
          'field-1': 'Test Value'
        },
        createdAt: Date.now(),
        updatedAt: Date.now()
      }

      const id = await db.records.add(record)
      expect(id).toBe('record-1')

      const savedRecord = await db.records.get('record-1')
      expect(savedRecord).toBeDefined()
      expect(savedRecord?.values['field-1']).toBe('Test Value')
    })

    it('should get records by table id', async () => {
      for (let i = 0; i < 10; i++) {
        await db.records.add({
          id: `record-${i}`,
          tableId: 'table-1',
          values: {
            'field-1': `Value ${i}`
          },
          createdAt: Date.now(),
          updatedAt: Date.now()
        })
      }

      const records = await db.records.where('tableId').equals('table-1').toArray()
      expect(records.length).toBe(10)
    })

    it('should update record values', async () => {
      await db.records.add({
        id: 'record-update',
        tableId: 'table-1',
        values: {
          'field-1': 'Original Value'
        },
        createdAt: Date.now(),
        updatedAt: Date.now()
      })

      await db.records.update('record-update', {
        values: {
          'field-1': 'Updated Value'
        }
      })

      const updatedRecord = await db.records.get('record-update')
      expect(updatedRecord?.values['field-1']).toBe('Updated Value')
    })

    it('should delete a record', async () => {
      await db.records.add({
        id: 'record-delete',
        tableId: 'table-1',
        values: {},
        createdAt: Date.now(),
        updatedAt: Date.now()
      })

      await db.records.delete('record-delete')
      
      const deletedRecord = await db.records.get('record-delete')
      expect(deletedRecord).toBeUndefined()
    })
  })

  describe('Transaction operations', () => {
    it('should rollback on error', async () => {
      await db.transaction('rw', [db.bases, db.tableEntities], async () => {
        await db.bases.add({
          id: 'base-tx',
          name: 'Transaction Test',
          icon: '📊',
          color: '#3370FF',
          isStarred: false,
          createdAt: Date.now(),
          updatedAt: Date.now()
        })

        await db.tableEntities.add({
          id: 'table-tx',
          baseId: 'base-tx',
          name: 'Transaction Table',
          primaryFieldId: 'field-tx',
          recordCount: 0,
          order: 0,
          isStarred: false,
          createdAt: Date.now(),
          updatedAt: Date.now()
        })

        throw new Error('Simulated error')
      }).catch(() => {
        // Expected error
      })

      const base = await db.bases.get('base-tx')
      const table = await db.tableEntities.get('table-tx')
      
      expect(base).toBeUndefined()
      expect(table).toBeUndefined()
    })
  })
})
