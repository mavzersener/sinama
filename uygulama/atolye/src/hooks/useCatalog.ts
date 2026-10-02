import { useCallback } from "react";
import { trpc } from "@/providers/trpc";
import { useStore } from "@/store/useStore";
import { yuklenenAkis } from "@/lib/kalicilik";

/**
 * P4 Faz A: admin-curated "best practice" catalog. Any authenticated user can
 * browse + clone an entry into their own workspace; only admins can
 * promote/retract. See GELISTIRME_PLANI_OGRENEN_SISTEM.md.
 */
export function useCatalog(enabled: boolean) {
  const utils = trpc.useUtils();
  const setNodes = useStore((s) => s.setNodes);
  const setEdges = useStore((s) => s.setEdges);
  const pushHistory = useStore((s) => s.pushHistory);

  const listQuery = trpc.catalog.list.useQuery(
    { limit: 50, offset: 0 },
    { enabled, staleTime: 1000 * 30, retry: false },
  );

  const cloneMutation = trpc.catalog.clone.useMutation({
    onSuccess: () => utils.workflow.list.invalidate(),
  });
  const promoteMutation = trpc.catalog.promote.useMutation({
    onSuccess: () => utils.catalog.list.invalidate(),
  });
  const retractMutation = trpc.catalog.retract.useMutation({
    onSuccess: () => utils.catalog.list.invalidate(),
  });

  /** Load a catalog entry onto the canvas AND persist a clone under the caller. */
  const useAsTemplate = useCallback(
    async (entry: { id: number; nodes: unknown; edges: unknown }) => {
      const asArray = <T,>(v: unknown): T[] => {
        const parsed = typeof v === "string" ? JSON.parse(v) : v;
        return Array.isArray(parsed) ? (parsed as T[]) : [];
      };
      const akis = yuklenenAkis(asArray<unknown>(entry.nodes), asArray<unknown>(entry.edges));
      setNodes(akis.nodes);
      setEdges(akis.edges);
      pushHistory();
      await cloneMutation.mutateAsync({ id: entry.id });
    },
    [setNodes, setEdges, pushHistory, cloneMutation],
  );

  return {
    entries: listQuery.data?.items ?? [],
    isLoading: listQuery.isLoading,
    isError: listQuery.isError,
    useAsTemplate,
    promote: (id: number, curatorNote?: string) => promoteMutation.mutateAsync({ id, curatorNote }),
    retract: (id: number) => retractMutation.mutateAsync({ id }),
    isPromoting: promoteMutation.isPending,
  };
}
