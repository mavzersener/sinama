// suc_analizi araç düğümleri (ml-service /api/ml/suc/* köprüsü).
// (executionEngine.ts'den bölündü — Faz 4.)

import { sucDiziAlanlari } from '../../nodes/sucAnaliziNodes.generated';
import { makeResult, makeError, type ExecutionResult } from '../sonuc';
import { SUNUCU_SATIR_SINIRI, sunucuUyarilari } from './ml';

export async function execSucAnalizi(
  nodeId: string,
  nodeType: string,
  config: Record<string, unknown>,
  inputData: Record<string, unknown> | null,
  sinyal?: AbortSignal,
): Promise<ExecutionResult> {
  const tumSatirlar = (inputData?.rows as Record<string, unknown>[] | undefined) ?? [];
  const rows = tumSatirlar.slice(0, SUNUCU_SATIR_SINIRI);
  if (rows.length === 0) {
    return makeError(nodeId, nodeType, 'Suç analizi node\'una satır içeren bir veri kaynağı bağlayın.');
  }
  const arac = nodeType.slice('suc_'.length);
  const arg: Record<string, unknown> = { satirlar: rows };
  const diziAlanlar = new Set(sucDiziAlanlari[nodeType] ?? []);
  for (const [k, v] of Object.entries(config)) {
    if (v === '' || v === undefined || v === null) continue;
    // array tipli alanlar PropertyPanel'de metin: "a, b" -> ["a","b"]
    arg[k] = diziAlanlar.has(k) && typeof v === 'string'
      ? v.split(',').map((s) => s.trim()).filter(Boolean)
      : v;
  }
  try {
    const resp = await fetch(`/api/ml/suc/${arac}`, {
      method: 'POST',
      signal: sinyal,
      credentials: 'include',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(arg),
    });
    if (resp.status === 401) {
      return makeError(nodeId, nodeType, 'Sunucu taraflı suç analizi için oturum açın.');
    }
    const paket = (await resp.json().catch(() => ({}))) as Record<string, unknown>;
    if (!resp.ok) {
      const mesaj = (paket.mesaj as string) ?? `suç analizi servisi hatası (${resp.status})`;
      return makeError(nodeId, nodeType, mesaj);
    }
    // Kesme DataFlow'da olur; suc_analizi'nin meta.kesildi'si bunu göremez
    // (kendi 200k sınırını görür) — burada düzeltilir ve görünür yapılır.
    const kesme = sunucuUyarilari(tumSatirlar.length, rows.length);
    const meta = (paket.meta ?? {}) as Record<string, unknown>;
    if (kesme.length) {
      paket.meta = { ...meta, kesildi: true, uyarilar: [...((meta.uyarilar as string[]) ?? []), ...kesme] };
    }
    const sunucuUyari = ((paket.meta as Record<string, unknown> | undefined)?.uyarilar as string[] | undefined) ?? [];
    return makeResult(nodeId, nodeType, { ...paket, uyarilar: sunucuUyari }, rows.length);
  } catch {
    return makeError(nodeId, nodeType, 'Suç analizi servisine ulaşılamadı (ml-service 8001 çalışıyor mu?).');
  }
}
