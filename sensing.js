// Dokunmasız Algılama — paylaşılan algılama motoru.
// index.html (yön+spektrum gösterimi) ve tiklama.html (temassız tıklama demosu)
// aynı motoru kullanır; algoritma tek yerde değişir, ikisi de güncel kalır.
'use strict';

// Ultrasonik Doppler tabanlı yaklaşma/uzaklaşma algılayıcı.
// onUpdate her karede {bias, confidence, spectrumData, binForFreq} ile çağrılır:
//   bias        : -1..+1  (negatif=uzaklaşma, pozitif=yaklaşma, ~0=hareketsiz/gürültü altı)
//   confidence  : 0..1    (sinyalin taban gürültüden ne kadar ayrıştığı)
class TouchlessSensor {
  constructor({ carrierFreq = 19000, onUpdate, onStatus } = {}) {
    this.carrierFreq = carrierFreq;
    this.onUpdate = onUpdate || (() => {});
    this.onStatus = onStatus || (() => {});
    this.actx = null;
    this.analyser = null;
    this.oscillator = null;
    this.noiseFloor = null;
    this.dirSmooth = 0;
    this.running = false;
  }

  setCarrierFreq(f) {
    this.carrierFreq = f;
    if (this.oscillator) this.oscillator.frequency.setValueAtTime(f, this.actx.currentTime);
  }

  async start() {
    this.actx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 44100 });

    this.oscillator = this.actx.createOscillator();
    this.oscillator.type = 'sine';
    this.oscillator.frequency.value = this.carrierFreq;
    const gain = this.actx.createGain();
    gain.gain.value = 0.35; // fazla yükseltme distorsiyon + mikrofon clipping yaratır
    this.oscillator.connect(gain);
    gain.connect(this.actx.destination);
    this.oscillator.start();

    const stream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: false, noiseSuppression: false, autoGainControl: false }
    });
    const micSource = this.actx.createMediaStreamSource(stream);
    this.analyser = this.actx.createAnalyser();
    this.analyser.fftSize = 16384; // yüksek frekans çözünürlüğü: 44100/16384 ≈ 2.7 Hz/bin
    this.analyser.smoothingTimeConstant = 0.2;
    micSource.connect(this.analyser);

    this.running = true;
    await this._calibrate();
  }

  stop() {
    this.running = false;
    if (this.oscillator) { try { this.oscillator.stop(); } catch (e) {} }
    if (this.actx) { try { this.actx.close(); } catch (e) {} }
  }

  _binForFreq(f) {
    const nyquist = this.actx.sampleRate / 2;
    return Math.round(f / nyquist * this.analyser.frequencyBinCount);
  }

  // Taşıyıcının hemen etrafındaki bandın enerjisini ölçer (dB -> lineer güç ortalaması).
  _bandEnergy(data, loHz, hiHz) {
    const lo = this._binForFreq(loHz), hi = this._binForFreq(hiHz);
    let sum = 0, n = 0;
    for (let i = lo; i <= hi; i++) { sum += Math.pow(10, data[i] / 10); n++; }
    return n ? sum / n : 0;
  }

  _calibrate() {
    return new Promise((resolve) => {
      this.onStatus('calibrating');
      const data = new Float32Array(this.analyser.frequencyBinCount);
      const samples = [];
      const t0 = performance.now();
      const step = () => {
        if (!this.running) return;
        this.analyser.getFloatFrequencyData(data);
        const above = this._bandEnergy(data, this.carrierFreq + 30, this.carrierFreq + 300);
        const below = this._bandEnergy(data, this.carrierFreq - 300, this.carrierFreq - 30);
        samples.push(above + below);
        this._lastSpectrum = data.slice();
        if (performance.now() - t0 < 1000) {
          requestAnimationFrame(step);
        } else {
          const avg = samples.reduce((a, b) => a + b, 0) / samples.length;
          this.noiseFloor = avg * 1.8; // %80 pay: hareketin taban gürültüden belirgin ayrışması için
          this.onStatus('ready');
          this._loop();
          resolve();
        }
      };
      step();
    });
  }

  _loop() {
    if (!this.running) return;
    const data = new Float32Array(this.analyser.frequencyBinCount);
    this.analyser.getFloatFrequencyData(data);

    const above = this._bandEnergy(data, this.carrierFreq + 30, this.carrierFreq + 300); // yaklaşma
    const below = this._bandEnergy(data, this.carrierFreq - 300, this.carrierFreq - 30); // uzaklaşma
    const total = above + below;

    let bias = 0, confidence = 0;
    if (total > this.noiseFloor) {
      const rawBias = (above - below) / total; // -1..+1
      this.dirSmooth += (rawBias - this.dirSmooth) * 0.3;
      bias = this.dirSmooth;
      confidence = Math.min(1, total / (this.noiseFloor * 4));
    } else {
      this.dirSmooth *= 0.7;
      bias = this.dirSmooth;
      confidence = 0;
    }

    this.onUpdate({ bias, confidence, spectrumData: data, binForFreq: (f) => this._binForFreq(f), carrierFreq: this.carrierFreq });
    requestAnimationFrame(() => this._loop());
  }
}

// Ortak spektrum çizim yardımcısı (canvas üzerine taşıyıcı etrafındaki enerjiyi çizer).
function drawSpectrum(ctx, canvas, spectrumData, binForFreq, carrierFreq) {
  const w = canvas.width, h = canvas.height;
  ctx.fillStyle = '#0e151c';
  ctx.fillRect(0, 0, w, h);
  const lo = binForFreq(carrierFreq - 400), hi = binForFreq(carrierFreq + 400);
  const n = hi - lo;
  ctx.strokeStyle = '#4fd1a5';
  ctx.lineWidth = 2;
  ctx.beginPath();
  for (let i = 0; i < n; i++) {
    const db = spectrumData[lo + i];
    const norm = Math.max(0, Math.min(1, (db + 100) / 70));
    const x = i / n * w, y = h - norm * h;
    if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
  }
  ctx.stroke();
  ctx.strokeStyle = 'rgba(255,255,255,.25)';
  ctx.lineWidth = 1;
  ctx.beginPath();
  ctx.moveTo(w / 2, 0); ctx.lineTo(w / 2, h);
  ctx.stroke();
}
