# Meter guard - silence when Ableton goes silent.
# TDAbleton only sends a track meter when it changes; when Ableton stops (or the link drops) the last value can stay
# frozen in TouchDesigner, so the scene thinks audio is still coming (no inversion in neith, ink stays, echoes go on).
# Each guard passes a track's channels through, but a meter that has not moved at all for Stale seconds fades to 0.
# Everything that listens to a track now reads its guard: /project1/meter_guard/<track>/out1 (same channel names).
# Rebuild: exec(open(project.folder + '/Guard/build_meter_guard.py').read())
D = project.folder + '/Guard'
P1 = op('/project1')
TRACKS = ['track_A_transient', 'track_B_tonal', 'track_C_ink', 'track_D_micro']
log = []

old = op('/project1/meter_guard')
if old is not None:
    old.destroy()
G = P1.create(baseCOMP, 'meter_guard'); G.nodeX, G.nodeY = -300, -1750
pg = G.appendCustomPage('Guard')
q = pg.appendFloat('Stale')[0]; q.default = 1.5; q.val = 1.5; q.normMin = 0.3; q.normMax = 10
q.help = 'seconds a meter may stay exactly the same before it counts as silence (real audio always moves)'
q = pg.appendFloat('Fade')[0]; q.default = 0.4; q.val = 0.4; q.normMin = 0.02; q.normMax = 5
q.help = 'seconds a frozen meter takes to fade to 0'

cb = G.create(textDAT, 'guard_callbacks'); cb.nodeX, cb.nodeY = 0, 300
cb.text = '''# meter guard: pass the track's channels through; a meter frozen for Stale seconds fades to 0
import math
_S = {}

def onSetupParameters(scriptOp):
    return

def onPulse(par):
    return

def onCook(scriptOp):
    G = op('/project1/meter_guard'); P = G.par
    now = absTime.seconds
    key = scriptOp.path
    st = _S.setdefault(key, {})
    if st.get('_t', 0.0) > now:
        st.clear()
    dt = min(0.1, max(1.0 / 240, now - st.get('_t', now - 1.0 / 60))); st['_t'] = now
    scriptOp.clear()
    if not scriptOp.inputs:
        return
    src = scriptOp.inputs[0]
    scriptOp.numSamples = 1
    stale, fade = P.Stale.eval(), max(P.Fade.eval(), 0.01)
    for ch in src.chans():
        v = float(ch[0])
        if v != v or abs(v) > 1e9:
            v = 0.0
        if 'output_meter' in ch.name:
            last, since, g = st.get(ch.name, (None, now, 1.0))
            if last is None or v != last:
                since = now
            frozen = (now - since) > stale
            g = max(0.0, g - dt / fade) if frozen else min(1.0, g + dt / 0.05)
            st[ch.name] = (v, since, g)
            v = v * g
        scriptOp.appendChan(ch.name)[0] = v if abs(v) > 1e-12 else 0.0
    return
'''
y = 0
for name in TRACKS:
    src = op('/project1/' + name)
    if src is None:
        log.append('no ' + name); continue
    T = G.create(baseCOMP, name); T.nodeX, T.nodeY = 200, y; y -= 150
    sel = T.create(selectCHOP, 'src'); sel.nodeX, sel.nodeY = -200, 0
    sel.par.chops = '/project1/%s/out1' % name
    sc = T.create(scriptCHOP, 'guard'); sc.nodeX, sc.nodeY = 0, 0
    for dd in list(sc.docked):
        try: dd.destroy()
        except Exception: pass
    sc.par.callbacks = cb.path
    sc.inputConnectors[0].connect(sel)
    o = T.create(nullCHOP, 'out1'); o.nodeX, o.nodeY = 200, 0
    o.inputConnectors[0].connect(sc)
ex = G.create(executeDAT, 'cook_exec'); ex.nodeX, ex.nodeY = 0, 150
ex.text = ("def onFrameStart(frame):\n"
           "\tfor t in parent().children:\n"
           "\t\tg = t.op('guard') if t.isCOMP else None\n"
           "\t\tif g is not None:\n\t\t\tg.cook(force=True)\n"
           "\treturn\n")
ex.par.framestart = True; ex.par.active = True

# repoint everything that listens to a track
GP = '/project1/meter_guard/'
def setp(path, par, val):
    o = op(path)
    p = getattr(o.par, par, None) if o is not None else None
    if p is None:
        log.append('%s.%s missing' % (path, par)); return
    p.val = val
setp('/project1/stems', 'Bassmeter', GP + 'track_D_micro/out1')
setp('/project1/stems', 'Padmeter', GP + 'track_C_ink/out1')
setp('/project1/nin_stage', 'Track1meter', GP + 'track_A_transient/out1')
setp('/project1/ink_track2', 'Abletonchop', GP + 'track_C_ink/out1')
setp('/project1/neith_live', 'Transienttrack', GP + 'track_A_transient')
setp('/project1/neith_live', 'Tonaltrack', GP + 'track_B_tonal')
G.save(D + '/meter_guard.tox')
print('METER GUARD built: %s | log %s' % (G.path, log or 'none'))
