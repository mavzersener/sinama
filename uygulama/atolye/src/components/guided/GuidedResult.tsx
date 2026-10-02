// Rehberli Mod sonuç görselleştirmesi — araç çıktısını haritaya/bara/tabloya
// çevirir (ham JSON yerine). Şekil algılama guidedResultShape'te (saf/test).
import {
  ScatterChart, Scatter, BarChart, Bar, XAxis, YAxis, ZAxis,
  CartesianGrid, Tooltip, ResponsiveContainer, Cell,
} from 'recharts';
import { sonucGorseli } from '../../lib/guidedResultShape';

const RENK = '#dc2626';
const IZGARA = '#334155';
const EKSEN = '#94a3b8';

export default function GuidedResult({ arac, sonuc }: { arac: string; sonuc: unknown }) {
  const plan = sonucGorseli(arac, sonuc);

  return (
    <div className="space-y-2">
      <div className="text-xs text-slate-400 font-medium">{plan.baslik}</div>

      {plan.tip === 'harita' && plan.harita && (
        <ResponsiveContainer width="100%" height={280}>
          <ScatterChart margin={{ top: 10, right: 10, bottom: 10, left: 0 }}>
            <CartesianGrid stroke={IZGARA} />
            <XAxis type="number" dataKey="lon" name="Boylam" stroke={EKSEN} tick={{ fontSize: 10 }} domain={['dataMin', 'dataMax']} />
            <YAxis type="number" dataKey="lat" name="Enlem" stroke={EKSEN} tick={{ fontSize: 10 }} domain={['dataMin', 'dataMax']} />
            <ZAxis type="number" dataKey="adet" range={[30, 400]} name="Olay" />
            <Tooltip cursor={{ strokeDasharray: '3 3' }} contentStyle={{ background: '#0f172a', border: '1px solid #334155', fontSize: 11 }} />
            <Scatter data={plan.harita} fill={RENK} fillOpacity={0.6} />
          </ScatterChart>
        </ResponsiveContainer>
      )}

      {plan.tip === 'bar' && plan.bar && (
        <ResponsiveContainer width="100%" height={Math.min(320, 60 + plan.bar.length * 26)}>
          <BarChart data={plan.bar} layout="vertical" margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
            <CartesianGrid stroke={IZGARA} horizontal={false} />
            <XAxis type="number" stroke={EKSEN} tick={{ fontSize: 10 }} />
            <YAxis type="category" dataKey="ad" stroke={EKSEN} tick={{ fontSize: 10 }} width={90} />
            <Tooltip contentStyle={{ background: '#0f172a', border: '1px solid #334155', fontSize: 11 }} cursor={{ fill: '#1e293b55' }} />
            <Bar dataKey="deger" radius={[0, 3, 3, 0]}>
              {plan.bar.map((_, i) => <Cell key={i} fill={RENK} fillOpacity={0.85} />)}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      )}

      {plan.tip === 'json' && (
        <pre className="text-[11px] text-slate-300 bg-slate-950 rounded p-3 overflow-x-auto max-h-64">
          {JSON.stringify(sonuc, null, 2)}
        </pre>
      )}
    </div>
  );
}
