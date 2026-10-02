// ============================================================
// Analysis Recommendations
// ============================================================
// Inspects a dataset's columns (names + inferred types) and suggests
// standard analyses, each mapped to an existing node type with a
// ready-to-run config preset. Pure and unit-testable (uses the shared
// statistics core only for the data-driven K suggestion).
// ============================================================

import { tamKayitlar, standartlastir, kMeans, silhouette, karistir, tohumluUretec } from './istatistik';

const K_ORNEKLEM = 400;

/**
 * K-Means için K'yı VERİDEN seçer: 2..8 denenir, silhouette'i en yüksek olan
 * önerilir — kümeleme düğümüyle aynı uzayda (standartlaştırılmış, tohum 42),
 * belirlenimci örneklemde. Kullanıcı geri bildirimi (3 Tem 2026): "K değeri
 * hep 3 öneriliyor, veriye göre değişmeli" — öneri sabit k: 3 idi.
 */
export function kOner(rows: Record<string, unknown>[], feats: string[]): { k: number; skor: number | null; kMaks: number } {
  const { matris } = tamKayitlar(rows, feats);
  if (matris.length < 6) return { k: 3, skor: null, kMaks: 0 };
  const orneklem = matris.length > K_ORNEKLEM ? karistir(matris, tohumluUretec(42)).slice(0, K_ORNEKLEM) : matris;
  const { Z } = standartlastir(orneklem);
  const kMaks = Math.min(8, orneklem.length - 1);
  let en: { k: number; skor: number | null } = { k: 3, skor: null };
  for (let k = 2; k <= kMaks; k++) {
    const { skor } = silhouette(Z, kMeans(Z, k, { nInit: 3, maksIter: 100, tohum: 42 }).etiketler, { tohum: 42 });
    if (skor !== null && (en.skor === null || skor > en.skor + 1e-9)) en = { k, skor };
  }
  return { ...en, kMaks };
}

export type ColumnType =
  | 'numeric'
  | 'categorical'
  | 'datetime'
  | 'boolean'
  | 'text'      // free text / list-like (contains delimiters)
  | 'id'
  | 'empty';

export interface ColumnProfile {
  name: string;
  type: ColumnType;
  distinct: number;
  fillRate: number; // 0..1 non-empty ratio
  isLatLng?: 'lat' | 'lng';
  isListLike?: boolean;
}

export interface Recommendation {
  nodeType: string;
  title: string;
  reason: string;
  priority: number;
  config: Record<string, unknown>;
}

const DATE_NAME = /(date|time|timestamp|datetime|tarih|zaman|created|updated)/i;
// Koordinat sütunu adları SÖZCÜK düzeyinde eşleşir, tam eşleşme değil.
//
// Önceki hâli `/^(lat|latitude|enlem)$/i` idi ve gerçek kolluk verisindeki
// "Koordinat Enlem" / "Koordinat Boylam" başlıklarını KAÇIRIYORDU: tespit
// olmayınca Coğrafi Hotspot önerisi hiç üretilmiyor, düğüm de
// latColumn/lngColumn boş diye hata veriyordu.
//
// Alt dize aramak da yanlış olurdu ("plate" içinde "lat" var). Bu yüzden ad
// sözcüklere bölünür ve HER SÖZCÜK tam olarak sınanır.
const LAT_SOZCUK = new Set(['lat', 'lattitude', 'latitude', 'enlem', 'yenlem']);
const LNG_SOZCUK = new Set([
  'lng', 'lon', 'long', 'longitude', 'boylam', 'xboylam',
]);

/**
 * Sütun adını karşılaştırılabilir sözcüklere böler.
 *
 * Türkçe tuzağı: "İ".toLowerCase() birleşik nokta üretir (i + U+0307);
 * birleştirici işaretler temizlenmezse "İl Enlem" gibi başlıklar eşleşmez.
 */
function adSozcukleri(ad: string): string[] {
  return ad
    .normalize('NFKD')
    .replace(/[̀-ͯ]/g, '')
    .toLowerCase()
    .split(/[^a-z0-9]+/)
    .filter(Boolean);
}

const latMi = (ad: string) => adSozcukleri(ad).some((s) => LAT_SOZCUK.has(s));
const lngMi = (ad: string) => adSozcukleri(ad).some((s) => LNG_SOZCUK.has(s));
const ID_NAME = /(^id$|_id$|kimlik|tc_?kimlik)/i;

function isNumericValue(v: unknown): boolean {
  if (typeof v === 'number') return Number.isFinite(v);
  if (typeof v === 'string') {
    const t = v.trim();
    if (t === '') return false;
    return !Number.isNaN(Number(t));
  }
  return false;
}

function isDateValue(v: unknown): boolean {
  if (typeof v !== 'string') return false;
  const t = v.trim();
  if (t.length < 6) return false;
  // Avoid treating plain integers as dates.
  if (/^\d+(\.\d+)?$/.test(t)) return false;
  return !Number.isNaN(Date.parse(t));
}

/** Infer a profile for each column from a sample of rows. */
export function profileColumns(
  columns: string[],
  rows: Record<string, unknown>[],
): ColumnProfile[] {
  const sample = rows.slice(0, 500);
  return columns.map((name) => {
    const values = sample.map((r) => r[name]);
    const nonEmpty = values.filter((v) => v !== null && v !== undefined && v !== '');
    const fillRate = sample.length ? nonEmpty.length / sample.length : 0;
    const distinct = new Set(nonEmpty.map((v) => String(v))).size;

    if (nonEmpty.length === 0) {
      return { name, type: 'empty' as ColumnType, distinct: 0, fillRate: 0 };
    }

    const numericRatio = nonEmpty.filter(isNumericValue).length / nonEmpty.length;
    const dateRatio = nonEmpty.filter(isDateValue).length / nonEmpty.length;
    const listLike =
      nonEmpty.filter((v) => typeof v === 'string' && /[,;|]/.test(v)).length /
        nonEmpty.length >
      0.5;

    let type: ColumnType;
    let isLatLng: 'lat' | 'lng' | undefined;

    if (ID_NAME.test(name) && (distinct === nonEmpty.length || numericRatio > 0.9)) {
      type = 'id';
    } else if (dateRatio > 0.7 || (DATE_NAME.test(name) && dateRatio > 0.3)) {
      type = 'datetime';
    } else if (numericRatio > 0.8) {
      type = 'numeric';
      // Boylam ÖNCE sınanır: "long" hem uzunluk hem boylam çağrışımı taşır,
      // ama "lat" hiçbir boylam adında geçmez — bu sıra yanlış eşleşmeyi azaltır.
      if (lngMi(name)) isLatLng = 'lng';
      else if (latMi(name)) isLatLng = 'lat';
    } else if (
      distinct === 2 &&
      nonEmpty.every((v) => /^(true|false|0|1|yes|no|evet|hayir)$/i.test(String(v)))
    ) {
      type = 'boolean';
    } else if (listLike) {
      type = 'text';
    } else if (distinct <= 50 && distinct / nonEmpty.length < 0.5) {
      type = 'categorical';
    } else {
      type = 'text';
    }

    return { name, type, distinct, fillRate, isLatLng, isListLike: listLike };
  });
}

/**
 * Produce ranked analysis recommendations for a dataset. Each recommendation
 * maps to an existing node type with a config preset wired to real columns.
 */
export function recommendAnalyses(
  columns: string[],
  rows: Record<string, unknown>[],
): Recommendation[] {
  const profiles = profileColumns(columns, rows);
  const numeric = profiles.filter((p) => p.type === 'numeric');
  const numericNames = numeric.map((p) => p.name);
  const categorical = profiles.filter((p) => p.type === 'categorical');
  const datetime = profiles.filter((p) => p.type === 'datetime');
  const listCols = profiles.filter((p) => p.type === 'text' && p.isListLike);
  const lat = profiles.find((p) => p.isLatLng === 'lat');
  const lng = profiles.find((p) => p.isLatLng === 'lng');

  const recs: Recommendation[] = [];

  // Always: data health check first.
  recs.push({
    nodeType: 'data_quality',
    title: 'Data Quality Check',
    reason: 'Start here: profile missing values, types and outliers before analysis.',
    priority: 100,
    config: { columns: '' },
  });

  // If any column has missing cells, clean before raw data reaches analysis.
  const incomplete = profiles.filter((p) => p.fillRate < 1);
  if (incomplete.length > 0) {
    recs.push({
      nodeType: 'data_clean',
      title: 'Data Cleaning',
      reason: `${incomplete.length} column(s) have missing values — clean (drop or impute) before analysis.`,
      priority: 95,
      config: { columns: '', strategy: 'drop_rows' },
    });
  }

  if (numericNames.length >= 1) {
    recs.push({
      nodeType: 'statistics',
      title: 'Descriptive Statistics',
      reason: `Summarize ${numericNames.length} numeric column(s): mean, std, min/max.`,
      priority: 90,
      config: { columns: numericNames.join(','), stats: ['count', 'mean', 'std', 'min', 'max'] },
    });
  }

  if (numericNames.length >= 2) {
    recs.push({
      nodeType: 'correlation',
      title: 'Correlation Matrix',
      reason: `${numericNames.length} numeric columns — measure pairwise relationships (Pearson).`,
      priority: 85,
      config: { columns: numericNames.join(','), method: 'pearson' },
    });
  }

  if (numericNames.length >= 1) {
    recs.push({
      nodeType: 'anomaly_detection',
      title: 'Anomaly Detection',
      reason: `Flag outliers in ${numericNames.slice(0, 3).join(', ')} using the IQR method.`,
      priority: 70,
      config: { columns: numericNames.join(','), method: 'iqr', threshold: 1.5 },
    });
  }

  if (numericNames.length >= 2) {
    const feats = numericNames.slice(0, 3);
    const oneri = kOner(rows, feats);
    recs.push({
      nodeType: 'clustering',
      title: 'K-Means Clustering',
      reason: oneri.skor === null
        ? `Segment rows into groups using ${feats.join(', ')} (too few complete rows to choose K from the data; default K=3).`
        : `Segment rows into groups using ${feats.join(', ')}. K=${oneri.k} chosen from the data (best silhouette ${oneri.skor.toFixed(2)} among K=2–${oneri.kMaks}).`,
      priority: 65,
      config: { features: feats.join(','), k: oneri.k, maxIterations: 100 },
    });

    // Regression: predict the last numeric column from the others.
    const target = numericNames[numericNames.length - 1];
    const features = numericNames.slice(0, -1);
    recs.push({
      nodeType: 'linear_regression',
      title: 'Linear Regression',
      reason: `Predict "${target}" from ${features.join(', ')}.`,
      priority: 60,
      config: { target, features: features.join(','), testSize: 20 },
    });
  }

  if (categorical.length >= 1 && numericNames.length >= 1) {
    const group = categorical[0].name;
    recs.push({
      nodeType: 'aggregate',
      title: 'Group & Aggregate',
      reason: `Summarize numeric values by "${group}" (${categorical[0].distinct} groups).`,
      priority: 55,
      config: { groupBy: group, aggregations: ['COUNT', 'AVG', 'SUM'] },
    });
  }

  if (listCols.length >= 1) {
    recs.push({
      nodeType: 'association_rules',
      title: 'Association Rules',
      reason: `"${listCols[0].name}" looks list-like — run market-basket analysis.`,
      priority: 50,
      config: { itemsColumn: listCols[0].name, minSupport: 0.05, minConfidence: 0.5 },
    });
  }

  if (datetime.length >= 1) {
    recs.push({
      nodeType: 'temporal_pattern',
      title: 'Temporal Pattern',
      reason: `Analyze event patterns over time using "${datetime[0].name}".`,
      priority: 45,
      config: {
        timeColumn: datetime[0].name,
        categoryColumn: categorical[0]?.name ?? '',
        bucket: 'day',
      },
    });
  }

  if (lat && lng) {
    recs.push({
      nodeType: 'geo_hotspot',
      title: 'Geographic Hotspot',
      reason: `Lat/Lng columns detected — map density hotspots.`,
      priority: 45,
      config: { latColumn: lat.name, lngColumn: lng.name, gridSize: 0.01 },
    });
  }

  // Natural-language interpretation via the local agent.
  recs.push({
    nodeType: 'agent_insight',
    title: 'AI Summary (Agent)',
    reason: 'Get a plain-language interpretation of this data from the local agent.',
    priority: 40,
    config: {
      question: 'Summarize the key findings in this data.',
      tone: 'concise',
      language: 'English',
    },
  });

  // Always offer a visualization.
  recs.push({
    nodeType: 'chart',
    title: 'Visualize Results',
    reason: 'Plot the data as a bar/line/scatter chart.',
    priority: 20,
    config: {
      chartType: 'bar',
      xColumn: categorical[0]?.name ?? columns[0] ?? '',
      yColumn: numericNames[0] ?? '',
    },
  });

  return recs.sort((a, b) => b.priority - a.priority);
}
