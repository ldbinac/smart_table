import { describe, it, expect } from 'vitest'
import { FormulaEngine, formulaEngine } from '../engine'
import { formulaFunctions, functionCategories, functionDescriptions } from '../functions'
import type { FieldEntity, RecordEntity } from '../../../db/schema'
import { FieldType } from '../../../types/fields'

describe('Formula Engine', () => {
  const mockFields: FieldEntity[] = [
    {
      id: 'price',
      tableId: 'table1',
      name: 'Price',
      type: FieldType.NUMBER,
      options: {},
      order: 0,
      isPrimary: false,
      isSystem: false,
      isRequired: false,
      createdAt: Date.now(),
      updatedAt: Date.now()
    },
    {
      id: 'quantity',
      tableId: 'table1',
      name: 'Quantity',
      type: FieldType.NUMBER,
      options: {},
      order: 1,
      isPrimary: false,
      isSystem: false,
      isRequired: false,
      createdAt: Date.now(),
      updatedAt: Date.now()
    },
    {
      id: 'name',
      tableId: 'table1',
      name: 'Name',
      type: FieldType.TEXT,
      options: {},
      order: 2,
      isPrimary: true,
      isSystem: false,
      isRequired: false,
      createdAt: Date.now(),
      updatedAt: Date.now()
    }
  ]

  const engine = new FormulaEngine(mockFields)

  describe('Field Reference Parsing', () => {
    it('should parse field references', () => {
      const refs = engine.parseFieldRefs('{Price} * {Quantity}')
      expect(refs).toContain('price')
    })

    it('should handle multiple field references', () => {
      const refs = engine.parseFieldRefs('{Price} + {Quantity}')
      expect(refs).toContain('price')
      expect(refs).toContain('quantity')
    })

    it('should handle case-insensitive field names', () => {
      const refs = engine.parseFieldRefs('{PRICE} + {quantity}')
      expect(refs).toContain('price')
      expect(refs).toContain('quantity')
    })
  })

  describe('Basic Calculations', () => {
    const record: RecordEntity = {
      id: 'rec1',
      tableId: 'table1',
      values: {
        price: 100,
        quantity: 5,
        name: 'Test Product'
      },
      createdAt: Date.now(),
      updatedAt: Date.now()
    }

    it('should calculate multiplication', () => {
      const result = engine.calculate(record, '{Price} * {Quantity}')
      expect(result).toBe(500)
    })

    it('should calculate addition', () => {
      const result = engine.calculate(record, '{Price} + {Quantity}')
      expect(result).toBe(105)
    })

    it('should calculate subtraction', () => {
      const result = engine.calculate(record, '{Price} - {Quantity}')
      expect(result).toBe(95)
    })

    it('should calculate division', () => {
      const result = engine.calculate(record, '{Price} / {Quantity}')
      expect(result).toBe(20)
    })
  })

  describe('Formula Validation', () => {
    it('should validate correct formula', () => {
      const result = engine.validateFormula('{Price} * 2')
      expect(result.valid).toBe(true)
    })

    it('should detect invalid field reference', () => {
      const result = engine.validateFormula('{InvalidField} * 2')
      expect(result.valid).toBe(false)
      expect(result.error).toBeDefined()
    })
  })

  describe('Formula Description', () => {
    it('should generate formula description', () => {
      const description = engine.getFormulaDescription('{Price} * {Quantity}')
      expect(description).toContain('Price')
      expect(description).toContain('Quantity')
    })
  })
})

describe('Formula Functions', () => {
  describe('Math Functions', () => {
    it('should calculate SUM', () => {
      expect(formulaFunctions.SUM(1, 2, 3, 4, 5)).toBe(15)
    })

    it('should calculate AVG', () => {
      expect(formulaFunctions.AVG(10, 20, 30)).toBe(20)
    })

    it('should calculate MAX', () => {
      expect(formulaFunctions.MAX(1, 5, 3, 2)).toBe(5)
    })

    it('should calculate MIN', () => {
      expect(formulaFunctions.MIN(1, 5, 3, 2)).toBe(1)
    })

    it('should calculate ROUND', () => {
      expect(formulaFunctions.ROUND(3.14159, 2)).toBe(3.14)
    })

    it('should calculate CEILING', () => {
      expect(formulaFunctions.CEILING(3.14)).toBe(4)
    })

    it('should calculate FLOOR', () => {
      expect(formulaFunctions.FLOOR(3.14)).toBe(3)
    })

    it('should calculate ABS', () => {
      expect(formulaFunctions.ABS(-5)).toBe(5)
    })

    it('should calculate MOD', () => {
      expect(formulaFunctions.MOD(10, 3)).toBe(1)
    })

    it('should calculate POWER', () => {
      expect(formulaFunctions.POWER(2, 3)).toBe(8)
    })

    it('should calculate SQRT', () => {
      expect(formulaFunctions.SQRT(16)).toBe(4)
    })
  })

  describe('Text Functions', () => {
    it('should concatenate text', () => {
      expect(formulaFunctions.CONCAT('Hello', ' ', 'World')).toBe('Hello World')
    })

    it('should get left characters', () => {
      expect(formulaFunctions.LEFT('Hello', 2)).toBe('He')
    })

    it('should get right characters', () => {
      expect(formulaFunctions.RIGHT('Hello', 2)).toBe('lo')
    })

    it('should get text length', () => {
      expect(formulaFunctions.LEN('Hello')).toBe(5)
    })

    it('should convert to upper case', () => {
      expect(formulaFunctions.UPPER('hello')).toBe('HELLO')
    })

    it('should convert to lower case', () => {
      expect(formulaFunctions.LOWER('HELLO')).toBe('hello')
    })

    it('should trim text', () => {
      expect(formulaFunctions.TRIM('  Hello  ')).toBe('Hello')
    })
  })

  describe('Logic Functions', () => {
    it('should evaluate IF true', () => {
      expect(formulaFunctions.IF(true, 'Yes', 'No')).toBe('Yes')
    })

    it('should evaluate IF false', () => {
      expect(formulaFunctions.IF(false, 'Yes', 'No')).toBe('No')
    })

    it('should evaluate AND', () => {
      expect(formulaFunctions.AND(true, true)).toBe(true)
      expect(formulaFunctions.AND(true, false)).toBe(false)
    })

    it('should evaluate OR', () => {
      expect(formulaFunctions.OR(false, true)).toBe(true)
      expect(formulaFunctions.OR(false, false)).toBe(false)
    })

    it('should evaluate NOT', () => {
      expect(formulaFunctions.NOT(true)).toBe(false)
      expect(formulaFunctions.NOT(false)).toBe(true)
    })
  })

  describe('Count Functions', () => {
    it('should count values', () => {
      expect(formulaFunctions.COUNT(1, 2, 3, null, '')).toBe(3)
    })

    it('should count all values', () => {
      expect(formulaFunctions.COUNTA(1, 2, 3, null, '')).toBe(5)
    })
  })

  describe('Function Categories', () => {
    it('should have math functions', () => {
      expect(functionCategories.math).toContain('SUM')
      expect(functionCategories.math).toContain('AVG')
    })

    it('should have text functions', () => {
      expect(functionCategories.text).toContain('CONCAT')
      expect(functionCategories.text).toContain('LEFT')
    })

    it('should have logic functions', () => {
      expect(functionCategories.logic).toContain('IF')
      expect(functionCategories.logic).toContain('AND')
    })
  })

  describe('Function Descriptions', () => {
    it('should have descriptions for all functions', () => {
      expect(functionDescriptions.SUM).toBeDefined()
      expect(functionDescriptions.IF).toBeDefined()
      expect(functionDescriptions.CONCAT).toBeDefined()
    })
  })
})

describe('Formula Engine Factory', () => {
  it('should create engine instance', () => {
    const engine = formulaEngine.createEngine([])
    expect(engine).toBeInstanceOf(FormulaEngine)
  })
})
