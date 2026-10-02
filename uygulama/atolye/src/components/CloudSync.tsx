import { useState, useCallback } from "react";
import { useNavigate } from "react-router";
import {
  Cloud, CloudOff, Save, FolderOpen, LogOut, Loader2, Trash2, Check, X, Award,
} from "lucide-react";
import { useAuth } from "@/hooks/useAuth";
import { useWorkflowSync } from "@/hooks/useWorkflowSync";
import { useCatalog } from "@/hooks/useCatalog";
import { useStore } from "@/store/useStore";

/**
 * P0 Integration UI: server-backed workflow sync for authenticated users.
 * The editor itself stays usable offline; this panel only adds cloud
 * persistence (save / open / delete) on top of the tRPC workflow API.
 */
export default function CloudSync() {
  const navigate = useNavigate();
  const { user, isAuthenticated, isLoading: authLoading, logout } = useAuth();
  const sync = useWorkflowSync(isAuthenticated);
  const catalog = useCatalog(false); // only need promote() here, not the list

  const nodeCount = useStore((s) => s.nodes.length);
  const isAdmin = user?.role === "admin";

  const [open, setOpen] = useState(false);
  const [naming, setNaming] = useState(false);
  const [name, setName] = useState("");
  const [currentId, setCurrentIdState] = useState<number | undefined>(undefined);
  const setCloudWorkflowId = useStore((s) => s.setCloudWorkflowId);
  // Yerel id ile global store'u tek noktadan senkron tut
  // (koşu kalıcılaştırma ve Anlam paneli cloudWorkflowId'yi kullanır).
  const setCurrentId = useCallback(
    (id: number | undefined) => {
      setCurrentIdState(id);
      setCloudWorkflowId(id ?? null);
    },
    [setCloudWorkflowId],
  );
  const [toast, setToast] = useState<string | null>(null);
  const [promoting, setPromoting] = useState(false);

  const flash = useCallback((msg: string) => {
    setToast(msg);
    window.setTimeout(() => setToast(null), 2500);
  }, []);

  const handleSave = useCallback(async () => {
    const finalName = name.trim() || `Workflow ${new Date().toLocaleString()}`;
    try {
      const id = await sync.save({ id: currentId, name: finalName });
      setCurrentId(id);
      setNaming(false);
      setName("");
      flash(currentId ? "Updated in cloud" : "Saved to cloud");
    } catch {
      flash("Save failed");
    }
  }, [name, currentId, sync, flash, setCurrentId]);

  const handleOpen = useCallback(
    (wf: { id: number; nodes: unknown; edges: unknown; name: string }) => {
      const id = sync.load(wf);
      setCurrentId(id);
      setOpen(false);
      flash(`Opened "${wf.name}"`);
    },
    [sync, flash, setCurrentId],
  );

  const handleDelete = useCallback(
    async (id: number, e: React.MouseEvent) => {
      e.stopPropagation();
      await sync.remove(id);
      if (currentId === id) setCurrentId(undefined);
    },
    [sync, currentId, setCurrentId],
  );

  const handlePromote = useCallback(async () => {
    if (!currentId) return;
    setPromoting(true);
    try {
      await catalog.promote(currentId);
      flash("Katalogda yayınlandı");
    } catch {
      flash("Katalogda yayınlanamadı");
    } finally {
      setPromoting(false);
    }
  }, [currentId, catalog, flash]);

  // ── Not signed in ──────────────────────────────────────
  if (!authLoading && !isAuthenticated) {
    return (
      <button
        onClick={() => navigate("/login")}
        title="Sign in to save workflows to the cloud"
        className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-slate-400 hover:text-white hover:bg-slate-800 transition-all"
      >
        <CloudOff size={13} />
        Sign in to sync
      </button>
    );
  }

  return (
    <div className="relative flex items-center gap-1">
      {/* Save to cloud */}
      {naming ? (
        <div className="flex items-center gap-1 bg-slate-800 rounded-lg px-1.5 py-1">
          <input
            autoFocus
            value={name}
            onChange={(e) => setName(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") void handleSave();
              if (e.key === "Escape") { setNaming(false); setName(""); }
            }}
            placeholder={currentId ? "Update name…" : "Workflow name…"}
            className="w-36 bg-transparent text-xs text-slate-200 placeholder-slate-500 focus:outline-none px-1"
          />
          <button onClick={() => void handleSave()} disabled={sync.isSaving} className="text-emerald-400 hover:text-emerald-300 disabled:opacity-50 p-0.5">
            {sync.isSaving ? <Loader2 size={13} className="animate-spin" /> : <Check size={13} />}
          </button>
          <button onClick={() => { setNaming(false); setName(""); }} className="text-slate-500 hover:text-slate-300 p-0.5">
            <X size={13} />
          </button>
        </div>
      ) : (
        <button
          onClick={() => setNaming(true)}
          disabled={nodeCount === 0}
          title={currentId ? "Update workflow in cloud" : "Save workflow to cloud"}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-slate-400 hover:text-white hover:bg-slate-800 transition-all disabled:opacity-40 disabled:cursor-not-allowed"
        >
          <Save size={13} />
          {currentId ? "Update Cloud" : "Save Cloud"}
        </button>
      )}

      {/* Open from cloud */}
      <button
        onClick={() => { setOpen((v) => !v); if (!open) void sync.refetch(); }}
        className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs transition-all ${
          open ? "text-cyan-400 bg-cyan-400/10" : "text-slate-400 hover:text-white hover:bg-slate-800"
        }`}
      >
        <FolderOpen size={13} />
        Open
      </button>

      {/* Promote to catalog (admin-only; requires an already-saved cloud workflow) */}
      {isAdmin && currentId !== undefined && (
        <button
          onClick={() => void handlePromote()}
          disabled={promoting}
          title="Bu iş akışını yönetici-onaylı kataloğa ekle"
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs text-amber-400/80 hover:text-amber-300 hover:bg-amber-400/10 transition-all disabled:opacity-50"
        >
          {promoting ? <Loader2 size={13} className="animate-spin" /> : <Award size={13} />}
          Promote
        </button>
      )}

      {/* User + sign out */}
      <div className="flex items-center gap-1.5 pl-1 text-[10px] text-slate-500" title={user?.email ?? undefined}>
        <Cloud size={12} className="text-emerald-500" />
        <span className="max-w-[90px] truncate">{user?.name || "Account"}</span>
        <button onClick={logout} title="Sign out" className="text-slate-500 hover:text-red-400 p-0.5">
          <LogOut size={12} />
        </button>
      </div>

      {/* Workflow list dropdown */}
      {open && (
        <div className="absolute top-full right-0 mt-1 w-72 max-h-80 overflow-y-auto bg-slate-900 border border-slate-700 rounded-xl shadow-2xl z-50 p-1.5">
          {sync.isLoading ? (
            <div className="flex items-center gap-2 px-3 py-3 text-xs text-slate-500">
              <Loader2 size={13} className="animate-spin" /> Loading…
            </div>
          ) : sync.isError ? (
            <div className="px-3 py-3 text-xs text-red-400">Failed to load workflows.</div>
          ) : sync.workflows.length === 0 ? (
            <div className="px-3 py-3 text-xs text-slate-500">No saved workflows yet.</div>
          ) : (
            sync.workflows.map((wf) => (
              <button
                key={wf.id}
                onClick={() => handleOpen(wf as unknown as { id: number; nodes: unknown; edges: unknown; name: string })}
                className={`group w-full flex items-center justify-between gap-2 px-3 py-2 rounded-lg text-left transition-colors ${
                  currentId === wf.id ? "bg-cyan-400/10" : "hover:bg-slate-800"
                }`}
              >
                <div className="min-w-0">
                  <div className="text-xs text-slate-200 truncate">{wf.name}</div>
                  <div className="text-[10px] text-slate-500">
                    {wf.status} · {new Date(wf.updatedAt).toLocaleDateString()}
                  </div>
                </div>
                <span
                  role="button"
                  tabIndex={0}
                  onClick={(e) => void handleDelete(wf.id, e)}
                  className="opacity-0 group-hover:opacity-100 text-slate-500 hover:text-red-400 p-1 shrink-0"
                >
                  <Trash2 size={12} />
                </span>
              </button>
            ))
          )}
        </div>
      )}

      {toast && (
        <div className="absolute top-full right-0 mt-1 px-3 py-1.5 rounded-lg bg-slate-800 border border-slate-700 text-[10px] text-emerald-300 shadow-lg whitespace-nowrap z-50">
          {toast}
        </div>
      )}
    </div>
  );
}
