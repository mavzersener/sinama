// OTOMATİK ÜRETİLDİ — elle düzenlemeyin.
// Üretici: scripts/generate_suc_nodes.py (kaynak: suc_analizi arayuz/araclar.py)
import type { NodeDefinition } from './nodeDefinitions';

export const sucAnaliziNodes: NodeDefinition[] = [
  {
    "type": "suc_agirlikli_kde",
    "label": "agirlikli kde",
    "category": "Suç Analizi",
    "icon": "Shield",
    "description": "Zarar-ağırlıklı KDE (harm-spot haritası)",
    "color": "#dc2626",
    "inputs": 1,
    "outputs": 1,
    "defaultConfig": {
      "bant_km": 0.4,
      "hucre_km": 0.3,
      "tur_alan": "tur",
      "agirlik_yolu": ""
    },
    "configFields": [
      {
        "name": "bant_km",
        "label": "bant_km",
        "type": "number",
        "default": 0.4
      },
      {
        "name": "hucre_km",
        "label": "hucre_km",
        "type": "number",
        "default": 0.3
      },
      {
        "name": "tur_alan",
        "label": "tur_alan",
        "type": "text",
        "default": "tur"
      },
      {
        "name": "agirlik_yolu",
        "label": "agirlik_yolu",
        "type": "text"
      }
    ]
  },
  {
    "type": "suc_analiz_oner",
    "label": "analiz oner",
    "category": "Suç Analizi",
    "icon": "Shield",
    "description": "Karar ağacı önericisi: veri yapısı + soruya göre uygun analizleri (mevcut/yok) sıralar",
    "color": "#dc2626",
    "inputs": 1,
    "outputs": 1,
    "defaultConfig": {
      "soru": "",
      "maks": 6
    },
    "configFields": [
      {
        "name": "soru",
        "label": "soru",
        "type": "text",
        "placeholder": "kullanıcının sorusu (opsiyonel)"
      },
      {
        "name": "maks",
        "label": "maks",
        "type": "number",
        "default": 6
      }
    ]
  },
  {
    "type": "suc_anova",
    "label": "anova",
    "category": "Suç Analizi",
    "icon": "Shield",
    "description": "Tek yönlü ANOVA + eta² + Bonferroni pairwise",
    "color": "#dc2626",
    "inputs": 1,
    "outputs": 1,
    "defaultConfig": {
      "gruplar": "",
      "alan": "",
      "grup_alan": ""
    },
    "configFields": [
      {
        "name": "gruplar",
        "label": "gruplar",
        "type": "text"
      },
      {
        "name": "alan",
        "label": "alan",
        "type": "text"
      },
      {
        "name": "grup_alan",
        "label": "grup_alan",
        "type": "text"
      }
    ]
  },
  {
    "type": "suc_aoristik",
    "label": "aoristik",
    "category": "Suç Analizi",
    "icon": "Shield",
    "description": "Aoristik saat dağılımı: belirsiz (aralık) olay zamanları için",
    "color": "#dc2626",
    "inputs": 1,
    "outputs": 1,
    "defaultConfig": {
      "bas_alan": "baslangic",
      "bit_alan": "bitis"
    },
    "configFields": [
      {
        "name": "bas_alan",
        "label": "bas_alan",
        "type": "text",
        "default": "baslangic"
      },
      {
        "name": "bit_alan",
        "label": "bit_alan",
        "type": "text",
        "default": "bitis"
      }
    ]
  },
  {
    "type": "suc_ay_serisi",
    "label": "ay serisi",
    "category": "Suç Analizi",
    "icon": "Shield",
    "description": "Ay bazlı olay serisi",
    "color": "#dc2626",
    "inputs": 1,
    "outputs": 1,
    "defaultConfig": {},
    "configFields": []
  },
  {
    "type": "suc_benford",
    "label": "benford",
    "category": "Suç Analizi",
    "icon": "Shield",
    "description": "Benford yasası: uydurma sayı tespiti",
    "color": "#dc2626",
    "inputs": 1,
    "outputs": 1,
    "defaultConfig": {
      "alan": ""
    },
    "configFields": [
      {
        "name": "alan",
        "label": "alan",
        "type": "text",
        "required": true
      }
    ]
  },
  {
    "type": "suc_bolge_anomali",
    "label": "bolge anomali",
    "category": "Suç Analizi",
    "icon": "Shield",
    "description": "Bölge bazında Poisson anomali (p-değerli)",
    "color": "#dc2626",
    "inputs": 1,
    "outputs": 1,
    "defaultConfig": {
      "bolge_alan": ""
    },
    "configFields": [
      {
        "name": "bolge_alan",
        "label": "bolge_alan",
        "type": "text",
        "required": true
      }
    ]
  },
  {
    "type": "suc_bulanik_eslesme",
    "label": "bulanik eslesme",
    "category": "Suç Analizi",
    "icon": "Shield",
    "description": "İsim/adres yazım farklarına dayanıklı eşleşme",
    "color": "#dc2626",
    "inputs": 1,
    "outputs": 1,
    "defaultConfig": {
      "alan": "",
      "hedef": "",
      "esik": 0.8,
      "alanlar": ""
    },
    "configFields": [
      {
        "name": "alan",
        "label": "alan",
        "type": "text",
        "required": true
      },
      {
        "name": "hedef",
        "label": "hedef",
        "type": "text",
        "required": true
      },
      {
        "name": "esik",
        "label": "esik",
        "type": "number",
        "default": 0.8
      },
      {
        "name": "alanlar",
        "label": "alanlar",
        "type": "text",
        "placeholder": "alan beyaz listesi (verilmezse güvenli çekirdek)"
      }
    ]
  },
  {
    "type": "suc_capraz_tablo",
    "label": "capraz tablo",
    "category": "Suç Analizi",
    "icon": "Shield",
    "description": "İki kategorik alanın çapraz tablosu",
    "color": "#dc2626",
    "inputs": 1,
    "outputs": 1,
    "defaultConfig": {
      "a": "",
      "b": ""
    },
    "configFields": [
      {
        "name": "a",
        "label": "a",
        "type": "text",
        "required": true
      },
      {
        "name": "b",
        "label": "b",
        "type": "text",
        "required": true
      }
    ]
  },
  {
    "type": "suc_cografi_profil",
    "label": "cografi profil",
    "category": "Suç Analizi",
    "icon": "Shield",
    "description": "Coğrafi profilleme: seri suçtan failin olası çapa (ikamet) bölgesi",
    "color": "#dc2626",
    "inputs": 1,
    "outputs": 1,
    "defaultConfig": {
      "hucre_km": 0.3,
      "decay_km": "",
      "buffer_km": 0
    },
    "configFields": [
      {
        "name": "hucre_km",
        "label": "hucre_km",
        "type": "number",
        "default": 0.3
      },
      {
        "name": "decay_km",
        "label": "decay_km",
        "type": "number",
        "placeholder": "azalım ölçeği (boş=otomatik)"
      },
      {
        "name": "buffer_km",
        "label": "buffer_km",
        "type": "number",
        "default": 0,
        "placeholder": "Rossmo tampon bölgesi (0=Dragnet)"
      }
    ]
  },
  {
    "type": "suc_coklu_regresyon",
    "label": "coklu regresyon",
    "category": "Suç Analizi",
    "icon": "Shield",
    "description": "Çoklu OLS: beta, t, p, R², düzeltilmiş R², F, VIF",
    "color": "#dc2626",
    "inputs": 1,
    "outputs": 1,
    "defaultConfig": {
      "X": "",
      "y": "",
      "hedef": "",
      "degiskenler": ""
    },
    "configFields": [
      {
        "name": "X",
        "label": "X",
        "type": "text",
        "placeholder": "virgülle ayrılmış liste"
      },
      {
        "name": "y",
        "label": "y",
        "type": "text",
        "placeholder": "virgülle ayrılmış liste"
      },
      {
        "name": "hedef",
        "label": "hedef",
        "type": "text"
      },
      {
        "name": "degiskenler",
        "label": "degiskenler",
        "type": "text",
        "placeholder": "virgülle ayrılmış liste"
      }
    ]
  },
  {
    "type": "suc_cusum",
    "label": "cusum",
    "category": "Suç Analizi",
    "icon": "Shield",
    "description": "Günlük seride kalıcı artış (CUSUM) alarmları",
    "color": "#dc2626",
    "inputs": 1,
    "outputs": 1,
    "defaultConfig": {},
    "configFields": []
  },
  {
    "type": "suc_dagilim_olculeri",
    "label": "dagilim olculeri",
    "category": "Suç Analizi",
    "icon": "Shield",
    "description": "Sağlam dağılım ölçüleri: IQR, MAD, CV",
    "color": "#dc2626",
    "inputs": 1,
    "outputs": 1,
    "defaultConfig": {
      "degerler": "",
      "alan": ""
    },
    "configFields": [
      {
        "name": "degerler",
        "label": "degerler",
        "type": "text",
        "placeholder": "virgülle ayrılmış liste"
      },
      {
        "name": "alan",
        "label": "alan",
        "type": "text"
      }
    ]
  },
  {
    "type": "suc_dongu_veri",
    "label": "dongu veri",
    "category": "Suç Analizi",
    "icon": "Shield",
    "description": "Döngü VERİ fazı: profil + fitness gate (otomatik)",
    "color": "#dc2626",
    "inputs": 1,
    "outputs": 1,
    "defaultConfig": {
      "oturum_id": "",
      "analiz": "",
      "sayisal_alan": ""
    },
    "configFields": [
      {
        "name": "oturum_id",
        "label": "oturum_id",
        "type": "text",
        "required": true
      },
      {
        "name": "analiz",
        "label": "analiz",
        "type": "text"
      },
      {
        "name": "sayisal_alan",
        "label": "sayisal_alan",
        "type": "text"
      }
    ]
  },
  {
    "type": "suc_endeks_hesapla",
    "label": "endeks hesapla",
    "category": "Suç Analizi",
    "icon": "Shield",
    "description": "Ağırlıklı bileşik endeks (Index of Disorder)",
    "color": "#dc2626",
    "inputs": 1,
    "outputs": 1,
    "defaultConfig": {
      "gostergeler": "",
      "agirliklar": "",
      "tersler": ""
    },
    "configFields": [
      {
        "name": "gostergeler",
        "label": "gostergeler",
        "type": "text",
        "placeholder": "virgülle ayrılmış liste",
        "required": true
      },
      {
        "name": "agirliklar",
        "label": "agirliklar",
        "type": "text"
      },
      {
        "name": "tersler",
        "label": "tersler",
        "type": "text",
        "placeholder": "virgülle ayrılmış liste"
      }
    ]
  },
  {
    "type": "suc_esitlik_analizi",
    "label": "esitlik analizi",
    "category": "Suç Analizi",
    "icon": "Shield",
    "description": "Dağılım eşitsizliği: Gini + bölgesel disparite (adalet-kısıtlı kaynak)",
    "color": "#dc2626",
    "inputs": 1,
    "outputs": 1,
    "defaultConfig": {
      "alan": ""
    },
    "configFields": [
      {
        "name": "alan",
        "label": "alan",
        "type": "text",
        "placeholder": "bölge/grup alanı (ör. grid_id, bolge)",
        "required": true
      }
    ]
  },
  {
    "type": "suc_frekans",
    "label": "frekans",
    "category": "Suç Analizi",
    "icon": "Shield",
    "description": "Bir alanın değer dağılımı",
    "color": "#dc2626",
    "inputs": 1,
    "outputs": 1,
    "defaultConfig": {
      "alan": ""
    },
    "configFields": [
      {
        "name": "alan",
        "label": "alan",
        "type": "text",
        "required": true
      }
    ]
  },
  {
    "type": "suc_grid_hotspot",
    "label": "grid hotspot",
    "category": "Suç Analizi",
    "icon": "Shield",
    "description": "Grid hotspot: hücre başına olay sayısı",
    "color": "#dc2626",
    "inputs": 1,
    "outputs": 1,
    "defaultConfig": {
      "hucre_km": 0.5
    },
    "configFields": [
      {
        "name": "hucre_km",
        "label": "hucre_km",
        "type": "number",
        "default": 0.5
      }
    ]
  },
  {
    "type": "suc_gun_dagilimi",
    "label": "gun dagilimi",
    "category": "Suç Analizi",
    "icon": "Shield",
    "description": "Haftanın günü dağılımı (0=Pzt)",
    "color": "#dc2626",
    "inputs": 1,
    "outputs": 1,
    "defaultConfig": {},
    "configFields": []
  },
  {
    "type": "suc_gun_saat_analizi",
    "label": "gun saat analizi",
    "category": "Suç Analizi",
    "icon": "Shield",
    "description": "Gün×saat ısı matrisi + en riskli dilimler",
    "color": "#dc2626",
    "inputs": 1,
    "outputs": 1,
    "defaultConfig": {},
    "configFields": []
  },
  {
    "type": "suc_hacim_zarar_karsilastir",
    "label": "hacim zarar karsilastir",
    "category": "Suç Analizi",
    "icon": "Shield",
    "description": "Hacim vs zarar sıralama ayrışması",
    "color": "#dc2626",
    "inputs": 1,
    "outputs": 1,
    "defaultConfig": {
      "grup_alan": "",
      "tur_alan": "tur",
      "agirlik_yolu": ""
    },
    "configFields": [
      {
        "name": "grup_alan",
        "label": "grup_alan",
        "type": "text",
        "required": true
      },
      {
        "name": "tur_alan",
        "label": "tur_alan",
        "type": "text",
        "default": "tur"
      },
      {
        "name": "agirlik_yolu",
        "label": "agirlik_yolu",
        "type": "text"
      }
    ]
  },
  {
    "type": "suc_kde_yogunluk",
    "label": "kde yogunluk",
    "category": "Suç Analizi",
    "icon": "Shield",
    "description": "KDE ısı yoğunluğu (saf Python)",
    "color": "#dc2626",
    "inputs": 1,
    "outputs": 1,
    "defaultConfig": {
      "bant_km": 0.4,
      "hucre_km": 0.3
    },
    "configFields": [
      {
        "name": "bant_km",
        "label": "bant_km",
        "type": "number",
        "default": 0.4
      },
      {
        "name": "hucre_km",
        "label": "hucre_km",
        "type": "number",
        "default": 0.3
      }
    ]
  },
  {
    "type": "suc_kendall",
    "label": "kendall",
    "category": "Suç Analizi",
    "icon": "Shield",
    "description": "Kendall tau-b ordinal ilişki",
    "color": "#dc2626",
    "inputs": 1,
    "outputs": 1,
    "defaultConfig": {
      "x": "",
      "y": ""
    },
    "configFields": [
      {
        "name": "x",
        "label": "x",
        "type": "text",
        "placeholder": "virgülle ayrılmış liste"
      },
      {
        "name": "y",
        "label": "y",
        "type": "text",
        "placeholder": "virgülle ayrılmış liste"
      }
    ]
  },
  {
    "type": "suc_ki_kare_testi",
    "label": "ki kare testi",
    "category": "Suç Analizi",
    "icon": "Shield",
    "description": "Ki-kare bağımsızlık testi (Yates/Cochran destekli)",
    "color": "#dc2626",
    "inputs": 1,
    "outputs": 1,
    "defaultConfig": {
      "a": "",
      "b": "",
      "yates": false
    },
    "configFields": [
      {
        "name": "a",
        "label": "a",
        "type": "text",
        "required": true
      },
      {
        "name": "b",
        "label": "b",
        "type": "text",
        "required": true
      },
      {
        "name": "yates",
        "label": "yates",
        "type": "boolean",
        "default": false
      }
    ]
  },
  {
    "type": "suc_knox_tablosu",
    "label": "knox tablosu",
    "category": "Suç Analizi",
    "icon": "Shield",
    "description": "Knox uzay-zaman tablosu; sim>0 ile MC anlamlılık",
    "color": "#dc2626",
    "inputs": 1,
    "outputs": 1,
    "defaultConfig": {
      "mesafe_km": 0.4,
      "gun": 14,
      "sim": 0
    },
    "configFields": [
      {
        "name": "mesafe_km",
        "label": "mesafe_km",
        "type": "number",
        "default": 0.4
      },
      {
        "name": "gun",
        "label": "gun",
        "type": "number",
        "default": 14
      },
      {
        "name": "sim",
        "label": "sim",
        "type": "number",
        "default": 0
      }
    ]
  },
  {
    "type": "suc_konsantrasyon_dagilimi",
    "label": "konsantrasyon dagilimi",
    "category": "Suç Analizi",
    "icon": "Shield",
    "description": "CCDI: suç artışı eski sıcak noktalardan mı (yoğunlaşma) yeni alanlardan mı (dağılma)",
    "color": "#dc2626",
    "inputs": 1,
    "outputs": 1,
    "defaultConfig": {
      "bolge_alan": "",
      "zaman_alan": ""
    },
    "configFields": [
      {
        "name": "bolge_alan",
        "label": "bolge_alan",
        "type": "text",
        "required": true
      },
      {
        "name": "zaman_alan",
        "label": "zaman_alan",
        "type": "text",
        "required": true
      }
    ]
  },
  {
    "type": "suc_kontrol_grafigi",
    "label": "kontrol grafigi",
    "category": "Suç Analizi",
    "icon": "Shield",
    "description": "Günlük seride ±3σ aşım günleri",
    "color": "#dc2626",
    "inputs": 1,
    "outputs": 1,
    "defaultConfig": {},
    "configFields": []
  },
  {
    "type": "suc_koordinat_maskele",
    "label": "koordinat maskele",
    "category": "Suç Analizi",
    "icon": "Shield",
    "description": "KVKK yayın maskesi: koordinatlara jitter uygular",
    "color": "#dc2626",
    "inputs": 1,
    "outputs": 1,
    "defaultConfig": {
      "yaricap_m": 200,
      "seed": ""
    },
    "configFields": [
      {
        "name": "yaricap_m",
        "label": "yaricap_m",
        "type": "number",
        "default": 200
      },
      {
        "name": "seed",
        "label": "seed",
        "type": "number"
      }
    ]
  },
  {
    "type": "suc_kruskal_wallis",
    "label": "kruskal wallis",
    "category": "Suç Analizi",
    "icon": "Shield",
    "description": "Kruskal-Wallis (nonparametrik ANOVA)",
    "color": "#dc2626",
    "inputs": 1,
    "outputs": 1,
    "defaultConfig": {
      "gruplar": "",
      "alan": "",
      "grup_alan": ""
    },
    "configFields": [
      {
        "name": "gruplar",
        "label": "gruplar",
        "type": "text"
      },
      {
        "name": "alan",
        "label": "alan",
        "type": "text"
      },
      {
        "name": "grup_alan",
        "label": "grup_alan",
        "type": "text"
      }
    ]
  },
  {
    "type": "suc_lojistik_regresyon",
    "label": "lojistik regresyon",
    "category": "Suç Analizi",
    "icon": "Shield",
    "description": "İkili lojistik regresyon: Wald, p, odds oranı",
    "color": "#dc2626",
    "inputs": 1,
    "outputs": 1,
    "defaultConfig": {
      "X": "",
      "y": "",
      "hedef": "",
      "degiskenler": ""
    },
    "configFields": [
      {
        "name": "X",
        "label": "X",
        "type": "text",
        "placeholder": "virgülle ayrılmış liste"
      },
      {
        "name": "y",
        "label": "y",
        "type": "text",
        "placeholder": "virgülle ayrılmış liste"
      },
      {
        "name": "hedef",
        "label": "hedef",
        "type": "text"
      },
      {
        "name": "degiskenler",
        "label": "degiskenler",
        "type": "text",
        "placeholder": "virgülle ayrılmış liste"
      }
    ]
  },
  {
    "type": "suc_mann_whitney",
    "label": "mann whitney",
    "category": "Suç Analizi",
    "icon": "Shield",
    "description": "Mann-Whitney U (nonparametrik iki örneklem)",
    "color": "#dc2626",
    "inputs": 1,
    "outputs": 1,
    "defaultConfig": {
      "x": "",
      "y": "",
      "alan": "",
      "grup_alan": ""
    },
    "configFields": [
      {
        "name": "x",
        "label": "x",
        "type": "text",
        "placeholder": "virgülle ayrılmış liste"
      },
      {
        "name": "y",
        "label": "y",
        "type": "text",
        "placeholder": "virgülle ayrılmış liste"
      },
      {
        "name": "alan",
        "label": "alan",
        "type": "text"
      },
      {
        "name": "grup_alan",
        "label": "grup_alan",
        "type": "text"
      }
    ]
  },
  {
    "type": "suc_mekansal_kumelenme",
    "label": "mekansal kumelenme",
    "category": "Suç Analizi",
    "icon": "Shield",
    "description": "Global Moran's I: olay dağılımı kümeli mi, dağınık mı, rastgele mi",
    "color": "#dc2626",
    "inputs": 1,
    "outputs": 1,
    "defaultConfig": {
      "hucre_km": 0.5,
      "bant_km": ""
    },
    "configFields": [
      {
        "name": "hucre_km",
        "label": "hucre_km",
        "type": "number",
        "default": 0.5
      },
      {
        "name": "bant_km",
        "label": "bant_km",
        "type": "number",
        "placeholder": "komşuluk eşiği (boş=otomatik)"
      }
    ]
  },
  {
    "type": "suc_mekansal_regresyon",
    "label": "mekansal regresyon",
    "category": "Suç Analizi",
    "icon": "Shield",
    "description": "Mekânsal regresyon tanısı: OLS + artık otokorelasyonu (mekânsal model gerekli mi)",
    "color": "#dc2626",
    "inputs": 1,
    "outputs": 1,
    "defaultConfig": {
      "hedef": "",
      "degiskenler": "",
      "bant_km": ""
    },
    "configFields": [
      {
        "name": "hedef",
        "label": "hedef",
        "type": "text",
        "placeholder": "bağımlı alan (ör. olay_sayisi)",
        "required": true
      },
      {
        "name": "degiskenler",
        "label": "degiskenler",
        "type": "text",
        "placeholder": "bağımsız alan adları",
        "required": true
      },
      {
        "name": "bant_km",
        "label": "bant_km",
        "type": "number",
        "placeholder": "komşuluk (boş=otomatik)"
      }
    ]
  },
  {
    "type": "suc_merkezsel_egilim",
    "label": "merkezsel egilim",
    "category": "Suç Analizi",
    "icon": "Shield",
    "description": "Sentrografik: ortalama merkez + standart mesafe + sapma elipsi (yayılım yönü)",
    "color": "#dc2626",
    "inputs": 1,
    "outputs": 1,
    "defaultConfig": {
      "agirlik_alan": ""
    },
    "configFields": [
      {
        "name": "agirlik_alan",
        "label": "agirlik_alan",
        "type": "text",
        "placeholder": "opsiyonel ağırlık alanı (ör. zarar_tl)"
      }
    ]
  },
  {
    "type": "suc_mukerrer_magduriyet",
    "label": "mukerrer magduriyet",
    "category": "Suç Analizi",
    "icon": "Shield",
    "description": "Aynı adres/mağdur için tekrar eden olaylar",
    "color": "#dc2626",
    "inputs": 1,
    "outputs": 1,
    "defaultConfig": {
      "alan": ""
    },
    "configFields": [
      {
        "name": "alan",
        "label": "alan",
        "type": "text",
        "required": true
      }
    ]
  },
  {
    "type": "suc_nni",
    "label": "nni",
    "category": "Suç Analizi",
    "icon": "Shield",
    "description": "NNI + z-testi ile kümelenme anlamlılığı (kenar_duzeltme=true ile Donnelly kenar düzeltmesi, v6.3)",
    "color": "#dc2626",
    "inputs": 1,
    "outputs": 1,
    "defaultConfig": {
      "kenar_duzeltme": "",
      "cevre_km": ""
    },
    "configFields": [
      {
        "name": "kenar_duzeltme",
        "label": "kenar_duzeltme",
        "type": "boolean"
      },
      {
        "name": "cevre_km",
        "label": "cevre_km",
        "type": "number"
      }
    ]
  },
  {
    "type": "suc_orneklem_cek",
    "label": "orneklem cek",
    "category": "Suç Analizi",
    "icon": "Shield",
    "description": "Basit/sistematik/tabakalı örneklem",
    "color": "#dc2626",
    "inputs": 1,
    "outputs": 1,
    "defaultConfig": {
      "yontem": "",
      "n": "",
      "tabaka_alan": "",
      "alanlar": ""
    },
    "configFields": [
      {
        "name": "yontem",
        "label": "yontem",
        "type": "select",
        "options": [
          "basit",
          "sistematik",
          "tabakali"
        ],
        "required": true
      },
      {
        "name": "n",
        "label": "n",
        "type": "number",
        "required": true
      },
      {
        "name": "tabaka_alan",
        "label": "tabaka_alan",
        "type": "text"
      },
      {
        "name": "alanlar",
        "label": "alanlar",
        "type": "text",
        "placeholder": "alan beyaz listesi (verilmezse güvenli çekirdek)"
      }
    ]
  },
  {
    "type": "suc_pearson",
    "label": "pearson",
    "category": "Suç Analizi",
    "icon": "Shield",
    "description": "İki sayısal alan için Pearson r ve r²",
    "color": "#dc2626",
    "inputs": 1,
    "outputs": 1,
    "defaultConfig": {
      "x": "",
      "y": ""
    },
    "configFields": [
      {
        "name": "x",
        "label": "x",
        "type": "text",
        "required": true
      },
      {
        "name": "y",
        "label": "y",
        "type": "text",
        "required": true
      }
    ]
  },
  {
    "type": "suc_power_few",
    "label": "power few",
    "category": "Suç Analizi",
    "icon": "Shield",
    "description": "Power Few: zararın %50'sini üreten en küçük birim kümesi",
    "color": "#dc2626",
    "inputs": 1,
    "outputs": 1,
    "defaultConfig": {
      "grup_alan": "",
      "tur_alan": "tur",
      "hedef_pay": 0.5,
      "agirlik_yolu": ""
    },
    "configFields": [
      {
        "name": "grup_alan",
        "label": "grup_alan",
        "type": "text",
        "required": true
      },
      {
        "name": "tur_alan",
        "label": "tur_alan",
        "type": "text",
        "default": "tur"
      },
      {
        "name": "hedef_pay",
        "label": "hedef_pay",
        "type": "number",
        "default": 0.5
      },
      {
        "name": "agirlik_yolu",
        "label": "agirlik_yolu",
        "type": "text"
      }
    ]
  },
  {
    "type": "suc_randomizasyon_testi",
    "label": "randomizasyon testi",
    "category": "Suç Analizi",
    "icon": "Shield",
    "description": "Permütasyon testi (varsayımsız ortalama farkı)",
    "color": "#dc2626",
    "inputs": 1,
    "outputs": 1,
    "defaultConfig": {
      "x": "",
      "y": "",
      "sim": 999,
      "alan": "",
      "grup_alan": ""
    },
    "configFields": [
      {
        "name": "x",
        "label": "x",
        "type": "text",
        "placeholder": "virgülle ayrılmış liste"
      },
      {
        "name": "y",
        "label": "y",
        "type": "text",
        "placeholder": "virgülle ayrılmış liste"
      },
      {
        "name": "sim",
        "label": "sim",
        "type": "number",
        "default": 999
      },
      {
        "name": "alan",
        "label": "alan",
        "type": "text"
      },
      {
        "name": "grup_alan",
        "label": "grup_alan",
        "type": "text"
      }
    ]
  },
  {
    "type": "suc_risk_arazi",
    "label": "risk arazi",
    "category": "Suç Analizi",
    "icon": "Shield",
    "description": "Risk Terrain Modeling: çevresel risk faktörlerinden kalıcı risk yüzeyi",
    "color": "#dc2626",
    "inputs": 1,
    "outputs": 1,
    "defaultConfig": {
      "faktor_alan": "",
      "hucre_km": 0.3,
      "yaricap_km": 0.4
    },
    "configFields": [
      {
        "name": "faktor_alan",
        "label": "faktor_alan",
        "type": "text",
        "placeholder": "risk faktörü tür alanı (ör. tesis_turu)",
        "required": true
      },
      {
        "name": "hucre_km",
        "label": "hucre_km",
        "type": "number",
        "default": 0.3
      },
      {
        "name": "yaricap_km",
        "label": "yaricap_km",
        "type": "number",
        "default": 0.4
      }
    ]
  },
  {
    "type": "suc_risk_skorla",
    "label": "risk skorla",
    "category": "Suç Analizi",
    "icon": "Shield",
    "description": "Ağırlıklı kural motoru ile olay risk skorlama",
    "color": "#dc2626",
    "inputs": 1,
    "outputs": 1,
    "defaultConfig": {
      "kurallar": ""
    },
    "configFields": [
      {
        "name": "kurallar",
        "label": "kurallar",
        "type": "text",
        "placeholder": "[{alan, kosul, deger, agirlik}]",
        "required": true
      }
    ]
  },
  {
    "type": "suc_saat_dagilimi",
    "label": "saat dagilimi",
    "category": "Suç Analizi",
    "icon": "Shield",
    "description": "0-23 saat dilimi olay dağılımı",
    "color": "#dc2626",
    "inputs": 1,
    "outputs": 1,
    "defaultConfig": {},
    "configFields": []
  },
  {
    "type": "suc_seri_eslestirme",
    "label": "seri eslestirme",
    "category": "Suç Analizi",
    "icon": "Shield",
    "description": "MO metin benzerliğiyle seri suç eşleştirme",
    "color": "#dc2626",
    "inputs": 1,
    "outputs": 1,
    "defaultConfig": {
      "mo_alan": "",
      "esik": 0.6
    },
    "configFields": [
      {
        "name": "mo_alan",
        "label": "mo_alan",
        "type": "text",
        "required": true
      },
      {
        "name": "esik",
        "label": "esik",
        "type": "number",
        "default": 0.6
      }
    ]
  },
  {
    "type": "suc_sicak_nokta_gi",
    "label": "sicak nokta gi",
    "category": "Suç Analizi",
    "icon": "Shield",
    "description": "Getis-Ord Gi*: istatistiksel anlamlı sıcak/soğuk noktalar (z + güven)",
    "color": "#dc2626",
    "inputs": 1,
    "outputs": 1,
    "defaultConfig": {
      "hucre_km": 0.5,
      "bant_km": ""
    },
    "configFields": [
      {
        "name": "hucre_km",
        "label": "hucre_km",
        "type": "number",
        "default": 0.5
      },
      {
        "name": "bant_km",
        "label": "bant_km",
        "type": "number",
        "placeholder": "komşuluk eşiği (boş=otomatik)"
      }
    ]
  },
  {
    "type": "suc_spearman",
    "label": "spearman",
    "category": "Suç Analizi",
    "icon": "Shield",
    "description": "Spearman rank korelasyonu + p-değeri",
    "color": "#dc2626",
    "inputs": 1,
    "outputs": 1,
    "defaultConfig": {
      "x": "",
      "y": "",
      "alan_x": "",
      "alan_y": ""
    },
    "configFields": [
      {
        "name": "x",
        "label": "x",
        "type": "text",
        "placeholder": "virgülle ayrılmış liste"
      },
      {
        "name": "y",
        "label": "y",
        "type": "text",
        "placeholder": "virgülle ayrılmış liste"
      },
      {
        "name": "alan_x",
        "label": "alan_x",
        "type": "text"
      },
      {
        "name": "alan_y",
        "label": "alan_y",
        "type": "text"
      }
    ]
  },
  {
    "type": "suc_t_testi",
    "label": "t testi",
    "category": "Suç Analizi",
    "icon": "Shield",
    "description": "t-testi: tek örneklem / bağımsız (Welch seçenekli) / bağımlı",
    "color": "#dc2626",
    "inputs": 1,
    "outputs": 1,
    "defaultConfig": {
      "tip": "",
      "x": "",
      "y": "",
      "mu0": "",
      "welch": true,
      "alan": "",
      "grup_alan": ""
    },
    "configFields": [
      {
        "name": "tip",
        "label": "tip",
        "type": "select",
        "options": [
          "tek",
          "bagimsiz",
          "bagimli"
        ],
        "required": true
      },
      {
        "name": "x",
        "label": "x",
        "type": "text",
        "placeholder": "virgülle ayrılmış liste"
      },
      {
        "name": "y",
        "label": "y",
        "type": "text",
        "placeholder": "virgülle ayrılmış liste"
      },
      {
        "name": "mu0",
        "label": "mu0",
        "type": "number"
      },
      {
        "name": "welch",
        "label": "welch",
        "type": "boolean",
        "default": true
      },
      {
        "name": "alan",
        "label": "alan",
        "type": "text"
      },
      {
        "name": "grup_alan",
        "label": "grup_alan",
        "type": "text"
      }
    ]
  },
  {
    "type": "suc_trend",
    "label": "trend",
    "category": "Suç Analizi",
    "icon": "Shield",
    "description": "Günlük seride doğrusal trend",
    "color": "#dc2626",
    "inputs": 1,
    "outputs": 1,
    "defaultConfig": {},
    "configFields": []
  },
  {
    "type": "suc_veri_kalitesi",
    "label": "veri kalitesi",
    "category": "Suç Analizi",
    "icon": "Shield",
    "description": "DOKTRIN: HER analizden önce çağırın — deterministik veri profili + isteğe bağlı fitness gate kararı",
    "color": "#dc2626",
    "inputs": 1,
    "outputs": 1,
    "defaultConfig": {
      "sayisal_alan": "",
      "analiz": "",
      "payda_var": "",
      "fuzzy": ""
    },
    "configFields": [
      {
        "name": "sayisal_alan",
        "label": "sayisal_alan",
        "type": "text"
      },
      {
        "name": "analiz",
        "label": "analiz",
        "type": "text",
        "placeholder": "verilirse analiz_uygun_mu kararı da döner"
      },
      {
        "name": "payda_var",
        "label": "payda_var",
        "type": "boolean"
      },
      {
        "name": "fuzzy",
        "label": "fuzzy",
        "type": "boolean",
        "placeholder": "yazım varyantı adayları (pahalı)"
      }
    ]
  },
  {
    "type": "suc_veri_ozeti",
    "label": "veri ozeti",
    "category": "Suç Analizi",
    "icon": "Shield",
    "description": "Kayıt sayısı, alanlar ve eksik veri raporu",
    "color": "#dc2626",
    "inputs": 1,
    "outputs": 1,
    "defaultConfig": {},
    "configFields": []
  },
  {
    "type": "suc_yakin_tekrar",
    "label": "yakin tekrar",
    "category": "Suç Analizi",
    "icon": "Shield",
    "description": "Near-repeat çiftleri; sim>0 ile Monte Carlo p-değeri",
    "color": "#dc2626",
    "inputs": 1,
    "outputs": 1,
    "defaultConfig": {
      "mesafe_km": 0.4,
      "gun": 14,
      "sim": 0
    },
    "configFields": [
      {
        "name": "mesafe_km",
        "label": "mesafe_km",
        "type": "number",
        "default": 0.4
      },
      {
        "name": "gun",
        "label": "gun",
        "type": "number",
        "default": 14
      },
      {
        "name": "sim",
        "label": "sim",
        "type": "number",
        "default": 0
      }
    ]
  },
  {
    "type": "suc_yerel_kumeleme",
    "label": "yerel kumeleme",
    "category": "Suç Analizi",
    "icon": "Shield",
    "description": "Local Moran's I (LISA): sıcak/soğuk küme vs mekânsal aykırı değer (HH/LL/HL/LH)",
    "color": "#dc2626",
    "inputs": 1,
    "outputs": 1,
    "defaultConfig": {
      "hucre_km": 0.5,
      "bant_km": ""
    },
    "configFields": [
      {
        "name": "hucre_km",
        "label": "hucre_km",
        "type": "number",
        "default": 0.5
      },
      {
        "name": "bant_km",
        "label": "bant_km",
        "type": "number",
        "placeholder": "komşuluk eşiği (boş=otomatik)"
      }
    ]
  },
  {
    "type": "suc_yukselen_sicak_nokta",
    "label": "yukselen sicak nokta",
    "category": "Suç Analizi",
    "icon": "Shield",
    "description": "Emerging Hotspot: bölgeleri kalıcı/yoğunlaşan/yeni/sönen/tarihsel sınıflar",
    "color": "#dc2626",
    "inputs": 1,
    "outputs": 1,
    "defaultConfig": {
      "bolge_alan": "",
      "zaman_alan": "",
      "donem_sayisi": 4
    },
    "configFields": [
      {
        "name": "bolge_alan",
        "label": "bolge_alan",
        "type": "text",
        "required": true
      },
      {
        "name": "zaman_alan",
        "label": "zaman_alan",
        "type": "text",
        "required": true
      },
      {
        "name": "donem_sayisi",
        "label": "donem_sayisi",
        "type": "number",
        "default": 4
      }
    ]
  },
  {
    "type": "suc_zarar_hesapla",
    "label": "zarar hesapla",
    "category": "Suç Analizi",
    "icon": "Shield",
    "description": "Crime Harm Index: zarar-ağırlıklı toplam/grup analizi",
    "color": "#dc2626",
    "inputs": 1,
    "outputs": 1,
    "defaultConfig": {
      "tur_alan": "tur",
      "grup_alan": "",
      "agirlik_yolu": ""
    },
    "configFields": [
      {
        "name": "tur_alan",
        "label": "tur_alan",
        "type": "text",
        "default": "tur"
      },
      {
        "name": "grup_alan",
        "label": "grup_alan",
        "type": "text"
      },
      {
        "name": "agirlik_yolu",
        "label": "agirlik_yolu",
        "type": "text",
        "placeholder": "kurum ağırlık JSON (veri kökünde)"
      }
    ]
  }
];

// node tipi -> array tipli config alanları (motor metni listeye çevirir)
export const sucDiziAlanlari: Record<string, string[]> = {
  "suc_bulanik_eslesme": [
    "alanlar"
  ],
  "suc_coklu_regresyon": [
    "X",
    "y",
    "degiskenler"
  ],
  "suc_dagilim_olculeri": [
    "degerler"
  ],
  "suc_endeks_hesapla": [
    "gostergeler",
    "tersler"
  ],
  "suc_kendall": [
    "x",
    "y"
  ],
  "suc_lojistik_regresyon": [
    "X",
    "y",
    "degiskenler"
  ],
  "suc_mann_whitney": [
    "x",
    "y"
  ],
  "suc_mekansal_regresyon": [
    "degiskenler"
  ],
  "suc_orneklem_cek": [
    "alanlar"
  ],
  "suc_randomizasyon_testi": [
    "x",
    "y"
  ],
  "suc_risk_skorla": [
    "kurallar"
  ],
  "suc_spearman": [
    "x",
    "y"
  ],
  "suc_t_testi": [
    "x",
    "y"
  ]
};
