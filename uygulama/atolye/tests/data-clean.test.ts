import { describe, it, expect } from 'vitest';
import { execDataClean } from '../src/engine/executionEngine';

function input(rows: Record<string, unknown>[]) {
  return { rows, columns: Object.keys(rows[0]) };
}

describe('execDataClean', () => {
  it('drops rows with missing values in target columns', () => {
    const r = execDataClean('n', { strategy: 'drop_rows' }, input([{ a: 1, b: 2 }, { a: '', b: 3 }, { a: 4, b: null }, { a: 5, b: 6 }]));
    expect(r.status).toBe('success');
    expect((r.data as { rows_after: number }).rows_after).toBe(2);
    expect((r.data as { rows_dropped: number }).rows_dropped).toBe(2);
  });
  it('fills missing numeric cells with the column mean', () => {
    const r = execDataClean('n', { columns: 'a', strategy: 'mean' }, input([{ a: 10 }, { a: '', }, { a: 20 }]));
    const rows = (r.data as { rows: Record<string, unknown>[] }).rows;
    expect(rows[1].a).toBe(15);
    expect((r.data as { cells_filled: number }).cells_filled).toBe(1);
  });
  it('fills with the mode for categorical columns', () => {
    const r = execDataClean('n', { columns: 'c', strategy: 'mode' }, input([{ c: 'x' }, { c: 'x' }, { c: '' }, { c: 'y' }]));
    const rows = (r.data as { rows: Record<string, unknown>[] }).rows;
    expect(rows[2].c).toBe('x');
  });
  it('errors on empty input', () => {
    const r = execDataClean('n', {}, { rows: [], columns: [] });
    expect(r.status).toBe('error');
  });
});
