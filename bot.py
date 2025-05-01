#!/usr/bin/env python3
# Telegram AI Chatbot with Long Polling
# Uses DeepSeek-V3-0324 for instant AI responses

import logging
import os
import time
from typing import Dict, List, Optional, Union

import requests
from transformers import pipeline

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Telegram bot configuration
TOKEN = "7435111550:AAGggKVIoyYQI-UQmpqIyB31VEM6f2sINeY"  # Replace with your bot token from BotFather
BASE_URL = f"https://api.telegram.org/bot{TOKEN}"

# Initialize AI model
def initialize_ai_model():
    logger.info("Initializing AI model...")
    return pipeline("text-generation", model="deepseek-ai/DeepSeek-V3-0324", trust_remote_code=True)

class TelegramBot:
    def __init__(self, token: str):
        self.token = token
        self.base_url = f"https://api.telegram.org/bot{token}"
        self.offset = 0
        self.ai_model = initialize_ai_model()
        self.user_conversations: Dict[int, List[Dict[str, str]]] = {}
        logger.info("Telegram bot initialized")

    def get_updates(self, timeout: int = 30) -> List[Dict]:
        """Get updates from Telegram server using long polling"""
        params = {
            "offset": self.offset,
            "timeout": timeout,
            "allowed_updates": ["message"]
        }
        response = requests.get(f"{self.base_url}/getUpdates", params=params)
        if response.status_code == 200:
            return response.json().get("result", [])
        logger.error(f"Failed to get updates: {response.text}")
        return []

    def send_message(self, chat_id: int, text: str) -> None:
        """Send message to a specific chat"""
        params = {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        response = requests.post(f"{self.base_url}/sendMessage", params=params)
        if response.status_code != 200:
            logger.error(f"Failed to send message: {response.text}")

    def send_typing_action(self, chat_id: int) -> None:
        """Send typing action to show the bot is processing"""
        params = {
            "chat_id": chat_id,
            "action": "typing"
        }
        response = requests.post(f"{self.base_url}/sendChatAction", params=params)
        if response.status_code != 200:
            logger.error(f"Failed to send typing action: {response.text}")

    def get_ai_response(self, user_id: int, user_message: str) -> str:
        """Generate AI response based on conversation history"""
        # Initialize or get conversation history for this user
        if user_id not in self.user_conversations:
            self.user_conversations[user_id] = [{"role": "system", "content": "You are a helpful AI assistant."}]
        
        # Add user message to conversation history
        self.user_conversations[user_id].append({"role": "user", "content": user_message})
        
        # If conversation is too long, keep only the last 10 messages
        if len(self.user_conversations[user_id]) > 11:  # system message + 10 conversation turns
            # Always keep the system message at index 0
            self.user_conversations[user_id] = [self.user_conversations[user_id][0]] + self.user_conversations[user_id][-10:]
        
        try:
            # Generate response using the AI model
            response = self.ai_model(self.user_conversations[user_id])
            ai_message = response[0]['generated_text']
            
            # Clean up the response if needed (the model output format may vary)
            # Extract just the assistant's response from the generated text
            if "assistant" in ai_message and "content" in ai_message:
                ai_message = ai_message.split("content\":\"")[-1].split("\"")[0]
            
            # Add AI response to conversation history
            self.user_conversations[user_id].append({"role": "assistant", "content": ai_message})
            
            return ai_message
        except Exception as e:
            logger.error(f"Error generating AI response: {e}")
            return "I'm having trouble processing your request. Please try again later."

    def process_message(self, message: Dict) -> None:
        """Process incoming message and respond with AI"""
        chat_id = message["chat"]["id"]
        user_id = message["from"]["id"]
        
        # Handle commands
        if "text" in message:
            user_text = message["text"]
            
            # Special commands
            if user_text.startswith("/start"):
                welcome_message = "👋 Hello! I'm your AI assistant. How can I help you today?"
                self.send_message(chat_id, welcome_message)
                return
                
            if user_text.startswith("/help"):
                help_message = (
                    "🤖 *AI Assistant Help*\n\n"
                    "Just send me any message and I'll respond with AI-generated content.\n\n"
                    "Commands:\n"
                    "/start - Start a new conversation\n"
                    "/help - Show this help message\n"
                    "/reset - Reset your conversation history"
                )
                self.send_message(chat_id, help_message)
                return
                
            if user_text.startswith("/reset"):
                if user_id in self.user_conversations:
                    system_message = self.user_conversations[user_id][0]  # Save the system message
                    self.user_conversations[user_id] = [system_message]  # Reset while keeping system message
                self.send_message(chat_id, "🔄 Conversation history has been reset.")
                return
            
            # Send "typing" action to show bot is processing
            self.send_typing_action(chat_id)
            
            # Get AI response
            ai_response = self.get_ai_response(user_id, user_text)
            
            # Send response back to user
            self.send_message(chat_id, ai_response)

    def run(self) -> None:
        """Main bot loop using long polling"""
        logger.info("Starting bot...")
        
        while True:
            try:
                updates = self.get_updates()
                
                for update in updates:
                    # Update offset for next polling
                    self.offset = update["update_id"] + 1
                    
                    # Process message if present
                    if "message" in update:
                        self.process_message(update["message"])
                    
            except Exception as e:
                logger.error(f"Error in main loop: {e}")
                time.sleep(5)  # Wait before retrying

def main():
    # Check if token is set
    token = os.environ.get("TELEGRAM_BOT_TOKEN", TOKEN)
    if token == "YOUR_TELEGRAM_BOT_TOKEN":
        logger.error("Please set your Telegram bot token in the script or as environment variable TELEGRAM_BOT_TOKEN")
        return
    
    # Create and run bot
    bot = TelegramBot(token)
    bot.run()

if __name__ == "__main__":
    main()
