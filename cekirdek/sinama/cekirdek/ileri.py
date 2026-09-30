# -*- coding: utf-8 -*-
"""
ileri.py — İleri suç analizi teknikleri:
kontrol grafiği/CUSUM, Poisson anomali, gün×saat matrisi, yükselen hotspot,
journey-to-crime (Rossmo), risk arazi modeli (RTM), olaylar arası süre,
Benford yasası, k-means kümeleme, Holt-Winters tahmin.
Tamamı saf Python.
"""

import calendar
import math
import random
import statistics
from collections import Counter, defaultdict
from datetime import date, timedelta
from .mekan import haversine_km, sinir_kutusu
from .hipotez import _betainc, t_cdf
from .iliski import _gammaincc


# --- 1) Kontrol grafiği + kalibre CUSUM (zaman serisinde kalıcı artış) ---
# A4.15: ham `cusum` (tüm seri ortalaması, h = 5σ) kaldırıldı — kalibre değildi
# (BMK v8: değişimsiz seride %89 alarm); yerine `kirilma_cusum`.

def kontrol_grafigi(seri, sigma_k=3.0):
    """
    Günlük seri için kontrol grafiği: ortalama ± k*sigma sınırları dışı
    günleri işaretler. Dönüş: {'ortalama','alt','ust','asim_gunleri'}.
    """
    if len(seri) < 5:
        return None
    mu = statistics.fmean(seri)
    # örneklem std sapması (stdev): kontrol limitleri çıkarımsal bağlamda
    # örneklem tabanlıdır; tanımlayıcı özetler için bkz. istatistik.ozet
    sd = statistics.stdev(seri) or 1e-9
    alt, ust = mu - sigma_k * sd, mu + sigma_k * sd
    asim = [{"gun": i, "deger": v} for i, v in enumerate(seri)
            if v < alt or v > ust]
    return {"ortalama": round(mu, 3), "alt": round(alt, 3),
            "ust": round(ust, 3), "asim_gunleri": asim}


_NORMAL = statistics.NormalDist()
_ESIK_ONBELLEK = {}
KIRILMA_ISINMA = {"hafta": 8, "ay": 6}


def _cusum_esigi(adim, k, alfa, benzetim=4000, tohum=20260930):
    """Bağımsız N(0,1) adımlarda en büyük CUSUM'un (1 - alfa) yüzdeliği:
    değişim yokken seri boyunca en az bir alarm olasılığı ≈ alfa olacak eşik
    (deterministik Monte Carlo, önbellekli)."""
    anahtar = (adim, k, alfa, benzetim, tohum)
    if anahtar not in _ESIK_ONBELLEK:
        r = random.Random(tohum)
        enbuyukler = []
        for _ in range(benzetim):
            s = m = 0.0
            for _ in range(adim):
                s = max(0.0, s + r.gauss(0.0, 1.0) - k)
                m = max(m, s)
            enbuyukler.append(m)
        enbuyukler.sort()
        _ESIK_ONBELLEK[anahtar] = enbuyukler[math.ceil((1 - alfa) * benzetim) - 1]
    return _ESIK_ONBELLEK[anahtar]


def _donem_sayimlari(gunler, donem):
    """Günlerden (date) dönem sayımları ve her dönemin son günü; hafta ilk
    günden başlayan 7 günlük bloklar, ay takvim ayları."""
    ilk, son = min(gunler), max(gunler)
    if donem == "hafta":
        adet = (son - ilk).days // 7 + 1
        sayim = [0] * adet
        for g in gunler:
            sayim[(g - ilk).days // 7] += 1
        return sayim, [ilk + timedelta(days=7 * i + 6) for i in range(adet)]
    aylar = []
    y, m = ilk.year, ilk.month
    while (y, m) <= (son.year, son.month):
        aylar.append((y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    sira = {a: i for i, a in enumerate(aylar)}
    sayim = [0] * len(aylar)
    for g in gunler:
        sayim[sira[(g.year, g.month)]] += 1
    return sayim, [date(y, m, calendar.monthrange(y, m)[1]) for y, m in aylar]


def ay_yayilim_p(aylik, benzetim=2000, tohum=20260930):
    """Aylık sayımlarda ardışık-fark yayılım testi (tek bir basamağa dayanıklı):
    V = Σ(x_m − x_{m−1})² / (2(M−1)x̄); p, bağımsız Poisson(x̄) altında
    deterministik Monte Carlo. Aylar arası heterojenlik (aşırı yayılım) varsa
    küçük p. Yetersiz veride None."""
    m = len(aylik)
    ort = statistics.fmean(aylik) if aylik else 0.0
    if m < 3 or ort <= 0:
        return None

    def v(x):
        """Ardışık fark istatistiği."""
        return sum((x[i] - x[i - 1]) ** 2 for i in range(1, len(x))) / (2 * (len(x) - 1) * ort)

    gozlenen = v(aylik)
    r = random.Random(tohum)
    esik = math.exp(-ort) if ort < 30 else None
    buyuk = 0
    for _ in range(benzetim):
        x = []
        for _ in range(m):
            if esik is not None:      # Knuth (küçük λ)
                k, p = 0, 1.0
                while True:
                    p *= r.random()
                    if p <= esik:
                        break
                    k += 1
            else:                     # büyük λ: yuvarlanmış normal yaklaşımı
                k = max(0, round(r.gauss(ort, math.sqrt(ort))))
            x.append(k)
        buyuk += v(x) >= gozlenen
    return (buyuk + 1) / (benzetim + 1)


def _kendinden_z(sayim, isinma):
    """Kendinden başlayan standartlaştırma (Hawkins): t. dönem, ÖNCEKİ t dönemin
    ortalaması ve örneklem sapmasıyla; kestirim hatası varyansı σ²(1 + 1/t) olduğundan
    oran t(t−1) dağılır, olasılık dönüşümüyle N(0,1)'e çevrilir. Sapma sıfırsa 0."""
    z = []
    for t in range(isinma, len(sayim)):
        once = sayim[:t]
        ort, sd = statistics.fmean(once), statistics.stdev(once)
        if sd <= 0:
            z.append(0.0)
            continue
        tt = (sayim[t] - ort) / (sd * math.sqrt(1 + 1 / t))
        z.append(_NORMAL.inv_cdf(min(max(t_cdf(tt, t - 1), 1e-12), 1 - 1e-12)))
    return z


def kirilma_cusum(gunler, donem=None, k=0.5, alfa=0.05):
    """
    Kalıcı artış alarmı — kendinden başlayan, seri düzeyinde kalibre CUSUM (A4.15).

    - Dönem: verilmezse otomatik — aylık sayımlarda ardışık-fark yayılım testi
      (ay_yayilim_p) p < alfa ise "ay" (aylar arası heterojenlik haftalık
      sapmaları ilişkili kılar), değilse "hafta".
    - Kendinden başlama (Hawkins): her dönem ÖNCEKİ dönemlerin ortalaması ve
      sapmasıyla standartlaştırılır, t → normal dönüşümüyle N(0,1)'e çevrilir;
      temel dönem varsayımı ve değişim sonrası veriyle kirlenmiş ortalama yoktur.
      Isınma: 8 hafta / 6 ay.
    - Eşik: bağımsız N(0,1) adımlarla Monte Carlo — değişim yokken seri
      BOYUNCA en az bir alarm olasılığı ≈ alfa (seri uzunluğuna göre).

    Args:
        gunler: olay günleri (date).
        donem: "hafta" | "ay" | None (otomatik).
        k: referans değeri (σ biriminde; 0,5 → 1σ kaymaya ayarlı).
        alfa: seri düzeyinde yanlış alarm olasılığı.

    Returns:
        (alarmlar, donem) — alarm: {gun (ilk günden itibaren, dönemin son günü),
        tarih, donem, cusum, esik}; alarm sonrası toplam sıfırlanır.
    """
    if not gunler:
        return [], None
    if donem is None:
        p = ay_yayilim_p(_donem_sayimlari(gunler, "ay")[0])
        donem = "ay" if p is not None and p < alfa else "hafta"
    sayim, bitis = _donem_sayimlari(gunler, donem)
    isinma = KIRILMA_ISINMA[donem]
    if len(sayim) <= isinma + 1:
        return [], donem
    z = _kendinden_z(sayim, isinma)
    h = _cusum_esigi(len(z), k, alfa)
    ilk = min(gunler)
    s, alarmlar = 0.0, []
    for i, deger in enumerate(z):
        s = max(0.0, s + deger - k)
        if s > h:
            b = bitis[isinma + i]
            alarmlar.append({"gun": (b - ilk).days, "tarih": b.isoformat(), "donem": donem,
                             "cusum": round(s, 3), "esik": round(h, 3)})
            s = 0.0
    return alarmlar, donem


# --- 2) Poisson anomali (bölge bazında olağandışılık) ---

def poisson_ust_kuyruk(gozlenen, beklenen):
    """
    P(X >= gozlenen | Poisson(beklenen)) — log-uzayında hesaplama.
    math.exp(-beklenen) büyük beklenen değerde (λ ≳ 745) underflow'a
    düştüğü için PMF logaritmik yazılır; yoğun bölgelerde de doğrudur.
    """
    if beklenen <= 0:
        return 1.0 if gozlenen <= 0 else 0.0

    def log_pmf(x):
        """Poisson log-olasılık kütle fonksiyonu (taşmayı önler; iç yardımcı).
        """
        return -beklenen + x * math.log(beklenen) - math.lgamma(x + 1)

    # sağ kuyruk toplamı: terim ihmal eşiğine kadar ilerle
    toplam = 0.0
    x = max(0, int(gozlenen))
    log0 = log_pmf(x)
    while True:
        lp = log_pmf(x)
        if lp < log0 - 40:  # göreli katkı < ~1e-17
            break
        toplam += math.exp(lp)
        x += 1
        if x > gozlenen + 100 * math.sqrt(beklenen) + 1000:
            break
    return round(min(1.0, max(0.0, toplam)), 5)


def fdr_benjamini_hochberg(p_degerleri):
    """
    Benjamini-Hochberg FDR: p-değer listesi → q-değer listesi (aynı sıra).
    Çoklu karşılaştırmada (çok bölge tek tek test) yanlış-pozitif
    oranını kontrol eder.
    """
    m = len(p_degerleri)
    if m == 0:
        return []
    sirali = sorted(enumerate(p_degerleri), key=lambda x: x[1])
    q = [0.0] * m
    onceki = 1.0
    for sira, (idx, p) in reversed(list(enumerate(sirali))):
        deger = min(onceki, p * m / (sira + 1))
        q[idx] = min(1.0, deger)
        onceki = deger
    return [round(x, 5) for x in q]


def neg_binom_ust_kuyruk(gozlenen, beklenen, varyans):
    """
    Negatif binom üst kuyruk P(X >= gözlenen) — aşırı yayılımlı sayım
    verisi için Poisson yerine (v6.3, Faz E1).
    Parametreler momentlerden: r = mu^2 / (var - mu), p = r / (r + mu).
    NB(r,p) CDF: F(k-1) = I_p(r, k)  →  üst kuyruk = I_{1-p}(k, r).
    varyans <= beklenen ise (yayılım yok) Poisson'a düşer.
    """
    if varyans <= beklenen or beklenen <= 0 or gozlenen <= 0:
        return poisson_ust_kuyruk(gozlenen, beklenen)
    r = beklenen * beklenen / (varyans - beklenen)
    p = r / (r + beklenen)
    k = int(gozlenen)
    return _betainc(1.0 - p, k, r)


def bolge_anomali(bolge_sayilari, beklenenler=None, alfa=0.05):
    """
    {'bolge': olay_sayisi} sözlüğü için anomali testi.
    beklenenler verilmezse genel ortalama kullanılır.
    Çıktıya BH-FDR q-değerleri eklenir (K10).
    A4.5: 'anlamli' KARARI q ≤ alfa ile verilir (alfa = FDR düzeyi, varsayılan
    0,05). Önceden düzeltmesiz p ≤ 0,01 idi: BMK v1 K6.2 — 50 homojen bölgede
    %40 sahte "anlamlı" (q hesaplanıyor ama karar onunla verilmiyordu).
    v6.3 (Faz E1): aşırı yayılım (var/mean > 1.5) saptandığında p-değerleri
    otomatik olarak NEGATİF BİNOM modelinden hesaplanır — naif Poisson'un
    yanlış-pozitif üretmesi yapısal olarak engellenir (model alanına bakın).
    """
    if beklenenler is None:
        mu = statistics.fmean(bolge_sayilari.values())
        beklenenler = {b: mu for b in bolge_sayilari}
    # Model seçimi: FORMAL Fisher dispersiyon testi (v6.3) —
    # T = Σ(x-μ)²/μ ~ χ²(n-1) (Poisson null); p<0.05 → aşırı yayılım.
    # Yayılım parametresi r: üst %10 kırpılmış momentlerden (maskeleme
    # önlemi) — tek uç bölge varyansı şişirip NB null'unu boğduramaz.
    degerler = list(bolge_sayilari.values())
    disp, disp_p, var_trim, mu_trim = None, None, None, None
    if len(degerler) > 2:
        mu_d = statistics.fmean(degerler)
        if mu_d > 0:
            disp = statistics.pvariance(degerler) / mu_d
            t_ist = sum((x - mu_d) ** 2 for x in degerler) / mu_d
            disp_p = _gammaincc((len(degerler) - 1) / 2, t_ist / 2)
        sirali = sorted(degerler)
        kirp = max(1, len(sirali) // 10) if len(sirali) > 3 else 0
        govde = sirali[:len(sirali) - kirp] if kirp else sirali
        mu_trim = statistics.fmean(govde)
        var_trim = statistics.pvariance(govde) if len(govde) > 1 else 0.0
    nb_kullan = disp_p is not None and disp_p < 0.05
    tum = []
    for b, goz in bolge_sayilari.items():
        lam = beklenenler.get(b, 1e-9)
        p_pois = poisson_ust_kuyruk(goz, lam)
        if nb_kullan:
            # ortak yayılım parametresi r (NB2), kırpılmış momentlerden:
            # var(lam) = lam + lam^2/r; var_trim <= mu_trim ise Poisson'a düşer
            mu_b = statistics.fmean(beklenenler.values()) or 1e-9
            r_ortak = mu_trim * mu_trim / max(var_trim - mu_trim, 1e-9)
            var_bolge = lam + lam * lam / r_ortak
            p = neg_binom_ust_kuyruk(goz, lam, var_bolge)
        else:
            p = p_pois
        tum.append({"bolge": b, "gozlenen": goz,
                    "beklenen": round(lam, 2), "p": p,
                    "p_poisson": p_pois})
    qs = fdr_benjamini_hochberg([x["p"] for x in tum])
    for x, q in zip(tum, qs):
        x["q"] = q
    notlar = []
    if nb_kullan:
        notlar.append(
            f"aşırı yayılım (Fisher testi p={round(disp_p, 4)}; "
            f"dispersiyon üst %10 kırpılmış tahmin); p-değerleri "
            f"negatif binom modelinden "
            f"(Poisson p'leri 'p_poisson' alanında karşılaştırma için "
            f"korunur)")
    if len(degerler) > 10:
        notlar.append(f"{len(degerler)} bölge tek tek test edildi; "
                      "çoklu karşılaştırma için q (FDR) kullanın")
    sonuc = [x for x in tum if x["q"] <= alfa]
    sonuc.sort(key=lambda x: x["p"])
    return {"anlamli": sonuc, "tum_sonuclar": sorted(tum, key=lambda x: x["p"]),
            "notlar": notlar, "model": "neg-binom" if nb_kullan else "poisson",
            "dispersiyon_orani": round(disp, 3) if disp is not None else None,
            "fisher_dispersiyon_p": round(disp_p, 5) if disp_p is not None else None}


# --- 3) Gün × saat ısı matrisi ---

def gun_saat_matrisi(kayitlar, alan="tarih"):
    """(haftanın günü, saat) kesişimi matrisi: {gun: {saat: adet}}."""
    m = defaultdict(Counter)
    for k in kayitlar:
        t = k.get(alan)
        if t is not None:
            m[t.weekday()][t.hour] += 1
    return {g: dict(sorted(s.items())) for g, s in sorted(m.items())}


def en_riskli_dilimler(matris, ust_n=5):
    """gun_saat_matrisi çıktısından en yoğun gün-saat dilimleri."""
    duz = [(g, s, a) for g, saatler in matris.items() for s, a in saatler.items()]
    duz.sort(key=lambda x: -x[2])
    return [{"gun": g, "saat": s, "adet": a} for g, s, a in duz[:ust_n]]


# --- 4) Yükselen/sönen/kalıcı hotspot (iki dönem karşılaştırması) ---

def donemsel_hotspot_karsilastirma(grid_once, grid_sonra, tolerans_km=0.3):
    """
    İki dönemin grid_hotspot çıktısını eşleştirir.
    Sınıflar: yeni / yükselen / kalıcı / zayıflayan / sönen.
    Args: tolerans_km (km) — aynı hücre sayılma eşleşme yarıçapı.
    """
    def anahtar(h, havuz):
        """Nokta havuzunda tolerans_km (km) içindeki ilk eşin indeksi; yoksa None (iç yardımcı).
        """
        for j, g in enumerate(havuz):
            if haversine_km(h["lat"], h["lon"], g["lat"], g["lon"]) <= tolerans_km:
                return j
        return None
    eslesen = {}
    kalan = list(grid_sonra)
    sonuc = []
    for h in grid_once:
        j = anahtar(h, kalan)
        if j is None:
            sonuc.append({"lat": h["lat"], "lon": h["lon"], "sinif": "sönen",
                          "once": h["adet"], "sonra": 0})
        else:
            g = kalan[j]
            eslesen[id(g)] = True
            fark = g["adet"] - h["adet"]
            sinif = ("yükselen" if fark > 0 else
                     ("zayıflayan" if fark < 0 else "kalıcı"))
            sonuc.append({"lat": h["lat"], "lon": h["lon"], "sinif": sinif,
                          "once": h["adet"], "sonra": g["adet"]})
    for g in kalan:
        if id(g) not in eslesen:
            sonuc.append({"lat": g["lat"], "lon": g["lon"], "sinif": "yeni",
                          "once": 0, "sonra": g["adet"]})
    return sonuc


# --- 5) Journey-to-crime (Rossmo coğrafi profil) ---

def cografi_profil(olay_noktalari, tampon_km=1.0, hucre_km=0.5, f=1.0, g=1.0):
    """
    Rossmo CGT formülüyle failin üs bölgesi olasılık haritası.
    Seri olay koordinatlarından [(lat,lon)...] grid olasılıkları üretir.
    Args: tampon_km (km) — etki tamponu; hucre_km (km) — grid çözünürlüğü.
    """
    if len(olay_noktalari) < 3:
        return []
    min_lat, min_lon, max_lat, max_lon = sinir_kutusu(olay_noktalari)
    ped = tampon_km / 110.574
    min_lat -= ped; max_lat += ped; min_lon -= ped; max_lon += ped
    d_lat = hucre_km / 110.574
    ort = math.radians((min_lat + max_lat) / 2)
    km_lon = 111.320 * math.cos(ort) or 1e-9
    d_lon = hucre_km / km_lon
    sonuc = []
    i = 0
    while min_lat + i * d_lat < max_lat:
        j = 0
        lat = min_lat + (i + 0.5) * d_lat
        while min_lon + j * d_lon < max_lon:
            lon = min_lon + (j + 0.5) * d_lon
            p = 0.0
            for (plat, plon) in olay_noktalari:
                d = math.hypot((plat - lat) * 110.574, (plon - lon) * km_lon)
                if d < 1e-6:
                    d = 1e-6
                if d > tampon_km:
                    p += 1.0 / (d ** f)
                else:
                    p += (tampon_km ** (g - f)) / ((2 * tampon_km - d) ** g)
            sonuc.append({"lat": round(lat, 6), "lon": round(lon, 6),
                          "olasilik": round(p, 4)})
            j += 1
        i += 1
    sonuc.sort(key=lambda x: -x["olasilik"])
    return sonuc


# --- 6) Risk arazi modeli (RTM: ağırlıklı katman üst üste bindirme) ---

def risk_arazi(nokta_katmanlari, hucre_km=0.5, etki_km=0.5, agirliklar=None):
    """
    nokta_katmanlari: {'katman_adi': [(lat,lon)...]} — risk faktörü konumları
    (ör. bar çıkışları, park cepleri). Her grid hücresi, etki_km (km)
    içindeki faktörlerin ağırlıklı toplamını skor alır; hucre_km (km)
    grid çözünürlüğüdür.
    """
    tum = [p for pts in nokta_katmanlari.values() for p in pts]
    if not tum:
        return []
    min_lat, min_lon, max_lat, max_lon = sinir_kutusu(tum)
    d_lat = hucre_km / 110.574
    ort = math.radians((min_lat + max_lat) / 2)
    km_lon = 111.320 * math.cos(ort) or 1e-9
    d_lon = hucre_km / km_lon
    agirliklar = agirliklar or {}
    sonuc = []
    i = 0
    while min_lat + i * d_lat < max_lat:
        j = 0
        lat = min_lat + (i + 0.5) * d_lat
        while min_lon + j * d_lon < max_lon:
            lon = min_lon + (j + 0.5) * d_lon
            skor = 0.0
            for ad, pts in nokta_katmanlari.items():
                w = float(agirliklar.get(ad, 1.0))
                for (plat, plon) in pts:
                    if haversine_km(lat, lon, plat, plon) <= etki_km:
                        skor += w
            if skor > 0:
                sonuc.append({"lat": round(lat, 6), "lon": round(lon, 6),
                              "risk_skoru": round(skor, 2)})
            j += 1
        i += 1
    sonuc.sort(key=lambda x: -x["risk_skoru"])
    return sonuc


# --- 7) Olaylar arası süre (seri fail ritmi) ---

def olaylar_arasi_sure(tarihler):
    """Sıralı tarih listesinden gün cinsinden aralıkların özeti (ritim)."""
    if len(tarihler) < 2:
        return None
    ts = sorted(tarihler)
    araliklar = [(ts[i + 1] - ts[i]).total_seconds() / 86400.0
                 for i in range(len(ts) - 1)]
    return {"n_aralik": len(araliklar),
            "ortalama_gun": round(statistics.fmean(araliklar), 2),
            "medyan_gun": round(statistics.median(araliklar), 2),
            "min_gun": round(min(araliklar), 2),
            "maks_gun": round(max(araliklar), 2)}


# --- 8) Benford yasası (uydurma sayı tespiti) ---

def benford_testi(degerler):
    """
    İlk basamak dağılımını Benford yasasıyla karşılaştırır.
    Dolandırıcılık/muhasebe verilerinde uydurma kayıt şüphesi için.
    Dönüş: {'gozlenen', 'beklenen', 'ki_kare', 'uyum'}
    """
    ilk = Counter()
    for v in degerler:
        try:
            s = str(abs(float(v))).lstrip("0.")
            if s and s[0].isdigit() and s[0] != "0":
                ilk[int(s[0])] += 1
        except (TypeError, ValueError):
            continue
    n = sum(ilk.values())
    if n < 10:
        return None
    beklenen = {d: n * math.log10(1 + 1 / d) for d in range(1, 10)}
    x2 = sum((ilk.get(d, 0) - beklenen[d]) ** 2 / beklenen[d]
             for d in range(1, 10))
    # df=8 için ki-kare %5 kritik değeri 15.51
    return {"n": n,
            "gozlenen": {d: ilk.get(d, 0) for d in range(1, 10)},
            "beklenen": {d: round(beklenen[d], 1) for d in range(1, 10)},
            "ki_kare": round(x2, 2),
            "uyum": "şüpheli (Benford'dan sapma)" if x2 > 15.51 else "uyumlu"}


# --- 9) Basit k-means (olay gruplama) ---

def k_means(noktalar, k=3, max_iter=50, seed=None):
    """
    UYARI: k-means başlangıç merkezlerine duyarlıdır; tek koşu kesin
    kümeleme sayılmamalıdır. Farklı seed değerleriyle kararlılığı
    doğrulayın (kritik kararlarda birden çok koşu önerilir).
    """
    """
    Özellik vektörleri üzerinde k-means.
    noktalar: [[x1, x2, ...], ...] (ör. [lat, lon] veya normalize özellikler).
    Dönüş: {'merkezler', 'etiketler', 'kume_buyuklukleri'}
    """
    if len(noktalar) < k:
        return None
    rng = random.Random(seed)
    merkezler = [list(p) for p in rng.sample(list(noktalar), k)]
    etiketler = [0] * len(noktalar)
    for _ in range(max_iter):
        degisim = False
        for i, p in enumerate(noktalar):
            en_yakin = min(range(k),
                           key=lambda c: sum((p[d] - merkezler[c][d]) ** 2
                                             for d in range(len(p))))
            if en_yakin != etiketler[i]:
                etiketler[i] = en_yakin
                degisim = True
        for c in range(k):
            uyeler = [noktalar[i] for i in range(len(noktalar))
                      if etiketler[i] == c]
            if uyeler:
                merkezler[c] = [statistics.fmean(p[d] for p in uyeler)
                                for d in range(len(uyeler[0]))]
        if not degisim:
            break
    buyukluk = Counter(etiketler)
    return {"merkezler": [[round(x, 5) for x in m] for m in merkezler],
            "etiketler": etiketler,
            "kume_buyuklukleri": dict(buyukluk)}


# --- 10) Holt-Winters tahmin (kısa vadeli projeksiyon) ---

def holt_winters(seri, mevsim=7, alfa=0.4, beta=0.1, gama=0.1, ileri=7):
    """
    Üçlü üstel düzleştirme (toplamalı mevsimsellik).
    Günlük seri için önümüzdeki 'ileri' gün tahmini.
    Uyarı: mekanik projeksiyon; karar değil, destek aracıdır.
    """
    if len(seri) < 2 * mevsim:
        return None
    seviye = statistics.fmean(seri[:mevsim])
    trend = (statistics.fmean(seri[mevsim:2 * mevsim]) - seviye) / mevsim
    mevsimsel = [seri[i] - seviye for i in range(mevsim)]
    for v in seri:
        onceki_seviye = seviye
        seviye = alfa * (v - mevsimsel[0]) + (1 - alfa) * (seviye + trend)
        trend = beta * (seviye - onceki_seviye) + (1 - beta) * trend
        mevsimsel.append(gama * (v - seviye) + (1 - gama) * mevsimsel.pop(0))
    tahmin = []
    for h in range(1, ileri + 1):
        tahmin.append(round(max(0.0, seviye + h * trend +
                              mevsimsel[(h - 1) % mevsim]), 2))
    return tahmin


def otokorelasyon(seri, lag):
    """Basit Pearson otokorelasyonu (lag gecikmeli). Mevsimsellik gerçekliği
    denetimi: Holt-Winters mevsim=7 öncesi lag=7 katsayısına bakın."""
    n = len(seri)
    if n <= lag:
        return None
    x, y = seri[:-lag], seri[lag:]
    mx, my = statistics.fmean(x), statistics.fmean(y)
    pay = sum((a - mx) * (b - my) for a, b in zip(x, y))
    dx = math.sqrt(sum((a - mx) ** 2 for a in x))
    dy = math.sqrt(sum((b - my) ** 2 for b in y))
    if dx == 0 or dy == 0:
        return 0.0
    return round(pay / (dx * dy), 4)
