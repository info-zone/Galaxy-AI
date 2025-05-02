import requests
from google import genai
from google.genai import types

# === CONFIG ===
BOT_TOKEN = "2109246071:LvlHCpvSkjpD8rFw1N4lNcaJmKP5EyCxgUNp6euX"
GEMINI_API_KEY = "AIzaSyDb19BEMO5RvvF07zq603efVIvdH_SXUT8"
URL = f"https://tapi.bale.ai/bot{BOT_TOKEN}/"

# === INIT GEMINI ===
client = genai.Client(api_key=GEMINI_API_KEY)
model = "gemini-2.0-flash-lite"
config = types.GenerateContentConfig(response_mime_type="text/plain")

# === GEMINI REPLY FUNCTION ===
def ask_gemini(prompt):
    contents = [types.Content(role="user", parts=[prompt])]
    reply = ""
    for chunk in client.models.generate_content_stream(
        model=model, contents=contents, config=config
    ):
        reply += chunk.text
    return reply.strip()

# === TELEGRAM GET/REPLY ===
def get_updates(offset=None):
    params = {"timeout": 100, "offset": offset}
    res = requests.get(URL + "getUpdates", params=params)
    return res.json()

def send_message(chat_id, text):
    data = {"chat_id": chat_id, "text": text}
    requests.post(URL + "sendMessage", data=data)

# === MAIN LOOP ===
def main():
    last_update_id = None
    while True:
        updates = get_updates(last_update_id)
        if "result" in updates:
            for update in updates["result"]:
                if "message" in update and "text" in update["message"]:
                    chat_id = update["message"]["chat"]["id"]
                    text = update["message"]["text"]

                    # Process user input
                    ai_response = ask_gemini(text)
                    send_message(chat_id, ai_response)

                    last_update_id = update["update_id"] + 1

if __name__ == "__main__":
    main()
