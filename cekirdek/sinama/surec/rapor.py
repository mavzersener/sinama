# -*- coding: utf-8 -*-
"""
rapor.py — Analiz ürünü üretimi (Ch 9/17: ürün kültürü).
Analiz çıktısı değil, ÜRÜN üretir: taktik brifing (günlük, saha) ve
stratejik değerlendirme (dönemsel, komuta). Belirsizlik notu zorunludur.
"""

import time

from ..cekirdek.hatalar import KullanimHatasi


def _satir_liste(ogeler, n=5):
    return ogeler[:n]


def taktik_brifing(talep, kalite=None, hotspot=None, gun_saat=None,
                   yakin_tekrar=None, power_few=None, ek_notlar=None,
                   belirsizlik=None):
    """
    Taktik brifing (Markdown): devriye görevlendirmesine yönelik günlük ürün.
    gun_saat: gün×saat yoğunluk matrisi (rapora gömülür).
    belirsizlik: zorunlu alan — komutana sınırların beyanı (Ch 17).
    """
    if not belirsizlik:
        raise KullanimHatasi("belirsizlik notu zorunludur — ürün, "
                         "sınırlarını beyan etmeden çıkamaz (Ch 17 ilkesi)",
                         oneri="verinin ve yöntemin sınırlarını bir-iki "
                              "cümleyle yazın")
    b = []
    b.append(f"# Taktik Brifing — {time.strftime('%d.%m.%Y')}")
    b.append(f"**Talep:** {talep.get('karar', '-')} | "
             f"**Kapsam:** {talep.get('kapsam', '-')} | "
             f"**Talep eden:** {talep.get('soran', '-')}\n")
    if kalite:
        b.append("## Veri durumu")
        b.append(f"- n={kalite.get('n')}, kesildi={kalite.get('kesildi', False)}")
        for u in (kalite.get("uyarilar") or [])[:5]:
            b.append(f"- ⚠ {u}")
        b.append("")
    if hotspot:
        b.append("## Öncelikli bölgeler (hotspot)")
        for h in _satir_liste(hotspot):
            b.append(f"- ({h.get('lat')}, {h.get('lon')}) — {h.get('adet', h.get('yogunluk', ''))} olay/yoğunluk")
        b.append("")
    if gun_saat:
        b.append("## En riskli zaman dilimleri")
        for d in _satir_liste(gun_saat, 3):
            b.append(f"- Gün {d.get('gun')} saat {d.get('saat')} — {d.get('adet')} olay")
        b.append("")
    if yakin_tekrar is not None:
        b.append("## Yakın-tekrar riski")
        if isinstance(yakin_tekrar, dict) and "anlamlilik" in yakin_tekrar:
            a = yakin_tekrar["anlamlilik"]
            b.append(f"- Gözlenen/beklenen oran: {a.get('oran')} (p={a.get('p')}) — {a.get('yorum')}")
        else:
            b.append(f"- {len(yakin_tekrar)} yakın-tekrar çifti tespit edildi")
        b.append("")
    if power_few:
        b.append("## Power few (zararın %50'sini üreten birimler)")
        b.append(f"- {power_few.get('birim_sayisi')}/{power_few.get('toplam_birim')} birim "
                 f"(yoğunlaşma {power_few.get('yogunlasma_orani')})")
        for x in _satir_liste(power_few.get("birimler", [])):
            b.append(f"- {x}")
        b.append("")
    b.append("## Belirsizlik ve sınırlar")
    for u in (belirsizlik if isinstance(belirsizlik, list) else [belirsizlik]):
        b.append(f"- {u}")
    for n in (ek_notlar or []):
        b.append(f"- {n}")
    b.append("\n*Bu ürün karar desteğidir; insan onayı olmadan eyleme "
             "dönüştürülemez (DOKTRIN kural 3).*")
    return "\n".join(b)


def stratejik_degerlendirme(talep, trend=None, oranlar=None, anomali=None,
                            degerlendirme=None, guc=None, belirsizlik=None):
    """Stratejik değerlendirme (Markdown): dönemsel komuta ürünü."""
    if not belirsizlik:
        raise KullanimHatasi("belirsizlik notu zorunludur",
                         oneri="verinin ve yöntemin sınırlarını yazın")
    b = [f"# Stratejik Değerlendirme — {time.strftime('%d.%m.%Y')}"]
    b.append(f"**Talep:** {talep.get('karar', '-')} | "
             f"**Kapsam:** {talep.get('kapsam', '-')}\n")
    if trend:
        b.append(f"## Eğilim\n- {trend}")
    if oranlar:
        b.append("## Bölge oranları (100.000 nüfus, GA'lı)")
        for o in _satir_liste(oranlar):
            ga = f"[{o.get('ga_alt')}–{o.get('ga_ust')}]" if o.get("ga_alt") is not None else ""
            b.append(f"- {o.get('bolge')}: {o.get('oran_100binde')} {ga}")
    if anomali:
        b.append("## Anlamlı anomaliler (FDR q ile)")
        for a in _satir_liste(anomali.get("anlamli", anomali) if isinstance(anomali, dict) else anomali):
            b.append(f"- {a.get('bolge')}: gözlenen {a.get('gozlenen')} (p={a.get('p')}, q={a.get('q')})")
    if degerlendirme:
        b.append(f"## Müdahale değerlendirmesi\n- {degerlendirme}")
    if guc:
        b.append(f"## Güç/örneklem notu\n- {guc}")
    b.append("## Belirsizlik ve sınırlar")
    for u in (belirsizlik if isinstance(belirsizlik, list) else [belirsizlik]):
        b.append(f"- {u}")
    b.append("\n*Bu ürün karar desteğidir; insan onayı olmadan eyleme "
             "dönüştürülemez.*")
    return "\n".join(b)


def muhakeme_izi(manifesto):
    """
    Katman 3 (v6.2, Faz 1.6): oturumun muhakeme izini Markdown olarak üretir.

    İlke (birleşik belge §4.4): olgu (K1/K2 — araç çıktısı, gate kararı)
    ile gerekçe (K3 — modelin hipotez/yorum/çıkarım/alternatifleri)
    GÖRSEL OLARAK AYRI sunulur. Gerekçe bölümü olgu gibi okunmamalıdır;
    bu yüzden ayrı başlık + blockquote biçimi kullanılır.
    """
    b = ["## Muhakeme İzi", "",
         "*Bu bölümdeki bloklar iki türdedir: **OLGU** (aracın ölçtüğü) ve",
         "**GEREKÇE** (analistin/modelin yorumu). Gerekçe olgu değildir;*",
         "*sınanabilir, reddedilebilir ve insan onayına tabidir.*", "",
         "*Gerekçe ve analitik ayrıntılar yerel gizli manifesto kaynağından "
         "okunur; olay akışı yalnız güvenli özet ve commitment taşır.*", ""]
    adimlar = [g for g in manifesto.get("gecmis", [])
               if g.get("faz") == "ANALIZ" and g.get("arac") != "analize_gec"]
    if not adimlar:
        b.append("_Bu oturumda analiz adımı yok._")
        return "\n".join(b)
    for i, a in enumerate(adimlar, 1):
        b.append(f"### Adım {i} — `{a.get('arac')}` ({a.get('zaman', '-')})")
        b.append(f"**OLGU (K1/K2):** {a.get('ozet', '-')}")
        g = a.get("gerekce")
        if g:
            b.append("")
            b.append("> **GEREKÇE (K3 — model/analist yorumu, olgu değil)**")
            if g.get("hipotez"):
                b.append(f"> - **Hipotez:** {g['hipotez']}")
            if g.get("yorum"):
                b.append(f"> - **Yorum:** {g['yorum']}")
            if g.get("cikarim"):
                b.append(f"> - **Çıkarım:** {g['cikarim']}")
            if g.get("alternatifler"):
                alt = g["alternatifler"]
                if isinstance(alt, list):
                    alt = "; ".join(str(x) for x in alt)
                b.append(f"> - **Alternatif açıklamalar:** {alt}")
        else:
            b.append("")
            b.append("> _Gerekçe kaydedilmemiş (keşif oturumu)._")
        b.append("")
    return "\n".join(b)
