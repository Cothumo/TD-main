# Artist photo loop - "Screen 2" silhouette of the head + Ambient Ink particles with their vibration.
#
# Offline renderer (numpy / OpenCV, no GPU, no TouchDesigner needed). It ports the TDA shaders to a still photo:
#   - Screen2/screen2.glsl         backlit haze, dark figure, lit rim, faint relief, scan-line figure, ghosts,
#                                  time slicing, tears, interlace, analog-TV band / wobble / snow / dropouts,
#                                  tracking overlay, scanlines, vignette
#   - Ambient Ink Live/ink_*.glsl  ink particles (sprites that spread and pale with age, trails, dissolved halo),
#                                  ink_post vibration (jitter + oscillation + row wobble + trailing second image),
#                                  ink_layer blend (ink greys laid over the picture beneath)
# Only the head is used: head_mask.png (background, neck and hoodie removed). The ink peels off the head's outline,
# erupting on two "unstable" moments in the loop, where the vibration and the signal glitches peak.
# Every time-dependent term is periodic in the loop length, so the video loops seamlessly.
#
#   python render_artist_loop.py [--size 1080] [--seconds 7] [--fps 30] [--out artist_head_ink_loop.mp4]
#                                [--frames-dir DIR] [--preview N] [--workers 4]
import argparse, math, os, shutil, subprocess, sys, time
import numpy as np
import cv2

HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument('--photo', default=os.path.join(HERE, 'artist_photo.jpg'))
ap.add_argument('--mask', default=os.path.join(HERE, 'head_mask.png'))
ap.add_argument('--size', type=int, default=1080)
ap.add_argument('--seconds', type=float, default=7.0)
ap.add_argument('--fps', type=int, default=30)
ap.add_argument('--particles', type=int, default=320000)
ap.add_argument('--out', default=os.path.join(HERE, 'artist_head_ink_loop.mp4'))
ap.add_argument('--frames-dir', default=None)
ap.add_argument('--preview', type=int, nargs='*', default=None, help='only render these frame numbers to PNG')
ap.add_argument('--workers', type=int, default=os.cpu_count() or 4)
ap.add_argument('--seed', type=int, default=7)
ARGS = ap.parse_args()

S = ARGS.size
FPS = ARGS.fps
N = int(round(ARGS.seconds * FPS))           # frames in the loop
T = N / FPS
K = S / 720.0                                # the TD shaders' pixel sizes are for a 720 high frame
TAU = 2 * math.pi

# ---------------------------------------------------------------- look (Screen 2 page values, tuned for a portrait)
P2 = dict(Figure=1.0, Echoes=0.8, Rim=1.2, Flow=1.0, Haze=1.5, Light=1.3, Lightsize=0.3, Lightx=0.66, Lighty=0.36,
          Noise=0.7, Tear=0.6, Ghosts=0.8, Scanlines=0.4, Chaos=0.6, Ambient=0.4, Interlace=0.8, Snow=0.5,
          Timeslice=0.6, Track=0.75, Trackcell=46.0, Lines=0.55, Lineheight=0.3, Linespacing=5.0, Detail=1.4,
          pads=0.4)
# Ambient Ink preset (README: Opacity 3, Condense 1, Dust 0.5, Trails 0.25, Lifetime 1, Vibration 1.5) + layer
PI = dict(Particlesize=1.3, Ink=0.9, Opacity=3.0, Diffusion=1.0, Diffusionsize=20.0, Dilution=1.5, Spreadgrowth=2.0,
          Trails=0.25, Vibration=1.5, Dust=0.5, Turbulence=1.6, Current=1.2, Buoyancy=0.3,
          Layeramount=0.85, Inktone=0.08, Inktonelight=0.6, Inkmatch=0.5, Inkthreshold=0.3)
BURSTS = (1.55, 4.85)                          # seconds: the unstable moments (ink erupts, vibration + glitch peak)

rng0 = np.random.default_rng(ARGS.seed)


def ss(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def h21(x, y):
    """the shaders' hash (vectorised): vec2 -> 0..1"""
    x = np.asarray(x, np.float64); y = np.asarray(y, np.float64)
    q0 = np.modf(x * 0.1031)[0]; q1 = np.modf(y * 0.1031)[0]; q2 = q0.copy()
    q0, q1, q2 = np.abs(q0), np.abs(q1), np.abs(q2)
    d = q0 * (q1 + 33.33) + q1 * (q2 + 33.33) + q2 * (q0 + 33.33)
    q0 = q0 + d; q1 = q1 + d; q2 = q2 + d
    return np.modf((q0 + q1) * q2)[0] % 1.0


def burst_env(t, tau=0.45, attack=0.06):
    """periodic envelope: jumps up at each burst, decays (used for the hit / vibration drive)"""
    e = 0.0
    for b in BURSTS:
        d = (t - b) % T
        e = max(e, (1 - math.exp(-d / attack)) * math.exp(-d / tau) / 0.85 if d < T * 0.9 else 0.0)
    return min(e, 1.0)


# ---------------------------------------------------------------- photo + head mask placed in the frame
photo = cv2.imread(ARGS.photo, cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255.0
mask = cv2.imread(ARGS.mask, cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255.0
ys, xs = np.nonzero(mask > 0.5)
top, bot = ys.min(), ys.max()
SC = 0.84 * S / (bot - top)                   # the head fills 84 % of the frame height
OY = 0.075 * S - top * SC                     # its left side stays on the frame's left edge (the photo is cut there)


def bob(f):
    """the head floats a little (vertical drift + breathing scale about the left edge) - periodic"""
    th = TAU * f / N
    return 5.0 * K / 1.5 * math.sin(th) + 2.0 * math.sin(2 * th + 1.0), 1.0 + 0.004 * math.sin(th + 0.5)


def place(img, f, interp=cv2.INTER_LINEAR):
    dy, sc = bob(f)
    s = SC * sc
    cy = 0.5 * S
    M = np.float32([[s, 0, 0], [0, s, OY * sc + cy * (1 - sc) + dy]])
    return cv2.warpAffine(img, M, (S, S), flags=interp, borderMode=cv2.BORDER_CONSTANT, borderValue=0)


# photo luma: the flash photo is lifted a little in the shadows so the relief reads
lum_src = np.clip((photo - 0.04) / 0.92, 0, 1) ** 0.9
print('placing head: %d frames at %dx%d' % (N, S, S)); sys.stdout.flush()
HIST_M = np.empty((N, S, S), np.uint8)       # body (r) history
HIST_L = np.empty((N, S, S), np.uint8)       # camera picture (photo luma) history
for f in range(N):
    HIST_M[f] = np.clip(place(mask, f) * 255 + 0.5, 0, 255).astype(np.uint8)
    HIST_L[f] = np.clip(place(lum_src * mask, f) * 255 + 0.5, 0, 255).astype(np.uint8)
# trail (g): slowly fading max of the body - run two loops so it is periodic
HIST_G = np.empty_like(HIST_M)
g = np.zeros((S, S), np.float32)
for rep in range(2):
    for f in range(N):
        g = np.maximum(HIST_M[f].astype(np.float32), g * 0.86)
        if rep == 1:
            HIST_G[f] = g.astype(np.uint8)
REST = place(mask, 0)

# ---------------------------------------------------------------- tileable value-noise textures for the haze fbm
NT = 256
NOISE = [rng0.random((NT, NT)).astype(np.float32) for _ in range(5)]


def fbm(px, py):
    s = np.zeros(px.shape, np.float32); a = 0.5
    for i in range(5):
        mx = np.mod(px, NT).astype(np.float32); my = np.mod(py, NT).astype(np.float32)
        s += a * cv2.remap(NOISE[i], mx, my, cv2.INTER_CUBIC, borderMode=cv2.BORDER_WRAP)
        px = px * 2.03 + 17.1; py = py * 2.03 + 9.7; a *= 0.5
    return np.clip(s / 0.96875, 0, 1)


# ---------------------------------------------------------------- ink: flow field (periodic in the loop)
G = 136                                       # flow grid
CELL = S / (G - 1)


def smooth_field(sig):
    a = cv2.GaussianBlur(rng0.standard_normal((G, G)).astype(np.float32), (0, 0), sig, borderType=cv2.BORDER_REFLECT)
    return a / (a.std() + 1e-6)


def curl(psi):
    gy, gx = np.gradient(psi)
    return np.stack([gy, -gx], -1)            # (vx, vy) in grid units


octs = []
for sig, amp in ((13.0, 70.0), (4.5, 42.0)):   # big slow billows, fine fluttering tendrils (px / s)
    C = [(smooth_field(sig), smooth_field(sig)) for _ in range(3)]
    octs.append((C, amp))
VEL = np.zeros((N, G, G, 2), np.float32)
for ci, (C, amp) in enumerate(octs):
    vs = []
    for f in range(N):
        th = TAU * f / N
        psi = sum(C[k][0] * math.cos(k * th + 1.3 * k * ci) - C[k][1] * math.sin(k * th + 1.3 * k * ci) for k in range(3))
        vs.append(curl(psi))
    vs = np.stack(vs)
    vs *= amp * PI['Turbulence'] / 1.6 / (np.sqrt((vs ** 2).sum(-1)).mean() + 1e-6)
    VEL += vs
VEL[..., 0] += 26.0 * PI['Current'] / 1.2            # current: drifts away from the face, to the right
VEL[..., 1] += -30.0 * PI['Buoyancy'] / 0.3          # buoyancy: the ink rises
# the head is solid: the water flows out of / round it
D = cv2.GaussianBlur(REST, (0, 0), 14 * K)
Dg = cv2.resize(D, (G, G), interpolation=cv2.INTER_AREA)
gy, gx = np.gradient(Dg)
rep = np.stack([-gx, -gy], -1)
rep *= 70.0 / (np.sqrt((rep ** 2).sum(-1)).max() + 1e-6)
VEL += rep[None]
VELF = VEL.reshape(-1, 2)


def sample_vel(fi, p):
    gx = np.clip(p[:, 0] / CELL, 0, G - 1.001); gy = np.clip(p[:, 1] / CELL, 0, G - 1.001)
    ix = gx.astype(np.int64); iy = gy.astype(np.int64); fx = (gx - ix)[:, None]; fy = (gy - iy)[:, None]
    b = fi * G * G + iy * G + ix
    v = (VELF[b] * (1 - fx) * (1 - fy) + VELF[b + 1] * fx * (1 - fy) + VELF[b + G] * (1 - fx) * fy + VELF[b + G + 1] * fx * fy)
    return v


# ---------------------------------------------------------------- ink: particles born on the head's outline
NP = ARGS.particles
band = (REST > 0.06) & (REST < 0.94)
inner = (REST >= 0.94) & (cv2.erode((REST > 0.5).astype(np.uint8), np.ones((3, 3), np.uint8), iterations=int(18 * K)) == 0)
by_, bx_ = np.nonzero(band | inner)
keep = (bx_ > 4) & (by_ > 4) & (by_ < S - 4)
by_, bx_ = by_[keep], bx_[keep]
w = np.full(by_.shape, 0.30)
w[by_ < 0.52 * S] = 1.0                                             # hair, top of the head
w[bx_ > 0.42 * S] = 1.0                                             # back of the head
w[(by_ > 0.66 * S) & (bx_ < 0.36 * S)] = 0.55                       # under the beard (where the neck was cut)
w[bx_ < 0.10 * S] *= 0.25                                           # little on the face side
w[inner[by_, bx_]] *= 0.6
w /= w.sum()
Dg_full_y, Dg_full_x = np.gradient(cv2.GaussianBlur(REST, (0, 0), 6 * K))


def normal_at(ix, iy):
    n = -np.stack([Dg_full_x[iy, ix], Dg_full_y[iy, ix]], -1)
    return n / (np.linalg.norm(n, axis=-1, keepdims=True) + 1e-6)


def rot(v, a):
    c, s_ = np.cos(a), np.sin(a)
    return np.stack([v[:, 0] * c - v[:, 1] * s_, v[:, 0] * s_ + v[:, 1] * c], -1)


# ink wells on the outline: each one releases a stream on its own slow cycle -> the flow stretches it into tendrils
NSITE = 56
site = rng0.choice(len(w), NSITE, replace=False, p=w)
SX_, SY_ = bx_[site], by_[site]
SN = normal_at(SX_, SY_)
SN = rot(SN, rng0.uniform(-0.35, 0.35, NSITE))
SSPD = rng0.uniform(18, 70, NSITE) * K / 1.5
SFRQ = rng0.integers(1, 3, NSITE)
SPH = rng0.uniform(0, TAU, NSITE)
SGAIN = rng0.uniform(0.85, 1.15, NSITE)
kind = rng0.random(NP)
stream = kind < 0.68
edgeh = (kind >= 0.68) & (kind < 0.82)
puff = kind >= 0.82
f0 = np.zeros(NP, np.int64)
sid = np.zeros(NP, np.int64)
spawn = np.zeros((NP, 2), np.float32)
vdir = np.zeros((NP, 2), np.float32)
speed0 = np.zeros(NP, np.float32)
turb = np.ones(NP, np.float32)
# streams: birth time follows the well's swell (periodic in the loop)
ns = int(stream.sum())
sid_s = rng0.integers(0, NSITE, ns)
fs = np.empty(ns, np.int64)
todo = np.arange(ns)
while len(todo):
    cand = rng0.integers(0, N, len(todo))
    pr = 0.25 + 0.75 * np.maximum(0, np.sin(TAU * SFRQ[sid_s[todo]] * cand / N + SPH[sid_s[todo]])) ** 2
    ok = rng0.random(len(todo)) < pr
    fs[todo[ok]] = cand[ok]
    todo = todo[~ok]
f0[stream] = fs; sid[stream] = sid_s
spawn[stream] = np.stack([SX_[sid_s], SY_[sid_s]], -1) + rng0.normal(0, 2.5 * K, (ns, 2))
vdir[stream] = SN[sid_s]; speed0[stream] = SSPD[sid_s] * rng0.uniform(0.8, 1.2, ns); turb[stream] = SGAIN[sid_s]
# edge haze: the whole outline slowly dissolves
ne = int(edgeh.sum())
pe = rng0.choice(len(w), ne, p=w)
f0[edgeh] = rng0.integers(0, N, ne)
spawn[edgeh] = np.stack([bx_[pe], by_[pe]], -1) + rng0.random((ne, 2))
vdir[edgeh] = normal_at(bx_[pe], by_[pe]); speed0[edgeh] = rng0.uniform(6, 22, ne) * K / 1.5
turb[edgeh] = rng0.uniform(0.6, 1.2, ne)
# puffs: on each unstable moment a few wells (back / top of the head) erupt in jets
npf = int(puff.sum())
pidx = np.nonzero(puff)[0]
backs = np.nonzero((SX_ > 0.30 * S) | (SY_ < 0.35 * S))[0]
bsel = rng0.integers(0, len(BURSTS), npf)
PS = [rng0.choice(backs, 7, replace=False) for _ in BURSTS]
ps = np.array([PS[bb][k] for bb, k in zip(bsel, rng0.integers(0, 7, npf))])
bt = np.array(BURSTS)[bsel] + rng0.random(npf) ** 1.8 * 0.32
f0[puff] = np.round(bt * FPS).astype(np.int64) % N
spawn[puff] = np.stack([SX_[ps], SY_[ps]], -1) + rng0.normal(0, 4 * K, (npf, 2))
vdir[puff] = rot(SN[ps], rng0.normal(0, 0.22, npf))
speed0[puff] = rng0.uniform(150, 330, npf) * K / 1.5
turb[puff] = SGAIN[ps]
H2 = rng0.random((NP, 4)).astype(np.float32)
spray = puff & (H2[:, 2] < 0.18)                                     # fine droplets, shot further
speed0[spray] *= 1.7
vdir[spray] = rot(vdir[spray], rng0.normal(0, 0.5, int(spray.sum())))
LIFE = np.where(puff, 2.2 + 2.6 * H2[:, 0], np.where(edgeh, 1.2 + 1.8 * H2[:, 0], 2.0 + 3.0 * H2[:, 0]))
LIFE = np.where(spray, 1.4 + 1.6 * H2[:, 0], LIFE)
LIFE_F = np.maximum((LIFE * FPS).astype(np.int64), 8)
LMAX = int(LIFE_F.max())
dy0 = np.array([bob(f)[0] for f in range(N)], np.float32)
p = spawn.astype(np.float32).copy(); p[:, 1] += dy0[f0]
v_push = (vdir * speed0[:, None]).astype(np.float32)
POS = np.empty((LMAX, NP, 2), np.float32)
print('simulating %d ink particles over %d steps' % (NP, LMAX)); sys.stdout.flush()
dt = 1.0 / FPS
turb_gain = turb[:, None]
for a in range(LMAX):
    POS[a] = p
    fi = (f0 + a) % N
    age_s = a * dt
    v = sample_vel(fi, p)
    grow = np.minimum(0.35 + age_s / 2.5, 1.2)                        # billows grow as the ink ages
    v = v * (grow * turb_gain) + v_push * math.exp(-age_s / 0.55)
    p = p + v.astype(np.float32) * dt

# sprite attributes (ink_vertex.glsl)
GY = rng0.random(NP).astype(np.float32)
GZ = rng0.random(NP).astype(np.float32)
SIZE0 = PI['Particlesize'] * K * (0.6 + 0.8 * GY)
SIZE0[spray] *= 0.5
AMT0 = PI['Ink'] * (0.4 + 0.6 * GZ)
AMT0[spray] = 0.7 * 1.3 * (0.5 + 0.5 * GZ[spray])
AMT0[edgeh] *= 0.55
# dust: dark specks floating slowly in the water
ND = int(450 * PI['Dust'] / 0.5)
DUST_P = (rng0.random((ND, 2)) * S).astype(np.float32)
DUST_PH = (rng0.random((ND, 2)) * TAU).astype(np.float32)
DUST_A = (1.2 + 1.6 * rng0.random(ND)).astype(np.float32) * 0.5
DUST_S = (PI['Particlesize'] * K * (0.4 + 0.8 * rng0.random(ND) ** 2)).astype(np.float32)

RAD_BINS = np.array([0.0, 1.6, 2.6, 4.2, 6.8, 11.0, 18.0, 1e9])


def splat(img, x, y, wgt):
    ok = (x >= 0) & (y >= 0) & (x < S - 1) & (y < S - 1)
    x, y, wgt = x[ok], y[ok], wgt[ok]
    ix = x.astype(np.int64); iy = y.astype(np.int64); fx = x - ix; fy = y - iy
    b = iy * S + ix
    flat = img.reshape(-1)
    flat += np.bincount(b, wgt * (1 - fx) * (1 - fy), S * S)
    flat += np.bincount(b + 1, wgt * fx * (1 - fy), S * S)
    flat += np.bincount(b + S, wgt * (1 - fx) * fy, S * S)
    flat += np.bincount(b + S + 1, wgt * fx * fy, S * S)


def ink_frame(f):
    """this frame's ink render (r = amount, g = amount x age) - soft sprites that spread and pale as they age"""
    a = (f - f0) % N
    vis = a < LIFE_F
    idx = np.nonzero(vis)[0]
    a = a[idx]
    pos = POS[a, idx]
    ageF = a / LIFE_F[idx]
    spr = spray[idx]
    size0 = SIZE0[idx]
    rad = np.where(spr, size0, size0 * (1.0 + 3.0 * PI['Spreadgrowth'] * ageF * 0.5))
    rad = np.maximum(rad, 1.0)
    fade_in = ss(0.0, 0.06, ageF)
    amt = AMT0[idx] * np.where(spr, (1 - ageF) ** 1.6 * ss(0.0, 0.06, ageF), (1 - ageF) ** PI['Dilution'] * fade_in)
    amt = amt * (size0 ** 2 + 0.5) / (rad ** 2 + 0.5)
    W_ = amt * math.pi * rad ** 2 / 3.5 * (330000.0 / NP) * 0.55     # deposit; scaled to the particle count
    out_r = np.zeros((S, S), np.float32); out_g = np.zeros((S, S), np.float32)
    for lo, hi in zip(RAD_BINS[:-1], RAD_BINS[1:]):
        m = (rad >= lo) & (rad < hi)
        if not m.any():
            continue
        rr = np.zeros((S, S), np.float64); gg = np.zeros((S, S), np.float64)
        splat(rr, pos[m, 0], pos[m, 1], W_[m])
        splat(gg, pos[m, 0], pos[m, 1], W_[m] * ageF[m])
        sig = float(np.clip(np.median(rad[m]), 0.5, 40)) / 2.65
        if sig > 0.45:
            rr = cv2.GaussianBlur(rr.astype(np.float32), (0, 0), sig); gg = cv2.GaussianBlur(gg.astype(np.float32), (0, 0), sig)
        out_r += rr.astype(np.float32); out_g += gg.astype(np.float32)
    # dust specks, drifting on small loops
    th = TAU * f / N
    dx = DUST_P[:, 0] + 14 * K * np.sin(th + DUST_PH[:, 0]); dy = DUST_P[:, 1] + 10 * K * np.cos(th + DUST_PH[:, 1])
    dd = np.zeros((S, S), np.float64)
    splat(dd, dx, dy, DUST_A * math.pi * DUST_S ** 2 / 3.5)
    out_r += cv2.GaussianBlur(dd.astype(np.float32), (0, 0), 0.8)
    return out_r, out_g


def ink_accum(f):
    """ink_accum.glsl: mix(cur, prev, Trails) unrolled over the last frames (periodic)"""
    keep = PI['Trails']
    r = np.zeros((S, S), np.float32); g = np.zeros((S, S), np.float32); tot = 0.0
    for k in range(4):
        wk = (1 - keep) * keep ** k
        cr, cg = ink_frame((f - k) % N)
        r += wk * cr; g += wk * cg; tot += wk
    return r / tot, g / tot


def ink_post(f, ink_r, ink_g, vib):
    """ink_post.glsl: vibration (jitter + oscillation + row wobble + a faint second image) and ink on white paper"""
    X, Y = GRID
    halo_r = cv2.GaussianBlur(ink_r, (0, 0), PI['Diffusionsize'] * K / 2.2)
    halo_g = cv2.GaussianBlur(ink_g, (0, 0), PI['Diffusionsize'] * K / 2.2)
    fr = float(f)
    offx = offy = 0.0
    if vib > 0.001:
        jx = h21(fr, 1.37) * 2 - 1; jy = h21(fr, 7.91) * 2 - 1
        sx, sy = math.sin(fr * 2.71), math.cos(fr * 3.37)
        offx = (jx * 0.65 + sx * 0.35) * vib * 16.0 * K
        offy = (jy * 0.65 + sy * 0.35) * vib * 16.0 * K
        rowx = np.sin(Y * (0.045 / K) + fr * 1.9) * vib * 5.0 * K
        mx = (X + offx + rowx).astype(np.float32); my = (Y + offy).astype(np.float32)
        mx2 = (X - 1.6 * (offx + rowx)).astype(np.float32); my2 = (Y - 1.6 * offy).astype(np.float32)
        rem = lambda im, a, b: cv2.remap(im, a, b, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        gw = min(0.45 * vib, 0.6)
        ir = rem(ink_r, mx, my) * (1 - gw) + rem(ink_r, mx2, my2) * gw
        ig = rem(ink_g, mx, my) * (1 - gw) + rem(ink_g, mx2, my2) * gw
        hr = rem(halo_r, mx, my) * (1 - gw) + rem(halo_r, mx2, my2) * gw
        hg = rem(halo_g, mx, my) * (1 - gw) + rem(halo_g, mx2, my2) * gw
    else:
        ir, ig, hr, hg = ink_r, ink_g, halo_r, halo_g
    dens = ir + hr * PI['Diffusion'] * 0.6
    ageR = np.clip((ig + hg * PI['Diffusion'] * 0.6) / np.maximum(dens, 1e-4), 0, 1)
    Tr = np.exp(-dens * PI['Opacity'])
    inkc = 0.015 + (0.32 - 0.015) * ageR ** 0.8
    return Tr + inkc * (1 - Tr)                                        # ink on white paper (grey)


def ink_layer(under, ink):
    """ink_layer.glsl: the ink's own greys (dense = Inktone, thin = Inktonelight), sunk into the picture beneath"""
    dens = 1.0 - ink
    thr = PI['Inkthreshold']
    d = ss(thr, 0.75, dens) * PI['Layeramount']
    g = ss(thr, 0.95, dens)
    tone = PI['Inktonelight'] + (PI['Inktone'] - PI['Inktonelight']) * g
    shade = under * (0.82 + (0.55 - 0.82) * g)
    tone = tone + (shade - tone) * PI['Inkmatch']
    return under + (tone - under) * d


# ---------------------------------------------------------------- Screen 2
GRID = np.meshgrid(np.arange(S, dtype=np.float32), np.arange(S, dtype=np.float32))
U = (GRID[0] + 0.5) / S
VI = (GRID[1] + 0.5) / S                     # image v (down)
VY = 1.0 - VI                                # shader uv.y (up)
ROWS = np.arange(S)
VYr = 1.0 - (ROWS + 0.5) / S
HAZE_S = S // 2


def rem(img, mx, my, interp=cv2.INTER_LINEAR):
    return cv2.remap(img, mx.astype(np.float32), my.astype(np.float32), interp, borderMode=cv2.BORDER_CONSTANT, borderValue=0)


def aged(H, f, age_rows):
    idx = (f - age_rows) % N
    return H[idx[:, None], ROWS[:, None], ROWS[None, :]]


def tracking(f, t, s0r, stat):
    """tracking overlay: points snapped onto the outline, boxed, labelled with tiny data bars, joined by hairlines"""
    cs = P2['Trackcell'] * K
    tk = math.floor(t * 6.0 + 1e-6)
    ov = np.zeros((S, S), np.float32)
    cnts, _ = cv2.findContours((s0r > 0.5).astype(np.uint8), cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
    if not cnts:
        return ov
    C = np.concatenate([c.reshape(-1, 2) for c in cnts]).astype(np.float32)
    C = C[(C[:, 0] > 0.05 * S) & (C[:, 1] > 3) & (C[:, 0] < S - 4) & (C[:, 1] < S - 4)]
    if len(C) == 0:
        return ov
    n = int(math.ceil(S / cs))
    nodes = {}
    for j in range(n):
        for i in range(n):
            if h21(i * 1.31 + tk * 0.29, j * 1.31 + tk * 0.29) < 0.3:
                continue
            q = np.array([(i + h21(i + tk * 0.137, j + tk * 0.137)) * cs, (j + h21(j + 3.7 + tk * 0.071, i + 3.7 + tk * 0.071)) * cs])
            d2 = ((C - q) ** 2).sum(1)
            k = int(d2.argmin())
            pt = C[k]
            if np.hypot(*(pt / cs - np.array([i + 0.5, j + 0.5]))) > 0.9:
                continue
            nodes[(i, j)] = pt
    L = lambda a, b, v: cv2.line(ov, (int(a[0] * 4), int(a[1] * 4)), (int(b[0] * 4), int(b[1] * 4)), v, 1, cv2.LINE_AA, 2)
    for (i, j), pt in nodes.items():
        x, y = pt
        bs = (5.0 + 4.0 * h21(i + 9.1, j + 9.1)) * K
        cv2.rectangle(ov, (int((x - bs) * 4), int((y - bs) * 4)), (int((x + bs) * 4), int((y + bs) * 4)), 1.0, 1, cv2.LINE_AA, 2)
        nb = 3 + int(4 * h21(i + 2.2, j + 2.2))
        bw = max(1, int(round(2 * K))); pitch = bw + max(1, int(round(K)))
        for b in range(nb):
            if h21(b, i + j * 7.0 + tk) < 0.3:
                continue
            x0 = int(x + bs + 3 * K + b * pitch); y0 = int(y + 2 * K - 4 * K)
            ov[max(y0, 0):max(y0 + int(4 * K), 0), max(x0, 0):max(x0 + bw, 0)] = np.maximum(ov[max(y0, 0):max(y0 + int(4 * K), 0), max(x0, 0):max(x0 + bw, 0)], 0.8)
        if h21(i + 5.5, j + 5.5) > 0.7:
            for r in range(int(30 * K / (3 * K))):
                ln = int((2 + 6 * h21(r, i + tk)) * K)
                y0 = int(y - bs - 3 * K - (r + 1) * 3 * K)
                x0 = int(x - K)
                if y0 > 0:
                    ov[y0:y0 + max(1, int(2 * K) - 1), max(x0, 0):max(x0 + ln, 0)] = np.maximum(ov[y0:y0 + max(1, int(2 * K) - 1), max(x0, 0):max(x0 + ln, 0)], 0.8)
        for (di, dj, v, need) in ((1, 0, 0.8, 0), (0, -1, 0.8, 0), (1, -1, 0.6, 1)):
            q = nodes.get((i + di, j + dj))
            if q is not None and (not need or h21(i + 7.7, j + 7.7) > 0.5):
                L(pt, q, v)
    return ov


def screen2(f, hitE):
    t = f / FPS
    th = TAU * f / N
    X, Y = GRID
    NOI, TEAR, GH = P2['Noise'], P2['Tear'], P2['Ghosts'] * P2['Echoes']
    CH, AMB = P2['Chaos'], P2['Ambient']
    rng = np.random.default_rng(1000 + f)
    cur_r = HIST_M[f].astype(np.float32) / 255; cur_g = HIST_G[f].astype(np.float32) / 255
    moved = np.clip(cur_g - cur_r, 0, 1)
    mot = float(np.clip(moved.mean() * 6.0 * 8.0, 0, 1))

    # ---- rows tear sideways, odd / even lines drift apart
    row = np.floor(VYr * 240.0); tk = math.floor(t * 7.0 + 1e-6)
    band = ss(0.78, 1.0, h21(row, tk)) + 0.35 * ss(0.5, 1.0, h21(np.floor(VYr * 30.0), tk + 7.0))
    s6 = HIST_M[(f - 6) % N].astype(np.float32) / 255
    tear = ((h21(row, tk + 3.1) - 0.5) * 0.05 * TEAR * band)[:, None] * ss(0.02, 0.4, moved + 0.6 * s6)
    tear += ((h21(row, tk + 5.3) - 0.5) * 0.03 * TEAR * band * AMB * CH)[:, None]
    il = ((np.floor(Y * 720.0 / S) % 2) - 0.5) * 0.006 * P2['Interlace'] * (0.15 + AMB * 0.5 + mot) * (0.4 + moved * 1.5 + AMB * 0.4)
    # ---- analog TV: tracking band rolling down (one pass per loop), sync wobble, vertical hold slip
    drive = max(AMB, mot, hitE)
    by = (0.3 - t / T) % 1.0
    bdy = np.abs(VYr - by); bdy = np.minimum(bdy, 1 - bdy)
    bandT = (1 - ss(0.0, 0.045 + 0.04 * mot, bdy)) * CH * (0.3 + 0.7 * drive)
    wob = np.sin(VYr * 38.0 + 3 * th) * np.sin(VYr * 7.0 - th) * 0.005 * CH * (AMB * 0.6 + mot * 1.5 + hitE * 0.8)
    bj = (h21(np.floor(VYr * 720 * 0.5), f + 0.5) - 0.5) * 0.08 * bandT
    vt = math.floor(t / (T / 2)); vph = t - vt * T / 2
    vslip = (0.0 if vt % 2 == 0 else -0.032) * math.exp(-vph * 4.0) * CH * (0.5 + drive)
    dxu = tear + il + (wob + bj)[:, None]
    SX = X + dxu * S
    SY = Y - vslip * S

    # ---- time slicing: how old the figure is at each row (the bottom rows lag further), some bands lag more
    ts = P2['Timeslice'] * 26.0 * (1.0 - VYr) * (0.65 + 0.35 * np.sin(th + VYr * 2.0))
    ts += P2['Timeslice'] * 8.0 * (h21(np.floor(VYr * 18.0), math.floor(t * 2.0 + 1e-6)) > 0.7)
    age = np.round(ts).astype(np.int64)
    A_r = aged(HIST_M, f, age); A_g = aged(HIST_G, f, age); A_l = aged(HIST_L, f, age)
    s0r = rem(A_r, SX, SY).astype(np.float32) / 255
    s0g = rem(A_g, SX, SY).astype(np.float32) / 255
    lum = rem(A_l, SX, SY).astype(np.float32) / 255
    o = int(round(0.006 * S))
    pad = np.pad(s0r, o, mode='edge')
    gx = pad[o:-o, 2 * o:] - pad[o:-o, :-2 * o]
    gy = pad[2 * o:, o:-o] - pad[:-2 * o, o:-o]
    edge = np.clip(np.sqrt(gx * gx + gy * gy) * 2.0, 0, 1)

    # ---- backlit haze, flowing round the head (half resolution, smooth)
    hs = HAZE_S
    sm = lambda a: cv2.resize(a, (hs, hs), interpolation=cv2.INTER_AREA)
    gxs, gys = sm(gx), sm(gy)
    uh, vh = np.meshgrid((np.arange(hs) + 0.5) / hs, (np.arange(hs) + 0.5) / hs)
    q = fbm(uh * 3.0 + 0.35 * math.cos(th), vh * 3.0 + 0.35 * math.sin(th)) - 0.5
    F = P2['Flow']
    fu = uh + sm((wob + bj)[:, None] * np.ones((1, S), np.float32)) * 0.6 - gxs * 0.05 * F + (-gys) * 0.06 * F * q * 2
    fv = vh - vslip * 0.5 - gys * 0.05 * F + gxs * 0.06 * F * q * 2
    # the haze drifts on a circle in noise space -> periodic
    f1 = fbm(fu * 2.0 + 0.22 * math.cos(th), fv * 2.0 + 0.22 * math.sin(th) + 3.0)
    f2 = fbm(fu * 4.5 + 0.3 * math.cos(-th + 1.0) + f1 * 1.5, fv * 4.5 + 0.3 * math.sin(-th + 1.0) + f1 * 1.5)
    fog = np.clip(0.25 + 0.75 * (f1 * 0.65 + f2 * 0.35), 0, 1)
    fog = cv2.resize(fog, (S, S), interpolation=cv2.INTER_CUBIC)
    Lx = P2['Lightx'] + 0.02 * math.sin(th); Ly = P2['Lighty'] + 0.02 * math.cos(th)
    r = np.sqrt((U - Lx) ** 2 + (VI - Ly) ** 2)
    size = P2['Lightsize']
    hz = min(P2['Haze'] * (0.55 + 0.9 * P2['pads']), 2.5)
    level = 0.5 + 0.3 * math.sin(2 * th) + 0.25 * hitE
    core = np.exp(-r * r / (size * size * 0.06)) * (1 - 0.55 * min(hz, 1.0))
    light = np.minimum(core * 0.7 + np.exp(-r / size) * 0.22 + np.exp(-r / (size * 2.2)) * fog * hz * 0.36, 0.8) * (0.8 + 0.2 * level) * P2['Light']
    col = light + 0.02 * fog * hz

    # ---- analog noise: grain + line noise, new every frame
    grain = rng.random((S // 2 + 1, S // 2 + 1)).astype(np.float32).repeat(2, 0).repeat(2, 1)[:S, :S]
    lines = rng.random(S // 2 + 1).astype(np.float32).repeat(2)[:S][:, None]
    stat = grain * 0.45 + lines * 0.55

    # ---- ghosts: older heads drifting behind it (towards the light), textured by the noise
    gh = 0.0
    for ag, ox, oy, wgt in ((6, 0.006, 0.004, 0.5), (15, 0.014, 0.010, 0.34), (30, 0.024, 0.018, 0.22)):
        Hh = HIST_M[(f - ag) % N]
        gh = gh + rem(Hh, SX - ox * S, SY + oy * S).astype(np.float32) / 255 * wgt
    gh = gh * GH * (1 - np.clip(s0r, 0, 1)) * (0.55 + 0.45 * stat)
    col = col * (1 - 0.6 * np.clip(gh, 0, 1))

    # ---- traces break up into noise and dissolve; snow; dropouts
    tr = np.clip(s0g - s0r, 0, 1)
    dis = ss(stat * 0.85, stat * 0.85 + 0.22, tr)
    col = col * (1 - NOI * dis * (0.35 + 0.45 * stat) * P2['Echoes'])
    snow = np.clip(P2['Snow'] * (0.1 * mot + moved * 0.7 + 0.4 * hitE * (moved + np.clip(s0r, 0, 1) * 0.3) + 0.4 * AMB * CH) + bandT[:, None] * 1.2, 0, 1)
    col = col + (grain * (0.25 + 0.6 * light) + 0.03 - col) * snow * 0.7
    lnr = np.floor((ROWS + 0.5) * 720.0 / S)
    x0 = h21(lnr, f + 11.0); dl = 0.05 + 0.25 * h21(lnr, f + 5.0)
    on = h21(lnr, f * 3.7 + 0.31) > 1 - 0.01 * CH * (AMB * 0.6 + mot * 3 + hitE + bandT * 4)
    drop = (on[:, None] & (U >= x0[:, None]) & (U <= (x0 + dl)[:, None])).astype(np.float32)
    col = col + (0.5 * (0.35 + light) - col) * drop * 0.7

    # ---- the head: a dark form, faint features inside it (the photo's relief catches the light), lit outline
    body = np.clip(s0r, 0, 1) * P2['Figure']
    col = col + (col * 0.03 + 0.012 * stat * NOI - col) * body
    o1 = 2.5 * K; o2 = 5.0 * K
    nb = (rem(lum, X + o1, Y) + rem(lum, X - o1, Y) + rem(lum, X, Y + o1) + rem(lum, X, Y - o1) + rem(lum, X + o2, Y + o2) + rem(lum, X - o2, Y - o2)) / 6
    rl = (lum - nb) * s0r
    col = col + body * P2['Detail'] * (np.maximum(rl, 0) * 2.2 * (0.35 + light) + 0.02 * ss(0.0, 0.4, light) + 0.17 * lum * (0.6 + light))
    col = col * (1 - body * P2['Detail'] * np.clip(-rl * 2.0, 0, 0.6))
    col = col + 0.6 * edge * light * P2['Rim'] * (1 - body) * P2['Figure'] * (0.75 + 0.25 * stat)

    # ---- scan-line displacement: the head drawn as horizontal lines lifted by the photo (analog video synth)
    if P2['Lines'] > 0.001:
        Lpx = max(P2['Linespacing'] * K, 2.0)
        Dpx = 0.08 * S * P2['Lineheight']
        ky = np.arange(Lpx * 0.5, S, Lpx)
        kr = np.clip(ky.astype(np.int64), 0, S - 1)
        b = s0r[kr]                                       # (K, S)
        lm = lum[kr]
        yd = ky[:, None] - lm * Dpx * b
        val = b * (0.35 + 0.65 * lm)
        acc = np.zeros(S * S, np.float32)
        cols_ = np.broadcast_to(np.arange(S), b.shape)
        sel = b > 0.05
        yd_s, v_s, c_s = yd[sel], val[sel], cols_[sel]
        for dd in range(-2, 3):
            rr = np.floor(yd_s).astype(np.int64) + dd
            ok = (rr >= 0) & (rr < S)
            dist = np.abs(rr + 0.5 - yd_s)
            vv = (1 - ss(0.35 * K, 1.2 * K, dist)) * v_s
            np.maximum.at(acc, (rr[ok] * S + c_s[ok]), vv[ok].astype(np.float32))
        lsum = np.clip(acc.reshape(S, S), 0, 1)
        col = col + (0.62 * (0.45 + light) - col) * lsum * P2['Lines']

    # ---- tracking overlay
    if P2['Track'] > 0.001:
        ov4 = tracking(f, t, s0r, stat)
        tamt = P2['Track'] * (0.4 + 0.6 * np.maximum(max(mot, hitE), np.clip(moved * 2, 0, 1)))
        col = col + (0.85 * (0.6 + 0.4 * stat) - col) * np.clip(ov4 * tamt, 0, 1)

    # ---- scanlines, the edges sink into darkness
    col = col * (1 - P2['Scanlines'] * 0.12 * (0.5 + 0.5 * np.sin(Y * TAU / 3.0)))
    col = col * (1 + (ss(0.75, 0.3, np.sqrt((U - 0.5) ** 2 + (VI - 0.5) ** 2)) - 1) * 0.6)
    return np.clip(col, 0, 1)


def render(f):
    t = f / FPS
    hitE = burst_env(t)
    under = screen2(f, hitE * 0.8)
    ink_r, ink_g = ink_accum(f)
    vib_env = 0.15 + 0.6 * burst_env(t, tau=0.55) + 0.06 * (h21(f, 3.3) - 0.5)
    vib = float(np.clip(vib_env * PI['Vibration'], 0.0, 3.0))
    ink = ink_post(f, ink_r, ink_g, vib)
    out = ink_layer(under, ink)
    return (np.clip(out, 0, 1) * 255 + 0.5).astype(np.uint8)


def work(f):
    img = render(f)
    cv2.imwrite(os.path.join(FR, 'f%04d.png' % f), img)
    return f


if __name__ == '__main__':
    import multiprocessing as mp
    FR = ARGS.frames_dir or os.path.join(HERE, '_frames')
    os.makedirs(FR, exist_ok=True)
    frames = ARGS.preview if ARGS.preview else list(range(N))
    t0 = time.time()
    with mp.get_context('fork').Pool(min(ARGS.workers, len(frames))) as pool:
        for k, f in enumerate(pool.imap_unordered(work, frames)):
            if k % 10 == 0:
                print('frame %d/%d  %.0fs' % (k + 1, len(frames), time.time() - t0)); sys.stdout.flush()
    if ARGS.preview:
        print('preview frames in', FR)
        sys.exit(0)
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', os.path.join(FR, 'f%04d.png'),
           '-c:v', 'libx264', '-preset', 'slow', '-crf', '15', '-pix_fmt', 'yuv420p', '-tune', 'grain',
           '-movflags', '+faststart', ARGS.out]
    subprocess.run(cmd, check=True)
    print('video:', ARGS.out, '%.1f s' % (N / FPS), '%.0fs total' % (time.time() - t0))
