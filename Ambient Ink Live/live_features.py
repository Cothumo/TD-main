# Ambient Ink Live - live audio features for the ink (no look-ahead, frame by frame).
# Runs live in TouchDesigner (the Script CHOP 'live' in /project1/ink_track2, fed by the TDA_Audio_Analyzer levels of
# Ableton track "2", an audio input or a test file); analyze_file() runs the same code over a file offline. Input per frame: the RMS level of the whole signal and of three bands (low < 150 Hz, mid 150-2000 Hz,
# high > 2000 Hz), on any scale (linear amplitude, or dB with db=True): everything is normalised on the fly against
# the recent past, so quiet and loud sources both work.
# Output per frame: the same columns the ink simulation reads from an offline analysis (ink_analyze.py):
#   level low mid high bright onset kick kick_id kick_age hat hat_id arc build phase spin cur_x cur_y,
#   vib (unstable sound: the level flickers), dis / dis_id (sharp accents: strong spikes of the whole flux),
#   presence (0..1: is anything coming in at all - rises in 0.1 s, falls over 2.5 s after the input stops),
#   6 puff slots p<s>_age/_x/_y/_ang/_str (ink erupts on low hits and swells), 4 spray slots s<k>_... (hi-hats).
import math
import random

NSLOT, NSPRAY = 6, 4
COLUMNS = ['level', 'low', 'mid', 'high', 'bright', 'onset', 'kick', 'kick_id', 'kick_age', 'hat', 'hat_id', 'hat_age',
           'arc', 'build', 'phase', 'spin', 'cur_x', 'cur_y', 'vib', 'dis', 'dis_id', 'presence'] \
    + ['p%d_%s' % (s, k) for s in range(NSLOT) for k in ('age', 'x', 'y', 'ang', 'str')] \
    + ['s%d_%s' % (s, k) for s in range(NSPRAY) for k in ('age', 'x', 'y', 'ang', 'str')]
# portrait currents: rising, up-left, up-right, sinking, steeply up-right (the current turns every CURRENT_TURN s)
CURRENTS = [0.5 * math.pi, 0.5 * math.pi + 0.5, 0.5 * math.pi - 0.5, -0.5 * math.pi, 0.5 * math.pi - 0.25]


class Norm:
    """0..1 over the R dB below the loudest recent peak. The peak memory starts at a typical reference level, jumps
    to every louder peak and sinks 3 dB per minute, but never more than 12 dB below the reference - so a quiet
    passage stays quiet instead of being turned up (use Gain on ink_visual for a much quieter source)."""
    def __init__(self, ref_db, rng_db=24.0):
        self.ref, self.hi, self.rng = ref_db, ref_db, rng_db

    def __call__(self, db, dt):
        self.hi = max(db, self.hi - 0.05 * dt, self.ref - 12.0)
        return min(1.0, max(0.0, (db - (self.hi - self.rng)) / self.rng))


class Hits:
    """Online peak picker on a flux signal: adaptive mean/deviation, a minimum gap, a decaying envelope."""
    def __init__(self, gap, tau, thr=1.6):
        self.gap, self.tau, self.thr = gap, tau, thr
        self.m, self.v, self.prev = 0.0, 1e-4, 0.0
        self.env, self.id, self.age = 0.0, 0, 10.0

    def __call__(self, flux, dt):
        z = (flux - self.m) / math.sqrt(self.v + 1e-9)
        k = 1.0 - math.exp(-dt / 2.0)                       # ~2 s statistics
        self.m += (flux - self.m) * k
        self.v += ((flux - self.m) ** 2 - self.v) * k
        self.env *= math.exp(-dt / self.tau)
        self.age += dt
        hit = 0.0
        if z > self.thr and self.prev <= self.thr * 1.15 and self.age >= self.gap:
            hit = min(1.0, 0.35 + 0.65 * (z - self.thr) / 3.0)
            self.env = max(self.env, hit); self.id += 1; self.age = 0.0
        self.prev = z
        return hit


def _ar(v, x, dt, attack, release):
    k = 1.0 - math.exp(-dt / max(attack if x > v else release, 1e-6))
    v = v + (x - v) * k
    return v if abs(v) > 1e-12 else 0.0          # no denormals: TouchDesigner turns them into inf in a CHOP


class LiveFeatures:
    PUFF_GAP, PUFF_MAX_GAP = 3.0, 12.0          # seconds between ink eruptions: at least / at most
    SPRAY_GAP = 0.25
    CURRENT_TURN = 30.0

    def __init__(self, seed=7):
        self.rnd = random.Random(seed)
        self.nl, self.nb = Norm(-9.0), [Norm(-9.0), Norm(-14.0), Norm(-30.0)]     # full, low, mid, high
        self.kicks, self.hats = Hits(0.30, 0.45), Hits(0.15, 0.18, 1.8)
        self.accents = Hits(0.16, 0.09, 3.0)
        self.jit = 0.0
        self.prev_db = None
        self.f = {c: 0.0 for c in COLUMNS}
        for s in range(NSLOT):
            self.f['p%d_age' % s] = 999.0
        for s in range(NSPRAY):
            self.f['s%d_age' % s] = 999.0
        self.f['kick_age'] = self.f['hat_age'] = 10.0
        self.t = 0.0
        self.arc_raw, self.arc_max, self.arc_hist = 0.0, 1e-3, []
        self.sm_level, self.sm_hist = 0.0, []
        self.flux_m, self.flux_v = 0.0, 1e-4
        self.npuff, self.last_puff, self.nspray, self.last_spray = 0, -99.0, 0, -99.0
        self.cur_a = CURRENTS[0]

    def step(self, level, low, mid, high, dt=1.0 / 30.0, db=False, gain_db=0.0):
        f = self.f
        dt = dt if (isinstance(dt, (int, float)) and math.isfinite(dt) and dt > 0) else 1.0 / 60.0
        self.t += dt
        # never let a bad input value (NaN / inf from a disconnected source) into the state
        level, low, mid, high = [v if math.isfinite(v) else 0.0 for v in (float(level), float(low), float(mid), float(high))]
        if not db:
            level, low, mid, high = [min(abs(v), 10.0) for v in (level, low, mid, high)]
        else:
            level, low, mid, high = [min(max(v, -140.0), 20.0) for v in (level, low, mid, high)]
        if db:
            dbs = [level, low, mid, high]
        else:
            dbs = [20.0 * math.log10(max(abs(v), 1e-7)) for v in (level, low, mid, high)]
        dbs = [d + gain_db for d in dbs]
        silent = dbs[0] < -70.0
        # presence: the input is there at all (raw level above -60 dB, before the gain), with a slow fade-out
        f['presence'] = _ar(f['presence'], 1.0 if dbs[0] - gain_db > -60.0 else 0.0, dt, 0.1, 2.5)
        # levels (same follower times as the offline analysis)
        f['level'] = _ar(f['level'], 0.0 if silent else self.nl(dbs[0], dt), dt, 0.03, 0.35)
        bn = [0.0 if silent else n(d, dt) for n, d in zip(self.nb, dbs[1:])]
        f['low'] = _ar(f['low'], bn[0], dt, 0.02, 0.30)
        f['mid'] = _ar(f['mid'], bn[1], dt, 0.03, 0.30)
        f['high'] = _ar(f['high'], bn[2], dt, 0.01, 0.20)
        eb = [10.0 ** (d / 10.0) for d in dbs[1:]]
        f['bright'] = _ar(f['bright'], min(1.0, 3.0 * eb[2] / (sum(eb) + 1e-12)), dt, 0.3, 0.8)
        # flux: rise of each band in dB (positive only)
        if self.prev_db is None:
            self.prev_db = dbs[:]
        fl = [max(0.0, a - b) for a, b in zip(dbs, self.prev_db)]
        self.prev_db = [p + (d - p) * 0.6 for p, d in zip(self.prev_db, dbs)]
        if silent:
            fl = [0.0] * 4
        flux_all = fl[1] + fl[2] + fl[3]
        k = 1.0 - math.exp(-dt / 4.0)
        self.flux_m += (flux_all - self.flux_m) * k
        self.flux_v += ((flux_all - self.flux_m) ** 2 - self.flux_v) * k
        on = min(1.0, max(0.0, (flux_all - self.flux_m) / (2.5 * math.sqrt(self.flux_v) + 1e-6)))
        f['onset'] = _ar(f['onset'], on, dt, 0.01, 0.25)
        kh = self.kicks(fl[1], dt)
        hh = self.hats(fl[3], dt)
        f['kick'], f['kick_id'], f['kick_age'] = self.kicks.env, float(self.kicks.id), self.kicks.age
        f['hat'], f['hat_id'], f['hat_age'] = self.hats.env, float(self.hats.id), self.hats.age
        self.accents(flux_all, dt)
        f['dis'], f['dis_id'] = self.accents.env, float(self.accents.id)
        # unstable sound: how much the band levels flicker frame to frame, against its own recent norm
        jit = abs(fl[2] - fl[1]) + abs(fl[3] - fl[2]) if not silent else 0.0
        self.jit = _ar(self.jit, jit, dt, 0.05, 0.6)
        vib = (self.jit - self.flux_m * 0.8) / (2.0 * math.sqrt(self.flux_v) + 1e-6) + 0.35 * f['onset'] * f['high']
        f['vib'] = _ar(f['vib'], min(1.0, max(0.0, vib)), dt, 0.08, 0.5)
        # the slow arc of the music and whether it is building up
        self.arc_raw = _ar(self.arc_raw, 0.55 * f['level'] + 0.30 * f['low'] + 0.15 * f['mid'], dt, 3.0, 3.0)
        self.arc_max = max(self.arc_raw, self.arc_max * math.exp(-dt / 60.0), 1e-3)
        f['arc'] = min(1.0, self.arc_raw / self.arc_max)
        self.arc_hist.append(f['arc'])
        back = int(round(2.0 / dt))
        if len(self.arc_hist) > back:
            self.arc_hist.pop(0)
        f['build'] = _ar(f['build'], min(1.0, max(0.0, (f['arc'] - self.arc_hist[0]) * 4.0)), dt, 0.5, 1.0)
        f['phase'] += (0.30 + 0.80 * f['level'] + 0.40 * f['onset'] + 0.60 * f['kick']) * dt
        f['spin'] += (0.03 + 0.10 * f['arc'] + 0.05 * f['mid']) * dt
        # the current turns slowly every CURRENT_TURN seconds (no sections are known live)
        target = CURRENTS[int(self.t / self.CURRENT_TURN) % len(CURRENTS)]
        d = math.atan2(math.sin(target - self.cur_a), math.cos(target - self.cur_a))
        self.cur_a += d * (1.0 - math.exp(-dt / 4.0))
        f['cur_x'], f['cur_y'] = math.cos(self.cur_a), math.sin(self.cur_a)
        # ink eruptions: low hits first, then swells (rise of the level over the last second) and onsets
        self.sm_level = _ar(self.sm_level, f['level'], dt, 0.25, 0.25)
        self.sm_hist.append(self.sm_level)
        if len(self.sm_hist) > int(round(1.0 / dt)):
            self.sm_hist.pop(0)
        rise = max(0.0, self.sm_level - self.sm_hist[0])
        score = min(1.0, rise * 4.0) + 0.4 * f['onset'] + 0.9 * kh
        since = self.t - self.last_puff
        if (since >= self.PUFF_GAP and score > 0.55 and not silent) or (since >= self.PUFF_MAX_GAP and f['level'] > 0.05):
            self._puff(min(1.0, 0.45 + 0.55 * min(score, 1.2) / 1.2))
        for s in range(NSLOT):
            if f['p%d_age' % s] < 999.0:
                f['p%d_age' % s] += dt
        # sprays: hi-hat hits
        if hh > 0 and self.t - self.last_spray >= self.SPRAY_GAP:
            self._spray(0.4 + 0.6 * max(hh, f['high'] * 0.6))
        for s in range(NSPRAY):
            if f['s%d_age' % s] < 999.0:
                f['s%d_age' % s] += dt
        # no denormals (TouchDesigner turns them into inf in a CHOP); and if anything ever went non-finite, start afresh
        for k_, v_ in f.items():
            if abs(v_) < 1e-12:
                f[k_] = 0.0
        self.kicks.env = self.kicks.env if self.kicks.env > 1e-12 else 0.0
        self.hats.env = self.hats.env if self.hats.env > 1e-12 else 0.0
        self.accents.env = self.accents.env if self.accents.env > 1e-12 else 0.0
        if self.flux_v < 1e-12: self.flux_v = 1e-12
        if abs(self.flux_m) < 1e-12: self.flux_m = 0.0
        if abs(self.arc_raw) < 1e-12: self.arc_raw = 0.0
        if abs(self.sm_level) < 1e-12: self.sm_level = 0.0
        if abs(self.jit) < 1e-12: self.jit = 0.0
        for h_ in (self.kicks, self.hats, self.accents):
            if h_.v < 1e-12: h_.v = 1e-12
            if abs(h_.m) < 1e-12: h_.m = 0.0
        if not all(math.isfinite(v) for v in f.values()):
            self.__init__()
            return self.f
        return f

    def _puff(self, st):
        f, r = self.f, self.rnd
        s = self.npuff % NSLOT
        cx, cy = f['cur_x'], f['cur_y']
        f['p%d_age' % s] = 0.0
        f['p%d_x' % s] = max(-0.85, min(0.85, (r.random() - 0.5) * 1.7 - cx * 0.2))     # anywhere in the water
        f['p%d_y' % s] = max(-0.85, min(0.85, (r.random() - 0.5) * 1.7 - cy * 0.2))
        f['p%d_ang' % s] = math.atan2(cy, cx) + (r.random() - 0.5) * 1.1
        f['p%d_str' % s] = st * 0.75                  # softer eruptions: the ink blooms rather than bursts
        self.npuff += 1; self.last_puff = self.t

    def _spray(self, st):
        f, r = self.f, self.rnd
        s = self.nspray % NSPRAY
        f['s%d_age' % s] = 0.0
        f['s%d_x' % s] = (r.random() - 0.5) * 1.3
        f['s%d_y' % s] = (r.random() - 0.5) * 1.3
        f['s%d_ang' % s] = r.random() * 2.0 * math.pi
        f['s%d_str' % s] = st
        self.nspray += 1; self.last_spray = self.t


# ---------------------------------------------------------------- offline: the same bands as the TouchDesigner chain
def biquad(x, kind, f0, sr, q=0.7071):
    """RBJ biquad (2nd order): 'lp', 'hp', 'bp' - as an Audio Filter CHOP with 12 dB/oct roll-off."""
    import numpy as np
    w = 2 * math.pi * f0 / sr; c, s = math.cos(w), math.sin(w); al = s / (2 * q)
    if kind == 'lp':
        b = [(1 - c) / 2, 1 - c, (1 - c) / 2]
    elif kind == 'hp':
        b = [(1 + c) / 2, -(1 + c), (1 + c) / 2]
    else:
        b = [al, 0.0, -al]
    a = [1 + al, -2 * c, 1 - al]
    try:
        from scipy.signal import lfilter
        return lfilter(np.array(b) / a[0], np.array(a) / a[0], x)
    except ImportError:
        y = np.zeros_like(x); x1 = x2 = y1 = y2 = 0.0
        b0, b1, b2, a1, a2 = b[0] / a[0], b[1] / a[0], b[2] / a[0], a[1] / a[0], a[2] / a[0]
        for i, v in enumerate(x):
            o = b0 * v + b1 * x1 + b2 * x2 - a1 * y1 - a2 * y2
            x2, x1, y2, y1 = x1, v, y1, o; y[i] = o
        return y


BANDS = [('lp', 150.0, 0.7071), ('bp', 550.0, 0.45), ('hp', 2000.0, 0.7071)]    # low / mid (150-2000 Hz) / high


def band_levels(x, sr, fps=30):
    """Per-frame RMS of the whole signal and of the three bands (n_frames x 4)."""
    import numpy as np
    sigs = [x] + [biquad(x, k, f0, sr, q) for k, f0, q in BANDS]
    n = int(len(x) / sr * fps)
    out = np.zeros((n, 4))
    for i in range(n):
        a, b = int(i * sr / fps), int((i + 1) * sr / fps)
        for j, s in enumerate(sigs):
            out[i, j] = math.sqrt(float(np.mean(s[a:b] ** 2)) + 1e-14)
    return out


def analyze_file(wav, tsv, fps=30):
    """Offline: run the live features over an audio file -> <tsv> with the ink columns (one row per frame)."""
    import numpy as np
    import wave as wv
    w = wv.open(wav, 'rb'); sr, ch, sw, n = w.getframerate(), w.getnchannels(), w.getsampwidth(), w.getnframes()
    x = np.frombuffer(w.readframes(n), '<i2').astype(np.float64).reshape(-1, ch).mean(axis=1) / 32768.0
    w.close()
    assert sw == 2, '16-bit wav expected'
    L = band_levels(x, sr, fps)
    lf = LiveFeatures()
    with open(tsv, 'w') as fo:
        fo.write('\t'.join(['frame', 'time'] + COLUMNS) + '\n')
        for i, row in enumerate(L):
            f = lf.step(*row, dt=1.0 / fps)
            fo.write('%d\t%.4f\t' % (i, i / float(fps)) + '\t'.join('%.4f' % f[c] for c in COLUMNS) + '\n')
    return tsv, {'frames': len(L), 'kicks': lf.kicks.id, 'hats': lf.hats.id, 'puffs': lf.npuff, 'sprays': lf.nspray}


if __name__ == '__main__':
    import sys
    print(analyze_file(sys.argv[1], sys.argv[2]))
