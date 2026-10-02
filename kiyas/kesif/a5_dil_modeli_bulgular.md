# A5 keşfi — opsiyonel dil modeli yolları (ön-kayıt dışı, CI dışı)

`a5_dil_modeli.py`, yerel Qwen3.8-27B (llama.cpp b10644, `http://127.0.0.1:8080`), 02.10.2026.
Dil modeli belirlenimci olmadığı için BMK'ya girmez; ADR-003 md. 5'teki "dil modelli sistem
ölçütleri ayrı ve opsiyonel" kapsamındadır.

## Bulgu: düşünme kipi içeriği boş bırakıyordu

İlk koşuda soru türü önerisi 10 sorunun **hiçbirinde** dil modelinden gelmedi (hepsi kurala
düştü) ve sade dille özet iki dilde de 422 verdi. Ham yanıt: `content: ""`,
`reasoning_content: "We need answer user's Turkish question:"`, `finish_reason: "length"` —
model sınırlı token bütçesini düşünmeye harcıyordu. Düzeltme: isteklerde
`chat_template_kwargs: {"enable_thinking": false}` (A5.3). Boş içerik zaten "erişilemez/
geçersiz" sayılıp kurala düştüğü için hata sessiz değil ama yetenek ölüydü.

## Düzeltmeden sonra

| | Doğru | Not |
|---|---|---|
| Dil modeli önerisi | 10/10 | 8 Türkçe + 2 İngilizce soru; yanıt ~0,3 sn |
| Kural tabanlı öneri | 9/10 | genişletilmiş anahtarlar (İngilizce dahil); kaçan: "kamera kurulduktan sonra … düştü" (müdahale ipucu bitişik değil) |
| Sade özet (tr) | sözleşmeye uydu | kategori korundu, rakam yok, ~1,2 sn |
| Sade özet (en) | sözleşmeye uydu | rakam yok; kategori İngilizce karşılığıyla ("uncertain") — en'de kategori denetimi yok |

Sözleşme (sayı yok, Türkçede kategori aynen) sahte sunucuyla birim testine bağlandı
(`tests/test_uygulama.py::test_dil_modeli_yollari_sahte_sunucuyla`).
