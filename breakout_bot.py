import os
import requests
import numpy as np
import talib
from telegram import Bot
from telegram.ext import Updater, CommandHandler
from dotenv import load_dotenv

load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

# جلب بيانات الأسعار من Binance
def fetch_ohlc(symbol="BTCUSDT", interval="15m"):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}"
    response = requests.get(url)
    data = response.json()
    closes = np.array([float(candle[4]) for candle in data])  # أسعار الإغلاق
    return closes

# تحليل النماذج الفنية
def detect_breakout(symbol="BTCUSDT"):
    timeframes = ["15m", "1h", "4h"]
    alerts = []
    for tf in timeframes:
        closes = fetch_ohlc(symbol, tf)
        # نموذج المثلث الصاعد (مثال)
        pattern = talib.CDLENGULFING(closes)
        if pattern[-1] > 0:  # إشارة صعودية
            alerts.append(
                f"📈 **اختراق نموذج فني!**\n"
                f"العملة: {symbol}\n"
                f"النموذج: Engulfing صاعد\n"
                f"الفريم: {tf}\n"
                f"السعر: {closes[-1]}"
            )
    return alerts

# إرسال التنبيهات
def send_breakout_alerts():
    bot = Bot(token=TELEGRAM_BOT_TOKEN)
    alerts = detect_breakout()
    for alert in alerts:
        bot.send_message(chat_id=CHAT_ID, text=alert, parse_mode="Markdown")

# تشغيل البوت كل 15 دقيقة
updater = Updater(TELEGRAM_BOT_TOKEN)
updater.job_queue.run_repeating(lambda _: send_breakout_alerts(), interval=900, first=0)
updater.start_polling()