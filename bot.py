import os
import re
import io
import json
import math
import random
import asyncio
import time
import traceback

import discord
from discord import app_commands
from discord.ext import commands
from PIL import Image, ImageDraw, ImageFont, ImageEnhance

TOKEN = os.getenv("DISCORD_TOKEN")
DIR = os.path.dirname(os.path.abspath(__file__))
BANNER = os.path.join(DIR, "bloomy_banner.jpg")
CONFIG = os.path.join(DIR, "config.json")
COLOR = 0x2B2D31

# "guild"   = لعبة وحدة بس شغالة في كل السيرفر
# "channel" = لعبة وحدة في كل روم
LOCK_SCOPE = "guild"
# اكتب اسم اللعبة في الشات (مثل: روليت) لتشغيلها
TEXT_TRIGGERS = True

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


# ================================================================ config
def _load():
    try:
        with open(CONFIG, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


CFG = _load()


def save_cfg():
    with open(CONFIG, "w", encoding="utf-8") as f:
        json.dump(CFG, f, ensure_ascii=False, indent=1)


def gcfg(gid):
    return CFG.setdefault(str(gid), {})


STATES = {
    "online": discord.Status.online,
    "idle": discord.Status.idle,
    "dnd": discord.Status.dnd,
    "invisible": discord.Status.invisible,
}


async def apply_status():
    s = CFG.get("_status", {"text": "Bloomy Games 🎮", "state": "online", "activity": "playing"})
    AT = discord.ActivityType
    kinds = {
        "playing": discord.Game(s["text"]),
        "watching": discord.Activity(type=AT.watching, name=s["text"]),
        "listening": discord.Activity(type=AT.listening, name=s["text"]),
        "competing": discord.Activity(type=AT.competing, name=s["text"]),
    }
    await bot.change_presence(status=STATES[s["state"]], activity=kinds[s["activity"]])


def can_start(m: discord.Member):
    p = m.guild_permissions
    if p.administrator or p.manage_guild:
        return True
    rid = gcfg(m.guild.id).get("role")
    return rid is None or any(r.id == rid for r in m.roles)


# ================================================================ helpers
IMG_DIR = os.path.join(DIR, "images")
SLUG = {
    "روليت": "roulette", "xo": "xo", "مافيا": "mafia", "كراسي": "chairs", "حجرة": "rps", "نرد": "dice",
    "عجلة": "wheel", "hotxo": "hotxo", "غميضة": "hide", "ريبلكا": "replica", "خمن": "guess", "رسمة": "draw",
    "كلمة": "word", "زر": "button", "اسرع": "fast", "فكك": "fakk", "ادمج": "dmj", "اعلام": "flags",
    "اعكس": "reverse", "حرف": "harf", "صحح": "fix", "ترتيب": "order", "الوان": "colors",
    "ايموجي": "emoji", "اكتشف": "spot",
}


def banner_file():
    return discord.File(BANNER, filename="banner.jpg")


def game_image(name):
    p = os.path.join(IMG_DIR, SLUG.get(name, "") + ".png")
    return p if os.path.exists(p) else BANNER


def gfile(g):
    """صورة اللعبة (تُرسل باسم banner.jpg عشان تشتغل مع كل الـembeds)"""
    return discord.File(game_image(g.name), filename="banner.jpg")


def mk(title, desc="", big=False):
    e = discord.Embed(title=title, description=desc, color=COLOR)
    if big:
        e.set_image(url="attachment://banner.jpg")
    else:
        e.set_thumbnail(url="attachment://banner.jpg")
    e.set_footer(text="discord.gg/bloomy")
    return e


_TASHKEEL = re.compile("[\u064B-\u0652\u0640\u200b]")


def norm(s):
    s = _TASHKEEL.sub("", s)
    s = re.sub("[أإآ]", "ا", s).replace("ة", "ه").replace("ى", "ي")
    return " ".join(s.lower().split())


class Replay(discord.ui.View):
    def __init__(self, name):
        super().__init__(timeout=90)
        self.name, self.msg = name, None

    @discord.ui.button(label="العب مرة ثانية", emoji="🔁", style=discord.ButtonStyle.primary)
    async def again(self, i: discord.Interaction, b: discord.ui.Button):
        err = await launch(i.channel, i.user, self.name)
        await i.response.send_message(err or f"🔁 بدأت **{self.name}** من جديد", ephemeral=bool(err))
        if not err:
            self.stop()
            try:
                await self.msg.edit(view=None)
            except discord.HTTPException:
                pass

    async def on_timeout(self):
        try:
            await self.msg.edit(view=None)
        except Exception:
            pass


class Game:
    def __init__(self, name, starter, channel):
        self.name, self.starter, self.channel = name, starter, channel
        self.task = None
        self.views = []
        self.first = True


ACTIVE = {}


def key(ch):
    return ch.guild.id if LOCK_SCOPE == "guild" else ch.id


async def say(g, title, desc="", view=None, file=None):
    big = g.first and file is None
    g.first = False
    e = mk(title, desc, big=big)
    files = [gfile(g)]
    kw = {}
    if file is not None:
        files.append(file)
        e.set_image(url=f"attachment://{file.filename}")
    if view is not None:
        kw["view"] = view
    m = await g.channel.send(embed=e, files=files, **kw)
    if view is not None:
        g.views.append((view, m))
    return m


async def close(m, v):
    for c in v.children:
        c.disabled = True
    v.stop()
    try:
        await m.edit(view=v)
    except discord.HTTPException:
        pass


async def scoreboard(g, scores):
    if not scores:
        return await say(g, "🏁 انتهت اللعبة", "ما أحد جاوب 😅")
    top = sorted(scores.items(), key=lambda x: -x[1])
    medals = ["🥇", "🥈", "🥉"]
    txt = "\n".join(f"{medals[i] if i < 3 else '▫️'} <@{u}> — {s}" for i, (u, s) in enumerate(top))
    card = None
    try:
        gm = g.channel.guild
        mem = gm.get_member(top[0][0]) or await gm.fetch_member(top[0][0])
        av = await mem.display_avatar.replace(size=256, format="png").read()
        buf = await asyncio.to_thread(winner_card, game_image(g.name), av)
        card = discord.File(buf, "winner.png")
    except Exception:
        pass
    await say(g, "🏁 النتائج", f"👑 الفائز: <@{top[0][0]}>\n\n{txt}", file=card)


async def first_answer(g, check_fn, timeout=20):
    def chk(m):
        return m.channel == g.channel and not m.author.bot and check_fn(m.content)

    try:
        return await bot.wait_for("message", check=chk, timeout=timeout)
    except asyncio.TimeoutError:
        return None


# ---------------------------------------------------------------- launch / stop
async def launch(channel, member, name):
    if not getattr(channel, "guild", None):
        return "الألعاب داخل السيرفرات فقط."
    if not can_start(member):
        return "ما عندك الرتبة اللي تشغّل الألعاب 🚫"
    k = key(channel)
    if k in ACTIVE:
        cur = ACTIVE[k]
        return f"فيه لعبة شغالة الحين: **{cur.name}** في {cur.channel.mention}\nلإيقافها اكتب `/stop`"
    g = Game(name, member, channel)
    ACTIVE[k] = g

    async def runner():
        try:
            await GAMES[name](g)
            try:
                rv = Replay(name)
                rv.msg = await channel.send("🔁 تبون جولة ثانية؟", view=rv)
            except Exception:
                pass
        except asyncio.CancelledError:
            pass
        except Exception:
            traceback.print_exc()
            try:
                await channel.send("⚠️ صار خطأ وتم إيقاف اللعبة.")
            except Exception:
                pass
        finally:
            for v, m in g.views:
                v.stop()
                try:
                    if any(not getattr(c, "disabled", True) for c in v.children):
                        for c in v.children:
                            c.disabled = True
                        await m.edit(view=v)
                except Exception:
                    pass
            if ACTIVE.get(k) is g:
                ACTIVE.pop(k, None)

    g.task = asyncio.create_task(runner())
    return None


async def stop_game(channel, member):
    g = ACTIVE.get(key(channel))
    if not g:
        return "ما فيه لعبة شغالة."
    p = member.guild_permissions
    if not (member == g.starter or p.administrator or p.manage_guild or p.manage_messages):
        return "بس اللي شغّل اللعبة أو الإدارة يقدر يوقفها."
    ACTIVE.pop(key(channel), None)
    g.task.cancel()
    return f"⛔ تم إيقاف لعبة **{g.name}**"


# ================================================================ lobby & small views
class Lobby(discord.ui.View):
    def __init__(self, g, title, minp, maxp):
        super().__init__(timeout=None)
        self.g, self.title, self.minp, self.maxp = g, title, minp, maxp
        self.players = [g.starter]
        self.go = asyncio.Event()

    def emb(self):
        names = "\n".join(f"• {p.mention}" for p in self.players)
        return mk(
            self.title,
            f"اضغط **انضم** للمشاركة، والمنظم يضغط **ابدأ**\n"
            f"اللاعبين ({len(self.players)}/{self.maxp}) — الحد الأدنى {self.minp}\n\n{names}",
            big=True,
        )

    @discord.ui.button(label="انضم", emoji="✅", style=discord.ButtonStyle.success)
    async def join(self, i: discord.Interaction, b: discord.ui.Button):
        if i.user in self.players:
            return await i.response.send_message("انت منضم أصلاً 👍", ephemeral=True)
        if len(self.players) >= self.maxp:
            return await i.response.send_message("اللوبي ممتلئ", ephemeral=True)
        self.players.append(i.user)
        await i.response.edit_message(embed=self.emb())
        if len(self.players) >= self.maxp:
            self.go.set()

    @discord.ui.button(label="خروج", emoji="🚪", style=discord.ButtonStyle.secondary)
    async def leave(self, i: discord.Interaction, b: discord.ui.Button):
        if i.user == self.g.starter or i.user not in self.players:
            return await i.response.send_message("ما تقدر تخرج", ephemeral=True)
        self.players.remove(i.user)
        await i.response.edit_message(embed=self.emb())

    @discord.ui.button(label="ابدأ", emoji="▶️", style=discord.ButtonStyle.primary)
    async def start(self, i: discord.Interaction, b: discord.ui.Button):
        if i.user != self.g.starter:
            return await i.response.send_message("المنظم فقط يبدأ", ephemeral=True)
        if len(self.players) < self.minp:
            return await i.response.send_message(f"يلزم {self.minp} لاعبين على الأقل", ephemeral=True)
        await i.response.defer()
        self.go.set()


async def lobby(g, title, minp=2, maxp=20, wait=90):
    v = Lobby(g, title, minp, maxp)
    g.first = False
    m = await g.channel.send(embed=v.emb(), view=v, file=gfile(g))
    g.views.append((v, m))
    try:
        await asyncio.wait_for(v.go.wait(), wait)
    except asyncio.TimeoutError:
        pass
    await close(m, v)
    if len(v.players) < minp:
        await say(g, "❌ ما اكتمل العدد", f"يلزم {minp} لاعبين على الأقل.")
        return None
    return list(v.players)


class OneBtn(discord.ui.View):
    def __init__(self, who, label, emoji):
        super().__init__(timeout=None)
        self.who, self.ev = who, asyncio.Event()
        b = discord.ui.Button(label=label, emoji=emoji, style=discord.ButtonStyle.primary)
        b.callback = self.cb
        self.add_item(b)

    async def cb(self, i: discord.Interaction):
        if i.user != self.who:
            return await i.response.send_message("مو دورك ✋", ephemeral=True)
        await i.response.defer()
        self.ev.set()


async def ask_press(g, text, who, label, emoji, timeout=30):
    v = OneBtn(who, label, emoji)
    m = await say(g, "🎮", text, view=v)
    try:
        await asyncio.wait_for(v.ev.wait(), timeout)
        ok = True
    except asyncio.TimeoutError:
        ok = False
    await close(m, v)
    return ok


# ================================================================ SERVER GAMES
# ---------------------------------------------------------------- XO / HotXO
LINES = [
    [(0, 0), (1, 0), (2, 0)], [(0, 1), (1, 1), (2, 1)], [(0, 2), (1, 2), (2, 2)],
    [(0, 0), (0, 1), (0, 2)], [(1, 0), (1, 1), (1, 2)], [(2, 0), (2, 1), (2, 2)],
    [(0, 0), (1, 1), (2, 2)], [(2, 0), (1, 1), (0, 2)],
]


class Cell(discord.ui.Button):
    def __init__(self, x, y):
        super().__init__(label="\u200b", style=discord.ButtonStyle.secondary, row=y)
        self.pos = (x, y)

    async def callback(self, i: discord.Interaction):
        v: "TTT" = self.view
        t = v.turn
        if i.user != v.p[t]:
            return await i.response.send_message("مو دورك ✋", ephemeral=True)
        if v.hot and len(v.moves[t]) == 3:
            old = v.moves[t].pop(0)
            v.cells.pop(old)
        v.moves[t].append(self.pos)
        v.cells[self.pos] = t
        if any(all(v.cells.get(c) == t for c in L) for L in LINES):
            v.result = t
        elif not v.hot and len(v.cells) == 9:
            v.result = -1
        else:
            v.turn = 1 - t
        v.refresh()
        await i.response.edit_message(embed=v.emb(), view=v)
        if v.result is not None:
            v.ev.set()


class TTT(discord.ui.View):
    def __init__(self, p1, p2, hot):
        super().__init__(timeout=None)
        self.p, self.hot, self.turn = [p1, p2], hot, 0
        self.cells, self.moves, self.result = {}, [[], []], None
        self.ev = asyncio.Event()
        self.btn = {}
        for y in range(3):
            for x in range(3):
                b = Cell(x, y)
                self.btn[(x, y)] = b
                self.add_item(b)

    def refresh(self):
        for pos, b in self.btn.items():
            if pos in self.cells:
                t = self.cells[pos]
                b.label = "X" if t == 0 else "O"
                b.style = discord.ButtonStyle.danger if t == 0 else discord.ButtonStyle.success
                b.disabled = True
            else:
                b.label, b.style, b.disabled = "\u200b", discord.ButtonStyle.secondary, False
        if self.hot:
            for t in (0, 1):
                if len(self.moves[t]) == 3:
                    self.btn[self.moves[t][0]].style = discord.ButtonStyle.secondary  # الأقدم
        if self.result is not None:
            for b in self.btn.values():
                b.disabled = True

    def emb(self):
        p0, p1 = self.p
        if self.result is None:
            st = f"دور: {self.p[self.turn].mention} ({'❌' if self.turn == 0 else '⭕'})"
        elif self.result == -1:
            st = "🤝 تعادل!"
        else:
            st = f"🏆 الفائز: {self.p[self.result].mention}"
        rule = "\n🔥 كل لاعب يبقى له 3 علامات فقط — الأقدم (الرمادية) تختفي!" if self.hot else ""
        return mk("🔥 HotXO" if self.hot else "❌⭕ XO", f"{p0.mention} ❌  🆚  {p1.mention} ⭕\n\n{st}{rule}")


async def g_xo(g, hot=False):
    pl = await lobby(g, "🔥 HotXO" if hot else "❌⭕ XO", 2, 2)
    if not pl:
        return
    random.shuffle(pl)
    v = TTT(pl[0], pl[1], hot)
    m = await g.channel.send(embed=v.emb(), view=v, file=gfile(g))
    g.views.append((v, m))
    try:
        await asyncio.wait_for(v.ev.wait(), 600)
    except asyncio.TimeoutError:
        await say(g, "⏰", "انتهى الوقت.")


# ---------------------------------------------------------------- roulette
async def g_roulette(g):
    pl = await lobby(g, "🎡 روليت — كل جولة تطيّر لاعب", 2, 20)
    if not pl:
        return
    alive, rnd = pl[:], 1
    m = await say(g, "🎡 روليت", "تبدأ اللعبة...")
    await asyncio.sleep(2)
    while len(alive) > 1:
        for _ in range(8):
            await m.edit(embed=mk(f"🎡 الجولة {rnd}", "العجلة تدور...\n# " + random.choice(alive).display_name))
            await asyncio.sleep(0.5)
        out = random.choice(alive)
        alive.remove(out)
        await m.edit(embed=mk(f"🎡 الجولة {rnd}", f"💥 طار {out.mention}!\nالباقين: {len(alive)}"))
        await asyncio.sleep(2.5)
        rnd += 1
    await say(g, "🏆 الفائز", f"{alive[0].mention} آخر واحد باقي!")


# ---------------------------------------------------------------- mafia
AR = {"mafia": "🔪 مافيا", "doctor": "💊 دكتور", "cop": "🕵️ محقق", "citizen": "🙂 مواطن"}


async def g_mafia(g):
    pl = await lobby(g, "🕵️ مافيا", 4, 15, wait=120)
    if not pl:
        return
    random.shuffle(pl)
    n = len(pl)
    nm = max(1, n // 4)
    role = {}
    for i, p in enumerate(pl):
        role[p.id] = "mafia" if i < nm else "doctor" if i == nm else "cop" if i == nm + 1 else "citizen"
    alive = {p.id: p for p in pl}

    # ---- reveal
    rv = discord.ui.View(timeout=None)
    rb = discord.ui.Button(label="اعرف دورك", emoji="🎭", style=discord.ButtonStyle.primary)

    async def reveal(i: discord.Interaction):
        r = role.get(i.user.id)
        if not r:
            return await i.response.send_message("انت مو باللعبة", ephemeral=True)
        extra = ""
        if r == "mafia":
            mates = "، ".join(p.display_name for p in pl if role[p.id] == "mafia" and p.id != i.user.id)
            extra = f"\nزملاؤك: {mates or 'ما عندك'}"
        await i.response.send_message(f"دورك: **{AR[r]}**{extra}", ephemeral=True)

    rb.callback = reveal
    rv.add_item(rb)
    rm = await say(g, "🕵️ مافيا — تم توزيع الأدوار", f"عدد اللاعبين: {n} — المافيا: {nm}\nاضغط الزر لمعرفة دورك (سري).", view=rv)
    await asyncio.sleep(20)
    await close(rm, rv)

    def winner():
        m = sum(role[p] == "mafia" for p in alive)
        c = len(alive) - m
        if m == 0:
            return "citizens"
        if m >= c:
            return "mafia"
        return None

    night = 1
    while True:
        # ---------------- night
        acts = {"mafia": {}, "doctor": None, "cop": None}
        ev = asyncio.Event()

        def check_done():
            mafias = [p for p in alive if role[p] == "mafia"]
            ok = all(x in acts["mafia"] for x in mafias)
            ok = ok and (acts["doctor"] is not None or not any(role[p] == "doctor" for p in alive))
            ok = ok and (acts["cop"] is not None or not any(role[p] == "cop" for p in alive))
            if ok:
                ev.set()

        async def act(i: discord.Interaction, r):
            if i.user.id not in alive or role[i.user.id] != r:
                return await i.response.send_message("هذا مو دورك 😉", ephemeral=True)
            opts = [p for p in alive.values() if not (r == "mafia" and role[p.id] == "mafia")]
            sv = discord.ui.View(timeout=90)
            sel = discord.ui.Select(
                placeholder="اختر...",
                options=[discord.SelectOption(label=p.display_name[:90], value=str(p.id)) for p in opts][:25],
            )

            async def pick(ii: discord.Interaction):
                t = int(sel.values[0])
                if r == "mafia":
                    acts["mafia"][ii.user.id] = t
                else:
                    acts[r] = t
                msg = "✅ تم"
                if r == "cop":
                    msg = f"{alive[t].display_name}: " + ("🔪 مافيا!" if role[t] == "mafia" else "🙂 بريء")
                await ii.response.edit_message(content=msg, view=None)
                check_done()

            sel.callback = pick
            sv.add_item(sel)
            await i.response.send_message("اختر:", view=sv, ephemeral=True)

        def mkcb(r):
            async def cb(i):
                await act(i, r)

            return cb

        nv = discord.ui.View(timeout=None)
        for r, label in (("mafia", "🔪 مافيا"), ("doctor", "💊 دكتور"), ("cop", "🕵️ محقق")):
            bt = discord.ui.Button(label=label, style=discord.ButtonStyle.secondary)
            bt.callback = mkcb(r)
            nv.add_item(bt)
        nm_msg = await say(
            g, f"🌙 الليل {night}",
            f"الأحياء: {len(alive)}\nالمافيا والدكتور والمحقق: اضغطوا زر دوركم واختاروا (45 ثانية).", view=nv,
        )
        try:
            await asyncio.wait_for(ev.wait(), 45)
        except asyncio.TimeoutError:
            pass
        await close(nm_msg, nv)

        votes = list(acts["mafia"].values())
        victim = max(set(votes), key=lambda x: (votes.count(x), random.random())) if votes else None
        if victim is not None and victim == acts["doctor"]:
            text = "💊 الدكتور أنقذ ضحية المافيا! ما مات أحد."
        elif victim is not None:
            dead = alive.pop(victim)
            text = f"🔪 المافيا قتلوا {dead.mention} (كان {AR[role[victim]]})"
        else:
            text = "الليل مرّ بهدوء."
        w = winner()
        if w:
            break

        # ---------------- day
        votes_d, ev2 = {}, asyncio.Event()
        vv = discord.ui.View(timeout=None)
        sel = discord.ui.Select(
            placeholder="صوّت لطرد مشتبه",
            options=[discord.SelectOption(label=p.display_name[:90], value=str(p.id)) for p in alive.values()],
        )

        async def vote(i: discord.Interaction):
            if i.user.id not in alive:
                return await i.response.send_message("الأموات ما يصوتون 💀", ephemeral=True)
            votes_d[i.user.id] = int(sel.values[0])
            await i.response.send_message("✅ تم تسجيل صوتك", ephemeral=True)
            if len(votes_d) >= len(alive):
                ev2.set()

        sel.callback = vote
        vv.add_item(sel)
        dm = await say(g, f"☀️ النهار {night}", f"{text}\n\nناقشوا ثم صوّتوا (60 ثانية).", view=vv)
        try:
            await asyncio.wait_for(ev2.wait(), 60)
        except asyncio.TimeoutError:
            pass
        await close(dm, vv)

        tally = {}
        for t in votes_d.values():
            tally[t] = tally.get(t, 0) + 1
        out_text = "ما أحد انطرد (تعادل أو ما فيه أصوات)."
        if tally:
            top = max(tally.values())
            tops = [t for t, c in tally.items() if c == top]
            if len(tops) == 1 and tops[0] in alive:
                out = alive.pop(tops[0])
                out_text = f"🗳️ انطرد {out.mention} وكان {AR[role[out.id]]}"
        await say(g, "🗳️ نتيجة التصويت", out_text)
        w = winner()
        if w:
            break
        night += 1
        await asyncio.sleep(3)

    roles_txt = "\n".join(f"{p.mention}: {AR[role[p.id]]}" for p in pl)
    head = "🏆 فاز **المواطنين**!" if w == "citizens" else "😈 فازت **المافيا**!"
    await say(g, "🕵️ انتهت المافيا", f"{text}\n\n{head}\n\n{roles_txt}")


# ---------------------------------------------------------------- chairs
class ChairBtn(discord.ui.Button):
    def __init__(self):
        super().__init__(label="🪑", style=discord.ButtonStyle.secondary, disabled=True)

    async def callback(self, i: discord.Interaction):
        v: "Chairs" = self.view
        if i.user not in v.alive:
            return await i.response.send_message("انت مو داخل اللعبة", ephemeral=True)
        if i.user in v.seated:
            return await i.response.send_message("انت جالس أصلاً 😎", ephemeral=True)
        v.seated.append(i.user)
        self.label, self.style, self.disabled = i.user.display_name[:12], discord.ButtonStyle.success, True
        if len(v.seated) >= v.n:
            v.ev.set()
        await i.response.edit_message(view=v)


class Chairs(discord.ui.View):
    def __init__(self, alive, n):
        super().__init__(timeout=None)
        self.alive, self.n, self.seated, self.ev = alive, n, [], asyncio.Event()
        for _ in range(n):
            self.add_item(ChairBtn())


async def g_chairs(g):
    pl = await lobby(g, "🪑 كراسي", 3, 20)
    if not pl:
        return
    alive, rnd = pl[:], 1
    while len(alive) > 1:
        v = Chairs(alive, len(alive) - 1)
        m = await say(g, f"🪑 الجولة {rnd}", f"🎵 الموسيقى شغالة...\nاللاعبين: {len(alive)} | الكراسي: {len(alive) - 1}", view=v)
        await asyncio.sleep(random.uniform(3, 8))
        for c in v.children:
            c.disabled = False
        await m.edit(embed=mk(f"🪑 الجولة {rnd}", "⏸️ **وقفت الموسيقى! اجلس بسرعة!**"), view=v)
        try:
            await asyncio.wait_for(v.ev.wait(), 10)
        except asyncio.TimeoutError:
            pass
        seated = list(v.seated)
        await close(m, v)
        if not seated:
            return await say(g, "😴", "ما أحد جلس! انتهت اللعبة بدون فائز.")
        out = [p for p in alive if p not in seated]
        await say(g, "💥 طلعوا", "، ".join(p.mention for p in out))
        alive, rnd = seated, rnd + 1
        await asyncio.sleep(2)
    await say(g, "🏆 الفائز", f"{alive[0].mention} فاز بآخر كرسي!")


# ---------------------------------------------------------------- rock paper scissors duel
RPS = {"🪨": "حجر", "📄": "ورقة", "✂️": "مقص"}
BEATS = {"🪨": "✂️", "📄": "🪨", "✂️": "📄"}


class DuelBtn(discord.ui.Button):
    def __init__(self, e):
        super().__init__(emoji=e, label=RPS[e], style=discord.ButtonStyle.primary)
        self.pick = e

    async def callback(self, i: discord.Interaction):
        v: "Duel" = self.view
        if i.user not in v.players:
            return await i.response.send_message("انت مو باللعبة", ephemeral=True)
        if i.user.id in v.picks:
            return await i.response.send_message("اخترت أصلاً", ephemeral=True)
        v.picks[i.user.id] = self.pick
        await i.response.send_message(f"اخترت {self.pick}", ephemeral=True)
        if len(v.picks) == 2:
            v.ev.set()


class Duel(discord.ui.View):
    def __init__(self, players):
        super().__init__(timeout=None)
        self.players, self.picks, self.ev = players, {}, asyncio.Event()
        for e in RPS:
            self.add_item(DuelBtn(e))


async def g_rps(g):
    pl = await lobby(g, "✊ حجرة ورقة مقص", 2, 2)
    if not pl:
        return
    for rnd in range(1, 6):
        v = Duel(pl)
        m = await say(g, f"✊ جولة {rnd}", f"{pl[0].mention} 🆚 {pl[1].mention}\nكل واحد يختار (اختيارك سري).", view=v)
        try:
            await asyncio.wait_for(v.ev.wait(), 45)
        except asyncio.TimeoutError:
            await close(m, v)
            return await say(g, "⏰", "انتهى الوقت.")
        await close(m, v)
        a, b = v.picks[pl[0].id], v.picks[pl[1].id]
        head = f"{pl[0].mention} {a}  🆚  {b} {pl[1].mention}"
        if a == b:
            await say(g, "🤝 تعادل", head + "\nنعيد الجولة!")
            await asyncio.sleep(2)
            continue
        w = pl[0] if BEATS[a] == b else pl[1]
        return await say(g, "🏆 الفائز", f"{head}\n\n{w.mention} فاز!")
    await say(g, "😂", "تعادلتوا 5 مرات!")


# ---------------------------------------------------------------- dice
FACES = "⚀⚁⚂⚃⚄⚅"


async def g_dice(g):
    pl = await lobby(g, "🎲 نرد — الأعلى يفوز", 2, 20)
    if not pl:
        return
    cand = pl
    while True:
        m = await say(g, "🎲 النرد", "يتدحرجون...")
        for _ in range(6):
            txt = "\n".join(f"{p.display_name}: {random.choice(FACES)}{random.choice(FACES)}" for p in cand)
            await m.edit(embed=mk("🎲 النرد", txt))
            await asyncio.sleep(0.5)
        rolls = {p.id: (random.randint(1, 6), random.randint(1, 6)) for p in cand}
        txt = "\n".join(f"{p.mention}: {FACES[rolls[p.id][0] - 1]}{FACES[rolls[p.id][1] - 1]} = **{sum(rolls[p.id])}**" for p in cand)
        await m.edit(embed=mk("🎲 النرد", txt))
        top = max(sum(r) for r in rolls.values())
        winners = [p for p in cand if sum(rolls[p.id]) == top]
        if len(winners) == 1:
            return await say(g, "🏆 الفائز", f"{winners[0].mention} بمجموع {top}!")
        cand = winners
        await say(g, "🤝 تعادل", "نعيد الرمي بين: " + "، ".join(p.mention for p in cand))
        await asyncio.sleep(2)


# ---------------------------------------------------------------- wheel
SEGMENTS = [("💰 +100", 100), ("💰 +200", 200), ("💰 +300", 300), ("💎 +500", 500),
            ("👑 +1000", 1000), ("💣 إفلاس", None), ("😴 صفر", 0)]


async def g_wheel(g):
    pl = await lobby(g, "🎡 عجلة الحظ — لفتين لكل لاعب", 2, 10)
    if not pl:
        return
    score = {p.id: 0 for p in pl}
    for rnd in (1, 2):
        for p in pl:
            await ask_press(g, f"دورك {p.mention}! لف العجلة (لفة {rnd}/2)", p, "لف", "🎡", 30)
            label, val = random.choice(SEGMENTS)
            m = await say(g, "🎡 العجلة تدور...", "")
            for _ in range(6):
                await m.edit(embed=mk("🎡 العجلة تدور...", "# " + random.choice(SEGMENTS)[0]))
                await asyncio.sleep(0.5)
            score[p.id] = 0 if val is None else score[p.id] + val
            await m.edit(embed=mk("🎡", f"{p.mention}: **{label}**\nمجموعك: {score[p.id]}"))
            await asyncio.sleep(1.5)
    await scoreboard(g, score)


# ---------------------------------------------------------------- hide & seek
SPOTS = ["🛋️ الكنب", "🚪 الخزانة", "🛏️ السرير", "🌳 الشجرة", "🚗 السيارة", "🛁 الحمام", "📦 الصندوق", "🪟 الستارة", "🧺 السلة"]


async def g_hide(g):
    pl = await lobby(g, "🙈 غميضة", 3, 12)
    if not pl:
        return
    seeker = random.choice(pl)
    hiders = [p for p in pl if p != seeker]
    hide, ev = {}, asyncio.Event()

    hv = discord.ui.View(timeout=None)
    hb = discord.ui.Button(label="اختبئ", emoji="🙈", style=discord.ButtonStyle.primary)

    async def hb_cb(i: discord.Interaction):
        if i.user not in hiders:
            return await i.response.send_message("انت الباحث أو مو باللعبة 😅", ephemeral=True)
        sv = discord.ui.View(timeout=60)
        sel = discord.ui.Select(
            placeholder="اختر مكان اختبائك",
            options=[discord.SelectOption(label=s, value=str(k)) for k, s in enumerate(SPOTS)],
        )

        async def pick(ii: discord.Interaction):
            k = int(sel.values[0])
            hide[ii.user.id] = k
            await ii.response.edit_message(content=f"✅ اختبأت في {SPOTS[k]}", view=None)
            if len(hide) == len(hiders):
                ev.set()

        sel.callback = pick
        sv.add_item(sel)
        await i.response.send_message("وين تختبئ؟", view=sv, ephemeral=True)

    hb.callback = hb_cb
    hv.add_item(hb)
    m = await say(g, "🙈 غميضة", f"الباحث: {seeker.mention}\nالمختبئين: اضغطوا الزر واختاروا مكانكم (30 ثانية).", view=hv)
    try:
        await asyncio.wait_for(ev.wait(), 30)
    except asyncio.TimeoutError:
        pass
    await close(m, hv)
    for h in hiders:
        hide.setdefault(h.id, random.randrange(len(SPOTS)))

    found, st, ev2 = [], {"left": 5}, asyncio.Event()
    sv = discord.ui.View(timeout=None)

    def mkcb(k, btn):
        async def cb(i: discord.Interaction):
            if i.user != seeker:
                return await i.response.send_message("الباحث فقط 🔎", ephemeral=True)
            hits = [h for h in hiders if hide[h.id] == k and h not in found]
            found.extend(hits)
            st["left"] -= 1
            btn.disabled = True
            btn.style = discord.ButtonStyle.success if hits else discord.ButtonStyle.danger
            res = "، ".join(h.display_name for h in hits) if hits else "فاضي"
            btn.label = f"{SPOTS[k].split()[0]} {res}"[:80]
            done = len(found) == len(hiders) or st["left"] == 0
            if done:
                for c in sv.children:
                    c.disabled = True
            await i.response.edit_message(
                embed=mk("🔎 البحث", f"الباحث: {seeker.mention}\nلقى: {len(found)}/{len(hiders)} | محاولات باقية: {st['left']}"),
                view=sv,
            )
            if done:
                ev2.set()

        return cb

    for k, s in enumerate(SPOTS):
        b = discord.ui.Button(label=s, style=discord.ButtonStyle.secondary, row=k // 3)
        b.callback = mkcb(k, b)
        sv.add_item(b)
    await say(g, "🔎 البحث", f"{seeker.mention} عندك 5 محاولات تدوّر على {len(hiders)} مختبئين!", view=sv)
    try:
        await asyncio.wait_for(ev2.wait(), 180)
    except asyncio.TimeoutError:
        pass
    if len(found) == len(hiders):
        await say(g, "🏆 الباحث فاز", f"{seeker.mention} لقى الكل!")
    else:
        left = [h for h in hiders if h not in found]
        await say(g, "🏆 المختبئين فازوا", "الناجين: " + "، ".join(h.mention for h in left))


# ---------------------------------------------------------------- generic typing rounds
async def typing_rounds(g, title, make, n=5, timeout=20):
    scores = {}
    for r in range(1, n + 1):
        prompt, answers, file = make()
        accepted = {norm(a) for a in answers}
        await say(g, f"{title} — جولة {r}/{n}", prompt, file=file)
        t0 = time.monotonic()
        m = await first_answer(g, lambda c: norm(c) in accepted, timeout)
        if m:
            scores[m.author.id] = scores.get(m.author.id, 0) + 1
            try:
                await m.add_reaction("✅")
            except discord.HTTPException:
                pass
            await say(g, "✅ صح", f"{m.author.mention} جاوب في {time.monotonic() - t0:.1f} ثانية")
        else:
            await say(g, "⏰ انتهى الوقت", f"الجواب: **{answers[0]}**")
        await asyncio.sleep(2)
    await scoreboard(g, scores)


# ---------------------------------------------------------------- data
WORDS = ("مدرسة سيارة طائرة حاسوب مكتبة شجرة نجمة صحراء كتاب طاولة نافذة حديقة مستشفى مطعم قهوة "
         "عصير تفاحة برتقال فراولة هاتف ساعة مفتاح مظلة دراجة قطار سفينة جبل غابة شاطئ ملعب مدينة قلعة").split()
SENTENCES = ["الوقت كالسيف إن لم تقطعه قطعك", "العلم نور والجهل ظلام", "من جد وجد ومن زرع حصد",
             "الصبر مفتاح الفرج", "الجار قبل الدار", "العقل السليم في الجسم السليم",
             "سيرفر بلومي أجمل مكان للعب", "لا تؤجل عمل اليوم إلى الغد", "القناعة كنز لا يفنى"]
COLORS = {"🟥": "أحمر", "🟦": "أزرق", "🟩": "أخضر", "🟨": "أصفر", "🟧": "برتقالي",
          "🟪": "بنفسجي", "⬛": "أسود", "⬜": "أبيض", "🟫": "بني"}
EMOJI_Q = [("🍎", "تفاحة", "تفاح"), ("🦁", "أسد"), ("🐪", "جمل"), ("🚗", "سيارة"), ("✈️", "طائرة"),
           ("🌧️☂️", "مطر"), ("🌙⭐", "ليل", "قمر"), ("📚🏫", "مدرسة"), ("☕", "قهوة"), ("🍕", "بيتزا"),
           ("⚽🥅", "كرة قدم", "هدف"), ("🕌", "مسجد"), ("🏜️🐪", "صحراء"), ("🎂🕯️", "كيكة", "عيد ميلاد"),
           ("📱", "جوال", "هاتف", "موبايل"), ("🔥", "نار"), ("👑", "ملك", "تاج"), ("🌹", "وردة", "ورد"),
           ("💡", "مصباح", "لمبة"), ("🎮", "لعبة", "العاب")]
FLAGS = [("🇸🇦", "السعودية"), ("🇦🇪", "الإمارات"), ("🇰🇼", "الكويت"), ("🇶🇦", "قطر"), ("🇧🇭", "البحرين"),
         ("🇴🇲", "عمان"), ("🇪🇬", "مصر"), ("🇯🇴", "الأردن"), ("🇮🇶", "العراق"), ("🇱🇧", "لبنان"),
         ("🇸🇾", "سوريا"), ("🇾🇪", "اليمن"), ("🇲🇦", "المغرب"), ("🇩🇿", "الجزائر"), ("🇹🇳", "تونس"),
         ("🇱🇾", "ليبيا"), ("🇸🇩", "السودان"), ("🇹🇷", "تركيا"), ("🇫🇷", "فرنسا"), ("🇩🇪", "ألمانيا"),
         ("🇯🇵", "اليابان"), ("🇧🇷", "البرازيل"), ("🇺🇸", "أمريكا", "الولايات المتحدة"),
         ("🇬🇧", "بريطانيا"), ("🇪🇸", "إسبانيا"), ("🇮🇹", "إيطاليا")]
PAIRS = [("🙂", "🙃"), ("😀", "😃"), ("🐶", "🐕"), ("🌕", "🌖"), ("🔵", "🟦"), ("⭐", "🌟"),
         ("🍎", "🍅"), ("🕐", "🕑"), ("🧡", "❤️"), ("🐱", "🐈"), ("🍊", "🍑"), ("😊", "☺️")]
SIM = {"س": "ص", "ص": "س", "د": "ض", "ض": "د", "ذ": "ظ", "ظ": "ذ", "ت": "ط", "ط": "ت",
       "ح": "خ", "خ": "ح", "ع": "غ", "غ": "ع", "ق": "ك", "ك": "ق"}
SHAPES = ["دائرة", "مربع", "مثلث", "نجمة", "قلب", "معين", "مستطيل"]
SHAPE_ALT = {"دائرة": ["دائرة", "دايرة", "مدور"], "نجمة": ["نجمة", "نجم"]}


def corrupt(w):
    idx = [i for i, c in enumerate(w) if c in SIM]
    if idx:
        i = random.choice(idx)
        res = w[:i] + SIM[w[i]] + w[i + 1:]
    else:
        l = list(w)
        i = random.randrange(len(l) - 1)
        l[i], l[i + 1] = l[i + 1], l[i]
        res = "".join(l)
    return res if res != w else w[::-1]


def draw_shape():
    name = random.choice(SHAPES)
    S = 400
    img = Image.new("RGB", (S, S), (24, 24, 28))
    d = ImageDraw.Draw(img)
    col = random.choice([(235, 64, 52), (52, 152, 219), (46, 204, 113), (241, 196, 15), (155, 89, 182), (230, 126, 34)])
    c, r = S // 2, 140
    if name == "دائرة":
        d.ellipse((c - r, c - r, c + r, c + r), fill=col)
    elif name == "مربع":
        d.rectangle((c - r, c - r, c + r, c + r), fill=col)
    elif name == "مستطيل":
        d.rectangle((c - r - 30, c - r // 2, c + r + 30, c + r // 2), fill=col)
    elif name == "مثلث":
        d.polygon([(c, c - r), (c - r, c + r), (c + r, c + r)], fill=col)
    elif name == "معين":
        d.polygon([(c, c - r - 20), (c + r, c), (c, c + r + 20), (c - r, c)], fill=col)
    elif name == "نجمة":
        pts = []
        for k in range(10):
            ang = -math.pi / 2 + k * math.pi / 5
            rad = (r + 10) if k % 2 == 0 else (r + 10) * 0.4
            pts.append((c + rad * math.cos(ang), c + rad * math.sin(ang)))
        d.polygon(pts, fill=col)
    else:  # قلب
        d.ellipse((c - 140, c - 98, c, c + 42), fill=col)
        d.ellipse((c, c - 98, c + 140, c + 42), fill=col)
        d.polygon([(c - 137, c - 5), (c + 137, c - 5), (c, c + 154)], fill=col)
    buf = io.BytesIO()
    img.save(buf, "PNG")
    buf.seek(0)
    return name, buf


# ---------------------------------------------------------------- makers  (prompt, answers, file)
def mk_fast():
    s = random.choice(SENTENCES)
    return "اكتب الجملة بأسرع وقت:\n# " + s.replace(" ", " \u200b "), [s], None


def mk_fakk():
    w = random.choice(WORDS)
    return f"فكّك الكلمة (حرف حرف بمسافات):\n# {w}", [" ".join(w)], None


def mk_dmj():
    w = random.choice(WORDS)
    return f"ادمج الحروف واكتب الكلمة:\n# {' '.join(w)}", [w], None


def mk_rev():
    w = random.choice(WORDS)
    return f"اكتب الكلمة بالمقلوب:\n# {w}", [w[::-1]], None


def mk_order():
    w = random.choice(WORDS)
    l = list(w)
    for _ in range(20):
        random.shuffle(l)
        if "".join(l) != w:
            break
    return f"رتّب الحروف لتكوّن كلمة:\n# {' '.join(l)}", [w], None


def mk_harf():
    w = random.choice(WORDS)
    i = random.randrange(len(w))
    return f"ما هو الحرف رقم **{i + 1}** في كلمة:\n# {w}", [w[i]], None


def mk_fix():
    w = random.choice(WORDS)
    return f"صحّح الكلمة واكتبها صح:\n# {corrupt(w)}", [w], None


def mk_color():
    e = random.choice(list(COLORS))
    word = random.choice([c for k, c in COLORS.items() if k != e])
    return f"# {e}\nالكلمة تقول: **{word}**\nاكتب **لون المربع** مو الكلمة!", [COLORS[e]], None


def mk_emoji():
    q = random.choice(EMOJI_Q)
    return f"خمّن الكلمة من الإيموجي:\n# {q[0]}", list(q[1:]), None


def mk_flag():
    q = random.choice(FLAGS)
    return f"ما اسم هذه الدولة؟\n# {q[0]}", list(q[1:]), None


def mk_word():
    w = random.choice(WORDS)
    i = random.randrange(len(w))
    return f"أكمل الحرف الناقص واكتب الكلمة كاملة:\n# {w[:i]}❓{w[i + 1:]}", [w], None


def mk_draw():
    name, buf = draw_shape()
    return "ما اسم هذا الشكل؟", SHAPE_ALT.get(name, [name]), discord.File(buf, "shape.png")


# ---------------------------------------------------------------- replica / guess / button / spot
async def g_replica(g):
    scores = {}
    for r in range(1, 4):
        seq = " ".join(random.sample(WORDS, 3 + r))
        m = await say(g, f"🧠 ريبلكا — جولة {r}/3", f"احفظ الكلمات بالترتيب!\n# {seq}")
        await asyncio.sleep(4 + r)
        await m.edit(embed=mk(f"🧠 ريبلكا — جولة {r}/3", "اختفت! ✍️ اكتبها بنفس الترتيب."))
        t = norm(seq)
        w = await first_answer(g, lambda c: norm(c) == t, 40)
        if w:
            scores[w.author.id] = scores.get(w.author.id, 0) + 1
            await say(g, "✅", f"{w.author.mention} حفظها صح!")
        else:
            await say(g, "⏰", f"ما أحد قدر! كانت: **{seq}**")
        await asyncio.sleep(2)
    await scoreboard(g, scores)


async def g_guess(g):
    secret, tries = random.randint(1, 100), 0
    await say(g, "🔢 خمّن الرقم", "فكرت برقم من 1 إلى 100!\nاكتبوا تخميناتكم في الشات — عندكم دقيقتين.")
    end = time.monotonic() + 120

    def chk(m):
        return m.channel == g.channel and not m.author.bot and m.content.strip().isdigit()

    while True:
        left = end - time.monotonic()
        if left <= 0:
            return await say(g, "⏰ انتهى الوقت", f"الرقم كان **{secret}**")
        try:
            m = await bot.wait_for("message", check=chk, timeout=left)
        except asyncio.TimeoutError:
            continue
        n = int(m.content.strip())
        tries += 1
        if n == secret:
            return await say(g, "🎉 صح!", f"{m.author.mention} خمّن الرقم **{secret}** (بعد {tries} محاولة)")
        try:
            await m.add_reaction("⬆️" if n < secret else "⬇️")
        except discord.HTTPException:
            pass


async def g_button(g):
    scores = {}
    for r in range(1, 4):
        v = discord.ui.View(timeout=None)
        b = discord.ui.Button(label="انتظر...", style=discord.ButtonStyle.secondary, disabled=True)
        winner, ev = [], asyncio.Event()

        async def cb(i: discord.Interaction, winner=winner, ev=ev):
            if winner:
                return await i.response.send_message("سبقوك 😅", ephemeral=True)
            winner.append(i.user)
            await i.response.defer()
            ev.set()

        b.callback = cb
        v.add_item(b)
        m = await say(g, f"🔘 زر — جولة {r}/3", "جهّز إصبعك...", view=v)
        await asyncio.sleep(random.uniform(2, 6))
        b.label, b.style, b.disabled = "اضغط الآن!", discord.ButtonStyle.success, False
        t0 = time.monotonic()
        await m.edit(embed=mk(f"🔘 زر — جولة {r}/3", "⚡ اضغط!"), view=v)
        try:
            await asyncio.wait_for(ev.wait(), 15)
            scores[winner[0].id] = scores.get(winner[0].id, 0) + 1
            await close(m, v)
            await say(g, "⚡", f"{winner[0].mention} أسرع واحد! ({time.monotonic() - t0:.2f} ث)")
        except asyncio.TimeoutError:
            await close(m, v)
            await say(g, "⏰", "ما أحد ضغط!")
        await asyncio.sleep(2)
    await scoreboard(g, scores)


async def g_spot(g):
    scores = {}
    for r in range(1, 4):
        a, b = random.choice(PAIRS)
        pos = random.randrange(20)
        v = discord.ui.View(timeout=None)
        state, ev, btns = {"w": None, "bad": set()}, asyncio.Event(), []

        def mkcb(k):
            async def cb(i: discord.Interaction):
                if state["w"]:
                    return await i.response.send_message("انتهت الجولة", ephemeral=True)
                if i.user.id in state["bad"]:
                    return await i.response.send_message("انت طلعت من هالجولة ❌", ephemeral=True)
                if k == pos:
                    state["w"] = i.user
                    await i.response.defer()
                    ev.set()
                else:
                    state["bad"].add(i.user.id)
                    await i.response.send_message("❌ غلط! طلعت من الجولة", ephemeral=True)

            return cb

        for k in range(20):
            btn = discord.ui.Button(emoji=b if k == pos else a, style=discord.ButtonStyle.secondary, row=k // 5)
            btn.callback = mkcb(k)
            btns.append(btn)
            v.add_item(btn)
        m = await say(g, f"🔍 اكتشف — جولة {r}/3", "اضغط على الإيموجي المختلف!", view=v)
        try:
            await asyncio.wait_for(ev.wait(), 25)
        except asyncio.TimeoutError:
            pass
        btns[pos].style = discord.ButtonStyle.success
        await close(m, v)
        if state["w"]:
            scores[state["w"].id] = scores.get(state["w"].id, 0) + 1
            await say(g, "✅", f"{state['w'].mention} لقاه!")
        else:
            await say(g, "⏰", "ما أحد لقاه!")
        await asyncio.sleep(2)
    await scoreboard(g, scores)


# ---------------------------------------------------------------- registry
GAMES = {
    # ألعاب السيرفر
    "روليت": g_roulette,
    "xo": lambda g: g_xo(g, False),
    "مافيا": g_mafia,
    "كراسي": g_chairs,
    "حجرة": g_rps,
    "نرد": g_dice,
    "عجلة": g_wheel,
    "hotxo": lambda g: g_xo(g, True),
    "غميضة": g_hide,
    "ريبلكا": g_replica,
    "خمن": g_guess,
    "رسمة": lambda g: typing_rounds(g, "🎨 رسمة", mk_draw, 5, 20),
    "كلمة": lambda g: typing_rounds(g, "📝 كلمة", mk_word, 5, 20),
    # ألعاب فردية
    "زر": g_button,
    "اسرع": lambda g: typing_rounds(g, "⚡ اسرع", mk_fast, 5, 30),
    "فكك": lambda g: typing_rounds(g, "🔨 فكك", mk_fakk, 5, 25),
    "ادمج": lambda g: typing_rounds(g, "🧩 ادمج", mk_dmj, 5, 25),
    "اعلام": lambda g: typing_rounds(g, "🏳️ اعلام", mk_flag, 5, 20),
    "اعكس": lambda g: typing_rounds(g, "🔄 اعكس", mk_rev, 5, 25),
    "حرف": lambda g: typing_rounds(g, "🔤 حرف", mk_harf, 5, 20),
    "صحح": lambda g: typing_rounds(g, "✏️ صحح", mk_fix, 5, 25),
    "ترتيب": lambda g: typing_rounds(g, "🔀 ترتيب", mk_order, 5, 25),
    "الوان": lambda g: typing_rounds(g, "🎨 الوان", mk_color, 5, 15),
    "ايموجي": lambda g: typing_rounds(g, "😎 ايموجي", mk_emoji, 5, 20),
    "اكتشف": g_spot,
}
SERVER_GAMES = ["روليت", "xo", "مافيا", "كراسي", "حجرة", "نرد", "عجلة", "hotxo", "غميضة", "ريبلكا", "خمن", "رسمة", "كلمة"]
SOLO_GAMES = ["زر", "اسرع", "فكك", "ادمج", "اعلام", "اعكس", "حرف", "صحح", "ترتيب", "الوان", "ايموجي", "اكتشف"]


# ================================================================ events & commands
async def start_web():
    """سيرفر ويب صغير عشان Render يلقى بورت مفتوح"""
    from aiohttp import web

    async def ok(_):
        return web.Response(text="Bloomy bot is running ✅")

    app = web.Application()
    app.router.add_get("/", ok)
    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "0.0.0.0", int(os.getenv("PORT", "10000"))).start()


@bot.event
async def setup_hook():
    await start_web()
    await bot.tree.sync()


@bot.event
async def on_ready():
    await apply_status()
    print(f"Logged in as {bot.user}")


@bot.event
async def on_message(msg: discord.Message):
    if not TEXT_TRIGGERS or msg.author.bot or not msg.guild:
        return
    t = msg.content.strip().lower()
    if t in GAMES:
        err = await launch(msg.channel, msg.author, t)
        if err:
            await msg.reply(err, mention_author=False)
    elif t in ("ايقاف", "إيقاف", "stop"):
        if key(msg.channel) in ACTIVE:
            await msg.reply(await stop_game(msg.channel, msg.author), mention_author=False)


async def slash_launch(inter: discord.Interaction, name):
    err = await launch(inter.channel, inter.user, name)
    await inter.response.send_message(err or f"🎮 بدأت لعبة **{name}**", ephemeral=bool(err))


@bot.tree.command(name="games", description="ألعاب السيرفر")
@app_commands.choices(game=[app_commands.Choice(name=n, value=n) for n in SERVER_GAMES])
async def games(inter: discord.Interaction, game: app_commands.Choice[str]):
    await slash_launch(inter, game.value)


@bot.tree.command(name="solo", description="الألعاب الفردية")
@app_commands.choices(game=[app_commands.Choice(name=n, value=n) for n in SOLO_GAMES])
async def solo(inter: discord.Interaction, game: app_commands.Choice[str]):
    await slash_launch(inter, game.value)


@bot.tree.command(name="stop", description="إيقاف اللعبة الشغالة")
async def stop(inter: discord.Interaction):
    msg = await stop_game(inter.channel, inter.user)
    await inter.response.send_message(msg)


@bot.tree.command(name="setrole", description="حدد الرتبة اللي تقدر تشغّل الألعاب")
@app_commands.describe(role="الرتبة")
async def setrole(inter: discord.Interaction, role: discord.Role):
    if not inter.user.guild_permissions.manage_guild:
        return await inter.response.send_message("تحتاج صلاحية Manage Server", ephemeral=True)
    gcfg(inter.guild_id)["role"] = role.id
    save_cfg()
    await inter.response.send_message(f"✅ الحين بس {role.mention} (والإدارة) يقدرون يشغّلون الألعاب", allowed_mentions=discord.AllowedMentions.none())


@bot.tree.command(name="clearrole", description="السماح للجميع بتشغيل الألعاب")
async def clearrole(inter: discord.Interaction):
    if not inter.user.guild_permissions.manage_guild:
        return await inter.response.send_message("تحتاج صلاحية Manage Server", ephemeral=True)
    gcfg(inter.guild_id).pop("role", None)
    save_cfg()
    await inter.response.send_message("✅ الكل يقدر يشغّل الألعاب")


@bot.tree.command(name="setstatus", description="غيّر حالة البوت")
@app_commands.describe(text="نص الحالة", state="الحالة", activity="نوع النشاط")
@app_commands.choices(
    state=[app_commands.Choice(name=a, value=b) for a, b in
           (("متصل", "online"), ("خامل", "idle"), ("مشغول", "dnd"), ("غير مرئي", "invisible"))],
    activity=[app_commands.Choice(name=a, value=b) for a, b in
              (("يلعب", "playing"), ("يشاهد", "watching"), ("يستمع", "listening"), ("يتنافس", "competing"))],
)
async def setstatus(inter: discord.Interaction, text: str, state: app_commands.Choice[str] = None,
                    activity: app_commands.Choice[str] = None):
    if not inter.user.guild_permissions.administrator:
        return await inter.response.send_message("للإدارة فقط", ephemeral=True)
    CFG["_status"] = {"text": text[:100], "state": state.value if state else "online",
                      "activity": activity.value if activity else "playing"}
    save_cfg()
    await apply_status()
    await inter.response.send_message("✅ تم تغيير حالة البوت (تنطبق على كل السيرفرات)", ephemeral=True)


@bot.tree.command(name="help", description="قائمة الألعاب")
async def help_cmd(inter: discord.Interaction):
    e = mk("🎮 Bloomy Games",
           "**ألعاب السيرفر:**\n" + " • ".join(SERVER_GAMES) +
           "\n\n**ألعاب فردية:**\n" + " • ".join(SOLO_GAMES) +
           "\n\nاكتب اسم اللعبة في الشات أو استخدم `/games` و `/solo`\n"
           "إيقاف: `/stop` أو اكتب **ايقاف**")
    e.set_image(url="attachment://banner.jpg")
    e.set_thumbnail(url=None)
    await inter.response.send_message(embed=e, file=banner_file())


# ---------------------------------------------------------------- image card
def _font(size):
    for name in ("arial.ttf", "DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        try:
            return ImageFont.truetype(name, size)
        except OSError:
            continue
    return ImageFont.load_default()


def build_card(avatar_bytes: bytes, name: str) -> io.BytesIO:
    bg = Image.open(BANNER).convert("RGB").resize((1000, 562))
    av = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA").resize((180, 180))
    mask = Image.new("L", (180, 180), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 180, 180), fill=255)
    ring = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
    ImageDraw.Draw(ring).ellipse((0, 0, 199, 199), fill=(255, 255, 255, 255))
    x, y = 400, 330
    bg.paste(ring, (x, y), ring)
    bg.paste(av, (x + 10, y + 10), mask)
    from PIL import features
    if features.check("raqm"):  # بدونها العربي يطلع مقطّع، فنكتفي بالصورة
        d = ImageDraw.Draw(bg)
        f = _font(40)
        w = d.textlength(name, font=f)
        d.text(((1000 - w) / 2, y + 215), name, font=f, fill="white", stroke_width=3, stroke_fill="black")
    out = io.BytesIO()
    bg.save(out, "PNG")
    out.seek(0)
    return out


def winner_card(img_path: str, avatar_bytes: bytes) -> io.BytesIO:
    bg = Image.open(img_path).convert("RGB").resize((800, 450))
    bg = ImageEnhance.Brightness(bg).enhance(0.55)
    av = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA").resize((220, 220))
    mask = Image.new("L", (220, 220), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, 220, 220), fill=255)
    d = ImageDraw.Draw(bg)
    cx, cy = 400, 245
    d.ellipse((cx - 124, cy - 124, cx + 124, cy + 124), fill=(255, 205, 40))
    bg.paste(av, (cx - 110, cy - 110), mask)
    d.polygon([(cx - 70, cy - 125), (cx - 80, cy - 185), (cx - 35, cy - 150), (cx, cy - 200),
               (cx + 35, cy - 150), (cx + 80, cy - 185), (cx + 70, cy - 125)], fill=(255, 205, 40), outline="white")
    out = io.BytesIO()
    bg.save(out, "PNG")
    out.seek(0)
    return out


@bot.tree.command(name="card", description="بطاقتك على صورة Bloomy")
@app_commands.describe(member="العضو (اختياري)")
async def card(inter: discord.Interaction, member: discord.Member = None):
    member = member or inter.user
    await inter.response.defer()
    avatar = await member.display_avatar.replace(size=256, format="png").read()
    img = await asyncio.to_thread(build_card, avatar, member.display_name)
    await inter.followup.send(file=discord.File(img, "card.png"))


if __name__ == "__main__":
    if not TOKEN:
        raise SystemExit("حط التوكن: export DISCORD_TOKEN=xxxx")
    bot.run(TOKEN)
