import asyncio, json, logging, websockets

logger = logging.getLogger("whale_tracker")
WATCH_SYMBOLS = ["btcusdt", "ethusdt", "solusdt", "bnbusdt", "xrpusdt"]
MIN_WHALE_USD = 50_000_000

def build_stream_url():
    streams = "/".join(f"{s}@aggTrade" for s in WATCH_SYMBOLS)
    return f"wss://stream.binance.com:9443/stream?streams={streams}"

async def run_whale_tracker(on_whale_trade):
    url = build_stream_url()
    while True:
        try:
            async with websockets.connect(url, ping_interval=20) as ws:
                logger.info("Connected to Binance aggTrade stream (whale tracker)")
                async for raw in ws:
                    try:
                        data = json.loads(raw).get("data", {})
                        qty = float(data.get("q", 0))
                        price = float(data.get("p", 0))
                        usd_value = qty * price
                        if usd_value >= MIN_WHALE_USD:
                            await on_whale_trade({
                                "symbol": data.get("s"),
                                "side": "sell" if data.get("m") else "buy",
                                "qty": qty, "price": price, "usd_value": usd_value,
                            })
                    except Exception as e:
                        logger.error(f"whale parse error: {e}")
        except Exception as e:
            logger.error(f"whale ws disconnected: {e}, retrying in 5s")
            await asyncio.sleep(5)
