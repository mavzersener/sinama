"""03: satır eşleşmesi ve çekirdek sayısal sınırlar."""
import copy
import unittest
from unittest.mock import patch

from suc_analizi.arayuz import ortak, araclar
from suc_analizi.cekirdek import regresyon, hipotez
from suc_analizi.cekirdek.hatalar import VeriHatasi


class TestRegresyon(unittest.TestCase):
    def test_tam_kayit_ve_kapsam(self):
        rows = [{'x': 1, 'y': 2}, {'x': 2, 'y': None},
                {'x': 3, 'y': 6}, {'x': 4, 'y': 8}]
        arg = dict(satirlar=rows, hedef='y', degiskenler=['x'])
        eski = copy.deepcopy(arg)
        self.assertEqual(ortak._matris_getir(arg), ([[1.0], [3.0], [4.0]], [2., 6., 8.], ['x']))
        sonuc = ortak.ARACLAR['coklu_regresyon']['fn'](arg)
        self.assertEqual(sonuc['n'], 3)
        self.assertEqual(sonuc['kapsam']['girdi_n'], 4)
        self.assertEqual(sonuc['kapsam']['dislanan_n'], 1)
        self.assertEqual(arg, eski)

    def test_sifir_ve_gecersiz(self):
        rows = [{'x': x, 'y': 1} for x in [None, 0, True, 'NaN', float('inf'), '', 'bozuk']]
        self.assertEqual(ortak._matris_getir(dict(satirlar=rows, hedef='y', degiskenler=['x']))[0], [[0.]])

    def test_mekansal_atomik(self):
        rows = [dict(x=i, y=2*i, lat=41+i*.001, lon=29) for i in range(5)]
        rows[1]['x'] = 'bozuk'
        with patch.object(araclar.mekansal_istatistik, 'mekansal_regresyon_tani', return_value={'n': 4}) as fn:
            s = ortak.ARACLAR['mekansal_regresyon']['fn'](dict(satirlar=rows, hedef='y', degiskenler=['x']))
        y, X, koord = fn.call_args.args[:3]
        self.assertEqual(y, [0., 4., 6., 8.])
        self.assertEqual(X, [[0.], [2.], [3.], [4.]])
        self.assertEqual(len(koord), 4)
        self.assertEqual(s['kapsam']['dislanan_n'], 1)

    def test_gecersiz_tasarim(self):
        cases = [([], []), ([[]]*3, [1, 2, 3]), ([[1], [2]], [1, 2, 3]),
                 ([[1], [2, 3], [3]], [1, 2, 3])]
        for bad in [None, True, float('nan'), float('inf'), -float('inf'), '']:
            cases.extend([([[1], [bad], [3]], [1, 2, 3]), ([[1], [2], [3]], [1, bad, 3])])
        for X, y in cases:
            for fn in [regresyon.coklu_ols, regresyon.lojistik,
                       lambda X, y: ortak._matris_getir({'X': X, 'y': y})]:
                with self.subTest(X=X, y=y, fn=fn), self.assertRaises(VeriHatasi):
                    fn(X, y)

    def test_golden_ve_yetersiz(self):
        s = regresyon.coklu_ols([[i] for i in range(8)], [2*i+1 for i in range(8)])
        self.assertEqual([k['beta'] for k in s['katsayilar']], [1., 2.])
        self.assertIsNone(regresyon.coklu_ols([[1]], [3]))
        with self.assertRaises(VeriHatasi):
            ortak._matris_getir(dict(satirlar=[{'x': None, 'y': 1}], hedef='y', degiskenler=['x']))

    def test_bagimli_inline_eslesme(self):
        for x, y in [([1, None, 3], [1, 2, None]), ([1, 2], [1, 2, 3]), ([True, 2], [1, 2])]:
            with self.subTest(x=x, y=y), self.assertRaises(VeriHatasi):
                ortak.ARACLAR['t_testi']['fn']({'tip': 'bagimli', 'x': x, 'y': y})
        self.assertEqual(ortak.ARACLAR['t_testi']['fn']({'tip': 'bagimli', 'x': [1, 2, 4], 'y': [0, 0, 1]}),
                         hipotez.t_test_bagimli([1, 2, 4], [0, 0, 1]))
