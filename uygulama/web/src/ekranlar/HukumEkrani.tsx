/**
 * Hüküm ekranı → kategorik hüküm (taslak), tetiklenen kurallar, rakipler, sonraki en iyi
 * kanıt, H_bilinmeyen; isteğe bağlı dil modeli özeti (bağlayıcı değil); insan onayıyla
 * SONUÇ. Olasılık, yüzde ya da güven puanı gösterilmez (AGENTS kural 6).
 */
import { useEffect, useState } from "react"
import { CheckCircle2, MessageSquareText, Stamp } from "lucide-react"
import { api, type HukumYaniti, type Manifesto } from "@/api"
import { Button } from "@/components/ui/button"
import { Bolum, Etiketli, GIRDI, HataKutusu, KategoriRozeti, rakipAdi, sonrakiKanit } from "@/bilesenler/ortak"
import { useDil, useT } from "@/i18n"

const SONUC_TURLERI = ["sorun_dogrulandi", "sorun_reddedildi", "izlemeye_alindi", "mudahale_onerildi"] as const

function olcumMetni(olcum?: Record<string, unknown>) {
  if (!olcum) return null
  return Object.entries(olcum)
    .filter(([, v]) => v !== null && v !== undefined)
    .map(([k, v]) => `${k}=${typeof v === "number" ? v : String(v)}`)
    .join(" · ")
}

export default function HukumEkrani({ id, dilModeli }: { id: string; dilModeli: boolean }) {
  const t = useT()
  const { dil } = useDil()
  const [y, setY] = useState<HukumYaniti | null>(null)
  const [durum, setDurum] = useState<Manifesto | null>(null)
  const [hata, setHata] = useState<unknown>(null)
  const [sade, setSade] = useState<string | null>(null)
  const [sonucTuru, setSonucTuru] = useState<string>("izlemeye_alindi")
  const [onaylayan, setOnaylayan] = useState("")
  const [not, setNot] = useState("")

  const yukle = async () => {
    try {
      setY(await api.hukum(id))
      setDurum(await api.durum(id))
    } catch (e) {
      setHata(e)
    }
  }
  useEffect(() => {
    yukle()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [id])

  const sadelestir = async () => {
    setHata(null)
    try {
      setSade((await api.sade(id, dil)).metin)
    } catch (e) {
      setHata(e)
    }
  }

  const onayla = async () => {
    setHata(null)
    try {
      await api.sonuc(id, { sonuc_turu: sonucTuru, onaylayan, onay_notu: not || undefined })
      setDurum(await api.durum(id))
    } catch (e) {
      setHata(e)
    }
  }

  if (!y) return hata ? <HataKutusu hata={hata} /> : <p>{t("genel.yukleniyor")}</p>
  const h = y.hukum
  const hip = y.hipotezler
  const birincilGerekce = durum?.bilimsel?.kanit?.birincil?.gerekce
  const onay = durum?.faz === "SONUC" ? durum.insan_onaylari[durum.insan_onaylari.length - 1] : null

  return (
    <div className="space-y-4" data-ekran="hukum">
      <h2 className="text-xl font-semibold">{t("hukum.baslik")}</h2>
      <HataKutusu hata={hata} />

      <div className="flex flex-wrap items-center gap-4 rounded-lg border border-slate-800 bg-slate-900/60 p-4">
        <KategoriRozeti kategori={h.kategori} buyuk />
        <span className="inline-flex items-center gap-1 rounded border border-amber-500/50 px-2 py-1 text-xs font-semibold text-amber-200" data-taslak>
          <Stamp className="size-3" /> {t("hukum.taslak")}
        </span>
        <div className="basis-full text-sm" data-ifade>
          <p>{t("hukum.ifade_kategori", { kategori: t(`kategori.${h.kategori}`) })}</p>
          <p>
            {h.en_guclu_rakip
              ? t("hukum.ifade_rakip", { rakip: rakipAdi(t, h.en_guclu_rakip, hip) })
              : t("hukum.hepsi_dislandi")}
          </p>
          <p className="text-slate-400" data-bilinmeyen>
            {t("plan.bilinmeyen")}
          </p>
          <p className="mt-1 text-xs text-slate-500">{t("uyg.olasilik_yok")}</p>
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <Bolum baslik={t("hukum.birincil")}>
          <p className="text-sm">{t(`birincil.${h.birincil_ongoru}`)}</p>
          {birincilGerekce && <p className="mt-1 text-xs text-slate-400">{birincilGerekce}</p>}
        </Bolum>
        <Bolum baslik={t("hukum.kurallar")}>
          <ol className="list-decimal space-y-1 pl-5 text-sm">
            {h.kurallar.map((k, i) => (
              <li key={i} data-kural={k.kural}>
                {t(`kural.${k.kural}`)}
                <div className="text-xs text-slate-500">{k.girdi}</div>
              </li>
            ))}
          </ol>
        </Bolum>
      </div>

      <Bolum baslik={t("hukum.rakipler")}>
        <table className="w-full text-left text-sm">
          <thead className="text-xs text-slate-400">
            <tr>
              <th className="py-1 pr-2">{t("plan.tablo_rakip")}</th>
              <th className="py-1 pr-2">{t("hukum.durum")}</th>
              <th className="py-1">{t("hukum.gerekce")}</th>
            </tr>
          </thead>
          <tbody>
            {h.rakipler.map((r) => (
              <tr key={r.kod} className="border-t border-slate-800 align-top" data-rakip={r.kod} data-durum={r.durum}>
                <td className="py-2 pr-2">{rakipAdi(t, r.kod, hip)}</td>
                <td className="py-2 pr-2">{t(`durum.${r.durum}`)}</td>
                <td className="py-2 text-slate-400">
                  {r.gerekce}
                  {olcumMetni(r.olcum) && <div className="font-mono text-[11px] text-slate-500">{olcumMetni(r.olcum)}</div>}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {dil === "en" && <p className="mt-2 text-xs text-slate-500">{t("hukum.gerekce_dil_notu")}</p>}
      </Bolum>

      <div className="grid gap-4 md:grid-cols-2">
        <Bolum baslik={t("hukum.sonraki")}>
          {h.sonraki_en_iyi_kanit.length ? (
            <ul className="list-disc space-y-1 pl-5 text-sm" data-sonraki>
              {h.sonraki_en_iyi_kanit.map((s) => (
                <li key={s.rakip}>
                  <span className="text-slate-300">{rakipAdi(t, s.rakip, hip)}:</span>{" "}
                  {sonrakiKanit(t, s.rakip, s.gereken, hip)}
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-slate-500" data-sonraki>
              —
            </p>
          )}
        </Bolum>
        <Bolum baslik={t("hukum.saglamlik")}>
          {h.saglamlik_uyarilari.length ? (
            <ul className="list-disc pl-5 text-sm text-amber-200">
              {h.saglamlik_uyarilari.map((u) => (
                <li key={u}>{u}</li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-slate-500">—</p>
          )}
          <p className="mt-3 text-xs text-slate-500">
            {t("hukum.sinamalar")}: {y.sinamalar.map((s) => s.arac).join(", ") || "—"}
          </p>
        </Bolum>
      </div>

      {y.uyarilar.length > 0 && (
        <Bolum baslik={t("hukum.uyarilar")}>
          <ul className="list-disc pl-5 text-xs text-slate-400">
            {y.uyarilar.map((u) => (
              <li key={u}>{u}</li>
            ))}
          </ul>
        </Bolum>
      )}

      {dilModeli && (
        <Bolum baslik={t("hukum.sade")}>
          <Button variant="outline" size="sm" onClick={sadelestir}>
            <MessageSquareText /> {t("hukum.sade")}
          </Button>
          {sade && (
            <div className="mt-2 text-sm">
              <p>{sade}</p>
              <p className="mt-1 text-xs text-slate-500">{t("hukum.sade_not")}</p>
            </div>
          )}
        </Bolum>
      )}

      <Bolum baslik={t("hukum.sonuc_baslik")}>
        {onay ? (
          <p className="inline-flex items-center gap-2 text-sm text-emerald-300" data-onay>
            <CheckCircle2 className="size-4" /> {t("hukum.onaylandi", { kisi: onay.onaylayan })} ·{" "}
            {durum?.sonuc && t(`sonuc_turu.${durum.sonuc.tur}`)}
          </p>
        ) : (
          <div className="grid gap-3 md:grid-cols-3">
            <Etiketli etiket={t("hukum.sonuc_turu")}>
              <select className={GIRDI} value={sonucTuru} onChange={(e) => setSonucTuru(e.target.value)}>
                {SONUC_TURLERI.map((s) => (
                  <option key={s} value={s}>
                    {t(`sonuc_turu.${s}`)}
                  </option>
                ))}
              </select>
            </Etiketli>
            <Etiketli etiket={t("hukum.onaylayan")}>
              <input className={GIRDI} value={onaylayan} onChange={(e) => setOnaylayan(e.target.value)} />
            </Etiketli>
            <Etiketli etiket={t("hukum.onay_notu")}>
              <input className={GIRDI} value={not} onChange={(e) => setNot(e.target.value)} />
            </Etiketli>
            <div className="md:col-span-3 flex justify-end">
              <Button onClick={onayla} disabled={!onaylayan.trim()} data-eylem="onayla">
                {t("hukum.onayla")}
              </Button>
            </div>
          </div>
        )}
      </Bolum>
    </div>
  )
}
