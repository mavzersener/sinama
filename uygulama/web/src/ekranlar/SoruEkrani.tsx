/**
 * Soru ekranı → calisma_baslat. Soru türü, amaç, veri ve türün parametreleri VERİYİ
 * ANALİZ ETMEDEN seçilir: önizleme yalnız şemayı (sütunlar, satır sayısı, kategorik
 * değerler) gösterir, ham satır göstermez — parametreler doğrulayıcı kilide girer.
 */
import { useEffect, useState } from "react"
import { Upload, Wand2 } from "lucide-react"
import { api, oturumNotu, type Onizleme } from "@/api"
import { Button } from "@/components/ui/button"
import { Bolum, Etiketli, GIRDI, HataKutusu } from "@/bilesenler/ortak"
import { useT } from "@/i18n"
import { git } from "@/yonlendirme"

const TURLER = ["ARTIS", "YOGUNLASMA", "SERI", "ETKI"] as const
const AMACLAR = ["dogrulayici", "kesifsel", "operasyonel"] as const
type Param = "kanal_alan" | "mo_alan" | "bolge_alan" | "mudahale" | "kontrol" | "tampon" | "kesinti_tarihi"
/** Türe göre parametreler: [ad, zorunlu, kaynak] — kaynak "sutun" ya da "deger" (bölge değeri) ya da "tarih". */
const PARAMETRELER: Record<string, [Param, boolean, "sutun" | "deger" | "tarih"][]> = {
  ARTIS: [["kanal_alan", false, "sutun"]],
  YOGUNLASMA: [],
  SERI: [["mo_alan", true, "sutun"]],
  ETKI: [
    ["bolge_alan", true, "sutun"],
    ["mudahale", true, "deger"],
    ["kontrol", false, "deger"],
    ["tampon", false, "deger"],
    ["kesinti_tarihi", true, "tarih"],
  ],
}

export default function SoruEkrani() {
  const t = useT()
  const [soru, setSoru] = useState("")
  const [oneri, setOneri] = useState<{ soru_turu: string | null; kaynak: string } | null>(null)
  const [tur, setTur] = useState<string>("ARTIS")
  const [amac, setAmac] = useState<string>("dogrulayici")
  const [onaylayan, setOnaylayan] = useState("")
  const [dosyalar, setDosyalar] = useState<{ ad: string; boyut: number }[]>([])
  const [dosya, setDosya] = useState("")
  const [onizleme, setOnizleme] = useState<Onizleme | null>(null)
  const [param, setParam] = useState<Partial<Record<Param, string>>>({})
  const [hata, setHata] = useState<unknown>(null)
  const [bekliyor, setBekliyor] = useState(false)

  useEffect(() => {
    api.veriListesi().then((v) => setDosyalar(v.dosyalar)).catch(setHata)
  }, [])
  useEffect(() => {
    setOnizleme(null)
    if (dosya) api.onizleme(dosya).then(setOnizleme).catch(setHata)
  }, [dosya])

  const oner = async () => {
    setHata(null)
    try {
      const o = await api.oneri(soru)
      setOneri(o)
      if (o.soru_turu) setTur(o.soru_turu)
    } catch (e) {
      setHata(e)
    }
  }

  const yukle = async (f: File | undefined) => {
    if (!f) return
    setHata(null)
    try {
      const y = await api.veriYukle(f)
      setDosyalar((await api.veriListesi()).dosyalar)
      setDosya(y.ad)
    } catch (e) {
      setHata(e)
    }
  }

  const eksik =
    !dosya ||
    (amac === "dogrulayici" && !onaylayan.trim()) ||
    PARAMETRELER[tur].some(([ad, zorunlu]) => zorunlu && !param[ad])

  const baslat = async () => {
    setHata(null)
    setBekliyor(true)
    try {
      const govde: Record<string, string> = { soru_turu: tur, amac }
      if (soru.trim()) govde.soru = soru.trim()
      if (amac === "dogrulayici") govde.onaylayan = onaylayan.trim()
      for (const [ad] of PARAMETRELER[tur]) if (param[ad]) govde[ad] = param[ad]!
      const y = await api.calismaBaslat(govde)
      oturumNotu.dosyaKaydet(y.oturum_id, dosya)
      git({ ad: "plan", id: y.oturum_id })
    } catch (e) {
      setHata(e)
    } finally {
      setBekliyor(false)
    }
  }

  const bolgeDegerleri = (param.bolge_alan && onizleme?.degerler[param.bolge_alan]) || null

  return (
    <div className="space-y-4" data-ekran="soru">
      <h2 className="text-xl font-semibold">{t("soru.baslik")}</h2>
      <HataKutusu hata={hata} />

      <Bolum baslik={t("soru.metin_etiket")}>
        <textarea
          className={GIRDI}
          rows={2}
          value={soru}
          placeholder={t("soru.metin_ornek")}
          onChange={(e) => setSoru(e.target.value)}
        />
        <div className="mt-2 flex items-center gap-3">
          <Button variant="outline" size="sm" onClick={oner} disabled={!soru.trim()}>
            <Wand2 /> {t("soru.oner")}
          </Button>
          {oneri && (
            <span className="text-xs text-slate-400" data-oneri={oneri.soru_turu ?? ""}>
              {oneri.soru_turu
                ? t(oneri.kaynak === "dil_modeli" ? "soru.oneri_dil" : "soru.oneri_kural", {
                    tur: t(`soru_turu.${oneri.soru_turu}`),
                  })
                : t("soru.oneri_yok")}
            </span>
          )}
        </div>
      </Bolum>

      <div className="grid gap-4 md:grid-cols-2">
        <Bolum baslik={t("soru.tur_etiket")}>
          <div className="space-y-2">
            {TURLER.map((x) => (
              <label key={x} className="flex items-start gap-2 text-sm">
                <input type="radio" name="tur" checked={tur === x} onChange={() => setTur(x)} className="mt-1" />
                <span>{t(`soru_turu.${x}`)}</span>
              </label>
            ))}
          </div>
        </Bolum>
        <Bolum baslik={t("soru.amac_etiket")}>
          <div className="space-y-2">
            {AMACLAR.map((x) => (
              <label key={x} className="flex items-start gap-2 text-sm">
                <input type="radio" name="amac" checked={amac === x} onChange={() => setAmac(x)} className="mt-1" />
                <span>{t(`amac.${x}`)}</span>
              </label>
            ))}
          </div>
          {amac === "dogrulayici" && (
            <div className="mt-3 space-y-1">
              <Etiketli etiket={t("soru.onaylayan_etiket")}>
                <input className={GIRDI} value={onaylayan} onChange={(e) => setOnaylayan(e.target.value)} />
              </Etiketli>
              <p className="text-xs text-slate-500">{t("soru.onaylayan_not")}</p>
            </div>
          )}
        </Bolum>
      </div>

      <Bolum baslik={t("soru.veri_etiket")}>
        <div className="flex flex-wrap items-center gap-3">
          <select className={GIRDI + " max-w-xs"} value={dosya} onChange={(e) => setDosya(e.target.value)}>
            <option value="">{dosyalar.length ? t("soru.veri_sec") : t("soru.veri_yok")}</option>
            {dosyalar.map((d) => (
              <option key={d.ad} value={d.ad}>
                {d.ad}
              </option>
            ))}
          </select>
          <label className="inline-flex cursor-pointer items-center gap-2 text-sm text-sky-300">
            <Upload className="size-4" /> {t("soru.veri_yukle")}
            <input type="file" accept=".csv,.tsv,.txt" className="hidden" onChange={(e) => yukle(e.target.files?.[0])} />
          </label>
        </div>
        {onizleme && (
          <p className="mt-2 text-xs text-slate-400">
            {t("soru.onizleme", { n: onizleme.satir, s: onizleme.sutunlar.join(", ") })}
            {onizleme.kesildi && <span className="ml-2 text-amber-300">{t("soru.kesildi")}</span>}
          </p>
        )}
      </Bolum>

      {PARAMETRELER[tur].length > 0 && (
        <Bolum baslik={t("soru.parametreler")}>
          <div className="grid gap-3 md:grid-cols-2">
            {PARAMETRELER[tur].map(([ad, zorunlu, kaynak]) => (
              <Etiketli key={ad} etiket={`${t(`param.${ad}`)} (${zorunlu ? t("param.zorunlu") : t("param.istege_bagli")})`}>
                {kaynak === "tarih" ? (
                  <input
                    type="date"
                    className={GIRDI}
                    value={param[ad] ?? ""}
                    onChange={(e) => setParam({ ...param, [ad]: e.target.value })}
                  />
                ) : kaynak === "deger" && bolgeDegerleri ? (
                  <select className={GIRDI} value={param[ad] ?? ""} onChange={(e) => setParam({ ...param, [ad]: e.target.value })}>
                    <option value="">{t("param.yok")}</option>
                    {bolgeDegerleri.map((v) => (
                      <option key={v}>{v}</option>
                    ))}
                  </select>
                ) : kaynak === "deger" ? (
                  <input className={GIRDI} value={param[ad] ?? ""} onChange={(e) => setParam({ ...param, [ad]: e.target.value })} />
                ) : (
                  <select className={GIRDI} value={param[ad] ?? ""} onChange={(e) => setParam({ ...param, [ad]: e.target.value })}>
                    <option value="">{t("param.yok")}</option>
                    {(onizleme?.sutunlar ?? []).map((s) => (
                      <option key={s}>{s}</option>
                    ))}
                  </select>
                )}
              </Etiketli>
            ))}
          </div>
        </Bolum>
      )}

      <div className="flex justify-end">
        <Button onClick={baslat} disabled={eksik || bekliyor} data-eylem="baslat">
          {t("soru.baslat")}
        </Button>
      </div>
    </div>
  )
}
