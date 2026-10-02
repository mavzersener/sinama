/* eslint-disable @typescript-eslint/no-explicit-any -- test, dinamik paket JSON'unu okur */
/**
 * Sınama A6 — DataFlow `tests/kanit-uctan-uca.test.ts`'in karşılığı (E2).
 *
 * DEĞİŞTİRİLMEMİŞ JS yürütücüsü (evidence_export düğümü) GERÇEK Sınama arka ucuna
 * (Python/FastAPI, uygulama/kanit_defteri.py) kayıt yapar; indirilen paket DataFlow'un
 * bağımsız Python doğrulayıcısıyla (scripts/kanit_dogrula.py) denetlenir.
 *
 * DataFlow'dan farklar: Hono uygulaması yerine gerçek sunucu (fetch ona yönlenir); "oturum
 * yok" durumu yerine "sunucuya ulaşılamıyor" (Sınama'da oturum yok — ADR-004 md. 3); aktör
 * yerel kullanıcıdır. Sunucuyu `tests/test_atolye_kanit_uctan_uca.py` kurar ve şu ortam
 * değişkenlerini verir: SINAMA_ATOLYE_URL, SINAMA_KANIT_DIZINI, KANIT_PY.
 */
import { describe, it, expect, vi, beforeAll, afterAll, beforeEach } from 'vitest';
import { spawnSync } from 'node:child_process';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import type { Node, Edge } from '@xyflow/react';
import { executeNode, type ExecutionResult } from '../../src/engine/executionEngine';
import { kanonikHash } from '../../contracts/kanit';
import type { NodeData } from '../../src/store/useStore';

const SUNUCU = process.env.SINAMA_ATOLYE_URL ?? '';
const KANIT = process.env.SINAMA_KANIT_DIZINI ?? '';
const PY = process.env.KANIT_PY ?? '';
if (!SUNUCU || !KANIT || !PY) {
  throw new Error('SINAMA_ATOLYE_URL, SINAMA_KANIT_DIZINI ve KANIT_PY gerekli — tests/test_atolye_kanit_uctan_uca.py çalıştırır');
}
const ULASILAMAZ = 'http://127.0.0.1:9';
const durum = { taban: SUNUCU };
const gercekFetch = globalThis.fetch;
const DOGRULAYICI = path.resolve(import.meta.dirname, '../../scripts/kanit_dogrula.py');

const SATIRLAR = [
  { olay_id: 'E1', il: 'İstanbul', ilçe: 'Şişli', zarar_tl: 1500, oran: 0.1, tarih: new Date('2026-03-01T10:00:00Z'), not: null },
  { olay_id: 'E2', il: 'Ağrı', ilçe: 'Doğubayazıt', zarar_tl: 1.0, oran: -2.5e-7, tarih: new Date('2026-03-02T11:30:00Z'), not: 'çğıöşü "tırnak"\n' },
  { olay_id: 'E3', il: 'Iğdır', ilçe: 'Merkez', zarar_tl: 123456789012345680000, oran: 1e21, tarih: new Date('2026-03-03T00:00:00Z'), not: '' },
];

const dugum = (id: string, type: string, config: Record<string, unknown>) =>
  ({ id, type: 'custom', position: { x: 0, y: 0 }, data: { type, label: id, config } }) as unknown as Node<NodeData>;
const EDGES = [{ id: 'e', source: 'src', target: 'kanit', sourceHandle: 'output', targetHandle: 'input' }] as Edge[];

let dizin: string;
let yakalanan: { icerik: string; ad: string } | null = null;

async function kos(kaynakConfig: Record<string, unknown>, kanitConfig: Record<string, unknown> = { caseNumber: '2026/77', officerId: 'PN-4242' }) {
  const sonuclar = new Map<string, ExecutionResult>();
  sonuclar.set('src', await executeNode(dugum('src', 'csv_source', kaynakConfig), EDGES, sonuclar));
  return executeNode(dugum('kanit', 'evidence_export', kanitConfig), EDGES, sonuclar);
}
const gercekKaynak = { filename: 'olaylar.csv', _uploadedData: { rows: SATIRLAR, columns: Object.keys(SATIRLAR[0]), filename: 'olaylar.csv' } };

function dogrula(paketYolu: string, ...ek: string[]) {
  const r = spawnSync(PY, [DOGRULAYICI, paketYolu, ...ek], { encoding: 'utf8', env: { ...process.env, PYTHONUTF8: '1' } });
  return { kod: r.status, cikti: `${r.stdout}${r.stderr}` };
}
const defterMakbuzlari = () => fs.readFileSync(path.join(KANIT, 'defter.jsonl'), 'utf8').split('\n').filter((s) => s.trim()).map((s) => JSON.parse(s));

beforeAll(() => {
  dizin = fs.mkdtempSync(path.join(os.tmpdir(), 'sinama-kanit-uu-'));
  vi.stubGlobal('fetch', (url: string, init?: RequestInit) => gercekFetch(url.startsWith('/') ? durum.taban + url : url, init));
  vi.stubGlobal('document', {
    createElement: () => {
      const a: Record<string, unknown> = { click: () => undefined };
      return new Proxy(a, { set: (h, k, v) => { h[k as string] = v; if (k === 'download' && yakalanan) yakalanan.ad = v; return true; } });
    },
    body: { appendChild: () => undefined, removeChild: () => undefined },
  });
  vi.spyOn(URL, 'createObjectURL').mockImplementation((b: Blob | MediaSource) => {
    yakalanan = { icerik: '', ad: '' };
    const y = yakalanan;
    (b as Blob).text().then((t) => { y.icerik = t; });
    return 'blob:test';
  });
  vi.spyOn(URL, 'revokeObjectURL').mockImplementation(() => undefined);
});
afterAll(() => {
  vi.unstubAllGlobals();
  fs.rmSync(dizin, { recursive: true, force: true });
});
beforeEach(() => { durum.taban = SUNUCU; yakalanan = null; });

async function indirilen(): Promise<any> {
  await new Promise((r) => setTimeout(r, 0)); // Blob.text() çözülsün
  expect(yakalanan, 'paket indirilmedi').not.toBeNull();
  return JSON.parse(yakalanan!.icerik);
}

describe('kanıt paketi — yürütücü + defter', () => {
  it('demo veriden paket ÜRETİLMEZ (eskiden "court-admissible" paket çıkıyordu)', async () => {
    const r = await kos({ filename: 'sahte.csv' }); // yükleme yok → demo veri
    expect(r.status).toBe('error');
    expect(r.error).toMatch(/demo\/sentetik/);
    expect(yakalanan).toBeNull();
  });

  it("gerçek veride KAYITLI: tüm satırların hash'i, oturumdaki aktör, defter sırası", async () => {
    const r = await kos(gercekKaynak);
    expect(r.status, r.error).toBe('success');
    const d = r.data as any;
    expect(d.durum).toBe('KAYITLI');
    expect(d.aktor).toEqual({ id: 1, ad: 'Yerel analist' });   // Sınama: tek yerel kullanıcı
    expect(d.beyan_eden).toBe('PN-4242');
    expect(d.satir).toBe(3);
    const dosya = await indirilen();
    expect(await kanonikHash(dosya.paket.veri)).toBe(d.veri_sha256);
    expect(dosya.paket.veri.rows).toHaveLength(3);
    expect(dosya.makbuz.kayit.veri_sha256).toBe(d.veri_sha256);
    expect(dosya.makbuz).not.toHaveProperty('harp');
    // Python defterinin yazdığı satır = indirilen makbuz (bayt değil, içerik eşitliği).
    expect(defterMakbuzlari().find((m) => m.kayit.sira === dosya.makbuz.kayit.sira)).toEqual(dosya.makbuz);
    expect(dosya.harp_capasi).toEqual({ durum: 'yapilandirilmamis' });
    expect(d.harp_durumu).toBe('yapilandirilmamis');
    expect(dosya.paket).not.toHaveProperty('_complianceNote');
    expect(JSON.stringify(dosya)).not.toMatch(/simulated|court-admissible/i);
    expect((await (await gercekFetch(`${SUNUCU}/api/evidence/verify`)).json()).gecerli).toBe(true);
  });

  it('sunucuya ulaşılamazsa paket KAYITSIZ işaretlenir ve bunu söyler', async () => {
    durum.taban = ULASILAMAZ;
    const r = await kos(gercekKaynak);
    const d = r.data as any;
    expect(d.durum).toBe('KAYITSIZ');
    expect(d.uyarilar.join(' ')).toMatch(/ulaşılamadı.*KAYITSIZ/);
    await indirilen();
    expect(yakalanan!.ad).toMatch(/_KAYITSIZ\.json$/);
  });
});

describe('kanıt paketi — bağımsız Python doğrulayıcısı', () => {
  const yaz = (ad: string, nesne: unknown) => {
    const p = path.join(dizin, ad);
    fs.writeFileSync(p, typeof nesne === 'string' ? nesne : JSON.stringify(nesne, null, 2), 'utf8');
    return p;
  };
  const anahtar = () => path.join(KANIT, 'imza_anahtari.pub.pem');
  const defter = () => path.join(KANIT, 'defter.jsonl');

  it('JS sayı biçimi Python es_sayi ile bayt bayt aynı (RFC 8785)', async () => {
    const { tohumluUretec } = await import('../../src/engine/istatistik');
    const rng = tohumluUretec(8785);
    const sayilar = [0, -0, 1, -1, 0.1, 1e21, 1e20, 1e-6, 1e-7, 123e-20, 5e-324, 1.7976931348623157e308, 2 ** 53, 0.30000000000000004,
      ...Array.from({ length: 300 }, () => (rng() - 0.5) * 10 ** Math.floor(rng() * 60 - 30))];
    const p = yaz('sayilar.json', JSON.stringify(sayilar.map((x) => [x, JSON.stringify(x)])));
    const kod = `import json,sys; sys.path.insert(0, r"${path.dirname(DOGRULAYICI)}"); from kanit_dogrula import es_sayi
bad=[(s,es_sayi(x)) for x,s in json.load(open(r"${p}",encoding="utf-8")) if es_sayi(x)!=s]
print(len(bad), bad[:3])`;
    const r = spawnSync(PY, ['-c', kod], { encoding: 'utf8' });
    expect(r.stdout.trim(), r.stderr).toMatch(/^0 /);
  });

  it('KAYITLI paket + defter: GEÇERLİ (çıkış 0)', async () => {
    const r = await kos(gercekKaynak);
    expect(r.status).toBe('success');
    const p = yaz('kayitli.json', await indirilen());
    const s = dogrula(p, '--genel-anahtar', anahtar(), '--defter', defter());
    expect(s.kod, s.cikti).toBe(0);
    expect(s.cikti).toMatch(/Ed25519 imzası geçerli/);
    expect(s.cikti).toMatch(/makbuz defterde aynı sıra/);
  });

  it('tek hücre değiştirilirse BAŞARISIZ (çıkış 1)', async () => {
    await kos(gercekKaynak);
    const dosya = await indirilen();
    dosya.paket.veri.rows[1].zarar_tl = 2.0;
    const s = dogrula(yaz('kurcalanmis.json', dosya), '--genel-anahtar', anahtar());
    expect(s.kod, s.cikti).toBe(1);
    expect(s.cikti).toMatch(/✗ veri SHA-256/);
  });

  it('paket ve makbuz birlikte değiştirilse de imza yakalar (çıkış 1)', async () => {
    await kos(gercekKaynak);
    const dosya = await indirilen();
    dosya.makbuz.kayit.dosya_no = '2099/1';
    dosya.paket.dosya_no = '2099/1';
    const s = dogrula(yaz('ikisi.json', dosya), '--genel-anahtar', anahtar());
    expect(s.kod, s.cikti).toBe(1);
  });

  it('KAYITSIZ paket: EKSİK (çıkış 2), yanlış anahtar: BAŞARISIZ (çıkış 1)', async () => {
    durum.taban = ULASILAMAZ;
    await kos(gercekKaynak);
    const kayitsiz = yaz('kayitsiz.json', await indirilen());
    expect(dogrula(kayitsiz).kod).toBe(2);

    durum.taban = SUNUCU;
    await kos(gercekKaynak);
    const kayitli = yaz('kayitli2.json', await indirilen());
    const { generateKeyPairSync } = await import('node:crypto');
    const yabanci = yaz('yabanci.pub.pem', generateKeyPairSync('ed25519').publicKey.export({ type: 'spki', format: 'pem' }).toString());
    expect(dogrula(kayitli, '--genel-anahtar', yabanci).kod).toBe(1);
  });
});
