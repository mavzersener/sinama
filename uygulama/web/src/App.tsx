import { useEffect, useMemo, useState } from "react"
import { api, type Saglik } from "@/api"
import { DILLER, DilBaglami, dilKaydet, kayitliDil, useT, type Dil } from "@/i18n"
import { cn } from "@/lib/utils"
import SoruEkrani from "@/ekranlar/SoruEkrani"
import PlanEkrani from "@/ekranlar/PlanEkrani"
import HukumEkrani from "@/ekranlar/HukumEkrani"
import { ekranCoz, git, type Ekran } from "@/yonlendirme"

function Ust({ ekran, saglik }: { ekran: Ekran; saglik: Saglik | null }) {
  const t = useT()
  return (
    <header className="border-b border-slate-800 bg-slate-950/80">
      <div className="mx-auto flex max-w-5xl flex-wrap items-center gap-4 px-4 py-3">
        <div className="mr-auto">
          <div className="text-lg font-bold text-slate-100">{t("uyg.baslik")}</div>
          <div className="text-xs text-slate-400">{t("uyg.altbaslik")}</div>
        </div>
        <nav className="flex gap-1 text-xs" aria-label="adimlar">
          {(["soru", "plan", "hukum"] as const).map((a) => (
            <span
              key={a}
              className={cn(
                "rounded px-2 py-1",
                ekran.ad === a ? "bg-sky-600/30 text-sky-200" : "text-slate-500",
              )}
            >
              {t(`adim.${a}`)}
            </span>
          ))}
        </nav>
        <DilSecici />
        {ekran.ad !== "soru" && (
          <button className="text-xs text-sky-300 underline" onClick={() => git({ ad: "soru" })}>
            {t("uyg.yeni")}
          </button>
        )}
      </div>
      {saglik && (
        <div className="mx-auto max-w-5xl px-4 pb-2 text-[11px] text-slate-500">
          {saglik.dil_modeli ? t("uyg.dil_modeli_acik") : t("uyg.dil_modeli_kapali")} · {t("uyg.veri_koku")}:{" "}
          <code>{saglik.veri_koku}</code> · {saglik.sinama_surumu}
        </div>
      )}
    </header>
  )
}

function DilSecici() {
  const t = useT()
  return (
    <DilBaglami.Consumer>
      {({ dil, setDil }) => (
        <div className="flex items-center gap-1 text-xs" aria-label={t("uyg.dil")}>
          {DILLER.map((d) => (
            <button
              key={d.kod}
              aria-pressed={dil === d.kod}
              onClick={() => setDil(d.kod)}
              className={cn(
                "rounded border px-2 py-0.5",
                dil === d.kod ? "border-sky-500 text-sky-200" : "border-slate-700 text-slate-400",
              )}
            >
              {d.etiket}
            </button>
          ))}
        </div>
      )}
    </DilBaglami.Consumer>
  )
}

export default function App() {
  const [dil, setDilDurum] = useState<Dil>(kayitliDil())
  const [ekran, setEkran] = useState<Ekran>(ekranCoz(window.location.hash))
  const [saglik, setSaglik] = useState<Saglik | null>(null)
  const baglam = useMemo(
    () => ({ dil, setDil: (d: Dil) => (dilKaydet(d), setDilDurum(d)) }),
    [dil],
  )

  useEffect(() => {
    document.documentElement.lang = dil
  }, [dil])
  useEffect(() => {
    const dinle = () => setEkran(ekranCoz(window.location.hash))
    window.addEventListener("hashchange", dinle)
    return () => window.removeEventListener("hashchange", dinle)
  }, [])
  useEffect(() => {
    api.saglik().then(setSaglik).catch(() => setSaglik(null))
  }, [])

  return (
    <DilBaglami.Provider value={baglam}>
      <div className="min-h-screen bg-slate-950 text-slate-200">
        <Ust ekran={ekran} saglik={saglik} />
        <main className="mx-auto max-w-5xl space-y-4 px-4 py-6">
          {ekran.ad === "soru" && <SoruEkrani />}
          {ekran.ad === "plan" && <PlanEkrani id={ekran.id} />}
          {ekran.ad === "hukum" && <HukumEkrani id={ekran.id} dilModeli={!!saglik?.dil_modeli} />}
        </main>
      </div>
    </DilBaglami.Provider>
  )
}
