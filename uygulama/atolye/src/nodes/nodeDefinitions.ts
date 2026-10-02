import { sucAnaliziNodes } from './sucAnaliziNodes.generated';

export interface NodeDefinition {
  type: string;
  label: string;
  category: string;
  icon: string;
  description: string;
  color: string;
  inputs: number;
  outputs: number;
  defaultConfig: Record<string, unknown>;
  configFields: ConfigField[];
}

export interface ConfigField {
  name: string;
  label: string;
  // 'column': yukarı akıştaki veriden sütun SEÇİLİR. Serbest metin yerine
  // bunu kullanın; kullanıcı sütun adını tahmin etmek zorunda kalmasın.
  type: 'text' | 'number' | 'select' | 'multiselect' | 'boolean' | 'textarea' | 'keyvalue' | 'column';
  /** 'column' alanları için sıralama ipucu: olası koordinat sütunları öne alınır. */
  sutunIpucu?: 'lat' | 'lng';
  options?: string[];
  default?: unknown;
  placeholder?: string;
  required?: boolean;
}

export const nodeDefinitions: NodeDefinition[] = [
  // DATA INPUT
  {
    type: 'csv_source',
    label: 'CSV Input',
    category: 'Data Input',
    icon: 'FileSpreadsheet',
    description: 'Import data from CSV file',
    color: '#10b981',
    inputs: 0,
    outputs: 1,
    defaultConfig: { filename: 'data.csv', delimiter: ',', hasHeader: true },
    configFields: [
      { name: 'filename', label: 'File Name', type: 'text', default: 'data.csv', required: true },
      { name: 'delimiter', label: 'Delimiter', type: 'select', options: [',', ';', '\t', '|'], default: ',' },
      { name: 'hasHeader', label: 'Has Header Row', type: 'boolean', default: true }
    ]
  },
  {
    type: 'logistic_regression',
    label: 'Logistic Regression',
    category: 'Analysis',
    icon: 'TrendingUp',
    description: 'Server-side Logistic Regression (ML service)',
    color: '#8b5cf6',
    inputs: 1,
    outputs: 1,
    defaultConfig: { target: '', c: 1.0, maxIter: 100, testSize: 20 },
    configFields: [
      { name: 'target', label: 'Target Column', type: 'text', placeholder: 'label', required: true },
      { name: 'c', label: 'Regularization (C)', type: 'number', default: 1.0 },
      { name: 'maxIter', label: 'Max Iterations', type: 'number', default: 100 },
      { name: 'testSize', label: 'Test Size (%)', type: 'number', default: 20 }
    ]
  },
  {
    type: 'svm',
    label: 'SVM',
    category: 'Analysis',
    icon: 'Target',
    description: 'Server-side SVM (ML service)',
    color: '#8b5cf6',
    inputs: 1,
    outputs: 1,
    defaultConfig: { target: '', task: 'classification', kernel: 'rbf', c: 1.0, testSize: 20 },
    configFields: [
      { name: 'target', label: 'Target Column', type: 'text', placeholder: 'label', required: true },
      { name: 'task', label: 'Task', type: 'select', options: ['classification', 'regression'], default: 'classification' },
      { name: 'kernel', label: 'Kernel', type: 'select', options: ['rbf', 'linear', 'poly', 'sigmoid'], default: 'rbf' },
      { name: 'c', label: 'Regularization (C)', type: 'number', default: 1.0 },
      { name: 'testSize', label: 'Test Size (%)', type: 'number', default: 20 }
    ]
  },
  {
    type: 'pca',
    label: 'PCA',
    category: 'Analysis',
    icon: 'Grid3x3',
    description: 'Server-side PCA (ML service)',
    color: '#8b5cf6',
    inputs: 1,
    outputs: 1,
    defaultConfig: { features: '', nComponents: 2 },
    configFields: [
      { name: 'features', label: 'Feature Columns', type: 'text', placeholder: 'x, y, z', required: true },
      { name: 'nComponents', label: 'Components', type: 'number', default: 2 }
    ]
  },
  {
    type: 'gradient_boosting',
    label: 'Gradient Boosting (XGBoost)',
    category: 'Analysis',
    icon: 'TrendingUp',
    description: 'Server-side Gradient Boosting (ML service)',
    color: '#8b5cf6',
    inputs: 1,
    outputs: 1,
    defaultConfig: { target: '', task: 'classification', nEstimators: 100, maxDepth: 3, learningRate: 0.1, testSize: 20 },
    configFields: [
      { name: 'target', label: 'Target Column', type: 'text', placeholder: 'label', required: true },
      { name: 'task', label: 'Task', type: 'select', options: ['classification', 'regression'], default: 'classification' },
      { name: 'nEstimators', label: 'Trees (n_estimators)', type: 'number', default: 100 },
      { name: 'maxDepth', label: 'Max Depth', type: 'number', default: 3 },
      { name: 'learningRate', label: 'Learning Rate', type: 'number', default: 0.1 },
      { name: 'testSize', label: 'Test Size (%)', type: 'number', default: 20 }
    ]
  },
  {
    type: 'db_source',
    label: 'Database Query',
    category: 'Data Input',
    icon: 'Database',
    description: 'Query data from SQL database',
    color: '#10b981',
    inputs: 0,
    outputs: 1,
    defaultConfig: { connection: '', table: '', query: 'SELECT * FROM table' },
    configFields: [
      { name: 'connection', label: 'Connection String', type: 'text', placeholder: 'postgresql://...', required: true },
      { name: 'table', label: 'Table Name', type: 'text', placeholder: 'users' },
      { name: 'query', label: 'SQL Query', type: 'textarea', default: 'SELECT * FROM table', placeholder: 'SELECT * FROM table WHERE...' }
    ]
  },
  {
    type: 'api_source',
    label: 'API Endpoint',
    category: 'Data Input',
    icon: 'Globe',
    description: 'Fetch data from REST API',
    color: '#10b981',
    inputs: 0,
    outputs: 1,
    defaultConfig: { url: '', method: 'GET', headers: '{}' },
    configFields: [
      { name: 'url', label: 'API URL', type: 'text', placeholder: 'https://api.example.com/data', required: true },
      { name: 'method', label: 'HTTP Method', type: 'select', options: ['GET', 'POST', 'PUT'], default: 'GET' },
      { name: 'headers', label: 'Headers (JSON)', type: 'textarea', default: '{}', placeholder: '{"Authorization": "Bearer token"}' }
    ]
  },
  // DATA PROCESSING
  {
    type: 'filter',
    label: 'Filter Rows',
    category: 'Processing',
    icon: 'Filter',
    description: 'Filter rows based on conditions',
    color: '#f59e0b',
    inputs: 1,
    outputs: 1,
    defaultConfig: { condition: 'equals', column: '', value: '' },
    configFields: [
      { name: 'column', label: 'Column', type: 'text', placeholder: 'age', required: true },
      { name: 'condition', label: 'Condition', type: 'select', options: ['equals', 'not_equals', 'greater_than', 'less_than', 'contains', 'starts_with', 'is_null', 'not_null'], default: 'equals' },
      { name: 'value', label: 'Value', type: 'text', placeholder: '18' }
    ]
  },
  {
    type: 'extend_field',
    label: 'Extend Field',
    category: 'Processing',
    icon: 'PlusCircle',
    description: 'Add computed columns to dataset',
    color: '#f59e0b',
    inputs: 1,
    outputs: 1,
    defaultConfig: { newColumn: '', expression: '' },
    configFields: [
      { name: 'newColumn', label: 'New Column Name', type: 'text', placeholder: 'full_name', required: true },
      { name: 'expression', label: 'Expression', type: 'textarea', default: '', placeholder: 'CONCAT(first_name, " ", last_name)' }
    ]
  },
  {
    type: 'aggregate',
    label: 'Aggregate',
    category: 'Processing',
    icon: 'BarChart3',
    description: 'Group and aggregate data',
    color: '#f59e0b',
    inputs: 1,
    outputs: 1,
    defaultConfig: { groupBy: '', aggregations: [], valueColumn: '' },
    configFields: [
      { name: 'groupBy', label: 'Group By Column', type: 'text', placeholder: 'category', required: true },
      { name: 'aggregations', label: 'Aggregations', type: 'multiselect', options: ['COUNT', 'SUM', 'AVG', 'MAX', 'MIN', 'STDEV'], default: ['COUNT'] },
      { name: 'valueColumn', label: 'Değer Sütunu (SUM/AVG/...; boş = ilk sayısal)', type: 'column', placeholder: 'ör. zarar_tl' }
    ]
  },
  {
    type: 'sort',
    label: 'Sort',
    category: 'Processing',
    icon: 'ArrowUpDown',
    description: 'Sort data by columns',
    color: '#f59e0b',
    inputs: 1,
    outputs: 1,
    defaultConfig: { columns: '', order: 'asc' },
    configFields: [
      { name: 'columns', label: 'Sort Columns', type: 'text', placeholder: 'date, name', required: true },
      { name: 'order', label: 'Sort Order', type: 'select', options: ['asc', 'desc'], default: 'asc' }
    ]
  },
  {
    type: 'join',
    label: 'Join Tables',
    category: 'Processing',
    icon: 'Merge',
    description: 'Merge two datasets by key',
    color: '#f59e0b',
    inputs: 2,
    outputs: 1,
    defaultConfig: { joinType: 'inner', leftKey: '', rightKey: '' },
    configFields: [
      { name: 'joinType', label: 'Join Type', type: 'select', options: ['inner', 'left', 'right', 'full'], default: 'inner' },
      { name: 'leftKey', label: 'Left Key Column', type: 'text', placeholder: 'user_id', required: true },
      { name: 'rightKey', label: 'Right Key Column', type: 'text', placeholder: 'user_id', required: true }
    ]
  },
  {
    type: 'dedup',
    label: 'Deduplicate',
    category: 'Processing',
    icon: 'CopyMinus',
    description: 'Remove duplicate rows',
    color: '#f59e0b',
    inputs: 1,
    outputs: 1,
    defaultConfig: { keyColumns: '', keep: 'first' },
    configFields: [
      { name: 'keyColumns', label: 'Key Columns', type: 'text', placeholder: 'email, phone' },
      { name: 'keep', label: 'Keep', type: 'select', options: ['first', 'last'], default: 'first' }
    ]
  },
  {
    type: 'data_clean',
    label: 'Data Cleaning',
    category: 'Processing',
    icon: 'Wand2',
    description: 'Handle missing values (drop/mean/median/mode/constant/ffill) + trim + dedup',
    color: '#f59e0b',
    inputs: 1,
    outputs: 1,
    defaultConfig: { columns: '', strategy: 'drop_rows', fillValue: '', trimWhitespace: false, dropDuplicates: false },
    configFields: [
      { name: 'columns', label: 'Columns (blank = all)', type: 'text', placeholder: 'age, income' },
      { name: 'strategy', label: 'Missing Value Strategy', type: 'select', options: ['drop_rows', 'mean', 'median', 'mode', 'zero', 'constant', 'ffill'], default: 'drop_rows' },
      { name: 'fillValue', label: 'Constant Fill Value', type: 'text', placeholder: 'for constant strategy' },
      { name: 'trimWhitespace', label: 'Trim Whitespace', type: 'boolean', default: false },
      { name: 'dropDuplicates', label: 'Remove Duplicate Rows', type: 'boolean', default: false }
    ]
  },
  {
    type: 'block_group',
    label: 'Block Group',
    category: 'Processing',
    icon: 'Rows3',
    description: 'Reconstruct merged-cell exports: assign a block ID and fill values WITHIN the block only',
    color: '#f59e0b',
    inputs: 1,
    outputs: 1,
    defaultConfig: { markerColumn: '', idColumn: 'blok_id', fillColumns: '' },
    configFields: [
      { name: 'markerColumn', label: 'Blok Başlangıç Sütunu', type: 'column', placeholder: 'yalnız ilk satırda dolu olan sütun', required: true },
      { name: 'idColumn', label: 'Üretilecek Kimlik Sütunu', type: 'text', default: 'blok_id' },
      { name: 'fillColumns', label: 'Blok İçinde Doldurulacak Sütunlar', type: 'text', placeholder: 'tarih, saat, yer (boş = doldurma)' }
    ]
  },
  // ANALYSIS
  {
    type: 'statistics',
    label: 'Statistics',
    category: 'Analysis',
    icon: 'PieChart',
    description: 'Calculate descriptive statistics',
    color: '#8b5cf6',
    inputs: 1,
    outputs: 1,
    defaultConfig: { columns: '', stats: ['count', 'mean', 'std', 'min', 'max'] },
    configFields: [
      { name: 'columns', label: 'Numeric Columns', type: 'text', placeholder: 'age, income, score' },
      { name: 'stats', label: 'Statistics', type: 'multiselect', options: ['count', 'mean', 'median', 'std', 'min', 'max', 'sum'], default: ['count', 'mean', 'std', 'min', 'max'] }
    ]
  },
  {
    type: 'linear_regression',
    label: 'Linear Regression',
    category: 'Analysis',
    icon: 'TrendingUp',
    description: 'Train linear regression model',
    color: '#8b5cf6',
    inputs: 1,
    outputs: 1,
    defaultConfig: { target: '', features: '', testSize: 20 },
    configFields: [
      { name: 'target', label: 'Target Column', type: 'text', placeholder: 'sales_amount', required: true },
      { name: 'features', label: 'Feature Columns', type: 'text', placeholder: 'promo_days, discount, temperature' },
      { name: 'testSize', label: 'Test Size (%) — holdout; 0 = yalnız örneklem içi', type: 'number', default: 20 }
    ]
  },
  {
    type: 'dbscan',
    label: 'DBSCAN Clustering',
    category: 'Analysis',
    icon: 'Target',
    description: 'Server-side density-based clustering (DBSCAN)',
    color: '#8b5cf6',
    inputs: 1,
    outputs: 1,
    defaultConfig: { features: '', eps: 0.5, minSamples: 5 },
    configFields: [
      { name: 'features', label: 'Feature Columns', type: 'text', placeholder: 'x, y, z', required: true },
      { name: 'eps', label: 'Epsilon (eps)', type: 'number', default: 0.5 },
      { name: 'minSamples', label: 'Min Samples', type: 'number', default: 5 }
    ]
  },
  {
    type: 'arima',
    label: 'ARIMA Forecast',
    category: 'Analysis',
    icon: 'TrendingUp',
    description: 'Server-side ARIMA time-series forecasting',
    color: '#8b5cf6',
    inputs: 1,
    outputs: 1,
    defaultConfig: { target: '', dateColumn: '', p: 1, d: 1, q: 1, forecastSteps: 10 },
    configFields: [
      { name: 'target', label: 'Target Column', type: 'text', placeholder: 'sales', required: true },
      { name: 'dateColumn', label: 'Date Column (optional)', type: 'text', placeholder: 'date' },
      { name: 'p', label: 'AR Order (p)', type: 'number', default: 1 },
      { name: 'd', label: 'Differencing (d)', type: 'number', default: 1 },
      { name: 'q', label: 'MA Order (q)', type: 'number', default: 1 },
      { name: 'forecastSteps', label: 'Forecast Steps', type: 'number', default: 10 }
    ]
  },
  {
    type: 'hierarchical',
    label: 'Hierarchical Clustering',
    category: 'Analysis',
    icon: 'Target',
    description: 'Server-side Hierarchical Clustering (ML service)',
    color: '#8b5cf6',
    inputs: 1,
    outputs: 1,
    defaultConfig: { features: '', nClusters: 3, linkage: 'ward' },
    configFields: [
      { name: 'features', label: 'Feature Columns', type: 'text', placeholder: 'x, y, z', required: true },
      { name: 'nClusters', label: 'Clusters', type: 'number', default: 3 },
      { name: 'linkage', label: 'Linkage', type: 'select', options: ['ward', 'complete', 'average', 'single'], default: 'ward' }
    ]
  },
  {
    type: 'association_rules',
    label: 'Association Rules',
    category: 'Analysis',
    icon: 'Link2',
    description: 'Market basket analysis (Apriori)',
    color: '#8b5cf6',
    inputs: 1,
    outputs: 1,
    defaultConfig: { itemsColumn: '', minSupport: 0.05, minConfidence: 0.5 },
    configFields: [
      { name: 'itemsColumn', label: 'Items Column', type: 'text', placeholder: 'product_id', required: true },
      { name: 'minSupport', label: 'Min Support', type: 'number', default: 0.05 },
      { name: 'minConfidence', label: 'Min Confidence', type: 'number', default: 0.5 }
    ]
  },
  {
    type: 'clustering',
    label: 'K-Means Clustering',
    category: 'Analysis',
    icon: 'Target',
    description: 'Group data into clusters',
    color: '#8b5cf6',
    inputs: 1,
    outputs: 1,
    defaultConfig: { features: '', k: 3, maxIterations: 100, standardize: true },
    configFields: [
      { name: 'features', label: 'Feature Columns', type: 'text', placeholder: 'x, y, z', required: true },
      { name: 'k', label: 'Number of Clusters (K)', type: 'number', default: 3 },
      { name: 'maxIterations', label: 'Max Iterations', type: 'number', default: 100 },
      { name: 'standardize', label: 'Standardize (farklı birimli sütunlar; yalnız enlem/boylamda kapatın)', type: 'boolean', default: true }
    ]
  },
  {
    type: 'random_forest',
    label: 'Random Forest',
    category: 'Analysis',
    icon: 'Target',
    description: 'Server-side Random Forest (classification/regression)',
    color: '#8b5cf6',
    inputs: 1,
    outputs: 1,
    defaultConfig: { target: '', task: 'classification', nEstimators: 100, testSize: 20 },
    configFields: [
      { name: 'target', label: 'Target Column', type: 'text', placeholder: 'label', required: true },
      { name: 'task', label: 'Task', type: 'select', options: ['classification', 'regression'], default: 'classification' },
      { name: 'nEstimators', label: 'Trees (n_estimators)', type: 'number', default: 100 },
      { name: 'testSize', label: 'Test Size (%)', type: 'number', default: 20 }
    ]
  },
  {
    type: 'anomaly_detection',
    label: 'Anomaly Detection',
    category: 'Analysis',
    icon: 'AlertTriangle',
    description: 'Detect outliers using IQR or Z-score',
    color: '#8b5cf6',
    inputs: 1,
    outputs: 1,
    defaultConfig: { columns: '', method: 'iqr', threshold: 1.5 },
    configFields: [
      { name: 'columns', label: 'Columns to Check', type: 'text', placeholder: 'amount, frequency', required: true },
      // isolation_forest tarayıcı motorunda YOK (eskiden sessizce |z|>2'ydi);
      // gerçek IsolationForest Python dışa aktarımında.
      { name: 'method', label: 'Detection Method', type: 'select', options: ['iqr', 'zscore'], default: 'iqr' },
      { name: 'threshold', label: 'Threshold', type: 'number', default: 1.5 }
    ]
  },
  {
    type: 'correlation',
    label: 'Correlation Matrix',
    category: 'Analysis',
    icon: 'Grid3x3',
    description: 'Compute correlation between variables',
    color: '#8b5cf6',
    inputs: 1,
    outputs: 1,
    defaultConfig: { columns: '', method: 'pearson' },
    configFields: [
      { name: 'columns', label: 'Numeric Columns', type: 'text', placeholder: 'var1, var2, var3' },
      { name: 'method', label: 'Method', type: 'select', options: ['pearson', 'spearman', 'kendall'], default: 'pearson' }
    ]
  },
  // P2-1: Model Validation
  {
    type: 'model_validation',
    label: 'Model Validation',
    category: 'Analysis',
    icon: 'Crosshair',
    description: 'Classification metrics: confusion matrix, precision, recall, F1',
    color: '#8b5cf6',
    inputs: 1,
    outputs: 1,
    defaultConfig: { actualColumn: '', predictedColumn: '' },
    configFields: [
      { name: 'actualColumn', label: 'Actual Label Column', type: 'text', placeholder: 'label', required: true },
      { name: 'predictedColumn', label: 'Predicted Label Column', type: 'text', placeholder: 'prediction', required: true }
    ]
  },
  // P2-3: Data Quality
  {
    type: 'data_quality',
    label: 'Data Quality',
    category: 'Processing',
    icon: 'ShieldCheck',
    description: 'Analyze data quality: missing values, types, outliers, score',
    color: '#f59e0b',
    inputs: 1,
    outputs: 1,
    defaultConfig: { columns: '' },
    configFields: [
      { name: 'columns', label: 'Columns to Analyze (empty = all)', type: 'text', placeholder: 'col1, col2, col3' }
    ]
  },
  // P2-4: Cross-Validation
  {
    type: 'cross_validation',
    label: 'Cross-Validation',
    category: 'Analysis',
    icon: 'Shuffle',
    description: 'K-fold cross-validation for regression models',
    color: '#8b5cf6',
    inputs: 1,
    outputs: 1,
    defaultConfig: { target: '', features: '', k: 5, metric: 'r2' },
    configFields: [
      { name: 'target', label: 'Target Column', type: 'text', placeholder: 'sales', required: true },
      { name: 'features', label: 'Feature Columns', type: 'text', placeholder: 'promo, discount, temp' },
      { name: 'k', label: 'Number of Folds (K)', type: 'number', default: 5 },
      { name: 'metric', label: 'Primary Metric', type: 'select', options: ['r2', 'mse', 'mae', 'rmse'], default: 'r2' }
    ]
  },
  // AGENT (local LLM agent via /api/agent/*)
  {
    type: 'agent_insight',
    label: 'Agent Insight',
    category: 'Agent',
    icon: 'Bot',
    description: 'Interpret upstream results in natural language (local agent)',
    color: '#06b6d4',
    inputs: 1,
    outputs: 1,
    defaultConfig: { question: 'Summarize the key findings in this data.', tone: 'concise', language: 'English' },
    configFields: [
      { name: 'question', label: 'Question / Instruction', type: 'textarea', default: 'Summarize the key findings in this data.' },
      { name: 'tone', label: 'Tone', type: 'select', options: ['concise', 'detailed', 'executive'], default: 'concise' },
      { name: 'language', label: 'Language', type: 'select', options: ['English', 'Türkçe'], default: 'English' }
    ]
  },
  // KOLLUK DATA (Police-Specific Sources)
  {
    type: 'pts_source',
    label: 'PTS Sorgu',
    category: 'Kolluk Data',
    icon: 'Shield',
    description: 'Polis Taktik Sistemi - kisi/arac sorgusu',
    color: '#dc2626',
    inputs: 0,
    outputs: 1,
    defaultConfig: { queryType: 'person', queryValue: '', legalBasis: '5271-md-3', kvkkClass: 'Gizli' },
    configFields: [
      { name: 'queryType', label: 'Sorgu Tipi', type: 'select', options: ['person', 'vehicle', 'address'], default: 'person' },
      { name: 'queryValue', label: 'Sorgu Degeri', type: 'text', placeholder: 'TC Kimlik No veya Plaka', required: true },
      { name: 'legalBasis', label: 'Hukuki Dayanak', type: 'select', options: ['5271-md-3', '5271-md-4', '2559-md-4', '6638-md-6'], default: '5271-md-3', required: true },
      { name: 'kvkkClass', label: 'KVKK Siniflandirmasi', type: 'select', options: ['Kisitli', 'Gizli', 'Cok Gizli'], default: 'Gizli', required: true }
    ]
  },
  {
    type: 'anpr_source',
    label: 'ANPR Plaka',
    category: 'Kolluk Data',
    icon: 'Camera',
    description: 'Otomatik plaka tanima sistem verisi',
    color: '#dc2626',
    inputs: 0,
    outputs: 1,
    defaultConfig: { plate: '', startDate: '', endDate: '', legalBasis: '2559-md-4', kvkkClass: 'Kisitli' },
    configFields: [
      { name: 'plate', label: 'Plaka', type: 'text', placeholder: '34ABC123' },
      { name: 'startDate', label: 'Baslangic Tarihi', type: 'text', placeholder: '2026-01-01' },
      { name: 'endDate', label: 'Bitis Tarihi', type: 'text', placeholder: '2026-06-30' },
      { name: 'legalBasis', label: 'Hukuki Dayanak', type: 'select', options: ['5271-md-3', '2559-md-4', '6638-md-6'], default: '2559-md-4', required: true },
      { name: 'kvkkClass', label: 'KVKK Siniflandirmasi', type: 'select', options: ['Kisitli', 'Gizli', 'Cok Gizli'], default: 'Kisitli', required: true }
    ]
  },
  {
    type: 'mobese_source',
    label: 'MOBESE Kamera',
    category: 'Kolluk Data',
    icon: 'Video',
    description: 'MOBESE kamera metadata sorgusu',
    color: '#dc2626',
    inputs: 0,
    outputs: 1,
    defaultConfig: { cameraId: '', region: '', eventType: 'all', legalBasis: '2559-md-4', kvkkClass: 'Kisitli' },
    configFields: [
      { name: 'cameraId', label: 'Kamera ID', type: 'text', placeholder: 'MBS-001' },
      { name: 'region', label: 'Bolge', type: 'text', placeholder: 'Istanbul-Beyoglu' },
      { name: 'eventType', label: 'Olay Tipi', type: 'select', options: ['all', 'vehicle', 'person', 'crowd', 'fight'], default: 'all' },
      { name: 'legalBasis', label: 'Hukuki Dayanak', type: 'select', options: ['5271-md-3', '2559-md-4', '6638-md-6'], default: '2559-md-4', required: true },
      { name: 'kvkkClass', label: 'KVKK Siniflandirmasi', type: 'select', options: ['Kisitli', 'Gizli', 'Cok Gizli'], default: 'Kisitli', required: true }
    ]
  },
  {
    type: 'ihbar_source',
    label: 'Ihbar Kayitlari',
    category: 'Kolluk Data',
    icon: 'PhoneCall',
    description: '155/156 ihbar veritabani sorgusu',
    color: '#dc2626',
    inputs: 0,
    outputs: 1,
    defaultConfig: { category: 'all', startDate: '', location: '', legalBasis: '5271-md-3', kvkkClass: 'Kisitli' },
    configFields: [
      { name: 'category', label: 'Ihbar Kategorisi', type: 'select', options: ['all', 'gurultu', 'siddet', 'hirsizlik', 'trafik', 'kacakcilik', 'teror'], default: 'all' },
      { name: 'location', label: 'Lokasyon', type: 'text', placeholder: 'Istanbul' },
      { name: 'startDate', label: 'Baslangic Tarihi', type: 'text', placeholder: '2026-01-01' },
      { name: 'legalBasis', label: 'Hukuki Dayanak', type: 'select', options: ['5271-md-3', '2559-md-4', '6638-md-6'], default: '5271-md-3', required: true },
      { name: 'kvkkClass', label: 'KVKK Siniflandirmasi', type: 'select', options: ['Kisitli', 'Gizli', 'Cok Gizli'], default: 'Kisitli', required: true }
    ]
  },
  {
    type: 'adli_sicil_source',
    label: 'Adli Sicil',
    category: 'Kolluk Data',
    icon: 'Scale',
    description: 'Adli sicil kaydi sorgusu',
    color: '#dc2626',
    inputs: 0,
    outputs: 1,
    defaultConfig: { tcKimlik: '', court: '', legalBasis: '5271-md-3', kvkkClass: 'Cok Gizli' },
    configFields: [
      { name: 'tcKimlik', label: 'TC Kimlik No', type: 'text', placeholder: '12345678901', required: true },
      { name: 'court', label: 'Mahkeme', type: 'text', placeholder: 'Istanbul AGY' },
      { name: 'legalBasis', label: 'Hukuki Dayanak', type: 'select', options: ['5271-md-3', '5271-md-4', '5275-md-7'], default: '5271-md-3', required: true },
      { name: 'kvkkClass', label: 'KVKK Siniflandirmasi', type: 'select', options: ['Gizli', 'Cok Gizli'], default: 'Cok Gizli', required: true }
    ]
  },
  // KOLLUK ANALYSIS (Police-Specific Analysis)
  {
    type: 'sna',
    label: 'Sosyal Ag Analizi',
    category: 'Kolluk Analysis',
    icon: 'Network',
    description: 'Supheli sosyal ag analizi - merkeziyet, baglantilar',
    color: '#7c3aed',
    inputs: 1,
    outputs: 1,
    defaultConfig: { personColumn: '', linkColumn: '', method: 'degree' },
    configFields: [
      { name: 'personColumn', label: 'Kisi Kolonu', type: 'text', placeholder: 'person_id', required: true },
      { name: 'linkColumn', label: 'Baglanti Kolonu', type: 'text', placeholder: 'associate_id', required: true },
      { name: 'method', label: 'Analiz Metodu', type: 'select', options: ['degree', 'betweenness', 'closeness'], default: 'degree' }
    ]
  },
  {
    type: 'geo_hotspot',
    label: 'Cografi Hotspot',
    category: 'Kolluk Analysis',
    icon: 'MapPin',
    description: 'Lokasyon bazli sicak nokta haritalandirma',
    color: '#7c3aed',
    inputs: 1,
    outputs: 1,
    defaultConfig: { latColumn: '', lngColumn: '', weightColumn: '', gridSize: 0.01 },
    configFields: [
      { name: 'latColumn', label: 'Enlem Kolonu', type: 'column', sutunIpucu: 'lat', placeholder: 'ör. Koordinat Enlem', required: true },
      { name: 'lngColumn', label: 'Boylam Kolonu', type: 'column', sutunIpucu: 'lng', placeholder: 'ör. Koordinat Boylam', required: true },
      { name: 'weightColumn', label: 'Agirlik Kolonu', type: 'column', placeholder: 'boş = her olay 1 sayılır' },
      { name: 'gridSize', label: 'Grid Boyutu (km)', type: 'number', default: 0.01 }
    ]
  },
  {
    type: 'temporal_pattern',
    label: 'Zamansal Oruntu',
    category: 'Kolluk Analysis',
    icon: 'Clock',
    description: 'Zaman bazli olay korelasyon ve oruntu tespiti',
    color: '#7c3aed',
    inputs: 1,
    outputs: 1,
    defaultConfig: { timeColumn: '', categoryColumn: '', bucket: 'hour' },
    configFields: [
      { name: 'timeColumn', label: 'Zaman Kolonu', type: 'text', placeholder: 'timestamp', required: true },
      { name: 'categoryColumn', label: 'Kategori Kolonu', type: 'text', placeholder: 'olay_turu' },
      { name: 'bucket', label: 'Zaman Dilimi', type: 'select', options: ['hour', 'day', 'week', 'month'], default: 'hour' }
    ]
  },
  {
    type: 'cooccurrence',
    label: 'Es-Olusum Analizi',
    category: 'Kolluk Analysis',
    icon: 'Users',
    description: 'Supheli es-olusum analizi (adres, arac, iletisim)',
    color: '#7c3aed',
    inputs: 1,
    outputs: 1,
    defaultConfig: { entityColumn: '', contextColumn: '', minOccurrences: 2 },
    configFields: [
      { name: 'entityColumn', label: 'Varlik Kolonu', type: 'text', placeholder: 'suspect_id', required: true },
      { name: 'contextColumn', label: 'Baglam Kolonu', type: 'text', placeholder: 'address', required: true },
      { name: 'minOccurrences', label: 'Min. Es-Olusum', type: 'number', default: 2 }
    ]
  },
  // OUTPUT
  {
    type: 'chart',
    label: 'Chart',
    category: 'Output',
    icon: 'BarChart',
    description: 'Visualize data with charts',
    color: '#ec4899',
    inputs: 1,
    outputs: 0,
    defaultConfig: { chartType: 'bar', xColumn: '', yColumn: '', title: '' },
    configFields: [
      // heatmap çizilmiyordu (sessizce çubuk); eski yapılandırma uyarıyla çubuğa düşer.
      { name: 'chartType', label: 'Chart Type', type: 'select', options: ['bar', 'line', 'pie', 'scatter', 'area'], default: 'bar' },
      { name: 'xColumn', label: 'X Axis Column', type: 'column', placeholder: 'boş = ilk metin sütunu' },
      { name: 'yColumn', label: 'Y Axis Column', type: 'column', placeholder: 'boş = ilk 3 sayısal sütun' },
      { name: 'title', label: 'Chart Title', type: 'text', placeholder: 'Sales by Category' }
    ]
  },
  {
    type: 'export',
    label: 'Export Data',
    category: 'Output',
    icon: 'Download',
    description: 'Export results to file',
    color: '#ec4899',
    inputs: 1,
    outputs: 0,
    defaultConfig: { format: 'csv', filename: 'output.csv' },
    configFields: [
      { name: 'format', label: 'Export Format', type: 'select', options: ['csv', 'json', 'excel', 'parquet'], default: 'csv' },
      { name: 'filename', label: 'Output File Name', type: 'text', default: 'output.csv' }
    ]
  },
  {
    type: 'alert',
    label: 'Alert',
    category: 'Output',
    icon: 'Bell',
    description: 'Trigger alert when condition met',
    color: '#ec4899',
    inputs: 1,
    outputs: 0,
    defaultConfig: { condition: 'count_greater_than', threshold: 0, channel: 'email' },
    configFields: [
      { name: 'condition', label: 'Trigger Condition', type: 'select', options: ['count_greater_than', 'count_less_than', 'value_greater_than', 'value_less_than'], default: 'count_greater_than' },
      { name: 'threshold', label: 'Threshold', type: 'number', default: 0 },
      { name: 'channel', label: 'Alert Channel', type: 'select', options: ['email', 'sms', 'webhook'], default: 'email' }
    ]
  },
  {
    type: 'evidence_export',
    label: 'Evidence Export',
    category: 'Output',
    icon: 'FileLock',
    description: 'Integrity-hashed (SHA-256) evidence package, recorded in a signed evidence ledger',
    color: '#dc2626',
    inputs: 1,
    outputs: 0,
    defaultConfig: { caseNumber: '', officerId: '', format: 'json' },
    configFields: [
      { name: 'caseNumber', label: 'Dosya/Esas No', type: 'text', placeholder: '2026/1234', required: true },
      { name: 'officerId', label: 'Memur Sicil No', type: 'text', placeholder: 'PN-12345', required: true },
      // pdf/signed_json üretilmiyordu (her ikisi de düz JSON'du); paket JSON + defter makbuzu.
      { name: 'format', label: 'Format', type: 'select', options: ['json'], default: 'json' }
    ]
  },
  // suc_analizi çekirdeğinden otomatik üretilen node'lar (scripts/generate_suc_nodes.py)
  ...sucAnaliziNodes
];

export const getNodeCategories = (): string[] => {
  const cats = new Set(nodeDefinitions.map((n) => n.category));
  return Array.from(cats);
};

export const getNodesByCategory = (category: string): NodeDefinition[] => {
  return nodeDefinitions.filter((n) => n.category === category);
};

export const getNodeDefinition = (type: string): NodeDefinition | undefined => {
  return nodeDefinitions.find((n) => n.type === type);
};
