"""04: gerçek transport, şema, istek bağlamı ve hesaplama tavanları."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from datetime import datetime
from unittest.mock import patch

from suc_analizi.arayuz import sunucu, ortak
from suc_analizi.arayuz.sema import sema_dogrula
from suc_analizi.cekirdek import mekan, tekrar, hipotez
from suc_analizi.cekirdek.hatalar import KullanimHatasi


class TestIstek(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.env = patch.dict(os.environ, SUC_ANALIZI_LOG_DIR=self.tmp.name,
                              SUC_ANALIZI_VERI_KOKU=self.tmp.name)
        self.env.start()
        self.addCleanup(self.env.stop)

    def call(self, name, args):
        return sunucu.isle({'jsonrpc': '2.0', 'id': 1, 'method': 'tools/call',
                            'params': {'name': name, 'arguments': args}})

    def payload(self, reply):
        self.assertNotIn('error', reply)
        self.assertFalse(reply['result']['isError'], reply)
        return json.loads(reply['result']['content'][0]['text'])

    def transport(self, lines, **env):
        script = Path(__file__).resolve().parents[1] / 'mcp_sunucu.py'
        r = subprocess.run([sys.executable, str(script)], input=lines.encode('utf-8'),
                           capture_output=True, timeout=10, cwd=self.tmp.name,
                           env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1', **env))
        self.assertEqual(r.returncode, 0, r.stderr.decode('utf-8'))
        return [json.loads(line) for line in r.stdout.decode('utf-8').splitlines()]

    def test_transport_hatalar_bildirim_ping(self):
        lines = ['[]', 'null', '42', '"text"', '{bozuk',
                 '{"id":1,"method":"ping","params":[]}',
                 '{"id":2,"method":"tools/call","params":{"name":"fisher_exact","arguments":[]}}',
                 '{"method":"ping"}', '{"id":3,"method":"ping"}']
        r = self.transport('\n'.join(lines)+'\n')
        self.assertEqual([v.get('error', {}).get('code') for v in r[:-1]],
                         [-32600]*4 + [-32700, -32600, -32602])
        self.assertEqual(r[-1], {'jsonrpc': '2.0', 'id': 3, 'result': {}})

    def test_transport_byte_siniri_ve_sonlu_json(self):
        ping = '{"id":8,"method":"ping"}\n'
        r = self.transport('"'+'ü'*100+'"\n'+ping,
                           SUC_ANALIZI_MAKS_ISTEK_BYTE='128')
        self.assertEqual(r[0]['error']['code'], -32600)
        self.assertEqual(r[1]['id'], 8)
        r = self.transport('{"id":NaN,"method":"ping"}\n'+ping)
        self.assertEqual(r[0]['error']['code'], -32700)
        self.assertEqual(r[1]['id'], 8)

    def test_recursive_schema(self):
        schema = {'type': 'object', 'additionalProperties': False,
                  'properties': {'v': {'type': 'array', 'minItems': 1, 'maxItems': 2,
                    'items': {'type': 'object', 'required': ['n'], 'properties': {
                        'n': {'type': 'number', 'minimum': 0, 'maximum': 10}}}}}, 'required': ['v']}
        self.assertIsNone(sema_dogrula('t', schema, {'v': [{'n': 0}, {'n': 10}]}))
        for arg in [{'v': []}, {'v': [{}, {}, {}]}, {'v': ['PII_SENTINEL']},
                    {'v': [{}]}, {'v': [{'n': 1}], 'other': 1}] + [
                    {'v': [{'n': v}]} for v in [True, float('nan'), float('inf'), -1, 11]]:
            with self.subTest(arg=arg):
                error = sema_dogrula('t', schema, arg)
                self.assertIsInstance(error, str)
                self.assertNotIn('PII_SENTINEL', error)

    def test_public_schema_internal_and_unknown(self):
        base = {'a': 1, 'b': 9, 'c': 11, 'd': 3}
        for extra in [{'_gate_karar': {}}, {'foo': {'_gate_karar': {}}}, {'a': True}, {'a': float('nan')}]:
            self.assertEqual(self.call('fisher_exact', dict(base, **extra))['error']['code'], -32602)
        p = self.payload(self.call('fisher_exact', dict(base, unused_public=1)))
        self.assertTrue(any('unused_public' in s for s in p['meta']['uyarilar']))
        self.assertFalse(any('unused_public' in s for s in self.payload(self.call('fisher_exact', base))['meta']['uyarilar']))
        self.assertNotIn('_gate_karar', base)

    def test_metadata_csv_inline_ve_nested(self):
        csv = Path(self.tmp.name) / 'data.csv'
        csv.write_text('id\n0\n1\n2\n3\n4\n5\n', encoding='utf-8')
        for arg in [{'satirlar': [{'id': str(i)} for i in range(6)]}, {'csv_yolu': str(csv)}]:
            self.assertEqual(self.payload(self.call('veri_ozeti', arg))['meta']['satir'], 6)
            meta = self.payload(self.call('fisher_exact', {'a': 1, 'b': 9, 'c': 11, 'd': 3}))['meta']
            self.assertIsNone(meta['satir'])
            self.assertFalse(meta['kesildi'])
        def nested(arg):
            ortak.kayitlari_getir({'satirlar': [{'id': 1}]})
            self.payload(self.call('veri_ozeti', {'satirlar': [{'id': i} for i in range(6)]}))
            return 'ok'
        politika = {'sinif': 'veri_hazirlama', 'gate': None,
                    'muafiyet_gerekcesi': 'sentetik nested context testi',
                    'insan_onayi': False, 'iz_zorunlu': False,
                    'veri_sinifi': 'sentetik', 'butce_turu': 'dogrusal'}
        with patch.dict(ortak.ARACLAR, nested={'fn': nested,
                        'sema': {'type': 'object'}, 'aciklama': '',
                        'politika': politika}):
            self.assertEqual(self.payload(self.call('nested', {}))['meta']['satir'], 1)

    def test_regression_gate_prepared_once(self):
        arg = dict(satirlar=[{'x': i, 'y': 2*i+1} for i in range(4)], hedef='y', degiskenler=['x'])
        before = copy.deepcopy(arg)
        with patch.object(ortak, 'kayitlari_getir', wraps=ortak.kayitlari_getir) as load:
            self.assertEqual(self.payload(self.call('coklu_regresyon', arg))['sonuc']['n'], 4)
        self.assertEqual(load.call_count, 1)
        self.assertEqual(arg, before)

    def test_kde_compute_oncesi_butce(self):
        for pts, cell in [([(41, 29), (42, 30)], .001),
                          # .1 km: 57*43*4000 = 9,804,000 katkı > 5,000,000.
                          ([(41, 29), (41.05, 29.05)]*2000, .1)]:
            with self.subTest(cell=cell), patch.object(mekan.math, 'exp', side_effect=AssertionError('hesaplama başladı')) as body:
                with self.assertRaises(KullanimHatasi):
                    mekan.kde_yogunluk(pts, hucre_km=cell)
                body.assert_not_called()
        for bad in [0, -1, True, float('nan'), float('inf')]:
            with self.subTest(bad=bad), self.assertRaises(KullanimHatasi):
                mekan.kde_yogunluk([(41, 29)], bant_km=bad)
            with self.subTest(bad=bad), self.assertRaises(KullanimHatasi):
                mekan.grid_hotspot([(41, 29)], hucre_km=bad)
        self.assertEqual(mekan.kde_yogunluk([(0, 0)], bant_km=.3, hucre_km=.25),
                         [{'lat': .00113, 'lon': .001123, 'yogunluk': .8406},
                          {'lat': .00113, 'lon': .003369, 'yogunluk': .4198},
                          {'lat': .003391, 'lon': .001123, 'yogunluk': .4198},
                          {'lat': .003391, 'lon': .003369, 'yogunluk': .2096}])

    def test_sim_compute_oncesi_butce(self):
        rows = [dict(lat=41, lon=29, tarih=datetime(2026, 1, 1))]*320
        for sim in [999, 1000, -1, 0, True, float('inf')]:
            with self.subTest(sim=sim), patch.object(tekrar, '_cift_sayisi', side_effect=AssertionError('hesaplama başladı')) as body:
                with self.assertRaises(KullanimHatasi):
                    tekrar.knox_anlamlilik(rows, sim=sim)
                body.assert_not_called()
        s = tekrar.knox_anlamlilik(rows[:3], sim=9, seed=1)
        self.assertEqual((s['gozlenen'], s['p'], s['sim']), (3, 1., 9))

    def test_randomizasyon_sim_butcesi(self):
        with patch('random.Random.shuffle', side_effect=AssertionError('hesaplama başladı')) as body:
            for sim in (0, -1, True, 1000):
                with self.subTest(sim=sim), self.assertRaises(KullanimHatasi):
                    hipotez.randomizasyon_testi([1, 2], [3, 4], sim=sim)
            with self.assertRaises(KullanimHatasi):
                hipotez.randomizasyon_testi([1]*160, [2]*160, sim=999)
            body.assert_not_called()
        self.assertEqual(hipotez.randomizasyon_testi([1, 2], [1, 2], sim=9, seed=1)['p'], 1.)

    def test_grid_bos_ve_temsil_edilemeyen_olcekler(self):
        self.assertEqual(mekan.kde_yogunluk([]), [])
        self.assertEqual(mekan.grid_hotspot([]), [])
        with self.assertRaises(KullanimHatasi):
            mekan.grid_hotspot([(41, 29)]*20001)
        for band, cell in ((1e-200, .25), (.3, 1e-320)):
            with self.subTest(band=band, cell=cell), self.assertRaises(KullanimHatasi):
                mekan.kde_yogunluk([(41, 29), (42, 30)], bant_km=band, hucre_km=cell)
