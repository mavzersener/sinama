// ============================================================
// Saf istatistik çekirdeği — tarayıcı motorunun sayısal doğruluk kaynağı.
// ============================================================
//
// Neden ayrı modül: yürütücüler aynı hesapları (sayıya çevirme, eksik atma,
// korelasyon, regresyon) kendi içlerinde farklı biçimlerde yapıyordu ve iki
// sessiz hata sınıfı bu dağınıklıktan doğdu:
//   1. `Number(null) === 0`: PapaParse boş hücreyi null yapar; null 0 sayılıp
//      ortalamaya, korelasyona, aykırı değere giriyordu.
//   2. x ve y ayrı ayrı süzülüp kısaltılıyordu: eksik hücre olunca satırlar
//      birbirine kayıyor (y=2x verisinde Pearson 0.64 çıkıyordu).
//
// Buradaki her fonksiyon saftır; rastgelelik yalnız tohumlu üreteçten gelir.
// Karşılıkları pandas/scikit-learn ile oracle testinde karşılaştırılır
// (tests/oracle.test.ts): semantik bilinçli olarak onlarla aynıdır (örneklem
// std ddof=1, doğrusal kantil, çift bazlı eksik atma, Kendall tau-b...).

export type Satir = Record<string, unknown>;

/** Eksik hücre: null/undefined ya da boş/yalnız boşluktan ibaret metin. */
export function eksikMi(v: unknown): boolean {
  return v === null || v === undefined || (typeof v === 'string' && v.trim() === '');
}

/**
 * Hücreyi sayıya çevirir; sayı değilse null. Türkçe ondalık virgülünü
 * ("37,58") kabul eder. null/boolean/Date/nesne ASLA sayı sayılmaz —
 * `Number(null) === 0`, `Number(true) === 1` tuzakları burada kapanır.
 */
export function sayiCoz(v: unknown): number | null {
  if (typeof v === 'number') return Number.isFinite(v) ? v : null;
  if (typeof v !== 'string') return null;
  const t = v.trim();
  if (!t) return null;
  // "37,58" → 37.58 (yalnız tek virgül ve nokta yoksa; binlik ayracıyla karışmasın)
  const d = t.includes('.') || (t.match(/,/g)?.length ?? 0) !== 1
    ? t
    : t.replace(',', '.');
  const n = Number(d);
  return Number.isFinite(n) ? n : null;
}

/**
 * Sayısal sütunlar: en az bir dolu hücresi olan ve dolu hücrelerinin TAMAMI
 * sayıya çözülen sütunlar (pandas'ın is_numeric_dtype davranışı). Eski motor
 * yalnız İLK satırın tipine bakıyordu: ilk satırı boş olan sayısal sütun
 * analizden sessizce düşüyordu.
 */
export function sayisalSutunlar(satirlar: Satir[], sutunlar: string[]): string[] {
  return sutunlar.filter((s) => {
    let dolu = 0;
    for (const r of satirlar) {
      const v = r[s];
      if (eksikMi(v)) continue;
      if (sayiCoz(v) === null) return false;
      dolu++;
    }
    return dolu > 0;
  });
}

/** Tek sütunun sayısal değerleri + eksik/geçersiz hücre sayıları. */
export function sutunDegerleri(satirlar: Satir[], sutun: string):
  { degerler: number[]; eksik: number; gecersiz: number } {
  const degerler: number[] = [];
  let eksik = 0;
  let gecersiz = 0;
  for (const r of satirlar) {
    const v = r[sutun];
    if (eksikMi(v)) { eksik++; continue; }
    const n = sayiCoz(v);
    if (n === null) gecersiz++;
    else degerler.push(n);
  }
  return { degerler, eksik, gecersiz };
}

/**
 * Tam kayıt (complete-case) matrisi: verilen sütunların HEPSİ sayı olan
 * satırlar, satır hizası korunarak. Çok değişkenli analizlerin tek girişi —
 * değişkenler asla ayrı ayrı süzülmez.
 */
export function tamKayitlar(satirlar: Satir[], sutunlar: string[]):
  { matris: number[][]; satirIdx: number[]; dislanan: number } {
  const matris: number[][] = [];
  const satirIdx: number[] = [];
  satirlar.forEach((r, i) => {
    const vals: number[] = [];
    for (const s of sutunlar) {
      const n = sayiCoz(r[s]);
      if (n === null) return;
      vals.push(n);
    }
    matris.push(vals);
    satirIdx.push(i);
  });
  return { matris, satirIdx, dislanan: satirlar.length - matris.length };
}

// ------------------------------------------------------------ betimsel

export function ortalama(x: number[]): number {
  let t = 0;
  for (const v of x) t += v;
  return t / x.length;
}

/** Varyans; ddof=1 örneklem (pandas varsayılanı), ddof=0 kitle. n<=ddof → null. */
export function varyans(x: number[], ddof = 1): number | null {
  if (x.length <= ddof) return null;
  const m = ortalama(x);
  let t = 0;
  for (const v of x) t += (v - m) ** 2;
  return t / (x.length - ddof);
}

export function stdSapma(x: number[], ddof = 1): number | null {
  const v = varyans(x, ddof);
  return v === null ? null : Math.sqrt(v);
}

/** Doğrusal enterpolasyonlu kantil (pandas/numpy varsayılanı); SIRALI dizi ister. */
export function kantil(sirali: number[], q: number): number {
  const pos = (sirali.length - 1) * q;
  const alt = Math.floor(pos);
  const ust = Math.ceil(pos);
  return sirali[alt] + (sirali[ust] - sirali[alt]) * (pos - alt);
}

/** Medyan: çift n'de iki ortanın ortalaması (eski motor üst ortayı veriyordu). */
export function medyan(x: number[]): number {
  return kantil([...x].sort((a, b) => a - b), 0.5);
}

/** Dizinin en küçük/en büyük değeri; spread kullanmaz (büyük dizide yığın taşması). */
export function enKucukBuyuk(x: number[]): { min: number; max: number } {
  let min = Infinity;
  let max = -Infinity;
  for (const v of x) {
    if (v < min) min = v;
    if (v > max) max = v;
  }
  return { min, max };
}

// ------------------------------------------------------------ korelasyon

/** Pearson r; n<2 ya da sabit değişken → null (tanımsız — 0 "ilişki yok" demektir). */
export function pearson(x: number[], y: number[]): number | null {
  const n = x.length;
  if (n < 2) return null;
  const mx = ortalama(x);
  const my = ortalama(y);
  let pay = 0, sx = 0, sy = 0;
  for (let i = 0; i < n; i++) {
    const dx = x[i] - mx, dy = y[i] - my;
    pay += dx * dy;
    sx += dx * dx;
    sy += dy * dy;
  }
  if (sx === 0 || sy === 0) return null;
  return pay / Math.sqrt(sx * sy);
}

/** Ortalama sıralar (bağlılar ortalama sıra alır). */
export function siralar(x: number[]): number[] {
  const sirali = x.map((v, i) => ({ v, i })).sort((a, b) => a.v - b.v);
  const r = new Array<number>(x.length);
  for (let i = 0; i < sirali.length;) {
    let j = i;
    while (j < sirali.length && sirali[j].v === sirali[i].v) j++;
    const ort = (i + 1 + j) / 2;
    for (let k = i; k < j; k++) r[sirali[k].i] = ort;
    i = j;
  }
  return r;
}

export function spearman(x: number[], y: number[]): number | null {
  if (x.length < 2) return null;
  return pearson(siralar(x), siralar(y));
}

/**
 * Kendall tau-b (scipy/pandas varsayılanı). Eski motor tau-a hesaplıyor ve
 * iki değişkende de bağlı çiftleri "uyumlu" sayıyordu.
 */
export function kendallTauB(x: number[], y: number[]): number | null {
  const n = x.length;
  if (n < 2) return null;
  let uyumlu = 0, uyumsuz = 0;
  for (let i = 0; i < n; i++) {
    for (let j = i + 1; j < n; j++) {
      const s = Math.sign(x[i] - x[j]) * Math.sign(y[i] - y[j]);
      if (s > 0) uyumlu++;
      else if (s < 0) uyumsuz++;
    }
  }
  const baglar = (a: number[]) => {
    const say = new Map<number, number>();
    for (const v of a) say.set(v, (say.get(v) ?? 0) + 1);
    let t = 0;
    for (const c of say.values()) t += (c * (c - 1)) / 2;
    return t;
  };
  const n0 = (n * (n - 1)) / 2;
  const payda = Math.sqrt((n0 - baglar(x)) * (n0 - baglar(y)));
  return payda === 0 ? null : (uyumlu - uyumsuz) / payda;
}

// ------------------------------------------------------------ regresyon

export interface OlsSonuc {
  katsayilar: number[];
  kesisim: number;
  r2: number;
  /** Düzeltilmiş R²; n-p-1 <= 0 ise null. */
  r2Duzeltilmis: number | null;
  /** Ortalama kare hata (sklearn mean_squared_error: SSE/n). */
  mse: number;
  n: number;
}

/**
 * Sabit terimli çok değişkenli en küçük kareler. Merkezlenmiş normal
 * denklemler kısmi pivotlu Gauss eliminasyonuyla çözülür (merkezleme
 * koşullanmayı iyileştirir). Sabit ya da doğrusal bağımlı özellik sessizce
 * yanlış katsayı üretmek yerine hata atar.
 */
export function ols(X: number[][], y: number[]): OlsSonuc {
  const n = X.length;
  const p = n > 0 ? X[0].length : 0;
  if (p === 0) throw new Error('en az bir özellik sütunu gerekli');
  if (n < p + 1) throw new Error(`${p} özellik için en az ${p + 1} tam kayıt gerekli (${n} var)`);

  const xm = Array.from({ length: p }, (_, j) => ortalama(X.map((r) => r[j])));
  const ym = ortalama(y);
  const A = Array.from({ length: p }, () => new Array<number>(p).fill(0));
  const b = new Array<number>(p).fill(0);
  for (let i = 0; i < n; i++) {
    const yc = y[i] - ym;
    for (let j = 0; j < p; j++) {
      const xj = X[i][j] - xm[j];
      b[j] += xj * yc;
      for (let k = j; k < p; k++) A[j][k] += xj * (X[i][k] - xm[k]);
    }
  }
  for (let j = 0; j < p; j++) for (let k = 0; k < j; k++) A[j][k] = A[k][j];

  const enBuyukKosegen = Math.max(...A.map((r, j) => r[j]));
  const tol = 1e-10 * Math.max(enBuyukKosegen, Number.MIN_VALUE);
  // Gauss eliminasyonu (kısmi pivot)
  const M = A.map((r, j) => [...r, b[j]]);
  for (let c = 0; c < p; c++) {
    let piv = c;
    for (let r = c + 1; r < p; r++) if (Math.abs(M[r][c]) > Math.abs(M[piv][c])) piv = r;
    if (Math.abs(M[piv][c]) <= tol) {
      throw new Error('özellik sütunları sabit ya da doğrusal bağımlı (ör. aynı bilgi iki sütunda); katsayılar tekil değil');
    }
    [M[c], M[piv]] = [M[piv], M[c]];
    for (let r = c + 1; r < p; r++) {
      const f = M[r][c] / M[c][c];
      for (let k = c; k <= p; k++) M[r][k] -= f * M[c][k];
    }
  }
  const beta = new Array<number>(p).fill(0);
  for (let c = p - 1; c >= 0; c--) {
    let t = M[c][p];
    for (let k = c + 1; k < p; k++) t -= M[c][k] * beta[k];
    beta[c] = t / M[c][c];
  }
  const kesisim = ym - beta.reduce((t, bj, j) => t + bj * xm[j], 0);

  let sse = 0, sst = 0;
  for (let i = 0; i < n; i++) {
    const tahmin = kesisim + beta.reduce((t, bj, j) => t + bj * X[i][j], 0);
    sse += (y[i] - tahmin) ** 2;
    sst += (y[i] - ym) ** 2;
  }
  const r2 = r2Hesapla(sse, sst);
  return {
    katsayilar: beta,
    kesisim,
    r2,
    r2Duzeltilmis: n - p - 1 > 0 ? 1 - ((1 - r2) * (n - 1)) / (n - p - 1) : null,
    mse: sse / n,
    n,
  };
}

/** R² (sklearn force_finite): sabit y'de mükemmel uyum 1, değilse 0. */
export function r2Hesapla(sse: number, sst: number): number {
  if (sst === 0) return sse === 0 ? 1 : 0;
  return 1 - sse / sst;
}

export function olsTahmin(model: Pick<OlsSonuc, 'katsayilar' | 'kesisim'>, x: number[]): number {
  return model.kesisim + model.katsayilar.reduce((t, b, j) => t + b * x[j], 0);
}

// ------------------------------------------------------------ rastgelelik

/** Tohumlu üreteç (mulberry32): aynı tohum → aynı dizi. [0, 1) döner. */
export function tohumluUretec(tohum: number): () => number {
  let a = tohum >>> 0;
  return () => {
    a = (a + 0x6d2b79f5) >>> 0;
    let t = a;
    t = Math.imul(t ^ (t >>> 15), t | 1);
    t ^= t + Math.imul(t ^ (t >>> 7), t | 61);
    return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
  };
}

/** Yapılandırmadan tohum: geçersizse varsayılan 42 (Python dışa aktarımıyla aynı). */
export function tohumAl(v: unknown): number {
  const n = sayiCoz(v);
  return n === null ? 42 : Math.trunc(n);
}

/** Fisher–Yates; kopya döner. */
export function karistir<T>(x: T[], rng: () => number): T[] {
  const a = [...x];
  for (let i = a.length - 1; i > 0; i--) {
    const j = Math.floor(rng() * (i + 1));
    [a[i], a[j]] = [a[j], a[i]];
  }
  return a;
}

// ------------------------------------------------------------ kümeleme

/** z-standartlaştırma (sklearn StandardScaler: kitle std, sabit sütunda ölçek 1). */
export function standartlastir(X: number[][]): { Z: number[][]; ort: number[]; olcek: number[] } {
  const p = X[0]?.length ?? 0;
  const ort = Array.from({ length: p }, (_, j) => ortalama(X.map((r) => r[j])));
  const olcek = Array.from({ length: p }, (_, j) => {
    const s = stdSapma(X.map((r) => r[j]), 0) ?? 0;
    return s === 0 ? 1 : s;
  });
  return { Z: X.map((r) => r.map((v, j) => (v - ort[j]) / olcek[j])), ort, olcek };
}

const kareUzaklik = (a: number[], b: number[]) => {
  let t = 0;
  for (let i = 0; i < a.length; i++) t += (a[i] - b[i]) ** 2;
  return t;
};

export interface KMeansSonuc {
  etiketler: number[];
  merkezler: number[][];
  /** Küme içi kare uzaklıklar toplamı (sklearn inertia_). */
  eylemsizlik: number;
}

function kMeansTek(X: number[][], k: number, maksIter: number, rng: () => number): KMeansSonuc {
  const n = X.length;
  // k-means++ başlangıcı: sonraki merkez, en yakın merkeze kare uzaklıkla orantılı seçilir.
  const merkezler: number[][] = [[...X[Math.floor(rng() * n)]]];
  const d2 = X.map((x) => kareUzaklik(x, merkezler[0]));
  while (merkezler.length < k) {
    const toplam = d2.reduce((a, b) => a + b, 0);
    let idx = 0;
    if (toplam > 0) {
      let r = rng() * toplam;
      for (idx = 0; idx < n - 1; idx++) {
        r -= d2[idx];
        if (r <= 0) break;
      }
    } else {
      idx = Math.floor(rng() * n);
    }
    merkezler.push([...X[idx]]);
    for (let i = 0; i < n; i++) d2[i] = Math.min(d2[i], kareUzaklik(X[i], X[idx]));
  }

  const etiketler = new Array<number>(n).fill(-1);
  for (let iter = 0; iter < maksIter; iter++) {
    let degisti = false;
    for (let i = 0; i < n; i++) {
      let en = 0, enD = Infinity;
      for (let c = 0; c < k; c++) {
        const d = kareUzaklik(X[i], merkezler[c]);
        if (d < enD) { enD = d; en = c; }
      }
      if (etiketler[i] !== en) { etiketler[i] = en; degisti = true; }
    }
    if (!degisti) break;
    const toplam = Array.from({ length: k }, () => new Array<number>(X[0].length).fill(0));
    const sayi = new Array<number>(k).fill(0);
    for (let i = 0; i < n; i++) {
      sayi[etiketler[i]]++;
      for (let j = 0; j < X[i].length; j++) toplam[etiketler[i]][j] += X[i][j];
    }
    for (let c = 0; c < k; c++) {
      if (sayi[c] > 0) {
        merkezler[c] = toplam[c].map((t) => t / sayi[c]);
      } else {
        // Boş küme: merkezine en uzak noktaya taşı (sklearn de yeniden konumlar).
        let uzak = 0, uzakD = -1;
        for (let i = 0; i < n; i++) {
          const d = kareUzaklik(X[i], merkezler[etiketler[i]]);
          if (d > uzakD) { uzakD = d; uzak = i; }
        }
        merkezler[c] = [...X[uzak]];
      }
    }
  }
  let eylemsizlik = 0;
  for (let i = 0; i < n; i++) eylemsizlik += kareUzaklik(X[i], merkezler[etiketler[i]]);
  return { etiketler, merkezler, eylemsizlik };
}

/**
 * K-Means (Lloyd, k-means++ başlangıç, nInit denemeden en düşük eylemsizlik).
 * Tohumlu: aynı veri + tohum → aynı sonuç. Kümeler büyükten küçüğe yeniden
 * numaralanır (etiket 0 = en kalabalık) — çıktı başlangıç şansına bağlı olmasın.
 */
export function kMeans(X: number[][], k: number, secenek: { maksIter?: number; nInit?: number; tohum?: number } = {}): KMeansSonuc {
  const rng = tohumluUretec(secenek.tohum ?? 42);
  let en: KMeansSonuc | null = null;
  for (let d = 0; d < (secenek.nInit ?? 10); d++) {
    const s = kMeansTek(X, k, secenek.maksIter ?? 300, rng);
    if (!en || s.eylemsizlik < en.eylemsizlik) en = s;
  }
  const sonuc = en!;
  const boyut = new Array<number>(k).fill(0);
  for (const e of sonuc.etiketler) boyut[e]++;
  const sira = Array.from({ length: k }, (_, c) => c).sort((a, b) => boyut[b] - boyut[a] || a - b);
  const yeni = new Array<number>(k);
  sira.forEach((eski, i) => { yeni[eski] = i; });
  return {
    etiketler: sonuc.etiketler.map((e) => yeni[e]),
    merkezler: sira.map((eski) => sonuc.merkezler[eski]),
    eylemsizlik: sonuc.eylemsizlik,
  };
}

/**
 * Ortalama silhouette (sklearn silhouette_score, öklid). Tek elemanlı kümede
 * s=0 (eski motor 1 veriyordu → skor şişiyordu); a=b=0'da s=0 (eski: NaN).
 * 2 ≤ küme sayısı ≤ n-1 değilse null. n > maksOrnek ise tohumlu alt örnekte
 * hesaplanır (O(n²)); kullanılan örnek büyüklüğü döner.
 */
export function silhouette(X: number[][], etiketler: number[], secenek: { maksOrnek?: number; tohum?: number } = {}):
  { skor: number | null; ornekN: number } {
  let idx = X.map((_, i) => i);
  const maks = secenek.maksOrnek ?? 3000;
  if (idx.length > maks) idx = karistir(idx, tohumluUretec(secenek.tohum ?? 42)).slice(0, maks);
  const n = idx.length;
  const kumeler = [...new Set(idx.map((i) => etiketler[i]))];
  if (kumeler.length < 2 || kumeler.length > n - 1) return { skor: null, ornekN: n };
  const kSira = new Map(kumeler.map((c, i) => [c, i]));
  const boyut = new Array<number>(kumeler.length).fill(0);
  for (const i of idx) boyut[kSira.get(etiketler[i])!]++;

  let toplam = 0;
  const uz = new Array<number>(kumeler.length);
  for (const i of idx) {
    uz.fill(0);
    for (const j of idx) {
      if (i === j) continue;
      uz[kSira.get(etiketler[j])!] += Math.sqrt(kareUzaklik(X[i], X[j]));
    }
    const kendi = kSira.get(etiketler[i])!;
    if (boyut[kendi] === 1) continue; // s=0
    const a = uz[kendi] / (boyut[kendi] - 1);
    let b = Infinity;
    for (let c = 0; c < kumeler.length; c++) {
      if (c !== kendi && boyut[c] > 0) b = Math.min(b, uz[c] / boyut[c]);
    }
    const m = Math.max(a, b);
    toplam += m === 0 ? 0 : (b - a) / m;
  }
  return { skor: toplam / n, ornekN: n };
}
