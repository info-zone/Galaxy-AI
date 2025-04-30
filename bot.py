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
    file_info = requests.get(f'{API_URL}/getFile', params={'file_id': file_id}).json()
    file_path = file_info['result']['file_path']
    return f'https://tapi.bale.ai/file/bot{BOT_TOKEN}/{file_path}'

def ask_openrouter(messages):
    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type": "application/json",
        "HTTP-Referer": "your-site.com",
        "X-Title": "Zone AI",
    }
    body = {
        "model": "meta-llama/llama-4-scout:free",
        "messages": [SYSTEM_PROMPT] + messages,
    }

    response = requests.post(
        'https://openrouter.ai/api/v1/chat/completions',
        headers=headers,
        json=body
    )

    if response.status_code != 200:
        return f"API Error: {response.status_code} - {response.text}"

    data = response.json()
    if "choices" not in data:
        return f"Unexpected response: {data}"

    return data["choices"][0]["message"]["content"]

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
