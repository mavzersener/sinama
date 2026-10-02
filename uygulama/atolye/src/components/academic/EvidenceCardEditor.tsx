// Kanıt kartı editörü — Akademik Mod'un insan onayı adımı.
//
// P7, use_local_gemma=true iken evidence_claims'in BOŞ OLMASINA izin vermez.
// Her kart bir iddiayı bir kaynağın belirli bir yerine (locator) bağlar ve
// araştırmacının o yeri AÇIP GÖRDÜĞÜNÜ beyan eder.
//
// BU EKRAN BİLİNÇLİ OLARAK ZAHMETLİDİR. Kartları LLM'e doldurtmak teknik
// olarak mümkün ama akademik olarak sahtekârlıktır: model kaynağı açmaz,
// sayfa numarasını uydurur. researcher_verified alanı ancak insan tıklamasıyla
// true olur; bu bileşende otomatik doldurma yolu YOKTUR.
import { useState } from 'react';
import { Plus, Trash2, BookOpen, CheckSquare, Square, AlertTriangle } from 'lucide-react';
import type { KanitKarti } from '../../lib/scienceBridge';
import { gecerliKartlar, kartGecerli, type KanitKartiTaslak } from '../../lib/kanitKarti';

// Motorun yerleşik kaynak kataloğu (P2'de doğrulanmış src_<32hex> kimlikleri
// dışında kabul ettiği sabit kimlikler).
const YERLESIK_KAYNAKLAR: { id: string; etiket: string }[] = [
  { id: 'weisburd_2022', etiket: 'Weisburd & Britt (2022) — Statistics in Criminal Justice' },
  { id: 'montgomery_runger_2018', etiket: 'Montgomery & Runger (2018) — Applied Statistics' },
  { id: 'mccue_2015', etiket: 'McCue (2015) — Data Mining and Predictive Analysis' },
  { id: 'paulsen_2009', etiket: 'Paulsen (2009) — Crime Mapping' },
  { id: 'chainey_2021', etiket: 'Chainey (2021) — Understanding Crime' },
  { id: 'bland_ariel_2022', etiket: 'Bland & Ariel (2022) — Targeting Domestic Abuse' },
];

const bosKart = (): KanitKartiTaslak => ({
  claim_id: '',
  source_id: YERLESIK_KAYNAKLAR[0].id,
  statement: '',
  locator: '',
  researcher_verified: false,
});

type Taslak = KanitKartiTaslak;

interface Props {
  kartlar: KanitKarti[];
  onDegisti: (kartlar: KanitKarti[]) => void;
}

export default function EvidenceCardEditor({ kartlar, onDegisti }: Props) {
  const [taslaklar, setTaslaklar] = useState<Taslak[]>(
    kartlar.length ? kartlar.map((k) => ({ ...k })) : [{ ...bosKart(), claim_id: 'C1' }],
  );

  /** Taslakları güncelle ve YALNIZ tam doğrulanmış kartları yukarı bildir. */
  const yay = (yeni: Taslak[]) => {
    setTaslaklar(yeni);
    onDegisti(gecerliKartlar(yeni));
  };

  const guncelle = (i: number, alan: keyof Taslak, deger: string | boolean) => {
    const yeni = taslaklar.map((t, j) => (j === i ? { ...t, [alan]: deger } : t));
    yay(yeni);
  };

  const ekle = () => yay([...taslaklar, { ...bosKart(), claim_id: `C${taslaklar.length + 1}` }]);
  const sil = (i: number) => yay(taslaklar.filter((_, j) => j !== i));

  const dogrulanan = taslaklar.filter(kartGecerli).length;

  return (
    <div className="space-y-3">
      <div className="flex items-start gap-2 text-xs bg-amber-950/40 text-amber-300 border border-amber-800/50 rounded p-2.5">
        <AlertTriangle size={15} className="shrink-0 mt-0.5" />
        <div>
          <div className="font-medium">Bu adım otomatikleştirilemez.</div>
          <div className="opacity-85">
            Her iddia için kaynağı açıp belirtilen yeri okumanız ve doğrulamanız gerekir.
            Model bu kartları sizin adınıza dolduramaz — sayfa numarasını uydurur.
          </div>
        </div>
      </div>

      {taslaklar.map((t, i) => (
        <div key={i} className="rounded-lg border border-slate-800 bg-slate-900/50 p-3 space-y-2">
          <div className="flex items-center gap-2">
            <input
              value={t.claim_id}
              onChange={(e) => guncelle(i, 'claim_id', e.target.value)}
              placeholder="C1"
              className="w-16 px-2 py-1 rounded bg-slate-950 border border-slate-700 text-xs text-slate-100"
              aria-label="İddia kimliği"
            />
            <select
              value={t.source_id}
              onChange={(e) => guncelle(i, 'source_id', e.target.value)}
              className="flex-1 px-2 py-1 rounded bg-slate-950 border border-slate-700 text-xs text-slate-200"
              aria-label="Kaynak"
            >
              {YERLESIK_KAYNAKLAR.map((k) => (
                <option key={k.id} value={k.id}>{k.etiket}</option>
              ))}
            </select>
            <button
              onClick={() => sil(i)}
              disabled={taslaklar.length === 1}
              className="p-1.5 rounded hover:bg-slate-800 text-slate-500 hover:text-red-400 disabled:opacity-30"
              aria-label="Kartı sil"
            >
              <Trash2 size={14} />
            </button>
          </div>

          <textarea
            value={t.statement}
            onChange={(e) => guncelle(i, 'statement', e.target.value)}
            rows={2}
            placeholder="İddia: kaynağın söylediği şey (en az 10 karakter)"
            className="w-full px-2 py-1.5 rounded bg-slate-950 border border-slate-700 text-xs text-slate-100 placeholder-slate-600 resize-none"
          />

          <div className="flex items-center gap-2">
            <BookOpen size={13} className="text-slate-500 shrink-0" />
            <input
              value={t.locator}
              onChange={(e) => guncelle(i, 'locator', e.target.value)}
              placeholder="Yer: ör. s. 142, Bölüm 6"
              className="flex-1 px-2 py-1 rounded bg-slate-950 border border-slate-700 text-xs text-slate-100 placeholder-slate-600"
            />
          </div>

          <button
            onClick={() => guncelle(i, 'researcher_verified', !t.researcher_verified)}
            className={`flex items-center gap-2 text-xs px-2 py-1.5 rounded w-full ${
              t.researcher_verified
                ? 'bg-emerald-950/40 text-emerald-300 border border-emerald-800/50'
                : 'bg-slate-950 text-slate-400 border border-slate-700 hover:border-slate-600'
            }`}
          >
            {t.researcher_verified ? <CheckSquare size={14} /> : <Square size={14} />}
            Kaynağı açtım, bu iddiayı belirtilen yerde doğruladım
          </button>
        </div>
      ))}

      <div className="flex items-center justify-between">
        <button
          onClick={ekle}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs"
        >
          <Plus size={13} /> Kart ekle
        </button>
        <span className="text-[11px] text-slate-500">
          {dogrulanan} / {taslaklar.length} kart doğrulandı
        </span>
      </div>
    </div>
  );
}
