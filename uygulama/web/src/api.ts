/**
 * Arka uç istemcisi (uygulama/sunucu.py). Ön yüz hesap yapmaz: her sayı ve hüküm arka
 * uçtan, çekirdeğin tek motorundan gelir (AGENTS kural 5).
 */
export class ApiHatasi extends Error {
  tur?: string
  oneri?: string | null
  constructor(mesaj: string, tur?: string, oneri?: string | null) {
    super(mesaj)
    this.tur = tur
    this.oneri = oneri
  }
}

async function istek<T>(yol: string, secenek: RequestInit = {}): Promise<T> {
  let y: Response
  try {
    y = await fetch(yol, { headers: { "Content-Type": "application/json" }, ...secenek })
  } catch {
    throw new ApiHatasi("__baglanti__", "baglanti")
  }
  const govde = await y.json().catch(() => ({}))
  if (!y.ok) {
    const h = (govde as { hata?: { mesaj?: string; tur?: string; oneri?: string | null } }).hata
    throw new ApiHatasi(h?.mesaj ?? `HTTP ${y.status}`, h?.tur, h?.oneri)
  }
  return govde as T
}

const post = (govde?: unknown): RequestInit => ({ method: "POST", body: JSON.stringify(govde ?? {}) })

export type Saglik = { durum: string; surum: string; sinama_surumu: string; veri_koku: string; dil_modeli: boolean }
export type Onizleme = { ad: string; sutunlar: string[]; satir: number; degerler: Record<string, string[] | null>; kesildi: boolean }
export type Hipotez = {
  kimlik: string
  tur: "BIRINCIL" | "RAKIP" | "BILINMEYEN"
  ifade: string
  ongoru?: { arac: string; olcut: string; kosul: string }
  yanlislama?: string
  serbest?: boolean
  sonraki_kanit?: string
}
export type PlanRakip = { kod: string; sinama: string; cozulebilir: boolean; gereksinim: string | null; sonraki_kanit: string }
export type Plan = {
  soru_turu: string
  amac: string
  birincil: { hipotez: string; arac: string; kosul: string; kapi_araci: string; gerekli_alanlar: string[] }
  rakipler: PlanRakip[]
  ulasilabilir_en_ust: string
  tavan_nedenleri: string[]
  uyarilar?: string[]
}
export type CalismaYaniti = { oturum_id: string; hipotezler: Hipotez[]; plan: Plan; uyarilar: string[] }
export type HukumRakip = { kod: string; durum: string; gerekce: string; olcum?: Record<string, unknown> }
export type Hukum = {
  kategori: string
  birincil_ongoru: string
  en_guclu_rakip: string | null
  rakipler: HukumRakip[]
  cozulmemis_rakipler: string[]
  sonraki_en_iyi_kanit: { rakip: string; gereken: string }[]
  saglamlik_uyarilari: string[]
  kurallar: { kural: string; girdi: string; sonuc: string }[]
  ifade: string
  insan_onayi_gerekir: boolean
  kisi_baglantisi: boolean
  durum: string
  kural_surumu: string
  sinama_surumu: string
  paket_hash: string
}
export type HukumYaniti = {
  oturum_id: string
  soru_turu: string
  amac: string
  kilit_hash: string | null
  hipotezler: Hipotez[]
  sinamalar: { arac: string; hipotez: string; amac: string }[]
  hukum: Hukum
  uyarilar: string[]
}
export type Manifesto = {
  oturum_id: string
  faz: string
  amac: string
  kilit: { onaylayan: string; hash: string } | null
  talep: { karar?: string }
  insan_onaylari: { onaylayan: string; not?: string }[]
  sonuc: { tur: string } | null
  bilimsel?: {
    soru_turu: string
    hipotezler: Hipotez[]
    parametreler: Record<string, string>
    onaylayan: string | null
    kanit?: { birincil: { durum: string; gerekce: string } }
    hukum?: Hukum
  }
}

export const api = {
  saglik: () => istek<Saglik>("/api/saglik"),
  oneri: (soru: string) => istek<{ soru_turu: string | null; kaynak: string }>("/api/oneri", post({ soru })),
  veriListesi: () => istek<{ dosyalar: { ad: string; boyut: number }[] }>("/api/veri"),
  veriYukle: async (dosya: File) => {
    let y: Response
    try {
      y = await fetch(`/api/veri?ad=${encodeURIComponent(dosya.name)}`, { method: "POST", body: dosya })
    } catch {
      throw new ApiHatasi("__baglanti__", "baglanti")
    }
    const govde = await y.json().catch(() => ({}))
    if (!y.ok) throw new ApiHatasi(govde?.hata?.mesaj ?? `HTTP ${y.status}`, govde?.hata?.tur, govde?.hata?.oneri)
    return govde as { ad: string; boyut: number }
  },
  onizleme: (ad: string) => istek<Onizleme>(`/api/veri/${encodeURIComponent(ad)}/onizleme`),
  calismaBaslat: (govde: Record<string, string>) => istek<CalismaYaniti>("/api/calisma", post(govde)),
  durum: (id: string) => istek<Manifesto>(`/api/calisma/${id}`),
  plan: (id: string) => istek<Plan>(`/api/calisma/${id}/plan`),
  hipotezEkle: (id: string, govde: { ifade: string; sonraki_kanit?: string }) =>
    istek<{ eklenen: Hipotez }>(`/api/calisma/${id}/hipotez`, post(govde)),
  kanit: (id: string, dosya: string) => istek<unknown>(`/api/calisma/${id}/kanit`, post({ dosya })),
  hukum: (id: string) => istek<HukumYaniti>(`/api/calisma/${id}/hukum`, post()),
  sade: (id: string, dil: string) => istek<{ metin: string }>(`/api/calisma/${id}/sade`, post({ dil })),
  sonuc: (id: string, govde: { sonuc_turu: string; onaylayan: string; onay_notu?: string }) =>
    istek<{ faz: string }>(`/api/calisma/${id}/sonuc`, post(govde)),
}

/** Oturuma bağlı istemci tarafı not: seçilen veri dosyası (arka uçta henüz bağlanmadı). */
export const oturumNotu = {
  dosya: (id: string) => sessionStorage.getItem(`sinama:${id}:dosya`),
  dosyaKaydet: (id: string, ad: string) => sessionStorage.setItem(`sinama:${id}:dosya`, ad),
}
