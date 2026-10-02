# -*- coding: utf-8 -*-
"""suc_analizi araç şemalarından DataFlow node tanımları üretir.

Çıktı: src/nodes/sucAnaliziNodes.generated.ts — elle düzenlenmez;
yeniden üretim: PYTHONUTF8=1 python scripts/generate_suc_nodes.py
(suc_analizi paketi import edilebilir olmalı: pip install -e C:\\Projects\\suc_analizi)

Kapsam: yalnız inline veri ('satirlar') kabul eden araçlar — süreç
(dongu_*, kanit_*, muhakeme_izi, brifing_uret) ve skaler-girdili araçlar
node olmaz. Veri, node girişine bağlanan kaynağın satırlarından gelir;
bu yüzden csv_yolu/satirlar configFields'a yazılmaz.
"""
import json
import os
import sys

CIKTI = os.path.join(os.path.dirname(__file__), "..", "src", "nodes",
                     "sucAnaliziNodes.generated.ts")

RENK = "#dc2626"
IKON = "Shield"
KATEGORI = "Suç Analizi"
GIZLI_PROPLAR = {"csv_yolu", "satirlar"}


def alan_tipi(ps):
    """JSON şema özelliğinden ConfigField tipi türetir."""
    if "enum" in ps:
        return "select"
    t = ps.get("type")
    if t in ("number", "integer"):
        return "number"
    if t == "boolean":
        return "boolean"
    return "text"  # string, array (virgülle ayrılmış) ve bilinmeyenler


def config_alanlari(sema_so):
    gerekli = set(sema_so.get("required", []))
    alanlar = []
    for ad, ps in sema_so.get("properties", {}).items():
        if ad in GIZLI_PROPLAR:
            continue
        alan = {"name": ad, "label": ad, "type": alan_tipi(ps)}
        if "enum" in ps:
            alan["options"] = [str(x) for x in ps["enum"]]
        if "default" in ps:
            alan["default"] = ps["default"]
        aciklama = ps.get("description")
        if aciklama:
            alan["placeholder"] = aciklama
        elif ps.get("type") == "array":
            alan["placeholder"] = "virgülle ayrılmış liste"
        if ad in gerekli:
            alan["required"] = True
        alanlar.append(alan)
    return alanlar


def uret():
    from suc_analizi.arayuz import araclar  # noqa: F401 — kayıt yan etkisi
    from suc_analizi.arayuz.ortak import ARACLAR

    nodelar = []
    for ad in sorted(ARACLAR):
        kayit = ARACLAR[ad]
        props = kayit["sema"].get("properties", {})
        if "satirlar" not in props:
            continue
        alanlar = config_alanlari(kayit["sema"])
        nodelar.append({
            "type": f"suc_{ad}",
            "label": ad.replace("_", " "),
            "category": KATEGORI,
            "icon": IKON,
            "description": kayit["aciklama"],
            "color": RENK,
            "inputs": 1,
            "outputs": 1,
            "defaultConfig": {a["name"]: a.get("default", "")
                              for a in alanlar},
            "configFields": alanlar,
        })

    # motor için: node tipi -> array tipli config alanları (metin "a,b" -> ["a","b"])
    dizi_alanlari = {}
    for n in nodelar:
        ad = n["type"][len("suc_"):]
        arr = [p for p, ps in ARACLAR[ad]["sema"]["properties"].items()
               if p not in GIZLI_PROPLAR and ps.get("type") == "array"]
        if arr:
            dizi_alanlari[n["type"]] = arr

    govde = json.dumps(nodelar, ensure_ascii=False, indent=2)
    dizi_govde = json.dumps(dizi_alanlari, ensure_ascii=False, indent=2)
    ts = (
        "// OTOMATİK ÜRETİLDİ — elle düzenlemeyin.\n"
        "// Üretici: scripts/generate_suc_nodes.py (kaynak: suc_analizi arayuz/araclar.py)\n"
        "import type { NodeDefinition } from './nodeDefinitions';\n\n"
        f"export const sucAnaliziNodes: NodeDefinition[] = {govde};\n\n"
        "// node tipi -> array tipli config alanları (motor metni listeye çevirir)\n"
        f"export const sucDiziAlanlari: Record<string, string[]> = {dizi_govde};\n"
    )
    with open(CIKTI, "w", encoding="utf-8", newline="\n") as f:
        f.write(ts)
    print(f"{len(nodelar)} node üretildi -> {os.path.normpath(CIKTI)}")


if __name__ == "__main__":
    sys.exit(uret())
