# -*- coding: utf-8 -*-
"""
test_duzeltme_08_p06_v2.py — iki güvenlik düzeltmesi BİRLİKTE (A2.3).

P06 (mahremiyet: beyaz listeli olay kaydı, gerekçe yerine SHA-256 taahhüdü)
hazırlık kopyasında v1 zinciri üzerinde yazıldı; 07 (zincir v2: bağ alanı
hash'e dahil) kanonik depoda P06'sız yazıldı. Sınama'da ikisi elle üçlü
birleştirildi. Kendi testleri her birini kendi biçiminde sınıyor; bunlar
BİRLEŞİK biçimi sınar.
"""
import json
import os
import sys
import tempfile
import unittest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from sinama.surec import dongu, kanit  # noqa: E402

GEREKCE = {"hipotez": "Sentetik hipotez metni", "yorum": "Sentetik yorum metni"}


def _oturum(tmp):
    """Gerekçeli resmî bir oturum kurar ve kaydeder; oturum kimliğini döner."""
    d = dongu.AnalizDongusu({"karar": "sentetik", "kapsam": "A bölgesi"}, mod="resmi")
    d.planla()
    d.veri_bagla({"n": 12, "uyarilar": []})
    d.analize_gec({"uygun": True, "sebepler": []})
    d.analiz_kaydet("nni", {"nni": 0.62, "n": 12}, GEREKCE)
    d.analiz_kaydet("frekans", {"hirsizlik": 7, "gasp": 5}, GEREKCE)
    dongu.kaydet(d, tmp)
    return d.manifesto["oturum_id"]


def _kayitlar(yol):
    """Olay akışı dosyasındaki kayıtları sırayla okur."""
    with open(yol, encoding="utf-8") as f:
        return [json.loads(s) for s in f if s.strip()]


def _yaz(yol, kayitlar):
    """Kayıtları olay akışı biçiminde (satır başına bir JSON) geri yazar."""
    with open(yol, "w", encoding="utf-8") as f:
        for k in kayitlar:
            f.write(json.dumps(k, ensure_ascii=False) + "\n")


class TestP06veV2Birlikte(unittest.TestCase):
    def test_kayit_bicimi_iki_duzeltmeyi_de_tasir(self):
        with tempfile.TemporaryDirectory() as tmp:
            oid = _oturum(tmp)
            olaylar = kanit.oku(tmp, oid)
            self.assertGreaterEqual(len(olaylar), 4)
            for o in olaylar:
                self.assertEqual(o.get("zincir"), kanit.ZINCIR_SURUMU)   # 07
                self.assertEqual(o.get("surum"), "b06")                  # P06
                self.assertNotIn("gerekce", o)                           # P06
            with open(kanit._akis_yolu(tmp, oid), encoding="utf-8") as f:
                ham = f.read()
            self.assertNotIn("hirsizlik", ham, "dinamik grup etiketi akışa girdi")
            self.assertNotIn("Sentetik hipotez", ham, "gerekçe metni akışa girdi")
            s = kanit.dogrula(tmp, oid)
            self.assertTrue(s["saglam"], s)
            self.assertEqual(s["gerekce_bagi"], "dogrulandi")
            self.assertEqual(len(s["zincir_son_hash"] or ""), 64)
            self.assertNotIn("korumasiz_olay", s)

    def test_v2_bilen_saldirganin_ortadan_kurcalamasi_yakalanir(self):
        with tempfile.TemporaryDirectory() as tmp:
            oid = _oturum(tmp)
            yol = kanit._akis_yolu(tmp, oid)
            kayitlar = _kayitlar(yol)
            self.assertGreaterEqual(len(kayitlar), 4)
            son_hash_once = kanit.dogrula(tmp, oid)["zincir_son_hash"]
            # Saldırgan uygulamanın KENDİ hash fonksiyonunu bilir: 1. kaydın
            # özetini değiştirir ve YALNIZ 2. kaydın bağını günceller. v2'de
            # bağ alanı hash'e dahil olduğu için 2. kaydın hash'i de değişir
            # ve 3. kaydın bağı kopar. (v1'de 2. kaydın hash'i değişmezdi ve
            # zincir "sağlam" görünürdü — 07 açığı.)
            kayitlar[1]["ozet"] = {"durum": "ozet_uretildi", "sayisal": {"n": 999}}
            kayitlar[2]["onceki_hash"] = kanit._kayit_hash(kayitlar[1])
            _yaz(yol, kayitlar)
            s = kanit.dogrula(tmp, oid)
            self.assertFalse(s["saglam"], "v2 zinciri ortadaki kurcalamayı kaçırdı")
            self.assertEqual(s["bozuk_adim"], 3)
            self.assertIsNotNone(son_hash_once)

    def test_gerekce_degisirse_bag_kopar_zincir_alanlari_korunur(self):
        with tempfile.TemporaryDirectory() as tmp:
            oid = _oturum(tmp)
            mf = kanit._oturum_yolu(tmp, oid, ".json")
            with open(mf, encoding="utf-8") as f:
                manifesto = json.load(f)
            adim = next(a for a in manifesto["gecmis"] if a.get("gerekce"))
            adim["gerekce"]["yorum"] = "sonradan değiştirilmiş yorum"
            with open(mf, "w", encoding="utf-8") as f:
                json.dump(manifesto, f, ensure_ascii=False)
            s = kanit.dogrula(tmp, oid)
            self.assertFalse(s["saglam"])
            self.assertEqual(s["gerekce_bagi"], "gerekce_bagi_bozuk")
            # Zincirin kendisi sağlam: dış çapa karşılaştırması hâlâ yapılabilir.
            self.assertEqual(len(s["zincir_son_hash"] or ""), 64)


if __name__ == "__main__":
    unittest.main()
