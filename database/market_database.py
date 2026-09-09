"""
KIA BOT - Market Database
"""

from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any


class MarketDatabase:

    def __init__(
        self,
        exchange: str,
        symbol: str,
        root: str | Path = "database",
    ) -> None:

        self.exchange = str(exchange).strip().lower()
        self.symbol = str(symbol).strip().upper()

        if not self.exchange:
            raise ValueError("Exchange name is required.")

        if not self.symbol:
            raise ValueError("Market symbol is required.")

        self.market_dir = (
            Path(root) / self.exchange / self.symbol
        )
        self.market_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.candles_db = (
            self.market_dir / f"{self.symbol}_candles.db"
        )
        self.trades_db = (
            self.market_dir / f"{self.symbol}_trades.db"
        )
        self.orderbook_db = (
            self.market_dir / f"{self.symbol}_orderbook.db"
        )
        self.market_stats_db = (
            self.market_dir / f"{self.symbol}_market_stats.db"
        )

        self.retention_file = (
            Path(root) / "retention.json"
        )

        self._initialize()

    def _initialize(self) -> None:

        with sqlite3.connect(self.candles_db) as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS candles (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp INTEGER NOT NULL,
                    open REAL,
                    high REAL,
                    low REAL,
                    close REAL,
                    volume REAL
                )
            """)
            db.execute("""
                CREATE INDEX IF NOT EXISTS
                idx_candles_timestamp
                ON candles(timestamp)
            """)

        with sqlite3.connect(self.trades_db) as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp INTEGER,
                    price REAL,
                    volume REAL,
                    side TEXT,
                    raw_json TEXT
                )
            """)
            db.execute("""
                CREATE INDEX IF NOT EXISTS
                idx_trades_timestamp
                ON trades(timestamp)
            """)

        with sqlite3.connect(self.orderbook_db) as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS orderbook (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp INTEGER,
                    bids_json TEXT,
                    asks_json TEXT,
                    raw_json TEXT
                )
            """)
            db.execute("""
                CREATE INDEX IF NOT EXISTS
                idx_orderbook_timestamp
                ON orderbook(timestamp)
            """)

        with sqlite3.connect(self.market_stats_db) as db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS market_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp INTEGER,
                    is_closed INTEGER,
                    best_sell REAL,
                    best_buy REAL,
                    volume_src REAL,
                    volume_dst REAL,
                    latest REAL,
                    mark REAL,
                    day_low REAL,
                    day_high REAL,
                    day_open REAL,
                    day_close REAL,
                    day_change REAL,
                    raw_json TEXT
                )
            """)
            db.execute("""
                CREATE INDEX IF NOT EXISTS
                idx_market_stats_timestamp
                ON market_stats(timestamp)
            """)

    @staticmethod
    def _float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _timestamp(message: dict[str, Any]) -> int:
        value = message.get("timestamp")
        if value is not None:
            return int(value)
        return int(time.time() * 1000)

    # ========================================================
    # RETENTION
    # ========================================================

    def _load_retention(self) -> dict[str, int]:
        if not self.retention_file.exists():
            return {}

        try:
            data = json.loads(
                self.retention_file.read_text(
                    encoding="utf-8"
                )
            )

            if not isinstance(data, dict):
                return {}

            return {
                str(k): int(v)
                for k, v in data.items()
                if int(v) > 0
            }

        except Exception:
            return {}

    def _retention_key(self, data_type: str) -> str:
        return (
            f"{self.exchange}/"
            f"{self.symbol}/"
            f"{data_type}"
        )

    def get_retention(self, data_type: str) -> int:
        data = self._load_retention()
        return int(
            data.get(
                self._retention_key(data_type),
                0
            )
        )

    def set_retention(
        self,
        data_type: str,
        maximum: int,
    ) -> None:

        maximum = int(maximum)

        if maximum < 0:
            raise ValueError(
                "Maximum records cannot be negative."
            )

        data = self._load_retention()

        key = self._retention_key(data_type)

        if maximum == 0:
            data.pop(key, None)
        else:
            data[key] = maximum

        self.retention_file.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.retention_file.write_text(
            json.dumps(
                data,
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        if maximum > 0:
            self._trim(data_type, maximum)

    def _trim(
        self,
        data_type: str,
        maximum: int,
    ) -> None:

        if maximum <= 0:
            return

        db_path = self.paths().get(data_type)

        if db_path is None or not db_path.exists():
            return

        table_map = {
            "candles": "candles",
            "trades": "trades",
            "orderbook": "orderbook",
            "market_stats": "market_stats",
        }

        table = table_map.get(data_type)

        if table is None:
            return

        with sqlite3.connect(db_path) as db:

            db.execute(
                f"""
                DELETE FROM {table}
                WHERE id IN (
                    SELECT id
                    FROM {table}
                    ORDER BY timestamp ASC, id ASC
                    LIMIT (
                        SELECT MAX(COUNT(*) - ?, 0)
                        FROM {table}
                    )
                )
                """,
                (maximum,),
            )

            db.commit()

    def _apply_retention(self, data_type: str) -> None:
        maximum = self.get_retention(data_type)

        if maximum > 0:
            self._trim(
                data_type,
                maximum
            )

    # ========================================================
    # SAVE
    # ========================================================

    def save(self, message: dict[str, Any]) -> None:

        data_type = str(
            message.get("type", "")
        ).strip().lower()

        if data_type == "candle":
            self.save_candle(message)

        elif data_type == "trades":
            self.save_trades(message)

        elif data_type == "orderbook":
            self.save_orderbook(message)

        elif data_type == "market_stats":
            self.save_market_stats(message)

    def save_candle(self, message: dict[str, Any]) -> None:

        data = message.get("data")

        if not isinstance(data, dict):
            return

        timestamp = data.get("t")

        if timestamp is None:
            return

        timestamp = int(timestamp)

        open_price = self._float(data.get("o"))
        high = self._float(data.get("h"))
        low = self._float(data.get("l"))
        close = self._float(data.get("c"))
        volume = self._float(data.get("v"))

        with sqlite3.connect(self.candles_db) as db:

            cursor = db.execute(
                """
                UPDATE candles
                SET
                    open = ?,
                    high = ?,
                    low = ?,
                    close = ?,
                    volume = ?
                WHERE timestamp = ?
                """,
                (
                    open_price,
                    high,
                    low,
                    close,
                    volume,
                    timestamp,
                ),
            )

            if cursor.rowcount == 0:

                db.execute(
                    """
                    INSERT INTO candles (
                        timestamp,
                        open,
                        high,
                        low,
                        close,
                        volume
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        timestamp,
                        open_price,
                        high,
                        low,
                        close,
                        volume,
                    ),
                )

        self._apply_retention("candles")

    def save_trades(self, message: dict[str, Any]) -> None:

        data = message.get("data")

        if not isinstance(data, dict):
            return

        timestamp = data.get("timestamp")
        price = data.get("price")
        volume = data.get("volume")
        side = data.get("side")

        with sqlite3.connect(self.trades_db) as db:
            db.execute(
                """
                INSERT INTO trades (
                    timestamp,
                    price,
                    volume,
                    side,
                    raw_json
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    int(timestamp)
                    if timestamp is not None
                    else self._timestamp(message),
                    self._float(price),
                    self._float(volume),
                    str(side)
                    if side is not None
                    else None,
                    json.dumps(
                        data,
                        ensure_ascii=False,
                    ),
                ),
            )

        self._apply_retention("trades")

    def save_orderbook(self, message: dict[str, Any]) -> None:

        data = message.get("data")

        if not isinstance(data, dict):
            return

        timestamp = (
            data.get("lastUpdate")
            or self._timestamp(message)
        )

        bids = data.get("bids", [])
        asks = data.get("asks", [])

        with sqlite3.connect(self.orderbook_db) as db:
            db.execute(
                """
                INSERT INTO orderbook (
                    timestamp,
                    bids_json,
                    asks_json,
                    raw_json
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    int(timestamp),
                    json.dumps(
                        bids,
                        ensure_ascii=False,
                    ),
                    json.dumps(
                        asks,
                        ensure_ascii=False,
                    ),
                    json.dumps(
                        data,
                        ensure_ascii=False,
                    ),
                ),
            )

        self._apply_retention("orderbook")

    def save_market_stats(
        self,
        message: dict[str, Any],
    ) -> None:

        data = message.get("data")

        if not isinstance(data, dict):
            return

        with sqlite3.connect(self.market_stats_db) as db:
            db.execute(
                """
                INSERT INTO market_stats (
                    timestamp,
                    is_closed,
                    best_sell,
                    best_buy,
                    volume_src,
                    volume_dst,
                    latest,
                    mark,
                    day_low,
                    day_high,
                    day_open,
                    day_close,
                    day_change,
                    raw_json
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    self._timestamp(message),
                    1 if data.get("isClosed") else 0,
                    self._float(data.get("bestSell")),
                    self._float(data.get("bestBuy")),
                    self._float(data.get("volumeSrc")),
                    self._float(data.get("volumeDst")),
                    self._float(data.get("latest")),
                    self._float(data.get("mark")),
                    self._float(data.get("dayLow")),
                    self._float(data.get("dayHigh")),
                    self._float(data.get("dayOpen")),
                    self._float(data.get("dayClose")),
                    self._float(data.get("dayChange")),
                    json.dumps(
                        data,
                        ensure_ascii=False,
                    ),
                ),
            )

        self._apply_retention("market_stats")

    def paths(self) -> dict[str, Path]:
        return {
            "candles": self.candles_db,
            "trades": self.trades_db,
            "orderbook": self.orderbook_db,
            "market_stats": self.market_stats_db,
        }
