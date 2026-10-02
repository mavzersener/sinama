import { useStore } from '../store/useStore';
import { X, ChevronLeft, ChevronRight } from 'lucide-react';
import { useState } from 'react';

export default function DataPreview() {
  const nodes = useStore((s) => s.nodes);
  const dataPreviewNodeId = useStore((s) => s.dataPreviewNodeId);
  const setShowDataPreview = useStore((s) => s.setShowDataPreview);
  const setDataPreviewNodeId = useStore((s) => s.setDataPreviewNodeId);
  const [page, setPage] = useState(0);

  const node = nodes.find((n) => n.id === dataPreviewNodeId);
  const result = node?.data.result;

  if (!node || !result || result.status !== 'success') {
    return null;
  }

  const rows = (result.data as Record<string, unknown> & { rows?: Record<string, unknown>[] })?.rows || [];
  const columns = result.columns || (rows.length > 0 ? Object.keys(rows[0]) : []);

  const PAGE_SIZE = 15;
  const totalPages = Math.ceil(rows.length / PAGE_SIZE);
  const paginatedRows = rows.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);

  const handleClose = () => {
    setShowDataPreview(false);
    setDataPreviewNodeId(null);
  };

  const handlePrevNode = () => {
    const idx = nodes.findIndex((n) => n.id === dataPreviewNodeId);
    if (idx > 0) {
      const prev = nodes[idx - 1];
      setDataPreviewNodeId(prev.id);
      setPage(0);
    }
  };

  const handleNextNode = () => {
    const idx = nodes.findIndex((n) => n.id === dataPreviewNodeId);
    if (idx < nodes.length - 1) {
      const next = nodes[idx + 1];
      setDataPreviewNodeId(next.id);
      setPage(0);
    }
  };

  const currentIdx = nodes.findIndex((n) => n.id === dataPreviewNodeId);

  return (
    <div className="h-[280px] bg-slate-900 border-t border-slate-800 flex flex-col">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-2 border-b border-slate-800">
        <div className="flex items-center gap-3">
          <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">Data Preview</span>
          <div className="flex items-center gap-1.5 text-[10px] text-slate-500">
            <button
              onClick={handlePrevNode}
              disabled={currentIdx <= 0}
              className="p-0.5 rounded hover:bg-slate-800 disabled:opacity-30 transition-colors"
            >
              <ChevronLeft size={12} />
            </button>
            <span className="bg-slate-800 px-1.5 py-0.5 rounded">{node.data.label}</span>
            <button
              onClick={handleNextNode}
              disabled={currentIdx >= nodes.length - 1}
              className="p-0.5 rounded hover:bg-slate-800 disabled:opacity-30 transition-colors"
            >
              <ChevronRight size={12} />
            </button>
          </div>
          <span className="text-[10px] text-slate-600">
            {result.rowCount?.toLocaleString()} rows
          </span>
        </div>
        <div className="flex items-center gap-2">
          {totalPages > 1 && (
            <div className="flex items-center gap-1 text-[10px] text-slate-500">
              <button
                onClick={() => setPage((p) => Math.max(0, p - 1))}
                disabled={page === 0}
                className="p-0.5 rounded hover:bg-slate-800 disabled:opacity-30"
              >
                <ChevronLeft size={10} />
              </button>
              <span>Page {page + 1} / {totalPages}</span>
              <button
                onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                disabled={page >= totalPages - 1}
                className="p-0.5 rounded hover:bg-slate-800 disabled:opacity-30"
              >
                <ChevronRight size={10} />
              </button>
            </div>
          )}
          <button onClick={handleClose} className="text-slate-500 hover:text-white transition-colors">
            <X size={14} />
          </button>
        </div>
      </div>

      {/* Table */}
      <div className="flex-1 overflow-auto">
        {rows.length === 0 ? (
          <div className="flex items-center justify-center h-full text-xs text-slate-500">
            No data available
          </div>
        ) : (
          <table className="w-full text-[10px]">
            <thead className="sticky top-0 bg-slate-800 z-10">
              <tr>
                <th className="text-left px-2 py-1.5 text-slate-500 font-medium border-b border-slate-700 w-8">#</th>
                {columns.map((col) => (
                  <th key={col} className="text-left px-2 py-1.5 text-slate-400 font-medium border-b border-slate-700 whitespace-nowrap">
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {paginatedRows.map((row, i) => (
                <tr key={i} className="hover:bg-slate-800/50 transition-colors">
                  <td className="px-2 py-1 text-slate-600 border-b border-slate-800/50">{page * PAGE_SIZE + i + 1}</td>
                  {columns.map((col) => (
                    <td key={col} className="px-2 py-1 text-slate-300 border-b border-slate-800/50 max-w-[150px] truncate">
                      {String((row as Record<string, unknown>)[col] ?? '')}
                    </td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
