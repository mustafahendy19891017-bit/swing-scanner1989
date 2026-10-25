import os
import requests
import pandas as pd
import yfinance as yf

# جلب بيانات الاعتماد من البيئة (GitHub Secrets)
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

def send_telegram_message(text):
    if not TELEGRAM_TOKEN or not CHAT_ID:
        print("Telegram credentials missing!")
        return
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "Markdown"
    }
    response = requests.post(url, json=payload)
    print("Telegram response:", response.text)

def scan_markets():
    # قائمة الأصول العالمية المستهدفة (أسهم، عملات، سلع، عملات رقمية)
    tickers = [
        # الأسهم الأمريكية الكبرى
        "AAPL", "MSFT", "NVDA", "TSLA", "AMZN", "GOOGL", "META", "AMD", "NFLX", "PLTR",
        # العملات الأجنبية (Forex)
        "EURUSD=X", "GBPUSD=X", "AUDUSD=X", "USDJPY=X",
        # السلع والمعادن
        "GC=F", "SI=F", "CL=F",
        # العملات الرقمية
        "BTC-USD", "ETH-USD"
    ]
    
    signals = []
    
    for ticker in tickers:
        try:
            df = yf.download(ticker, period="60d", interval="1d", progress=False)
            if df.empty or len(df) < 50:
                continue
            
            # معالجة تنسيق الأعمدة في yfinance إذا كانت متعددة المستويات
            if isinstance(df.columns, pd.MultiIndex):
                df.columns = df.columns.get_level_values(0)
            
            close = df['Close']
            high = df['High']
            low = df['Low']
            
            # حساب المؤشرات الفنية
            ema50 = close.ewm(span=50, adjust=False).mean()
            prev_high_21 = high.shift(1).rolling(window=21).max()
            
            # مؤشر القوة النسبية RSI (14)
            delta = close.diff()
            gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
            rs = gain / loss
            rsi = 100 - (100 / (1 + rs))
            
            # مؤشر التذبذب ATR (14) لحساب وقف الخسارة
            tr1 = high - low
            tr2 = (high - close.shift(1)).abs()
            tr3 = (low - close.shift(1)).abs()
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr = tr.rolling(window=14).mean()
            
            # القيم الحالية للأداة
            curr_close = close.iloc[-1]
            curr_ema50 = ema50.iloc[-1]
            curr_rsi = rsi.iloc[-1]
            curr_atr = atr.iloc[-1]
            prev_max_21 = prev_high_21.iloc[-1]
            
            # شروط الاستراتيجية:
            # 1. إغلاق أعلى قمة 21 يوم (اختراق)
            # 2. السعر أعلى من المتوسط المتحرك 50 (اتجاه صاعد)
            # 3. مؤشر RSI بين 50 و 72
            is_breakout = curr_close > prev_max_21
            is_uptrend = curr_close > curr_ema50
            is_rsi_valid = 50 <= curr_rsi <= 72
            
            if is_breakout and is_uptrend and is_rsi_valid:
                stop_loss = curr_close - (1.5 * curr_atr)
                target = curr_close + (3.0 * curr_atr)
                signals.append(
                    f"🚀 *فرصة سوينغ مطابقة للاستراتيجية*\n"
                    f"📌 *الأصل:* `{ticker}`\n"
                    f"💰 *السعر الحالي:* `{curr_close:.2f}`\n"
                    f"📈 *RSI:* `{curr_rsi:.1f}`\n"
                    f"🛑 *وقف الخسارة:* `{stop_loss:.2f}`\n"
                    f"🎯 *الهدف المقترح:* `{target:.2f}`"
                )
        except Exception as e:
            print(f"Error processing {ticker}: {e}")
            
    # صياغة التقرير النهائي وإرساله عبر تليجرام (حتى لو لم توجد صفقات سيرسل رسالة نجاح الفحص)
    if signals:
        report = "📊 *تقرير مسح الأسواق اليومي (فرص إيجابية)*\n\n" + "\n\n".join(signals)
    else:
        report = "📊 *تقرير مسح الأسواق اليومي*\n\n✅ تم الانتهاء من فحص جميع الأصول بنجاح.\n🔍 لم يتم رصد صفقات مطابقة لشروط الاختراق الصارمة اليوم."
        
    send_telegram_message(report)

if __name__ == "__main__":
    scan_markets()
