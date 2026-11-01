"""Generates the animated space SVGs used by the profile README.

Every SVG has a twinkling starfield and shooting stars. Each shooting star has its own
duration and delay drawn at random, so the combined pattern only repeats after a very long
time and looks random. GitHub renders README SVGs as images: CSS animations work, scripts
do not, so "random" here means many independent, irregular timers.

usage: python3 assets/gen_space.py   (writes into assets/)
"""
import math, os, random

OUT = os.path.dirname(os.path.abspath(__file__))
BG = "#0d1117"
PURPLE = "#c9d1d9"  # accent, kept neutral


def starfield(rng, w, h, n, prefix):
    css, els = [], []
    for i in range(n):
        x, y = rng.uniform(0, w), rng.uniform(0, h)
        big = rng.random() < 0.12
        r = rng.uniform(0.9, 1.6) if big else rng.uniform(0.3, 0.9)
        col = rng.choice(["#ffffff", "#f0f3f6", "#e6edf3", "#dfe4ea"])
        lo, hi = rng.uniform(0.15, 0.45), rng.uniform(0.7, 1.0)
        d, delay = rng.uniform(2.2, 7.5), rng.uniform(0, 8)
        name = f"{prefix}tw{i}"
        css.append(f"@keyframes {name}{{0%,100%{{opacity:{lo:.2f}}}50%{{opacity:{hi:.2f}}}}}"
                   f".{name}{{animation:{name} {d:.2f}s ease-in-out {-delay:.2f}s infinite}}")
        els.append(f'<circle class="{name}" cx="{x:.1f}" cy="{y:.1f}" r="{r:.2f}" fill="{col}"/>')
        if big:
            els.append(f'<circle class="{name}" cx="{x:.1f}" cy="{y:.1f}" r="{r*3:.2f}" fill="{col}" opacity="0.12" filter="url(#{prefix}glow)"/>')
    return css, els


def shooting(rng, w, h, n, prefix):
    css, els = [], []
    for i in range(n):
        # direction: mostly falling diagonally, either way
        ang = math.radians(rng.uniform(18, 42)) * rng.choice([1, -1])
        length = rng.uniform(70, 160)
        dist = rng.uniform(w * 0.25, w * 0.55)
        dx = math.copysign(math.cos(ang) * dist, ang)
        dy = abs(math.sin(ang)) * dist
        x0 = rng.uniform(0.1 * w, 0.9 * w) - dx / 2
        y0 = rng.uniform(-0.2 * h, 0.45 * h)
        flight = rng.uniform(0.6, 1.3)
        period = rng.uniform(6, 23) + rng.random() * 0.37  # irregular, mutually "prime-ish"
        delay = rng.uniform(0, period)
        f = flight / period * 100
        name = f"{prefix}ss{i}"
        deg = math.degrees(math.atan2(dy, dx))
        tr0 = f"translate({x0:.0f}px,{y0:.0f}px) rotate({deg:.1f}deg)"
        tr1 = f"translate({x0+dx:.0f}px,{y0+dy:.0f}px) rotate({deg:.1f}deg)"
        css.append(
            f"@keyframes {name}{{0%{{transform:{tr0}}}{f:.3f}%,100%{{transform:{tr1}}}}}"
            f"@keyframes {name}o{{0%{{opacity:0}}{f*0.15:.3f}%{{opacity:1}}{f:.3f}%,100%{{opacity:0}}}}"
            f".{name}{{animation:{name} {period:.2f}s linear {-delay:.2f}s infinite}}"
            f".{name}o{{opacity:0;animation:{name}o {period:.2f}s linear {-delay:.2f}s infinite}}")
        els.append(
            f'<linearGradient id="{name}g" gradientUnits="userSpaceOnUse" x1="{-length:.0f}" y1="0" x2="0" y2="0">'
            f'<stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset="0.75" stop-color="#dfe6ee" stop-opacity="0.55"/>'
            f'<stop offset="1" stop-color="#fff"/></linearGradient>'
            f'<g class="{name}"><g class="{name}o"><path d="M{-length:.0f},0 L0,-1.3 L1.5,0 L0,1.3 Z" fill="url(#{name}g)"/>'
            f'<circle r="2.6" fill="#fff" opacity="0.35"/><circle r="1.3" fill="#fff"/></g></g>')
    return css, els


def defs(prefix):
    return (f'<defs><linearGradient id="{prefix}tail" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
            f'<stop offset="0.7" stop-color="#dfe6ee" stop-opacity="0.5"/><stop offset="1" stop-color="#fff"/></linearGradient>'
            f'<filter id="{prefix}glow" x="-200%" y="-200%" width="500%" height="500%"><feGaussianBlur stdDeviation="1.6"/></filter>'
            f'<radialGradient id="{prefix}neb1" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stop-color="#8b949e" stop-opacity="0.07"/>'
            f'<stop offset="1" stop-color="#8b949e" stop-opacity="0"/></radialGradient>'
            f'<radialGradient id="{prefix}neb2" cx="0.5" cy="0.5" r="0.5"><stop offset="0" stop-color="#6e7681" stop-opacity="0.05"/>'
            f'<stop offset="1" stop-color="#6e7681" stop-opacity="0"/></radialGradient>'
            f'<linearGradient id="{prefix}line" x1="0" x2="1"><stop offset="0" stop-color="#ffffff" stop-opacity="0"/>'
            f'<stop offset="0.5" stop-color="#ffffff" stop-opacity="0.55"/>'
            f'<stop offset="1" stop-color="#ffffff" stop-opacity="0"/></linearGradient></defs>')


def svg(w, h, body, css, prefix, extra_css=""):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">'
            f'{defs(prefix)}<style>{"".join(css)}{extra_css}</style>'
            f'<rect width="{w}" height="{h}" fill="{BG}"/>{body}</svg>')


def nebula(rng, w, h, prefix, k=2):
    out = []
    for _ in range(k):
        out.append(f'<ellipse cx="{rng.uniform(0, w):.0f}" cy="{rng.uniform(0, h):.0f}" rx="{rng.uniform(w*0.18, w*0.35):.0f}" '
                   f'ry="{rng.uniform(h*0.4, h*0.9):.0f}" fill="url(#{prefix}{rng.choice(["neb1", "neb2"])})"/>')
    return "".join(out)


HEAD_FONT = "'Fira Code','JetBrains Mono','SFMono-Regular',Menlo,Consolas,'Liberation Mono',monospace"
TITLE_FONT = "'Orbitron','Fira Code','SFMono-Regular',Menlo,Consolas,monospace"
CW = 0.6  # monospace advance, em; textLength pins every line to n * CW * size so the reveal lines up


def typed_line(key, text, size, cx, y, fill, slot0, slot1, period, prefix, loop=True):
    """A line typed character by character with a blinking cursor, then deleted (loop) or kept.

    slot0/slot1: the share of the cycle (0..1) this line owns; period: full cycle in seconds."""
    n = len(text.replace("&amp;", "&"))
    tw = n * CW * size
    x0 = cx - tw / 2
    s0, s1 = slot0 * 100, slot1 * 100
    span = s1 - s0
    t_typed = s0 + span * 0.42
    t_hold = s0 + span * (0.80 if loop else 1.0)
    t_gone = s0 + span * 0.97
    k = f"{prefix}{key}"
    if loop:
        clip = (f"@keyframes {k}c{{0%,{s0:.2f}%{{width:0}}{t_typed:.2f}%{{width:{tw:.1f}px}}{t_hold:.2f}%{{width:{tw:.1f}px}}"
                f"{t_gone:.2f}%,100%{{width:0}}}}")
        cur = (f"@keyframes {k}m{{0%,{s0:.2f}%{{transform:translateX(0)}}{t_typed:.2f}%,{t_hold:.2f}%{{transform:translateX({tw:.1f}px)}}"
               f"{t_gone:.2f}%,100%{{transform:translateX(0)}}}}"
               f"@keyframes {k}v{{0%{{opacity:0}}{s0:.2f}%{{opacity:1}}{t_gone:.2f}%{{opacity:1}}{min(t_gone+0.5, 100):.2f}%,100%{{opacity:0}}}}")
        steps = n
        css = (clip + cur + f".{k}c{{animation:{k}c {period:.2f}s steps({steps},end) infinite}}"
               f".{k}m{{animation:{k}m {period:.2f}s steps({steps},end) infinite}}"
               f".{k}v{{opacity:0;animation:{k}v {period:.2f}s steps(1,end) infinite}}")
    else:
        dur = max(0.9, n * 0.07)
        css = (f"@keyframes {k}c{{from{{width:0}}to{{width:{tw:.1f}px}}}}@keyframes {k}m{{from{{transform:translateX(0)}}to{{transform:translateX({tw:.1f}px)}}}}"
               f".{k}c{{animation:{k}c {dur:.2f}s steps({n},end) {period:.2f}s both}}"
               f".{k}m{{animation:{k}m {dur:.2f}s steps({n},end) {period:.2f}s both}}")
    els = (f'<clipPath id="{k}clip"><rect class="{k}c" x="{x0:.1f}" y="{y - size:.1f}" height="{size*1.4:.1f}" width="0"/></clipPath>'
           f'<g clip-path="url(#{k}clip)">'
           f'<text x="{x0:.1f}" y="{y}" textLength="{tw:.1f}" lengthAdjust="spacingAndGlyphs" font-family="{{font}}" '
           f'font-size="{size}" font-weight="700" fill="{fill}" filter="url(#{prefix}glow)" opacity="0.35">{text}</text>'
           f'<text x="{x0:.1f}" y="{y}" textLength="{tw:.1f}" lengthAdjust="spacingAndGlyphs" font-family="{{font}}" '
           f'font-size="{size}" font-weight="700" fill="{fill}">{text}</text></g>'
           f'<g class="{k}m"><g class="{k}v"><rect class="{prefix}blink" x="{x0 + 2:.1f}" y="{y - size*0.85:.1f}" width="{max(2, size*0.08):.1f}" '
           f'height="{size*1.0:.1f}" fill="{fill}"/></g></g>')
    return css, els


BLINK = "@keyframes {p}bl{{0%,49%{{opacity:1}}50%,100%{{opacity:0}}}}.{p}blink{{animation:{p}bl 0.9s infinite}}"


def banner():
    rng = random.Random(11); p = "b"; w, h = 1000, 260
    c1, e1 = starfield(rng, w, h, 220, p)
    c2, e2 = shooting(rng, w, h, 9, p)
    # same lines and colour as the original readme-typing-svg header
    lines = ["Hi, I'm Sachin Gupta", "SDE | Full-Stack &amp; SaaS Engineer", "Building secure, scalable platforms"]
    period = 4.6 * len(lines)
    tc, te = [], []
    for i, t in enumerate(lines):
        c, e = typed_line(f"l{i}", t, 34, 500, 145, "#f0f3f6", i / len(lines), (i + 1) / len(lines), period, p)
        tc.append(c); te.append(e.replace("{font}", HEAD_FONT))
    body = nebula(rng, w, h, p, 3) + "".join(e1) + "".join(e2) + "".join(te)
    open(os.path.join(OUT, "space-banner.svg"), "w").write(svg(w, h, body, c1 + c2 + tc + [BLINK.format(p=p)], p))


def title(name, text, seed):
    rng = random.Random(seed); p = f"t{seed}"; w, h = 1000, 130
    c1, e1 = starfield(rng, w, h, 110, p)
    c2, e2 = shooting(rng, w, h, 4, p)
    # typed once (like the old repeat=false typing titles), cursor keeps blinking
    c, e = typed_line("h", text, 34, 500, 80, "#f0f3f6", 0, 1, 0.3, p, loop=False)
    body = (nebula(rng, w, h, p, 2) + "".join(e1) + "".join(e2)
            + f'<rect x="60" y="117.4" width="880" height="1.2" fill="url(#{p}line)"/>'
            + e.replace("{font}", TITLE_FONT))
    open(os.path.join(OUT, f"title-{name}.svg"), "w").write(svg(w, h, body, c1 + c2 + [c, BLINK.format(p=p)], p))


def divider(i):
    rng = random.Random(100 + i); p = f"d{i}"; w, h = 1000, 90
    c1, e1 = starfield(rng, w, h, 80, p)
    c2, e2 = shooting(rng, w, h, 3, p)
    body = (nebula(rng, w, h, p, 1) + "".join(e1) + "".join(e2)
            + f'<rect x="40" y="{h/2 - 0.65}" width="920" height="1.3" fill="url(#{p}line)"/>'
            + f'<circle class="{p}pulse" cy="{h/2}" r="2.4" fill="#ffffff" filter="url(#{p}glow)"/>')
    pulse = (f"@keyframes {p}pm{{0%{{transform:translateX(60px)}}100%{{transform:translateX(940px)}}}}"
             f".{p}pulse{{animation:{p}pm {rng.uniform(7, 12):.2f}s linear {-rng.uniform(0, 8):.2f}s infinite}}")
    open(os.path.join(OUT, f"divider-{i}.svg"), "w").write(svg(w, h, body, c1 + c2, p, pulse))


if __name__ == "__main__":
    banner()
    for n, (k, t) in enumerate([("about", "WHO AM I?"), ("stack", "TECH STACK"), ("stats", "GITHUB STATS"),
                                ("projects", "FEATURED PROJECTS")]):
        title(k, t, 20 + n)
    for i in range(1, 7):
        divider(i)
    print("ok")


# ---------------- project cards and footer ----------------
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',Helvetica,Arial,sans-serif"

PROJECTS = [
    ("crm", "🤝", "Trio CRM", "MULTI-TENANT CRM PLATFORM",
     "Leads, customers and sales documents with appointment booking, reminders, web-push notifications and document sharing via link and WhatsApp. Hardened with separate share-link and login JWT secrets, per-user sales scoping and duplicate-payment guards.",
     [("React", "#61DAFB"), ("Node.js", "#339933"), ("Express", "#bbbbbb"), ("MongoDB", "#47A248"), ("Redis", "#DC382D"), ("JWT", "#d63aff")]),
    ("lms", "🎓", "Multi-Tenant Learning Platform", "EDTECH FOR COACHING CENTRES",
     "Scalable multi-tenant platform with RESTful services, caching, object storage, live-streaming, class recording and video-conferencing. Key endpoints load-tested and tuned through query consolidation, result reuse and ORM tuning.",
     [("Next.js", "#ffffff"), ("React", "#61DAFB"), ("Spring Boot", "#6DB33F"), ("PostgreSQL", "#4169E1"), ("WebRTC", "#aaaaaa"), ("JWT", "#d63aff")]),
    ("fee", "🏫", "Fee & Result Management", "MULTI-TENANT · SCHOOLS & COLLEGES",
     "Organization-to-school hierarchy with RBAC, rate limiting, login lockout and verified cross-tenant isolation. Query optimization and tenant-namespaced caching with single-flight locking keep heavy pages fast.",
     [("Laravel", "#FF2D20"), ("MySQL", "#4479A1"), ("Redis", "#DC382D"), ("Docker", "#2496ED"), ("Nginx", "#009639")]),
    ("payroll", "💼", "School Payroll Software", "PAYROLL & STAFF OPERATIONS",
     "Payroll runs, PDF payslips, attendance tracking, leave management and employee administration, with role-based access for staff and administrators.",
     [("Laravel", "#FF2D20"), ("Alpine.js", "#8BC0D0"), ("Tailwind", "#06B6D4"), ("MySQL", "#4479A1"), ("Docker", "#2496ED")]),
    ("qpg", "📝", "Question Paper Generator", "EXAMS FROM QUESTION BANKS",
     "Question banks organized by board, class, subject, chapter, topic, type and difficulty, with criteria-based paper generation, bulk imports and printable PDF exports with answer keys.",
     [("Laravel", "#FF2D20"), ("Tailwind", "#06B6D4"), ("MySQL", "#4479A1"), ("Docker", "#2496ED"), ("Apache", "#D22128")]),
    ("poetry", "🌸", "Poetry Store", "E-COMMERCE FOR PERSONALIZED POETRY",
     "Storefront for customizable poetry products with customer accounts, cart, Razorpay checkout and appointment requests, plus an admin dashboard for products, content, settings and analytics.",
     [("Next.js", "#ffffff"), ("TypeScript", "#3178C6"), ("Express", "#bbbbbb"), ("MongoDB", "#47A248"), ("Razorpay", "#3395FF")]),
    ("bakeree", "🥐", "Bake-Ree", "BAKERY E-COMMERCE PLATFORM",
     "Connects online ordering with bakery operations: storefront, cart and checkout for delivery or pickup, order lifecycle, kitchen coordination, coupons, loyalty points and real-time notifications.",
     [("Next.js", "#ffffff"), ("TypeScript", "#3178C6"), ("Express", "#bbbbbb"), ("MongoDB", "#47A248"), ("Socket.IO", "#cccccc")]),
]


def wrap(text, maxc):
    lines, cur = [], ""
    for wd in text.split():
        if len(cur) + len(wd) + 1 > maxc and cur:
            lines.append(cur); cur = wd
        else:
            cur = (cur + " " + wd).strip()
    return lines + [cur]


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;")


def card(key, emoji, name, sub, desc, chips, seed):
    rng = random.Random(seed); p = f"c{seed}"; w, h = 500, 300
    c1, e1 = starfield(rng, w, h, 70, p)
    c2, e2 = shooting(rng, w, h, 2, p)
    lines = wrap(desc, 62)[:6]
    txt = "".join(f'<text x="28" y="{122 + i*21}" font-family="{SANS}" font-size="14" fill="#c9d1d9">{esc(l)}</text>' for i, l in enumerate(lines))
    cx, chip_els = 28, []
    for label, col in chips:
        cw = len(label)*7.2 + 30
        chip_els.append(f'<g transform="translate({cx:.0f},258)"><rect width="{cw:.0f}" height="24" rx="12" fill="#161b22" stroke="#30363d"/>'
                        f'<circle cx="13" cy="12" r="4.5" fill="{col}"/><text x="23" y="16.5" font-family="{SANS}" font-size="12" '
                        f'font-weight="600" fill="#e6edf3">{esc(label)}</text></g>')
        cx += cw + 7
    border = (f'<linearGradient id="{p}bd" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{PURPLE}"/>'
              f'<stop offset="0.5" stop-color="#30363d"/><stop offset="1" stop-color="#6e7681" stop-opacity="0.8"/></linearGradient>')
    glow = (f"@keyframes {p}gl{{0%,100%{{opacity:0.55}}50%{{opacity:1}}}}.{p}gl{{animation:{p}gl {rng.uniform(4, 6):.1f}s ease-in-out infinite}}")
    body = (f'<defs>{border}<clipPath id="{p}cl"><rect x="1" y="1" width="{w-2}" height="{h-2}" rx="16"/></clipPath></defs>'
            f'<g clip-path="url(#{p}cl)">{nebula(rng, w, h, p, 2)}{"".join(e1)}{"".join(e2)}</g>'
            f'<rect class="{p}gl" x="1" y="1" width="{w-2}" height="{h-2}" rx="16" fill="none" stroke="url(#{p}bd)" stroke-width="2"/>'
            f'<text x="28" y="56" font-size="26">{emoji}</text>'
            f'<text x="66" y="54" font-family="{SANS}" font-size="21" font-weight="700" fill="#ffffff">{esc(name)}</text>'
            f'<text x="28" y="86" font-family="{SANS}" font-size="11.5" font-weight="700" letter-spacing="1.6" fill="#8b949e">{esc(sub)}</text>'
            f'<rect x="28" y="97" width="60" height="2" rx="1" fill="{PURPLE}"/>'
            f'{txt}<g transform="translate(28,0) scale({min(1, (w - 56)/(cx - 7 - 28)):.3f},1) translate(-28,0)">{"".join(chip_els)}</g>')
    s = svg(w, h, body, c1 + c2 + [glow], p).replace(f'<rect width="{w}" height="{h}" fill="{BG}"/>',
                                                       f'<rect width="{w}" height="{h}" rx="16" fill="{BG}"/>')
    open(os.path.join(OUT, f"card-{key}.svg"), "w").write(s)


def footer():
    rng = random.Random(77); p = "f"; w, h = 1000, 230
    c1, e1 = starfield(rng, w, h, 180, p)
    c2, e2 = shooting(rng, w, h, 7, p)
    c, e = typed_line("q", "Always learning. Always building. Always improving.", 26, 500, 95, "#f0f3f6", 0, 1, 0.4, p, loop=False)
    body = (nebula(rng, w, h, p, 3) + "".join(e1) + "".join(e2) + e.replace("{font}", HEAD_FONT)
            + f'<text class="{p}fade" x="500" y="140" text-anchor="middle" font-family="{SANS}" font-style="italic" font-size="17" fill="#8b949e">'
              f'"Turning ideas into scalable software."</text>'
            + f'<rect x="200" y="175" width="600" height="1.2" fill="url(#{p}line)"/>'
            + f'<text class="{p}fade" x="500" y="205" text-anchor="middle" font-family="{SANS}" font-size="13" letter-spacing="3" fill="#8b949e">'
              f'THANKS FOR VISITING · SEE YOU AMONG THE STARS</text>')
    fade = f"@keyframes {p}fd{{from{{opacity:0}}to{{opacity:1}}}}.{p}fade{{opacity:0;animation:{p}fd 1.2s ease 4.2s forwards}}"
    open(os.path.join(OUT, "space-footer.svg"), "w").write(svg(w, h, body, c1 + c2 + [c, BLINK.format(p=p), fade], p))


def build_extras():
    for i, pr in enumerate(PROJECTS):
        card(*pr, seed=300 + i)
    footer()


build_extras()
