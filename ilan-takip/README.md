# Kamu İlan Takip

Biyomedikal mühendisi için **KPSS ile kamu personel alımı** takibi. 2 yıl boyunca (varsayılan: 08.10.2026 → 08.10.2028)
internette kamu ilanlarını tarar; sana uygun olanı bulunca telefonuna bildirim gönderir.

APK ya da sunucu yok: tarayıcıda açılan bir **HTML sayfası** + ücretsiz **GitHub Actions** zamanlayıcısı.

```
GitHub Actions (3 saatte bir)  →  data/ilanlar.json  →  index.html (telefonda açtığın sayfa)
        └── yeni uygun ilan varsa  →  ntfy bildirimi (telefona)
```

Neden böyle? Salt HTML sayfası tarayıcı kapalıyken çalışamaz ve çoğu siteyi (CORS yüzünden) doğrudan okuyamaz.
Bu yüzden taramayı GitHub'ın zamanlayıcısı yapar, sayfa sadece sonucu gösterir.

## Kurulum (telefondan, ~5 dakika)

1. **Birleştir:** Bu dalı `main`'e birleştir (GitHub → Pull requests → Merge). Zamanlanmış akışlar ve Pages yalnızca `main`'den çalışır.
2. **Sayfa:** `https://hakanerbasss.github.io/dokunmasiz-algilama/ilan-takip/` (Pages zaten açık).
3. **İlk tarama:** Birleştirince akış kendiliğinden çalışır. Elle başlatmak için: Actions → **ilan-tara** → *Run workflow*.
4. **Profil:** Sayfada *Profilim* bölümüne KPSS puanlarını ve doğum yılını gir. Yalnızca telefonda saklanır.
5. **Bildirim:** Sayfada *Telefona bildirim kurulumu* bölümünü izle (konu adı üret → ntfy uygulaması → GitHub secret).

İlk bildirim "Takip başladı: N uygun ilan" olur; bu, bildirim kanalının çalıştığını da doğrular.

## Ne bulur, nasıl eler?

Her ilan şu seviyelerden birine konur:

| Seviye | Anlamı | Bildirim |
|---|---|---|
| 🔥 Biyomedikal | Başlık ya da metinde biyomedikal / tıp mühendisliği geçiyor | evet |
| ⚙️ Mühendis | Kamu mühendis ilanı, bölüm kısıtı görünmüyor | evet |
| ▫️ Düşük ihtimal | Mühendis ilanı ama bölüm listesinde biyomedikal yok | hayır |
| 📋 Toplu alım | Kurum toplu personel alıyor; kadro listesinde mühendis var mı elle bak | hayır |

Sonra şu şartlarla **elenir** (sayfada *Elenenler* sekmesinde nedeniyle birlikte görünür):

- **KPSS yılı:** Yalnızca 2026 puanın var; "2024 KPSS esas alınır" diyen ilanlar elenir.
- **Puan türü ve asgari puan:** ilan "KPSSP3 en az 70" derse ve puanın düşükse elenir. İlan P93/P94 gibi başka düzeylerin
  puan türlerini de sayıyorsa, sahip olduğun türe (P1/P2/P3) bakılır.
- **Yaş sınırı:** "35 yaşını doldurmamış" gibi ifadeler doğum yılına göre kontrol edilir.
- **İl:** Doğu/Güneydoğu illeri elenir; İstanbul, Tekirdağ, Kocaeli, Karabük, Bartın, Zonguldak, Kastamonu ★ ile öne çıkar.
- **Düzey:** yalnızca lise/ön lisans mezunlarına açık ilanlar elenir.
- Askerlik yapıldığı için askerlik şartı sorun çıkarmaz.

Tüm bu ayarlar `scraper/ayar.json` içindedir (iller, yıl, bitiş tarihi, arama sorguları, kaynaklar).

## Kaynaklar

| Kaynak | Ne verir |
|---|---|
| Google Haberler (10 sorgu, son 30 gün) | Haber başlıkları. Gövde okunamaz; başlıktan sınıflanır. |
| İşin Olsa RSS | Kamu ilanı haberleri **tam metinle** (kadro listesi dahil) |
| ÖSYM duyuruları | KPSS merkezi yerleştirme (tercih) kılavuzu yayımlanınca haber verir |
| TİTCK duyuruları | Kurumun kendi personel ilanları |
| Kariyer Kapısı, ilan.gov.tr (deneysel) | Resmî ilan siteleri. Bu siteler JavaScript ile çizilebilir ve yurt dışı sunuculardan açılmayabilir; çalışıp çalışmadığı sayfadaki *Kaynak sağlığı* bölümünde görünür. |

> Kariyer Kapısı ve ilan.gov.tr'ye kodu yazarken kullandığım ortamdan ulaşamadım (bağlantı reddedildi). Bu yüzden bu iki kaynağı
> test edemedim. Resmî ilanları yine de sayfadaki *Elle kontrol et* bağlantılarından haftada bir gözden geçir.

## Gizlilik

Depo herkese açık olduğu için **puanların, doğum yılın ve TC kimlik numaran depoya yazılmaz.**
Profilin yalnızca telefonundaki tarayıcıda durur. Bildirimlerin de puana/yaşa göre süzülmesini istersen sayfadaki
*PROFIL_JSON değerini kopyala* düğmesiyle bunu **GitHub Secret** olarak ekleyebilirsin (secret'lar herkese kapalıdır).
`data/ilanlar.json` kişisel veri içermez.

## Sınırlar

- Sınıflandırma **otomatik ve sezgiseldir**. Google Haberler için yalnızca başlık okunur; bir ilan kaçabilir ya da gereksiz çıkabilir.
  Başvurmadan önce ilanın kendisini, KPSS yılını, puan türünü ve bölüm şartını mutlaka oku.
- Eleme yalnızca ilan metninde yazanı bilir. Metinde olmayan bir şart (ör. deneyim) kontrol edilmez.
- 2 yıl dolunca (`bitis_tarihi`) son bir bildirim gelir ve zamanlayıcı kendini kapatır. Uzatmak için tarihi ileri al ve
  Actions → ilan-tara → *Enable workflow*.
- GitHub, 60 gün hiç etkinlik olmayan depolarda zamanlanmış akışı kapatır. Akış en geç 10 günde bir kayıt yazarak bunu önler.
  Sayfa, tarama 12 saatten uzun durursa uyarı gösterir.

## Geliştirme

```
python3 -m unittest discover -s ilan-takip/scraper      # testler (ağ gerekmez)
python3 ilan-takip/scraper/tara.py --kuru               # canlı kaynaklara bak, hiçbir şey yazma/bildirme
VERI_DIZINI=/tmp/veri python3 ilan-takip/scraper/tara.py  # başka klasöre yaz
python3 -m http.server -d ilan-takip                    # sayfayı yerelde aç
```
