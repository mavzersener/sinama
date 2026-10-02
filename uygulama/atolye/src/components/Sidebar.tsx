import { useState } from 'react';
import { useStore } from '../store/useStore';
import { getNodeCategories, getNodesByCategory, type NodeDefinition } from '../nodes/nodeDefinitions';
import type { SavedModel } from '../store/useStore';
import { useAuth } from '../hooks/useAuth';
import { useCatalog } from '../hooks/useCatalog';
import { useT, LANGUAGES } from '../i18n';
import { nodeLabel, nodeDesc, categoryLabel } from '../i18nNodes';
import { pythonBetigiUret, pythonBetiginiIndir } from '../lib/pythonExport';
import {
  Database, Cpu, Brain, Monitor, Workflow, Library, Settings,
  ChevronRight, Search, Plus, Inbox, MoreVertical, Play,
  PanelLeftClose, PanelLeftOpen, Zap, Tag, Download, Shield,
  Award, Loader2, XCircle
} from 'lucide-react';

const categoryIcons: Record<string, React.ComponentType<{ size?: number; className?: string }>> = {
  'Data Input': Database,
  'Processing': Cpu,
  'Analysis': Brain,
  'Output': Monitor,
  'Kolluk Data': Shield,
  'Kolluk Analysis': Brain
};

const panelIcons = {
  nodes: Workflow,
  models: Library,
  catalog: Award,
  settings: Settings
};

function NodeCard({ def }: { def: NodeDefinition }) {
  const language = useStore((s) => s.language);
  const onDragStart = (e: React.DragEvent) => {
    e.dataTransfer.setData('application/reactflow', JSON.stringify({
      type: def.type,
      label: def.label,
      category: def.category,
      icon: def.icon,
      color: def.color
    }));
    e.dataTransfer.effectAllowed = 'move';
  };

  const IconComp = categoryIcons[def.category] || Database;

  return (
    <div
      draggable
      onDragStart={onDragStart}
      className="flex items-center gap-2 p-2 rounded-lg bg-slate-800/60 border border-slate-700/50 cursor-grab active:cursor-grabbing hover:bg-slate-700/60 hover:border-slate-600 transition-all group"
    >
      <div className="flex items-center justify-center w-8 h-8 rounded-md shrink-0" style={{ backgroundColor: def.color + '25' }}>
        <div style={{ color: def.color }}>
          <IconComp size={16} />
        </div>
      </div>
      <div className="flex-1 min-w-0">
        <div className="text-xs font-medium text-slate-300 group-hover:text-white truncate">{nodeLabel(language, def.type, def.label)}</div>
        <div className="text-[10px] text-slate-500 truncate">{nodeDesc(language, def.type, def.description)}</div>
      </div>
    </div>
  );
}

function NodesPanel() {
  const language = useStore((s) => s.language);
  const categories = getNodeCategories();
  const [expanded, setExpanded] = useState<Record<string, boolean>>({
    'Data Input': true,
    'Processing': true,
    'Analysis': true,
    'Output': true,
    'Kolluk Data': true,
    'Kolluk Analysis': true
  });
  const [searchQuery, setSearchQuery] = useState('');

  const filteredCategories = categories.map((cat) => {
    const catNodes = getNodesByCategory(cat);
    const filtered = searchQuery
      ? catNodes.filter((n) =>
          n.label.toLowerCase().includes(searchQuery.toLowerCase()) ||
          n.description.toLowerCase().includes(searchQuery.toLowerCase()) ||
          n.type.toLowerCase().includes(searchQuery.toLowerCase())
        )
      : catNodes;
    return { cat, nodes: filtered };
  }).filter((c) => c.nodes.length > 0);

  return (
    <div className="flex-1 overflow-y-auto p-3 space-y-3">
      {/* Search */}
      <div className="relative">
        <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search nodes..."
          className="sidebar-search w-full pl-8 pr-3 py-2 text-xs bg-slate-800/60 border border-slate-700/60 rounded-lg text-slate-300 placeholder-slate-500 transition-all"
        />
        {searchQuery && (
          <button
            onClick={() => setSearchQuery('')}
            className="absolute right-2.5 top-1/2 -translate-y-1/2 text-[10px] text-slate-500 hover:text-slate-300"
          >
            Clear
          </button>
        )}
      </div>

      {filteredCategories.map(({ cat, nodes: catNodes }) => {
        const isExpanded = expanded[cat];
        const IconComp = categoryIcons[cat] || Database;

        return (
          <div key={cat}>
            <button
              onClick={() => setExpanded((prev) => ({ ...prev, [cat]: !prev[cat] }))}
              className="flex items-center gap-2 w-full px-1 py-1.5 text-xs font-semibold text-slate-400 hover:text-slate-200 transition-colors"
            >
              <IconComp size={14} />
              <span>{categoryLabel(language, cat)}</span>
              <span className="ml-auto text-[10px] bg-slate-700 text-slate-400 px-1.5 py-0.5 rounded-full">{catNodes.length}</span>
              <span className={`transform transition-transform ${isExpanded ? 'rotate-90' : ''}`}>
                <ChevronRight size={12} />
              </span>
            </button>
            {isExpanded && (
              <div className="mt-1.5 space-y-1.5 pl-1">
                {catNodes.map((def) => (
                  <NodeCard key={def.type} def={def} />
                ))}
              </div>
            )}
          </div>
        );
      })}

      {filteredCategories.length === 0 && (
        <div className="text-center py-6 text-xs text-slate-500">
          <Inbox size={24} className="mx-auto mb-2 opacity-50" />
          No nodes match "{searchQuery}"
        </div>
      )}
    </div>
  );
}

function ModelsPanel() {
  const { savedModels, loadModel, deleteModel, nodes, edges, addSavedModel } = useStore();
  const [showNewModel, setShowNewModel] = useState(false);
  const [newModelName, setNewModelName] = useState('');
  const [newModelDesc, setNewModelDesc] = useState('');
  const [newModelCategory, setNewModelCategory] = useState('');
  const [searchQuery, setSearchQuery] = useState('');

  const filteredModels = savedModels.filter((m) =>
    m.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
    m.category.toLowerCase().includes(searchQuery.toLowerCase()) ||
    m.tags.some((t) => t.toLowerCase().includes(searchQuery.toLowerCase()))
  );

  const handleSaveCurrent = () => {
    if (!newModelName.trim()) return;
    addSavedModel({
      name: newModelName,
      description: newModelDesc || 'Custom model',
      category: newModelCategory || 'Custom',
      nodes,
      edges,
      tags: []
    });
    setShowNewModel(false);
    setNewModelName('');
    setNewModelDesc('');
    setNewModelCategory('');
  };

  return (
    <div className="flex-1 overflow-y-auto p-3 space-y-3">
      {/* Search */}
      <div className="relative">
        <Search size={14} className="absolute left-2.5 top-1/2 -translate-y-1/2 text-slate-500" />
        <input
          type="text"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search models..."
          className="w-full pl-8 pr-3 py-2 text-xs bg-slate-800/60 border border-slate-700 rounded-lg text-slate-300 placeholder-slate-500 focus:outline-none focus:border-blue-500"
        />
      </div>

      {/* Save current model */}
      {nodes.length > 0 && !showNewModel && (
        <button
          onClick={() => setShowNewModel(true)}
          className="flex items-center gap-2 w-full p-2 rounded-lg bg-blue-600/20 border border-blue-600/40 text-blue-400 hover:bg-blue-600/30 transition-all text-xs font-medium"
        >
          <Plus size={14} />
          Save Current Workflow
        </button>
      )}

      {showNewModel && (
        <div className="p-3 rounded-lg bg-slate-800/80 border border-slate-700 space-y-2">
          <input
            type="text"
            value={newModelName}
            onChange={(e) => setNewModelName(e.target.value)}
            placeholder="Model name..."
            className="w-full px-2.5 py-1.5 text-xs bg-slate-700 border border-slate-600 rounded text-slate-300 placeholder-slate-500 focus:outline-none focus:border-blue-500"
          />
          <input
            type="text"
            value={newModelDesc}
            onChange={(e) => setNewModelDesc(e.target.value)}
            placeholder="Description..."
            className="w-full px-2.5 py-1.5 text-xs bg-slate-700 border border-slate-600 rounded text-slate-300 placeholder-slate-500 focus:outline-none focus:border-blue-500"
          />
          <input
            type="text"
            value={newModelCategory}
            onChange={(e) => setNewModelCategory(e.target.value)}
            placeholder="Category..."
            className="w-full px-2.5 py-1.5 text-xs bg-slate-700 border border-slate-600 rounded text-slate-300 placeholder-slate-500 focus:outline-none focus:border-blue-500"
          />
          <div className="flex gap-2">
            <button onClick={handleSaveCurrent} className="flex-1 py-1.5 text-xs bg-blue-600 hover:bg-blue-500 rounded text-white font-medium transition-colors">
              Save
            </button>
            <button onClick={() => setShowNewModel(false)} className="flex-1 py-1.5 text-xs bg-slate-700 hover:bg-slate-600 rounded text-slate-300 font-medium transition-colors">
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Model list */}
      <div className="space-y-2">
        {filteredModels.map((model) => (
          <ModelCard key={model.id} model={model} onLoad={loadModel} onDelete={deleteModel} />
        ))}
        {filteredModels.length === 0 && (
          <div className="text-center py-6 text-xs text-slate-500">
            <Inbox size={24} className="mx-auto mb-2 opacity-50" />
            No models found
          </div>
        )}
      </div>
    </div>
  );
}

function ModelCard({ model, onLoad, onDelete }: { model: SavedModel; onLoad: (m: SavedModel) => void; onDelete: (id: string) => void }) {
  const [showDelete, setShowDelete] = useState(false);

  return (
    <div className="p-3 rounded-lg bg-slate-800/60 border border-slate-700/50 hover:border-slate-600 transition-all">
      <div className="flex items-start justify-between gap-2">
        <div className="flex-1 min-w-0 cursor-pointer" onClick={() => onLoad(model)}>
          <div className="text-xs font-semibold text-slate-200 truncate">{model.name}</div>
          <div className="text-[10px] text-slate-500 mt-0.5 line-clamp-2">{model.description}</div>
          <div className="flex items-center gap-2 mt-1.5">
            <span className="text-[10px] bg-slate-700 text-slate-400 px-1.5 py-0.5 rounded">{model.category}</span>
            <span className="text-[10px] text-slate-500 flex items-center gap-1">
              <Play size={10} /> {model.runs} runs
            </span>
          </div>
          {model.tags.length > 0 && (
            <div className="flex flex-wrap gap-1 mt-1.5">
              {model.tags.map((tag) => (
                <span key={tag} className="text-[9px] flex items-center gap-0.5 bg-slate-700/50 text-slate-500 px-1 py-0.5 rounded">
                  <Tag size={8} /> {tag}
                </span>
              ))}
            </div>
          )}
        </div>
        <button
          onClick={() => setShowDelete(!showDelete)}
          className="text-slate-500 hover:text-red-400 transition-colors p-0.5"
        >
          <MoreVertical size={14} />
        </button>
      </div>
      {showDelete && (
        <button
          onClick={() => onDelete(model.id)}
          className="mt-2 w-full py-1 text-[10px] bg-red-600/20 text-red-400 hover:bg-red-600/30 rounded border border-red-600/30 transition-all"
        >
          Delete Model
        </button>
      )}
    </div>
  );
}

/**
 * P4 Faz A: admin-curated best-practice catalog. Everyone can browse + clone
 * an entry as a template; admins additionally see a "Retract" action.
 */
function CatalogPanel() {
  const { isAuthenticated, user } = useAuth();
  const catalog = useCatalog(isAuthenticated);
  const [cloningId, setCloningId] = useState<number | null>(null);
  const isAdmin = user?.role === 'admin';

  if (!isAuthenticated) {
    return (
      <div className="flex-1 flex items-center justify-center p-6 text-center">
        <p className="text-xs text-slate-500">Kataloğu görmek için giriş yapmalısın.</p>
      </div>
    );
  }

  const handleUse = async (entry: { id: number; nodes: unknown; edges: unknown }) => {
    setCloningId(entry.id);
    try {
      await catalog.useAsTemplate(entry);
    } finally {
      setCloningId(null);
    }
  };

  return (
    <div className="flex-1 overflow-y-auto p-3 space-y-2">
      <p className="text-[10px] text-slate-500">
        Yönetici onaylı, kurumsal olarak paylaşılan iş akışları. "Kullan" ile kendi
        çalışma alanına kopyalanır.
      </p>

      {catalog.isLoading ? (
        <div className="flex items-center gap-2 py-6 justify-center text-xs text-slate-500">
          <Loader2 size={14} className="animate-spin" /> Yükleniyor…
        </div>
      ) : catalog.isError ? (
        <div className="text-center py-6 text-xs text-red-400">Katalog yüklenemedi.</div>
      ) : catalog.entries.length === 0 ? (
        <div className="text-center py-6 text-xs text-slate-500">
          <Inbox size={24} className="mx-auto mb-2 opacity-50" />
          Henüz onaylı bir örnek yok.
        </div>
      ) : (
        catalog.entries.map((entry) => (
          <div key={entry.id} className="p-3 rounded-lg bg-slate-800/60 border border-slate-700/50">
            <div className="flex items-start gap-2">
              <Award size={14} className="text-amber-400 mt-0.5 shrink-0" />
              <div className="min-w-0 flex-1">
                <div className="text-xs font-semibold text-slate-200 truncate">{entry.name}</div>
                {entry.curatorNote && (
                  <div className="text-[10px] text-slate-500 mt-0.5 line-clamp-2">{entry.curatorNote}</div>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2 mt-2">
              <button
                onClick={() => void handleUse(entry as unknown as { id: number; nodes: unknown; edges: unknown })}
                disabled={cloningId === entry.id}
                className="flex-1 flex items-center justify-center gap-1 py-1.5 text-[10px] bg-blue-600/20 border border-blue-600/40 text-blue-400 hover:bg-blue-600/30 rounded transition-all disabled:opacity-50"
              >
                {cloningId === entry.id ? <Loader2 size={11} className="animate-spin" /> : <Download size={11} />}
                Kullan
              </button>
              {isAdmin && (
                <button
                  onClick={() => void catalog.retract(entry.id)}
                  title="Kataloğdan kaldır"
                  className="p-1.5 text-slate-500 hover:text-red-400 rounded transition-colors"
                >
                  <XCircle size={13} />
                </button>
              )}
            </div>
          </div>
        ))
      )}
    </div>
  );
}

function SettingsPanel() {
  const t = useT();
  const language = useStore((s) => s.language);
  const setLanguage = useStore((s) => s.setLanguage);
  const nodes = useStore((s) => s.nodes);
  const edges = useStore((s) => s.edges);
  // Dışa aktarım sonrası geri bildirim: kaç düğüm yazıldı, hangi uyarılar çıktı.
  const [pyDurum, setPyDurum] = useState<{ dosya: string; uyarilar: string[] } | null>(null);

  const pythonDisaAktar = () => {
    const { kod, uyarilar } = pythonBetigiUret(nodes, edges);
    if (!kod) {
      setPyDurum({ dosya: '', uyarilar });
      return;
    }
    const dosya = `dataflow_akis_${new Date().toISOString().slice(0, 10)}.py`;
    pythonBetiginiIndir(kod, dosya);
    setPyDurum({ dosya, uyarilar });
  };

  return (
    <div className="flex-1 overflow-y-auto p-3 space-y-4">
      {/* Language selector */}
      <div>
        <h4 className="text-xs font-semibold text-slate-400 mb-2">{t('settings_language')}</h4>
        <div className="flex gap-1.5">
          {LANGUAGES.map((l) => (
            <button
              key={l.code}
              onClick={() => setLanguage(l.code)}
              className={`flex-1 py-1.5 rounded-lg text-xs font-medium transition-all border ${
                language === l.code
                  ? 'bg-blue-500/15 border-blue-500/50 text-blue-400'
                  : 'bg-slate-800 border-slate-700 text-slate-400 hover:text-white hover:bg-slate-700'
              }`}
            >
              {l.label}
            </button>
          ))}
        </div>
      </div>

      <div className="border-t border-slate-700 pt-3">
        <h4 className="text-xs font-semibold text-slate-400 mb-2">{t('settings_execution')}</h4>
        <div className="space-y-2">
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-500">{t('settings_parallel')}</span>
            <button className="w-9 h-5 bg-blue-600 rounded-full relative transition-colors">
              <div className="w-4 h-4 bg-white rounded-full absolute top-0.5 right-0.5 transition-transform" />
            </button>
          </div>
          <div className="flex items-center justify-between">
            <span className="text-xs text-slate-500">{t('settings_cache')}</span>
            <button className="w-9 h-5 bg-blue-600 rounded-full relative transition-colors">
              <div className="w-4 h-4 bg-white rounded-full absolute top-0.5 right-0.5 transition-transform" />
            </button>
          </div>
        </div>
      </div>

      <div className="border-t border-slate-700 pt-3">
        <h4 className="text-xs font-semibold text-slate-400 mb-2">{t('settings_performance')}</h4>
        <div className="space-y-2">
          <div>
            <div className="flex justify-between text-[10px] text-slate-500 mb-1">
              <span>{t('settings_memory')}</span>
              <span>4 GB</span>
            </div>
            <div className="h-1.5 bg-slate-700 rounded-full overflow-hidden">
              <div className="h-full w-1/3 bg-blue-500 rounded-full" />
            </div>
          </div>
        </div>
      </div>

      <div className="border-t border-slate-700 pt-3">
        <h4 className="text-xs font-semibold text-slate-400 mb-2">{t('settings_export')}</h4>
        <button
          onClick={pythonDisaAktar}
          disabled={nodes.length === 0}
          className="flex items-center gap-2 w-full p-2 rounded-lg bg-slate-800 border border-slate-700 text-xs text-slate-300 hover:bg-slate-700 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <Download size={14} />
          {t('settings_exportPy')}
        </button>
        <p className="mt-1.5 text-[10px] text-slate-500">
          {nodes.length > 0
            ? t('settings_exportPyHint').replace('{n}', String(nodes.length))
            : t('settings_exportPyEmpty')}
        </p>
        {pyDurum && (
          <div className="mt-2 space-y-1">
            {pyDurum.dosya && (
              <div className="text-[10px] text-emerald-400 break-all">✓ {pyDurum.dosya}</div>
            )}
            {pyDurum.uyarilar.map((u, i) => (
              <div key={i} className="text-[10px] text-amber-400/90 leading-snug">⚠ {u}</div>
            ))}
          </div>
        )}
      </div>

      <div className="border-t border-slate-700 pt-3">
        <h4 className="text-xs font-semibold text-slate-400 mb-2">{t('settings_shortcuts')}</h4>
        <div className="space-y-1 text-[10px] text-slate-500">
          <div className="flex justify-between"><span>Ctrl+Z</span><span>Undo</span></div>
          <div className="flex justify-between"><span>Ctrl+Shift+Z</span><span>Redo</span></div>
          <div className="flex justify-between"><span>Delete</span><span>Remove node</span></div>
          <div className="flex justify-between"><span>D</span><span>Data preview</span></div>
          <div className="flex justify-between"><span>Esc</span><span>Close panels</span></div>
        </div>
      </div>
    </div>
  );
}

export default function Sidebar() {
  const { activePanel, setActivePanel, sidebarOpen, setSidebarOpen } = useStore();
  const t = useT();

  return (
    <>
      {/* Toggle button */}
      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className={`absolute top-3 z-20 p-1.5 rounded-lg bg-slate-800 border border-slate-700 text-slate-400 hover:text-white hover:bg-slate-700 transition-all ${sidebarOpen ? 'left-[280px]' : 'left-3'}`}
      >
        {sidebarOpen ? <PanelLeftClose size={16} /> : <PanelLeftOpen size={16} />}
      </button>

      {/* Sidebar */}
      <div
        className={`
          flex flex-col bg-slate-900 border-r border-slate-800 transition-all duration-300 ease-in-out z-10
          ${sidebarOpen ? 'w-[280px] opacity-100' : 'w-0 opacity-0 overflow-hidden'}
        `}
      >
        {/* Header */}
        <div className="flex items-center gap-2 px-4 py-3 border-b border-slate-800">
          <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-blue-500 to-cyan-400 flex items-center justify-center">
            <Zap size={18} className="text-white" />
          </div>
          <div>
            <div className="text-sm font-bold text-white">DataFlow</div>
            <div className="text-[10px] text-slate-500">Zero-Code Analytics</div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex border-b border-slate-800">
          {(['nodes', 'models', 'catalog', 'settings'] as const).map((panel) => {
            const IconComp = panelIcons[panel];
            return (
              <button
                key={panel}
                onClick={() => setActivePanel(panel)}
                className={`flex-1 flex items-center justify-center gap-1.5 py-2.5 text-[11px] font-medium transition-all
                  ${activePanel === panel
                    ? 'text-blue-400 border-b-2 border-blue-500 bg-blue-500/10'
                    : 'text-slate-500 hover:text-slate-300 hover:bg-slate-800/50'
                  }`}
              >
                <IconComp size={13} />
                {t('tab_' + panel)}
              </button>
            );
          })}
        </div>

        {activePanel === 'nodes' && <NodesPanel />}
        {activePanel === 'models' && <ModelsPanel />}
        {activePanel === 'catalog' && <CatalogPanel />}
        {activePanel === 'settings' && <SettingsPanel />}

        {/* Footer — sürüm package.json'dan gelir (vite.config.ts define) */}
        <div className="px-3 py-2 border-t border-slate-800 text-[10px] text-slate-600 text-center">
          v{__APP_VERSION__} - Kolluk Intelligence
        </div>
      </div>
    </>
  );
}
