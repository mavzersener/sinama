import { trpc } from "@/providers/trpc";

/**
 * P4 Faz B: explicit user feedback (👍/👎 + optional free-text). Feeds Faz C's
 * agent-assisted recommendation-tuning loop (not yet built — see
 * GELISTIRME_PLANI_OGRENEN_SISTEM.md). Silently no-ops when not signed in
 * (feedback is a cloud feature, like CloudSync).
 */
export function useFeedback() {
  const mutation = trpc.feedback.create.useMutation();

  const send = (input: {
    kind: "suggestion" | "node_result" | "general";
    nodeType?: string;
    workflowId?: number;
    rating?: "up" | "down";
    comment?: string;
  }) => mutation.mutateAsync(input).catch(() => {
    /* best-effort: signed-out or offline users simply can't send feedback */
  });

  return { send, isSending: mutation.isPending };
}
