# -*- coding: utf-8 -*-
r"""
cekirdek/veri.py — CSV/TSV veri yükleme, tiplendirme, alan çözümleri.
Sadece standart kütüphane kullanır.

Güvenlik modeli: dosya erişimi kalite.guvenlik üzerinden izinli köke
kilitlidir (realpath çözülür, ".." kaçışları reddedilir). Geriye
uyumluluk: veri.guvenli_yol / veri.veri_koku / veri.veri_profili /
veri.analiz_uygun_mu adları buradan erişilebilir kalır (ince delegasyon).
"""

import csv
import re
import statistics
from datetime import datetime

from .guvenlik import (IZINLI_UZANTILAR, MAKS_DOSYA_MB,
                               guvenli_yol, veri_koku)

__all__ = ["MAKS_SATIR", "son_okuma", "tarih_coz", "tip_tahmin", "csv_yukle",
           "tiplendir", "eksik_raporu", "koordinat_al", "normalize_metin",
           "duplikat_isaretle", "guvenli_yol", "veri_koku",
           "veri_profili", "analiz_uygun_mu", "olay_dogrula"]

MAKS_SATIR = 200_000


son_okuma = {"kesildi": False, "satir": 0}


TARIH_FORMATLARI = [
    "%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M",  # ISO 8601 'T' ayraçlı (olay/1 kanonik biçimi)
    "%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d",
    "%d.%m.%Y %H:%M:%S", "%d.%m.%Y %H:%M", "%d.%m.%Y",
    "%d/%m/%Y %H:%M:%S", "%d/%m/%Y %H:%M", "%d/%m/%Y",
    "%Y/%m/%d %H:%M:%S", "%Y/%m/%d",
]


def tarih_coz(deger):
    """Metni datetime'a çevirir; başarısızsa None döner."""
    if isinstance(deger, datetime):
        return deger
    if deger is None:
        return None
    s = str(deger).strip()
    if not s:
        return None
    for fmt in TARIH_FORMATLARI:
        try:
            return datetime.strptime(s, fmt)
        except ValueError:
            continue
    return None


def _sayi_coz(s):
    r"""
    Katı sayı ayrıştırma:
    - Tam sayı: -?\d+
    - Ondalık nokta: -?\d+.\d+
    - Türkçe ondalık virgül: -?\d+,\d{1,2}  (ör. '12,5')
    '1,234' (İng. binlik) gibi biçimler SAYI SAYILMAZ — sessiz veri
    bozulmasını önler.
    """
    if re.fullmatch(r"-?\d+", s):
        try:
            return int(s)
        except ValueError:
            return None
    if re.fullmatch(r"-?\d+\.\d+", s):
        return float(s)
    if re.fullmatch(r"-?\d+,\d{1,2}", s):
        return float(s.replace(",", "."))
    return None


def tip_tahmin(deger):
    """Metin değeri int/float/datetime/str olarak tiplendirir."""
    if deger is None:
        return None
    s = str(deger).strip()
    if s == "":
        return None
    t = tarih_coz(s)
    if t is not None:
        return t
    n = _sayi_coz(s)
    if n is not None:
        return n
    return s


def csv_yukle(yol, ayirac=None, kodlama="utf-8-sig", maks_satir=None, kok=None):
    """
    CSV/TSV dosyasını sözlük listesi olarak yükler.
    Güvenlik: yol guvenli_yol'dan geçer; maks_satir aşılırsa kesilir ve
    veri.son_okuma["kesildi"] True olur.
    """
    maks_satir = maks_satir or MAKS_SATIR
    guvenli = guvenli_yol(yol, kok)
    son_okuma["kesildi"] = False
    son_okuma["satir"] = 0
    with open(guvenli, "r", encoding=kodlama, newline="") as f:
        ornek = f.read(4096)
        f.seek(0)
        if ayirac is None:
            try:
                ayirac = csv.Sniffer().sniff(ornek, delimiters=",;\t|").delimiter
            except csv.Error:
                ayirac = ","
        okuyucu = csv.DictReader(f, delimiter=ayirac)
        kayitlar = []
        for satir in okuyucu:
            kayitlar.append({(k or "").strip(): v for k, v in satir.items()})
            if len(kayitlar) >= maks_satir:
                son_okuma["kesildi"] = True
                break
    son_okuma["satir"] = len(kayitlar)
    return kayitlar


def tiplendir(kayitlar, alanlar=None):
    """Seçilen alanları (None ise tümü) tip_tahmin ile dönüştürür."""
    sonuc = []
    for k in kayitlar:
        yeni = dict(k)
        hedef = alanlar if alanlar else list(k.keys())
        for a in hedef:
            if a in yeni:
                yeni[a] = tip_tahmin(yeni[a])
        sonuc.append(yeni)
    return sonuc


def eksik_raporu(kayitlar):
    """Her alan için eksik (None/boş) kayıt sayısını verir."""
    if not kayitlar:
        return {}
    rapor = {a: 0 for a in kayitlar[0].keys()}
    for k in kayitlar:
        for a in rapor:
            v = k.get(a)
            if v is None or str(v).strip() == "":
                rapor[a] += 1
    return rapor


def koordinat_al(kayit, lat_alan="lat", lon_alan="lon"):
    """Kayıttan (lat, lon) çiftini float olarak alır; yoksa None."""
    try:
        lat = float(str(kayit.get(lat_alan)).replace(",", "."))
        lon = float(str(kayit.get(lon_alan)).replace(",", "."))
        if not (-90 <= lat <= 90 and -180 <= lon <= 180):
            return None
        return (lat, lon)
    except (TypeError, ValueError):
        return None


def normalize_metin(s):
    """Bulanık eşleşme öncesi basit normalizasyon."""
    if s is None:
        return ""
    return re.sub(r"\s+", " ", str(s).strip().lower())


def duplikat_isaretle(kayitlar):
    """
    Tahribatsızlık ilkesi: hiçbir kayıt SİLİNMEZ; tam-duplikat satırlar
    '_duplikat': True ile işaretlenir. Kaldırma kararı insan onayındadır.
    Dönüş: {'kayitlar': [...], 'duplikat_sayisi': n}
    """
    goruldu, sonuc, sayi = set(), [], 0
    for r in kayitlar:
        imza = tuple(sorted((k, str(v)) for k, v in r.items()))
        yeni = dict(r)
        if imza in goruldu:
            yeni["_duplikat"] = True
            sayi += 1
        else:
            goruldu.add(imza)
        sonuc.append(yeni)
    return {"kayitlar": sonuc, "duplikat_sayisi": sayi}

def veri_profili(*a, **k):
    """GERİYE UYUMLULUK: otorite kalite.profil.veri_profili'dir (v6.1)."""
    from ..kalite.profil import veri_profili as _vp
    return _vp(*a, **k)


def analiz_uygun_mu(profil, analiz, **baglam):
    """
    GERİYE UYUMLULUK sarmalayıcısı (v6.0+): tek fitness-gate otoritesi
    kalite.kapi'ye delege eder. Yeni gate kuralı buraya DEĞİL,
    kalite/kapi.py'ye yazılır (birleşik yol haritası §4.2, G2).
    """
    from ..kalite.kapi import kapi
    return kapi(profil, analiz, **baglam)


def olay_dogrula(kayitlar, maks_hata_ornegi=20):
    """
    olay/1 ortak olay şeması doğrulaması. Kayıtların zorunlu alanlarını,
    tiplendirme kurallarını ve mantıksal kısıtlamalarını denetler.

    Şema kuralları:
    - olay_id: boş olmayan str, TÜM kayıtlarda benzersiz
    - zaman: tarih_coz ile çözülebilir tarih/saat
    - tur: boş olmayan str
    - Mekân: (lat, lon) koordinat çifti VEYA boş olmayan grid_id
    - guvenilirlik (opsiyonel): 0-1 aralığında sayı
    - zarar (opsiyonel): >= 0 sayı
    - zaman_bitis (opsiyonel): tarih_coz ile çözülebilir ve zaman >= zaman_bitis

    Args:
        kayitlar: Doğrulanacak kayıt sözlükleri listesi
        maks_hata_ornegi: Raporlanan hata örneği sayısı (varsayılan: 20)

    Returns:
        dict: {
            "gecerli": bool (hata yoksa True),
            "hatalar": [str] (satır indeksli hata mesajları),
            "uyarilar": [str] (uyarı mesajları),
            "doluluk": {
                "olay_id": 0-1,
                "zaman": 0-1,
                "zaman_bitis": 0-1,
                "tur": 0-1,
                "lat": 0-1,
                "lon": 0-1,
                "grid_id": 0-1,
                "guvenilirlik": 0-1,
                "zarar": 0-1,
                "not_metni": 0-1
            },
            "kayit_sayisi": int,
            "sema": "olay/1"
        }
    """
    hatalar = []
    uyarilar = []

    # Boş liste kontrolü
    if not kayitlar:
        return {
            "gecerli": False,
            "hatalar": ["kayıt yok"],
            "uyarilar": [],
            "doluluk": {},
            "kayit_sayisi": 0,
            "sema": "olay/1"
        }

    # Olay ID'leri benzersizlik kontrolü
    olay_idleri = set()
    tekrarlanan_idler = []
    for satir_idx, kayit in enumerate(kayitlar):
        olay_id = kayit.get("olay_id", "")
        if not olay_id or str(olay_id).strip() == "":
            hatalar.append(f"satır {satir_idx}: olay_id boş")
        elif str(olay_id) in olay_idleri:
            if str(olay_id) not in tekrarlanan_idler:
                hatalar.append(f"satır {satir_idx}: olay_id '{olay_id}' tekrarlanıyor")
                tekrarlanan_idler.append(str(olay_id))
        else:
            olay_idleri.add(str(olay_id))

    # Zorunlu alanlar ve mekân kontrolü
    for satir_idx, kayit in enumerate(kayitlar):
        # zaman
        zaman_val = kayit.get("zaman")
        zaman_resolved = tarih_coz(zaman_val) if zaman_val else None
        if not zaman_resolved:
            hatalar.append(f"satır {satir_idx}: zaman çözülemiyor veya boş")

        # tur
        tur = kayit.get("tur", "")
        if not tur or str(tur).strip() == "":
            hatalar.append(f"satır {satir_idx}: tur boş")

        # Mekân kontrolü: (lat, lon) VEYA grid_id
        koordinat = koordinat_al(kayit)
        grid_id = kayit.get("grid_id", "")
        if not koordinat and (not grid_id or str(grid_id).strip() == ""):
            hatalar.append(f"satır {satir_idx}: geçerli koordinat veya grid_id yok")

        # guvenilirlik (opsiyonel)
        guvenilirlik = kayit.get("guvenilirlik")
        if guvenilirlik is not None and str(guvenilirlik).strip() != "":
            try:
                g_float = float(str(guvenilirlik).replace(",", "."))
                if not (0 <= g_float <= 1):
                    hatalar.append(f"satır {satir_idx}: guvenilirlik aralık dışı [{g_float}]")
            except ValueError:
                hatalar.append(f"satır {satir_idx}: guvenilirlik sayıya çevrilemez")

        # zarar (opsiyonel)
        zarar = kayit.get("zarar")
        if zarar is not None and str(zarar).strip() != "":
            try:
                z_float = float(str(zarar).replace(",", "."))
                if z_float < 0:
                    hatalar.append(f"satır {satir_idx}: zarar negatif [{z_float}]")
            except ValueError:
                hatalar.append(f"satır {satir_idx}: zarar sayıya çevrilemez")

        # zaman_bitis (opsiyonel)
        zaman_bitis = kayit.get("zaman_bitis")
        if zaman_bitis is not None and str(zaman_bitis).strip() != "":
            zaman_bitis_resolved = tarih_coz(zaman_bitis)
            if not zaman_bitis_resolved:
                hatalar.append(f"satır {satir_idx}: zaman_bitis çözülemiyor")
            elif zaman_resolved and zaman_bitis_resolved < zaman_resolved:
                hatalar.append(f"satır {satir_idx}: zaman_bitis zaman'dan önce")

    # Doluluk oranları hesapla
    doluluk = {}
    alanlar_kontrol = ["olay_id", "zaman", "zaman_bitis", "tur", "lat", "lon",
                       "grid_id", "guvenilirlik", "zarar", "not_metni"]

    for alan in alanlar_kontrol:
        dolu_sayi = 0
        for kayit in kayitlar:
            val = kayit.get(alan)
            if val is not None and str(val).strip() != "":
                dolu_sayi += 1
        doluluk[alan] = round(dolu_sayi / len(kayitlar), 2) if kayitlar else 0

    # Hata sayısı kırpması
    hatalar_gosterilecek = hatalar[:maks_hata_ornegi]
    kalanlar = len(hatalar) - len(hatalar_gosterilecek)
    if kalanlar > 0:
        hatalar_gosterilecek.append(f"... ve {kalanlar} hata daha")

    gecerli = len(hatalar) == 0

    return {
        "gecerli": gecerli,
        "hatalar": hatalar_gosterilecek,
        "uyarilar": uyarilar,
        "doluluk": doluluk,
        "kayit_sayisi": len(kayitlar),
        "sema": "olay/1"
    }
