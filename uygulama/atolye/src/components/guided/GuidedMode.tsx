// Rehberli Mod — düz metin görevden sonuca, node tuvali görmeden.
//
// FR3 vizyonunun DataFlow üzerindeki uygulaması. Node tuvaliyle aynı
// suc_analizi backend'ini (dongu_* ailesi) paylaşır; kullanıcı oturum/graf
// kavramını görmez. Üç öncelik tek akışta:
//   1) Görev girişi     → dongu_baslat (öneri motoru)
//   2) Veri + fitness    → dongu_veri
//   3) Analiz + kanıt    → dongu_analiz + muhakeme_izi / kanit_dogrula
import { useState, useCallback, useRef } from 'react';
import Papa from 'papaparse';
import { X, Wand2, Upload, ShieldCheck, ShieldAlert, ScrollText, Loader2, AlertTriangle, ArrowRight } from 'lucide-react';
import { useStore } from '../../store/useStore';
import { LOGIN_PATH } from '../../const';
import {
  dongurBaslat, dongurVeri, dongurAnalizeGec, dongurAnaliz,
  muhakemeIzi, kanitDogrula, analizOner, BackendError,
  type DonguBaslatSonuc, type FitnessProfil, type FitnessUygunluk, type KanitDogrulaSonuc,
  type OneriKalem,
} from '../../lib/sucBridge';
import BackendErrorCard from './BackendErrorCard';
import GuidedResult from './GuidedResult';

const aracEtiket = (arac: string) => arac.replace(/_/g, ' ');

type Rows = Record<string, unknown>[];

export default function GuidedMode() {
  const guidedOpen = useStore((s) => s.guidedOpen);
  const setGuidedOpen = useStore((s) => s.setGuidedOpen);
  const setAcademicOpen = useStore((s) => s.setAcademicOpen);
  const setAcademicDevir = useStore((s) => s.setAcademicDevir);

  // Ön-kayıt niyeti. İşaretlenmişse akademik devir VERİ YÜKLENMEDEN yapılır;
  // sıra bu yüzden önemlidir — veriye bakıp sonra hipotez yazmak HARKing'dir.
  const [akademikNiyet, setAkademikNiyet] = useState(false);
  const [gorev, setGorev] = useState('');
  const [plan, setPlan] = useState<DonguBaslatSonuc | null>(null);
  const [rows, setRows] = useState<Rows>([]);
  const [dosyaAdi, setDosyaAdi] = useState('');
  // Profil yüklemede alınır (analizden bağımsız); uygunluk ise SEÇİLEN analize
  // göre belirlenir (dongu_veri uygunluğu yalnız 'analiz' verilince döndürür).
  const [profil, setProfil] = useState<FitnessProfil | null>(null);
  const [uygunluk, setUygunluk] = useState<FitnessUygunluk | null>(null);
  // Veri yüklendikten sonra data-aware öneriler (analiz_oner); keyword planın
  // yerine geçer çünkü dosyanın GERÇEK yapısını bilir.
  const [dataOneriler, setDataOneriler] = useState<OneriKalem[] | null>(null);
  const [seciliAnaliz, setSeciliAnaliz] = useState<string | null>(null);
  // Her analiz kendi PPDAC oturumunu kullanır (döngü tek-analiz durum makinesi);
  // kanıt eylemleri bu aktif oturuma referans verir.
  const [aktifOturum, setAktifOturum] = useState<string | null>(null);
  const [sonuc, setSonuc] = useState<Record<string, unknown> | null>(null);
  const [kanitDurumu, setKanitDurumu] = useState<string | null>(null);
  const [iz, setIz] = useState<string | null>(null);
  const [rozet, setRozet] = useState<KanitDogrulaSonuc | null>(null);
  const [hata, setHata] = useState<BackendError | null>(null);
  const [mesgul, setMesgul] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);

  const sifirla = useCallback(() => {
    setPlan(null); setRows([]); setDosyaAdi(''); setProfil(null); setUygunluk(null);
    setSeciliAnaliz(null); setAktifOturum(null); setSonuc(null); setKanitDurumu(null);
    setIz(null); setRozet(null); setHata(null); setDataOneriler(null);
  }, []);

  const calis = useCallback(async <T,>(fn: () => Promise<T>): Promise<T | undefined> => {
    setMesgul(true); setHata(null);
    try {
      return await fn();
    } catch (e) {
      if (e instanceof BackendError) setHata(e);
      else setHata(new BackendError('sistem', String(e)));
      return undefined;
    } finally {
      setMesgul(false);
    }
  }, []);

  // 1) Görev → plan (öneriler)
  const gorevGonder = useCallback(async () => {
    const g = gorev.trim();
    if (!g) return;
    sifirla();
    const r = await calis(() => dongurBaslat(g));
    if (r) setPlan(r.sonuc);
  }, [gorev, calis, sifirla]);

  // 2) Dosya → satırları çöz+sakla (backend çağrısı YOK; PPDAC döngüsü tek
  //    dongu_veri kabul ettiğinden veri, analiz çalıştırılırken bağlanır)
  const dosyaSec = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    Papa.parse<Record<string, unknown>>(file, {
      header: true, dynamicTyping: true, skipEmptyLines: true, preview: 5000,
      complete: async (res) => {
        const parsed = res.data as Rows;
        setRows(parsed); setDosyaAdi(file.name);
        setProfil(null); setUygunluk(null); setSonuc(null); setSeciliAnaliz(null);
        // Veri yapısına göre data-aware öneriler (keyword planın yerine geçer)
        const r = await calis(() => analizOner(parsed, gorev || undefined));
        if (r) setDataOneriler(r.sonuc.oneriler);
      },
    });
  }, [calis, gorev]);

  // 3) Önerilen analizi çalıştır: TAZE oturum → veri+fitness → gate → analiz.
  //    PPDAC oturumu tek-analizdir; her çalıştırma kendi oturumunu kurar.
  const analizCalistir = useCallback(async (arac: string) => {
    if (rows.length === 0) return;
    setSeciliAnaliz(arac); setSonuc(null); setUygunluk(null); setIz(null); setRozet(null);
    const r = await calis(async () => {
      const bas = await dongurBaslat(gorev);
      const oid = bas.sonuc.oturum_id;
      setAktifOturum(oid);
      const veri = await dongurVeri(oid, rows, arac);
      setProfil(veri.sonuc.profil ?? null);
      const uyg = veri.sonuc.uygunluk ?? null;
      setUygunluk(uyg);
      if (!uyg || !uyg.uygun) {
        throw new BackendError(
          'kapi',
          'Bu analizin ön koşulu karşılanmadı: ' + (uyg?.sebepler?.join('; ') ?? 'veri uygun değil'),
        );
      }
      await dongurAnalizeGec(oid, uyg);
      return dongurAnaliz(
        oid, arac,
        { hipotez: gorev, yorum: 'Rehberli mod otomatik çalıştırma' },
        { satirlar: rows },
      );
    });
    if (r) {
      setSonuc(r.sonuc);
      setKanitDurumu(r.meta.kanit_durumu ?? null);
    }
  }, [rows, gorev, calis]);

  const izGoster = useCallback(async () => {
    if (!aktifOturum) return;
    const r = await calis(() => muhakemeIzi(aktifOturum));
    if (r) setIz(r.sonuc.urun);
  }, [aktifOturum, calis]);

  const zinciriDogrula = useCallback(async () => {
    if (!aktifOturum) return;
    const r = await calis(() => kanitDogrula(aktifOturum));
    if (r) setRozet(r.sonuc);
  }, [aktifOturum, calis]);

  if (!guidedOpen) return null;

  return (
    <div className="fixed inset-0 z-40 bg-slate-950 flex flex-col" role="dialog" aria-label="Rehberli Mod">
      {/* Üst çubuk */}
      <div className="flex items-center justify-between px-5 py-3 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <Wand2 size={18} className="text-indigo-400" />
          <span className="text-sm font-semibold text-slate-100">Rehberli Mod</span>
          <span className="text-[11px] text-slate-500">— düz metin görev, otomatik analiz</span>
        </div>
        <button onClick={() => setGuidedOpen(false)} className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-white" aria-label="Kapat">
          <X size={18} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-4 max-w-3xl w-full mx-auto space-y-4">
        {/* Adım 1: Görev */}
        <section>
          <label className="block text-xs text-slate-400 mb-1.5">1. Ne öğrenmek istiyorsunuz?</label>
          <div className="flex gap-2">
            <textarea
              value={gorev}
              onChange={(e) => setGorev(e.target.value)}
              onKeyDown={(e) => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) gorevGonder(); }}
              rows={2}
              placeholder="ör. köylere göre olay yoğunluğu nerede toplanıyor?"
              className="flex-1 px-3 py-2 rounded bg-slate-900 border border-slate-700 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:border-indigo-500 resize-none"
            />
            <button
              onClick={gorevGonder}
              disabled={mesgul || !gorev.trim()}
              className="px-4 rounded bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white text-sm font-semibold flex items-center gap-1.5"
            >
              {mesgul && !plan ? <Loader2 size={15} className="animate-spin" /> : <Wand2 size={15} />}
              Öner
            </button>
          </div>

          {/* Ön-kayıt kapısı — akademik yayın niyeti */}
          <div className="mt-2 space-y-2">
            <label className="flex items-center gap-2 text-[11px] text-slate-400 cursor-pointer select-none">
              <input
                type="checkbox"
                checked={akademikNiyet}
                onChange={(e) => setAkademikNiyet(e.target.checked)}
                className="accent-violet-500"
              />
              Bu çalışmayı akademik olarak yayınlamayı düşünüyorum
            </label>

            {akademikNiyet && (
              <div className="rounded border border-violet-800/50 bg-violet-950/30 p-2.5 space-y-2">
                {rows.length > 0 ? (
                  <div className="text-[11px] text-amber-300">
                    Veri zaten yüklendi. Bu noktadan sonra alınacak kilit ön-kayıt sayılmaz;
                    çalışma <b>keşifsel</b> olarak etiketlenir ve doğrulayıcı yorum yapılamaz.
                  </div>
                ) : (
                  <div className="text-[11px] text-violet-200/80">
                    Doğrulayıcı çalışma için protokol <b>veri yüklenmeden önce</b> kilitlenmelidir.
                    Şimdi geçerseniz sıra korunur.
                  </div>
                )}
                <button
                  onClick={() => {
                    setAcademicDevir({ hipotez: gorev.trim() || undefined });
                    setGuidedOpen(false);
                    setAcademicOpen(true);
                  }}
                  className="px-3 py-1.5 rounded bg-violet-600 hover:bg-violet-500 text-white text-xs font-semibold"
                >
                  Akademik Mod'a geç
                </button>
              </div>
            )}
          </div>
        </section>

        {hata && (
          <BackendErrorCard
            hata={hata}
            onEylem={() => {
              // 'kimlik': oturum eksik — kartı kapatmak sorunu çözmez, aynı
              // 401 bir sonraki denemede tekrar döner. Gerçek çıkış: girişe git.
              if (hata.tip === 'kimlik') { window.location.href = LOGIN_PATH; return; }
              setHata(null);
            }}
          />
        )}

        {/* Adım 2: Öneriler + veri */}
        {plan && (
          <section className="rounded-lg border border-slate-800 bg-slate-900/50 p-4 space-y-3">
            <div className="text-xs text-slate-400">
              <span className="text-slate-300 font-medium">Önerilen analizler</span>
              <span className="ml-2 text-slate-500">— {plan.plan.hedef_kitle}</span>
            </div>
            <p className="text-[11px] text-slate-500 italic">{plan.plan.not}</p>

            {/* Veri yükleme */}
            <div className="flex items-center gap-2">
              <button
                onClick={() => fileRef.current?.click()}
                className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs"
              >
                <Upload size={13} /> {dosyaAdi || 'CSV yükle'}
              </button>
              <input ref={fileRef} type="file" accept=".csv,.tsv,.txt" onChange={dosyaSec} className="hidden" />
              {rows.length > 0 && <span className="text-[11px] text-slate-500">{rows.length} satır</span>}
            </div>

            {/* Profil özeti (yüklemede; analizden bağımsız) */}
            {profil && (
              <div className="text-[11px] text-slate-400 bg-slate-950/40 rounded p-2">
                <span className="text-slate-300">Profil:</span> {profil.n ?? rows.length} kayıt
                {(profil.uyarilar?.length ?? 0) > 0 && <span className="text-amber-400"> · {profil.uyarilar!.join('; ')}</span>}
              </div>
            )}

            {/* Uygunluk rozeti (SEÇİLEN analize özel) */}
            {uygunluk && (
              <div className={`flex items-start gap-2 text-xs rounded p-2 ${uygunluk.uygun ? 'bg-emerald-950/40 text-emerald-300' : 'bg-amber-950/40 text-amber-300'}`}>
                {uygunluk.uygun ? <ShieldCheck size={15} className="mt-0.5 shrink-0" /> : <ShieldAlert size={15} className="mt-0.5 shrink-0" />}
                <div>
                  <div className="font-medium">{uygunluk.uygun ? `Veri ${seciliAnaliz} için uygun` : 'Bu analiz için uygun değil'}</div>
                  <div className="opacity-80">{(uygunluk.sebepler ?? []).join('; ')}</div>
                </div>
              </div>
            )}

            {/* Öneriler: veri yüklendiyse data-aware (analiz_oner), yoksa keyword plan */}
            {dataOneriler ? (
              <div className="space-y-1.5">
                <div className="text-[11px] text-slate-500">Veri yapısına göre öneriler (karar ağacı):</div>
                {dataOneriler.map((o, i) => (
                  <div key={i} className="flex items-start gap-2">
                    <button
                      onClick={() => o.arac && analizCalistir(o.arac)}
                      disabled={mesgul || !o.mevcut || !o.arac}
                      title={o.mevcut ? `${o.arac} çalıştır` : 'Bu sürümde yok'}
                      className={`flex items-center gap-1 px-2.5 py-1 rounded-full text-xs border transition-all shrink-0 ${
                        !o.mevcut ? 'bg-slate-900 border-slate-800 text-slate-600 cursor-not-allowed'
                          : seciliAnaliz === o.arac ? 'bg-indigo-600 border-indigo-500 text-white'
                            : 'bg-slate-800 border-slate-700 text-slate-300 hover:border-indigo-500'
                      }`}
                    >
                      {o.analiz} {o.mevcut ? <ArrowRight size={11} /> : <span className="text-[9px]">(yok)</span>}
                    </button>
                    <div className="text-[10px] text-slate-500 pt-1">
                      {o.gerekce}
                      {o.uyari && <span className="text-amber-500/80"> · ⚠ {o.uyari}</span>}
                      <span className="text-slate-600"> [{o.kaynak_kural}]</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="flex flex-wrap gap-2">
                {plan.plan.onerilen.map((arac) => (
                  <button
                    key={arac}
                    onClick={() => analizCalistir(arac)}
                    disabled={mesgul || rows.length === 0}
                    title={rows.length === 0 ? 'Önce CSV yükleyin' : `${arac} çalıştır`}
                    className={`flex items-center gap-1 px-2.5 py-1 rounded-full text-xs border transition-all disabled:opacity-40 ${
                      seciliAnaliz === arac ? 'bg-indigo-600 border-indigo-500 text-white' : 'bg-slate-800 border-slate-700 text-slate-300 hover:border-indigo-500'
                    }`}
                  >
                    {aracEtiket(arac)} <ArrowRight size={11} />
                  </button>
                ))}
              </div>
            )}
          </section>
        )}

        {/* Adım 3: Sonuç */}
        {sonuc && (
          <section className="rounded-lg border border-slate-800 bg-slate-900/50 p-4 space-y-3">
            {kanitDurumu === 'YAZILAMADI' && (
              <div className="flex items-center gap-2 text-xs bg-orange-950/50 text-orange-300 border border-orange-800/60 rounded p-2">
                <AlertTriangle size={15} className="shrink-0" />
                Bu oturumun kanıt kaydı diske yazılamadı; sonuçlar geçerlidir ancak denetim izi eksiktir.
              </div>
            )}
            <div className="text-xs text-slate-400 font-medium">Sonuç — {seciliAnaliz}</div>
            <GuidedResult arac={seciliAnaliz ?? ''} sonuc={sonuc} />

            {/* Kanıt eylemleri */}
            <div className="flex flex-wrap items-center gap-2 pt-1">
              <button onClick={izGoster} disabled={mesgul} className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs disabled:opacity-40">
                <ScrollText size={13} /> Muhakeme izini göster
              </button>
              <button onClick={zinciriDogrula} disabled={mesgul} className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs disabled:opacity-40">
                <ShieldCheck size={13} /> Kanıt zincirini doğrula
              </button>
              {rozet && (
                <span className={`text-xs px-2 py-1 rounded ${rozet.saglam ? 'bg-emerald-950/40 text-emerald-300' : 'bg-red-950/40 text-red-300'}`}>
                  {rozet.saglam ? `✔ Zincir sağlam (${rozet.olay_sayisi} adım)` : '⚠ Zincir doğrulanamadı'}
                </span>
              )}
            </div>

            {iz && (
              <pre className="text-[11px] text-slate-300 bg-slate-950 rounded p-3 overflow-x-auto max-h-72 whitespace-pre-wrap">{iz}</pre>
            )}
          </section>
        )}
      </div>
    </div>
  );
}
