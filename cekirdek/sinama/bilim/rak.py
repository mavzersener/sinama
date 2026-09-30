# -*- coding: utf-8 -*-
"""
rak.py — Rakip Açıklama Kataloğu (RAK) v1 (ADR-002 §4).

Her rakip, birincil hipotezin öngördüğü deseni BAŞKA bir mekanizmayla
üretebilecek açıklamadır. Her kaydın ayırt edici bir sınaması vardır; veri ya
da araç yoksa rakip düşürülmez, "çözülmedi" kalır ve hüküm bunu söyler.
Sıra, eşitlik bozmada kullanılır (katalog sırası).
"""

RAK_SURUMU = "rak-v1"

DURUMLAR = ("dışlandı", "destekleniyor", "çözülmedi", "uygulanamaz")

KATALOG = {
    "R-RASTLANTI": {
        "ad": "Rastgele dalgalanma / küçük sayı / çoklu karşılaştırma",
        "turler": ("ARTIS", "YOGUNLASMA", "SERI", "ETKI"),
        "mekanizma": "gürültü, rastgele nokta deseni ya da çok sayıda sınamadan biri "
                     "tesadüfen 'anlamlı' görünür",
        "sinama": "birincil öngörünün anlamlılık sınaması (çoklu test düzeltmeli)",
        "etki": "yüksek",
        "sonraki_kanit": "daha uzun dönem ya da daha fazla kayıt (güç)",
        "kaynak": "Weisburd & Britt, Statistics in Criminal Justice (çoklu test)",
    },
    "R-BILDIRIM": {
        "ad": "Kayıt/bildirim değişikliği (yeni kanal, sistem, tanım)",
        "turler": ("ARTIS",),
        "mekanizma": "suç değişmeden kayıt olasılığı artar: yeni bildirim kanalı ya "
                     "da kayıt pratiği kayıtlı sayıyı yükseltir",
        "sinama": "artış dönem boyunca var olan (sürekli) kanallarda da görülüyor mu",
        "etki": "yüksek",
        "sonraki_kanit": "kayıtlarda bildirim kanalı/kaynak alanı",
        "kaynak": "Maltz (1977); kayıt dışı suç ve bildirim eğilimi",
    },
    "R-MEVSIM": {
        "ad": "Mevsimsellik",
        "turler": ("ARTIS",),
        "mekanizma": "dönem düşük mevsimde başlayıp yüksek mevsimde bitince trend "
                     "yükseliş gibi görünür",
        "sinama": "son 12 ay ile önceki 12 ayın aynı takvim aylarının eşli karşılaştırması",
        "etki": "yüksek",
        "sonraki_kanit": "en az 24 aylık veri (aynı ayların yıllar arası karşılaştırması)",
        "kaynak": "Boba Santos, Crime Analysis with Crime Mapping (zaman desenleri)",
    },
    "R-PAYDA": {
        "ad": "Risk altındaki nüfus / hedef değişimi (payda)",
        "turler": ("YOGUNLASMA",),
        "mekanizma": "yoğunlaşma, olayların değil hedeflerin (konut, işyeri, nüfus) "
                     "yoğunluğunu yansıtabilir",
        "sinama": "risk altındaki nüfus/hedef verisiyle oran",
        "etki": "yüksek",
        "sonraki_kanit": "bölge/hücre başına risk altındaki nüfus ya da hedef sayısı",
        "kaynak": "Clarke & Eck, Crime Analysis for Problem Solvers (oran ve payda)",
    },
    "R-VERI": {
        "ad": "Veri kalitesi (geçersiz tarih/koordinat, varsayılan konum yığılması, boş MO)",
        "turler": ("ARTIS", "YOGUNLASMA", "SERI", "ETKI"),
        "mekanizma": "kayıt hataları deseni üretir ya da gizler",
        "sinama": "soru türüne göre alan geçerliliği ve yığılma denetimi",
        "etki": "yüksek",
        "sonraki_kanit": "veri temizliği ve geçersiz kayıtların kaynağının açıklanması",
        "kaynak": "kalite kapısı (kalite/kapi.py)",
    },
    "R-ORTAK-MO": {
        "ad": "Yaygın yöntem (taban oranı)",
        "turler": ("SERI",),
        "mekanizma": "bağımsız failler çok yaygın bir yöntemi paylaşır",
        "sinama": "paylaşılan davranışın ayırt ediciliği (A4.8, FDR)",
        "etki": "yüksek",
        "sonraki_kanit": "daha ayrıntılı ve standart MO kodlaması",
        "kaynak": "Bennell & Canter (2002); Bennell & Jones (2005)",
    },
    "R-TESADUF-YAKINLIK": {
        "ad": "Farklı faillerin uzay-zaman yakınlığı",
        "turler": ("SERI",),
        "mekanizma": "yakın zaman ve yerdeki olaylar farklı faillerin işi olabilir "
                     "(yakın tekrar)",
        "sinama": "MO kanıt hattının uzay-zaman hattıyla örtüşmesi (A4.8)",
        "etki": "orta",
        "sonraki_kanit": "fiziksel/dijital iz ya da tanık bilgisi (insan incelemesi)",
        "kaynak": "Johnson vd. (2007) yakın tekrar",
    },
    "R-ESZAMANLI": {
        "ad": "Eşzamanlı genel değişim (tarih etkisi)",
        "turler": ("ETKI",),
        "mekanizma": "mevsim, ekonomi, politika ya da başka bir olay müdahaleyle aynı "
                     "anda her yerde değişim yaratır; müdahale bölgesindeki düşüş ona ait "
                     "olmayabilir",
        "sinama": "kontrol bölgesiyle oran oranları farkı (farkların farkı)",
        "etki": "yüksek",
        "sonraki_kanit": "karşılaştırılabilir bir kontrol bölgesinin verisi",
        "kaynak": "Shadish, Cook & Campbell (2002) — tarih tehdidi",
    },
    "R-ORTALAMAYA-DONUS": {
        "ad": "Ortalamaya dönüş (seçim etkisi)",
        "turler": ("ETKI",),
        "mekanizma": "bölge olağandışı yüksek bir dönemden sonra müdahale için "
                     "seçildiyse düşüş kendiliğinden gelir",
        "sinama": "müdahale öncesi son 3 ayın önceki temel döneme (kontrol varsa ona "
                  "göre) oranı",
        "etki": "yüksek",
        "sonraki_kanit": "daha uzun müdahale öncesi dönem",
        "kaynak": "Campbell & Ross (1968) — Connecticut hız denetimi",
    },
    "R-YER-DEGISTIRME": {
        "ad": "Yer değiştirme (suçun komşu bölgeye kayması)",
        "turler": ("ETKI",),
        "mekanizma": "suç ortadan kalkmaz, tampon bölgeye kayar; net etki sıfıra yakın "
                     "olabilir",
        "sinama": "tampon bölgenin kontrole göre oran oranları farkı",
        "etki": "yüksek",
        "sonraki_kanit": "müdahale bölgesini çevreleyen tampon bölgenin verisi",
        "kaynak": "Weisburd vd. (2006); Wheeler & Ratcliffe (2018) WDD",
    },
}

SIRA = tuple(KATALOG)


def uygulanabilir(soru_turu):
    """Soru türüne uygulanabilen rakip kodları (katalog sırasıyla)."""
    return [k for k in SIRA if soru_turu in KATALOG[k]["turler"]]
