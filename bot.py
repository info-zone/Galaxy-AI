import requests
import time
import io
from PIL import Image
import google.generativeai as genai
import logging
import json
from requests.exceptions import RequestException

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

# === CONFIG ===
# Note: In production, these should be stored in environment variables
BOT_TOKEN = "2109246071:LvlHCpvSkjpD8rFw1N4lNcaJmKP5EyCxgUNp6euX"
HF_TOKEN = "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"
HF_API_URL = "https://api-inference.huggingface.co/models/black-forest-labs/FLUX.1-dev"
GEMINI_API_KEY = "AIzaSyDb19BEMO5RvvF07zq603efVIvdH_SXUT8"
SPAM_DELAY = 30  # seconds
URL = f"https://tapi.bale.ai/bot{BOT_TOKEN}/"

# === Gemini Setup ===
try:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel("gemini-pro")
    logger.info("Gemini API configured successfully")
except Exception as e:
    logger.error(f"Failed to configure Gemini API: {e}")
    exit(1)

# === TRACK USERS ===
user_last_gen = {}

def is_persian(text):
    """Check if text contains Persian characters."""
    return any('\u0600' <= ch <= '\u06FF' for ch in text)

def translate_fa_to_en(text):
    """Translate Persian text to English using Google Translate API."""
    try:
        params = {
            "client": "gtx",
            "sl": "fa",
            "tl": "en", 
            "dt": "t",
            "q": text
        }
        r = requests.get("https://translate.googleapis.com/translate_a/single", params=params)
        r.raise_for_status()
        result = r.json()
        if result and len(result) > 0 and len(result[0]) > 0:
            return result[0][0][0]
        return text
    except Exception as e:
        logger.error(f"Translation error: {e}")
        return text

def generate_image(prompt):
    """Generate an image using Hugging Face API."""
    try:
        headers = {"Authorization": f"Bearer {HF_TOKEN}"}
        payload = {"inputs": prompt}
        
        logger.info(f"Sending image generation request with prompt: {prompt}")
        response = requests.post(HF_API_URL, headers=headers, json=payload)
        response.raise_for_status()
        
        # Check if the response is JSON (error) or bytes (image)
        content_type = response.headers.get('content-type', '')
        if 'application/json' in content_type:
            error_info = response.json()
            logger.error(f"HF API returned error: {error_info}")
            return None
            
        return response.content
    except RequestException as e:
        logger.error(f"Image generation request failed: {e}")
        return None

def send_message(chat_id, text):
    """Send a text message to a chat."""
    try:
        response = requests.post(URL + "sendMessage", json={"chat_id": chat_id, "text": text})
        response.raise_for_status()
        return response.json()
    except RequestException as e:
        logger.error(f"Failed to send message: {e}")
        return None

def send_image(chat_id, image_bytes):
    """Send an image to a chat."""
    if not image_bytes:
        send_message(chat_id, "متأسفانه در تولید تصویر خطایی رخ داد. لطفا دوباره امتحان کنید.")
        return
        
    try:
        img = io.BytesIO(image_bytes)
        img.name = "image.png"
        files = {"photo": img}
        data = {
            "chat_id": chat_id,
            "caption": "تصویر توسط Zone AI تولید شده است.",
            "parse_mode": "HTML"
        }
        response = requests.post(URL + "sendPhoto", data=data, files=files)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to send image: {e}")
        send_message(chat_id, "متأسفانه در ارسال تصویر خطایی رخ داد.")
        return None

def send_typing(chat_id):
    """Send typing action to a chat."""
    try:
        requests.post(URL + "sendChatAction", json={"chat_id": chat_id, "action": "typing"})
    except Exception as e:
        logger.error(f"Failed to send typing action: {e}")

def send_upload(chat_id):
    """Send upload_photo action to a chat."""
    try:
        requests.post(URL + "sendChatAction", json={"chat_id": chat_id, "action": "upload_photo"})
    except Exception as e:
        logger.error(f"Failed to send upload action: {e}")

def chat_reply(text):
    """Generate a response using Gemini API."""
    try:
        SYSTEM_PROMPT = "شما یک ربات فارسی زبان هستید، مؤدب، مفید و خلاصه پاسخ می‌دهید. اگر درخواست تصویر بود، کاربر را به دستور /gen ارجاع دهید."
        
        message = [
            {"role": "system", "parts": [SYSTEM_PROMPT]},
            {"role": "user", "parts": [text]}
        ]
        
        response = gemini_model.generate_content(message)
        return response.text.strip()
    except Exception as e:
        logger.error(f"Chat generation error: {e}")
        return "متأسفانه در پاسخگویی خطایی رخ داد. لطفا دوباره امتحان کنید."

def handle_message(msg):
    """Handle incoming messages."""
    try:
        chat_id = msg['chat']['id']
        user_id = msg['from']['id']
        
        if 'text' not in msg:
            send_message(chat_id, "لطفاً یک پیام متنی ارسال کنید.")
            return
            
        text = msg['text']
        logger.info(f"Received message from {user_id}: {text[:50]}...")

        if text.startswith('/start'):
            send_message(chat_id, "به ربات Zone AI خوش آمدید! برای تولید تصویر از دستور /gen استفاده کنید.")
            
        elif text.startswith('/help'):
            help_text = """دستورات موجود:
/gen [توضیحات] - تولید تصویر براساس توضیحات
برای گفتگو با هوش مصنوعی کافیست پیام خود را ارسال کنید."""
            send_message(chat_id, help_text)
            
        elif text.startswith('/gen'):
            now = time.time()
            last = user_last_gen.get(user_id, 0)

            if now - last < SPAM_DELAY:
                wait = int(SPAM_DELAY - (now - last))
                send_message(chat_id, f"لطفاً {wait} ثانیه دیگر صبر کنید.")
                return

            prompt = text[5:].strip()
            if not prompt:
                send_message(chat_id, "لطفاً توضیحات تصویر مورد نظر را وارد کنید. مثال: /gen یک گربه نارنجی")
                return
                
            # Update last generation time
            user_last_gen[user_id] = now
            
            # Translate prompt if it's in Persian
            prompt_en = translate_fa_to_en(prompt) if is_persian(prompt) else prompt
            logger.info(f"Translated prompt: {prompt_en}")

            send_message(chat_id, "در حال تولید تصویر، لطفاً صبر کنید...")
            send_upload(chat_id)
            
            image_bytes = generate_image(prompt_en)
            send_image(chat_id, image_bytes)

        else:
            send_typing(chat_id)
            reply = chat_reply(text)
            send_message(chat_id, reply)
    
    except Exception as e:
        logger.error(f"Error handling message: {e}")
        try:
            send_message(chat_id, "متأسفانه خطایی رخ داد. لطفا دوباره امتحان کنید.")
        except:
            pass

def get_updates(offset=None):
    """Get updates from Bale API."""
    params = {"timeout": 100}
    if offset:
        params["offset"] = offset
        
    try:
        response = requests.get(URL + "getUpdates", params=params)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"Failed to get updates: {e}")
        # Wait before retrying to avoid overwhelming the server
        time.sleep(5)
        return {"ok": False, "result": []}

def main():
    """Main function to run the bot."""
    logger.info("Starting bot...")
    last_update_id = None
    
    # Verify API tokens before starting
    try:
        info = requests.get(URL + "getMe").json()
        if info.get("ok"):
            bot_name = info["result"].get("username", "Unknown")
            logger.info(f"Bot connected successfully as @{bot_name}")
        else:
            logger.error(f"Failed to connect to Bale API: {info}")
            return
    except Exception as e:
        logger.error(f"Failed to verify bot token: {e}")
        return
    
    while True:
        try:
            updates = get_updates(last_update_id)
            
            if not updates.get("ok", False):
                logger.error(f"Error in getUpdates: {updates}")
                time.sleep(5)
                continue
                
            if updates and "result" in updates and updates["result"]:
                for update in updates["result"]:
                    if "message" in update:
                        handle_message(update["message"])
                    
                    # Update the last update ID
                    last_update_id = update["update_id"] + 1
            
            # If no updates, just continue the loop
            else:
                time.sleep(1)
                
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
            break
        except Exception as e:
            logger.error(f"Unexpected error in main loop: {e}")
            time.sleep(5)

if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
