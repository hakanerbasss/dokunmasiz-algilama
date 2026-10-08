"""İlan metnini çözümleyen saf mantık. Ağ yok; test edilebilir.

Bir ilan başlığı (ve varsa gövde metni) alınır, biyomedikal mühendisine uygun
olup olmadığı sınıflanır ve KPSS puanı / yaş sınırı / il gibi "gerçekler" çıkarılır.
"""
import re

_TR = str.maketrans("çğıöşüâîûÇĞİÖŞÜÂÎÛ", "cgiosuaiuCGIOSUAIU")


def fold(s):
    """Türkçe karakterleri sadeleştirip küçük harfe çevirir ("İŞ" -> "is")."""
    return re.sub(r"\s+", " ", (s or "").translate(_TR).lower())


BIO = re.compile(r"biyomedikal|biomedikal|biyo medikal|biomedical|biyomedical|"
                 r"\btip muhendis|\bklinik muhendis|biyomuhendis|tibbi cihaz muhendis")
MUH = re.compile(r"\bmuhendis(?!lik)")
HIRE = re.compile(r"\b(?:alim|alin|alac|aliyor|alir|arani?yor|ariyor|ilani|ilan\b|ilanlar|"
                  r"basvuru|yerlestirme|istihdam|duyuru|kadro)")
PERSONEL = re.compile(r"personel|memur|sozlesmeli|\bkadro|\bisci\b|istihdam|kpss|"
                      r"\b4\s?/\s?[abd]\b|mulakat|uzman yardimci|gorevlisi|ogretim uyesi|ise alim")
PROC = re.compile(r"\bihale|mal alim|hizmet alim|cihaz alim|arac alim|satin alim|ekipman alim")
PROC_ISTISNA = re.compile(r"personel alim|memur alim|isci alim")
PRIVATE = re.compile(r"\bfirma|\bsirket|ozel sektor|\bholding|kariyer\.net")
ILGILI_KURUM = re.compile(r"titck|tibbi cihaz kurumu|saglik bakanlig|saglik bilimleri universite|"
                          r"kamu hastaneleri|tubitak|tuseb|devlet malzeme ofisi|acil saglik")
KILAVUZ = re.compile(r"kpss.*(?:tercih kilavuz|merkezi yerlestirme|yerlestirme)|"
                     r"(?:tercih kilavuz|merkezi yerlestirme).*kpss")
KILAVUZ_HARIC = re.compile(r"sonuc|tus\b|ydus|ozyes|cevap|soru kitapcigi|ek-?\s?yerlestirme sonuc")
_BRANS_AD = (r"insaat|makine|elektrik|elektronik|bilgisayar|yazilim|gida|ziraat|harita|jeoloji|jeofizik|"
             r"maden|cevre|kimya|endustri|orman|metalurji|malzeme|ucak|gemi|tekstil|petrol|fizik|"
             r"biyoloji|mekatronik|otomasyon|enerji|kontrol")
BRANS = re.compile(r"((?:(?:%s)\w*[\s\-/,]*(?:ve\s+)?)+)muhendis" % _BRANS_AD)
PUBLIC = re.compile(r"kpss|kamu|bakanlig|universite|rektorlug|belediye|baskanlig|genel mudurlug|valilig|"
                    r"\bkurumu|hastane|tubitak|tuseb|titck|devlet|sozlesmeli|memur")
SONUC = re.compile(r"\bsonuc|resmi gazete karar")
TAHMIN = re.compile(r"ne zaman|\bmi\b|\bmu\b|\?|nasil|nereden|tarihi belli|bekleniyor|gundemi")
TOPLU_HARIC = re.compile(r"akademik|ogretim uyesi|ogretim gorevlisi|arastirma gorevlisi|profesor|docent|"
                         r"kpss\W{0,3}siz|kpss (?:sarti )?olmadan|kpss (?:puani )?(?:olmayan|aranmaz)|"
                         r"\biskur|\bisci\b")
HER_BRANS = re.compile(r"tum muhendis|her turlu muhendis|muhendislik fakulteler|ilgili muhendis|"
                       r"muhendislik bolumler|muhendislik alanlar|muhendis \(her|muhendislik programlar")

ILLER = ["Adana", "Adıyaman", "Afyonkarahisar", "Ağrı", "Aksaray", "Amasya", "Ankara", "Antalya",
         "Ardahan", "Artvin", "Aydın", "Balıkesir", "Bartın", "Batman", "Bayburt", "Bilecik", "Bingöl",
         "Bitlis", "Bolu", "Burdur", "Bursa", "Çanakkale", "Çankırı", "Çorum", "Denizli", "Diyarbakır",
         "Düzce", "Edirne", "Elazığ", "Erzincan", "Erzurum", "Eskişehir", "Gaziantep", "Giresun",
         "Gümüşhane", "Hakkari", "Hatay", "Iğdır", "Isparta", "İstanbul", "İzmir", "Kahramanmaraş",
         "Karabük", "Karaman", "Kars", "Kastamonu", "Kayseri", "Kırıkkale", "Kırklareli", "Kırşehir",
         "Kilis", "Kocaeli", "Konya", "Kütahya", "Malatya", "Manisa", "Mardin", "Mersin", "Muğla",
         "Muş", "Nevşehir", "Niğde", "Ordu", "Osmaniye", "Rize", "Sakarya", "Samsun", "Siirt", "Sinop",
         "Sivas", "Şanlıurfa", "Şırnak", "Tekirdağ", "Tokat", "Trabzon", "Tunceli", "Uşak", "Van",
         "Yalova", "Yozgat", "Zonguldak"]
# İlçe / eski ad -> il
TAKMA_ADLAR = {"silivri": "İstanbul", "izmit": "Kocaeli", "gebze": "Kocaeli", "golcuk": "Kocaeli",
               "corlu": "Tekirdağ", "cerkezkoy": "Tekirdağ", "safranbolu": "Karabük",
               "amasra": "Bartın", "maras": "Kahramanmaraş", "urfa": "Şanlıurfa",
               "afyon": "Afyonkarahisar", "icel": "Mersin"}
# "Van", "Ordu", "Ağrı" sıradan sözcük de olabilir; yalnızca büyük harfle yazılmışsa il say.
_BELIRSIZ = {"Van", "Ordu", "Ağrı"}
_IL_RE = {fold(il): re.compile(r"\b%s\b" % re.escape(fold(il))) for il in ILLER if il not in _BELIRSIZ}
_TAKMA_RE = {k: re.compile(r"\b%s\b" % k) for k in TAKMA_ADLAR}
_BELIRSIZ_RE = {il: re.compile(r"(?<!\w)(?:%s|%s)(?!\w)" % (il, il.upper())) for il in _BELIRSIZ}
_FOLD_IL = {fold(il): il for il in ILLER}


def govde_temizle(metin):
    """Haber sitelerinin "benzer haberler" kuyruğunu keser; yoksa ilgisiz il/yıl sızar."""
    # fold() boşlukları birleştirir ve indeksi kaydırır; burada yalnızca 1:1 harf eşlemesi kullanılır.
    m = re.search(r"ilginiz cekebilir|benzer gonderiler|populer haberler|ilgili haberler|diger haberler|"
                  r"yorumlar\b", metin.translate(_TR).lower())
    return metin[:m.start()] if m else metin


def temiz_baslik(baslik):
    """Google Haberler başlıklarının sonundaki " - Yayıncı" ekini atar."""
    return re.sub(r"\s+-\s+[^-]{2,60}$", "", baslik or "").strip()


def iller_bul(orijinal, katlanmis):
    bulunan = []
    for ad, rx in _IL_RE.items():
        if rx.search(katlanmis):
            bulunan.append(_FOLD_IL[ad])
    for takma, rx in _TAKMA_RE.items():
        if rx.search(katlanmis) and TAKMA_ADLAR[takma] not in bulunan:
            bulunan.append(TAKMA_ADLAR[takma])
    for il, rx in _BELIRSIZ_RE.items():
        if rx.search(orijinal) and il not in bulunan:
            bulunan.append(il)
    return sorted(bulunan)


def _sayi(s):
    try:
        return float(s.replace(",", "."))
    except ValueError:
        return None


def kpss_yillari(tum):
    """KPSS'ye bitişik yıllar: "2024 KPSS (B)", "2024 yılı KPSS", "KPSS-2026/2", "2026 P3". Tarihleri saymaz."""
    yillar = set()
    for rx in (r"(?<!\d)(20[12]\d)\s*(?:yili\s*)?kpss", r"kpss\W{0,3}(20[12]\d)(?!\d)",
               r"(?<!\d)(20[12]\d)\s*p\d{1,3}\b"):
        for y in re.findall(rx, tum):
            if 2018 <= int(y) <= 2027:
                yillar.add(int(y))
    return sorted(yillar)


def puan_turleri(tum):
    """{"P3": 70.0, ...}; asgari puan yazmıyorsa None."""
    sonuc = {}
    rx = re.compile(r"kpss\s*[-_(]*\s*(?:[ab]\s*\)?\s*(?:grubu)?\s*)?[-\s]*p\s*(\d{1,3})(?!\d)")
    for m in rx.finditer(tum):
        tur = "P" + m.group(1)
        pencere = tum[m.end(): m.end() + 90]
        mn = None
        a = re.search(r"(?:en az|asgari|taban|minimum|az)\D{0,40}?(?<![\d.,])(\d{2}(?:[.,]\d{1,5})?)(?![\d/])", pencere)
        b = re.search(r"(?<![\d.,/])(\d{2}(?:[.,]\d{1,5})?)(?![\d/])\s*(?:puan|ve ustu|ve uzeri)", pencere)
        for hit in (a, b):
            if hit:
                v = _sayi(hit.group(1))
                if v is not None and 40 <= v <= 100:
                    mn = v
                    break
        if tur not in sonuc or (sonuc[tur] is None and mn is not None):
            sonuc[tur] = mn
    return sonuc


def genel_puanlar(tum):
    """Puan türü belirtilmeden geçen "65 puanla", "50-59 puanla" gibi taban puanlar."""
    bulunan = []
    for m in re.finditer(r"(?<![\d.,/p])(\d{2})(?:\s*-\s*(\d{2}))?\s*puan(?:la|i|in|a)?\b", tum):
        for g in m.groups():
            if g and 40 <= int(g) <= 100:
                bulunan.append(int(g))
    return sorted(set(bulunan))


def yas_siniri(tum):
    m = re.search(r"(\d{2})\s*yas(?:ini|indan)?\s*(?:doldurmamis|gecmemis|asmamis|gun\s*almamis)", tum)
    if m:
        return int(m.group(1))
    m = re.search(r"18\s*-\s*(\d{2})\s*yas", tum)
    return int(m.group(1)) if m else None


def branslar(tum):
    bulunan = set()
    for m in BRANS.finditer(tum):
        bulunan |= set(re.findall(_BRANS_AD, m.group(1)))
    return sorted(bulunan)


def gercekler(orijinal, tum):
    return {
        "kpss_yillari": kpss_yillari(tum),
        "puan_turleri": puan_turleri(tum),
        "genel_puanlar": genel_puanlar(tum),
        "yas_siniri": yas_siniri(tum),
        "iller": iller_bul(orijinal, tum),
        "ehliyet": bool(re.search(r"surucu belgesi|ehliyet", tum)),
        "bolumler": branslar(tum),
    }


def sinifla(baslik, govde="", resmi=False):
    """-> (seviye, nedenler) ya da None (ilgisiz).

    seviye: guclu (biyomedikal geçiyor) | olasi (mühendis ilanı / KPSS kılavuzu) |
            dusuk (bölüm listesinde biyomedikal yok) | toplu (toplu alım, kadro listesine bak)
    """
    t = fold(baslik)
    g = fold(govde[:12000])
    tum = f"{t} {g}".strip()
    nedenler = []

    if resmi and KILAVUZ.search(t) and not KILAVUZ_HARIC.search(t) and not TAHMIN.search(t):
        return "olasi", ["KPSS merkezi yerleştirme kılavuzu: biyomedikal/mühendis kadrolarını kılavuzda ara"]

    if not HIRE.search(t) or SONUC.search(t):
        return None
    dogrudan = BIO.search(t) or (MUH.search(t) and PUBLIC.search(t))
    if not (PERSONEL.search(t) or dogrudan):
        return None
    if PROC.search(t) and not PROC_ISTISNA.search(t):
        return None
    if PRIVATE.search(t) and "kpss" not in tum:
        return None

    if BIO.search(t):
        return "guclu", ["Başlıkta biyomedikal/tıp mühendisliği geçiyor"]
    if BIO.search(g):
        return "guclu", ["Metinde biyomedikal/tıp mühendisliği kadrosu geçiyor"]

    if MUH.search(t) or MUH.search(g):
        if TAHMIN.search(t):
            return None
        liste = branslar(tum)
        if liste and not HER_BRANS.search(tum):
            return "dusuk", ["Mühendis ilanı ama bölüm listesinde biyomedikal yok (%s)" % ", ".join(liste)]
        kaynak = "başlıkta" if MUH.search(t) else "metinde"
        return "olasi", [f"Mühendis ilanı ({kaynak}); bölüm kısıtı görünmüyor"]

    if g and not MUH.search(g):
        # Gövde okundu ve mühendis hiç geçmiyor: toplu alımda mühendis kadrosu yok demektir.
        if len(g) > 800:
            return None

    if TAHMIN.search(t) or TOPLU_HARIC.search(t) or egitim_elemesi(tum):
        return None
    if ILGILI_KURUM.search(tum):
        nedenler.append("Sağlık/tıbbi cihaz ile ilgili kurum: kadro listesinde mühendis olabilir")
    else:
        nedenler.append("Toplu personel alımı: kadro listesinde mühendis var mı bak")
    return "toplu", nedenler


def kpss_yili_elemesi(g, ayar):
    gecerli = set(ayar.get("kpss_yillari", [2026]))
    if g["kpss_yillari"] and not (set(g["kpss_yillari"]) & gecerli):
        return "%s KPSS puanı esas alınıyor (sende yalnızca %s var)" % (
            "/".join(map(str, g["kpss_yillari"])), "/".join(map(str, sorted(gecerli))))
    return None


def il_elemesi(g, ayar):
    engelli = set(ayar.get("engelli_iller", []))
    iller = g["iller"]
    if iller and set(iller) <= engelli:
        return "İl tercihin dışında: " + ", ".join(iller)
    return None


def egitim_elemesi(tum):
    """Yalnızca lise/ön lisans mezunlarına açık ilan mı? (Kullanıcının lisans KPSS'i var.)"""
    if re.search(r"\bon ?lisans|\blise\b|ortaogretim", tum) and not re.search(r"(?<!on)(?<!on )lisans", tum):
        return "Lise/ön lisans düzeyi (sende lisans KPSS var)"
    return None


def profilsiz_elemeler(baslik, govde, g, ayar):
    """Kişisel bilgi gerektirmeyen kesin elemeler (ilanlar.json'a yazılır)."""
    tum = fold(baslik + " " + (govde or "")[:12000])
    return [e for e in (kpss_yili_elemesi(g, ayar), il_elemesi(g, ayar), egitim_elemesi(tum)) if e]


def profil_elemeleri(g, profil, yil):
    """Puan ve yaşa bağlı eleme nedenleri. Profil yoksa boş döner."""
    if not profil:
        return []
    nedenler = []
    puan = profil.get("puanlar") or {}
    turler = g["puan_turleri"]
    if turler and puan:
        # İlan lisans/önlisans/ortaöğretim için ayrı puan türleri sayabilir (P3, P93, P94);
        # yalnızca sahip olduklarımıza bakılır.
        sahip = {t: mn for t, mn in turler.items() if t in puan}
        if not sahip:
            nedenler.append("KPSS" + "/".join(sorted(turler)) + " puan türü isteniyor (sende yok)")
        elif all(mn is not None and puan[t] < mn for t, mn in sahip.items()):
            t, mn = next(iter(sahip.items()))
            nedenler.append(f"KPSS{t} en az {mn:g} isteniyor (sende {puan[t]:g})")
    if g["yas_siniri"] and profil.get("dogum_yili"):
        en_kucuk_yas = yil - int(profil["dogum_yili"]) - 1
        if en_kucuk_yas >= g["yas_siniri"]:
            nedenler.append(f"Yaş sınırı {g['yas_siniri']} (sen {en_kucuk_yas}+)")
    return nedenler


def degerlendir(baslik, govde, ayar, profil=None, yil=2026, resmi=False):
    """Tam hat: ilgisizse None, değilse {seviye, nedenler, gercekler, elendi, elendi_profil}."""
    s = sinifla(baslik, govde, resmi)
    if s is None:
        return None
    seviye, nedenler = s
    tum = fold(baslik + " " + (govde or "")[:12000])
    g = gercekler(baslik + " " + (govde or "")[:12000], tum)
    return {
        "seviye": seviye,
        "nedenler": nedenler,
        "gercekler": g,
        "elendi": profilsiz_elemeler(baslik, govde, g, ayar),
        "elendi_profil": profil_elemeleri(g, profil, yil),
    }
