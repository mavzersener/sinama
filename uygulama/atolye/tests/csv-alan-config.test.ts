import { describe, it, expect } from 'vitest';
import { executeNode } from '../src/engine/executionEngine';

type ExecArgs = Parameters<typeof executeNode>;

/**
 * Regresyon: nodeDefinitions.defaultConfig'te CSV-metin alanları (columns,
 * keyColumns, features) bir süre dizi ([]) olarak tanımlıydı; exec
 * fonksiyonları bunları `.split(',')` ile string varsayıyordu ->
 * "(config.columns || '').split is not a function" (demo akışında canlı
 * gözlendi, bkz. Data Quality düğümü). csvAlan() artık ikisini de kabul
 * ediyor; bu test hem boş dizi (eski default) hem dolu dizi (eski kayıtlı
 * workflow) şeklini her etkilenen düğüm tipi için kapatır.
 */

// 8 satır: cross_validation k=3 katlama başına en az 2 satır ister (>=6 toplam).
const upstreamRows = Array.from({ length: 8 }, (_, i) => ({
  id: i + 1,
  age: 20 + i * 5,
  income: 30000 + i * 4000,
  category: i % 2 === 0 ? 'A' : 'B',
}));

function upstream(): ExecArgs[2] {
  const m = new Map();
  m.set('src', {
    status: 'success', nodeId: 'src', nodeType: 'csv_source', timestamp: '',
    data: { columns: ['id', 'age', 'income', 'category'], rows: upstreamRows },
  });
  return m as unknown as ExecArgs[2];
}

const edges = [{ id: 'e1', source: 'src', target: 'n1' }] as unknown as ExecArgs[1];

function node(type: string, config: Record<string, unknown>): ExecArgs[0] {
  return {
    id: 'n1', type: 'custom', position: { x: 0, y: 0 },
    data: { label: type, type, category: 'Test', icon: 'Box', color: '#fff', config, status: 'idle' },
  } as unknown as ExecArgs[0];
}

describe('CSV-metin alanları dizi geldiğinde çökmemeli (csvAlan)', () => {
  // dolu: alanın gerçek analiz için yeterli sütun/satır sağlayan dizi değeri
  // (correlation >=2 sayısal sütun ister; diğerleri tek sütunla da çalışır).
  const vakalar: Array<{ type: string; alan: string; dolu: string[]; digerConfig: Record<string, unknown> }> = [
    { type: 'sort', alan: 'columns', dolu: ['age'], digerConfig: { order: 'asc' } },
    { type: 'dedup', alan: 'keyColumns', dolu: ['id'], digerConfig: { keep: 'first' } },
    { type: 'data_clean', alan: 'columns', dolu: ['age'], digerConfig: { strategy: 'drop_rows' } },
    { type: 'statistics', alan: 'columns', dolu: ['age'], digerConfig: { stats: ['count', 'mean'] } },
    { type: 'linear_regression', alan: 'features', dolu: ['age'], digerConfig: { target: 'income' } },
    { type: 'clustering', alan: 'features', dolu: ['age'], digerConfig: { k: 2, maxIterations: 10 } },
    { type: 'anomaly_detection', alan: 'columns', dolu: ['age'], digerConfig: { method: 'iqr', threshold: 1.5 } },
    { type: 'correlation', alan: 'columns', dolu: ['age', 'income'], digerConfig: { method: 'pearson' } },
    { type: 'data_quality', alan: 'columns', dolu: ['age'], digerConfig: {} },
    { type: 'cross_validation', alan: 'features', dolu: ['age'], digerConfig: { target: 'income', k: 3, metric: 'r2' } },
  ];

  for (const { type, alan, dolu, digerConfig } of vakalar) {
    it(`${type}: ${alan} boş dizi ([]) olsa da TypeError atmaz`, async () => {
      const res = await executeNode(node(type, { [alan]: [], ...digerConfig }), edges, upstream());
      expect(res.error ?? '').not.toMatch(/split is not a function/);
    });

    it(`${type}: ${alan} dolu dizi (${JSON.stringify(dolu)}) string gibi çalışır ve başarılı olur`, async () => {
      const res = await executeNode(node(type, { [alan]: dolu, ...digerConfig }), edges, upstream());
      expect(res.error ?? '').not.toMatch(/split is not a function/);
      expect(res.status).toBe('success');
    });
  }

  it('data_quality: Toolbar demo düzeltmesi sonrası gerçek config ile başarılı çalışır', async () => {
    // Toolbar.tsx demo-dq düğümünün ürettiği tam config (düzeltmeden önce
    // `columns: []` idi ve demoda canlı çöküyordu).
    const res = await executeNode(node('data_quality', { columns: '' }), edges, upstream());
    expect(res.status).toBe('success');
  });
});
