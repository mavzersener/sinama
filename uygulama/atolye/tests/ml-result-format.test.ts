import { describe, it, expect } from 'vitest';
import { isMlResult, extractMetricRows, extractImportance } from '../src/engine/mlResultFormat';

const sample = {
  algorithm: 'RandomForest-classification',
  metrics: { accuracy: 0.9123456, f1_macro: 0.8891, cv_accuracy_mean: 0.87 },
  feature_importance: { age: 0.7, income: 0.2, city: 0.1 },
};

describe('mlResultFormat', () => {
  it('detects ML results by algorithm+metrics', () => {
    expect(isMlResult(sample)).toBe(true);
    expect(isMlResult({ rows: [] })).toBe(false);
    expect(isMlResult(null)).toBe(false);
  });

  it('extracts numeric metric rows with 4-digit rounding', () => {
    const rows = extractMetricRows(sample);
    expect(rows).toContainEqual({ name: 'accuracy', value: '0.9123' });
    expect(rows.length).toBe(3);
  });

  it('sorts importance desc and honors topN', () => {
    const imp = extractImportance(sample, 2);
    expect(imp).toEqual([{ feature: 'age', value: 0.7 }, { feature: 'income', value: 0.2 }]);
  });
});
