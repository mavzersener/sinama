// Agent Insight düğümü: yerel ajan servisine (/api/agent/*) yorum isteği.
// (executionEngine.ts'den bölündü — Faz 4.)

import type { Edge } from '@xyflow/react';
import { demoMu, makeResult, makeError, type ExecutionResult } from '../sonuc';

const DEMO_NOTU = 'SENTETİK DEMO VERİSİ: rastgele üretildi, gerçek kayıt değildir. Bundan bulgu, örüntü ya da öneri çıkarma; yalnız yöntemi açıkla.';

// ---- Agent Nodes (call the local YerelAjan service via /api/agent/*) ----

/**
 * YerelAjan bağlamı `json.dumps(inputs, ensure_ascii=False)[:6000]` ile KESER
 * (gui/server.py) — JSON'un ortasından. Sığmayan bağlamda sondaki alanlar
 * (uyarılar, demo notu) modele hiç ulaşmıyordu. Burada bağlam o bütçeye
 * sığdırılır ve öncelikli alanlar her girdinin BAŞINA konur.
 */
export const AJAN_BAGLAM_BUTCESI = 6000;
const ONCELIKLI = ['veri_notu', 'uyarilar'];
const SATIR_KADEMELERI = [20, 10, 5, 2, 0];

/**
 * Python `json.dumps(x, ensure_ascii=False)` çıktısının uzunluğu: varsayılan
 * ayraçlar ", " ve ": " (JS JSON.stringify'dan her ayraçta 1 fazla).
 */
export function pyJsonUzunlugu(v: unknown): number {
  if (v === undefined) return 0;
  if (v === null || typeof v !== 'object') return JSON.stringify(v)?.length ?? 4;
  if (Array.isArray(v)) {
    return 2 + v.reduce((t: number, x) => t + pyJsonUzunlugu(x === undefined ? null : x), 0) + Math.max(0, v.length - 1) * 2;
  }
  const girdiler = Object.entries(v as Record<string, unknown>).filter(([, x]) => x !== undefined);
  return 2 + girdiler.reduce((t, [k, x]) => t + JSON.stringify(k).length + 2 + pyJsonUzunlugu(x), 0) + Math.max(0, girdiler.length - 1) * 2;
}

/** Öncelikli alanlar başta; diziler en çok `satir` öğe; uzun metinler `metin` karakter. */
function kirp(data: Record<string, unknown> | null, satir: number, metin: number): Record<string, unknown> | null {
  if (!data) return null;
  const sirali = [...ONCELIKLI.filter((k) => k in data), ...Object.keys(data).filter((k) => !ONCELIKLI.includes(k))];
  const out: Record<string, unknown> = {};
  for (const k of sirali) {
    let v = data[k];
    if (Array.isArray(v) && !ONCELIKLI.includes(k)) v = v.slice(0, satir);
    if (typeof v === 'string' && v.length > metin && !ONCELIKLI.includes(k)) v = `${v.slice(0, metin)}…`;
    out[k] = v;
  }
  return out;
}

/** Bağlamı bütçeye sığana kadar kademeli kırpar; kırpıldıysa bunu söyler. */
export function baglamiSigdir<T extends { data: Record<string, unknown> | null }>(inputs: T[]): { inputs: T[]; kirpildi: boolean } {
  for (const metin of [Infinity, 500, 200]) {
    for (const satir of SATIR_KADEMELERI) {
      const aday = inputs.map((i) => ({ ...i, data: kirp(i.data, satir, metin) }));
      if (pyJsonUzunlugu(aday) <= AJAN_BAGLAM_BUTCESI) return { inputs: aday, kirpildi: satir < 20 || metin !== Infinity };
    }
  }
  // Yine sığmadı (çok sayıda girdi/alan): öncelikli alanlar en azından başta.
  return { inputs: inputs.map((i) => ({ ...i, data: kirp(i.data, 0, 200) })), kirpildi: true };
}

/**
 * Agent Insight: gathers the results of ALL connected upstream nodes and asks
 * the local agent to interpret them together in natural language. Degrades
 * gracefully when the agent is unavailable.
 */
export async function execAgentInsight(
  nodeId: string,
  config: Record<string, unknown>,
  edges: Edge[],
  allResults: Map<string, ExecutionResult>,
  sinyal?: AbortSignal,
): Promise<ExecutionResult> {
  const question = (config.question as string) || 'Summarize the key findings in this data.';
  const tone = (config.tone as string) || 'concise';
  const language = (config.language as string) || 'English';

  // Collect every connected upstream node's result as a labelled input.
  const inputs = edges
    .filter((e) => e.target === nodeId)
    .map((e) => allResults.get(e.source))
    .filter((r): r is ExecutionResult => !!r)
    .map((r) => ({
      nodeType: r.nodeType,
      rowCount: r.rowCount,
      // Vekil şeması inputs nesnesindeki bilinmeyen alanı SESSİZCE atar; not
      // bu yüzden serbest `data` alanında taşınır.
      data: demoMu(r) ? { ...r.data, veri_notu: DEMO_NOTU } : r.data,
    }));
  const { inputs: sigan, kirpildi } = baglamiSigdir(inputs);

  const demoVar = edges.some((e) => e.target === nodeId && demoMu(allResults.get(e.source)));

  // Nothing connected/produced → don't waste an LLM call; guide the user.
  if (inputs.length === 0) {
    return makeError(nodeId, 'agent_insight', 'Connect one or more analysis nodes to Agent Insight, then run.');
  }

  try {
    const resp = await fetch('/api/agent/insight', {
      method: 'POST',
      signal: sinyal,
      credentials: 'include',
      headers: { 'content-type': 'application/json' },
      // Demo girdide not sorunun başında da: model bağlamdaki alanı atlasa bile görsün.
      body: JSON.stringify({ question: demoVar ? `[${DEMO_NOTU}] ${question}`.slice(0, 4000) : question, tone, language, context: { inputs: sigan } }),
    });

    if (resp.status === 401) {
      return makeError(nodeId, 'agent_insight', 'Sign in to use the agent (cloud feature).');
    }
    if (!resp.ok) {
      const detail = (await resp.json().catch(() => ({}))) as { error?: string };
      return makeError(nodeId, 'agent_insight', detail.error || `Agent error (${resp.status})`);
    }

    const out = (await resp.json()) as { insight?: string; model?: string };
    return makeResult(
      nodeId,
      'agent_insight',
      {
        insight: out.insight ?? '', model: out.model ?? 'agent', question,
        ...(kirpildi ? { uyarilar: [`Ajana giden bağlam ${AJAN_BAGLAM_BUTCESI} karakter sınırına sığdırmak için kısaltıldı (satır örnekleri azaltıldı); uyarılar ve özetler korundu.`] } : {}),
      },
    );
  } catch (err) {
    return makeError(nodeId, 'agent_insight', err instanceof Error ? err.message : 'Agent request failed');
  }
}
