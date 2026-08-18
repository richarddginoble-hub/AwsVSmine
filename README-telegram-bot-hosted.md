# Hosted Telegram bot (example)

This repo includes a GitHub Actions-based poller and an optional hosted Telegram bot implementation. The hosted bot files are for deployment to a container host (Railway/Render/Heroku) or a VPS.

Files added for hosted bot
- telegram_bot.py — long-running bot that triggers GitHub workflows or performs GitHub API calls when GITHUB_PAT is set (see earlier bot version)
- Dockerfile — container image to run the bot
- Procfile — for platforms like Heroku/Render

Security: do NOT commit .env with real tokens. Use platform environment variables / secrets.
