FROM python:3.10-slim

WORKDIR /app
COPY . .

RUN pip install --no-cache-dir --prefer-binary -r requirements.txt

CMD ["python", "liquidity_bot.py"]
