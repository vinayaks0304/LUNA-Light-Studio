"""Optional live audio capture for LUNA's host microphone mode.

The device can listen to a physical microphone or a PipeWire monitor source,
if that monitor is exposed by PortAudio. No recording is saved to disk.
"""
import time

try:
    import numpy as np
    import sounddevice as sd
except (ImportError, OSError):
    np = None
    sd = None


def input_devices():
    if sd is None:
        return []
    return [(index, str(item['name'])) for index, item in enumerate(sd.query_devices())
            if int(item['max_input_channels']) >= 1]


class AudioCapture:
    def __init__(self, callback):
        self.callback = callback
        self.stream = None
        self.last_emit = 0.0
        self.active = False

    def start(self, device=None):
        if sd is None or np is None:
            raise RuntimeError('Install sounddevice and numpy to use PC audio input.')
        self.stop()
        info = sd.query_devices(device, 'input')
        rate = int(info['default_samplerate'])
        if rate <= 0:
            rate = 44100
        self.last_emit = 0.0
        self.stream = sd.InputStream(device=device, samplerate=rate, channels=1,
                                     dtype='float32', blocksize=2048,
                                     callback=lambda data, frames, timing, status:
                                         self._on_samples(data, rate))
        try:
            self.stream.start()
            self.active = True
        except Exception:
            self.stream.close()
            self.stream = None
            raise

    def _on_samples(self, data, rate):
        now = time.monotonic()
        if not self.active or now - self.last_emit < 0.16:
            return
        self.last_emit = now
        samples = data[:, 0].copy()
        rms = float(np.sqrt(np.mean(samples * samples)))
        if rms < 0.00001:
            self.callback(0.0, 0.0)
            return
        window = np.hanning(len(samples))
        spectrum = np.abs(np.fft.rfft(samples * window))
        freqs = np.fft.rfftfreq(len(samples), 1.0 / rate)
        valid = (freqs >= 60) & (freqs <= 2500)
        peak = float(freqs[valid][np.argmax(spectrum[valid])]) if valid.any() else 0.0
        self.callback(rms, peak)

    def stop(self):
        self.active = False
        if self.stream is not None:
            try:
                self.stream.stop()
            finally:
                self.stream.close()
                self.stream = None
