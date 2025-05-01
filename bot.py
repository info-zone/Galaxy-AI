import logging
import torch
from telegram import Update, Bot
from telegram.ext import Updater, MessageHandler, Filters, CallbackContext
from transformers import pipeline

# Directly set your bot token here
TOKEN = "7151280338:AAGf5-CPmnhvmFEaRFEPuRP1PD3qY79fsOY"

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)
logger = logging.getLogger(__name__)

# Determine device for model (GPU if available, else CPU)
device = 0 if torch.cuda.is_available() else -1
if device == 0:
    logger.info(f"CUDA is available. Using GPU: {torch.cuda.get_device_name(0)}")
else:
    logger.info("CUDA is not available. Using CPU.")

# Initialize the text-generation pipeline
pipe = pipeline(
    "text-generation",
    model="deepseek-ai/DeepSeek-V3-0324",
    trust_remote_code=True,
    device=device
)

# Handler for incoming messages
def handle_message(update: Update, context: CallbackContext) -> None:
    user_msg = update.message.text
    logger.info(f"Received message: {user_msg}")

    messages = [{"role": "user", "content": user_msg}]

    try:
        result = pipe(messages)
        if isinstance(result, list) and "generated_text" in result[0]:
            response = result[0]["generated_text"]
        else:
            response = str(result)
    except Exception as e:
        logger.error(f"Error during generation: {e}")
        response = "Sorry, I encountered an error while thinking."

    update.message.reply_text(response)


def main():
    if not TOKEN:
        logger.error("Bot token is missing. Please set it in the script.")
        return

    updater = Updater(token=TOKEN, use_context=True)
    dp = updater.dispatcher
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    updater.start_polling()
    logger.info("Bot started. Listening for messages...")
    updater.idle()


if __name__ == '__main__':
    main()
