import requests
import time

BOT_TOKEN = '1917206133:eS44bI1l1x11BZtwxb1IKmHM27YJ2LZ6d4a9I7cw'
API_URL = f'https://tapi.bale.ai/bot{BOT_TOKEN}'
OPENROUTER_API_KEY = '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'

SYSTEM_PROMPT = {
    "role": "system",
    "content": "You are Zone AI, a smart and helpful Persian-English assistant that responds clearly and politely. Always understand context from text and images. If an image is sent, describe it in detail. If the user speaks Persian, reply in Persian. Be short, useful, and friendly."
}

def get_updates(offset=None):
    params = {'timeout': 10, 'offset': offset}
    return requests.get(f'{API_URL}/getUpdates', params=params).json()

def send_message(chat_id, text):
    requests.post(f'{API_URL}/sendMessage', json={'chat_id': chat_id, 'text': text})

def send_chat_action(chat_id, action='typing'):
    requests.post(f'{API_URL}/sendChatAction', data={'chat_id': chat_id, 'action': action})

def get_file_url(file_id):
    file_path = requests.get(f'{API_URL}/getFile', params={'file_id': file_id}).json()['result']['file_path']
    return f'https://tapi.bale.ai/file/bot{BOT_TOKEN}/{file_path}'

def ask_openrouter(messages):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "your-site.com",
        "X-Title": "Zone AI",
    }
    body = {
        "model": "opengvlab/internvl3-14b:free",
        "messages": [SYSTEM_PROMPT] + messages,
    }
    r = requests.post('https://openrouter.ai/api/v1/chat/completions', headers=headers, json=body)
    return r.json()['choices'][0]['message']['content']

def main():
    last_update = None
    print("Bot is running...")

    while True:
        updates = get_updates(offset=last_update)
        for update in updates.get('result', []):
            last_update = update['update_id'] + 1
            message = update.get('message')
            if not message:
                continue

            chat_id = message['chat']['id']
            send_chat_action(chat_id)

            user_msg = []
            if 'photo' in message:
                # Get the largest photo
                photo = message['photo'][-1]
                file_url = get_file_url(photo['file_id'])
                user_msg.append({"type": "image_url", "image_url": {"url": file_url}})
                if 'caption' in message:
                    user_msg.insert(0, {"type": "text", "text": message['caption']})
            elif 'text' in message:
                user_msg.append({"type": "text", "text": message['text']})
            else:
                send_message(chat_id, "Only text and images are supported.")
                continue

            try:
                reply = ask_openrouter([{"role": "user", "content": user_msg}])
                send_message(chat_id, reply)
            except Exception as e:
                send_message(chat_id, f"Error: {e}")

        time.sleep(0.5)

if __name__ == '__main__':
    main()
