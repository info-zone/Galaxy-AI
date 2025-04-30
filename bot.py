import requests
import time
import base64

# Telegram Bot Token
BOT_TOKEN = "1917206133:eS44bI1l1x11BZtwxb1IKmHM27YJ2LZ6d4a9I7cw"
BASE_URL = f"https://tapi.bale.ai/bot{BOT_TOKEN}"

# OpenRouter API
OPENROUTER_API_KEY = "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"
OPENROUTER_BASE_URL = "https://openrouter.ai/api/v1"

# System prompt
SYSTEM_PROMPT = "You are Zone AI, a smart, friendly, highly detailed assistant. Always stay friendly, helpful, and very intelligent. If you receive an image, describe it thoughtfully and helpfully."

# Last update ID
last_update_id = None

def get_updates():
    global last_update_id
    params = {
        "timeout": 100,
        "offset": last_update_id + 1 if last_update_id else None,
    }
    response = requests.get(f"{BASE_URL}/getUpdates", params=params, timeout=120)
    return response.json()["result"]

def send_message(chat_id, text, reply_to=None):
    data = {
        "chat_id": chat_id,
        "text": text,
        "reply_to_message_id": reply_to,
    }
    requests.post(f"{BASE_URL}/sendMessage", data=data)

def send_chat_action(chat_id, action="typing"):
    requests.post(f"{BASE_URL}/sendChatAction", data={"chat_id": chat_id, "action": action})

def download_file(file_id):
    file_info = requests.get(f"{BASE_URL}/getFile", params={"file_id": file_id}).json()
    file_path = file_info["result"]["file_path"]
    file_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_path}"
    file_content = requests.get(file_url).content
    return file_content

def ask_openrouter_text(user_text):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": "deepseek/deepseek-r1:free",
        "extra_body": {},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text},
        ]
    }
    response = requests.post(f"{OPENROUTER_BASE_URL}/chat/completions", headers=headers, json=body, timeout=60)
    return response.json()["choices"][0]["message"]["content"]

def ask_openrouter_image(image_base64):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
    }
    body = {
        "model": "deepseek/deepseek-r1:free",
        "extra_body": {},
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "Analyze this image and describe it thoughtfully."},
                    {"type": "image", "image": image_base64}
                ]
            }
        ]
    }
    response = requests.post(f"{OPENROUTER_BASE_URL}/chat/completions", headers=headers, json=body, timeout=120)
    return response.json()["choices"][0]["message"]["content"]

def handle_message(message):
    chat_id = message["chat"]["id"]
    message_id = message["message_id"]

    send_chat_action(chat_id)

    if "photo" in message:
        # Handling image
        file_id = message["photo"][-1]["file_id"]
        file_content = download_file(file_id)
        image_base64 = base64.b64encode(file_content).decode("utf-8")

        try:
            reply = ask_openrouter_image(image_base64)
        except Exception as e:
            print(e)
            reply = "Sorry, I couldn't analyze the image."

        send_message(chat_id, reply, reply_to=message_id)

    elif "text" in message:
        # Handling text
        user_text = message["text"]

        try:
            reply = ask_openrouter_text(user_text)
        except Exception as e:
            print(e)
            reply = "Sorry, I couldn't understand your message."

        send_message(chat_id, reply, reply_to=message_id)

    else:
        send_message(chat_id, "I currently only support text and images.", reply_to=message_id)

def main():
    global last_update_id
    while True:
        try:
            updates = get_updates()
            for update in updates:
                last_update_id = update["update_id"]
                if "message" in update:
                    handle_message(update["message"])
        except Exception as e:
            print("Error:", e)
            time.sleep(2)

if __name__ == "__main__":
    main()
