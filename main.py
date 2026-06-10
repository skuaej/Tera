import telebot
from telebot import types
import requests
import json
import ast

# --- CONFIGURATION ---
BOT_TOKEN = "8813950194:AAH2yG4DacWmy7SQZ-Z_hDK4wP6l6ftH_eg"
CHANNEL_ID = -1003962725416  # Your Tera Downloader Channel ID
CHANNEL_INVITE_LINK = "https://t.me/+If8mcTBKn5o5Yzll"  # Your custom private invite link

bot = telebot.TeleBot(BOT_TOKEN)

def check_forced_join(user_id):
    """Checks if the user is a member/admin/creator of the target channel."""
    try:
        member = bot.get_chat_member(CHANNEL_ID, user_id)
        # Allowed statuses
        if member.status in ['creator', 'administrator', 'member']:
            return True
        return False
    except Exception as e:
        print(f"Error checking channel membership: {e}")
        # Note: Make sure your bot is an ADMIN in the channel, otherwise this will always return True
        return True

def extract_terabox(terabox_url):
    """Extracts stream links from the Terabox downloader API."""
    session = requests.Session()
    headers = {
        "user-agent": "Mozilla/5.0 (Linux; Android 16; SM-S921E Build/BP4A.251205.006) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/148.0.7778.215 Mobile Safari/537.36",
        "accept": "application/json, text/plain, */*",
        "origin": "https://1024teradownloader.com",
        "referer": "https://1024teradownloader.com/"
    }
    
    try:
        session.get("https://1024teradownloader.com/", headers=headers)
        
        api_url = "https://1024teradownloader.com/api/stream"
        payload = {"url": terabox_url}
        response = session.post(api_url, data=payload, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        file_list = data.get('list', [])
        
        if not file_list:
            return None, "No files were found for this link."
            
        file_info = file_list[0]
        file_name = file_info.get("name", "downloaded_video.mp4")
        thumbnail_url = file_info.get("thumbnail", "")
        raw_stream_data = file_info.get("fast_stream_url")
        
        stream_dict = {}
        if isinstance(raw_stream_data, dict):
            stream_dict = raw_stream_data
        elif isinstance(raw_stream_data, str):
            if raw_stream_data.startswith("{"):
                try:
                    stream_dict = ast.literal_eval(raw_stream_data)
                except (ValueError, SyntaxError):
                    return None, "Failed to parse the resolution data."
            else:
                stream_dict = {"Default": raw_stream_data}
        else:
            return None, "Invalid stream data format encountered."

        return {
            "file_name": file_name,
            "thumbnail": thumbnail_url,
            "streams": stream_dict
        }, None

    except requests.exceptions.RequestException as e:
        return None, f"HTTP Request failed: {e}"
    except json.JSONDecodeError:
        return None, "Failed to parse API response JSON."
    except Exception as e:
        return None, f"Unexpected error: {e}"


# --- BOT HANDLERS ---

@bot.message_handler(commands=['start'])
def send_welcome(message):
    user_id = message.from_user.id
    
    # Check Forced Join First
    if not check_forced_join(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(text="📢 Join Channel", url=CHANNEL_INVITE_LINK))
        
        bot.reply_to(
            message, 
            "⚠️ **Access Denied!**\n\nYou must join our channel to use this bot. Click the button below to join, then try sending your link again!", 
            parse_mode="Markdown", 
            reply_markup=markup
        )
        return
        
    bot.reply_to(message, "👋 **Welcome!**\n\nSend me any Terabox link, and I will instantly extract the high-quality HLS stream links for you.", parse_mode="Markdown")


@bot.message_handler(func=lambda message: True)
def handle_terabox_links(message):
    user_id = message.from_user.id

    # Check Forced Join
    if not check_forced_join(user_id):
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton(text="📢 Join Channel", url=CHANNEL_INVITE_LINK))
        
        bot.reply_to(
            message, 
            "⚠️ **Access Denied!**\n\nYou must join our updates channel before you can use this bot.", 
            parse_mode="Markdown", 
            reply_markup=markup
        )
        return

    url = message.text.strip()
    
    if "terabox" not in url and "1024tera" not in url and "tera" not in url:
        bot.reply_to(message, "⚠️ Please send a valid Terabox link.")
        return

    status_msg = bot.reply_to(message, "🔄 *Bypassing Terabox & Extracting Links...*", parse_mode="Markdown")
    
    result, error = extract_terabox(url)
    
    if error:
        bot.edit_message_text(f"❌ *Error:* {error}", chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode="Markdown")
        return
        
    file_name = result["file_name"]
    thumbnail = result["thumbnail"]
    streams = result["streams"]
    
    caption = f"🎬 **File Name:** `{file_name}`\n\n"
    caption += "⚠️ *Note:* These are HLS (`.m3u8`) stream playlists. Use an external player (like VLC) or an m3u8 downloader tool to download them."
    
    markup = types.InlineKeyboardMarkup()
    for resolution, link in streams.items():
        markup.add(types.InlineKeyboardButton(text=f"📺 Stream [{resolution}]", url=link))
        
    if thumbnail:
        try:
            bot.send_photo(message.chat.id, thumbnail, caption=caption, parse_mode="Markdown", reply_markup=markup)
            bot.delete_message(message.chat.id, status_msg.message_id)
        except Exception:
            bot.edit_message_text(caption, chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode="Markdown", reply_markup=markup)
    else:
        bot.edit_message_text(caption, chat_id=message.chat.id, message_id=status_msg.message_id, parse_mode="Markdown", reply_markup=markup)


if __name__ == "__main__":
    print("Bot is up and running publicly with Forced Join protection...")
    bot.infinity_polling()
  
