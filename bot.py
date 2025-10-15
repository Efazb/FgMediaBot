#!/usr/bin/env python3
import os
import json
import time
import shutil
import subprocess
import tempfile
import asyncio
from functools import wraps
from pathlib import Path

from pyrogram import Client, filters
from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message

# Load config (env preferred)
API_ID = int(os.environ.get("API_ID", "123456"))
API_HASH = os.environ.get("API_HASH", "your_api_hash_here")
BOT_TOKEN = os.environ.get("BOT_TOKEN", "123456:ABC-DEF")
# Admin identity: prefer numeric ADMIN_ID but username fallback allowed
ADMIN_ID = int(os.environ.get("ADMIN_ID") or "0")
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME") or "Efab429"

# Compression defaults (env overrides allowed)
AUDIO_BITRATE = os.environ.get("AUDIO_BITRATE") or "32k"
AUDIO_FORMAT = os.environ.get("AUDIO_FORMAT") or "mp3"
AUDIO_CHANNELS = int(os.environ.get("AUDIO_CHANNELS") or "1")
AUDIO_SAMPLE_RATE = int(os.environ.get("AUDIO_SAMPLE_RATE") or "44100")

VIDEO_SCALE = os.environ.get("VIDEO_SCALE") or "640:360"
VIDEO_CRF = int(os.environ.get("VIDEO_CRF") or "28")
VIDEO_PRESET = os.environ.get("VIDEO_PRESET") or "fast"
VIDEO_AUDIO_BITRATE = os.environ.get("VIDEO_AUDIO_BITRATE") or "64k"

USERS_DB = os.environ.get("USERS_DB") or "users.json"

# i18n strings
STRINGS = {
    "en": {
        "start": "👋 Hello! I'm *FgMediaBot* — your friendly media compressor.\\n\\nChoose an option below ⬇️",
        "help": "ℹ️ *How to use*\\n\\n• Send an audio or video file and I will compress it.\\n• Use the buttons to select options.",
        "about": "FgMediaBot — compress audio & video with minimal quality loss.\\nMade with ❤️",
        "compressing": "⏳ Compressing your file... This may take a bit. I'll send it when done.",
        "done_audio": "✅ Audio compressed! Saved {old} → {new} ({pct} saved).",
        "done_video": "✅ Video compressed! Saved {old} → {new} ({pct} saved).",
        "error": "⚠️ Something went wrong: {err}",
        "choose_lang": "Choose language / ቋንቋ ይምረጡ",
        "stats": "📊 Your Stats\\n• Files compressed: {count}\\n• Total saved: {saved}",
        "admin_only": "🚫 Admin only command.",
        "deleted": "✅ Deleted.",
    },
    "am": {
        "start": "👋 ሰላም! እኔ *FgMediaBot* ነኝ — የሚጠቃሚ የሚዲያ ኮምፕሬሰር።\\n\\nከከታች አማራጮችን ይምረጡ ⬇️",
        "help": "ℹ️ *እንዴት ታገለግላለህ*\\n\\n• ኦዲዮ ወይም ቪዲዮ ፋይል ላክና ኮምፕሬስ ይምረጡ።",
        "about": "FgMediaBot — ኦዲዮና ቪዲዮ በጥራት ያለው እና በታቀለ መልኩ ይኮምፕሬስ ያደርጋል።",
        "compressing": "⏳ ፋይሉን እኮምፕሬስ እሰራለሁ... እባክህ ትንሽ ቆይ።",
        "done_audio": "✅ የኦዲዮ ኮምፕሬሽን ተጠናቋል! {old} → {new} ({pct} ተቀንሷል).",
        "done_video": "✅ የቪዲዮ ኮምፕሬሽን ተጠናቋል! {old} → {new} ({pct} ተቀንሷል).",
        "error": "⚠️ ችግኝ ተከስቷል: {err}",
        "choose_lang": "Choose language / ቋንቋ ይምረጡ",
        "stats": "📊 የእርስዎ ስታቲስቲክስ\\n• የተኮምፕሬስ ፋይሎች: {count}\\n• ጠቅላላ የታቀረ መጠን: {saved}",
        "admin_only": "🚫 ለአስተዳደር ብቻ።",
        "deleted": "✅ ተደርጓል።",
    }
}

def load_db(path=USERS_DB):
    if not os.path.exists(path):
        with open(path, "w") as f:
            json.dump({}, f)
    with open(path, "r") as f:
        return json.load(f)

def save_db(data, path=USERS_DB):
    with open(path, "w") as f:
        json.dump(data, f, indent=2)

def get_lang(user_id):
    db = load_db()
    user = db.get(str(user_id), {})
    return user.get("lang", "en")

def set_lang(user_id, lang):
    db = load_db()
    u = db.setdefault(str(user_id), {})
    u["lang"] = lang
    save_db(db)

def add_stats(user_id, saved_bytes):
    db = load_db()
    u = db.setdefault(str(user_id), {})
    u["count"] = u.get("count", 0) + 1
    u["saved"] = u.get("saved", 0) + int(saved_bytes)
    save_db(db)

def human_size(n):
    try:
        n = float(n)
    except:
        return "0B"
    for unit in ["B","KB","MB","GB","TB"]:
        if abs(n) < 1024.0:
            return f"{n:3.1f}{unit}"
        n /= 1024.0
    return f"{n:.1f}PB"

def is_admin(user):
    try:
        if ADMIN_ID and int(user.id) == int(ADMIN_ID):
            return True
    except:
        pass
    try:
        if user.username and user.username.lower().strip() == ADMIN_USERNAME.lower().strip().lstrip("@"):
            return True
    except:
        pass
    return False

def admin_only(func):
    @wraps(func)
    async def wrapper(client, message):
        if not is_admin(message.from_user):
            lang = get_lang(message.from_user.id)
            await message.reply_text(STRINGS[lang]["admin_only"])
            return
        return await func(client, message)
    return wrapper

# Build client
app = Client("fgmediabot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, workdir=".")

def main_keyboard(lang="en"):
    t = STRINGS[lang]
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("🎧 Compress Audio", callback_data="menu_compress_audio"),
         InlineKeyboardButton("🎥 Compress Video", callback_data="menu_compress_video")],
        [InlineKeyboardButton("💬 Help", callback_data="menu_help"),
         InlineKeyboardButton("ℹ️ About", callback_data="menu_about")],
        [InlineKeyboardButton("🌐 ቋንቋ / Language", callback_data="menu_lang"),
         InlineKeyboardButton("📊 My Stats", callback_data="menu_stats")]
    ])

@app.on_message(filters.command("start"))
async def start(client, message: Message):
    # show lang select if new user
    db = load_db()
    uid = str(message.from_user.id)
    if uid not in db:
        # default set to english until they choose
        db[uid] = {"lang": "en", "count": 0, "saved": 0}
        save_db(db)
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("English 🇬🇧", callback_data="lang_en"),
             InlineKeyboardButton("አማርኛ 🇪🇹", callback_data="lang_am")]
        ])
        await message.reply_text(STRINGS["en"]["choose_lang"], reply_markup=kb)
        return
    lang = get_lang(message.from_user.id)
    await message.reply_text(STRINGS[lang]["start"], reply_markup=main_keyboard(lang), parse_mode="markdown")

@app.on_callback_query()
async def cb_handler(client, cq):
    data = cq.data or ""
    user_id = cq.from_user.id
    lang = get_lang(user_id)
    t = STRINGS[lang]

    if data == "menu_help":
        await cq.answer()
        await cq.message.edit_text(t["help"], reply_markup=main_keyboard(lang), parse_mode="markdown")
    elif data == "menu_about":
        await cq.answer()
        await cq.message.edit_text(t["about"], reply_markup=main_keyboard(lang), parse_mode="markdown")
    elif data == "menu_lang":
        await cq.answer()
        kb = InlineKeyboardMarkup([
            [InlineKeyboardButton("English 🇬🇧", callback_data="lang_en"),
             InlineKeyboardButton("አማርኛ 🇪🇹", callback_data="lang_am")],
            [InlineKeyboardButton("⬅️ Back", callback_data="back_main")]
        ])
        await cq.message.edit_text(t["choose_lang"], reply_markup=kb)
    elif data in ("lang_en", "lang_am"):
        await cq.answer("Saved ✅")
        set_lang(user_id, "en" if data == "lang_en" else "am")
        lang = get_lang(user_id)
        await cq.message.edit_text(STRINGS[lang]["start"], reply_markup=main_keyboard(lang), parse_mode="markdown")
    elif data == "back_main":
        await cq.answer()
        await cq.message.edit_text(STRINGS[lang]["start"], reply_markup=main_keyboard(lang), parse_mode="markdown")
    elif data == "menu_stats":
        await cq.answer()
        db = load_db()
        u = db.get(str(user_id), {})
        count = u.get("count", 0)
        saved = human_size(u.get("saved", 0))
        await cq.message.edit_text(STRINGS[lang]["stats"].format(count=count, saved=saved), reply_markup=InlineKeyboardMarkup([
            [InlineKeyboardButton("🗑️ Reset Stats", callback_data="reset_stats"), InlineKeyboardButton("⬅️ Back", callback_data="back_main")]
        ]))
    elif data == "reset_stats":
        await cq.answer()
        db = load_db()
        if str(user_id) in db:
            db[str(user_id)]["count"] = 0
            db[str(user_id)]["saved"] = 0
            save_db(db)
        await cq.message.edit_text(STRINGS[lang]["deleted"], reply_markup=main_keyboard(lang))
    elif data == "menu_compress_audio":
        await cq.answer()
        await cq.message.edit_text("📎 Send me an audio file (mp3, m4a, wav) and I will compress it.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back_main")]]))
    elif data == "menu_compress_video":
        await cq.answer()
        await cq.message.edit_text("📎 Send me a video (mp4, mov, mkv) and I will compress it for you.", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⬅️ Back", callback_data="back_main")]]))
    else:
        await cq.answer()

async def run_cmd(cmd, edit_msg=None, prefix=""):
    proc = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.STDOUT)
    while True:
        line = await proc.stdout.readline()
        if not line:
            break
        if edit_msg:
            try:
                # show short preview of ffmpeg output for feedback
                await edit_msg.edit_text(prefix + " " + line.decode(errors="ignore")[:200])
            except:
                pass
    await proc.wait()
    return proc.returncode

@app.on_message(filters.audio | filters.voice)
async def audio_handler(client, message: Message):
    lang = get_lang(message.from_user.id)
    t = STRINGS[lang]
    status = await message.reply_text(t["compressing"])
    try:
        file_path = await client.download_media(message)
        orig_size = os.path.getsize(file_path)
        tmp = tempfile.NamedTemporaryFile(suffix="." + AUDIO_FORMAT, delete=False)
        tmp.close()
        out_path = tmp.name
        cmd = f'ffmpeg -y -i "{file_path}" -vn -ac {AUDIO_CHANNELS} -ar {AUDIO_SAMPLE_RATE} -b:a {AUDIO_BITRATE} "{out_path}"'
        await run_cmd(cmd, edit_msg=status, prefix="🔊 Compressing audio...")
        new_size = os.path.getsize(out_path)
        await status.edit_text("✅ Uploading compressed audio...")
        await client.send_audio(message.chat.id, audio=out_path, caption="Compressed by FgMediaBot")
        saved = orig_size - new_size
        add_stats(message.from_user.id, saved)
        pct = int((saved / orig_size) * 100) if orig_size else 0
        await status.edit_text(t["done_audio"].format(old=human_size(orig_size), new=human_size(new_size), pct=f"{pct}%"))
    except Exception as e:
        await status.edit_text(t["error"].format(err=str(e)))
    finally:
        for f in (locals().get("file_path", None), locals().get("out_path", None)):
            try:
                if f and os.path.exists(f):
                    os.remove(f)
            except:
                pass

@app.on_message(filters.video | filters.animation)
async def video_handler(client, message: Message):
    lang = get_lang(message.from_user.id)
    t = STRINGS[lang]
    status = await message.reply_text(t["compressing"])
    try:
        file_path = await client.download_media(message)
        orig_size = os.path.getsize(file_path)
        tmp = tempfile.NamedTemporaryFile(suffix=".mp4", delete=False)
        tmp.close()
        out_path = tmp.name
        codec = "libx265"
        cmd = (
            f'ffmpeg -y -i "{file_path}" -vcodec {codec} -crf {VIDEO_CRF} -preset {VIDEO_PRESET} '
            f'-vf "scale={VIDEO_SCALE}" -r 24 -acodec aac -b:a {VIDEO_AUDIO_BITRATE} "{out_path}"'
        )
        await run_cmd(cmd, edit_msg=status, prefix="🎬 Compressing video...")
        new_size = os.path.getsize(out_path)
        await status.edit_text("✅ Uploading compressed video...")
        await client.send_video(message.chat.id, video=out_path, caption="Compressed by FgMediaBot")
        saved = orig_size - new_size
        add_stats(message.from_user.id, saved)
        pct = int((saved / orig_size) * 100) if orig_size else 0
        await status.edit_text(t["done_video"].format(old=human_size(orig_size), new=human_size(new_size), pct=f"{pct}%"))
    except Exception as e:
        await status.edit_text(t["error"].format(err=str(e)))
    finally:
        for f in (locals().get("file_path", None), locals().get("out_path", None)):
            try:
                if f and os.path.exists(f):
                    os.remove(f)
            except:
                pass

@app.on_message(filters.command("broadcast") & filters.user(ADMIN_ID))
@admin_only
async def broadcast(client, message: Message):
    text = message.text.partition(" ")[2]
    if not text:
        await message.reply_text("Usage: /broadcast <message>")
        return
    db = load_db()
    count = 0
    for uid in list(db.keys()):
        try:
            await client.send_message(int(uid), text)
            count += 1
            await asyncio.sleep(0.05)
        except:
            pass
    await message.reply_text(f"Broadcast sent to {count} users.")

@app.on_message(filters.command("stats"))
async def my_stats(client, message: Message):
    lang = get_lang(message.from_user.id)
    db = load_db()
    u = db.get(str(message.from_user.id), {})
    await message.reply_text(STRINGS[lang]["stats"].format(count=u.get("count", 0), saved=human_size(u.get("saved", 0))))

@app.on_message(filters.command("about"))
async def about_cmd(client, message: Message):
    lang = get_lang(message.from_user.id)
    await message.reply_text(STRINGS[lang]["about"])

if __name__ == "__main__":
    print("Starting FgMediaBot...")
    app.run()
