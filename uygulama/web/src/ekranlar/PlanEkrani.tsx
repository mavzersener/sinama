/**
 * Plan ekranı → hipotez seti, sınama planı (veriye bakmadan), serbest rakip ekleme,
 * doğrulayıcıda kilit notu; "Kanıtı bağla" kilit + veri + sınamalar (kanit_bagla) ve
 * ardından hüküm.
 */
import { useCallback, useEffect, useState } from "react"
import { Lock, Play, Plus } from "lucide-react"
import { api, oturumNotu, type Manifesto, type Plan } from "@/api"
import { Button } from "@/components/ui/button"
import { Bolum, Etiketli, GIRDI, HataKutusu, KategoriRozeti, rakipAdi } from "@/bilesenler/ortak"
import { useT } from "@/i18n"
import { git } from "@/yonlendirme"

export default function PlanEkrani({ id }: { id: string }) {
  const t = useT()
  const [durum, setDurum] = useState<Manifesto | null>(null)
  const [plan, setPlan] = useState<Plan | null>(null)
  const [hata, setHata] = useState<unknown>(null)
  const [ifade, setIfade] = useState("")
  const [sonraki, setSonraki] = useState("")
  const [dosya, setDosya] = useState(oturumNotu.dosya(id) ?? "")
  const [dosyalar, setDosyalar] = useState<{ ad: string }[]>([])
  const [bekliyor, setBekliyor] = useState(false)

  const yukle = useCallback(async () => {
    try {
      const d = await api.durum(id)
      if (d.bilimsel?.kanit) return git({ ad: "hukum", id })
      setDurum(d)
      setPlan(await api.plan(id))
    } catch (e) {
      setHata(e)
    }
  }, [id])

  useEffect(() => {
    yukle()
    if (!oturumNotu.dosya(id)) api.veriListesi().then((v) => setDosyalar(v.dosyalar)).catch(setHata)
  }, [id, yukle])

  const ekle = async () => {
    setHata(null)
    try {
      await api.hipotezEkle(id, { ifade, sonraki_kanit: sonraki || undefined })
      setIfade("")
      setSonraki("")
      await yukle()
    } catch (e) {
      setHata(e)
    }
  }

  const sina = async () => {
    setHata(null)
    setBekliyor(true)
    try {
      oturumNotu.dosyaKaydet(id, dosya)
      await api.kanit(id, dosya)
      await api.hukum(id)
      git({ ad: "hukum", id })
    } catch (e) {
      setHata(e)
    } finally {
      setBekliyor(false)
    }
  }

  if (!durum || !plan) return hata ? <HataKutusu hata={hata} /> : <p>{t("genel.yukleniyor")}</p>
  const hipotezler = durum.bilimsel?.hipotezler ?? []
  const birincil = hipotezler.find((h) => h.tur === "BIRINCIL")
  const onaylayan = durum.bilimsel?.onaylayan

  return (
    <div className="space-y-4" data-ekran="plan">
      <h2 className="text-xl font-semibold">{t("plan.baslik")}</h2>
      <HataKutusu hata={hata} />

      <Bolum baslik={t("plan.birincil")}>
        <p className="text-sm">{t(`hipotez.${plan.soru_turu}`)}</p>
        {birincil?.ongoru && (
          <p className="mt-2 text-xs text-slate-400">
            {t("plan.ongoru")}: <code>{plan.birincil.arac}</code> · {t(`ongoru.${plan.soru_turu}`)}
          </p>
        )}
        <p className="text-xs text-slate-400">
          {t("plan.yanlislama")}: {t(`yanlislama.${plan.soru_turu}`)}
        </p>
      </Bolum>

      <Bolum baslik={t("plan.rakipler")}>
        <table className="w-full text-left text-sm">
          <thead className="text-xs text-slate-400">
            <tr>
              <th className="py-1 pr-2">{t("plan.tablo_rakip")}</th>
              <th className="py-1 pr-2">{t("plan.tablo_sinama")}</th>
              <th className="py-1 pr-2">{t("plan.tablo_onceden")}</th>
              <th className="py-1">{t("plan.gereksinim")}</th>
            </tr>
          </thead>
          <tbody>
            {plan.rakipler.map((r) => (
              <tr key={r.kod} className="border-t border-slate-800 align-top" data-rakip={r.kod}>
                <td className="py-2 pr-2">{rakipAdi(t, r.kod, hipotezler)}</td>
                <td className="py-2 pr-2 text-slate-400">
                  {hipotezler.some((h) => h.kimlik === r.kod && h.serbest) ? t("sinama.serbest") : t(`sinama.${r.kod}`)}
                </td>
                <td className="py-2 pr-2">
                  {r.cozulebilir ? (
                    <span className="text-emerald-300">{t("plan.cozulebilir")}</span>
                  ) : (
                    <span className="text-amber-300">{t("plan.cozulemez")}</span>
                  )}
                </td>
                <td className="py-2 text-slate-400">{r.gereksinim ?? "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
        <p className="mt-3 text-xs text-slate-400" data-bilinmeyen>
          {t("plan.bilinmeyen")}
        </p>
      </Bolum>

      <Bolum baslik={t("plan.tavan")}>
        <div className="flex flex-wrap items-center gap-3" data-tavan={plan.ulasilabilir_en_ust}>
          <KategoriRozeti kategori={plan.ulasilabilir_en_ust} />
          {plan.tavan_nedenleri.length > 0 && (
            <ul className="list-disc pl-5 text-xs text-slate-400">
              {plan.tavan_nedenleri.map((n) => (
                <li key={n}>{n}</li>
              ))}
            </ul>
          )}
        </div>
      </Bolum>

      <Bolum baslik={t("plan.serbest_baslik")}>
        <div className="grid gap-3 md:grid-cols-2">
          <Etiketli etiket={t("plan.serbest_ifade")}>
            <input className={GIRDI} value={ifade} onChange={(e) => setIfade(e.target.value)} />
          </Etiketli>
          <Etiketli etiket={t("plan.serbest_sonraki")}>
            <input className={GIRDI} value={sonraki} onChange={(e) => setSonraki(e.target.value)} />
          </Etiketli>
        </div>
        <div className="mt-2 flex items-center gap-3">
          <Button variant="outline" size="sm" onClick={ekle} disabled={!ifade.trim()}>
            <Plus /> {t("plan.serbest_ekle")}
          </Button>
          <span className="text-xs text-slate-500">{t("plan.serbest_not")}</span>
        </div>
      </Bolum>

      <div className="flex flex-wrap items-center justify-end gap-3">
        {!oturumNotu.dosya(id) && (
          <select className={GIRDI + " max-w-xs"} value={dosya} onChange={(e) => setDosya(e.target.value)}>
            <option value="">{t("plan.veri_secilmedi")}</option>
            {dosyalar.map((d) => (
              <option key={d.ad}>{d.ad}</option>
            ))}
          </select>
        )}
        {durum.amac === "dogrulayici" && onaylayan && (
          <span className="inline-flex items-center gap-1 text-xs text-amber-200">
            <Lock className="size-3" /> {t("plan.kilit_not", { kisi: onaylayan })}
          </span>
        )}
        <Button onClick={sina} disabled={!dosya || bekliyor} data-eylem="sina">
          <Play /> {t("plan.kanit_bagla")}
        </Button>
      </div>
    </div>
  )
}
