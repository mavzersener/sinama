import { describe, it, expect } from 'vitest';
import { profileColumns, recommendAnalyses } from '../src/engine/recommendations';

function types(rows: Record<string, unknown>[]) {
  const cols = Object.keys(rows[0]);
  return Object.fromEntries(profileColumns(cols, rows).map((p) => [p.name, p.type]));
}

describe('profileColumns', () => {
  it('classifies numeric, categorical, id and datetime columns', () => {
    const rows = Array.from({ length: 30 }, (_, i) => ({
      id: i + 1,
      city: ['A', 'B', 'C'][i % 3],
      income: 1000 + i * 10,
      created: `2026-0${(i % 9) + 1}-15`,
    }));
    const t = types(rows);
    expect(t.id).toBe('id');
    expect(t.city).toBe('categorical');
    expect(t.income).toBe('numeric');
    expect(t.created).toBe('datetime');
  });

  it('detects list-like text columns', () => {
    const rows = Array.from({ length: 10 }, () => ({ items: 'milk,bread,eggs' }));
    expect(types(rows).items).toBe('text');
  });

  it('detects lat/lng numeric columns', () => {
    const rows = Array.from({ length: 10 }, (_, i) => ({
      latitude: 41.0 + i * 0.01,
      longitude: 28.9 + i * 0.01,
    }));
    const profiles = profileColumns(['latitude', 'longitude'], rows);
    expect(profiles.find((p) => p.name === 'latitude')?.isLatLng).toBe('lat');
    expect(profiles.find((p) => p.name === 'longitude')?.isLatLng).toBe('lng');
  });
});

describe('recommendAnalyses', () => {
  const numericRows = Array.from({ length: 40 }, (_, i) => ({
    age: 20 + (i % 40),
    income: 30000 + i * 500,
    score: (i * 7) % 100,
    city: ['A', 'B', 'C'][i % 3],
  }));

  it('always recommends data quality first', () => {
    const recs = recommendAnalyses(Object.keys(numericRows[0]), numericRows);
    expect(recs[0].nodeType).toBe('data_quality');
  });

  it('recommends correlation, clustering and regression for multi-numeric data', () => {
    const recs = recommendAnalyses(Object.keys(numericRows[0]), numericRows);
    const kinds = recs.map((r) => r.nodeType);
    expect(kinds).toContain('correlation');
    expect(kinds).toContain('clustering');
    expect(kinds).toContain('linear_regression');
    expect(kinds).toContain('statistics');
    expect(kinds).toContain('anomaly_detection');
  });

  it('presets correlation config with the numeric columns', () => {
    const recs = recommendAnalyses(Object.keys(numericRows[0]), numericRows);
    const corr = recs.find((r) => r.nodeType === 'correlation');
    expect(corr?.config.columns).toContain('age');
    expect(corr?.config.columns).toContain('income');
  });

  it('recommends group & aggregate when a categorical + numeric exist', () => {
    const recs = recommendAnalyses(Object.keys(numericRows[0]), numericRows);
    const agg = recs.find((r) => r.nodeType === 'aggregate');
    expect(agg).toBeDefined();
    expect(agg?.config.groupBy).toBe('city');
  });

  it('recommends association rules for list-like columns', () => {
    const rows = Array.from({ length: 20 }, () => ({ basket: 'a,b,c' }));
    const recs = recommendAnalyses(['basket'], rows);
    expect(recs.some((r) => r.nodeType === 'association_rules')).toBe(true);
  });

  it('recommends geo hotspot when lat/lng present', () => {
    const rows = Array.from({ length: 20 }, (_, i) => ({
      latitude: 41 + i * 0.01,
      longitude: 28.9 + i * 0.01,
    }));
    const recs = recommendAnalyses(['latitude', 'longitude'], rows);
    const geo = recs.find((r) => r.nodeType === 'geo_hotspot');
    expect(geo?.config.latColumn).toBe('latitude');
  });

  it('does not recommend correlation with only one numeric column', () => {
    const rows = Array.from({ length: 10 }, (_, i) => ({ x: i, name: `n${i}` }));
    const recs = recommendAnalyses(['x', 'name'], rows);
    expect(recs.some((r) => r.nodeType === 'correlation')).toBe(false);
  });

  it('recommends data cleaning (before analysis) when columns have missing cells', () => {
    const rows = Array.from({ length: 10 }, (_, i) => ({ a: i % 3 === 0 ? '' : i, b: i }));
    const recs = recommendAnalyses(['a', 'b'], rows);
    const clean = recs.find((r) => r.nodeType === 'data_clean');
    expect(clean).toBeDefined();
    expect(clean!.priority).toBeGreaterThan(90); // after data_quality, before analyses
  });

  it('does not recommend data cleaning when all columns are complete', () => {
    const rows = Array.from({ length: 10 }, (_, i) => ({ a: i, b: i * 2 }));
    const recs = recommendAnalyses(['a', 'b'], rows);
    expect(recs.some((r) => r.nodeType === 'data_clean')).toBe(false);
  });
});
