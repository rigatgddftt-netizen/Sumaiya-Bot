import os
import time
import uuid
import asyncio
import logging
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, BotCommand
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
import yt_dlp

# ==========================================
# 1. BOT TOKEN & LOGGING
# ==========================================
TOKEN = os.getenv("BOT_TOKEN")
if not TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable set করুন! (BotFather থেকে নতুন টোকেন নিন)")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

MAX_TELEGRAM_MSG_LEN = 3800


def _split_text(text: str, limit: int = MAX_TELEGRAM_MSG_LEN) -> list[str]:
    if len(text) <= limit:
        return [text]
    chunks: list[str] = []
    current = ""
    for line in text.split("\n"):
        if len(line) > limit:
            if current:
                chunks.append(current)
                current = ""
            start = 0
            while start < len(line):
                end = min(start + limit, len(line))
                if end < len(line):
                    space_idx = line.rfind(" ", start, end)
                    if space_idx > start:
                        end = space_idx
                chunks.append(line[start:end].strip())
                start = end
            continue
        candidate = f"{current}\n{line}" if current else line
        if len(candidate) > limit:
            if current:
                chunks.append(current)
            current = line
        else:
            current = candidate
    if current:
        chunks.append(current)
    return chunks


# ==========================================
# 2. SYNC WORKERS (RUN IN THREADS)
# ==========================================
def _download_video_sync(url: str, output_template: str) -> None:
    ydl_opts = {
        "format": "best[filesize<48M][ext=mp4]/best[ext=mp4]/best[filesize<48M]/best",
        "outtmpl": output_template,
        "quiet": True,
        "no_warnings": True,
        "noplaylist": True,
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


# নতুন এন্ডপয়েন্ট: DuckDuckGo AI (সম্পূর্ণ ফ্রি)
def _ask_duckduckgo(prompt: str) -> str:
    url = "https://api.duckduckgo.com/"
    params = {"q": prompt, "format": "json", "no_html": 1, "skip_disambig": 1}
    resp = requests.get(url, params=params, timeout=15)
    resp.raise_for_status()
    data = resp.json()
    answer = data.get("AbstractText", "")
    if answer:
        return answer
    # ফলব্যাক: DuckDuckGo চ্যাট
    url2 = "https://quack.duckduckgo.com/api/chat"
    payload = {"messages": [{"role": "user", "content": prompt}]}
    resp2 = requests.post(url2, json=payload, timeout=15)
    resp2.raise_for_status()
    return resp2.json().get("message", "").strip()

# ফলব্যাক হিসেবে Pollinations GET (যদি DDG ফেইল করে)
def _ask_pollinations_get(prompt: str) -> str:
    url = f"https://text.pollinations.ai/{requests.utils.quote(prompt)}"
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    return resp.text.strip()


def _fetch_ai_sync(prompt: str) -> str:
    providers = [
        ("DuckDuckGo", _ask_duckduckgo),
        ("Pollinations-GET", _ask_pollinations_get),
    ]

    last_error = None
    for name, fn in providers:
        for attempt in range(2):
            try:
                answer = fn(prompt)
                if answer and len(answer) > 1:
                    return answer
                break
            except Exception as exc:
                last_error = exc
                logger.warning("%s attempt %d failed: %s", name, attempt + 1, exc)
                if attempt == 0:
                    time.sleep(1.0)

    raise RuntimeError(f"All AI providers failed: {last_error}")


# ==========================================
# 3. COMMANDS (/start, /chat, /video)
# ==========================================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    context.user_data.setdefault("mode", "ai_chat")
    user_name = update.effective_user.first_name if update.effective_user else "User"
    keyboard = [
        [
            InlineKeyboardButton("💬 Chat with AI", callback_data="ai_chat"),
            InlineKeyboardButton("🎬 Video Downloader", callback_data="video_dl"),
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    welcome_text = (
        "╔══════════════════════╗\n"
        "   ✨ SUMAIYA BOT ✨\n"
        "╚══════════════════════╝\n\n"
        f"👋 Welcome {user_name},\n"
        "I am a smart AI bot. You can chat with me in any language, or download any video instantly.\n\n"
        "👇 Tap a button below to begin:"
    )
    await update.message.reply_text(welcome_text, reply_markup=reply_markup)


async def chat_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    context.user_data["mode"] = "ai_chat"
    keyboard = [[InlineKeyboardButton("🎬 Switch to Video Download", callback_data="video_dl")]]
    await update.message.reply_text(
        "💠 AI CHAT MODE ACTIVATED!\n\nSend me any question in any language, and I will reply in the same language.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def video_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message:
        return
    context.user_data["mode"] = "video_dl"
    keyboard = [[InlineKeyboardButton("💬 Switch to Chat", callback_data="ai_chat")]]
    await update.message.reply_text(
        "🎬 VIDEO DOWNLOADER MODE!\n\nPaste any video link (YouTube, Facebook, TikTok) and I will download it instantly.",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


# ==========================================
# 4. BUTTON CLICK HANDLER
# ==========================================
async def button_click(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if not query:
        return
    await query.answer()
    if query.data == "ai_chat":
        context.user_data["mode"] = "ai_chat"
        keyboard = [[InlineKeyboardButton("🎬 Switch to Video Download", callback_data="video_dl")]]
        await query.edit_message_text(
            text="💠 AI CHAT MODE ACTIVATED!\n\nSend me any question in any language, and I will reply in the same language.",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )
    elif query.data == "video_dl":
        context.user_data["mode"] = "video_dl"
        keyboard = [[InlineKeyboardButton("💬 Switch to Chat", callback_data="ai_chat")]]
        await query.edit_message_text(
            text="🎬 VIDEO DOWNLOADER MODE!\n\nPaste any video link (YouTube, Facebook, TikTok) and I will download it instantly.",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )


# ==========================================
# 5. MESSAGE HANDLER (AI & DOWNLOADER)
# ==========================================
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    text = update.message.text.strip()
    mode = context.user_data.get("mode", "ai_chat")

    if mode == "video_dl":
        if not (text.startswith("http://") or text.startswith("https://")):
            keyboard = [[InlineKeyboardButton("💬 Switch to Chat", callback_data="ai_chat")]]
            await update.message.reply_text(
                "🎬 আপনি এখন Video Downloader মোডে আছেন। অনুগ্রহ করে একটি বৈধ ভিডিও লিংক (http/https) পাঠান।",
                reply_markup=InlineKeyboardMarkup(keyboard),
            )
            return

        status_msg = await update.message.reply_text("🔄 Processing Link... Please wait.")
        unique_id = uuid.uuid4().hex
        output_template = f"video_{unique_id}.%(ext)s"
        downloaded_file = None

        try:
            await asyncio.to_thread(_download_video_sync, text, output_template)
            for fname in os.listdir("."):
                if fname.startswith(f"video_{unique_id}."):
                    downloaded_file = fname
                    break
            if not downloaded_file or not os.path.exists(downloaded_file):
                raise FileNotFoundError("Video file not created.")
            file_size = os.path.getsize(downloaded_file)
            if file_size > 49 * 1024 * 1024:
                await status_msg.edit_text("❌ ভিডিওটির সাইজ Telegram-এর আপলোড সীমার (৫০ MB) চেয়ে বড়।")
                return
            await status_msg.edit_text("📤 Download Complete! Uploading video...")
            nav_keyboard = [[InlineKeyboardButton("💬 Chat with AI", callback_data="ai_chat")]]
            with open(downloaded_file, "rb") as video_file:
                await update.message.reply_video(
                    video=video_file,
                    caption="✨ Video Downloaded Successfully!\n\n🤖 Powered by Sumaiya Bot.",
                    reply_markup=InlineKeyboardMarkup(nav_keyboard),
                )
        except Exception as e:
            logger.error("Download error: %s", e)
            try:
                await status_msg.edit_text("❌ Sorry, I couldn't download this video. Please check the link or try another one.")
            except Exception:
                pass
        finally:
            if downloaded_file and os.path.exists(downloaded_file):
                try:
                    os.remove(downloaded_file)
                except OSError:
                    pass
            try:
                await status_msg.delete()
            except Exception:
                pass

    else:
        status_msg = await update.message.reply_text("🧠 AI is thinking...")
        try:
            prompt = f"You are a helpful AI assistant. Please answer in the same language the user used. User: {text}"
            ai_reply = await asyncio.to_thread(_fetch_ai_sync, prompt)
            chunks = _split_text(ai_reply)
            nav_keyboard = [[InlineKeyboardButton("🎬 Switch to Video Download", callback_data="video_dl")]]
            reply_markup = InlineKeyboardMarkup(nav_keyboard)
            for idx, chunk in enumerate(chunks):
                formatted_reply = (
                    "╔══════════════════════╗\n"
                    "   🤖 AI RESPONSE\n"
                    "╚══════════════════════╝\n\n"
                    f"{chunk}\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━"
                )
                if idx == len(chunks) - 1:
                    await update.message.reply_text(formatted_reply, reply_markup=reply_markup)
                else:
                    await update.message.reply_text(formatted_reply)
        except Exception as e:
            logger.error("AI error: %s", e)
            try:
                await status_msg.edit_text("❌ All AI servers are busy right now. Please try again in a few seconds.")
            except Exception:
                pass
        finally:
            try:
                await status_msg.delete()
            except Exception:
                pass


# ==========================================
# 6. SET BOT COMMANDS
# ==========================================
async def set_commands(application):
    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("chat", "AI Chat Mode"),
        BotCommand("video", "Video Download Mode"),
    ]
    await application.bot.set_my_commands(commands)


# ==========================================
# 7. RUN THE BOT (WEBHOOK FOR RENDER)
# ==========================================
if __name__ == "__main__":
    print("Starting Sumaiya Bot...")
    application = (
        ApplicationBuilder()
        .token(TOKEN)
        .post_init(set_commands)
        .build()
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("chat", chat_command))
    application.add_handler(CommandHandler("video", video_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    application.add_handler(CallbackQueryHandler(button_click))

    # Render-এর জন্য Webhook সেটআপ
    PORT = int(os.environ.get("PORT", 8080))
    RENDER_EXTERNAL_URL = os.environ.get("RENDER_EXTERNAL_URL")

    if RENDER_EXTERNAL_URL:
        print(f"Starting Webhook on {RENDER_EXTERNAL_URL}")
        application.run_webhook(
            listen="0.0.0.0",
            port=PORT,
            url_path=TOKEN,
            webhook_url=f"{RENDER_EXTERNAL_URL}/{TOKEN}",
        )
    else:
        print("RENDER_EXTERNAL_URL not found. Falling back to Polling (Local testing).")
        application.run_polling(allowed_updates=Update.ALL_TYPES)
