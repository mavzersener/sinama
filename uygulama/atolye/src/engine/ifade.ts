import { sayiCoz } from './istatistik';

/**
 * "Alan Ekle" (extend_field) düğümünün güvenli ifade dili.
 *
 * Eskiden ifade `new Function(..., "return (" + ifade + ");")` ile JavaScript
 * olarak çalıştırılıyordu: parantez kapatılıp istenen kod yazılabiliyordu.
 * İş akışları paylaşıldığı için (katalog, bulut) başkasının akışı sizin
 * tarayıcınızda SİZİN oturumunuzla keyfi kod çalıştırabilirdi. Ayrıca
 * arayüzdeki örnek (`CONCAT(ad, " ", soyad)`) JS'te tanımsız olduğundan hiç
 * çalışmıyordu.
 *
 * Burada ifade bir ağaca ayrıştırılır; ağaçta yalnız sayı, metin, sabit,
 * sütun, işleç, koşul ve BEYAZ LİSTELİ işlev çağrısı olabilir — üye erişimi
 * (`a.b`, `a[b]`) ve keyfi çağrı sözdiziminde yoktur. Değerler hep ilkel
 * (CSV hücreleri) olduğundan işleçler JS'in kendi kurallarıyla uygulanır:
 * `gelir * 2`, `ad + " " + soyad` eskisiyle birebir aynı sonucu verir.
 *
 * Sözdizimi:
 *   sütun           gelir, ilçe_adı      (boşluk/özel karakter: [Sütun Adı])
 *   sabit           12, 3.5, "metin", 'metin', true, false, null
 *   işleç           + - * / % **   == != === !== = <>   < <= > >=
 *                   && || !  (ya da AND OR NOT)   koşul ? a : b
 *   işlev           CONCAT UPPER LOWER TRIM LEN LEFT RIGHT MID ROUND ABS FLOOR
 *                   CEIL SQRT LOG LOG10 EXP POW MIN MAX TRUNC IF COALESCE
 *                   NUMBER TEXT; eski ifadeler için Math.round, Math.abs, …
 */

export type IfadeDugumu =
  | { t: 'deger'; v: number | string | boolean | null }
  | { t: 'sutun'; ad: string }
  | { t: 'birli'; op: '-' | '+' | '!'; x: IfadeDugumu }
  | { t: 'ikili'; op: string; a: IfadeDugumu; b: IfadeDugumu }
  | { t: 'kosul'; c: IfadeDugumu; a: IfadeDugumu; b: IfadeDugumu }
  | { t: 'cagri'; ad: string; args: IfadeDugumu[] };

export class IfadeHatasi extends Error {}

const AZAMI_UZUNLUK = 2000;
const AZAMI_DERINLIK = 100;

// ------------------------------------------------------------------ işlevler

type Islev = { en: number; ek: number; f: (...a: unknown[]) => unknown };
const sayi = (v: unknown) => Number(v);
const metin = (v: unknown) => (v === null || v === undefined ? '' : String(v));
/** Yarım değerleri sıfırdan uzağa yuvarlar (hesap tablosu gibi; Math.round -0.5 → -0). */
function yuvarla(x: unknown, n: unknown = 0): number {
  const f = 10 ** Math.trunc(sayi(n) || 0);
  const v = sayi(x);
  return (Math.sign(v) * Math.round(Math.abs(v) * f)) / f;
}

const ISLEVLER: Record<string, Islev> = {
  CONCAT: { en: 1, ek: Infinity, f: (...a) => a.map(metin).join('') },
  UPPER: { en: 1, ek: 1, f: (s) => metin(s).toLocaleUpperCase('tr-TR') },
  LOWER: { en: 1, ek: 1, f: (s) => metin(s).toLocaleLowerCase('tr-TR') },
  TRIM: { en: 1, ek: 1, f: (s) => metin(s).trim() },
  LEN: { en: 1, ek: 1, f: (s) => metin(s).length },
  LENGTH: { en: 1, ek: 1, f: (s) => metin(s).length },
  LEFT: { en: 2, ek: 2, f: (s, n) => metin(s).slice(0, Math.max(0, sayi(n))) },
  RIGHT: { en: 2, ek: 2, f: (s, n) => { const k = Math.max(0, sayi(n)); return k ? metin(s).slice(-k) : ''; } },
  MID: { en: 2, ek: 3, f: (s, bas, uz) => { const b = Math.max(1, sayi(bas)) - 1; return uz === undefined ? metin(s).slice(b) : metin(s).slice(b, b + Math.max(0, sayi(uz))); } },
  ROUND: { en: 1, ek: 2, f: yuvarla },
  ABS: { en: 1, ek: 1, f: (x) => Math.abs(sayi(x)) },
  FLOOR: { en: 1, ek: 1, f: (x) => Math.floor(sayi(x)) },
  CEIL: { en: 1, ek: 1, f: (x) => Math.ceil(sayi(x)) },
  CEILING: { en: 1, ek: 1, f: (x) => Math.ceil(sayi(x)) },
  SQRT: { en: 1, ek: 1, f: (x) => Math.sqrt(sayi(x)) },
  LOG: { en: 1, ek: 1, f: (x) => Math.log(sayi(x)) },
  LOG10: { en: 1, ek: 1, f: (x) => Math.log10(sayi(x)) },
  EXP: { en: 1, ek: 1, f: (x) => Math.exp(sayi(x)) },
  POW: { en: 2, ek: 2, f: (x, y) => sayi(x) ** sayi(y) },
  POWER: { en: 2, ek: 2, f: (x, y) => sayi(x) ** sayi(y) },
  MIN: { en: 1, ek: Infinity, f: (...a) => Math.min(...a.map(sayi)) },
  MAX: { en: 1, ek: Infinity, f: (...a) => Math.max(...a.map(sayi)) },
  TRUNC: { en: 1, ek: 1, f: (x) => Math.trunc(sayi(x)) },
  // IF tembel değerlendirilir (bkz. degerlendir); burada yalnız sayı denetimi için.
  IF: { en: 3, ek: 3, f: () => undefined },
  COALESCE: { en: 1, ek: Infinity, f: (...a) => a.find((v) => v !== null && v !== undefined && v !== '') ?? null },
  NUMBER: { en: 1, ek: 1, f: (x) => sayiCoz(x) },
  TEXT: { en: 1, ek: 1, f: metin },
};
// Eski (JS) ifadeler: Math.round(x) vb. JS anlamıyla çalışmaya devam eder.
const MATH: Record<string, Islev> = {
  'MATH.ROUND': { en: 1, ek: 1, f: (x) => Math.round(sayi(x)) },
  'MATH.ABS': ISLEVLER.ABS, 'MATH.FLOOR': ISLEVLER.FLOOR, 'MATH.CEIL': ISLEVLER.CEIL,
  'MATH.SQRT': ISLEVLER.SQRT, 'MATH.LOG': ISLEVLER.LOG, 'MATH.LOG10': ISLEVLER.LOG10,
  'MATH.EXP': ISLEVLER.EXP, 'MATH.POW': ISLEVLER.POW, 'MATH.MIN': ISLEVLER.MIN,
  'MATH.MAX': ISLEVLER.MAX, 'MATH.TRUNC': ISLEVLER.TRUNC,
};
const islevBul = (ad: string): Islev | undefined => ISLEVLER[ad] ?? MATH[ad];
export const ISLEV_ADLARI = Object.keys(ISLEVLER);

// ------------------------------------------------------------ sözcükleyici

type Belirtec =
  | { t: 'sayi'; v: number; k: number }
  | { t: 'metin'; v: string; k: number }
  | { t: 'ad'; v: string; k: number }
  | { t: 'koseli'; v: string; k: number }
  | { t: 'isaret'; v: string; k: number }
  | { t: 'son'; k: number };

const ISARETLER = ['===', '!==', '**', '==', '!=', '<=', '>=', '&&', '||', '<>',
  '<', '>', '=', '+', '-', '*', '/', '%', '!', '?', ':', '(', ')', ',', '.'];

function sozcukle(k: string): Belirtec[] {
  const b: Belirtec[] = [];
  let i = 0;
  while (i < k.length) {
    const c = k[i];
    if (/\s/.test(c)) { i++; continue; }
    const sayiEs = /^(\d+(\.\d*)?|\.\d+)([eE][+-]?\d+)?/.exec(k.slice(i));
    if (sayiEs) { b.push({ t: 'sayi', v: Number(sayiEs[0]), k: i }); i += sayiEs[0].length; continue; }
    if (c === '"' || c === "'") {
      let j = i + 1;
      let v = '';
      while (j < k.length && k[j] !== c) {
        if (k[j] === '\\' && j + 1 < k.length) {
          const e = k[j + 1];
          v += e === 'n' ? '\n' : e === 't' ? '\t' : e;
          j += 2;
        } else {
          v += k[j++];
        }
      }
      if (j >= k.length) throw new IfadeHatasi(`kapanmamış metin (konum ${i + 1})`);
      b.push({ t: 'metin', v, k: i });
      i = j + 1;
      continue;
    }
    if (c === '[') {
      const j = k.indexOf(']', i + 1);
      if (j < 0) throw new IfadeHatasi(`kapanmamış [sütun adı] (konum ${i + 1})`);
      b.push({ t: 'koseli', v: k.slice(i + 1, j).trim(), k: i });
      i = j + 1;
      continue;
    }
    const adEs = /^[\p{ID_Start}$_][\p{ID_Continue}$]*/u.exec(k.slice(i));
    if (adEs) { b.push({ t: 'ad', v: adEs[0], k: i }); i += adEs[0].length; continue; }
    const isaret = ISARETLER.find((s) => k.startsWith(s, i));
    if (!isaret) throw new IfadeHatasi(`beklenmeyen karakter '${c}' (konum ${i + 1})`);
    b.push({ t: 'isaret', v: isaret, k: i });
    i += isaret.length;
  }
  b.push({ t: 'son', k: k.length });
  return b;
}

// ------------------------------------------------------------- ayrıştırıcı

/** İfadeyi ağaca çevirir; bilinmeyen sütun/işlev ve sözdizimi hatası burada yakalanır. */
export function ifadeyiCoz(kaynak: string, sutunlar: string[]): IfadeDugumu {
  if (!kaynak.trim()) throw new IfadeHatasi('ifade boş');
  if (kaynak.length > AZAMI_UZUNLUK) throw new IfadeHatasi(`ifade çok uzun (en çok ${AZAMI_UZUNLUK} karakter)`);
  const b = sozcukle(kaynak);
  const var_ = new Set(sutunlar);
  let i = 0;
  let derinlik = 0;
  const bak = () => b[i];
  const isaretMi = (v: string) => { const x = b[i]; return x.t === 'isaret' && x.v === v; };
  // AND/OR/NOT işlev değil anahtar sözcüktür: ardından '(' gelebilir ("NOT (a > b)").
  // Bu adda bir sütun [köşeli] yazılır.
  const anahtar = (v: string) => { const x = b[i]; return x.t === 'ad' && x.v.toUpperCase() === v; };
  const bekle = (v: string) => {
    if (!isaretMi(v)) throw new IfadeHatasi(`'${v}' bekleniyordu (konum ${bak().k + 1})`);
    i++;
  };
  const in_ = <T,>(f: () => T): T => {
    if (++derinlik > AZAMI_DERINLIK) throw new IfadeHatasi('ifade çok derin');
    try { return f(); } finally { derinlik--; }
  };

  const ikiliSeviye = (alt: () => IfadeDugumu, ops: string[], kelimeler: Record<string, string> = {}) => (): IfadeDugumu => {
    let a = alt();
    for (;;) {
      const x = bak();
      let op: string | null = null;
      if (x.t === 'isaret' && ops.includes(x.v)) op = x.v;
      else for (const [kelime, karsilik] of Object.entries(kelimeler)) if (anahtar(kelime)) op = karsilik;
      if (!op) return a;
      i++;
      a = { t: 'ikili', op, a, b: alt() };
    }
  };

  const birincil = (): IfadeDugumu => in_(() => {
    const x = bak();
    if (x.t === 'sayi') { i++; return { t: 'deger', v: x.v }; }
    if (x.t === 'metin') { i++; return { t: 'deger', v: x.v }; }
    if (x.t === 'koseli') {
      i++;
      if (!var_.has(x.v)) throw new IfadeHatasi(`bilinmeyen sütun: "${x.v}"`);
      return { t: 'sutun', ad: x.v };
    }
    if (x.t === 'isaret' && x.v === '(') {
      i++;
      const d = ifade();
      bekle(')');
      return d;
    }
    if (x.t === 'ad') {
      i++;
      let ad = x.v;
      if (ad === 'Math' && isaretMi('.')) {
        i++;
        const y = bak();
        if (y.t !== 'ad') throw new IfadeHatasi(`Math. sonrası işlev adı bekleniyordu (konum ${y.k + 1})`);
        i++;
        ad = `Math.${y.v}`;
      }
      if (isaretMi('(')) {
        i++;
        const buyuk = ad.toUpperCase();
        const islev = islevBul(buyuk);
        if (!islev) throw new IfadeHatasi(`bilinmeyen işlev: ${ad} (kullanılabilir: ${ISLEV_ADLARI.join(', ')})`);
        const args: IfadeDugumu[] = [];
        if (!isaretMi(')')) {
          do { args.push(ifade()); } while (isaretMi(',') && ++i);
        }
        bekle(')');
        if (args.length < islev.en || args.length > islev.ek) {
          throw new IfadeHatasi(`${buyuk} ${islev.en === islev.ek ? islev.en : `${islev.en}–${islev.ek === Infinity ? '…' : islev.ek}`} bağımsız değişken alır, ${args.length} verildi`);
        }
        return { t: 'cagri', ad: buyuk, args };
      }
      if (ad.includes('.')) throw new IfadeHatasi(`beklenmeyen '.' (konum ${x.k + 1}): üye erişimi desteklenmez`);
      const kucuk = ad.toLowerCase();
      if (kucuk === 'true' || kucuk === 'false') return { t: 'deger', v: kucuk === 'true' };
      if (kucuk === 'null') return { t: 'deger', v: null };
      if (!var_.has(ad)) throw new IfadeHatasi(`bilinmeyen sütun: "${ad}"`);
      return { t: 'sutun', ad };
    }
    if (x.t === 'son') throw new IfadeHatasi('ifade yarım kaldı');
    throw new IfadeHatasi(`beklenmeyen '${(x as { v: string }).v}' (konum ${x.k + 1})`);
  });

  const birli = (): IfadeDugumu => in_(() => {
    const x = bak();
    if (x.t === 'isaret' && (x.v === '-' || x.v === '+' || x.v === '!')) { i++; return { t: 'birli', op: x.v, x: birli() }; }
    if (anahtar('NOT')) { i++; return { t: 'birli', op: '!', x: birli() }; }
    const taban = birincil();
    // ** sağdan birleşir ve birli işleçten güçlüdür (JS gibi).
    if (isaretMi('**')) { i++; return { t: 'ikili', op: '**', a: taban, b: birli() }; }
    return taban;
  });
  const carpim = ikiliSeviye(birli, ['*', '/', '%']);
  const toplam = ikiliSeviye(carpim, ['+', '-']);
  const karsilastirma = ikiliSeviye(toplam, ['<', '<=', '>', '>=']);
  const esitlik = ikiliSeviye(karsilastirma, ['==', '!=', '===', '!==', '=', '<>']);
  const ve = ikiliSeviye(esitlik, ['&&'], { AND: '&&' });
  const veya = ikiliSeviye(ve, ['||'], { OR: '||' });
  function ifade(): IfadeDugumu {
    return in_(() => {
      const c = veya();
      if (!isaretMi('?')) return c;
      i++;
      const a = ifade();
      bekle(':');
      return { t: 'kosul', c, a, b: ifade() };
    });
  }

  const sonuc = ifade();
  if (bak().t !== 'son') {
    const x = bak() as { v?: string; k: number };
    throw new IfadeHatasi(`beklenmeyen '${x.v ?? ''}' (konum ${x.k + 1})${x.v === '.' ? ': üye erişimi desteklenmez' : ''}`);
  }
  return sonuc;
}

// --------------------------------------------------------- değerlendirici

type Ilkel = number | string | boolean | null | undefined;

/** Ağacı bir satır için değerlendirir; işleçler JS kurallarıyla (değerler ilkel). */
export function ifadeyiDegerlendir(d: IfadeDugumu, satir: Record<string, unknown>): unknown {
  switch (d.t) {
    case 'deger': return d.v;
    case 'sutun': return satir[d.ad];
    case 'birli': {
      const x = ifadeyiDegerlendir(d.x, satir) as Ilkel;
      return d.op === '-' ? -(x as number) : d.op === '+' ? +(x as number) : !x;
    }
    case 'kosul':
      return ifadeyiDegerlendir(d.c, satir) ? ifadeyiDegerlendir(d.a, satir) : ifadeyiDegerlendir(d.b, satir);
    case 'cagri': {
      if (d.ad === 'IF') {
        return ifadeyiDegerlendir(d.args[0], satir) ? ifadeyiDegerlendir(d.args[1], satir) : ifadeyiDegerlendir(d.args[2], satir);
      }
      return islevBul(d.ad)!.f(...d.args.map((a) => ifadeyiDegerlendir(a, satir)));
    }
    case 'ikili': {
      if (d.op === '&&') { const a = ifadeyiDegerlendir(d.a, satir); return a ? ifadeyiDegerlendir(d.b, satir) : a; }
      if (d.op === '||') { const a = ifadeyiDegerlendir(d.a, satir); return a ? a : ifadeyiDegerlendir(d.b, satir); }
      const a = ifadeyiDegerlendir(d.a, satir) as Ilkel;
      const b = ifadeyiDegerlendir(d.b, satir) as Ilkel;
      const an = a as number;
      const bn = b as number;
      switch (d.op) {
        case '+': return (a as string) + (b as string);
        case '-': return an - bn;
        case '*': return an * bn;
        case '/': return an / bn;
        case '%': return an % bn;
        case '**': return an ** bn;
        // Eşitlik JS'teki gibi: == gevşek, === katı; = ve <> hesap tablosu yazımı.
        case '==': case '=': return a == b;
        case '!=': case '<>': return a != b;
        case '===': return a === b;
        case '!==': return a !== b;
        case '<': return an < bn;
        case '<=': return an <= bn;
        case '>': return an > bn;
        case '>=': return an >= bn;
      }
      throw new IfadeHatasi(`bilinmeyen işleç ${d.op}`);
    }
  }
}
