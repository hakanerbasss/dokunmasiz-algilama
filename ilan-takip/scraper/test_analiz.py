import unittest

import analiz as a

AYAR = {
    "kpss_yillari": [2026],
    "engelli_iller": ["Van", "Erzurum", "Diyarbakır", "Şanlıurfa", "Hakkari"],
}


def sev(baslik, govde=""):
    s = a.sinifla(baslik, govde)
    return s[0] if s else None


class Sinifla(unittest.TestCase):
    """Başlıklar 8 Ekim 2026'da Google Haberler / İşin Olsa'dan alınmış gerçek örneklerdir."""

    def test_muhendis_ilani_olasi(self):
        self.assertEqual(sev("Mühendis, biyolog ve kimyager alımı: TÜSEB yeni personel ilanı yayınladı"), "olasi")
        self.assertEqual(sev("TÜSEB mühendis, biyolog ve kimyager alacak! KPSS şartı ve başvuru tarihleri belli oldu"), "olasi")
        self.assertEqual(sev("Mühendislere Dev Kadro! Savunma Sanayiinde Kariyer Fırsatı Başlıyor!"), "olasi")

    def test_biyomedikal_guclu(self):
        self.assertEqual(sev("Sağlık Bilimleri Üniversitesi 38 sözleşmeli personel alacak: Mühendis (Biyomedikal)"), "guclu")
        self.assertEqual(sev("Biyomedikal Mühendisi alınacak"), "guclu")
        self.assertEqual(sev("Tıp mühendisi alımı yapılacak, KPSS şartı"), "guclu")

    def test_kamu_muhendis_basliginda_personel_kelimesi_sart_degil(self):
        self.assertEqual(sev("Belediye mühendis alımı yapacak"), "olasi")

    def test_govdede_biyomedikal(self):
        govde = "Kadrolar: Hemşire 10, Mühendis (Biyomedikal) 1, Tekniker 3. " + "x " * 300
        self.assertEqual(sev("Bir Üniversite 40 Sözleşmeli Personel Alacak", govde), "guclu")

    def test_toplu_alim(self):
        self.assertEqual(sev("Balıkesir Üniversitesi Rektörlüğü 309 Sözleşmeli Personel Alacak! İşte Başvuru Şartları"), "toplu")
        self.assertEqual(sev("KPSS Puanıyla Mülatsız Atama! Türkiye İlaç ve Tıbbi Cihaz Kurumu 16 Personel Alımı Yapacak"), "toplu")

    def test_govde_okundu_muhendis_yoksa_ele(self):
        govde = "Kadrolar: Hemşire, Ebe, Tekniker, Sekreter, Büro Personeli. " * 30
        self.assertIsNone(sev("Dicle Üniversitesi 72 sözleşmeli personel alıyor", govde))

    def test_brans_listesinde_biyomedikal_yoksa_dusuk(self):
        govde = "Mühendis (Elektrik-Elektronik Mühendisliği) 2, Mühendis (Makine Mühendisliği) 1"
        self.assertEqual(sev("Trabzon Üniversitesi sözleşmeli personel alacak: mühendis", govde), "dusuk")

    def test_her_brans_olursa_olasi(self):
        govde = "Mühendis kadrosu: Mühendislik fakültelerinin ilgili bölümlerinden mezun, makine mühendisliği dahil."
        self.assertEqual(sev("Belediye mühendis alımı yapacak, KPSS şartı", govde), "olasi")

    def test_ilgisiz(self):
        for b in [
            "Asperger sendromlu yüksek mühendis, Eşrefpaşa Hastanesi’nde görevde",
            "Sakarya'da tıbbi cihazların bakım ve onarımı özel ekibe emanet",
            "Geleceğin mesleklerinden: Biyomedikal Mühendisliği nedir?",
            "Kocaeli’deki 13 firma mühendis arıyor!",
            "Kocaeli'deki 19 firma 21 mühendis alacak",
            "Jaguar’ın Tarihindeki En Güçlü Model! Type 01 1.030 PS ile Geldi",
            "2026’da Ucuz Otomobil Almanın Gerçek Maliyeti: İlan Fiyatına Neler Ekleniyor?",
            "Tıbbi cihaz alımı ihalesi sonuç ilanı",
            "2026 KPSS Branş Sıralaması Ne Zaman Açıklanacak? ÖSYM Henüz Tarih Vermedi",
            "Tofaş mühendis alıyor, başvurular başladı",
            "ÖSYM Sözleşmeli Bilişim Personeli Alımı Mülakat Sonuçları",
        ]:
            self.assertIsNone(sev(b), b)

    def test_kilavuz_yalniz_resmi_kaynakta(self):
        def rs(b):
            s = a.sinifla(b, "", resmi=True)
            return s[0] if s else None
        self.assertEqual(rs("KPSS-2026/6 Tercih Kılavuzu Yayımlandı"), "olasi")
        self.assertIsNone(rs("2026-KPSS Lisans Sınavı: Sınav Sonuçları Açıklandı"))
        self.assertIsNone(rs("2026-TUS 2. Dönem: Tercihlerin Alınması"))
        self.assertIsNone(rs("KPSS tercih kılavuzu 2026 ne zaman yayınlanacak?"))
        # haber sitesinde (resmi değil) kılavuz haberi bildirim üretmemeli
        self.assertIsNone(sev("KPSS-2026/6 Tercih Kılavuzu Yayımlandı"))

    def test_toplu_gurultu_elenir(self):
        for b in [
            "Sağlık Bilimleri Üniversitesi 13 Personel Alacak: Lise Mezunları Başvurabilecek",
            "SUBÜ 15 akademik personel alacak",
            "DSİ 31 Memur Alımı Yapacak! KPSS Şartı Olmadan",
            "EGM, MSB, KGM ve MEB Birimlerine İŞKUR’dan Personel Alımı! İşte 6 İlan",
            "KPSS 2026/2 merkezi atama ne zaman yapılacak, kaç memur alınacak?",
            "Bugün Resmi Gazete kararları 10 Eylül 2026 | atamaları ve kararları neler? personel alımı",
            "Batman Üniversitesi 60 KPSS ile 15 Personel Alacak! Lise ve Ön Lisans Mezunlarına Mülakatsız Alım",
        ]:
            self.assertIsNone(sev(b), b)
        self.assertEqual(sev("Lise-MYO-Lisans 133 Kontenjana Kamu Personel Alımları: KPSS 60 Yeterli"), "toplu")


class Gercekler(unittest.TestCase):
    def g(self, metin):
        return a.gercekler(metin, a.fold(metin))

    def test_puan_turu_ve_asgari(self):
        g = self.g("KPSSP3 puan türünden en az 70 puan almış olmak")
        self.assertEqual(g["puan_turleri"], {"P3": 70.0})
        g = self.g("2024 yılı KPSS (B) grubu KPSS P3 puanı esas alınacaktır. Taban puan 60")
        self.assertEqual(g["puan_turleri"], {"P3": 60.0})
        self.assertEqual(g["kpss_yillari"], [2024])

    def test_yil_puan_turu_bitisik(self):
        g = self.g("2024 KPSS Lisans Defteri Kapandı! Personel Alımlarında 2026 P3 Dönemi Başlıyor")
        self.assertEqual(g["kpss_yillari"], [2024, 2026])

    def test_puan_turu_asgari_yok(self):
        self.assertEqual(self.g("KPSSP1 puan türüne göre sıralama yapılacak")["puan_turleri"], {"P1": None})

    def test_yil_ile_puan_karismaz(self):
        g = self.g("2026 KPSSP3 puan türünden başvuru alınacaktır")
        self.assertEqual(g["puan_turleri"], {"P3": None})
        self.assertEqual(g["kpss_yillari"], [2026])

    def test_genel_puan(self):
        self.assertEqual(self.g("2026 KPSS Puanıyla 860 Memur Alımı! 65 Puanla Başvurular Başlıyor")["genel_puanlar"], [65])
        self.assertEqual(self.g("2026 KPSS 50-59 Puanla Memur Alımı!")["genel_puanlar"], [50, 59])

    def test_yas_siniri(self):
        self.assertEqual(self.g("35 yaşını doldurmamış olmak")["yas_siniri"], 35)
        self.assertEqual(self.g("30 yaşından gün almamış olmak")["yas_siniri"], 30)
        self.assertIsNone(self.g("Yaş sınırı bulunmamaktadır")["yas_siniri"])

    def test_iller(self):
        self.assertEqual(self.g("Kocaeli’nde ve Silivri’de görev yapacak")["iller"], ["Kocaeli", "İstanbul"][::-1] if False else sorted(["Kocaeli", "İstanbul"]))
        self.assertEqual(self.g("Zonguldak Bülent Ecevit Üniversitesi")["iller"], ["Zonguldak"])
        self.assertEqual(self.g("Van Yüzüncü Yıl Üniversitesi")["iller"], ["Van"])
        self.assertEqual(self.g("bir van dolusu iş")["iller"], [])
        self.assertEqual(self.g("Ağrı İbrahim Çeçen Üniversitesi")["iller"], ["Ağrı"])

    def test_ehliyet_brans(self):
        g = self.g("B sınıfı sürücü belgesi sahibi; Elektrik-Elektronik Mühendisliği, Makine Mühendisliği")
        self.assertTrue(g["ehliyet"])
        self.assertEqual(g["bolumler"], ["elektrik", "elektronik", "makine"])


SBU = """Sağlık Bilimleri Üniversitesi Rektörlüğü, 2024 KPSS (B) grubu puan sırasına göre istihdam etmek üzere 20 farklı
pozisyonda toplam 38 sözleşmeli personel (4/B) alacak. Erkek adaylar için askerlik yükümlülüğünü yerine getirmiş olmak
KPSS puan şartları mezuniyet düzeyine göre farklılık gösteriyor:
Ortaöğretim mezunları: 2024 KPSS (B) P94 puanı
Ön lisans mezunları: 2024 KPSS (B) P93 puanı
Lisans mezunları: 2024 KPSS (B) P3 puanı
Her kadro için asgari 60 puan şartı aranıyor.
Kadro Şehir Adet: Mühendis (Makine) Ankara 1, Mühendis (Biyomedikal) Ankara 1, Mühendis (İnşaat) İstanbul 1
Son başvuru tarihi 20 Nisan 2026"""


class GercekIlan(unittest.TestCase):
    """8 Ekim 2026'da isinolsa.com'dan alınan gerçek SBÜ ilanı (Nisan 2026) metninden."""

    def test_gercekler(self):
        g = a.gercekler(SBU, a.fold(SBU))
        self.assertEqual(g["kpss_yillari"], [2024])          # "Nisan 2026" tarihi yıl sayılmamalı
        self.assertEqual(g["puan_turleri"]["P3"], 60.0)
        self.assertEqual(g["genel_puanlar"], [60])           # P93/P94 puan sayılmamalı
        self.assertEqual(g["iller"], ["Ankara", "İstanbul"])

    def test_siniflama_ve_eleme(self):
        profil = {"dogum_yili": 1988, "puanlar": {"P1": 64.6, "P2": 64.3, "P3": 63.9}}
        d = a.degerlendir("Sağlık Bilimleri Üniversitesi 38 sözleşmeli personel alımı yapacak", SBU,
                          {"kpss_yillari": [2026], "engelli_iller": []}, profil, 2026)
        self.assertEqual(d["seviye"], "guclu")
        self.assertIn("2024 KPSS", d["elendi"][0])           # sadece 2026 puanı olan aday başvuramaz
        self.assertEqual(d["elendi_profil"], [])             # P3=63.9 >= 60; P93/P94 yok sayılır
        d = a.degerlendir("SBÜ personel alımı", SBU.replace("2024 KPSS", "2026 KPSS"),
                          {"kpss_yillari": [2026], "engelli_iller": []}, profil, 2026)
        self.assertEqual(d["elendi"], [])

    def test_profil_yalniz_olmayan_tur(self):
        g = a.gercekler("KPSSP93 puan türünden en az 60", "kpssp93 puan turunden en az 60")
        self.assertIn("P93", a.profil_elemeleri(g, {"puanlar": {"P3": 63.9}}, 2026)[0])

    def test_govde_temizle(self):
        self.assertEqual(a.govde_temizle("Asıl metin. İlginiz Çekebilir\nBatman Üniversitesi"), "Asıl metin. ")
        uzun = "Kadro:\n\n\n   Mühendis      Ankara   \n\n   POPÜLER HABERLER Van Üniversitesi"
        self.assertNotIn("Van", a.govde_temizle(uzun))
        self.assertIn("Ankara", a.govde_temizle(uzun))


class Elemeler(unittest.TestCase):
    def deg(self, baslik, govde="", profil=None):
        return a.degerlendir(baslik, govde, AYAR, profil, yil=2026)

    def test_eski_kpss_yili(self):
        d = self.deg("Üniversite 2024 KPSS puanı ile sözleşmeli mühendis alacak")
        self.assertIn("2024 KPSS", d["elendi"][0])

    def test_2026_ve_2024_birlikte_uygun(self):
        d = self.deg("2024 ve 2026 KPSS puanı ile mühendis alımı yapılacak")
        self.assertEqual(d["elendi"], [])

    def test_dogu_ili(self):
        d = self.deg("Van Yüzüncü Yıl Üniversitesi KPSS ile mühendis alacak")
        self.assertTrue(d["elendi"])
        d = self.deg("Van ve Kocaeli'ne KPSS ile mühendis alınacak")
        self.assertEqual(d["elendi"], [])

    def test_onlisans(self):
        d = self.deg("Belediye KPSS ön lisans puanıyla mühendis alımı yapacak")
        self.assertTrue(any("ön lisans" in e for e in d["elendi"]))
        d = self.deg("Belediye KPSS lisans ve ön lisans puanıyla mühendis alımı yapacak")
        self.assertFalse(any("ön lisans" in e for e in d["elendi"]))

    def test_profil_puan(self):
        profil = {"puanlar": {"P1": 64.6, "P2": 64.3, "P3": 63.9}, "dogum_yili": 1988}
        d = self.deg("KPSS mühendis alımı", "KPSSP3 puan türünden en az 70 puan", profil)
        self.assertIn("en az 70", d["elendi_profil"][0])
        d = self.deg("KPSS mühendis alımı", "KPSSP3 puan türünden en az 60 puan", profil)
        self.assertEqual(d["elendi_profil"], [])
        d = self.deg("KPSS mühendis alımı", "KPSSP93 puan türünden en az 60 puan", profil)
        self.assertIn("P93", d["elendi_profil"][0])

    def test_profil_yas(self):
        profil = {"puanlar": {"P3": 63.9}, "dogum_yili": 1988}
        d = self.deg("KPSS mühendis alımı", "35 yaşını doldurmamış olmak", profil)
        self.assertIn("Yaş sınırı 35", d["elendi_profil"][0])
        d = self.deg("KPSS mühendis alımı", "45 yaşını doldurmamış olmak", profil)
        self.assertEqual(d["elendi_profil"], [])

    def test_profil_yok(self):
        d = self.deg("KPSS mühendis alımı", "KPSSP3 en az 99 puan")
        self.assertEqual(d["elendi_profil"], [])


class Yardimci(unittest.TestCase):
    def test_fold(self):
        self.assertEqual(a.fold("İŞÇİ Alımı ığüşöç"), "isci alimi igusoc")

    def test_temiz_baslik(self):
        self.assertEqual(a.temiz_baslik("Mühendis alımı - Hürriyet"), "Mühendis alımı")
        self.assertEqual(a.temiz_baslik("Mühendis alımı"), "Mühendis alımı")


if __name__ == "__main__":
    unittest.main()
