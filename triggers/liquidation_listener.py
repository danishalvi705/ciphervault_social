import asyncio, json, logging, time, websockets

logger = logging.getLogger("liquidation_listener")
OKX_WS = "wss://ws.okx.com:8443/ws/v5/public"
SUBSCRIBE_MSG = json.dumps({"op": "subscribe", "args": [{"channel": "liquidation-orders", "instType": "SWAP"}]})
MIN_LIQ_USD = 5_000_000
COOLDOWN_SECONDS = 3600  # only one alert per symbol per hour
PING_INTERVAL_SECONDS = 20

_last_fired = {}

async def _keepalive(ws):
    while True:
        await asyncio.sleep(PING_INTERVAL_SECONDS)
        try:
            await ws.send("ping")
        except Exception:
            return

async def run_liquidation_listener(on_liquidation):
    while True:
        try:
            async with websockets.connect(OKX_WS, ping_interval=None) as ws:
                await ws.send(SUBSCRIBE_MSG)
                logger.info("Connected to OKX liquidation-orders stream")
                keepalive_task = asyncio.create_task(_keepalive(ws))
                try:
                    async for raw in ws:
                        try:
                            if raw == "pong":
                                continue
                            msg = json.loads(raw)
                            if "data" not in msg:
                                continue
                            for entry in msg["data"]:
                                inst_id = entry.get("instId")
                                for d in entry.get("details", []):
                                    bk_px = float(d.get("bkPx", 0))
                                    sz = float(d.get("sz", 0))
                                    side = d.get("side")
                                    usd_value = bk_px * sz
                                    if usd_value >= MIN_LIQ_USD:
                                        now = time.time()
                                        last = _last_fired.get(inst_id, 0)
                                        if now - last < COOLDOWN_SECONDS:
                                            logger.info(f"Skipping liquidation for {inst_id} (cooldown active)")
                                            continue
                                        _last_fired[inst_id] = now
                                        await on_liquidation({
                                            "symbol": inst_id,
                                            "side": side.upper() if side else "",
                                            "price": bk_px,
                                            "usd_value": usd_value,
                                        })
                        except Exception as e:
                            logger.error(f"liq parse error: {e}")
                finally:
                    keepalive_task.cancel()
        except Exception as e:
            logger.error(f"liquidation ws disconnected: {e}, retrying in 5s")
            await asyncio.sleep(5)
