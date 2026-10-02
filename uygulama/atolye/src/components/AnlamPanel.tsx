import { useEffect, useState } from 'react';
import { Network } from 'lucide-react';
import { useStore } from '@/store/useStore';

/**
 * Anlam Paneli: workflow'un Anlam Çekirdeği'ndeki epistemik aynası.
 * Veriyi anlam-viewer sunucusundan (8137, CORS'lu) çeker; DataFlow
 * backend'ine dokunmaz. "Kullanıcı az şey görür ama neyi görmediğini bilir."
 */

interface IndexEntry {
  id: string;
  title: string;
  profile: string;
}

interface Korunum {
  evren: number;
  gorunur: number;
  katlanan: number;
  hayalet: number;
  tutar: boolean;
}

interface Hayalet {
  title: string;
  sayi: number;
  _celiskili: boolean;
}

interface Birim {
  id: string;
  kind: string;
  type: string;
  title?: string;
  source?: string;
  target?: string;
  relation?: string;
  grounding?: { truth_status?: string };
}

interface AnlamVeri {
  meta: { title: string };
  sade: { korunum: Korunum; hayaletler: Hayalet[] };
  detay: { nodes: Birim[]; edges: Birim[] };
}

const VIEWER = 'http://localhost:8137';

// Modül düzeyinde: render içinde tanımlanan bileşen her render'da YENİ bir
// tür olur ve alt ağaç her seferinde sökülüp yeniden kurulurdu.
const Baslik = ({ children }: { children: React.ReactNode }) => (
  <div className="text-slate-400 uppercase text-[10px] tracking-wide mt-3 mb-1">{children}</div>
);

/** Yüklenen veri, AİT OLDUĞU workflow kimliğiyle saklanır. */
interface Yukleme {
  workflowId: number;
  veri: AnlamVeri | null;
  mesaj: string | null;
}

export default function AnlamPanel() {
  const cloudWorkflowId = useStore((s) => s.cloudWorkflowId);
  const selectedNode = useStore((s) => s.selectedNode);

  const [open, setOpen] = useState(false);
  const [yukleme, setYukleme] = useState<Yukleme | null>(null);

  // Effect yalnız asenkron yüklemeyi başlatır; durum ancak yanıt gelince ve
  // panel hâlâ aynı workflow'u gösteriyorsa yazılır (eskiden effect içinde
  // eşzamanlı setState vardı ve workflow değişince eski veri bir an kalırdı).
  useEffect(() => {
    if (!open || cloudWorkflowId == null) return;
    let iptal = false;
    const yaz = (y: Omit<Yukleme, 'workflowId'>) => { if (!iptal) setYukleme({ workflowId: cloudWorkflowId, ...y }); };
    void (async () => {
      try {
        const idx: IndexEntry[] = await (await fetch(`${VIEWER}/surfaces/viewer3d/data/index.json`)).json();
        const kayit = idx.find((g) => g.id.startsWith(`df_${cloudWorkflowId}_`));
        if (!kayit) {
          yaz({ veri: null, mesaj: "Bu workflow henüz Anlam Çekirdeği'ne aktarılmamış (pipeline/dataflow_import.py)." });
          return;
        }
        const d: AnlamVeri = await (await fetch(`${VIEWER}/surfaces/viewer3d/data/${kayit.id}.json`)).json();
        yaz({ veri: d, mesaj: null });
      } catch {
        yaz({ veri: null, mesaj: 'Anlam sunucusu (8137) kapalı.' });
      }
    })();
    return () => { iptal = true; };
  }, [open, cloudWorkflowId]);

  // Görünen durum TÜRETİLİR: başka workflow'un verisi asla gösterilmez.
  const guncel = yukleme && yukleme.workflowId === cloudWorkflowId ? yukleme : null;
  const veri = guncel?.veri ?? null;
  const mesaj = cloudWorkflowId == null
    ? 'Workflow buluta kaydedilmemiş — Anlam aynası için önce kaydedin.'
    : guncel ? guncel.mesaj : 'Yükleniyor…';

  const kosular = veri?.detay.nodes.filter((n) => n.type === 'veri_kumesi') ?? [];
  const baglar = selectedNode
    ? (veri?.detay.edges.filter((e) => e.source === selectedNode || e.target === selectedNode) ?? [])
    : [];

  return (
    <>
      <button
        onClick={() => setOpen((o) => !o)}
        className="fixed bottom-4 right-4 z-50 flex items-center gap-1.5 bg-violet-700 hover:bg-violet-600 text-white rounded-full px-4 py-2 text-xs shadow-lg"
        title="Anlam Çekirdeği aynası"
      >
        <Network className="w-3.5 h-3.5" />
        Anlam
      </button>

      {open && (
        <div className="fixed bottom-14 right-4 z-50 w-96 max-h-[28rem] overflow-y-auto bg-slate-900 border border-slate-700 rounded-lg p-4 text-xs text-slate-200 shadow-xl">
          {mesaj && <div className="text-slate-400">{mesaj}</div>}

          {veri && (
            <>
              <div className="font-medium text-sm">{veri.meta.title}</div>
              <div className="text-slate-400 mt-1">
                evren {veri.sade.korunum.evren} birim: {veri.sade.korunum.gorunur} görünür +{' '}
                {veri.sade.korunum.katlanan} katlanan + {veri.sade.korunum.hayalet} hayalet{' '}
                {veri.sade.korunum.tutar ? '✓ korunum' : '✗ KORUNUM BOZUK'}
              </div>

              <Baslik>Gizlenenler</Baslik>
              {veri.sade.hayaletler.length === 0 && <div>Gizlenen yok (bütçe altında).</div>}
              {veri.sade.hayaletler.map((h) => (
                <div key={h.title}>
                  {h.title}
                  {h._celiskili && <span className="text-red-400"> ⚠ çelişkili bilgi içeriyor</span>}
                </div>
              ))}

              <Baslik>Koşu Kayıtları</Baslik>
              {kosular.length === 0 && <div>Henüz kalıcı koşu yok — Run ile koşu kaydı oluşur.</div>}
              {kosular.map((k) => (
                <div key={k.id}>
                  {k.title}{' '}
                  <span className={k.grounding?.truth_status === 'contested' ? 'text-amber-400' : 'text-slate-400'}>
                    [{k.grounding?.truth_status ?? '?'}]
                  </span>
                </div>
              ))}

              {selectedNode && (
                <>
                  <Baslik>Seçili Düğümün Bağları</Baslik>
                  {baglar.length === 0 && <div>Bu düğümün kaydı grafta yok.</div>}
                  {baglar.map((e) => (
                    <div key={e.id} className="font-mono text-[10px]">
                      {e.source} —{e.relation}→ {e.target}
                    </div>
                  ))}
                </>
              )}

              <div className="mt-3">
                <a
                  href={`${VIEWER}/surfaces/viewer3d/index.html`}
                  target="_blank"
                  rel="noreferrer"
                  className="text-violet-400 hover:text-violet-300"
                >
                  3B görünümde aç ↗
                </a>
              </div>
            </>
          )}
        </div>
      )}
    </>
  );
}
