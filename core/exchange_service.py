"""
KIA BOT - Exchange Service
"""

from __future__ import annotations

from exchange.nobitex import Nobitex


class ExchangeService:

    def __init__(self, bot: Nobitex) -> None:
        self.bot = bot
        self.running = False

    async def start(self) -> None:
        await self.bot.connect()
        self.running = True

    async def stop(self) -> None:
        if self.running:
            await self.bot.close()

        self.running = False

    async def switch(self, bot: Nobitex) -> None:
        await self.stop()

        self.bot = bot

        await self.bot.connect()

        self.running = True
