# Arc - the song's shape drives the scene: build-ups, breakdowns, drops, and a slow camera over the whole set.
# Listens to the real audio (neith_live/audio_in, the Voicemeeter feed) and the kick detector of neith_live:
#   energy     slow loudness against the music's own recent range (quiet passage 0 .. loudest 1)
#   tension    grows while the music builds (rising energy, more hats and snares) - the frame slowly closes in
#   breakdown  the music thins out (quieter than usual, no kick) - the scene holds back, opens up, slows
#   drop       the release after a build or breakdown (the kick comes back hard) - tension lets go with a spring,
#              the act changes, the black hole may appear, the silhouette screen stutters. No flashes.
# Chain: ... sphere -> arc (camera: slow zoom / drift / tilt) -> viewer and Spout 'TDA Main'.
# Rebuild: exec(open(project.folder + '/Arc/build_arc.py').read())  (run it again after rebuilding nin_stage,
# the ink or the sphere - it wires its multipliers into them)
D = project.folder + '/Arc'
P1 = op('/project1')
log = []

def sp(n, name, val=None, expr=None):
    p = getattr(n.par, name, None)
    if p is None:
        log.append('%s.%s missing' % (n.name, name)); return
    try:
        if expr is not None: p.expr = expr
        else: p.val = val
    except Exception as e:
        log.append('%s.%s: %s' % (n.name, name, e))

old = P1.op('arc')
if old is not None:
    old.destroy()
C = P1.create(baseCOMP, 'arc'); C.nodeX, C.nodeY = 1000, -900
pg = C.appendCustomPage('Arc')
def fl(nm, dv, lo, hi, hlp, label=None):
    q = (pg.appendFloat(nm, label=label) if label else pg.appendFloat(nm))[0]
    q.default = dv; q.val = dv; q.normMin = lo; q.normMax = hi; q.help = hlp
q = pg.appendToggle('Enable')[0]; q.default = True; q.val = True
fl('Amount', 1.0, 0, 2, 'how strongly the song shape (build, breakdown, drop) changes the scene')
fl('Sensitivity', 1.0, 0.3, 3, 'higher = builds, breakdowns and drops are detected more easily')
fl('Buildtime', 10.0, 2, 40, 'seconds of building it takes to reach full tension')
fl('Dropcooldown', 16.0, 4, 60, 'at least this many seconds between two drops')
fl('Buildzoom', 0.07, 0, 0.3, 'how far the camera slowly pushes in while the music builds')
fl('Drift', 1.0, 0, 3, 'the slow camera drift and tilt over the whole set (0 = still)')
q = pg.appendToggle('Dropact', label='Drop Changes Act')[0]; q.default = True; q.val = True
q.help = 'a drop moves the acts on (when the acts run on Auto)'
q = pg.appendToggle('Dropsphere', label='Drop Summons Sphere')[0]; q.default = True; q.val = True
q.help = 'a drop may bring the black hole (half of the drops, when it is not there)'
q = pg.appendStr('State')[0]; q.readOnly = True; q.help = 'what the music does now: calm / build / peak / breakdown / drop'

cb = C.create(textDAT, 'arc_callbacks'); cb.nodeX, cb.nodeY = -200, 200
cb.text = r'''# arc: song shape from the audio - energy, tension (build), breakdown, drop; a sprung camera zoom
import math, random
_S = {}

def _ema(k, x, tau, dt):
    v = _S.get(k, x)
    v += (x - v) * (1.0 - math.exp(-dt / max(tau, 1e-3)))
    _S[k] = v
    return v

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
    sens = max(P.Sensitivity.eval(), 0.1)
    # loudness of the real audio (dB)
    a = op('/project1/neith_live/audio_in')
    rms = 0.0
    try:
        arr = a.numpyArray()
        if arr.size:
            rms = float((arr ** 2).mean() ** 0.5)
    except Exception:
        pass
    db = 20.0 * math.log10(rms + 1e-6)
    silent = db < -55.0
    fast = _ema('fast', db, 0.25, dt)
    slow = _ema('slow', db, 4.0, dt)
    lng = _ema('long', db, 30.0, dt)
    # the music's own range: the loudest recent level falls slowly, the quietest rises slowly
    hi = _S.get('hi', slow); lo = _S.get('lo', slow - 20.0)
    hi = slow if slow > hi else hi - 0.25 * dt
    lo = slow if slow < lo else lo + 0.25 * dt
    if hi - lo < 12.0:
        m = 0.5 * (hi + lo); hi, lo = m + 6.0, m - 6.0
    _S['hi'], _S['lo'] = hi, lo
    energy = 0.0 if silent else min(max((slow - lo) / (hi - lo), 0.0), 1.0)
    # kick and hats from neith's detector
    f = op('/project1/neith_live/features')
    def feat(k):
        try:
            return float(f[1, k].val)
        except Exception:
            return 0.0
    kick, hat, snare = feat('kick'), feat('hat'), feat('snare')
    kickavg = _ema('kick', kick, 2.0, dt)
    busy = _ema('busy', 0.6 * hat + 0.4 * snare, 3.0, dt)
    busyslow = _ema('busyslow', 0.6 * hat + 0.4 * snare, 12.0, dt)
    # slope of the slow loudness over the last ~4 s (dB per second)
    hist = _S.setdefault('hist', [])
    hist.append((now, slow))
    while hist and now - hist[0][0] > 4.0:
        hist.pop(0)
    slope = (slow - hist[0][1]) / max(now - hist[0][0], 0.5) if len(hist) > 1 else 0.0
    # tension: grows while it builds, fades otherwise
    building = (slope * sens > 0.25) or (busy - busyslow) * sens > 0.06
    tension = _S.get('tension', 0.0)
    if building and not silent:
        tension = min(1.0, tension + dt / max(P.Buildtime.eval(), 0.5))
    else:
        tension = max(0.0, tension - dt / 6.0)
    # breakdown: clearly quieter than usual and no kick for a while
    thin = (slow < lng - 4.0 / sens) and kickavg < 0.2
    _S['thin_t'] = _S.get('thin_t', 0.0) + dt if thin else 0.0
    bd = _ema('bd', 1.0 if (_S['thin_t'] > 3.0 or silent) else 0.0, 3.0 if thin else 1.5, dt)
    # drop: after a build or breakdown the kick comes back hard and the level jumps
    drop = _S.get('drop', 0.0) * math.exp(-dt / 3.0)
    pulse = 0.0
    primed = tension > 0.45 or bd > 0.4 or _S.get('primed_t', 0.0) > 0.0
    _S['primed_t'] = 6.0 if (tension > 0.45 or bd > 0.4) else max(0.0, _S.get('primed_t', 0.0) - dt)
    if primed and not silent and kick > 0.6 and fast > lng + 1.0 / sens and now - _S.get('lastdrop', -999.0) > P.Dropcooldown.eval():
        drop, pulse = 1.0, 1.0
        _S['lastdrop'] = now; _S['primed_t'] = 0.0
        tension = 0.0; _S['bd'] = 0.0; bd = 0.0
        _S['newdrop'] = True
    _S['tension'], _S['drop'] = tension, drop
    # sprung camera zoom: pushes in with tension, opens a little in breakdowns, springs back on the drop
    A = P.Amount.eval() if P.Enable.eval() else 0.0
    zt = A * (P.Buildzoom.eval() * tension - 0.03 * bd)
    z, zv = _S.get('z', 0.0), _S.get('zv', 0.0)
    zv += ((zt - z) * 6.0 - zv * 3.2) * dt
    z += zv * dt
    _S['z'], _S['zv'] = z, zv
    state = 'drop' if drop > 0.5 else ('breakdown' if bd > 0.5 else ('build' if tension > 0.3 else ('peak' if energy > 0.75 else 'calm')))
    try:
        if P.State.eval() != state:
            P.State.val = state
    except Exception:
        pass
    # multipliers for the scene (neutral when off)
    out = (('energy', energy), ('tension', tension), ('breakdown', bd), ('drop', drop), ('pulse', pulse),
           ('zoom', z), ('slope', slope),
           ('emul', 1.0 + A * (0.5 * tension + 0.6 * drop - 0.5 * bd)),           # echoes
           ('smul', 1.0 + A * (0.6 * tension - 0.3 * bd)),                          # scrim layers
           ('dmul', 1.0 + A * (0.45 * tension - 0.35 * bd - 0.25 * drop)),          # darkness closing in / opening
           ('madd', A * (0.3 * tension + 0.25 * bd)),                               # melt trails stretch
           ('imul', 1.0 + A * (0.4 * energy + 0.5 * drop - 0.55 * bd)))             # ink
    scriptOp.clear(); scriptOp.numSamples = 1
    for nm, v in out:
        scriptOp.appendChan(nm)[0] = v if abs(v) > 1e-9 else 0.0
    return
'''
sc = C.create(scriptCHOP, 'arc'); sc.nodeX, sc.nodeY = 0, 200
for dd in list(sc.docked):
    try: dd.destroy()
    except Exception: pass
sc.par.callbacks = cb
o = C.create(nullCHOP, 'out'); o.nodeX, o.nodeY = 200, 200; o.inputConnectors[0].connect(sc)

# what a drop does: act change, maybe the black hole, the silhouette screen stutters
ex = C.create(executeDAT, 'arc_exec'); ex.nodeX, ex.nodeY = 0, 50
ex.text = r'''import random
def onFrameStart(frame):
	C = me.parent()
	C.op('arc').cook(force=True)
	m = C.op('arc_callbacks').module
	if not m._S.pop('newdrop', False) or not C.par.Enable.eval():
		return
	N = op('/project1/nin_stage')
	if C.par.Dropact.eval() and N is not None and N.par.Actsource.eval() == 'auto':
		names = list(N.par.Act.menuNames)
		if N.par.Act.eval() in names:
			N.par.Act = names[(names.index(N.par.Act.eval()) + 1) % len(names)]
	S = op('/project1/sphere')
	if C.par.Dropsphere.eval() and S is not None and S.storage.get('phase') in (None, 'idle') and random.random() < 0.5:
		S.storage['summon'] = True
	S2 = op('/project1/screen2')
	if S2 is not None:
		S2.store('stu_base', absTime.frame); S2.store('stu_len', random.randint(4, 8)); S2.store('stu_until', absTime.seconds + 0.6)
	return
'''
sp(ex, 'framestart', True); sp(ex, 'active', True)

# the camera over the whole picture
src = C.create(selectTOP, 'src'); src.nodeX, src.nodeY = 0, -150
sp(src, 'top', '/project1/sphere/OUT' if op('/project1/sphere') else '/project1/scenes/OUT')
cam = C.create(transformTOP, 'camera'); cam.nodeX, cam.nodeY = 200, -150
cam.inputConnectors[0].connect(src)
sp(cam, 'extend', 'mirror')
# the zoom always covers the frame: enough for the current tilt (portrait needs more) and drift, plus the breathing
Z = ("(max(1.0, math.cos(math.radians(abs(me.par.rotate))) + (max(me.width, me.height) / max(min(me.width, me.height), 1)) * math.sin(math.radians(abs(me.par.rotate))))"
     " + 2.0 * max(abs(me.par.tx), abs(me.par.ty)) + 0.015)"
     " * (1.0 + max(0.0, op('out')['zoom'].eval()) + 0.025 * parent().par.Drift * (0.5 + 0.5 * math.sin(absTime.seconds * 0.021)))")
sp(cam, 'sx', expr=Z); sp(cam, 'sy', expr=Z)
sp(cam, 'tx', expr="0.035 * parent().par.Drift * (math.sin(absTime.seconds * 0.031) + 0.4 * math.sin(absTime.seconds * 0.083 + 2.1))")
sp(cam, 'ty', expr="0.03 * parent().par.Drift * (math.sin(absTime.seconds * 0.027 + 1.7) + 0.4 * math.sin(absTime.seconds * 0.071))")
sp(cam, 'rotate', expr="2.5 * parent().par.Drift * (math.sin(absTime.seconds * 0.019 + 0.4) + 0.3 * math.sin(absTime.seconds * 0.061)) + 1.2 * op('out')['tension'].eval() * parent().par.Amount * math.sin(absTime.seconds * 0.07)")
out = C.create(nullTOP, 'OUT'); out.nodeX, out.nodeY = 400, -150; out.inputConnectors[0].connect(cam); out.viewer = True
sp(C, 'opviewer', 'OUT')

# wire the multipliers into the scene (neutral fallback if arc is missing)
def A(ch, d):
    return "(op('/project1/arc/out')['%s'].eval() if op('/project1/arc/out') is not None and op('/project1/arc/out')['%s'] is not None else %s)" % (ch, ch, d)
def blk(g, nm):
    for i in range(12):
        n = getattr(g.par, 'vec%dname' % i, None)
        if n is not None and n.eval() == nm:
            return i
    return None
def wrap(g, nm, ch, how):
    if g is None:
        log.append('missing op for ' + nm); return
    i = blk(g, nm)
    if i is None:
        log.append('%s: no %s' % (g.path, nm)); return
    p = getattr(g.par, 'vec%dvalue%s' % (i, ch))
    e = p.expr if p.mode == ParMode.EXPRESSION else str(p.eval())
    if '/project1/arc/out' in e:
        return
    p.expr = how(e)
st = op('/project1/nin_stage/stage'); tr = op('/project1/nin_stage/trails'); bl = op('/project1/ink_layer/blend')
wrap(st, 'uE', 'x', lambda e: "(" + e + ") * " + A('emul', '1.0'))
wrap(st, 'uS', 'x', lambda e: "(" + e + ") * " + A('smul', '1.0'))
wrap(st, 'uD', 'w', lambda e: "min(1.0, (" + e + ") * " + A('dmul', '1.0') + ")")
wrap(st, 'uN', 'y', lambda e: "min(1.0, (" + e + ") + " + A('madd', '0.0') + ")")
wrap(tr, 'uM', 'x', lambda e: "min(1.0, (" + e + ") + " + A('madd', '0.0') + ")")
wrap(bl, 'uL', 'x', lambda e: "(" + e + ") * " + A('imul', '1.0'))

# the picture now leaves through the camera
v = op('/project1/viewer')
if v is not None:
    sp(v, 'winop', C.path + '/OUT')
ms = op('/project1/obs_out/main_src')
if ms is not None:
    sp(ms, 'top', C.path + '/OUT')
C.save(D + '/arc.tox')
print('ARC built: %s | log %s' % (C.path, log or 'none'))
