import requests
import json
import time
import datetime
import random
import string
import pymongo
from threading import Thread

# Bot Configuration
BOT_TOKEN = "2109246071:LvlHCpvSkjpD8rFw1N4lNcaJmKP5EyCxgUNp6euX"
BASE_URL = f"https://tapi.bale.ai/bot{BOT_TOKEN}"

# Initialize MongoDB connection
mongo_client = pymongo.MongoClient("mongodb://mongo:iOaGntNtUjrGOVEEfkVxVZArKMTLpfiT@tramway.proxy.rlwy.net:56584")
db = mongo_client["carbon_ai_bot"]
users_collection = db["users"]
codes_collection = db["codes"]

# Constants - Persian translations
WELCOME_MESSAGE = "🌟 به ربات چند منظوره کربن خوش آمدید! 🌟"
COIN_STATUS = "💰 سکه های شما: {}"
DAILY_COLLECTED = "✅ سکه روزانه شما دریافت شد! +1 سکه"
ALREADY_COLLECTED = "⚠️ شما امروز سکه روزانه خود را دریافت کرده اید."
NOT_ENOUGH_COINS = "⚠️ سکه کافی ندارید! لطفا سکه دریافت کنید."
CODE_REDEEMED = "✅ کد هدیه با موفقیت استفاده شد! +{} سکه"
INVALID_CODE = "❌ کد نامعتبر یا منقضی شده است."
ENTER_CODE = "🎁 لطفا کد هدیه خود را وارد کنید:"
ENTER_TEXT_TRANSLATE_EN_TO_FA = "🇺🇸➡️🇮🇷 لطفا متن انگلیسی برای ترجمه وارد کنید:"
ENTER_TEXT_TRANSLATE_FA_TO_EN = "🇮🇷➡️🇺🇸 لطفا متن فارسی برای ترجمه وارد کنید:"
TRANSLATED_BY = "ترجمه شده توسط کربن AI"

# User state dictionary
user_states = {}

# Create or get user
def get_or_create_user(user_id):
    user = users_collection.find_one({"user_id": user_id})
    if not user:
        user = {
            "user_id": user_id,
            "coins": 5,
            "last_daily": None
        }
        users_collection.insert_one(user)
    return user

# Generate unique code
def generate_code(length=8, coins=5):
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
    while codes_collection.find_one({"code": code}):
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=length))
    
    codes_collection.insert_one({
        "code": code,
        "coins": coins,
        "is_used": False,
        "created_at": datetime.datetime.now()
    })
    return code

# Check if user can claim daily coins
def can_claim_daily(user):
    if user["last_daily"] is None:
        return True
    
    last_daily = user["last_daily"]
    today = datetime.datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    return last_daily < today

# Check if user has enough coins and deduct
def use_coin(user_id):
    user = get_or_create_user(user_id)
    if user["coins"] > 0:
        users_collection.update_one(
            {"user_id": user_id},
            {"$inc": {"coins": -1}}
        )
        return True
    return False

# Create keyboard markup
def create_markup(keyboard):
    return {
        "keyboard": keyboard,
        "resize_keyboard": True,
        "one_time_keyboard": False
    }

# Main menu keyboard
def main_menu_keyboard():
    return create_markup([
        ["🇺🇸➡️🇮🇷 انگلیسی به فارسی", "🇮🇷➡️🇺🇸 فارسی به انگلیسی"],
        ["💰 دریافت سکه روزانه", "🎁 استفاده از کد هدیه"],
        ["👤 حساب کاربری"]
    ])

# Back keyboard
def back_keyboard():
    return create_markup([["🔙 بازگشت به منوی اصلی"]])

# Send message function
def send_message(chat_id, text, reply_markup=None, parse_mode="HTML"):
    data = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": parse_mode
    }
    
    if reply_markup:
        data["reply_markup"] = json.dumps(reply_markup)
    
    response = requests.post(f"{BASE_URL}/sendMessage", data=data)
    return response.json()

# Translate text using Google Translate API with HTTP requests
def translate_text(text, source_lang, target_lang):
    url = "https://translate.googleapis.com/translate_a/single"
    params = {
        "client": "gtx",
        "sl": source_lang,
        "tl": target_lang,
        "dt": "t",
        "q": text
    }
    
    response = requests.get(url, params=params)
    
    if response.status_code == 200:
        try:
            result = response.json()
            translated_text = ""
            for sentence in result[0]:
                if sentence[0]:
                    translated_text += sentence[0]
            return translated_text
        except Exception as e:
            print(f"Translation error: {e}")
            return "Error in translation"
    else:
        return "Error in translation request"

# Process updates
def process_updates(updates):
    for update in updates:
        if "message" in update:
            message = update["message"]
            chat_id = message["chat"]["id"]
            user_id = message["from"]["id"]
            
            # Get user from database
            user = get_or_create_user(user_id)
            
            if "text" in message:
                text = message["text"]
                process_message(user_id, chat_id, text)

# Process message
def process_message(user_id, chat_id, text):
    user_state = user_states.get(user_id, "main")
    
    # Back to main menu
    if text == "🔙 بازگشت به منوی اصلی":
        user_states[user_id] = "main"
        send_message(
            chat_id, 
            f"{WELCOME_MESSAGE}\n\n{COIN_STATUS.format(get_or_create_user(user_id)['coins'])}",
            main_menu_keyboard()
        )
        return
        
    # Main menu options
    if user_state == "main":
        if text == "/start":
            send_message(
                chat_id, 
                f"{WELCOME_MESSAGE}\n\n{COIN_STATUS.format(get_or_create_user(user_id)['coins'])}",
                main_menu_keyboard()
            )
        
        elif text == "🇺🇸➡️🇮🇷 انگلیسی به فارسی":
            user_states[user_id] = "en_to_fa"
            send_message(chat_id, ENTER_TEXT_TRANSLATE_EN_TO_FA, back_keyboard())
            
        elif text == "🇮🇷➡️🇺🇸 فارسی به انگلیسی":
            user_states[user_id] = "fa_to_en"
            send_message(chat_id, ENTER_TEXT_TRANSLATE_FA_TO_EN, back_keyboard())
            
        elif text == "💰 دریافت سکه روزانه":
            user = get_or_create_user(user_id)
            
            if can_claim_daily(user):
                users_collection.update_one(
                    {"user_id": user_id},
                    {
                        "$inc": {"coins": 1},
                        "$set": {"last_daily": datetime.datetime.now()}
                    }
                )
                send_message(
                    chat_id, 
                    f"{DAILY_COLLECTED}\n\n{COIN_STATUS.format(user['coins'] + 1)}",
                    main_menu_keyboard()
                )
            else:
                send_message(
                    chat_id, 
                    f"{ALREADY_COLLECTED}\n\n{COIN_STATUS.format(user['coins'])}",
                    main_menu_keyboard()
                )
                
        elif text == "🎁 استفاده از کد هدیه":
            user_states[user_id] = "redeem_code"
            send_message(chat_id, ENTER_CODE, back_keyboard())
            
        elif text == "👤 حساب کاربری":
            user = get_or_create_user(user_id)
            account_info = f"👤 <b>حساب کاربری شما</b>\n\n"
            account_info += f"🆔 شناسه کاربری: <code>{user_id}</code>\n"
            account_info += f"💰 سکه های شما: <b>{user['coins']}</b>\n"
            
            if user["last_daily"]:
                account_info += f"📅 آخرین دریافت سکه روزانه: <b>{user['last_daily'].strftime('%Y-%m-%d')}</b>"
            
            send_message(chat_id, account_info, main_menu_keyboard())
    
    # English to Persian translation
    elif user_state == "en_to_fa":
        if use_coin(user_id):
            translated = translate_text(text, "en", "fa")
            response = f"🇺🇸➡️🇮🇷 <b>ترجمه:</b>\n\n{translated}\n\n<i>{TRANSLATED_BY}</i>"
            send_message(chat_id, response, back_keyboard())
        else:
            send_message(chat_id, NOT_ENOUGH_COINS, main_menu_keyboard())
            user_states[user_id] = "main"
    
    # Persian to English translation
    elif user_state == "fa_to_en":
        if use_coin(user_id):
            translated = translate_text(text, "fa", "en")
            response = f"🇮🇷➡️🇺🇸 <b>Translation:</b>\n\n{translated}\n\n<i>{TRANSLATED_BY}</i>"
            send_message(chat_id, response, back_keyboard())
        else:
            send_message(chat_id, NOT_ENOUGH_COINS, main_menu_keyboard())
            user_states[user_id] = "main"
    
    # Redeem code
    elif user_state == "redeem_code":
        code = text.strip().upper()
        code_doc = codes_collection.find_one({"code": code, "is_used": False})
        
        if code_doc:
            coin_amount = code_doc["coins"]
            
            # Update code status
            codes_collection.update_one(
                {"code": code},
                {"$set": {"is_used": True, "used_by": user_id, "used_at": datetime.datetime.now()}}
            )
            
            # Add coins to user
            users_collection.update_one(
                {"user_id": user_id},
                {"$inc": {"coins": coin_amount}}
            )
            
            user = get_or_create_user(user_id)
            send_message(
                chat_id, 
                f"{CODE_REDEEMED.format(coin_amount)}\n\n{COIN_STATUS.format(user['coins'] + coin_amount)}",
                main_menu_keyboard()
            )
        else:
            send_message(chat_id, INVALID_CODE, back_keyboard())
        
        user_states[user_id] = "main"

# Long polling function
def start_bot():
    print("Bot started...")
    offset = None
    
    while True:
        try:
            params = {"timeout": 30}
            if offset:
                params["offset"] = offset
                
            response = requests.get(f"{BASE_URL}/getUpdates", params=params)
            updates = response.json().get("result", [])
            
            if updates:
                offset = updates[-1]["update_id"] + 1
                process_updates(updates)
                
        except Exception as e:
            print(f"Error in polling: {e}")
            time.sleep(3)

# Admin function to generate gift codes (can be called from shell)
def admin_generate_codes(count=5, coins_per_code=3):
    codes = []
    for _ in range(count):
        code = generate_code(coins=coins_per_code)
        codes.append(code)
    return codes

# Main execution
if __name__ == "__main__":
    # Start the bot
    start_bot()
