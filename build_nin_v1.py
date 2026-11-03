# NIN Stage - builds /project1/nin_stage in the open TDA project: the last layer, after ink_layer.
# Inspired by Nine Inch Nails' Peel It Back tour (projection on stacked translucent scrims, live delayed copies of the
# picture - "Copy of A"). No flashes. Run in the Textport (Alt+T):
#   exec(open(project.folder + '/build_nin.py').read())
# It points the 'viewer' window at /project1/nin_stage/OUT. Running it again rebuilds only nin_stage.
import os
D = (globals().get('NIN_DIR') or project.folder).replace('\\', '/').rstrip('/')       # the project's folder (Ableton Reactive)
SRC = globals().get('NIN_SOURCE', '/project1/ink_layer/OUT')
TRACKS = globals().get('NIN_TRACKS', '/project1/ableton_reactive/TRACKS')
nin_log = []

def sp(n, name, val=None, expr=None):
    try:
        p = getattr(n.par, name)
        if expr is not None: p.expr = expr
        else: p.val = val
    except Exception as e:
        nin_log.append('%s.%s: %s' % (n.name, name, e))

def mk(ty, name, x, y):
    n = C.create(ty, name); n.nodeX, n.nodeY = x, y; return n

old = op('/project1/nin_stage')
if old: old.destroy()
C = op('/project1').create(baseCOMP, 'nin_stage')
C.nodeX, C.nodeY = 1100, -600
C.color = (0.15, 0.15, 0.15)

PARS = [  # name, default, min, max, help
    ('Amount', 1.0, 0, 1, 'the whole NIN stage layer (0 = the picture as it comes from ink_layer)'),
    ('Scrim', 0.8, 0, 1, 'stacked scrims: where the front picture is empty, softer, smaller copies further back show through'),
    ('Ripple', 0.8, 0, 3, 'the front scrim moves in the air: slow folds bend the picture (more when track 1 is loud)'),
    ('Parallax', 1.0, 0, 3, 'the scrims behind sway slowly and are pushed by the hits of track 1'),
    ('Ghost', 0.6, 0, 2, "Pepper's ghost: a faint, slightly larger reflection of the scene floating in front"),
    ('Echo', 0.8, 0, 1, 'Copy of A: on strong hits the scene leaves three delayed copies that drift out and fade'),
    ('Echospacing', 9, 2, 40, 'frames between the picture and the first delayed copy (at 60 fps: 9 = 0.15 s); the second is 2.5x as old'),
    ('Echodrift', 1.0, 0, 3, 'how far the copies drift away'),
    ('Echodecay', 1.4, 0.2, 5, 'seconds the copies take to fade'),
    ('Echogap', 1.2, 0.1, 8, 'at least this many seconds between two echoes (only strong hits trigger one)'),
    ('Echothreshold', 0.5, 0, 1, 'how strong a hit must be to leave copies'),
    ('Haze', 0.4, 0, 1, 'a soft haze lifts the darks a little (in the dark, negative picture)'),
    ('Darkness', 0.5, 0, 1, 'the edges of the frame sink into darkness'),
]
pg = C.appendCustomPage('NIN')
for nm, dv, lo, hi, hlp in PARS:
    q = pg.appendFloat(nm)[0]; q.default = dv; q.val = dv; q.normMin = lo; q.normMax = hi; q.help = hlp
q = pg.appendCHOP('Tracks')[0]; q.default = TRACKS; q.val = TRACKS
q = pg.appendMenu('Hitsource', label='Hits From')[0]
q.menuNames = ['track1', 'track2', 'reactive']
q.menuLabels = ['Track 1 (its output meter, own hit detection)', 'Track 2 (the ink layer\'s hits)', 'ableton_reactive t1_pulse']
q.default = 'track1'; q.val = 'track1'
q = pg.appendCHOP('Track1meter', label='Track 1 Meter')[0]; q.default = '/project1/track_A_transient/out1'; q.val = q.default

src = mk(selectTOP, 'src', -600, 100); sp(src, 'top', SRC)
cache = mk(cacheTOP, 'cache', -400, 100)
cache.inputConnectors[0].connect(src)
sp(cache, 'cachesize', 128); sp(cache, 'active', True)
cs = []
for k, mult in ((1, 1.0), (2, 2.5)):
    s = mk(cacheselectTOP, 'copy%d' % k, -200, 250 - 150 * k)
    sp(s, 'cachetop', 'cache')
    sp(s, 'index', expr="-min(127, int(parent().par.Echospacing * %r))" % mult)
    cs.append(s)

# echo trigger: a strong hit of track 1 (ableton_reactive TRACKS t1_pulse) starts an envelope and picks a drift direction
tick = mk(constantCHOP, 'tick', -600, -300); tick.par.name0 = 'frame'; tick.par.value0.expr = 'absTime.frame'
ech = mk(scriptCHOP, 'echo', -400, -300)
ech.inputConnectors[0].connect(tick)
try:
    for dd in list(ech.docked): dd.destroy()
except Exception:
    pass
cb = mk(textDAT, 'echo_callbacks', -400, -450)
cb.text = '''# echo trigger: a strong hit starts an envelope and picks a new drift direction
import math, random
def _fin(v):
    try:
        v = float(v)
    except Exception:
        return 0.0
    return v if (v == v and abs(v) < 1e30 and abs(v) > 1e-12) else 0.0
def onSetupParameters(scriptOp):
    return
def onCook(scriptOp):
    p = scriptOp.parent(); st = scriptOp.storage
    now = absTime.seconds
    dt = min(0.1, max(1.0 / 240, now - st.get('t', now - 1.0 / 60))); st['t'] = now
    src = p.par.Hitsource.eval()
    hit, pulse, level = False, 0.0, 0.0
    if src == 'track1':
        # own hit detection on the output meter of track 1 (the same live analysis as the ink layer)
        if st.get('lf') is None:
            st['lf'] = mod('/project1/ink_track2/live_features').LiveFeatures()
        c = p.par.Track1meter.eval()
        vals = [_fin(ch.eval()) for ch in c.chans() if 'output_meter_left' in ch.name or 'output_meter_right' in ch.name] if c is not None else []
        v0 = sum(vals) / len(vals) if vals else 0.0
        f = st['lf'].step(v0, v0, v0, v0, dt=dt)
        pulse, level = max(f['kick'], f['onset']), f['level']
        kid = f['kick_id']; hit = kid != st.get('kid', kid) and f['kick'] >= p.par.Echothreshold.eval(); st['kid'] = kid
    elif src == 'track2':
        L = op('/project1/ink_track2/live')
        if L is not None and L['kick'] is not None:
            pulse, level = max(_fin(L['kick']), _fin(L['onset'])), _fin(L['level'])
            kid = _fin(L['kick_id']); hit = kid != st.get('kid', kid) and _fin(L['kick']) >= p.par.Echothreshold.eval(); st['kid'] = kid
    else:
        T = p.par.Tracks.eval()
        pulse = _fin(T['t1_pulse']) if T is not None and T['t1_pulse'] is not None else 0.0
        level = _fin(T['t1_level']) if T is not None and T['t1_level'] is not None else 0.0
        hit = pulse >= p.par.Echothreshold.eval() and st.get('prev', 0.0) < p.par.Echothreshold.eval()
        st['prev'] = pulse
    last = st.get('last', -99.0)
    if hit and now - last >= p.par.Echogap.eval():
        st['last'] = last = now
        a = random.uniform(0, 2 * math.pi)
        st['dir'] = (math.cos(a), math.sin(a))
    age = now - last
    env = math.exp(-age / max(p.par.Echodecay.eval(), 0.05)) if age < 30 else 0.0
    d = st.get('dir', (1.0, 0.0))
    scriptOp.clear(); scriptOp.numSamples = 1
    for k, v in (('env', env), ('age', min(age, 30.0)), ('dx', d[0]), ('dy', d[1]), ('pulse', pulse), ('level', level)):
        scriptOp.appendChan(k)[0] = _fin(v) if k not in ('dx', 'dy') else v
    return
'''
sp(ech, 'callbacks', 'echo_callbacks')

px = mk(textDAT, 'stage_pixel', 0, 300); px.text = open(D + '/nin_stage.glsl').read()
g = mk(glslTOP, 'stage', 0, 100)
# inputs 0..2: the picture, then the two delayed copies (connected one per frame: the TOP adds its connectors as it cooks)
def _nin_connect(i):
    _g = op('/project1/nin_stage/stage')
    _s = op('/project1/nin_stage/' + ['src', 'copy1', 'copy2'][i])
    _g.inputConnectors[min(i, len(_g.inputConnectors) - 1)].connect(_s)
g.inputConnectors[0].connect(src)
run(_nin_connect, 1, delayFrames=2)
run(_nin_connect, 2, delayFrames=4)
sp(g, 'pixeldat', 'stage_pixel')
try:
    for dd in list(g.docked):
        if dd.name != 'stage_pixel': dd.destroy()
except Exception:
    pass
try:
    g.par.outputresolution = 'useinput'
except Exception as e:
    nin_log.append('res: %s' % e)
E = "op('echo')['%s']"
U = [('uA', ['absTime.seconds % 10000', 'parent().par.Amount', E % 'level', E % 'pulse']),
     ('uS', ['parent().par.Scrim', 'parent().par.Ripple', 'parent().par.Parallax', 'parent().par.Ghost']),
     ('uE', ['parent().par.Echo', E % 'env', E % 'age', 'parent().par.Echodrift']),
     ('uD', [E % 'dx', E % 'dy', 'parent().par.Haze', 'parent().par.Darkness'])]
g.seq.vec.numBlocks = len(U)
for i, (nm, ex) in enumerate(U):
    getattr(g.par, 'vec%dname' % i).val = nm
    for ch, e in zip('xyzw', ex):
        getattr(g.par, 'vec%dvalue%s' % (i, ch)).expr = e
o = mk(nullTOP, 'OUT', 200, 100); o.inputConnectors[0].connect(g); o.viewer = True
oo = mk(outTOP, 'out1', 400, 100); oo.inputConnectors[0].connect(o)
sp(C, 'opviewer', 'OUT')
v = op('/project1/viewer')
if v is not None:
    sp(v, 'winop', C.path + '/OUT')
C.save(D + '/nin_stage.tox')
print('NIN stage built: %s (from %s), viewer -> %s/OUT | log %s | errors %s' % (
    C.path, SRC, C.path, nin_log or 'none', [(n.name, n.errors()) for n in C.children if n.errors()] or 'none'))
