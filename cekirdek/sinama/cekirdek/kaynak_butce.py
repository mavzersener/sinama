"""Hesaplama öncesi deterministik tavanlar; süre garantisi veya iptal mekanizması değildir."""
import math
from .hatalar import KullanimHatasi

MAKS_QUADRATIC_N = 5000
MAKS_GRID = 20000
MAKS_KATKI = 5000000
MAKS_SIM = 999


def _pozitif(v, alan):
    """Sonlu, pozitif sayısal parametre; bool sayı sayılmaz."""
    try:
        if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0:
            raise ValueError
    except (ValueError, OverflowError):
        raise KullanimHatasi(f'{alan}: sonlu pozitif sayı gerekli') from None


def _grid_butce(n, ni, nj):
    """Tam KDE ızgarasının hücre ve katkı sayısını allocation öncesinde sınırlar."""
    if n > MAKS_QUADRATIC_N or ni * nj > MAKS_GRID or ni * nj * n > MAKS_KATKI:
        raise KullanimHatasi('KDE: kayıt/grid/katkı bütçesi aşıldı', oneri='hücre boyunu büyütün veya kayıtları süzün')


def _sim_butce(n, sim, sifir_izinli=False):
    """İndeksten bağımsız muhafazakâr sim*n*(n-1)/2 aday üst sınırı."""
    if (isinstance(sim, bool) or not isinstance(sim, int) or
            not (0 if sifir_izinli else 1) <= sim <= MAKS_SIM):
        raise KullanimHatasi('sim: izinli tamsayı aralığı dışında')
    if n > MAKS_QUADRATIC_N or sim * n * (n-1) // 2 > MAKS_KATKI:
        raise KullanimHatasi('sim: aday çift bütçesi aşıldı', oneri='sim veya kayıt sayısını azaltın')
