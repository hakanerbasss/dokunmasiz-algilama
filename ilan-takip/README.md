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

Sayfada ilanlar **ayrı sekmelerde** durur, birbirine karışmaz:

| Sekme | Anlamı | Bildirim |
|---|---|---|
| 🔥 Biyomedikal · KPSS'li | Biyomedikal / tıp mühendisliği kadrosu, KPSS'li (sözleşmeli ya da kadrolu) | evet (yüksek öncelik) |
| 🔥 Biyomedikal · KPSS'siz | Aynısı ama "KPSS'siz", "KPSS şartı aranmaz" gibi ifadeyle | evet (yüksek öncelik) |
| 📄 Herhangi lisans | "Herhangi bir lisans mezunu" alımları, **KPSS'li** olanlar (bölüm şartı yok) | evet (düşük öncelik) |
| ⚙️ Mühendis | Kamu mühendis ilanı, bölüm kısıtı görünmüyor | yalnızca **ilan metni okunabildiyse** (başlıktan bölüm bilinemez; KPSS'siz olanlar hariç) |
| 🏛️ Belediye ilanları | Başlığında belediye geçen personel alımı (işçi, memur, sözleşmeli; tüm iller) | hayır |
| 🏛️ İzlediklerim | `izlenen` ayarındaki kurumlardan (Avcılar, Bathonea, İBB ve İstanbul ilçe belediyeleri) gelen her ilan | evet |
| 📋 Toplu alım | Kurum toplu personel alıyor; kadro listesinde mühendis var mı elle bak | hayır |
| Elenenler | Aşağıdaki şartlardan biri tutmadı, nedeniyle birlikte görünür | hayır |
| Düşük ihtimal | Mühendis ilanı ama bölüm listesinde biyomedikal yok | hayır |

Hangi sekmelerden bildirim geleceği `scraper/ayar.json` içindeki `bildirim_seviyeleri` ile değişir
(`guclu`, `olasi`, `lisans`).

**İzlenen kurumlar:** `ayar.json` içindeki `izlenen` bölümü, çalıştığın/izlediğin kurumları işaretler.
`kurumlar` listesindeki bir ad (ör. "Avcılar") ilan başlığında geçerse ya da `belediye_illeri` listesindeki bir ilin
(ör. İstanbul, ilçe belediyeleri dahil) belediyesi ilan verirse ilan "İzlediklerim" sekmesine düşer ve —KPSS ya da bölüm
şartı aranmaksızın— bildirim gelir. Elenme şartları (2024 KPSS, doğu ili vb.) yine geçerlidir.

**Tarihli hatırlatmalar:** `ayar.json` içindeki `hatirlatmalar`, bir tarih aralığından 14 gün ve 3 gün önce ile ilk gün
bildirim gönderir (varsayılan: KPSS-2026/2 merkezi atama tercih dönemi, 17–24 Aralık 2026 — haberlere dayanıyor,
ÖSYM'nin resmî duyurusuyla doğrulanmadı). Aynı eşik için bir kez bildirilir; gönderim başarısız olursa sonraki taramada
yeniden denenir. Aralıklar sayfada "Yaklaşan tarihler" kartında da görünür.

## Başka biri için profil (ör. arkadaşın)

Sayfanın en üstündeki **Profil** listesinden profil seçilir; her profil için puanlar ayrı ve yalnızca o telefonda saklanır.
Bir profile doğrudan bağlantı da verilebilir: `.../ilan-takip/?profil=ceei` (bağlantıyı sayfadaki
"Bu profilin bağlantısını kopyala" düğmesi verir).

| Profil | Ne gösterir |
|---|---|
| Biyomedikal Mühendisi | Yukarıdaki sekmelerin hepsi (doğu illeri elenir, İstanbul çevresi öne çıkar) |
| Çalışma Ekonomisi ve Endüstri İlişkileri | **Tüm iller**, **tüm belediyeler** (işçi, memur, sözleşmeli); sekmeler: bölümüne uyanlar, herhangi lisans, belediye ilanları, toplu alım |
| Kendi bölümüm (yaz) | Yazdığın kelimelere uyan ilanlar + herhangi lisans + belediye ilanları (tüm iller) |

- Bölüme uyma, ilan başlığında ya da (okunabiliyorsa) metninde profilin `anahtarlar` listesindeki kelimenin geçmesiyle
  anlaşılır (`ayar.json` → `profiller`). Haber başlıklarında bölüm adı nadiren geçtiği için bu sekme çoğu zaman boş
  kalır; asıl işe yarayanlar **belediye ilanları** ve **herhangi lisans** sekmeleridir.
- Yeni bir profil eklemek için `profiller` listesine `id`, `ad`, `anahtarlar` (bölüm adı, görev unvanı) eklenir.
- Belediye işçi alımlarının bir kısmı İŞKUR üzerinden yürür ve haberlerde görünmez; sayfadaki *Elle kontrol et*
  bağlantılarına İŞKUR eklendi.
- **Bildirimler tek bir konu adına (tek telefona) gider.** Diğer profiller şimdilik sayfadan bakmak içindir. Ayrı bildirim
  için ayrı konu adı ve ayrı ayar gerekir.
- Belediye ve toplu alım ilanları 60 gün sonra listeden düşer; biyomedikal, mühendis ve herhangi lisans ilanları kalır.
  Önemsiz ilanlar veri dosyasını en fazla 6 saatte bir yazdırır (depo büyümesini sınırlar), önemli ilanlar hemen.

**Elenme şartları** (KPSS'siz ilanlarda KPSS şartları uygulanmaz, yaş ve il uygulanır):

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
| **Kariyer Kapısı** (`kariyerkapisi.gov.tr/RSS`) | Resmî kamu ilanlarının başlıkları (hangi kurum, ne zaman). İçerik için aşağıdaki nota bak. |
| Google Haberler (10 sorgu, son 30 gün) | Haber başlıkları. Gövde okunamaz; başlıktan sınıflanır. |
| İşin Olsa RSS | Kamu ilanı haberleri **tam metinle** (kadro listesi dahil) |
| ÖSYM duyuruları | KPSS merkezi yerleştirme (tercih) kılavuzu yayımlanınca haber vermesi beklenir |
| TİTCK duyuruları | Kurumun kendi personel ilanları |

Kaynakların çalışıp çalışmadığı sayfadaki *Kaynak sağlığı* bölümünde görünür.

> **Sınır — Kariyer Kapısı ilan içeriği:** Resmî RSS yalnızca başlık verir ("X ÜNİVERSİTESİ - SÖZLEŞMELİ PERSONEL ALIM İLANI");
> kadro listesi ve KPSS şartları sitenin ayrı bir API'siyle gelir. Bu API'ye GitHub Actions'tan **zaman aşımı** alınıyor
> (site yurt dışı sunuculara kapalı görünüyor), bu yüzden Kariyer Kapısı ilanları "Toplu alım" sekmesine düşer; ilanı
> açıp kadro listesine kendin bakmalısın. Kod hazırdır ve testlidir: Türkiye'den çalışan bir ortamda
> (ör. telefonda Termux) `ayar.json` içinde `"kk_api": true` yapılırsa pozisyonlar okunur ve biyomedikal kadrosu olan
> ilanlar doğru sekmeye taşınır.
> `ilan.gov.tr` sertifika zinciri eksik olduğu için doğrulanamıyor; Resmî Gazete'ye erişilemedi. İkisi için
> sayfadaki *Elle kontrol et* bağlantılarını kullan.

## Bildirimleri puana ve yaşa göre süzmek (PROFIL_JSON)

Puanların ve doğum yılın yalnızca telefondaki sayfada durur; **sunucu bunları bilmez.** Bu yüzden `PROFIL_JSON` gizli
anahtarı eklenmedikçe bildirimler puana/yaşa bakmaz ("65 KPSS ile" diyen bir ilan için de haber gelir). Sayfada o ilan
yine "Elenenler"e düşer. Süzgeç için sayfadaki *PROFIL_JSON değerini kopyala* düğmesiyle değeri alıp
Settings → Secrets and variables → Actions → *New repository secret* (ad: `PROFIL_JSON`) olarak ekle.

Süzgeç ilanda yazan şartlara bakar: başlıkta ya da metinde asgari puan ("65 KPSS", "KPSS 70 puan", "en az 75 puan"),
puan türü ("KPSSP3 en az 70") ve yaş sınırı ("35 yaşını doldurmamış"). Başlık bunları söylemiyorsa şart bilinemez:
bildirim yine gelir, mesajda bulunan eşik ("KPSS taban ≥ 65") yazar. Zabıta, itfaiye, koruma-güvenlik gibi kadrolarda yaş
sınırı ve fiziki şart genelde bulunduğu için "yaş/fiziki şart olabilir" uyarısı eklenir. "KPSS'siz de olabilir" diyen
ilanlarda puan eleme nedeni sayılmaz.

## Gizlilik

Depo herkese açık olduğu için **puanların, doğum yılın ve TC kimlik numaran depoya yazılmaz.**
Profilin yalnızca telefonundaki tarayıcıda durur. Bildirimlerin de puana/yaşa göre süzülmesini istersen sayfadaki
*PROFIL_JSON değerini kopyala* düğmesiyle bunu **GitHub Secret** olarak ekleyebilirsin (secret'lar herkese kapalıdır).
`data/ilanlar.json` kişisel veri içermez.

## Sınırlar

- **İlan metni her zaman okunamaz.** Google Haberler yalnızca başlık verir (haber sayfasına ulaşmaya çalışınca Google
  429 hatası veriyor) ve Kariyer Kapısı ilanlarının içeriği de okunamıyor. Bu ilanlar "Metin okunamadı" uyarısıyla
  görünür. Başlığında yalnızca "mühendis" yazan bir ilan için bildirim **gönderilmez**, çünkü bölüm şartı (ör. "İnşaat
  Mühendisliği") ve asgari puan metinde yazar. Başlığında "biyomedikal" geçen ilanlar ise bildirilir, mesajda
  "metin okunamadı" uyarısıyla.
- Sınıflandırma **otomatik ve sezgiseldir**. Bir ilan kaçabilir ya da gereksiz çıkabilir.
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
