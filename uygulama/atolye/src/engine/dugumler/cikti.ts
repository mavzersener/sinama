// Çıktı düğümleri: grafik, dışa aktarma, uyarı.
// (executionEngine.ts'den bölündü — Faz 4.)

import { sayisalSutunlar, sutunDegerleri } from '../istatistik';
import { GRAFIK_AZAMI_SATIR } from '../../lib/grafikVerisi';
import { extractRows, extractColumns, makeResult, makeError, type ExecutionResult } from '../sonuc';

// ---- Output Nodes ----

export function execChart(nodeId: string, config: Record<string, unknown>, inputData: Record<string, unknown> | null, demo = false): ExecutionResult {
  const rows = extractRows(inputData);
  const baslik = String(config.title ?? '');
  return makeResult(nodeId, 'chart', {
    chartType: config.chartType,
    // Grafik ekran görüntüsü paylaşılabilir: sentetik veri başlıkta da yazar.
    title: demo ? `${baslik}${baslik ? ' ' : ''}(DEMO VERİ)` : config.title,
    rowCount: rows.length,
    // Grafik ilk GRAFIK_AZAMI_SATIR satırı çizer ve kesildiğini söyler (eskiden sessizce 20/50).
    inputData: rows.slice(0, GRAFIK_AZAMI_SATIR)
  }, rows.length);
}

/**
 * CSV hücresi: virgül, satır sonu ya da TIRNAK içeren değer tırnaklanır (eskiden
 * `"` içeren değer kaçışsız yazılıyor, sütunlar kayabiliyordu). =, +, -, @,
 * sekme ile başlayan METİN hücresi `'` ile nötrlenir: Excel'de açılınca formül
 * olarak çalışmasın (ihbar kaydı gibi dışarıdan gelen metin — CSV/formül
 * enjeksiyonu). Gerçek sayılar (-5) değişmez.
 */
export function csvHucresi(v: unknown): string {
  let s = v === null || v === undefined ? '' : String(v);
  if (typeof v === 'string' && /^[=+\-@\t\r]/.test(s) && !/^[+-]?\d+([.,]\d+)?$/.test(s.trim())) s = `'${s}`;
  return /[",\r\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}

export function execExport(nodeId: string, config: Record<string, unknown>, inputData: Record<string, unknown> | null, demo = false): ExecutionResult {
  const rows = extractRows(inputData);
  const format = (config.format as string) || 'csv';
  // Sentetik veriden türeyen dosya adından tanınır (paylaşıldığında da).
  const filename = `${(config.filename as string) || 'output'}${demo ? '_DEMO' : ''}`;
  const columns = extractColumns(inputData);

  let content = '';
  let mimeType = '';
  let ext = '';

  if (format === 'csv') {
    ext = 'csv';
    mimeType = 'text/csv;charset=utf-8;';
    content = columns.map(csvHucresi).join(',') + '\n' + rows.map((r) => columns.map((c) => csvHucresi(r[c])).join(',')).join('\n');
  } else if (format === 'json') {
    ext = 'json';
    mimeType = 'application/json';
    content = JSON.stringify(rows, null, 2);
  } else {
    ext = 'csv';
    mimeType = 'text/csv';
    content = columns.map(csvHucresi).join(',') + '\n' + rows.map((r) => columns.map((c) => csvHucresi(r[c])).join(',')).join('\n');
  }

  // İndirme yalnız tarayıcıda (Node testlerinde içerik yine üretilir ve sonuçta döner).
  const indirildi = typeof document !== 'undefined';
  if (indirildi) {
    const blob = new Blob([content], { type: mimeType });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${filename}.${ext}`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  return makeResult(nodeId, 'export', {
    format, filename, rowCount: rows.length, ext, downloaded: indirildi,
    ...(indirildi ? {} : { icerik: content }),
  }, rows.length);
}

export function execAlert(nodeId: string, config: Record<string, unknown>, inputData: Record<string, unknown> | null): ExecutionResult {
  const rows = extractRows(inputData);
  const condition = String(config.condition ?? '');
  const threshold = Number(config.threshold) || 0;
  // Eskiden koşul adında yalnız "greater" aranıyordu: value_greater_than /
  // value_less_than seçilse de SATIR SAYISI karşılaştırılıyordu (Python dışa
  // aktarımı ise değeri karşılaştırıyordu — iki motor farklı sonuç veriyordu),
  // koşul yoksa TypeError atıyordu. Şimdi Python ile aynı kural.
  let olculen: number;
  switch (condition) {
    case 'count_greater_than':
    case 'count_less_than':
      olculen = rows.length;
      break;
    case 'value_greater_than':
    case 'value_less_than': {
      // Tüm sayısal sütunlardaki en büyük / en küçük değer (pandas
      // select_dtypes("number").max().max() / .min().min() karşılığı).
      const buyuk = condition === 'value_greater_than';
      let uc: number | null = null;
      for (const c of sayisalSutunlar(rows, extractColumns(inputData))) {
        for (const v of sutunDegerleri(rows, c).degerler) {
          if (uc === null || (buyuk ? v > uc : v < uc)) uc = v;
        }
      }
      if (uc === null) return makeError(nodeId, 'alert', 'Değer koşulu için girdide sayısal sütun yok.');
      olculen = uc;
      break;
    }
    default:
      return makeError(nodeId, 'alert', `Bilinmeyen uyarı koşulu: "${condition}"`);
  }
  const triggered = condition.endsWith('greater_than') ? olculen > threshold : olculen < threshold;

  return makeResult(nodeId, 'alert', {
    triggered,
    condition,
    threshold,
    olculen,
    rowCount: rows.length,
    channel: config.channel,
    _demoNote: 'Alert delivery requires backend integration'
  }, rows.length);
}

// ============================================================
// PRE-BUILT MODEL TEMPLATES
// ============================================================
