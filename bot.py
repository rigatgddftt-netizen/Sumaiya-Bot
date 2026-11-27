import os
import logging
import requests
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# ==========================================
# 1. BOT TOKEN
# ==========================================
TOKEN = "9029968342:AAG-XRHnHFhkbW7bxiZbegqYb3rWuYxNMh4"

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

# ==========================================
# 2. START COMMAND (Premium & Stylish UI)
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name
    
    # Premium Styled Inline Buttons
    keyboard = [
        [InlineKeyboardButton("✨ 𝗖𝗛𝗔𝗧 𝗪𝗜𝗧𝗛 𝗔𝗜 ✨", callback_data='ai_chat')],
        [InlineKeyboardButton("🎬 𝗗𝗢𝗪𝗡𝗟𝗢𝗔𝗗 𝗩𝗜𝗗𝗘𝗢 🎬", callback_data='video_dl')],
        [InlineKeyboardButton("🚀 𝗝𝗢𝗜𝗡 𝗢𝗨𝗥 𝗖𝗛𝗔𝗡𝗡𝗘𝗟 🚀", url='https://t.me/auraffxofficial')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    # Stylish Welcome Message with Markdown
    welcome_text = (
        "╔══════════════════════╗\n"
        "   🌌 **DREAM AI BOT** 🌌\n"
        "╚══════════════════════╝\n\n"
        f"👋 Hello **{user_name}**,\n"
        "Welcome to the ultimate AI experience. I am designed to assist you with smart answers and instant video downloads.\n\n"
        "🛠 **Available Features:**\n"
        "➔ 🤖 **AI Assistant:** Ask me anything.\n"
        "➔ ⬇️ **Video Downloader:** Paste any video link.\n\n"
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
        await query.edit_message_text(
            text="💠 **AI MODE ACTIVATED**\n\nSend me any question or prompt, and I will generate a smart response for you.", 
            parse_mode='Markdown'
        )
    elif query.data == 'video_dl':
        await query.edit_message_text(
            text="🎬 **DOWNLOADER MODE**\n\nPaste any video link (YouTube, Instagram, TikTok, Facebook) and I will download it instantly.", 
            parse_mode='Markdown'
        )

# ==========================================
# 4. MESSAGE HANDLER (AI Chat & Video Downloader)
# ==========================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    
    # VIDEO DOWNLOADER
    if text.startswith("http://") or text.startswith("https://"):
        status_msg = await update.message.reply_text("🔄 **Processing Link...** Please wait, checking the video quality.")
        
        ydl_opts = {
            'format': 'best',
            'outtmpl': 'video.mp4',
            'quiet': True
        }
        
        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([text])
            
            await status_msg.edit_text("📤 **Download Complete!** Uploading your video now...")
            
            with open('video.mp4', 'rb') as video_file:
                await update.message.reply_video(
                    video=video_file, 
                    caption="✨ **Video Downloaded Successfully!**\n\n🤖 Powered by Dream AI Bot."
                )
            
            os.remove('video.mp4')
            await status_msg.delete()
            
        except Exception as e:
            await status_msg.edit_text("❌ **Error:** I couldn't download this link. Please make sure the link is public and valid.")
            print(f"Download error: {e}")
            
    # AI CHAT
    else:
        status_msg = await update.message.reply_text("🧠 **AI is thinking...**")
        
        try:
            prompt = f"You are a highly intelligent, friendly AI. Answer this clearly in English: {text}"
            encoded_prompt = requests.utils.quote(prompt)
            response = requests.get(f"https://text.pollinations.ai/{encoded_prompt}")
            
            if response.status_code == 200:
                ai_reply = response.text
                formatted_reply = (
                    "╔══════════════════════╗\n"
                    "   🤖 **AI RESPONSE**\n"
                    "╚══════════════════════╝\n\n"
                    f"{ai_reply}\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━"
                )
                await update.message.reply_text(formatted_reply, parse_mode='Markdown')
                await status_msg.delete()
            else:
                await status_msg.edit_text("❌ **Server Busy:** The AI is currently overloaded. Please try again shortly.")
                
        except Exception as e:
            await status_msg.edit_text("❌ **Connection Error:** Failed to reach the AI server.")
            print(f"AI error: {e}")

# ==========================================
# 5. RUN THE BOT
# ==========================================
if __name__ == '__main__':
    print("Starting Dream AI Bot...")
    application = ApplicationBuilder().token(TOKEN).build()
    
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_click))
    
    print("Bot is online and running!")
    application.run_polling()
