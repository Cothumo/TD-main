# Ambient Ink Live - the third reacting layer of TDA.16: the Ambient Ink simulation (1M GPU particles), driven LIVE by
# Ableton track "2" through TDAbleton, multiplied over neith_live (white paper, black ink, like the layers below it).
# Run it inside the open project (Textport, Alt+T):
#   exec(open(project.folder + '/Ambient Ink Live/build_ink.py').read())
# It builds /project1/ink_track2 and /project1/ink_layer (the mix: neith_live/OUT x ink), points the 'viewer' window at
# the mix and saves ink_track2.tox. Nothing else in the project is changed; running it again rebuilds both.
# The Script CHOP 'live' computes the ink's features frame by frame (live_features.py) from the level of track "2" in
# three bands. Sources (Play page of ink_track2):
#   ableton .. the output meter of Ableton track "2" (track_C_ink, like the other layers) - the default;
#              or, with 'Ableton Values' = bands, the Low / Mid / High of its TDA_Audio_Analyzer
#   device ... an audio input (Audio Device In CHOP 'audio_in': pick the driver / device / channels there)
#   file ..... a looping test file
import os


def _own_folder():
    # run from a Text DAT that was dragged in from disk: its File parameter points at this script
    try:
        f = me.par.file.eval()
        if f and os.path.exists(f):
            return os.path.dirname(os.path.abspath(f))
    except Exception:
        pass
    return None


D = (globals().get('INK_DIR') or _own_folder() or project.folder + '/Ambient Ink Live').replace('\\', '/').rstrip('/')
spec = {}
exec(open(D + '/ink_spec.py').read(), spec)
FPS, W, H, SIM_W, SIM_H = spec['FPS'], spec['W'], spec['H'], spec['SIM_W'], spec['SIM_H']
ink_log = []

# ---------------------------------------------------------------- live: no song, no analysis
TEST = globals().get('INK_TEST') or spec.get('TEST_AUDIO', '')
test = TEST.replace('\\', '/') if os.path.isabs(TEST) else D + '/' + TEST
print('INK live | test audio:', test)
ABL_TRACK = globals().get('INK_ABLETON_TRACK', '2')                  # the Ableton track the ink listens to
ABL_CHOP = globals().get('INK_ABLETON_CHOP', '/project1/track_C_ink/out1')
# an abletonTrack COMP for that track (a copy of track_A_transient, the way the other layers of TDA.16 listen)
try:
    _src = op('/project1/track_A_transient')
    if _src is not None and op('/project1/track_C_ink') is None:
        _t = op('/project1').copy(_src, name='track_C_ink')
        _t.nodeX, _t.nodeY = -600, -1150
        for _n, _l in zip(_t.par.Track.menuNames, _t.par.Track.menuLabels):
            if _l == ABL_TRACK:
                _t.par.Track = _n
        try:
            _t.par.Enablecallbacks = False
        except Exception:
            pass
except Exception as e:
    print('INK: could not make track_C_ink:', e)
UNDER = globals().get('INK_UNDER', '/project1/neith_live/OUT')        # the picture the ink is multiplied over

def trypar(n, name, val=None, expr=None):
    try:
        p = getattr(n.par, name)
        if expr is not None:
            p.expr = expr
        else:
            p.val = val
        return True
    except Exception as e:
        ink_log.append('%s.%s: %s' % (n.name, name, e))
        return False


def setmenu(n, name, *keys):
    try:
        p = getattr(n.par, name)
        for k in keys:
            for m in p.menuNames:
                if k == m.lower() or k in m.lower():
                    p.val = m
                    return m
        ink_log.append('%s.%s no match in %s' % (n.name, name, p.menuNames[:12]))
    except Exception as e:
        ink_log.append('%s.%s: %s' % (n.name, name, e))


def mk(parent, ty, name, x, y):
    n = parent.create(ty, name)
    n.nodeX, n.nodeY = x, y
    return n


def shader(parent, name, fname, x, y):
    t = mk(parent, textDAT, name, x, y)
    t.text = open(D + '/' + fname).read()
    return t


def drop_docked(n, keep):
    # GLSL ops may come with their own docked example shaders; remove them so ours are the only ones
    try:
        for d in list(n.docked):
            if d.name not in keep:
                d.destroy()
    except Exception as e:
        ink_log.append('%s docked: %s' % (n.name, e))


ROW = "op('live')['%s']"
SPECIAL = {
    'frame': "parent().par.Loopframe",
    'dt': "1.0 / max(1, project.cookRate)",          # the project cooks at its own rate (60 fps in TDA.16)
    'reset': "1 if parent().par.Forcereset else 0",
    'aspect': "%r" % (W / float(H)),
    'resh': "%d" % H,
}


GATED = ('Ink', 'Condense', 'Jet', 'Dust', 'Sprayamount')      # no input -> no new ink, and the old ink fades out


def uniforms(g, block):
    U = spec['UNIFORMS'][block]
    try:
        g.seq.vec.numBlocks = len(U)
    except Exception as e:
        ink_log.append('%s vec seq: %s' % (g.name, e))
    for i, (nm, srcs) in enumerate(U):
        trypar(g, 'vec%dname' % i, nm)
        for c, s in zip('xyzw', srcs):
            if s.startswith('f:'):
                ex = ROW % s[2:]
            elif s.startswith('p:') and s[2:] in GATED:
                ex = "parent().par.%s * op('live')['presence']" % s[2:]
            elif s.startswith('p:'):
                ex = 'parent().par.%s' % s[2:]
            elif s.startswith('g:'):                  # the sphere, shared with /project1/sphere
                ex = "op('/project1/sphere/geometry').module.G()['%s'] if op('/project1/sphere/geometry') else 0" % s[2:]
            else:
                ex = SPECIAL.get(s, s)
            trypar(g, 'vec%dvalue%s' % (i, c), expr=ex)


# ---------------------------------------------------------------- component + parameters
NAME, PREFIX, SH = spec['NAME'], spec['PREFIX'], spec['SHADERS']
old = op('/project1/' + NAME)
if old:
    old.destroy()
C = op('/project1').create(baseCOMP, NAME)
C.nodeX, C.nodeY = 0, -900

pg = C.appendCustomPage('Play')
q = pg.appendMenu('Source')[0]
q.menuNames = ['ableton', 'device', 'file']
q.menuLabels = ['Ableton track "2" (TDA_Audio_Analyzer)', 'Audio input (audio_in)', 'Test file (looping)']
q.default = 'ableton'; q.val = 'ableton'
q = pg.appendCHOP('Abletonchop', label='Ableton CHOP')[0]
q.default = ABL_CHOP; q.val = ABL_CHOP
q.help = 'the abletonLevel output of track "2" (its TDA_Audio_Analyzer: Low / Mid / High, left and right)'
q = pg.appendMenu('Abletonmode', label='Ableton Values')[0]
q.menuNames = ['meter', 'bands']
q.menuLabels = ['Track output meter (abletonTrack)', 'Low / Mid / High (TDA_Audio_Analyzer)']
q.default = 'meter'; q.val = 'meter'
q = pg.appendStr('Abletonchans', label='Ableton Channels')[0]
q.default = 'output_meter_left output_meter_right'; q.val = q.default
q.help = 'meter: the channel(s) averaged as the level; bands: parts of the names used as low / mid / high'
q = pg.appendToggle('Abletondb', label='Ableton Values In dB')[0]; q.default = False; q.val = False
q = pg.appendFile('Testfile', label='Test File')[0]; q.default = test; q.val = test
q = pg.appendFloat('Gain', label='Input Gain (dB)')[0]; q.default = 0.0; q.val = 0.0; q.normMin = -24; q.normMax = 24
q = pg.appendToggle('Monitor', label='Monitor Test File')[0]; q.default = True; q.val = True
q = pg.appendFloat('Volume')[0]; q.default = 1.0; q.val = 1.0; q.normMax = 1.0
pg.appendPulse('Restart', label='Restart Ink')
q = pg.appendToggle('Forcereset')[0]; q.val = False
lf = pg.appendInt('Loopframe')[0]
lf.expr = "int(absTime.frame)"
lf.readOnly = True

lk = C.appendCustomPage('Look')
for nm, dv, lo, hi, _help in spec['PARAMS']:
    q = lk.appendFloat(nm)[0]
    q.default = dv; q.val = dv; q.normMin = lo; q.normMax = hi
    try:
        q.help = _help
    except Exception:
        pass
for nm, dv, lo, hi, _help in spec.get('LAYER_PARAMS', []):
    q = lk.appendFloat(nm)[0]
    q.default = dv; q.val = dv; q.normMin = lo; q.normMax = hi
    q.help = _help
for cname, rgb in spec['COLORS']:
    grp = lk.appendRGB(cname)
    for i, v in enumerate(rgb):
        grp[i].default = v; grp[i].val = v

# ---------------------------------------------------------------- live analysis: source -> level of the whole signal and 3 bands -> features
lfd = mk(C, textDAT, 'live_features', -1000, 700)
lfd.text = open(D + '/live_features.py').read()
fin = mk(C, audiofileinCHOP, 'test_audio', -1200, 500)
trypar(fin, 'file', expr='parent().par.Testfile')
setmenu(fin, 'playmode', 'sequential')
trypar(fin, 'repeat', True) or setmenu(fin, 'repeat', 'on', 'loop')
din = mk(C, audiodeviceinCHOP, 'audio_in', -1200, 380)
trypar(din, 'active', expr="parent().par.Source == 'device'")
srcsw = mk(C, switchCHOP, 'source', -1050, 450)
srcsw.inputConnectors[0].connect(fin); srcsw.inputConnectors[1].connect(din)
trypar(srcsw, 'index', expr="1 if parent().par.Source == 'device' else 0")
mono = mk(C, mathCHOP, 'mono', -900, 450)
mono.inputConnectors[0].connect(srcsw)
setmenu(mono, 'chanop', 'average', 'avg')
bands = mk(C, mergeCHOP, 'bands', -450, 450)
for k, (nm, kind, f0) in enumerate([('level', None, 0), ('low', 'lowpass', 150), ('mid', 'bandpass', 550), ('high', 'highpass', 2000)]):
    src = mono
    if kind:
        flt = mk(C, audiofilterCHOP, 'filter_' + nm, -750, 600 - 120 * k)
        flt.inputConnectors[0].connect(mono)
        setmenu(flt, 'filter', kind)
        setmenu(flt, 'units', 'frequency')          # Hz (the default 'logarithmic' would ignore the cutoff below)
        trypar(flt, 'cutofffrequency', f0) or trypar(flt, 'cutoff', f0)
        src = flt
    an_ = mk(C, analyzeCHOP, 'rms_' + nm, -600, 600 - 120 * k)
    an_.inputConnectors[0].connect(src)
    setmenu(an_, 'function', 'rmspower', 'rms')
    rn = mk(C, renameCHOP, 'name_' + nm, -500, 600 - 120 * k)
    rn.inputConnectors[0].connect(an_)
    trypar(rn, 'renameto', nm)
    bands.inputConnectors[k].connect(rn)
tick = mk(C, constantCHOP, 'tick', -450, 300)
tick.par.name0 = 'frame'; tick.par.value0.expr = 'absTime.frame'
live = mk(C, scriptCHOP, 'live', -300, 450)
live.inputConnectors[0].connect(bands); live.inputConnectors[1].connect(tick)
drop_docked(live, ())                     # the Script CHOP brings its own example callbacks DAT; ours replaces it
lcb = mk(C, textDAT, 'live_callbacks', -300, 600)
lcb.text = '''# the live features: the levels of Ableton track "2" (or of the audio source) -> live_features.LiveFeatures
import math

def _band(c, key):
    vals = [ch.eval() for ch in c.chans() if key.lower() in ch.name.lower()] if c is not None else []
    return sum(vals) / len(vals) if vals else None

_S = {}          # state lives here, in memory (op.storage is saved into the .toe and cannot hold the analysis object)

def onSetupParameters(scriptOp):
    return

def onCook(scriptOp):
    p = scriptOp.parent()
    st = _S
    if st.get('lf') is None or p.par.Forcereset.eval():
        st['lf'] = mod('live_features').LiveFeatures()
        st['t'] = absTime.seconds
    lf = st['lf']
    now = absTime.seconds
    dt = min(0.1, max(1.0 / 240, now - st.get('t', now - 1.0 / 60)))
    st['t'] = now
    db = False
    if p.par.Source.eval() == 'ableton' and p.par.Abletonmode.eval() == 'meter':
        c = p.par.Abletonchop.eval()
        lv = [_band(c, k) for k in p.par.Abletonchans.eval().split()]
        lv = [v for v in lv if v is not None]
        v0 = float(sum(lv) / len(lv)) if lv else 0.0
        vals = [v0, v0, v0, v0]
    elif p.par.Source.eval() == 'ableton':
        c = p.par.Abletonchop.eval()
        keys = (p.par.Abletonchans.eval().split() + ['low', 'mid', 'high'])[:3]
        b = [_band(c, k) for k in keys]
        if all(v is None for v in b):                         # no bands: use whatever the CHOP has as the level
            v0 = float(c.chans()[0].eval()) if c is not None and c.numChans else 0.0
            b = [v0, v0, v0]
        b = [float(v) if v is not None else 0.0 for v in b]
        vals = [math.sqrt(b[0] ** 2 + b[1] ** 2 + b[2] ** 2)] + b
        db = bool(p.par.Abletondb.eval())
        if db:
            vals[0] = max(b)
    else:
        b = scriptOp.inputs[0]
        vals = [float(b[nm][b.numSamples - 1]) if b[nm] is not None else 0.0 for nm in ('level', 'low', 'mid', 'high')]
    f = lf.step(vals[0], vals[1], vals[2], vals[3], dt=dt, db=db, gain_db=float(p.par.Gain.eval()))
    scriptOp.clear()
    scriptOp.numSamples = 1
    for k, v in f.items():
        scriptOp.appendChan(k)[0] = v if (math.isfinite(v) and abs(v) > 1e-12) else 0.0
    return
'''
trypar(live, 'callbacks', 'live_callbacks')
mk(C, textDAT, 'readme', -800, 750).text = (
    '%s - built by build_ink.py (live)\n'
    'Source (Play page): ableton = the TDA_Audio_Analyzer levels of track "2" (Ableton CHOP), '
    'device = audio_in, file = the test file.\n'
    'live (Script CHOP) turns the level of the whole signal and 3 bands into the ink features (live_features.py).\n'
    % spec['TITLE'])

# ---------------------------------------------------------------- simulation (GPU feedback loop)
d_sim = shader(C, 'shader_sim', SH['sim'], -600, 400)
d_vert = shader(C, 'shader_vertex', SH['vertex'], -400, 400)
d_pix = shader(C, 'shader_pixel', SH['pixel'], -200, 400)
d_acc = shader(C, 'shader_accum', SH['accum'], 200, 400)
d_post = shader(C, 'shader_post', SH['post'], 600, 400)

seed = mk(C, constantTOP, 'seed', -800, 150)
setmenu(seed, 'outputresolution', 'custom')
trypar(seed, 'resolutionw', SIM_W); trypar(seed, 'resolutionh', SIM_H)
setmenu(seed, 'format', 'rgba32float', '32-bit float (rgba)')
for nm in ('colorr', 'colorg', 'colorb', 'alpha'):
    trypar(seed, nm, 0)

sim_fb = mk(C, feedbackTOP, 'sim_fb', -600, 150)
sim_fb.inputConnectors[0].connect(seed)
sim = mk(C, glslTOP, 'sim', -400, 150)
sim.inputConnectors[0].connect(sim_fb)
trypar(sim, 'pixeldat', d_sim.name)
setmenu(sim, 'format', 'rgba32float', '32-bit float (rgba)')
drop_docked(sim, ())
uniforms(sim, 'sim')
trypar(sim_fb, 'top', 'sim')

# ---------------------------------------------------------------- particles: 1x1 quad instanced once per texel
mat = mk(C, glslMAT, 'particle_mat', -400, -100)
trypar(mat, 'vdat', d_vert.name) or trypar(mat, 'vertexdat', d_vert.name)
trypar(mat, 'pdat', d_pix.name) or trypar(mat, 'pixeldat', d_pix.name)
drop_docked(mat, ())
trypar(mat, 'blending', True)
setmenu(mat, 'srcblend', 'one'); setmenu(mat, 'destblend', 'one')
trypar(mat, 'depthtest', False); trypar(mat, 'depthwriting', False)
setmenu(mat, 'cullface', 'neither', 'none', 'off')
try:
    mat.seq.sampler.numBlocks = 1
except Exception as e:
    ink_log.append('sampler seq: %s' % e)
trypar(mat, 'sampler0name', 'sState')
trypar(mat, 'sampler0top', 'sim') or trypar(mat, 'top0', 'sim')
uniforms(mat, 'mat')

geo = mk(C, geometryCOMP, 'particles', -200, -100)
for c in list(geo.children):
    c.destroy()
rect = geo.create(rectangleSOP, 'quad')
trypar(rect, 'sizex', 1); trypar(rect, 'sizey', 1)
rect.render = True; rect.display = True
trypar(geo, 'material', 'particle_mat')
trypar(geo, 'instancing', True)
setmenu(geo, 'instancecountmode', 'manual')
trypar(geo, 'numinstances', expr="max(1, int(%d * parent().par.Quality))" % (SIM_W * SIM_H))

cam = mk(C, cameraCOMP, 'cam', -200, 50)        # the Render TOP needs one; the vertex shader projects on its own

ren = mk(C, renderTOP, 'render', 0, -100)
trypar(ren, 'camera', 'cam'); trypar(ren, 'geometry', 'particles'); trypar(ren, 'lights', '')
setmenu(ren, 'outputresolution', 'custom'); trypar(ren, 'resolutionw', W); trypar(ren, 'resolutionh', H)
setmenu(ren, 'format', 'rgba32float', '32-bit float (rgba)')
for nm in ('bgcolorr', 'bgcolorg', 'bgcolorb', 'bgcolora'):
    trypar(ren, nm, 0)
setmenu(ren, 'antialias', 'aa1', '1x')

# ---------------------------------------------------------------- trails, bloom, tone map
acc_fb = mk(C, feedbackTOP, 'accum_fb', 0, 150)
acc_fb.inputConnectors[0].connect(ren)
acc = mk(C, glslTOP, 'accum', 200, -100)
acc.inputConnectors[0].connect(ren)
acc.inputConnectors[1].connect(acc_fb)
trypar(acc, 'pixeldat', d_acc.name)
setmenu(acc, 'format', 'rgba16float', '16-bit float (rgba)')
drop_docked(acc, ())
uniforms(acc, 'accum')
trypar(acc_fb, 'top', 'accum')

bloom = mk(C, blurTOP, 'blur', 400, 50)
bloom.inputConnectors[0].connect(acc)
trypar(bloom, 'size', expr='parent().par.%s' % spec['BLUR_PARAM'])

post = mk(C, glslTOP, 'post', 600, -100)
post.inputConnectors[0].connect(acc)
post.inputConnectors[1].connect(bloom)
trypar(post, 'pixeldat', d_post.name)
setmenu(post, 'format', 'rgba8fixed', '8-bit fixed (rgba)')
drop_docked(post, ())
uniforms(post, 'post')

out = mk(C, nullTOP, 'OUT', 800, -100)
out.inputConnectors[0].connect(post)
out.viewer = True
mk(C, outTOP, 'out1', 1000, -100).inputConnectors[0].connect(out)

# ---------------------------------------------------------------- the test file to the speakers (only while it is the source)
dev = mk(C, audiodeviceoutCHOP, 'speakers', -1050, 300)
dev.inputConnectors[0].connect(fin)
trypar(dev, 'active', expr="parent().par.Monitor and parent().par.Source == 'file'")
trypar(dev, 'volume', expr='parent().par.Volume')

pe = mk(C, parameterexecuteDAT, 'pulses', 800, -500)
pe.text = '''def onPulse(par):
	if par.name == 'Restart':
		p = par.owner
		p.par.Forcereset = True
		run("args[0].par.Forcereset = False", p, delayFrames=2)
	return
'''
trypar(pe, 'op', '..')
trypar(pe, 'pars', 'Restart')
trypar(pe, 'onpulse', True)
trypar(pe, 'valuechange', False)

C.save(D + '/%s.tox' % NAME)
# ---------------------------------------------------------------- the third layer: multiplied over the picture below it
mx = op('/project1/ink_layer')
if mx:
    mx.destroy()
P1 = op('/project1')
mx = P1.create(baseCOMP, 'ink_layer')
mx.nodeX, mx.nodeY = 900, -600
mx.color = (0.2, 0.2, 0.2)
under = mx.create(selectTOP, 'under'); under.nodeX, under.nodeY = 0, 100
trypar(under, 'top', UNDER)
inkt = mx.create(selectTOP, 'ink'); inkt.nodeX, inkt.nodeY = 0, -50
trypar(inkt, 'top', C.path + '/OUT')
small = mx.create(resolutionTOP, 'local'); small.nodeX, small.nodeY = 150, 200
small.inputConnectors[0].connect(under)
setmenu(small, 'outputresolution', 'custom'); trypar(small, 'resolutionw', 1); trypar(small, 'resolutionh', 1)
avg = mx.create(toptoCHOP, 'brightness'); avg.nodeX, avg.nodeY = 300, 300
trypar(avg, 'top', 'local')
lagc = mx.create(lagCHOP, 'brightness_slow'); lagc.nodeX, lagc.nodeY = 450, 300
lagc.inputConnectors[0].connect(avg)
trypar(lagc, 'lag1', 0.8); trypar(lagc, 'lag2', 0.8)
bpx = mx.create(textDAT, 'blend_pixel'); bpx.nodeX, bpx.nodeY = 300, 200
bpx.text = open(D + '/ink_layer.glsl').read()
xf = mx.create(glslTOP, 'blend'); xf.nodeX, xf.nodeY = 450, 50
xf.inputConnectors[0].connect(under); xf.inputConnectors[1].connect(inkt); xf.inputConnectors[2].connect(small)
trypar(xf, 'pixeldat', 'blend_pixel')
drop_docked(xf, ('blend_pixel',))
setmenu(xf, 'outputresolution', 'input')
try:
    xf.seq.vec.numBlocks = 2
except Exception as e:
    ink_log.append('blend vec: %s' % e)
trypar(xf, 'vec1name', 'uM')
trypar(xf, 'vec1valuex', 0)
trypar(xf, 'vec1valuey', expr="op('%s').par.Inktonelight" % C.path)
trypar(xf, 'vec1valuez', expr="op('%s').par.Inkmatch" % C.path)
trypar(xf, 'vec0name', 'uL')
trypar(xf, 'vec0valuex', expr="op('%s').par.Layeramount * op('%s/live')['presence']" % (C.path, C.path))
trypar(xf, 'vec0valuey', 0)
trypar(xf, 'vec0valuez', expr="op('%s').par.Inktone" % C.path)
trypar(xf, 'vec0valuew', expr="op('%s').par.Inkthreshold" % C.path)
o2 = mx.create(nullTOP, 'OUT'); o2.nodeX, o2.nodeY = 600, 50
o2.inputConnectors[0].connect(xf)
oo = mx.create(outTOP, 'out1'); oo.nodeX, oo.nodeY = 750, 50
oo.inputConnectors[0].connect(o2)
trypar(mx, 'opviewer', 'OUT')
v = op('/project1/viewer')
if v is not None and op('/project1/nin_stage') is None:     # with the NIN stage the viewer keeps showing it
    trypar(v, 'winop', mx.path + '/OUT')
print('INK layer: %s = %s + %s (Layeramount on %s); viewer -> %s' % (mx.path, UNDER, C.path + '/OUT', C.path, mx.path + '/OUT'))

print('ink_log', ink_log)
print('errors', [(o.path, o.errors()) for o in C.findChildren(depth=2) if o.errors()] or 'none')
print('warnings', [(o.path, o.warnings()) for o in C.findChildren(depth=2) if o.warnings()] or 'none')
print('INK built (live): %s @ %d fps, %d particles' % (C.path, FPS, SIM_W * SIM_H))
