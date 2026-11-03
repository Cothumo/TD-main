# Artist photo loop, hologram version: the head is hidden inside a particle stream that constantly flows across the
# whole frame from the left side to the right side. It only shows where the stream passes through it.
#
# - The stream: particles enter on the left and leave on the right, carried by a current with curl-noise swirls
#   (periodic in the loop). In the head's volume they slow down and light up, brightest on its rim and on faint
#   feature contours (hairline, eyes, brow, ear, beard edge, taken from the photo's edges). So the head is a denser,
#   glowing zone of the same flow, a projection made of moving light rather than a solid shape.
# - The head's own particles: a thinner layer rests on the rim and contours (trembling), then evaporates into the
#   stream. The back of the head goes first.
# - Hologram: additive glowing particles with bloom over a dark background, fine projection scanlines, a bright scan
#   band rolling up through it twice per loop, flicker, horizontal slices that glitch sideways, and an RGB fringe
#   (chromatic split). The tint is a faint cool white (set Tint to (1, 1, 1) for pure grey).
# - On the two unstable moments (BURSTS) a gust drives the flow, the slices glitch harder and the Ambient Ink
#   vibration (ink_post.glsl: jitter, fast oscillation, row wobble, trailing second image) shakes the light.
# - Behind it, very dim: the Screen 2 haze and its far light. Everything loops seamlessly.
#
#   python render_hologram_loop.py [--size 1080] [--seconds 7] [--fps 30] [--out artist_head_hologram_loop.mp4]
#                                  [--preview N ...] [--workers 4]
import argparse, math, os, subprocess, sys, time
import numpy as np
import cv2

HERE = os.path.dirname(os.path.abspath(__file__))
ap = argparse.ArgumentParser()
ap.add_argument('--photo', default=os.path.join(HERE, 'artist_photo.jpg'))
ap.add_argument('--mask', default=os.path.join(HERE, 'head_mask.png'))
ap.add_argument('--size', type=int, default=1080)
ap.add_argument('--seconds', type=float, default=7.0)
ap.add_argument('--fps', type=int, default=30)
ap.add_argument('--out', default=os.path.join(HERE, 'artist_head_hologram_loop.mp4'))
ap.add_argument('--frames-dir', default=None)
ap.add_argument('--preview', type=int, nargs='*', default=None, help='only render these frame numbers to PNG')
ap.add_argument('--workers', type=int, default=os.cpu_count() or 4)
ap.add_argument('--seed', type=int, default=21)
ARGS = ap.parse_args()

S = ARGS.size
FPS = ARGS.fps
N = int(round(ARGS.seconds * FPS))
T = N / FPS
K = S / 720.0                      # pixel sizes below are for a 720 high frame
TAU = 2 * math.pi
rng0 = np.random.default_rng(ARGS.seed)

LOOK = dict(
    Stream=0.2,           # stream particles alive per frame pixel (density of the flow)
    Streamspeed=165.0,    # px/s (at 720) of the flow, left -> right
    Headslow=0.6,         # how much the flow slows down inside the head (it gathers there -> the head shows)
    Turbulence=1.0,       # curl-noise swirls of the flow
    Ambientglow=0.06,     # brightness of the stream outside the head
    Headglow=0.10,        # extra brightness inside the head volume
    Rim=1.25,             # the outline lights up
    Contours=1.0,         # feature contours light up
    Headdensity=0.35,     # the head's own particles (per head pixel per loop)
    Hold=2.6, Flight=2.4, # s: how long a head particle rests on the contours, then flies with the stream
    Gain=1.25,            # exposure of the light
    Bloom=0.6,            # glow around the light
    Scanlines=0.3,        # projection scanlines
    Scanband=1.0,         # bright band rolling up through the hologram
    Flicker=0.06,         # hologram flicker
    Slices=0.6,           # horizontal slices glitching sideways
    Chroma=1.6,           # px of RGB split (more on hits)
    Tint=(0.84, 0.97, 1.08),  # RGB multiplier of the light (cool white); (1, 1, 1) = grey
    Vibration=1.5,        # ink_post vibration on the light
    Backlight=0.32,       # the dim Screen 2 haze / far light behind
)
BURSTS = (1.55, 4.85)


def ss(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def h21(x, y):
    x = np.asarray(x, np.float64); y = np.asarray(y, np.float64)
    q0 = np.abs(np.modf(x * 0.1031)[0]); q1 = np.abs(np.modf(y * 0.1031)[0]); q2 = q0.copy()
    d = q0 * (q1 + 33.33) + q1 * (q2 + 33.33) + q2 * (q0 + 33.33)
    return np.modf(((q0 + d) + (q1 + d)) * (q2 + d))[0] % 1.0


def burst_env(t, tau=0.45, attack=0.06):
    e = 0.0
    for b in BURSTS:
        d = (t - b) % T
        if d < T * 0.9:
            e = max(e, (1 - math.exp(-d / attack)) * math.exp(-d / tau) / 0.85)
    return min(e, 1.0)


def bob(f):
    th = TAU * f / N
    return 5.0 * math.sin(th) + 2.0 * math.sin(2 * th + 1.0)


# ---------------------------------------------------------------- the head: volume, rim and feature contours
photo = cv2.imread(ARGS.photo, cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255.0
mask = cv2.imread(ARGS.mask, cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255.0
ys, xs = np.nonzero(mask > 0.5)
top, bot = ys.min(), ys.max()
SC = 0.84 * S / (bot - top)
OY = 0.075 * S - top * SC
M = np.float32([[SC, 0, 0], [0, SC, OY]])
HEAD = cv2.warpAffine(mask, M, (S, S), flags=cv2.INTER_LINEAR)
PH = cv2.warpAffine(photo, M, (S, S), flags=cv2.INTER_AREA)
HEAD_W = float(np.nonzero(HEAD.max(0) > 0.5)[0].max())
dist = cv2.distanceTransform((HEAD > 0.5).astype(np.uint8), cv2.DIST_L2, 5)
dist[:, :3] = 999                                    # the frame's left edge is not an outline (the photo is cut there)
g0 = cv2.GaussianBlur(PH, (0, 0), 2.2 * K / 1.5)
gx_ = cv2.Sobel(g0, cv2.CV_32F, 1, 0, ksize=3); gy_ = cv2.Sobel(g0, cv2.CV_32F, 0, 1, ksize=3)
mag = np.sqrt(gx_ * gx_ + gy_ * gy_)
can = cv2.Canny((g0 * 255).astype(np.uint8), 18, 42, L2gradient=True).astype(np.float32) / 255
can = cv2.GaussianBlur(can, (0, 0), 0.6 * K) * 2.2
g1 = cv2.GaussianBlur(PH, (0, 0), 1.4 * K / 1.5); g2 = cv2.GaussianBlur(PH, (0, 0), 4.0 * K / 1.5)
dl = ss(0.035, 0.11, g2 - g1) * ss(0.22, 0.45, g2)
lines_ = np.clip(np.maximum(can * ss(0.05, 0.15, mag) * 0.9, dl * 0.8), 0, 1) * ss(7 * K, 16 * K, dist)
lines_ *= 0.45 + 0.55 * ss(0.12, 0.3, g2)
cc_n, cc_lab, cc_st, _ = cv2.connectedComponentsWithStats((lines_ > 0.25).astype(np.uint8), 8)
cc_keep = np.zeros(cc_n, bool); cc_keep[1:] = cc_st[1:, cv2.CC_STAT_AREA] >= int(110 * K * K / 2.25)
LINES = lines_ * cc_keep[cc_lab]
_X, _Y = np.meshgrid((np.arange(S) + 0.5) / S, (np.arange(S) + 0.5) / S)
RIM = np.exp(-np.maximum(dist - 0.5, 0) / (4.0 * K / 1.5)) * (dist < 900)
RIM *= 1 - 0.75 * ss(0.62 * S, 0.7 * S, _Y * S) * (1 - ss(0.3 * S, 0.4 * S, _X * S))   # not on the cut under the beard
VOL = cv2.GaussianBlur(HEAD, (0, 0), 3 * K)
# how bright a particle is at each place of the frame (the head at rest; the bob is added per frame)
GLOW = LOOK['Ambientglow'] + LOOK['Headglow'] * VOL + LOOK['Rim'] * 0.95 * RIM + LOOK['Contours'] * LINES
GLOW = GLOW.astype(np.float32)
SLOW = cv2.GaussianBlur(HEAD, (0, 0), 10 * K).astype(np.float32)
HG = 270                                              # sampling grid for the slow-down map
SLOWG = cv2.resize(SLOW, (HG, HG), interpolation=cv2.INTER_AREA)
del _X, _Y

# ---------------------------------------------------------------- flow: periodic curl noise + the current
G = 136
CELL = S / (G - 1)


def smooth_field(sig):
    a = cv2.GaussianBlur(rng0.standard_normal((G, G)).astype(np.float32), (0, 0), sig, borderType=cv2.BORDER_REFLECT)
    return a / (a.std() + 1e-6)


VEL = np.zeros((N, G, G, 2), np.float32)
for ci, (sig, amp) in enumerate(((14.0, 45.0), (5.0, 40.0), (2.0, 22.0))):
    C = [(smooth_field(sig), smooth_field(sig)) for _ in range(3)]
    vs = []
    for f in range(N):
        th = TAU * f / N
        psi = sum(C[k][0] * math.cos(k * th + 1.3 * k * ci) - C[k][1] * math.sin(k * th + 1.3 * k * ci) for k in range(3))
        gy, gx = np.gradient(psi)
        vs.append(np.stack([gy, -gx], -1))
    vs = np.stack(vs)
    vs *= amp * K * LOOK['Turbulence'] / (np.sqrt((vs ** 2).sum(-1)).mean() + 1e-6)
    VEL += vs
GUST = np.array([burst_env(f / FPS, tau=0.7) for f in range(N)], np.float32)
VELF = VEL.reshape(-1, 2)


def sample_vel(fi, p):
    gx = np.clip(p[:, 0] / CELL, 0, G - 1.001); gy = np.clip(p[:, 1] / CELL, 0, G - 1.001)
    ix = gx.astype(np.int64); iy = gy.astype(np.int64); fx = (gx - ix)[:, None]; fy = (gy - iy)[:, None]
    b = fi * G * G + iy * G + ix
    return (VELF[b] * (1 - fx) * (1 - fy) + VELF[b + 1] * fx * (1 - fy) + VELF[b + G] * (1 - fx) * fy + VELF[b + G + 1] * fx * fy)


def sample_map(m, hg, p):
    gx = np.clip(p[:, 0] * hg / S, 0, hg - 1).astype(np.int64); gy = np.clip(p[:, 1] * hg / S, 0, hg - 1).astype(np.int64)
    return m[gy, gx]


DY = np.array([bob(f) for f in range(N)], np.float32)
dt = 1.0 / FPS

# ---------------------------------------------------------------- the stream (left -> right, across the frame)
SPD = LOOK['Streamspeed'] * K
cross_f = int(S / SPD * FPS * 1.35)                   # a typical crossing (with the slow-down) in frames
NF = int(LOOK['Stream'] * S * S * N / max(cross_f, 1))
FMAXS = N - 1
print('stream: %d particles, up to %d steps' % (NF, FMAXS)); sys.stdout.flush()
SF0 = rng0.integers(0, N, NF)
sp = rng0.uniform(0.75, 1.3, NF).astype(np.float32)
tg = rng0.uniform(0.6, 1.4, NF).astype(np.float32)[:, None]
p = np.stack([-rng0.uniform(2, 40 * K, NF), rng0.uniform(-0.04 * S, 1.04 * S, NF)], -1).astype(np.float32)
SPOS = np.empty((FMAXS, NF, 2), np.float16)
SLIFE = np.full(NF, FMAXS, np.int64)
for a in range(FMAXS):
    SPOS[a] = p
    out = (p[:, 0] > S + 12) & (SLIFE == FMAXS)
    SLIFE[out] = a
    fi = (SF0 + a) % N
    sl = sample_map(SLOWG, HG, np.stack([p[:, 0], p[:, 1] - DY[fi]], -1))
    v = sample_vel(fi, p) * tg
    vx = SPD * sp * (1 - LOOK['Headslow'] * sl) * (1 + 1.3 * GUST[fi])
    p = p + (v + np.stack([vx, np.zeros_like(vx)], -1)).astype(np.float32) * dt
    if a % 30 == 0:
        print('  stream step %d/%d' % (a, FMAXS)); sys.stdout.flush()
SLIFE = np.maximum(SLIFE, 2)
SFADE = np.minimum(1.0, SLIFE / 12.0).astype(np.float32)
del p

# ---------------------------------------------------------------- the head's own particles: rest on it, then fly
inside = HEAD > 0.04
py_, px_ = np.nonzero(inside)
wgt = HEAD[py_, px_].astype(np.float64) * (0.35 + 2.5 * np.clip(RIM[py_, px_] + LINES[py_, px_], 0, 1))
NH = int(LOOK['Headdensity'] * float(HEAD.sum()))
pick = rng0.choice(len(py_), NH, p=wgt / wgt.sum())
P0 = np.stack([px_[pick], py_[pick]], -1).astype(np.float32) + rng0.random((NH, 2)).astype(np.float32)
iy0 = np.clip(P0[:, 1].astype(int), 0, S - 1); ix0 = np.clip(P0[:, 0].astype(int), 0, S - 1)
HB = GLOW[iy0, ix0]
xn = np.clip(P0[:, 0] / HEAD_W, 0, 1)
hold = LOOK['Hold'] * (0.3 + 0.7 * (1 - xn) ** 1.1 + 0.2) * (0.55 + 0.9 * rng0.random(NH))
flight = LOOK['Flight'] * (0.6 + 0.8 * rng0.random(NH))
HOLD_F = np.maximum((hold * FPS).astype(np.int64), 1)
FL_F = np.maximum((flight * FPS).astype(np.int64), 6)
over = HOLD_F + FL_F - (N - 1)
HOLD_F = np.where(over > 0, np.maximum(HOLD_F - over, 1), HOLD_F)
FL_F = np.minimum(FL_F, N - 1 - HOLD_F)
LIFE_F = HOLD_F + FL_F
HF0 = rng0.integers(0, N, NH)
FMAXH = int(FL_F.max())
print('head: %d particles, flight steps %d' % (NH, FMAXH)); sys.stdout.flush()
HFL = np.empty((FMAXH, NH, 2), np.float16)
start = (HF0 + HOLD_F) % N
p = P0.copy(); p[:, 1] += DY[start]
lift = rng0.uniform(0.7, 1.3, NH).astype(np.float32)
tgh = rng0.uniform(0.6, 1.3, NH).astype(np.float32)[:, None]
for a in range(FMAXH):
    HFL[a] = p
    fi = (start + a) % N
    s_ = a * dt
    ramp = 1 - math.exp(-s_ / 0.7)
    v = sample_vel(fi, p) * tgh * (0.3 + 0.7 * ramp)
    vx = SPD * lift * ramp * (1 + 1.3 * GUST[fi])
    p = p + (v + np.stack([vx, np.zeros_like(vx)], -1)).astype(np.float32) * dt
del p

# ---------------------------------------------------------------- background (Screen 2 haze, very dim)
GRID = np.meshgrid(np.arange(S, dtype=np.float32), np.arange(S, dtype=np.float32))
U = (GRID[0] + 0.5) / S
VI = (GRID[1] + 0.5) / S
ROWS = np.arange(S)
NT = 256
NOISE = [rng0.random((NT, NT)).astype(np.float32) for _ in range(5)]


def fbm(px, py):
    s = np.zeros(px.shape, np.float32); a = 0.5
    for i in range(5):
        s += a * cv2.remap(NOISE[i], np.mod(px, NT).astype(np.float32), np.mod(py, NT).astype(np.float32), cv2.INTER_CUBIC, borderMode=cv2.BORDER_WRAP)
        px = px * 2.03 + 17.1; py = py * 2.03 + 9.7; a *= 0.5
    return np.clip(s / 0.96875, 0, 1)


def background(f):
    th = TAU * f / N
    hs = S // 2
    uh, vh = np.meshgrid((np.arange(hs) + 0.5) / hs, (np.arange(hs) + 0.5) / hs)
    f1 = fbm(uh * 2.0 + 0.22 * math.cos(th), vh * 2.0 + 0.22 * math.sin(th) + 3.0)
    f2 = fbm(uh * 4.5 + 0.3 * math.cos(-th + 1.0) + f1 * 1.5, vh * 4.5 + 0.3 * math.sin(-th + 1.0) + f1 * 1.5)
    fog = cv2.resize(np.clip(0.25 + 0.75 * (f1 * 0.65 + f2 * 0.35), 0, 1), (S, S), interpolation=cv2.INTER_CUBIC)
    r = np.sqrt((U - 0.55 - 0.02 * math.sin(th)) ** 2 + (VI - 0.42 - 0.02 * math.cos(th)) ** 2)
    light = (np.exp(-r / 0.4) * 0.22 + np.exp(-r / 0.9) * fog * 0.3) * LOOK['Backlight']
    return light + 0.015 * fog


# ---------------------------------------------------------------- particles -> light
def splat(img, x, y, w):
    ok = (x >= 0) & (y >= 0) & (x < S - 1) & (y < S - 1)
    x, y, w = x[ok], y[ok], w[ok]
    ix = x.astype(np.int64); iy = y.astype(np.int64); fx = x - ix; fy = y - iy
    b = iy * S + ix
    flat = img.reshape(-1)
    flat += np.bincount(b, w * (1 - fx) * (1 - fy), S * S)
    flat += np.bincount(b + 1, w * fx * (1 - fy), S * S)
    flat += np.bincount(b + S, w * (1 - fx) * fy, S * S)
    flat += np.bincount(b + S + 1, w * fx * fy, S * S)


def streak(img, p0, p1, w, taps=3):
    """a short motion streak from the last position to this one (the flow reads as moving light)"""
    for k in range(taps):
        q = p0 + (p1 - p0) * ((k + 1) / taps)
        splat(img, q[:, 0], q[:, 1], w / taps)


def glow_at(p, f):
    ix = np.clip(p[:, 0].astype(np.int64), 0, S - 1)
    iy = np.clip((p[:, 1] - DY[f]).astype(np.int64), 0, S - 1)
    return GLOW[iy, ix]


def light_frame(f):
    rng = np.random.default_rng(7000 + f)
    E = np.zeros((S, S), np.float64)
    # the stream
    a = (f - SF0) % N
    al = np.nonzero(a < SLIFE)[0]
    a = a[al]
    p1 = SPOS[a, al].astype(np.float32)
    p0 = SPOS[np.maximum(a - 1, 0), al].astype(np.float32)
    w = glow_at(p1, f) * np.minimum(1.0, (a + 1) / 4.0) * np.minimum(1.0, (SLIFE[al] - a) / 4.0)
    w = w * (0.35 + 1.3 * rng.random(len(al)) ** 2)                    # twinkle: a few bright sparks
    streak(E, p0, p1, w.astype(np.float64))
    # the head's own particles
    a = (f - HF0) % N
    al = np.nonzero(a < LIFE_F)[0]
    a = a[al]
    rest = a < HOLD_F[al]
    ri = al[rest]
    pr = P0[ri].copy(); pr[:, 1] += DY[f]
    pr += rng.normal(0, 0.5 * K / 1.5, pr.shape).astype(np.float32)
    wr = 0.6 * HB[ri] * np.minimum(a[rest] / 6.0, 1.0) * (0.3 + 1.2 * rng.random(len(ri)) ** 2)
    splat(E, pr[:, 0], pr[:, 1], wr.astype(np.float64))
    fl = al[~rest]
    s_ = a[~rest] - HOLD_F[fl]
    q1 = HFL[s_, fl].astype(np.float32)
    q0 = HFL[np.maximum(s_ - 1, 0), fl].astype(np.float32)
    u = s_ / FL_F[fl]
    wf = (HB[fl] * (1 - u) + glow_at(q1, f) * u) * (1 - u) ** 0.8 * (0.7 + 0.6 * rng.random(len(fl)))
    streak(E, q0, q1, wf.astype(np.float64))
    return E.astype(np.float32)


def vibrate(f, im, vib):
    if vib <= 0.001:
        return im
    X, Y = GRID
    fr = float(f)
    jx = h21(fr, 1.37) * 2 - 1; jy = h21(fr, 7.91) * 2 - 1
    offx = (jx * 0.65 + math.sin(fr * 2.71) * 0.35) * vib * 16.0 * K
    offy = (jy * 0.65 + math.cos(fr * 3.37) * 0.35) * vib * 16.0 * K
    rowx = np.sin(Y * (0.045 / K) + fr * 1.9) * vib * 5.0 * K
    gw = min(0.45 * vib, 0.6)
    a = cv2.remap(im, (X + offx + rowx).astype(np.float32), (Y + offy).astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    b = cv2.remap(im, (X - 1.6 * (offx + rowx)).astype(np.float32), (Y - 1.6 * offy).astype(np.float32), cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    return a * (1 - gw) + b * gw


def slices(f, im, hitE):
    """horizontal slices of the hologram jump sideways for a frame or two (more on hits)"""
    rng = np.random.default_rng(3000 + f // 2)
    off = np.zeros(S, np.float32)
    y = 0
    prob = 0.05 + 0.3 * hitE
    while y < S:
        hgt = int(rng.integers(int(4 * K), int(26 * K)))
        if rng.random() < prob * LOOK['Slices']:
            off[y:y + hgt] = rng.normal(0, 10 * K * (1 + 2 * hitE))
        y += hgt
    if not off.any():
        return im
    X, Y = GRID
    return cv2.remap(im, (X - off[:, None]).astype(np.float32), Y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)


def render(f):
    t = f / FPS
    th = TAU * f / N
    hitE = burst_env(t)
    E = light_frame(f)
    vib_env = 0.12 + 0.6 * burst_env(t, tau=0.55) + 0.05 * (h21(f, 3.3) - 0.5)
    E = vibrate(f, E, float(np.clip(vib_env * LOOK['Vibration'], 0, 3)))
    # bloom
    Eg = E + LOOK['Bloom'] * (0.55 * cv2.GaussianBlur(E, (0, 0), 2.2 * K) + 0.35 * cv2.GaussianBlur(E, (0, 0), 10 * K))
    # projection: scanlines, a bright band rolling up (two passes per loop), flicker
    Y = GRID[1]
    scan = 1 - LOOK['Scanlines'] * (0.5 + 0.5 * np.sin(Y * TAU / (2.0 * K)))
    by = (1.0 - 2.0 * t / T) % 1.0
    d = np.abs(VI - by); d = np.minimum(d, 1 - d)
    band = LOOK['Scanband'] * (0.9 * np.exp(-(d / 0.035) ** 2) + 0.6 * np.exp(-(d / 0.004) ** 2))
    flick = 1 + LOOK['Flicker'] * (h21(f, 9.9) * 2 - 1) - (0.25 if h21(f, 4.2) > 0.965 else 0.0)
    Eg = Eg * scan * (1 + band) * flick
    Eg = slices(f, Eg.astype(np.float32), hitE)
    # RGB split, tone-mapped light over the dim background
    ca = LOOK['Chroma'] * K / 1.5 * (1 + 3 * hitE)
    X = GRID[0]
    sh = lambda im, dx: cv2.remap(im, (X - dx).astype(np.float32), Y, cv2.INTER_LINEAR, borderMode=cv2.BORDER_REPLICATE)
    chans = [sh(Eg, ca), Eg, sh(Eg, -ca)]                               # R, G, B
    bg = background(f)
    rng = np.random.default_rng(11000 + f)
    grain = rng.random((S // 2 + 1, S // 2 + 1)).astype(np.float32).repeat(2, 0).repeat(2, 1)[:S, :S]
    vig = 1 + (ss(0.78, 0.3, np.sqrt((U - 0.5) ** 2 + (VI - 0.5) ** 2)) - 1) * 0.55
    out = []
    for c, tint in zip(chans, LOOK['Tint']):
        v = bg + tint * (1 - np.exp(-c * LOOK['Gain']))
        v = v + (grain - 0.5) * 0.035
        out.append(np.clip(v * vig, 0, 1))
    rgb = np.stack(out[::-1], -1)                                       # BGR for OpenCV
    return (rgb * 255 + 0.5).astype(np.uint8)


def work(f):
    cv2.imwrite(os.path.join(FR, 'f%04d.png' % f), render(f))
    return f


if __name__ == '__main__':
    import multiprocessing as mp
    FR = ARGS.frames_dir or os.path.join(HERE, '_frames_holo')
    os.makedirs(FR, exist_ok=True)
    frames = ARGS.preview if ARGS.preview else list(range(N))
    t0 = time.time()
    with mp.get_context('fork').Pool(min(ARGS.workers, len(frames))) as pool:
        for k, f in enumerate(pool.imap_unordered(work, frames)):
            if k % 10 == 0:
                print('frame %d/%d  %.0fs' % (k + 1, len(frames), time.time() - t0)); sys.stdout.flush()
    if ARGS.preview:
        print('preview frames in', FR); sys.exit(0)
    subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-framerate', str(FPS), '-i', os.path.join(FR, 'f%04d.png'),
                    '-c:v', 'libx264', '-preset', 'slow', '-crf', '20', '-pix_fmt', 'yuv420p', '-tune', 'grain',
                    '-movflags', '+faststart', ARGS.out], check=True)
    print('video:', ARGS.out, '%.1f s' % (N / FPS), '%.0fs total' % (time.time() - t0))
