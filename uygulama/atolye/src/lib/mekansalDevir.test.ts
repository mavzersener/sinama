import { describe, it, expect, vi } from 'vitest';
import {
  mekansalDevret,
  devirUyarisi,
  type DevirBagimliliklari,
  type DevirPaketi,
  type DevirSonucu,
} from './mekansalDevir';

/**
 * Başarılı bir varsayılan bağımlılık seti oluşturan fabrika.
 * Ek alanlarla override edilebilir.
 */
function bagimlilikYap<T = Record<string, unknown>>(
  ek: Partial<DevirBagimliliklari<T>> = {},
): DevirBagimliliklari<T> {
  let oturumSayac = 0;

  return {
    baslat: vi.fn(async () => {
      oturumSayac++;
      return { oturumId: `oturum_${oturumSayac}` };
    }),
    veriBagla: vi.fn(async () => ({
      uygun: true,
      girdi_n: 150,
      sebepler: [],
    })),
    analizeGec: vi.fn(async () => {}),
    calistir: vi.fn(async () => ({})),
    devret: vi.fn(async (paket) => ({
      external_id: `ext_${paket.okc_oturum_id}`,
    } as T)),
    ilerleme: vi.fn(),
    ...ek,
  };
}

describe('mekansalDevir — mekansalDevret()', () => {
  it('her yöntem TAZE oturumda koşar — baslat her seferinde farklı id üretir', async () => {
    const bagimlilik = bagimlilikYap();
    const araclar = ['X', 'Y', 'Z'];

    await mekansalDevret(araclar, 'hipotez_1', bagimlilik);

    // baslat üç kez çağrılmalı
    expect(bagimlilik.baslat).toHaveBeenCalledTimes(3);

    // devret çağrılarındaki okc_oturum_id değerleri birbirinden farklı olmalı
    const devretCagrilari = vi.mocked(bagimlilik.devret).mock.calls;
    const oturumIdleri = devretCagrilari.map((call) => call[0].okc_oturum_id);
    const uniqueIdler = new Set(oturumIdleri);
    expect(uniqueIdler.size).toBe(3);
  });

  it('sıra doğru — baslat → veriBagla → analizeGec → calistir → devret', async () => {
    const cagriSirasi: string[] = [];

    const bagimlilik = bagimlilikYap({
      baslat: vi.fn(async () => {
        cagriSirasi.push('baslat');
        return { oturumId: 'oturum_1' };
      }),
      veriBagla: vi.fn(async () => {
        cagriSirasi.push('veriBagla');
        return { uygun: true, girdi_n: 150, sebepler: [] };
      }),
      analizeGec: vi.fn(async () => {
        cagriSirasi.push('analizeGec');
      }),
      calistir: vi.fn(async () => {
        cagriSirasi.push('calistir');
        return {};
      }),
      devret: vi.fn(async () => {
        cagriSirasi.push('devret');
        return { external_id: 'ext_1' };
      }),
    });

    await mekansalDevret(['X'], 'hipotez_1', bagimlilik);

    expect(cagriSirasi).toEqual([
      'baslat',
      'veriBagla',
      'analizeGec',
      'calistir',
      'devret',
    ]);
  });

  it('kapı reddederse yöntem ATLANIR — analizeGec, calistir, devret çağrılmaz', async () => {
    const bagimlilik = bagimlilikYap({
      veriBagla: vi.fn(async () => ({
        uygun: false,
        girdi_n: 5,
        sebepler: ['ornek yetersiz'],
      })),
    });

    const sonuc = await mekansalDevret(['X'], 'hipotez_1', bagimlilik);

    // Sonuç doğrulaması
    expect(sonuc.kabulEdilen).toHaveLength(0);
    expect(sonuc.atlanan).toHaveLength(1);
    expect(sonuc.atlanan[0].arac).toBe('X');
    expect(sonuc.atlanan[0].sebep).toContain('ornek yetersiz');

    // analizeGec, calistir, devret HİÇ çağrılmamalı
    expect(bagimlilik.analizeGec).not.toHaveBeenCalled();
    expect(bagimlilik.calistir).not.toHaveBeenCalled();
    expect(bagimlilik.devret).not.toHaveBeenCalled();
  });

  it('veriBagla null döndürse de ATLANIR — sebep "veri uygun değil" olur', async () => {
    const bagimlilik = bagimlilikYap({
      veriBagla: vi.fn(async () => null),
    });

    const sonuc = await mekansalDevret(['X'], 'hipotez_1', bagimlilik);

    expect(sonuc.atlanan).toHaveLength(1);
    expect(sonuc.atlanan[0].arac).toBe('X');
    expect(sonuc.atlanan[0].sebep).toBe('veri uygun değil');
    expect(sonuc.kabulEdilen).toHaveLength(0);
  });

  it('kapı kararı devredilen pakete konur — uygun, girdi_n, sebepler aynen taşınır', async () => {
    const bagimlilik = bagimlilikYap({
      veriBagla: vi.fn(async () => ({
        uygun: true,
        girdi_n: 150,
        sebepler: ['uyari x'],
      })),
      devret: vi.fn(async (paket: DevirPaketi) => paket as unknown as Record<string, unknown>),
    });

    const sonuc = await mekansalDevret(['X'], 'hipotez_1', bagimlilik);

    expect(sonuc.kabulEdilen).toHaveLength(1);
    const paket = sonuc.kabulEdilen[0];
    expect((paket as unknown as DevirPaketi).gate_karari).toEqual({
      uygun: true,
      girdi_n: 150,
      sebepler: ['uyari x'],
    });
  });

  it('sebepler undefined ise boş dizi olarak taşınır — gate_karari.sebepler = []', async () => {
    const bagimlilik = bagimlilikYap({
      veriBagla: vi.fn(async () => ({
        uygun: true,
        girdi_n: 150,
        // sebepler alanı yok
      })),
      devret: vi.fn(async (paket: DevirPaketi) => paket as unknown as Record<string, unknown>),
    });

    const sonuc = await mekansalDevret(['X'], 'hipotez_1', bagimlilik);

    expect(sonuc.kabulEdilen).toHaveLength(1);
    const paket = sonuc.kabulEdilen[0];
    expect((paket as unknown as DevirPaketi).gate_karari.sebepler).toEqual([]);
  });

  it('bir yöntemin hatası diğerlerini düşürmez — başarılılar korunur, hatalar toplanır', async () => {
    const bagimlilik = bagimlilikYap({
      calistir: vi.fn(async (oturumId: string) => {
        // İkinci oturum hatası versin
        if (oturumId === 'oturum_2') {
          throw new Error('hesaplama başarısız');
        }
        return { sonuc: 'ok' };
      }),
      devret: vi.fn(async (paket: DevirPaketi) => paket as unknown as Record<string, unknown>),
    });

    const sonuc = await mekansalDevret(
      ['X', 'Y', 'Z'],
      'hipotez_1',
      bagimlilik,
    );

    expect(sonuc.kabulEdilen).toHaveLength(2);
    expect(sonuc.hatali).toHaveLength(1);
    expect(sonuc.hatali[0].arac).toBe('Y');
    expect(sonuc.hatali[0].mesaj).toContain('hesaplama başarısız');
  });

  it('devret sonucu aynen taşınır — motor kaydı tamamıyla kabulEdilen dizisine girer', async () => {
    const mockKayit = {
      external_id: 'ext_1',
      yontem_adi: 'X',
      skor: 99,
    };

    const bagimlilik = bagimlilikYap({
      devret: vi.fn(async () => mockKayit),
    });

    const sonuc = await mekansalDevret(['X'], 'hipotez_1', bagimlilik);

    expect(sonuc.kabulEdilen).toHaveLength(1);
    expect(sonuc.kabulEdilen[0]).toEqual(mockKayit);
  });

  it('boş araç listesi — hiçbir çağrı yapılmaz, tüm çıktılar boş', async () => {
    const bagimlilik = bagimlilikYap();

    const sonuc = await mekansalDevret([], 'hipotez_1', bagimlilik);

    expect(sonuc.kabulEdilen).toHaveLength(0);
    expect(sonuc.atlanan).toHaveLength(0);
    expect(sonuc.hatali).toHaveLength(0);
    expect(bagimlilik.baslat).not.toHaveBeenCalled();
  });

  it('ilerleme geri çağrısı çağrılır — en az iki kez (çalışıyor + devrediliyor)', async () => {
    const bagimlilik = bagimlilikYap();

    await mekansalDevret(['X'], 'hipotez_1', bagimlilik);

    expect(bagimlilik.ilerleme).toHaveBeenCalledTimes(2);
    expect(vi.mocked(bagimlilik.ilerleme!).mock.calls[0][0]).toContain('çalışıyor');
    expect(vi.mocked(bagimlilik.ilerleme!).mock.calls[1][0]).toContain(
      'devrediliyor',
    );
  });
});

describe('mekansalDevir — devirUyarisi()', () => {
  it('her şey temizse null döner (atlanan ve hatali boş)', () => {
    const sonuc: DevirSonucu<unknown> = {
      kabulEdilen: [],
      atlanan: [],
      hatali: [],
    };

    expect(devirUyarisi(sonuc)).toBeNull();
  });

  it('atlanan varsa mesaj "Kapı" kelimesini ve araç adını içerir', () => {
    const sonuc: DevirSonucu<unknown> = {
      kabulEdilen: [],
      atlanan: [{ arac: 'Yontem1', sebep: 'sebepler: ornek yetersiz' }],
      hatali: [],
    };

    const mesaj = devirUyarisi(sonuc);
    expect(mesaj).toContain('Kapı');
    expect(mesaj).toContain('Yontem1');
  });

  it('hatali varsa mesaj "Hata" kelimesini ve araç adını içerir', () => {
    const sonuc: DevirSonucu<unknown> = {
      kabulEdilen: [],
      atlanan: [],
      hatali: [{ arac: 'Yontem2', mesaj: 'bağlantı hatası' }],
    };

    const mesaj = devirUyarisi(sonuc);
    expect(mesaj).toContain('Hata');
    expect(mesaj).toContain('Yontem2');
  });

  it('hem atlanan hem hatali varsa ikisi de mesajda geçer', () => {
    const sonuc: DevirSonucu<unknown> = {
      kabulEdilen: [],
      atlanan: [{ arac: 'Yontem1', sebep: 'yetersiz' }],
      hatali: [{ arac: 'Yontem2', mesaj: 'çöktü' }],
    };

    const mesaj = devirUyarisi(sonuc);
    expect(mesaj).toContain('Kapı');
    expect(mesaj).toContain('Yontem1');
    expect(mesaj).toContain('Hata');
    expect(mesaj).toContain('Yontem2');
  });
});
