"""İlan metnini çözümleyen saf mantık. Ağ yok; test edilebilir.

Bir ilan başlığı (ve varsa gövde metni) alınır, biyomedikal mühendisine uygun
olup olmadığı sınıflanır ve KPSS puanı / yaş sınırı / il gibi "gerçekler" çıkarılır.
"""
import re

GOVDE_SINIRI = 30000   # bir ilanın en çok bu kadar karakteri çözümlenir

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
                      r"\b4\s?/\s?[abd]\b|mulakat|uzman yardimci|gorevlisi|ogretim uyesi|ise alim|mufettis")
PROC = re.compile(r"\bihale|mal alim|hizmet alim|cihaz alim|arac alim|satin alim|ekipman alim|"
                  r"(?:yem|malzeme|makine|ilac|arsa|gayrimenkul|kamyon|otobus|konteyn\w*)\s+alim")
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
# Bu kadrolarda genelde yaş sınırı ve fiziki şart bulunur (başlık yaşı söylemese de uyarılır).
YAS_RISKLI = re.compile(r"zabita|itfaiye|koruma ve guvenlik|guvenlik gorevlisi|bekci|polis|jandarma|infaz")
TAHMIN = re.compile(r"ne zaman|\bmi\b|\bmu\b|\?|nasil|nereden|tarihi belli|bekleniyor|gundemi")
TOPLU_HARIC = re.compile(r"akademik|ogretim uyesi|ogretim gorevlisi|arastirma gorevlisi|profesor|docent|"
                         r"bekci|temizlik|guvenlik gorevlisi|koruma ve guvenlik|itfaiye|zabita|infaz|"
                         r"jandarma|polis|ogretmen|hemsire|gorevde yukselme|unvan degisikligi|\biskur|\bisci\b")
# Belediye ilanları (işçi, memur, sözleşmeli; her il) ve başka profillerin anahtar kelimeleri için ek sınıflama.
BELEDIYE = re.compile(r"\bbelediye")
PERSONEL_GENIS = re.compile(r"personel|memur|\bisci|sozlesmeli|\bkadro|zabita|itfaiye|temizlik gorevlisi|"
                            r"guvenlik gorevlisi|sofor|istihdam|is ilani|ise alim")
# "KPSS'siz", "KPSS şartı aranmaz", "KPSS puanı olmayanlar da başvurabilir" ...
SIZ = re.compile(r"kpss\W{0,3}siz|kpss\s+(?:sarti\s+|puani\s+)?(?:olmadan|olmayan\w*|aranmaz|aranmamakta\w*|"
                 r"aranmaksizin|sartsiz|yok)|kpss\s+sart\w*\s+(?:olmadan|aranmaz|aranmamakta\w*|"
                 r"bulunmamakta\w*|yok)")
# "Herhangi bir lisans mezunu", "her bölümden", "bölüm şartı aranmaz"
HERHANGI_LISANS = re.compile(r"herhangi bir (?:\w+ )?(?:on ?)?lisans|herhangi bir (?:fakulte|bolum|program|dal)|"
                             r"her (?:turlu )?bolum|bolum (?:sarti|siniri|kisiti) (?:aranmaz|aranmay\w*|yok|bulunmaz|bulunmay\w*)|tum lisans")
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
# "Avcılar Belediyesi", "Beylikdüzü Belediyesi" ... İstanbul'a sayılır (ilçe adı tek başına yanıltıcı olabilir:
# "tuzla", "kartal", "fatih" sıradan sözcük/özel ad olabilir, bu yüzden yalnızca "<ilçe> belediye" kalıbında).
ISTANBUL_ILCELERI = ["adalar", "arnavutkoy", "atasehir", "avcilar", "bagcilar", "bahcelievler", "bakirkoy",
                     "basaksehir", "bayrampasa", "besiktas", "beykoz", "beylikduzu", "beyoglu", "buyukcekmece",
                     "catalca", "cekmekoy", "esenler", "esenyurt", "eyupsultan", "fatih", "gaziosmanpasa",
                     "gungoren", "kadikoy", "kagithane", "kartal", "kucukcekmece", "maltepe", "pendik",
                     "sancaktepe", "sariyer", "silivri", "sultanbeyli", "sultangazi", "sile", "sisli", "tuzla",
                     "umraniye", "uskudar", "zeytinburnu"]
_ILCE_BELEDIYE_RE = re.compile(r"\b(?:%s)\s+belediye" % "|".join(ISTANBUL_ILCELERI))
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
    if _ILCE_BELEDIYE_RE.search(katlanmis) and "İstanbul" not in bulunan:
        bulunan.append("İstanbul")
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
    """Puan türü belirtilmeden geçen asgari puanlar: "65 puanla", "50-59 puanla", "65 KPSS ile", "KPSS 70 puan".
    Yıllar ("2026 KPSS", "KPSS-2026/2"), puan türü numaraları (P93) ve 4/B sayılmaz."""
    bulunan = []
    desenler = (r"(?<![\d.,/p])(\d{2})(?:\s*-\s*(\d{2}))?(?!\d)\s*(?:puan(?:la|i|in|a)?\b|kpss)",
                r"kpss\s*(?:puani\s*)?(?<![\d])(\d{2})(?:\s*-\s*(\d{2}))?(?![\d/])")
    for rx in desenler:
        for m in re.finditer(rx, tum):
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


def kpss_durumu(tum):
    """"yok" (KPSS'siz), "karma" (hem KPSS'li hem KPSS'siz), "var" (KPSS geçiyor) ya da "belirsiz"."""
    siz = bool(SIZ.search(tum))
    gerisi = SIZ.sub(" ", tum)
    var = "kpss" in gerisi
    if siz and var:
        return "karma"
    return "yok" if siz else ("var" if var else "belirsiz")


def gercekler(orijinal, tum):
    return {
        "kpss_durum": kpss_durumu(tum),
        "kpss_yillari": kpss_yillari(tum),
        "puan_turleri": puan_turleri(tum),
        "genel_puanlar": genel_puanlar(tum),
        "yas_siniri": yas_siniri(tum),
        "yas_riski": bool(YAS_RISKLI.search(tum)),
        "iller": iller_bul(orijinal, tum),
        "ehliyet": bool(re.search(r"surucu belgesi|ehliyet", tum)),
        "bolumler": branslar(tum),
    }


def sinifla(baslik, govde="", resmi=False, izlenen=False):
    """-> (seviye, nedenler) ya da None (ilgisiz).

    seviye: guclu (biyomedikal geçiyor; KPSS'li ya da KPSS'siz olduğu gercekler.kpss_durum'dan okunur) |
            olasi (mühendis ilanı / KPSS kılavuzu) | lisans (herhangi bir lisans mezunu, KPSS'li) |
            dusuk (bölüm listesinde biyomedikal yok) | toplu (toplu alım, kadro listesine bak)
    """
    t = fold(baslik)
    g = fold(govde[:GOVDE_SINIRI])
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

    if BIO.search(t):
        # Biyomedikal ilanı özel/yarı kamu kuruluşundan da olsa (özellikle KPSS'siz) gösterilir.
        ek = ["Özel sektör ilanı olabilir"] if PRIVATE.search(t) else []
        return "guclu", ["Başlıkta biyomedikal/tıp mühendisliği geçiyor"] + ek
    if PRIVATE.search(t) and "kpss" not in tum and not izlenen:
        return None         # izlenen kurumun iştirak şirketi ilanları özel sektör sayılmaz
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

    if TAHMIN.search(t) or egitim_elemesi(tum):
        return None

    if HERHANGI_LISANS.search(t) or HERHANGI_LISANS.search(g):
        # Bölüm şartı olmayan lisans alımı: biyomedikal mühendisi de başvurabilir. KPSS'siz olanlar
        # bu kategoriye alınmaz (yalnızca KPSS'li alımlar isteniyor).
        if kpss_durumu(tum) != "yok" and not TOPLU_HARIC.search(t):
            return "lisans", ["Herhangi bir lisans mezunu başvurabilir (bölüm şartı yok)"]
        return None

    if g and not MUH.search(g):
        # Gövde okundu ve mühendis hiç geçmiyor: toplu alımda mühendis kadrosu yok demektir.
        if len(g) > 800:
            return None

    if TOPLU_HARIC.search(t) or SIZ.search(t):
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
    tum = fold(baslik + " " + (govde or "")[:GOVDE_SINIRI])
    kpssiz = g["kpss_durum"] in ("yok", "karma")        # KPSS'siz yoldan da başvurulabiliyorsa KPSS yılı eleme nedeni olamaz
    return [e for e in (None if kpssiz else kpss_yili_elemesi(g, ayar), il_elemesi(g, ayar), egitim_elemesi(tum)) if e]


def profil_elemeleri(g, profil, yil):
    """Puan ve yaşa bağlı eleme nedenleri. Profil yoksa boş döner."""
    if not profil:
        return []
    nedenler = []
    puan = profil.get("puanlar") or {}
    kpsssiz_yol = g["kpss_durum"] in ("yok", "karma")      # KPSS'siz da başvurulabiliyorsa puan eleme nedeni olamaz
    turler = {} if kpsssiz_yol else g["puan_turleri"]
    if turler and puan:
        # İlan lisans/önlisans/ortaöğretim için ayrı puan türleri sayabilir (P3, P93, P94);
        # yalnızca sahip olduklarımıza bakılır.
        sahip = {t: mn for t, mn in turler.items() if t in puan}
        if not sahip:
            nedenler.append("KPSS" + "/".join(sorted(turler)) + " puan türü isteniyor (sende yok)")
        elif all(mn is not None and puan[t] < mn for t, mn in sahip.items()):
            t, mn = next(iter(sahip.items()))
            nedenler.append(f"KPSS{t} en az {mn:g} isteniyor (sende {puan[t]:g})")
    if not turler and not kpsssiz_yol and g["genel_puanlar"] and puan:
        en, alt = max(puan.values()), min(g["genel_puanlar"])      # "KPSS 60-70": en düşük kadro eşiği 60
        if en < alt:
            nedenler.append(f"KPSS en az {alt} isteniyor (en yüksek puanın {en:g})")
    if g["yas_siniri"] and profil.get("dogum_yili"):
        en_kucuk_yas = yil - int(profil["dogum_yili"]) - 1
        if en_kucuk_yas >= g["yas_siniri"]:
            nedenler.append(f"Yaş sınırı {g['yas_siniri']} (sen {en_kucuk_yas}+)")
    return nedenler


def anahtar_eslesmesi(metin, ayar):
    """ayar["profiller"][*]["anahtarlar"] (bölüm adı, görev unvanı...) metinde geçen profillerin kimlikleri.
    `metin` katlanmış (fold) olmalı."""
    bulunan = []
    for p in ayar.get("profiller", []):
        if any(fold(k) in metin for k in p.get("anahtarlar", [])):
            bulunan.append(p["id"])
    return bulunan


def sinifla_ek(baslik, govde="", ayar=None):
    """sinifla()'nın kapsamadığı ilanlar -> (seviye, nedenler) ya da None.

    profil: başka bir profilin bölüm/görev anahtarı geçiyor (başlıkta; ya da gövdede, başlıkta personel bağlamı varsa)
    belediye: belediye ilanı (işçi/memur/sözleşmeli; tüm iller)"""
    ayar = ayar or {}
    t = fold(baslik)
    tum = f"{t} {fold(govde[:GOVDE_SINIRI])}"
    if SONUC.search(t) or TAHMIN.search(t) or not HIRE.search(t):
        return None
    if PROC.search(t) and not PROC_ISTISNA.search(t):
        return None
    if anahtar_eslesmesi(t, ayar) or (PERSONEL.search(t) and anahtar_eslesmesi(tum, ayar)):
        return "profil", ["Bölümüne/mesleğine uyan anahtar kelime geçiyor"]
    if BELEDIYE.search(t) and PERSONEL_GENIS.search(t):
        return "belediye", ["Belediye ilanı: kadro listesi ve şartlar ilanda"]
    return None


def izlenen_mi(baslik, ayar):
    """Kullanıcının çalıştığı/izlediği kurum mu? Yalnızca BAŞLIĞA bakılır (gövdede tesadüfen geçmesin).

    ayar["izlenen"] = {"kurumlar": ["Avcılar", ...], "belediye_illeri": ["İstanbul"]}
    - kurumlar: başlıkta bu sözcükle başlayan bir ad geçiyorsa
    - belediye_illeri: başlıkta "belediye" geçiyor ve ilçe/il bu illerden biriyse"""
    iz = ayar.get("izlenen") or {}
    t = fold(baslik)
    for k in iz.get("kurumlar", []):
        if re.search(r"\b%s" % re.escape(fold(k)), t):
            return True
    iller = iz.get("belediye_illeri", [])
    return bool(iller and re.search(r"\bbelediye", t) and set(iller) & set(iller_bul(baslik, t)))


def degerlendir(baslik, govde, ayar, profil=None, yil=2026, resmi=False):
    """Tam hat: ilgisizse None, değilse {seviye, nedenler, gercekler, elendi, elendi_profil}."""
    izlenen = izlenen_mi(baslik, ayar)
    s = sinifla(baslik, govde, resmi, izlenen)
    ek = sinifla_ek(baslik, govde, ayar)
    if s is None or (s[0] == "toplu" and ek):
        s = ek or s          # genel "toplu alım" yerine daha özel olan (belediye / bölüme uyan) tercih edilir
    if s is None:
        return None
    seviye, nedenler = s
    tum = fold(baslik + " " + (govde or "")[:GOVDE_SINIRI])
    g = gercekler(baslik + " " + (govde or "")[:GOVDE_SINIRI], tum)
    return {
        "seviye": seviye,
        "nedenler": nedenler,
        "gercekler": g,
        "elendi": profilsiz_elemeler(baslik, govde, g, ayar),
        "elendi_profil": profil_elemeleri(g, profil, yil),
        "izlenen": izlenen,
        "profiller": anahtar_eslesmesi(tum, ayar),
    }
