import os
import time
import logging
import requests
import yt_dlp
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, CallbackQueryHandler
)

# ==========================================
# 1. টোকেন (পরিবেশ ভেরিয়েবল থেকে পড়ার পরামর্শ দেওয়া হয়)
# ==========================================
TOKEN = os.getenv("BOT_TOKEN", "9029968342:AAG-XRHnHFhkbW7bxiZbegqYb3rWuYxNMh4")

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ==========================================
# 2. START কমান্ড
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_name = update.effective_user.first_name

    keyboard = [
        [
            InlineKeyboardButton("💬 AI-এর সাথে চ্যাট", callback_data='ai_chat'),
            InlineKeyboardButton("🎬 ভিডিও ডাউনলোড", callback_data='video_dl')
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    welcome_text = (
        "╔══════════════════════╗\n"
        "   ✨ **SUMAIYA BOT** ✨\n"
        "╚══════════════════════╝\n\n"
        f"👋 স্বাগতম **{user_name}**,\n"
        "আমি একটি স্মার্ট AI বট। যেকোনো ভাষায় আমার সাথে চ্যাট করতে পারেন, অথবা যেকোনো ভিডিও লিংক পাঠিয়ে ডাউনলোড করতে পারেন।\n\n"
        "👇 **শুরু করতে নিচের বাটনে ক্লিক করুন:**"
    )
    await update.message.reply_text(welcome_text, reply_markup=reply_markup, parse_mode='Markdown')


# ==========================================
# 3. বাটন ক্লিক হ্যান্ডলার (মোড সংরক্ষণ)
# ==========================================
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == 'ai_chat':
        context.user_data['mode'] = 'ai'
        keyboard = [[InlineKeyboardButton("🎬 ভিডিও ডাউনলোডে যান", callback_data='video_dl')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text="💠 **AI চ্যাট মোড চালু হয়েছে!**\n\nযেকোনো ভাষায় প্রশ্ন পাঠান, আমি সেই ভাষাতেই উত্তর দেব।",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )
    elif query.data == 'video_dl':
        context.user_data['mode'] = 'video'
        keyboard = [[InlineKeyboardButton("💬 চ্যাটে ফিরে যান", callback_data='ai_chat')]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(
            text="🎬 **ভিডিও ডাউনলোড মোড!**\n\nযেকোনো ভিডিও লিংক (YouTube, Facebook, TikTok) পেস্ট করুন, আমি ডাউনলোড করে পাঠিয়ে দেব।",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )


# ==========================================
# 4. AI অনুরোধ (পুনরায় চেষ্টাসহ)
# ==========================================
def ask_ai(text: str, max_retries: int = 3) -> str:
    """
    Pollinations OpenAI-সামঞ্জস্যপূর্ণ ইন্টারফেস কল করুন, ব্যর্থ হলে পুনরায় চেষ্টা করুন।
    সফল হলে AI উত্তর স্ট্রিং রিটার্ন করে; সব ব্যর্থ হলে None রিটার্ন করে।
    """
    url = "https://text.pollinations.ai/openai"
    payload = {
        "model": "openai",
        "messages": [
            {
                "role": "system",
                "content": "You are a helpful AI assistant. Always reply in the same language the user used."
            },
            {"role": "user", "content": text}
        ]
    }
    headers = {"Content-Type": "application/json"}

    for attempt in range(max_retries):
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=25)
            if resp.status_code == 200:
                data = resp.json()
                content = data["choices"][0]["message"]["content"]
                if content and content.strip():
                    return content.strip()
            logger.warning(f"AI অনুরোধ ব্যর্থ, স্ট্যাটাস কোড: {resp.status_code}, চেষ্টা: {attempt + 1}")
        except Exception as e:
            logger.warning(f"AI অনুরোধে ত্রুটি (চেষ্টা {attempt + 1}): {e}")

        if attempt < max_retries - 1:
            time.sleep(1.5)  # পুনরায় চেষ্টার আগে অপেক্ষা করুন

    return None


# ==========================================
# 5. ভিডিও ডাউনলোড ফাংশন
# ==========================================
def download_video(url: str, user_id: int) -> str | None:
    """
    ভিডিও ডাউনলোড করুন, ফাইল পাথ রিটার্ন করুন; ব্যর্থ হলে None রিটার্ন করুন।
    """
    filename = f"video_{user_id}_{int(time.time())}.mp4"
    ydl_opts = {
        'format': 'best[ext=mp4]/best',
        'outtmpl': filename,
        'quiet': True,
        'no_warnings': True,
        'restrictfilenames': True,
    }
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])
        return filename if os.path.exists(filename) else None
    except Exception as e:
        logger.error(f"ভিডিও ডাউনলোড ব্যর্থ: {e}")
        return None


# ==========================================
# 6. মেসেজ হ্যান্ডলার
# ==========================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if not text:
        return

    mode = context.user_data.get('mode', 'ai')  # ডিফল্ট AI মোড

    # ---------- ভিডিও মোড ----------
    if mode == 'video' and (text.startswith("http://") or text.startswith("https://")):
        status_msg = await update.message.reply_text("🔄 **লিংক প্রসেস হচ্ছে…** অনুগ্রহ করে অপেক্ষা করুন।")
        file_path = None
        try:
            file_path = download_video(text, update.effective_user.id)
            if not file_path:
                await status_msg.edit_text("❌ **দুঃখিত, এই ভিডিওটি ডাউনলোড করা যায়নি।** লিংকটি পরীক্ষা করুন বা পরে আবার চেষ্টা করুন।")
                return

            await status_msg.edit_text("📤 **ডাউনলোড সম্পন্ন!** ভিডিও আপলোড হচ্ছে…")
            with open(file_path, 'rb') as video_file:
                await update.message.reply_video(
                    video=video_file,
                    caption="✨ **ভিডিও সফলভাবে ডাউনলোড হয়েছে!**\n\n🤖 Sumaiya Bot দ্বারা প্রস্তুতকৃত।"
                )
            await status_msg.delete()
        except Exception as e:
            logger.error(f"ভিডিও পাঠানোর সময় ত্রুটি: {e}")
            try:
                await status_msg.edit_text("❌ **ভিডিও পাঠাতে সমস্যা হয়েছে।**")
            except:
                pass
        finally:
            if file_path and os.path.exists(file_path):
                try:
                    os.remove(file_path)
                except:
                    pass

    # ---------- AI মোড ----------
    else:
        status_msg = await update.message.reply_text("🧠 **AI ভাবছে…**")
        try:
            ai_reply = ask_ai(text)
            if ai_reply:
                # সতর্কতামূলক: এখানে parse_mode='Markdown' ব্যবহার করা হয় না, টেলিগ্রাম পার্সিং ত্রুটি এড়াতে
                formatted = (
                    "╔══════════════════════╗\n"
                    "   🤖 **AI উত্তর**\n"
                    "╚══════════════════════╝\n\n"
                    f"{ai_reply}\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━"
                )
                nav_keyboard = [[InlineKeyboardButton("🎬 ভিডিও ডাউনলোডে যান", callback_data='video_dl')]]
                reply_markup = InlineKeyboardMarkup(nav_keyboard)
                await update.message.reply_text(formatted, reply_markup=reply_markup)
            else:
                await status_msg.edit_text(
                    "❌ **AI সার্ভার সাময়িকভাবে সাড়া দিচ্ছে না।**\n\n"
                    "অনুগ্রহ করে **কয়েক সেকেন্ড পরে** আবার চেষ্টা করুন, অথবা প্রশ্নটি অন্যভাবে জিজ্ঞাসা করুন।"
                )
        except Exception as e:
            logger.error(f"AI হ্যান্ডলিং ত্রুটি: {e}")
            try:
                await status_msg.edit_text("❌ **একটি অপ্রত্যাশিত ত্রুটি ঘটেছে।** অনুগ্রহ করে পরে আবার চেষ্টা করুন।")
            except:
                pass
        finally:
            # status_msg সফলভাবে reply_text দ্বারা প্রতিস্থাপিত হলে মুছে ফেলার চেষ্টা করুন (পার্থক্য না থাকলে বাদ দিন)
            try:
                await status_msg.delete()
            except:
                pass


# ==========================================
# 7. কমান্ড হ্যান্ডলার
# ==========================================
async def cmd_chat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['mode'] = 'ai'
    await update.message.reply_text("💠 **AI চ্যাট মোডে পরিবর্তিত হয়েছে।** যেকোনো প্রশ্ন পাঠান।")


async def cmd_video(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['mode'] = 'video'
    await update.message.reply_text("🎬 **ভিডিও ডাউনলোড মোডে পরিবর্তিত হয়েছে।** ভিডিও লিংক পাঠান।")


# ==========================================
# 8. গ্লোবাল ত্রুটি হ্যান্ডলার
# ==========================================
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error(f"আপডেট প্রসেস করার সময় ব্যতিক্রম: {context.error}", exc_info=context.error)


# ==========================================
# 9. কমান্ড সেট করুন
# ==========================================
async def set_commands(application):
    commands = [
        BotCommand("start", "বট শুরু করুন"),
        BotCommand("chat", "AI চ্যাট মোড"),
        BotCommand("video", "ভিডিও ডাউনলোড মোড")
    ]
    await application.bot.set_my_commands(commands)


# ==========================================
# 10. চালান
# ==========================================
if __name__ == '__main__':
    print("Sumaiya Bot চালু হচ্ছে…")
    application = (
        ApplicationBuilder()
        .token(TOKEN)
        .post_init(set_commands)
        .build()
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("chat", cmd_chat))
    application.add_handler(CommandHandler("video", cmd_video))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_click))
    application.add_error_handler(error_handler)

    print("Sumaiya Bot অনলাইন এবং চলছে!")
    application.run_polling()
