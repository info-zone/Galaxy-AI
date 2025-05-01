import requests
import time
import io
from PIL import Image

# === CONFIG ===
BOT_TOKEN = "2109246071:LvlHCpvSkjpD8rFw1N4lNcaJmKP5EyCxgUNp6euX"
HF_API_TOKEN = "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"  # Use HF token that never expires
URL = f"https://tapi.bale.ai/bot{BOT_TOKEN}/"
SPAM_DELAY = 30  # seconds

# === HEADERS ===
HF_IMG_HEADERS = {"Authorization": f"Bearer {HF_API_TOKEN}"}
HF_CHAT_HEADERS = {"Authorization": f"Bearer {HF_API_TOKEN}"}
HF_IMAGE_API = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-dev"
HF_CHAT_API = "https://router.huggingface.co/together/v1/chat/completions"

user_last_gen = {}

# === UTILS ===
def is_persian(text):
    return any('\u0600' <= ch <= '\u06FF' for ch in text)

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

def generate_image(prompt):
    payload = {"inputs": prompt}
    r = requests.post(HF_IMAGE_API, headers=HF_IMG_HEADERS, json=payload)
    return r.content

def chat_reply(text):
    system_prompt = "شما یک ربات فارسی زبان مودب و مفید هستید. اگر کاربر درخواست تصویر داشت، به او بگویید از دستور /gen استفاده کند."
    payload = {
        "model": "Qwen/Qwen3-235B-A22B-fp8-tput",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": text}
        ],
        "max_tokens": 512
    }
    res = requests.post(HF_CHAT_API, headers=HF_CHAT_HEADERS, json=payload)
    return res.json()["choices"][0]["message"]["content"]

# === TELEGRAM UTILS ===
def send_message(chat_id, text):
    requests.post(URL + "sendMessage", data={"chat_id": chat_id, "text": text})

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

def send_typing(chat_id):
    requests.post(URL + "sendChatAction", data={"chat_id": chat_id, "action": "typing"})

def send_upload(chat_id):
    requests.post(URL + "sendChatAction", data={"chat_id": chat_id, "action": "upload_photo"})

# === CORE ===
def handle_message(msg):
    chat_id = msg['chat']['id']
    user_id = msg['from']['id']
    text = msg.get('text', '')

    if not text:
        return

    if text.startswith('/gen '):
        now = time.time()
        last = user_last_gen.get(user_id, 0)

        if now - last < SPAM_DELAY:
            wait = int(SPAM_DELAY - (now - last))
            send_message(chat_id, f"لطفاً {wait} ثانیه دیگر صبر کنید.")
            return

        user_last_gen[user_id] = now
        prompt = text[5:].strip()
        if is_persian(prompt):
            prompt = translate_fa_to_en(prompt)

        send_message(chat_id, "در حال تولید تصویر، لطفاً منتظر بمانید...")
        send_upload(chat_id)
        image_bytes = generate_image(prompt)
        send_image(chat_id, image_bytes)

    else:
        send_typing(chat_id)
        reply = chat_reply(text)
        send_message(chat_id, reply)

def get_updates(offset=None):
    params = {"timeout": 100, "offset": offset}
    return requests.get(URL + "getUpdates", params=params).json()

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
