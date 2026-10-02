/* eslint-disable @typescript-eslint/no-explicit-any -- test, motorun dinamik sonuç JSON'unu derinlemesine okur */
import { describe, it, expect, beforeAll } from 'vitest';
import { execFileSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import Papa from 'papaparse';
import type { Node, Edge } from '@xyflow/react';
import { executeNode, getExecutionOrder, type ExecutionResult } from '../src/engine/executionEngine';
import { pythonBetigiUret } from '../src/lib/pythonExport';
import { tohumluUretec } from '../src/engine/istatistik';
import type { NodeData } from '../src/store/useStore';

/**
 * ORACLE (farklılık) testi: tarayıcı motoru ↔ pandas/scikit-learn.
 *
 * Aynı veri + aynı akış iki kez koşar: (1) JS motoru, (2) pythonExport'un
 * ürettiği betik. Sayılar tolerans içinde aynı olmalı. Matris testi
 * ön-kontrol kapılarını sınar, sayısal doğruluğu DEĞİL — Number(null)===0
 * ve x/y'yi ayrı süzme hataları o yüzden aylarca görünmedi. Bu katman o
 * sınıfı yakalar: veri seti bilerek eksik hücre, bağlı değer ve aykırı
 * değer taşır.
 *
 * Python: ML_PY (yoksa conda 'mlservice'). Bulunamazsa test atlanır ve
 * bunu yazar; ORACLE_ZORUNLU=1 iken (yerel kapı) atlamak yerine BAŞARISIZ olur.
 */

function pythonBul(): string | null {
  const adaylar = [
    process.env.ML_PY,
    path.join(os.homedir(), 'anaconda3', 'envs', 'mlservice', 'python.exe'),
    path.join(os.homedir(), 'miniconda3', 'envs', 'mlservice', 'python.exe'),
  ].filter((p): p is string => !!p);
  for (const p of adaylar) {
    try {
      execFileSync(p, ['-c', 'import pandas, sklearn, scipy'], { stdio: 'ignore', timeout: 60_000 });
      return p;
    } catch { /* sıradaki aday */ }
  }
  return null;
}

const PY = pythonBul();
if (!PY) {
  const mesaj = '[oracle] pandas/sklearn kurulu Python bulunamadı (ML_PY) — oracle testi atlandı';
  if (process.env.ORACLE_ZORUNLU === '1') throw new Error(mesaj + ' ve ORACLE_ZORUNLU=1');
  console.log(mesaj);
}

// ---------------------------------------------------------------- veri seti

function veriSeti(): Record<string, unknown>[] {
  const rng = tohumluUretec(2026);
  const gauss = () => Math.sqrt(-2 * Math.log(1 - rng())) * Math.cos(2 * Math.PI * rng());
  const merkez = [[0, 0], [8, 8], [0, 10]];
  return Array.from({ length: 240 }, (_, i) => {
    const [cx, cy] = merkez[i % 3];
    const x1 = cx + gauss() * 0.8;
    const x2 = cy + gauss() * 0.8;
    const yTemiz = 3 + 2 * x1 - 1.5 * x2 + gauss() * 0.5;
    const y = i === 100 ? 500 : yTemiz; // bilinçli aykırı değer
    const sinif = x1 > 4 ? 'yuksek' : 'dusuk';
    return {
      bolge: ['A', 'B', 'C', 'D'][i % 4],
      x1: i % 17 === 5 ? '' : x1.toFixed(4),
      x2: i % 19 === 7 ? '' : x2.toFixed(4),
      y: i % 23 === 11 ? '' : y.toFixed(4),
      // Aykırısız hedef: CV'de tek aykırı, hangi katmana düştüğüne göre o
      // katmanın R²'sini çökertir; JS ve numpy farklı karıştırdığından
      // ortalamalar karşılaştırılamaz hale gelir (motor hatası değil).
      y2: i % 23 === 11 ? '' : yTemiz.toFixed(4),
      skor: Math.round(y / 3), // bol bağlı değer (Kendall/Spearman)
      gercek: i % 31 === 3 ? '' : sinif,
      tahmin: i % 31 === 3 || i % 29 === 4 ? '' : (i % 9 === 0 ? (sinif === 'yuksek' ? 'dusuk' : 'yuksek') : sinif),
    };
  });
}

// ---------------------------------------------------------------- akış

const ANALIZLER: Array<[string, string, Record<string, unknown>]> = [
  ['ist', 'statistics', { columns: 'x1,x2,y', stats: ['count', 'mean', 'median', 'std', 'min', 'max'] }],
  ['kor_p', 'correlation', { columns: 'x1,x2,y,skor', method: 'pearson' }],
  ['kor_s', 'correlation', { columns: 'x1,x2,y,skor', method: 'spearman' }],
  ['kor_k', 'correlation', { columns: 'x1,x2,y,skor', method: 'kendall' }],
  ['reg', 'linear_regression', { target: 'y', features: 'x1,x2', testSize: 0 }],
  ['iqr', 'anomaly_detection', { columns: 'x1,x2,y', method: 'iqr', threshold: 1.5 }],
  ['z', 'anomaly_detection', { columns: 'x1,x2,y', method: 'zscore', threshold: 3 }],
  ['mv', 'model_validation', { actualColumn: 'gercek', predictedColumn: 'tahmin' }],
  ['km', 'clustering', { features: 'x1,x2', k: 3, maxIterations: 100, standardize: true }],
  ['cv', 'cross_validation', { target: 'y2', features: 'x1,x2', k: 5, metric: 'r2' }],
];

const dugum = (id: string, type: string, config: Record<string, unknown>) =>
  ({ id, type: 'custom', position: { x: 0, y: 0 }, data: { type, label: id, config } }) as unknown as Node<NodeData>;

type Sozluk = Record<string, any>;

describe.skipIf(!PY)('oracle: JS motoru ↔ pandas/scikit-learn', () => {
  const js = new Map<string, Sozluk>();
  const py = new Map<string, Sozluk>();

  beforeAll(async () => {
    const dizin = fs.mkdtempSync(path.join(os.tmpdir(), 'dataflow-oracle-'));
    try {
      const csv = Papa.unparse(veriSeti());
      fs.writeFileSync(path.join(dizin, 'oracle.csv'), csv, 'utf8');
      // Uygulamanın PropertyPanel ayarlarıyla aynı ayrıştırma.
      const cozum = Papa.parse<Record<string, unknown>>(csv, { header: true, delimiter: '', dynamicTyping: true, skipEmptyLines: true });

      const kaynak = dugum('src', 'csv_source', {
        filename: 'oracle.csv', delimiter: ',', hasHeader: true,
        _uploadedData: { rows: cozum.data, columns: cozum.meta.fields, filename: 'oracle.csv' },
      });
      const nodes = [kaynak, ...ANALIZLER.map(([id, t, c]) => dugum(id, t, c))];
      const edges = ANALIZLER.map(([id]) => ({ id: `e_${id}`, source: 'src', target: id, sourceHandle: 'output', targetHandle: 'input' })) as Edge[];

      // (1) JS motoru
      const sonuclar = new Map<string, ExecutionResult>();
      for (const id of getExecutionOrder(nodes, edges)) {
        const r = await executeNode(nodes.find((n) => n.id === id)!, edges, sonuclar);
        if (r.status !== 'success') throw new Error(`JS ${id}: ${r.error}`);
        sonuclar.set(id, r);
        js.set(id, r.data as Sozluk);
      }

      // (2) Dışa aktarılan betik
      const { kod, desteklenmeyen } = pythonBetigiUret(nodes, edges);
      expect(desteklenmeyen).toEqual([]);
      fs.writeFileSync(path.join(dizin, 'akis.py'), kod, 'utf8');
      execFileSync(PY!, ['akis.py'], {
        cwd: dizin, timeout: 180_000, stdio: 'pipe',
        env: { ...process.env, PYTHONUTF8: '1', PYTHONWARNINGS: 'ignore' },
      });
      const sira = getExecutionOrder(nodes, edges);
      const dosyalar = fs.readdirSync(path.join(dizin, 'cikti'));
      sira.forEach((id, i) => {
        const dosya = dosyalar.find((f) => f.startsWith(`dugum_${i + 1}_`));
        if (!dosya) return;
        const ham = fs.readFileSync(path.join(dizin, 'cikti', dosya), 'utf8');
        py.set(id, JSON.parse(ham.replace(/\bNaN\b/g, 'null')));
      });
    } finally {
      fs.rmSync(dizin, { recursive: true, force: true });
    }
  }, 240_000);

  const yakin = (a: number | null | undefined, b: number | null | undefined, tol: number, ad: string) => {
    expect(a, `${ad}: JS değeri yok`).not.toBeNull();
    expect(b, `${ad}: Python değeri yok`).not.toBeNull();
    expect(Math.abs((a as number) - (b as number)), `${ad}: JS ${a} ↔ Python ${b}`).toBeLessThanOrEqual(tol);
  };

  it('betimsel istatistik (count/mean/median/std/min/max)', () => {
    for (const col of ['x1', 'x2', 'y']) {
      for (const st of ['count', 'mean', 'median', 'std', 'min', 'max']) {
        yakin(js.get('ist')!.stats[col][st], py.get('ist')![col][st], 1e-3, `${col}.${st}`);
      }
    }
  });

  it('korelasyon: Pearson, Spearman, Kendall tau-b (çift bazlı eksik atma)', () => {
    for (const id of ['kor_p', 'kor_s', 'kor_k']) {
      const cols = js.get(id)!.columns as string[];
      for (const a of cols) for (const b of cols) {
        yakin(js.get(id)!.matrix[a][b], py.get(id)!.matrix[a][b], 1e-3, `${id} ${a}×${b}`);
      }
    }
  });

  it('çok değişkenli regresyon: katsayılar, kesişim, R², MSE, n', () => {
    const j = js.get('reg')!;
    const p = py.get('reg')!;
    for (const c of j.coefficients) yakin(c.coefficient, p.coefficients[c.feature], 1e-3, `katsayı ${c.feature}`);
    yakin(j.intercept, p.intercept, 1e-3, 'kesişim');
    yakin(j.r_squared, p.r_squared, 1e-3, 'R²');
    yakin(j.mse, p.mse, 1e-2, 'MSE');
    expect(j.sample_size).toBe(p.sample_size);
  });

  it('aykırı değer: IQR ve z-skoru, satır bazında ve sütun bazında sayılar', () => {
    for (const id of ['iqr', 'z']) {
      expect(js.get(id)!.anomalies_detected, id).toBe(py.get(id)!.aykiri_sayisi);
      expect(js.get(id)!.kolon_bazinda, id).toEqual(py.get(id)!.kolon_bazinda);
    }
    // Bilinçli aykırı (y=500) iki yöntemde de yakalanır.
    expect(js.get('z')!.kolon_bazinda.y).toBeGreaterThanOrEqual(1);
  });

  it('model doğrulama: accuracy ve örneklem (boş etiketler dışlanır)', () => {
    yakin(js.get('mv')!.accuracy, py.get('mv')!.report.accuracy, 1e-4, 'accuracy');
    expect(js.get('mv')!.total_samples).toBe(py.get('mv')!.sample_size);
  });

  it('K-Means: aynı bölüntü (boyutlar, merkezler, silhouette)', () => {
    const j = js.get('km')!;
    const p = py.get('km')!;
    const boy = (x: Sozluk) => (x.clusters as Array<{ size: number }>).map((c) => c.size).sort((a, b) => b - a);
    expect(boy(j)).toEqual(boy(p));
    for (const jc of j.clusters as Array<{ centroid: number[] }>) {
      const enYakin = Math.min(...(p.clusters as Array<{ centroid: number[] }>).map((pc) =>
        Math.hypot(...pc.centroid.map((v, d) => v - jc.centroid[d]))));
      expect(enYakin, `merkez ${jc.centroid}`).toBeLessThan(0.05);
    }
    yakin(j.silhouette_score, p.silhouette_score, 1e-3, 'silhouette');
    expect(j.sample_size).toBe(p.sample_size);
  });

  it('çapraz doğrulama: ortalama R² (farklı karıştırma, gevşek tolerans)', () => {
    yakin(js.get('cv')!.avg_r2, py.get('cv')!.ortalama, 0.05, 'CV R²');
    expect(js.get('cv')!.total_samples).toBe(py.get('cv')!.total_samples);
  });
});
