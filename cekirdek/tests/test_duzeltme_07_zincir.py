# -*- coding: utf-8 -*-
"""07: kanıt zinciri — bağ alanı hash'e dahil (v2) + sürüm düşürme koruması.

Bulgu (23 Eyl 2026, DataFlow entegrasyon değerlendirmesi): v1 _kayit_hash
onceki_hash'i hash DIŞINDA bırakıyordu. Ortadaki bir kaydı değiştirip yalnız
bir sonrakinin onceki_hash'ini güncellemek dogrula()'yı 'sağlam' bırakıyor,
zincirin baş ve son hash'i değişmiyordu — dış çapa bile yakalayamazdı.
"""
import hashlib
import json
import tempfile
import unittest

from suc_analizi.surec import kanit


def _yaz(yol, kayitlar):
    with open(yol, "w", encoding="utf-8") as f:
        f.write("\n".join(json.dumps(k, ensure_ascii=False) for k in kayitlar) + "\n")


def _oku(yol):
    with open(yol, encoding="utf-8") as f:
        return [json.loads(s) for s in f.read().splitlines() if s.strip()]


def _v1_hash(kayit):
    govde = {a: b for a, b in kayit.items() if a != "onceki_hash"}
    return hashlib.sha256(json.dumps(govde, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()


class TestZincirV2(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()

    def _akis(self, oid, n=4):
        for i in range(n):
            kanit.olay_yaz(self.tmp, oid, {"olay": f"adim{i}", "faz": "ANALIZ", "ozet": f"x{i}"})
        return kanit._akis_yolu(self.tmp, oid)

    def test_ortadaki_degisiklik_ve_bag_guncellemesi_saptanir(self):
        # v1'de sessizce geçen saldırının aynısı: ortadaki kayıt + YALNIZ
        # bir sonraki halkanın bağı. v2'de o halkanın kendi hash'i değişir,
        # bir sonraki bağ kopar.
        yol = self._akis("s1", 5)
        s = _oku(yol)
        s[1]["ozet"] = "SAHTE"
        s[2]["onceki_hash"] = kanit._kayit_hash(s[1])
        _yaz(yol, s)
        d = kanit.dogrula(self.tmp, "s1")
        self.assertFalse(d["saglam"])
        self.assertEqual(d["bozuk_adim"], 3)

    def test_sondan_bir_onceki_degisirse_son_hash_degisir(self):
        # Ardında tek halka varsa HER hash zinciri içeride tutarlı kalır;
        # v2'de son hash değişir (v1'de değişmiyordu) → dış çapa yakalar.
        yol = self._akis("s1b", 4)
        once = kanit.dogrula(self.tmp, "s1b")["zincir_son_hash"]
        s = _oku(yol)
        s[2]["ozet"] = "SAHTE"
        s[3]["onceki_hash"] = kanit._kayit_hash(s[2])
        _yaz(yol, s)
        self.assertNotEqual(kanit.dogrula(self.tmp, "s1b")["zincir_son_hash"], once)

    def test_tum_sonek_yeniden_yazilirsa_son_hash_degisir(self):
        yol = self._akis("s2")
        once = kanit.dogrula(self.tmp, "s2")["zincir_son_hash"]
        s = _oku(yol)
        s[1]["ozet"] = "SAHTE"
        for i in range(2, len(s)):  # saldırgan tüm sonraki halkaları yeniden bağlar
            s[i]["onceki_hash"] = kanit._kayit_hash(s[i - 1])
        _yaz(yol, s)
        d = kanit.dogrula(self.tmp, "s2")
        self.assertTrue(d["saglam"])  # iç tutarlı…
        self.assertNotEqual(d["zincir_son_hash"], once)  # …ama dış çapa yakalar

    def test_son_hash_son_kaydin_hashidir(self):
        yol = self._akis("s3", 3)
        self.assertEqual(kanit.dogrula(self.tmp, "s3")["zincir_son_hash"], kanit._kayit_hash(_oku(yol)[-1]))
        self.assertIsNone(kanit.dogrula(self.tmp, "yok")["zincir_son_hash"])

    def test_cagiran_surum_ve_bag_alanini_ezemez(self):
        k = kanit.olay_yaz(self.tmp, "s4", {"olay": "a", "zincir": 1, "onceki_hash": "sahte"})
        self.assertEqual(k["zincir"], kanit.ZINCIR_SURUMU)
        self.assertIsNone(k["onceki_hash"])

    def test_eski_v1_akis_okunur_ve_korumasiz_raporlanir(self):
        yol = kanit._akis_yolu(self.tmp, "eski", olustur=True)
        s, onceki = [], None
        for i in range(3):
            k = {"zaman": "2026-07-01T10:00:00", "olay": f"adim{i}", "onceki_hash": onceki}
            s.append(k)
            onceki = _v1_hash(k)
        _yaz(yol, s)
        d = kanit.dogrula(self.tmp, "eski")
        self.assertTrue(d["saglam"])
        self.assertEqual(d["korumasiz_olay"], 3)
        self.assertIn("saptanamaz", d["uyari"])
        # Eski akışa yeni kayıt eklenebilir; v2 halkası v1 sonuna bağlanır.
        kanit.olay_yaz(self.tmp, "eski", {"olay": "yeni"})
        d2 = kanit.dogrula(self.tmp, "eski")
        self.assertTrue(d2["saglam"])
        self.assertEqual(d2["korumasiz_olay"], 3)

    def test_v2_den_sonra_v1_surum_dusurme_reddedilir(self):
        yol = self._akis("s5", 3)
        s = _oku(yol)
        del s[2]["zincir"]  # son halkayı zayıf biçime indir
        _yaz(yol, s)
        self.assertFalse(kanit.dogrula(self.tmp, "s5")["saglam"])

    def test_yeni_akista_uyari_yok(self):
        self._akis("s6")
        self.assertNotIn("korumasiz_olay", kanit.dogrula(self.tmp, "s6"))


if __name__ == "__main__":
    unittest.main()
