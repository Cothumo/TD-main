# Grid - the notes played on the Ableton MIDI track "GRID" shape the visuals (no buttons, no triggers).
#   pitch (average of the held notes)  -> the backlight rises / sinks; low notes darken the edges, high notes lighten them
#   chord (how many notes are held)    -> the haze opens and the scrim layers multiply
#   velocity                           -> more ink
#   held notes (sustain)               -> the Melt trails stretch
# Everything is smoothed and neutral when nothing is played. The TDA_MIDI device sits on the GRID track in Live.
# Rebuild: exec(open(project.folder + '/Grid/build_grid.py').read())  (run it again after rebuilding nin_stage,
# ink or scenes - it wires its multipliers into them)
D = project.folder + '/Grid'
P1 = op('/project1')
TRACK = globals().get('GRID_TRACK', 'GRID')
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

# 1. the abletonMIDI COMP on the GRID track (and the TDA_MIDI device on that track in Live)
m = op('/project1/grid_midi')
if m is None:
    srcm = op('/project1/tdAbletonPackage/tdAbleton/comps/abletonMIDI1')
    m = P1.copy(srcm, name='grid_midi'); m.nodeX, m.nodeY = -600, -1550
    try: m.par.clone = srcm.path
    except Exception: pass
for n_, l_ in zip(m.par.Track.menuNames, m.par.Track.menuLabels):
    if l_ == TRACK:
        m.par.Track = n_
sp(m, 'Callbackdat', '')
sp(m, 'Showdefaultnotechannels', True)
if len(m.par.Device.menuNames) > 1:
    if m.par.Device.eval() in ('', 'None'):
        m.par.Device = m.par.Device.menuNames[1]
else:
    run("op('/project1/grid_midi').par.Adddevice.pulse()", delayFrames=30)   # puts TDA_MIDI on the GRID track in Live

# 2. the grid COMP: note features -> multipliers
old = op('/project1/grid')
if old is not None:
    old.destroy()
C = P1.create(baseCOMP, 'grid'); C.nodeX, C.nodeY = 400, -1550
pg = C.appendCustomPage('Grid')
def fl(nm, dv, lo, hi, hlp, label=None):
    q = (pg.appendFloat(nm, label=label) if label else pg.appendFloat(nm))[0]
    q.default = dv; q.val = dv; q.normMin = lo; q.normMax = hi; q.help = hlp
fl('Amount', 1.0, 0, 2, 'how much the GRID notes shape the visuals (0 = off)')
fl('Pitchlight', 1.0, 0, 2, 'pitch moves the backlight up and down (act 4)')
fl('Pitchdark', 1.0, 0, 2, 'low notes darken the edges of the frame, high notes lighten them')
fl('Chordhaze', 1.0, 0, 2, 'the more notes held, the more the haze opens and the scrim layers multiply')
fl('Velink', 1.0, 0, 2, 'harder notes bring more ink')
fl('Holdmelt', 1.0, 0, 2, 'long held notes stretch the Melt trails')
fl('Lownote', 36, 0, 127, 'the lowest note of the range you play (pitch 0)')
fl('Highnote', 84, 0, 127, 'the highest note of the range you play (pitch 1)')
fl('Attack', 0.6, 0.05, 5, 'seconds the visuals take to follow a note')
fl('Release', 2.5, 0.1, 15, 'seconds they take to settle after it')
fl('Holdtime', 3.0, 0.2, 15, 'seconds a note must be held to stretch the trails fully')
q = pg.appendStr('Midichop', label='MIDI CHOP')[0]; q.default = '/project1/grid_midi/out1'; q.val = q.default
q.help = 'the CHOP with the GRID track notes (TDA_MIDI, channels .../note_<n>)'

cb = C.create(textDAT, 'notes_callbacks'); cb.nodeX, cb.nodeY = -200, 0
cb.text = '''# GRID notes -> pitch, chord, velocity, sustain -> multipliers for the visuals
import math
_S = {}

def _ar(cur, tgt, att, rel, dt):
    v = cur + (tgt - cur) * (1.0 - math.exp(-dt / max(att if tgt > cur else rel, 1e-3)))
    return v if abs(v) > 1e-6 else 0.0

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
    src = op(P.Midichop.eval())
    notes, vels = [], []
    if src is not None:
        for ch in src.chans('*note_*'):
            v = float(ch[0])
            if v == v and v > 0.0:
                try:
                    notes.append(int(ch.name.rsplit('_', 1)[1])); vels.append(v / 127.0 if v > 1.0 else v)
                except Exception:
                    pass
    att, rel = P.Attack.eval(), P.Release.eval()
    lo, hi = P.Lownote.eval(), max(P.Highnote.eval(), P.Lownote.eval() + 1)
    if notes:
        pt = min(max((sum(notes) / len(notes) - lo) / (hi - lo), 0.0), 1.0)
        _S['p'] = _ar(_S.get('p', pt), pt, att, att, dt)
    p = _S.get('p', 0.5)
    on = _S['on'] = _ar(_S.get('on', 0.0), 1.0 if notes else 0.0, att, rel, dt)
    c = _S['c'] = _ar(_S.get('c', 0.0), min(max((len(notes) - 1) / 3.0, 0.0), 1.0), att, rel, dt)
    v = _S['v'] = _ar(_S.get('v', 0.0), max(vels) if vels else 0.0, att * 0.5, rel, dt)
    h = _S['h'] = _ar(_S.get('h', 0.0), 1.0 if notes else 0.0, P.Holdtime.eval() / 3.0, rel * 0.6, dt)
    A = P.Amount.eval()
    out = (('count', float(len(notes))), ('pitch', p), ('on', on), ('chord', c), ('vel', v), ('held', h),
           ('hmul', 1.0 + A * P.Chordhaze.eval() * c),
           ('smul', 1.0 + A * P.Chordhaze.eval() * c * 0.6),
           ('dmul', max(0.0, 1.0 + A * P.Pitchdark.eval() * on * (0.35 - 0.7 * p))),
           ('ly', A * P.Pitchlight.eval() * on * (p - 0.5) * 0.5),
           ('imul', 1.0 + A * P.Velink.eval() * v * 0.6),
           ('madd', A * P.Holdmelt.eval() * h * 0.45))
    scriptOp.clear(); scriptOp.numSamples = 1
    for nm, val in out:
        scriptOp.appendChan(nm)[0] = val if abs(val) > 1e-9 else 0.0
    return
'''
sc = C.create(scriptCHOP, 'notes'); sc.nodeX, sc.nodeY = 0, 0
for dd in list(sc.docked):
    try: dd.destroy()
    except Exception: pass
sc.par.callbacks = cb
o = C.create(nullCHOP, 'out'); o.nodeX, o.nodeY = 200, 0; o.inputConnectors[0].connect(sc)
fx = C.create(executeDAT, 'cook_exec'); fx.nodeX, fx.nodeY = 0, -150
fx.text = "def onFrameStart(frame):\n\top('notes').cook(force=True)\n\treturn\n"
sp(fx, 'framestart', True); sp(fx, 'active', True)

# 3. wire the multipliers in (neutral fallback if grid is missing)
def G(ch, d):
    return "(op('/project1/grid/out')['%s'].eval() if op('/project1/grid/out') is not None and op('/project1/grid/out')['%s'] is not None else %s)" % (ch, ch, d)
def STM(ch):
    return "(op('/project1/stems/out')['%s'].eval() if op('/project1/stems/out') is not None and op('/project1/stems/out')['%s'] is not None else 1.0)" % (ch, ch)
def blk(g, nm):
    for i in range(10):
        n = getattr(g.par, 'vec%dname' % i, None)
        if n is not None and n.eval() == nm:
            return i
    return None
st = op('/project1/nin_stage/stage')
if st is not None:
    i = blk(st, 'uD')
    if i is not None:
        getattr(st.par, 'vec%dvaluez' % i).expr = "parent().par.Haze * " + STM('hmul') + " * " + G('hmul', '1.0')
        getattr(st.par, 'vec%dvaluew' % i).expr = "min(1.0, parent().par.Darkness * " + STM('dmul') + " * " + G('dmul', '1.0') + ")"
    i = blk(st, 'uS')
    if i is not None:
        getattr(st.par, 'vec%dvaluex' % i).expr = "min(max(parent().par.Scrim, 1.0), parent().par.Scrim * " + G('smul', '1.0') + ")"
    i = blk(st, 'uN')
    if i is not None:
        getattr(st.par, 'vec%dvaluey' % i).expr = "min(1.0, parent().par.Melt + " + G('madd', '0.0') + ")"
else:
    log.append('no nin_stage/stage')
tr = op('/project1/nin_stage/trails')
if tr is not None and blk(tr, 'uM') is not None:
    getattr(tr.par, 'vec%dvaluex' % blk(tr, 'uM')).expr = "min(1.0, parent().par.Melt + " + G('madd', '0.0') + ")"
bl = op('/project1/ink_layer/blend')
if bl is not None and blk(bl, 'uL') is not None:
    p = getattr(bl.par, 'vec%dvaluex' % blk(bl, 'uL'))
    e = p.expr
    if '/project1/grid/out' not in e:
        p.expr = "(" + e + ") * " + G('imul', '1.0')
else:
    log.append('no ink_layer/blend uL')
scn = op('/project1/scenes/scenes')
if scn is not None and blk(scn, 'uC') is not None:
    getattr(scn.par, 'vec%dvaluey' % blk(scn, 'uC')).expr = "parent().par.Lighty + " + G('ly', '0.0')
else:
    log.append('no scenes')
v = op('/project1/viewer')
if v is not None and op('/project1/sphere/OUT') is not None:
    sp(v, 'winop', '/project1/sphere/OUT')
C.save(D + '/grid.tox')
print('GRID built: %s (notes of track %s shape the visuals) | log %s' % (C.path, TRACK, log or 'none'))
