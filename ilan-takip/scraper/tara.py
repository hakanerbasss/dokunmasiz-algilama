#!/usr/bin/env python3
"""Kaynakları gezer, uygun ilanları data/ilanlar.json'a yazar, yenileri ntfy ile bildirir.

Ortam değişkenleri (hepsi isteğe bağlı):
  NTFY_TOPIC   bildirim konusu (GitHub Secret). Yoksa bildirim gönderilmez.
  PROFIL_JSON  {"dogum_yili":1988,"puanlar":{"P1":..,"P2":..,"P3":..}} (GitHub Secret).
               Varsa puanı/yaşı tutmayan ilanlar için bildirim gönderilmez.
  VERI_DIZINI  data/ yerine başka bir klasöre yaz (yerel deneme).
Bayraklar: --kuru (yazma/bildirim yok, sadece yazdır), --sifirla (görülenleri unut).
"""
import datetime as dt
import gzip
import hashlib
import json
import os
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from email.utils import parsedate_to_datetime
from html.parser import HTMLParser
from pathlib import Path

import analiz

KLASOR = Path(__file__).resolve().parent
VERI = Path(os.environ.get("VERI_DIZINI") or KLASOR.parent / "data")
UA = "Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Mobile Safari/537.36"
NS_ICERIK = "{http://purl.org/rss/1.0/modules/content/}encoded"
ILAN_SINIRI = 600          # data/ilanlar.json'da tutulacak en çok ilan
GORULEN_GUN = 500          # görülen kimliklerin saklanma süresi
BILDIRIM_GUN = 30          # bundan eski ilanlar için bildirim gönderme
KEEPALIVE_GUN = 10         # değişiklik olmasa da bu sürede bir kayıt yaz (Actions'ı canlı tutar)
DETAY_SINIRI = 12          # çalıştırma başına en çok kaç ilan sayfası açılsın


# ---------------------------------------------------------------- ağ ve ayrıştırma
def indir(url, zaman_asimi=25, tekrar=2):
    son = None
    for _ in range(tekrar + 1):
        try:
            istek = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Encoding": "gzip, identity",
                                                         "Accept-Language": "tr-TR,tr;q=0.9"})
            with urllib.request.urlopen(istek, timeout=zaman_asimi) as r:
                veri = r.read(6_000_000)
                if r.headers.get("Content-Encoding") == "gzip":
                    veri = gzip.decompress(veri)
                return veri, r.headers.get("Content-Type", ""), r.headers.get_content_charset() or "utf-8"
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            son = e
    raise RuntimeError(f"{url}: {son}")


class _Sayfa(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.parcalar, self.baglar, self._atla, self._a = [], [], 0, None

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "noscript"):
            self._atla += 1
        elif tag == "a":
            self._a = {"href": dict(attrs).get("href"), "metin": []}
        elif tag in ("p", "br", "li", "tr", "div", "h1", "h2", "h3", "h4", "table"):
            self.parcalar.append("\n")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "noscript"):
            self._atla = max(0, self._atla - 1)
        elif tag == "a" and self._a is not None:
            self.baglar.append((self._a["href"], " ".join("".join(self._a["metin"]).split())))
            self._a = None
        elif tag in ("td", "th"):
            self.parcalar.append(" ")

    def handle_data(self, d):
        if self._atla:
            return
        self.parcalar.append(d)
        if self._a is not None:
            self._a["metin"].append(d)


def html_coz(html):
    p = _Sayfa()
    try:
        p.feed(html)
    except Exception:  # bozuk HTML'de eldekiyle devam et
        pass
    metin = re.sub(r"[ \t\r\f\v]+", " ", "".join(p.parcalar))
    return re.sub(r"\n\s*\n+", "\n", metin).strip(), p.baglar


def kisa_id(s):
    return hashlib.sha1(s.encode("utf-8")).hexdigest()[:16]


def tarih_iso(s):
    try:
        return parsedate_to_datetime(s).astimezone(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    except (TypeError, ValueError):
        return None


def rss_oku(veri, ad, gnews=False):
    kok = ET.fromstring(veri)
    ogeler = []
    for it in kok.iter("item"):
        baslik = (it.findtext("title") or "").strip()
        url = (it.findtext("link") or "").strip()
        if not baslik or not url:
            continue
        govde = ""
        icerik = it.findtext(NS_ICERIK)
        if icerik:
            govde = html_coz(icerik)[0]
        ogeler.append({
            "id": (it.findtext("guid") or url).strip() if gnews else kisa_id(url),
            "baslik": analiz.temiz_baslik(baslik) if gnews else baslik,
            "url": url, "govde": govde, "kaynak": ad,
            "tarih": tarih_iso(it.findtext("pubDate")),
        })
    return ogeler


def sayfa_oku(html, taban, ad, filtre, resmi=False):
    _, baglar = html_coz(html)
    rx = re.compile(filtre) if filtre else None
    gorulen, ogeler = set(), []
    for href, metin in baglar:
        if not href or len(metin) < 15 or href.startswith(("#", "javascript:", "mailto:")):
            continue
        if rx and not rx.search(analiz.fold(metin)):
            continue
        url = urllib.parse.urljoin(taban, href)
        if url in gorulen:
            continue
        gorulen.add(url)
        ogeler.append({"id": kisa_id(url), "baslik": metin, "url": url, "govde": "", "kaynak": ad, "tarih": None,
                       "resmi": resmi})
    return ogeler


def gnews_url(sorgu):
    q = urllib.parse.quote_plus(sorgu + " when:30d")
    return f"https://news.google.com/rss/search?q={q}&hl=tr&gl=TR&ceid=TR:tr"


def kaynak_getir(k):
    """-> (kaynak_durumu, ogeler). Hata bir kaynağı düşürür, çalıştırmayı değil."""
    try:
        veri, _, kodlama = indir(k["url"])
        if k["tur"] == "rss":
            ogeler = rss_oku(veri, k["ad"], gnews=k.get("gnews", False))
        else:
            ogeler = sayfa_oku(veri.decode(kodlama, "replace"), k["url"], k["ad"], k.get("filtre"), k.get("resmi", False))
        return {"ad": k["ad"], "tamam": True, "hata": ""}, ogeler
    except Exception as e:  # noqa: BLE001 - tek kaynağın hatası diğerlerini durdurmamalı
        print(f"   kaynak hatası ({k['ad']}): {str(e)[:200]}")
        return {"ad": k["ad"], "tamam": False, "hata": "erişilemedi"}, []


def govde_getir(url):
    try:
        veri, tur, kodlama = indir(url, zaman_asimi=20, tekrar=1)
        if "html" not in tur.lower():
            return ""
        return analiz.govde_temizle(html_coz(veri.decode(kodlama, "replace"))[0])[:12000]
    except Exception:  # noqa: BLE001
        return ""


# ---------------------------------------------------------------- bildirim
def ntfy_gonder(konu, baslik, mesaj, tikla=None, oncelik=3, etiketler=()):
    govde = {"topic": konu, "title": baslik[:200], "message": mesaj[:900], "priority": oncelik, "tags": list(etiketler)}
    if tikla:
        govde["click"] = tikla
    istek = urllib.request.Request("https://ntfy.sh/", data=json.dumps(govde).encode("utf-8"),
                                   headers={"Content-Type": "application/json", "User-Agent": "ilan-takip"})
    with urllib.request.urlopen(istek, timeout=20) as r:
        r.read()


def ozet(ilan, ayar):
    g = ilan["gercekler"]
    parcalar = []
    if g["iller"]:
        isaret = lambda il: "★" + il if il in ayar["tercih_iller"] else il  # noqa: E731
        parcalar.append("📍 " + ", ".join(isaret(i) for i in g["iller"][:5]))
    for tur, mn in g["puan_turleri"].items():
        parcalar.append(f"KPSS{tur}" + (f" ≥ {mn:g}" if mn else ""))
    if g["yas_siniri"]:
        parcalar.append(f"yaş < {g['yas_siniri']}")
    return " · ".join(parcalar)


def bildir(konu, yeniler, ayar, sayfa_url, ilk):
    if not yeniler:
        return
    if ilk or len(yeniler) > 5:
        satirlar = [("🔥 " if i["seviye"] == "guclu" else "⚙️ ") + i["baslik"][:90] for i in yeniler[:8]]
        baslik = f"Takip başladı: {len(yeniler)} uygun ilan" if ilk else f"{len(yeniler)} yeni uygun ilan"
        ntfy_gonder(konu, baslik, "\n".join(satirlar) + f"\n\nTümü: {sayfa_url}", tikla=sayfa_url, oncelik=3, etiketler=["briefcase"])
        return
    for i in yeniler:
        guclu = i["seviye"] == "guclu"
        ntfy_gonder(konu, ("🔥 Biyomedikal ilanı" if guclu else "⚙️ Mühendis ilanı"),
                    f"{i['baslik']}\n{ozet(i, ayar)}".strip(), tikla=i["url"],
                    oncelik=4 if guclu else 3, etiketler=["dart" if guclu else "gear"])


# ---------------------------------------------------------------- ana akış
def oku_json(yol, varsayilan):
    try:
        return json.loads(Path(yol).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return varsayilan


def yaz_json(yol, veri):
    Path(yol).parent.mkdir(parents=True, exist_ok=True)
    Path(yol).write_text(json.dumps(veri, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def bildirilebilir(ilan, profil_elemesi, simdi):
    if ilan["seviye"] not in ("guclu", "olasi") or ilan["elendi"] or profil_elemesi:
        return False
    if ilan["tarih"]:
        yas = simdi - dt.datetime.strptime(ilan["tarih"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=dt.timezone.utc)
        if yas.days > BILDIRIM_GUN:
            return False
    return True


def calistir(kuru=False, sifirla=False):
    ayar = oku_json(KLASOR / "ayar.json", {})
    simdi = dt.datetime.now(dt.timezone.utc)
    bugun = simdi.date()
    konu = (os.environ.get("NTFY_TOPIC") or "").strip()
    if konu and not re.fullmatch(r"[A-Za-z0-9_-]{8,64}", konu):
        print("UYARI: NTFY_TOPIC geçersiz (8-64 harf/rakam/-/_); bildirim kapalı.")
        konu = ""
    try:
        profil = json.loads(os.environ.get("PROFIL_JSON") or "null")
    except ValueError:
        print("UYARI: PROFIL_JSON okunamadı; puan/yaş filtresi bildirimde kapalı.")
        profil = None
    depo = os.environ.get("GITHUB_REPOSITORY", "")
    sayfa_url = (f"https://{depo.split('/')[0]}.github.io/{depo.split('/')[1]}/ilan-takip/" if "/" in depo else "")

    durum = oku_json(VERI / "durum.json", {})
    if sifirla:
        durum = {}
    ilk = "gorulen" not in durum
    gorulen = durum.setdefault("gorulen", {})

    bitis = dt.date.fromisoformat(ayar["bitis_tarihi"])
    if bugun > bitis:
        if konu and not durum.get("bitis_bildirildi") and not kuru:
            ntfy_gonder(konu, "Takip süresi doldu", f"{ayar['bitis_tarihi']} tarihinde 2 yıllık takip sona erdi. "
                        "Uzatmak için ilan-takip/scraper/ayar.json içindeki bitis_tarihi'ni ileri al.")
            durum["bitis_bildirildi"] = True
            yaz_json(VERI / "durum.json", durum)
        print("Takip süresi doldu.")
        return "bitti"

    # 1) kaynakları paralel getir
    kaynaklar = [{"ad": f"Google Haberler: {q}", "tur": "rss", "url": gnews_url(q), "gnews": True}
                 for q in ayar.get("google_haberler", [])] + ayar.get("kaynaklar", [])
    with ThreadPoolExecutor(max_workers=4) as havuz:
        sonuclar = list(havuz.map(kaynak_getir, kaynaklar))
    kaynak_durumlari = [d for d, _ in sonuclar]
    adaylar = [o for _, ogeler in sonuclar for o in ogeler]
    for d, ogeler in sonuclar:
        print(f"{'ok ' if d['tamam'] else 'HATA'} {len(ogeler):3d}  {d['ad']}")
    if not any(d["tamam"] for d in kaynak_durumlari):
        print("Hiçbir kaynağa ulaşılamadı; çalıştırma boş geçildi.")
        return "hata"

    # 2) çözümle
    onceki = oku_json(VERI / "ilanlar.json", {})
    ilanlar = [] if sifirla else list(onceki.get("ilanlar", []))
    tk_gorulen = {k for k in gorulen if k.startswith("t:")}
    yeniler, detay = [], 0
    for o in adaylar:
        tk = "t:" + kisa_id(analiz.fold(o["baslik"])[:90])
        if o["id"] in gorulen or tk in tk_gorulen:
            continue
        gorulen[o["id"]] = gorulen[tk] = bugun.isoformat()
        tk_gorulen.add(tk)
        resmi = o.get("resmi", False)
        if analiz.sinifla(o["baslik"], o["govde"], resmi) is None:
            continue
        govde = o["govde"]
        if not govde and "news.google.com" not in o["url"] and detay < DETAY_SINIRI:
            govde, detay = govde_getir(o["url"]), detay + 1
        d = analiz.degerlendir(o["baslik"], govde, ayar, profil, yil=bugun.year, resmi=resmi)
        if d is None:
            continue
        ilan = {"id": o["id"], "baslik": o["baslik"], "url": o["url"], "kaynak": o["kaynak"], "tarih": o["tarih"],
                "ilk_gorulme": simdi.strftime("%Y-%m-%dT%H:%M:%SZ"), "seviye": d["seviye"],
                "nedenler": d["nedenler"], "gercekler": d["gercekler"], "elendi": d["elendi"]}
        ilanlar.append(ilan)
        print(f"  + [{d['seviye']:6}] {o['baslik'][:100]}" + (f"   (eleme: {'; '.join(d['elendi'] + d['elendi_profil'])})" if d["elendi"] or d["elendi_profil"] else ""))
        if bildirilebilir(ilan, d["elendi_profil"], simdi):
            yeniler.append(ilan)

    ilanlar.sort(key=lambda i: (i["ilk_gorulme"], i["tarih"] or ""), reverse=True)
    ilanlar = ilanlar[:ILAN_SINIRI]
    sinir = (bugun - dt.timedelta(days=GORULEN_GUN)).isoformat()
    durum["gorulen"] = {k: v for k, v in gorulen.items() if v >= sinir}

    # 3) yaz (değişiklik yoksa dosyaya dokunma; ama KEEPALIVE_GUN'de bir kayıt yaz)
    yeni_icerik = {"ilanlar": ilanlar, "kaynaklar": kaynak_durumlari}
    eski_icerik = {"ilanlar": onceki.get("ilanlar", []), "kaynaklar": onceki.get("kaynaklar", [])}
    son_kayit = dt.date.fromisoformat(durum.get("son_kayit", "2000-01-01"))
    degisti = yeni_icerik != eski_icerik or ilk
    if not kuru and (degisti or (bugun - son_kayit).days >= KEEPALIVE_GUN):
        yaz_json(VERI / "ilanlar.json", {
            "surum": 1, "guncelleme": simdi.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "baslangic": ayar["baslangic_tarihi"], "bitis": ayar["bitis_tarihi"], "depo": depo,
            "ayar": {k: ayar[k] for k in ("kpss_yillari", "tercih_iller", "yakin_iller", "engelli_iller")},
            "kaynaklar": kaynak_durumlari, "ilanlar": ilanlar})
        durum["son_kayit"] = bugun.isoformat()
        yaz_json(VERI / "durum.json", durum)

    # 4) bildir
    print(f"Yeni ilan: {len([i for i in ilanlar if i['ilk_gorulme'] == simdi.strftime('%Y-%m-%dT%H:%M:%SZ')])}, bildirilecek: {len(yeniler)}")
    if konu and not kuru:
        try:
            bildir(konu, yeniler, ayar, sayfa_url, ilk)
        except Exception as e:  # noqa: BLE001 - bildirim hatası veri kaydını bozmamalı
            print(f"UYARI: bildirim gönderilemedi: {e}")
    return "tamam"


if __name__ == "__main__":
    sonuc = calistir(kuru="--kuru" in sys.argv, sifirla="--sifirla" in sys.argv)
    cikti = os.environ.get("GITHUB_OUTPUT")
    if cikti:
        with open(cikti, "a", encoding="utf-8") as f:
            f.write(f"bitti={'true' if sonuc == 'bitti' else 'false'}\n")
    sys.exit(1 if sonuc == "hata" else 0)
