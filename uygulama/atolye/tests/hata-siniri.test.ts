import { describe, it, expect, vi, beforeEach } from 'vitest';
import { renderToStaticMarkup } from 'react-dom/server';
import { HataSiniri } from '../src/components/HataSiniri';
import { useStore } from '../src/store/useStore';

/**
 * Hata sınırı mantığı. Test ortamı node (jsdom yok): React'in sınır
 * sözleşmesi (getDerivedStateFromError → render → componentDidUpdate)
 * doğrudan çağrılır; yedek kart renderToStaticMarkup ile okunur.
 * Gerçek yakalama davranışı tarayıcıda doğrulandı (DURUM §7e).
 */

const yeni = (ozellik: Partial<ConstructorParameters<typeof HataSiniri>[0]> = {}) =>
  new HataSiniri({ bolge: 'Sonuç paneli', children: 'içerik', ...ozellik });

beforeEach(() => useStore.getState().clearLogs());

describe('HataSiniri', () => {
  it('hata yokken çocukları AYNEN döner (sarmalayıcı eleman eklemez — düzen bozulmaz)', () => {
    expect(yeni().render()).toBe('içerik');
  });

  it('getDerivedStateFromError: Error olmayan fırlatılanı da Error\'a çevirir', () => {
    const e = new Error('patladı');
    expect(HataSiniri.getDerivedStateFromError(e)).toEqual({ hata: e });
    const s = HataSiniri.getDerivedStateFromError('düz metin');
    expect(s.hata).toBeInstanceOf(Error);
    expect(s.hata?.message).toBe('düz metin');
  });

  it('yedek kart: bölge adı, ileti, "Yeniden dene"; kapat verilince "Kapat" da çıkar', () => {
    const s = yeni();
    s.state = { hata: new Error('beklenmedik sonuç biçimi') };
    const html = renderToStaticMarkup(s.render() as never);
    expect(html).toContain('role="alert"');
    expect(html).toContain('Sonuç paneli bir hata nedeniyle gösterilemiyor.');
    expect(html).toContain('beklenmedik sonuç biçimi');
    expect(html).toContain('Yeniden dene');
    expect(html).not.toContain('Kapat');

    const k = yeni({ bolge: 'Rehberli Mod', kapat: () => {}, kaplama: true });
    k.state = { hata: new Error('x') };
    const html2 = renderToStaticMarkup(k.render() as never);
    expect(html2).toContain('Kapat');
    expect(html2).toContain('fixed'); // kaplama kartı ekranın üstünde
  });

  it('çok uzun ileti 300 karakterde kesilir', () => {
    const s = yeni();
    s.state = { hata: new Error('a'.repeat(5000)) };
    const html = renderToStaticMarkup(s.render() as never);
    expect(html).toContain('a'.repeat(300));
    expect(html).not.toContain('a'.repeat(301));
  });

  it('componentDidCatch hatayı Günlük sekmesine yazar', () => {
    const konsol = vi.spyOn(console, 'error').mockImplementation(() => {});
    yeni({ bolge: 'Özellik paneli' }).componentDidCatch(new Error('config yok'), { componentStack: '' } as never);
    expect(useStore.getState().logs.some((l) => l.includes('Arayüz hatası (Özellik paneli): config yok'))).toBe(true);
    konsol.mockRestore();
  });

  it('sifirlaAnahtari değişince sıfırlanır; aynı kalırsa ya da hata yoksa dokunmaz', () => {
    const s = yeni({ sifirlaAnahtari: 'dugum-1' });
    const setState = vi.fn();
    s.setState = setState as never;

    s.state = { hata: null };
    s.componentDidUpdate({ ...s.props, sifirlaAnahtari: 'dugum-0' });
    expect(setState).not.toHaveBeenCalled();

    s.state = { hata: new Error('x') };
    s.componentDidUpdate({ ...s.props }); // anahtar aynı
    expect(setState).not.toHaveBeenCalled();

    s.componentDidUpdate({ ...s.props, sifirlaAnahtari: 'dugum-0' });
    expect(setState).toHaveBeenCalledWith({ hata: null });
  });

  it('Kapat: önce kaplamayı kapatır, sonra sınırı sıfırlar', () => {
    const sira: string[] = [];
    const s = yeni({ kapat: () => sira.push('kapat') });
    s.setState = (() => sira.push('sifirla')) as never;
    s.kapatVeSifirla();
    expect(sira).toEqual(['kapat', 'sifirla']);
  });
});
