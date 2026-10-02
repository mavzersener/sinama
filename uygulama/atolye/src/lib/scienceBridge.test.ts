import { describe, it, expect, vi, afterEach, beforeEach } from 'vitest';
import {
  saglik,
  BilimHatasi,
  protokolKilitle,
  veriYukle,
  makaleUret,
} from './scienceBridge';

/**
 * Fetch'i taklit eden helper — başarılı veya başarısız yanıtlar üretir.
 * ok: status >= 200 && status < 300
 */
function mockFetch(status: number, body: unknown) {
  const fn = vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  });
  vi.stubGlobal('fetch', fn);
  return fn;
}

beforeEach(() => {
  vi.clearAllMocks();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe('scienceBridge — saglik()', () => {
  it('sağlık çağrısı doğru yola ve credentials ile gider', async () => {
    const fn = mockFetch(200, { status: 'ok', phase: 'P7' });
    await saglik();
    expect(fn).toHaveBeenCalledWith(
      '/api/science/health',
      expect.objectContaining({
        method: 'GET',
        credentials: 'include',
      })
    );
  });

  it('başarılı yanıt Saglik tipini döndürür', async () => {
    mockFetch(200, { status: 'running', phase: 'P3' });
    const r = await saglik();
    expect(r.status).toBe('running');
    expect(r.phase).toBe('P3');
  });
});

describe('scienceBridge — hata taksonomisi (BilimHatasi tipleri)', () => {
  it('401 → BilimHatasi tip guvenlik, yenidenDenenebilir false', async () => {
    mockFetch(401, {});
    try {
      await saglik();
      expect.unreachable('401 hatası bekleniyordu');
    } catch (e) {
      expect(e).toBeInstanceOf(BilimHatasi);
      expect((e as BilimHatasi).tip).toBe('guvenlik');
      expect((e as BilimHatasi).yenidenDenenebilir).toBe(false);
    }
  });

  it('404 → BilimHatasi tip bulunamadi, yenidenDenenebilir false', async () => {
    mockFetch(404, {});
    try {
      await saglik();
      expect.unreachable('404 hatası bekleniyordu');
    } catch (e) {
      expect(e).toBeInstanceOf(BilimHatasi);
      expect((e as BilimHatasi).tip).toBe('bulunamadi');
      expect((e as BilimHatasi).yenidenDenenebilir).toBe(false);
    }
  });

  it('409 → BilimHatasi tip cakisma, yenidenDenenebilir false', async () => {
    mockFetch(409, {});
    try {
      await saglik();
      expect.unreachable('409 hatası bekleniyordu');
    } catch (e) {
      expect(e).toBeInstanceOf(BilimHatasi);
      expect((e as BilimHatasi).tip).toBe('cakisma');
      expect((e as BilimHatasi).yenidenDenenebilir).toBe(false);
    }
  });

  it('413 → BilimHatasi tip cok_buyuk, yenidenDenenebilir false', async () => {
    mockFetch(413, {});
    try {
      await saglik();
      expect.unreachable('413 hatası bekleniyordu');
    } catch (e) {
      expect(e).toBeInstanceOf(BilimHatasi);
      expect((e as BilimHatasi).tip).toBe('cok_buyuk');
      expect((e as BilimHatasi).yenidenDenenebilir).toBe(false);
    }
  });

  it('422 → BilimHatasi tip sema, yenidenDenenebilir false (KRİTİK: şema hatası tekrar denemekle düzelmez)', async () => {
    mockFetch(422, { detail: 'şema geçersiz' });
    try {
      await saglik();
      expect.unreachable('422 hatası bekleniyordu');
    } catch (e) {
      expect(e).toBeInstanceOf(BilimHatasi);
      expect((e as BilimHatasi).tip).toBe('sema');
      expect((e as BilimHatasi).yenidenDenenebilir).toBe(false);
    }
  });

  it('503 → BilimHatasi tip erisilemez, yenidenDenenebilir TRUE', async () => {
    mockFetch(503, {});
    try {
      await saglik();
      expect.unreachable('503 hatası bekleniyordu');
    } catch (e) {
      expect(e).toBeInstanceOf(BilimHatasi);
      expect((e as BilimHatasi).tip).toBe('erisilemez');
      expect((e as BilimHatasi).yenidenDenenebilir).toBe(true);
    }
  });

  it('502 → BilimHatasi tip erisilemez, yenidenDenenebilir TRUE', async () => {
    mockFetch(502, {});
    try {
      await saglik();
      expect.unreachable('502 hatası bekleniyordu');
    } catch (e) {
      expect(e).toBeInstanceOf(BilimHatasi);
      expect((e as BilimHatasi).tip).toBe('erisilemez');
      expect((e as BilimHatasi).yenidenDenenebilir).toBe(true);
    }
  });

  it('bilinmeyen durum (500) → BilimHatasi tip sistem, yenidenDenenebilir false', async () => {
    mockFetch(500, {});
    try {
      await saglik();
      expect.unreachable('500 hatası bekleniyordu');
    } catch (e) {
      expect(e).toBeInstanceOf(BilimHatasi);
      expect((e as BilimHatasi).tip).toBe('sistem');
      expect((e as BilimHatasi).yenidenDenenebilir).toBe(false);
    }
  });

  it('hata mesajı motordaki detail alanından okunur', async () => {
    mockFetch(422, { detail: 'şema geçersiz — alan: email' });
    try {
      await saglik();
      expect.unreachable('422 hatası bekleniyordu');
    } catch (e) {
      expect((e as BilimHatasi).message).toBe('şema geçersiz — alan: email');
    }
  });

  it('ağ koptuğunda (fetch reject) → tip erisilemez, durum 0', async () => {
    vi.stubGlobal('fetch', vi.fn().mockRejectedValue(new Error('ECONNREFUSED')));
    try {
      await saglik();
      expect.unreachable('fetch hatası bekleniyordu');
    } catch (e) {
      expect(e).toBeInstanceOf(BilimHatasi);
      expect((e as BilimHatasi).tip).toBe('erisilemez');
      expect((e as BilimHatasi).durum).toBe(0);
    }
  });
});

describe('scienceBridge — protokolKilitle() çapraz zincir alanları', () => {
  it('protokolKilitle tüm çapraz zincir alanlarını gövdeye koyar', async () => {
    const fn = mockFetch(200, { research_id: 'res_x', version: 1, locked: true });
    await protokolKilitle('res_x', 'Sener', {
      okcOturumId: 'abc',
      yerliKilitHash: 'f'.repeat(64),
    });
    const body = JSON.parse(fn.mock.calls[0][1].body);
    expect(body.approved_by).toBe('Sener');
    expect(body.okc_oturum_id).toBe('abc');
    expect(body.yerli_kilit_hash).toBe('f'.repeat(64));
  });

  it('ek verilmediğinde çapraz zincir alanları gövdede BULUNMAMALI', async () => {
    const fn = mockFetch(200, { research_id: 'res_x', version: 1, locked: true });
    await protokolKilitle('res_x', 'Sener');
    const body = JSON.parse(fn.mock.calls[0][1].body);
    expect(body.approved_by).toBe('Sener');
    expect('okc_oturum_id' in body).toBe(false);
    expect('yerli_kilit_hash' in body).toBe(false);
  });

  it('yalnızca okcOturumId verilirse sadece o alan gövdeye eklenir', async () => {
    const fn = mockFetch(200, { research_id: 'res_x', version: 1, locked: true });
    await protokolKilitle('res_x', 'Sener', { okcOturumId: 'xyz' });
    const body = JSON.parse(fn.mock.calls[0][1].body);
    expect(body.okc_oturum_id).toBe('xyz');
    expect('yerli_kilit_hash' in body).toBe(false);
  });
});

describe('scienceBridge — veriYukle() FormData', () => {
  it('veriYukle FormData gönderir ve content-type başlığı ELLE ayarlanmaz', async () => {
    const fn = mockFetch(200, { dataset_id: 'dat_1', raw_sha256: 'abc123' });
    const file = new File(['data'], 'test.csv', { type: 'text/csv' });
    await veriYukle('res_1', file);

    // fetch'e geçilen options kontrol et
    const options = fn.mock.calls[0][1];
    expect(options.body).toBeInstanceOf(FormData);
    // content-type başlığı ELLE ayarlanmamış olmalı — tarayıcı sınırlayıcıyı üretir
    const headers = options.headers as Record<string, string> | undefined;
    expect(headers?.['content-type']).toBeUndefined();
  });
});

describe('scienceBridge — makaleUret() iç içe yolu', () => {
  it('makaleUret doğru iç içe yola gider', async () => {
    const fn = mockFetch(200, {
      manuscript_id: 'msk_1',
      manuscript_filename: 'paper.pdf',
      artifacts: {},
    });
    await makaleUret('res_a', 'dat_b', 'ana_c', 'val_d', {
      evidence_claims: [],
    });

    const path = fn.mock.calls[0][0];
    expect(path).toContain('/api/science/api/research/res_a/datasets/dat_b/analysis/runs/ana_c/validations/val_d/manuscripts');
  });

  it('makaleUret POST yöntemi kullanır ve evidence_claims gönderir', async () => {
    const fn = mockFetch(200, {
      manuscript_id: 'msk_2',
      manuscript_filename: 'paper.pdf',
      artifacts: {},
    });
    const claims = [
      {
        claim_id: 'c1',
        source_id: 's1',
        statement: 'test iddiası',
        locator: 'page 5',
        researcher_verified: true as const,
      },
    ];
    await makaleUret('res_a', 'dat_b', 'ana_c', 'val_d', {
      evidence_claims: claims,
    });

    const options = fn.mock.calls[0][1];
    expect(options.method).toBe('POST');
    const body = JSON.parse(options.body);
    expect(body.evidence_claims).toEqual(claims);
  });
});
