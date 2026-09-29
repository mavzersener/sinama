# AGENTS.md — Sınama'da çalışan her yapay zekâ ajanı için

Bu depo **tek** bilimsel suç analizi programıdır ([ADR-001](KARARLAR/ADR-001-tek-program.md)).
Dağınık projelerden hasatla kurulur. İşe başlamadan bu dosyayı, ADR-001'i ve
[HASAT.md](HASAT.md)'yi oku. Bu kurallar başka hiçbir belgedeki plana göre gevşetilmez.

## Şu anki aşama

**A0 — iskelet (yerel).** Sıradaki: A1 GitHub özel depo → A2 çekirdek hasadı.
Aşama tablosu ADR-001'dedir. Aynı anda tek aşama açıktır; aşamayı proje sahibi kapatır.

## Mutlak kurallar

1. **Özel veri ve sır depoya giremez.** Gerçek veri (CSV/XLSX/JSONL/DB), oturum ve
   kanıt kayıtları, Bilgi Notları, `.env`, anahtarlar. Veri kökü depo dışındadır
   (bugün `C:\Users\ASUS\Documents\suc_veri`; A2'de `SINAMA_VERI_KOKU` olarak
   sabitlenecek). Test verisi yalnız sentetiktir ve yalnız `*/sentetik/` altında durur.
   `betikler/veri_bekcisi.py` commit ve push'ta çalışır — devre dışı bırakma,
   kuralı gevşetme; gerekçeli istisna yalnız `betikler/bekci_izinleri.txt`.
2. **Hasat, yeniden yazım değil.** Kaynaktan yalnız izlenen dosyaları al:
   `git -C <kaynak> archive <commit> -- <yol>`. Çalışma ağacını ASLA kopyalama
   (ignore'lu anahtar, veri ve `.env` fiziksel olarak orada durur). Parça testleriyle
   gelir; HASAT.md'ye kaynak@commit satırı yazılır.
3. **Kaynak depolar salt okunur.** `C:\Projects\{suc_analizi, DataFlow, harp_pol_x,
   science_gpt, AnlamCekirdegi, YerelAjan_v2}` ve
   `Documents\ChatGPT\JSGA Kolluk\duzeltme_suc_analizi`: okumak serbest, yazmak yasak.
4. **Paralel kopya yok.** Değişiklik bu depoda, bir dalda yapılır ve birleştirilir.
5. **Kanıt üreten hesap sunucuda, tek motorda.** İkinci bir yürütme yolu açma;
   tarayıcıdaki motor yalnız önizleme içindir.
6. **Dil modeli sayı üretmez.** Metindeki her sayı bir koşu kaydına/kanıt öğesine
   bağlanır. Sahte olasılık ya da "confidence" puanı üretme; epistemik hüküm
   kategoriktir (DESTEKLENDİ / KIRILGAN / BELİRSİZ / ÇELİŞKİLİ, ya da çekimser).
7. **Kişi/fail tespiti yok.** Desen benzerliği aynı fail demek değildir; kişi
   bağlantısı içeren her çıktı insan onayı ister.
8. **Dışa dönük eylem** (push, GitHub ayarı, paylaşım) yalnız proje sahibinin açık
   onayıyla yapılır.

## Yapma listesi (yaşanmış hatalardan)

- Veriyi sessizce kesme (tarayıcı yalnız ilk 5000 satırı okuyordu) — kesme varsa uyarı ve sayı ver.
- Demo/uydurma veriyi gerçek sonuca karıştırma (grafik düğümü sabit/rastgele veri çiziyordu).
- Kullanıcı ifadesini `eval`/`new Function` ile çalıştırma.
- Sunucuyu `0.0.0.0`'a bağlama; varsayılan `127.0.0.1`.
- Hash zincirinde bağ alanını hash dışında bırakma (zincir v1 ortadan kurcalamayı kaçırıyordu).
- Kütüphaneyi yalnız kendi testleriyle doğrulama; tüketici yolunu da test et
  (istek bağlamı değişikliği kendi testleri yeşilken 23 aracı kırdı).
- Olay akışına ham özet, gerekçe metni ya da dinamik grup etiketi yazma (P06).
- Doğrulayıcı okuyucusu bozuk kayıtta fırlatmaz, raporlar; ekleme tarafı kapalı hata verir.

## Ortam (Windows 11, Git Bash)

- Python çağrılarında `PYTHONUTF8=1` (konsol cp1252; Türkçe karakterler bozulur).
- `python3` Windows'ta Store yönlendiricisidir; `python` ya da `SINAMA_PY` kullan.
- Satır sonu LF (`.gitattributes`); stdout'a yama yazarken `sys.stdout.buffer`.
- Kancalar: `git config core.hooksPath .githooks` (her klonda bir kez).

## Dil ve üslup

Yorumlar, belgeler ve commit mesajları Türkçe; tanımlayıcılar ASCII Türkçe
(`oturum_id`, `veri_bagla`) — hasat edilen kodun üslubunu sürdür.

## Test

```bash
PYTHONUTF8=1 python -m unittest discover -s tests
```
