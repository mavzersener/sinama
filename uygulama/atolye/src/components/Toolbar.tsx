import { useStore } from '../store/useStore';
import {
  Play, Loader2, Square, Trash2, Save, FolderOpen, Undo2, Redo2,
  Box, Link2, Activity, Table2, AlertCircle, CheckCircle2,
  FlaskConical, HardDrive, Sparkles, Keyboard, Wand2, Compass, GraduationCap
} from 'lucide-react';
import { useState, useCallback, useRef } from 'react';
import { validateWorkflow, demoKaynagiMi } from '../engine/executionEngine';
import { calistirIsAkisi } from '../engine/yurutucu';
import { buildWorkflow, intentAciklama } from '../lib/flowGenerator';
import CloudSync from './CloudSync';
import { useT } from '../i18n';
import { trpc } from '@/providers/trpc';

export default function Toolbar() {
  const t = useT();
  const {
    nodes,
    edges,
    isRunning,
    setIsRunning,
    setShowResults,
    setExecutionResults,
    addLog,
    clearLogs,
    updateNodeStatus,
    setNodeResult,
    setSelectedNode,
    addSavedModel,
    undo,
    redo,
    canUndo,
    canRedo,
    showResults,
    showDataPreview,
    setShowDataPreview,
    setDataPreviewNodeId,
    pushHistory
  } = useStore();

  // Koşu kalıcılaştırma: buluta kayıtlı workflow'larda her koşu executions
  // tablosuna yazılır (başarısızlık akışı bozmaz — sessizce atlanır).
  const cloudWorkflowId = useStore((s) => s.cloudWorkflowId);
  const executeMutation = trpc.workflow.execute.useMutation();
  const completeMutation = trpc.workflow.completeExecution.useMutation();

  const [validationErrors, setValidationErrors] = useState<Array<{ nodeLabel: string; message: string; severity: string }>>([]);
  const [showValidation, setShowValidation] = useState(false);
  const [showKeyboardHelp, setShowKeyboardHelp] = useState(false);
  const [showToast, setShowToast] = useState<{ message: string; type: 'success' | 'error' | 'info'; visible: boolean } | null>(null);
  const [goalOpen, setGoalOpen] = useState(false);
  const [goalText, setGoalText] = useState('');

  const toast = useCallback((message: string, type: 'success' | 'error' | 'info' = 'info') => {
    setShowToast({ message, type, visible: true });
    setTimeout(() => setShowToast(null), 3000);
  }, []);

  // P1-1: Auto-save on run
  const handleSaveToDisk = () => {
    // Başarısızlığı depo kendisi günlüğe yazar; burada yalnız başarı bildirilir.
    if (useStore.getState().saveToLocalStorage()) addLog('Workflow saved to browser storage');
  };

  // P1-1: Load from disk
  const handleLoadFromDisk = () => {
    const ok = useStore.getState().loadFromLocalStorage();
    addLog(ok ? 'Workflow loaded from browser storage' : 'No saved workflow found');
  };

  // Koşunun iptal denetleyicisi: "Durdur" düğmesi bunu tetikler.
  const kosuDenetleyici = useRef<AbortController | null>(null);

  /**
   * Tek koşu yolu (normal ve demo). Yürütücü bağımlılık sırasıyla, bağımsız
   * dalları eşzamanlı çalıştırır; yapay bekleme yok (eskiden düğüm başına
   * 0,6–1,4 sn "UX için" gecikme vardı). İlk hatada durur; Durdur iptal eder.
   */
  const kos = async (workflowNodes: typeof nodes, workflowEdges: typeof edges, secenek: { demo?: boolean } = {}) => {
    if (useStore.getState().isRunning) return;
    const errors = validateWorkflow(workflowNodes, workflowEdges);
    const criticalErrors = errors.filter((e) => e.severity === 'error');
    if (criticalErrors.length > 0) {
      setValidationErrors(errors.map((e) => ({ nodeLabel: e.nodeLabel, message: e.message, severity: e.severity })));
      setShowValidation(true);
      criticalErrors.forEach((e) => addLog(`Validation Error: ${e.message}`));
      if (secenek.demo) toast('Workflow has errors', 'error');
      return;
    }

    setShowValidation(false);
    setValidationErrors([]);
    setIsRunning(true);
    clearLogs();
    setShowResults(false);
    setShowDataPreview(false);
    setDataPreviewNodeId(null);
    setSelectedNode(null);
    addLog(secenek.demo ? 'Auto-running demo workflow...' : 'Starting workflow execution...');

    // Koşuyu kalıcılaştır (yalnız buluta kayıtlı workflow'larda; hata akışı bozmaz)
    let executionId: number | null = null;
    if (cloudWorkflowId != null) {
      try {
        const r = await executeMutation.mutateAsync({
          workflowId: cloudWorkflowId,
          nodeCount: workflowNodes.length,
          edgeCount: workflowEdges.length,
        });
        executionId = r.executionId;
        addLog(`Execution #${executionId} recorded.`);
      } catch {
        addLog('Execution record skipped (offline/unauthenticated).');
      }
    }

    workflowNodes.forEach((node) => updateNodeStatus(node.id, 'idle'));
    const etiket = (id: string) => workflowNodes.find((n) => n.id === id)?.data.label ?? id;
    const denetleyici = new AbortController();
    kosuDenetleyici.current = denetleyici;

    let sonuc;
    try {
      sonuc = await calistirIsAkisi({
        nodes: workflowNodes,
        edges: workflowEdges,
        sinyal: denetleyici.signal,
        olaylar: {
          basladi: (id) => {
            updateNodeStatus(id, 'running');
            addLog(`Executing: ${etiket(id)}...`);
          },
          bitti: (id, r) => {
            setNodeResult(id, r);
            updateNodeStatus(id, 'completed');
            addLog(`Completed: ${etiket(id)} (${r.rowCount?.toLocaleString() || 0} rows)`);
          },
          hata: (id, r) => {
            setNodeResult(id, r);
            updateNodeStatus(id, 'error');
            addLog(`Error in ${etiket(id)}: ${r.error}`);
          },
          kesildi: (id) => {
            updateNodeStatus(id, 'idle');
            addLog(`Kesildi: ${etiket(id)}`);
          },
        },
      });
    } finally {
      kosuDenetleyici.current = null;
    }

    const saniye = (sonuc.sureMs / 1000).toFixed(1);
    if (sonuc.durum === 'tamamlandi') {
      addLog(`Workflow execution completed successfully! (${saniye} sn)`);
    } else if (sonuc.durum === 'hata') {
      const kalan = sonuc.baslamayanlar.length + sonuc.kesilenler.length;
      addLog(`Koşu "${etiket(sonuc.hataDugumu!)}" hatasıyla durdu${kalan ? `; ${kalan} düğüm çalışmadı` : ''} (${saniye} sn).`);
    } else {
      addLog(`Koşu iptal edildi; ${sonuc.sonuclar.size} düğüm tamamlanmıştı (${saniye} sn).`);
    }

    if (executionId != null) {
      const summary: Record<string, unknown> = {};
      sonuc.sonuclar.forEach((r, id) => {
        summary[id] = { status: r.status, rowCount: r.rowCount ?? null };
      });
      try {
        await completeMutation.mutateAsync({
          executionId,
          status: sonuc.durum === 'tamamlandi' ? 'completed' : sonuc.durum === 'hata' ? 'failed' : 'cancelled',
          results: summary,
        });
      } catch {
        addLog('Execution completion record failed (non-fatal).');
      }
    }

    setExecutionResults(sonuc.sonuclar);
    setIsRunning(false);
    setShowResults(true);
    if (sonuc.durum === 'iptal') toast('Koşu iptal edildi', 'info');
    if (sonuc.durum !== 'tamamlandi') return;

    pushHistory();
    // P1-1: Auto-save to localStorage after successful run
    useStore.getState().saveToLocalStorage();
    // P1-2: Audit log
    useStore.getState().addAuditLog({
      timestamp: new Date().toISOString(),
      action: 'execute',
      // (Eskiden Object.keys(Map) → hep "0 results" yazıyordu.)
      details: `Executed ${workflowNodes.length} nodes, ${sonuc.sonuclar.size} results in ${saniye}s`,
      userAgent: navigator.userAgent
    });
    if (secenek.demo) toast('Demo workflow executed successfully!', 'success');
  };

  const handleRun = () => kos(nodes, edges);
  const handleStop = () => kosuDenetleyici.current?.abort();

  const handleClear = () => {
    useStore.getState().setNodes([]);
    useStore.getState().setEdges([]);
    clearLogs();
    setShowResults(false);
    setShowDataPreview(false);
    setDataPreviewNodeId(null);
    setValidationErrors([]);
    setShowValidation(false);
  };

  // Hedeften akış: düz metin amaç → otomatik iş akışı iskeleti
  const handleCompose = () => {
    const goal = goalText.trim();
    if (!goal) {
      toast('Önce yapmak istediğiniz analizi yazın.', 'info');
      return;
    }
    const { nodes: genNodes, edges: genEdges, intent } = buildWorkflow(goal);
    if (genNodes.length === 0) {
      toast('Bu amaç için akış üretilemedi.', 'error');
      return;
    }
    pushHistory();
    useStore.getState().setNodes(genNodes);
    useStore.getState().setEdges(genEdges);
    setSelectedNode(null);
    clearLogs();
    addLog(`Hedeften akış üretildi (niyet: ${intent}): ${genNodes.map((n) => n.data.type).join(' -> ')}`);
    toast(`Akış oluşturuldu: ${intentAciklama(goal)}`, 'success');
    setGoalOpen(false);
  };

  // P4-3: One-click demo workflow
  const handleDemo = async () => {
    if (isRunning) return;
    toast('Loading demo workflow...', 'info');

    // Build a showcase workflow
    const demoNodes = [
      { id: 'demo-csv', type: 'custom' as const, position: { x: 50, y: 80 }, data: { label: 'Sales Data', type: 'csv_source', category: 'Data Input', icon: 'FileSpreadsheet', color: '#10b981', config: { filename: 'sales.csv', delimiter: ',', hasHeader: true }, status: 'idle' as const } },
      { id: 'demo-dq', type: 'custom' as const, position: { x: 350, y: 80 }, data: { label: 'Data Quality', type: 'data_quality', category: 'Processing', icon: 'ShieldCheck', color: '#f59e0b', config: { columns: '' }, status: 'idle' as const } },
      { id: 'demo-stats', type: 'custom' as const, position: { x: 50, y: 280 }, data: { label: 'Statistics', type: 'statistics', category: 'Analysis', icon: 'PieChart', color: '#8b5cf6', config: { columns: 'income,score', stats: ['count', 'mean', 'std', 'min', 'max'] }, status: 'idle' as const } },
      { id: 'demo-corr', type: 'custom' as const, position: { x: 350, y: 280 }, data: { label: 'Correlation', type: 'correlation', category: 'Analysis', icon: 'Grid3X3', color: '#8b5cf6', config: { columns: 'age,income,score', method: 'pearson' }, status: 'idle' as const } },
      { id: 'demo-anomaly', type: 'custom' as const, position: { x: 650, y: 80 }, data: { label: 'Anomaly Detection', type: 'anomaly_detection', category: 'Analysis', icon: 'AlertTriangle', color: '#8b5cf6', config: { columns: 'income', method: 'iqr', threshold: 1.5 }, status: 'idle' as const } },
      { id: 'demo-cluster', type: 'custom' as const, position: { x: 650, y: 280 }, data: { label: 'K-Means', type: 'clustering', category: 'Analysis', icon: 'Target', color: '#8b5cf6', config: { features: 'age,income', k: 3, maxIterations: 50 }, status: 'idle' as const } },
      { id: 'demo-chart', type: 'custom' as const, position: { x: 950, y: 80 }, data: { label: 'Results Chart', type: 'chart', category: 'Output', icon: 'BarChart', color: '#ec4899', config: { chartType: 'bar', title: 'Analytics Results' }, status: 'idle' as const } },
      { id: 'demo-export', type: 'custom' as const, position: { x: 950, y: 280 }, data: { label: 'Export CSV', type: 'export', category: 'Output', icon: 'Download', color: '#ec4899', config: { format: 'csv', filename: 'analysis_results' }, status: 'idle' as const } },
    ];

    const demoEdges = [
      { id: 'd1', source: 'demo-csv', target: 'demo-dq' },
      { id: 'd2', source: 'demo-csv', target: 'demo-stats' },
      { id: 'd3', source: 'demo-csv', target: 'demo-corr' },
      { id: 'd4', source: 'demo-dq', target: 'demo-anomaly' },
      { id: 'd5', source: 'demo-csv', target: 'demo-cluster' },
      { id: 'd6', source: 'demo-anomaly', target: 'demo-chart' },
      { id: 'd7', source: 'demo-cluster', target: 'demo-export' },
    ];

    useStore.getState().setNodes(demoNodes);
    useStore.getState().setEdges(demoEdges);
    clearLogs();
    addLog('Demo workflow loaded: CSV -> Quality -> Stats + Correlation + Anomaly + Cluster -> Chart + Export');
    toast('Demo workflow loaded! Click Run to execute.', 'success');

    kos(demoNodes, demoEdges, { demo: true });
  };

  const handleSave = () => {
    if (nodes.length === 0) {
      addLog('No workflow to save');
      return;
    }
    addSavedModel({
      name: `Workflow ${new Date().toLocaleTimeString()}`,
      description: 'Auto-saved workflow',
      category: 'Custom',
      nodes,
      edges,
      tags: ['autosave']
    });
    addLog('Workflow saved to models library');
  };

  // Bant, akışta gerçekten sentetik veri üretecek kaynak varsa görünür (eskiden
  // hep true olan bir bayrağa bağlıydı: gerçek veriyle de "Demo Mode" diyordu).
  const demoKaynaklar = nodes.filter((n) => demoKaynagiMi(n.data.type, n.data.config));

  const toggleValidation = () => {
    if (!showValidation) {
      const errors = validateWorkflow(nodes, edges);
      setValidationErrors(errors.map((e) => ({ nodeLabel: e.nodeLabel, message: e.message, severity: e.severity })));
    }
    setShowValidation(!showValidation);
  };

  return (
    <div className="relative">
      <div className="flex items-center gap-1 px-3 py-2 bg-slate-900 border-b border-slate-800">
        {/* Run button */}
        <button
          onClick={isRunning ? handleStop : handleRun}
          disabled={!isRunning && nodes.length === 0}
          title={isRunning ? t('stopTitle') : undefined}
          className={`
            flex items-center gap-2 px-4 py-1.5 rounded-lg text-xs font-semibold transition-all
            ${isRunning
              ? 'bg-red-700 hover:bg-red-600 text-white shadow-lg shadow-red-700/20'
              : nodes.length === 0
                ? 'bg-slate-800 text-slate-500 cursor-not-allowed'
                : 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-lg shadow-emerald-600/20'
            }
          `}
        >
          {isRunning ? (
            <>
              <Square size={13} className="fill-current" />
              {t('stop')}
            </>
          ) : (
            <>
              <Play size={14} />
              {t('run')}
            </>
          )}
        </button>

        {/* Demo Button */}
        <button
          onClick={handleDemo}
          disabled={isRunning}
          title={t('demoTitle')}
          className="btn-demo flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-white font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed shadow-lg shadow-purple-500/20"
        >
          <Sparkles size={13} />
          {t('demo')}
        </button>

        {/* Hedeften Akış (düz metin → otomatik iş akışı) */}
        <div className="relative">
          <button
            onClick={() => setGoalOpen((v) => !v)}
            disabled={isRunning}
            title="Düz metin amaç yazın, otomatik iş akışı oluşsun"
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-white font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed bg-indigo-600 hover:bg-indigo-500 shadow-lg shadow-indigo-500/20"
          >
            <Wand2 size={13} />
            Hedeften Akış
          </button>
          {goalOpen && (
            <div className="absolute left-0 top-full mt-2 z-50 w-80 p-3 rounded-lg bg-slate-900 border border-slate-700 shadow-xl">
              <label className="block text-[11px] text-slate-400 mb-1.5">
                Ne yapmak istiyorsunuz? (ör. "köylere göre olay yoğunluğunu haritala")
              </label>
              <textarea
                value={goalText}
                onChange={(e) => setGoalText(e.target.value)}
                onKeyDown={(e) => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) handleCompose(); }}
                rows={3}
                autoFocus
                placeholder="Amacınızı düz metin yazın..."
                className="w-full px-2 py-1.5 rounded bg-slate-800 border border-slate-700 text-xs text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 resize-none"
              />
              <div className="flex items-center justify-between mt-2">
                <span className="text-[10px] text-slate-500">Ctrl+Enter</span>
                <button
                  onClick={handleCompose}
                  className="flex items-center gap-1 px-3 py-1 rounded text-xs text-white font-semibold bg-indigo-600 hover:bg-indigo-500 transition-all"
                >
                  <Wand2 size={12} />
                  Oluştur
                </button>
              </div>
            </div>
          )}
        </div>

        {/* Rehberli Mod (düz metin görev → otomatik analiz, node tuvali gizli) */}
        <button
          onClick={() => useStore.getState().setGuidedOpen(true)}
          disabled={isRunning}
          title="Rehberli Mod: düz metin görev yazın, analiz otomatik yürüsün"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-white font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed bg-teal-600 hover:bg-teal-500 shadow-lg shadow-teal-500/20"
        >
          <Compass size={13} />
          Rehberli Mod
        </button>

        {/* Akademik Mod (ön-kayıtlı, denetlenebilir makale taslağı) */}
        <button
          onClick={() => useStore.getState().setAcademicOpen(true)}
          disabled={isRunning}
          title="Akademik Mod: ön-kayıtlı çalışmadan denetlenebilir makale taslağına"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-white font-semibold transition-all disabled:opacity-50 disabled:cursor-not-allowed bg-violet-600 hover:bg-violet-500 shadow-lg shadow-violet-500/20"
        >
          <GraduationCap size={13} />
          Akademik Mod
        </button>

        <div className="w-px h-6 bg-slate-800 mx-1" />

        {/* Undo/Redo */}
        <button
          onClick={undo}
          disabled={!canUndo || isRunning}
          title="Undo (Ctrl+Z)"
          className="flex items-center gap-1.5 px-2 py-1.5 rounded-lg text-xs text-slate-400 hover:text-white hover:bg-slate-800 transition-all disabled:opacity-30 disabled:cursor-not-allowed"
        >
          <Undo2 size={13} />
        </button>
        <button
          onClick={redo}
          disabled={!canRedo || isRunning}
          title="Redo (Ctrl+Shift+Z)"
          className="flex items-center gap-1.5 px-2 py-1.5 rounded-lg text-xs text-slate-400 hover:text-white hover:bg-slate-800 transition-all disabled:opacity-30 disabled:cursor-not-allowed"
        >
          <Redo2 size={13} />
        </button>

        <div className="w-px h-6 bg-slate-800 mx-1" />

        {/* Clear */}
        <button
          onClick={handleClear}
          disabled={isRunning}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-slate-400 hover:text-white hover:bg-slate-800 transition-all disabled:opacity-50"
        >
          <Trash2 size={13} />
          {t('clear')}
        </button>

        {/* Save */}
        <button
          onClick={handleSave}
          disabled={isRunning}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-slate-400 hover:text-white hover:bg-slate-800 transition-all disabled:opacity-50"
        >
          <Save size={13} />
          {t('save')}
        </button>

        {/* P1-1: Persist to browser */}
        <button
          onClick={handleSaveToDisk}
          disabled={isRunning}
          title={t('diskTitle')}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-slate-400 hover:text-white hover:bg-slate-800 transition-all disabled:opacity-50"
        >
          <HardDrive size={13} />
          {t('disk')}
        </button>
        <button
          onClick={handleLoadFromDisk}
          disabled={isRunning}
          title={t('loadTitle')}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-slate-400 hover:text-white hover:bg-slate-800 transition-all disabled:opacity-50"
        >
          <FolderOpen size={13} />
          {t('load')}
        </button>

        <div className="w-px h-6 bg-slate-800 mx-1" />

        {/* Models */}
        <button
          onClick={() => useStore.getState().setActivePanel('models')}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-slate-400 hover:text-white hover:bg-slate-800 transition-all"
        >
          <FolderOpen size={13} />
          {t('models')}
        </button>

        {/* Validate */}
        <button
          onClick={toggleValidation}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs transition-all ${
            showValidation
              ? 'text-amber-400 bg-amber-400/10'
              : 'text-slate-400 hover:text-white hover:bg-slate-800'
          }`}
        >
          <AlertCircle size={13} />
          {t('validate')}
        </button>

        {/* Toggle Data Preview */}
        <button
          onClick={() => setShowDataPreview(!showDataPreview)}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs transition-all ${
            showDataPreview
              ? 'text-blue-400 bg-blue-400/10'
              : 'text-slate-400 hover:text-white hover:bg-slate-800'
          }`}
        >
          <Table2 size={13} />
          {t('data')}
        </button>

        {/* Toggle Results */}
        <button
          onClick={() => setShowResults(!showResults)}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs transition-all ${
            showResults
              ? 'text-purple-400 bg-purple-400/10'
              : 'text-slate-400 hover:text-white hover:bg-slate-800'
          }`}
        >
          <Activity size={13} />
          {t('results')}
        </button>

        {/* Keyboard Help */}
        <button
          onClick={() => setShowKeyboardHelp(true)}
          title="Keyboard shortcuts"
          className="flex items-center gap-1.5 px-2 py-1.5 rounded-lg text-xs text-slate-400 hover:text-white hover:bg-slate-800 transition-all"
        >
          <Keyboard size={13} />
        </button>

        {/* Demo Mode Banner */}
        {demoKaynaklar.length > 0 && (
          <div
            className="flex items-center gap-1.5 px-2.5 py-1 rounded-md bg-amber-500/10 border border-amber-500/20 text-amber-400 text-[10px] font-medium"
            title={`${t('demoTitle2')}: ${demoKaynaklar.map((n) => n.data.label).join(', ')}`}
          >
            <FlaskConical size={12} />
            {t('demoMode')} ({demoKaynaklar.length})
          </div>
        )}

        {/* P0: Cloud sync — server-backed workflow persistence */}
        <div className="ml-auto flex items-center gap-1">
          <CloudSync />
        </div>
        <div className="w-px h-6 bg-slate-800 mx-1" />

        {/* Stats */}
        <div className="flex items-center gap-3 text-[10px] text-slate-500">
          <span className="flex items-center gap-1">
            <Box size={12} />
            {nodes.length} {t('nodes')}
          </span>
          <span className="flex items-center gap-1">
            <Link2 size={12} />
            {edges.length} {t('edges')}
          </span>
          {isRunning && (
            <span className="flex items-center gap-1 text-blue-400 animate-pulse">
              <Loader2 size={12} className="animate-spin" />
              {t('executing')}
            </span>
          )}
        </div>
      </div>

      {/* Validation panel */}
      {showValidation && validationErrors.length > 0 && (
        <div className="absolute top-full left-0 right-0 bg-slate-900 border-b border-slate-800 z-50 max-h-[200px] overflow-y-auto">
          {validationErrors.map((err, i) => (
            <div
              key={i}
              className={`flex items-center gap-2 px-4 py-1.5 text-[10px] ${
                err.severity === 'error' ? 'text-red-400 bg-red-400/5' : 'text-amber-400 bg-amber-400/5'
              }`}
            >
              <AlertCircle size={10} />
              <span className="font-medium">{err.severity === 'error' ? 'Error' : 'Warning'}:</span>
              <span>{err.message}</span>
            </div>
          ))}
        </div>
      )}
      {showValidation && validationErrors.length === 0 && (
        <div className="absolute top-full left-0 right-0 bg-slate-900 border-b border-slate-800 z-50">
          <div className="flex items-center gap-2 px-4 py-1.5 text-[10px] text-emerald-400 bg-emerald-400/5">
            <CheckCircle2 size={10} />
            <span>Workflow is valid. Ready to execute.</span>
          </div>
        </div>
      )}
      {/* Toast Notification */}
      {showToast && (
        <div className={`fixed bottom-4 right-4 z-50 toast-enter`}>
          <div className={`flex items-center gap-2 px-4 py-2.5 rounded-lg text-xs font-medium shadow-xl border ${
            showToast.type === 'success' ? 'bg-emerald-900/90 text-emerald-300 border-emerald-700/50' :
            showToast.type === 'error' ? 'bg-red-900/90 text-red-300 border-red-700/50' :
            'bg-slate-800/90 text-slate-300 border-slate-700/50'
          } backdrop-blur-sm`}>
            {showToast.type === 'success' && <CheckCircle2 size={14} />}
            {showToast.type === 'error' && <AlertCircle size={14} />}
            {showToast.type === 'info' && <FlaskConical size={14} />}
            {showToast.message}
          </div>
        </div>
      )}

      {/* Keyboard Help Overlay */}
      {showKeyboardHelp && (
        <div className="fixed inset-0 z-50 flex items-center justify-center overlay-backdrop" onClick={() => setShowKeyboardHelp(false)}>
          <div className="overlay-content bg-slate-900/95 border border-slate-700 rounded-xl shadow-2xl p-6 max-w-sm w-full mx-4 backdrop-blur-sm" onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between mb-4">
              <h3 className="text-sm font-semibold text-white">Keyboard Shortcuts</h3>
              <button onClick={() => setShowKeyboardHelp(false)} className="text-slate-500 hover:text-white">
                <Trash2 size={14} />
              </button>
            </div>
            <div className="space-y-2">
              {[
                { keys: ['Ctrl', 'Z'], action: 'Undo' },
                { keys: ['Ctrl', 'Shift', 'Z'], action: 'Redo' },
                { keys: ['Delete'], action: 'Remove selected node' },
                { keys: ['D'], action: 'Toggle data preview' },
                { keys: ['Esc'], action: 'Close panels / deselect' },
                { keys: ['Ctrl', 'R'], action: 'Run workflow' },
                { keys: ['Ctrl', 'S'], action: 'Save workflow' },
                { keys: ['?'], action: 'Show this help' },
              ].map((shortcut) => (
                <div key={shortcut.action} className="flex items-center justify-between text-xs">
                  <span className="text-slate-400">{shortcut.action}</span>
                  <div className="flex gap-1">
                    {shortcut.keys.map((k) => (
                      <kbd key={k} className="kbd">{k}</kbd>
                    ))}
                  </div>
                </div>
              ))}
            </div>
            <p className="mt-4 text-[10px] text-slate-600 text-center">Press ? anywhere to open this dialog</p>
          </div>
        </div>
      )}
    </div>
  );
}
