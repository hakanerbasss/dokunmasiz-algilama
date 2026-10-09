import datetime as dt
import json
import os
import tempfile
import unittest
from email.utils import format_datetime
from pathlib import Path
from unittest import mock

import tara

AYAR = {
    "baslangic_tarihi": "2026-10-08", "bitis_tarihi": "2099-01-01", "kpss_yillari": [2026],
    "tercih_iller": ["Kocaeli"], "yakin_iller": [], "engelli_iller": ["Van"],
    "google_haberler": [],
    "kaynaklar": [{"ad": "Deneme RSS", "tur": "rss", "url": "https://haber.test/feed"},
                  {"ad": "Deneme Sayfa", "tur": "sayfa", "url": "https://kurum.test/", "filtre": "personel", "resmi": True}],
}


def rss(*ogeler):
    simdi = format_datetime(dt.datetime.now(dt.timezone.utc))
    govdeler = []
    for baslik, link, icerik in ogeler:
        ic = f"<content:encoded><![CDATA[{icerik}]]></content:encoded>" if icerik else ""
        govdeler.append(f"<item><title>{baslik}</title><link>{link}</link><pubDate>{simdi}</pubDate>{ic}</item>")
    return ('<?xml version="1.0"?><rss version="2.0" xmlns:content="http://purl.org/rss/1.0/modules/content/">'
            "<channel><title>x</title>" + "".join(govdeler) + "</channel></rss>").encode("utf-8")


SAYFA = """<html><body><nav><a href="/iletisim">İletişim ve adres bilgileri sayfası</a></nav>
<a href="/duyuru/1">KPSS-2026/6 Tercih Kılavuzu Yayımlandı</a>
<a href="/duyuru/2">Kurumumuz 5 sözleşmeli personel alacak: Mühendis kadrosu</a>
<a href="#">Başa dön ve sayfanın üstüne git lütfen</a></body></html>""".encode("utf-8")


class RssSayfa(unittest.TestCase):
    def test_rss_oku(self):
        veri = rss(("Mühendis alımı", "https://x.test/a", "<p>Kadro: Mühendis (Biyomedikal)</p><script>x()</script>"))
        o = tara.rss_oku(veri, "Kaynak")[0]
        self.assertEqual(o["baslik"], "Mühendis alımı")
        self.assertIn("Biyomedikal", o["govde"])
        self.assertNotIn("x()", o["govde"])
        self.assertTrue(o["tarih"].endswith("Z"))

    def test_gnews_baslik_temizlenir(self):
        veri = rss(("Belediye mühendis alacak - Yeni Şafak", "https://news.google.com/rss/articles/abc", ""))
        self.assertEqual(tara.rss_oku(veri, "G", gnews=True)[0]["baslik"], "Belediye mühendis alacak")

    def test_sayfa_oku(self):
        o = tara.sayfa_oku(SAYFA.decode(), "https://kurum.test/", "K", "tercih|personel", resmi=True)
        self.assertEqual([x["url"] for x in o], ["https://kurum.test/duyuru/1", "https://kurum.test/duyuru/2"])
        self.assertTrue(all(x["resmi"] for x in o))

    def test_sayfa_oku_filtresiz(self):
        o = tara.sayfa_oku(SAYFA.decode(), "https://kurum.test/", "K", None)
        urls = [x["url"] for x in o]
        self.assertIn("https://kurum.test/duyuru/1", urls)
        self.assertFalse([u for u in urls if u.endswith("#")])            # '#' bağlantıları atlanır


class Taban(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.kok = Path(self.tmp.name)
        (self.kok / "ayar").mkdir()
        self.ayar(AYAR)
        self.veri = self.kok / "data"
        self.bildirimler = []
        self.sayfalar = {}
        self.api = {}            # guid -> liste (başarı) ya da Exception (erişilemedi)
        self.api_cagri = []
        self.yamalar = [
            mock.patch.object(tara, "KLASOR", self.kok / "ayar"),
            mock.patch.object(tara, "VERI", self.veri),
            mock.patch.object(tara, "indir", side_effect=self._indir),
            mock.patch.object(tara, "ntfy_gonder", side_effect=lambda *a, **k: self.bildirimler.append((a, k))),
            mock.patch.object(tara, "api_post", side_effect=self._api),
            mock.patch.object(tara.time, "sleep", return_value=None),
            mock.patch.dict(os.environ, {"NTFY_TOPIC": "deneme-konu-12345", "GITHUB_REPOSITORY": "ben/depo"}, clear=False),
        ]
        for y in self.yamalar:
            y.start()
        os.environ.pop("PROFIL_JSON", None)

    def tearDown(self):
        for y in self.yamalar:
            y.stop()
        self.tmp.cleanup()

    def ayar(self, ayar):
        (self.kok / "ayar" / "ayar.json").write_text(json.dumps(ayar), encoding="utf-8")

    def _indir(self, url, **kw):
        if url not in self.sayfalar:
            raise RuntimeError("erişilemedi: " + url)
        return self.sayfalar[url], "text/xml", "utf-8"

    def _api(self, url, nesne, **kw):
        self.api_cagri.append(nesne["ilanGuid"])
        sonuc = self.api.get(nesne["ilanGuid"], RuntimeError("API kapalı"))
        if isinstance(sonuc, Exception):
            raise sonuc
        return sonuc

    def ilanlar(self):
        return json.loads((self.veri / "ilanlar.json").read_text(encoding="utf-8"))



class Akis(Taban):
    def test_ilk_calisma_ozet_bildirir(self):
        self.sayfalar["https://haber.test/feed"] = rss(
            ("Kocaeli Üniversitesi mühendis alacak, KPSS şartı", "https://haber.test/1", ""),
            ("Jaguar yeni model tanıttı", "https://haber.test/2", ""))
        self.sayfalar["https://kurum.test/"] = SAYFA
        self.assertEqual(tara.calistir(), "tamam")
        d = self.ilanlar()
        self.assertEqual([i["baslik"] for i in d["ilanlar"] if i["seviye"] == "olasi"][:1],
                         ["Kocaeli Üniversitesi mühendis alacak, KPSS şartı"])
        self.assertTrue(all(k["tamam"] for k in d["kaynaklar"]))
        self.assertEqual(d["depo"], "ben/depo")
        self.assertEqual(len(self.bildirimler), 1)                       # ilk çalışma: tek özet
        self.assertIn("Takip başladı", self.bildirimler[0][0][1])

    def test_ikinci_calisma_sessiz_ve_dosyalara_dokunmaz(self):
        self.sayfalar["https://haber.test/feed"] = rss(("Belediye mühendis alacak, KPSS", "https://haber.test/1", ""))
        self.sayfalar["https://kurum.test/"] = SAYFA
        tara.calistir()
        once = (self.veri / "ilanlar.json").read_bytes(), (self.veri / "durum.json").read_bytes()
        self.bildirimler.clear()
        tara.calistir()
        self.assertEqual(self.bildirimler, [])
        self.assertEqual(((self.veri / "ilanlar.json").read_bytes(), (self.veri / "durum.json").read_bytes()), once)

    def test_yeni_ilan_tek_bildirim_elenen_bildirilmez(self):
        self.sayfalar["https://haber.test/feed"] = rss(("Belediye mühendis alacak, KPSS", "https://haber.test/1", ""))
        self.sayfalar["https://kurum.test/"] = SAYFA
        tara.calistir()
        self.bildirimler.clear()
        self.sayfalar["https://haber.test/feed"] = rss(
            ("Belediye mühendis alacak, KPSS", "https://haber.test/1", ""),
            ("Kocaeli Devlet Hastanesi biyomedikal mühendisi alacak", "https://haber.test/3", ""),
            ("Van Üniversitesi KPSS ile mühendis alacak", "https://haber.test/4", ""),
            ("Üniversite 2024 KPSS ile mühendis alımı yapacak", "https://haber.test/5", ""))
        tara.calistir()
        self.assertEqual(len(self.bildirimler), 1)
        (konu, baslik, mesaj), kw = self.bildirimler[0]
        self.assertEqual(konu, "deneme-konu-12345")
        self.assertIn("Biyomedikal", baslik)
        self.assertIn("★Kocaeli", mesaj)
        self.assertEqual(kw["tikla"], "https://haber.test/3")
        tum = {i["url"]: i for i in self.ilanlar()["ilanlar"]}
        self.assertTrue(tum["https://haber.test/4"]["elendi"])           # saklanır ama bildirilmez
        self.assertTrue(tum["https://haber.test/5"]["elendi"])

    def test_profil_secret_puani_tutmayani_bildirmez(self):
        self.sayfalar["https://haber.test/feed"] = rss(("Kocaeli KPSS mühendis alımı", "https://haber.test/9", "KPSSP3 puan türünden en az 70 puan"))
        self.sayfalar["https://kurum.test/"] = SAYFA
        tara.calistir()                                                   # ilk çalışma (özet)
        self.bildirimler.clear()
        self.sayfalar["https://haber.test/feed"] = rss(
            ("Kocaeli KPSS mühendis alımı", "https://haber.test/9", "KPSSP3 puan türünden en az 70 puan"),
            ("Tekirdağ KPSS mühendis alımı", "https://haber.test/10", "KPSSP3 puan türünden en az 70 puan"),
            ("Zonguldak KPSS mühendis alımı", "https://haber.test/11", "KPSSP3 en az 60 puan"))
        with mock.patch.dict(os.environ, {"PROFIL_JSON": json.dumps({"dogum_yili": 1988, "puanlar": {"P3": 63.9}})}):
            tara.calistir()
        self.assertEqual([k["tikla"] for _, k in self.bildirimler], ["https://haber.test/11"])
        # ilanlar.json kişisel veri içermemeli
        self.assertNotIn("63.9", (self.veri / "ilanlar.json").read_text(encoding="utf-8"))
        self.assertNotIn("1988", (self.veri / "ilanlar.json").read_text(encoding="utf-8"))

    def test_gecersiz_konu_bildirimi_kapatir(self):
        self.sayfalar["https://haber.test/feed"] = rss(("Belediye mühendis alacak, KPSS", "https://haber.test/1", ""))
        self.sayfalar["https://kurum.test/"] = SAYFA
        with mock.patch.dict(os.environ, {"NTFY_TOPIC": "bu konu geçersiz!"}):
            tara.calistir()
        self.assertEqual(self.bildirimler, [])

    def test_tek_kaynak_cokerse_digerleri_calisir(self):
        self.sayfalar["https://haber.test/feed"] = rss(("Belediye mühendis alacak, KPSS", "https://haber.test/1", ""))
        self.assertEqual(tara.calistir(), "tamam")                        # kurum.test erişilemez
        d = self.ilanlar()
        self.assertEqual([k["tamam"] for k in d["kaynaklar"]], [True, False])
        self.assertEqual(d["kaynaklar"][1]["hata"], "erişilemedi")        # sabit metin: commit gürültüsü yok

    def test_hic_kaynak_yoksa_hata_ve_dosya_yok(self):
        self.assertEqual(tara.calistir(), "hata")
        self.assertFalse((self.veri / "ilanlar.json").exists())

    def test_sure_bitince_bir_kez_haber_verir(self):
        self.ayar({**AYAR, "bitis_tarihi": "2020-01-01"})
        self.assertEqual(tara.calistir(), "bitti")
        self.assertEqual(tara.calistir(), "bitti")
        self.assertEqual(len(self.bildirimler), 1)
        self.assertIn("Takip süresi doldu", self.bildirimler[0][0][1])

    def test_kuru_calisma_yazmaz_bildirmez(self):
        self.sayfalar["https://haber.test/feed"] = rss(("Belediye mühendis alacak, KPSS", "https://haber.test/1", ""))
        self.sayfalar["https://kurum.test/"] = SAYFA
        tara.calistir(kuru=True)
        self.assertFalse(self.veri.exists())
        self.assertEqual(self.bildirimler, [])


GUID_A = "11111111-1111-1111-1111-111111111111"
GUID_B = "22222222-2222-2222-2222-222222222222"
GUID_C = "33333333-3333-3333-3333-333333333333"
API_BIO = [
    {"ilanBaslik": "Mühendis (Biyomedikal)", "unvan": "Mühendis",
     "ilanMetni": "[b]Aranan nitelikler[/b]\nBiyomedikal Mühendisliği lisans mezunu olmak.\n2026 KPSS (B) P3 puanından en az 60 puan.",
     "kontenjanList": [{"il": "Kocaeli", "kontenjan": 1}], "degerlemeAsamaList": []},
    {"ilanBaslik": "Büro Personeli", "unvan": "Büro Personeli", "ilanMetni": "Lise mezunu olmak.",
     "kontenjanList": [{"il": "Van", "kontenjan": 2}], "degerlemeAsamaList": []},
]
API_SIRADAN = [{"ilanBaslik": "Hemşire", "unvan": "Hemşire", "ilanMetni": "Sağlık meslek lisesi mezunu. " * 40,
                "kontenjanList": [{"il": "Ankara", "kontenjan": 3}], "degerlemeAsamaList": []}]


def kk_rss(*ogeler):
    govde = "".join(
        f'<item><guid isPermaLink="true">https://kariyerkapisi.gov.tr/IlanDetay?i={g}</guid>'
        f"<link>https://kariyerkapisi.gov.tr/IlanDetay?i={g}</link><category>Sözleşmeli Personel İlanları</category>"
        f"<title>{b}</title><pubDate>{format_datetime(dt.datetime.now(dt.timezone.utc))}</pubDate></item>"
        for b, g in ogeler)
    return f'<?xml version="1.0" encoding="utf-8"?><rss version="2.0"><channel><title>KK</title>{govde}</channel></rss>'.encode("utf-8")


class Kategoriler(Taban):
    """Üç ayrı liste ve resmî Kariyer Kapısı akışı."""

    KK = "https://kariyerkapisi.gov.tr/RSS"

    def setUp(self):
        super().setUp()
        self.ayar({**AYAR, "kk_api": True,
                   "kaynaklar": [{"ad": "Kariyer Kapısı (resmî RSS)", "tur": "rss", "url": self.KK, "resmi": True},
                                         {"ad": "Deneme RSS", "tur": "rss", "url": "https://haber.test/feed"}]})
        self.sayfalar["https://haber.test/feed"] = rss(("Jaguar yeni model tanıttı", "https://haber.test/0", ""))
        self.sayfalar[self.KK] = kk_rss()
        tara.calistir()                      # "ilk çalışma" bitsin; sonraki çalışmalar tekil bildirim gönderir
        self.bildirimler.clear()
        self.api_cagri.clear()

    def test_kk_api_varsayilan_kapali(self):
        self.ayar({**AYAR, "kaynaklar": [{"ad": "Kariyer Kapısı (resmî RSS)", "tur": "rss", "url": self.KK, "resmi": True}]})
        self.sayfalar[self.KK] = kk_rss(("KOCAELİ ÜNİVERSİTESİ REKTÖRLÜĞÜ - SÖZLEŞMELİ PERSONEL ALIM İLANI", GUID_A))
        tara.calistir()
        d = self.ilanlar()
        ilan = [i for i in d["ilanlar"] if "KOCAELİ" in i["baslik"]][0]
        self.assertEqual(ilan["seviye"], "toplu")
        self.assertNotIn("ayrinti", ilan)                     # yeniden deneme etiketi yok
        self.assertIn("Resmî Kariyer Kapısı ilanı", ilan["nedenler"][0])
        self.assertEqual(self.api_cagri, [])                  # API hiç çağrılmaz
        self.assertNotIn(tara.KK_DURUM_AD, [k["ad"] for k in d["kaynaklar"]])

    def test_kk_govde_metni(self):
        self.api[GUID_A] = API_BIO
        metin = tara.kk_govde(GUID_A)
        self.assertTrue(metin.startswith("Pozisyonlar:\nMühendis - Mühendis (Biyomedikal) [Kocaeli (1)]"))
        self.assertIn("Biyomedikal Mühendisliği lisans mezunu", metin)
        self.assertNotIn("[b]", metin)

    def test_kk_biyomedikal_pozisyon_bulunur_ve_bildirilir(self):
        self.api[GUID_A] = API_BIO
        self.sayfalar[self.KK] = kk_rss(("KOCAELİ ÜNİVERSİTESİ REKTÖRLÜĞÜ - SÖZLEŞMELİ PERSONEL ALIM İLANI", GUID_A))
        tara.calistir()
        ilan = [i for i in self.ilanlar()["ilanlar"] if i["id"] == tara.kisa_id(f"https://kariyerkapisi.gov.tr/IlanDetay?i={GUID_A}")][0]
        self.assertEqual(ilan["seviye"], "guclu")
        self.assertTrue(ilan["ayrinti"])
        self.assertEqual(ilan["gercekler"]["puan_turleri"], {"P3": 60.0})
        self.assertEqual(ilan["gercekler"]["kpss_durum"], "var")
        self.assertEqual(len(self.bildirimler), 1)
        self.assertEqual(self.bildirimler[0][0][1], "🔥 Biyomedikal ilanı (KPSS'li)")
        durum = {k["ad"]: k["tamam"] for k in self.ilanlar()["kaynaklar"]}
        self.assertTrue(durum[tara.KK_DURUM_AD])

    def test_kk_siradan_ilan_ayrintiya_bakilinca_elenir(self):
        self.api[GUID_B] = API_SIRADAN
        self.sayfalar[self.KK] = kk_rss(("ANKARA ÜNİVERSİTESİ REKTÖRLÜĞÜ - SÖZLEŞMELİ PERSONEL ALIM İLANI", GUID_B))
        tara.calistir()
        self.assertEqual([i for i in self.ilanlar()["ilanlar"] if "ANKARA" in i["baslik"]], [])
        self.assertEqual(self.bildirimler, [])

    def test_kk_api_kapaliysa_baslikla_sinifla_sonra_yeniden_dene(self):
        self.sayfalar[self.KK] = kk_rss(("KOCAELİ ÜNİVERSİTESİ REKTÖRLÜĞÜ - SÖZLEŞMELİ PERSONEL ALIM İLANI", GUID_A))
        tara.calistir()                                                      # API kapalı
        d = self.ilanlar()
        ilan = [i for i in d["ilanlar"] if "KOCAELİ" in i["baslik"]][0]
        self.assertEqual((ilan["seviye"], ilan["ayrinti"]), ("toplu", False))
        self.assertFalse({k["ad"]: k["tamam"] for k in d["kaynaklar"]}[tara.KK_DURUM_AD])
        self.assertEqual(self.bildirimler, [])
        self.api[GUID_A] = API_BIO                                           # API açıldı: aynı ilan yükselir
        tara.calistir()
        ilan = [i for i in self.ilanlar()["ilanlar"] if "KOCAELİ" in i["baslik"]][0]
        self.assertEqual((ilan["seviye"], ilan["ayrinti"]), ("guclu", True))
        self.assertEqual(len(self.bildirimler), 1)
        self.assertEqual(len([i for i in self.ilanlar()["ilanlar"] if "KOCAELİ" in i["baslik"]]), 1)   # çoğalmaz
        self.assertTrue({k["ad"]: k["tamam"] for k in self.ilanlar()["kaynaklar"]}[tara.KK_DURUM_AD])

    def test_kk_iki_hatadan_sonra_denemeyi_birakir(self):
        self.sayfalar[self.KK] = kk_rss(("A ÜNİVERSİTESİ - SÖZLEŞMELİ PERSONEL ALIM İLANI", GUID_A),
                                        ("B ÜNİVERSİTESİ - SÖZLEŞMELİ PERSONEL ALIM İLANI", GUID_B),
                                        ("C ÜNİVERSİTESİ - SÖZLEŞMELİ PERSONEL ALIM İLANI", GUID_C))
        tara.calistir()
        self.assertEqual(len(self.api_cagri), 2)

    def test_kk_durum_sonraki_calismada_korunur(self):
        self.sayfalar[self.KK] = kk_rss(("KOCAELİ ÜNİVERSİTESİ - SÖZLEŞMELİ PERSONEL ALIM İLANI", GUID_A))
        tara.calistir()
        once = self.ilanlar()["kaynaklar"]
        tara.calistir()                      # yeni ilan yok, yeniden deneme API'yi çağırır ve yine hata alır
        self.assertEqual(self.ilanlar()["kaynaklar"], once)

    def test_kpsssiz_biyomedikal_ayri_baslikla_bildirilir(self):
        self.sayfalar["https://haber.test/feed"] = rss(
            ("Hastane KPSS'siz sözleşmeli biyomedikal mühendisi alacak", "https://haber.test/20", ""),
            ("Üniversite KPSS ile sözleşmeli biyomedikal mühendisi alacak", "https://haber.test/21", ""))
        tara.calistir()
        basliklar = sorted(a[1] for a, _ in self.bildirimler)
        self.assertEqual(basliklar, ["🔥 Biyomedikal ilanı (KPSS'li)", "🔥 Biyomedikal ilanı (KPSS'siz)"])

    def test_kpsssiz_genel_muhendis_bildirilmez_ama_listelenir(self):
        self.sayfalar["https://haber.test/feed"] = rss(("Savunma firması KPSS'siz mühendis alacak, kamu ortaklığı", "https://haber.test/22", ""))
        tara.calistir()
        self.assertEqual(self.bildirimler, [])
        self.assertTrue([i for i in self.ilanlar()["ilanlar"] if i["seviye"] == "olasi"])

    def test_herhangi_lisans_dusuk_oncelikle_bildirilir(self):
        self.sayfalar["https://haber.test/feed"] = rss(
            ("DHMİ 12 Personel Alımı Yapacak! Herhangi Bir Lisans Mezununa Memur Kadrosu Açıldı", "https://haber.test/23", ""))
        tara.calistir()
        (konu, baslik, mesaj), kw = self.bildirimler[0]
        self.assertEqual(baslik, "📄 Herhangi lisans · KPSS'li alım")
        self.assertEqual(kw["oncelik"], 2)
        self.assertEqual([i["seviye"] for i in self.ilanlar()["ilanlar"] if "DHMİ" in i["baslik"]], ["lisans"])

    def test_bildirim_seviyeleri_ayardan_degisir(self):
        self.ayar({**AYAR, "bildirim_seviyeleri": ["guclu"],
                   "kaynaklar": [{"ad": "Deneme RSS", "tur": "rss", "url": "https://haber.test/feed"}]})
        self.sayfalar["https://haber.test/feed"] = rss(
            ("DHMİ 12 Personel Alımı Yapacak! Herhangi Bir Lisans Mezununa Memur Kadrosu Açıldı", "https://haber.test/23", ""),
            ("Belediye mühendis alacak, KPSS", "https://haber.test/24", ""))
        tara.calistir()
        self.assertEqual(self.bildirimler, [])


HAT = {"ad": "Deneme dönemi", "baslangic": "2026-12-17", "bitis": "2026-12-24", "gunler_once": [14, 3, 0],
       "not": "Kılavuzda 'Biyomedikal' ara.", "baglanti": "https://osym.test/"}


class HatirlatmaMantigi(unittest.TestCase):
    def bul(self, gun, gonderilen=()):
        return tara.hatirlatma_bul({"hatirlatmalar": [HAT]}, dt.date.fromisoformat(gun), set(gonderilen))

    def test_esikler(self):
        self.assertEqual(self.bul("2026-12-02"), [])                                    # 15 gün kala: henüz değil
        b = self.bul("2026-12-03")[0]
        self.assertEqual(b[1], "📅 Deneme dönemi: 14 gün kaldı")
        self.assertIn("17.12.2026 – 24.12.2026", b[2])
        self.assertIn("Biyomedikal", b[2])
        self.assertEqual(b[3], "https://osym.test/")
        self.assertEqual(self.bul("2026-12-14")[0][1], "📅 Deneme dönemi: 3 gün kaldı")
        self.assertEqual(self.bul("2026-12-17")[0][1], "📅 Deneme dönemi: başladı")
        self.assertEqual(self.bul("2026-12-20")[0][1], "📅 Deneme dönemi: başladı")       # dönem sürerken de (bir kez)
        self.assertEqual(self.bul("2026-12-25"), [])                                    # bitti

    def test_ayni_esik_bir_kez(self):
        anahtarlar = self.bul("2026-12-03")[0][0]
        self.assertEqual(self.bul("2026-12-03", anahtarlar), [])
        self.assertEqual(self.bul("2026-12-10", anahtarlar), [])                        # 14 gün eşiği tamam, 3 gün henüz yok

    def test_kacan_esikler_tek_bildirim(self):
        b = self.bul("2026-12-15")                                                      # 2 gün kala, hiç gönderilmemiş
        self.assertEqual(len(b), 1)
        self.assertEqual(b[0][1], "📅 Deneme dönemi: 2 gün kaldı")
        self.assertEqual(len(b[0][0]), 2)                                               # 14 ve 3 gün eşikleri de işaretlenir
        self.assertEqual(self.bul("2026-12-16", b[0][0]), [])


class Hatirlatma(Taban):
    def setUp(self):
        super().setUp()
        self.saat = dt.datetime(2026, 12, 2, 9, 0, tzinfo=dt.timezone.utc)
        self.yama = mock.patch.object(tara, "simdi_al", side_effect=lambda: self.saat)
        self.yama.start()
        self.ayar({**AYAR, "hatirlatmalar": [HAT], "kaynaklar": [{"ad": "Deneme RSS", "tur": "rss", "url": "https://haber.test/feed"}]})
        self.sayfalar["https://haber.test/feed"] = rss(("Jaguar yeni model tanıttı", "https://haber.test/0", ""))

    def tearDown(self):
        self.yama.stop()
        super().tearDown()

    def gun(self, g):
        self.saat = dt.datetime.fromisoformat(g + "T09:00:00+00:00")
        self.bildirimler.clear()
        tara.calistir()
        return [(a[1], k) for a, k in self.bildirimler]

    def test_takvim_boyunca(self):
        self.assertEqual(self.gun("2026-12-02"), [])
        b = self.gun("2026-12-03")
        self.assertEqual([x[0] for x in b], ["📅 Deneme dönemi: 14 gün kaldı"])
        self.assertEqual(b[0][1]["oncelik"], 4)
        self.assertEqual(self.gun("2026-12-03"), [])                                    # aynı gün ikinci tarama: sessiz
        self.assertEqual(self.gun("2026-12-10"), [])
        self.assertEqual([x[0] for x in self.gun("2026-12-14")], ["📅 Deneme dönemi: 3 gün kaldı"])
        self.assertEqual([x[0] for x in self.gun("2026-12-17")], ["📅 Deneme dönemi: başladı"])
        self.assertEqual(self.gun("2026-12-18"), [])
        self.assertEqual(self.gun("2026-12-25"), [])

    def test_durum_kalici(self):
        self.gun("2026-12-03")
        durum = json.loads((self.veri / "durum.json").read_text(encoding="utf-8"))
        self.assertEqual(len(durum["hatirlatma"]), 1)

    def test_konu_yoksa_gonderilmez_ve_isaretlenmez(self):
        self.saat = dt.datetime(2026, 12, 3, 9, 0, tzinfo=dt.timezone.utc)
        with mock.patch.dict(os.environ, {"NTFY_TOPIC": ""}):
            tara.calistir()
        self.assertEqual(self.bildirimler, [])
        self.assertEqual(self.gun("2026-12-03")[0][0], "📅 Deneme dönemi: 14 gün kaldı")   # konu gelince yine gönderilir

    def test_gonderim_hatasinda_isaretlenmez(self):
        self.saat = dt.datetime(2026, 12, 3, 9, 0, tzinfo=dt.timezone.utc)
        with mock.patch.object(tara, "ntfy_gonder", side_effect=OSError("ağ yok")):
            tara.calistir()
        self.assertEqual(self.gun("2026-12-03")[0][0], "📅 Deneme dönemi: 14 gün kaldı")   # bir sonraki taramada tekrar denenir

    def test_hatirlatma_ayari_sayfaya_yansir(self):
        tara.calistir()
        d = self.ilanlar()
        self.assertEqual(d["ayar"]["hatirlatmalar"][0]["ad"], "Deneme dönemi")


class IzlenenKurum(Taban):
    def setUp(self):
        super().setUp()
        self.ayar({**AYAR, "izlenen": {"kurumlar": ["Avcılar"], "belediye_illeri": ["İstanbul"]},
                   "kaynaklar": [{"ad": "Deneme RSS", "tur": "rss", "url": "https://haber.test/feed"}]})
        self.sayfalar["https://haber.test/feed"] = rss(("Jaguar yeni model tanıttı", "https://haber.test/0", ""))
        tara.calistir()
        self.bildirimler.clear()

    def test_izlenen_kurum_toplu_olsa_da_bildirilir(self):
        self.sayfalar["https://haber.test/feed"] = rss(
            ("Avcılar Belediyesi 20 personel alacak", "https://haber.test/1", ""),
            ("Kocaeli Belediyesi 20 personel alacak", "https://haber.test/2", ""))
        tara.calistir()
        self.assertEqual(len(self.bildirimler), 1)
        (konu, baslik, mesaj), kw = self.bildirimler[0]
        self.assertEqual(baslik, "🏛️ İzlediğin kurumda ilan")
        self.assertEqual(kw["tikla"], "https://haber.test/1")
        kayit = {i["url"]: i for i in self.ilanlar()["ilanlar"]}
        self.assertTrue(kayit["https://haber.test/1"]["izlenen"])
        self.assertNotIn("izlenen", kayit["https://haber.test/2"])

    def test_izlenen_kurum_elenmisse_bildirilmez(self):
        self.sayfalar["https://haber.test/feed"] = rss(
            ("Avcılar Belediyesi 2024 KPSS ile personel alacak", "https://haber.test/3", ""))
        tara.calistir()
        self.assertEqual(self.bildirimler, [])


if __name__ == "__main__":
    unittest.main()
