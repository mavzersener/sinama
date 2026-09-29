# -*- coding: utf-8 -*-
"""Paket 06: olay akışı gizli manifesto içeriğini dışarı taşımaz."""

import json
import os
import tempfile
import unittest

from sinama.surec import dongu, kanit, rapor


ISARETLEYICILER = ("Ada Gizli", "555-0101", "Gizli Sokak", "dinamik-grup")
GEREKCE = {"hipotez": "Ada Gizli için hipotez", "yorum": "Gizli Sokak yorumu"}


def _analiz_dongusu(mod):
    d = dongu.AnalizDongusu({"karar": "sentetik", "kapsam": "Gizli Sokak"},
                            mod=mod)
    d.planla()
    d.veri_bagla({"n": 7, "uyarilar": ["Ada Gizli 555-0101"]})
    d.analize_gec({"uygun": True, "sebepler": []})
    return d


class TestDuzeltme06Mahremiyet(unittest.TestCase):
    def _kaydet(self, mod):
        with tempfile.TemporaryDirectory() as tmp:
            d = _analiz_dongusu(mod)
            d.analiz_kaydet("nni", {"nni": 0.62, "_ozet": "dinamik-grup",
                                     "adres": "Gizli Sokak"},
                             GEREKCE if mod == "resmi" else None)
            dongu.kaydet(d, tmp)
            olaylar = kanit.oku(tmp, d.manifesto["oturum_id"])
            with open(kanit._akis_yolu(tmp, d.manifesto["oturum_id"]),
                      encoding="utf-8") as f:
                ham = f.read()
            with open(os.path.join(tmp, "oturumlar",
                                   d.manifesto["oturum_id"] + ".json"),
                      encoding="utf-8") as f:
                manifesto = json.load(f)
            return olaylar[-1], ham, manifesto

    def test_formal_akis_guvenli_ozet_gerekce_digest_manifesto_kaynagi(self):
        olay, ham, manifesto = self._kaydet("resmi")
        self.assertEqual(olay["surum"], "b06")
        self.assertEqual(olay["ozet"]["sayisal"]["nni"], 0.62)
        self.assertNotIn("_ozet", olay["ozet"])
        self.assertIn("gerekce_digest", olay)
        for isaretleyici in ISARETLEYICILER:
            self.assertNotIn(isaretleyici, ham)
        self.assertEqual(manifesto["gecmis"][-1]["gerekce"], GEREKCE)
        self.assertTrue(kanit.gerekce_bagi_dogrula(manifesto, [olay])["saglam"])
        self.assertIn("yerel gizli manifesto", rapor.muhakeme_izi(manifesto))

    def test_standalone_istemci_ozeti_enjekte_edemez(self):
        olay, ham, _ = self._kaydet("kesif")
        self.assertEqual(olay["ozet"]["sayisal"]["nni"], 0.62)
        self.assertNotIn("dinamik-grup", ham)

    def test_dinamik_frekans_etiketsiz_toplamla_ozetlenir(self):
        for mod in ("resmi", "kesif"):
            with tempfile.TemporaryDirectory() as tmp:
                d = _analiz_dongusu(mod)
                d.analiz_kaydet("frekans",
                                 {"dinamik-grup-A": 2, "dinamik-grup-B": 4},
                                 GEREKCE if mod == "resmi" else None)
                dongu.kaydet(d, tmp)
                olay = kanit.oku(tmp, d.manifesto["oturum_id"])[-1]
                self.assertEqual(olay["ozet"],
                                 {"durum": "ozet_uretildi",
                                  "sayisal": {"toplam": 6}})

    def test_public_dogrulama_manifesto_gerekcesi_degisimini_gorur(self):
        with tempfile.TemporaryDirectory() as tmp:
            d = _analiz_dongusu("resmi")
            d.analiz_kaydet("nni", {"nni": 0.62}, GEREKCE)
            dongu.kaydet(d, tmp)
            self.assertTrue(kanit.dogrula(tmp, d.manifesto["oturum_id"])["saglam"])
            yol = os.path.join(tmp, "oturumlar", d.manifesto["oturum_id"] + ".json")
            with open(yol, encoding="utf-8") as f:
                manifesto = json.load(f)
            manifesto["gecmis"][-1]["gerekce"]["yorum"] = "değiştirildi"
            with open(yol, "w", encoding="utf-8") as f:
                json.dump(manifesto, f, ensure_ascii=False)
            sonuc = kanit.dogrula(tmp, d.manifesto["oturum_id"])
            self.assertFalse(sonuc["saglam"])
            self.assertEqual(sonuc["gerekce_bagi"], "gerekce_bagi_bozuk")

    def test_manifesto_gerekcesi_degisirse_bag_kopar(self):
        olay, _, manifesto = self._kaydet("resmi")
        manifesto["gecmis"][-1]["gerekce"]["yorum"] = "değiştirildi"
        self.assertFalse(kanit.gerekce_bagi_dogrula(manifesto, [olay])["saglam"])


if __name__ == "__main__":
    unittest.main()
