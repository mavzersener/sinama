# -*- coding: utf-8 -*-
"""
sinamalar.py — Öngörü ve rakiplerin deterministik değerlendirmesi (ADR-002 §5).

Her soru türü için birincil öngörüyü ve uygulanabilir rakipleri, resmi araç
yolundan (yurut: şema + kapı + hesap + iz) koşulan sınamalarla değerlendirir.
Dil modeli yoktur. Durumlar:
- birincil: tutuldu | karşıt | belirsiz | sınanamadı
- rakip: dışlandı | destekleniyor | çözülmedi | uygulanamaz

yurut(ad, arg, hipotez, amac_metni) → araç sonucu; kapı reddi ya da kullanım
hatası fırlatır (birincilde 'sınanamadı' olur).
"""
from collections import Counter

from ..cekirdek import veri
from ..cekirdek.hatalar import SucAnaliziHatasi
from . import rak

ALFA = 0.05
SUREKLI_PAY = 1 / 16      # kanalın çeyrek başına beklenen payının dörtte biri
VERI_ESIK = 0.05          # geçersiz tarih/koordinat oranı üst sınırı
YIGILMA_ESIK = 0.05       # tek koordinattaki kayıt payı üst sınırı
MO_BOS_ESIK = 0.20


def _rakip(kod, durum, gerekce):
    k = rak.KATALOG[kod]
    return {"kod": kod, "durum": durum, "etki": k["etki"], "gerekce": gerekce,
            "sonraki_kanit": k["sonraki_kanit"]}


def _dene(yurut, ad, arg, hipotez, amac):
    """Aracı koşar; kapı reddi/kullanım/veri hatasını (sonuç, hata) olarak döner."""
    try:
        return yurut(ad, arg, hipotez, amac), None
    except SucAnaliziHatasi as e:
        return None, f"{type(e).__name__}: {e}"


# ---------------------------------------------------------------- ARTIŞ

def _tarihli(kayitlar, kanal_alan=None):
    """(datetime, kanal) çiftleri; geçersiz tarihli kayıtlar atlanır."""
    cikti = []
    for r in kayitlar:
        dt = veri.tarih_coz(r.get("tarih"))
        if dt is not None:
            cikti.append((dt, r.get(kanal_alan) if kanal_alan else None))
    return cikti


def _surekli_kanallar(tarihli):
    """Dönemin ilk VE son çeyreğinde yeterince kaydı olan kanallar."""
    t0 = min(dt for dt, _ in tarihli)
    t1 = max(dt for dt, _ in tarihli)
    ceyrek = (t1 - t0) / 4
    toplam, ilk, son = Counter(), Counter(), Counter()
    for dt, k in tarihli:
        toplam[k] += 1
        ilk[k] += dt <= t0 + ceyrek
        son[k] += dt >= t1 - ceyrek
    return sorted(k for k, n in toplam.items()
                  if ilk[k] >= max(3, n * SUREKLI_PAY) and son[k] >= max(3, n * SUREKLI_PAY))


def _aylik_sayim(tarihli):
    """İlk aydan son aya takvim ayları ve her ayın kayıt sayısı."""
    say = Counter((dt.year, dt.month) for dt, _ in tarihli)
    y, m = min(say)
    son = max(say)
    aylar = []
    while (y, m) <= son:
        aylar.append(say.get((y, m), 0))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return aylar


def artis(kaynak, kayitlar, yurut, kanal_alan=None):
    """ARTIŞ: trend (birincil), R-RASTLANTI, R-BILDIRIM, R-MEVSIM, R-VERI."""
    tarihli = _tarihli(kayitlar, kanal_alan)
    n = len(kayitlar)
    saglamlik = []
    tr, hata = _dene(yurut, "trend", dict(kaynak), "H1", "birincil öngörü: eğim anlamlı pozitif")
    if hata or tr is None:
        birincil = {"durum": "sınanamadı", "gerekce": hata or "trend sonucu yok"}
    else:
        yorum = tr.get("yorum")
        durum = {"artan": "tutuldu", "azalan": "karşıt", "anlamlı trend yok": "belirsiz",
                 "yatay": "belirsiz"}.get(yorum, "sınanamadı")
        birincil = {"durum": durum,
                    "gerekce": f"trend: {yorum} (eğim {tr.get('egim')}, p {tr.get('p')})"}
    tuttu = birincil["durum"] == "tutuldu"
    rakipler = [_rakip("R-RASTLANTI", "dışlandı" if tuttu else "çözülmedi",
                       "eğim t-testi p < 0,05" if tuttu else "anlamlı eğim yok; rastlantı dışlanamaz")]

    # R-BILDIRIM — artış dönem boyunca var olan kanallarda da var mı
    if not tuttu:
        rakipler.append(_rakip("R-BILDIRIM", "uygulanamaz", "açıklanacak anlamlı artış yok"))
    elif not kanal_alan:
        rakipler.append(_rakip("R-BILDIRIM", "çözülmedi", "kanal/kaynak alanı verilmedi"))
    else:
        bos = sum(1 for _, k in tarihli if k in (None, ""))
        surekli = _surekli_kanallar(tarihli) if tarihli else []
        tum_kanallar = sorted({k for _, k in tarihli}, key=str)
        if tarihli and bos / len(tarihli) > VERI_ESIK:
            rakipler.append(_rakip("R-BILDIRIM", "çözülmedi",
                                   f"kanal alanı kayıtların %{round(100 * bos / len(tarihli))}'inde boş"))
        elif not surekli:
            rakipler.append(_rakip("R-BILDIRIM", "çözülmedi",
                                   "dönem boyunca süren kanal yok; bileşim değişimi ayrıştırılamaz"))
        elif surekli == tum_kanallar:
            rakipler.append(_rakip("R-BILDIRIM", "dışlandı",
                                   "kanal bileşimi değişmedi (kanal içi kayıt değişikliği bu "
                                   "sınamayla görülmez)"))
        else:
            alt = [r for r in kayitlar if r.get(kanal_alan) in surekli]
            surekli_trend, h2 = _dene(yurut, "trend", {"satirlar": alt}, "R-BILDIRIM",
                             f"sürekli kanallarda ({', '.join(map(str, surekli))}) artış var mı")
            if h2 or surekli_trend is None:
                rakipler.append(_rakip("R-BILDIRIM", "çözülmedi", h2 or "sonuç yok"))
            elif surekli_trend.get("yorum") == "artan":
                rakipler.append(_rakip("R-BILDIRIM", "dışlandı",
                                       f"sürekli kanallarda da anlamlı artış (p {surekli_trend.get('p')})"))
            else:
                yeni = [k for k in tum_kanallar if k not in surekli]
                rakipler.append(_rakip("R-BILDIRIM", "destekleniyor",
                                       f"sürekli kanallarda anlamlı artış yok "
                                       f"({surekli_trend.get('yorum')}); artış dönem içinde beliren "
                                       f"kanallardan: {', '.join(map(str, yeni))}"))

    # R-MEVSIM — aynı takvim aylarının yıllar arası eşli karşılaştırması
    if not tuttu:
        rakipler.append(_rakip("R-MEVSIM", "uygulanamaz", "açıklanacak anlamlı artış yok"))
    else:
        aylar = _aylik_sayim(tarihli)
        if len(aylar) < 24:
            rakipler.append(_rakip("R-MEVSIM", "çözülmedi", f"yalnız {len(aylar)} ay; en az 24 gerekir"))
        else:
            son24 = aylar[-24:]
            tt, h3 = _dene(yurut, "t_testi", {"tip": "bagimli", "x": son24[12:], "y": son24[:12]},
                           "R-MEVSIM", "son 12 ay ile önceki 12 ayın aynı ayları")
            if h3 or not tt or tt.get("p") is None:
                rakipler.append(_rakip("R-MEVSIM", "çözülmedi",
                                       h3 or (tt or {}).get("not") or "sonuç yok"))
            elif tt["p"] < ALFA and tt.get("ortalama", 0) > 0:
                rakipler.append(_rakip("R-MEVSIM", "dışlandı",
                                       f"aynı aylarda yıllar arası anlamlı artış (ort. fark "
                                       f"{tt.get('ortalama')}, p {tt.get('p')})"))
            elif tt["p"] < ALFA:
                rakipler.append(_rakip("R-MEVSIM", "destekleniyor",
                                       f"aynı aylarda yıllar arası anlamlı DÜŞÜŞ (ort. fark "
                                       f"{tt.get('ortalama')}); trend mevsim/zamanlamadan"))
            else:
                rakipler.append(_rakip("R-MEVSIM", "çözülmedi",
                                       f"aynı aylarda yıllar arası fark anlamsız (p {tt.get('p')})"))

    # R-VERI — tarih geçerliliği ve yinelenen kimlik
    gecersiz = 1 - len(tarihli) / n if n else 1.0
    kimlikler = [r.get("id") for r in kayitlar if r.get("id") not in (None, "")]
    yinelenen = len(kimlikler) - len(set(kimlikler))
    if gecersiz > VERI_ESIK:
        rakipler.append(_rakip("R-VERI", "çözülmedi", f"tarih alanı kayıtların %{round(100 * gecersiz)}'inde geçersiz/eksik"))
    elif n and yinelenen > 0.01 * n:
        rakipler.append(_rakip("R-VERI", "çözülmedi", f"{yinelenen} yinelenen kimlik"))
    else:
        rakipler.append(_rakip("R-VERI", "dışlandı", "tarih geçerli, kimlik yinelenmiyor"))

    if len({dt.date() for dt, _ in tarihli}) < 60:
        saglamlik.append("kısa seri: 60'tan az olaylı gün")
    return birincil, rakipler, saglamlik


# ---------------------------------------------------------------- YOĞUNLAŞMA

def yogunlasma(kaynak, kayitlar, yurut):
    """YOĞUNLAŞMA: Gi* FDR (birincil), R-RASTLANTI, R-PAYDA, R-VERI."""
    saglamlik = []
    gi, hata = _dene(yurut, "sicak_nokta_gi", dict(kaynak), "H1",
                     "birincil öngörü: FDR'li en az bir sıcak hücre")
    if hata or gi is None or "hata" in gi:
        birincil = {"durum": "sınanamadı", "gerekce": hata or (gi or {}).get("hata", "sonuç yok")}
    else:
        sicak = gi.get("sicak", 0)
        birincil = {"durum": "tutuldu" if sicak >= 1 else "belirsiz",
                    "gerekce": f"Gi*: {sicak} sıcak hücre (q ≤ 0,05)"}
    tuttu = birincil["durum"] == "tutuldu"
    rakipler = [_rakip("R-RASTLANTI", "dışlandı" if tuttu else "çözülmedi",
                       "FDR'li sıcak hücre var" if tuttu else "FDR'li sıcak hücre yok")]
    rakipler.append(_rakip("R-PAYDA", "çözülmedi" if tuttu else "uygulanamaz",
                           "risk altındaki nüfus/hedef verisi yok" if tuttu
                           else "açıklanacak yoğunlaşma yok"))
    n = len(kayitlar)
    noktalar = [p for p in (veri.koordinat_al(r) for r in kayitlar) if p]
    gecersiz = 1 - len(noktalar) / n if n else 1.0
    en_sik = Counter(noktalar).most_common(1)
    if gecersiz > VERI_ESIK:
        rakipler.append(_rakip("R-VERI", "çözülmedi", f"koordinat kayıtların %{round(100 * gecersiz)}'inde geçersiz/eksik"))
    elif en_sik and en_sik[0][1] > 2 and en_sik[0][1] / len(noktalar) > YIGILMA_ESIK:
        rakipler.append(_rakip("R-VERI", "çözülmedi",
                               f"tek koordinatta {en_sik[0][1]} kayıt: varsayılan konum yığılması şüphesi"))
    else:
        rakipler.append(_rakip("R-VERI", "dışlandı", "koordinat geçerli, yığılma yok"))
    if len(noktalar) < 30:
        saglamlik.append("30'dan az geçerli nokta")
    return birincil, rakipler, saglamlik


# ---------------------------------------------------------------- SERİ

def seri(kaynak, kayitlar, yurut, mo_alan):
    """SERİ: güçlü seri adayı (birincil), R-RASTLANTI, R-ORTAK-MO, R-TESADUF-YAKINLIK, R-VERI."""
    saglamlik = []
    adaylar, hata = _dene(yurut, "seri_eslestirme", {**kaynak, "mo_alan": mo_alan}, "H1",
                          "birincil öngörü: en az bir güçlü seri adayı")
    if hata or adaylar is None:
        birincil = {"durum": "sınanamadı", "gerekce": hata or "sonuç yok"}
        guclu = []
    else:
        guclu = [c for c in adaylar if c.get("katman") == "güçlü"]
        birincil = {"durum": "tutuldu" if guclu else "belirsiz",
                    "gerekce": f"{len(guclu)} güçlü, {len(adaylar) - len(guclu)} zayıf aday"}
    tuttu = birincil["durum"] == "tutuldu"
    rakipler = [_rakip("R-RASTLANTI", "dışlandı" if tuttu else "çözülmedi",
                       "güçlü adaylar çoklu test (FDR) sonrası" if tuttu else "güçlü aday yok")]
    rakipler.append(_rakip("R-ORTAK-MO", "dışlandı" if tuttu else "uygulanamaz",
                           "güçlü adaylarda paylaşılan davranış taban oranına göre ayırt edici"
                           if tuttu else "güçlü aday yok"))
    rakipler.append(_rakip("R-TESADUF-YAKINLIK", "dışlandı" if tuttu else "uygulanamaz",
                           "güçlü adaylarda MO hattı uzay-zaman hattıyla örtüşüyor"
                           if tuttu else "güçlü aday yok"))
    n = len(kayitlar)
    bos = sum(1 for r in kayitlar if not str(r.get(mo_alan) or "").strip())
    if n and bos / n > MO_BOS_ESIK:
        rakipler.append(_rakip("R-VERI", "çözülmedi", f"MO alanı kayıtların %{round(100 * bos / n)}'inde boş"))
    else:
        rakipler.append(_rakip("R-VERI", "dışlandı", "MO alanı dolu"))
    if n - bos < 20:
        saglamlik.append("MO'lu kayıt 20'den az: taban oranları kararsız")
    return birincil, rakipler, saglamlik

