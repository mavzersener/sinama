// Kanıt paketi düğümü: RFC 8785 + SHA-256 paket, sunucu kanıt defteri kaydı ve HARP dış çapası.
// (executionEngine.ts'den bölündü — Faz 4.)

import type { Edge } from '@xyflow/react';
import { KANIT_SEMASI, kanonikHash, type KanitVerisi, type KanitKayitIstegi, type KanitMakbuzu, type HarpIletimi } from '@contracts/kanit';
import { extractRows, extractColumns, makeResult, makeError, type ExecutionResult } from '../sonuc';

/**
 * Kanıt paketi (dataflow.kanit/1).
 *
 * Eskiden: "SHA-256-simulated" etiketli 32-bit dize hash'i, yalnız ilk 5
 * satır; sabit KVKK sınıfı ve hukuki dayanak; "pdf" seçeneği JSON üretiyordu;
 * rastgele DEMO veriden "court-admissible" paket çıkabiliyordu.
 *
 * Şimdi: verinin TAMAMI üzerinde RFC 8785 kanonik JSON + gerçek SHA-256;
 * yukarı akışta demo veri varsa paket ÜRETİLMEZ; KVKK sınıfı/hukuki dayanak
 * kaynak düğümlerden toplanır (yoksa "belirtilmedi"); paket sunucunun kanıt
 * defterine kaydedilip Ed25519 imzalı makbuz alınır. Oturum yoksa paket
 * KAYITSIZ işaretlenir — resmî delil niteliği taşımaz ve bunu söyler.
 * Hukuki uygunluk iddiası YOKTUR; bu teknik bir bütünlük kanıtıdır.
 */
export async function execEvidenceExport(
  nodeId: string, config: Record<string, unknown>, inputData: Record<string, unknown> | null,
  edges: Edge[], allResults: Map<string, ExecutionResult>,
): Promise<ExecutionResult> {
  const rows = extractRows(inputData);
  const columns = extractColumns(inputData);
  const dosyaNo = String(config.caseNumber ?? '').trim();
  const beyanEden = String(config.officerId ?? '').trim();
  if (!dosyaNo) return makeError(nodeId, 'evidence_export', 'Dosya/Esas No gerekli');
  if (rows.length === 0) return makeError(nodeId, 'evidence_export', 'Kanıt paketi için satır yok');

  // Yukarı akış kapanışı: kaynak zinciri + demo denetimi.
  const zincir: string[] = [];
  const gorulen = new Set<string>([nodeId]);
  const kuyruk = [nodeId];
  while (kuyruk.length) {
    const hedef = kuyruk.shift()!;
    for (const e of edges.filter((x) => x.target === hedef)) {
      if (gorulen.has(e.source)) continue;
      gorulen.add(e.source);
      zincir.push(e.source);
      kuyruk.push(e.source);
    }
  }
  const ustSonuclar = zincir.map((id) => allResults.get(id)).filter((r): r is ExecutionResult => !!r);
  const demo = ustSonuclar.filter((r) => (r.data as Record<string, unknown> | undefined)?._demoMode === true);
  if (demo.length) {
    return makeError(nodeId, 'evidence_export',
      `Kanıt paketi demo/sentetik veriden üretilemez (${demo.map((r) => r.nodeType).join(', ')}). ` +
      'Gerçek veri yükleyin ya da kaynağı bağlayın.');
  }
  const topla = (alan: string) => [...new Set(ustSonuclar
    .map((r) => (r.data as Record<string, unknown> | undefined)?.[alan])
    .filter((v): v is string => typeof v === 'string' && v.trim() !== ''))];
  const kvkk = topla('kvkkClass');
  const dayanak = topla('legalBasis');

  const uyarilar: string[] = [];
  if (config.format && config.format !== 'json') {
    uyarilar.push(`"${String(config.format)}" biçimi üretilmiyor; paket JSON olarak hazırlandı.`);
  }
  if (!beyanEden) uyarilar.push('Beyan eden sicil no boş; kayıt yalnız oturumdaki kullanıcıya bağlanır.');
  if (!kvkk.length) uyarilar.push('Kaynaklarda KVKK sınıfı belirtilmemiş.');
  if (!dayanak.length) uyarilar.push('Kaynaklarda hukuki dayanak belirtilmemiş.');

  const kanitId = globalThis.crypto.randomUUID();
  const veri: KanitVerisi = { columns, rows };
  let veriSha: string;
  try {
    veriSha = await kanonikHash(veri);
  } catch (e) {
    return makeError(nodeId, 'evidence_export', `Veri kanonik biçime çevrilemedi: ${(e as Error).message}`);
  }
  const paket = {
    sema: KANIT_SEMASI,
    kanit_id: kanitId,
    dosya_no: dosyaNo,
    beyan_eden: beyanEden,
    olusturma_zamani_istemci: new Date().toISOString(),
    kaynak_zinciri: ustSonuclar.map((r) => ({ tip: r.nodeType, etiket: r.nodeId })),
    kvkk_siniflari: kvkk,
    hukuki_dayanaklar: dayanak,
    veri_sha256: veriSha,
    veri,
    // KOPYA: aşağıda eklenen kayıt uyarıları hash'lenmiş paketi değiştirmemeli
    // (referans olsaydı indirilen paket, hash'lenen paketten farklı olurdu).
    uyarilar: [...uyarilar],
  };
  const paketSha = await kanonikHash(paket);
  const kayitUyarilari: string[] = [];

  // Sunucu kaydı: veri DEĞİL, yalnız hash'ler ve özet gider.
  let makbuz: KanitMakbuzu | null = null;
  let harp: HarpIletimi | null = null;
  const istek: KanitKayitIstegi = {
    kanit_id: kanitId, dosya_no: dosyaNo, veri_sha256: veriSha, paket_sha256: paketSha,
    satir: rows.length, sutun: columns.length, beyan_eden: beyanEden, kaynak_zinciri: paket.kaynak_zinciri,
  };
  try {
    const resp = await fetch('/api/evidence/record', {
      method: 'POST', credentials: 'include',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(istek),
    });
    if (resp.ok) {
      // `harp` sunucunun dış çapa iletim durumudur; makbuzun (imzalı kaydın) parçası DEĞİL.
      const { harp: h, ...m } = (await resp.json()) as KanitMakbuzu & { harp?: HarpIletimi };
      makbuz = m;
      harp = h ?? null;
    } else if (resp.status === 401) {
      kayitUyarilari.push('Oturum yok: paket kanıt defterine KAYDEDİLMEDİ — resmî delil niteliği taşımaz.');
    } else {
      const d = (await resp.json().catch(() => ({}))) as { error?: string };
      kayitUyarilari.push(`Kanıt defterine kaydedilemedi (${resp.status}${d.error ? `: ${d.error}` : ''}) — paket KAYITSIZ.`);
    }
  } catch {
    kayitUyarilari.push('Kanıt defterine ulaşılamadı — paket KAYITSIZ.');
  }
  if (makbuz && (makbuz.kayit.paket_sha256 !== paketSha || makbuz.kayit.veri_sha256 !== veriSha)) {
    return makeError(nodeId, 'evidence_export', 'Sunucu makbuzu paketle eşleşmiyor; paket üretilmedi.');
  }

  if (makbuz && harp?.durum === 'reddedildi') {
    kayitUyarilari.push(`HARP dış çapası kaydı REDDETTİ (${harp.kod}): ${harp.mesaj} — yerel defter HARP'ın gördüğü zincirle çelişiyor; yöneticiye bildirin.`);
  } else if (makbuz && harp?.durum === 'iletilemedi') {
    kayitUyarilari.push(`Kayıt HARP'a iletilemedi (${harp.neden}). Yerel kayıt geçerli; dış çapa yönetici eşitlemesiyle tamamlanmalı.`);
  }

  const durum = makbuz ? 'KAYITLI' : 'KAYITSIZ';
  const dosyaAdi = `kanit_${dosyaNo.replace(/[^\p{L}\p{N}_-]+/gu, '_')}_${kanitId.slice(0, 8)}${makbuz ? '' : '_KAYITSIZ'}.json`;
  const icerik = JSON.stringify({
    paket,
    paket_sha256: paketSha,
    makbuz,
    // Hash'in DIŞINDA: kaydın kendisine dair durum (paketin içeriği değil).
    kayit_durumu: durum,
    kayit_uyarilari: kayitUyarilari,
    // Dış çapa: HARP'ın kabul makbuzu (WORM mührü) ya da neden iletilemediği.
    harp_capasi: harp,
    dogrulama: 'python scripts/kanit_dogrula.py <bu dosya> --genel-anahtar <kanit/imza_anahtari.pub.pem>',
  }, null, 2);
  if (typeof document !== 'undefined') {
    const url = URL.createObjectURL(new Blob([icerik], { type: 'application/json' }));
    const a = document.createElement('a');
    a.href = url;
    a.download = dosyaAdi;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  return makeResult(nodeId, 'evidence_export', {
    durum,
    kanit_id: kanitId,
    dosya_no: dosyaNo,
    beyan_eden: beyanEden,
    veri_sha256: veriSha,
    paket_sha256: paketSha,
    satir: rows.length,
    sutun: columns.length,
    kvkk_siniflari: kvkk,
    hukuki_dayanaklar: dayanak,
    defter_sira: makbuz?.kayit.sira ?? null,
    sunucu_zamani: makbuz?.kayit.sunucu_zamani ?? null,
    aktor: makbuz?.kayit.aktor ?? null,
    anahtar_parmak_izi: makbuz?.anahtar_parmak_izi ?? null,
    harp_durumu: harp?.durum ?? null,
    harp_kayit_id: harp?.durum === 'iletildi' ? harp.makbuz.harp_kayit_id : null,
    dosya_adi: dosyaAdi,
    uyarilar: [...uyarilar, ...kayitUyarilari],
  }, rows.length);
}
