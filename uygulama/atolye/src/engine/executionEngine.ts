// ============================================================
// DataFlow Execution Engine v2 - Real Math, Real CSV, Real Export
// ============================================================
// Demo Mode: Source nodes use generated sample data when no real
// file is uploaded. All processing/analysis nodes use real
// mathematical algorithms on the actual data flowing through.
// ============================================================

import type { Node, Edge } from '@xyflow/react';
import type { NodeData } from '../store/useStore';
import { akisVerisi, demoMu, getUpstreamResult, extractColumns, makeResult, makeError, type ExecutionResult } from './sonuc';
import { veriOnKontrolu } from './dogrulama';
import { execAgentInsight } from './dugumler/ajan';
import { ML_DUGUMLERI, execMl } from './dugumler/ml';
import { execCsvSource, execDbSource, execApiSource, execPtsSource, execAnprSource, execMobeseSource, execIhbarSource, execAdliSicilSource } from './dugumler/kaynaklar';
import { execFilter, execExtendField, execAggregate, execSort, execJoin, execBlockGroup, execDataClean, execDedup } from './dugumler/donusum';
import { execStatistics, execLinearRegression, execClustering, execAnomalyDetection, execCorrelation, execAssociationRules, execModelValidation, execDataQuality, execCrossValidation } from './dugumler/analiz';
import { execSna, execGeoHotspot, execTemporalPattern, execCooccurrence } from './dugumler/kolluk';
import { execEvidenceExport } from './dugumler/kanit';
import { execChart, execExport, execAlert } from './dugumler/cikti';
import { execSucAnalizi } from './dugumler/suc';

// Genel arayüz: modüllere bölündükten sonra da içe aktaran dosyalar değişmez.
export { akisVerisi, demoMu, type ExecutionResult } from './sonuc';
export { validateWorkflow, getExecutionOrder, demoKaynagiMi, type ValidationError } from './dogrulama';
export { ML_DUGUMLERI, numericRows } from './dugumler/ml';
export { execDataClean } from './dugumler/donusum';
export { getPrebuiltModels } from './hazirModeller';

// ============================================================
// NODE EXECUTORS
// ============================================================

export async function executeNode(
  node: Node<NodeData>, edges: Edge[], allResults: Map<string, ExecutionResult>,
  baglam: { sinyal?: AbortSignal } = {},
): Promise<ExecutionResult> {
  const inputData = akisVerisi(getUpstreamResult(node.id, edges, allResults));
  // Demo işareti bulaşıcıdır: herhangi bir girdisi demo olan düğümün sonucu da demo.
  const girdiDemo = edges.some((e) => e.target === node.id && demoMu(allResults.get(e.source)));
  const sonuc = await dugumuYurut(node, edges, allResults, inputData, { ...baglam, demo: girdiDemo });
  if (sonuc.status === 'success' && (girdiDemo || demoMu(sonuc))) sonuc.demo = true;
  // Özet düğümü satır üretmediyse girdi tablosu ardındakilere aynen geçer.
  // (Başvuru, kopya değil: bellek maliyeti yok.)
  if (sonuc.status === 'success' && !Array.isArray(sonuc.data?.rows) && Array.isArray(inputData?.rows)) {
    sonuc.akis = { rows: inputData.rows as Record<string, unknown>[], columns: extractColumns(inputData) };
  }
  return sonuc;
}

async function dugumuYurut(
  node: Node<NodeData>, edges: Edge[], allResults: Map<string, ExecutionResult>,
  inputData: Record<string, unknown> | null, baglam: { sinyal?: AbortSignal; demo?: boolean },
): Promise<ExecutionResult> {
  const { type, config } = node.data;
  // İptal/zaman aşımı sinyali yalnız ağ düğümlerine gider (ML, suç analizi,
  // ajan). Kanıt kaydına BİLEREK verilmez: bkz. yurutucu.ts.
  const { sinyal, demo = false } = baglam;

  try {
    // ÖN-KONTROL: analizi çalıştırmadan önce verinin sözleşmeye uygunluğunu
    // sına. Amaç, kullanıcıyı ham çökmelerle ya da anlamsız sonuçlarla
    // karşılaştırmamak: kırılacak analiz, kırılmadan önce SEBEBİYLE ve
    // ÇÖZÜMÜYLE bildirilir.
    const onKontrol = veriOnKontrolu(type, config, inputData);
    if (onKontrol) return makeError(node.id, type, onKontrol);

    if (type.startsWith('suc_')) {
      return await execSucAnalizi(node.id, type, config, inputData, sinyal);
    }
    if (type in ML_DUGUMLERI) return await execMl(node.id, type, config, inputData, sinyal);
    switch (type) {
      case 'agent_insight': return await execAgentInsight(node.id, config, edges, allResults, sinyal);
      case 'csv_source': return await execCsvSource(node.id, config, sinyal);
      case 'db_source': return execDbSource(node.id, config);
      case 'api_source': return execApiSource(node.id, config);
      case 'filter': return execFilter(node.id, config, inputData);
      case 'extend_field': return execExtendField(node.id, config, inputData);
      case 'aggregate': return execAggregate(node.id, config, inputData);
      case 'sort': return execSort(node.id, config, inputData);
      case 'join': return execJoin(node.id, config, edges, allResults);
      case 'dedup': return execDedup(node.id, config, inputData);
      case 'data_clean': return execDataClean(node.id, config, inputData);
      case 'block_group': return execBlockGroup(node.id, config, inputData);
      case 'statistics': return execStatistics(node.id, config, inputData);
      case 'linear_regression': return execLinearRegression(node.id, config, inputData);
      case 'association_rules': return execAssociationRules(node.id, config, inputData);
      case 'clustering': return execClustering(node.id, config, inputData);
      case 'anomaly_detection': return execAnomalyDetection(node.id, config, inputData);
      case 'correlation': return execCorrelation(node.id, config, inputData);
      case 'model_validation': return execModelValidation(node.id, config, inputData);
      case 'data_quality': return execDataQuality(node.id, config, inputData);
      case 'cross_validation': return execCrossValidation(node.id, config, inputData);
      case 'pts_source': return execPtsSource(node.id, config);
      case 'anpr_source': return execAnprSource(node.id, config);
      case 'mobese_source': return execMobeseSource(node.id, config);
      case 'ihbar_source': return execIhbarSource(node.id, config);
      case 'adli_sicil_source': return execAdliSicilSource(node.id, config);
      case 'sna': return execSna(node.id, config, inputData);
      case 'geo_hotspot': return execGeoHotspot(node.id, config, inputData);
      case 'temporal_pattern': return execTemporalPattern(node.id, config, inputData);
      case 'cooccurrence': return execCooccurrence(node.id, config, inputData);
      case 'chart': return execChart(node.id, config, inputData, demo);
      case 'export': return execExport(node.id, config, inputData, demo);
      case 'alert': return execAlert(node.id, config, inputData);
      case 'evidence_export': return await execEvidenceExport(node.id, config, inputData, edges, allResults);
      default: return makeResult(node.id, type, { message: 'Unknown node type' }, 0);
    }
  } catch (err) {
    return makeError(node.id, type, err instanceof Error ? err.message : 'Unknown error');
  }
}
