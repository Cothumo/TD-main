# Stems - each element of TDA belongs to a sound.
#   Ableton track "Microcosm" (bass)  ->  the sphere's gravity (Lens, Swirl, Streaks swell with it)
#   Ableton track "2" (pads)          ->  the NIN stage's Haze and Darkness (slowly, breathing with the pads)
# The gravity follows the bass within a second or so, the haze and darkness drift after the pads over several
# seconds. Nothing pulses: both are smooth envelopes of an adaptive level (each track its own).
# Rebuild: exec(open(project.folder + '/Stems/build_stems.py').read())
import math

D = project.folder + '/Stems'
P1 = op('/project1')
TRACK = globals().get('STEMS_BASS_TRACK', 'Microcosm')        # bass -> gravity
# pads -> haze / darkness: Ableton track "2", already listened to by track_C_ink (Ambient Ink)
log = []

# 1. an abletonTrack COMP for Microcosm (a copy of track_A_transient, the way the other layers listen)
t = op('/project1/track_D_micro')
if t is None:
    src = op('/project1/track_A_transient')
    t = P1.copy(src, name='track_D_micro')
    t.nodeX, t.nodeY = -600, -1350
for n_, l_ in zip(t.par.Track.menuNames, t.par.Track.menuLabels):
    if l_ == TRACK:
        t.par.Track = n_
try:
    t.par.Enablecallbacks = False
except Exception:
    pass

# 2. the stems COMP: settings + the envelopes
old = op('/project1/stems')
if old is not None:
    old.destroy()
C = P1.create(baseCOMP, 'stems'); C.nodeX, C.nodeY = -300, -1350
pg = C.appendCustomPage('Stems')
PARS = [
    ('Gravity', 0.45, 0, 2, 'how much the bass (Microcosm) swells the sphere\'s gravity (Lens, Swirl, Streaks); 0 = off'),
    ('Gravityattack', 0.9, 0.02, 3, 'seconds the gravity takes to swell'),
    ('Gravityrelease', 3.5, 0.1, 8, 'seconds it takes to settle back'),
    ('Haze', 1.0, 0, 2, 'how much the pads (track 2) lift the haze of the NIN stage; 0 = off'),
    ('Darkness', 1.0, 0, 2, 'how much the pads (track 2) deepen the darkness at the edges; 0 = off'),
    ('Padattack', 2.5, 0.1, 15, 'seconds the haze / darkness take to rise'),
    ('Padrelease', 6.0, 0.1, 30, 'seconds they take to fall back'),
    ('Adapt', 0.03, 0.005, 0.3, 'how fast the level window follows the track (meter units per second): its quietest recent level = 0, loudest = 1'),
]
for nm, dv, lo, hi, hlp in PARS:
    q = pg.appendFloat(nm)[0]; q.default = dv; q.val = dv; q.normMin = lo; q.normMax = hi; q.help = hlp
q = pg.appendStr('Bassmeter')[0]; q.default = '/project1/track_D_micro/out1'; q.val = q.default
q.help = 'CHOP with the bass track\'s output_meter_left / output_meter_right (Microcosm)'
q = pg.appendStr('Padmeter')[0]; q.default = '/project1/track_C_ink/out1'; q.val = q.default
q.help = 'CHOP with the pad track\'s output_meter_left / output_meter_right (track 2)'

cb = C.create(textDAT, 'stems_callbacks'); cb.nodeX, cb.nodeY = -200, 0
cb.text = '''# stems: bass (Microcosm) -> the sphere's gravity, pads (track 2) -> the NIN haze / darkness
import math
_S = {}          # module state (never in op.storage - it is pickled into the .toe)

def _fin(v):
    try:
        v = float(v)
    except Exception:
        return 0.0
    if v != v or abs(v) > 1e9 or abs(v) < 1e-12:
        return 0.0
    return v

def _ar(cur, tgt, att, rel, dt):
    tau = att if tgt > cur else rel
    v = cur + (tgt - cur) * (1.0 - math.exp(-dt / max(tau, 1e-3)))
    return v if abs(v) > 1e-9 else 0.0

def _norm(key, path, ad, dt):
    # adaptive level 0..1 of a track meter (Ableton's meter is already log-scaled, 0..1): between its recent
    # quietest and loudest level, which follow it slowly (ad = meter units per second). Silence = 0.
    m = op(path)
    L = 0.0
    if m is not None:
        for ch in m.chans():                      # TDAbleton names them song/<track>/output_meter_left etc.
            if ch.name.endswith('output_meter_left') or ch.name.endswith('output_meter_right'):
                L = max(L, abs(_fin(ch[0])))
    if L < 0.2:
        return 0.0
    pk = _S.get(key + 'pk', L); fl = _S.get(key + 'fl', L)
    pk = L if L > pk else pk - ad * dt
    fl = L if L < fl else fl + ad * dt
    if pk - fl < 0.1:
        mid = 0.5 * (pk + fl); pk, fl = mid + 0.05, mid - 0.05
    _S[key + 'pk'] = pk; _S[key + 'fl'] = fl
    n = min(max((L - fl) / (pk - fl), 0.0), 1.0)
    return n * n * (3.0 - 2.0 * n)

def onSetupParameters(scriptOp):
    return

def onPulse(par):
    return

def onCook(scriptOp):
    C = scriptOp.parent(); P = C.par
    now = absTime.seconds
    if _S.get('t', 0.0) > now:
        _S.clear()
    dt = min(0.1, max(1.0 / 240, now - _S.get('t', now - 1.0 / 60))); _S['t'] = now
    ad = max(P.Adapt.eval(), 1e-4)
    nb = _norm('b', P.Bassmeter.eval(), ad, dt)
    npd = _norm('p', P.Padmeter.eval(), ad, dt)
    g = _ar(_S.get('g', 0.0), nb, P.Gravityattack.eval(), P.Gravityrelease.eval(), dt); _S['g'] = g
    p = _ar(_S.get('p', 0.0), npd, P.Padattack.eval(), P.Padrelease.eval(), dt); _S['p'] = p
    gmul = max(0.35, 1.0 + P.Gravity.eval() * (g * 1.2 - 0.6))      # around 1 on average: weaker when quiet, up to 1.6x loud
    hmul = max(0.0, 1.0 + P.Haze.eval() * (p * 1.8 - 0.8))
    dmul = max(0.0, 1.0 + P.Darkness.eval() * (p * 0.9 - 0.4))
    scriptOp.clear()
    scriptOp.numSamples = 1
    for nm, v in (('bass', nb), ('padlevel', npd), ('grav', g), ('pads', p), ('gmul', gmul), ('hmul', hmul), ('dmul', dmul)):
        scriptOp.appendChan(nm)[0] = v
    return
'''
sc = C.create(scriptCHOP, 'env'); sc.nodeX, sc.nodeY = 0, 0
try:
    for dd in list(sc.docked):
        dd.destroy()
except Exception:
    pass
sc.par.callbacks = cb
o = C.create(nullCHOP, 'out'); o.nodeX, o.nodeY = 200, 0
o.inputConnectors[0].connect(sc)
ex = C.create(executeDAT, 'cook_exec'); ex.nodeX, ex.nodeY = 0, -150
ex.text = "def onFrameStart(frame):\n\top('env').cook(force=True)\n\treturn\n"
ex.par.framestart = True; ex.par.active = True

# 3. wire them in (with a fallback of 1 if the stems are missing)
def M(ch):
    return "(op('/project1/stems/out')['%s'].eval() if op('/project1/stems/out') is not None and op('/project1/stems/out')['%s'] is not None else 1.0)" % (ch, ch)
g = op('/project1/sphere/sphere')
if g is not None:
    g.par.vec2valuex.expr = "parent().par.Lens * " + M('gmul')
    g.par.vec2valuey.expr = "parent().par.Streaks * (0.6 + 0.4 * " + M('gmul') + ")"
    g.par.vec3valuex.expr = "parent().par.Swirl * " + M('gmul')
else:
    log.append('no sphere')
ns = op('/project1/nin_stage/stage')
if ns is not None:
    for i in range(10):
        nmp = getattr(ns.par, 'vec%dname' % i, None)
        if nmp is not None and nmp.eval() == 'uD':
            getattr(ns.par, 'vec%dvaluez' % i).expr = "parent().par.Haze * " + M('hmul')
            getattr(ns.par, 'vec%dvaluew' % i).expr = "min(1.0, parent().par.Darkness * " + M('dmul') + ")"
            break
    else:
        log.append('uD not found on nin_stage/stage')
else:
    log.append('no nin_stage/stage')
C.save(D + '/stems.tox')
print('STEMS built: %s | bass %s, pads track 2 | log %s' % (C.path, TRACK, log or 'none'))
