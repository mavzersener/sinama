// Hata taksonomisi kartı — backend hata tipine göre kullanıcı dostu mesaj +
// doğru eylem düğmesi (FR3 §D.2). Ham "HATA [" öneki veya araç/parametre adı
// kullanıcıya asla gösterilmez; yalnız tip rozeti + anlaşılır Türkçe.
//
// Tailwind JIT dinamik olarak kurulan sınıf adlarını (`bg-${x}-900`) purge
// eder; bu yüzden her tip için TAM sınıf dizeleri statik olarak yazılır.
import { AlertCircle } from 'lucide-react';
import type { BackendError, BackendErrorTip } from '../../lib/sucBridge';

interface TipStil {
  baslik: string;
  eylem: string;
  kart: string;
  ikon: string;
  rozet: string;
  buton: string;
}

const TIP_STIL: Record<BackendErrorTip, TipStil> = {
  veri: {
    baslik: 'Veride eksik veya bozuk alan var', eylem: 'Veri özetini göster',
    kart: 'border-amber-800/60 bg-amber-950/40', ikon: 'text-amber-400',
    rozet: 'bg-amber-900/60 text-amber-300', buton: 'bg-amber-800/60 hover:bg-amber-700/60 text-amber-100',
  },
  guvenlik: {
    baslik: 'Dosya güvenlik sınırları dışında', eylem: 'Dosyayı güvenli alana kopyala',
    kart: 'border-red-800/60 bg-red-950/40', ikon: 'text-red-400',
    rozet: 'bg-red-900/60 text-red-300', buton: 'bg-red-800/60 hover:bg-red-700/60 text-red-100',
  },
  kullanim: {
    baslik: 'İstek biçimi hatalı', eylem: 'Ayarları gözden geçir',
    kart: 'border-sky-800/60 bg-sky-950/40', ikon: 'text-sky-400',
    rozet: 'bg-sky-900/60 text-sky-300', buton: 'bg-sky-800/60 hover:bg-sky-700/60 text-sky-100',
  },
  kapi: {
    baslik: 'Bu analizin ön koşulu karşılanmadı', eylem: 'Ön analizi çalıştır',
    kart: 'border-violet-800/60 bg-violet-950/40', ikon: 'text-violet-400',
    rozet: 'bg-violet-900/60 text-violet-300', buton: 'bg-violet-800/60 hover:bg-violet-700/60 text-violet-100',
  },
  dongu: {
    baslik: 'Oturum durumu bu işleme uygun değil', eylem: 'Oturum durumunu göster',
    kart: 'border-orange-800/60 bg-orange-950/40', ikon: 'text-orange-400',
    rozet: 'bg-orange-900/60 text-orange-300', buton: 'bg-orange-800/60 hover:bg-orange-700/60 text-orange-100',
  },
  sistem: {
    baslik: 'Beklenmeyen bir iç hata oluştu', eylem: 'Yeniden dene',
    kart: 'border-red-800/60 bg-red-950/40', ikon: 'text-red-400',
    rozet: 'bg-red-900/60 text-red-300', buton: 'bg-red-800/60 hover:bg-red-700/60 text-red-100',
  },
  // İstemciye özel: backend hiç üretmez (bkz. sucBridge.ts). Sunucu taraflı
  // analiz oturum ister; 'guvenlik' (dosya sınırı) ile karışmasın diye ayrı.
  kimlik: {
    baslik: 'Sunucu taraflı analiz oturum ister', eylem: 'Giriş yap',
    kart: 'border-sky-800/60 bg-sky-950/40', ikon: 'text-sky-400',
    rozet: 'bg-sky-900/60 text-sky-300', buton: 'bg-sky-800/60 hover:bg-sky-700/60 text-sky-100',
  },
};

export default function BackendErrorCard({ hata, onEylem }: { hata: BackendError; onEylem?: () => void }) {
  const s = TIP_STIL[hata.tip] ?? TIP_STIL.sistem;
  return (
    <div className={`rounded-lg border p-3 ${s.kart}`} role="alert">
      <div className="flex items-start gap-2">
        <AlertCircle size={16} className={`mt-0.5 shrink-0 ${s.ikon}`} />
        <div className="flex-1 min-w-0">
          {/* Kategori üst-etiketi (küçük) + tip rozeti */}
          <div className="flex items-center gap-2">
            <span className="text-[10px] uppercase tracking-wide text-slate-400">{s.baslik}</span>
            <span className={`text-[10px] uppercase tracking-wide px-1.5 py-0.5 rounded ${s.rozet}`}>{hata.tip}</span>
          </div>
          {/* Backend'in ürettiği anlaşılır mesaj = ana başlık (her tip için doğru) */}
          <p className="text-xs font-semibold text-slate-100 mt-1">{hata.message}</p>
          {hata.oneri && <p className="text-[11px] text-slate-400 mt-0.5">{hata.oneri}</p>}
          <button onClick={onEylem} className={`mt-2 text-xs px-2.5 py-1 rounded font-medium ${s.buton}`}>
            {s.eylem}
          </button>
        </div>
      </div>
    </div>
  );
}
