# Ableton Reactive - per-track audio analysis shared by the Script CHOPs in /project1/ableton_reactive.
# Pure Python + numpy (no TouchDesigner imports), so it can be tested outside TD: python test_analysis.py
# build_ableton_reactive.py loads this file into the text DAT 'analysis'; edit it there or here and rebuild.
import math
import re
import numpy as np

BANDS = (('low', 20.0, 250.0), ('mid', 250.0, 2000.0), ('high', 2000.0, 12000.0))
FEATURES = ('level', 'low', 'mid', 'high')
OUT = FEATURES + ('pulse', 'hits')       # channels per track: tN_level, tN_low, ... tN_hits
FFT_N = 2048                             # audio-rate inputs: band analysis window (~43 ms at 48 kHz)
NOISE_FLOOR = 0.02                       # autogain never boosts anything quieter than this
PEAK_TAU = 8.0                           # seconds for the autogain peak to fall back
MIN_GAP = 0.09                           # seconds between two onsets (caps at ~11 hits/s)
LEVEL_TOKENS = {'level', 'meter', 'left', 'right', 'peak', 'rms'}


def _tokens(name):
    return [t for t in re.split(r'[^a-z0-9]+', name.lower()) if t]


def _coef(dt, tau):
    return 1.0 if tau <= 1e-6 else 1.0 - math.exp(-dt / tau)


def levels_from_audio(x, rate):
    """Mono audio window -> {'level','low','mid','high'} as linear RMS (a full-scale sine gives ~0.707)."""
    x = np.asarray(x, dtype=np.float64).ravel()
    n = x.size
    if n < 32:
        return None
    win = np.hanning(n)
    spec = np.abs(np.fft.rfft(x * win)) * 2.0 / win.sum()      # bin magnitude ~ sine amplitude
    freqs = np.fft.rfftfreq(n, 1.0 / rate)
    out = {'level': float(np.sqrt(np.mean(x * x)))}
    for name, lo, hi in BANDS:
        m = (freqs >= lo) & (freqs < hi)
        # /1.5 undoes the Hann window's energy spread over neighbouring bins, /2 turns amplitude^2 into RMS^2
        out[name] = float(np.sqrt(np.sum(spec[m] ** 2) / 1.5 / 2.0)) if m.any() else 0.0
    return out


def levels_from_control(chans):
    """Control-rate channels [(name, value)], e.g. a TDAbleton abletonLevel output -> features dict.
    Channels whose name has a 'low' / 'mid' / 'high' token become bands (TDA Audio Analyzer rack);
    otherwise the level is the loudest meter-like channel ('level', 'meter', 'left', ... in its name, else any
    channel) and the bands copy it (single TDA Level device, or abletonTrack's output_meter_* channels).
    All-negative values that dip below -1.5 are taken as dB."""
    chans = [(n, float(v)) for n, v in chans]
    if not chans:
        return None
    if all(v <= 0 for _, v in chans) and any(v < -1.5 for _, v in chans):
        chans = [(n, 10.0 ** (v / 20.0)) for n, v in chans]
    chans = [(_tokens(n), max(0.0, v)) for n, v in chans]
    out = {}
    for band in ('low', 'mid', 'high'):
        vals = [v for t, v in chans if band in t]
        if vals:
            out[band] = max(vals)
    banded = set(t for t in ('low', 'mid', 'high') if t in out)
    rest = [(t, v) for t, v in chans if not banded.intersection(t)]
    meters = [v for t, v in rest if LEVEL_TOKENS.intersection(t)]   # abletonTrack also sends volume, pan...
    rest = meters or [v for t, v in rest]
    out['level'] = max(rest) if rest else max(out.values())
    for band in ('low', 'mid', 'high'):
        out.setdefault(band, out['level'])
    return out


def test_signal(track, t, bpm):
    """Synthetic per-track features so the template moves with nothing connected.
    Track 1 four-on-the-floor kick, 2 off-beat bass, 3 sixteenth hats, 4 slow pad, then repeats."""
    beat = t * bpm / 60.0
    kind = (track - 1) % 4
    if kind == 0:
        e = math.exp(-(beat % 1.0) * 7.0)
        return {'level': e, 'low': e, 'mid': 0.25 * e, 'high': 0.05 * e}
    if kind == 1:
        e = math.exp(-((beat + 0.5) % 1.0) * 4.0) * (0.65 + 0.35 * math.sin(beat * math.pi / 8.0))
        return {'level': e, 'low': 0.8 * e, 'mid': e, 'high': 0.2 * e}
    if kind == 2:
        e = math.exp(-((beat * 4.0) % 1.0) * 10.0) * (1.0 if int(beat * 4.0) % 4 != 3 else 0.4)
        return {'level': 0.6 * e, 'low': 0.0, 'mid': 0.2 * e, 'high': e}
    e = 0.5 + 0.5 * math.sin(beat * math.pi / 16.0)
    return {'level': e, 'low': 0.3 * e, 'mid': e, 'high': 0.5 * e}


class TrackAnalyzer:
    """Smooths one track's features, normalises them to ~0..1 and detects onsets (pulse + hit counter)."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.value = dict.fromkeys(FEATURES, 0.0)
        self.peak = NOISE_FLOOR
        self.slow = 0.0
        self.pulse = 0.0
        self.hits = 0
        self.since_hit = 1e9
        self.armed = True
        self.buf = np.zeros(0)

    def audio(self, samples, rate):
        """Features from this frame's audio slice ((channels, n) or (n,)); bands use the last FFT_N samples."""
        x = np.asarray(samples, dtype=np.float64)
        if x.ndim == 2:
            x = x.mean(axis=0) if x.shape[0] else np.zeros(0)
        if x.size == 0:
            return None
        self.buf = np.concatenate((self.buf, x))[-FFT_N:]
        out = levels_from_audio(self.buf, rate)
        if out is not None:
            out['level'] = float(np.sqrt(np.mean(x * x)))      # level reacts to this frame only
        return out

    def update(self, raw, dt, gain=1.0, attack=0.02, release=0.25, threshold=0.15, decay=0.3,
               autogain=True, onset='level'):
        """raw: features dict or None (no input: everything falls back to 0). Returns {OUT name: value}."""
        dt = min(max(dt, 1e-4), 0.25)
        out = {}
        for k in FEATURES:
            target = gain * (raw.get(k, 0.0) if raw else 0.0)
            v = self.value[k]
            v += (target - v) * _coef(dt, attack if target > v else release)
            self.value[k] = v
        # one gain per track (not per band) so the low/mid/high balance survives normalisation
        self.peak = max(max(self.value.values()), NOISE_FLOOR, self.peak * math.exp(-dt / PEAK_TAU))
        scale = 1.0 / self.peak if autogain else 1.0
        for k in FEATURES:
            out[k] = min(1.0, max(0.0, self.value[k] * scale))
        o = out.get(onset, out['level'])
        self.slow += (o - self.slow) * _coef(dt, 0.4)
        self.since_hit += dt
        self.pulse *= math.exp(-dt / max(decay, 1e-3))
        rise = o - self.slow
        if rise < 0.5 * threshold:
            self.armed = True                             # hysteresis: one hit per rise, not one per frame
        elif rise > threshold and self.armed and self.since_hit > MIN_GAP:
            self.armed = False
            self.pulse = 1.0
            self.hits += 1
            self.since_hit = 0.0
        out['pulse'] = self.pulse
        out['hits'] = float(self.hits)
        return out


class Clock:
    """Song position: from TDAbleton's abletonSong (song/info/tempo, /play, /time in beats) or an internal clock."""

    def __init__(self):
        self.beat = 0.0

    def update(self, chans, dt, bpm):
        named = {}
        for n, v in chans or ():
            t = _tokens(n)
            if t:
                named[t[-1]] = float(v)
        play = named.get('play', 1.0) >= 0.5
        bpm = named.get('tempo', bpm)
        if 'time' in named:
            self.beat = named['time']
        elif play:
            self.beat += min(max(dt, 0.0), 0.25) * bpm / 60.0
        return {'bpm': bpm, 'play': float(play), 'beat': self.beat,
                'phase': self.beat % 1.0, 'barphase': (self.beat % 4.0) / 4.0}
