# Artist photo loop, "evaporating" version: the whole head is made of noise particles that constantly drift off to the
# right, so the portrait looks like it is evaporating. The Screen 2 backlit haze is behind it, and the Ambient Ink
# vibration shakes the particles.
#
# Every particle is born inside the head (head_mask.png) and takes the photo's tone at that spot, so together the
# resting particles draw the portrait. Each one holds still (trembling) for a while, then lifts off: a current that
# speeds up carries it to the right, and curl-noise turbulence and buoyancy tear the streams into smoke. It fades as
# it goes. Particles near the outline and at the back of the head leave sooner than the ones in the face, so the head
# is thinner and more eroded on the right and the face stays readable. On the two unstable moments (BURSTS) a gust
# drives the streams and the ink_post vibration (jitter, fast oscillation, row wobble, trailing second image) shakes
# the whole particle layer.
# Everything is periodic in the loop length, so the video loops seamlessly.
#
#   python render_evaporate_loop.py [--size 1080] [--seconds 7] [--fps 30] [--out artist_head_evaporate_loop.mp4]
#                                   [--density 3.6] [--preview N ...] [--workers 4]
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
ap.add_argument('--density', type=float, default=3.6, help='particles born per head pixel per loop')
ap.add_argument('--out', default=os.path.join(HERE, 'artist_head_evaporate_loop.mp4'))
ap.add_argument('--frames-dir', default=None)
ap.add_argument('--preview', type=int, nargs='*', default=None, help='only render these frame numbers to PNG')
ap.add_argument('--workers', type=int, default=os.cpu_count() or 4)
ap.add_argument('--seed', type=int, default=11)
ARGS = ap.parse_args()

S = ARGS.size
FPS = ARGS.fps
N = int(round(ARGS.seconds * FPS))
T = N / FPS
K = S / 720.0
TAU = 2 * math.pi
rng0 = np.random.default_rng(ARGS.seed)

# Screen 2 background (haze + light + analog TV) and the particle look
P2 = dict(Haze=1.5, Light=1.25, Lightsize=0.32, Lightx=0.6, Lighty=0.34, Chaos=0.6, Ambient=0.4, Snow=0.5,
          Scanlines=0.4, pads=0.4)
PP = dict(Hold=3.2,            # s: how long a face particle rests before it evaporates (the back of the head: less)
          Flight=2.6,          # s: mean flight time to fade out
          Current=230.0,       # px/s (at 720 high) the current reaches to the right
          Rise=45.0,           # px/s upward drift (buoyancy)
          Turbulence=1.0,      # curl-noise strength
          Coverage=1.35,       # how opaque the resting particles are
          Shimmer=0.07,        # per-frame tone noise of each particle
          Tremble=0.55,        # px of per-frame jitter of the resting particles
          Dust=1.9,            # how dense / visible the evaporating particles are
          Vibration=1.5)       # ink_post Vibration
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


# ---------------------------------------------------------------- the head in the frame
photo = cv2.imread(ARGS.photo, cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255.0
mask = cv2.imread(ARGS.mask, cv2.IMREAD_GRAYSCALE).astype(np.float32) / 255.0
ys, xs = np.nonzero(mask > 0.5)
top, bot = ys.min(), ys.max()
SC = 0.84 * S / (bot - top)
OY = 0.075 * S - top * SC
M = np.float32([[SC, 0, 0], [0, SC, OY]])
HEAD = cv2.warpAffine(mask, M, (S, S), flags=cv2.INTER_LINEAR)
TONE = cv2.warpAffine(np.clip((photo - 0.03) / 0.93, 0, 1) ** 1.05, M, (S, S), flags=cv2.INTER_AREA)
HEAD_W = float(np.nonzero(HEAD.max(0) > 0.5)[0].max())


def bob(f):
    th = TAU * f / N
    return 5.0 * math.sin(th) + 2.0 * math.sin(2 * th + 1.0)


# ---------------------------------------------------------------- flow: periodic curl noise + a current to the right
G = 136
CELL = S / (G - 1)


def smooth_field(sig):
    a = cv2.GaussianBlur(rng0.standard_normal((G, G)).astype(np.float32), (0, 0), sig, borderType=cv2.BORDER_REFLECT)
    return a / (a.std() + 1e-6)


VEL = np.zeros((N, G, G, 2), np.float32)
for ci, (sig, amp) in enumerate(((12.0, 80.0), (4.0, 75.0), (1.8, 40.0))):
    C = [(smooth_field(sig), smooth_field(sig)) for _ in range(3)]
    vs = []
    for f in range(N):
        th = TAU * f / N
        psi = sum(C[k][0] * math.cos(k * th + 1.3 * k * ci) - C[k][1] * math.sin(k * th + 1.3 * k * ci) for k in range(3))
        gy, gx = np.gradient(psi)
        vs.append(np.stack([gy, -gx], -1))
    vs = np.stack(vs)
    vs *= amp * K / 1.5 * PP['Turbulence'] / (np.sqrt((vs ** 2).sum(-1)).mean() + 1e-6)
    VEL += vs
GUST = np.array([burst_env(f / FPS, tau=0.7) for f in range(N)], np.float32)
VELF = VEL.reshape(-1, 2)


def sample_vel(fi, p):
    gx = np.clip(p[:, 0] / CELL, 0, G - 1.001); gy = np.clip(p[:, 1] / CELL, 0, G - 1.001)
    ix = gx.astype(np.int64); iy = gy.astype(np.int64); fx = (gx - ix)[:, None]; fy = (gy - iy)[:, None]
    b = fi * G * G + iy * G + ix
    return (VELF[b] * (1 - fx) * (1 - fy) + VELF[b + 1] * fx * (1 - fy) + VELF[b + G] * (1 - fx) * fy + VELF[b + G + 1] * fx * fy)


# ---------------------------------------------------------------- particles
inside = HEAD > 0.04
py_, px_ = np.nonzero(inside)
wgt = HEAD[py_, px_].astype(np.float64)
area = float(HEAD.sum())
NP = int(ARGS.density * area)
pick = rng0.choice(len(py_), NP, p=wgt / wgt.sum())
P0 = np.stack([px_[pick], py_[pick]], -1).astype(np.float32) + rng0.random((NP, 2)).astype(np.float32)
TN = TONE[np.clip(P0[:, 1].astype(int), 0, S - 1), np.clip(P0[:, 0].astype(int), 0, S - 1)].astype(np.float32)
# distance to the outline: the edge sheds first
dist = cv2.distanceTransform((HEAD > 0.5).astype(np.uint8), cv2.DIST_L2, 5)
dist[:, :3] = 999                                             # the frame's left edge is not an outline (photo cut)
DE = dist[np.clip(P0[:, 1].astype(int), 0, S - 1), np.clip(P0[:, 0].astype(int), 0, S - 1)]
xn = np.clip(P0[:, 0] / HEAD_W, 0, 1)
hold = PP['Hold'] * (0.35 + 0.65 * (1 - xn) ** 1.1 + 0.25) * (0.55 + 0.9 * rng0.random(NP))
hold *= 0.35 + 0.65 * ss(0.0, 34.0 * K, DE)
flight = PP['Flight'] * (0.6 + 0.8 * rng0.random(NP))
HOLD_F = np.maximum((hold * FPS).astype(np.int64), 1)
FL_F = np.maximum((flight * FPS).astype(np.int64), 6)
over = HOLD_F + FL_F - (N - 1)
HOLD_F = np.where(over > 0, np.maximum(HOLD_F - over, 1), HOLD_F)  # a life must fit in the loop
FL_F = np.minimum(FL_F, N - 1 - HOLD_F)
LIFE_F = HOLD_F + FL_F
F0 = rng0.integers(0, N, NP)                                       # births spread evenly over the loop -> steady
FMAX = int(FL_F.max())
DY = np.array([bob(f) for f in range(N)], np.float32)
print('%d particles (head area %.0f px), flight steps %d' % (NP, area, FMAX)); sys.stdout.flush()

# flight paths, simulated from the moment each particle lifts off
FL = np.empty((FMAX, NP, 2), np.float16)
start = (F0 + HOLD_F) % N
p = P0.copy(); p[:, 1] += DY[start]
lift = rng0.uniform(0.7, 1.3, NP).astype(np.float32)
tg = rng0.uniform(0.6, 1.3, NP).astype(np.float32)[:, None]
dt = 1.0 / FPS
cur = PP['Current'] * K / 1.5
rise = PP['Rise'] * K / 1.5
for a in range(FMAX):
    FL[a] = p
    fi = (start + a) % N
    s_ = a * dt
    ramp = 1 - np.exp(-s_ / 0.9)                                     # it peels off slowly, then is carried away
    v = sample_vel(fi, p) * tg * (0.25 + 0.75 * ramp)
    vx = cur * lift * (ramp * (0.35 + 0.65 * min(s_ / 2.0, 1.0))) * (1 + 1.4 * GUST[fi])
    vy = -rise * lift * ramp
    p = p + (v + np.stack([vx, vy], -1)).astype(np.float32) * dt
    if a % 20 == 0:
        print('  step %d/%d' % (a, FMAX)); sys.stdout.flush()
del p

# ---------------------------------------------------------------- Screen 2 background
GRID = np.meshgrid(np.arange(S, dtype=np.float32), np.arange(S, dtype=np.float32))
U = (GRID[0] + 0.5) / S
VI = (GRID[1] + 0.5) / S
ROWS = np.arange(S)
VYr = 1.0 - (ROWS + 0.5) / S
NT = 256
NOISE = [rng0.random((NT, NT)).astype(np.float32) for _ in range(5)]


def fbm(px, py):
    s = np.zeros(px.shape, np.float32); a = 0.5
    for i in range(5):
        s += a * cv2.remap(NOISE[i], np.mod(px, NT).astype(np.float32), np.mod(py, NT).astype(np.float32), cv2.INTER_CUBIC, borderMode=cv2.BORDER_WRAP)
        px = px * 2.03 + 17.1; py = py * 2.03 + 9.7; a *= 0.5
    return np.clip(s / 0.96875, 0, 1)


def background(f, hitE):
    t = f / FPS; th = TAU * f / N
    CH, AMB = P2['Chaos'], P2['Ambient']
    rng = np.random.default_rng(5000 + f)
    hs = S // 2
    uh, vh = np.meshgrid((np.arange(hs) + 0.5) / hs, (np.arange(hs) + 0.5) / hs)
    # the haze drifts with the evaporation: slowly to the right, on a loop (circle in noise space + periodic shift)
    f1 = fbm(uh * 2.0 + 0.22 * math.cos(th) - 0.0, vh * 2.0 + 0.22 * math.sin(th) + 3.0)
    f2 = fbm(uh * 4.5 + 0.3 * math.cos(-th + 1.0) + f1 * 1.5, vh * 4.5 + 0.3 * math.sin(-th + 1.0) + f1 * 1.5)
    fog = cv2.resize(np.clip(0.25 + 0.75 * (f1 * 0.65 + f2 * 0.35), 0, 1), (S, S), interpolation=cv2.INTER_CUBIC)
    Lx = P2['Lightx'] + 0.02 * math.sin(th); Ly = P2['Lighty'] + 0.02 * math.cos(th)
    r = np.sqrt((U - Lx) ** 2 + (VI - Ly) ** 2)
    size = P2['Lightsize']
    hz = min(P2['Haze'] * (0.55 + 0.9 * P2['pads']), 2.5)
    level = 0.5 + 0.3 * math.sin(2 * th) + 0.25 * hitE
    core = np.exp(-r * r / (size * size * 0.06)) * (1 - 0.55 * min(hz, 1.0))
    light = np.minimum(core * 0.7 + np.exp(-r / size) * 0.22 + np.exp(-r / (size * 2.2)) * fog * hz * 0.36, 0.8) * (0.8 + 0.2 * level) * P2['Light']
    col = light + 0.02 * fog * hz
    grain = rng.random((S // 2 + 1, S // 2 + 1)).astype(np.float32).repeat(2, 0).repeat(2, 1)[:S, :S]
    drive = max(AMB, hitE)
    by = (0.3 - t / T) % 1.0
    bdy = np.abs(VYr - by); bdy = np.minimum(bdy, 1 - bdy)
    bandT = (1 - ss(0.0, 0.045, bdy)) * CH * (0.3 + 0.7 * drive)
    snow = np.clip(P2['Snow'] * (0.4 * hitE * 0.3 + 0.4 * AMB * CH) + bandT[:, None] * 1.2, 0, 1)
    col = col + (grain * (0.25 + 0.6 * light) + 0.03 - col) * snow * 0.7
    lnr = np.floor((ROWS + 0.5) * 720.0 / S)
    x0 = h21(lnr, f + 11.0); dl = 0.05 + 0.25 * h21(lnr, f + 5.0)
    on = h21(lnr, f * 3.7 + 0.31) > 1 - 0.01 * CH * (AMB * 0.6 + hitE + bandT * 4)
    drop = (on[:, None] & (U >= x0[:, None]) & (U <= (x0 + dl)[:, None])).astype(np.float32)
    col = col + (0.5 * (0.35 + light) - col) * drop * 0.7
    return col, light, grain, bandT


# ---------------------------------------------------------------- particles -> picture
RAD_BINS = np.array([0.0, 1.2, 2.2, 3.6, 6.0, 1e9])


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


def particles(f, light):
    rng = np.random.default_rng(9000 + f)
    a = (f - F0) % N
    alive = a < LIFE_F
    idx = np.nonzero(alive)[0]
    a = a[idx]
    resting = a < HOLD_F[idx]
    # resting: on the portrait, trembling; the tone shimmers like noise
    ri = idx[resting]
    pr = P0[ri].copy()
    pr[:, 1] += DY[f]
    pr += rng.normal(0, PP['Tremble'] * K / 1.5, pr.shape).astype(np.float32)
    ar = a[resting]
    fade_in = np.minimum(ar / 6.0, 1.0)                               # born softly (6 frames)
    wr = fade_in.astype(np.float32)
    tr = TN[ri] + rng.normal(0, PP['Shimmer'], len(ri)).astype(np.float32)
    # flying: along the simulated path, growing, fading, catching the backlight
    fi_ = idx[~resting]
    s_ = (a[~resting] - HOLD_F[fi_])
    pf = FL[s_, fi_].astype(np.float32)
    u = s_ / FL_F[fi_]
    wf = (PP['Dust'] * (1 - u) ** 1.2 * np.minimum(s_ / 4.0, 1.0)).astype(np.float32)
    lx = np.clip(pf[:, 0].astype(int), 0, S - 1); ly = np.clip(pf[:, 1].astype(int), 0, S - 1)
    e = np.minimum(u * 2.2, 1.0) * 0.85
    tf = TN[fi_] * (1 - e) + (0.66 + 0.2 * light[ly, lx] - 0.4 * ss(0.5, 0.8, light[ly, lx])) * e + rng.normal(0, PP['Shimmer'], len(fi_)).astype(np.float32)
    rad = 0.55 + 1.1 * u * K / 1.5
    W = np.zeros((S, S), np.float64); TW = np.zeros((S, S), np.float64)
    splat(W, pr[:, 0], pr[:, 1], wr); splat(TW, pr[:, 0], pr[:, 1], wr * tr)
    for lo, hi in zip(RAD_BINS[:-1], RAD_BINS[1:]):
        m = (rad >= lo) & (rad < hi)
        if not m.any():
            continue
        w2 = np.zeros((S, S), np.float64); t2 = np.zeros((S, S), np.float64)
        splat(w2, pf[m, 0], pf[m, 1], wf[m]); splat(t2, pf[m, 0], pf[m, 1], wf[m] * tf[m])
        sig = float(np.median(rad[m])) / 2.0
        if sig > 0.5:
            w2 = cv2.GaussianBlur(w2, (0, 0), sig); t2 = cv2.GaussianBlur(t2, (0, 0), sig)
        W += w2; TW += t2
    return W.astype(np.float32), TW.astype(np.float32)


def vibrate(f, imgs, vib):
    """ink_post.glsl vibration on the particle layer: jitter + fast oscillation + row wobble + a trailing second image"""
    if vib <= 0.001:
        return imgs
    X, Y = GRID
    fr = float(f)
    jx = h21(fr, 1.37) * 2 - 1; jy = h21(fr, 7.91) * 2 - 1
    offx = (jx * 0.65 + math.sin(fr * 2.71) * 0.35) * vib * 16.0 * K
    offy = (jy * 0.65 + math.cos(fr * 3.37) * 0.35) * vib * 16.0 * K
    rowx = np.sin(Y * (0.045 / K) + fr * 1.9) * vib * 5.0 * K
    m1 = ((X + offx + rowx).astype(np.float32), (Y + offy).astype(np.float32))
    m2 = ((X - 1.6 * (offx + rowx)).astype(np.float32), (Y - 1.6 * offy).astype(np.float32))
    gw = min(0.45 * vib, 0.6)
    out = []
    for im in imgs:
        a = cv2.remap(im, m1[0], m1[1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        b = cv2.remap(im, m2[0], m2[1], cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        out.append(a * (1 - gw) + b * gw)
    return out


def render(f):
    t = f / FPS
    hitE = burst_env(t)
    col, light, grain, bandT = background(f, hitE * 0.8)
    W, TW = particles(f, light)
    vib_env = 0.12 + 0.6 * burst_env(t, tau=0.55) + 0.05 * (h21(f, 3.3) - 0.5)
    W, TW = vibrate(f, [W, TW], float(np.clip(vib_env * PP['Vibration'], 0, 3)))
    tone = np.clip(TW / np.maximum(W, 1e-4), 0, 1)
    A = 1 - np.exp(-W * PP['Coverage'])
    col = col + (tone - col) * A
    # the tracking band and grain also run over the particles a little (one signal)
    col = col + (grain * (0.25 + 0.6 * light) + 0.03 - col) * np.clip(bandT[:, None] * 0.5, 0, 1) * 0.5
    Y = GRID[1]
    col = col * (1 - P2['Scanlines'] * 0.12 * (0.5 + 0.5 * np.sin(Y * TAU / 3.0)))
    col = col * (1 + (ss(0.75, 0.3, np.sqrt((U - 0.5) ** 2 + (VI - 0.5) ** 2)) - 1) * 0.6)
    return (np.clip(col, 0, 1) * 255 + 0.5).astype(np.uint8)


def work(f):
    cv2.imwrite(os.path.join(FR, 'f%04d.png' % f), render(f))
    return f


if __name__ == '__main__':
    import multiprocessing as mp
    FR = ARGS.frames_dir or os.path.join(HERE, '_frames_evap')
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
                    '-c:v', 'libx264', '-preset', 'slow', '-crf', '15', '-pix_fmt', 'yuv420p', '-tune', 'grain',
                    '-movflags', '+faststart', ARGS.out], check=True)
    print('video:', ARGS.out, '%.1f s' % (N / FPS), '%.0fs total' % (time.time() - t0))
