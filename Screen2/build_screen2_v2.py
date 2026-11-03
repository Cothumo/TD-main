# Screen 2 - the live camera silhouette on a second screen (its own window, e.g. a second projector).
# It reads the silhouette that /project1/scenes already extracts from the camera (camera, mode, capture, threshold
# stay on the Silhouette page of scenes). In Main = False takes the figure out of the main scene.
# Rebuild: exec(open(project.folder + '/Screen2/build_screen2.py').read())
D = project.folder + '/Screen2'
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

old = op('/project1/screen2')
if old is not None:
    old.destroy()
C = P1.create(baseCOMP, 'screen2'); C.nodeX, C.nodeY = 600, -900
pg = C.appendCustomPage('Screen 2')
q = pg.appendToggle('Open', label='Open Window')[0]; q.default = False; q.val = False
q.help = 'open / close the second window (fills the second monitor when one is connected)'
q = pg.appendInt('Monitor')[0]; q.default = 1; q.val = 1; q.normMin = 0; q.normMax = 3
q.help = 'which monitor (0 = the main one, 1 = the second ...); without a second monitor it opens as a window'
q = pg.appendInt('Resolution', size=2)[0]
C.par.Resolution1.default = 1280; C.par.Resolution1.val = 1280; C.par.Resolution2.default = 720; C.par.Resolution2.val = 720
q = pg.appendToggle('Inmain', label='Figure In Main Scene')[0]; q.default = False; q.val = False
q.help = 'off = the figure is only on screen 2, on = on both'
def fl(nm, dv, lo, hi, hlp, label=None):
    q = (pg.appendFloat(nm, label=label) if label else pg.appendFloat(nm))[0]
    q.default = dv; q.val = dv; q.normMin = lo; q.normMax = hi; q.help = hlp
fl('Figure', 1.0, 0, 1, 'how dark and present the figure is')
fl('Echoes', 0.8, 0, 1, 'faint echoes trailing its movement')
fl('Rim', 1.0, 0, 2, 'its outline catches the light')
fl('Flow', 1.0, 0, 3, 'how much the haze flows round the body')
fl('Haze', 1.0, 0, 2.5, 'how thick the haze is (the pads, Stems, thicken it further)')
fl('Light', 1.0, 0, 2, 'brightness of the light behind the haze (breathes with the music)')
fl('Lightsize', 0.22, 0.03, 0.8, 'size of the light')
fl('Lightx', 0.5, 0, 1, 'where the light is, left - right')
fl('Lighty', 0.62, 0, 1, 'where the light is, bottom - top')
fl('Scale', 1.0, 0.2, 3, 'size of the figure (1 = the camera fills the screen)')
fl('X', 0.0, -1, 1, 'move the figure left / right')
fl('Y', 0.0, -1, 1, 'move the figure down / up')
q = pg.appendToggle('Mirror')[0]; q.default = True; q.val = True
fl('Noise', 0.7, 0, 1, 'where the figure moved its traces break up into analog noise (grain, line noise) and dissolve')
fl('Tear', 0.6, 0, 2, 'while it moves its rows tear sideways like a bad signal')
fl('Ghosts', 0.8, 0, 1, 'older copies of the figure drift behind it')
fl('Ghostdelay', 1.0, 0.3, 3, 'how far back the ghosts are (1 = about 0.1, 0.25 and 0.5 s)')
fl('Scanlines', 0.4, 0, 1, 'faint scanlines over the screen')
fl('Detail', 0.6, 0, 2, 'faint features inside the figure (its relief from the camera catches a little light)')

src = C.create(selectTOP, 'sil'); src.nodeX, src.nodeY = -400, 0
sp(src, 'top', '/project1/scenes/sil')
px = C.create(textDAT, 'screen2_pixel'); px.nodeX, px.nodeY = -200, -150
px.text = open(D + '/screen2.glsl').read()
g = C.create(glslTOP, 'screen2'); g.nodeX, g.nodeY = -200, 0
sp(g, 'pixeldat', px.name)
for dd in list(g.docked):
    if dd.name != px.name:
        try: dd.destroy()
        except Exception: pass
g.inputConnectors[0].connect(src)
# the ghosts: older bodies from a cache of the silhouette, packed into one picture (r, g, b = older and older)
cache = C.create(cacheTOP, 'sil_cache'); cache.nodeX, cache.nodeY = -600, -300
cache.inputConnectors[0].connect(src)
sp(cache, 'cachesize', 100)
cs = []
for k, d in enumerate((6, 15, 30)):
    s_ = C.create(cacheselectTOP, 'ghost%d' % (k + 1)); s_.nodeX, s_.nodeY = -400, -300 - 120 * k
    sp(s_, 'cachetop', 'sil_cache')
    sp(s_, 'index', expr='-int(round(%d * parent().par.Ghostdelay))' % d)
    cs.append(s_)
gpx = C.create(textDAT, 'ghost_pixel'); gpx.nodeX, gpx.nodeY = -200, -450
gpx.text = open(D + '/ghost_pack.glsl').read()
gp = C.create(glslTOP, 'ghosts'); gp.nodeX, gp.nodeY = -200, -300
sp(gp, 'pixeldat', gpx.name)
for dd in list(gp.docked):
    if dd.name != gpx.name:
        try: dd.destroy()
        except Exception: pass
for k, s_ in enumerate(cs):
    run("op(args[0]).inputConnectors[args[1]].connect(op(args[2]))", gp.path, k, s_.path, delayFrames=1 + 2 * k)
run("op(args[0]).inputConnectors[1].connect(op(args[1]))", g.path, gp.path, delayFrames=3)
camsel = C.create(selectTOP, 'camera'); camsel.nodeX, camsel.nodeY = -400, 150
sp(camsel, 'top', '/project1/scenes/cam_small')
run("op(args[0]).inputConnectors[2].connect(op(args[1]))", g.path, camsel.path, delayFrames=6)
sp(g, 'outputresolution', 'custom')
sp(g, 'resolutionw', expr='parent().par.Resolution1')
sp(g, 'resolutionh', expr='parent().par.Resolution2')
STEM = "(op('/project1/stems/out')['pads'].eval() if op('/project1/stems/out') is not None and op('/project1/stems/out')['pads'] is not None else 0.0)"
LVL = "(op('/project1/nin_stage/echo')['slevel'].eval() if op('/project1/nin_stage/echo') is not None and op('/project1/nin_stage/echo')['slevel'] is not None else 0.0)"
P = 'parent().par.'
U = [('uA', ['absTime.seconds % 10000', P + 'Figure', P + 'Echoes', '1.0 if parent().par.Mirror else 0.0']),
     ('uB', [STEM, LVL, P + 'Haze', P + 'Lightsize']),
     ('uC', [P + 'Lightx', P + 'Lighty', P + 'Scale', P + 'Rim']),
     ('uD', [P + 'X', P + 'Y', P + 'Flow', P + 'Light']),
     ('uE', [P + 'Noise', P + 'Tear', P + 'Ghosts', P + 'Scanlines']),
     ('uF', [P + 'Detail', '0', '0', '0'])]
g.seq.vec.numBlocks = len(U)
for i, (nm, ex_) in enumerate(U):
    getattr(g.par, 'vec%dname' % i).val = nm
    for ch, e in zip('xyzw', ex_):
        getattr(g.par, 'vec%dvalue%s' % (i, ch)).expr = e
o = C.create(nullTOP, 'OUT'); o.nodeX, o.nodeY = 0, 0; o.inputConnectors[0].connect(g); o.viewer = True
sp(C, 'opviewer', 'OUT')

w = C.create(windowCOMP, 'window2'); w.nodeX, w.nodeY = 200, 0
sp(w, 'winop', C.path + '/OUT')
sp(w, 'location', 'specifydisplay')
sp(w, 'monitor', expr='min(parent().par.Monitor.eval(), len(monitors) - 1)')
sp(w, 'size', expr="'fill' if len(monitors) > parent().par.Monitor.eval() and parent().par.Monitor.eval() > 0 else 'custom'")
sp(w, 'winw', 960); sp(w, 'winh', 540)
sp(w, 'borders', expr="not (len(monitors) > parent().par.Monitor.eval() and parent().par.Monitor.eval() > 0)")
pe = C.create(parameterexecuteDAT, 'window_pexec'); pe.nodeX, pe.nodeY = 200, -150
pe.text = ("def onValueChange(par, prev):\n"
           "\tw = par.owner.op('window2')\n"
           "\tif par.eval():\n\t\tw.par.winopen.pulse()\n"
           "\telse:\n\t\tw.par.winclose.pulse()\n"
           "\treturn\n")
sp(pe, 'op', '..'); sp(pe, 'pars', 'Open'); sp(pe, 'valuechange', True)

# the main scene keeps the figure only when Figure In Main Scene is on
scn = op('/project1/scenes/scenes')
if scn is not None:
    sp(scn, 'vec0valuew', expr="(parent().par.Silhouette if parent().par.Cameraon else 0.0) * (1.0 if op('/project1/screen2') is None or op('/project1/screen2').par.Inmain else 0.0)")
else:
    log.append('no scenes')
run("op(args[0]).save(args[1])", C.path, D + '/screen2.tox', delayFrames=10)
print('SCREEN 2 built: %s | monitors %d | log %s' % (C.path, len(monitors), log or 'none'))
