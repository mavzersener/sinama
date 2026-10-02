import { create } from 'zustand';
import type { Node, Edge, Connection } from '@xyflow/react';
import { addEdge } from '@xyflow/react';
import type { ExecutionResult } from '../engine/executionEngine';
import { getPrebuiltModels } from '../engine/executionEngine';
import { kaliciDugumler, yuklenenAkis, sonuclariAktar } from '../lib/kalicilik';

export interface NodeData extends Record<string, unknown> {
  label: string;
  type: string;
  category: string;
  icon: string;
  color: string;
  config: Record<string, unknown>;
  status?: 'idle' | 'running' | 'completed' | 'error';
  result?: ExecutionResult;
}

export interface SavedModel {
  id: string;
  name: string;
  description: string;
  category: string;
  nodes: Node<NodeData>[];
  edges: Edge[];
  createdAt: string;
  updatedAt: string;
  runs: number;
  tags: string[];
}

interface HistoryState {
  nodes: Node<NodeData>[];
  edges: Edge[];
}

interface WorkflowState {
  nodes: Node<NodeData>[];
  edges: Edge[];
  selectedNode: string | null;
  // Buluttaki workflow kaydının DB id'si (CloudSync yönetir); koşu kalıcılaştırma
  // ve Anlam paneli bu id ile çalışır.
  cloudWorkflowId: number | null;
  setCloudWorkflowId: (id: number | null) => void;
  isRunning: boolean;
  showResults: boolean;
  executionResults: Map<string, ExecutionResult>;
  logs: string[];
  savedModels: SavedModel[];
  activePanel: 'nodes' | 'models' | 'catalog' | 'settings';
  sidebarOpen: boolean;
  showDataPreview: boolean;
  guidedOpen: boolean;
  academicOpen: boolean;
  // Rehberli Mod'dan Akademik Mod'a devredilen ön-kayıt bağlamı. Hipotez
  // veriye BAKILMADAN yazıldıysa doğrulayıcı çalışma mümkündür; oturum ve
  // kilit özeti iki denetim zincirini birbirine bağlar.
  academicDevir: { hipotez?: string; oturumId?: string; kilitHash?: string } | null;
  dataPreviewNodeId: string | null;
  history: HistoryState[];
  historyIndex: number;
  canUndo: boolean;
  canRedo: boolean;
  language: 'en' | 'tr';
  auditLog: AuditLogEntry[];

  setNodes: (nodes: Node<NodeData>[] | ((prev: Node<NodeData>[]) => Node<NodeData>[])) => void;
  setEdges: (edges: Edge[] | ((prev: Edge[]) => Edge[])) => void;
  onNodesChange: (changes: unknown) => void;
  onEdgesChange: (changes: unknown) => void;
  onConnect: (connection: Connection) => void;
  addNode: (node: Node<NodeData>) => void;
  deleteNode: (nodeId: string) => void;
  setSelectedNode: (id: string | null) => void;
  updateNodeConfig: (nodeId: string, config: Record<string, unknown>) => void;
  updateNodeStatus: (nodeId: string, status: NodeData['status']) => void;
  setNodeResult: (nodeId: string, result: ExecutionResult) => void;
  setIsRunning: (running: boolean) => void;
  setShowResults: (show: boolean) => void;
  setExecutionResults: (results: Map<string, ExecutionResult>) => void;
  addLog: (log: string) => void;
  clearLogs: () => void;
  setShowDataPreview: (show: boolean) => void;
  setGuidedOpen: (open: boolean) => void;
  setAcademicOpen: (open: boolean) => void;
  setAcademicDevir: (devir: { hipotez?: string; oturumId?: string; kilitHash?: string } | null) => void;
  setDataPreviewNodeId: (nodeId: string | null) => void;
  undo: () => void;
  redo: () => void;
  pushHistory: () => void;
  addSavedModel: (model: Omit<SavedModel, 'id' | 'createdAt' | 'updatedAt' | 'runs'>) => void;
  loadModel: (model: SavedModel) => void;
  deleteModel: (id: string) => void;
  setActivePanel: (panel: 'nodes' | 'models' | 'catalog' | 'settings') => void;
  setSidebarOpen: (open: boolean) => void;
  setLanguage: (lang: 'en' | 'tr') => void;

  // P1-1: Persistence
  saveToLocalStorage: () => boolean;
  loadFromLocalStorage: () => boolean;

  // P1-2: Audit logging
  addAuditLog: (entry: AuditLogEntry) => void;
  loadAuditLog: () => void;
}

const MAX_HISTORY = 50;
const prebuilt = getPrebuiltModels();
const DEPO_ANAHTARI = 'dataflow_workflows';

/**
 * Kullanıcının kaydettiği modeller + hazır modeller. Eskiden modeller
 * localStorage'a YAZILIYOR ama hiç OKUNMUYORDU: kitaplığa kaydedilen iş
 * akışları sayfa yenilenince kayboluyordu.
 */
function modelleriBirlestir(kayitli: unknown): SavedModel[] {
  const hazirKimlik = new Set(prebuilt.map((m) => m.id));
  const kullanici: SavedModel[] = [];
  for (const m of Array.isArray(kayitli) ? kayitli : []) {
    if (!m || typeof m !== 'object' || typeof (m as SavedModel).id !== 'string' || hazirKimlik.has((m as SavedModel).id)) continue;
    const { nodes, edges } = yuklenenAkis((m as SavedModel).nodes, (m as SavedModel).edges);
    kullanici.push({ ...(m as SavedModel), nodes, edges });
  }
  return [...prebuilt, ...kullanici];
}

function kayitliModeller(): SavedModel[] {
  try {
    const ham = localStorage.getItem(DEPO_ANAHTARI);
    return modelleriBirlestir(ham ? JSON.parse(ham).savedModels : []);
  } catch {
    return prebuilt;
  }
}

export const useStore = create<WorkflowState>((set, get) => ({
  nodes: [],
  edges: [],
  selectedNode: null,
  cloudWorkflowId: null,
  setCloudWorkflowId: (id) => set({ cloudWorkflowId: id }),
  isRunning: false,
  showResults: false,
  executionResults: new Map(),
  logs: [],
  savedModels: kayitliModeller(),
  activePanel: 'nodes',
  sidebarOpen: true,
  showDataPreview: false,
  guidedOpen: false,
  academicOpen: false,
  academicDevir: null,
  dataPreviewNodeId: null,
  history: [{ nodes: [], edges: [] }],
  historyIndex: 0,
  canUndo: false,
  canRedo: false,
  language: ((): 'en' | 'tr' => {
    try {
      const saved = localStorage.getItem('dataflow_lang');
      return saved === 'tr' ? 'tr' : 'en';
    } catch {
      return 'en';
    }
  })(),
  auditLog: [],

  setNodes: (nodes) => {
    const newNodes = typeof nodes === 'function' ? nodes(get().nodes) : nodes;
    set({ nodes: newNodes });
  },

  setEdges: (edges) => {
    const newEdges = typeof edges === 'function' ? edges(get().edges) : edges;
    set({ edges: newEdges });
  },

  onNodesChange: (changes) => {
    const { nodes } = get();
    const changesArray = changes as Array<{ id: string; type: string; [key: string]: unknown }>;
    let newNodes = [...nodes];

    for (const change of changesArray) {
      switch (change.type) {
        case 'position': {
          const idx = newNodes.findIndex((n) => n.id === change.id);
          if (idx !== -1) {
            newNodes[idx] = { ...newNodes[idx], position: change.position as { x: number; y: number } };
          }
          break;
        }
        case 'remove': {
          newNodes = newNodes.filter((n) => n.id !== change.id);
          break;
        }
        case 'select': {
          const idx = newNodes.findIndex((n) => n.id === change.id);
          if (idx !== -1) {
            newNodes[idx] = { ...newNodes[idx], selected: change.selected as boolean };
          }
          break;
        }
      }
    }
    set({ nodes: newNodes });
  },

  onEdgesChange: (changes) => {
    const { edges } = get();
    const changesArray = changes as Array<{ id: string; type: string }>;
    let newEdges = [...edges];
    for (const change of changesArray) {
      if (change.type === 'remove') newEdges = newEdges.filter((e) => e.id !== change.id);
    }
    set({ edges: newEdges });
  },

  onConnect: (connection) => {
    set((state) => ({ edges: addEdge(connection, state.edges) }));
  },

  addNode: (node) => {
    set((state) => {
      const newNodes = [...state.nodes, node];
      return { nodes: newNodes, selectedNode: node.id };
    });
    get().pushHistory();
  },

  deleteNode: (nodeId) => {
    set((state) => ({
      nodes: state.nodes.filter((n) => n.id !== nodeId),
      edges: state.edges.filter((e) => e.source !== nodeId && e.target !== nodeId),
      selectedNode: state.selectedNode === nodeId ? null : state.selectedNode
    }));
    get().pushHistory();
  },

  setSelectedNode: (id) => set({ selectedNode: id }),

  // FIXED: Config changes now push to history
  updateNodeConfig: (nodeId, config) => {
    set((state) => ({
      nodes: state.nodes.map((node) =>
        node.id === nodeId
          ? { ...node, data: { ...node.data, config: { ...node.data.config, ...config } } }
          : node
      )
    }));
    get().pushHistory();
  },

  updateNodeStatus: (nodeId, status) => set((state) => ({
    nodes: state.nodes.map((node) =>
      node.id === nodeId ? { ...node, data: { ...node.data, status } } : node
    )
  })),

  setNodeResult: (nodeId, result) => set((state) => ({
    nodes: state.nodes.map((node) =>
      node.id === nodeId ? { ...node, data: { ...node.data, result } } : node
    ),
    executionResults: new Map(state.executionResults).set(nodeId, result)
  })),

  setIsRunning: (running) => set({ isRunning: running }),
  setShowResults: (show) => set({ showResults: show }),
  setExecutionResults: (results) => set({ executionResults: results }),

  addLog: (log) => set((state) => ({
    logs: [...state.logs, `[${new Date().toLocaleTimeString()}] ${log}`]
  })),

  clearLogs: () => set({ logs: [] }),

  setShowDataPreview: (show) => set({ showDataPreview: show }),
  setGuidedOpen: (open) => set({ guidedOpen: open }),
  setAcademicOpen: (open) => set({ academicOpen: open }),
  setAcademicDevir: (devir) => set({ academicDevir: devir }),
  setDataPreviewNodeId: (nodeId) => set({ dataPreviewNodeId: nodeId, showDataPreview: !!nodeId }),

  // Geçmiş yalnız YAPIYI tutar (sonuç ve CSV satırı yok — bkz. lib/kalicilik).
  // Eskiden her adım tüm satırları ve sonuçları derin kopyalıyordu.
  pushHistory: () => {
    const { nodes, edges, history, historyIndex } = get();
    const newHistory = history.slice(0, historyIndex + 1);
    newHistory.push({
      nodes: JSON.parse(JSON.stringify(kaliciDugumler(nodes))),
      edges: JSON.parse(JSON.stringify(edges))
    });
    if (newHistory.length > MAX_HISTORY) newHistory.shift();
    const newIndex = newHistory.length - 1;
    set({ history: newHistory, historyIndex: newIndex, canUndo: newIndex > 0, canRedo: false });
  },

  undo: () => {
    const { historyIndex, history } = get();
    if (historyIndex <= 0) return;
    const newIndex = historyIndex - 1;
    const state = history[newIndex];
    const edges = JSON.parse(JSON.stringify(state.edges));
    set({
      // Yapısı değişmemiş alt grafın sonuçları korunur.
      nodes: sonuclariAktar(get().nodes, get().edges, JSON.parse(JSON.stringify(state.nodes)), edges),
      edges,
      historyIndex: newIndex,
      canUndo: newIndex > 0,
      canRedo: true,
      selectedNode: null
    });
  },

  redo: () => {
    const { historyIndex, history } = get();
    if (historyIndex >= history.length - 1) return;
    const newIndex = historyIndex + 1;
    const state = history[newIndex];
    const edges = JSON.parse(JSON.stringify(state.edges));
    set({
      nodes: sonuclariAktar(get().nodes, get().edges, JSON.parse(JSON.stringify(state.nodes)), edges),
      edges,
      historyIndex: newIndex,
      canUndo: true,
      canRedo: newIndex < history.length - 1,
      selectedNode: null
    });
  },

  addSavedModel: (model) => set((state) => ({
    savedModels: [...state.savedModels, { ...model, nodes: kaliciDugumler(model.nodes), id: `model-${Date.now()}`, createdAt: new Date().toISOString(), updatedAt: new Date().toISOString(), runs: 0 }]
  })),

  loadModel: (model) => {
    const { nodes, edges } = yuklenenAkis(model.nodes, model.edges);
    set({ nodes, edges, selectedNode: null });
    get().pushHistory();
  },

  deleteModel: (id) => set((state) => ({
    savedModels: state.savedModels.filter((m) => m.id !== id)
  })),

  setActivePanel: (panel) => set({ activePanel: panel }),
  setSidebarOpen: (open) => set({ sidebarOpen: open }),
  setLanguage: (lang) => {
    try { localStorage.setItem('dataflow_lang', lang); } catch { /* private mode */ }
    set({ language: lang });
  },

  // P1-1: localStorage persistence
  // Sonuç ve CSV satırı yazılmaz (lib/kalicilik). Başarı döner: eskiden kota
  // dolunca hata yutuluyor, arayüz yine "kaydedildi" diyordu.
  saveToLocalStorage: () => {
    const state = get();
    const data = {
      nodes: kaliciDugumler(state.nodes),
      edges: state.edges,
      savedModels: state.savedModels
        .filter((m) => !prebuilt.some((h) => h.id === m.id))
        .map((m) => ({ ...m, nodes: kaliciDugumler(m.nodes) })),
      timestamp: new Date().toISOString()
    };
    try {
      localStorage.setItem(DEPO_ANAHTARI, JSON.stringify(data));
      return true;
    } catch {
      get().addLog('Tarayıcı deposuna yazılamadı (dolu ya da gizli pencere) — iş akışı KAYDEDİLMEDİ.');
      return false;
    }
  },

  loadFromLocalStorage: () => {
    try {
      const raw = localStorage.getItem(DEPO_ANAHTARI);
      if (!raw) return false;
      const data = JSON.parse(raw);
      if (data.nodes && Array.isArray(data.nodes)) {
        const { nodes, edges, atlanan } = yuklenenAkis(data.nodes, data.edges);
        set({ nodes, edges, savedModels: modelleriBirlestir(data.savedModels) });
        if (atlanan) get().addLog(`Kayıtlı iş akışında onarılamayan ${atlanan} düğüm/bağlantı atlandı.`);
        get().pushHistory();
        return true;
      }
    } catch { /* Invalid data */ }
    return false;
  },

  // P1-2: Execution audit log
  addAuditLog: (entry: AuditLogEntry) => {
    const logs = get().auditLog;
    logs.push(entry);
    // Keep only last 100 entries
    if (logs.length > 100) logs.shift();
    // Persist to localStorage
    try {
      localStorage.setItem('dataflow_audit', JSON.stringify(logs));
    } catch { /* Storage full */ }
    set({ auditLog: [...logs] });
  },

  loadAuditLog: () => {
    try {
      const raw = localStorage.getItem('dataflow_audit');
      if (raw) set({ auditLog: JSON.parse(raw) });
    } catch { /* Invalid data */ }
  },
}));

export interface AuditLogEntry {
  timestamp: string;
  action: 'execute' | 'node_add' | 'node_delete' | 'node_config' | 'connect' | 'disconnect' | 'save' | 'load';
  nodeId?: string;
  nodeType?: string;
  details?: string;
  userAgent: string;
}
