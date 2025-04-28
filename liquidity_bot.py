import os
import asyncio
import requests
import random
import time
from datetime import datetime
from pytz import timezone
from telegram import Bot
from telegram.ext import Application
from telegram.error import NetworkError
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from dotenv import load_dotenv

# تحميل المتغيرات البيئية
load_dotenv()
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
CHAT_ID = os.getenv('CHAT_ID')

# التحقق من صحة التوكن
if not TELEGRAM_BOT_TOKEN or not TELEGRAM_BOT_TOKEN.startswith(('7', '6')):
    raise ValueError("❌ Invalid Telegram Token Format!")
print("✅ Token format is valid")

# تعريف النطاق الزمني
arabic_tz = timezone('Asia/Riyadh')

# تهيئة البوت والمجدول
bot = Bot(token=TELEGRAM_BOT_TOKEN)
application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
scheduler = AsyncIOScheduler(timezone=arabic_tz)

# قاموس لتتبع آخر تنبيهات السيولة
last_alerts = {}

async def analyze_exchanges(symbol: str) -> dict:
    """تحليل تغيرات السيولة من منصات التداول"""
    exchanges = {
        'binance': f'https://api.binance.com/api/v3/ticker/24hr?symbol={symbol}USDT',
        'bybit': f'https://api.bybit.com/v2/public/tickers?symbol={symbol}USDT',
        'kucoin': f'https://api.kucoin.com/api/v1/market/stats?symbol={symbol}-USDT'
    }
    
    results = {}
    for exchange, url in exchanges.items():
        try:
            data = requests.get(url).json()
            if 'volume' in data:
                volume = float(data['volume'])
            elif 'result' in data and 'volume_24h' in data['result'][0]:
                volume = float(data['result'][0]['volume_24h'])
            elif 'data' in data and 'volValue' in data['data']:
                volume = float(data['data']['volValue'])
            else:
                continue
            
            results[exchange] = volume
        except Exception:
            continue
    
    return results

async def check_liquidity_spikes() -> list:
    """الكشف عن تغيرات السيولة"""
    alerts = []
    EXCLUDED_COINS = ['USDT', 'USDC', 'BNB', 'TRX', 'USDe', 'OKB', 
                     'TRUMP', 'FDUSD', 'KCS', 'PYUSD', 'FARTCOIN', 'CRV', 'CAKE', 'WBTC']
    
    try:
        # جلب بيانات العملات
        url = "https://api.coingecko.com/api/v3/coins/markets"
        params = {'vs_currency': 'usd', 'order': 'market_cap_desc', 'per_page': 500}
        response = requests.get(url, params=params)
        coins = [coin for coin in response.json() if coin['symbol'].upper() not in EXCLUDED_COINS]

        for coin in coins[:100]:  # أول 100 عملة فقط
            symbol = coin['symbol'].upper()
            exchange_data = await analyze_exchanges(symbol)
            
            if not exchange_data:
                continue

            avg_volume = sum(exchange_data.values()) / len(exchange_data)
            
            for exchange, volume in exchange_data.items():
                if volume == 0:
                    continue
                    
                change_percent = ((volume - avg_volume) / avg_volume) * 100
                alert_key = f"{symbol}-{exchange}"
                
                if volume > avg_volume * 1.5:
                    if alert_key not in last_alerts or change_percent > last_alerts[alert_key] * 1.1:
                        last_alerts[alert_key] = change_percent
                        alert_msg = (
                            f"🚨 ({symbol}) - {exchange.capitalize()}\n"
                            f"Volume: ${volume:,.2f}\n"
                            f"Change: +{change_percent:.2f}%\n"
                        )
                        alerts.append(alert_msg)
                        
    except Exception as e:
        print(f"Error in liquidity analysis: {e}")
    
    return alerts

async def send_liquidity_alerts():
    """إرسال تنبيهات السيولة"""
    max_retries = 3
    for attempt in range(max_retries):
        try:
            alerts = await check_liquidity_spikes()
            for alert in alerts:
                await bot.send_message(
                    chat_id=CHAT_ID,
                    text=alert,
                    parse_mode="Markdown",
                    timeout=30
                )
            break
        except NetworkError as e:
            wait_time = (2 ** attempt) + random.random()
            print(f"Network error (attempt {attempt + 1}): {e}")
            await asyncio.sleep(wait_time)
        except Exception as e:
            print(f"Unexpected error: {e}")
            break

async def post_init(app: Application):
    """تهيئة ما بعد التشغيل"""
    await app.bot.delete_webhook(drop_pending_updates=True)
    print("🟢 Bot initialized successfully!")

async def main():
    """الدالة الرئيسية للتشغيل"""
    # تهيئة البوت
    application.post_init(post_init)
    
    # جدولة المهام
    scheduler.add_job(send_liquidity_alerts, 'interval', minutes=5)
    scheduler.start()
    
    print("🟢 Bot started successfully!")
    await application.initialize()
    await application.start()
    await asyncio.Event().wait()  # يبقي البوت نشطًا

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"🔴 Fatal Error: {str(e)}")
