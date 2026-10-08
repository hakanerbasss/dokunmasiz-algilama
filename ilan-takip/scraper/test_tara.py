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


class Akis(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.kok = Path(self.tmp.name)
        (self.kok / "ayar").mkdir()
        self.ayar(AYAR)
        self.veri = self.kok / "data"
        self.bildirimler = []
        self.sayfalar = {}
        self.yamalar = [
            mock.patch.object(tara, "KLASOR", self.kok / "ayar"),
            mock.patch.object(tara, "VERI", self.veri),
            mock.patch.object(tara, "indir", side_effect=self._indir),
            mock.patch.object(tara, "ntfy_gonder", side_effect=lambda *a, **k: self.bildirimler.append((a, k))),
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

    def ilanlar(self):
        return json.loads((self.veri / "ilanlar.json").read_text(encoding="utf-8"))

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


if __name__ == "__main__":
    unittest.main()
