# Use a minimal Python image
FROM python:3.11-slim
WORKDIR /app

# install dependencies
COPY requirements-bot.txt /app/requirements-bot.txt
RUN pip install --no-cache-dir -r requirements-bot.txt

# copy bot
COPY telegram_bot.py /app/telegram_bot.py

CMD ["python", "telegram_bot.py"]
