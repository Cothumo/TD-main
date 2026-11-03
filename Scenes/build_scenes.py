# Scenes - backlit haze and the live camera silhouette (NIN live performance elements).
# Chain: ink_layer -> nin_stage -> scenes -> sphere -> viewer. The acts of nin_stage now have 5 acts:
#   1 Static, 2 Melt, 3 Scrim, 4 Backlit haze  (the silhouette is in every act).
# Rebuild: exec(open(project.folder + '/Scenes/build_scenes.py').read())
import math

D = project.folder + '/Scenes'
P1 = op('/project1')
SRC = '/project1/nin_stage/OUT' if op('/project1/nin_stage') is not None else '/project1/ink_layer/OUT'
log = []

def sp(n, name, val=None, expr=None):
    p = getattr(n.par, name, None)
    if p is None:
        log.append('%s.%s missing' % (n.name, name)); return
    try:
        if expr is not None:
            p.expr = expr
        else:
            p.val = val
    except Exception as e:
        log.append('%s.%s: %s' % (n.name, name, e))

old = op('/project1/scenes')
if old is not None:
    old.destroy()
C = P1.create(baseCOMP, 'scenes'); C.nodeX, C.nodeY = 200, -900

def mk(ty, name, x, y):
    n = C.create(ty, name); n.nodeX, n.nodeY = x, y; return n

def drop_docked(n):
    try:
        for dd in list(n.docked):
            dd.destroy()
    except Exception:
        pass

# ---------------- parameters
pg = C.appendCustomPage('Scenes')
def fl(page, nm, dv, lo, hi, hlp, label=None):
    q = page.appendFloat(nm, label=label)[0] if label else page.appendFloat(nm)[0]
    q.default = dv; q.val = dv; q.normMin = lo; q.normMax = hi; q.help = hlp
    return q
fl(pg, 'Backlight', 0.0, 0, 1, 'Backlit haze: one soft light far behind drifting haze, the scene dark against it (the acts set it: act 5)')
fl(pg, 'Hazedensity', 1.0, 0, 2.5, 'how thick the haze is (the pads, Stems, thicken it further)')
fl(pg, 'Lightsize', 0.2, 0.03, 0.8, 'size of the light behind the haze (fraction of the frame width)')
fl(pg, 'Lightx', 0.5, 0, 1, 'where the light is, left - right')
fl(pg, 'Lighty', 0.64, 0, 1, 'where the light is, bottom - top')
ps = C.appendCustomPage('Silhouette')
fl(ps, 'Silhouette', 0.7, 0, 1, 'the live camera silhouette in the scene (0 = off)')
q = ps.appendToggle('Cameraon', label='Camera On')[0]; q.default = True; q.val = True
cam_probe = C.create(videodeviceinTOP, '_probe')
labels = list(cam_probe.par.device.menuLabels)
cam_probe.destroy()
q = ps.appendStrMenu('Camera')[0]
q.menuNames = labels or ['Integrated Camera']; q.menuLabels = labels or ['Integrated Camera']
want = globals().get('SCENES_CAMERA', 'Integrated Camera')
q.default = want if want in (labels or [want]) else (labels[0] if labels else want); q.val = q.default
q = ps.appendMenu('Mode')[0]
q.menuNames = ['ai', 'difference', 'dark']
q.menuLabels = ['AI person detection (NVIDIA RTX + Video Effects SDK; falls back to Difference if unavailable)',
                'Difference from the empty stage (press Capture with nobody in view)', 'Dark figure (performer lit from behind)']
q.default = 'ai'; q.val = 'ai'
ps.appendPulse('Capture', label='Capture Empty Stage')
fl(ps, 'Learn', 40.0, 0, 300, 'seconds the empty stage takes to be learned slowly (0 = only on Capture)')
fl(ps, 'Threshold', 0.14, 0.01, 0.8, 'how different from the background (or how dark) a pixel must be to count as the performer')
fl(ps, 'Softness', 0.15, 0.005, 1.0, 'soft edge of the figure')
fl(ps, 'Silscale', 1.0, 0.2, 3, 'size of the figure (1 = the camera fills the frame height)')
fl(ps, 'Silx', 0.0, -1, 1, 'move the figure left / right')
fl(ps, 'Sily', 0.0, -1, 1, 'move the figure down / up')
q = ps.appendToggle('Mirror')[0]; q.default = True; q.val = True
fl(ps, 'Silflow', 1.0, 0, 3, 'how much the picture flows round the body')
fl(ps, 'Silhouettedark', 0.85, 0, 1, 'how dark the figure is')
fl(ps, 'Siltrail', 0.7, 0, 1, 'faint echoes trailing its movement')
fl(ps, 'Trailtime', 1.5, 0.1, 8, 'seconds the echoes take to fade')

def shader(name, fname, x, y):
    px = mk(textDAT, name + '_pixel', x, y - 150); px.text = open(D + '/' + fname).read()
    g = mk(glslTOP, name, x, y)
    sp(g, 'pixeldat', px.name)
    for dd in list(g.docked):
        if dd.name != px.name:
            try: dd.destroy()
            except Exception: pass
    return g

def uniforms(g, U):
    g.seq.vec.numBlocks = len(U)
    for i, (nm, ex_) in enumerate(U):
        getattr(g.par, 'vec%dname' % i).val = nm
        for ch, e in zip('xyzw', ex_):
            getattr(g.par, 'vec%dvalue%s' % (i, ch)).expr = e

# ---------------- the live silhouette
cam = mk(videodeviceinTOP, 'cam', -1200, -500)
# the laptop camera runs at 640 x 360: with the phone camera (camera2) running at the same time, a higher format
# leaves one of the two stuck 'Initializing' (USB bandwidth)
def _fmt640():
    try:
        d = dict(zip(cam.par.signalformat.menuLabels, cam.par.signalformat.menuNames))
        k = [l for l in d if l.startswith('640x360p 30')]
        if k: cam.par.signalformat = d[k[0]]
    except Exception:
        pass
run("args[0]()", _fmt640, delayFrames=30)
sp(cam, 'active', expr="parent().par.Cameraon and parent().par.Silhouette > 0")
for n_, l_ in zip(cam.par.device.menuNames, cam.par.device.menuLabels):
    if l_ == C.par.Camera.eval():
        cam.par.device = n_
pe = mk(parameterexecuteDAT, 'camera_pexec', -1200, -350)
pe.text = ("def onValueChange(par, prev):\n"
           "\tif par.name == 'Camera':\n"
           "\t\tc = par.owner.op('cam')\n"
           "\t\tfor n_, l_ in zip(c.par.device.menuNames, c.par.device.menuLabels):\n"
           "\t\t\tif l_ == par.eval():\n\t\t\t\tc.par.device = n_\n"
           "\tif par.name == 'Mode':\n\t\tn = par.owner.op('nv')\n\t\tif n is not None:\n\t\t\tn.bypass = par.eval() != 'ai'\n"
           "\treturn\n"
           "def onPulse(par):\n"
           "\tif par.name == 'Capture':\n\t\tpar.owner.store('cap', 3)\n"
           "\treturn\n")
sp(pe, 'op', '..'); sp(pe, 'pars', 'Camera Capture Mode'); sp(pe, 'valuechange', True); sp(pe, 'onpulse', True)
lo = mk(resolutionTOP, 'cam_small', -1000, -500); lo.inputConnectors[0].connect(cam)
sp(lo, 'outputresolution', 'custom'); sp(lo, 'resolutionw', 640); sp(lo, 'resolutionh', 360)   # 640 x 360: a detailed outline
bgfb = mk(feedbackTOP, 'bg_fb', -800, -650); bgfb.inputConnectors[0].connect(lo)
bg = shader('bg', 'sil_bg.glsl', -800, -500)
sp(bg, 'format', 'rgba16float')
sp(bgfb, 'top', 'bg')
uniforms(bg, [('uR', ["1.0 if parent().fetch('cap', 0, search=False) > 0 else (0.0 if parent().par.Learn <= 0 else 1.0 / (60.0 * parent().par.Learn))", '0', '0', '0'])])
C.store('cap', 30)          # learn the stage straight away at the start
dif = shader('diff', 'sil_diff.glsl', -600, -500)
# AI person detection: NVIDIA Background TOP (needs an RTX card and NVIDIA's Video Effects SDK); if it reports an
# error the silhouette falls back to the difference from the empty stage
nvi = mk(resolutionTOP, 'nv_in', -1000, -950); nvi.inputConnectors[0].connect(cam)   # the AI needs >= 512 px wide, whatever the camera gives
sp(nvi, 'outputresolution', 'custom'); sp(nvi, 'resolutionw', 960); sp(nvi, 'resolutionh', 540)
nv = mk(nvidiabackgroundTOP, 'nv', -800, -800); nv.inputConnectors[0].connect(nvi)
sp(nv, 'mode', 'quality'); sp(nv, 'segment', 'foreground')
nv.bypass = C.par.Mode.eval() != 'ai'   # the camera_pexec switches it with the Mode
uniforms(dif, [('uM', ["2.0 if (parent().par.Mode == 'ai' and not op('nv').errors()) else (1.0 if parent().par.Mode == 'dark' else 0.0)", '0', '0', '0'])])
bl = mk(blurTOP, 'diff_blur', -400, -500); bl.inputConnectors[0].connect(dif)
sp(bl, 'size', 4)
trfb = mk(feedbackTOP, 'trail_fb', -200, -650); trfb.inputConnectors[0].connect(bl)
tr = shader('trail', 'sil_trail.glsl', -200, -500)
sp(tr, 'format', 'rgba16float')
sp(trfb, 'top', 'trail')
uniforms(tr, [('uT', ['parent().par.Threshold', 'parent().par.Softness',
                      'math.exp(-1.0 / (60.0 * max(parent().par.Trailtime, 0.05)))',
                      "1.0 if (parent().par.Cameraon and parent().par.Silhouette > 0) else 0.0"])])
wide = mk(blurTOP, 'mask_wide', 0, -650); wide.inputConnectors[0].connect(tr)
sp(wide, 'size', 18)
fill = shader('fill', 'sil_fill.glsl', 0, -500)      # closes the holes inside the figure
silo = mk(nullTOP, 'sil', 200, -500); silo.inputConnectors[0].connect(fill)
cx = mk(executeDAT, 'cap_exec', -1000, -350)
# self-repair: if almost the whole frame counts as the figure for 2 s (the empty stage was lost, e.g. after a
# reset), the empty stage is captured again
can = mk(analyzeTOP, 'cover_an', 400, -650); can.inputConnectors[0].connect(silo); sp(can, 'op', 'average')
cov = mk(toptoCHOP, 'cover', 600, -650); sp(cov, 'top', 'cover_an')
cx.text = ("_S = {'n': 0}\n"
           "def onFrameEnd(frame):\n\tc = me.parent()\n\tn = c.fetch('cap', 0, search=False)\n\tif n > 0:\n\t\tc.store('cap', n - 1)\n"
           "\tv = c.op('cover')\n\tr = float(v['r']) if v is not None and v['r'] is not None else 0.0\n"
           "\t_S['n'] = _S['n'] + 1 if r > 0.7 else 0\n\tif _S['n'] > 120:\n\t\tc.store('cap', 3); _S['n'] = 0\n\treturn\n")
sp(cx, 'frameend', True); sp(cx, 'active', True)

# ---------------- the scenes shader
src = mk(selectTOP, 'src', -400, 0); sp(src, 'top', SRC)
g = shader('scenes', 'scenes.glsl', 0, 0)
sp(g, 'outputresolution', 'useinput')
STEM = "(op('/project1/stems/out')['pads'].eval() if op('/project1/stems/out') is not None and op('/project1/stems/out')['pads'] is not None else 0.0)"
LVL = "(op('/project1/nin_stage/echo')['slevel'].eval() if op('/project1/nin_stage/echo') is not None and op('/project1/nin_stage/echo')['slevel'] is not None else 0.0)"
P = 'parent().par.'
uniforms(g, [('uA', ['absTime.seconds % 10000', '0', P + 'Backlight', "(parent().par.Silhouette if parent().par.Cameraon else 0.0) * (1.0 if op('/project1/screen2') is None or op('/project1/screen2').par.Inmain else 0.0)"]),
             ('uB', [STEM, LVL, P + 'Hazedensity', P + 'Lightsize']),
             ('uC', [P + 'Lightx', P + 'Lighty', P + 'Silhouettedark', P + 'Siltrail']),
             ('uD', [P + 'Silscale', P + 'Silx', P + 'Sily', "1.0 if parent().par.Mirror else 0.0"]),
             ('uE', ['0', '0', '0', P + 'Silflow'])])
o = mk(nullTOP, 'OUT', 200, 0); o.inputConnectors[0].connect(g); o.viewer = True
oo = mk(outTOP, 'out1', 400, 0); oo.inputConnectors[0].connect(o)
sp(C, 'opviewer', 'OUT')
# GLSL TOP input connectors appear one per frame: connect them over the next frames
run("o = op(args[0]); o.inputConnectors[0].connect(op(args[1]))", bg.path, lo.path, delayFrames=1)
run("o = op(args[0]); o.inputConnectors[1].connect(op(args[1]))", bg.path, bgfb.path, delayFrames=3)
run("o = op(args[0]); o.inputConnectors[0].connect(op(args[1]))", dif.path, lo.path, delayFrames=1)
run("o = op(args[0]); o.inputConnectors[1].connect(op(args[1]))", dif.path, bg.path, delayFrames=3)
run("o = op(args[0]); o.inputConnectors[2].connect(op(args[1]))", dif.path, nv.path, delayFrames=5)
run("o = op(args[0]); o.inputConnectors[0].connect(op(args[1]))", tr.path, bl.path, delayFrames=1)
run("o = op(args[0]); o.inputConnectors[1].connect(op(args[1]))", tr.path, trfb.path, delayFrames=3)
run("o = op(args[0]); o.inputConnectors[0].connect(op(args[1]))", fill.path, tr.path, delayFrames=1)
run("o = op(args[0]); o.inputConnectors[1].connect(op(args[1]))", fill.path, wide.path, delayFrames=3)
run("o = op(args[0]); o.inputConnectors[0].connect(op(args[1]))", g.path, src.path, delayFrames=1)
run("o = op(args[0]); o.inputConnectors[1].connect(op(args[1]))", g.path, silo.path, delayFrames=3)

# ---------------- into the chain: the sphere now reads the scenes
s = op('/project1/sphere/src')
if s is not None:
    sp(s, 'top', C.path + '/OUT')
else:
    v = op('/project1/viewer')
    if v is not None:
        sp(v, 'winop', C.path + '/OUT')

# ---------------- 4 acts in nin_stage (4 Backlit haze)
ACTS_TEXT = '''ACTS = {
    '1': {'Static': 0.85, 'Melt': 0.0, 'Warp': 0.15, 'Scrim': 0.25, 'Ghost': 0.15, 'Echo': 0.45, 'Ripple': 0.3,
          'Parallax': 0.5, 'Haze': 0.3, 'Darkness': 0.55, 'ink:Layeramount': 0.4, 'scenes:Backlight': 0.0},
    '2': {'Static': 0.1, 'Melt': 0.85, 'Warp': 0.8, 'Scrim': 0.3, 'Ghost': 0.2, 'Echo': 0.6, 'Ripple': 0.4,
          'Parallax': 0.7, 'Haze': 0.4, 'Darkness': 0.6, 'ink:Layeramount': 0.45, 'scenes:Backlight': 0.0},
    '3': {'Static': 0.0, 'Melt': 0.0, 'Warp': 0.6, 'Scrim': 1.0, 'Ghost': 0.9, 'Echo': 0.6, 'Ripple': 1.0,
          'Parallax': 1.4, 'Haze': 0.6, 'Darkness': 0.4, 'ink:Layeramount': 0.55, 'scenes:Backlight': 0.0},
    '4': {'Static': 0.0, 'Melt': 0.3, 'Warp': 0.3, 'Scrim': 0.15, 'Ghost': 0.2, 'Echo': 0.4, 'Ripple': 0.3,
          'Parallax': 0.5, 'Haze': 0.5, 'Darkness': 0.35, 'ink:Layeramount': 0.5, 'scenes:Backlight': 1.0},
}'''
ACT_LABELS = ['1 Static (analog signal breaking up)', '2 Melt (feedback trails, noise warp)', '3 Scrim (layered projection, heat haze)',
              '4 Backlit haze (one light behind the haze)']

def patch_acts_text(t):
    i = t.index('ACTS = {'); j = t.index('\n}', i) + 2
    t = t[:i] + ACTS_TEXT + t[j:]
    t = t.replace('% 3 + 1', '% len(ACTS) + 1')
    if "name.startswith('scenes:')" not in t:
        t = t.replace("        else:\n            par = getattr(C.par, name, None)",
                      "        elif name.startswith('scenes:'):\n            o = op('/project1/scenes'); par = getattr(o.par, name[7:], None) if o is not None else None\n"
                      "        else:\n            par = getattr(C.par, name, None)")
    return t.replace('# the three acts:', '# the four acts:')

N = op('/project1/nin_stage')
if N is not None:
    a = N.op('acts')
    a.text = patch_acts_text(a.text)
    N.par.Act.menuNames = ['1', '2', '3', '4']; N.par.Act.menuLabels = ACT_LABELS
    pa = N.par.Act1.page
    if not hasattr(N.par, 'Act4'):
        pa.appendPulse('Act4', label='Go to Act 4')
    if hasattr(N.par, 'Act5'):
        N.par.Act5.destroy()
    if N.par.Act.eval() not in ('1', '2', '3', '4'):
        N.par.Act = '4'
    try:
        N.par.Actsource.menuLabels = ['Auto (1 > 2 > 3 > 4 > 1 ... every Act Duration, on a hit)', 'Manual (the Act menu / buttons)',
                                      'Ableton scene launches (scene 1 = act 1, 5 = act 1 again)']
    except Exception as e:
        log.append('labels: %s' % e)
    for d in N.children:
        if d.OPType == 'parameterexecuteDAT' and 'Act1' in d.par.pars.eval():
            d.par.pars = 'Act1 Act2 Act3 Act4'
    N.save(project.folder + '/nin_stage.tox')
else:
    log.append('no nin_stage: acts not extended')
run("op(args[0]).save(args[1])", C.path, D + '/scenes.tox', delayFrames=8)   # after the inputs are connected
print('SCENES built: %s (from %s) -> %s | log %s' % (C.path, SRC, 'sphere' if s is not None else 'viewer', log or 'none'))
