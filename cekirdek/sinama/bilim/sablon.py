# -*- coding: utf-8 -*-
"""
sablon.py — Soru türü şablonları (ADR-002 §2–3).

Şablon; birincil hipotezi, onun makinece değerlendirilebilir öngörüsünü ve
yanlışlama koşulunu tanımlar. Rakipler RAK'tan (soru türüne uygulanabilen her
kayıt), H_bilinmeyen her sette zorunludur. Serbest öngörü dili v1.1'e kalır.
"""
from . import rak

SABLON_SURUMU = "sablon-v1"

SABLONLAR = {
    "ARTIS": {
        "birincil": "kayıtlı olay sayısındaki artış gerçek bir suç artışını yansıtır",
        "ongoru": {"arac": "trend", "olcut": "yorum", "kosul": "== 'artan' (eğim t-testi, p < 0,05)"},
        "yanlislama": "eğim anlamlı biçimde negatif ('azalan')",
        "gerekli_alanlar": ("tarih",),
    },
    "YOGUNLASMA": {
        "birincil": "olaylar mekânda rastgele beklenenden fazla yoğunlaşır (sıcak nokta)",
        "ongoru": {"arac": "sicak_nokta_gi", "olcut": "sicak",
                   "kosul": ">= 1 (Gi*, Benjamini–Hochberg q ≤ 0,05)"},
        "yanlislama": "v1'de tanımsız: sıcak nokta bulunmaması yalnız 'desteklenmedi'dir",
        "gerekli_alanlar": ("lat", "lon"),
    },
    "SERI": {
        "birincil": "bu olayların bir kısmı ortak bir kaynaktan (seri) gelen bir desen "
                    "gösterir — desen, kimlik ya da aynı fail iddiası değildir",
        "ongoru": {"arac": "seri_eslestirme", "olcut": "katman",
                   "kosul": "en az bir 'güçlü' aday (MO ayırt edici + uzay-zaman, FDR)"},
        "yanlislama": "v1'de tanımsız: aday bulunmaması yalnız 'desteklenmedi'dir",
        "gerekli_alanlar": ("mo",),
    },
}

TURLER = tuple(SABLONLAR)

H_BILINMEYEN = {
    "kimlik": "H_bilinmeyen", "tur": "BILINMEYEN",
    "ifade": "listelenen açıklamaların dışında kalan, modellenmemiş bir açıklama",
    "not": "silinemez, birincil yapılamaz, hüküm almaz; her hüküm listelenen "
           "rakiplere göredir",
}


def hipotez_seti(soru_turu):
    """Şablondan hipotez seti: birincil + uygulanabilir rakipler + H_bilinmeyen."""
    s = SABLONLAR[soru_turu]
    hipotezler = [{"kimlik": "H1", "tur": "BIRINCIL", "ifade": s["birincil"],
                   "ongoru": dict(s["ongoru"]), "yanlislama": s["yanlislama"]}]
    for kod in rak.uygulanabilir(soru_turu):
        k = rak.KATALOG[kod]
        hipotezler.append({"kimlik": kod, "tur": "RAKIP", "ifade": k["ad"],
                           "mekanizma": k["mekanizma"], "sinama": k["sinama"],
                           "etki": k["etki"]})
    hipotezler.append(dict(H_BILINMEYEN))
    return hipotezler
