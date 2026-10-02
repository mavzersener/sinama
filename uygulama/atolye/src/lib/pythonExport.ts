// Akışı çalıştırılabilir bir Python betiğine çevirir.
//
// Amaç: tarayıcıdaki motor (executionEngine.ts) neyi hesaplıyorsa, aynı
// boru hattını pandas/scikit-learn ile yeniden üretilebilir bir dosya olarak
// vermek. Motor bazı yerlerde bilinçli sadeleştirme yapar (ör. doğrusal
// regresyonda yalnız ilk özellik); betik bu durumlarda BİLİMSEL DOĞRU olanı
// üretir ve farkı "# NOT:" yorumuyla yazar.
//
// Sentetik demo verisi ÜRETİLMEZ: tarayıcıda demo modda çalışan kaynaklar
// (kolluk sorguları vb.) betikte gürültüsüzce başarısız olur — sahte veri bir
// analiz raporuna sızmasın diye NotImplementedError yükseltilir.

import type { Node, Edge } from '@xyflow/react';
import type { NodeData } from '../store/useStore';
import { getExecutionOrder } from '../engine/executionEngine';
import { getNodeDefinition } from '../nodes/nodeDefinitions';
import { sucDiziAlanlari } from '../nodes/sucAnaliziNodes.generated';

export interface PythonExportSonuc {
  /** Tam betik metni (UTF-8). */
  kod: string;
  /** Kullanıcıya gösterilecek uyarılar (eksik/desteklenmeyen düğümler vb.). */
  uyarilar: string[];
  /** Kod üretilemeyen düğüm tipleri. */
  desteklenmeyen: string[];
}

/** Çıktı türü: veri çerçevesi mi yoksa (satırı olmayan) rapor sözlüğü mü. */
type CiktiTipi = 'df' | 'rapor';

interface Girdi {
  vari: string;
  tip: CiktiTipi;
  etiket: string;
  /**
   * Düğümden ardındakilere akan TABLO değişkeni: tablo üreten düğümde kendi
   * değişkeni, rapor üreten düğümde kendi girdisinin tablosu (tarayıcı
   * motorundaki akisVerisi() ile aynı kural).
   */
  akis: string;
}

interface Baglam {
  cfg: Record<string, unknown>;
  vari: string;
  girdiler: Girdi[];
  /** İlk girdinin değişkeni; yoksa `pd.DataFrame()`. */
  df: string;
  imports: Set<string>;
  yardimcilar: Set<string>;
  uyarilar: string[];
  etiket: string;
}

interface Uretim {
  satirlar: string[];
  cikti: CiktiTipi;
}

// ============================================================
// Python literal yardımcıları
// ============================================================

function pyStr(v: unknown): string {
  // JSON string kaçışları Python'da birebir geçerlidir (\" \\ \n \uXXXX).
  return JSON.stringify(String(v ?? ''));
}

function pyNum(v: unknown, varsayilan = 0): string {
  const n = Number(v);
  return Number.isFinite(n) ? String(n) : String(varsayilan);
}

function pyInt(v: unknown, varsayilan = 0): string {
  const n = Math.trunc(Number(v));
  return Number.isFinite(n) ? String(n) : String(varsayilan);
}

function pyBool(v: unknown): string {
  return v === true || v === 'true' ? 'True' : 'False';
}

function pyListe(items: string[]): string {
  return `[${items.map(pyStr).join(', ')}]`;
}

/** "a, b" → ['a','b']; dizi de kabul eder. */
function kolonListesi(v: unknown): string[] {
  if (Array.isArray(v)) return v.map((x) => String(x).trim()).filter(Boolean);
  return String(v ?? '').split(',').map((s) => s.trim()).filter(Boolean);
}

// ============================================================
// Betiğe gömülen yardımcı fonksiyonlar (yalnız kullanılanlar yazılır)
// ============================================================

const YARDIMCI_KOD: Record<string, string> = {
  kolonlar: `
def _kolonlar(df: pd.DataFrame, metin: str, sadece_sayisal: bool = True) -> list[str]:
    """"a, b" metnini sütun listesine çevirir; boşsa sayısal sütunlara düşer."""
    secili = [k.strip() for k in (metin or "").split(",") if k.strip()]
    secili = [k for k in secili if k in df.columns]
    if secili:
        return secili
    if sadece_sayisal:
        return [k for k in df.columns if pd.api.types.is_numeric_dtype(df[k])]
    return list(df.columns)
`.trim(),

  rapor_yaz: `
def _rapor_yaz(ad: str, nesne) -> None:
    """Rapor sözlüğünü hem ekrana hem cikti/<ad>.json dosyasına yazar."""
    yol = CIKTI_DIZINI / f"{ad}.json"
    yol.write_text(json.dumps(nesne, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print(json.dumps(nesne, ensure_ascii=False, indent=2, default=str)[:2000])
    print(f"    -> {yol}")
`.trim(),

  ozellik_hedef: `
def _ozellik_hedef(df: pd.DataFrame, ozellikler: list[str], hedef: str):
    """Sayısal özellik matrisi + hedef vektörü (eksik satırlar düşürülür)."""
    if hedef not in df.columns:
        raise ValueError(f"hedef sütun bulunamadı: {hedef}")
    kolonlar = [k for k in ozellikler if k in df.columns]
    if not kolonlar:
        kolonlar = [k for k in df.columns
                    if k != hedef and pd.api.types.is_numeric_dtype(df[k])]
    if not kolonlar:
        raise ValueError(f"'{hedef}' icin sayisal ozellik sutunu yok")
    alt = df[kolonlar + [hedef]].copy()
    X = alt[kolonlar].apply(pd.to_numeric, errors="coerce")
    y = alt[hedef]
    gecerli = X.notna().all(axis=1) & y.notna()
    return X[gecerli], y[gecerli], kolonlar
`.trim(),

  temizle: `
def _temizle(df: pd.DataFrame, kolonlar: list[str], strateji: str, sabit: str,
             kirp: bool, tekilles: bool) -> pd.DataFrame:
    """Veri Temizleme düğümü: boş hücre stratejisi + kırpma + tekilleştirme."""
    out = df.copy()
    if kirp:
        for k in out.columns:
            out[k] = out[k].map(lambda v: v.strip() if isinstance(v, str) else v)
    kolonlar = [k for k in kolonlar if k in out.columns] or list(out.columns)
    # Motorla aynı: yalnız boşluktan ibaret metin de "eksik" sayılır.
    out[kolonlar] = out[kolonlar].replace(r"^\\s*$", np.nan, regex=True)

    if strateji == "drop_rows":
        out = out.dropna(subset=kolonlar)
    elif strateji == "ffill":
        out[kolonlar] = out[kolonlar].ffill()
    else:
        for k in kolonlar:
            if strateji in ("mean", "median"):
                # Metin sütununda sayısal değer yoktur; boş dilimin ortalamasını
                # almaya kalkmadan atla (aksi halde RuntimeWarning + NaN).
                sayisal = pd.to_numeric(out[k], errors="coerce")
                if not sayisal.notna().any():
                    continue
                deger = sayisal.mean() if strateji == "mean" else sayisal.median()
            elif strateji == "mode":
                mod = out[k].mode(dropna=True)
                deger = mod.iloc[0] if len(mod) else None
            elif strateji == "zero":
                deger = 0
            elif strateji == "constant":
                deger = sabit
            else:
                deger = None
            if deger is not None and not (isinstance(deger, float) and np.isnan(deger)):
                out[k] = out[k].fillna(deger)
    if tekilles:
        out = out.drop_duplicates()
    return out.reset_index(drop=True)
`.trim(),

  aykiri: `
def _aykiri(df: pd.DataFrame, kolonlar: list[str], yontem: str, esik: float) -> dict:
    """IQR / z-skoru / IsolationForest ile aykırı değer tespiti."""
    isaretli = pd.Series(False, index=df.index)
    detay: dict[str, int] = {}
    if yontem == "isolation_forest":
        from sklearn.ensemble import IsolationForest
        X = df[kolonlar].apply(pd.to_numeric, errors="coerce").dropna()
        if len(X) == 0:
            return {"yontem": yontem, "toplam_satir": len(df), "aykiri_sayisi": 0,
                    "aykiri_orani": 0.0, "kolon_bazinda": {}}
        etiket = IsolationForest(random_state=42, contamination="auto").fit_predict(X)
        isaretli.loc[X.index] = etiket == -1
        detay = {"tum_kolonlar": int((etiket == -1).sum())}
    else:
        for k in kolonlar:
            v = pd.to_numeric(df[k], errors="coerce")
            if yontem == "zscore":
                std = v.std(ddof=0)
                mask = ((v - v.mean()).abs() / std > esik) if std else pd.Series(False, index=df.index)
            else:  # iqr
                q1, q3 = v.quantile(0.25), v.quantile(0.75)
                iqr = q3 - q1
                mask = (v < q1 - esik * iqr) | (v > q3 + esik * iqr)
            mask = mask.fillna(False)
            detay[k] = int(mask.sum())
            isaretli |= mask
    toplam = len(df)
    return {
        "yontem": yontem,
        "esik": esik,
        "toplam_satir": toplam,
        "aykiri_sayisi": int(isaretli.sum()),
        "aykiri_orani": round(float(isaretli.sum()) / toplam * 100, 2) if toplam else 0.0,
        "kolon_bazinda": detay,
        "ornek_aykirilar": df[isaretli].head(5).to_dict("records"),
    }
`.trim(),

  suc_arac: `
def _suc_arac(arac: str, arg: dict) -> dict:
    """suc_analizi çekirdeğini kamusal gömülü girişinden çağırır (ml-service
    köprüsü ve MCP ile aynı boru hattı: istek bağlamı + fitness kapısı +
    kanıt oturumu + meta sözleşmesi). Bilinmeyen araç / eksik argüman /
    kapı reddi tipli suc_analizi hatası olarak yükselir."""
    from suc_analizi.arayuz.sunucu import arac_calistir
    return arac_calistir(arac, arg)
`.trim(),
};

// ============================================================
// Düğüm üreticileri
// ============================================================

type Uretici = (b: Baglam) => Uretim;

/** Rapor düğümlerinin ortak kuyruğu: JSON'a yaz + ekrana bas. */
function raporKuyrugu(b: Baglam, ad: string): string[] {
  b.yardimcilar.add('rapor_yaz');
  return [`_rapor_yaz(${pyStr(ad)}, ${b.vari})`];
}

const URETICILER: Record<string, Uretici> = {
  // ---------- Veri kaynakları ----------
  csv_source: (b) => {
    const dosya = String(b.cfg.filename || 'data.csv');
    const ayirici = String(b.cfg.delimiter ?? ',');
    const baslik = b.cfg.hasHeader === false ? 'None' : '0';
    return {
      satirlar: [
        `# NOT: tarayıcıda dosya yüklenmemişse motor demo verisi üretir; betik gerçek dosyayı okur.`,
        `${b.vari} = pd.read_csv(GIRDI_DIZINI / ${pyStr(dosya)}, sep=${pyStr(ayirici)}, header=${baslik})`,
      ],
      cikti: 'df',
    };
  },

  db_source: (b) => {
    b.imports.add('import os');
    b.imports.add('from sqlalchemy import create_engine  # pip install sqlalchemy');
    const sorgu = String(b.cfg.query || `SELECT * FROM ${b.cfg.table || 'tablo'}`);
    return {
      satirlar: [
        `# Bağlantı dizesi ortam değişkeninden okunur; parolayı betiğe gömmeyin.`,
        `_baglanti = os.environ.get("DATAFLOW_DB_URL", ${pyStr(b.cfg.connection ?? '')})`,
        `if not _baglanti:`,
        `    raise RuntimeError("DATAFLOW_DB_URL tanımlı değil")`,
        `${b.vari} = pd.read_sql(${pyStr(sorgu)}, create_engine(_baglanti))`,
      ],
      cikti: 'df',
    };
  },

  api_source: (b) => {
    b.imports.add('import requests  # pip install requests');
    let basliklar = '{}';
    try {
      const h = JSON.parse(String(b.cfg.headers || '{}'));
      basliklar = JSON.stringify(h).replace(/"/g, '"');
      basliklar = `json.loads(${pyStr(JSON.stringify(h))})`;
    } catch {
      b.uyarilar.push(`${b.etiket}: HTTP başlıkları geçerli JSON değil, boş bırakıldı.`);
      basliklar = '{}';
    }
    return {
      satirlar: [
        `_yanit = requests.request(${pyStr(b.cfg.method || 'GET')}, ${pyStr(b.cfg.url ?? '')},`,
        `                          headers=${basliklar}, timeout=60)`,
        `_yanit.raise_for_status()`,
        `${b.vari} = pd.json_normalize(_yanit.json())`,
      ],
      cikti: 'df',
    };
  },

  // ---------- İşleme ----------
  filter: (b) => {
    const kolon = String(b.cfg.column ?? '');
    const kosul = String(b.cfg.condition ?? 'equals');
    const deger = String(b.cfg.value ?? '');
    if (!kolon) {
      b.uyarilar.push(`${b.etiket}: sütun seçilmemiş, filtre atlandı.`);
      return { satirlar: [`${b.vari} = ${b.df}  # sütun boş — filtre uygulanmadı`], cikti: 'df' };
    }
    const k = `${b.df}[${pyStr(kolon)}]`;
    // Motor metin karşılaştırmalarını küçük harfe indirir; birebir taklit ediyoruz.
    const metin = `_m = ${k}.fillna("").astype(str).str.lower()`;
    const sayi = `_s = pd.to_numeric(${k}, errors="coerce")`;
    const d = pyStr(deger.toLowerCase());
    const kosullar: Record<string, [string, string]> = {
      equals: [metin, `_m == ${d}`],
      not_equals: [metin, `_m != ${d}`],
      contains: [metin, `_m.str.contains(${d}, regex=False)`],
      starts_with: [metin, `_m.str.startswith(${d})`],
      greater_than: [sayi, `_s > ${pyNum(deger)}`],
      less_than: [sayi, `_s < ${pyNum(deger)}`],
      is_null: ['', `${k}.isna()`],
      not_null: ['', `${k}.notna()`],
    };
    const [on, ifade] = kosullar[kosul] ?? ['', 'pd.Series(True, index=' + b.df + '.index)'];
    const satirlar = on ? [on] : [];
    satirlar.push(`${b.vari} = ${b.df}[${ifade}].reset_index(drop=True)`);
    return { satirlar, cikti: 'df' };
  },

  extend_field: (b) => {
    const yeni = String(b.cfg.newColumn ?? '');
    const ifade = String(b.cfg.expression ?? '');
    b.uyarilar.push(`${b.etiket}: ifade DataFlow ifade dilinde yazıldı; pandas.eval sözdizimini doğrulayın (CONCAT, IF gibi işlevler pandas'ta yok).`);
    return {
      satirlar: [
        `# NOT: ifade DataFlow ifade dilinde (CONCAT, IF, [Sütun Adı]…); pandas.eval sözdizimi farklıdır — kontrol edin.`,
        `${b.vari} = ${b.df}.copy()`,
        `${b.vari}[${pyStr(yeni)}] = ${b.df}.eval(${pyStr(ifade)})`,
      ],
      cikti: 'df',
    };
  },

  aggregate: (b) => {
    const grup = String(b.cfg.groupBy ?? '');
    const aggler = (Array.isArray(b.cfg.aggregations) ? b.cfg.aggregations : ['COUNT']) as string[];
    const eslesme: Record<string, [string, string]> = {
      SUM: ['sum', 'sum'],
      AVG: ['avg', 'mean'],
      MAX: ['max', 'max'],
      MIN: ['min', 'min'],
      STDEV: ['stdev', 'std'],
    };
    const satirlar = [
      `_grup = ${b.df}.groupby(${pyStr(grup)}, dropna=False)`,
      `${b.vari} = _grup.size().reset_index(name="count")`,
      `# Motorla aynı: değer sütunu seçildiyse o, yoksa grup dışı ilk sayısal sütun.`,
      `_sayisal = [k for k in ${b.df}.columns if k != ${pyStr(grup)} and pd.api.types.is_numeric_dtype(${b.df}[k])]`,
      `_agg_kolon = ${b.cfg.valueColumn ? pyStr(b.cfg.valueColumn) : `(_sayisal[0] if _sayisal else None)`}`,
    ];
    for (const a of aggler) {
      const e = eslesme[a.toUpperCase()];
      if (!e) continue;
      satirlar.push(`if _agg_kolon is not None: ${b.vari}[${pyStr(e[0])}] = pd.to_numeric(${b.df}[_agg_kolon], errors="coerce").groupby(${b.df}[${pyStr(grup)}], dropna=False).${e[1]}().to_numpy()`);
    }
    return { satirlar, cikti: 'df' };
  },

  sort: (b) => {
    const kolonlar = kolonListesi(b.cfg.columns);
    const artan = String(b.cfg.order ?? 'asc') !== 'desc';
    return {
      satirlar: [
        `${b.vari} = ${b.df}.sort_values(by=${pyListe(kolonlar)}, ascending=${artan ? 'True' : 'False'}).reset_index(drop=True)`,
      ],
      cikti: 'df',
    };
  },

  join: (b) => {
    const tip = String(b.cfg.joinType ?? 'inner');
    const how = tip === 'full' ? 'outer' : tip;
    const sag = b.girdiler[1]?.vari;
    if (!sag) {
      b.uyarilar.push(`${b.etiket}: birleştirme iki girdi ister, ikincisi bağlı değil.`);
      return { satirlar: [`${b.vari} = ${b.df}  # ikinci girdi yok — birleştirme atlandı`], cikti: 'df' };
    }
    return {
      satirlar: [
        `${b.vari} = pd.merge(${b.df}, ${sag}, left_on=${pyStr(b.cfg.leftKey ?? '')},`,
        `                     right_on=${pyStr(b.cfg.rightKey ?? '')}, how=${pyStr(how)})`,
      ],
      cikti: 'df',
    };
  },

  dedup: (b) => {
    const kolonlar = kolonListesi(b.cfg.keyColumns);
    const keep = String(b.cfg.keep ?? 'first');
    const subset = kolonlar.length ? `subset=${pyListe(kolonlar)}, ` : '';
    return {
      satirlar: [
        `${b.vari} = ${b.df}.drop_duplicates(${subset}keep=${pyStr(keep)}).reset_index(drop=True)`,
        `print(f"    tekrar silinen: {len(${b.df}) - len(${b.vari})}")`,
      ],
      cikti: 'df',
    };
  },

  data_clean: (b) => {
    b.yardimcilar.add('temizle');
    return {
      satirlar: [
        `${b.vari} = _temizle(${b.df}, ${pyListe(kolonListesi(b.cfg.columns))},`,
        `                    strateji=${pyStr(b.cfg.strategy ?? 'drop_rows')}, sabit=${pyStr(b.cfg.fillValue ?? '')},`,
        `                    kirp=${pyBool(b.cfg.trimWhitespace)}, tekilles=${pyBool(b.cfg.dropDuplicates)})`,
        `print(f"    {len(${b.df})} -> {len(${b.vari})} satır")`,
      ],
      cikti: 'df',
    };
  },

  block_group: (b) => {
    const marker = String(b.cfg.markerColumn ?? '');
    const idCol = String(b.cfg.idColumn || 'blok_id');
    const fill = kolonListesi(b.cfg.fillColumns);
    const satirlar = [
      `# "Birleştirilmiş hücre" ihracını onar: blok kimliği SATIR SIRASINDAN`,
      `# gelir. Sütun birleştirerek kimlik üretmek farklı olayları tek anahtara`,
      `# çökertir; groupby(...).ffill() ise doldurmayı blok sınırında durdurur.`,
      `${b.vari} = ${b.df}.copy()`,
      `_marker = ${b.vari}[${pyStr(marker)}].notna()`,
      `if ${b.vari}[${pyStr(marker)}].dtype == object:`,
      `    _marker &= ${b.vari}[${pyStr(marker)}].astype(str).str.strip() != ""`,
      `_blok = _marker.cumsum()`,
    ];
    if (fill.length) {
      satirlar.push(
        `_doldur = [k for k in ${pyListe(fill)} if k in ${b.vari}.columns]`,
        `${b.vari}[_doldur] = ${b.vari}.groupby(_blok)[_doldur].ffill()`,
      );
    }
    satirlar.push(
      // cumsum()==0 → ilk bloktan önceki satırlar; hiçbir olaya ait değil.
      `${b.vari}[${pyStr(idCol)}] = np.where(`,
      `    _blok > 0, "B" + _blok.astype(str).str.zfill(6), "")`,
      `print(f"    blok: {int(_blok.max())} | bloksuz satır: {int((_blok == 0).sum())}")`,
    );
    return { satirlar, cikti: 'df' };
  },

  data_quality: (b) => {
    const kolonlar = kolonListesi(b.cfg.columns);
    const secim = kolonlar.length ? pyListe(kolonlar) : `list(${b.df}.columns)`;
    return {
      satirlar: [
        `_kols = [k for k in ${secim} if k in ${b.df}.columns]`,
        `${b.vari} = {`,
        `    "satir_sayisi": int(len(${b.df})),`,
        `    "kolon_sayisi": int(len(_kols)),`,
        `    "tekrar_satir": int(${b.df}.duplicated().sum()),`,
        `    "kolonlar": {`,
        `        k: {`,
        `            "tip": str(${b.df}[k].dtype),`,
        `            "eksik": int(${b.df}[k].isna().sum()),`,
        `            "eksik_yuzde": round(float(${b.df}[k].isna().mean()) * 100, 2),`,
        `            "tekil": int(${b.df}[k].nunique(dropna=True)),`,
        `        }`,
        `        for k in _kols`,
        `    },`,
        `}`,
        `${b.vari}["kalite_skoru"] = round(`,
        `    100 - float(${b.df}[_kols].isna().mean().mean()) * 100, 2) if _kols else 0.0`,
        ...raporKuyrugu(b, `${b.vari}_veri_kalitesi`),
      ],
      cikti: 'rapor',
    };
  },

  // ---------- Analiz ----------
  statistics: (b) => {
    b.yardimcilar.add('kolonlar');
    const istatistikler = (Array.isArray(b.cfg.stats) ? b.cfg.stats : ['count', 'mean', 'std', 'min', 'max']) as string[];
    return {
      satirlar: [
        `_kols = _kolonlar(${b.df}, ${pyStr(kolonListesi(b.cfg.columns).join(','))})`,
        `${b.vari} = (${b.df}[_kols].apply(pd.to_numeric, errors="coerce")`,
        `              .agg(${pyListe(istatistikler)}).round(4).to_dict())`,
        ...raporKuyrugu(b, `${b.vari}_istatistik`),
      ],
      cikti: 'rapor',
    };
  },

  correlation: (b) => {
    b.yardimcilar.add('kolonlar');
    return {
      satirlar: [
        `_kols = _kolonlar(${b.df}, ${pyStr(kolonListesi(b.cfg.columns).join(','))})`,
        `${b.vari} = {`,
        `    "method": ${pyStr(b.cfg.method ?? 'pearson')},`,
        `    "columns": _kols,`,
        `    "matrix": ${b.df}[_kols].apply(pd.to_numeric, errors="coerce")`,
        `               .corr(method=${pyStr(b.cfg.method ?? 'pearson')}).round(4).to_dict(),`,
        `}`,
        ...raporKuyrugu(b, `${b.vari}_korelasyon`),
      ],
      cikti: 'rapor',
    };
  },

  linear_regression: (b) => {
    b.imports.add('from sklearn.linear_model import LinearRegression');
    b.imports.add('from sklearn.metrics import mean_squared_error, r2_score');
    b.yardimcilar.add('ozellik_hedef');
    return {
      satirlar: [
        `# Motorla aynı: tüm özellikler, tam kayıtlar; katsayılar ve R² örneklem içi.`,
        `# (Motor ayrıca tohumlu bir holdout ile test R² raporlar.)`,
        `_X, _y, _kols = _ozellik_hedef(${b.df}, ${pyListe(kolonListesi(b.cfg.features))}, ${pyStr(b.cfg.target ?? '')})`,
        `_model = LinearRegression().fit(_X, _y)`,
        `_tahmin = _model.predict(_X)`,
        `${b.vari} = {`,
        `    "target": ${pyStr(b.cfg.target ?? '')},`,
        `    "features": _kols,`,
        `    "coefficients": dict(zip(_kols, [round(float(c), 4) for c in _model.coef_])),`,
        `    "intercept": round(float(_model.intercept_), 4),`,
        `    "r_squared": round(float(r2_score(_y, _tahmin)), 4),`,
        `    "mse": round(float(mean_squared_error(_y, _tahmin)), 4),`,
        `    "sample_size": int(len(_X)),`,
        `}`,
        ...raporKuyrugu(b, `${b.vari}_dogrusal_regresyon`),
      ],
      cikti: 'rapor',
    };
  },

  cross_validation: (b) => {
    b.imports.add('from sklearn.linear_model import LinearRegression');
    b.imports.add('from sklearn.model_selection import KFold, cross_val_score');
    b.yardimcilar.add('ozellik_hedef');
    const metrikler: Record<string, string> = { r2: 'r2', mse: 'neg_mean_squared_error', mae: 'neg_mean_absolute_error', rmse: 'neg_root_mean_squared_error' };
    const metrik = metrikler[String(b.cfg.metric ?? 'r2')] ?? 'r2';
    return {
      satirlar: [
        `_X, _y, _kols = _ozellik_hedef(${b.df}, ${pyListe(kolonListesi(b.cfg.features))}, ${pyStr(b.cfg.target ?? '')})`,
        `_kf = KFold(n_splits=${pyInt(b.cfg.k, 5)}, shuffle=True, random_state=42)`,
        `_skor = cross_val_score(LinearRegression(), _X, _y, cv=_kf, scoring=${pyStr(metrik)})`,
        `${b.vari} = {`,
        `    "k": ${pyInt(b.cfg.k, 5)},`,
        `    "metric": ${pyStr(b.cfg.metric ?? 'r2')},`,
        `    "features": _kols,`,
        `    "fold_skorlari": [round(float(s), 4) for s in _skor],`,
        `    "ortalama": round(float(np.mean(_skor)), 4),`,
        `    "std": round(float(np.std(_skor, ddof=1)), 4) if len(_skor) > 1 else 0.0,`,
        `    "total_samples": int(len(_X)),`,
        `}`,
        ...raporKuyrugu(b, `${b.vari}_capraz_dogrulama`),
      ],
      cikti: 'rapor',
    };
  },

  model_validation: (b) => {
    b.imports.add('from sklearn.metrics import classification_report, confusion_matrix');
    const gercek = pyStr(b.cfg.actualColumn ?? '');
    const tahmin = pyStr(b.cfg.predictedColumn ?? '');
    return {
      satirlar: [
        `_alt = ${b.df}[[${gercek}, ${tahmin}]].dropna()`,
        `if _alt.empty:`,
        `    raise ValueError(${gercek} + " / " + ${tahmin} + " çiftinde karşılaştırılabilir satır yok")`,
        `_etiketler = sorted(set(_alt[${gercek}]) | set(_alt[${tahmin}]))`,
        `${b.vari} = {`,
        `    "labels": [str(e) for e in _etiketler],`,
        `    "confusion_matrix": confusion_matrix(_alt[${gercek}], _alt[${tahmin}],`,
        `                                        labels=_etiketler).tolist(),`,
        `    "report": classification_report(_alt[${gercek}], _alt[${tahmin}],`,
        `                                   output_dict=True, zero_division=0),`,
        `    "sample_size": int(len(_alt)),`,
        `}`,
        ...raporKuyrugu(b, `${b.vari}_model_dogrulama`),
      ],
      cikti: 'rapor',
    };
  },

  anomaly_detection: (b) => {
    b.yardimcilar.add('kolonlar');
    b.yardimcilar.add('aykiri');
    return {
      satirlar: [
        `_kols = _kolonlar(${b.df}, ${pyStr(kolonListesi(b.cfg.columns).join(','))})`,
        `${b.vari} = _aykiri(${b.df}, _kols, ${pyStr(b.cfg.method ?? 'iqr')}, ${pyNum(b.cfg.threshold, 1.5)})`,
        ...raporKuyrugu(b, `${b.vari}_aykiri_deger`),
      ],
      cikti: 'rapor',
    };
  },

  clustering: (b) => {
    b.imports.add('from sklearn.cluster import KMeans');
    b.imports.add('from sklearn.metrics import silhouette_score');
    b.imports.add('from sklearn.preprocessing import StandardScaler');
    b.yardimcilar.add('kolonlar');
    const k = pyInt(b.cfg.k, 3);
    // Motorla aynı: varsayılan z-standartlaştırma (standardize=false ile kapanır).
    const olcekle = b.cfg.standardize !== false && b.cfg.standardize !== 'false';
    return {
      satirlar: [
        `_kols = _kolonlar(${b.df}, ${pyStr(kolonListesi(b.cfg.features).join(','))})`,
        `_X = ${b.df}[_kols].apply(pd.to_numeric, errors="coerce").dropna()`,
        olcekle
          ? `_olcek = StandardScaler().fit(_X); _Z = _olcek.transform(_X)`
          : `_olcek = None; _Z = _X.to_numpy()`,
        `_km = KMeans(n_clusters=${k}, max_iter=${pyInt(b.cfg.maxIterations, 100)}, n_init=10, random_state=${pyInt(b.cfg.seed, 42)}).fit(_Z)`,
        `# Kümeler büyükten küçüğe numaralanır (motorla aynı); merkezler ÖZGÜN birimde.`,
        `_sira = sorted(range(${k}), key=lambda c: (-int((_km.labels_ == c).sum()), c))`,
        `_merkez = _olcek.inverse_transform(_km.cluster_centers_) if _olcek is not None else _km.cluster_centers_`,
        `${b.vari} = {`,
        `    "k": ${k},`,
        `    "features": _kols,`,
        `    "standardize": ${olcekle ? 'True' : 'False'},`,
        `    "silhouette_score": round(float(silhouette_score(_Z, _km.labels_)), 4) if len(set(_km.labels_)) > 1 else None,`,
        `    "inertia": round(float(_km.inertia_), 4),`,
        `    "sample_size": int(len(_X)),`,
        `    "clusters": [`,
        `        {"cluster": i + 1, "size": int((_km.labels_ == c).sum()),`,
        `         "centroid": [round(float(v), 2) for v in _merkez[c]]}`,
        `        for i, c in enumerate(_sira)`,
        `    ],`,
        `}`,
        ...raporKuyrugu(b, `${b.vari}_kmeans`),
      ],
      cikti: 'rapor',
    };
  },

  dbscan: (b) => {
    b.imports.add('from sklearn.cluster import DBSCAN');
    b.yardimcilar.add('kolonlar');
    return {
      satirlar: [
        `_kols = _kolonlar(${b.df}, ${pyStr(kolonListesi(b.cfg.features).join(','))})`,
        `_X = ${b.df}[_kols].apply(pd.to_numeric, errors="coerce").dropna()`,
        `_db = DBSCAN(eps=${pyNum(b.cfg.eps, 0.5)}, min_samples=${pyInt(b.cfg.minSamples, 5)}).fit(_X)`,
        `${b.vari} = {`,
        `    "features": _kols,`,
        `    "eps": ${pyNum(b.cfg.eps, 0.5)},`,
        `    "min_samples": ${pyInt(b.cfg.minSamples, 5)},`,
        `    "kume_sayisi": int(len(set(_db.labels_)) - (1 if -1 in _db.labels_ else 0)),`,
        `    "gurultu_sayisi": int((_db.labels_ == -1).sum()),`,
        `    "kume_boyutlari": {str(e): int((_db.labels_ == e).sum()) for e in sorted(set(_db.labels_))},`,
        `}`,
        ...raporKuyrugu(b, `${b.vari}_dbscan`),
      ],
      cikti: 'rapor',
    };
  },

  hierarchical: (b) => {
    b.imports.add('from sklearn.cluster import AgglomerativeClustering');
    b.yardimcilar.add('kolonlar');
    return {
      satirlar: [
        `_kols = _kolonlar(${b.df}, ${pyStr(kolonListesi(b.cfg.features).join(','))})`,
        `_X = ${b.df}[_kols].apply(pd.to_numeric, errors="coerce").dropna()`,
        `_hc = AgglomerativeClustering(n_clusters=${pyInt(b.cfg.nClusters, 3)}, linkage=${pyStr(b.cfg.linkage ?? 'ward')}).fit(_X)`,
        `${b.vari} = {`,
        `    "features": _kols,`,
        `    "linkage": ${pyStr(b.cfg.linkage ?? 'ward')},`,
        `    "kume_boyutlari": {str(e): int((_hc.labels_ == e).sum()) for e in sorted(set(_hc.labels_))},`,
        `}`,
        ...raporKuyrugu(b, `${b.vari}_hiyerarsik`),
      ],
      cikti: 'rapor',
    };
  },

  pca: (b) => {
    b.imports.add('from sklearn.decomposition import PCA');
    b.imports.add('from sklearn.preprocessing import StandardScaler');
    b.yardimcilar.add('kolonlar');
    return {
      satirlar: [
        `_kols = _kolonlar(${b.df}, ${pyStr(kolonListesi(b.cfg.features).join(','))})`,
        `_X = ${b.df}[_kols].apply(pd.to_numeric, errors="coerce").dropna()`,
        `_pca = PCA(n_components=${pyInt(b.cfg.nComponents, 2)}).fit(StandardScaler().fit_transform(_X))`,
        `${b.vari} = {`,
        `    "features": _kols,`,
        `    "aciklanan_varyans": [round(float(v), 4) for v in _pca.explained_variance_ratio_],`,
        `    "kumulatif": [round(float(v), 4) for v in np.cumsum(_pca.explained_variance_ratio_)],`,
        `    "bilesenler": [[round(float(x), 4) for x in satir] for satir in _pca.components_],`,
        `}`,
        ...raporKuyrugu(b, `${b.vari}_pca`),
      ],
      cikti: 'rapor',
    };
  },

  arima: (b) => {
    b.imports.add('from statsmodels.tsa.arima.model import ARIMA  # pip install statsmodels');
    const hedef = pyStr(b.cfg.target ?? '');
    const tarih = String(b.cfg.dateColumn ?? '');
    const satirlar = [`_seri = pd.to_numeric(${b.df}[${hedef}], errors="coerce").dropna()`];
    if (tarih) {
      satirlar.unshift(
        `${b.vari}_veri = ${b.df}.copy()`,
        `${b.vari}_veri[${pyStr(tarih)}] = pd.to_datetime(${b.vari}_veri[${pyStr(tarih)}], errors="coerce")`,
        `${b.vari}_veri = ${b.vari}_veri.dropna(subset=[${pyStr(tarih)}]).sort_values(${pyStr(tarih)})`,
      );
      satirlar[3] = `_seri = pd.to_numeric(${b.vari}_veri[${hedef}], errors="coerce").dropna()`;
    }
    satirlar.push(
      `_fit = ARIMA(_seri, order=(${pyInt(b.cfg.p, 1)}, ${pyInt(b.cfg.d, 1)}, ${pyInt(b.cfg.q, 1)})).fit()`,
      `_ongoru = _fit.forecast(steps=${pyInt(b.cfg.forecastSteps, 10)})`,
      `${b.vari} = {`,
      `    "target": ${hedef},`,
      `    "order": [${pyInt(b.cfg.p, 1)}, ${pyInt(b.cfg.d, 1)}, ${pyInt(b.cfg.q, 1)}],`,
      `    "aic": round(float(_fit.aic), 4),`,
      `    "bic": round(float(_fit.bic), 4),`,
      `    "ongoru": [round(float(v), 4) for v in _ongoru],`,
      `}`,
      ...raporKuyrugu(b, `${b.vari}_arima`),
    );
    return { satirlar, cikti: 'rapor' };
  },

  association_rules: (b) => {
    b.imports.add('from collections import Counter');
    b.imports.add('from itertools import combinations');
    const kolon = pyStr(b.cfg.itemsColumn ?? '');
    return {
      satirlar: [
        `# Motorla aynı yaklaşım: tekil ve ikili ürün sayımından kural türetme.`,
        `_tekil, _ikili = Counter(), Counter()`,
        `_toplam = len(${b.df})`,
        `for _hucre in ${b.df}[${kolon}].fillna("").astype(str):`,
        `    _urunler = [p.strip() for p in re.split(r"[,;|]", _hucre) if p.strip()]`,
        `    _tekil.update(_urunler)`,
        `    _ikili.update("→".join(sorted(c)) for c in combinations(_urunler, 2))`,
        `_kurallar = []`,
        `for _cift, _adet in _ikili.items():`,
        `    _a, _b = _cift.split("→")`,
        `    _destek = _adet / _toplam if _toplam else 0`,
        `    _guven = _adet / _tekil[_a] if _tekil[_a] else 0`,
        `    _lift = _guven / (_tekil[_b] / _toplam) if _tekil[_b] and _toplam else 0`,
        `    if _guven >= ${pyNum(b.cfg.minConfidence, 0.5)} and _destek >= ${pyNum(b.cfg.minSupport, 0.05)}:`,
        `        _kurallar.append({"onculi": _a, "sonuc": _b, "support": round(_destek, 4),`,
        `                          "confidence": round(_guven, 4), "lift": round(_lift, 4)})`,
        `${b.vari} = {`,
        `    "items_column": ${kolon},`,
        `    "toplam_islem": _toplam,`,
        `    "kurallar": sorted(_kurallar, key=lambda r: -r["lift"])[:20],`,
        `}`,
        ...raporKuyrugu(b, `${b.vari}_birliktelik_kurallari`),
      ],
      cikti: 'rapor',
    };
  },

  // ---------- Denetimli öğrenme (ml-service karşılıkları) ----------
  random_forest: (b) => denetimliOgrenme(b, 'RandomForest', {
    siniflama: `RandomForestClassifier(n_estimators=${pyInt(b.cfg.nEstimators, 100)}, random_state=42)`,
    regresyon: `RandomForestRegressor(n_estimators=${pyInt(b.cfg.nEstimators, 100)}, random_state=42)`,
    importlar: ['from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor'],
  }),

  gradient_boosting: (b) => denetimliOgrenme(b, 'GradientBoosting', {
    siniflama: `GradientBoostingClassifier(n_estimators=${pyInt(b.cfg.nEstimators, 100)}, max_depth=${pyInt(b.cfg.maxDepth, 3)}, learning_rate=${pyNum(b.cfg.learningRate, 0.1)}, random_state=42)`,
    regresyon: `GradientBoostingRegressor(n_estimators=${pyInt(b.cfg.nEstimators, 100)}, max_depth=${pyInt(b.cfg.maxDepth, 3)}, learning_rate=${pyNum(b.cfg.learningRate, 0.1)}, random_state=42)`,
    importlar: ['from sklearn.ensemble import GradientBoostingClassifier, GradientBoostingRegressor'],
  }),

  svm: (b) => denetimliOgrenme(b, 'SVM', {
    siniflama: `SVC(kernel=${pyStr(b.cfg.kernel ?? 'rbf')}, C=${pyNum(b.cfg.c, 1)})`,
    regresyon: `SVR(kernel=${pyStr(b.cfg.kernel ?? 'rbf')}, C=${pyNum(b.cfg.c, 1)})`,
    importlar: ['from sklearn.svm import SVC, SVR'],
  }),

  logistic_regression: (b) => denetimliOgrenme(b, 'LogisticRegression', {
    siniflama: `LogisticRegression(C=${pyNum(b.cfg.c, 1)}, max_iter=${pyInt(b.cfg.maxIter, 100)})`,
    regresyon: `LogisticRegression(C=${pyNum(b.cfg.c, 1)}, max_iter=${pyInt(b.cfg.maxIter, 100)})`,
    importlar: ['from sklearn.linear_model import LogisticRegression'],
    hepSiniflama: true,
  }),

  // ---------- Kolluk analizi ----------
  sna: (b) => {
    b.imports.add('import networkx as nx  # pip install networkx');
    const kisi = pyStr(b.cfg.personColumn ?? '');
    const bag = pyStr(b.cfg.linkColumn ?? '');
    const yontem = String(b.cfg.method ?? 'degree');
    const merkez: Record<string, string> = {
      degree: 'nx.degree_centrality(_G)',
      betweenness: 'nx.betweenness_centrality(_G)',
      closeness: 'nx.closeness_centrality(_G)',
    };
    return {
      satirlar: [
        `_kenarlar = ${b.df}[[${kisi}, ${bag}]].dropna().astype(str)`,
        `_G = nx.from_pandas_edgelist(_kenarlar, source=${kisi}, target=${bag})`,
        `_merkeziyet = ${merkez[yontem] ?? merkez.degree}`,
        `_bilesenler = sorted(nx.connected_components(_G), key=len, reverse=True)`,
        `${b.vari} = {`,
        `    "method": ${pyStr(yontem)},`,
        `    "node_count": _G.number_of_nodes(),`,
        `    "edge_count": _G.number_of_edges(),`,
        `    "network_density": round(nx.density(_G), 4),`,
        `    "community_count": len(_bilesenler),`,
        `    "top_nodes": [{"node": k, "skor": round(float(v), 4), "degree": _G.degree(k)}`,
        `                  for k, v in sorted(_merkeziyet.items(), key=lambda x: -x[1])[:10]],`,
        `    "communities": [{"id": i + 1, "size": len(c), "members": sorted(c)[:5]}`,
        `                    for i, c in enumerate(_bilesenler[:5])],`,
        `}`,
        ...raporKuyrugu(b, `${b.vari}_sosyal_ag`),
      ],
      cikti: 'rapor',
    };
  },

  geo_hotspot: (b) => {
    const lat = pyStr(b.cfg.latColumn ?? '');
    const lng = pyStr(b.cfg.lngColumn ?? '');
    const agirlik = String(b.cfg.weightColumn ?? '');
    const grid = pyNum(b.cfg.gridSize, 0.01);
    return {
      satirlar: [
        `_g = ${b.df}.copy()`,
        `_g["_lat"] = pd.to_numeric(_g[${lat}], errors="coerce")`,
        `_g["_lng"] = pd.to_numeric(_g[${lng}], errors="coerce")`,
        agirlik
          ? `_g["_agirlik"] = pd.to_numeric(_g[${pyStr(agirlik)}], errors="coerce").fillna(1.0)`
          : `_g["_agirlik"] = 1.0`,
        `_g = _g.dropna(subset=["_lat", "_lng"])`,
        `if _g.empty:`,
        `    raise ValueError("koordinat sütunları (" + ${lat} + ", " + ${lng} + ") sayısal değere çevrilemedi")`,
        `_grid = ${grid}`,
        `_g["_hucre_lat"] = (_g["_lat"] / _grid).apply(np.floor) * _grid`,
        `_g["_hucre_lng"] = (_g["_lng"] / _grid).apply(np.floor) * _grid`,
        `_yogunluk = (_g.groupby(["_hucre_lat", "_hucre_lng"])`,
        `              .agg(sayi=("_agirlik", "size"), agirlik=("_agirlik", "sum"))`,
        `              .reset_index().sort_values("agirlik", ascending=False))`,
        `${b.vari} = {`,
        `    "grid_km": _grid,`,
        `    "gecerli_nokta": int(len(_g)),`,
        `    "hucre_sayisi": int(len(_yogunluk)),`,
        `    "sicak_noktalar": _yogunluk.head(10).to_dict("records"),`,
        `}`,
        ...raporKuyrugu(b, `${b.vari}_hotspot`),
      ],
      cikti: 'rapor',
    };
  },

  temporal_pattern: (b) => {
    const zaman = pyStr(b.cfg.timeColumn ?? '');
    const kategori = String(b.cfg.categoryColumn ?? '');
    const dilim = String(b.cfg.bucket ?? 'hour');
    const dilimIfade: Record<string, string> = {
      hour: '_z.dt.hour',
      day: '_z.dt.day_name()',
      week: '_z.dt.isocalendar().week',
      month: '_z.dt.month',
    };
    const satirlar = [
      // format= verilmez: "mixed" pandas 2.0+ ister, eskisinde tüm satırları
      // sessizce NaT yapar. Çıktının boş kalması bir bulgu değil, arızadır.
      `_z = pd.to_datetime(${b.df}[${zaman}], errors="coerce")`,
      `_gecerli = _z.notna()`,
      `if not _gecerli.any():`,
      `    raise ValueError("zaman sütunu " + ${zaman} + " hiçbir satırda tarihe çevrilemedi")`,
      `_dilim = (${dilimIfade[dilim] ?? dilimIfade.hour})[_gecerli]`,
      `${b.vari} = {`,
      `    "bucket": ${pyStr(dilim)},`,
      `    "gecerli_kayit": int(_gecerli.sum()),`,
      `    "dagilim": {str(k): int(v) for k, v in _dilim.value_counts().sort_index().items()},`,
      `    "zirve": str(_dilim.value_counts().idxmax()) if len(_dilim) else None,`,
    ];
    if (kategori) {
      satirlar.push(
        `    "kategori_capraz": pd.crosstab(_dilim, ${b.df}[${pyStr(kategori)}][_gecerli]).to_dict(),`,
      );
    }
    satirlar.push(`}`, ...raporKuyrugu(b, `${b.vari}_zamansal_oruntu`));
    return { satirlar, cikti: 'rapor' };
  },

  cooccurrence: (b) => {
    b.imports.add('from collections import Counter');
    b.imports.add('from itertools import combinations');
    const varlik = pyStr(b.cfg.entityColumn ?? '');
    const baglam = pyStr(b.cfg.contextColumn ?? '');
    const min = pyInt(b.cfg.minOccurrences, 2);
    return {
      satirlar: [
        `_alt = ${b.df}[[${varlik}, ${baglam}]].dropna().astype(str)`,
        `_sayac = Counter()`,
        `for _, _grup in _alt.groupby(${baglam}):`,
        `    _varliklar = sorted(set(_grup[${varlik}]))`,
        `    _sayac.update(combinations(_varliklar, 2))`,
        `_ciftler = [{"varlik_a": a, "varlik_b": c, "es_olusum": n}`,
        `            for (a, c), n in _sayac.most_common() if n >= ${min}]`,
        `${b.vari} = {`,
        `    "entity_column": ${varlik},`,
        `    "context_column": ${baglam},`,
        `    "min_es_olusum": ${min},`,
        `    "cift_sayisi": len(_ciftler),`,
        `    "en_guclu": _ciftler[:20],`,
        `}`,
        ...raporKuyrugu(b, `${b.vari}_es_olusum`),
      ],
      cikti: 'rapor',
    };
  },

  // ---------- Çıktı ----------
  chart: (b) => {
    b.imports.add('import matplotlib\nmatplotlib.use("Agg")\nimport matplotlib.pyplot as plt  # pip install matplotlib');
    const tip = String(b.cfg.chartType ?? 'bar');
    const x = String(b.cfg.xColumn ?? '');
    const y = String(b.cfg.yColumn ?? '');
    const baslik = String(b.cfg.title || 'Grafik');
    const cizim: Record<string, string> = {
      bar: `_eksen = ${b.df}.plot(kind="bar", x=${pyStr(x)}, y=${pyStr(y)}, legend=False)`,
      line: `_eksen = ${b.df}.plot(kind="line", x=${pyStr(x)}, y=${pyStr(y)}, legend=False)`,
      area: `_eksen = ${b.df}.plot(kind="area", x=${pyStr(x)}, y=${pyStr(y)}, legend=False)`,
      scatter: `_eksen = ${b.df}.plot(kind="scatter", x=${pyStr(x)}, y=${pyStr(y)})`,
      pie: `_eksen = ${b.df}.set_index(${pyStr(x)})[${pyStr(y)}].plot(kind="pie", ylabel="")`,
      heatmap: `_eksen = plt.gca()\n_eksen.imshow(${b.df}.select_dtypes("number").corr(), cmap="viridis")`,
    };
    return {
      satirlar: [
        `plt.figure(figsize=(9, 5))`,
        cizim[tip] ?? cizim.bar,
        `plt.title(${pyStr(baslik)})`,
        `plt.tight_layout()`,
        `${b.vari} = CIKTI_DIZINI / ${pyStr(`${baslik.replace(/[^\w.-]+/g, '_') || 'grafik'}.png`)}`,
        `plt.savefig(${b.vari}, dpi=150)`,
        `plt.close("all")`,
        `print(f"    grafik: {${b.vari}}")`,
      ],
      cikti: 'rapor',
    };
  },

  export: (b) => {
    const format = String(b.cfg.format ?? 'csv');
    const dosya = String(b.cfg.filename || 'output.csv').replace(/\.[^.]+$/, '');
    const uzanti: Record<string, string> = { csv: 'csv', json: 'json', excel: 'xlsx', parquet: 'parquet' };
    const yazim: Record<string, string> = {
      csv: `${b.df}.to_csv(_yol, index=False, encoding="utf-8-sig")`,
      json: `${b.df}.to_json(_yol, orient="records", force_ascii=False, indent=2)`,
      excel: `${b.df}.to_excel(_yol, index=False)  # pip install openpyxl`,
      parquet: `${b.df}.to_parquet(_yol, index=False)  # pip install pyarrow`,
    };
    return {
      satirlar: [
        `_yol = CIKTI_DIZINI / ${pyStr(`${dosya}.${uzanti[format] ?? 'csv'}`)}`,
        yazim[format] ?? yazim.csv,
        `${b.vari} = _yol`,
        `print(f"    yazıldı: {_yol} ({len(${b.df})} satır)")`,
      ],
      cikti: 'rapor',
    };
  },

  alert: (b) => {
    const kosul = String(b.cfg.condition ?? 'count_greater_than');
    const esik = pyNum(b.cfg.threshold, 0);
    const ifadeler: Record<string, string> = {
      count_greater_than: `len(${b.df}) > ${esik}`,
      count_less_than: `len(${b.df}) < ${esik}`,
      value_greater_than: `${b.df}.select_dtypes("number").max().max() > ${esik}`,
      value_less_than: `${b.df}.select_dtypes("number").min().min() < ${esik}`,
    };
    // Bilinmeyen koşul eskiden sessizce count_greater_than'a düşüyordu.
    if (!ifadeler[kosul]) {
      b.uyarilar.push(`${b.etiket}: bilinmeyen uyarı koşulu "${kosul}".`);
      return { satirlar: [`raise ValueError(${pyStr(`Bilinmeyen uyarı koşulu: ${kosul}`)})`], cikti: 'rapor' };
    }
    return {
      satirlar: [
        `_tetik = bool(${ifadeler[kosul]})`,
        `${b.vari} = {"kosul": ${pyStr(kosul)}, "esik": ${esik}, "tetiklendi": _tetik,`,
        `              "kanal": ${pyStr(b.cfg.channel ?? 'email')}, "satir": len(${b.df})}`,
        `# NOT: bildirim GÖNDERİLMEZ; kanal entegrasyonunu buraya siz ekleyin.`,
        `print("    uyarı", "TETİKLENDİ" if _tetik else "tetiklenmedi", ${pyStr(kosul)}, ${esik})`,
      ],
      cikti: 'rapor',
    };
  },

  evidence_export: (b) => {
    b.imports.add('import hashlib');
    b.imports.add('from datetime import datetime, timezone');
    return {
      satirlar: [
        `_veri_yolu = CIKTI_DIZINI / ${pyStr(`kanit_${String(b.cfg.caseNumber || 'dosya').replace(/[^\w.-]+/g, '_')}.csv`)}`,
        `${b.df}.to_csv(_veri_yolu, index=False, encoding="utf-8-sig")`,
        `_ozet = hashlib.sha256(_veri_yolu.read_bytes()).hexdigest()`,
        `${b.vari} = {`,
        `    "dosya_no": ${pyStr(b.cfg.caseNumber ?? '')},`,
        `    "memur_sicil": ${pyStr(b.cfg.officerId ?? '')},`,
        `    "veri_dosyasi": str(_veri_yolu),`,
        `    "sha256": _ozet,`,
        `    "satir_sayisi": int(len(${b.df})),`,
        `    "zaman_utc": datetime.now(timezone.utc).isoformat(),`,
        `}`,
        ...raporKuyrugu(b, `${b.vari}_kanit_manifesto`),
      ],
      cikti: 'rapor',
    };
  },

  agent_insight: (b) => {
    b.imports.add('import os');
    b.imports.add('import json');
    b.imports.add('import requests  # pip install requests');
    return {
      satirlar: [
        `# Yerel ajan uç noktası; DataFlow sunucusu çalışıyor olmalı.`,
        `_ajan_url = os.environ.get("DATAFLOW_AGENT_URL", "http://localhost:5000/api/agent/insight")`,
        `_yanit = requests.post(_ajan_url, timeout=180, json={`,
        `    "question": ${pyStr(b.cfg.question ?? '')},`,
        `    "tone": ${pyStr(b.cfg.tone ?? 'concise')},`,
        `    "language": ${pyStr(b.cfg.language ?? 'English')},`,
        // Rapor girdisinde özetin kendisi gider (tarayıcı motoru da özeti verir);
        // eskiden pd.DataFrame() nesnesi gidiyordu → json= ile TypeError.
        `    "context": ${b.girdiler[0]?.tip === 'rapor' ? `json.loads(json.dumps(${b.girdiler[0].vari}, default=str))` : `${b.df}.head(50).to_dict("records")`},`,
        `})`,
        `_yanit.raise_for_status()`,
        `${b.vari} = _yanit.json()`,
        ...raporKuyrugu(b, `${b.vari}_ajan_yorumu`),
      ],
      cikti: 'rapor',
    };
  },
};

// ---------- Denetimli öğrenme ortak üreteci ----------

function denetimliOgrenme(
  b: Baglam,
  ad: string,
  ayar: { siniflama: string; regresyon: string; importlar: string[]; hepSiniflama?: boolean },
): Uretim {
  ayar.importlar.forEach((i) => b.imports.add(i));
  b.imports.add('from sklearn.model_selection import train_test_split');
  b.imports.add('from sklearn.metrics import accuracy_score, f1_score, mean_squared_error, r2_score');
  b.yardimcilar.add('ozellik_hedef');

  const siniflama = ayar.hepSiniflama || String(b.cfg.task ?? 'classification') === 'classification';
  const testOrani = Number(b.cfg.testSize ?? 20) / 100;
  const ozellikler = kolonListesi(b.cfg.features);

  return {
    satirlar: [
      `_X, _y, _kols = _ozellik_hedef(${b.df}, ${pyListe(ozellikler)}, ${pyStr(b.cfg.target ?? '')})`,
      `_Xe, _Xt, _ye, _yt = train_test_split(_X, _y, test_size=${testOrani}, random_state=42)`,
      `_model = ${siniflama ? ayar.siniflama : ayar.regresyon}.fit(_Xe, _ye)`,
      `_tahmin = _model.predict(_Xt)`,
      `${b.vari} = {`,
      `    "model": ${pyStr(ad)},`,
      `    "task": ${pyStr(siniflama ? 'classification' : 'regression')},`,
      `    "target": ${pyStr(b.cfg.target ?? '')},`,
      `    "features": _kols,`,
      `    "train_size": int(len(_Xe)),`,
      `    "test_size": int(len(_Xt)),`,
      siniflama
        ? `    "accuracy": round(float(accuracy_score(_yt, _tahmin)), 4),`
        : `    "r2": round(float(r2_score(_yt, _tahmin)), 4),`,
      siniflama
        ? `    "f1_weighted": round(float(f1_score(_yt, _tahmin, average="weighted", zero_division=0)), 4),`
        : `    "mse": round(float(mean_squared_error(_yt, _tahmin)), 4),`,
      `}`,
      `if hasattr(_model, "feature_importances_"):`,
      `    ${b.vari}["feature_importances"] = dict(`,
      `        zip(_kols, [round(float(v), 4) for v in _model.feature_importances_]))`,
      ...raporKuyrugu(b, `${b.vari}_${ad.toLowerCase()}`),
    ],
    cikti: 'rapor',
  };
}

// ---------- Kolluk veri kaynakları: sahte veri üretilmez ----------

const KOLLUK_KAYNAKLARI: Record<string, string> = {
  pts_source: 'PTS (Polis Taktik Sistemi)',
  anpr_source: 'ANPR plaka tanıma',
  mobese_source: 'MOBESE kamera',
  ihbar_source: '155/156 ihbar kayıtları',
  adli_sicil_source: 'Adli sicil',
};

function kollukKaynagi(b: Baglam, tip: string): Uretim {
  const sistem = KOLLUK_KAYNAKLARI[tip];
  const ayarlar = Object.entries(b.cfg)
    .filter(([k]) => !k.startsWith('_'))
    .map(([k, v]) => `#   ${k}: ${String(v)}`);
  b.uyarilar.push(`${b.etiket}: ${sistem} bağlantısı betikte yok — sorgu parametreleri yorum olarak taşındı.`);
  return {
    satirlar: [
      `# ${sistem} — tarayıcıda DEMO verisiyle çalışır. Sahte veri bir rapora`,
      `# sızmasın diye betik burada bilerek durur: kurum API'sini siz bağlayın.`,
      ...(ayarlar.length ? ['# Akıştaki sorgu parametreleri:', ...ayarlar] : []),
      `raise NotImplementedError(`,
      `    "${sistem} bağlantısı tanımlı değil — bu düğümü kurum API'sine bağlayın "`,
      `    "(hukuki dayanak: ${String(b.cfg.legalBasis ?? '-')}, KVKK: ${String(b.cfg.kvkkClass ?? '-')})")`,
      `${b.vari} = pd.DataFrame()`,
    ],
    cikti: 'df',
  };
}

// ---------- suc_analizi köprüsü ----------

function sucAnaliziDugumu(b: Baglam, tip: string): Uretim {
  b.yardimcilar.add('suc_arac');
  const arac = tip.slice('suc_'.length);
  const diziAlanlari = new Set(sucDiziAlanlari[tip] ?? []);
  const argSatirlari: string[] = [];
  for (const [k, v] of Object.entries(b.cfg)) {
    if (v === '' || v === undefined || v === null || k.startsWith('_')) continue;
    if (diziAlanlari.has(k) && typeof v === 'string') {
      argSatirlari.push(`    ${pyStr(k)}: ${pyListe(kolonListesi(v))},`);
    } else if (typeof v === 'number') {
      argSatirlari.push(`    ${pyStr(k)}: ${pyNum(v)},`);
    } else if (typeof v === 'boolean') {
      argSatirlari.push(`    ${pyStr(k)}: ${pyBool(v)},`);
    } else if (Array.isArray(v)) {
      argSatirlari.push(`    ${pyStr(k)}: ${pyListe(v.map(String))},`);
    } else {
      argSatirlari.push(`    ${pyStr(k)}: ${pyStr(v)},`);
    }
  }
  return {
    satirlar: [
      `_arg = {`,
      `    "satirlar": ${b.df}.head(5000).to_dict("records"),  # motorla aynı üst sınır`,
      ...argSatirlari,
      `}`,
      `${b.vari} = _suc_arac(${pyStr(arac)}, _arg)`,
      ...raporKuyrugu(b, `${b.vari}_${arac}`),
    ],
    cikti: 'rapor',
  };
}

// ============================================================
// Ana üreteç
// ============================================================

export function pythonBetigiUret(
  nodes: Node<NodeData>[],
  edges: Edge[],
): PythonExportSonuc {
  const uyarilar: string[] = [];
  const desteklenmeyen: string[] = [];
  const imports = new Set<string>();
  const yardimcilar = new Set<string>();
  const govde: string[] = [];
  const ciktilar = new Map<string, Girdi>();

  if (nodes.length === 0) {
    return {
      kod: '',
      uyarilar: ['Tuvalde düğüm yok — önce bir akış kurun.'],
      desteklenmeyen: [],
    };
  }

  const sira = getExecutionOrder(nodes, edges);
  if (sira.length < nodes.length) {
    uyarilar.push(`${nodes.length - sira.length} düğüm çevrim (döngü) içinde kaldığı için dışa aktarılmadı.`);
  }

  const haritaSatirlari: string[] = [];

  sira.forEach((nodeId, i) => {
    const node = nodes.find((n) => n.id === nodeId);
    if (!node) return;
    const tip = String(node.data.type);
    const vari = `dugum_${i + 1}`;
    const tanim = getNodeDefinition(tip);
    const etiket = String(node.data.label || tanim?.label || tip);

    const girdiler: Girdi[] = edges
      .filter((e) => e.target === nodeId)
      .map((e) => ciktilar.get(e.source))
      .filter((g): g is Girdi => !!g);

    // Tablo girdisi: ilk girdinin akış tablosu. Rapor üreten bir düğümün
    // ardında tablo, raporun girdisinden AYNEN geçer (eskiden boş
    // pd.DataFrame() veriliyordu — tarayıcı motoru da boş veri veriyordu).
    const ilk = girdiler[0];
    const df = ilk ? ilk.akis : 'pd.DataFrame()';
    const akisNotu = ilk?.tip === 'rapor'
      ? [`# Girdi "${ilk.etiket}" rapor üretir; veri tablosu önceki adımdan aynen geçer (${df}).`]
      : [];

    const b: Baglam = {
      cfg: (node.data.config ?? {}) as Record<string, unknown>,
      vari,
      girdiler,
      df,
      imports,
      yardimcilar,
      uyarilar,
      etiket,
    };

    let uretim: Uretim;
    if (URETICILER[tip]) {
      uretim = URETICILER[tip](b);
    } else if (tip in KOLLUK_KAYNAKLARI) {
      uretim = kollukKaynagi(b, tip);
    } else if (tip.startsWith('suc_')) {
      uretim = sucAnaliziDugumu(b, tip);
    } else {
      desteklenmeyen.push(tip);
      uretim = {
        satirlar: [
          `# '${tip}' için kod üreteci yok. Ayarlar aşağıda; kendi kodunuzu yazın.`,
          `# config: ${JSON.stringify(b.cfg)}`,
          `raise NotImplementedError(${pyStr(`${tip} düğümü Python'a çevrilmedi`)})`,
          `${vari} = ${df}`,
        ],
        cikti: 'df',
      };
    }

    govde.push(
      `# ${'-'.repeat(69)}`,
      `# [${i + 1}] ${etiket} — ${tip} (id: ${node.id})`,
      `# ${'-'.repeat(69)}`,
      `print("[${i + 1}] ${etiket.replace(/"/g, "'")}")`,
      ...akisNotu,
      ...uretim.satirlar,
      '',
    );

    haritaSatirlari.push(`#   ${vari.padEnd(10)} = [${i + 1}] ${etiket} (${tip})`);
    ciktilar.set(nodeId, { vari, tip: uretim.cikti, etiket, akis: uretim.cikti === 'df' ? vari : df });
  });

  // ---- Başlık ----
  const zaman = new Date().toISOString();
  const paketler = new Set(['pandas', 'numpy']);
  for (const im of imports) {
    if (im.includes('sklearn')) paketler.add('scikit-learn');
    if (im.includes('networkx')) paketler.add('networkx');
    if (im.includes('matplotlib')) paketler.add('matplotlib');
    if (im.includes('statsmodels')) paketler.add('statsmodels');
    if (im.includes('requests')) paketler.add('requests');
    if (im.includes('sqlalchemy')) paketler.add('sqlalchemy');
  }
  if (yardimcilar.has('suc_arac')) paketler.add('suc_analizi');

  const baslik = [
    '#!/usr/bin/env python3',
    '# -*- coding: utf-8 -*-',
    '"""DataFlow akışının Python karşılığı — otomatik üretildi.',
    '',
    `Üretim zamanı : ${zaman}`,
    `Düğüm / bağlantı: ${sira.length} / ${edges.length}`,
    '',
    'Kurulum:',
    `    pip install ${Array.from(paketler).join(' ')}`,
    'Çalıştırma:',
    '    python akis.py            # girdi dosyaları betikle aynı dizinde beklenir',
    '',
    'Değişken haritası:',
    ...haritaSatirlari,
    '',
    'NOT: Tarayıcıdaki motor bazı yerlerde sadeleştirir (ör. doğrusal regresyonda',
    'yalnız ilk özellik). Bu betik bilimsel olarak doğru olanı yapar; farklar',
    '"# NOT:" yorumlarıyla işaretlidir.',
    '"""',
    'from __future__ import annotations',
    '',
    'import json',
    'import re',
    'from pathlib import Path',
    '',
    'import numpy as np',
    'import pandas as pd',
    ...Array.from(imports).sort(),
    '',
    '',
    '# Girdi dosyaları ve çıktılar betiğin yanındadır; gerekirse değiştirin.',
    'GIRDI_DIZINI = Path(__file__).resolve().parent',
    'CIKTI_DIZINI = GIRDI_DIZINI / "cikti"',
    'CIKTI_DIZINI.mkdir(exist_ok=True)',
    '',
  ];

  const yardimciBloklari = Array.from(yardimcilar)
    .sort()
    .map((ad) => YARDIMCI_KOD[ad])
    .filter(Boolean);

  const parcalar = [baslik.join('\n')];
  if (yardimciBloklari.length) {
    parcalar.push(
      ['', '# ' + '='.repeat(69), '# Yardımcılar', '# ' + '='.repeat(69), ''].join('\n'),
      yardimciBloklari.join('\n\n\n'),
      '',
    );
  }
  parcalar.push(
    ['', '# ' + '='.repeat(69), '# Akış (topolojik sırada)', '# ' + '='.repeat(69), ''].join('\n'),
    govde.join('\n'),
    'print("Akış tamamlandı. Çıktılar:", CIKTI_DIZINI)',
    '',
  );

  if (desteklenmeyen.length) {
    uyarilar.push(`Kod üreteci olmayan düğüm tipleri: ${Array.from(new Set(desteklenmeyen)).join(', ')}`);
  }

  return { kod: parcalar.join('\n'), uyarilar, desteklenmeyen };
}

/** Üretilen betiği .py dosyası olarak indirir. */
export function pythonBetiginiIndir(kod: string, dosyaAdi = 'dataflow_akis.py'): void {
  const blob = new Blob([kod], { type: 'text/x-python;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = dosyaAdi;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
