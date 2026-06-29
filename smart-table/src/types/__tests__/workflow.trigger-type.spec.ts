import { describe, it, assertType } from 'vitest';
import type { TriggerType } from '@/types/workflow';

describe('TriggerType 类型', () => {
  it('应包含 specified_time', () => {
    assertType<TriggerType>('specified_time');
  });
});
