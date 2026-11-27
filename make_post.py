#!/usr/bin/env python3
"""CodeAj Marketplace Instagram post generator.

Usage:
  python3 make_post.py spec.json OUT_DIR
  python3 make_post.py --styles            # list the design styles

spec.json:
{
  "type": "carousel" | "reel" | "story",
  "slug": "2026-11-27-ai-project-ideas",
  "style": "terminal",                    # design style, see STYLES below. Pick one that is
                                          # NOT among the last 5 posts in history.json.
                                          # "festival" only on festival days.
  "festival": "Diwali",                   # optional, festival style only: name shown as a badge
  "caption": "...",                       # used later for posting
  "slides": [                             # carousel: 4-10 slides
     {"kicker": "Final year 2026", "title": "...", "body": "...", "points": ["...", "..."],
      "code": "print(1)\\nprint(2)", "options": ["A", "B"]}
  ],
  "scenes": [                             # reel: 4-8 scenes / story: 1 scene
     {"text": "On-screen text", "sub": "small line (optional)", "vo": "English voiceover"}
  ],
  "voice": "bf_emma",
  "cta": "Comment DEMO",                  # last slide / last scene
  "review": {"name": "Ganesh Sawant", "text": "..."}   # optional, real Google review only
}
"""
import json, math, os, random, subprocess, sys
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")
FONTS = os.path.join(ASSETS, "fonts")

# Brand: taken from the CodeAj Marketplace logo (navy swoosh, blue, orange "PROJECTS")
NAVY = (20, 54, 90)
NAVY_DARK = (11, 27, 46)
BLUE = (46, 111, 183)
ORANGE = (247, 147, 30)
CREAM = (248, 250, 253)
GREY = (92, 105, 122)
WHITE = (255, 255, 255)
GOLD_STAR = (251, 188, 5)

GOOGLE_RATING = "5.0"
GOOGLE_COUNT = "48"
SITE = "projects.codeaj.com"

# ---------------- design styles ----------------
# Each style changes background, fonts, colours, kicker, bullet markers, cards, alignment and
# decoration, so consecutive posts never look alike. Keys:
#   mode(i, n) -> "light" | "dark" | "accent"   which surface slide i of n uses
#   fonts: title/body/med/label/mono file names (+ "title_var" for variable fonts)
#   decor: glow | grid | stripes | editorial | dots | frame | festival
#   kicker: pill | prompt | bar | underline | number | gold
#   marker: check | arrow | num | dash | numplain | diamond
#   card:   white | dark | none | rule | cream
#   align:  left | center
STYLES = {
    "classic": dict(
        desc="Brand navy/cream with soft glows, check-box cards (the original look).",
        surfaces=dict(light=(CREAM, (11, 27, 46), GREY), dark=(NAVY_DARK, WHITE, (200, 212, 228)),
                      accent=(NAVY_DARK, WHITE, (200, 212, 228))),
        mode=lambda i, n: "dark" if i == 1 else "light",
        fonts=dict(title="Poppins-Bold.ttf", body="Poppins-Regular.ttf", med="Poppins-Medium.ttf",
                   label="Poppins-Bold.ttf"),
        accent=ORANGE, accent2=BLUE, decor="glow", kicker="pill", marker="check", card="white",
        align="left", title_scale=1.0, upper=False),
    "terminal": dict(
        desc="Dark code-editor look: GitHub-dark background, grid, green prompt kicker, mono details.",
        surfaces=dict(light=((13, 17, 23), (230, 237, 243), (139, 148, 158)),
                      dark=((13, 17, 23), (230, 237, 243), (139, 148, 158)),
                      accent=((1, 4, 9), (230, 237, 243), (139, 148, 158))),
        mode=lambda i, n: "accent" if i in (1, n) else "dark",
        fonts=dict(title="Inter-Black.otf", body="Inter-Regular.otf", med="Inter-Medium.otf",
                   label="DejaVuSansMono-Bold.ttf"),
        accent=(63, 185, 80), accent2=(88, 166, 255), decor="grid", kicker="prompt", marker="arrow",
        card="dark", align="left", title_scale=1.0, upper=False),
    "poster": dict(
        desc="Loud poster: huge condensed uppercase titles, solid orange cover, big numbered points.",
        surfaces=dict(light=((255, 244, 230), (11, 27, 46), (90, 80, 70)),
                      dark=(NAVY_DARK, WHITE, (200, 212, 228)),
                      accent=(ORANGE, (11, 27, 46), (60, 35, 10))),
        mode=lambda i, n: "accent" if i in (1, n) else ("dark" if i % 2 == 0 else "light"),
        fonts=dict(title="Anton-Regular.ttf", body="Poppins-Regular.ttf", med="Poppins-Medium.ttf",
                   label="Poppins-Bold.ttf"),
        accent=ORANGE, accent2=BLUE, decor="stripes", kicker="bar", marker="num", card="none",
        align="left", title_scale=1.45, upper=True),
    "editorial": dict(
        desc="Magazine page: warm paper, serif headlines, big faded slide numbers, rust accents.",
        surfaces=dict(light=((246, 241, 231), (33, 30, 28), (105, 96, 86)),
                      dark=((33, 30, 28), (246, 241, 231), (190, 180, 165)),
                      accent=((33, 30, 28), (246, 241, 231), (190, 180, 165))),
        mode=lambda i, n: "accent" if i == 1 else "light",
        fonts=dict(title="Lora-Variable.ttf", title_var="Bold", body="Inter-Regular.otf",
                   med="Inter-Medium.otf", label="Inter-Bold.otf"),
        accent=(196, 80, 30), accent2=(20, 54, 90), decor="editorial", kicker="underline",
        marker="dash", card="rule", align="left", title_scale=1.05, upper=False),
    "pop": dict(
        desc="Vivid gradients that change every slide, chunky centred titles, white cards.",
        surfaces=dict(light=(None, WHITE, (236, 240, 255)), dark=(None, WHITE, (236, 240, 255)),
                      accent=(None, WHITE, (236, 240, 255))),
        mode=lambda i, n: "accent",
        gradients=[((46, 111, 183), (124, 58, 237)), ((247, 147, 30), (219, 39, 119)),
                   ((13, 148, 136), (46, 111, 183)), ((124, 58, 237), (219, 39, 119)),
                   ((234, 88, 12), (202, 138, 4))],
        fonts=dict(title="ArchivoBlack-Regular.ttf", body="Poppins-Regular.ttf",
                   med="Poppins-Medium.ttf", label="Poppins-Bold.ttf"),
        accent=WHITE, accent2=(124, 58, 237), decor="dots", kicker="pill_white", marker="num",
        card="white", align="center", title_scale=0.95, upper=False),
    "minimal": dict(
        desc="Clean Swiss minimal: white page, black type, one orange block, thin frame, lots of space.",
        surfaces=dict(light=(WHITE, (17, 17, 17), (95, 95, 95)), dark=(WHITE, (17, 17, 17), (95, 95, 95)),
                      accent=((17, 17, 17), WHITE, (190, 190, 190))),
        mode=lambda i, n: "accent" if i == n else "light",
        fonts=dict(title="Inter-Black.otf", body="Inter-Regular.otf", med="Inter-Medium.otf",
                   label="Inter-Bold.otf"),
        accent=ORANGE, accent2=(17, 17, 17), decor="frame", kicker="number", marker="numplain",
        card="rule", align="left", title_scale=1.1, upper=False),
    "festival": dict(
        desc="Festival days only: maroon and cream, marigold garland, rangoli dot motifs, gold accents.",
        surfaces=dict(light=((255, 247, 230), (92, 18, 32), (120, 70, 50)),
                      dark=((92, 18, 32), (255, 240, 210), (240, 200, 160)),
                      accent=((92, 18, 32), (255, 240, 210), (240, 200, 160))),
        mode=lambda i, n: "accent" if i in (1, n) else "light",
        fonts=dict(title="Lora-Variable.ttf", title_var="Bold", body="Poppins-Regular.ttf",
                   med="Poppins-Medium.ttf", label="Poppins-Bold.ttf"),
        accent=(255, 166, 0), accent2=(214, 51, 108), decor="festival", kicker="gold",
        marker="diamond", card="cream", align="center", title_scale=1.05, upper=False),
}

T = STYLES["classic"]   # active style, set in main()
SPEC = {}


def set_style(name):
    global T
    if name not in STYLES:
        raise SystemExit(f"unknown style '{name}'. Options: {', '.join(STYLES)}")
    T = STYLES[name]
    T["name"] = name


_font_cache = {}


def F(role, size):
    """Font for a role of the active style: title | body | med | label | mono."""
    if role == "mono":
        fn, var = "DejaVuSansMono.ttf", None
    else:
        fn, var = T["fonts"][role], (T["fonts"].get("title_var") if role == "title" else None)
    key = (fn, var, size)
    if key not in _font_cache:
        p = os.path.join(FONTS, fn)
        f = ImageFont.truetype(p, size) if os.path.exists(p) else ImageFont.load_default(size)
        if var:
            try:
                f.set_variation_by_name(var)
            except Exception:
                pass
        _font_cache[key] = f
    return _font_cache[key]


def font(weight, size):
    """Brand Poppins (used by the trust badge in every style)."""
    n = {"bold": "Poppins-Bold.ttf", "semi": "Poppins-Bold.ttf", "med": "Poppins-Medium.ttf",
         "reg": "Poppins-Regular.ttf", "black": "Poppins-Bold.ttf"}[weight]
    return ImageFont.truetype(os.path.join(FONTS, n), size)


def mono(size):
    return ImageFont.truetype(os.path.join(FONTS, "DejaVuSansMono.ttf"), size)


def wrap(draw, text, fnt, max_w):
    words, lines, cur = text.split(), [], ""
    for w in words:
        t = (cur + " " + w).strip()
        if draw.textlength(t, font=fnt) <= max_w:
            cur = t
        else:
            if cur:
                lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def draw_lines(draw, lines, fnt, x, y, fill, gap=1.18, center_w=None):
    lh = int(fnt.size * gap)
    for ln in lines:
        xx = x
        if center_w:
            xx = x + (center_w - draw.textlength(ln, font=fnt)) / 2
        draw.text((xx, y), ln, font=fnt, fill=fill)
        y += lh
    return y


def star(draw, cx, cy, r, fill):
    pts = []
    for i in range(10):
        ang = math.pi / 2 + i * math.pi / 5
        rr = r if i % 2 == 0 else r * 0.45
        pts.append((cx + rr * math.cos(ang), cy - rr * math.sin(ang)))
    draw.polygon(pts, fill=fill)


def trust_badge(img, x, y, scale=1.0, dark=False):
    """'G 5.0 ★★★★★ 48 Google reviews' pill. Uses only the real Google rating."""
    d = ImageDraw.Draw(img)
    h = int(64 * scale)
    f_big = font("bold", int(30 * scale))
    f_small = font("med", int(20 * scale))
    label = f"{GOOGLE_COUNT} Google reviews"
    w = int(h * 0.9 + d.textlength(GOOGLE_RATING, font=f_big) + 5 * h * 0.42 + d.textlength(label, font=f_small) + h * 1.1)
    d.rounded_rectangle([x, y, x + w, y + h], radius=h // 2, fill=WHITE, outline=(225, 230, 238), width=2)
    gx = x + h * 0.55
    d.text((gx - d.textlength("G", font=f_big) / 2, y + h * 0.12), "G", font=f_big, fill=(66, 133, 244))
    cx = x + h * 0.95
    d.text((cx, y + h * 0.12), GOOGLE_RATING, font=f_big, fill=NAVY_DARK)
    cx += d.textlength(GOOGLE_RATING, font=f_big) + h * 0.25
    for i in range(5):
        star(d, cx + h * 0.2, y + h / 2, h * 0.2, GOLD_STAR)
        cx += h * 0.42
    cx += h * 0.15
    d.text((cx, y + h * 0.29), label, font=f_small, fill=GREY)
    return w, h


def paste_logo(img, x, y, width, pill=False):
    logo = Image.open(os.path.join(ASSETS, "logo.webp")).convert("RGBA")
    r = width / logo.width
    logo = logo.resize((width, int(logo.height * r)), Image.LANCZOS)
    if pill:
        d = ImageDraw.Draw(img)
        p = int(width * 0.06)
        d.rounded_rectangle([x - p, y - p // 2, x + width + p, y + logo.height + p // 2], radius=int(width * 0.08), fill=WHITE)
    img.alpha_composite(logo, (x, y))
    return logo.height


def arrow(draw, x, y, w, color, t=5):
    draw.line([x, y, x + w, y], fill=color, width=t)
    draw.line([x + w - 14, y - 12, x + w, y, x + w - 14, y + 12], fill=color, width=t, joint="curve")


def mix(a, b, t):
    return tuple(int(a[k] + (b[k] - a[k]) * t) for k in range(3))


def surface(i, n):
    """(bg, ink, soft, mode) for slide/scene i of n."""
    m = T["mode"](i, n)
    bg, ink, soft = T["surfaces"][m]
    return bg, ink, soft, m


def is_darkish(c):
    return c is None or sum(c) < 380


def readable(col, bg):
    """col, unless it is too close to the background bg; then a contrasting brand colour."""
    if bg is None:
        return col
    if sum(abs(a - b) for a, b in zip(col, bg)) >= 160:
        return col
    return NAVY_DARK if not is_darkish(bg) else WHITE


def link_color(bg):
    if T["name"] == "minimal":
        return readable(ORANGE, bg)
    if T["name"] == "festival" and not is_darkish(bg):
        return (92, 18, 32)
    return readable(T["accent"], bg)


def background(W, H, i, n):
    bg, ink, soft, m = surface(i, n)
    decor = T["decor"]
    if decor == "dots" or bg is None:   # pop: diagonal gradient, new pair per slide
        c1, c2 = T["gradients"][(i - 1) % len(T["gradients"])]
        grad = Image.new("RGB", (2, 2))
        grad.putdata([c1, mix(c1, c2, .5), mix(c1, c2, .5), c2])
        img = grad.resize((W, H), Image.BILINEAR).convert("RGBA")
    else:
        img = Image.new("RGBA", (W, H), bg + (255,))
    lay = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    g = ImageDraw.Draw(lay)
    dark = is_darkish(bg)
    rnd = random.Random(f"{SPEC.get('slug', '')}-{i}")
    if decor == "glow":
        g.ellipse([W * 0.55, -H * 0.15, W * 1.35, H * 0.45], fill=BLUE + ((120 if dark else 38),))
        g.ellipse([-W * 0.4, H * 0.7, W * 0.45, H * 1.25], fill=ORANGE + ((70 if dark else 30),))
        lay = lay.filter(ImageFilter.GaussianBlur(60))
    elif decor == "grid":
        for x in range(0, W, 54):
            g.line([x, 0, x, H], fill=(255, 255, 255, 14), width=1)
        for y in range(0, H, 54):
            g.line([0, y, W, y], fill=(255, 255, 255, 14), width=1)
        g.ellipse([W * 0.5, -H * 0.2, W * 1.3, H * 0.35], fill=T["accent"] + (34,))
        lay = lay.filter(ImageFilter.GaussianBlur(1))
        glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        ImageDraw.Draw(glow).ellipse([W * 0.55, -H * 0.2, W * 1.3, H * 0.3], fill=T["accent2"] + (50,))
        lay.alpha_composite(glow.filter(ImageFilter.GaussianBlur(90)))
    elif decor == "stripes":
        col = (255, 255, 255, 22) if dark or m == "accent" else (11, 27, 46, 14)
        for k in range(-H, W, 46):
            g.line([k, H, k + H * 0.5, H - H * 0.5 * 1.0], fill=col, width=14)
        lay = lay.crop((0, 0, W, H))
        mask = Image.new("L", (W, H), 0)
        ImageDraw.Draw(mask).rectangle([0, int(H * 0.78), W, H], fill=255)
        lay.putalpha(Image.composite(lay.getchannel("A"), Image.new("L", (W, H), 0), mask))
        if m != "accent":
            ImageDraw.Draw(lay).rectangle([0, 0, 22, H], fill=T["accent"] + (255,))
    elif decor == "editorial":
        fnum = F("title", 420)
        num = f"{i:02d}"
        tw = g.textlength(num, font=fnum)
        g.text((W - tw - 40, H - 560), num, font=fnum,
               fill=(T["accent"] + (36,)) if not dark else (255, 255, 255, 22))
        g.line([80, 200, W - 80, 200], fill=(ink + (90,)), width=2)
    elif decor == "dots":
        for _ in range(3):
            cx, cy, r = rnd.randint(-100, W + 100), rnd.randint(-100, H + 100), rnd.randint(180, 340)
            g.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(255, 255, 255, 26))
        for y in range(H - 330, H, 30):
            for x in range(W - 330, W, 30):
                rr = max(0, 7 - ((W - x) + (H - y)) / 95)
                if rr > 0.6:
                    g.ellipse([x - rr, y - rr, x + rr, y + rr], fill=(255, 255, 255, 80))
    elif decor == "frame":
        col = ink + (255,)
        g.rectangle([36, 36, W - 36, H - 36], outline=col, width=3)
        if m != "accent":
            g.rectangle([W - 36 - 150, H - 36 - 22, W - 36, H - 36], fill=T["accent"] + (255,))
    elif decor == "festival":
        gold = (212, 160, 23)
        # marigold garland: drooping string of flowers across the top
        for k in range(0, W + 40, 34):
            t = k / W
            y = 24 + math.sin(t * math.pi * 3) ** 2 * 40
            r = 17
            colr = T["accent"] if (k // 34) % 2 == 0 else (255, 205, 40)
            g.ellipse([k - r, y - r, k + r, y + r], fill=colr + (255,))
            g.ellipse([k - 5, y - 5, k + 5, y + 5], fill=(200, 90, 0, 255))
        for hx in (W * 0.18, W * 0.5, W * 0.82):   # hanging strands
            for j in range(4):
                y = 80 + j * 34
                g.ellipse([hx - 14, y - 14, hx + 14, y + 14],
                          fill=(T["accent"] if j % 2 else (255, 205, 40)) + (255,))
        # rangoli dot rings in the lower corners
        for (cx, cy) in ((0, H), (W, H)):
            for ring, rr in enumerate((60, 110, 160, 210)):
                cnt = 10 + ring * 6
                for q in range(cnt):
                    a = 2 * math.pi * q / cnt
                    x, y = cx + rr * math.cos(a), cy + rr * math.sin(a)
                    s = 9 - ring
                    col = (gold if ring % 2 == 0 else T["accent2"]) + (200 if dark else 150,)
                    g.ellipse([x - s, y - s, x + s, y + s], fill=col)
        g.rectangle([28, 28, W - 28, H - 28], outline=gold + (160,), width=3)
    img.alpha_composite(lay)
    return img, ink, soft, dark


def kicker(d, text, x, y, W, M, ink, center):
    k = T["kicker"]
    acc = T["accent"]
    up = text.upper()
    if k in ("pill", "gold", "pill_white"):
        f = F("label", 30)
        tw = d.textlength(up, font=f)
        x0 = x + ((W - 2 * M) - (tw + 40)) / 2 if center else x
        fill = {"pill": acc, "gold": (212, 160, 23), "pill_white": WHITE}[k]
        tc = T["accent2"] if k == "pill_white" else WHITE
        d.rounded_rectangle([x0, y, x0 + tw + 40, y + 56], radius=28, fill=fill)
        d.text((x0 + 20, y + 9), up, font=f, fill=tc)
        return 92
    if k == "prompt":
        f = F("label", 32)
        d.text((x, y), "$ ", font=f, fill=acc)
        d.text((x + d.textlength("$ ", font=f), y), text.lower().replace(" ", "-"), font=f, fill=T["accent2"])
        return 76
    if k == "bar":
        f = F("label", 30)
        d.rectangle([x, y + 20, x + 60, y + 28], fill=acc if not is_darkish(acc) and ink != (11, 27, 46) else ink)
        d.text((x + 80, y + 4), up, font=f, fill=ink)
        return 80
    if k == "underline":
        f = F("label", 28)
        sp = " ".join(up)  # letter-spaced
        d.text((x, y), sp, font=f, fill=acc)
        d.line([x, y + 50, x + 90, y + 50], fill=acc, width=4)
        return 86
    if k == "number":
        f = F("label", 28)
        n = SPEC.get("_idx", 1)
        d.text((x, y), f"{n:02d} — {up}", font=f, fill=acc)
        return 76
    return 0


def marker(d, k, x, y, ph, ink, card_ink):
    """Draw the bullet for point k at (x, y) with row height ph. Returns text x offset."""
    m = T["marker"]
    acc = T["accent"]
    if m == "check":
        d.rounded_rectangle([x + 26, y + 26, x + 66, y + 66], radius=10, fill=BLUE)
        d.line([x + 35, y + 46, x + 43, y + 55, x + 57, y + 37], fill=WHITE, width=5)
        return 92
    if m == "arrow":
        d.text((x + 24, y + 14), ">", font=F("mono", 42), fill=acc)
        return 76
    if m == "num":
        if T["name"] == "pop":
            d.ellipse([x + 22, y + 22, x + 72, y + 72], fill=T["gradients"][(SPEC.get("_idx", 1) - 1) % 5][0])
            f = F("label", 28)
            t = str(k + 1)
            d.text((x + 47 - d.textlength(t, font=f) / 2, y + 28), t, font=f, fill=WHITE)
            return 92
        f = F("title", 74)
        d.text((x, y - 8), f"{k + 1:02d}", font=f, fill=acc if acc != ink else T["accent2"])
        return 120
    if m == "numplain":
        f = F("label", 40)
        d.text((x, y + 14), f"{k + 1}.", font=f, fill=acc)
        return 64
    if m == "dash":
        d.line([x, y + 40, x + 36, y + 40], fill=acc, width=5)
        return 60
    if m == "diamond":
        cx, cy, r = x + 44, y + 44, 14
        d.polygon([(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)], fill=T["accent2"])
        return 80
    return 40


# ---------------- carousel ----------------

def carousel_slide(s, idx, total, cta=None, review=None):
    W, H = 1080, 1350
    SPEC["_idx"] = idx
    img, ink, soft, dark = background(W, H, idx, total)
    sbg = surface(idx, total)[0]
    d = ImageDraw.Draw(img)
    M = 80 if T["decor"] != "stripes" else 90
    center = T["align"] == "center"
    acc = T["accent"]
    top_y = 56 if T["decor"] != "festival" else 200
    paste_logo(img, M if not center else (W - 300) // 2, top_y, 300, pill=dark)
    fnum = F("label", 28)
    d.text((W - M - 70, top_y + 14), f"{idx}/{total}", font=fnum, fill=soft)
    if T["name"] == "festival" and idx == 1 and SPEC.get("festival"):
        pass  # festival name is shown in the kicker by the spec writer

    is_last = cta is not None
    cw_ = W - 2 * M

    def card_colors():
        c = T["card"]
        if c == "white":
            return WHITE, (226, 232, 240), (11, 27, 46)
        if c == "dark":
            return (22, 27, 34), (48, 54, 61), ink
        if c == "cream":
            return (255, 252, 243), (212, 160, 23), (92, 18, 32)
        return None, None, ink

    def layout(dd, y0, draw_it):
        y = y0
        if s.get("kicker"):
            y += kicker(dd, s["kicker"], M, y, W, M, ink, center) if draw_it else \
                {"pill": 92, "gold": 92, "pill_white": 92, "prompt": 76, "bar": 80, "underline": 86, "number": 76}.get(T["kicker"], 0)
        base = 84 if idx == 1 else 62
        ft = F("title", int(base * T["title_scale"]))
        title = s.get("title", "")
        if T["upper"]:
            title = title.upper()
        lines = wrap(dd, title, ft, cw_)
        gap = 1.02 if T["upper"] else 1.12
        if draw_it:
            y = draw_lines(dd, lines, ft, M, y, ink, gap=gap, center_w=cw_ if center else None)
        else:
            y += len(lines) * int(ft.size * gap)
        if idx == 1:
            if draw_it and T["decor"] not in ("frame",):
                x0 = (W - 140) // 2 if center else M
                dd.rectangle([x0, y + 18, x0 + 140, y + 28], fill=acc if acc != ink else T["accent2"])
            y += 50
        else:
            y += 24 + (16 if T["upper"] else 0)
        if s.get("body"):
            fb = F("body", 36)
            bl = wrap(dd, s["body"], fb, cw_)
            if draw_it:
                y = draw_lines(dd, bl, fb, M, y, soft, gap=1.4, center_w=cw_ if center else None)
            else:
                y += len(bl) * int(36 * 1.4)
            y += 20
        if s.get("code"):
            fm = mono(30)
            cl = s["code"].split("\n")[:14]
            chh = 70 + len(cl) * 42 + 30
            if draw_it:
                bgc = (1, 4, 9) if T["name"] == "terminal" else (15, 23, 42)
                dd.rounded_rectangle([M, y, W - M, y + chh], radius=22, fill=bgc,
                                     outline=(48, 54, 61) if T["name"] == "terminal" else None, width=2)
                for k, col in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
                    dd.ellipse([M + 28 + k * 30, y + 26, M + 46 + k * 30, y + 44], fill=col)
                yy = y + 70
                for ln in cl:
                    dd.text((M + 34, yy), ln, font=fm, fill=(226, 232, 240))
                    yy += 42
            y += chh + 24
        cbg, cline, cink = card_colors()
        for k, p in enumerate(s.get("options", [])):
            fp = F("med", 36)
            pl = wrap(dd, p, fp, cw_ - 110)
            ph = len(pl) * int(36 * 1.3) + 40
            if draw_it:
                dd.rounded_rectangle([M, y, W - M, y + ph], radius=22, fill=cbg or WHITE,
                                     outline=cline or (226, 232, 240), width=2)
                dd.ellipse([M + 22, y + ph / 2 - 24, M + 70, y + ph / 2 + 24],
                           fill=acc if T["name"] in ("terminal", "poster", "festival") else NAVY)
                L = "ABCD"[k]
                fl = F("label", 28)
                dd.text((M + 46 - dd.textlength(L, font=fl) / 2, y + ph / 2 - 19), L, font=fl,
                        fill=(13, 17, 23) if T["name"] == "terminal" else WHITE)
                draw_lines(dd, pl, fp, M + 92, y + 18, cink if cbg else (11, 27, 46), gap=1.3)
            y += ph + 16
        for k, p in enumerate(s.get("points", [])):
            fp = F("med", 38)
            mk_w = {"check": 92, "arrow": 76, "num": 120 if T["name"] != "pop" else 92, "numplain": 64,
                    "dash": 60, "diamond": 80}.get(T["marker"], 40)
            pad = 0 if cbg is None else 0
            pl = wrap(dd, p, fp, cw_ - mk_w - 30)
            ph = len(pl) * int(38 * 1.3) + 44
            if draw_it:
                if cbg is not None:
                    dd.rounded_rectangle([M, y, W - M, y + ph], radius=22, fill=cbg, outline=cline, width=2)
                elif T["card"] == "rule":
                    dd.line([M, y + ph + 8, W - M, y + ph + 8], fill=mix(ink, img.getpixel((M, y + ph + 8))[:3], .75), width=2)
                off = marker(dd, k, M, y, ph, ink, cink)
                draw_lines(dd, pl, fp, M + off, y + 20, cink if cbg is not None else ink, gap=1.3)
            y += ph + 18 + pad
        return y

    top, bottom = 230 if T["decor"] != "festival" else 330, (H - 470 if is_last else H - 200)
    h = layout(d, 0, False)
    y0 = top + max(0, (bottom - top - h) // 2) if not is_last else (260 if T["decor"] != "festival" else 370)
    y = layout(d, y0, True)

    if is_last:
        if review and review.get("text"):
            box_y = max(y + 10, H - 560)
            fr = F("body", 29)
            lines = wrap(d, "“" + review["text"] + "”", fr, W - 2 * M - 60)[:3]
            bh = 70 + len(lines) * 38 + 50
            d.rounded_rectangle([M, box_y, W - M, box_y + bh], radius=26, fill=WHITE, outline=(225, 230, 238), width=2)
            sx = M + 30
            for i in range(5):
                star(d, sx + 14, box_y + 36, 14, GOLD_STAR); sx += 34
            yy = draw_lines(d, lines, fr, M + 30, box_y + 62, NAVY_DARK, gap=1.3)
            d.text((M + 30, yy + 2), "— " + review.get("name", "") + ", Google review", font=font("semi", 25), fill=GREY)
        fc = F("label", 44)
        cy = H - 280
        cw = d.textlength(cta, font=fc) + 80
        cx = (W - cw) / 2 if center else M
        btn = readable(acc, sbg)
        tcol = (13, 17, 23) if T["name"] in ("terminal",) else (T["accent2"] if btn == WHITE else WHITE)
        if T["name"] == "minimal":
            btn, tcol = ORANGE, WHITE
        d.rounded_rectangle([cx, cy, cx + cw, cy + 92], radius=46 if T["name"] != "minimal" else 0, fill=btn)
        d.text((cx + 40, cy + 18), cta, font=fc, fill=tcol)

    bw, _ = trust_badge(Image.new("RGBA", (10, 10)), 0, 0, 1.0)
    bx = (W - bw) // 2 if center and is_last is False and False else M
    trust_badge(img, bx, H - 150, 1.0)
    fs = F("label", 30)
    lc = link_color(sbg)
    if is_last:
        d.text((W - M - d.textlength(SITE, font=fs), H - 135), SITE, font=fs, fill=lc)
    else:
        t = "Swipe"
        tw = d.textlength(t, font=fs)
        d.text((W - M - tw - 60, H - 137), t, font=fs, fill=lc)
        arrow(d, W - M - 48, H - 117, 48, lc)
    return img.convert("RGB")


def make_carousel(spec, out):
    slides = spec["slides"]
    n = len(slides)
    paths = []
    for i, s in enumerate(slides, 1):
        last = i == n
        im = carousel_slide(s, i, n, cta=spec.get("cta", "Link in bio") if last else None,
                            review=spec.get("review") if last else None)
        p = os.path.join(out, f"slide_{i:02d}.jpg")
        im.save(p, "JPEG", quality=92)
        paths.append(p)
    return paths


# ---------------- reel ----------------

_kokoro = None


def tts(text, path, voice="hf_alpha", lang="hi", speed=1.05):
    global _kokoro
    import soundfile as sf
    from kokoro_onnx import Kokoro
    if _kokoro is None:
        mdir = os.environ.get("KOKORO_DIR", os.path.join(HERE, "tts"))
        _kokoro = Kokoro(os.path.join(mdir, "kokoro.onnx"), os.path.join(mdir, "voices.bin"))
    samples, sr = _kokoro.create(text, voice=voice, speed=speed, lang=lang)
    sf.write(path, samples, sr)
    return len(samples) / sr


def reel_frame(sc, idx, total, cta=None):
    W, H = 1080, 1920
    SPEC["_idx"] = idx
    # stories / single scenes use the cover surface; reels alternate like carousel slides
    img, ink, soft, dark = background(W, H, idx if total > 1 else 1, max(total, 2))
    sbg = surface(idx if total > 1 else 1, max(total, 2))[0]
    d = ImageDraw.Draw(img)
    M = 80
    acc = T["accent"]
    top = 130 if T["decor"] != "festival" else 230
    paste_logo(img, (W - 400) // 2, top, 400, pill=dark)
    dx = (W - total * 34) // 2
    if total > 1:
        for i in range(total):
            d.rounded_rectangle([dx + i * 34, top + 190, dx + i * 34 + 22, top + 198], radius=4,
                                fill=acc if i < idx else ((70, 90, 120) if dark else (210, 216, 226)))
    text = sc["text"].upper() if T["upper"] else sc["text"]
    ft = F("title", int((88 if len(text) < 45 else 72) * min(T["title_scale"], 1.3)))
    lines = wrap(d, text, ft, W - 2 * M)
    th = len(lines) * int(ft.size * 1.12)
    y = (H - th) // 2 - 90
    if T["kicker"] == "prompt":
        f = F("label", 34)
        t = "$ codeaj --tip"
        d.text(((W - d.textlength(t, font=f)) / 2, y - 80), t, font=f, fill=acc)
    y = draw_lines(d, lines, ft, M, y, ink, gap=1.12, center_w=W - 2 * M) + 20
    if T["decor"] != "frame":
        d.rectangle([(W - 140) // 2, y + 6, (W + 140) // 2, y + 16], fill=acc if acc != ink else T["accent2"])
    y += 50
    if sc.get("sub"):
        fs = F("med", 42)
        subc = T["accent2"] if not dark else (soft if T["name"] != "classic" else (150, 190, 240))
        if T["name"] == "terminal":
            subc = T["accent2"]
        if not dark and sbg is not None and T["mode"](idx if total > 1 else 1, max(total, 2)) == "accent":
            subc = soft
        y = draw_lines(d, wrap(d, sc["sub"], fs, W - 2 * M), fs, M, y, subc, gap=1.3, center_w=W - 2 * M)
    if cta:
        fc = F("label", 54)
        cw = d.textlength(cta, font=fc) + 100
        cy = y + 50
        btn = readable(acc, sbg)
        tcol = (13, 17, 23) if T["name"] == "terminal" else (T["accent2"] if btn == WHITE else WHITE)
        if T["name"] == "minimal":
            btn, tcol = ORANGE, WHITE
        d.rounded_rectangle([(W - cw) / 2, cy, (W + cw) / 2, cy + 112], radius=56, fill=btn)
        d.text(((W - cw) / 2 + 50, cy + 22), cta, font=fc, fill=tcol)
    bw, bh = trust_badge(Image.new("RGBA", (10, 10)), 0, 0, 1.25)
    trust_badge(img, (W - bw) // 2, H - 440, 1.25)
    fs = F("label", 36)
    lc = link_color(sbg)
    d.text(((W - d.textlength(SITE, font=fs)) / 2, H - 340), SITE, font=fs, fill=lc)
    return img.convert("RGB")


def make_reel(spec, out):
    scenes = spec["scenes"]
    n = len(scenes)
    voice = spec.get("voice", "bf_emma")
    lang = "hi" if voice.startswith("h") else ("en-gb" if voice.startswith("b") else "en-us")
    clips = []
    for i, sc in enumerate(scenes, 1):
        last = i == n
        fr = reel_frame(sc, i, n, cta=spec.get("cta") if last else None)
        fp = os.path.join(out, f"scene_{i:02d}.png"); fr.save(fp)
        ap = os.path.join(out, f"vo_{i:02d}.wav")
        dur = tts(sc["vo"], ap, voice=voice, lang=lang) + 0.35
        cp = os.path.join(out, f"clip_{i:02d}.mp4")
        frames = int(dur * 30) + 1
        # slow zoom-in + fade, audio padded to scene length
        vf = (f"scale=1188:2112,zoompan=z='min(zoom+0.0006,1.06)':x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
              f":d={frames}:s=1080x1920:fps=30,fade=t=in:st=0:d=0.25,format=yuv420p")
        subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-loop", "1", "-i", fp, "-i", ap,
                        "-vf", vf, "-af", f"apad=whole_dur={dur:.2f}", "-t", f"{dur:.2f}",
                        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-r", "30",
                        "-c:a", "aac", "-b:a", "160k", "-ar", "44100", cp], check=True)
        clips.append(cp)
    lst = os.path.join(out, "list.txt")
    with open(lst, "w") as f:
        f.writelines(f"file '{c}'\n" for c in clips)
    final = os.path.join(out, "reel.mp4")
    subprocess.run(["ffmpeg", "-loglevel", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst,
                    "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-c:a", "aac", "-b:a", "160k",
                    "-movflags", "+faststart", final], check=True)
    # cover = first scene as JPEG
    Image.open(os.path.join(out, "scene_01.png")).convert("RGB").save(os.path.join(out, "cover.jpg"), quality=92)
    for p in clips + [lst] + [os.path.join(out, f) for f in os.listdir(out) if f.startswith(("vo_", "scene_"))]:
        if os.path.exists(p):
            os.remove(p)
    return [final, os.path.join(out, "cover.jpg")]




def main():
    if len(sys.argv) > 1 and sys.argv[1] == "--styles":
        for k, v in STYLES.items():
            print(f"{k:10s} {v['desc']}")
        return
    spec = json.load(open(sys.argv[1]))
    SPEC.clear(); SPEC.update(spec)
    style = spec.get("style", "classic")
    set_style(style)
    out = os.path.abspath(sys.argv[2])
    os.makedirs(out, exist_ok=True)
    if spec["type"] == "carousel":
        files = make_carousel(spec, out)
    elif spec["type"] == "story":
        sc = spec["scenes"][0]
        p = os.path.join(out, "story.jpg")
        reel_frame(sc, 1, 1, cta=spec.get("cta")).save(p, "JPEG", quality=92)
        files = [p]
    else:
        files = make_reel(spec, out)
    json.dump(spec, open(os.path.join(out, "spec.json"), "w"), ensure_ascii=False, indent=2)
    print("\n".join(files))


if __name__ == "__main__":
    main()
