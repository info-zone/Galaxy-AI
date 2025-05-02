import requests
import json
import time
import threading
import random
import string
from datetime import datetime, timedelta
from pymongo import MongoClient

# Bot Configuration
BOT_TOKEN = "2109246071:LvlHCpvSkjpD8rFw1N4lNcaJmKP5EyCxgUNp6euX"
BASE_URL = f"https://tapi.bale.ai/bot{BOT_TOKEN}"
ADMIN_USERNAMES = ["zonercm"]  # Add admin usernames here

# MongoDB Configuration
mongo_client = MongoClient('mongodb://mongo:iOaGntNtUjrGOVEEfkVxVZArKMTLpfiT@tramway.proxy.rlwy.net:56584)
db = mongo_client['carbon_ai_bot']
users_collection = db['users']
codes_collection = db['codes']
daily_claims_collection = db['daily_claims']

# Keyboard Layouts
main_keyboard = {
    "keyboard": [
        ["🔄 فارسی ← انگلیسی", "🔄 انگلیسی ← فارسی"],
        ["💰 سکه های روزانه", "🎁 کد هدیه"],
        ["👤 اطلاعات حساب"]
    ],
    "resize_keyboard": True
}

back_keyboard = {
    "keyboard": [
        ["🔙 بازگشت"]
    ],
    "resize_keyboard": True
}

# Initialize the bot
def send_message(chat_id, text, reply_markup=None, reply_to_message_id=None):
    url = f"{BASE_URL}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "reply_to_message_id": reply_to_message_id
    }
    
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
        
    response = requests.post(url, json=payload)
    return response.json()

def send_photo(chat_id, photo, caption=None, reply_markup=None):
    url = f"{BASE_URL}/sendPhoto"
    files = {'photo': photo}
    payload = {
        "chat_id": chat_id,
        "parse_mode": "HTML"
    }
    
    if caption:
        payload["caption"] = caption
        
    if reply_markup:
        payload["reply_markup"] = json.dumps(reply_markup)
        
    response = requests.post(url, data=payload, files=files)
    return response.json()

def get_updates(offset=None, timeout=30):
    url = f"{BASE_URL}/getUpdates"
    params = {"timeout": timeout}
    if offset:
        params["offset"] = offset
    response = requests.get(url, params=params)
    return response.json()

# User Management
def get_user(user_id):
    user = users_collection.find_one({"user_id": user_id})
    if not user:
        # Create new user with default 5 coins
        user = {
            "user_id": user_id,
            "coins": 5,
            "username": "",
            "first_name": "",
            "last_interaction": datetime.now()
        }
        users_collection.insert_one(user)
    return user

def update_user_info(user_id, username, first_name):
    users_collection.update_one(
        {"user_id": user_id},
        {"$set": {"username": username, "first_name": first_name, "last_interaction": datetime.now()}}
    )

def use_coin(user_id):
    result = users_collection.update_one(
        {"user_id": user_id, "coins": {"$gt": 0}},
        {"$inc": {"coins": -1}}
    )
    return result.modified_count > 0

def add_coins(user_id, amount):
    users_collection.update_one(
        {"user_id": user_id},
        {"$inc": {"coins": amount}}
    )

# Daily Coin System
def claim_daily_coin(user_id):
    today = datetime.now().date()
    last_claim = daily_claims_collection.find_one({"user_id": user_id})
    
    if last_claim:
        last_claim_date = last_claim["claim_date"].date()
        if last_claim_date == today:
            return False, "⚠️ شما امروز سکه روزانه خود را دریافت کرده‌اید. فردا دوباره تلاش کنید."
    
    # Add coin and record claim
    add_coins(user_id, 1)
    daily_claims_collection.update_one(
        {"user_id": user_id},
        {"$set": {"claim_date": datetime.now()}},
        upsert=True
    )
    return True, "✅ تبریک! یک سکه روزانه به حساب شما اضافه شد."

# Gift Code System
def generate_code(count=1, expiry_days=7):
    codes = []
    for _ in range(count):
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        codes_collection.insert_one({
            "code": code,
            "is_used": False,
            "created_at": datetime.now(),
            "expires_at": datetime.now() + timedelta(days=expiry_days)
        })
        codes.append(code)
    return codes

def redeem_code(user_id, code):
    code_doc = codes_collection.find_one({
        "code": code,
        "is_used": False,
        "expires_at": {"$gt": datetime.now()}
    })
    
    if not code_doc:
        return False, "⚠️ کد نامعتبر یا منقضی شده است."
    
    # Mark code as used
    codes_collection.update_one(
        {"_id": code_doc["_id"]},
        {"$set": {"is_used": True, "used_by": user_id, "used_at": datetime.now()}}
    )
    
    # Add 3 coins to user
    add_coins(user_id, 3)
    return True, "🎉 تبریک! کد هدیه با موفقیت استفاده شد و 3 سکه به حساب شما اضافه شد."

# Translation Service
def translate_text(text, target_lang):
    url = "https://translate.googleapis.com/translate_a/single"
    params = {
        "client": "gtx",
        "sl": "auto",
        "tl": target_lang,
        "dt": "t",
        "q": text
    }
    
    response = requests.get(url, params=params)
    if response.status_code == 200:
        try:
            result = response.json()
            translated_text = ''.join([sentence[0] for sentence in result[0]])
            return translated_text
        except:
            return "❌ خطا در ترجمه متن. لطفا دوباره تلاش کنید."
    else:
        return "❌ خطا در ارتباط با سرویس ترجمه. لطفا دوباره تلاش کنید."

# Admin Functions
def generate_admin_keyboard(user_id):
    user = get_user(user_id)
    username = user.get('username', '')
    
    # Check if user is admin
    is_admin = username in ADMIN_USERNAMES
    
    keyboard = {
        "keyboard": [
            ["🔄 فارسی ← انگلیسی", "🔄 انگلیسی ← فارسی"],
            ["💰 سکه های روزانه", "🎁 کد هدیه"],
            ["👤 اطلاعات حساب"]
        ],
        "resize_keyboard": True
    }
    
    if is_admin:
        keyboard["keyboard"].append(["👑 پنل مدیریت"])
    
    return keyboard

def admin_panel_keyboard():
    return {
        "keyboard": [
            ["📢 ارسال پیام عمومی", "📊 آمار کاربران"],
            ["🎁 ساخت کد هدیه", "💰 افزودن سکه"],
            ["📸 ارسال تصویر عمومی"],
            ["🔙 بازگشت"]
        ],
        "resize_keyboard": True
    }

def broadcast_message(message):
    all_users = users_collection.find({})
    success_count = 0
    
    for user in all_users:
        try:
            send_message(user["user_id"], message)
            success_count += 1
        except:
            pass
        time.sleep(0.1)  # To avoid hitting rate limits
        
    return success_count

def broadcast_photo(photo_file, caption=None):
    all_users = users_collection.find({})
    success_count = 0
    
    for user in all_users:
        try:
            send_photo(user["user_id"], photo_file, caption)
            success_count += 1
        except:
            pass
        time.sleep(0.1)  # To avoid hitting rate limits
        
    return success_count

# Message Handler
def process_message(message):
    chat_id = message.get("chat", {}).get("id")
    text = message.get("text", "")
    user_id = message.get("from", {}).get("id")
    username = message.get("from", {}).get("username", "")
    first_name = message.get("from", {}).get("first_name", "")
    message_id = message.get("message_id")
    
    # Update user info
    update_user_info(user_id, username, first_name)
    user = get_user(user_id)
    
    # Check if user is admin
    is_admin = username in ADMIN_USERNAMES
    
    # Start command
    if text == "/start":
        welcome_message = (
            f"✨ سلام <b>{first_name}</b> عزیز!\n\n"
            f"به ربات چندکاره <b>کربن</b> خوش آمدید! 🤖\n\n"
            f"💎 امکانات ربات:\n"
            f"• ترجمه سریع متن بین فارسی و انگلیسی\n"
            f"• دریافت سکه روزانه\n"
            f"• استفاده از کدهای هدیه\n\n"
            f"هر تراکنش نیاز به یک سکه دارد. شما هم‌اکنون {user['coins']} سکه دارید."
        )
        send_message(chat_id, welcome_message, generate_admin_keyboard(user_id))
        return

    # Main Menu Options
    if text == "🔙 بازگشت":
        send_message(chat_id, "🏠 به منوی اصلی بازگشتید.", generate_admin_keyboard(user_id))
        return
        
    elif text == "🔄 فارسی ← انگلیسی":
        send_message(
            chat_id, 
            "🔤 لطفا متن فارسی خود را برای ترجمه به انگلیسی ارسال کنید:", 
            back_keyboard
        )
        users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"state": "waiting_fa_text"}}
        )
        return
        
    elif text == "🔄 انگلیسی ← فارسی":
        send_message(
            chat_id, 
            "🔤 Please send your English text to translate to Persian:", 
            back_keyboard
        )
        users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"state": "waiting_en_text"}}
        )
        return
        
    elif text == "💰 سکه های روزانه":
        success, message = claim_daily_coin(user_id)
        updated_user = get_user(user_id)
        response = f"{message}\n\n💰 تعداد سکه‌های فعلی شما: {updated_user['coins']}"
        send_message(chat_id, response, generate_admin_keyboard(user_id))
        return
        
    elif text == "🎁 کد هدیه":
        send_message(
            chat_id, 
            "🎟️ لطفا کد هدیه خود را وارد کنید:", 
            back_keyboard
        )
        users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"state": "waiting_code"}}
        )
        return
        
    elif text == "👤 اطلاعات حساب":
        info_message = (
            f"👤 <b>اطلاعات حساب شما</b>\n\n"
            f"🆔 شناسه کاربری: <code>{user_id}</code>\n"
            f"👤 نام: {first_name}\n"
        )
        
        if username:
            info_message += f"📝 نام کاربری: @{username}\n"
            
        info_message += f"💰 سکه‌ها: {user['coins']}\n"
        
        last_claim = daily_claims_collection.find_one({"user_id": user_id})
        if last_claim:
            last_claim_date = last_claim["claim_date"].strftime("%Y-%m-%d")
            info_message += f"📅 آخرین دریافت سکه روزانه: {last_claim_date}\n"
        
        send_message(chat_id, info_message, generate_admin_keyboard(user_id))
        return
    
    # Admin Panel
    elif text == "👑 پنل مدیریت":
        if is_admin:
            admin_message = (
                f"👑 <b>پنل مدیریت</b>\n\n"
                f"خوش آمدید ادمین عزیز!\n"
                f"لطفا یکی از گزینه‌های زیر را انتخاب کنید:"
            )
            send_message(chat_id, admin_message, admin_panel_keyboard())
        else:
            # Non-admin users trying to access admin panel
            help_message = (
                "❓ <b>راهنمای ربات</b>\n\n"
                "برای استفاده از ربات، یکی از گزینه‌های موجود در منو را انتخاب کنید.\n\n"
                "💡 تعداد سکه‌های فعلی شما: " + str(user['coins'])
            )
            send_message(chat_id, help_message, generate_admin_keyboard(user_id))
        return
        
    elif text == "📢 ارسال پیام عمومی":
        if is_admin:
            send_message(
                chat_id, 
                "📢 لطفا پیامی که می‌خواهید به تمام کاربران ارسال شود را وارد کنید:", 
                back_keyboard
            )
            users_collection.update_one(
                {"user_id": user_id},
                {"$set": {"state": "waiting_broadcast_message"}}
            )
        else:
            help_message = (
                "❓ <b>راهنمای ربات</b>\n\n"
                "برای استفاده از ربات، یکی از گزینه‌های موجود در منو را انتخاب کنید.\n\n"
                "💡 تعداد سکه‌های فعلی شما: " + str(user['coins'])
            )
            send_message(chat_id, help_message, generate_admin_keyboard(user_id))
        return
        
    elif text == "📊 آمار کاربران":
        if is_admin:
            total_users = users_collection.count_documents({})
            active_today = users_collection.count_documents({
                "last_interaction": {"$gte": datetime.now() - timedelta(days=1)}
            })
            total_coins = sum([user.get("coins", 0) for user in users_collection.find({})])
            
            stats_message = (
                f"📊 <b>آمار ربات</b>\n\n"
                f"👥 تعداد کل کاربران: {total_users}\n"
                f"🟢 کاربران فعال امروز: {active_today}\n"
                f"💰 مجموع سکه‌های موجود: {total_coins}\n"
            )
            send_message(chat_id, stats_message, admin_panel_keyboard())
        else:
            help_message = (
                "❓ <b>راهنمای ربات</b>\n\n"
                "برای استفاده از ربات، یکی از گزینه‌های موجود در منو را انتخاب کنید.\n\n"
                "💡 تعداد سکه‌های فعلی شما: " + str(user['coins'])
            )
            send_message(chat_id, help_message, generate_admin_keyboard(user_id))
        return
        
    elif text == "🎁 ساخت کد هدیه":
        if is_admin:
            send_message(
                chat_id, 
                "🎁 لطفا تعداد کدهای هدیه مورد نظر را وارد کنید (حداکثر 10):", 
                back_keyboard
            )
            users_collection.update_one(
                {"user_id": user_id},
                {"$set": {"state": "waiting_code_count"}}
            )
        else:
            help_message = (
                "❓ <b>راهنمای ربات</b>\n\n"
                "برای استفاده از ربات، یکی از گزینه‌های موجود در منو را انتخاب کنید.\n\n"
                "💡 تعداد سکه‌های فعلی شما: " + str(user['coins'])
            )
            send_message(chat_id, help_message, generate_admin_keyboard(user_id))
        return
        
    elif text == "💰 افزودن سکه":
        if is_admin:
            send_message(
                chat_id, 
                "💰 لطفا شناسه کاربر و تعداد سکه را به صورت زیر وارد کنید:\n<code>user_id amount</code>\nمثال: <code>123456789 5</code>", 
                back_keyboard
            )
            users_collection.update_one(
                {"user_id": user_id},
                {"$set": {"state": "waiting_add_coins"}}
            )
        else:
            help_message = (
                "❓ <b>راهنمای ربات</b>\n\n"
                "برای استفاده از ربات، یکی از گزینه‌های موجود در منو را انتخاب کنید.\n\n"
                "💡 تعداد سکه‌های فعلی شما: " + str(user['coins'])
            )
            send_message(chat_id, help_message, generate_admin_keyboard(user_id))
        return
        
    elif text == "📸 ارسال تصویر عمومی":
        send_message(
            chat_id, 
            "📸 لطفا تصویر مورد نظر را همراه با توضیحات (Caption) ارسال کنید:", 
            back_keyboard
        )
        users_collection.update_one(
            {"user_id": user_id},
            {"$set": {"state": "waiting_broadcast_photo"}}
        )
        return
    
    # Process states
    user_state = user.get("state", "")
    
    # Translation states
    if user_state == "waiting_fa_text":
        if not use_coin(user_id):
            send_message(
                chat_id, 
                "⚠️ سکه‌های شما کافی نیست! لطفا از طریق سکه روزانه یا کد هدیه، سکه دریافت کنید.", 
                generate_admin_keyboard(user_id)
            )
            users_collection.update_one(
                {"user_id": user_id},
                {"$unset": {"state": ""}}
            )
            return
            
        translated = translate_text(text, "en")
        response = (
            f"🔄 <b>ترجمه به انگلیسی:</b>\n\n"
            f"{translated}\n\n"
            f"<i>ترجمه شده توسط هوش مصنوعی کربن</i>"
        )
        send_message(chat_id, response, back_keyboard, message_id)
        return
        
    elif user_state == "waiting_en_text":
        if not use_coin(user_id):
            send_message(
                chat_id, 
                "⚠️ سکه‌های شما کافی نیست! لطفا از طریق سکه روزانه یا کد هدیه، سکه دریافت کنید.", 
                generate_admin_keyboard(user_id)
            )
            users_collection.update_one(
                {"user_id": user_id},
                {"$unset": {"state": ""}}
            )
            return
            
        translated = translate_text(text, "fa")
        response = (
            f"🔄 <b>ترجمه به فارسی:</b>\n\n"
            f"{translated}\n\n"
            f"<i>ترجمه شده توسط هوش مصنوعی کربن</i>"
        )
        send_message(chat_id, response, back_keyboard, message_id)
        return
    
    # Code redemption
    elif user_state == "waiting_code":
        success, message = redeem_code(user_id, text.strip().upper())
        updated_user = get_user(user_id)
        response = f"{message}\n\n💰 تعداد سکه‌های فعلی شما: {updated_user['coins']}"
        
        users_collection.update_one(
            {"user_id": user_id},
            {"$unset": {"state": ""}}
        )
        
        send_message(chat_id, response, generate_admin_keyboard(user_id))
        return
    
    # Admin states
    elif user_state == "waiting_broadcast_message":
        if is_admin:
            send_message(chat_id, "📤 در حال ارسال پیام به کاربران...")
            success_count = broadcast_message(text)
            
            users_collection.update_one(
                {"user_id": user_id},
                {"$unset": {"state": ""}}
            )
            
            send_message(
                chat_id, 
                f"✅ پیام با موفقیت به {success_count} کاربر ارسال شد.", 
                admin_panel_keyboard()
            )
        else:
            users_collection.update_one(
                {"user_id": user_id},
                {"$unset": {"state": ""}}
            )
            
            help_message = (
                "❓ <b>راهنمای ربات</b>\n\n"
                "برای استفاده از ربات، یکی از گزینه‌های موجود در منو را انتخاب کنید.\n\n"
                "💡 تعداد سکه‌های فعلی شما: " + str(user['coins'])
            )
            send_message(chat_id, help_message, generate_admin_keyboard(user_id))
        return
        
    elif user_state == "waiting_code_count":
        if is_admin:
            try:
                count = int(text.strip())
                if count < 1 or count > 10:
                    raise ValueError()
                    
                codes = generate_code(count)
                codes_text = "\n".join([f"<code>{code}</code>" for code in codes])
                
                response = (
                    f"✅ {count} کد هدیه با موفقیت ایجاد شد:\n\n"
                    f"{codes_text}\n\n"
                    f"این کدها به مدت 7 روز معتبر هستند."
                )
                
                users_collection.update_one(
                    {"user_id": user_id},
                    {"$unset": {"state": ""}}
                )
                
                send_message(chat_id, response, admin_panel_keyboard())
                
            except:
                send_message(
                    chat_id, 
                    "⚠️ لطفا یک عدد معتبر بین 1 تا 10 وارد کنید.", 
                    back_keyboard
                )
        else:
            users_collection.update_one(
                {"user_id": user_id},
                {"$unset": {"state": ""}}
            )
            
            help_message = (
                "❓ <b>راهنمای ربات</b>\n\n"
                "برای استفاده از ربات، یکی از گزینه‌های موجود در منو را انتخاب کنید.\n\n"
                "💡 تعداد سکه‌های فعلی شما: " + str(user['coins'])
            )
            send_message(chat_id, help_message, generate_admin_keyboard(user_id))
        return
        
    elif user_state == "waiting_add_coins":
        try:
            parts = text.strip().split()
            target_user_id = int(parts[0])
            amount = int(parts[1])
            
            if amount < 1 or amount > 100:
                raise ValueError("Amount must be between 1 and 100")
                
            add_coins(target_user_id, amount)
            target_user = get_user(target_user_id)
            
            users_collection.update_one(
                {"user_id": user_id},
                {"$unset": {"state": ""}}
            )
            
            response = (
                f"✅ تعداد {amount} سکه با موفقیت به کاربر با شناسه {target_user_id} اضافه شد.\n"
                f"تعداد سکه‌های فعلی کاربر: {target_user['coins']}"
            )
            
            send_message(chat_id, response, admin_panel_keyboard())
            
        except Exception as e:
            send_message(
                chat_id, 
                f"⚠️ خطا در افزودن سکه. لطفا فرمت درست را وارد کنید.", 
                back_keyboard
            )
        return
    
    # Default response if message doesn't match any command or state
    help_message = (
        "❓ <b>راهنمای ربات</b>\n\n"
        "برای استفاده از ربات، یکی از گزینه‌های موجود در منو را انتخاב کنید.\n\n"
        "💡 تعداد سکه‌های فعلی شما: " + str(user['coins'])
    )
    send_message(chat_id, help_message, generate_admin_keyboard(user_id))

# Photo Handler
def process_photo(message):
    chat_id = message.get("chat", {}).get("id")
    user_id = message.get("from", {}).get("id")
    username = message.get("from", {}).get("username", "")
    
    # Check if user is admin
    is_admin = username in ADMIN_USERNAMES
    
    # Get user state
    user = get_user(user_id)
    user_state = user.get("state", "")
    
    # Admin broadcasting photo
    if user_state == "waiting_broadcast_photo" and is_admin:
        # Get photo file_id (largest size)
        photos = message.get("photo", [])
        if not photos:
            send_message(chat_id, "⚠️ لطفا یک تصویر معتبر ارسال کنید.", back_keyboard)
            return
            
        file_id = photos[-1].get("file_id")
        caption = message.get("caption", "")
        
        # Get file path
        file_path_response = requests.get(f"{BASE_URL}/getFile?file_id={file_id}").json()
        if not file_path_response.get("ok"):
            send_message(chat_id, "⚠️ خطا در دریافت تصویر. لطفا دوباره تلاش کنید.", back_keyboard)
            return
            
        file_path = file_path_response.get("result", {}).get("file_path")
        file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
        
        # Download photo
        photo_data = requests.get(file_url).content
        
        send_message(chat_id, "📤 در حال ارسال تصویر به کاربران...")
        
        # Broadcast photo
        with open("temp_photo.jpg", "wb") as f:
            f.write(photo_data)
            
        with open("temp_photo.jpg", "rb") as photo_file:
            success_count = broadcast_photo(photo_file, caption)
        
        users_collection.update_one(
            {"user_id": user_id},
            {"$unset": {"state": ""}}
        )
        
        send_message(
            chat_id, 
            f"✅ تصویر با موفقیت به {success_count} کاربر ارسال شد.", 
            admin_panel_keyboard()
        )
        return
    
    # Default response for photos
    send_message(
        chat_id, 
        "📸 تصویر شما دریافت شد. هم‌اکنون قادر به پردازش تصاویر نیستیم.", 
        generate_admin_keyboard(user_id)
    )

# Main Bot Loop
def main():
    print("🤖 Carbon AI Bot is running...")
    offset = None
    
    while True:
        try:
            updates = get_updates(offset, timeout=30)
            
            if updates.get("ok") and updates.get("result"):
                for update in updates["result"]:
                    offset = update["update_id"] + 1
                    
                    # Process message updates
                    if "message" in update:
                        message = update["message"]
                        
                        # Handle text messages
                        if "text" in message:
                            threading.Thread(target=process_message, args=(message,)).start()
                        
                        # Handle photo messages
                        elif "photo" in message:
                            threading.Thread(target=process_photo, args=(message,)).start()
            
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)

if __name__ == "__main__":
    main()
