import os
import logging
import requests
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# ==========================================
# 1. BOT TOKEN
# ==========================================
TOKEN = "9029968342:AAG-XRHnHFhkbW7bxiZbegqYb3rWuYxNMh4"

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# ==========================================
# 2. START COMMAND (SUMAIYA BOT)
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    
    keyboard = [
        [
            InlineKeyboardButton("💬 Chat with AI", callback_data='ai_chat'),
            InlineKeyboardButton("🎬 Video Downloader", callback_data='video_dl')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    welcome_text = (
        "╔══════════════════════╗\n"
        "   ✨ **SUMAIYA BOT** ✨\n"
        "╚══════════════════════╝\n\n"
        f"👋 Welcome **{user_name}**,\n"
        "I am a smart AI bot. You can chat with me in any language, or download any video instantly.\n\n"
        "👇 **Tap a button below to begin:**"
    )
    
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')

# ==========================================
# 3. BUTTON CLICK HANDLER
# ==========================================
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == 'ai_chat':
        keyboard = [[InlineKeyboardButton("🎬 Switch to Video Download", callback_data='video_dl')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text="💠 **AI CHAT MODE ACTIVATED!**\n\nSend me any question in any language, and I will reply in the same language.", 
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    elif query.data == 'video_dl':
        keyboard = [[InlineKeyboardButton("💬 Switch to Chat", callback_data='ai_chat')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text="🎬 **VIDEO DOWNLOADER MODE!**\n\nPaste any video link (YouTube, Facebook, TikTok) and I will download it instantly.", 
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

# ==========================================
# 4. MESSAGE HANDLER (AI & Downloader)
# ==========================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    if text.startswith("http://") or text.startswith("https://"):
        status_msg = await update.message.reply_text("🔄 **Processing Link...** Please wait.")
        
        ydl_opts = {
            'format': 'best',
            'outtmpl': 'video.mp4',
            'quiet': True
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([text])
            
            await status_msg.edit_text("📤 **Download Complete!** Uploading video...")
            
            download_keyboard = [[InlineKeyboardButton("⬇️ Download Video", url='https://t.me')]]
            reply_markup = InlineKeyboardMarkup(download_keyboard)
            
            with open('video.mp4', 'rb') as video_file:
                await update.message.reply_video(
                    video=video_file, 
                    caption="✨ **Video Downloaded Successfully!**\n\n🤖 Powered by Sumaiya Bot.",
                    reply_markup=reply_markup
                )
            
            os.remove('video.mp4')
            await status_msg.delete()
            
        except Exception as e:
            await status_msg.edit_text("❌ **Sorry, I couldn't download this video.**")
            print(f"Download error: {e}")
            
    else:
        status_msg = await update.message.reply_text("🧠 **AI is thinking...**")
        
        try:
            # Pollinations API-এর পরিবর্তে একটি স্মার্ট এবং রিলায়েবল এন্ডপয়েন্ট ব্যবহার করা হলো
            prompt = f"You are a helpful AI assistant. Please answer in the same language the user used. User: {text}"
            
            # Pollinations-এর নতুন এবং স্ট্যাবল লিংক
            api_url = f"https://text.pollinations.ai/{requests.utils.quote(prompt)}"
            
            # রিকোয়েস্ট পাঠানো (টাইমআউট ১৫ সেকেন্ড)
            response = requests.get(api_url, timeout=15)
            
            if response.status_code == 200:
                ai_reply = response.text.strip()
                
                formatted_reply = (
                    "╔══════════════════════╗\n"
                    "   🤖 **AI RESPONSE**\n"
                    "╚══════════════════════╝\n\n"
                    f"{ai_reply}\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━"
                )
                
                nav_keyboard = [[InlineKeyboardButton("🎬 Switch to Video Download", callback_data='video_dl')]]
                reply_markup = InlineKeyboardMarkup(nav_keyboard)
                
                await update.message.reply_text(formatted_reply, reply_markup=reply_markup, parse_mode='Markdown')
                await status_msg.delete()
            else:
                await status_msg.edit_text("❌ **Server Busy.** Please try again in a few seconds.")
                
        except Exception as e:
            await status_msg.edit_text("❌ **Connection Error.** Failed to reach AI server.")
            print(f"AI error: {e}")

# ==========================================
# 5. SET BOT COMMANDS
# ==========================================
async def set_commands(application):
    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("chat", "AI Chat Mode"),
        BotCommand("video", "Video Download Mode")
    ]
    await application.bot.set_my_commands(commands)

# ==========================================
# 6. RUN THE BOT
# ==========================================
if __name__ == '__main__':
    print("Starting Sumaiya Bot...")
    application = ApplicationBuilder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_click))
    
    application.post_init = set_commands
    
    print("Sumaiya Bot is online and running!")
    application.run_polling()
