import { describe, it, expect } from 'vitest';
import { nodeLabel, nodeDesc, categoryLabel } from '../src/i18nNodes';

describe('i18nNodes', () => {
  it('returns Turkish label/description for known nodes', () => {
    expect(nodeLabel('tr', 'csv_source', 'CSV Input')).toBe('CSV Girişi');
    expect(nodeDesc('tr', 'filter', 'x')).toContain('filtrele');
  });
  it('returns English for en lang', () => {
    expect(nodeLabel('en', 'random_forest', 'x')).toBe('Random Forest');
  });
  it('falls back to the provided default for unknown type', () => {
    expect(nodeLabel('tr', 'nonexistent_node', 'Fallback')).toBe('Fallback');
    expect(nodeDesc('en', 'nonexistent_node', 'Def')).toBe('Def');
  });
  it('translates categories and falls back to raw', () => {
    expect(categoryLabel('tr', 'Analysis')).toBe('Analiz');
    expect(categoryLabel('en', 'Kolluk Data')).toBe('Law Enforcement Data');
    expect(categoryLabel('tr', 'Unknown')).toBe('Unknown');
  });
});
