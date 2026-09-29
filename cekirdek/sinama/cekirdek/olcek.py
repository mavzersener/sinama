# -*- coding: utf-8 -*-
"""
olcek.py — Bileşik ölçüm: endeks kurma ve güvenilirlik
(Maxfield & Babbie, Bölüm 5: levels of measurement, composite measures,
Index of Disorder, reliability).
"""

import statistics


def min_max_normalize(degerler, ters=False):
    """0-1 aralığına normalleştirme; ters=True ise gösterge ters yönlüdür."""
    d = [float(x) for x in degerler]
    lo, hi = min(d), max(d)
    if hi == lo:
        return [0.5] * len(d)
    if ters:
        return [round((hi - x) / (hi - lo), 4) for x in d]
    return [round((x - lo) / (hi - lo), 4) for x in d]


def endeks_kur(kayitlar, gostergeler, agirliklar=None, tersler=None):
    """
    Bileşik endeks (Ch 5: Index of Disorder örneği).
    gostergeler: alan adları listesi; her biri önce min-max normalize edilir,
    sonra ağırlıklı ortalaması alınır.
    agirliklar: {alan: ağırlık} (verilmezse eşit)
    tersler: ters yönlü gösterge alanları (yüksek değer = düşük kavram)
    Dönüş: her kayda 'endeks' eklenmiş liste (0-100 ölçeğinde).
    """
    agirliklar = agirliklar or {}
    tersler = set(tersler or [])
    norm = {}
    for g in gostergeler:
        degerler = []
        for k in kayitlar:
            try:
                degerler.append(float(k.get(g)))
            except (TypeError, ValueError):
                degerler.append(0.0)
        norm[g] = min_max_normalize(degerler, ters=(g in tersler))
    toplam_w = sum(float(agirliklar.get(g, 1.0)) for g in gostergeler) or 1.0
    sonuc = []
    for i, k in enumerate(kayitlar):
        skor = sum(norm[g][i] * float(agirliklar.get(g, 1.0))
                   for g in gostergeler) / toplam_w
        yeni = dict(k)
        yeni["endeks"] = round(skor * 100, 2)
        sonuc.append(yeni)
    return sonuc


def cronbach_alfa(madde_yanitlari):
    """
    Cronbach alfa güvenilirlik katsayısı (Ch 5: reliability).
    madde_yanitlari: satır=kişi/birim, sütun=madde; [[x1, x2, ...], ...]
    alfa >= 0.7 kabul edilebilir sayılır.
    """
    if not madde_yanitlari or len(madde_yanitlari[0]) < 2:
        return None
    k = len(madde_yanitlari[0])
    sutunlar = list(zip(*madde_yanitlari))
    madde_varyanslari = []
    for sut in sutunlar:
        if len(sut) < 2:
            return None
        madde_varyanslari.append(statistics.pvariance([float(x) for x in sut]))
    toplamlar = [sum(float(x) for x in satir) for satir in madde_yanitlari]
    toplam_varyans = statistics.pvariance(toplamlar)
    if toplam_varyans == 0:
        return None
    alfa = (k / (k - 1)) * (1 - sum(madde_varyanslari) / toplam_varyans)
    return round(alfa, 4)


def olcum_duzeyi_belirle(degerler):
    """
    Veri örneğine bakarak olası ölçüm düzeyi önerisi
    (Ch 5: nominal/ordinal/interval-ratio ayrımı analiz seçimini belirler).
    """
    sayisal = True
    for d in degerler:
        try:
            float(d)
        except (TypeError, ValueError):
            sayisal = False
            break
    if sayisal:
        return "aralik/oran (ortalama, std, Pearson uygulanabilir)"
    benzersiz = len(set(str(d) for d in degerler))
    if benzersiz <= 2:
        return "nominal-ikili (mod, lambda, ki-kare uygulanabilir)"
    return "nominal/ordinal (mod, frekans, ki-kare, gamma uygulanabilir; ortalama UYGUN DEĞİL)"
