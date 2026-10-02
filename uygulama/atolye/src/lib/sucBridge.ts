// suc_analizi köprüsü istemcisi — Rehberli Mod'un backend erişim katmanı.
//
// Tüm çağrılar DataFlow'un auth-korumalı proxy'si üzerinden ml-service'teki
// /suc/{arac} köprüsüne gider (POST /api/ml/suc/*). Köprü, suc_analizi MCP
// çekirdeğinin dispatch boru hattını çağırır: fitness gate + kanıt oturumu +
// meta sözleşmesi korunur. Bu istemci yalnız tipleme ve hata çevirisi yapar.
//
// Rehberli Mod, PPDAC döngü ailesini (dongu_*) sürücü olarak kullanır;
// kullanıcı oturum kavramını görmez (FR3 §B.1), istemci oturum_id'yi arkada
// taşır.

// Backend yapılandırılmış hata döner: HATA [tip]: mesaj + ÖNERİ: ... (FR3 §D.1)
// 'kimlik' bu listede DEĞİL: suc_analizi çekirdeği hiç üretmez (bkz.
// suc_analizi_koprusu.py _TIP_DURUM — yalnız 400/404/422/500/503 eşler).
// 401, FastAPI'ye ulaşmadan DataFlow'un kendi proxy'sinde (ml-proxy.ts)
// doğar; "oturum yok" backend'in "guvenlik" (dosya sınırı) tipiyle karıştı-
// rılmasın diye ayrı, istemciye özel bir tip olarak tutulur.
export type BackendErrorTip = 'veri' | 'guvenlik' | 'kullanim' | 'kapi' | 'dongu' | 'sistem' | 'kimlik';

export class BackendError extends Error {
  tip: BackendErrorTip;
  oneri?: string;
  constructor(tip: BackendErrorTip, mesaj: string, oneri?: string) {
    super(mesaj);
    this.name = 'BackendError';
    this.tip = tip;
    this.oneri = oneri;
  }
}

// { sonuc, meta } başarı zarfı; hata { tip, mesaj, oneri }
export interface Meta {
  arac: string;
  satir?: number;
  kesildi?: boolean;
  insan_onayi_gerekir?: boolean;
  uyarilar?: string[];
  kanit_durumu?: string; // "YAZILAMADI" ise kanıt kaydı diske yazılamadı
}
export interface Zarf<T> {
  sonuc: T;
  meta: Meta;
}

// HTTP durumundan hata tipine — köprü tip alanını gövdede taşır
const DURUM_TIP: Record<number, BackendErrorTip> = {
  400: 'kullanim',
  404: 'kullanim',
  422: 'kapi',
  500: 'sistem',
  503: 'sistem',
};

async function cagir<T>(arac: string, arg: Record<string, unknown>): Promise<Zarf<T>> {
  let resp: Response;
  try {
    resp = await fetch(`/api/ml/suc/${arac}`, {
      method: 'POST',
      credentials: 'include',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify(arg),
    });
  } catch {
    throw new BackendError('sistem', 'Suç analizi servisine ulaşılamadı (ml-service 8001 çalışıyor mu?).');
  }
  if (resp.status === 401) {
    throw new BackendError('kimlik', 'Sunucu taraflı analiz için oturum açın.');
  }
  const govde = (await resp.json().catch(() => ({}))) as Record<string, unknown>;
  if (!resp.ok) {
    const tip = (govde.tip as BackendErrorTip) ?? DURUM_TIP[resp.status] ?? 'sistem';
    const mesaj = (govde.mesaj as string) ?? `Beklenmeyen hata (${resp.status})`;
    throw new BackendError(tip, mesaj, govde.oneri as string | undefined);
  }
  return govde as unknown as Zarf<T>;
}

// ---- Tipli çıktılar (canlı köprü şekillerinden türetildi) ----

export interface DonguPlan {
  urun_turu: string | null;
  hedef_kitle: string;
  onerilen: string[]; // fitness-gate beslemeli önerilen araç adları
  not: string;
}
export interface DonguBaslatSonuc {
  oturum_id: string;
  faz: string;
  plan: DonguPlan;
  sonraki: string;
}

export interface FitnessProfil {
  n: number;
  kesildi: boolean;
  uyarilar: string[];
  eksik_oran: Record<string, number>;
  kritik_eksik?: Record<string, number>;
  koordinat_gecerli_oran?: number;
  kardinalite?: Record<string, number>;
  duplikat_oran?: number;
}
export interface FitnessUygunluk {
  uygun: boolean;
  girdi_n: number;
  sebepler: string[];
}
export interface DonguVeriSonuc {
  faz: string;
  profil: FitnessProfil;
  uygunluk: FitnessUygunluk;
  sonraki?: string;
}

export interface KanitDogrulaSonuc {
  saglam: boolean;
  olay_sayisi: number;
  bozuk_adim: number | null;
  zincir_bas_hash: string;
}
export interface MuhakemeIziSonuc {
  urun: string; // Markdown muhakeme izi
}

// dongu_analiz gerekçesi resmî modda yapılandırılmıştır (string DEĞİL)
export interface AnalizGerekce {
  hipotez: string;
  yorum: string;
}

// ---- PPDAC döngü ailesi ----

/** Görev metnini oturuma çevirir; plan.onerilen fitness-gate önerileridir. */
export function dongurBaslat(karar: string, soran = 'analist', kapsam?: string) {
  return cagir<DonguBaslatSonuc>('dongu_baslat', { karar, soran, ...(kapsam ? { kapsam } : {}) });
}

/** Veri fazı: profil + fitness gate (otomatik). */
export function dongurVeri(oturumId: string, satirlar: Record<string, unknown>[], analiz?: string) {
  return cagir<DonguVeriSonuc>('dongu_veri', { oturum_id: oturumId, satirlar, ...(analiz ? { analiz } : {}) });
}

// Karar ağacı önericisi (analiz_oner): veri-yapısı + soruya göre öneriler
export interface OneriKalem {
  analiz: string;
  arac: string | null;
  mevcut: boolean;
  gerekce: string;
  kaynak_kural: string;
  uyari: string | null;
}
export interface AnalizOnerSonuc {
  profil_ozet: Record<string, unknown>;
  oneriler: OneriKalem[];
  not: string;
}

/** Yüklenen veri + soruya göre data-aware analiz önerileri (araç eşlemeli). */
export function analizOner(satirlar: Record<string, unknown>[], soru?: string, maks = 6) {
  return cagir<AnalizOnerSonuc>('analiz_oner', { satirlar, ...(soru ? { soru } : {}), maks });
}

/**
 * VERİ→ANALİZ kapısı: dongu_veri'den gelen uygunluk KARARINI (obje) iletir.
 * Backend `uygunluk.get("uygun")` bekler — string değil, dongu_veri
 * çıktısındaki uygunluk objesi geçilmelidir.
 */
export function dongurAnalizeGec(oturumId: string, uygunluk: FitnessUygunluk) {
  return cagir<{ faz: string }>('dongu_analize_gec', { oturum_id: oturumId, uygunluk });
}

/** Döngü içinde analiz aracı çalıştır; gerekçe yapılandırılmış (hipotez+yorum). */
export function dongurAnaliz(
  oturumId: string,
  arac: string,
  gerekce: AnalizGerekce,
  argumanlar: Record<string, unknown>,
) {
  return cagir<Record<string, unknown>>('dongu_analiz', {
    oturum_id: oturumId,
    arac,
    gerekce,
    argumanlar,
  });
}

/** Oturum manifestosu / açık oturum listesi (PPDAC durum görünümü). */
export function dongurDurum(oturumId?: string) {
  return cagir<Record<string, unknown>>('dongu_durum', oturumId ? { oturum_id: oturumId } : {});
}

// ---- Kanıt eylemleri (FR3 §B.2) ----

/** Oturumun muhakeme izi (Markdown): olgu (K1/K2) vs gerekçe (K3) ayrımlı. */
export function muhakemeIzi(oturumId: string) {
  return cagir<MuhakemeIziSonuc>('muhakeme_izi', { oturum_id: oturumId });
}

/** Kanıt zinciri hash bütünlüğünü sına (rozet: ✔ sağlam / ⚠ doğrulanamadı). */
export function kanitDogrula(oturumId: string) {
  return cagir<KanitDogrulaSonuc>('kanit_dogrula', { oturum_id: oturumId });
}

// ---- Provenans dikişi (Faz 4) ----
//
// Akademik çıktı ayrı bir sistemde (Science GPT) üretilir ve orada kendi
// denetim zincirini tutar. Bu iki zincir uçlarından bağlanmazsa, analizin
// yapıldığı oturumdan bakan biri akademik çıktının denetim durumunu göremez.

export interface DisDenetimBagi {
  zaman: string;
  sistem: string;
  kimlik: string;
  valid: boolean;
  olay_sayisi: number | null;
  son_hash: string | null;
  kanit_turu: string;
}

/**
 * Dış sistemin denetim doğrulamasını bu PPDAC oturumuna bağlar.
 *
 * `dogrulama` motorun `audit/verify` yanıtıdır ve OLDUĞU GİBİ geçirilir —
 * özetlenmez, yeniden yorumlanmaz.
 */
export function provenansDisDenetim(
  oturumId: string,
  kimlik: string,
  dogrulama: Record<string, unknown>,
  sistem = 'science_gpt',
) {
  return cagir<DisDenetimBagi>('provenans_dis_denetim', {
    oturum_id: oturumId, kimlik, dogrulama, sistem,
  });
}

export interface ProvenansHalka {
  halka: string;
  kurulu: boolean;
  /** makine | beyan | eksik — beyan MAKİNEYLE DOĞRULANAMAZ. */
  kanit_turu: 'makine' | 'beyan' | 'eksik';
  ozet: string;
}
export interface ProvenansOzeti {
  halkalar: ProvenansHalka[];
  kopukluklar: string[];
  tam_makine_zinciri: boolean;
  not: string;
}

/** Uçtan uca kaynak zinciri: her halkanın kanıt türü ve kopukluklar. */
export function provenansOzet(oturumId: string) {
  return cagir<ProvenansOzeti>('provenans_ozet', { oturum_id: oturumId });
}
