#!/usr/bin/env python3
"""Regenerate the animated SVG cards from public GitHub data.

Usage:  python assets/generate.py
Needs:  `gh` logged in (used for repo + language data), stdlib only.
Writes: hero.svg, space-shooter.svg, snake.svg next to this file.
"""

import base64
import html
import json
import re
import subprocess
import urllib.request
from datetime import date, timedelta
from pathlib import Path

LOGIN = "Rajshalem5"
OUT = Path(__file__).resolve().parent

W, COLS, ROWS, CELL, GAP = 860, 53, 7, 11, 2.6
PITCH = CELL + GAP
GRID_W = COLS * PITCH - GAP
GRID_H = ROWS * PITCH - GAP
GX = (W - GRID_W) / 2

BG0, BG1 = "#080b12", "#0e1622"
BORDER = "#22d3ee"
CYAN, GREEN, LIME, YELLOW, MAGENTA = "#22d3ee", "#3fb950", "#86efac", "#f2cc60", "#ff5cc8"
TEXT, MUTED = "#e6edf3", "#8b949e"
EMPTY = "#101a26"
LEVEL = ["#0f3d24", "#166534", "#22c55e", "#86efac"]
MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,'Liberation Mono',monospace"
SANS = "-apple-system,BlinkMacSystemFont,'Segoe UI',Helvetica,Arial,sans-serif"


def gh(path):
    out = subprocess.run(["gh", "api", path], capture_output=True, text=True)
    if out.returncode != 0:
        raise SystemExit(f"gh api {path} failed: {out.stderr.strip()}")
    return json.loads(out.stdout)


def fetch_contributions(login):
    url = f"https://github.com/users/{login}/contributions"
    req = urllib.request.Request(url, headers={"User-Agent": "readme-generator"})
    page = urllib.request.urlopen(req, timeout=30).read().decode("utf-8", "replace")
    cells = [
        (m.group(1), int(m.group(2)))
        for m in re.finditer(r'data-date="([\d-]+)"[^>]*data-level="(\d)"', page)
    ]
    tips = [
        html.unescape(t).strip()
        for t in re.findall(r"<tool-tip[^>]*>([^<]*)</tool-tip>", page)
    ]
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
    return {
        "total": total,
        "active": active,
        "best": best,
        "streak": streak,
        "bestday": bestday["d"],
        "bestdayn": bestday["c"],
    }


def grid_cells(weeks):
    for w, col in enumerate(weeks):
        for d, c in enumerate(col):
            if c:
                yield w, d, c


def avatar_b64(url):
    req = urllib.request.Request(url + ("&" if "?" in url else "?") + "s=200",
                                 headers={"User-Agent": "readme-generator"})
    raw = urllib.request.urlopen(req, timeout=30).read()
    return base64.b64encode(raw).decode()


def esc(s):
    return html.escape(s or "", quote=True)


# ---------------------------------------------------------------- hero

def build_hero(profile, langs, st):
    av = avatar_b64(profile["avatarUrl"])
    name = esc(profile["name"] or LOGIN)
    bio = (profile["bio"] or "").strip()
    bio = " ".join(bio.split())
    line1, line2 = wrap(bio, 66)[:2]
    if len(wrap(bio, 66)) > 2:
        line2 = line2.rstrip(". ,") + "…"

    chips, x = [], 146
    for lang in langs[:4]:
        label = lang["name"]
        w = 35 + len(label) * 5.9
        chips.append(
            f'<g class="chip"><rect x="{x:.1f}" y="192" width="{w:.1f}" height="24" rx="12" '
            f'fill="#ffffff" fill-opacity=".04" stroke="#ffffff" stroke-opacity=".14"/>'
            f'<circle cx="{x+12:.1f}" cy="204" r="3.4" fill="{lang["color"]}"/>'
            f'<text x="{x+21:.1f}" y="208" font-family="{SANS}" font-size="11" fill="{TEXT}">{esc(label)}</text></g>'
        )
        x += w + 8

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="250" viewBox="0 0 {W} 250" role="img" aria-label="{name} — GitHub profile card">
<title>{name} (@{LOGIN})</title>
<defs>
  <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
    <stop offset="0%" stop-color="{BG0}"/><stop offset="58%" stop-color="{BG1}"/><stop offset="100%" stop-color="{BG0}"/>
  </linearGradient>
  <radialGradient id="glowA" cx="50%" cy="50%" r="50%">
    <stop offset="0%" stop-color="{CYAN}" stop-opacity=".5"/><stop offset="100%" stop-color="{CYAN}" stop-opacity="0"/>
  </radialGradient>
  <radialGradient id="glowB" cx="50%" cy="50%" r="50%">
    <stop offset="0%" stop-color="{MAGENTA}" stop-opacity=".34"/><stop offset="100%" stop-color="{MAGENTA}" stop-opacity="0"/>
  </radialGradient>
  <pattern id="scan" width="4" height="4" patternUnits="userSpaceOnUse">
    <rect width="4" height="1" fill="#ffffff" opacity=".022"/>
  </pattern>
  <clipPath id="av"><circle cx="78" cy="124" r="44"/></clipPath>
  <style>
    .orb-a {{ animation: drift 12s ease-in-out infinite; }}
    .orb-b {{ animation: drift 15s ease-in-out infinite reverse; }}
    .chip {{ animation: rise .7s ease-out both; }}
    .chip:nth-of-type(1) {{ animation-delay: .15s; }}
    .chip:nth-of-type(2) {{ animation-delay: .25s; }}
    .chip:nth-of-type(3) {{ animation-delay: .35s; }}
    .chip:nth-of-type(4) {{ animation-delay: .45s; }}
    @keyframes drift {{ 0%,100% {{ transform: translate(0,0); }} 50% {{ transform: translate(26px,-14px); }} }}
    @keyframes rise {{ from {{ opacity: 0; transform: translateY(6px); }} to {{ opacity: 1; transform: translateY(0); }} }}
  </style>
</defs>
<rect width="{W}" height="250" rx="18" fill="url(#bg)"/>
<ellipse class="orb-a" cx="150" cy="30" rx="250" ry="120" fill="url(#glowA)"/>
<ellipse class="orb-b" cx="700" cy="240" rx="280" ry="130" fill="url(#glowB)"/>
<rect width="{W}" height="250" rx="18" fill="url(#scan)"/>
<circle cx="78" cy="124" r="47" fill="#ffffff" fill-opacity=".05" stroke="{CYAN}" stroke-opacity=".75" stroke-width="1.5"/>
<circle cx="78" cy="124" r="52" fill="none" stroke="{CYAN}" stroke-opacity=".18"/>
<image x="34" y="80" width="88" height="88" clip-path="url(#av)" preserveAspectRatio="xMidYMid slice"
       href="data:image/jpeg;base64,{av}"/>
<text x="146" y="69" font-family="{MONO}" font-size="11" letter-spacing="3" fill="{MUTED}">@{LOGIN.upper()}</text>
<text x="146" y="120" font-family="{SANS}" font-size="40" font-weight="800" letter-spacing="-1.2" fill="{TEXT}">{name}</text>
<text x="146" y="150" font-family="{SANS}" font-size="13.5" fill="{MUTED}">{esc(line1)}</text>
<text x="146" y="170" font-family="{SANS}" font-size="13.5" fill="{MUTED}">{esc(line2)}</text>
{"".join(chips)}
<line x1="646" y1="60" x2="646" y2="200" stroke="#ffffff" stroke-opacity=".1"/>
<text x="832" y="72" text-anchor="end" font-family="{MONO}" font-size="9" letter-spacing="3" fill="{MAGENTA}">ARCADE TRAIL</text>
<text x="832" y="122" text-anchor="end" font-family="{MONO}" font-size="40" font-weight="700" fill="{CYAN}">{st["total"]}</text>
<text x="832" y="146" text-anchor="end" font-family="{MONO}" font-size="8.5" letter-spacing="2.4" fill="{MUTED}">CONTRIBUTIONS</text>
<text x="832" y="172" text-anchor="end" font-family="{MONO}" font-size="10.5" fill="{MUTED}">{profile["totalRepos"]} REPOS · {profile["followers"]} FOLLOWERS</text>
<text x="832" y="190" text-anchor="end" font-family="{MONO}" font-size="10.5" fill="{MUTED}">★ {profile["totalStars"]} STARS</text>
<text x="832" y="232" text-anchor="end" font-family="{MONO}" font-size="8" letter-spacing="1.6" fill="{MUTED}" fill-opacity=".55">PLAYER 1 · READY</text>
<rect x=".75" y=".75" width="{W-1.5}" height="248.5" rx="17.5" fill="none" stroke="{BORDER}" stroke-opacity=".45"/>
</svg>
'''


def wrap(text, width):
    words, lines, cur = text.split(), [], ""
    for word in words:
        cand = (cur + " " + word).strip()
        if len(cand) <= width:
            cur = cand
        else:
            lines.append(cur)
            cur = word
    if cur:
        lines.append(cur)
    return lines or [""]


# ---------------------------------------------------- space shooter

def build_shooter(weeks, st, start, last):
    cells, hits = [], []
    lit = [(w, d, c) for w, d, c in grid_cells(weeks) if c["l"] > 0]
    for w, d, c in lit:
        x, y = GX + w * PITCH, 92 + d * PITCH
        cells.append(
            f'<rect x="{x:.1f}" y="{y:.1f}" width="{CELL}" height="{CELL}" rx="2" '
            f'fill="{LEVEL[c["l"]-1]}" fill-opacity="{0.55 + 0.12 * c["l"]:.2f}"/>'
        )
    for w, col in enumerate(weeks):
        for d, c in enumerate(col):
            if not c:
                continue
            if c["l"] == 0:
                x, y = GX + w * PITCH, 92 + d * PITCH
                cells.append(
                    f'<rect x="{x:.1f}" y="{y:.1f}" width="{CELL}" height="{CELL}" rx="2" '
                    f'fill="{EMPTY}" stroke="#1b2735" stroke-width=".6"/>'
                )
    # muzzle flashes on a few lit cells
    for i, (w, d, c) in enumerate(lit[:: max(1, len(lit) // 7)][:8]):
        x, y = GX + w * PITCH, 92 + d * PITCH
        hits.append(
            f'<rect class="hit" x="{x-1:.1f}" y="{y-1:.1f}" width="{CELL+2}" height="{CELL+2}" rx="3" '
            f'fill="#ffffff" style="animation-delay:-{i * 1.37 % 11:.2f}s"/>'
        )

    lasers = "".join(
        f'<rect class="laser" x="{-9 + i * 6}" y="196" width="2" height="54" rx="1" fill="{CYAN}" '
        f'style="animation-delay:{i * 0.42:.2f}s"/>'
        for i in range(4)
    )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="330" viewBox="0 0 {W} 330" role="img" aria-label="Contribution space shooter: {st["total"]} contributions between {start} and {last}">
<title>Contribution space shooter</title>
<defs>
  <linearGradient id="sbg" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="{BG0}"/><stop offset="100%" stop-color="{BG1}"/>
  </linearGradient>
  <filter id="glow" x="-80%" y="-80%" width="260%" height="260%">
    <feGaussianBlur stdDeviation="3" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <pattern id="sscan" width="4" height="4" patternUnits="userSpaceOnUse">
    <rect width="4" height="1" fill="#ffffff" opacity=".03"/>
  </pattern>
  <style>
    .ship {{ animation: patrol 11s ease-in-out infinite; }}
    .laser {{ animation: fire 2.2s linear infinite; }}
    .muzzle {{ animation: flash .55s steps(2,end) infinite; }}
    .hit {{ animation: hit 11s linear infinite; opacity: 0; }}
    .spark {{ animation: spark 11s linear infinite; opacity: 0; }}
    @keyframes patrol {{ 0%,100% {{ transform: translateX(-288px); }} 50% {{ transform: translateX(288px); }} }}
    @keyframes fire {{ 0% {{ transform: translateY(0); opacity: 0; }} 8% {{ opacity: 1; }} 60% {{ opacity: .9; }} 100% {{ transform: translateY(-104px); opacity: 0; }} }}
    @keyframes flash {{ 0% {{ opacity: 1; }} 100% {{ opacity: .25; }} }}
    @keyframes hit {{ 0%,86% {{ opacity: 0; }} 88% {{ opacity: .95; }} 92% {{ opacity: .25; }} 100% {{ opacity: 0; }} }}
    @keyframes spark {{ 0%,84% {{ opacity: 0; transform: scale(.2); }} 88% {{ opacity: .9; transform: scale(1); }} 100% {{ opacity: 0; transform: scale(1.6); }} }}
  </style>
</defs>
<rect width="{W}" height="330" rx="18" fill="url(#sbg)"/>
<text x="{GX}" y="42" font-family="{MONO}" font-size="10.5" letter-spacing="2.6" fill="{CYAN}">◉ PLAYER ONE</text>
<text x="{W-GX}" y="42" text-anchor="end" font-family="{MONO}" font-size="10.5" letter-spacing="1.4" fill="{MUTED}">{start} → {last}</text>
<line x1="{GX}" y1="58" x2="{W-GX}" y2="58" stroke="#ffffff" stroke-opacity=".09"/>
{"".join(cells)}
{"".join(hits)}
<g class="ship" transform="translate(430 0)">
  <rect x="-16" y="188" width="32" height="74" fill="{CYAN}" opacity=".05"/>
  {lasers}
  <g filter="url(#glow)">
    <path d="M0 246 L13 272 L0 264 L-13 272 Z" fill="{CYAN}" fill-opacity=".95"/>
    <path d="M0 252 L7 268 L-7 268 Z" fill="#e6fbff"/>
    <circle class="muzzle" cx="0" cy="262" r="3" fill="#e6fbff"/>
  </g>
</g>
<text x="{GX}" y="308" font-family="{MONO}" font-size="10" letter-spacing="1.6" fill="{MUTED}">SCORE <tspan fill="{GREEN}">{st["total"]:04d}</tspan></text>
<text x="{GX+190}" y="308" font-family="{MONO}" font-size="10" letter-spacing="1.6" fill="{MUTED}">ACTIVE DAYS <tspan fill="{TEXT}">{st["active"]}</tspan></text>
<text x="{GX+390}" y="308" font-family="{MONO}" font-size="10" letter-spacing="1.6" fill="{MUTED}">BEST DAY <tspan fill="{YELLOW}">{st["bestdayn"]}</tspan></text>
<text x="{W-GX}" y="308" text-anchor="end" font-family="{MONO}" font-size="10" letter-spacing="1.6" fill="{MUTED}">COMBO ×<tspan fill="{MAGENTA}">{st["best"]:02d}</tspan></text>
<rect width="{W}" height="330" rx="18" fill="url(#sscan)"/>
<rect x=".75" y=".75" width="{W-1.5}" height="328.5" rx="17.5" fill="none" stroke="{BORDER}" stroke-opacity=".4"/>
</svg>
'''


# ------------------------------------------------------------ snake

def build_snake(weeks, st, start, last):
    seq = []
    for w, col in enumerate(weeks):
        order = range(ROWS) if w % 2 == 0 else range(ROWS - 1, -1, -1)
        for d in order:
            if col[d]:
                seq.append((w, d, col[d]))
    pts = [(GX + w * PITCH + CELL / 2, 92 + d * PITCH + CELL / 2) for w, d, _ in seq]
    step_of = {(w, d): i for i, (w, d, _) in enumerate(seq)}
    path = "M " + " L ".join(f"{x:.1f} {y:.1f}" for x, y in pts)
    total_steps = max(1, len(pts) - 1)

    cells = []
    for w, col in enumerate(weeks):
        for d, c in enumerate(col):
            if not c:
                continue
            x, y = GX + w * PITCH, 92 + d * PITCH
            if c["c"] > 0:
                delay = step_of[(w, d)] / total_steps * 7.2
                cells.append(
                    f'<rect class="cell" x="{x:.1f}" y="{y:.1f}" width="{CELL}" height="{CELL}" rx="2" '
                    f'fill="{LEVEL[min(c["l"], 4) - 1]}" style="animation-delay:{delay:.2f}s"/>'
                )
            else:
                cells.append(
                    f'<rect x="{x:.1f}" y="{y:.1f}" width="{CELL}" height="{CELL}" rx="2" '
                    f'fill="{EMPTY}" stroke="#1b2735" stroke-width=".6"/>'
                )

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="330" viewBox="0 0 {W} 330" role="img" aria-label="Snake trail over {st["total"]} contributions, {st["active"]} active days">
<title>Contribution snake trail</title>
<defs>
  <linearGradient id="nbg" x1="0" y1="0" x2="0" y2="1">
    <stop offset="0%" stop-color="{BG1}"/><stop offset="100%" stop-color="{BG0}"/>
  </linearGradient>
  <linearGradient id="trail" x1="0" y1="0" x2="1" y2="0">
    <stop offset="0%" stop-color="{GREEN}"/><stop offset="55%" stop-color="{LIME}"/><stop offset="100%" stop-color="{CYAN}"/>
  </linearGradient>
  <filter id="nglow" x="-60%" y="-60%" width="220%" height="220%">
    <feGaussianBlur stdDeviation="4" result="b"/><feMerge><feMergeNode in="b"/><feMergeNode in="SourceGraphic"/></feMerge>
  </filter>
  <pattern id="nscan" width="4" height="4" patternUnits="userSpaceOnUse">
    <rect width="4" height="1" fill="#ffffff" opacity=".03"/>
  </pattern>
  <style>
    .trail {{ stroke-dasharray: 1; stroke-dashoffset: 1; animation: draw 9s linear infinite; }}
    .cell {{ animation: pop 9s linear infinite; opacity: .28; }}
    @keyframes draw {{
      0% {{ stroke-dashoffset: 1; opacity: .9; }}
      82% {{ stroke-dashoffset: 0; opacity: .9; }}
      97% {{ stroke-dashoffset: 0; opacity: 0; }}
      100% {{ stroke-dashoffset: 1; opacity: 0; }}
    }}
    @keyframes pop {{
      0% {{ opacity: .22; }}
      6% {{ opacity: 1; }}
      70% {{ opacity: .95; }}
      86%,100% {{ opacity: .22; }}
    }}
  </style>
</defs>
<rect width="{W}" height="330" rx="18" fill="url(#nbg)"/>
<text x="{GX}" y="42" font-family="{MONO}" font-size="10.5" letter-spacing="2.6" fill="{LIME}">◉ TRAIL MODE</text>
<text x="{W-GX}" y="42" text-anchor="end" font-family="{MONO}" font-size="10.5" letter-spacing="1.4" fill="{MUTED}">LONGEST RUN {st["best"]:02d} DAYS</text>
<line x1="{GX}" y1="58" x2="{W-GX}" y2="58" stroke="#ffffff" stroke-opacity=".09"/>
{"".join(cells)}
<path class="trail" d="{path}" fill="none" stroke="url(#trail)" stroke-width="4.4" stroke-linecap="round" stroke-linejoin="round" pathLength="1" filter="url(#nglow)"/>
<circle r="6" fill="#ffffff" filter="url(#nglow)">
  <animateMotion dur="9s" repeatCount="indefinite" path="{path}" keyPoints="0;1;1" keyTimes="0;0.82;1" calcMode="linear"/>
</circle>
<text x="{GX}" y="308" font-family="{MONO}" font-size="10" letter-spacing="1.6" fill="{MUTED}">TOTAL <tspan fill="{GREEN}">{st["total"]}</tspan></text>
<text x="{GX+170}" y="308" font-family="{MONO}" font-size="10" letter-spacing="1.6" fill="{MUTED}">ACTIVE <tspan fill="{TEXT}">{st["active"]}</tspan></text>
<text x="{GX+330}" y="308" font-family="{MONO}" font-size="10" letter-spacing="1.6" fill="{MUTED}">BEST DAY <tspan fill="{YELLOW}">{st["bestdayn"]}</tspan> · {st["bestday"]}</text>
<text x="{W-GX}" y="308" text-anchor="end" font-family="{MONO}" font-size="10" letter-spacing="1.6" fill="{MUTED}">STREAK <tspan fill="{MAGENTA}">{st["streak"]:02d}</tspan></text>
<rect width="{W}" height="330" rx="18" fill="url(#nscan)"/>
<rect x=".75" y=".75" width="{W-1.5}" height="328.5" rx="17.5" fill="none" stroke="{BORDER}" stroke-opacity=".4"/>
</svg>
'''


def main():
    user = gh(f"users/{LOGIN}")
    repos = json.loads(subprocess.run(
        ["gh", "repo", "list", LOGIN, "--limit", "100", "--visibility", "public",
         "--json", "name,description,stargazerCount,primaryLanguage,isFork,pushedAt,url"],
        capture_output=True, text=True, check=True).stdout)
    live = [r for r in repos if not r["isFork"]]
    langs = {}
    for r in live[:40]:
        for name, size in gh(f"repos/{LOGIN}/{r['name']}/languages").items():
            langs[name] = langs.get(name, 0) + size
    total_lang = sum(langs.values()) or 1
    colors = {"TypeScript": "#3178c6", "JavaScript": "#f1e05a", "Python": "#3572A5",
              "HTML": "#e34c26", "CSS": "#663399", "EJS": "#a91e50", "SCSS": "#c6538c",
              "Java": "#b07219", "Shell": "#89e051", "Dockerfile": "#384d54"}
    top_langs = [
        {"name": k, "color": colors.get(k, CYAN), "percentage": round(v / total_lang * 100)}
        for k, v in sorted(langs.items(), key=lambda kv: -kv[1])
    ]

    weeks, start, last = fetch_contributions(LOGIN)
    st = stats(weeks)
    profile = {
        "name": user["name"], "bio": user["bio"], "avatarUrl": user["avatar_url"],
        "followers": user["followers"],
        "totalRepos": len(live),
        "totalStars": sum(r["stargazerCount"] for r in live),
    }

    (OUT / "hero.svg").write_text(build_hero(profile, top_langs, st), encoding="utf-8")
    (OUT / "space-shooter.svg").write_text(build_shooter(weeks, st, start, last), encoding="utf-8")
    (OUT / "snake.svg").write_text(build_snake(weeks, st, start, last), encoding="utf-8")
    print(f"wrote 3 cards · {st['total']} contributions · {len(live)} repos · {len(top_langs)} languages")
    print("top repos:")
    for r in sorted(live, key=lambda r: (-r["stargazerCount"], r["pushedAt"]), reverse=False)[:8]:
        print(f"  {r['name']:<32}{(r['primaryLanguage'] or {}).get('name','-'):<12}★{r['stargazerCount']}  {r['pushedAt'][:10]}")


if __name__ == "__main__":
    main()