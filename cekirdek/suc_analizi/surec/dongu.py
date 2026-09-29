# -*- coding: utf-8 -*-
"""
dongu.py — Analiz Döngüsü Motoru (PPDAC).
The Crime Analyst's Companion'daki ortak süreç modeli:
PROBLEM → PLAN → VERİ → ANALİZ → SONUÇ → (İZLEME ile yeni döngü).
SARA bu döngünün polislik özelindeki karşılığıdır; 3T (Targeting-Testing-
Tracking) döngünün operasyonel ritmidir.

Mimari ilkeler:
- Döngü bir DURUM MAKİNESİDİR: geçişler doğrulanır, faz atlanamaz.
- Her fazın kapısı vardır: VERİ→ANALİZ geçişinde veri_kalitesi + fitness
  gate ZORUNLU; SONUÇ fazında insan onayı ZORUNLU.
- Her oturum bir MANİFESTO üretir (talep, geçmiş, kalite, onaylar,
  izleme planı) — audit'in semantik katmanı, "analysing yourself".
- Oturumlar JSON dosyasında kalıcıdır (log dizini/oturumlar/).
"""

import json
import os
import time
import uuid

from ..cekirdek.hatalar import SucAnaliziHatasi
from . import kanit, kilit

FAZ_SIRASI = ["PROBLEM", "PLAN", "VERI", "ANALIZ", "SONUC"]

# Faz başına izinli analiz araçları (doktrin: faz disiplini)
FAZ_ARACLARI = {
    "VERI": ["veri_kalitesi", "veri_ozeti"],
    "ANALIZ": None,  # None = tüm analiz araçları (gate ayrıca korur)
    "SONUC": ["brifing_uret"],
}

# Ürün türüne göre önerilen araç dizisi (Ch 17 Stratified Analysis Model:
# rütbeye/kapsama göre ürün farklılaşır)
PLAN_SABLONLARI = {
    "taktik": {
        "hedef_kitle": "saha personeli / karakol amiri (olay düzeyi, günlük)",
        "onerilen": ["veri_kalitesi", "grid_hotspot", "gun_saat_analizi",
                     "yakin_tekrar", "mukerrer_magduriyet", "power_few",
                     "brifing_uret"],
        "not": "kısa vadeli desenler; devriye görevlendirmesine yönelik"},
    "stratejik": {
        "hedef_kitle": "komuta kademesi (bölge düzeyi, dönemsel)",
        "onerilen": ["veri_kalitesi", "ay_serisi", "trend", "suc_oranlari",
                     "bolge_anomali", "hacim_zarar_karsilastir",
                     "degerlendirme_did", "guc_analizi", "brifing_uret"],
        "not": "uzun vadeli eğilimler; kaynak tahsisi ve politika"},
    "sorun_cozme": {
        "hedef_kitle": "problem yönelimli ekip (SARA tam döngü)",
        "onerilen": ["veri_kalitesi", "frekans", "grid_hotspot",
                     "gun_saat_analizi", "seri_eslestirme", "ag_analizi",
                     "degerlendirme_did", "brifing_uret"],
        "not": "kurban-fail-yer üçgeni; müdahale tasarımı + değerlendirme"},
}

SONUC_TURLERI = ["sorun_dogrulandi", "sorun_reddedildi", "izlemeye_alindi",
                 "mudahale_onerildi"]

# Yapılandırılmış gerekçe (Faz 1.6 / §4.5): her ANALİZ adımında zorunlu
# alanlar. cikarim ve alternatifler önerilir (zorunlu değil).
GEREKCE_ZORUNLU = {"hipotez", "yorum"}

# Kanıt gücü notları (EBP hiyerarşisi, Maryland ölçeği mantığı)
KANIT_GUCU = {
    "degerlendirme_did": "orta-güçlü (kontrol gruplu yarı-deney)",
    "oncesi_sonrasi": "zayıf (kontrolsüz; tarihsel etkenler dışlanamaz)",
    "kesinti_analizi": "orta (kesintili zaman serisi)",
    "randomizasyon_testi": "güçlü (varsayımsız çıkarım)",
}


def _simdi():
    return time.strftime("%Y-%m-%dT%H:%M:%S")


class DonguHatasi(SucAnaliziHatasi):
    """PPDAC durum makinesi ihlali (faz atlama, gerekçesiz adım vb.)."""
    tip = "dongu"


class AnalizDongusu:
    """
    Tek bir analiz oturumunun PPDAC durum makinesi + manifestosu.
    mod="resmi": tam PPDAC (onay + izleme zorunlu).
    mod="kesif": standalone araç çağrısının minimal oturumu (v6.1, G3) —
    onay/izleme istenmez ama profil + gate kararı + adım izi YİNE tutulur;
    gate'siz/izsiz analiz yolu yoktur.
    """

    def __init__(self, talep, oturum_id=None, mod="resmi",
                 amac="operasyonel"):
        if amac not in kilit.AMACLAR:
            raise DonguHatasi(f"amac şunlardan biri olmalı: {kilit.AMACLAR}")
        self.manifesto = {
            "oturum_id": oturum_id or uuid.uuid4().hex[:10],
            "olusturma": _simdi(),
            "mod": mod,
            "amac": amac,            # operasyonel | dogrulayici | kesifsel
            "kilit": None,           # protokol ön-kaydı — v6.9
            "faz": "PROBLEM",
            "talep": talep,          # {soran, karar, kapsam, urun_turu, donem}
            "plan": None,
            "veri_kalitesi": None,
            "veri_kimligi": None,   # {dosya_adi, sha256, boyut} — v6.9
            "hazirlik_beyani": None,  # veri pakete girmeden önceki adımlar
            "dis_denetimler": [],     # dış sistemlerin audit sonuçları
            "gate_kararlari": [],
            "gecmis": [],            # [{zaman, faz, arac, ozet}]
            "insan_onaylari": [],
            "sonuc": None,
            "izleme": None,
        }

    # --- yardımcılar ---
    def _gecis_kontrol(self, hedef):
        mevcut = FAZ_SIRASI.index(self.manifesto["faz"])
        if FAZ_SIRASI.index(hedef) != mevcut + 1:
            raise DonguHatasi(
                f"faz atlanamaz: {self.manifesto['faz']} → {hedef}; "
                f"sıradaki faz: {FAZ_SIRASI[mevcut + 1] if mevcut + 1 < len(FAZ_SIRASI) else 'yok'}")

    def _kaydet(self, arac, ozet, gerekce=None):
        adim = {"zaman": _simdi(), "faz": self.manifesto["faz"],
                "arac": arac, "ozet": str(ozet)[:500]}
        if gerekce is not None:
            gecersiz = GEREKCE_ZORUNLU - set(gerekce)
            if gecersiz:
                raise DonguHatasi(
                    f"gerekçe eksik alan: {sorted(gecersiz)}; "
                    f"zorunlu: {sorted(GEREKCE_ZORUNLU)}")
            adim["gerekce"] = dict(gerekce)
        self.manifesto["gecmis"].append(adim)

    # --- faz geçişleri ---
    def planla(self):
        """PROBLEM → PLAN: ürün türüne göre araç planı önerilir."""
        self._gecis_kontrol("PLAN")
        urun = self.manifesto["talep"].get("urun_turu", "taktik")
        sablon = PLAN_SABLONLARI.get(urun, PLAN_SABLONLARI["taktik"])
        self.manifesto["plan"] = {"urun_turu": urun, **sablon}
        self.manifesto["faz"] = "PLAN"
        self._kaydet("planla", sablon["onerilen"])
        return self.manifesto["plan"]

    def protokol_kilitle(self, hipotez, onaylayan):
        """PLAN fazında protokolü dondurur (ön-kayıt).

        Kilit olayı analiz adımlarıyla AYNI kanıt zincirine yazılır;
        böylece "kilitten önce analiz yapılmadı" iddiası zincirden
        okunabilir hâle gelir (bkz. surec/kilit.py).

        Args:
            hipotez: veriye bakılmadan yazılmış hipotez.
            onaylayan: kilidi alan araştırmacı.

        Returns:
            Kilit kaydı ({'zaman', 'onaylayan', 'hipotez', 'hash'}).
        """
        kayit = kilit.kilitle(self.manifesto, hipotez, onaylayan)
        self.manifesto["kilit"] = kayit
        self._kaydet("protokol_kilitle", {"hash": kayit["hash"],
                                          "onaylayan": onaylayan})
        return kayit

    def onkayit_dogrula(self, olaylar=None):
        """Ön-kayıt bütünlüğü ve sırası (kilit.dogrula sarmalayıcısı).

        Args:
            olaylar: kanıt zinciri olayları; verilmezse manifesto geçmişi.

        Returns:
            kilit.dogrula() çıktısı.
        """
        return kilit.dogrula(self.manifesto, olaylar)

    def veri_bagla(self, profil, uygunluk=None, veri_yolu=None):
        """
        PLAN → VERİ: veri_kalitesi çıktısı kaydedilir. Fitness gate
        'uygun değil' derse döngü ANALİZ'e geçemez (kapı).

        veri_yolu verilirse dosyanın SHA-256 kimliği manifestoya yazılır
        (v6.9): oturumun hangi dosya İÇERİĞİ üzerinde çalıştığı sonradan
        kanıtlanabilir olur. Verilmezse alan None kalır — mevcut çağrılar
        aynen çalışmayı sürdürür.

        Args:
            profil: veri_kalitesi çıktısı.
            uygunluk: fitness gate kararı (opsiyonel).
            veri_yolu: bağlanan veri dosyasının yolu (opsiyonel).

        Returns:
            Faz bilgisi ve kapı hatırlatması taşıyan sözlük.
        """
        self._gecis_kontrol("VERI")
        # Doğrulayıcı çalışmada kilit veriden ÖNCE alınmış olmalıdır;
        # sonradan alınan kilit ön-kayıt değil, ön-kayıt tiyatrosudur.
        if self.manifesto.get("amac") == "dogrulayici" and \
                not self.manifesto.get("kilit"):
            raise kilit.KilitHatasi(
                "doğrulayıcı çalışmada veri, protokol kilitlenmeden "
                "bağlanamaz",
                oneri="önce protokol_kilitle(hipotez, onaylayan) çağırın; "
                      "hipotezi sonradan yazacaksanız amac='kesifsel' seçin")
        self.manifesto["veri_kalitesi"] = profil
        ozet = {"n": profil.get("n"), "uyarilar": profil.get("uyarilar")}
        if veri_yolu is not None:
            kimlik = kanit.dosya_kimligi(veri_yolu)
            self.manifesto["veri_kimligi"] = kimlik
            ozet["sha256"] = kimlik["sha256"]
        if uygunluk:
            self.manifesto["gate_kararlari"].append(
                {"faz": "VERI-kapi", **uygunluk})
        self.manifesto["faz"] = "VERI"
        self._kaydet("veri_bagla", ozet)
        return {"faz": "VERI", "kapi": "analiz oncesi fitness gate zorunlu"}

    def analize_gec(self, uygunluk):
        """VERİ → ANALİZ: fitness gate kontrolü (ZORUNLU KAPI)."""
        self._gecis_kontrol("ANALIZ")
        if not uygunluk.get("uygun", False):
            raise DonguHatasi(
                "fitness gate reddetti: " + "; ".join(uygunluk.get("sebepler", [])))
        self.manifesto["gate_kararlari"].append(
            {"faz": "ANALIZ", **uygunluk})
        self.manifesto["faz"] = "ANALIZ"
        self._kaydet("analize_gec", uygunluk)
        return {"faz": "ANALIZ"}

    def analiz_kaydet(self, arac, ozet, gerekce=None):
        """
        ANALİZ fazında çalıştırılan aracı manifestoya işler.
        Resmî oturumlarda yapılandırılmış gerekçe ZORUNLUDUR (Faz 1.6,
        "her adımda gerekçe" — yapısal); keşif oturumları muaftır.
        """
        if self.manifesto["faz"] != "ANALIZ":
            raise DonguHatasi(f"analiz kaydı yalnız ANALIZ fazında; "
                              f"mevcut faz: {self.manifesto['faz']}")
        if self.manifesto.get("mod", "resmi") == "resmi" and gerekce is None:
            raise DonguHatasi(
                "resmî oturumda analiz adımı gerekçesiz kaydedilemez "
                "(hipotez + yorum zorunlu)")
        self._kaydet(arac, ozet, gerekce)
        return {"kaydedildi": arac, "gecmis_sayisi": len(self.manifesto["gecmis"])}

    def sonucla(self, sonuc_turu, insan_onayi, bulgular=None):
        """
        ANALİZ → SONUÇ: insan onayı ZORUNLU (her algoritmanın bir analiste
        ihtiyacı vardır — Bölüm 15).
        insan_onayi: {'onaylayan': ..., 'not': ...}
        """
        self._gecis_kontrol("SONUC")
        if sonuc_turu not in SONUC_TURLERI:
            raise DonguHatasi(f"sonuc_turu şunlardan biri olmalı: {SONUC_TURLERI}")
        if not insan_onayi or not insan_onayi.get("onaylayan"):
            raise DonguHatasi("insan onayı zorunlu: 'onaylayan' alanı boş olamaz")
        if self.manifesto.get("mod", "resmi") == "resmi":
            yorumsuz = [g["arac"] for g in self.manifesto["gecmis"]
                        if g["faz"] == "ANALIZ" and g["arac"] != "analize_gec"
                        and "gerekce" not in g]
            if yorumsuz:
                raise DonguHatasi(
                    "yorumsuz adımla sonuca geçilemez; gerekçesiz adımlar: "
                    + ", ".join(yorumsuz))
        self.manifesto["insan_onaylari"].append(
            {"zaman": _simdi(), **insan_onayi})
        self.manifesto["sonuc"] = {"tur": sonuc_turu,
                                   "bulgular": bulgular or [],
                                   "zaman": _simdi()}
        self.manifesto["faz"] = "SONUC"
        self._kaydet("sonucla", sonuc_turu)
        return {"faz": "SONUC", "sonuc": self.manifesto["sonuc"]}

    def izleme_plani(self, metrik, esik, kontrol_tarihi, not_=None):
        """
        Döngüyü kapat: SONUÇ'tan sonra izleme planı → yeni döngünün
        PROBLEM fazına beslenir (3T'nin 'Tracking'i).
        """
        if self.manifesto["faz"] != "SONUC":
            raise DonguHatasi("izleme planı yalnız SONUC fazında tanımlanır")
        self.manifesto["izleme"] = {"metrik": metrik, "esik": esik,
                                    "kontrol_tarihi": kontrol_tarihi,
                                    "not": not_}
        self._kaydet("izleme_plani", self.manifesto["izleme"])
        return {"izleme": self.manifesto["izleme"],
                "dongu": "kapandı; kontrol tarihinde yeni döngü önerilir"}


# ---------------- kalıcılık ----------------

def _oturum_dizini(log_dir, olustur=False):
    return os.path.dirname(kanit._oturum_yolu(log_dir, "_dizin", ".json", olustur))


def kaydet(dongu, log_dir):
    """
    Manifestoyu kalıcılaştırır + yeni gecmiş adımlarını Katman-1 olay
    akışına delta olarak işler (kanit.py): akış kaynaktır, manifesto
    anlamsal görünümdür. Olaylara PII değeri yazılmaz.

    Dayanıklılık (v6.5, H1):
    - Delta başlangıcı manifestodaki sayaçtan DEĞİL, akışın kendisinden
      türetilir → olay yazıldıktan sonra çökme olursa yeniden kayıt
      olayı ÇOĞALTMAZ (idempotent; sayaç diske hiç yazılmaz).
    - Manifesto ATOMİK yazılır (kanit.atomik_json_yaz).
    - Manifesto yazılamazsa hata GÜRÜLTÜLÜDÜR (DonguHatasi): kanıt
      kaybı asla sessiz değildir — olaylar akışta sağlamdır, manifesto
      akıştan onarılabilir (yukle uzlaştırması).
    """
    from . import kanit
    m = dongu.manifesto
    islenen = len(kanit.oku(log_dir, m["oturum_id"]))  # akıştan türet
    for adim in m["gecmis"][islenen:]:
        olay = {"olay": adim["arac"], "faz": adim["faz"],
                "ozet": adim.get("ozet", "")[:200]}
        if "gerekce" in adim:
            olay["gerekce"] = {k: str(v)[:300]
                               for k, v in adim["gerekce"].items()}
        kanit.olay_yaz(log_dir, m["oturum_id"], olay)
    m.pop("olay_sayaci", None)  # eski sürüm kalıntısı; artık kullanılmıyor
    yol = kanit._oturum_yolu(log_dir, m["oturum_id"], ".json", olustur=True)
    try:
        kanit.atomik_json_yaz(yol, m)
    except OSError as e:
        raise DonguHatasi(
            f"manifesto yazılamadı: {e}; olay akışı sağlam — oturum "
            f"yeniden yüklenince akıştan onarılır") from e
    return yol


def _akistan_gecmis(olaylar):
    """Katman-1 olaylarından gecmis projeksiyonu (H1.4 onarımı)."""
    g = []
    for o in olaylar:
        adim = {"zaman": o.get("zaman"), "faz": o.get("faz"),
                "arac": o.get("olay"), "ozet": o.get("ozet", "")}
        if "gerekce" in o:
            adim["gerekce"] = o["gerekce"]
        g.append(adim)
    return g


def yukle(oturum_id, log_dir):
    """
    Oturumu yükler + H1.4 uzlaştırması: manifesto ile olay akışı
    karşılaştırılır.
    - Akış İLERİDEYSE (çökme: olay yazıldı, manifesto yazılamadı):
      zincir sağlamsa gecmis akıştan ONARILIR; kanit_uyari işaretlenir.
    - Akış GERİDEYSE / zincir BOZUKSA: onarım yapılmaz, kanit_uyari ile
      kanit_dogrula önerilir. Hiçbir durumda sessiz geçilmez.
    """
    from . import kanit
    yol = kanit._oturum_yolu(log_dir, oturum_id, ".json")
    if not os.path.isfile(yol):
        raise DonguHatasi(f"oturum bulunamadı: {oturum_id}")
    with open(yol, encoding="utf-8") as f:
        m = json.load(f)
    olaylar = kanit.oku(log_dir, oturum_id)
    n_akis, n_gecmis = len(olaylar), len(m["gecmis"])
    if n_akis > n_gecmis:
        if kanit.dogrula(log_dir, oturum_id)["saglam"]:
            m["gecmis"] = _akistan_gecmis(olaylar)
            m["kanit_uyari"] = (f"çökme onarımı: {n_akis - n_gecmis} adım "
                                "olay akışından geri yüklendi")
        else:
            m["kanit_uyari"] = ("olay akışı zinciri BOZUK; onarım "
                                "yapılmadı — kanit_dogrula çalıştırın")
    elif n_akis < n_gecmis:
        m["kanit_uyari"] = (f"olay akışı eksik ({n_akis}/{n_gecmis} adım); "
                            "kanit_dogrula çalıştırın")
    d = AnalizDongusu(m["talep"], m["oturum_id"])
    d.manifesto = m
    return d


def listele(log_dir):
    """Oturum dizinindeki tüm manifestoları özet projeksiyonla döner.
    Args: log_dir. Returns: [{oturum_id, mod, faz, adim_sayisi, ...}] listesi.
    """
    d = _oturum_dizini(log_dir)
    if not os.path.isdir(d):
        return []
    sonuc = []
    for fn in sorted(os.listdir(d)):
        if fn.endswith(".json") and kanit._OTURUM_ID.fullmatch(fn[:-5]):
            try:
                with open(kanit._oturum_yolu(log_dir, fn[:-5], ".json"),
                          encoding="utf-8") as f:
                    m = json.load(f)
                if (not isinstance(m, dict) or m.get("oturum_id") != fn[:-5]
                        or not {"faz", "talep", "olusturma"} <= m.keys()
                        or not isinstance(m["talep"], dict)):
                    raise DonguHatasi("oturum listesinde geçersiz manifesto")
            except json.JSONDecodeError as exc:
                raise DonguHatasi("oturum listesinde bozuk manifesto") from exc
            sonuc.append({"oturum_id": m["oturum_id"], "faz": m["faz"],
                          "mod": m.get("mod", "resmi"),
                          "urun_turu": m["talep"].get("urun_turu"),
                          "olusturma": m["olusturma"]})
    return sonuc
