/** Yer: #/plan/<oturum> ve #/hukum/<oturum> — yeniden yüklemede ekran korunur. */
export type Ekran = { ad: "soru" } | { ad: "plan"; id: string } | { ad: "hukum"; id: string }

export function ekranCoz(hash: string): Ekran {
  const m = hash.match(/^#\/(plan|hukum)\/([A-Za-z0-9_-]+)$/)
  return m ? { ad: m[1] as "plan" | "hukum", id: m[2] } : { ad: "soru" }
}

export function git(ekran: Ekran) {
  window.location.hash = ekran.ad === "soru" ? "" : `#/${ekran.ad}/${ekran.id}`
}
