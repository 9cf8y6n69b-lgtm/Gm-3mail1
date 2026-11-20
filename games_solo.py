from common import *

WORDS = ("مدرسة سيارة طائرة حاسوب مكتبة شجرة نجمة صحراء كتاب طاولة نافذة حديقة مستشفى مطعم قهوة "
         "عصير تفاحة برتقال فراولة هاتف ساعة مفتاح مظلة دراجة قطار سفينة جبل غابة شاطئ ملعب مدينة قلعة "
         "ارنب حارس نمر فيل اسد غزال جمل حصان بطيخ موز عنب رمان ليمون خيمة سلم مطر قمر شمس سحابة").split()
SIM = {"س": "ص", "ص": "س", "د": "ض", "ض": "د", "ذ": "ظ", "ظ": "ذ", "ت": "ط", "ط": "ت",
       "ح": "خ", "خ": "ح", "ع": "غ", "غ": "ع", "ق": "ك", "ك": "ق"}
PLURALS = [("كتاب", "كتب"), ("قلم", "اقلام"), ("بيت", "بيوت"), ("ولد", "اولاد"), ("رجل", "رجال"),
           ("مدينة", "مدن"), ("شجرة", "اشجار"), ("نهر", "انهار"), ("جبل", "جبال"), ("طفل", "اطفال"),
           ("باب", "ابواب"), ("نجم", "نجوم"), ("سيف", "سيوف"), ("بحر", "بحار"), ("كلب", "كلاب"),
           ("قلب", "قلوب"), ("شارع", "شوارع"), ("مفتاح", "مفاتيح"), ("ورقة", "اوراق"), ("طالب", "طلاب"),
           ("معلم", "معلمون", "معلمين"), ("مهندس", "مهندسون", "مهندسين"), ("مسلم", "مسلمون", "مسلمين"),
           ("طائر", "طيور"), ("وردة", "ورود"), ("يوم", "ايام"), ("شهر", "شهور", "اشهر"), ("عين", "عيون")]
OPPOSITES = [("كبير", "صغير"), ("طويل", "قصير"), ("حار", "بارد"), ("سريع", "بطيء", "بطي"), ("ليل", "نهار"),
             ("قوي", "ضعيف"), ("جديد", "قديم"), ("سعيد", "حزين"), ("غني", "فقير"), ("نظيف", "قذر", "وسخ"),
             ("سهل", "صعب"), ("بعيد", "قريب"), ("فوق", "تحت"), ("داخل", "خارج"), ("شمال", "جنوب"),
             ("شرق", "غرب"), ("ممتلئ", "فارغ"), ("ثقيل", "خفيف"), ("ابيض", "اسود"), ("حلو", "مر"),
             ("صباح", "مساء"), ("اول", "اخر"), ("حي", "ميت"), ("نعم", "لا")]
CAPITALS = [("السعودية", "الرياض"), ("الامارات", "ابوظبي", "ابو ظبي"), ("الكويت", "الكويت", "مدينة الكويت"),
            ("قطر", "الدوحة"), ("البحرين", "المنامة"), ("عمان", "مسقط"), ("مصر", "القاهرة"), ("الاردن", "عمان"),
            ("العراق", "بغداد"), ("لبنان", "بيروت"), ("سوريا", "دمشق"), ("اليمن", "صنعاء"), ("المغرب", "الرباط"),
            ("الجزائر", "الجزائر"), ("تونس", "تونس"), ("ليبيا", "طرابلس"), ("السودان", "الخرطوم"),
            ("فلسطين", "القدس"), ("تركيا", "انقرة"), ("فرنسا", "باريس"), ("المانيا", "برلين"),
            ("اليابان", "طوكيو"), ("بريطانيا", "لندن"), ("ايطاليا", "روما"), ("اسبانيا", "مدريد"),
            ("روسيا", "موسكو"), ("الصين", "بكين"), ("امريكا", "واشنطن"), ("البرازيل", "برازيليا"),
            ("كوريا الجنوبية", "سيول"), ("الهند", "نيودلهي", "دلهي")]
COMPANIES = [("شركة صنعت الآيفون", "ابل", "apple"), ("شركة صنعت هواتف جالكسي", "سامسونج", "samsung"),
             ("اكبر محرك بحث في العالم", "قوقل", "جوجل", "google"), ("شركة البلايستيشن", "سوني", "sony"),
             ("شركة ويندوز والاكس بوكس", "مايكروسوفت", "microsoft"), ("شركة سيارات مؤسسها ايلون ماسك", "تيسلا", "tesla"),
             ("اكبر متجر الكتروني مؤسسه جيف بيزوس", "امازون", "amazon"),
             ("شركة فيسبوك وانستقرام الام", "ميتا", "فيسبوك", "meta", "facebook"),
             ("مطاعم شعارها حرف M ذهبي", "ماكدونالدز", "ماكدونالد", "mcdonalds"),
             ("شركة ملابس رياضية شعارها علامة صح", "نايكي", "nike"), ("مقاهي شعارها حورية خضراء", "ستاربكس", "starbucks"),
             ("سيارات رياضية شعارها حصان اسود", "فيراري", "ferrari"), ("مشروب غازي احمر شهير", "كوكاكولا", "كوكا كولا"),
             ("منصة افلام ومسلسلات شعارها N احمر", "نتفلكس", "netflix"),
             ("شركة النفط السعودية العملاقة", "ارامكو", "aramco"), ("شركة طيران الامارات الشهيرة", "طيران الامارات", "emirates")]
FLAGS = [("SA", "السعودية"), ("AE", "الامارات"), ("KW", "الكويت"), ("QA", "قطر"), ("BH", "البحرين"),
         ("OM", "عمان"), ("EG", "مصر"), ("JO", "الاردن"), ("IQ", "العراق"), ("LB", "لبنان"), ("SY", "سوريا"),
         ("YE", "اليمن"), ("MA", "المغرب"), ("DZ", "الجزائر"), ("TN", "تونس"), ("LY", "ليبيا"), ("SD", "السودان"),
         ("PS", "فلسطين"), ("TR", "تركيا"), ("FR", "فرنسا"), ("DE", "المانيا"), ("JP", "اليابان"),
         ("BR", "البرازيل"), ("US", "امريكا", "الولايات المتحدة"), ("GB", "بريطانيا", "انجلترا"), ("ES", "اسبانيا"),
         ("IT", "ايطاليا"), ("RU", "روسيا"), ("CN", "الصين"), ("KR", "كوريا", "كوريا الجنوبية"), ("IN", "الهند")]
LETTERS = list("ابتجحدرسشعفقكلمنهوي")
CATEGORIES = ["جماد", "اسم", "حيوان", "نبات", "بلاد"]


def exact(answers):
    acc = {norm(a) for a in answers}
    return (lambda c: norm(c) in acc), answers[0]


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


# ---------------------------------------------------------------- makers -> (prompt, check, reveal, file)
async def mk_fast():
    w = random.choice(WORDS)
    buf = await asyncio.to_thread(word_image, w)
    return "اكتب الكلمة اللي في الصورة بأسرع وقت!", *exact([w]), discord.File(buf, "word.png")


async def mk_fakk():
    w = random.choice(WORDS)
    return f"فكّك الكلمة (حرف حرف بمسافات)، مثال: ارنب ← ا ر ن ب\n# {w}", *exact([" ".join(w)]), None


async def mk_asbk():
    w = random.choice(WORDS)
    return f"اشبك الحروف واكتب الكلمة:\n# {' '.join(w)}", *exact([w]), None


async def mk_dmj():
    a, b = random.sample(WORDS, 2)
    return f"ادمج الكلمتين في كلمة وحدة بدون مسافة:\n# {a}  +  {b}", *exact([a + b]), None


async def mk_reverse():
    w = random.choice(WORDS)
    return f"الحروف مقلوبة! اكتب الكلمة الصحيحة:\n# {' '.join(w[::-1])}", *exact([w]), None


async def mk_fix():
    w = random.choice(WORDS)
    return f"صحّح الكلمة واكتبها صح:\n# {corrupt(w)}", *exact([w]), None


async def mk_plural():
    q = random.choice(PLURALS)
    return f"اكتب **جمع** الكلمة:\n# {q[0]}", *exact(list(q[1:])), None


async def mk_singular():
    q = random.choice(PLURALS)
    return f"اكتب **مفرد** الكلمة:\n# {q[1]}", *exact([q[0]]), None


async def mk_opposite():
    q = random.choice(OPPOSITES)
    return f"اكتب **عكس** الكلمة:\n# {q[0]}", *exact(list(q[1:])), None


async def mk_capital():
    q = random.choice(CAPITALS)
    return f"ما هي عاصمة:\n# {q[0]}", *exact(list(q[1:])), None


async def mk_company():
    q = random.choice(COMPANIES)
    return f"ما اسم الشركة؟\n# {q[0]}", *exact(list(q[1:])), None


async def mk_flag():
    q = random.choice(FLAGS)
    path = os.path.join(IMG_DIR, "flags", q[0] + ".png")
    f = discord.File(path, "flag.png") if os.path.exists(path) else None
    return "ما اسم هذه الدولة؟", *exact(list(q[1:])), f


async def mk_mul():
    a, b = random.randint(2, 12), random.randint(2, 12)
    return f"احسب الناتج:\n# {ar_digits(a)} × {ar_digits(b)}", *exact([str(a * b)]), None


async def mk_sub():
    a = random.randint(20, 99)
    b = random.randint(3, a - 1)
    return f"احسب الناتج:\n# {ar_digits(a)} − {ar_digits(b)}", *exact([str(a - b)]), None


async def mk_harf():
    letter, cat = random.choice(LETTERS), random.choice(CATEGORIES)
    nl = norm(letter)

    def chk(c):
        n = norm(c)
        return len(n.split()) == 1 and len(n) >= 3 and n[0] == nl and n not in reserved()

    return f"اكتب كلمة من نوع **{cat}** تبدأ بحرف:\n# {letter}", chk, f"أي {cat} تبدأ بـ {letter}", None


# ---------------------------------------------------------------- rounds
async def solo_rounds(g, title, make, n=5):
    scores = {}
    timeout = g.T()
    for r in range(1, n + 1):
        prompt, chk, reveal, file = await make()
        await say(g, f"{title} — جولة {r}/{n}", prompt, file=file)
        t0 = time.monotonic()
        m = await first_answer(g, chk, timeout)
        if m:
            dt = time.monotonic() - t0
            scores[m.author.id] = scores.get(m.author.id, 0) + 1
            reward(g, m.author, points=1)
            u = DB.user(g.gid, m.author.id)
            if u["best"] is None or dt < u["best"]:
                u["best"] = round(dt, 2)
                DB.save()
            try:
                await m.add_reaction("✅")
            except discord.HTTPException:
                pass
            await say(g, "✅ صح", f"{m.author.mention} جاوب في {dt:.1f} ثانية")
        else:
            await say(g, "⏰ انتهى الوقت", f"الجواب: **{reveal}**")
        await asyncio.sleep(2)
    top = await scoreboard(g, scores)
    if g.event_points and top:
        await finish(g, [await get_member(g, top)])


def solo(name, slug, title, make, t=20):
    async def run(g):
        await solo_rounds(g, title, make, 5)

    GAMES[name] = dict(fn=run, slug=slug, title=title, kind="solo", t=t)


solo("اسرع", "fast", "⚡ اسرع", mk_fast, 25)
solo("فكك", "fakk", "🔨 فكك", mk_fakk, 25)
solo("شركة", "company", "🏢 شركة", mk_company, 25)
solo("اشبك", "asbk", "🧷 اشبك", mk_asbk, 25)
solo("صحح", "fix", "✏️ صحح", mk_fix, 25)
solo("اعكس", "reverse", "🔄 اعكس", mk_reverse, 25)
solo("عكس", "opposite", "↔️ عكس", mk_opposite, 20)
solo("جمع", "plural", "➕ جمع", mk_plural, 20)
solo("مفرد", "singular", "1️⃣ مفرد", mk_singular, 20)
solo("حرف", "harf", "🔤 حرف", mk_harf, 25)
solo("اعلام", "flags", "🏳️ اعلام", mk_flag, 20)
solo("عواصم", "capitals", "🏛️ عواصم", mk_capital, 20)
solo("ضرب", "mul", "✖️ ضرب", mk_mul, 20)
solo("طرح", "sub", "➖ طرح", mk_sub, 20)
solo("ادمج", "dmj", "🧩 ادمج", mk_dmj, 25)
