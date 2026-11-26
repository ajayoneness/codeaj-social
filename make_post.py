#!/usr/bin/env python3
"""CodeAj Marketplace Instagram post generator.

Usage:
  python3 make_post.py spec.json OUT_DIR

spec.json:
{
  "type": "carousel" | "reel",
  "slug": "2026-11-27-ai-project-ideas",
  "caption": "...",                      # used later for posting
  "slides": [                             # carousel: 4-10 slides
     {"kicker": "Final year 2026", "title": "...", "body": "...", "points": ["...", "..."]}
  ],
  "scenes": [                             # reel: 4-8 scenes
     {"text": "On-screen text", "sub": "small line (optional)", "vo": "Devanagari Hinglish voiceover"}
  ],
  "cta": "Comment DEMO",                  # last slide / last scene
  "review": {"name": "Ganesh Sawant", "text": "..."}   # optional, real Google review only
}
"""
import json, os, subprocess, sys, textwrap
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(HERE, "assets")

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

FONT_DIR = "/usr/share/fonts/truetype/google-fonts"


def font(weight, size):
    names = {"bold": "Poppins-Bold.ttf", "semi": "Poppins-SemiBold.ttf",
             "med": "Poppins-Medium.ttf", "reg": "Poppins-Regular.ttf",
             "black": "Poppins-ExtraBold.ttf"}
    for n in (names[weight], "Poppins-Bold.ttf"):
        p = os.path.join(FONT_DIR, n)
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default(size)


def mono(size):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",):
        if os.path.exists(p):
            return ImageFont.truetype(p, size)
    return ImageFont.load_default(size)


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
    import math
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
    bg = WHITE if not dark else (255, 255, 255)
    d.rounded_rectangle([x, y, x + w, y + h], radius=h // 2, fill=bg, outline=(225, 230, 238), width=2)
    # G mark
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


def background(W, H, dark=False):
    img = Image.new("RGBA", (W, H), (NAVY_DARK if dark else CREAM) + (255,))
    d = ImageDraw.Draw(img)
    # soft brand shapes
    glow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    g = ImageDraw.Draw(glow)
    g.ellipse([W * 0.55, -H * 0.15, W * 1.35, H * 0.45], fill=BLUE + ((120 if dark else 38),))
    g.ellipse([-W * 0.4, H * 0.7, W * 0.45, H * 1.25], fill=ORANGE + ((70 if dark else 30),))
    glow = glow.filter(ImageFilter.GaussianBlur(60))
    img.alpha_composite(glow)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 10], fill=NAVY)
    d.rectangle([0, 10, int(W * 0.3), 16], fill=ORANGE)
    return img


# ---------------- carousel ----------------

def carousel_slide(s, idx, total, cta=None, review=None):
    W, H = 1080, 1350
    dark = idx == 1
    img = background(W, H, dark=dark)
    d = ImageDraw.Draw(img)
    M = 80
    ink = WHITE if dark else NAVY_DARK
    soft = (200, 212, 228) if dark else GREY
    paste_logo(img, M, 56, 300, pill=dark)
    d.text((W - M - 70, 70), f"{idx}/{total}", font=font("semi", 30), fill=soft)

    is_last = cta is not None
    # measure content height first so it can be vertically centered
    def layout(dd, y0, draw_it):
        y = y0
        if s.get("kicker"):
            f = font("semi", 30)
            tw = dd.textlength(s["kicker"].upper(), font=f)
            if draw_it:
                dd.rounded_rectangle([M, y, M + tw + 40, y + 56], radius=28, fill=ORANGE)
                dd.text((M + 20, y + 9), s["kicker"].upper(), font=f, fill=WHITE)
            y += 92
        ft = font("bold", 84 if idx == 1 else 62)
        lines = wrap(dd, s.get("title", ""), ft, W - 2 * M)
        if draw_it:
            y = draw_lines(dd, lines, ft, M, y, ink, gap=1.12)
        else:
            y += len(lines) * int(ft.size * 1.12)
        if idx == 1:
            if draw_it:
                dd.rectangle([M, y + 18, M + 140, y + 28], fill=ORANGE)
            y += 50
        else:
            y += 24
        if s.get("body"):
            fb = font("reg", 36)
            bl = wrap(dd, s["body"], fb, W - 2 * M)
            if draw_it:
                y = draw_lines(dd, bl, fb, M, y, soft, gap=1.4)
            else:
                y += len(bl) * int(36 * 1.4)
            y += 20
        if s.get("code"):
            fm = mono(30)
            cl = s["code"].split("\n")[:14]
            chh = 70 + len(cl) * 42 + 30
            if draw_it:
                dd.rounded_rectangle([M, y, W - M, y + chh], radius=22, fill=(15, 23, 42))
                for k, col in enumerate([(255, 95, 86), (255, 189, 46), (39, 201, 63)]):
                    dd.ellipse([M + 28 + k * 30, y + 26, M + 46 + k * 30, y + 44], fill=col)
                yy = y + 70
                for ln in cl:
                    dd.text((M + 34, yy), ln, font=fm, fill=(226, 232, 240))
                    yy += 42
            y += chh + 24
        for k, p in enumerate(s.get("options", [])):
            fp = font("med", 36)
            pl = wrap(dd, p, fp, W - 2 * M - 110)
            ph = len(pl) * int(36 * 1.3) + 40
            if draw_it:
                dd.rounded_rectangle([M, y, W - M, y + ph], radius=22, fill=WHITE, outline=(226, 232, 240), width=2)
                dd.ellipse([M + 22, y + ph / 2 - 24, M + 70, y + ph / 2 + 24], fill=NAVY)
                L = "ABCD"[k]
                fl = font("bold", 28)
                dd.text((M + 46 - dd.textlength(L, font=fl) / 2, y + ph / 2 - 19), L, font=fl, fill=WHITE)
                draw_lines(dd, pl, fp, M + 92, y + 18, NAVY_DARK, gap=1.3)
            y += ph + 16
        for p in s.get("points", []):
            fp = font("med", 38)
            pl = wrap(dd, p, fp, W - 2 * M - 110)
            ph = len(pl) * int(38 * 1.3) + 44
            if draw_it:
                dd.rounded_rectangle([M, y, W - M, y + ph], radius=22, fill=WHITE, outline=(226, 232, 240), width=2)
                dd.rounded_rectangle([M + 26, y + 26, M + 66, y + 66], radius=10, fill=BLUE)
                dd.line([M + 35, y + 46, M + 43, y + 55, M + 57, y + 37], fill=WHITE, width=5)
                draw_lines(dd, pl, fp, M + 92, y + 20, NAVY_DARK, gap=1.3)
            y += ph + 18
        return y

    top, bottom = 230, (H - 470 if is_last else H - 200)
    h = layout(d, 0, False)
    y0 = top + max(0, (bottom - top - h) // 2) if not is_last else 260
    y = layout(d, y0, True)

    if is_last:
        if review and review.get("text"):
            box_y = max(y + 10, H - 560)
            fr = font("reg", 29)
            lines = wrap(d, "\u201c" + review["text"] + "\u201d", fr, W - 2 * M - 60)[:3]
            bh = 70 + len(lines) * 38 + 50
            d.rounded_rectangle([M, box_y, W - M, box_y + bh], radius=26, fill=WHITE, outline=(225, 230, 238), width=2)
            sx = M + 30
            for i in range(5):
                star(d, sx + 14, box_y + 36, 14, GOLD_STAR); sx += 34
            yy = draw_lines(d, lines, fr, M + 30, box_y + 62, NAVY_DARK, gap=1.3)
            d.text((M + 30, yy + 2), "\u2014 " + review.get("name", "") + ", Google review", font=font("semi", 25), fill=GREY)
        fc = font("bold", 44)
        cy = H - 280
        cw = d.textlength(cta, font=fc) + 80
        d.rounded_rectangle([M, cy, M + cw, cy + 92], radius=46, fill=ORANGE)
        d.text((M + 40, cy + 18), cta, font=fc, fill=WHITE)

    trust_badge(img, M, H - 150, 1.0)
    fs = font("semi", 30)
    if is_last:
        d.text((W - M - d.textlength(SITE, font=fs), H - 135), SITE, font=fs, fill=BLUE)
    else:
        t = "Swipe"
        tw = d.textlength(t, font=fs)
        d.text((W - M - tw - 60, H - 137), t, font=fs, fill=ORANGE)
        arrow(d, W - M - 48, H - 117, 48, ORANGE)
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
    dark = idx % 2 == 1
    img = background(W, H, dark=dark)
    d = ImageDraw.Draw(img)
    M = 80
    ink = WHITE if dark else NAVY_DARK
    paste_logo(img, (W - 400) // 2, 130, 400, pill=dark)
    dx = (W - total * 34) // 2
    for i in range(total):
        d.rounded_rectangle([dx + i * 34, 320, dx + i * 34 + 22, 328], radius=4,
                            fill=ORANGE if i < idx else ((70, 90, 120) if dark else (210, 216, 226)))
    ft = font("bold", 88 if len(sc["text"]) < 45 else 72)
    lines = wrap(d, sc["text"], ft, W - 2 * M)
    th = len(lines) * int(ft.size * 1.12)
    y = (H - th) // 2 - 90
    y = draw_lines(d, lines, ft, M, y, ink, gap=1.12, center_w=W - 2 * M) + 20
    d.rectangle([(W - 140) // 2, y + 6, (W + 140) // 2, y + 16], fill=ORANGE)
    y += 50
    if sc.get("sub"):
        fs = font("med", 42)
        y = draw_lines(d, wrap(d, sc["sub"], fs, W - 2 * M), fs, M, y,
                       (150, 190, 240) if dark else BLUE, gap=1.3, center_w=W - 2 * M)
    if cta:
        fc = font("bold", 54)
        cw = d.textlength(cta, font=fc) + 100
        cy = y + 50
        d.rounded_rectangle([(W - cw) / 2, cy, (W + cw) / 2, cy + 112], radius=56, fill=ORANGE)
        d.text(((W - cw) / 2 + 50, cy + 22), cta, font=fc, fill=WHITE)
    bw, bh = trust_badge(Image.new("RGBA", (10, 10)), 0, 0, 1.25)
    trust_badge(img, (W - bw) // 2, H - 440, 1.25)
    fs = font("semi", 36)
    d.text(((W - d.textlength(SITE, font=fs)) / 2, H - 340), SITE, font=fs, fill=ORANGE)
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
    spec = json.load(open(sys.argv[1]))
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
