import asyncio, json, logging, time, websockets
from collections import defaultdict, deque

logger = logging.getLogger("volatility_monitor")
BINANCE_TICKER_WS = "wss://stream.binance.com:9443/ws/!ticker@arr"
WATCH_SYMBOLS = {"BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "XRPUSDT"}
WINDOW_SECONDS = 3600
PCT_THRESHOLD = 3.0
COOLDOWN_SECONDS = 3600

_price_history = defaultdict(lambda: deque())
_last_fired = {}

async def run_volatility_monitor(on_volatility_spike):
    while True:
        try:
            async with websockets.connect(BINANCE_TICKER_WS, ping_interval=20) as ws:
                logger.info("Connected to Binance ticker stream (volatility monitor)")
                async for raw in ws:
                    try:
                        now = time.time()
                        for t in json.loads(raw):
                            symbol = t.get("s")
                            if symbol not in WATCH_SYMBOLS:
                                continue
                            price = float(t.get("c", 0))
                            hist = _price_history[symbol]
                            hist.append((now, price))
                            while hist and now - hist[0][0] > WINDOW_SECONDS:
                                hist.popleft()
                            if len(hist) < 2:
                                continue
                            oldest_price = hist[0][1]
                            pct_change = ((price - oldest_price) / oldest_price) * 100
                            if abs(pct_change) >= PCT_THRESHOLD:
                                last = _last_fired.get(symbol, 0)
                                if now - last >= COOLDOWN_SECONDS:
                                    _last_fired[symbol] = now
                                    await on_volatility_spike({
                                        "symbol": symbol, "pct_change": round(pct_change, 2),
                                        "price": price, "window_seconds": WINDOW_SECONDS,
                                    })
                    except Exception as e:
                        logger.error(f"volatility parse error: {e}")
        except Exception as e:
            logger.error(f"volatility ws disconnected: {e}, retrying in 5s")
            await asyncio.sleep(5)
