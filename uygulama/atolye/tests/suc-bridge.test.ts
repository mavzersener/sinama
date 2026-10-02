import { describe, it, expect, vi, afterEach } from 'vitest';
import {
  dongurBaslat, dongurVeri, dongurAnaliz, dongurAnalizeGec, muhakemeIzi, kanitDogrula,
  BackendError,
} from '../src/lib/sucBridge';

function mockFetch(status: number, body: unknown) {
  const fn = vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  });
  vi.stubGlobal('fetch', fn);
  return fn;
}

afterEach(() => vi.restoreAllMocks());

describe('sucBridge — başarı yolu', () => {
  it('dongurBaslat doğru araca POST atar ve planı döndürür', async () => {
    const fn = mockFetch(200, {
      sonuc: { oturum_id: 'abc', faz: 'PLAN', plan: { onerilen: ['grid_hotspot'], hedef_kitle: 'x', not: 'y', urun_turu: null }, sonraki: 'z' },
      meta: { arac: 'dongu_baslat' },
    });
    const r = await dongurBaslat('olay yoğunluğu nerede?');
    expect(fn).toHaveBeenCalledWith('/api/ml/suc/dongu_baslat', expect.objectContaining({ method: 'POST', credentials: 'include' }));
    expect(r.sonuc.oturum_id).toBe('abc');
    expect(r.sonuc.plan.onerilen).toContain('grid_hotspot');
  });

  it('dongurVeri satırları ve oturum_id gönderir, fitness döndürür', async () => {
    const fn = mockFetch(200, {
      sonuc: { faz: 'VERI', profil: { n: 2, kesildi: false, uyarilar: [], eksik_oran: {} }, uygunluk: { uygun: true, girdi_n: 2, sebepler: ['belirgin engel yok'] } },
      meta: { arac: 'dongu_veri' },
    });
    const r = await dongurVeri('abc', [{ a: 1 }, { a: 2 }], 'grid_hotspot');
    const body = JSON.parse(fn.mock.calls[0][1].body);
    expect(body.oturum_id).toBe('abc');
    expect(body.satirlar.length).toBe(2);
    expect(body.analiz).toBe('grid_hotspot');
    expect(r.sonuc.uygunluk.uygun).toBe(true);
  });

  it('dongurAnaliz gerekçeyi OBJECT olarak gönderir (string değil)', async () => {
    const fn = mockFetch(200, { sonuc: {}, meta: { arac: 'dongu_analiz' } });
    await dongurAnaliz('abc', 'grid_hotspot', { hipotez: 'h', yorum: 'y' }, { satirlar: [] });
    const body = JSON.parse(fn.mock.calls[0][1].body);
    expect(typeof body.gerekce).toBe('object');
    expect(body.gerekce.hipotez).toBe('h');
  });

  it('dongurAnalizeGec uygunluğu OBJECT olarak gönderir (backend .get bekler, string değil)', async () => {
    const fn = mockFetch(200, { sonuc: { faz: 'ANALIZ' }, meta: { arac: 'dongu_analize_gec' } });
    await dongurAnalizeGec('abc', { uygun: true, girdi_n: 60, sebepler: ['belirgin engel yok'] });
    const body = JSON.parse(fn.mock.calls[0][1].body);
    expect(typeof body.uygunluk).toBe('object');
    expect(body.uygunluk.uygun).toBe(true);
    expect(body.uygunluk).not.toBe('uygun');
  });

  it('kanitDogrula zincir rozetini döndürür', async () => {
    mockFetch(200, { sonuc: { saglam: true, olay_sayisi: 2, bozuk_adim: null, zincir_bas_hash: 'ff' }, meta: { arac: 'kanit_dogrula' } });
    const r = await kanitDogrula('abc');
    expect(r.sonuc.saglam).toBe(true);
  });

  it('muhakemeIzi markdown ürünü döndürür', async () => {
    mockFetch(200, { sonuc: { urun: '## Muhakeme İzi' }, meta: { arac: 'muhakeme_izi' } });
    const r = await muhakemeIzi('abc');
    expect(r.sonuc.urun).toContain('Muhakeme');
  });
});

describe('sucBridge — hata taksonomisi (FR3 §D)', () => {
  it('422 + gövde tip=kapi → BackendError(kapi)', async () => {
    mockFetch(422, { tip: 'kapi', mesaj: 'fitness gate: n<30' });
    await expect(dongurAnaliz('x', 'anova', { hipotez: '', yorum: '' }, {})).rejects.toMatchObject({
      tip: 'kapi',
      message: expect.stringContaining('fitness'),
    });
  });

  it('400 + tip=veri + öneri → BackendError öneriyi taşır', async () => {
    mockFetch(400, { tip: 'veri', mesaj: 'eksik alan', oneri: 'veri_ozeti çalıştır' });
    try {
      await dongurVeri('x', []);
      expect.unreachable('hata bekleniyordu');
    } catch (e) {
      expect(e).toBeInstanceOf(BackendError);
      expect((e as BackendError).tip).toBe('veri');
      expect((e as BackendError).oneri).toBe('veri_ozeti çalıştır');
    }
  });

  it('401 → kimlik tipli oturum hatası (guvenlik=dosya sınırı ile karışmaz)', async () => {
    mockFetch(401, {});
    await expect(muhakemeIzi('x')).rejects.toMatchObject({ tip: 'kimlik' });
  });

  it('gövde tip yoksa HTTP durumundan türetilir (500→sistem)', async () => {
    mockFetch(500, {});
    await expect(kanitDogrula('x')).rejects.toMatchObject({ tip: 'sistem' });
  });

  it('fetch reddi → sistem hatası (servis kapalı)', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('ECONNREFUSED')));
    await expect(dongurBaslat('x')).rejects.toMatchObject({ tip: 'sistem' });
  });
});
