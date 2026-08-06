 import asyncio, logging, os, sqlite3, random, string, threading

try:
    from flask import Flask
    flask_app = Flask(__name__)
    @flask_app.route("/")
    def home(): return "EverXX Bot Running! 1000 + Worldwide"
    @flask_app.route("/health")
    def health(): return "OK", 200
    def run_flask():
        import os
        port = int(os.environ.get("PORT", 10000))
        flask_app.run(host="0.0.0.0", port=port)
    HAS_FLASK = True
except:
    HAS_FLASK = False

from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.enums import ParseMode

BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
ADMIN_IDS = [123456789]
if os.getenv("ADMIN_IDS"):
    try:
        ADMIN_IDS = [int(x.strip()) for x in os.getenv("ADMIN_IDS").split(",") if x.strip()]
    except:
        pass

REFERRAL_REWARD = 1000
MIN_PAYOUT = 2000
BOT_USERNAME = os.getenv("BOT_USERNAME", "Ever_XXbot")

COUNTRIES = [
    "🌍 Worldwide",
    "🇳🇬 Nigeria", "🇬🇭 Ghana", "🇿🇦 South Africa", "🇰🇪 Kenya", "🇪🇬 Egypt", "🇪🇹 Ethiopia",
    "🇺🇸 USA", "🇬🇧 UK", "🇨🇦 Canada", "🇦🇺 Australia", "🇩🇪 Germany", "🇫🇷 France",
    "🇮🇳 India", "🇵🇰 Pakistan", "🇧🇩 Bangladesh", "🇵🇭 Philippines", "🇮🇩 Indonesia",
    "🇧🇷 Brazil", "🇲🇽 Mexico", "🇹🇷 Turkey", "🇦🇪 UAE", "🇸🇦 Saudi Arabia", "🇷🇺 Russia",
    "🇺🇦 Ukraine", "🇮🇹 Italy", "🇪🇸 Spain", "🇳🇱 Netherlands", "🇸🇪 Sweden", "🇳🇴 Norway"
]

DB_PATH = "everxx.db"
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.execute("CREATE TABLE IF NOT EXISTS users (user_id INTEGER PRIMARY KEY, username TEXT, gender TEXT, age INTEGER, location TEXT, country TEXT DEFAULT 'Worldwide', search_country TEXT DEFAULT 'Worldwide', bio TEXT, photo_id TEXT, preference TEXT DEFAULT 'All', referral_code TEXT UNIQUE, referred_by INTEGER, balance INTEGER DEFAULT 0, referrals INTEGER DEFAULT 0, is_registered BOOLEAN DEFAULT 0, is_banned BOOLEAN DEFAULT 0, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    try: c.execute("ALTER TABLE users ADD COLUMN country TEXT DEFAULT 'Worldwide'")
    except: pass
    try: c.execute("ALTER TABLE users ADD COLUMN search_country TEXT DEFAULT 'Worldwide'")
    except: pass
    c.execute("CREATE TABLE IF NOT EXISTS likes (id INTEGER PRIMARY KEY AUTOINCREMENT, from_id INTEGER, to_id INTEGER, type TEXT DEFAULT 'like', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(from_id, to_id))")
    c.execute("CREATE TABLE IF NOT EXISTS seen (viewer_id INTEGER, viewed_id INTEGER, PRIMARY KEY (viewer_id, viewed_id))")
    c.execute("CREATE TABLE IF NOT EXISTS matches (id INTEGER PRIMARY KEY AUTOINCREMENT, user1 INTEGER, user2 INTEGER, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP, UNIQUE(user1, user2))")
    c.execute("CREATE TABLE IF NOT EXISTS messages (id INTEGER PRIMARY KEY AUTOINCREMENT, from_id INTEGER, to_id INTEGER, text TEXT, created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    c.execute("CREATE TABLE IF NOT EXISTS payouts (id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER, amount INTEGER, status TEXT DEFAULT 'pending', created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP)")
    conn.commit()
    conn.close()

def gen_code(uid): return f"EVER{uid % 10000}{''.join(random.choices(string.digits, k=2))}"
def create_user(uid, uname):
    conn=get_db(); c=conn.cursor(); rc=gen_code(uid)
    c.execute("INSERT OR IGNORE INTO users (user_id, username, referral_code) VALUES (?,?,?)",(uid, uname, rc))
    conn.commit(); conn.close(); return rc
def get_user(uid):
    conn=get_db(); c=conn.cursor(); c.execute("SELECT * FROM users WHERE user_id=?",(uid,)); r=c.fetchone(); conn.close(); return r
def update_user(uid, **kw):
    conn=get_db(); c=conn.cursor()
    for k,v in kw.items():
        c.execute(f"UPDATE users SET {k}=? WHERE user_id=?",(v, uid))
    conn.commit(); conn.close()
def add_ref(new_uid, code):
    conn=get_db(); c=conn.cursor()
    c.execute("SELECT user_id FROM users WHERE referral_code=?",(code,)); ref=c.fetchone()
    if ref and ref['user_id']!=new_uid:
        rid=ref['user_id']
        c.execute("SELECT referred_by FROM users WHERE user_id=?",(new_uid,)); u=c.fetchone()
        if u and u['referred_by'] is None:
            c.execute("UPDATE users SET referred_by=? WHERE user_id=?",(rid,new_uid))
            c.execute("UPDATE users SET balance=balance+1000, referrals=referrals+1 WHERE user_id=?",(rid,))
            conn.commit(); conn.close(); return rid
    conn.close(); return None
def get_random(uid):
    conn=get_db(); c=conn.cursor(); viewer=get_user(uid)
    if not viewer: return None
    pref=viewer['preference'] if 'preference' in viewer.keys() and viewer['preference'] else 'All'
    sc=viewer['search_country'] if 'search_country' in viewer.keys() and viewer['search_country'] else 'Worldwide'
    q="SELECT * FROM users WHERE user_id!=? AND is_registered=1 AND is_banned=0 AND user_id NOT IN (SELECT viewed_id FROM seen WHERE viewer_id=?)"
    p=[uid,uid]
    if pref!='All': q+=" AND gender=?"; p.append(pref)
    if 'Worldwide' not in sc: q+=" AND country=?"; p.append(sc)
    q+=" ORDER BY RANDOM() LIMIT 1"
    c.execute(q,p); row=c.fetchone()
    if row:
        c.execute("INSERT OR IGNORE INTO seen (viewer_id, viewed_id) VALUES (?,?)",(uid,row['user_id'])); conn.commit()
    conn.close(); return row
def add_like(fid,tid,lt='like'):
    conn=get_db(); c=conn.cursor()
    c.execute("INSERT OR IGNORE INTO likes (from_id,to_id,type) VALUES (?,?,?)",(fid,tid,lt))
    c.execute("SELECT * FROM likes WHERE from_id=? AND to_id=?",(tid,fid)); mut=c.fetchone(); is_match=False
    if mut:
        u1,u2=sorted([fid,tid]); c.execute("INSERT OR IGNORE INTO matches (user1,user2) VALUES (?,?)",(u1,u2)); is_match=True
    conn.commit(); conn.close(); return is_match
def get_likers(uid):
    conn=get_db(); c=conn.cursor()
    c.execute("SELECT l.from_id, u.* FROM likes l JOIN users u ON l.from_id=u.user_id WHERE l.to_id=? AND l.from_id NOT IN (SELECT user2 FROM matches WHERE user1=? UNION SELECT user1 FROM matches WHERE user2=?)",(uid,uid,uid))
    rows=c.fetchall(); conn.close(); return rows
def get_matches(uid):
    conn=get_db(); c=conn.cursor()
    c.execute("SELECT m.*, u.* FROM matches m JOIN users u ON (u.user_id = CASE WHEN m.user1=? THEN m.user2 ELSE m.user1 END) WHERE m.user1=? OR m.user2=? ORDER BY m.created_at DESC",(uid,uid,uid))
    rows=c.fetchall(); conn.close(); return rows

def main_menu():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Find People"),KeyboardButton(text="Who Liked Me")],[KeyboardButton(text="My Chats"),KeyboardButton(text="My Profile")],[KeyboardButton(text="Affiliate"),KeyboardButton(text="About")],[KeyboardButton(text="Settings")]],resize_keyboard=True)
def profile_kb(uid):
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Like",callback_data=f"like_{uid}"),InlineKeyboardButton(text="Dislike",callback_data=f"dislike_{uid}")],[InlineKeyboardButton(text="Super Like",callback_data=f"super_{uid}"),InlineKeyboardButton(text="Next",callback_data="next_profile")]])
def settings_menu():
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Change Country",callback_data="change_country"),InlineKeyboardButton(text="Search Country",callback_data="search_country")],[InlineKeyboardButton(text="Edit Bio",callback_data="edit_bio")]])
def countries_kb():
    b=[]; r=[]
    for co in COUNTRIES:
        r.append(InlineKeyboardButton(text=co,callback_data=f"country_{co}"))
        if len(r)==2: b.append(r); r=[]
    if r: b.append(r)
    return InlineKeyboardMarkup(inline_keyboard=b)
def search_kb():
    b=[]; r=[]
    for co in COUNTRIES:
        r.append(InlineKeyboardButton(text=co,callback_data=f"search_{co}"))
        if len(r)==2: b.append(r); r=[]
    if r: b.append(r)
    return InlineKeyboardMarkup(inline_keyboard=b)
def aff_kb(rc,bu):
    link=f"https://t.me/{bu}?start={rc}"
    return InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Share Link",url=f"https://t.me/share/url?url={link}")],[InlineKeyboardButton(text="Withdraw",callback_data="withdraw")]])
def gender_kb():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Male"),KeyboardButton(text="Female")],[KeyboardButton(text="Other")]],resize_keyboard=True,one_time_keyboard=True)
def skip_kb():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Skip")]],resize_keyboard=True)

logging.basicConfig(level=logging.INFO)
bot=Bot(token=BOT_TOKEN)
dp=Dispatcher()

class Reg(StatesGroup):
    gender=State(); age=State(); location=State(); country=State(); search_country=State(); bio=State(); photo=State(); edit_bio=State()

@dp.message(CommandStart())
async def start_cmd(message:Message,state:FSMContext):
    args=message.text.split(); ref=args[1] if len(args)>1 else None
    create_user(message.from_user.id,message.from_user.username); user=get_user(message.from_user.id)
    if ref and user and not user['is_registered']:
        rid=add_ref(message.from_user.id,ref)
        if rid:
            try: await bot.send_message(rid,f"New referral! You earned {REFERRAL_REWARD}!",parse_mode=ParseMode.HTML)
            except: pass
    if user and user['is_registered']:
        await message.answer(f"Welcome back! {user['country']} | Searching: {user['search_country']}",reply_markup=main_menu())
    else:
        await message.answer("Welcome to EverXX! 100% a2zDatingbot clone\n\nWhat's your gender?",parse_mode=ParseMode.HTML,reply_markup=gender_kb())
        await state.set_state(Reg.gender)

@dp.message(Reg.gender)
async def rg(message:Message,state:FSMContext):
    g="Male" if "Male" in message.text else "Female" if "Female" in message.text else "Other"
    await state.update_data(gender=g); await message.answer("How old are you? (18-60)",reply_markup=skip_kb()); await state.set_state(Reg.age)

@dp.message(Reg.age)
async def ra(message:Message,state:FSMContext):
    try: age=int(message.text)
    except: age=22
    if age<18: await message.answer("Must be 18+"); return
    await state.update_data(age=age); await message.answer("Send your city (e.g. Lagos, Ifo)",reply_markup=skip_kb()); await state.set_state(Reg.location)

@dp.message(Reg.location)
async def rl(message:Message,state:FSMContext):
    loc=message.text if not message.location else "Nearby"
    await state.update_data(location=loc); await message.answer("Select your Country:",reply_markup=countries_kb()); await state.set_state(Reg.country)

@dp.callback_query(F.data.startswith("country_"),Reg.country)
async def rc(callback:CallbackQuery,state:FSMContext):
    country=callback.data.replace("country_","")
    await state.update_data(country=country)
    await callback.message.answer("Who to FIND? Worldwide = all",reply_markup=search_kb()); await state.set_state(Reg.search_country); await callback.answer(f"Country: {country}")

@dp.callback_query(F.data.startswith("search_"),Reg.search_country)
async def rs(callback:CallbackQuery,state:FSMContext):
    sc=callback.data.replace("search_","")
    await state.update_data(search_country=sc)
    await callback.message.answer("Write bio:",reply_markup=skip_kb()); await state.set_state(Reg.bio); await callback.answer(f"Searching: {sc}")

@dp.message(Reg.bio)
async def rb(message:Message,state:FSMContext):
    bio=message.text if message.text!="Skip" else "Hey!"
    await state.update_data(bio=bio); await message.answer("Send photo",reply_markup=skip_kb()); await state.set_state(Reg.photo)

@dp.message(Reg.photo,F.photo)
async def rp(message:Message,state:FSMContext):
    data=await state.get_data()
    update_user(message.from_user.id,gender=data['gender'],age=data['age'],location=data.get('location','Lagos'),country=data.get('country','Worldwide'),search_country=data.get('search_country','Worldwide'),bio=data['bio'],photo_id=message.photo[-1].file_id,is_registered=1)
    await state.clear(); await message.answer(f"Created! {data.get('country')} | Searching: {data.get('search_country')}",reply_markup=main_menu())

@dp.message(Reg.photo)
async def rps(message:Message,state:FSMContext):
    if message.text=="Skip":
        data=await state.get_data()
        update_user(message.from_user.id,gender=data['gender'],age=data['age'],location=data.get('location','Lagos'),country=data.get('country','Worldwide'),search_country=data.get('search_country','Worldwide'),bio=data['bio'],is_registered=1)
        await state.clear(); await message.answer("Created!",reply_markup=main_menu())

@dp.message(F.text=="Find People")
async def find_p(message:Message):
    profile=get_random(message.from_user.id)
    if not profile: await message.answer("No more profiles. Change to Worldwide in Settings."); return
    cap=f"{profile['username'] or 'Anonymous'}, {profile['age'] or '??'}\n{profile['country'] or ''} | {profile['location'] or ''}\n\n{profile['bio'] or ''}"
    if profile['photo_id']:
        await bot.send_photo(message.from_user.id,profile['photo_id'],caption=cap,parse_mode=ParseMode.HTML,reply_markup=profile_kb(profile['user_id']))
    else:
        await message.answer(cap,parse_mode=ParseMode.HTML,reply_markup=profile_kb(profile['user_id']))

@dp.callback_query(F.data.startswith("like_") | F.data.startswith("dislike_") | F.data.startswith("super_"))
async def handle_like(callback:CallbackQuery):
    action,tid=callback.data.split("_")[0],int(callback.data.split("_")[1])
    fid=callback.from_user.id
    if action=="like":
        is_match=add_like(fid,tid,'like'); await callback.answer("Liked!")
        if is_match:
            await bot.send_message(fid,f"MATCH! {tid} liked you too!")
            try: await bot.send_message(tid,f"New Match! {fid} liked you back!")
            except: pass
    else:
        await callback.answer("Skipped")
    profile=get_random(fid)
    if profile:
        cap=f"{profile['username'] or 'Anonymous'}, {profile['age'] or '??'}\n{profile['country'] or ''} | {profile['location']}\n\n{profile['bio'] or ''}"
        if profile['photo_id']:
            await bot.send_photo(fid,profile['photo_id'],caption=cap,parse_mode=ParseMode.HTML,reply_markup=profile_kb(profile['user_id']))
        else:
            await bot.send_message(fid,cap,parse_mode=ParseMode.HTML,reply_markup=profile_kb(profile['user_id']))

@dp.callback_query(F.data=="next_profile")
async def next_p(callback:CallbackQuery):
    await callback.answer()
    profile=get_random(callback.from_user.id)
    if not profile: await bot.send_message(callback.from_user.id,"No more profiles."); return
    cap=f"{profile['username'] or 'Anonymous'}, {profile['age'] or '??'}\n{profile['country'] or ''} | {profile['location']}\n\n{profile['bio'] or ''}"
    if profile['photo_id']:
        await bot.send_photo(callback.from_user.id,profile['photo_id'],caption=cap,parse_mode=ParseMode.HTML,reply_markup=profile_kb(profile['user_id']))
    else:
        await bot.send_message(callback.from_user.id,cap,parse_mode=ParseMode.HTML,reply_markup=profile_kb(profile['user_id']))

@dp.message(F.text=="Who Liked Me")
async def wlm(message:Message):
    likers=get_likers(message.from_user.id)
    if not likers: await message.answer("No likes yet."); return
    txt=f"{len(likers)} liked you!\n\n"
    for u in likers[:5]: txt+=f"{u['username'] or u['user_id']} - {u['country'] or ''}\n"
    await message.answer(txt,parse_mode=ParseMode.HTML)

@dp.message(F.text=="My Chats")
async def my_chats(message:Message):
    ms=get_matches(message.from_user.id)
    if not ms: await message.answer("No chats yet."); return
    t="Your Chats:\n\n"
    for m in ms: t+=f"{m['username'] or m['user_id']} - /chat_{m['user_id']}\n"
    await message.answer(t,parse_mode=ParseMode.HTML)

@dp.message(F.text.startswith("/chat_"))
async def chat_cmd(message:Message):
    try:
        parts=message.text.split(" ",1); tid=int(parts[0].replace("/chat_",""))
        if len(parts)<2: await message.answer("Send: /chat_123 Hi"); return
        conn=get_db(); c=conn.cursor(); c.execute("INSERT INTO messages (from_id,to_id,text) VALUES (?,?,?)",(message.from_user.id,tid,parts[1])); conn.commit(); conn.close()
        await message.answer("Sent!")
        try: await bot.send_message(tid,f"From {message.from_user.id}:\n{parts[1]}\n\nReply: /chat_{message.from_user.id} Hi")
        except: pass
    except Exception as e: await message.answer(f"Error {e}")

@dp.message(F.text=="My Profile")
async def my_profile(message:Message):
    u=get_user(message.from_user.id)
    if not u: await message.answer("Create profile /start"); return
    cap=f"Your Profile:\n{u['username']}, {u['age']} - {u['gender']}\n{u['country']}\nSearching: {u['search_country']}\n{u['location']}\n{u['bio']}\n\nReferrals: {u['referrals']} | Balance: {u['balance']}"
    if u['photo_id']: await bot.send_photo(message.from_user.id,u['photo_id'],caption=cap,parse_mode=ParseMode.HTML)
    else: await message.answer(cap,parse_mode=ParseMode.HTML)

@dp.message(F.text=="Affiliate")
async def aff(message:Message):
    u=get_user(message.from_user.id); link=f"https://t.me/{BOT_USERNAME}?start={u['referral_code']}"
    txt=f"Affiliate\n\nLink:\n{link}\n\nYou earn {REFERRAL_REWARD} per friend!\n{u['referrals']}\nBalance {u['balance']}"
    await message.answer(txt,parse_mode=ParseMode.HTML,reply_markup=aff_kb(u['referral_code'],BOT_USERNAME))

@dp.callback_query(F.data=="withdraw")
async def withdraw(callback:CallbackQuery):
    u=get_user(callback.from_user.id)
    if u['balance']<MIN_PAYOUT: await callback.answer(f"Min {MIN_PAYOUT} You have {u['balance']}",show_alert=True); return
    conn=get_db(); c=conn.cursor(); c.execute("INSERT INTO payouts (user_id,amount) VALUES (?,?)",(callback.from_user.id,u['balance'])); c.execute("UPDATE users SET balance=0 WHERE user_id=?",(callback.from_user.id,)); conn.commit(); conn.close()
    await callback.answer(f"Withdrawal {u['balance']} requested!",show_alert=True)

@dp.message(F.text=="Settings")
async def settings(message:Message): await message.answer("Settings:",reply_markup=settings_menu())
@dp.callback_query(F.data=="change_country")
async def change_c(callback:CallbackQuery): await callback.message.answer("New country:",reply_markup=countries_kb()); await callback.answer()
@dp.callback_query(F.data=="search_country")
async def search_c(callback:CallbackQuery): await callback.message.answer("Search who?",reply_markup=search_kb()); await callback.answer()
@dp.callback_query(F.data.startswith("country_"))
async def upd_c(callback:CallbackQuery):
    if "search_" not in callback.data:
        country_val=callback.data.replace("country_","")
        update_user(callback.from_user.id,country=country_val)
        await callback.answer(f"Country {country_val}",show_alert=True)
        await callback.message.answer(f"Country {country_val}",reply_markup=main_menu())
@dp.callback_query(F.data.startswith("search_"))
async def upd_s(callback:CallbackQuery):
    sc=callback.data.replace("search_","")
    update_user(callback.from_user.id,search_country=sc)
    await callback.answer(f"Searching {sc}",show_alert=True)
    await callback.message.answer(f"Searching {sc}",reply_markup=main_menu())
@dp.callback_query(F.data=="edit_bio")
async def edit_bio_cb(callback:CallbackQuery,state:FSMContext): await callback.message.answer("Send new bio:"); await state.set_state(Reg.edit_bio); await callback.answer()
@dp.message(Reg.edit_bio)
async def save_bio(message:Message,state:FSMContext): update_user(message.from_user.id,bio=message.text); await state.clear(); await message.answer("Bio updated!",reply_markup=main_menu())
@dp.message(F.text=="About")
async def about(message:Message): await message.answer("EverXX - 100% a2zDatingbot clone + Worldwide + 1000 referral")

async def main():
    init_db(); print(f"EverXX Started {REFERRAL_REWARD} Worldwide"); await dp.start_polling(bot)

if __name__=="__main__":
    if HAS_FLASK: threading.Thread(target=run_flask,daemon=True).start()
    asyncio.run(main())
