// Akademik Mod — PPDAC çalışmasından denetlenebilir makale taslağına.
//
// NEDEN SİHİRBAZ, NODE GRAFI DEĞİL: Science GPT'nin sözleşmesi katı sıralıdır
// (her adım bir öncekinin kimliğine bağlı) ve üç yerinde otomatikleştirilmesi
// YASAK insan onayı vardır: şema onayı, protokol kilidi, kanıt kartları.
// Serbest node bağlama, backend'in 409'la reddedeceği akışlar vaat ederdi.
//
// ÖN-KAYIT SIRASI: kilit veri yüklenmeden ÖNCE alınır. Keşif önce yapılıp
// hipotez sonra yazılırsa bu ön-kayıt değil HARKing'dir; adım sırası bunu
// yapısal olarak engeller (2. adım geçilmeden 3. adım açılmaz).
import { useState, useCallback, useRef, useEffect } from 'react';
import {
  X, GraduationCap, Lock, Upload, FileCheck2, Lightbulb, Play,
  ShieldCheck, BookOpen, FileText, Loader2, Check, AlertTriangle, Map,
} from 'lucide-react';
import { useStore } from '../../store/useStore';
import { LOGIN_PATH } from '../../const';
import {
  saglik, yurutucular, taslakUret, protokolKilitle, veriYukle, semaGetir,
  semaOnayla, oneriUret, oneriOnayla, analizCalistir, dogrula, makaleUret,
  denetimDogrula, BilimHatasi,
  type Yurutucular, type OneriSonuc, type AnalizSonuc, type DogrulamaSonuc,
  type MakaleSonuc, type KanitKarti, type DenetimDogrulama,
  type CikarilmisSema, type DegiskenOnayi,
} from '../../lib/scienceBridge';
import EvidenceCardEditor from './EvidenceCardEditor';
import SchemaConfirmTable from './SchemaConfirmTable';
import SpatialPath from './SpatialPath';

type AdimNo = 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8;

const ADIMLAR: { no: AdimNo; ad: string; ikon: React.ElementType }[] = [
  { no: 1, ad: 'Protokol', ikon: FileText },
  { no: 2, ad: 'Ön-kayıt kilidi', ikon: Lock },
  { no: 3, ad: 'Veri', ikon: Upload },
  { no: 4, ad: 'Şema onayı', ikon: FileCheck2 },
  { no: 5, ad: 'Yöntem önerisi', ikon: Lightbulb },
  { no: 6, ad: 'Yürütme', ikon: Play },
  { no: 7, ad: 'Doğrulama', ikon: ShieldCheck },
  { no: 8, ad: 'Kanıt + makale', ikon: BookOpen },
];

export default function AcademicMode() {
  const acik = useStore((s) => s.academicOpen);
  const setAcik = useStore((s) => s.setAcademicOpen);
  // Rehberli Mod'dan devredilen ön-kayıt bağlamı (varsa).
  const devir = useStore((s) => s.academicDevir);

  const [adim, setAdim] = useState<AdimNo>(1);
  // Kilitten sonra seçilen yol. P5 tablosal altı yöntemi çalıştırır;
  // mekânsal yol suc_analizi çekirdeğinde koşup sonucu devreder.
  const [yol, setYol] = useState<'secilmedi' | 'p5' | 'mekansal'>('secilmedi');
  const [mesgul, setMesgul] = useState(false);
  const [hata, setHata] = useState<BilimHatasi | null>(null);
  const [motorAyakta, setMotorAyakta] = useState<boolean | null>(null);
  const [yurutulen, setYurutulen] = useState<Yurutucular | null>(null);

  // Adım çıktıları — her biri bir sonrakinin ön koşulu.
  const [metin, setMetin] = useState('');
  const [researchId, setResearchId] = useState('');
  const [kilitli, setKilitli] = useState(false);
  const [onaylayan, setOnaylayan] = useState('');
  const [hipotez, setHipotez] = useState('');
  const [datasetId, setDatasetId] = useState('');
  const [veriOzet, setVeriOzet] = useState('');
  const [sema, setSema] = useState<CikarilmisSema | null>(null);
  const [semaOnaylari, setSemaOnaylari] = useState<DegiskenOnayi[]>([]);
  const [semaOnayli, setSemaOnayli] = useState(false);
  const [oneri, setOneri] = useState<OneriSonuc | null>(null);
  const [approvalId, setApprovalId] = useState('');
  const [analiz, setAnaliz] = useState<AnalizSonuc | null>(null);
  const [dogrulama, setDogrulama] = useState<DogrulamaSonuc | null>(null);
  const [kartlar, setKartlar] = useState<KanitKarti[]>([]);
  const [makale, setMakale] = useState<MakaleSonuc | null>(null);
  const [denetim, setDenetim] = useState<DenetimDogrulama | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  // Motor sağlığı ve P5'in gerçekten çalıştırdığı yöntemler.
  useEffect(() => {
    if (!acik) return;
    saglik()
      .then(() => setMotorAyakta(true))
      .catch(() => setMotorAyakta(false));
    yurutucular().then(setYurutulen).catch(() => setYurutulen(null));
  }, [acik]);

  // Rehberli Mod'dan gelen hipotez/oturum bağlamını devral.
  useEffect(() => {
    if (acik && devir?.hipotez && !hipotez) setHipotez(devir.hipotez);
  }, [acik, devir, hipotez]);

  const calis = useCallback(async <T,>(fn: () => Promise<T>): Promise<T | undefined> => {
    setMesgul(true);
    setHata(null);
    try {
      return await fn();
    } catch (e) {
      setHata(e instanceof BilimHatasi ? e : new BilimHatasi('sistem', String(e), 0));
      return undefined;
    } finally {
      setMesgul(false);
    }
  }, []);

  // ---- Adım eylemleri ----

  const protokolUret = () =>
    calis(async () => {
      const r = await taslakUret(metin.trim());
      setResearchId(r.protocol.research_id);
      setAdim(2);
    });

  const kilitle = () =>
    calis(async () => {
      await protokolKilitle(researchId, onaylayan.trim(), {
        okcOturumId: devir?.oturumId,
        yerliKilitHash: devir?.kilitHash,
      });
      setKilitli(true);
      setAdim(3);
    });

  const dosyaSec = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (!f) return;
    calis(async () => {
      const r = await veriYukle(researchId, f);
      const did = r.manifest.dataset_id;
      setDatasetId(did);
      setVeriOzet(
        `${r.profile.row_count} satır · ${r.profile.column_count} sütun · ` +
          `SHA-256 ${r.manifest.sha256.slice(0, 12)}…`,
      );
      const s = await semaGetir(researchId, did);
      setSema(s.inferred);
      setAdim(4);
    });
  };

  const semayiOnayla = () =>
    calis(async () => {
      await semaOnayla(researchId, datasetId, semaOnaylari);
      setSemaOnayli(true);
      setAdim(5);
    });

  const oneriIste = () =>
    calis(async () => {
      const r = await oneriUret(researchId, datasetId, { research_question: metin.trim() });
      setOneri(r);
      setAdim(5);
    });

  const oneriyiOnayla = () =>
    calis(async () => {
      if (!oneri) return;
      const r = await oneriOnayla(researchId, datasetId, oneri.recommendation_id, {
        approved_by: onaylayan.trim(),
      });
      setApprovalId(r.approval_id);
      setAdim(6);
    });

  const calistir = () =>
    calis(async () => {
      const r = await analizCalistir(researchId, datasetId, approvalId);
      setAnaliz(r);
      setAdim(7);
    });

  const dogrulamayiCalistir = () =>
    calis(async () => {
      if (!analiz) return;
      const r = await dogrula(researchId, datasetId, analiz.analysis_id);
      setDogrulama(r);
      setAdim(8);
    });

  const makaleyiUret = () =>
    calis(async () => {
      if (!analiz || !dogrulama) return;
      const r = await makaleUret(researchId, datasetId, analiz.analysis_id, dogrulama.validation_id, {
        author_line: onaylayan.trim() || '[Yazar adı]',
        use_local_gemma: true,
        evidence_claims: kartlar,
      });
      setMakale(r);
      const d = await denetimDogrula(researchId);
      setDenetim(d);
    });

  if (!acik) return null;

  const kutu = 'rounded-lg border border-slate-800 bg-slate-900/50 p-4 space-y-3';
  const btn =
    'px-4 py-1.5 rounded bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 text-white text-xs font-semibold flex items-center gap-1.5';
  const girdi =
    'w-full px-3 py-2 rounded bg-slate-950 border border-slate-700 text-sm text-slate-100 placeholder-slate-600';

  return (
    <div className="fixed inset-0 z-40 bg-slate-950 flex flex-col" role="dialog" aria-label="Akademik Mod">
      <div className="flex items-center justify-between px-5 py-3 border-b border-slate-800">
        <div className="flex items-center gap-2">
          <GraduationCap size={18} className="text-violet-400" />
          <span className="text-sm font-semibold text-slate-100">Akademik Mod</span>
          <span className="text-[11px] text-slate-500">— ön-kayıtlı, denetlenebilir makale taslağı</span>
          {motorAyakta === false && (
            <span className="ml-2 text-[11px] px-2 py-0.5 rounded bg-red-950/50 text-red-300">
              motor kapalı (8000)
            </span>
          )}
        </div>
        <button
          onClick={() => setAcik(false)}
          className="p-1.5 rounded hover:bg-slate-800 text-slate-400 hover:text-white"
          aria-label="Kapat"
        >
          <X size={18} />
        </button>
      </div>

      {/* Adım şeridi */}
      <div className="flex items-center gap-1 px-5 py-2 border-b border-slate-800 overflow-x-auto">
        {(yol === 'mekansal' ? ADIMLAR.slice(0, 2) : ADIMLAR).map(({ no, ad, ikon: Ikon }) => {
          const bitti = no < adim;
          const aktif = no === adim;
          return (
            <div
              key={no}
              className={`flex items-center gap-1.5 px-2.5 py-1 rounded text-[11px] shrink-0 ${
                aktif
                  ? 'bg-violet-600 text-white'
                  : bitti
                    ? 'bg-emerald-950/40 text-emerald-300'
                    : 'text-slate-600'
              }`}
            >
              {bitti ? <Check size={12} /> : <Ikon size={12} />}
              {no}. {ad}
            </div>
          );
        })}
        {yol === 'mekansal' && (
          <div className="flex items-center gap-1.5 px-2.5 py-1 rounded text-[11px] shrink-0 bg-sky-700 text-white">
            <Map size={12} /> 3. Mekânsal analiz ve makale
          </div>
        )}
      </div>

      <div className="flex-1 overflow-y-auto px-5 py-4 max-w-3xl w-full mx-auto space-y-4">
        {hata && hata.tip === 'guvenlik' ? (
          // 401: oturum yok. Ham "Authentication required" + "tip: guvenlik ·
          // HTTP 401" teşhis satırı kullanıcıya anlamsız gelir; gerçek çıkış
          // girişe gitmektir (Rehberli Mod'daki 'kimlik' kartıyla aynı düzeltme).
          <div className="rounded-lg border border-sky-800/60 bg-sky-950/40 p-3 space-y-2">
            <div className="flex items-start gap-2 text-xs text-sky-200">
              <AlertTriangle size={15} className="shrink-0 mt-0.5" />
              <div className="font-medium">Akademik Mod sunucu taraflı analiz için oturum ister.</div>
            </div>
            <button
              onClick={() => { window.location.href = LOGIN_PATH; }}
              className="text-xs px-2.5 py-1 rounded font-medium bg-sky-800/60 hover:bg-sky-700/60 text-sky-100"
            >
              Giriş yap
            </button>
          </div>
        ) : hata && (
          <div className="rounded-lg border border-red-800/60 bg-red-950/40 p-3 space-y-2">
            <div className="flex items-start gap-2 text-xs text-red-200">
              <AlertTriangle size={15} className="shrink-0 mt-0.5" />
              <div>
                <div className="font-medium">{hata.message}</div>
                <div className="opacity-70 mt-0.5">
                  tip: {hata.tip}
                  {hata.durum ? ` · HTTP ${hata.durum}` : ''}
                </div>
              </div>
            </div>
            {hata.yenidenDenenebilir && (
              <div className="text-[11px] text-red-300/80">
                Bu hata geçici olabilir; servis ayağa kalkınca tekrar deneyebilirsiniz.
              </div>
            )}
          </div>
        )}

        {/* 1. Protokol */}
        {adim === 1 && (
          <section className={kutu}>
            <div className="text-xs text-slate-300 font-medium">1. Araştırma protokolü</div>
            <p className="text-[11px] text-slate-500">
              Araştırma sorunuzu ve beklentinizi yazın. Yerel Gemma bundan şema doğrulamalı
              bir protokol taslağı üretir; taslağı bir sonraki adımda kilitleyeceksiniz.
            </p>
            <textarea
              value={metin}
              onChange={(e) => setMetin(e.target.value)}
              rows={5}
              placeholder="ör. Köy düzeyinde olay yoğunluğu ile nüfus arasındaki ilişkiyi inceliyorum..."
              className={girdi + ' resize-none'}
            />
            <button onClick={protokolUret} disabled={mesgul || metin.trim().length < 20} className={btn}>
              {mesgul ? <Loader2 size={13} className="animate-spin" /> : <FileText size={13} />}
              Protokol taslağı üret
            </button>
          </section>
        )}

        {/* 2. Ön-kayıt kilidi */}
        {adim === 2 && (
          <section className={kutu}>
            <div className="text-xs text-slate-300 font-medium">2. Ön-kayıt kilidi</div>
            <div className="flex items-start gap-2 text-xs bg-amber-950/40 text-amber-300 border border-amber-800/50 rounded p-2.5">
              <AlertTriangle size={15} className="shrink-0 mt-0.5" />
              <div>
                <div className="font-medium">Kilit veriden ÖNCE alınır.</div>
                <div className="opacity-85">
                  Önce analiz yapıp hipotezi sonra yazmak ön-kayıt değil, HARKing'dir.
                  Bu adım geçilmeden veri yükleme açılmaz.
                </div>
              </div>
            </div>
            <div className="text-[11px] text-slate-500">Protokol: {researchId}</div>
            <input
              value={onaylayan}
              onChange={(e) => setOnaylayan(e.target.value)}
              placeholder="Kilidi alan araştırmacı"
              className={girdi}
            />
            {devir?.oturumId && (
              <div className="text-[11px] text-emerald-400/80">
                Suç analizi oturumu bağlanacak: {devir.oturumId}
              </div>
            )}
            <button onClick={kilitle} disabled={mesgul || !onaylayan.trim()} className={btn}>
              {mesgul ? <Loader2 size={13} className="animate-spin" /> : <Lock size={13} />}
              Protokolü kilitle
            </button>
          </section>
        )}

        {/* Yol seçimi — kilitten SONRA. Sıra önemli: hangi yol seçilirse
            seçilsin protokol zaten kilitlidir, yani ön-kayıt bozulmaz. */}
        {adim >= 3 && kilitli && yol === 'secilmedi' && (
          <section className={kutu}>
            <div className="text-xs text-slate-300 font-medium">
              Hangi analiz yolu?
            </div>
            <div className="grid gap-2 sm:grid-cols-2">
              <button
                onClick={() => setYol('p5')}
                className="text-left rounded border border-slate-700 hover:border-indigo-500 bg-slate-950/60 p-3 space-y-1"
              >
                <div className="text-xs text-slate-100 font-medium">
                  Tablosal (P5 yürütücüsü)
                </div>
                <div className="text-[11px] text-slate-500">
                  Regresyon ve grup karşılaştırması. Motor içinde çalışır;
                  P4 yöntem onayı ve P6 çapraz doğrulama uygulanır.
                </div>
                {yurutulen && (
                  <div className="text-[10px] text-slate-600">
                    {yurutulen.supported_method_ids.join(', ')}
                  </div>
                )}
              </button>
              <button
                onClick={() => setYol('mekansal')}
                className="text-left rounded border border-slate-700 hover:border-sky-500 bg-slate-950/60 p-3 space-y-1"
              >
                <div className="text-xs text-slate-100 font-medium">
                  Mekânsal (suç analizi çekirdeği)
                </div>
                <div className="text-[11px] text-slate-500">
                  Getis-Ord Gi*, Global Moran, LISA. Motor dışında çalışır;
                  P4/P6 uygulanmaz ve taslak bunu beyan eder.
                </div>
                <div className="text-[10px] text-slate-600">
                  sıcak nokta · otokorelasyon · küme/aykırı değer
                </div>
              </button>
            </div>
          </section>
        )}

        {/* Mekânsal yol */}
        {kilitli && yol === 'mekansal' && (
          <SpatialPath
            researchId={researchId}
            onaylayan={onaylayan}
            hipotez={hipotez || metin}
          />
        )}

        {/* 3. Veri */}
        {adim === 3 && kilitli && yol === 'p5' && (
          <section className={kutu}>
            <div className="text-xs text-slate-300 font-medium">3. Ham veri</div>
            <p className="text-[11px] text-slate-500">
              Motor dosyayı salt-okunur saklar ve SHA-256 kimliğini alır. Ham veri üzerinde
              otomatik temizlik YAPILMAZ.
            </p>
            <button onClick={() => fileRef.current?.click()} disabled={mesgul} className={btn}>
              {mesgul ? <Loader2 size={13} className="animate-spin" /> : <Upload size={13} />}
              Dosya seç (CSV / XLSX / JSON)
            </button>
            <input
              ref={fileRef}
              type="file"
              accept=".csv,.tsv,.json,.jsonl,.xlsx"
              onChange={dosyaSec}
              className="hidden"
            />
          </section>
        )}

        {/* 4. Şema onayı */}
        {adim === 4 && yol === 'p5' && (
          <section className={kutu}>
            <div className="text-xs text-slate-300 font-medium">4. Şema onayı</div>
            {veriOzet && <div className="text-[11px] text-emerald-400/80">{veriOzet}</div>}
            <p className="text-[11px] text-slate-500">
              Çıkarılan şemayı inceleyin. Bu onay otomatikleştirilemez — değişken türleri
              ve rolleri yanlışsa tüm analiz yanlış olur.
            </p>
            {sema && <SchemaConfirmTable sema={sema} onDegisti={setSemaOnaylari} />}
            <button
              onClick={semayiOnayla}
              disabled={mesgul || semaOnaylari.some((o) => o.rationale.trim().length < 3)}
              className={btn}
            >
              {mesgul ? <Loader2 size={13} className="animate-spin" /> : <FileCheck2 size={13} />}
              Şemayı onaylıyorum
            </button>
            {semaOnaylari.some((o) => o.rationale.trim().length < 3) && (
              <div className="text-[11px] text-amber-400">
                Her değişken için en az 3 karakterlik gerekçe gerekir.
              </div>
            )}
          </section>
        )}

        {/* 5. Yöntem önerisi + onay */}
        {adim === 5 && semaOnayli && yol === 'p5' && (
          <section className={kutu}>
            <div className="text-xs text-slate-300 font-medium">5. Yöntem önerisi</div>
            {!oneri ? (
              <button onClick={oneriIste} disabled={mesgul} className={btn}>
                {mesgul ? <Loader2 size={13} className="animate-spin" /> : <Lightbulb size={13} />}
                Öneri üret
              </button>
            ) : (
              <>
                <div
                  className={`text-xs rounded p-2 ${
                    oneri.readiness === 'ready'
                      ? 'bg-emerald-950/40 text-emerald-300'
                      : oneri.readiness === 'conditional'
                        ? 'bg-amber-950/40 text-amber-300'
                        : 'bg-red-950/40 text-red-300'
                  }`}
                >
                  Hazırlık durumu: <b>{oneri.readiness}</b>
                  {oneri.readiness === 'blocked' && ' — yürütme denenmemelidir.'}
                </div>
                {yurutulen && (
                  <div className="text-[10px] text-slate-500">
                    P5'in gerçekten çalıştırdığı yöntemler:{' '}
                    {yurutulen.supported_method_ids.join(', ')}. Öneri bunların dışındaysa
                    motor yaklaşık bir yöntemle DEĞİŞTİRMEZ, çalıştırmaz.
                  </div>
                )}
                <button
                  onClick={oneriyiOnayla}
                  disabled={mesgul || oneri.readiness === 'blocked'}
                  className={btn}
                >
                  {mesgul ? <Loader2 size={13} className="animate-spin" /> : <Check size={13} />}
                  Yöntemi onayla
                </button>
              </>
            )}
          </section>
        )}

        {/* 6. Yürütme */}
        {adim === 6 && approvalId && yol === 'p5' && (
          <section className={kutu}>
            <div className="text-xs text-slate-300 font-medium">6. Model yürütme</div>
            <p className="text-[11px] text-slate-500">
              Motor yürütmeden hemen önce ham veri, protokol, öneri ve şema hash'lerini
              yeniden doğrular.
            </p>
            <button onClick={calistir} disabled={mesgul} className={btn}>
              {mesgul ? <Loader2 size={13} className="animate-spin" /> : <Play size={13} />}
              Analizi çalıştır
            </button>
          </section>
        )}

        {/* 7. Doğrulama */}
        {adim === 7 && analiz && yol === 'p5' && (
          <section className={kutu}>
            <div className="text-xs text-slate-300 font-medium">7. Doğrulama</div>
            <div className="text-[11px] text-slate-400">
              Model: {analiz.model_name} ({analiz.method_id})
            </div>
            {analiz.warnings?.length > 0 && (
              <div className="text-[11px] text-amber-400">{analiz.warnings.join(' · ')}</div>
            )}
            <p className="text-[11px] text-slate-500">
              Çapraz doğrulama dakikalar sürebilir; sayfayı kapatmayın.
            </p>
            <button onClick={dogrulamayiCalistir} disabled={mesgul} className={btn}>
              {mesgul ? <Loader2 size={13} className="animate-spin" /> : <ShieldCheck size={13} />}
              Doğrulamayı çalıştır
            </button>
          </section>
        )}

        {/* 8. Kanıt kartları + makale */}
        {adim === 8 && dogrulama && yol === 'p5' && (
          <section className={kutu}>
            <div className="text-xs text-slate-300 font-medium">8. Kanıt kartları ve makale</div>
            <div className="text-xs rounded p-2 bg-slate-950/60 text-slate-300">
              Kalite kapısı: <b>{dogrulama.quality_gate}</b>
              <div className="text-[11px] text-slate-500 mt-0.5">
                İki değer de model onayı DEĞİLDİR; insan incelemesi zorunludur.
              </div>
            </div>

            <EvidenceCardEditor kartlar={kartlar} onDegisti={setKartlar} />

            <button onClick={makaleyiUret} disabled={mesgul || kartlar.length === 0} className={btn}>
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
                  Makale üretildi: {makale.manuscript_filename}
                </div>
                <div className="text-[11px] text-slate-500">{makale.manuscript_id}</div>
                {denetim && (
                  <div
                    className={`text-xs px-2 py-1 rounded inline-block ${
                      denetim.valid
                        ? 'bg-emerald-950/40 text-emerald-300'
                        : 'bg-red-950/40 text-red-300'
                    }`}
                  >
                    {denetim.valid
                      ? `✔ Denetim zinciri geçerli (${denetim.event_count} olay)`
                      : '⚠ Denetim zinciri doğrulanamadı'}
                  </div>
                )}
              </div>
            )}
          </section>
        )}
      </div>
    </div>
  );
}
