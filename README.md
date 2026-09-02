# Dokunmasız Algılama

Kamera veya hazır yapay zeka modeli kullanmadan, telefonun kendi hoparlör +
mikrofon donanımıyla temassız el hareketi algılama teknolojisi.

## Fikir

Telefon, insan kulağının duyamayacağı sabit bir ton çalar (~19 kHz).
El bu sese yaklaşıp uzaklaştıkça, yansıyan sesin frekansı **Doppler etkisiyle**
çok küçük bir miktar kayar. Bu kaymayı mikrofonla yakalayıp FFT (Fourier
analizi) ile ölçerek elin yönünü (yaklaşıyor/uzaklaşıyor) ve hızını çıkarmak
mümkün.

Bu, Google'ın Project Soli'sindeki gibi özel bir radar çipi ya da kapasitif
ekran donanımına erişim gerektirmez — sadece her telefonda zaten bulunan
hoparlör + mikrofon ve saf sinyal işleme matematiği.

## Durum

- [x] `poc.html` — kanıt-of-concept: taşıyıcı ton + Doppler bant enerjisi
      analiziyle yaklaşma/uzaklaşma yönü tespiti, canlı spektrum görselleştirme
- [ ] Kalibrasyon/gürültü bağışıklığını iyileştirme
- [ ] Gerçek hareket sınıflandırma (yön ötesi: hız, jest tipi)
- [ ] SDK/kütüphane olarak paketleme

## Test etme

`poc.html` dosyasını bir telefon tarayıcısında aç (GitHub Pages üzerinden
yayınlanınca), mikrofon iznini ver, telefonu masaya koy, 1 saniye sessiz kal
(kalibrasyon), sonra elini telefonun üzerinde yaklaştır/uzaklaştır.

