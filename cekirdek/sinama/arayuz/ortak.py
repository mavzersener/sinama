# -*- coding: utf-8 -*-
r"""
arayuz/ortak.py — arayüz katmanının ortak servisleri (v6.1, G1).
Araç kaydı (ARACLAR), PII varsayılan-red, denetim logu, veri erişim
yardımcıları, vektör/matris çözümleri ve TEK GATE OTORİTESİNİN dispatch
bağlantısı (dispatch_gate). Domain mantığı burada ve araclar.py'de;
sunucu.py yalnız protokol konuşur (ince transport).
"""

import json
import logging
import logging.handlers
import os
import re
import sys
import time
import traceback
import uuid

from ..cekirdek import veri, zarar
from ..cekirdek.hatalar import KullanimHatasi, VeriHatasi
from ..cekirdek.regresyon import _sonlu_sayi, _tasarim_dogrula
from .istek_baglam import baglam
from ..kalite import kapi as _kapi, KapiRed

PROTOKOL = "2024-11-05"
# H6.2: sunucunun konuştuğu protokoller (initialize'da beyan edilir;
# bilinmeyen istemci sürümü reddedilmez — en yakın uyumlu davranış +
# uyarı notu ile devam edilir)
DESTEKLENEN_PROTOKOLLER = ["2024-11-05"]


SURUM = "6.8.0"


MAKS_QUADRATIC_N = 5000


OTURUM = uuid.uuid4().hex[:12]


def logger_kur():
    """
    H5.1 (v6.7): paket loglayıcısı — stdlib logging, seviyeli, modül
    etiketli. stderr'e yazar (stdout yalnız JSON-RPC içindir). Seviye
    SINAMA_LOG_SEVIYE ile ayarlanır (varsayılan INFO). Audit akışı
    bundan BAĞIMSIZDIR ve ayrı kalır (kanıt niteliği taşır).
    """
    lg = logging.getLogger("sinama")
    if not lg.handlers:
        h = logging.StreamHandler()
        h.setFormatter(logging.Formatter(
            "%(asctime)s %(levelname)-7s [%(name)s] %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S"))
        lg.addHandler(h)
        lg.propagate = False
    lg.setLevel(os.environ.get("SINAMA_LOG_SEVIYE", "INFO").upper())
    return lg


def log(*a, seviye="INFO"):
    """Tek nokta log cephesi: log("mesaj:", x) veya seviye="WARNING".
    Seviyeler: INFO yaşam döngüsü, WARNING politika/protokol,
    ERROR kanıt kaybı/iç hata."""
    logger_kur().log(getattr(logging, seviye.upper(), logging.INFO),
                     " ".join(str(x) for x in a))


def audit_kur():
    """Dönen rotasyonlu audit logu; yalnız meta veri, asla argüman değeri yok."""
    log_dizin = os.environ.get("SINAMA_LOG_DIR") or os.getcwd()
    os.makedirs(log_dizin, exist_ok=True)
    yol = os.path.join(log_dizin, "sinama_audit.log")
    h = logging.handlers.RotatingFileHandler(
        yol, maxBytes=5 * 1024 * 1024, backupCount=3, encoding="utf-8")
    h.setFormatter(logging.Formatter("%(message)s"))
    lg = logging.getLogger("sinama_audit")
    lg.setLevel(logging.INFO)
    if not lg.handlers:
        lg.addHandler(h)
    return lg


AUDIT = None


def audit_yaz(arac, arg, satir, sure_ms, hata):
    """Denetim satırı yazar: araç adı, argüman ANAHTARLARI (değerler asla
    yazılmaz — K17), satır sayısı, süre (ms), hata bayrağı. AUDIT None ise no-op.
    """
    if AUDIT is None:
        return
    AUDIT.info(json.dumps({
        "ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
        "oturum": OTURUM,
        "arac": arac,
        "arg_anahtarlari": sorted(arg.keys()),  # değerler YOK (PII koruması)
        "satir": satir,
        "sure_ms": round(sure_ms, 1),
        "hata": bool(hata),
    }, ensure_ascii=False))


GUVENLI_VARSAYILAN_ALANLAR = {"id", "tarih", "lat", "lon", "tur", "mahalle"}


PII_TOKENLARI = {"ad", "isim", "soyad", "tc", "kimlik", "telefon", "tel",
                 "adres", "eposta", "email", "dogum", "plaka", "pasaport",
                 "magdur", "fail", "sanik", "supheli", "sahis", "kisi",
                 "ehliyet"}


def pii_mi(alan):
    """Token/kelime-sınırı eşleşmesi: 'adet' artık yanlışlıkla yakalanmaz."""
    tokenlar = set(re.split(r"[_\s\-]+", alan.lower()))
    return bool(tokenlar & PII_TOKENLARI)


def kayitlari_kisitla(kayitlar, alanlar=None):
    """
    Kayıt listesini istemciye dönmeden önce sınırlar:
    - alanlar verilirse açık beyaz liste (çağıranın sorumluluğu)
    - verilmezse DEFAULT-DENY: güvenli çekirdek ∩ mevcut ∩ PII-değil
    """
    if alanlar:
        return [{a: k.get(a) for a in alanlar} for k in kayitlar]
    return [{a: v for a, v in k.items()
             if a in GUVENLI_VARSAYILAN_ALANLAR and not pii_mi(a)}
            for k in kayitlar]


def kayitlari_getir(arg):
    """Kayıtları csv_yolu veya satirlar üzerinden yükler + tiplendirir.
    Satır tavanı (MAKS_SATIR) kırparak uygulanır; son_okuma güncellenir.
    Args: arg (araç argümanları). Returns: tiplenmiş kayıt listesi.
    """
    ctx = baglam()
    key = ("kayitlar", id(arg))
    if ctx is not None and key in ctx['hazir']:
        return ctx['hazir'][key][1]
    if arg.get("csv_yolu"):
        sonuc = veri.tiplendir(veri.csv_yukle(arg["csv_yolu"]))
        if ctx is not None:
            ctx.update(satir=len(sonuc), kesildi=veri.son_okuma['kesildi'])
    elif arg.get("satirlar") is not None:
        s = arg["satirlar"]
        veri.son_okuma["kesildi"] = len(s) > veri.MAKS_SATIR
        veri.son_okuma["satir"] = min(len(s), veri.MAKS_SATIR)
        if ctx is not None:
            ctx.update(satir=min(len(s), veri.MAKS_SATIR), kesildi=len(s) > veri.MAKS_SATIR)
        sonuc = veri.tiplendir(s[:veri.MAKS_SATIR])
    else:
        raise KullanimHatasi("csv_yolu veya satirlar gerekli",
                             oneri="veri kökündeki bir CSV'nin yolunu verin "
                                   "veya kayıtları 'satirlar' dizisiyle gönderin")
    if ctx is not None:
        ctx['hazir'][key] = (arg, sonuc)
    return sonuc


def noktalari_getir(arg):
    """Kayıtlardan geçerli koordinat çiftlerini çıkarır.
    Args: arg (araç argümanları). Returns: [{lat, lon, ...}] nokta listesi.
    """
    kayitlar = kayitlari_getir(arg)
    pts = [veri.koordinat_al(k) for k in kayitlar]
    return [p for p in pts if p]


def quadratic_guard(pts_veya_kayitlar, arac_adi):
    """O(n^2) araçlarda compute-DoS koruması (Faz 1.1)."""
    n = len(pts_veya_kayitlar)
    if n > MAKS_QUADRATIC_N:
        raise KullanimHatasi(
            f"{arac_adi}: {n} kayıt bu aracın tavanını ({MAKS_QUADRATIC_N}) "
            "aşıyor",
            oneri="önce filtreleyin veya orneklem_cek ile örnekleyin")


def kapsam_uret(kayitlar, analize_giren, sebep):
    """Sessiz filtreleme yasağı: girdi_N → analize_giren_N → dışlanma."""
    return {"girdi_n": len(kayitlar), "analize_giren_n": analize_giren,
            "dislanan_n": len(kayitlar) - analize_giren,
            "dislanma_sebebi": sebep}


ARACLAR = {}


class AracSemaHatasi(KullanimHatasi):
    """İç içe araçta da JSON-RPC -32602'ye eşlenecek şema hatası."""


INSAN_ONAYI = frozenset()


ARAC_UYARILARI = {
    "grid_hotspot": ["geri-besleme uyarısı: devriye yoğunluğu veriyi, veri "
                     "devriyeyi besleyebilir; periyodik önyargı denetimi önerilir"],
    "kde_yogunluk": ["bant genişliği ve hücre boyutu sonucu değiştirir; "
                     "duyarlılık testi önerilir",
                     "equirectangular yaklaşım şehir ölçeği içindir; geniş "
                     "alan/yüksek enlemde yerel projeksiyon gerekir"],
    "nni": ["sınır kutusu alan tahmini sonucu etkiler; equirectangular "
            "yaklaşım şehir ölçeği içindir"],
    "risk_skorla": ["çıktı karar desteğidir, karar değildir; insan onayı "
                    "olmadan eyleme dönüştürülemez"],
    "suc_oranlari": ["ham oranları GA'sız karşılaştırmayın; küçük bölgeler "
                     "uçlarda görünebilir"],
    "knox_tablosu": ["sim>0 ile Monte Carlo p-değeri isteyin; gözlem tek "
                     "başına kanıt değildir"],
    "t_testi": ["normallik varsayar; şüphede welch=True veya mann_whitney"],
    "mann_whitney": ["n<20 ise p normal yaklaşımdır"],
    "anova": ["eşit varyans varsayar; şüphede kruskal_wallis"],
    "coklu_regresyon": ["ilişki analizidir; tek başına tekil karar girdisi yapılmamalıdır"],
    "lojistik_regresyon": ["odds oranı olasılık değildir; tek başına tekil karar girdisi yapılmamalıdır"],
    "guc_analizi": ["etki büyüklüğü abartılırsa çalışma yetersiz güçle kalır"],
    "zarar_hesapla": ["ağırlık tablosu jürisdiksyona özeldir; örnek tablo "
                      "üretimde kullanılmamalıdır (demokratik meşruiyet)"],
    "power_few": ["küçük birim listesi damgalama riski taşır; çıktı insan "
                  "denetiminde kullanılmalıdır"],
    "brifing_uret": ["belirsizlik notu zorunludur; ürün sınırlarını beyan "
                      "etmeden çıkamaz"],
    "risk_arazi": ["RTM risk faktörü türlerini sayar; çıktı olasılık değildir"],
    # A4.5 — LISA çoklu test düzeltmeli; güç sınırı BMK v1 K4.1'de ölçüldü.
    "yerel_kumeleme": ["karar çoklu test düzeltmelidir (FDR); kompakt tek hücrelik "
                       "yoğunlaşmayı güvenilir yakalamaz — sıcak nokta sorusu için "
                       "sicak_nokta_gi kullanın",
                       "coklu_test.duzeltmesiz_anlamli kanıt değildir, yalnız keşif "
                       "ipucudur"],
    # A4.2 — kişi/kayıt bağlantısı sınıfı: benzerlik ya da bağlantı KİMLİK değildir.
    "seri_eslestirme": ["dönen çiftler SERİ ADAYIDIR (inceleme hipotezi): MO "
                        "benzerliği aynı fail ya da kimlik anlamına gelmez; insan "
                        "incelemesi gerekir",
                        "benzerlik bu veri setindeki MO yaygınlığıyla ağırlıklıdır; "
                        "küçük veri setinde ağırlıklar kararsızdır"],
    "bulanik_eslesme": ["yazım benzerliği kimlik doğrulaması değildir; eşleşen "
                        "kayıtların aynı kişi olduğu insan incelemesiyle "
                        "doğrulanmalıdır"],
    "ag_analizi": ["merkezilik ya da bağlantı suçluluk göstergesi değildir; "
                   "ağ bir inceleme hipotezidir, fail/kimlik çıkarımı insan "
                   "incelemesi gerektirir"],
}


def arac(ad, aciklama, sema):
    """Araç kayıt dekoratörü: @arac(ad, aciklama, sema) fn'i ARACLAR'a işler.
    """
    def sar(fn):
        """Dekoratörün iç sarmalayıcısı: fn'i kaydeder ve değiştirmeden döner.
        """
        politika = ARAC_POLITIKALARI.get(ad)
        if politika is None:
            raise KullanimHatasi(f"politikasız araç kaydı reddedildi: {ad}")
        ARACLAR[ad] = {"fn": fn, "aciklama": aciklama, "sema": sema,
                       "politika": politika}
        return fn
    return sar


S_KAYIT = {
    "type": "object",
    "properties": {
        "csv_yolu": {"type": "string",
                     "description": "CSV yolu (izinli veri kökü içinde)"},
        "satirlar": {"type": "array", "items": {"type": "object"},
                    "description": "veya satır listesi (dict)"},
    },
}


ALANLAR_PROP = {"alanlar": {"type": "array",
                "description": "alan beyaz listesi (verilmezse güvenli çekirdek)"}}


def sema(extra=None, gerekli=None):
    """Paylaşılan kayıt-alanları şemasına ek özellik/gerekli alan ekler.
    Args: extra (özellik sözlüğü), gerekli (alan adları). Returns: JSON şema.
    """
    s = json.loads(json.dumps(S_KAYIT))
    if extra:
        s["properties"].update(extra)
    if gerekli:
        s["required"] = gerekli
    return s


ALAN = {"alan": {"type": "string"}}


def sayisal_vektor(degerler):
    """Metin/sayı karışık listeden float vektör (geçersizler atılır)."""
    out = []
    for v in degerler:
        try:
            out.append(_sonlu_sayi(v))
        except (TypeError, ValueError):
            continue
    return out


def grup_vektorleri(a):
    """{'gruplar': {ad: [...]}} veya csv+alan+grup_alan → {ad: [float...]}."""
    if a.get("gruplar"):
        return {g: sayisal_vektor(v) for g, v in a["gruplar"].items()}
    if a.get("csv_yolu") or a.get("satirlar"):
        k = kayitlari_getir(a)
        gruplar = {}
        for r in k:
            g = str(r.get(a["grup_alan"]))
            try:
                gruplar.setdefault(g, []).append(float(r.get(a["alan"])))
            except (TypeError, ValueError):
                continue
        return gruplar
    raise KullanimHatasi(
        "gruplar veya csv/satirlar + alan + grup_alan gerekli",
        oneri="'gruplar' nesnesi verin ya da alan + grup_alan belirtin")


def iki_vektor(a):
    """x/y inline veya csv+alan+grup_alan (2 grup) → (x, y)."""
    if a.get("x") is not None and a.get("y") is not None:
        if a.get("tip") == "bagimli":
            X, y = _tasarim_dogrula([[v] for v in a['x']], a['y'])
            return [row[0] for row in X], y
        return sayisal_vektor(a["x"]), sayisal_vektor(a["y"])
    if a.get("tip") == "bagimli":
        k = kayitlari_getir(a)
        gruplar = {}
        for r in k:
            gruplar.setdefault(str(r.get(a['grup_alan'])), []).append(r.get(a['alan']))
        if len(gruplar) != 2:
            raise VeriHatasi("bağımlı test için tam iki grup gerekli")
        x, y = [gruplar[g] for g in sorted(gruplar)]
        if len(x) != len(y):
            raise VeriHatasi("bağımlı grupların satır sayıları eşleşmeli")
        ciftler = []
        for v, w in zip(x, y):
            try:
                ciftler.append((_sonlu_sayi(v), _sonlu_sayi(w)))
            except VeriHatasi:
                continue
        return [v for v, w in ciftler], [w for v, w in ciftler]
    gruplar = grup_vektorleri(a)
    if len(gruplar) != 2:
        raise KullanimHatasi("tam 2 grup gerekli",
                             oneri="grup_alan değerlerini süzerek iki "
                                   "gruba indirin")
    adlar = sorted(gruplar.keys())
    return gruplar[adlar[0]], gruplar[adlar[1]]


SEMA_IKI = sema({"x": {"type": "array"}, "y": {"type": "array"},
                 "alan": {"type": "string"}, "grup_alan": {"type": "string"}})


SEMA_GRUP = sema({"gruplar": {"type": "object"},
                  "alan": {"type": "string"}, "grup_alan": {"type": "string"}})


def _matris_getir(a):
    """X/y inline veya csv + hedef + degiskenler → (X, y, adlar)."""
    return _reg_hazirla(a)[:3]


def _reg_hazirla(a, mekansal=False):
    """Tam kaydı atomik seçer; gate ve hesaplama aynı istekte girdiyi paylaşır."""
    ctx = baglam()
    key = (id(a), mekansal)
    if ctx is not None and key in ctx['hazir']:
        return ctx['hazir'][key][1]
    koord, sebepler = [], {}
    if 'X' in a:
        X, y = _tasarim_dogrula(a['X'], a.get('y'), a.get('degiskenler'))
        adlar = a.get('degiskenler') or [f'x{i+1}' for i in range(len(X[0]))]
        girdi_n = len(y)
    else:
        adlar = a.get('degiskenler')
        if not isinstance(adlar, list) or not adlar or any(not isinstance(g, str) for g in adlar):
            raise VeriHatasi('degiskenler: dolu alan adı listesi gerekli')
        if not isinstance(a.get('hedef'), str):
            raise VeriHatasi('hedef: alan adı gerekli')
        kayitlar = kayitlari_getir(a)
        girdi_n = len(kayitlar)
        X, y = [], []
        for r in kayitlar:
            try:
                xv = [_sonlu_sayi(r.get(g)) for g in adlar]
                yv = _sonlu_sayi(r.get(a['hedef']))
            except VeriHatasi:
                sebepler['gecersiz_sayi'] = sebepler.get('gecersiz_sayi', 0) + 1
                continue
            q = veri.koordinat_al(r) if mekansal else None
            if mekansal and q is None:
                sebepler['gecersiz_koordinat'] = sebepler.get('gecersiz_koordinat', 0) + 1
                continue
            X.append(xv)
            y.append(yv)
            if mekansal:
                koord.append(q)
        if not X:
            raise VeriHatasi('tam kayıt seçimi sonrası geçerli tasarım kalmadı')
    kapsam = {'girdi_n': girdi_n, 'analize_giren_n': len(y),
              'dislanan_n': girdi_n - len(y), 'dislanma_sebepleri': sebepler}
    sonuc = (X, y, adlar, koord, kapsam)
    if ctx is not None:
        ctx['hazir'][key] = (a, sonuc)
    return sonuc


SEMA_REG = sema({"X": {"type": "array", "minItems": 1,
                      "items": {"type": "array", "minItems": 1, "items": {"type": "number"}}},
                 "y": {"type": "array", "items": {"type": "number"}},
                 "hedef": {"type": "string"},
                 "degiskenler": {"type": "array", "minItems": 1, "items": {"type": "string"}}})


def _log_dir():
    return os.environ.get("SINAMA_LOG_DIR") or os.getcwd()


def _profil_kayit(a, sayisal_alan=None):
    k = kayitlari_getir(a)
    return veri.veri_profili(k, sayisal_alan=sayisal_alan), {}


def _g_bolge(a):
    k = kayitlari_getir(a)
    prof = veri.veri_profili(k)
    sayim = {}
    for r in k:
        b = str(r.get(a["bolge_alan"]))
        sayim[b] = sayim.get(b, 0) + 1
    degerler = list(sayim.values())
    if degerler:
        ort = sum(degerler) / len(degerler)
        var = sum((v - ort) ** 2 for v in degerler) / len(degerler)
        prof["dispersiyon_orani"] = round(var / ort, 3) if ort else None
    return prof, {"bolge_sayisi": len(sayim)}


def _g_benford(a):
    return _profil_kayit(a, sayisal_alan=a["alan"])


def _g_kikare(a):
    k = kayitlari_getir(a)
    av = sorted({str(r.get(a["a"])) for r in k})
    bv = sorted({str(r.get(a["b"])) for r in k})
    ai = {v: i for i, v in enumerate(av)}
    bi = {v: j for j, v in enumerate(bv)}
    tablo = [[0] * len(bv) for _ in av]
    for r in k:
        tablo[ai[str(r.get(a["a"]))]][bi[str(r.get(a["b"]))]] += 1
    n = len(k)
    rs = [sum(sat) for sat in tablo]
    cs = [sum(tablo[i][j] for i in range(len(av))) for j in range(len(bv))]
    beklenen = [rs[i] * cs[j] / n for i in range(len(av))
                for j in range(len(bv))] if n else []
    return {"n": n}, {"beklenen_hucreler": beklenen}


def _g_oran(a):
    bol = a.get("bolgeler", [])
    return {"n": len(bol)}, {"payda_var": all(b.get("nufus") for b in bol)}


def _g_n_ttest(a):
    if a["tip"] == "tek":
        x = sayisal_vektor(a.get("x") or
                           [r.get(a.get("alan")) for r in kayitlari_getir(a)])
        return {"n": len(x)}, {}
    x, y = iki_vektor(a)
    return {"n": len(x) + len(y)}, {}


def _g_n_iki(a):
    x, y = iki_vektor(a)
    return {"n": len(x) + len(y)}, {}


def _g_n_grup(a):
    gruplar = grup_vektorleri(a)
    return {"n": sum(len(v) for v in gruplar.values())}, {}


def _g_n_reg(a):
    _, y, _ = _matris_getir(a)
    return {"n": len(y)}, {}


def _g_dagilim(a):
    """dagilim_olculeri: nominal alanda sayısal özet yapısal reddedilir
    (kapi 'ozet' kuralı — v6.4'te ulaşılabilir kılındı)."""
    if a.get("degerler") is not None:
        return {"n": len(a["degerler"])}, {}
    k = kayitlari_getir(a)
    degerler = [r.get(a.get("alan")) for r in k]
    gecerli = [v for v in degerler if v is not None]
    if not gecerli:
        return {"n": len(k)}, {"olcum_duzeyi": "nominal"}
    sayisal = sum(1 for v in gecerli
                  if isinstance(veri.tip_tahmin(v), (int, float))
                  and not isinstance(veri.tip_tahmin(v), bool))
    duzey = "sayisal" if sayisal >= 0.8 * len(gecerli) else "nominal"
    return {"n": len(k)}, {"olcum_duzeyi": duzey}


def _g_zarar(a):
    k = kayitlari_getir(a)
    tur_alan = a.get("tur_alan", "tur")
    yol = (veri.guvenli_yol(a["agirlik_yolu"], izinli_uzantilar={".json"})
           if a.get("agirlik_yolu") else None)
    agirliklar = zarar.agirlik_tablosu_yukle(yol)
    kard = len({str(r.get(tur_alan)) for r in k})
    tt = zarar.zarar_tablosu(k, tur_alan, agirliklar, grup_alan=tur_alan)
    maks = max((e["pay"] for e in tt["gruplar"].values()), default=0)
    return veri.veri_profili(k), {"tur_kardinalite": kard, "maks_tur_pay": maks}


def _g_mekansal_regresyon(a):
    """03'ün tam-kayıt hazırlığını mekânsal gate ile ortak kullanır."""
    _, y, _, koord, kapsam = _reg_hazirla(a, mekansal=True)
    return {"n": len(y), "koordinat_gecerli_oran": 1.0 if y else 0.0,
            "koordinat_tek_nokta": len(set(koord)) <= 1}, kapsam


def _g_yukselen_sicak_nokta(a):
    """Yükselen hotspot için geçerli zaman+bölge satırlarını sayar."""
    kayitlar = kayitlari_getir(a)
    gecerli = [(r.get(a["bolge_alan"]), veri.tarih_coz(r.get(a["zaman_alan"])))
               for r in kayitlar]
    gecerli = [(b, t) for b, t in gecerli if b not in (None, "") and t is not None]
    gunler = {t.date() for _, t in gecerli}
    return {"n": len(gecerli), "zaman_kapsam": {"olayli_gun": len(gunler)}}, {
        "bolge_sayisi": len({str(b) for b, _ in gecerli})}


_GATE_KANCALARI = {
    "kde_yogunluk": ("kde_yogunluk", _profil_kayit),
    "grid_hotspot": ("grid_hotspot", _profil_kayit),
    "mekansal_kumelenme": ("grid_hotspot", _profil_kayit),
    "sicak_nokta_gi": ("grid_hotspot", _profil_kayit),
    "yerel_kumeleme": ("grid_hotspot", _profil_kayit),
    "nni": ("nni", _profil_kayit),
    "yakin_tekrar": ("yakin_tekrar", _profil_kayit),
    "knox_tablosu": ("knox_tablosu", _profil_kayit),
    "agirlikli_kde": ("kde_yogunluk", _profil_kayit),
    "trend": ("trend", _profil_kayit),
    "cusum": ("cusum", _profil_kayit),
    "kontrol_grafigi": ("kontrol_grafigi", _profil_kayit),
    "bolge_anomali": ("bolge_anomali", _g_bolge),
    "dagilim_olculeri": ("ozet", _g_dagilim),
    "benford": ("benford", _g_benford),
    "ki_kare_testi": ("ki_kare_testi", _g_kikare),
    "suc_oranlari": ("suc_oranlari", _g_oran),
    "t_testi": ("t_testi", _g_n_ttest),
    "mann_whitney": ("mann_whitney", _g_n_iki),
    "randomizasyon_testi": ("randomizasyon_testi", _g_n_iki),
    "anova": ("anova", _g_n_grup),
    "kruskal_wallis": ("kruskal_wallis", _g_n_grup),
    "coklu_regresyon": ("coklu_regresyon", _g_n_reg),
    "lojistik_regresyon": ("lojistik_regresyon", _g_n_reg),
    "zarar_hesapla": ("zarar_analizi", _g_zarar),
    "power_few": ("zarar_analizi", _g_zarar),
    "hacim_zarar_karsilastir": ("zarar_analizi", _g_zarar),
    "mekansal_regresyon": ("grid_hotspot", _g_mekansal_regresyon),
    "yukselen_sicak_nokta": ("yukselen_sicak_nokta", _g_yukselen_sicak_nokta),
}


def _politika(sinif, adlar, *, gate=None, insan_onayi=False,
              iz_zorunlu=False, veri_sinifi="islenmis",
              butce_turu="dogrusal", muafiyet=None):
    """Açık araç politikalarını tek kayıt kaynağında üretir."""
    if gate is None and not muafiyet:
        raise ValueError("gate veya muafiyet gerekçesi zorunlu")
    return {ad: {"sinif": sinif, "gate": gate,
                 "muafiyet_gerekcesi": muafiyet,
                 "insan_onayi": insan_onayi, "iz_zorunlu": iz_zorunlu,
                 "veri_sinifi": veri_sinifi, "butce_turu": butce_turu}
            for ad in adlar}


ARAC_POLITIKALARI = {}
ARAC_POLITIKALARI.update(_politika("veri_hazirlama", (
    "veri_ozeti", "saat_dagilimi", "gun_dagilimi", "ay_serisi", "aoristik",
    "analiz_oner", "teori_yorumu", "veri_kalitesi", "koordinat_maskele",
    "orneklem_cek", "bulanik_eslesme"),
    muafiyet="betimleyici/hazırlık işlemi; yöntem gate'i gerektirmez"))
ARAC_POLITIKALARI.update(_politika("analitik", (
    "frekans", "capraz_tablo", "trend", "grid_hotspot", "mekansal_kumelenme", "sicak_nokta_gi",
    "risk_arazi", "mekansal_regresyon", "cografi_profil", "yerel_kumeleme",
    "yukselen_sicak_nokta", "merkezsel_egilim", "gun_saat_analizi", "konsantrasyon_dagilimi",
    "esitlik_analizi", "oran_karsilastir", "mukerrer_magduriyet", "seri_eslestirme", "bolge_oran",
    "kde_yogunluk", "nni", "yakin_tekrar", "knox_tablosu",
    "kontrol_grafigi", "cusum", "bolge_anomali", "suc_oranlari", "ki_kare_testi",
    "pearson", "endeks_hesapla", "degerlendirme_did", "wdd_testi", "benford",
    "ag_analizi", "risk_skorla", "t_testi", "iki_oran_testi", "fisher_exact",
    "binomial_test", "mann_whitney", "anova", "kruskal_wallis", "spearman",
    "kendall", "phi", "randomizasyon_testi", "guc_analizi", "coklu_regresyon",
    "lojistik_regresyon", "dagilim_olculeri", "zarar_hesapla", "power_few",
    "hacim_zarar_karsilastir", "agirlikli_kde"),
    muafiyet="metodolojik gate için özel veri koşulu tanımlı değildir",
    iz_zorunlu=True))
ARAC_POLITIKALARI.update(_politika("surec", (
    "kanit_dogrula", "provenans_hazirlik", "provenans_dis_denetim",
    "provenans_ozet", "dongu_baslat", "dongu_veri", "dongu_analize_gec",
    "dongu_analiz", "dongu_sonuc", "dongu_izleme", "dongu_durum"),
    muafiyet="süreç yönetimi analiz hesabı değildir", veri_sinifi="oturum"))
ARAC_POLITIKALARI.update(_politika("raporlama", ("brifing_uret", "muhakeme_izi"),
    muafiyet="resmî çıktı oturum sağlığıyla doğrulanır", veri_sinifi="oturum"))

for _ad, _gate in _GATE_KANCALARI.items():
    ARAC_POLITIKALARI[_ad]["gate"] = _gate
    ARAC_POLITIKALARI[_ad]["muafiyet_gerekcesi"] = None
for _ad in ("risk_arazi", "cografi_profil"):
    ARAC_POLITIKALARI[_ad]["gate"] = ("grid_hotspot", _profil_kayit)
    ARAC_POLITIKALARI[_ad]["muafiyet_gerekcesi"] = None
for _ad in ("risk_arazi", "cografi_profil", "mekansal_regresyon",
            "yukselen_sicak_nokta", "yerel_kumeleme", "sicak_nokta_gi"):
    ARAC_POLITIKALARI[_ad]["insan_onayi"] = True
for _ad in ("risk_skorla", "bolge_anomali", "kontrol_grafigi", "cusum",
            "yakin_tekrar", "knox_tablosu", "nni", "kde_yogunluk",
            "grid_hotspot", "coklu_regresyon", "lojistik_regresyon", "power_few",
            "agirlikli_kde", "zarar_hesapla"):
    ARAC_POLITIKALARI[_ad]["insan_onayi"] = True
# A4.2 — kişi/kayıt bağlantısı iddiası taşıyabilen araçlar (BMK v0 K3.4)
for _ad in ("seri_eslestirme", "bulanik_eslesme", "ag_analizi"):
    ARAC_POLITIKALARI[_ad]["insan_onayi"] = True

# Dış importlar için uyumluluk görünümleri; bağımsız ikinci listeler değildir.
ARAC_GATE = {ad: p["gate"] for ad, p in ARAC_POLITIKALARI.items() if p["gate"]}
INSAN_ONAYI = frozenset(ad for ad, p in ARAC_POLITIKALARI.items()
                        if p["insan_onayi"])


def dispatch_gate(ad, arg):
    """
    Tek gate otoritesinin TEK uygulama noktası (birleşik yol haritası §4.2).
    Karar kalite.kapi'den gelir; uygun=False ise KapiRed fırlatılır.
    Uygun=True kararı (danışma sebepleriyle) döner — meta'ya işlenir.
    Gate'i olmayan araçlar (frekans, veri_kalitesi vb.) için None döner.
    """
    cfg = ARAC_GATE.get(ad)
    if not cfg:
        return None
    analiz_adi, kanca = cfg
    profil, baglam = kanca(arg)
    karar = _kapi(profil, analiz_adi, **baglam)
    karar["_profil"] = profil  # oturum=birim için (G3); meta'ya sızdırılmaz
    if not karar["uygun"]:
        raise KapiRed("fitness gate: " + "; ".join(karar["sebepler"]))
    return karar


def arac_yurut(ad, arg, *, sadece_analitik=False, hesap_oncesi=None):
    """Politika, şema, gate ve hesaplamayı tüm çağrı yollarında birleştirir.

    ``hesap_oncesi`` süreç fazı gibi kontrolleri gate/veri hazırlama ve
    hesaplamadan önce yapar. Dönen çalışma argümanı iç alan eklenmiş yerel
    kopyadır; istemcinin sözlüğü değiştirilmez.
    """
    if ad not in ARACLAR:
        raise KullanimHatasi(f"bilinmeyen araç: {ad}",
                             oneri="tools/list ile araç adlarını görün")
    kayit = ARACLAR[ad]
    politika = kayit.get("politika")
    if politika is None:
        raise KullanimHatasi(f"politikasız araç yürütülemez: {ad}")
    if sadece_analitik and politika["sinif"] != "analitik":
        raise KullanimHatasi(
            "yalnız analitik araçlar iç içe çağrılabilir",
            oneri="süreç ve raporlama araçları üst seviye çağrılmalıdır")
    calisma_arg = dict(arg)
    from .sema import sema_dogrula
    hata = sema_dogrula(ad, kayit["sema"], calisma_arg,
                        baglam()["uyarilar"] if baglam() is not None else None)
    if hata:
        raise AracSemaHatasi(hata)
    if hesap_oncesi is not None:
        hesap_oncesi()
    try:
        karar = dispatch_gate(ad, calisma_arg)
        calisma_arg["_gate_karar"] = karar
        return kayit["fn"](calisma_arg), karar, calisma_arg
    except KeyError as e:
        # Alternatif girdi kipli araçlar (x/y dizisi VEYA satirlar+alan;
        # guc_analizi tip=oran→p1/p2) şemada hiçbir alanı zorunlu tutamaz;
        # kipin gerektirdiği argüman eksikse adaptör a["alan"] ile KeyError
        # atıp çıplak 'sistem' hatası (HTTP köprüsünde 500) veriyordu.
        # YALNIZ şemada tanımlı ve çağrıda VERİLMEMİŞ bir argümanın
        # KeyError'ı kullanıcı hatasıdır; iç/veri KeyError'ları maskelenmez.
        eksik = e.args[0] if e.args else None
        if (isinstance(eksik, str) and eksik not in calisma_arg
                and eksik in kayit["sema"].get("properties", {})):
            raise KullanimHatasi(
                f"{ad}.{eksik}: bu çağrı kipinde zorunlu alan eksik",
                oneri="şemadaki girdi kiplerinden birini eksiksiz verin "
                      "(ör. x/y dizileri ya da satirlar + alan adları)") from None
        raise


def cevap(rid, result=None, error=None):
    """JSON-RPC 2.0 cevap zarfı kurar (result veya error).
    """
    m = {"jsonrpc": "2.0", "id": rid}
    if error is not None:
        m["error"] = error
    else:
        m["result"] = result
    return m


def meta_uret(ad):
    """{sonuc, meta} sözleşmesinin meta bloğunu üretir: araç, satır, kesildi,
    uyarilar (list), insan_onayi_gerekir bayrakları.
    """
    ctx = baglam() or {}
    return {"arac": ad,
            "satir": ctx.get("satir"),
            "kesildi": ctx.get("kesildi", False),
            "insan_onayi_gerekir": ad in INSAN_ONAYI,
            "uyarilar": list(ARAC_UYARILARI.get(ad, [])) + ctx.get('uyarilar', [])}
