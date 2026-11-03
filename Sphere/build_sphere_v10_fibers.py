# Sphere - builds /project1/sphere in the open TDA project: the Sepulcra sphere with a liquid circumference, appearing
# now and then, with plasma bursts (Penumbra) and gravity - it bends the picture around it and pulls the Ambient Ink.
# It is the last layer (after nin_stage), so the NIN distortions never touch it. Run in the Textport (Alt+T):
#   exec(open(project.folder + '/Sphere/build_sphere.py').read())
# Running it again rebuilds only /project1/sphere (it reads nin_stage/OUT; the viewer window shows sphere/OUT).
D = (globals().get('SPHERE_DIR') or project.folder + '/Sphere').replace('\\', '/').rstrip('/')
SRC = globals().get('SPHERE_SOURCE') or ('/project1/scenes/OUT' if op('/project1/scenes') else ('/project1/nin_stage/OUT' if op('/project1/nin_stage') else '/project1/ink_layer/OUT'))
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
    ('Size', 0.05, 0.02, 0.3, 'radius of the event horizon as a fraction of the frame width'),
    ('Sizevariation', 0.015, 0, 0.1, 'each appearance is a little bigger or smaller'),
    ('Travel', 0.8, 0, 1.5, 'how far it drifts through the frame during one appearance (1 = across the frame), meandering'),
    ('Conceal', 0.75, 0, 1, '0 = a clear black disc, 1 = barely there: a soft, vague shadow you notice by its gravity'),
    ('Reach', 3.0, 1, 15, 'how far its gravity reaches, in horizon radii (the effect stays local round it)'),
    ('Sizechange', 0.5, 0, 1, 'it swells and shrinks while it drifts (0 = keeps its size)'),
    ('Lens', 1.3, 0, 3, 'gravity: how strongly the space sags towards it'),
    ('Swirl', 1.3, 0, 3, 'gravity: how strongly the space twists round it (most close in)'),
    ('Streaks', 1.0, 0, 3, 'gravity: close to it the scene is torn into radial streaks falling into it'),
    ('Plasma', 1.0, 0, 1, 'while the sphere is there the Ambient Ink becomes its plasma: born on its limb, pulled back, swirling round it'),
    ('Beam', 0.6, 0, 2, 'its two beams: a split-second flash along its axis now and then, spinning round fast (0 = never)'),
    ('Beamrate', 9.0, 2, 60, 'about this many seconds between beam flashes (a flash waits for a hit, or 3 s)'),
    ('Fibers', 0.8, 0, 2, 'fine filament streams spiralling into it - the gravity made visible (the hole stays round)'),
    ('Fiberspeed', 1.0, 0, 4, 'how fast the filaments are carried round (faster close in)'),
]
pg = C.appendCustomPage('Sphere')
q = pg.appendToggle('Enable')[0]; q.default = True; q.val = True
pg.appendPulse('Summon', label='Summon Now')
pg.appendPulse('Dismiss', label='Dismiss Now')
for nm, dv, lo, hi, hlp in PARS:
    q = pg.appendFloat(nm)[0]; q.default = dv; q.val = dv; q.normMin = lo; q.normMax = hi; q.help = hlp

state = mk(constantCHOP, 'state', -400, 200)
for i, nm in enumerate(['presence', 'cx', 'cy', 'r', 'bang', 'hit', 'hage', 'level', 'dang', 'benv', 'beang']):
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
        # a path through the frame: from one side towards the other, meandering (Travel = how far)
        ang = random.uniform(0, 2 * math.pi); tr = P.Travel.eval()
        mx, my = random.uniform(0.38, 0.62), random.uniform(0.35, 0.65)
        st['p0'] = (mx - 0.5 * tr * 0.55 * math.cos(ang), my - 0.5 * tr * 0.6 * math.sin(ang))
        st['p1'] = (mx + 0.5 * tr * 0.55 * math.cos(ang), my + 0.5 * tr * 0.6 * math.sin(ang))
        st['t0'] = now
        st['cx'], st['cy'] = st['p0']
        st['r'] = max(0.05, P.Size.eval() + random.uniform(-1, 1) * P.Sizevariation.eval())
        st['until'] = now + P.Grow.eval() + random.uniform(P.Durationmin.eval(), max(P.Durationmin.eval(), P.Durationmax.eval()))
        st['seed'] = random.uniform(0, 100)
        st['dang'] = random.uniform(-0.5, 0.5)            # the disc's tilt on screen, a little different each time
        st['bnext'] = now + P.Grow.eval() + random.uniform(2.0, 6.0)
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
    # sporadic events while it is there: a split-second flash of its two beams, spinning
    if pres > 0.5 and ph != 'shrink':
        if P.Beam.eval() > 0 and now >= st.get('bnext', now + 1) and (hit or now >= st['bnext'] + 3.0):
            st['b0'] = now; st['ba'] = random.uniform(-math.pi, math.pi); st['bd'] = random.uniform(0.18, 0.35)
            st['bs'] = random.choice((-1.0, 1.0)) * random.uniform(9.0, 16.0)          # it spins round fast while it flashes
            st['bnext'] = now + P.Beamrate.eval() * random.uniform(0.6, 1.4)
    ba_ = now - st.get('b0', -100.0); bd_ = st.get('bd', 3.0)
    benv = math.sin(math.pi * ba_ / bd_) ** 2 if 0.0 <= ba_ < bd_ else 0.0
    s = st.get('seed', 0.0)
    p0, p1 = st.get('p0', (0.5, 0.5)), st.get('p1', (0.5, 0.5))
    span = max(st.get('until', now + 1.0) + g - st.get('t0', now), 1.0)
    u = min(max((now - st.get('t0', now)) / span, 0.0), 1.0)
    u = u * u * (3.0 - 2.0 * u) * 0.6 + u * 0.4                       # eases in and out a little
    px, py = p0[0] + (p1[0] - p0[0]) * u, p0[1] + (p1[1] - p0[1]) * u
    nx, ny = -(p1[1] - p0[1]), (p1[0] - p0[0])                        # meander across the path
    mw = 0.06 * math.sin(now * 0.23 + s) + 0.03 * math.sin(now * 0.61 + 2.0 * s)
    cx = min(max(px + nx * mw, 0.08), 0.92); cy = min(max(py + ny * mw, 0.08), 0.92)
    S = C.op('state')
    sc = 1.0 + P.Sizechange.eval() * (0.45 * math.sin(now * 0.17 + s) + 0.25 * math.sin(now * 0.43 + 2.0 * s) + 0.15 * (lvl - 0.5))
    vals = {'presence': pres * pres * (3 - 2 * pres), 'cx': cx, 'cy': cy, 'r': st.get('r', 0.2) * max(sc, 0.3), 'bang': st.get('bang', 0.0),
            'hit': env, 'hage': age, 'level': lvl, 'dang': st.get('dang', 0.0),
            'benv': benv, 'beang': st.get('ba', 0.0) + st.get('bs', 0.0) * max(min(ba_, 1.0), 0.0)}
    for i in range(11):
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
     ('uQ', ["parent().par.Lens * (op('/project1/stems/out')['gmul'].eval() if op('/project1/stems/out') is not None and op('/project1/stems/out')['gmul'] is not None else 1.0)", "parent().par.Streaks * (0.6 + 0.4 * (op('/project1/stems/out')['gmul'].eval() if op('/project1/stems/out') is not None and op('/project1/stems/out')['gmul'] is not None else 1.0))", '0', '0']),   # gravity swells with the bass (Stems)
     ('uR', ["parent().par.Swirl * (op('/project1/stems/out')['gmul'].eval() if op('/project1/stems/out') is not None and op('/project1/stems/out')['gmul'] is not None else 1.0)", '0', S % 'dang', '0']),
     ('uS', ['0', '0', 'parent().par.Reach', 'parent().par.Conceal']),
     ('uF', ['0', S % 'benv', S % 'beang', 'parent().par.Beam']),
     ('uT', ['parent().par.Fibers', 'parent().par.Fiberspeed', "(op('/project1/stems/out')['grav'].eval() if op('/project1/stems/out') is not None and op('/project1/stems/out')['grav'] is not None else 0.5)", '0'])]
g.seq.vec.numBlocks = len(U)
for i, (nm, ex_) in enumerate(U):
    getattr(g.par, 'vec%dname' % i).val = nm
    for ch, e in zip('xyzw', ex_):
        getattr(g.par, 'vec%dvalue%s' % (i, ch)).expr = e
o = mk(nullTOP, 'OUT', 0, -300); o.inputConnectors[0].connect(g); o.viewer = True
oo = mk(outTOP, 'out1', 200, -300); oo.inputConnectors[0].connect(o)
sp(C, 'opviewer', 'OUT')

# order: ink_layer -> nin_stage -> sphere (last, untouched by the NIN distortions) -> viewer
ns = op('/project1/nin_stage/src')
if ns is not None:
    sp(ns, 'top', '/project1/ink_layer/OUT')
v = op('/project1/viewer')
if v is not None and op('/project1/arc') is None:      # the arc camera is the last stage when it exists
    sp(v, 'winop', C.path + '/OUT')
C.save(D + '/sphere.tox')
print('SPHERE built: %s (from %s) -> viewer | log %s | errors %s' % (C.path, SRC, sph_log or 'none',
      [(n.name, n.errors()) for n in C.children if n.errors()] or 'none'))
