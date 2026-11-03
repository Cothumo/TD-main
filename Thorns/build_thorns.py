# Thorns - thorn web between the ink's dense spots, barbed bursts on hits.
# Chain: ink_layer -> thorns -> nin_stage (its src). Rebuild: exec(open(project.folder + '/Thorns/build_thorns.py').read())
# (run it again after rebuilding nin_stage, whose build points its src back at ink_layer/OUT)
D = project.folder + '/Thorns'
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

old = P1.op('thorns')
if old is not None:
    old.destroy()
C = P1.create(baseCOMP, 'thorns'); C.nodeX, C.nodeY = -300, -700
pg = C.appendCustomPage('Thorns')
def fl(nm, dv, lo, hi, hlp):
    q = pg.appendFloat(nm)[0]; q.default = dv; q.val = dv; q.normMin = lo; q.normMax = hi; q.help = hlp
fl('Web', 0.7, 0, 1.5, 'thorn web: sharp barbed strands strung between the dense spots of the ink (strongest in the white, inverted picture)')
fl('Webcell', 70.0, 25, 200, 'pixels between the web\'s knots (smaller = denser web)')
fl('Barbs', 1.0, 0, 2, 'the barbs along the strands')
fl('Depth', 1.0, 0, 2, 'some strands soft, as if out of focus')
fl('Bursts', 0.9, 0, 2, 'barbed bursts: spiky thorn marks shooting out on hits where the ink is')
fl('Burstsize', 60.0, 15, 200, 'size of a burst in pixels')
fl('Inkthreshold', 0.25, 0.02, 0.9, 'how dense the ink must be to carry the web')

src = C.create(selectTOP, 'src'); src.nodeX, src.nodeY = -400, 0; sp(src, 'top', '/project1/ink_layer/OUT')
ink = C.create(selectTOP, 'ink'); ink.nodeX, ink.nodeY = -400, -150; sp(ink, 'top', '/project1/ink_layer/ink')
px = C.create(textDAT, 'thorns_pixel'); px.nodeX, px.nodeY = -200, -150; px.text = open(D + '/thorns.glsl').read()
g = C.create(glslTOP, 'thorns'); g.nodeX, g.nodeY = -200, 0
sp(g, 'pixeldat', px.name)
for dd in list(g.docked):
    if dd.name != px.name:
        try: dd.destroy()
        except Exception: pass
sp(g, 'outputresolution', 'useinput')
E = "(op('/project1/nin_stage/echo')['%s'].eval() if op('/project1/nin_stage/echo') is not None and op('/project1/nin_stage/echo')['%s'] is not None else %s)"
P = 'parent().par.'
U = [('uA', ['absTime.seconds % 10000', P + 'Web', P + 'Bursts', P + 'Webcell']),
     ('uB', [E % ('env', 'env', '0.0'), E % ('age', 'age', '30.0'),
             "math.floor(abs(" + (E % ('dx', 'dx', '0.0')) + ") * 997.0 + abs(" + (E % ('dy', 'dy', '0.0')) + ") * 131.0) % 1000",
             "math.atan2(" + (E % ('dy', 'dy', '0.0')) + ", " + (E % ('dx', 'dx', '1.0')) + ")"]),
     ('uC', [P + 'Barbs', P + 'Depth', P + 'Burstsize', P + 'Inkthreshold'])]
g.seq.vec.numBlocks = len(U)
for i, (nm, ex_) in enumerate(U):
    getattr(g.par, 'vec%dname' % i).val = nm
    for ch, e in zip('xyzw', ex_):
        getattr(g.par, 'vec%dvalue%s' % (i, ch)).expr = e
o = C.create(nullTOP, 'OUT'); o.nodeX, o.nodeY = 0, 0; o.inputConnectors[0].connect(g); o.viewer = True
sp(C, 'opviewer', 'OUT')
run("op(args[0]).inputConnectors[0].connect(op(args[1]))", g.path, src.path, delayFrames=1)
run("op(args[0]).inputConnectors[1].connect(op(args[1]))", g.path, ink.path, delayFrames=3)
ns = op('/project1/nin_stage/src')
if ns is not None:
    sp(ns, 'top', C.path + '/OUT')
else:
    log.append('no nin_stage/src')
run("op(args[0]).save(args[1])", C.path, D + '/thorns.tox', delayFrames=8)
print('THORNS built: %s -> nin_stage | log %s' % (C.path, log or 'none'))
