// Dönüştürücü düğümler: filtre, alan ekleme, toplama, sıralama, birleştirme, blok grup, temizlik, tekilleştirme.
// (executionEngine.ts'den bölündü — Faz 4.)

import { ifadeyiCoz, ifadeyiDegerlendir, type IfadeDugumu } from '../ifade';
import type { Edge } from '@xyflow/react';
import { eksikMi, sayiCoz, sayisalSutunlar, sutunDegerleri, ortalama, stdSapma, enKucukBuyuk } from '../istatistik';
import { akisVerisi, extractRows, extractColumns, csvAlan, makeResult, makeError, type ExecutionResult } from '../sonuc';

// ---- Processing Nodes (REAL algorithms) ----

export function execFilter(nodeId: string, config: Record<string, unknown>, inputData: Record<string, unknown> | null): ExecutionResult {
  const rows = extractRows(inputData);
  const column = config.column as string;
  const condition = config.condition as string;
  const value = config.value as string;
  if (!column) return makeError(nodeId, 'filter', 'Column not specified');
  // Bilinmeyen koşul eskiden `default: return true` ile TÜM satırları sessizce
  // geçiriyordu (bozuk/eski kayıtlı akış); artık açıkça hata.
  const KOSULLAR = ['equals', 'not_equals', 'contains', 'starts_with', 'greater_than', 'less_than', 'is_null', 'not_null'];
  if (!KOSULLAR.includes(condition)) {
    return makeError(nodeId, 'filter', `Bilinmeyen filtre koşulu: "${String(condition)}" (geçerli: ${KOSULLAR.join(', ')})`);
  }
  // Sayı karşılaştırması tek çözücüyle (sayiCoz): "1.234,5" ve "%12" gibi
  // biçimler Number() ile NaN olup satırı sessizce düşürüyordu.
  const valNum = sayiCoz(value);

  const filtered = rows.filter((row) => {
    const cell = row[column];
    const cellStr = String(cell ?? '').toLowerCase();
    const valStr = String(value ?? '').toLowerCase();
    const cellNum = sayiCoz(cell);
    switch (condition) {
      case 'equals': return cellStr === valStr;
      case 'not_equals': return cellStr !== valStr;
      case 'contains': return cellStr.includes(valStr);
      case 'starts_with': return cellStr.startsWith(valStr);
      case 'greater_than': return cellNum !== null && valNum !== null && cellNum > valNum;
      case 'less_than': return cellNum !== null && valNum !== null && cellNum < valNum;
      case 'is_null': return cell === null || cell === undefined;
      case 'not_null': return cell !== null && cell !== undefined;
      default: return true;
    }
  });

  const columns = extractColumns(inputData);
  return makeResult(nodeId, 'filter', { rows: filtered, columns, condition: `${column} ${condition} ${value}` }, filtered.length, columns, filtered.slice(0, 10));
}

export function execExtendField(nodeId: string, config: Record<string, unknown>, inputData: Record<string, unknown> | null): ExecutionResult {
  const rows = extractRows(inputData);
  const newCol = config.newColumn as string;
  if (!newCol) return makeError(nodeId, 'extend_field', 'New column name required');

  const expression = (config.expression as string) ?? '';
  if (!expression.trim()) return makeError(nodeId, 'extend_field', 'Expression required');
  if (rows.length === 0) return makeError(nodeId, 'extend_field', 'No input rows');

  // İfade bir KEZ ayrıştırılır (güvenli dil, bkz. engine/ifade.ts): eskiden
  // `new Function` ile JS olarak çalışıyordu — paylaşılan bir akışın ifadesi
  // kullanıcının tarayıcısında keyfi kod çalıştırabilirdi. Bilinmeyen sütun ve
  // işlev satırlar işlenmeden, sebebiyle bildirilir. (Daha önceki metin
  // ikamesi metin sütunlarında sessizce '' üretiyordu.)
  const columns = extractColumns(inputData);
  let agac: IfadeDugumu;
  try {
    agac = ifadeyiCoz(expression, columns);
  } catch (err) {
    return makeError(nodeId, 'extend_field', `Expression could not be compiled: ${(err as Error).message}`);
  }

  const extended: Record<string, unknown>[] = [];
  for (let i = 0; i < rows.length; i++) {
    let value: unknown;
    try {
      value = ifadeyiDegerlendir(agac, rows[i]);
    } catch (err) {
      // SESSİZ '' YOK: ilk hatalı satırda dur ve sebebini söyle.
      return makeError(nodeId, 'extend_field', `Expression failed on row ${i + 1}: ${(err as Error).message}`);
    }
    extended.push({
      ...rows[i],
      [newCol]: typeof value === 'number' ? Number(value.toFixed(4)) : String(value ?? ''),
    });
  }

  const outColumns = [...columns, newCol];
  return makeResult(nodeId, 'extend_field', { rows: extended, columns: outColumns, newColumn: newCol, expression }, extended.length, outColumns, extended.slice(0, 10));
}

export function execAggregate(nodeId: string, config: Record<string, unknown>, inputData: Record<string, unknown> | null): ExecutionResult {
  const rows = extractRows(inputData);
  const groupBy = config.groupBy as string;
  const aggregations = (config.aggregations as string[]) || ['COUNT'];
  if (!groupBy) return makeError(nodeId, 'aggregate', 'Group by column required');

  // Group rows
  const groups: Record<string, Record<string, unknown>[]> = {};
  rows.forEach((row) => {
    const key = String(row[groupBy] ?? 'null');
    (groups[key] = groups[key] || []).push(row);
  });

  // Değer sütunu: kullanıcı seçtiyse o; yoksa ilk sayısal sütun (hangisi
  // olduğu sonuçta yazılır — eski motor sessizce seçiyordu).
  const allColumns = extractColumns(inputData);
  const secilen = (config.valueColumn as string) || '';
  const uyarilar: string[] = [];
  let aggCol: string | null = null;
  const sayisalIstek = aggregations.some((a) => a !== 'COUNT');
  if (secilen) {
    if (sayisalSutunlar(rows, [secilen]).length) aggCol = secilen;
    else uyarilar.push(`Değer sütunu "${secilen}" sayısal değil; yalnız COUNT hesaplandı.`);
  } else if (sayisalIstek) {
    aggCol = sayisalSutunlar(rows, allColumns.filter((c) => c !== groupBy))[0] ?? null;
    if (aggCol) uyarilar.push(`Değer sütunu seçilmedi; ilk sayısal sütun kullanıldı: ${aggCol}.`);
    else uyarilar.push('Sayısal sütun yok; yalnız COUNT hesaplandı.');
  }
  if (groups['null']) {
    uyarilar.push(`${groups['null'].length} satırda "${groupBy}" boş; "null" grubunda toplandı.`);
  }

  let eksikDeger = 0;
  const result = Object.entries(groups).map(([groupKey, groupRows]) => {
    const out: Record<string, unknown> = { [groupBy]: groupKey, count: groupRows.length };
    if (!aggCol) return out;
    const { degerler: values, eksik, gecersiz } = sutunDegerleri(groupRows, aggCol);
    eksikDeger += eksik + gecersiz;
    const mm = values.length ? enKucukBuyuk(values) : null;

    aggregations.forEach((agg) => {
      switch (agg) {
        case 'SUM': out.sum = values.length ? values.reduce((a, b) => a + b, 0) : null; break;
        case 'AVG': out.avg = values.length ? ortalama(values) : null; break;
        case 'MAX': out.max = mm ? mm.max : null; break;
        case 'MIN': out.min = mm ? mm.min : null; break;
        case 'STDEV': out.stdev = stdSapma(values, 1); break;
      }
    });
    return out;
  });
  if (aggCol && eksikDeger > 0) {
    uyarilar.push(`"${aggCol}" sütununda ${eksikDeger} boş/sayısal olmayan hücre toplamalara katılmadı (0 sayılmadı).`);
  }

  const columns = [groupBy, 'count', ...(aggCol ? aggregations.filter((a) => a !== 'COUNT').map((a) => a.toLowerCase()) : [])];
  return makeResult(nodeId, 'aggregate', { rows: result, columns, groupBy, aggregations, deger_sutunu: aggCol, uyarilar }, result.length, columns, result.slice(0, 10));
}

export function execSort(nodeId: string, config: Record<string, unknown>, inputData: Record<string, unknown> | null): ExecutionResult {
  const rows = extractRows(inputData);
  const sortCols = csvAlan(config.columns);
  const order = config.order as string;
  if (sortCols.length === 0) return makeError(nodeId, 'sort', 'Sort columns required');

  const sorted = [...rows].sort((a, b) => {
    for (const col of sortCols) {
      const av = a[col], bv = b[col];
      if (av === bv) continue;
      const an = Number(av), bn = Number(bv);
      if (!isNaN(an) && !isNaN(bn)) {
        return order === 'desc' ? bn - an : an - bn;
      }
      return order === 'desc' ? String(bv).localeCompare(String(av)) : String(av).localeCompare(String(bv));
    }
    return 0;
  });

  const columns = extractColumns(inputData);
  return makeResult(nodeId, 'sort', { rows: sorted, columns, sortBy: sortCols, order }, sorted.length, columns, sorted.slice(0, 10));
}

export function execJoin(nodeId: string, config: Record<string, unknown>, edges: Edge[], allResults: Map<string, ExecutionResult>): ExecutionResult {
  const incoming = edges.filter((e) => e.target === nodeId);
  if (incoming.length < 2) return makeError(nodeId, 'join', 'Join requires 2 inputs');

  const leftResult = allResults.get(incoming[0].source);
  const rightResult = allResults.get(incoming[1].source);
  const leftRows = extractRows(akisVerisi(leftResult));
  const rightRows = extractRows(akisVerisi(rightResult));
  const leftKey = config.leftKey as string;
  const rightKey = config.rightKey as string;
  const joinType = config.joinType as string;

  const rightMap = new Map<string, Record<string, unknown>[]>();
  rightRows.forEach((row) => {
    const key = String(row[rightKey] ?? 'null');
    const arr = rightMap.get(key) || [];
    arr.push(row);
    rightMap.set(key, arr);
  });

  const joined: Record<string, unknown>[] = [];
  leftRows.forEach((leftRow) => {
    const key = String(leftRow[leftKey] ?? 'null');
    const matches = rightMap.get(key);
    if (matches) {
      matches.forEach((rightRow) => joined.push({ ...leftRow, ...rightRow, _join_key: key }));
    } else if (joinType === 'left' || joinType === 'full') {
      joined.push({ ...leftRow, _join_key: key });
    }
  });

  if (joinType === 'right' || joinType === 'full') {
    const leftKeys = new Set(leftRows.map((r) => String(r[leftKey] ?? 'null')));
    rightRows.forEach((rightRow) => {
      const key = String(rightRow[rightKey] ?? 'null');
      if (!leftKeys.has(key)) joined.push({ ...rightRow, _join_key: key });
    });
  }

  const columns = Array.from(new Set([...Object.keys(leftRows[0] || {}), ...Object.keys(rightRows[0] || {})]));
  return makeResult(nodeId, 'join', { rows: joined, columns, joinType, leftKey, rightKey }, joined.length, columns, joined.slice(0, 10));
}

/**
 * "Birleştirilmiş hücre" ihracını onarır.
 *
 * Excel/rapor ihraçlarında bir olayın ek kayıtları, olay sütunları BOŞ satırlar
 * olarak gelir; olay kimliği sütunlarda değil SATIR SIRASINDA saklıdır. Sütun
 * birleştirerek kimlik üretmek (tarih+yer gibi) iki tuzağa düşer: farklı olaylar
 * aynı anahtara çöker ve `ffill` bir olayın eksik değerini ÖNCEKİ olaydan
 * doldurur. Bu düğüm kimliği doğrudan blok yapısından üretir ve doldurmayı
 * blok sınırında durdurur.
 */
export function execBlockGroup(nodeId: string, config: Record<string, unknown>, inputData: Record<string, unknown> | null): ExecutionResult {
  const rows = extractRows(inputData);
  const marker = (config.markerColumn as string) || '';
  const idCol = (config.idColumn as string) || 'blok_id';
  const fillCols = csvAlan(config.fillColumns);

  if (!marker) return makeError(nodeId, 'block_group', 'Blok başlangıç sütunu gerekli');
  if (rows.length === 0) return makeError(nodeId, 'block_group', 'Girdi satırı yok');
  const srcColumns = extractColumns(inputData);
  if (!srcColumns.includes(marker)) {
    return makeError(nodeId, 'block_group', `Sütun bulunamadı: ${marker}`);
  }

  let blockIndex = 0;
  let started = false;
  let orphanRows = 0;
  let filledCells = 0;
  const carry: Record<string, unknown> = {};

  const out = rows.map((row) => {
    const o = { ...row };
    if (!isMissingCell(o[marker])) {
      blockIndex++;
      started = true;
      // Yeni blok: taşınan değerler SIFIRLANIR. Bu bloğun kendi değeri
      // eksikse boş kalır — önceki olaydan miras almaz.
      for (const c of fillCols) carry[c] = o[c];
    } else if (started) {
      for (const c of fillCols) {
        if (isMissingCell(o[c]) && !isMissingCell(carry[c])) {
          o[c] = carry[c];
          filledCells++;
        }
      }
    } else {
      // İlk blok başlamadan gelen satırlar hiçbir olaya ait değildir.
      orphanRows++;
    }
    o[idCol] = started ? `B${String(blockIndex).padStart(6, '0')}` : '';
    return o;
  });

  const columns = [...srcColumns, idCol];
  return makeResult(nodeId, 'block_group', {
    rows: out,
    columns,
    block_count: blockIndex,
    rows_total: rows.length,
    rows_before_first_block: orphanRows,
    cells_filled: filledCells,
    marker_column: marker,
    filled_columns: fillCols,
  }, out.length, columns, out.slice(0, 10));
}

/** A cell counts as missing if null/undefined or a blank/whitespace string. */
function isMissingCell(v: unknown): boolean {
  return eksikMi(v);
}

/**
 * Data Cleaning node: handle missing values before data enters analysis.
 * Strategies: drop_rows | mean | median | mode | zero | constant | ffill.
 * Optional whitespace trim and duplicate removal. Returns cleaned rows plus a
 * report of what changed (so raw data never flows straight into the pipeline).
 */
export function execDataClean(nodeId: string, config: Record<string, unknown>, inputData: Record<string, unknown> | null): ExecutionResult {
  const srcRows = extractRows(inputData);
  if (srcRows.length === 0) {
    return makeError(nodeId, 'data_clean', 'Connect a data source with rows to Data Cleaning, then run.');
  }
  const srcColumns = (inputData?.columns as string[] | undefined) ?? Object.keys(srcRows[0] ?? {});
  const targets = csvAlan(config.columns);
  const cols = targets.length ? targets : srcColumns;
  const strategy = (config.strategy as string) || 'drop_rows';
  const fillValue = (config.fillValue as string) ?? '';
  const trim = config.trimWhitespace === true || config.trimWhitespace === 'true';
  const dropDup = config.dropDuplicates === true || config.dropDuplicates === 'true';

  // Work on shallow copies; optionally trim string cells first.
  let rows = srcRows.map((r) => {
    const o = { ...r };
    if (trim) for (const k of Object.keys(o)) if (typeof o[k] === 'string') o[k] = (o[k] as string).trim();
    return o;
  });
  const before = rows.length;

  const numericVals = (col: string): number[] =>
    rows.map((r) => r[col]).filter((v) => !isMissingCell(v)).map(Number).filter((n) => Number.isFinite(n));
  const fillFor = (col: string): unknown => {
    switch (strategy) {
      case 'mean': { const v = numericVals(col); return v.length ? v.reduce((a, b) => a + b, 0) / v.length : undefined; }
      case 'median': { const v = numericVals(col).sort((a, b) => a - b); return v.length ? v[Math.floor(v.length / 2)] : undefined; }
      case 'mode': {
        const m = new Map<unknown, number>();
        for (const r of rows) { const val = r[col]; if (!isMissingCell(val)) m.set(val, (m.get(val) ?? 0) + 1); }
        let best: unknown; let bc = -1;
        for (const [k, c] of m) if (c > bc) { bc = c; best = k; }
        return best;
      }
      case 'zero': return 0;
      case 'constant': return fillValue;
      default: return undefined;
    }
  };

  const filled: Record<string, number> = {};
  let dropped = 0;

  if (strategy === 'drop_rows') {
    rows = rows.filter((r) => cols.every((c) => !isMissingCell(r[c])));
    dropped = before - rows.length;
  } else if (strategy === 'ffill') {
    const last: Record<string, unknown> = {};
    for (const r of rows) for (const c of cols) {
      if (isMissingCell(r[c])) { if (!isMissingCell(last[c])) { r[c] = last[c]; filled[c] = (filled[c] ?? 0) + 1; } }
      else last[c] = r[c];
    }
  } else {
    const fills: Record<string, unknown> = {};
    for (const c of cols) fills[c] = fillFor(c);
    for (const r of rows) for (const c of cols) {
      if (isMissingCell(r[c]) && fills[c] !== undefined) { r[c] = fills[c]; filled[c] = (filled[c] ?? 0) + 1; }
    }
  }

  if (dropDup) {
    const seen = new Set<string>();
    const out: Record<string, unknown>[] = [];
    for (const r of rows) { const k = JSON.stringify(srcColumns.map((c) => r[c])); if (!seen.has(k)) { seen.add(k); out.push(r); } }
    dropped += rows.length - out.length;
    rows = out;
  }

  const cellsFilled = Object.values(filled).reduce((a, b) => a + b, 0);
  return makeResult(nodeId, 'data_clean', {
    rows, columns: srcColumns, strategy,
    rows_before: before, rows_after: rows.length,
    rows_dropped: dropped, cells_filled: cellsFilled,
    filled_per_column: filled,
  }, rows.length, srcColumns, rows.slice(0, 10));
}

export function execDedup(nodeId: string, config: Record<string, unknown>, inputData: Record<string, unknown> | null): ExecutionResult {
  const rows = extractRows(inputData);
  const keyCols = csvAlan(config.keyColumns);
  const keep = config.keep as string;

  const seen = new Map<string, Record<string, unknown>>();
  rows.forEach((row) => {
    const key = keyCols.length > 0 ? keyCols.map((c) => String(row[c] ?? '')).join('|') : JSON.stringify(row);
    if (!seen.has(key)) seen.set(key, row);
    else if (keep === 'last') seen.set(key, row);
  });

  const deduped = Array.from(seen.values());
  const columns = extractColumns(inputData);
  return makeResult(nodeId, 'dedup', { rows: deduped, columns, removed: rows.length - deduped.length }, deduped.length, columns, deduped.slice(0, 10));
}
