import requests
import time
import io
from PIL import Image
from openai import OpenAI

# === CONFIG ===
BOT_TOKEN = "2109246071:LvlHCpvSkjpD8rFw1N4lNcaJmKP5EyCxgUNp6euX"
HF_TOKEN = "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"
HF_API_URL = "https://router.huggingface.co/hf-inference/models/black-forest-labs/FLUX.1-dev"
OR_API_KEY = "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"
SYSTEM_PROMPT = "شما یک دستیار فارسی زبان هستید. مودب، مفید و خلاصه جواب بده. در صورتی که سوال مربوط به تصویر بود از کاربر بخواه که از دستور /gen استفاده کند."
SPAM_DELAY = 30  # seconds between /gen requests
URL = f"https://tapi.bale.ai/bot{BOT_TOKEN}/"

# === TRACK USERS ===
user_last_gen = {}

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

# === IMAGE GENERATION ===
def generate_image(prompt):
    headers = {"Authorization": f"Bearer {HF_TOKEN}"}
    payload = {"inputs": prompt}
    r = requests.post(HF_API_URL, headers=headers, json=payload)
    return r.content

# === SEND TO TELEGRAM ===
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

# === CHATBOT (OpenRouter) ===
def chat_reply(user_message):
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=OR_API_KEY,
    )

    completion = client.chat.completions.create(
        model="mistralai/mistral-small-24b-instruct-2501:free",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_message}
        ]
    )
    return completion.choices[0].message.content.strip()

# === HANDLE MESSAGE ===
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

        prompt = text[5:]
        prompt_en = translate_fa_to_en(prompt) if is_persian(prompt) else prompt

        send_message(chat_id, "در حال تولید تصویر، لطفاً صبر کنید...")
        send_upload(chat_id)
        image_bytes = generate_image(prompt_en)
        send_image(chat_id, image_bytes)
    else:
        send_typing(chat_id)
        reply = chat_reply(text)
        send_message(chat_id, reply)

# === TELEGRAM LOOP ===
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
