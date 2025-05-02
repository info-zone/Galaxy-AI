import requests
import json
import time
from pymongo import MongoClient
from datetime import datetime, timedelta
import random
import string

# MongoDB setup
client = MongoClient('mongodb://mongo:iOaGntNtUjrGOVEEfkVxVZArKMTLpfiT@tramway.proxy.rlwy.net:56584')
db = client['telegram_bot']
users_collection = db['users']
coin_codes_collection = db['coin_codes']
admin_usernames = ['admin1', 'admin2']  # Replace with actual admin usernames

# Bot configuration
BOT_TOKEN = '2109246071:LvlHCpvSkjpD8rFw1N4lNcaJmKP5EyCxgUNp6euX'
API_URL = f'https://tapi.bale.ai/bot{BOT_TOKEN}/'
LAST_UPDATE_ID = 0

# Translation directions
PERSIAN_TO_ENGLISH = 'فارسی←انگلیسی'
ENGLISH_TO_PERSIAN = 'انگلیسی ← فارسی'
BACK_BUTTON = '🔙 بازگشت'

# Keyboard layouts
MAIN_KEYBOARD = {
    'keyboard': [
        [PERSIAN_TO_ENGLISH, ENGLISH_TO_PERSIAN],
        ['💰 کیف پول', '🎫 کد سکه'],
        ['ℹ️ اطلاعات حساب']
    ],
    'resize_keyboard': True
}

if admin_usernames:
    MAIN_KEYBOARD['keyboard'].append(['👑 پنل ادمین'])

WALLET_KEYBOARD = {
    'keyboard': [
        ['🎁 سکه روزانه'],
        [BACK_BUTTON]
    ],
    'resize_keyboard': True
}

ADMIN_KEYBOARD = {
    'keyboard': [
        ['📢 ارسال پیام به همه'],
        ['🖼 ارسال عکس به همه'],
        ['📝 ارسال عکس با کپشن'],
        ['🎟 ایجاد کد سکه'],
        ['📊 آمار کاربران'],
        [BACK_BUTTON]
    ],
    'resize_keyboard': True
}

def translate_text(text, target_language):
    """Translate text using Google Translate API"""
    url = "https://translate.googleapis.com/translate_a/single"
    params = {
        'client': 'gtx',
        'sl': 'auto',
        'tl': target_language,
        'dt': 't',
        'q': text
    }
    
    try:
        response = requests.get(url, params=params)
        if response.status_code == 200:
            result = response.json()
            translated_text = result[0][0][0]
            return translated_text
        return None
    except:
        return None

def get_user(user_id):
    """Get or create user in database"""
    user = users_collection.find_one({'user_id': user_id})
    if not user:
        user = {
            'user_id': user_id,
            'coins': 5,
            'last_daily_coin': None,
            'username': '',
            'first_name': '',
            'last_name': '',
            'created_at': datetime.now()
        }
        users_collection.insert_one(user)
    return user

def update_user(user_id, update_data):
    """Update user data"""
    users_collection.update_one({'user_id': user_id}, {'$set': update_data})

def can_get_daily_coin(user_id):
    """Check if user can get daily coin"""
    user = get_user(user_id)
    if not user.get('last_daily_coin'):
        return True
    
    last_claim = user['last_daily_coin']
    now = datetime.now()
    return (now - last_claim) >= timedelta(hours=24)

def generate_coin_code(amount=1):
    """Generate a new coin code"""
    code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
    coin_codes_collection.insert_one({
        'code': code,
        'amount': amount,
        'used': False,
        'created_at': datetime.now()
    })
    return code

def redeem_coin_code(user_id, code):
    """Redeem a coin code"""
    code_data = coin_codes_collection.find_one({'code': code})
    if not code_data:
        return False, "کد نامعتبر است ❌"
    
    if code_data['used']:
        return False, "این کد قبلاً استفاده شده است ⚠️"
    
    # Update code status
    coin_codes_collection.update_one(
        {'code': code},
        {'$set': {'used': True, 'used_by': user_id, 'used_at': datetime.now()}}
    )
    
    # Add coins to user
    user = get_user(user_id)
    new_coins = user['coins'] + code_data['amount']
    update_user(user_id, {'coins': new_coins})
    
    return True, f"🎉 {code_data['amount']} سکه به کیف پول شما اضافه شد!"

def send_message(chat_id, text, reply_markup=None, parse_mode='HTML'):
    """Send message to Telegram chat"""
    payload = {
        'chat_id': chat_id,
        'text': text,
        'parse_mode': parse_mode
    }
    if reply_markup:
        payload['reply_markup'] = json.dumps(reply_markup)
    
    response = requests.post(API_URL + 'sendMessage', json=payload)
    return response.json()

def send_photo(chat_id, photo_url, caption=None, reply_markup=None):
    """Send photo to Telegram chat"""
    payload = {
        'chat_id': chat_id,
        'photo': photo_url
    }
    if caption:
        payload['caption'] = caption
    if reply_markup:
        payload['reply_markup'] = json.dumps(reply_markup)
    
    response = requests.post(API_URL + 'sendPhoto', json=payload)
    return response.json()

def get_updates(offset=None):
    """Get updates from Telegram"""
    params = {'timeout': 10}
    if offset:
        params['offset'] = offset
    response = requests.get(API_URL + 'getUpdates', params=params)
    return response.json().get('result', [])

def handle_message(update):
    """Handle incoming message"""
    global LAST_UPDATE_ID
    
    message = update.get('message')
    if not message:
        return
    
    chat_id = message['chat']['id']
    user_id = message['from']['id']
    text = message.get('text', '')
    username = message['from'].get('username', '')
    first_name = message['from'].get('first_name', '')
    last_name = message['from'].get('last_name', '')
    
    # Update user info
    update_user(user_id, {
        'username': username,
        'first_name': first_name,
        'last_name': last_name
    })
    
    user = get_user(user_id)
    
    # Admin panel check
    if text == '👑 پنل ادمین':
        if username in admin_usernames:
            send_message(chat_id, "👑 به پنل ادمین خوش آمدید", ADMIN_KEYBOARD)
        else:
            send_message(chat_id, "⛔️ شما دسترسی ادمین ندارید", MAIN_KEYBOARD)
        return
    
    # Handle admin commands
    if username in admin_usernames and text.startswith('/admin'):
        handle_admin_command(chat_id, text)
        return
    
    # Main menu commands
    if text == '💰 کیف پول':
        wallet_text = f"""
💰 <b>کیف پول شما</b> 💰

🪙 سکه‌ها: <b>{user['coins']}</b>
🎁 سکه روزانه: {'✅ آماده دریافت' if can_get_daily_coin(user_id) else '⏳ لطفاً صبر کنید'}
        """
        send_message(chat_id, wallet_text, WALLET_KEYBOARD)
        return
    
    if text == '🎁 سکه روزانه':
        if can_get_daily_coin(user_id):
            new_coins = user['coins'] + 1
            update_user(user_id, {
                'coins': new_coins,
                'last_daily_coin': datetime.now()
            })
            send_message(chat_id, f"🎉 1 سکه به کیف پول شما اضافه شد! مجموع سکه‌ها: {new_coins}", WALLET_KEYBOARD)
        else:
            last_claim = user.get('last_daily_coin', datetime.now())
            next_claim = last_claim + timedelta(hours=24)
            remaining = next_claim - datetime.now()
            hours = remaining.seconds // 3600
            minutes = (remaining.seconds % 3600) // 60
            send_message(chat_id, f"⏳ شما می‌توانید بعد از {hours} ساعت و {minutes} دقیقه سکه روزانه دریافت کنید.", WALLET_KEYBOARD)
        return
    
    if text == '🎫 کد سکه':
        send_message(chat_id, "🎫 لطفاً کد سکه خود را وارد کنید:", {
            'keyboard': [[BACK_BUTTON]],
            'resize_keyboard': True
        })
        return
    
    if text == 'ℹ️ اطلاعات حساب':
        account_info = f"""
📌 <b>اطلاعات حساب</b>

👤 نام: <b>{first_name} {last_name}</b>
🔖 نام کاربری: <b>@{username}</b>
🆔 آیدی: <code>{user_id}</code>
🪙 سکه‌ها: <b>{user['coins']}</b>
📅 تاریخ ایجاد: <b>{user['created_at'].strftime('%Y-%m-%d %H:%M')}</b>
        """
        send_message(chat_id, account_info, MAIN_KEYBOARD)
        return
    
    if text == BACK_BUTTON:
        send_message(chat_id, "🏠 به منوی اصلی بازگشتید", MAIN_KEYBOARD)
        return
    
    # Handle coin code redemption
    if len(text) == 10 and text.isalnum():  # Simple check for coin code format
        success, message = redeem_coin_code(user_id, text)
        send_message(chat_id, message, MAIN_KEYBOARD)
        return
    
    # Handle translation
    if text in [PERSIAN_TO_ENGLISH, ENGLISH_TO_PERSIAN]:
        direction = "لطفاً متن مورد نظر برای ترجمه را ارسال کنید:"
        if text == PERSIAN_TO_ENGLISH:
            direction = "🔹 فارسی به انگلیسی\n" + direction
        else:
            direction = "🔹 انگلیسی به فارسی\n" + direction
        
        send_message(chat_id, direction, {
            'keyboard': [[BACK_BUTTON]],
            'resize_keyboard': True
        })
        return
    
    # Check if we're expecting a translation text
    # (This is simplified - in a real bot you'd track user state)
    if 'text' in message:
        # Check if previous message was asking for translation
        # (In a production bot, you'd use proper state management)
        if user['coins'] <= 0:
            send_message(chat_id, "⚠️ سکه کافی ندارید! لطفاً سکه خریداری کنید.", MAIN_KEYBOARD)
            return
        
        # Deduct coin
        update_user(user_id, {'coins': user['coins'] - 1})
        
        # Determine translation direction based on previous messages
        # (Again, in production you'd track user state properly)
        target_lang = 'en'  # Default to Persian to English
        if ENGLISH_TO_PERSIAN in message.get('reply_to_message', {}).get('text', ''):
            target_lang = 'fa'
        
        translated_text = translate_text(text, target_lang)
        if translated_text:
            if target_lang == 'en':
                result = f"""
🔹 <b>ترجمه فارسی به انگلیسی:</b>

📌 متن اصلی:
{text}

🌐 ترجمه:
{translated_text}

<i>ترجمه شده توسط Carbon AI</i>
                """
            else:
                result = f"""
🔹 <b>ترجمه انگلیسی به فارسی:</b>

📌 متن اصلی:
{text}

🌐 ترجمه:
{translated_text}

<i>ترجمه شده توسط Carbon AI</i>
                """
            
            send_message(chat_id, result, MAIN_KEYBOARD)
        else:
            send_message(chat_id, "⚠️ خطا در ترجمه! لطفاً دوباره امتحان کنید.", MAIN_KEYBOARD)
            # Refund the coin
            update_user(user_id, {'coins': user['coins'] + 1})
        return
    
    # Default response
    send_message(chat_id, "لطفاً از منوی زیر انتخاب کنید:", MAIN_KEYBOARD)

def handle_admin_command(chat_id, command):
    """Handle admin commands"""
    if command == '/admin stats':
        user_count = users_collection.count_documents({})
        active_today = users_collection.count_documents({
            'last_daily_coin': {'$gte': datetime.now() - timedelta(days=1)}
        })
        total_coins = sum(user['coins'] for user in users_collection.find())
        
        stats = f"""
📊 <b>آمار ربات</b>

👥 کاربران کل: <b>{user_count}</b>
🟢 کاربران فعال امروز: <b>{active_today}</b>
🪙 مجموع سکه‌ها: <b>{total_coins}</b>
        """
        send_message(chat_id, stats, ADMIN_KEYBOARD)
    
    elif command == '/admin broadcast':
        send_message(chat_id, "📢 لطفاً پیام خود را برای ارسال به همه کاربران وارد کنید:", {
            'keyboard': [[BACK_BUTTON]],
            'resize_keyboard': True
        })
    
    elif command == '/admin generate_code':
        code = generate_coin_code()
        send_message(chat_id, f"🎟 کد سکه جدید:\n\n<code>{code}</code>", ADMIN_KEYBOARD)
    
    else:
        send_message(chat_id, "دستور ادمین نامعتبر", ADMIN_KEYBOARD)

def main():
    global LAST_UPDATE_ID
    
    print("Bot started...")
    while True:
        try:
            updates = get_updates(LAST_UPDATE_ID + 1)
            for update in updates:
                LAST_UPDATE_ID = update['update_id']
                if 'message' in update:
                    handle_message(update)
                elif 'callback_query' in update:
                    # Handle callback queries if needed
                    pass
        except Exception as e:
            print(f"Error: {e}")
            time.sleep(5)

if __name__ == '__main__':
    main()
