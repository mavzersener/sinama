// Yürütme sonucu tipi ve düğümler arası veri akışı yardımcıları (akış kanalı, satır/sütun çıkarma, sonuç/hata kurucuları).
// (executionEngine.ts'den bölündü — Faz 4.)

import type { Edge } from '@xyflow/react';
import { sayisalSutunlar } from './istatistik';

export interface ExecutionResult {
  status: 'success' | 'error';
  nodeId: string;
  nodeType: string;
  timestamp: string;
  data: Record<string, unknown>;
  error?: string;
  rowCount?: number;
  preview?: Record<string, unknown>[];
  columns?: string[];
  /**
   * Akış kanalı: özet üreten düğümün (istatistik, korelasyon, veri kalitesi…)
   * ardındakilere AYNEN geçirdiği girdi tablosu. Bkz. akisVerisi().
   */
  akis?: { rows: Record<string, unknown>[]; columns: string[] };
  /**
   * Sentetik (demo) veriden türedi: düğüm demo kaynak ya da girdilerinden biri
   * demo. Eskiden işaret yalnız kaynağın kendi sonucundaydı; demo veri
   * üzerindeki istatistik/kümeleme sonucu gerçek bulgu gibi görünüyordu.
   */
  demo?: true;
}

/** Sonuç sentetik (demo) veriden mi türedi? */
export function demoMu(r: ExecutionResult | null | undefined): boolean {
  return !!r && (r.demo === true || (r.data as Record<string, unknown> | undefined)?._demoMode === true);
}

/**
 * Bir sonucun ardındaki düğümlere akan tablo.
 *
 * Kaynak ve dönüştürücü düğümler kendi satırlarını üretir (`data.rows`).
 * Özet üreten analiz düğümleri satır üretmez; ardındaki düğümler onların
 * GİRDİ tablosunu aynen alır (`akis`). Eskiden özet düğümünden sonra gelen
 * her düğüm boş veri görüyordu (demo: Veri Kalitesi → Anomali "No numeric
 * columns"; Hedeften Akış'ın zincirleri ikinci adımda kuruyordu) ve Veri
 * Kalitesi `data.columns`a profil NESNELERİ koyduğu için sütun adı bekleyen
 * her şey bozuluyordu. Özetin kendisi `data`da kalır: sonuç paneli ve ajan
 * (yorum için özeti okur) değişmez. Python dışa aktarımı aynı kuralı izler.
 */
export function akisVerisi(r: ExecutionResult | null | undefined): Record<string, unknown> | null {
  if (!r) return null;
  if (Array.isArray(r.data?.rows)) return r.data;
  return r.akis ?? r.data ?? null;
}

// ============================================================
// DATA FLOW
// ============================================================

export function getUpstreamResult(nodeId: string, edges: Edge[], allResults: Map<string, ExecutionResult>): ExecutionResult | null {
  const incoming = edges.filter((e) => e.target === nodeId);
  if (incoming.length === 0) return null;
  return allResults.get(incoming[0].source) || null;
}

export function extractRows(data: Record<string, unknown> | null): Record<string, unknown>[] {
  if (!data) return [];
  return (data.rows as Record<string, unknown>[]) || [];
}

export function extractColumns(data: Record<string, unknown> | null): string[] {
  if (!data) return [];
  return (data.columns as string[]) || (extractRows(data).length > 0 ? Object.keys(extractRows(data)[0]) : []);
}

/**
 * PropertyPanel'de "column"/"multiselect" alanları CSV metin ("a, b") olarak
 * tutulur, ama bazı node'ların defaultConfig'i (ve eski kaydedilmiş
 * workflow'lar) aynı alanı dizi olarak taşır. `.split()` yalnız string'de
 * vardır — dizi verilirse TypeError atar; ikisini de kabul et.
 */
export function csvAlan(v: unknown): string[] {
  if (Array.isArray(v)) return v.map((x) => String(x).trim()).filter(Boolean);
  return String(v ?? '').split(',').map((s) => s.trim()).filter(Boolean);
}

// ============================================================
// SAYISAL YARDIMCILAR
// ============================================================
// Hesapların kendisi saf modülde (./istatistik): tek sayı çözücü, tam kayıt
// seçimi, korelasyon, OLS, K-Means, silhouette. Eski yerel kopyalar
// Number(null)===0 ve x/y'yi ayrı süzme hatalarını taşıyordu.

/** Yürütücü uyarıları: sonuç kartında görünür (sessiz dışlama/sadeleştirme yok). */
export function dislamaUyarisi(dislanan: number, toplam: number, neden: string): string | null {
  if (dislanan <= 0) return null;
  const oran = toplam > 0 ? ((dislanan / toplam) * 100).toFixed(1) : '0';
  return `${dislanan} / ${toplam} satır (%${oran}) ${neden} için dışlandı.`;
}

/** Sayısal sütun seçimi: kullanıcı verdiyse onlar (sayısal olmayanlar uyarıyla ayıklanır), yoksa tümü. */
export function sayisalSecim(
  satirlar: Record<string, unknown>[], secili: string[], tumSutunlar: string[], uyarilar: string[],
): string[] {
  if (secili.length === 0) return sayisalSutunlar(satirlar, tumSutunlar);
  const sayisal = new Set(sayisalSutunlar(satirlar, secili));
  const disari = secili.filter((c) => !sayisal.has(c));
  if (disari.length) {
    uyarilar.push(`Sayısal olmayan ya da bulunamayan sütunlar analiz dışı: ${disari.join(', ')}.`);
  }
  return secili.filter((c) => sayisal.has(c));
}

export const yuvarla = (v: number | null, basamak = 4) => (v === null ? null : Number(v.toFixed(basamak)));

export function makeResult(nodeId: string, nodeType: string, data: Record<string, unknown>, rowCount?: number, columns?: string[], preview?: Record<string, unknown>[]): ExecutionResult {
  return { status: 'success', nodeId, nodeType, timestamp: new Date().toISOString(), data, rowCount, columns, preview };
}

export function makeError(nodeId: string, nodeType: string, error: string): ExecutionResult {
  return { status: 'error', nodeId, nodeType, timestamp: new Date().toISOString(), data: {}, error, rowCount: 0 };
}
