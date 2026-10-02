import { describe, it, expect, afterEach } from 'vitest';
import type { Node, Edge } from '@xyflow/react';
import type { NodeData } from '../src/store/useStore';
import { executeNode, type ExecutionResult } from '../src/engine/executionEngine';
import { ifadeyiCoz, ifadeyiDegerlendir, IfadeHatasi } from '../src/engine/ifade';

const satirlar: Record<string, unknown>[] = [
  { gelir: 1200, gider: 300, ad: 'ali', soyad: 'yılmaz', il: 'istanbul', puan: 2.5, bos: null, metinSayi: '37,5', 'Sütun Adı': 7 },
  { gelir: 0, gider: 50, ad: '', soyad: 'kaya', il: 'izmir', puan: -2.5, bos: '', metinSayi: 'x', 'Sütun Adı': 0 },
  { gelir: -40, gider: -40, ad: 'Ece', soyad: 'Şen', il: 'ığdır', puan: 1.005, bos: 0, metinSayi: '12', 'Sütun Adı': -3 },
];
const kolonlar = Object.keys(satirlar[0]);
const deg = (ifade: string, satir = satirlar[0]) => ifadeyiDegerlendir(ifadeyiCoz(ifade, kolonlar), satir);

describe('JS ile birebir aynı sonuç (ortak alt küme)', () => {
  // Kâhin YALNIZ testte: aynı ifade JS olarak çalıştırılır ve sonuçlar karşılaştırılır.
  const JS_UYUMLU = [
    'gelir * 2', 'gelir - gider', 'gelir / gider', 'gelir % 7', 'gelir ** 2', '-gelir + +gider',
    'ad + " " + soyad', 'gelir + ad', 'gelir + gider + "x"', '"x" + gelir + gider',
    'gelir > gider', 'gelir >= 1200', 'gelir == 1200', 'gelir != gider', 'gelir === "1200"', 'gelir == "1200"',
    'bos == null', 'bos === null', 'gelir > 100 && gider < 100', 'gelir > 100 || gider > 100', '!gelir',
    'gelir > 1000 ? "yüksek" : gelir > 0 ? "orta" : "düşük"', 'ad || "adsız"', 'gelir && soyad',
    'Math.round(puan)', 'Math.abs(gider)', 'Math.floor(puan)', 'Math.max(gelir, gider, 5)', 'Math.pow(2, 3)',
    '(gelir + gider) * 2 - gider / 5', '1 < 2 < 3', 'gelir * 1.18', '.5 + 1e2',
  ];
  it.each(JS_UYUMLU)('%s', (ifade) => {
    for (const s of satirlar) {
      const js = new Function(...kolonlar.filter((k) => /^\w+$/.test(k)), `return (${ifade});`)(
        ...kolonlar.filter((k) => /^\w+$/.test(k)).map((k) => s[k]));
      expect(deg(ifade, s)).toStrictEqual(js);
    }
  });
});

describe('işlevler ve sözdizimi', () => {
  it('arayüzdeki örnek CONCAT artık çalışır (eskiden JS\'te tanımsızdı)', () => {
    expect(deg('CONCAT(ad, " ", soyad)')).toBe('ali yılmaz');
    expect(deg('CONCAT(bos, "-", gelir)')).toBe('-1200'); // null → ''
  });

  it('Türkçe büyük/küçük harf (i→İ, ı→I)', () => {
    expect(deg('UPPER(il)')).toBe('İSTANBUL');
    expect(deg('LOWER("IĞDIR")')).toBe('ığdır');
  });

  it('metin işlevleri', () => {
    expect(deg('LEN(soyad)')).toBe(6);
    expect(deg('LEFT(soyad, 3)')).toBe('yıl');
    expect(deg('RIGHT(soyad, 3)')).toBe('maz');
    expect(deg('RIGHT(soyad, 0)')).toBe('');
    expect(deg('MID(soyad, 2, 3)')).toBe('ılm');
    expect(deg('TRIM("  a  ")')).toBe('a');
    expect(deg('TEXT(gelir) + 1')).toBe('12001');
  });

  it('ROUND yarımı sıfırdan uzağa yuvarlar; Math.round JS anlamını korur', () => {
    expect(deg('ROUND(puan)')).toBe(3);
    expect(deg('ROUND(puan)', satirlar[1])).toBe(-3);
    expect(deg('Math.round(puan)', satirlar[1])).toBe(-2);
    expect(deg('ROUND(1234.5678, 2)')).toBe(1234.57);
  });

  it('IF tembel, COALESCE, NUMBER (ondalık virgül), sabitler, anahtar sözcükler', () => {
    expect(deg('IF(gelir > 0, "var", "yok")')).toBe('var');
    expect(deg('COALESCE(bos, ad, "x")')).toBe('ali');
    expect(deg('COALESCE(bos, ad, "x")', satirlar[1])).toBe('x'); // '' ve null atlanır
    expect(deg('NUMBER(metinSayi) * 2')).toBe(75);
    expect(deg('NUMBER(metinSayi)', satirlar[1])).toBe(null);
    expect(deg('gelir > 0 AND NOT (gider > 1000) OR false')).toBe(true);
    expect(deg('TRUE = true')).toBe(true);
    expect(deg('gelir <> gider')).toBe(true);
  });

  it('[köşeli] sütun adı: boşluk ve özel karakterli sütunlar', () => {
    expect(deg('[Sütun Adı] * 10')).toBe(70);
  });
});

describe('güvenlik: kod çalıştırma sözdizimde YOK', () => {
  afterEach(() => { delete (globalThis as Record<string, unknown>).__ele; });
  const SALDIRI = [
    '0); globalThis.__ele = 1; (0',
    'gelir.constructor.constructor("globalThis.__ele = 1")()',
    'constructor.constructor("return this")()',
    '(() => 1)()',
    'globalThis',
    'window.location',
    'this',
    'gelir["constructor"]',
    '`${gelir}`',
    'eval("1")',
    'Function("return 1")()',
    'fetch("https://ornek.test")',
    'import("x")',
    'Math.constructor',
    'gelir; 1',
    'a = 1; globalThis.__ele = 1',
  ];
  it.each(SALDIRI)('reddedilir: %s', (ifade) => {
    expect(() => ifadeyiCoz(ifade, kolonlar)).toThrow(IfadeHatasi);
    expect((globalThis as Record<string, unknown>).__ele).toBeUndefined();
  });

  it('çok uzun ve çok derin ifade reddedilir (yığın taşması yok)', () => {
    expect(() => ifadeyiCoz('1+'.repeat(1500) + '1', kolonlar)).toThrow(/çok uzun/);
    expect(() => ifadeyiCoz('('.repeat(300) + '1' + ')'.repeat(300), kolonlar)).toThrow(/çok derin/);
  });
});

describe('hata iletileri', () => {
  const hata = (ifade: string) => { try { ifadeyiCoz(ifade, kolonlar); return ''; } catch (e) { return (e as Error).message; } };
  it('bilinmeyen sütun / işlev, yanlış sayı, sözdizimi', () => {
    expect(hata('boyleBirSutunYok + 1')).toBe('bilinmeyen sütun: "boyleBirSutunYok"');
    expect(hata('[Yok Böyle]')).toBe('bilinmeyen sütun: "Yok Böyle"');
    expect(hata('FOO(1)')).toMatch(/^bilinmeyen işlev: FOO \(kullanılabilir: CONCAT, UPPER/);
    expect(hata('ROUND()')).toBe('ROUND 1–2 bağımsız değişken alır, 0 verildi');
    expect(hata('IF(1, 2)')).toBe('IF 3 bağımsız değişken alır, 2 verildi');
    expect(hata('"kapanmadı')).toMatch(/kapanmamış metin/);
    expect(hata('gelir +')).toBe('ifade yarım kaldı');
    expect(hata('gelir gider')).toMatch(/beklenmeyen 'gider'/);
    expect(hata('gelir.toFixed(2)')).toMatch(/üye erişimi desteklenmez/);
    expect(hata('   ')).toBe('ifade boş');
  });
});

describe('Alan Ekle düğümü', () => {
  const d = (id: string, type: string, config: Record<string, unknown>): Node<NodeData> =>
    ({ id, type: 'custom', position: { x: 0, y: 0 }, data: { label: id, type, category: 'x', icon: 'x', color: '#000', config, status: 'idle' } }) as Node<NodeData>;
  const kos = async (expression: string) => {
    const sonuclar = new Map<string, ExecutionResult>();
    sonuclar.set('csv', await executeNode(d('csv', 'csv_source', { _uploadedData: { rows: satirlar, columns: kolonlar, filename: 'f.csv' } }), [], sonuclar));
    return executeNode(d('x', 'extend_field', { newColumn: 'yeni', expression }), [{ id: 'e', source: 'csv', target: 'x' } as Edge], sonuclar);
  };

  it('CONCAT ve [köşeli] sütunla yeni sütun üretir', async () => {
    const r = await kos('CONCAT(UPPER(ad), " / ", [Sütun Adı])');
    expect(r.status).toBe('success');
    expect((r.data.rows as Record<string, unknown>[]).map((x) => x.yeni)).toEqual(['ALİ / 7', ' / 0', 'ECE / -3']);
  });

  it('saldırı ifadesi derlenmez, hiçbir satır işlenmez', async () => {
    const r = await kos('0); globalThis.__ele = 1; (0');
    expect(r.status).toBe('error');
    expect(r.error).toMatch(/^Expression could not be compiled: /);
    expect((globalThis as Record<string, unknown>).__ele).toBeUndefined();
  });
});
