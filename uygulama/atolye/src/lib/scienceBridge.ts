// Science GPT (akademik makale motoru) istemcisi — Akademik Mod'un erişim katmanı.
//
// Tüm çağrılar DataFlow'un auth-korumalı proxy'sinden geçer (/api/science/*).
// Proxy `actor` alanını DataFlow oturumundan türetip gövdeye zorla yazar —
// bu istemci actor GÖNDERMEZ, gönderse de ezilir (bkz. api/science-proxy.ts).
//
// Motorun sözleşmesi KATI SIRALIDIR: her adım bir öncekinin kimliğine bağlıdır
// ve üç yerinde otomatikleştirilmesi YASAK insan onayı vardır (şema onayı,
// protokol kilidi, kanıt kartları). Bu yüzden Akademik Mod bir node grafı değil
// sihirbazdır; buradaki fonksiyon sırası o sihirbazın adımlarıdır.

// ---- Hata taksonomisi ----
//
// suc_analizi'nin taksonomisinde YENİDEN-DENENEBİLİRLİK alanı yok; motorun
// HTTP kodlarında bu ayrım anlamlı ve korunmalı: LLM/servis erişilemezliği
// yeniden denenebilir, şema doğrulama hatası DEĞİLDİR. Kullanıcıya "tekrar
// dene" düğmesi yalnız ilkinde gösterilir.
export type BilimHataTipi =
  | 'guvenlik'      // 401 — oturum yok
  | 'bulunamadi'    // 404 — kimlik yanlış / kayıt yok
  | 'cakisma'       // 409 — protokol kilitli veya durum çakışması
  | 'cok_buyuk'     // 413 — dosya sınırı aşıldı
  | 'sema'          // 422 — biçim/şema doğrulama
  | 'erisilemez'    // 502/503 — motor veya LLM ayakta değil
  | 'sistem';       // diğer

export class BilimHatasi extends Error {
  tip: BilimHataTipi;
  yenidenDenenebilir: boolean;
  durum: number;
  constructor(tip: BilimHataTipi, mesaj: string, durum: number) {
    super(mesaj);
    this.name = 'BilimHatasi';
    this.tip = tip;
    this.durum = durum;
    // YALNIZ erişilemezlik yeniden denenebilir. 422/409 tekrar denemekle
    // düzelmez — kullanıcı girdiyi düzeltmelidir.
    this.yenidenDenenebilir = tip === 'erisilemez';
  }
}

const DURUM_TIP: Record<number, BilimHataTipi> = {
  401: 'guvenlik',
  404: 'bulunamadi',
  409: 'cakisma',
  413: 'cok_buyuk',
  422: 'sema',
  502: 'erisilemez',
  503: 'erisilemez',
};

const KOK = '/api/science';

async function istek<T>(
  yol: string,
  secenek: { method?: string; govde?: unknown; form?: FormData } = {},
): Promise<T> {
  const method = secenek.method ?? 'GET';
  let resp: Response;
  try {
    resp = await fetch(`${KOK}${yol}`, {
      method,
      credentials: 'include',
      ...(secenek.form
        ? { body: secenek.form }
        : secenek.govde !== undefined
          ? {
              headers: { 'content-type': 'application/json' },
              body: JSON.stringify(secenek.govde),
            }
          : {}),
    });
  } catch {
    // Ağ katmanı koptu. Motor kapalıyken YAKLAŞIK bir çıktı üretmiyoruz —
    // istek başarısız olmalıdır.
    throw new BilimHatasi('erisilemez', 'Science GPT servisine ulaşılamadı (8000 çalışıyor mu?).', 0);
  }

  const govde = (await resp.json().catch(() => ({}))) as Record<string, unknown>;
  if (!resp.ok) {
    const tip = DURUM_TIP[resp.status] ?? 'sistem';
    const mesaj =
      (govde.detail as string) ??
      (govde.error as string) ??
      `Beklenmeyen hata (${resp.status})`;
    throw new BilimHatasi(tip, mesaj, resp.status);
  }
  return govde as unknown as T;
}

// ---- Tipler (motorun yanıt şekillerinden) ----

// Şekiller canlı motordan doğrulandı (8000, 29 Tem) — tahmin değil.
export interface Saglik {
  status: string;
  phase: string; // "P7"
}
export interface LlmDurum {
  available: boolean;
  base_url: string;
  configured_model: string;
  resolved_model: string | null;
  models: string[];
  error: string | null;
}
export interface Yurutucular {
  executor_version: string;
  supported_method_ids: string[];
}
export interface Protokol {
  research_id: string;
  version: number;
  locked: boolean;
}
/**
 * Yükleme yanıtı DÜZ DEĞİLDİR: motor manifest + profil demeti döner.
 * (Uçtan uca koşuda doğrulandı — ilk tahmin `{dataset_id}` idi ve yanlıştı.)
 */
export interface VeriSeti {
  manifest: {
    dataset_id: string;
    research_id: string;
    original_filename: string;
    /** Ham dosyanın özeti. DİKKAT: manifest'te `sha256`, profilde `raw_sha256`. */
    sha256: string;
    size_bytes: number;
    row_count: number;
    column_count: number;
    immutable_raw: boolean;
  };
  profile: {
    dataset_id: string;
    raw_sha256: string;
    row_count: number;
    column_count: number;
    limitations: string[];
  };
}
export interface OneriSonuc {
  recommendation_id: string;
  /** ready | conditional | blocked — 'blocked' ise yürütme DENENMEMELİ. */
  readiness: 'ready' | 'conditional' | 'blocked';
}
export interface OnaySonuc {
  approval_id: string;
}
export interface AnalizSonuc {
  analysis_id: string;
  method_id: string;
  model_name: string;
  warnings: string[];
}
export interface DogrulamaSonuc {
  validation_id: string;
  /** passed_with_notes | review_required — İKİSİ DE model onayı DEĞİLDİR. */
  quality_gate: 'passed_with_notes' | 'review_required';
  warnings: string[];
}
export interface KanitKarti {
  claim_id: string;
  source_id: string;
  statement: string;
  locator: string;
  /** Araştırmacı kaynağı açıp sayfa düzeyinde doğruladı mı. LLM dolduramaz. */
  researcher_verified: true;
}
export interface MakaleSonuc {
  manuscript_id: string;
  manuscript_filename: string;
  artifacts: Record<string, string>;
}
export interface DenetimDogrulama {
  valid: boolean;
  event_count: number;
  last_hash: string | null;
  message: string;
}

// ---- Sağlık / yetenek ----

/** Motor ayakta mı. */
export const saglik = () => istek<Saglik>('/health');

/** Yerel Gemma erişilebilir mi (P0 taslak ve P7 anlatısı buna bağlı). */
export const llmDurum = () => istek<LlmDurum>('/api/llm/status');

/**
 * P5'in GERÇEKTEN çalıştırdığı yöntemler.
 *
 * P4 bunların dışında yöntem önerebilir; P5 çalıştırmaz ve sessizce yaklaşık
 * bir yöntemle DEĞİŞTİRMEZ. Arayüz bu farkı kullanıcıya göstermelidir.
 */
export const yurutucular = () => istek<Yurutucular>('/api/analysis/executors');

// ---- Sıralı akış (her adım bir öncekinin çıktısına bağlı) ----

/** P0: serbest metinden şema doğrulamalı protokol taslağı (yerel Gemma). */
export const taslakUret = (metin: string) =>
  istek<{ protocol: Protokol }>('/api/research/draft-from-text', {
    method: 'POST',
    govde: { user_input: metin },
  });

/** P0: protokolü elle oluştur. */
export const arastirmaOlustur = (icerik: Record<string, unknown>) =>
  istek<Protokol>('/api/research', { method: 'POST', govde: icerik });

/**
 * ÖN-KAYIT KİLİDİ. Sıra bilimsel bütünlük meselesidir: keşif önce yapılıp
 * kilit sonra alınırsa bu bir ön-kayıt değil, ön-kayıt tiyatrosudur (HARKing).
 * Doğrulayıcı çalışmada bu çağrı veri yüklenmeden ÖNCE yapılmalıdır.
 *
 * yerliKilitHash: suc_analizi oturumundaki kilit özeti — iki zinciri bağlar.
 */
export const protokolKilitle = (
  researchId: string,
  onaylayan: string,
  ek?: { okcOturumId?: string; yerliKilitHash?: string },
) =>
  istek<Protokol>(`/api/research/${researchId}/lock`, {
    method: 'POST',
    govde: {
      approved_by: onaylayan,
      ...(ek?.okcOturumId ? { okc_oturum_id: ek.okcOturumId } : {}),
      ...(ek?.yerliKilitHash ? { yerli_kilit_hash: ek.yerliKilitHash } : {}),
    },
  });

/** P3: ham veri yükleme. Motor dosyayı salt-okunur saklar ve SHA-256 alır. */
export function veriYukle(researchId: string, dosya: File) {
  const form = new FormData();
  form.append('file', dosya);
  return istek<VeriSeti>(`/api/research/${researchId}/datasets/upload`, {
    method: 'POST',
    form,
  });
}

export const DEGISKEN_TURLERI = [
  'identifier', 'boolean', 'categorical_nominal', 'categorical_ordinal',
  'integer', 'count', 'continuous', 'datetime', 'latitude', 'longitude',
  'geometry_wkt', 'free_text',
] as const;
export type DegiskenTuru = (typeof DEGISKEN_TURLERI)[number];

export const DEGISKEN_ROLLERI = [
  'identifier', 'outcome', 'predictor', 'grouping', 'time', 'geometry',
  'coordinate', 'weight', 'offset', 'unspecified',
] as const;
export type DegiskenRolu = (typeof DEGISKEN_ROLLERI)[number];

/** Motorun çıkardığı değişken — `advisory_only`, yani ÖNERİdir. */
export interface CikarilmisDegisken {
  name: string;
  source_dtype: string;
  inferred_type: DegiskenTuru;
  inferred_role: DegiskenRolu;
  confidence: number;
  reason: string;
  missing_rate: number;
  unique_count: number;
  sensitive_field_hint: boolean;
}
export interface CikarilmisSema {
  variables: CikarilmisDegisken[];
  advisory_only: boolean;
  confirmation_required: boolean;
  interpretation_note: string;
}
/** Şema uç noktası çıkarımı SARMALAR: {inferred, latest_confirmation}. */
export interface SemaGorunumu {
  inferred: CikarilmisSema;
  latest_confirmation: { confirmation_id: string } | null;
}

/** Araştırmacının onayladığı değişken. `rationale` en az 3 karakter. */
export interface DegiskenOnayi {
  name: string;
  confirmed_type: DegiskenTuru;
  role: DegiskenRolu;
  rationale: string;
}

/** P3: çıkarılmış şemayı görüntüle (onaydan önce insan incelemesi için). */
export const semaGetir = (researchId: string, datasetId: string) =>
  istek<SemaGorunumu>(
    `/api/research/${researchId}/datasets/${datasetId}/schema`,
  );

/**
 * P3: ŞEMA ONAYI — insan adımıdır, otomatikleştirilmez.
 *
 * Motor DEĞİŞKEN BAZINDA onay ister; her değişken için tür, rol ve gerekçe.
 * Çıkarılan şemayı toptan "onaylıyorum" demek sözleşmeye uymaz (422).
 */
export const semaOnayla = (
  researchId: string,
  datasetId: string,
  degiskenler: DegiskenOnayi[],
) =>
  istek<{ confirmation_id: string }>(
    `/api/research/${researchId}/datasets/${datasetId}/schema/confirm`,
    { method: 'POST', govde: { variables: degiskenler } },
  );

/** P4: deterministik yöntem önerisi + readiness kapısı. */
export const oneriUret = (
  researchId: string,
  datasetId: string,
  istem: Record<string, unknown>,
) =>
  istek<OneriSonuc>(
    `/api/research/${researchId}/datasets/${datasetId}/analysis/recommendations`,
    { method: 'POST', govde: istem },
  );

/** P4: yöntem onayı — araştırmacı imzası. */
export const oneriOnayla = (
  researchId: string,
  datasetId: string,
  recommendationId: string,
  onay: Record<string, unknown>,
) =>
  istek<OnaySonuc>(
    `/api/research/${researchId}/datasets/${datasetId}` +
      `/analysis/recommendations/${recommendationId}/approve`,
    { method: 'POST', govde: onay },
  );

/**
 * P5: model yürütme. Protokol KİLİTLİ olmalıdır.
 *
 * Gövde YALNIZ approval_id taşır — recommendation_id gönderilirse motor
 * extra_forbidden ile 422 verir (uçtan uca koşuda yakalandı). Öneri kimliği
 * zaten onayın içinde saklıdır.
 */
export const analizCalistir = (
  researchId: string,
  datasetId: string,
  approvalId: string,
) =>
  istek<AnalizSonuc>(
    `/api/research/${researchId}/datasets/${datasetId}/analysis/runs`,
    { method: 'POST', govde: { approval_id: approvalId } },
  );

/** P6: çapraz doğrulama. Dakikalar sürebilir — proxy zaman aşımı 15 dk. */
export const dogrula = (
  researchId: string,
  datasetId: string,
  analysisId: string,
) =>
  istek<DogrulamaSonuc>(
    `/api/research/${researchId}/datasets/${datasetId}` +
      `/analysis/runs/${analysisId}/validate`,
    { method: 'POST', govde: {} },
  );

/**
 * P7: akademik makale taslağı.
 *
 * use_local_gemma true ise kanitKartlari BOŞ OLAMAZ. Kartlar
 * otomatikleştirilemez: araştırmacının kaynağı açıp iddiayı sayfa düzeyinde
 * doğrulaması gerekir. Arayüz bunu insan onayı adımı olarak modeller,
 * LLM'e doldurtmaz.
 */
export const makaleUret = (
  researchId: string,
  datasetId: string,
  analysisId: string,
  validationId: string,
  istem: {
    title?: string;
    author_line?: string;
    target_journal?: string;
    use_local_gemma?: boolean;
    evidence_claims: KanitKarti[];
  },
) =>
  istek<MakaleSonuc>(
    `/api/research/${researchId}/datasets/${datasetId}` +
      `/analysis/runs/${analysisId}/validations/${validationId}/manuscripts`,
    { method: 'POST', govde: istem },
  );

// ---- Mekânsal (dış) yol ----
//
// P5 altı tablosal yöntem çalıştırır; Getis-Ord Gi*, Global Moran, LISA gibi
// mekânsal yöntemler motorda YOKTUR. Onlar suc_analizi'nde koşturulur ve
// sonucu buraya devredilir. Devredilen analiz P4 yöntem onayından ve P6
// çapraz doğrulamadan GEÇMEZ; üretilen makale bunu kendi metninde beyan eder.

/** suc_analizi fitness gate kararı — dış analizin kalite kapısı. */
export interface GateKarari {
  uygun: boolean;
  girdi_n: number;
  sebepler: string[];
}

export interface DisAnalizKaydi {
  external_id: string;
  arac: string;
  yontem_adi: string;
  bulgular: string[];
  yontem_ifadeleri: string[];
  sinirliliklar: string[];
  p5_onay_zinciri: false;
}

export interface DisMakaleSonucu {
  manuscript_id: string;
  external_ids: string[];
  okc_oturum_idleri: string[];
  generation_mode: string;
  grounding_facts: { fact_id: string; kind: string; statement: string }[];
  references: string[];
  manuscript_filename: string;
  p5_onay_zinciri: false;
  p6_capraz_dogrulama: false;
}

/** Makaleye taşınabilen mekânsal yöntemler (P5 listesinden AYRIdır). */
export const disYontemler = () =>
  istek<{ supported_tools: string[] }>('/api/analysis/external/methods');

/**
 * Dışarıda çalıştırılmış mekânsal analizi devreder.
 *
 * Protokol kilitli olmalıdır: dış analiz de ön-kayıt disiplinine tabidir.
 * Fitness gate reddettiyse motor kabul etmez (422) — bu kasıtlıdır.
 */
export const disAnalizDevret = (
  researchId: string,
  paket: {
    okc_oturum_id: string;
    arac: string;
    parametreler?: Record<string, unknown>;
    sonuc: Record<string, unknown>;
    gate_karari: GateKarari;
    veri_sha256?: string;
    veri_adi?: string;
  },
) =>
  istek<DisAnalizKaydi>(`/api/research/${researchId}/analysis/external`, {
    method: 'POST',
    govde: paket,
  });

/** Devredilmiş dış analizlerden akademik taslak üretir. */
export const disMakaleUret = (
  researchId: string,
  istem: {
    external_ids: string[];
    title?: string;
    author_line?: string;
    use_local_gemma?: boolean;
    evidence_claims: KanitKarti[];
  },
) =>
  istek<DisMakaleSonucu>(`/api/research/${researchId}/external-manuscripts`, {
    method: 'POST',
    govde: istem,
  });

/** Dış makale artefaktının indirme adresi (manuscript.md / claim_matrix.csv). */
export const disMakaleArtefaktUrl = (
  researchId: string,
  manuscriptId: string,
  filename: string,
) =>
  `${KOK}/api/research/${researchId}/external-manuscripts/` +
  `${manuscriptId}/artifacts/${filename}`;

/** Denetim zinciri bütünlüğü — kabul ölçütü: valid=true. */
export const denetimDogrula = (researchId: string) =>
  istek<DenetimDogrulama>(`/api/research/${researchId}/audit/verify`);
