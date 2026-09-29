# -*- coding: utf-8 -*-
"""Özgün MCP senaryoları: gerçek assertion kapısı ve izole sentetik test turu."""
import csv
import json
import os
import queue
import random
import subprocess
import sys
import tempfile
import threading
from collections import deque
from contextlib import ExitStack
from datetime import datetime, timedelta

BASE = os.path.dirname(os.path.abspath(__file__))


def check(label, condition):
    """Koşul false ise -O altında da AssertionError yükseltir."""
    if not condition:
        raise AssertionError(label)
    print(f"{label}: True")


class MCPProcess:
    """Satır protokolünü süre sınırlı okur/yazar; bütün kaynakları kapatır."""

    def __init__(self, env, command=None, timeout=30):
        self.timeout = timeout
        self.out = queue.Queue()
        self.errors = deque(maxlen=20)
        self.threads = []
        self.p = subprocess.Popen(
            command or [sys.executable, os.path.join(BASE, "mcp_sunucu.py")],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=True, encoding="utf-8", env=env, cwd=BASE)
        try:
            self.threads = [
                threading.Thread(target=self._read, daemon=True),
                threading.Thread(target=self._drain_errors, daemon=True),
            ]
            for thread in self.threads:
                thread.start()
        except BaseException:
            self.close()
            raise

    def _read(self):
        try:
            for line in self.p.stdout:
                self.out.put(line)
        finally:
            self.out.put(None)

    def _drain_errors(self):
        for line in self.p.stderr:
            self.errors.append(line)

    def send(self, message):
        """Yazma ve flush da sunucu okumadığında süre aşımına tabidir."""
        outcome = queue.Queue()
        line = json.dumps(message, ensure_ascii=False) + "\n"

        def write():
            try:
                self.p.stdin.write(line)
                self.p.stdin.flush()
                outcome.put(None)
            except Exception as exc:
                outcome.put(exc)

        # Her gönderim beklenir; bir sonraki yazıcı öncekiyle yarışmaz.
        worker = threading.Thread(target=write, daemon=True)
        self.threads.append(worker)
        worker.start()
        try:
            error = outcome.get(timeout=self.timeout)
        except queue.Empty as exc:
            raise AssertionError("MCP yazma zaman aşımı") from exc
        if error is not None:
            raise AssertionError("MCP yazma başarısız") from error

    def recv(self):
        """Yanıt için en fazla timeout saniye bekler; EOF başarı değildir."""
        try:
            line = self.out.get(timeout=self.timeout)
        except queue.Empty as exc:
            raise AssertionError("MCP yanıt zaman aşımı") from exc
        if line is None:
            raise AssertionError("MCP yanıt vermeden kapandı")
        return json.loads(line)

    def close(self):
        """Süreci terminate/kill + wait ile bitirir; thread ve pipe bırakmaz."""
        if self.p.poll() is None:
            self.p.terminate()
        try:
            self.p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            self.p.kill()
            self.p.wait(timeout=5)
        for thread in self.threads:
            if thread.ident is not None:
                thread.join(timeout=5)
        for stream in (self.p.stdin, self.p.stdout, self.p.stderr):
            stream.close()
        if any(t.is_alive() for t in self.threads):
            raise AssertionError("MCP I/O thread kapanmadı")


def main():
    """Tüm özgün entegrasyon senaryolarını geçici dizinlerde çalıştırır."""
    processes = []
    with tempfile.TemporaryDirectory(prefix="test_mcp_") as tmp:
        with ExitStack() as cleanup:
            VERI_DIR = os.path.join(tmp, "ornek_veri")
            LOG_DIR = os.path.join(tmp, "loglar")
            os.makedirs(VERI_DIR, exist_ok=True)
            os.makedirs(LOG_DIR, exist_ok=True)
            CSV = os.path.join(VERI_DIR, "ornek_olaylar.csv")

            rng = random.Random(11)
            with open(CSV, 'w', newline='', encoding='utf-8') as f:
                w = csv.writer(f)
                w.writerow(["id", "tarih", "lat", "lon", "tur", "mahalle", "adet",
                            "adres", "magdur_ad", "supheli", "telefon", "zarar_tl"])
                for i in range(300):
                    hs = rng.choice([(41.035, 28.975), (41.065, 29.01)])
                    lat = hs[0] + rng.gauss(0, 0.004) if rng.random() < 0.6 else 41.03 + rng.uniform(0, 0.06)
                    lon = hs[1] + rng.gauss(0, 0.004) if rng.random() < 0.6 else 28.96 + rng.uniform(0, 0.07)
                    t = datetime(2026, 4, 1) + timedelta(days=rng.randint(0, 100), hours=rng.randint(0, 23))
                    w.writerow([f"O{i}", t.strftime("%Y-%m-%d %H:%M"), round(lat, 6), round(lon, 6),
                                rng.choice(["hırsızlık", "kapkaç", "dolandırıcılık"]),
                                rng.choice(["merkez", "liman", "istasyon"]),
                                rng.randint(1, 5), f"sokak-{rng.randint(1, 40)}",
                                f"Vatandas{i}", f"Kisi{i}", f"0555{i:07d}",
                                rng.randint(500, 60000)])

            env = dict(os.environ)
            env["SINAMA_VERI_KOKU"] = VERI_DIR
            env["SINAMA_LOG_DIR"] = LOG_DIR

            def baslat(kok=VERI_DIR, env_ek=None):
                e = dict(env)
                e["SINAMA_VERI_KOKU"] = kok
                if env_ek:
                    e.update(env_ek)
                process = MCPProcess(e)
                processes.append(process)
                cleanup.callback(process.close)
                return process

            # --- kök guard testleri (Faz 0.2) ---
            print("--- KÖK GUARD ---")
            e = dict(env); del e["SINAMA_VERI_KOKU"]
            p0 = subprocess.run([sys.executable, 'mcp_sunucu.py'], capture_output=True,
                                text=True, encoding="utf-8", env=e, cwd=BASE, timeout=10, input="")
            check("env'siz başlatma reddedildi:", p0.returncode != 0 and "SINAMA_VERI_KOKU ayarlanmalı" in p0.stderr)
            p0b = subprocess.run([sys.executable, 'mcp_sunucu.py'], capture_output=True,
                                 text=True, encoding="utf-8", env={**env, "SINAMA_VERI_KOKU": "/"},
                                 cwd=BASE, timeout=10, input="")
            check("kök='/' reddedildi:", p0b.returncode != 0 and "çok geniş" in p0b.stderr)

            p = baslat()
            def gonder(msg):
                p.send(msg)
            def oku():
                return p.recv()

            gonder({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                    "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                               "clientInfo": {"name": "test", "version": "0"}}})
            check("initialize", bool(oku()["result"]["serverInfo"]))
            gonder({"jsonrpc": "2.0", "method": "notifications/initialized"})
            # H6.2: bilinmeyen istemci protokolü reddedilmez, uyarıyla devam edilir
            gonder({"jsonrpc": "2.0", "id": 99, "method": "initialize",
                    "params": {"protocolVersion": "2025-06-18", "capabilities": {},
                               "clientInfo": {"name": "test", "version": "0"}}})
            _r99 = oku()["result"]
            check("protokol anlaşması (bilinmeyen sürüm):",
                  _r99["protocolVersion"] == "2024-11-05"
                  and "2025-06-18" in _r99.get("protokolUyari", "")
                  and "2024-11-05" in _r99.get("desteklenenProtokoller", []))
            gonder({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
            araclar = [t["name"] for t in oku()["result"]["tools"]]
            check("tools/list", len(araclar) > 0 and len(araclar) == len(set(araclar)))

            def cagir(rid, ad, args):
                gonder({"jsonrpc": "2.0", "id": rid, "method": "tools/call",
                        "params": {"name": ad, "arguments": args}})
                response = oku()
                check(f"{ad}: RPC yanıtı", "result" in response and response.get("id") == rid)
                return response["result"]

            print("--- İŞLEV TESTLERİ ---")
            testler = [
                ("veri_ozeti", {"csv_yolu": "ornek_olaylar.csv"}),
                ("saat_dagilimi", {"csv_yolu": "ornek_olaylar.csv"}),
                ("grid_hotspot", {"csv_yolu": "ornek_olaylar.csv", "hucre_km": 0.5}),
                ("nni", {"csv_yolu": "ornek_olaylar.csv"}),
                ("ki_kare_testi", {"csv_yolu": "ornek_olaylar.csv", "a": "tur", "b": "mahalle"}),
                ("suc_oranlari", {"bolgeler": [{"bolge": "merkez", "olay": 5, "nufus": 10000}]}),
                ("yakin_tekrar", {"csv_yolu": "ornek_olaylar.csv", "mesafe_km": 0.3, "gun": 7, "sim": 49}),
                ("ag_analizi", {"kenarlar": [["A","B",3],["B","C",2],["D","E",4],["C","D",1]],
                                "analiz": "pagerank"}),
                ("koordinat_maskele", {"csv_yolu": "ornek_olaylar.csv", "yaricap_m": 300, "seed": 1}),
            ]
            basarisiz = 0
            for i, (ad, args) in enumerate(testler, start=10):
                r = cagir(i, ad, args)
                if r.get("isError"):
                    basarisiz += 1
                    print(f"[HATA] {ad}: {r['content'][0]['text'][:120]}")
                else:
                    paket = json.loads(r["content"][0]["text"])
                    meta = paket["meta"]
                    print(f"[OK] {ad} | insan_onayi={meta['insan_onayi_gerekir']} | {str(paket['sonuc'])[:90]}...")
            check("işlev grubu", len(testler) - basarisiz == len(testler))

            print("--- GÜVENLİK REGRESYONLARI ---")
            # 1) kök dışı mutlak yol
            r = cagir(50, "veri_ozeti", {"csv_yolu": "/etc/passwd"})
            check("kök dışı reddedildi:", r["isError"] and "dışında" in r["content"][0]["text"])
            # 2) '..' kaçışı
            r = cagir(51, "veri_ozeti", {"csv_yolu": "../mcp_sunucu.py"})
            check("'..' reddedildi:", r["isError"])
            # 3) PII default-deny: magdur_ad/supheli/telefon dönmemeli; 'adet' DÖNMELİ değil (çekirdekte yok)
            r = cagir(52, "orneklem_cek", {"csv_yolu": "ornek_olaylar.csv", "yontem": "basit", "n": 5})
            paket = json.loads(r["content"][0]["text"])
            metin = json.dumps(paket["sonuc"], ensure_ascii=False)
            sizinti = any(x in metin for x in ["magdur_ad", "supheli", "telefon", "Vatandas", "0555"])
            check("PII default-deny (domain terimleri dahil):", not sizinti)
            # 4) beyaz liste
            r = cagir(53, "orneklem_cek", {"csv_yolu": "ornek_olaylar.csv", "yontem": "basit", "n": 3,
                                           "alanlar": ["id", "tur"]})
            satir = json.loads(r["content"][0]["text"])["sonuc"][0]
            check("beyaz liste:", set(satir.keys()) == {"id", "tur"})
            # 5) pii_mi token doğruluğu (birim mantığı)
            from sinama import sunucu
            check("'adet' PII sayılmıyor / 'magdur_ad' sayılıyor",
                  not sunucu.pii_mi("adet") and sunucu.pii_mi("magdur_ad"))
            # 6) şema doğrulama (Faz 1.2)
            gonder({"jsonrpc": "2.0", "id": 60, "method": "tools/call",
                    "params": {"name": "frekans", "arguments": {}}})
            r60 = oku()
            check("zorunlu alan eksik → -32602:", r60["error"]["code"] == -32602)
            gonder({"jsonrpc": "2.0", "id": 61, "method": "tools/call",
                    "params": {"name": "grid_hotspot",
                               "arguments": {"csv_yolu": "ornek_olaylar.csv", "hucre_km": "abc"}}})
            r61 = oku()
            check("tip hatası → -32602:", r61["error"]["code"] == -32602)
            # 7) quadratic guard (Faz 1.1)
            buyuk = [{"id": f"B{i}", "tarih": "2026-05-01 10:00",
                      "lat": 41.0 + (i % 100) * 0.001, "lon": 29.0 + (i // 100) * 0.001}
                     for i in range(6000)]
            r = cagir(62, "yakin_tekrar", {"satirlar": buyuk})
            check("O(n^2) guard reddetti:", r["isError"] and "tavanını" in r["content"][0]["text"])
            # 8) traceback sızıntısı
            r = cagir(63, "benford", {"csv_yolu": "ornek_olaylar.csv", "alan": "yok_boyle_alan"})
            m = r["content"][0]["text"]
            check("traceback yok:", "Traceback" not in m and "/tmp" not in m)

            p.close()
            # 9) audit logu (Faz 1.3)
            audit_yol = os.path.join(LOG_DIR, "sinama_audit.log")
            with open(audit_yol, encoding='utf-8') as f:
                satirlar = f.read().strip().split("\n")
            ornek = json.loads(satirlar[0])
            deger_sizdi = any("ornek_olaylar" in s or "Vatandas" in s or "0555" in s for s in satirlar)
            check("audit / argüman anahtarları / PII", len(satirlar) > 0
                  and "arg_anahtarlari" in ornek and not deger_sizdi)
            print("--- FAZ 1.5: VERİ PROFİLİ + FITNESS GATE ---")
            p = baslat()  # önceki sunucu terminate edildi; yeni oturum
            gonder({"jsonrpc": "2.0", "id": 1, "method": "initialize",
                    "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                               "clientInfo": {"name": "test", "version": "0"}}})
            check("ikinci initialize", bool(oku()["result"]["serverInfo"]))
            gonder({"jsonrpc": "2.0", "method": "notifications/initialized"})
            # 1) veri_kalitesi aracı
            r = cagir(70, "veri_kalitesi", {"csv_yolu": "ornek_olaylar.csv", "analiz": "kde_yogunluk"})
            paket = json.loads(r["content"][0]["text"])["sonuc"]
            check("veri_kalitesi profil + uygunluk + tahribatsızlık",
                  "profil" in paket and "uygunluk" in paket
                  and paket["profil"]["n"] == 300 and "tahribatsizlik" in paket)
            # 2) kapsam zarfı (sessiz filtreleme yasağı)
            r = cagir(71, "grid_hotspot", {"csv_yolu": "ornek_olaylar.csv"})
            kapsam = json.loads(r["content"][0]["text"])["sonuc"]["kapsam"]
            check("kapsam zarfı", kapsam["girdi_n"] == 300
                  and kapsam["analize_giren_n"] == 300 and kapsam["dislanan_n"] == 0
                  and bool(kapsam["dislanma_sebebi"]))
            # 3) payda'sız suc_oranlari reddedilir
            r = cagir(72, "suc_oranlari", {"bolgeler": [{"bolge": "x", "olay": 10}]})
            check("payda'sız reddedildi:", r["isError"] and "fitness gate" in r["content"][0]["text"])
            # 4) benford mertebe gate (zarar_tl 3+ mertebe → uygun; tek mertebeli → ret)
            r = cagir(73, "benford", {"csv_yolu": "ornek_olaylar.csv", "alan": "zarar_tl"})
            sonuc73 = json.loads(r["content"][0]["text"])["sonuc"]
            check("benford (çok mertebeli) çalıştı:", "uyum" in sonuc73)
            tek_mertebe = [{"v": str(100 + i % 900)} for i in range(60)]
            r = cagir(74, "benford", {"satirlar": tek_mertebe, "alan": "v"})
            check("benford (tek mertebe) yapısal reddedildi:", r.get("isError") == True
                  and "fitness gate" in r["content"][0]["text"])
            # 4b) v6.0: standalone mekânsal analiz de kapıdan geçer (bozuk koordinat)
            bozuk = [{"id": f"X{i}", "tarih": "2026-05-01 10:00"} for i in range(40)]
            r = cagir(76, "grid_hotspot", {"satirlar": bozuk})
            check("grid_hotspot (koordinatsız) yapısal reddedildi:", r.get("isError") == True
                  and "fitness gate" in r["content"][0]["text"])
            # 4c) v6.0: uygun çağrıda kapı kararı meta'ya işlenir
            r = cagir(77, "grid_hotspot", {"csv_yolu": "ornek_olaylar.csv"})
            m77 = json.loads(r["content"][0]["text"])["meta"]
            check("meta.gate kayıtlı:", m77.get("gate", {}).get("uygun") == True)
            # 5) ki_kare gate bloğu
            r = cagir(75, "ki_kare_testi", {"csv_yolu": "ornek_olaylar.csv", "a": "tur", "b": "mahalle"})
            sonuc75 = json.loads(r["content"][0]["text"])["sonuc"]
            check("ki_kare gate mevcut:", "gate" in sonuc75)
            print("--- P0-P2: HİPOTEZ TESTLERİ + REGRESYON ---")
            yeni_testler = [
                ("t_testi", {"tip": "bagimsiz", "x": [4,5,6,7,5], "y": [1,2,3,4,2], "welch": True}),
                ("iki_oran_testi", {"x1": 60, "n1": 100, "x2": 40, "n2": 100}),
                ("fisher_exact", {"a": 1, "b": 9, "c": 11, "d": 3}),
                ("binomial_test", {"x": 8, "n": 10, "p0": 0.5}),
                ("mann_whitney", {"x": [1,2,3,4], "y": [5,6,7,8]}),
                ("anova", {"gruplar": {"A": [1,2,3], "B": [4,5,6], "C": [7,8,9]}}),
                ("kruskal_wallis", {"gruplar": {"A": [1,2,3], "B": [4,5,6], "C": [7,8,9]}}),
                ("spearman", {"x": [1,2,3,4,5], "y": [10,20,30,40,50]}),
                ("kendall", {"x": [1,2,3,4], "y": [1,2,3,4]}),
                ("phi", {"a": 10, "b": 0, "c": 0, "d": 10}),
                ("randomizasyon_testi", {"x": [1,1,2,2,1], "y": [9,9,8,9,8], "sim": 199}),
                ("guc_analizi", {"tip": "oran", "p1": 0.5, "p2": 0.6}),
                ("coklu_regresyon", {"X": [[i, i % 3] for i in range(1, 20)],
                                      "y": [2 + 3 * i - (i % 3) for i in range(1, 20)],
                                      "degiskenler": ["x1", "x2"]}),
                ("lojistik_regresyon", {"X": [[x] for x in range(-10, 10)],
                                         "y": [1 if x > 0 else 0 for x in range(-10, 10)]}),
                ("dagilim_olculeri", {"csv_yolu": "ornek_olaylar.csv", "alan": "zarar_tl"}),
            ]
            basarisiz2 = 0
            for i, (ad, args) in enumerate(yeni_testler, start=80):
                r = cagir(i, ad, args)
                if r.get("isError"):
                    basarisiz2 += 1
                    print(f"[HATA] {ad}: {r['content'][0]['text'][:150]}")
                else:
                    paket = json.loads(r["content"][0]["text"])
                    print(f"[OK] {ad}: {str(paket['sonuc'])[:95]}...")
            check("P0-P2 işlev grubu", len(yeni_testler) - basarisiz2 == len(yeni_testler))

            # ============ v5.3: CHI + PPDAC DÖNGÜ ============
            print("--- v5.3: ZARAR (CHI) ARAÇLARI ---")
            r = cagir(90, "zarar_hesapla", {"csv_yolu": "ornek_olaylar.csv",
                                            "grup_alan": "mahalle"})
            z90 = json.loads(r["content"][0]["text"])["sonuc"]
            check("zarar_hesapla", "toplam_zarar" in z90 and "gruplar" in z90
                  and z90["toplam_zarar"] > 0 and z90["olay_sayisi"] == 300)
            r = cagir(91, "power_few", {"csv_yolu": "ornek_olaylar.csv",
                                        "grup_alan": "adres", "hedef_pay": 0.5})
            z91 = json.loads(r["content"][0]["text"])["sonuc"]
            check("power_few", 0 < z91["birim_sayisi"] <= z91["toplam_birim"]
                  and 0 < z91["yogunlasma_orani"] <= 1)
            r = cagir(92, "hacim_zarar_karsilastir", {"csv_yolu": "ornek_olaylar.csv",
                                                      "grup_alan": "mahalle"})
            z92 = json.loads(r["content"][0]["text"])["sonuc"]
            check("hacim_zarar_karsilastir", len(z92) == 3
                  and all("grup" in g and "sinif" in g for g in z92))
            r = cagir(93, "agirlikli_kde", {"csv_yolu": "ornek_olaylar.csv"})
            z93 = json.loads(r["content"][0]["text"])["sonuc"]
            check("agirlikli_kde", len(z93["hucreler"]) > 0
                  and z93["kapsam"]["girdi_n"] == 300
                  and z93["kapsam"]["analize_giren_n"] == 300)
            # meta: CHI araçları insan onayı bayrağı taşımalı
            m93 = json.loads(r["content"][0]["text"])["meta"]
            check("power_few/zarar insan_onayi bayrağı:", m93["insan_onayi_gerekir"])

            print("--- v5.3: BRİFİNG ÜRÜNÜ ---")
            gonder({"jsonrpc": "2.0", "id": 94, "method": "tools/call",
                    "params": {"name": "brifing_uret",
                               "arguments": {"urun_turu": "taktik"}}})
            r94 = oku()
            check("belirsizlik'siz brifing → -32602:", r94["error"]["code"] == -32602)
            r = cagir(95, "brifing_uret",
                      {"urun_turu": "taktik",
                       "talep": {"karar": "gece devriye planı", "kapsam": "merkez"},
                       "hotspot": z93["hucreler"][:3],
                       "belirsizlik": ["300 olay, 100 gün; mevsimsel etki test edilmedi"]})
            z95 = json.loads(r["content"][0]["text"])["sonuc"]
            check("brifing_uret ürün + belirsizlik", len(z95["urun"]) > 0
                  and "Belirsizlik ve sınırlar" in z95["urun"])

            print("--- v5.3: PPDAC DÖNGÜSÜ (tam tur) ---")
            r = cagir(96, "dongu_baslat", {"soran": "komiser A", "karar": "kapkaç artışına müdahale",
                                           "kapsam": "merkez-liman", "urun_turu": "taktik"})
            z96 = json.loads(r["content"][0]["text"])["sonuc"]
            OID = z96["oturum_id"]
            check("dongu_baslat", z96["faz"] == "PLAN"
                  and z96["plan"]["urun_turu"] == "taktik" and len(z96["plan"]["onerilen"]) > 0)
            # faz atlama reddedilmeli: PLAN'dayken doğrudan analiz (gerekçe verse bile)
            r = cagir(97, "dongu_analiz", {"oturum_id": OID, "arac": "frekans",
                                           "argumanlar": {"csv_yolu": "ornek_olaylar.csv",
                                                          "alan": "tur"},
                                           "gerekce": {"hipotez": "h", "yorum": "y"}})
            check("faz atlama reddedildi (PLAN→analiz):", r.get("isError") == True)
            # v6.2: gerekçesiz adım şema düzeyinde reddedilir (-32602)
            gonder({"jsonrpc": "2.0", "id": 970, "method": "tools/call",
                    "params": {"name": "dongu_analiz",
                               "arguments": {"oturum_id": OID, "arac": "frekans"}}})
            r970 = oku()
            check("gerekçesiz dongu_analiz → -32602:", r970["error"]["code"] == -32602)
            r = cagir(98, "dongu_veri", {"oturum_id": OID,
                                         "csv_yolu": "ornek_olaylar.csv",
                                         "analiz": "kde_yogunluk"})
            z98 = json.loads(r["content"][0]["text"])["sonuc"]
            check("dongu_veri", z98["faz"] == "VERI" and z98["uygunluk"]["uygun"])
            r = cagir(99, "dongu_analize_gec", {"oturum_id": OID,
                                                "uygunluk": z98["uygunluk"]})
            check("dongu_analize_gec", json.loads(r["content"][0]["text"])["sonuc"]["faz"] == "ANALIZ")
            r = cagir(100, "dongu_analiz", {"oturum_id": OID, "arac": "grid_hotspot",
                                            "argumanlar": {"csv_yolu": "ornek_olaylar.csv"},
                                            "gerekce": {
                                             "hipotez": "liman-merkez aksında gece kümelenmesi",
                                             "yorum": "hotspot hücreleri iki odakta toplanıyor",
                                             "cikarim": "gece devriyesi liman çevresine kaydırılabilir",
                                             "alternatifler": ["raporlama artışı", "tek etkinlik"]}})
            z100 = json.loads(r["content"][0]["text"])["sonuc"]
            check("dongu_analiz (grid_hotspot):", "hucreler" in z100 or "kapsam" in z100)
            # v6.0: döngü içi çağrı da aynı kapıdan geçer — payda'sız oran reddedilir
            r = cagir(107, "dongu_analiz", {"oturum_id": OID, "arac": "suc_oranlari",
                                            "argumanlar": {"bolgeler": [{"bolge": "x",
                                                                         "olay": 5}]},
                                            "gerekce": {"hipotez": "h", "yorum": "y"}})
            check("döngü içi kapı reddi (payda'sız oran):", r.get("isError") == True
                  and "fitness gate" in r["content"][0]["text"])
            # v6.2: iç içe döngü çağrısı da gerekçe şemasına tabi
            r = cagir(101, "dongu_analiz", {"oturum_id": OID, "arac": "dongu_durum",
                                            "argumanlar": {},
                                            "gerekce": {"hipotez": "h", "yorum": "y"}})
            # iç içe döngü çağrısı reddedilmeli (gerekçeli çağrı iç mantık reddine ulaşır)
            check("iç içe döngü reddedildi:", r.get("isError") == True)
            # insan onayı olmadan sonuç: şema 'onaylayan'ı zorunlu tutar → -32602
            gonder({"jsonrpc": "2.0", "id": 102, "method": "tools/call",
                    "params": {"name": "dongu_sonuc",
                               "arguments": {"oturum_id": OID,
                                             "sonuc_turu": "mudahale_onerildi"}}})
            r102 = oku()
            check("onaysız sonuç → -32602:", r102["error"]["code"] == -32602)
            r = cagir(103, "dongu_sonuc", {"oturum_id": OID,
                                           "sonuc_turu": "mudahale_onerildi",
                                           "onaylayan": "analist B",
                                           "bulgular": ["liman çevresi gece hotspot"]})
            z103 = json.loads(r["content"][0]["text"])["sonuc"]
            check("dongu_sonuc", z103["faz"] == "SONUC"
                  and z103["sonuc"]["tur"] == "mudahale_onerildi")
            r = cagir(104, "dongu_izleme", {"oturum_id": OID, "metrik": "haftalık kapkaç",
                                            "esik": 5, "kontrol_tarihi": "2026-08-01"})
            check("dongu_izleme:", "izleme" in json.loads(r["content"][0]["text"])["sonuc"])
            r = cagir(105, "dongu_durum", {"oturum_id": OID})
            z105 = json.loads(r["content"][0]["text"])["sonuc"]
            check("dongu_durum manifesto", z105["faz"] == "SONUC"
                  and len(z105["insan_onaylari"]) == 1 and len(z105["gecmis"]) == 6)
            r = cagir(106, "dongu_durum", {})
            check("açık oturum listesi", any(m["oturum_id"] == OID
                  for m in json.loads(r["content"][0]["text"])["sonuc"]))

            print("--- v6.3: FAZ E — METODOLOJİK DERİNLİK ---")
            # E2: iki Poisson oranı exact karşılaştırma (yeni araç)
            r = cagir(110, "oran_karsilastir", {"k1": 30, "e1": 100, "k2": 20, "e2": 200})
            z110 = json.loads(r["content"][0]["text"])["sonuc"]
            check("oran_karsilastir", z110["oran_orani"] == 3.0
                  and 1 < z110["ga_alt"] < 3 < z110["ga_ust"] and z110["p"] < .05
                  and bool(z110["yorum"]))
            r = cagir(111, "oran_karsilastir", {"k1": 10, "e1": 100, "k2": 20, "e2": 200})
            z111 = json.loads(r["content"][0]["text"])["sonuc"]
            check("eşit oran GA 1 içerir:", z111["ga_alt"] < 1 < z111["ga_ust"])
            # E3: NNI Donnelly kenar düzeltmesi araç üzerinden
            r = cagir(112, "nni", {"csv_yolu": "ornek_olaylar.csv",
                                   "kenar_duzeltme": True})
            z112 = json.loads(r["content"][0]["text"])["sonuc"]
            check("nni Donnelly", z112["kenar_duzeltme"] is True
                  and isinstance(z112["z"], (int, float)) and z112["beklenen"] > 0)
            # E1: bolge_anomali aşırı yayılımda negatif binom modeli
            asiri = ([{"mahalle": f"m{i % 11}", "tur": "hırsızlık",
                       "tarih": "2026-05-01 10:00"} for i in range(55)] +
                     [{"mahalle": "m11", "tur": "hırsızlık",
                       "tarih": "2026-05-01 10:00"} for _ in range(100)])
            s = cagir(113, "bolge_anomali", {"satirlar": asiri, "bolge_alan": "mahalle"})
            z113 = json.loads(s["content"][0]["text"])["sonuc"]
            check("bolge_anomali model", z113["model"] == "neg-binom"
                  and z113["dispersiyon_orani"] > 1
                  and "m11" in [b["bolge"] for b in z113["anlamli"]])

            print("--- v6.4: FAZ F/G + P2 ---")
            # K20: nominal alanda sayısal özet yapısal reddedilir
            r = cagir(114, "dagilim_olculeri", {"csv_yolu": "ornek_olaylar.csv",
                                                "alan": "tur"})
            check("dagilim_olculeri (nominal) reddedildi:", r.get("isError") == True
                  and "nominal" in r["content"][0]["text"])
            r = cagir(115, "dagilim_olculeri", {"csv_yolu": "ornek_olaylar.csv",
                                                "alan": "lat"})
            check("dagilim_olculeri (sayısal) geçti:", not r.get("isError"))
            # P2: kanit_dogrula — tam PPDAC oturumunun zinciri sağlam
            r = cagir(116, "kanit_dogrula", {"oturum_id": OID})
            z116 = json.loads(r["content"][0]["text"])["sonuc"]
            check("kanit_dogrula", z116["saglam"] and z116["olay_sayisi"] == 6
                  and z116["bozuk_adim"] is None)

            print("--- v6.2: KANIT + MUHAKEME İZİ ---")
            # muhakeme_izi aracı: olgu/gerekçe ayrımlı çıktı
            r = cagir(108, "muhakeme_izi", {"oturum_id": OID})
            z108 = json.loads(r["content"][0]["text"])["sonuc"]["urun"]
            check("muhakeme_izi / olgu-gerekçe / hipotez", "Muhakeme İzi" in z108
                  and "OLGU (K1/K2)" in z108 and "GEREKÇE (K3" in z108
                  and "liman-merkez" in z108)
            # brifing_uret + oturum_id → ürüne muhakeme izi eklenir
            r = cagir(109, "brifing_uret",
                      {"urun_turu": "taktik", "oturum_id": OID,
                       "belirsizlik": ["100 günlük veri; mevsimsel etki test edilmedi"]})
            z109 = json.loads(r["content"][0]["text"])["sonuc"]["urun"]
            check("brifing + muhakeme + belirsizlik", "Muhakeme İzi" in z109
                  and "Belirsizlik ve sınırlar" in z109)
            # Katman 1: olay akışı dosyada, gerekçe içeriyor, PII değeri yok
            import glob
            akislar = glob.glob(os.path.join(LOG_DIR, "oturumlar", f"{OID}.olaylar.jsonl"))
            ham = ""
            if akislar:
                with open(akislar[0], encoding="utf-8") as f:
                    ham = f.read()
            satir_sayisi = len([s for s in ham.splitlines() if s.strip()])
            check("olay akışı / gerekçe / PII", len(akislar) == 1 and satir_sayisi == 6
                  and "hipotez" in ham and "Vatandas" not in ham and "0555" not in ham)

            print("--- v6.5: DAYANIKLILIK + HATA TAKSONOMİSİ (H1/H2) ---")
            # H2.3: her hata tipi yapısal bildirilir + düzeltici ÖNERİ taşır
            r = cagir(117, "oran_karsilastir", {"k1": 5, "e1": 0, "k2": 3, "e2": 100})
            t117 = r["content"][0]["text"]
            check("veri tipi + öneri:", r.get("isError") and "HATA [veri]:" in t117
                  and "ÖNERİ:" in t117)
            r = cagir(118, "frekans", {"alan": "tur"})  # csv/satirlar yok
            t118 = r["content"][0]["text"]
            check("kullanim tipi + öneri:", r.get("isError")
                  and "HATA [kullanim]:" in t118 and "ÖNERİ:" in t118)
            r = cagir(119, "dongu_analiz",
                      {"oturum_id": "yokboyle", "arac": "nni",
                       "gerekce": {"hipotez": "h", "yorum": "y"}})
            t119 = r["content"][0]["text"]
            check("dongu tipi:", r.get("isError") and "HATA [dongu]:" in t119)
            r = cagir(120, "veri_ozeti", {"csv_yolu": "../kacis.csv"})
            t120 = r["content"][0]["text"]
            check("guvenlik tipi + öneri:", r.get("isError")
                  and "HATA [guvenlik]:" in t120 and "ÖNERİ:" in t120)

            # H1.3: keşif oturumu yazılamazsa meta.kanit_durumu GÜRÜLTÜLÜ işaretlenir
            oturumlar = os.path.join(LOG_DIR, "oturumlar")
            yedek = os.path.join(LOG_DIR, "oturumlar_yedek")
            os.rename(oturumlar, yedek)
            with open(oturumlar, "w") as f:  # dizin oluşumunu engelleyen DOSYA
                f.write("engel")
            try:
                r = cagir(121, "nni", {"csv_yolu": "ornek_olaylar.csv"})
                m121 = json.loads(r["content"][0]["text"])["meta"]
                check("kanıt kaybı gürültülü (yazılamadı bayrağı):",
                          m121.get("kanit_durumu") == "YAZILAMADI"
                          and m121.get("oturum_izlendi") is False
                          and any("KANIT KAYBI" in u for u in m121["uyarilar"])
                      and not r.get("isError"))  # sonuç döner ama işaretli
            finally:
                os.remove(oturumlar)
                os.rename(yedek, oturumlar)

            # H1.4: çökme sonrası yukle uzlaştırması — manifesto geriye alınırsa
            # dongu_durum kanit_uyari gösterir ve gecmis akıştan onarılır
            mjson = os.path.join(LOG_DIR, "oturumlar", f"{OID}.json")
            with open(mjson, encoding="utf-8") as f:
                m = json.load(f)
            m["gecmis"] = m["gecmis"][:-1]
            with open(mjson, "w", encoding="utf-8") as f:
                json.dump(m, f, ensure_ascii=False)
            r = cagir(122, "dongu_durum", {"oturum_id": OID})
            m122 = json.loads(r["content"][0]["text"])["sonuc"]
            check("çökme onarımı + uyarı:", "onarım" in m122.get("kanit_uyari", "")
                  and len(m122["gecmis"]) == 6)

            p.close()
        check("MCP süreçleri/pipe/thread temizliği",
              all(p.p.poll() is not None
                  and all(s.closed for s in (p.p.stdin, p.p.stdout, p.p.stderr))
                  and all(not t.is_alive() for t in p.threads) for p in processes))
    print("TEST BİTTİ")
    return 0


if __name__ == "__main__":
    sys.exit(main())
