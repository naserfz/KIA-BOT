from __future__ import annotations

import asyncio
import json
from pathlib import Path

from core.database_service import DatabaseService
from core.exchange_service import ExchangeService
from core.service_manager import ServiceManager

from database.market_database import MarketDatabase

from exchange.nobitex import Nobitex
from exchange.normalizer import ExchangeNormalizer


ROOT = Path(__file__).parent.parent
SELECTION_FILE = ROOT / "market_selection.json"


class KIACore:

    SUPPORTED_EXCHANGES = (
        "NOBITEX",
    )

    def __init__(self) -> None:

        self.selections = self._load_selection()

        self.bots: dict[str, Nobitex] = {}
        self.databases: dict[tuple[str, str], MarketDatabase] = {}
        self.database_services: dict[tuple[str, str], DatabaseService] = {}
        self.exchange_services: dict[str, ExchangeService] = {}

        self.normalizer = ExchangeNormalizer()
        self.service_manager = ServiceManager()

        self.running = False

        self._build_runtime()

    @staticmethod
    def _load_selection() -> dict[str, set[str]]:

        if not SELECTION_FILE.exists():
            raise RuntimeError(
                "market_selection.json not found."
            )

        payload = json.loads(
            SELECTION_FILE.read_text(
                encoding="utf-8"
            )
        )

        result: dict[str, set[str]] = {}

        for item in payload.get("selections", []):

            exchange = str(
                item.get("exchange", "")
            ).strip().upper()

            if not exchange:
                continue

            symbols = {
                str(symbol).strip().upper()
                for symbol in item.get("symbols", [])
                if str(symbol).strip()
            }

            if symbols:
                result[exchange] = symbols

        if not result:
            raise RuntimeError(
                "No markets selected in market_selection.json."
            )

        return result

    def _build_runtime(self) -> None:

        for exchange, symbols in self.selections.items():

            if exchange not in self.SUPPORTED_EXCHANGES:
                raise RuntimeError(
                    f"Unsupported exchange: {exchange}"
                )

            bot = Nobitex()

            self.bots[exchange] = bot

            exchange_service = ExchangeService(bot)

            self.exchange_services[exchange] = (
                exchange_service
            )

            self.service_manager.register(
                f"exchange_{exchange.lower()}",
                exchange_service,
            )

            for symbol in sorted(symbols):

                database = MarketDatabase(
                    exchange=exchange.lower(),
                    symbol=symbol,
                    root=ROOT / "database",
                )

                database_service = DatabaseService(
                    database
                )

                key = (
                    exchange,
                    symbol,
                )

                self.databases[key] = database
                self.database_services[key] = (
                    database_service
                )

                self.service_manager.register(
                    f"database_{exchange.lower()}_{symbol.lower()}",
                    database_service,
                )

    async def start(self) -> None:

        if self.running:
            return

        print("")
        print("=" * 70)
        print("KIA BOT")
        print("=" * 70)

        for exchange, symbols in self.selections.items():

            print(
                f"EXCHANGE: {exchange}"
            )

            print(
                f"MARKETS: {', '.join(sorted(symbols))}"
            )

        print("=" * 70)

        await self.service_manager.start_all()

        for exchange, symbols in self.selections.items():

            bot = self.bots[exchange]

            await bot.connect()

            await bot.select_markets(
                sorted(symbols),
                "5",
            )

        self.running = True

        print("")
        print("DATABASES READY")
        print("WAITING FOR RAW DATA...")
        print("")

        try:

            tasks = [
                asyncio.create_task(
                    self._consume_exchange(
                        exchange,
                        bot,
                    )
                )
                for exchange, bot
                in self.bots.items()
            ]

            await asyncio.gather(*tasks)

        except asyncio.CancelledError:
            raise

        finally:

            self.running = False

    async def _consume_exchange(
        self,
        exchange: str,
        bot: Nobitex,
    ) -> None:

        async for message in bot.messages():

            normalized = self.normalizer.normalize(
                message
            )

            symbol = str(
                normalized.get("symbol", "")
            ).strip().upper()

            key = (
                exchange,
                symbol,
            )

            database_service = (
                self.database_services.get(key)
            )

            if database_service is None:
                print(
                    f"[SKIP] No database for "
                    f"{exchange}/{symbol}"
                )
                continue

            database_service.save(
                normalized
            )

            print(
                f"[SAVED] "
                f"{exchange} "
                f"{symbol} "
                f"{normalized['type']}"
            )

    async def stop(self) -> None:

        if not self.running:
            return

        print("")
        print("STOPPING KIA BOT...")

        for bot in self.bots.values():

            await bot.close()

        await self.service_manager.stop_all()

        self.running = False

        print("KIA BOT STOPPED")

    async def restart(self) -> None:

        await self.stop()

        self.selections = self._load_selection()

        self.bots.clear()
        self.databases.clear()
        self.database_services.clear()
        self.exchange_services.clear()
        self.service_manager = ServiceManager()

        self._build_runtime()

        await self.start()


if __name__ == "__main__":
    asyncio.run(KIACore().start())
