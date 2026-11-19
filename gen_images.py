"""يولّد صورة لكل لعبة داخل مجلد images/  (الصور جاهزة، تشغيله اختياري)
يحتاج Pillow مع raqm لعرض العربي بشكل صحيح."""
import os
import math
import random
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance

DIR = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(DIR, "images")
BANNER = os.path.join(DIR, "bloomy_banner.jpg")
os.makedirs(OUT, exist_ok=True)

W, H = 800, 450
WHITE = (245, 245, 250)
DARK = (22, 22, 28)
GOLD = (255, 205, 40)


def font(size):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "DejaVuSans-Bold.ttf", "arialbd.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            continue
    return ImageFont.load_default()


def background(seed, accent):
    rnd = random.Random(seed)
    b = Image.open(BANNER).convert("RGB")
    bw, bh = b.size
    cw = int(bw * rnd.uniform(0.35, 0.6))
    ch = int(cw * H / W)
    x, y = rnd.randint(0, bw - cw), rnd.randint(0, bh - ch)
    img = b.crop((x, y, x + cw, y + ch)).resize((W, H), Image.LANCZOS).filter(ImageFilter.GaussianBlur(3))
    img = ImageEnhance.Brightness(img).enhance(0.45)
    return Image.blend(img, Image.new("RGB", (W, H), accent), 0.28)


def rot(pts, ang, cx, cy):
    a = math.radians(ang)
    return [(cx + x * math.cos(a) - y * math.sin(a), cy + x * math.sin(a) + y * math.cos(a)) for x, y in pts]


def arrow(d, cx, cy, r, ang, col):
    a = math.radians(ang)
    px, py = cx + r * math.cos(a), cy + r * math.sin(a)
    tx, ty = -math.sin(a), math.cos(a)
    nx, ny = math.cos(a), math.sin(a)
    d.polygon([(px + tx * 34, py + ty * 34), (px + nx * 24, py + ny * 24), (px - nx * 24, py - ny * 24)], fill=col)


def X(d, x, y, s, col, w=12):
    d.line((x - s, y - s, x + s, y + s), fill=col, width=w)
    d.line((x - s, y + s, x + s, y - s), fill=col, width=w)


def O(d, x, y, s, col, w=12):
    d.ellipse((x - s, y - s, x + s, y + s), outline=col, width=w)


# ------------------------------------------------------------------ icons
def roulette(d, cx, cy, c):
    r = 105
    for k in range(8):
        d.pieslice((cx - r, cy - r, cx + r, cy + r), k * 45 - 90, (k + 1) * 45 - 90, fill=c if k % 2 else WHITE)
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=DARK, width=6)
    d.ellipse((cx - 22, cy - 22, cx + 22, cy + 22), fill=DARK)
    d.polygon([(cx - 15, cy - r - 20), (cx + 15, cy - r - 20), (cx, cy - r + 12)], fill=GOLD)


def xo(d, cx, cy, c):
    s = 100
    for t in (-s / 3, s / 3):
        d.line((cx + t, cy - s, cx + t, cy + s), fill=WHITE, width=8)
        d.line((cx - s, cy + t, cx + s, cy + t), fill=WHITE, width=8)
    X(d, cx - 67, cy - 67, 20, c, 10)
    O(d, cx, cy, 22, WHITE, 10)
    X(d, cx + 67, cy + 67, 20, c, 10)
    O(d, cx + 67, cy - 67, 20, WHITE, 10)


def mafia(d, cx, cy, c):
    d.rounded_rectangle((cx - 70, cy - 80, cx + 70, cy + 25), 20, fill=(35, 35, 42), outline=WHITE, width=5)
    d.rectangle((cx - 68, cy - 8, cx + 68, cy + 18), fill=c)
    d.ellipse((cx - 125, cy + 5, cx + 125, cy + 58), fill=WHITE)


def chairs(d, cx, cy, c):
    d.rounded_rectangle((cx - 45, cy - 100, cx + 45, cy - 5), 12, outline=WHITE, width=9)
    d.rounded_rectangle((cx - 62, cy, cx + 62, cy + 30), 9, fill=c)
    d.line((cx - 50, cy + 30, cx - 62, cy + 98), fill=WHITE, width=10)
    d.line((cx + 50, cy + 30, cx + 62, cy + 98), fill=WHITE, width=10)


def rps(d, cx, cy, c):
    d.ellipse((cx - 130, cy - 40, cx - 50, cy + 40), fill=WHITE)
    d.rounded_rectangle((cx - 38, cy - 55, cx + 38, cy + 55), 8, fill=c)
    d.line((cx + 65, cy - 50, cx + 125, cy + 30), fill=WHITE, width=11)
    d.line((cx + 125, cy - 50, cx + 65, cy + 30), fill=WHITE, width=11)
    d.ellipse((cx + 52, cy + 28, cx + 80, cy + 56), outline=c, width=8)
    d.ellipse((cx + 110, cy + 28, cx + 138, cy + 56), outline=c, width=8)


def dice(d, cx, cy, c):
    d.rounded_rectangle((cx - 90, cy - 90, cx + 90, cy + 90), 30, fill=WHITE)
    for px, py in ((-45, -45), (45, -45), (0, 0), (-45, 45), (45, 45)):
        d.ellipse((cx + px - 15, cy + py - 15, cx + px + 15, cy + py + 15), fill=c)


def wheel(d, cx, cy, c):
    r = 100
    d.ellipse((cx - r, cy - r, cx + r, cy + r), outline=WHITE, width=12)
    for k in range(8):
        a = k * math.pi / 4
        d.line((cx, cy, cx + r * math.cos(a), cy + r * math.sin(a)), fill=c, width=7)
        bx, by = cx + (r + 2) * math.cos(a + math.pi / 8), cy + (r + 2) * math.sin(a + math.pi / 8)
        d.ellipse((bx - 8, by - 8, bx + 8, by + 8), fill=GOLD)
    d.ellipse((cx - 24, cy - 24, cx + 24, cy + 24), fill=c, outline=WHITE, width=5)
    d.polygon([(cx - 14, cy - r - 24), (cx + 14, cy - r - 24), (cx, cy - r + 6)], fill=WHITE)


def hotxo(d, cx, cy, c):
    d.polygon([(cx, cy - 105), (cx + 34, cy - 45), (cx + 17, cy - 50), (cx + 40, cy - 5), (cx - 40, cy - 5),
               (cx - 17, cy - 50), (cx - 34, cy - 45)], fill=(255, 110, 20))
    d.polygon([(cx, cy - 65), (cx + 16, cy - 30), (cx + 20, cy - 5), (cx - 20, cy - 5), (cx - 16, cy - 30)], fill=GOLD)
    X(d, cx - 75, cy + 60, 28, c, 14)
    O(d, cx + 75, cy + 60, 30, WHITE, 14)


def hide(d, cx, cy, c):
    d.ellipse((cx - 125, cy - 62, cx + 125, cy + 62), outline=WHITE, width=10)
    d.ellipse((cx - 46, cy - 46, cx + 46, cy + 46), fill=c)
    d.ellipse((cx - 20, cy - 20, cx + 20, cy + 20), fill=DARK)
    d.ellipse((cx + 8, cy - 32, cx + 24, cy - 16), fill=WHITE)


def replica(d, cx, cy, c):
    d.rounded_rectangle((cx - 90, cy - 90, cx + 25, cy + 25), 16, outline=WHITE, width=9)
    d.rounded_rectangle((cx - 25, cy - 25, cx + 90, cy + 90), 16, fill=c, outline=WHITE, width=9)


def guess(d, cx, cy, c):
    d.ellipse((cx - 100, cy - 100, cx + 100, cy + 100), outline=WHITE, width=10)
    d.text((cx, cy + 4), "?", font=font(170), fill=c, anchor="mm")


def draw(d, cx, cy, c):
    body = [(-75, -22), (55, -22), (55, 22), (-75, 22)]
    tip = [(55, -22), (108, 0), (55, 22)]
    lead = [(88, -8), (108, 0), (88, 8)]
    erase = [(-98, -22), (-75, -22), (-75, 22), (-98, 22)]
    for pts, col in ((body, c), (tip, (240, 200, 150)), (lead, DARK), (erase, (255, 130, 160))):
        d.polygon(rot(pts, -45, cx, cy), fill=col)


def word(d, cx, cy, c):
    d.rounded_rectangle((cx - 120, cy - 80, cx + 120, cy + 80), 24, outline=WHITE, width=8)
    d.text((cx, cy - 4), "أبت", font=font(120), fill=c, anchor="mm")


def button(d, cx, cy, c):
    d.ellipse((cx - 105, cy - 105, cx + 105, cy + 105), fill=(45, 45, 54), outline=WHITE, width=8)
    d.ellipse((cx - 78, cy - 78, cx + 78, cy + 78), fill=c)
    d.ellipse((cx - 50, cy - 60, cx + 10, cy - 20), fill=tuple(min(255, v + 70) for v in c))


def fast(d, cx, cy, c):
    d.polygon([(cx + 15, cy - 115), (cx - 62, cy + 10), (cx - 5, cy + 10), (cx - 28, cy + 115),
               (cx + 68, cy - 30), (cx + 10, cy - 30)], fill=GOLD, outline=WHITE)


def fakk(d, cx, cy, c):
    zz = [(0, -60), (16, -25), (-10, 5), (10, 35), (0, 60)]
    d.polygon([(cx - 120, cy - 60)] + [(cx + x - 12, cy + y) for x, y in zz] + [(cx - 120, cy + 60)], fill=WHITE)
    d.polygon([(cx + x + 12, cy + y) for x, y in zz] + [(cx + 120, cy + 60), (cx + 120, cy - 60)], fill=c)


def dmj(d, cx, cy, c):
    d.rounded_rectangle((cx - 130, cy - 50, cx - 40, cy + 50), 14, fill=WHITE)
    d.rounded_rectangle((cx + 40, cy - 50, cx + 130, cy + 50), 14, fill=c)
    d.line((cx - 20, cy, cx + 20, cy), fill=WHITE, width=14)
    d.line((cx, cy - 20, cx, cy + 20), fill=WHITE, width=14)


def flags(d, cx, cy, c):
    d.line((cx - 80, cy - 105, cx - 80, cy + 105), fill=WHITE, width=11)
    for k, col in enumerate((c, WHITE, (40, 40, 52))):
        d.rectangle((cx - 74, cy - 100 + k * 38, cx + 100, cy - 62 + k * 38), fill=col)


def reverse(d, cx, cy, c):
    r = 78
    d.arc((cx - r, cy - r, cx + r, cy + r), 200, 335, fill=WHITE, width=16)
    arrow(d, cx, cy, r, 335, WHITE)
    d.arc((cx - r, cy - r, cx + r, cy + r), 20, 155, fill=c, width=16)
    arrow(d, cx, cy, r, 155, c)


def harf(d, cx, cy, c):
    d.rounded_rectangle((cx - 95, cy - 100, cx + 95, cy + 100), 28, outline=WHITE, width=9)
    d.text((cx, cy - 8), "ح", font=font(190), fill=c, anchor="mm")


def fix(d, cx, cy, c):
    d.ellipse((cx - 105, cy - 105, cx + 105, cy + 105), fill=c)
    d.line([(cx - 52, cy + 2), (cx - 12, cy + 44), (cx + 56, cy - 38)], fill=WHITE, width=20, joint="curve")


def order(d, cx, cy, c):
    for k, (h, col) in enumerate(((60, WHITE), (110, c), (160, GOLD))):
        x = cx - 90 + k * 90
        d.rounded_rectangle((x - 30, cy + 95 - h, x + 30, cy + 95), 8, fill=col)
        d.text((x, cy + 95 - h - 22), str(k + 1), font=font(34), fill=WHITE, anchor="mm")


def colors(d, cx, cy, c):
    pal = [(235, 64, 52), (241, 196, 15), (46, 204, 113), (52, 152, 219), (155, 89, 182), (230, 126, 34)]
    for k, col in enumerate(pal):
        a = k * math.pi / 3 - math.pi / 2
        x, y = cx + 68 * math.cos(a), cy + 68 * math.sin(a)
        d.ellipse((x - 40, y - 40, x + 40, y + 40), fill=col, outline=WHITE, width=4)


def emoji(d, cx, cy, c):
    d.ellipse((cx - 102, cy - 102, cx + 102, cy + 102), fill=(255, 205, 60), outline=WHITE, width=6)
    d.ellipse((cx - 50, cy - 45, cx - 20, cy + 0), fill=DARK)
    d.ellipse((cx + 20, cy - 45, cx + 50, cy + 0), fill=DARK)
    d.arc((cx - 60, cy - 35, cx + 60, cy + 65), 20, 160, fill=DARK, width=11)


def spot(d, cx, cy, c):
    lx, ly, r = cx - 20, cy - 20, 75
    d.line((lx + r * 0.7, ly + r * 0.7, cx + 100, cy + 100), fill=c, width=24)
    d.ellipse((lx - r, ly - r, lx + r, ly + r), fill=(30, 30, 38), outline=WHITE, width=14)
    for px, py, col in ((-30, -25, WHITE), (25, -30, WHITE), (-25, 28, WHITE), (30, 25, c)):
        d.ellipse((lx + px - 13, ly + py - 13, lx + px + 13, ly + py + 13), fill=col)


# slug, عنوان, لون, أيقونة
GAMES = [
    ("roulette", "روليت", (231, 76, 60), roulette),
    ("xo", "XO", (52, 152, 219), xo),
    ("mafia", "مافيا", (192, 57, 43), mafia),
    ("chairs", "كراسي", (230, 126, 34), chairs),
    ("rps", "حجرة ورقة مقص", (26, 188, 156), rps),
    ("dice", "نرد", (155, 89, 182), dice),
    ("wheel", "عجلة الحظ", (241, 196, 15), wheel),
    ("hotxo", "HotXO", (255, 110, 20), hotxo),
    ("hide", "غميضة", (52, 73, 94), hide),
    ("replica", "ريبلكا", (46, 204, 113), replica),
    ("guess", "خمّن الرقم", (52, 152, 219), guess),
    ("draw", "رسمة", (233, 30, 99), draw),
    ("word", "كلمة", (0, 188, 212), word),
    ("button", "زر", (231, 76, 60), button),
    ("fast", "اسرع", (255, 193, 7), fast),
    ("fakk", "فكّك", (96, 125, 139), fakk),
    ("dmj", "ادمج", (76, 175, 80), dmj),
    ("flags", "أعلام", (244, 67, 54), flags),
    ("reverse", "اعكس", (103, 58, 183), reverse),
    ("harf", "حرف", (255, 87, 34), harf),
    ("fix", "صحّح", (39, 174, 96), fix),
    ("order", "ترتيب", (63, 81, 181), order),
    ("colors", "ألوان", (233, 30, 99), colors),
    ("emoji", "إيموجي", (255, 193, 7), emoji),
    ("spot", "اكتشف", (0, 150, 136), spot),
]


def make(i, slug, title, accent, fn):
    img = background(i, accent)
    d = ImageDraw.Draw(img)
    fn(d, W // 2, 185, accent)
    d.rectangle((0, H - 10, W, H), fill=accent)
    d.text((W // 2, 385), title, font=font(66), fill=WHITE, anchor="mm", stroke_width=4, stroke_fill=DARK)
    d.text((W - 18, H - 24), "discord.gg/bloomy", font=font(18), fill=(210, 210, 220), anchor="rb")
    img.save(os.path.join(OUT, f"{slug}.png"))
    return img


def preview(imgs):
    tw, th = 320, 180
    sheet = Image.new("RGB", (5 * tw + 6 * 10, 5 * th + 6 * 10), (14, 14, 18))
    for k, im in enumerate(imgs):
        sheet.paste(im.resize((tw, th), Image.LANCZOS), (10 + (k % 5) * (tw + 10), 10 + (k // 5) * (th + 10)))
    sheet.save(os.path.join(DIR, "games_preview.png"))


if __name__ == "__main__":
    ims = [make(i, *g) for i, g in enumerate(GAMES)]
    preview(ims)
    print(f"done: {len(ims)} images")
