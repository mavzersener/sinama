import { useCallback } from "react";
import type { Node, Edge } from "@xyflow/react";
import { trpc } from "@/providers/trpc";
import { useStore, type NodeData } from "@/store/useStore";
import { kaliciDugumler, yuklenenAkis } from "@/lib/kalicilik";

/**
 * P0 Integration: connects the visual editor to the tRPC workflow API
 * (workflow.list / create / update / delete). Replaces localStorage-only
 * persistence with server-backed, per-user storage.
 *
 * The editor remains fully usable offline; these helpers are only active
 * for authenticated users (the queries are gated by `enabled`).
 */

export interface CloudWorkflow {
  id: number;
  name: string;
  description: string | null;
  nodes: Node<NodeData>[];
  edges: Edge[];
  status: "draft" | "published" | "archived";
  updatedAt: string | Date;
}

export function useWorkflowSync(enabled: boolean) {
  const utils = trpc.useUtils();
  const setNodes = useStore((s) => s.setNodes);
  const setEdges = useStore((s) => s.setEdges);
  const pushHistory = useStore((s) => s.pushHistory);

  const listQuery = trpc.workflow.list.useQuery(
    { status: "all", limit: 50, offset: 0 },
    { enabled, staleTime: 1000 * 30, retry: false },
  );

  const createMutation = trpc.workflow.create.useMutation({
    onSuccess: () => utils.workflow.list.invalidate(),
  });
  const updateMutation = trpc.workflow.update.useMutation({
    onSuccess: () => utils.workflow.list.invalidate(),
  });
  const deleteMutation = trpc.workflow.delete.useMutation({
    onSuccess: () => utils.workflow.list.invalidate(),
  });

  /** Persist the current canvas. Creates a new workflow or updates an existing one. */
  const save = useCallback(
    async (params: { id?: number; name: string; description?: string }) => {
      const state = useStore.getState();
      // Sonuç ve CSV satırı buluta yazılmaz (lib/kalicilik).
      const nodes = kaliciDugumler(state.nodes) as unknown as Record<string, unknown>[];
      const edges = state.edges as unknown as Record<string, unknown>[];

      if (params.id !== undefined) {
        await updateMutation.mutateAsync({
          id: params.id,
          name: params.name,
          description: params.description,
          nodes,
          edges,
        });
        return params.id;
      }
      const created = await createMutation.mutateAsync({
        name: params.name,
        description: params.description,
        nodes,
        edges,
      });
      return created.id;
    },
    [createMutation, updateMutation],
  );

  /** Load a workflow returned by the list query into the canvas. */
  const load = useCallback(
    (workflow: { id: number; nodes: unknown; edges: unknown }) => {
      // JSON columns come back parsed on MySQL 8 but as strings on some
      // drivers/engines (e.g. MariaDB) — normalize defensively.
      const asArray = <T,>(v: unknown): T[] => {
        const parsed = typeof v === 'string' ? JSON.parse(v) : v;
        return Array.isArray(parsed) ? (parsed as T[]) : [];
      };
      const akis = yuklenenAkis(asArray<unknown>(workflow.nodes), asArray<unknown>(workflow.edges));
      setNodes(akis.nodes);
      setEdges(akis.edges);
      pushHistory();
      return workflow.id;
    },
    [setNodes, setEdges, pushHistory],
  );

  const remove = useCallback(
    (id: number) => deleteMutation.mutateAsync({ id }),
    [deleteMutation],
  );

  return {
    workflows: listQuery.data?.items ?? [],
    isLoading: listQuery.isLoading,
    isError: listQuery.isError,
    isSaving: createMutation.isPending || updateMutation.isPending,
    save,
    load,
    remove,
    refetch: listQuery.refetch,
  };
}
