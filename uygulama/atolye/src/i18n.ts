/**
 * Lightweight i18n for the UI chrome (English + Turkish).
 * Language lives in the Zustand store (see useStore.language). Use the `useT`
 * hook inside components to get a `t(key)` function that re-renders on switch.
 * Missing keys fall back to English, then to the raw key.
 */
import { useStore } from './store/useStore';

export type Lang = 'en' | 'tr';

export const LANGUAGES: { code: Lang; label: string }[] = [
  { code: 'en', label: 'EN' },
  { code: 'tr', label: 'TR' },
];

type Dict = Record<string, string>;

export const translations: Record<Lang, Dict> = {
  en: {
    // Toolbar
    run: 'Run',
    running: 'Running...',
    stop: 'Stop',
    stopTitle: 'Cancel the run (in-flight network requests are aborted; an evidence record in progress is allowed to finish)',
    demo: 'Demo',
    demoTitle: 'Load and run demo workflow',
    clear: 'Clear',
    save: 'Save',
    disk: 'Disk',
    diskTitle: 'Save to browser storage',
    load: 'Load',
    loadTitle: 'Load from browser storage',
    models: 'Models',
    validate: 'Validate',
    data: 'Data',
    results: 'Results',
    demoMode: 'Demo data',
    demoTitle2: 'These sources produce SYNTHETIC data — results downstream are not real findings and no evidence package is produced',
    nodes: 'nodes',
    edges: 'edges',
    executing: 'Executing...',
    workflowValid: 'Workflow is valid. Ready to execute.',
    error: 'Error',
    warning: 'Warning',
    // Sidebar tabs
    tab_nodes: 'Nodes',
    tab_models: 'Models',
    tab_catalog: 'Catalog',
    tab_settings: 'Settings',
    // Settings panel
    settings_execution: 'Execution',
    settings_parallel: 'Parallel execution',
    settings_cache: 'Cache results',
    settings_performance: 'Performance',
    settings_memory: 'Memory Limit',
    settings_export: 'Export',
    settings_exportPy: 'Export as Python Script',
    settings_exportPyHint: 'Runnable pandas/scikit-learn script for {n} node(s).',
    settings_exportPyEmpty: 'Add nodes to the canvas first.',
    settings_shortcuts: 'Keyboard Shortcuts',
    settings_language: 'Language',
    // Property panel
    prop_selectNode: 'Select a node to configure its properties',
  },
  tr: {
    // Toolbar
    run: 'Çalıştır',
    running: 'Çalışıyor...',
    stop: 'Durdur',
    stopTitle: 'Koşuyu iptal et (süren ağ istekleri kesilir; yürüyen kanıt kaydının bitmesine izin verilir)',
    demo: 'Demo',
    demoTitle: 'Demo iş akışını yükle ve çalıştır',
    clear: 'Temizle',
    save: 'Kaydet',
    disk: 'Disk',
    diskTitle: 'Tarayıcı deposuna kaydet',
    load: 'Yükle',
    loadTitle: 'Tarayıcı deposundan yükle',
    models: 'Modeller',
    validate: 'Doğrula',
    data: 'Veri',
    results: 'Sonuçlar',
    demoMode: 'Demo veri',
    demoTitle2: 'Bu kaynaklar SENTETİK veri üretir — ardındaki sonuçlar gerçek bulgu değildir, kanıt paketi üretilmez',
    nodes: 'düğüm',
    edges: 'bağlantı',
    executing: 'Yürütülüyor...',
    workflowValid: 'İş akışı geçerli. Çalıştırmaya hazır.',
    error: 'Hata',
    warning: 'Uyarı',
    // Sidebar tabs
    tab_nodes: 'Düğümler',
    tab_models: 'Modeller',
    tab_catalog: 'Katalog',
    tab_settings: 'Ayarlar',
    // Settings panel
    settings_execution: 'Yürütme',
    settings_parallel: 'Paralel yürütme',
    settings_cache: 'Sonuçları önbelleğe al',
    settings_performance: 'Performans',
    settings_memory: 'Bellek Sınırı',
    settings_export: 'Dışa Aktar',
    settings_exportPy: 'Python Betiği olarak dışa aktar',
    settings_exportPyHint: '{n} düğüm için çalıştırılabilir pandas/scikit-learn betiği.',
    settings_exportPyEmpty: 'Önce tuvale düğüm ekleyin.',
    settings_shortcuts: 'Klavye Kısayolları',
    settings_language: 'Dil',
    // Property panel
    prop_selectNode: 'Özelliklerini yapılandırmak için bir düğüm seçin',
  },
};

export function translate(lang: Lang, key: string): string {
  return translations[lang]?.[key] ?? translations.en[key] ?? key;
}

/** Hook: returns a `t(key)` bound to the current store language. */
export function useT(): (key: string) => string {
  const lang = useStore((s) => s.language);
  return (key: string) => translate(lang, key);
}
