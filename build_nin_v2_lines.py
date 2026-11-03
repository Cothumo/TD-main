# NIN Stage - builds /project1/nin_stage in the open TDA project: the last layer, after ink_layer.
# Inspired by Nine Inch Nails' Peel It Back tour (projection on stacked translucent scrims, live delayed copies of the
# picture - "Copy of A", the linear light rig - sheets of light and turning blades in haze, and a show in four acts).
# No flashes. Run in the Textport (Alt+T):
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
    ('Lines', 0.6, 0, 1.5, 'sheets of light: the linear rig seen in haze (grey light in the dark, thin shadows on white)'),
    ('Linemode', 0.0, 0, 1, '0 = thin sheets rising from the floor (as high as the music is loud), 1 = blades turning about the centre'),
    ('Linecount', 9, 2, 24, 'how many sheets of light'),
    ('Linewidth', 0.004, 0.001, 0.02, 'how thin the sheets / blades are'),
    ('Chasespeed', 1.0, 0, 4, 'speed of the soft chase running along the sheets (a hit speeds it up)'),
    ('Bladespeed', 1.0, 0, 4, 'how fast the blades turn (a hit nudges them on)'),
    ('Actfade', 6.0, 0.5, 30, 'seconds the scene takes to move from one act to the next'),
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
pa = C.appendCustomPage('Acts')
q = pa.appendMenu('Act', label='Act')[0]
q.menuNames = ['1', '2', '3', '4']; q.menuLabels = ['1 Panels (sparse, soft)', '2 Projection (layered depth)', '3 Club (turning blades)', '4 Wall (sheets, echoes)']
q.default = '1'; q.val = '1'
for k in range(1, 5):
    pa.appendPulse('Act%d' % k, label='Go to Act %d' % k)
q = pa.appendMenu('Actsource', label='Acts Follow')[0]
q.menuNames = ['manual', 'ableton']; q.menuLabels = ['Manual (the Act menu / buttons)', 'Ableton scene launches (scene 1 = act 1, ... 5 = act 1 again)']
q.default = 'manual'; q.val = 'manual'
q = pa.appendToggle('Actsenabled', label='Acts Drive The Look')[0]; q.default = True; q.val = True

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
    st['phase'] = (st.get('phase', 0.0) + dt * p.par.Chasespeed.eval() * (0.6 + 3.0 * env)) % 6283.0
    st['ang'] = (st.get('ang', 0.0) + dt * p.par.Bladespeed.eval() * (0.12 + 0.5 * env)) % 6.2832
    st['sl'] = st.get('sl', 0.0) + (level - st.get('sl', 0.0)) * (1.0 - math.exp(-dt / 0.6))
    scriptOp.clear(); scriptOp.numSamples = 1
    for k, v in (('env', env), ('age', min(age, 30.0)), ('dx', d[0]), ('dy', d[1]), ('pulse', pulse), ('level', level),
                 ('phase', st['phase']), ('ang', st['ang']), ('slevel', st['sl'])):
        scriptOp.appendChan(k)[0] = _fin(v) if k not in ('dx', 'dy', 'phase', 'ang') else v
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
     ('uD', [E % 'dx', E % 'dy', 'parent().par.Haze', 'parent().par.Darkness']),
     ('uL', ['parent().par.Lines', 'parent().par.Linemode', E % 'phase', E % 'slevel']),
     ('uK', ['parent().par.Linecount', 'parent().par.Linewidth', E % 'ang', '0'])]
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
# ---- acts: four looks for the whole scene (NIN Stage + the ink layer), crossfaded over Actfade seconds
acts = mk(textDAT, 'acts', 400, -300)
acts.text = """# the four acts: the values each one moves the scene to (NIN page of nin_stage, Layeramount of ink_track2)
ACTS = {
    '1': {'Scrim': 0.5, 'Ripple': 0.6, 'Parallax': 0.6, 'Ghost': 0.3, 'Echo': 0.35, 'Haze': 0.3, 'Darkness': 0.35,
          'Lines': 0.25, 'Linemode': 0.0, 'Linecount': 6, 'ink:Layeramount': 0.35},
    '2': {'Scrim': 1.0, 'Ripple': 1.0, 'Parallax': 1.6, 'Ghost': 1.0, 'Echo': 0.6, 'Haze': 0.5, 'Darkness': 0.5,
          'Lines': 0.0, 'Linemode': 0.0, 'Linecount': 9, 'ink:Layeramount': 0.5},
    '3': {'Scrim': 0.4, 'Ripple': 0.4, 'Parallax': 0.8, 'Ghost': 0.4, 'Echo': 0.9, 'Haze': 0.8, 'Darkness': 0.75,
          'Lines': 0.9, 'Linemode': 1.0, 'Linecount': 9, 'ink:Layeramount': 0.4},
    '4': {'Scrim': 0.8, 'Ripple': 0.8, 'Parallax': 1.2, 'Ghost': 0.6, 'Echo': 1.0, 'Haze': 0.7, 'Darkness': 0.45,
          'Lines': 1.0, 'Linemode': 0.0, 'Linecount': 16, 'ink:Layeramount': 0.6},
}
INK = '/project1/ink_track2'
import math

def frame(dt):
    C = me.parent()
    if not C.par.Actsenabled.eval():
        return
    st = C.storage
    if C.par.Actsource.eval() == 'ableton':
        s = op('/project1/abletonSong1/abletonSong')
        o = s.op('out1') if s is not None else None
        if o is not None and o['song/info/last_started_scene'] is not None:
            sc = int(o['song/info/last_started_scene'].eval())
            if sc >= 0 and sc != st.get('scene', -1):
                st['scene'] = sc
                C.par.Act = str(sc % 4 + 1)
    tgt = ACTS.get(C.par.Act.eval(), {})
    k = 1.0 - math.exp(-dt / max(C.par.Actfade.eval(), 0.05))
    for name, v in tgt.items():
        if name.startswith('ink:'):
            o = op(INK); par = getattr(o.par, name[4:], None) if o is not None else None
        else:
            par = getattr(C.par, name, None)
        if par is None:
            continue
        cur = par.eval()
        nv = cur + (v - cur) * k
        par.val = round(nv) if name == 'Linecount' and abs(nv - v) < 0.5 else nv
"""
ax = mk(executeDAT, 'acts_exec', 600, -300)
ax.text = "_t = [None]\ndef onFrameStart(frame):\n\tnow = absTime.seconds\n\tdt = min(0.1, now - _t[0]) if _t[0] is not None else 1.0 / 60\n\t_t[0] = now\n\top('acts').module.frame(dt)\n\treturn\n"
sp(ax, 'framestart', True); sp(ax, 'active', True)
pe = mk(parameterexecuteDAT, 'acts_pulses', 600, -450)
pe.text = "def onPulse(par):\n\tif par.name.startswith('Act') and par.name[3:].isdigit():\n\t\tpar.owner.par.Act = par.name[3:]\n\treturn\n"
sp(pe, 'op', '..'); sp(pe, 'pars', 'Act1 Act2 Act3 Act4'); sp(pe, 'onpulse', True); sp(pe, 'valuechange', False)

C.save(D + '/nin_stage.tox')
print('NIN stage built: %s (from %s), viewer -> %s/OUT | log %s | errors %s' % (
    C.path, SRC, C.path, nin_log or 'none', [(n.name, n.errors()) for n in C.children if n.errors()] or 'none'))
