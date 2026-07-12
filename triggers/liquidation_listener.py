import asyncio, json, logging, websockets

logger = logging.getLogger("liquidation_listener")
OKX_WS = "wss://ws.okx.com:8443/ws/v5/public"
SUBSCRIBE_MSG = json.dumps({"op": "subscribe", "args": [{"channel": "liquidation-orders", "instType": "SWAP"}]})
MIN_LIQ_USD = 500_000

async def run_liquidation_listener(on_liquidation):
    while True:
        try:
            async with websockets.connect(OKX_WS, ping_interval=20) as ws:
                await ws.send(SUBSCRIBE_MSG)
                logger.info("Connected to OKX liquidation-orders stream")
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
                                    await on_liquidation({
                                        "symbol": inst_id,
                                        "side": side.upper() if side else "",
                                        "price": bk_px,
                                        "usd_value": usd_value,
                                    })
                    except Exception as e:
                        logger.error(f"liq parse error: {e}")
        except Exception as e:
            logger.error(f"liquidation ws disconnected: {e}, retrying in 5s")
            await asyncio.sleep(5)
