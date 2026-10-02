// Kanıt bütünlüğü sözleşmesi — istemci (kanıt paketi) ve sunucu (kanıt
// defteri) AYNI kanonik biçimi ve hash'i kullanır.
//
// Kanonik biçim RFC 8785 (JCS): nesne anahtarları UTF-16 kod birimi
// sırasıyla, ayraçlarda boşluk yok, sayılar ECMAScript Number→String
// kuralıyla, NaN/Infinity/undefined YASAK. Python doğrulayıcısı
// (scripts/kanit_dogrula.py) aynı kuralları uygular; JS'nin ürettiği hash
// Python'da bayt bayt yeniden üretilir.
//
// Neden JCS: kardeş uygulamalarda beş ayrı hash zinciri var (science_gpt
// AuditLedger, suc_analizi kanit, HARP AuditLogger/WormLedger/
// ImmutableAuditLog) ve hepsi farklı kanonik JSON kullanıyor — Python
// json.dumps 1.0'ı "1.0", JS "1" yazar; ortak doğrulayıcı imkânsız.
// Dil-bağımsız standart ortak zemindir (bkz. ENTEGRASYON.md).

export const KANIT_SEMASI = 'dataflow.kanit/1';
export const DEFTER_SEMASI = 'dataflow.kanit-defteri/1';
export const BASLANGIC_HASH = '0'.repeat(64);

/** RFC 8785 kanonik JSON. Temsil edilemeyen değerde hata atar (sessiz düşürme yok). */
export function kanonikJson(deger: unknown): string {
  if (deger === null) return 'null';
  switch (typeof deger) {
    case 'boolean':
      return deger ? 'true' : 'false';
    case 'number':
      if (!Number.isFinite(deger)) throw new Error(`kanonik JSON: sonlu olmayan sayı (${deger})`);
      // JSON.stringify sayıları ECMAScript Number→String ile yazar (JCS §3.2.2.3); -0 → "0".
      return JSON.stringify(deger);
    case 'string':
      return JSON.stringify(deger);
    case 'object': {
      if (deger instanceof Date) {
        if (Number.isNaN(deger.getTime())) throw new Error('kanonik JSON: geçersiz tarih');
        return JSON.stringify(deger.toISOString());
      }
      if (Array.isArray(deger)) return `[${deger.map(kanonikJson).join(',')}]`;
      const nesne = deger as Record<string, unknown>;
      // JCS: anahtarlar UTF-16 kod birimi sırasıyla — JS'nin varsayılan
      // sort()'u tam olarak budur (localeCompare DEĞİL).
      const anahtarlar = Object.keys(nesne).filter((k) => nesne[k] !== undefined).sort();
      return `{${anahtarlar.map((k) => `${JSON.stringify(k)}:${kanonikJson(nesne[k])}`).join(',')}}`;
    }
    default:
      throw new Error(`kanonik JSON: desteklenmeyen tip (${typeof deger})`);
  }
}

/** SHA-256 (onaltılık). Tarayıcı ve Node ≥19 WebCrypto ile. */
export async function sha256Hex(metin: string): Promise<string> {
  const ozet = await globalThis.crypto.subtle.digest('SHA-256', new TextEncoder().encode(metin));
  return Array.from(new Uint8Array(ozet), (b) => b.toString(16).padStart(2, '0')).join('');
}

export const kanonikHash = (deger: unknown) => sha256Hex(kanonikJson(deger));

/** Paketteki veri gövdesi: hash'in kapsadığı TAM içerik (ilk N satır değil). */
export interface KanitVerisi {
  columns: string[];
  rows: Record<string, unknown>[];
}

/** Sunucuya giden kayıt isteği — veri DEĞİL, yalnız özet ve hash'ler gider. */
export interface KanitKayitIstegi {
  kanit_id: string;
  dosya_no: string;
  veri_sha256: string;
  paket_sha256: string;
  satir: number;
  sutun: number;
  beyan_eden: string;
  kaynak_zinciri: Array<{ tip: string; etiket: string }>;
}

/** Defter kaydı: hash zincirinin bir halkası (imza hariç her alan hash'e girer). */
export interface DefterKaydi extends KanitKayitIstegi {
  sema: typeof DEFTER_SEMASI;
  sira: number;
  sunucu_zamani: string;
  aktor: { id: number; ad: string | null };
  onceki_hash: string;
  kayit_hash: string;
}

/** Sunucu makbuzu: defter kaydı + Ed25519 imzası (kayit_hash üzerine). */
export interface KanitMakbuzu {
  kayit: DefterKaydi;
  imza: string;
  anahtar_parmak_izi: string;
}

/** HARP'ın (dış çapa) kabul makbuzu — DataFlow imzası değil, HARP WORM mührü. */
export interface HarpMakbuzu {
  kabul: boolean;
  zaten_kayitli: boolean;
  sira: number;
  kayit_hash: string;
  harp_kayit_id: string | null;
  harp_entry_hash: string | null;
  harp_zamani: string | null;
  uyarilar: string[];
}

/** Makbuzun HARP'a iletim sonucu. Kaydı ENGELLEMEZ; yalnız dış çapa durumunu söyler. */
export type HarpIletimi =
  | { durum: 'yapilandirilmamis' }
  | { durum: 'iletildi'; makbuz: HarpMakbuzu }
  | { durum: 'reddedildi'; kod: string; mesaj: string; http: number }
  | { durum: 'iletilemedi'; neden: string };

/** Kaydın zincir hash'i: kayit_hash alanı hariç kanonik içerik. */
export function kayitHashGirdisi(kayit: Omit<DefterKaydi, 'kayit_hash'> | DefterKaydi): string {
  const { kayit_hash: _atla, ...govde } = kayit as DefterKaydi;
  void _atla;
  return kanonikJson(govde);
}
