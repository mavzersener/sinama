// İş akışı doğrulaması (port kuralları, zorunlu alanlar, döngü, veri sözleşmesi ön-kontrolü) ve yürütme sırası.
// (executionEngine.ts'den bölündü — Faz 4.)

import type { Node, Edge } from '@xyflow/react';
import { analizOnKontrol, VERI_SOZLESMELERI, engelVar } from './veriSozlesmesi';
import type { NodeData } from '../store/useStore';
import type { VeriKaynagi } from '../lib/veriDeposu';

export interface ValidationError {
  nodeId: string;
  nodeLabel: string;
  message: string;
  severity: 'error' | 'warning';
}

// ============================================================
// WORKFLOW VALIDATION
// ============================================================

export function validateWorkflow(nodes: Node<NodeData>[], edges: Edge[]): ValidationError[] {
  const errors: ValidationError[] = [];

  if (nodes.length === 0) {
    errors.push({ nodeId: '', nodeLabel: '', message: 'Workflow is empty. Add at least one node.', severity: 'error' });
    return errors;
  }

  // Check for source nodes
  const sourceTypes = new Set(['csv_source', 'db_source', 'api_source', 'pts_source', 'anpr_source', 'mobese_source', 'ihbar_source', 'adli_sicil_source']);
  const sourceNodes = nodes.filter((n) => sourceTypes.has(n.data.type));
  if (sourceNodes.length === 0) {
    errors.push({ nodeId: '', nodeLabel: '', message: 'Workflow must have at least one data source (CSV, Database, or API).', severity: 'error' });
  }

  // Check for orphaned nodes
  const connectedNodeIds = new Set<string>();
  edges.forEach((e) => { connectedNodeIds.add(e.source); connectedNodeIds.add(e.target); });

  nodes.forEach((node) => {
    const isSource = sourceTypes.has(node.data.type);
    if (!isSource && !connectedNodeIds.has(node.id)) {
      errors.push({ nodeId: node.id, nodeLabel: node.data.label, message: `Node "${node.data.label}" has no connections.`, severity: 'warning' });
    }

    // Check required config
    const required = getRequiredFields(node.data.type);
    // Hata mesajı NE YAPILACAĞINI söylemeli: yalnız "boş" demek kullanıcıyı
    // sütun adını tahmin etmeye zorluyordu. Yukarı akıştaki sütunları
    // mesaja ekliyoruz.
    const ustSutunlar = ustAkisSutunlari(node.id, nodes, edges);
    for (const field of required) {
      const val = node.data.config?.[field];
      if (val === undefined || val === null || val === '') {
        const ipucu = /column$/i.test(field) && ustSutunlar.length
          ? ` Seçilebilir sütunlar: ${ustSutunlar.slice(0, 12).join(', ')}${ustSutunlar.length > 12 ? '…' : ''}.`
          : '';
        errors.push({ nodeId: node.id, nodeLabel: node.data.label, message: `Required "${field}" is empty in ${node.data.label}.${ipucu}`, severity: 'error' });
      }
    }

    // Check port constraints
    const def = getNodePortDef(node.data.type);
    const incoming = edges.filter((e) => e.target === node.id).length;

    if (def.minInputs > 0 && incoming < def.minInputs) {
      errors.push({ nodeId: node.id, nodeLabel: node.data.label, message: `${node.data.label} needs ${def.minInputs} input(s), has ${incoming}.`, severity: 'error' });
    }
    if (def.maxInputs > 0 && incoming > def.maxInputs) {
      errors.push({ nodeId: node.id, nodeLabel: node.data.label, message: `${node.data.label} accepts max ${def.maxInputs} input(s), has ${incoming}.`, severity: 'error' });
    }
  });

  // Check for cycles
  const cycleNodes = detectCycles(nodes, edges);
  cycleNodes.forEach((id) => {
    const node = nodes.find((n) => n.id === id);
    if (node) errors.push({ nodeId: id, nodeLabel: node.data.label, message: `Cycle detected involving "${node.data.label}".`, severity: 'error' });
  });

  return errors;
}

function getNodePortDef(type: string): { minInputs: number; maxInputs: number } {
  const defs: Record<string, { minInputs: number; maxInputs: number }> = {
    csv_source: { minInputs: 0, maxInputs: 0 },
    db_source: { minInputs: 0, maxInputs: 0 },
    api_source: { minInputs: 0, maxInputs: 0 },
    filter: { minInputs: 1, maxInputs: 1 },
    extend_field: { minInputs: 1, maxInputs: 1 },
    aggregate: { minInputs: 1, maxInputs: 1 },
    sort: { minInputs: 1, maxInputs: 1 },
    join: { minInputs: 2, maxInputs: 2 },
    dedup: { minInputs: 1, maxInputs: 1 },
    statistics: { minInputs: 1, maxInputs: 1 },
    linear_regression: { minInputs: 1, maxInputs: 1 },
    association_rules: { minInputs: 1, maxInputs: 1 },
    clustering: { minInputs: 1, maxInputs: 1 },
    anomaly_detection: { minInputs: 1, maxInputs: 1 },
    correlation: { minInputs: 1, maxInputs: 1 },
    model_validation: { minInputs: 1, maxInputs: 1 },
    data_quality: { minInputs: 1, maxInputs: 1 },
    cross_validation: { minInputs: 1, maxInputs: 1 },
    pts_source: { minInputs: 0, maxInputs: 0 },
    anpr_source: { minInputs: 0, maxInputs: 0 },
    mobese_source: { minInputs: 0, maxInputs: 0 },
    ihbar_source: { minInputs: 0, maxInputs: 0 },
    adli_sicil_source: { minInputs: 0, maxInputs: 0 },
    agent_insight: { minInputs: 1, maxInputs: 0 }, // 0 = unlimited: summarize many upstream analyses
    sna: { minInputs: 1, maxInputs: 1 },
    geo_hotspot: { minInputs: 1, maxInputs: 1 },
    temporal_pattern: { minInputs: 1, maxInputs: 1 },
    cooccurrence: { minInputs: 1, maxInputs: 1 },
    chart: { minInputs: 1, maxInputs: 1 },
    export: { minInputs: 1, maxInputs: 1 },
    alert: { minInputs: 1, maxInputs: 1 },
    evidence_export: { minInputs: 1, maxInputs: 1 },
  };
  return defs[type] || { minInputs: 1, maxInputs: 1 };
}

function detectCycles(nodes: Node<NodeData>[], edges: Edge[]): string[] {
  const adj: Record<string, string[]> = {};
  nodes.forEach((n) => { adj[n.id] = []; });
  edges.forEach((e) => { adj[e.source] = adj[e.source] || []; adj[e.source].push(e.target); });

  const visited = new Set<string>();
  const recStack = new Set<string>();
  const cycles: string[] = [];

  function dfs(id: string): boolean {
    visited.add(id); recStack.add(id);
    for (const n of adj[id] || []) {
      if (!visited.has(n)) { if (dfs(n)) { if (!cycles.includes(id)) cycles.push(id); return true; } }
      else if (recStack.has(n)) { if (!cycles.includes(id)) cycles.push(id); return true; }
    }
    recStack.delete(id);
    return false;
  }

  for (const n of nodes) if (!visited.has(n.id)) dfs(n.id);
  return cycles;
}

function getRequiredFields(type: string): string[] {
  const map: Record<string, string[]> = {
    csv_source: ['filename'], db_source: ['connection', 'query'], api_source: ['url'],
    filter: ['column', 'condition'], extend_field: ['newColumn'],
    aggregate: ['groupBy'], join: ['leftKey', 'rightKey'],
    anomaly_detection: ['columns'], linear_regression: ['target'],
    association_rules: ['itemsColumn'], clustering: ['features'],
    correlation: ['columns'],
    model_validation: ['actualColumn', 'predictedColumn'],
    data_quality: [],
    cross_validation: ['target'],
    pts_source: ['legalBasis', 'kvkkClass'],
    anpr_source: ['legalBasis', 'kvkkClass'],
    mobese_source: ['legalBasis', 'kvkkClass'],
    ihbar_source: ['legalBasis', 'kvkkClass'],
    adli_sicil_source: ['tcKimlik', 'legalBasis', 'kvkkClass'],
    sna: ['personColumn', 'linkColumn'],
    geo_hotspot: ['latColumn', 'lngColumn'],
    temporal_pattern: ['timeColumn'],
    cooccurrence: ['entityColumn', 'contextColumn'],
    evidence_export: ['caseNumber', 'officerId'],
    chart: ['chartType'], export: ['filename']
  };
  return map[type] || [];
}

/**
 * Bir düğümün yukarı akışındaki sütun adları (doğrulama mesajına ipucu).
 *
 * Motor tarafında hafif tutuldu: en yakın sonucu/yüklenmiş veriyi taşıyan
 * düğümü genişlik-öncelikli arar ve döngüde takılmaz.
 */
function ustAkisSutunlari(hedefId: string, nodes: Node<NodeData>[], edges: Edge[]): string[] {
  const gelen = new Map<string, string[]>();
  edges.forEach((e) => {
    const l = gelen.get(e.target) ?? [];
    l.push(e.source);
    gelen.set(e.target, l);
  });
  const harita = new Map(nodes.map((n) => [n.id, n]));
  const gorulen = new Set<string>([hedefId]);
  let sira = [...(gelen.get(hedefId) ?? [])];
  while (sira.length) {
    const sonraki: string[] = [];
    for (const id of sira) {
      if (gorulen.has(id)) continue;
      gorulen.add(id);
      const n = harita.get(id);
      const yuklenen = (n?.data.config?._veriKaynagi as VeriKaynagi | undefined)?.columns
        ?? (n?.data.config?._uploadedData as { columns?: string[] } | undefined)?.columns;
      const sutunlar = n?.data.result?.columns?.length ? n.data.result.columns : yuklenen;
      if (sutunlar?.length) return [...sutunlar];
      sonraki.push(...(gelen.get(id) ?? []));
    }
    sira = sonraki;
  }
  return [];
}

/**
 * Analiz öncesi veri uygunluk kontrolü.
 *
 * @returns engel varsa kullanıcıya gösterilecek hata metni; yoksa null
 */
export function veriOnKontrolu(
  type: string,
  config: Record<string, unknown>,
  inputData: Record<string, unknown> | null,
): string | null {
  if (!VERI_SOZLESMELERI[type]) return null;
  const rows = (inputData?.rows as Record<string, unknown>[] | undefined) ?? [];
  if (rows.length === 0) return null; // boş girdiyi yürütücüler kendi bildirir
  const cols = (inputData?.columns as string[] | undefined) ?? Object.keys(rows[0] ?? {});

  const bulgular = analizOnKontrol(type, config, cols, rows);
  if (!engelVar(bulgular)) return null;

  // Yalnız engelleri bildir; uyarılar sonucu durdurmaz.
  return bulgular
    .filter((b) => b.seviye === 'engel')
    .map((b) => `${b.mesaj} → ${b.cozum}`)
    .join(' | ');
}

// ============================================================
// EXECUTION ORDER
// ============================================================

export function getExecutionOrder(nodes: Node<NodeData>[], edges: Edge[]): string[] {
  const inDegree: Record<string, number> = {};
  const adj: Record<string, string[]> = {};
  nodes.forEach((n) => { inDegree[n.id] = 0; adj[n.id] = []; });
  edges.forEach((e) => { adj[e.source] = adj[e.source] || []; adj[e.source].push(e.target); inDegree[e.target] = (inDegree[e.target] || 0) + 1; });

  const queue: string[] = [];
  Object.keys(inDegree).forEach((id) => { if (inDegree[id] === 0) queue.push(id); });

  const order: string[] = [];
  while (queue.length > 0) {
    const curr = queue.shift()!;
    order.push(curr);
    (adj[curr] || []).forEach((next) => { inDegree[next]--; if (inDegree[next] === 0) queue.push(next); });
  }
  return order;
}

/** Her zaman sentetik veri üreten kaynaklar (gerçek bağlantıları yok). */
const HEP_DEMO_KAYNAK = new Set(['db_source', 'api_source', 'pts_source', 'anpr_source', 'mobese_source', 'ihbar_source', 'adli_sicil_source']);

/**
 * Düğüm koşulduğunda sentetik (demo) veri mi üretecek? DB/API ve kolluk
 * kaynakları her zaman; CSV yalnız dosya yüklenmemişse. Araç çubuğu bandı ve
 * düğüm rozeti bunu KOŞMADAN önce de gösterir.
 */
export function demoKaynagiMi(tip: string, config: Record<string, unknown> | null | undefined): boolean {
  if (HEP_DEMO_KAYNAK.has(tip)) return true;
  if (tip === 'csv_source') return !config?._veriKaynagi && !config?._uploadedData;
  return false;
}
