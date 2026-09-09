"""
KIA BOT - Exchange Data Normalizer

Converts exchange-specific WebSocket payloads into a common
internal format before data reaches the database.
"""

from __future__ import annotations

import time
from typing import Any


class ExchangeNormalizer:

    def normalize(self, message: dict[str, Any]) -> dict[str, Any]:
        channel = str(message.get("channel", "")).strip()
        symbol = str(message.get("symbol", "")).strip().upper()
        data = message.get("data")

        if channel.startswith("public:market-stats-"):
            return self.market_stats(symbol, data)

        if channel.startswith("public:trades-"):
            return self.trades(symbol, data)

        if channel.startswith("public:orderbook-"):
            return self.orderbook(symbol, data)

        if channel.startswith("public:candle-"):
            return self.candle(symbol, data)

        return {
            "type": "unknown",
            "symbol": symbol,
            "timestamp": int(time.time() * 1000),
            "data": data,
        }

    def market_stats(self, symbol: str, data: Any) -> dict[str, Any]:
        return self._result("market_stats", symbol, data)

    def trades(self, symbol: str, data: Any) -> dict[str, Any]:

        if isinstance(data, dict):
            data = {
                "price": data.get("price"),
                "timestamp": data.get("time"),
                "side": data.get("type"),
                "volume": data.get("volume"),
            }

        return self._result("trades", symbol, data)

    def orderbook(self, symbol: str, data: Any) -> dict[str, Any]:
        return self._result("orderbook", symbol, data)

    def candle(self, symbol: str, data: Any) -> dict[str, Any]:
        return self._result("candle", symbol, data)

    @staticmethod
    def _result(
        data_type: str,
        symbol: str,
        data: Any,
    ) -> dict[str, Any]:

        return {
            "type": data_type,
            "symbol": symbol,
            "timestamp": int(time.time() * 1000),
            "data": data,
        }


def normalize_message(
    message: dict[str, Any],
) -> dict[str, Any]:

    return ExchangeNormalizer().normalize(message)
