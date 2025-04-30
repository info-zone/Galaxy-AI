import requests
import time
import torch
from diffusers import DiffusionPipeline
from io import BytesIO

# Telegram Bot Token
TOKEN = ""
URL = f"https://tapi.bale.ai/bot{TOKEN}/"

# Load the Stable Diffusion pipeline
pipe = DiffusionPipeline.from_pretrained("stabilityai/stable-diffusion-xl-base-1.0", torch_dtype=torch.float16)
pipe.to("cuda" if torch.cuda.is_available() else "cpu")

# Function to check if a string contains Persian characters
def is_persian(text):
    return any('\u0600' <= ch <= '\u06FF' for ch in text)

# Translate Persian to English using Google Translate (web)
def translate_persian_to_english(text):
    params = {
        "sl": "fa",
        "tl": "en",
        "q": text
    }
    response = requests.get("https://translate.googleapis.com/translate_a/single", params={
        "client": "gtx",
        "sl": "fa",
        "tl": "en",
        "dt": "t",
        "q": text
    })
    try:
        return response.json()[0][0][0]
    except Exception:
        return text  # fallback to original

# Send photo
def send_image(chat_id, image):
    bio = BytesIO()
    image.save(bio, format='PNG')
    bio.seek(0)
    files = {'photo': bio}
    data = {'chat_id': chat_id}
    requests.post(URL + "sendPhoto", data=data, files=files)

# Long polling
def get_updates(offset=None):
    params = {"timeout": 100, "offset": offset}
    response = requests.get(URL + "getUpdates", params=params)
    return response.json()

def handle_message(message):
    chat_id = message['chat']['id']
    text = message.get('text', '')
    if not text:
        return

    prompt = translate_persian_to_english(text) if is_persian(text) else text
    print(f"Generating image for: {prompt}")
    image = pipe(prompt).images[0]
    send_image(chat_id, image)

def main():
    last_update_id = None
    while True:
        updates = get_updates(last_update_id)
        if "result" in updates:
            for update in updates["result"]:
                if "message" in update:
                    handle_message(update["message"])
                    last_update_id = update["update_id"] + 1

if __name__ == "__main__":
    main()
