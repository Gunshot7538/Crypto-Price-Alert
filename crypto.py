from binance.client import Client
import pandas as pd
from telegram import Bot
import asyncio
import time
from dotenv import load_dotenv
import os

load_dotenv()

# ==== CONFIG ====
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")

bot = Bot(token=BOT_TOKEN)
client = Client()

# duplicate alert avoid 
sent_alerts = set()


# ==== TELEGRAM FUNCTION ====
async def send_message(text):
    try:
        await bot.send_message(chat_id=CHAT_ID, text=text)
    except Exception as e:
        print("Telegram error:", e)


# ==== DATA FETCH ====
def get_data(symbol, interval):
    klines = client.get_klines(symbol=symbol, interval=interval, limit=100)

    df = pd.DataFrame(klines)
    df = df.iloc[:, :6]  

    df.columns = ['time', 'open', 'high', 'low', 'close', 'volume']

    df['open'] = df['open'].astype(float)
    df['high'] = df['high'].astype(float)
    df['low'] = df['low'].astype(float)
    df['close'] = df['close'].astype(float)

    return df


# ==== INSIDE CANDLE ====
def inside_candle(df):
    prev = df.iloc[-3]   # previous closed
    curr = df.iloc[-2]   # last closed

    if curr['high'] < prev['high'] and curr['low'] > prev['low']:
        return True
    return False


# ==== EMA 50 CHECK ====
def check_ema(df):
    df['ema50'] = df['close'].ewm(span=50).mean()

    prev_close = df['close'].iloc[-2]
    curr_close = df['close'].iloc[-1]

    prev_ema = df['ema50'].iloc[-2]
    curr_ema = df['ema50'].iloc[-1]

    # bottom to top (support)
    if prev_close < prev_ema and curr_close > curr_ema:
        return "📈 EMA Support"

    # top to bottom (resistance)
    if prev_close > prev_ema and curr_close < curr_ema:
        return "📉 EMA Resistance"

    return None


# ==== MAIN LOGIC ====
def run_bot():
    symbols = ['BTCUSDT', 'ETHUSDT']

    for sym in symbols:

        msg = f"\n{sym} ALERT\n"
        found = False

        # ---- 1H ----
        df1 = get_data(sym, '1h')

        if inside_candle(df1):
            key = f"{sym}_1h_inside"
            if key not in sent_alerts:
                msg += "Inside Candle 1H\n"
                sent_alerts.add(key)
                found = True

        ema1 = check_ema(df1)
        if ema1:
            key = f"{sym}_1h_ema"
            if key not in sent_alerts:
                msg += f"{ema1} (1H)\n"
                sent_alerts.add(key)
                found = True

        # ---- 4H ----
        df4 = get_data(sym, '4h')

        if inside_candle(df4):
            key = f"{sym}_4h_inside"
            if key not in sent_alerts:
                msg += "Inside Candle 4H\n"
                sent_alerts.add(key)
                found = True

        ema4 = check_ema(df4)
        if ema4:
            key = f"{sym}_4h_ema"
            if key not in sent_alerts:
                msg += f"{ema4} (4H)\n"
                sent_alerts.add(key)
                found = True

        # ---- SEND ----
        if found:
            price = df1['close'].iloc[-1]
            msg += f"Price: {price}"

            asyncio.run(send_message(msg))


# ==== LOOP ====
while True:
    try:
        run_bot()
        time.sleep(60)
    except Exception as err:
        print("Error:", err)
        time.sleep(60)

