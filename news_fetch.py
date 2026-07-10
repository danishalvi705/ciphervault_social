"""
news_fetch.py — Live crypto news + price correlation
Sources: CryptoPanic, CoinDesk RSS, CoinGecko
"""
import os
import re
import logging
import requests
import xml.etree.ElementTree as ET

logger = logging.getLogger(__name__)

COINDESK_RSS = "https://www.coindesk.com/arc/outboundfeeds/rss/"
COINTELEGRAPH_RSS = "https://cointelegraph.com/rss"
DECRYPT_RSS = "https://decrypt.co/feed"

# Common tickers to detect in headlines (extend as needed)
KNOWN_COINS = {
    "BITCOIN": "bitcoin", "BTC": "bitcoin",
    "ETHEREUM": "ethereum", "ETH": "ethereum",
    "XRP": "ripple", "RIPPLE": "ripple",
    "SOLANA": "solana", "SOL": "solana",
    "DOGECOIN": "dogecoin", "DOGE": "dogecoin",
    "CARDANO": "cardano", "ADA": "cardano",
    "BNB": "binancecoin",
    "AVALANCHE": "avalanche-2", "AVAX": "avalanche-2",
    "POLKADOT": "polkadot", "DOT": "polkadot",
    "CHAINLINK": "chainlink", "LINK": "chainlink",
    "LITECOIN": "litecoin", "LTC": "litecoin",
    "TRON": "tron", "TRX": "tron",
    "SHIBA": "shiba-inu", "SHIB": "shiba-inu",
}


def _fetch_rss(url: str, source_name: str, limit: int = 10):
    """Generic RSS fetcher — free, no key required."""
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
        items = root.findall(".//item")[:limit]
        result = []
        for i in items:
            title_el = i.find("title")
            link_el = i.find("link")
            if title_el is not None and title_el.text:
                result.append({
                    "title": title_el.text.strip(),
                    "source": source_name,
                    "url": link_el.text if link_el is not None else "",
                })
        return result
    except Exception as e:
        logger.error(f"{source_name} RSS fetch failed: {e}")
        return []


def fetch_coindesk_headlines(limit: int = 10):
    return _fetch_rss(COINDESK_RSS, "CoinDesk", limit)


def fetch_cointelegraph_headlines(limit: int = 10):
    return _fetch_rss(COINTELEGRAPH_RSS, "CoinTelegraph", limit)


def fetch_decrypt_headlines(limit: int = 10):
    return _fetch_rss(DECRYPT_RSS, "Decrypt", limit)


def extract_coin_from_headline(headline: str):
    """Find which known coin a headline is about."""
    upper = headline.upper()
    for keyword, coingecko_id in KNOWN_COINS.items():
        if re.search(rf"\b{keyword}\b", upper):
            return coingecko_id, keyword
    return None, None


def get_price_change(coingecko_id: str):
    """Get live 1h/24h/7d % change from CoinGecko (free, no key)."""
    try:
        url = (
            f"https://api.coingecko.com/api/v3/coins/markets"
            f"?vs_currency=usd&ids={coingecko_id}"
            f"&price_change_percentage=1h,24h,7d"
        )
        resp = requests.get(url, timeout=15)
        resp.raise_for_status()
        data = resp.json()
        if not data:
            return None
        d = data[0]
        return {
            "symbol": d["symbol"].upper(),
            "price": d["current_price"],
            "change_1h": d.get("price_change_percentage_1h_in_currency", 0) or 0,
            "change_24h": d.get("price_change_percentage_24h_in_currency", 0) or 0,
            "change_7d": d.get("price_change_percentage_7d_in_currency", 0) or 0,
        }
    except Exception as e:
        logger.error(f"CoinGecko fetch failed: {e}")
        return None


def get_top_news_with_impact():
    """
    Merge CryptoPanic + CoinDesk, find the first headline that mentions
    a known coin, and attach live price data for that coin.
    Returns None if nothing usable found (caller should retry/skip, no static fallback).
    """
    headlines = (
        fetch_coindesk_headlines()
        + fetch_cointelegraph_headlines()
        + fetch_decrypt_headlines()
    )
    if not headlines:
        return None

    for h in headlines:
        coin_id, symbol_hit = extract_coin_from_headline(h["title"])
        if coin_id:
            price_data = get_price_change(coin_id)
            if price_data:
                return {
                    "headline": h["title"],
                    "source": h["source"],
                    "coin_id": coin_id,
                    "symbol_hit": symbol_hit,
                    **price_data,
                }
    return None
