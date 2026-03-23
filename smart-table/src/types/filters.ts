export const FilterOperator = {
  EQUALS: 'equals',
  NOT_EQUALS: 'notEquals',
  CONTAINS: 'contains',
  NOT_CONTAINS: 'notContains',
  STARTS_WITH: 'startsWith',
  ENDS_WITH: 'endsWith',
  IS_EMPTY: 'isEmpty',
  IS_NOT_EMPTY: 'isNotEmpty',
  GREATER_THAN: 'greaterThan',
  LESS_THAN: 'lessThan',
  GREATER_THAN_OR_EQUAL: 'greaterThanOrEqual',
  LESS_THAN_OR_EQUAL: 'lessThanOrEqual',
  IS_WITHIN: 'isWithin',
  IS_BEFORE: 'isBefore',
  IS_AFTER: 'isAfter',
  IS_ANY_OF: 'isAnyOf',
  IS_NONE_OF: 'isNoneOf'
} as const;

export type FilterOperatorValue = typeof FilterOperator[keyof typeof FilterOperator];

export const SortDirection = {
  ASC: 'asc',
  DESC: 'desc'
} as const;

export type SortDirectionValue = typeof SortDirection[keyof typeof SortDirection];

export interface FilterCondition {
  fieldId: string;
  operator: FilterOperatorValue;
  value?: unknown;
}

export interface SortConfig {
  fieldId: string;
  direction: SortDirectionValue;
}

export interface FilterGroup {
  conditions: FilterCondition[];
  conjunction: 'and' | 'or';
}
