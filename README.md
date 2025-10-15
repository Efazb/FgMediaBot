# FgMediaBot (package)
This package contains a ready-to-run Telegram bot that compresses audio and video files and provides a modern UI with language selection (English + Amharic), user stats, and admin broadcast support.

## Files in this package
- `bot.py` - the main bot script (uses environment variables for credentials)
- `config.py` - optional local config (you can ignore and use env variables)
- `keep_alive.py` - small webserver to keep the bot alive on Replit
- `requirements.txt` - dependencies
- `users.json` - empty DB for user stats

## Quick setup on Replit (phone-friendly)
1. Create a free account on https://replit.com and create a new **Python** Repl.
2. Upload all files from this ZIP into the Repl.
3. In the Repl Secrets (Environment variables), add:
   - `API_ID` -> your Telegram API ID (from https://my.telegram.org)
   - `API_HASH` -> your API Hash
   - `BOT_TOKEN` -> token from BotFather
   - `ADMIN_ID` (optional) -> your numeric Telegram user id (or set `ADMIN_USERNAME` to Efab429)
4. Ensure `ffmpeg` is available in the runtime (Replit usually has it).
5. Install dependencies (Replit often auto-installs `requirements.txt`), or run in the console:
   ```
   pip install -r requirements.txt
   ```
6. Run `python bot.py`.

## Notes
- The bot prefers environment variables for security. Do **not** commit real tokens publicly.
- If you want continuous uptime, consider using a free ping service to hit the Repl URL or upgrade for always-on.
- I set the admin username to `@Efab429` — if you want to restrict admin by numeric id, set `ADMIN_ID` in Replit secrets.
