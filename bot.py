import requests
import time
import io
from PIL import Image

# === CONFIG ===
BOT_TOKEN = "1917206133:eS44bI1l1x11BZtwxb1IKmHM27YJ2LZ6d4a9I7cw"
URL = f"https://tapi.bale.ai/bot{BOT_TOKEN}/"
HF_TOKEN = "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"
HF_API_URL = "https://router.huggingface.co/hf-inference/models/stabilityai/stable-diffusion-xl-base-1.0"

# === CHECK PERSIAN ===
def is_persian(text):
    return any('\u0600' <= ch <= '\u06FF' for ch in text)

# === TRANSLATE USING GOOGLETRANSLATE (via requests) ===
def translate_persian_to_english(text):
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
    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
    }
    payload = {"inputs": prompt}
    r = requests.post(HF_API_URL, headers=headers, json=payload)
    return r.content  # image bytes

# === SEND IMAGE ===
def send_image(chat_id, image_bytes):
    image_file = io.BytesIO(image_bytes)
    image_file.name = "image.png"
    files = {'photo': image_file}
    data = {'chat_id': chat_id}
    requests.post(URL + "sendPhoto", data=data, files=files)

# === LONG POLLING ===
def get_updates(offset=None):
    params = {"timeout": 100, "offset": offset}
    return requests.get(URL + "getUpdates", params=params).json()

def handle_message(msg):
    chat_id = msg['chat']['id']
    text = msg.get('text', '')
    if not text:
        return
    prompt = translate_persian_to_english(text) if is_persian(text) else text
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
