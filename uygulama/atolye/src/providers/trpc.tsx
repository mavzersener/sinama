/**
 * tRPC bağdaştırıcısı (Sınama A6, ADR-004 md. 2 — HASAT uyarlaması).
 *
 * DataFlow'da bu dosya `@trpc/react-query` istemcisini Hono + tRPC sunucusuna
 * (`/api/trpc`, superjson) bağlıyor ve sunucunun `AppRouter` türünü içe
 * aktarıyordu. Sınama'da sunucu tek FastAPI süreci: aynı prosedürler
 * `POST /api/atolye/rpc/<yol>` (JSON) uçlarıdır. Bu bağdaştırıcı ÇAĞIRANLARIN
 * kullandığı arayüzü birebir sağlar — `trpc.<grup>.<prosedür>.useQuery(girdi,
 * ayar)`, `.useMutation(ayar)`, `trpc.useUtils()` (`invalidate`) ve
 * `TRPCProvider` — böylece hasat edilen bileşenler ve kancalar değişmez.
 * Satır türleri DataFlow'un drizzle şemasından (db/schema.ts) aktarıldı;
 * tarih alanları ISO-8601 dizgesidir (superjson yok).
 */
import {
  QueryClient, QueryClientProvider, useMutation, useQuery, useQueryClient,
  type UseMutationResult, type UseQueryResult,
} from "@tanstack/react-query";
import type { ReactNode } from "react";

export class RpcHatasi extends Error {
  durum: number;
  constructor(mesaj: string, durum: number) {
    super(mesaj);
    this.durum = durum;
  }
}

async function rpc(yol: string, girdi: unknown): Promise<unknown> {
  const yanit = await fetch(`/api/atolye/rpc/${yol}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    credentials: "include",
    body: JSON.stringify({ girdi: girdi ?? null }),
  });
  const govde = await yanit.json().catch(() => ({}));
  if (!yanit.ok) {
    const h = (govde as { hata?: { mesaj?: string } }).hata;
    throw new RpcHatasi(h?.mesaj ?? `HTTP ${yanit.status}`, yanit.status);
  }
  return govde;
}

// ── DataFlow satır türleri (db/schema.ts) ──────────────────────────────
type Tarih = string;
export interface Kullanici {
  id: number; unionId: string; name: string | null; email: string | null; avatar: string | null;
  role: "user" | "admin"; createdAt: Tarih; updatedAt: Tarih; lastSignInAt: Tarih;
}
export interface AkisSatiri {
  id: number; userId: number; name: string; description: string | null; nodes: unknown; edges: unknown;
  status: "draft" | "published" | "archived"; isPublic: "true" | "false"; version: number; tags: string | null;
  isBestPractice: "true" | "false"; curatorNote: string | null; curatedBy: number | null;
  curatedAt: Tarih | null; createdAt: Tarih; updatedAt: Tarih;
}
export interface KosuSatiri {
  id: number; workflowId: number; userId: number; status: "running" | "completed" | "failed" | "cancelled";
  results: unknown; error: string | null; nodeCount: number | null; edgeCount: number | null;
  startedAt: Tarih; completedAt: Tarih | null;
}
export interface DenetimSatiri {
  id: number; userId: number; action: string; entityType: string; entityId: string | null;
  details: string | null; ipAddress: string | null; userAgent: string | null; createdAt: Tarih;
}
export interface VeriSetiSatiri {
  id: number; userId: number; name: string; filename: string; storageKey: string | null; columns: string[];
  rowCount: number; sizeBytes: number | null; status: "uploading" | "ready" | "processing" | "error";
  createdAt: Tarih; updatedAt: Tarih;
}
export interface GeriBildirimSatiri {
  id: number; userId: number; kind: "suggestion" | "node_result" | "general"; nodeType: string | null;
  workflowId: number | null; rating: "up" | "down" | null; comment: string | null; createdAt: Tarih;
}

type Ayar = Record<string, unknown>;
interface Prosedur<G, C> {
  useQuery(girdi?: G, ayar?: Ayar): UseQueryResult<C, RpcHatasi>;
  useMutation(ayar?: Ayar): UseMutationResult<C, RpcHatasi, G>;
}
type Bos = undefined | void;
interface Yonlendirici {
  auth: { me: Prosedur<Bos, Kullanici | null>; logout: Prosedur<Bos, { success: boolean }> };
  workflow: {
    list: Prosedur<{ status?: string; search?: string; limit?: number; offset?: number } | undefined, { items: AkisSatiri[]; total: number }>;
    getById: Prosedur<{ id: number }, AkisSatiri>;
    create: Prosedur<Record<string, unknown>, { id: number } & Record<string, unknown>>;
    update: Prosedur<{ id: number } & Record<string, unknown>, { id: number } & Record<string, unknown>>;
    delete: Prosedur<{ id: number }, { success: boolean }>;
    execute: Prosedur<{ workflowId: number; nodeCount?: number; edgeCount?: number }, { executionId: number }>;
    completeExecution: Prosedur<{ executionId: number; status: string; results?: Record<string, unknown>; error?: string }, { success: boolean }>;
    executions: Prosedur<{ workflowId: number; limit?: number; offset?: number }, { items: KosuSatiri[] }>;
  };
  audit: {
    list: Prosedur<{ action?: string; entityType?: string; limit?: number; offset?: number } | undefined, { items: DenetimSatiri[]; total: number }>;
    log: Prosedur<{ action: string; entityType: string; entityId?: string; details?: string }, { id: number }>;
  };
  dataset: {
    list: Prosedur<{ limit?: number; offset?: number } | undefined, { items: VeriSetiSatiri[] }>;
    create: Prosedur<{ name: string; filename: string; columns?: string[]; rowCount: number; sizeBytes?: number }, { id: number }>;
    getById: Prosedur<{ id: number }, VeriSetiSatiri>;
    delete: Prosedur<{ id: number }, { success: boolean }>;
  };
  catalog: {
    list: Prosedur<{ limit?: number; offset?: number } | undefined, { items: AkisSatiri[] }>;
    clone: Prosedur<{ id: number }, { id: number }>;
    promote: Prosedur<{ id: number; curatorNote?: string }, { success: boolean }>;
    retract: Prosedur<{ id: number }, { success: boolean }>;
  };
  feedback: {
    create: Prosedur<{ kind: string; nodeType?: string; workflowId?: number; rating?: "up" | "down"; comment?: string }, { id: number }>;
    list: Prosedur<{ kind?: string; limit?: number; offset?: number } | undefined, { items: GeriBildirimSatiri[] }>;
    summary: Prosedur<Bos, { items: { nodeType: string; up: number; down: number }[] }>;
  };
}
type Gecersizlestir<T> = { invalidate(): Promise<void> } & { [K in keyof T]: Gecersizlestir<T[K]> };
type Arac = Yonlendirici & { useUtils(): Gecersizlestir<Yonlendirici> };

function prosedur(yol: string) {
  return {
    useQuery: (girdi?: unknown, ayar?: Ayar) =>
      useQuery({ queryKey: [yol, girdi ?? null], queryFn: () => rpc(yol, girdi), ...(ayar ?? {}) }),
    useMutation: (ayar?: Ayar) => useMutation({ mutationFn: (girdi: unknown) => rpc(yol, girdi), ...(ayar ?? {}) }),
  };
}

/** trpc.<grup>.<prosedür> — her erişimde yolu biriktiren vekil. */
function vekil(yol: string[]): unknown {
  return new Proxy(() => undefined, {
    get(_hedef, ad: string) {
      if (yol.length === 0 && ad === "useUtils") return useUtils;
      if (ad === "useQuery" || ad === "useMutation") return prosedur(yol.join("."))[ad];
      return vekil([...yol, ad]);
    },
  });
}

function useUtils(): unknown {
  const qc = useQueryClient();
  const utilsVekili = (yol: string[]): unknown =>
    new Proxy(() => undefined, {
      get(_hedef, ad: string) {
        if (ad === "invalidate") {
          return () => qc.invalidateQueries(yol.length ? { queryKey: [yol.join(".")] } : undefined);
        }
        return utilsVekili([...yol, ad]);
      },
    });
  return utilsVekili([]);
}

export const trpc = vekil([]) as Arac;

const queryClient = new QueryClient();

export function TRPCProvider({ children }: { children: ReactNode }) {
  return <QueryClientProvider client={queryClient}>{children}</QueryClientProvider>;
}
