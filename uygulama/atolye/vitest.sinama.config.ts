// Sınama A6: gerçek arka uca karşı koşan JS testleri (tests/sinama/*.sinama.ts).
// Varsayılan `vitest run` bunları ALMAZ (sunucu ister); onları Python test sürücüsü
// (tests/test_atolye_kanit_uctan_uca.py) sunucuyu kurup bu yapılandırmayla çalıştırır.
import taban from "./vitest.config";

export default {
  ...taban,
  test: { ...taban.test, include: ["tests/sinama/**/*.sinama.ts"] },
};
