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
import statistics
from collections import Counter

from ..cekirdek import degerlendirme, veri
from ..cekirdek.hatalar import SucAnaliziHatasi
from ..cekirdek.iliski import _gammaincc
from . import rak

SINAMA_SURUMU = "sinama-v1.3"
ALFA = 0.05
Z_TEK = statistics.NormalDist().inv_cdf(1 - ALFA)   # tek yönlü, ≈ 1,645
YENI_KANAL_YUZDELIK = 0.05   # ayrım noktası: yeni kanal kayıtlarının %5'lik tarihi
MIN_DONEM_GUN = 30
SUREKLI_PAY = 1 / 16      # kanalın çeyrek başına beklenen payının dörtte biri
VERI_ESIK = 0.05          # geçersiz tarih/koordinat oranı üst sınırı
YIGILMA_ESIK = 0.05       # tek koordinattaki kayıt payı üst sınırı
MO_BOS_ESIK = 0.20


def _rakip(kod, durum, gerekce, olcum=None):
    k = rak.KATALOG[kod]
    r = {"kod": kod, "durum": durum, "etki": k["etki"], "gerekce": gerekce,
         "sonraki_kanit": k["sonraki_kanit"]}
    if olcum is not None:
        r["olcum"] = olcum
    return r


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


def _tam_aylar(tarihli, grup, bas, bit):
    """Pencere içindeki TAM takvim aylarının grup sayımları."""
    say = Counter((dt.year, dt.month) for dt, k in tarihli if k in grup and bas <= dt <= bit)
    aylar = []
    y, a = bas.year, bas.month
    while (y, a) <= (bit.year, bit.month):
        ay_bas = bas.replace(year=y, month=a, day=1, hour=0, minute=0, second=0, microsecond=0)
        sonraki = ay_bas.replace(year=y + (a // 12), month=a % 12 + 1)
        if ay_bas >= bas and sonraki <= bit:
            aylar.append(say.get((y, a), 0))
        y, a = (y + 1, 1) if a == 12 else (y, a + 1)
    return aylar


def _yayilim_sinamasi(tarihli, parcalar):
    """Bir bileşenin Fisher yayılım testi (v1.3; A4.6'daki bölge anomalisiyle aynı
    ilke): T = ΣΣ (x − μ)² / μ, sd = Σ (n − 1) — bileşenin pencere parçalarının
    tam aylarından (≥ 3 ay, μ > 0). Poisson altında T ~ χ²(sd).

    p < ALFA ise φ = T / sd (aşırı yayılım gösterildi), değilse φ = 1. Çarpan
    YALNIZ bu bileşenin varyans terimine uygulanır: v1.1 tüm gruplara en büyük
    oranı (kazara ihtiyatlı), v1.2 havuzlanmış tek çarpanı (baskın bileşenin
    varyansını küçük tahmin etti — BMK v5 K11.6, reddedildi) uyguluyordu.

    Returns: (phi, p ya da None, T, sd).
    """
    ki, sd = 0.0, 0
    for grup, bas, bit in parcalar:
        aylar = _tam_aylar(tarihli, grup, bas, bit)
        if len(aylar) >= 3 and statistics.fmean(aylar) > 0:
            mu = statistics.fmean(aylar)
            ki += sum((x - mu) ** 2 for x in aylar) / mu
            sd += len(aylar) - 1
    if sd == 0:
        return 1.0, None, ki, sd
    p = _gammaincc(sd / 2, ki / 2)
    return (max(1.0, ki / sd) if p < ALFA else 1.0), p, ki, sd


def _bildirim_ayristirma(tarihli, surekli, yeni, kaydet):
    """R-BILDIRIM v1.1: artışın çoğu sürekli kanallarda mı (etki büyüklüğü)."""
    yeni_tarihler = sorted(dt for dt, k in tarihli if k in yeni)
    t_k = yeni_tarihler[int(YENI_KANAL_YUZDELIK * len(yeni_tarihler))]
    t0 = min(dt for dt, _ in tarihli)
    t1 = max(dt for dt, _ in tarihli)
    g_once = (t_k.date() - t0.date()).days
    g_sonra = (t1.date() - t_k.date()).days + 1
    if g_once < MIN_DONEM_GUN or g_sonra < MIN_DONEM_GUN:
        return _rakip("R-BILDIRIM", "çözülmedi",
                      f"yeni kanal öncesi/sonrası dönem {MIN_DONEM_GUN} günden kısa")
    say = Counter((k in surekli, dt >= t_k) for dt, k in tarihli)
    phi_s, p_s, _, _ = _yayilim_sinamasi(tarihli, [(set(surekli), t0, t_k), (set(surekli), t_k, t1)])
    phi_y, p_y, _, _ = _yayilim_sinamasi(tarihli, [(set(yeni), t0, t_k), (set(yeni), t_k, t1)])
    r = degerlendirme.oran_degisimi_ayristirma(
        say[(True, False)], say[(True, True)], say[(False, False)], say[(False, True)],
        g_once, g_sonra, phi_s, phi_y)
    olcum = {"surekli_artis_payi": r["pay_a"], "z": r["z"],
             "yayilim": r["dispersiyon"], "yayilim_yeni": r["dispersiyon_b"],
             "yayilim_p": None if p_s is None else round(p_s, 5),
             "yayilim_p_yeni": None if p_y is None else round(p_y, 5),
             "ayrim_tarihi": t_k.date().isoformat()}
    if kaydet is not None:
        kaydet("bildirim_ayristirma", {k: v for k, v in r.items() if isinstance(v, (int, float))},
               "R-BILDIRIM", "artışın çoğu sürekli kanallarda mı (Δsürekli − Δyeni, quasi-Poisson)")
    pay = "tanımsız" if r["pay_a"] is None else r["pay_a"]
    if r["z"] is None:
        return _rakip("R-BILDIRIM", "çözülmedi", "ayrıştırma tanımsız (varyans sıfır)", olcum)
    if r["z"] > Z_TEK:
        return _rakip("R-BILDIRIM", "dışlandı",
                      f"artışın çoğu dönem boyunca süren kanallarda (pay {pay}, z {r['z']})", olcum)
    if r["z"] < -Z_TEK:
        return _rakip("R-BILDIRIM", "destekleniyor",
                      f"artışın çoğu dönem içinde beliren kanallardan: {', '.join(map(str, yeni))} "
                      f"(sürekli kanal payı {pay}, z {r['z']})", olcum)
    return _rakip("R-BILDIRIM", "çözülmedi",
                  f"artışın ne çoğunun sürekli kanallarda ne yeni kanallarda olduğu gösterilebildi "
                  f"(pay {pay}, z {r['z']})", olcum)


def artis(kaynak, kayitlar, yurut, kanal_alan=None, kaydet=None):
    """ARTIŞ: trend (birincil), R-RASTLANTI, R-BILDIRIM, R-MEVSIM, R-VERI.

    kaydet(ad, ozet, hipotez, amac_metni): araç dışı yerel sınamayı (R-BILDIRIM
    ayrıştırması) gerekçeli adım olarak kanıt zincirine yazar; None ise yazılmaz.
    """
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
                                   "sınamayla görülmez)", {"surekli_artis_payi": 1.0}))
        else:
            yeni = [k for k in tum_kanallar if k not in surekli]
            rakipler.append(_bildirim_ayristirma(tarihli, surekli, yeni, kaydet))

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


# ---------------------------------------------------------------- ETKİ

Z_IKI = statistics.NormalDist().inv_cdf(1 - ALFA / 2)   # iki yönlü, ≈ 1,96
MIN_ETKI_GUN = 90        # öncesi/sonrası penceresinin en kısa uzunluğu
SON_DONEM_GUN = 90       # ortalamaya dönüş: müdahale öncesi "son" dönem


def etki(kaynak, kayitlar, yurut, kaydet, bolge_alan, mudahale, kesinti_tarihi,
         kontrol=None, tampon=None):
    """ETKİ (A4.13): müdahale bölgesinde azalma (birincil), R-RASTLANTI, R-VERI,
    R-ESZAMANLI, R-ORTALAMAYA-DONUS, R-YER-DEGISTIRME.

    Pencereler kesintinin iki yanında EŞİT uzunluktadır (L = kısa taraf).
    Kontrol varsa birincil sınama oran oranlarının log farkıdır (bölgeye özgü,
    Fisher testiyle kapılı φ); kontrol yoksa müdahale bölgesinin kesintili
    zaman serisidir ve R-ESZAMANLI çözülemez (hüküm en çok KIRILGAN).
    """
    kt = veri.tarih_coz(kesinti_tarihi)
    tarihli = []
    for r in kayitlar:
        dt, b = veri.tarih_coz(r.get("tarih")), r.get(bolge_alan)
        if dt is not None and b not in (None, ""):
            tarihli.append((dt, str(b)))
    saglamlik = []
    n = len(kayitlar)
    kalite = len(tarihli) / n if n else 0.0
    r_veri = (_rakip("R-VERI", "dışlandı", "tarih ve bölge alanı geçerli") if kalite >= 1 - VERI_ESIK
              else _rakip("R-VERI", "çözülmedi",
                          f"tarih ya da bölge alanı kayıtların %{round(100 * (1 - kalite))}'inde geçersiz/eksik"))
    if not tarihli or kt is None:
        birincil = {"durum": "sınanamadı", "gerekce": "geçerli tarih/bölge ya da kesinti tarihi yok"}
        return birincil, [_rakip(k, "çözülmedi", "veri yok") for k in
                          ("R-RASTLANTI", "R-ESZAMANLI", "R-ORTALAMAYA-DONUS", "R-YER-DEGISTIRME")] + [r_veri], []
    t0 = min(dt for dt, _ in tarihli)
    t1 = max(dt for dt, _ in tarihli)
    gun = min((kt - t0).days, (t1 - kt).days + 1)
    if gun < MIN_ETKI_GUN:
        birincil = {"durum": "sınanamadı",
                    "gerekce": f"kesintinin iki yanında en az {MIN_ETKI_GUN} gün gerekir ({gun})"}
        return birincil, [_rakip(k, "çözülmedi", "dönem kısa") for k in
                          ("R-RASTLANTI", "R-ESZAMANLI", "R-ORTALAMAYA-DONUS", "R-YER-DEGISTIRME")] + [r_veri], []
    from datetime import timedelta
    bas, bit = kt - timedelta(days=gun), kt + timedelta(days=gun)
    say = Counter((b, dt >= kt) for dt, b in tarihli if bas <= dt < bit)

    def phi(b):
        """Bölgenin Fisher testiyle kapılı yayılım çarpanı (öncesi + sonrası)."""
        return _yayilim_sinamasi(tarihli, [({b}, bas, kt), ({b}, kt, bit)])[0]

    m_o, m_s = say[(mudahale, False)], say[(mudahale, True)]
    if kontrol:
        k_o, k_s = say[(kontrol, False)], say[(kontrol, True)]
        r = degerlendirme.oran_orani_farki(m_o, m_s, k_o, k_s, phi(mudahale), phi(kontrol))
        if kaydet is not None and r is not None:
            kaydet("etki_oran_orani", {k: v for k, v in r.items() if isinstance(v, (int, float))},
                   "H1", "müdahale bölgesinin kontrole göre oran oranı")
        if r is None:
            birincil = {"durum": "sınanamadı", "gerekce": "bir bölgede sıfır sayım: oran tanımsız"}
        else:
            durum = ("tutuldu" if r["z"] <= -Z_IKI else "karşıt" if r["z"] >= Z_IKI else "belirsiz")
            birincil = {"durum": durum,
                        "gerekce": f"oran oranı {r['oran']} (GA {r['ga_alt']}–{r['ga_ust']}, z {r['z']})"}
    else:
        alt = [x for x in kayitlar if str(x.get(bolge_alan)) == str(mudahale)]
        its, hata = _dene(yurut, "kesinti_analizi",
                          {"satirlar": alt, "kesinti_tarihi": kesinti_tarihi, "donem": "ay"},
                          "H1", "kontrolsüz: müdahale bölgesinin kesintili zaman serisi")
        sv = (its or {}).get("seviye_degisimi") or {}
        if hata or sv.get("ga_ust") is None:
            birincil = {"durum": "sınanamadı", "gerekce": hata or "kesinti analizi modeli kurulamadı"}
        else:
            durum = ("tutuldu" if sv["ga_ust"] < 0 else "karşıt" if sv["ga_alt"] > 0 else "belirsiz")
            birincil = {"durum": durum,
                        "gerekce": f"ITS seviye değişimi {sv.get('tahmin')} (GA {sv['ga_alt']}–{sv['ga_ust']})"}
    tuttu = birincil["durum"] == "tutuldu"
    rakipler = [_rakip("R-RASTLANTI", "dışlandı" if tuttu else "çözülmedi",
                       "birincil sınama anlamlı" if tuttu else "anlamlı azalma yok"), r_veri]

    if not tuttu:
        rakipler.append(_rakip("R-ESZAMANLI", "uygulanamaz", "açıklanacak azalma yok"))
    elif kontrol:
        rakipler.append(_rakip("R-ESZAMANLI", "dışlandı", "azalma kontrol bölgesindeki değişimden anlamlı farklı"))
    else:
        rakipler.append(_rakip("R-ESZAMANLI", "çözülmedi", "kontrol bölgesi yok"))

    # ortalamaya dönüş: müdahale öncesi son dönem, önceki temel döneme göre olağandışı yüksek mi
    if not tuttu:
        rakipler.append(_rakip("R-ORTALAMAYA-DONUS", "uygulanamaz", "açıklanacak azalma yok"))
    else:
        son_bas = kt - timedelta(days=SON_DONEM_GUN)
        g_onceki = (son_bas - bas).days
        if g_onceki < SON_DONEM_GUN:
            rakipler.append(_rakip("R-ORTALAMAYA-DONUS", "çözülmedi",
                                   f"müdahale öncesi temel dönem {SON_DONEM_GUN} günden kısa"))
        else:
            ps = Counter((b, dt >= son_bas) for dt, b in tarihli if bas <= dt < kt)
            if kontrol:
                r2 = degerlendirme.oran_orani_farki(ps[(mudahale, False)], ps[(mudahale, True)],
                                                    ps[(kontrol, False)], ps[(kontrol, True)],
                                                    phi(mudahale), phi(kontrol))
            else:
                r2 = degerlendirme.oran_farki_log(ps[(mudahale, False)], ps[(mudahale, True)],
                                                  g_onceki, SON_DONEM_GUN, phi(mudahale))
            if kaydet is not None and r2 is not None:
                kaydet("ortalamaya_donus", {k: v for k, v in r2.items() if isinstance(v, (int, float))},
                       "R-ORTALAMAYA-DONUS", "müdahale öncesi son 3 ay / önceki temel dönem")
            if r2 is None:
                rakipler.append(_rakip("R-ORTALAMAYA-DONUS", "çözülmedi", "sıfır sayım: oran tanımsız"))
            elif r2["z"] > Z_TEK:
                rakipler.append(_rakip("R-ORTALAMAYA-DONUS", "destekleniyor",
                                       f"müdahale öncesi son 3 ayda olağandışı yükseliş (oran {r2['oran']}, z {r2['z']})",
                                       {"oncesi_zirve_orani": r2["oran"], "z": r2["z"]}))
            else:
                rakipler.append(_rakip("R-ORTALAMAYA-DONUS", "dışlandı",
                                       f"müdahale öncesinde olağandışı zirve yok (oran {r2['oran']}, z {r2['z']})",
                                       {"oncesi_zirve_orani": r2["oran"], "z": r2["z"]}))

    # yer değiştirme: tampon bölge kontrole göre arttı mı
    if not tuttu:
        rakipler.append(_rakip("R-YER-DEGISTIRME", "uygulanamaz", "açıklanacak azalma yok"))
    elif not tampon:
        rakipler.append(_rakip("R-YER-DEGISTIRME", "çözülmedi", "tampon bölge verilmedi"))
    elif not kontrol:
        rakipler.append(_rakip("R-YER-DEGISTIRME", "çözülmedi",
                               "kontrol yok: tampondaki değişim genel eğilimden ayrılamaz"))
    else:
        r3 = degerlendirme.oran_orani_farki(say[(tampon, False)], say[(tampon, True)],
                                            say[(kontrol, False)], say[(kontrol, True)],
                                            phi(tampon), phi(kontrol))
        if kaydet is not None and r3 is not None:
            kaydet("yer_degistirme", {k: v for k, v in r3.items() if isinstance(v, (int, float))},
                   "R-YER-DEGISTIRME", "tampon bölgenin kontrole göre oran oranı")
        if r3 is None:
            rakipler.append(_rakip("R-YER-DEGISTIRME", "çözülmedi", "sıfır sayım: oran tanımsız"))
        elif r3["z"] > Z_TEK:
            rakipler.append(_rakip("R-YER-DEGISTIRME", "destekleniyor",
                                   f"tampon bölge kontrole göre arttı (oran {r3['oran']}, z {r3['z']})",
                                   {"tampon_orani": r3["oran"], "z": r3["z"]}))
        else:
            rakipler.append(_rakip("R-YER-DEGISTIRME", "dışlandı",
                                   f"tamponda kontrole göre anlamlı artış yok (oran {r3['oran']}, z {r3['z']})",
                                   {"tampon_orani": r3["oran"], "z": r3["z"]}))
    if gun < 2 * MIN_ETKI_GUN:
        saglamlik.append(f"kısa dönem: kesintinin iki yanında {gun} gün (< {2 * MIN_ETKI_GUN})")
    return birincil, rakipler, saglamlik

