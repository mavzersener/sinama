// Kanıt kartı geçerlilik kuralı — P7'ye yarım kart gitmesini engeller.
//
// Editörden çıkarıldı çünkü akademik olarak KRİTİK: motorun use_local_gemma
// yolunda evidence_claims boş olamaz, ama boş olmaması yetmez — her kart
// araştırmacının kaynağı açıp o yeri gördüğünü beyan etmelidir. Bu kural UI
// durumundan bağımsız sınanabilir olmalıdır.
import type { KanitKarti } from './scienceBridge';

/** Editördeki yarı-dolu kart. researcher_verified henüz boolean'dır. */
export interface KanitKartiTaslak {
  claim_id: string;
  source_id: string;
  statement: string;
  locator: string;
  researcher_verified: boolean;
}

/** İddia metni için asgari uzunluk — tek kelimelik "doğru" beyanları elenir. */
export const ASGARI_IFADE = 10;

/**
 * Bir taslak P7'ye gönderilebilir mi.
 *
 * Dört koşulun HEPSİ gerekir; researcher_verified tek başına yetmez, çünkü
 * kullanıcı kutucuğu işaretleyip alanları boş bırakabilir.
 */
export function kartGecerli(t: KanitKartiTaslak): boolean {
  return (
    t.researcher_verified &&
    t.claim_id.trim().length > 0 &&
    t.source_id.trim().length > 0 &&
    t.statement.trim().length >= ASGARI_IFADE &&
    t.locator.trim().length > 0
  );
}

/**
 * Taslaklardan motora gönderilecek kartları süzer.
 *
 * Geçersiz kartlar SESSİZCE DÜŞÜRÜLÜR (gönderilmez), tamamlanmış sayılmaz.
 * Kırpma bilinçlidir: motorun alan sınırlarına takılmamak için.
 */
export function gecerliKartlar(taslaklar: KanitKartiTaslak[]): KanitKarti[] {
  return taslaklar.filter(kartGecerli).map((t) => ({
    claim_id: t.claim_id.trim(),
    source_id: t.source_id.trim(),
    statement: t.statement.trim(),
    locator: t.locator.trim(),
    researcher_verified: true as const,
  }));
}
