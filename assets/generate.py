#!/usr/bin/env python3
"""Regenerate the arcade-trail SVG cards from public GitHub data.

Usage:  python assets/generate.py
Needs:  `gh` logged in (repo + language data), stdlib only.
Writes: hero.svg, projects.svg, space-shooter.svg, snake.svg, social.svg, README.md
"""

import base64
import html
import json
import math
import re
import subprocess
import urllib.request
from datetime import date, timedelta
from pathlib import Path

LOGIN = "Rajshalem5"
OUT = Path(__file__).resolve().parent
ROOT = OUT.parent

W = 860
COLS, ROWS, CELL, GAP = 53, 7, 11, 3
PITCH = CELL + GAP
GX, GY = 46, 106                      # grid origin inside a 264-tall card
GRID_W = COLS * PITCH - GAP

BG0, BG1 = "#0d1117", "#161b22"
INK = "rgba(8,8,12,0.5)"
ACC, GREEN, PURPLE, CYAN = "#58a6ff", "#39d353", "#a371f7", "#22d3ee"
TEXT, MUTED, DIM = "#e6edf3", "#8b949e", "#bedcff"
MONO = "ui-monospace,'SF Mono',SFMono-Regular,Menlo,Consolas,monospace"
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"

# level -> (fill, opacity): index 0 = no activity, 1..4 = contribution levels
LEVEL = [("", 0), (TEXT, .07), (ACC, .34), (ACC, .55), (ACC, 1)]

CSS = """<style>
.orb-a{animation:fa 9s ease-in-out infinite}
.orb-b{animation:fb 11s ease-in-out infinite 1.1s}
.orb-c{animation:fc 13s ease-in-out infinite .6s}
.chip{animation:rise .6s ease-out both}
.chip:nth-of-type(2){animation-delay:.12s}
.chip:nth-of-type(3){animation-delay:.24s}
.chip:nth-of-type(4){animation-delay:.36s}
.cursor{animation:blink 1.1s step-end infinite}
.pulse{animation:pulse 1.8s ease-in-out infinite}
.cell{animation:pop 9s linear infinite;opacity:.3}
.trail{stroke-dasharray:1;stroke-dashoffset:1;animation:draw 9s linear infinite}
.ship{animation:sweep 9s ease-in-out infinite alternate}
.laser{animation:fire 1.3s linear infinite}
.boom{animation:boom 5.5s ease-out infinite;opacity:0}
.star{animation:twinkle 4s ease-in-out infinite}
.bar{animation:barin 1.15s cubic-bezier(.2,.8,.2,1) both;transform-box:fill-box;transform-origin:left}
.badge{animation:rise .6s ease-out both}
@keyframes barin{from{transform:scaleX(0)}to{transform:scaleX(1)}}
@keyframes fa{0%,100%{transform:translate(0,0);opacity:.58}50%{transform:translate(28px,-20px);opacity:.86}}
@keyframes fb{0%,100%{transform:translate(0,0);opacity:.42}50%{transform:translate(-24px,18px);opacity:.72}}
@keyframes fc{0%,100%{transform:translate(0,0) scale(1);opacity:.34}50%{transform:translate(18px,-12px) scale(1.18);opacity:.62}}
@keyframes rise{from{opacity:0;transform:translateY(8px)}to{opacity:1;transform:translateY(0)}}
@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.25}}
@keyframes pop{0%{opacity:.18}6%{opacity:1}70%{opacity:.95}86%,100%{opacity:.18}}
@keyframes draw{0%{stroke-dashoffset:1;opacity:.9}82%{stroke-dashoffset:0;opacity:.9}97%,100%{stroke-dashoffset:0;opacity:0}}
@keyframes sweep{0%{transform:translateX(0)}100%{transform:translateX(720px)}}
@keyframes fire{0%{transform:translateY(0);opacity:0}10%{opacity:1}80%{opacity:.9}100%{transform:translateY(-96px);opacity:0}}
@keyframes boom{0%,72%{opacity:0;transform:scale(.2)}78%{opacity:.9;transform:scale(1)}88%,100%{opacity:0;transform:scale(1.7)}}
@keyframes twinkle{0%,100%{opacity:.15}50%{opacity:.6}}
</style>"""

ORB = ((ACC, ".72"), (GREEN, ".5"), (PURPLE, ".72"), (CYAN, ".5"))


def gh(path):
    out = subprocess.run(["gh", "api", path], capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit(f"gh api {path} failed: {out.stderr.strip()}")
    return json.loads(out.stdout)


def esc(s):
    return html.escape(s or "", quote=True)


def fit(s, limit):
    s = " ".join((s or "").split())
    return s if len(s) <= limit else s[: limit - 1].rstrip(" ,.;") + "…"


# ---------------------------------------------------------------- data

def fetch_contributions(login):
    url = f"https://github.com/users/{login}/contributions"
    req = urllib.request.Request(url, headers={"User-Agent": "readme-generator"})
    page = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    cells = [
        (m.group(1), int(m.group(2)))
        for m in re.finditer(r'data-date="([\d-]+)"[^>]*data-level="(\d)"', page)
    ]
    tips = [html.unescape(t).strip() for t in re.findall(r"<tool-tip[^>]*>([^<]*)</tool-tip>", page)]
    if not cells:
        raise SystemExit("no contribution cells parsed")

    def count(tip):
        if tip.startswith("No contributions"):
            return 0
        m = re.match(r"(\d+) contribution", tip)
        return int(m.group(1)) if m else 0

    counts = {cells[i][0]: count(tips[i]) for i in range(min(len(cells), len(tips)))}
    first = date.fromisoformat(cells[0][0])
    start = first - timedelta(days=(first.weekday() + 1) % 7)
    last = date.fromisoformat(max(c[0] for c in cells))
    nweeks = (last - start).days // 7 + 1
    weeks = [[None] * ROWS for _ in range(nweeks)]
    for d, level in cells:
        idx = (date.fromisoformat(d) - start).days
        weeks[idx // 7][idx % 7] = {"d": d, "c": counts.get(d, 0), "l": level}
    return weeks, start, last


def stats(weeks):
    flat = [c for w in weeks for c in w if c]
    total = sum(c["c"] for c in flat)
    active = sum(1 for c in flat if c["c"] > 0)
    best = cur = 0
    for c in flat:
        cur = cur + 1 if c["c"] > 0 else 0
        best = max(best, cur)
    streak = 0
    for c in reversed(flat):
        if c["c"] > 0:
            streak += 1
        else:
            break
    bestday = max(flat, key=lambda c: c["c"])
    return {"total": total, "active": active, "best": best, "streak": streak,
            "bestday": bestday["d"], "bestdayn": bestday["c"]}


def avatar_b64(url):
    req = urllib.request.Request(url + ("&" if "?" in url else "?") + "s=200",
                                 headers={"User-Agent": "readme-generator"})
    return base64.b64encode(urllib.request.urlopen(req, timeout=30).read()).decode()


# --------------------------------------------------------------- frame

def frame_defs(uid):
    grads = (f'<linearGradient id="{uid}-bg" x1="0" y1="0" x2="1" y2="1">'
             f'<stop offset="0%" stop-color="{BG0}"/><stop offset="54%" stop-color="{BG1}"/>'
             f'<stop offset="100%" stop-color="{BG0}"/></linearGradient>')
    for i, (c, o) in enumerate(ORB):
        grads += (f'<radialGradient id="{uid}-o{i}" cx="50%" cy="50%" r="50%">'
                  f'<stop offset="0%" stop-color="{c}" stop-opacity="{o}"/>'
                  f'<stop offset="58%" stop-color="{c}" stop-opacity="0.18"/>'
                  f'<stop offset="100%" stop-color="{c}" stop-opacity="0"/></radialGradient>')
    return grads


def frame_orbs(uid, h):
    pos = ((138, .18, 206, .46), (654, .22, 241, .42), (499, .88, 310, .34), (826, .77, 172, .42))
    cls = ("a", "b", "c", "b")
    return "".join(
        f'<ellipse class="orb-{cls[i]}" cx="{x}" cy="{h * fy:.0f}" rx="{rx}" ry="{h * fr:.0f}" '
        f'fill="url(#{uid}-o{i})"/>'
        for i, (x, fy, rx, fr) in enumerate(pos)
    )


def shell(uid, h, label, title, body, defs=""):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{W}" height="{h}" viewBox="0 0 {W} {h}" role="img" aria-label="{label}">\n'
        f"<title>{title}</title>\n"
        f"<defs>{frame_defs(uid)}{defs}{CSS}</defs>\n"
        f'<rect width="{W}" height="{h}" rx="20" fill="url(#{uid}-bg)"/>\n'
        f"{frame_orbs(uid, h)}\n{body}\n"
        f'<rect x=".5" y=".5" width="{W - 1}" height="{h - 1}" rx="19.5" fill="none" '
        f'stroke="{ACC}" stroke-opacity=".62"/>\n</svg>\n'
    )


def card(x, y, w, h, rx=20, stroke_op=".5"):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{INK}" '
            f'stroke="{ACC}" stroke-opacity="{stroke_op}"/>')


# ---------------------------------------------------------------- hero

def build_hero(profile, langs, st):
    uid, H = "hero", 240
    av = avatar_b64(profile["avatarUrl"])
    name = esc(profile["name"] or LOGIN)
    bio = fit(profile["bio"], 64)

    chips, x = [], 166
    for lang in langs[:4]:
        label = lang["name"]
        w = 30 + len(label) * 6.1
        chips.append(
            f'<g class="chip"><rect x="{x:.1f}" y="172" width="{w:.1f}" height="24" rx="12" '
            f'fill="#ffffff" fill-opacity=".04" stroke="#ffffff" stroke-opacity=".13"/>'
            f'<circle cx="{x + 12:.1f}" cy="184" r="3.4" fill="{lang["color"]}"/>'
            f'<text x="{x + 20:.1f}" y="188" font-family="{MONO}" font-size="11" '
            f'fill="{TEXT}">{esc(label)}</text></g>'
        )
        x += w + 8

    defs = f'<clipPath id="{uid}-av"><circle cx="96" cy="94" r="45"/></clipPath>'
    body = card(26, 26, 808, 188, rx=20, stroke_op=".55")
    body += (f'<circle cx="96" cy="94" r="48" fill="#ffffff" fill-opacity=".06" stroke="{ACC}" '
             f'stroke-opacity=".85" stroke-width="2"/>'
             f'<image x="51" y="49" width="90" height="90" clip-path="url(#{uid}-av)" '
             f'preserveAspectRatio="xMidYMid slice" xlink:href="data:image/jpeg;base64,{av}"/>')
    body += (f'<text x="166" y="69" font-family="{MONO}" font-size="12" letter-spacing="2.6" '
             f'fill="{MUTED}">@{LOGIN.lower()}</text>'
             f'<text x="166" y="122" font-family="{SANS}" font-size="44" font-weight="850" '
             f'letter-spacing="-1.5" fill="{TEXT}">{name}</text>'
             f'<text x="166" y="152" font-family="{SANS}" font-size="14.5" '
             f'fill="{MUTED}">{bio}</text>')
    body += "".join(chips)

    # star orb, right side
    ox, oy, r2 = 735, 118, 53.3
    body += (f'<circle cx="{ox}" cy="{oy}" r="86" fill="none" stroke="{TEXT}" stroke-opacity=".1"/>'
             f'<circle cx="{ox}" cy="{oy}" r="{r2}" fill="none" stroke="{TEXT}" stroke-opacity=".16"/>'
             f'<circle cx="{ox}" cy="{oy}" r="31" fill="{ACC}" fill-opacity=".06" stroke="{TEXT}" '
             f'stroke-opacity=".3"/>'
             f'<g><animateTransform attributeName="transform" type="rotate" from="0 {ox} {oy}" '
             f'to="360 {ox} {oy}" dur="16s" repeatCount="indefinite"/>'
             f'<circle cx="{ox + r2}" cy="{oy}" r="3.4" fill="{ACC}"/></g>'
             f'<text x="{ox}" y="112" text-anchor="middle" font-family="{SANS}" font-size="32" '
             f'font-weight="900" letter-spacing="-1" fill="{ACC}">{profile["totalStars"]}</text>'
             f'<text x="{ox}" y="133" text-anchor="middle" font-family="{SANS}" font-size="9.5" '
             f'font-weight="800" letter-spacing="2.4" fill="{MUTED}">TOTAL STARS</text>')

    return shell(uid, H, f'{profile["name"] or LOGIN} GitHub profile card',
                 f'{profile["name"] or LOGIN} (@{LOGIN})', body, defs)


# ------------------------------------------------------------ projects

CARD_W, CARD_H = 394, 162
SLOTS = ((28, 88), (438, 88), (28, 266), (438, 266))


def since(iso):
    days = (date.today() - date.fromisoformat(iso[:10])).days
    if days < 1:
        return "today"
    if days < 7:
        return f"{days}d ago"
    if days < 31:
        return f"{days // 7}w ago"
    if days < 365:
        return f"{days // 30}mo ago"
    return f"{days // 365}y ago"


def build_projects(repos, langs):
    uid, H = "projects", 452
    body = (f'<text x="30" y="40" font-family="{MONO}" font-size="12" letter-spacing="2" '
            f'fill="{ACC}">PROJECTS.LIST</text>'
            f'<text x="180" y="40" font-family="{MONO}" font-size="11" fill="{MUTED}" '
            f'fill-opacity=".8">./projects.sh --all</text>'
            f'<text x="830" y="40" text-anchor="end" font-family="{MONO}" font-size="11" '
            f'fill="{MUTED}" fill-opacity=".7">{len(repos)} projects</text>'
            f'<line x1="28" y1="52" x2="832" y2="52" stroke="{ACC}" stroke-opacity=".5" '
            f'stroke-width="1.5"/>')

    for i, r in enumerate(repos[:4]):
        cx, cy = SLOTS[i]
        name = fit(r["name"], 24)
        desc = r["description"] or "No description provided."
        line1 = fit(desc, 54)
        rest = desc[len(line1.rstrip("…")):].strip() if line1.endswith("…") else ""
        line2 = fit(rest, 54) if rest else ""
        lang = (r["primaryLanguage"] or {}).get("name") or "—"
        chip_w = 16 + len(lang) * 5.6
        age = since(r["pushedAt"])
        dot = GREEN if age.endswith(("d ago", "w ago", "today")) else MUTED

        body += (
            f'<a href="{r["url"]}" target="_blank"><g opacity="0" transform="translate({cx},{cy})">'
            f'<animate attributeName="opacity" from="0" to="1" dur="0.5s" '
            f'begin="{0.25 + i * 0.15:.2f}s" fill="freeze"/>'
            f'<rect width="{CARD_W}" height="{CARD_H}" rx="13" fill="{INK}" stroke="{ACC}">'
            f'<animate attributeName="stroke-opacity" values="0.45;0.85;0.45" dur="4.5s" '
            f'begin="{0.25 + i * 0.85:.2f}s" repeatCount="indefinite"/></rect>'
            f'<path d="M0 13a13 13 0 0 1 13-13h368a13 13 0 0 1 13 13v17H0z" fill="{ACC}" '
            f'fill-opacity=".06"/>'
            f'<line x1="0" y1="30" x2="{CARD_W}" y2="30" stroke="{ACC}" stroke-opacity=".5"/>'
            f'<text x="16" y="19.5" font-family="{MONO}" font-size="10.5" fill="{MUTED}">'
            f'<tspan fill="{ACC}">&#8226;</tspan> {esc(fit(r["name"], 32))}</text>'
            f'<circle class="pulse" cx="378" cy="15" r="4" fill="{dot}" fill-opacity=".9"/>'
            f'<text x="18" y="58" font-family="{MONO}" font-size="16.5" font-weight="700" '
            f'fill="{TEXT}">{esc(name)}<tspan class="cursor" fill="{ACC}">_</tspan></text>'
            f'<text x="18" y="79" font-family="{MONO}" font-size="11.5" '
            f'fill="{MUTED}">{esc(line1)}</text>'
            + (f'<text x="18" y="95" font-family="{MONO}" font-size="11.5" '
               f'fill="{MUTED}">{esc(line2)}</text>' if line2 else "")
            + f'<rect x="18" y="114" width="{chip_w:.0f}" height="18" rx="9" fill="{ACC}" '
            f'fill-opacity=".14"/><text x="{18 + chip_w / 2:.0f}" y="126.5" text-anchor="middle" '
            f'font-family="{MONO}" font-size="9.5" fill="{ACC}">{esc(lang)}</text>'
            f'<text x="18" y="150" font-family="{MONO}" font-size="11" fill="{MUTED}">'
            f'<tspan fill="{ACC}">&#9733;</tspan> {r["stargazerCount"]}'
            f'<tspan fill="{MUTED}" fill-opacity=".7" dx="12">updated {age}</tspan></text>'
            f"</g></a>"
        )

    return shell(uid, H, f"Projects — {len(repos)} public repositories", "Projects", body)


# ----------------------------------------------------------------- city

C3 = 8.72                 # isometric cell size
DX3, DY3 = 9.69, 5.59     # one day = left+down, one week = right+down
HMAX3, PAD3 = 56.0, 2.6   # tallest tower (in cell units) / flat empty lot
CITY_SCALE, TX3, TY3 = 0.93, 252, 16
CITY_COLORS = (           # level -> (top, left, right) shaded faces
    ("#1e4a6d", "#17395a", "#122c46"),
    ("#2f6f9e", "#265c85", "#1d4768"),
    ("#4a95cc", "#3d7cad", "#2f5f86"),
    ("#6fb6e6", "#5a96bf", "#467594"),
    ("#9dd2f5", "#7fb0cf", "#648ba1"),
)


def build_city(weeks, st):
    uid, H = "city", 420
    cells = [c for w in weeks for c in w if c]
    maxc = max([c["c"] for c in cells] + [1])

    city = []
    for w, col in enumerate(weeks):
        for d, c in enumerate(col):
            if not c:
                continue
            city.append((w + d, w, d, c))

    parts = []
    for _, w, d, c in sorted(city):        # painter's order: back rows first
        x = (6 + w - d) * DX3
        y = (HMAX3 + 2) + (w + d) * DY3
        hb = PAD3 if not c["c"] else PAD3 + c["c"] / maxc * (HMAX3 - PAD3)
        up = hb - PAD3
        lvl = min(c["l"], 4)
        anim = (f'<g class="bld" style="animation-delay:{w * 0.018:.2f}s">'
                if c["c"] else "<g>")
        parts.append(
            f'<g transform="translate({x:.1f} {y:.1f})">{anim}'
            f'<rect width="{C3}" height="{C3}" class="t{lvl}" '
            f'transform="translate(0 {-up:.2f}) skewY(-30) skewX(40.89) scale(1 1.15)"/>'
            f'<rect width="{C3}" height="{hb:.2f}" class="l{lvl}" '
            f'transform="translate(0 {-up:.2f}) skewY(30) scale(1 1.15)"/>'
            f'<rect width="{C3}" height="{hb:.2f}" class="r{lvl}" '
            f'transform="translate({C3} {5.03 - up:.2f}) skewY(-30) scale(1 1.15)"/>'
            f"</g></g>"
        )

    faces = "".join(f".t{i}{{fill:{t}}}.l{i}{{fill:{l}}}.r{i}{{fill:{r}}}"
                    for i, (t, l, r) in enumerate(CITY_COLORS))
    defs = ("<style>" + faces +
            ".bld{animation:grow .9s cubic-bezier(.2,.75,.3,1) both}"
            "@keyframes grow{from{transform:translateY(64px);opacity:0}"
            "to{transform:translateY(0);opacity:1}}</style>")

    body = card(28, 26, 804, 368)
    body += (f'<text x="{GX}" y="66" font-family="{SANS}" font-size="11" font-weight="850" '
             f'letter-spacing="3.4" fill="{ACC}">CONTRIBUTION CITY</text>'
             f'<text x="{GX}" y="122" font-family="{SANS}" font-size="44" font-weight="900" '
             f'letter-spacing="-1.5" fill="{TEXT}">{st["total"]}</text>'
             f'<text x="{GX}" y="144" font-family="{SANS}" font-size="12.5" '
             f'fill="{MUTED}">contributions in the last year</text>')
    stats = (("active days", st["active"]), ("busiest day", st["bestdayn"]),
             ("best run", f'{st["best"]}d'), ("streak", f'{st["streak"]}d'))
    for i, (label, val) in enumerate(stats):
        y = 186 + i * 26
        body += (f'<text x="{GX}" y="{y}" font-family="{MONO}" font-size="10" '
                 f'letter-spacing="2.2" fill="{MUTED}">{label.upper()}</text>'
                 f'<text x="{GX + 120}" y="{y}" font-family="{MONO}" font-size="12" '
                 f'font-weight="700" fill="{ACC}">{val}</text>')
    body += (f'<text x="{GX}" y="372" font-family="{MONO}" font-size="11" '
             f'fill="{MUTED}">@{LOGIN.lower()}</text>'
             f'<g transform="translate({TX3} {TY3}) scale({CITY_SCALE})">'
             f'{"".join(parts)}</g>')

    return shell(uid, H, f'Contribution city — {st["total"]} contributions, '
                         f'{st["active"]} active days', "Contribution city", body, defs)


# --------------------------------------------------------------- resume

RESUME = {
    "title": "Software Engineer · Full-Stack & AI",
    "place": "VISAKHAPATNAM, INDIA",
    "email": "rajshalem72@gmail.com",
    # (label, number of tools listed in that resume category) — no invented ratings
    "loadout": (("PROGRAMMING", 6), ("FRONTEND", 2), ("BACKEND", 4), ("DATA / SQL", 7),
                ("AI / GENAI", 9), ("CLOUD / DEVOPS", 8), ("DELIVERY", 6)),
    "education": ("B.Tech, Information Technology",
                  "Anil Neerukonda Institute of Technology & Sciences",
                  "2022 – 2026 · CGPA 8.69 / 10"),
    "badges": (("PRESIDENT · ENTREPRENEURSHIP CLUB", "5+ workshops · teams of 5–10"),
               ("SMART INDIA HACKATHON 2025", "AI & Product Innovation")),
}


def build_resume(profile, st):
    uid, H = "resume", 430
    r = RESUME
    mx = max(n for _, n in r["loadout"])
    bx, bw = 452, 302

    body = card(28, 26, 804, 378)

    # identity
    body += (f'<text x="{GX}" y="66" font-family="{SANS}" font-size="11" font-weight="850" '
             f'letter-spacing="3.4" fill="{ACC}">PLAYER PROFILE</text>'
             f'<text x="{GX}" y="106" font-family="{SANS}" font-size="30" font-weight="850" '
             f'letter-spacing="-0.8" fill="{TEXT}">{esc(profile["name"] or LOGIN)}'
             f'<tspan class="cursor" fill="{ACC}">_</tspan></text>'
             f'<text x="{GX}" y="130" font-family="{SANS}" font-size="13" '
             f'fill="{MUTED}">{esc(r["title"])}</text>'
             f'<text x="{GX}" y="152" font-family="{MONO}" font-size="10" letter-spacing="2" '
             f'fill="{MUTED}">{r["place"]}</text>'
             f'<text x="{GX}" y="180" font-family="{MONO}" font-size="11" '
             f'fill="{ACC}">{r["email"]}</text>'
             f'<text x="{GX}" y="198" font-family="{MONO}" font-size="11" '
             f'fill="{ACC}">github.com/{LOGIN}</text>'
             f'<line x1="{GX}" y1="218" x2="{GX + 330}" y2="218" stroke="{TEXT}" '
             f'stroke-opacity=".12"/>'
             f'<text x="{GX}" y="244" font-family="{SANS}" font-size="10" font-weight="700" '
             f'letter-spacing="2.2" fill="{MUTED}">EDUCATION</text>'
             f'<text x="{GX}" y="268" font-family="{SANS}" font-size="13" font-weight="700" '
             f'fill="{TEXT}">{esc(r["education"][0])}</text>'
             f'<text x="{GX}" y="286" font-family="{SANS}" font-size="11" '
             f'fill="{MUTED}">{esc(fit(r["education"][1], 52))}</text>'
             f'<text x="{GX}" y="306" font-family="{MONO}" font-size="10.5" '
             f'fill="{ACC}">{r["education"][2]}</text>')

    # loadout bars
    body += (f'<text x="{bx}" y="66" font-family="{SANS}" font-size="10" font-weight="700" '
             f'letter-spacing="2.2" fill="{MUTED}">LOADOUT · TOOLS PER STACK</text>')
    for i, (label, n) in enumerate(r["loadout"]):
        y = 96 + i * 30
        w = bw * n / mx
        body += (f'<text x="{bx}" y="{y}" font-family="{MONO}" font-size="10.5" '
                 f'letter-spacing="1.6" fill="{TEXT}">{label}</text>'
                 f'<text x="{bx + bw + 42}" y="{y}" text-anchor="end" font-family="{MONO}" '
                 f'font-size="11" fill="{ACC}">{n:02d}</text>'
                 f'<rect x="{bx}" y="{y + 7}" width="{bw}" height="6" rx="3" fill="#ffffff" '
                 f'fill-opacity=".06"/>'
                 f'<rect class="bar" x="{bx}" y="{y + 7}" width="{w:.0f}" height="6" rx="3" '
                 f'fill="{ACC}" fill-opacity="{0.55 + 0.05 * n:.2f}" '
                 f'style="animation-delay:{0.15 + i * 0.08:.2f}s"/>')

    # badges
    for i, (head, sub) in enumerate(r["badges"]):
        x = GX + i * 396
        body += (f'<g class="badge" style="animation-delay:{0.9 + i * 0.12:.2f}s">'
                 f'<rect x="{x}" y="330" width="380" height="46" rx="12" fill="{ACC}" '
                 f'fill-opacity=".07" stroke="{ACC}" stroke-opacity=".35"/>'
                 f'<text x="{x + 16}" y="350" font-family="{MONO}" font-size="10" '
                 f'letter-spacing="1.4" fill="{TEXT}">{esc(head)}</text>'
                 f'<text x="{x + 16}" y="366" font-family="{MONO}" font-size="10" '
                 f'fill="{MUTED}">{esc(sub)}</text></g>')

    return shell(uid, H, f'{profile["name"] or LOGIN} — player profile',
                 "Player profile", body)


# --------------------------------------------------------------- galaxy

GAL_CX, GAL_CY = 566, 198
GAL_VIOLET, GAL_PALE, GAL_LILAC = "#818cf8", "#e0e7ff", "#a5b4fc"


def _lcg(n):
    """Stable pseudo-random in [0,1) so the sky looks the same on every run."""
    return ((n * 1103515245 + 12345) % 2147483648) / 2147483648


def build_galaxy(repos, langs, profile):
    uid, H = "galaxy", 380
    n = max(1, len(repos))
    # five labels, spread along the spiral; owned-star repos get first pick
    leaders = sorted(({i for i in (9, 17, 25) if i < n}
                      | {i for i in range(n) if repos[i]["stargazerCount"]}))[:5]
    color_of = {l["name"]: l["color"] for l in langs}

    sky, stars = [], []

    # background dust
    for i in range(300):
        a = _lcg(i * 3 + 1) * 6.28318
        r = 20 + _lcg(i * 3 + 2) ** 0.62 * 175
        x, y = GAL_CX + r * 0.96 * math.cos(a), GAL_CY + r * 0.74 * math.sin(a)
        if x < 250 or x > 828 or y < 34 or y > 386:
            continue
        sky.append(f'<circle class="star" cx="{x:.1f}" cy="{y:.1f}" '
                   f'r="{0.6 + _lcg(i * 3 + 3) * 1.3:.2f}" fill="{GAL_PALE}" fill-opacity=".7" '
                   f'style="animation-delay:{_lcg(i * 7 + 5) * 5:.2f}s"/>')

    # orbits
    for r in (72, 118, 164):
        stars.append(f'<circle cx="{GAL_CX}" cy="{GAL_CY}" r="{r}" fill="none" stroke="{GAL_LILAC}" '
                     f'stroke-opacity=".07" stroke-dasharray="2 7"/>')

    # one star per repository, sunflower spiral so nothing overlaps
    pts = []
    for i in range(n):
        ang = i * 2.399963
        rad = 46 + 3.9 * i
        pts.append((GAL_CX + rad * math.cos(ang),
                    GAL_CY + rad * 0.78 * math.sin(ang),
                    rad))

    for i, r in enumerate(repos):
        x, y, rad = pts[i]
        col = color_of.get((r["primaryLanguage"] or {}).get("name"), GAL_VIOLET)
        core = 8.2 if r["stargazerCount"] else 6.2
        halo = ""
        if r["stargazerCount"]:
            halo = (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{core * 2.6:.1f}" fill="{col}" '
                    f'fill-opacity=".18"/>')
        stars.append(f'{halo}<circle cx="{x:.1f}" cy="{y:.1f}" r="{core:.1f}" fill="{col}"/>'
                     f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{core * 2.6:.1f}" fill="none" '
                     f'stroke="{col}" stroke-opacity=".28"/>')

    # labels for the five biggest, nudged apart
    used = []
    for i in leaders:
        x, y, rad = pts[i]
        right = x < GAL_CX + 30
        while any(abs(y - u) < 14 for u in used):
            y += 14
        used.append(y)
        name = fit(repos[i]["name"], 16)
        tx = x + 16 if right else x - 16
        anchor = "start" if right else "end"
        stars.append(
            f'<line x1="{x + 9:.1f}" y1="{y:.1f}" x2="{tx - (4 if right else -4):.1f}" y2="{y:.1f}" '
            f'stroke="{GAL_LILAC}" stroke-opacity=".35"/>'
            f'<text x="{tx:.1f}" y="{y - 1:.1f}" text-anchor="{anchor}" font-family="{MONO}" '
            f'font-size="10" fill="{GAL_PALE}">{esc(name)}</text>'
            f'<text x="{tx:.1f}" y="{y + 10:.1f}" text-anchor="{anchor}" font-family="{MONO}" '
            f'font-size="9" fill="{GAL_LILAC}">&#9733; {repos[i]["stargazerCount"]}</text>')

    body = card(28, 26, 804, 328, rx=20, stroke_op=".5")
    body += (f'<text x="{GX}" y="52" font-family="{SANS}" font-size="11" font-weight="700" '
             f'letter-spacing="2.2" fill="#7884f7">REPO GALAXY</text>'
             f'<text x="{GX}" y="86" font-family="{SANS}" font-size="26" font-weight="800" '
             f'fill="{GAL_PALE}">@{LOGIN}</text>'
             f'<text x="{GX}" y="112" font-family="{SANS}" font-size="13" font-weight="600" '
             f'fill="{GAL_LILAC}">{profile["totalStars"]} stars · {n} repositories</text>'
             f'<text x="{GX}" y="134" font-family="{SANS}" font-size="11.5" '
             f'fill="{GAL_LILAC}" fill-opacity=".85">Each star is a repository, sized by its '
             f'stars.</text>'
             f'<text x="{GX}" y="196" font-family="{SANS}" font-size="10" font-weight="700" '
             f'letter-spacing="2" fill="{GAL_LILAC}">LANGUAGES</text>')
    for i, lang in enumerate(langs[:4]):
        y = 220 + i * 22
        body += (f'<circle cx="{GX + 5}" cy="{y - 4}" r="3.4" fill="{lang["color"]}"/>'
                 f'<text x="{GX + 18}" y="{y}" font-family="{SANS}" font-size="12" '
                 f'font-weight="700" fill="{GAL_PALE}">{esc(lang["name"])}</text>'
                 f'<text x="{GX + 168}" y="{y}" text-anchor="end" font-family="{MONO}" '
                 f'font-size="11" fill="{GAL_LILAC}">{lang["percentage"]}%</text>')
    body += "".join(sky) + "".join(stars)

    return shell(uid, H, f'Repo galaxy — {n} repositories, {profile["totalStars"]} stars',
                 "Repo galaxy", body)


# ------------------------------------------------------------- heatmaps

def grid(weeks, gy=GY):
    out = []
    for w, col in enumerate(weeks):
        for d, c in enumerate(col):
            if not c:
                continue
            x, y = GX + w * PITCH, gy + d * PITCH
            if c["l"]:
                fill, op = LEVEL[c["l"]]
                out.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2.5" '
                           f'fill="{fill}" fill-opacity="{op}"/>')
            else:
                out.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2.5" '
                           f'fill="{TEXT}" fill-opacity=".05"/>')
    return "".join(out)


def heatmap_head(body, title, subtitle, live="LIVE"):
    return (body + f'<text x="{GX}" y="60" font-family="{SANS}" font-size="11" font-weight="850" '
                   f'letter-spacing="3.4" fill="{ACC}">{title}</text>'
                   f'<text x="{GX}" y="84" font-family="{SANS}" font-size="20" font-weight="800" '
                   f'fill="{TEXT}">{subtitle}</text>'
                   f'<circle class="pulse" cx="798" cy="68" r="3" fill="{GREEN}"/>'
                   f'<text x="814" y="72" text-anchor="end" font-family="{SANS}" font-size="10" '
                   f'font-weight="850" letter-spacing="1.8" fill="{DIM}">{live}</text>')


def build_snake(weeks, st, start, last):
    uid, H = "snake", 264
    seq = []
    for w, col in enumerate(weeks):
        order = range(ROWS) if w % 2 == 0 else range(ROWS - 1, -1, -1)
        for d in order:
            if col[d] and col[d]["c"] > 0:
                seq.append((w, d))
    pts = [(GX + w * PITCH + CELL / 2, GY + d * PITCH + CELL / 2) for w, d in seq]
    path = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    step = {p: i for i, p in enumerate(seq)}
    total = max(1, len(pts) - 1)

    cells = []
    for w, col in enumerate(weeks):
        for d, c in enumerate(col):
            if not c:
                continue
            x, y = GX + w * PITCH, GY + d * PITCH
            if c["c"] > 0:
                fill, op = LEVEL[c["l"]]
                delay = step[(w, d)] / total * 7.4
                cells.append(f'<rect class="cell" x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
                             f'rx="2.5" fill="{fill}" fill-opacity="{op}" '
                             f'style="animation-delay:{delay:.2f}s"/>')
            else:
                cells.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2.5" '
                             f'fill="{TEXT}" fill-opacity=".05"/>')

    defs = (f'<linearGradient id="{uid}-trail" x1="0" y1="0" x2="1" y2="0">'
            f'<stop offset="0%" stop-color="{GREEN}"/><stop offset="55%" stop-color="{DIM}"/>'
            f'<stop offset="100%" stop-color="{ACC}"/></linearGradient>'
            f'<filter id="{uid}-glow" x="-60%" y="-60%" width="220%" height="220%">'
            f'<feGaussianBlur stdDeviation="4" result="b"/>'
            f'<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>')

    body = heatmap_head(card(28, 26, 804, 212), "SNAKE TRAIL",
                        f'{st["total"]} contributions, one continuous run')
    body += "".join(cells)
    body += (f'<path class="trail" d="{path}" fill="none" stroke="url(#{uid}-trail)" '
             f'stroke-width="4.4" stroke-linecap="round" stroke-linejoin="round" pathLength="1" '
             f'filter="url(#{uid}-glow)"/>'
             f'<circle r="6" fill="#ffffff" filter="url(#{uid}-glow)">'
             f'<animateMotion dur="9s" repeatCount="indefinite" path="{path}" '
             f'keyPoints="0;1;1" keyTimes="0;0.82;1" calcMode="linear"/></circle>')
    return shell(uid, H, f'Snake trail — {st["total"]} contributions, best run {st["best"]} days',
                 "Contribution snake trail", body, defs)


def build_shooter(weeks, st, start, last):
    uid, H = "shooter", 264
    lit = [(w, d, c) for w, col in enumerate(weeks) for d, c in enumerate(col)
           if c and c["l"] > 0]
    booms = "".join(
        f'<rect class="boom" x="{GX + w * PITCH - 3}" y="{GY + d * PITCH - 3}" '
        f'width="{CELL + 6}" height="{CELL + 6}" rx="4" fill="{DIM}" '
        f'style="animation-delay:{(i * 1.7) % 5.5:.2f}s"/>'
        for i, (w, d, c) in enumerate(lit[:: max(1, len(lit) // 6)][:6])
    )
    stars = "".join(
        f'<circle class="star" cx="{GX + (i * 97) % 730 + 4}" cy="{94 + (i * 53) % 116}" '
        f'r="{1 + (i % 3) * 0.6:.1f}" fill="{TEXT}" style="animation-delay:{i * 0.4:.1f}s"/>'
        for i in range(18)
    )
    lasers = "".join(
        f'<rect class="laser" x="{6 + i * 5}" y="196" width="2" height="16" rx="1" fill="{CYAN}" '
        f'style="animation-delay:{i * 0.33:.2f}s"/>' for i in range(3)
    )
    defs = (f'<filter id="{uid}-glow" x="-80%" y="-80%" width="260%" height="260%">'
            f'<feGaussianBlur stdDeviation="3" result="b"/>'
            f'<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>')

    body = heatmap_head(card(28, 26, 804, 212), "SPACE SHOOTER",
                        f'{st["total"]} contributions · score {st["total"]:04d}')
    body += stars + grid(weeks, GY) + booms
    body += (f'<g transform="translate({GX},0)"><g class="ship"><g transform="translate(0,206)">'
             f'<rect x="-16" y="-22" width="32" height="60" fill="{CYAN}" fill-opacity=".05"/>'
             f"{lasers}"
             f'<path d="M0 -12 L12 12 L0 6 L-12 12 Z" fill="{ACC}" filter="url(#{uid}-glow)"/>'
             f'<path d="M0 -6 L6 9 L-6 9 Z" fill="#e6fbff"/>'
             f'<circle class="pulse" cx="0" cy="7" r="2.6" fill="#e6fbff"/>'
             f"</g></g></g>")
    return shell(uid, H, f'Contribution space shooter — {st["total"]} contributions',
                 "Contribution space shooter", body, defs)


def build_social():
    uid, H = "social", 126
    mark = ("M8 0C3.58 0 0 3.58 0 8c0 3.54 2.29 6.53 5.47 7.59.4.07.55-.17.55-.38 "
            "0-.19-.01-.82-.01-1.49-2.01.37-2.53-.49-2.69-.94-.09-.23-.48-.94-.82-1.13"
            "-.28-.15-.68-.52-.01-.53.63-.01 1.08.58 1.23.82.72 1.21 1.87.87 2.33.66"
            ".07-.52.28-.87.51-1.07-1.78-.2-3.64-.89-3.64-3.95 0-.87.31-1.59.82-2.15"
            "-.08-.2-.36-1.02.08-2.12 0 0 .67-.21 2.2.82.64-.18 1.32-.27 2-.27s1.36.09 2 .27"
            "c1.53-1.04 2.2-.82 2.2-.82.44 1.1.16 1.92.08 2.12.51.56.82 1.27.82 2.15 "
            "0 3.07-1.87 3.75-3.65 3.95.29.25.54.73.54 1.48 0 1.07-.01 1.93-.01 2.2 "
            "0 .21.15.46.55.38A8.01 8.01 0 0 0 16 8c0-4.42-3.58-8-8-8z")
    body = card(26, 22, 808, 82, rx=22, stroke_op=".48")
    body += (f'<a href="https://github.com/{LOGIN}" target="_blank">'
             f'<rect x="341" y="40" width="178" height="46" rx="23" fill="#ffffff" '
             f'fill-opacity=".05"/>'
             f'<rect x="342" y="41" width="176" height="44" rx="22" fill="none" stroke="{ACC}" '
             f'stroke-opacity=".55"><animate attributeName="stroke-opacity" values=".3;.8;.3" '
             f'dur="4s" repeatCount="indefinite"/></rect>'
             f'<g transform="translate(366,57) scale(1.35)" fill="{TEXT}"><path d="{mark}"/></g>'
             f'<text x="396" y="59" font-family="{SANS}" font-size="10" font-weight="850" '
             f'letter-spacing="1.2" fill="{MUTED}">GitHub</text>'
             f'<text x="396" y="76" font-family="{SANS}" font-size="13.5" font-weight="800" '
             f'fill="{TEXT}">@{LOGIN}</text></a>')
    return shell(uid, H, f"GitHub @{LOGIN}", f"GitHub @{LOGIN}", body)


# --------------------------------------------------------------- write

def build_readme(repos, st):
    links = " · ".join(f'[{esc(r["name"])}]({r["url"]})' for r in repos[:4])
    return (
        '<div align="center">\n\n'
        f'<img src="assets/hero.svg" width="860" alt="Shalem Raj (@{LOGIN}) profile card">\n\n'
        f'<img src="assets/city.svg" width="860" alt="Contribution city — {st["total"]} '
        f'contributions, {st["active"]} active days">\n\n'
        f'<img src="assets/space-shooter.svg" width="860" alt="Contribution space shooter — '
        f'{st["total"]} contributions, {st["active"]} active days">\n\n'
        f'<img src="assets/galaxy.svg" width="860" alt="Repo galaxy — every repository as a star, '
        f'sized by its stars">\n\n'
        f'<img src="assets/projects.svg" width="860" alt="Projects">\n\n'
        f"<sub>{links}</sub>\n\n"
        f'<img src="assets/snake.svg" width="860" alt="Snake trail — {st["total"]} contributions, '
        f'best run {st["best"]} days">\n\n'
        f'<img src="assets/resume.svg" width="860" alt="Player profile — skills, education, '
        f'leadership">\n\n'
        f'<img src="assets/social.svg" width="860" alt="GitHub @{LOGIN}">\n\n'
        "</div>\n" + DETAILS
    )


DETAILS = """
<details>
<summary><b>▸ EXPERIENCE</b> — 2 roles, expand</summary>

**Full Stack Engineer** · Aegion Dynamic Solutions · Jul 2026 – present

- **AnthyOS** — CI/CD translation platform: converts TeamCity and Jenkins pipelines into equivalent GitHub Actions workflows; built the companion desktop app `anthyos-desktop`.
- Pipeline work cut execution from `16m22s` to `10m32s` and cost per run from `$1.26` to `$0.22`.
- **Ruchi** — AI voice kitchen companion: voice interaction workflows, stateful multi-step agents on LangGraph, and a TTS cache that serves audio in ~0 ms against ~1200 ms for fresh synthesis.
- Requirement discussions, technical documentation, MVP builds and product demos with stakeholders.

**Python Full Stack Developer Intern** · Coastal Seven Technologies · Apr 2026

- **Career Portal** — React, Flask, MySQL and REST APIs; resume upload, parsing, structured profile extraction, AI resume scoring and candidate-job matching.
- **Hiring Factory** — Next.js, FastAPI, Supabase, PostgreSQL with JWT auth and RBAC across recruiter, admin, HR, interviewer and candidate roles.

</details>

<details>
<summary><b>▸ PROJECTS</b> — expand</summary>

- **AnySite** — AI tools discovery platform (React, Flask, PostgreSQL, n8n). RAG recommendation workflow: a user's problem becomes a tool sequence.
- **IoT Water Quality Monitor** — ESP8266 + TDS sensors, ThingSpeak dashboards, IFTTT alerts.
- **Library Management System** — MySQL schema and operations for a second-year academic project.

</details>

<details>
<summary><b>▸ LEADERSHIP</b> — expand</summary>

- **President, Entrepreneurship Club** (2024–2025) — ran 5+ workshops on innovation, startup execution and design thinking; led teams of 5–10.
- **Smart India Hackathon 2025** — AI and Product Innovation category.

</details>
"""


def main():
    user = gh(f"users/{LOGIN}")
    repos = json.loads(subprocess.run(
        ["gh", "repo", "list", LOGIN, "--limit", "100", "--visibility", "public",
         "--json", "name,description,stargazerCount,primaryLanguage,isFork,pushedAt,url"],
        capture_output=True, text=True, check=True).stdout)
    live = [r for r in repos if not r["isFork"] and r["name"] != LOGIN]

    langs = {}
    for r in live[:40]:
        for name, size in gh(f"repos/{LOGIN}/{r['name']}/languages").items():
            langs[name] = langs.get(name, 0) + size
    total_lang = sum(langs.values()) or 1
    colors = {"TypeScript": "#3178c6", "JavaScript": "#f1e05a", "Python": "#3572A5",
              "HTML": "#e34c26", "CSS": "#663399", "EJS": "#a91e50", "SCSS": "#c6538c",
              "Java": "#b07219", "Shell": "#89e051", "Dockerfile": "#384d54", "C": "#555555",
              "C++": "#f34b7d", "Jupyter Notebook": "#DA5B0B", "Vue": "#41b883"}
    top_langs = [{"name": k, "color": colors.get(k, ACC), "percentage": round(v / total_lang * 100)}
                 for k, v in sorted(langs.items(), key=lambda kv: -kv[1])]

    weeks, start, last = fetch_contributions(LOGIN)
    st = stats(weeks)
    profile = {"name": user["name"], "bio": user["bio"], "avatarUrl": user["avatar_url"],
               "followers": user["followers"], "totalRepos": len(live),
               "totalStars": sum(r["stargazerCount"] for r in live)}

    picks = sorted(live, key=lambda r: (r["stargazerCount"], r["pushedAt"]), reverse=True)[:4]

    (OUT / "hero.svg").write_text(build_hero(profile, top_langs, st), encoding="utf-8")
    (OUT / "city.svg").write_text(build_city(weeks, st), encoding="utf-8")
    (OUT / "space-shooter.svg").write_text(build_shooter(weeks, st, start, last), encoding="utf-8")
    (OUT / "galaxy.svg").write_text(build_galaxy(live, top_langs, profile), encoding="utf-8")
    (OUT / "projects.svg").write_text(build_projects(picks, top_langs), encoding="utf-8")
    (OUT / "snake.svg").write_text(build_snake(weeks, st, start, last), encoding="utf-8")
    (OUT / "resume.svg").write_text(build_resume(profile, st), encoding="utf-8")
    (OUT / "social.svg").write_text(build_social(), encoding="utf-8")
    (ROOT / "README.md").write_text(build_readme(picks, st), encoding="utf-8")

    print(f'wrote 6 cards · {st["total"]} contributions · {st["active"]} active days · '
          f'{len(live)} repos · {profile["totalStars"]} stars')
    for r in picks:
        print(f'  {r["name"]:<34}{(r["primaryLanguage"] or {}).get("name", "-"):<12}'
              f'★{r["stargazerCount"]}  {since(r["pushedAt"])}')


if __name__ == "__main__":
    main()