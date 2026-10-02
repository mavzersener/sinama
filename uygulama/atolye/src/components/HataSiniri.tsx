import { Component, type ErrorInfo, type ReactNode } from 'react';
import { AlertTriangle, RotateCcw, X } from 'lucide-react';
import { useStore } from '../store/useStore';

/**
 * Hata sınırı: bir bölgedeki render hatası yalnız o bölgeyi düşürür.
 *
 * Sınır yokken React tek bir bileşen hatasında TÜM ağacı söküyordu (ör.
 * Rehberli Mod'da beklenmedik bir sonuç biçimi bütün uygulamayı boş ekrana
 * çevirmişti). Sınır hatayı yakalar, bölgenin yerine açıklayıcı bir kart
 * koyar ve hatayı Günlük sekmesine yazar; tuval ve diğer paneller çalışmaya
 * devam eder.
 *
 * - `sifirlaAnahtari` değişince sınır kendiliğinden sıfırlanır (ör. özellik
 *   paneli başka bir düğüm seçilince yeniden dener).
 * - `kapat` verilirse kartta "Kapat" düğmesi çıkar (kaplamalar: Rehberli
 *   Mod, Akademik Mod — açık bayrağı kapatılıp sınır sıfırlanır).
 * - Sınır olay işleyicilerindeki ve async koddaki hataları YAKALAMAZ (React
 *   kuralı); onlar zaten ağacı sökmez.
 */

interface Ozellikler {
  bolge: string;
  children: ReactNode;
  sifirlaAnahtari?: unknown;
  kapat?: () => void;
  kompakt?: boolean;
  /** Sabit konumlu kaplama bölgesi: yedek kart ekranın üstünde görünür. */
  kaplama?: boolean;
}

interface Durum {
  hata: Error | null;
}

export class HataSiniri extends Component<Ozellikler, Durum> {
  state: Durum = { hata: null };

  static getDerivedStateFromError(hata: unknown): Durum {
    return { hata: hata instanceof Error ? hata : new Error(String(hata)) };
  }

  componentDidCatch(hata: unknown, bilgi: ErrorInfo) {
    const ileti = hata instanceof Error ? hata.message : String(hata);
    console.error(`[hata-sınırı:${this.props.bolge}]`, hata, bilgi.componentStack);
    try {
      useStore.getState().addLog(`Arayüz hatası (${this.props.bolge}): ${ileti}`);
    } catch {
      /* günlük yazılamasa da yedek kart gösterilir */
    }
  }

  componentDidUpdate(onceki: Ozellikler) {
    if (this.state.hata && !Object.is(onceki.sifirlaAnahtari, this.props.sifirlaAnahtari)) {
      this.setState({ hata: null });
    }
  }

  sifirla = () => this.setState({ hata: null });

  kapatVeSifirla = () => {
    this.props.kapat?.();
    this.setState({ hata: null });
  };

  render() {
    const { hata } = this.state;
    if (!hata) return this.props.children;
    const { bolge, kapat, kompakt, kaplama } = this.props;
    const konum = kaplama ? 'fixed top-16 left-1/2 -translate-x-1/2 z-[60] w-[28rem] max-w-[90vw] shadow-xl bg-red-950' : 'bg-red-950/40';
    return (
      <div
        role="alert"
        className={`${kompakt ? 'm-1 p-2' : 'm-3 p-3'} rounded border border-red-800/60 ${konum} text-red-200`}
      >
        <div className="flex items-center gap-2 text-xs font-medium">
          <AlertTriangle size={14} className="text-red-400 shrink-0" />
          <span>{bolge} bir hata nedeniyle gösterilemiyor.</span>
        </div>
        <div className="mt-1 text-[10px] text-red-300/80 font-mono break-all">
          {hata.message.slice(0, 300) || hata.name}
        </div>
        {!kompakt && (
          <div className="mt-1 text-[10px] text-slate-400">
            Uygulamanın geri kalanı çalışıyor. Ayrıntı Günlük sekmesinde ve tarayıcı konsolunda.
          </div>
        )}
        <div className="mt-2 flex gap-2">
          <button
            type="button"
            onClick={this.sifirla}
            className="flex items-center gap-1 px-2 py-1 text-[10px] rounded bg-slate-800 hover:bg-slate-700 text-slate-200"
          >
            <RotateCcw size={11} /> Yeniden dene
          </button>
          {kapat && (
            <button
              type="button"
              onClick={this.kapatVeSifirla}
              className="flex items-center gap-1 px-2 py-1 text-[10px] rounded bg-slate-800 hover:bg-slate-700 text-slate-200"
            >
              <X size={11} /> Kapat
            </button>
          )}
        </div>
      </div>
    );
  }
}
