import { describe, it, expect } from 'vitest';
import {
  kartGecerli,
  gecerliKartlar,
  ASGARI_IFADE,
  type KanitKartiTaslak,
} from './kanitKarti';

/**
 * Geçerli bir taslak oluşturan fabrika — ek alanlar varsayılan değerleri geçersiz kıl.
 */
function taslakYap(ek: Partial<KanitKartiTaslak> = {}): KanitKartiTaslak {
  return {
    claim_id: 'iddia_1',
    source_id: 'kaynak_1',
    statement: 'Bu bir test iddiasıdır ve yeterli uzunluktadır.',
    locator: 'sayfa 5',
    researcher_verified: true,
    ...ek,
  };
}

describe('kanitKarti — kartGecerli()', () => {
  it('tam dolu ve doğrulanmış kart geçerli döner', () => {
    const kart = taslakYap();
    expect(kartGecerli(kart)).toBe(true);
  });

  it('doğrulanmamış kart geçersiz döner (diğer alanlar dolu olsa bile)', () => {
    const kart = taslakYap({ researcher_verified: false });
    expect(kartGecerli(kart)).toBe(false);
  });

  it('boş claim_id geçersiz döner', () => {
    const kart = taslakYap({ claim_id: '' });
    expect(kartGecerli(kart)).toBe(false);
  });

  it('sadece boşluk içeren claim_id geçersiz döner', () => {
    const kart = taslakYap({ claim_id: '   ' });
    expect(kartGecerli(kart)).toBe(false);
  });

  it('boş source_id geçersiz döner', () => {
    const kart = taslakYap({ source_id: '' });
    expect(kartGecerli(kart)).toBe(false);
  });

  it('statement ASGARI_IFADE uzunluğundan kısa ise geçersiz', () => {
    const kart = taslakYap({ statement: 'kısa' }); // 4 karakter, ASGARI_IFADE=10
    expect(kartGecerli(kart)).toBe(false);
  });

  it('statement tam ASGARI_IFADE uzunluğunda (sınır) geçerli döner', () => {
    const stmt = 'a'.repeat(ASGARI_IFADE); // Tam 10 karakter
    const kart = taslakYap({ statement: stmt });
    expect(kartGecerli(kart)).toBe(true);
  });

  it('boş locator geçersiz döner', () => {
    const kart = taslakYap({ locator: '' });
    expect(kartGecerli(kart)).toBe(false);
  });

  it('sadece boşluk içeren locator geçersiz döner', () => {
    const kart = taslakYap({ locator: '  ' });
    expect(kartGecerli(kart)).toBe(false);
  });

  it('yalnız boşluklardan oluşan statement geçersiz döner', () => {
    const kart = taslakYap({ statement: '               ' }); // 15 boşluk
    expect(kartGecerli(kart)).toBe(false);
  });
});

describe('kanitKarti — gecerliKartlar()', () => {
  it('karışık listeden yalnız geçerli kartlar döner', () => {
    const gecerli = taslakYap({ claim_id: 'valid_1' });
    const dogrulanmamis = taslakYap({
      claim_id: 'unverified_1',
      researcher_verified: false,
    });
    const eksikLocator = taslakYap({
      claim_id: 'missing_locator',
      locator: '',
    });

    const sonuc = gecerliKartlar([gecerli, dogrulanmamis, eksikLocator]);
    expect(sonuc).toHaveLength(1);
    expect(sonuc[0].claim_id).toBe('valid_1');
  });

  it('dönen kartların researcher_verified alanı her zaman true', () => {
    const taslaklar = [
      taslakYap({ claim_id: 'c1' }),
      taslakYap({ claim_id: 'c2' }),
    ];
    const sonuc = gecerliKartlar(taslaklar);
    sonuc.forEach((kart) => {
      expect(kart.researcher_verified).toBe(true);
    });
  });

  it('alanlar kırpılır: başında/sonunda boşluk olan değerler trim edilir', () => {
    const gecerli = taslakYap({
      claim_id: '  iddia_trim  ',
      statement: '  Bu test iddiasıdır ve yeterli uzunluktadır.  ',
      locator: '  sayfa 10  ',
    });
    const sonuc = gecerliKartlar([gecerli]);
    expect(sonuc).toHaveLength(1);
    expect(sonuc[0].claim_id).toBe('iddia_trim');
    expect(sonuc[0].statement).toBe(
      'Bu test iddiasıdır ve yeterli uzunluktadır.'
    );
    expect(sonuc[0].locator).toBe('sayfa 10');
  });

  it('tüm taslaklar geçersizse boş dizi döner', () => {
    const taslaklar = [
      taslakYap({ researcher_verified: false }),
      taslakYap({ source_id: '' }),
      taslakYap({ locator: '' }),
    ];
    const sonuc = gecerliKartlar(taslaklar);
    expect(sonuc).toHaveLength(0);
  });

  it('girdi listesi boşsa boş dizi döner', () => {
    const sonuc = gecerliKartlar([]);
    expect(sonuc).toHaveLength(0);
  });
});
