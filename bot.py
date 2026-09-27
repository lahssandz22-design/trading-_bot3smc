from http.server import BaseHTTPRequestHandler, HTTPServer
import os
import threading
import time
import pandas as pd
import requests

# ==========================================
# الإعدادات الخاصة بك
# ==========================================
TELEGRAM_BOT_TOKEN = "8963424681:AAHNrjFvPraD5TrLGXKZ1JhhLzhZyaSAubw"
TELEGRAM_CHAT_ID = "7895743860"

TIMEFRAME = "5m"
last_signal_times = {}

def send_telegram_alert(message):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": message,
        "parse_mode": "Markdown"
    }
    try:
        requests.post(url, data=payload, timeout=10)
    except Exception as e:
        print(f"❌ خطأ في إرسال التيليجرام: {e}")

def fetch_binance_klines(symbol="BTCUSDT", interval="5m", limit=5):
    url = f"https://fapi.binance.com/fapi/v1/klines?symbol={symbol}&interval={interval}&limit={limit}"
    try:
        response = requests.get(url, timeout=10)
        data = response.json()
        df = pd.DataFrame(data, columns=[
            'timestamp', 'open', 'high', 'low', 'close', 'volume',
            'close_time', 'quote_asset_volume', 'number_of_trades',
            'taker_buy_base_vol', 'taker_buy_quote_vol', 'ignore'
        ])
        for col in ['open', 'high', 'low', 'close']:
            df[col] = df[col].astype(float)
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        return df
    except Exception as e:
        print(f"❌ خطأ في جلب الشموع: {e}")
        return None

def monitor_market():
    print(f"🚀 بدء تشغيل بوت فريم {TIMEFRAME}...")
    send_telegram_alert(f"🤖 *تم تشغيل بوت تداول فريم الـ 5 دقائق بنجاح!*")
    
    # يمكنك مراقبة عملة واحدة أو عدة عملات (مثل BTCUSDT)
    symbol = "BTCUSDT"
    
    while True:
        try:
            df = fetch_binance_klines(symbol=symbol, interval=TIMEFRAME, limit=5)
            if df is not None and not df.empty:
                # الشمعة المغلقة الأخيرة هي iloc[-2] (لأن iloc[-1] هي الشمعة الجارية التي لم تغلق بعد)
                closed_candle = df.iloc[-2]
                candle_time = closed_candle['timestamp']
                open_price = closed_candle['open']
                close_price = closed_candle['close']
                
                # التأكد من عدم إرسال تنبيه لنفس الشمعة مرتين
                if last_signal_times.get(symbol) != candle_time:
                    last_signal_times[symbol] = candle_time
                    
                    # تحديد الاتجاه بناءً على لون الشمعة المغلقة
                    if close_price > open_price:
                        signal_type = "BUY (شراء - شمعة خضراء 🟢)"
                    elif close_price < open_price:
                        signal_type = "SELL (بيع - شمعة حمراء 🔴)"
                    else:
                        signal_type = None
                        
                    if signal_type:
                        msg = (
                            f"🚨 *إشارة جديدة بناءً على إغلاق شمعة 5m*\n"
                            f"━━━━━━━━━━━━━━━━━━━\n"
                            f"🪙 الزوج: `{symbol}`\n"
                            f"📊 الإشارة: `{signal_type}`\n"
                            f"💰 سعر الافتتاح: `{open_price}`\n"
                            f"💰 سعر الإغلاق: `{close_price}`\n"
                            f"⏱ وقت الشمعة: `{candle_time}`\n"
                            f"━━━━━━━━━━━━━━━━━━━"
                        )
                        send_telegram_alert(msg)
                        print(f"✨ تم إرسال إشارة {symbol}: {signal_type}")
                        
        except Exception as e:
            print(f"⚠️ خطأ في حلقة المراقبة: {e}")
            
        # فحص الحالة كل 30 ثانية لتتبع إغلاق الشموع بدقة
        time.sleep(30)

class SimpleHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"5m Trading Bot is running successfully!")
    def log_message(self, format, *args):
        return

if __name__ == "__main__":
    bot_thread = threading.Thread(target=monitor_market)
    bot_thread.daemon = True
    bot_thread.start()

    port = int(os.environ.get("PORT", 10000))
    server = HTTPServer(("0.0.0.0", port), SimpleHandler)
    server.serve_forever()
