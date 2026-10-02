import type { ReactNode } from "react"
import { AlertTriangle } from "lucide-react"
import { ApiHatasi, type Hipotez } from "@/api"
import { cn } from "@/lib/utils"
import { useT, type Cevirici } from "@/i18n"

const KATEGORI_RENK: Record<string, string> = {
  "DESTEKLENDİ": "bg-emerald-600/20 text-emerald-300 border-emerald-500/40",
  KIRILGAN: "bg-amber-600/20 text-amber-200 border-amber-500/40",
  "BELİRSİZ": "bg-slate-600/30 text-slate-200 border-slate-400/40",
  "ÇELİŞKİLİ": "bg-red-600/20 text-red-300 border-red-500/40",
  "ÇEKİMSER": "bg-zinc-700/40 text-zinc-300 border-zinc-500/40",
}

export function KategoriRozeti({ kategori, buyuk }: { kategori: string; buyuk?: boolean }) {
  const t = useT()
  return (
    <span
      data-kategori={kategori}
      className={cn(
        "inline-flex items-center rounded-md border font-semibold tracking-wide",
        buyuk ? "px-4 py-2 text-xl" : "px-2 py-0.5 text-xs",
        KATEGORI_RENK[kategori] ?? KATEGORI_RENK["ÇEKİMSER"],
      )}
    >
      {t(`kategori.${kategori}`)}
    </span>
  )
}

export function Bolum({ baslik, children, className }: { baslik: string; children: ReactNode; className?: string }) {
  return (
    <section className={cn("rounded-lg border border-slate-800 bg-slate-900/60 p-4", className)}>
      <h3 className="mb-3 text-sm font-semibold uppercase tracking-wide text-slate-400">{baslik}</h3>
      {children}
    </section>
  )
}

export function HataKutusu({ hata }: { hata: unknown }) {
  const t = useT()
  if (!hata) return null
  const e = hata instanceof ApiHatasi ? hata : new ApiHatasi(String(hata))
  return (
    <div role="alert" className="flex gap-3 rounded-md border border-red-500/40 bg-red-950/40 p-3 text-sm text-red-200">
      <AlertTriangle className="mt-0.5 size-4 shrink-0" />
      <div>
        <div className="font-semibold">{t("hata.baslik")}</div>
        <div>{e.message === "__baglanti__" ? t("hata.baglanti") : e.message}</div>
        {e.oneri && (
          <div className="mt-1 text-red-300/80">
            {t("hata.oneri")}: {e.oneri}
          </div>
        )}
      </div>
    </div>
  )
}

/** Rakip adı: katalog rakibi sözlükten, serbest rakip kendi ifadesiyle. */
export function rakipAdi(t: Cevirici, kod: string, hipotezler: Hipotez[] = []): string {
  const serbest = hipotezler.find((h) => h.kimlik === kod && h.serbest)
  return serbest ? serbest.ifade : t(`rakip.${kod}`)
}

/** Serbest rakibin "sonraki kanıt"ı kendi metnidir; katalog rakibininki sözlükten. */
export function sonrakiKanit(t: Cevirici, kod: string, gereken: string, hipotezler: Hipotez[] = []): string {
  return hipotezler.some((h) => h.kimlik === kod && h.serbest) ? gereken : t(`sonraki.${kod}`)
}

export function Etiketli({ etiket, children }: { etiket: string; children: ReactNode }) {
  return (
    <label className="block space-y-1 text-sm">
      <span className="text-slate-300">{etiket}</span>
      {children}
    </label>
  )
}

export const GIRDI =
  "w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-sky-500"
