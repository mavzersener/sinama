# -*- coding: utf-8 -*-
"""
a5_dil_modeli.py — KEŞİF (ön-kayıt dışı; dil modeli belirlenimci değil, CI'da koşmaz).

A5'in opsiyonel dil modeli yollarını yerel sunucuyla (OpenAI uyumlu, varsayılan
http://127.0.0.1:8080) dener: (a) soru türü önerisi — kural tabanlı öneriyle kıyas,
(b) hükmün sade dille özeti — sözleşme denetimi (sayı yok, kategori korunur). Sentetik
veri, geçici veri kökü (depo dışı).

Kullanım (depo kökünden): python kiyas/kesif/a5_dil_modeli.py [url]
"""
import os
import re
import sys
import tempfile
import time

KOK = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, KOK)
sys.path.insert(0, os.path.join(KOK, "kiyas"))

from fastapi.testclient import TestClient  # noqa: E402
import uretec  # noqa: E402
from uygulama import sunucu as uyg  # noqa: E402

SORULAR = {
    "Son 12 ayda hırsızlık arttı mı?": "ARTIS",
    "Devriye artırımı bölgedeki suçları azalttı mı?": "ETKI",
    "Olaylar belirli yerlerde yoğunlaşıyor mu?": "YOGUNLASMA",
    "Bu hırsızlıklar aynı seriden mi?": "SERI",
    "Kamera kurulduktan sonra kapkaç düştü mü?": "ETKI",
    "Gasp olayları geçen yıla göre çoğaldı mı?": "ARTIS",
    "Oto hırsızlıkları şehrin hangi bölgelerinde toplanıyor?": "YOGUNLASMA",
    "Bu üç konut hırsızlığını aynı ekip mi yapmış olabilir?": "SERI",
    "Did burglaries go up this year?": "ARTIS",
    "Did the new lighting reduce street robberies?": "ETKI",
}


def main(url="http://127.0.0.1:8080"):
    kok = tempfile.mkdtemp(prefix="a5_dm_")
    c = TestClient(uyg.uygulama_olustur(veri_koku=kok, dil_modeli_url=url))
    print("sağlık:", c.get("/api/saglik").json()["dil_modeli"])
    dogru = {"dil_modeli": 0, "kural": 0}
    kaynaklar = []
    for soru, tur in SORULAR.items():
        t0 = time.perf_counter()
        y = c.post("/api/oneri", json={"soru": soru}).json()
        sure = time.perf_counter() - t0
        kural = uyg.kural_onerisi(soru)
        kaynaklar.append(y["kaynak"])
        dogru["dil_modeli"] += y["kaynak"] == "dil_modeli" and y["soru_turu"] == tur
        dogru["kural"] += kural == tur
        print(f"{sure:5.1f} sn | beklenen {tur:10s} | yanıt {str(y['soru_turu']):10s} ({y['kaynak']}) | "
              f"kural {kural} | {soru}")
    print(f"doğru: dil modeli {dogru['dil_modeli']}/{len(SORULAR)} (kaynağı dil_modeli olanlarda), "
          f"kural {dogru['kural']}/{len(SORULAR)}; kaynak dağılımı {dict((k, kaynaklar.count(k)) for k in set(kaynaklar))}")
    p = {"baslangic": "2024-01-01", "ay_sayisi": 24, "kesinti_ayi": 13, "karakol_lambda": 40, "cevrimici_lambda": 12}
    satirlar, _ = uretec.v2_bildirim(p, 951)
    oid = c.post("/api/calisma", json={"soru_turu": "ARTIS", "amac": "kesifsel", "kanal_alan": "kanal"}).json()["oturum_id"]
    c.post(f"/api/calisma/{oid}/kanit", json={"satirlar": satirlar})
    h = c.post(f"/api/calisma/{oid}/hukum").json()["hukum"]
    for dil in ("tr", "en"):
        t0 = time.perf_counter()
        r = c.post(f"/api/calisma/{oid}/sade", json={"dil": dil})
        govde = r.json()
        metin = govde.get("metin") or govde.get("hata", {}).get("mesaj")
        print(f"sade[{dil}] {time.perf_counter() - t0:.1f} sn HTTP {r.status_code} kategori {h['kategori']} | "
              f"rakam {'VAR' if re.search(r'[0-9]', metin or '') else 'yok'} | {metin}")


if __name__ == "__main__":
    for akis in (sys.stdout, sys.stderr):
        akis.reconfigure(encoding="utf-8")
    main(*sys.argv[1:2])
