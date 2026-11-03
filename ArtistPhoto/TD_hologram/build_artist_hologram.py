# Artist Hologram - the artist photo as a hologram hidden in a particle stream (the TouchDesigner version of
# ArtistPhoto/artist_head_hologram_loop.mp4), built from the Screen 2 silhouette look + the Ambient Ink vibration.
#
# Run it inside the open project (Textport, Alt+T):
#   exec(open(project.folder + '/ArtistPhoto/TD_hologram/build_artist_hologram.py').read())
# or drag this file into the network and right-click the Text DAT > Run Script. If it cannot find its own folder:
#   HOLO_DIR = r'C:/.../TD_hologram'      (first, then run it)
# It builds /project1/artist_hologram (rebuilt on every run, nothing else in the project is touched) and saves
# artist_hologram.tox next to this file - drag that .tox into any later project.
# Everything runs live on the GPU: two particle simulations (GLSL TOP feedback loops, one texel per particle), drawn
# as instanced sprites (GLSL MAT) and finished by a GLSL post shader. View OUT; 'Record Loop' writes one loop to disk.
import os


def _own_folder():
    try:
        f = me.par.file.eval()
        if f and os.path.exists(f):
            return os.path.dirname(os.path.abspath(f))
    except Exception:
        pass
    return None


D = (globals().get('HOLO_DIR') or _own_folder() or project.folder + '/ArtistPhoto/TD_hologram').replace('\\', '/').rstrip('/')
holo_log = []
SIZE = 1080                 # square output (the Non-Commercial licence allows up to 1280)
STREAM_RES = 512            # 512 x 512 = 262,144 stream particles
HEAD_RES = 512              # 262,144 candidates for the head's own particles (about a fifth are in use at a time)


def trypar(n, name, val=None, expr=None):
    try:
        p = getattr(n.par, name)
        if expr is not None:
            p.expr = expr
        else:
            p.val = val
        return True
    except Exception as e:
        holo_log.append('%s.%s: %s' % (n.name, name, e))
        return False


def setmenu(n, name, *keys):
    try:
        p = getattr(n.par, name)
        for k in keys:
            for m in p.menuNames:
                if k == m.lower() or k in m.lower():
                    p.val = m
                    return m
        holo_log.append('%s.%s no match in %s' % (n.name, name, p.menuNames[:12]))
    except Exception as e:
        holo_log.append('%s.%s: %s' % (n.name, name, e))


def mk(parent, ty, name, x, y):
    n = parent.create(ty, name)
    n.nodeX, n.nodeY = x, y
    return n


COMMON = open(D + '/holo_common.glsl').read()


def shader(parent, name, fname, x, y, common=True):
    t = mk(parent, textDAT, name, x, y)
    t.text = (COMMON + '\n' if common else '') + open(D + '/' + fname).read()
    return t


def drop_docked(n, keep=()):
    try:
        for d in list(n.docked):
            if d.name not in keep:
                d.destroy()
    except Exception as e:
        holo_log.append('%s docked: %s' % (n.name, e))


P = 'parent().par.'
TIME = "((absTime.seconds - parent().par.Timeoffset) % max(0.1, parent().par.Loop))"
HIT = ("(op('/project1/nin_stage/echo')['env'].eval() if parent().par.Hits == 'nin' and op('/project1/nin_stage/echo') "
       "is not None and op('/project1/nin_stage/echo')['env'] is not None else -1.0)")
COMMON_U = [
    ('uTime', [TIME, P + 'Loop', '1.0 / max(1, project.cookRate)', 'absTime.seconds % 100000']),
    ('uApp', [P + 'Appear1', P + 'Strength1', P + 'Appear2', P + 'Strength2']),
    ('uEnv', [P + 'Rise', P + 'Linger', P + 'Fall', HIT]),
    ('uBur', [P + 'Burst1', P + 'Burst2', 'absTime.frame', '0']),
]


def uniforms(g, extra):
    U = COMMON_U + extra
    try:
        g.seq.vec.numBlocks = len(U)
    except Exception as e:
        holo_log.append('%s vec seq: %s' % (g.name, e))
    for i, (nm, exprs) in enumerate(U):
        trypar(g, 'vec%dname' % i, nm)
        for c, ex in zip('xyzw', exprs):
            trypar(g, 'vec%dvalue%s' % (i, c), expr=ex)


def glsl_top(parent, name, dat, x, y, fmt=('rgba16float', '16-bit float (rgba)'), res=None):
    g = mk(parent, glslTOP, name, x, y)
    trypar(g, 'pixeldat', dat.name)
    drop_docked(g)
    setmenu(g, 'format', *fmt)
    if res:
        setmenu(g, 'outputresolution', 'custom')
        trypar(g, 'resolutionw', res[0]); trypar(g, 'resolutionh', res[1])
    return g


def blur(parent, name, src, size, x, y):
    b = mk(parent, blurTOP, name, x, y)
    b.inputConnectors[0].connect(src)
    trypar(b, 'size', size)
    return b


# ---------------------------------------------------------------- component + parameters
old = op('/project1/artist_hologram')
if old:
    old.destroy()
C = op('/project1').create(baseCOMP, 'artist_hologram')
C.nodeX, C.nodeY = 900, -1100
C.color = (0.25, 0.35, 0.45)

pg = C.appendCustomPage('Hologram')


def fl(page, nm, dv, lo, hi, hlp, label=None):
    q = (page.appendFloat(nm, label=label) if label else page.appendFloat(nm))[0]
    q.default = dv; q.val = dv; q.normMin = lo; q.normMax = hi; q.help = hlp
    return q


fl(pg, 'Streamglow', 1.2, 0, 3, 'brightness of the stream outside the head')
fl(pg, 'Figure', 0.68, 0, 1, 'the head is a dark form in the stream (the Screen 2 figure): how much darker it gets at the peak')
fl(pg, 'Headglow', 0.07, 0, 1, 'faint light left inside the head volume')
fl(pg, 'Rim', 1.5, 0, 4, 'the outline catches the light (Screen 2 rim)')
fl(pg, 'Flow', 0.85, 0, 3, 'the haze flows round the head: the outline wobbles and breathes')
fl(pg, 'Tear', 1.0, 0, 3, 'rows of the outline tear sideways now and then (more on hits)')
fl(pg, 'Echoes', 1.0, 0, 2, 'two faint older outlines trailing behind it')
fl(pg, 'Detail', 0.22, 0, 1, 'faint soft relief inside the head (the photo highlights only, no traced features)')
fl(pg, 'Streamspeed', 165.0, 0, 600, 'speed of the stream, left -> right (px/s at 720 high)')
fl(pg, 'Headslow', 0.6, 0, 1, 'while the face is present the stream slows down inside the head (it gathers there)')
fl(pg, 'Turbulence', 1.0, 0, 3, 'curl-noise swirls in the stream')
fl(pg, 'Particlesize', 0.9, 0.3, 4, 'sprite radius (px at 720 high)')
fl(pg, 'Particlehold', 2.6, 0.3, 6, "seconds the head's own particles rest on it before they fly off (the back of the head goes first)")
fl(pg, 'Gain', 1.25, 0, 4, 'exposure of the light')
fl(pg, 'Bloom', 0.6, 0, 2, 'glow around the light')
fl(pg, 'Scanlines', 0.3, 0, 1, 'projection scanlines')
fl(pg, 'Scanband', 1.0, 0, 3, 'bright band rolling up through the hologram (twice per loop)')
fl(pg, 'Flicker', 0.06, 0, 0.5, 'hologram flicker (and a rare short dip)')
fl(pg, 'Slices', 0.6, 0, 3, 'horizontal slices glitching sideways (more on hits)')
fl(pg, 'Chroma', 1.6, 0, 8, 'RGB split in px at 720 high (more on hits)')
fl(pg, 'Vibration', 1.5, 0, 3, 'Ambient Ink vibration on the light: jitter, oscillation, row wobble, trailing second image')
fl(pg, 'Backlight', 0.32, 0, 2, 'the dim Screen 2 haze and its far light behind')
tint = pg.appendRGB('Tint')
for k, v in enumerate((0.84, 0.97, 1.08)):
    tint[k].default = v; tint[k].val = v
tint[0].help = 'colour of the light (1, 1, 1 = grey like Screen 2)'

tp = C.appendCustomPage('Timing')
fl(tp, 'Loop', 7.0, 1, 30, 'loop length (s): every timing below repeats with it')
fl(tp, 'Appear1', 0.15, 0, 30, 'when the face starts to surface (s in the loop)')
fl(tp, 'Strength1', 0.78, 0, 1, 'how clearly it shows (1 = full)')
fl(tp, 'Appear2', 3.45, 0, 30, 'second appearance (s in the loop)')
fl(tp, 'Strength2', 0.55, 0, 1, 'how clearly it shows the second time (0 = only one appearance)')
fl(tp, 'Rise', 1.4, 0.05, 5, 'seconds it takes to surface (eased in)')
fl(tp, 'Linger', 0.3, 0, 5, 'seconds it stays')
fl(tp, 'Fall', 1.8, 0.05, 5, 'seconds it takes to sink back into the stream')
fl(tp, 'Burst1', 1.55, 0, 30, 'first unstable moment (s): gust, vibration, glitches peak')
fl(tp, 'Burst2', 4.85, 0, 30, 'second unstable moment (s)')
q = tp.appendMenu('Hits')[0]
q.menuNames = ['loop', 'nin']
q.menuLabels = ['Loop timing (Burst1 / Burst2)', 'NIN stage hits (/project1/nin_stage/echo env)']
q.default = 'loop'; q.val = 'loop'
q.help = 'what drives the gusts, vibration and glitches: the loop or the music hits of nin_stage'

op_ = C.appendCustomPage('Output')
q = op_.appendFile('Recordfile', label='Record File')[0]
q.default = D + '/artist_hologram_loop.mov'; q.val = q.default
op_.appendPulse('Recordloop', label='Record Loop')
op_.appendPulse('Restart', label='Restart Particles')
q = op_.appendToggle('Forcereset')[0]; q.val = False
q = op_.appendFloat('Timeoffset')[0]; q.val = 0.0
q.help = 'the loop starts at this absolute time (set by Record Loop)'

# ---------------------------------------------------------------- the photo, placed; the head's static maps
photo = mk(C, moviefileinTOP, 'photo', -1400, 600)
trypar(photo, 'file', D + '/artist_photo.jpg')
mask = mk(C, moviefileinTOP, 'mask', -1400, 450)
trypar(mask, 'file', D + '/head_mask.png')
d_place = shader(C, 'shader_place', 'holo_place.glsl', -1250, 750, common=False)
place = glsl_top(C, 'place', d_place, -1250, 520, res=(SIZE, SIZE))
place.inputConnectors[0].connect(photo); place.inputConnectors[1].connect(mask)
k = SIZE / 720.0
# Blur TOP 'size' is the filter width: about 3 x the video renderer's Gaussian sigma
b_soft = blur(C, 'mask_soft', place, 7.5 * k, -1100, 700)      # sigma 2.5 (720 px): the soft outline
b_vol = blur(C, 'mask_vol', place, 9 * k, -1100, 600)          # sigma 3: the volume
b_rs = blur(C, 'luma_small', place, 7.5 * k, -1100, 500)       # sigma 2.5 } relief = small - large blur
b_rl = blur(C, 'luma_large', place, 27 * k, -1100, 400)        # sigma 9   }
b_slow = blur(C, 'mask_slow', place, 30 * k, -1100, 300)       # sigma 10: where the stream slows down
b_deep = blur(C, 'mask_deep', place, 40 * k, -1100, 200)       # deep inside the head (relief only there)
d_maps = shader(C, 'shader_maps', 'holo_maps.glsl', -950, 750, common=False)
maps = glsl_top(C, 'maps', d_maps, -950, 450, res=(SIZE, SIZE))
for i, b in enumerate((b_soft, b_vol, b_rs, b_rl, b_slow, b_deep)):
    maps.inputConnectors[i].connect(b)

# ---------------------------------------------------------------- the glow map: the Screen 2 figure, this frame
d_glow = shader(C, 'shader_glow', 'holo_glow.glsl', -800, 750)
glow = glsl_top(C, 'glow', d_glow, -800, 450, res=(SIZE // 2, SIZE // 2))
glow.inputConnectors[0].connect(maps)
uniforms(glow, [('uG1', [P + 'Streamglow', P + 'Figure', P + 'Headglow', P + 'Rim']),
                ('uG2', [P + 'Flow', P + 'Tear', P + 'Echoes', P + 'Detail'])])

# ---------------------------------------------------------------- the two particle simulations (feedback loops)
RESET = '1 if parent().par.Forcereset else 0'


def simulation(name, fname, res, extra, y):
    seed = mk(C, constantTOP, name + '_seed', -800, y)
    setmenu(seed, 'outputresolution', 'custom')
    trypar(seed, 'resolutionw', res); trypar(seed, 'resolutionh', res)
    setmenu(seed, 'format', 'rgba32float', '32-bit float (rgba)')
    for nm in ('colorr', 'colorg', 'colorb', 'alpha'):
        trypar(seed, nm, 0)
    fb = mk(C, feedbackTOP, name + '_fb', -650, y)
    fb.inputConnectors[0].connect(seed)
    d = shader(C, 'shader_' + name, fname, -500, y + 120)
    sim = glsl_top(C, name, d, -500, y, fmt=('rgba32float', '32-bit float (rgba)'))
    sim.inputConnectors[0].connect(fb)
    sim.inputConnectors[1].connect(maps)
    uniforms(sim, extra)
    trypar(fb, 'top', name)
    return sim


sim_s = simulation('stream', 'holo_sim_stream.glsl', STREAM_RES,
                   [('uS', [P + 'Streamspeed', P + 'Headslow', P + 'Turbulence', RESET])], 150)
sim_h = simulation('head', 'holo_sim_head.glsl', HEAD_RES,
                   [('uH', [P + 'Particlehold', P + 'Streamspeed', P + 'Turbulence', RESET])], -100)

# ---------------------------------------------------------------- sprites: a 1 x 1 quad instanced once per texel
d_vert = shader(C, 'shader_vertex', 'holo_vertex.glsl', -300, 400)
d_pix = shader(C, 'shader_pixel', 'holo_pixel.glsl', -150, 400, common=False)


def particles(name, sim, res, kind, y):
    mat = mk(C, glslMAT, name + '_mat', -300, y)
    trypar(mat, 'vdat', d_vert.name) or trypar(mat, 'vertexdat', d_vert.name)
    trypar(mat, 'pdat', d_pix.name) or trypar(mat, 'pixeldat', d_pix.name)
    drop_docked(mat)
    trypar(mat, 'blending', True)
    setmenu(mat, 'srcblend', 'one'); setmenu(mat, 'destblend', 'one')
    trypar(mat, 'depthtest', False); trypar(mat, 'depthwriting', False)
    setmenu(mat, 'cullface', 'neither', 'none', 'off')
    try:
        mat.seq.sampler.numBlocks = 2
    except Exception as e:
        holo_log.append('%s sampler seq: %s' % (mat.name, e))
    trypar(mat, 'sampler0name', 'sState')
    trypar(mat, 'sampler0top', sim.name) or trypar(mat, 'top0', sim.name)
    trypar(mat, 'sampler1name', 'sGlow')
    trypar(mat, 'sampler1top', 'glow') or trypar(mat, 'top1', 'glow')
    uniforms(mat, [('uV', [str(kind), P + 'Particlesize', str(SIZE), P + 'Particlehold']),
                   ('uW', [P + 'Streamspeed', '0', '0', '0'])])
    geo = mk(C, geometryCOMP, name + '_geo', -150, y)
    for ch in list(geo.children):
        ch.destroy()
    rect = geo.create(rectangleSOP, 'quad')
    trypar(rect, 'sizex', 1); trypar(rect, 'sizey', 1)
    rect.render = True; rect.display = True
    trypar(geo, 'material', '../' + mat.name) or trypar(geo, 'material', mat.name)
    trypar(geo, 'instancing', True)
    setmenu(geo, 'instancecountmode', 'manual')
    trypar(geo, 'numinstances', res * res)
    return geo


g_s = particles('stream', sim_s, STREAM_RES, 0, 150)
g_h = particles('head', sim_h, HEAD_RES, 1, -100)
cam = mk(C, cameraCOMP, 'cam', 0, 300)          # the Render TOP needs one; the vertex shader places the sprites itself
ren = mk(C, renderTOP, 'render', 0, 100)
trypar(ren, 'camera', 'cam'); trypar(ren, 'geometry', '%s %s' % (g_s.name, g_h.name)); trypar(ren, 'lights', '')
setmenu(ren, 'outputresolution', 'custom'); trypar(ren, 'resolutionw', SIZE); trypar(ren, 'resolutionh', SIZE)
setmenu(ren, 'format', 'rgba16float', '16-bit float (rgba)')
for nm in ('bgcolorr', 'bgcolorg', 'bgcolorb', 'bgcolora'):
    trypar(ren, nm, 0)
setmenu(ren, 'antialias', 'aa1', '1x')

# ---------------------------------------------------------------- the hologram
b1 = blur(C, 'bloom_small', ren, 2.2 * k * 3, 150, 200)
b2 = blur(C, 'bloom_large', ren, 10 * k * 3, 150, 0)
d_post = shader(C, 'shader_post', 'holo_post.glsl', 300, 300)
post = glsl_top(C, 'post', d_post, 300, 100, fmt=('rgba8fixed', '8-bit fixed (rgba)'), res=(SIZE, SIZE))
post.inputConnectors[0].connect(ren); post.inputConnectors[1].connect(b1); post.inputConnectors[2].connect(b2)
uniforms(post, [('uP1', [P + 'Gain', P + 'Bloom', P + 'Scanlines', P + 'Scanband']),
                ('uP2', [P + 'Flicker', P + 'Slices', P + 'Chroma', P + 'Vibration']),
                ('uP3', [P + 'Tintr', P + 'Tintg', P + 'Tintb', P + 'Backlight'])])
out = mk(C, nullTOP, 'OUT', 450, 100)
out.inputConnectors[0].connect(post)
out.viewer = True
mk(C, outTOP, 'out1', 600, 100).inputConnectors[0].connect(out)
trypar(C, 'opviewer', 'OUT')

# ---------------------------------------------------------------- recording one loop
rec = mk(C, moviefileoutTOP, 'record', 600, -50)
rec.inputConnectors[0].connect(out)
setmenu(rec, 'type', 'movie')
setmenu(rec, 'videocodec', 'h264', 'h.264', 'mjpa', 'photo')
trypar(rec, 'file', expr='parent().par.Recordfile')
trypar(rec, 'record', False)
pe = mk(C, parameterexecuteDAT, 'pulses', 600, -200)
pe.text = '''def onPulse(par):
	p = par.owner
	if par.name == 'Restart':
		p.par.Forcereset = True
		run("args[0].par.Forcereset = False", p, delayFrames=2)
	elif par.name == 'Recordloop':
		# the loop starts now (t = 0), one loop is written, then recording stops
		p.par.Timeoffset = absTime.seconds
		r = p.op('record')
		r.par.record = True
		run("args[0].par.record = False", r, delayFrames=max(1, int(round(p.par.Loop.eval() * project.cookRate))))
	return
'''
trypar(pe, 'op', '..')
trypar(pe, 'pars', 'Restart Recordloop')
trypar(pe, 'onpulse', True)
trypar(pe, 'valuechange', False)

mk(C, textDAT, 'readme', -1400, 900).text = (
    'artist_hologram - built by build_artist_hologram.py\n'
    'The artist photo as a hologram hidden in a particle stream flowing left -> right; the face only surfaces now '
    'and then (page Timing), drawn like the Screen 2 figure (page Hologram). View OUT.\n'
    'Record Loop (page Output) writes one loop to Record File, starting the loop at t = 0.\n'
    'Hits = NIN stage hits: the gusts / vibration / glitches follow /project1/nin_stage/echo instead of the loop.\n')

C.save(D + '/artist_hologram.tox')
print('holo_log', holo_log or 'none')
print('errors', [(o.path, o.errors()) for o in C.findChildren(depth=2) if o.errors()] or 'none')
print('warnings', [(o.path, o.warnings()) for o in C.findChildren(depth=2) if o.warnings()] or 'none')
print('ARTIST HOLOGRAM built: %s (%dx%d, %d stream + %d head particles), saved %s/artist_hologram.tox'
      % (C.path, SIZE, SIZE, STREAM_RES ** 2, HEAD_RES ** 2, D))
