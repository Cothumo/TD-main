# Ableton Reactive - default template: visuals driven live by two (or more) Ableton tracks at once.
# Builds /project1/ableton_reactive. Either
#   - drag this file into the TouchDesigner network, right-click the new Text DAT > Run Script, or
#   - in the Textport (Alt+T): exec(open(r'C:/path/to/Ableton Reactive/build_ableton_reactive.py').read())
# analysis.py must sit next to this file. Anything the build could not set is printed in ar_log.
#
# Sources (custom parameter 'Source' on the component):
#   Test signal  - built-in kick / bass / hats / pad patterns, nothing else needed
#   TDAbleton    - point Track1, Track2, ... at abletonLevel (or abletonTrack) components and Song at abletonSong
#   Audio device - Ableton track outputs routed to separate channels of an audio interface / virtual device
# Every track becomes channels tN_level, tN_low, tN_mid, tN_high (0..1), tN_pulse (onset envelope), tN_hits (count)
# in the CHOP 'TRACKS', plus bpm, play, beat, phase, barphase. The visual uses t1 (rhythm) and t2 (texture/colour).
import os

def _folder():
    # where this script lives: AR_DIR if you set it, the File of the Text DAT it was dragged in as, or the default
    cands = [globals().get('AR_DIR')]
    try:
        f = me.par.file.eval()
        if f:
            cands.append(os.path.dirname(f if os.path.isabs(f) else os.path.join(project.folder, f)))
    except Exception:
        pass
    cands.append('C:/Users/cothu/Documents/TD Visuals/Ableton Reactive')
    for c in cands:
        if c and os.path.isfile(os.path.join(c, 'analysis.py')):
            return c.replace('\\', '/')
    raise RuntimeError('analysis.py not found next to build_ableton_reactive.py (tried %s); '
                       'set AR_DIR = r"<folder>" in the Textport and run again' % [c for c in cands if c])
D = _folder()
TRACKS = 2                    # number of track analyzers; extra tracks show up in TRACKS for your own mappings
W, H = 1280, 720              # non-commercial licence caps every TOP at 1280 px
LOAD_TDABLETON = True         # try to load abletonLevel / abletonSong from the Palette and wire them up
ar_log = []

def trypar(n, name, val=None, expr=None):
    try:
        p = getattr(n.par, name)
        if expr is not None: p.expr = expr
        else: p.val = val
        return True
    except Exception as e:
        ar_log.append('%s.%s: %s' % (n.name, name, e)); return False

def setmenu(n, name, *keys):
    try:
        p = getattr(n.par, name)
        for k in keys:
            for m in p.menuNames:
                if k == m.lower() or k in m.lower():
                    p.val = m; return m
        ar_log.append('%s.%s no match in %s' % (n.name, name, p.menuNames[:12]))
    except Exception as e:
        ar_log.append('%s.%s: %s' % (n.name, name, e))

def anypar(n, names, val=None, expr=None):
    # parameter names that differ between operators / builds: set the first one that exists
    for nm in names:
        if hasattr(n.par, nm):
            return trypar(n, nm, val, expr)
    ar_log.append('%s: none of %s' % (n.name, names)); return False

def mk(parent, ty, name, x, y):
    n = parent.create(ty, name); n.nodeX, n.nodeY = x, y; return n

def wire(dst, *srcs):
    for i, s in enumerate(srcs):
        dst.inputConnectors[i].connect(s)
    return dst

def res(n):
    setmenu(n, 'outputresolution', 'custom'); trypar(n, 'resolutionw', W); trypar(n, 'resolutionh', H)

def ch(name):
    return "op('TRACKS')['%s']" % name

old = op('/project1/ableton_reactive')
if old: old.destroy()
C = op('/project1').create(baseCOMP, 'ableton_reactive')
C.nodeX, C.nodeY = 0, -900

# ---- controls
pg = C.appendCustomPage('Ableton')
p = pg.appendMenu('Source', label='Source')[0]
p.menuNames = ['test', 'tdableton', 'audio']; p.menuLabels = ['Test signal', 'TDAbleton', 'Audio device']; p.val = 'test'
p = pg.appendFloat('Bpm', label='BPM (test / no Song)')[0]; p.default = 124; p.val = 124; p.normMin = 60; p.normMax = 180
for i in range(1, TRACKS + 1):
    pg.appendOP('Track%d' % i, label='Track %d (abletonLevel)' % i)
for i in range(1, TRACKS + 1):
    p = pg.appendStr('Track%daudio' % i, label='Track %d audio chans' % i)[0]
    p.default = p.val = 'chan%d chan%d' % (2 * i - 1, 2 * i)
pg.appendOP('Song', label='Song (abletonSong)')
pg = C.appendCustomPage('React')
for nm, dv, hi, lb in [('Gain', 1.0, 4.0, 'Gain'), ('Attack', 0.02, 0.5, 'Attack (s)'), ('Release', 0.25, 2.0, 'Release (s)'),
                       ('Threshold', 0.15, 0.6, 'Onset threshold'), ('Decay', 0.3, 2.0, 'Pulse decay (s)')]:
    q = pg.appendFloat(nm, label=lb)[0]; q.default = dv; q.val = dv; q.normMax = hi
q = pg.appendToggle('Autogain', label='Auto gain')[0]; q.default = True; q.val = True
q = pg.appendMenu('Onsetband', label='Onset from')[0]
q.menuNames = ['level', 'low', 'mid', 'high']; q.menuLabels = ['Level', 'Low', 'Mid', 'High']; q.val = 'level'
pg = C.appendCustomPage('Look')
for nm, dv, hi, lb in [('Track1amount', 1.0, 2.0, 'Track 1 amount'), ('Track2amount', 1.0, 2.0, 'Track 2 amount'),
                       ('Feedback', 0.9, 0.99, 'Feedback'), ('Huespeed', 0.03, 0.3, 'Hue speed')]:
    q = pg.appendFloat(nm, label=lb)[0]; q.default = dv; q.val = dv; q.normMax = hi

# ---- python: analysis (tested outside TD, see test_analysis.py), callbacks, expression helpers
an = mk(C, textDAT, 'analysis', -1200, 400); an.text = open(D + '/analysis.py').read()
util = mk(C, textDAT, 'util', -1000, 400)
util.text = '''# helpers for parameter expressions in this component
import colorsys

def source(par):
    """OP parameter -> CHOP path: the CHOP itself, or the Out CHOP of a COMP such as abletonLevel."""
    o = par.eval()
    if o is None: return ''
    if o.isCHOP: return o.path
    if o.isCOMP:
        outs = sorted(o.findChildren(type=outCHOP, depth=1), key=lambda c: c.name)
        if outs: return outs[0].path
    return ''

def tint(k, hue, sat=0.65):
    return colorsys.hsv_to_rgb(hue % 1.0, sat, 1.0)[k]
'''
cb = mk(C, textDAT, 'analyze_callbacks', -800, 400)
cb.text = '''# shared by t1_analyze, t2_analyze, ...: one TrackAnalyzer per track, state lives while this DAT is unchanged
_an, _last, _out = {}, {}, {}

def onSetupParameters(scriptOp):
    return

def onPulse(par):
    return

def onCook(scriptOp):
    C = scriptOp.parent(); P = C.par
    A = C.op('analysis').module
    i = int(scriptOp.name[1:].split('_')[0])
    an = _an.setdefault(i, A.TrackAnalyzer())
    now = absTime.seconds
    dt = now - _last.get(i, now - 1.0 / 60)
    if dt > 0 or i not in _out:
        _last[i] = now
        raw, inp = None, (scriptOp.inputs[0] if scriptOp.inputs else None)
        if P.Source.eval() == 'test':
            raw = A.test_signal(i, now, P.Bpm.eval())
        elif inp is not None and inp.numChans:
            if inp.rate > 2000:
                raw = an.audio(inp.numpyArray(), inp.rate)
            else:
                raw = A.levels_from_control([(c.name, c.eval()) for c in inp.chans()])
        _out[i] = an.update(raw, dt, gain=P.Gain.eval(), attack=P.Attack.eval(), release=P.Release.eval(),
                            threshold=P.Threshold.eval(), decay=P.Decay.eval(), autogain=P.Autogain.eval(),
                            onset=P.Onsetband.eval())
    scriptOp.clear()
    scriptOp.numSamples = 1
    try: scriptOp.rate = project.cookRate
    except Exception: pass
    for k in A.OUT:
        scriptOp.appendChan('t%d_%s' % (i, k))[0] = _out[i][k]
'''
scb = mk(C, textDAT, 'song_callbacks', -800, 250)
scb.text = '''# song position from abletonSong (Source = TDAbleton and Song set), else an internal clock at BPM
_clock, _last = [], []

def onSetupParameters(scriptOp):
    return

def onPulse(par):
    return

def onCook(scriptOp):
    C = scriptOp.parent(); A = C.op('analysis').module
    if not _clock: _clock.append(A.Clock()); _last.append(absTime.seconds)
    now = absTime.seconds; dt = now - _last[0]; _last[0] = now
    inp = scriptOp.inputs[0] if scriptOp.inputs else None
    chans = [(c.name, c.eval()) for c in inp.chans()] if inp is not None and C.par.Source.eval() == 'tdableton' else []
    out = _clock[0].update(chans, dt, C.par.Bpm.eval())
    scriptOp.clear()
    scriptOp.numSamples = 1
    try: scriptOp.rate = project.cookRate
    except Exception: pass
    for k, v in out.items():
        scriptOp.appendChan(k)[0] = v
'''

def script(name, callbacks, x, y):
    n = mk(C, scriptCHOP, name, x, y)
    for d in list(n.docked): d.destroy()          # use the shared callbacks DAT instead of a generated one
    trypar(n, 'callbacks', callbacks.name)
    return n

# ---- inputs -> per-track analysis
tick = mk(C, constantCHOP, 'tick', -800, -100)    # changes every frame, so the analyzers cook every frame
trypar(tick, 'name0', 'frame'); trypar(tick, 'value0', expr='absTime.frame')
ain = mk(C, audiodeviceinCHOP, 'audio_in', -1200, -300)   # pick the device on this node
trypar(ain, 'active', expr="parent().par.Source.eval() == 'audio'")
merge = mk(C, mergeCHOP, 'merge', -200, 0)
for i in range(1, TRACKS + 1):
    y = 300 - i * 200
    sel = mk(C, selectCHOP, 't%d_ableton' % i, -1000, y)
    anypar(sel, ['chop', 'chops'], expr="op('util').module.source(parent().par.Track%d)" % i)
    aud = wire(mk(C, selectCHOP, 't%d_audio' % i, -1000, y - 80), ain)
    trypar(aud, 'channames', expr='parent().par.Track%daudio.eval()' % i)
    sw = wire(mk(C, switchCHOP, 't%d_switch' % i, -800, y), sel, aud)
    trypar(sw, 'index', expr="1 if parent().par.Source.eval() == 'audio' else 0")
    sc = wire(script('t%d_analyze' % i, cb, -600, y), sw, tick)
    merge.inputConnectors[i - 1].connect(sc)
ssel = mk(C, selectCHOP, 'song_ableton', -1000, -500)
anypar(ssel, ['chop', 'chops'], expr="op('util').module.source(parent().par.Song)")
song = wire(script('song', scb, -600, -500), ssel, tick)
merge.inputConnectors[TRACKS].connect(song)
T = wire(mk(C, nullCHOP, 'TRACKS', 0, 0), merge); T.viewer = True
scope = wire(mk(C, selectCHOP, 'scope_sel', 200, 0), T)
trypar(scope, 'channames', 't*_level t*_pulse')
wire(mk(C, trailCHOP, 'scope', 400, 0), scope).viewer = True

# ---- visual: track 1 punches (ring size, zoom, flash), track 2 paints (noise, rotation, warp, colour)
A1, A2 = 'parent().par.Track1amount', 'parent().par.Track2amount'
ring = mk(C, circleTOP, 'ring', 0, -400); res(ring)
for nm in ('radiusx', 'radiusy'):
    trypar(ring, nm, expr='0.05 + 0.22 * %s * %s' % (ch('t1_pulse'), A1))
trypar(ring, 'softness', 0.15)
noise = mk(C, noiseTOP, 'noise', 0, -550); res(noise)
trypar(noise, 'monochrome', False)
trypar(noise, 'period', expr='1.6 - 0.9 * %s * %s' % (ch('t2_low'), A2))
trypar(noise, 'tz', expr='absTime.seconds * 0.15 + 0.4 * %s' % ch('t2_level'))
nlev = wire(mk(C, levelTOP, 'noise_level', 200, -550), noise)
trypar(nlev, 'brightness1', expr='0.08 + 0.5 * %s * %s' % (ch('t2_level'), A2))
src = wire(mk(C, compositeTOP, 'src', 400, -450), ring, nlev); setmenu(src, 'operand', 'add')
tc = mk(C, constantTOP, 'tint_color', 400, -650)
hue = 'absTime.seconds * parent().par.Huespeed + 0.35 * %s' % ch('t2_mid')
for k, nm in enumerate(('colorr', 'colorg', 'colorb')):
    trypar(tc, nm, expr="op('util').module.tint(%d, %s)" % (k, hue))
tint = wire(mk(C, compositeTOP, 'tint', 600, -450), src, tc); setmenu(tint, 'operand', 'multiply')
fb = wire(mk(C, feedbackTOP, 'feedback', 600, -650), tint); trypar(fb, 'top', 'mix')
fx = wire(mk(C, transformTOP, 'feedback_move', 800, -650), fb)
for nm in ('sx', 'sy'):
    trypar(fx, nm, expr='1.004 + 0.035 * %s * %s' % (ch('t1_pulse'), A1))
trypar(fx, 'rotate', expr='0.2 + 2.5 * %s * %s' % (ch('t2_mid'), A2))
ff = wire(mk(C, levelTOP, 'feedback_fade', 1000, -650), fx); trypar(ff, 'brightness1', expr='parent().par.Feedback')
mix = wire(mk(C, compositeTOP, 'mix', 1000, -450), tint, ff); setmenu(mix, 'operand', 'add')
wn = mk(C, noiseTOP, 'warp_noise', 1000, -800)
setmenu(wn, 'outputresolution', 'custom'); trypar(wn, 'resolutionw', W // 2); trypar(wn, 'resolutionh', H // 2)
trypar(wn, 'monochrome', False); trypar(wn, 'tz', expr='absTime.seconds * 0.3')
warp = wire(mk(C, displaceTOP, 'warp', 1200, -450), mix, wn)
for sfx in ('x', 'y'):
    anypar(warp, ['displaceweight' + sfx, 'displaceweight' + {'x': '1', 'y': '2'}[sfx]],
           expr='0.005 + 0.06 * %s * %s' % (ch('t2_high'), A2))
flash = wire(mk(C, levelTOP, 'flash', 1400, -450), warp)
trypar(flash, 'brightness1', expr='1 + 0.6 * %s * %s' % (ch('t1_pulse'), A1))
out = wire(mk(C, nullTOP, 'OUT', 1600, -450), flash); out.viewer = True
wire(mk(C, outTOP, 'out1', 1800, -450), out)

# ---- optional: bring in TDAbleton components next to the template and point the parameters at them
_found = {}
def palette(name):
    if name in _found: return _found[name]
    roots = []
    for attr in ('samplesFolder', 'installFolder'):
        try: roots.append(getattr(app, attr))
        except Exception: pass
    for r in roots:
        for dirpath, dirs, files in os.walk(r):
            if name + '.tox' in files:
                _found[name] = os.path.join(dirpath, name + '.tox').replace('\\', '/'); return _found[name]
    _found[name] = None

if LOAD_TDABLETON:
    P1 = op('/project1')
    for i, (tox, nm) in enumerate([('abletonLevel', 'abletonLevel_t%d' % t) for t in range(1, TRACKS + 1)] + [('abletonSong', 'abletonSong1')]):
        n = P1.op(nm)
        if n is None:
            path = palette(tox)
            if path is None:
                ar_log.append('%s.tox not found in the Palette: drag it from Palette > TDAbleton yourself' % tox); continue
            try:
                n = P1.loadTox(path); n.name = nm; n.nodeX, n.nodeY = -500, -700 - i * 150
            except Exception as e:
                ar_log.append('loading %s: %s' % (tox, e)); continue
        par = 'Song' if tox == 'abletonSong' else 'Track%d' % (i + 1)
        trypar(C, par, n.path)

C.save(D + '/ableton_reactive.tox')
print('ar_log', ar_log)
print('errors', [(o.name, o.errors()) for o in C.findChildren(depth=1) if o.errors()] or 'none')
print('ableton_reactive built from %s' % D)
print('ableton_reactive built | Source = %s | set Source on the component\'s Ableton page' % C.par.Source.eval())
