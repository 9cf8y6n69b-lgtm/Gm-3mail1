import os
import html
import base64
import hmac
from urllib.parse import quote

from aiohttp import web
from PIL import Image, ImageOps

from common import DB, GAMES, CUSTOM_DIR, game_image

DEFAULT_LOBBY = {"roulette": 60, "mafia": 60, "mine": 30, "chairs": 30, "rps": 10, "hide": 30, "connect": 30, "xo": 30}

CSS = """
body{font-family:system-ui,Segoe UI,Tahoma,sans-serif;background:#14141a;color:#eee;margin:0;padding:16px;direction:rtl}
h1{margin:0 0 12px}h2{margin:24px 0 8px;color:#9ad}
.card{background:#1e1e28;border-radius:14px;padding:14px;margin:10px 0}
.row{display:flex;gap:12px;align-items:center;flex-wrap:wrap}
img{width:160px;height:90px;object-fit:cover;border-radius:8px}
input,button{font:inherit;padding:8px 10px;border-radius:8px;border:1px solid #444;background:#2a2a36;color:#eee}
button{background:#5865f2;border:0;cursor:pointer}button.red{background:#c0392b}
label{display:block;margin:6px 0}small{color:#9a9}
"""


def Q(t):
    return quote(t)


def authed(request):
    pw = os.getenv("DASH_PASSWORD")
    if not pw:
        return False
    h = request.headers.get("Authorization", "")
    if not h.startswith("Basic "):
        return False
    try:
        _, _, p = base64.b64decode(h[6:]).decode().partition(":")
    except Exception:
        return False
    return hmac.compare_digest(p, pw)


def deny():
    if not os.getenv("DASH_PASSWORD"):
        return web.Response(text="حط متغير DASH_PASSWORD في إعدادات الاستضافة عشان تفتح الداشبورد.", status=503)
    return web.Response(status=401, headers={"WWW-Authenticate": 'Basic realm="Bloomy Dashboard"'}, text="Unauthorized")


async def index(request):
    return web.Response(text="Bloomy bot is running ✅")


async def page(request):
    if not authed(request):
        return deny()
    s = DB.settings
    note = html.escape(request.query.get("msg", ""))
    rows = []
    for name, info in GAMES.items():
        slug = info["slug"]
        cur = s["timeouts"].get(slug, info["t"])
        lobby_field = ""
        if slug in DEFAULT_LOBBY:
            lv = s["lobby"].get(slug, DEFAULT_LOBBY[slug])
            lobby_field = f'<label>⏳ وقت اللوبي (ثواني) <input form="main" type="number" min="5" max="300" name="l_{slug}" value="{lv}"></label>'
        rows.append(f"""
<div class="card"><div class="row">
<img src="/img/{slug}?v={os.path.getmtime(game_image(slug)):.0f}">
<div style="flex:1"><b>{html.escape(info['title'])}</b> <small>({html.escape(name)})</small>
<label>⏱️ الوقت (ثواني) <input form="main" type="number" min="5" max="600" name="t_{slug}" value="{cur}"></label>{lobby_field}</div>
<form method="post" action="/dashboard/upload" enctype="multipart/form-data">
<input type="hidden" name="slug" value="{slug}">
<input type="file" name="file" accept="image/*" required>
<button>رفع صورة</button></form>
<form method="post" action="/dashboard/reset"><input type="hidden" name="slug" value="{slug}"><button class="red">حذف المخصصة</button></form>
</div></div>""")
    body = f"""<!doctype html><html lang="ar"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Bloomy Dashboard</title><style>{CSS}</style></head><body>
<h1>🎮 لوحة تحكم Bloomy</h1>{f'<div class="card">✅ {note}</div>' if note else ''}
<form id="main" method="post" action="/dashboard/save">
<div class="card"><h2>⚙️ إعدادات عامة</h2>
<label>💬 وقت النقاش في المافيا (ثواني) <input type="number" min="10" max="600" name="discussion" value="{s['discussion']}"></label>
<label>🪙 مكافأة اليومي (عملات) <input type="number" min="1" max="1000" name="daily" value="{s['daily']}"></label>
<label><input type="checkbox" name="ping_here" {'checked' if s.get('ping_here', True) else ''}> منشن @here عند فتح لوبي</label>
<label><input type="checkbox" name="afk_kick" {'checked' if s['afk_kick'] else ''}> طرد اللاعب اللي ما يتفاعل من اللعبة</label>
<button>💾 حفظ الإعدادات والأوقات</button></div></form>
<h2>🖼️ الألعاب (الوقت + الصورة)</h2>{''.join(rows)}
<small>الصور المرفوعة تُحفظ في images/custom — على الاستضافة المجانية قد تنمسح عند إعادة النشر.</small>
</body></html>"""
    return web.Response(text=body, content_type="text/html")


async def save(request):
    if not authed(request):
        return deny()
    f = await request.post()
    s = DB.settings
    try:
        s["discussion"] = max(10, min(600, int(f.get("discussion", 60))))
        s["daily"] = max(1, min(1000, int(f.get("daily", 5))))
    except ValueError:
        pass
    s["afk_kick"] = "afk_kick" in f
    s["ping_here"] = "ping_here" in f
    for slug in DEFAULT_LOBBY:
        v = f.get("l_" + slug)
        if v and str(v).isdigit():
            s["lobby"][slug] = max(5, min(300, int(v)))
    for info in GAMES.values():
        v = f.get("t_" + info["slug"])
        if v and str(v).isdigit():
            s["timeouts"][info["slug"]] = max(5, min(600, int(v)))
    DB.save()
    raise web.HTTPFound("/dashboard?msg=" + Q("تم الحفظ"))


async def upload(request):
    if not authed(request):
        return deny()
    f = await request.post()
    slug, file = f.get("slug"), f.get("file")
    if slug not in {i["slug"] for i in GAMES.values()} or not hasattr(file, "file"):
        raise web.HTTPFound("/dashboard?msg=" + Q("ملف غير صالح"))
    try:
        img = ImageOps.fit(Image.open(file.file).convert("RGB"), (800, 450))
        img.save(os.path.join(CUSTOM_DIR, slug + ".png"))
    except Exception:
        raise web.HTTPFound("/dashboard?msg=" + Q("الصورة غير صالحة"))
    raise web.HTTPFound("/dashboard?msg=" + Q("تم رفع الصورة"))


async def reset(request):
    if not authed(request):
        return deny()
    f = await request.post()
    p = os.path.join(CUSTOM_DIR, str(f.get("slug", "")).replace("/", "").replace("\\", "") + ".png")
    if os.path.exists(p):
        os.remove(p)
    raise web.HTTPFound("/dashboard?msg=" + Q("رجعت الصورة الأصلية"))


async def img(request):
    slug = request.match_info["slug"]
    if slug not in {i["slug"] for i in GAMES.values()}:
        raise web.HTTPNotFound()
    return web.FileResponse(game_image(slug))


async def start_web():
    app = web.Application(client_max_size=10 * 1024 * 1024)
    app.router.add_get("/", index)
    app.router.add_get("/dashboard", page)
    app.router.add_post("/dashboard/save", save)
    app.router.add_post("/dashboard/upload", upload)
    app.router.add_post("/dashboard/reset", reset)
    app.router.add_get("/img/{slug}", img)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.getenv("PORT", "10000"))
    await web.TCPSite(runner, "0.0.0.0", port).start()
    print(f"WEB SERVER STARTED on port {port}")
