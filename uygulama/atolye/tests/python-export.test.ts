import { describe, it, expect } from 'vitest';
import type { Node, Edge } from '@xyflow/react';
import type { NodeData } from '../src/store/useStore';
import { pythonBetigiUret } from '../src/lib/pythonExport';

/** Kısa düğüm kurucusu. */
function dugum(id: string, type: string, config: Record<string, unknown> = {}, label = type): Node<NodeData> {
  return {
    id,
    type: 'custom',
    position: { x: 0, y: 0 },
    data: { label, type, category: 'Test', icon: 'Box', color: '#fff', config, status: 'idle' },
  };
}

function kenar(source: string, target: string): Edge {
  return { id: `${source}->${target}`, source, target };
}

/** Boş bırakılan zorunlu alanların gerçekçi değerlerle doldurulması. */
function ornekAyar(tip: string): Record<string, unknown> {
  const ortak: Record<string, unknown> = {
    target: 'y', features: 'a, b', columns: 'a, b', column: 'a', value: '1',
    groupBy: 'g', newColumn: 'yeni', expression: 'a + b', leftKey: 'id', rightKey: 'id',
    keyColumns: 'id', itemsColumn: 'sepet', actualColumn: 'y', predictedColumn: 'p',
    personColumn: 'kisi', linkColumn: 'bag', latColumn: 'lat', lngColumn: 'lng',
    timeColumn: 'ts', entityColumn: 'e', contextColumn: 'c', xColumn: 'a', yColumn: 'b',
    caseNumber: '2026/1', officerId: 'PN-1', title: 'Başlık "tırnaklı"',
    connection: 'postgresql://x', url: 'https://x', dateColumn: 'ts', tcKimlik: '1',
  };
  return tip.startsWith('suc_') ? {} : ortak;
}

describe('pythonBetigiUret', () => {
  it('boş tuvalde kod üretmez, uyarı verir', () => {
    const { kod, uyarilar } = pythonBetigiUret([], []);
    expect(kod).toBe('');
    expect(uyarilar[0]).toMatch(/düğüm yok/);
  });

  it('temel boru hattını topolojik sırada yazar', () => {
    const nodes = [
      dugum('a', 'csv_source', { filename: 'veri.csv', delimiter: ',', hasHeader: true }),
      dugum('b', 'filter', { column: 'city', condition: 'equals', value: 'Ankara' }),
      dugum('c', 'export', { format: 'csv', filename: 'sonuc.csv' }),
    ];
    const edges = [kenar('a', 'b'), kenar('b', 'c')];
    const { kod, desteklenmeyen } = pythonBetigiUret(nodes, edges);

    expect(desteklenmeyen).toEqual([]);
    expect(kod).toContain('pd.read_csv(GIRDI_DIZINI / "veri.csv"');
    // Filtre bir önceki düğümün değişkenini tüketir.
    expect(kod).toContain('dugum_2 = dugum_1[_m == "ankara"]');
    expect(kod).toContain('dugum_2.to_csv(_yol, index=False');
    // Sıra: kaynak → filtre → export
    expect(kod.indexOf('[1]')).toBeLessThan(kod.indexOf('[2]'));
    expect(kod.indexOf('[2]')).toBeLessThan(kod.indexOf('[3]'));
  });

  it('yalnız kullanılan importları ve yardımcıları yazar', () => {
    const sade = pythonBetigiUret([dugum('a', 'csv_source', { filename: 'v.csv' })], []);
    expect(sade.kod).not.toContain('sklearn');
    expect(sade.kod).not.toContain('def _ozellik_hedef');

    const ml = pythonBetigiUret(
      [dugum('a', 'csv_source', { filename: 'v.csv' }), dugum('b', 'random_forest', { target: 'y', task: 'classification', nEstimators: 50, testSize: 20 })],
      [kenar('a', 'b')],
    );
    expect(ml.kod).toContain('from sklearn.ensemble import RandomForestClassifier');
    expect(ml.kod).toContain('def _ozellik_hedef');
    expect(ml.kod).toContain('RandomForestClassifier(n_estimators=50, random_state=42)');
    expect(ml.kod).toContain('pip install').valueOf();
    expect(ml.kod).toMatch(/pip install .*scikit-learn/);
  });

  it('kolluk kaynakları sahte veri üretmez, betiği durdurur', () => {
    const { kod, uyarilar } = pythonBetigiUret(
      [dugum('a', 'anpr_source', { plate: '34ABC123', legalBasis: '2559-md-4', kvkkClass: 'Kisitli' })],
      [],
    );
    expect(kod).toContain('raise NotImplementedError');
    expect(kod).toContain('2559-md-4');
    expect(kod).not.toMatch(/random|Math\.random/i);
    expect(uyarilar.join(' ')).toMatch(/ANPR/);
  });

  it("suc_* düğümleri suc_analizi çekirdeğini çağırır", () => {
    const { kod } = pythonBetigiUret(
      [dugum('a', 'csv_source', { filename: 'v.csv' }), dugum('b', 'suc_frekans', { alan: 'tur' })],
      [kenar('a', 'b')],
    );
    expect(kod).toContain('_suc_arac("frekans", _arg)');
    // Kamusal gömülü giriş: istek bağlamını kendisi kurar. İç _arac_yurut
    // bağlamsız çağrılınca 23 araç çöküyor, kalanlarda meta kayboluyordu.
    expect(kod).toContain('from suc_analizi.arayuz.sunucu import arac_calistir');
    expect(kod).not.toMatch(/_arac_yurut|_basari_paketi/);
    expect(kod).toContain('"satirlar": dugum_1.head(5000).to_dict("records")');
  });

  it('bilinmeyen düğüm tipini işaretler ve betiği durdurur', () => {
    const { kod, desteklenmeyen, uyarilar } = pythonBetigiUret([dugum('a', 'hayali_dugum', { x: 1 })], []);
    expect(desteklenmeyen).toContain('hayali_dugum');
    expect(kod).toContain('raise NotImplementedError');
    expect(uyarilar.join(' ')).toMatch(/hayali_dugum/);
  });

  it('rapor üreten düğümün ardında tablo AYNEN geçer (tarayıcı motoruyla aynı kural)', () => {
    // Eskiden bu düğüme boş pd.DataFrame() verilip "rapor üretiyor" uyarısı
    // basılıyordu; tarayıcı motoru da boş veri veriyordu (demo ve Hedeften
    // Akış zincirleri bu yüzden kırılıyordu).
    const { kod, uyarilar } = pythonBetigiUret(
      [
        dugum('a', 'csv_source', { filename: 'v.csv' }),
        dugum('b', 'statistics', { columns: '', stats: ['count', 'mean'] }),
        dugum('c', 'sort', { columns: 'x', order: 'asc' }),
      ],
      [kenar('a', 'b'), kenar('b', 'c')],
    );
    expect(kod).toContain('dugum_3 = dugum_1.sort_values(');
    expect(kod).toContain('# Girdi "statistics" rapor üretir; veri tablosu önceki adımdan aynen geçer (dugum_1).');
    expect(kod).not.toContain('pd.DataFrame().sort_values');
    expect(uyarilar.join(' ')).not.toMatch(/rapor üretiyor/);
  });

  it('uyarı: bilinmeyen koşul betiği durdurur (eskiden sessizce count_greater_than)', () => {
    const { kod, uyarilar } = pythonBetigiUret(
      [dugum('a', 'csv_source', { filename: 'v.csv' }), dugum('b', 'alert', { condition: 'mean_above', threshold: 3 })],
      [kenar('a', 'b')],
    );
    expect(kod).toContain('raise ValueError("Bilinmeyen uyarı koşulu: mean_above")');
    expect(kod).not.toContain('len(dugum_1) > 3');
    expect(uyarilar.join(' ')).toMatch(/bilinmeyen uyarı koşulu "mean_above"/);
  });

  it('iki rapor üst üste: tablo ikisinden de geçer; ajan raporun kendisini alır', () => {
    const { kod } = pythonBetigiUret(
      [
        dugum('a', 'csv_source', { filename: 'v.csv' }),
        dugum('b', 'data_quality', { columns: '' }),
        dugum('c', 'statistics', { columns: '', stats: ['mean'] }),
        dugum('d', 'agent_insight', { question: 'yorumla' }),
        dugum('e', 'sort', { columns: 'x', order: 'desc' }),
      ],
      [kenar('a', 'b'), kenar('b', 'c'), kenar('c', 'd'), kenar('d', 'e')],
    );
    expect(kod).toContain('_kols = _kolonlar(dugum_1,');           // istatistik CSV tablosunda
    expect(kod).toContain('json.loads(json.dumps(dugum_3, default=str))'); // ajan: istatistik raporu
    expect(kod).toContain('import json');
    expect(kod).toContain('dugum_5 = dugum_1.sort_values(');     // üç rapordan sonra hâlâ CSV
  });

  it('çift girdili join sağ tabloyu bağlar', () => {
    const { kod } = pythonBetigiUret(
      [
        dugum('a', 'csv_source', { filename: 'sol.csv' }),
        dugum('b', 'csv_source', { filename: 'sag.csv' }),
        dugum('c', 'join', { joinType: 'full', leftKey: 'id', rightKey: 'user_id' }),
      ],
      [kenar('a', 'c'), kenar('b', 'c')],
    );
    expect(kod).toContain('pd.merge(dugum_1, dugum_2, left_on="id"');
    expect(kod).toContain('how="outer"');
  });

  it('metin değerlerini güvenle kaçırır (kod enjeksiyonu yok)', () => {
    const { kod } = pythonBetigiUret(
      [dugum('a', 'csv_source', { filename: 'a".csv"; import os; os.system("x")' })],
      [],
    );
    expect(kod).toContain('pd.read_csv(GIRDI_DIZINI / "a\\".csv\\"; import os; os.system(\\"x\\")"');
  });

  /**
   * f-string süslü parantezi içinde çift tırnak Python 3.12'den ÖNCE
   * SyntaxError'dur — betik hiç çalışmaz. Bu tuzağa iki kez düşüldüğü için
   * tüm düğüm tipleri üzerinde yapısal olarak taranıyor.
   */
  function fStringCakismasi(kod: string): string[] {
    const hatali: string[] = [];
    for (const satir of kod.split('\n')) {
      for (let i = 0; i < satir.length - 1; i++) {
        if (satir[i] !== 'f' || satir[i + 1] !== '"') continue;
        if (i > 0 && /[\w"]/.test(satir[i - 1])) continue;
        let derinlik = 0;
        for (let j = i + 2; j < satir.length; j++) {
          const c = satir[j];
          if (c === '{') derinlik++;
          else if (c === '}') derinlik = Math.max(0, derinlik - 1);
          else if (c === '"') {
            if (derinlik > 0) hatali.push(satir.trim());
            break;
          }
        }
        break;
      }
    }
    return hatali;
  }

  it('hiçbir düğüm tipi geçersiz f-string üretmez', async () => {
    const { nodeDefinitions } = await import('../src/nodes/nodeDefinitions');
    // Her tipten bir düğüm + hepsini besleyen tek bir CSV kaynağı.
    const kaynak = dugum('kaynak', 'csv_source', { filename: 'v.csv' });
    const hepsi = nodeDefinitions
      .filter((d) => d.type !== 'csv_source')
      .map((d) => dugum(`n_${d.type}`, d.type, { ...d.defaultConfig, ...ornekAyar(d.type) }, d.label));
    const edges = hepsi.filter((n) => (n.data.type as string) !== 'csv_source').map((n) => kenar('kaynak', n.id));

    const { kod, desteklenmeyen } = pythonBetigiUret([kaynak, ...hepsi], edges);
    expect(fStringCakismasi(kod)).toEqual([]);
    // Katalogdaki her tip için bir üreteç olmalı (suc_* ve kolluk dahil).
    expect(desteklenmeyen).toEqual([]);
  });

  it('çevrimdeki düğümleri atlar ve uyarır', () => {
    const { uyarilar } = pythonBetigiUret(
      [dugum('a', 'filter', { column: 'x', condition: 'equals', value: '1' }), dugum('b', 'sort', { columns: 'x' })],
      [kenar('a', 'b'), kenar('b', 'a')],
    );
    expect(uyarilar.join(' ')).toMatch(/çevrim/);
  });
});
