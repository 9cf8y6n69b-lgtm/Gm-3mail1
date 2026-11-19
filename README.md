# Bloomy Games Bot 🎮

## التشغيل
1. `pip install -r requirements.txt`
2. في https://discord.com/developers/applications ← Bot:
   - انسخ التوكن
   - فعّل **Message Content Intent**
3. ادعُ البوت بصلاحيات: Send Messages, Embed Links, Attach Files, Add Reactions, Read Message History
   (مع scope: `bot` و `applications.commands`)
4. `export DISCORD_TOKEN=التوكن` (ويندوز: `set DISCORD_TOKEN=التوكن`) ثم `python bot.py`

## الأوامر
| الأمر | وظيفته |
|---|---|
| `/games` `/solo` أو اكتب اسم اللعبة | تشغيل لعبة |
| `/stop` أو اكتب `ايقاف` | إيقاف اللعبة الشغالة |
| `/setrole` `/clearrole` | تحديد رتبة تشغيل الألعاب |
| `/setstatus` | تغيير حالة البوت (للإدارة) |
| `/help` `/card` | القائمة / بطاقتك |

## الملفات
- `bot.py` — البوت
- `images/` — صورة لكل لعبة (تتغير وتنعاد بـ `python gen_images.py`)
- `games_preview.png` — معاينة كل الصور
- `bloomy_banner.jpg` — صورة Bloomy الأساسية
- `config.json` — يتولّد تلقائياً (الرتبة والحالة)

## إعدادات في أول bot.py
- `LOCK_SCOPE = "guild"` لعبة وحدة لكل السيرفر، أو `"channel"` لكل روم
- `TEXT_TRIGGERS = True` تشغيل الألعاب بكتابة اسمها
