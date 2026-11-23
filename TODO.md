## 🛠️ Windsurf "Pro" Bot Development Roadmap

### ✅ Phase 1: Foundations & Database
*   [x] **Project Setup:** Initialize the project with `discord.py` and `python-dotenv`.
*   [x] **Config Management:** Create a `.env` file for the token and a `config.py` to load environment variables.
*   [x] **Database Architecture:** Upgrade to **SQLAlchemy (Async)**.
    *   *Tables needed:* `users` (id, balance, xp, msg_count, vc_timer).
*   [x] **Cog System:** Structure the bot into Cogs: `Economy.py`, `Shop.py`, and `Core.py`.

### ✅ Phase 2: The Reward Engines
*   [x] **Message Reward Logic:** 
    *   Create a listener: 10 messages = 1 coin.
    *   [x] Add a 30-second cooldown per message to prevent "gibberish" spamming.
*   [x] **VC Reward Logic:** 
    *   Create a `tasks.loop` that runs every 10 minutes.
    *   Reward 5 coins for every 10 minutes.
    *   [x] *Pro Feature:* Check `if not member.voice.self_deaf` to ensure they are actually active.

### ✅ Phase 3: Pro UI/UX (Slash Commands & Components)
*   [x] **Slash Command Migration:** Ensure all commands use `@app_commands.command()`.
*   [x] **The Shop Interface:**
    *   [x] Create a `/buyroyal` command with high-quality **Embed**.
    *   [x] Add **Button** labeled "Buy Royal Role (500 🪙)".
*   [x] **The Role Logic:** 
    *   [x] When the button is clicked, check the database.
    *   [x] Deduct coins and use `await member.add_roles()` to give the "Royal Role".
*   [x] **Balance & Leaderboard:**
    *   [x] `/balance`: Show an embed with the user's coins.
    *   [x] `/top`: Show the top 10 richest users in a clean list.
    *   [x] Add current level to balance display.

### ✅ Phase 4: Polish & Stability
*   [x] **Global Error Handler:** Create an `on_app_command_error` listener to catch "Insufficient Funds" or "Missing Permissions" errors gracefully.
*   [x] **Admin Logs:** Set up a logging system that sends an embed to a staff channel whenever a "Royal Role" is purchased.
*   [x] **XP/Leveling UI:** Add a feature where users "Level Up" every 100 coins earned, sending a "Level Up!" embed.

---

## 📊 Status: ✅ ALL PHASES COMPLETE

**Bot Features Implemented:**
- SQLAlchemy async ORM with unified User model
- Cog-based architecture for clean code organization
- All commands converted to Slash Commands
- 30-second message cooldown anti-spam
- XP/Leveling system (1 XP per coin, level up every 100 XP)
- Level up notifications in server channel
- Leaderboard system (`/top`)
- Admin logging to staff channel
- Global error handling for all commands
- Professional embed templates

---

## 🚀 Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure .env with your token
# DISCORD_TOKEN=your_token_here
# STAFF_CHANNEL_ID=your_channel_id_here

# 3. Run the bot
python bot.py
```

**Available Commands:**
- `/ping`, `/balance`, `/userinfo`, `/top`, `/shop`, `/buyroyal`
- `/give`, `/take` (Admin only), `/sync` (Owner only)
