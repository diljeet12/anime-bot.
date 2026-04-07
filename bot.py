import logging
import sqlite3
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, filters, ContextTypes
)
from telegram.error import TelegramError
from config import BOT_TOKEN, FORCE_SUB_CHANNEL, ADMIN_IDS, DB_FILE

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────
# DATABASE HELPERS
# ─────────────────────────────────────────────

def get_db():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()
    c.executescript("""
        CREATE TABLE IF NOT EXISTS animes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            description TEXT,
            poster_file_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS episodes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            anime_id INTEGER NOT NULL,
            episode_number INTEGER NOT NULL,
            title TEXT,
            file_id TEXT NOT NULL,
            file_type TEXT DEFAULT 'video',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (anime_id) REFERENCES animes(id)
        );

        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
    """)
    conn.commit()
    conn.close()

# ─────────────────────────────────────────────
# FORCE SUBSCRIBE CHECK
# ─────────────────────────────────────────────

async def is_subscribed(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(FORCE_SUB_CHANNEL, user_id)
        return member.status in ("member", "administrator", "creator")
    except TelegramError:
        return False

async def force_subscribe_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send force subscribe prompt."""
    keyboard = [
        [InlineKeyboardButton("🔔 Join Our Group", url=f"https://t.me/{FORCE_SUB_CHANNEL.lstrip('@')}")],
        [InlineKeyboardButton("✅ I've Joined — Check Now", callback_data="check_sub")]
    ]
    await update.effective_message.reply_text(
        "🚫 *Access Denied!*\n\n"
        "You must join our community group to get anime episodes.\n\n"
        "1️⃣ Click *Join Our Group* below\n"
        "2️⃣ Then click *I've Joined* to verify\n\n"
        "💡 This helps us keep the bot alive for everyone!",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ─────────────────────────────────────────────
# USER REGISTRATION
# ─────────────────────────────────────────────

def register_user(user):
    conn = get_db()
    conn.execute(
        "INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
        (user.id, user.username, user.first_name)
    )
    conn.commit()
    conn.close()

# ─────────────────────────────────────────────
# /start COMMAND
# ─────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    register_user(user)

    if not await is_subscribed(user.id, context):
        await force_subscribe_message(update, context)
        return

    # If started with a deep link like /start anime_5
    if context.args:
        arg = context.args[0]
        if arg.startswith("anime_"):
            anime_id = arg.split("_")[1]
            await show_episodes(update, context, anime_id)
            return

    await show_anime_list(update, context)

# ─────────────────────────────────────────────
# ANIME LIST
# ─────────────────────────────────────────────

async def show_anime_list(update: Update, context: ContextTypes.DEFAULT_TYPE):
    conn = get_db()
    animes = conn.execute("SELECT * FROM animes ORDER BY title").fetchall()
    conn.close()

    if not animes:
        await update.effective_message.reply_text(
            "📭 No anime available yet. Check back soon!",
            parse_mode="Markdown"
        )
        return

    keyboard = []
    for anime in animes:
        keyboard.append([InlineKeyboardButton(
            f"🎬 {anime['title']}",
            callback_data=f"anime_{anime['id']}"
        )])

    await update.effective_message.reply_text(
        "🌸 *Welcome to the Anime Bot!*\n\n"
        "Choose an anime below to get episodes:",
        parse_mode="Markdown",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

# ─────────────────────────────────────────────
# EPISODE LIST
# ─────────────────────────────────────────────

async def show_episodes(update: Update, context: ContextTypes.DEFAULT_TYPE, anime_id: str):
    conn = get_db()
    anime = conn.execute("SELECT * FROM animes WHERE id = ?", (anime_id,)).fetchone()
    episodes = conn.execute(
        "SELECT * FROM episodes WHERE anime_id = ? ORDER BY episode_number",
        (anime_id,)
    ).fetchall()
    conn.close()

    if not anime:
        await update.effective_message.reply_text("❌ Anime not found.")
        return

    if not episodes:
        await update.effective_message.reply_text(
            f"📭 No episodes uploaded yet for *{anime['title']}*.",
            parse_mode="Markdown"
        )
        return

    keyboard = []
    row = []
    for i, ep in enumerate(episodes):
        label = f"Ep {ep['episode_number']}"
        row.append(InlineKeyboardButton(label, callback_data=f"ep_{ep['id']}"))
        if len(row) == 4:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)

    keyboard.append([InlineKeyboardButton("🔙 Back to Anime List", callback_data="list")])

    msg = f"📺 *{anime['title']}*\n"
    if anime["description"]:
        msg += f"\n_{anime['description']}_\n"
    msg += f"\n*{len(episodes)} episode(s) available*\nSelect an episode:"

    if anime["poster_file_id"]:
        await update.effective_message.reply_photo(
            photo=anime["poster_file_id"],
            caption=msg,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    else:
        await update.effective_message.reply_text(
            msg,
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

# ─────────────────────────────────────────────
# SEND EPISODE
# ─────────────────────────────────────────────

async def send_episode(update: Update, context: ContextTypes.DEFAULT_TYPE, ep_id: str):
    conn = get_db()
    ep = conn.execute(
        """SELECT e.*, a.title as anime_title
           FROM episodes e JOIN animes a ON e.anime_id = a.id
           WHERE e.id = ?""", (ep_id,)
    ).fetchone()
    conn.close()

    if not ep:
        await update.effective_message.reply_text("❌ Episode not found.")
        return

    caption = (
        f"🎬 *{ep['anime_title']}*\n"
        f"📺 Episode {ep['episode_number']}"
        + (f" — {ep['title']}" if ep['title'] else "")
        + "\n\n_Enjoy watching! 🍿_"
    )

    back_keyboard = InlineKeyboardMarkup([[
        InlineKeyboardButton("🔙 Back to Episodes", callback_data=f"anime_{ep['anime_id']}")
    ]])

    try:
        if ep["file_type"] == "document":
            await update.effective_message.reply_document(
                document=ep["file_id"],
                caption=caption,
                parse_mode="Markdown",
                reply_markup=back_keyboard
            )
        else:
            await update.effective_message.reply_video(
                video=ep["file_id"],
                caption=caption,
                parse_mode="Markdown",
                reply_markup=back_keyboard
            )
    except TelegramError as e:
        await update.effective_message.reply_text(f"❌ Could not send episode: {e}")

# ─────────────────────────────────────────────
# CALLBACK QUERY HANDLER
# ─────────────────────────────────────────────

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user = query.from_user
    await query.answer()

    if query.data == "check_sub":
        if await is_subscribed(user.id, context):
            await query.message.edit_text(
                "✅ *Verified! Welcome!*\n\nLoading anime list...",
                parse_mode="Markdown"
            )
            await show_anime_list(update, context)
        else:
            keyboard = [
                [InlineKeyboardButton("🔔 Join Our Group", url=f"https://t.me/{FORCE_SUB_CHANNEL.lstrip('@')}")],
                [InlineKeyboardButton("✅ I've Joined — Check Now", callback_data="check_sub")]
            ]
            await query.message.edit_text(
                "❌ *Still not joined!*\n\n"
                "Please join the group first, then click verify again.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return

    if query.data == "list":
        await show_anime_list(update, context)
        return

    if query.data.startswith("anime_"):
        if not await is_subscribed(user.id, context):
            await force_subscribe_message(update, context)
            return
        anime_id = query.data.split("_")[1]
        await show_episodes(update, context, anime_id)
        return

    if query.data.startswith("ep_"):
        if not await is_subscribed(user.id, context):
            await force_subscribe_message(update, context)
            return
        ep_id = query.data.split("_")[1]
        await send_episode(update, context, ep_id)
        return

# ─────────────────────────────────────────────
# ADMIN COMMANDS
# ─────────────────────────────────────────────

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

async def add_anime(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        await update.message.reply_text("🚫 Admins only.")
        return
    # Usage: /addanime Title | Description
    if not context.args:
        await update.message.reply_text(
            "Usage: `/addanime Anime Title | Optional description`",
            parse_mode="Markdown"
        )
        return
    text = " ".join(context.args)
    parts = text.split("|", 1)
    title = parts[0].strip()
    desc = parts[1].strip() if len(parts) > 1 else None

    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO animes (title, description) VALUES (?, ?)", (title, desc)
    )
    anime_id = cursor.lastrowid
    conn.commit()
    conn.close()

    await update.message.reply_text(
        f"✅ Anime added!\n\n*{title}*\nID: `{anime_id}`\n\n"
        f"Now upload episodes with:\n`/addep {anime_id} <episode_number> | Optional title`\n"
        f"then send the video/file.",
        parse_mode="Markdown"
    )

async def set_poster(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Reply to a photo with /setposter <anime_id>"""
    if not is_admin(update.effective_user.id):
        return
    if not context.args or not update.message.reply_to_message:
        await update.message.reply_text("Reply to a photo with `/setposter <anime_id>`", parse_mode="Markdown")
        return
    anime_id = context.args[0]
    photo = update.message.reply_to_message.photo
    if not photo:
        await update.message.reply_text("Please reply to a photo.")
        return
    file_id = photo[-1].file_id
    conn = get_db()
    conn.execute("UPDATE animes SET poster_file_id = ? WHERE id = ?", (file_id, anime_id))
    conn.commit()
    conn.close()
    await update.message.reply_text(f"✅ Poster set for anime ID {anime_id}!")

# Store pending episode uploads per admin
pending_ep = {}

async def add_episode_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    # /addep <anime_id> <ep_number> | optional title
    if len(context.args) < 2:
        await update.message.reply_text(
            "Usage: `/addep <anime_id> <ep_number> | Optional title`\nThen send the video/file.",
            parse_mode="Markdown"
        )
        return
    anime_id = context.args[0]
    rest = " ".join(context.args[1:])
    parts = rest.split("|", 1)
    ep_num = parts[0].strip()
    ep_title = parts[1].strip() if len(parts) > 1 else None

    # Check anime exists
    conn = get_db()
    anime = conn.execute("SELECT title FROM animes WHERE id = ?", (anime_id,)).fetchone()
    conn.close()
    if not anime:
        await update.message.reply_text(f"❌ No anime with ID {anime_id}.")
        return

    pending_ep[update.effective_user.id] = {
        "anime_id": anime_id,
        "ep_num": ep_num,
        "ep_title": ep_title
    }
    await update.message.reply_text(
        f"✅ Ready! Now send the *video file* for:\n\n"
        f"📺 *{anime['title']}* — Episode {ep_num}"
        + (f" ({ep_title})" if ep_title else ""),
        parse_mode="Markdown"
    )

async def receive_file(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if not is_admin(user_id) or user_id not in pending_ep:
        return

    msg = update.message
    file_id = None
    file_type = "video"

    if msg.video:
        file_id = msg.video.file_id
        file_type = "video"
    elif msg.document:
        file_id = msg.document.file_id
        file_type = "document"
    else:
        return

    ep = pending_ep.pop(user_id)
    conn = get_db()
    conn.execute(
        "INSERT INTO episodes (anime_id, episode_number, title, file_id, file_type) VALUES (?, ?, ?, ?, ?)",
        (ep["anime_id"], ep["ep_num"], ep["ep_title"], file_id, file_type)
    )
    conn.commit()
    anime = conn.execute("SELECT title FROM animes WHERE id = ?", (ep["anime_id"],)).fetchone()
    conn.close()

    await msg.reply_text(
        f"✅ *Episode saved!*\n\n"
        f"📺 {anime['title']} — Ep {ep['ep_num']}"
        + (f" ({ep['ep_title']})" if ep['ep_title'] else ""),
        parse_mode="Markdown"
    )

async def list_animes_admin(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    conn = get_db()
    animes = conn.execute("SELECT id, title FROM animes").fetchall()
    conn.close()
    if not animes:
        await update.message.reply_text("No animes yet.")
        return
    text = "📋 *All Animes:*\n\n"
    for a in animes:
        text += f"• ID `{a['id']}` — {a['title']}\n"
    await update.message.reply_text(text, parse_mode="Markdown")

async def stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update.effective_user.id):
        return
    conn = get_db()
    users = conn.execute("SELECT COUNT(*) FROM users").fetchone()[0]
    animes = conn.execute("SELECT COUNT(*) FROM animes").fetchone()[0]
    eps = conn.execute("SELECT COUNT(*) FROM episodes").fetchone()[0]
    conn.close()
    await update.message.reply_text(
        f"📊 *Bot Stats*\n\n"
        f"👤 Users: `{users}`\n"
        f"🎬 Animes: `{animes}`\n"
        f"📺 Episodes: `{eps}`",
        parse_mode="Markdown"
    )

# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()

    # User commands
    app.add_handler(CommandHandler("start", start))

    # Admin commands
    app.add_handler(CommandHandler("addanime", add_anime))
    app.add_handler(CommandHandler("addep", add_episode_cmd))
    app.add_handler(CommandHandler("setposter", set_poster))
    app.add_handler(CommandHandler("listanimes", list_animes_admin))
    app.add_handler(CommandHandler("stats", stats))

    # Button callbacks
    app.add_handler(CallbackQueryHandler(button_handler))

    # File upload handler (admin only)
    app.add_handler(MessageHandler(filters.VIDEO | filters.Document.ALL, receive_file))

    logger.info("Bot is running...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
