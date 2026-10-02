// Akademik Mod — mekânsal (P5 dışı) yol.
//
// NEDEN AYRI YOL: Science GPT'nin P5 yürütücüsü altı tablosal yöntem
// çalıştırır (OLS, lojistik, Poisson, negatif binom, grup karşılaştırması,
// randomize ANCOVA). Getis-Ord Gi*, Global Moran ve LISA orada YOKTUR.
// Bu yöntemler suc_analizi çekirdeğinde koşturulur, sonucu motora devredilir.
//
// DEVREDİLEN ANALİZ P4 ONAYINDAN VE P6 DOĞRULAMASINDAN GEÇMEZ. Bu gizlenmez:
// üretilen taslak bunu kendi metninde beyan eder, kayıtta da işaretlidir.
//
// PPDAC DİSİPLİNİ KORUNUR: her analiz TAZE bir oturumda koşar
// (döngü tek-analiz durum makinesidir) ve fitness gate kararı motora
// devredilen pakete konur — kapı reddettiyse motor kabul etmez.
import { useState, useCallback, useRef, useEffect } from 'react';
import Papa from 'papaparse';
import {
  Upload, Play, Loader2, Check, AlertTriangle, BookOpen, Download, ShieldCheck,
} from 'lucide-react';
import {
  dongurBaslat, dongurVeri, dongurAnalizeGec, dongurAnaliz, BackendError,
  provenansDisDenetim, provenansOzet,
  type FitnessUygunluk, type ProvenansOzeti,
} from '../../lib/sucBridge';
import {
  disYontemler, disAnalizDevret, disMakaleUret, disMakaleArtefaktUrl,
  denetimDogrula, BilimHatasi,
  type DisAnalizKaydi, type DisMakaleSonucu, type KanitKarti,
  type DenetimDogrulama,
} from '../../lib/scienceBridge';
import EvidenceCardEditor from './EvidenceCardEditor';
import { mekansalDevret, devirUyarisi } from '../../lib/mekansalDevir';

type Rows = Record<string, unknown>[];

const ETIKET: Record<string, string> = {
  sicak_nokta_gi: 'Getis-Ord Gi* (sıcak nokta)',
  mekansal_kumelenme: "Global Moran's I (otokorelasyon)",
  yerel_kumeleme: 'Yerel Moran / LISA (küme ve aykırı)',
  wdd_testi: 'WDD (müdahale değerlendirmesi)',
  yukselen_sicak_nokta: 'Emerging Hotspot (uzay-zaman)',
};

// Satır listesiyle çalışamayan yöntemler (elle parametre ister).
const SATIRSIZ = new Set(['wdd_testi']);

interface Props {
  researchId: string;
  onaylayan: string;
  hipotez: string;
}

export default function SpatialPath({ researchId, onaylayan, hipotez }: Props) {
  const [yontemler, setYontemler] = useState<string[]>([]);
  const [rows, setRows] = useState<Rows>([]);
  const [dosyaAdi, setDosyaAdi] = useState('');
  const [secili, setSecili] = useState<string[]>([]);
  const [devredilen, setDevredilen] = useState<DisAnalizKaydi[]>([]);
  const [kartlar, setKartlar] = useState<KanitKarti[]>([]);
  const [makale, setMakale] = useState<DisMakaleSonucu | null>(null);
  const [denetim, setDenetim] = useState<DenetimDogrulama | null>(null);
  const [provenans, setProvenans] = useState<ProvenansOzeti | null>(null);
  const [mesgul, setMesgul] = useState(false);
  const [ilerleme, setIlerleme] = useState('');
  const [hata, setHata] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    disYontemler()
      .then((r) => setYontemler(r.supported_tools.filter((t) => !SATIRSIZ.has(t))))
      .catch(() => setYontemler([]));
  }, []);

  const dosyaSec = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    Papa.parse<Record<string, unknown>>(f, {
      header: true, dynamicTyping: true, skipEmptyLines: true, preview: 5000,
      complete: (res) => {
        setRows(res.data as Rows);
        setDosyaAdi(f.name);
        setDevredilen([]);
        setMakale(null);
      },
    });
  }, []);

  /**
   * Seçilen her yöntemi TAZE bir PPDAC oturumunda koşturur ve motora devreder.
   * Kapı reddederse o yöntem atlanır; sebebi kullanıcıya gösterilir.
   */
  const kosturVeDevret = useCallback(async () => {
    setMesgul(true);
    setHata(null);
    try {
      const sonuc = await mekansalDevret(secili, hipotez || 'mekânsal yoğunlaşma incelemesi', {
        baslat: async (h) => ({ oturumId: (await dongurBaslat(h)).sonuc.oturum_id }),
        veriBagla: async (oid, arac) =>
          (await dongurVeri(oid, rows, arac)).sonuc.uygunluk ?? null,
        analizeGec: async (oid, u) => {
          await dongurAnalizeGec(oid, u as FitnessUygunluk);
        },
        calistir: async (oid, arac) =>
          (await dongurAnaliz(
            oid, arac,
            { hipotez: hipotez || 'mekânsal yoğunlaşma', yorum: 'Akademik Mod mekânsal yol' },
            { satirlar: rows },
          )).sonuc as Record<string, unknown>,
        devret: async (paket) =>
          disAnalizDevret(researchId, { ...paket, veri_adi: dosyaAdi || undefined }),
        ilerleme: setIlerleme,
      });
      // Kabul edilenlerin tam kaydını motordan değil, devir çıktısından
      // biliyoruz; ayrıntı için listeyi yeniden okumak yerine kimlikleri
      // saklıyoruz ve motorun döndürdüğü kayıtları gösteriyoruz.
      setDevredilen(sonuc.kabulEdilen);
      setHata(devirUyarisi(sonuc));
      if (!sonuc.kabulEdilen.length && !sonuc.atlanan.length && !sonuc.hatali.length) {
        setHata('Hiçbir yöntem seçilmedi.');
      }
    } catch (e) {
      if (e instanceof BilimHatasi) setHata(`${e.message} (${e.tip})`);
      else if (e instanceof BackendError) setHata(`${e.message} (${e.tip})`);
      else setHata(String(e));
    } finally {
      setMesgul(false);
      setIlerleme('');
    }
  }, [secili, rows, hipotez, researchId, dosyaAdi]);

  const makaleUret = useCallback(async () => {
    setMesgul(true);
    setHata(null);
    try {
      const r = await disMakaleUret(researchId, {
        external_ids: devredilen.map((d) => d.external_id),
        author_line: onaylayan || '[Yazar adı]',
        use_local_gemma: true,
        evidence_claims: kartlar,
      });
      setMakale(r);
      const dogrulama = await denetimDogrula(researchId);
      setDenetim(dogrulama);
      // PROVENANS DİKİŞİ: akademik çıktının denetim durumunu, analizin
      // yapıldığı PPDAC oturumuna geri yaz. Aksi hâlde oturumdan bakan
      // biri akademik zincirin durumunu göremez.
      for (const oturumId of r.okc_oturum_idleri) {
        try {
          await provenansDisDenetim(
            oturumId, researchId,
            dogrulama as unknown as Record<string, unknown>,
          );
        } catch {
          // Geri yazım başarısızsa makale geçerliliğini yitirmez;
          // yalnız dikiş eksik kalır. Özet bunu zaten kopukluk olarak gösterir.
        }
      }
      if (r.okc_oturum_idleri.length) {
        try {
          setProvenans((await provenansOzet(r.okc_oturum_idleri[0])).sonuc);
        } catch {
          setProvenans(null);
        }
      }
    } catch (e) {
      if (e instanceof BilimHatasi) setHata(`${e.message} (${e.tip})`);
      else setHata(String(e));
    } finally {
      setMesgul(false);
    }
  }, [researchId, devredilen, kartlar, onaylayan]);

  const kutu = 'rounded-lg border border-slate-800 bg-slate-900/50 p-4 space-y-3';
  const btn =
    'px-4 py-1.5 rounded bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white text-xs font-semibold flex items-center gap-1.5';

  return (
    <div className="space-y-4">
      <div className="flex items-start gap-2 text-xs bg-sky-950/40 text-sky-200 border border-sky-800/50 rounded p-2.5">
        <AlertTriangle size={15} className="shrink-0 mt-0.5" />
        <div>
          <div className="font-medium">Mekânsal yol P5 dışıdır.</div>
          <div className="opacity-85">
            Bu yöntemler suç analizi çekirdeğinde koşar. P4 yöntem onayı ve P6
            çapraz doğrulama adımları uygulanmaz; üretilen taslak bunu kendi
            metninde beyan eder.
          </div>
        </div>
      </div>

      {hata && (
        <div className="rounded border border-amber-800/60 bg-amber-950/40 p-2.5 text-xs text-amber-200">
          {hata}
        </div>
      )}

      {/* Veri */}
      <section className={kutu}>
        <div className="text-xs text-slate-300 font-medium">Mekânsal veri</div>
        <p className="text-[11px] text-slate-500">
          Enlem/boylam taşıyan olay kayıtları (CSV). Fitness kapısı geçerli
          koordinat oranını ve örneklem büyüklüğünü sınar.
        </p>
        <div className="flex items-center gap-2">
          <button onClick={() => fileRef.current?.click()} className={btn}>
            <Upload size={13} /> {dosyaAdi || 'CSV yükle'}
          </button>
          <input ref={fileRef} type="file" accept=".csv,.tsv,.txt"
                 onChange={dosyaSec} className="hidden" />
          {rows.length > 0 && (
            <span className="text-[11px] text-slate-500">{rows.length} satır</span>
          )}
        </div>
      </section>

      {/* Yöntem seçimi */}
      {rows.length > 0 && (
        <section className={kutu}>
          <div className="text-xs text-slate-300 font-medium">Yöntemler</div>
          <div className="flex flex-wrap gap-2">
            {yontemler.map((y) => {
              const acik = secili.includes(y);
              return (
                <button
                  key={y}
                  onClick={() =>
                    setSecili((s) => (acik ? s.filter((x) => x !== y) : [...s, y]))
                  }
                  className={`px-2.5 py-1 rounded-full text-xs border ${
                    acik
                      ? 'bg-indigo-600 border-indigo-500 text-white'
                      : 'bg-slate-800 border-slate-700 text-slate-300 hover:border-indigo-500'
                  }`}
                >
                  {acik && <Check size={11} className="inline mr-1" />}
                  {ETIKET[y] ?? y}
                </button>
              );
            })}
          </div>
          <button
            onClick={kosturVeDevret}
            disabled={mesgul || secili.length === 0}
            className={btn}
          >
            {mesgul ? <Loader2 size={13} className="animate-spin" /> : <Play size={13} />}
            {ilerleme || 'Çalıştır ve devret'}
          </button>
        </section>
      )}

      {/* Devredilen analizler */}
      {devredilen.length > 0 && (
        <section className={kutu}>
          <div className="text-xs text-slate-300 font-medium">
            Devredilen analizler ({devredilen.length})
          </div>
          {devredilen.map((d) => (
            <div key={d.external_id} className="rounded bg-slate-950/50 p-2 space-y-1">
              <div className="text-xs text-slate-200">{d.yontem_adi}</div>
              {d.bulgular.map((b, i) => (
                <div key={i} className="text-[11px] text-slate-400">• {b}</div>
              ))}
            </div>
          ))}
        </section>
      )}

      {/* Kanıt kartları + makale */}
      {devredilen.length > 0 && (
        <section className={kutu}>
          <div className="text-xs text-slate-300 font-medium">
            Kanıt kartları ve makale
          </div>
          <EvidenceCardEditor kartlar={kartlar} onDegisti={setKartlar} />
          <button
            onClick={makaleUret}
            disabled={mesgul || kartlar.length === 0}
            className={btn}
          >
            {mesgul ? <Loader2 size={13} className="animate-spin" /> : <BookOpen size={13} />}
            Makale taslağı üret
          </button>
          {kartlar.length === 0 && (
            <div className="text-[11px] text-slate-500">
              En az bir doğrulanmış kanıt kartı gerekir.
            </div>
          )}

          {makale && (
            <div className="space-y-2 pt-2 border-t border-slate-800">
              <div className="text-xs text-emerald-300">
                Taslak üretildi — {makale.grounding_facts.length} olgu
              </div>
              <div className="text-[11px] text-slate-500">
                {makale.manuscript_id} · {makale.generation_mode}
              </div>
              <div className="flex flex-wrap items-center gap-2">
                {['manuscript.md', 'claim_matrix.csv'].map((ad) => (
                  <a
                    key={ad}
                    href={disMakaleArtefaktUrl(researchId, makale.manuscript_id, ad)}
                    target="_blank"
                    rel="noreferrer"
                    className="flex items-center gap-1.5 px-3 py-1.5 rounded bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs"
                  >
                    <Download size={13} /> {ad}
                  </a>
                ))}
                {denetim && (
                  <span
                    className={`flex items-center gap-1.5 text-xs px-2 py-1 rounded ${
                      denetim.valid
                        ? 'bg-emerald-950/40 text-emerald-300'
                        : 'bg-red-950/40 text-red-300'
                    }`}
                  >
                    <ShieldCheck size={13} />
                    {denetim.valid
                      ? `Denetim zinciri geçerli (${denetim.event_count} olay)`
                      : 'Denetim zinciri doğrulanamadı'}
                  </span>
                )}
              </div>
              <div className="text-[11px] text-amber-400/80">
                Taslak P4 onayı ve P6 doğrulaması olmadan üretilmiştir; insan
                incelemesi zorunludur.
              </div>

              {provenans && (
                <div className="rounded bg-slate-950/60 p-2.5 space-y-1.5">
                  <div className="text-[11px] text-slate-300 font-medium">
                    Kaynak zinciri
                  </div>
                  {provenans.halkalar.map((h) => (
                    <div key={h.halka} className="flex items-start gap-2 text-[11px]">
                      <span
                        className={
                          'px-1.5 py-0.5 rounded shrink-0 ' +
                          (h.kanit_turu === 'makine'
                            ? 'bg-emerald-950/50 text-emerald-300'
                            : h.kanit_turu === 'beyan'
                              ? 'bg-amber-950/50 text-amber-300'
                              : 'bg-slate-800 text-slate-500')
                        }
                      >
                        {h.kanit_turu}
                      </span>
                      <span className="text-slate-400">
                        <b className="text-slate-300">{h.halka}</b> — {h.ozet}
                      </span>
                    </div>
                  ))}
                  <div className="text-[10px] text-slate-500 pt-1 border-t border-slate-800">
                    &quot;beyan&quot; halkası makineyle doğrulanamaz; araştırmacı
                    sorumluluğundadır.
                  </div>
                </div>
              )}
            </div>
          )}
        </section>
      )}
    </div>
  );
}
