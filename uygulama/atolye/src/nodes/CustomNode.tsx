import { demoKaynagiMi } from '../engine/executionEngine';
import { memo, useCallback, type ComponentType } from 'react';
import { Handle, Position } from '@xyflow/react';
import { useStore } from '../store/useStore';
import type { NodeData } from '../store/useStore';
import {
  FileSpreadsheet, Database, Globe, Filter, PlusCircle,
  BarChart3, ArrowUpDown, GitMerge, CopyMinus, PieChart,
  TrendingUp, Link2, Target, AlertTriangle, Grid3X3,
  BarChart, Download, Bell, Box, Loader2, CheckCircle2, XCircle,
  Table2, Crosshair, ShieldCheck, Shuffle, Shield, Camera,
  Video, PhoneCall, Scale, Network, MapPin, Clock, Users, FileLock, Bot, Wand2
} from 'lucide-react';

const iconComponents: Record<string, ComponentType<{ size?: number; color?: string; className?: string }>> = {
  FileSpreadsheet, Database, Globe, Filter, PlusCircle,
  BarChart3, ArrowUpDown, Merge: GitMerge, CopyMinus, PieChart,
  TrendingUp, Link2, Target, AlertTriangle, Grid3X3,
  BarChart, Download, Bell, Box, Crosshair, ShieldCheck, Shuffle,
  Shield, Camera, Video, PhoneCall, Scale, Network, MapPin, Clock, Users, FileLock, Bot, Wand2
};

const statusBorderClass: Record<string, string> = {
  idle: 'border-slate-600',
  running: 'node-running border-blue-500',
  completed: 'node-completed border-emerald-500',
  error: 'node-error border-red-500'
};

const statusIconComponents: Record<string, ComponentType<{ size?: number; className?: string }>> = {
  running: Loader2,
  completed: CheckCircle2,
  error: XCircle
};

interface NodePropsLike {
  id: string;
  data: NodeData & { status?: 'idle' | 'running' | 'completed' | 'error' };
  selected: boolean;
}

function CustomNode({ id, data, selected }: NodePropsLike) {
  const setSelectedNode = useStore((s) => s.setSelectedNode);
  const setDataPreviewNodeId = useStore((s) => s.setDataPreviewNodeId);

  const handleClick = useCallback(() => {
    setSelectedNode(id);
  }, [id, setSelectedNode]);

  const handlePreviewClick = useCallback((e: React.MouseEvent) => {
    e.stopPropagation();
    setDataPreviewNodeId(id);
  }, [id, setDataPreviewNodeId]);

  const IconComponent = iconComponents[data.icon] || Box;
  const status = data.status || 'idle';
  const StatusIcon = status !== 'idle' ? statusIconComponents[status] : null;

  const categoryGlowClass = `glow-${data.category.toLowerCase().replace(/\s+/g, '-')}`;

  return (
    // DIŞ KATMAN: overflow KIRPMAZ. Handle'lar buranın çocuğudur.
    //
    // Daha önce köşe yuvarlama için kök div'de `overflow-hidden` vardı ve
    // handle'lar `left:-6`/`right:-6` ile kutunun dışına taşıdığı için
    // TAMAMEN kırpılıyordu: tıklama tuvale isabet ediyor, hiçbir bağlantı
    // kurulamıyordu (tests/ui/02-node-baglama.spec.ts bunu ölçüyor).
    // Çözüm: kırpma iç gövdeye indi, handle'lar dışarıda kaldı.
    <div
      onClick={handleClick}
      className={`
        node-appear relative cursor-pointer transition-all duration-200
        min-w-[190px] hover:translate-y-[-1px]
      `}
    >
      {/* İÇ GÖVDE: köşe yuvarlama ve içerik kırpması burada. */}
      <div
        className={`
          rounded-xl overflow-hidden
          ${selected ? 'ring-2 ring-blue-500 shadow-blue-500/20' : ''}
          ${statusBorderClass[status] || 'border border-slate-600/60'}
          ${status === 'idle' ? categoryGlowClass : ''}
          bg-gradient-to-br from-[#141b2d] to-[#1a2332] shadow-xl
          hover:shadow-2xl
        `}
      >
      {/* Category color strip */}
      <div className="h-0.5 w-full" style={{ background: `linear-gradient(90deg, ${data.color}, ${data.color}88)` }} />

      {/* Header */}
      <div
        className="flex items-center gap-2 px-3 py-2 border-b border-slate-700/50"
        style={{ backgroundColor: data.color + '12' }}
      >
        <div
          className="flex items-center justify-center w-7 h-7 rounded-md"
          style={{ backgroundColor: data.color + '30' }}
        >
          <IconComponent size={16} color={data.color} />
        </div>
        <div className="flex-1 min-w-0">
          <div className="text-xs font-semibold text-slate-200 truncate">{data.label}</div>
          <div className="text-[10px] text-slate-500 truncate">{data.category}</div>
        </div>
        <div className="flex items-center gap-1">
          {(data.result ? data.result.status === 'success' && !!data.result.demo : demoKaynagiMi(data.type, data.config)) && (
            <span
              className="text-[9px] font-bold px-1 rounded bg-amber-500/15 text-amber-400 border border-amber-500/30"
              title="Sentetik (demo) veri — gerçek bulgu değildir"
            >
              DEMO
            </span>
          )}
          {data.result && (
            <button
              onClick={handlePreviewClick}
              className="p-0.5 rounded hover:bg-slate-700 text-slate-500 hover:text-blue-400 transition-colors"
              title="View data preview"
            >
              <Table2 size={12} />
            </button>
          )}
          {StatusIcon && (
            <StatusIcon
              size={16}
              className={
                status === 'running'
                  ? 'animate-spin text-blue-400'
                  : status === 'completed'
                    ? 'text-emerald-400'
                    : 'text-red-400'
              }
            />
          )}
        </div>
      </div>

      {/* Body - config preview */}
      <div className="px-3 py-2">
        {Object.entries(data.config || {}).slice(0, 2).map(([key, value]) => (
          <div key={key} className="flex items-center gap-1 text-[10px] text-slate-400">
            <span className="text-slate-500 capitalize">{key}:</span>
            <span className="truncate max-w-[120px] text-slate-300">
              {Array.isArray(value) ? value.join(', ') : String(value)}
            </span>
          </div>
        ))}
        {data.result && (
          <div className="mt-1 pt-1 border-t border-slate-700 flex items-center justify-between">
            <span className="text-[10px] text-emerald-400 font-medium">
              {data.result.rowCount?.toLocaleString()} rows
            </span>
            <span className="text-[9px] text-slate-600">
              {data.result.status}
            </span>
          </div>
        )}
      </div>
      </div>

      {/* Handles — DIŞ katmanda; iç gövdenin overflow-hidden'ı bunları kırpmaz.
          Boyut 14px: 8px'lik nokta fare ile güvenilir tutulamıyordu. */}
      {data.type !== 'csv_source' && data.type !== 'db_source' && data.type !== 'api_source' && (
        <Handle
          type="target"
          position={Position.Left}
          id="input"
          className="!w-3.5 !h-3.5 !bg-blue-500 !border-2 !border-slate-800 hover:!bg-blue-400"
          style={{ left: -7 }}
        />
      )}
      {data.type !== 'chart' && data.type !== 'export' && data.type !== 'alert' && (
        <Handle
          type="source"
          position={Position.Right}
          id="output"
          className="!w-3.5 !h-3.5 !bg-blue-500 !border-2 !border-slate-800 hover:!bg-blue-400"
          style={{ right: -7 }}
        />
      )}
      {data.type === 'join' && (
        <Handle
          type="target"
          position={Position.Top}
          id="input2"
          className="!w-3.5 !h-3.5 !bg-blue-500 !border-2 !border-slate-800 hover:!bg-blue-400"
          style={{ top: -7 }}
        />
      )}
    </div>
  );
}

export default memo(CustomNode);
