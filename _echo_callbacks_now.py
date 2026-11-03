# echo trigger: a strong hit starts an envelope and picks a new drift direction
import math, random
def _fin(v):
    try:
        v = float(v)
    except Exception:
        return 0.0
    return v if (v == v and abs(v) < 1e30 and abs(v) > 1e-12) else 0.0
_S = {}          # state lives here, in memory (op.storage is saved into the .toe and cannot hold the analysis object)

def onSetupParameters(scriptOp):
    return
def onCook(scriptOp):
    p = scriptOp.parent(); st = _S
    now = absTime.seconds
    dt = min(0.1, max(1.0 / 240, now - st.get('t', now - 1.0 / 60))) if now >= st.get('t', 0.0) else 1.0 / 60; st['t'] = now
    src = p.par.Hitsource.eval()
    hit, pulse, level = False, 0.0, 0.0
    hat, onset = 0.0, 0.0
    if src == 'track1':
        # own hit detection on the output meter of track 1 (the same live analysis as the ink layer)
        if st.get('lf') is None:
            st['lf'] = mod('/project1/ink_track2/live_features').LiveFeatures()
        c = p.par.Track1meter.eval()
        vals = [_fin(ch.eval()) for ch in c.chans() if 'output_meter_left' in ch.name or 'output_meter_right' in ch.name] if c is not None else []
        v0 = sum(vals) / len(vals) if vals else 0.0
        f = st['lf'].step(v0, v0, v0, v0, dt=dt)
        pulse, level = max(f['kick'], f['onset']), f['level']
        hat, onset = f['hat'], f['onset']
        kid = f['kick_id']; hit = kid != st.get('kid', kid) and f['kick'] >= p.par.Echothreshold.eval(); st['kid'] = kid
    elif src == 'track2':
        L = op('/project1/ink_track2/live')
        if L is not None and L['kick'] is not None:
            pulse, level = max(_fin(L['kick']), _fin(L['onset'])), _fin(L['level'])
            hat, onset = _fin(L['hat']), _fin(L['onset'])
            kid = _fin(L['kick_id']); hit = kid != st.get('kid', kid) and _fin(L['kick']) >= p.par.Echothreshold.eval(); st['kid'] = kid
    else:
        T = p.par.Tracks.eval()
        pulse = _fin(T['t1_pulse']) if T is not None and T['t1_pulse'] is not None else 0.0
        level = _fin(T['t1_level']) if T is not None and T['t1_level'] is not None else 0.0
        hit = pulse >= p.par.Echothreshold.eval() and st.get('prev', 0.0) < p.par.Echothreshold.eval()
        st['prev'] = pulse
    last = st.get('last', -99.0)
    if last > now:                       # TouchDesigner restarted (its clock starts again from 0; storage is saved in the .toe)
        st['last'] = last = -99.0
    if hit and now - last >= p.par.Echogap.eval():
        st['last'] = last = now
        a = random.uniform(0, 2 * math.pi)
        st['dir'] = (math.cos(a), math.sin(a))
    age = now - last
    env = math.exp(-min(max(age, 0.0) / max(p.par.Echodecay.eval(), 0.05), 50.0)) if 0.0 <= age < 30 else 0.0
    d = st.get('dir', (1.0, 0.0))
    st['sl'] = st.get('sl', 0.0) + (level - st.get('sl', 0.0)) * (1.0 - math.exp(-dt / 0.6))
    # flicker: how unsteady the level is (for the heat shimmer) - fast changes against the slow level
    jit = min(1.0, abs(level - st.get('pl', level)) * 18.0); st['pl'] = level
    k_ = 1.0 - math.exp(-dt / (0.06 if jit > st.get('fl', 0.0) else 0.6))
    st['fl'] = st.get('fl', 0.0) + (jit - st.get('fl', 0.0)) * k_
    scriptOp.clear(); scriptOp.numSamples = 1
    for k, v in (('env', env), ('age', min(age, 30.0)), ('dx', d[0]), ('dy', d[1]), ('pulse', pulse), ('level', level),
                 ('slevel', st['sl']), ('hat', hat), ('onset', onset), ('flicker', st['fl'])):
        scriptOp.appendChan(k)[0] = _fin(v) if k not in ('dx', 'dy') else v
    return
