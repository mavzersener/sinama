// Analiz düğümleri: istatistik, regresyon, kümeleme, anomali, korelasyon, birliktelik, model doğrulama, veri kalitesi, çapraz doğrulama.
// (executionEngine.ts'den bölündü — Faz 4.)

import { analizOnKontrol, VERI_SOZLESMELERI } from '../veriSozlesmesi';
import { eksikMi, sayiCoz, sayisalSutunlar, sutunDegerleri, tamKayitlar, ortalama, stdSapma, kantil, pearson, spearman, kendallTauB, ols, olsTahmin, r2Hesapla, tohumAl, tohumluUretec, karistir, standartlastir, kMeans, silhouette } from '../istatistik';
import { extractRows, extractColumns, csvAlan, dislamaUyarisi, sayisalSecim, yuvarla, makeResult, makeError, type ExecutionResult } from '../sonuc';

// ---- Analysis Nodes (REAL mathematical algorithms) ----

export function execStatistics(nodeId: string, config: Record<string, unknown>, inputData: Record<string, unknown> | null): ExecutionResult {
  const rows = extractRows(inputData);
  const cols = csvAlan(config.columns);
  const statsToCompute = (config.stats as string[]) || ['count', 'mean', 'std', 'min', 'max'];

  const uyarilar: string[] = [];
  const kullanilan = sayisalSecim(rows, cols, extractColumns(inputData), uyarilar);

  const stats: Record<string, Record<string, number | null>> = {};
  kullanilan.forEach((col) => {
    // Boş hücre sayılmaz (eski motorda Number(null)=0 olarak count/mean/min'e giriyordu).
    const { degerler: values, eksik, gecersiz } = sutunDegerleri(rows, col);
    if (values.length === 0) return;
    const sorted = [...values].sort((a, b) => a - b);
    stats[col] = {};
    if (statsToCompute.includes('count')) stats[col].count = values.length;
    if (statsToCompute.includes('mean')) stats[col].mean = yuvarla(ortalama(values));
    if (statsToCompute.includes('median')) stats[col].median = yuvarla(kantil(sorted, 0.5));
    if (statsToCompute.includes('std')) stats[col].std = yuvarla(stdSapma(values, 1));
    if (statsToCompute.includes('min')) stats[col].min = sorted[0];
    if (statsToCompute.includes('max')) stats[col].max = sorted[sorted.length - 1];
    if (statsToCompute.includes('sum')) stats[col].sum = yuvarla(values.reduce((a, b) => a + b, 0), 2);
    stats[col].eksik = eksik + gecersiz;
    if (eksik + gecersiz > 0) uyarilar.push(`${col}: ${eksik + gecersiz} boş/sayısal olmayan hücre hesaba katılmadı.`);
  });

  return makeResult(nodeId, 'statistics', { stats, columns: kullanilan, rowCount: rows.length, uyarilar }, rows.length);
}

export function execLinearRegression(nodeId: string, config: Record<string, unknown>, inputData: Record<string, unknown> | null): ExecutionResult {
  const rows = extractRows(inputData);
  const target = config.target as string;
  const features = csvAlan(config.features);
  if (!target) return makeError(nodeId, 'linear_regression', 'Target column required');

  if (!sayisalSutunlar(rows, [target]).length) {
    return makeError(nodeId, 'linear_regression', `Target column "${target}" is not numeric`);
  }
  // TÜM özellikler modele girer (eski motor sessizce yalnız ilkini kullanıyordu).
  const uyarilar: string[] = [];
  const featureCols = sayisalSecim(
    rows, features.filter((f) => f !== target), extractColumns(inputData).filter((c) => c !== target), uyarilar,
  );
  if (featureCols.length === 0) return makeError(nodeId, 'linear_regression', 'No numeric feature column found');

  // Tam kayıtlar: x'ler ve y AYNI satırlardan (ayrı süzme satır kaydırıyordu).
  const { matris, dislanan } = tamKayitlar(rows, [...featureCols, target]);
  const u = dislamaUyarisi(dislanan, rows.length, 'hedef ya da özelliklerde boş/sayısal olmayan hücre');
  if (u) uyarilar.push(u);
  const X = matris.map((r) => r.slice(0, -1));
  const y = matris.map((r) => r[r.length - 1]);

  let model;
  try {
    model = ols(X, y);
  } catch (err) {
    return makeError(nodeId, 'linear_regression', (err as Error).message);
  }

  // Holdout (Test Size): katsayılar TÜM tam kayıtlardan; ayrıca tohumlu bir
  // ayrımda eğitim→test başarımı. Alan eskiden gösteriliyor ama yok sayılıyordu.
  const oranHam = sayiCoz(config.testSize) ?? 0;
  const testOrani = Math.min(0.5, Math.max(0, oranHam > 1 ? oranHam / 100 : oranHam));
  const tohum = tohumAl(config.seed);
  let holdout: Record<string, unknown> | null = null;
  const testN = Math.round(X.length * testOrani);
  if (testN >= 2 && X.length - testN >= featureCols.length + 1) {
    const sira = karistir(X.map((_, i) => i), tohumluUretec(tohum));
    const test = sira.slice(0, testN);
    const egitim = sira.slice(testN);
    try {
      const m = ols(egitim.map((i) => X[i]), egitim.map((i) => y[i]));
      const ty = test.map((i) => y[i]);
      const tm = ortalama(ty);
      let sse = 0, sst = 0;
      test.forEach((i, t) => { sse += (y[i] - olsTahmin(m, X[i])) ** 2; sst += (ty[t] - tm) ** 2; });
      holdout = { test_orani: testOrani, egitim_n: egitim.length, test_n: testN, test_r_squared: yuvarla(r2Hesapla(sse, sst)), test_mse: yuvarla(sse / testN), tohum };
    } catch {
      uyarilar.push('Eğitim kümesinde özellikler tekil kaldı; holdout başarımı hesaplanamadı.');
    }
  } else if (testOrani > 0) {
    uyarilar.push('Holdout için kayıt yetersiz; yalnız örneklem-içi başarım raporlandı.');
  }

  return makeResult(nodeId, 'linear_regression', {
    r_squared: yuvarla(model.r2),
    r_squared_adj: yuvarla(model.r2Duzeltilmis),
    mse: yuvarla(model.mse),
    intercept: yuvarla(model.kesisim),
    target,
    features: featureCols,
    coefficients: featureCols.map((f, j) => ({ feature: f, coefficient: yuvarla(model.katsayilar[j]) })),
    // Tek özellikte geriye uyum: eski alanlar.
    ...(featureCols.length === 1 ? { feature: featureCols[0], slope: yuvarla(model.katsayilar[0]) } : {}),
    sample_size: model.n,
    n_dislanan: dislanan,
    degerlendirme: 'orneklem_ici',
    holdout,
    uyarilar,
  }, rows.length);
}

export function execClustering(nodeId: string, config: Record<string, unknown>, inputData: Record<string, unknown> | null): ExecutionResult {
  const rows = extractRows(inputData);
  const featureCols = csvAlan(config.features);
  const k = Math.max(2, Math.min(10, Number(config.k) || 3));
  const maxIter = Number(config.maxIterations) || 100;

  // TÜM seçili sayısal sütunlar (eski motor sessizce ilk 2'sini alıyordu).
  const uyarilar: string[] = [];
  const cols = sayisalSecim(rows, featureCols, extractColumns(inputData), uyarilar);
  if (cols.length === 0) return makeError(nodeId, 'clustering', 'No numeric columns found');

  // Tam kayıtlar: boş hücre eskiden 0 sayılıp sahte bir noktaya dönüşüyordu.
  const { matris: ham, dislanan } = tamKayitlar(rows, cols);
  const u = dislamaUyarisi(dislanan, rows.length, 'boş/sayısal olmayan özellik hücresi');
  if (u) uyarilar.push(u);
  if (ham.length < k) return makeError(nodeId, 'clustering', `Need at least ${k} complete rows, got ${ham.length}`);

  // Ölçekleme: farklı birimli sütunlarda (gelir ~1e5, skor ~1e2) büyük olan
  // mesafeye hâkim olur. Aynı birimli veride (ör. yalnız enlem/boylam)
  // standardize=false seçilmeli.
  const olcekle = config.standardize !== false && config.standardize !== 'false';
  const tohum = tohumAl(config.seed);
  const { Z, ort, olcek } = olcekle ? standartlastir(ham) : { Z: ham, ort: cols.map(() => 0), olcek: cols.map(() => 1) };
  const km = kMeans(Z, k, { maksIter: maxIter, nInit: 10, tohum });
  const sil = silhouette(Z, km.etiketler, { tohum });
  if (sil.ornekN < Z.length) uyarilar.push(`Silhouette ${sil.ornekN} satırlık tohumlu örnekte hesaplandı (n=${Z.length}).`);

  const counts = new Array<number>(k).fill(0);
  km.etiketler.forEach((c) => { counts[c]++; });

  return makeResult(nodeId, 'clustering', {
    k,
    features: cols,
    standardize: olcekle,
    clusters: Array.from({ length: k }, (_, i) => ({
      cluster: i + 1,
      size: counts[i],
      // Merkez ÖZGÜN birimde (standartlaştırma geri alınır).
      centroid: km.merkezler[i].map((v, j) => yuvarla(v * olcek[j] + ort[j], 2)),
    })),
    silhouette_score: yuvarla(sil.skor),
    inertia: yuvarla(km.eylemsizlik),
    sample_size: ham.length,
    n_dislanan: dislanan,
    tohum,
    uyarilar,
  }, rows.length);
}

export function execAnomalyDetection(nodeId: string, config: Record<string, unknown>, inputData: Record<string, unknown> | null): ExecutionResult {
  const rows = extractRows(inputData);
  const istenen = (config.method as string) || 'iqr';
  const uyarilar: string[] = [];
  const cols = sayisalSecim(rows, csvAlan(config.columns), extractColumns(inputData), uyarilar);
  if (cols.length === 0) return makeError(nodeId, 'anomaly_detection', 'No numeric columns');

  // Isolation Forest tarayıcıda YOK. Eskiden sessizce |z|>2 uygulanıp sonuç
  // "isolation_forest" diye etiketleniyordu; artık uygulanan yöntem yazılır.
  let yontem = istenen;
  let esik = sayiCoz(config.threshold) ?? 1.5;
  if (istenen !== 'iqr' && istenen !== 'zscore') {
    yontem = 'zscore';
    esik = 2;
    uyarilar.push(`"${istenen}" tarayıcı motorunda yok; yerine |z| > 2 uygulandı. Gerçek Isolation Forest için Python dışa aktarımını kullanın.`);
  }

  const isaretli = new Set<number>();
  const kolonBazinda: Record<string, number> = {};
  const bulgular: Array<{ i: number; score: number; column: string }> = [];

  for (const col of cols) {
    // Satır hizası KORUNUR: eskiden süzülmüş dizi `values[i]` ile tüm
    // satırlara geri eşleniyordu — eksik hücre olunca aykırı değer YANLIŞ
    // kayda atanıyordu. Boş hücre de 0 sayılıp sahte aykırı olabiliyordu.
    const cift: Array<[number, number]> = [];
    rows.forEach((r, i) => {
      const v = sayiCoz(r[col]);
      if (v !== null) cift.push([i, v]);
    });
    kolonBazinda[col] = 0;
    if (cift.length === 0) continue;
    const vals = cift.map((c) => c[1]);

    let skor: (v: number) => number | null;
    if (yontem === 'iqr') {
      const s = [...vals].sort((a, b) => a - b);
      const q1 = kantil(s, 0.25);
      const q3 = kantil(s, 0.75);
      const iqr = q3 - q1;
      const alt = q1 - esik * iqr;
      const ust = q3 + esik * iqr;
      skor = (v) => (v < alt ? (alt - v) / (iqr || 1) : v > ust ? (v - ust) / (iqr || 1) : null);
    } else {
      const m = ortalama(vals);
      const sd = stdSapma(vals, 0);
      if (!sd) continue;
      skor = (v) => { const z = Math.abs((v - m) / sd); return z > esik ? z : null; };
    }
    for (const [i, v] of cift) {
      const sc = skor(v);
      if (sc === null) continue;
      kolonBazinda[col]++;
      isaretli.add(i);
      bulgular.push({ i, score: Number(sc.toFixed(2)), column: col });
    }
  }

  bulgular.sort((a, b) => b.score - a.score);
  return makeResult(nodeId, 'anomaly_detection', {
    method: istenen,
    uygulanan_yontem: yontem,
    threshold: esik,
    total_rows: rows.length,
    // SATIR bazında (birleşim): aynı satır iki sütunda işaretlense de bir kez
    // sayılır — oran %100'ü aşamaz. Hücre bazındaki sayım ayrıca verilir.
    anomalies_detected: isaretli.size,
    anomaly_rate: rows.length ? Number(((isaretli.size / rows.length) * 100).toFixed(2)) : 0,
    isaretli_hucre: bulgular.length,
    kolon_bazinda: kolonBazinda,
    sample_anomalies: bulgular.slice(0, 5).map((b) => ({ row: rows[b.i], score: b.score, column: b.column })),
    uyarilar,
  }, rows.length);
}

export function execCorrelation(nodeId: string, config: Record<string, unknown>, inputData: Record<string, unknown> | null): ExecutionResult {
  const rows = extractRows(inputData);
  const method = config.method as string;
  const uyarilar: string[] = [];
  const cols = sayisalSecim(rows, csvAlan(config.columns), extractColumns(inputData), uyarilar);
  if (cols.length < 2) return makeError(nodeId, 'correlation', 'Need at least 2 numeric columns');

  // Çift bazlı tam kayıt (pandas .corr ile aynı): her çift için İKİ değeri de
  // dolu satırlar, hizası korunarak. Eskiden x ve y ayrı süzülüp kısaltılıyor,
  // eksik hücre olunca satırlar kayıyordu (y=2x verisinde r=0.64 çıkıyordu).
  // Tanımsız (n<2 ya da sabit sütun) → null; 0 "ilişki yok" demektir.
  const matrix: Record<string, Record<string, number | null>> = {};
  const nMatrix: Record<string, Record<string, number>> = {};
  let enAzN = Infinity;
  let enCokN = 0;
  cols.forEach((c1) => { matrix[c1] = {}; nMatrix[c1] = {}; });
  cols.forEach((c1, a) => {
    cols.forEach((c2, b) => {
      if (b < a) return;
      const { matris } = tamKayitlar(rows, [c1, c2]);
      const x = matris.map((r) => r[0]);
      const y = matris.map((r) => r[1]);
      const r = c1 === c2 ? (x.length >= 2 && new Set(x).size > 1 ? 1 : null)
        : method === 'spearman' ? spearman(x, y)
          : method === 'kendall' ? kendallTauB(x, y)
            : pearson(x, y);
      matrix[c1][c2] = matrix[c2][c1] = yuvarla(r);
      nMatrix[c1][c2] = nMatrix[c2][c1] = x.length;
      if (c1 !== c2) {
        enAzN = Math.min(enAzN, x.length);
        enCokN = Math.max(enCokN, x.length);
      }
    });
  });
  if (enAzN < rows.length) {
    const aralik = enAzN === enCokN ? `${enAzN}` : `${enAzN}–${enCokN}`;
    uyarilar.push(`Eksik hücreler çift bazında dışlandı; çift başına ${aralik} satır kullanıldı (toplam ${rows.length}; ayrıntı n_matrix).`);
  }
  const tanimsiz = cols.flatMap((c1) => cols.filter((c2) => c2 > c1 && matrix[c1][c2] === null).map((c2) => `${c1}×${c2}`));
  if (tanimsiz.length) uyarilar.push(`Tanımsız korelasyon (sabit sütun ya da <2 ortak kayıt): ${tanimsiz.join(', ')}.`);

  return makeResult(nodeId, 'correlation', { method, matrix, n_matrix: nMatrix, columns: cols, uyarilar }, rows.length);
}

export function execAssociationRules(nodeId: string, config: Record<string, unknown>, inputData: Record<string, unknown> | null): ExecutionResult {
  const rows = extractRows(inputData);
  const itemsCol = config.itemsColumn as string;
  const minSupport = Number(config.minSupport) || 0.05;
  const minConfidence = Number(config.minConfidence) || 0.5;

  // If no items column specified, try to find one
  let col = itemsCol;
  if (!col) {
    // İlk satırın tipine bakmak yetmez (ilk hücre boş olabilir): dolu
    // hücrelerinde sayı dışı metin taşıyan ilk sütun.
    const sayisal = new Set(sayisalSutunlar(rows, extractColumns(inputData)));
    col = extractColumns(inputData).find(
      (c) => !sayisal.has(c) && rows.some((r) => typeof r[c] === 'string' && !eksikMi(r[c])),
    ) ?? '';
  }
  if (!col) return makeError(nodeId, 'association_rules', 'No text column found for items');

  // Simple frequent itemset mining
  const itemCounts: Record<string, number> = {};
  const pairCounts: Record<string, number> = {};
  const total = rows.length;

  rows.forEach((row) => {
    const items = String(row[col] || '').split(/[,;|]/).map((s) => s.trim()).filter(Boolean);
    items.forEach((item) => { itemCounts[item] = (itemCounts[item] || 0) + 1; });
    for (let i = 0; i < items.length; i++) {
      for (let j = i + 1; j < items.length; j++) {
        const pair = [items[i], items[j]].sort().join('→');
        pairCounts[pair] = (pairCounts[pair] || 0) + 1;
      }
    }
  });

  const rules = Object.entries(pairCounts)
    .map(([pair, count]) => {
      const [a, b] = pair.split('→');
      const support = count / total;
      const confA = count / (itemCounts[a] || 1);
      const lift = confA / ((itemCounts[b] || 1) / total);
      return { antecedent: [a], consequent: [b], support, confidence: confA, lift };
    })
    .filter((r) => r.confidence >= minConfidence && r.support >= minSupport)
    .sort((a, b) => b.lift - a.lift)
    .slice(0, 10)
    .map((r) => ({
      ...r,
      support: Number(r.support.toFixed(3)),
      confidence: Number(r.confidence.toFixed(3)),
      lift: Number(r.lift.toFixed(2))
    }));

  return makeResult(nodeId, 'association_rules', { rules_found: rules.length, rules, minSupport, minConfidence }, rows.length);
}

// P2-1: Model Validation - Confusion Matrix, Precision, Recall, F1, Accuracy
export function execModelValidation(nodeId: string, config: Record<string, unknown>, inputData: Record<string, unknown> | null): ExecutionResult {
  const rows = extractRows(inputData);
  const actualCol = config.actualColumn as string;
  const predictedCol = config.predictedColumn as string;

  if (!actualCol || !predictedCol) return makeError(nodeId, 'model_validation', 'actualColumn and predictedColumn required');

  // Yalnız iki değeri de dolu satırlar. Eskiden ikisi de boş satırlar
  // '' === '' diye DOĞRU tahmin sayılıyor, accuracy şişiyordu.
  const uyarilar: string[] = [];
  const actuals: string[] = [];
  const predicted: string[] = [];
  for (const r of rows) {
    if (eksikMi(r[actualCol]) || eksikMi(r[predictedCol])) continue;
    actuals.push(String(r[actualCol]).trim());
    predicted.push(String(r[predictedCol]).trim());
  }
  const u = dislamaUyarisi(rows.length - actuals.length, rows.length, 'gerçek ya da tahmin değeri boş');
  if (u) uyarilar.push(u);

  if (actuals.length === 0) return makeError(nodeId, 'model_validation', 'No rows with both actual and predicted values');

  // Get unique classes
  const classes = Array.from(new Set([...actuals, ...predicted])).filter((c) => c !== '').sort();
  if (classes.length === 0) return makeError(nodeId, 'model_validation', 'No classes found');

  // Build confusion matrix
  const cm: Record<string, Record<string, number>> = {};
  classes.forEach((c) => { cm[c] = {}; classes.forEach((c2) => { cm[c][c2] = 0; }); });

  for (let i = 0; i < actuals.length; i++) {
    const a = actuals[i];
    const p = predicted[i];
    if (a !== '' && p !== '') cm[a][p] = (cm[a][p] || 0) + 1;
  }

  // Per-class metrics
  const perClass: Array<{
    class: string; precision: number; recall: number; f1: number; support: number;
    tp: number; fp: number; fn: number; tn: number;
  }> = [];

  classes.forEach((cls) => {
    const tp = cm[cls][cls] || 0;
    let fp = 0, fn = 0, tn = 0;
    classes.forEach((c1) => {
      classes.forEach((c2) => {
        if (c1 === cls && c2 !== cls) fn += cm[c1][c2] || 0;
        if (c1 !== cls && c2 === cls) fp += cm[c1][c2] || 0;
        if (c1 !== cls && c2 !== cls) tn += cm[c1][c2] || 0;
      });
    });
    const precision = tp + fp > 0 ? tp / (tp + fp) : 0;
    const recall = tp + fn > 0 ? tp / (tp + fn) : 0;
    const f1 = precision + recall > 0 ? 2 * precision * recall / (precision + recall) : 0;
    const support = actuals.filter((a) => a === cls).length;
    perClass.push({ class: cls, precision: Number(precision.toFixed(4)), recall: Number(recall.toFixed(4)), f1: Number(f1.toFixed(4)), support, tp, fp, fn, tn });
  });

  // Macro averages
  const macroPrecision = perClass.length > 0 ? perClass.reduce((s, c) => s + c.precision, 0) / perClass.length : 0;
  const macroRecall = perClass.length > 0 ? perClass.reduce((s, c) => s + c.recall, 0) / perClass.length : 0;
  const macroF1 = perClass.length > 0 ? perClass.reduce((s, c) => s + c.f1, 0) / perClass.length : 0;

  // Accuracy
  let correct = 0;
  for (let i = 0; i < actuals.length; i++) if (actuals[i] === predicted[i]) correct++;
  const accuracy = actuals.length > 0 ? correct / actuals.length : 0;

  // Total support
  const totalSupport = actuals.length;

  return makeResult(nodeId, 'model_validation', {
    confusion_matrix: cm,
    classes,
    per_class: perClass,
    macro_precision: Number(macroPrecision.toFixed(4)),
    macro_recall: Number(macroRecall.toFixed(4)),
    macro_f1: Number(macroF1.toFixed(4)),
    accuracy: Number(accuracy.toFixed(4)),
    total_samples: totalSupport,
    n_dislanan: rows.length - totalSupport,
    uyarilar,
  }, rows.length);
}

// P2-3: Data Quality Analysis
export function execDataQuality(nodeId: string, config: Record<string, unknown>, inputData: Record<string, unknown> | null): ExecutionResult {
  const rows = extractRows(inputData);
  const allColumns = extractColumns(inputData);
  let cols = csvAlan(config.columns);
  if (cols.length === 0) cols = allColumns;

  if (rows.length === 0) return makeError(nodeId, 'data_quality', 'No data to analyze');

  const columnReport: Array<{
    column: string; type: string; nonNull: number; nullCount: number; nullPct: number;
    unique: number; uniquePct: number; outlierCount: number; outlierPct: number; qualityScore: number;
  }> = [];

  cols.forEach((col) => {
    const values = rows.map((r) => r[col]);
    // Tek eksik tanımı (istatistik.eksikMi): yalnız boşluktan ibaret hücre de eksiktir.
    const nullCount = values.filter((v) => eksikMi(v)).length;
    const nonNull = values.length - nullCount;
    const nullPct = values.length > 0 ? (nullCount / values.length) * 100 : 0;

    // Type inference
    const nonNullValues = values.filter((v) => !eksikMi(v));
    // sayiCoz: Number(true)===1 yüzünden boolean sütun "sayısal" görünüyordu.
    const allNumeric = nonNullValues.length > 0 && nonNullValues.every((v) => sayiCoz(v) !== null);
    const allBoolean = nonNullValues.length > 0 && nonNullValues.every((v) => ['true', 'false', '0', '1', true, false].includes(String(v).toLowerCase()));
    let type = 'string';
    if (allNumeric) type = 'number';
    else if (allBoolean) type = 'boolean';

    // Unique count
    const unique = new Set(nonNullValues.map((v) => String(v))).size;
    const uniquePct = nonNull > 0 ? (unique / nonNull) * 100 : 0;

    // Outlier detection (for numeric columns)
    let outlierCount = 0;
    if (type === 'number') {
      const nums = nonNullValues.map((v) => sayiCoz(v)).filter((v): v is number => v !== null);
      if (nums.length > 0) {
        const sorted = [...nums].sort((a, b) => a - b);
        const q1 = kantil(sorted, 0.25);
        const q3 = kantil(sorted, 0.75);
        const iqr = q3 - q1;
        const lower = q1 - 1.5 * iqr;
        const upper = q3 + 1.5 * iqr;
        outlierCount = nums.filter((v) => v < lower || v > upper).length;
      }
    }
    const outlierPct = nonNull > 0 ? (outlierCount / nonNull) * 100 : 0;

    // Quality score (0-100): penalize nulls, outliers, and near-zero variance
    let qualityScore = 100;
    qualityScore -= nullPct * 0.5; // up to 50 pts for nulls
    qualityScore -= outlierPct * 0.3; // up to 30 pts for outliers
    if (uniquePct < 1 && nonNull > 10) qualityScore -= 10; // near-zero variance penalty
    qualityScore = Math.max(0, Math.min(100, Number(qualityScore.toFixed(1))));

    columnReport.push({ column: col, type, nonNull, nullCount, nullPct: Number(nullPct.toFixed(2)), unique, uniquePct: Number(uniquePct.toFixed(2)), outlierCount, outlierPct: Number(outlierPct.toFixed(2)), qualityScore });
  });

  // Overall quality score
  const overallScore = columnReport.length > 0
    ? Number((columnReport.reduce((s, c) => s + c.qualityScore, 0) / columnReport.length).toFixed(1))
    : 0;

  // Row-level issues
  const duplicateRows = rows.length - new Set(rows.map((r) => JSON.stringify(r))).size;
  const emptyRows = rows.filter((r) => cols.every((c) => r[c] === null || r[c] === undefined || r[c] === '')).length;

  // ÖNGÖRÜ: bu veriyle hangi analizler kırılır. Betimsel rapor tek başına
  // yetmiyordu — kullanıcı sorunu ancak analizi koşup hata alınca görüyordu.
  // Burada her analizin veri sözleşmesi bu veriye karşı sınanır ve
  // KIRILACAK olanlar çözüm önerisiyle listelenir.
  const analizUyarilari: Array<{
    analiz: string; seviye: string; kod: string; sutun?: string;
    mesaj: string; cozum: string;
  }> = [];
  for (const analiz of Object.keys(VERI_SOZLESMELERI)) {
    // Sütun seçimi henüz yapılmadığı için sözleşmenin sütun alanları boş
    // geçilir: bu aşamada satır sayısı ve sütun VARLIĞI sınanır. Sütun
    // seçildikten sonra tam kontrol düğümün kendi doğrulamasında yapılır.
    const bulgular = analizOnKontrol(analiz, {}, cols, rows);
    for (const b of bulgular) {
      analizUyarilari.push({
        analiz, seviye: b.seviye, kod: b.kod, sutun: b.sutun,
        mesaj: b.mesaj, cozum: b.cozum,
      });
    }
  }

  return makeResult(nodeId, 'data_quality', {
    overall_score: overallScore,
    total_rows: rows.length,
    total_columns: cols.length,
    duplicate_rows: duplicateRows,
    empty_rows: emptyRows,
    columns: columnReport,
    // Sonraki analizler için öngörü (Türkçe alan adı bilinçli: kullanıcıya
    // gösterilen bir sözleşme).
    analiz_uyarilari: analizUyarilari,
    engellenen_analizler: [...new Set(
      analizUyarilari.filter((u) => u.seviye === 'engel').map((u) => u.analiz),
    )],
  }, rows.length);
}

// P2-4: Cross-Validation (K-Fold)
export function execCrossValidation(nodeId: string, config: Record<string, unknown>, inputData: Record<string, unknown> | null): ExecutionResult {
  const rows = extractRows(inputData);
  const target = config.target as string;
  const featureCols = csvAlan(config.features);
  const k = Math.max(2, Math.min(20, Number(config.k) || 5));
  const metric = (config.metric as string) || 'r2';

  if (!target) return makeError(nodeId, 'cross_validation', 'Target column required');

  if (!sayisalSutunlar(rows, [target]).length) {
    return makeError(nodeId, 'cross_validation', `Target column "${target}" is not numeric`);
  }
  // TÜM özellikler (eski motor yalnız ilkini kullanıyordu); tam kayıtlar.
  const uyarilar: string[] = [];
  const features = sayisalSecim(
    rows, featureCols.filter((f) => f !== target), extractColumns(inputData).filter((c) => c !== target), uyarilar,
  );
  if (features.length === 0) return makeError(nodeId, 'cross_validation', 'No numeric feature columns found');
  const { matris, dislanan } = tamKayitlar(rows, [...features, target]);
  const u = dislamaUyarisi(dislanan, rows.length, 'hedef ya da özelliklerde boş/sayısal olmayan hücre');
  if (u) uyarilar.push(u);

  if (matris.length < k * 2) return makeError(nodeId, 'cross_validation', `Need at least ${k * 2} valid rows, got ${matris.length}`);

  // Tohumlu karıştırma: aynı veri + tohum → aynı katmanlar (eskiden Math.random).
  const tohum = tohumAl(config.seed);
  const sira = karistir(matris.map((_, i) => i), tohumluUretec(tohum));
  // sklearn KFold katman boyutları: ilk n % k katman bir fazla.
  const taban = Math.floor(sira.length / k);
  const fazla = sira.length % k;

  const foldResults: Array<{ fold: number; r2: number | null; mse: number | null; mae: number | null; rmse: number | null; trainSize: number; testSize: number }> = [];
  let bas = 0;
  for (let fold = 0; fold < k; fold++) {
    const boy = taban + (fold < fazla ? 1 : 0);
    const test = sira.slice(bas, bas + boy);
    const egitim = [...sira.slice(0, bas), ...sira.slice(bas + boy)];
    bas += boy;
    let model;
    try {
      model = ols(egitim.map((i) => matris[i].slice(0, -1)), egitim.map((i) => matris[i][matris[i].length - 1]));
    } catch {
      uyarilar.push(`Katman ${fold + 1}: eğitim kümesinde özellikler tekil; katman atlandı.`);
      continue;
    }
    const ty = test.map((i) => matris[i][matris[i].length - 1]);
    const tahmin = test.map((i) => olsTahmin(model, matris[i].slice(0, -1)));
    const tm = ortalama(ty);
    let sse = 0, sst = 0, sae = 0;
    ty.forEach((yi, t) => { sse += (yi - tahmin[t]) ** 2; sst += (yi - tm) ** 2; sae += Math.abs(yi - tahmin[t]); });
    const mse = sse / ty.length;
    foldResults.push({
      fold: fold + 1,
      r2: yuvarla(r2Hesapla(sse, sst)),
      mse: yuvarla(mse),
      mae: yuvarla(sae / ty.length),
      rmse: yuvarla(Math.sqrt(mse)),
      trainSize: egitim.length,
      testSize: test.length,
    });
  }

  const ort = (sec: (f: typeof foldResults[number]) => number | null) => {
    const v = foldResults.map(sec).filter((x): x is number => x !== null);
    return v.length ? ortalama(v) : null;
  };
  const r2ler = foldResults.map((f) => f.r2).filter((x): x is number => x !== null);

  return makeResult(nodeId, 'cross_validation', {
    k,
    target,
    features,
    metric,
    total_samples: matris.length,
    n_dislanan: dislanan,
    tohum,
    folds: foldResults,
    avg_r2: yuvarla(ort((f) => f.r2)),
    std_r2: yuvarla(stdSapma(r2ler, 1) ?? 0),
    avg_mse: yuvarla(ort((f) => f.mse)),
    avg_mae: yuvarla(ort((f) => f.mae)),
    // Katman RMSE'lerinin ortalaması (sklearn neg_root_mean_squared_error ile aynı).
    avg_rmse: yuvarla(ort((f) => f.rmse)),
    uyarilar,
  }, matris.length);
}
