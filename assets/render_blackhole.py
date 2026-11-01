"""Offline port of My-Portfolio's black hole lens shader (scene/shaders.js).

Backward ray trace of Schwarzschild null geodesics (u'' = -u + 1.5u^2, RK4) per pixel,
Kerr (a = 0.6) disk kinematics, blackbody colour at T0 * flux^(1/4) * g, intensity ~ g^4,
spin shadow offset, faint corona, lensed stars. The geodesics are static, so they are traced
once; each frame only re-evaluates the time-dependent disk turbulence (period T = 30 r_s/c,
which makes the animation loop seamlessly).

usage: python render.py OUT_DIR [frames] [width] [height] [supersample]
"""
import sys, os, math
import numpy as np
from multiprocessing import Pool
from PIL import Image

OUT = sys.argv[1]
FRAMES = int(sys.argv[2]) if len(sys.argv) > 2 else 90
W = int(sys.argv[3]) if len(sys.argv) > 3 else 960
Hh = int(sys.argv[4]) if len(sys.argv) > 4 else 440
SS = int(sys.argv[5]) if len(sys.argv) > 5 else 2

# --- model (same constants as the portfolio) ---
SPINA = 0.6
RH = 1 + math.sqrt(1 - SPINA**2)  # in M units -> convert to r_s below
RH = RH / 2.0                      # r_s = 2M -> 0.9
def kerr_isco(a):
    z1 = 1 + (1 - a*a)**(1/3) * ((1 + a)**(1/3) + (1 - a)**(1/3))
    z2 = math.sqrt(3*a*a + z1*z1)
    return (3 + z2 - math.sqrt((3 - z1)*(3 + z1 + 2*z2))) / 2.0  # r_s
ISCO = kerr_isco(SPINA)           # ~1.91
T0 = 4200.0
OUTER = 14.0
EXPOSURE = float(os.environ.get("EXP", 1.6))
SHADOW_SCH = 3*math.sqrt(3)/2
KAPPA_BASE = 0.5 * SPINA / SHADOW_SCH
BG = np.array([13, 17, 23]) / 255.0   # GitHub dark background (#0d1117)
FOV = 30.0
DIST = float(os.environ.get("DIST", 28.0))
ELEV = float(os.environ.get("ELEV", 0.30))
TILT = -0.16
HSTEP = 0.08
MAXSTEPS = 420
U_OUT = 1/60.0
SPIN = np.array([0.0, -1.0, 0.0])
EX = np.array([1.0, 0, 0]); EZ = np.array([0, 0, 1.0])
KMAX = 5

def dot(a, b): return (np.asarray(a)*np.asarray(b)).sum(-1)

def blackbody(k):
    t = np.clip(k, 1000, 40000) / 100.0
    r = np.where(t <= 66, 1.0, np.clip(1.292936 * np.power(np.maximum(t - 60, 1e-6), -0.1332047592), 0, 1))
    g = np.where(t <= 66, np.clip(0.390081579 * np.log(t) - 0.631841444, 0, 1),
                 np.clip(1.129890861 * np.power(np.maximum(t - 60, 1e-6), -0.0755148492), 0, 1))
    b = np.where(t >= 66, 1.0, np.where(t <= 19, 0.0, np.clip(0.543206789 * np.log(np.maximum(t - 10, 1e-6)) - 1.196254089, 0, 1)))
    return np.stack([r, g, b], -1)

def omega_disk(r):
    rr = np.maximum(r, ISCO)
    w = 2.0 / (np.power(2*rr, 1.5) + SPINA)
    q = ISCO / np.minimum(r, ISCO)
    return w * q * q

def ut_disk(r):
    rr = 2.0 * np.maximum(r, ISCO); s = np.sqrt(rr)
    return (rr*s + SPINA) / (np.power(rr, 0.75) * np.sqrt(np.maximum(rr*s - 3*s + 2*SPINA, 1e-3)))

def disk_g(r, lam, obsR):
    g = 1.0 / (ut_disk(r) * np.maximum(1.0 - omega_disk(r) * lam, 0.15))
    g = np.where(r < ISCO, g * np.sqrt(np.maximum((r - RH) / (ISCO - RH), 0)), g)
    return g / math.sqrt(max(1 - 1/obsR, 0.05))

def disk_flux(r):
    x0 = 1.3611 * ISCO
    f0 = x0**-3 * (1 - math.sqrt(ISCO / x0))
    out = np.power(r, -3.0) * (1 - np.sqrt(ISCO / np.maximum(r, ISCO))) / f0
    q = np.clip((r - RH) / (ISCO - RH), 0, 1)
    return np.where(r <= ISCO, 0.05*q*q, out)

def fract(x): return x - np.floor(x)
def hash13(p):
    p = fract(p * 0.1031)
    d = (p * (p[..., ::-1] + 31.32)).sum(-1)  # dot(p, p.zyx + 31.32)
    p = p + d[..., None]
    return fract((p[..., 0] + p[..., 1]) * p[..., 2])

def vnoise(p):
    i = np.floor(p); f = p - i
    f = f*f*(3 - 2*f)
    def h(dx, dy, dz): return hash13(i + np.array([dx, dy, dz], float))
    fx, fy, fz = f[..., 0], f[..., 1], f[..., 2]
    mix = lambda a, b, t: a + (b - a)*t
    return mix(mix(mix(h(0,0,0), h(1,0,0), fx), mix(h(0,1,0), h(1,1,0), fx), fy),
               mix(mix(h(0,0,1), h(1,0,1), fx), mix(h(0,1,1), h(1,1,1), fx), fy), fz)

def turb(r, th, t):
    ang = th - omega_disk(r) * t
    lr = np.log(r)
    a = np.stack([np.cos(ang)*2.2, np.sin(ang)*2.2, lr*3.4], -1)
    arms = vnoise(a)*0.6 + vnoise(a*2.2 + 7.1)*0.28 + vnoise(a*4.6 + 3.3)*0.12
    g = np.stack([np.cos(ang)*10, np.sin(ang)*10, lr*15], -1) + 11.3
    grain = vnoise(g)*0.6 + vnoise(g*2.1 + 5.0)*0.4
    return arms*0.8 + grain*0.5

def disk_density(r, th, sim):
    T = 30.0
    ta = sim % T; tb = (sim + 0.5*T) % T
    wa = 1 - abs(2*ta/T - 1)
    n = turb(r, th, tb) + (turb(r, th, ta) - turb(r, th, tb)) * wa
    return np.clip(0.28 + 2.3*(n - 0.6), 0.03, 1.7)

def disk_sample(r, th, lam, sim, flare=0.0):
    g = disk_g(r, lam, DIST)
    flux = disk_flux(r)
    # overfeeding: the inner disk heats up (same form as the portfolio's uFlare), and the whole disk glows wider
    t9 = np.clip((r - 9.0)/(ISCO - 9.0), 0, 1)
    flux = flux*(1 + flare*3.0*t9*t9*(3 - 2*t9))*(1 + 0.6*flare)
    dens = disk_density(r, th, sim)
    def ss(e0, e1, x):
        t = np.clip((x - e0)/(e1 - e0), 0, 1); return t*t*(3 - 2*t)
    edge = ss(OUTER, OUTER - 4, r) * ss(RH*1.02, RH*1.25, r)
    T = T0 * np.power(np.maximum(flux, 1e-4), 0.25) * g
    I = np.power(g, 4) * flux * dens * edge
    opac = (0.95 + (0.35 - 0.95)*ss(5.0, OUTER, r)) * np.clip(dens, 0, 1) * edge
    return blackbody(T) * I[..., None], np.clip(opac, 0, 0.97)

def stars(d):
    out = np.zeros(d.shape[:-1] + (3,))
    # two layers: the shader's sparse bright layer plus a denser faint one (artistic)
    for scale, thr, sig, gain, tint in ((19.0, 0.84, 0.0016, 0.75, (0.85, 0.9, 1.0)),
                                        (46.0, 0.80, 0.0030, 0.30, (1.0, 0.95, 0.88))):
        p = d*scale; c = np.floor(p); h = hash13(c)
        pos = c + 0.25 + 0.5*np.stack([hash13(c + 1.7), hash13(c + 5.3), hash13(c + 9.1)], -1)
        dd = np.linalg.norm(p - pos, axis=-1)
        s = np.exp(-dd*dd/sig) * (0.25 + 0.75*fract(h*37.0)) * (h >= thr)
        out += np.array(tint) * (s*gain)[..., None]
    return out

def starfield(w, h, seed=7):
    """Round catalogue stars, lensed by a point mass: theta_pm = (beta +- sqrt(beta^2 + 4 thE^2)) / 2.
    Einstein radius for a source at infinity: thE = sqrt(2 r_s / D) (r_s = 1)."""
    rng = np.random.default_rng(seed)
    px = 2*math.tan(math.radians(FOV)/2)/h          # radians per pixel (small-angle)
    thE = math.sqrt(2.0/DIST)/px                     # Einstein radius, pixels
    n = int(w*h/1800)
    bx = rng.uniform(-0.6, 0.6, n)*w; by = rng.uniform(-0.6, 0.6, n)*h
    flux = np.minimum(rng.pareto(1.6, n)*0.08 + 0.03, 1.4)
    tint = np.where(rng.random(n)[:, None] < 0.7, [0.85, 0.9, 1.0], [1.0, 0.9, 0.78])
    beta = np.hypot(bx, by) + 1e-6; ux, uy = bx/beta, by/beta
    q = np.sqrt(beta*beta + 4*thE*thE)
    uu = beta/thE
    mu0 = (uu*uu + 2)/(2*uu*np.sqrt(uu*uu + 4))
    img = np.zeros((h, w, 3))
    sig = 0.55*SS
    R = int(math.ceil(3*sig))
    for th_, mu in (((beta + q)/2, mu0 + 0.5), ((beta - q)/2, mu0 - 0.5)):
        x = w/2 + ux*th_; y = h/2 - uy*th_
        a = flux*np.minimum(mu, 3.0)
        for xi, yi, ai, ti in zip(x, y, a, tint):
            if ai < 0.01 or not (R <= xi < w - R and R <= yi < h - R): continue
            x0, y0 = int(xi), int(yi)
            yy, xx = np.mgrid[y0 - R:y0 + R + 1, x0 - R:x0 + R + 1]
            gk = np.exp(-((xx - xi)**2 + (yy - yi)**2)/(2*sig*sig))
            img[y0 - R:y0 + R + 1, x0 - R:x0 + R + 1] += gk[..., None]*ti*ai
    return img

def trace():
    w, h = W*SS, Hh*SS
    cam = np.array([0.0, DIST*math.sin(ELEV), DIST*math.cos(ELEV)])
    fwd = -cam/np.linalg.norm(cam)
    right = np.cross(fwd, [0, 1, 0]); right /= np.linalg.norm(right)
    up = np.cross(right, fwd)
    cr, sr = math.cos(TILT), math.sin(TILT)
    right, up = cr*right + sr*up, -sr*right + cr*up
    th = math.tan(math.radians(FOV)/2)
    xs = ((np.arange(w) + 0.5)/w*2 - 1) * th * w/h
    ys = (1 - (np.arange(h) + 0.5)/h*2) * th
    X, Y = np.meshgrid(xs, ys)
    dirs = fwd + X[..., None]*right + Y[..., None]*up
    dirs = (dirs/np.linalg.norm(dirs, axis=-1, keepdims=True)).reshape(-1, 3)
    N = dirs.shape[0]

    D = DIST; C = cam/D
    c0 = dot(dirs, -C)
    s0 = np.sqrt(np.maximum(1 - c0*c0, 0))
    et = (dirs + c0[:, None]*C) / np.maximum(s0, 1e-6)[:, None]
    b0 = D*s0/math.sqrt(1 - 1/D)
    pa = np.cross(C, SPIN); pa /= np.linalg.norm(pa)
    sinI = math.sqrt(max(1 - float(dot(C, SPIN))**2, 0))
    kappa = KAPPA_BASE * sinI
    b = b0/(1 - kappa*dot(et, pa))
    lam = -b0*dot(np.cross(C, et), SPIN)
    u = np.full(N, 1/D)
    w_ = np.sqrt(np.maximum(1/(b*b) - u*u*(1 - u), 0)) * np.where(c0 >= 0, 1, -1)
    A = float(dot(C, SPIN)); B = dot(et, SPIN)
    cs = np.ones(N); sn = np.zeros(N); g0 = np.full(N, A)

    cr_r = np.full((N, KMAX), np.nan); cr_th = np.zeros((N, KMAX))
    corona = np.zeros((N, KMAX + 1)); ncross = np.zeros(N, int)
    escaped = np.zeros(N, bool); escdir = dirs.copy()
    idx = np.arange(N)
    COSH, SINH = math.cos(HSTEP), math.sin(HSTEP)
    F = lambda x: -x + 1.5*x*x
    Bv = B.copy(); etv = et.copy()
    for i in range(MAXSTEPS):
        if idx.size == 0: break
        uu, ww = u[idx], w_[idx]
        k1u, k1w = ww, F(uu)
        k2u, k2w = ww + 0.5*HSTEP*k1w, F(uu + 0.5*HSTEP*k1u)
        k3u, k3w = ww + 0.5*HSTEP*k2w, F(uu + 0.5*HSTEP*k2u)
        k4u, k4w = ww + HSTEP*k3w, F(uu + HSTEP*k3u)
        u1 = uu + HSTEP/6*(k1u + 2*k2u + 2*k3u + k4u)
        w1 = ww + HSTEP/6*(k1w + 2*k2w + 2*k3w + k4w)
        c_, s_ = cs[idx], sn[idx]
        cs1 = c_*COSH - s_*SINH; sn1 = s_*COSH + c_*SINH
        g1 = A*cs1 + Bv[idx]*sn1
        gg0 = g0[idx]
        rm = 2/(uu + u1)
        zz = rm*0.5*(gg0 + g1); sc = 0.35*rm
        jc = np.where((u1 > 0) & (rm > 0) & (rm < 9), np.exp(-zz*zz/(2*sc*sc))*np.exp(-(rm - ISCO)*0.4)*HSTEP*rm, 0)
        k = ncross[idx]
        np.add.at(corona, (idx, np.minimum(k, KMAX)), 0.010*jc/rm)
        hit = (gg0*g1 < 0)
        if hit.any():
            t = gg0[hit]/(gg0[hit] - g1[hit])
            uc = uu[hit] + (u1[hit] - uu[hit])*t
            r = 1/uc
            ok = (uc > 0) & (r < OUTER) & (k[hit] < KMAX)
            ii = idx[hit][ok]; r = r[ok]; t = t[ok]
            ph = (i + t)*HSTEP
            P = np.cos(ph)[:, None]*C + np.sin(ph)[:, None]*etv[ii]
            thv = np.arctan2(dot(P, EZ), dot(P, EX))
            kk = ncross[ii]
            cr_r[ii, kk] = r; cr_th[ii, kk] = thv
            ncross[ii] += 1
        cap = u1 >= 1.0
        esc = (w1 < 0) & (u1 <= 0)
        if esc.any():
            # exact asymptotic direction: the orbital angle where u reaches 0 (r = infinity)
            e = idx[esc]
            tt = uu[esc]/(uu[esc] - u1[esc])
            ph = (i + tt)*HSTEP
            v = np.cos(ph)[:, None]*C + np.sin(ph)[:, None]*etv[e]
            escdir[e] = v/np.linalg.norm(v, axis=-1, keepdims=True)
            escaped[e] = True
        u[idx] = u1; w_[idx] = w1; cs[idx] = cs1; sn[idx] = sn1; g0[idx] = g1
        idx = idx[~(cap | esc)]
    # rays still running at MAXSTEPS: treat as escaped along the current direction
    escaped[idx] = True
    st = starfield(w, h).reshape(-1, 3)
    return dict(r=cr_r, th=cr_th, lam=lam, corona=corona, n=ncross, escaped=escaped, stars=st, w=w, h=h,
                cam=cam, fwd=fwd, right=right, up=up, tanh=th)

G = None
# ---------------- story: feed -> overfeed -> burst (flash, shock, twin jets) -> calm ----------------
def sstep(e0, e1, x):
    t = np.clip((x - e0)/(e1 - e0), 0, 1); return t*t*(3 - 2*t)

# timeline (same beats as the original blackhole.svg, 10 s loop):
#   0.00-0.40 feeding: clumps fall in from every side, a big star is tidally stretched and swallowed at 0.40
#   0.40-0.56 overfed: the hole goes white, twin gamma-ray jets fire up and down, debris is thrown out
#   0.56-1.00 settles back to calm while feeding resumes
PB, PE = 0.40, 0.56
def flare_level(p):
    up = sstep(0.05, PB, p)
    down = np.where(p < PE, 1.0, np.exp(-(p - PE)/0.05))
    return float(up*down*sstep(1.0, 0.92, p))

def project(P):
    v = P - G['cam']; z = v @ G['fwd'] if v.ndim == 1 else (v*G['fwd']).sum(-1)
    xs = (v*G['right']).sum(-1)/z; ys = (v*G['up']).sum(-1)/z
    th = G['tanh']; w, h = G['w'], G['h']
    return ((xs/(th*w/h)) + 1)/2*w - 0.5, (1 - ys/th)/2*h - 0.5, z

def splat(img, x, y, sig, rgb):
    h, w, _ = img.shape
    R = int(math.ceil(3*sig)) + 1
    x0, x1 = max(int(x) - R, 0), min(int(x) + R + 1, w)
    y0, y1 = max(int(y) - R, 0), min(int(y) + R + 1, h)
    if x0 >= x1 or y0 >= y1: return
    yy, xx = np.mgrid[y0:y1, x0:x1]
    img[y0:y1, x0:x1] += np.exp(-((xx - x)**2 + (yy - y)**2)/(2*sig*sig))[..., None]*np.asarray(rgb)

RNG = np.random.default_rng(5)
CLUMPS = []
for i in range(22):
    if i < 13: p0 = 0.0 + 0.30*i/13 + RNG.uniform(0, 0.02)     # feeding run-up
    else:      p0 = 0.55 + 0.33*(i - 13)/9 + RNG.uniform(0, 0.02)  # feeding resumes
    CLUMPS.append(dict(p0=p0, dur=RNG.uniform(0.12, 0.18), r0=RNG.uniform(16, 24), ph0=RNG.uniform(0, 2*math.pi),
                       y0=RNG.uniform(-7, 7), turns=RNG.uniform(0.5, 0.9), m=RNG.uniform(1.0, 1.8),
                       col=[(1.0, 0.95, 0.85), (1.0, 0.78, 0.55), (0.85, 0.6, 1.0), (1.0, 0.6, 0.35)][i % 4]))
STAR = dict(p0=0.02, dur=PB - 0.02, r0=26, ph0=2.3, y0=9, turns=0.55, m=4.0, col=(1.0, 0.97, 0.9))
DEBRIS = [dict(ang=RNG.uniform(0, 2*math.pi), sp=RNG.uniform(0.6, 1.0), col=[(1, 1, 1), (1, 0.85, 0.7), (0.8, 0.6, 1.0)][i % 3])
          for i in range(26)]

def clump_pos(c, u):
    """Inspiral from far out: radius shrinks to the horizon, angle advances faster as it falls."""
    u = np.clip(u, 0, 1)
    r = RH + (c['r0'] - RH)*(1 - u)**1.6
    ph = c['ph0'] + 2*math.pi*c['turns']*(1 - ((r - RH)/(c['r0'] - RH))**0.6)
    y = c['y0']*((r - RH)/(c['r0'] - RH))**1.2
    return np.stack([r*np.cos(ph), y, r*np.sin(ph)], -1), r

def draw_body(fx, c, p, trans_img, cx, cy, sh, px, size, ntrail=24):
    h, w = G['h'], G['w']
    u = (p - c['p0'])/c['dur']
    if u <= 0 or u >= 1.03: return
    us = u - np.linspace(0, 0.16, ntrail)
    P, r = clump_pos(c, us)
    X, Y, Z = project(P)
    for k in range(ntrail):
        if us[k] < 0: break
        rr = r[k]
        heat = np.clip(2.0/(rr - RH*0.95), 0.25, 3.0)
        fade = np.clip((rr - RH)/0.8, 0, 1)
        a = c['m']*heat*fade*(1 - k/ntrail)**1.2*0.9*24/ntrail
        x, y = X[k], Y[k]
        d = P[k] @ G['fwd']
        behind = d > 0
        dx, dy = x - cx, y - cy; b = math.hypot(dx, dy) + 1e-6
        if behind:
            thE = math.sqrt(2*d/(DIST*(DIST + d)))/px
            t = (b + math.sqrt(b*b + 4*thE*thE))/2
            x, y = cx + dx/b*t, cy + dy/b*t
            if t < sh*1.02: continue
        ix, iy = int(np.clip(x, 0, w - 1)), int(np.clip(y, 0, h - 1))
        occl = trans_img[iy, ix] if behind else 1.0
        # tidal stretching: the body shrinks across and stretches along the orbit as it falls
        sig = size*SS*(1 - 0.6*min(u, 1)**2)*(1 - 0.5*k/ntrail)
        splat(fx, x, y, max(sig, 0.7*SS), np.array(c['col'])*a*occl)

def effects(p, trans_img):
    h, w = G['h'], G['w']
    fx = np.zeros((h, w, 3))
    px = 2*G['tanh']/h
    sh = (SHADOW_SCH*math.sqrt(1 - 1/DIST)/DIST)/px
    cx, cy, _ = project(np.zeros(3))
    pxs = 1/(DIST*px)
    for c in CLUMPS:
        draw_body(fx, c, p, trans_img, cx, cy, sh, px, 2.4, ntrail=70)
    draw_body(fx, STAR, p, trans_img, cx, cy, sh, px, 6.0, ntrail=90)
    yy, xx = np.mgrid[0:h, 0:w]
    rr2 = (xx - cx)**2 + (yy - cy)**2
    # burst envelope: snaps on at PB, holds, releases by PE + 0.03
    env = sstep(PB - 0.004, PB + 0.02, p)*(1 - sstep(PE - 0.03, PE + 0.03, p))
    if env > 0:
        q = p - PB
        grow = 1 - math.exp(-max(q, 0)/0.03)
        white = np.array([1.0, 0.98, 0.95])
        # the hole itself goes white-hot, glow balloons outward (like the original whiteglow 130 -> 280)
        core = np.exp(-rr2/(2*(sh*0.95)**2))*5.0
        halo = np.exp(-rr2/(2*(sh*(1.3 + 1.0*grow))**2))*0.45
        wide = np.exp(-rr2/(2*(sh*(2.6 + 2.0*grow))**2))*0.07
        fx += (core + halo + wide)[..., None]*white*env
        # shock shell
        R = sh*1.2 + w*0.6*grow
        fx += (np.exp(-((np.sqrt(rr2) - R)/(2*SS + R*0.03))**2)*0.18*(1 - grow*0.7))[..., None]*np.array([0.75, 0.7, 1.0])*env
        # twin gamma-ray jets along the spin axis, shooting past the frame edges
        L = 90*grow + 2
        for sgn in (1, -1):
            sv = np.linspace(1.0, L, 420)
            P = np.stack([np.zeros_like(sv), sgn*sv, np.zeros_like(sv)], -1)
            X, Y, Z = project(P)
            for k in range(len(sv)):
                s_ = sv[k]; x, y = X[k], Y[k]
                if not (-60 < x < w + 60 and -60 < y < h + 60): continue
                knots = 1 + 1.4*math.exp(-(((s_ - 160*q) % 22) - 11)**2/6.0)
                base = env*math.exp(-s_/90)*knots*0.07
                wid = (0.3 + 0.025*s_)*pxs
                splat(fx, x, y, max(wid*0.3, 1.0*SS), np.array([0.9, 0.95, 1.0])*base*2.2)
                splat(fx, x, y, max(wid, 2.0*SS), np.array([0.62, 0.78, 1.0])*base*0.45)
        # debris thrown out in every direction
        for dbr in DEBRIS:
            dist_ = (sh*1.3 + w*0.55*dbr['sp']*grow)
            x = cx + math.cos(dbr['ang'])*dist_; y = cy + math.sin(dbr['ang'])*dist_*0.75
            fade = max(1 - grow*1.1, 0)
            for k in range(6):
                t = dist_ - k*4*SS
                splat(fx, cx + math.cos(dbr['ang'])*t, cy + math.sin(dbr['ang'])*t*0.75, 1.3*SS,
                      np.array(dbr['col'])*1.4*fade*env*(1 - k/6))
    return fx

def frame(fi):
    p = fi/FRAMES
    sim = 60.0*p
    fl = flare_level(p)
    r, th, lam, corona = G['r'], G['th'], G['lam'], G['corona']
    N = r.shape[0]
    acc = np.zeros((N, 3)); trans = np.ones(N)
    for k in range(KMAX + 1):
        acc += trans[:, None]*np.array([0.75, 0.82, 1.0])*corona[:, k][:, None]*(1 + 4*fl)
        if k == KMAX: break
        m = ~np.isnan(r[:, k])
        if not m.any(): continue
        rgb, a = disk_sample(r[m, k], th[m, k], lam[m], sim, fl)
        acc[m] += trans[m][:, None]*rgb
        trans[m] *= 1 - a
    esc = G['escaped']
    c = acc + G['stars']*trans[:, None]
    c = c + effects(p, trans.reshape(G['h'], G['w'])).reshape(-1, 3)
    col = 1 - np.exp(-c*EXPOSURE) + np.where(esc[:, None], BG*trans[:, None], 0)
    img = np.clip(col, 0, 1).reshape(G['h'], G['w'], 3)
    im = Image.fromarray((img*255 + np.random.default_rng(fi).uniform(-0.5, 0.5, img.shape)).clip(0, 255).astype(np.uint8))
    if SS > 1: im = im.resize((W, Hh), Image.LANCZOS)
    im.save(os.path.join(OUT, f"f{fi:03d}.png"))
    return fi

def init(g):
    global G; G = g

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    import time; t0 = time.time()
    g = trace(); print("traced", round(time.time() - t0, 1), "s", flush=True)
    with Pool(os.cpu_count(), initializer=init, initargs=(g,)) as pool:
        ONLY = os.environ.get('ONLY')
        todo = [int(x) for x in ONLY.split(',')] if ONLY else range(FRAMES)
        for _ in pool.imap_unordered(frame, todo): pass
    print("frames", round(time.time() - t0, 1), "s")
