import time
import requests
import pymongo
from datetime import datetime, timedelta

# ----- Configuration -----
TOKEN = "2109246071:LvlHCpvSkjpD8rFw1N4lNcaJmKP5EyCxgUNp6euX"
BASE_URL = f"https://tapi.bale/bot{TOKEN}"
MONGO_URI = "mongodb://mongo:iOaGntNtUjrGOVEEfkVxVZArKMTLpfiT@tramway.proxy.rlwy.net:56584"
ADMINS = ["zonercm", "dszone"]  # List of admin usernames

# Reply keyboard layouts
MAIN_KEYBOARD = [["فارسی ← انگلیسی", "انگلیسی ← فارسی"], ["🎁 کوین رایگان روزانه", "🎟️ کد هدیه"], ["👤 اطلاعات حساب"]]
BACK_KEYBOARD = [["🔙 بازگشت به منوی اصلی"]]
ADMIN_KEYBOARD = [["📤 ارسال پیام"], ["🖼️ ارسال تصویر"], ["📸 تصویر با کپشن"], ["🔙 بازگشت (ادمین)"]]

# ----- Database Setup -----
client = pymongo.MongoClient(MONGO_URI)
db = client["botdb"]
users_col = db["users"]
codes_col = db["codes"]

# Ensure some sample codes (expired field)
if codes_col.count_documents({}) == 0:
    codes_col.insert_many([
        {"code": "WELCOME5", "value": 5, "used": False},
        {"code": "BONUS10", "value": 10, "used": False}
    ])

# ----- Helper Functions -----

def send_method(method: str, data: dict, files=None):
    url = f"{BASE_URL}/{method}"
    return requests.post(url, data=data, files=files)


def send_message(chat_id, text, reply_markup=None):
    payload = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    return send_method("sendMessage", payload)


def send_photo(chat_id, photo_url, caption=None):
    payload = {"chat_id": chat_id, "photo": photo_url}
    if caption:
        payload["caption"] = caption
        payload["parse_mode"] = "HTML"
    return send_method("sendPhoto", payload)


def get_updates(offset=None, timeout=30):
    params = {"timeout": timeout, "offset": offset}
    return requests.get(f"{BASE_URL}/getUpdates", params=params).json()


def google_translate(text, target_lang):
    resp = requests.get(
        "https://translate.googleapis.com/translate_a/single",
        params={"client": "gtx", "sl": "auto", "tl": target_lang, "dt": "t", "q": text}
    ).json()
    return resp[0][0][0]


def get_user(chat_id, username, first_name):
    user = users_col.find_one({"chat_id": chat_id})
    if not user:
        user = {"chat_id": chat_id, "username": username, "first_name": first_name,
                "coins": 5, "last_daily": None, "state": None}
        users_col.insert_one(user)
    return user


def update_user(chat_id, **kwargs):
    users_col.update_one({"chat_id": chat_id}, {"$set": kwargs})

# ----- Main Loop -----
offset = None
while True:
    updates = get_updates(offset)
    for item in updates.get("result", []):
        offset = item["update_id"] + 1
        msg = item.get("message")
        if not msg: continue
        chat_id = msg["chat"]["id"]
        txt = msg.get("text", "")
        user = get_user(chat_id, msg["from"].get("username", ''), msg["from"].get("first_name", ''))
        state = user.get("state")

        # Deduct coin (except admin)
        def use_coin():
            if user["coins"] <= 0:
                send_message(chat_id, "❌ کوین شما کافی نیست!", reply_markup={"keyboard": MAIN_KEYBOARD, "resize_keyboard": True})
                return False
            update_user(chat_id, coins=user["coins"] - 1)
            return True

        # Handle /start
        if txt == "/start":
            update_user(chat_id, state=None)
            send_message(chat_id,
                         f"👋 سلام {user['first_name']}! خوش اومدی به ربات Carbon AI 🤖\nلطفاً گزینه‌ای را انتخاب کن:",
                         reply_markup={"keyboard": MAIN_KEYBOARD, "resize_keyboard": True})
            continue

        # Admin panel toggle
        if txt == "/admin" and user.get("username") in ADMINS:
            update_user(chat_id, state="admin_panel")
            send_message(chat_id, "🔒 پنل ادمین:", reply_markup={"keyboard": ADMIN_KEYBOARD, "resize_keyboard": True})
            continue

        # State: admin_panel
        if state == "admin_panel":
            if txt == "🔙 بازگشت (ادمین)":
                update_user(chat_id, state=None)
                send_message(chat_id, "🔙 بازگشت به منوی اصلی", reply_markup={"keyboard": MAIN_KEYBOARD, "resize_keyboard": True})
            elif txt == "📤 ارسال پیام":
                update_user(chat_id, state="admin_send_msg")
                send_message(chat_id, "📩 لطفاً پیام برای ارسال را تایپ کنید:")
            elif txt == "🖼️ ارسال تصویر":
                update_user(chat_id, state="admin_send_img")
                send_message(chat_id, "🌆 لطفاً آدرس تصویر را ارسال کنید:")
            elif txt == "📸 تصویر با کپشن":
                update_user(chat_id, state="admin_send_img_cap")
                send_message(chat_id, "🌄 لطفاً آدرس تصویر و سپس کپشن را با خط جدید ارسال کنید:")
            else:
                # Handle admin send flows
                if state == "admin_send_msg":
                    for u in users_col.find():
                        send_message(u["chat_id"], txt)
                    send_message(chat_id, "✅ پیام شما ارسال شد.")
                    update_user(chat_id, state="admin_panel")
                elif state == "admin_send_img":
                    for u in users_col.find():
                        send_photo(u["chat_id"], txt)
                    send_message(chat_id, "✅ تصویر ارسال شد.")
                    update_user(chat_id, state="admin_panel")
                elif state == "admin_send_img_cap":
                    parts = txt.split("\n", 1)
                    if len(parts) == 2:
                        url, cap = parts
                        for u in users_col.find():
                            send_photo(u["chat_id"], url, cap)
                        send_message(chat_id, "✅ تصویر با کپشن ارسال شد.")
                    else:
                        send_message(chat_id, "⚠️ فرمت اشتباه! دوباره تلاش کنید.")
                    update_user(chat_id, state="admin_panel")
            continue

        # Main Menu Buttons
        if txt == "🔙 بازگشت به منوی اصلی":
            update_user(chat_id, state=None)
            send_message(chat_id, "🔙 بازگشت به منوی اصلی", reply_markup={"keyboard": MAIN_KEYBOARD, "resize_keyboard": True})
            continue

        if txt in ["فارسی ← انگلیسی", "انگلیسی ← فارسی"]:
            direction = "en" if txt.startswith("فارسی") else "fa"
            update_user(chat_id, state=f"trans_{direction}")
            send_message(chat_id, "✏️ لطفاً متن را ارسال کنید:", reply_markup={"keyboard": BACK_KEYBOARD, "resize_keyboard": True})
            continue

        if state and state.startswith("trans_"):
            # translation flow
            if txt == "🔙 بازگشت به منوی اصلی":
                update_user(chat_id, state=None)
                send_message(chat_id, "🔙 بازگشت", reply_markup={"keyboard": MAIN_KEYBOARD, "resize_keyboard": True})
                continue
            if not use_coin():
                continue
            _, lang = state.split("_")
            target = "en" if lang == "en" else "fa"
            result = google_translate(txt, target)
            send_message(chat_id, f"<b>🔤 ترجمه:</b>\n{result}\n\n<i>Translated by Carbon AI</i>",
                         reply_markup={"keyboard": BACK_KEYBOARD, "resize_keyboard": True})
            update_user(chat_id, state=None)
            continue

        if txt == "🎁 کوین رایگان روزانه":
            # daily coin
            last = user.get("last_daily")
            today = datetime.utcnow().date()
            if last and datetime.fromisoformat(last).date() == today:
                send_message(chat_id, "❌ امروز کوین خود را دریافت کرده‌اید! فردا بازگردید.")
            else:
                update_user(chat_id, coins=user["coins"] + 1, last_daily=today.isoformat())
                send_message(chat_id, f"✅ یک کوین دریافت شد! کوین‌های شما: {user['coins']+1}")
            continue

        if txt == "🎟️ کد هدیه":
            update_user(chat_id, state="redeem_code")
            send_message(chat_id, "🎫 لطفاً کد هدیه را وارد کنید:", reply_markup={"keyboard": BACK_KEYBOARD, "resize_keyboard": True})
            continue

        if state == "redeem_code":
            if txt == "🔙 بازگشت به منوی اصلی":
                update_user(chat_id, state=None)
                send_message(chat_id, "🔙 بازگشت", reply_markup={"keyboard": MAIN_KEYBOARD, "resize_keyboard": True})
                continue
            code = codes_col.find_one({"code": txt, "used": False})
            if code:
                users_col.update_one({"chat_id": chat_id}, {"$inc": {"coins": code["value"]}})
                codes_col.update_one({"_id": code["_id"]}, {"$set": {"used": True}})
                send_message(chat_id, f"🎉 موفق! {code['value']} کوین به حساب شما اضافه شد.")
            else:
                send_message(chat_id, "❌ کد نامعتبر یا استفاده شده است.")
            update_user(chat_id, state=None)
            continue

        if txt == "👤 اطلاعات حساب":
            send_message(chat_id,
                         f"👤 <b>حساب شما:</b>\n
• نام کاربری: @{user.get('username')}\n• نام: {user.get('first_name')}\n• کوین‌ها: {user.get('coins')}", reply_markup={"keyboard": MAIN_KEYBOARD, "resize_keyboard": True})
            continue

        # Fallback
        send_message(chat_id, "⚠️ دستور نامعتبر. لطفاً از منوی اصلی انتخاب کنید.", reply_markup={"keyboard": MAIN_KEYBOARD, "resize_keyboard": True})

    time.sleep(0.5)
