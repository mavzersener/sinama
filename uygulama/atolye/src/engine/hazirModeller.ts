// Hazır iş akışı şablonları (model kitaplığı).
// (executionEngine.ts'den bölündü — Faz 4.)

import type { SavedModel } from '../store/useStore';

export function getPrebuiltModels(): SavedModel[] {
  return [
    // 0. Otodan Hırsızlık — gerçek şüpheli/mağdur ihracı üzerinde doğrulandı.
    //
    // Bu ihraç "birleştirilmiş hücre" biçimindedir: bir olayın ek şüphelileri,
    // olay sütunları BOŞ satırlar olarak gelir. Olay kimliği sütunlarda değil
    // satır sırasındadır; bu yüzden akış `block_group` ile başlar. Sütun
    // birleştirip (tarih+yer) kimlik üretmek YANLIŞ sonuç verir — gerçek veride
    // 41 hayalet birliktelik üretip 56 tekrarlayan çiftin tamamını kaçırıyordu.
    //
    // İki ayrı analiz birimi bilinçlidir:
    //   OLAY düzeyi    → dedup(olay_id) sonrası; hotspot/zamansal/ilçe
    //   ŞÜPHELİ düzeyi → tüm satırlar; birlikte suç işleyenler
    {
      id: 'model-otodan-hirsizlik',
      name: 'Otodan Hırsızlık — Şüpheli/Mağdur',
      description: 'Birleştirilmiş hücre ihracını onarır, olay ve şüpheli düzeyinde ayrı ayrı analiz eder (hotspot + birlikte suç işleyenler)',
      category: 'Kolluk - Hırsızlık',
      createdAt: '2026-07-31T00:00:00Z',
      updatedAt: '2026-07-31T00:00:00Z',
      runs: 0,
      tags: ['hırsızlık', 'blok-onarım', 'hotspot', 'birlikte-suç'],
      nodes: [
        { id: 'oto-csv', type: 'custom', position: { x: 40, y: 220 }, data: { label: 'Şüpheli/Mağdur CSV', type: 'csv_source', category: 'Data Input', icon: 'FileSpreadsheet', color: '#10b981', config: { filename: 'otodan hirsizlik supheliMagdur.csv', delimiter: ';', hasHeader: true }, status: 'idle' } },
        { id: 'oto-blok', type: 'custom', position: { x: 300, y: 220 }, data: { label: 'Olay Bloğu', type: 'block_group', category: 'Processing', icon: 'Rows3', color: '#f59e0b', config: { markerColumn: 'suc', idColumn: 'olay_id', fillColumns: 'enlem, boylam, tarih, saat, il, ilce, yer, suc, MO' }, status: 'idle' } },
        { id: 'oto-olay', type: 'custom', position: { x: 570, y: 80 }, data: { label: 'Olay Düzeyi (tekilleştir)', type: 'dedup', category: 'Processing', icon: 'CopyMinus', color: '#f59e0b', config: { keyColumns: 'olay_id', keep: 'first' }, status: 'idle' } },
        { id: 'oto-geo', type: 'custom', position: { x: 850, y: 20 }, data: { label: 'Coğrafi Hotspot', type: 'geo_hotspot', category: 'Kolluk Analysis', icon: 'MapPin', color: '#7c3aed', config: { latColumn: 'enlem', lngColumn: 'boylam', weightColumn: '', gridSize: 0.05 }, status: 'idle' } },
        { id: 'oto-zaman', type: 'custom', position: { x: 850, y: 140 }, data: { label: 'Zamansal Örüntü', type: 'temporal_pattern', category: 'Kolluk Analysis', icon: 'Clock', color: '#7c3aed', config: { timeColumn: 'tarih', categoryColumn: 'ilce', bucket: 'month' }, status: 'idle' } },
        { id: 'oto-ilce', type: 'custom', position: { x: 850, y: 260 }, data: { label: 'İlçe Dağılımı', type: 'aggregate', category: 'Processing', icon: 'BarChart3', color: '#f59e0b', config: { groupBy: 'ilce', aggregations: ['COUNT'] }, status: 'idle' } },
        { id: 'oto-birlikte', type: 'custom', position: { x: 570, y: 380 }, data: { label: 'Birlikte Suç İşleyenler', type: 'cooccurrence', category: 'Kolluk Analysis', icon: 'Users', color: '#7c3aed', config: { entityColumn: 'Skodu', contextColumn: 'olay_id', minOccurrences: 2 }, status: 'idle' } },
        { id: 'oto-kalite', type: 'custom', position: { x: 570, y: 500 }, data: { label: 'Veri Kalitesi', type: 'data_quality', category: 'Processing', icon: 'ShieldCheck', color: '#f59e0b', config: { columns: '' }, status: 'idle' } },
      ],
      edges: [
        { id: 'oto-e1', source: 'oto-csv', target: 'oto-blok' },
        { id: 'oto-e2', source: 'oto-blok', target: 'oto-olay' },
        { id: 'oto-e3', source: 'oto-olay', target: 'oto-geo' },
        { id: 'oto-e4', source: 'oto-olay', target: 'oto-zaman' },
        { id: 'oto-e5', source: 'oto-olay', target: 'oto-ilce' },
        { id: 'oto-e6', source: 'oto-blok', target: 'oto-birlikte' },
        { id: 'oto-e7', source: 'oto-blok', target: 'oto-kalite' },
      ],
    },
    // 1. Drug Co-Residence Analysis
    {
      id: 'model-drug-coresi',
      name: 'Drug Co-Residence Analysis',
      description: 'Analyze address patterns among suspects to identify potential drug dens via co-residence frequency',
      category: 'Police - Narcotics',
      createdAt: '2026-06-01T00:00:00Z',
      updatedAt: '2026-06-28T00:00:00Z',
      runs: 0,
      tags: ['narcotics', 'co-residence', 'hotspot'],
      nodes: [
        { id: 'db-src', type: 'custom', position: { x: 50, y: 100 }, data: { label: 'Suspect DB', type: 'db_source', category: 'Data Input', icon: 'Database', color: '#10b981', config: { connection: 'police_db', table: 'suspects', query: 'SELECT person_id, address, arrest_date, drug_type FROM suspects WHERE arrest_date >= 2024-01-01' }, status: 'idle' } },
        { id: 'filter-drug', type: 'custom', position: { x: 300, y: 100 }, data: { label: 'Filter Drug Cases', type: 'filter', category: 'Processing', icon: 'Filter', color: '#f59e0b', config: { column: 'drug_type', condition: 'not_null', value: '' }, status: 'idle' } },
        { id: 'agg-addr', type: 'custom', position: { x: 550, y: 100 }, data: { label: 'Count by Address', type: 'aggregate', category: 'Processing', icon: 'BarChart3', color: '#f59e0b', config: { groupBy: 'address', aggregations: ['COUNT'] }, status: 'idle' } },
        { id: 'filter-freq', type: 'custom', position: { x: 800, y: 100 }, data: { label: 'High-Freq Addresses', type: 'filter', category: 'Processing', icon: 'Filter', color: '#f59e0b', config: { column: 'count', condition: 'greater_than', value: '2' }, status: 'idle' } },
        { id: 'anomaly', type: 'custom', position: { x: 1050, y: 100 }, data: { label: 'Anomaly Detection', type: 'anomaly_detection', category: 'Analysis', icon: 'AlertTriangle', color: '#8b5cf6', config: { columns: 'count', method: 'iqr', threshold: 1.5 }, status: 'idle' } },
        { id: 'chart', type: 'custom', position: { x: 1300, y: 100 }, data: { label: 'Risk Chart', type: 'chart', category: 'Output', icon: 'BarChart', color: '#ec4899', config: { chartType: 'bar', xColumn: 'address', yColumn: 'count', title: 'High-Risk Addresses' }, status: 'idle' } },
      ],
      edges: [
        { id: 'e1', source: 'db-src', target: 'filter-drug' },
        { id: 'e2', source: 'filter-drug', target: 'agg-addr' },
        { id: 'e3', source: 'agg-addr', target: 'filter-freq' },
        { id: 'e4', source: 'filter-freq', target: 'anomaly' },
        { id: 'e5', source: 'anomaly', target: 'chart' },
      ]
    },
    // 2. Vehicle Clustering Analysis
    {
      id: 'model-vehicle-cluster',
      name: 'Vehicle Clustering Analysis',
      description: 'Cluster vehicle sightings by location and time to identify potential surveillance targets',
      category: 'Police - Intelligence',
      createdAt: '2026-06-01T00:00:00Z',
      updatedAt: '2026-06-28T00:00:00Z',
      runs: 0,
      tags: ['vehicle', 'clustering', 'surveillance'],
      nodes: [
        { id: 'csv-pts', type: 'custom', position: { x: 50, y: 100 }, data: { label: 'ANPR Data', type: 'csv_source', category: 'Data Input', icon: 'FileSpreadsheet', color: '#10b981', config: { filename: 'anpr_sightings.csv', delimiter: ',', hasHeader: true }, status: 'idle' } },
        { id: 'filter-time', type: 'custom', position: { x: 300, y: 100 }, data: { label: 'Filter Night Hours', type: 'filter', category: 'Processing', icon: 'Filter', color: '#f59e0b', config: { column: 'hour', condition: 'greater_than', value: '20' }, status: 'idle' } },
        { id: 'cluster', type: 'custom', position: { x: 550, y: 100 }, data: { label: 'K-Means Cluster', type: 'clustering', category: 'Analysis', icon: 'Target', color: '#8b5cf6', config: { features: 'lat,lng', k: 5, maxIterations: 100 }, status: 'idle' } },
        { id: 'stats', type: 'custom', position: { x: 550, y: 300 }, data: { label: 'Statistics', type: 'statistics', category: 'Analysis', icon: 'PieChart', color: '#8b5cf6', config: { columns: 'lat,lng', stats: ['count', 'mean', 'std', 'min', 'max'] }, status: 'idle' } },
        { id: 'export', type: 'custom', position: { x: 800, y: 100 }, data: { label: 'Export Clusters', type: 'export', category: 'Output', icon: 'Download', color: '#ec4899', config: { format: 'csv', filename: 'cluster_results' }, status: 'idle' } },
      ],
      edges: [
        { id: 'e1', source: 'csv-pts', target: 'filter-time' },
        { id: 'e2', source: 'filter-time', target: 'cluster' },
        { id: 'e3', source: 'filter-time', target: 'stats' },
        { id: 'e4', source: 'cluster', target: 'export' },
      ]
    },
    // 3. Retail Promotion Prediction
    {
      id: 'model-retail-promo',
      name: 'Retail Promotion Prediction',
      description: 'Predict promotion effectiveness using linear regression on historical sales data',
      category: 'Retail - Sales',
      createdAt: '2026-06-01T00:00:00Z',
      updatedAt: '2026-06-28T00:00:00Z',
      runs: 0,
      tags: ['retail', 'promotion', 'prediction'],
      nodes: [
        { id: 'csv-sales', type: 'custom', position: { x: 50, y: 100 }, data: { label: 'Sales Data', type: 'csv_source', category: 'Data Input', icon: 'FileSpreadsheet', color: '#10b981', config: { filename: 'sales_history.csv', delimiter: ',', hasHeader: true }, status: 'idle' } },
        { id: 'stats-overview', type: 'custom', position: { x: 50, y: 300 }, data: { label: 'Overview Stats', type: 'statistics', category: 'Analysis', icon: 'PieChart', color: '#8b5cf6', config: { columns: 'sales_amount,discount_days', stats: ['count', 'mean', 'std', 'min', 'max'] }, status: 'idle' } },
        { id: 'corr', type: 'custom', position: { x: 300, y: 100 }, data: { label: 'Correlation', type: 'correlation', category: 'Analysis', icon: 'Grid3X3', color: '#8b5cf6', config: { columns: 'sales_amount,discount_days,temperature', method: 'pearson' }, status: 'idle' } },
        { id: 'regression', type: 'custom', position: { x: 550, y: 100 }, data: { label: 'Linear Regression', type: 'linear_regression', category: 'Analysis', icon: 'TrendingUp', color: '#8b5cf6', config: { target: 'sales_amount', features: 'discount_days,temperature', testSize: 20 }, status: 'idle' } },
        { id: 'chart-result', type: 'custom', position: { x: 800, y: 100 }, data: { label: 'Results Chart', type: 'chart', category: 'Output', icon: 'BarChart', color: '#ec4899', config: { chartType: 'scatter', title: 'Sales vs Discount' }, status: 'idle' } },
        { id: 'export-csv', type: 'custom', position: { x: 800, y: 300 }, data: { label: 'Export Predictions', type: 'export', category: 'Output', icon: 'Download', color: '#ec4899', config: { format: 'csv', filename: 'promo_predictions' }, status: 'idle' } },
      ],
      edges: [
        { id: 'e1', source: 'csv-sales', target: 'corr' },
        { id: 'e2', source: 'csv-sales', target: 'stats-overview' },
        { id: 'e3', source: 'corr', target: 'regression' },
        { id: 'e4', source: 'regression', target: 'chart-result' },
        { id: 'e5', source: 'regression', target: 'export-csv' },
      ]
    },
    // 4. Market Basket Analysis
    {
      id: 'model-basket',
      name: 'Market Basket Analysis',
      description: 'Discover product associations using frequent itemset mining on transaction data',
      category: 'Retail - Analytics',
      createdAt: '2026-06-01T00:00:00Z',
      updatedAt: '2026-06-28T00:00:00Z',
      runs: 0,
      tags: ['retail', 'association', 'basket'],
      nodes: [
        { id: 'csv-trans', type: 'custom', position: { x: 50, y: 100 }, data: { label: 'Transactions', type: 'csv_source', category: 'Data Input', icon: 'FileSpreadsheet', color: '#10b981', config: { filename: 'transactions.csv', delimiter: ',', hasHeader: true }, status: 'idle' } },
        { id: 'dedup', type: 'custom', position: { x: 300, y: 100 }, data: { label: 'Deduplicate', type: 'dedup', category: 'Processing', icon: 'CopyMinus', color: '#f59e0b', config: { keyColumns: 'transaction_id', keep: 'first' }, status: 'idle' } },
        { id: 'rules', type: 'custom', position: { x: 550, y: 100 }, data: { label: 'Association Rules', type: 'association_rules', category: 'Analysis', icon: 'Link2', color: '#8b5cf6', config: { itemsColumn: 'product_name', minSupport: 0.05, minConfidence: 0.5 }, status: 'idle' } },
        { id: 'export-rules', type: 'custom', position: { x: 800, y: 100 }, data: { label: 'Export Rules', type: 'export', category: 'Output', icon: 'Download', color: '#ec4899', config: { format: 'json', filename: 'association_rules' }, status: 'idle' } },
      ],
      edges: [
        { id: 'e1', source: 'csv-trans', target: 'dedup' },
        { id: 'e2', source: 'dedup', target: 'rules' },
        { id: 'e3', source: 'rules', target: 'export-rules' },
      ]
    },
    // 5. Sosyal Ag ve Cografi Hotspot Analizi (P3 Police)
    {
      id: 'model-sna-geo',
      name: 'SNA + Cografi Hotspot',
      description: 'Supheli sosyal ag analizi ve cografi sicak nokta tespiti - kolluk istihbarat',
      category: 'Kolluk - Istihbarat',
      createdAt: '2026-06-01T00:00:00Z',
      updatedAt: '2026-06-28T00:00:00Z',
      runs: 0,
      tags: ['kolluk', 'sna', 'hotspot', 'istihbarat'],
      nodes: [
        { id: 'pts', type: 'custom', position: { x: 50, y: 100 }, data: { label: 'PTS Sorgu', type: 'pts_source', category: 'Kolluk Data', icon: 'Shield', color: '#dc2626', config: { queryType: 'person', queryValue: '', legalBasis: '5271-md-3', kvkkClass: 'Gizli' }, status: 'idle' } },
        { id: 'sna', type: 'custom', position: { x: 350, y: 100 }, data: { label: 'Sosyal Ag Analizi', type: 'sna', category: 'Kolluk Analysis', icon: 'Network', color: '#7c3aed', config: { personColumn: 'person_id', linkColumn: 'tc_kimlik', method: 'degree' }, status: 'idle' } },
        { id: 'anpr', type: 'custom', position: { x: 50, y: 300 }, data: { label: 'ANPR Plaka', type: 'anpr_source', category: 'Kolluk Data', icon: 'Camera', color: '#dc2626', config: { plate: '', startDate: '2026-01-01', endDate: '2026-06-30', legalBasis: '2559-md-4', kvkkClass: 'Kisitli' }, status: 'idle' } },
        { id: 'hotspot', type: 'custom', position: { x: 350, y: 300 }, data: { label: 'Cografi Hotspot', type: 'geo_hotspot', category: 'Kolluk Analysis', icon: 'MapPin', color: '#7c3aed', config: { latColumn: 'latitude', lngColumn: 'longitude', weightColumn: 'violation_count', gridSize: 0.01 }, status: 'idle' } },
        { id: 'temporal', type: 'custom', position: { x: 650, y: 100 }, data: { label: 'Zamansal Oruntu', type: 'temporal_pattern', category: 'Kolluk Analysis', icon: 'Clock', color: '#7c3aed', config: { timeColumn: 'capture_time', categoryColumn: 'location', bucket: 'hour' }, status: 'idle' } },
        { id: 'evidence', type: 'custom', position: { x: 650, y: 300 }, data: { label: 'Evidence Export', type: 'evidence_export', category: 'Output', icon: 'FileLock', color: '#dc2626', config: { caseNumber: '', officerId: '', format: 'json' }, status: 'idle' } },
      ],
      edges: [
        { id: 'e1', source: 'pts', target: 'sna' },
        { id: 'e2', source: 'anpr', target: 'hotspot' },
        { id: 'e3', source: 'anpr', target: 'temporal' },
        { id: 'e4', source: 'sna', target: 'evidence' },
        { id: 'e5', source: 'hotspot', target: 'evidence' },
      ]
    },
    // 6. Supheli Es-Olusum ve Ihbar Korelasyonu (P3 Police)
    {
      id: 'model-cooc-ihbar',
      name: 'Supheli Es-Olusum + Ihbar',
      description: 'Supheli es-olusum analizi ve ihbar kayitlari korelasyonu',
      category: 'Kolluk - Operasyonel',
      createdAt: '2026-06-01T00:00:00Z',
      updatedAt: '2026-06-28T00:00:00Z',
      runs: 0,
      tags: ['kolluk', 'cooccurrence', 'ihbar', 'operasyonel'],
      nodes: [
        { id: 'ihbar', type: 'custom', position: { x: 50, y: 100 }, data: { label: 'Ihbar Kayitlari', type: 'ihbar_source', category: 'Kolluk Data', icon: 'PhoneCall', color: '#dc2626', config: { category: 'all', startDate: '2026-01-01', location: 'Istanbul', legalBasis: '5271-md-3', kvkkClass: 'Kisitli' }, status: 'idle' } },
        { id: 'mobese', type: 'custom', position: { x: 50, y: 300 }, data: { label: 'MOBESE Kamera', type: 'mobese_source', category: 'Kolluk Data', icon: 'Video', color: '#dc2626', config: { cameraId: '', region: 'Istanbul', eventType: 'all', legalBasis: '2559-md-4', kvkkClass: 'Kisitli' }, status: 'idle' } },
        { id: 'cooc', type: 'custom', position: { x: 350, y: 100 }, data: { label: 'Es-Olusum Analizi', type: 'cooccurrence', category: 'Kolluk Analysis', icon: 'Users', color: '#7c3aed', config: { entityColumn: 'ihbar_id', contextColumn: 'location', minOccurrences: 2 }, status: 'idle' } },
        { id: 'dq', type: 'custom', position: { x: 350, y: 300 }, data: { label: 'Veri Kalitesi', type: 'data_quality', category: 'Processing', icon: 'ShieldCheck', color: '#f59e0b', config: { columns: '' }, status: 'idle' } },
        { id: 'alert', type: 'custom', position: { x: 650, y: 100 }, data: { label: 'Alert', type: 'alert', category: 'Output', icon: 'Bell', color: '#ec4899', config: { condition: 'count_greater_than', threshold: 5, channel: 'email' }, status: 'idle' } },
        { id: 'export', type: 'custom', position: { x: 650, y: 300 }, data: { label: 'Rapor Export', type: 'export', category: 'Output', icon: 'Download', color: '#ec4899', config: { format: 'csv', filename: 'kollup_rapor' }, status: 'idle' } },
      ],
      edges: [
        { id: 'e1', source: 'ihbar', target: 'cooc' },
        { id: 'e2', source: 'mobese', target: 'dq' },
        { id: 'e3', source: 'cooc', target: 'alert' },
        { id: 'e4', source: 'dq', target: 'export' },
      ]
    },
  ];
}
