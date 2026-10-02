# -*- coding: utf-8 -*-
"""
uygulama/sunucu.py — A5 tek süreç arka uç (ADR-003).

FastAPI uygulaması çekirdeği süreç içinde çağırır; ikinci bir hesap yolu yoktur
(AGENTS kural 5): her uç, MCP ile BİREBİR aynı boru hattı olan
`sinama.arayuz.sunucu.arac_calistir`'ın ince sarmalayıcısıdır — kapı, gerekçe, kanıt
zinciri ve uyarılar aynı yoldan geçer. Rehberli yüzün üç ekranı ayrıntılı bilim
araçlarının sırasını izler: calisma_baslat → (hipotez_ekle) → sinama_plani →
kanit_bagla → hukum → dongu_sonuc (insan onayı).

Veri kökü depo dışındadır (ADR-003 md. 3): `uygulama_olustur` depo içi kökü reddeder ve
SINAMA_VERI_KOKU / SINAMA_LOG_DIR'i köke ayarlar (veri/ girdi, oturumlar/ kayıt).
Dil modeli opsiyoneldir (md. 4): soru türü önerisi ve hüküm ifadesinin sade dile
çevrilmesi; sayı üretmez, hüküm kategorisini değiştiremez; kapalıyken her şey çalışır.
"""
import json
import os
import re
import sys
import threading
import urllib.request

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if os.path.join(KOK, "cekirdek") not in sys.path:
    sys.path.insert(0, os.path.join(KOK, "cekirdek"))

from fastapi import Body, FastAPI, Request  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from fastapi.staticfiles import StaticFiles  # noqa: E402

from sinama.arayuz import sunucu as cekirdek_sunucu  # noqa: E402
from sinama.bilim import sablon, sinamalar  # noqa: E402
from sinama.cekirdek import guvenlik, veri  # noqa: E402
from sinama.cekirdek.hatalar import SucAnaliziHatasi  # noqa: E402

VARSAYILAN_HOST = "127.0.0.1"
VARSAYILAN_PORT = 8810
VARSAYILAN_DIL_MODELI = "http://127.0.0.1:8080"
SURUM = "a5.1"
WEB_DIST = os.path.join(KOK, "uygulama", "web", "dist")
CALISMA_ALANLARI = ("soru_turu", "amac", "onaylayan", "soru", "kanal_alan", "mo_alan",
                    "bolge_alan", "mudahale", "kontrol", "tampon", "kesinti_tarihi")
HIPOTEZ_ALANLARI = ("ifade", "mekanizma", "sonraki_kanit", "etki")
SONUC_ALANLARI = ("sonuc_turu", "onaylayan", "onay_notu", "bulgular")
ONIZLEME_DEGER_SINIRI = 30   # daha çok farklı değeri olan sütun kategorik sayılmaz
# Kural tabanlı öneri: sıra önemlidir (ETKİ sorusu "artırımı" içerebilir).
ONERI_KURALLARI = (
    ("ETKI", ("azalt", "etki", "müdahale", "işe yara", "önle", "sonra düş", "sonrasında düş",
              "reduce", "impact", "effect", "after the", "since the")),
    ("SERI", ("seri", "aynı fail", "aynı kişi", "aynı ekip", "aynı grup", "dizi halinde",
              "series", "same offender", "same group", "linked")),
    ("YOGUNLASMA", ("yoğunlaş", "kümelen", "toplan", "sıcak nokta", "belirli yer", "hangi bölge",
                    "nerede", "concentrat", "cluster", "hot spot", "hotspot", "where")),
    ("ARTIS", ("art", "yüksel", "çoğal", "eğilim", "trend", "increase", "go up", "went up", "rise",
               "rising")),
)
_MOTOR = threading.Lock()   # tek motor, tek kullanıcı: çekirdek çağrıları sırayla
# Hata tipi → HTTP durumu (DataFlow ml-service suc köprüsünden kavram hasadı): kapı reddi
# 422, düzeltilebilir istemci hataları 400, sistem 500; bilinmeyen tip 400.
_TIP_DURUM = {"kapi": 422, "veri": 400, "guvenlik": 400, "kullanim": 400, "dongu": 400,
              "kilit": 400, "sistem": 500}


def depo_icinde_mi(yol):
    """Yol bu deponun içinde mi (sembolik bağlar çözülerek)."""
    yol, kok = os.path.realpath(yol), os.path.realpath(KOK)
    try:
        return os.path.commonpath([yol, kok]) == kok
    except ValueError:   # farklı sürücüler (Windows)
        return False


def _kucult(metin):
    """Türkçe büyük/küçük harf duyarlı küçültme (İ → i, I → ı)."""
    return metin.replace("İ", "i").replace("I", "ı").lower()


def kural_onerisi(soru):
    """Soru metninden kural tabanlı soru türü önerisi (None: eşleşme yok)."""
    s = _kucult(soru or "")
    for tur, anahtarlar in ONERI_KURALLARI:
        if any(a in s for a in anahtarlar):
            return tur
    return None


def _dil_modeli_istek(url, yol, govde=None, zaman=0.8):
    """Dil modeli sunucusuna JSON isteği (yerel; vekil yok). Hata → None."""
    if not url:
        return None
    istek = urllib.request.Request(url.rstrip("/") + yol, method="POST" if govde else "GET",
                                   data=json.dumps(govde).encode("utf-8") if govde else None,
                                   headers={"Content-Type": "application/json"})
    acici = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    try:
        with acici.open(istek, timeout=zaman) as y:
            return json.loads(y.read().decode("utf-8") or "{}")
    except Exception:   # noqa: BLE001 — opsiyonel yol: bozuk adres (InvalidURL) bile akışı düşürmez
        return None


def dil_modeli_erisilebilir(url):
    """Dil modeli sunucusu yanıt veriyor mu (llama.cpp /health, yoksa /v1/models)."""
    return bool(_dil_modeli_istek(url, "/health") is not None
                or _dil_modeli_istek(url, "/v1/models") is not None)


def _sohbet(url, sistem, kullanici, en_cok=200):
    """OpenAI uyumlu sohbet tamamlaması; metin ya da None."""
    # Düşünme kipi kapatılır: Qwen3.8 gibi modeller aksi hâlde sınırlı token bütçesini
    # reasoning_content'e harcayıp content'i BOŞ döndürüyordu (a5_dil_modeli keşfi).
    y = _dil_modeli_istek(url, "/v1/chat/completions", {
        "messages": [{"role": "system", "content": sistem}, {"role": "user", "content": kullanici}],
        "temperature": 0, "max_tokens": en_cok,
        "chat_template_kwargs": {"enable_thinking": False}}, zaman=60)
    try:
        return y["choices"][0]["message"]["content"].strip()
    except (TypeError, KeyError, IndexError, AttributeError):
        return None


def _hata_yaniti(e, kod=None):
    """Alan hatası → istemciye tek satırlık, tipli hata (iç ayrıntı sızdırılmaz)."""
    kod = kod or _TIP_DURUM.get(getattr(e, "tip", None), 400)
    return JSONResponse(status_code=kod, content={"hata": {
        "tur": getattr(e, "tip", "sistem"), "mesaj": str(e), "oneri": getattr(e, "oneri", None)}})


def uygulama_olustur(veri_koku=None, dil_modeli_url=VARSAYILAN_DIL_MODELI):
    """A5 arka ucu (ASGI). Veri kökü depo içindeyse ValueError.

    Args:
        veri_koku: depo dışı veri kökü; None → SINAMA_VERI_KOKU ya da platform varsayılanı.
        dil_modeli_url: OpenAI uyumlu yerel dil modeli sunucusu; None → dil modeli yok.

    Returns:
        FastAPI uygulaması.
    """
    kok = os.path.realpath(veri_koku or os.environ.get("SINAMA_VERI_KOKU")
                           or guvenlik.varsayilan_veri_koku())
    if depo_icinde_mi(kok):
        raise ValueError(f"veri kökü depo içinde olamaz ({kok}); ADR-001 md. 5 — depo dışı bir "
                         f"dizin verin (SINAMA_VERI_KOKU)")
    os.makedirs(os.path.join(kok, "veri"), exist_ok=True)
    os.makedirs(os.path.join(kok, "oturumlar"), exist_ok=True)
    os.environ["SINAMA_VERI_KOKU"] = kok
    os.environ["SINAMA_LOG_DIR"] = kok

    app = FastAPI(title="Sınama", version=SURUM, docs_url=None, redoc_url=None, openapi_url=None)

    def arac(ad, arg):
        """Çekirdek aracı resmi yoldan: {sonuc..., uyarilar} ya da tipli hata yanıtı."""
        try:
            with _MOTOR:
                paket = cekirdek_sunucu.arac_calistir(ad, arg)
        except SucAnaliziHatasi as e:
            return _hata_yaniti(e)
        sonuc, uyarilar = paket["sonuc"], paket["meta"].get("uyarilar", [])
        if isinstance(sonuc, dict):
            return {**sonuc, "uyarilar": uyarilar}
        return {"sonuc": sonuc, "uyarilar": uyarilar}

    def secili(govde, alanlar):
        """Gövdeden yalnız sözleşmedeki ve dolu alanlar."""
        return {k: govde[k] for k in alanlar if isinstance(govde, dict) and govde.get(k) not in (None, "")}

    @app.get("/api/saglik")
    def saglik():
        """Sürüm, veri kökü ve dil modelinin erişilebilirliği."""
        return {"durum": "hazir", "surum": SURUM, "sinama_surumu": sinamalar.SINAMA_SURUMU,
                "veri_koku": kok, "dil_modeli": dil_modeli_erisilebilir(dil_modeli_url)}

    @app.post("/api/oneri")
    def oneri(govde: dict = Body(...)):
        """Serbest soru metninden soru türü önerisi (kullanıcı onaylar)."""
        soru = str(govde.get("soru") or "")
        if dil_modeli_erisilebilir(dil_modeli_url):
            cevap = _sohbet(dil_modeli_url, "Bir suç analizi sorusunu şu türlerden BİRİNE ayır ve "
                            "yalnız türün adını yaz: " + ", ".join(sablon.TURLER) + ". ARTIS: kayıtlı "
                            "olaylar arttı mı; YOGUNLASMA: olaylar mekânda yoğunlaşıyor mu; SERI: "
                            "olaylar ortak bir kaynaktan mı; ETKI: bir müdahale olayları azalttı mı.",
                            soru, en_cok=8)
            bulunan = [t for t in sablon.TURLER if cevap and t in cevap.upper()]
            if len(bulunan) == 1:
                return {"soru_turu": bulunan[0], "kaynak": "dil_modeli"}
        return {"soru_turu": kural_onerisi(soru), "kaynak": "kural"}

    @app.post("/api/calisma")
    def calisma_baslat(govde: dict = Body(...)):
        """Soru ekranı → çalışma (hipotez seti + sınama planı)."""
        return arac("calisma_baslat", secili(govde, CALISMA_ALANLARI))

    @app.get("/api/calisma/{oturum_id}")
    def calisma_durum(oturum_id: str):
        """Oturum manifestosu (ekranın yeniden yüklenmesi için)."""
        return arac("dongu_durum", {"oturum_id": oturum_id})

    @app.post("/api/calisma/{oturum_id}/hipotez")
    def hipotez_ekle(oturum_id: str, govde: dict = Body(...)):
        """Plan ekranı → serbest rakip açıklama (kilitten önce)."""
        return arac("hipotez_ekle", {"oturum_id": oturum_id, **secili(govde, HIPOTEZ_ALANLARI)})

    @app.get("/api/calisma/{oturum_id}/plan")
    def plan(oturum_id: str):
        """Plan ekranı → sınama planı (veriye bakmadan)."""
        return arac("sinama_plani", {"oturum_id": oturum_id})

    @app.post("/api/calisma/{oturum_id}/kanit")
    def kanit(oturum_id: str, govde: dict = Body(...)):
        """Plan ekranı → kilit (doğrulayıcıda) + veri + sınamalar."""
        arg = {"oturum_id": oturum_id}
        if govde.get("dosya"):
            arg["csv_yolu"] = os.path.join("veri", os.path.basename(str(govde["dosya"])))
        elif isinstance(govde.get("satirlar"), list):
            arg["satirlar"] = govde["satirlar"]
        return arac("kanit_bagla", arg)

    @app.post("/api/calisma/{oturum_id}/hukum")
    def hukum(oturum_id: str):
        """Hüküm ekranı → kategorik hüküm (taslak)."""
        return arac("hukum", {"oturum_id": oturum_id})

    @app.post("/api/calisma/{oturum_id}/sade")
    def sade(oturum_id: str, govde: dict = Body(default={})):
        """Hüküm ifadesinin sade dile çevrilmesi (dil modeli; bağlayıcı değil, sayı yok)."""
        dil = "İngilizce" if govde.get("dil") == "en" else "Türkçe"
        durum = arac("dongu_durum", {"oturum_id": oturum_id})
        if isinstance(durum, JSONResponse):
            return durum
        h = (durum.get("bilimsel") or {}).get("hukum")
        if not h:
            return JSONResponse(status_code=409, content={"hata": {"tur": "kullanim",
                                "mesaj": "önce hüküm alınmalı", "oneri": None}})
        if not dil_modeli_erisilebilir(dil_modeli_url):
            return JSONResponse(status_code=503, content={"hata": {"tur": "dil_modeli",
                                "mesaj": "dil modeli erişilemiyor", "oneri": None}})
        metin = _sohbet(dil_modeli_url, f"Aşağıdaki bilimsel hükmü {dil} sade dille, iki üç "
                        "cümleyle açıkla. Kategoriyi aynen koru, yeni bilgi ekleme, HİÇ SAYI ya da "
                        "yüzde yazma, olasılık ifade etme.",
                        json.dumps({"kategori": h["kategori"], "ifade": h["ifade"],
                                    "kurallar": [k["girdi"] for k in h["kurallar"]]},
                                   ensure_ascii=False))
        kategori_yok = dil == "Türkçe" and _kucult(h["kategori"]) not in _kucult(metin or "")
        if not metin or re.search(r"\d", metin) or kategori_yok:
            return JSONResponse(status_code=422, content={"hata": {"tur": "dil_modeli",
                                "mesaj": "dil modeli çıktısı sözleşmeyi bozdu (sayı ya da kategori)",
                                "oneri": None}})
        return {"metin": metin, "kaynak": "dil_modeli", "baglayici": False}

    @app.post("/api/calisma/{oturum_id}/sonuc")
    def sonuc(oturum_id: str, govde: dict = Body(...)):
        """İnsan onayıyla SONUÇ (onaylayan zorunlu)."""
        return arac("dongu_sonuc", {"oturum_id": oturum_id, **secili(govde, SONUC_ALANLARI)})

    @app.get("/api/veri")
    def veri_listesi():
        """Veri kökündeki girdi dosyaları."""
        dizin = os.path.join(kok, "veri")
        return {"dosyalar": [{"ad": ad, "boyut": os.path.getsize(os.path.join(dizin, ad))}
                             for ad in sorted(os.listdir(dizin))
                             if os.path.splitext(ad)[1].lower() in guvenlik.IZINLI_UZANTILAR]}

    @app.post("/api/veri")
    async def veri_yukle(request: Request, ad: str):
        """Ham gövdeyle dosya yükleme (çok parçalı biçim gerekmez)."""
        if os.path.basename(ad) != ad or ad.startswith(".") \
                or os.path.splitext(ad)[1].lower() not in guvenlik.IZINLI_UZANTILAR:
            return JSONResponse(status_code=400, content={"hata": {"tur": "guvenlik",
                                "mesaj": "geçersiz dosya adı ya da uzantı", "oneri": "ör. olaylar.csv"}})
        icerik = await request.body()
        if len(icerik) > guvenlik.MAKS_DOSYA_MB * 1024 * 1024:
            return JSONResponse(status_code=413, content={"hata": {"tur": "guvenlik",
                                "mesaj": f"dosya {guvenlik.MAKS_DOSYA_MB} MB'tan büyük", "oneri": None}})
        hedef = os.path.join(kok, "veri", ad)
        if os.path.exists(hedef):
            return JSONResponse(status_code=409, content={"hata": {"tur": "kullanim",
                                "mesaj": "bu adla dosya var", "oneri": "başka ad verin"}})
        with open(hedef, "wb") as f:
            f.write(icerik)
        return {"ad": ad, "boyut": len(icerik)}

    @app.get("/api/veri/{ad}/onizleme")
    def onizleme(ad: str):
        """Sütunlar, satır sayısı ve ilk beş satır (alan seçimi için)."""
        try:
            with _MOTOR:
                satirlar = veri.csv_yukle(os.path.join("veri", os.path.basename(ad)))
        except (SucAnaliziHatasi, OSError, ValueError) as e:
            return _hata_yaniti(e)
        sutunlar = list(satirlar[0].keys()) if satirlar else []
        degerler = {}
        for s in sutunlar:   # kategorik alanların değerleri (müdahale/kontrol seçimi için)
            farkli = sorted({str(r.get(s)) for r in satirlar if str(r.get(s) or "").strip()})
            degerler[s] = farkli if len(farkli) <= ONIZLEME_DEGER_SINIRI else None
        return {"ad": ad, "sutunlar": sutunlar, "satir": len(satirlar), "ilk": satirlar[:5],
                "degerler": degerler, "kesildi": bool(veri.son_okuma.get("kesildi"))}

    if os.path.isfile(os.path.join(WEB_DIST, "index.html")):
        app.mount("/", StaticFiles(directory=WEB_DIST, html=True), name="web")
    else:
        @app.get("/")
        def kok_sayfa():
            """Ön yüz derlenmemişse kısa bilgi."""
            return {"durum": "hazir", "not": "ön yüz derlenmemiş: uygulama/web içinde npm run build"}
    return app
