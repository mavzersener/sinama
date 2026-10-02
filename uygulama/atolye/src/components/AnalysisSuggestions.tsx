import { useMemo, useRef } from 'react';
import type { Node } from '@xyflow/react';
import { Sparkles, Plus } from 'lucide-react';
import { useStore, type NodeData } from '../store/useStore';
import { getNodeDefinition } from '../nodes/nodeDefinitions';
import { recommendAnalyses, type Recommendation } from '../engine/recommendations';
import FeedbackButtons from './FeedbackButtons';
import { veriAl, type VeriKaynagi } from '../lib/veriDeposu';

/** Extract columns + sample rows from an uploaded file or an executed result. */
function extractData(node: Node<NodeData>): { columns: string[]; rows: Record<string, unknown>[] } | null {
  // Yüklenen dosya: tablo depoda (bu oturumda); yoksa düğümdeki önizleme.
  const kaynak = node.data.config?._veriKaynagi as VeriKaynagi | undefined;
  if (kaynak) {
    const rows = veriAl(kaynak.anahtar)?.rows ?? kaynak.onizleme;
    if (rows.length) return { columns: kaynak.columns, rows };
  }

  const result = node.data.result;
  const data = result?.data as { rows?: Record<string, unknown>[]; columns?: string[] } | undefined;
  if (data?.rows?.length) {
    const columns = data.columns ?? Object.keys(data.rows[0] ?? {});
    return { columns, rows: data.rows };
  }
  return null;
}

export default function AnalysisSuggestions({ node }: { node: Node<NodeData> }) {
  const addNode = useStore((s) => s.addNode);
  const onConnect = useStore((s) => s.onConnect);
  const setSelectedNode = useStore((s) => s.setSelectedNode);
  const addedCount = useRef(0);

  const recommendations = useMemo<Recommendation[]>(() => {
    const data = extractData(node);
    if (!data || data.columns.length === 0) return [];
    return recommendAnalyses(data.columns, data.rows);
    // Re-run when the node's data changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [node.id, node.data.config?._veriKaynagi, node.data.result]);

  if (recommendations.length === 0) {
    return (
      <div className="mt-3 p-3 rounded-lg bg-slate-800/40 border border-slate-700/60">
        <div className="flex items-center gap-2 text-xs text-slate-400">
          <Sparkles size={13} className="text-amber-400" />
          <span className="font-medium">Suggested Analyses</span>
        </div>
        <p className="mt-1.5 text-[10px] text-slate-500">
          Upload a CSV or run the workflow to get data-driven analysis suggestions.
        </p>
      </div>
    );
  }

  const handleAdd = (rec: Recommendation) => {
    const def = getNodeDefinition(rec.nodeType);
    if (!def) return;

    const idx = addedCount.current++;
    const newId = `${rec.nodeType}-${Date.now()}`;
    const newNode: Node<NodeData> = {
      id: newId,
      type: 'custom',
      position: {
        x: (node.position?.x ?? 0) + 300,
        y: (node.position?.y ?? 0) + idx * 90,
      },
      data: {
        label: def.label,
        type: def.type,
        category: def.category,
        icon: def.icon,
        color: def.color,
        config: { ...def.defaultConfig, ...rec.config },
        status: 'idle',
      },
    };

    addNode(newNode);
    onConnect({ source: node.id, target: newId, sourceHandle: null, targetHandle: null });
    // Keep the source node selected so several suggestions can be added in a row.
    setSelectedNode(node.id);
  };

  return (
    <div className="mt-3 p-3 rounded-lg bg-slate-800/40 border border-slate-700/60 space-y-2">
      <div className="flex items-center gap-2 text-xs text-slate-400">
        <Sparkles size={13} className="text-amber-400" />
        <span className="font-medium">Suggested Analyses</span>
        <span className="ml-auto text-[10px] text-slate-600">{recommendations.length}</span>
      </div>
      <p className="text-[10px] text-slate-500">Based on this node's columns and value types.</p>

      <div className="space-y-1.5">
        {recommendations.map((rec) => {
          const def = getNodeDefinition(rec.nodeType);
          return (
            <div
              key={`${rec.nodeType}-${rec.title}`}
              className="group flex items-start gap-2 p-2 rounded-lg bg-slate-900/60 border border-slate-800 hover:border-slate-600 transition-colors"
            >
              <span
                className="mt-0.5 w-1.5 h-1.5 rounded-full shrink-0"
                style={{ backgroundColor: def?.color ?? '#8b5cf6' }}
              />
              <div className="min-w-0 flex-1">
                <div className="text-[11px] font-medium text-slate-200">{rec.title}</div>
                <div className="text-[10px] text-slate-500 leading-snug">{rec.reason}</div>
                <div className="mt-1 opacity-60 group-hover:opacity-100 transition-opacity">
                  <FeedbackButtons kind="suggestion" nodeType={rec.nodeType} />
                </div>
              </div>
              <button
                onClick={() => handleAdd(rec)}
                title={`Add "${rec.title}" and connect it`}
                className="shrink-0 flex items-center gap-0.5 px-1.5 py-1 rounded-md text-[10px] text-slate-400 hover:text-white hover:bg-blue-600/80 transition-colors opacity-70 group-hover:opacity-100"
              >
                <Plus size={11} />
                Add
              </button>
            </div>
          );
        })}
      </div>
    </div>
  );
}
