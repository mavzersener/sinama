// Bir düğümün YUKARI AKIŞINDAKİ sütun adlarını bulur.
//
// NEDEN VAR: "Enlem Kolonu" gibi zorunlu alanlar serbest metindi; kullanıcı
// sütunun tam adını bilmek zorundaydı. Gerçek kolluk verisinde başlık
// "Koordinat Enlem" olabiliyor ve kullanıcı "latitude" yazıp hata alıyordu.
// Sütunlar yukarı akıştan okunabildiği için tahmin etmek gereksizdir.
//
// Saf tutuldu (React'ten bağımsız) çünkü sınanabilir olması gerekiyor:
// graf gezinmesi döngüde sonsuza gitmemeli ve en yakın veri kaynağını
// bulmalı.

export interface DugumOzeti {
  id: string;
  /** Koşu sonucu sütunları (varsa). */
  sonucSutunlari?: string[];
  /** Henüz koşulmamış CSV düğümünde yüklenen dosyanın sütunları. */
  yuklenenSutunlar?: string[];
}

export interface KenarOzeti {
  source: string;
  target: string;
}

/**
 * Hedef düğümün yukarı akışındaki en yakın sütun listesini döndürür.
 *
 * Genişlik-öncelikli gider: en yakın kaynak kazanır. Ziyaret edilen
 * düğümler işaretlenir; döngülü graf sonsuz dönmez.
 *
 * @param hedefId sütun arayan düğüm
 * @param dugumler graf düğümleri
 * @param kenarlar graf kenarları
 * @returns bulunan sütun adları; hiç yoksa boş dizi
 */
export function ustSutunlariBul(
  hedefId: string,
  dugumler: DugumOzeti[],
  kenarlar: KenarOzeti[],
): string[] {
  const haritada = new Map(dugumler.map((d) => [d.id, d]));
  const gelenler = new Map<string, string[]>();
  for (const k of kenarlar) {
    const liste = gelenler.get(k.target) ?? [];
    liste.push(k.source);
    gelenler.set(k.target, liste);
  }

  const gorulen = new Set<string>([hedefId]);
  let sira = [...(gelenler.get(hedefId) ?? [])];

  while (sira.length) {
    const sonraki: string[] = [];
    for (const id of sira) {
      if (gorulen.has(id)) continue;
      gorulen.add(id);
      const d = haritada.get(id);
      // Koşu sonucu daha güvenilirdir; yoksa yüklenen dosyaya bakılır.
      const sutunlar = d?.sonucSutunlari?.length
        ? d.sonucSutunlari
        : d?.yuklenenSutunlar;
      if (sutunlar?.length) return [...sutunlar];
      sonraki.push(...(gelenler.get(id) ?? []));
    }
    sira = sonraki;
  }
  return [];
}

/** Ada göre olası koordinat sütunlarını öne alır (seçimi kolaylaştırmak için). */
export function sutunlariSirala(sutunlar: string[], ipucu: 'lat' | 'lng' | null): string[] {
  if (!ipucu) return sutunlar;
  const anahtar = ipucu === 'lat'
    ? /(^|\b)(lat|latitude|enlem)(\b|$)/i
    : /(^|\b)(lng|lon|long|longitude|boylam)(\b|$)/i;
  const uygun = sutunlar.filter((s) => anahtar.test(s));
  const digerleri = sutunlar.filter((s) => !anahtar.test(s));
  return [...uygun, ...digerleri];
}
