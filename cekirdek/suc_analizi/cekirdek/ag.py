# -*- coding: utf-8 -*-
"""
ag.py — İlişki/ağ analizi: derece merkeziyeti, aracılık merkeziyeti
(Brandes algoritması), bağlı bileşenler, birlikte-olay ağı.
Saf Python; büyük ağlar için aracılık merkeziyeti yavaşlayabilir.
"""

from collections import defaultdict, deque


def ag_kur(baglanti_listesi):
    """
    baglanti_listesi: [(dugum1, dugum2, agirlik), ...] yönsüz varsayılır.
    Dönüş: {dugum: {komsu: agirlik}}
    """
    g = defaultdict(dict)
    for e in baglanti_listesi:
        a, b = e[0], e[1]
        w = e[2] if len(e) > 2 else 1.0
        g[a][b] = g[a].get(b, 0.0) + w
        g[b][a] = g[b].get(a, 0.0) + w
    return dict(g)


def derece_merkeziyeti(g):
    """Her düğüm için (derece, ağırlıklı derece). Azalan sıralı."""
    sonuc = []
    for d, komsular in g.items():
        sonuc.append({"dugum": d, "derece": len(komsular),
                      "agirlikli_derece": round(sum(komsular.values()), 2)})
    sonuc.sort(key=lambda x: (-x["agirlikli_derece"], -x["derece"]))
    return sonuc


def bagli_bilesenler(g):
    """Bağlı bileşenleri (suç grubu kümeleri) bulur."""
    goruldu = set()
    bilesenler = []
    for dugum in g:
        if dugum in goruldu:
            continue
        kume, kuyruk = set(), deque([dugum])
        while kuyruk:
            d = kuyruk.popleft()
            if d in kume:
                continue
            kume.add(d)
            goruldu.add(d)
            kuyruk.extend(k for k in g.get(d, {}) if k not in kume)
        bilesenler.append(sorted(kume))
    bilesenler.sort(key=len, reverse=True)
    return bilesenler


def aracilik_merkeziyeti(g):
    """
    Brandes algoritması (ağırlıksız). Köprü/aracı kişileri bulur.
    Dönüş: {dugum: skor} azalan sıralı liste.
    """
    cb = {v: 0.0 for v in g}
    for s in g:
        yigin, oncul, sigma, mesafe = [], {v: [] for v in g}, {v: 0 for v in g}, {v: -1 for v in g}
        sigma[s] = 1
        mesafe[s] = 0
        kuyruk = deque([s])
        while kuyruk:
            v = kuyruk.popleft()
            yigin.append(v)
            for w in g.get(v, {}):
                if mesafe[w] < 0:
                    kuyruk.append(w)
                    mesafe[w] = mesafe[v] + 1
                if mesafe[w] == mesafe[v] + 1:
                    sigma[w] += sigma[v]
                    oncul[w].append(v)
        delta = {v: 0.0 for v in g}
        while yigin:
            w = yigin.pop()
            for v in oncul[w]:
                delta[v] += (sigma[v] / sigma[w]) * (1 + delta[w])
            if w != s:
                cb[w] += delta[w]
    return sorted(({"dugum": d, "aracilik": round(s / 2, 3)}
                   for d, s in cb.items()), key=lambda x: -x["aracilik"])


def birlikte_olay_ag(kayitlar, olay_alan, kisi_alan):
    """
    Aynı olaya karışan kişiler arasında kenar kurar (co-offending ağı).
    Dönüş: ag_kur formatına uygun bağlantı listesi.
    """
    olay_kisiler = defaultdict(set)
    for k in kayitlar:
        olay, kisi = k.get(olay_alan), k.get(kisi_alan)
        if olay and kisi:
            olay_kisiler[olay].add(kisi)
    kenar_agirlik = defaultdict(float)
    for kisiler in olay_kisiler.values():
        kl = sorted(kisiler)
        for i in range(len(kl)):
            for j in range(i + 1, len(kl)):
                kenar_agirlik[(kl[i], kl[j])] += 1.0
    return [(a, b, w) for (a, b), w in kenar_agirlik.items()]


# --- Genişletme: topluluk tespiti, PageRank, ego ağı, en kısa yol ---

import random


def topluluk_tespiti(g, max_iter=30, seed=None):
    """
    Label propagation ile topluluk (suç grubu) tespiti.
    UYARI: algoritma doğası gereği kararsızdır; farklı seed'lerde
    topluluk sınırları değişebilir. Kritik tespitlerde birden çok
    koşuda istikrarlı kalan kümeleri esas alın.
    Dönüş: {topluluk_id: [düğümler]} büyükten küçüğe.
    """
    rng = random.Random(seed)
    etiket = {v: i for i, v in enumerate(g)}
    dugumler = list(g.keys())
    for _ in range(max_iter):
        degisim = False
        rng.shuffle(dugumler)
        for v in dugumler:
            komsu_etiket = defaultdict(float)
            for w, agirlik in g.get(v, {}).items():
                komsu_etiket[etiket[w]] += agirlik
            if not komsu_etiket:
                continue
            en = max(komsu_etiket.items(), key=lambda x: x[1])[0]
            if en != etiket[v]:
                etiket[v] = en
                degisim = True
        if not degisim:
            break
    topluluklar = defaultdict(list)
    for v, e in etiket.items():
        topluluklar[e].append(v)
    sonuc = {i: sorted(uyeler) for i, uyeler in
             enumerate(sorted(topluluklar.values(), key=len, reverse=True))}
    return sonuc


def pagerank(g, sonumleme=0.85, max_iter=100, tol=1e-6):
    """
    PageRank etki merkeziyeti (ağırlıklı kenarlarla).
    Dönüş: [{'dugum', 'skor'}] azalan sıralı.
    """
    dugumler = list(g.keys())
    n = len(dugumler)
    if n == 0:
        return []
    pr = {v: 1.0 / n for v in dugumler}
    cikis_agirlik = {v: sum(g[v].values()) or 1e-9 for v in dugumler}
    for _ in range(max_iter):
        yeni = {v: (1 - sonumleme) / n for v in dugumler}
        for v in dugumler:
            for w, agirlik in g.get(v, {}).items():
                yeni[w] += sonumleme * pr[v] * agirlik / cikis_agirlik[v]
        fark = sum(abs(yeni[v] - pr[v]) for v in dugumler)
        pr = yeni
        if fark < tol:
            break
    return sorted(({"dugum": v, "skor": round(s, 5)} for v, s in pr.items()),
                  key=lambda x: -x["skor"])


def ego_agi(g, dugum, adim=1):
    """Bir düğümün 'adim' mesafedeki komşuluk alt ağını döner."""
    if dugum not in g:
        return {}
    sinir = {dugum}
    for _ in range(adim):
        yeni = set(sinir)
        for d in sinir:
            yeni.update(g.get(d, {}))
        sinir = yeni
    return {d: {k: v for k, v in g.get(d, {}).items() if k in sinir}
            for d in sinir}


def en_kisa_yol(g, kaynak, hedef):
    """BFS ile iki kişi arasındaki bağlantı zinciri (düğüm listesi)."""
    if kaynak not in g or hedef not in g:
        return None
    kuyruk = deque([[kaynak]])
    goruldu = {kaynak}
    while kuyruk:
        yol = kuyruk.popleft()
        son = yol[-1]
        if son == hedef:
            return yol
        for komsu in g.get(son, {}):
            if komsu not in goruldu:
                goruldu.add(komsu)
                kuyruk.append(yol + [komsu])
    return None
