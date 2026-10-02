import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import type { Node } from '@xyflow/react';
import type { NodeData } from '../src/store/useStore';
import { executeNode, type ExecutionResult } from '../src/engine/executionEngine';
import { kanonikHash } from '../contracts/kanit';
import {
  metniCoz, kaynakOlustur, veriKaydet, veriAl, tabloyuGetir, depoyuTemizle, eskiVeriyiTasi, ONIZLEME_SATIR,
} from '../src/lib/veriDeposu';

const secenek = { hasHeader: true, delimiter: ',' };
const csvMetni = (n: number) => 'id,ad,tutar\n' + Array.from({ length: n }, (_, i) => `${i + 1},K${i},${(i * 7) % 100}`).join('\n');
const csvDugumu = (config: Record<string, unknown>): Node<NodeData> =>
  ({ id: 'csv', type: 'custom', position: { x: 0, y: 0 }, data: { label: 'CSV', type: 'csv_source', category: 'x', icon: 'x', color: '#000', config, status: 'idle' } }) as Node<NodeData>;
const kos = (config: Record<string, unknown>) => executeNode(csvDugumu(config), [], new Map<string, ExecutionResult>());

beforeEach(() => depoyuTemizle());
afterEach(() => vi.unstubAllGlobals());

describe('ayrıştırma', () => {
  it('dosyanın TAMAMI okunur (eskiden preview: 5000 → ilk 5000 satır)', () => {
    const t = metniCoz(csvMetni(12_000), secenek, 'buyuk.csv');
    expect(t.rows).toHaveLength(12_000);
    expect(t.rows[11_999]).toEqual({ id: 12_000, ad: 'K11999', tutar: (11_999 * 7) % 100 });
  });

  it('başlık kırpılır ve BOM atılır — sütun listesi ile satır anahtarları AYNI', () => {
    // Eskiden yalnız sütun listesi kırpılıyordu: row["yas"] hep undefined dönüyordu.
    const t = metniCoz('﻿ yas , gelir\n30,1000\n40,2000', secenek, 'b.csv');
    expect(t.columns).toEqual(['yas', 'gelir']);
    expect(t.rows[0]).toEqual({ yas: 30, gelir: 1000 });
  });

  it('başlıksız dosya: col_N, en geniş satıra göre', () => {
    const t = metniCoz('1,2\n3,4,5', { hasHeader: false, delimiter: ',' }, 'b.csv');
    expect(t.columns).toEqual(['col_0', 'col_1', 'col_2']);
    expect(t.rows[0]).toEqual({ col_0: 1, col_1: 2, col_2: '' });
  });

  it('kaynak: yalnız önizleme (10 satır) + sayılar; satırlar düğümde taşınmaz', () => {
    const t = metniCoz(csvMetni(500), secenek, 'k.csv');
    const k = kaynakOlustur('yerel:x', t, secenek);
    expect(k.onizleme).toHaveLength(ONIZLEME_SATIR);
    expect(k.rowCount).toBe(500);
    expect(JSON.stringify(k).length).toBeLessThan(2_000);
  });
});

describe('tabloyuGetir / csv_source', () => {
  it('depoda varsa depodan; TÜM satırlarla koşar', async () => {
    const t = metniCoz(csvMetni(7_000), secenek, 'v.csv');
    veriKaydet('yerel:a', t);
    const r = await kos({ _veriKaynagi: kaynakOlustur('yerel:a', t, secenek) });
    expect(r.status).toBe('success');
    expect(r.rowCount).toBe(7_000);
    expect((r.data.rows as unknown[]).length).toBe(7_000);
  });

  it('oturumsuz yüklenmiş ve depoda yok: açık hata (sessiz demo verisi DEĞİL)', async () => {
    const t = metniCoz(csvMetni(5), secenek, 'kayip.csv');
    const r = await kos({ _veriKaynagi: kaynakOlustur('yerel:yok', t, secenek) });
    expect(r.status).toBe('error');
    expect(r.error).toContain('"kayip.csv" bu oturumda yok');
  });

  it('sunucudaki kopya: bir kez indirilir (eşzamanlı istekler birleşir), aynı tablo, aynı kanıt hash\'i', async () => {
    const metin = csvMetni(300);
    const yerelTablo = metniCoz(metin, secenek, 's.csv');
    const kaynak = { ...kaynakOlustur('ds:9', yerelTablo, secenek, 9) };
    const fetchSahte = vi.fn(async (url: string) => {
      expect(url).toBe('/api/datasets/9/download');
      return new Response(metin, { status: 200 });
    });
    vi.stubGlobal('fetch', fetchSahte);
    const [a, b] = await Promise.all([tabloyuGetir(kaynak), tabloyuGetir(kaynak)]);
    expect(fetchSahte).toHaveBeenCalledTimes(1);
    expect(a).toBe(b);
    expect(a!.rows).toEqual(yerelTablo.rows);
    // Sayfa yenilemeden önce ve sonra kanıt paketinin veri hash'i aynı kalır.
    expect(await kanonikHash({ columns: a!.columns, rows: a!.rows }))
      .toBe(await kanonikHash({ columns: yerelTablo.columns, rows: yerelTablo.rows }));
    expect(veriAl('ds:9')).toBe(a);
  });

  it('sunucu 401 → oturum iletisi; kopya satır sayısı farklıysa uyarı', async () => {
    const t = metniCoz(csvMetni(10), secenek, 'x.csv');
    vi.stubGlobal('fetch', vi.fn(async () => new Response('', { status: 401 })));
    const r = await kos({ _veriKaynagi: kaynakOlustur('ds:1', t, secenek, 1) });
    expect(r.error).toContain('oturum açın');

    depoyuTemizle();
    vi.stubGlobal('fetch', vi.fn(async () => new Response(csvMetni(8), { status: 200 })));
    const r2 = await kos({ _veriKaynagi: kaynakOlustur('ds:2', t, secenek, 2) });
    expect(r2.status).toBe('success');
    expect(r2.data.uyarilar).toEqual(['Sunucudaki kopya 8 satır; yüklemede 10 satır görülmüştü.']);
  });

  it('eski kayıttan taşınan tam 5000 satırlık veri kesik olabilir diye uyarır', async () => {
    const t = metniCoz(csvMetni(5_000), secenek, 'eski.csv');
    const kaynak = eskiVeriyiTasi('n1', { rows: t.rows, columns: t.columns, filename: 'eski.csv' }, secenek)!;
    expect(kaynak.eskiKesikOlabilir).toBe(true);
    const r = await kos({ _veriKaynagi: kaynak });
    expect(String((r.data.uyarilar as string[])[0])).toContain('ilk 5000 satırını');
  });

  it('eski biçim (_uploadedData) doğrudan da çalışmaya devam eder', async () => {
    const r = await kos({ _uploadedData: { rows: [{ a: 1 }], columns: ['a'], filename: 'e.csv' } });
    expect(r.status).toBe('success');
    expect(r.rowCount).toBe(1);
  });
});
