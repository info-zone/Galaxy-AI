import requests
import time
import logging
from google import genai
from google.genai import types

# === SETUP LOGGING ===
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# === CONFIG ===
BOT_TOKEN = "2109246071:LvlHCpvSkjpD8rFw1N4lNcaJmKP5EyCxgUNp6euX"
GEMINI_API_KEY = "AIzaSyDb19BEMO5RvvF07zq603efVIvdH_SXUT8"
URL = f"https://tapi.bale.ai/bot{BOT_TOKEN}/"
MAX_RETRIES = 3
RETRY_DELAY = 2  # seconds

# === INIT GEMINI ===
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(model_name="gemini-2.0-flash-lite", 
                             generation_config=types.GenerationConfig(
                                 response_mime_type="text/plain"
                             ))

# === GEMINI REPLY FUNCTION ===
def ask_gemini(prompt, retries=MAX_RETRIES):
    """Get response from Gemini with error handling and retries"""
    for attempt in range(retries):
        try:
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Gemini API error (attempt {attempt+1}/{retries}): {str(e)}")
            if attempt < retries - 1:
                time.sleep(RETRY_DELAY)
            else:
                return "Sorry, I'm having trouble processing your request right now. Please try again later."

# === TELEGRAM GET/REPLY ===
def get_updates(offset=None, retries=MAX_RETRIES):
    """Get updates from Telegram API with error handling"""
    params = {"timeout": 100, "offset": offset}
    
    for attempt in range(retries):
        try:
            response = requests.get(URL + "getUpdates", params=params, timeout=120)
            response.raise_for_status()  # Raise exception for 4XX/5XX responses
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Telegram API error (attempt {attempt+1}/{retries}): {str(e)}")
            if attempt < retries - 1:
                time.sleep(RETRY_DELAY)
    
    logger.critical("Failed to get updates after multiple attempts")
    return {"ok": False, "result": []}  # Return empty result to prevent crashing

def send_message(chat_id, text, retries=MAX_RETRIES):
    """Send message with error handling"""
    data = {"chat_id": chat_id, "text": text}
    
    for attempt in range(retries):
        try:
            response = requests.post(URL + "sendMessage", data=data, timeout=60)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send message (attempt {attempt+1}/{retries}): {str(e)}")
            if attempt < retries - 1:
                time.sleep(RETRY_DELAY)
    
    logger.error(f"Could not send message to {chat_id} after {retries} attempts")

# === MESSAGE HANDLERS ===
def handle_command(text, chat_id):
    """Handle special commands"""
    if text == '/start':
        return "Hello! I'm your AI assistant. How can I help you today?"
    elif text == '/help':
        return "You can ask me any question and I'll try to help. Just type your message and I'll respond."
    else:
        return None  # Not a command

# === MAIN LOOP ===
def main():
    logger.info("Starting the bot...")
    last_update_id = None
    connection_failures = 0
    
    while True:
        try:
            updates = get_updates(last_update_id)
            connection_failures = 0  # Reset counter on successful connection
            
            if not updates.get("ok", False):
                logger.error(f"Error in updates: {updates}")
                time.sleep(RETRY_DELAY)
                continue
                
            if "result" in updates and updates["result"]:
                for update in updates["result"]:
                    if "message" in update and "text" in update["message"]:
                        chat_id = update["message"]["chat"]["id"]
                        text = update["message"]["text"]
                        
                        logger.info(f"Received message from {chat_id}: {text[:50]}{'...' if len(text) > 50 else ''}")
                        
                        # Check for commands first
                        command_response = handle_command(text, chat_id)
                        if command_response:
                            send_message(chat_id, command_response)
                        else:
                            # Process regular message with Gemini
                            logger.info("Asking Gemini for response...")
                            ai_response = ask_gemini(text)
                            logger.info(f"Sending response to {chat_id}: {ai_response[:50]}{'...' if len(ai_response) > 50 else ''}")
                            send_message(chat_id, ai_response)
                    
                    # Update the offset to acknowledge processed updates
                    last_update_id = update["update_id"] + 1
            
            # If no updates, just continue polling
            else:
                time.sleep(0.5)
                
        except KeyboardInterrupt:
            logger.info("Bot stopped by user")
            break
            
        except Exception as e:
            connection_failures += 1
            logger.error(f"Unexpected error: {str(e)}")
            
            # Implement exponential backoff for repeated failures
            wait_time = min(30, RETRY_DELAY * (2 ** min(connection_failures, 5)))
            logger.info(f"Waiting {wait_time} seconds before retrying...")
            time.sleep(wait_time)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Bot terminated by user")
    except Exception as e:
        logger.critical(f"Fatal error: {str(e)}")
