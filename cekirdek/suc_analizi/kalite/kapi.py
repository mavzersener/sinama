# -*- coding: utf-8 -*-
r"""
kalite.py — TEK FITNESS-GATE OTORİTESİ (v6.0 / Faz A, G2+G4).

Mimari ilke (birleşik yol haritası §4.2): gate mantığı tek fonksiyonda
tanımlıdır ve dispatch yolunda tek noktadan uygulanır — döngü içi ya da
standalone fark etmez, her analiz aynı kapıdan geçer.

Tarihçe: kurallar v5.1'de veri.analiz_uygun_mu içinde tanımlandı; v6.0'da
otorite bu modüle taşındı. veri.analiz_uygun_mu geriye uyumluluk için
buraya delege eden ince bir sarmalayıcıdır — YENİ KURAL BURAYA yazılır.

Sözleşme:
  kapi(profil, analiz, **baglam) -> {"uygun": bool, "girdi_n": int,
                                     "sebepler": [str, ...]}
  uygun=False  -> analiz ÇALIŞTIRILMAZ (KapiRed fırlatılır).
  uygun=True + sebepler -> engel yok ama danışma uyarıları; meta'ya düşer.
  "uygun değil" geçerli ve profesyonel bir cevaptır.

baglam anahtarları: payda_var, beklenen_hucreler, olcum_duzeyi,
bolge_sayisi, mevsim_otokorelasyon, tur_kardinalite, maks_tur_pay.
"""

from ..cekirdek.hatalar import SucAnaliziHatasi


class KapiRed(SucAnaliziHatasi, ValueError):
    """Fitness gate reddi: analiz bu veriyle/bağlamla çalıştırılamaz.

    ValueError'dan türetilir — istemciye traceback değil, tek satırlık
    profesyonel gerekçe döner (güvenlik sözleşmesi korunur).
    v6.5: taksonomide tipi "kapi"dir (politika reddi).
    """
    tip = "kapi"


# Kapının tanıdığı analiz adları — araç adıyla birebir aynı olmayanlar
# sunucu.ARAC_GATE üzerinden eşlenir.
MEKANSAL = ("kde_yogunluk", "grid_hotspot", "nni", "yakin_tekrar",
            "knox_tablosu")
ZAMANSAL = ("trend", "cusum", "kontrol_grafigi", "holt_winters")


def kapi(profil, analiz, **baglam):
    """
    Deterministik fitness gate (K9): analiz çalıştırılabilir mi?
    'uygun=False' geçerli ve profesyonel bir cevaptır.
    """
    s, uygun, n = [], True, profil.get("n", 0)
    if profil.get("kesildi"):
        s.append("veri MAKS_SATIR tavanında kesildi; sonuç eksik olabilir")

    if analiz in MEKANSAL:
        if profil.get("koordinat_gecerli_oran", 0) < 0.5:
            uygun = False
            s.append("geçerli koordinat < %50; mekânsal analiz güvenilmez")
        if profil.get("koordinat_tek_nokta"):
            uygun = False
            s.append("tüm koordinatlar tek noktada; geokodlama hatası şüphesi")
        if n < 30:
            s.append("nokta sayısı < 30; KDE/hotspot/NNI zayıf")

    if analiz in ZAMANSAL:
        if profil.get("zaman_kapsam", {}).get("olayli_gun", 0) < 14:
            s.append("seri çok kısa; trend/tahmin zayıf")

    if analiz == "yukselen_sicak_nokta":
        if baglam.get("bolge_sayisi", 0) < 2:
            uygun = False
            s.append("en az iki geçerli bölge gerekli; yükselen hotspot sınıflanamaz")
        if profil.get("zaman_kapsam", {}).get("olayli_gun", 0) < 2:
            uygun = False
            s.append("geçerli zaman kapsamı yok; dönemsel hotspot sınıflanamaz")

    if analiz == "suc_oranlari" and not baglam.get("payda_var"):
        uygun = False
        s.append("nüfus (payda) yok; ham sayı yerine oran verilemez")

    if analiz == "bolge_anomali":
        disp = profil.get("dispersiyon_orani")
        if disp and disp > 1.5:
            s.append(f"aşırı yayılım (var/mean={disp}); p-değerleri negatif "
                     "binom modelinden hesaplanır (v6.3, otomatik) — "
                     "q değerini esas alın")
        if baglam.get("bolge_sayisi", 0) > 10:
            s.append("çoklu karşılaştırma: Bonferroni/FDR düzeltmesi zorunlu")

    if analiz == "benford" and profil.get("benford_mertebe", 0) < 3:
        uygun = False
        s.append("veri yeterli büyüklük mertebesi kapsamıyor; Benford anlamsız")

    if analiz == "ki_kare_testi":
        beklenen = baglam.get("beklenen_hucreler")
        if beklenen:
            kucuk = sum(1 for e in beklenen if e < 5)
            if kucuk / len(beklenen) > 0.2:
                s.append("beklenen hücre <5 oranı yüksek (Cochran); "
                         "2x2 ise fisher_exact aracını kullanın veya "
                         "kategori birleştirin")

    if analiz in ("ozet", "ortalama") and \
            baglam.get("olcum_duzeyi", "").startswith("nominal"):
        uygun = False
        s.append("nominal veride ortalama/standart sapma geçersizdir; "
                 "mod, frekans, ki-kare kullanın")

    if analiz in ("t_testi", "mann_whitney", "randomizasyon_testi"):
        if n and n < 20:
            s.append("örneklem < 20; güç düşük — guc_analizi ile kontrol edin")

    if analiz in ("anova", "kruskal_wallis"):
        if n and n < 30:
            s.append("toplam n < 30; grup başına güç düşük olabilir")

    if analiz == "coklu_regresyon":
        if n and n < 50:
            s.append("n < 50; çoklu regresyon katsayıları kararsız olabilir")

    if analiz == "lojistik_regresyon":
        if n and n < 100:
            s.append("n < 100; lojistik katsayılar ve odds oranları kararsız "
                     "olabilir (kural: değişken başına ~10 olay)")

    if analiz == "zarar_analizi":
        if baglam.get("tur_kardinalite", 99) <= 1:
            s.append("homojen suç kümesi: zarar ağırlıklandırma ek bilgi "
                     "üretmez (Ch 13.6 tuzağı)")
        if baglam.get("maks_tur_pay", 0) > 0.8:
            s.append("tek suç türü zararın >%80'ini domine ediyor; "
                     "tablo bu türe indirgenir — tür bazında ayrıştırın")

    if analiz == "holt_winters":
        ok7 = baglam.get("mevsim_otokorelasyon")
        if ok7 is not None and ok7 < 0.3:
            s.append(f"haftalık otokorelasyon zayıf ({ok7}); mevsim=7 "
                     "varsayımı veriyle desteklenmiyor")

    return {"uygun": uygun, "girdi_n": n,
            "sebepler": s or ["belirgin engel yok"]}
