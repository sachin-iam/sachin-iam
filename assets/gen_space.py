"""Generates the SVGs used by the profile README.

- space-banner.svg / space-footer.svg: starfield with twinkling and shooting stars, edges fading
  into the page background, typed text.
- title-*.svg: typed section titles with a thin fading underline, transparent background.
- divider.svg: just a thin fading line, transparent background.
- tech-stack.svg: minimal grouped pills.
- card-*.svg: project cards; tech pills never overflow, extras collapse into "+N".
  The README lists the hidden ones in a <details> under each card pair (images are not clickable).

Shooting stars each get their own random duration and delay, so the pattern looks random.
GitHub renders README SVGs as images: CSS animations work, scripts do not.

usage: python3 assets/gen_space.py   (writes into assets/, saves the overflow lists to card-overflow.json)
"""
import json, math, os, random

OUT = os.path.dirname(os.path.abspath(__file__))
BG = "#0d1117"
INK = "#f0f3f6"
MUTED = "#8b949e"
LINE = "#30363d"
PILL = "#161b22"
MONO = "'SFMono-Regular','JetBrains Mono','Fira Code',Menlo,Consolas,'Liberation Mono',monospace"
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans',Helvetica,Arial,sans-serif"
CW = 0.6  # monospace advance (em); textLength pins text to n * CW * size


def esc(t):
    return t.replace("&", "&amp;").replace("<", "&lt;")


# ---------------- sky ----------------
def starfield(rng, w, h, n, p):
    css, els = [], []
    for i in range(n):
        x, y = rng.uniform(0, w), rng.uniform(0, h)
        big = rng.random() < 0.1
        r = rng.uniform(0.9, 1.5) if big else rng.uniform(0.3, 0.85)
        lo, hi = rng.uniform(0.15, 0.4), rng.uniform(0.6, 0.95)
        d, delay = rng.uniform(2.5, 7.5), rng.uniform(0, 8)
        k = f"{p}t{i}"
        css.append(f"@keyframes {k}{{0%,100%{{opacity:{lo:.2f}}}50%{{opacity:{hi:.2f}}}}}"
                   f".{k}{{animation:{k} {d:.2f}s ease-in-out {-delay:.2f}s infinite}}")
        els.append(f'<circle class="{k}" cx="{x:.1f}" cy="{y:.1f}" r="{r:.2f}" fill="#fff"/>')
    return css, els


def shooting(rng, w, h, n, p):
    css, els = [], []
    for i in range(n):
        ang = math.radians(rng.uniform(18, 40)) * rng.choice([1, -1])
        length = rng.uniform(70, 150)
        dist = rng.uniform(w * 0.25, w * 0.5)
        dx = math.copysign(math.cos(ang) * dist, ang)
        dy = abs(math.sin(ang)) * dist
        x0 = rng.uniform(0.15 * w, 0.85 * w) - dx / 2
        y0 = rng.uniform(0.05 * h, 0.45 * h)
        flight = rng.uniform(0.7, 1.3)
        period = rng.uniform(6, 23) + rng.random() * 0.37
        delay = rng.uniform(0, period)
        f = flight / period * 100
        k = f"{p}s{i}"
        deg = math.degrees(math.atan2(dy, dx))
        tr0 = f"translate({x0:.0f}px,{y0:.0f}px) rotate({deg:.1f}deg)"
        tr1 = f"translate({x0 + dx:.0f}px,{y0 + dy:.0f}px) rotate({deg:.1f}deg)"
        # movement and fade on separate elements (combining them in one animation broke in Chrome)
        css.append(f"@keyframes {k}{{0%{{transform:{tr0}}}{f:.3f}%,100%{{transform:{tr1}}}}}"
                   f"@keyframes {k}o{{0%{{opacity:0}}{f * 0.15:.3f}%{{opacity:1}}{f:.3f}%,100%{{opacity:0}}}}"
                   f".{k}{{animation:{k} {period:.2f}s linear {-delay:.2f}s infinite}}"
                   f".{k}o{{opacity:0;animation:{k}o {period:.2f}s linear {-delay:.2f}s infinite}}")
        els.append(f'<linearGradient id="{k}g" gradientUnits="userSpaceOnUse" x1="{-length:.0f}" y1="0" x2="0" y2="0">'
                   f'<stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#fff"/></linearGradient>'
                   f'<g class="{k}"><g class="{k}o"><path d="M{-length:.0f},0 L0,-1.1 L1.4,0 L0,1.1 Z" fill="url(#{k}g)"/>'
                   f'<circle r="1.2" fill="#fff"/></g></g>')
    return css, els


def fade_masks(p, w, h, ex=0.12, ey=0.25):
    """Two masks that fade the content out toward every edge, so it melts into the page."""
    return (f'<linearGradient id="{p}fx" x1="0" x2="1" y1="0" y2="0"><stop offset="0" stop-color="#000"/>'
            f'<stop offset="{ex}" stop-color="#fff"/><stop offset="{1 - ex}" stop-color="#fff"/><stop offset="1" stop-color="#000"/></linearGradient>'
            f'<linearGradient id="{p}fy" x1="0" x2="0" y1="0" y2="1"><stop offset="0" stop-color="#000"/>'
            f'<stop offset="{ey}" stop-color="#fff"/><stop offset="{1 - ey}" stop-color="#fff"/><stop offset="1" stop-color="#000"/></linearGradient>'
            f'<mask id="{p}mx"><rect width="{w}" height="{h}" fill="url(#{p}fx)"/></mask>'
            f'<mask id="{p}my"><rect width="{w}" height="{h}" fill="url(#{p}fy)"/></mask>')


def sky_svg(w, h, p, rng, nstars, nshoot, fg_css, fg):
    c1, e1 = starfield(rng, w, h, nstars, p)
    c2, e2 = shooting(rng, w, h, nshoot, p)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">'
            f'<defs>{fade_masks(p, w, h)}</defs><style>{"".join(c1 + c2 + fg_css)}</style>'
            f'<g mask="url(#{p}mx)"><g mask="url(#{p}my)"><rect width="{w}" height="{h}" fill="{BG}"/>'
            f'{"".join(e1)}{"".join(e2)}</g></g>{fg}</svg>')


def plain_svg(w, h, css, body):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" width="{w}" height="{h}">'
            f'<style>{"".join(css)}</style>{body}</svg>')


def fading_line(p, x, y, length, opacity=0.5):
    return (f'<defs><linearGradient id="{p}ln" x1="0" x2="1"><stop offset="0" stop-color="#fff" stop-opacity="0"/>'
            f'<stop offset="0.5" stop-color="#fff" stop-opacity="{opacity}"/><stop offset="1" stop-color="#fff" stop-opacity="0"/>'
            f'</linearGradient></defs><rect x="{x}" y="{y}" width="{length}" height="1" fill="url(#{p}ln)"/>')


# ---------------- typing ----------------
BLINK = "@keyframes {p}bl{{0%,49%{{opacity:1}}50%,100%{{opacity:0}}}}.{p}blink{{animation:{p}bl 0.9s infinite}}"


def typed_line(p, key, text, size, cx, y, fill, font, weight, slot=None, period=None, delay=0.3):
    """Typed with a cursor. slot=(a, b) cycles inside a loop of `period` s; slot=None types once and stays."""
    n = len(text)
    tw = n * CW * size
    x0 = cx - tw / 2
    k = f"{p}{key}"
    if slot:
        s0, s1 = slot[0] * 100, slot[1] * 100
        span = s1 - s0
        ty, th, tg = s0 + span * 0.42, s0 + span * 0.80, s0 + span * 0.97
        css = (f"@keyframes {k}c{{0%,{s0:.2f}%{{width:0}}{ty:.2f}%,{th:.2f}%{{width:{tw:.1f}px}}{tg:.2f}%,100%{{width:0}}}}"
               f"@keyframes {k}m{{0%,{s0:.2f}%{{transform:translateX(0)}}{ty:.2f}%,{th:.2f}%{{transform:translateX({tw:.1f}px)}}"
               f"{tg:.2f}%,100%{{transform:translateX(0)}}}}"
               f"@keyframes {k}v{{0%{{opacity:0}}{s0:.2f}%{{opacity:1}}{tg:.2f}%{{opacity:1}}{min(tg + 0.5, 100):.2f}%,100%{{opacity:0}}}}"
               f".{k}c{{animation:{k}c {period:.2f}s steps({n},end) infinite}}"
               f".{k}m{{animation:{k}m {period:.2f}s steps({n},end) infinite}}"
               f".{k}v{{opacity:0;animation:{k}v {period:.2f}s steps(1,end) infinite}}")
    else:
        dur = max(0.9, n * 0.07)
        css = (f"@keyframes {k}c{{from{{width:0}}to{{width:{tw:.1f}px}}}}"
               f"@keyframes {k}m{{from{{transform:translateX(0)}}to{{transform:translateX({tw:.1f}px)}}}}"
               f".{k}c{{animation:{k}c {dur:.2f}s steps({n},end) {delay:.2f}s both}}"
               f".{k}m{{animation:{k}m {dur:.2f}s steps({n},end) {delay:.2f}s both}}")
    body = (f'<clipPath id="{k}clip"><rect class="{k}c" x="{x0:.1f}" y="{y - size:.1f}" height="{size * 1.4:.1f}" width="0"/></clipPath>'
            f'<text clip-path="url(#{k}clip)" x="{x0:.1f}" y="{y}" textLength="{tw:.1f}" lengthAdjust="spacingAndGlyphs" '
            f'font-family="{font}" font-size="{size}" font-weight="{weight}" fill="{fill}">{esc(text)}</text>'
            f'<g class="{k}m"><g class="{k}v"><rect class="{p}blink" x="{x0 + 2:.1f}" y="{y - size * 0.85:.1f}" '
            f'width="{max(2, size * 0.07):.1f}" height="{size:.1f}" fill="{fill}"/></g></g>')
    return css, body


# ---------------- pieces ----------------
def banner():
    rng = random.Random(11); p = "b"; w, h = 1000, 240
    lines = ["Hi, I'm Sachin Gupta", "SDE | Full-Stack & SaaS Engineer", "Building secure, scalable platforms"]
    period = 4.6 * len(lines)
    css, fg = [BLINK.format(p=p)], []
    for i, t in enumerate(lines):
        c, b = typed_line(p, f"l{i}", t, 32, 500, 132, INK, MONO, 600, (i / 3, (i + 1) / 3), period)
        css.append(c); fg.append(b)
    open(os.path.join(OUT, "space-banner.svg"), "w").write(sky_svg(w, h, p, rng, 200, 8, css, "".join(fg)))


def footer():
    rng = random.Random(77); p = "f"; w, h = 1000, 200
    c, b = typed_line(p, "q", "Always learning. Always building. Always improving.", 22, 500, 92, INK, MONO, 500)
    fade = f"@keyframes {p}fd{{from{{opacity:0}}to{{opacity:1}}}}.{p}fade{{opacity:0;animation:{p}fd 1.2s ease 4s forwards}}"
    fg = (b + f'<text class="{p}fade" x="500" y="130" text-anchor="middle" font-family="{SANS}" font-style="italic" '
              f'font-size="15" fill="{MUTED}">"Turning ideas into scalable software."</text>')
    open(os.path.join(OUT, "space-footer.svg"), "w").write(sky_svg(w, h, p, rng, 150, 6, [c, BLINK.format(p=p), fade], fg))


def title(name, text, seed):
    p = f"t{seed}"; w, h = 1000, 80
    c, b = typed_line(p, "h", text, 22, 500, 44, INK, MONO, 600)
    body = b + fading_line(p, 300, 66, 400, 0.35)
    open(os.path.join(OUT, f"title-{name}.svg"), "w").write(plain_svg(w, h, [c, BLINK.format(p=p)], body))


def divider():
    w, h = 1000, 24
    open(os.path.join(OUT, "divider.svg"), "w").write(plain_svg(w, h, [], fading_line("d", 100, 12, 800, 0.28)))


def pill(x, y, label, size=12, padx=11, hgt=26):
    tw = len(label) * CW * size
    pw = tw + 2 * padx
    return pw, (f'<g transform="translate({x:.1f},{y:.1f})"><rect width="{pw:.1f}" height="{hgt}" rx="{hgt / 2}" fill="{PILL}" '
                f'stroke="{LINE}"/><text x="{padx}" y="{hgt / 2 + size * 0.36:.1f}" textLength="{tw:.1f}" lengthAdjust="spacingAndGlyphs" '
                f'font-family="{MONO}" font-size="{size}" fill="#e6edf3">{esc(label)}</text></g>')


STACK = [
    ("Languages", ["Java", "JavaScript", "TypeScript", "SQL"]),
    ("Frontend", ["React.js", "Next.js", "Tailwind CSS"]),
    ("Backend", ["Node.js", "Express.js", "REST APIs", "JWT Authentication"]),
    ("Databases", ["MongoDB", "MySQL", "PostgreSQL", "Redis"]),
    ("Tools & DevOps", ["Git", "Docker", "Nginx", "k6", "GitHub Actions"]),
    ("Core Concepts", ["Authentication", "Authorization", "RBAC", "Caching", "Rate Limiting"]),
]


def tech_stack():
    w, rowh, top = 1000, 46, 10
    h = top + rowh * len(STACK)
    els = []
    for i, (cat, items) in enumerate(STACK):
        y = top + i * rowh
        els.append(f'<text x="120" y="{y + 18}" font-family="{SANS}" font-size="13" font-weight="600" fill="{MUTED}" '
                   f'letter-spacing="1">{esc(cat.upper())}</text>')
        x = 300
        for it in items:
            pw, g = pill(x, y, it)
            els.append(g); x += pw + 8
    open(os.path.join(OUT, "tech-stack.svg"), "w").write(plain_svg(w, h, [], "".join(els)))


# Tech lists are the portfolio's verified ones (My-Portfolio/client/src/data/projects.js), main ones first.
PROJECTS = [
    ("crm", "Trio CRM", "MULTI-TENANT CRM PLATFORM",
     "Leads, customers and sales documents with appointment booking, reminders, web-push notifications and document sharing via link and WhatsApp. Hardened with separate share-link and login JWT secrets, per-user sales scoping and duplicate-payment guards.",
     ["React", "Node.js", "Express.js", "MongoDB", "Redis", "JWT", "JavaScript", "Vite", "Tailwind CSS", "TanStack Query", "React Flow",
      "Dagre", "Mongoose", "bcryptjs", "BullMQ", "Stripe Checkout", "React Native", "Expo", "Expo Notifications", "Docker", "Docker Compose"]),
    ("lms", "Multi-Tenant Learning Platform", "EDTECH FOR COACHING CENTRES",
     "Scalable multi-tenant platform with RESTful services, caching, object storage, live-streaming, class recording and video-conferencing. Key endpoints load-tested and tuned through query consolidation, result reuse and ORM tuning.",
     ["React", "TypeScript", "Spring Boot", "PostgreSQL", "Java", "Vite", "Tailwind CSS", "Spring Security", "JPA", "Flyway",
      "Agora Cloud Recording", "OvenMediaEngine", "WebSocket / STOMP", "FFmpeg", "HLS", "MinIO", "ShedLock", "Docker Compose", "Bash"]),
    ("fee", "Fee & Result Management", "MULTI-TENANT · SCHOOLS & COLLEGES",
     "Organization-to-school hierarchy with RBAC, rate limiting, login lockout and verified cross-tenant isolation. Query optimization and tenant-namespaced caching with single-flight locking keep heavy pages fast.",
     ["Laravel", "PHP", "MariaDB", "Redis", "Docker", "Nginx", "Alpine.js", "Tailwind CSS", "Vite", "Laravel Horizon", "Laravel Reverb",
      "Chart.js", "Blade", "Predis", "Pusher", "Laravel Echo", "Axios", "GrapesJS", "Lenis", "Browsershot", "DOMPDF", "Maatwebsite Excel",
      "OpenSpout", "PHP-FPM", "Supervisor", "Cloudflare", "GitHub Actions", "PHPUnit", "Paratest", "Mockery", "Faker", "Larastan",
      "PHPStan", "Laravel Pint", "Composer", "Playwright", "ESLint", "Prettier", "k6", "Sentry", "Node.js"]),
    ("payroll", "School Payroll Software", "PAYROLL & STAFF OPERATIONS",
     "Payroll runs, PDF payslips, attendance tracking, leave management and employee administration, with role-based access for staff and administrators.",
     ["Laravel 12", "PHP", "MySQL", "Alpine.js", "Tailwind CSS", "Laravel Blade", "JavaScript", "Vite", "Eloquent ORM", "Laravel Dompdf",
      "PhpSpreadsheet", "Docker", "Docker Compose"]),
    ("qpg", "Question Paper Generator", "EXAMS FROM QUESTION BANKS",
     "Question banks organized by board, class, subject, chapter, topic, type and difficulty, with criteria-based paper generation, bulk imports and printable PDF exports with answer keys.",
     ["Laravel 12", "PHP", "MySQL", "Tailwind CSS 4", "Laravel Blade", "JavaScript", "Vite", "Jodit", "Eloquent ORM",
      "Spatie Laravel Permission", "Dompdf", "PhpSpreadsheet", "PhpWord", "Docker", "Docker Compose", "Apache"]),
    ("poetry", "Poetry Store", "E-COMMERCE FOR PERSONALIZED POETRY",
     "Storefront for customizable poetry products with customer accounts, cart, Razorpay checkout and appointment requests, plus an admin dashboard for products, content, settings and analytics.",
     ["Next.js", "TypeScript", "Express", "MongoDB", "Razorpay", "React", "Tailwind CSS", "Framer Motion", "dnd-kit", "Recharts",
      "Node.js", "JavaScript", "Mongoose", "JWT", "bcryptjs", "Multer", "Nodemailer", "Docker", "Nginx"]),
    ("bakeree", "Bake-Ree", "BAKERY E-COMMERCE PLATFORM",
     "Connects online ordering with bakery operations: storefront, cart and checkout for delivery or pickup, order lifecycle, kitchen coordination, coupons, loyalty points and real-time notifications.",
     ["Next.js 15", "TypeScript", "Express 5", "MongoDB", "Socket.IO", "React 19", "JavaScript", "Tailwind CSS 4", "Zustand", "Axios",
      "Framer Motion", "Recharts", "Lucide React", "Node.js", "JWT", "bcryptjs", "Mongoose", "socket.io-client", "Nodemailer"]),
]


def wrap(text, maxc):
    lines, cur = [], ""
    for wd in text.split():
        if len(cur) + len(wd) + 1 > maxc and cur:
            lines.append(cur); cur = wd
        else:
            cur = (cur + " " + wd).strip()
    return lines + [cur]


def card(key, name, sub, desc, techs):
    """Writes card-<key>.svg and returns the tech that did not fit (shown as "+N" on the card)."""
    w, h, pad, gap, y = 500, 300, 28, 6, 252
    lines = wrap(desc, 58)[:6]
    txt = "".join(f'<text x="{pad}" y="{110 + i * 21}" font-family="{SANS}" font-size="14" fill="#c9d1d9">{esc(l)}</text>'
                  for i, l in enumerate(lines))
    right = w - pad
    shown, x = [], pad
    for i, t in enumerate(techs):
        pw = pill(0, 0, t, 11, 9, 24)[0]
        rest = len(techs) - i - 1
        more_w = gap + pill(0, 0, f"+{rest}", 11, 9, 24)[0] if rest else 0
        if x + pw + more_w > right:
            break
        shown.append(pill(x, y, t, 11, 9, 24)[1]); x += pw + gap
    hidden = techs[len(shown):]
    if hidden:
        shown.append(pill(x, y, f"+{len(hidden)}", 11, 9, 24)[1].replace(f'fill="{PILL}"', 'fill="#21262d"'))
    body = (f'<rect x="0.5" y="0.5" width="{w - 1}" height="{h - 1}" rx="14" fill="{BG}" stroke="{LINE}"/>'
            f'<text x="{pad}" y="52" font-family="{SANS}" font-size="20" font-weight="700" fill="{INK}">{esc(name)}</text>'
            f'<text x="{pad}" y="78" font-family="{SANS}" font-size="11" font-weight="600" letter-spacing="1.5" fill="{MUTED}">{esc(sub)}</text>'
            f'{txt}{"".join(shown)}')
    open(os.path.join(OUT, f"card-{key}.svg"), "w").write(plain_svg(w, h, [], body))
    return hidden


if __name__ == "__main__":
    for f in os.listdir(OUT):
        if f.startswith(("divider-", "title-", "card-")) and f.endswith(".svg"):
            os.remove(os.path.join(OUT, f))
    banner(); footer(); divider(); tech_stack()
    for n, (k, t) in enumerate([("about", "WHO AM I?"), ("stack", "TECH STACK"), ("stats", "GITHUB STATS"),
                                ("projects", "FEATURED PROJECTS")]):
        title(k, t, 20 + n)
    overflow = {pr[0]: card(*pr) for pr in PROJECTS}
    with open(os.path.join(OUT, "card-overflow.json"), "w") as fh:
        json.dump(overflow, fh, indent=1)
    print({k: len(v) for k, v in overflow.items()})
