// Mekânsal analizlerin koşturulup motora devredilmesi — saf orkestrasyon.
//
// UI'den ayrıldı çünkü sıra KRİTİK ve sınanabilir olmalı:
//
// 1. HER YÖNTEM TAZE OTURUMDA koşar. PPDAC döngüsü tek-analiz durum
//    makinesidir; aynı oturumda ikinci analiz faz ihlali üretir.
// 2. FITNESS GATE REDDEDERSE yöntem ATLANIR, devredilmez. Kapının
//    reddettiği bir analizi makaleye taşımak, kapıyı anlamsızlaştırır.
// 3. Kapı kararı devredilen pakete KONUR. Motor bunu yeniden sınar;
//    çift denetim bilinçlidir.
//
// Bir yöntemin hata vermesi diğerlerini düşürmez: hatalar toplanır ve
// kullanıcıya bildirilir, başarılı devirler korunur.

/** suc_analizi fitness gate kararı. */
export interface Uygunluk {
  uygun: boolean;
  girdi_n: number;
  sebepler?: string[];
}

/** Motora devredilecek paket. */
export interface DevirPaketi {
  okc_oturum_id: string;
  arac: string;
  sonuc: Record<string, unknown>;
  gate_karari: { uygun: boolean; girdi_n: number; sebepler: string[] };
}

/**
 * Orkestratörün ihtiyaç duyduğu dış çağrılar (test için enjekte edilir).
 *
 * `T` motorun döndürdüğü dış analiz kaydıdır; orkestratör içeriğini
 * bilmez, yalnız taşır.
 */
export interface DevirBagimliliklari<T> {
  baslat: (hipotez: string) => Promise<{ oturumId: string }>;
  veriBagla: (oturumId: string, arac: string) => Promise<Uygunluk | null>;
  analizeGec: (oturumId: string, uygunluk: Uygunluk) => Promise<void>;
  calistir: (oturumId: string, arac: string) => Promise<Record<string, unknown>>;
  devret: (paket: DevirPaketi) => Promise<T>;
  ilerleme?: (mesaj: string) => void;
}

export interface DevirSonucu<T> {
  /** Motorun kabul ettiği dış analiz kayıtları. */
  kabulEdilen: T[];
  /** Kapının reddettiği yöntemler ve gerekçeleri. */
  atlanan: { arac: string; sebep: string }[];
  /** Beklenmedik hata alan yöntemler. */
  hatali: { arac: string; mesaj: string }[];
}

/**
 * Seçilen yöntemleri sırayla koşturur ve motora devreder.
 *
 * Sıralı çalışır — paralel değil: motorun tek-süreç varsayımı ve PPDAC
 * oturum disiplini eşzamanlı koşuyu güvensiz kılar.
 */
export async function mekansalDevret<T>(
  araclar: string[],
  hipotez: string,
  bagimlilik: DevirBagimliliklari<T>,
): Promise<DevirSonucu<T>> {
  const kabulEdilen: T[] = [];
  const atlanan: { arac: string; sebep: string }[] = [];
  const hatali: { arac: string; mesaj: string }[] = [];

  for (const arac of araclar) {
    try {
      bagimlilik.ilerleme?.(`${arac} çalışıyor`);
      // Her yöntem KENDİ oturumunda: döngü tek-analizdir.
      const { oturumId } = await bagimlilik.baslat(hipotez);
      const uygunluk = await bagimlilik.veriBagla(oturumId, arac);

      if (!uygunluk || !uygunluk.uygun) {
        atlanan.push({
          arac,
          sebep: (uygunluk?.sebepler ?? []).join('; ') || 'veri uygun değil',
        });
        continue;
      }

      await bagimlilik.analizeGec(oturumId, uygunluk);
      const sonuc = await bagimlilik.calistir(oturumId, arac);

      bagimlilik.ilerleme?.(`${arac} devrediliyor`);
      const kayit = await bagimlilik.devret({
        okc_oturum_id: oturumId,
        arac,
        sonuc,
        gate_karari: {
          uygun: uygunluk.uygun,
          girdi_n: uygunluk.girdi_n,
          sebepler: uygunluk.sebepler ?? [],
        },
      });
      kabulEdilen.push(kayit);
    } catch (e) {
      // Bir yöntemin hatası diğerlerini düşürmez.
      hatali.push({ arac, mesaj: e instanceof Error ? e.message : String(e) });
    }
  }

  return { kabulEdilen, atlanan, hatali };
}

/** Kullanıcıya gösterilecek özet uyarı metni (yoksa null). */
export function devirUyarisi<T>(sonuc: DevirSonucu<T>): string | null {
  const parcalar: string[] = [];
  if (sonuc.atlanan.length) {
    parcalar.push(
      'Kapı şu yöntemleri reddetti — ' +
        sonuc.atlanan.map((a) => `${a.arac}: ${a.sebep}`).join(' · '),
    );
  }
  if (sonuc.hatali.length) {
    parcalar.push(
      'Hata alan yöntemler — ' +
        sonuc.hatali.map((h) => `${h.arac}: ${h.mesaj}`).join(' · '),
    );
  }
  return parcalar.length ? parcalar.join(' | ') : null;
}
