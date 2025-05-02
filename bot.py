import time
import requests
import pymongo
from datetime import datetime

# ----- Configuration -----
TOKEN = "2109246071:LvlHCpvSkjpD8rFw1N4lNcaJmKP5EyCxgUNp6euX"
BASE_URL = f"https://tapi.bale.ai/bot{TOKEN}"
MONGO_URI = "mongodb://mongo:iOaGntNtUjrGOVEEfkVxVZArKMTLpfiT@tramway.proxy.rlwy.net:56584"
ADMINS = ["zonercm", "admin2"]  # لیست یوزرنیم‌های ادمین‌ها

# ----- Keyboard Layouts -----
MAIN_KEYBOARD = [
    ["📥 فارسی ← انگلیسی", "📤 انگلیسی ← فارسی"],
    ["🎁 کوین روزانه", "🎟️ کد هدیه"],
    ["👤 اطلاعات حساب"]
]
BACK_KEYBOARD = [["🔙 بازگشت به منوی اصلی"]]
ADMIN_KEYBOARD = [
    ["📣 ارسال پیام به همه"],
    ["🖼️ ارسال تصویر"],
    ["📸 تصویر با کپشن"],
    ["❌ خروج ادمین"]
]

# ----- Database Setup -----
client = pymongo.MongoClient(MONGO_URI)
db = client["botdb"]
users_col = db["users"]
codes_col = db["codes"]

# نمونه کدها
if codes_col.count_documents({}) == 0:
    codes_col.insert_many([
        {"code": "WELCOME5", "value": 5, "used": False},
        {"code": "BONUS10", "value": 10, "used": False}
    ])

# ----- Helper Functions -----

def send_method(method, data, files=None):
    return requests.post(f"{BASE_URL}/{method}", data=data, files=files)


def send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return send_method("sendMessage", payload)


def send_photo(chat_id, photo, caption=None):
    payload = {"chat_id": chat_id, "photo": photo}
    if caption:
        payload.update({"caption": caption, "parse_mode": "HTML"})
    return send_method("sendPhoto", payload)


def get_updates(offset=None, timeout=30):
    return requests.get(f"{BASE_URL}/getUpdates", params={"offset": offset, "timeout": timeout}).json()


def google_translate(text, target):
    # JSON response: [[ ["translated",...],... ]]
    res = requests.get(
        "https://translate.googleapis.com/translate_a/single",
        params={"client": "gtx", "sl": "auto", "tl": target, "dt": "t", "q": text}
    ).json()
    return res[0][0][0]


def get_user(chat_id, username, first_name):
    user = users_col.find_one({"chat_id": chat_id})
    if not user:
        user = {"chat_id": chat_id, "username": username, "first_name": first_name,
                "coins": 5, "last_daily": None, "state": None}
        users_col.insert_one(user)
    return user


def update_user(chat_id, **fields):
    users_col.update_one({"chat_id": chat_id}, {"$set": fields})

# ----- Main Polling Loop -----
offset = None
while True:
    data = get_updates(offset)
    for upd in data.get("result", []):
        offset = upd["update_id"] + 1
        msg = upd.get("message")
        if not msg: continue
        chat_id = msg["chat"]["id"]
        txt = msg.get("text", "")
        user = get_user(chat_id, msg["from"].get("username", ''), msg["from"].get("first_name", ''))
        state = user.get("state")

        # Deduct a coin (non-admin)
        def use_coin():
            if user["username"] not in ADMINS:
                if user["coins"] <= 0:
                    send_message(chat_id, "⛔️ کوین‌هات تموم شده! لطفاً شارژ کن.",
                                 reply_markup={"keyboard": MAIN_KEYBOARD, "resize_keyboard": True})
                    return False
                update_user(chat_id, coins=user["coins"] - 1)
            return True

        # /start
        if txt == "/start":
            update_user(chat_id, state=None)
            send_message(chat_id,
                         f"👋 سلام {user['first_name']}! به Carbon AI خوش اومدی 🤖✨\nیه گزینه انتخاب کن:",
                         reply_markup={"keyboard": MAIN_KEYBOARD, "resize_keyboard": True})
            continue

        # Admin panel entry
        if txt == "/admin" and user.get("username") in ADMINS:
            update_user(chat_id, state="admin")
            send_message(chat_id, "🔐 پنل ادمین باز شد:",
                         reply_markup={"keyboard": ADMIN_KEYBOARD, "resize_keyboard": True})
            continue

        # Admin panel actions
        if state == "admin":
            if txt == "❌ خروج ادمین":
                update_user(chat_id, state=None)
                send_message(chat_id, "🔙 بازگشت به منو اصلی", reply_markup={"keyboard": MAIN_KEYBOARD, "resize_keyboard": True})

            elif txt == "📣 ارسال پیام به همه":
                update_user(chat_id, state="adm_msg")
                send_message(chat_id, "✏️ پیام خودت رو تایپ کن:")

            elif txt == "🖼️ ارسال تصویر":
                update_user(chat_id, state="adm_img")
                send_message(chat_id, "🔗 آدرس تصویر رو بفرست:")

            elif txt == "📸 تصویر با کپشن":
                update_user(chat_id, state="adm_imgcap")
                send_message(chat_id, "🔗 URL و بعدش کپشن رو بذار تو دو خط:")

            else:
                # Broadcast flows
                if state == "adm_msg":
                    for u in users_col.find(): send_message(u["chat_id"], txt)
                    send_message(chat_id, "✅ پیام ارسال شد!")
                    update_user(chat_id, state="admin")

                elif state == "adm_img":
                    for u in users_col.find(): send_photo(u["chat_id"], txt)
                    send_message(chat_id, "✅ تصویر ارسال شد!")
                    update_user(chat_id, state="admin")

                elif state == "adm_imgcap":
                    parts = txt.split("\n", 1)
                    if len(parts) == 2:
                        url, cap = parts
                        for u in users_col.find(): send_photo(u["chat_id"], url, cap)
                        send_message(chat_id, "✅ تصویر با کپشن ارسال شد!")
                        update_user(chat_id, state="admin")
                    else:
                        send_message(chat_id, "⚠️ فرمت درست نبود، دوباره تلاش کن.")
            continue

        # Back button
        if txt == "🔙 بازگشت به منوی اصلی":
            update_user(chat_id, state=None)
            send_message(chat_id, "🔙 برگشت!", reply_markup={"keyboard": MAIN_KEYBOARD, "resize_keyboard": True})
            continue

        # Translation commands
        if txt in ["📥 فارسی ← انگلیسی", "📤 انگلیسی ← فارسی"]:
            direction = "en" if txt.startswith("📥") else "fa"
            update_user(chat_id, state=f"trans_{direction}")
            send_message(chat_id, "✏️ متنت رو بفرس:", reply_markup={"keyboard": BACK_KEYBOARD, "resize_keyboard": True})
            continue

        # Process translation
        if state and state.startswith("trans_"):
            if txt == "🔙 بازگشت به منوی اصلی":
                update_user(chat_id, state=None)
                send_message(chat_id, "🔙 برگشت", reply_markup={k: v for k,v in [("keyboard", MAIN_KEYBOARD), ("resize_keyboard", True)]})
                continue
            if not use_coin(): continue
            _, lang = state.split("_")
            target = "en" if lang == "en" else "fa"
            translated = google_translate(txt, target)
            send_message(chat_id,
                         f"🔤 <b>ترجمه:</b>\n{translated}\n\n<i>Translated by Carbon AI</i>",
                         reply_markup={"keyboard": BACK_KEYBOARD, "resize_keyboard": True})
            update_user(chat_id, state=None)
            continue

        # Daily coin
        if txt == "🎁 کوین روزانه":
            last = user.get("last_daily")
            today = datetime.utcnow().date()
            if last and datetime.fromisoformat(last).date() == today:
                send_message(chat_id, "⛔️ امروز دریافت کردی! فردا بیا.")
            else:
                update_user(chat_id, coins=user["coins"] + 1, last_daily=today.isoformat())
                send_message(chat_id, f"🎉 یک کوین جدید! تو الان {user['coins']+1} کوین داری 😎")
            continue

        # Redeem code
        if txt == "🎟️ کد هدیه":
            update_user(chat_id, state="redeem")
            send_message(chat_id, "🎫 کده رو وارد کن:", reply_markup={"keyboard": BACK_KEYBOARD, "resize_keyboard": True})
            continue

        if state == "redeem":
            if txt == "🔙 بازگشت به منوی اصلی":
                update_user(chat_id, state=None)
                send_message(chat_id, "🔙 برگشت", reply_markup={"keyboard": MAIN_KEYBOARD, "resize_keyboard": True})
                continue
            code = codes_col.find_one({"code": txt, "used": False})
            if code:
                users_col.update_one({"chat_id": chat_id}, {"$inc": {"coins": code["value"]}})
                codes_col.update_one({"_id": code["_id"]}, {"$set": {"used": True}})
                send_message(chat_id, f"🎉 موفق! +{code['value']} کوین دریافت شد!")
            else:
                send_message(chat_id, "❌ کد نامعتبر یا استفاده شده.")
            update_user(chat_id, state=None)
            continue

        # Account info
        if txt == "👤 اطلاعات حساب":
            msg = f"""👤 <b>حساب شما:</b>
• نام کاربری: @{user.get('username')}
• نام: {user.get('first_name')}
• کوین‌ها: {user.get('coins')}"""
            send_message(chat_id, msg, reply_markup={"keyboard": MAIN_KEYBOARD, "resize_keyboard": True})
            continue

        # Default fallback
        send_message(chat_id, "⚠️ دستور نامعتبر! لطفاً از منو انتخاب کن.", reply_markup={"keyboard": MAIN_KEYBOARD, "resize_keyboard": True})

    time.sleep(0.5)
