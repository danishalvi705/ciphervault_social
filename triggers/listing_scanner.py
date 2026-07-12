import asyncio, logging
import ccxt.async_support as ccxt

logger = logging.getLogger("listing_scanner")
POLL_INTERVAL_SECONDS = 900
VOLUME_SPIKE_MULTIPLIER = 3.0
EXCHANGES = ["binance", "okx", "bybit", "kucoin", "gate", "kraken"]

_known_symbols = {ex: set() for ex in EXCHANGES}
_volume_baseline = {}

async def run_listing_scanner(on_new_listing, on_volume_spike):
    clients = {ex: getattr(ccxt, ex)({"enableRateLimit": True}) for ex in EXCHANGES}
    first_pass = True
    try:
        while True:
            for ex_name, client in clients.items():
                try:
                    markets = await client.load_markets(reload=True)
                    current_symbols = set(markets.keys())
                    if not first_pass:
                        for sym in current_symbols - _known_symbols[ex_name]:
                            await on_new_listing({"exchange": ex_name, "symbol": sym})
                    _known_symbols[ex_name] = current_symbols

                    tickers = await client.fetch_tickers()
                    for sym, t in tickers.items():
                        vol = t.get("quoteVolume") or 0
                        if not vol:
                            continue
                        key = (ex_name, sym)
                        hist = _volume_baseline.setdefault(key, [])
                        if len(hist) >= 12:
                            avg = sum(hist) / len(hist)
                            if avg > 0 and vol >= avg * VOLUME_SPIKE_MULTIPLIER:
                                await on_volume_spike({
                                    "exchange": ex_name, "symbol": sym, "volume": vol,
                                    "avg_volume": avg, "multiplier": round(vol / avg, 2),
                                })
                            hist.pop(0)
                        hist.append(vol)
                except Exception as e:
                    logger.error(f"listing scan error on {ex_name}: {e}")
            first_pass = False
            await asyncio.sleep(POLL_INTERVAL_SECONDS)
    finally:
        for client in clients.values():
            await client.close()
