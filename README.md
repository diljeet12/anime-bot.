# 🎌 Anime Telegram Bot — Complete Setup Guide

A powerful Telegram bot that serves anime episodes with **Force Subscribe** verification.

---

## ✨ Features

- 🔒 **Force Subscribe** — Users must join your group before accessing episodes
- ✅ **Auto Verification** — Bot checks membership automatically
- 🎬 **Multi-Anime Support** — Unlimited animes with a database
- 📺 **Episode Browser** — Clean button menu to browse episodes
- 📥 **Native Telegram Streaming** — Episodes are watchable & downloadable inside Telegram
- 🖼️ **Anime Posters** — Add thumbnail images per anime
- 📊 **Admin Stats** — See user count, anime count, episode count
- 🔗 **Deep Links** — Link directly to an anime from your channel banners

---

## 🚀 STEP-BY-STEP SETUP

### STEP 1 — Create Your Bot

1. Open Telegram → search **@BotFather**
2. Send `/newbot`
3. Choose a name (e.g. `My Anime Bot`)
4. Choose a username ending in `bot` (e.g. `myanimeserverbot`)
5. Copy the **bot token** you receive

---

### STEP 2 — Get Your Telegram User ID

1. Open Telegram → search **@userinfobot**
2. Send `/start`
3. Copy your **User ID** (a number like `123456789`)

---

### STEP 3 — Edit config.py

Open `config.py` and fill in:

```python
BOT_TOKEN = "paste_your_bot_token_here"
FORCE_SUB_CHANNEL = "@your_group_username"   # the group users must join
ADMIN_IDS = [123456789]                       # your Telegram user ID
```

> ⚠️ Make sure your bot is an **admin** in the FORCE_SUB_CHANNEL group, with permission to see members.

---

### STEP 4 — Add Bot to Your Group as Admin

1. Go to your Force Subscribe group/channel
2. Add the bot as admin
3. Give it **"Add Members"** or at minimum read permissions so it can check membership

---

### STEP 5 — Deploy to Railway (Free Hosting)

1. Go to **https://railway.app** and sign up (free, no credit card)
2. Click **"New Project"** → **"Deploy from GitHub repo"**
3. Upload your bot files to a **GitHub repo** first:
   - Go to https://github.com → New repo → upload all 4 files
4. Connect Railway to that GitHub repo
5. Railway will detect `Procfile` and auto-deploy ✅
6. Your bot will be running 24/7 for free!

**Alternative — Run Locally (for testing):**
```bash
pip install -r requirements.txt
python bot.py
```

---

## 📋 ADMIN COMMANDS

| Command | What it does |
|---|---|
| `/addanime Title \| Description` | Add a new anime |
| `/addep <anime_id> <ep_num> \| Title` | Prepare to upload an episode |
| `/setposter <anime_id>` | Reply to a photo to set poster |
| `/listanimes` | See all animes with their IDs |
| `/stats` | See users, animes, episodes count |

---

## 🎬 HOW TO UPLOAD EPISODES

1. Send `/addep 1 1 | The Beginning` (anime_id=1, episode=1, title optional)
2. Bot says "Ready! Now send the video file"
3. Send the video file directly in chat
4. Bot saves it and confirms ✅

> 💡 Episodes are stored as **Telegram File IDs** — videos are hosted on Telegram's own servers, completely free, no size limit worries for users!

---

## 🔗 HOW TO LINK FROM YOUR CHANNEL BANNERS

When posting an anime banner in your channel, use this button URL format:

```
https://t.me/YOUR_BOT_USERNAME?start=anime_ID
```

Example: `https://t.me/myanimebot?start=anime_3`

This takes users directly to the episode list for that anime!

---

## 📁 File Structure

```
anime_bot/
├── bot.py           # Main bot logic
├── config.py        # Your settings (edit this!)
├── requirements.txt # Python dependencies
├── Procfile         # For Railway hosting
└── anime_bot.db     # Auto-created database
```

---

## 🛡️ How Force Subscribe Works

1. User clicks your channel banner link
2. Bot checks if user is in your group via Telegram API
3. If **not joined** → shows "Join Group" + "I've Joined" buttons
4. User joins → clicks verify → bot checks again
5. If **still not joined** → shows message again (loop)
6. If **joined** ✅ → episodes are sent!

---

## ❓ Troubleshooting

**Bot doesn't verify membership:**
→ Make sure the bot is admin in your force-sub group

**Episodes not sending:**
→ Make sure you uploaded using `/addep` first, then sent the file

**Bot not responding:**
→ Check your BOT_TOKEN in config.py is correct
