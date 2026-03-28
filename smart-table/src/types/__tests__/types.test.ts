import { describe, it, expect } from "vitest";
import { FieldType } from "../fields";
import { FilterOperator, type FilterCondition } from "../filters";
import { SortDirection, type SortConfig } from "../filters";
import {
  applyFilter,
  applyFilters,
  createEmptyCondition,
  isValidCondition,
  getConditionDescription,
} from "../../utils/filter";
import { applySort, applySorts, getSortDescription } from "../../utils/sort";
import type { RecordEntity, FieldEntity } from "../../db/schema";

describe("Field Types", () => {
  it("should define all field types", () => {
    expect(FieldType.TEXT).toBe("text");
    expect(FieldType.NUMBER).toBe("number");
    expect(FieldType.DATE).toBe("date");
    expect(FieldType.SINGLE_SELECT).toBe("singleSelect");
    expect(FieldType.MULTI_SELECT).toBe("multiSelect");
    expect(FieldType.CHECKBOX).toBe("checkbox");
    expect(FieldType.ATTACHMENT).toBe("attachment");
    expect(FieldType.MEMBER).toBe("member");
    expect(FieldType.RATING).toBe("rating");
    expect(FieldType.PROGRESS).toBe("progress");
    expect(FieldType.PHONE).toBe("phone");
    expect(FieldType.EMAIL).toBe("email");
    expect(FieldType.URL).toBe("url");
    expect(FieldType.FORMULA).toBe("formula");
    expect(FieldType.LINK).toBe("link");
    expect(FieldType.LOOKUP).toBe("lookup");
    expect(FieldType.CREATED_BY).toBe("createdBy");
    expect(FieldType.CREATED_TIME).toBe("createdTime");
    expect(FieldType.UPDATED_BY).toBe("updatedBy");
    expect(FieldType.UPDATED_TIME).toBe("updatedTime");
    expect(FieldType.AUTO_NUMBER).toBe("autoNumber");
  });
});

describe("Filter Types", () => {
  const mockRecords: RecordEntity[] = [
    {
      id: "rec1",
      tableId: "table1",
      values: { name: "Alice", age: 25, active: true },
      createdAt: Date.now(),
      updatedAt: Date.now(),
    },
    {
      id: "rec2",
      tableId: "table1",
      values: { name: "Bob", age: 30, active: false },
      createdAt: Date.now(),
      updatedAt: Date.now(),
    },
    {
      id: "rec3",
      tableId: "table1",
      values: { name: "Charlie", age: 35, active: true },
      createdAt: Date.now(),
      updatedAt: Date.now(),
    },
  ];

  const mockFields: FieldEntity[] = [
    {
      id: "name",
      tableId: "table1",
      name: "Name",
      type: FieldType.TEXT,
      options: {},
      order: 0,
      isPrimary: true,
      isSystem: false,
      isRequired: false,
      createdAt: Date.now(),
      updatedAt: Date.now(),
    },
    {
      id: "age",
      tableId: "table1",
      name: "Age",
      type: FieldType.NUMBER,
      options: {},
      order: 1,
      isPrimary: false,
      isSystem: false,
      isRequired: false,
      createdAt: Date.now(),
      updatedAt: Date.now(),
    },
    {
      id: "active",
      tableId: "table1",
      name: "Active",
      type: FieldType.CHECKBOX,
      options: {},
      order: 2,
      isPrimary: false,
      isSystem: false,
      isRequired: false,
      createdAt: Date.now(),
      updatedAt: Date.now(),
    },
  ];

  it("should create empty filter condition", () => {
    const condition = createEmptyCondition("name");
    expect(condition.fieldId).toBe("name");
    expect(condition.operator).toBeDefined();
    expect(condition.value).toBeNull();
  });

  it("should validate filter condition", () => {
    const validCondition: FilterCondition = {
      fieldId: "name",
      operator: FilterOperator.CONTAINS,
      value: "test",
    };
    expect(isValidCondition(validCondition)).toBe(true);

    const invalidCondition: FilterCondition = {
      fieldId: "name",
      operator: FilterOperator.CONTAINS,
      value: null,
    };
    expect(isValidCondition(invalidCondition)).toBe(false);
  });

  it("should apply single filter", () => {
    const condition: FilterCondition = {
      fieldId: "name",
      operator: FilterOperator.CONTAINS,
      value: "a",
    };

    const filtered = applyFilter(mockRecords, condition, mockFields);
    expect(filtered.length).toBe(2); // Alice and Charlie
    expect(filtered.map((r) => r.values.name)).toContain("Alice");
    expect(filtered.map((r) => r.values.name)).toContain("Charlie");
  });

  it("should apply multiple filters with AND logic", () => {
    const conditions: FilterCondition[] = [
      {
        fieldId: "active",
        operator: FilterOperator.EQUALS,
        value: true,
      },
      {
        fieldId: "age",
        operator: FilterOperator.LESS_THAN,
        value: 30,
      },
    ];

    const filtered = applyFilters(mockRecords, conditions, mockFields, "and");
    expect(filtered.length).toBe(1); // Only Alice
    expect(filtered[0].values.name).toBe("Alice");
  });

  it("should apply multiple filters with OR logic", () => {
    const conditions: FilterCondition[] = [
      {
        fieldId: "name",
        operator: FilterOperator.EQUALS,
        value: "Alice",
      },
      {
        fieldId: "name",
        operator: FilterOperator.EQUALS,
        value: "Bob",
      },
    ];

    const filtered = applyFilters(mockRecords, conditions, mockFields, "or");
    expect(filtered.length).toBe(2);
    expect(filtered.map((r) => r.values.name)).toContain("Alice");
    expect(filtered.map((r) => r.values.name)).toContain("Bob");
  });

  it("should get condition description", () => {
    const condition: FilterCondition = {
      fieldId: "name",
      operator: FilterOperator.CONTAINS,
      value: "test",
    };

    const description = getConditionDescription(condition, mockFields);
    expect(description).toContain("Name");
    expect(description).toContain("包含");
    expect(description).toContain("test");
  });
});

describe("Sort Types", () => {
  const mockRecords: RecordEntity[] = [
    {
      id: "rec1",
      tableId: "table1",
      values: { name: "Charlie", age: 35 },
      createdAt: Date.now(),
      updatedAt: Date.now(),
    },
    {
      id: "rec2",
      tableId: "table1",
      values: { name: "Alice", age: 25 },
      createdAt: Date.now(),
      updatedAt: Date.now(),
    },
    {
      id: "rec3",
      tableId: "table1",
      values: { name: "Bob", age: 30 },
      createdAt: Date.now(),
      updatedAt: Date.now(),
    },
  ];

  const mockFields: FieldEntity[] = [
    {
      id: "name",
      tableId: "table1",
      name: "Name",
      type: FieldType.TEXT,
      options: {},
      order: 0,
      isPrimary: true,
      isSystem: false,
      isRequired: false,
      createdAt: Date.now(),
      updatedAt: Date.now(),
    },
    {
      id: "age",
      tableId: "table1",
      name: "Age",
      type: FieldType.NUMBER,
      options: {},
      order: 1,
      isPrimary: false,
      isSystem: false,
      isRequired: false,
      createdAt: Date.now(),
      updatedAt: Date.now(),
    },
  ];

  it("should apply single sort ascending", () => {
    const sort: SortConfig = {
      fieldId: "name",
      direction: SortDirection.ASC,
    };

    const sorted = applySort(mockRecords, sort, mockFields);
    expect(sorted[0].values.name).toBe("Alice");
    expect(sorted[1].values.name).toBe("Bob");
    expect(sorted[2].values.name).toBe("Charlie");
  });

  it("should apply single sort descending", () => {
    const sort: SortConfig = {
      fieldId: "age",
      direction: SortDirection.DESC,
    };

    const sorted = applySort(mockRecords, sort, mockFields);
    expect(sorted[0].values.age).toBe(35);
    expect(sorted[1].values.age).toBe(30);
    expect(sorted[2].values.age).toBe(25);
  });

  it("should apply multiple sorts", () => {
    const records: RecordEntity[] = [
      {
        id: "rec1",
        tableId: "table1",
        values: { name: "Alice", age: 30 },
        createdAt: Date.now(),
        updatedAt: Date.now(),
      },
      {
        id: "rec2",
        tableId: "table1",
        values: { name: "Alice", age: 25 },
        createdAt: Date.now(),
        updatedAt: Date.now(),
      },
      {
        id: "rec3",
        tableId: "table1",
        values: { name: "Bob", age: 20 },
        createdAt: Date.now(),
        updatedAt: Date.now(),
      },
    ];

    const sorts: SortConfig[] = [
      { fieldId: "name", direction: SortDirection.ASC },
      { fieldId: "age", direction: SortDirection.DESC },
    ];

    const sorted = applySorts(records, sorts, mockFields);
    expect(sorted[0].values.name).toBe("Alice");
    expect(sorted[0].values.age).toBe(30);
    expect(sorted[1].values.name).toBe("Alice");
    expect(sorted[1].values.age).toBe(25);
  });

  it("should get sort description", () => {
    const sort: SortConfig = {
      fieldId: "name",
      direction: SortDirection.ASC,
    };

    const description = getSortDescription(sort, mockFields);
    expect(description).toContain("Name");
    expect(description).toContain("升序");
  });
});
