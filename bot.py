import requests
import time
from pymongo import MongoClient
from datetime import datetime
import random
import string

TOKEN = "2109246071:LvlHCpvSkjpD8rFw1N4lNcaJmKP5EyCxgUNp6euX"
URL = f"https://tapi.bale.ai/bot{TOKEN}"
MONGO_URI = "mongodb://mongo:iOaGntNtUjrGOVEEfkVxVZArKMTLpfiT@tramway.proxy.rlwy.net:56584"

client = MongoClient(MONGO_URI)
db = client["carbon_ai_bot"]
users = db["users"]
codes = db["codes"]

def get_updates(offset=None):
    params = {"timeout": 100, "offset": offset}
    return requests.get(f"{URL}/getUpdates", params=params).json()

def send_message(chat_id, text, reply_markup=None):
    data = {"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}
    if reply_markup:
        data["reply_markup"] = reply_markup
    requests.post(f"{URL}/sendMessage", json=data)

def reply_keyboard(buttons):
    return {
        "keyboard": [[{"text": btn} for btn in row] for row in buttons],
        "resize_keyboard": True,
        "one_time_keyboard": False
    }

def check_user(user_id):
    if not users.find_one({"_id": user_id}):
        users.insert_one({
            "_id": user_id,
            "coins": 5,
            "last_daily": "",
            "used_codes": []
        })

def has_coin(user_id):
    user = users.find_one({"_id": user_id})
    return user["coins"] > 0

def deduct_coin(user_id):
    users.update_one({"_id": user_id}, {"$inc": {"coins": -1}})

def add_coin(user_id):
    users.update_one({"_id": user_id}, {"$inc": {"coins": 1}})

def translate(text, source, target):
    url = "https://translate.googleapis.com/translate_a/single"
    params = {"client": "gtx", "sl": source, "tl": target, "dt": "t", "q": text}
    response = requests.get(url, params=params)
    try:
        return response.json()[0][0][0]
    except:
        return "خطا در ترجمه"

def today():
    return datetime.now().strftime("%Y-%m-%d")

def generate_code():
    return ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

def main():
    offset = None
    state = {}

    while True:
        updates = get_updates(offset)
        for update in updates.get("result", []):
            offset = update["update_id"] + 1

            if "message" not in update: continue
            msg = update["message"]
            chat_id = msg["chat"]["id"]
            user_id = msg["from"]["id"]
            text = msg.get("text", "")
            check_user(user_id)

            if user_id in state:
                lang = state[user_id]["lang"]
                if has_coin(user_id):
                    translated = translate(text, "en" if lang == "en2fa" else "fa", "fa" if lang == "en2fa" else "en")
                    deduct_coin(user_id)
                    send_message(chat_id, f"*{translated}*\n\n_ترجمه شده توسط Carbon AI_")
                else:
                    send_message(chat_id, "❗ شما سکه کافی ندارید!")
                del state[user_id]
                continue

            if text in ["🇺🇸 English ➡️ Persian", "🇮🇷 Persian ➡️ English"]:
                state[user_id] = {"lang": "en2fa" if "English" in text else "fa2en"}
                send_message(chat_id, "✏️ لطفا متن خود را ارسال کنید:")
                continue

            elif text == "🪙 دریافت سکه روزانه":
                user = users.find_one({"_id": user_id})
                if user["last_daily"] == today():
                    send_message(chat_id, "✅ شما امروز سکه دریافت کرده‌اید.\nفردا دوباره امتحان کنید!")
                else:
                    users.update_one({"_id": user_id}, {"$set": {"last_daily": today()}})
                    add_coin(user_id)
                    send_message(chat_id, "🎉 یک سکه به حساب شما افزوده شد!")

            elif text == "🎁 وارد کردن کد سکه":
                send_message(chat_id, "لطفا کد خود را ارسال کنید:")
                state[user_id] = {"redeem": True}

            elif state.get(user_id, {}).get("redeem"):
                code_data = codes.find_one({"code": text})
                if not code_data:
                    send_message(chat_id, "❌ کد نامعتبر است.")
                elif user_id in code_data["used_by"]:
                    send_message(chat_id, "⚠️ شما قبلا این کد را استفاده کرده‌اید.")
                else:
                    add_coin(user_id)
                    codes.update_one({"code": text}, {"$push": {"used_by": user_id}})
                    send_message(chat_id, "✅ سکه با موفقیت اضافه شد!")
                del state[user_id]

            elif text == "/start":
                keyboard = reply_keyboard([
                    ["🇺🇸 English ➡️ Persian", "🇮🇷 Persian ➡️ English"],
                    ["🪙 دریافت سکه روزانه"],
                    ["🎁 وارد کردن کد سکه"]
                ])
                send_message(chat_id, "*سلام!*\nبه ربات *Carbon AI* خوش آمدید! ✨\nهر فعالیت ۱ سکه مصرف می‌کند.", reply_markup=keyboard)

            else:
                send_message(chat_id, "❓ گزینه‌ی نامعتبر. لطفا از کیبورد استفاده کنید.")

if __name__ == "__main__":
    main()
