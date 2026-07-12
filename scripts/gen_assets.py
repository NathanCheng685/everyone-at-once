"""Generate brand-consistent SVG assets (no external deps, no AI image model):

  - Character monogram avatars  -> web/img/<ip>/<char>.svg   (color + initial)
  - Themed IP card art          -> web/img/ip-<id>.svg       (gradient + emblem)

The app deliberately avoids real character likenesses (the existing IP cards are
generic thematic art, not copyrighted faces), so we stay symbolic: tasteful
initial-avatars and motif emblems. Drop a real raster into web/img/ to override.

Run:  .venv/bin/python scripts/gen_assets.py            # all
      .venv/bin/python scripts/gen_assets.py --sample   # just the preview set
"""
import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMG = ROOT / "web" / "img"
IPS = ROOT / "ips"

# IPs whose character avatars we generate (friends already has real PNGs).
AVATAR_IPS = ("harry-potter", "avengers", "naruto", "fifa", "nba")


def _h(c):
    c = c.lstrip("#")
    return int(c[0:2], 16), int(c[2:4], 16), int(c[4:6], 16)


def lighten(c, t=0.42):
    r, g, b = _h(c)
    return f"#{int(r+(255-r)*t):02x}{int(g+(255-g)*t):02x}{int(b+(255-b)*t):02x}"


def darken(c, k=0.22):
    r, g, b = _h(c)
    return f"#{int(r*(1-k)):02x}{int(g*(1-k)):02x}{int(b*(1-k)):02x}"


def avatar_svg(color, initial):
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 220 220">
  <defs>
    <linearGradient id="g" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{lighten(color)}"/>
      <stop offset="1" stop-color="{darken(color)}"/>
    </linearGradient>
    <radialGradient id="s" cx="0.32" cy="0.26" r="0.85">
      <stop offset="0" stop-color="#ffffff" stop-opacity="0.30"/>
      <stop offset="0.55" stop-color="#ffffff" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="220" height="220" fill="url(#g)"/>
  <rect width="220" height="220" fill="url(#s)"/>
  <text x="110" y="118" text-anchor="middle" dominant-baseline="central"
        font-family="Fraunces, Georgia, 'Times New Roman', serif" font-weight="500"
        font-size="118" fill="#ffffff" fill-opacity="0.94">{initial}</text>
</svg>
"""


def _card(top, bot, glow, emblem):
    """Shared 4:3 IP-card frame: diagonal gradient + radial glow + centered motif.

    No title text baked in — the app renders ip.title / ip.tagline in the card
    body beneath the thumb (matching the existing friends/hp/avengers art)."""
    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 760 570">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1" y2="1">
      <stop offset="0" stop-color="{top}"/>
      <stop offset="1" stop-color="{bot}"/>
    </linearGradient>
    <radialGradient id="glow" cx="0.5" cy="0.5" r="0.62">
      <stop offset="0" stop-color="{glow}" stop-opacity="0.55"/>
      <stop offset="1" stop-color="{glow}" stop-opacity="0"/>
    </radialGradient>
  </defs>
  <rect width="760" height="570" fill="url(#bg)"/>
  <rect width="760" height="570" fill="url(#glow)"/>
  <g transform="translate(380 285)">{emblem}</g>
</svg>
"""


def naruto_card():
    # Uzumaki-style swirl emblem.
    swirl = ('<circle r="118" fill="none" stroke="#ffffff" stroke-opacity="0.14" stroke-width="16"/>'
             '<path d="M0,-86 A86,86 0 1 1 -70,50 A52,52 0 1 0 32,24 A24,24 0 1 1 0,-2"'
             ' fill="none" stroke="#ffffff" stroke-opacity="0.92" stroke-width="17"'
             ' stroke-linecap="round"/>'
             '<circle r="12" fill="#ffffff" fill-opacity="0.92"/>')
    return _card("#F0A35E", "#B5491B", "#FFD9A0", swirl)


def chinese_card():
    # Mountains + sea-waves + sun motif (山海经 mood).
    sun = '<circle cx="0" cy="-58" r="50" fill="#F6D98A" fill-opacity="0.92"/>'
    mtn = ('<path d="M-190,92 L-72,-52 L-8,40 L76,-74 L190,92 Z"'
           ' fill="#ffffff" fill-opacity="0.15"/>'
           '<path d="M-190,92 L-72,-52 L-26,12 L-190,92 Z" fill="#ffffff" fill-opacity="0.10"/>')
    waves = ''.join(
        f'<path d="M-190,{112+i*24} q 48,-22 95,0 q 48,22 95,0 q 48,-22 95,0 q 48,22 95,0"'
        f' fill="none" stroke="#ffffff" stroke-opacity="{0.5-i*0.13:.2f}" stroke-width="7"/>'
        for i in range(3))
    return _card("#9E2B2B", "#4A1414", "#E8B04B", sun + mtn + waves)


def fifa_card():
    # Football: center circle + halfway line on grass, classic ball at kickoff.
    pitch = ('<rect x="-380" y="-285" width="760" height="570" fill="#ffffff" fill-opacity="0"/>'
             '<line x1="-380" y1="0" x2="380" y2="0" stroke="#ffffff" stroke-opacity="0.35" stroke-width="6"/>'
             '<circle r="130" fill="none" stroke="#ffffff" stroke-opacity="0.35" stroke-width="6"/>')
    stripes = ''.join(
        f'<rect x="{-380+i*95}" y="-285" width="95" height="570" fill="#ffffff" fill-opacity="{0.05 if i%2 else 0:.2f}"/>'
        for i in range(8))
    ball = ('<circle r="62" fill="#ffffff" fill-opacity="0.95"/>'
            '<path d="M0,-26 L24,-8 L15,20 L-15,20 L-24,-8 Z" fill="#1C2B22"/>'
            ''.join(f'<path transform="rotate({a})" d="M0,-62 L0,-26" stroke="#1C2B22" stroke-width="7"/>'
                    for a in (0, 72, 144, 216, 288)) +
            '<circle r="62" fill="none" stroke="#1C2B22" stroke-opacity="0.75" stroke-width="5"/>')
    return _card("#2F9E55", "#125A31", "#B8F0C8", stripes + pitch + ball)


def nba_card():
    # Basketball: big ball with seams, floor-line arcs behind.
    arcs = ('<circle r="150" fill="none" stroke="#ffffff" stroke-opacity="0.16" stroke-width="10"/>'
            '<circle r="200" fill="none" stroke="#ffffff" stroke-opacity="0.09" stroke-width="10"/>')
    ball = ('<circle r="104" fill="#E8833A"/>'
            '<circle r="104" fill="none" stroke="#3D1E0C" stroke-opacity="0.85" stroke-width="7"/>'
            '<path d="M-104,0 H104 M0,-104 V104" stroke="#3D1E0C" stroke-opacity="0.85" stroke-width="7" fill="none"/>'
            '<path d="M-74,-74 Q0,-20 74,-74 M-74,74 Q0,20 74,74" stroke="#3D1E0C" stroke-opacity="0.85"'
            ' stroke-width="7" fill="none"/>')
    return _card("#B24B2E", "#5A1E14", "#F2B27E", arcs + ball)


def write(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def gen_avatars(ip):
    chars = json.loads((IPS / ip / "characters.json").read_text(encoding="utf-8"))["characters"]
    n = 0
    for c in chars:
        initial = (c.get("name_en") or c["id"])[0].upper()
        color = c.get("color", "#C8553D")
        write(IMG / ip / f"{c['id']}.svg", avatar_svg(color, initial))
        n += 1
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sample", action="store_true", help="only naruto + chinese card preview")
    args = ap.parse_args()

    if args.sample:
        write(IMG / "ip-naruto.svg", naruto_card())
        write(IMG / "ip-chinese-mythology.svg", chinese_card())
        n = gen_avatars("naruto")
        print(f"sample: ip-naruto.svg, ip-chinese-mythology.svg, {n} naruto avatars")
        return

    write(IMG / "ip-naruto.svg", naruto_card())
    write(IMG / "ip-chinese-mythology.svg", chinese_card())
    write(IMG / "ip-fifa.svg", fifa_card())
    write(IMG / "ip-nba.svg", nba_card())
    total = 0
    for ip in AVATAR_IPS:
        total += gen_avatars(ip)
    print(f"wrote 4 IP cards + {total} character avatars under web/img/")


if __name__ == "__main__":
    main()
