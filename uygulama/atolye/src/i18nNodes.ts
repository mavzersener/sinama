/**
 * Node-level translations (label + description) and category names.
 * Canonical node data (nodeDefinitions.ts) stays English/Turkish as authored;
 * these tables provide the OTHER language. Unknown types fall back to the
 * caller-supplied default (the canonical string), so this never blocks a node.
 */
import type { Lang } from './i18n';

interface Text { label: string; description: string }
type Pair = { en: Text; tr: Text };

const nodeI18n: Record<string, Pair> = {
  // --- Data Input ---
  csv_source: { en: { label: 'CSV Input', description: 'Import data from CSV file' }, tr: { label: 'CSV Girişi', description: 'CSV dosyasından veri içe aktar' } },
  db_source: { en: { label: 'Database Query', description: 'Query data from SQL database' }, tr: { label: 'Veritabanı Sorgusu', description: 'SQL veritabanından veri sorgula' } },
  api_source: { en: { label: 'API Endpoint', description: 'Fetch data from REST API' }, tr: { label: 'API Uç Noktası', description: "REST API'den veri çek" } },
  // --- Processing ---
  filter: { en: { label: 'Filter Rows', description: 'Filter rows based on conditions' }, tr: { label: 'Satır Filtrele', description: 'Koşullara göre satırları filtrele' } },
  extend_field: { en: { label: 'Extend Field', description: 'Add computed columns to dataset' }, tr: { label: 'Alan Ekle', description: 'Veri setine hesaplanmış sütunlar ekle' } },
  aggregate: { en: { label: 'Aggregate', description: 'Group and aggregate data' }, tr: { label: 'Topla (Grupla)', description: 'Verileri grupla ve topla' } },
  sort: { en: { label: 'Sort', description: 'Sort data by columns' }, tr: { label: 'Sırala', description: 'Verileri sütunlara göre sırala' } },
  join: { en: { label: 'Join Tables', description: 'Merge two datasets by key' }, tr: { label: 'Tabloları Birleştir', description: 'İki veri setini anahtara göre birleştir' } },
  dedup: { en: { label: 'Deduplicate', description: 'Remove duplicate rows' }, tr: { label: 'Yinelenenleri Kaldır', description: 'Yinelenen satırları kaldır' } },
  data_clean: { en: { label: 'Data Cleaning', description: 'Handle missing values (drop/mean/median/mode/constant/ffill) + trim + dedup' }, tr: { label: 'Veri Temizleme', description: 'Eksik değerleri işle (düş/ortalama/medyan/mod/sabit/ileri-doldur) + kırp + yinelenen kaldır' } },
  data_quality: { en: { label: 'Data Quality', description: 'Analyze data quality: missing values, types, outliers, score' }, tr: { label: 'Veri Kalitesi', description: 'Veri kalitesi analizi: eksik değerler, tipler, aykırılar, skor' } },
  block_group: { en: { label: 'Block Group', description: 'Reconstruct merged-cell exports: assign a block ID and fill values WITHIN the block only' }, tr: { label: 'Olay Bloğu', description: 'Birleştirilmiş hücre ihracını onarır: blok kimliği üretir ve doldurmayı blok sınırında durdurur' } },
  // --- Analysis ---
  statistics: { en: { label: 'Statistics', description: 'Calculate descriptive statistics' }, tr: { label: 'İstatistikler', description: 'Betimsel istatistikleri hesapla' } },
  linear_regression: { en: { label: 'Linear Regression', description: 'Train linear regression model' }, tr: { label: 'Doğrusal Regresyon', description: 'Doğrusal regresyon modeli eğit' } },
  association_rules: { en: { label: 'Association Rules', description: 'Market basket analysis (Apriori)' }, tr: { label: 'Birliktelik Kuralları', description: 'Pazar sepeti analizi (Apriori)' } },
  clustering: { en: { label: 'K-Means Clustering', description: 'Group data into clusters' }, tr: { label: 'K-Ortalama Kümeleme', description: 'Verileri kümelere ayır' } },
  anomaly_detection: { en: { label: 'Anomaly Detection', description: 'Detect outliers using IQR or Z-score' }, tr: { label: 'Anomali Tespiti', description: 'IQR veya Z-skoru ile aykırı değer tespiti' } },
  correlation: { en: { label: 'Correlation Matrix', description: 'Compute correlation between variables' }, tr: { label: 'Korelasyon Matrisi', description: 'Değişkenler arası korelasyonu hesapla' } },
  model_validation: { en: { label: 'Model Validation', description: 'Classification metrics: confusion matrix, precision, recall, F1' }, tr: { label: 'Model Doğrulama', description: 'Sınıflandırma metrikleri: karmaşıklık matrisi, kesinlik, duyarlılık, F1' } },
  cross_validation: { en: { label: 'Cross-Validation', description: 'K-fold cross-validation for regression models' }, tr: { label: 'Çapraz Doğrulama', description: 'Regresyon modelleri için K-katlı çapraz doğrulama' } },
  random_forest: { en: { label: 'Random Forest', description: 'Server-side Random Forest (classification/regression)' }, tr: { label: 'Rastgele Orman', description: 'Sunucu-taraflı Rastgele Orman (sınıflandırma/regresyon)' } },
  gradient_boosting: { en: { label: 'Gradient Boosting (XGBoost)', description: 'Server-side Gradient Boosting (ML service)' }, tr: { label: 'Gradyan Artırma (XGBoost)', description: 'Sunucu-taraflı Gradyan Artırma (ML servisi)' } },
  svm: { en: { label: 'SVM', description: 'Server-side SVM (ML service)' }, tr: { label: 'DVM (SVM)', description: 'Sunucu-taraflı Destek Vektör Makinesi (ML servisi)' } },
  logistic_regression: { en: { label: 'Logistic Regression', description: 'Server-side Logistic Regression (ML service)' }, tr: { label: 'Lojistik Regresyon', description: 'Sunucu-taraflı Lojistik Regresyon (ML servisi)' } },
  pca: { en: { label: 'PCA', description: 'Server-side PCA (ML service)' }, tr: { label: 'TBA (PCA)', description: 'Sunucu-taraflı Temel Bileşen Analizi (ML servisi)' } },
  dbscan: { en: { label: 'DBSCAN Clustering', description: 'Server-side density-based clustering (DBSCAN)' }, tr: { label: 'DBSCAN Kümeleme', description: 'Sunucu-taraflı yoğunluk-tabanlı kümeleme (DBSCAN)' } },
  arima: { en: { label: 'ARIMA Forecast', description: 'Server-side ARIMA time-series forecasting' }, tr: { label: 'ARIMA Tahmin', description: 'Sunucu-taraflı ARIMA zaman-serisi tahmini' } },
  hierarchical: { en: { label: 'Hierarchical Clustering', description: 'Server-side Hierarchical Clustering (ML service)' }, tr: { label: 'Hiyerarşik Kümeleme', description: 'Sunucu-taraflı Hiyerarşik Kümeleme (ML servisi)' } },
  // --- Agent ---
  agent_insight: { en: { label: 'Agent Insight', description: 'Interpret upstream results in natural language (local agent)' }, tr: { label: 'Ajan İçgörüsü', description: 'Üst-akış sonuçlarını doğal dilde yorumla (yerel ajan)' } },
  // --- Output ---
  chart: { en: { label: 'Chart', description: 'Visualize data with charts' }, tr: { label: 'Grafik', description: 'Verileri grafiklerle görselleştir' } },
  export: { en: { label: 'Export Data', description: 'Export results to file' }, tr: { label: 'Veri Dışa Aktar', description: 'Sonuçları dosyaya aktar' } },
  alert: { en: { label: 'Alert', description: 'Trigger alert when condition met' }, tr: { label: 'Uyarı', description: 'Koşul sağlandığında uyarı tetikle' } },
  evidence_export: { en: { label: 'Evidence Export', description: 'Integrity-hashed (SHA-256) evidence package, recorded in a signed evidence ledger' }, tr: { label: 'Delil Dışa Aktarımı', description: "Bütünlük hash'li (SHA-256) kanıt paketi; imzalı kanıt defterine kaydedilir" } },
  // --- Kolluk Data (authored in Turkish; EN provided) ---
  pts_source: { en: { label: 'PTS Query', description: 'Police Tactical System - person/vehicle query' }, tr: { label: 'PTS Sorgu', description: 'Polis Taktik Sistemi - kişi/araç sorgusu' } },
  anpr_source: { en: { label: 'ANPR Plate', description: 'Automatic plate recognition system data' }, tr: { label: 'ANPR Plaka', description: 'Otomatik plaka tanıma sistem verisi' } },
  mobese_source: { en: { label: 'MOBESE Camera', description: 'MOBESE camera metadata query' }, tr: { label: 'MOBESE Kamera', description: 'MOBESE kamera metadata sorgusu' } },
  ihbar_source: { en: { label: 'Tip-off Records', description: '155/156 tip-off database query' }, tr: { label: 'İhbar Kayıtları', description: '155/156 ihbar veritabanı sorgusu' } },
  adli_sicil_source: { en: { label: 'Criminal Record', description: 'Criminal record query' }, tr: { label: 'Adli Sicil', description: 'Adli sicil kaydı sorgusu' } },
  // --- Kolluk Analysis ---
  sna: { en: { label: 'Social Network Analysis', description: 'Suspect social network - centrality, links' }, tr: { label: 'Sosyal Ağ Analizi', description: 'Şüpheli sosyal ağ analizi - merkeziyet, bağlantılar' } },
  geo_hotspot: { en: { label: 'Geographic Hotspot', description: 'Location-based hotspot mapping' }, tr: { label: 'Coğrafi Hotspot', description: 'Lokasyon bazlı sıcak nokta haritalandırma' } },
  temporal_pattern: { en: { label: 'Temporal Pattern', description: 'Time-based event correlation and pattern detection' }, tr: { label: 'Zamansal Örüntü', description: 'Zaman bazlı olay korelasyon ve örüntü tespiti' } },
  cooccurrence: { en: { label: 'Co-occurrence Analysis', description: 'Suspect co-occurrence (address, vehicle, comms)' }, tr: { label: 'Eş-Oluşum Analizi', description: 'Şüpheli eş-oluşum analizi (adres, araç, iletişim)' } },
};

const categoryI18n: Record<string, { en: string; tr: string }> = {
  'Data Input': { en: 'Data Input', tr: 'Veri Girişi' },
  Processing: { en: 'Processing', tr: 'İşleme' },
  Analysis: { en: 'Analysis', tr: 'Analiz' },
  Agent: { en: 'Agent', tr: 'Ajan' },
  Output: { en: 'Output', tr: 'Çıktı' },
  'Kolluk Data': { en: 'Law Enforcement Data', tr: 'Kolluk Verisi' },
  'Kolluk Analysis': { en: 'Law Enforcement Analysis', tr: 'Kolluk Analizi' },
};

export function nodeLabel(lang: Lang, type: string, fallback: string): string {
  return nodeI18n[type]?.[lang]?.label ?? fallback;
}

export function nodeDesc(lang: Lang, type: string, fallback: string): string {
  return nodeI18n[type]?.[lang]?.description ?? fallback;
}

export function categoryLabel(lang: Lang, category: string): string {
  return categoryI18n[category]?.[lang] ?? category;
}
