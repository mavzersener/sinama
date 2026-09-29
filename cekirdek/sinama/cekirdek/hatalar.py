# -*- coding: utf-8 -*-
r"""
cekirdek/hatalar.py — hata taksonomisi (v6.5, GELISME_PLANI H2.1).

Tek kök: SucAnaliziHatasi. Her hata bir "tip" taşır; arayüz bu tipi
istemciye yapısal olarak bildirir (HATA [tip]: mesaj + ÖNERİ). Amaç:
istemcinin (yerel agent) hatadan DÜZELTİCİ EYLEM seçebilmesi — no-code
hedefinin omurgası.

Katmanlar bu modülü import eder (cekirdek en alttadır, döngü yok):
  kalite.KapiRed        — politika/fitness reddi (kapı)
  surec.DonguHatasi     — süreç ihlali (PPDAC durum makinesi)
  GuvenlikHatasi        — yol hapsi / boyut / uzantı (guvenlik.py)
  VeriHatasi            — veriyle düzeltilebilir (yetersiz/uygunsuz veri)
  KullanimHatasi        — şemayı geçen ama sözleşmeyi bozan çağrı
Beklenmedik her şey "sistem" tipine düşer (sunucu eşler).

Geriye uyumluluk: VeriHatasi/GuvenlikHatasi/KullanimHatasi ValueError'dan
da türetilir — mevcut assertRaises(ValueError) kanıtları bozulmaz.
"""


class SucAnaliziHatasi(Exception):
    """Tüm alan hatalarının kökü. tip: istemciye bildirilen sınıf."""
    tip = "sistem"

    def __init__(self, mesaj, oneri=None):
        super().__init__(mesaj)
        self.oneri = oneri  # düzeltici eylem önerisi (opsiyonel)


class VeriHatasi(SucAnaliziHatasi, ValueError):
    """Veri bu analiz için yetersiz/uygunsuz; kullanıcı veriyi veya
    yöntemi değiştirerek düzeltebilir (örn. tekil matris, sıfır maruz
    kalma)."""
    tip = "veri"


class GuvenlikHatasi(SucAnaliziHatasi, ValueError):
    """Güvenlik sınırı ihlali: yol hapsi dışı, boyut/uzantı sınırı.
    Denetimde (audit) ayrıca izlenir."""
    tip = "guvenlik"


class KullanimHatasi(SucAnaliziHatasi, ValueError):
    """Şemayı geçen ama aracın sözleşmesini bozan çağrı (eksik girdi
    kombinasyonu, belirsizlik notu yokluğu vb.)."""
    tip = "kullanim"
