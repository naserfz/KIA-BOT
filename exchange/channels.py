"""
KIA BOT - Nobitex Channels
"""

def orderbook_channel(symbol: str) -> str:
    return f"public:orderbook-{symbol}"


def candle_channel(symbol: str, resolution: str) -> str:
    return f"public:candle-{symbol}-{resolution}"


def trades_channel(symbol: str) -> str:
    return f"public:trades-{symbol}"


def market_stats_channel(symbol: str) -> str:
    return f"public:market-stats-{symbol}"
