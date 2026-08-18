# Poller README

This poller implements:
- Two-step confirmation (/run then /confirm within timeout)
- Run completion notifications to Telegram with Actions run URL
- Detailed logs written to run_logs/ and uploaded as artifact
- Persistent state files committed back to repo (telegram_offset.json, pending_confirmations.json, run_output.json)

Hosted bot files for deployment are included (telegram_bot.py, Dockerfile, Procfile). Use environment variables to configure the hosted bot.
