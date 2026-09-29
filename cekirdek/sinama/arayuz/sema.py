# -*- coding: utf-8 -*-
r"""
arayuz/sema.py — sunucu-tarafı şema doğrulama (Faz 1.2, -32602).
Stdlib mini doğrulayıcı; istemci hatası sunucuya değil çağırana döner.
"""

import math

_TIP_ESLEME = {
    "string": lambda v: isinstance(v, str),
    "number": lambda v: isinstance(v, (int, float)) and not isinstance(v, bool),
    "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    "array": lambda v: isinstance(v, list),
    "object": lambda v: isinstance(v, dict),
    "boolean": lambda v: isinstance(v, bool),
}


def sema_dogrula(ad, sema_so, arg, uyarilar=None):
    """Recursive mini şema: hata yolu veya None; bilinmeyen alanlar uyarilar'a eklenir."""
    def kontrol(v, s, yol):
        """Şema olmayan alt değerlerde de iç alanları ve NaN/Inf'i reddeder."""
        if isinstance(v, float) and not math.isfinite(v):
            return f'{yol}: sonlu sayı gerekli'
        tip = s.get('type')
        if tip in _TIP_ESLEME and not _TIP_ESLEME[tip](v):
            return f'{yol}: {tip} olmalı'
        if 'enum' in s and not any(v == e and isinstance(v, bool) == isinstance(e, bool) for e in s['enum']):
            return f'{yol}: izinli enum değeri gerekli'
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            if 'minimum' in s and v < s['minimum']:
                return f'{yol}: minimum sınırı'
            if 'maximum' in s and v > s['maximum']:
                return f'{yol}: maximum sınırı'
        if isinstance(v, list):
            if len(v) < s.get('minItems', 0) or len(v) > s.get('maxItems', float('inf')):
                return f'{yol}: dizi uzunluğu sınırı'
            for i, deger in enumerate(v):
                hata = kontrol(deger, s.get('items', {}), f'{yol}[{i}]')
                if hata:
                    return hata
        if isinstance(v, dict):
            for g in s.get('required', []):
                if g not in v:
                    return f'{yol}.{g}: zorunlu alan eksik'
            props = s.get('properties', {})
            ek = s.get('additionalProperties', True)
            for k, deger in v.items():
                if not isinstance(k, str) or k.startswith('_'):
                    return f'{yol}: iç alan adı yasak'
                alt_yol = f'{yol}.{k}'
                if k not in props:
                    if ek is False:
                        return f'{alt_yol}: bilinmeyen alan'
                    if uyarilar is not None and 'properties' in s and not isinstance(ek, dict):
                        uyarilar.append(f'bilinmeyen alan: {alt_yol}')
                alt = props.get(k, ek if isinstance(ek, dict) else {})
                hata = kontrol(deger, alt, alt_yol)
                if hata:
                    return hata
        return None
    try:
        if not isinstance(arg, dict):
            return f'{ad}: arguments nesne olmalı'
        return kontrol(arg, sema_so, ad)
    except RecursionError:
        return f'{ad}: iç içe alan derinliği sınırı'
