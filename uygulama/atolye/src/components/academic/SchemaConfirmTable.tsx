// Şema onay tablosu — Akademik Mod'un ikinci insan onayı adımı.
//
// Motorun çıkardığı şema `advisory_only`dir: ÖNERİdir, karar değil. Değişken
// türü ve rolü yanlışsa tüm analiz yanlış olur (sayım verisini sürekli sanmak,
// sonucu yordayıcı sanmak gibi). Bu yüzden motor toptan onayı kabul etmez —
// her değişken için tür, rol ve GEREKÇE ister.
//
// Gerekçe alanı çıkarım açıklamasıyla ön-doldurulur ama düzenlenebilir:
// araştırmacı motorun gerekçesini devralıyorsa bu bilinçli bir tercihtir,
// boş bırakılamaz (motor en az 3 karakter dayatır).
import { useState, useEffect } from 'react';
import { AlertTriangle, Eye } from 'lucide-react';
import {
  DEGISKEN_TURLERI, DEGISKEN_ROLLERI,
  type CikarilmisSema, type DegiskenOnayi, type DegiskenTuru, type DegiskenRolu,
} from '../../lib/scienceBridge';

interface Props {
  sema: CikarilmisSema;
  onDegisti: (onaylar: DegiskenOnayi[]) => void;
}

export default function SchemaConfirmTable({ sema, onDegisti }: Props) {
  const [onaylar, setOnaylar] = useState<DegiskenOnayi[]>([]);

  // Çıkarımdan başla; kullanıcı buradan değiştirir.
  useEffect(() => {
    const baslangic = sema.variables.map((v) => ({
      name: v.name,
      confirmed_type: v.inferred_type,
      role: v.inferred_role,
      rationale: v.reason.slice(0, 2000),
    }));
    setOnaylar(baslangic);
    onDegisti(baslangic);
    // sema değiştiğinde yeniden kur; onDegisti kimliği değişse de tetikleme.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [sema]);

  const guncelle = (i: number, alan: keyof DegiskenOnayi, deger: string) => {
    const yeni = onaylar.map((o, j) => (j === i ? { ...o, [alan]: deger } : o));
    setOnaylar(yeni);
    onDegisti(yeni);
  };

  const secim = 'px-1.5 py-1 rounded bg-slate-950 border border-slate-700 text-[11px] text-slate-200';

  return (
    <div className="space-y-2">
      <div className="flex items-start gap-2 text-[11px] text-slate-400 bg-slate-950/60 rounded p-2">
        <Eye size={13} className="shrink-0 mt-0.5" />
        <div>
          {sema.interpretation_note}
          {sema.advisory_only && (
            <div className="text-slate-500 mt-0.5">
              Aşağıdaki değerler motorun ÖNERİSİdir; onaylayan sizsiniz.
            </div>
          )}
        </div>
      </div>

      <div className="space-y-2 max-h-96 overflow-y-auto pr-1">
        {sema.variables.map((v, i) => {
          const o = onaylar[i];
          if (!o) return null;
          const degisti =
            o.confirmed_type !== v.inferred_type || o.role !== v.inferred_role;
          return (
            <div
              key={v.name}
              className={`rounded border p-2 space-y-1.5 ${
                degisti ? 'border-violet-700/60 bg-violet-950/20' : 'border-slate-800 bg-slate-900/40'
              }`}
            >
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-xs text-slate-100 font-medium">{v.name}</span>
                <span className="text-[10px] text-slate-500">{v.source_dtype}</span>
                {v.sensitive_field_hint && (
                  <span className="flex items-center gap-1 text-[10px] px-1.5 py-0.5 rounded bg-amber-950/50 text-amber-300">
                    <AlertTriangle size={9} /> hassas alan olabilir
                  </span>
                )}
                {v.missing_rate > 0 && (
                  <span className="text-[10px] text-slate-500">
                    eksik %{Math.round(v.missing_rate * 100)}
                  </span>
                )}
                <span className="text-[10px] text-slate-600 ml-auto">
                  güven {Math.round(v.confidence * 100)}%
                </span>
              </div>

              <div className="flex items-center gap-1.5 flex-wrap">
                <select
                  value={o.confirmed_type}
                  onChange={(e) => guncelle(i, 'confirmed_type', e.target.value as DegiskenTuru)}
                  className={secim}
                  aria-label={`${v.name} türü`}
                >
                  {DEGISKEN_TURLERI.map((t) => (
                    <option key={t} value={t}>{t}</option>
                  ))}
                </select>
                <select
                  value={o.role}
                  onChange={(e) => guncelle(i, 'role', e.target.value as DegiskenRolu)}
                  className={secim}
                  aria-label={`${v.name} rolü`}
                >
                  {DEGISKEN_ROLLERI.map((r) => (
                    <option key={r} value={r}>{r}</option>
                  ))}
                </select>
                {degisti && (
                  <span className="text-[10px] text-violet-300">
                    çıkarım: {v.inferred_type} / {v.inferred_role}
                  </span>
                )}
              </div>

              <input
                value={o.rationale}
                onChange={(e) => guncelle(i, 'rationale', e.target.value)}
                placeholder="Gerekçe (en az 3 karakter)"
                className="w-full px-2 py-1 rounded bg-slate-950 border border-slate-700 text-[11px] text-slate-200 placeholder-slate-600"
                aria-label={`${v.name} gerekçesi`}
              />
            </div>
          );
        })}
      </div>
    </div>
  );
}
