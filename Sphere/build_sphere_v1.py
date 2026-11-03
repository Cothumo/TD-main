# Sphere - builds /project1/sphere in the open TDA project: the Sepulcra sphere with a liquid circumference, appearing
# now and then, with plasma bursts (Penumbra) and gravity - it bends the picture around it and pulls the Ambient Ink.
# Sits between ink_layer and nin_stage. Run in the Textport (Alt+T):
#   exec(open(project.folder + '/Sphere/build_sphere.py').read())
# Running it again rebuilds only /project1/sphere (and points nin_stage at it).
D = (globals().get('SPHERE_DIR') or project.folder + '/Sphere').replace('\\', '/').rstrip('/')
SRC = globals().get('SPHERE_SOURCE', '/project1/ink_layer/OUT')
sph_log = []

def sp(n, name, val=None, expr=None):
    try:
        p = getattr(n.par, name)
        if expr is not None: p.expr = expr
        else: p.val = val
    except Exception as e:
        sph_log.append('%s.%s: %s' % (n.name, name, e))

old = op('/project1/sphere')
if old: old.destroy()
C = op('/project1').create(baseCOMP, 'sphere')
C.nodeX, C.nodeY = 1000, -400
C.color = (0.1, 0.1, 0.12)

def mk(ty, name, x, y):
    n = C.create(ty, name); n.nodeX, n.nodeY = x, y; return n

PARS = [
    ('Intervalmin', 35.0, 5, 300, 'the sphere comes back at the earliest this many seconds after it left'),
    ('Intervalmax', 75.0, 5, 400, '... and at the latest after this many (it waits for a strong hit in between)'),
    ('Durationmin', 14.0, 3, 120, 'it stays at least this many seconds'),
    ('Durationmax', 22.0, 3, 180, '... and at most this many'),
    ('Grow', 3.0, 0.3, 15, 'seconds it takes to grow out of a point / collapse back'),
    ('Size', 0.20, 0.05, 0.45, 'radius as a fraction of the frame width'),
    ('Sizevariation', 0.05, 0, 0.2, 'each appearance is a little bigger or smaller'),
    ('Lens', 1.0, 0, 3, 'gravity: how strongly the picture around it is bent towards it'),
    ('Swirl', 0.8, 0, 3, 'gravity: the space around it is slowly drawn round it'),
    ('Liquid', 1.0, 0, 3, 'the liquid circumference: the edge undulates like a drop, surging with the music and on hits'),
    ('Corona', 0.8, 0, 3, 'the corona breathing with the music (a shadow halo on white paper)'),
    ('Bursts', 1.0, 0, 3, 'plasma bursts from the limb on strong hits'),
    ('Rim', 0.6, 0, 3, 'a thin light on the liquid edge'),
    ('Plasma', 1.0, 0, 1, 'while the sphere is there the Ambient Ink becomes its plasma: born on its limb, pulled back, swirling round it'),
]
pg = C.appendCustomPage('Sphere')
q = pg.appendToggle('Enable')[0]; q.default = True; q.val = True
pg.appendPulse('Summon', label='Summon Now')
pg.appendPulse('Dismiss', label='Dismiss Now')
for nm, dv, lo, hi, hlp in PARS:
    q = pg.appendFloat(nm)[0]; q.default = dv; q.val = dv; q.normMin = lo; q.normMax = hi; q.help = hlp

state = mk(constantCHOP, 'state', -400, 200)
for i, nm in enumerate(['presence', 'cx', 'cy', 'r', 'bang', 'hit', 'hage', 'level']):
    sp(state, 'name%d' % i, nm)
    sp(state, 'value%d' % i, 0.0)

sched = mk(textDAT, 'scheduler', -400, 50)
sched.text = '''# when the sphere comes and goes, where it is, its plasma bursts - updated every frame (sphere/scheduler_exec)
import math, random
HITS = '/project1/nin_stage/echo'          # track 1 hits (env, age, level) from the NIN stage

def _f(v, d=0.0):
    try:
        v = float(v)
        return v if (v == v and abs(v) < 1e30) else d
    except Exception:
        return d

def frame():
    C = me.parent(); P = C.par; st = C.storage
    now = absTime.seconds
    if st.get('t', 0.0) > now:                             # TouchDesigner restarted: its clock starts from 0 again
        st.clear()
    dt = min(0.1, max(1.0 / 240, now - st.get('t', now - 1.0 / 60))); st['t'] = now
    e = op(HITS)
    env = _f(e['env']) if e is not None and e['env'] is not None else 0.0
    age = _f(e['age'], 30.0) if e is not None and e['age'] is not None else 30.0
    lvl = _f(e['slevel']) if e is not None and e['slevel'] is not None else 0.0
    hit = age < 0.05 and st.get('lastage', 30.0) >= 0.05
    st['lastage'] = age
    if 'next' not in st:
        st.update(phase='idle', next=now + random.uniform(8.0, 15.0), pres=0.0)
    ph = st['phase']
    if st.pop('summon', False) and ph in ('idle', 'shrink'):
        ph = 'start'
    if st.pop('dismiss', False) and ph in ('grow', 'hold'):
        ph = 'shrink'
    if not P.Enable.eval() and ph in ('grow', 'hold'):
        ph = 'shrink'
    if ph == 'idle' and P.Enable.eval() and now >= st['next'] and (hit or now >= st['next'] + 6.0):
        ph = 'start'
    if ph == 'start':
        st['cx'] = random.uniform(0.32, 0.68); st['cy'] = random.uniform(0.32, 0.68)
        st['r'] = max(0.05, P.Size.eval() + random.uniform(-1, 1) * P.Sizevariation.eval())
        st['until'] = now + P.Grow.eval() + random.uniform(P.Durationmin.eval(), max(P.Durationmin.eval(), P.Durationmax.eval()))
        st['seed'] = random.uniform(0, 100)
        ph = 'grow'
    g = max(P.Grow.eval(), 0.05)
    pres = st.get('pres', 0.0)
    if ph == 'grow':
        pres = min(1.0, pres + dt / g)
        if now >= st.get('until', now):
            ph = 'shrink'
    elif ph == 'shrink':
        pres = max(0.0, pres - dt / g)
        if pres <= 0.0:
            ph = 'idle'
            st['next'] = now + random.uniform(P.Intervalmin.eval(), max(P.Intervalmin.eval(), P.Intervalmax.eval()))
    st['phase'] = ph; st['pres'] = pres
    if hit:
        st['bang'] = random.uniform(0, 2 * math.pi)
    s = st.get('seed', 0.0)
    cx = st.get('cx', 0.5) + 0.025 * math.sin(now * 0.11 + s); cy = st.get('cy', 0.5) + 0.02 * math.cos(now * 0.083 + s)
    S = C.op('state')
    vals = {'presence': pres * pres * (3 - 2 * pres), 'cx': cx, 'cy': cy, 'r': st.get('r', 0.2), 'bang': st.get('bang', 0.0),
            'hit': env, 'hage': age, 'level': lvl}
    for i in range(8):
        nm = getattr(S.par, 'name%d' % i).eval()
        if nm in vals:
            getattr(S.par, 'value%d' % i).val = vals[nm]
'''
ex = mk(executeDAT, 'scheduler_exec', -200, 50)
ex.text = "def onFrameStart(frame):\n\top('scheduler').module.frame()\n\treturn\n"
sp(ex, 'framestart', True); sp(ex, 'active', True)
pe = mk(parameterexecuteDAT, 'pulses', -200, -100)
pe.text = "def onPulse(par):\n\tif par.name == 'Summon':\n\t\tpar.owner.storage['summon'] = True\n\telif par.name == 'Dismiss':\n\t\tpar.owner.storage['dismiss'] = True\n\treturn\n"
sp(pe, 'op', '..'); sp(pe, 'pars', 'Summon Dismiss'); sp(pe, 'onpulse', True); sp(pe, 'valuechange', False)

# geometry for the ink (ink_track2 reads it through g: uniforms): the sphere in the simulation's world units
geo = mk(textDAT, 'geometry', -400, -100)
geo.text = '''# where the sphere is, in the ink simulation's world units (x: +-aspect, y: +-1)
ASPECT = 720.0 / 1280.0
def G():
    S = me.parent().op('state'); P = me.parent().par
    pres = float(S['presence']); k = 2.0 * ASPECT
    x = (float(S['cx']) - 0.5) * k; y = (float(S['cy']) - 0.5) * 2.0
    r = float(S['r']) * pres * k
    return {'wOx': x, 'wOy': y, 'wRo': r * 0.96, 'behind': 1.0 if pres > 0.05 else 0.0,
            'wMx': x, 'wMy': y, 'wRm': r, 'rad': 0.0, 'limb': pres * float(P.Plasma),
            'fa': 0.0, 'fb': 0.0, 'fm': 0.0, 'fs': 0.0, 'flood': 0.0, 'hard': 0.0}
'''

src = mk(selectTOP, 'src', -400, -300); sp(src, 'top', SRC)
px = mk(textDAT, 'sphere_pixel', -200, -450); px.text = open(D + '/sphere.glsl').read()
g = mk(glslTOP, 'sphere', -200, -300)
g.inputConnectors[0].connect(src)
sp(g, 'pixeldat', 'sphere_pixel')
try:
    for dd in list(g.docked):
        if dd.name != 'sphere_pixel': dd.destroy()
except Exception:
    pass
try:
    g.par.outputresolution = 'useinput'
except Exception as e:
    sph_log.append('res: %s' % e)
S = "op('state')['%s']"
U = [('uP', [S % 'presence', S % 'cx', S % 'cy', S % 'r']),
     ('uH', ['absTime.seconds % 10000', S % 'level', S % 'hit', S % 'hage']),
     ('uQ', ['parent().par.Lens', 'parent().par.Liquid', 'parent().par.Corona', 'parent().par.Bursts']),
     ('uR', ['parent().par.Swirl', 'parent().par.Rim', S % 'bang', '0'])]
g.seq.vec.numBlocks = len(U)
for i, (nm, ex_) in enumerate(U):
    getattr(g.par, 'vec%dname' % i).val = nm
    for ch, e in zip('xyzw', ex_):
        getattr(g.par, 'vec%dvalue%s' % (i, ch)).expr = e
o = mk(nullTOP, 'OUT', 0, -300); o.inputConnectors[0].connect(g); o.viewer = True
oo = mk(outTOP, 'out1', 200, -300); oo.inputConnectors[0].connect(o)
sp(C, 'opviewer', 'OUT')

# the NIN stage now reads the picture with the sphere in it
ns = op('/project1/nin_stage/src')
if ns is not None:
    sp(ns, 'top', C.path + '/OUT')
C.save(D + '/sphere.tox')
print('SPHERE built: %s (from %s) -> nin_stage | log %s | errors %s' % (C.path, SRC, sph_log or 'none',
      [(n.name, n.errors()) for n in C.children if n.errors()] or 'none'))
