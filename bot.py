import requests
import time
import io
from PIL import Image

# === CONFIG ===
BOT_TOKEN = "2109246071:LvlHCpvSkjpD8rFw1N4lNcaJmKP5EyCxgUNp6euX"
HF_TOKEN = "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"
HF_API_URL = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-dev"
URL = f"https://tapi.bale.ai/bot{BOT_TOKEN}/"
SPAM_DELAY = 30  # seconds between user requests

# === TRACK USERS ===
user_last_request = {}

# === CHECK PERSIAN ===
def is_persian(text):
    return any('\u0600' <= ch <= '\u06FF' for ch in text)

# === TRANSLATE PERSIAN TO ENGLISH ===
def translate_fa_to_en(text):
    params = {
        "client": "gtx",
        "sl": "fa",
        "tl": "en",
        "dt": "t",
        "q": text
    }
    r = requests.get("https://translate.googleapis.com/translate_a/single", params=params)
    try:
        return r.json()[0][0][0]
    except:
        return text

# === SEND PHOTO ===
def send_image(chat_id, image_bytes):
    img = io.BytesIO(image_bytes)
    img.name = "image.png"
    files = {"photo": img}
    data = {
        "chat_id": chat_id,
        "caption": "تصویر توسط Zone AI تولید شده است.",
        "parse_mode": "HTML"
    }
    requests.post(URL + "sendPhoto", data=data, files=files)

# === TELEGRAM ACTION ===
def send_typing(chat_id):
    requests.post(URL + "sendChatAction", data={"chat_id": chat_id, "action": "upload_photo"})

def send_message(chat_id, text):
    requests.post(URL + "sendMessage", data={"chat_id": chat_id, "text": text})

# === GENERATE IMAGE ===
def generate_image(prompt):
    headers = {
        "Authorization": f"Bearer {HF_TOKEN}"
    }
    payload = {"inputs": prompt}
    r = requests.post(HF_API_URL, headers=headers, json=payload)
    return r.content  # image bytes

# === GET UPDATES ===
def get_updates(offset=None):
    params = {"timeout": 100, "offset": offset}
    return requests.get(URL + "getUpdates", params=params).json()

# === HANDLE MESSAGE ===
def handle_message(msg):
    chat_id = msg['chat']['id']
    user_id = msg['from']['id']
    text = msg.get('text', '')

    if not text:
        return

    now = time.time()
    last = user_last_request.get(user_id, 0)

    if now - last < SPAM_DELAY:
        wait = int(SPAM_DELAY - (now - last))
        send_message(chat_id, f"لطفاً {wait} ثانیه دیگر صبر کنید.")
        return

    user_last_request[user_id] = now

    prompt = translate_fa_to_en(text) if is_persian(text) else text

    send_message(chat_id, "در حال تولید تصویر، لطفاً صبر کنید...")
    send_typing(chat_id)

    image_bytes = generate_image(prompt)
    send_image(chat_id, image_bytes)

# === MAIN LOOP ===
def main():
    last_update = None
    while True:
        updates = get_updates(last_update)
        if 'result' in updates:
            for update in updates['result']:
                if 'message' in update:
                    handle_message(update['message'])
                    last_update = update['update_id'] + 1

if __name__ == "__main__":
    main()
