#!/usr/bin/env python3
"""Regenerate the arcade-trail SVG cards from public GitHub data.

Hallmark · genre: atmospheric · world: arcade HUD · theme: GitHub dark
· enrichment: Tier-B hand-built SVG · surfaces: 8 cards, one series
· pre-emit critique: Philosophy 5 · Hierarchy 4 · Execution 5 · Specificity 4 · Restraint 5 · Variety 4

Usage:  python assets/generate.py
Needs:  `gh` logged in (repo + language data), stdlib only.
Writes: hero.svg, city.svg, projects.svg, space-shooter.svg, galaxy.svg,
        snake.svg, resume.svg, social.svg, README.md

One design system for all eight cards: five type steps, one baseline, one
inset panel, one heading spec, one motion language. Tokens live below.
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
SITE = "https://rajshalem5.github.io"
OUT = Path(__file__).resolve().parent
ROOT = OUT.parent

# ------------------------------------------------------------- tokens
W = 860                                   # every card
GUTTER = 46                               # left text edge, all cards
CARD_X, CARD_Y, RADIUS = 28, 26, 20       # inset panel
BASE = 66                                 # first baseline, all cards
RULE_Y = 80                               # heading rule

PAPER, PAPER2 = "#0d1117", "#161b22"
INK, INK2 = "#e6edf3", "#8b949e"          # 12.9:1 and 5.5:1 on PAPER
ACCENT = "#58a6ff"
RULE = "#30363d"                          # neutral; accent no longer draws edges
GREEN, VIOLET, VIOLET_PALE, VIOLET_LILAC = "#39d353", "#818cf8", "#e0e7ff", "#a5b4fc"
PANEL = "rgba(8,8,12,0.5)"

T_DISPLAY, T_TITLE, T_LEAD, T_BODY, T_DATA = 44, 28, 18, 13, 11.5

MONO = "ui-monospace,'SF Mono',SFMono-Regular,Menlo,Consolas,monospace"
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"

COLS, ROWS, CELL, GAP = 53, 7, 11, 3
PITCH = CELL + GAP
GX, GY = GUTTER, 106

# ------------------------------------------------------------- motion
# Every animation in the set, in one place, so no card ships dead CSS and
# the reduced-motion block can restore each one's final state.
MOTION = (
    (("orb-a", "orb-b", "orb-c"), """<style>
.orb-a{animation:fa 9s ease-in-out infinite}
.orb-b{animation:fb 11s ease-in-out infinite 1.1s}
.orb-c{animation:fc 13s ease-in-out infinite .6s}
@keyframes fa{0%,100%{transform:translate(0,0);opacity:.58}50%{transform:translate(28px,-20px);opacity:.86}}
@keyframes fb{0%,100%{transform:translate(0,0);opacity:.42}50%{transform:translate(-24px,18px);opacity:.72}}
@keyframes fc{0%,100%{transform:translate(0,0) scale(1);opacity:.34}50%{transform:translate(18px,-12px) scale(1.18);opacity:.62}}
</style>"""),
    (("chip",), """<style>
.chip{animation:spring .62s cubic-bezier(.34,1.56,.64,1) both;transform-box:fill-box;
transform-origin:center}
.chip:nth-of-type(2){animation-delay:.07s}
.chip:nth-of-type(3){animation-delay:.14s}
.chip:nth-of-type(4){animation-delay:.21s}
@keyframes spring{0%{opacity:0;transform:translateY(7px) scale(.82)}
55%{opacity:1;transform:translateY(0) scale(1.06)}
78%{transform:scale(.985)}100%{opacity:1;transform:translateY(0) scale(1)}}
</style>"""),
    (("bld",), """<style>
.bld{animation:grow .9s cubic-bezier(.2,.75,.3,1) both}
@keyframes grow{from{transform:translateY(64px);opacity:0}to{transform:translateY(0);opacity:1}}
</style>"""),
    (("cell",), """<style>
.cell{opacity:.3;animation:pop 9s linear infinite}
@keyframes pop{0%{opacity:.2}6%{opacity:1}70%{opacity:.95}86%,100%{opacity:.2}}
</style>"""),
    (("trail",), """<style>
.trail{stroke-dasharray:1;stroke-dashoffset:1;animation:draw 9s linear infinite}
.slash{stroke-dasharray:.055 .945;stroke-dashoffset:.06;animation:slash 9s linear infinite;opacity:0}
@keyframes slash{0%{stroke-dashoffset:.06;opacity:0}
4%{opacity:1}78%{stroke-dashoffset:-.9;opacity:1}
82%,100%{stroke-dashoffset:-.9;opacity:0}}
@keyframes draw{0%{stroke-dashoffset:1;opacity:.9}82%{stroke-dashoffset:0;opacity:.9}97%,100%{stroke-dashoffset:0;opacity:0}}
</style>"""),
    (("ship", "laser"), """<style>
.ship{animation:sweep 9s ease-in-out infinite alternate}
.laser{animation:fire 1.3s linear infinite}
@keyframes sweep{0%{transform:translateX(0)}100%{transform:translateX(720px)}}
@keyframes fire{0%{transform:translateY(0);opacity:0}10%{opacity:1}80%{opacity:.9}100%{transform:translateY(-96px);opacity:0}}
</style>"""),
    (("boom",), """<style>
.boom{opacity:0;animation:burst 5.5s ease-out infinite;transform-box:fill-box;
transform-origin:center}
@keyframes burst{0%,70%{opacity:0;transform:scale(.25) rotate(0deg)}
76%{opacity:1;transform:scale(1) rotate(11deg)}
84%{opacity:.7;transform:scale(1.35) rotate(16deg)}
92%,100%{opacity:0;transform:scale(1.6) rotate(20deg)}}
</style>"""),
    (("star",), """<style>
.star{animation:twinkle 6s ease-in-out infinite}
@keyframes twinkle{0%,100%{opacity:.12}50%{opacity:.5}}
</style>"""),
    (("badge",), """<style>
.badge{animation:rise .5s cubic-bezier(.16,1,.3,1) both}
@keyframes rise{from{opacity:0;transform:translateY(6px)}to{opacity:1;transform:translateY(0)}}
</style>"""),
    (("bar",), """<style>
.bar{animation:surge 1.6s cubic-bezier(.22,1.4,.36,1) both;transform-box:fill-box;
transform-origin:left}
@keyframes surge{0%{transform:scaleX(0)}
34%{transform:scaleX(.58)}
40%{transform:scaleX(.55)}
70%{transform:scaleX(.92)}
86%{transform:scaleX(1.035)}
100%{transform:scaleX(1)}}
</style>"""),
    (("cursor",), """<style>
.cursor{animation:blink 1.1s step-end infinite}
@keyframes blink{0%,49%{opacity:1}50%,100%{opacity:0}}
</style>"""),
    (("pulse",), """<style>
.pulse{animation:pulse 2.4s ease-in-out infinite}
@keyframes pulse{0%,100%{opacity:1}50%{opacity:.35}}
</style>"""),
)

ORB = ((ACCENT, ".72"), (GREEN, ".5"), (VIOLET, ".72"), ("#22d3ee", ".5"))


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
    cells = [(m.group(1), int(m.group(2)))
             for m in re.finditer(r'data-date="([\d-]+)"[^>]*data-level="(\d)"', page)]
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
    out = (f'<linearGradient id="{uid}-bg" x1="0" y1="0" x2="1" y2="1">'
           f'<stop offset="0%" stop-color="{PAPER}"/><stop offset="54%" stop-color="{PAPER2}"/>'
           f'<stop offset="100%" stop-color="{PAPER}"/></linearGradient>')
    for i, (c, o) in enumerate(ORB):
        out += (f'<radialGradient id="{uid}-o{i}" cx="50%" cy="50%" r="50%">'
                f'<stop offset="0%" stop-color="{c}" stop-opacity="{o}"/>'
                f'<stop offset="58%" stop-color="{c}" stop-opacity="0.18"/>'
                f'<stop offset="100%" stop-color="{c}" stop-opacity="0"/></radialGradient>')
    return out


def frame_orbs(uid, h):
    pos = ((138, .18, 206, .46), (654, .22, 241, .42), (499, .88, 310, .34), (826, .77, 172, .42))
    cls = ("a", "b", "c", "b")
    return "".join(
        f'<ellipse class="orb-{cls[i]}" cx="{x}" cy="{h * fy:.0f}" rx="{rx}" ry="{h * fr:.0f}" '
        f'fill="url(#{uid}-o{i})"/>' for i, (x, fy, rx, fr) in enumerate(pos))


def motion_css(body):
    used = set()
    for m in re.findall(r'class="([^"]+)"', body):
        used.update(m.split())
    used.update(("orb-a", "orb-b", "orb-c"))     # the chrome always carries the orbs
    return "".join(block for names, block in MOTION if used & set(names))


def shell(uid, h, label, title, body, defs="", head=""):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
        f'width="{W}" height="{h}" viewBox="0 0 {W} {h}" role="img" aria-label="{esc(label)}">\n'
        f"<title>{esc(title)}</title>\n"
        f"<defs>{frame_defs(uid)}{defs}{motion_css(body + head)}</defs>\n"
        f'<rect width="{W}" height="{h}" rx="{RADIUS}" fill="url(#{uid}-bg)"/>\n'
        f"{frame_orbs(uid, h)}\n{body}{head}\n"
        f'<rect x=".5" y=".5" width="{W - 1}" height="{h - 1}" rx="19.5" fill="none" '
        f'stroke="{RULE}"/>\n</svg>\n'
    )


def card(x, y, w, h, rx=RADIUS, op="1"):
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{rx}" fill="{PANEL}" '
            f'fill-opacity="{op}" stroke="{RULE}"/>')


def head(title, meta=""):
    """One heading spec for every card: title on the baseline, neutral rule under it."""
    out = (f'<text x="{GUTTER}" y="{BASE}" font-family="{SANS}" font-size="{T_TITLE}" '
           f'font-weight="850" letter-spacing="-0.6" fill="{INK}">{esc(title)}</text>'
           f'<line x1="{GUTTER}" y1="{RULE_Y}" x2="{W - GUTTER}" y2="{RULE_Y}" '
           f'stroke="{RULE}" stroke-width="1"/>')
    if meta:
        out += (f'<text x="{W - GUTTER}" y="{BASE}" text-anchor="end" font-family="{MONO}" '
                f'font-size="{T_DATA}" fill="{INK2}">{esc(meta)}</text>')
    return out


def label(x, y, text, fill=INK2, size=T_DATA, spacing="1.6", weight=""):
    size = max(size, T_DATA)          # floor: nothing renders below 11.5px
    w = f' font-weight="{weight}"' if weight else ""
    return (f'<text x="{x}" y="{y}" font-family="{MONO}" font-size="{size}" '
            f'letter-spacing="{spacing}" fill="{fill}"{w}>{esc(text)}</text>')


# --------------------------------------------------------------- hero

def build_hero(profile, langs, st):
    uid, H = "hero", 240
    av = avatar_b64(profile["avatarUrl"])
    name = esc(profile["name"] or LOGIN)
    bio = fit(profile["bio"], 60)

    chips, x = [], GUTTER + 120
    for lang in langs[:4]:
        lw = 30 + len(lang["name"]) * 6.1
        chips.append(
            f'<g class="chip"><rect x="{x:.1f}" y="180" width="{lw:.1f}" height="22" rx="11" '
            f'fill="#ffffff" fill-opacity=".05"/>'
            f'<circle cx="{x + 11:.1f}" cy="191" r="3.2" fill="{lang["color"]}"/>'
            f'<text x="{x + 19:.1f}" y="191" font-family="{MONO}" font-size="{T_DATA}" '
            f'fill="{INK}">{esc(lang["name"])}</text></g>')
        x += lw + 7

    defs = f'<clipPath id="{uid}-av"><circle cx="96" cy="94" r="44"/></clipPath>'
    body = card(CARD_X, CARD_Y, W - 2 * CARD_X, 188)
    body += (f'<circle cx="96" cy="94" r="48" fill="#ffffff" fill-opacity=".06" '
             f'stroke="{RULE}" stroke-width="2"/>'
             f'<image x="52" y="50" width="88" height="88" clip-path="url(#{uid}-av)" '
             f'preserveAspectRatio="xMidYMid slice" xlink:href="data:image/jpeg;base64,{av}"/>')
    body += (f'<text x="166" y="66" font-family="{MONO}" font-size="{T_DATA}" letter-spacing="2.4" '
             f'fill="{INK2}">@{LOGIN.lower()}</text>'
             f'<text x="166" y="114" font-family="{SANS}" font-size="{T_DISPLAY}" font-weight="850" '
             f'letter-spacing="-1.6" fill="{INK}">{name}</text>'
             f'<text x="166" y="142" font-family="{SANS}" font-size="{T_LEAD}" font-weight="700" '
             f'fill="{ACCENT}">Software Engineer · full-stack &amp; AI</text>'
             f'<text x="166" y="164" font-family="{SANS}" font-size="{T_BODY}" '
             f'fill="{INK2}">{bio}</text>')
    body += "".join(chips)

    ox, oy, r2 = 735, 112, 53.3
    body += (f'<circle cx="{ox}" cy="{oy}" r="86" fill="none" stroke="{INK}" stroke-opacity=".1"/>'
             f'<circle cx="{ox}" cy="{oy}" r="{r2}" fill="none" stroke="{INK}" stroke-opacity=".16"/>'
             f'<circle cx="{ox}" cy="{oy}" r="31" fill="none" stroke="{INK}" stroke-opacity=".24"/>'
             f'<g><animateTransform attributeName="transform" type="rotate" from="0 {ox} {oy}" '
             f'to="360 {ox} {oy}" dur="16s" repeatCount="indefinite"/>'
             f'<circle cx="{ox + r2}" cy="{oy}" r="3.2" fill="{ACCENT}"/></g>'
             f'<text x="{ox}" y="108" text-anchor="middle" font-family="{SANS}" '
             f'font-size="{T_TITLE}" font-weight="850" fill="{INK}">{profile["totalStars"]}</text>'
             f'<text x="{ox}" y="128" text-anchor="middle" font-family="{MONO}" '
             f'font-size="{T_DATA}" letter-spacing="1.8" fill="{INK2}">STARS</text>')
    return shell(uid, H, f'{profile["name"] or LOGIN} — software engineer, full-stack and AI',
                 f'{profile["name"] or LOGIN} (@{LOGIN})', body, defs)


# ---------------------------------------------------------------- city

C3, DX3, DY3 = 8.72, 9.69, 5.59
HMAX3, PAD3 = 56.0, 2.6
CITY_SCALE, TX3, TY3 = 0.93, 252, 16
CITY_COLORS = (("#1e4a6d", "#17395a", "#122c46"), ("#2f6f9e", "#265c85", "#1d4768"),
               ("#4a95cc", "#3d7cad", "#2f5f86"), ("#6fb6e6", "#5a96bf", "#467594"),
               ("#9dd2f5", "#7fb0cf", "#648ba1"))


def build_city(weeks, st):
    uid, H = "city", 420
    cells = [c for w in weeks for c in w if c]
    maxc = max([c["c"] for c in cells] + [1])
    city = sorted((w + d, w, d, c) for w, col in enumerate(weeks) for d, c in enumerate(col) if c)

    parts = []
    for _, w, d, c in city:
        x = (6 + w - d) * DX3
        y = (HMAX3 + 2) + (w + d) * DY3
        hb = PAD3 if not c["c"] else PAD3 + c["c"] / maxc * (HMAX3 - PAD3)
        up, lvl = hb - PAD3, min(c["l"], 4)
        anim = (f'<g class="bld" style="animation-delay:{w * 0.018:.2f}s">' if c["c"] else "<g>")
        parts.append(
            f'<g transform="translate({x:.1f} {y:.1f})">{anim}'
            f'<rect width="{C3}" height="{C3}" class="t{lvl}" '
            f'transform="translate(0 {-up:.2f}) skewY(-30) skewX(40.89) scale(1 1.15)"/>'
            f'<rect width="{C3}" height="{hb:.2f}" class="l{lvl}" '
            f'transform="translate(0 {-up:.2f}) skewY(30) scale(1 1.15)"/>'
            f'<rect width="{C3}" height="{hb:.2f}" class="r{lvl}" '
            f'transform="translate({C3} {5.03 - up:.2f}) skewY(-30) scale(1 1.15)"/></g></g>')

    defs = ("<style>" + "".join(f".t{i}{{fill:{t}}}.l{i}{{fill:{l}}}.r{i}{{fill:{r}}}"
                                for i, (t, l, r) in enumerate(CITY_COLORS)) + "</style>")
    body = card(CARD_X, CARD_Y, W - 2 * CARD_X, 368)
    body += head("Contribution city", f"{st['active']} active days")
    body += (f'<text x="{GUTTER}" y="132" font-family="{SANS}" font-size="{T_DISPLAY}" '
             f'font-weight="850" letter-spacing="-1.6" fill="{INK}">{st["total"]}</text>'
             f'<text x="{GUTTER}" y="158" font-family="{SANS}" font-size="{T_BODY}" '
             f'fill="{INK2}">contributions this year</text>')
    rows = (("busiest day", f'{st["bestdayn"]} on {st["bestday"]}'),
            ("best run", f'{st["best"]} days'), ("current streak", f'{st["streak"]} days'))
    for i, (k, v) in enumerate(rows):
        y = 196 + i * 24
        body += label(GUTTER, y, k.upper())
        body += label(GUTTER + 130, y, v, INK, weight="700")
    body += label(GUTTER, 292, f"ONE BLOCK = ONE DAY · TALLEST {st['bestdayn']}", INK2, 10.5)
    body += (f'<g transform="translate({TX3} {TY3}) scale({CITY_SCALE})">'
             f'{"".join(parts)}</g>')
    return shell(uid, H, f'Contribution city — {st["total"]} contributions, '
                         f'{st["active"]} active days, busiest day {st["bestdayn"]}',
                 "Contributions as a city skyline", body, defs)


# ------------------------------------------------------------ projects

CARD_W, CARD_H = 394, 162
SLOTS = ((28, 104), (438, 104), (28, 282), (438, 282))


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


def build_projects(repos):
    uid, H = "projects", 452
    body = card(CARD_X, CARD_Y, W - 2 * CARD_X, 400)
    body += head("Projects", f"{len(repos)} public repos")

    for i, r in enumerate(repos[:4]):
        cx, cy = SLOTS[i]
        name = fit(r["name"], 24)
        desc = r["description"] or ""
        line1 = fit(desc, 54)
        rest = desc[len(line1.rstrip("…")):].strip() if line1.endswith("…") else ""
        line2 = fit(rest, 54) if rest else ""
        lang = (r["primaryLanguage"] or {}).get("name") or "—"
        chip_w = 16 + len(lang) * 5.6
        age = since(r["pushedAt"])

        body += (
            f'<a href="{r["url"]}" target="_blank"><g opacity="0" transform="translate({cx},{cy})">'
            f'<animate attributeName="opacity" from="0" to="1" dur="0.45s" '
            f'begin="{0.15 + i * 0.1:.2f}s" fill="freeze"/>'
            f'<rect width="{CARD_W}" height="{CARD_H}" rx="14" fill="{PANEL}" stroke="{RULE}"/>'
            f'<path d="M0 13a13 13 0 0 1 13-13h368a13 13 0 0 1 13 13v17H0z" fill="#ffffff" '
            f'fill-opacity=".03"/>'
            f'<line x1="0" y1="30" x2="{CARD_W}" y2="30" stroke="{RULE}"/>'
            f'{label(16, 19.5, fit(r["name"], 32), INK2, 10.5, "1.2")}'
            f'<circle cx="378" cy="15" r="3.5" fill="{GREEN if age.endswith(("d ago", "w ago", "today")) else INK2}" '
            f'fill-opacity=".9"/>'
            f'<text x="18" y="60" font-family="{MONO}" font-size="{T_LEAD}" font-weight="700" '
            f'fill="{INK}">{esc(name)}<tspan class="cursor" fill="{ACCENT}">_</tspan></text>'
            + (f'<text x="18" y="82" font-family="{SANS}" font-size="{T_BODY}" '
               f'fill="{INK2}">{esc(line1)}</text>' if line1 else "")
            + (f'<text x="18" y="98" font-family="{SANS}" font-size="{T_BODY}" '
               f'fill="{INK2}">{esc(line2)}</text>' if line2 else "")
            + f'<rect x="18" y="116" width="{chip_w:.0f}" height="18" rx="9" fill="#ffffff" '
            f'fill-opacity=".06"/><text x="{18 + chip_w / 2:.0f}" y="128.5" text-anchor="middle" '
            f'font-family="{MONO}" font-size="{T_DATA}" fill="{INK2}">{esc(lang)}</text>'
            f'{label(18, 152, f"pushed {age}", INK2, 11)}'
            f"</g></a>")
    return shell(uid, H, f'Projects — {", ".join(r["name"] for r in repos[:4])}', "Projects", body)


# --------------------------------------------------------------- galaxy

GAL_CX, GAL_CY = 572, 234


def _lcg(n):
    return ((n * 1103515245 + 12345) % 2147483648) / 2147483648


def build_galaxy(repos, langs, profile):
    uid, H = "galaxy", 380
    n = max(1, len(repos))
    max_stars = max([r["stargazerCount"] for r in repos] + [1])
    leaders = sorted(({i for i in (9, 17, 25) if i < n}
                      | {i for i in range(n) if repos[i]["stargazerCount"]}))[:5]
    color_of = {l["name"]: l["color"] for l in langs}

    sky, stars = [], []
    for i in range(90):                       # 90 dust points, not 300
        a = _lcg(i * 3 + 1) * 6.28318
        r = 30 + _lcg(i * 3 + 2) ** 0.62 * 150
        x, y = GAL_CX + r * 0.98 * math.cos(a), GAL_CY + r * 0.66 * math.sin(a)
        if x < 250 or x > 828 or y < 100 or y > 348:
            continue
        sky.append(f'<circle class="star" cx="{x:.1f}" cy="{y:.1f}" '
                   f'r="{0.6 + _lcg(i * 3 + 3) * 1.1:.2f}" fill="{VIOLET_PALE}" fill-opacity=".6" '
                   f'style="animation-delay:{_lcg(i * 7 + 5) * 6:.2f}s"/>')

    for r in (62, 104, 146):
        stars.append(f'<circle cx="{GAL_CX}" cy="{GAL_CY}" r="{r}" fill="none" '
                     f'stroke="{VIOLET_LILAC}" stroke-opacity=".08" stroke-dasharray="2 8"/>')

    pts = []
    for i in range(n):
        ang, rad = i * 2.399963, 42 + 3.7 * i
        pts.append((GAL_CX + rad * math.cos(ang), GAL_CY + rad * 0.72 * math.sin(ang)))

    for i, r in enumerate(repos):
        x, y = pts[i]
        col = color_of.get((r["primaryLanguage"] or {}).get("name"), VIOLET)
        core = 4.6 + 4.4 * (r["stargazerCount"] / max_stars)   # continuous, matches the promise
        halo = (f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{core * 2.6:.1f}" fill="{col}" '
                f'fill-opacity=".16"/>') if r["stargazerCount"] else ""
        stars.append(f'{halo}<circle cx="{x:.1f}" cy="{y:.1f}" r="{core:.1f}" fill="{col}"/>'
                     f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{core * 2.6:.1f}" fill="none" '
                     f'stroke="{col}" stroke-opacity=".26"/>')

    used = []
    for i in leaders:
        x, y = pts[i]
        right = x < GAL_CX + 30
        while any(abs(y - u) < 28 for u in used):
            y += 28
        used.append(y)
        tx, anchor = (x + 15, "start") if right else (x - 15, "end")
        star_txt = "★ " + str(repos[i]["stargazerCount"])
        stars.append(
            f'<line x1="{x + 8:.1f}" y1="{y:.1f}" x2="{tx - (3 if right else -3):.1f}" y2="{y:.1f}" '
            f'stroke="{VIOLET_LILAC}" stroke-opacity=".3"/>'
            f'{label(tx, y - 2, fit(repos[i]["name"], 16), VIOLET_PALE, 10.5, "0")}'
            f'{label(tx, y + 13, star_txt, VIOLET_LILAC, 10, "0")}')

    body = card(CARD_X, CARD_Y, W - 2 * CARD_X, 328)
    body += head("Repo galaxy", f"{profile['totalStars']} stars")
    body += (f'<text x="{GUTTER}" y="114" font-family="{SANS}" font-size="{T_BODY}" '
             f'fill="{INK2}">{n} public repositories, one star each — radius is its star '
             f'count.</text>')
    body += label(GUTTER, 156, "LANGUAGES", VIOLET_LILAC, 10.5, "2")
    for i, lang in enumerate(langs[:4]):
        y = 182 + i * 22
        pct = str(lang["percentage"]) + "%"
        body += (f'<circle cx="{GUTTER + 5}" cy="{y - 4}" r="3.2" fill="{lang["color"]}"/>'
                 f'<text x="{GUTTER + 18}" y="{y}" font-family="{SANS}" font-size="{T_BODY}" '
                 f'font-weight="700" fill="{VIOLET_PALE}">{esc(lang["name"])}</text>'
                 f'{label(GUTTER + 158, y, pct, VIOLET_LILAC, 11, "0")}')
    body += "".join(sky) + "".join(stars)
    return shell(uid, H, f'Repo galaxy — {n} repositories, {profile["totalStars"]} stars in total',
                 "Repositories as a galaxy", body)


# ----------------------------------------------------------- heatmaps

def grid(weeks, gy=GY):
    out = []
    for w, col in enumerate(weeks):
        for d, c in enumerate(col):
            if not c:
                continue
            x, y = GX + w * PITCH, gy + d * PITCH
            op = (0, .07, .34, .55, 1)[c["l"]]
            fill, o = (INK, .07) if c["l"] == 0 else (ACCENT, op)
            out.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2.5" '
                       f'fill="{fill}" fill-opacity="{o}"/>')
    return "".join(out)


def build_snake(weeks, st, start, last):
    uid, H = "snake", 264
    seq = []
    for w, col in enumerate(weeks):
        for d in (range(ROWS) if w % 2 == 0 else range(ROWS - 1, -1, -1)):
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
                cells.append(f'<rect class="cell" x="{x}" y="{y}" width="{CELL}" height="{CELL}" '
                             f'rx="2.5" fill="{ACCENT}" fill-opacity="{(.34, .55, 1)[min(c["l"], 3) - 1]}" '
                             f'style="animation-delay:{step[(w, d)] / total * 7.4:.2f}s"/>')
            else:
                cells.append(f'<rect x="{x}" y="{y}" width="{CELL}" height="{CELL}" rx="2.5" '
                             f'fill="{INK}" fill-opacity=".05"/>')

    defs = (f'<linearGradient id="{uid}-trail" x1="0" y1="0" x2="1" y2="0">'
            f'<stop offset="0%" stop-color="{GREEN}"/><stop offset="100%" stop-color="{ACCENT}"/>'
            f'</linearGradient>'
            f'<filter id="{uid}-glow" x="-60%" y="-60%" width="220%" height="220%">'
            f'<feGaussianBlur stdDeviation="4" result="b"/>'
            f'<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>')

    body = card(CARD_X, CARD_Y, W - 2 * CARD_X, 212)
    body += head("Snake trail", f"{st['active']} active days")
    body += "".join(cells)
    body += (f'<path class="trail" d="{path}" fill="none" stroke="url(#{uid}-trail)" '
                 f'stroke-width="4" stroke-linecap="round" stroke-linejoin="round" pathLength="1" '
                 f'filter="url(#{uid}-glow)"/>'
                 f'<path class="slash" d="{path}" fill="none" stroke="#ffffff" stroke-width="5" '
                 f'stroke-linecap="round" stroke-linejoin="round" pathLength="1" '
                 f'filter="url(#{uid}-glow)"/>'
                 f'<circle r="5" fill="#ffffff" filter="url(#{uid}-glow)">'
             f'<animateMotion dur="9s" repeatCount="indefinite" path="{path}" '
             f'keyPoints="0;1;1" keyTimes="0;0.82;1" calcMode="linear"/></circle>')
    return shell(uid, H, f'Snake trail through {st["total"]} contributions over {st["active"]} '
                         f'active days, longest run {st["best"]} days',
                 "Contribution snake trail", body, defs)


def build_shooter(weeks, st):
    uid, H = "shooter", 264
    lit = [(w, d, c) for w, col in enumerate(weeks) for d, c in enumerate(col)
           if c and c["l"] > 0]
    rays = "".join(f'<line x1="0" y1="-5" x2="0" y2="-13" transform="rotate({a})"/>'
                   for a in range(0, 360, 45))
    rays = "".join(f'<line x1="0" y1="-5" x2="0" y2="-13" transform="rotate({a})"/>'
                   for a in range(0, 360, 45))
    booms = "".join(
        f'<g transform="translate({GX + w * PITCH + CELL / 2:.1f} {GY + d * PITCH + CELL / 2:.1f})">'
        f'<g class="boom" stroke="{ACCENT}" stroke-width="1.8" stroke-linecap="round" '
        f'style="animation-delay:{(i * 1.9) % 5.5:.2f}s">'
        f'{rays}<circle r="2.6" fill="{ACCENT}" stroke="none"/></g></g>'
        for i, (w, d, _) in enumerate(lit[:: max(1, len(lit) // 7)][:6]))

    stars = "".join(
        f'<circle class="star" cx="{GX + (i * 97) % 730 + 4}" cy="{94 + (i * 53) % 116}" '
        f'r="{1 + (i % 3) * 0.5:.1f}" fill="{INK}" style="animation-delay:{i * 0.7:.1f}s"/>'
        for i in range(18))
    lasers = "".join(
        f'<rect class="laser" x="{6 + i * 5}" y="196" width="2" height="16" rx="1" fill="{ACCENT}" '
        f'style="animation-delay:{i * 0.33:.2f}s"/>' for i in range(3))
    defs = (f'<filter id="{uid}-glow" x="-80%" y="-80%" width="260%" height="260%">'
            f'<feGaussianBlur stdDeviation="3" result="b"/>'
            f'<feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge></filter>')

    body = card(CARD_X, CARD_Y, W - 2 * CARD_X, 212)
    body += head("Space shooter", f"score {st['total']:04d}")
    body += stars + grid(weeks) + booms
    body += (f'<g transform="translate({GX},0)"><g class="ship"><g transform="translate(0,206)">'
             f'<rect x="-16" y="-22" width="32" height="60" fill="{ACCENT}" fill-opacity=".05"/>'
             f'{lasers}'
             f'<path d="M0 -12 L12 12 L0 6 L-12 12 Z" fill="{ACCENT}" filter="url(#{uid}-glow)"/>'
             f'<path d="M0 -6 L6 9 L-6 9 Z" fill="#e6fbff"/>'
             f'<circle class="pulse" cx="0" cy="7" r="2.6" fill="#e6fbff"/></g></g></g>')
    return shell(uid, H, f'Contribution space shooter — {st["total"]} contributions, score '
                         f'{st["total"]:04d}', "Contribution space shooter", body, defs)


# --------------------------------------------------------------- resume

RESUME = {
    "place": "VISAKHAPATNAM, INDIA",
    "email": "rajshalem72@gmail.com",
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
    bx, bw = 452, 292

    body = card(CARD_X, CARD_Y, W - 2 * CARD_X, 378)
    body += head("Profile", "full-stack & AI")
    body += (f'<text x="{GUTTER}" y="112" font-family="{MONO}" font-size="{T_DATA}" '
             f'letter-spacing="2.2" fill="{INK2}">{r["place"]}</text>'
             f'{label(GUTTER, 138, r["email"], ACCENT, T_BODY, "0")}'
             f'{label(GUTTER, 158, f"github.com/{LOGIN}", ACCENT, T_BODY, "0")}'
             f'<line x1="{GUTTER}" y1="180" x2="{GUTTER + 330}" y2="180" stroke="{RULE}"/>'
             f'{label(GUTTER, 204, "EDUCATION", INK2, 10.5, "2")}'
             f'<text x="{GUTTER}" y="230" font-family="{SANS}" font-size="{T_BODY}" '
             f'font-weight="700" fill="{INK}">{esc(r["education"][0])}</text>'
             f'<text x="{GUTTER}" y="250" font-family="{SANS}" font-size="{T_DATA}" '
             f'fill="{INK2}">{esc(fit(r["education"][1], 52))}</text>'
             f'{label(GUTTER, 272, r["education"][2], INK, 11)}')

    body += label(bx, 112, "TOOLS LISTED PER STACK", INK2, 10.5, "2")
    for i, (name, n) in enumerate(r["loadout"]):
        y = 140 + i * 28
        body += (label(bx, y, name, INK, 10.5)
                 + label(bx + bw + 40, y, f"{n:02d}", ACCENT, 11, "0")
                 + f'<rect x="{bx}" y="{y + 6}" width="{bw}" height="6" rx="3" fill="#ffffff" '
                   f'fill-opacity=".06"/>'
                   f'<rect class="bar" x="{bx}" y="{y + 6}" width="{bw * n / mx:.0f}" height="6" '
                   f'rx="3" fill="{ACCENT}" style="animation-delay:{0.1 + i * 0.07:.2f}s"/>')
    body += label(bx, 348, "COUNTS, NOT A RATING", INK2, 10, "1.4")

    for i, (name, sub) in enumerate(r["badges"]):
            x = GUTTER + i * 396
            body += (f'<g class="badge" style="animation-delay:{0.2 + i * 0.1:.2f}s">'
                     f'<rect x="{x}" y="300" width="380" height="46" rx="12" fill="#ffffff" '
                     f'fill-opacity=".04" stroke="{RULE}"/>'
                     f'{label(x + 16, 320, name, INK, 10, "1.4")}'
                     f'{label(x + 16, 336, sub, INK2, 10, "0.6")}</g>')
    return shell(uid, H, f'{profile["name"] or LOGIN} — B.Tech IT, Anil Neerukonda Institute of '
                         f'Technology & Sciences, CGPA 8.69/10, {r["email"]}, president of the '
                         f'entrepreneurship club, Smart India Hackathon 2025',
                 "Profile: skills, education, leadership", body)


# --------------------------------------------------------------- social

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
    body = card(CARD_X, 22, W - 2 * CARD_X, 82, rx=22)
    body += (f'<a href="https://github.com/{LOGIN}" target="_blank">'
             f'<rect x="222" y="40" width="200" height="46" rx="23" fill="#ffffff" fill-opacity=".05" '
             f'stroke="{RULE}"/>'
             f'<g transform="translate(242,56) scale(1.2)" fill="{INK}"><path d="{mark}"/></g>'
             f'{label(270, 59, "GITHUB", INK2, 10, "1.2")}'
             f'<text x="270" y="77" font-family="{SANS}" font-size="{T_BODY}" font-weight="700" '
             f'fill="{INK}">@{LOGIN}</text></a>'
             f'<a href="{SITE}" target="_blank">'
             f'<rect x="438" y="40" width="200" height="46" rx="23" fill="{ACCENT}" fill-opacity=".1" '
             f'stroke="{ACCENT}" stroke-opacity=".45"/>'
             f'<text x="456" y="72" font-family="{MONO}" font-size="17" fill="{ACCENT}">&#8599;</text>'
             f'{label(478, 59, "INTERACTIVE", ACCENT, 10, "1.2")}'
             f'<text x="478" y="77" font-family="{MONO}" font-size="{T_DATA}" font-weight="700" '
             f'fill="{INK}">rajshalem5.github.io</text></a>')
    return shell(uid, H, f'GitHub and the interactive site — {SITE}', f'GitHub @{LOGIN}', body)


# --------------------------------------------------------------- write

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


def build_readme(repos, st):
    links = " · ".join(f'[{esc(r["name"])}]({r["url"]})' for r in repos[:4])
    return (
        '<div align="center">\n\n'
        f'<img src="assets/hero.svg" width="860" alt="Shalem Raj (@{LOGIN}) — software engineer, '
        f'full-stack and AI, Visakhapatnam">\n\n'
        f'<sub><a href="{SITE}"><b>\u2192 the interactive version</b></a> \u2014 same data, '
        f'with a console you can actually use</sub>\n\n'
        f'<img src="assets/city.svg" width="860" alt="Contributions this year drawn as a city '
        f'skyline: {st["total"]} contributions over {st["active"]} active days, busiest day '
        f'{st["bestdayn"]}, best run {st["best"]} days">\n\n'
        f'<img src="assets/space-shooter.svg" width="860" alt="The same contribution grid as a '
        f'space shooter, score {st["total"]:04d}">\n\n'
        f'<img src="assets/galaxy.svg" width="860" alt="Every public repository as a star, '
        f'sized by its star count">\n\n'
        f'<img src="assets/projects.svg" width="860" alt="Projects: '
        f'{", ".join(r["name"] for r in repos[:4])}">\n\n'
        f"<sub>{links}</sub>\n\n"
        f'<img src="assets/snake.svg" width="860" alt="A trail through {st["total"]} '
        f'contributions across {st["active"]} active days">\n\n'
        f'<img src="assets/resume.svg" width="860" alt="Profile: B.Tech in Information '
        f'Technology at Anil Neerukonda Institute of Technology and Sciences, Visakhapatnam, '
        f'CGPA 8.69 of 10, 2022 to 2026; email rajshalem72@gmail.com; president of the '
        f'Entrepreneurship Club; Smart India Hackathon 2025">\n\n'
        f'<img src="assets/social.svg" width="860" alt="GitHub @{LOGIN}">\n\n'
        "</div>\n" + DETAILS
    )


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
    top_langs = [{"name": k, "color": colors.get(k, ACCENT), "percentage": round(v / total_lang * 100)}
                 for k, v in sorted(langs.items(), key=lambda kv: -kv[1])]

    weeks, start, last = fetch_contributions(LOGIN)
    st = stats(weeks)
    profile = {"name": user["name"], "bio": user["bio"], "avatarUrl": user["avatar_url"],
               "followers": user["followers"], "totalRepos": len(live),
               "totalStars": sum(r["stargazerCount"] for r in live)}

    # a described, recently-touched repo beats a bare one: no "No description provided." cards
    picks = sorted(live, key=lambda r: (bool(r["description"]), r["description"] or "",
                                        r["pushedAt"]), reverse=True)[:4]

    (OUT / "hero.svg").write_text(build_hero(profile, top_langs, st), encoding="utf-8")
    (OUT / "city.svg").write_text(build_city(weeks, st), encoding="utf-8")
    (OUT / "space-shooter.svg").write_text(build_shooter(weeks, st), encoding="utf-8")
    (OUT / "galaxy.svg").write_text(build_galaxy(live, top_langs, profile), encoding="utf-8")
    (OUT / "projects.svg").write_text(build_projects(picks), encoding="utf-8")
    (OUT / "snake.svg").write_text(build_snake(weeks, st, start, last), encoding="utf-8")
    (OUT / "resume.svg").write_text(build_resume(profile, st), encoding="utf-8")
    (OUT / "social.svg").write_text(build_social(), encoding="utf-8")
    (ROOT / "README.md").write_text(build_readme(picks, st), encoding="utf-8")

    print(f'8 cards · {st["total"]} contributions · {st["active"]} active days · '
          f'{len(live)} repos · {profile["totalStars"]} stars')
    for r in picks:
        print(f'  {fit(r["name"], 32):<34}{(r["primaryLanguage"] or {}).get("name", "-"):<12}'
              f'★{r["stargazerCount"]}  {(r["description"] or "")[:44]}')


if __name__ == "__main__":
    main()