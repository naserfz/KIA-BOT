"""
KIA BOT - Database Service
"""

from __future__ import annotations

from database.market_database import MarketDatabase


class DatabaseService:

    def __init__(self, database: MarketDatabase) -> None:
        self.database = database
        self.running = False

    async def start(self) -> None:
        self.running = True

    async def stop(self) -> None:
        self.running = False

    def save(self, message: dict) -> None:
        self.database.save(message)
