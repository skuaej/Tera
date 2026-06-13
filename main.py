import os
import telebot
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, WebAppInfo
import requests
from dotenv import load_dotenv

# --- LOAD ENVIRONMENT VARIABLES ---
load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_ID = int(os.getenv("CHANNEL_ID")) 
CHANNEL_INVITE_LINK = os.getenv("CHANNEL_INVITE_LINK")

if not BOT_TOKEN:
    raise ValueError("BOT_TOKEN is missing. Please check your .env file.")

bot = telebot.TeleBot(BOT_TOKEN)

# --- HELPER FUNCTIONS ---
def check_sub(user_id):
    """Checks if the user is a member of the required channel."""
    try:
        member = bot.get_chat_member(CHANNEL_ID, user_id)
        if member.status in ['member', 'creator', 'administrator']:
            return True
        return False
    except Exception:
        return False

def get_resolution_value(res_str):
    """Converts resolution strings (e.g., '360p', '2K') to integers for sorting."""
    res = res_str.lower().replace('p', '').replace('k', '000')
    try:
        return int(res)
    except ValueError:
        return 99999  

# --- MESSAGE HANDLERS ---
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.from_user.id
    
    if not check_sub(user_id):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔔 Join Channel to Use Bot", url=CHANNEL_INVITE_LINK))
        bot.send_message(
            message.chat.id, 
            "👋 Welcome! You must join our channel to use this bot.\n\nPlease join using the button below, then send /start again.", 
            reply_markup=markup
        )
        return
        
    bot.send_message(message.chat.id, "✅ Welcome! Send me a Terabox link, and I will extract the direct streams for you.")

@bot.message_handler(func=lambda message: 'terabox.com' in message.text or 'teraboxapp.com' in message.text or '1024tera.com' in message.text)
def handle_terabox_link(message):
    user_id = message.from_user.id
    
    if not check_sub(user_id):
        markup = InlineKeyboardMarkup()
        markup.add(InlineKeyboardButton("🔔 Join Channel to Use Bot", url=CHANNEL_INVITE_LINK))
        bot.send_message(
            message.chat.id, 
            "⚠️ Please join our channel first to use this bot.", 
            reply_markup=markup
        )
        return

    processing_msg = bot.reply_to(message, "🔄 Extracting link, please wait...")
    
    url = message.text.strip()
    api_url = f"https://tera-download-rose.vercel.app/api/extract?url={url}"
    
    try:
        response = requests.get(api_url).json()
        
        if response.get("success"):
            data = response.get("data", {})
            streams = data.get("streams", {})
            
            # REMOVED FILE NAME HERE
            text = "👇 **Select Quality to Play (Lowest to Highest):**"
            
            sorted_streams = sorted(streams.items(), key=lambda item: get_resolution_value(item[0]))
            
            markup = InlineKeyboardMarkup()
            for resolution, link in sorted_streams:
                markup.add(InlineKeyboardButton(f"▶️ Play {resolution}", web_app=WebAppInfo(url=link)))
                
            bot.edit_message_text(
                text=text, 
                chat_id=message.chat.id, 
                message_id=processing_msg.message_id, 
                reply_markup=markup, 
                parse_mode="Markdown"
            )
        else:
            bot.edit_message_text(
                "❌ Failed to extract the link. Please check if the link is valid or try again later.",
                chat_id=message.chat.id,
                message_id=processing_msg.message_id
            )
            
    except Exception as e:
        bot.edit_message_text(
            "⚠️ An error occurred while communicating with the API.",
            chat_id=message.chat.id,
            message_id=processing_msg.message_id
        )

@bot.message_handler(func=lambda message: True)
def handle_other_messages(message):
    bot.reply_to(message, "Please send a valid Terabox link.")

# --- START BOT ---
if __name__ == "__main__":
    print("Bot is running securely using .env configurations...")
    bot.infinity_polling()
    
