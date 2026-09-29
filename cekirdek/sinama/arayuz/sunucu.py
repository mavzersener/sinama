# -*- coding: utf-8 -*-
r"""
arayuz/sunucu.py — İNCE transport: JSON-RPC 2.0 döngüsü + dispatch (v6.1).

Domain mantığı burada DEĞİLDİR (G1): araç tanımları araclar.py'de, ortak
servisler ortak.py'de, şema sema.py'de, gate kalite/kapi.py'de.

G3 (oturum = analizin birimi, §4.3): gate'li bir analiz aracı standalone
çağrıldığında bile arka planda minimal bir KEŞİF oturumu açılır — profil,
kapı kararı ve adım izi manifestoya düşer. Gate'siz/izsiz analiz yolu
yoktur; "karar döngüye girmeli" bir rica değil tek mümkün yoldur.
Tam PPDAC (onay + izleme) yalnız resmî döngü oturumlarında zorunludur.
"""

import json
import os
import sys
import time
import traceback

from . import araclar as _arac_kaydi  # noqa: F401 — araç kaydı yan etkisi
from .ortak import (ARACLAR, PROTOKOL, DESTEKLENEN_PROTOKOLLER, SURUM,
                    OTURUM, log, logger_kur, audit_kur, audit_yaz, cevap,
                    meta_uret, dispatch_gate, kayitlari_kisitla, pii_mi,
                    arac_yurut, AracSemaHatasi, _log_dir)
from .istek_baglam import yeni_baglam, baglam, baglam_bitir
from ..cekirdek import veri
from ..cekirdek.hatalar import SucAnaliziHatasi, KullanimHatasi, VeriHatasi
from ..kalite import KapiRed
from ..surec import dongu

# Geriye uyumluluk: testler/istemciler bu adları sunucu üzerinde arıyor.
# arac_calistir: MCP dışı gömülü çağıranların TEK kamusal giriş noktası.
__all__ = ["isle", "dogrula_kok", "main", "ARACLAR", "dispatch_gate",
           "kayitlari_kisitla", "pii_mi", "SURUM", "PROTOKOL",
           "arac_calistir"]


# ---------------- G3: oturum = analizin birimi ----------------

def _kesif_oturumu_ac(ad, karar):
    """Standalone analiz çağrısı için minimal keşif oturumu (izsiz yol yok)."""
    karar = dict(karar)
    karar.setdefault("kaynak", "dispatch_gate")
    d = dongu.AnalizDongusu(
        {"soran": "standalone", "karar": f"keşif: {ad}",
         "kapsam": "", "urun_turu": "taktik", "donem": ""},
        mod="kesif")
    d.planla()
    d.veri_bagla(karar.get("_profil") or {"n": karar.get("girdi_n", 0)},
                 uygunluk=karar)
    d.analize_gec(karar)
    return d


def _kesif_oturumu_kapat(d, ad, sonuc):
    """Adımı manifestoya işle ve kalıcılaştır; hata analizi DURDURMAZ."""
    try:
        d.analiz_kaydet(ad, sonuc)
        dongu.kaydet(d, _log_dir())
    except Exception as e:  # manifesto yazılamazsa analiz yine de döner
        log("KEŞİF OTURUMU yazılamadı:", type(e).__name__, str(e)[:120],
            seviye="ERROR")  # kanıt kaybı: en yüksek seviye
        return False
    return True


def _gate_meta(karar):
    """meta.gate: iç alanlar (_profil gibi) sızdırılmaz."""
    return {k: v for k, v in karar.items() if not k.startswith("_")}


# ---------------- H2: hata eşlemesi + dispatch boru hattı ----------------

def _hata_cevap(rid, tip, mesaj, oneri=None):
    """
    H2.1: yapısal hata cevabı. Format: 'HATA [tip]: mesaj' + varsa
    'ÖNERİ: ...' — istemci (yerel agent) hata TİPİNDEN düzeltici eylem
    seçebilir: veri→veri/yöntem değiştir, kullanim→argümanları düzelt,
    kapi→gate gerekçesine uy, guvenlik→kök içine taşı, dongu→faz sırasına
    dön, sistem→loga bak.
    """
    metin = f"HATA [{tip}]: {mesaj}"
    if oneri:
        metin += f"\nÖNERİ: {oneri}"
    return cevap(rid, {"content": [{"type": "text", "text": metin}],
                       "isError": True})


def _arac_yurut(ad, arg):
    """
    H2.2 boru hattı: gate → G3 keşif oturumu → araç → oturumu kapat.
    Döner: (sonuc, gate_karar, kanit_durumu). Hatalar çağırana yayılır;
    eşleme isle() içindedir.

    İstek bağlamı İSTER (isle() veya arac_calistir() kurar). Bağlamsız
    çağrı eskiden iz-zorunlu gate'siz araçlarda anlamsız bir
    AttributeError'la, diğerlerinde eksik metadatayla (satir/kesildi/
    uyarılar) SESSİZCE sonuçlanıyordu; artık sebebini söyleyerek durur.
    """
    if baglam() is None:
        raise RuntimeError(
            "istek bağlamı yok: _arac_yurut iç ayrıntıdır; gömülü "
            "çağıranlar sunucu.arac_calistir(ad, arg) kullanmalı")
    sonuc, gate_karar, _ = arac_yurut(ad, arg)
    politika = ARACLAR[ad]["politika"]
    iz_karari = gate_karar
    if politika["iz_zorunlu"] and iz_karari is None:
        n = baglam().get("satir") or 0
        iz_karari = {"uygun": True, "girdi_n": n,
                     "sebepler": [politika["muafiyet_gerekcesi"]],
                     "_profil": {"n": n}}
    oturum = _kesif_oturumu_ac(ad, iz_karari) if iz_karari else None
    kanit_durumu = None
    if oturum is not None:
        izlendi = _kesif_oturumu_kapat(oturum, ad, sonuc)
        kanit_durumu = "yazildi" if izlendi else "YAZILAMADI"
    return sonuc, gate_karar, kanit_durumu


def _basari_paketi(ad, sonuc, gate_karar, kanit_durumu):
    """{sonuc, meta} sözleşmesi; H1.3: kanıt kaybı meta'da GÜRÜLTÜLÜDÜR."""
    paket = {"sonuc": sonuc, "meta": meta_uret(ad)}
    if gate_karar:
        paket["meta"]["gate"] = _gate_meta(gate_karar)
        if gate_karar["sebepler"] != ["belirgin engel yok"]:
            paket["meta"]["uyarilar"] = (paket["meta"]["uyarilar"] +
                                         gate_karar["sebepler"])
    if kanit_durumu is not None:
        paket["meta"]["oturum_izlendi"] = kanit_durumu == "yazildi"
        if kanit_durumu == "YAZILAMADI":
            paket["meta"]["kanit_durumu"] = "YAZILAMADI"
            paket["meta"]["uyarilar"].insert(
                0, "KANIT KAYBI: adım olay akışına yazılamadı; bu sonuç "
                   "resmî delil olarak kullanılamaz — sunucu loguna bakın")
    return paket


def _paket_uret(ad, arg):
    """Aktif istek bağlamında aracı yürütür ve {sonuc, meta} paketini kurar.

    MCP (tools/call) ile gömülü yol (arac_calistir) AYNI fonksiyondan geçer;
    dongu_analiz'in iç içe gate kararı ve paket adı burada tek yerde çözülür.
    """
    sonuc, gate_karar, kanit_durumu = _arac_yurut(ad, arg)
    if ad == "dongu_analiz":
        gate_karar = baglam().pop("nested_gate", None)
        kanit_durumu = baglam().pop("nested_kanit_durumu", None)
    paket_ad = arg.get("arac", ad) if ad == "dongu_analiz" else ad
    return _basari_paketi(paket_ad, sonuc, gate_karar, kanit_durumu)


# ---------------- Gömülü kullanım: kamusal giriş noktası ----------------

def arac_calistir(ad, arg):
    """Tek aracı MCP tools/call ile BİREBİR aynı boru hattından geçirir.

    MCP dışındaki gömülü çağıranların (ör. DataFlow ml-service HTTP
    köprüsü, dışa aktarılan Python betikleri) kamusal sözleşmesi. İstek
    bağlamını kendisi kurar ve kapatır; satır/kesildi/uyarı metadatası,
    gate ile hesabın paylaştığı hazır girdi, keşif oturumu izi ve
    dongu_analiz'in iç içe gate kararı MCP yoluyla aynı üretilir. Denetim
    satırı (AUDIT kuruluysa) aynı biçimde yazılır.

    Args:
        ad: kayıtlı araç adı.
        arg: araç argümanları (dict; kopyalanır, çağıranınki değişmez).

    Returns:
        {"sonuc", "meta"} paketi — MCP istemcisinin gördüğüyle aynı, sonlu
        JSON'a normalize edilmiş (tuple→list, datetime→str).

    Raises:
        KullanimHatasi: bilinmeyen araç, dict olmayan argüman, şema ihlali
            (AracSemaHatasi) veya araç içinden çıplak ValueError.
        KapiRed: fitness gate reddi (tip='kapi').
        VeriHatasi: sonuç sonlu JSON olarak temsil edilemiyorsa.
        SucAnaliziHatasi: diğer tipli alan hataları (.tip taşır).
    """
    if not isinstance(ad, str) or ad not in ARACLAR:
        raise KullanimHatasi(f"bilinmeyen araç: {ad}",
                             oneri="tools/list ile araç adlarını görün")
    if not isinstance(arg, dict):
        raise KullanimHatasi("argümanlar dict (JSON nesnesi) olmalı")
    arg = dict(arg)
    token = yeni_baglam()
    baslangic = time.perf_counter()
    hata_oldu = True
    try:
        try:
            paket = _paket_uret(ad, arg)
        except SucAnaliziHatasi:
            raise
        except ValueError as e:
            # MCP yolu çıplak ValueError'ı 'kullanim' olarak eşler; aynısı.
            raise KullanimHatasi(str(e)) from e
        try:
            metin = json.dumps(paket, ensure_ascii=False, default=str,
                               allow_nan=False)
        except (ValueError, OverflowError):
            raise VeriHatasi("sonuç sonlu JSON olarak temsil edilemiyor") from None
        hata_oldu = False
        return json.loads(metin)
    finally:
        audit_yaz(ad, arg, baglam().get("satir"),
                  (time.perf_counter() - baslangic) * 1000, hata_oldu)
        baglam_bitir(token)


# ---------------- JSON-RPC döngüsü ----------------

def isle(mesaj):
    """İstek bağlamında mesaj işler; geçerli bildirimler yanıt üretmez."""
    if (not isinstance(mesaj, dict) or not isinstance(mesaj.get('method'), str) or
            mesaj.get('jsonrpc', '2.0') != '2.0' or
            not isinstance(mesaj.get('params', {}), dict)):
        return cevap(None, error={'code': -32600, 'message': 'geçersiz istek'})
    rid = mesaj.get('id')
    if rid is not None and (isinstance(rid, bool) or not isinstance(rid, (int, str))):
        return cevap(None, error={'code': -32600, 'message': 'geçersiz id'})
    token = yeni_baglam()
    try:
        sonuc = _isle(mesaj)
        return sonuc if 'id' in mesaj else None
    finally:
        baglam_bitir(token)


def _isle(mesaj):
    """Tek JSON-RPC mesajını işler ve cevap sözlüğü döner (test edilebilir
    çekirdek; I/O içermez). Yöntemler: initialize, tools/list, tools/call.
    """
    yontem = mesaj.get("method")
    rid = mesaj.get("id")
    params = mesaj.get("params") or {}

    if yontem == "initialize":
        # H6.2 protokol anlaşması: desteklenen sürümler beyan edilir;
        # bilinmeyen istemci sürümü reddedilmez, uyarıyla devam edilir
        sonuc = {"protocolVersion": PROTOKOL,
                 "capabilities": {"tools": {}},
                 "serverInfo": {"name": "sinama", "version": SURUM},
                 "desteklenenProtokoller": DESTEKLENEN_PROTOKOLLER}
        istemci_v = (params or {}).get("protocolVersion")
        if istemci_v and istemci_v not in DESTEKLENEN_PROTOKOLLER:
            sonuc["protokolUyari"] = (
                f"istemci protokolü ({istemci_v}) doğrulanan sürümlerde "
                f"yok; {PROTOKOL} ile devam ediliyor")
            log("PROTOKOL UYARISI:", istemci_v, seviye="WARNING")
        return cevap(rid, sonuc)
    if yontem == "ping":
        return cevap(rid, {})
    if yontem == "tools/list":
        return cevap(rid, {"tools": [
            {"name": ad, "description": t["aciklama"],
             "inputSchema": t["sema"]} for ad, t in ARACLAR.items()]})
    if yontem == "tools/call":
        ad = params.get("name")
        arg = params.get("arguments", {})
        if not isinstance(ad, str) or not isinstance(arg, dict):
            return cevap(rid, error={'code': -32602, 'message': 'name metin ve arguments nesne olmalı'})
        arg = dict(arg)
        baslangic = time.perf_counter()
        hata_oldu = False
        try:
            if ad not in ARACLAR:
                return cevap(rid, error={"code": -32602,
                                         "message": f"bilinmeyen araç: {ad}"})
            try:
                paket = _paket_uret(ad, arg)
            except AracSemaHatasi as e:
                hata_oldu = True
                return cevap(rid, error={"code": -32602, "message": str(e)})
            except KapiRed as e:
                hata_oldu = True
                log("KAPI REDDİ:", str(e))
                return _hata_cevap(rid, e.tip, str(e), e.oneri)
            except SucAnaliziHatasi as e:
                hata_oldu = True
                log(f"HATA [{e.tip}]:", str(e), seviye="WARNING")
                return _hata_cevap(rid, e.tip, str(e), e.oneri)
            except ValueError as e:
                hata_oldu = True
                log("DOĞRULAMA:", str(e))
                return _hata_cevap(rid, "kullanim", str(e))
            except Exception as e:
                hata_oldu = True
                log("ARAÇ HATASI:", traceback.format_exc(limit=5), seviye="ERROR")
                return _hata_cevap(rid, "sistem",
                                   f"{type(e).__name__} — işlem başarısız; "
                                   "ayrıntı sunucu logunda")
            try:
                metin = json.dumps(paket, ensure_ascii=False, default=str, allow_nan=False)
            except (ValueError, OverflowError):
                hata_oldu = True
                return _hata_cevap(rid, 'veri', 'sonuç sonlu JSON olarak temsil edilemiyor')
            return cevap(rid, {"content": [{"type": "text", "text": metin}],
                               "isError": False})
        finally:
            audit_yaz(ad, arg, baglam().get("satir"),
                      (time.perf_counter() - baslangic) * 1000, hata_oldu)
    if rid is not None:
        return cevap(rid, error={"code": -32601,
                                 "message": f"yöntem yok: {yontem}"})
    return None


def dogrula_kok():
    """Faz 0.2: kök doğrulama guard'ı — güvensiz yapılandırmada başlama."""
    if not os.environ.get("SINAMA_VERI_KOKU"):
        sys.exit("HATA: SINAMA_VERI_KOKU ayarlanmalı "
                 "(özel, dar kapsamlı veri dizini).")
    kok = veri.veri_koku()
    ev = os.path.realpath(os.path.expanduser("~"))
    yasak = {os.path.realpath(os.sep), ev}
    if kok in yasak or (ev + os.sep).startswith(kok + os.sep):
        sys.exit(f"HATA: veri kökü çok geniş ({kok}); dar bir alt dizin verin.")
    if not os.path.isdir(kok):
        sys.exit(f"HATA: veri kökü mevcut değil ({kok}).")
    return kok


def main():
    """Sunucu giriş noktası: veri kökü + loglama + audit kurulur, stdio
    JSON-RPC döngüsü sonsuz çalışır.
    """
    from . import ortak
    # Windows'ta ana süreç PYTHONUTF8 vermeden başlatırsa stdio cp1252 açılır
    # ve Türkçe karakterli ilk cevap UnicodeEncodeError ile süreci düşürür;
    # transport kendini UTF-8'e kilitler (host konsolundan bağımsız).
    for akis in (sys.stdin, sys.stdout, sys.stderr):
        if hasattr(akis, "reconfigure"):
            akis.reconfigure(encoding="utf-8")
    logger_kur()  # H5.1: seviyeli loglama açılışta kurulur
    kok = dogrula_kok()
    ortak.AUDIT = audit_kur()
    log(f"sinama MCP sunucusu v{SURUM} — {len(ARACLAR)} araç | "
        f"veri kökü: {kok} | oturum: {OTURUM}")
    try:
        tavan = int(os.environ.get('SINAMA_MAKS_ISTEK_BYTE', 8 * 1024 * 1024))
        if tavan <= 0:
            raise ValueError
    except ValueError:
        sys.exit('HATA: SINAMA_MAKS_ISTEK_BYTE pozitif tamsayı olmalı')
    for satir in _sinirli_satirlar(sys.stdin.buffer, tavan):
        mesaj = None
        try:
            if satir is None:
                c = cevap(None, error={'code': -32600, 'message': 'istek byte sınırı aşıldı'})
            elif not satir.strip():
                continue
            else:
                mesaj = json.loads(satir.decode('utf-8'), parse_constant=_gecersiz_sabit)
                c = isle(mesaj)
        except (ValueError, UnicodeError, RecursionError):
            c = cevap(None, error={'code': -32700, 'message': 'geçersiz JSON'})
        except Exception:
            log("GENEL HATA:", traceback.format_exc(limit=3), seviye="ERROR")
            c = cevap(mesaj.get("id") if isinstance(mesaj, dict) else None,
                      error={"code": -32603, "message": "iç hata"})
        if c is not None:
            sys.stdout.write(json.dumps(c, ensure_ascii=False, allow_nan=False) + "\n")
            sys.stdout.flush()


def _gecersiz_sabit(_):
    """JSON standardı dışındaki NaN/Infinity sabitlerini reddeder."""
    raise ValueError('sonlu JSON sayısı gerekli')


def _sinirli_satirlar(akis, tavan):
    """Byte sınırı aşılan satırı sınırlı parçalarla tüketir; satır başına tek hata."""
    while True:
        satir = akis.readline(tavan + 1)
        if not satir:
            return
        if len(satir) > tavan:
            while not satir.endswith(b'\n'):
                satir = akis.readline(min(tavan + 1, 65536))
                if not satir:
                    break
            yield None
        else:
            yield satir


if __name__ == "__main__":
    main()
