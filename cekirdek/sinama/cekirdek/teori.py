# -*- coding: utf-8 -*-
"""
teori.py — kriminolojik teori yorum katmanı (Chainey Böl.1 meta-dersi:
"analiz çıktıları TEORİ ile yorumlanmalı; aksi halde ne yapılacağı belirsiz").

Bir istatistiksel BULGU türünü ilgili teorilere + yorum + müdahale yönü +
uyarıya eşler. Amaç sayıyı eyleme çevirmek: bir sıcak nokta "neden" oradadır?
Teori bunu açıklar, açıklama da müdahaleyi belirler.

Teoriler (Böl.1): sosyal düzensizlik, kolektif yeterlik, rutin faaliyet,
rasyonel tercih, suç deseni teorisi, en-az-çaba, suç üreticileri/çekicileri.
"""
from __future__ import annotations

from typing import Any, Dict, List

# bulgu türü -> {teoriler, yorum, oneri, uyari}
_TEORI: Dict[str, Dict[str, Any]] = {
    "kalici_sicak_nokta": {
        "teoriler": ["rutin faaliyet", "suç çekicileri", "suç üreticileri"],
        "yorum": ("Kalıcı sıcak nokta, istikrarlı bir fırsat yapısına işaret "
                  "eder: ya suça ELVERİŞLİ hedef+fail buluşması süreklidir (suç "
                  "çekicisi, ör. eğlence bölgesi) ya da çok sayıda insanı çeken "
                  "bir üretici (ör. terminal) yakınında fırsat suçları oluşur."),
        "oneri": ("Yer-temelli kalıcı müdahale (çevresel tasarım, hedef "
                  "sertleştirme, düzenli varlık); kısa vadeli devriye yetmez."),
        "uyari": "Kalıcılık kaydın sürekliliğinden de gelebilir; raporlama yanlılığını ele.",
    },
    "yeni_sicak_nokta": {
        "teoriler": ["suç deseni teorisi", "rutin faaliyet"],
        "yorum": ("Yükselen/yeni sıcak nokta genellikle ÇEVRESEL bir değişimin "
                  "işaretidir: yeni bir aktivite düğümü, değişen hareket "
                  "güzergâhı veya yeni bir fırsat açılmış olabilir."),
        "oneri": "Ne DEĞİŞTİĞİNİ araştır (yeni tesis, etkinlik, güzergâh); erken müdahale fırsatı.",
        "uyari": "Düşük tabanlı küçük sayısal artışlar yanıltıcı olabilir; anlamlılığı kontrol et.",
    },
    "mekansal_aykiri": {
        "teoriler": ["rasyonel tercih", "suç deseni teorisi"],
        "yorum": ("Çevresinden farklı yüksek ada (HL), MİKRO-YER'e özgü bir "
                  "etkeni gösterir: tek bir bina/tesis, belirli bir hedef "
                  "yoğunluğu ya da yerel bir suç çekicisi."),
        "oneri": "Saha düzeyinde nokta incelemesi; o tekil yerin özelliklerini araştır.",
        "uyari": "Tek nokta anomalisi istatistiksel olarak kararsız olabilir; permütasyon anlamlılığına bak.",
    },
    "mukerrer_magduriyet": {
        "teoriler": ["rasyonel tercih", "en-az-çaba"],
        "yorum": ("Aynı hedefin tekrar mağdur olması, faili ödüllendiren "
                  "'boost' etkisidir: bilinen, kolay, kârlı hedef tekrar "
                  "seçilir (least-effort + öğrenilmiş fırsat)."),
        "oneri": "Hızlı hedef sertleştirme; ilk olaydan sonraki kısa pencere kritik.",
        "uyari": "Tekrarı doğru kişi/adres eşlemesiyle doğrula (kayıt hatası tekrarı şişirir).",
    },
    "risk_faktoru_colocation": {
        "teoriler": ["suç deseni teorisi", "rutin faaliyet"],
        "yorum": ("Birden çok risk faktörünün bir arada olması, aktivite "
                  "düğüm/güzergâh/kenarlarının kesiştiği KALICI risk ortamıdır; "
                  "suç henüz olmasa da koşullar elverişlidir."),
        "oneri": "Önleyici çevresel tasarım ve faktör-temelli hedefleme (suç beklemeden).",
        "uyari": "Risk = olasılık, kesinlik değil; RTM tahmin değil koşul haritasıdır.",
    },
    "kumelenme": {
        "teoriler": ["sosyal düzensizlik", "kolektif yeterlik"],
        "yorum": ("Anlamlı mekânsal kümelenme, suçun rastgele olmadığını; "
                  "altta yapısal etkenler (zayıf kolektif yeterlik, sosyal "
                  "düzensizlik) veya yoğun fırsat bulunduğunu düşündürür."),
        "oneri": "Yapısal/toplumsal müdahaleler (sadece bastırma değil) ve kök-neden analizi.",
        "uyari": "Korelasyon nedensellik değildir; kümelenme 'neden'i açıklamaz, işaret eder.",
    },
    "zamansal_oruntu": {
        "teoriler": ["rutin faaliyet"],
        "yorum": ("Belirli saat/gün yoğunlaşması, fail-hedef-koruyucu buluşma "
                  "ritminin (günlük rutinler) sonucudur."),
        "oneri": "Kaynağı yoğun zaman dilimlerine kaydır (zaman-temelli devriye).",
        "uyari": "Zaman deseni mevsimsellik/etkinlikle karışabilir; yeterli dönem kullan.",
    },
}

BULGU_TURLERI = sorted(_TEORI)


def yorumla(bulgu: str) -> Dict[str, Any]:
    """Bir bulgu türü için kriminolojik teori yorumu döndürür.
    Args: bulgu (BULGU_TURLERI'nden biri).
    Returns: {bulgu, teoriler, yorum, oneri, uyari} veya bilinmeyen için liste.
    """
    t = _TEORI.get(bulgu)
    if not t:
        return {"hata": f"bilinmeyen bulgu: '{bulgu}'",
                "gecerli_bulgular": BULGU_TURLERI}
    return {"bulgu": bulgu, **t}
