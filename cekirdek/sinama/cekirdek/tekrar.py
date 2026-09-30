# -*- coding: utf-8 -*-
"""
tekrar.py — Mükerrer mağduriyet ve yakın-tekrar (near-repeat) analizi.
Kayıt alanları: id, tarih (datetime), lat, lon, adres/mağdur anahtarı.
Sadece standart kütüphane.
"""

import math
import random
from collections import Counter, defaultdict
from datetime import date
from itertools import combinations
from .mekan import haversine_km
from .veri import koordinat_al
from .kaynak_butce import _pozitif, _sim_butce
from .ileri import fdr_benjamini_hochberg


def mukerrer_magduriyet(kayitlar, anahtar_alan, gun_penceresi=365):
    """
    Aynı anahtar (adres/mağdur/tesis) için tekrar eden olayları bulur.
    Dönüş: {anahtar: [kayıt_id'leri]} — yalnızca 2+ olayı olan anahtarlar.
    """
    gruplar = defaultdict(list)
    for k in kayitlar:
        anahtar = str(k.get(anahtar_alan) or "").strip()
        if anahtar:
            gruplar[anahtar].append(k)
    return {a: [x.get("id") for x in v] for a, v in gruplar.items() if len(v) >= 2}


def yakin_tekrar_ciftleri(kayitlar, mesafe_km=0.4, gun=14):
    """
    Knox mantığında yakın-tekrar çiftleri: hem uzayda hem zamanda yakın olay çiftleri.
    kayitlar: [{'id':..., 'tarih': datetime, 'lat':..., 'lon':...}, ...]
    Dönüş: [{'id1','id2','mesafe_km','gun_fark'}]
    """
    gecerli = [k for k in kayitlar
               if k.get("tarih") is not None and k.get("lat") is not None]
    # Faz G (v6.4): grid budaması; nihai mesafe haversine — birebir sonuç
    from .mekan import yakin_ciftler_hizli
    pts = [(k["lat"], k["lon"]) for k in gecerli]
    sonuc = []
    for a, b, d in yakin_ciftler_hizli(pts, mesafe_km):
        gf = abs((gecerli[a]["tarih"] - gecerli[b]["tarih"]).days)
        if gf <= gun:
            sonuc.append({"id1": gecerli[a].get("id"),
                          "id2": gecerli[b].get("id"),
                          "mesafe_km": round(d, 3), "gun_fark": gf})
    return sonuc


def knox_tablosu(kayitlar, mesafe_bantlari=None, gun_bantlari=None):
    """
    Gözlenen çift sayılarını uzay-zaman bantlarına dağıtır (Knox testi tablosu).
    Dönüş: {(mesafe_bandi, gun_bandi): adet}
    """
    if mesafe_bantlari is None:
        mesafe_bantlari = [0.2, 0.5, 1.0, 2.0]
    if gun_bantlari is None:
        gun_bantlari = [7, 14, 28, 56]
    gecerli = [k for k in kayitlar
               if k.get("tarih") is not None and k.get("lat") is not None]
    from .mekan import yakin_ciftler_hizli
    pts = [(k["lat"], k["lon"]) for k in gecerli]
    tablo = Counter()
    for a, b, d in yakin_ciftler_hizli(pts, max(mesafe_bantlari)):
        gf = abs((gecerli[a]["tarih"] - gecerli[b]["tarih"]).days)
        mb = next((m for m in mesafe_bantlari if d <= m), None)
        gb = next((g for g in gun_bantlari if gf <= g), None)
        if mb is not None and gb is not None:
            tablo[(mb, gb)] += 1
    return dict(tablo)


SERI_MESAFE_KM = 2.0
SERI_GUN = 60


def _tarih_gunu(v):
    """datetime/date ya da ISO metni → gün sırası (toordinal); çözülemezse None."""
    if hasattr(v, "toordinal"):
        return v.toordinal()
    if isinstance(v, str) and len(v) >= 10:
        try:
            return date.fromisoformat(v[:10]).toordinal()
        except ValueError:
            return None
    return None


SERI_Q = 0.05
_KUYRUK_BUTCE = 200_000


def _kuyruk_olasiligi(agirliklar, olasiliklar, esik):
    """P(Σ wᵢ·Xᵢ ≥ esik), Xᵢ ~ Bernoulli(pᵢ) bağımsız (iç yardımcı).

    Dal-sınır ile kesin hesap; düğüm bütçesi aşılırsa Chernoff üst sınırı
    (ihtiyatlı: gerçek olasılıktan küçük olamaz).
    Returns: (olasılık, kesin_mi).
    """
    cift = sorted(zip(agirliklar, olasiliklar), reverse=True)
    w = [a for a, _ in cift]
    p = [b for _, b in cift]
    kalan = [0.0] * (len(w) + 1)
    for i in range(len(w) - 1, -1, -1):
        kalan[i] = kalan[i + 1] + w[i]
    esik -= 1e-9          # aynı ağırlıkların toplamı: kayan nokta eşitliği
    sayac = [0]

    def dal(i, birikim):
        """i. terimden sonrası için koşullu kuyruk (iç yardımcı)."""
        if birikim >= esik:
            return 1.0
        if birikim + kalan[i] < esik:
            return 0.0
        sayac[0] += 1
        if sayac[0] > _KUYRUK_BUTCE:
            raise OverflowError
        return p[i] * dal(i + 1, birikim + w[i]) + (1 - p[i]) * dal(i + 1, birikim)

    try:
        return min(1.0, dal(0, 0.0)), True
    except (OverflowError, RecursionError):
        en_iyi = 1.0
        for j in range(1, 101):
            lam = 0.05 * j
            log_s = -lam * esik + sum(math.log(1 - pi + pi * math.exp(lam * wi))
                                      for wi, pi in zip(w, p))
            if log_s < 0:
                en_iyi = min(en_iyi, math.exp(log_s))
        return en_iyi, False


def seri_eslestirme(kayitlar, mo_alan, benzerlik_esik=None,
                    mesafe_km=SERI_MESAFE_KM, gun=SERI_GUN, q_esik=SERI_Q):
    """
    Seri suç ADAYI eşleştirme (A4.8): kanıt hatları ve katman.

    Neden (BMK v2): A4.2'nin oran benzerliği (Ružička ≥ 0,6) + ikili
    uzay-zaman süzgeci davranışı tutarsız seriyi neredeyse hiç bağlamıyordu
    (her olayda 8 davranışın 5'i: geri çağırma %3), yayılmış seriyi süzgeçle
    eliyordu (%20) ve özdeş ama yaygın tanımlara en yüksek puanı veriyordu
    (seri yokken tohumların %20'sinde aday). Bağlantı analizinde davranışın
    ayırt ediciliği (taban oranı) ile uzay-zaman yakınlığı ayrı kanıt
    hatlarıdır (Bennell & Canter 2002; Tonkin vd. 2008).

    - MO kanıtı — ayırt edici paylaşım testi: paylaşılan bilgi
      I = Σ idf(A∩B) (nats; idf = ln(N/df)). p = P(rastgele bir kayıt A'nın
      terimlerinden ≥ I bilgi paylaşır), terimler bağımsız ve terim sıklığı
      df/N ile; hangi alt kümenin paylaşıldığı çokluğu hesaba girer. Simetri
      için iki yönün büyüğü alınır (ihtiyatlı).
    - Çoklu test (Benjamini-Hochberg, q_esik) iki ailede: (1) uzay-zaman
      penceresindeki çiftler — pencere MO'dan bağımsız seçildiği için geçerli
      bağımsız süzgeçleme; (2) tüm çiftler.
    - Katman: 'güçlü' = pencere içinde ve MO anlamlı (iki hat örtüşür);
      'zayıf' = MO tüm çiftler ailesinde bile anlamlı ama pencere dışında ya
      da konum/tarih bilinmiyor (hatlar çelişir ya da tek hat var).
    - Dönen her çift bir SERİ ADAYIDIR: inceleme hipotezi, aynı fail ya da
      kimlik iddiası DEĞİLDİR ('ayni_fail_cikarimi': False).

    Sınır: terimler bağımsız sayılır; hep birlikte geçen yaygın kalıp
    ifadeler (ör. "kapı kırılarak girildi") ayırt ediciliğinden fazla bilgi
    taşıyor görünür.

    Args:
        kayitlar: olay kayıtları ('id', MO alanı; varsa lat/lon ve tarih).
        mo_alan: MO metninin alanı.
        benzerlik_esik: isteğe bağlı ek Ružička alt sınırı (varsayılan yok).
        mesafe_km: uzay penceresi (km).
        gun: zaman penceresi (gün).
        q_esik: FDR düzeyi (varsayılan 0,05).

    Returns:
        [{id1, id2, katman, benzerlik, jaccard, paylasilan_bilgi, mesafe_km,
          gun_farki, uzay_zaman, kanit{mo, uzay, zaman}, ayni_fail_cikarimi}]
        — güçlü önce, sonra MO p'sine göre.
    """
    def kelime_kumesi(s):
        """Metni küçük harfli kelime kümesine çevirir (iç yardımcı)."""
        return set(str(s or "").lower().split())

    girdiler = []
    for k in kayitlar:
        kume = kelime_kumesi(k.get(mo_alan))
        if kume:
            girdiler.append((k.get("id"), kume, koordinat_al(k), _tarih_gunu(k.get("tarih"))))
    n = len(girdiler)
    df = Counter(t for _, kume, _, _ in girdiler for t in kume)
    idf = {t: math.log(n / d) for t, d in df.items()}
    bilgili = [[t for t in kume if idf[t] > 0] for _, kume, _, _ in girdiler]
    agirlik = [[idf[t] for t in b] for b in bilgili]
    olasilik = [[df[t] / n for t in b] for b in bilgili]

    ciftler = []
    for i, j in combinations(range(n), 2):
        (_, a, k1, t1), (_, b, k2, t2) = girdiler[i], girdiler[j]
        ortak = a & b
        bilgi = sum(idf[t] for t in ortak)
        if bilgi > 0:
            pa, kesa = _kuyruk_olasiligi(agirlik[i], olasilik[i], bilgi)
            pb, kesb = _kuyruk_olasiligi(agirlik[j], olasilik[j], bilgi)
            p, kesin = max(pa, pb), kesa and kesb
        else:
            p, kesin = 1.0, True
        mesafe = fark = None
        if k1 and k2 and t1 is not None and t2 is not None:
            mesafe = haversine_km(k1[0], k1[1], k2[0], k2[1])
            fark = abs(t1 - t2)
            pencere = "yakin" if mesafe <= mesafe_km and fark <= gun else "uzak"
        else:
            pencere = "bilinmiyor"
        ciftler.append({"i": i, "j": j, "ortak": ortak, "bilgi": bilgi, "p": p,
                        "kesin": kesin, "mesafe": mesafe, "fark": fark,
                        "pencere": pencere})

    q_tum = fdr_benjamini_hochberg([c["p"] for c in ciftler])
    yakin = [x for x, c in enumerate(ciftler) if c["pencere"] == "yakin"]
    q_yakin = dict(zip(yakin, fdr_benjamini_hochberg([ciftler[x]["p"] for x in yakin])))

    def durum(deger, esik):
        """Tek hattın durumu (iç yardımcı)."""
        return "bilinmiyor" if deger is None else ("yakın" if deger <= esik else "uzak")

    sonuc = []
    for x, c in enumerate(ciftler):
        qy = q_yakin.get(x)
        guclu = c["pencere"] == "yakin" and (qy <= q_esik or q_tum[x] <= q_esik)
        if not guclu and q_tum[x] > q_esik:
            continue
        (id1, a, _, _), (id2, b, _, _) = girdiler[c["i"]], girdiler[c["j"]]
        birlesim = sum(idf[t] for t in a | b)
        ruzicka = c["bilgi"] / birlesim if birlesim > 0 else 0.0
        if benzerlik_esik is not None and ruzicka < benzerlik_esik:
            continue
        if str(id1) > str(id2):   # çift içi sıra girdi sırasına bağlı olmasın
            id1, id2 = id2, id1
        mesafe = None if c["mesafe"] is None else round(c["mesafe"], 3)
        sonuc.append({
            "id1": id1, "id2": id2, "katman": "güçlü" if guclu else "zayıf",
            "benzerlik": round(ruzicka, 3), "jaccard": round(len(a & b) / len(a | b), 3),
            "paylasilan_bilgi": round(c["bilgi"], 3),
            "mesafe_km": mesafe, "gun_farki": c["fark"], "uzay_zaman": c["pencere"],
            "kanit": {
                "mo": {"paylasilan": sorted(c["ortak"]), "bilgi_nats": round(c["bilgi"], 3),
                       "p": round(c["p"], 8), "q_tum": q_tum[x], "q_pencere": qy,
                       "kesin_hesap": c["kesin"]},
                "uzay": {"mesafe_km": mesafe, "esik_km": mesafe_km,
                         "durum": durum(c["mesafe"], mesafe_km)},
                "zaman": {"gun_farki": c["fark"], "esik_gun": gun,
                          "durum": durum(c["fark"], gun)}},
            "ayni_fail_cikarimi": False})
    sonuc.sort(key=lambda s: (s["katman"] != "güçlü", s["kanit"]["mo"]["p"],
                              str(s["id1"]), str(s["id2"])))
    return sonuc


# --- Faz 3.1: Monte Carlo anlamlılık (gözlem ≠ kanıt) ---

def _cift_sayisi(kayitlar, mesafe_km, gun):
    """(uzay, zaman) penceresi içindeki çift sayısı — test istatistiği."""
    gecerli = [k for k in kayitlar
               if k.get("tarih") is not None and k.get("lat") is not None]
    from .mekan import yakin_ciftler_hizli
    pts = [(k["lat"], k["lon"]) for k in gecerli]
    n = 0
    for a, b, d in yakin_ciftler_hizli(pts, mesafe_km):
        if abs((gecerli[a]["tarih"] - gecerli[b]["tarih"]).days) <= gun:
            n += 1
    return n


def knox_anlamlilik(kayitlar, mesafe_km=0.4, gun=14, sim=99, seed=None):
    """
    Knox / near-repeat Monte Carlo permütasyon testi.
    Args: mesafe_km (km) — uzaysal yakınlık eşiği.
    Null hipotez: zaman damgaları mekândan bağımsız (uzay-zaman etkileşimi
    yok). Tarihler noktalar arasında karıştırılır, istatistik yeniden
    hesaplanır; p = (1 + sim >= gözlenen) / (sim + 1).
    Dönüş: {'gozlenen', 'beklenen_ortalama', 'oran', 'p', 'sim', 'yorum'}
    """
    _pozitif(mesafe_km, 'mesafe_km')
    _sim_butce(len(kayitlar), sim)
    gecerli = [dict(k) for k in kayitlar
               if k.get("tarih") is not None and k.get("lat") is not None]
    if len(gecerli) < 3:
        return None
    rng = random.Random(seed)
    gozlenen = _cift_sayisi(gecerli, mesafe_km, gun)
    tarihler = [k["tarih"] for k in gecerli]
    sim_degerler = []
    for _ in range(sim):
        kopya = [dict(k) for k in gecerli]
        karisik = tarihler[:]
        rng.shuffle(karisik)
        for k, trh in zip(kopya, karisik):
            k["tarih"] = trh
        sim_degerler.append(_cift_sayisi(kopya, mesafe_km, gun))
    asan = sum(1 for s in sim_degerler if s >= gozlenen)
    p = (1 + asan) / (sim + 1)
    beklenen = sum(sim_degerler) / len(sim_degerler)
    oran = round(gozlenen / beklenen, 3) if beklenen > 0 else None
    # Faz E4 (v6.3): bağımsızlık altında ANALİTİK beklenti — MC'ye ek olarak.
    # E[uzay-zaman yakın çift] = (uzay-yakın çift × zaman-yakın çift) /
    # toplam çift; MC'nin yakınsaması gereken değer.
    uzay_yakin, zaman_yakin, toplam = 0, 0, 0
    for a, b in combinations(gecerli, 2):
        toplam += 1
        if haversine_km(a["lat"], a["lon"], b["lat"], b["lon"]) <= mesafe_km:
            uzay_yakin += 1
        if abs((a["tarih"] - b["tarih"]).days) <= gun:
            zaman_yakin += 1
    beklenen_analitik = (uzay_yakin * zaman_yakin / toplam) if toplam else 0
    return {"gozlenen": gozlenen, "beklenen_ortalama": round(beklenen, 1),
            "beklenen_analitik": round(beklenen_analitik, 1),
            "oran": oran, "p": round(p, 4), "sim": sim,
            "yorum": ("anlamlı yakın-tekrar kümelenmesi" if p < 0.05
                      else "rastgelelik reddedilemedi")}


def yakin_tekrar_anlamlilik(kayitlar, mesafe_km=0.4, gun=14, sim=99, seed=None):
    """yakin_tekrar_ciftleri için anlamlılık sarmalayıcısı (Knox MC).
    Args: mesafe_km (km) — uzaysal yakınlık eşiği."""
    return knox_anlamlilik(kayitlar, mesafe_km, gun, sim, seed)
