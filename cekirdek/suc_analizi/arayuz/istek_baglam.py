"""İstek ömrüyle sınırlı metadata ve hazırlanmış girdi önbelleği."""
from contextvars import ContextVar

_istek = ContextVar('suc_analizi_istek', default=None)


def yeni_baglam():
    """Çağrı için bağımsız bağlam kurar; dönen token reset edilmelidir."""
    return _istek.set({'satir': None, 'kesildi': False, 'uyarilar': [], 'hazir': {}})


def baglam():
    """Aktif bağlamı veya bağlam dışı çağrılarda None döner."""
    return _istek.get()


def baglam_bitir(token):
    """Üst çağrının bağlamını geri yükler; kardeş çağrılara veri sızdırmaz."""
    _istek.reset(token)
