# Arayüz test programı

Gerçek fare olaylarıyla, gerçek Chromium'da senaryo tabanlı arayüz testleri.

## Çalıştırma

```bash
npm run ui
```

Dev sunucu açık değilse kendisi başlatır; açıksa mevcut sunucuyu kullanır.

Testleri gözünüzle izlemek için:

```bash
npm run ui:headed
```

Başarısızlık sonrası ayrıntılı rapor (ekran görüntüsü, video, iz):

```bash
npm run ui:rapor
```

## Neden ayrı bir koşucu

`vitest` bu projede **saf mantık** testleri için kullanılıyor (`environment: node`,
DOM yok). Arayüz sorunlarının çoğu orada görünmez:

- kırpılan tıklama alanı,
- ölçülmediği için görünmez kalan düğüm,
- sürüklenemeyen bağlantı,
- üstünü başka elemanın kapattığı düğme.

Bunlar yalnız gerçek bir tarayıcıda, gerçek fare olaylarıyla ortaya çıkar.

**Uygulama içi önizleme paneli bu iş için yetersizdir:** orada ResizeObserver
tetiklenmediği için React Flow düğümleri `visibility: hidden` kalır ve hiçbir
tıklama isabet etmez. Panelde ölçülen "görünmez düğüm" bulgusu bir ortam
artefaktıdır, gerçek kullanıcıyı etkilemez. Playwright'ın Chromium'u gerçek
ölçüm yapar; bu yüzden gerçek kusurları da o gösterir.

## Senaryolar

| Dosya | Kapsam |
|---|---|
| `01-acilis.spec.ts` | Uygulama yüklenir, araç çubuğu görünür, Demo grafı çizilir, düğümler **ölçülür** |
| `02-node-baglama.spec.ts` | Handle'lar var, tıklanabilir, tutulabilir alanı yeterli, iki düğüm fareyle **bağlanır** |
| `03-modlar.spec.ts` | Rehberli Mod / Akademik Mod açılır-kapanır, ön-kayıt kapısı sırası, motor kapalıyken açık bildirim |

## Teşhis: `handleTani`

Bir bağlantı kurulamadığında "kurulamadı" demek yetmez. `yardimcilar.ts`
içindeki `handleTani`, engeli sırayla ölçer ve **insan okuyabilir bir teşhis**
döndürür:

1. Eleman DOM'da var mı
2. `visibility` / `display` uygun mu
3. `pointer-events` açık mı
4. Boyutu sıfır mı
5. Ebeveyn **kırpıyor** mu (taşma varsa tutulabilir alan daralır)
6. Merkezine gerçekten kendisi mi isabet ediyor

Her madde ayrı bir düzeltme demektir; bu yüzden ayrı ayrı raporlanır.

## Bulunan ve düzeltilen kusur (29 Tem 2026)

Kullanıcı düğümleri birbirine bağlayamadığını bildirdi. Bu program sorunu
gerçek tarayıcıda üretti ve kök nedeni ölçtü:

- `src/index.css` içinde `.react-flow__node { overflow: hidden }` vardı.
- `.react-flow__node`, React Flow'un düğüm sarmalayıcısıdır ve bağlantı
  tutamakları **tanımı gereği** bu kutunun dışına taşar.
- Ölçüm: tutamak 9.2px, taşma 9.2px → **tamamen kırpılıyor**; merkezine tuval
  (`react-flow__pane`) isabet ediyordu. Yani tutulabilir alan sıfırdı.
- `CustomNode`'un kök div'inde de aynı sorun vardı (`overflow-hidden` +
  handle'lar `left/right: -6`).

Düzeltme: kırpma iki yerden de kaldırıldı; köşe yuvarlama/içerik kırpması
`CustomNode`'un **iç gövdesine** indi, tutamaklar kırpılmayan dış katmanda
kaldı. Tutamak boyutu 12px → 14px yapıldı (8px'lik nokta fareyle güvenilir
tutulamıyordu).

Regresyon koruması: `02-node-baglama.spec.ts`. Biri yeniden `overflow: hidden`
eklerse bu testler kırılır.
