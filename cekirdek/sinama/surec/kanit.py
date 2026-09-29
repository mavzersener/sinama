# -*- coding: utf-8 -*-
r"""
surec/kanit.py — birleşik kanıt mimarisi, Katman 1 (v6.2, G5/§4.4).

Üç katman, tek kaynak — çoğalma yok, katmanlanma var:

  Katman 1  OLAY AKIŞI (bu modül): oturum bazlı, değişmez (append-only)
            JSONL. Her analitik adım bir olaydır; PII DEĞERİ ASLA yazılmaz
            (yalnız argüman ANAHTARLARI + sayımlar).
  Katman 2  MANİFESTO (dongu.py): olay akışının anlamsal oturum görünümü
            (projeksiyon). dongu.kaydet her çağrıldığında yeni gecmiş
            adımları olay akışına delta olarak işlenir — akış kaynaktır,
            manifesto son durum görünümüdür.
  Katman 3  MUHAKEME İZİ (rapor.muhakeme_izi): manifestodaki ANALİZ
            adımlarının model-gerekçe katmanı; olgudan görsel olarak ayrı
            sunulur.

Not: sunucunun global audit.log'u (arayuz/ortak.py) GÜVENLİK/operasyon
kayıdıdır (kim, ne zaman, hangi araç — değersiz); bu modül ANALİTİK kanıt
zinciridir. İkisi farklı kaygılardır, örtüşmez.

Hash zinciri (tamper-evident bütünlük) UYGULANMIŞTIR (P2): her kayıt bir
önceki kaydın kanonik hash'ini 'onceki_hash' alanında taşır; bütünlük
dogrula() ile sınanır. (v6.9'a kadar bu paragraf "ertelendi" diyordu —
kod çoktan yapıyordu, belge yanıltıyordu.)

VERİ KİMLİĞİ (v6.9): dosya_kimligi() bir veri dosyasının SHA-256 özetini
ve boyutunu üretir; dongu.veri_bagla bunu manifestoya yazar. Böylece bir
oturumun HANGİ dosya içeriği üzerinde çalıştığı sonradan kanıtlanabilir.

Dayanıklılık (v6.5, H1): olay yazımı fsync ile kapanır; manifesto yazımı
ATOMIKTIR (temp + os.replace) — çökme ortasında yarım JSON kalmaz.
Kanıt kaybı asla sessiz değildir (DOKTRIN kural 22).
"""

import hashlib
import json
import math
import os
import re
import numbers
import tempfile
import time

from ..cekirdek.hatalar import GuvenlikHatasi, VeriHatasi


_OTURUM_ID = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")
_GUVENLI_SAYISAL_ALANLAR = frozenset({
    "n", "girdi_n", "kullanilan_n", "dislanan_n", "adet", "hucre",
    "nni", "p", "q", "oran", "egim", "istatistik", "z", "t",
    "df", "serbestlik", "gozlenen", "beklenen", "toplam",
})


def guvenli_ozet(sonuc):
    """Sonuçtan yalnız sabit anahtarlı sayısal olay özeti üretir.

    Olay akışı kişisel metin, dinamik grup adı veya ham sonucu taşımaz.
    Tanınmayan sonuçlar hata vermez; ``ozet_uretılemedi`` metadata'sına
    dönüşür. Böylece kanıt yazımı, bir ``str(sonuc)`` geri dönüş yoluyla
    hassas içerik sızdırmaz.
    """
    if not isinstance(sonuc, dict):
        return {"durum": "ozet_uretilemedi", "sayisal": {}}
    sayisal = {}
    for ad in _GUVENLI_SAYISAL_ALANLAR:
        deger = sonuc.get(ad)
        if (isinstance(deger, numbers.Real) and not isinstance(deger, bool)
                and math.isfinite(deger)):
            sayisal[ad] = deger
    if not sayisal and sonuc and all(
            isinstance(deger, numbers.Real) and not isinstance(deger, bool)
            and math.isfinite(deger) and deger >= 0
            for deger in sonuc.values()):
        # Frekans gibi dinamik grup→adet eşlemelerinde grup etiketleri
        # olay akışına giremez; yalnız toplam gözlem sayısı güvenlidir.
        sayisal["toplam"] = sum(sonuc.values())
    return {"durum": "ozet_uretildi" if sayisal else "ozet_uretilemedi",
            "sayisal": sayisal}


def gerekce_digest(gerekce):
    """Gizli manifesto gerekçesini kanonik SHA-256 commitment'a bağlar."""
    metin = json.dumps(gerekce, ensure_ascii=False, sort_keys=True,
                       separators=(",", ":"))
    return hashlib.sha256(metin.encode("utf-8")).hexdigest()


def gerekce_bagi_dogrula(manifesto, olaylar):
    """Manifestodaki gerekçe commitment'larının olay akışıyla bağını sınar."""
    adimlar = [a for a in manifesto.get("gecmis", [])
               if a.get("gerekce_digest")]
    baglar = [o for o in olaylar if o.get("gerekce_digest")]
    if len(adimlar) != len(baglar):
        return {"saglam": False, "neden": "gerekçe commitment sayısı uyuşmuyor"}
    for adim, olay in zip(adimlar, baglar):
        if (not isinstance(adim.get("gerekce"), dict)
                or gerekce_digest(adim["gerekce"]) != adim["gerekce_digest"]
                or olay["gerekce_digest"] != adim["gerekce_digest"]):
            return {"saglam": False, "neden": "gerekçe digest uyuşmuyor"}
    return {"saglam": True, "neden": None}


def _oturum_yolu(log_dir, oturum_id, uzanti, olustur=False):
    """Oturum kimliğiyle güvenli, sabit uzantılı dosya yolu üretir."""
    if not isinstance(oturum_id, str) or not _OTURUM_ID.fullmatch(oturum_id):
        raise GuvenlikHatasi("geçersiz oturum kimliği")
    if uzanti not in (".json", ".olaylar.jsonl"):
        raise GuvenlikHatasi("geçersiz oturum dosya türü")
    kok = os.path.realpath(log_dir)
    dizin = os.path.join(kok, "oturumlar")
    if os.path.lexists(dizin):
        gercek_dizin = os.path.realpath(dizin)
        try:
            ortak = os.path.commonpath([os.path.normcase(gercek_dizin),
                                        os.path.normcase(kok)])
        except ValueError:
            ortak = ""
        if (ortak != os.path.normcase(kok)
                or os.path.normcase(gercek_dizin) != os.path.normcase(dizin)):
            raise GuvenlikHatasi("oturum kökü güvenli değil")
        if not os.path.isdir(gercek_dizin):
            raise OSError("oturum dizini kullanılamıyor")
    elif olustur:
        os.makedirs(dizin, exist_ok=True)
        gercek_dizin = os.path.realpath(dizin)
    else:
        gercek_dizin = dizin
    yol = os.path.realpath(os.path.join(gercek_dizin, oturum_id + uzanti))
    try:
        ortak = os.path.commonpath([os.path.normcase(yol),
                                    os.path.normcase(gercek_dizin)])
    except ValueError:
        ortak = ""
    if ortak != os.path.normcase(gercek_dizin):
        raise GuvenlikHatasi("oturum yolu güvenli kökün dışında")
    return yol


def _simdi():
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _akis_yolu(log_dir, oturum_id, olustur=False):
    return _oturum_yolu(log_dir, oturum_id, ".olaylar.jsonl", olustur)


ZINCIR_SURUMU = 2


def _kanonik(govde):
    """Hash girdisi: anahtar sıralı JSON (yazımla aynı default=str)."""
    return json.dumps(govde, ensure_ascii=False, sort_keys=True, default=str)


def _kayit_hash(kayit):
    """Kaydın zincir hash'i (SHA-256).

    v2 (kayit["zincir"] == 2, v6.9+): onceki_hash DAHİL tüm kayıt. Geçmiş
    bir kaydı değiştirmek sonraki TÜM halkaların yeniden yazılmasını
    gerektirir ve zincir_son_hash değişir — dış çapaya bağlanabilir.

    v1 (eski akışlar): onceki_hash HARİÇ. GÜVENLİK AÇIĞIYDI (23 Eyl 2026):
    ortadaki bir kaydı değiştirip yalnız bir sonrakinin onceki_hash'ini
    güncellemek zinciri 'sağlam' bırakıyordu; baş ve son hash değişmiyordu,
    dış çapa bile yakalayamazdı. Yalnız eski akışları okumak için korunur;
    dogrula() bu kayıtları 'korumasiz_olay' olarak raporlar.
    """
    if kayit.get("zincir") == ZINCIR_SURUMU:
        return hashlib.sha256(_kanonik(kayit).encode("utf-8")).hexdigest()
    govde = {a: b for a, b in kayit.items() if a != "onceki_hash"}
    return hashlib.sha256(_kanonik(govde).encode("utf-8")).hexdigest()


def _son_hash(yol):
    """Akıştaki son kaydın hash'i; dosya yoksa None (zincir başı)."""
    if not os.path.isfile(yol):
        return None
    son = None
    with open(yol, encoding="utf-8") as f:
        for satir in f:
            if satir.strip():
                son = satir
    if son is None:
        return None
    return _kayit_hash(json.loads(son))


def dosya_kimligi(yol):
    """Veri dosyasının SHA-256 özeti ve boyutu.

    Dosya 64 KB'lık bloklar hâlinde okunur; büyük CSV'ler belleğe
    tümüyle alınmaz.

    Args:
        yol: okunacak dosyanın yolu.

    Returns:
        {'dosya_adi': ..., 'sha256': ..., 'boyut': ...} sözlüğü.
        dosya_adi yalnız taban addır; tam yol sızdırılmaz.

    Raises:
        VeriHatasi: dosya yoksa.
    """
    ad = os.path.basename(yol)
    if not os.path.isfile(yol):
        raise VeriHatasi(f"veri dosyası bulunamadı: {ad}",
                         oneri="dosya yolunu kontrol edin")
    h = hashlib.sha256()
    boyut = 0
    with open(yol, "rb") as f:
        for blok in iter(lambda: f.read(65536), b""):
            h.update(blok)
            boyut += len(blok)
    return {"dosya_adi": ad, "sha256": h.hexdigest(), "boyut": boyut}


def olay_yaz(log_dir, oturum_id, olay):
    """
    Değişmez olay akışına tek kayıt ekler (append-only).
    Kayıt BEYAZ LİSTEYLE kurulur (P06): yalnız 'olay', 'faz', guvenli_ozet()
    ile sabit adlı sayısal 'ozet' ve varsa 'gerekce_digest' yazılır; çağıranın
    gönderdiği diğer alanlar (ham özet, gerekçe metni, dinamik grup etiketi)
    akışa GİRMEZ — sözleşmeyi çağıran değil bu fonksiyon uygular. Gerekçenin
    kendisi yerel manifestoda kalır; akış yalnız SHA-256 taahhüdünü taşır
    (gerekce_bagi_dogrula).
    P2 + v2 (v6.9): her kayıt zincir sürümü ve onceki_hash ile zincirlenir;
    bağ alanı hash'e dahildir — kurcalama kanıtı kanit.dogrula ile sınanır.
    Dönüş: yazılan kayıt.
    """
    kayit = {"zaman": _simdi(), "surum": "b06",
             "olay": olay.get("olay", "bilinmeyen"),
             "faz": olay.get("faz", "BILINMEYEN"),
             "ozet": guvenli_ozet(olay.get("ozet"))}
    if isinstance(olay.get("gerekce_digest"), str):
        kayit["gerekce_digest"] = olay["gerekce_digest"]
    akis = _akis_yolu(log_dir, oturum_id, olustur=True)
    kayit["zincir"] = ZINCIR_SURUMU  # çağıran ezemez
    kayit["onceki_hash"] = _son_hash(akis)
    with open(akis, "a", encoding="utf-8") as f:
        f.write(json.dumps(kayit, ensure_ascii=False) + "\n")
        f.flush()
        os.fsync(f.fileno())  # H1.2: çökmede olay kaybolmasın
    return kayit


def atomik_json_yaz(yol, nesne):
    """
    H1.1: JSON'ı atomik yazar — aynı dizinde temp dosyaya yaz, fsync,
    os.replace. Çökme her noktada olursa olsun hedef ya ESKİ tam içeriği
    ya YENİ tam içeriği taşır; yarım dosya yapısal olarak imkânsızdır.
    """
    gecici = None
    try:
        with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=os.path.dirname(os.path.abspath(yol)),
                prefix=".oturum_", suffix=".tmp", delete=False) as f:
            gecici = f.name
            json.dump(nesne, f, ensure_ascii=False, indent=2, default=str)
            f.flush()
            os.fsync(f.fileno())
        os.replace(gecici, yol)
    finally:
        if gecici is not None and os.path.exists(gecici):
            os.unlink(gecici)


def _zincir_dogrula(olaylar):
    """
    P2: salt hash-zinciri bütünlüğü (olay listesi üzerinde). Her kaydın
    onceki_hash'i bir önceki kaydın zincir hash'ine eşit olmalı; ilk kayıt
    None taşımalı. v2 bir kez başladıysa sonrası v1 olamaz (sürüm düşürme
    saldırısı).

    Dönüş: {'saglam': bool, 'olay_sayisi': n, 'bozuk_adim': i|None,
            'zincir_bas_hash': ilk kaydın hash'i,
            'zincir_son_hash': son kaydın hash'i (dış çapa için),
            ['korumasiz_olay': v1 kayıt sayısı, 'uyari': ...]}
    Not: son kaydın kendisindeki değişiklik ancak zincir_son_hash dışarıda
    saklanıp karşılaştırılırsa saptanır (her hash zincirinin sınırı).
    """
    def _bozuk(i):
        """Bozuk zincir sonucu: hash'ler güvenilmez olduğu için None."""
        return {"saglam": False, "olay_sayisi": len(olaylar), "bozuk_adim": i,
                "zincir_bas_hash": None, "zincir_son_hash": None}

    onceki = None
    v2_basladi = False
    korumasiz = 0
    for i, o in enumerate(olaylar):
        surum = o.get("zincir")
        if surum == ZINCIR_SURUMU:
            v2_basladi = True
        elif v2_basladi or surum is not None:
            return _bozuk(i)  # v2'den sonra v1 ya da bilinmeyen sürüm
        else:
            korumasiz += 1
        if o.get("onceki_hash") != onceki:
            return _bozuk(i)
        onceki = _kayit_hash(o)
    sonuc = {"saglam": True, "olay_sayisi": len(olaylar), "bozuk_adim": None,
             "zincir_bas_hash": _kayit_hash(olaylar[0]) if olaylar else None,
             "zincir_son_hash": onceki}
    if korumasiz:
        sonuc["korumasiz_olay"] = korumasiz
        sonuc["uyari"] = (f"{korumasiz} olay eski (v1) biçimde: bağ alanı "
                          "hash'e dahil değil; bu kayıtlarda ortadaki bir "
                          "değişiklik saptanamaz")
    return sonuc


def dogrula(log_dir, oturum_id):
    """Hash zincirini ve mevcutsa manifesto gerekçe bağını birlikte sınar.

    Dönüş: _zincir_dogrula() sözlüğü + 'gerekce_bagi' ('manifesto_yok' |
    'dogrulandi' | 'gerekce_bagi_bozuk' | 'manifesto_gecersiz'). Bağ bozuksa
    'saglam' False olur; zincirin kendi alanları (zincir_son_hash dahil)
    zincir sağlamsa yine raporlanır.
    """
    olaylar = oku(log_dir, oturum_id)
    sonuc = _zincir_dogrula(olaylar)
    manifesto_yolu = _oturum_yolu(log_dir, oturum_id, ".json")
    bag_saglam, bag_durumu = True, "manifesto_yok"
    if os.path.isfile(manifesto_yolu):
        try:
            with open(manifesto_yolu, encoding="utf-8") as f:
                manifesto = json.load(f)
            bag_saglam = gerekce_bagi_dogrula(manifesto, olaylar)["saglam"]
            bag_durumu = "dogrulandi" if bag_saglam else "gerekce_bagi_bozuk"
        except (OSError, ValueError, json.JSONDecodeError):
            bag_saglam, bag_durumu = False, "manifesto_gecersiz"
    sonuc["saglam"] = sonuc["saglam"] and bag_saglam
    sonuc["gerekce_bagi"] = bag_durumu
    return sonuc


def oku(log_dir, oturum_id):
    """Oturumun olay akışını sırayla döner (yoksa boş liste)."""
    yol = _akis_yolu(log_dir, oturum_id)
    if not os.path.isfile(yol):
        return []
    with open(yol, encoding="utf-8") as f:
        return [json.loads(s) for s in f if s.strip()]


def projeksiyon(olaylar):
    """
    Katman 1 → Katman 2: olay akışından anlamsal oturum görünümü.
    Manifestonun gecmis'iyle birebir örtüşmelidir (tek-kaynak kanıtı:
    tests/test_kanit_muhakeme.py bunu doğrular).
    """
    adimlar = [{"zaman": o.get("zaman"), "faz": o.get("faz"),
                "arac": o.get("olay") or o.get("arac"),
                "ozet": o.get("ozet")} for o in olaylar]
    arac_sayilari = {}
    for a in adimlar:
        arac_sayilari[a["arac"]] = arac_sayilari.get(a["arac"], 0) + 1
    return {"adim_sayisi": len(adimlar),
            "faz_akisi": [a["faz"] for a in adimlar],
            "arac_sayilari": arac_sayilari,
            "adimlar": adimlar}
