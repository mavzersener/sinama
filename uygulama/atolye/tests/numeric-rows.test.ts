import { describe, it, expect } from 'vitest';
import { numericRows } from '../src/engine/executionEngine';

describe('numericRows (ML garbage-in guard)', () => {
  const rows = [
    { lat: 40.1, lng: 29.0, name: 'a' },
    { lat: '', lng: 30.0, name: 'b' },
    { lat: 41.0, lng: null, name: 'c' },
    { lat: '38.5', lng: '27.1', name: 'd' },
    { lat: 39.0, lng: 32.0, name: 'e' },
  ];
  it('keeps only rows where all listed columns are finite numbers', () => {
    const out = numericRows(rows, ['lat', 'lng']);
    expect(out.map((r) => r.name)).toEqual(['a', 'd', 'e']);
  });
  it('ignores columns not in the list', () => {
    expect(numericRows(rows, ['lng']).length).toBe(4);
  });
  it('returns empty when a column is absent everywhere', () => {
    expect(numericRows(rows, ['missing']).length).toBe(0);
  });
});
