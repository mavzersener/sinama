/**
 * Hafif i18n (DataFlow src/i18n.ts düzeninden, ADR-003): Türkçe varsayılan, İngilizce
 * seçenek; seçim tarayıcıda kalıcı. Sözlükler düz anahtar → metin JSON'larıdır ve BMK v10
 * K17.5 tarafından denetlenir (aynı anahtar kümesi, boş değer yok, kaynaktaki her t()
 * anahtarı ve çekirdekten türetilen aileler). Eksik anahtar önce Türkçeye, sonra ham
 * anahtara düşer. Dinamik anahtarlar ters tırnakla yazılır: t(`kategori.${k}`).
 */
import { createContext, useContext } from "react"
import en from "./en.json"
import tr from "./tr.json"

export type Dil = "tr" | "en"
export const DILLER: { kod: Dil; etiket: string }[] = [
  { kod: "tr", etiket: "TR" },
  { kod: "en", etiket: "EN" },
]
const SOZLUKLER: Record<Dil, Record<string, string>> = { tr, en }
const ANAHTAR = "sinama_dil"

export function kayitliDil(): Dil {
  try {
    return localStorage.getItem(ANAHTAR) === "en" ? "en" : "tr"
  } catch {
    return "tr"
  }
}

export function dilKaydet(dil: Dil) {
  try {
    localStorage.setItem(ANAHTAR, dil)
  } catch {
    /* gizli kip */
  }
}

export const DilBaglami = createContext<{ dil: Dil; setDil: (d: Dil) => void }>({
  dil: "tr",
  setDil: () => {},
})

export type Cevirici = (anahtar: string, degerler?: Record<string, string | number>) => string

export function cevirici(dil: Dil): Cevirici {
  return (anahtar, degerler) => {
    let s = SOZLUKLER[dil][anahtar] ?? SOZLUKLER.tr[anahtar] ?? anahtar
    for (const [a, v] of Object.entries(degerler ?? {})) s = s.split(`{${a}}`).join(String(v))
    return s
  }
}

export function useT(): Cevirici {
  return cevirici(useContext(DilBaglami).dil)
}

export function useDil() {
  return useContext(DilBaglami)
}
