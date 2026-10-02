import Papa from 'papaparse';

/**
 * Yüklenen CSV tablolarının bellek içi deposu.
 *
 * Eskiden satırların TAMAMI düğümün config'inde (`_uploadedData`) duruyordu:
 * her geri-alma adımında (50'ye kadar) derin kopyalanıyor, localStorage'a
 * (dolunca SESSİZCE yazılamıyordu) ve bulut kaydına giriyordu. Bunu sınırlamak
 * için tarayıcı dosyanın yalnız İLK 5000 SATIRINI okuyordu (`preview: 5000`):
 * daha büyük dosyalarda tüm analizler ve "tüm veri" kanıt paketi sessizce
 * ilk 5000 satırı kapsıyordu.
 *
 * Şimdi düğüm yalnız bir `VeriKaynagi` taşır (anahtar, sunucu kimliği,
 * sütunlar, satır sayısı, 10 satırlık önizleme); tablo burada, TAMAMI
 * okunarak tutulur. Sayfa yenilenince sunucudaki kopya (`/api/datasets/:id/
 * download`) aynı ayrıştırıcıyla yeniden okunur; oturumsuz yüklenmiş dosya
 * yenilemede kaybolur ve düğüm bunu açıkça söyler.
 */

export interface VeriTablosu {
  rows: Record<string, unknown>[];
  columns: string[];
  filename: string;
}

export interface CozumSecenekleri {
  hasHeader: boolean;
  delimiter: string;
}

export interface VeriKaynagi extends CozumSecenekleri {
  /** Depo anahtarı: `ds:<id>` (sunucuda) ya da `yerel:<…>` (yalnız bu oturum). */
  anahtar: string;
  datasetId?: number;
  filename: string;
  columns: string[];
  rowCount: number;
  onizleme: Record<string, unknown>[];
  /** Eski kayıttan taşındı ve tam 5000 satır: eski ayrıştırıcı kesmiş olabilir. */
  eskiKesikOlabilir?: boolean;
}

export const ONIZLEME_SATIR = 10;
const ESKI_KESME_SINIRI = 5000;

const depo = new Map<string, VeriTablosu>();
const bekleyen = new Map<string, Promise<VeriTablosu>>();

export const veriAl = (anahtar: string): VeriTablosu | undefined => depo.get(anahtar);
export function veriKaydet(anahtar: string, tablo: VeriTablosu): void {
  depo.set(anahtar, tablo);
}
/** Yalnız testler için. */
export function depoyuTemizle(): void {
  depo.clear();
  bekleyen.clear();
}

export function kaynakOlustur(
  anahtar: string, tablo: VeriTablosu, secenek: CozumSecenekleri, datasetId?: number,
): VeriKaynagi {
  return {
    anahtar,
    ...(datasetId !== undefined ? { datasetId } : {}),
    filename: tablo.filename,
    columns: tablo.columns,
    rowCount: tablo.rows.length,
    onizleme: tablo.rows.slice(0, ONIZLEME_SATIR),
    hasHeader: secenek.hasHeader,
    delimiter: secenek.delimiter,
  };
}

/** Eski (`_uploadedData`) biçimden taşıma: satırlar depoya, düğüme kaynak. */
export function eskiVeriyiTasi(
  nodeId: string, eski: { rows?: unknown; columns?: unknown; filename?: unknown },
  secenek: CozumSecenekleri, datasetId?: number,
): VeriKaynagi | null {
  if (!Array.isArray(eski.rows)) return null;
  const rows = eski.rows as Record<string, unknown>[];
  const tablo: VeriTablosu = {
    rows,
    columns: Array.isArray(eski.columns) ? (eski.columns as string[]) : Object.keys(rows[0] ?? {}),
    filename: typeof eski.filename === 'string' ? eski.filename : 'veri.csv',
  };
  const anahtar = datasetId !== undefined ? `ds:${datasetId}` : `yerel:${nodeId}`;
  veriKaydet(anahtar, tablo);
  const kaynak = kaynakOlustur(anahtar, tablo, secenek, datasetId);
  if (rows.length === ESKI_KESME_SINIRI) kaynak.eskiKesikOlabilir = true;
  return kaynak;
}

// ------------------------------------------------------------- ayrıştırma

// Başlık: UTF-8 BOM atılır ve kırpılır — Papa'nın kendi dönüşümüyle, böylece
// sütun listesi ile satır anahtarları AYNI olur. (Eskiden yalnız sütun
// listesi kırpılıyordu: " yas" başlıklı dosyada row["yas"] hep boş dönüyordu.)
const papaAyarlari = (s: CozumSecenekleri) => ({
  header: s.hasHeader,
  delimiter: s.delimiter === ',' ? '' : s.delimiter, // '' = otomatik
  dynamicTyping: true,
  skipEmptyLines: true as const,
  transformHeader: (h: string) => h.replace(/^\uFEFF/, '').trim(),
});

function tabloyaCevir(sonuc: Papa.ParseResult<unknown>, hasHeader: boolean, filename: string): VeriTablosu {
  if (hasHeader) {
    const columns = (sonuc.meta.fields ?? []).slice();
    return { rows: sonuc.data as Record<string, unknown>[], columns, filename };
  }
  // Başlıksız: Papa dizi döndürür; col_N nesnelerine çevrilir.
  const diziler = sonuc.data as unknown[][];
  const genislik = diziler.reduce((m, r) => Math.max(m, r.length), 0);
  const columns = Array.from({ length: genislik }, (_, i) => `col_${i}`);
  const rows = diziler.map((degerler) => {
    const satir: Record<string, unknown> = {};
    columns.forEach((c, i) => { satir[c] = degerler[i] ?? ''; });
    return satir;
  });
  return { rows, columns, filename };
}

/** Metni TAMAMIYLA ayrıştırır (sunucudan inen kopya ve testler). */
export function metniCoz(metin: string, s: CozumSecenekleri, filename: string): VeriTablosu {
  return tabloyaCevir(Papa.parse(metin, papaAyarlari(s)) as Papa.ParseResult<unknown>, s.hasHeader, filename);
}

/** Tarayıcıda seçilen dosyayı TAMAMIYLA ayrıştırır (eski `preview: 5000` yok). */
export function dosyayiCoz(dosya: File, s: CozumSecenekleri): Promise<VeriTablosu> {
  return new Promise((tamam, red) => {
    Papa.parse<unknown>(dosya, {
      ...papaAyarlari(s),
      complete: (sonuc) => {
        try { tamam(tabloyaCevir(sonuc, s.hasHeader, dosya.name)); } catch (e) { red(e); }
      },
      error: (e: unknown) => red(e instanceof Error ? e : new Error(String(e))),
    });
  });
}

// ------------------------------------------------------------ sunucudan

/**
 * Tabloyu döndürür: önce depo, yoksa sunucudaki kopya (aynı ayrıştırıcıyla).
 * Oturumsuz yüklenmiş (`yerel:`) ve depoda olmayan tablo için null.
 * Aynı veri seti için eşzamanlı istekler tek indirmede birleşir.
 */
export async function tabloyuGetir(kaynak: VeriKaynagi, sinyal?: AbortSignal): Promise<VeriTablosu | null> {
  const hazir = depo.get(kaynak.anahtar);
  if (hazir) return hazir;
  if (kaynak.datasetId === undefined) return null;
  let is = bekleyen.get(kaynak.anahtar);
  if (!is) {
    is = (async () => {
      const r = await fetch(`/api/datasets/${kaynak.datasetId}/download`, { credentials: 'include', signal: sinyal });
      if (r.status === 401) throw new Error('Sunucudaki veri seti için oturum açın.');
      if (!r.ok) throw new Error(`Veri seti #${kaynak.datasetId} indirilemedi (HTTP ${r.status}).`);
      const tablo = metniCoz(await r.text(), kaynak, kaynak.filename);
      depo.set(kaynak.anahtar, tablo);
      return tablo;
    })().finally(() => bekleyen.delete(kaynak.anahtar));
    bekleyen.set(kaynak.anahtar, is);
  }
  return is;
}
