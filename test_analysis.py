# Checks analysis.py outside TouchDesigner: python test_analysis.py  (needs numpy)
import math
import numpy as np
import analysis as A

RATE = 48000


def sine(freq, amp=1.0, n=A.FFT_N):
    return amp * np.sin(2 * np.pi * freq * np.arange(n) / RATE)


def test_bands_follow_frequency():
    for freq, band in ((80, 'low'), (900, 'mid'), (5000, 'high')):
        f = A.levels_from_audio(sine(freq), RATE)
        assert abs(f[band] - 0.707) < 0.08, (freq, f)
        assert all(f[b] < 0.1 for b in ('low', 'mid', 'high') if b != band), (freq, f)
        assert abs(f['level'] - 0.707) < 0.01, f


def test_control_rack_and_single_device():
    rack = A.levels_from_control([('Drums/Low/TDA_Level/level', 0.8), ('Drums/Mid/TDA_Level/level', 0.3),
                                  ('Drums/High/TDA_Level/level', 0.1)])
    assert rack == {'low': 0.8, 'mid': 0.3, 'high': 0.1, 'level': 0.8}, rack
    single = A.levels_from_control([('Slow Pad/level_left', 0.4), ('Slow Pad/level_right', 0.6)])
    assert single == {'level': 0.6, 'low': 0.6, 'mid': 0.6, 'high': 0.6}, single   # 'slow' is not 'low'
    track = A.levels_from_control([('tracks/2/mixer_device/volume', 0.85), ('tracks/2/output_meter_left', 0.2),
                                   ('tracks/2/output_meter_right', 0.3), ('tracks/2/output_meter_level', 0.3)])
    assert track['level'] == 0.3, track                      # abletonTrack: volume is not a level
    db = A.levels_from_control([('level', -6.0)])
    assert abs(db['level'] - 0.501) < 0.01, db
    assert A.levels_from_control([]) is None


def test_onsets_on_kick_pattern():
    an, dt, bpm, hits = A.TrackAnalyzer(), 1 / 60.0, 120.0, []
    for f in range(60 * 8):                                  # 8 s = 16 beats
        out = an.update(A.test_signal(1, f * dt, bpm), dt)
        assert all(0.0 <= out[k] <= 1.0 for k in A.FEATURES + ('pulse',)), out
    assert 14 <= out['hits'] <= 16, out['hits']              # first beat or so is spent warming up
    for f in range(60 * 3):                                  # input disappears -> everything decays
        out = an.update(None, dt)
    assert out['level'] < 0.05 and out['pulse'] < 0.01, out


def test_audio_slices_accumulate():
    an = A.TrackAnalyzer()
    x = sine(80, 0.5, 4000)
    for i in range(0, 4000, 800):                            # 60 fps slices of a 48 kHz device
        f = an.audio(x[i:i + 800][None, :], RATE)
    assert an.buf.size == A.FFT_N and f['low'] > 0.3 and f['high'] < 0.05, f


def test_clock():
    c = A.Clock()
    out = c.update([], 0.25, 120.0)
    assert out['beat'] == 0.5 and out['phase'] == 0.5
    out = c.update([('song/info/tempo', 100.0), ('song/info/play', 1.0), ('song/info/time', 6.5)], 1 / 60, 120.0)
    assert out['bpm'] == 100.0 and out['phase'] == 0.5 and out['barphase'] == 0.625, out
    out = c.update([('song/info/play', 0.0)], 1.0, 120.0)
    assert out['play'] == 0.0 and out['beat'] == 6.5


if __name__ == '__main__':
    for name, fn in sorted(globals().items()):
        if name.startswith('test_'):
            fn()
            print('ok', name)
